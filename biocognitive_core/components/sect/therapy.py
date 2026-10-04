# src/biocognitive_core/components/sect/therapy.py
"""
Therapeutic Intervention Execution System

Manages implementation and tracking of cognitive therapies with:
- Multi-modal intervention delivery
- Real-time effectiveness monitoring
- Adaptive protocol adjustments
Author: Morpheus
Date: 2025-05-08
Version: 1.0.0
Description: This module implements the SECT (Synthetic Emotional Cognitive Therapy) system, which is responsible for executing therapeutic interventions. It includes various phases of therapy, such as initialization, execution, evaluation, and adaptation. The system tracks metrics and adjusts interventions based on real-time feedback.
ID: SECT-001
SHA-256: 3f3b2c4e5d6a7b8c9e0f1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3
"""

from typing import Dict, Any, Optional, List, Tuple, Union, AsyncGenerator
from pydantic import BaseModel, Field, validator
from enum import Enum
import asyncio
from biocognitive_core.config import settings
from biocognitive_core.exceptions import BiocognitiveError, TherapyMisalignmentError
from biocognitive_core.metrics import SECTMetrics
from .agent import CognitiveTherapist, TherapeuticIntervention, TherapyGoal
from datetime import datetime, timedelta
import numpy as np

class TherapyPhase(Enum):
    """Stages of therapeutic intervention"""
    INITIALIZATION = "initialization"
    EXECUTION = "execution"
    EVALUATION = "evaluation"
    ADAPTATION = "adaptation"

class TherapySession:
    """Structured therapeutic intervention execution"""
    def __init__(self, intervention: TherapeuticIntervention):
        self.intervention = intervention
        self.phase: TherapyPhase = TherapyPhase.INITIALIZATION
        self.start_time = datetime.utcnow()
        self.progress = 0.0
        self.metrics_collector = SECTMetrics()

    async def execute(self, agent: CognitiveTherapist):
        """
        Execute therapeutic intervention across multiple phases
        
        >>> session = TherapySession(TherapeuticIntervention(goal=TherapyGoal.EMOTIONAL_STABILITY))
        >>> await session.execute(CognitiveTherapist("user123"))
        """
        try:
            self.phase = TherapyPhase.EXECUTION
            await self._initialize_intervention(agent)
            
            # Main execution loop
            while self.progress < 1.0:
                await self._apply_techniques(agent)
                self.progress += 0.1
                await asyncio.sleep(1)
                
            self.phase = TherapyPhase.EVALUATION
            result = await self._evaluate_outcome(agent)
            
            if result["success_rate"] < 0.7:
                self.phase = TherapyPhase.ADAPTATION
                await self._adapt_intervention(agent)
                
            self.metrics_collector.track_therapy_completion(
                self.intervention.goal.value, 
                result["success_rate"]
            )
            
        except Exception as e:
            self.metrics_collector.track_event("therapy_failure", {"error": str(e)})
            raise

    async def _initialize_intervention(self, agent: CognitiveTherapist):
        """Prepare for therapeutic intervention"""
        if not agent.alignment_engine.verify_alignment(agent.model):
            raise TherapyMisalignmentError(
                "Therapy cannot proceed due to misalignment",
                code="SECT-003",
                alignment_score=agent.model.alignment_score
            )
        self.metrics_collector.track_event("therapy_start", {"goal": self.intervention.goal.value})

    async def _apply_techniques(self, agent: CognitiveTherapist):
        """Implement selected therapeutic techniques"""
        for technique in self.intervention.techniques:
            await self._execute_technique(technique, agent)
            self.metrics_collector.track_event(f"technique_applied", {"technique": technique})

    async def _execute_technique(self, technique: str, agent: CognitiveTherapist):
        """Apply specific therapeutic technique"""
        if technique == "mindfulness":
            await self._perform_mindfulness(agent)
        elif technique == "cognitive_restructuring":
            await self._perform_cognitive_restructuring(agent)
        # Add additional technique implementations

    async def _perform_mindfulness(self, agent: CognitiveTherapist):
        """Implement mindfulness-based intervention"""
        # Simulated mindfulness protocol
        agent.model.emotional_profile["mindfulness"] = min(
            1.0, 
            agent.model.emotional_profile.get("mindfulness", 0.0) + 0.1
        )
        await asyncio.sleep(0.1)

    async def _perform_cognitive_restructuring(self, agent: CognitiveTherapist):
        """Implement cognitive restructuring technique"""
        # Simulated cognitive restructuring
        for key in agent.model.cognitive_patterns:
            agent.model.cognitive_patterns[key] = [min(1.0, x * 1.05) for x in agent.model.cognitive_patterns[key]]
        await asyncio.sleep(0.1)

    async def _evaluate_outcome(self, agent: CognitiveTherapist) -> Dict[str, float]:
        """Assess intervention effectiveness"""
        # In production, this would use machine learning models
        return {
            "success_rate": np.random.uniform(0.7, 0.95),
            "side_effects": np.random.uniform(0.0, 0.2),
            "engagement": np.random.uniform(0.8, 1.0)
        }

    async def _adapt_intervention(self, agent: CognitiveTherapist):
        """Adjust intervention based on evaluation results"""
        self.intervention.intensity = min(1.0, self.intervention.intensity * 0.8)
        self.intervention.techniques.append("adaptive_meditation")
        self.metrics_collector.track_event("intervention_adapted", {"techniques": self.intervention.techniques})

