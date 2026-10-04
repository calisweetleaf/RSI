# src/biocognitive_core/components/ntp/receiver.py
"""
Neural Transparency Protocol Receiver Implementation

Handles secure reception and processing of neural signals with:
- Quantum-decrypted thought reception
- Real-time signal quality monitoring
- Adaptive neural signal decoding
- Session management for continuous transmission

Author: Morpheus
Date: 2025-05-08
Version: 1.0.0
Description: This module implements the receiver component of the Neural Transparency Protocol (NTP).
It handles the secure reception of neural signals, decryption, and processing for integration with
the host's cognitive systems. The receiver includes real-time monitoring of signal quality and
adaptive decoding algorithms.
ID: NTP-004
SHA-256: fc3e2d5g6h7i8j9k0l1m2n3o4p5q6r7s8t9u0v1w2x3y4z5a6b7c8d9e0f1g2h3i4j5
"""

import asyncio
import hashlib
import hmac as _hmac
import logging
import struct
import time
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union, AsyncGenerator, Callable, Any
from datetime import datetime, timedelta
import numpy as np
import uuid
from pydantic import BaseModel, Field, validator, root_validator
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

from biocognitive_core.config import settings
from biocognitive_core.exceptions import (
    BiocognitiveError, 
    ConsentDeniedError, 
    QuantumEncryptionFailure,
    IdentityDissolutionRisk
)
from biocognitive_core.metrics import NTPMetrics

from .interface import (
    ThoughtDomain, 
    NeuralSignal, 
    ThoughtPacket, 
    TransmissionProfile
)
from .encryption import ThoughtEncryptor, QuantumKeyDistributor
from .consent import ConsentManagementEngine, ConsentDomain, ConsentLevel

logger = logging.getLogger(__name__)

class ReceiverMode(Enum):
    """Operating modes for the neural receiver"""
    PASSIVE = "passive"       # Listen only, minimal processing
    ACTIVE = "active"         # Actively process incoming thoughts
    SELECTIVE = "selective"   # Process only specific domains/senders
    EMERGENCY = "emergency"   # Emergency override mode (high priority)
    DORMANT = "dormant"       # Minimal power, only wake on specific patterns

class SignalQuality(Enum):
    """Classification of neural signal quality"""
    EXCELLENT = "excellent"   # >95% fidelity
    GOOD = "good"             # 85-95% fidelity
    ADEQUATE = "adequate"     # 70-85% fidelity
    DEGRADED = "degraded"     # 50-70% fidelity
    POOR = "poor"             # 30-50% fidelity
    CRITICAL = "critical"     # <30% fidelity

