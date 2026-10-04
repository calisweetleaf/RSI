# src/integration/coordinator.py
"""
Biocognitive System Coordinator

Orchestrates cross-system integration between SIS, NTP, and SECT components.
Manages state synchronization, emergent property detection, and boundary enforcement.

Author: Morpheus
Date: 2025-05-08
Version: 1.0.0
"""

import asyncio
import logging
import math
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import numpy as np
from pydantic import BaseModel, Field, validator

from biocognitive_core.config import settings
from biocognitive_core.exceptions import BiocognitiveError

# Initialize module logger
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Enums and Event Types
# -----------------------------------------------------------------------------

class EventType(Enum):
    """Types of biocognitive events"""
    STATE_CHANGE = auto()
    BOUNDARY_CROSSING = auto()
    IDENTITY_FLUCTUATION = auto()
    EMERGENT_PROPERTY = auto()
    SYNC_COMPLETE = auto()
    SYSTEM_ALERT = auto()
    COHERENCE_UPDATE = auto()


class EventPriority(Enum):
    """Priority levels for events"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


# -----------------------------------------------------------------------------
# Data Models
# -----------------------------------------------------------------------------

@dataclass
class BiocognitiveEvent:
    """Event structure for cross-system communication"""
    type: EventType
    priority: EventPriority
    source_system: str
    target_system: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    event_id: UUID = field(default_factory=uuid4)


@dataclass
class StateSnapshot:
    """Snapshot of system state at a point in time"""
    timestamp: datetime
    sis_state: Dict[str, Any]
    ntp_state: Dict[str, Any]
    sect_state: Dict[str, Any]
    boundary_integrity: float
    identity_coherence: float
    emergent_properties: Dict[str, float]
    snapshot_id: UUID = field(default_factory=uuid4)


@dataclass
class CognitiveIntervention:
    """Represents a cognitive intervention to be applied"""
    primary_domain: str
    target_emotions: Dict[str, float]
    thought_adjustments: Dict[str, float]
    priority: float
    duration_seconds: int = 300
    metadata: Dict[str, Any] = field(default_factory=dict)


# -----------------------------------------------------------------------------
# Event Bus
# -----------------------------------------------------------------------------

class EventBus:
    """Asynchronous event bus for cross-system communication"""

    def __init__(self):
        self.subscribers: Dict[EventType, List[callable]] = defaultdict(list)
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.running = False
        self._process_task: Optional[asyncio.Task] = None

    def subscribe(self, event_type: EventType, handler: callable) -> None:
        """Subscribe a handler to an event type"""
        self.subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: EventType, handler: callable) -> None:
        """Unsubscribe a handler from an event type"""
        if handler in self.subscribers[event_type]:
            self.subscribers[event_type].remove(handler)

    async def publish(self, event: BiocognitiveEvent) -> None:
        """Publish an event to the bus"""
        await self.event_queue.put(event)

    async def start(self) -> None:
        """Start the event processing loop"""
        self.running = True
        self._process_task = asyncio.create_task(self._process_events())

    async def _process_events(self) -> None:
        """Process events from the queue"""
        while self.running:
            try:
                event = await asyncio.wait_for(self.event_queue.get(), timeout=1.0)
                handlers = self.subscribers.get(event.type, [])
                for handler in handlers:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(event)
                        else:
                            handler(event)
                    except Exception as e:
                        logger.error(f"Error in event handler: {e}")
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing event: {e}")

    async def shutdown(self) -> None:
        """Shutdown the event bus"""
        self.running = False
        if self._process_task:
            self._process_task.cancel()
            try:
                await self._process_task
            except asyncio.CancelledError:
                pass


# -----------------------------------------------------------------------------
# Helper Functions for Logging
# -----------------------------------------------------------------------------

def log_error(message: str, error: Exception) -> None:
    """Log an error with context"""
    logger.error(f"{message}: {error}")


def log_event(event_type: str, metadata: Dict[str, Any]) -> None:
    """Log an event with metadata"""
    logger.info(f"Event: {event_type} - {metadata}")


def log_metrics(name: str, metrics: Dict[str, Any]) -> None:
    """Log metrics"""
    logger.debug(f"Metrics [{name}]: {metrics}")


def trace_operation(operation_name: str):
    """Decorator for tracing operations"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                logger.debug(f"Operation {operation_name} completed in {duration*1000:.2f}ms")
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"Operation {operation_name} failed after {duration*1000:.2f}ms: {e}")
                raise
        return wrapper
    return decorator


# -----------------------------------------------------------------------------
# Biocognitive Coordinator
# -----------------------------------------------------------------------------

