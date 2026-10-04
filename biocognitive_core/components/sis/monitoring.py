# src/biocognitive_core/components/sis/monitoring.py
"""
Synthetic Immune Symbiont Monitoring and Alerting System

Provides real-time health tracking, anomaly detection, and system-wide status reporting with:
- Distributed health monitoring
- Predictive failure detection
- Multi-tier alerting mechanisms
- Historical state analysis
Author: Morpheus
Date: 2025-05-08
Version: 1.0.0
Description: This module implements the monitoring and alerting system for the SIS component. It includes various health metrics, anomaly detection algorithms, and alerting mechanisms. The system is designed to provide real-time insights into the health of the nanobiotic network and facilitate rapid response to critical conditions.
ID: SIS-005
SHA-256: 958c3f4e5d6a7b8c9e0f1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3
"""

from typing import Any, Dict, Set, Optional, List, Tuple, Union, AsyncGenerator
from pydantic import BaseModel, Field, validator, root_validator
from enum import Enum
import asyncio
import numpy as np
from biocognitive_core.config import settings
from biocognitive_core.exceptions import BiocognitiveError, EvolutionConstraintViolation
from biocognitive_core.metrics import SISMetrics
from .network import NanobotNode, CellState, SISNetwork
from datetime import datetime, timedelta
import json
import hashlib

