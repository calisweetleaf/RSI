"""
Quantum State - Unified Interface for Quantum-Inspired Cognitive States

This module provides a unified interface for representing and manipulating
quantum-inspired states in cognitive modeling, bridging wavefunctions,
density matrices, and phase-space representations.
"""

import numpy as np
from typing import Dict, Tuple, Optional, Union
from dataclasses import dataclass
from enum import Enum


class QuantumStateType(Enum):
    """Types of quantum state representations"""
    WAVEFUNCTION = "wavefunction"        # Pure state |ψ⟩
    DENSITY_MATRIX = "density_matrix"    # Mixed state ρ
    PHASE_SPACE = "phase_space"          # Wigner function W(x,p)
    GEOMETRIC = "geometric"              # Berry phase/curvature


@dataclass
class QuantumState:
    """
    Unified quantum state representation for cognitive modeling.
    
    This class provides a common interface for different quantum state
    representations, enabling seamless integration with consciousness models.
    """
    state_type: QuantumStateType
    data: Union[np.ndarray, Dict[str, np.ndarray]]
    dimension: int
    basis_labels: Optional[Tuple[str, ...]] = None
    
    # State properties
    purity: float = 1.0
    entropy: float = 0.0
    coherence: float = 1.0
    
    # Cognitive interpretation
    cognitive_meaning: Optional[str] = None
    attention_weight: float = 1.0
    emotional_valence: float = 0.0
    
    def __post_init__(self):
        """Validate state data"""
        if self.state_type == QuantumStateType.WAVEFUNCTION:
            if self.data.ndim != 1:
                raise ValueError(f"Wavefunction must be 1D, got shape {self.data.shape}")
            if len(self.data) != self.dimension:
                raise ValueError(f"Wavefunction length {len(self.data)} != dimension {self.dimension}")
        
        elif self.state_type == QuantumStateType.DENSITY_MATRIX:
            if self.data.shape != (self.dimension, self.dimension):
                raise ValueError(f"Density matrix shape {self.data.shape} != required {(self.dimension, self.dimension)}")
    
    def to_wavefunction(self) -> np.ndarray:
        """Convert to wavefunction representation (if possible)"""
        if self.state_type == QuantumStateType.WAVEFUNCTION:
            return self.data
        
        elif self.state_type == QuantumStateType.DENSITY_MATRIX:
            # Extract dominant eigenvector
            eigenvalues, eigenvectors = np.linalg.eigh(self.data)
            return eigenvectors[:, -1]  # Return eigenvector with largest eigenvalue
        
        else:
            raise ValueError(f"Cannot convert {self.state_type} to wavefunction")
    
    def to_density_matrix(self) -> np.ndarray:
        """Convert to density matrix representation"""
        if self.state_type == QuantumStateType.WAVEFUNCTION:
            return np.outer(self.data, np.conj(self.data))
        
        elif self.state_type == QuantumStateType.DENSITY_MATRIX:
            return self.data
        
        else:
            raise ValueError(f"Cannot convert {self.state_type} to density matrix")
    
    def measure(self, observable: np.ndarray) -> Tuple[float, 'QuantumState']:
        """
        Measure an observable and return expectation value and collapsed state.
        
        Args:
            observable: Hermitian operator to measure
        
        Returns:
            (expectation_value, collapsed_state)
        """
        if self.state_type == QuantumStateType.DENSITY_MATRIX:
            # Expectation value: ⟨O⟩ = Tr(ρO)
            expectation = np.real(np.trace(self.data @ observable))
            
            # Collapse to eigenstate (simplified)
            eigenvalues, eigenvectors = np.linalg.eigh(observable)
            measured_idx = np.argmin(np.abs(eigenvalues - expectation))
            collapsed_wavefunction = eigenvectors[:, measured_idx]
            
            return expectation, QuantumState(
                state_type=QuantumStateType.WAVEFUNCTION,
                data=collapsed_wavefunction,
                dimension=self.dimension,
                basis_labels=self.basis_labels,
                purity=1.0,
                entropy=0.0
            )
        
        elif self.state_type == QuantumStateType.WAVEFUNCTION:
            # Expectation value: ⟨ψ|O|ψ⟩
            expectation = np.real(np.dot(np.conj(self.data), observable @ self.data))
            
            # Collapse to eigenstate
            eigenvalues, eigenvectors = np.linalg.eigh(observable)
            measured_idx = np.argmin(np.abs(eigenvalues - expectation))
            collapsed_wavefunction = eigenvectors[:, measured_idx]
            
            return expectation, QuantumState(
                state_type=QuantumStateType.WAVEFUNCTION,
                data=collapsed_wavefunction,
                dimension=self.dimension,
                basis_labels=self.basis_labels,
                purity=1.0,
                entropy=0.0
            )
        
        else:
            raise ValueError(f"Cannot measure {self.state_type}")
    
    def evolve(self, operator: np.ndarray, time: float = 1.0) -> 'QuantumState':
        """
        Evolve state under operator.
        
        For unitary evolution: |ψ(t)⟩ = U|ψ(0)⟩
        For density matrix: ρ(t) = U ρ(0) U†
        
        Args:
            operator: Evolution operator
            time: Time parameter (for history tracking)
        
        Returns:
            Evolved quantum state
        """
        if self.state_type == QuantumStateType.WAVEFUNCTION:
            evolved_data = operator @ self.data
            return QuantumState(
                state_type=QuantumStateType.WAVEFUNCTION,
                data=evolved_data,
                dimension=self.dimension,
                basis_labels=self.basis_labels,
                purity=self.purity,
                entropy=self.entropy
            )
        
        elif self.state_type == QuantumStateType.DENSITY_MATRIX:
            evolved_data = operator @ self.data @ operator.conj().T
            return QuantumState(
                state_type=QuantumStateType.DENSITY_MATRIX,
                data=evolved_data,
                dimension=self.dimension,
                basis_labels=self.basis_labels,
                purity=self.purity,
                entropy=self.entropy
            )
        
        else:
            raise ValueError(f"Cannot evolve {self.state_type}")
    
    def __repr__(self) -> str:
        return (f"QuantumState(type={self.state_type.value}, "
                f"dim={self.dimension}, purity={self.purity:.4f}, "
                f"entropy={self.entropy:.4f})")