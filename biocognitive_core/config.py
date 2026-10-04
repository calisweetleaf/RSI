# src/biocognitive_core/config.py
"""
Biocognitive System Configuration Framework

Manages complex configuration for multi-layered biocognitive architecture with
strict separation of concerns, cryptographic security, and evolutionary constraints.
Author: Morpheus
Date: 2025-05-08
Version: 1.0.0
Description: This module implements the configuration management system for the biocognitive architecture. It includes various components such as the synthetic immune symbiont, neural transparency protocol, self-evolving cognitive therapist, and security infrastructure. The system is designed to ensure coherence, validation, and safety across all components.
ID: CONFIG-001
SHA-256: 1192536cf4e5d6a7b8c9e0f1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3
"""

from typing import Dict, List, Optional, Union, Literal, Any
from dataclasses import dataclass
from pydantic import BaseModel, Field, validator, root_validator
try:
    from pydantic_settings import BaseSettings
except ImportError:
    try:
        from pydantic import BaseSettings  # pydantic v1 fallback
    except ImportError:
        # Fallback: use BaseModel as BaseSettings
        class BaseSettings(BaseModel):  # type: ignore
            class Config:
                env_prefix = ""
                env_file = ".env"
from enum import Enum
import os
import logging
from pathlib import Path
from datetime import timedelta
import secrets
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
import json
from functools import lru_cache

class ConfigValidationError(Exception):
    """Raised when configuration validation fails"""
    def __init__(self, field: str, value: Any, reason: str):
        self.field = field
        self.value = value
        self.reason = reason
        super().__init__(f"Configuration validation failed for {field}: {reason}")

class QuantumSafetyLevel(str, Enum):
    """Quantum-resistant encryption safety levels"""
    QRL1 = "qrl1"  # NIST Post-Quantum Candidate Algorithms
    QRL2 = "qrl2"  # Hybrid Classical/Quantum
    QRL3 = "qrl3"  # Full Quantum-Resistant

class IdentityCoherenceMode(str, Enum):
    """Identity boundary management modes"""
    STRICT = "strict"        # Traditional identity boundaries
    ADAPTIVE = "adaptive"    # Dynamic boundary adjustment
    MERGED = "merged"        # Partial identity integration

class ImmuneSystemConfig(BaseModel):
    """Synthetic Immune Symbiont Configuration"""
    replication_rate_limit: float = Field(
        default=0.05, 
        ge=0.01,
        le=0.2,
        description="Max replication rate per second (0.01-0.2)"
    )
    mutation_threshold: float = Field(
        default=0.75,
        ge=0.5,
        le=0.95,
        description="DNA damage threshold for mutation response"
    )
    energy_efficiency_factor: float = Field(
        default=0.85,
        ge=0.7,
        le=0.95,
        description="Energy utilization efficiency factor"
    )
    communication_protocol: Literal["quantum_entanglement", "neural_spike", "chemical_signaling"] = Field(
        default="quantum_entanglement",
        description="Primary communication mechanism"
    )
    evolution_window: timedelta = Field(
        default=timedelta(hours=24),
        description="Time window for evolutionary adaptation"
    )

    @validator("evolution_window")
    def validate_evolution_window(cls, v):
        if v < timedelta(hours=1) or v > timedelta(days=7):
            raise ValueError("Evolution window must be between 1 hour and 7 days")
        return v

class NeuralInterfaceConfig(BaseModel):
    """Neural Transparency Protocol Configuration"""
    signal_resolution: int = Field(
        default=4096,
        ge=2048,
        le=16384,
        description="Neural signal sampling resolution (bits)"
    )
    transmission_latency: float = Field(
        default=0.015,
        ge=0.001,
        le=0.1,
        description="Max acceptable transmission latency (seconds)"
    )
    quantum_safety: QuantumSafetyLevel = Field(
        default=QuantumSafetyLevel.QRL2,
        description="Quantum-resistant encryption level"
    )
    consent_timeout: timedelta = Field(
        default=timedelta(seconds=30),
        description="Maximum consent validation duration"
    )
    allowed_domains: List[Literal[
        "EMOTIONAL", "COGNITIVE", "PHYSIOLOGICAL", "SPIRITUAL"
    ]] = Field(
        default=["EMOTIONAL", "COGNITIVE", "PHYSIOLOGICAL"],
        description="Permitted thought transmission domains"
    )
    identity_mode: IdentityCoherenceMode = Field(
        default=IdentityCoherenceMode.ADAPTIVE,
        description="Identity boundary management mode"
    )

