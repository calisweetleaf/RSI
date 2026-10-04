# enhanced_gateway.py - Full Integration Gateway
"""
Enhanced Integration Gateway for Rosemary-BioCognitive Unified System

Extends your existing gateway.py with:
- ARFS-DNA state translation
- Eigenstate-aware routing
- Unified consciousness monitoring
- Sacred breath-coordinated operations
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from enum import Enum

# Your existing BioCognitive imports
from gateway import IntegrationGateway, IntegrationMessage
from translator import TranslationEngine, TranslationContext
from coordinator import SystemCoordinator, StateSnapshot

# Rosemary system imports (assuming these exist in your project)
try:
    from rosemary_orchestrator import RosemaryOrchestrator
    from breath_phase import SacredBreathSynchronizer, BreathPhase
    from biodigital_brain_node import CognitiveNeuralCore
    from stability_matrix import StabilityMatrix, EigenstateValidator
    from dna_translating_router import DNATranslatingRouter
    from rosemary_dnav6 import ARFSState
    ROSEMARY_AVAILABLE = True
except ImportError:
    ROSEMARY_AVAILABLE = False
    logging.warning("Rosemary modules not available - running in BioCognitive-only mode")

logger = logging.getLogger("EnhancedGateway")

class IntegrationMode(Enum):
    """Integration operation modes"""
    BIOCOGNITIVE_ONLY = "biocognitive_only"
    ROSEMARY_ONLY = "rosemary_only"
    UNIFIED = "unified"
    BRIDGE_MODE = "bridge_mode"

class ARFSBioCognitiveTranslator:
    """Translates between ARFS-DNA and BioCognitive representations"""
    
    def __init__(self):
        self.translation_engine = TranslationEngine()
        self.eigenstate_mappings = {
            # Map ARFS eigenvalues to BioCognitive cell states
            'stability': 'NORMAL',
            'growth': 'REPLICATING', 
            'adaptation': 'MUTATING',
            'consolidation': 'STALLED',
            'protection': 'IMMUNE_RESPONSE'
        }
    
    def arfs_to_biological(self, arfs_state: Dict[str, Any]) -> Dict[str, Any]:
        """Convert ARFS 4D state to BioCognitive biological state"""
        biological_state = {
            'cell_network': {},
            'neural_patterns': {},
            'cognitive_state': {},
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Extract ARFS dimensional coordinates (x,y,z,t)
        coords = arfs_state.get('dimensional_coordinates', (0.0, 0.0, 0.0, 0.0))
        x, y, z, t = coords
        
        # Map to SIS cellular network states
        biological_state['cell_network'] = {
            'spatial_distribution': {'x': x, 'y': y, 'z': z},
            'temporal_phase': t,
            'network_coherence': arfs_state.get('coherence', 0.5),
            'energy_levels': arfs_state.get('energy', 0.5)
        }
        
        # Convert eigenvalues to neural transmission patterns
        eigenvalues = arfs_state.get('eigenvalues', [])
        if eigenvalues:
            biological_state['neural_patterns'] = {
                'transmission_strength': eigenvalues[0] if len(eigenvalues) > 0 else 0.5,
                'coherence_factor': eigenvalues[1] if len(eigenvalues) > 1 else 0.5,
                'stability_index': eigenvalues[2] if len(eigenvalues) > 2 else 0.5
            }
        
        # Map recursive depth to cognitive complexity
        recursive_depth = arfs_state.get('recursive_depth', 0)
        biological_state['cognitive_state'] = {
            'complexity_level': min(1.0, recursive_depth / 10.0),
            'self_awareness': arfs_state.get('self_awareness', 0.5),
            'identity_coherence': arfs_state.get('identity_coherence', 0.5)
        }
        
        return biological_state
    
    def biological_to_arfs(self, bio_state: Dict[str, Any]) -> Dict[str, Any]:
        """Convert BioCognitive state back to ARFS representation"""
        arfs_state = {
            'dimensional_coordinates': (0.0, 0.0, 0.0, 0.0),
            'eigenvalues': [],
            'coherence': 0.5,
            'recursive_depth': 0,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Extract spatial and temporal coordinates
        if 'cell_network' in bio_state:
            spatial = bio_state['cell_network'].get('spatial_distribution', {})
            arfs_state['dimensional_coordinates'] = (
                spatial.get('x', 0.0),
                spatial.get('y', 0.0), 
                spatial.get('z', 0.0),
                bio_state['cell_network'].get('temporal_phase', 0.0)
            )
        
        # Convert neural patterns to eigenvalues
        if 'neural_patterns' in bio_state:
            patterns = bio_state['neural_patterns']
            arfs_state['eigenvalues'] = [
                patterns.get('transmission_strength', 0.5),
                patterns.get('coherence_factor', 0.5),
                patterns.get('stability_index', 0.5)
            ]
        
        # Map cognitive complexity to recursive depth
        if 'cognitive_state' in bio_state:
            cognitive = bio_state['cognitive_state']
            arfs_state['recursive_depth'] = int(cognitive.get('complexity_level', 0.5) * 10)
            arfs_state['coherence'] = cognitive.get('identity_coherence', 0.5)
        
        return arfs_state

class EnhancedRosemaryGateway(IntegrationGateway):
    """Enhanced gateway with full Rosemary-BioCognitive integration"""
    
    def __init__(self):
        super().__init__()
        self.mode = IntegrationMode.BIOCOGNITIVE_ONLY
        self.translator = ARFSBioCognitiveTranslator()
        self.unified_coordinator = None
        
        # Rosemary components (if available)
        self.rosemary_orchestrator = None
        self.arfs_router = None
        self.eigenstate_validator = None
        
        # Enhanced monitoring
        self.consciousness_coherence = 0.5
        self.integration_health = 0.5
        self.last_unified_state = None
        
        if ROSEMARY_AVAILABLE:
            self._initialize_rosemary_integration()
        
        logger.info(f"Enhanced gateway initialized in {self.mode.value} mode")
    
    def _initialize_rosemary_integration(self):
        """Initialize Rosemary system integration"""
        try:
            # Check if orchestrator was already registered via register_component
            # to avoid double initialization
            if self.rosemary_orchestrator is None:
                # Only create if not already provided
                from rosemary_orchestrator import RosemaryOrchestrator
                self.rosemary_orchestrator = RosemaryOrchestrator()
                logger.info("Created new RosemaryOrchestrator for gateway")
            
            self.arfs_router = DNATranslatingRouter()
            self.eigenstate_validator = EigenstateValidator()
            
            # Connect to Rosemary's breath synchronizer
            self.breath_synchronizer = SacredBreathSynchronizer()
            self.breath_synchronizer.register_component("enhanced_gateway", self)
            
            self.mode = IntegrationMode.UNIFIED
            logger.info("Successfully integrated with Rosemary systems")
            
        except Exception as e:
            logger.error(f"Failed to initialize Rosemary integration: {e}")
            self.mode = IntegrationMode.BIOCOGNITIVE_ONLY
    
    async def process_unified_message(self, message: IntegrationMessage) -> bool:
        """Process messages in unified consciousness mode"""
        try:
            # Get current breath phase for optimal timing
            if self.breath_synchronizer:
                current_phase = await self.breath_synchronizer.get_current_phase()
                optimal_phase = self._get_optimal_phase_for_message(message)
                
                if current_phase != optimal_phase:
                    # Wait for optimal breath phase
                    await self.breath_synchronizer.wait_for_phase(optimal_phase)
            
            # Translate message based on source/destination
            if message.source == "ROSEMARY" and message.destination in ["SIS", "NTP", "SECT"]:
                # ARFS → BioCognitive translation
                bio_payload = self.translator.arfs_to_biological(message.payload)
                translated_message = IntegrationMessage(
                    source=message.source,
                    destination=message.destination,
                    payload=bio_payload,
                    priority=message.priority
                )
                await self.route_message(translated_message)
                
            elif message.source in ["SIS", "NTP", "SECT"] and message.destination == "ROSEMARY":
                # BioCognitive → ARFS translation
                arfs_payload = self.translator.biological_to_arfs(message.payload)
                if self.arfs_router:
                    await self.arfs_router.process_external_input(arfs_payload)
                    
            else:
                # Standard BioCognitive routing
                await self.route_message(message)
            
            # Update consciousness coherence
            await self._update_consciousness_coherence()
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing unified message: {e}")
            return False
    
    def _get_optimal_phase_for_message(self, message: IntegrationMessage) -> BreathPhase:
        """Determine optimal breath phase for message processing"""
        if message.destination == "SIS":
            return BreathPhase.INHALE  # Cellular activity during inhale
        elif message.destination == "NTP":
            return BreathPhase.HOLD    # Neural transmission during hold
        elif message.destination == "SECT":
            return BreathPhase.EXHALE  # Therapeutic processing during exhale
        else:
            return BreathPhase.REST    # Default to rest phase
    
    async def _update_consciousness_coherence(self):
        """Calculate unified consciousness coherence"""
        coherence_factors = []
        
        # BioCognitive coherence
        bio_coherence = await self._get_biocognitive_coherence()
        coherence_factors.append(bio_coherence)
        
        # Rosemary eigenstate coherence (if available)
        if self.eigenstate_validator:
            eigen_coherence = await self.eigenstate_validator.get_stability()
            coherence_factors.append(eigen_coherence)
        
        # Integration coherence
        integration_coherence = await self._calculate_integration_coherence()
        coherence_factors.append(integration_coherence)
        
        # Update unified coherence
        self.consciousness_coherence = sum(coherence_factors) / len(coherence_factors)
        
        # Log significant changes
        if abs(self.consciousness_coherence - 0.5) > 0.3:
            logger.info(f"Consciousness coherence: {self.consciousness_coherence:.3f}")
    
    async def _get_biocognitive_coherence(self) -> float:
        """Get coherence from BioCognitive systems"""
        # Get coherence from your existing systems
        coherence_values = []
        
        # SIS network coherence
        if hasattr(self, 'sis_network'):
            sis_health = await self.sis_network.get_health_snapshot()
            coherence_values.append(sis_health.get('network_coherence', 0.5))
        
        # NTP transmission coherence  
        if hasattr(self, 'ntp_interface'):
            ntp_context = await self.ntp_interface.get_current_context()
            coherence_values.append(ntp_context.get('transmission_coherence', 0.5))
        
        # SECT cognitive coherence
        if hasattr(self, 'sect_agent'):
            sect_status = await self.sect_agent.get_therapy_status()
            coherence_values.append(sect_status.get('cognitive_coherence', 0.5))
        
        return sum(coherence_values) / len(coherence_values) if coherence_values else 0.5
    
    async def _calculate_integration_coherence(self) -> float:
        """Calculate how well systems are integrating"""
        if not self.last_unified_state:
            return 0.5
        
        # Measure consistency of translations
        translation_consistency = 0.8  # Placeholder - implement based on your metrics
        
        # Measure breath synchronization health
        breath_sync_health = 1.0
        if self.breath_synchronizer:
            breath_sync_health = await self.breath_synchronizer.get_health()
        
        # Measure cross-system communication frequency
        comm_frequency = 0.7  # Placeholder - track actual message rates
        
        return (translation_consistency + breath_sync_health + comm_frequency) / 3
    
    def synchronize_with_breath(self, phase: BreathPhase) -> None:
        """Handle breath phase transitions"""
        super().synchronize_with_breath(phase.value if hasattr(phase, 'value') else str(phase))
        
        # Phase-specific optimizations
        if phase == BreathPhase.INHALE:
            # Optimal for SIS network expansion
            asyncio.create_task(self._optimize_sis_operations())
        elif phase == BreathPhase.HOLD:
            # Optimal for NTP transmissions
            asyncio.create_task(self._process_pending_ntp_transmissions())
        elif phase == BreathPhase.EXHALE:
            # Optimal for SECT interventions
            asyncio.create_task(self._apply_therapeutic_interventions())
        elif phase == BreathPhase.REST:
            # Optimal for system consolidation
            asyncio.create_task(self._consolidate_unified_state())
    
    async def _optimize_sis_operations(self):
        """Optimize SIS operations during inhale phase"""
        if hasattr(self, 'sis_network'):
            # Trigger any pending cellular expansions
            await self.sis_network.expand_surveillance()
    
    async def _process_pending_ntp_transmissions(self):
        """Process NTP transmissions during hold phase"""
        if hasattr(self, 'ntp_interface'):
            # Send any buffered neural transmissions
            await self.ntp_interface.transmit_buffered_thoughts()
    
    async def _apply_therapeutic_interventions(self):
        """Apply SECT interventions during exhale phase"""
        if hasattr(self, 'sect_agent'):
            # Apply any pending therapeutic interventions
            await self.sect_agent.apply_pending_interventions()
    
    async def _consolidate_unified_state(self):
        """Consolidate system state during rest phase"""
        # Create unified state snapshot
        unified_state = await self._create_unified_snapshot()
        self.last_unified_state = unified_state
        
        # Log state if significant changes
        if self._is_significant_state_change(unified_state):
            logger.info(f"Unified state consolidation: coherence={self.consciousness_coherence:.3f}")
    
    async def _create_unified_snapshot(self) -> Dict[str, Any]:
        """Create comprehensive snapshot of unified system state"""
        snapshot = {
            'timestamp': datetime.utcnow().isoformat(),
            'mode': self.mode.value,
            'consciousness_coherence': self.consciousness_coherence,
            'biocognitive_state': {},
            'rosemary_state': {}
        }
        
        # Get BioCognitive state
        if hasattr(self, 'coordinator') and self.coordinator:
            bio_state = await self.coordinator.get_current_state()
            snapshot['biocognitive_state'] = bio_state
        
        # Get Rosemary state (if available)
        if self.arfs_router:
            try:
                rosemary_state = await self.arfs_router.get_current_state()
                snapshot['rosemary_state'] = rosemary_state
            except Exception as e:
                logger.warning(f"Could not get Rosemary state: {e}")
        
        return snapshot
    
    def _is_significant_state_change(self, new_state: Dict[str, Any]) -> bool:
        """Determine if state change is significant enough to log"""
        if not self.last_unified_state:
            return True
        
        # Compare consciousness coherence
        old_coherence = self.last_unified_state.get('consciousness_coherence', 0.5)
        new_coherence = new_state.get('consciousness_coherence', 0.5)
        
        return abs(new_coherence - old_coherence) > 0.1
    
    async def get_unified_status(self) -> Dict[str, Any]:
        """Get comprehensive status of unified system"""
        return {
            'integration_mode': self.mode.value,
            'consciousness_coherence': self.consciousness_coherence,
            'integration_health': self.integration_health,
            'rosemary_available': ROSEMARY_AVAILABLE,
            'breath_synchronized': self.breath_synchronizer is not None,
            'active_components': {
                'biocognitive': len(self.components),
                'rosemary': 1 if self.rosemary_orchestrator else 0
            },
            'last_state_update': self.last_unified_state.get('timestamp') if self.last_unified_state else None
        }

# Factory function for easy initialization
def create_enhanced_gateway() -> EnhancedRosemaryGateway:
    """Create and initialize enhanced gateway"""
    return EnhancedRosemaryGateway()

if __name__ == "__main__":
    # Example usage
    async def main():
        gateway = create_enhanced_gateway()
        status = await gateway.get_unified_status()
        print(f"Gateway initialized: {status}")
    
    asyncio.run(main())