# src/biocognitive_core/components/sis/network.py
"""
Synthetic Immune Symbiont Network Architecture

Manages distributed nanobiotic cellular networks with:
- Self-regulating replication and mutation
- Multi-scale homeostatic control
- Distributed evolutionary adaptation
- Immune response coordination
Author: Morpheus
Date: 2025-05-08
Version: 1.0.0
Description: This module implements the SIS (Synthetic Immune Symbiont) network architecture. It includes various components for managing nanobot nodes, evolutionary adaptation, and immune response coordination. The system is designed to operate in a distributed environment with real-time monitoring and adaptive control.
ID: SIS-006
SHA-256: 26631c4e5d6a7b8c9e0f1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3
"""

from typing import Dict, Set, Optional, List, Tuple, Union, AsyncGenerator, Any
from pydantic import BaseModel, Field, validator, root_validator
from enum import Enum
import asyncio
from dataclasses import dataclass
from biocognitive_core.config import settings
from biocognitive_core.exceptions import BiocognitiveError, EvolutionConstraintViolation
from biocognitive_core.metrics import SISMetrics
import secrets
import numpy as np
from datetime import datetime, timedelta
import json
import hashlib

class CellState(Enum):
    """Cellular operational states"""
    ACTIVE = "active"
    REPLICATING = "replicating"
    MUTATING = "mutating"
    APOPTOTIC = "apoptotic"
    STALLED = "stalled"

class NanobotSpec(BaseModel):
    """Nanobot operational parameters"""
    replication_rate: float = Field(ge=0.01, le=0.2)
    mutation_threshold: float = Field(ge=0.5, le=0.95)
    energy_efficiency: float = Field(ge=0.7, le=0.95)
    communication_range: float = Field(ge=1.0, le=10.0)
    version: int = Field(default=1)

    @validator("replication_rate")
    def validate_replication_rate(cls, v):
        if v < 0.01 or v > 0.2:
            raise ValueError("Replication rate must be between 0.01 and 0.2")
        return v

    @validator("mutation_threshold")
    def validate_mutation_threshold(cls, v):
        if v < 0.5 or v > 0.95:
            raise ValueError("Mutation threshold must be between 0.5 and 0.95")
        return v

class NanobotNode:
    """Individual nanobot unit in the network"""
    def __init__(self, node_id: str, spec: NanobotSpec):
        self.node_id = node_id
        self.spec = spec
        self.state: CellState = CellState.ACTIVE
        self.connected_nodes: Set[str] = set()
        self.energy_reserve = 1.0
        self.version = spec.version
        self.last_activity = datetime.utcnow()
        self.mutation_history: List[Tuple[datetime, str]] = []
        self._health_monitor = HealthMonitor()
        self._base_spec = NanobotSpec(
            replication_rate=0.05,
            mutation_threshold=0.75,
            energy_efficiency=0.85,
            communication_range=5.0,
            version=1
        )

    async def monitor_cell(self, cell_data: Dict) -> CellState:
        """
        Monitor cellular health with adaptive thresholds
        
        >>> node = NanobotNode("node123", NanobotSpec())
        >>> await node.monitor_cell({"dna_damage": 0.8})
        <CellState.MUTATING: 'mutating'>
        """
        dna_damage = cell_data.get("dna_damage", 0)
        if dna_damage > self.spec.mutation_threshold:
            return CellState.MUTATING
        if self.energy_reserve < 0.2:
            return CellState.STALLED
        return CellState.ACTIVE

    def add_connection(self, neighbor_id: str):
        """Establish communication link with another node"""
        self.connected_nodes.add(neighbor_id)
        SISMetrics.track_boundary_crossing(self.node_id, 1)

    def update_energy(self, delta: float):
        """Adjust energy reserves with bounds"""
        self.energy_reserve = max(0.0, min(1.0, self.energy_reserve + delta))
        self.last_activity = datetime.utcnow()

    def _calculate_energy_usage(self, operation: str) -> float:
        """Calculate energy cost of an operation"""
        base_cost = {
            "replication": 0.15,
            "mutation": 0.25,
            "communication": 0.05
        }.get(operation, 0.01)
        return base_cost * self.spec.energy_efficiency
        
    def _calculate_containment_score(self) -> float:
        """
        Calculate how contained/controlled the nanobot is
        
        Returns:
            float: Containment score between 0.0 (uncontained) and 1.0 (fully contained)
        """
        # Calculate deviation from base specification
        deviation = 0.0
        
        # Weight deviations from baseline for critical parameters
        deviation += abs(self.spec.replication_rate - self._base_spec.replication_rate) / self._base_spec.replication_rate * 2.0
        deviation += abs(self.spec.mutation_threshold - self._base_spec.mutation_threshold) / self._base_spec.mutation_threshold
        deviation += abs(self.spec.energy_efficiency - self._base_spec.energy_efficiency) / self._base_spec.energy_efficiency
        
        # Factor in mutation history - more mutations reduce containment
        history_penalty = min(0.3, len(self.mutation_history) * 0.03)
        
        # Factor in energy reserve - lower energy means higher containment risk
        energy_penalty = max(0.0, 0.2 - self.energy_reserve) * 0.5
        
        # Calculate time since last activity - inactive nodes may be evading control
        inactivity_penalty = 0.0
        time_since_activity = (datetime.utcnow() - self.last_activity).total_seconds()
        if time_since_activity > 3600:  # 1 hour
            inactivity_penalty = min(0.2, time_since_activity / 86400)  # Max 0.2 penalty (1 day)
            
        # Calculate final score with penalties
        raw_score = max(0.0, 1.0 - (deviation / 4.0) - history_penalty - energy_penalty - inactivity_penalty)
        
        # Normalize to 0.0-1.0 range
        return max(0.0, min(1.0, raw_score))

