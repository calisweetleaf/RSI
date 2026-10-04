from __future__ import annotations

import importlib.util
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class ContradictionSignal:
    """Structured contradiction signal surfaced by the URSMIF sentinel."""

    contradictions: List[str]
    severity: float
    detected_at: float
    pattern_type: str = "contradiction"
    metadata: Dict[str, Any] = field(default_factory=dict)


class URSMIFContradictionSentinel:
    """Detect contradictions using URSMIF and relay them into SECT workflows."""

    def __init__(
        self,
        *,
        contradiction_threshold: float = 0.3,
        repetition_threshold: float = 0.8,
        srd_threshold: float = 0.05,
        max_history: int = 100,
        belief_high: float = 0.65,
        belief_low: float = 0.35,
        goal_high: float = 0.65,
        goal_low: float = 0.35,
        memory_truth_threshold: float = 0.7,
        ursmif_path: Optional[Path] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self._validate_threshold("contradiction_threshold", contradiction_threshold)
        self._validate_threshold("repetition_threshold", repetition_threshold)
        self._validate_threshold("srd_threshold", srd_threshold)
        self._validate_threshold("belief_high", belief_high)
        self._validate_threshold("belief_low", belief_low)
        self._validate_threshold("goal_high", goal_high)
        self._validate_threshold("goal_low", goal_low)
        self._validate_threshold("memory_truth_threshold", memory_truth_threshold)
        if max_history <= 0:
            raise ValueError("max_history must be greater than zero")

        self._contradiction_threshold = contradiction_threshold
        self._repetition_threshold = repetition_threshold
        self._srd_threshold = srd_threshold
        self._max_history = max_history
        self._belief_high = belief_high
        self._belief_low = belief_low
        self._goal_high = goal_high
        self._goal_low = goal_low
        self._memory_truth_threshold = memory_truth_threshold
        self._logger = logger or logging.getLogger(__name__)

        self._monitor = None
        self._system_state_cls = None
        self._history: List[Set[Tuple[str, bool]]] = []

        self._load_ursmif(ursmif_path)

    def analyze_state(self, state: Any) -> Optional[ContradictionSignal]:
        """Analyze cognitive state and return contradiction signals when found."""
        if state is None:
            raise ValueError("state is required")

        knowledge_base = self._build_knowledge_base(state)
        self._record_history(knowledge_base)
        contradictions = self._find_contradictions(knowledge_base)

        if hasattr(state, "knowledge_base"):
            state.knowledge_base = knowledge_base

        if self._monitor and self._system_state_cls:
            signal = self._analyze_with_ursmif(state, knowledge_base, contradictions)
            if signal:
                return signal

        return self._analyze_with_fallback(knowledge_base, contradictions)

    def _analyze_with_ursmif(
        self,
        state: Any,
        knowledge_base: Set[Tuple[str, bool]],
        contradictions: List[str],
    ) -> Optional[ContradictionSignal]:
        try:
            system_state = self._system_state_cls(
                outputs=self._build_outputs(state),
                knowledge_base=knowledge_base,
                self_references=self._count_self_references(state),
                timestamp=time.time(),
            )
            patterns = self._monitor.monitor(system_state)
        except Exception as exc:
            self._logger.warning("URSMIF monitoring failed, falling back: %s", exc)
            self._monitor = None
            self._system_state_cls = None
            return None

        contradiction_pattern = next(
            (pattern for pattern in patterns if getattr(pattern, "pattern_type", "") == "contradiction"),
            None,
        )
        if not contradiction_pattern or not contradictions:
            return None

        return ContradictionSignal(
            contradictions=contradictions,
            severity=float(getattr(contradiction_pattern, "severity", 0.0)),
            detected_at=time.time(),
            metadata={
                "source": "ursmif_monitor",
                "pattern_instances": list(getattr(contradiction_pattern, "instances", [])),
            },
        )

    def _analyze_with_fallback(
        self,
        knowledge_base: Set[Tuple[str, bool]],
        contradictions: List[str],
    ) -> Optional[ContradictionSignal]:
        if not contradictions:
            return None

        contradiction_density = self._contradiction_density(knowledge_base)
        if contradiction_density <= self._contradiction_threshold:
            return None

        return ContradictionSignal(
            contradictions=contradictions,
            severity=contradiction_density,
            detected_at=time.time(),
            metadata={"source": "fallback"},
        )

    def _load_ursmif(self, ursmif_path: Optional[Path]) -> None:
        path = ursmif_path or self._default_ursmif_path()
        if not path or not path.exists():
            self._logger.warning("URSMIF module not found at %s", path)
            return

        try:
            spec = importlib.util.spec_from_file_location("ursmif_theory", str(path))
            if not spec or not spec.loader:
                self._logger.warning("URSMIF module spec could not be created")
                return
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except Exception as exc:
            self._logger.warning("URSMIF module load failed: %s", exc)
            return

        monitor_cls = getattr(module, "URSMIFMonitor", None)
        system_state_cls = getattr(module, "SystemState", None)
        if not monitor_cls or not system_state_cls:
            self._logger.warning("URSMIF module missing required classes")
            return

        try:
            self._monitor = monitor_cls(
                repetition_threshold=self._repetition_threshold,
                contradiction_threshold=self._contradiction_threshold,
                srd_threshold=self._srd_threshold,
                max_history=self._max_history,
            )
            self._system_state_cls = system_state_cls
        except Exception as exc:
            self._logger.warning("URSMIF monitor initialization failed: %s", exc)

    def _default_ursmif_path(self) -> Path:
        root = Path(__file__).resolve().parents[3]
        return root / "rosemary_integration" / "ursmif-theory.py"

    def _build_outputs(self, state: Any) -> List[str]:
        outputs: List[str] = []
        attention_focus = getattr(state, "attention_focus", []) or []
        thought_patterns = getattr(state, "thought_patterns", {}) or {}
        memory_activation = getattr(state, "memory_activation", {}) or {}

        if attention_focus:
            outputs.append("attention:" + " ".join(str(item) for item in attention_focus))
        if thought_patterns:
            outputs.append("patterns:" + " ".join(str(item) for item in thought_patterns.keys()))
        if memory_activation:
            outputs.append("memory:" + " ".join(str(item) for item in memory_activation.keys()))

        if not outputs:
            outputs.append("no_output")

        return outputs

    def _count_self_references(self, state: Any) -> int:
        tokens: List[str] = []
        attention_focus = getattr(state, "attention_focus", []) or []
        belief_confidence = getattr(state, "belief_confidence", {}) or {}
        goal_alignment = getattr(state, "goal_alignment", {}) or {}
        memory_activation = getattr(state, "memory_activation", {}) or {}

        tokens.extend(str(item) for item in attention_focus)
        tokens.extend(str(item) for item in belief_confidence.keys())
        tokens.extend(str(item) for item in goal_alignment.keys())
        tokens.extend(str(item) for item in memory_activation.keys())

        return sum(1 for token in tokens if "self" in token.lower())

    def _build_knowledge_base(self, state: Any) -> Set[Tuple[str, bool]]:
        knowledge_base: Set[Tuple[str, bool]] = set()

        existing_kb = getattr(state, "knowledge_base", None)
        if existing_kb:
            for prop, truth in existing_kb:
                knowledge_base.add((str(prop), bool(truth)))

        belief_confidence = getattr(state, "belief_confidence", {}) or {}
        goal_alignment = getattr(state, "goal_alignment", {}) or {}
        memory_activation = getattr(state, "memory_activation", {}) or {}

        all_keys = set(belief_confidence.keys()) | set(goal_alignment.keys())
        for key in all_keys:
            prop = str(key)
            belief_truth = self._infer_truth(
                belief_confidence.get(key),
                high=self._belief_high,
                low=self._belief_low,
            )
            goal_truth = self._infer_truth(
                goal_alignment.get(key),
                high=self._goal_high,
                low=self._goal_low,
            )
            if belief_truth is not None and goal_truth is not None and belief_truth != goal_truth:
                knowledge_base.add((prop, True))
                knowledge_base.add((prop, False))
            else:
                if belief_truth is not None:
                    knowledge_base.add((prop, belief_truth))
                if goal_truth is not None:
                    knowledge_base.add((prop, goal_truth))

        for key, value in memory_activation.items():
            if isinstance(value, (int, float)) and value >= self._memory_truth_threshold:
                knowledge_base.add((str(key), True))

        return knowledge_base

    def _record_history(self, knowledge_base: Set[Tuple[str, bool]]) -> None:
        self._history.append(knowledge_base)
        if len(self._history) > self._max_history:
            self._history.pop(0)

    def _contradiction_density(self, knowledge_base: Set[Tuple[str, bool]]) -> float:
        recent = self._history[-10:] if len(self._history) >= 10 else self._history
        if not recent:
            return 0.0

        contradiction_count = sum(1 for kb in recent if self._has_contradiction(kb))
        return contradiction_count / len(recent)

    def _has_contradiction(self, knowledge_base: Set[Tuple[str, bool]]) -> bool:
        propositions: Dict[str, bool] = {}
        for prop, truth_value in knowledge_base:
            if prop in propositions and propositions[prop] != truth_value:
                return True
            propositions[prop] = truth_value
        return False

    def _find_contradictions(self, knowledge_base: Set[Tuple[str, bool]]) -> List[str]:
        propositions: Dict[str, bool] = {}
        contradictions: List[str] = []
        for prop, truth_value in knowledge_base:
            if prop in propositions and propositions[prop] != truth_value:
                contradictions.append(prop)
            else:
                propositions[prop] = truth_value
        return sorted(set(contradictions))

    @staticmethod
    def _infer_truth(value: Any, *, high: float, low: float) -> Optional[bool]:
        if not isinstance(value, (int, float)):
            return None
        if value >= high:
            return True
        if value <= low:
            return False
        return None

    @staticmethod
    def _validate_threshold(name: str, value: float) -> None:
        if not isinstance(value, (int, float)):
            raise ValueError(f"{name} must be a number")
        if value < 0.0 or value > 1.0:
            raise ValueError(f"{name} must be between 0.0 and 1.0")