class AlertLevel(Enum):
    """Severity levels for system alerts"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class HealthStatus(Enum):
    """Overall system health states"""
    OPTIMAL = "optimal"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNSTABLE = "unstable"

class NodeHealthReport(BaseModel):
    """Comprehensive health assessment for a nanobot node"""
    node_id: str
    state: CellState
    energy_reserve: float
    last_activity: datetime
    mutation_history: List[Tuple[datetime, str]]
    anomalies: List[str]
    containment_score: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @validator("energy_reserve")
    def validate_energy_reserve(cls, v):
        if v < 0.0 or v > 1.0:
            raise ValueError("Energy reserve must be between 0.0 and 1.0")
        return v

class SystemHealthSnapshot(BaseModel):
    """Aggregate health status of the entire network"""
    total_nodes: int
    active_nodes: int
    replicating_nodes: int
    mutating_nodes: int
    stalled_nodes: int
    apoptotic_nodes: int
    average_energy_reserve: float
    containment_score: float
    status: HealthStatus
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class HealthMonitor:
    """Real-time health tracking and anomaly detection"""
    def __init__(self, network: SISNetwork):
        self.network = network
        self.alert_callbacks = []
        self.metrics_collector = SISMetrics()
        self._health_history = {}

    async def monitor_network(self):
        """
        Continuous health monitoring loop
        
        >>> monitor = HealthMonitor(SISNetwork())
        >>> await monitor.monitor_network()
        """
        while True:
            snapshot = await self._generate_health_snapshot()
            if snapshot.status != HealthStatus.OPTIMAL:
                await self._trigger_alert(snapshot)
            self.metrics_collector.track_event("health_check", {"status": snapshot.status.value})
            self._update_health_history(snapshot)
            interval = getattr(getattr(settings, "observability", None), "metric_interval", None)
            sleep_seconds = interval.total_seconds() if interval else 15.0
            await asyncio.sleep(sleep_seconds)

    async def _generate_health_snapshot(self) -> SystemHealthSnapshot:
        """Create current health status report"""
        active = 0
        replicating = 0
        mutating = 0
        stalled = 0
        apoptotic = 0
        total_energy = 0.0
        containment_sum = 0.0

        for node in self.network.nodes.values():
            if node.state == CellState.ACTIVE:
                active += 1
            elif node.state == CellState.REPLICATING:
                replicating += 1
            elif node.state == CellState.MUTATING:
                mutating += 1
            elif node.state == CellState.STALLED:
                stalled += 1
            elif node.state == CellState.APOPTOTIC:
                apoptotic += 1

            total_energy += node.energy_reserve
            containment_sum += node._calculate_containment_score()

        avg_energy = total_energy / len(self.network.nodes) if self.network.nodes else 0.0
        containment = containment_sum / len(self.network.nodes) if self.network.nodes else 0.0

        status = HealthStatus.OPTIMAL
        if avg_energy < 0.4:
            status = HealthStatus.DEGRADED
        elif containment < 0.6:
            status = HealthStatus.DEGRADED
        elif stalled + apoptotic > len(self.network.nodes) * 0.2:
            status = HealthStatus.CRITICAL

        return SystemHealthSnapshot(
            total_nodes=len(self.network.nodes),
            active_nodes=active,
            replicating_nodes=replicating,
            mutating_nodes=mutating,
            stalled_nodes=stalled,
            apoptotic_nodes=apoptotic,
            average_energy_reserve=avg_energy,
            containment_score=containment,
            status=status
        )

    def _calculate_containment_score(self, node: NanobotNode) -> float:
        """Calculate containment score for a node"""
        deviation = 0.0
        base_spec = NanobotSpec(replication_rate=0.05, mutation_threshold=0.75, energy_efficiency=0.85)
        
        deviation += abs(node.spec.replication_rate - base_spec.replication_rate) / base_spec.replication_rate
        deviation += abs(node.spec.mutation_threshold - base_spec.mutation_threshold) / base_spec.mutation_threshold
        deviation += abs(node.spec.energy_efficiency - base_spec.energy_efficiency) / base_spec.energy_efficiency
        
        return max(0.0, min(1.0, 1.0 - (deviation / 3.0)))

    async def _trigger_alert(self, snapshot: SystemHealthSnapshot):
        """Generate alerts based on health status"""
        alert_level = AlertLevel.INFO
        message = ""

        if snapshot.status == HealthStatus.DEGRADED:
            alert_level = AlertLevel.WARNING
            message = f"Network health degraded: {snapshot.status.value}"
        elif snapshot.status == HealthStatus.CRITICAL:
            alert_level = AlertLevel.CRITICAL
            message = f"Network health critical: {snapshot.status.value}"

        alert = SystemAlert(
            level=alert_level,
            message=message,
            snapshot=snapshot,
            timestamp=datetime.utcnow()
        )

        for callback in self.alert_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                self.metrics_collector.track_event("alert_failure", {"error": str(e)})

    def register_alert_callback(self, callback):
        """Register external alert handler"""
        self.alert_callbacks.append(callback)

    def _update_health_history(self, snapshot: SystemHealthSnapshot):
        """Store historical health data"""
        self._health_history[snapshot.timestamp] = snapshot
        if len(self._health_history) > 100:
            oldest = min(self._health_history.keys())
            self._health_history.pop(oldest)

    async def analyze_anomalies(self) -> List[Dict]:
        """Identify and analyze abnormal patterns"""
        anomalies = []

        # Check for rapid state changes
        if len(self._health_history) >= 5:
            recent = list(self._health_history.values())[-5:]
            if any(h.status == HealthStatus.CRITICAL for h in recent):
                anomalies.append({
                    "type": "critical_flare",
                    "timestamp": datetime.utcnow(),
                    "description": "Sudden critical health degradation detected"
                })

            if recent[0].average_energy_reserve > 0.8 and recent[-1].average_energy_reserve < 0.4:
                anomalies.append({
                    "type": "energy_crash",
                    "timestamp": datetime.utcnow(),
                    "description": "Rapid energy reserve depletion"
                })

        return anomalies

class SystemAlert(BaseModel):
    """Standardized alert format for monitoring systems"""
    level: AlertLevel
    message: str
    snapshot: SystemHealthSnapshot
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_json(self) -> str:
        """Convert alert to JSON for external systems"""
        return json.dumps(self.dict(), default=str)

class DistributedHealthMonitor:
    """Multi-node health monitoring coordinator"""
    def __init__(self, network: SISNetwork):
        self.network = network
        self.local_monitors: Dict[str, HealthMonitor] = {}
        self.central_collector = HealthDataCollector()

    async def start_monitoring(self):
        """Initialize distributed monitoring across all nodes"""
        for node_id in self.network.nodes:
            self.local_monitors[node_id] = HealthMonitor(self.network)
            self.local_monitors[node_id].register_alert_callback(self._central_alert_handler)
            asyncio.create_task(self.local_monitors[node_id].monitor_network())

    async def _central_alert_handler(self, alert: SystemAlert):
        """Handle alerts from local monitors"""
        self.central_collector.record_alert(alert)
        self._trigger_global_response(alert)

    def _trigger_global_response(self, alert: SystemAlert):
        """Coordinate network-wide response to critical conditions"""
        if alert.level == AlertLevel.CRITICAL:
            self._initiate_emergency_protocol()
        elif alert.level == AlertLevel.WARNING:
            self._initiate_maintenance_protocol()

    def _initiate_emergency_protocol(self):
        """Emergency containment procedures"""
        # Trigger immediate replication rollback
        for node in self.network.nodes.values():
            if node.state in [CellState.MUTATING, CellState.REPLICATING]:
                self.network.rollback_node(node.node_id)

        # Initiate energy redistribution
        self._redistribute_energy()

    def _initiate_maintenance_protocol(self):
        """Preventative maintenance operations"""
        # Schedule controlled mutations
        for node in self.network.nodes.values():
            if node.energy_reserve > 0.7:
                self.network.evolutionary_update(node.node_id)

    def _redistribute_energy(self):
        """Balance energy reserves across the network"""
        energy_map = {node_id: node.energy_reserve for node_id, node in self.network.nodes.items()}
        avg_energy = sum(energy_map.values()) / len(energy_map)

        for node_id, node in self.network.nodes.items():
            delta = avg_energy - node.energy_reserve
            if abs(delta) > 0.1:
                node.update_energy(delta)

class HealthDataCollector:
    """Centralized health data storage and analysis"""
    def __init__(self):
        self.alert_history: List[SystemAlert] = []
        self.metrics_collector = SISMetrics()

    def record_alert(self, alert: SystemAlert):
        """Log alert for historical analysis"""
        self.alert_history.append(alert)
        if len(self.alert_history) > 1000:
            self.alert_history.pop(0)
        self.metrics_collector.track_event("alert_recorded", {"level": alert.level.value})

    def analyze_trends(self) -> Dict[str, Any]:
        """Identify long-term health trends"""
        if not self.alert_history:
            return {"trend": "stable", "confidence": 1.0}

        critical_count = sum(1 for a in self.alert_history if a.level == AlertLevel.CRITICAL)
        warning_count = sum(1 for a in self.alert_history if a.level == AlertLevel.WARNING)

        trend = "stable"
        confidence = 1.0

        if critical_count > 5 and warning_count > 10:
            trend = "degrading"
            confidence = 0.9
        elif critical_count > 2:
            trend = "unstable"
            confidence = 0.7

        return {
            "trend": trend,
            "confidence": confidence,
            "critical_alerts": critical_count,
            "warning_alerts": warning_count
        }
