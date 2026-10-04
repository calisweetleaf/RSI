"""
Density Matrix Tensor - Mixed States for Decoherence in Thought Streams

The density matrix ρ_ab represents mixed quantum states, where a system is in a
statistical ensemble of pure states. For consciousness modeling, this enables:

- Decoherence modeling: How quantum superpositions collapse into classical states
- Mixed thought streams: Simultaneous consideration of multiple possibilities
- Entanglement between cognitive modules
- Thermal and environmental effects on cognition

Key Features:
- Hermitian matrix: ρ† = ρ (ensures real eigenvalues = probabilities)
- Positive semi-definite: All eigenvalues ≥ 0
- Unit trace: Tr(ρ) = 1 (probabilities sum to 1)
- Pure states: ρ² = ρ (idempotent)
- Mixed states: ρ² ≠ ρ (non-idempotent)

For Consciousness Integration:
- Decoherence in thought streams (collapse of superposition)
- Mixed states in decision-making (weighing multiple options)
- Entanglement between perception and memory
- Environmental noise in cognitive processes

Mathematical Foundation:
ρ = Σᵢ pᵢ |ψᵢ⟩⟨ψᵢ|

Where:
- pᵢ = probability of state |ψᵢ⟩
- |ψᵢ⟩⟨ψᵢ| = projector onto state |ψᵢ⟩

Properties:
- Eigenvalues = probabilities of eigenstates
- von Neumann entropy: S = -Tr(ρ ln ρ)
- Purity: γ = Tr(ρ²) ∈ [1/d, 1] where d = dimension
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


class StatePurity(Enum):
    """Purity classification of quantum states"""
    PURE = "pure"              # γ = 1 (idempotent)
    NEARLY_PURE = "nearly_pure"  # γ ≈ 1
    MIXED = "mixed"            # 1/d < γ < 1
    MAXIMALLY_MIXED = "maximally_mixed"  # γ = 1/d (maximal entropy)


@dataclass
class DensityMatrixState:
    """Complete density matrix state information"""
    matrix: np.ndarray                    # ρ_ab [d, d]
    eigenvalues: np.ndarray               # Probabilities of eigenstates
    eigenvectors: np.ndarray              # Eigenstate vectors
    purity: float                         # γ = Tr(ρ²)
    von_neumann_entropy: float           # S = -Tr(ρ ln ρ)
    state_purity: StatePurity            # Purity classification
    decoherence_rate: float              # Rate of coherence loss
    entanglement_entropy: float          # Entanglement with environment


class DensityMatrixTensor:
    """
    Density Matrix Tensor for Mixed Quantum States in Cognition
    
    This tensor represents mixed quantum states using density matrices, enabling:
    - Decoherence modeling in thought streams
    - Mixed states in decision-making (weighing multiple options)
    - Entanglement between cognitive modules
    - Environmental noise effects on cognition
    
    The density matrix is essential for consciousness modeling because:
    1. It naturally handles mixed states (statistical ensembles)
    2. It captures decoherence (loss of quantum coherence)
    3. It enables entanglement measures
    4. It provides a bridge between quantum and classical descriptions
    """
    
    def __init__(
        self,
        dimension: int = 4,
        basis_labels: Optional[List[str]] = None
    ) -> None:
        """
        Initialize density matrix tensor.
        
        Args:
            dimension: Hilbert space dimension (number of basis states)
            basis_labels: Optional labels for basis states (e.g., ['ground', 'excited'])
        
        Raises:
            ValueError: If dimension is invalid
        """
        if dimension <= 0:
            raise ValueError(f"Invalid dimension: {dimension}")
        
        self.dimension = dimension
        self.basis_labels = basis_labels or [f"state_{i}" for i in range(dimension)]
        
        # Density matrix ρ_ab [d, d]
        self.density_matrix = np.eye(dimension, dtype=complex) / dimension  # Maximally mixed initially
        
        # Eigen decomposition cache
        self._eigenvalues: Optional[np.ndarray] = None
        self._eigenvectors: Optional[np.ndarray] = None
        
        # Decoherence and entanglement tracking
        self.decoherence_rate = 0.0
        self.entanglement_entropy = 0.0
        
        # Time evolution tracking
        self.time_history: List[Tuple[float, np.ndarray]] = []
        self.max_history_length = 1000
        
        # Track initialization
        self._is_computed = False
        
        logger.info(f"DensityMatrixTensor initialized with dimension {dimension}")
    
    def set_from_pure_state(
        self,
        state_vector: np.ndarray,
        normalize: bool = True
    ) -> np.ndarray:
        """
        Set density matrix from pure state |ψ⟩.
        
        ρ = |ψ⟩⟨ψ|
        
        Args:
            state_vector: Complex state vector |ψ⟩ [d]
            normalize: Whether to normalize the state vector
        
        Returns:
            Density matrix ρ [d, d]
            
        Raises:
            ValueError: If state vector is invalid
        """
        if state_vector.ndim != 1:
            raise ValueError(f"State vector must be 1D, got shape {state_vector.shape}")
        
        if len(state_vector) != self.dimension:
            raise ValueError(
                f"State vector length {len(state_vector)} != dimension {self.dimension}"
            )
        
        # Normalize if requested
        if normalize:
            state_vector = state_vector / np.linalg.norm(state_vector)
        
        # Compute density matrix: ρ = |ψ⟩⟨ψ|
        self.density_matrix = np.outer(state_vector, np.conj(state_vector))
        
        # Update eigen decomposition
        self._update_eigen_decomposition()
        
        self._is_computed = True
        
        logger.info(f"Set density matrix from pure state, purity={self.purity():.6f}")
        
        return self.density_matrix
    
    def set_from_mixed_states(
        self,
        state_vectors: List[np.ndarray],
        probabilities: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Set density matrix from mixed state ensemble.
        
        ρ = Σᵢ pᵢ |ψᵢ⟩⟨ψᵢ|
        
        Args:
            state_vectors: List of state vectors |ψᵢ⟩
            probabilities: Probability of each state (if None, uniform)
        
        Returns:
            Density matrix ρ [d, d]
            
        Raises:
            ValueError: If inputs are invalid
        """
        if not state_vectors:
            raise ValueError("Empty state vectors list")
        
        if probabilities is None:
            probabilities = np.ones(len(state_vectors)) / len(state_vectors)
        
        if len(state_vectors) != len(probabilities):
            raise ValueError(
                f"Number of states {len(state_vectors)} != "
                f"number of probabilities {len(probabilities)}"
            )
        
        if not np.isclose(np.sum(probabilities), 1.0):
            raise ValueError(f"Probabilities must sum to 1, got {np.sum(probabilities)}")
        
        # Initialize density matrix
        self.density_matrix = np.zeros((self.dimension, self.dimension), dtype=complex)
        
        # Add each state with its probability
        for state, prob in zip(state_vectors, probabilities):
            # Normalize state
            state_norm = state / np.linalg.norm(state)
            # Add to density matrix
            self.density_matrix += prob * np.outer(state_norm, np.conj(state_norm))
        
        # Update eigen decomposition
        self._update_eigen_decomposition()
        
        self._is_computed = True
        
        logger.info(f"Set density matrix from {len(state_vectors)} mixed states, "
                   f"purity={self.purity():.6f}")
        
        return self.density_matrix
    
    def set_from_matrix(
        self,
        matrix: np.ndarray,
        validate: bool = True
    ) -> np.ndarray:
        """
        Set density matrix directly from matrix.
        
        Args:
            matrix: Density matrix ρ [d, d]
            validate: Whether to validate density matrix properties
        
        Returns:
            Density matrix ρ [d, d]
            
        Raises:
            ValueError: If matrix is not a valid density matrix
        """
        if matrix.shape != (self.dimension, self.dimension):
            raise ValueError(
                f"Matrix shape {matrix.shape} != required {(self.dimension, self.dimension)}"
            )
        
        if validate:
            # Check Hermitian
            if not np.allclose(matrix, matrix.conj().T):
                raise ValueError("Matrix is not Hermitian")
            
            # Check trace = 1
            trace = np.trace(matrix)
            if not np.isclose(trace, 1.0, atol=1e-6):
                raise ValueError(f"Trace {trace} != 1")
            
            # Check positive semi-definite (all eigenvalues ≥ 0)
            eigenvalues = np.linalg.eigvalsh(matrix)
            if np.any(eigenvalues < -1e-10):
                raise ValueError(f"Matrix has negative eigenvalues: {eigenvalues}")
        
        self.density_matrix = matrix.copy()
        
        # Update eigen decomposition
        self._update_eigen_decomposition()
        
        self._is_computed = True
        
        logger.info(f"Set density matrix from matrix, purity={self.purity():.6f}")
        
        return self.density_matrix
    
    def evolve_unitary(
        self,
        unitary_matrix: np.ndarray,
        time_step: float = 1.0
    ) -> np.ndarray:
        """
        Evolve density matrix under unitary evolution.
        
        ρ(t) = U ρ(0) U†
        
        Args:
            unitary_matrix: Unitary operator U [d, d]
            time_step: Time step for history tracking
        
        Returns:
            Evolved density matrix ρ(t) [d, d]
            
        Raises:
            ValueError: If unitary matrix is invalid
        """
        if unitary_matrix.shape != (self.dimension, self.dimension):
            raise ValueError(
                f"Unitary shape {unitary_matrix.shape} != required {(self.dimension, self.dimension)}"
            )
        
        # Check unitarity: U U† = I
        identity = np.eye(self.dimension)
        if not np.allclose(unitary_matrix @ unitary_matrix.conj().T, identity, atol=1e-6):
            raise ValueError("Matrix is not unitary")
        
        # Evolve: ρ → U ρ U†
        self.density_matrix = unitary_matrix @ self.density_matrix @ unitary_matrix.conj().T
        
        # Update eigen decomposition
        self._update_eigen_decomposition()
        
        # Add to history
        self.time_history.append((time_step, self.density_matrix.copy()))
        if len(self.time_history) > self.max_history_length:
            self.time_history.pop(0)
        
        logger.debug(f"Evolved density matrix under unitary, purity={self.purity():.6f}")
        
        return self.density_matrix
    
    def apply_decoherence(
        self,
        decoherence_rate: float = 0.1,
        decoherence_basis: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Apply decoherence to density matrix.
        
        Models environmental interaction that destroys quantum coherence.
        Off-diagonal elements decay exponentially.
        
        Args:
            decoherence_rate: Rate of coherence loss (0 = no decoherence, 1 = complete)
            decoherence_basis: Basis in which decoherence occurs (if None, computational basis)
        
        Returns:
            Decohered density matrix ρ [d, d]
        """
        if decoherence_rate < 0 or decoherence_rate > 1:
            raise ValueError(f"Decoherence rate must be in [0,1], got {decoherence_rate}")
        
        if decoherence_rate == 0:
            return self.density_matrix
        
        if decoherence_basis is None:
            # Decohere in computational basis
            decohered = self.density_matrix.copy()
            # Decay off-diagonal elements
            for i in range(self.dimension):
                for j in range(self.dimension):
                    if i != j:
                        decohered[i, j] *= (1 - decoherence_rate)
            
            # Renormalize to maintain trace = 1
            trace = np.trace(decohered)
            if trace > 0:
                decohered /= trace
            
            self.density_matrix = decohered
        else:
            # Decohere in specified basis
            # Transform to decoherence basis, apply decoherence, transform back
            raise NotImplementedError("Arbitrary basis decoherence not yet implemented")
        
        # Update eigen decomposition
        self._update_eigen_decomposition()
        
        # Update decoherence tracking
        self.decoherence_rate = decoherence_rate
        
        logger.info(f"Applied decoherence with rate {decoherence_rate}, "
                   f"new purity={self.purity():.6f}")
        
        return self.density_matrix
    
    def purity(self) -> float:
        """
        Compute purity of density matrix.
        
        γ = Tr(ρ²)
        
        Returns:
            Purity γ ∈ [1/d, 1]
            - γ = 1: Pure state
            - γ = 1/d: Maximally mixed state
        """
        if not self._is_computed:
            return 1.0 / self.dimension
        
        return np.real(np.trace(self.density_matrix @ self.density_matrix))
    
    def von_neumann_entropy(self) -> float:
        """
        Compute von Neumann entropy.
        
        S = -Tr(ρ ln ρ) = -Σᵢ λᵢ ln λᵢ
        
        Returns:
            Entropy S ∈ [0, ln d]
            - S = 0: Pure state (zero entropy)
            - S = ln d: Maximally mixed state (maximum entropy)
        """
        if not self._is_computed:
            return np.log(self.dimension)
        
        # Use cached eigenvalues if available
        if self._eigenvalues is None:
            self._update_eigen_decomposition()
        
        eigenvalues = self._eigenvalues
        
        # Compute entropy: S = -Σ λᵢ ln λᵢ
        entropy = 0.0
        for lam in eigenvalues:
            if lam > 1e-12:  # Avoid log(0)
                entropy -= lam * np.log(lam)
        
        return np.real(entropy)
    
    def classify_purity(self) -> StatePurity:
        """
        Classify the purity of the density matrix.
        
        Returns:
            StatePurity enum
        """
        purity = self.purity()
        dim = self.dimension
        
        if np.isclose(purity, 1.0, atol=1e-6):
            return StatePurity.PURE
        elif purity > 0.95:
            return StatePurity.NEARLY_PURE
        elif np.isclose(purity, 1.0/dim, atol=1e-6):
            return StatePurity.MAXIMALLY_MIXED
        else:
            return StatePurity.MIXED
    
    def compute_entanglement_entropy(
        self,
        subsystem_dim: int
    ) -> float:
        """
        Compute entanglement entropy for a bipartite system.
        
        For a system partitioned into A and B, the entanglement entropy is:
        S_A = -Tr(ρ_A ln ρ_A)
        where ρ_A = Tr_B(ρ) is the reduced density matrix of subsystem A.
        
        Args:
            subsystem_dim: Dimension of subsystem A
        
        Returns:
            Entanglement entropy S_A
        """
        if not self._is_computed:
            return 0.0
        
        if subsystem_dim >= self.dimension:
            raise ValueError(
                f"Subsystem dimension {subsystem_dim} >= total dimension {self.dimension}"
            )
        
        # Compute reduced density matrix by partial trace
        # This is simplified - assumes tensor product structure
        reduced_dm = self._partial_trace(subsystem_dim)
        
        # Compute von Neumann entropy of reduced density matrix
        eigenvalues = np.linalg.eigvalsh(reduced_dm)
        entropy = 0.0
        for lam in eigenvalues:
            if lam > 1e-12:
                entropy -= lam * np.log(lam)
        
        self.entanglement_entropy = np.real(entropy)
        
        logger.info(f"Computed entanglement entropy: {self.entanglement_entropy:.6f}")
        
        return self.entanglement_entropy
    
    def measure_observable(
        self,
        observable: np.ndarray
    ) -> Tuple[float, np.ndarray]:
        """
        Measure expectation value of observable.
        
        ⟨O⟩ = Tr(ρ O)
        
        Args:
            observable: Hermitian operator O [d, d]
        
        Returns:
            (expectation_value, post_measurement_state)
            - expectation_value: ⟨O⟩
            - post_measurement_state: Density matrix after measurement
        """
        if observable.shape != (self.dimension, self.dimension):
            raise ValueError(
                f"Observable shape {observable.shape} != required {(self.dimension, self.dimension)}"
            )
        
        # Compute expectation value
        expectation = np.real(np.trace(self.density_matrix @ observable))
        
        # For projective measurement, collapse to eigenstate
        # This is simplified - assumes non-degenerate measurement
        eigenvalues, eigenvectors = np.linalg.eigh(observable)
        
        # Find closest eigenstate
        measured_idx = np.argmin(np.abs(eigenvalues - expectation))
        measured_state = eigenvectors[:, measured_idx]
        
        # Post-measurement state (collapsed to eigenstate)
        post_measurement = np.outer(measured_state, np.conj(measured_state))
        
        logger.info(f"Measured observable, expectation={expectation:.6f}")
        
        return expectation, post_measurement
    
    def get_density_matrix_state(self) -> DensityMatrixState:
        """
        Get complete density matrix state information.
        
        Returns:
            DensityMatrixState object with all state information
        """
        if not self._is_computed:
            return DensityMatrixState(
                matrix=self.density_matrix,
                eigenvalues=np.ones(self.dimension) / self.dimension,
                eigenvectors=np.eye(self.dimension),
                purity=self.purity(),
                von_neumann_entropy=self.von_neumann_entropy(),
                state_purity=self.classify_purity(),
                decoherence_rate=self.decoherence_rate,
                entanglement_entropy=self.entanglement_entropy
            )
        
        # Update eigen decomposition if needed
        if self._eigenvalues is None:
            self._update_eigen_decomposition()
        
        return DensityMatrixState(
            matrix=self.density_matrix.copy(),
            eigenvalues=self._eigenvalues.copy(),
            eigenvectors=self._eigenvectors.copy(),
            purity=self.purity(),
            von_neumann_entropy=self.von_neumann_entropy(),
            state_purity=self.classify_purity(),
            decoherence_rate=self.decoherence_rate,
            entanglement_entropy=self.entanglement_entropy
        )
    
    # ============================================================================
    # Internal Helper Methods
    # ============================================================================
    
    def _update_eigen_decomposition(self) -> None:
        """Update cached eigen decomposition"""
        if self._is_computed:
            self._eigenvalues, self._eigenvectors = np.linalg.eigh(self.density_matrix)
        else:
            self._eigenvalues = np.ones(self.dimension) / self.dimension
            self._eigenvectors = np.eye(self.dimension)
    
    def _partial_trace(self, subsystem_dim: int) -> np.ndarray:
        """
        Compute partial trace over subsystem B.
        
        This is a simplified implementation assuming tensor product structure.
        """
        # For now, just trace out the last (dim - subsystem_dim) dimensions
        remaining_dim = subsystem_dim
        traced_dim = self.dimension // remaining_dim
        
        if remaining_dim * traced_dim != self.dimension:
            raise ValueError("System does not factor into integer dimensions")
        
        # Reshape and trace
        reshaped = self.density_matrix.reshape(remaining_dim, traced_dim, remaining_dim, traced_dim)
        reduced = np.trace(reshaped, axis1=1, axis2=3)
        
        return reduced
    
    def to_ml_features(
        self,
        feature_set: str = 'all'
    ) -> np.ndarray:
        """
        Extract ML-compatible features from density matrix.
        
        Args:
            feature_set: 'all', 'purity', 'entropy', 'eigenvalues'
        
        Returns:
            Feature vector
        """
        if not self._is_computed:
            return np.zeros(10)
        
        features = []
        
        if feature_set in ['all', 'purity']:
            features.extend([
                self.purity(),
                self.decoherence_rate,
                self.entanglement_entropy
            ])
        
        if feature_set in ['all', 'entropy']:
            features.extend([
                self.von_neumann_entropy(),
                np.log(self.dimension) - self.von_neumann_entropy()  # Purity measure
            ])
        
        if feature_set in ['all', 'eigenvalues']:
            if self._eigenvalues is None:
                self._update_eigen_decomposition()
            # Add top eigenvalues
            top_eigenvalues = np.sort(self._eigenvalues)[-min(5, self.dimension):]
            features.extend(top_eigenvalues)
        
        return np.array(features)
    
    def __repr__(self) -> str:
        purity = self.purity()
        entropy = self.von_neumann_entropy()
        return (f"DensityMatrixTensor(dimension={self.dimension}, "
                f"purity={purity:.4f}, entropy={entropy:.4f}, "
                f"decoherence_rate={self.decoherence_rate:.4f})")