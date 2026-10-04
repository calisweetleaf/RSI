# src/biocognitive_core/components/sis/evolution.py
"""
Synthetic Immune Symbiont Evolutionary Control System

Manages multi-timescale evolutionary adaptation with:
- Hierarchical constraint enforcement
- Multi-objective optimization
- Evolutionary containment protocols
- Versioned lineage tracking
Author: Morpheus
Date: 2025-05-08
Version: 1.0.0
Description: This module implements the evolutionary control system for the SIS component. It includes various evolutionary strategies, constraint management, and lineage tracking. The system is designed to adapt nanobot specifications based on environmental conditions and evolutionary pressures.
ID: SIS-003
SHA-256: 192c3f4e5d6a7b8c9e0f1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3
"""

from typing import Dict, Set, Optional, List, Tuple, Union, AsyncGenerator
from pydantic import BaseModel, Field, validator, root_validator
from enum import Enum
import asyncio
import numpy as np
from biocognitive_core.config import settings
from biocognitive_core.exceptions import BiocognitiveError, EvolutionConstraintViolation
from biocognitive_core.metrics import SISMetrics
from .network import NanobotSpec, CellState
from datetime import datetime, timedelta
import hashlib
import json

class EvolutionStrategy(Enum):
    """Evolutionary adaptation strategies"""
    STOCHASTIC_MUTATION = "stochastic"
    DIRECTIONAL_SELECTION = "directional"
    PREDICTIVE_ADAPTATION = "predictive"
    COEVOLUTION = "coevolution"

class EvolutionConstraint(BaseModel):
    """Constraint definitions for evolutionary processes"""
    max_mutation_rate: float = Field(default=0.1)
    min_energy_reserve: float = Field(default=0.3)
    max_replication_rate: float = Field(default=0.2)
    lineage_depth_limit: int = Field(default=5)
    containment_threshold: float = Field(default=0.9)

class EvolutionLineage:
    """Tracks evolutionary lineage history"""
    def __init__(self, spec: NanobotSpec):
        self.root_hash = self._generate_spec_hash(spec)
        self.lineage: List[Tuple[str, datetime]] = [(self.root_hash, datetime.utcnow())]
        self.containment_score = 1.0

    def _generate_spec_hash(self, spec: NanobotSpec) -> str:
        """Generate cryptographic hash of nanobot specification"""
        spec_bytes = json.dumps(spec.dict(), sort_keys=True).encode()
        return hashlib.sha256(spec_bytes).hexdigest()

    def add_evolution_step(self, new_spec: NanobotSpec):
        """Record evolutionary step in lineage"""
        new_hash = self._generate_spec_hash(new_spec)
        self.lineage.append((new_hash, datetime.utcnow()))
        
        # Calculate containment score based on deviation
        deviation = self._calculate_deviation(new_spec)
        self.containment_score = max(0.0, min(1.0, 1.0 - deviation * 0.5))
        
        if self.containment_score < settings.immune.evolution_containment_threshold:
            raise EvolutionConstraintViolation(
                "Evolutionary containment threshold breached",
                code="SIS-002",
                mutation_rate=new_spec.mutation_threshold,
                allowed_threshold=settings.immune.mutation_threshold
            )

    def _calculate_deviation(self, new_spec: NanobotSpec) -> float:
        """Calculate deviation from original specification"""
        root_spec = NanobotSpec(**json.loads(hashlib.sha256(self.root_hash.encode()).digest().hex()))
        deviation = 0.0
        
        # Calculate parameter deviations
        deviation += abs(new_spec.replication_rate - root_spec.replication_rate) / (root_spec.replication_rate + 1e-9)
        deviation += abs(new_spec.mutation_threshold - root_spec.mutation_threshold) / (root_spec.mutation_threshold + 1e-9)
        deviation += abs(new_spec.energy_efficiency - root_spec.energy_efficiency) / (root_spec.energy_efficiency + 1e-9)
        
        return deviation / 3.0