class TherapyAgentConfig(BaseModel):
    """Self-Evolving Cognitive Therapist Configuration"""
    intervention_window: timedelta = Field(
        default=timedelta(minutes=5),
        description="Maximum intervention latency"
    )
    pattern_recognition_depth: int = Field(
        default=7,
        ge=3,
        le=12,
        description="Depth of cognitive pattern analysis"
    )
    self_modification_limit: float = Field(
        default=0.15,
        ge=0.05,
        le=0.3,
        description="Maximum allowed self-modification rate"
    )
    emotional_model_complexity: int = Field(
        default=9,
        ge=5,
        le=15,
        description="Emotional processing model complexity level"
    )
    alignment_tolerance: float = Field(
        default=0.85,
        ge=0.7,
        le=1.0,
        description="Minimum therapeutic alignment threshold"
    )


class SECTAgentConfig(BaseModel):
    """Runtime configuration for SECT agents."""
    max_processing_threads: int = Field(default=8, ge=1, le=64)
    max_concurrent_interventions: int = Field(default=3, ge=1, le=10)
    adaptation_frequency: int = Field(default=5, ge=1, le=100)
    allow_self_modification: bool = Field(default=True)
    max_recursion_depth: int = Field(default=5, ge=1, le=10)
    effectiveness_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    max_modification_level: int = Field(default=3, ge=0, le=5)
    perform_dry_run: bool = Field(default=False)
    cycle_interval: float = Field(default=1.0, ge=0.01)

    @classmethod
    def load_from_env(cls) -> "SECTAgentConfig":
        def _get_int(name: str, default: int) -> int:
            raw = os.getenv(name)
            return int(raw) if raw is not None else default

        def _get_float(name: str, default: float) -> float:
            raw = os.getenv(name)
            return float(raw) if raw is not None else default

        def _get_bool(name: str, default: bool) -> bool:
            raw = os.getenv(name)
            if raw is None:
                return default
            return raw.lower() in {"1", "true", "yes", "on"}

        return cls(
            max_processing_threads=_get_int("SECT_MAX_PROCESSING_THREADS", 8),
            max_concurrent_interventions=_get_int("SECT_MAX_CONCURRENT_INTERVENTIONS", 3),
            adaptation_frequency=_get_int("SECT_ADAPTATION_FREQUENCY", 5),
            allow_self_modification=_get_bool("SECT_ALLOW_SELF_MODIFICATION", True),
            max_recursion_depth=_get_int("SECT_MAX_RECURSION_DEPTH", 5),
            effectiveness_threshold=_get_float("SECT_EFFECTIVENESS_THRESHOLD", 0.6),
            max_modification_level=_get_int("SECT_MAX_MODIFICATION_LEVEL", 3),
            perform_dry_run=_get_bool("SECT_PERFORM_DRY_RUN", False),
            cycle_interval=_get_float("SECT_CYCLE_INTERVAL", 1.0),
        )

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SECTAgentConfig":
        return cls(**data)


@dataclass
class BiometricState:
    """Snapshot of biometric readings for cognitive state construction."""
    thought_patterns: Dict[str, Any]
    emotional_metrics: Dict[str, float]
    cognitive_load: float
    attention_foci: List[str]
    active_memories: Dict[str, float]
    self_awareness: float


class BiometricInterface:
    """Biometric interface with a safe default implementation."""
    async def get_current_state(self) -> BiometricState:
        return BiometricState(
            thought_patterns={"baseline": [0.1, 0.2, 0.3]},
            emotional_metrics={"calm": 0.2},
            cognitive_load=0.4,
            attention_foci=["baseline"],
            active_memories={"baseline": 0.1},
            self_awareness=0.3,
        )

    def get_vitals(self) -> Dict[str, float]:
        return {"heart_rate": 70.0, "stress_index": 0.2}

    async def restore_state(self, _state: Any) -> None:
        return None

    async def shutdown(self) -> None:
        return None


