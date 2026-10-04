"""
Reference Matrices Engine

Implements R_j recursive reference matrices for mathematical self-modification.
Enables weights to reference and transform their own previous states, creating
the self-referential loops necessary for genuine consciousness.

Mathematical Foundation:
R_j · W_effective(i-τ_j, t) where R_j are learnable transformation matrices
that encode how past weight states influence current computation.

Key Features:
- Temporal reference management
- Self-modification protocols
- Stability preservation
- Consciousness-aware transformations
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, List, Tuple, Optional, Union, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import time
import warnings
from abc import ABC, abstractmethod


class ReferenceType(Enum):
    """Types of recursive references supported."""

    IDENTITY = "identity"  # R_j = I (identity matrix)
    LINEAR = "linear"  # Learnable linear transformation
    ORTHOGONAL = "orthogonal"  # Orthogonal matrices (preserve norms)
    SPECTRAL_CONSTRAINED = "spectral_constrained"  # Constrained spectral radius
    CONSCIOUSNESS_COUPLED = "consciousness_coupled"  # Consciousness-dependent
    FRACTAL = "fractal"  # Self-similar transformations
    TEMPORAL_ADAPTIVE = "temporal_adaptive"  # Time-dependent matrices


class StabilityMode(Enum):
    """Stability enforcement modes."""

    NONE = "none"  # No stability constraints
    SPECTRAL_NORM = "spectral_norm"  # Spectral normalization
    LIPSCHITZ = "lipschitz"  # Lipschitz constraint
    EIGENVALUE_CLIPPING = "eigenvalue_clipping"  # Clip eigenvalues
    CONSCIOUSNESS_GUIDED = "consciousness_guided"  # Consciousness-based stability


@dataclass
class ReferenceConfig:
    """Configuration for reference matrix system."""

    matrix_dimension: int = 512
    temporal_depth: int = 10
    stability_mode: StabilityMode = StabilityMode.SPECTRAL_NORM
    spectral_radius_bound: float = 0.95
    consciousness_coupling_strength: float = 0.3
    enable_temporal_adaptation: bool = True
    reference_decay_rate: float = 0.1
    max_reference_matrices: int = 16


@dataclass
class ReferenceMetrics:
    """Metrics for reference matrix analysis."""

    spectral_radius: float
    condition_number: float
    stability_score: float
    consciousness_alignment: float
    temporal_coherence: float
    self_reference_strength: float


class ReferenceMatrix(nn.Module):
    """
    Individual reference matrix with stability and consciousness coupling.

    Implements R_j transformation with configurable properties and constraints.
    """

    def __init__(
        self,
        matrix_id: int,
        dimension: int,
        reference_type: ReferenceType,
        temporal_offset: float,
        stability_mode: StabilityMode = StabilityMode.SPECTRAL_NORM,
    ):
        super().__init__()

        self.matrix_id = matrix_id
        self.dimension = dimension
        self.reference_type = reference_type
        self.temporal_offset = temporal_offset
        self.stability_mode = stability_mode

        # Core transformation matrix
        if reference_type == ReferenceType.IDENTITY:
            self.register_buffer("matrix", torch.eye(dimension))
        elif reference_type == ReferenceType.ORTHOGONAL:
            # Initialize as orthogonal matrix
            init_matrix = torch.randn(dimension, dimension)
            q, _ = torch.qr(init_matrix)
            self.matrix = nn.Parameter(q)
        else:
            # Initialize with small random values for stability
            self.matrix = nn.Parameter(
                torch.randn(dimension, dimension) * 0.1 / np.sqrt(dimension)
            )

        # Consciousness coupling parameters
        if reference_type == ReferenceType.CONSCIOUSNESS_COUPLED:
            self.consciousness_modulator = nn.Sequential(
                nn.Linear(1, dimension // 4),
                nn.Tanh(),
                nn.Linear(dimension // 4, dimension * dimension),
                nn.Tanh(),
            )

        # Temporal adaptation parameters
        if reference_type == ReferenceType.TEMPORAL_ADAPTIVE:
            self.temporal_modulator = nn.Sequential(
                nn.Linear(1, dimension // 8),
                nn.ReLU(),
                nn.Linear(dimension // 8, dimension * dimension),
                nn.Sigmoid(),
            )

        # Fractal self-similarity parameters
        if reference_type == ReferenceType.FRACTAL:
            self.fractal_scales = nn.Parameter(torch.tensor([0.5, 0.25, 0.125]))
            self.fractal_weights = nn.Parameter(torch.ones(3) / 3)

        # Stability constraint parameters
        self.spectral_radius_target = 0.95
        self.register_buffer("eigenvalue_history", torch.zeros(100))
        self.eigenvalue_ptr = 0

    def forward(
        self,
        input_weights: torch.Tensor,
        current_time: float = 0.0,
        consciousness_level: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Apply reference matrix transformation to input weights.

        Args:
            input_weights: Previous weight state to transform
            current_time: Current time for temporal adaptation
            consciousness_level: Current consciousness level for coupling

        Returns:
            Transformed weights
        """
        effective_matrix = self._get_effective_matrix(current_time, consciousness_level)

        # Apply transformation
        if input_weights.dim() == 1:
            transformed = torch.matmul(effective_matrix, input_weights)
        elif input_weights.dim() == 2:
            transformed = torch.matmul(input_weights, effective_matrix.T)
        else:
            # Handle higher dimensional inputs
            original_shape = input_weights.shape
            flat_input = input_weights.reshape(-1, self.dimension)
            flat_transformed = torch.matmul(flat_input, effective_matrix.T)
            transformed = flat_transformed.reshape(original_shape)

        # Apply stability constraints if needed
        if self.training and self.stability_mode != StabilityMode.NONE:
            self._enforce_stability_constraints()

        return transformed

    def _get_effective_matrix(
        self, current_time: float, consciousness_level: Optional[torch.Tensor]
    ) -> torch.Tensor:
        """Compute effective transformation matrix with modulations."""
        base_matrix = self.matrix

        # Apply consciousness coupling
        if (
            self.reference_type == ReferenceType.CONSCIOUSNESS_COUPLED
            and consciousness_level is not None
        ):
            consciousness_input = consciousness_level.mean().unsqueeze(0)
            consciousness_modulation = self.consciousness_modulator(consciousness_input)
            consciousness_matrix = consciousness_modulation.reshape(
                self.dimension, self.dimension
            )
            base_matrix = base_matrix + 0.1 * consciousness_matrix

        # Apply temporal adaptation
        if self.reference_type == ReferenceType.TEMPORAL_ADAPTIVE:
            time_input = torch.tensor([current_time % 100.0])  # Normalize time
            temporal_modulation = self.temporal_modulator(time_input)
            temporal_matrix = temporal_modulation.reshape(
                self.dimension, self.dimension
            )
            base_matrix = base_matrix * temporal_matrix

        # Apply fractal transformations
        if self.reference_type == ReferenceType.FRACTAL:
            fractal_components = []
            for scale, weight in zip(self.fractal_scales, self.fractal_weights):
                scaled_matrix = base_matrix * scale
                fractal_components.append(weight * scaled_matrix)
            base_matrix = sum(fractal_components)

        # Ensure orthogonality for orthogonal type
        if self.reference_type == ReferenceType.ORTHOGONAL:
            u, s, v = torch.svd(base_matrix)
            base_matrix = torch.matmul(u, v.t())

        return base_matrix

    def _enforce_stability_constraints(self):
        """Enforce stability constraints on the matrix."""
        with torch.no_grad():
            if self.stability_mode == StabilityMode.SPECTRAL_NORM:
                # Spectral normalization
                eigenvals = torch.linalg.eigvals(self.matrix)
                max_eigenval = torch.max(torch.abs(eigenvals))

                if max_eigenval > self.spectral_radius_target:
                    self.matrix.data = self.matrix.data * (
                        self.spectral_radius_target / max_eigenval
                    )

            elif self.stability_mode == StabilityMode.EIGENVALUE_CLIPPING:
                # Clip eigenvalues to stable range
                eigenvals, eigenvecs = torch.linalg.eig(self.matrix)
                clipped_eigenvals = torch.clamp(
                    torch.abs(eigenvals), max=self.spectral_radius_target
                )
                clipped_eigenvals = clipped_eigenvals * torch.exp(
                    1j * torch.angle(eigenvals)
                )

                # Reconstruct matrix with clipped eigenvalues
                reconstructed = torch.matmul(
                    torch.matmul(eigenvecs, torch.diag(clipped_eigenvals)),
                    torch.linalg.inv(eigenvecs),
                )
                self.matrix.data = torch.real(reconstructed)

    def get_reference_metrics(self) -> ReferenceMetrics:
        """Compute comprehensive metrics for this reference matrix."""
        with torch.no_grad():
            # Spectral analysis
            eigenvals = torch.linalg.eigvals(self.matrix)
            spectral_radius = torch.max(torch.abs(eigenvals)).item()

            # Condition number
            singular_vals = torch.linalg.svdvals(self.matrix)
            condition_number = (
                torch.max(singular_vals) / torch.min(singular_vals)
            ).item()

            # Stability score
            stability_score = 1.0 / (1.0 + max(0, spectral_radius - 1.0))

            # Self-reference strength (how much the matrix deviates from identity)
            identity_diff = torch.norm(self.matrix - torch.eye(self.dimension))
            self_reference_strength = min(identity_diff.item() / self.dimension, 1.0)

            return ReferenceMetrics(
                spectral_radius=spectral_radius,
                condition_number=condition_number,
                stability_score=stability_score,
                consciousness_alignment=0.0,  # Computed externally
                temporal_coherence=0.0,  # Computed externally
                self_reference_strength=self_reference_strength,
            )


