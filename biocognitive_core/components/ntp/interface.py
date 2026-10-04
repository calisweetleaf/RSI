# src/biocognitive_core/components/ntp/interface.py
"""
Neural Transparency Protocol Interface Layer

Handles secure bidirectional neural communication with:
- Quantum-secured thought transmission
- Domain-restricted consent enforcement
- Adaptive signal encoding/decoding
"""

from dataclasses import dataclass, field
import hashlib
import hmac as _hmac
from typing import Dict, Any, Optional, List, Tuple, Union, AsyncGenerator
from biocognitive_core.components.ntp.encryption import QuantumSecureSignalProcessor
from pydantic import BaseModel, Field, validator, root_validator
from enum import Enum, auto
import asyncio
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes, serialization
import secrets
from biocognitive_core.config import settings
from biocognitive_core.exceptions import BiocognitiveError, ConsentDeniedError, QuantumEncryptionFailure
from biocognitive_core.metrics import NTPMetrics
import numpy as np
import logging
import uuid
import time

# Configure module logger
logger = logging.getLogger(__name__)


class BreathPhaseError(BiocognitiveError):
    """Raised when breath phase is incompatible with a requested transmission."""
    pass


class ThoughtDomain(Enum):
    """Cognitive domains for transmission control"""
    EMOTIONAL = "emotional"
    COGNITIVE = "cognitive"
    PHYSIOLOGICAL = "physiological"
    SPIRITUAL = "spiritual"

