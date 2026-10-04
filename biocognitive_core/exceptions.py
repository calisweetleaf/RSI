# src/biocognitive_core/exceptions.py
"""
Biocognitive Exception Hierarchy Framework

Defines a comprehensive, component-specific exception hierarchy with:
- Error categorization by system component (SIS, NTP, SECT)
- Machine-readable error codes with metadata
- Human-readable diagnostic messages
- Integration with system monitoring and alerting
Author: Morpheus
Date: 2025-05-08
Version: 1.0.0
Description: This module implements a standardized exception handling framework for the biocognitive system. It includes various exception classes that represent different error conditions, each with specific metadata and recovery actions. The framework is designed to facilitate debugging, monitoring, and system resilience.
"""

from typing import Dict, Any, Optional, Union, List, Tuple
from enum import Enum
import abc
import json
from datetime import datetime
from pydantic import BaseModel, Field
import traceback
import inspect
import sys

class ErrorCategory(Enum):
    """Classifies exceptions by system component and severity"""
    SYSTEM_BOUNDARY_VIOLATION = "system_boundary"
    IDENTITY_DISRUPTION = "identity"
    EVOLUTION_MISALIGNMENT = "evolution"
    NEURAL_TRANSPARENCY_FAILURE = "ntp"
    THERAPY_MISALIGNMENT = "therapy"
    SECURITY_VIOLATION = "security"
    RESOURCE_EXHAUSTION = "resource"
    CONFIGURATION_ERROR = "config"
    COMMUNICATION_FAILURE = "communication"

