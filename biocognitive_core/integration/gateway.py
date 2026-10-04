# src/integration/gateway.py
"""
System Integration Gateway

Coordinates communication between SIS, NTP, and SECT components with:
- Secure inter-component messaging
- Protocol translation
- Emergency containment protocols
"""

from typing import Dict, Any, Optional, List, Union, AsyncGenerator
from pydantic import BaseModel, Field, validator
import asyncio
import json
import uuid
import logging
from datetime import datetime

# Use absolute imports for cross-package access
from biocognitive_core.components.sis.network import SISNetwork, CellState, NanobotNode
from biocognitive_core.components.ntp.interface import NeuralInterface, ThoughtDomain, TransmissionProfile
from biocognitive_core.components.sect.agent import CognitiveTherapist, PsychologicalModel, TherapyGoal
from biocognitive_core.exceptions import BiocognitiveError, SystemBoundaryViolation
from biocognitive_core.metrics import SISMetrics, NTPMetrics, SECTMetrics
from infrastructure.observability import log_event, log_error

logger = logging.getLogger(__name__)

class IntegrationMessage(BaseModel):
    """Standardized message format for inter-component communication"""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str
    destination: str
    payload: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    priority: int = Field(default=1, ge=1, le=5)

class GatewayRouter:
    """Central routing engine for inter-component communication"""
    def __init__(self):
        self.sis_network = SISNetwork()
        self.ntp_interface = NeuralInterface(TransmissionProfile())
        self.sect_agent = CognitiveTherapist("system")
        self.message_handlers = {
            "SIS->NTP": self._handle_sis_to_ntp,
            "NTP->SIS": self._handle_ntp_to_sis,
            "SECT->SIS": self._handle_sect_to_sis,
            "NTP->SECT": self._handle_ntp_to_sect,
            "SIS->SECT": self._handle_sis_to_sect
        }

    async def route_message(self, message: IntegrationMessage):
        """
        Route messages between components with protocol translation
        
        >>> gateway = GatewayRouter()
        >>> await gateway.route_message(IntegrationMessage(source="SIS", destination="NTP", payload={"cell_state": "mutating"}))
        """
        handler_key = f"{message.source}->{message.destination}"
        if handler_key not in self.message_handlers:
            raise SystemBoundaryViolation(
                f"No valid handler for {handler_key} communication",
                code="CORE-004",
                violating_component=handler_key
            )
            
        await self.message_handlers[handler_key](message)
        log_event("message_routed", {"source": message.source, "destination": message.destination})

    async def _handle_sis_to_ntp(self, message: IntegrationMessage):
        """Translate immune system states to neural signals"""
        if "cell_state" in message.payload:
            cell_state = CellState(message.payload["cell_state"])
            if cell_state == CellState.MUTATING:
                await self.ntp_interface.transmit_thought(
                    NeuralSignal(domain=ThoughtDomain.PHYSIOLOGICAL),
                    "central_monitor"
                )
                SISMetrics.track_event("mutation_notification", {"source": "SIS"})

    async def _handle_ntp_to_sis(self, message: IntegrationMessage):
        """Convert neural signals to immune responses"""
        if "thought_domain" in message.payload:
            domain = ThoughtDomain(message.payload["thought_domain"])
            if domain == ThoughtDomain.EMOTIONAL:
                self.sis_network.initiate_response(ImmuneAction("replication", "stress_response"))
                NTPMetrics.track_event("emotion_to_immune", {"domain": domain.value})

    async def _handle_sect_to_sis(self, message: IntegrationMessage):
        """Apply cognitive therapy to immune system states"""
        if "therapy_goal" in message.payload:
            goal = TherapyGoal(message.payload["therapy_goal"])
            if goal == TherapyGoal.EMOTIONAL_STABILITY:
                self.sis_network.evolutionary_update("stress_regulation")
                SECTMetrics.track_event("therapy_applied", {"goal": goal.value})

    async def _handle_ntp_to_sect(self, message: IntegrationMessage):
        """Translate neural signals to therapeutic interventions"""
        if "cognitive_pattern" in message.payload:
            pattern = message.payload["cognitive_pattern"]
            self.sect_agent.generate_intervention(TherapyGoal.IDENTITY_COHERENCE)
            NTPMetrics.track_event("pattern_to_therapy", {"pattern": pattern})

    async def _handle_sis_to_sect(self, message: IntegrationMessage):
        """Convert immune system states to therapeutic goals"""
        if "cell_health" in message.payload:
            health = message.payload["cell_health"]
            if health < 0.6:
                self.sect_agent.generate_intervention(TherapyGoal.PHYSIOLOGICAL_STABILITY)
                SISMetrics.track_event("health_to_therapy", {"health": health})

