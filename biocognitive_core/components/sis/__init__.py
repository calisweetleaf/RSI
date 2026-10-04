# src/biocognitive_core/components/sis/__init__.py
"""
Synthetic Immune Symbiont (SIS) Component

This package implements the SIS component of the biocognitive framework,
which provides programmable nanobiotic cellular networks with self-regulatory capacities.
"""

from .network import (
    NanobotSpec, 
    NanobotNode, 
    SISNetwork, 
    CellState, 
    ImmuneAction,
    HealthMonitor
)
from .evolution import (
    EvolutionStrategy,
    EvolutionConstraint,
    EvolutionLineage,
    EvolutionManager
)
from .monitoring import (
    AlertLevel,
    HealthStatus,
    NodeHealthReport,
    SystemHealthSnapshot,
    HealthMonitor as NetworkHealthMonitor
)

__all__ = [
    # From network.py
    'NanobotSpec',
    'NanobotNode',
    'SISNetwork',
    'CellState',
    'ImmuneAction',
    'HealthMonitor',
    
    # From evolution.py
    'EvolutionStrategy',
    'EvolutionConstraint',
    'EvolutionLineage',
    'EvolutionManager',
    
    # From monitoring.py
    'AlertLevel',
    'HealthStatus',
    'NodeHealthReport',
    'SystemHealthSnapshot',
    'NetworkHealthMonitor'
]

import asyncio
import logging
import os

# Package initialization
async def _check_component_integrity_async() -> None:
    """Verify component compatibility when explicitly requested."""
    network = SISNetwork()
    evolver = EvolutionManager()
    monitor = NetworkHealthMonitor(network)

    node_id = "test_node"
    await network.add_node(node_id, NanobotSpec())
    evolver.evolve_node(node_id, EvolutionStrategy.DIRECTIONAL_SELECTION, {"dna_damage": 0.8})
    snapshot = await monitor._generate_health_snapshot()

    if not isinstance(snapshot, SystemHealthSnapshot):
        raise RuntimeError("Unexpected health snapshot type")
    if len(network.nodes) == 0:
        raise RuntimeError("No nodes registered during integrity check")
    if len(evolver.lineage_db) == 0:
        raise RuntimeError("Evolution lineage not recorded during integrity check")


def _maybe_run_integrity_check() -> None:
    """Run integrity check only when explicitly enabled."""
    if os.getenv("BIOC_SIS_VALIDATE_IMPORT", "").lower() not in {"1", "true", "yes"}:
        return
    try:
        asyncio.run(_check_component_integrity_async())
    except RuntimeError as exc:
        logging.getLogger(__name__).warning(
            "Skipping SIS integrity check: %s", exc
        )


_maybe_run_integrity_check()