class HealthMonitor:
    """Real-time health tracking and anomaly detection"""
    def __init__(self):
        self._state_history = []

    def record_state(self, state: CellState):
        """Log state transitions for analysis"""
        self._state_history.append({
            "timestamp": datetime.utcnow(),
            "state": state.value,
            "duration": (datetime.utcnow() - self._state_history[-1]["timestamp"]).total_seconds() if self._state_history else 0
        })

    def detect_anomalies(self) -> List[str]:
        """Identify abnormal state patterns"""
        anomalies = []
        if len(self._state_history) >= 3:
            # Check for rapid state changes
            state_transitions = [h["state"] for h in self._state_history[-3:]]
            if len(set(state_transitions)) >= 3:
                anomalies.append("Rapid state transitions")
        return anomalies

class SISNetwork:
    """Distributed nanobiotic network manager"""
    def __init__(self):
        self.nodes: Dict[str, NanobotNode] = {}
        self.evolution_lock = asyncio.Lock()
        self.health_snapshot = {}
        self.metrics_collector = SISMetrics()
        self.max_replication_rate = settings.immune.replication_rate_limit
        self.mutation_window = settings.immune.evolution_window
        self._evolution_cache = {}

    async def add_node(self, node_id: str, spec: NanobotSpec):
        """
        Add new nanobot node with version validation
        
        >>> network = SISNetwork()
        >>> await network.add_node("node123", NanobotSpec())
        """
        if not self._validate_spec(spec):
            raise EvolutionConstraintViolation(
                "Nanobot spec violates safety thresholds",
                code="SIS-001",
                mutation_rate=spec.mutation_threshold,
                allowed_threshold=settings.immune.mutation_threshold
            )
        self.nodes[node_id] = NanobotNode(node_id, spec)
        await self._establish_connections(node_id)

    async def _establish_connections(self, node_id: str):
        """Create initial network connections"""
        neighbors = self._find_neighbors(node_id)
        for neighbor in neighbors:
            self.nodes[node_id].add_connection(neighbor)
            self.nodes[neighbor].add_connection(node_id)

    def _find_neighbors(self, node_id: str) -> List[str]:
        """Identify nearby nodes within communication range"""
        # In production, this would use spatial positioning data
        return [n for n in self.nodes if n != node_id][:3]

    def _validate_spec(self, spec: NanobotSpec) -> bool:
        """Validate nanobot spec against system constraints"""
        return (
            spec.replication_rate <= self.max_replication_rate and
            spec.mutation_threshold >= settings.immune.mutation_threshold and
            spec.mutation_threshold <= settings.immune.mutation_threshold + 0.2
        )

    async def evolutionary_update(self, node_id: str):
        """
        Controlled evolutionary adaptation with rollback capability
        
        >>> network = SISNetwork()
        >>> await network.evolutionary_update("node123")
        """
        async with self.evolution_lock:
            current_node = self.nodes[node_id]
            new_spec = await self._generate_adaptation(current_node.spec)
            
            if await self._validate_evolution(current_node, new_spec):
                current_node.spec = new_spec
                current_node.version += 1
                current_node.mutation_history.append(
                    (datetime.utcnow(), "evolution_complete")
                )
                self.metrics_collector.track_mutation(node_id, new_spec.mutation_threshold)
            else:
                await self._rollback_node(current_node)

    async def _generate_adaptation(self, spec: NanobotSpec) -> NanobotSpec:
        """Create next-generation nanobot specification"""
        mutation_rate = min(1.0, spec.mutation_threshold + np.random.normal(0.05, 0.02))
        return NanobotSpec(
            replication_rate=min(0.2, spec.replication_rate * 1.1),
            mutation_threshold=mutation_rate,
            energy_efficiency=spec.energy_efficiency * 1.05,
            communication_range=spec.communication_range * 1.02,
            version=spec.version + 1
        )

    async def _validate_evolution(self, node: NanobotNode, new_spec: NanobotSpec) -> bool:
        """Check if evolutionary adaptation is safe"""
        # Validate against system constraints
        if new_spec.mutation_threshold > settings.immune.mutation_threshold + 0.2:
            return False
        if new_spec.replication_rate > self.max_replication_rate * 1.2:
            return False
        if new_spec.energy_efficiency < node.spec.energy_efficiency * 0.9:
            return False
            
        # Simulate stress test
        stress_test = self._simulate_evolution(node, new_spec)
        return stress_test["success"]

    def _simulate_evolution(self, node: NanobotNode, new_spec: NanobotSpec) -> Dict[str, Any]:
        """Simulate evolutionary adaptation in controlled environment"""
        # In production, this would use virtual environment testing
        return {
            "success": np.random.rand() > 0.1,  # 10% failure rate for demonstration
            "energy_usage": 0.85,
            "stability": 0.92
        }

    async def _rollback_node(self, node: NanobotNode):
        """Revert to previous stable configuration"""
        if len(node.mutation_history) > 0:
            last_version = node.mutation_history[-1][0]
            node.spec = self._get_stable_spec(last_version)
            node.version -= 1
            node.mutation_history.append((datetime.utcnow(), "rollback_complete"))
            self.metrics_collector.track_event(
                "evolution_rollback",
                {"node_id": node.node_id, "version": node.version}
            )
        else:
            raise EvolutionConstraintViolation(
                "No previous stable configuration available",
                code="SIS-004",
                mutation_rate=node.spec.mutation_threshold,
                allowed_threshold=settings.immune.mutation_threshold
            )

    def _get_stable_spec(self, timestamp: datetime) -> NanobotSpec:
        """Retrieve stable specification from history"""
        # In production, this would query a persistent storage
        return NanobotSpec(
            replication_rate=0.05,
            mutation_threshold=0.75,
            energy_efficiency=0.85,
            communication_range=5.0,
            version=1
        )

    async def initiate_response(self, immune_action: "ImmuneAction"):
        """
        Execute coordinated immune response across the network
        
        >>> network = SISNetwork()
        >>> await network.initiate_response(ImmuneAction("replication", "node123"))
        """
        tasks = []
        for node_id, node in self.nodes.items():
            if node_id == immune_action.target:
                tasks.append(self._execute_local_action(node, immune_action))
            else:
                tasks.append(self._propagate_signal(node, immune_action))
        await asyncio.gather(*tasks)
        self.metrics_collector.track_event("immune_response_complete", {"action": immune_action.type})

    async def _execute_local_action(self, node: NanobotNode, action: "ImmuneAction"):
        """Perform direct action on target node"""
        if action.type == "replication":
            energy_cost = node._calculate_energy_usage("replication")
            if node.energy_reserve >= energy_cost:
                node.update_energy(-energy_cost)
                node.state = CellState.REPLICATING
                await asyncio.sleep(action.duration.total_seconds())
                node.state = CellState.ACTIVE
            else:
                raise EvolutionConstraintViolation(
                    "Insufficient energy for replication",
                    code="SIS-005",
                    mutation_rate=node.spec.mutation_threshold,
                    allowed_threshold=settings.immune.mutation_threshold
                )

    async def _propagate_signal(self, node: NanobotNode, action: "ImmuneAction"):
        """Broadcast action signal to connected nodes"""
        for neighbor in node.connected_nodes:
            if self.nodes[neighbor].state == CellState.ACTIVE:
                self.nodes[neighbor].add_connection(node.node_id)
                self.metrics_collector.track_event("signal_propagation", {"source": node.node_id, "target": neighbor})

