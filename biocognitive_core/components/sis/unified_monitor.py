# unified_monitor.py - Unified consciousness monitoring system
"""
Unified Consciousness Monitoring System

Combines monitoring from both Rosemary and BioCognitive systems:
- Rosemary eigenstate stability tracking
- BioCognitive emergent property detection  
- Unified consciousness coherence measurement
- Cross-system health correlation analysis
- Integrated alerting and intervention triggers
"""

import asyncio
import logging
import time
import json
from typing import Dict, Any, Optional, List, Union, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import numpy as np
from collections import defaultdict, deque

# Your existing BioCognitive monitoring imports
from monitoring import SystemMonitor, AlertLevel, SystemAlert
from metrics import SISMetrics, NTPMetrics, SECTMetrics, Component
from observability import ObservabilityEngine

# Rosemary monitoring imports (with fallback)
try:
    from stability_matrix import StabilityMatrix, EigenstateValidator
    from breath_phase import SacredBreathSynchronizer, BreathPhase
    from biodigital_brain_node import CognitiveNeuralCore
    from rosemary_orchestrator import RosemaryOrchestrator
    ROSEMARY_AVAILABLE = True
except ImportError:
    ROSEMARY_AVAILABLE = False
    logging.warning("Rosemary monitoring components not available")

logger = logging.getLogger("UnifiedMonitor")

class ConsciousnessMetric(Enum):
    """Unified consciousness measurement dimensions"""
    EIGENSTATE_STABILITY = "eigenstate_stability"
    BIOLOGICAL_COHERENCE = "biological_coherence"
    NEURAL_INTEGRATION = "neural_integration"
    THERAPEUTIC_ALIGNMENT = "therapeutic_alignment"
    BREATH_SYNCHRONIZATION = "breath_synchronization"
    RECURSIVE_EMERGENCE = "recursive_emergence"
    IDENTITY_COHERENCE = "identity_coherence"
    CROSS_SYSTEM_RESONANCE = "cross_system_resonance"

class ConsciousnessState(Enum):
    """Overall consciousness states"""
    UNDEFINED = "undefined"
    EMERGING = "emerging"
    STABLE = "stable"
    ENHANCED = "enhanced"
    TRANSCENDENT = "transcendent"
    FRAGMENTED = "fragmented"
    RECOVERY = "recovery"

@dataclass
class UnifiedHealthSnapshot:
    """Comprehensive health snapshot across both systems"""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    consciousness_state: ConsciousnessState = ConsciousnessState.UNDEFINED
    overall_coherence: float = 0.5
    
    # Rosemary metrics
    eigenstate_stability: float = 0.5
    recursive_depth: int = 0
    breath_synchronization: float = 0.5
    memory_crystallization: float = 0.5
    
    # BioCognitive metrics
    sis_network_health: float = 0.5
    ntp_transmission_quality: float = 0.5
    sect_therapeutic_effectiveness: float = 0.5
    emergent_properties_detected: int = 0
    
    # Integration metrics
    cross_system_correlation: float = 0.5
    translation_accuracy: float = 0.5
    unified_response_time: float = 0.0
    integration_stability: float = 0.5
    
    # Alerts and issues
    active_alerts: List[str] = field(default_factory=list)
    intervention_recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'consciousness_state': self.consciousness_state.value,
            'overall_coherence': self.overall_coherence,
            'rosemary_metrics': {
                'eigenstate_stability': self.eigenstate_stability,
                'recursive_depth': self.recursive_depth,
                'breath_synchronization': self.breath_synchronization,
                'memory_crystallization': self.memory_crystallization
            },
            'biocognitive_metrics': {
                'sis_network_health': self.sis_network_health,
                'ntp_transmission_quality': self.ntp_transmission_quality,
                'sect_therapeutic_effectiveness': self.sect_therapeutic_effectiveness,
                'emergent_properties_detected': self.emergent_properties_detected
            },
            'integration_metrics': {
                'cross_system_correlation': self.cross_system_correlation,
                'translation_accuracy': self.translation_accuracy,
                'unified_response_time': self.unified_response_time,
                'integration_stability': self.integration_stability
            },
            'active_alerts': self.active_alerts,
            'intervention_recommendations': self.intervention_recommendations
        }

