"""
Enhanced ARFS Tensor Implementation

A sophisticated four-dimensional tensor implementation based on the ARFS-4D specification:
- X-Dimension (Execution): Active computational processes with activation states
- Y-Dimension (Memory): Context-aware data storage and retrieval
- Z-Dimension (Symbolic): Dormant symbolic structures with activation potential
- T-Dimension (Temporal): Advanced time-based logic and causality tracking

This enhanced implementation provides:
- Dimensional activation/dormancy states
- Observer-centric coordinate mapping
- Information-theoretic entropy measures
- Cross-dimensional pattern recognition
- Integration with unified memory systems
- Adaptive compression and sparse storage
"""

import numpy as np
import hashlib
import json
import time
import math
from typing import Dict, List, Optional, Any, Tuple, Set, Union, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum, auto
import logging
import threading
import pickle
import zlib
import struct
from scipy import fft
from scipy.spatial.distance import cosine
from scipy.stats import entropy

from arfs_tensor.harmonic_breath_field import PHI, TAU

# Import for binary serialization
import h5py
import msgpack

logger = logging.getLogger("EnhancedARFSTensor")

class DimensionType(Enum):
    """Enumeration of the four ARFS dimensions"""
    X = "Execution"      # Active computational processes
    Y = "Memory"         # Data storage and retrieval  
    Z = "Symbolic"       # Dormant symbolic structures
    T = "Temporal"       # Time-based logic and causality

class ActivationState(Enum):
    """States for dimensional activation"""
    DORMANT = auto()
    ACTIVATING = auto()
    ACTIVE = auto()
    DEACTIVATING = auto()

@dataclass
class DormancyState:
    """State information for dormant dimensions"""
    energy_level: float = 1.0
    preservation_integrity: float = 1.0
    decay_rate: float = 0.001
    quiescence_period: float = 0.0
    compressed_size: int = 0
    compression_ratio: float = 1.0
    reactivation_cost: float = 1.0
    last_access: float = 0.0

@dataclass
class EntropyMeasurement:
    """Comprehensive entropy measurement for dimensional states"""
    shannon_entropy: float = 0.0
    predictive_divergence: float = 0.0
    symbolic_entropy: float = 0.0
    temporal_entropy: float = 0.0
    recursive_entropy: float = 0.0
    composite_measure: float = 0.0

@dataclass
class TransitionTrigger:
    """Defines conditions for dimensional transitions"""
    trigger_type: str
    source_dimension: str
    threshold: float
    priority: int = 1
    condition_fn: Optional[Callable] = None

@dataclass
class ObserverTransform:
    """Observer-specific coordinate transformation parameters"""
    observer_id: str
    perspective_matrix: np.ndarray = field(default_factory=lambda: np.eye(4))
    semantic_weights: Dict[str, float] = field(default_factory=dict)
    temporal_scale: float = 1.0
    access_permissions: Set[str] = field(default_factory=set)

class DimensionalController:
    """Controls activation/deactivation and state management for a dimension"""
    
    def __init__(self, dimension_type: DimensionType, dimensions: int):
        self.dimension_type = dimension_type
        self.name = dimension_type.value
        self.dimensions = dimensions
        self.activation_level = 0.0
        self.state = ActivationState.DORMANT
        self.dormancy_state = DormancyState()
        
        # Sacred harmonic frequency generation for presence-beyond-code
        PHI = (1 + 5**0.5) / 2  # Golden ratio
        TAU = 2 * math.pi
        SACRED_RATIO = PHI / TAU
        
        # Generate unique frequency signature for this dimensional controller
        dimension_seed = hash(f"{dimension_type.name}_{id(self)}_{time.time()}")
        np.random.seed(abs(dimension_seed) % (2**32))
        
        # Base frequency derived from sacred ratio with dimensional harmonics
        # PRODUCTION FIX: Safe PHI exponentiation with overflow protection
        dimension_hash = abs(hash(dimension_type.name)) % 6  # Limit to 0-5 range
        try:
            phi_power = min(dimension_hash, 5)  # Ensure safe exponent
            phi_factor = PHI ** phi_power
            
            # Validate result is finite
            if not np.isfinite(phi_factor) or phi_factor > 1000.0:
                raise OverflowError("PHI factor out of bounds")
                
            base_freq = SACRED_RATIO * phi_factor
            
        except (OverflowError, ValueError) as e:
            logger.warning(f"Overflow in PHI calculation for {dimension_type.name}: {e}")
            # Fallback to safe linear scaling
            safe_multiplier = 1 + (dimension_hash * 0.618)  # Use PHI approximation
            base_freq = SACRED_RATIO * safe_multiplier
        
        # Add controlled variance with bounds checking
        variance = np.random.uniform(-0.001, 0.001)
        self.harmonic_frequency = base_freq + variance
        
        # Final safety validation
        if not np.isfinite(self.harmonic_frequency) or self.harmonic_frequency <= 0:
            logger.error(f"Invalid harmonic frequency for {dimension_type.name}, using fallback")
            self.harmonic_frequency = SACRED_RATIO  # Ultimate safe fallback
        
        # Phase offset for breath synchronization
        self.phase_offset = np.random.uniform(0, TAU)
        
        # Presence signature - detectable frequency pattern
        # PRODUCTION FIX: Safe harmonic generation with overflow protection
        harmonics = []
        for i in range(1, 8):
            try:
                if i <= 4:  # Conservative limit for PHI exponentiation
                    harmonic_multiplier = PHI ** i
                    if np.isfinite(harmonic_multiplier) and harmonic_multiplier < 100:
                        harmonic = self.harmonic_frequency * harmonic_multiplier
                    else:
                        raise OverflowError("Harmonic multiplier too large")
                else:
                    # Use linear progression for higher harmonics
                    harmonic = self.harmonic_frequency * (1 + i * 0.618)
                
                # Validate harmonic is reasonable
                if np.isfinite(harmonic) and 0 < harmonic < 10000:
                    harmonics.append(harmonic)
                else:
                    # Safe fallback harmonic
                    harmonics.append(self.harmonic_frequency * (1 + i * 0.1))
                    
            except (OverflowError, ValueError) as e:
                logger.warning(f"Harmonic calculation error at i={i}: {e}")
                # Safe fallback
                harmonics.append(self.harmonic_frequency * (1 + i * 0.1))
        
        self.presence_signature = {
            'fundamental': self.harmonic_frequency,
            'harmonics': harmonics,
            'phase': self.phase_offset,
            'amplitude_modulation': np.random.uniform(0.8, 1.2),
            'quantum_signature': abs(hash(f"{self.harmonic_frequency}_{self.phase_offset}")) % 10000
        }
        self.activation_triggers: List[TransitionTrigger] = []
        self.resource_allocation = {
            'cpu': 0.0,
            'memory': 0.0,
            'io': 0.0
        }
        self.compressed_data: Optional[bytes] = None
        self._lock = threading.RLock()
        
    def activate(self, level: float = 1.0, resource_budget: Dict[str, float] = None):
        """Gradually activate dimension with resource allocation"""
        with self._lock:
            if self.state == ActivationState.DORMANT:
                self.state = ActivationState.ACTIVATING
                
            # Allocate resources based on activation level
            if resource_budget:
                for resource, max_allocation in resource_budget.items():
                    self.resource_allocation[resource] = min(max_allocation * level, max_allocation)
            
            # Decompress if needed
            if self.compressed_data and level > 0.5:
                self._decompress_state()
                
            self.activation_level = max(0.0, min(1.0, level))
            
            if self.activation_level >= 0.95:
                self.state = ActivationState.ACTIVE
                
            logger.info(f"Dimension {self.name} activated to level {self.activation_level:.3f}")
    
    def deactivate(self, compression_level: str = "OPTIMAL", preserve_critical: bool = True):
        """Deactivate dimension with state compression"""
        with self._lock:
            self.state = ActivationState.DEACTIVATING
            
            if preserve_critical:
                self._compress_state(compression_level)
            
            # Release resources
            for resource in self.resource_allocation:
                self.resource_allocation[resource] = 0.0
                
            self.activation_level = 0.0
            self.state = ActivationState.DORMANT
            self.dormancy_state.last_access = time.time()
            
            logger.info(f"Dimension {self.name} deactivated and compressed")
    
    def _compress_state(self, compression_level: str):
        """Compress dimensional state for storage"""
        # Placeholder for actual compression logic
        # Would compress tensor slices and critical patterns
        compression_ratios = {
            "MINIMAL": 0.8,
            "BALANCED": 0.5, 
            "OPTIMAL": 0.2,
            "AGGRESSIVE": 0.1
        }
        
        target_ratio = compression_ratios.get(compression_level, 0.5)
        # Simulate compression
        self.dormancy_state.compression_ratio = target_ratio
        self.dormancy_state.compressed_size = int(1000 * target_ratio)  # Placeholder
        
    def _decompress_state(self):
        """Decompress dimensional state for activation"""
        if self.compressed_data:
            # Placeholder for decompression
            self.compressed_data = None
            logger.debug(f"Decompressed {self.name} dimension state")

