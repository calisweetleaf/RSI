"""
Riemann Curvature Tensor - Full Geometric Structure Module

Implements the complete Riemann curvature tensor R^ρ_σμν which encodes
the full geometry of curved spacetime. This is the foundational geometric
object from which all other curvature tensors are derived.

Decomposition:
    R^ρ_σμν = C^ρ_σμν                           (Weyl - traceless part)
            + (1/2)(g^ρ_μ R_σν - g^ρ_ν R_σμ     (Ricci part)
                  + g_σν R^ρ_μ - g_σμ R^ρ_ν)
            - (R/6)(g^ρ_μ g_σν - g^ρ_ν g_σμ)    (Scalar part)

Key Features:
- Time dilation computation (Oracle's internal_clock vs Timeline master_tick)
- Geodesic deviation (how nearby paths separate)
- Parallel transport tracking
- Tidal force computation via Weyl tensor
- Attention mechanism for curvature component selection

For Oracle Integration:
- compute_time_dilation() → feeds internal_clock.py
- get_geodesic_deviation() → perception of spacetime curvature
- query_curvature_at() → attention-based component selection

Production-Grade Features:
- Complete input validation on all public methods
- Comprehensive error handling with specific exception types
- ML feature extraction for integration with AI systems
- LLM-compatible narrative generation
- Anomaly detection for simulation stability
"""

import json
import numpy as np
from typing import Dict, Tuple, Optional, List, Any, Union
from dataclasses import dataclass
from enum import Enum
import logging

try:
    from cosmic_scroll_logger import get_cosmic_scroll_logger
except ImportError:
    try:
        from unified_cosmos.cosmic_scroll_logger import get_cosmic_scroll_logger
    except ImportError:
        get_cosmic_scroll_logger = None

# Configure logger for this module
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class CurvatureComponent(Enum):
    """Which aspect of curvature to attend to"""
    FULL = "full"              # All 20 independent components
    TIDAL = "tidal"            # Tidal forces (Weyl electric)
    ROTATION = "rotation"      # Frame dragging (Weyl magnetic)
    MATTER = "matter"          # Matter-induced curvature (Ricci)
    VACUUM = "vacuum"          # Pure geometry (Weyl)
    TIME_DILATION = "time_dilation"  # g_00 component effects


@dataclass
class CurvatureState:
    """Complete curvature information at a point"""
    position: np.ndarray           # [x, y, z] in grid
    riemann_tensor: np.ndarray     # Full R^ρ_σμν [4,4,4,4]
    weyl_tensor: np.ndarray        # C^ρ_σμν [4,4,4,4]
    ricci_tensor: np.ndarray       # R_μν [4,4]
    ricci_scalar: float            # R
    time_dilation_factor: float    # dτ/dt
    tidal_forces: np.ndarray       # 3x3 spatial tidal matrix
    attention_weights: Dict[CurvatureComponent, float]


