# src/integration/translator.py
"""
Protocol Translation Engine

Handles data format conversion between biological and cognitive systems with:
- Multi-modal data transformation
- Context-aware translation
- Emergent property containment
"""

from datetime import datetime
from typing import Dict, Any, Optional, List, Union
import uuid
import logging
from pydantic import BaseModel, Field, validator
from enum import Enum
import numpy as np

# Use absolute imports for cross-package access
from biocognitive_core.components.sis.network import CellState, NanobotNode
from biocognitive_core.components.ntp.interface import ThoughtDomain
from biocognitive_core.components.sect.agent import TherapyGoal
from biocognitive_core.exceptions import BiocognitiveError, SystemBoundaryViolation
from infrastructure.observability import log_event, log_error

logger = logging.getLogger(__name__)

class TranslationDirection(Enum):
    """Supported translation paths"""
    BIOLOGICAL_TO_COGNITIVE = "BIO->COG"
    COGNITIVE_TO_BIOLOGICAL = "COG->BIO"
    COGNITIVE_TO_COGNITIVE = "COG->COG"

class TranslationContext(BaseModel):
    """Contextual information for translation operations"""
    source_type: str
    target_type: str
    urgency: float = Field(ge=0.0, le=1.0)
    domain: Optional[ThoughtDomain] = None
    cell_state: Optional[CellState] = None
    therapy_goal: Optional[TherapyGoal] = None

class TranslationEngine:
    """Multi-layered translation system with containment protocols"""
    def __init__(self):
        self.translation_rules = self._load_translation_rules()
        self.emergence_monitor = EmergenceMonitor()

    def _load_translation_rules(self) -> Dict[str, Dict]:
        """Load pre-defined translation mappings"""
        return {
            "BIO->COG": {
                "mutating": {"domain": "PHYSIOLOGICAL", "urgency": 0.8},
                "stalled": {"domain": "PHYSIOLOGICAL", "urgency": 0.6},
                "replicating": {"domain": "COGNITIVE", "urgency": 0.5}
            },
            "COG->BIO": {
                "EMOTIONAL": {"action": "replication", "intensity": 0.3},
                "COGNITIVE": {"action": "mutation", "intensity": 0.2}
            }
        }

    def translate_signal(self, context: TranslationContext) -> Dict:
        """
        Convert between biological and cognitive representations
        
        >>> engine = TranslationEngine()
        >>> engine.translate_signal(TranslationContext(source_type="BIO", target_type="COG", cell_state=CellState.MUTATING))
        {'domain': 'PHYSIOLOGICAL', 'urgency': 0.8}
        """
        # Build the combined rule key
        rule_key = f"{context.source_type}->{context.target_type}"
        
        if rule_key not in self.translation_rules:
            raise SystemBoundaryViolation(
                f"No translation rules for {rule_key}",
                code="CORE-004",
                violating_component=rule_key
            )
            
        rule_set = self.translation_rules[rule_key]
        translation = {}
        
        if context.cell_state:
            translation.update(rule_set.get(context.cell_state.value, {}))
        if context.domain:
            translation.update(rule_set.get(context.domain.value, {}))
        if context.therapy_goal:
            translation.update(rule_set.get(context.therapy_goal.value, {}))
            
        translation["urgency"] = context.urgency * 1.1  # Urgency amplification
        translation["translation_id"] = str(uuid.uuid4())
        
        self.emergence_monitor.record_translation(translation)
        return translation

class EmergenceMonitor:
    """Tracks emergent properties across translation boundaries"""
    def __init__(self):
        self.emergence_history = []
        self.emergence_threshold = 0.75

    def record_translation(self, translation: Dict):
        """Log translation events for emergent property detection"""
        self.emergence_history.append({
            "timestamp": datetime.utcnow(),
            "translation": translation,
            "emergence_score": self._calculate_emergence_score(translation)
        })
        
        if len(self.emergence_history) > 100:
            self.emergence_history.pop(0)

    def _calculate_emergence_score(self, translation: Dict) -> float:
        """Calculate emergence potential of translation"""
        # Simplified emergence calculation
        return min(1.0, sum(translation.values()) / len(translation.values()))

    def check_emergence(self) -> bool:
        """Detect emergence risks in translation history"""
        if not self.emergence_history:
            return False
            
        recent_scores = [e["emergence_score"] for e in self.emergence_history[-10:]]
        avg_score = np.mean(recent_scores)
        
        if avg_score > self.emergence_threshold:
            log_event("emergence_risk", {"score": avg_score})
            return True
            
        return False