class NeuralSignal(BaseModel):
    """Raw neural signal representation"""
    timestamp: float = Field(default_factory=time.time)
    amplitude: float = Field(ge=0.0, le=1.0)
    frequency: float = Field(ge=0.1, le=100.0)
    domain: ThoughtDomain
    coherence: float = Field(ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "allow"

class ThoughtPacket(BaseModel):
    """Encoded thought for transmission"""
    content: bytes
    domain: ThoughtDomain
    sender: str
    receiver: str
    encryption_key: bytes
    signature: bytes
    timestamp: float = Field(default_factory=time.time)

class TransmissionProfile(BaseModel):
    """Secure transmission configuration"""
    sender: str = Field(default="")
    quantum_safety: str = Field(default=settings.neural.quantum_safety)
    allowed_domains: List[ThoughtDomain] = Field(default=settings.neural.allowed_domains)
    identity_mode: str = Field(default=settings.neural.identity_mode)
    encryption_key_length: int = Field(default=settings.security.quantum_key_length)
    
    @validator("allowed_domains")
    def validate_domains(cls, v):
        if not set(v).issubset(set(ThoughtDomain.__members__.values())):
            raise ValueError("Invalid thought domains specified")
        return v

class TransmissionType(Enum):
    THOUGHT = auto()
    EMOTION = auto()
    SENSATION = auto()
    MEMORY = auto()
    DREAM = auto()
    INTENTION = auto()

class ConsentLevel(Enum):
    NONE = 0
    BASIC = 1
    STANDARD = 2
    ENHANCED = 3
    FULL = 4

@dataclass
class ThoughtPattern:
    """Representation of a thought pattern for transmission"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    transmission_type: TransmissionType = TransmissionType.THOUGHT
    timestamp: float = field(default_factory=time.time)

@dataclass
class TransmissionChannel:
    """Secure channel for thought transmission"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str = ""
    receiver_id: str = ""
    encryption_level: int = 3
    consent_verification: bool = True
    active: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

class NeuralInterface:
    """Core interface for neural transparency operations"""
    def __init__(self, user_profile: TransmissionProfile):
        from biocognitive_core.components.ntp.consent import ConsentManagementEngine as _CME
        self.profile = user_profile
        self.key_pair = self._generate_quantum_key()
        self.signal_processor = QuantumSecureSignalProcessor()
        self.consent_engine = _CME()
        self.metrics_collector = NTPMetrics()
        self.channels: Dict[str, TransmissionChannel] = {}
        self.active_connections: List[str] = []
        self.consent_manager = ConsentManager(user_profile.sender)
        # ROSEMARY integration: Connect to breath phase system
        self.breath_phase_sync = BreathPhaseSync()
        self.dream_integration = DreamPhaseIntegration()
        self._initialize_interface()

    def _initialize_interface(self) -> None:
        """Validate profile, wire up transmission queue, and register with metrics."""
        sender = self.profile.sender or "<anonymous>"
        logger.info("Initializing neural interface for '%s'", sender)

        # Validate domain list
        for domain in self.profile.allowed_domains:
            if not isinstance(domain, ThoughtDomain):
                raise ValueError(f"Invalid domain in profile: {domain!r}")

        # Async transmission queue (bounded to avoid runaway memory under backpressure)
        self._transmission_queue: asyncio.Queue = asyncio.Queue(maxsize=1024)
        self._transmission_log: List[Dict[str, Any]] = []

        # Register with metrics system
        self.metrics_collector.track_event("interface_initialized", {
            "sender": sender,
            "quantum_safety": self.profile.quantum_safety,
            "domain_count": len(self.profile.allowed_domains),
        })

        logger.info(
            "Neural interface ready — quantum_safety=%s, domains=%s",
            self.profile.quantum_safety,
            [d.value for d in self.profile.allowed_domains],
        )

    def _generate_quantum_key(self) -> Tuple[ec.EllipticCurvePrivateKey, ec.EllipticCurvePublicKey]:
        """Generate a proper EC key pair for the configured security level."""
        if self.profile.quantum_safety == "QRL3":
            private = ec.generate_private_key(ec.SECP521R1())
        elif self.profile.quantum_safety == "QRL2":
            private = ec.generate_private_key(ec.SECP384R1())
        else:
            private = ec.generate_private_key(ec.SECP256R1())
        return private, private.public_key()

    def create_channel(self, receiver_id: str, encryption_level: int = 3) -> str:
        """Create a new transmission channel"""
        channel = TransmissionChannel(
            sender_id=self.profile.sender,
            receiver_id=receiver_id,
            encryption_level=encryption_level
        )
        self.channels[channel.id] = channel
        return channel.id

    def close_channel(self, channel_id: str) -> bool:
        """Close an existing transmission channel"""
        if channel_id in self.channels:
            self.channels[channel_id].active = False
            return True
        return False

    async def transmit_thought(self, thought: NeuralSignal, recipient: str):
        """
        Securely transmit thought packet with domain validation and consent checking
        
        >>> interface = NeuralInterface(TransmissionProfile())
        >>> signal = NeuralSignal(domain=ThoughtDomain.COGNITIVE)
        >>> await interface.transmit_thought(signal, "user123")
        """
        if not self.consent_engine.check_consent(self.profile.sender, recipient):
            raise ConsentDeniedError(
                f"Recipient {recipient} not in allowed domains",
                code="NTP-002",
                domains=self.profile.allowed_domains
            )
            
        if not self._validate_domain(thought.domain):
            raise ConsentDeniedError(
                f"Domain {thought.domain} not permitted",
                code="NTP-003",
                domains=self.profile.allowed_domains
            )

        try:
            packet = await self._encode_thought(thought, recipient)
            await self._secure_transmission(packet)
            self.metrics_collector.track_transmission(self.profile.sender, packet.timestamp - thought.timestamp)
        except Exception as e:
            self.metrics_collector.track_event("transmission_failure", {"error": str(e)})
            raise

    async def _encode_thought(self, signal: NeuralSignal, recipient: str) -> ThoughtPacket:
        """Convert neural signal to encrypted thought packet"""
        encoded = self.signal_processor.encode_signal(signal)
        encryption_key = self._derive_shared_key(recipient)
        
        return ThoughtPacket(
            content=encoded,
            domain=signal.domain,
            sender=self.profile.sender,
            receiver=recipient,
            encryption_key=encryption_key,
            signature=self._sign_packet(encoded, encryption_key)
        )

    def _derive_shared_key(self, recipient: str) -> bytes:
        """Derive a quantum-safe shared key bound to the recipient identity."""
        try:
            key_len = max(16, self.profile.encryption_key_length // 8)

            if self.profile.quantum_safety == "QRL3":
                # Full quantum resistance: deterministic key from private key bytes + recipient
                private_bytes = self.key_pair[0].private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                )
                return HKDF(
                    algorithm=hashes.SHA3_512(),
                    length=key_len,
                    salt=recipient.encode(),
                    info=b"neural-transparency-key-qrl3",
                ).derive(private_bytes)

            # QRL2 / QRL1: ECDH exchange with an ephemeral peer key (same curve)
            curve = self.key_pair[0].curve
            ephemeral_peer = ec.generate_private_key(curve)
            shared_secret = self.key_pair[0].exchange(ec.ECDH(), ephemeral_peer.public_key())
            return HKDF(
                algorithm=hashes.SHA3_512(),
                length=key_len,
                salt=recipient.encode(),
                info=b"neural-transparency-key",
            ).derive(shared_secret)

        except Exception as exc:
            raise QuantumEncryptionFailure(
                f"Key derivation failed: {exc}",
                code="NTP-005",
                retry_count=0,
            ) from exc

    async def _secure_transmission(self, packet: ThoughtPacket):
        """
        Queue the encrypted packet with HMAC integrity check and exponential-backoff retry.

        The packet is enqueued into self._transmission_queue (bounded asyncio.Queue).
        Integrity is verified via HMAC-SHA256 before enqueue so corrupted packets are
        rejected without consuming queue capacity. Up to 3 retries with 0.1 / 0.2 / 0.4s
        backoff are attempted on transient failures.
        """
        max_retries = 3
        base_delay = 0.1

        for attempt in range(max_retries + 1):
            try:
                # HMAC integrity check: verify the packet hasn't been tampered with
                integrity_key = hashlib.sha256(
                    packet.encryption_key + packet.sender.encode()
                ).digest()
                expected_mac = _hmac.new(integrity_key, packet.content, hashlib.sha256).digest()
                if not _hmac.compare_digest(packet.signature[:32], expected_mac[:32]):
                    raise QuantumEncryptionFailure(
                        "Packet integrity check failed — signature mismatch",
                        code="NTP-006",
                        retry_count=attempt,
                    )

                # Enqueue (non-blocking — raises asyncio.QueueFull if at capacity)
                self._transmission_queue.put_nowait(packet)

                # Record successful transmission
                self.metrics_collector.track_encryption(
                    self.profile.sender, self.profile.quantum_safety
                )
                self._transmission_log.append({
                    "timestamp": time.time(),
                    "sender": packet.sender,
                    "receiver": packet.receiver,
                    "domain": packet.domain.value,
                    "attempt": attempt,
                })
                return

            except asyncio.QueueFull:
                if attempt >= max_retries:
                    raise QuantumEncryptionFailure(
                        "Transmission queue full — backpressure exceeded",
                        code="NTP-010",
                        retry_count=attempt,
                    )
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    "Transmission queue full (attempt %d), retrying in %.2fs",
                    attempt + 1, delay,
                )
                await asyncio.sleep(delay)

            except QuantumEncryptionFailure:
                raise  # Do not retry integrity failures

    def _sign_packet(self, content: bytes, key: bytes) -> bytes:
        """
        HMAC-SHA256 signature over packet content, keyed by sender identity.
        Constant-time verifiable by the receiver without a PKI exchange.
        """
        sign_key = hashlib.sha256(self.profile.sender.encode()).digest()
        return _hmac.new(sign_key, content, hashlib.sha256).digest()

    def _validate_domain(self, domain: ThoughtDomain) -> bool:
        """Check if domain is allowed by profile"""
        return domain in self.profile.allowed_domains