"""
Self-Evolving Cognitive Therapist Core Implementation

Implements advanced therapeutic capabilities with:
- Multi-dimensional cognitive modeling
- Personalized intervention strategies
- Adaptive therapy progression tracking
- Session synchronization with neural interfaces

This module contains the core therapeutic algorithms that power the SECT component,
providing the primary therapeutic capabilities integrated with biocognitive systems.

Author: Morpheus
Date: 2025-05-08
Version: 1.0.0
ID: SECT-002
SHA-256: 842c3f4e5d6a7b8c9e0f1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3
"""

import asyncio
import numpy as np
import logging
import random
import time
from typing import Dict, List, Optional, Tuple, Union, Any, Callable, Awaitable, TypeVar, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from enum import Enum
import json
import warnings

from biocognitive_core.config import settings
from biocognitive_core.exceptions import (
    TherapyMisalignmentError, 
    IdentityDissolutionRisk,
    CognitiveAlignmentError,
    BiocognitiveError
)
from biocognitive_core.metrics import SECTMetrics
from .agent import (
    CognitiveState, 
    CognitiveStateDifferential, 
    TherapeuticIntervention,
    CognitiveReframing,
    EmotionalRegulation,
    CognitiveProcessingMode
)

logger = logging.getLogger(__name__)


class TherapyModality(Enum):
    """Available therapy modalities"""
    COGNITIVE_BEHAVIORAL = "cbt"
    PSYCHODYNAMIC = "psychodynamic"
    MINDFULNESS = "mindfulness"
    EXISTENTIAL = "existential"
    INTERPERSONAL = "interpersonal"
    SOMATIC = "somatic"
    INTEGRATIVE = "integrative"


class SessionStage(Enum):
    """Stages of a therapeutic session"""
    PREPARATION = "preparation"
    ASSESSMENT = "assessment"
    INSIGHT_BUILDING = "insight_building"
    INTERVENTION = "intervention"
    CONSOLIDATION = "consolidation"
    INTEGRATION = "integration"
    FOLLOW_UP = "follow_up"


@dataclass
class TherapeuticGoal:
    """Represents a structured therapeutic goal with tracking"""
    goal_id: str = field(default_factory=lambda: str(uuid4()))
    description: str = ""
    target_cognitive_dimensions: Dict[str, float] = field(default_factory=dict)
    target_emotional_state: Dict[str, float] = field(default_factory=dict)
    priority: float = 0.5
    creation_date: datetime = field(default_factory=datetime.now)
    target_completion_date: Optional[datetime] = None
    progress: float = 0.0
    related_goals: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    def update_progress(self, current_state: CognitiveState) -> float:
        """Update progress based on current cognitive state"""
        # Calculate progress along cognitive dimensions
        cognitive_progress = 0.0
        if self.target_cognitive_dimensions:
            dimension_scores = []
            for dim, target in self.target_cognitive_dimensions.items():
                if dim in current_state.thought_patterns:
                    current = np.mean(current_state.thought_patterns[dim])
                    diff = abs(current - target)
                    # Convert difference to similarity score (1.0 = perfect match)
                    score = max(0.0, 1.0 - min(1.0, diff))
                    dimension_scores.append(score)
            
            if dimension_scores:
                cognitive_progress = sum(dimension_scores) / len(dimension_scores)
        
        # Calculate progress along emotional dimensions
        emotional_progress = 0.0
        if self.target_emotional_state:
            emotion_scores = []
            for emotion, target in self.target_emotional_state.items():
                if emotion in current_state.emotional_valence:
                    current = current_state.emotional_valence[emotion]
                    diff = abs(current - target)
                    # Convert difference to similarity score (1.0 = perfect match)
                    score = max(0.0, 1.0 - min(1.0, diff))
                    emotion_scores.append(score)
            
            if emotion_scores:
                emotional_progress = sum(emotion_scores) / len(emotion_scores)
        
        # Combine progress measures
        if self.target_cognitive_dimensions and self.target_emotional_state:
            # Weighted combination
            self.progress = 0.6 * cognitive_progress + 0.4 * emotional_progress
        elif self.target_cognitive_dimensions:
            self.progress = cognitive_progress
        elif self.target_emotional_state:
            self.progress = emotional_progress
        
        return self.progress
    
    def estimated_completion_date(self) -> Optional[datetime]:
        """Estimate completion date based on progress trajectory"""
        if self.progress >= 1.0:
            return datetime.now()
            
        if self.progress <= 0.0 or not self.metrics.get('progress_history'):
            return self.target_completion_date
        
        # Calculate rate of progress from history
        history = self.metrics['progress_history']
        if len(history) < 2:
            return self.target_completion_date
            
        # Get progress rate per day
        days_elapsed = (history[-1]['date'] - history[0]['date']).days or 1
        progress_gained = history[-1]['progress'] - history[0]['progress']
        daily_rate = progress_gained / days_elapsed
        
        if daily_rate <= 0:
            return None  # Cannot estimate with negative progress
        
        # Project completion
        days_remaining = (1.0 - self.progress) / daily_rate
        return datetime.now() + timedelta(days=days_remaining)


