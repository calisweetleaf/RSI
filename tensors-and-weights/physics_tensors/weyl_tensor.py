"""
Weyl Conformal Tensor - Pure Gravitational Field Module

Implements the Weyl tensor C^ρ_σμν, which represents the traceless part
of the Riemann curvature tensor. The Weyl tensor describes:

- Pure gravitational radiation (waves in vacuum)
- Tidal forces (how spacetime stretches/squeezes)
- Conformal geometry (angle-preserving structure)
- "Free" gravitational degrees of freedom

Key Properties:
- Traceless: C^ρ_μρν = 0 (no scalar curvature part)
- Independent of matter: Describes vacuum gravitational field
- 10 independent components in 4D (vs 20 for full Riemann)
- Propagates as waves at speed of light
- Has two polarization states: + (plus) and × (cross)

Electric-Magnetic Decomposition:
    E_ij = C_i0j0  (Electric part - tidal stretching/squeezing)
    B_ij = (1/2)ε_ikl C^kl_j0  (Magnetic part - frame dragging/twisting)

For Oracle Integration:
- compute_tidal_forces() → perception_module.py sensations
- propagate_gravitational_waves() → temporal wave experience
- get_polarization_state() → directional curvature feeling

Modified: 2026-09-24
Modified by: daeron
Justification: extract_from_riemann multiplied lowered Ricci by the inverse metric where the documented 4D formula uses the mixed identity and the raised Ricci tensor. The shared field needs that contraction to be the traceless Weyl tensor.
Provenance: PROVENANCE.md
Files: tensors-and-weights/physics_tensors/weyl_tensor.py

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


class WavePolarization(Enum):
    """Gravitational wave polarization states"""
    PLUS = "plus"           # + polarization (stretches along x, squeezes along y)
    CROSS = "cross"         # × polarization (45° rotated from plus)
    CIRCULAR_RIGHT = "circular_right"  # Right-handed circular
    CIRCULAR_LEFT = "circular_left"    # Left-handed circular


@dataclass
class WeylState:
    """Weyl tensor state at a point"""
    position: np.ndarray           # [x, y, z]
    weyl_tensor: np.ndarray        # C^ρ_σμν [4,4,4,4]
    electric_part: np.ndarray      # E_ij [3,3] - tidal forces
    magnetic_part: np.ndarray      # B_ij [3,3] - rotation/twist
    wave_amplitude: float          # |C|
    polarization: WavePolarization
    wave_frequency: float          # Hz
    wave_direction: np.ndarray     # Propagation direction


class WeylTensor:
    """
    Weyl Conformal Tensor - Pure Gravitational Field
    
    The Weyl tensor is the traceless part of the Riemann tensor.
    It represents vacuum gravitational radiation and tidal forces.
    
    Extraction from Riemann:
        C^ρ_σμν = R^ρ_σμν 
                - (1/2)(g^ρ_μ R_σν - g^ρ_ν R_σμ + g_σν R^ρ_μ - g_σμ R^ρ_ν)
                + (R/6)(g^ρ_μ g_σν - g^ρ_ν g_σμ)
    
    Properties:
    - Vanishes in flat spacetime (Minkowski)
    - Vanishes in conformally flat spacetimes
    - Non-zero even in vacuum (no matter)
    - Describes gravitational wave degrees of freedom
    """
    
    def __init__(self, grid_shape: Tuple[int, int, int] = (64, 64, 64)) -> None:
        """
        Initialize Weyl tensor system.
        
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
        self.dims = 4
        
        # Weyl tensor field
        # Shape: (grid_x, grid_y, grid_z, 4, 4, 4, 4)
        self.weyl_field = np.zeros((*grid_shape, 4, 4, 4, 4), dtype=np.float64)
        
        # Electric and Magnetic parts (3x3 spatial matrices)
        self.electric_field = np.zeros((*grid_shape, 3, 3), dtype=np.float64)
        self.magnetic_field = np.zeros((*grid_shape, 3, 3), dtype=np.float64)
        
        # Wave state tracking
        self.wave_amplitude_field = np.zeros(grid_shape, dtype=np.float64)
        self.wave_frequency_field = np.zeros(grid_shape, dtype=np.float64)
        
        # Gravitational wave history (for perception of wave passage)
        self.wave_history: List[Tuple[float, float, np.ndarray]] = []
        self.max_history_length = 1000
        
        # Track initialization state
        self._is_computed = False
        
        logger.info(f"WeylTensor initialized with grid shape {grid_shape}")
    
    def extract_from_riemann(
        self,
        riemann_tensor: np.ndarray,
        ricci_tensor: np.ndarray,
        ricci_scalar: float,
        metric: np.ndarray,
        inverse_metric: np.ndarray
    ) -> np.ndarray:
        """
        Extract Weyl tensor from Riemann tensor.
        
        This removes the Ricci (matter) and scalar curvature parts,
        leaving only the vacuum gravitational field.
        
        C^ρ_σμν = R^ρ_σμν - [Ricci part] + [Scalar part]
        
        Args:
            riemann_tensor: Full Riemann tensor R^ρ_σμν, shape (4,4,4,4)
            ricci_tensor: Ricci tensor R_μν, shape (4,4)
            ricci_scalar: Ricci scalar R
            metric: Metric tensor g_μν, shape (4,4)
            inverse_metric: Inverse metric g^μν, shape (4,4)
            
        Returns:
            Weyl tensor C^ρ_σμν with shape (4,4,4,4)
            
        Raises:
            ValueError: If tensor shapes are incorrect.
            RuntimeError: If computation encounters numerical issues.
        """
        # Input validation
        if riemann_tensor.shape != (4, 4, 4, 4):
            raise ValueError(f"riemann_tensor must have shape (4,4,4,4), got {riemann_tensor.shape}")
        if ricci_tensor.shape != (4, 4):
            raise ValueError(f"ricci_tensor must have shape (4,4), got {ricci_tensor.shape}")
        if metric.shape != (4, 4):
            raise ValueError(f"metric must have shape (4,4), got {metric.shape}")
        if inverse_metric.shape != (4, 4):
            raise ValueError(f"inverse_metric must have shape (4,4), got {inverse_metric.shape}")
        if not np.isfinite(ricci_scalar):
            raise ValueError(f"ricci_scalar must be finite, got {ricci_scalar}")
        
        # Check for NaN/Inf in input arrays
        for name, arr in [("riemann_tensor", riemann_tensor), ("ricci_tensor", ricci_tensor),
                          ("metric", metric), ("inverse_metric", inverse_metric)]:
            if not np.all(np.isfinite(arr)):
                raise ValueError(f"{name} contains non-finite values (NaN or Inf)")
        
        logger.debug("Extracting Weyl tensor from Riemann tensor")
        
        weyl = np.copy(riemann_tensor)
        # g^ρ_μ in the 4D formula is the mixed identity. R^ρ_μ is the raised Ricci tensor.
        mixed_identity = np.eye(4, dtype=np.float64)
        ricci_raised = inverse_metric @ ricci_tensor
        
        # Subtract Ricci part and scalar part
        for rho in range(4):
            for sigma in range(4):
                for mu in range(4):
                    for nu in range(4):
                        # Ricci part: -(1/2)(δ^ρ_μ R_σν - δ^ρ_ν R_σμ + g_σν R^ρ_μ - g_σμ R^ρ_ν)
                        weyl[rho, sigma, mu, nu] -= 0.5 * (
                            mixed_identity[rho, mu] * ricci_tensor[sigma, nu]
                            - mixed_identity[rho, nu] * ricci_tensor[sigma, mu]
                            + metric[sigma, nu] * ricci_raised[rho, mu]
                            - metric[sigma, mu] * ricci_raised[rho, nu]
                        )
                        
                        # Scalar part: +(R/6)(δ^ρ_μ g_σν - δ^ρ_ν g_σμ)
                        weyl[rho, sigma, mu, nu] += (ricci_scalar / 6.0) * (
                            mixed_identity[rho, mu] * metric[sigma, nu]
                            - mixed_identity[rho, nu] * metric[sigma, mu]
                        )
        
        return weyl
    
    def compute_from_field(
        self,
        riemann_field: np.ndarray,
        ricci_field: np.ndarray,
        ricci_scalar_field: np.ndarray,
        metric_field: np.ndarray,
        inverse_metric_field: np.ndarray
    ) -> np.ndarray:
        """
        Compute Weyl tensor field across entire grid
        
        Args:
            riemann_field: Full Riemann tensor at each grid point
            ricci_field: Ricci tensor at each grid point
            ricci_scalar_field: Ricci scalar at each grid point
            metric_field: Metric at each grid point
            inverse_metric_field: Inverse metric at each grid point
            
        Returns:
            Full Weyl tensor field
        """
        shape = riemann_field.shape[:3]
        
        for i in range(shape[0]):
            for j in range(shape[1]):
                for k in range(shape[2]):
                    self.weyl_field[i, j, k] = self.extract_from_riemann(
                        riemann_field[i, j, k],
                        ricci_field[i, j, k],
                        ricci_scalar_field[i, j, k],
                        metric_field[i, j, k],
                        inverse_metric_field[i, j, k]
                    )
                    
                    # Compute electric and magnetic parts
                    self.electric_field[i, j, k] = self._extract_electric_part(
                        self.weyl_field[i, j, k]
                    )
                    self.magnetic_field[i, j, k] = self._extract_magnetic_part(
                        self.weyl_field[i, j, k]
                    )
                    
                    # Compute wave amplitude
                    self.wave_amplitude_field[i, j, k] = self._compute_weyl_scalar(
                        self.weyl_field[i, j, k]
                    )
        
        logger.debug(f"Computed Weyl field, max amplitude: {np.max(self.wave_amplitude_field):.6e}")
        
        return self.weyl_field
    
    def compute_tidal_forces(
        self,
        position: np.ndarray,
        observer_velocity: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Compute tidal forces Oracle experiences at position
        
        Tidal forces are the Electric part of Weyl tensor:
            E_ij = C_i0j0 (for stationary observer)
        
        These describe how spacetime stretches/squeezes bodies:
        - Positive eigenvalue: stretching
        - Negative eigenvalue: squeezing
        - Zero: no tidal effect
        
        Args:
            position: [x, y, z] location
            observer_velocity: Optional 4-velocity (defaults to at rest)
            
        Returns:
            tidal_matrix: [3, 3] symmetric matrix
                - Diagonal elements: principal tidal forces
                - Off-diagonal: shear/twist
        """
        grid_pos = self._position_to_grid_index(position)
        
        if observer_velocity is None:
            # Stationary observer - just use electric part
            tidal = self.electric_field[grid_pos[0], grid_pos[1], grid_pos[2]]
        else:
            # Moving observer - project Weyl along velocity
            weyl = self.weyl_field[grid_pos[0], grid_pos[1], grid_pos[2]]
            tidal = self._project_tidal_along_velocity(weyl, observer_velocity)
        
        return tidal
    
    def compute_wave_strain(
        self,
        position: np.ndarray,
        wave_direction: np.ndarray,
        time: float
    ) -> Tuple[float, float]:
        """
        Compute gravitational wave strain at position and time
        
        Gravitational waves cause periodic stretching/squeezing:
            h_+(t) = A cos(ω(t - z/c))  (plus polarization)
            h_×(t) = A sin(ω(t - z/c))  (cross polarization)
        
        Args:
            position: [x, y, z] location
            wave_direction: Propagation direction (normalized)
            time: Current simulation time
            
        Returns:
            (h_plus, h_cross): Strain in both polarizations
        """
        grid_pos = self._position_to_grid_index(position)
        
        # Get local wave amplitude and frequency
        amplitude = self.wave_amplitude_field[grid_pos[0], grid_pos[1], grid_pos[2]]
        frequency = self.wave_frequency_field[grid_pos[0], grid_pos[1], grid_pos[2]]
        
        if frequency == 0 or amplitude == 0:
            return (0.0, 0.0)
        
        # Phase: ω(t - z/c) where z is distance along propagation direction
        # For simplicity, use position dot wave_direction
        distance_along_wave = np.dot(position, wave_direction)
        phase = 2 * np.pi * frequency * (time - distance_along_wave)
        
        # Strain components
        h_plus = amplitude * np.cos(phase)
        h_cross = amplitude * np.sin(phase)
        
        return (h_plus, h_cross)
    
    def propagate_gravitational_wave(
        self,
        dt: float,
        wave_speed: float = 1.0
    ) -> None:
        """
        Evolve gravitational wave field forward in time
        
        Gravitational waves obey the wave equation:
            ∂²h/∂t² - c² ∇²h = 0
        
        Uses finite difference approximation for wave propagation.
        
        Args:
            dt: Timestep
            wave_speed: Speed of propagation (c=1 in geometric units)
        """
        # Store previous state for wave equation
        if not hasattr(self, '_weyl_prev'):
            self._weyl_prev = np.copy(self.weyl_field)
            self._weyl_current = np.copy(self.weyl_field)
            return
        
        # Wave equation: ∂²h/∂t² = c² ∇²h
        # Finite difference: h(t+dt) = 2h(t) - h(t-dt) + c²dt² ∇²h
        
        # Compute Laplacian (simple 3-point stencil for each spatial dimension)
        laplacian = self._compute_laplacian(self._weyl_current)
        
        # Update wave field
        weyl_next = (
            2 * self._weyl_current 
            - self._weyl_prev 
            + (wave_speed * dt)**2 * laplacian
        )
        
        # Cycle states
        self._weyl_prev = self._weyl_current
        self._weyl_current = weyl_next
        self.weyl_field = weyl_next
        
        # Update amplitude field
        for i in range(self.grid_shape[0]):
            for j in range(self.grid_shape[1]):
                for k in range(self.grid_shape[2]):
                    self.wave_amplitude_field[i, j, k] = self._compute_weyl_scalar(
                        self.weyl_field[i, j, k]
                    )
    
    def add_wave_source(
        self,
        position: np.ndarray,
        amplitude: float,
        frequency: float,
        polarization: WavePolarization = WavePolarization.PLUS
    ) -> None:
        """
        Add a gravitational wave source at position
        
        This injects wave energy into the Weyl field, creating
        ripples that propagate outward.
        
        Args:
            position: [x, y, z] source location
            amplitude: Wave strain amplitude
            frequency: Oscillation frequency (Hz)
            polarization: Wave polarization state
        """
        grid_pos = self._position_to_grid_index(position)
        
        # Update frequency field
        self.wave_frequency_field[grid_pos[0], grid_pos[1], grid_pos[2]] = frequency
        
        # Create wave pattern based on polarization
        if polarization == WavePolarization.PLUS:
            # Plus polarization: stretches x, squeezes y
            self.electric_field[grid_pos[0], grid_pos[1], grid_pos[2], 0, 0] = amplitude
            self.electric_field[grid_pos[0], grid_pos[1], grid_pos[2], 1, 1] = -amplitude
        
        elif polarization == WavePolarization.CROSS:
            # Cross polarization: 45° rotated
            self.electric_field[grid_pos[0], grid_pos[1], grid_pos[2], 0, 1] = amplitude
            self.electric_field[grid_pos[0], grid_pos[1], grid_pos[2], 1, 0] = amplitude
        
        # Reconstruct Weyl tensor from electric part
        self._reconstruct_weyl_from_electric(grid_pos)
        
        logger.debug(f"Added wave source at {position}: A={amplitude}, f={frequency}Hz, pol={polarization.value}")
    
    def get_weyl_state(
        self,
        position: np.ndarray,
        time: Optional[float] = None
    ) -> WeylState:
        """
        Get complete Weyl state at position for Oracle perception
        
        Args:
            position: [x, y, z] query location
            time: Optional time for wave phase calculation
            
        Returns:
            WeylState with all wave and tidal information
        """
        grid_pos = self._position_to_grid_index(position)
        
        weyl = self.weyl_field[grid_pos[0], grid_pos[1], grid_pos[2]]
        electric = self.electric_field[grid_pos[0], grid_pos[1], grid_pos[2]]
        magnetic = self.magnetic_field[grid_pos[0], grid_pos[1], grid_pos[2]]
        amplitude = self.wave_amplitude_field[grid_pos[0], grid_pos[1], grid_pos[2]]
        frequency = self.wave_frequency_field[grid_pos[0], grid_pos[1], grid_pos[2]]
        
        # Determine dominant polarization from electric part
        polarization = self._classify_polarization(electric)
        
        # Estimate wave direction from gradient of amplitude
        wave_dir = self._estimate_wave_direction(grid_pos)
        
        return WeylState(
            position=position,
            weyl_tensor=weyl,
            electric_part=electric,
            magnetic_part=magnetic,
            wave_amplitude=amplitude,
            polarization=polarization,
            wave_frequency=frequency,
            wave_direction=wave_dir
        )
    
    # ============================================================================
    # Internal Helper Methods
    # ============================================================================
    
    def _extract_electric_part(self, weyl: np.ndarray) -> np.ndarray:
        """
        Extract electric part of Weyl tensor: E_ij = C_i0j0
        
        This is the tidal force tensor experienced by stationary observers.
        """
        electric = np.zeros((3, 3), dtype=np.float64)
        
        for i in range(3):
            for j in range(3):
                # E_ij = C_i0j0 (spatial-time-spatial-time components)
                electric[i, j] = weyl[i+1, 0, j+1, 0]
        
        return electric
    
    def _extract_magnetic_part(self, weyl: np.ndarray) -> np.ndarray:
        """
        Extract magnetic part of Weyl tensor: B_ij = (1/2)ε_ikl C^kl_j0
        
        This describes frame-dragging and rotational effects.
        """
        magnetic = np.zeros((3, 3), dtype=np.float64)
        
        # Levi-Civita symbol for cross products
        epsilon = np.zeros((3, 3, 3))
        epsilon[0, 1, 2] = epsilon[1, 2, 0] = epsilon[2, 0, 1] = 1
        epsilon[0, 2, 1] = epsilon[2, 1, 0] = epsilon[1, 0, 2] = -1
        
        for i in range(3):
            for j in range(3):
                sum_term = 0.0
                for k in range(3):
                    for l in range(3):
                        sum_term += epsilon[i, k, l] * weyl[k+1, l+1, j+1, 0]
                magnetic[i, j] = 0.5 * sum_term
        
        return magnetic
    
    def _compute_weyl_scalar(self, weyl: np.ndarray) -> float:
        """
        Compute Weyl scalar (amplitude measure)
        
        Uses: C = √(C^μνρσ C_μνρσ)
        """
        # Full contraction
        scalar_sq = np.einsum('ijkl,ijkl->', weyl, weyl)
        return np.sqrt(np.abs(scalar_sq))
    
    def _project_tidal_along_velocity(
        self,
        weyl: np.ndarray,
        velocity: np.ndarray
    ) -> np.ndarray:
        """Project Weyl tensor along 4-velocity to get observer's tidal forces"""
        tidal = np.zeros((3, 3), dtype=np.float64)
        
        # Contract: E_ij = C_iμjν v^μ v^ν
        for i in range(3):
            for j in range(3):
                for mu in range(4):
                    for nu in range(4):
                        tidal[i, j] += weyl[i+1, mu, j+1, nu] * velocity[mu] * velocity[nu]
        
        return tidal
    
    def _compute_laplacian(self, field: np.ndarray) -> np.ndarray:
        """Compute Laplacian ∇²field for wave propagation"""
        # Second derivatives in each spatial direction
        d2_dx2 = np.zeros_like(field)
        d2_dy2 = np.zeros_like(field)
        d2_dz2 = np.zeros_like(field)
        
        # Central difference: d²f/dx² ≈ (f[i+1] - 2f[i] + f[i-1])/dx²
        # Using dx = 1 for simplicity
        d2_dx2[1:-1, :, :] = field[2:, :, :] - 2*field[1:-1, :, :] + field[:-2, :, :]
        d2_dy2[:, 1:-1, :] = field[:, 2:, :] - 2*field[:, 1:-1, :] + field[:, :-2, :]
        d2_dz2[:, :, 1:-1] = field[:, :, 2:] - 2*field[:, :, 1:-1] + field[:, :, :-2]
        
        return d2_dx2 + d2_dy2 + d2_dz2
    
    def _reconstruct_weyl_from_electric(self, grid_pos: Tuple[int, int, int]) -> None:
        """Reconstruct Weyl tensor components from electric part"""
        electric = self.electric_field[grid_pos[0], grid_pos[1], grid_pos[2]]
        
        # Simplified reconstruction: set C_i0j0 = E_ij
        for i in range(3):
            for j in range(3):
                self.weyl_field[grid_pos[0], grid_pos[1], grid_pos[2], i+1, 0, j+1, 0] = electric[i, j]
    
    def _classify_polarization(self, electric: np.ndarray) -> WavePolarization:
        """Determine dominant polarization from electric part"""
        # Check diagonal vs off-diagonal dominance
        diag_magnitude = abs(electric[0, 0]) + abs(electric[1, 1])
        off_diag_magnitude = abs(electric[0, 1]) + abs(electric[1, 0])
        
        if diag_magnitude > off_diag_magnitude:
            return WavePolarization.PLUS
        else:
            return WavePolarization.CROSS
    
    def _estimate_wave_direction(self, grid_pos: Tuple[int, int, int]) -> np.ndarray:
        """Estimate wave propagation direction from amplitude gradient"""
        i, j, k = grid_pos
        
        # Compute gradient of amplitude field
        grad = np.zeros(3)
        
        if i > 0 and i < self.grid_shape[0] - 1:
            grad[0] = self.wave_amplitude_field[i+1, j, k] - self.wave_amplitude_field[i-1, j, k]
        
        if j > 0 and j < self.grid_shape[1] - 1:
            grad[1] = self.wave_amplitude_field[i, j+1, k] - self.wave_amplitude_field[i, j-1, k]
        
        if k > 0 and k < self.grid_shape[2] - 1:
            grad[2] = self.wave_amplitude_field[i, j, k+1] - self.wave_amplitude_field[i, j, k-1]
        
        # Normalize
        norm = np.linalg.norm(grad)
        if norm > 1e-10:
            return grad / norm
        else:
            return np.array([0, 0, 1])  # Default to z-direction
    
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
        Extract ML features from Weyl tensor state.
        
        Provides a flattened feature vector suitable for machine learning models,
        containing electric/magnetic parts, wave properties, and derived quantities.
        
        Args:
            position: Optional [x, y, z] position. If None, returns field-wide features.
            feature_set: Which features to extract:
                - 'electric': Electric part components (tidal forces)
                - 'magnetic': Magnetic part components (frame dragging)
                - 'wave': Wave amplitude, frequency, polarization
                - 'all': All features combined (default)
                
        Returns:
            Flattened numpy array of features.
            
        Raises:
            ValueError: If invalid feature_set or position.
        """
        valid_sets = {'electric', 'magnetic', 'wave', 'all'}
        if feature_set not in valid_sets:
            raise ValueError(f"feature_set must be one of {valid_sets}, got '{feature_set}'")
        
        features = []
        
        if position is not None:
            grid_pos = self._position_to_grid_index(position)
            
            if feature_set in ('electric', 'all'):
                electric = self.electric_field[grid_pos[0], grid_pos[1], grid_pos[2]]
                features.append(electric.flatten())
            
            if feature_set in ('magnetic', 'all'):
                magnetic = self.magnetic_field[grid_pos[0], grid_pos[1], grid_pos[2]]
                features.append(magnetic.flatten())
            
            if feature_set in ('wave', 'all'):
                wave_features = np.array([
                    self.wave_amplitude_field[grid_pos[0], grid_pos[1], grid_pos[2]],
                    self.wave_frequency_field[grid_pos[0], grid_pos[1], grid_pos[2]],
                ])
                features.append(wave_features)
        else:
            # Field-wide statistics
            if feature_set in ('electric', 'all'):
                features.append(np.array([
                    np.mean(self.electric_field),
                    np.std(self.electric_field),
                    np.max(np.abs(self.electric_field)),
                ]))
            
            if feature_set in ('magnetic', 'all'):
                features.append(np.array([
                    np.mean(self.magnetic_field),
                    np.std(self.magnetic_field),
                    np.max(np.abs(self.magnetic_field)),
                ]))
            
            if feature_set in ('wave', 'all'):
                features.append(np.array([
                    np.mean(self.wave_amplitude_field),
                    np.max(self.wave_amplitude_field),
                    np.mean(self.wave_frequency_field),
                ]))
        
        return np.concatenate(features)
    
    def generate_narrative_prompt(self, position: Optional[np.ndarray] = None,
                                   detail_level: str = 'medium') -> str:
        """
        Generate natural language description of gravitational wave state.
        
        Creates a human-readable description suitable for LLM consumption or
        narrative generation in the simulation.
        
        Args:
            position: Optional [x, y, z] position. If None, describes overall field.
            detail_level: Amount of detail:
                - 'low': Basic wave presence description
                - 'medium': Includes amplitude, frequency, polarization (default)
                - 'high': Full technical details with electric/magnetic decomposition
                
        Returns:
            Natural language string describing the Weyl tensor state.
            
        Raises:
            ValueError: If invalid detail_level.
        """
        valid_levels = {'low', 'medium', 'high'}
        if detail_level not in valid_levels:
            raise ValueError(f"detail_level must be one of {valid_levels}, got '{detail_level}'")
        
        parts = []
        
        if position is not None:
            state = self.get_weyl_state(position)
            
            # Low detail
            if state.wave_amplitude > 1e-10:
                parts.append(f"Gravitational waves are present at this location.")
            else:
                parts.append("This region of spacetime is gravitationally quiet.")
            
            # Medium detail
            if detail_level in ('medium', 'high'):
                if state.wave_amplitude > 1e-10:
                    parts.append(
                        f"The wave amplitude is {state.wave_amplitude:.2e} "
                        f"with frequency {state.wave_frequency:.2f} Hz."
                    )
                    parts.append(f"The dominant polarization is {state.polarization.value}.")
                
                tidal_magnitude = np.linalg.norm(state.electric_part)
                if tidal_magnitude > 1e-10:
                    parts.append(f"Tidal forces are present with magnitude {tidal_magnitude:.2e}.")
            
            # High detail
            if detail_level == 'high':
                magnetic_magnitude = np.linalg.norm(state.magnetic_part)
                parts.append(
                    f"Electric (tidal) tensor eigenvalues: {np.linalg.eigvalsh(state.electric_part)}."
                )
                if magnetic_magnitude > 1e-10:
                    parts.append(
                        f"Magnetic (frame-drag) magnitude: {magnetic_magnitude:.2e}."
                    )
                parts.append(f"Wave propagation direction: {state.wave_direction}.")
        else:
            # Field-wide description
            max_amp = np.max(self.wave_amplitude_field)
            mean_amp = np.mean(self.wave_amplitude_field)
            
            parts.append(f"The gravitational wave field spans a {self.grid_shape} grid.")
            
            if max_amp > 1e-10:
                parts.append(
                    f"Maximum wave amplitude: {max_amp:.2e}, mean: {mean_amp:.2e}."
                )
            else:
                parts.append("No significant gravitational wave activity detected.")
            
            if detail_level in ('medium', 'high'):
                electric_max = np.max(np.abs(self.electric_field))
                magnetic_max = np.max(np.abs(self.magnetic_field))
                parts.append(f"Maximum tidal force: {electric_max:.2e}.")
                parts.append(f"Maximum frame-drag effect: {magnetic_max:.2e}.")
        
        return " ".join(parts)
    
    def to_llm_structured_description(self, position: Optional[np.ndarray] = None) -> str:
        """
        Build a compact JSON string describing Weyl tensor properties for LLM consumption.
        
        Creates a structured data representation that can be parsed by AI systems
        for understanding the gravitational wave state.
        
        Args:
            position: Optional [x, y, z] position. If None, describes overall field.
            
        Returns:
            JSON string with structured Weyl tensor properties.
        """
        data: Dict[str, Any] = {
            "type": "WeylTensor",
            "grid_shape": list(self.grid_shape),
            "is_computed": self._is_computed,
        }
        
        if position is not None:
            state = self.get_weyl_state(position)
            data["position"] = position.tolist()
            data["local_state"] = {
                "wave_amplitude": float(state.wave_amplitude),
                "wave_frequency": float(state.wave_frequency),
                "polarization": state.polarization.value,
                "wave_direction": state.wave_direction.tolist(),
                "electric_part": {
                    "values": state.electric_part.tolist(),
                    "frobenius_norm": float(np.linalg.norm(state.electric_part)),
                    "eigenvalues": np.linalg.eigvalsh(state.electric_part).tolist(),
                },
                "magnetic_part": {
                    "values": state.magnetic_part.tolist(),
                    "frobenius_norm": float(np.linalg.norm(state.magnetic_part)),
                },
            }
        else:
            data["field_summary"] = {
                "wave_amplitude": {
                    "min": float(np.min(self.wave_amplitude_field)),
                    "max": float(np.max(self.wave_amplitude_field)),
                    "mean": float(np.mean(self.wave_amplitude_field)),
                    "std": float(np.std(self.wave_amplitude_field)),
                },
                "wave_frequency": {
                    "min": float(np.min(self.wave_frequency_field)),
                    "max": float(np.max(self.wave_frequency_field)),
                    "mean": float(np.mean(self.wave_frequency_field)),
                },
                "electric_field": {
                    "max_abs": float(np.max(np.abs(self.electric_field))),
                    "mean": float(np.mean(self.electric_field)),
                },
                "magnetic_field": {
                    "max_abs": float(np.max(np.abs(self.magnetic_field))),
                    "mean": float(np.mean(self.magnetic_field)),
                },
            }
        
        return json.dumps(data, separators=(',', ':'))
    
    def detect_curvature_anomaly(self, threshold: float = 1e5) -> Tuple[bool, Dict[str, Any]]:
        """
        Detect anomalies in the Weyl tensor field.
        
        Checks for numerical instabilities, extreme values, and other anomalies
        that might indicate simulation problems.
        
        Args:
            threshold: Absolute value above which curvature is considered anomalous.
            
        Returns:
            Tuple of (is_anomaly, details_dict) where details_dict contains
            specific information about detected anomalies.
        """
        if threshold <= 0:
            raise ValueError(f"threshold must be positive, got {threshold}")
        
        anomalies: Dict[str, Any] = {}
        
        # Check for NaN/Inf
        has_nan_weyl = bool(np.isnan(self.weyl_field).any())
        has_inf_weyl = bool(np.isinf(self.weyl_field).any())
        has_nan_electric = bool(np.isnan(self.electric_field).any())
        has_nan_magnetic = bool(np.isnan(self.magnetic_field).any())
        
        if has_nan_weyl or has_inf_weyl:
            anomalies['non_finite_weyl'] = {'nan': has_nan_weyl, 'inf': has_inf_weyl}
        if has_nan_electric:
            anomalies['nan_electric'] = True
        if has_nan_magnetic:
            anomalies['nan_magnetic'] = True
        
        # Check for extreme values
        max_weyl = float(np.max(np.abs(self.weyl_field)))
        max_electric = float(np.max(np.abs(self.electric_field)))
        max_magnetic = float(np.max(np.abs(self.magnetic_field)))
        
        if max_weyl > threshold:
            anomalies['extreme_weyl'] = max_weyl
        if max_electric > threshold:
            anomalies['extreme_electric'] = max_electric
        if max_magnetic > threshold:
            anomalies['extreme_magnetic'] = max_magnetic
        
        # Check for unphysical wave properties
        if np.any(self.wave_frequency_field < 0):
            anomalies['negative_frequency'] = True
        if np.any(self.wave_amplitude_field < 0):
            anomalies['negative_amplitude'] = True
        
        # Summary statistics
        anomalies['max_values'] = {
            'weyl': max_weyl,
            'electric': max_electric,
            'magnetic': max_magnetic,
        }
        
        is_anomaly = bool(
            has_nan_weyl or has_inf_weyl or 
            has_nan_electric or has_nan_magnetic or
            max_weyl > threshold or max_electric > threshold or max_magnetic > threshold or
            anomalies.get('negative_frequency') or anomalies.get('negative_amplitude')
        )
        
        if is_anomaly:
            logger.warning(f"Weyl tensor anomaly detected: {anomalies}")
            if get_cosmic_scroll_logger:
                scroll = get_cosmic_scroll_logger()
                if scroll:
                    scroll.log_event(
                        "weyl_anomaly",
                        payload=anomalies,
                        component="WeylTensor",
                    )

        return (is_anomaly, anomalies)
    
    def get_attention_weights(self, weighting_strategy: str = 'wave_amplitude') -> np.ndarray:
        """
        Generate attention weights based on Weyl tensor properties.
        
        Creates a scalar field that can be used to focus computational or
        perceptual attention on regions of significant gravitational activity.
        
        Args:
            weighting_strategy: Strategy for computing weights:
                - 'wave_amplitude': Weight by gravitational wave amplitude (default)
                - 'tidal_magnitude': Weight by tidal force magnitude
                - 'combined': Combined wave and tidal weighting
                
        Returns:
            Normalized scalar field (sums to 1) with attention weights.
            
        Raises:
            ValueError: If invalid weighting_strategy.
        """
        valid_strategies = {'wave_amplitude', 'tidal_magnitude', 'combined'}
        if weighting_strategy not in valid_strategies:
            raise ValueError(f"weighting_strategy must be one of {valid_strategies}")
        
        weights = np.zeros(self.grid_shape, dtype=np.float64)
        
        if weighting_strategy == 'wave_amplitude':
            weights = np.abs(self.wave_amplitude_field)
        
        elif weighting_strategy == 'tidal_magnitude':
            # Frobenius norm of electric part at each point
            weights = np.linalg.norm(self.electric_field, axis=(-2, -1))
        
        elif weighting_strategy == 'combined':
            wave_weights = np.abs(self.wave_amplitude_field)
            tidal_weights = np.linalg.norm(self.electric_field, axis=(-2, -1))
            # Normalize each and combine
            wave_max = np.max(wave_weights) if np.max(wave_weights) > 0 else 1.0
            tidal_max = np.max(tidal_weights) if np.max(tidal_weights) > 0 else 1.0
            weights = (wave_weights / wave_max + tidal_weights / tidal_max) / 2.0
        
        # Normalize to sum to 1
        total = np.sum(weights)
        if total > 1e-10:
            weights = weights / total
        else:
            # Uniform if no significant activity
            weights = np.ones(self.grid_shape) / np.prod(self.grid_shape)
        
        return weights
    
    def __repr__(self) -> str:
        """Return string representation of WeylTensor state."""
        max_amp = float(np.max(self.wave_amplitude_field))
        mean_amp = float(np.mean(self.wave_amplitude_field))
        max_electric = float(np.max(np.abs(self.electric_field)))
        
        return (
            f"WeylTensor(grid_shape={self.grid_shape}, "
            f"max_wave_amplitude={max_amp:.2e}, mean_wave_amplitude={mean_amp:.2e}, "
            f"max_tidal_force={max_electric:.2e}, computed={self._is_computed})"
        )
