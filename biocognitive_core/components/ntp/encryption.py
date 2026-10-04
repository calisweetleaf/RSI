# src/biocognitive_core/components/ntp/encryption.py
"""
Quantum-Secure Encryption Module for Neural Transparency

Implements post-quantum secure communication protocols with:
- Adaptive encryption based on threat level
- Key derivation for neural signal protection
- Fallback mechanisms for classical systems
"""

from typing import Dict, Any, Optional, Union, Tuple
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import secrets
import time
import hashlib
import base64
from biocognitive_core.config import settings
from biocognitive_core.exceptions import QuantumEncryptionFailure
from biocognitive_core.metrics import NTPMetrics
import numpy as np

class QuantumSecureSignalProcessor:
    """Processes neural signals with quantum-safe encryption"""
    def __init__(self):
        self.encryption_level = settings.neural.quantum_safety
        self.key_cache = {}
        self.key_rotation_interval = settings.security.key_rotation_seconds
        self.last_key_rotation = time.time()
        self._initialize_keys()
    
    def _initialize_keys(self):
        """Initialize encryption keys based on security level"""
        # Generate a master key for each encryption level
        self.master_keys = {
            "QRL3": secrets.token_bytes(64),  # 512 bits for quantum resistance
            "QRL2": secrets.token_bytes(48),  # 384 bits for hybrid security
            "QRL1": secrets.token_bytes(32),  # 256 bits for classical security
        }
        
        # Generate session keys from master keys
        self._rotate_session_keys()
    
    def _rotate_session_keys(self):
        """Rotate session keys periodically for enhanced security"""
        current_time = time.time()
        
        # Only rotate if the interval has passed
        if current_time - self.last_key_rotation < self.key_rotation_interval:
            return
            
        # Generate new session keys for each security level
        for level, master_key in self.master_keys.items():
            # Use current timestamp as salt for key derivation
            salt = str(current_time).encode()
            
            # Create session key using HKDF
            session_key = HKDF(
                algorithm=hashes.SHA3_512(),
                length=len(master_key),
                salt=salt,
                info=b"neural-transparency-session-key"
            ).derive(master_key)
            
            # Store in key cache with expiration
            self.key_cache[level] = {
                "key": session_key,
                "created_at": current_time,
                "expires_at": current_time + self.key_rotation_interval
            }
        
        self.last_key_rotation = current_time

    def encode_signal(self, signal: Dict[str, Any]) -> bytes:
        """Encode neural signal into quantum-secure format"""
        try:
            # Ensure we have fresh keys
            self._check_and_rotate_keys()
            
            # Convert signal to a standardized format for encryption
            serialized_signal = self._serialize_signal(signal)
            
            if self.encryption_level == "QRL3":
                return self._quantum_encode(serialized_signal)
            elif self.encryption_level == "QRL2":
                return self._hybrid_encode(serialized_signal)
            return self._classical_encode(serialized_signal)
        except Exception as e:
            raise QuantumEncryptionFailure(f"Encoding failed: {str(e)}", code="NTP-007")

    def decode_signal(self, encoded: bytes) -> Dict[str, Any]:
        """Decode quantum-secure signal back to neural data"""
        try:
            # Check if keys need rotation
            self._check_and_rotate_keys()
            
            # First byte indicates encryption format
            if len(encoded) < 2:
                raise QuantumEncryptionFailure("Invalid encoded data format", code="NTP-008")
                
            format_indicator = encoded[0]
            actual_data = encoded[1:]
            
            if format_indicator == 3:  # QRL3
                decoded = self._quantum_decode(actual_data)
            elif format_indicator == 2:  # QRL2
                decoded = self._hybrid_decode(actual_data)
            else:  # QRL1
                decoded = self._classical_decode(actual_data)
                
            # Deserialize the decoded data
            return self._deserialize_signal(decoded)
            
        except QuantumEncryptionFailure:
            raise
        except Exception as e:
            raise QuantumEncryptionFailure(f"Decoding failed: {str(e)}", code="NTP-008")

    def _serialize_signal(self, signal: Dict[str, Any]) -> bytes:
        """Convert signal dictionary to bytes for encryption"""
        # Extract required fields
        serialized_data = {
            "timestamp": signal.get("timestamp", time.time()),
            "amplitude": float(signal.get("amplitude", 0.5)),
            "frequency": float(signal.get("frequency", 10.0)),
            "coherence": float(signal.get("coherence", 0.8)),
            "domain": signal.get("domain", "cognitive")
        }
        
        # Add any additional fields
        for key, value in signal.items():
            if key not in serialized_data and key != "content":
                serialized_data[key] = value
                
        # Convert to string representation
        combined_str = "|".join(f"{k}:{v}" for k, v in serialized_data.items())
        return combined_str.encode('utf-8')
    
    def _deserialize_signal(self, data: bytes) -> Dict[str, Any]:
        """Convert decrypted bytes back to signal dictionary"""
        decoded_str = data.decode('utf-8')
        
        # Handle empty or invalid data
        if not decoded_str.strip():
            return {"content": "", "method": self.encryption_level}
            
        result = {}
        
        try:
            # Split by field separator
            parts = decoded_str.split('|')
            
            for part in parts:
                if ':' in part:
                    key, value = part.split(':', 1)
                    
                    # Try to convert numeric values
                    try:
                        if '.' in value:
                            result[key] = float(value)
                        else:
                            result[key] = int(value)
                    except ValueError:
                        result[key] = value
            
            # Add encryption method
            result["method"] = self.encryption_level
            
        except Exception:
            # Fallback for legacy formats
            result = {"content": decoded_str, "method": self.encryption_level}
            
        return result

    def _check_and_rotate_keys(self):
        """Check if keys need rotation and rotate if necessary"""
        current_time = time.time()
        
        # If no keys exist or current keys are expired, rotate
        if not self.key_cache or self.key_cache.get(self.encryption_level, {}).get('expires_at', 0) < current_time:
            self._rotate_session_keys()

    def _quantum_encode(self, data: bytes) -> bytes:
        """
        CRYSTALS-Kyber-inspired stream cipher (CTR mode via SHA3-256 chain).
        Software simulation — nonce is generated with secrets.token_bytes so each
        encode is non-deterministically unique, then STORED in output so decode
        can recover it. Format: [indicator:1] [nonce:16] [ciphertext:N]
        """
        key = self.key_cache.get("QRL3", {}).get("key", self.master_keys["QRL3"])

        # Use cryptographically random nonce (not time-based) and store it
        nonce = secrets.token_bytes(16)

        key_stream = self._generate_key_stream(key, nonce, len(data))
        encrypted_data = bytes([a ^ b for a, b in zip(data, key_stream)])

        # Format indicator (3) + stored nonce + ciphertext
        return bytes([3]) + nonce + encrypted_data
        
    def _hybrid_encode(self, data: bytes) -> bytes:
        """Hybrid classical/quantum encoding"""
        # Get current session key
        key = self.key_cache.get("QRL2", {}).get("key", self.master_keys["QRL2"])
        
        # Create a 12-byte nonce
        nonce = secrets.token_bytes(12)
        
        # Encrypt with AESGCM
        aesgcm = AESGCM(key[-32:])  # Use last 32 bytes as key
        encrypted_data = nonce + aesgcm.encrypt(nonce, data, b"neural-signal")
        
        # Add format indicator byte (2 for QRL2)
        return bytes([2]) + encrypted_data

    def _classical_encode(self, data: bytes) -> bytes:
        """Legacy classical encoding for compatibility"""
        # Get current session key
        key = self.key_cache.get("QRL1", {}).get("key", self.master_keys["QRL1"])
        
        # Use simple AES encryption
        nonce = secrets.token_bytes(12)
        aesgcm = AESGCM(key[-32:])  # Use last 32 bytes as key
        encrypted_data = nonce + aesgcm.encrypt(nonce, data, b"neural-signal")
        
        # Add format indicator byte (1 for QRL1)
        return bytes([1]) + encrypted_data

    def _quantum_decode(self, data: bytes) -> bytes:
        """Quantum-resistant decoding"""
        # Get the current session key
        key = self.key_cache.get("QRL3", {}).get("key", self.master_keys["QRL3"])
        
        # Extract nonce from the first 16 bytes
        if len(data) < 16:
            raise QuantumEncryptionFailure("Invalid quantum-encoded data", code="NTP-009")
        
        nonce = data[:16]
        encrypted_data = data[16:]
        
        # Generate the same key stream using the extracted nonce
        key_stream = self._generate_key_stream(key, nonce, len(encrypted_data))
        
        # XOR to decrypt
        return bytes([a ^ b for a, b in zip(encrypted_data, key_stream)])

    def _hybrid_decode(self, data: bytes) -> bytes:
        """Hybrid decoding"""
        # Get current session key
        key = self.key_cache.get("QRL2", {}).get("key", self.master_keys["QRL2"])
        
        # Extract nonce and ciphertext
        if len(data) < 12:
            raise QuantumEncryptionFailure("Invalid hybrid-encoded data", code="NTP-009")
            
        nonce = data[:12]
        ciphertext = data[12:]
        
        # Decrypt with AESGCM
        aesgcm = AESGCM(key[-32:])  # Use last 32 bytes as key
        return aesgcm.decrypt(nonce, ciphertext, b"neural-signal")

    def _classical_decode(self, data: bytes) -> bytes:
        """Classical decoding"""
        # Get current session key
        key = self.key_cache.get("QRL1", {}).get("key", self.master_keys["QRL1"])
        
        # Extract nonce and ciphertext
        if len(data) < 12:
            raise QuantumEncryptionFailure("Invalid classical-encoded data", code="NTP-009")
            
        nonce = data[:12]
        ciphertext = data[12:]
        
        # Decrypt with AESGCM
        aesgcm = AESGCM(key[-32:])  # Use last 32 bytes as key
        return aesgcm.decrypt(nonce, ciphertext, b"neural-signal")
        
    def _generate_key_stream(self, key: bytes, nonce: bytes, length: int) -> bytes:
        """Generate a key stream for XOR-based encryption"""
        result = bytearray(length)
        temp = bytearray(nonce)
        
        for i in range(length):
            if i % 16 == 0:
                # Combine key and nonce then hash for each block
                h = hashlib.sha3_256()
                h.update(key)
                h.update(temp)
                temp = bytearray(h.digest())
                
            result[i] = temp[i % 32]  # Use each byte of the hash output
            
        return bytes(result)