class ImmuneAction:
    """Structured immune system action request"""
    def __init__(self, action_type: str, target: str, duration: timedelta = timedelta(seconds=10)):
        self.type = action_type
        self.target = target
        self.duration = duration
        self.created_at = datetime.utcnow()
        self.id = hashlib.sha256(f"{action_type}:{target}:{self.created_at.isoformat()}".encode()).hexdigest()[:16]
        self.completed = False
        self.parameters = {}
        
    def add_parameter(self, key: str, value: Any):
        """Add additional action parameters"""
        self.parameters[key] = value
        return self
        
    def mark_completed(self):
        """Mark action as completed"""
        self.completed = True
        self.completed_at = datetime.utcnow()
        
    def execution_time(self) -> float:
        """Return execution time in seconds if completed"""
        if self.completed and hasattr(self, 'completed_at'):
            return (self.completed_at - self.created_at).total_seconds()
        return 0.0

    def __repr__(self):
        return f"ImmuneAction(type={self.type!r}, target={self.target!r}, duration={self.duration!r}, id={self.id})"

from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Union, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime
import uuid
import numpy as np
import asyncio
import logging

from biocognitive_core.config import settings
from biocognitive_core.exceptions import BiocognitiveError, EvolutionConstraintViolation

logger = logging.getLogger(__name__)

class CellState(Enum):
    """Possible states for nanobiotic cells"""
    DORMANT = "dormant"
    ACTIVE = "active"
    REPLICATING = "replicating"
    DEFENDING = "defending"
    REPAIRING = "repairing"
    SIGNALING = "signaling"
    RECYCLING = "recycling"
    COMPROMISED = "compromised"

class ImmuneAction(Enum):
    """Possible immune actions performed by nanobots"""
    IDENTIFY = "identify"       # Identify foreign or compromised elements
    CONTAIN = "contain"         # Contain the spread of threats
    NEUTRALIZE = "neutralize"   # Neutralize threats directly
    REPAIR = "repair"           # Repair damaged systems
    SIGNAL = "signal"           # Signal for additional response
    ADAPT = "adapt"             # Adapt to new threat patterns
    REMEMBER = "remember"       # Store threat signatures for future response
    TOLERATE = "tolerate"       # Deliberately tolerate specific patterns