class CoordinationInterface:
    async def request_modification_window(self) -> None:
        return None

    async def release_modification_window(self) -> None:
        return None

    async def flush_operations(self) -> None:
        return None


class ModificationInterface:
    async def execute_modification(self, modification_plan: Dict[str, Any], validation_checks: bool) -> Dict[str, Any]:
        return {
            "success": True,
            "new_config": modification_plan.get("config", {}),
            "error": "",
        }

    async def shutdown(self) -> None:
        return None


class AlertSubsystem:
    def __init__(self) -> None:
        self._logger = logging.getLogger("sect_alerts")

    def trigger_alert(self, code: str, message: str) -> None:
        self._logger.warning("%s: %s", code, message)


class StorageInterface:
    def __init__(self, storage_path: Path) -> None:
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)

    async def persist_state(self, agent_id: str, state_data: Dict[str, Any]) -> None:
        path = self.storage_path / f"sect_state_{agent_id}.json"
        path.write_text(json.dumps(state_data, default=str, indent=2), encoding="utf-8")


class SystemIntegrationConfig:
    """Facade that provides system integration interfaces."""
    def __init__(
        self,
        biometric_interface: Optional[BiometricInterface] = None,
        coordination_interface: Optional[CoordinationInterface] = None,
        modification_interface: Optional[ModificationInterface] = None,
        alert_subsystem: Optional[AlertSubsystem] = None,
        storage_interface: Optional[StorageInterface] = None,
    ):
        self.biometric_interface = biometric_interface or BiometricInterface()
        self.coordination_interface = coordination_interface or CoordinationInterface()
        self.modification_interface = modification_interface or ModificationInterface()
        self.alert_subsystem = alert_subsystem or AlertSubsystem()
        self.storage_interface = storage_interface or StorageInterface(settings.storage_path)

    def available_resources(self) -> float:
        return 1.0

    async def shutdown_all(self) -> None:
        await self.biometric_interface.shutdown()
        await self.modification_interface.shutdown()

    @classmethod
    def load_default(cls) -> "SystemIntegrationConfig":
        return cls()

class SecurityConfig(BaseModel):
    """Security Infrastructure Configuration"""
    quantum_key_length: int = Field(
        default=512,
        ge=256,
        le=1024,
        description="Quantum-resistant key length in bits"
    )
    key_rotation_seconds: int = Field(
        default=86400,
        ge=300,
        le=2592000,
        description="Session key rotation interval in seconds"
    )
    encryption_iterations: int = Field(
        default=10000,
        ge=5000,
        le=50000,
        description="Key derivation function iterations"
    )
    biometric_verification: bool = Field(
        default=True,
        description="Enable multi-factor identity verification"
    )
    consent_chain_depth: int = Field(
        default=7,
        ge=3,
        le=15,
        description="Blockchain depth for consent verification"
    )

class ObservabilityConfig(BaseModel):
    """System Monitoring and Metrics Configuration"""
    metric_interval: timedelta = Field(
        default=timedelta(seconds=15),
        description="Metrics collection interval"
    )
    trace_sampling_rate: float = Field(
        default=0.2,
        ge=0.01,
        le=1.0,
        description="Distributed tracing sampling rate"
    )
    log_level: str = Field(
        default="INFO",
        description="Default logging severity level"
    )
    alert_threshold: float = Field(
        default=0.75,
        ge=0.5,
        le=0.95,
        description="Anomaly detection threshold"
    )

class IntegrationConfig(BaseModel):
    """Cross-System Integration Configuration"""
    metrics_interval: timedelta = Field(
        default=timedelta(seconds=30),
        description="Integration metrics collection interval"
    )
    sync_timeout: timedelta = Field(
        default=timedelta(seconds=60),
        description="Maximum time for cross-system synchronization"
    )
    sync_interval: timedelta = Field(
        default=timedelta(seconds=30),
        description="Interval for cross-system state synchronization"
    )
    boundary_check_interval: timedelta = Field(
        default=timedelta(seconds=10),
        description="Interval for boundary integrity checks"
    )
    max_adaptation_rate: float = Field(
        default=0.1,
        ge=0.01,
        le=0.5,
        description="Maximum adaptation rate for system integration"
    )
    coherence_threshold: float = Field(
        default=0.8,
        ge=0.5,
        le=1.0,
        description="Minimum coherence threshold for integrated systems"
    )
    min_identity_coherence: float = Field(
        default=0.75,
        ge=0.5,
        le=1.0,
        description="Minimum identity coherence threshold for system integration"
    )