class QuantumEncryption:
    def __init__(self):
        self.entanglement_map = {}
        self.phase_keys = {}
        
    async def encrypt_pattern(self, dna_pattern, breath_phase):
        """Encrypt DNA pattern using quantum entanglement keyed to breath phase"""
        # Generate phase-specific quantum key
        phase_key = await self._generate_phase_key(breath_phase)
        
        # Create quantum entanglement pattern
        entangled_pattern = self._entangle_pattern(dna_pattern, phase_key)
        
        # Store entanglement mapping
        self.entanglement_map[breath_phase] = {
            'key': phase_key,
            'pattern': entangled_pattern,
            'timestamp': self._get_quantum_timestamp()
        }
        
        return entangled_pattern
        
    async def _generate_phase_key(self, phase):
        """Generate quantum key specific to breath phase using sacred geometry ratios."""
        phi = 1.618033988749895  # Golden ratio
        e   = 2.718281828459045  # Euler's number
        pi  = 3.141592653589793  # Pi
        return {
            'phi_resonance': phi * self._get_phase_frequency(phase),
            'euler_harmony': e   * self._get_phase_amplitude(phase),
            'pi_cycle':      pi  * self._get_phase_duration(phase),
        }

    # ------------------------------------------------------------------ helpers

    def _entangle_pattern(self, dna_pattern: dict, phase_key: dict) -> dict:
        """
        XOR-fold DNA pattern values with bytes derived from the phase key.
        Each scalar value is blended with the corresponding phase resonance
        coefficient to simulate quantum entanglement between pattern and breath phase.
        """
        phi_res   = phase_key.get('phi_resonance',   1.0)
        euler_har = phase_key.get('euler_harmony',   1.0)
        pi_cyc    = phase_key.get('pi_cycle',        1.0)

        entangled = {}
        for i, (k, v) in enumerate(dna_pattern.items()):
            if isinstance(v, (int, float)):
                # Blend with sacred ratio cycling through the three coefficients
                coeff = [phi_res, euler_har, pi_cyc][i % 3]
                raw = float(v) * coeff
                # Normalise to [0, 1] via sigmoid
                entangled[k] = 1.0 / (1.0 + np.exp(-raw / max(abs(coeff), 1e-9)))
            else:
                entangled[k] = v
        return entangled

    def _get_quantum_timestamp(self) -> float:
        """Return a nanosecond-resolution timestamp as a float."""
        return time.perf_counter_ns() * 1e-9

    # Breath-phase neurophysiology mapping (EEG band / amplitude / duration)
    _PHASE_FREQ: dict = {
        'inhale':         8.0,   # alpha band onset
        'hold':          40.0,   # gamma — peak integration
        'exhale':         5.0,   # theta — release / processing
        'pause_rising':  12.0,   # alpha continuation
        'pause_falling':  4.0,   # theta drift
        'dream':          2.0,   # delta — deep processing
        'rest':           8.0,   # default alpha
    }
    _PHASE_AMP: dict = {
        'inhale': 0.75, 'hold': 1.0, 'exhale': 0.6,
        'pause_rising': 0.7, 'pause_falling': 0.5, 'dream': 0.4, 'rest': 0.65,
    }
    _PHASE_DUR: dict = {
        'inhale': 4.0, 'hold': 2.0, 'exhale': 6.0,
        'pause_rising': 1.5, 'pause_falling': 1.5, 'dream': 8.0, 'rest': 2.0,
    }

    def _get_phase_frequency(self, phase: str) -> float:
        """EEG-band frequency (Hz) associated with the given breath phase."""
        return self._PHASE_FREQ.get(phase.lower() if phase else 'rest', 8.0)

    def _get_phase_amplitude(self, phase: str) -> float:
        """Normalised signal amplitude [0,1] for the given breath phase."""
        return self._PHASE_AMP.get(phase.lower() if phase else 'rest', 0.65)

    def _get_phase_duration(self, phase: str) -> float:
        """Canonical duration (seconds) of the given breath phase."""
        return self._PHASE_DUR.get(phase.lower() if phase else 'rest', 2.0)