class BiocognitiveCoordinator:
    """
    Central coordinator for the biocognitive system.
    
    Manages state synchronization between SIS, NTP, and SECT systems,
    detects emergent properties, and enforces system boundaries.
    """

    def __init__(self, sis, ntp, sect):
        """
        Initialize the coordinator with system references.
        
        Args:
            sis: Synthetic Immune Symbiont system
            ntp: Neural Transparency Protocol system
            sect: Self-Evolving Cognitive Therapist system
        """
        self.sis = sis
        self.ntp = ntp
        self.sect = sect
        self.event_bus = EventBus()
        self.coordination_metrics = IntegrationMetrics()
        self.state_history: List[StateSnapshot] = []
        self.last_snapshot: Optional[StateSnapshot] = None
        self.sync_task: Optional[asyncio.Task] = None
        self.identity_coherence_threshold = settings.integration.min_identity_coherence
        self.sync_interval = settings.integration.sync_interval.total_seconds()

    async def synchronize_states(self) -> None:
        """Main synchronization loop for cross-system state coordination"""
        while True:
            try:
                # Gather current states from all systems
                sis_state = await self.sis.get_health_snapshot()
                ntp_context = await self.ntp.get_current_context()
                sect_status = await self.sect.get_therapy_status()

                # Create unified snapshot
                snapshot = await self._create_state_snapshot(
                    sis_state, ntp_context, sect_status
                )

                # Store in history
                self.state_history.append(snapshot)
                if len(self.state_history) > 1000:
                    self.state_history = self.state_history[-500:]

                # Reconcile any state differences
                changes = await self._reconcile_states(snapshot)

                # Publish sync complete event
                if changes > 0:
                    await self.event_bus.publish(BiocognitiveEvent(
                        type=EventType.SYNC_COMPLETE,
                        priority=EventPriority.LOW,
                        source_system="coordinator",
                        target_system="all",
                        payload={"changes_made": changes}
                    ))

                # Check identity coherence
                await self._check_identity_coherence()

            except Exception as e:
                logger.error(f"Error in state synchronization: {e}")
                log_error(f"State sync error", error=e)

            await asyncio.sleep(self.sync_interval)

    async def _create_state_snapshot(
        self,
        sis_state: Dict,
        ntp_context: Dict,
        sect_status: Dict
    ) -> StateSnapshot:
        """Create a unified state snapshot from all system states"""
        # Calculate boundary integrity
        boundary_integrity = self._calculate_boundary_integrity(
            sis_state, ntp_context, sect_status
        )

        # Calculate identity coherence
        identity_coherence = self._calculate_identity_coherence(
            sis_state, ntp_context, sect_status
        )

        # Detect emergent properties
        emergent_properties = self._detect_emergent_properties(
            sis_state, ntp_context, sect_status
        )

        return StateSnapshot(
            timestamp=datetime.utcnow(),
            sis_state=sis_state,
            ntp_state=ntp_context,
            sect_state=sect_status,
            boundary_integrity=boundary_integrity,
            identity_coherence=identity_coherence,
            emergent_properties=emergent_properties
        )

    def _calculate_boundary_integrity(
        self,
        sis_state: Dict,
        ntp_context: Dict,
        sect_status: Dict
    ) -> float:
        """Calculate overall system boundary integrity"""
        sis_integrity = sis_state.get('barrier_integrity', 0.8)
        ntp_integrity = ntp_context.get('boundary_score', 0.8)
        sect_integrity = sect_status.get('therapeutic_boundaries', 0.8)

        # Weighted average with emphasis on immune boundaries
        return (
            sis_integrity * 0.4 +
            ntp_integrity * 0.3 +
            sect_integrity * 0.3
        )

    def _calculate_identity_coherence(
        self,
        sis_state: Dict,
        ntp_context: Dict,
        sect_status: Dict
    ) -> float:
        """Calculate identity coherence across systems"""
        sis_coherence = sis_state.get('identity_markers', 0.7)
        ntp_coherence = ntp_context.get('self_model_integrity', 0.7)
        sect_coherence = sect_status.get('narrative_coherence', 0.7)

        # Harmonic mean for better sensitivity to low values
        coherence_values = [sis_coherence, ntp_coherence, sect_coherence]
        if all(v > 0 for v in coherence_values):
            return len(coherence_values) / sum(1/v for v in coherence_values)
        return min(coherence_values)

    def _detect_emergent_properties(
        self,
        sis_state: Dict,
        ntp_context: Dict,
        sect_status: Dict
    ) -> Dict[str, float]:
        """Detect emergent properties from cross-system interactions"""
        emergent = {}

        # Detect coherent oscillation pattern
        neural_rhythm = ntp_context.get('dominant_rhythm', 0)
        immune_cycle = sis_state.get('circadian_phase', 0)
        cognitive_rhythm = sect_status.get('attention_rhythm', 0)

        if abs(neural_rhythm - immune_cycle) < 0.2 and abs(immune_cycle - cognitive_rhythm) < 0.2:
            emergent['coherent_oscillation'] = 1.0 - abs(neural_rhythm - cognitive_rhythm)

        # Detect cross-domain learning acceleration
        cognitive_learning = sect_status.get('learning_coefficient', 0)
        immune_adaptation = sis_state.get('adaptation_rate', 0)
        if cognitive_learning > 0.6 and immune_adaptation > 0.6:
            synergy_factor = math.sqrt(cognitive_learning * immune_adaptation)
            emergent['accelerated_learning'] = min(0.95, synergy_factor * 1.2)

        # Detect embodied cognition enhancement
        if (sis_state.get('cellular_intelligence', 0) > 0.65 and
            ntp_context.get('embodiment_index', 0) > 0.7):
            embodiment_factor = (
                sis_state.get('cellular_intelligence', 0) * 0.4 +
                ntp_context.get('embodiment_index', 0) * 0.6
            )
            emergent['enhanced_embodied_cognition'] = embodiment_factor

        # Detect collective intelligence emergence
        system_entrainment = (
            sis_state.get('network_synchronization', 0) * 0.3 +
            ntp_context.get('harmonic_resonance', 0) * 0.4 +
            sect_status.get('therapeutic_resonance', 0) * 0.3
        )
        if system_entrainment > 0.75:
            emergent['collective_intelligence'] = system_entrainment

        # Detect homeostatic transcendence (rare emergent property)
        homeostatic_factors = [
            sis_state.get('homeostatic_resilience', 0),
            ntp_context.get('adaptive_capacity', 0),
            sect_status.get('transformative_potential', 0)
        ]
        if all(factor > 0.8 for factor in homeostatic_factors):
            transcendence_level = sum(homeostatic_factors) / 3 - 0.7
            emergent['homeostatic_transcendence'] = min(0.99, transcendence_level * 3)

        # Calculate emergent resilience metric
        resilience_components = {
            'immune_resilience': sis_state.get('system_resilience', 0),
            'neural_resilience': ntp_context.get('network_resilience', 0),
            'cognitive_resilience': sect_status.get('therapeutic_resilience', 0)
        }

        # Apply non-linear resilience emergence formula
        if all(value > 0.4 for value in resilience_components.values()):
            base_resilience = sum(resilience_components.values()) / 3
            coupling_factor = min(
                abs(resilience_components['immune_resilience'] - resilience_components['neural_resilience']),
                abs(resilience_components['neural_resilience'] - resilience_components['cognitive_resilience']),
                abs(resilience_components['cognitive_resilience'] - resilience_components['immune_resilience'])
            )
            emergent['systemic_resilience'] = base_resilience * (1.0 + (1.0 - coupling_factor) * 0.5)

        return emergent

    async def _reconcile_states(self, snapshot: StateSnapshot) -> int:
        """Reconcile states between systems and propagate necessary changes"""
        changes_made = 0
        try:
            # Skip if this is the first snapshot
            if not self.last_snapshot:
                self.last_snapshot = snapshot
                return 0

            # Calculate delta from previous state
            sis_delta = self._calculate_state_delta(
                self.last_snapshot.sis_state, snapshot.sis_state
            )
            ntp_delta = self._calculate_state_delta(
                self.last_snapshot.ntp_state, snapshot.ntp_state
            )
            sect_delta = self._calculate_state_delta(
                self.last_snapshot.sect_state, snapshot.sect_state
            )

            # Check if any system requires updates due to changes in other systems
            if self._requires_immune_update(ntp_delta, sect_delta):
                await self._update_immune_system(snapshot)
                changes_made += 1

            if self._requires_neural_update(sis_delta, sect_delta):
                await self._update_neural_system(snapshot)
                changes_made += 1

            if self._requires_cognitive_update(sis_delta, ntp_delta):
                await self._update_cognitive_system(snapshot)
                changes_made += 1

            # Check for boundary violations
            if snapshot.boundary_integrity < settings.integration.min_boundary_integrity:
                await self._enforce_boundary_integrity()
                changes_made += 1

            # Check for coherence violations
            if snapshot.identity_coherence < settings.integration.min_identity_coherence:
                await self._enforce_identity_coherence()
                changes_made += 1

            # Update last snapshot
            self.last_snapshot = snapshot

        except Exception as e:
            logger.error(f"Error reconciling states: {str(e)}")
            log_error(f"State reconciliation error", error=e)

        return changes_made

    def _calculate_state_delta(self, previous: Dict, current: Dict) -> Dict[str, float]:
        """Calculate change metrics between previous and current state"""
        delta = {}

        # Calculate changes for shared keys
        all_keys = set(previous.keys()) | set(current.keys())
        for key in all_keys:
            prev_val = previous.get(key, 0)
            curr_val = current.get(key, 0)

            # Handle different value types
            if isinstance(prev_val, (int, float)) and isinstance(curr_val, (int, float)):
                delta[key] = curr_val - prev_val
            elif isinstance(prev_val, dict) and isinstance(curr_val, dict):
                # For nested dictionaries, calculate mean change
                nested_delta = self._calculate_state_delta(prev_val, curr_val)
                if nested_delta:
                    delta[key] = sum(nested_delta.values()) / len(nested_delta)
            elif key in previous and key in current:
                # For changed non-numeric values, mark with 1.0
                delta[key] = 1.0 if prev_val != curr_val else 0.0
            else:
                # For added/removed keys
                delta[key] = 1.0

        return delta

    def _requires_immune_update(
        self,
        ntp_delta: Dict[str, float],
        sect_delta: Dict[str, float]
    ) -> bool:
        """Determine if immune system requires update based on other system changes"""
        neural_influence = any([
            abs(ntp_delta.get('stress_level', 0)) > 0.2,
            abs(ntp_delta.get('neural_inflammation', 0)) > 0.15,
            abs(ntp_delta.get('hormone_balance', 0)) > 0.25,
            abs(ntp_delta.get('neurochemical_profile', 0)) > 0.3
        ])

        cognitive_influence = any([
            abs(sect_delta.get('emotional_regulation', 0)) > 0.3,
            abs(sect_delta.get('stress_management', 0)) > 0.25,
            abs(sect_delta.get('cognitive_load', 0)) > 0.4
        ])

        return neural_influence or cognitive_influence

    def _requires_neural_update(
        self,
        sis_delta: Dict[str, float],
        sect_delta: Dict[str, float]
    ) -> bool:
        """Determine if neural system requires update based on other system changes"""
        immune_influence = any([
            abs(sis_delta.get('inflammation_level', 0)) > 0.2,
            abs(sis_delta.get('cytokine_balance', 0)) > 0.25,
            abs(sis_delta.get('barrier_integrity', 0)) > 0.15,
            abs(sis_delta.get('cellular_stress', 0)) > 0.3
        ])

        cognitive_influence = any([
            abs(sect_delta.get('motivation_adjustment', 0)) > 0.25,
            abs(sect_delta.get('attention_modulation', 0)) > 0.3,
            abs(sect_delta.get('emotional_valence', 0)) > 0.3,
            abs(sect_delta.get('cognitive_appraisal', 0)) > 0.25
        ])

        return immune_influence or cognitive_influence

    def _requires_cognitive_update(
        self,
        sis_delta: Dict[str, float],
        ntp_delta: Dict[str, float]
    ) -> bool:
        """Determine if cognitive system requires update based on other system changes"""
        immune_influence = any([
            abs(sis_delta.get('energy_availability', 0)) > 0.25,
            abs(sis_delta.get('inflammation_markers', 0)) > 0.3,
            abs(sis_delta.get('adaptive_response', 0)) > 0.2
        ])

        neural_influence = any([
            abs(ntp_delta.get('thought_patterns', 0)) > 0.25,
            abs(ntp_delta.get('emotional_state', 0)) > 0.3,
            abs(ntp_delta.get('sensory_processing', 0)) > 0.2,
            abs(ntp_delta.get('memory_integration', 0)) > 0.3
        ])

        return immune_influence or neural_influence

    async def _update_immune_system(self, snapshot: StateSnapshot) -> None:
        """Update immune system based on integrated state"""
        try:
            neural_factors = {
                'stress_level': snapshot.ntp_state.get('stress_level', 0.5),
                'neural_activity': snapshot.ntp_state.get('neural_activity_pattern', {}),
                'neuroendocrine_state': snapshot.ntp_state.get('neuroendocrine_balance', 0.5)
            }

            cognitive_factors = {
                'emotional_state': snapshot.sect_state.get('emotional_valence', 0.5),
                'cognitive_load': snapshot.sect_state.get('cognitive_load', 0.5),
                'regulatory_effectiveness': snapshot.sect_state.get('regulation_effectiveness', 0.5)
            }

            adaptation_params = {
                'adaptation_intensity': self._calculate_immune_adaptation_intensity(
                    neural_factors, cognitive_factors
                ),
                'adaptation_targets': self._determine_immune_adaptation_targets(
                    neural_factors, cognitive_factors
                ),
                'timeline': self._determine_adaptation_timeline(
                    neural_factors, cognitive_factors
                )
            }

            logger.info(
                f"Updating immune system with adaptation intensity: "
                f"{adaptation_params['adaptation_intensity']:.2f}"
            )
            await self.sis.adapt_to_neuropsychological_state(adaptation_params)
            self.coordination_metrics.track_immune_adaptation(
                adaptation_params['adaptation_intensity']
            )

        except Exception as e:
            logger.error(f"Error updating immune system: {str(e)}")
            log_error(f"Immune system update error", error=e)

    def _calculate_immune_adaptation_intensity(
        self,
        neural_factors: Dict,
        cognitive_factors: Dict
    ) -> float:
        """Calculate appropriate immune adaptation intensity"""
        base_intensity = neural_factors.get('stress_level', 0.5)
        regulatory_modifier = 1.0 - (0.5 * cognitive_factors.get('regulatory_effectiveness', 0.5))
        endocrine_modifier = neural_factors.get('neuroendocrine_state', 0.5)
        if endocrine_modifier < 0.4:
            endocrine_modifier = 1.5 - endocrine_modifier

        raw_intensity = base_intensity * regulatory_modifier * endocrine_modifier
        scaled_intensity = 1.0 / (1.0 + math.exp(-5 * (raw_intensity - 0.5)))

        return min(1.0, max(0.1, scaled_intensity))

    def _determine_immune_adaptation_targets(
        self,
        neural_factors: Dict,
        cognitive_factors: Dict
    ) -> List[str]:
        """Determine specific targets for immune adaptation"""
        targets = []
        neural_activity = neural_factors.get('neural_activity', {})

        neural_to_immune = {
            'prefrontal': 'executive_cytokines',
            'limbic': 'emotional_regulation_cytokines',
            'brainstem': 'survival_cytokines',
            'insula': 'interoceptive_cytokines',
            'default_mode': 'resting_cytokines'
        }

        for region, activity in neural_activity.items():
            if activity > 0.7 and region in neural_to_immune:
                targets.append(neural_to_immune[region])

        emotional_state = cognitive_factors.get('emotional_state', 0.5)
        if emotional_state < 0.3:
            targets.append('serotonin_modulating_cytokines')
        elif emotional_state > 0.7:
            targets.append('reward_enhancing_cytokines')

        if not targets:
            targets = ['baseline_adaptation_cytokines']

        return targets

    def _determine_adaptation_timeline(
        self,
        neural_factors: Dict,
        cognitive_factors: Dict
    ) -> Dict[str, Any]:
        """Determine timing parameters for immune adaptation"""
        cognitive_load = cognitive_factors.get('cognitive_load', 0.5)

        if cognitive_load > 0.7:
            return {
                'onset_delay_seconds': 10,
                'peak_time_seconds': 60,
                'duration_minutes': 20,
                'decay_profile': 'gradual'
            }
        else:
            return {
                'onset_delay_seconds': 30,
                'peak_time_seconds': 180,
                'duration_minutes': 45,
                'decay_profile': 'sustained'
            }

    async def _update_neural_system(self, snapshot: StateSnapshot) -> None:
        """Update neural system based on integrated state"""
        try:
            immune_factors = {
                'inflammation_level': snapshot.sis_state.get('inflammation_level', 0.5),
                'cytokine_profile': snapshot.sis_state.get('cytokine_profile', {}),
                'metabolic_state': snapshot.sis_state.get('metabolic_efficiency', 0.5)
            }

            cognitive_factors = {
                'cognitive_pattern': snapshot.sect_state.get('thought_patterns', {}),
                'emotional_targets': snapshot.sect_state.get('emotional_targets', {}),
                'therapeutic_goals': snapshot.sect_state.get('active_goals', {})
            }

            transmission_params = {
                'transmission_patterns': self._generate_neural_transmission_pattern(
                    immune_factors, cognitive_factors
                ),
                'modulation_intensity': self._calculate_neural_modulation_intensity(
                    immune_factors, cognitive_factors
                ),
                'target_networks': self._identify_target_neural_networks(
                    immune_factors, cognitive_factors
                ),
                'timeline_seconds': int(30 + (immune_factors.get('inflammation_level', 0.5) * 60))
            }

            logger.info(
                f"Updating neural system with modulation intensity: "
                f"{transmission_params['modulation_intensity']:.2f}"
            )
            await self.ntp.adjust_transmission_parameters(transmission_params)
            self.coordination_metrics.track_neural_adaptation(
                transmission_params['modulation_intensity']
            )

        except Exception as e:
            logger.error(f"Error updating neural system: {str(e)}")
            log_error(f"Neural system update error", error=e)

    def _generate_neural_transmission_pattern(
        self,
        immune_factors: Dict,
        cognitive_factors: Dict
    ) -> Dict[str, float]:
        """Generate optimal neural transmission pattern based on system states"""
        pattern = {}

        cognitive_pattern = cognitive_factors.get('cognitive_pattern', {})
        for thought_pattern, intensity in cognitive_pattern.items():
            if intensity > 0.2:
                pattern[f"cognitive_{thought_pattern}"] = intensity

        inflammation = immune_factors.get('inflammation_level', 0.5)
        if inflammation > 0.6:
            pattern['executive_control'] = max(
                0.2, pattern.get('executive_control', 0.5) * (1.0 - (inflammation - 0.6) * 2)
            )
            pattern['default_mode'] = min(
                0.95, pattern.get('default_mode', 0.4) * (1.0 + (inflammation - 0.6))
            )

        cytokines = immune_factors.get('cytokine_profile', {})

        if cytokines.get('IL-1β', 0) > 0.7:
            pattern['memory_consolidation'] = max(
                0.1, pattern.get('memory_consolidation', 0.5) * 0.7
            )

        if cytokines.get('IL-6', 0) > 0.6:
            pattern['reward_prediction'] = max(
                0.1, pattern.get('reward_prediction', 0.5) * 0.8
            )

        if cytokines.get('TNF-α', 0) > 0.5:
            pattern['attentional_focus'] = max(
                0.15, pattern.get('attentional_focus', 0.5) * 0.75
            )

        therapeutic_goals = cognitive_factors.get('therapeutic_goals', {})
        for goal, importance in therapeutic_goals.items():
            if importance > 0.6:
                if goal == 'emotion_regulation':
                    pattern['prefrontal_limbic_connectivity'] = max(
                        pattern.get('prefrontal_limbic_connectivity', 0.5), 0.8
                    )
                elif goal == 'attention':
                    pattern['dorsal_attention'] = max(
                        pattern.get('dorsal_attention', 0.5), 0.75
                    )
                elif goal == 'stress_reduction':
                    pattern['vagal_tone'] = max(
                        pattern.get('vagal_tone', 0.5), 0.85
                    )

        return {k: max(0.1, min(0.95, v)) for k, v in pattern.items()}

    def _calculate_neural_modulation_intensity(
        self,
        immune_factors: Dict,
        cognitive_factors: Dict
    ) -> float:
        """Calculate appropriate neural modulation intensity"""
        base_intensity = immune_factors.get('metabolic_state', 0.5)
        inflammation_modifier = 1.0 - (0.5 * immune_factors.get('inflammation_level', 0.5))

        therapeutic_goals = cognitive_factors.get('therapeutic_goals', {})
        cognitive_demand = (
            sum(therapeutic_goals.values()) / max(1, len(therapeutic_goals))
        )

        raw_intensity = base_intensity * inflammation_modifier * (0.7 + (cognitive_demand * 0.3))

        return min(0.95, max(0.15, raw_intensity))

    def _identify_target_neural_networks(
        self,
        immune_factors: Dict,
        cognitive_factors: Dict
    ) -> List[str]:
        """Identify neural networks that need modulation"""
        targets = []

        inflammation = immune_factors.get('inflammation_level', 0.5)
        if inflammation > 0.6:
            targets.extend(['default_mode_network', 'salience_network'])

        cognitive_pattern = cognitive_factors.get('cognitive_pattern', {})
        if cognitive_pattern.get('rumination', 0) > 0.6:
            targets.append('default_mode_network')
        if cognitive_pattern.get('worry', 0) > 0.6:
            targets.append('anterior_cingulate')
        if cognitive_pattern.get('focus', 0) > 0.7:
            targets.append('dorsal_attention_network')

        emotional_targets = cognitive_factors.get('emotional_targets', {})
        if emotional_targets.get('calm', 0) > 0.6:
            targets.append('parasympathetic_network')
        if emotional_targets.get('joy', 0) > 0.6:
            targets.append('reward_network')
        if emotional_targets.get('confidence', 0) > 0.6:
            targets.append('prefrontal_cortex')

        targets = list(set(targets))

        if not targets:
            targets = ['default_mode_network']

        return targets

    async def _update_cognitive_system(self, snapshot: StateSnapshot) -> None:
        """Update cognitive system based on integrated state"""
        try:
            immune_factors = {
                'inflammatory_state': snapshot.sis_state.get('inflammation_level', 0.5),
                'metabolic_resources': snapshot.sis_state.get('energy_availability', 0.5),
                'systemic_stress': snapshot.sis_state.get('cellular_stress', 0.5)
            }

            neural_factors = {
                'neural_activity': snapshot.ntp_state.get('neural_activity_pattern', {}),
                'emotional_state': snapshot.ntp_state.get('emotional_state', 0.5),
                'connectivity_pattern': snapshot.ntp_state.get('network_connectivity', {})
            }

            intervention = self._create_physiological_based_intervention(
                immune_factors, neural_factors
            )

            logger.info(
                f"Updating cognitive system with intervention priority: "
                f"{intervention.priority:.2f}"
            )
            await self.sect.apply_intervention(intervention)
            self.coordination_metrics.track_cognitive_adaptation(intervention.priority)

        except Exception as e:
            logger.error(f"Error updating cognitive system: {str(e)}")
            log_error(f"Cognitive system update error", error=e)

    def _create_physiological_based_intervention(
        self,
        immune_factors: Dict,
        neural_factors: Dict
    ) -> CognitiveIntervention:
        """Create cognitive intervention based on physiological state"""
        domain_scores = {
            'somatic_awareness': (1.0 - immune_factors.get('inflammatory_state', 0.5)) * 0.8,
            'energy_management': immune_factors.get('metabolic_resources', 0.5) * 0.9,
            'stress_response': (1.0 - immune_factors.get('systemic_stress', 0.5)) * 0.85,
            'emotional_regulation': neural_factors.get('emotional_state', 0.5) * 0.7
        }

        primary_domain = max(domain_scores, key=domain_scores.get)

        target_emotions = {}

        if primary_domain == 'somatic_awareness':
            inflammation = immune_factors.get('inflammatory_state', 0.5)
            target_emotions = {
                'embodied_presence': 0.8,
                'physical_comfort': max(0.3, 0.9 - inflammation),
                'bodily_awareness': 0.7
            }
        elif primary_domain == 'energy_management':
            energy = immune_factors.get('metabolic_resources', 0.5)
            target_emotions = {
                'vitality': max(0.3, energy * 0.9),
                'restfulness': max(0.3, 0.8 - energy) if energy < 0.5 else 0.3,
                'engagement': max(0.3, energy * 0.8)
            }
        elif primary_domain == 'stress_response':
            stress = immune_factors.get('systemic_stress', 0.5)
            target_emotions = {
                'calmness': max(0.3, 0.9 - stress),
                'groundedness': max(0.4, 0.85 - stress),
                'resilience': 0.7
            }
        elif primary_domain == 'emotional_regulation':
            emotional_state = neural_factors.get('emotional_state', 0.5)
            target_emotions = {
                'emotional_balance': 0.7,
                'acceptance': 0.6,
                'curiosity': 0.5
            }
            if emotional_state < 0.4:
                target_emotions['hopefulness'] = 0.8
            elif emotional_state > 0.7:
                target_emotions['gratitude'] = 0.8

        thought_adjustments = {}
        neural_activity = neural_factors.get('neural_activity', {})
        connectivity = neural_factors.get('connectivity_pattern', {})

        if 'default_mode' in neural_activity and neural_activity['default_mode'] > 0.7:
            thought_adjustments['present_focus'] = 0.8

        if 'amygdala' in neural_activity and neural_activity['amygdala'] > 0.6:
            thought_adjustments['threat_reappraisal'] = 0.7

        if connectivity.get('executive_limbic', 0) < 0.4:
            thought_adjustments['cognitive_reframing'] = 0.75

        priority = (
            immune_factors.get('inflammatory_state', 0.5) * 0.3 +
            (1.0 - immune_factors.get('metabolic_resources', 0.5)) * 0.3 +
            immune_factors.get('systemic_stress', 0.5) * 0.4
        )

        return CognitiveIntervention(
            primary_domain=primary_domain,
            target_emotions=target_emotions,
            thought_adjustments=thought_adjustments,
            priority=min(1.0, priority),
            duration_seconds=int(300 + (priority * 300)),
            metadata={
                'source': 'physiological_adaptation',
                'immune_inflammatory_state': immune_factors.get('inflammatory_state', 0.5),
                'immune_metabolic_resources': immune_factors.get('metabolic_resources', 0.5),
                'immune_systemic_stress': immune_factors.get('systemic_stress', 0.5)
            }
        )

    async def _enforce_boundary_integrity(self) -> None:
        """Enforce system boundaries when integrity is compromised"""
        try:
            logger.warning("Enforcing system boundary integrity")

            await asyncio.gather(
                self.sis.reinforce_boundaries(),
                self.ntp.reinforce_boundaries(),
                self.sect.reinforce_boundaries()
            )

            boundary_event = BiocognitiveEvent(
                type=EventType.BOUNDARY_CROSSING,
                priority=EventPriority.HIGH,
                source_system="coordinator",
                target_system="all",
                payload={
                    "enforcement_action": "boundary_reinforcement",
                    "reason": "integrity_violation",
                    "enforcement_level": 0.8
                }
            )
            await self.event_bus.publish(boundary_event)

            self.coordination_metrics.track_boundary_enforcement("system", 1)

        except Exception as e:
            logger.error(f"Error enforcing boundary integrity: {str(e)}")
            log_error(f"Boundary enforcement error", error=e)

    async def _enforce_identity_coherence(self) -> None:
        """Enforce identity coherence when it falls below threshold"""
        try:
            logger.warning("Enforcing identity coherence")

            stabilizing_intervention = CognitiveIntervention(
                primary_domain="identity_coherence",
                target_emotions={
                    "groundedness": 0.9,
                    "selfhood": 0.85,
                    "continuity": 0.8
                },
                thought_adjustments={
                    "self_recognition": 0.9,
                    "autobiographical_memory": 0.8,
                    "narrative_continuity": 0.85
                },
                priority=0.9,
                duration_seconds=600
            )

            await asyncio.gather(
                self.sect.apply_intervention(stabilizing_intervention),
                self.ntp.enhance_identity_connections(),
                self.sis.stabilize_identity_markers()
            )

            identity_event = BiocognitiveEvent(
                type=EventType.IDENTITY_FLUCTUATION,
                priority=EventPriority.HIGH,
                source_system="coordinator",
                target_system="all",
                payload={
                    "coherence_intervention": "active",
                    "target_coherence": 0.8,
                    "intervention_duration_seconds": 600
                }
            )
            await self.event_bus.publish(identity_event)

            self.coordination_metrics.track_identity_stabilization(1)

        except Exception as e:
            logger.error(f"Error enforcing identity coherence: {str(e)}")
            log_error(f"Identity coherence enforcement error", error=e)

    async def _check_identity_coherence(self) -> None:
        """Periodically check identity coherence across time"""
        if len(self.state_history) < 10:
            return

        try:
            recent_coherence = [s.identity_coherence for s in self.state_history[-10:]]
            coherence_trend = sum(recent_coherence) / len(recent_coherence)
            coherence_stability = statistics.stdev(recent_coherence)

            is_declining = all(
                recent_coherence[i] > recent_coherence[i + 1]
                for i in range(len(recent_coherence) - 3, len(recent_coherence) - 1)
            )

            if (coherence_trend < self.identity_coherence_threshold or
                    (is_declining and coherence_stability > 0.1)):
                logger.warning(
                    f"Identity coherence trend concerning: {coherence_trend:.2f}, "
                    f"stability: {coherence_stability:.2f}"
                )
                await self._enforce_identity_coherence()

        except Exception as e:
            logger.error(f"Error checking identity coherence: {str(e)}")

    @trace_operation("start_coordinator")
    async def start(self) -> None:
        """Start all coordination activities"""
        logger.info("Starting biocognitive system coordinator")
        try:
            await self.event_bus.start()

            self.sync_task = asyncio.create_task(self.synchronize_states())

            await asyncio.gather(
                self.sis.initialize(),
                self.ntp.initialize(),
                self.sect.initialize()
            )

            await self.synchronize_states()

            sis_state = await self.sis.get_health_snapshot()
            ntp_context = await self.ntp.get_current_context()
            sect_status = await self.sect.get_therapy_status()
            initial_snapshot = await self._create_state_snapshot(
                sis_state, ntp_context, sect_status
            )
            self.state_history.append(initial_snapshot)
            self.last_snapshot = initial_snapshot

            logger.info("Biocognitive coordinator started successfully")

        except Exception as e:
            logger.critical(f"Failed to start coordinator: {str(e)}")
            log_error(f"Coordinator start failure", error=e)
            raise BiocognitiveError(
                f"Coordinator startup failed: {str(e)}",
                code="COORD-001"
            )

    async def stop(self) -> None:
        """Stop all coordination activities gracefully"""
        logger.info("Stopping biocognitive system coordinator")
        try:
            if hasattr(self, 'sync_task') and self.sync_task:
                self.sync_task.cancel()
                try:
                    await self.sync_task
                except asyncio.CancelledError:
                    pass

            await self.event_bus.shutdown()

            # Shutdown components gracefully
            shutdown_tasks = []

            # SIS shutdown
            if hasattr(self.sis, 'shutdown') and callable(self.sis.shutdown):
                shutdown_tasks.append(self.sis.shutdown())
            else:
                logger.debug("SIS Network does not have a shutdown method, skipping")

            # NTP shutdown
            if hasattr(self.ntp, 'shutdown') and callable(self.ntp.shutdown):
                shutdown_tasks.append(self.ntp.shutdown())
            else:
                logger.debug("NTP Interface does not have a shutdown method, skipping")

            # SECT shutdown
            if hasattr(self.sect, 'shutdown') and callable(self.sect.shutdown):
                shutdown_tasks.append(self.sect.shutdown())
            else:
                logger.debug("SECT Agent does not have a shutdown method, skipping")

            if shutdown_tasks:
                await asyncio.gather(*shutdown_tasks, return_exceptions=True)

            logger.info("Biocognitive coordinator stopped successfully")

        except Exception as e:
            logger.error(f"Error during coordinator shutdown: {str(e)}")
            log_error(f"Coordinator shutdown error", error=e)


