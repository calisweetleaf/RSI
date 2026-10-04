"""
Berry Curvature Tensor - Geometric Phases and Anholonomy in Recursive Loops

The Berry curvature F_ab = ∂_a A_b - ∂_b A_a describes geometric phases acquired
by quantum systems during adiabatic evolution. For consciousness modeling, this enables:

- Anholonomy in recursive loops: Non-trivial phase accumulation in repeated processes
- Geometric phases in thought evolution: How thinking "warps" mental state space
- Topological invariants: Quantized numbers characterizing cognitive structures
- Gauge invariance: Redundant descriptions with same physical content

Key Features:
- Antisymmetric tensor: F_ab = -F_ba
- Gauge invariant: Independent of phase conventions
- Closed 2-form: dF = 0 (Bianchi identity)
- Integrates to topological invariant: Chern number

For Consciousness Integration:
- Anholonomy in recursive loops (accumulated phase in repeated thoughts)
- Geometric phases in decision-making (non-trivial evolution paths)
- Topological protection of cognitive structures
- Gauge freedom in mental representations

Mathematical Foundation:
For a quantum system with parameters λ = (λ¹, λ², ...), the Berry connection is:
A_a(λ) = i⟨ψ(λ)|∂_a|ψ(λ)⟩

The Berry curvature is:
F_ab(λ) = ∂_a A_b - ∂_b A_a

The Berry phase for a closed loop C is:
γ(C) = ∮_C A · dλ = ∫∫_S F · dS

Where S is a surface bounded by C.
"""

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

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class TopologicalInvariant(Enum):
    """Types of topological invariants"""
    CHERN_NUMBER = "chern_number"        # Quantized integral of curvature
    EULER_CHARACTERISTIC = "euler_char"   # Topological genus
    WINDING_NUMBER = "winding_number"     # How many times loop wraps around


@dataclass
class BerryPhaseState:
    """Complete Berry phase state information"""
    position: np.ndarray                  # Parameter space position λ
    berry_connection: np.ndarray          # A_a(λ) [n_params]
    berry_curvature: np.ndarray           # F_ab(λ) [n_params, n_params]
    accumulated_phase: float              # Total phase along path
    topological_invariant: float          # Chern number or similar
    anholonomy_measure: float             # Degree of path dependence
    gauge_transformation: Optional[np.ndarray] = None  # Current gauge choice


