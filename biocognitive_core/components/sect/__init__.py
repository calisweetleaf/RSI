# src/biocognitive_core/components/sect/__init__.py
"""
Self-Evolving Cognitive Therapist (SECT) Component

This package implements the SECT component of the biocognitive framework,
which provides AI agents with recursive self-improvement capacities
specifically tailored to mental health optimization.
"""

from .agent import (
    CognitiveProcessingMode,
    RecursionLevel,
    CognitiveState,
    CognitiveStateDifferential,
    TherapeuticIntervention,
    CognitiveReframing,
    EmotionalRegulation,
    URSMIFContradictionIntervention,
    AdaptiveInterventionManager,
    SECTAgent,
    ModificationPlan
)
from .ursmif_sentinel import (
    URSMIFContradictionSentinel,
    ContradictionSignal,
)

from .therapy import (
    TherapyModality,
    SessionStage,
    TherapeuticGoal,
    TherapeuticSession,
    TherapeuticProfile,
    CognitiveTherapist,
    TherapyPhase
)

try:
    from infrastructure.ethical_tensor import (
        ETHICAL_DIMENSIONS,
        BreathPhase,
        NarrativeArchetype,
        QuantumBreathAdapter,
        SymbolicQuantumState,
        CollapseAdapter,
        EthicalTensorFactory,
        create_ethical_tensor,
        apply_ethical_force,
        analyze_ethical_distribution,
    )
    _ETHICS_AVAILABLE = True
except ImportError:
    _ETHICS_AVAILABLE = False

__all__ = [
    # From agent.py
    'CognitiveProcessingMode',
    'RecursionLevel',
    'CognitiveState',
    'CognitiveStateDifferential',
    'TherapeuticIntervention',
    'CognitiveReframing',
    'EmotionalRegulation',
    'URSMIFContradictionIntervention',
    'AdaptiveInterventionManager',
    'SECTAgent',
    'ModificationPlan',

    # From therapy.py
    'TherapyModality',
    'SessionStage',
    'TherapeuticGoal',
    'TherapeuticSession',
    'TherapeuticProfile',
    'CognitiveTherapist',
    'TherapyPhase',
    'URSMIFContradictionSentinel',
    'ContradictionSignal',
]

if _ETHICS_AVAILABLE:
    __all__.extend([
        'ETHICAL_DIMENSIONS',
        'BreathPhase',
        'NarrativeArchetype',
        'QuantumBreathAdapter',
        'SymbolicQuantumState',
        'CollapseAdapter',
        'EthicalTensorFactory',
        'create_ethical_tensor',
        'apply_ethical_force',
        'analyze_ethical_distribution',
    ])

import logging
import os

# Package initialization
def initialize_sect() -> bool:
    """Initialize SECT component and verify correct setup when requested."""
    from biocognitive_core.metrics import SECTMetrics
    metrics = SECTMetrics()
    if hasattr(metrics, "register_metrics"):
        metrics.register_metrics()

    try:
        from biocognitive_core import config as config_module
        validator = getattr(config_module, "validate_sect_config", None)
        if callable(validator):
            validator()
    except Exception as exc:
        logging.getLogger(__name__).warning(
            "SECT configuration validation skipped: %s", exc
        )

    return True


def _maybe_initialize() -> None:
    if os.getenv("BIOC_SECT_VALIDATE_IMPORT", "").lower() not in {"1", "true", "yes"}:
        return
    try:
        initialize_sect()
    except Exception as exc:
        logging.getLogger(__name__).critical(
            "Failed to initialize SECT component: %s", exc
        )
        raise RuntimeError(
            "Self-Evolving Cognitive Therapist initialization failed"
        ) from exc


_maybe_initialize()