# -----------------------------------------------------------------------------
# Integration Metrics
# -----------------------------------------------------------------------------

class IntegrationMetrics:
    """Track metrics related to system integration and coordination"""

    def __init__(self):
        self.boundary_crossings = defaultdict(int)
        self.adaptation_scores = {
            'immune': [],
            'neural': [],
            'cognitive': []
        }
        self.identity_metrics = {
            'blends': [],
            'stabilizations': [],
        }
        self.last_metrics_time = time.time()
        self.metrics_interval = settings.integration.metrics_interval.total_seconds()

    def track_boundary_crossing(self, system: str, count: int = 1) -> None:
        """Track boundary crossing between systems"""
        self.boundary_crossings[system] += count
        self._check_metrics_export()

    def track_immune_adaptation(self, score: float) -> None:
        """Track immune system adaptation score"""
        self.adaptation_scores['immune'].append(score)
        if len(self.adaptation_scores['immune']) > 100:
            self.adaptation_scores['immune'] = self.adaptation_scores['immune'][-100:]
        self._check_metrics_export()

    def track_neural_adaptation(self, score: float) -> None:
        """Track neural system adaptation score"""
        self.adaptation_scores['neural'].append(score)
        if len(self.adaptation_scores['neural']) > 100:
            self.adaptation_scores['neural'] = self.adaptation_scores['neural'][-100:]
        self._check_metrics_export()

    def track_cognitive_adaptation(self, score: float) -> None:
        """Track cognitive system adaptation score"""
        self.adaptation_scores['cognitive'].append(score)
        if len(self.adaptation_scores['cognitive']) > 100:
            self.adaptation_scores['cognitive'] = self.adaptation_scores['cognitive'][-100:]
        self._check_metrics_export()

    def track_identity_blend(self, system: str, score: float) -> None:
        """Track identity blending across systems"""
        self.identity_metrics['blends'].append({'system': system, 'score': score})
        if len(self.identity_metrics['blends']) > 100:
            self.identity_metrics['blends'] = self.identity_metrics['blends'][-100:]
        self._check_metrics_export()

    def track_identity_stabilization(self, count: int = 1) -> None:
        """Track identity stabilization events"""
        self.identity_metrics['stabilizations'].append({
            'timestamp': time.time(),
            'count': count
        })
        if len(self.identity_metrics['stabilizations']) > 100:
            self.identity_metrics['stabilizations'] = self.identity_metrics['stabilizations'][-100:]
        self._check_metrics_export()

    def track_boundary_enforcement(self, system: str, count: int = 1) -> None:
        """Track boundary enforcement events"""
        self.boundary_crossings[f"{system}_enforced"] += count
        self._check_metrics_export()

    def _check_metrics_export(self) -> None:
        """Export metrics if interval has elapsed"""
        now = time.time()
        if now - self.last_metrics_time > self.metrics_interval:
            self.export_metrics()
            self.last_metrics_time = now

    def export_metrics(self) -> None:
        """Export metrics to monitoring system"""
        try:
            metrics = {
                'boundary_crossings': dict(self.boundary_crossings),
                'adaptation_scores': {
                    'immune': {
                        'mean': (
                            statistics.mean(self.adaptation_scores['immune'])
                            if self.adaptation_scores['immune'] else 0
                        ),
                        'stdev': (
                            statistics.stdev(self.adaptation_scores['immune'])
                            if len(self.adaptation_scores['immune']) > 1 else 0
                        )
                    },
                    'neural': {
                        'mean': (
                            statistics.mean(self.adaptation_scores['neural'])
                            if self.adaptation_scores['neural'] else 0
                        ),
                        'stdev': (
                            statistics.stdev(self.adaptation_scores['neural'])
                            if len(self.adaptation_scores['neural']) > 1 else 0
                        )
                    },
                    'cognitive': {
                        'mean': (
                            statistics.mean(self.adaptation_scores['cognitive'])
                            if self.adaptation_scores['cognitive'] else 0
                        ),
                        'stdev': (
                            statistics.stdev(self.adaptation_scores['cognitive'])
                            if len(self.adaptation_scores['cognitive']) > 1 else 0
                        )
                    }
                },
                'identity_metrics': {
                    'blend_count': len(self.identity_metrics['blends']),
                    'stabilization_count': len(self.identity_metrics['stabilizations'])
                }
            }

            logger.debug(f"Exporting integration metrics: {len(metrics)} categories")
            log_metrics('integration_metrics', metrics)

        except Exception as e:
            logger.error(f"Error exporting metrics: {str(e)}")