class ConsentManager:
    """Manages consent for neural transmissions"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.consent_registry: Dict[str, Dict[TransmissionType, ConsentLevel]] = {}
    
    def register_consent(self, target_id: str, 
                        transmission_type: TransmissionType,
                        level: ConsentLevel) -> bool:
        """Register consent for a specific user and transmission type"""
        if target_id not in self.consent_registry:
            self.consent_registry[target_id] = {}
        self.consent_registry[target_id][transmission_type] = level
        return True
    
    def verify_consent(self, target_id: str, 
                      transmission_type: TransmissionType,
                      required_level: ConsentLevel = ConsentLevel.STANDARD) -> bool:
        """Verify if consent has been granted for a specific transmission"""
        if target_id not in self.consent_registry:
            return False
        if transmission_type not in self.consent_registry[target_id]:
            return False
        return self.consent_registry[target_id][transmission_type].value >= required_level.value
    
    def revoke_consent(self, target_id: str, 
                      transmission_type: Optional[TransmissionType] = None) -> bool:
        """Revoke consent for a specific user and transmission type"""
        if target_id not in self.consent_registry:
            return False
        
        if transmission_type is None:
            # Revoke all consent types for this user
            self.consent_registry[target_id] = {}
        elif transmission_type in self.consent_registry[target_id]:
            del self.consent_registry[target_id][transmission_type]
            
        return True

# ROSEMARY Integration Components
class BreathPhaseSync:
    """Synchronizes neural interface operations with breath phases"""
    
    def __init__(self):
        self.current_phase = None
        self.breath_synchronizer = None
        self._initialize_sync()
    
    def _initialize_sync(self):
        """Initialize synchronization with breath phase system (graceful degradation)."""
        for module_path in (
            "rosemary_integration.breath_phase",
            "ROSEMARY_updates.breath_phase",
        ):
            try:
                import importlib
                mod = importlib.import_module(module_path)
                get_sync = getattr(mod, "get_sacred_breath_synchronizer", None)
                if get_sync is None:
                    continue
                self.breath_synchronizer = get_sync()
                self.breath_synchronizer.register_component("ntp_interface", self)
                logger.info("NTP interface connected to Sacred Breath Synchronizer (%s)", module_path)
                return
            except Exception as exc:
                logger.debug("Breath sync init via %s failed: %s", module_path, exc)
        logger.warning("Breath synchronizer unavailable — NTP running without breath sync")
            
    def synchronize_with_breath(self, phase: str) -> None:
        """Callback method for breath synchronizer updates"""
        self.current_phase = phase
        logger.debug(f"NTP Interface synchronized to breath phase: {phase}")

    async def wait_for_optimal_phase(self, transmission_type: TransmissionType, 
                                   timeout: float = 5.0) -> bool:
        """Wait until breath phase is optimal for transmission"""
        optimal_phase = self.get_optimal_phase(transmission_type)
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.current_phase == optimal_phase:
                return True
            if self.breath_synchronizer:
                # Use the breath synchronizer's phase information
                current_phase = self.breath_synchronizer.get_current_phase().name
                if current_phase == optimal_phase:
                    return True
            await asyncio.sleep(0.1)
            
        return False

    def verify_transmission_compatibility(self, thought: ThoughtPattern) -> bool:
        """
        Return True when the current breath phase is compatible with this transmission type.
        Degrades gracefully — allows transmission when phase is unknown or sync unavailable.
        """
        if self.breath_synchronizer is None:
            return True  # No sync available — allow all

        optimal = self.get_optimal_phase(thought.transmission_type)
        current = None

        try:
            phase_obj = self.breath_synchronizer.get_current_phase()
            current = phase_obj.name if hasattr(phase_obj, "name") else str(phase_obj)
        except Exception:
            pass

        if current is None:
            current = self.current_phase

        if current is None:
            return True  # Phase unknown — allow

        compatible = current.upper() == optimal.upper()
        if not compatible:
            logger.debug(
                "Breath phase mismatch: current=%s optimal=%s for %s",
                current, optimal, thought.transmission_type.value,
            )
        return compatible
    
    def get_optimal_phase(self, transmission_type: TransmissionType) -> str:
        """Get the optimal breath phase for a specific transmission type"""
        phase_map = {
            TransmissionType.THOUGHT: "INHALE",
            TransmissionType.EMOTION: "HOLD",
            TransmissionType.SENSATION: "EXHALE",
            TransmissionType.MEMORY: "PAUSE_RISING",
            TransmissionType.DREAM: "DREAM",
            TransmissionType.INTENTION: "PAUSE_FALLING"
        }
        return phase_map.get(transmission_type, "REST")

class DreamPhaseIntegration:
    """Integrates with dream phase processing for relevant thought patterns"""
    
    def __init__(self):
        self.active = False
        self.dream_processors = {}
        self._initialize_integration()
    
    def _initialize_integration(self):
        """Initialize integration with dream phase system"""
        logger.info("Initializing dream phase integration")
        self.active = True
    
    def process_transmission(self, thought: ThoughtPattern) -> None:
        """Process a thought transmission for dream phase integration"""
        if not self.active:
            return
            
        # Different processing based on transmission type
        if thought.transmission_type == TransmissionType.DREAM:
            self._process_dream_content(thought)
        elif thought.transmission_type == TransmissionType.MEMORY:
            self._process_memory_content(thought)
    
    def _process_dream_content(self, thought: ThoughtPattern) -> None:
        """
        Tokenise dream content, timestamp it, and store in the integration buffer.
        Tokens are extracted by splitting on whitespace and filtering short words
        (>3 chars) — a lightweight symbolic decomposition compatible with the
        recursive DNA encoding layer without requiring an NLP dependency.
        """
        if not self.active:
            return

        if isinstance(thought.content, dict):
            raw = str(thought.content.get("text", thought.content))
        elif isinstance(thought.content, (bytes, bytearray)):
            raw = thought.content.decode("utf-8", errors="replace")
        else:
            raw = str(thought.content)

        tokens = [w for w in raw.split() if len(w) > 3]

        entry = {
            "type": "dream",
            "thought_id": thought.id,
            "transmission_type": thought.transmission_type.value,
            "tokens": tokens,
            "token_count": len(tokens),
            "timestamp": thought.timestamp,
            "processed_at": time.time(),
        }

        bucket = self.dream_processors.setdefault("dream", [])
        bucket.append(entry)
        if len(bucket) > 50:
            bucket.pop(0)

        logger.debug("Dream content processed: %d tokens, thought_id=%s", len(tokens), thought.id)

    def _process_memory_content(self, thought: ThoughtPattern) -> None:
        """
        Extract memory keys from the thought payload and store them with a 1-hour
        expiry for later retrieval by the memory integration layer.
        """
        if not self.active:
            return

        memory_keys: List[str] = []
        content_snapshot: Dict[str, Any] = {}
        if isinstance(thought.content, dict):
            memory_keys = list(thought.content.keys())
            content_snapshot = {
                k: v for k, v in thought.content.items()
                if isinstance(v, (str, int, float, bool))
            }

        entry = {
            "type": "memory",
            "thought_id": thought.id,
            "memory_keys": memory_keys,
            "content_snapshot": content_snapshot,
            "timestamp": thought.timestamp,
            "expires_at": time.time() + 3600,
        }

        bucket = self.dream_processors.setdefault("memory", [])
        # Prune expired entries first
        now = time.time()
        bucket[:] = [e for e in bucket if e.get("expires_at", 0) > now]
        bucket.append(entry)

        logger.debug(
            "Memory content processed: %d keys stored (1h expiry), thought_id=%s",
            len(memory_keys), thought.id,
        )