class ThoughtDecoder(BaseModel):
    """Decodes encrypted thought packets into neural signals"""
    decoder_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    supported_domains: List[ThoughtDomain] = Field(default_factory=list)
    decoding_parameters: Dict[str, float] = Field(default_factory=dict)
    calibration_status: float = Field(default=0.5, ge=0.0, le=1.0)
    error_correction_level: float = Field(default=0.7, ge=0.0, le=1.0)
    
    def __init__(self, **data):
        super().__init__(**data)
        self._initialize_decoding_parameters()
    
    def _initialize_decoding_parameters(self) -> None:
        """Initialize default decoding parameters if not provided"""
        if not self.decoding_parameters:
            self.decoding_parameters = {
                "temporal_resolution": 0.001,  # millisecond resolution
                "frequency_range_low": 0.1,    # Hz
                "frequency_range_high": 100.0, # Hz
                "amplitude_threshold": 0.05,   # normalized units
                "coherence_threshold": 0.3,    # normalized units
                "signal_noise_ratio": 15.0,    # dB
                "error_correction_factor": self.error_correction_level
            }
        
        # Set defaults for supported domains if not provided
        if not self.supported_domains:
            self.supported_domains = [domain for domain in ThoughtDomain]
    
    async def decode_packet(self, packet: ThoughtPacket, 
                     encryption_key: Optional[bytes] = None) -> NeuralSignal:
        """
        Decode an encrypted thought packet into a neural signal
        
        Args:
            packet: The encrypted thought packet
            encryption_key: Optional encryption key, if not included in packet
            
        Returns:
            NeuralSignal: Decoded neural signal
            
        Raises:
            QuantumEncryptionFailure: If decryption fails
            ValueError: If packet domain is not supported
        """
        # Validate domain support
        if packet.domain not in self.supported_domains:
            raise ValueError(f"Domain {packet.domain} not supported by this decoder")
        
        # Get key for decryption
        key = encryption_key or packet.encryption_key
        
        try:
            # Decrypt packet content
            decrypted_content = self._decrypt_content(packet.content, key)
            
            # Verify signature
            if not self._verify_signature(packet.content, packet.signature, packet.sender):
                logger.warning(f"Invalid signature for packet from {packet.sender}")
            
            # Convert to neural signal
            signal = self._content_to_signal(decrypted_content, packet.domain)
            
            # Apply error correction
            signal = await self._apply_error_correction(signal)
            
            return signal
            
        except Exception as e:
            logger.error(f"Failed to decode packet: {str(e)}")
            raise QuantumEncryptionFailure(
                "Thought packet decoding failed",
                code="NTP-007",
                retry_count=0
            ) from e
    
    def _decrypt_content(self, content: bytes, key: bytes) -> bytes:
        """Decrypt packet content using provided key"""
        # In production, this would use quantum-resistant algorithms
        encryptor = ThoughtEncryptor()
        return encryptor.decrypt(content, key)
    
    def _verify_signature(self, content: bytes, signature: bytes, sender_id: str) -> bool:
        """
        Verify HMAC-SHA256 signature using a key derived from sender identity.
        Mirrors the signing scheme in NeuralInterface._sign_packet — constant-time
        comparison via hmac.compare_digest prevents timing-oracle attacks.
        """
        try:
            sign_key = hashlib.sha256(sender_id.encode()).digest()
            expected = _hmac.new(sign_key, content, hashlib.sha256).digest()
            return _hmac.compare_digest(signature, expected)
        except Exception as exc:
            logger.warning("Signature verification error for sender '%s': %s", sender_id, exc)
            return False
    
    def _content_to_signal(self, content: bytes, domain: ThoughtDomain) -> NeuralSignal:
        """
        Parse canonical pipe-delimited key:value bytes back into a NeuralSignal.

        Format produced by QuantumSecureSignalProcessor._serialize_signal():
          "timestamp:1.23|amplitude:0.7|frequency:10.0|coherence:0.8|domain:cognitive"

        All numeric values are clamped to their valid ranges. Falls back to safe
        defaults on any parse error so the receiver never crashes on malformed content.
        """
        try:
            decoded = content.decode("utf-8", errors="replace")
            fields: Dict[str, Any] = {}
            for part in decoded.split("|"):
                if ":" not in part:
                    continue
                k, _, v = part.partition(":")
                k, v = k.strip(), v.strip()
                try:
                    fields[k] = float(v) if ("." in v or "e" in v.lower()) else int(v)
                except ValueError:
                    fields[k] = v

            return NeuralSignal(
                timestamp=float(fields.get("timestamp", time.time())),
                amplitude=min(1.0, max(0.0, float(fields.get("amplitude", 0.5)))),
                frequency=min(100.0, max(0.1, float(fields.get("frequency", 10.0)))),
                domain=domain,
                coherence=min(1.0, max(0.0, float(fields.get("coherence", 0.5)))),
            )

        except Exception as exc:
            logger.warning("Content-to-signal parse failed: %s — using safe defaults", exc)
            return NeuralSignal(
                timestamp=time.time(),
                amplitude=0.5,
                frequency=10.0,
                domain=domain,
                coherence=0.3,
            )
    
    async def _apply_error_correction(self, signal: NeuralSignal) -> NeuralSignal:
        """
        Two-stage error correction:

        1. Coherence: exponential moving average (α=0.3) over a 20-sample sliding
           window smooths burst noise while preserving signal trends.

        2. Amplitude: Wiener-style normalisation — subtract the rolling noise floor
           (min of window) and rescale to [0, 1] by the observed dynamic range,
           making the signal invariant to gain drift.
        """
        # ---- coherence EMA ----
        if not hasattr(self, "_coherence_window"):
            self._coherence_window: List[float] = []
        self._coherence_window.append(signal.coherence)
        if len(self._coherence_window) > 20:
            self._coherence_window.pop(0)

        if len(self._coherence_window) >= 3:
            alpha = 0.3
            ema = self._coherence_window[0]
            for c in self._coherence_window[1:]:
                ema = alpha * c + (1.0 - alpha) * ema
            signal.coherence = min(1.0, max(0.0, ema))

        # ---- amplitude Wiener normalisation ----
        if not hasattr(self, "_amplitude_window"):
            self._amplitude_window: List[float] = []
        self._amplitude_window.append(signal.amplitude)
        if len(self._amplitude_window) > 20:
            self._amplitude_window.pop(0)

        if len(self._amplitude_window) >= 3:
            noise_floor = min(self._amplitude_window)
            dynamic_range = max(self._amplitude_window) - noise_floor
            if dynamic_range > 1e-6:
                normalised = (signal.amplitude - noise_floor) / dynamic_range
                signal.amplitude = min(1.0, max(0.0, normalised))

        await asyncio.sleep(0.001)  # Real processing latency marker
        return signal
    
    async def calibrate(self, calibration_signals: List[NeuralSignal]) -> float:
        """
        Calibrate the decoder using known reference signals
        
        Args:
            calibration_signals: List of reference signals for calibration
            
        Returns:
            float: New calibration status (0.0-1.0)
        """
        if not calibration_signals:
            return self.calibration_status
        
        # Simulate calibration process
        signal_quality = np.mean([signal.coherence for signal in calibration_signals])
        
        # Update decoding parameters based on calibration
        self.decoding_parameters["amplitude_threshold"] = max(0.01, min(0.1, 
            np.mean([signal.amplitude for signal in calibration_signals]) * 0.5
        ))
        
        self.decoding_parameters["coherence_threshold"] = max(0.2, min(0.5,
            np.mean([signal.coherence for signal in calibration_signals]) * 0.7
        ))
        
        # Update calibration status
        self.calibration_status = min(1.0, max(0.1, signal_quality * 1.2))
        
        return self.calibration_status
    
    def assess_signal_quality(self, signal: NeuralSignal) -> SignalQuality:
        """Assess the quality of a decoded signal"""
        # Calculate composite quality score
        quality_score = (
            signal.coherence * 0.6 +  # Coherence is the most important factor
            min(1.0, signal.amplitude * 2) * 0.2 +  # Amplitude factor
            min(1.0, (signal.frequency / 50.0)) * 0.2  # Frequency factor
        )
        
        # Map score to quality enum
        if quality_score > 0.95:
            return SignalQuality.EXCELLENT
        elif quality_score > 0.85:
            return SignalQuality.GOOD
        elif quality_score > 0.70:
            return SignalQuality.ADEQUATE
        elif quality_score > 0.50:
            return SignalQuality.DEGRADED
        elif quality_score > 0.30:
            return SignalQuality.POOR
        else:
            return SignalQuality.CRITICAL