class IntegrationGateway:
    """Gateway for handling integration between components"""
    
    def __init__(self):
        self.breath_synchronizer = None
        self.components = {}
        self._initialize_gateway()
    
    def _initialize_gateway(self):
        """Initialize the integration gateway"""
        try:
            from rosemary_integration.breath_phase import get_sacred_breath_synchronizer
            self.breath_synchronizer = get_sacred_breath_synchronizer()
            self.breath_synchronizer.register_component("integration_gateway", self)
            logger.info("Successfully connected to Sacred Breath Synchronizer")
        except Exception as e:
            logger.error(f"Failed to initialize breath synchronization: {e}")

    def register_component(self, name: str, component: Any) -> None:
        """Register a component with the gateway"""
        self.components[name] = component
        if self.breath_synchronizer and hasattr(component, 'synchronize_with_breath'):
            try:
                self.breath_synchronizer.register_component(name, component)
                logger.info(f"Registered {name} with breath synchronizer")
            except Exception as e:
                logger.error(f"Failed to register {name} with breath synchronizer: {e}")

    async def initialize(self) -> None:
        """
        Initialize the integration gateway asynchronously

        Performs any async initialization tasks and ensures all components are ready.
        """
        logger.info("Initializing IntegrationGateway...")

        # Initialize any async components
        for name, component in self.components.items():
            if hasattr(component, 'initialize') and asyncio.iscoroutinefunction(component.initialize):
                try:
                    await component.initialize()
                    logger.debug(f"Initialized component: {name}")
                except Exception as e:
                    logger.error(f"Failed to initialize component {name}: {e}")

        logger.info("IntegrationGateway initialization complete")

    async def shutdown(self) -> None:
        """
        Gracefully shutdown the integration gateway

        Ensures all components are properly shut down and resources are released.
        """
        logger.info("Shutting down IntegrationGateway...")

        # Shutdown all registered components
        for name, component in self.components.items():
            if hasattr(component, 'shutdown'):
                try:
                    if asyncio.iscoroutinefunction(component.shutdown):
                        await component.shutdown()
                    else:
                        component.shutdown()
                    logger.debug(f"Shutdown component: {name}")
                except Exception as e:
                    logger.error(f"Failed to shutdown component {name}: {e}")

        # Unregister from breath synchronizer
        if self.breath_synchronizer and hasattr(self.breath_synchronizer, 'unregister_component'):
            try:
                self.breath_synchronizer.unregister_component("integration_gateway")
            except Exception as e:
                logger.debug(f"Could not unregister from breath synchronizer: {e}")

        logger.info("IntegrationGateway shutdown complete")

    def synchronize_with_breath(self, phase: str) -> None:
        """Handle breath phase updates"""
        for name, component in self.components.items():
            if hasattr(component, 'synchronize_with_breath'):
                try:
                    component.synchronize_with_breath(phase)
                except Exception as e:
                    logger.error(f"Failed to synchronize {name} with breath phase: {e}")

    async def coordinate_transmission(self, source: str, target: str, data: Any) -> bool:
        """Coordinate transmission between components with breath synchronization"""
        if not self.breath_synchronizer:
            logger.warning("Breath synchronization not available")
            return True  # Allow transmission without synchronization
            
        # Wait for optimal transmission phase
        try:
            await self.breath_synchronizer.wait_for_optimal_phase(data.get('type', 'STANDARD'))
        except Exception as e:
            logger.error(f"Error waiting for optimal phase: {e}")
            return False
            
        # Proceed with transmission
        if source in self.components and target in self.components:
            try:
                await self.components[target].receive(data, source)
                return True
            except Exception as e:
                logger.error(f"Transmission failed: {e}")
                return False
        return False