class BaseExceptionMetadata(BaseModel):
    """Standardized metadata for exception tracking"""
    component: str = Field(..., description="Component where error originated")
    error_code: str = Field(..., description="Machine-readable error identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    stack_trace: List[str] = Field(default_factory=list)
    user_id: Optional[str] = Field(None, description="User context if applicable")
    system_id: Optional[str] = Field(None, description="System instance identifier")
    severity: int = Field(5, description="Error severity level (1-10)")
    recovery_actions: List[str] = Field(default_factory=list)

class BiocognitiveError(Exception, metaclass=abc.ABCMeta):
    """
    Base class for all biocognitive system exceptions
    
    >>> try:
    ...     raise EvolutionConstraintViolation("Mutation threshold exceeded", code="SIS-001")
    ... except BiocognitiveError as e:
    ...     print(e.metadata.error_code)
    SIS-001
    """
    def __init__(self, message: str, code: str, metadata: Optional[BaseExceptionMetadata] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.metadata = metadata or BaseExceptionMetadata(
            component=self._get_component(),
            error_code=code,
            stack_trace=self._capture_stack_trace()
        )
        self._record_exception()

    @abc.abstractmethod
    def _get_component(self) -> str:
        """Identify the system component responsible for the error"""
        pass

    def _capture_stack_trace(self) -> List[str]:
        """Capture stack trace with frame filtering"""
        return [
            f"{frame.filename}:{frame.lineno} in {frame.function}"
            for frame in inspect.stack(context=2)
            if not frame.function.startswith("__")
        ]

    def _record_exception(self):
        """Integrate with system monitoring and alerting"""
        from infrastructure.observability import log_exception
        log_exception(self)

    def __str__(self):
        return f"[{self.metadata.error_code}] {self.message}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to serializable dictionary"""
        return {
            "code": self.code,
            "message": self.message,
            "metadata": self.metadata.dict(),
            "type": self.__class__.__name__
        }

class EvolutionConstraintViolation(BiocognitiveError):
    """
    Raised when evolutionary parameters exceed safety limits
    
    >>> try:
    ...     raise EvolutionConstraintViolation("Mutation rate exceeded safe threshold", code="SIS-001")
    ... except EvolutionConstraintViolation as e:
    ...     print(e.metadata.severity)
    9
    """
    def _get_component(self) -> str:
        return "SIS"

    def __init__(
        self,
        message: str,
        code: str,
        mutation_rate: float = 0.0,
        allowed_threshold: float = 0.0
    ):
        super().__init__(message, code)
        self.mutation_rate = mutation_rate
        self.allowed_threshold = allowed_threshold
        self.metadata.severity = 9
        self.metadata.recovery_actions = [
            "Initiate evolutionary rollback",
            "Isolate affected nanobiotic cluster",
            "Trigger emergency containment protocol"
        ]

class ConsentDeniedError(BiocognitiveError):
    """
    Raised when transmission consent is not granted
    
    >>> try:
    ...     raise ConsentDeniedError("Recipient not in allowed domains", code="NTP-002")
    ... except ConsentDeniedError as e:
    ...     print(e.metadata.component)
    NTP
    """
    def _get_component(self) -> str:
        return "NTP"

    def __init__(self, message: str, code: str, domains: List[str]):
        super().__init__(message, code)
        self.domains = domains
        self.metadata.severity = 7
        self.metadata.recovery_actions = [
            "Request explicit consent re-approval",
            "Revert to default transmission restrictions",
            "Log access attempt for audit"
        ]

class IdentityDissolutionRisk(BiocognitiveError):
    """
    Raised when identity coherence falls below safety threshold
    
    >>> try:
    ...     raise IdentityDissolutionRisk("Identity boundary integrity compromised", code="SECT-003")
    ... except IdentityDissolutionRisk as e:
    ...     print(e.metadata.severity)
    8
    """
    def _get_component(self) -> str:
        return "SECT"

    def __init__(
        self,
        message: str,
        code: str,
        coherence_score: float,
        threshold: float
    ):
        super().__init__(message, code)
        self.coherence_score = coherence_score
        self.threshold = threshold
        self.metadata.severity = 8
        self.metadata.recovery_actions = [
            "Activate identity stabilization protocol",
            "Reinforce boundary markers",
            "Trigger emergency self-diagnosis"
        ]

class SystemBoundaryViolation(BiocognitiveError):
    """
    Raised when component isolation is compromised
    
    >>> try:
    ...     raise SystemBoundaryViolation("Immune system accessed cognitive domain", code="CORE-004")
    ... except SystemBoundaryViolation as e:
    ...     print(e.metadata.recovery_actions)
    ['Isolate affected subsystem', 'Trigger system-wide boundary check', 'Log breach for forensic analysis']
    """
    def _get_component(self) -> str:
        return "CORE"

    def __init__(self, message: str, code: str, violating_component: str):
        super().__init__(message, code)
        self.violating_component = violating_component
        self.metadata.severity = 10
        self.metadata.recovery_actions = [
            "Isolate affected subsystem",
            "Trigger system-wide boundary check",
            "Log breach for forensic analysis"
        ]

class QuantumEncryptionFailure(BiocognitiveError):
    """
    Raised when quantum-secured communication fails
    
    >>> try:
    ...     raise QuantumEncryptionFailure("Key exchange failed with quantum channel", code="NTP-005")
    ... except QuantumEncryptionFailure as e:
    ...     print(e.metadata.severity)
    9
    """
    def _get_component(self) -> str:
        return "NTP"

    def __init__(self, message: str, code: str, retry_count: int = 0):
        super().__init__(message, code)
        self.retry_count = retry_count
        self.metadata.severity = 9
        self.metadata.recovery_actions = [
            "Attempt quantum key reinitialization",
            "Switch to classical encryption fallback",
            "Log quantum channel degradation"
        ]

class TherapyMisalignmentError(BiocognitiveError):
    """
    Raised when therapeutic agent goals diverge from user intent
    
    >>> try:
    ...     raise TherapyMisalignmentError("Therapeutic intervention violates user values", code="SECT-006")
    ... except TherapyMisalignmentError as e:
    ...     print(e.metadata.component)
    SECT
    """
    def _get_component(self) -> str:
        return "SECT"

    def __init__(self, message: str, code: str, alignment_score: float):
        super().__init__(message, code)
        self.alignment_score = alignment_score
        self.metadata.severity = 8
        self.metadata.recovery_actions = [
            "Re-evaluate therapeutic objectives",
            "Re-initiate alignment calibration",
            "Suspend autonomous modifications"
        ]

class ResourceExhaustionError(BiocognitiveError):
    """
    Raised when system resources fall below operational thresholds
    
    >>> try:
    ...     raise ResourceExhaustionError("Energy reserve below 10%", code="CORE-007")
    ... except ResourceExhaustionError as e:
    ...     print(e.metadata.recovery_actions)
    ['Initiate resource conservation mode', 'Trigger emergency power allocation', 'Log resource depletion']
    """
    def _get_component(self) -> str:
        return "CORE"

    def __init__(self, message: str, code: str, resource_type: str, current_level: float, threshold: float):
        super().__init__(message, code)
        self.resource_type = resource_type
        self.current_level = current_level
        self.threshold = threshold
        self.metadata.severity = 7
        self.metadata.recovery_actions = [
            "Initiate resource conservation mode",
            "Trigger emergency power allocation",
            "Log resource depletion"
        ]

class ConfigurationValidationError(BiocognitiveError):
    """
    Raised when configuration parameters are invalid
    
    >>> try:
    ...     raise ConfigurationValidationError("Invalid quantum safety level", code="CORE-008")
    ... except ConfigurationValidationError as e:
    ...     print(e.metadata.severity)
    6
    """
    def _get_component(self) -> str:
        return "CORE"

    def __init__(self, message: str, code: str, config_path: str):
        super().__init__(message, code)
        self.config_path = config_path
        self.metadata.severity = 6
        self.metadata.recovery_actions = [
            "Revert to default configuration",
            "Validate configuration schema",
            "Trigger configuration rollback"
        ]

"""
Core system exceptions
"""
from typing import Optional, Any


class BiocognitiveError(Exception):
    """Base exception class for all biocognitive system errors"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class ConfigurationError(BiocognitiveError):
    """Error in system configuration"""
    pass


class AuthenticationError(BiocognitiveError):
    """Error in authentication process"""
    pass


class AuthorizationError(BiocognitiveError):
    """Error in authorization process"""
    pass


class DataIntegrityError(BiocognitiveError):
    """Error in data integrity check"""
    pass


class CommunicationError(BiocognitiveError):
    """Error in communication between components"""
    pass


class ResourceNotFoundError(BiocognitiveError):
    """Resource not found"""
    pass


class OperationTimeoutError(BiocognitiveError):
    """Operation timed out"""
    pass


class ModelConvergenceError(BiocognitiveError):
    """Raised when model optimization fails to converge."""
    pass


class CognitiveAlignmentError(BiocognitiveError):
    """Raised when cognitive alignment constraints are violated."""
    pass


class InterfaceCompatibilityError(BiocognitiveError):
    """Raised when integration interfaces are incompatible."""
    pass


class SelfModificationConstraintViolation(BiocognitiveError):
    """Raised when self-modification violates safety constraints."""
    pass


class TherapeuticIntegrityError(BiocognitiveError):
    """Raised when therapeutic integrity checks fail."""
    pass


class RecursionDepthExceededError(BiocognitiveError):
    """Raised when recursion depth limits are exceeded."""
    pass


# === ROSEMARY Integration: DNA and Node Exceptions ===
class RosemaryError(BiocognitiveError):
    """Base exception class for all ROSEMARY-specific errors"""
    pass


class DNATranslationError(RosemaryError):
    """Error during DNA structure translation"""
    def __init__(self, message: str, chromosome: Optional[str] = None, gene: Optional[str] = None):
        self.chromosome = chromosome
        self.gene = gene
        detail = f" in chromosome '{chromosome}'" if chromosome else ""
        detail += f", gene '{gene}'" if gene else ""
        full_message = f"{message}{detail}"
        super().__init__(full_message)


class StabilityMatrixError(RosemaryError):
    """Error in stability matrix operations"""
    def __init__(self, message: str, pattern_type: Optional[str] = None):
        self.pattern_type = pattern_type
        detail = f" (pattern: {pattern_type})" if pattern_type else ""
        super().__init__(f"{message}{detail}")


class RecursionDetectionError(StabilityMatrixError):
    """Error related to recursion detection"""
    def __init__(self, message: str, depth: Optional[int] = None, pattern_type: Optional[str] = None):
        self.depth = depth
        detail = f" (depth: {depth})" if depth is not None else ""
        super().__init__(f"{message}{detail}", pattern_type)


class ContradictionError(StabilityMatrixError):
    """Error related to contradictions in stability matrix"""
    def __init__(self, message: str, tension: Optional[float] = None, contradiction_type: Optional[str] = None):
        self.tension = tension
        detail = f" (tension: {tension:.2f})" if tension is not None else ""
        super().__init__(f"{message}{detail}", contradiction_type)


class BreathPhaseError(RosemaryError):
    """Error in breath phase system"""
    def __init__(self, message: str, phase: Optional[str] = None):
        self.phase = phase
        detail = f" (phase: {phase})" if phase else ""
        super().__init__(f"{message}{detail}")


class DreamPhaseError(RosemaryError):
    """Error in dream phase processing"""
    pass


class SovereigntyError(RosemaryError):
    """Error in sovereignty core operations"""
    pass


class BodySyncError(RosemaryError):
    """Error in body synchronization operations"""
    def __init__(self, message: str, system: Optional[str] = None, state: Any = None):
        self.system = system
        self.state = state
        detail = f" in {system}" if system else ""
        super().__init__(f"{message}{detail}")


# Common HTTP-style exceptions for API compatibility
class ConflictError(BiocognitiveError):
    """Error indicating a conflict with current state (HTTP 409 equivalent)"""
    pass


class NotFoundError(BiocognitiveError):
    """Error indicating resource not found (HTTP 404 equivalent)"""
    pass


class PermissionDeniedError(BiocognitiveError):
    """Error indicating permission denied (HTTP 403 equivalent)"""
    pass


# Register all exception types with system monitoring
from infrastructure.observability import register_exception_class
register_exception_class(EvolutionConstraintViolation)
register_exception_class(ConsentDeniedError)
register_exception_class(IdentityDissolutionRisk)
register_exception_class(SystemBoundaryViolation)
register_exception_class(QuantumEncryptionFailure)
register_exception_class(TherapyMisalignmentError)
register_exception_class(ResourceExhaustionError)
register_exception_class(ConfigurationValidationError)
# End of file