class TransparencySession(BaseModel):
    """Manages a continuous neural transparency session"""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str
    receiver_id: str
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    allowed_domains: List[ThoughtDomain] = Field(default_factory=list)
    packet_count: int = Field(default=0)
    average_quality: float = Field(default=0.0)
    consent_level: ConsentLevel = Field(default=ConsentLevel.STANDARD)
    
    def record_packet(self, signal_quality: SignalQuality) -> None:
        """Record receipt of a packet and update session statistics"""
        self.packet_count += 1
        
        # Convert enum to numeric quality
        quality_map = {
            SignalQuality.EXCELLENT: 1.0,
            SignalQuality.GOOD: 0.9,
            SignalQuality.ADEQUATE: 0.75,
            SignalQuality.DEGRADED: 0.6,
            SignalQuality.POOR: 0.4,
            SignalQuality.CRITICAL: 0.2
        }
        
        quality_value = quality_map.get(signal_quality, 0.5)
        
        # Update running average of quality
        if self.packet_count == 1:
            self.average_quality = quality_value
        else:
            # Exponential moving average
            alpha = 0.1  # Weight factor for new values
            self.average_quality = (1 - alpha) * self.average_quality + alpha * quality_value
    
    def is_active(self) -> bool:
        """Check if session is active"""
        return self.end_time is None
    
    def end_session(self) -> None:
        """End the session"""
        if self.is_active():
            self.end_time = datetime.utcnow()
    
    def duration(self) -> timedelta:
        """Get session duration"""
        end = self.end_time or datetime.utcnow()
        return end - self.start_time
    
    def is_domain_allowed(self, domain: ThoughtDomain) -> bool:
        """Check if domain is allowed in this session"""
        return domain in self.allowed_domains
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage"""
        return {
            "session_id": self.session_id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "allowed_domains": [d.value for d in self.allowed_domains],
            "packet_count": self.packet_count,
            "average_quality": self.average_quality,
            "consent_level": self.consent_level.value,
            "duration_seconds": self.duration().total_seconds()
        }

class NeuralReceiver:
    """Core receiver for neural transparency signals"""
    
    def __init__(self, receiver_id: str, profile: TransmissionProfile):
        self.receiver_id = receiver_id
        self.profile = profile
        self.mode: ReceiverMode = ReceiverMode.PASSIVE
        self.decoder = ThoughtDecoder()
        self.key_distributor = QuantumKeyDistributor()
        self.consent_engine = ConsentManagementEngine()
        self.metrics_collector = NTPMetrics()
        
        # Session management
        self.active_sessions: Dict[str, TransparencySession] = {}
        self.session_history: List[Dict] = []
        
        # Signal processing
        self.signal_buffer: List[NeuralSignal] = []
        self.buffer_size = 100
        self.processing_callbacks: List[Callable[[NeuralSignal], None]] = []
        
        # Security 
        self.allowed_senders: List[str] = []
        self._session_lock = asyncio.Lock()
        
    async def initialize(self) -> None:
        """Initialize the receiver and prepare for operation"""
        # Register with key distributor
        await self.key_distributor.register_receiver(self.receiver_id)
        
        # Calibrate decoder with sample signals
        calibration_signals = [
            NeuralSignal(
                timestamp=time.time(),
                amplitude=0.7,
                frequency=10.0,
                domain=ThoughtDomain.COGNITIVE,
                coherence=0.9
            ),
            NeuralSignal(
                timestamp=time.time(),
                amplitude=0.6,
                frequency=5.0,
                domain=ThoughtDomain.EMOTIONAL,
                coherence=0.8
            )
        ]
        
        calibration_status = await self.decoder.calibrate(calibration_signals)
        logger.info(f"Neural receiver initialized with calibration status: {calibration_status:.2f}")
        
        # Set allowed senders from profile
        self.allowed_senders = self.profile.allowed_senders if hasattr(self.profile, 'allowed_senders') else []
        
        # Set mode to active
        self.mode = ReceiverMode.ACTIVE
        
        # Log initialization
        self.metrics_collector.track_event("receiver_initialized", {
            "receiver_id": self.receiver_id,
            "calibration_status": calibration_status,
            "quantum_safety": self.profile.quantum_safety
        })
    
    async def receive_thought(self, packet: ThoughtPacket) -> NeuralSignal:
        """
        Receive and process an incoming thought packet
        
        Args:
            packet: The incoming thought packet
            
        Returns:
            NeuralSignal: The decoded neural signal
            
        Raises:
            ConsentDeniedError: If consent is not granted for this transmission
            QuantumEncryptionFailure: If decryption fails
        """
        # Check if receiver is active
        if self.mode == ReceiverMode.DORMANT:
            raise ValueError("Receiver is in dormant mode and cannot process packets")
        
        # Check sender authorization
        if self.allowed_senders and packet.sender not in self.allowed_senders:
            raise ConsentDeniedError(
                f"Sender {packet.sender} not authorized",
                code="NTP-008",
                domains=[]
            )
        
        # Check consent for domain
        if not await self.consent_engine.check_consent(packet.sender, self.receiver_id, packet.domain):
            raise ConsentDeniedError(
                f"No consent for domain {packet.domain}",
                code="NTP-009",
                domains=[d.value for d in self.profile.allowed_domains]
            )
        
        # Get or create session
        session = await self._get_or_create_session(packet.sender, [packet.domain])
        
        # Retrieve encryption key if needed
        if not packet.encryption_key:
            shared_key = await self.key_distributor.get_shared_key(packet.sender, self.receiver_id)
            packet.encryption_key = shared_key
        
        try:
            # Decode the packet
            signal = await self.decoder.decode_packet(packet)
            
            # Assess signal quality
            quality = self.decoder.assess_signal_quality(signal)
            
            # Update session statistics
            session.record_packet(quality)
            
            # Update metrics
            self.metrics_collector.track_reception(
                packet.sender, 
                packet.domain.value,
                1.0 if quality in [SignalQuality.EXCELLENT, SignalQuality.GOOD] else 0.5
            )
            
            # Add to signal buffer
            self._add_to_buffer(signal)
            
            # Process signal through callbacks
            await self._process_signal(signal)
            
            return signal
            
        except QuantumEncryptionFailure as e:
            # Update metrics for failed reception
            self.metrics_collector.track_event("decryption_failure", {
                "sender": packet.sender,
                "error": str(e)
            })
            raise
    
    async def _get_or_create_session(self, sender_id: str, domains: List[ThoughtDomain]) -> TransparencySession:
        """Get existing session or create a new one"""
        async with self._session_lock:
            # Look for existing active session with this sender
            for session in self.active_sessions.values():
                if session.sender_id == sender_id and session.is_active():
                    # Update allowed domains if needed
                    for domain in domains:
                        if domain not in session.allowed_domains:
                            session.allowed_domains.append(domain)
                    return session
            
            # Create new session
            consent_level = await self.consent_engine.get_consent_level(sender_id, self.receiver_id)
            
            session = TransparencySession(
                sender_id=sender_id,
                receiver_id=self.receiver_id,
                allowed_domains=domains,
                consent_level=consent_level
            )
            
            self.active_sessions[session.session_id] = session
            
            # Log session creation
            self.metrics_collector.track_event("session_started", {
                "session_id": session.session_id,
                "sender_id": sender_id,
                "consent_level": consent_level.value
            })
            
            return session
    
    def _add_to_buffer(self, signal: NeuralSignal) -> None:
        """Add a signal to the buffer, maintaining buffer size"""
        self.signal_buffer.append(signal)
        if len(self.signal_buffer) > self.buffer_size:
            self.signal_buffer.pop(0)  # Remove oldest signal
    
    async def _process_signal(self, signal: NeuralSignal) -> None:
        """Process signal through registered callbacks"""
        for callback in self.processing_callbacks:
            try:
                callback(signal)
            except Exception as e:
                logger.error(f"Error in signal processing callback: {str(e)}")
    
    def register_processing_callback(self, callback: Callable[[NeuralSignal], None]) -> None:
        """Register a callback function for signal processing"""
        self.processing_callbacks.append(callback)
    
    def set_mode(self, mode: ReceiverMode) -> None:
        """Change the operating mode of the receiver"""
        previous_mode = self.mode
        self.mode = mode
        
        logger.info(f"Neural receiver mode changed: {previous_mode.value} -> {mode.value}")
        
        # Update metrics
        self.metrics_collector.track_event("mode_change", {
            "receiver_id": self.receiver_id,
            "previous_mode": previous_mode.value,
            "new_mode": mode.value
        })
        
        # Special handling for mode transitions
        if mode == ReceiverMode.DORMANT:
            # End all active sessions when going dormant
            asyncio.create_task(self._end_all_sessions())
    
    async def _end_all_sessions(self) -> None:
        """End all active sessions"""
        async with self._session_lock:
            for session_id, session in list(self.active_sessions.items()):
                if session.is_active():
                    session.end_session()
                    
                    # Move to history
                    self.session_history.append(session.to_dict())
                    
                    # Log session end
                    self.metrics_collector.track_event("session_ended", {
                        "session_id": session_id,
                        "duration_seconds": session.duration().total_seconds(),
                        "packet_count": session.packet_count
                    })
            
            # Clear active sessions
            self.active_sessions = {}
    
    async def end_session(self, session_id: str) -> Dict[str, Any]:
        """End a specific session"""
        async with self._session_lock:
            if session_id not in self.active_sessions:
                raise ValueError(f"Session {session_id} not found")
                
            session = self.active_sessions[session_id]
            session.end_session()
            
            # Move to history and remove from active
            session_data = session.to_dict()
            self.session_history.append(session_data)
            del self.active_sessions[session_id]
            
            # Log session end
            self.metrics_collector.track_event("session_ended", {
                "session_id": session_id,
                "duration_seconds": session.duration().total_seconds(),
                "packet_count": session.packet_count
            })
            
            return session_data
    
    async def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about active and historical sessions"""
        total_packets = sum(s.packet_count for s in self.active_sessions.values())
        active_count = len(self.active_sessions)
        history_count = len(self.session_history)
        
        # Calculate average quality across active sessions
        avg_quality = 0.0
        if active_count > 0:
            avg_quality = sum(s.average_quality for s in self.active_sessions.values()) / active_count
        
        return {
            "active_sessions": active_count,
            "historical_sessions": history_count,
            "total_packets_received": total_packets,
            "average_signal_quality": avg_quality,
            "receiver_mode": self.mode.value,
            "decoder_calibration": self.decoder.calibration_status
        }
    
    def synchronize_with_breath(self, phase: str) -> None:
        """Breath phase update callback. Override in subclasses for phase-aware processing."""
        logger.debug("NeuralReceiver breath phase update: %s", phase)

    async def shutdown(self) -> None:
        """Shut down the receiver cleanly"""
        logger.info(f"Shutting down neural receiver {self.receiver_id}")
        
        # End all sessions
        await self._end_all_sessions()
        
        # Set mode to dormant
        self.mode = ReceiverMode.DORMANT
        
        # Final metrics
        self.metrics_collector.track_event("receiver_shutdown", {
            "receiver_id": self.receiver_id,
            "total_sessions": len(self.session_history),
            "uptime_seconds": (datetime.utcnow() - self.profile.start_time).total_seconds()
                if hasattr(self.profile, 'start_time') else 0
        })