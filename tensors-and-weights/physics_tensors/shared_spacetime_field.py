"""
Shared spacetime field for the Physics World Model.

Source: tensors-and-weights/physics_tensors RiemannTensor, RicciTensor,
WeylTensor, EinsteinTensor, and EnergyMomentumTensor.
Integrated: 2026-09-24
Purpose: one persistent metric field whose connection, Riemann, Ricci,
Weyl, and Einstein tensors are derived aspects of that same geometry.
Matter stress-energy is stored on the matter side. The metric's dynamical
evolution law is not invented here.

Modified: 2026-09-24
Modified by: daeron
Justification: the world-model path was projecting independent tensor
samples onto five oscillator bands and assigning Ricci from stress-energy.
Those calls are not relations of a shared geometry. This module is the
field owner those relations require. A wrapper around the projection would
have preserved the false architecture. Derive now refuses a silent identity
inverse, and observation returns a detached harmonic snapshot.
Provenance: PROVENANCE.md
Files: tensors-and-weights/physics_tensors/shared_spacetime_field.py
"""

from __future__ import annotations

import hashlib
import math
from typing import Any, Dict, Optional

import numpy as np

from physics_tensors.einstein_tensor import EinsteinTensor
from physics_tensors.energy_momentum_tensor import EnergyMomentumTensor
from physics_tensors.ricci_tensor import RicciTensor
from physics_tensors.riemann_tensor import RiemannTensor
from physics_tensors.weyl_tensor import WeylTensor


METRIC_EVOLUTION_LAW = "UNRESOLVED"
"""No ADM, BSSN, Z4c, or other metric evolution equation is canonical here."""

_UNRESOLVED_EVOLUTION_REASON = (
    "No canonical metric evolution law is specified. Repository search found "
    "weyl-todo.md naming BSSN/Z4c, Regge-Wheeler/Zerilli, and Teukolsky as later "
    "options for a different experiment, not as the Physics World Model evolution "
    "equation. g_mu_nu is not advanced."
)


class SharedFieldError(RuntimeError):
    """The shared spacetime field rejected a state that breaks its geometry."""

    def __init__(self, message: str) -> None:
        super().__init__(f"SharedFieldError: {message}")


class UnresolvedSpacetimeEvolution(SharedFieldError):
    """The metric evolution equation has not been specified by repository authority."""

    def __init__(self, message: str = _UNRESOLVED_EVOLUTION_REASON) -> None:
        RuntimeError.__init__(self, f"UnresolvedSpacetimeEvolution: {message}")


def minkowski_metric(grid_shape: tuple[int, int, int]) -> np.ndarray:
    """Return a constant mostly-minus Minkowski metric on a 3-D spatial lattice.

    Args:
        grid_shape: Positive ``(nx, ny, nz)`` lattice used by ``RiemannTensor``.

    Returns:
        Metric field with shape ``grid_shape + (4, 4)`` and diagonal
        ``(-1, 1, 1, 1)``.
    """
    _require_grid_shape(grid_shape)
    metric = np.zeros(grid_shape + (4, 4), dtype=np.float64)
    metric[..., 0, 0] = -1.0
    metric[..., 1, 1] = 1.0
    metric[..., 2, 2] = 1.0
    metric[..., 3, 3] = 1.0
    return metric


def spatial_curvature_metric(
    grid_shape: tuple[int, int, int],
    amplitude: float = 0.08,
) -> np.ndarray:
    """Return Minkowski plus a smooth positive bump in ``g_11``.

    The bump is a product of sine lobes that vanish on the lattice boundary.
    It is a fixed geometry for relation checks. It is not a time-evolution step.

    Args:
        grid_shape: Positive ``(nx, ny, nz)`` lattice.
        amplitude: Height of the ``g_11`` bump. Must be finite and greater than zero,
            and small enough that ``g_11`` stays positive.

    Returns:
        Metric field with shape ``grid_shape + (4, 4)``.
    """
    _require_grid_shape(grid_shape)
    if not math.isfinite(amplitude) or amplitude <= 0.0 or amplitude >= 1.0:
        raise SharedFieldError(
            f"spatial curvature amplitude must lie in (0, 1), received {amplitude!r}"
        )
    metric = minkowski_metric(grid_shape)
    axes = [np.linspace(0.0, 1.0, count, dtype=np.float64) for count in grid_shape]
    xx, yy, zz = np.meshgrid(*axes, indexing="ij")
    bump = amplitude * np.sin(np.pi * xx) * np.sin(np.pi * yy) * np.sin(np.pi * zz)
    metric[..., 1, 1] = metric[..., 1, 1] + bump
    return metric