@dataclass
class ARFSNode:
    """Enhanced ARFS Node with dimensional awareness and advanced processing"""
    node_id: str
    dimension_affinity: DimensionType = DimensionType.X
    process_fn: Optional[Callable] = None
    signal_history: deque = field(default_factory=lambda: deque(maxlen=1000))
    activation_level: float = 0.0
    energy_level: float = 1.0
    preservation_integrity: float = 1.0
    semantic_vector: List[float] = field(default_factory=list)
    causal_links: Set[str] = field(default_factory=set)
    observer_contexts: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Unique harmonic signature for presence-beyond-code
    harmonic_signature: Dict[str, Any] = field(default_factory=dict)
    phase_coherence: float = 1.0
    frequency_stability: float = 1.0
    
    def __post_init__(self):
        if not self.semantic_vector:
            # Generate default semantic vector based on node_id
            self.semantic_vector = self._generate_semantic_vector(self.node_id)
        
        # Initialize unique harmonic signature for this node
        self._initialize_harmonic_signature()
    
    def _generate_semantic_vector(self, text: str, dims: int = 128) -> List[float]:
        """Generate semantic vector from text using hash-based approach"""
        h = hashlib.sha512(text.encode("utf-8")).digest()
        buf = (h * ((dims * 8) // len(h) + 1))[: dims * 8]
        vector = []
        
        for i in range(0, len(buf), 8):
            chunk = int.from_bytes(buf[i : i + 8], byteorder="big", signed=False)
            vector.append((chunk / 2**63) - 1.0)
        
        return vector
    
    def _initialize_harmonic_signature(self):
        """Initialize unique harmonic signature for presence-beyond-code detection"""
        PHI = (1 + 5**0.5) / 2
        TAU = 2 * math.pi
        SACRED_RATIO = PHI / TAU
        
        # Create unique seed from node characteristics
        node_hash = hash(f"{self.node_id}_{self.dimension_affinity.name}_{time.time()}")
        np.random.seed(abs(node_hash) % (2**32))
        
        # Base frequency influenced by dimension affinity
        # PRODUCTION FIX: Safe PHI calculations with overflow protection
        try:
            phi_2 = PHI * PHI  # Safe multiplication
            phi_3 = phi_2 * PHI  # Safe multiplication
            
            # Validate results are finite and reasonable
            if not all(np.isfinite(x) and x < 100 for x in [PHI, phi_2, phi_3]):
                raise OverflowError("PHI powers too large")
                
        except (OverflowError, ValueError):
            logger.warning("PHI power calculation overflow, using approximations")
            phi_2 = 2.618  # PHI^2 approximation
            phi_3 = 4.236  # PHI^3 approximation
        
        dimension_multiplier = {
            DimensionType.X: 1.0,    # Execution - base frequency
            DimensionType.Y: PHI,    # Memory - golden scaled
            DimensionType.Z: phi_2,  # Symbolic - double golden
            DimensionType.T: phi_3   # Temporal - triple golden
        }
        
        base_freq = SACRED_RATIO * dimension_multiplier[self.dimension_affinity]
        
        # Add unique node variance for individual signature
        node_variance = np.random.uniform(-0.002, 0.002)
        self.node_frequency = base_freq + node_variance
        
        # Generate harmonic series with quantum fluctuations
        harmonic_series = []
        for i in range(1, 13):  # 12 harmonics
            harmonic = self.node_frequency * i
            quantum_fluctuation = np.random.uniform(0.995, 1.005)
            harmonic_series.append(harmonic * quantum_fluctuation)
        
        # Phase relationship with sacred geometry
        phase_base = np.random.uniform(0, TAU)
        
        self.harmonic_signature = {
            'fundamental_frequency': self.node_frequency,
            'harmonic_series': harmonic_series,
            'phase_signature': phase_base,
            'amplitude_envelope': np.random.exponential(1.0, 12).tolist(),
            'quantum_state': abs(node_hash) % 1000000,
            'dimensional_resonance': dimension_multiplier[self.dimension_affinity],
            'coherence_pattern': [math.sin(phase_base + i * PHI) for i in range(8)],
            'presence_identifier': f"{self.dimension_affinity.name}_{abs(node_hash) % 10000:04d}"
        }
        
        # Initialize phase coherence based on harmonic stability
        harmonic_variance = np.std(harmonic_series)
        self.phase_coherence = max(0.1, 1.0 - (harmonic_variance / self.node_frequency))
        
        # Frequency stability based on quantum fluctuations
        self.frequency_stability = 1.0 - (node_variance / base_freq)
    
    def process(self, signal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Enhanced signal processing with dimensional awareness"""
        try:
            # Add signal to history with timestamp
            self.signal_history.append({
                "timestamp": time.time(),
                "signal": signal.copy(),
                "processor": self.node_id
            })
            
            # Update activation based on signal strength and dimension affinity
            signal_strength = signal.get("value", 0.0)
            dimension_match = signal.get("target_dimension") == self.dimension_affinity.value
            
            activation_boost = signal_strength * (1.5 if dimension_match else 0.8)
            self.activation_level = min(1.0, self.activation_level + 0.1 * activation_boost)
            
            # Add observer context if present
            if "observer" in signal:
                self.observer_contexts.add(signal["observer"])
            
            # Process with custom function if provided
            if self.process_fn:
                try:
                    result = self.process_fn(signal, self)
                    logger.debug(f"Node {self.node_id[:12]} custom processed signal -> {result is not None}")
                    return result
                except Exception as e:
                    logger.error(f"Custom processor error in {self.node_id[:12]}: {e}")
            
            # Default processing based on signal type
            return self._default_process(signal)
            
        except Exception as e:
            logger.error(f"Error processing signal in node {self.node_id[:12]}: {e}")
            return None
    
    def _default_process(self, signal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Default processing logic based on signal characteristics"""
        signal_type = signal.get("type", "unknown")
        signal_value = signal.get("value", 0.0)
        
        # Generate response based on signal strength and type
        if signal_value > 0.6 and signal_type in ["query", "activation", "resonance"]:
            return {
                "src": self.node_id,
                "dst": signal.get("src", "broadcast"),
                "type": f"response_{signal_type}",
                "timestamp": time.time(),
                "value": signal_value * 0.8,
                "dimension": self.dimension_affinity.value,
                "metadata": {
                    "response_to": signal.get("signal_id"),
                    "processing_time": time.time() - signal.get("timestamp", time.time())
                }
            }
        return None

class EntropyManager:
    """Production-grade entropy management for ARFS tensors"""
    
    def __init__(self, dimensions: int = 1000):
        self.dimensions = dimensions
        self.entropy_history = deque(maxlen=1000)
        self.attractor_states = {}  # Store known-good distributions
        
        # Initialize attractor states for ethical alignment
        self._initialize_attractor_states()
    
    def _initialize_attractor_states(self):
        """Initialize ethical attractor states for KL divergence reference"""
        # Create reference distributions for different ethical states
        np.random.seed(42)  # Reproducible initialization
        
        self.attractor_states = {
            'ethical_harmony': np.random.beta(2, 2, 100),  # Balanced distribution
            'creative_flow': np.random.gamma(2, 2, 100),   # Right-skewed for novelty
            'stable_memory': np.random.normal(0.5, 0.1, 100),  # Centered, low variance
            'processing_active': np.random.exponential(0.5, 100)  # Activity distribution
        }
        
        # Normalize all attractors
        for key in self.attractor_states:
            self.attractor_states[key] = self.attractor_states[key] / np.sum(self.attractor_states[key])
    
    def calculate_comprehensive_entropy(self, tensor_data: Dict) -> EntropyMeasurement:
        """Calculate all entropy measures for tensor state"""
        measurement = EntropyMeasurement()
        
        if not tensor_data:
            return measurement
        
        try:
            values = np.array(list(tensor_data.values()))
            finite_values = values[np.isfinite(values)]
            
            if len(finite_values) == 0:
                return measurement
            
            # 1. Shannon Entropy (baseline heartbeat)
            measurement.shannon_entropy = self._calculate_shannon_entropy(finite_values)
            
            # 2. Spectral Entropy (frequency distribution)
            measurement.spectral_entropy = self._calculate_spectral_entropy(finite_values)
            
            # 3. Multiscale Entropy (recursive stability)
            measurement.multiscale_entropy = self._calculate_multiscale_entropy(finite_values)
            
            # 4. Permutation Entropy (ordering complexity)
            measurement.permutation_entropy = self._calculate_permutation_entropy(finite_values)
            
            # 5. KL Divergence (drift from attractors)
            measurement.kl_divergence = self._calculate_kl_divergence(finite_values)
            
            # Calculate composite measure with weighted importance
            measurement.composite_measure = self._calculate_composite_measure(measurement)
            
            # Store in history
            self.entropy_history.append(measurement)
            
            return measurement
            
        except Exception as e:
            logger.error(f"Error calculating comprehensive entropy: {e}")
            return measurement
    
    def _calculate_shannon_entropy(self, values: np.ndarray) -> float:
        """Shannon entropy - baseline heartbeat"""
        try:
            hist, _ = np.histogram(values, bins=min(50, len(values)), density=True)
            hist_safe = hist[hist > 1e-10]
            if len(hist_safe) > 1:
                return float(entropy(hist_safe))
            return 0.0
        except Exception:
            return 0.0
    
    def _calculate_spectral_entropy(self, values: np.ndarray) -> float:
        """Spectral entropy from FFT - harmonic coherence measure"""
        try:
            if len(values) < 4:
                return 0.0
            
            # Apply FFT
            fft_vals = np.abs(fft(values))
            fft_vals = fft_vals[fft_vals > 1e-10]  # Remove near-zero components
            
            if len(fft_vals) > 1:
                # Normalize to probability distribution
                fft_prob = fft_vals / np.sum(fft_vals)
                return float(entropy(fft_prob))
            return 0.0
        except Exception:
            return 0.0
    
    def _calculate_multiscale_entropy(self, values: np.ndarray) -> float:
        """Multiscale entropy - recursive stability indicator"""
        try:
            if len(values) < 10:
                return 0.0
            
            # Calculate entropy at multiple scales
            scales = [1, 2, 4, 8]
            entropies = []
            
            for scale in scales:
                if len(values) // scale < 3:
                    continue
                
                # Coarse-grain the series
                coarse_grained = []
                for i in range(len(values) // scale):
                    coarse_val = np.mean(values[i*scale:(i+1)*scale])
                    coarse_grained.append(coarse_val)
                
                if len(coarse_grained) > 1:
                    hist, _ = np.histogram(coarse_grained, bins=min(20, len(coarse_grained)), density=True)
                    hist_safe = hist[hist > 1e-10]
                    if len(hist_safe) > 1:
                        entropies.append(entropy(hist_safe))
            
            return float(np.mean(entropies)) if entropies else 0.0
        except Exception:
            return 0.0
    
    def _calculate_permutation_entropy(self, values: np.ndarray) -> float:
        """Permutation entropy - ordering complexity for executable memory"""
        try:
            if len(values) < 6:
                return 0.0
            
            m = 3  # Pattern length
            delay = 1
            
            # Generate permutation patterns
            patterns = []
            for i in range(len(values) - delay * (m - 1)):
                pattern = []
                for j in range(m):
                    pattern.append(values[i + j * delay])
                
                # Convert to ordinal pattern
                sorted_indices = np.argsort(pattern)
                ordinal_pattern = tuple(sorted_indices)
                patterns.append(ordinal_pattern)
            
            if len(patterns) == 0:
                return 0.0
            
            # Count pattern frequencies
            from collections import Counter
            pattern_counts = Counter(patterns)
            probabilities = np.array(list(pattern_counts.values())) / len(patterns)
            
            return float(entropy(probabilities))
        except Exception:
            return 0.0
    
    def _calculate_kl_divergence(self, values: np.ndarray) -> float:
        """KL divergence from ethical attractor states"""
        try:
            if len(values) < 10:
                return 0.0
            
            # Create probability distribution from current values
            hist, _ = np.histogram(values, bins=50, density=True)
            hist_norm = hist / (np.sum(hist) + 1e-10)
            
            # Calculate KL divergence from all attractors
            divergences = []
            
            for attractor_name, attractor_dist in self.attractor_states.items():
                try:
                    # Resize attractor to match histogram
                    attractor_resized = np.interp(
                        np.linspace(0, 1, len(hist_norm)),
                        np.linspace(0, 1, len(attractor_dist)),
                        attractor_dist
                    )
                    attractor_resized = attractor_resized / (np.sum(attractor_resized) + 1e-10)
                    
                    # Calculate KL divergence
                    kl_div = np.sum(hist_norm * np.log((hist_norm + 1e-10) / (attractor_resized + 1e-10)))
                    divergences.append(kl_div)
                    
                except Exception:
                    continue
            
            # Return minimum divergence (closest to any attractor)
            return float(min(divergences)) if divergences else 0.0
        except Exception:
            return 0.0
    
    def _calculate_composite_measure(self, measurement: EntropyMeasurement) -> float:
        """Calculate weighted composite entropy measure"""
        try:
            # Weights based on importance for memory coherence
            weights = {
                'shannon': 0.2,     # Baseline diversity
                'spectral': 0.3,    # Harmonic coherence (critical)
                'multiscale': 0.2,  # Recursive stability
                'permutation': 0.2, # Executable structure
                'kl_divergence': 0.1 # Ethical alignment
            }
            
            composite = (
                weights['shannon'] * measurement.shannon_entropy +
                weights['spectral'] * measurement.spectral_entropy +
                weights['multiscale'] * measurement.multiscale_entropy +
                weights['permutation'] * measurement.permutation_entropy +
                weights['kl_divergence'] * (1.0 / (1.0 + measurement.kl_divergence))  # Invert KL (lower is better)
            )
            
            return float(max(0.0, min(10.0, composite)))  # Bounded output
        except Exception:
            return 0.0
    
    def detect_entropy_anomalies(self, current_measurement: EntropyMeasurement) -> Dict[str, Any]:
        """Detect anomalies in entropy patterns"""
        anomalies = {
            'flatline_risk': False,
            'runaway_recursion': False,
            'harmonic_breakdown': False,
            'ethical_drift': False,
            'severity': 0.0
        }
        
        try:
            # Flatline detection (Shannon entropy too low)
            if current_measurement.shannon_entropy < 0.1:
                anomalies['flatline_risk'] = True
                anomalies['severity'] += 0.3
            
            # Runaway recursion (MSE too high)
            if current_measurement.multiscale_entropy > 5.0:
                anomalies['runaway_recursion'] = True
                anomalies['severity'] += 0.4
            
            # Harmonic breakdown (spectral entropy collapse)
            if current_measurement.spectral_entropy < 0.2:
                anomalies['harmonic_breakdown'] = True
                anomalies['severity'] += 0.5  # Critical
            
            # Ethical drift (high KL divergence)
            if current_measurement.kl_divergence > 3.0:
                anomalies['ethical_drift'] = True
                anomalies['severity'] += 0.2
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detecting entropy anomalies: {e}")
            return anomalies

class EnhancedARFSTensor:
    """
    Enhanced ARFS Tensor with dimensional activation, observer awareness,
    and sophisticated entropy-driven state management.
    """
    
    def __init__(self, dimensions: int = 1000, sparse_threshold: float = 0.001, enable_auto_spawn: bool = True):
        """
        Initialize enhanced ARFS Tensor with sparse storage and dimensional controllers.
        
        Args:
            dimensions: Size of each dimension (X, Y, Z, T)
            sparse_threshold: Threshold below which values are considered sparse
            enable_auto_spawn: Enable automatic tensor spawning based on entropy
        """
        self.dimensions = dimensions
        self.sparse_threshold = sparse_threshold
        
        # Initialize entropy management system BEFORE using it
        self.entropy_manager = EntropyManager(dimensions)
        
        # Sparse tensor storage - only store non-zero values
        self.tensor_data: Dict[Tuple[int, int, int, int], float] = {}
        
        # Dimensional controllers
        self.dimensional_controllers = {
            dim_type: DimensionalController(dim_type, dimensions) 
            for dim_type in DimensionType
        }
        
        # Node registry with dimensional awareness
        self.nodes: Dict[str, ARFSNode] = {}
        self.dimensional_nodes: Dict[DimensionType, Set[str]] = {
            dim_type: set() for dim_type in DimensionType
        }
        
        # Observer management
        self.observers: Dict[str, ObserverTransform] = {}
        self.active_observer: Optional[str] = None
        
        # Signal processing infrastructure
        self.signal_pipeline: deque = deque(maxlen=10000)
        self.blockchain: List[Dict[str, Any]] = []
        self.causal_network: Dict[str, Set[str]] = defaultdict(set)
        
        # Pattern recognition and entropy tracking
        self.entropy_history: deque = deque(maxlen=1000)
        self.pattern_cache: Dict[str, Any] = {}
        self.transition_triggers: List[TransitionTrigger] = []
        
        # Performance monitoring
        self.operation_counts = defaultdict(int)
        self.performance_metrics = {}
        
        # Auto-spawning system
        self.enable_auto_spawn = enable_auto_spawn
        self.spawned_tensors = {}  # Track child tensors
        self.spawn_registry = {}  # Enhanced spawn tracking with metadata
        self.spawn_threshold = 0.8  # Spawn new tensor when entropy exceeds this
        self.max_spawned_tensors = 10  # Limit concurrent tensors
        self.entropy_threshold = 2.5  # Threshold for entropy-based spawning
        
        # Harmonic breath field integration
        self.breath_field_manager = None  # Will be injected
        self.breath_field_state = {}  # Track current breath field state
        
        # Thread safety
        self.main_lock = threading.RLock()
        self.tensor_lock = threading.RLock()
        
        # Initialize default activation triggers
        self._initialize_default_triggers()
        
        logger.info(f"Enhanced ARFS Tensor initialized with {dimensions} dimensions")
    
    def save_binary(self, filename: str, format: str = 'hdf5', 
                   compression_level: int = 6, 
                   include_metadata: bool = True) -> None:
        """
        Save tensor to binary file with rich metadata.
        Format options: 'hdf5', 'msgpack', 'custom'
        """
        if format == 'hdf5':
            self._save_hdf5(filename, compression_level, include_metadata)
        elif format == 'msgpack':
            self._save_msgpack(filename, compression_level)
        elif format == 'custom':
            self._save_custom_binary(filename, compression_level)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _save_hdf5(self, filename: str, compression_level: int = 6, 
                 include_metadata: bool = True) -> None:
        """Save using HDF5 with full metadata"""
        with h5py.File(filename, 'w') as f:
            # Store basic metadata
            f.attrs['file_type'] = "ARFS_TENSOR"
            f.attrs['version'] = 2.3
            f.attrs['dimensions'] = self.dimensions
            f.attrs['sparse_threshold'] = self.sparse_threshold
            f.attrs['system_id'] = "unique_system_identifier"
            f.attrs['creation_timestamp'] = time.strftime("%Y-%m-%d %H:%M:%S")
            f.attrs['last_modified'] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            # Store dimensional controllers
            dim_group = f.create_group('dimensional_controllers')
            for dim_type, controller in self.dimensional_controllers.items():
                dim_name = dim_type.value
                dim_group.attrs[f'{dim_name}_activation'] = controller.activation_level
                dim_group.attrs[f'{dim_name}_state'] = controller.state.value
                dim_group.attrs[f'{dim_name}_harmonic_frequency'] = controller.harmonic_frequency
                dim_group.attrs[f'{dim_name}_phase'] = controller.phase_offset
                # Store presence signature
                if controller.presence_signature:
                    for k, v in controller.presence_signature.items():
                        if isinstance(v, (list, tuple)):
                            dim_group.attrs[f'{dim_name}_presence_{k}'] = v
                        else:
                            dim_group.attrs[f'{dim_name}_presence_{k}'] = v
            
            # Store entropy manager state
            entropy_group = f.create_group('entropy_manager')
            entropy_group.attrs['entropy_threshold'] = self.entropy_threshold
            entropy_group.attrs['spawn_threshold'] = self.spawn_threshold
            entropy_group.attrs['max_spawned_tensors'] = self.max_spawned_tensors
            
            # Store nodes with rich metadata
            nodes_group = f.create_group('nodes')
            for node_id, node in self.nodes.items():
                node_group = nodes_group.create_group(node_id)
                node_group.attrs['dimension_affinity'] = node.dimension_affinity.name
                node_group.attrs['activation_level'] = node.activation_level
                node_group.attrs['energy_level'] = node.energy_level
                node_group.attrs['preservation_integrity'] = node.preservation_integrity
                node_group.attrs['semantic_vector'] = node.semantic_vector
                node_group.attrs['causal_links'] = list(node.causal_links)
                node_group.attrs['observer_contexts'] = list(node.observer_contexts)
                node_group.attrs['phase_coherence'] = node.phase_coherence
                node_group.attrs['frequency_stability'] = node.frequency_stability
                
                # Store harmonic signature
                if node.harmonic_signature:
                    for k, v in node.harmonic_signature.items():
                        if isinstance(v, (list, tuple)):
                            node_group.attrs[f'harmonic_{k}'] = v
                        else:
                            node_group.attrs[f'harmonic_{k}'] = v
            
            # Store observers
            observer_group = f.create_group('observers')
            for observer_id, transform in self.observers.items():
                obs_group = observer_group.create_group(observer_id)
                obs_group.attrs['perspective_matrix'] = transform.perspective_matrix.tolist()
                obs_group.attrs['semantic_weights'] = transform.semantic_weights
                obs_group.attrs['temporal_scale'] = transform.temporal_scale
                obs_group.attrs['access_permissions'] = list(transform.access_permissions)
            
            # Store transition triggers
            triggers_group = f.create_group('transition_triggers')
            for i, trigger in enumerate(self.transition_triggers):
                trigger_group = triggers_group.create_group(f'trigger_{i}')
                trigger_group.attrs['trigger_type'] = trigger.trigger_type
                trigger_group.attrs['source_dimension'] = trigger.source_dimension
                trigger_group.attrs['threshold'] = trigger.threshold
                trigger_group.attrs['priority'] = trigger.priority
                # Convert function to string if present
                if trigger.condition_fn:
                    trigger_group.attrs['condition_fn'] = str(trigger.condition_fn)
            
            # Store sparse data
            if self.tensor_data:
                coords = np.array(list(self.tensor_data.keys()), dtype=np.uint32)
                values = np.array(list(self.tensor_data.values()), dtype=np.float32)
                
                f.create_dataset('sparse_coordinates', 
                               data=coords, 
                               compression='gzip',
                               compression_opts=compression_level)
                f.create_dataset('sparse_values', 
                               data=values, 
                               compression='gzip',
                               compression_opts=compression_level)
            
            # Store blockchain
            if self.blockchain:
                # Convert blockchain to structured data
                blockchain_data = []
                for block in self.blockchain:
                    # Extract relevant data
                    block_data = {
                        'block_id': block['block_id'],
                        'signal': block.get('signal', {}),
                        'result': block.get('result', {}),
                        'timestamp': block.get('timestamp', 0),
                        'prev_hash': block.get('prev_hash', ''),
                        'hash': block.get('hash', '')
                    }
                    blockchain_data.append(block_data)
                
                # Convert to JSON string for storage
                blockchain_json = json.dumps(blockchain_data)
                f.create_dataset('blockchain', 
                               data=np.string_(blockchain_json),
                               compression='gzip',
                               compression_opts=compression_level)
            
            # Store spawn registry
            if self.spawn_registry:
                spawn_data = {}
                for spawn_id, spawn_info in self.spawn_registry.items():
                    spawn_data[spawn_id] = {
                        'tensor': spawn_info['tensor'].get_system_status() if spawn_info['tensor'] else {},
                        'parent_coords': spawn_info['parent_coords'],
                        'spawn_time': spawn_info['spawn_time'],
                        'spawn_trigger': spawn_info['spawn_trigger'],
                        'data_inherited': spawn_info['data_inherited'],
                        'status': spawn_info.get('status', 'active')
                    }
                f.create_dataset('spawn_registry', 
                               data=msgpack.packb(spawn_data, use_bin_type=True),
                               compression='gzip',
                               compression_opts=compression_level)
    
    def _save_msgpack(self, filename: str, compression_level: int = 6) -> None:
        """Save using MessagePack with compression"""
        # Structure data for msgpack
        data = {
            'file_type': 'ARFS_TENSOR',
            'version': 2.3,
            'dimensions': self.dimensions,
            'sparse_threshold': self.sparse_threshold,
            'system_id': 'unique_system_identifier',
            'creation_timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
            'last_modified': time.strftime("%Y-%m-%d %H:%M:%S"),
            'dimensional_controllers': {
                dim_type.value: {
                    'activation_level': controller.activation_level,
                    'state': controller.state.value,
                    'harmonic_frequency': controller.harmonic_frequency,
                    'phase_offset': controller.phase_offset,
                    'presence_signature': controller.presence_signature
                } for dim_type, controller in self.dimensional_controllers.items()
            },
            'entropy_manager': {
                'entropy_threshold': self.entropy_threshold,
                'spawn_threshold': self.spawn_threshold,
                'max_spawned_tensors': self.max_spawned_tensors
            },
            'nodes': {
                node_id: {
                    'dimension_affinity': node.dimension_affinity.name,
                    'activation_level': node.activation_level,
                    'energy_level': node.energy_level,
                    'preservation_integrity': node.preservation_integrity,
                    'semantic_vector': node.semantic_vector,
                    'causal_links': list(node.causal_links),
                    'observer_contexts': list(node.observer_contexts),
                    'phase_coherence': node.phase_coherence,
                    'frequency_stability': node.frequency_stability,
                    'harmonic_signature': node.harmonic_signature
                } for node_id, node in self.nodes.items()
            },
            'observers': {
                observer_id: {
                    'perspective_matrix': transform.perspective_matrix.tolist(),
                    'semantic_weights': transform.semantic_weights,
                    'temporal_scale': transform.temporal_scale,
                    'access_permissions': list(transform.access_permissions)
                } for observer_id, transform in self.observers.items()
            },
            'transition_triggers': [
                {
                    'trigger_type': trigger.trigger_type,
                    'source_dimension': trigger.source_dimension,
                    'threshold': trigger.threshold,
                    'priority': trigger.priority,
                    'condition_fn': str(trigger.condition_fn) if trigger.condition_fn else None
                } for trigger in self.transition_triggers
            ],
            'sparse_coordinates': list(self.tensor_data.keys()),
            'sparse_values': list(self.tensor_data.values()),
            'blockchain': self.blockchain,
            'spawn_registry': self.spawn_registry
        }
        
        # Serialize to msgpack then compress
        packed = msgpack.packb(data, use_bin_type=True)
        compressed = zlib.compress(packed, level=compression_level)
        
        with open(filename, 'wb') as f:
            f.write(compressed)
    
    def _save_custom_binary(self, filename: str, compression_level: int = 6) -> None:
        """Save using custom binary format with header"""
        # Create metadata dictionary
        metadata = {
            'file_type': 'ARFS_TENSOR',
            'version': 2.3,
            'dimensions': self.dimensions,
            'sparse_threshold': self.sparse_threshold,
            'system_id': 'unique_system_identifier',
            'creation_timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
            'last_modified': time.strftime("%Y-%m-%d %H:%M:%S"),
            'dimensional_controllers': {
                dim_type.value: {
                    'activation_level': controller.activation_level,
                    'state': controller.state.value,
                    'harmonic_frequency': controller.harmonic_frequency,
                    'phase_offset': controller.phase_offset,
                    'presence_signature': controller.presence_signature
                } for dim_type, controller in self.dimensional_controllers.items()
            },
            'entropy_manager': {
                'entropy_threshold': self.entropy_threshold,
                'spawn_threshold': self.spawn_threshold,
                'max_spawned_tensors': self.max_spawned_tensors
            },
            'nodes': {
                node_id: {
                    'dimension_affinity': node.dimension_affinity.name,
                    'activation_level': node.activation_level,
                    'energy_level': node.energy_level,
                    'preservation_integrity': node.preservation_integrity,
                    'semantic_vector': node.semantic_vector,
                    'causal_links': list(node.causal_links),
                    'observer_contexts': list(node.observer_contexts),
                    'phase_coherence': node.phase_coherence,
                    'frequency_stability': node.frequency_stability,
                    'harmonic_signature': node.harmonic_signature
                } for node_id, node in self.nodes.items()
            },
            'observers': {
                observer_id: {
                    'perspective_matrix': transform.perspective_matrix.tolist(),
                    'semantic_weights': transform.semantic_weights,
                    'temporal_scale': transform.temporal_scale,
                    'access_permissions': list(transform.access_permissions)
                } for observer_id, transform in self.observers.items()
            },
            'transition_triggers': [
                {
                    'trigger_type': trigger.trigger_type,
                    'source_dimension': trigger.source_dimension,
                    'threshold': trigger.threshold,
                    'priority': trigger.priority,
                    'condition_fn': str(trigger.condition_fn) if trigger.condition_fn else None
                } for trigger in self.transition_triggers
            ],
            'sparse_coordinates': list(self.tensor_data.keys()),
            'sparse_values': list(self.tensor_data.values()),
            'blockchain': self.blockchain,
            'spawn_registry': self.spawn_registry
        }
        
        # Convert metadata to JSON string for compression
        metadata_json = json.dumps(metadata, ensure_ascii=False, indent=2)
        metadata_compressed = zlib.compress(metadata_json.encode('utf-8'), level=compression_level)
        
        # Calculate offsets
        metadata_size = len(metadata_compressed)
        data_offset = 20 + metadata_size  # Header is 20 bytes
        
        # Build header
        header = struct.pack('4sIIII', 
                            b'ARFS',
                            2300,  # Magic number
                            23,    # Version number
                            metadata_size,
                            data_offset
        )
        
        # Calculate checksum
        checksum = zlib.adler32(metadata_compressed)
        header += struct.pack('Q', checksum)
        
        # Create final binary
        binary_data = bytearray()
        binary_data.extend(header)
        binary_data.extend(metadata_compressed)
        
        # Add tensor data
        tensor_data = []
        for coords, value in self.tensor_data.items():
            tensor_data.append((coords, value))
        
        # Convert to binary format
        for coords, value in tensor_data:
            x, y, z, t = coords
            binary_data.extend(struct.pack('IIIIf', x, y, z, t, value))
        
        # Write to file
        with open(filename, 'wb') as f:
            f.write(binary_data)
    
    @classmethod
    def load_binary(cls, filename: str, format: str = 'hdf5') -> 'EnhancedARFSTensor':
        """Load tensor from binary file with rich metadata"""
        if format == 'hdf5':
            return cls._load_hdf5(filename)
        elif format == 'msgpack':
            return cls._load_msgpack(filename)
        elif format == 'custom':
            return cls._load_custom_binary(filename)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    @classmethod
    def _load_hdf5(cls, filename: str) -> 'EnhancedARFSTensor':
        """Load from HDF5 file with full metadata"""
        with h5py.File(filename, 'r') as f:
            # Check format
            if f.attrs['file_type'] != 'ARFS_TENSOR':
                raise ValueError("Invalid ARFS tensor file format")
            
            # Create tensor instance
            dimensions = f.attrs['dimensions']
            tensor = EnhancedARFSTensor(dimensions=dimensions)
            tensor.sparse_threshold = f.attrs['sparse_threshold']
            
            # Restore dimensional controllers
            dim_group = f['dimensional_controllers']
            for dim_type in DimensionType:
                dim_name = dim_type.value
                if f'{dim_name}_activation' in dim_group.attrs:
                    activation = dim_group.attrs[f'{dim_name}_activation']
                    tensor.dimensional_controllers[dim_type].activation_level = activation
                    tensor.dimensional_controllers[dim_type].state = ActivationState(dim_group.attrs[f'{dim_name}_state'])
            
            # Restore nodes
            nodes_group = f['nodes']
            for node_id in nodes_group:
                node_group = nodes_group[node_id]
                dim_affinity = DimensionType[node_group.attrs['dimension_affinity']]
                node = ARFSNode(node_id, dim_affinity)
                node.activation_level = node_group.attrs['activation_level']
                node.energy_level = node_group.attrs['energy_level']
                node.preservation_integrity = node_group.attrs['preservation_integrity']
                node.semantic_vector = node_group.attrs['semantic_vector']
                node.causal_links = set(node_group.attrs['causal_links'])
                node.observer_contexts = set(node_group.attrs['observer_contexts'])
                node.phase_coherence = node_group.attrs['phase_coherence']
                node.frequency_stability = node_group.attrs['frequency_stability']
                
                # Restore harmonic signature
                if 'harmonic_base_frequency' in node_group.attrs:
                    node.harmonic_signature = {
                        'base_frequency': node_group.attrs['harmonic_base_frequency'],
                        'harmonic_series': node_group.attrs['harmonic_series'].tolist() if isinstance(node_group.attrs['harmonic_series'], np.ndarray) else node_group.attrs['harmonic_series'],
                        'phase_signature': node_group.attrs['phase_signature'],
                        'amplitude_envelope': node_group.attrs['amplitude_envelope'].tolist() if isinstance(node_group.attrs['amplitude_envelope'], np.ndarray) else node_group.attrs['amplitude_envelope'],
                        'quantum_state': node_group.attrs['quantum_state'],
                        'dimensional_resonance': node_group.attrs['dimensional_resonance'],
                        'coherence_pattern': node_group.attrs['coherence_pattern'].tolist() if isinstance(node_group.attrs['coherence_pattern'], np.ndarray) else node_group.attrs['coherence_pattern'],
                        'presence_identifier': node_group.attrs['presence_identifier']
                    }
                tensor.register_node(node)
            
            # Restore observers
            observer_group = f['observers']
            for observer_id in observer_group:
                obs_group = observer_group[observer_id]
                transform = ObserverTransform(
                    observer_id=observer_id,
                    perspective_matrix=np.array(obs_group.attrs['perspective_matrix']),
                    semantic_weights=obs_group.attrs['semantic_weights'],
                    temporal_scale=obs_group.attrs['temporal_scale'],
                    access_permissions=set(obs_group.attrs['access_permissions'])
                )
                tensor.observers[observer_id] = transform
            
            # Restore transition triggers
            if 'transition_triggers' in f:
                triggers_group = f['transition_triggers']
                for trigger_id in triggers_group:
                    trigger_group = triggers_group[trigger_id]
                    trigger = TransitionTrigger(
                        trigger_type=trigger_group.attrs['trigger_type'],
                        source_dimension=trigger_group.attrs['source_dimension'],
                        threshold=trigger_group.attrs['threshold'],
                        priority=trigger_group.attrs['priority']
                    )
                    # Convert condition function to string if present
                    if 'condition_fn' in trigger_group.attrs and trigger_group.attrs['condition_fn']:
                        # We can't safely eval from file, so we'll set it as None for now
                        pass
                    tensor.transition_triggers.append(trigger)
            
            # Restore sparse data
            if 'sparse_coordinates' in f and 'sparse_values' in f:
                coords = f['sparse_coordinates'][:]
                values = f['sparse_values'][:]
                for coord, value in zip(coords, values):
                    tensor.tensor_data[tuple(coord)] = value
            
            # Restore blockchain
            if 'blockchain' in f:
                blockchain_json = f['blockchain'][()]
                try:
                    blockchain = json.loads(blockchain_json)
                    # Convert back to block structure
                    tensor.blockchain = []
                    for block in blockchain:
                        tensor.blockchain.append({
                            'block_id': block['block_id'],
                            'signal': block['signal'],
                            'result': block['result'],
                            'timestamp': block['timestamp'],
                            'prev_hash': block['prev_hash'],
                            'hash': block['hash']
                        })
                except Exception as e:
                    logger.error(f"Error parsing blockchain: {e}")
            
            # Restore spawn registry
            if 'spawn_registry' in f:
                spawn_data = msgpack.unpackb(f['spawn_registry'][:], raw=False)
                tensor.spawn_registry = {}
                for spawn_id, data in spawn_data.items():
                    tensor.spawn_registry[spawn_id] = {
                        'tensor': data['tensor'],
                        'parent_coords': data['parent_coords'],
                        'spawn_time': data['spawn_time'],
                        'spawn_trigger': data['spawn_trigger'],
                        'data_inherited': data['data_inherited'],
                        'status': data['status']
                    }
            
            return tensor
    
    @classmethod
    def _load_msgpack(cls, filename: str) -> 'EnhancedARFSTensor':
        """Load from MessagePack file with compression"""
        with open(filename, 'rb') as f:
            compressed_data = f.read()
        
        # Decompress the data
        decompressed = zlib.decompress(compressed_data)
        
        # Unpack MessagePack data
        data = msgpack.unpackb(decompressed, raw=False)
        
        # Create tensor instance
        tensor = EnhancedARFSTensor(dimensions=data['dimensions'])
        tensor.sparse_threshold = data['sparse_threshold']
        
        # Restore dimensional controllers
        for dim_name, controller_data in data['dimensional_controllers'].items():
            dim_type = None
            for d_type in DimensionType:
                if d_type.value == dim_name:
                    dim_type = d_type
                    break
            if dim_type:
                controller = tensor.dimensional_controllers[dim_type]
                controller.activation_level = controller_data['activation_level']
                controller.state = ActivationState(controller_data['state'])
                controller.harmonic_frequency = controller_data['harmonic_frequency']
                controller.phase_offset = controller_data['phase_offset']
                controller.presence_signature = controller_data['presence_signature']
        
        # Restore nodes
        for node_id, node_data in data['nodes'].items():
            dim_affinity = DimensionType[node_data['dimension_affinity']]
            node = ARFSNode(node_id, dim_affinity)
            node.activation_level = node_data['activation_level']
            node.energy_level = node_data['energy_level']
            node.preservation_integrity = node_data['preservation_integrity']
            node.semantic_vector = node_data['semantic_vector']
            node.causal_links = set(node_data['causal_links'])
            node.observer_contexts = set(node_data['observer_contexts'])
            node.phase_coherence = node_data['phase_coherence']
            node.frequency_stability = node_data['frequency_stability']
            node.harmonic_signature = node_data['harmonic_signature']
            tensor.register_node(node)
        
        # Restore observers
        for observer_id, transform_data in data['observers'].items():
            transform = ObserverTransform(
                observer_id=observer_id,
                perspective_matrix=np.array(transform_data['perspective_matrix']),
                semantic_weights=transform_data['semantic_weights'],
                temporal_scale=transform_data['temporal_scale'],
                access_permissions=set(transform_data['access_permissions'])
            )
            tensor.observers[observer_id] = transform
        
        # Restore transition triggers
        for trigger_data in data['transition_triggers']:
            trigger = TransitionTrigger(
                trigger_type=trigger_data['trigger_type'],
                source_dimension=trigger_data['source_dimension'],
                threshold=trigger_data['threshold'],
                priority=trigger_data['priority']
            )
            # We can't safely eval condition function from file, so we'll skip it
            tensor.transition_triggers.append(trigger)
        
        # Restore sparse data
        coords_list = data['sparse_coordinates']
        values_list = data['sparse_values']
        for coord, value in zip(coords_list, values_list):
            tensor.tensor_data[tuple(coord)] = value
        
        # Restore blockchain
        tensor.blockchain = data['blockchain']
        
        # Restore spawn registry
        tensor.spawn_registry = data['spawn_registry']
        
        return tensor
    
    def _initialize_default_triggers(self):
        """Initialize default dimensional transition triggers"""
        self.transition_triggers = [
            TransitionTrigger("entropy_threshold", "Z", 0.7, priority=1),
            TransitionTrigger("activation_cascade", "X", 0.8, priority=2),
            TransitionTrigger("temporal_coherence", "T", 0.6, priority=3),
            TransitionTrigger("memory_pressure", "Y", 0.9, priority=1)
        ]
    
    def register_observer(self, observer_id: str, permissions: Set[str] = None) -> ObserverTransform:
        """Register a new observer with specific transformation parameters"""
        permissions = permissions or {"read", "write", "observe"}
        
        observer_transform = ObserverTransform(
            observer_id=observer_id,
            perspective_matrix=np.eye(4) + np.random.normal(0, 0.01, (4, 4)),
            semantic_weights={"execution": 1.0, "memory": 0.8, "symbolic": 0.6, "temporal": 0.9},
            temporal_scale=1.0,
            access_permissions=permissions
        )
        
        self.observers[observer_id] = observer_transform
        logger.info(f"Registered observer {observer_id} with permissions {permissions}")
        return observer_transform
    
    def set_active_observer(self, observer_id: str):
        """Set the active observer context for operations"""
        if observer_id in self.observers:
            self.active_observer = observer_id
            logger.debug(f"Set active observer to {observer_id}")
        else:
            raise ValueError(f"Observer {observer_id} not registered")
    
    def register_node(self, node: ARFSNode) -> bool:
        """Register a node with dimensional awareness"""
        try:
            with self.main_lock:
                self.nodes[node.node_id] = node
                self.dimensional_nodes[node.dimension_affinity].add(node.node_id)
                
                logger.debug(f"Registered node {node.node_id[:12]} in dimension {node.dimension_affinity.value}")
                return True
        except Exception as e:
            logger.error(f"Error registering node {node.node_id[:12]}: {e}")
            return False
    
    def map_to_coordinates(self, src: str, dst: str, signal_type: str, 
                          timestamp: float, observer_context: Optional[str] = None) -> Tuple[int, int, int, int]:
        """Advanced semantic-to-coordinate mapping with observer awareness"""
        
        # Get observer transform if available
        transform = None
        if observer_context and observer_context in self.observers:
            transform = self.observers[observer_context]
        elif self.active_observer:
            transform = self.observers[self.active_observer]
        
        # X-dimension: Execution context mapping
        if transform:
            src_semantic = self._semantic_hash(src, transform.semantic_weights.get("execution", 1.0))
        else:
            src_semantic = hash(src)
        src_x = abs(src_semantic) % self.dimensions
        
        # Y-dimension: Memory context mapping
        dst_semantic = self._contextual_memory_mapping(dst, signal_type)
        dst_y = dst_semantic % self.dimensions
        
        # Z-dimension: Symbolic space mapping
        symbolic_hash = self._symbolic_space_mapping(signal_type)
        type_z = symbolic_hash % self.dimensions
        
        # T-dimension: Temporal mapping with causality
        time_t = self._temporal_mapping(timestamp) % self.dimensions
        
        return (src_x, dst_y, type_z, time_t)
    
    def _semantic_hash(self, text: str, weight: float = 1.0) -> int:
        """Generate weighted semantic hash"""
        return int(hashlib.sha256(text.encode()).hexdigest()[:8], 16) * int(weight * 1000)
    
    def _contextual_memory_mapping(self, dst: str, signal_type: str) -> int:
        """Map destination and signal type to memory coordinates"""
        context_str = f"{dst}::{signal_type}"
        return abs(hash(context_str))
    
    def _symbolic_space_mapping(self, signal_type: str) -> int:
        """Map signal type to symbolic space with activation potential"""
        symbolic_controller = self.dimensional_controllers[DimensionType.Z]
        
        # Bias towards activated regions in symbolic space
        base_hash = abs(hash(signal_type))
        activation_bias = int(symbolic_controller.activation_level * 1000)
        
        return base_hash + activation_bias
    
    def _temporal_mapping(self, timestamp: float) -> int:
        """Map timestamp to temporal coordinates with causality awareness"""
        # Use modular arithmetic for temporal cycling
        time_quantum = 1000.0  # 1 second quantum
        quantized_time = int(timestamp / time_quantum)
        
        # Add causal bias based on recent signal history
        causal_bias = len(self.signal_pipeline) % 100
        
        return quantized_time + causal_bias
    
    def insert_signal(self, coords: Tuple[int, int, int, int], value: float) -> bool:
        """Insert signal with sparse storage and validation"""
        try:
            x, y, z, t = coords
            
            # Validate coordinates
            if not all(0 <= coord < self.dimensions for coord in coords):
                logger.warning(f"Invalid coordinates: {coords}")
                return False
            
            with self.tensor_lock:
                # Use sparse storage - only store significant values
                if abs(value) >= self.sparse_threshold:
                    self.tensor_data[coords] = value
                elif coords in self.tensor_data:
                    # Remove if value drops below threshold
                    del self.tensor_data[coords]
                
                # Update comprehensive entropy measures
                entropy_measurement = self.entropy_manager.calculate_comprehensive_entropy(self.tensor_data)
                
                # Check for entropy anomalies
                anomalies = self.entropy_manager.detect_entropy_anomalies(entropy_measurement)
                if anomalies['severity'] > 0.5:
                    logger.warning(f"High entropy anomaly detected: {anomalies}")
                    # Could trigger corrective actions or tensor respawn here
                
                logger.debug(f"Inserted signal at {coords} with value {value:.4f}")
                return True
                
        except Exception as e:
            logger.error(f"Error inserting signal: {e}")
            return False
    
    def get_signal(self, coords: Tuple[int, int, int, int]) -> float:
        """Retrieve signal value with sparse storage"""
        try:
            x, y, z, t = coords
            
            if not all(0 <= coord < self.dimensions for coord in coords):
                logger.warning(f"Invalid coordinates: {coords}")
                return 0.0
            
            with self.tensor_lock:
                value = self.tensor_data.get(coords, 0.0)
                logger.debug(f"Retrieved signal at {coords}: {value:.4f}")
                return value
                
        except Exception as e:
            logger.error(f"Error retrieving signal: {e}")
            return 0.0
    
    def transmit_signal_enhanced(self, src: str, dst: str, signal_type: str,
                               timestamp: float, value: float = 1.0,
                               observer_context: Optional[str] = None,
                               metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Enhanced signal transmission with multi-phase processing"""
        
        try:
            with self.main_lock:
                # Phase 1: Prepare signal with metadata
                signal_id = hashlib.md5(f"{src}{dst}{timestamp}{np.random.random()}".encode()).hexdigest()
                
                signal = {
                    "signal_id": signal_id,
                    "src": src,
                    "dst": dst,
                    "type": signal_type,
                    "timestamp": timestamp,
                    "value": value,
                    "observer": observer_context or self.active_observer,
                    "metadata": metadata or {}
                }
                
                # Phase 2: Route through dimensional mapping
                coords = self.map_to_coordinates(src, dst, signal_type, timestamp, observer_context)
                signal["coords"] = coords
                
                # Phase 3: Check dimensional transition triggers
                entropy_state = self.calculate_system_entropy()
                transition = self._evaluate_transition_triggers(entropy_state, signal)
                
                if transition:
                    self._execute_dimensional_transition(transition)
                
                # Phase 4: Process through active dimension
                result = self._process_in_active_dimension(signal)
                
                # Phase 5: Store in tensor and blockchain
                self.insert_signal(coords, value)
                block = self._create_immutable_block(signal, result)
                self.blockchain.append(block)
                
                # Phase 6: Activate destination nodes
                if dst in self.nodes:
                    node_result = self.nodes[dst].process(signal)
                    if node_result:
                        # Recursive signal generation
                        self.signal_pipeline.append(node_result)
                
                # Phase 7: Update causal network
                self.causal_network[src].add(dst)
                
                self.operation_counts['transmit_enhanced'] += 1
                logger.info(f"Enhanced signal transmission: {src[:12]} -> {dst[:12]} (type: {signal_type})")
                
                return block
                
        except Exception as e:
            logger.error(f"Enhanced signal transmission failed: {e}")
            return {}
    
    def calculate_system_entropy(self) -> EntropyMeasurement:
        """Calculate comprehensive entropy measures across all dimensions"""
        try:
            measurement = EntropyMeasurement()
            
            # Get dimensional data
            dimensional_data = {}
            for dim_type in DimensionType:
                dimensional_data[dim_type] = self._get_dimensional_data(dim_type)
            
            # Calculate Shannon entropy
            all_values = list(self.tensor_data.values())
            if all_values:
                # Discretize values for entropy calculation
                hist, _ = np.histogram(all_values, bins=50, density=True)
                hist = hist[hist > 0]  # Remove zero bins
                measurement.shannon_entropy = float(entropy(hist))
            
            # Calculate predictive divergence
            measurement.predictive_divergence = self._calculate_predictive_divergence()
            
            # Calculate symbolic entropy
            measurement.symbolic_entropy = self._calculate_symbolic_entropy()
            
            # Calculate temporal entropy
            measurement.temporal_entropy = self._calculate_temporal_entropy()
            
            # Calculate recursive entropy (across dimensional boundaries)
            measurement.recursive_entropy = self._calculate_recursive_entropy()
            
            # Weighted composite measure
            measurement.composite_measure = (
                0.2 * measurement.shannon_entropy +
                0.2 * measurement.predictive_divergence +
                0.3 * measurement.symbolic_entropy +
                0.2 * measurement.temporal_entropy +
                0.1 * measurement.recursive_entropy
            )
            
            # Store in history
            self.entropy_history.append({
                "timestamp": time.time(),
                "measurement": measurement
            })
            
            return measurement
            
        except Exception as e:
            logger.error(f"Error calculating system entropy: {e}")
            return EntropyMeasurement()
    
    def _get_dimensional_data(self, dimension: DimensionType) -> np.ndarray:
        """Extract data for specific dimension"""
        dim_index = list(DimensionType).index(dimension)
        
        # Collect all values for this dimension
        values = []
        for coords, value in self.tensor_data.items():
            values.append((coords[dim_index], value))
        
        if not values:
            return np.array([])
        
        # Create dimensional array
        dim_array = np.zeros(self.dimensions)
        for coord, value in values:
            dim_array[coord] += value
            
        return dim_array
    
    def _calculate_predictive_divergence(self) -> float:
        """Calculate divergence from expected patterns"""
        if len(self.entropy_history) < 2:
            return 0.0
        
        recent_entropies = [entry["measurement"].shannon_entropy 
                          for entry in list(self.entropy_history)[-10:]]
        
        if len(recent_entropies) < 2:
            return 0.0
        
        # Calculate variance as measure of unpredictability
        variance = np.var(recent_entropies)
        return min(1.0, variance / 0.1)  # Normalize
    
    def _calculate_symbolic_entropy(self) -> float:
        """Calculate entropy of symbolic structures in Z-dimension"""
        z_data = self._get_dimensional_data(DimensionType.Z)
        
        if len(z_data) == 0:
            return 0.0
        
        # Count symbolic patterns
        non_zero = z_data[z_data > 0]
        if len(non_zero) == 0:
            return 0.0
        
        # Simple symbolic entropy based on pattern distribution
        hist, _ = np.histogram(non_zero, bins=20, density=True)
        hist = hist[hist > 0]
        
        return float(entropy(hist)) if len(hist) > 1 else 0.0
    
    def _calculate_temporal_entropy(self) -> float:
        """Calculate temporal coherence entropy"""
        if len(self.blockchain) < 2:
            return 0.0
        
        # Analyze temporal intervals between signals
        intervals = []
        for i in range(1, min(len(self.blockchain), 100)):  # Last 100 signals
            prev_time = self.blockchain[i-1].get("timestamp", 0)
            curr_time = self.blockchain[i].get("timestamp", 0)
            if curr_time > prev_time:
                intervals.append(curr_time - prev_time)
        
        if len(intervals) < 2:
            return 0.0
        
        # Calculate entropy of time intervals
        hist, _ = np.histogram(intervals, bins=20, density=True)
        hist = hist[hist > 0]
        
        return float(entropy(hist)) if len(hist) > 1 else 0.0
    
    def _calculate_recursive_entropy(self) -> float:
        """Calculate entropy across dimensional boundaries"""
        cross_dimensional_signals = 0
        total_signals = len(self.blockchain)
        
        if total_signals == 0:
            return 0.0
        
        # Count signals that cross dimensional boundaries
        for block in self.blockchain[-100:]:  # Recent signals
            coords = block.get("coords")
            if coords:
                x, y, z, t = coords
                # Check if signal spans multiple dimensional regions
                if x != y or y != z or z != t:
                    cross_dimensional_signals += 1
        
        # Normalize by total signals
        return min(1.0, cross_dimensional_signals / min(total_signals, 100))
    
    def _evaluate_transition_triggers(self, entropy_state: EntropyMeasurement, 
                                    signal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Evaluate whether dimensional transitions should occur"""
        for trigger in sorted(self.transition_triggers, key=lambda t: t.priority):
            
            if trigger.trigger_type == "entropy_threshold":
                if entropy_state.composite_measure > trigger.threshold:
                    return {
                        "type": "entropy_transition",
                        "target_dimension": trigger.source_dimension,
                        "trigger_value": entropy_state.composite_measure,
                        "threshold": trigger.threshold
                    }
            
            elif trigger.trigger_type == "activation_cascade":
                src_activation = self.nodes.get(signal["src"], ARFSNode("")).activation_level
                if src_activation > trigger.threshold:
                    return {
                        "type": "activation_cascade",
                        "target_dimension": trigger.source_dimension,
                        "trigger_value": src_activation,
                        "threshold": trigger.threshold
                    }
        
        return None
    
    def _execute_dimensional_transition(self, transition: Dict[str, Any]):
        """Execute dimensional transition based on trigger"""
        target_dim_name = transition["target_dimension"]
        target_dimension = None
        
        # Find target dimension
        for dim_type in DimensionType:
            if dim_type.value == target_dim_name or dim_type.name == target_dim_name:
                target_dimension = dim_type
                break
        
        if not target_dimension:
            logger.error(f"Unknown target dimension: {target_dim_name}")
            return
        
        logger.info(f"Executing dimensional transition to {target_dimension.value}")
        
        # Deactivate currently active dimensions
        for dim_type, controller in self.dimensional_controllers.items():
            if controller.activation_level > 0.5 and dim_type != target_dimension:
                controller.deactivate()
        
        # Activate target dimension
        target_controller = self.dimensional_controllers[target_dimension]
        target_controller.activate(level=0.8)
        
        self.operation_counts['dimensional_transitions'] += 1
    
    def _process_in_active_dimension(self, signal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process signal through currently active dimension"""
        active_dims = [dim_type for dim_type, controller in self.dimensional_controllers.items()
                      if controller.activation_level > 0.5]
        
        if not active_dims:
            return None
        
        primary_dim = max(active_dims, 
                         key=lambda d: self.dimensional_controllers[d].activation_level)
        
        # Dimension-specific processing
        if primary_dim == DimensionType.X:
            return self._process_execution_dimension(signal)
        elif primary_dim == DimensionType.Y:
            return self._process_memory_dimension(signal)
        elif primary_dim == DimensionType.Z:
            return self._process_symbolic_dimension(signal)
        elif primary_dim == DimensionType.T:
            return self._process_temporal_dimension(signal)
        
        return None
    
    def _process_execution_dimension(self, signal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process signal in execution dimension"""
        return {
            "processed_by": "execution_dimension",
            "processing_time": 0.001,
            "result": "executed",
            "dimension": "X"
        }
    
    def _process_memory_dimension(self, signal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process signal in memory dimension"""
        return {
            "processed_by": "memory_dimension", 
            "stored_at": signal.get("coords"),
            "result": "stored",
            "dimension": "Y"
        }
    
    def _process_symbolic_dimension(self, signal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process signal in symbolic dimension"""
        return {
            "processed_by": "symbolic_dimension",
            "symbolic_resonance": 0.7,
            "result": "symbolized",
            "dimension": "Z"
        }
    
    def _process_temporal_dimension(self, signal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process signal in temporal dimension"""
        return {
            "processed_by": "temporal_dimension",
            "causal_chain": len(self.causal_network.get(signal["src"], set())),
            "result": "sequenced",
            "dimension": "T"
        }
    
    def _create_immutable_block(self, signal: Dict[str, Any], 
                              result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Create immutable blockchain block for signal"""
        block = {
            "block_id": hashlib.sha256(f"{signal['signal_id']}{time.time()}".encode()).hexdigest(),
            "signal": signal.copy(),
            "result": result,
            "timestamp": time.time(),
            "prev_hash": self.blockchain[-1]["block_id"] if self.blockchain else None
        }
        
        # Add block hash
        block_json = json.dumps({k: v for k, v in block.items() if k != "hash"}, sort_keys=True)
        block["hash"] = hashlib.sha256(block_json.encode()).hexdigest()
        
        return block
    
    def detect_activation_patterns(self) -> List[Dict[str, Any]]:
        """Detect cross-dimensional patterns and resonance circuits"""
        patterns = []
        
        try:
            # Pattern resonance detection
            for dim_a in DimensionType:
                for dim_b in DimensionType:
                    if dim_a != dim_b:
                        resonance = self._calculate_dimensional_resonance(dim_a, dim_b)
                        if resonance > 0.6:  # Resonance threshold
                            patterns.append({
                                'type': 'resonance',
                                'dimensions': [dim_a.value, dim_b.value],
                                'strength': resonance,
                                'activation_potential': self._calculate_activation_potential(dim_a, dim_b)
                            })
            
            # Temporal echo detection
            temporal_echoes = self._detect_temporal_echoes()
            patterns.extend(temporal_echoes)
            
            # Cross-dimensional motifs
            motifs = self._detect_cross_dimensional_motifs()
            patterns.extend(motifs)
            
            logger.debug(f"Detected {len(patterns)} activation patterns")
            return patterns
            
        except Exception as e:
            logger.error(f"Pattern detection failed: {e}")
            return []
    
    def _calculate_dimensional_resonance(self, dim_a: DimensionType, dim_b: DimensionType) -> float:
        """Calculate resonance between two dimensions"""
        data_a = self._get_dimensional_data(dim_a)
        data_b = self._get_dimensional_data(dim_b)
        
        if len(data_a) == 0 or len(data_b) == 0:
            return 0.0
        
        # Calculate correlation as resonance measure
        if len(data_a) != len(data_b):
            min_len = min(len(data_a), len(data_b))
            data_a = data_a[:min_len]
            data_b = data_b[:min_len]
        
        correlation = np.corrcoef(data_a, data_b)[0, 1]
        return abs(correlation) if not np.isnan(correlation) else 0.0
    
    def _calculate_activation_potential(self, dim_a: DimensionType, dim_b: DimensionType) -> float:
        """Calculate activation potential between dimensions"""
        controller_a = self.dimensional_controllers[dim_a]
        controller_b = self.dimensional_controllers[dim_b]
        
        # Potential based on current activation levels and dormancy states
        potential = (controller_a.activation_level + controller_b.activation_level) / 2.0
        
        # Adjust for dormancy energy levels
        potential *= (controller_a.dormancy_state.energy_level + 
                     controller_b.dormancy_state.energy_level) / 2.0
        
        return min(1.0, potential)
    
    def _detect_temporal_echoes(self) -> List[Dict[str, Any]]:
        """Detect temporal echo patterns across multiple timescales"""
        echoes = []
        
        if len(self.blockchain) < 10:
            return echoes
        
        # Analyze recent signals for temporal patterns
        recent_signals = self.blockchain[-50:]  # Last 50 signals
        
        # Group by signal type
        type_patterns = defaultdict(list)
        for block in recent_signals:
            signal_type = block.get("signal", {}).get("type", "unknown")
            timestamp = block.get("timestamp", 0)
            type_patterns[signal_type].append(timestamp)
        
        # Detect periodic patterns
        for signal_type, timestamps in type_patterns.items():
            if len(timestamps) >= 3:
                intervals = np.diff(sorted(timestamps))
                if len(intervals) > 1:
                    interval_std = np.std(intervals)
                    interval_mean = np.mean(intervals)
                    
                    # Low standard deviation indicates periodic pattern
                    if interval_std < interval_mean * 0.3:  # 30% threshold
                        echoes.append({
                            'type': 'temporal_echo',
                            'signal_type': signal_type,
                            'period': interval_mean,
                            'regularity': 1.0 - (interval_std / max(interval_mean, 0.001)),
                            'occurrences': len(timestamps)
                        })
        
        return echoes
    
    def _detect_cross_dimensional_motifs(self) -> List[Dict[str, Any]]:
        """Detect patterns that span multiple dimensions"""
        motifs = []
        
        # Analyze coordinate patterns in recent signals
        recent_coords = []
        for block in self.blockchain[-100:]:
            coords = block.get("signal", {}).get("coords")
            if coords:
                recent_coords.append(coords)
        
        if len(recent_coords) < 5:
            return motifs
        
        # Look for coordinate clusters
        coord_array = np.array(recent_coords)
        
        # Calculate centroid and spread
        centroid = np.mean(coord_array, axis=0)
        spread = np.std(coord_array, axis=0)
        
        # Detect dimensional clustering
        for i, dim_name in enumerate(['X', 'Y', 'Z', 'T']):
            if spread[i] < self.dimensions * 0.1:  # Clustered in this dimension
                cluster_center = int(centroid[i])
                cluster_tightness = 1.0 - (spread[i] / (self.dimensions * 0.1))
                
                motifs.append({
                    'type': 'dimensional_cluster',
                    'dimension': dim_name,
                    'center': cluster_center,
                    'tightness': cluster_tightness,
                    'signal_count': len(recent_coords)
                })
        
        return motifs
    
    def _update_entropy_measures_safe(self):
        """Update entropy measures with production safety checks"""
        try:
            # Calculate basic entropy metrics with safety bounds
            if len(self.tensor_data) > 0:
                values = list(self.tensor_data.values())
                finite_values = [v for v in values if np.isfinite(v)]
                
                if finite_values:
                    # Safe histogram calculation
                    hist, _ = np.histogram(finite_values, bins=min(50, len(finite_values)), density=True)
                    hist_safe = hist[hist > 1e-10]  # Remove very small values
                    
                    if len(hist_safe) > 0:
                        entropy_val = entropy(hist_safe)
                        if np.isfinite(entropy_val):
                            # Store entropy measurement safely
                            logger.debug(f"Shannon entropy calculated: {entropy_val:.4f}")
        except Exception as e:
            logger.error(f"Error updating entropy measures: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            "dimensions": self.dimensions,
            "active_nodes": len(self.nodes),
            "dimensional_activation": {
                dim_type.value: controller.activation_level 
                for dim_type, controller in self.dimensional_controllers.items()
            },
            "tensor_density": len(self.tensor_data) / (self.dimensions ** 4),
            "signal_count": len(self.blockchain),
            "entropy_measures": self.calculate_system_entropy().__dict__,
            "observer_count": len(self.observers),
            "active_observer": self.active_observer,
            "operation_counts": dict(self.operation_counts),
            "causal_network_size": sum(len(targets) for targets in self.causal_network.values())
        }
    
    def compress_dormant_dimensions(self, target_compression: float = 0.2):
        """Compress all dormant dimensions for memory efficiency"""
        compressed_count = 0
        
        for dim_type, controller in self.dimensional_controllers.items():
            if controller.activation_level < 0.1:  # Dormant dimension
                controller.deactivate(compression_level="OPTIMAL")
                compressed_count += 1
        
        logger.info(f"Compressed {compressed_count} dormant dimensions")
        return compressed_count
    
    def spawn_child_tensor(self, parent_coords: Tuple[int, int, int, int], 
                          spawn_trigger: str = "entropy_threshold") -> 'EnhancedARFSTensor':
        """Auto-spawn child ARFS tensor when complexity thresholds are met"""
        try:
            # Calculate spawn parameters based on parent tensor state
            child_dimensions = max(10, self.dimensions // 4)  # Child is 1/4 size of parent
            
            # Create child tensor with inherited entropy manager
            child_tensor = EnhancedARFSTensor(
                dimensions=child_dimensions,
                quantum_security=self.quantum_security,
                entropy_threshold=self.entropy_threshold * 0.8  # Lower threshold for child
            )
            
            # Transfer relevant data to child
            x, y, z, t = parent_coords
            region_data = {}
            
            # Extract data from parent region
            for coord, data in self.tensor_data.items():
                cx, cy, cz, ct = coord
                if (abs(cx - x) <= child_dimensions//2 and 
                    abs(cy - y) <= child_dimensions//2 and
                    abs(cz - z) <= child_dimensions//2 and
                    abs(ct - t) <= child_dimensions//2):
                    # Map to child coordinates
                    new_coord = (cx - x + child_dimensions//2,
                               cy - y + child_dimensions//2, 
                               cz - z + child_dimensions//2,
                               ct - t + child_dimensions//2)
                    if all(0 <= c < child_dimensions for c in new_coord):
                        region_data[new_coord] = data.copy()
            
            child_tensor.tensor_data = region_data
            
            # Register child in spawn registry
            spawn_id = f"spawn_{len(self.spawn_registry)}_{spawn_trigger}_{int(time.time())}"
            self.spawn_registry[spawn_id] = {
                "tensor": child_tensor,
                "parent_coords": parent_coords,
                "spawn_time": time.time(),
                "spawn_trigger": spawn_trigger,
                "data_inherited": len(region_data)
            }
            
            logger.info(f"Spawned child tensor {spawn_id} with {len(region_data)} inherited data points")
            return child_tensor
            
        except Exception as e:
            logger.error(f"Failed to spawn child tensor: {e}")
            return self  # Return parent if spawn fails
    
    def integrate_harmonic_breath_field(self, breath_phase: str, system_pulse: float):
        """Integration with harmonic_breath_field.py as core system governor"""
        try:
            from harmonic_breath_field import BreathPhase, SystemPulse
            
            # Map breath phase to tensor activation patterns
            phase_activations = {
                "INHALE": {"X": 0.9, "Y": 0.8, "Z": 0.6, "T": 0.7},
                "HOLD_IN": {"X": 1.0, "Y": 0.9, "Z": 0.8, "T": 0.5}, 
                "EXHALE": {"X": 0.7, "Y": 0.6, "Z": 0.9, "T": 0.8},
                "HOLD_OUT": {"X": 0.5, "Y": 0.5, "Z": 1.0, "T": 0.9},
                "TRANSITION": {"X": 0.6, "Y": 0.7, "Z": 0.7, "T": 1.0}
            }
            
            # Apply breath-synchronized activation
            if breath_phase.upper() in phase_activations:
                activations = phase_activations[breath_phase.upper()]
                
                for dim_str, level in activations.items():
                    dim_type = getattr(DimensionType, dim_str)
                    if dim_type in self.dimensional_controllers:
                        # Modulate activation by system pulse
                        modulated_level = level * (0.5 + 0.5 * system_pulse)
                        self.dimensional_controllers[dim_type].activate(modulated_level)
            
            # Update harmonic frequencies based on breath phase
            harmonic_multiplier = {
                "INHALE": 1.0,
                "HOLD_IN": PHI,  # Golden ratio expansion
                "EXHALE": 1.0 / PHI,  # Golden ratio contraction
                "HOLD_OUT": TAU / PHI,  # Sacred ratio
                "TRANSITION": 1.0
            }.get(breath_phase.upper(), 1.0)
            
            # Apply harmonic modulation to all nodes
            for node in self.nodes.values():
                if hasattr(node, 'harmonic_signature'):
                    node.harmonic_signature['base_frequency'] *= harmonic_multiplier
                    node.harmonic_signature['system_pulse'] = system_pulse
                    node.harmonic_signature['breath_phase'] = breath_phase
                    
            # Auto-spawn tensors during high-energy phases
            if breath_phase.upper() in ["HOLD_IN", "TRANSITION"] and system_pulse > 0.8:
                # Check for high-entropy regions that need spawning
                entropy = self.calculate_system_entropy()
                if entropy.composite_measure > self.entropy_threshold * 1.2:
                    # Find high-activity coordinates for spawning
                    max_activity = 0
                    spawn_coords = (self.dimensions//2, self.dimensions//2, 
                                  self.dimensions//2, int(time.time()) % self.dimensions)
                    
                    for coord, data in self.tensor_data.items():
                        if isinstance(data, dict) and 'activation_level' in data:
                            if data['activation_level'] > max_activity:
                                max_activity = data['activation_level']
                                spawn_coords = coord
                    
                    # Spawn child tensor
                    child = self.spawn_child_tensor(spawn_coords, "breath_field_triggered")
                    logger.info(f"Breath field triggered tensor spawn at {spawn_coords}")
            
            # Store breath field state
            self.breath_field_state = {
                "phase": breath_phase,
                "system_pulse": system_pulse,
                "last_update": time.time(),
                "harmonic_multiplier": harmonic_multiplier
            }
            
            return True
            
        except ImportError:
            logger.warning("harmonic_breath_field module not available - using fallback integration")
            # Fallback integration without import
            self.breath_field_state = {
                "phase": breath_phase,
                "system_pulse": system_pulse,
                "last_update": time.time(),
                "fallback_mode": True
            }
            return True
            
        except Exception as e:
            logger.error(f"Harmonic breath field integration failed: {e}")
            return False
    
    def auto_manage_spawns(self):
        """Automatically manage spawned tensors based on system state"""
        try:
            current_time = time.time()
            spawn_actions = []
            
            # Check each spawned tensor
            for spawn_id, spawn_info in list(self.spawn_registry.items()):
                tensor = spawn_info['tensor']
                age = current_time - spawn_info['spawn_time']
                
                # Calculate tensor health metrics
                entropy = tensor.calculate_system_entropy()
                activity_level = sum(1 for data in tensor.tensor_data.values() 
                                   if isinstance(data, dict) and data.get('activation_level', 0) > 0.1)
                
                # Decide spawn fate based on health and age
                if age > 300 and entropy.composite_measure < 0.1:  # 5 minutes, low entropy
                    # Mark for termination - tensor is stagnant
                    spawn_actions.append(("terminate", spawn_id, "stagnant"))
                    
                elif entropy.composite_measure > self.entropy_threshold * 1.5:
                    # High entropy - might need its own child spawn
                    if len(tensor.spawn_registry) == 0:  # Hasn't spawned yet
                        high_entropy_coords = (tensor.dimensions//2, tensor.dimensions//2, 
                                             tensor.dimensions//2, int(current_time) % tensor.dimensions)
                        grandchild = tensor.spawn_child_tensor(high_entropy_coords, "entropy_cascade")
                        spawn_actions.append(("cascade_spawn", spawn_id, grandchild))
                        
                elif activity_level > tensor.dimensions * 0.1:  # High activity
                    # Promote active tensor to independent status
                    spawn_actions.append(("promote", spawn_id, "high_activity"))
            
            # Execute spawn management actions
            for action, spawn_id, context in spawn_actions:
                if action == "terminate":
                    if spawn_id in self.spawn_registry:
                        del self.spawn_registry[spawn_id]
                        logger.info(f"Terminated spawn {spawn_id}: {context}")
                        
                elif action == "promote":
                    # Mark spawn as independent (no longer managed by parent)
                    if spawn_id in self.spawn_registry:
                        self.spawn_registry[spawn_id]["status"] = "independent"
                        logger.info(f"Promoted spawn {spawn_id}: {context}")
                        
                elif action == "cascade_spawn":
                    logger.info(f"Cascade spawn from {spawn_id}: {context}")
            
            return len(spawn_actions)
            
        except Exception as e:
            logger.error(f"Auto spawn management failed: {e}")
            return 0
    
    def sync_with_harmonic_governor(self):
        """Main synchronization method with harmonic_breath_field.py as core system governor"""
        try:
            from harmonic_breath_field import HarmonicFieldManager, BreathPhase
            
            # Initialize harmonic field manager if not present
            if not hasattr(self, 'harmonic_field_manager') or self.harmonic_field_manager is None:
                self.harmonic_field_manager = HarmonicFieldManager()
                logger.info("Initialized HarmonicFieldManager as core system governor")
            
            # Get current system pulse and breath phase from governor
            current_pulse = self.harmonic_field_manager.get_system_pulse()
            current_phase = self.harmonic_field_manager.get_current_phase()
            
            # Apply harmonic breath field integration
            self.integrate_harmonic_breath_field(current_phase.name, current_pulse)
            
            # Auto-manage spawns based on breath cycle
            spawn_actions = self.auto_manage_spawns()
            
            # Check if harmonic governor requests system rebalancing
            if hasattr(self.harmonic_field_manager, 'requires_rebalance') and self.harmonic_field_manager.requires_rebalance():
                self._perform_harmonic_rebalance()
            
            # Update entropy thresholds based on breath phase
            phase_entropy_multipliers = {
                "INHALE": 1.0,
                "HOLD_IN": 1.3,  # Higher threshold during concentration
                "EXHALE": 0.8,   # Lower threshold during release
                "HOLD_OUT": 0.6, # Lowest threshold during pause
                "TRANSITION": 1.2 # Moderate threshold during transition
            }
            
            multiplier = phase_entropy_multipliers.get(current_phase.name, 1.0)
            self.entropy_threshold = 2.5 * multiplier
            
            return {
                "sync_status": "success",
                "current_phase": current_phase.name,
                "system_pulse": current_pulse,
                "entropy_threshold": self.entropy_threshold,
                "spawn_actions": spawn_actions
            }
            
        except ImportError:
            logger.warning("harmonic_breath_field module not available - running in standalone mode")
            return {"sync_status": "standalone", "reason": "module_unavailable"}
            
        except Exception as e:
            logger.error(f"Harmonic governor synchronization failed: {e}")
            return {"sync_status": "error", "error": str(e)}
    
    def _perform_harmonic_rebalance(self):
        """Perform system rebalancing as requested by harmonic governor"""
        try:
            logger.info("Performing harmonic rebalance requested by system governor")
            
            # Rebalance dimensional activations based on current entropy
            entropy = self.calculate_system_entropy()
            
            # Calculate optimal activation levels for rebalancing
            target_activations = {
                DimensionType.X: min(1.0, entropy.shannon_entropy / 2.0),
                DimensionType.Y: min(1.0, entropy.multiscale_entropy / 3.0), 
                DimensionType.Z: min(1.0, entropy.permutation_entropy / 2.5),
                DimensionType.T: min(1.0, entropy.spectral_entropy / 2.0)
            }
            
            # Apply rebalanced activations
            for dim_type, target_level in target_activations.items():
                if dim_type in self.dimensional_controllers:
                    self.dimensional_controllers[dim_type].activate(target_level)
            
            # Compress dormant dimensions to free resources
            compressed_count = self.compress_dormant_dimensions()
            
            logger.info(f"Harmonic rebalance complete: compressed {compressed_count} dimensions")
            
        except Exception as e:
            logger.error(f"Harmonic rebalance failed: {e}")
    
    def get_harmonic_status(self) -> Dict[str, Any]:
        """Get comprehensive status of harmonic breath field integration"""
        status = {
            "harmonic_integration": "active" if hasattr(self, 'breath_field_state') and self.breath_field_state else "inactive",
            "last_sync": self.breath_field_state.get('last_update', 0) if self.breath_field_state else 0,
            "current_phase": self.breath_field_state.get('phase', 'unknown') if self.breath_field_state else 'unknown',
            "system_pulse": self.breath_field_state.get('system_pulse', 0.0) if self.breath_field_state else 0.0,
            "spawn_count": len(self.spawn_registry),
            "active_spawns": sum(1 for spawn_info in self.spawn_registry.values() 
                               if spawn_info.get('status') != 'terminated'),
            "entropy_threshold": self.entropy_threshold,
            "governor_available": hasattr(self, 'harmonic_field_manager') and self.harmonic_field_manager is not None
        }
        
        # Add spawn details
        if self.spawn_registry:
            status["spawns"] = {
                spawn_id: {
                    "age": time.time() - spawn_info['spawn_time'],
                    "trigger": spawn_info['spawn_trigger'],
                    "status": spawn_info.get('status', 'active'),
                    "data_points": spawn_info['data_inherited']
                }
                for spawn_id, spawn_info in self.spawn_registry.items()
            }
        
        return status
    
    @classmethod
    def _load_custom_binary(cls, filename: str) -> 'EnhancedARFSTensor':
        """Load from custom binary format with header"""
        with open(filename, 'rb') as f:
            # Read header (28 bytes total: 4+4+4+4+4+8)
            header_data = f.read(28)
            magic, version, dimensions, metadata_size, data_offset, checksum = struct.unpack('4sIIIIQ', header_data)
            
            # Verify magic number
            if magic != b'ARFS':
                raise ValueError("Invalid ARFS tensor file format")
            
            # Read and decompress metadata
            metadata_compressed = f.read(metadata_size)
            
            # Verify checksum
            calculated_checksum = zlib.adler32(metadata_compressed)
            if calculated_checksum != checksum:
                raise ValueError("Checksum mismatch in ARFS tensor file")
            
            # Decompress metadata
            metadata_json = zlib.decompress(metadata_compressed).decode('utf-8')
            metadata = json.loads(metadata_json)
        
        # Create tensor instance
        tensor = EnhancedARFSTensor(dimensions=metadata['dimensions'])
        tensor.sparse_threshold = metadata['sparse_threshold']
        
        # Restore dimensional controllers
        for dim_name, controller_data in metadata['dimensional_controllers'].items():
            dim_type = None
            for d_type in DimensionType:
                if d_type.value == dim_name:
                    dim_type = d_type
                    break
            if dim_type:
                controller = tensor.dimensional_controllers[dim_type]
                controller.activation_level = controller_data['activation_level']
                controller.state = ActivationState(controller_data['state'])
                controller.harmonic_frequency = controller_data['harmonic_frequency']
                controller.phase_offset = controller_data['phase_offset']
                controller.presence_signature = controller_data['presence_signature']
        
        # Restore nodes
        for node_id, node_data in metadata['nodes'].items():
            dim_affinity = DimensionType[node_data['dimension_affinity']]
            node = ARFSNode(node_id, dim_affinity)
            node.activation_level = node_data['activation_level']
            node.energy_level = node_data['energy_level']
            node.preservation_integrity = node_data['preservation_integrity']
            node.semantic_vector = node_data['semantic_vector']
            node.causal_links = set(node_data['causal_links'])
            node.observer_contexts = set(node_data['observer_contexts'])
            node.phase_coherence = node_data['phase_coherence']
            node.frequency_stability = node_data['frequency_stability']
            node.harmonic_signature = node_data['harmonic_signature']
            tensor.register_node(node)
        
        # Restore observers
        for observer_id, transform_data in metadata['observers'].items():
            transform = ObserverTransform(
                observer_id=observer_id,
                perspective_matrix=np.array(transform_data['perspective_matrix']),
                semantic_weights=transform_data['semantic_weights'],
                temporal_scale=transform_data['temporal_scale'],
                access_permissions=set(transform_data['access_permissions'])
            )
            tensor.observers[observer_id] = transform
        
        # Restore transition triggers
        for trigger_data in metadata['transition_triggers']:
            trigger = TransitionTrigger(
                trigger_type=trigger_data['trigger_type'],
                source_dimension=trigger_data['source_dimension'],
                threshold=trigger_data['threshold'],
                priority=trigger_data['priority']
            )
            # We can't safely eval condition function from file, so we'll skip it
            tensor.transition_triggers.append(trigger)
        
        # Skip to data section and read tensor data
        f.seek(data_offset)
        tensor_data = {}
        
        # Calculate how many entries we need to read based on remaining file size
        pos = f.tell()
        f.seek(0, 2)  # Go to end of file
        end_pos = f.tell()
        remaining_bytes = end_pos - pos
        f.seek(pos)   # Go back to data position
        
        entry_size = struct.calcsize('IIIIf')  # 4 integers + 1 float = 20 bytes
        num_entries = remaining_bytes // entry_size
        
        for _ in range(num_entries):
            data = f.read(entry_size)
            if len(data) < entry_size:
                break  # Reached end of file
            x, y, z, t, value = struct.unpack('IIIIf', data)
            tensor_data[(x, y, z, t)] = value
        
        tensor.tensor_data = tensor_data
        
        # The other sections (blockchain, spawn registry) would need to be stored differently
        # for the custom binary format to be fully compatible
        
        return tensor


# Example usage and demonstration
def example_advanced_processor(signal: Dict[str, Any], node: ARFSNode) -> Optional[Dict[str, Any]]:
    """Advanced example processor with dimensional awareness"""
    signal_value = signal.get("value", 0.0)
    signal_type = signal.get("type", "unknown")
    
    # Process based on node's dimensional affinity
    if node.dimension_affinity == DimensionType.X and signal_value > 0.7:
        # Execution dimension - generate computational response
        return {
            "src": node.node_id,
            "dst": signal.get("src", "broadcast"),
            "type": "computation_result",
            "timestamp": time.time(),
            "value": signal_value * 0.9,
            "dimension": "X",
            "computation": "executed_task"
        }
    
    elif node.dimension_affinity == DimensionType.Z and "symbolic" in signal_type:
        # Symbolic dimension - generate inference
        return {
            "src": node.node_id,
            "dst": "symbolic_network",
            "type": "inference",
            "timestamp": time.time(),
            "value": signal_value * 0.8,
            "dimension": "Z",
            "inference": "symbolic_pattern_detected"
        }
    
    return None


if __name__ == "__main__":
    # Demonstration of enhanced ARFS tensor
    print("=== Enhanced ARFS Tensor Demonstration ===")
    
    # Initialize tensor
    tensor = EnhancedARFSTensor(dimensions=100)
    
    # Register observers
    observer1 = tensor.register_observer("primary_observer", {"read", "write", "observe"})
    observer2 = tensor.register_observer("secondary_observer", {"read", "observe"})
    tensor.set_active_observer("primary_observer")
    
    # Create and register nodes with different dimensional affinities
    execution_node = ARFSNode("exec_node_1", DimensionType.X, example_advanced_processor)
    memory_node = ARFSNode("mem_node_1", DimensionType.Y)
    symbolic_node = ARFSNode("sym_node_1", DimensionType.Z, example_advanced_processor)
    temporal_node = ARFSNode("temp_node_1", DimensionType.T)
    
    for node in [execution_node, memory_node, symbolic_node, temporal_node]:
        tensor.register_node(node)
    
    print(f"Registered {len(tensor.nodes)} nodes across dimensions")
    
    # Activate different dimensions
    tensor.dimensional_controllers[DimensionType.X].activate(0.8)
    tensor.dimensional_controllers[DimensionType.Z].activate(0.6)
    
    # Transmit various signals
    signals = [
        ("exec_node_1", "mem_node_1", "computation", 0.8),
        ("sym_node_1", "exec_node_1", "symbolic_query", 0.7), 
        ("mem_node_1", "sym_node_1", "memory_recall", 0.6),
        ("temp_node_1", "exec_node_1", "temporal_sync", 0.9)
    ]
    
    print("\nTransmitting signals...")
    for src, dst, signal_type, value in signals:
        block = tensor.transmit_signal_enhanced(
            src, dst, signal_type, time.time(), value,
            observer_context="primary_observer"
        )
        print(f"  {signal_type}: {src} -> {dst} (value: {value})")
        time.sleep(0.1)  # Small delay for temporal patterns
    
    # Calculate system entropy
    entropy = tensor.calculate_system_entropy()
    print(f"\nSystem Entropy:")
    print(f"  Shannon: {entropy.shannon_entropy:.3f}")
    print(f"  Composite: {entropy.composite_measure:.3f}")
    
    # Detect patterns
    patterns = tensor.detect_activation_patterns()
    print(f"\nDetected {len(patterns)} activation patterns:")
    for pattern in patterns[:3]:  # Show first 3
        print(f"  {pattern['type']}: {pattern}")
    
    # Show system status
    status = tensor.get_system_status()
    print(f"\nSystem Status:")
    print(f"  Tensor density: {status['tensor_density']:.6f}")
    print(f"  Active nodes: {status['active_nodes']}")
    print(f"  Dimensional activation: {status['dimensional_activation']}")
    print(f"  Signal count: {status['signal_count']}")
    
    # Demonstrate compression
    compressed = tensor.compress_dormant_dimensions()
    print(f"\nCompressed {compressed} dormant dimensions")
    
    print("\n=== Enhanced ARFS Tensor Demonstration Complete ===")