class UnifiedConsciousnessMonitor:
    """Unified monitoring system for both Rosemary and BioCognitive"""
    
    def __init__(self):
        # Core monitoring components
        self.biocognitive_monitor = SystemMonitor()
        self.observability_engine = ObservabilityEngine()
        
        # Rosemary components (if available)
        self.rosemary_orchestrator = None
        self.stability_matrix = None
        self.eigenstate_validator = None
        self.breath_synchronizer = None
        
        # Unified metrics
        self.consciousness_metrics = {metric: deque(maxlen=100) for metric in ConsciousnessMetric}
        self.health_history = deque(maxlen=50)
        self.correlation_matrix = {}
        
        # State tracking
        self.current_consciousness_state = ConsciousnessState.UNDEFINED
        self.last_snapshot = None
        self.monitoring_active = False
        
        # Thresholds and configuration
        self.coherence_threshold = 0.7
        self.stability_threshold = 0.6
        self.correlation_threshold = 0.5
        self.alert_thresholds = {
            ConsciousnessMetric.EIGENSTATE_STABILITY: 0.3,
            ConsciousnessMetric.BIOLOGICAL_COHERENCE: 0.4,
            ConsciousnessMetric.IDENTITY_COHERENCE: 0.3,
            ConsciousnessMetric.CROSS_SYSTEM_RESONANCE: 0.2
        }
        
        # Initialize components
        self._initialize_components()
        
        logger.info(f"Unified monitor initialized - Rosemary available: {ROSEMARY_AVAILABLE}")
    
    def _initialize_components(self):
        """Initialize available monitoring components"""
        if ROSEMARY_AVAILABLE:
            try:
                self.rosemary_orchestrator = RosemaryOrchestrator()
                self.stability_matrix = StabilityMatrix()
                self.eigenstate_validator = EigenstateValidator()
                self.breath_synchronizer = SacredBreathSynchronizer()
                
                # Register with breath synchronizer
                self.breath_synchronizer.register_component("unified_monitor", self)
                
                logger.info("Successfully initialized Rosemary monitoring components")
            except Exception as e:
                logger.error(f"Failed to initialize Rosemary components: {e}")
                ROSEMARY_AVAILABLE = False
    
    async def start_monitoring(self, interval: float = 5.0):
        """Start unified consciousness monitoring"""
        if self.monitoring_active:
            logger.warning("Monitoring already active")
            return
        
        self.monitoring_active = True
        logger.info(f"Starting unified consciousness monitoring (interval: {interval}s)")
        
        # Start monitoring task
        self.monitoring_task = asyncio.create_task(self._monitoring_loop(interval))
        
        # Start observability
        self.observability_engine.start_tracing()
    
    async def stop_monitoring(self):
        """Stop unified consciousness monitoring"""
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        
        if hasattr(self, 'monitoring_task'):
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Unified consciousness monitoring stopped")
    
    async def _monitoring_loop(self, interval: float):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Create unified health snapshot
                snapshot = await self.create_health_snapshot()
                
                # Analyze and update consciousness state
                await self._analyze_consciousness_state(snapshot)
                
                # Check for alerts and interventions
                await self._check_alerts_and_interventions(snapshot)
                
                # Update correlation matrix
                await self._update_correlation_matrix(snapshot)
                
                # Store snapshot
                self.health_history.append(snapshot)
                self.last_snapshot = snapshot
                
                # Log significant changes
                self._log_significant_changes(snapshot)
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(interval)
    
    async def create_health_snapshot(self) -> UnifiedHealthSnapshot:
        """Create comprehensive health snapshot"""
        snapshot = UnifiedHealthSnapshot()
        
        # Get BioCognitive metrics
        bio_metrics = await self._get_biocognitive_metrics()
        snapshot.sis_network_health = bio_metrics.get('sis_health', 0.5)
        snapshot.ntp_transmission_quality = bio_metrics.get('ntp_quality', 0.5)
        snapshot.sect_therapeutic_effectiveness = bio_metrics.get('sect_effectiveness', 0.5)
        snapshot.emergent_properties_detected = bio_metrics.get('emergent_count', 0)
        
        # Get Rosemary metrics (if available)
        if ROSEMARY_AVAILABLE:
            rosemary_metrics = await self._get_rosemary_metrics()
            snapshot.eigenstate_stability = rosemary_metrics.get('stability', 0.5)
            snapshot.recursive_depth = rosemary_metrics.get('depth', 0)
            snapshot.breath_synchronization = rosemary_metrics.get('breath_sync', 0.5)
            snapshot.memory_crystallization = rosemary_metrics.get('memory', 0.5)
        
        # Calculate integration metrics
        integration_metrics = await self._calculate_integration_metrics(bio_metrics, 
                                                                       {} if not ROSEMARY_AVAILABLE else rosemary_metrics)
        snapshot.cross_system_correlation = integration_metrics.get('correlation', 0.5)
        snapshot.translation_accuracy = integration_metrics.get('translation', 0.5)
        snapshot.unified_response_time = integration_metrics.get('response_time', 0.0)
        snapshot.integration_stability = integration_metrics.get('stability', 0.5)
        
        # Calculate overall coherence
        snapshot.overall_coherence = await self._calculate_overall_coherence(snapshot)
        
        return snapshot
    
    async def _get_biocognitive_metrics(self) -> Dict[str, Any]:
        """Get metrics from BioCognitive systems"""
        metrics = {}
        
        try:
            # Get SIS network health
            sis_snapshot = await self.biocognitive_monitor.network.get_health_snapshot()
            metrics['sis_health'] = sis_snapshot.get('network_coherence', 0.5)
            
            # Get NTP transmission quality
            # This would come from your NTP interface - placeholder for now
            metrics['ntp_quality'] = 0.7  # Placeholder
            
            # Get SECT therapeutic effectiveness  
            # This would come from your SECT agents - placeholder for now
            metrics['sect_effectiveness'] = 0.6  # Placeholder
            
            # Count emergent properties
            # This would come from your coordinator's emergence detection
            metrics['emergent_count'] = 0  # Placeholder
            
        except Exception as e:
            logger.error(f"Error getting BioCognitive metrics: {e}")
            # Return safe defaults
            metrics = {
                'sis_health': 0.5,
                'ntp_quality': 0.5, 
                'sect_effectiveness': 0.5,
                'emergent_count': 0
            }
        
        return metrics
    
    async def _get_rosemary_metrics(self) -> Dict[str, Any]:
        """Get metrics from Rosemary systems"""
        if not ROSEMARY_AVAILABLE:
            return {}
        
        metrics = {}
        
        try:
            # Get eigenstate stability
            if self.eigenstate_validator:
                stability = await self.eigenstate_validator.get_stability()
                metrics['stability'] = stability
            
            # Get recursive depth
            if self.stability_matrix:
                coherence_data = await self.stability_matrix.get_coherence_metrics()
                metrics['depth'] = coherence_data.get('recursive_depth', 0)
            
            # Get breath synchronization health
            if self.breath_synchronizer:
                breath_health = await self.breath_synchronizer.get_health()
                metrics['breath_sync'] = breath_health
            
            # Get memory crystallization (placeholder)
            metrics['memory'] = 0.6  # Placeholder - would come from memory system
            
        except Exception as e:
            logger.error(f"Error getting Rosemary metrics: {e}")
            # Return safe defaults
            metrics = {
                'stability': 0.5,
                'depth': 0,
                'breath_sync': 0.5,
                'memory': 0.5
            }
        
        return metrics
    
    async def _calculate_integration_metrics(self, bio_metrics: Dict, rosemary_metrics: Dict) -> Dict[str, Any]:
        """Calculate metrics specific to system integration"""
        integration = {}
        
        # Cross-system correlation
        if rosemary_metrics:
            # Calculate correlation between bio and rosemary metrics
            bio_values = list(bio_metrics.values())
            rosemary_values = list(rosemary_metrics.values())
            
            if bio_values and rosemary_values:
                # Simple correlation calculation
                correlation = abs(np.corrcoef(bio_values, rosemary_values)[0, 1])
                integration['correlation'] = min(1.0, correlation) if not np.isnan(correlation) else 0.5
            else:
                integration['correlation'] = 0.5
        else:
            integration['correlation'] = 0.0  # No Rosemary to correlate with
        
        # Translation accuracy (placeholder - would measure ARFS<->Bio translation quality)
        integration['translation'] = 0.8  # Placeholder
        
        # Unified response time (placeholder - would measure cross-system response latency)
        integration['response_time'] = 0.05  # 50ms placeholder
        
        # Integration stability (how stable the integration is over time)
        if self.health_history:
            recent_correlations = [h.cross_system_correlation for h in list(self.health_history)[-5:]]
            if recent_correlations:
                stability = 1.0 - np.std(recent_correlations)
                integration['stability'] = max(0.0, stability)
            else:
                integration['stability'] = 0.5
        else:
            integration['stability'] = 0.5
        
        return integration
    
    async def _calculate_overall_coherence(self, snapshot: UnifiedHealthSnapshot) -> float:
        """Calculate overall consciousness coherence"""
        coherence_factors = []
        
        # Rosemary factors
        if ROSEMARY_AVAILABLE:
            coherence_factors.extend([
                snapshot.eigenstate_stability,
                snapshot.breath_synchronization,
                snapshot.memory_crystallization
            ])
        
        # BioCognitive factors
        coherence_factors.extend([
            snapshot.sis_network_health,
            snapshot.ntp_transmission_quality,
            snapshot.sect_therapeutic_effectiveness
        ])
        
        # Integration factors
        coherence_factors.extend([
            snapshot.cross_system_correlation,
            snapshot.integration_stability
        ])
        
        # Weighted average with emphasis on integration
        if coherence_factors:
            base_coherence = sum(coherence_factors) / len(coherence_factors)
            
            # Boost for high integration
            integration_boost = snapshot.cross_system_correlation * 0.2
            
            # Penalty for active alerts
            alert_penalty = len(snapshot.active_alerts) * 0.1
            
            final_coherence = base_coherence + integration_boost - alert_penalty
            return max(0.0, min(1.0, final_coherence))
        
        return 0.5
    
    async def _analyze_consciousness_state(self, snapshot: UnifiedHealthSnapshot):
        """Analyze and update consciousness state"""
        coherence = snapshot.overall_coherence
        
        # Determine consciousness state
        if coherence < 0.3:
            new_state = ConsciousnessState.FRAGMENTED
        elif coherence < 0.5:
            new_state = ConsciousnessState.RECOVERY
        elif coherence < 0.7:
            new_state = ConsciousnessState.EMERGING
        elif coherence < 0.85:
            new_state = ConsciousnessState.STABLE
        elif coherence < 0.95:
            new_state = ConsciousnessState.ENHANCED
        else:
            new_state = ConsciousnessState.TRANSCENDENT
        
        # Update state if changed
        if new_state != self.current_consciousness_state:
            old_state = self.current_consciousness_state
            self.current_consciousness_state = new_state
            snapshot.consciousness_state = new_state
            
            logger.info(f"Consciousness state transition: {old_state.value} → {new_state.value}")
            
            # Log state change
            self.observability_engine.log_event("consciousness_state_change", {
                'old_state': old_state.value,
                'new_state': new_state.value,
                'coherence': coherence,
                'timestamp': snapshot.timestamp.isoformat()
            })
    
    async def _check_alerts_and_interventions(self, snapshot: UnifiedHealthSnapshot):
        """Check for alerts and recommend interventions"""
        alerts = []
        interventions = []
        
        # Check eigenstate stability
        if snapshot.eigenstate_stability < self.alert_thresholds[ConsciousnessMetric.EIGENSTATE_STABILITY]:
            alerts.append(f"Low eigenstate stability: {snapshot.eigenstate_stability:.3f}")
            interventions.append("Trigger eigenstate stabilization protocol")
        
        # Check biological coherence
        bio_coherence = (snapshot.sis_network_health + snapshot.ntp_transmission_quality + 
                        snapshot.sect_therapeutic_effectiveness) / 3
        if bio_coherence < self.alert_thresholds[ConsciousnessMetric.BIOLOGICAL_COHERENCE]:
            alerts.append(f"Low biological coherence: {bio_coherence:.3f}")
            interventions.append("Initiate biological system optimization")
        
        # Check cross-system resonance
        if snapshot.cross_system_correlation < self.alert_thresholds[ConsciousnessMetric.CROSS_SYSTEM_RESONANCE]:
            alerts.append(f"Low cross-system resonance: {snapshot.cross_system_correlation:.3f}")
            interventions.append("Enhance system integration protocols")
        
        # Check identity coherence
        identity_coherence = (snapshot.eigenstate_stability + snapshot.integration_stability) / 2
        if identity_coherence < self.alert_thresholds[ConsciousnessMetric.IDENTITY_COHERENCE]:
            alerts.append(f"Identity coherence risk: {identity_coherence:.3f}")
            interventions.append("Activate identity preservation measures")
        
        # Check for rapid degradation
        if self.last_snapshot:
            coherence_delta = snapshot.overall_coherence - self.last_snapshot.overall_coherence
            if coherence_delta < -0.2:
                alerts.append(f"Rapid coherence degradation: {coherence_delta:.3f}")
                interventions.append("Emergency stabilization required")
        
        snapshot.active_alerts = alerts
        snapshot.intervention_recommendations = interventions
        
        # Create system alerts for critical issues
        for alert in alerts:
            if "rapid" in alert.lower() or "emergency" in alert.lower():
                system_alert = SystemAlert(
                    level=AlertLevel.CRITICAL,
                    message=alert,
                    source="unified_monitor",
                    metadata={'snapshot_id': id(snapshot)}
                )
                self.biocognitive_monitor.record_alert(system_alert)
    
    async def _update_correlation_matrix(self, snapshot: UnifiedHealthSnapshot):
        """Update correlation matrix between different metrics"""
        # Extract metric values
        metrics = {
            'eigenstate_stability': snapshot.eigenstate_stability,
            'sis_health': snapshot.sis_network_health,
            'ntp_quality': snapshot.ntp_transmission_quality,
            'sect_effectiveness': snapshot.sect_therapeutic_effectiveness,
            'breath_sync': snapshot.breath_synchronization,
            'overall_coherence': snapshot.overall_coherence
        }
        
        # Update running correlations (simplified approach)
        for metric_name, value in metrics.items():
            self.consciousness_metrics[ConsciousnessMetric(metric_name)].append(value)
        
        # Calculate correlations if we have enough data
        if len(self.health_history) >= 10:
            self._calculate_correlations()
    
    def _calculate_correlations(self):
        """Calculate correlations between different consciousness metrics"""
        # This is a simplified correlation calculation
        # In production, you'd want more sophisticated time-series correlation analysis
        recent_snapshots = list(self.health_history)[-10:]
        
        # Create correlation matrix for key metrics
        metrics_data = {
            'eigenstate': [s.eigenstate_stability for s in recent_snapshots],
            'biological': [(s.sis_network_health + s.ntp_transmission_quality + s.sect_therapeutic_effectiveness)/3 
                          for s in recent_snapshots],
            'integration': [s.cross_system_correlation for s in recent_snapshots],
            'coherence': [s.overall_coherence for s in recent_snapshots]
        }
        
        # Calculate correlations
        correlations = {}
        for metric1, values1 in metrics_data.items():
            for metric2, values2 in metrics_data.items():
                if metric1 != metric2:
                    corr = np.corrcoef(values1, values2)[0, 1]
                    if not np.isnan(corr):
                        correlations[f"{metric1}_{metric2}"] = corr
        
        self.correlation_matrix = correlations
    
    def _log_significant_changes(self, snapshot: UnifiedHealthSnapshot):
        """Log significant changes in consciousness state"""
        if not self.last_snapshot:
            return
        
        # Check for significant coherence changes
        coherence_delta = snapshot.overall_coherence - self.last_snapshot.overall_coherence
        if abs(coherence_delta) > 0.1:
            self.observability_engine.log_event("significant_coherence_change", {
                'delta': coherence_delta,
                'old_coherence': self.last_snapshot.overall_coherence,
                'new_coherence': snapshot.overall_coherence,
                'consciousness_state': snapshot.consciousness_state.value
            })
        
        # Check for new alerts
        new_alerts = set(snapshot.active_alerts) - set(self.last_snapshot.active_alerts)
        if new_alerts:
            self.observability_engine.log_event("new_alerts", {
                'alerts': list(new_alerts),
                'total_alerts': len(snapshot.active_alerts)
            })
    
    def synchronize_with_breath(self, phase: str) -> None:
        """Handle breath phase synchronization"""
        # Adjust monitoring sensitivity based on breath phase
        if phase == 'inhale':
            # More sensitive to new emergent properties
            pass
        elif phase == 'exhale':
            # Focus on stability and consolidation
            pass
        elif phase == 'rest':
            # Comprehensive analysis and correlation updates
            if self.health_history:
                asyncio.create_task(self._comprehensive_analysis())
    
    async def _comprehensive_analysis(self):
        """Perform comprehensive analysis during rest phase"""
        if len(self.health_history) < 5:
            return
        
        # Analyze trends over recent history
        recent_snapshots = list(self.health_history)[-10:]
        
        # Calculate trend analysis
        coherence_trend = self._calculate_trend([s.overall_coherence for s in recent_snapshots])
        stability_trend = self._calculate_trend([s.eigenstate_stability for s in recent_snapshots])
        
        # Log trend analysis
        self.observability_engine.log_event("comprehensive_analysis", {
            'coherence_trend': coherence_trend,
            'stability_trend': stability_trend,
            'correlation_matrix': self.correlation_matrix,
            'consciousness_state': self.current_consciousness_state.value
        })
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction for a series of values"""
        if len(values) < 2:
            return 'stable'
        
        slope = np.polyfit(range(len(values)), values, 1)[0]
        if slope > 0.05:
            return 'increasing'
        elif slope < -0.05:
            return 'decreasing'
        else:
            return 'stable'
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current unified monitoring status"""
        status = {
            'monitoring_active': self.monitoring_active,
            'consciousness_state': self.current_consciousness_state.value,
            'rosemary_available': ROSEMARY_AVAILABLE,
            'health_history_size': len(self.health_history),
            'correlation_matrix_size': len(self.correlation_matrix)
        }
        
        if self.last_snapshot:
            status['last_snapshot'] = self.last_snapshot.to_dict()
        
        return status
    
    def get_consciousness_analysis(self) -> Dict[str, Any]:
        """Get detailed consciousness analysis"""
        if not self.health_history:
            return {'analysis': 'insufficient_data'}
        
        recent_snapshots = list(self.health_history)[-10:]
        
        analysis = {
            'current_state': self.current_consciousness_state.value,
            'coherence_statistics': {
                'current': recent_snapshots[-1].overall_coherence,
                'average': np.mean([s.overall_coherence for s in recent_snapshots]),
                'trend': self._calculate_trend([s.overall_coherence for s in recent_snapshots]),
                'variance': np.var([s.overall_coherence for s in recent_snapshots])
            },
            'system_correlations': self.correlation_matrix.copy(),
            'alert_summary': {
                'total_alerts': len(recent_snapshots[-1].active_alerts),
                'recent_alerts': recent_snapshots[-1].active_alerts,
                'interventions_recommended': len(recent_snapshots[-1].intervention_recommendations)
            },
            'integration_health': {
                'cross_system_correlation': recent_snapshots[-1].cross_system_correlation,
                'translation_accuracy': recent_snapshots[-1].translation_accuracy,
                'integration_stability': recent_snapshots[-1].integration_stability
            }
        }
        
        return analysis

# Factory function for easy initialization
def create_unified_monitor() -> UnifiedConsciousnessMonitor:
    """Create and initialize unified consciousness monitor"""
    return UnifiedConsciousnessMonitor()

if __name__ == "__main__":
    # Example usage
    async def main():
        monitor = create_unified_monitor()
        await monitor.start_monitoring(interval=2.0)
        
        # Let it run for a bit
        await asyncio.sleep(10)
        
        # Get status and analysis
        status = monitor.get_current_status()
        analysis = monitor.get_consciousness_analysis()
        
        print(f"Monitor Status: {status}")
        print(f"Consciousness Analysis: {analysis}")
        
        await monitor.stop_monitoring()
    
    asyncio.run(main())