class NanobotSpec(BaseModel):
    """Specification for nanobot nodes"""
    memory_capacity: int = Field(default=1024)
    processing_capacity: float = Field(default=1.0)
    communication_range: float = Field(default=10.0)
    energy_efficiency: float = Field(default=0.8, ge=0.0, le=1.0)
    replication_rate: float = Field(default=0.05, ge=0.0, le=1.0)
    sensory_precision: float = Field(default=0.9, ge=0.0, le=1.0)
    defense_capability: float = Field(default=0.7, ge=0.0, le=1.0)
    repair_capability: float = Field(default=0.6, ge=0.0, le=1.0)
    identification_precision: float = Field(default=0.85, ge=0.0, le=1.0)
    
    @validator('energy_efficiency', 'sensory_precision', 'defense_capability', 
              'repair_capability', 'identification_precision')
    def check_normalized(cls, v, values, **kwargs):
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"Value must be between 0.0 and 1.0")
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "memory_capacity": self.memory_capacity,
            "processing_capacity": self.processing_capacity,
            "communication_range": self.communication_range,
            "energy_efficiency": self.energy_efficiency,
            "replication_rate": self.replication_rate,
            "sensory_precision": self.sensory_precision,
            "defense_capability": self.defense_capability,
            "repair_capability": self.repair_capability,
            "identification_precision": self.identification_precision
        }