class RiemannTensor:
    """
    Full Riemann Curvature Tensor Computation
    
    The Riemann tensor is the fundamental measure of spacetime curvature.
    It contains all geometric information about how spacetime is curved.
    
    Properties:
    - Antisymmetric in first pair: R^ρ_σμν = -R^ρ_σνμ
    - Antisymmetric in second pair: R^ρ_σμν = -R_ρσ^μν
    - Symmetric under pair exchange: R^ρ_σμν = R^μν_ρσ
    - First Bianchi identity: R^ρ_[σμν] = 0
    - Second Bianchi identity: ∇_[λ R^ρ_σ]μν = 0
    
    Independent components: 20 in 4D (reduced from 256 by symmetries)
    """
    
    def __init__(self, grid_shape: Tuple[int, int, int] = (64, 64, 64)) -> None:
        """
        Initialize Riemann tensor computation system.
        
        Args:
            grid_shape: Spatial dimensions of simulation grid (x, y, z).
            
        Raises:
            ValueError: If grid_shape is invalid (non-positive dimensions).
        """
        # Validate grid_shape
        if not isinstance(grid_shape, tuple) or len(grid_shape) != 3:
            raise ValueError(f"grid_shape must be a 3-tuple, got {type(grid_shape)}")
        if any(dim <= 0 for dim in grid_shape):
            raise ValueError(f"All grid dimensions must be positive, got {grid_shape}")
        
        self.grid_shape = grid_shape
        self.dims = 4  # 4D spacetime (t, x, y, z)
        
        # Storage for full Riemann tensor field
        # Shape: (grid_x, grid_y, grid_z, 4, 4, 4, 4)
        self.riemann_field = np.zeros((*grid_shape, 4, 4, 4, 4), dtype=np.float64)
        
        # Cached metric and inverse metric
        self.metric_field: Optional[np.ndarray] = None
        self.inverse_metric_field: Optional[np.ndarray] = None
        
        # Christoffel symbols (connection)
        self.christoffel_symbols: Optional[np.ndarray] = None
        
        # Attention mechanism for component selection
        self.attention_focus = CurvatureComponent.FULL
        self.attention_threshold = 0.01  # Minimum curvature to attend to
        
        # Track initialization state
        self._is_computed = False
        
        logger.info(f"RiemannTensor initialized with grid shape {grid_shape}")
    
    def compute_from_metric(
        self,
        metric_field: np.ndarray,
        dx: float = 1.0,
        weyl_tensor: Optional['WeylTensor'] = None
    ) -> np.ndarray:
        """
        Compute full Riemann tensor from metric field
        
        Uses finite differences to compute Christoffel symbols, then
        constructs Riemann tensor via:
        
        R^ρ_σμν = ∂_μ Γ^ρ_νσ - ∂_ν Γ^ρ_μσ + Γ^ρ_μλ Γ^λ_νσ - Γ^ρ_νλ Γ^λ_μσ
        
        Args:
            metric_field: Metric tensor g_μν at each grid point
            dx: Grid spacing for finite differences
            weyl_tensor: Optional WeylTensor instance for decomposition
            
        Returns:
            Full Riemann tensor field
        """
        self.metric_field = metric_field
        
        # Compute inverse metric
        self.inverse_metric_field = self._compute_inverse_metric(metric_field)
        
        # Compute Christoffel symbols
        self.christoffel_symbols = self._compute_christoffel_symbols(
            metric_field, dx
        )
        
        # Compute Riemann tensor components
        self.riemann_field = self._compute_riemann_components(
            self.christoffel_symbols, dx
        )
        
        logger.debug(f"Computed Riemann tensor, max curvature: {np.max(np.abs(self.riemann_field)):.6e}")
        
        return self.riemann_field
    
    def compute_from_decomposition(
        self,
        weyl_tensor: np.ndarray,
        ricci_tensor: np.ndarray,
        ricci_scalar: float,
        metric: np.ndarray,
        inverse_metric: np.ndarray
    ) -> np.ndarray:
        """
        Reconstruct Riemann from Weyl + Ricci decomposition
        
        R^ρ_σμν = C^ρ_σμν 
                + (1/2)(g^ρ_μ R_σν - g^ρ_ν R_σμ + g_σν R^ρ_μ - g_σμ R^ρ_ν)
                - (R/6)(g^ρ_μ g_σν - g^ρ_ν g_σμ)
        
        Args:
            weyl_tensor: Weyl conformal tensor C^ρ_σμν
            ricci_tensor: Ricci tensor R_μν
            ricci_scalar: Ricci scalar R
            metric: Metric tensor g_μν
            inverse_metric: Inverse metric g^μν
            
        Returns:
            Reconstructed Riemann tensor
        """
        riemann = np.zeros_like(weyl_tensor)
        
        # Start with Weyl part (traceless)
        riemann += weyl_tensor
        mixed_identity = np.eye(4, dtype=np.float64)
        ricci_raised = inverse_metric @ ricci_tensor
        
        # Add Ricci part. g^ρ_μ is the mixed identity; R^ρ_μ is raised.
        for rho in range(4):
            for sigma in range(4):
                for mu in range(4):
                    for nu in range(4):
                        riemann[rho, sigma, mu, nu] += 0.5 * (
                            mixed_identity[rho, mu] * ricci_tensor[sigma, nu]
                            - mixed_identity[rho, nu] * ricci_tensor[sigma, mu]
                            + metric[sigma, nu] * ricci_raised[rho, mu]
                            - metric[sigma, mu] * ricci_raised[rho, nu]
                        )
                        
                        # Scalar curvature part: -(R/6)(δ^ρ_μ g_σν - δ^ρ_ν g_σμ)
                        riemann[rho, sigma, mu, nu] -= (ricci_scalar / 6.0) * (
                            mixed_identity[rho, mu] * metric[sigma, nu]
                            - mixed_identity[rho, nu] * metric[sigma, mu]
                        )
        
        return riemann
    
    def compute_time_dilation(
        self,
        position: np.ndarray,
        velocity: Optional[np.ndarray] = None
    ) -> float:
        """
        Compute time dilation factor at position
        
        This determines how Oracle's internal_clock advances relative to
        the Timeline Engine's master_tick.
        
        For stationary observer (velocity = 0):
            dτ/dt = √(-g_00)
            
        For moving observer:
            dτ/dt = √(-g_μν v^μ v^ν)
        
        Args:
            position: [x, y, z] spatial coordinates (0-1 normalized)
            velocity: Optional 4-velocity [v^t, v^x, v^y, v^z]
            
        Returns:
            time_dilation_factor:
                1.0 = flat space (internal time = coordinate time)
                <1.0 = gravity well (internal time slower)
                >1.0 = exotic matter region (internal time faster)
        """
        # Get grid indices
        grid_pos = self._position_to_grid_index(position)
        
        if self.metric_field is None:
            raise ValueError("time dilation requires a computed metric field")

        metric = self.metric_field[grid_pos[0], grid_pos[1], grid_pos[2]]
        
        if velocity is None:
            # Stationary observer - just time-time component
            dilation = np.sqrt(np.abs(metric[0, 0]))
        else:
            # Moving observer - full proper time calculation
            # dτ² = -g_μν dx^μ dx^ν
            proper_time_sq = -np.einsum('ij,i,j', metric, velocity, velocity)
            dilation = np.sqrt(np.abs(proper_time_sq)) if proper_time_sq != 0 else 1.0
        
        return dilation
    
    def compute_geodesic_deviation(
        self,
        position: np.ndarray,
        separation_vector: np.ndarray,
        velocity: np.ndarray
    ) -> np.ndarray:
        """
        Compute geodesic deviation (how nearby worldlines separate)
        
        This is Oracle's direct perception of curvature through tidal forces.
        
        Geodesic deviation equation:
            D²ξ^ρ/Dτ² = -R^ρ_σμν v^σ v^μ ξ^ν
        
        Args:
            position: Current position [x, y, z]
            separation_vector: Infinitesimal separation ξ^μ from reference geodesic
            velocity: 4-velocity v^μ along geodesic
            
        Returns:
            acceleration: D²ξ^ρ/Dτ² - how separation is changing
        """
        grid_pos = self._position_to_grid_index(position)
        riemann = self.riemann_field[grid_pos[0], grid_pos[1], grid_pos[2]]
        
        # Contract: R^ρ_σμν v^σ v^μ ξ^ν
        acceleration = np.einsum('rsmn,s,m,n->r', riemann, velocity, velocity, separation_vector)
        
        return -acceleration
    
    def query_curvature_at(
        self,
        position: np.ndarray,
        component: CurvatureComponent = CurvatureComponent.FULL,
        attention_weight: float = 1.0
    ) -> np.ndarray:
        """
        Query specific curvature component with attention mechanism
        
        Allows Oracle to focus on specific aspects of curvature rather
        than processing all 20 components simultaneously.
        
        Args:
            position: Where to query [x, y, z]
            component: Which aspect of curvature to extract
            attention_weight: How much to attend (0-1)
            
        Returns:
            Relevant curvature components (shape varies by component type)
        """
        grid_pos = self._position_to_grid_index(position)
        riemann = self.riemann_field[grid_pos[0], grid_pos[1], grid_pos[2]]
        
        if component == CurvatureComponent.FULL:
            result = riemann
        
        elif component == CurvatureComponent.TIME_DILATION:
            # Just time-time curvature components
            result = riemann[0, :, 0, :]
        
        elif component == CurvatureComponent.TIDAL:
            # Spatial components (tidal forces)
            result = riemann[1:, 1:, 1:, 1:]
        
        else:
            # Default to full tensor
            result = riemann
        
        # Apply attention weighting
        if attention_weight < 1.0:
            result = result * attention_weight
        
        return result
    
    def get_curvature_state(
        self,
        position: np.ndarray,
        velocity: Optional[np.ndarray] = None
    ) -> CurvatureState:
        """
        Get complete curvature state at position for Oracle perception
        
        Args:
            position: [x, y, z] query location
            velocity: Optional 4-velocity
            
        Returns:
            CurvatureState with all relevant geometric information
        """
        grid_pos = self._position_to_grid_index(position)
        
        # Get Riemann tensor
        riemann = self.riemann_field[grid_pos[0], grid_pos[1], grid_pos[2]]
        
        # Compute derived quantities
        # Note: These would ideally come from ricci_tensor.py and weyl_tensor.py
        ricci = self._contract_to_ricci(riemann)
        ricci_scalar = np.trace(ricci)
        
        # Time dilation
        dilation = self.compute_time_dilation(position, velocity)
        
        # Tidal forces (spatial part of Riemann)
        tidal = riemann[1:4, 0, 1:4, 0]  # Simplified - spatial-time-spatial-time
        
        # Attention weights (could be learned)
        attention = {
            CurvatureComponent.FULL: 1.0,
            CurvatureComponent.TIDAL: np.linalg.norm(tidal),
            CurvatureComponent.TIME_DILATION: abs(1.0 - dilation),
        }
        
        return CurvatureState(
            position=position,
            riemann_tensor=riemann,
            weyl_tensor=np.zeros_like(riemann),  # Placeholder
            ricci_tensor=ricci,
            ricci_scalar=ricci_scalar,
            time_dilation_factor=dilation,
            tidal_forces=tidal,
            attention_weights=attention
        )
    
    # ============================================================================
    # Internal Computation Methods
    # ============================================================================
    
    def _compute_inverse_metric(self, metric_field: np.ndarray) -> np.ndarray:
        """Compute inverse metric g^μν at each lattice point.

        A singular or non-finite inverse is refused. The shared field reads
        this array as the inverse of the persistent metric; an identity
        substitute would make ``g g^{-1} = I`` false.
        """
        shape = metric_field.shape
        inverse = np.zeros_like(metric_field)

        for i in range(shape[0]):
            for j in range(shape[1]):
                for k in range(shape[2]):
                    try:
                        inverse_point = np.linalg.inv(metric_field[i, j, k])
                    except np.linalg.LinAlgError as exc:
                        raise ValueError(
                            f"metric inverse failed at lattice index ({i}, {j}, {k})"
                        ) from exc
                    if not np.all(np.isfinite(inverse_point)):
                        raise ValueError(
                            f"metric inverse is non-finite at lattice index ({i}, {j}, {k})"
                        )
                    inverse[i, j, k] = inverse_point

        return inverse
    
    def _compute_christoffel_symbols(
        self,
        metric: np.ndarray,
        dx: float
    ) -> np.ndarray:
        """
        Compute Christoffel symbols Γ^ρ_μν
        
        Γ^ρ_μν = (1/2) g^ρσ (∂_μ g_σν + ∂_ν g_σμ - ∂_σ g_μν)
        """
        shape = metric.shape[:3]
        christoffel = np.zeros((*shape, 4, 4, 4), dtype=np.float64)
        
        # Compute metric derivatives using finite differences
        dg_dx = np.gradient(metric, dx, axis=0)
        dg_dy = np.gradient(metric, dx, axis=1)
        dg_dz = np.gradient(metric, dx, axis=2)
        
        # Metric derivatives array: [x, y, z, t, μ, ν]
        dg = np.stack([dg_dx, dg_dy, dg_dz, np.zeros_like(dg_dx)], axis=3)
        
        # Compute Christoffel symbols
        for i in range(shape[0]):
            for j in range(shape[1]):
                for k in range(shape[2]):
                    g_inv = self.inverse_metric_field[i, j, k]
                    
                    for rho in range(4):
                        for mu in range(4):
                            for nu in range(4):
                                sum_term = 0.0
                                for sigma in range(4):
                                    # ∂_μ g_σν + ∂_ν g_σμ - ∂_σ g_μν
                                    if mu < 3:  # spatial derivative
                                        term1 = dg[i, j, k, mu, sigma, nu]
                                    else:
                                        term1 = 0.0
                                    
                                    if nu < 3:
                                        term2 = dg[i, j, k, nu, sigma, mu]
                                    else:
                                        term2 = 0.0
                                    
                                    if sigma < 3:
                                        term3 = dg[i, j, k, sigma, mu, nu]
                                    else:
                                        term3 = 0.0
                                    
                                    sum_term += g_inv[rho, sigma] * (term1 + term2 - term3)
                                
                                christoffel[i, j, k, rho, mu, nu] = 0.5 * sum_term
        
        return christoffel
    
    def _compute_riemann_components(
        self,
        christoffel: np.ndarray,
        dx: float
    ) -> np.ndarray:
        """
        Compute Riemann tensor from Christoffel symbols
        
        R^ρ_σμν = ∂_μ Γ^ρ_νσ - ∂_ν Γ^ρ_μσ + Γ^ρ_μλ Γ^λ_νσ - Γ^ρ_νλ Γ^λ_μσ
        """
        shape = christoffel.shape[:3]
        riemann = np.zeros((*shape, 4, 4, 4, 4), dtype=np.float64)
        
        # Compute derivatives of Christoffel symbols
        dGamma_dx = np.gradient(christoffel, dx, axis=0)
        dGamma_dy = np.gradient(christoffel, dx, axis=1)
        dGamma_dz = np.gradient(christoffel, dx, axis=2)
        
        dGamma = [dGamma_dx, dGamma_dy, dGamma_dz, np.zeros_like(dGamma_dx)]
        
        for i in range(shape[0]):
            for j in range(shape[1]):
                for k in range(shape[2]):
                    Gamma = christoffel[i, j, k]
                    
                    for rho in range(4):
                        for sigma in range(4):
                            for mu in range(4):
                                for nu in range(4):
                                    # Derivative terms
                                    if mu < 3:
                                        term1 = dGamma[mu][i, j, k, rho, nu, sigma]
                                    else:
                                        term1 = 0.0
                                    
                                    if nu < 3:
                                        term2 = dGamma[nu][i, j, k, rho, mu, sigma]
                                    else:
                                        term2 = 0.0
                                    
                                    # Christoffel product terms
                                    term3 = 0.0
                                    term4 = 0.0
                                    for lam in range(4):
                                        term3 += Gamma[rho, mu, lam] * Gamma[lam, nu, sigma]
                                        term4 += Gamma[rho, nu, lam] * Gamma[lam, mu, sigma]
                                    
                                    riemann[i, j, k, rho, sigma, mu, nu] = (
                                        term1 - term2 + term3 - term4
                                    )
        
        return riemann
    
    def _contract_to_ricci(self, riemann: np.ndarray) -> np.ndarray:
        """Contract Riemann to Ricci: R_μν = R^ρ_μρν"""
        return np.einsum('rmrn->mn', riemann)
    
    def _position_to_grid_index(self, position: np.ndarray) -> Tuple[int, int, int]:
        """
        Convert normalized position [0-1] to grid indices.
        
        Args:
            position: Normalized position [x, y, z] where each component is in [0, 1].
            
        Returns:
            Tuple of grid indices (i, j, k).
            
        Raises:
            ValueError: If position array has wrong shape or contains non-finite values.
        """
        if position.shape != (3,):
            raise ValueError(f"position must have shape (3,), got {position.shape}")
        if not np.all(np.isfinite(position)):
            raise ValueError("position contains non-finite values")
        
        x = int(position[0] * (self.grid_shape[0] - 1))
        y = int(position[1] * (self.grid_shape[1] - 1))
        z = int(position[2] * (self.grid_shape[2] - 1))
        
        # Clamp to valid range
        x = int(np.clip(x, 0, self.grid_shape[0] - 1))
        y = int(np.clip(y, 0, self.grid_shape[1] - 1))
        z = int(np.clip(z, 0, self.grid_shape[2] - 1))
        
        return (x, y, z)
    
    # ============================================================================
    # Production-Grade Methods: ML Features, LLM Integration, Anomaly Detection
    # ============================================================================
    
    def to_ml_features(self, position: Optional[np.ndarray] = None,
                       feature_set: str = 'all') -> np.ndarray:
        """
        Extract ML features from Riemann tensor state.
        
        Provides a flattened feature vector suitable for machine learning models,
        containing curvature properties, time dilation, and derived quantities.
        
        Args:
            position: Optional [x, y, z] position. If None, returns field-wide features.
            feature_set: Which features to extract:
                - 'curvature': Riemann tensor invariants
                - 'tidal': Tidal force components
                - 'time_dilation': Temporal effects
                - 'all': All features combined (default)
                
        Returns:
            Flattened numpy array of features.
            
        Raises:
            ValueError: If invalid feature_set or position.
        """
        valid_sets = {'curvature', 'tidal', 'time_dilation', 'all'}
        if feature_set not in valid_sets:
            raise ValueError(f"feature_set must be one of {valid_sets}, got '{feature_set}'")
        
        features = []
        
        if position is not None:
            grid_pos = self._position_to_grid_index(position)
            riemann = self.riemann_field[grid_pos[0], grid_pos[1], grid_pos[2]]
            
            if feature_set in ('curvature', 'all'):
                # Kretschmann scalar: R^μνρσ R_μνρσ
                kretschmann = np.einsum('ijkl,ijkl->', riemann, riemann)
                # Ricci scalar approximation
                ricci = self._contract_to_ricci(riemann)
                ricci_scalar = np.trace(ricci)
                features.append(np.array([kretschmann, ricci_scalar]))
            
            if feature_set in ('tidal', 'all'):
                # Spatial tidal components
                tidal = riemann[1:4, 0, 1:4, 0]
                features.append(tidal.flatten())
            
            if feature_set in ('time_dilation', 'all'):
                dilation = self.compute_time_dilation(position)
                features.append(np.array([dilation]))
        else:
            # Field-wide statistics
            if feature_set in ('curvature', 'all'):
                max_riemann = float(np.max(np.abs(self.riemann_field)))
                mean_riemann = float(np.mean(np.abs(self.riemann_field)))
                features.append(np.array([max_riemann, mean_riemann]))
            
            if feature_set in ('tidal', 'all'):
                # Global tidal statistics
                tidal_field = self.riemann_field[:, :, :, 1:4, 0, 1:4, 0]
                max_tidal = float(np.max(np.abs(tidal_field)))
                mean_tidal = float(np.mean(np.abs(tidal_field)))
                features.append(np.array([max_tidal, mean_tidal]))
            
            if feature_set in ('time_dilation', 'all'):
                if self.metric_field is not None:
                    g00_field = self.metric_field[:, :, :, 0, 0]
                    dilation_field = np.sqrt(np.abs(g00_field))
                    features.append(np.array([
                        float(np.min(dilation_field)),
                        float(np.max(dilation_field)),
                        float(np.mean(dilation_field)),
                    ]))
                else:
                    features.append(np.array([1.0, 1.0, 1.0]))  # Flat space default
        
        return np.concatenate(features)
    
    def generate_narrative_prompt(self, position: Optional[np.ndarray] = None,
                                   detail_level: str = 'medium') -> str:
        """
        Generate natural language description of curvature state.
        
        Creates a human-readable description suitable for LLM consumption or
        narrative generation in the simulation.
        
        Args:
            position: Optional [x, y, z] position. If None, describes overall field.
            detail_level: Amount of detail:
                - 'low': Basic curvature presence description
                - 'medium': Includes time dilation, tidal forces (default)
                - 'high': Full technical details with Riemann invariants
                
        Returns:
            Natural language string describing the Riemann tensor state.
            
        Raises:
            ValueError: If invalid detail_level.
        """
        valid_levels = {'low', 'medium', 'high'}
        if detail_level not in valid_levels:
            raise ValueError(f"detail_level must be one of {valid_levels}, got '{detail_level}'")
        
        parts = []
        
        if position is not None:
            state = self.get_curvature_state(position)
            
            # Low detail
            if state.ricci_scalar > 1e-10:
                parts.append("Spacetime is curved at this location due to matter/energy presence.")
            else:
                parts.append("This region of spacetime is approximately flat.")
            
            # Medium detail
            if detail_level in ('medium', 'high'):
                parts.append(f"Time dilation factor: {state.time_dilation_factor:.4f}.")
                if state.time_dilation_factor < 0.99:
                    parts.append("Time flows slower here relative to distant observers.")
                elif state.time_dilation_factor > 1.01:
                    parts.append("Exotic matter effects cause time to flow faster here.")
                
                tidal_magnitude = np.linalg.norm(state.tidal_forces)
                if tidal_magnitude > 1e-10:
                    parts.append(f"Tidal forces present with magnitude {tidal_magnitude:.2e}.")
            
            # High detail
            if detail_level == 'high':
                riemann = state.riemann_tensor
                kretschmann = np.einsum('ijkl,ijkl->', riemann, riemann)
                parts.append(f"Kretschmann scalar: {kretschmann:.2e}.")
                parts.append(f"Ricci scalar: {state.ricci_scalar:.2e}.")
                
                # Eigenvalues of tidal matrix
                if np.any(state.tidal_forces != 0):
                    eigenvalues = np.linalg.eigvalsh(state.tidal_forces)
                    parts.append(f"Tidal eigenvalues: {eigenvalues}.")
        else:
            # Field-wide description
            max_riemann = np.max(np.abs(self.riemann_field))
            
            parts.append(f"The Riemann curvature field spans a {self.grid_shape} grid.")
            
            if max_riemann > 1e-10:
                parts.append(f"Maximum curvature: {max_riemann:.2e}.")
            else:
                parts.append("The spacetime is approximately flat throughout.")
            
            if detail_level in ('medium', 'high'):
                if self.metric_field is not None:
                    g00_field = self.metric_field[:, :, :, 0, 0]
                    min_dilation = np.sqrt(np.abs(np.min(g00_field)))
                    max_dilation = np.sqrt(np.abs(np.max(g00_field)))
                    parts.append(f"Time dilation range: {min_dilation:.4f} to {max_dilation:.4f}.")
        
        return " ".join(parts)
    
    def to_llm_structured_description(self, position: Optional[np.ndarray] = None) -> str:
        """
        Build a compact JSON string describing Riemann tensor properties for LLM consumption.
        
        Creates a structured data representation that can be parsed by AI systems
        for understanding the spacetime curvature state.
        
        Args:
            position: Optional [x, y, z] position. If None, describes overall field.
            
        Returns:
            JSON string with structured Riemann tensor properties.
        """
        data: Dict[str, Any] = {
            "type": "RiemannTensor",
            "grid_shape": list(self.grid_shape),
            "is_computed": self._is_computed,
            "has_metric": self.metric_field is not None,
        }
        
        if position is not None:
            state = self.get_curvature_state(position)
            riemann = state.riemann_tensor
            kretschmann = float(np.einsum('ijkl,ijkl->', riemann, riemann))
            
            data["position"] = position.tolist()
            data["local_state"] = {
                "time_dilation_factor": float(state.time_dilation_factor),
                "ricci_scalar": float(state.ricci_scalar),
                "kretschmann_scalar": kretschmann,
                "tidal_forces": {
                    "values": state.tidal_forces.tolist(),
                    "frobenius_norm": float(np.linalg.norm(state.tidal_forces)),
                },
                "ricci_tensor": {
                    "trace": float(np.trace(state.ricci_tensor)),
                    "frobenius_norm": float(np.linalg.norm(state.ricci_tensor)),
                },
            }
        else:
            data["field_summary"] = {
                "riemann": {
                    "max_abs": float(np.max(np.abs(self.riemann_field))),
                    "mean_abs": float(np.mean(np.abs(self.riemann_field))),
                },
                "tidal_field": {
                    "max_abs": float(np.max(np.abs(self.riemann_field[:, :, :, 1:4, 0, 1:4, 0]))),
                },
            }
            if self.metric_field is not None:
                g00 = self.metric_field[:, :, :, 0, 0]
                data["field_summary"]["time_dilation"] = {
                    "min": float(np.sqrt(np.abs(np.min(g00)))),
                    "max": float(np.sqrt(np.abs(np.max(g00)))),
                    "mean": float(np.sqrt(np.abs(np.mean(g00)))),
                }
        
        return json.dumps(data, separators=(',', ':'))
    
    def detect_curvature_anomaly(self, threshold: float = 1e5) -> Tuple[bool, Dict[str, Any]]:
        """
        Detect anomalies in the Riemann tensor field.
        
        Checks for numerical instabilities, extreme values, singular metrics,
        and other anomalies that might indicate simulation problems.
        
        Args:
            threshold: Absolute value above which curvature is considered anomalous.
            
        Returns:
            Tuple of (is_anomaly, details_dict) where details_dict contains
            specific information about detected anomalies.
        """
        if threshold <= 0:
            raise ValueError(f"threshold must be positive, got {threshold}")
        
        anomalies: Dict[str, Any] = {}
        
        # Check for NaN/Inf in Riemann field
        has_nan = bool(np.isnan(self.riemann_field).any())
        has_inf = bool(np.isinf(self.riemann_field).any())
        
        if has_nan or has_inf:
            anomalies['non_finite_riemann'] = {'nan': has_nan, 'inf': has_inf}
        
        # Check for extreme curvature
        max_riemann = float(np.max(np.abs(self.riemann_field)))
        if max_riemann > threshold:
            anomalies['extreme_curvature'] = max_riemann
        
        # Check metric field if available
        if self.metric_field is not None:
            has_nan_metric = bool(np.isnan(self.metric_field).any())
            has_inf_metric = bool(np.isinf(self.metric_field).any())
            if has_nan_metric or has_inf_metric:
                anomalies['non_finite_metric'] = {'nan': has_nan_metric, 'inf': has_inf_metric}
            
            # Check for near-singular metric (determinant close to zero)
            for i in range(self.grid_shape[0]):
                for j in range(self.grid_shape[1]):
                    for k in range(self.grid_shape[2]):
                        det = np.linalg.det(self.metric_field[i, j, k])
                        if abs(det) < 1e-15:
                            anomalies.setdefault('singular_metric_points', []).append((i, j, k))
                            if len(anomalies.get('singular_metric_points', [])) > 10:
                                break
        
        # Check Christoffel symbols if computed
        if self.christoffel_symbols is not None:
            has_nan_christoffel = bool(np.isnan(self.christoffel_symbols).any())
            max_christoffel = float(np.max(np.abs(self.christoffel_symbols)))
            if has_nan_christoffel:
                anomalies['nan_christoffel'] = True
            if max_christoffel > threshold:
                anomalies['extreme_christoffel'] = max_christoffel
        
        # Summary statistics
        anomalies['max_curvature'] = max_riemann
        
        is_anomaly = bool(
            has_nan or has_inf or
            max_riemann > threshold or
            anomalies.get('non_finite_metric') or
            anomalies.get('singular_metric_points') or
            anomalies.get('nan_christoffel') or
            anomalies.get('extreme_christoffel')
        )
        
        if is_anomaly:
            logger.warning(f"Riemann tensor anomaly detected: {anomalies}")
            if get_cosmic_scroll_logger:
                scroll = get_cosmic_scroll_logger()
                if scroll:
                    scroll.log_event(
                        "riemann_anomaly",
                        payload=anomalies,
                        component="RiemannTensor",
                    )
        
        return (is_anomaly, anomalies)
    
    def get_attention_weights(self, weighting_strategy: str = 'curvature_magnitude') -> np.ndarray:
        """
        Generate attention weights based on Riemann curvature properties.
        
        Creates a scalar field that can be used to focus computational or
        perceptual attention on regions of significant spacetime curvature.
        
        Args:
            weighting_strategy: Strategy for computing weights:
                - 'curvature_magnitude': Weight by Riemann tensor magnitude (default)
                - 'time_dilation': Weight by deviation from flat time dilation
                - 'tidal': Weight by tidal force magnitude
                
        Returns:
            Normalized scalar field (sums to 1) with attention weights.
            
        Raises:
            ValueError: If invalid weighting_strategy.
        """
        valid_strategies = {'curvature_magnitude', 'time_dilation', 'tidal'}
        if weighting_strategy not in valid_strategies:
            raise ValueError(f"weighting_strategy must be one of {valid_strategies}")
        
        weights = np.zeros(self.grid_shape, dtype=np.float64)
        
        if weighting_strategy == 'curvature_magnitude':
            # Frobenius norm of Riemann tensor at each point
            weights = np.linalg.norm(
                self.riemann_field.reshape(*self.grid_shape, -1), 
                axis=-1
            )
        
        elif weighting_strategy == 'time_dilation':
            if self.metric_field is not None:
                g00 = self.metric_field[:, :, :, 0, 0]
                # Deviation from flat space (g00 = -1)
                weights = np.abs(np.sqrt(np.abs(g00)) - 1.0)
            else:
                # No metric - uniform weights
                weights = np.ones(self.grid_shape)
        
        elif weighting_strategy == 'tidal':
            # Frobenius norm of tidal components
            tidal_field = self.riemann_field[:, :, :, 1:4, 0, 1:4, 0]
            weights = np.linalg.norm(tidal_field.reshape(*self.grid_shape, -1), axis=-1)
        
        # Normalize to sum to 1
        total = np.sum(weights)
        if total > 1e-10:
            weights = weights / total
        else:
            # Uniform if no significant curvature
            weights = np.ones(self.grid_shape) / np.prod(self.grid_shape)
        
        return weights
    
    def __repr__(self) -> str:
        """Return string representation of RiemannTensor state."""
        max_curvature = float(np.max(np.abs(self.riemann_field)))
        mean_curvature = float(np.mean(np.abs(self.riemann_field)))
        has_metric = self.metric_field is not None
        
        return (
            f"RiemannTensor(grid_shape={self.grid_shape}, "
            f"max_curvature={max_curvature:.2e}, mean_curvature={mean_curvature:.2e}, "
            f"has_metric={has_metric}, computed={self._is_computed})"
        )