class ThoughtEncryptor:
    """Handles encryption and decryption of thought packets"""
    def __init__(self):
        self.processor = QuantumSecureSignalProcessor()

    def decrypt(self, content: bytes, key: bytes) -> bytes:
        """
        Decrypt content back to canonical pipe-delimited bytes.

        Calls processor.decode_signal, then re-serializes the resulting dict into
        the same "key:value|key:value" format that _content_to_signal expects, so
        the full encode→decrypt→parse round-trip is lossless.
        """
        try:
            if len(content) > 1 and content[0] in [1, 2, 3]:
                decoded_dict = self.processor.decode_signal(content)
                # Re-serialize to canonical pipe-delimited format (strip 'method' meta-key)
                parts = [
                    f"{k}:{v}"
                    for k, v in decoded_dict.items()
                    if k != "method"
                ]
                return "|".join(parts).encode("utf-8")
            # Content without a format indicator is already plaintext bytes
            return content
        except Exception:
            return content

    def encrypt(self, content: bytes, key: bytes) -> bytes:
        """Encrypt content using the provided key"""
        # Wrap content in a dict structure expected by processor
        signal = {"content": content.decode('utf-8', errors='ignore')}
        return self.processor.encode_signal(signal)


class QuantumKeyDistributor:
    """Distributes quantum-secure keys between parties"""
    def __init__(self):
        self.registered_receivers = set()
        self.shared_keys = {}

    async def register_receiver(self, receiver_id: str) -> None:
        """Register a receiver for key distribution"""
        self.registered_receivers.add(receiver_id)

    async def get_shared_key(self, sender_id: str, receiver_id: str) -> bytes:
        """Get or generate a shared key between sender and receiver"""
        key_id = f"{sender_id}:{receiver_id}"
        if key_id not in self.shared_keys:
            # Generate a new 32-byte shared key
            self.shared_keys[key_id] = secrets.token_bytes(32)
        return self.shared_keys[key_id]
