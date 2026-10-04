# src/biocognitive_core/metrics.py
"""
Biocognitive System Metrics Framework

Implements comprehensive monitoring and observability for:
- Synthetic Immune Symbionts (SIS)
- Neural Transparency Protocols (NTP)
- Self-Evolving Cognitive Therapists (SECT)
- System Integration Points

Includes distributed tracing, anomaly detection, and performance benchmarking
"""

from typing import Dict, Any, Optional, List, Union, Tuple, AsyncGenerator
from pydantic import BaseModel, Field, validator
from enum import Enum
import asyncio
import time
import threading
import json
from datetime import datetime, timedelta
import random
from collections import defaultdict
import numpy as np
from biocognitive_core.config import settings
from biocognitive_core.exceptions import BiocognitiveError, ConfigurationValidationError
from infrastructure.observability import log_metric, log_trace, log_error

class MetricType(Enum):
    """Classifies metric data types"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"
    EVENT = "event"

class Component(Enum):
    """Identifies system components for metric tagging"""
    SIS = "synthetic_immune_symbiont"
    NTP = "neural_transparency_protocol"
    SECT = "self_evolving_cognitive_therapist"
    INTEGRATION = "system_integration"
    CORE = "core_system"

class MetricMetadata(BaseModel):
    """Standardized metadata for all metrics"""
    component: Component
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(default=settings.version)
    environment: str = Field(default=settings.environment)
    tags: Dict[str, str] = Field(default_factory=dict)

class BaseMetric(BaseModel):
    """Abstract base class for all metric types"""
    name: str
    type: MetricType
    metadata: MetricMetadata
    value: Union[int, float, str, dict]

    @validator("metadata")
    def validate_metadata(cls, v):
        if not v.component or not v.version:
            raise ValueError("Metadata must include component and version")
        return v

class CounterMetric(BaseMetric):
    """Counts occurrences of events"""
    type: MetricType = Field(MetricType.COUNTER)
    delta: int = Field(1)

class GaugeMetric(BaseMetric):
    """Measures instantaneous values"""
    type: MetricType = Field(MetricType.GAUGE)
    current_value: float

class HistogramMetric(BaseMetric):
    """Records distribution of values"""
    type: MetricType = Field(MetricType.HISTOGRAM)
    values: List[float]
    buckets: List[float] = Field(default_factory=lambda: [0.1, 0.5, 1.0, 2.0, 5.0, 10.0])

class SummaryMetric(BaseMetric):
    """Tracks statistical summaries"""
    type: MetricType = Field(MetricType.SUMMARY)
    count: int
    sum: float
    quantiles: Dict[float, float] = Field(default_factory=lambda: {0.5: 0.0, 0.9: 0.0, 0.99: 0.0})

class EventMetric(BaseMetric):
    """Logs discrete events with context"""
    type: MetricType = Field(MetricType.EVENT)
    context: Dict[str, Any] = Field(default_factory=dict)

class MetricCollector:
    """Central metrics collection and aggregation engine"""
    _instance: Optional['MetricCollector'] = None
    
    def __init__(self):
        self.metrics: Dict[str, BaseMetric] = {}
        self.lock = threading.Lock()
        self.batch_interval = settings.observability.metric_interval.total_seconds()
        self.flush_task = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            self.flush_task = loop.create_task(self._flush_metrics())
    
    @classmethod
    def instance(cls) -> 'MetricCollector':
        """Get singleton instance of MetricCollector"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def start_flush_loop(self) -> None:
        """Start the async flush loop when an event loop is available."""
        if self.flush_task is not None:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        if loop.is_running():
            self.flush_task = loop.create_task(self._flush_metrics())

    async def _flush_metrics(self):
        """Periodically flush metrics to monitoring system"""
        while True:
            await asyncio.sleep(self.batch_interval)
            batch = self._aggregate_metrics()
            if batch:
                self._submit_to_monitoring(batch)
                self._clear_metrics()

    def _aggregate_metrics(self) -> List[BaseMetric]:
        """Aggregate metrics across all components"""
        with self.lock:
            aggregated = []
            for key, metric in self.metrics.items():
                if isinstance(metric, (CounterMetric, GaugeMetric)):
                    aggregated.append(metric.copy())
                elif isinstance(metric, HistogramMetric):
                    aggregated.append(self._process_histogram(metric))
                elif isinstance(metric, SummaryMetric):
                    aggregated.append(self._process_summary(metric))
                elif isinstance(metric, EventMetric):
                    aggregated.append(metric.copy())
            return aggregated

    def _process_histogram(self, metric: HistogramMetric) -> HistogramMetric:
        """Process histogram data into summary statistics"""
        if not metric.values:
            return metric
        return HistogramMetric(
            name=metric.name,
            metadata=metric.metadata,
            values=metric.values,
            buckets=metric.buckets,
            count=len(metric.values),
            mean=np.mean(metric.values),
            std=np.std(metric.values)
        )

    def _process_summary(self, metric: SummaryMetric) -> SummaryMetric:
        """Generate summary statistics from raw data"""
        if metric.count == 0:
            return metric
        return SummaryMetric(
            name=metric.name,
            metadata=metric.metadata,
            count=metric.count,
            sum=metric.sum,
            mean=metric.sum / metric.count,
            quantiles=metric.quantiles
        )

    def _submit_to_monitoring(self, batch: List[BaseMetric]):
        """Send metrics to monitoring system with error handling"""
        try:
            log_metric(batch)
        except Exception as e:
            log_error(f"Failed to submit metrics: {str(e)}", error=e)

    def _clear_metrics(self):
        """Reset metrics after flush"""
        with self.lock:
            self.metrics.clear()

    def record_counter(self, name: str, component: Component, delta: int = 1, tags: Optional[Dict] = None):
        """Record a counter metric"""
        key = f"{component.value}:{name}"
        with self.lock:
            if key not in self.metrics:
                self.metrics[key] = CounterMetric(
                    name=name,
                    metadata=MetricMetadata(component=component, tags=tags or {}),
                    value=0,
                    delta=delta
                )
            else:
                self.metrics[key].value += delta

    def record_gauge(self, name: str, component: Component, value: float, tags: Optional[Dict] = None):
        """Record a gauge metric"""
        key = f"{component.value}:{name}"
        with self.lock:
            self.metrics[key] = GaugeMetric(
                name=name,
                metadata=MetricMetadata(component=component, tags=tags or {}),
                value=value,
                current_value=value
            )

    def record_histogram(self, name: str, component: Component, value: float, tags: Optional[Dict] = None):
        """Record a histogram metric"""
        key = f"{component.value}:{name}"
        with self.lock:
            if key not in self.metrics:
                self.metrics[key] = HistogramMetric(
                    name=name,
                    metadata=MetricMetadata(component=component, tags=tags or {}),
                    values=[value]
                )
            else:
                self.metrics[key].values.append(value)

    def record_summary(self, name: str, component: Component, value: float, tags: Optional[Dict] = None):
        """Record a summary metric"""
        key = f"{component.value}:{name}"
        with self.lock:
            if key not in self.metrics:
                self.metrics[key] = SummaryMetric(
                    name=name,
                    metadata=MetricMetadata(component=component, tags=tags or {}),
                    count=1,
                    sum=value,
                    quantiles={}
                )
            else:
                metric = self.metrics[key]
                metric.count += 1
                metric.sum += value
                metric.quantiles = self._update_quantiles(metric.quantiles, value)

    def _update_quantiles(self, current: Dict[float, float], value: float) -> Dict[float, float]:
        """Update quantile estimates using P² algorithm"""
        # Simplified implementation for demonstration
        updated = current.copy()
        for q in [0.5, 0.9, 0.99]:
            if q not in updated:
                updated[q] = value
        return updated

    def record_event(self, name: str, component: Component, context: Dict[str, Any], tags: Optional[Dict] = None):
        """Record an event metric"""
        key = f"{component.value}:{name}"
        with self.lock:
            event = EventMetric(
                name=name,
                metadata=MetricMetadata(component=component, tags=tags or {}),
                value=1,
                context=context
            )
            self.metrics[key] = event