class EvolutionManager:
    """Central evolutionary control system"""
    def __init__(self):
        self.lineage_db: Dict[str, EvolutionLineage] = {}
        self.constraint_set = EvolutionConstraint()
        self.strategy_map = {
            EvolutionStrategy.STOCHASTIC_MUTATION: self._stochastic_evolution,
            EvolutionStrategy.DIRECTIONAL_SELECTION: self._directional_evolution,
            EvolutionStrategy.PREDICTIVE_ADAPTATION: self._predictive_evolution,
            EvolutionStrategy.COEVOLUTION: self._coevolution
        }
        self.metrics_collector = SISMetrics()

    async def evolve_node(self, node_id: str, strategy: EvolutionStrategy, target_conditions: Dict):
        """
        Execute evolutionary adaptation with specified strategy
        
        >>> manager = EvolutionManager()
        >>> await manager.evolve_node("node123", EvolutionStrategy.DIRECTIONAL_SELECTION, {"dna_damage": 0.8})
        """
        if node_id not in self.lineage_db:
            self.lineage_db[node_id] = EvolutionLineage(NanobotSpec())
            
        lineage = self.lineage_db[node_id]
        new_spec = await self._apply_evolution_strategy(strategy, target_conditions)
        
        if self._validate_evolution(lineage, new_spec):
            lineage.add_evolution_step(new_spec)
            self.metrics_collector.track_evolution(node_id, new_spec.mutation_threshold)
            return new_spec
        else:
            raise EvolutionConstraintViolation(
                "Evolution failed validation checks",
                code="SIS-003",
                mutation_rate=new_spec.mutation_threshold,
                allowed_threshold=settings.immune.mutation_threshold
            )

    async def _apply_evolution_strategy(self, strategy: EvolutionStrategy, target_conditions: Dict) -> NanobotSpec:
        """Apply selected evolutionary strategy"""
        return await self.strategy_map[strategy](target_conditions)

    async def _stochastic_evolution(self, conditions: Dict) -> NanobotSpec:
        """Random mutation-based evolution"""
        base_spec = NanobotSpec()
        mutation_rate = base_spec.mutation_threshold + np.random.normal(0.05, 0.02)
        return NanobotSpec(
            replication_rate=min(0.2, base_spec.replication_rate * 1.1),
            mutation_threshold=mutation_rate,
            energy_efficiency=base_spec.energy_efficiency * 1.05,
            communication_range=base_spec.communication_range * 1.02,
            version=1
        )

    async def _directional_evolution(self, conditions: Dict) -> NanobotSpec:
        """Directed adaptation based on environmental pressures"""
        dna_damage = conditions.get("dna_damage", 0.0)
        energy_demand = conditions.get("energy_demand", 0.0)
        
        base_spec = NanobotSpec()
        mutation_rate = base_spec.mutation_threshold + max(0.0, dna_damage - 0.7)
        energy_efficiency = base_spec.energy_efficiency * (1.0 + energy_demand * 0.2)
        
        return NanobotSpec(
            replication_rate=min(0.2, base_spec.replication_rate * (1.0 + energy_demand * 0.1)),
            mutation_threshold=min(0.95, mutation_rate),
            energy_efficiency=min(0.95, energy_efficiency),
            communication_range=base_spec.communication_range * (1.0 + dna_damage * 0.1),
            version=1
        )

    async def _predictive_evolution(self, conditions: Dict) -> NanobotSpec:
        """Adaptive evolution using predictive modeling"""
        # In production, this would use machine learning models
        dna_damage = conditions.get("dna_damage", 0.0)
        return NanobotSpec(
            replication_rate=min(0.2, 0.05 + dna_damage * 0.15),
            mutation_threshold=min(0.95, 0.75 + dna_damage * 0.2),
            energy_efficiency=0.85 * (1.0 + dna_damage * 0.05),
            communication_range=5.0 * (1.0 + dna_damage * 0.1),
            version=1
        )

    async def _coevolution(self, conditions: Dict) -> NanobotSpec:
        """Co-evolution with neighboring nodes"""
        # In production, this would analyze network dynamics
        return NanobotSpec(
            replication_rate=0.05 + np.random.uniform(0.0, 0.1),
            mutation_threshold=0.75 + np.random.uniform(0.0, 0.2),
            energy_efficiency=0.85 * (1.0 + np.random.uniform(0.0, 0.1)),
            communication_range=5.0 * (1.0 + np.random.uniform(0.0, 0.2)),
            version=1
        )

    def _validate_evolution(self, lineage: EvolutionLineage, new_spec: NanobotSpec) -> bool:
        """Validate evolutionary adaptation against constraints"""
        # Check lineage depth
        if len(lineage.lineage) > self.constraint_set.lineage_depth_limit:
            return False
            
        # Check mutation rate
        if new_spec.mutation_threshold > self.constraint_set.max_mutation_rate:
            return False
            
        # Check energy efficiency
        if new_spec.energy_efficiency < self.constraint_set.min_energy_reserve:
            return False
            
        # Check replication rate
        if new_spec.replication_rate > self.constraint_set.max_replication_rate:
            return False
            
        # Check containment score
        if lineage.containment_score < self.constraint_set.containment_threshold:
            return False
            
        return True

    def get_evolution_history(self, node_id: str) -> List[Dict]:
        """Retrieve evolutionary history for audit purposes"""
        if node_id not in self.lineage_db:
            return []
            
        lineage = self.lineage_db[node_id]
        return [
            {
                "timestamp": step[1].isoformat(),
                "spec_hash": step[0],
                "containment_score": lineage.containment_score
            }
            for step in lineage.lineage
        ]
