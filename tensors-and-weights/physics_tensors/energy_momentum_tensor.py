"""
energy_momentum_tensor.py
-------------------------
Production-grade relativistic stress-energy tensor field T^μν for General Relativity
and classical/quantum field theory simulation.

Pipeline Integration
--------------------
This tensor is one of four in the Genesis Cosmos physics stack:

    metric_field (shared compute substrate)
        |
    EinsteinTensor.compute_from_metric_field(metric_field)
        |-- Gamma^l_mn  (Christoffel symbols)
        |-- R^r_smn (Riemann tensor)  -> WeylTensor.extract_from_riemann()
        |-- R_mn    (Ricci tensor)    -> RicciTensor
        |-- R       (Ricci scalar)
        +-- G_mn    (Einstein tensor) -> EnergyMomentumTensor.from_einstein_tensor()

    EnergyMomentumTensor can be constructed two ways:
        1. Forward:  from matter fields (scalar, fluid, EM) -> T^mn
        2. Inverse:  from Einstein tensor G_mn -> T_mn = (c^4/8piG)(G_mn + L g_mn)

    When used inside the pipeline, Christoffel symbols are injected from
    EinsteinTensor via inject_christoffel() rather than recomputed.

Field Types
-----------
    - Real scalar fields (Klein-Gordon Lagrangian)
    - Perfect fluids (Euler stress-energy)
    - Electromagnetic fields (Maxwell stress-energy)
    - From geometry (inverse Einstein equations)

Dependencies: numpy, scipy
"""

import json
import numpy as np
import logging
from typing import Optional, Tuple, Union, Dict, Any, List
from enum import Enum
from dataclasses import dataclass, field as dc_field
from scipy.integrate import solve_ivp

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Physical constants (SI)
# ---------------------------------------------------------------------------
class PhysicalConstants:
    """SI physical constants for stress-energy computation."""
    c: float = 299_792_458.0
    G: float = 6.674_30e-11
    hbar: float = 1.054_571_817e-34
    k_B: float = 1.380_649e-23
    epsilon_0: float = 8.854_187_8128e-12
    mu_0: float = 1.256_637_062_12e-6

    @classmethod
    def geometrized(cls) -> "PhysicalConstants":
        pc = cls()
        pc.c = 1.0
        pc.G = 1.0
        pc.hbar = 1.054_571_817e-34 / (6.674_30e-11 * 299_792_458.0)
        pc.epsilon_0 = 1.0
        pc.mu_0 = 1.0
        return pc


class UnitSystem(Enum):
    SI = "si"
    GEOMETRIZED = "geometrized"
    CGS = "cgs"
    NATURAL = "natural"


class EnergyCondition(Enum):
    NULL = "null"
    WEAK = "weak"
    STRONG = "strong"
    DOMINANT = "dominant"


class FieldType(Enum):
    SCALAR = "scalar"
    PERFECT_FLUID = "perfect_fluid"
    ELECTROMAGNETIC = "electromagnetic"
    FROM_GEOMETRY = "from_geometry"


@dataclass
class TensorDiagnostics:
    max_energy_density: float = 0.0
    min_energy_density: float = 0.0
    max_divergence: float = 0.0
    trace_range: Tuple[float, float] = (0.0, 0.0)
    condition_number: float = 0.0
    singular_points: int = 0
    energy_conditions: Dict[str, bool] = dc_field(default_factory=dict)
    is_symmetric: bool = True
    max_asymmetry: float = 0.0