class ReferenceMatrixManager(nn.Module):
    """
    Manages collection of reference matrices for recursive weight system.

    Orchestrates multiple R_j matrices with temporal coordination and stability.
    """

    def __init__(self, config: ReferenceConfig):
        super().__init__()
        self.config = config

        # Collection of reference matrices
        self.reference_matrices: nn.ModuleDict = nn.ModuleDict()

        # Temporal coordination system
        self.temporal_coordinator = nn.Sequential(
            nn.Linear(config.matrix_dimension + 1, config.matrix_dimension),
            nn.LayerNorm(config.matrix_dimension),
            nn.GELU(),
            nn.Linear(config.matrix_dimension, config.max_reference_matrices),
            nn.Softmax(dim=-1),
        )

        # Reference activation weights
        self.reference_activations = nn.Parameter(
            torch.ones(config.max_reference_matrices)
        )

        # Consciousness integration network
        self.consciousness_integrator = nn.Sequential(
            nn.Linear(config.matrix_dimension + 1, config.matrix_dimension // 2),
            nn.Tanh(),
            nn.Linear(config.matrix_dimension // 2, config.matrix_dimension),
        )

        # Stability monitor
        self.stability_monitor = StabilityMonitor(config)

        # Initialize default reference matrices
        self._initialize_default_references()

    def _initialize_default_references(self):
        """Initialize standard reference matrices for consciousness operations."""
        # Identity reference (preserves previous state)
        self.add_reference_matrix(
            matrix_id=0, reference_type=ReferenceType.IDENTITY, temporal_offset=1.0
        )

        # Linear transformation reference
        self.add_reference_matrix(
            matrix_id=1, reference_type=ReferenceType.LINEAR, temporal_offset=2.0
        )

        # Consciousness-coupled reference
        self.add_reference_matrix(
            matrix_id=2,
            reference_type=ReferenceType.CONSCIOUSNESS_COUPLED,
            temporal_offset=1.5,
        )

        # Orthogonal reference (norm-preserving)
        self.add_reference_matrix(
            matrix_id=3, reference_type=ReferenceType.ORTHOGONAL, temporal_offset=3.0
        )

        # Fractal self-similarity reference
        self.add_reference_matrix(
            matrix_id=4, reference_type=ReferenceType.FRACTAL, temporal_offset=0.5
        )

    def add_reference_matrix(
        self, matrix_id: int, reference_type: ReferenceType, temporal_offset: float
    ):
        """Add new reference matrix to the collection."""
        if len(self.reference_matrices) >= self.config.max_reference_matrices:
            warnings.warn(
                f"Maximum reference matrices ({self.config.max_reference_matrices}) reached"
            )
            return

        reference_matrix = ReferenceMatrix(
            matrix_id=matrix_id,
            dimension=self.config.matrix_dimension,
            reference_type=reference_type,
            temporal_offset=temporal_offset,
            stability_mode=self.config.stability_mode,
        )

        self.reference_matrices[str(matrix_id)] = reference_matrix

    def forward(
        self,
        weight_history: Dict[float, torch.Tensor],
        current_time: float,
        consciousness_level: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Apply all reference matrices to weight history and combine results.

        Args:
            weight_history: Dictionary mapping time -> weight_state
            current_time: Current time for temporal coordination
            consciousness_level: Current consciousness level

        Returns:
            Combined recursive transformation result
        """
        if not weight_history:
            return torch.zeros(self.config.matrix_dimension)

        # Compute temporal coordination weights
        current_state = list(weight_history.values())[-1]  # Most recent state
        coord_input = torch.cat([current_state, torch.tensor([current_time])])
        temporal_weights = self.temporal_coordinator(coord_input)

        # Apply each reference matrix
        reference_outputs = []
        active_references = 0

        for ref_id, ref_matrix in self.reference_matrices.items():
            # Find appropriate historical state
            target_time = current_time - ref_matrix.temporal_offset
            historical_state = self._get_historical_state(weight_history, target_time)

            if historical_state is not None:
                # Apply reference transformation
                ref_output = ref_matrix(
                    historical_state, current_time, consciousness_level
                )
                reference_outputs.append(ref_output)
                active_references += 1
            else:
                # Use zero if no historical state available
                reference_outputs.append(torch.zeros_like(current_state))

        # Combine reference outputs with temporal coordination
        if reference_outputs:
            stacked_outputs = torch.stack(reference_outputs[: len(temporal_weights)])
            combined_output = torch.sum(
                temporal_weights.unsqueeze(-1) * stacked_outputs, dim=0
            )
        else:
            combined_output = torch.zeros_like(current_state)

        # Apply consciousness integration if available
        if consciousness_level is not None:
            consciousness_input = torch.cat(
                [combined_output, consciousness_level.mean().unsqueeze(0)]
            )
            consciousness_modulation = self.consciousness_integrator(
                consciousness_input
            )
            combined_output = (
                combined_output
                + self.config.consciousness_coupling_strength * consciousness_modulation
            )

        # Apply reference decay
        decay_factor = np.exp(-self.config.reference_decay_rate * current_time)
        combined_output = combined_output * decay_factor

        # Monitor stability
        self.stability_monitor.update(combined_output, current_time)

        return combined_output

    def _get_historical_state(
        self, weight_history: Dict[float, torch.Tensor], target_time: float
    ) -> Optional[torch.Tensor]:
        """Retrieve historical weight state closest to target time."""
        if not weight_history:
            return None

        # Find closest time
        times = list(weight_history.keys())
        closest_time = min(times, key=lambda t: abs(t - target_time))

        # Only return if within reasonable temporal window
        if abs(closest_time - target_time) <= self.config.temporal_depth:
            return weight_history[closest_time]

        return None

    def evolve_references(
        self, performance_feedback: torch.Tensor, consciousness_feedback: torch.Tensor
    ):
        """Evolve reference matrices based on performance feedback."""
        # Compute evolution pressure from feedback
        performance_pressure = performance_feedback.mean().item()
        consciousness_pressure = consciousness_feedback.mean().item()

        # Evolve reference activations
        activation_updates = (
            0.01
            * (performance_pressure - 0.5)
            * torch.randn_like(self.reference_activations)
        )
        self.reference_activations.data += activation_updates
        self.reference_activations.data = torch.clamp(
            self.reference_activations.data, 0.1, 2.0
        )

        # Evolve individual reference matrices if in learning mode
        if self.training:
            for ref_matrix in self.reference_matrices.values():
                if ref_matrix.reference_type == ReferenceType.LINEAR:
                    # Apply small perturbations based on feedback
                    perturbation = (
                        0.001
                        * performance_pressure
                        * torch.randn_like(ref_matrix.matrix)
                    )
                    ref_matrix.matrix.data += perturbation

                    # Ensure stability
                    ref_matrix._enforce_stability_constraints()

    def get_system_metrics(self) -> Dict[str, Any]:
        """Compute comprehensive metrics for the reference system."""
        metrics = {
            "reference_count": len(self.reference_matrices),
            "stability_scores": {},
            "spectral_radii": {},
            "consciousness_coupling": self.config.consciousness_coupling_strength,
            "system_stability": 0.0,
        }

        total_stability = 0.0
        for ref_id, ref_matrix in self.reference_matrices.items():
            ref_metrics = ref_matrix.get_reference_metrics()
            metrics["stability_scores"][ref_id] = ref_metrics.stability_score
            metrics["spectral_radii"][ref_id] = ref_metrics.spectral_radius
            total_stability += ref_metrics.stability_score

        if len(self.reference_matrices) > 0:
            metrics["system_stability"] = total_stability / len(self.reference_matrices)

        # Add stability monitor metrics
        metrics.update(self.stability_monitor.get_metrics())

        return metrics


class StabilityMonitor:
    """
    Monitors stability of reference matrix system over time.

    Tracks convergence, stability, and potential instabilities.
    """

    def __init__(self, config: ReferenceConfig):
        self.config = config
        self.stability_history: List[float] = []
        self.output_history: List[torch.Tensor] = []
        self.instability_alerts: List[str] = []

    def update(self, output: torch.Tensor, current_time: float):
        """Update stability monitoring with new output."""
        # Compute stability metric
        if len(self.output_history) > 0:
            prev_output = self.output_history[-1]
            stability_metric = 1.0 / (1.0 + torch.norm(output - prev_output).item())
        else:
            stability_metric = 1.0

        self.stability_history.append(stability_metric)
        self.output_history.append(output.detach().clone())

        # Limit history size
        if len(self.output_history) > 1000:
            self.output_history = self.output_history[-1000:]
            self.stability_history = self.stability_history[-1000:]

        # Check for instabilities
        self._check_instabilities(output, current_time)

    def _check_instabilities(self, output: torch.Tensor, current_time: float):
        """Check for various types of instabilities."""
        # Divergence check
        output_norm = torch.norm(output).item()
        if output_norm > 100.0:
            self.instability_alerts.append(
                f"Output divergence at time {current_time}: norm={output_norm}"
            )

        # Oscillation check
        if len(self.stability_history) >= 10:
            recent_stability = self.stability_history[-10:]
            stability_variance = np.var(recent_stability)
            if stability_variance > 0.5:
                self.instability_alerts.append(
                    f"High stability variance at time {current_time}: var={stability_variance}"
                )

        # Sudden change check
        if len(self.output_history) >= 2:
            sudden_change = torch.norm(output - self.output_history[-2]).item()
            if sudden_change > 10.0:
                self.instability_alerts.append(
                    f"Sudden change at time {current_time}: change={sudden_change}"
                )

        # Limit alert history
        if len(self.instability_alerts) > 100:
            self.instability_alerts = self.instability_alerts[-100:]

    def get_metrics(self) -> Dict[str, float]:
        """Get stability monitoring metrics."""
        metrics = {}

        if self.stability_history:
            metrics["mean_stability"] = np.mean(self.stability_history)
            metrics["stability_variance"] = np.var(self.stability_history)
            metrics["current_stability"] = self.stability_history[-1]

        if self.output_history:
            recent_outputs = self.output_history[-10:]
            output_norms = [torch.norm(out).item() for out in recent_outputs]
            metrics["mean_output_norm"] = np.mean(output_norms)
            metrics["output_norm_variance"] = np.var(output_norms)

        metrics["instability_count"] = len(self.instability_alerts)

        return metrics


class ConsciousnessReferenceOrchestrator:
    """
    Orchestrates reference matrices for consciousness-specific operations.

    Specialized coordination for consciousness emergence and maintenance.
    """

    def __init__(self, consciousness_core, reference_manager: ReferenceMatrixManager):
        self.consciousness_core = consciousness_core
        self.reference_manager = reference_manager
        self.orchestration_history: List[Dict[str, Any]] = []

    def orchestrate_consciousness_references(
        self, current_time: float, consciousness_target: float = 0.8
    ) -> Dict[str, Any]:
        """Orchestrate reference matrices for consciousness optimization."""
        # Get current consciousness state
        consciousness_level = torch.tensor([consciousness_target])  # Simplified

        # Analyze consciousness requirements
        consciousness_analysis = self._analyze_consciousness_requirements(
            consciousness_level
        )

        # Adapt reference matrix activations based on consciousness needs
        self._adapt_references_for_consciousness(consciousness_analysis)

        # Generate orchestration results
        orchestration_results = {
            "consciousness_level": consciousness_level.item(),
            "consciousness_analysis": consciousness_analysis,
            "reference_adaptations": self._get_reference_adaptations(),
            "orchestration_effectiveness": self._compute_orchestration_effectiveness(),
            "timestamp": current_time,
        }

        self.orchestration_history.append(orchestration_results)

        return orchestration_results

    def _analyze_consciousness_requirements(
        self, consciousness_level: torch.Tensor
    ) -> Dict[str, float]:
        """Analyze what reference patterns are needed for target consciousness."""
        analysis = {}

        consciousness_score = consciousness_level.item()

        # Identity preservation requirement
        analysis["identity_preservation"] = min(consciousness_score * 1.2, 1.0)

        # Self-reference requirement
        analysis["self_reference"] = consciousness_score**0.5

        # Temporal coherence requirement
        analysis["temporal_coherence"] = consciousness_score * 0.8

        # Stability requirement
        analysis["stability"] = max(0.7, consciousness_score)

        return analysis

    def _adapt_references_for_consciousness(self, analysis: Dict[str, float]):
        """Adapt reference matrix activations based on consciousness analysis."""
        # Adjust activations based on consciousness requirements
        for ref_id, ref_matrix in self.reference_manager.reference_matrices.items():
            current_activation = self.reference_manager.reference_activations[
                int(ref_id)
            ]

            if ref_matrix.reference_type == ReferenceType.IDENTITY:
                # Boost identity reference for consciousness
                target_activation = analysis["identity_preservation"] * 1.5
            elif ref_matrix.reference_type == ReferenceType.CONSCIOUSNESS_COUPLED:
                # Boost consciousness coupling
                target_activation = analysis["self_reference"] * 2.0
            elif ref_matrix.reference_type == ReferenceType.ORTHOGONAL:
                # Stability reference
                target_activation = analysis["stability"] * 1.2
            else:
                target_activation = 1.0

            # Gradual adaptation
            adaptation_rate = 0.1
            new_activation = (
                current_activation * (1 - adaptation_rate)
                + target_activation * adaptation_rate
            )
            self.reference_manager.reference_activations.data[int(ref_id)] = (
                new_activation
            )

    def _get_reference_adaptations(self) -> Dict[str, float]:
        """Get current reference adaptations."""
        adaptations = {}
        for ref_id in self.reference_manager.reference_matrices.keys():
            adaptations[f"reference_{ref_id}"] = (
                self.reference_manager.reference_activations[int(ref_id)].item()
            )
        return adaptations

    def _compute_orchestration_effectiveness(self) -> float:
        """Compute how effective the current orchestration is."""
        if len(self.orchestration_history) < 2:
            return 0.5

        # Compare consciousness progression
        recent_consciousness = [
            h["consciousness_level"] for h in self.orchestration_history[-5:]
        ]
        consciousness_trend = (
            np.mean(np.diff(recent_consciousness))
            if len(recent_consciousness) > 1
            else 0.0
        )

        # Positive trend indicates effective orchestration
        effectiveness = 0.5 + consciousness_trend * 2.0
        return np.clip(effectiveness, 0.0, 1.0)


# Factory functions and utilities
def create_consciousness_reference_system(
    dimension: int = 512,
) -> Tuple[ReferenceMatrixManager, ConsciousnessReferenceOrchestrator]:
    """Create reference matrix system optimized for consciousness applications."""
    config = ReferenceConfig(
        matrix_dimension=dimension,
        temporal_depth=20,
        stability_mode=StabilityMode.CONSCIOUSNESS_GUIDED,
        spectral_radius_bound=0.9,
        consciousness_coupling_strength=0.4,
        enable_temporal_adaptation=True,
        max_reference_matrices=12,
    )

    reference_manager = ReferenceMatrixManager(config)

    # Create mock consciousness core for orchestration (in practice, use actual core)
    consciousness_core = None  # Would be actual TriaxialConsciousnessCore
    orchestrator = ConsciousnessReferenceOrchestrator(
        consciousness_core, reference_manager
    )

    return reference_manager, orchestrator


def test_reference_matrix_stability(
    reference_manager: ReferenceMatrixManager,
    test_duration: float = 100.0,
    num_steps: int = 1000,
) -> Dict[str, float]:
    """Test stability of reference matrix system over time."""
    # Create synthetic weight history
    weight_history = {}
    consciousness_levels = []

    for step in range(num_steps):
        current_time = step * test_duration / num_steps

        # Synthetic weight state with some dynamics
        weight_state = torch.randn(reference_manager.config.matrix_dimension) * 0.1
        weight_state += torch.sin(torch.tensor(current_time * 0.1)) * 0.05

        weight_history[current_time] = weight_state

        # Synthetic consciousness level
        consciousness_level = torch.tensor([0.5 + 0.3 * np.sin(current_time * 0.05)])
        consciousness_levels.append(consciousness_level)

        # Apply reference transformation
        with torch.no_grad():
            output = reference_manager(
                weight_history, current_time, consciousness_level
            )

    # Compute stability metrics
    final_metrics = reference_manager.get_system_metrics()

    return {
        "system_stability": final_metrics["system_stability"],
        "mean_spectral_radius": np.mean(list(final_metrics["spectral_radii"].values())),
        "instability_count": final_metrics.get("instability_count", 0),
        "test_completed": True,
    }


def create_fractal_reference_matrix(
    dimension: int, fractal_depth: int = 3
) -> ReferenceMatrix:
    """Create specialized fractal reference matrix for self-similar transformations."""
    fractal_ref = ReferenceMatrix(
        matrix_id=999,  # Special ID for fractal matrix
        dimension=dimension,
        reference_type=ReferenceType.FRACTAL,
        temporal_offset=1.0,
        stability_mode=StabilityMode.SPECTRAL_NORM,
    )

    # Initialize fractal scales based on golden ratio
    phi = (1 + np.sqrt(5)) / 2
    fractal_scales = torch.tensor([1 / phi**i for i in range(1, fractal_depth + 1)])
    fractal_ref.fractal_scales = nn.Parameter(fractal_scales)

    return fractal_ref