class NanobotNode:
    """Individual nanobot node in SIS network"""
    
    def __init__(self, node_id: str, spec: NanobotSpec):
        self.node_id = node_id
        self.spec = spec
        self.state = CellState.DORMANT
        self.creation_timestamp = datetime.utcnow()
        self.last_active_timestamp = self.creation_timestamp
        self.connected_nodes: Set[str] = set()
        self.threat_memory: Dict[str, float] = {}  # Threat signature -> confidence
        self.action_history: List[Dict[str, Any]] = []
        self.health_metrics = {
            "energy_level": 1.0,
            "integrity": 1.0,
            "contamination": 0.0,
            "error_rate": 0.0,
            "responsiveness": 1.0
        }
        self._action_lock = asyncio.Lock()
    
    async def activate(self) -> bool:
        """Activate the nanobot node"""
        if self.state == CellState.COMPROMISED:
            return False
            
        self.state = CellState.ACTIVE
        self.last_active_timestamp = datetime.utcnow()
        self._record_action("activate", {})
        return True
    
    async def connect_to(self, node_id: str) -> bool:
        """Connect to another node"""
        if node_id != self.node_id:  # Prevent self-connection
            self.connected_nodes.add(node_id)
            self._record_action("connect", {"target_node": node_id})
            return True
        return False
    
    async def disconnect_from(self, node_id: str) -> bool:
        """Disconnect from another node"""
        if node_id in self.connected_nodes:
            self.connected_nodes.remove(node_id)
            self._record_action("disconnect", {"target_node": node_id})
            return True
        return False
    
    async def perform_immune_action(self, 
                                action: ImmuneAction, 
                                target: Optional[str] = None,
                                threat_signature: Optional[str] = None,
                                params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Perform a specific immune action
        
        Args:
            action: The immune action to perform
            target: Optional target identifier (node, region, etc.)
            threat_signature: Optional threat signature being addressed
            params: Additional parameters for the action
            
        Returns:
            Dict containing action results
        """
        # Use a lock to ensure action atomicity
        async with self._action_lock:
            # Update activity timestamp
            self.last_active_timestamp = datetime.utcnow()
            
            # Create parameters dictionary
            action_params = params or {}
            if target:
                action_params["target"] = target
            if threat_signature:
                action_params["threat_signature"] = threat_signature
                
            # Calculate baseline success probability
            success_prob = self._calculate_action_probability(action, threat_signature)
            
            # Apply energy cost
            energy_cost = self._calculate_energy_cost(action)
            self.health_metrics["energy_level"] = max(0.0, self.health_metrics["energy_level"] - energy_cost)
            
            # Update state based on action
            self._update_state_for_action(action)
            
            # Determine success (with randomness)
            rand_factor = np.random.random() * 0.3  # Random factor of up to 30%
            success = np.random.random() < (success_prob - rand_factor)
            
            # Calculate containment score if applicable
            containment_score = None
            if action == ImmuneAction.CONTAIN and threat_signature:
                containment_score = self._calculate_containment_score(threat_signature)
            
            # Record threat signature in memory if applicable
            if threat_signature and action in [
                ImmuneAction.IDENTIFY, ImmuneAction.NEUTRALIZE, 
                ImmuneAction.REMEMBER, ImmuneAction.ADAPT
            ]:
                # Update threat memory with confidence boost if successful
                current_confidence = self.threat_memory.get(threat_signature, 0.3)
                confidence_boost = 0.2 if success else 0.05
                self.threat_memory[threat_signature] = min(1.0, current_confidence + confidence_boost)
            
            # Prepare result
            result = {
                "action": action.value,
                "success": success,
                "energy_remaining": self.health_metrics["energy_level"],
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if containment_score is not None:
                result["containment_score"] = containment_score
                
            if threat_signature and threat_signature in self.threat_memory:
                result["threat_confidence"] = self.threat_memory[threat_signature]
            
            # Record the action
            self._record_action(action.value, action_params, success=success)
            
            return result
    
    def _calculate_action_probability(self, action: ImmuneAction, threat_signature: Optional[str]) -> float:
        """Calculate probability of success for an action"""
        # Base probabilities determined by nanobot capabilities
        base_probs = {
            ImmuneAction.IDENTIFY: self.spec.identification_precision,
            ImmuneAction.CONTAIN: self.spec.defense_capability * 0.9,
            ImmuneAction.NEUTRALIZE: self.spec.defense_capability,
            ImmuneAction.REPAIR: self.spec.repair_capability,
            ImmuneAction.SIGNAL: 0.95,  # Signaling is usually reliable
            ImmuneAction.ADAPT: self.spec.identification_precision * 0.8,
            ImmuneAction.REMEMBER: min(1.0, self.spec.memory_capacity / 1000),
            ImmuneAction.TOLERATE: 0.9  # Tolerance is a passive action, usually successful
        }
        
        # Get base probability
        prob = base_probs.get(action, 0.5)
        
        # Adjust for threat recognition if applicable
        if threat_signature and threat_signature in self.threat_memory:
            threat_confidence = self.threat_memory[threat_signature]
            
            # Higher confidence improves most action types
            if action in [ImmuneAction.CONTAIN, ImmuneAction.NEUTRALIZE, ImmuneAction.ADAPT]:
                prob = min(1.0, prob + threat_confidence * 0.2)
                
            # Especially helpful for identification
            elif action == ImmuneAction.IDENTIFY:
                prob = min(1.0, prob + threat_confidence * 0.3)
        
        # Adjust for health metrics
        # Low energy reduces effectiveness
        if self.health_metrics["energy_level"] < 0.5:
            energy_factor = 0.5 + (self.health_metrics["energy_level"] / 2.0)
            prob *= energy_factor
            
        # Low integrity reduces effectiveness
        if self.health_metrics["integrity"] < 0.7:
            integrity_factor = 0.7 + (self.health_metrics["integrity"] / 3.0)
            prob *= integrity_factor
        
        # High contamination reduces effectiveness
        if self.health_metrics["contamination"] > 0.3:
            contamination_penalty = 1.0 - (self.health_metrics["contamination"] * 0.5)
            prob *= contamination_penalty
        
        return min(0.99, max(0.01, prob))  # Clamp between 1% and 99%
    
    def _calculate_energy_cost(self, action: ImmuneAction) -> float:
        """Calculate energy cost of an action"""
        # Base energy costs
        base_costs = {
            ImmuneAction.IDENTIFY: 0.01,
            ImmuneAction.CONTAIN: 0.05,
            ImmuneAction.NEUTRALIZE: 0.10,
            ImmuneAction.REPAIR: 0.08,
            ImmuneAction.SIGNAL: 0.02,
            ImmuneAction.ADAPT: 0.07,
            ImmuneAction.REMEMBER: 0.01,
            ImmuneAction.TOLERATE: 0.005
        }
        
        # Get base cost
        cost = base_costs.get(action, 0.03)
        
        # Apply energy efficiency
        cost /= max(0.1, self.spec.energy_efficiency)
        
        # Being in compromised state increases energy costs
        if self.state == CellState.COMPROMISED:
            cost *= 2.0
            
        return cost
    
    def _update_state_for_action(self, action: ImmuneAction) -> None:
        """Update nanobot state based on action"""
        # Map actions to appropriate states
        state_map = {
            ImmuneAction.IDENTIFY: CellState.ACTIVE,
            ImmuneAction.CONTAIN: CellState.DEFENDING,
            ImmuneAction.NEUTRALIZE: CellState.DEFENDING,
            ImmuneAction.REPAIR: CellState.REPAIRING,
            ImmuneAction.SIGNAL: CellState.SIGNALING,
            ImmuneAction.ADAPT: CellState.ACTIVE,
            ImmuneAction.REMEMBER: CellState.ACTIVE,
            ImmuneAction.TOLERATE: CellState.ACTIVE
        }
        
        # Update state
        self.state = state_map.get(action, CellState.ACTIVE)
    
    def _calculate_containment_score(self, threat_signature: str) -> float:
        """Calculate threat containment effectiveness score"""
        # Base containment score from defense capability
        base_score = self.spec.defense_capability
        
        # Adjust based on prior knowledge of threat
        if threat_signature in self.threat_memory:
            threat_confidence = self.threat_memory[threat_signature]
            base_score = min(1.0, base_score + threat_confidence * 0.3)
        
        # Adjust based on node health
        health_factor = (
            self.health_metrics["energy_level"] * 0.4 +
            self.health_metrics["integrity"] * 0.4 +
            (1.0 - self.health_metrics["contamination"]) * 0.2
        )
        
        # Calculate final score
        containment_score = base_score * health_factor
        
        # Add some randomness (±10%)
        random_factor = 0.9 + (np.random.random() * 0.2)
        containment_score *= random_factor
        
        return min(1.0, max(0.0, containment_score))
    
    def _record_action(self, action_type: str, params: Dict[str, Any], success: bool = True) -> None:
        """Record an action in the node's history"""
        self.action_history.append({
            "action_type": action_type,
            "params": params,
            "timestamp": datetime.utcnow().isoformat(),
            "energy_level": self.health_metrics["energy_level"],
            "state": self.state.value,
            "success": success
        })
        
        # Trim history if too large
        if len(self.action_history) > 1000:
            self.action_history = self.action_history[-1000:]
    
    def update_health_metrics(self, metrics_update: Dict[str, float]) -> None:
        """Update health metrics with new values"""
        for key, value in metrics_update.items():
            if key in self.health_metrics:
                # Ensure values are in valid range
                self.health_metrics[key] = min(1.0, max(0.0, value))
        
        # Check if node has become compromised
        if self.health_metrics["integrity"] < 0.2 or self.health_metrics["contamination"] > 0.8:
            self.state = CellState.COMPROMISED
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary representation"""
        return {
            "node_id": self.node_id,
            "spec": self.spec.to_dict(),
            "state": self.state.value,
            "creation_timestamp": self.creation_timestamp.isoformat(),
            "last_active_timestamp": self.last_active_timestamp.isoformat(),
            "connected_nodes": list(self.connected_nodes),
            "threat_memory_size": len(self.threat_memory),
            "action_history_size": len(self.action_history),
            "health_metrics": self.health_metrics
        }

class SISNetwork:
    """Synthetic Immune Symbiont Network"""
    
    def __init__(self):
        self.nodes: Dict[str, NanobotNode] = {}
        self.creation_timestamp = datetime.utcnow()
        self.global_threat_registry: Dict[str, Dict[str, Any]] = {}
        self.network_metrics = {
            "total_energy": 0.0,
            "average_responsiveness": 0.0,
            "threat_neutralization_rate": 0.0,
            "adaptation_rate": 0.0
        }
        self._network_lock = asyncio.Lock()
        
        logger.info("SIS Network initialized")
    
    async def add_node(self, node_id: str, spec: Optional[NanobotSpec] = None) -> NanobotNode:
        """Add a new node to the network"""
        async with self._network_lock:
            # Use provided spec or create default
            node_spec = spec or NanobotSpec()
            
            # Create new node
            node = NanobotNode(node_id, node_spec)
            self.nodes[node_id] = node
            
            # Update network metrics
            await self._update_network_metrics()
            
            logger.info(f"Added node {node_id} to SIS network")
            return node
    
    async def remove_node(self, node_id: str) -> bool:
        """Remove a node from the network"""
        async with self._network_lock:
            if node_id in self.nodes:
                # Remove connections to this node
                for other_node in self.nodes.values():
                    if node_id in other_node.connected_nodes:
                        await other_node.disconnect_from(node_id)
                
                # Remove the node
                del self.nodes[node_id]
                
                # Update network metrics
                await self._update_network_metrics()
                
                logger.info(f"Removed node {node_id} from SIS network")
                return True
            return False
    
    async def connect_nodes(self, source_id: str, target_id: str) -> bool:
        """Connect two nodes in the network"""
        if source_id not in self.nodes or target_id not in self.nodes:
            return False
            
        if source_id == target_id:  # Prevent self-connection
            return False
            
        source_node = self.nodes[source_id]
        target_node = self.nodes[target_id]
        
        # Create bidirectional connection
        source_success = await source_node.connect_to(target_id)
        target_success = await target_node.connect_to(source_id)
        
        return source_success and target_success
    
    async def register_threat(self, 
                       threat_signature: str, 
                       threat_level: float, 
                       detected_by: str) -> Dict[str, Any]:
        """Register a new threat in the global registry"""
        async with self._network_lock:
            # Create or update threat entry
            if threat_signature in self.global_threat_registry:
                # Update existing threat
                self.global_threat_registry[threat_signature]["detection_count"] += 1
                self.global_threat_registry[threat_signature]["last_detected_by"] = detected_by
                self.global_threat_registry[threat_signature]["last_detected_at"] = datetime.utcnow().isoformat()
                
                # Update threat level (use maximum)
                current_level = self.global_threat_registry[threat_signature]["threat_level"]
                self.global_threat_registry[threat_signature]["threat_level"] = max(current_level, threat_level)
            else:
                # Create new threat entry
                self.global_threat_registry[threat_signature] = {
                    "threat_signature": threat_signature,
                    "threat_level": threat_level,
                    "first_detected_by": detected_by,
                    "last_detected_by": detected_by,
                    "first_detected_at": datetime.utcnow().isoformat(),
                    "last_detected_at": datetime.utcnow().isoformat(),
                    "detection_count": 1,
                    "containment_status": 0.0,
                    "neutralization_status": 0.0
                }
            
            # Log the threat
            logger.warning(
                f"Threat {threat_signature} registered with level {threat_level:.2f} "
                f"detected by {detected_by}"
            )
            
            return self.global_threat_registry[threat_signature]
    
    async def update_threat_status(self, 
                           threat_signature: str, 
                           containment_status: Optional[float] = None,
                           neutralization_status: Optional[float] = None) -> bool:
        """Update containment or neutralization status for a threat"""
        if threat_signature not in self.global_threat_registry:
            return False
            
        # Update statuses if provided
        if containment_status is not None:
            self.global_threat_registry[threat_signature]["containment_status"] = max(
                self.global_threat_registry[threat_signature]["containment_status"],
                containment_status
            )
            
        if neutralization_status is not None:
            self.global_threat_registry[threat_signature]["neutralization_status"] = max(
                self.global_threat_registry[threat_signature]["neutralization_status"],
                neutralization_status
            )
            
        return True
    
    async def perform_network_immune_response(self, 
                                      threat_signature: str, 
                                      action: ImmuneAction,
                                      node_subset: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Perform coordinated immune response across multiple nodes
        
        Args:
            threat_signature: The threat to respond to
            action: The immune action to perform
            node_subset: Optional list of node IDs to include (default: all active nodes)
        
        Returns:
            Dictionary with response results
        """
        # Check if threat is registered
        if threat_signature not in self.global_threat_registry:
            return {"error": "Threat not registered", "success": False}
        
        # Get threat details
        threat_details = self.global_threat_registry[threat_signature]
        
        # Determine which nodes to involve
        if node_subset:
            # Filter to include only existing nodes
            target_nodes = [
                node_id for node_id in node_subset 
                if node_id in self.nodes
            ]
        else:
            # Default: use all non-compromised nodes
            target_nodes = [
                node_id for node_id, node in self.nodes.items()
                if node.state != CellState.COMPROMISED
            ]
        
        if not target_nodes:
            return {"error": "No valid nodes available for response", "success": False}
        
        # Track response metrics
        success_count = 0
        total_containment = 0.0
        total_energy_used = 0.0
        participated_nodes = 0
        
        # Perform action on all selected nodes
        response_details = []
        for node_id in target_nodes:
            node = self.nodes[node_id]
            try:
                # Skip nodes with very low energy
                if node.health_metrics["energy_level"] < 0.1:
                    continue
                    
                # Perform the immune action
                result = await node.perform_immune_action(
                    action=action,
                    threat_signature=threat_signature,
                    params={"coordinated_response": True}
                )
                
                # Track metrics
                participated_nodes += 1
                if result.get("success", False):
                    success_count += 1
                
                if "containment_score" in result:
                    total_containment += result["containment_score"]
                    
                # Track energy used
                initial_energy = result.get("energy_remaining", 0) + self._calculate_energy_cost(action)
                energy_used = initial_energy - result.get("energy_remaining", 0)
                total_energy_used += energy_used
                
                # Add to response details
                response_details.append({
                    "node_id": node_id,
                    "success": result.get("success", False),
                    "energy_remaining": result.get("energy_remaining", 0)
                })
                
            except Exception as e:
                logger.error(f"Error during immune response on node {node_id}: {str(e)}")
                response_details.append({
                    "node_id": node_id,
                    "error": str(e),
                    "success": False
                })
        
        # Calculate overall success metrics
        if participated_nodes > 0:
            success_rate = success_count / participated_nodes
            avg_containment = total_containment / participated_nodes if action == ImmuneAction.CONTAIN else None
            
            # Update threat registry with new containment level if applicable
            if action == ImmuneAction.CONTAIN and avg_containment is not None:
                await self.update_threat_status(threat_signature, containment_status=avg_containment)
                
            # Update threat registry with neutralization level if applicable
            if action == ImmuneAction.NEUTRALIZE:
                neutralization_level = success_rate * 0.8  # Simplified calculation
                await self.update_threat_status(threat_signature, neutralization_status=neutralization_level)
        else:
            success_rate = 0.0
            avg_containment = None
        
        # Compile overall response result
        response_result = {
            "threat_signature": threat_signature,
            "action": action.value,
            "nodes_participated": participated_nodes,
            "success_rate": success_rate,
            "energy_used": total_energy_used,
            "timestamp": datetime.utcnow().isoformat(),
            "node_details": response_details
        }
        
        if avg_containment is not None:
            response_result["average_containment"] = avg_containment
        
        # Update network metrics
        await self._update_network_metrics()
        
        return response_result
    
    def _calculate_energy_cost(self, action: ImmuneAction) -> float:
        """Helper to calculate energy cost for a given action"""
        # Base energy costs
        base_costs = {
            ImmuneAction.IDENTIFY: 0.01,
            ImmuneAction.CONTAIN: 0.05,
            ImmuneAction.NEUTRALIZE: 0.10,
            ImmuneAction.REPAIR: 0.08,
            ImmuneAction.SIGNAL: 0.02,
            ImmuneAction.ADAPT: 0.07,
            ImmuneAction.REMEMBER: 0.01,
            ImmuneAction.TOLERATE: 0.005
        }
        
        return base_costs.get(action, 0.03)
    
    async def _update_network_metrics(self) -> None:
        """Update global network metrics"""
        if not self.nodes:
            return
            
        # Calculate total energy
        total_energy = sum(node.health_metrics["energy_level"] for node in self.nodes.values())
        
        # Calculate average responsiveness
        avg_responsiveness = sum(
            node.health_metrics["responsiveness"] for node in self.nodes.values()
        ) / len(self.nodes)
        
        # Calculate threat metrics
        total_threats = len(self.global_threat_registry)
        if total_threats > 0:
            # Calculate neutralization rate
            neutralized = sum(
                1 for threat in self.global_threat_registry.values()
                if threat.get("neutralization_status", 0) > 0.8
            )
            neutralization_rate = neutralized / total_threats
            
            # Calculate adaptation rate (from threat memory across nodes)
            total_memory_entries = sum(len(node.threat_memory) for node in self.nodes.values())
            max_possible = total_threats * len(self.nodes)
            adaptation_rate = total_memory_entries / max_possible if max_possible > 0 else 0
        else:
            neutralization_rate = 0
            adaptation_rate = 0
        
        # Update metrics
        self.network_metrics = {
            "total_energy": total_energy,
            "average_responsiveness": avg_responsiveness,
            "threat_neutralization_rate": neutralization_rate,
            "adaptation_rate": adaptation_rate,
            "total_nodes": len(self.nodes),
            "active_threats": total_threats
        }
    
    def get_network_stats(self) -> Dict[str, Any]:
        """Get current network statistics"""
        # Count nodes by state
        state_counts = {}
        for node in self.nodes.values():
            state = node.state.value
            state_counts[state] = state_counts.get(state, 0) + 1
        
        # Combine with network metrics
        stats = {
            "total_nodes": len(self.nodes),
            "node_states": state_counts,
            "registered_threats": len(self.global_threat_registry),
            "network_age_hours": (datetime.utcnow() - self.creation_timestamp).total_seconds() / 3600,
        }
        
        # Add network metrics
        stats.update(self.network_metrics)
        
        return stats

class HealthMonitor:
    """Monitors health of SIS network nodes"""
    
    def __init__(self, network: SISNetwork):
        self.network = network
        self.check_interval = 60  # seconds
        self.active = False
        self.monitoring_task = None
    
    async def start_monitoring(self) -> None:
        """Start continuous health monitoring"""
        if self.active:
            return
            
        self.active = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        logger.info("SIS Health monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop health monitoring"""
        if not self.active:
            return
            
        self.active = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            
        logger.info("SIS Health monitoring stopped")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        while self.active:
            try:
                await self._check_all_nodes()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring: {str(e)}")
                await asyncio.sleep(self.check_interval * 2)  # Back off on error
    
    async def _check_all_nodes(self) -> None:
        """Check health of all nodes"""
        for node_id, node in self.network.nodes.items():
            try:
                # Skip recently active nodes
                time_since_activity = (datetime.utcnow() - node.last_active_timestamp).total_seconds()
                if time_since_activity < self.check_interval * 2:
                    continue
                
                # Perform automatic repair for compromised nodes
                if node.state == CellState.COMPROMISED and node.health_metrics["energy_level"] > 0.3:
                    # Attempt self-repair
                    result = await node.perform_immune_action(
                        action=ImmuneAction.REPAIR,
                        params={"auto_repair": True}
                    )
                    
                    if result.get("success", False):
                        # Improve metrics if repair successful
                        node.update_health_metrics({
                            "integrity": min(1.0, node.health_metrics["integrity"] + 0.2),
                            "contamination": max(0.0, node.health_metrics["contamination"] - 0.3)
                        })
                    
                    logger.info(f"Auto-repair attempt on compromised node {node_id}: "
                               f"{'successful' if result.get('success', False) else 'failed'}")
                
                # Apply passive energy regeneration for dormant nodes
                elif node.state == CellState.DORMANT:
                    node.update_health_metrics({
                        "energy_level": min(1.0, node.health_metrics["energy_level"] + 0.05)
                    })
                
                # Random check for contamination
                if np.random.random() < 0.05 and node.health_metrics["contamination"] > 0.5:
                    # Report high contamination threat
                    threat_sig = f"contamination-{uuid.uuid4().hex[:8]}"
                    await self.network.register_threat(
                        threat_signature=threat_sig,
                        threat_level=node.health_metrics["contamination"],
                        detected_by="health_monitor"
                    )
                    
                    logger.warning(f"High contamination detected in node {node_id}")
                    
                    # Initiate containment response
                    nearby_nodes = list(node.connected_nodes)[:5]
                    if nearby_nodes:
                        await self.network.perform_network_immune_response(
                            threat_signature=threat_sig,
                            action=ImmuneAction.CONTAIN,
                            node_subset=nearby_nodes
                        )
            
            except Exception as e:
                logger.error(f"Error monitoring node {node_id}: {str(e)}")
    
    async def check_node_health(self, node_id: str) -> Dict[str, Any]:
        """Check health of a specific node"""
        if node_id not in self.network.nodes:
            return {"error": f"Node {node_id} not found"}
            
        node = self.network.nodes[node_id]
        
        # Get current metrics
        metrics = node.health_metrics.copy()
        
        # Add derived metrics
        metrics["overall_health"] = self._calculate_overall_health(metrics)
        metrics["state"] = node.state.value
        metrics["connected_nodes"] = len(node.connected_nodes)
        metrics["time_since_activity"] = (datetime.utcnow() - node.last_active_timestamp).total_seconds()
        
        return metrics
    
    def _calculate_overall_health(self, metrics: Dict[str, float]) -> float:
        """Calculate overall health score from individual metrics"""
        # Weighted sum of positive metrics
        positives = (
            metrics["energy_level"] * 0.3 +
            metrics["integrity"] * 0.4 +
            metrics["responsiveness"] * 0.3
        )
        
        # Negative impact from contamination and errors
        negatives = (
            metrics["contamination"] * 0.6 +
            metrics["error_rate"] * 0.4
        )
        
        # Combine (scale negatives to 0-1)
        return max(0.0, min(1.0, positives * (1.0 - negatives * 0.8)))