class EnergyMomentumTensor:
    """
    Relativistic stress-energy tensor field T^mn(x).

    Encodes energy density, momentum flux, and stress for a field configuration
    on a (pseudo-)Riemannian manifold. Central to Einstein's field equations:

        G_mn + L g_mn = (8piG / c^4) T_mn

    Participates in the four-tensor pipeline where all tensors share
    a single metric field / compute substrate. Christoffel symbols and
    curvature quantities are computed by EinsteinTensor and injected via
    inject_christoffel() rather than recomputed here.
    """

    def __init__(
        self,
        field: Union[np.ndarray, Dict[str, np.ndarray]],
        metric: np.ndarray,
        potential: Optional[np.ndarray] = None,
        field_type: FieldType = FieldType.SCALAR,
        units: UnitSystem = UnitSystem.SI,
        cosmological_constant: float = 0.0,
        grid_spacing: Optional[np.ndarray] = None,
    ):
        if metric.ndim < 2:
            raise ValueError(f"Metric must be at least 2D, got shape {metric.shape}.")
        if metric.shape[-1] != metric.shape[-2]:
            raise ValueError(
                f"Metric must have square trailing dims, got "
                f"{metric.shape[-2]}x{metric.shape[-1]}."
            )

        self.field_type = field_type
        self.metric = np.asarray(metric, dtype=np.float64)
        self.dimensions = self.metric.shape[-1]
        self._uniform_metric = (self.metric.ndim == 2)

        self.units = units
        if units == UnitSystem.GEOMETRIZED:
            self._constants = PhysicalConstants.geometrized()
        else:
            self._constants = PhysicalConstants()
        self.c = self._constants.c
        self.G = self._constants.G
        self.cosmological_constant = cosmological_constant
        self.grid_spacing = grid_spacing

        if field_type == FieldType.SCALAR:
            self._init_scalar(field, potential)
        elif field_type == FieldType.PERFECT_FLUID:
            self._init_perfect_fluid(field)
        elif field_type == FieldType.ELECTROMAGNETIC:
            self._init_electromagnetic(field)
        elif field_type == FieldType.FROM_GEOMETRY:
            self._init_from_geometry(field)
        else:
            raise ValueError(f"Unknown field type: {field_type}")

        self.tensor: Optional[np.ndarray] = None
        self._inverse_metric: Optional[np.ndarray] = None
        self._christoffel: Optional[np.ndarray] = None
        self._diagnostics = TensorDiagnostics()

        self._compute_inverse_metric()
        self._compute_tensor()
        self._run_diagnostics()

    # =================================================================
    # Init helpers
    # =================================================================

    def _init_scalar(self, field, potential):
        self.field = np.asarray(field, dtype=np.float64)
        self.potential = np.asarray(potential, dtype=np.float64) if potential is not None else None
        self.spatial_grid_shape = self.field.shape
        self.spatial_dims = len(self.spatial_grid_shape)
        if not self._uniform_metric and self.metric.shape[:-2] != self.spatial_grid_shape:
            raise ValueError(f"Metric spatial shape {self.metric.shape[:-2]} != field shape {self.spatial_grid_shape}.")
        if self.potential is not None and self.potential.shape != self.spatial_grid_shape:
            raise ValueError(f"Potential shape {self.potential.shape} != field shape {self.spatial_grid_shape}.")
        self._fluid_density = self._fluid_pressure = self._fluid_velocity = self._faraday = None

    def _init_perfect_fluid(self, field):
        if not isinstance(field, dict):
            raise TypeError("Perfect fluid field must be dict with 'density','pressure','velocity'.")
        for key in ("density", "pressure", "velocity"):
            if key not in field:
                raise KeyError(f"Perfect fluid dict missing '{key}'.")
        self._fluid_density = np.asarray(field["density"], dtype=np.float64)
        self._fluid_pressure = np.asarray(field["pressure"], dtype=np.float64)
        self._fluid_velocity = np.asarray(field["velocity"], dtype=np.float64)
        self.spatial_grid_shape = self._fluid_density.shape
        self.spatial_dims = len(self.spatial_grid_shape)
        if self._fluid_pressure.shape != self.spatial_grid_shape:
            raise ValueError("Pressure shape must match density shape.")
        expected_vel = self.spatial_grid_shape + (self.dimensions,)
        if self._fluid_velocity.shape != expected_vel:
            raise ValueError(f"Velocity shape {self._fluid_velocity.shape} must be {expected_vel}.")
        if not self._uniform_metric and self.metric.shape[:-2] != self.spatial_grid_shape:
            raise ValueError("Metric spatial shape must match fluid density shape.")
        self.field = self._fluid_density
        self.potential = None
        self._faraday = None

    def _init_electromagnetic(self, field):
        self._faraday = np.asarray(field, dtype=np.float64)
        if self._faraday.shape[-1] != self.dimensions or self._faraday.shape[-2] != self.dimensions:
            raise ValueError(f"Faraday tensor trailing dims must be ({self.dimensions},{self.dimensions}).")
        self.spatial_grid_shape = self._faraday.shape[:-2]
        self.spatial_dims = len(self.spatial_grid_shape)
        if not self._uniform_metric and self.metric.shape[:-2] != self.spatial_grid_shape:
            raise ValueError("Metric spatial shape must match Faraday tensor spatial shape.")
        self.field = self._faraday
        self.potential = None
        self._fluid_density = self._fluid_pressure = self._fluid_velocity = None

    def _init_from_geometry(self, field):
        self._einstein_input = np.asarray(field, dtype=np.float64)
        if self._einstein_input.shape[-1] != self.dimensions or self._einstein_input.shape[-2] != self.dimensions:
            raise ValueError(f"Einstein tensor trailing dims must be ({self.dimensions},{self.dimensions}).")
        self.spatial_grid_shape = self._einstein_input.shape[:-2]
        self.spatial_dims = len(self.spatial_grid_shape)
        self.field = self._einstein_input
        self.potential = None
        self._fluid_density = self._fluid_pressure = self._fluid_velocity = self._faraday = None

    # =================================================================
    # Metric inversion
    # =================================================================

    def _compute_inverse_metric(self):
        if self._uniform_metric:
            try:
                self._inverse_metric = np.linalg.inv(self.metric)
            except np.linalg.LinAlgError:
                logger.error("Singular uniform metric. Using pseudo-inverse.")
                self._inverse_metric = np.linalg.pinv(self.metric)
                self._diagnostics.singular_points += 1
        else:
            self._inverse_metric = np.zeros_like(self.metric)
            singular_count = 0
            for idx in np.ndindex(self.spatial_grid_shape):
                try:
                    self._inverse_metric[idx] = np.linalg.inv(self.metric[idx])
                except np.linalg.LinAlgError:
                    self._inverse_metric[idx] = np.linalg.pinv(self.metric[idx])
                    singular_count += 1
            self._diagnostics.singular_points = singular_count

    def _g(self):
        if self._uniform_metric:
            return np.broadcast_to(self.metric, self.spatial_grid_shape + self.metric.shape)
        return self.metric

    def _g_inv(self):
        if self._uniform_metric:
            return np.broadcast_to(self._inverse_metric, self.spatial_grid_shape + self._inverse_metric.shape)
        return self._inverse_metric

    # =================================================================
    # Pipeline: Christoffel injection
    # =================================================================

    def inject_christoffel(self, christoffel: np.ndarray) -> None:
        """
        Accept pre-computed Christoffel symbols from EinsteinTensor pipeline.
        Avoids recomputing when operating inside the shared metric field stack.
        """
        self._christoffel = np.asarray(christoffel, dtype=np.float64)

    def get_christoffel(self) -> Optional[np.ndarray]:
        return self._christoffel

    def _ensure_christoffel(self) -> np.ndarray:
        if self._christoffel is not None:
            return self._christoffel
        self._christoffel = self._compute_christoffel_local()
        return self._christoffel

    def _compute_christoffel_local(self) -> np.ndarray:
        """
        Fallback: compute Christoffel symbols locally from the metric.
        Only used when not part of the 4-tensor pipeline.
        """
        dim = self.dimensions
        g = self._g()
        g_inv = self._g_inv()

        dg = []
        for sigma in range(self.spatial_dims):
            dx = self.grid_spacing[sigma] if self.grid_spacing is not None and sigma < len(self.grid_spacing) else 1.0
            dg.append(np.gradient(g, dx, axis=sigma))
        while len(dg) < dim:
            dg.append(np.zeros_like(g))

        christoffel_lower = np.zeros(self.spatial_grid_shape + (dim, dim, dim), dtype=np.float64)
        for lam in range(dim):
            for mu in range(dim):
                for nu in range(dim):
                    christoffel_lower[..., lam, mu, nu] = 0.5 * (
                        dg[mu][..., lam, nu] + dg[nu][..., lam, mu] - dg[lam][..., mu, nu]
                    )
        return np.einsum("...ls,...smn->...lmn", g_inv, christoffel_lower)

    # =================================================================
    # Compute stress-energy tensor
    # =================================================================

    def _compute_tensor(self):
        dispatch = {
            FieldType.SCALAR: self._compute_scalar_tensor,
            FieldType.PERFECT_FLUID: self._compute_perfect_fluid_tensor,
            FieldType.ELECTROMAGNETIC: self._compute_em_tensor,
            FieldType.FROM_GEOMETRY: self._compute_from_einstein,
        }
        dispatch[self.field_type]()

    def _compute_scalar_tensor(self):
        """T^mn = d^m phi d^n phi - 1/2 g^mn [d_a phi d^a phi + 2V(phi)]"""
        g_inv = self._g_inv()
        partial_derivs = self._compute_field_gradients()
        partials_stacked = np.stack(partial_derivs, axis=-1)
        contra_derivs = np.einsum("...ma,...a->...m", g_inv, partials_stacked)
        T = np.einsum("...m,...n->...mn", contra_derivs, contra_derivs)
        kinetic_scalar = np.einsum("...a,...a->...", partials_stacked, contra_derivs)
        lagrangian = kinetic_scalar.copy()
        if self.potential is not None:
            lagrangian += 2.0 * self.potential
        T -= 0.5 * np.einsum("...mn,...->...mn", g_inv, lagrangian)
        self.tensor = T

    def _compute_field_gradients(self) -> List[np.ndarray]:
        derivs = []
        for i in range(self.spatial_dims):
            dx = self.grid_spacing[i] if self.grid_spacing is not None and i < len(self.grid_spacing) else 1.0
            derivs.append(np.gradient(self.field, dx, axis=i))
        while len(derivs) < self.dimensions:
            derivs.append(np.zeros_like(self.field))
        return derivs

    def _compute_perfect_fluid_tensor(self):
        """T^mn = (rho + p/c^2) u^m u^n + p g^mn"""
        rho = self._fluid_density
        p = self._fluid_pressure
        u = self._fluid_velocity
        g_inv = self._g_inv()
        c2 = self.c ** 2
        enthalpy = rho + p / c2
        uu = np.einsum("...m,...n->...mn", u, u)
        self.tensor = np.einsum("...,...mn->...mn", enthalpy, uu) + np.einsum("...,...mn->...mn", p, g_inv)

    def _compute_em_tensor(self):
        """T^mn = (1/mu0)[F^ma F^n_a - 1/4 g^mn F_ab F^ab]"""
        F = self._faraday
        g = self._g()
        g_inv = self._g_inv()
        mu0 = self._constants.mu_0
        F_cov = np.einsum("...am,...bn,...mn->...ab", g, g, F)
        F_mixed = np.einsum("...nb,...ba->...na", g_inv, F_cov)
        FF = np.einsum("...ma,...na->...mn", F, F_mixed)
        F_scalar = np.einsum("...ab,...ab->...", F_cov, F)
        self.tensor = (1.0 / mu0) * (FF - 0.25 * np.einsum("...mn,...->...mn", g_inv, F_scalar))

    def _compute_from_einstein(self):
        """T_mn = (c^4/8piG)(G_mn + L g_mn), then raise indices."""
        G_cov = self._einstein_input
        g = self._g()
        g_inv = self._g_inv()
        kappa_inv = self.c ** 4 / (8.0 * np.pi * self.G)
        T_cov = kappa_inv * (G_cov + self.cosmological_constant * g)
        self.tensor = np.einsum("...ma,...nb,...ab->...mn", g_inv, g_inv, T_cov)

    # =================================================================
    # Diagnostics
    # =================================================================

    def _run_diagnostics(self):
        if self.tensor is None:
            return
        T00 = self.tensor[..., 0, 0]
        self._diagnostics.max_energy_density = float(np.nanmax(T00))
        self._diagnostics.min_energy_density = float(np.nanmin(T00))
        tr = self._trace_raw()
        self._diagnostics.trace_range = (float(np.nanmin(tr)), float(np.nanmax(tr)))
        if self._uniform_metric:
            self._diagnostics.condition_number = float(np.linalg.cond(self.metric))
        else:
            center = tuple(s // 2 for s in self.spatial_grid_shape)
            self._diagnostics.condition_number = float(np.linalg.cond(self.metric[center]))
        sym, asym = self._symmetry_check_internal()
        self._diagnostics.is_symmetric = sym
        self._diagnostics.max_asymmetry = asym

    @property
    def diagnostics(self) -> TensorDiagnostics:
        return self._diagnostics

    # =================================================================
    # Constructors
    # =================================================================

    @classmethod
    def from_scalar_field(cls, scalar: float, dim: int = 4) -> "EnergyMomentumTensor":
        field = np.array(scalar, dtype=np.float64)
        eta = np.diag([-1.0] + [1.0] * (dim - 1))
        return cls(field, eta, units=UnitSystem.GEOMETRIZED)

    @classmethod
    def from_manifold(cls, manifold: dict, dim: int = 4) -> "EnergyMomentumTensor":
        try:
            norm = float(manifold.get("ere", {}).get("norm", 0.0))
        except Exception:
            norm = 0.0
        return cls.from_scalar_field(norm, dim=dim)

    @classmethod
    def from_einstein_tensor(
        cls,
        einstein_tensor: np.ndarray,
        metric: np.ndarray,
        units: UnitSystem = UnitSystem.GEOMETRIZED,
        cosmological_constant: float = 0.0,
        christoffel: Optional[np.ndarray] = None,
    ) -> "EnergyMomentumTensor":
        """
        Construct T^mn from a pre-computed Einstein tensor G_mn.

        Pipeline integration path: EinsteinTensor computes G_mn from the
        metric, this derives what matter content the geometry implies.

            T_mn = (c^4 / 8piG) ( G_mn + L g_mn )
        """
        emt = cls(
            field=einstein_tensor,
            metric=metric,
            field_type=FieldType.FROM_GEOMETRY,
            units=units,
            cosmological_constant=cosmological_constant,
        )
        if christoffel is not None:
            emt.inject_christoffel(christoffel)
        return emt

    @classmethod
    def schwarzschild(cls, r: np.ndarray, M: float, units: UnitSystem = UnitSystem.GEOMETRIZED) -> "EnergyMomentumTensor":
        if units == UnitSystem.GEOMETRIZED:
            rs = 2.0 * M
        else:
            pc = PhysicalConstants()
            rs = 2.0 * pc.G * M / (pc.c ** 2)
        r = np.asarray(r, dtype=np.float64)
        Nr = r.shape[0]
        metric = np.zeros((Nr, 4, 4), dtype=np.float64)
        f = 1.0 - rs / np.clip(r, 1e-30, None)
        metric[:, 0, 0] = -f
        metric[:, 1, 1] = 1.0 / np.clip(f, 1e-30, None)
        metric[:, 2, 2] = r ** 2
        metric[:, 3, 3] = r ** 2
        return cls(np.zeros(Nr, dtype=np.float64), metric, units=units)

    @classmethod
    def flrw(cls, a, rho, p, units=UnitSystem.GEOMETRIZED) -> "EnergyMomentumTensor":
        a = np.asarray(a, dtype=np.float64)
        rho = np.asarray(rho, dtype=np.float64)
        p = np.asarray(p, dtype=np.float64)
        N = a.shape[0]
        metric = np.zeros((N, 4, 4), dtype=np.float64)
        metric[:, 0, 0] = -1.0
        metric[:, 1, 1] = a ** 2
        metric[:, 2, 2] = a ** 2
        metric[:, 3, 3] = a ** 2
        velocity = np.zeros((N, 4), dtype=np.float64)
        velocity[:, 0] = 1.0
        return cls(
            field={"density": rho, "pressure": p, "velocity": velocity},
            metric=metric, field_type=FieldType.PERFECT_FLUID, units=units,
        )

    # =================================================================
    # Index gymnastics
    # =================================================================

    def get_tensor(self) -> np.ndarray:
        self._assert_computed()
        return self.tensor

    def get_covariant_tensor(self) -> np.ndarray:
        self._assert_computed()
        g = self._g()
        return np.einsum("...ma,...nb,...ab->...mn", g, g, self.tensor)

    def get_mixed_tensor(self) -> np.ndarray:
        self._assert_computed()
        g = self._g()
        return np.einsum("...nb,...mb->...mn", g, self.tensor)

    def raise_index(self, T_lower, index=0):
        g_inv = self._g_inv()
        if index == 0:
            return np.einsum("...ma,...an->...mn", g_inv, T_lower)
        elif index == 1:
            return np.einsum("...na,...ma->...mn", g_inv, T_lower)
        raise ValueError(f"index must be 0 or 1, got {index}")

    def lower_index(self, T_upper, index=0):
        g = self._g()
        if index == 0:
            return np.einsum("...ma,...an->...mn", g, T_upper)
        elif index == 1:
            return np.einsum("...na,...ma->...mn", g, T_upper)
        raise ValueError(f"index must be 0 or 1, got {index}")

    # =================================================================
    # Physical observables
    # =================================================================

    def energy_density(self) -> np.ndarray:
        self._assert_computed()
        return self.tensor[..., 0, 0]

    def momentum_density(self) -> np.ndarray:
        self._assert_computed()
        return self.tensor[..., 0, 1:]

    def stress_tensor(self) -> np.ndarray:
        self._assert_computed()
        return self.tensor[..., 1:, 1:]

    def pressure(self) -> np.ndarray:
        self._assert_computed()
        spatial = self.stress_tensor()
        n_spatial = self.dimensions - 1
        return np.einsum("...ii->...", spatial) / max(n_spatial, 1)

    def trace(self) -> np.ndarray:
        self._assert_computed()
        g = self._g()
        return np.einsum("...mn,...mn->...", g, self.tensor)

    def _trace_raw(self):
        if self.tensor is None:
            return np.array(0.0)
        g = self._g()
        return np.einsum("...mn,...mn->...", g, self.tensor)

    def contract(self, indices: Tuple[int, int]) -> np.ndarray:
        self._assert_computed()
        mu, nu = indices
        if not (0 <= mu < self.dimensions and 0 <= nu < self.dimensions):
            raise ValueError(f"Indices {indices} out of bounds for {self.dimensions}D.")
        return self.tensor[..., mu, nu]

    def equation_of_state_parameter(self) -> np.ndarray:
        self._assert_computed()
        rho = self.energy_density()
        p = self.pressure()
        return np.where(np.abs(rho) > 1e-30, p / rho, 0.0)

    # =================================================================
    # Conservation laws
    # =================================================================

    def check_conservation(self, tolerance=1e-6, use_covariant=True) -> Tuple[bool, np.ndarray]:
        """
        Check local conservation nabla_m T^mn ~ 0.
        Uses pipeline Christoffel if injected, otherwise computes locally.
        """
        self._assert_computed()
        dim = self.dimensions
        div = np.zeros(self.spatial_grid_shape + (dim,), dtype=np.float64)

        for nu in range(dim):
            for mu in range(dim):
                if mu < self.spatial_dims:
                    dx = self.grid_spacing[mu] if self.grid_spacing is not None and mu < len(self.grid_spacing) else 1.0
                    div[..., nu] += np.gradient(self.tensor[..., mu, nu], dx, axis=mu)

        if use_covariant:
            gamma = self._ensure_christoffel()
            gamma_trace = np.einsum("...mmn->...n", gamma)
            div += np.einsum("...l,...ln->...n", gamma_trace, self.tensor)
            div += np.einsum("...nml,...ml->...n", gamma, self.tensor)

        max_div = float(np.max(np.abs(div)))
        self._diagnostics.max_divergence = max_div
        return max_div <= tolerance, div

    # =================================================================
    # Energy conditions
    # =================================================================

    def check_energy_condition(self, condition: EnergyCondition, n_samples=1000) -> Tuple[bool, Dict[str, Any]]:
        self._assert_computed()
        dim = self.dimensions
        g = self._g()
        T_cov = self.get_covariant_tensor()
        rng = np.random.default_rng(42)
        violations = 0
        min_val = np.inf

        for _ in range(n_samples):
            spatial = rng.normal(size=dim - 1)
            spatial /= np.linalg.norm(spatial) + 1e-30

            if condition == EnergyCondition.NULL:
                k = np.zeros(dim); k[0] = 1.0; k[1:] = spatial
                m = float(np.min(np.einsum("...mn,m,n->...", T_cov, k, k)))
                if m < -1e-12: violations += 1
                min_val = min(min_val, m)

            elif condition == EnergyCondition.WEAK:
                speed = rng.uniform(0, 0.99)
                u = np.zeros(dim)
                u[0] = 1.0 / np.sqrt(1.0 - speed**2)
                u[1:] = speed * spatial * u[0]
                m = float(np.min(np.einsum("...mn,m,n->...", T_cov, u, u)))
                if m < -1e-12: violations += 1
                min_val = min(min_val, m)

            elif condition == EnergyCondition.STRONG:
                speed = rng.uniform(0, 0.99)
                u = np.zeros(dim)
                u[0] = 1.0 / np.sqrt(1.0 - speed**2)
                u[1:] = speed * spatial * u[0]
                tr = self.trace()
                T_eff = T_cov - 0.5 * np.einsum("...,...mn->...mn", tr, g)
                m = float(np.min(np.einsum("...mn,m,n->...", T_eff, u, u)))
                if m < -1e-12: violations += 1
                min_val = min(min_val, m)

            elif condition == EnergyCondition.DOMINANT:
                speed = rng.uniform(0, 0.99)
                u = np.zeros(dim)
                u[0] = 1.0 / np.sqrt(1.0 - speed**2)
                u[1:] = speed * spatial * u[0]
                T_mixed = self.get_mixed_tensor()
                j = -np.einsum("...mn,n->...m", T_mixed, u)
                j_norm = np.einsum("...mn,...m,...n->...", g, j, j)
                future = j[..., 0]
                if float(np.max(j_norm)) > 1e-12 or float(np.min(future)) < -1e-12:
                    violations += 1
                min_val = min(min_val, float(np.min(future)))

        satisfied = violations == 0
        details = {
            "condition": condition.value, "satisfied": satisfied,
            "violations": violations, "samples": n_samples,
            "violation_rate": violations / n_samples, "min_value": float(min_val),
        }
        self._diagnostics.energy_conditions[condition.value] = satisfied
        return satisfied, details

    # =================================================================
    # Geodesic integration
    # =================================================================

    def compute_geodesic(self, initial_position, initial_velocity,
                         proper_time_span=(0.0, 10.0), rtol=1e-10, atol=1e-12) -> Dict[str, np.ndarray]:
        """
        Integrate the geodesic equation via RK45. Uses pipeline Christoffel if injected.
        """
        dim = self.dimensions
        if len(initial_position) != dim or len(initial_velocity) != dim:
            raise ValueError(f"Position and velocity must have {dim} components.")

        gamma = self._ensure_christoffel()

        if self._uniform_metric:
            gamma_at = lambda pos: gamma if gamma.ndim == 3 else np.zeros((dim, dim, dim))
        else:
            shape = self.spatial_grid_shape
            def gamma_at(pos):
                idx = tuple(int(np.clip(np.round(pos[i]), 0, shape[i]-1)) if i < len(shape) else 0 for i, s in enumerate(shape))
                return gamma[idx]

        def rhs(tau, state):
            v = state[dim:]
            G = gamma_at(state[:dim])
            return np.concatenate([v, -np.einsum("mab,a,b->m", G, v, v)])

        sol = solve_ivp(rhs, proper_time_span, np.concatenate([initial_position, initial_velocity]),
                        method="RK45", rtol=rtol, atol=atol)
        if not sol.success:
            logger.warning(f"Geodesic integration: {sol.message}")
        return {"tau": sol.t, "position": sol.y[:dim].T, "velocity": sol.y[dim:].T}

    # =================================================================
    # Volume integrals
    # =================================================================

    def total_energy(self, volume_element=None) -> float:
        self._assert_computed()
        T00 = self.tensor[..., 0, 0]
        if volume_element is None:
            volume_element = self._compute_volume_element()
        cell_vol = np.prod(self.grid_spacing[:self.spatial_dims]) if self.grid_spacing is not None else 1.0
        return float(np.sum(T00 * volume_element * cell_vol))

    def total_momentum(self, volume_element=None) -> np.ndarray:
        self._assert_computed()
        if volume_element is None:
            volume_element = self._compute_volume_element()
        cell_vol = np.prod(self.grid_spacing[:self.spatial_dims]) if self.grid_spacing is not None else 1.0
        P = np.zeros(self.dimensions - 1)
        for i in range(1, self.dimensions):
            P[i-1] = float(np.sum(self.tensor[..., 0, i] * volume_element * cell_vol))
        return P

    def _compute_volume_element(self):
        g = self._g()
        if self._uniform_metric:
            return np.full(self.spatial_grid_shape, np.sqrt(np.abs(np.linalg.det(self.metric))))
        return np.sqrt(np.abs(np.linalg.det(g)))

    # =================================================================
    # Tensor algebra
    # =================================================================

    def tensor_contract(self, indices):
        return self.contract(indices)

    def tensor_project(self, axis, projection_type="sum"):
        self._assert_computed()
        if not (0 <= axis < self.spatial_dims):
            raise ValueError(f"Axis {axis} out of bounds for {self.spatial_dims} spatial dims.")
        ops = {"sum": np.sum, "mean": np.mean, "max": np.amax, "min": np.amin}
        if projection_type not in ops:
            raise ValueError(f"Unknown projection '{projection_type}'.")
        return ops[projection_type](self.tensor, axis=axis)

    def symmetry_check(self, tolerance=1e-12):
        self._assert_computed()
        return self._symmetry_check_internal(tolerance)

    def _symmetry_check_internal(self, tolerance=1e-12):
        if self.tensor is None:
            return True, 0.0
        diff = float(np.max(np.abs(self.tensor - np.swapaxes(self.tensor, -2, -1))))
        return diff <= tolerance, diff

    # =================================================================
    # Anomaly detection
    # =================================================================

    def detect_anomaly(self, threshold=1e5) -> Tuple[bool, Dict[str, Any]]:
        """Detect NaN, Inf, extreme values, spatial jumps. Compatible with Ricci/Weyl APIs."""
        self._assert_computed()
        anomalies: Dict[str, Any] = {}
        has_nan = bool(np.isnan(self.tensor).any())
        has_inf = bool(np.isinf(self.tensor).any())
        if has_nan or has_inf:
            anomalies["non_finite"] = {"nan": has_nan, "inf": has_inf}
        max_abs = float(np.max(np.abs(self.tensor)))
        anomalies["max_abs"] = max_abs
        if max_abs > threshold:
            anomalies["extreme_values"] = True
        if self.tensor.ndim > 2:
            max_jump = 0.0
            for axis in range(min(self.spatial_dims, self.tensor.ndim - 2)):
                max_jump = max(max_jump, float(np.max(np.abs(np.diff(self.tensor, axis=axis)))))
            anomalies["max_spatial_jump"] = max_jump
            if max_jump > threshold:
                anomalies["spatial_discontinuity"] = True
        min_rho = float(np.min(self.tensor[..., 0, 0]))
        if min_rho < -1e-10:
            anomalies["negative_energy_density"] = min_rho
        is_anomaly = bool(has_nan or has_inf or max_abs > threshold
                          or anomalies.get("spatial_discontinuity")
                          or anomalies.get("negative_energy_density") is not None)
        return is_anomaly, anomalies

    # =================================================================
    # ML features (compatible with Ricci/Weyl APIs)
    # =================================================================

    def to_ml_features(self, feature_set="all") -> np.ndarray:
        self._assert_computed()
        features = []
        if feature_set in ("tensor_components", "all"):
            mean_T = np.mean(self.tensor.reshape(-1, self.dimensions, self.dimensions), axis=0)
            features.append(mean_T.flatten())
        if feature_set in ("scalar", "all"):
            tr, rho, p = self.trace(), self.energy_density(), self.pressure()
            features.append(np.array([float(np.mean(tr)), float(np.std(tr)),
                                      float(np.mean(rho)), float(np.max(rho)), float(np.mean(p))]))
        if feature_set in ("eigenvalues", "all"):
            mean_T = np.mean(self.tensor.reshape(-1, self.dimensions, self.dimensions), axis=0)
            features.append(np.linalg.eigvalsh(mean_T))
        return np.concatenate(features)

    def get_attention_weights(self, weighting_strategy="energy_density") -> np.ndarray:
        self._assert_computed()
        if weighting_strategy == "energy_density":
            weights = np.abs(self.energy_density())
        elif weighting_strategy == "trace_magnitude":
            weights = np.abs(self.trace())
        elif weighting_strategy == "frobenius":
            weights = np.linalg.norm(self.tensor, axis=(-2, -1))
        else:
            raise ValueError(f"Unknown strategy '{weighting_strategy}'.")
        total = np.sum(weights)
        return weights / total if total > 1e-10 else np.ones(self.spatial_grid_shape) / max(np.prod(self.spatial_grid_shape), 1)

    # =================================================================
    # Narrative generation (compatible with Ricci/Weyl APIs)
    # =================================================================

    def generate_narrative_prompt(self, detail_level="medium") -> str:
        self._assert_computed()
        parts = []
        rho = self.energy_density()
        mean_rho, max_rho = float(np.mean(rho)), float(np.max(rho))
        if max_rho < 1e-10:
            parts.append("This region is essentially vacuum.")
        else:
            parts.append(f"Matter/energy present: mean density {mean_rho:.2e}, peak {max_rho:.2e}.")
        if detail_level in ("medium", "high"):
            w = float(np.mean(self.equation_of_state_parameter()))
            if abs(w) < 0.01: parts.append("Equation of state: dust-like (w~0).")
            elif abs(w - 1/3) < 0.05: parts.append("Equation of state: radiation-like (w~1/3).")
            elif w < -0.5: parts.append(f"Equation of state: dark-energy-like (w~{w:.2f}).")
            else: parts.append(f"EOS parameter w~{w:.3f}.")
        if detail_level == "high":
            d = self._diagnostics
            parts.append(f"Symmetric: {d.is_symmetric}. Trace: [{d.trace_range[0]:.2e},{d.trace_range[1]:.2e}].")
            parts.append(f"Metric cond#: {d.condition_number:.2e}. Singular pts: {d.singular_points}.")
        return " ".join(parts)

    # =================================================================
    # GAN feedback (compatible with RicciTensor API)
    # =================================================================

    def get_gan_feedback(self, target_tensor, feedback_type="component_wise") -> Dict[str, np.ndarray]:
        self._assert_computed()
        target = np.asarray(target_tensor, dtype=np.float64)
        if feedback_type == "component_wise":
            diff = self.tensor - target
            return {"difference": diff, "mse": np.array(np.mean(diff**2)), "max_abs_diff": np.array(np.max(np.abs(diff)))}
        elif feedback_type == "scalar_difference":
            g = self._g()
            return {"trace_difference": self.trace() - np.einsum("...mn,...mn->...", g, target)}
        elif feedback_type == "eigenvalue_difference":
            mean_s = np.mean(self.tensor.reshape(-1, self.dimensions, self.dimensions), axis=0)
            mean_t = np.mean(target.reshape(-1, self.dimensions, self.dimensions), axis=0)
            return {"eigenvalue_diff": np.linalg.eigvalsh(mean_s) - np.linalg.eigvalsh(mean_t)}
        raise ValueError(f"Unknown feedback_type: {feedback_type}")

    # =================================================================
    # Causal influence map (compatible with RicciTensor API)
    # =================================================================

    def get_causal_influence_map(self, event_type="generic") -> Dict[str, np.ndarray]:
        self._assert_computed()
        infl = {
            "energy_density_influence": np.abs(self.energy_density()),
            "pressure_influence": np.abs(self.pressure()),
            "trace_influence": np.abs(self.trace()),
        }
        if event_type == "black_hole_formation":
            infl["energy_density_influence"] *= 2.0; infl["pressure_influence"] *= 1.5
        elif event_type == "gravitational_wave_emission":
            infl["energy_density_influence"] *= 0.5; infl["trace_influence"] *= 2.5
        elif event_type == "stable_region":
            for k in infl:
                mx = np.max(infl[k]) + 1e-9
                infl[k] = 1.0 - np.clip(infl[k] / mx, 0, 1)
        for k in infl:
            total = np.sum(infl[k])
            infl[k] = infl[k] / total if total > 1e-9 else np.ones_like(infl[k]) / max(infl[k].size, 1)
        return infl

    # =================================================================
    # Serialization
    # =================================================================

    def to_dict(self) -> Dict[str, Any]:
        self._assert_computed()
        d = self._diagnostics
        return {
            "tensor": self.tensor.tolist(), "metric": self.metric.tolist(),
            "dimensions": self.dimensions, "field_type": self.field_type.value,
            "units": self.units.value, "spatial_grid_shape": list(self.spatial_grid_shape),
            "c": self.c, "G": self.G, "cosmological_constant": self.cosmological_constant,
            "diagnostics": {
                "max_energy_density": d.max_energy_density,
                "min_energy_density": d.min_energy_density,
                "max_divergence": d.max_divergence,
                "trace_range": list(d.trace_range),
                "condition_number": d.condition_number,
                "singular_points": d.singular_points,
                "is_symmetric": d.is_symmetric,
            },
        }

    def to_llm_structured_description(self) -> str:
        self._assert_computed()
        return json.dumps({
            "type": "EnergyMomentumTensor", "field_type": self.field_type.value,
            "dimensions": self.dimensions, "spatial_grid_shape": list(self.spatial_grid_shape),
            "energy_density": {"min": self._diagnostics.min_energy_density,
                               "max": self._diagnostics.max_energy_density,
                               "mean": float(np.mean(self.energy_density()))},
            "trace_range": list(self._diagnostics.trace_range),
            "is_symmetric": self._diagnostics.is_symmetric,
        }, separators=(",", ":"))

    def as_numpy(self) -> np.ndarray:
        self._assert_computed()
        return self.tensor

    def _assert_computed(self):
        if self.tensor is None:
            raise ValueError("Energy-momentum tensor has not been computed.")

    def __repr__(self):
        shape = self.tensor.shape if self.tensor is not None else None
        return f"<EnergyMomentumTensor shape={shape} dim={self.dimensions} type={self.field_type.value} units={self.units.value} L={self.cosmological_constant}>"

    def summary(self) -> str:
        self._assert_computed()
        d = self._diagnostics
        return "\n".join([
            "Energy-Momentum Tensor Summary",
            f"  Shape           : {self.tensor.shape}",
            f"  Field type      : {self.field_type.value}",
            f"  Dimensions      : {self.dimensions}",
            f"  Units           : {self.units.value}",
            f"  Energy density  : [{d.min_energy_density:.6e}, {d.max_energy_density:.6e}]",
            f"  Trace range     : [{d.trace_range[0]:.6e}, {d.trace_range[1]:.6e}]",
            f"  Metric cond #   : {d.condition_number:.6e}",
            f"  Singular points : {d.singular_points}",
            f"  Symmetric       : {d.is_symmetric} (max asym: {d.max_asymmetry:.2e})",
            f"  Lambda          : {self.cosmological_constant}",
        ])
