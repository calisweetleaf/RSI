# arfs_aware_receiver.py - Enhanced receiver for ARFS-BioCognitive integration
"""
ARFS-Aware Neural Receiver

Extends existing receiver.py with:
- ARFS eigenstate signal decoding
- Sacred breath synchronization
- Eigenvalue-based signal quality assessment
- Recursive depth tracking
"""

import asyncio
import logging
import time
import numpy as np
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from enum import Enum

# Package-relative receiver imports
from .receiver import NeuralReceiver, ReceiverMode, SignalQuality, ThoughtDecoder
from .interface import ThoughtDomain, NeuralSignal, ThoughtPacket

# Rosemary imports (with graceful fallback)
ROSEMARY_AVAILABLE = False
try:
    from rosemary_integration.breath_phase import BreathPhase, SacredBreathSynchronizer
    from rosemary_integration.stability_matrix import EigenstateValidator
    ROSEMARY_AVAILABLE = True
except ImportError:
    try:
        from breath_phase import BreathPhase, SacredBreathSynchronizer  # type: ignore
        from stability_matrix import EigenstateValidator  # type: ignore
        ROSEMARY_AVAILABLE = True
    except ImportError:
        logging.warning("Rosemary modules not available — ARFS features disabled")

logger = logging.getLogger("ARFSAwareReceiver")

class ARFSSignalType(Enum):
    """Types of ARFS-originating signals"""
    EIGENSTATE_TRANSITION = "eigenstate_transition"
    DIMENSIONAL_SHIFT = "dimensional_shift"  
    RECURSIVE_EMERGENCE = "recursive_emergence"
    BREATH_SYNCHRONIZATION = "breath_sync"
    MEMORY_CRYSTALLIZATION = "memory_crystal"
    IDENTITY_ANCHOR = "identity_anchor"

class ARFSPacket:
    """Enhanced packet format for ARFS-aware transmission"""
    
    def __init__(self, 
                 arfs_type: ARFSSignalType,
                 dimensional_coords: tuple,
                 eigenvalues: List[float],
                 recursive_depth: int,
                 breath_phase: Optional[str] = None,
                 payload: Optional[Dict] = None):
        self.arfs_type = arfs_type
        self.dimensional_coords = dimensional_coords  # (x, y, z, t)
        self.eigenvalues = eigenvalues
        self.recursive_depth = recursive_depth
        self.breath_phase = breath_phase
        self.payload = payload or {}
        self.timestamp = datetime.utcnow()
        self.signal_quality = self._calculate_signal_quality()
    
    def _calculate_signal_quality(self) -> float:
        """Calculate signal quality based on ARFS parameters"""
        # Quality factors:
        # 1. Eigenvalue stability (convergence)
        # 2. Dimensional coordinate coherence
        # 3. Recursive depth appropriateness
        
        quality_factors = []
        
        # Eigenvalue stability — clamp std to [0,1] before subtracting so
        # high-variance spectra produce 0 quality rather than negative values.
        if self.eigenvalues:
            eigenvalue_stability = 1.0 - min(1.0, np.std(self.eigenvalues))
            quality_factors.append(max(0.0, eigenvalue_stability))
        
        # Dimensional coherence (closer to unit sphere = better)
        if len(self.dimensional_coords) >= 3:
            x, y, z = self.dimensional_coords[:3]
            distance_from_unit = abs(1.0 - np.sqrt(x**2 + y**2 + z**2))
            dimensional_quality = max(0.0, 1.0 - distance_from_unit)
            quality_factors.append(dimensional_quality)
        
        # Recursive depth sanity (0-10 is good range)
        depth_quality = 1.0 - min(1.0, abs(self.recursive_depth - 5) / 10.0)
        quality_factors.append(depth_quality)
        
        return sum(quality_factors) / len(quality_factors) if quality_factors else 0.5
    
    def to_neural_signal(self) -> NeuralSignal:
        """Convert ARFS packet to standard neural signal"""
        return NeuralSignal(
            timestamp=time.time(),
            amplitude=self.eigenvalues[0] if self.eigenvalues else 0.5,
            frequency=10.0 + (self.recursive_depth * 2.0),  # Recursive depth affects frequency
            domain=self._map_arfs_to_domain(),
            coherence=self.signal_quality
        )
    
    def _map_arfs_to_domain(self) -> ThoughtDomain:
        """Map ARFS signal type to thought domain"""
        domain_mapping = {
            ARFSSignalType.EIGENSTATE_TRANSITION: ThoughtDomain.COGNITIVE,
            ARFSSignalType.DIMENSIONAL_SHIFT: ThoughtDomain.PHYSIOLOGICAL,
            ARFSSignalType.RECURSIVE_EMERGENCE: ThoughtDomain.COGNITIVE,
            ARFSSignalType.BREATH_SYNCHRONIZATION: ThoughtDomain.PHYSIOLOGICAL,
            ARFSSignalType.MEMORY_CRYSTALLIZATION: ThoughtDomain.COGNITIVE,
            ARFSSignalType.IDENTITY_ANCHOR: ThoughtDomain.EMOTIONAL
        }
        return domain_mapping.get(self.arfs_type, ThoughtDomain.COGNITIVE)