def _require_grid_shape(grid_shape: tuple[int, int, int]) -> None:
    """Reject a lattice RiemannTensor cannot own."""
    if not isinstance(grid_shape, tuple) or len(grid_shape) != 3:
        raise SharedFieldError(f"grid_shape must be a 3-tuple, received {grid_shape!r}")
    if any((not isinstance(dim, int)) or isinstance(dim, bool) or dim <= 1 for dim in grid_shape):
        raise SharedFieldError(
            f"each grid dimension must be an integer greater than 1, received {grid_shape!r}"
        )


class SharedSpacetimeField:
    """
    Persistent spacetime geometry and the quantities derived from it.

    The metric field is the stored geometry. The inverse metric, Christoffel
    connection, Riemann tensor, Ricci tensor, Ricci scalar, Weyl tensor, and
    Einstein tensor are recomputed from that metric. Stress-energy is matter
    state on the same metric. Harmonic, recursive, ARFS, and quantum structures
    may be held beside this geometry only with an explicit coupling status.
    """

    def __init__(self, grid_shape: tuple[int, int, int] = (4, 4, 4), dx: float = 1.0) -> None:
        """Own an empty lattice until ``establish_metric`` loads a geometry.

        Args:
            grid_shape: Spatial lattice passed to the curvature owners.
            dx: Finite-difference spacing used by ``RiemannTensor.compute_from_metric``.
        """
        _require_grid_shape(grid_shape)
        if not math.isfinite(dx) or dx <= 0.0:
            raise SharedFieldError(f"grid spacing dx must be positive and finite, received {dx!r}")
        self.grid_shape = grid_shape
        self.dx = float(dx)
        self.riemann = RiemannTensor(grid_shape=grid_shape)
        self.ricci = RicciTensor(dimensions=4)
        self.weyl = WeylTensor(grid_shape=grid_shape)
        self.einstein = EinsteinTensor(dimensions=4)
        self.metric_field: Optional[np.ndarray] = None
        self.ricci_scalar_field: Optional[np.ndarray] = None
        self.stress_energy: Optional[EnergyMomentumTensor] = None
        self.geometry_current = False
        self.geometry_generation = 0
        self.coordinate_time = 0.0
        self.proper_time = 0.0
        self.elapsed_coordinate = 0.0
        self.time_dilation: Optional[float] = None
        self.harmonic_state: Optional[Dict[str, Any]] = None
        self.recursive_tensor: Any = None
        self.recursive_coupling = "UNRESOLVED"
        self.arfs_tensor: Any = None
        self.arfs_coupling = "UNRESOLVED"
        self.quantum_coupling = "UNRESOLVED"
        self.metric_evolution_law = METRIC_EVOLUTION_LAW
        self._observer_position = np.array([0.5, 0.5, 0.5], dtype=np.float64)

    def establish_minkowski(self) -> None:
        """Load a flat Minkowski lattice and derive its curvature."""
        self.establish_metric(minkowski_metric(self.grid_shape))

    def establish_metric(self, metric_field: np.ndarray) -> None:
        """Replace the persistent metric and derive the shared geometry from it.

        Args:
            metric_field: ``g_mu_nu`` with shape ``grid_shape + (4, 4)``.
        """
        metric = self._validated_metric(metric_field)
        self.metric_field = metric
        self.geometry_current = False
        self.derive_geometry()

    def perturb_metric(self, delta: np.ndarray) -> None:
        """Add a metric perturbation to the persistent field and mark geometry stale.

        The next ``derive_geometry`` starts from the perturbed metric. This does
        not reconstruct a metric from another tensor family.

        Args:
            delta: Additive perturbation with the same shape as the metric field.
        """
        if self.metric_field is None:
            raise SharedFieldError("cannot perturb a metric that has not been established")
        shift = np.asarray(delta, dtype=np.float64)
        if shift.shape != self.metric_field.shape:
            raise SharedFieldError(
                f"metric perturbation shape {shift.shape} != metric shape {self.metric_field.shape}"
            )
        if not np.all(np.isfinite(shift)):
            raise SharedFieldError("metric perturbation contains non-finite values")
        self.metric_field = self._validated_metric(self.metric_field + shift)
        self.geometry_current = False

    def install_stress_energy(self, stress_energy: EnergyMomentumTensor) -> None:
        """Store matter stress-energy that was built on this field's metric.

        Args:
            stress_energy: A computed ``EnergyMomentumTensor``. Curvature is not
                replaced by this tensor.

        Returns:
            None. The Ricci field is left untouched.
        """
        if not isinstance(stress_energy, EnergyMomentumTensor):
            raise SharedFieldError(
                "stress-energy must be an EnergyMomentumTensor built from matter, "
                f"received {type(stress_energy).__name__}"
            )
        if self.metric_field is None:
            raise SharedFieldError("cannot install stress-energy before a metric exists")
        if stress_energy.tensor is None:
            raise SharedFieldError("stress-energy tensor was not computed")
        matter_metric = np.asarray(stress_energy.metric, dtype=np.float64)
        if matter_metric.shape != self.metric_field.shape or not np.allclose(
            matter_metric, self.metric_field, rtol=0.0, atol=1e-12
        ):
            raise SharedFieldError("stress-energy was not built on the persistent metric")
        tensor = np.asarray(stress_energy.tensor, dtype=np.float64)
        if tensor.shape != self.grid_shape + (4, 4):
            raise SharedFieldError(
                f"stress-energy shape {tensor.shape} != {self.grid_shape + (4, 4)}"
            )
        if not np.all(np.isfinite(tensor)):
            raise SharedFieldError("stress-energy tensor contains non-finite values")
        self.stress_energy = stress_energy
        christoffel = self.riemann.christoffel_symbols
        if christoffel is not None:
            stress_energy.inject_christoffel(christoffel)

    def derive_geometry(self) -> Dict[str, np.ndarray]:
        """Derive connection and curvature from the persistent metric.

        Returns:
            The derived fields: inverse metric, Christoffel, Riemann, Ricci,
            Ricci scalar, Weyl, and Einstein. Ricci is not read from stress-energy.
        """
        if self.metric_field is None:
            raise SharedFieldError("cannot derive geometry without a metric")
        try:
            riemann_field = self.riemann.compute_from_metric(self.metric_field, dx=self.dx)
        except (ValueError, np.linalg.LinAlgError) as exc:
            raise SharedFieldError(
                f"geometry derivation could not invert the persistent metric: {exc}"
            ) from exc
        if self.riemann.inverse_metric_field is None or self.riemann.christoffel_symbols is None:
            raise SharedFieldError("Riemann derivation did not retain inverse metric and connection")
        inverse_residual = self._inverse_identity_residual()
        if inverse_residual >= 1e-9:
            raise SharedFieldError(
                "derived inverse is not the inverse of the persistent metric "
                f"(residual {inverse_residual})"
            )
        ricci_field = self.ricci.compute_from_riemann(riemann_field)
        scalar_field = self.einstein._compute_ricci_scalar(
            ricci_field,
            self.riemann.inverse_metric_field,
            self.grid_shape,
        )
        einstein_field = self.einstein._compute_einstein_tensor(
            ricci_field,
            self.metric_field,
            scalar_field,
            self.grid_shape,
        )
        self.einstein._ricci_tensor_field = ricci_field
        self.einstein._ricci_scalar_field = scalar_field
        self.einstein._einstein_tensor_field = einstein_field
        self.einstein.tensor = np.mean(einstein_field, axis=(0, 1, 2))
        self.ricci_scalar_field = scalar_field
        self.weyl.compute_from_field(
            riemann_field,
            ricci_field,
            scalar_field,
            self.metric_field,
            self.riemann.inverse_metric_field,
        )
        if self.stress_energy is not None:
            self.stress_energy.inject_christoffel(self.riemann.christoffel_symbols)
        self._refresh_time_dilation()
        self.geometry_generation += 1
        self.geometry_current = True
        return {
            "inverse_metric": self.riemann.inverse_metric_field,
            "christoffel": self.riemann.christoffel_symbols,
            "riemann": riemann_field,
            "ricci": ricci_field,
            "ricci_scalar": scalar_field,
            "weyl": self.weyl.weyl_field,
            "einstein": einstein_field,
        }

    def evolve_metric(self, elapsed: float) -> None:
        """Refuse to advance ``g_mu_nu`` until an evolution law is specified.

        Args:
            elapsed: Requested coordinate interval. It is validated and then not applied
                to the metric.
        """
        if not math.isfinite(elapsed) or elapsed <= 0.0:
            raise SharedFieldError(
                f"metric evolution interval must be positive and finite, received {elapsed!r}"
            )
        raise UnresolvedSpacetimeEvolution(_UNRESOLVED_EVOLUTION_REASON)

    def integrate_temporal_interval(self, elapsed: float, coordinate: float) -> Dict[str, float]:
        """Advance coordinate time and proper time without evolving the metric.

        Proper time uses ``RiemannTensor.compute_time_dilation`` at the field's
        observer position. The metric components stay on the last established geometry.

        Args:
            elapsed: Positive finite coordinate interval from the internal clock.
            coordinate: Absolute coordinate time reported by that clock.

        Returns:
            The elapsed interval, dilation factor, proper-time advance, and the
            stored coordinate and proper times after the advance.
        """
        if not self.geometry_current or self.time_dilation is None:
            raise SharedFieldError("temporal integration requires current derived geometry")
        if not math.isfinite(elapsed) or elapsed <= 0.0:
            raise SharedFieldError(
                f"temporal elapsed must be positive and finite, received {elapsed!r}"
            )
        if not math.isfinite(coordinate):
            raise SharedFieldError(f"temporal coordinate must be finite, received {coordinate!r}")
        metric_digest = self.metric_digest()
        proper_advance = float(elapsed) * float(self.time_dilation)
        self.elapsed_coordinate += float(elapsed)
        self.coordinate_time = float(coordinate)
        self.proper_time += proper_advance
        if self.metric_digest() != metric_digest:
            raise SharedFieldError("temporal integration changed the metric")
        return {
            "elapsed": float(elapsed),
            "coordinate_time": self.coordinate_time,
            "time_dilation": float(self.time_dilation),
            "proper_advance": proper_advance,
            "proper_time": self.proper_time,
        }

    def hold_recursive_state(self, recursive_tensor: Any) -> None:
        """Retain recursive state machinery without a geometry coupling.

        Args:
            recursive_tensor: The repository ``RecursiveTensor`` instance.
        """
        if recursive_tensor is None:
            raise SharedFieldError("recursive state holder is missing")
        self.recursive_tensor = recursive_tensor
        self.recursive_coupling = "UNRESOLVED"

    def hold_arfs_state(self, arfs_tensor: Any) -> None:
        """Retain an ARFS substrate without treating it as a log callback.

        Args:
            arfs_tensor: The repository ARFS tensor, or None when it is not constructed.
        """
        self.arfs_tensor = arfs_tensor
        self.arfs_coupling = "UNRESOLVED"

    def record_harmonic_state(self, snapshot: Dict[str, Any]) -> None:
        """Store harmonic oscillator state as subordinate field state.

        Args:
            snapshot: Amplitudes, phases, breath position, and elapsed interval
                produced by the harmonic equations. Geometry is not read from it.
        """
        amplitudes = snapshot.get("amplitudes")
        phases = snapshot.get("phases")
        if not isinstance(amplitudes, dict) or not isinstance(phases, dict):
            raise SharedFieldError("harmonic snapshot is missing amplitude and phase maps")
        self.harmonic_state = {
            "breath_position": snapshot.get("breath_position"),
            "field_elapsed": snapshot.get("field_elapsed"),
            "amplitudes": {str(band): float(value) for band, value in amplitudes.items()},
            "phases": {str(band): float(value) for band, value in phases.items()},
        }

    def relation_residuals(self) -> Dict[str, float]:
        """Measure the shared-geometry identities on the current fields.

        Returns:
            Maximum absolute residuals of ``g g^{-1} = I``, the Einstein
            definition, and the Weyl contraction. Stress-energy is not an input.
        """
        self._require_derived()
        assert self.metric_field is not None
        assert self.riemann.inverse_metric_field is not None
        assert self.ricci_scalar_field is not None
        assert self.einstein.get_einstein_tensor_field() is not None
        expected_einstein = self.ricci.tensor - 0.5 * self.metric_field * self.ricci_scalar_field[..., None, None]
        weyl_contraction = np.einsum("...am an->...mn", self.weyl.weyl_field)
        return {
            "inverse_metric": self._inverse_identity_residual(),
            "einstein_definition": float(
                np.max(np.abs(self.einstein.get_einstein_tensor_field() - expected_einstein))
            ),
            "weyl_trace": float(np.max(np.abs(weyl_contraction))),
        }

    def observe(self) -> Dict[str, Any]:
        """Read the persistent field. This does not evolve or perturb it.

        Returns:
            Digests, norms, temporal coordinates, relation residuals, and the
            unresolved coupling statuses.
        """
        self._require_derived()
        assert self.metric_field is not None
        assert self.riemann.christoffel_symbols is not None
        assert self.ricci_scalar_field is not None
        assert self.einstein.get_einstein_tensor_field() is not None
        stress_norm = None
        if self.stress_energy is not None and self.stress_energy.tensor is not None:
            stress_norm = float(np.max(np.abs(self.stress_energy.tensor)))
        return {
            "metric_digest": self.metric_digest(),
            "metric_shape": list(self.metric_field.shape),
            "coordinate_time": self.coordinate_time,
            "proper_time": self.proper_time,
            "elapsed_coordinate": self.elapsed_coordinate,
            "time_dilation": self.time_dilation,
            "geometry_generation": self.geometry_generation,
            "geometry_current": self.geometry_current,
            "metric_evolution_law": self.metric_evolution_law,
            "metric_evolution_reason": _UNRESOLVED_EVOLUTION_REASON,
            "christoffel_max_abs": float(np.max(np.abs(self.riemann.christoffel_symbols))),
            "riemann_max_abs": float(np.max(np.abs(self.riemann.riemann_field))),
            "ricci_max_abs": float(np.max(np.abs(self.ricci.tensor))),
            "ricci_scalar_max_abs": float(np.max(np.abs(self.ricci_scalar_field))),
            "weyl_max_abs": float(np.max(np.abs(self.weyl.weyl_field))),
            "einstein_max_abs": float(np.max(np.abs(self.einstein.get_einstein_tensor_field()))),
            "stress_energy_max_abs": stress_norm,
            "einstein_equation_enforced": False,
            "relation_residuals": self.relation_residuals(),
            "recursive_coupling": self.recursive_coupling,
            "arfs_coupling": self.arfs_coupling,
            "quantum_coupling": self.quantum_coupling,
            "harmonic_state": self._harmonic_observation(),
            "curvature_derived_from_metric": True,
            "ricci_copied_from_stress_energy": False,
        }

    def metric_digest(self) -> str:
        """Return the SHA-256 digest of the persistent metric bytes.

        Returns:
            Hex digest of ``metric_field``.
        """
        if self.metric_field is None:
            raise SharedFieldError("metric digest requested before a metric exists")
        return hashlib.sha256(np.ascontiguousarray(self.metric_field).tobytes()).hexdigest()

    def unresolved_interfaces(self) -> Dict[str, Dict[str, str]]:
        """Name the couplings this field refuses to invent.

        Returns:
            Status, reason, and the authority that would close each gap.
        """
        return {
            "metric_evolution": {
                "status": self.metric_evolution_law,
                "reason": _UNRESOLVED_EVOLUTION_REASON,
                "source_required": (
                    "an operator-authored evolution formulation that names the "
                    "equation advancing g_mu_nu, such as a chosen ADM, BSSN, or other "
                    "numerical-relativity system"
                ),
            },
            "recursive_tensor": {
                "status": self.recursive_coupling,
                "reason": (
                    "RecursiveTensor owns its own state tensor and operations. "
                    "No repository artifact maps that state onto g_mu_nu or onto a scalar matter field."
                ),
                "source_required": (
                    "an operator-authored identification of which RecursiveTensor operation "
                    "acts on the shared metric or on the matter stress-energy"
                ),
            },
            "arfs": {
                "status": self.arfs_coupling,
                "reason": (
                    "EnhancedARFSTensor defines X execution, Y memory, Z symbolic, and T temporal "
                    "coordinates. No repository artifact maps those coordinates onto this metric field. "
                    "record_state_change is not an ARFS method and is not a field coupling."
                ),
                "source_required": (
                    "an operator-authored map from ARFS dimension controllers to the shared field state"
                ),
            },
            "quantum_tensors": {
                "status": self.quantum_coupling,
                "reason": (
                    "Quantum tensor modules define their own states and Berry curvature. "
                    "No repository artifact supplies a GR-quantum coupling equation."
                ),
                "source_required": (
                    "an operator-authored equation relating a named quantum tensor to this metric "
                    "or to its curvature"
                ),
            },
            "harmonic_geometry": {
                "status": "UNRESOLVED",
                "reason": (
                    "CoupledHarmonicBreath evolves delta, theta, alpha, beta, and gamma by its own "
                    "oscillator equation. Those bands are not a coordinate chart for g_mu_nu, and no "
                    "repository equation couples the curvature tensors into those bands."
                ),
                "source_required": (
                    "an operator-authored field boundary between the harmonic state and the metric "
                    "that preserves the geometric indices"
                ),
            },
            "timeline_engine": {
                "status": "UNRESOLVED",
                "reason": (
                    "TimelineEngine.process_tick advances its own harmonic phase by temporal_resolution. "
                    "TemporalCoherence does not name that engine."
                ),
                "source_required": (
                    "a packet that names which TimelineEngine state the internal-clock interval advances"
                ),
            },
            "einstein_equation_constraint": {
                "status": "UNRESOLVED",
                "reason": (
                    "G_mu_nu is derived from the metric and T_mu_nu is stored from matter. "
                    "The Einstein equation relates them, but no specified evolution law imposes "
                    "that constraint or chooses the 8 pi G / c^4 convention as a dynamical update."
                ),
                "source_required": (
                    "the same evolution formulation that advances the metric, stating whether and how "
                    "G_mu_nu and T_mu_nu are constrained"
                ),
            },
        }

    def _inverse_identity_residual(self) -> float:
        """Return max |g g^{-1} - I| on the current metric and derived inverse."""
        if self.metric_field is None or self.riemann.inverse_metric_field is None:
            raise SharedFieldError("inverse residual requested before a metric inverse exists")
        product = np.einsum(
            "...ij,...jk->...ik",
            self.metric_field,
            self.riemann.inverse_metric_field,
        )
        identity = np.broadcast_to(np.eye(4, dtype=np.float64), product.shape)
        return float(np.max(np.abs(product - identity)))

    def _harmonic_observation(self) -> Optional[Dict[str, Any]]:
        """Return a detached copy of stored harmonic state."""
        if self.harmonic_state is None:
            return None
        amplitudes = self.harmonic_state["amplitudes"]
        phases = self.harmonic_state["phases"]
        return {
            "breath_position": self.harmonic_state.get("breath_position"),
            "field_elapsed": self.harmonic_state.get("field_elapsed"),
            "amplitudes": {str(band): float(value) for band, value in amplitudes.items()},
            "phases": {str(band): float(value) for band, value in phases.items()},
        }

    def _refresh_time_dilation(self) -> float:
        """Store the stationary observer factor ``sqrt(|g_00|)`` at the field center."""
        dilation = float(self.riemann.compute_time_dilation(self._observer_position))
        if not math.isfinite(dilation) or dilation <= 0.0:
            raise SharedFieldError(f"metric time dilation is not positive and finite: {dilation}")
        self.time_dilation = dilation
        return dilation

    def _require_derived(self) -> None:
        """Reject observation of a field whose derived geometry is stale or absent."""
        if (
            not self.geometry_current
            or self.metric_field is None
            or self.ricci_scalar_field is None
            or self.riemann.inverse_metric_field is None
            or self.riemann.christoffel_symbols is None
            or self.einstein.get_einstein_tensor_field() is None
        ):
            raise SharedFieldError("shared geometry is not current")

    def _validated_metric(self, metric_field: np.ndarray) -> np.ndarray:
        """Return a contiguous finite, symmetric, invertible, mostly-minus metric."""
        metric = np.array(metric_field, dtype=np.float64, copy=True, order="C")
        expected = self.grid_shape + (4, 4)
        if metric.shape != expected:
            raise SharedFieldError(f"metric shape {metric.shape} != {expected}")
        if not np.all(np.isfinite(metric)):
            raise SharedFieldError("metric contains non-finite values")
        if not np.allclose(metric, np.swapaxes(metric, -1, -2), rtol=0.0, atol=1e-10):
            raise SharedFieldError("metric is not symmetric")
        if not np.all(metric[..., 0, 0] < 0.0):
            raise SharedFieldError("metric g_00 must be negative on the mostly-minus signature")
        for index in np.ndindex(self.grid_shape):
            point = metric[index]
            sign, logdet = np.linalg.slogdet(point)
            if sign == 0.0 or not np.isfinite(logdet):
                raise SharedFieldError(f"metric is singular at lattice index {index}")
        return metric
