"""
Wigner Function Tensor - Phase-Space Representation for Fuzzy Causality

The Wigner function W(x,p) provides a quasi-probability distribution in phase space,
representing quantum states in a way that reveals both position and momentum information.
For consciousness modeling, this enables "fuzzy causality" where cause-effect relationships
are probabilistic rather than deterministic.

Key Features:
- Phase-space representation of quantum states
- Negative values indicate quantum interference
- Marginal distributions recover position/momentum probabilities
- Time evolution via Moyal bracket (quantum Poisson bracket)

For Consciousness Integration:
- Fuzzy causality in perception (probabilistic cause-effect)
- Quantum interference patterns in decision-making
- Phase-space entanglement between cognitive modules
- Uncertainty relations in attention allocation

Mathematical Foundation:
W(x,p) = (1/πℏ) ∫ ψ*(x+y) ψ(x-y) e^(2ipy/ℏ) dy

Properties:
- Real-valued but can be negative (non-classical)
- ∫ W(x,p) dx dp = 1 (normalization)
- ∫ W(x,p) dp = |ψ(x)|² (position probability)
- ∫ W(x,p) dx = |φ(p)|² (momentum probability)
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


class QuantumInterference(Enum):
    """Types of quantum interference in phase space"""
    CONSTRUCTIVE = "constructive"      # Positive interference (amplification)
    DESTRUCTIVE = "destructive"        # Negative interference (cancellation)
    NONE = "none"                      # Classical-like behavior


@dataclass
class WignerState:
    """Complete Wigner function state at a point in phase space"""
    position: float
    momentum: float
    wigner_value: float              # W(x,p) value (can be negative)
    probability_density: float       # |W(x,p)| (positive definite)
    interference_type: QuantumInterference
    coherence_length: float          # Scale of quantum coherence
    entanglement_measure: float      # Degree of entanglement with other systems


class WignerFunctionTensor:
    """
    Wigner Function Tensor for Phase-Space Quantum Cognition
    
    This tensor represents quantum states in phase space, enabling modeling of:
    - Fuzzy causality (probabilistic cause-effect relationships)
    - Quantum interference in decision-making
    - Uncertainty relations in perception and attention
    - Phase-space entanglement between cognitive modules
    
    The Wigner function is particularly suited for consciousness modeling because:
    1. It reveals quantum effects (negative values = interference)
    2. It treats position and momentum symmetrically (complementary observables)
    3. It naturally handles mixed states and decoherence
    4. It provides a bridge between quantum and classical descriptions
    """
    
    def __init__(
        self,
        position_range: Tuple[float, float] = (-10.0, 10.0),
        momentum_range: Tuple[float, float] = (-10.0, 10.0),
        grid_points: Tuple[int, int] = (256, 256),
        hbar: float = 1.0
    ) -> None:
        """
        Initialize Wigner function tensor.
        
        Args:
            position_range: (x_min, x_max) range for position coordinate
            momentum_range: (p_min, p_max) range for momentum coordinate
            grid_points: (n_x, n_p) number of grid points in each dimension
            hbar: Reduced Planck's constant (default 1.0 for natural units)
            
        Raises:
            ValueError: If ranges or grid points are invalid
        """
        # Validate inputs
        if position_range[0] >= position_range[1]:
            raise ValueError(f"Invalid position range: {position_range}")
        if momentum_range[0] >= momentum_range[1]:
            raise ValueError(f"Invalid momentum range: {momentum_range}")
        if grid_points[0] <= 0 or grid_points[1] <= 0:
            raise ValueError(f"Invalid grid points: {grid_points}")
        
        self.position_range = position_range
        self.momentum_range = momentum_range
        self.grid_points = grid_points
        self.hbar = hbar
        
        # Create phase-space grid
        self.x_grid = np.linspace(position_range[0], position_range[1], grid_points[0])
        self.p_grid = np.linspace(momentum_range[0], momentum_range[1], grid_points[1])
        self.dx = self.x_grid[1] - self.x_grid[0]
        self.dp = self.p_grid[1] - self.p_grid[0]
        
        # Wigner function field W(x,p)
        self.wigner_field = np.zeros(grid_points, dtype=np.float64)
        
        # Quantum interference pattern (where W(x,p) < 0)
        self.interference_mask = np.zeros(grid_points, dtype=bool)
        
        # Coherence and entanglement measures
        self.coherence_field = np.zeros(grid_points, dtype=np.float64)
        self.entanglement_field = np.zeros(grid_points, dtype=np.float64)
        
        # Track initialization
        self._is_computed = False
        
        logger.info(f"WignerFunctionTensor initialized: {grid_points[0]}x{grid_points[1]} grid")
    
    def compute_from_wavefunction(
        self,
        wavefunction: np.ndarray,
        position_values: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Compute Wigner function from wavefunction ψ(x).
        
        Uses the integral definition:
        W(x,p) = (1/πℏ) ∫ ψ*(x+y) ψ(x-y) e^(2ipy/ℏ) dy
        
        Args:
            wavefunction: Complex wavefunction ψ(x) values
            position_values: Position values corresponding to wavefunction
                           (if None, uses self.x_grid)
        
        Returns:
            Wigner function field W(x,p)
            
        Raises:
            ValueError: If wavefunction is invalid
        """
        if wavefunction.ndim != 1:
            raise ValueError(f"Wavefunction must be 1D, got shape {wavefunction.shape}")
        
        if position_values is None:
            position_values = self.x_grid
        
        if len(wavefunction) != len(position_values):
            raise ValueError(
                f"Wavefunction length {len(wavefunction)} != position length {len(position_values)}"
            )
        
        # Ensure wavefunction is normalized
        psi = wavefunction / np.sqrt(np.trapz(np.abs(wavefunction)**2, position_values))
        
        # Compute Wigner function via Fourier transform method
        n_x = len(self.x_grid)
        n_p = len(self.p_grid)
        
        wigner = np.zeros((n_x, n_p), dtype=np.float64)
        
        for i, x in enumerate(self.x_grid):
            # Find closest index in position_values
            idx_x = np.argmin(np.abs(position_values - x))
            
            # Create y-grid centered at x
            y_min = max(position_values[0] - x, position_values[0] - position_values[-1])
            y_max = min(position_values[-1] - x, position_values[-1] - position_values[0])
            y_grid = np.linspace(y_min, y_max, min(512, len(position_values)))
            
            # Evaluate ψ(x+y) and ψ*(x-y)
            psi_plus = np.interp(x + y_grid, position_values, psi)
            psi_minus = np.interp(x - y_grid, position_values, psi)
            
            # Compute integrand
            integrand = np.conj(psi_plus) * psi_minus
            
            # Fourier transform to get W(x,p)
            for j, p in enumerate(self.p_grid):
                phase = np.exp(2j * p * y_grid / self.hbar)
                wigner[i, j] = np.real(np.trapz(integrand * phase, y_grid)) / (np.pi * self.hbar)
        
        self.wigner_field = wigner
        
        # Compute interference pattern (negative values)
        self.interference_mask = wigner < 0
        
        # Estimate coherence length from interference pattern
        self._compute_coherence_measures()
        
        self._is_computed = True
        
        logger.info(f"Computed Wigner function from wavefunction, "
                   f"min W={np.min(wigner):.6f}, max W={np.max(wigner):.6f}")
        
        return wigner
    
    def compute_from_density_matrix(
        self,
        density_matrix: np.ndarray,
        position_basis: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Compute Wigner function from density matrix ρ(x,x').
        
        For mixed states:
        W(x,p) = (1/πℏ) ∫ ρ(x+y, x-y) e^(2ipy/ℏ) dy
        
        Args:
            density_matrix: Density matrix ρ(x,x') [n_x, n_x]
            position_basis: Position basis values (if None, uses self.x_grid)
        
        Returns:
            Wigner function field W(x,p)
            
        Raises:
            ValueError: If density matrix is invalid
        """
        if density_matrix.ndim != 2:
            raise ValueError(f"Density matrix must be 2D, got shape {density_matrix.shape}")
        
        if position_basis is None:
            position_basis = self.x_grid
        
        n_x = len(self.x_grid)
        n_p = len(self.p_grid)
        
        wigner = np.zeros((n_x, n_p), dtype=np.float64)
        
        for i, x in enumerate(self.x_grid):
            # Find closest indices
            idx_x = np.argmin(np.abs(position_basis - x))
            
            # Create y-grid
            y_min = max(position_basis[0] - x, position_basis[0] - position_basis[-1])
            y_max = min(position_basis[-1] - x, position_basis[-1] - position_basis[0])
            y_grid = np.linspace(y_min, y_max, min(512, len(position_basis)))
            
            # Evaluate ρ(x+y, x-y) along diagonal
            rho_diag = np.zeros(len(y_grid), dtype=complex)
            for k, y in enumerate(y_grid):
                idx_plus = np.argmin(np.abs(position_basis - (x + y)))
                idx_minus = np.argmin(np.abs(position_basis - (x - y)))
                if 0 <= idx_plus < len(position_basis) and 0 <= idx_minus < len(position_basis):
                    rho_diag[k] = density_matrix[idx_plus, idx_minus]
            
            # Fourier transform
            for j, p in enumerate(self.p_grid):
                phase = np.exp(2j * p * y_grid / self.hbar)
                wigner[i, j] = np.real(np.trapz(rho_diag * phase, y_grid)) / (np.pi * self.hbar)
        
        self.wigner_field = wigner
        self.interference_mask = wigner < 0
        self._compute_coherence_measures()
        self._is_computed = True
        
        logger.info(f"Computed Wigner function from density matrix, "
                   f"min W={np.min(wigner):.6f}, max W={np.max(wigner):.6f}")
        
        return wigner
    
    def compute_fuzzy_causality(
        self,
        cause_position: float,
        effect_position: float,
        time_step: float = 1.0
    ) -> float:
        """
        Compute fuzzy causality measure between cause and effect.
        
        In quantum cognition, causality is not deterministic but probabilistic.
        This method computes the causal influence using Wigner function propagation.
        
        C(cause → effect) = ∫ W(effect, p | cause, t) dp
        
        Args:
            cause_position: Position of cause event
            effect_position: Position of effect event
            time_step: Time elapsed between cause and effect
        
        Returns:
            Causal strength (0 to 1, where 1 = strong causality)
        """
        if not self._is_computed:
            logger.warning("Wigner function not computed, returning default causality")
            return 0.5
        
        # Find indices for cause and effect positions
        idx_cause = np.argmin(np.abs(self.x_grid - cause_position))
        idx_effect = np.argmin(np.abs(self.x_grid - effect_position))
        
        # Simple propagation: assume free particle evolution
        # W(x,p,t) ≈ W(x - pt/m, p, 0)
        # For m=1 and natural units
        
        causal_strength = 0.0
        for j, p in enumerate(self.p_grid):
            # Propagate position backward in time
            x_propagated = effect_position - p * time_step
            
            # Find closest grid point
            idx_prop = np.argmin(np.abs(self.x_grid - x_propagated))
            
            # Accumulate Wigner function value
            if 0 <= idx_prop < len(self.x_grid):
                causal_strength += self.wigner_field[idx_prop, j] * self.dp
        
        # Normalize to [0, 1]
        causal_strength = np.clip(np.abs(causal_strength), 0, 1)
        
        logger.debug(f"Fuzzy causality {cause_position} → {effect_position}: {causal_strength:.4f}")
        
        return causal_strength
    
    def detect_quantum_interference(
        self,
        position_range: Optional[Tuple[float, float]] = None,
        momentum_range: Optional[Tuple[float, float]] = None
    ) -> Dict[str, Any]:
        """
        Detect and analyze quantum interference patterns.
        
        Quantum interference is indicated by negative values of W(x,p).
        This is the hallmark of non-classical behavior.
        
        Args:
            position_range: (x_min, x_max) subrange to analyze
            momentum_range: (p_min, p_max) subrange to analyze
        
        Returns:
            Dictionary with interference statistics
        """
        if not self._is_computed:
            logger.warning("Wigner function not computed")
            return {"error": "Wigner function not computed"}
        
        # Determine analysis range
        if position_range is None:
            x_mask = slice(None)
        else:
            x_mask = (self.x_grid >= position_range[0]) & (self.x_grid <= position_range[1])
        
        if momentum_range is None:
            p_mask = slice(None)
        else:
            p_mask = (self.p_grid >= momentum_range[0]) & (self.p_grid <= momentum_range[1])
        
        # Extract subfield
        wigner_sub = self.wigner_field[x_mask, p_mask]
        interference_sub = self.interference_mask[x_mask, p_mask]
        
        # Compute statistics
        total_points = wigner_sub.size
        interference_points = np.sum(interference_sub)
        interference_fraction = interference_points / total_points if total_points > 0 else 0
        
        # Average negative value (strength of interference)
        if interference_points > 0:
            avg_interference = np.mean(wigner_sub[interference_sub])
        else:
            avg_interference = 0.0
        
        result = {
            "total_points": total_points,
            "interference_points": interference_points,
            "interference_fraction": interference_fraction,
            "avg_negative_value": avg_interference,
            "max_negative_value": np.min(wigner_sub) if interference_points > 0 else 0.0,
            "quantumness_measure": interference_fraction * np.abs(avg_interference)
        }
        
        logger.info(f"Quantum interference detected: {interference_fraction:.2%} of phase space")
        
        return result
    
    def compute_uncertainty_relation(
        self,
        position_std: Optional[float] = None,
        momentum_std: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Compute Heisenberg uncertainty relation from Wigner function.
        
        Δx Δp ≥ ℏ/2
        
        Args:
            position_std: Standard deviation in position (if None, computed from marginals)
            momentum_std: Standard deviation in momentum (if None, computed from marginals)
        
        Returns:
            Dictionary with uncertainty measures
        """
        if not self._is_computed:
            logger.warning("Wigner function not computed")
            return {"error": "Wigner function not computed"}
        
        # Compute marginal distributions
        position_marginal = np.sum(self.wigner_field, axis=1) * self.dp
        momentum_marginal = np.sum(self.wigner_field, axis=0) * self.dx
        
        # Compute standard deviations
        if position_std is None:
            x_mean = np.sum(self.x_grid * position_marginal) * self.dx
            x_var = np.sum((self.x_grid - x_mean)**2 * position_marginal) * self.dx
            position_std = np.sqrt(max(0, x_var))
        
        if momentum_std is None:
            p_mean = np.sum(self.p_grid * momentum_marginal) * self.dp
            p_var = np.sum((self.p_grid - p_mean)**2 * momentum_marginal) * self.dp
            momentum_std = np.sqrt(max(0, p_var))
        
        # Uncertainty product
        uncertainty_product = position_std * momentum_std
        uncertainty_bound = self.hbar / 2
        
        # Saturation measure (how close to minimum uncertainty)
        saturation = uncertainty_product / uncertainty_bound if uncertainty_bound > 0 else float('inf')
        
        result = {
            "position_std": position_std,
            "momentum_std": momentum_std,
            "uncertainty_product": uncertainty_product,
            "heisenberg_bound": uncertainty_bound,
            "saturation": saturation,
            "is_minimal": saturation < 1.01  # Within 1% of bound
        }
        
        logger.info(f"Uncertainty relation: Δx={position_std:.4f}, Δp={momentum_std:.4f}, "
                   f"product={uncertainty_product:.4f}, bound={uncertainty_bound:.4f}")
        
        return result
    
    def get_wigner_state(
        self,
        position: float,
        momentum: float
    ) -> WignerState:
        """
        Get complete Wigner state at a point in phase space.
        
        Args:
            position: Position coordinate
            momentum: Momentum coordinate
        
        Returns:
            WignerState object with all state information
        """
        if not self._is_computed:
            logger.warning("Wigner function not computed")
            return WignerState(
                position=position,
                momentum=momentum,
                wigner_value=0.0,
                probability_density=0.0,
                interference_type=QuantumInterference.NONE,
                coherence_length=0.0,
                entanglement_measure=0.0
            )
        
        # Find closest grid indices
        idx_x = np.argmin(np.abs(self.x_grid - position))
        idx_p = np.argmin(np.abs(self.p_grid - momentum))
        
        # Get Wigner value
        wigner_value = self.wigner_field[idx_x, idx_p]
        probability_density = np.abs(wigner_value)
        
        # Determine interference type
        if wigner_value < -1e-6:
            interference_type = QuantumInterference.DESTRUCTIVE
        elif wigner_value > 1e-6:
            interference_type = QuantumInterference.CONSTRUCTIVE
        else:
            interference_type = QuantumInterference.NONE
        
        # Get coherence and entanglement measures
        coherence_length = self.coherence_field[idx_x, idx_p]
        entanglement_measure = self.entanglement_field[idx_x, idx_p]
        
        return WignerState(
            position=position,
            momentum=momentum,
            wigner_value=wigner_value,
            probability_density=probability_density,
            interference_type=interference_type,
            coherence_length=coherence_length,
            entanglement_measure=entanglement_measure
        )
    
    # ============================================================================
    # Internal Helper Methods
    # ============================================================================
    
    def _compute_coherence_measures(self) -> None:
        """Compute coherence length and entanglement measures from Wigner function"""
        # Coherence length: characteristic scale of interference patterns
        # Estimate from gradient of Wigner function
        grad_x = np.gradient(self.wigner_field, axis=0)
        grad_p = np.gradient(self.wigner_field, axis=1)
        
        # Coherence length ~ 1/|∇W|
        grad_magnitude = np.sqrt(grad_x**2 + grad_p**2)
        self.coherence_field = np.where(
            grad_magnitude > 1e-10,
            1.0 / grad_magnitude,
            0.0
        )
        
        # Entanglement measure: negativity of Wigner function
        # More negative = more entangled with other systems
        self.entanglement_field = np.maximum(0, -self.wigner_field)
    
    def to_ml_features(
        self,
        feature_set: str = 'all'
    ) -> np.ndarray:
        """
        Extract ML-compatible features from Wigner function.
        
        Args:
            feature_set: 'all', 'interference', 'uncertainty', 'coherence'
        
        Returns:
            Feature vector
        """
        if not self._is_computed:
            return np.zeros(10)
        
        features = []
        
        if feature_set in ['all', 'interference']:
            interference_stats = self.detect_quantum_interference()
            features.extend([
                interference_stats['interference_fraction'],
                interference_stats['avg_negative_value'],
                interference_stats['quantumness_measure']
            ])
        
        if feature_set in ['all', 'uncertainty']:
            uncertainty_stats = self.compute_uncertainty_relation()
            features.extend([
                uncertainty_stats['position_std'],
                uncertainty_stats['momentum_std'],
                uncertainty_stats['saturation']
            ])
        
        if feature_set in ['all', 'coherence']:
            features.extend([
                np.mean(self.coherence_field),
                np.std(self.coherence_field),
                np.mean(self.entanglement_field),
                np.std(self.entanglement_field)
            ])
        
        return np.array(features)
    
    def __repr__(self) -> str:
        return (f"WignerFunctionTensor(grid={self.grid_points}, "
                f"x∈[{self.position_range[0]:.2f},{self.position_range[1]:.2f}], "
                f"p∈[{self.momentum_range[0]:.2f},{self.momentum_range[1]:.2f}], "
                f"ℏ={self.hbar:.2f})")