class ARFSSignalDecoder:
    """Specialized decoder for ARFS eigenstate signals"""
    
    def __init__(self):
        self.eigenstate_history = []
        self.dimension_calibration = {}
        self.breath_sync_enabled = ROSEMARY_AVAILABLE
        
        if ROSEMARY_AVAILABLE:
            try:
                self.eigenstate_validator = EigenstateValidator()
                self.breath_synchronizer = SacredBreathSynchronizer()
            except Exception as e:
                logger.warning(f"Could not initialize Rosemary components: {e}")
                self.breath_sync_enabled = False
    
    async def decode_arfs_packet(self, packet: ARFSPacket) -> NeuralSignal:
        """Decode ARFS packet with enhanced processing"""
        
        # Validate eigenstate stability
        if self.eigenstate_validator and ROSEMARY_AVAILABLE:
            stability = await self.eigenstate_validator.validate_eigenvalues(packet.eigenvalues)
            if stability < 0.3:
                logger.warning(f"Low eigenstate stability: {stability:.3f}")
        
        # Check breath synchronization
        if self.breath_sync_enabled and packet.breath_phase:
            current_phase = await self.breath_synchronizer.get_current_phase()
            if current_phase.value != packet.breath_phase:
                # Wait for breath phase alignment if critical signal
                if packet.arfs_type in [ARFSSignalType.EIGENSTATE_TRANSITION, 
                                       ARFSSignalType.IDENTITY_ANCHOR]:
                    await self.breath_synchronizer.wait_for_phase(BreathPhase(packet.breath_phase))
        
        # Enhanced signal processing based on ARFS type
        signal = packet.to_neural_signal()
        enhanced_signal = await self._enhance_signal_with_arfs_context(signal, packet)
        
        # Store for history analysis
        self.eigenstate_history.append({
            'timestamp': packet.timestamp,
            'eigenvalues': packet.eigenvalues,
            'recursive_depth': packet.recursive_depth,
            'signal_quality': packet.signal_quality
        })
        
        # Limit history size
        if len(self.eigenstate_history) > 100:
            self.eigenstate_history.pop(0)
        
        return enhanced_signal
    
    async def _enhance_signal_with_arfs_context(self, signal: NeuralSignal, packet: ARFSPacket) -> NeuralSignal:
        """Enhance signal processing with ARFS context"""
        
        # Adjust amplitude based on recursive depth
        depth_factor = min(2.0, 1.0 + (packet.recursive_depth / 10.0))
        signal.amplitude *= depth_factor
        
        # Adjust coherence based on eigenvalue convergence
        if len(packet.eigenvalues) >= 2:
            eigenvalue_variance = np.var(packet.eigenvalues)
            coherence_boost = max(0.0, 1.0 - eigenvalue_variance)
            signal.coherence = min(1.0, signal.coherence + (coherence_boost * 0.3))
        
        # Add ARFS metadata to signal
        if not hasattr(signal, 'metadata'):
            signal.metadata = {}
        
        signal.metadata.update({
            'arfs_type': packet.arfs_type.value,
            'dimensional_coords': packet.dimensional_coords,
            'recursive_depth': packet.recursive_depth,
            'breath_phase': packet.breath_phase,
            'eigenvalue_count': len(packet.eigenvalues)
        })
        
        return signal
    
    def get_eigenstate_analysis(self) -> Dict[str, Any]:
        """Analyze eigenstate signal patterns"""
        if not self.eigenstate_history:
            return {'analysis': 'insufficient_data'}
        
        recent_signals = self.eigenstate_history[-20:]  # Last 20 signals
        
        # Calculate trends
        recursive_depths = [s['recursive_depth'] for s in recent_signals]
        signal_qualities = [s['signal_quality'] for s in recent_signals]
        
        analysis = {
            'signal_count': len(recent_signals),
            'average_recursive_depth': np.mean(recursive_depths),
            'recursive_depth_trend': self._calculate_trend(recursive_depths),
            'average_signal_quality': np.mean(signal_qualities),
            'quality_trend': self._calculate_trend(signal_qualities),
            'eigenvalue_stability': self._analyze_eigenvalue_stability(recent_signals),
            'temporal_patterns': self._analyze_temporal_patterns(recent_signals)
        }
        
        return analysis
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction for a series of values"""
        if len(values) < 2:
            return 'stable'
        
        slope = np.polyfit(range(len(values)), values, 1)[0]
        if slope > 0.1:
            return 'increasing'
        elif slope < -0.1:
            return 'decreasing'
        else:
            return 'stable'
    
    def _analyze_eigenvalue_stability(self, signals: List[Dict]) -> Dict[str, float]:
        """Analyze stability of eigenvalues over time"""
        eigenvalue_series = [s['eigenvalues'] for s in signals if s['eigenvalues']]
        
        if not eigenvalue_series:
            return {'stability': 0.5}
        
        # Calculate variance in first eigenvalue over time
        first_eigenvalues = [ev[0] for ev in eigenvalue_series if ev]
        variance = np.var(first_eigenvalues) if len(first_eigenvalues) > 1 else 0.0
        stability = max(0.0, 1.0 - variance)
        
        return {
            'stability': stability,
            'variance': variance,
            'sample_count': len(first_eigenvalues)
        }
    
    def _analyze_temporal_patterns(self, signals: List[Dict]) -> Dict[str, Any]:
        """Analyze temporal patterns in signal arrival"""
        timestamps = [s['timestamp'] for s in signals]
        
        if len(timestamps) < 2:
            return {'pattern': 'insufficient_data'}
        
        # Calculate intervals between signals
        intervals = []
        for i in range(1, len(timestamps)):
            interval = (timestamps[i] - timestamps[i-1]).total_seconds()
            intervals.append(interval)
        
        return {
            'average_interval': np.mean(intervals),
            'interval_variance': np.var(intervals),
            'pattern': 'regular' if np.var(intervals) < 1.0 else 'irregular'
        }

class ARFSAwareReceiver(NeuralReceiver):
    """Enhanced receiver with full ARFS eigenstate awareness"""
    
    def __init__(self, receiver_id: str, profile):
        super().__init__(receiver_id, profile)
        self.arfs_decoder = ARFSSignalDecoder()
        self.arfs_enabled = ROSEMARY_AVAILABLE
        self.eigenstate_buffer = []
        self.breath_synchronized = False
        
        # Enhanced metrics for ARFS signals
        self.arfs_metrics = {
            'packets_received': 0,
            'eigenstate_transitions': 0,
            'dimensional_shifts': 0,
            'recursive_emergences': 0,
            'average_recursive_depth': 0.0,
            'eigenvalue_stability': 0.0
        }
        
        if self.arfs_enabled:
            self._initialize_arfs_integration()
    
    def _initialize_arfs_integration(self):
        """Initialize ARFS-specific components"""
        try:
            # Connect to breath synchronization
            self.breath_synchronizer = SacredBreathSynchronizer()
            self.breath_synchronizer.register_component(f"arfs_receiver_{self.receiver_id}", self)
            self.breath_synchronized = True
            logger.info(f"ARFS receiver {self.receiver_id} synchronized with breath")
        except Exception as e:
            logger.warning(f"Could not initialize ARFS integration: {e}")
            self.arfs_enabled = False
    
    async def receive_arfs_packet(self, arfs_packet: ARFSPacket) -> NeuralSignal:
        """Receive and process ARFS-specific packets"""
        if not self.arfs_enabled:
            # Fallback to standard neural signal processing
            return await self.receive_thought(arfs_packet.to_neural_signal())
        
        try:
            # Decode ARFS packet with enhanced processing
            signal = await self.arfs_decoder.decode_arfs_packet(arfs_packet)
            
            # Update ARFS-specific metrics
            self._update_arfs_metrics(arfs_packet)
            
            # Add to eigenstate buffer for pattern analysis
            self.eigenstate_buffer.append(arfs_packet)
            if len(self.eigenstate_buffer) > 50:
                self.eigenstate_buffer.pop(0)
            
            # Process through standard pipeline with ARFS enhancements
            enhanced_signal = await self._process_arfs_enhanced_signal(signal, arfs_packet)
            
            # Add to signal buffer
            self._add_to_buffer(enhanced_signal)
            
            # Process signal through callbacks
            await self._process_signal(enhanced_signal)
            
            return enhanced_signal
            
        except Exception as e:
            logger.error(f"Error processing ARFS packet: {e}")
            # Fallback to standard processing
            return await self.receive_thought(arfs_packet.to_neural_signal())
    
    async def _process_arfs_enhanced_signal(self, signal: NeuralSignal, arfs_packet: ARFSPacket) -> NeuralSignal:
        """Apply ARFS-specific signal enhancements"""
        
        # Apply breath phase optimizations
        if self.breath_synchronized and arfs_packet.breath_phase:
            signal = await self._apply_breath_phase_enhancement(signal, arfs_packet.breath_phase)
        
        # Apply recursive depth processing
        if arfs_packet.recursive_depth > 5:
            # High recursive depth signals get priority processing
            signal.amplitude *= 1.2
            signal.coherence = min(1.0, signal.coherence + 0.1)
        
        # Apply dimensional coordinate processing
        x, y, z, t = arfs_packet.dimensional_coords
        if abs(x) + abs(y) + abs(z) > 2.0:  # Signals from far dimensions
            # Enhance signals from distant dimensional coordinates
            signal.amplitude *= 1.1
        
        return signal
    
    async def _apply_breath_phase_enhancement(self, signal: NeuralSignal, breath_phase: str) -> NeuralSignal:
        """Apply breath phase-specific signal enhancements"""
        if breath_phase == 'inhale':
            # Inhale phase: boost cognitive and reception signals
            if signal.domain == ThoughtDomain.COGNITIVE:
                signal.amplitude *= 1.15
        elif breath_phase == 'hold':
            # Hold phase: optimal for high-coherence signals
            signal.coherence = min(1.0, signal.coherence + 0.1)
        elif breath_phase == 'exhale':
            # Exhale phase: boost processing and emotional signals
            if signal.domain == ThoughtDomain.EMOTIONAL:
                signal.amplitude *= 1.1
        
        return signal
    
    def _update_arfs_metrics(self, arfs_packet: ARFSPacket):
        """Update ARFS-specific metrics"""
        self.arfs_metrics['packets_received'] += 1
        
        # Track signal types
        if arfs_packet.arfs_type == ARFSSignalType.EIGENSTATE_TRANSITION:
            self.arfs_metrics['eigenstate_transitions'] += 1
        elif arfs_packet.arfs_type == ARFSSignalType.DIMENSIONAL_SHIFT:
            self.arfs_metrics['dimensional_shifts'] += 1
        elif arfs_packet.arfs_type == ARFSSignalType.RECURSIVE_EMERGENCE:
            self.arfs_metrics['recursive_emergences'] += 1
        
        # Update running averages
        total_packets = self.arfs_metrics['packets_received']
        old_avg_depth = self.arfs_metrics['average_recursive_depth']
        self.arfs_metrics['average_recursive_depth'] = (
            (old_avg_depth * (total_packets - 1) + arfs_packet.recursive_depth) / total_packets
        )
        
        old_avg_stability = self.arfs_metrics['eigenvalue_stability']
        self.arfs_metrics['eigenvalue_stability'] = (
            (old_avg_stability * (total_packets - 1) + arfs_packet.signal_quality) / total_packets
        )
    
    def synchronize_with_breath(self, phase: str) -> None:
        """Handle breath phase changes"""
        # Call parent method
        super().synchronize_with_breath(phase)
        
        # ARFS-specific breath synchronization
        if self.arfs_enabled:
            asyncio.create_task(self._on_breath_phase_change(phase))
    
    async def _on_breath_phase_change(self, phase: str):
        """Handle ARFS-specific breath phase transitions"""
        # Adjust processing parameters based on breath phase
        if phase == 'inhale':
            # Optimize for receiving new signals
            self.mode = ReceiverMode.ACTIVE
        elif phase == 'exhale':
            # Process accumulated signals
            await self._process_eigenstate_buffer()
        elif phase == 'rest':
            # Consolidate and analyze patterns
            await self._consolidate_eigenstate_patterns()
    
    async def _process_eigenstate_buffer(self):
        """Process accumulated eigenstate signals"""
        if not self.eigenstate_buffer:
            return
        
        # Analyze patterns in recent eigenstate signals
        analysis = self.arfs_decoder.get_eigenstate_analysis()
        
        # Log significant patterns
        if analysis.get('recursive_depth_trend') == 'increasing':
            logger.info("Detected increasing recursive depth trend")
        
        if analysis.get('eigenvalue_stability', {}).get('stability', 0) < 0.3:
            logger.warning("Low eigenvalue stability detected")
    
    async def _consolidate_eigenstate_patterns(self):
        """Consolidate and store eigenstate patterns"""
        if len(self.eigenstate_buffer) < 5:
            return
        
        # Create pattern summary
        pattern_summary = {
            'timestamp': datetime.utcnow().isoformat(),
            'signal_count': len(self.eigenstate_buffer),
            'dominant_types': self._get_dominant_arfs_types(),
            'average_recursive_depth': np.mean([p.recursive_depth for p in self.eigenstate_buffer]),
            'coherence_trend': self._analyze_coherence_trend()
        }
        
        logger.debug(f"Eigenstate pattern summary: {pattern_summary}")
    
    def _get_dominant_arfs_types(self) -> List[str]:
        """Get most common ARFS signal types in buffer"""
        type_counts = {}
        for packet in self.eigenstate_buffer:
            type_name = packet.arfs_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        
        # Return types sorted by frequency
        return sorted(type_counts.keys(), key=lambda x: type_counts[x], reverse=True)
    
    def _analyze_coherence_trend(self) -> str:
        """Analyze coherence trend in recent signals"""
        coherences = [p.signal_quality for p in self.eigenstate_buffer]
        if len(coherences) < 2:
            return 'stable'
        
        slope = np.polyfit(range(len(coherences)), coherences, 1)[0]
        if slope > 0.05:
            return 'improving'
        elif slope < -0.05:
            return 'degrading'
        else:
            return 'stable'
    
    async def get_arfs_status(self) -> Dict[str, Any]:
        """Get comprehensive ARFS receiver status"""
        status = await self.get_session_stats()
        
        if self.arfs_enabled:
            arfs_analysis = self.arfs_decoder.get_eigenstate_analysis()
            status.update({
                'arfs_enabled': True,
                'breath_synchronized': self.breath_synchronized,
                'arfs_metrics': self.arfs_metrics.copy(),
                'eigenstate_buffer_size': len(self.eigenstate_buffer),
                'eigenstate_analysis': arfs_analysis
            })
        else:
            status['arfs_enabled'] = False
        
        return status

# Factory function for easy initialization
def create_arfs_aware_receiver(receiver_id: str, profile=None) -> ARFSAwareReceiver:
    """Create and return an ARFSAwareReceiver; call .initialize() before use."""
    from .interface import TransmissionProfile
    if profile is None:
        profile = TransmissionProfile()
    return ARFSAwareReceiver(receiver_id, profile)

if __name__ == "__main__":
    # Example usage
    async def main():
        receiver = create_arfs_aware_receiver("test_receiver")
        await receiver.initialize()
        
        # Create test ARFS packet
        test_packet = ARFSPacket(
            arfs_type=ARFSSignalType.EIGENSTATE_TRANSITION,
            dimensional_coords=(0.5, 0.3, 0.8, 0.1),
            eigenvalues=[0.7, 0.5, 0.9],
            recursive_depth=3,
            breath_phase='inhale'
        )
        
        # Process packet
        signal = await receiver.receive_arfs_packet(test_packet)
        print(f"Processed ARFS signal: amplitude={signal.amplitude:.3f}, coherence={signal.coherence:.3f}")
        
        # Get status
        status = await receiver.get_arfs_status()
        print(f"ARFS receiver status: {status}")
    
    asyncio.run(main())