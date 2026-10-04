"""
Decoherence Model - Environmental Interaction and Coherence Loss

This module implements decoherence models for quantum-inspired cognitive systems,
modeling how quantum superpositions collapse into classical states through
interaction with the environment.
"""

import numpy as np
from typing import Dict, Tuple, Optional, Callable
from dataclasses import dataclass
from enum import Enum


class DecoherenceType(Enum):
    """Types of decoherence models"""
    PHASE_DAMPING = "phase_damping"        # Loss of phase coherence
    AMPLITUDE_DAMPING = "amplitude_damping"  # Energy dissipation
    DEPHASING = "dephasing"                # Pure dephasing
    ENVIRONMENTAL = "environmental"        # General environmental coupling


@dataclass
class DecoherenceModel:
    """
    Decoherence model for quantum-inspired cognitive systems.
    
    Models how quantum superpositions collapse into classical states through
    interaction with the environment. This is crucial for understanding how
    "fuzzy" quantum-like thoughts become definite decisions.
    """
    decoherence_type: DecoherenceType
    rate: float  # Decoherence rate (0 = no decoherence, 1 = complete)
    temperature: float = 0.0  # Environmental temperature
    correlation_time: float = 1.0  # Environmental correlation time
    
    # Decoherence operators
    jump_operators: Optional[Tuple[np.ndarray, ...]] = None
    
    # History tracking
    coherence_history: Optional[np.ndarray] = None
    time_points: Optional[np.ndarray] = None
    
    def __post_init__(self):
        """Initialize decoherence model"""
        if self.rate < 0 or self.rate > 1:
            raise ValueError(f"Decoherence rate must be in [0,1], got {self.rate}")
    
    def apply_to_density_matrix(
        self,
        density_matrix: np.ndarray,
        time_step: float = 1.0
    ) -> np.ndarray:
        """
        Apply decoherence to density matrix.
        
        Args:
            density_matrix: Input density matrix
            time_step: Time step for decoherence evolution
        
        Returns:
            Decohered density matrix
        """
        if self.rate == 0:
            return density_matrix
        
        if self.decoherence_type == DecoherenceType.PHASE_DAMPING:
            return self._apply_phase_damping(density_matrix, time_step)
        
        elif self.decoherence_type == DecoherenceType.AMPLITUDE_DAMPING:
            return self._apply_amplitude_damping(density_matrix, time_step)
        
        elif self.decoherence_type == DecoherenceType.DEPHASING:
            return self._apply_dephasing(density_matrix, time_step)
        
        else:
            raise ValueError(f"Decoherence type {self.decoherence_type} not implemented")
    
    def _apply_phase_damping(
        self,
        density_matrix: np.ndarray,
        time_step: float
    ) -> np.ndarray:
        """
        Apply phase damping decoherence.
        
        Phase damping destroys phase coherence without energy loss.
        Off-diagonal elements decay exponentially.
        """
        decohered = density_matrix.copy()
        decay_factor = np.exp(-self.rate * time_step)
        
        # Decay off-diagonal elements
        n = density_matrix.shape[0]
        for i in range(n):
            for j in range(n):
                if i != j:
                    decohered[i, j] *= decay_factor
        
        # Renormalize
        trace = np.trace(decohered)
        if trace > 0:
            decohered /= trace
        
        return decohered
    
    def _apply_amplitude_damping(
        self,
        density_matrix: np.ndarray,
        time_step: float
    ) -> np.ndarray:
        """
        Apply amplitude damping decoherence.
        
        Amplitude damping models energy dissipation (e.g., relaxation to ground state).
        """
        # Simplified amplitude damping for 2-level system
        n = density_matrix.shape[0]
        
        # Create jump operator for energy dissipation
        jump_op = np.zeros((n, n))
        for i in range(n - 1):
            jump_op[i + 1, i] = np.sqrt(self.rate * time_step)
        
        # Apply Lindblad master equation (simplified)
        decohered = density_matrix.copy()
        decohered = decohered + self.rate * time_step * (
            jump_op @ density_matrix @ jump_op.conj().T
            - 0.5 * (jump_op.conj().T @ jump_op @ density_matrix)
            - 0.5 * (density_matrix @ jump_op.conj().T @ jump_op)
        )
        
        # Renormalize
        trace = np.trace(decohered)
        if trace > 0:
            decohered /= trace
        
        return decohered
    
    def _apply_dephasing(
        self,
        density_matrix: np.ndarray,
        time_step: float
    ) -> np.ndarray:
        """
        Apply pure dephasing decoherence.
        
        Dephasing destroys coherence in a specific basis.
        """
        # Dephasing in computational basis
        decohered = density_matrix.copy()
        
        # Create dephasing operator
        n = density_matrix.shape[0]
        dephasing_op = np.diag([np.exp(-self.rate * time_step * i) for i in range(n)])
        
        # Apply dephasing
        decohered = dephasing_op * decohered
        
        # Renormalize
        trace = np.trace(decohered)
        if trace > 0:
            decohered /= trace
        
        return decohered
    
    def compute_coherence(
        self,
        density_matrix: np.ndarray
    ) -> float:
        """
        Compute coherence measure of density matrix.
        
        Uses l1-norm of off-diagonal elements as coherence measure.
        """
        n = density_matrix.shape[0]
        coherence = 0.0
        
        for i in range(n):
            for j in range(n):
                if i != j:
                    coherence += np.abs(density_matrix[i, j])
        
        return coherence
    
    def simulate_decoherence_trajectory(
        self,
        initial_state: np.ndarray,
        time_points: np.ndarray,
        is_density_matrix: bool = True
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Simulate decoherence over time.
        
        Args:
            initial_state: Initial quantum state
            time_points: Time points for simulation
            is_density_matrix: Whether initial state is density matrix
        
        Returns:
            (time_points, coherence_history)
        """
        if not is_density_matrix:
            # Convert wavefunction to density matrix
            initial_state = np.outer(initial_state, np.conj(initial_state))
        
        coherence_history = np.zeros(len(time_points))
        current_state = initial_state.copy()
        
        for i, t in enumerate(time_points):
            if i == 0:
                dt = 0
            else:
                dt = time_points[i] - time_points[i - 1]
            
            # Apply decoherence
            current_state = self.apply_to_density_matrix(current_state, dt)
            
            # Compute coherence
            coherence_history[i] = self.compute_coherence(current_state)
        
        self.coherence_history = coherence_history
        self.time_points = time_points
        
        return time_points, coherence_history
    
    def estimate_decoherence_time(
        self,
        initial_coherence: float = 1.0,
        threshold: float = 0.01
    ) -> float:
        """
        Estimate decoherence time (time for coherence to drop to threshold).
        
        Args:
            initial_coherence: Initial coherence value
            threshold: Coherence threshold for "decohered" state
        
        Returns:
            Decoherence time
        """
        if self.rate == 0:
            return float('inf')
        
        # Exponential decay model: C(t) = C₀ exp(-γt)
        # Solve for t when C(t) = threshold
        decoherence_time = -np.log(threshold / initial_coherence) / self.rate
        
        return decoherence_time
    
    def __repr__(self) -> str:
        return (f"DecoherenceModel(type={self.decoherence_type.value}, "
                f"rate={self.rate:.4f}, temp={self.temperature:.2f})")