# Global metrics collector instance
collector = MetricCollector()


class CognitiveStateMetrics:
    """Track cognitive state transitions and metacognitive indicators."""
    def __init__(self) -> None:
        self.state_history: List[Dict[str, Any]] = []
        self.load_anomaly: float = 0.0

    def update_metacognitive_stats(
        self,
        pattern_coherence: float,
        load_anomaly: float,
        emotional_consistency: float,
        self_awareness: float,
    ) -> None:
        self.load_anomaly = load_anomaly
        self.state_history.append({
            "pattern_coherence": pattern_coherence,
            "load_anomaly": load_anomaly,
            "emotional_consistency": emotional_consistency,
            "self_awareness": self_awareness,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def record_state(self, before_state: Any, after_state: Any, vitals: Dict[str, Any]) -> None:
        self.state_history.append({
            "before": before_state,
            "after": after_state,
            "vitals": vitals,
            "timestamp": datetime.utcnow().isoformat(),
        })


class TherapeuticEffectivenessMetrics:
    """Track therapeutic interventions and effectiveness statistics."""
    def __init__(self) -> None:
        self.interventions: List[Dict[str, Any]] = []

    def record_intervention(self, intervention_type: str, effectiveness: float, duration: float) -> None:
        self.interventions.append({
            "type": intervention_type,
            "effectiveness": effectiveness,
            "duration": duration,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def get_recent_stats(self, window: int = 10) -> Dict[str, float]:
        if not self.interventions:
            return {"mean": 1.0, "count": 0}
        recent = self.interventions[-window:]
        mean_effectiveness = sum(i["effectiveness"] for i in recent) / len(recent)
        return {"mean": mean_effectiveness, "count": len(recent)}


class SelfEvolutionMetrics:
    """Track self-evolution cycles and modification outcomes."""
    def __init__(self) -> None:
        self.cycles: List[Dict[str, Any]] = []
        self.modifications: List[Dict[str, Any]] = []

    def record_cycle(self, intervention_count: int, recursion_depth: int, resources: float) -> None:
        self.cycles.append({
            "interventions": intervention_count,
            "recursion_depth": recursion_depth,
            "resources": resources,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def record_modification(self, level: int, success_metrics: Dict[str, Any]) -> None:
        self.modifications.append({
            "level": level,
            "success_metrics": success_metrics,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def modification_count(self, level: Any) -> int:
        return sum(1 for mod in self.modifications if mod["level"] == getattr(level, "value", level))

class SISMetrics:
    """Specialized metrics for Synthetic Immune Symbionts"""
    
    def __init__(self):
        self._metrics: Dict[str, Any] = {}
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Return all collected SIS metrics"""
        return self._metrics.copy()
    
    @staticmethod
    def track_replication(user_id: str, count: int):
        """Track nanobot replication events"""
        collector.record_counter(
            name="nanobot_replication",
            component=Component.SIS,
            delta=count,
            tags={"user": user_id}
        )

    @staticmethod
    def track_mutation(user_id: str, rate: float):
        """Track mutation rate metrics"""
        collector.record_gauge(
            name="mutation_rate",
            component=Component.SIS,
            value=rate,
            tags={"user": user_id}
        )

    @staticmethod
    def track_energy(user_id: str, level: float):
        """Track energy consumption"""
        collector.record_gauge(
            name="energy_level",
            component=Component.SIS,
            value=level,
            tags={"user": user_id}
        )

class NTPMetrics:
    """Specialized metrics for Neural Transparency Protocols"""
    
    def __init__(self):
        self._metrics: Dict[str, Any] = {}
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Return all collected NTP metrics"""
        return self._metrics.copy()
    
    @staticmethod
    def track_transmission(user_id: str, latency: float):
        """Track thought transmission latency"""
        collector.record_histogram(
            name="transmission_latency",
            component=Component.NTP,
            value=latency,
            tags={"user": user_id}
        )

    @staticmethod
    def track_encryption(user_id: str, level: str):
        """Track encryption level usage"""
        collector.record_gauge(
            name="encryption_level",
            component=Component.NTP,
            value=int(level[-1]),  # QRL1=1, QRL2=2, QRL3=3
            tags={"user": user_id}
        )

class SECTMetrics:
    """Specialized metrics for Self-Evolving Cognitive Therapists"""
    
    def __init__(self):
        self._metrics: Dict[str, Any] = {}
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Return all collected SECT metrics"""
        return self._metrics.copy()
    
    @staticmethod
    def track_intervention(user_id: str, duration: float):
        """Track therapy intervention duration"""
        collector.record_histogram(
            name="intervention_duration",
            component=Component.SECT,
            value=duration,
            tags={"user": user_id}
        )

    @staticmethod
    def track_alignment(user_id: str, score: float):
        """Track therapeutic alignment score"""
        collector.record_gauge(
            name="alignment_score",
            component=Component.SECT,
            value=score,
            tags={"user": user_id}
        )

    @staticmethod
    def track_event(event_name: str, context: Dict[str, Any]):
        """Track SECT lifecycle events."""
        collector.record_event(
            name=event_name,
            component=Component.SECT,
            context=context,
        )

    @staticmethod
    def track_therapy_completion(goal: str, success_rate: float):
        """Track completion outcomes for therapy sessions."""
        collector.record_event(
            name="therapy_completion",
            component=Component.SECT,
            context={"goal": goal, "success_rate": success_rate},
        )

class IntegrationMetrics:
    """Metrics for system integration points"""
    @staticmethod
    def track_boundary_crossing(user_id: str, count: int):
        """Track system boundary crossings"""
        collector.record_counter(
            name="boundary_crossings",
            component=Component.INTEGRATION,
            delta=count,
            tags={"user": user_id}
        )

    @staticmethod
    def track_identity_blend(user_id: str, score: float):
        """Track identity blending metrics"""
        collector.record_gauge(
            name="identity_blend_score",
            component=Component.INTEGRATION,
            value=score,
            tags={"user": user_id}
        )

# Example usage
if __name__ == "__main__":
    # Simulate SIS metrics
    SISMetrics.track_replication("user123", 150)
    SISMetrics.track_mutation("user123", 0.072)
    SISMetrics.track_energy("user123", 0.85)

    # Simulate NTP metrics
    NTPMetrics.track_transmission("user123", 0.012)
    NTPMetrics.track_encryption("user123", "QRL2")

    # Simulate SECT metrics
    SECTMetrics.track_intervention("user123", 4.2)
    SECTMetrics.track_alignment("user123", 0.91)

    # Simulate integration metrics
    IntegrationMetrics.track_boundary_crossing("user123", 1)
    IntegrationMetrics.track_identity_blend("user123", 0.68)

    # Wait for metrics to flush
    time.sleep(settings.observability.metric_interval.total_seconds() * 1.5)


# Aliases for compatibility
MetricsCollector = MetricCollector


class Span:
    """Tracing span for performance measurement"""
    def __init__(self, name: str, parent: Optional['Span'] = None):
        self.name = name
        self.parent = parent
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.attributes: Dict[str, Any] = {}
    
    def __enter__(self) -> 'Span':
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        return False
    
    def set_attribute(self, key: str, value: Any):
        self.attributes[key] = value
    
    @property
    def duration(self) -> float:
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time


class Timer:
    """Simple timer for measuring execution time"""
    def __init__(self, name: str = ""):
        self.name = name
        self.start_time: Optional[float] = None
        self.elapsed: float = 0.0
    
    def __enter__(self) -> 'Timer':
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            self.elapsed = time.time() - self.start_time
        return False
    
    def start(self):
        self.start_time = time.time()
    
    def stop(self) -> float:
        if self.start_time:
            self.elapsed = time.time() - self.start_time
        return self.elapsed


def track_event(event_name: str, properties: Optional[Dict[str, Any]] = None, 
                component: str = "unknown") -> None:
    """Track a discrete event with optional properties"""
    collector = MetricCollector()
    collector.track_event(
        name=event_name,
        component=Component.SIS,  # Default component
        context=properties or {}
    )