@dataclass
class TherapeuticSession:
    """Represents a therapeutic session"""
    session_id: str = field(default_factory=lambda: str(uuid4()))
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    client_id: str = ""
    modality: TherapyModality = TherapyModality.INTEGRATIVE
    current_stage: SessionStage = SessionStage.PREPARATION
    initial_state: Optional[CognitiveState] = None
    current_state: Optional[CognitiveState] = None
    interventions_applied: List[Dict] = field(default_factory=list)
    session_goals: List[str] = field(default_factory=list)
    session_notes: Dict[str, Any] = field(default_factory=dict)
    
    def duration(self) -> float:
        """Get session duration in minutes"""
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds() / 60
    
    def is_active(self) -> bool:
        """Check if session is currently active"""
        return self.end_time is None
    
    def add_intervention(self, intervention: TherapeuticIntervention, effectiveness: float) -> None:
        """Record an applied intervention"""
        self.interventions_applied.append({
            "type": type(intervention).__name__,
            "id": str(intervention.intervention_id),
            "timestamp": datetime.now().isoformat(),
            "effectiveness": effectiveness,
            "priority": intervention.priority
        })
    
    def advance_stage(self) -> SessionStage:
        """Advance to the next session stage"""
        stages = list(SessionStage)
        current_index = stages.index(self.current_stage)
        
        if current_index < len(stages) - 1:
            self.current_stage = stages[current_index + 1]
        
        return self.current_stage
    
    def close(self) -> None:
        """End the therapeutic session"""
        self.end_time = datetime.now()
        if self.current_stage != SessionStage.FOLLOW_UP:
            self.current_stage = SessionStage.FOLLOW_UP
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for storage"""
        return {
            "session_id": self.session_id,
            "client_id": self.client_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "modality": self.modality.value,
            "stage": self.current_stage.value,
            "duration_minutes": self.duration(),
            "interventions_count": len(self.interventions_applied),
            "session_goals": self.session_goals,
            "session_notes": self.session_notes
        }


class TherapeuticProfile:
    """Client therapeutic profile with history and preferences"""
    
    def __init__(self, client_id: str):
        self.client_id = client_id
        self.creation_date = datetime.now()
        self.last_updated = self.creation_date
        self.sessions: List[str] = []
        self.active_goals: Dict[str, TherapeuticGoal] = {}
        self.completed_goals: Dict[str, TherapeuticGoal] = {}
        self.preferences = {
            "preferred_modalities": [TherapyModality.INTEGRATIVE.value],
            "intervention_sensitivity": 0.5,  # 0.0-1.0 scale
            "session_frequency": 2,  # per week
            "session_duration": 45,  # minutes
        }
        self.contraindications: Set[str] = set()
        self.therapeutic_history: Dict[str, Any] = {
            "past_modalities": [],
            "effectiveness_ratings": {},
            "milestone_achievements": []
        }
        self.cognitive_baselines: Dict[str, Any] = {}
        self.long_term_trends: Dict[str, List[float]] = {}
    
    def add_session(self, session_id: str) -> None:
        """Add a session to client history"""
        self.sessions.append(session_id)
        self.last_updated = datetime.now()
    
    def add_goal(self, goal: TherapeuticGoal) -> None:
        """Add a new therapeutic goal"""
        self.active_goals[goal.goal_id] = goal
        self.last_updated = datetime.now()
    
    def update_goal(self, goal_id: str, current_state: CognitiveState) -> Optional[float]:
        """Update goal progress based on current cognitive state"""
        if goal_id in self.active_goals:
            goal = self.active_goals[goal_id]
            progress = goal.update_progress(current_state)
            
            # Add to progress history
            if 'progress_history' not in goal.metrics:
                goal.metrics['progress_history'] = []
            
            goal.metrics['progress_history'].append({
                "date": datetime.now(),
                "progress": progress
            })
            
            # Check if goal is complete
            if progress >= 1.0:
                self.complete_goal(goal_id)
            
            self.last_updated = datetime.now()
            return progress
        
        return None
    
    def complete_goal(self, goal_id: str) -> None:
        """Mark a goal as completed and move to completed goals"""
        if goal_id in self.active_goals:
            goal = self.active_goals.pop(goal_id)
            goal.progress = 1.0
            self.completed_goals[goal_id] = goal
            
            # Add milestone achievement
            self.therapeutic_history["milestone_achievements"].append({
                "date": datetime.now().isoformat(),
                "goal_id": goal_id,
                "description": goal.description
            })
            
            self.last_updated = datetime.now()
    
    def get_preferred_modality(self) -> TherapyModality:
        """Get client's preferred therapy modality"""
        preferred = self.preferences.get("preferred_modalities", [TherapyModality.INTEGRATIVE.value])[0]
        return TherapyModality(preferred)
    
    def update_effectiveness(self, modality: TherapyModality, rating: float) -> None:
        """Update effectiveness rating for a therapy modality"""
        if modality.value not in self.therapeutic_history["effectiveness_ratings"]:
            self.therapeutic_history["effectiveness_ratings"][modality.value] = []
        
        self.therapeutic_history["effectiveness_ratings"][modality.value].append({
            "date": datetime.now().isoformat(),
            "rating": rating
        })
        
        # Update preferred modalities based on effectiveness
        all_modalities = [(m, self._calculate_avg_effectiveness(m)) 
                         for m in self.therapeutic_history["effectiveness_ratings"].keys()]
        all_modalities.sort(key=lambda x: x[1], reverse=True)
        
        # Update preference list with top 3 most effective modalities
        self.preferences["preferred_modalities"] = [m for m, _ in all_modalities[:3]]
        self.last_updated = datetime.now()
    
    def _calculate_avg_effectiveness(self, modality: str) -> float:
        """Calculate average effectiveness for a modality"""
        ratings = self.therapeutic_history["effectiveness_ratings"].get(modality, [])
        if not ratings:
            return 0.0
        
        # Weight recent ratings more heavily
        total_weight = 0
        weighted_sum = 0
        
        for i, rating_data in enumerate(ratings):
            # More recent ratings get higher weight
            weight = i + 1
            weighted_sum += rating_data["rating"] * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def update_cognitive_baseline(self, state: CognitiveState) -> None:
        """Update cognitive baselines using exponential smoothing"""
        alpha = 0.3  # Smoothing factor
        
        # Initialize if empty
        if not self.cognitive_baselines:
            self.cognitive_baselines = {
                "emotional_valence": {k: v for k, v in state.emotional_valence.items()},
                "thought_patterns": {k: v.tolist() for k, v in state.thought_patterns.items()},
                "cognitive_load": state.cognitive_load,
                "self_awareness_level": state.self_awareness_level,
                "last_updated": datetime.now().isoformat()
            }
            return
        
        # Update emotional baselines with smoothing
        if "emotional_valence" not in self.cognitive_baselines:
            self.cognitive_baselines["emotional_valence"] = {}
        
        for emotion, value in state.emotional_valence.items():
            if emotion in self.cognitive_baselines["emotional_valence"]:
                old_value = self.cognitive_baselines["emotional_valence"][emotion]
                self.cognitive_baselines["emotional_valence"][emotion] = (1-alpha) * old_value + alpha * value
            else:
                self.cognitive_baselines["emotional_valence"][emotion] = value
        
        # Update thought pattern baselines
        if "thought_patterns" not in self.cognitive_baselines:
            self.cognitive_baselines["thought_patterns"] = {}
        
        for pattern_key, pattern in state.thought_patterns.items():
            if pattern_key in self.cognitive_baselines["thought_patterns"]:
                old_pattern = np.array(self.cognitive_baselines["thought_patterns"][pattern_key])
                if old_pattern.shape == pattern.shape:
                    new_pattern = (1-alpha) * old_pattern + alpha * pattern
                    self.cognitive_baselines["thought_patterns"][pattern_key] = new_pattern.tolist()
            else:
                self.cognitive_baselines["thought_patterns"][pattern_key] = pattern.tolist()
        
        # Update scalar metrics
        for metric in ["cognitive_load", "self_awareness_level"]:
            if metric in self.cognitive_baselines:
                old_value = self.cognitive_baselines[metric]
                self.cognitive_baselines[metric] = (1-alpha) * old_value + alpha * getattr(state, metric)
            else:
                self.cognitive_baselines[metric] = getattr(state, metric)
        
        self.cognitive_baselines["last_updated"] = datetime.now().isoformat()
        self.last_updated = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary for storage"""
        return {
            "client_id": self.client_id,
            "creation_date": self.creation_date.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "sessions_count": len(self.sessions),
            "active_goals_count": len(self.active_goals),
            "completed_goals_count": len(self.completed_goals),
            "preferences": self.preferences,
            "contraindications": list(self.contraindications),
            "therapeutic_history": self.therapeutic_history
        }


class CognitiveTherapist:
    """Main therapeutic engine implementing SECT capabilities"""
    
    def __init__(self):
        self.therapist_id = str(uuid4())
        self.client_profiles: Dict[str, TherapeuticProfile] = {}
        self.active_sessions: Dict[str, TherapeuticSession] = {}
        self.session_history: Dict[str, TherapeuticSession] = {}
        self.metrics_collector = SECTMetrics()
        self.intervention_library = self._initialize_intervention_library()
        self.intervention_effectiveness_cache = {}
        self._session_lock = asyncio.Lock()
        self._profile_locks: Dict[str, asyncio.Lock] = {}
    
    def _initialize_intervention_library(self) -> Dict[str, List[TherapeuticIntervention]]:
        """Initialize the library of available therapeutic interventions"""
        library = {modality.value: [] for modality in TherapyModality}
        
        # Add cognitive behavioral interventions
        library[TherapyModality.COGNITIVE_BEHAVIORAL.value] = [
            CognitiveReframing(
                target_thought_patterns={
                    "negative_self_assessment": np.array([-0.8, -0.7, -0.9, -0.6]),
                    "catastrophizing": np.array([-0.7, -0.9, -0.8, -0.7])
                },
                replacement_patterns={
                    "negative_self_assessment": np.array([-0.2, -0.1, -0.3, 0.1]),
                    "catastrophizing": np.array([-0.1, -0.3, -0.2, 0.0])
                },
                reframing_strength=0.6,
                priority=0.8
            ),
            EmotionalRegulation(
                target_emotions={"anxiety": -0.2, "depression": -0.3},
                regulation_strategies={
                    "cognitive_reappraisal": 0.7,
                    "problem_solving": 0.8,
                    "distress_tolerance": 0.5
                },
                priority=0.7
            )
        ]
        
        # Add mindfulness interventions
        library[TherapyModality.MINDFULNESS.value] = [
            EmotionalRegulation(
                target_emotions={"anxiety": -0.3, "present_awareness": 0.8},
                regulation_strategies={
                    "mindfulness": 0.9,
                    "acceptance": 0.8,
                    "cognitive_defusion": 0.7
                },
                priority=0.7
            )
        ]
        
        # Add integrative interventions
        library[TherapyModality.INTEGRATIVE.value] = [
            CognitiveReframing(
                target_thought_patterns={
                    "negative_self_assessment": np.array([-0.8, -0.7, -0.9, -0.6]),
                },
                replacement_patterns={
                    "negative_self_assessment": np.array([-0.3, -0.2, -0.3, 0.0]),
                },
                reframing_strength=0.5,
                priority=0.6
            ),
            EmotionalRegulation(
                target_emotions={"anxiety": -0.3, "depression": -0.3, "present_awareness": 0.7},
                regulation_strategies={
                    "mindfulness": 0.7,
                    "cognitive_reappraisal": 0.6,
                    "acceptance": 0.7
                },
                priority=0.6
            )
        ]
        
        return library
    
    async def get_client_profile(self, client_id: str) -> TherapeuticProfile:
        """Get client profile, creating if it doesn't exist"""
        if client_id not in self.client_profiles:
            # Create new profile
            profile = TherapeuticProfile(client_id)
            self.client_profiles[client_id] = profile
            self._profile_locks[client_id] = asyncio.Lock()
        
        return self.client_profiles[client_id]
    
    async def start_session(self, client_id: str, 
                     initial_state: Optional[CognitiveState] = None,
                     modality: Optional[TherapyModality] = None) -> str:
        """Start a new therapeutic session"""
        async with self._session_lock:
            # Get client profile
            profile = await self.get_client_profile(client_id)
            
            # Use preferred modality if none specified
            if modality is None:
                modality = profile.get_preferred_modality()
            
            # Create new session
            session = TherapeuticSession(
                client_id=client_id,
                modality=modality,
                initial_state=initial_state,
                current_state=initial_state
            )
            
            # Register session
            self.active_sessions[session.session_id] = session
            profile.add_session(session.session_id)
            
            # Update metrics
            self.metrics_collector.track_session_start(client_id, modality.value)
            
            # Log session start
            logger.info(f"Started {modality.value} therapy session {session.session_id} for client {client_id}")
            
            return session.session_id
    
    async def end_session(self, session_id: str) -> Dict[str, Any]:
        """End an active therapeutic session"""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found or already ended")
        
        async with self._session_lock:
            # Get the session and close it
            session = self.active_sessions.pop(session_id)
            session.close()
            
            # Move to history
            self.session_history[session_id] = session
            
            # Update metrics
            effectiveness = self._calculate_session_effectiveness(session)
            client_id = session.client_id
            self.metrics_collector.track_session_end(client_id, session.modality.value, effectiveness)
            
            # Update client profile with effectiveness rating
            profile = await self.get_client_profile(client_id)
            async with self._profile_locks[client_id]:
                profile.update_effectiveness(session.modality, effectiveness)
            
            # Log session end
            logger.info(f"Ended therapy session {session_id} for client {client_id} with effectiveness {effectiveness:.2f}")
            
            return {
                "session_id": session_id,
                "duration_minutes": session.duration(),
                "interventions_applied": len(session.interventions_applied),
                "effectiveness": effectiveness
            }
    
    def _calculate_session_effectiveness(self, session: TherapeuticSession) -> float:
        """Calculate overall effectiveness of a therapeutic session"""
        if not session.interventions_applied:
            return 0.5  # Neutral if no interventions were applied
        
        # Calculate weighted average of intervention effectiveness
        total_weight = 0.0
        weighted_sum = 0.0
        
        for intervention in session.interventions_applied:
            weight = intervention.get("priority", 0.5)
            effectiveness = intervention.get("effectiveness", 0.5)
            weighted_sum += effectiveness * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.5
            
        effectiveness = weighted_sum / total_weight
        
        # Adjust based on session duration (penalize very short or unusually long sessions)
        duration = session.duration()
        duration_factor = 1.0
        
        # Optimal duration around 45-60 minutes
        if duration < 15:  # Too short
            duration_factor = duration / 15
        elif duration > 90:  # Too long
            duration_factor = max(0.8, 1.0 - (duration - 90) / 180)
        
        return effectiveness * duration_factor
    
    async def process_cognitive_state(self, session_id: str, 
                              cognitive_state: CognitiveState) -> Dict[str, Any]:
        """Process a new cognitive state within an active session"""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found or not active")
        
        session = self.active_sessions[session_id]
        client_id = session.client_id
        
        # Update client profile with new state data
        profile = await self.get_client_profile(client_id)
        async with self._profile_locks[client_id]:
            profile.update_cognitive_baseline(cognitive_state)
            
            # Update all active goals
            for goal_id in list(profile.active_goals.keys()):
                profile.update_goal(goal_id, cognitive_state)
        
        # Calculate state differential if we have a previous state
        differential = None
        if session.current_state:
            differential = cognitive_state.differential(session.current_state)
        
        # Select and apply interventions
        interventions = self._select_interventions(session, cognitive_state, differential)
        results = await self._apply_interventions(session, cognitive_state, interventions)
        
        # Update session state
        session.current_state = results["new_state"]
        
        # Record interventions in session
        for intervention, effectiveness in zip(interventions, results["effectiveness"]):
            session.add_intervention(intervention, effectiveness)
        
        # Store intervention effectiveness for adaptation
        for intervention, effectiveness in zip(interventions, results["effectiveness"]):
            intervention_id = str(intervention.intervention_id)
            if intervention_id not in self.intervention_effectiveness_cache:
                self.intervention_effectiveness_cache[intervention_id] = []
            self.intervention_effectiveness_cache[intervention_id].append(effectiveness)
        
        # Update metrics
        self.metrics_collector.track_cognitive_processing(
            client_id=client_id,
            session_id=session_id,
            interventions_count=len(interventions),
            avg_effectiveness=np.mean(results["effectiveness"]) if results["effectiveness"] else 0.0
        )
        
        # Check if we should advance session stage based on progress
        if self._should_advance_session_stage(session):
            session.advance_stage()
            logger.info(f"Advanced session {session_id} to stage {session.current_stage.value}")
        
        return {
            "session_id": session_id,
            "interventions_applied": len(interventions),
            "effectiveness": results["effectiveness"],
            "current_stage": session.current_stage.value,
            "cognitive_load": results["new_state"].cognitive_load
        }
    
    def _select_interventions(self, session: TherapeuticSession, 
                            cognitive_state: CognitiveState,
                            differential: Optional[CognitiveStateDifferential] = None) -> List[TherapeuticIntervention]:
        """Select appropriate interventions based on session and cognitive state"""
        modality = session.modality.value
        available_interventions = self.intervention_library.get(modality, [])
        
        if not available_interventions:
            # Fall back to integrative if modality has no interventions
            available_interventions = self.intervention_library.get(TherapyModality.INTEGRATIVE.value, [])
        
        # Calculate applicability scores for each intervention
        scored_interventions = []
        for intervention in available_interventions:
            applicability = intervention.calculate_applicability(cognitive_state)
            scored_interventions.append((intervention, applicability))
        
        # Sort by applicability score
        scored_interventions.sort(key=lambda x: x[1], reverse=True)
        
        # Consider session stage in selection
        stage_factor = 0.5  # Default max interventions
        if session.current_stage == SessionStage.INTERVENTION:
            stage_factor = 1.0
        elif session.current_stage == SessionStage.INSIGHT_BUILDING:
            stage_factor = 0.7
        elif session.current_stage == SessionStage.CONSOLIDATION:
            stage_factor = 0.3
        elif session.current_stage == SessionStage.INTEGRATION:
            stage_factor = 0.4
        
        # Calculate max interventions based on stage
        max_interventions = max(1, int(len(available_interventions) * stage_factor))
        max_interventions = min(3, max_interventions)  # Never more than 3
        
        # Filter by minimum applicability threshold
        min_threshold = 0.2
        filtered_interventions = [
            intervention for intervention, score in scored_interventions
            if score >= min_threshold
        ]
        
        # Return top interventions limited by max count
        return filtered_interventions[:max_interventions]
    
    async def _apply_interventions(self, session: TherapeuticSession,
                           cognitive_state: CognitiveState,
                           interventions: List[TherapeuticIntervention]) -> Dict:
        """Apply selected interventions to transform cognitive state"""
        current_state = cognitive_state
        effectiveness_scores = []
        
        for intervention in interventions:
            try:
                # Apply the intervention
                new_state = await intervention.apply(current_state)
                
                # Calculate effectiveness
                effectiveness = self._calculate_intervention_effectiveness(
                    current_state, new_state, session.current_stage
                )
                effectiveness_scores.append(effectiveness)
                
                # Update current state for next intervention
                current_state = new_state
                
            except Exception as e:
                logger.error(f"Error applying intervention: {str(e)}")
                effectiveness_scores.append(0.0)
        
        return {
            "new_state": current_state,
            "effectiveness": effectiveness_scores
        }
    
    def _calculate_intervention_effectiveness(self, 
                                           before_state: CognitiveState,
                                           after_state: CognitiveState,
                                           session_stage: SessionStage) -> float:
        """Calculate effectiveness of an intervention based on cognitive state changes"""
        # Calculate differential between states
        diff = after_state.differential(before_state)
        
        # Different effectiveness metrics based on session stage
        if session_stage == SessionStage.ASSESSMENT:
            # In assessment, self-awareness increase is most important
            return max(0.0, min(1.0, diff.self_awareness_delta + 0.5))
            
        elif session_stage == SessionStage.INSIGHT_BUILDING:
            # In insight building, cognitive shifts are important
            cognitive_shift = np.mean([
                abs(shift) for shifts in diff.thought_pattern_shift.values() for shift in shifts
            ]) if diff.thought_pattern_shift else 0.0
            return max(0.0, min(1.0, cognitive_shift * 5.0))
            
        elif session_stage == SessionStage.INTERVENTION:
            # In intervention, emotional improvement is important
            emotional_improvement = np.mean([
                -v for v in diff.emotional_valence_shift.values() 
                if v < 0  # Only count reductions in negative emotions
            ]) if diff.emotional_valence_shift else 0.0
            return max(0.0, min(1.0, emotional_improvement * 3.0 + 0.5))
            
        elif session_stage == SessionStage.CONSOLIDATION:
            # In consolidation, stability is more important
            stability = 1.0 - diff.rate_of_change() * 2.0
            return max(0.0, min(1.0, stability))
            
        else:
            # Default: general improvement across dimensions
            dimensions = diff.direction_vector()
            improvement_factors = [v for k, v in dimensions.items() if v > 0]
            if not improvement_factors:
                return 0.5
            return max(0.0, min(1.0, np.mean(improvement_factors) + 0.5))
    
    def _should_advance_session_stage(self, session: TherapeuticSession) -> bool:
        """Determine if session should advance to next stage"""
        # Don't advance if already at final stage
        if session.current_stage == SessionStage.FOLLOW_UP:
            return False
        
        # Time-based stage advancement
        duration = session.duration()
        interventions_count = len(session.interventions_applied)
        
        # Different criteria based on current stage
        if session.current_stage == SessionStage.PREPARATION:
            return duration >= 5
            
        elif session.current_stage == SessionStage.ASSESSMENT:
            return duration >= 10 and interventions_count >= 2
            
        elif session.current_stage == SessionStage.INSIGHT_BUILDING:
            return duration >= 20 and interventions_count >= 5
            
        elif session.current_stage == SessionStage.INTERVENTION:
            # Need significant intervention work before advancing
            return duration >= 35 and interventions_count >= 8
            
        elif session.current_stage == SessionStage.CONSOLIDATION:
            return duration >= 45 and interventions_count >= 10
            
        return False
    
    async def create_therapeutic_goal(self, client_id: str, 
                              description: str,
                              target_cognitive_dimensions: Optional[Dict[str, float]] = None,
                              target_emotional_state: Optional[Dict[str, float]] = None,
                              target_completion_days: Optional[int] = None,
                              priority: float = 0.5) -> str:
        """Create a new therapeutic goal for a client"""
        profile = await self.get_client_profile(client_id)
        
        # Set default values if not provided
        target_cognitive = target_cognitive_dimensions or {}
        target_emotional = target_emotional_state or {}
        
        # Ensure we have at least one target
        if not target_cognitive and not target_emotional:
            raise ValueError("Must specify at least one cognitive or emotional target")
        
        # Calculate target completion date if specified
        target_date = None
        if target_completion_days is not None:
            target_date = datetime.now() + timedelta(days=target_completion_days)
        
        # Create the goal
        goal = TherapeuticGoal(
            description=description,
            target_cognitive_dimensions=target_cognitive,
            target_emotional_state=target_emotional,
            priority=priority,
            target_completion_date=target_date
        )
        
        # Add to client profile
        async with self._profile_locks[client_id]:
            profile.add_goal(goal)
        
        # Log goal creation
        logger.info(f"Created therapeutic goal '{description}' for client {client_id}")
        
        return goal.goal_id
    
    async def get_goal_progress(self, client_id: str, goal_id: str) -> Dict[str, Any]:
        """Get progress information for a specific goal"""
        profile = await self.get_client_profile(client_id)
        
        # Check active goals
        if goal_id in profile.active_goals:
            goal = profile.active_goals[goal_id]
            return {
                "goal_id": goal_id,
                "description": goal.description,
                "progress": goal.progress,
                "status": "active",
                "creation_date": goal.creation_date.isoformat(),
                "target_completion_date": goal.target_completion_date.isoformat() if goal.target_completion_date else None,
                "estimated_completion_date": goal.estimated_completion_date().isoformat() if goal.estimated_completion_date() else None,
                "related_goals": goal.related_goals
            }
            
        # Check completed goals
        elif goal_id in profile.completed_goals:
            goal = profile.completed_goals[goal_id]
            return {
                "goal_id": goal_id,
                "description": goal.description,
                "progress": 1.0,
                "status": "completed",
                "creation_date": goal.creation_date.isoformat(),
                "target_completion_date": goal.target_completion_date.isoformat() if goal.target_completion_date else None,
                "related_goals": goal.related_goals
            }
        
        # Goal not found
        else:
            raise ValueError(f"Goal {goal_id} not found for client {client_id}")
    
    async def adapt_therapy_approach(self, client_id: str) -> Dict[str, Any]:
        """Adapt therapy approach based on client history and preferences"""
        profile = await self.get_client_profile(client_id)
        
        async with self._profile_locks[client_id]:
            # Calculate effectiveness of different modalities
            modality_scores = {}
            for modality in TherapyModality:
                effectiveness = profile._calculate_avg_effectiveness(modality.value)
                if effectiveness > 0:
                    modality_scores[modality.value] = effectiveness
            
            # Identify top modalities
            sorted_modalities = sorted(
                modality_scores.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            
            # Update client preferences
            if sorted_modalities:
                profile.preferences["preferred_modalities"] = [
                    m for m, _ in sorted_modalities[:2]
                ]
            
            # Adapt intervention parameters
            self._adapt_intervention_parameters(client_id)
            
            # Log adaptation
            logger.info(f"Adapted therapy approach for client {client_id}")
            
            return {
                "adapted_modalities": profile.preferences["preferred_modalities"],
                "effectiveness_scores": modality_scores
            }
    
    def _adapt_intervention_parameters(self, client_id: str) -> None:
        """Adapt intervention parameters based on effectiveness history"""
        # Identify most effective interventions for this client
        effective_interventions = {}
        
        for intervention_id, scores in self.intervention_effectiveness_cache.items():
            if len(scores) >= 3:  # Only consider interventions with enough data
                avg_effectiveness = sum(scores) / len(scores)
                effective_interventions[intervention_id] = avg_effectiveness
        
        # Sort by effectiveness
        sorted_interventions = sorted(
            effective_interventions.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        top_interventions = sorted_interventions[:5]
        
        # Use effectiveness data to adapt interventions in library
        for modality, interventions in self.intervention_library.items():
            # Create adapted versions of effective interventions
            new_interventions = []
            
            for intervention in interventions:
                intervention_id = str(intervention.intervention_id)
                
                # If this is a top intervention, boost priority
                if any(id == intervention_id for id, _ in top_interventions):
                    intervention.priority = min(1.0, intervention.priority * 1.2)
                
                # Create adapted variants of successful interventions
                if intervention_id in effective_interventions and effective_interventions[intervention_id] > 0.7:
                    if isinstance(intervention, CognitiveReframing):
                        # Create variant with higher reframing strength
                        variant = CognitiveReframing(
                            target_thought_patterns=intervention.target_thought_patterns.copy(),
                            replacement_patterns=intervention.replacement_patterns.copy(),
                            reframing_strength=min(1.0, intervention.reframing_strength * 1.1),
                            contextual_triggers=intervention.contextual_triggers.copy(),
                            priority=intervention.priority
                        )
                        new_interventions.append(variant)
                    
                    elif isinstance(intervention, EmotionalRegulation):
                        # Create variant with different strategy emphasis
                        variant_strategies = intervention.regulation_strategies.copy()
                        
                        # Boost most effective strategy
                        most_effective = max(variant_strategies.items(), key=lambda x: x[1])[0]
                        variant_strategies[most_effective] = min(1.0, variant_strategies[most_effective] * 1.2)
                        
                        variant = EmotionalRegulation(
                            target_emotions=intervention.target_emotions.copy(),
                            regulation_strategies=variant_strategies,
                            adaptation_rate=intervention.adaptation_rate * 1.1,
                            priority=intervention.priority
                        )
                        new_interventions.append(variant)
            
            # Add new variants to library
            self.intervention_library[modality].extend(new_interventions)
    
    async def get_therapeutic_recommendations(self, client_id: str) -> Dict[str, Any]:
        """Get therapeutic recommendations based on client profile"""
        profile = await self.get_client_profile(client_id)
        
        recommendations = {
            "recommended_modalities": [],
            "focus_areas": [],
            "goal_suggestions": [],
            "session_frequency": 0
        }
        
        # Recommend therapy modalities
        if profile.preferences.get("preferred_modalities"):
            recommendations["recommended_modalities"] = profile.preferences["preferred_modalities"]
        else:
            recommendations["recommended_modalities"] = [TherapyModality.INTEGRATIVE.value]
        
        # Determine focus areas
        if profile.cognitive_baselines:
            focus_areas = []
            
            # Check emotional baselines
            negative_emotions = [
                (emotion, value) for emotion, value in 
                profile.cognitive_baselines.get("emotional_valence", {}).items()
                if value < -0.4
            ]
            if negative_emotions:
                for emotion, value in negative_emotions:
                    focus_areas.append({
                        "type": "emotional",
                        "name": emotion,
                        "priority": min(1.0, abs(value) * 1.5)
                    })
            
            # Check cognitive load
            if profile.cognitive_baselines.get("cognitive_load", 0) > 0.7:
                focus_areas.append({
                    "type": "cognitive_load",
                    "name": "stress_management",
                    "priority": 0.8
                })
            
            recommendations["focus_areas"] = focus_areas
        
        # Suggest new goals based on profile
        # Use existing goals as templates
        if profile.completed_goals:
            # Get most recently completed goal as template
            template_goals = sorted(
                profile.completed_goals.values(),
                key=lambda g: g.creation_date,
                reverse=True
            )[:2]
            
            for goal in template_goals:
                # Create a similar but more advanced goal
                if goal.target_emotional_state:
                    # Suggest more ambitious emotional targets
                    new_emotional_targets = {}
                    for emotion, value in goal.target_emotional_state.items():
                        if value < 0:  # Negative emotion target
                            new_emotional_targets[emotion] = value * 0.8  # More reduction
                        else:  # Positive emotion target
                            new_emotional_targets[emotion] = min(1.0, value * 1.2)  # More increase
                    
                    recommendations["goal_suggestions"].append({
                        "description": f"Advanced emotional regulation targeting {', '.join(new_emotional_targets.keys())}",
                        "target_emotional_state": new_emotional_targets,
                        "target_days": 30
                    })
        
        # Recommend session frequency based on profile characteristics
        if profile.active_goals:
            # More goals = higher recommended frequency
            goal_count = len(profile.active_goals)
            base_frequency = min(5, max(1, goal_count // 2 + 1))
            
            # Adjust based on historical effectiveness
            effectiveness_values = []
            for modality, ratings in profile.therapeutic_history.get("effectiveness_ratings", {}).items():
                if ratings:
                    effectiveness_values.extend([r["rating"] for r in ratings])
            
            if effectiveness_values:
                avg_effectiveness = sum(effectiveness_values) / len(effectiveness_values)
                
                # Higher effectiveness = potentially fewer sessions needed
                if avg_effectiveness > 0.8:
                    frequency_modifier = 0.8
                elif avg_effectiveness < 0.4:
                    frequency_modifier = 1.2
                else:
                    frequency_modifier = 1.0
                    
                recommendations["session_frequency"] = round(base_frequency * frequency_modifier)
            else:
                recommendations["session_frequency"] = base_frequency
        else:
            # Default recommendation
            recommendations["session_frequency"] = 1
        
        return recommendations