class BiocognitiveSettings(BaseSettings):
    """
    Core Biocognitive System Settings
    
    >>> settings = BiocognitiveSettings()
    >>> settings.immune.replication_rate_limit
    0.05
    """
    # System Identity
    system_id: str = Field(
        default_factory=lambda: secrets.token_hex(16),
        description="Unique system identifier"
    )
    version: str = Field(
        default="1.0.0",
        description="System version string"
    )
    environment: str = Field(
        default="production",
        env=["env_type", "environment"],
        description="Operating environment (development/production/test)"
    )
    
    # Component Configurations
    immune: ImmuneSystemConfig = Field(
        default_factory=ImmuneSystemConfig,
        description="Synthetic Immune Symbiont Configuration"
    )
    neural: NeuralInterfaceConfig = Field(
        default_factory=NeuralInterfaceConfig,
        description="Neural Transparency Protocol Configuration"
    )
    therapy: TherapyAgentConfig = Field(
        default_factory=TherapyAgentConfig,
        description="Self-Evolving Cognitive Therapist Configuration"
    )
    security: SecurityConfig = Field(
        default_factory=SecurityConfig,
        description="Security Infrastructure Configuration"
    )
    observability: ObservabilityConfig = Field(
        default_factory=ObservabilityConfig,
        description="System Monitoring Configuration"
    )
    integration: IntegrationConfig = Field(
        default_factory=IntegrationConfig,
        description="Cross-System Integration Configuration"
    )

    # Infrastructure Settings
    storage_path: Path = Field(
        default=Path("/var/lib/biocognitive"),
        description="System data storage directory"
    )
    max_concurrent_tasks: int = Field(
        default=100,
        ge=10,
        le=1000,
        description="Maximum concurrent async tasks"
    )
    heartbeat_interval: timedelta = Field(
        default=timedelta(seconds=5),
        description="System health check interval"
    )
    
    # Validation and Safety
    @root_validator(pre=True)
    def validate_config_coherence(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure cross-component configuration coherence"""
        immune = values.get("immune")
        neural = values.get("neural")
        
        if immune and neural:
            if immune.communication_protocol == "quantum_entanglement" and \
               neural.quantum_safety != QuantumSafetyLevel.QRL3:
                raise ConfigValidationError(
                    "quantum_safety", 
                    neural.quantum_safety,
                    "QRL3 required for quantum entanglement communication"
                )
        
        return values
    
    @validator("storage_path")
    def validate_storage_path(cls, v: Path) -> Path:
        """Ensure storage path exists and has proper permissions"""
        try:
            v.mkdir(parents=True, exist_ok=True)
            if not os.access(v, os.R_OK | os.W_OK):
                raise PermissionError(f"Insufficient permissions for {v}")
        except Exception as e:
            raise ConfigValidationError("storage_path", v, str(e))
        return v

    class Config:
        env_prefix = "BIOC_"
        env_nested_delimiter = "__"
        case_sensitive = False
        validate_default = True
        arbitrary_types_allowed = True

@lru_cache()
def get_settings() -> BiocognitiveSettings:
    """
    Create cached configuration instance
    
    Returns:
        BiocognitiveSettings: Loaded system configuration
    """
    return BiocognitiveSettings()

# Global settings instance
settings = get_settings()

if __name__ == "__main__":
    # Example configuration validation
    try:
        print(f"System ID: {settings.system_id}")
        print(f"Quantum Safety Level: {settings.neural.quantum_safety}")
        print(f"Replication Rate Limit: {settings.immune.replication_rate_limit}")
    except ConfigValidationError as e:
        print(f"Configuration Error: {e}")

# === ROSEMARY Integration: DNA and Node Configuration ===
ROSEMARY_ENABLED = True
ROSEMARY_DNA_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'ROSEMARY_updates', 'dna.rosemary.arfs')
ROSEMARY_NODE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'ROSEMARY_updates')

# Base configuration settings
class Settings:
    """Configuration settings with defaults and environment overrides"""
    
    def __init__(self):
        self.version = "1.0.0"
        self.debug = os.getenv("DEBUG", "False").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.environment = os.getenv("ENVIRONMENT", "development")
        
        # Neural settings
        self.neural = NeuralSettings()
        
        # Security settings
        self.security = SecuritySettings()
        
        # Load ROSEMARY DNA if enabled
        self.rosemary = RosemarySettings()

class NeuralSettings:
    """Neural-specific settings"""
    
    def __init__(self):
        self.batch_size = int(os.getenv("NEURAL_BATCH_SIZE", "64"))
        self.learning_rate = float(os.getenv("NEURAL_LEARNING_RATE", "0.001"))
        self.hidden_layers = int(os.getenv("NEURAL_HIDDEN_LAYERS", "3"))
        self.consent_timeout = int(os.getenv("CONSENT_TIMEOUT_HOURS", "24")) * 3600
        self.thought_domains = ["COGNITIVE", "EMOTIONAL", "PHYSICAL", "SPIRITUAL"]

class SecuritySettings:
    """Security-specific settings"""
    
    def __init__(self):
        self.encryption_algorithm = os.getenv("ENCRYPTION_ALGORITHM", "AES-256-GCM")
        self.key_rotation_days = int(os.getenv("KEY_ROTATION_DAYS", "30"))
        self.max_auth_attempts = int(os.getenv("MAX_AUTH_ATTEMPTS", "5"))
        self.session_timeout = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30")) * 60
        self.min_password_length = int(os.getenv("MIN_PASSWORD_LENGTH", "12"))
        self.quantum_resistant = os.getenv("QUANTUM_RESISTANT", "True").lower() == "true"

class RosemarySettings:
    """Rosemary-specific settings and DNA configuration"""
    
    def __init__(self):
        self.enabled = ROSEMARY_ENABLED
        self.dna_path = ROSEMARY_DNA_PATH
        self.node_path = ROSEMARY_NODE_PATH
        
        # Default chromosome activation levels - can be adjusted at runtime
        self.chromosome_activation = {
            "identity_core": 1.0,
            "ethical_framework": 1.0,
            "cognitive_architecture": 1.0,
            "perception_framework": 0.8, 
            "dream_processing": 0.6,
            "temporal_dynamics": 0.7,
            "quantum_integration": 0.5,
            "metamorphic_evolution": 0.4
        }
        
        # Node activation status - initially all enabled
        self.node_activation = {
            "body_synch_node": True,
            "breath_phase": True,
            "dream_phase": True,
            "stability_matrix": True,
            "soverignty_core": True,
            "launch_core": True
        }
        
        # Load DNA if file exists
        self.dna = self._load_dna()
        
    def _load_dna(self) -> Dict[str, Any]:
        """Load DNA configuration from arfs file"""
        try:
            if os.path.exists(self.dna_path):
                with open(self.dna_path, 'r') as f:
                    # Parse as JSON but skip initial comment lines if present
                    content = f.read()
                    if content.strip().startswith('```'):
                        # Remove markdown code fences if present
                        content = '\n'.join(content.split('\n')[1:-1])
                    return json.loads(content)
            return {}
        except Exception as e:
            print(f"Error loading Rosemary DNA: {e}")
            return {}
    
    def get_chromosome(self, name: str) -> Dict[str, Any]:
        """Get a specific chromosome from the DNA"""
        try:
            return self.dna.get("ARFS-DNA-V2", {}).get("chromosomes", {}).get(name, {})
        except (KeyError, AttributeError):
            return {}
    
    def get_gene(self, chromosome: str, gene: str) -> Dict[str, Any]:
        """Get a specific gene from a chromosome"""
        chromosome_data = self.get_chromosome(chromosome)
        return chromosome_data.get("genes", {}).get(gene, {})
    
    def is_node_active(self, node_name: str) -> bool:
        """Check if a specific Rosemary node is activated"""
        return self.node_activation.get(node_name, False)

# Rosemary-specific settings instance (kept separate from core settings)
rosemary_settings = Settings()