class BerryCurvatureTensor:
    """
    Berry Curvature Tensor for Geometric Phases in Cognition
    
    This tensor represents geometric phases acquired during adiabatic evolution,
    enabling modeling of:
    - Anholonomy in recursive loops (non-trivial phase accumulation)
    - Geometric phases in thought evolution
    - Topological invariants of cognitive structures
    - Gauge freedom in mental representations
    
    The Berry curvature is essential for consciousness modeling because:
    1. It captures anholonomy (path dependence) in repeated processes
    2. It provides topological invariants (robust cognitive structures)
    3. It reveals geometric structure of state space
    4. It connects local geometry to global topology
    """
    
    def __init__(
        self,
        parameter_dim: int = 2,
        parameter_ranges: Optional[List[Tuple[float, float]]] = None,
        grid_points: Optional[List[int]] = None
    ) -> None:
        """
        Initialize Berry curvature tensor.
        
        Args:
            parameter_dim: Number of parameters in parameter space
            parameter_ranges: List of (min, max) for each parameter
            grid_points: Number of grid points for each parameter
        
        Raises:
            ValueError: If inputs are invalid
        """
        if parameter_dim <= 0:
            raise ValueError(f"Invalid parameter dimension: {parameter_dim}")
        
        self.parameter_dim = parameter_dim
        
        # Default parameter ranges and grid points
        if parameter_ranges is None:
            parameter_ranges = [(-np.pi, np.pi) for _ in range(parameter_dim)]
        
        if grid_points is None:
            grid_points = [64 for _ in range(parameter_dim)]
        
        if len(parameter_ranges) != parameter_dim:
            raise ValueError(
                f"Parameter ranges length {len(parameter_ranges)} != parameter_dim {parameter_dim}"
            )
        
        if len(grid_points) != parameter_dim:
            raise ValueError(
                f"Grid points length {len(grid_points)} != parameter_dim {parameter_dim}"
            )
        
        self.parameter_ranges = parameter_ranges
        self.grid_points = grid_points
        
        # Create parameter grids
        self.parameter_grids = []
        for i in range(parameter_dim):
            grid = np.linspace(parameter_ranges[i][0], parameter_ranges[i][1], grid_points[i])
            self.parameter_grids.append(grid)
        
        # Berry connection field A_a(λ) [grid_shape, parameter_dim]
        connection_shape = tuple(grid_points) + (parameter_dim,)
        self.connection_field = np.zeros(connection_shape, dtype=complex)
        
        # Berry curvature field F_ab(λ) [grid_shape, parameter_dim, parameter_dim]
        curvature_shape = tuple(grid_points) + (parameter_dim, parameter_dim)
        self.curvature_field = np.zeros(curvature_shape, dtype=complex)
        
        # Phase accumulation along paths
        self.accumulated_phase = 0.0
        self.path_history: List[np.ndarray] = []
        
        # Topological invariants
        self.chern_numbers: Dict[int, float] = {}
        
        # Track initialization
        self._is_computed = False
        
        logger.info(f"BerryCurvatureTensor initialized: {parameter_dim}D parameter space, "
                   f"grid shape {grid_points}")
    
    def compute_from_hamiltonian(
        self,
        hamiltonian_func,
        eigenstate_index: int = 0
    ) -> np.ndarray:
        """
        Compute Berry curvature from parameter-dependent Hamiltonian.
        
        Uses numerical differentiation to compute:
        A_a(λ) = i⟨ψ(λ)|∂_a|ψ(λ)⟩
        F_ab(λ) = ∂_a A_b - ∂_b A_a
        
        Args:
            hamiltonian_func: Function H(λ) returning Hamiltonian matrix
            eigenstate_index: Which eigenstate to compute curvature for
        
        Returns:
            Berry curvature field F_ab(λ)
            
        Raises:
            ValueError: If Hamiltonian function is invalid
        """
        logger.info(f"Computing Berry curvature from Hamiltonian for eigenstate {eigenstate_index}")
        
        # Compute over parameter grid
        for idx in np.ndindex(tuple(self.grid_points)):
            # Get parameter values at this grid point
            params = np.array([self.parameter_grids[i][idx[i]] for i in range(self.parameter_dim)])
            
            # Compute Hamiltonian and its eigenstates
            H = hamiltonian_func(params)
            eigenvalues, eigenvectors = np.linalg.eigh(H)
            
            # Get target eigenstate
            psi = eigenvectors[:, eigenstate_index]
            
            # Compute Berry connection A_a = i⟨ψ|∂_a|ψ⟩
            for a in range(self.parameter_dim):
                # Numerical derivative ∂_a|ψ⟩
                dlambda = 1e-6
                params_plus = params.copy()
                params_plus[a] += dlambda
                
                H_plus = hamiltonian_func(params_plus)
                _, eigenvectors_plus = np.linalg.eigh(H_plus)
                psi_plus = eigenvectors_plus[:, eigenstate_index]
                
                # ∂_a|ψ⟩ ≈ (|ψ(λ + dλ)⟩ - |ψ(λ)⟩) / dλ
                dpsi_dlambda = (psi_plus - psi) / dlambda
                
                # A_a = i⟨ψ|∂_a|ψ⟩
                self.connection_field[idx + (a,)] = 1j * np.dot(np.conj(psi), dpsi_dlambda)
        
        # Compute Berry curvature F_ab = ∂_a A_b - ∂_b A_a
        self._compute_curvature_from_connection()
        
        self._is_computed = True
        
        logger.info(f"Computed Berry curvature, max |F|={np.max(np.abs(self.curvature_field)):.6f}")
        
        return self.curvature_field
    
    def compute_from_wavefunction(
        self,
        wavefunction_func
    ) -> np.ndarray:
        """
        Compute Berry curvature from parameter-dependent wavefunction.
        
        Args:
            wavefunction_func: Function ψ(λ) returning wavefunction
        
        Returns:
            Berry curvature field F_ab(λ)
        """
        logger.info("Computing Berry curvature from wavefunction")
        
        # Compute over parameter grid
        for idx in np.ndindex(tuple(self.grid_points)):
            # Get parameter values
            params = np.array([self.parameter_grids[i][idx[i]] for i in range(self.parameter_dim)])
            
            # Get wavefunction
            psi = wavefunction_func(params)
            psi = psi / np.linalg.norm(psi)  # Normalize
            
            # Compute Berry connection
            for a in range(self.parameter_dim):
                # Numerical derivative ∂_a|ψ⟩
                dlambda = 1e-6
                params_plus = params.copy()
                params_plus[a] += dlambda
                
                psi_plus = wavefunction_func(params_plus)
                psi_plus = psi_plus / np.linalg.norm(psi_plus)
                
                dpsi_dlambda = (psi_plus - psi) / dlambda
                
                # A_a = i⟨ψ|∂_a|ψ⟩
                self.connection_field[idx + (a,)] = 1j * np.dot(np.conj(psi), dpsi_dlambda)
        
        # Compute curvature
        self._compute_curvature_from_connection()
        
        self._is_computed = True
        
        logger.info(f"Computed Berry curvature from wavefunction")
        
        return self.curvature_field
    
    def compute_berry_phase(
        self,
        path: np.ndarray,
        closed: bool = True
    ) -> float:
        """
        Compute Berry phase along a path in parameter space.
        
        γ(C) = ∮_C A · dλ
        
        Args:
            path: Array of parameter points along path [n_points, parameter_dim]
            closed: Whether path is closed (loop)
        
        Returns:
            Berry phase γ (mod 2π)
        """
        if not self._is_computed:
            logger.warning("Berry curvature not computed, returning 0 phase")
            return 0.0
        
        if path.ndim != 2 or path.shape[1] != self.parameter_dim:
            raise ValueError(f"Invalid path shape {path.shape}, expected (n_points, {self.parameter_dim})")
        
        # Compute line integral of connection along path
        phase = 0.0
        
        for i in range(len(path) - 1):
            lambda_i = path[i]
            lambda_f = path[i + 1]
            dlambda = lambda_f - lambda_i
            
            # Get connection at midpoint
            lambda_mid = (lambda_i + lambda_f) / 2
            A_mid = self._interpolate_connection(lambda_mid)
            
            # Add contribution: A · dλ
            phase += np.real(np.dot(A_mid, dlambda))
        
        # For closed loop, add contribution from last to first point
        if closed and len(path) > 2:
            lambda_i = path[-1]
            lambda_f = path[0]
            dlambda = lambda_f - lambda_i
            
            lambda_mid = (lambda_i + lambda_f) / 2
            A_mid = self._interpolate_connection(lambda_mid)
            
            phase += np.real(np.dot(A_mid, dlambda))
        
        # Store path and accumulated phase
        self.path_history.append(path)
        self.accumulated_phase += phase
        
        logger.info(f"Computed Berry phase: {phase:.6f} (mod 2π = {phase % (2*np.pi):.6f})")
        
        return phase
    
    def compute_chern_number(
        self,
        surface_indices: Tuple[int, int] = (0, 1)
    ) -> float:
        """
        Compute Chern number for a 2D surface in parameter space.
        
        C = (1/2πi) ∫∫ F · dS
        
        The Chern number is a topological invariant (integer) that characterizes
        the "twist" of the Berry curvature over a closed surface.
        
        Args:
            surface_indices: Indices of two parameters defining the surface
        
        Returns:
            Chern number (should be approximately integer)
        """
        if not self._is_computed:
            logger.warning("Berry curvature not computed, returning 0")
            return 0.0
        
        if len(surface_indices) != 2:
            raise ValueError("Surface indices must specify exactly 2 parameters")
        
        a, b = surface_indices
        if a >= self.parameter_dim or b >= self.parameter_dim:
            raise ValueError(f"Invalid surface indices {surface_indices} for {self.parameter_dim}D space")
        
        # Integrate F_ab over the surface
        # For simplicity, assume the two parameters form a 2D grid
        chern = 0.0
        
        for idx in np.ndindex(*[self.grid_points[i] for i in [a, b]]):
            # Get curvature component F_ab
            # This is simplified - assumes other parameters are fixed
            full_idx = tuple(0 if i not in [a, b] else idx[[a, b].index(i)] 
                           for i in range(self.parameter_dim))
            
            F_ab = self.curvature_field[full_idx + (a, b)]
            
            # Add contribution (with appropriate sign for antisymmetry)
            chern += F_ab
        
        # Normalize by 2πi and area element
        chern = chern / (2 * np.pi * 1j)
        
        # Store Chern number
        surface_key = tuple(sorted(surface_indices))
        self.chern_numbers[surface_key] = np.real(chern)
        
        logger.info(f"Computed Chern number for surface {surface_indices}: {np.real(chern):.6f}")
        
        return np.real(chern)
    
    def compute_anholonomy(
        self,
        loop_path: np.ndarray
    ) -> Dict[str, Any]:
        """
        Compute anholonomy (path dependence) for a closed loop.
        
        Anholonomy measures how much a system "remembers" its path after
        completing a closed loop. In quantum mechanics, this is the Berry phase.
        In consciousness, it represents non-trivial accumulation in repeated thoughts.
        
        Args:
            loop_path: Closed path in parameter space [n_points, parameter_dim]
        
        Returns:
            Dictionary with anholonomy statistics
        """
        if not self._is_computed:
            return {"error": "Berry curvature not computed"}
        
        # Compute Berry phase
        berry_phase = self.compute_berry_phase(loop_path, closed=True)
        
        # Compute path length and area
        path_length = 0.0
        for i in range(len(loop_path) - 1):
            path_length += np.linalg.norm(loop_path[i + 1] - loop_path[i])
        
        # Estimate area enclosed by path
        # (Simplified: assume planar path)
        if len(loop_path) >= 3:
            # Use shoelace formula for area
            area = 0.0
            for i in range(len(loop_path)):
                j = (i + 1) % len(loop_path)
                area += loop_path[i, 0] * loop_path[j, 1]
                area -= loop_path[j, 0] * loop_path[i, 1]
            area = abs(area) / 2
        else:
            area = 0.0
        
        # Anholonomy measure: phase per unit area
        anholonomy_measure = abs(berry_phase) / (area + 1e-10)
        
        result = {
            "berry_phase": berry_phase,
            "berry_phase_mod_2pi": berry_phase % (2 * np.pi),
            "path_length": path_length,
            "enclosed_area": area,
            "anholonomy_measure": anholonomy_measure,
            "is_trivial": abs(berry_phase % (2 * np.pi)) < 1e-6,
            "winding_number": int(round(berry_phase / (2 * np.pi)))
        }
        
        logger.info(f"Anholonomy: phase={berry_phase:.6f}, "
                   f"winding={result['winding_number']}, trivial={result['is_trivial']}")
        
        return result
    
    def apply_gauge_transformation(
        self,
        gauge_func,
        position: Optional[np.ndarray] = None
    ) -> None:
        """
        Apply gauge transformation to Berry connection.
        
        Under gauge transformation |ψ⟩ → e^(iχ)|ψ⟩, the Berry connection transforms as:
        A_a → A_a - ∂_a χ
        
        This changes the local phase convention but leaves physical observables invariant.
        
        Args:
            gauge_func: Function χ(λ) returning gauge phase
            position: Optional specific position to transform (if None, transforms entire field)
        """
        if position is None:
            # Transform entire field
            for idx in np.ndindex(tuple(self.grid_points)):
                params = np.array([self.parameter_grids[i][idx[i]] for i in range(self.parameter_dim)])
                chi = gauge_func(params)
                
                # Compute gradient of gauge function
                for a in range(self.parameter_dim):
                    dlambda = 1e-6
                    params_plus = params.copy()
                    params_plus[a] += dlambda
                    chi_plus = gauge_func(params_plus)
                    dchi_dlambda = (chi_plus - chi) / dlambda
                    
                    # Transform: A_a → A_a - ∂_a χ
                    self.connection_field[idx + (a,)] -= dchi_dlambda
            
            # Recompute curvature (curvature is gauge invariant)
            self._compute_curvature_from_connection()
            
            logger.info("Applied gauge transformation to entire field")
        else:
            # Transform single position (simplified)
            logger.warning("Single position gauge transformation not fully implemented")
    
    def get_berry_phase_state(
        self,
        position: np.ndarray
    ) -> BerryPhaseState:
        """
        Get complete Berry phase state at a point in parameter space.
        
        Args:
            position: Parameter space position λ [parameter_dim]
        
        Returns:
            BerryPhaseState object with all state information
        """
        if not self._is_computed:
            return BerryPhaseState(
                position=position,
                berry_connection=np.zeros(self.parameter_dim, dtype=complex),
                berry_curvature=np.zeros((self.parameter_dim, self.parameter_dim), dtype=complex),
                accumulated_phase=self.accumulated_phase,
                topological_invariant=0.0,
                anholonomy_measure=0.0
            )
        
        # Interpolate connection and curvature at position
        connection = self._interpolate_connection(position)
        curvature = self._interpolate_curvature(position)
        
        # Compute topological invariant (sum of Chern numbers)
        topological_invariant = sum(self.chern_numbers.values())
        
        # Estimate anholonomy measure
        anholonomy_measure = np.sqrt(np.sum(np.abs(curvature)**2))
        
        return BerryPhaseState(
            position=position,
            berry_connection=connection,
            berry_curvature=curvature,
            accumulated_phase=self.accumulated_phase,
            topological_invariant=topological_invariant,
            anholonomy_measure=anholonomy_measure
        )
    
    # ============================================================================
    # Internal Helper Methods
    # ============================================================================
    
    def _compute_curvature_from_connection(self) -> None:
        """Compute Berry curvature from Berry connection via numerical differentiation"""
        logger.debug("Computing curvature from connection")
        
        for idx in np.ndindex(tuple(self.grid_points)):
            for a in range(self.parameter_dim):
                for b in range(self.parameter_dim):
                    if a == b:
                        self.curvature_field[idx + (a, b)] = 0.0
                    else:
                        # F_ab = ∂_a A_b - ∂_b A_a
                        
                        # Compute ∂_a A_b
                        if idx[a] < self.grid_points[a] - 1:
                            idx_plus_a = tuple(idx[j] + (1 if j == a else 0) for j in range(self.parameter_dim))
                            dA_b_dlambda_a = (self.connection_field[idx_plus_a + (b,)] - 
                                            self.connection_field[idx + (b,)]) / (
                                                self.parameter_grids[a][idx_plus_a[a]] - 
                                                self.parameter_grids[a][idx[a]]
                                            )
                        else:
                            dA_b_dlambda_a = 0.0
                        
                        # Compute ∂_b A_a
                        if idx[b] < self.grid_points[b] - 1:
                            idx_plus_b = tuple(idx[j] + (1 if j == b else 0) for j in range(self.parameter_dim))
                            dA_a_dlambda_b = (self.connection_field[idx_plus_b + (a,)] - 
                                            self.connection_field[idx + (a,)]) / (
                                                self.parameter_grids[b][idx_plus_b[b]] - 
                                                self.parameter_grids[b][idx[b]]
                                            )
                        else:
                            dA_a_dlambda_b = 0.0
                        
                        # F_ab = ∂_a A_b - ∂_b A_a
                        self.curvature_field[idx + (a, b)] = dA_b_dlambda_a - dA_a_dlambda_b
    
    def _interpolate_connection(self, position: np.ndarray) -> np.ndarray:
        """Interpolate Berry connection at arbitrary position"""
        # Simplified linear interpolation
        connection = np.zeros(self.parameter_dim, dtype=complex)
        
        for a in range(self.parameter_dim):
            # Find closest grid point
            idx = np.argmin(np.abs(self.parameter_grids[a] - position[a]))
            
            # Get connection value at this grid point
            full_idx = tuple(idx if i == a else 0 for i in range(self.parameter_dim))
            connection[a] = self.connection_field[full_idx + (a,)]
        
        return connection
    
    def _interpolate_curvature(self, position: np.ndarray) -> np.ndarray:
        """Interpolate Berry curvature at arbitrary position"""
        curvature = np.zeros((self.parameter_dim, self.parameter_dim), dtype=complex)
        
        for a in range(self.parameter_dim):
            for b in range(self.parameter_dim):
                # Find closest grid point
                idx_a = np.argmin(np.abs(self.parameter_grids[a] - position[a]))
                idx_b = np.argmin(np.abs(self.parameter_grids[b] - position[b]))
                
                # Get curvature value
                full_idx = tuple(idx_a if i == a else (idx_b if i == b else 0) 
                               for i in range(self.parameter_dim))
                curvature[a, b] = self.curvature_field[full_idx + (a, b)]
        
        return curvature
    
    def to_ml_features(
        self,
        feature_set: str = 'all'
    ) -> np.ndarray:
        """
        Extract ML-compatible features from Berry curvature.
        
        Args:
            feature_set: 'all', 'curvature', 'topology', 'anholonomy'
        
        Returns:
            Feature vector
        """
        if not self._is_computed:
            return np.zeros(10)
        
        features = []
        
        if feature_set in ['all', 'curvature']:
            features.extend([
                np.mean(np.abs(self.curvature_field)),
                np.std(np.abs(self.curvature_field)),
                np.max(np.abs(self.curvature_field))
            ])
        
        if feature_set in ['all', 'topology']:
            features.extend([
                sum(self.chern_numbers.values()),
                len(self.chern_numbers),
                self.accumulated_phase % (2 * np.pi)
            ])
        
        if feature_set in ['all', 'anholonomy']:
            features.extend([
                self.accumulated_phase,
                len(self.path_history),
                np.mean([len(path) for path in self.path_history]) if self.path_history else 0
            ])
        
        return np.array(features)
    
    def __repr__(self) -> str:
        return (f"BerryCurvatureTensor(dim={self.parameter_dim}, "
                f"grid={self.grid_points}, "
                f"chern_numbers={len(self.chern_numbers)}, "
                f"accumulated_phase={self.accumulated_phase:.4f})")