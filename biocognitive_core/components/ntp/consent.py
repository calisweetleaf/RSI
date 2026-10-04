"""
Neural Transparency Protocol - Consent Management Module

This module implements the Neural Transparency Protocol's consent management system,
providing granular control over thought domain accessibility, real-time authentication
of transmission boundaries, and nested permission structures for complex thought sharing.

Classes:
 ConsentStatus: Enumeration of possible consent states
 ThoughtDomain: Enumeration of neural transmission domains
 ConsentScope: Defines the scope of consent permission
 ConsentRecord: Data model for consent agreements
 ConsentRepository: Interface for consent data storage
 ConsentValidationError: Exception hierarchy for consent validation
 ConsentEngine: Core consent management and enforcement engine
 ConsentAuditLogger: Specialized logger for consent operations
 
Architecture:
 - Domain models represent the core entities
 - Repository pattern for data access abstraction
 - Strategy pattern for consent validation rules
 - Observer pattern for consent change notifications
 - Circuit breakers for external service resilience
"""

import asyncio
import datetime
import enum
import functools
import hashlib
import json
import logging
import os
import secrets
import time
import uuid
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager, contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import (Any, Callable, Dict, FrozenSet, Generic, List, Literal,
     Mapping, Optional, Protocol, Set, Tuple, Type, TypeVar, Union,
     cast, overload, TYPE_CHECKING)

# Forward references for type hints to avoid circular imports
if TYPE_CHECKING:
    from infrastructure.security import EncryptionService, IdentityVerifier

try:
    import aiohttp
except ImportError:
    aiohttp = None  # type: ignore

import pydantic
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from pydantic import AnyHttpUrl, BaseModel, Field, SecretStr, validator
try:
    from pydantic_settings import BaseSettings
except ImportError:
    try:
        from pydantic import BaseSettings  # pydantic v1 fallback
    except ImportError:
        BaseSettings = BaseModel  # ultimate fallback
try:
    from pydantic.error_wrappers import ValidationError
except ImportError:
    from pydantic import ValidationError  # pydantic v2

from biocognitive_core.config import get_settings
from biocognitive_core.exceptions import (BiocognitiveError, ConflictError,
           NotFoundError, PermissionDeniedError)

# Lazy imports to avoid circular dependency
def _get_metrics():
    from biocognitive_core.metrics import MetricsCollector
    return MetricsCollector()

def _get_logger(name):
    from infrastructure.observability import LoggerFactory
    return LoggerFactory.get_logger(name)

def _get_tracer(name):
    from infrastructure.observability import get_tracer
    return get_tracer(name)

def _get_encryption_service():
    from infrastructure.security import EncryptionService
    return EncryptionService

def _get_identity_verifier():
    from infrastructure.security import IdentityVerifier
    return IdentityVerifier

# Configure module logging with lazy initialization
logger = None
tracer = None
metrics = None

def _init_module():
    global logger, tracer, metrics
    if logger is None:
        logger = _get_logger(__name__)
    if tracer is None:
        tracer = _get_tracer(__name__)
    if metrics is None:
        metrics = _get_metrics()


def _traced(span_name: str):
    """Defer tracer span lookup to call time — safe when tracer is not yet initialised."""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                _init_module()
                _t = tracer
                if _t is not None:
                    try:
                        with _t.start_as_current_span(span_name):
                            return await func(*args, **kwargs)
                    except Exception:
                        pass
                return await func(*args, **kwargs)
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                _init_module()
                _t = tracer
                if _t is not None:
                    try:
                        with _t.start_as_current_span(span_name):
                            return func(*args, **kwargs)
                    except Exception:
                        pass
                return func(*args, **kwargs)
            return sync_wrapper
    return decorator


class Timer:
    """Monotonic wall-clock context manager. Stores elapsed seconds in self.elapsed."""

    def __init__(self):
        self.elapsed: float = 0.0
        self._start: float = 0.0

    def __enter__(self) -> "Timer":
        self._start = time.monotonic()
        return self

    def __exit__(self, *_):
        self.elapsed = time.monotonic() - self._start

class ConsentStatus(str, enum.Enum):
 """
 Status of consent between users
 
 Attributes:
  GRANTED: Active consent allowing thought transmission
  REVOKED: Previously granted consent that is now inactive
  EXPIRED: Consent that has reached its temporal limit
  PENDING: Consent request awaiting action
  DENIED: Explicit denial of consent request
 """
 GRANTED = "granted"
 REVOKED = "revoked"  
 EXPIRED = "expired"
 PENDING = "pending"
 DENIED = "denied"


class ThoughtDomain(str, enum.Enum):
 """
 Defined domains for thought transmission boundaries
 
 Each domain represents distinct categories of neural information
 that can be selectively shared between users.
 
 Attributes:
  SENSORY: Direct sensory perceptions (vision, hearing, etc.)
  EMOTIONAL: Affective states and emotional responses
  COGNITIVE: Explicit/analytical thought processes
  MEMORY: Access to episodic or semantic memories
  LINGUISTIC: Language formulation processes
  MOTOR: Motor planning and execution processes
  META: Thoughts about thoughts (metacognition)
 """
 SENSORY = "sensory"
 EMOTIONAL = "emotional"
 COGNITIVE = "cognitive"
 MEMORY = "memory"
 LINGUISTIC = "linguistic"
 MOTOR = "motor"
 META = "meta"
 
 @classmethod
 def validate_domains(cls, domains: Set[str]) -> Set["ThoughtDomain"]:
  """
  Validate that provided domains exist in the defined enum
  
  Args:
   domains: Set of domain string identifiers to validate
   
  Returns:
   Set of validated ThoughtDomain enum objects
   
  Raises:
   ValueError: If any provided domain is invalid
  """
  valid_domains = set()
  invalid_domains = set()
  
  for domain in domains:
   try:
    valid_domains.add(cls(domain))
   except ValueError:
    invalid_domains.add(domain)
    
  if invalid_domains:
   raise ValueError(f"Invalid thought domains: {', '.join(invalid_domains)}")
   
  return valid_domains


class ConsentScope(BaseModel):
 """
 Defines the granular scope of consent permissions
 
 Attributes:
  domains: Set of thought domains consent applies to
  temporal_limit: Optional time limit after which consent expires
  transmission_limit: Optional max number of transmissions allowed
  bandwidth_limit: Optional max data transfer rate (thoughts/second)
  recursion_depth: Max depth for nested thought access (0=surface only)
 """
 domains: Set[ThoughtDomain] = Field(...)
 temporal_limit: Optional[datetime] = Field(default=None)
 transmission_limit: Optional[int] = Field(default=None, ge=1)
 bandwidth_limit: Optional[float] = Field(default=None, gt=0)
 recursion_depth: int = Field(default=1, ge=0, le=5)
 
 @validator("domains")
 def validate_domains_not_empty(cls, v: Set[ThoughtDomain]) -> Set[ThoughtDomain]:
  """Ensures at least one thought domain is specified"""
  if not v:
   raise ValueError("At least one thought domain must be specified")
  return v
 

class ConsentRecord(BaseModel):
 """
 Data model for consent agreements between users
 
 Attributes:
  id: Unique identifier for this consent record
  grantor_id: ID of user granting consent
  grantee_id: ID of user receiving consent
  scope: Detailed permission scope
  status: Current status of this consent agreement
  created_at: Timestamp when consent was first established
  updated_at: Timestamp of last modification
  expires_at: Timestamp when consent automatically expires
  verification_hash: Cryptographic proof of consent authenticity
 """
 id: str = Field(default_factory=lambda: str(uuid.uuid4()))
 grantor_id: str
 grantee_id: str
 scope: ConsentScope
 status: ConsentStatus = Field(default=ConsentStatus.PENDING)
 created_at: datetime = Field(default_factory=datetime.utcnow)
 updated_at: datetime = Field(default_factory=datetime.utcnow)
 expires_at: Optional[datetime] = None
 verification_hash: str = Field(default_factory=lambda: secrets.token_hex(32))
 
 def is_valid(self) -> bool:
  """
  Check if this consent record is currently valid for transmission
  
  Returns:
   bool: True if consent is active and not expired
  """
  if self.status != ConsentStatus.GRANTED:
   return False
   
  if self.expires_at and self.expires_at <= datetime.utcnow():
   return False
   
  return True
 
 def calculate_verification_hash(self, secret_key: str) -> str:
  """
  Generate a cryptographic verification hash for this consent record
  
  Args:
   secret_key: Server-side secret used for hash generation
   
  Returns:
   str: Hexadecimal hash string
  """
  content = f"{self.grantor_id}:{self.grantee_id}:{self.created_at.isoformat()}"
  return hashlib.sha256(f"{content}:{secret_key}".encode()).hexdigest()
  

class ConsentValidationError(BiocognitiveError):
 """Base exception for consent validation errors"""
 pass


class InvalidDomainError(ConsentValidationError):
 """Exception raised when thought domain is invalid"""
 pass
 

class ExpiredConsentError(ConsentValidationError):
 """Exception raised when consent has expired"""
 pass


class InsufficientConsentError(ConsentValidationError):
 """Exception raised when consent does not cover requested domains"""
 pass


class ConsentRepository(ABC):
 """
 Abstract base interface for consent data storage
 """
 @abstractmethod
 async def create(self, consent: ConsentRecord) -> ConsentRecord:
  """Create a new consent record in storage"""
  pass
  
 @abstractmethod
 async def get(self, consent_id: str) -> Optional[ConsentRecord]:
  """Retrieve a consent record by ID"""
  pass
  
 @abstractmethod
 async def find_by_participants(
  self, 
  grantor_id: str, 
  grantee_id: str
 ) -> List[ConsentRecord]:
  """Find consent records between specific participants"""
  pass
 
 @abstractmethod
 async def find_by_grantor(self, grantor_id: str) -> List[ConsentRecord]:
  """Find all consent records granted by a user"""
  pass
  
 @abstractmethod
 async def find_by_grantee(self, grantee_id: str) -> List[ConsentRecord]:
  """Find all consent records granted to a user"""
  pass
  
 @abstractmethod  
 async def update(self, consent: ConsentRecord) -> ConsentRecord:
  """Update an existing consent record"""
  pass
  
 @abstractmethod
 async def delete(self, consent_id: str) -> bool:
  """Delete a consent record permanently"""
  pass


class DatabaseConsentRepository(ConsentRepository):
 """
 Implementation of consent repository using database storage
 """
 def __init__(self, db_pool, encryption_service: 'EncryptionService'):
  """
  Initialize the repository with a database connection pool
  
  Args:
   db_pool: Database connection pool
   encryption_service: Service for encrypting sensitive data
  """
  self.db_pool = db_pool
  self.encryption = encryption_service
  self.circuit_breaker = self._create_circuit_breaker()
  
 def _create_circuit_breaker(self):
  """Initialize circuit breaker for database resilience"""
  # Configure with appropriate thresholds and recovery strategy
  return CircuitBreaker(
   failure_threshold=5,
   recovery_timeout=30,
   expected_exception=Exception,
   name="consent-db"
  )
  
 @asynccontextmanager
 async def _get_connection(self):
  """Acquire a database connection from the pool with timeout handling"""
  start = time.monotonic()
  try:
   async with self.db_pool.acquire() as conn:
    yield conn
  except Exception as e:
   elapsed = time.monotonic() - start
   logger.error(
    f"Database connection acquisition failed after {elapsed:.2f}s", 
    exc_info=e
   )
   metrics.increment("db.connection.failure")
   raise
  finally:
   elapsed = time.monotonic() - start
   metrics.timing("db.connection.time", elapsed)
 
 @_traced("consent_repository.create")
 async def create(self, consent: ConsentRecord) -> ConsentRecord:
  """
  Create a new consent record in the database
  
  Args:
   consent: The consent record to store
   
  Returns:
   ConsentRecord: The stored record with generated ID
   
  Raises:
   ConflictError: If a record with this ID already exists
  """
  query = """
  INSERT INTO consent_records (
   id, grantor_id, grantee_id, scope, status, 
   created_at, updated_at, expires_at, verification_hash
  ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
  RETURNING id
  """
  
  encrypted_scope = self.encryption.encrypt(consent.scope.json())
  
  async with self._get_connection() as conn:
   try:
    result = await conn.fetchval(
     query,
     consent.id,
     consent.grantor_id,
     consent.grantee_id,
     encrypted_scope,
     consent.status,
     consent.created_at,
     consent.updated_at,
     consent.expires_at,
     consent.verification_hash
    )
    
    metrics.increment("consent.created")
    logger.info(f"Created consent record {consent.id} between "
         f"{consent.grantor_id} and {consent.grantee_id}")
    return consent
    
   except Exception as e:
    if "duplicate key" in str(e).lower():
     raise ConflictError(f"Consent record already exists: {consent.id}")
    logger.error(f"Failed to create consent record: {e}", exc_info=True)
    metrics.increment("consent.creation.error")
    raise
 
 @_traced("consent_repository.get")
 async def get(self, consent_id: str) -> Optional[ConsentRecord]:
  """
  Retrieve a consent record by ID
  
  Args:
   consent_id: The unique identifier of the record
   
  Returns:
   Optional[ConsentRecord]: The found record or None if not found
  """
  query = """
  SELECT id, grantor_id, grantee_id, scope, status, 
      created_at, updated_at, expires_at, verification_hash
  FROM consent_records
  WHERE id = $1
  """
  
  async with self._get_connection() as conn:
   try:
    row = await conn.fetchrow(query, consent_id)
    if not row:
     return None
    
    # Decrypt the scope data
    scope_json = self.encryption.decrypt(row['scope'])
    scope = ConsentScope.parse_raw(scope_json)
    
    return ConsentRecord(
     id=row['id'],
     grantor_id=row['grantor_id'],
     grantee_id=row['grantee_id'],
     scope=scope,
     status=ConsentStatus(row['status']),
     created_at=row['created_at'],
     updated_at=row['updated_at'],
     expires_at=row['expires_at'],
     verification_hash=row['verification_hash']
    )
    
   except Exception as e:
    logger.error(f"Failed to retrieve consent record {consent_id}: {e}", 
       exc_info=True)
    metrics.increment("consent.retrieval.error")
    raise
 
 @_traced("consent_repository.find_by_participants")
 async def find_by_participants(
  self, 
  grantor_id: str, 
  grantee_id: str
 ) -> List[ConsentRecord]:
  """
  Find consent records between specific participants
  
  Args:
   grantor_id: ID of the user granting consent
   grantee_id: ID of the user receiving consent
   
  Returns:
   List[ConsentRecord]: List of matching consent records
  """
  query = """
  SELECT id, grantor_id, grantee_id, scope, status, 
      created_at, updated_at, expires_at, verification_hash
  FROM consent_records
  WHERE grantor_id = $1 AND grantee_id = $2
  """
  
  async with self._get_connection() as conn:
   records = []
   rows = await conn.fetch(query, grantor_id, grantee_id)
   
   for row in rows:
    # Decrypt the scope data
    scope_json = self.encryption.decrypt(row['scope'])
    scope = ConsentScope.parse_raw(scope_json)
    
    records.append(ConsentRecord(
     id=row['id'],
     grantor_id=row['grantor_id'],
     grantee_id=row['grantee_id'],
     scope=scope,
     status=ConsentStatus(row['status']),
     created_at=row['created_at'],
     updated_at=row['updated_at'],
     expires_at=row['expires_at'],
     verification_hash=row['verification_hash']
    ))
   
   return records
 
 # Implementation of other repository methods follows similar pattern...
 
 @_traced("consent_repository.find_by_grantor")
 async def find_by_grantor(self, grantor_id: str) -> List[ConsentRecord]:
  """Find all consent records granted by a user"""
  query = """
  SELECT id, grantor_id, grantee_id, scope, status, 
      created_at, updated_at, expires_at, verification_hash
  FROM consent_records
  WHERE grantor_id = $1
  """
  
  async with self._get_connection() as conn:
   records = []
   rows = await conn.fetch(query, grantor_id)
   
   for row in rows:
    # Decrypt the scope data
    scope_json = self.encryption.decrypt(row['scope'])
    scope = ConsentScope.parse_raw(scope_json)
    
    records.append(ConsentRecord(
     id=row['id'],
     grantor_id=row['grantor_id'],
     grantee_id=row['grantee_id'],
     scope=scope,
     status=ConsentStatus(row['status']),
     created_at=row['created_at'],
     updated_at=row['updated_at'],
     expires_at=row['expires_at'],
     verification_hash=row['verification_hash']
    ))
   
   return records
 
 @_traced("consent_repository.find_by_grantee")
 async def find_by_grantee(self, grantee_id: str) -> List[ConsentRecord]:
  """Find all consent records granted to a user"""
  query = """
  SELECT id, grantor_id, grantee_id, scope, status, 
      created_at, updated_at, expires_at, verification_hash
  FROM consent_records
  WHERE grantee_id = $1
  """
  
  async with self._get_connection() as conn:
   records = []
   rows = await conn.fetch(query, grantee_id)
   
   for row in rows:
    # Decrypt the scope data
    scope_json = self.encryption.decrypt(row['scope'])
    scope = ConsentScope.parse_raw(scope_json)
    
    records.append(ConsentRecord(
     id=row['id'],
     grantor_id=row['grantor_id'],
     grantee_id=row['grantee_id'],
     scope=scope,
     status=ConsentStatus(row['status']),
     created_at=row['created_at'],
     updated_at=row['updated_at'],
     expires_at=row['expires_at'],
     verification_hash=row['verification_hash']
    ))
   
   return records
 
 @_traced("consent_repository.update")
 async def update(self, consent: ConsentRecord) -> ConsentRecord:
  """Update an existing consent record"""
  query = """
  UPDATE consent_records
  SET grantor_id = $2,
   grantee_id = $3,
   scope = $4,
   status = $5,
   updated_at = $6,
   expires_at = $7,
   verification_hash = $8
  WHERE id = $1
  RETURNING id
  """
  
  encrypted_scope = self.encryption.encrypt(consent.scope.json())
  consent.updated_at = datetime.utcnow()
  
  async with self._get_connection() as conn:
   try:
    result = await conn.fetchval(
     query,
     consent.id,
     consent.grantor_id,
     consent.grantee_id,
     encrypted_scope,
     consent.status,
     consent.updated_at,
     consent.expires_at,
     consent.verification_hash
    )
    
    if not result:
     raise NotFoundError(f"Consent record not found: {consent.id}")
    
    metrics.increment("consent.updated")
    logger.info(f"Updated consent record {consent.id}")
    return consent
    
   except Exception as e:
    if not isinstance(e, NotFoundError):
     logger.error(f"Failed to update consent record: {e}", exc_info=True)
     metrics.increment("consent.update.error")
    raise
 
 @_traced("consent_repository.delete")
 async def delete(self, consent_id: str) -> bool:
  """Delete a consent record permanently"""
  query = """
  DELETE FROM consent_records
  WHERE id = $1
  RETURNING id
  """
  
  async with self._get_connection() as conn:
   try:
    result = await conn.fetchval(query, consent_id)
    
    if not result:
     raise NotFoundError(f"Consent record not found: {consent_id}")
    
    metrics.increment("consent.deleted")
    logger.info(f"Deleted consent record {consent_id}")
    return True
    
   except Exception as e:
    if not isinstance(e, NotFoundError):
     logger.error(f"Failed to delete consent record: {e}", exc_info=True)
     metrics.increment("consent.deletion.error")
    raise


class ConsentEngine:
 """
 Core consent management and enforcement engine
 
 This class provides the central logic for establishing, validating,
 and enforcing consent between participants in the Neural Transparency
 Protocol system.
 """
 def __init__(
  self,
  repository: ConsentRepository,
  identity_verifier: IdentityVerifier,
  settings: Optional[BaseSettings] = None
 ):
  """
  Initialize the consent engine with required dependencies
  
  Args:
   repository: Storage implementation for consent records
   identity_verifier: Service to verify user identity
   settings: Configuration settings (uses defaults if None)
  """
  self.repository = repository
  self.identity_verifier = identity_verifier
  self.settings = settings or get_settings()
  self.secret_key = self.settings.security.consent_secret_key
  self._setup_observers()
  
 def _setup_observers(self):
  """Initialize consent event observers"""
  self._observers = {
   "consent_granted": [],
   "consent_revoked": [],
   "consent_expired": [],
   "consent_requested": [],
   "consent_denied": []
  }
 
 def register_observer(self, event_type: str, callback: Callable):
  """
  Register a callback function for specific consent events
  
  Args:
   event_type: Event to subscribe to
   callback: Function to call when event occurs
  """
  if event_type not in self._observers:
   raise ValueError(f"Unknown event type: {event_type}")
   
  self._observers[event_type].append(callback)
  
 def _notify_observers(self, event_type: str, consent: ConsentRecord):
  """
  Notify all observers of a consent event
  
  Args:
   event_type: Type of event that occurred
   consent: Consent record associated with the event
  """
  if event_type not in self._observers:
   return
   
  for callback in self._observers[event_type]:
   try:
    callback(consent)
   except Exception as e:
    logger.error(f"Error in observer callback: {e}", exc_info=True)
    metrics.increment("consent.observer.error")
    # Continue with other observers despite error
 
 @_traced("consent_engine.request_consent")
 async def request_consent(
  self,
  grantor_id: str,
  grantee_id: str,
  scope: ConsentScope
 ) -> ConsentRecord:
  """
  Create a new consent request between users
  
  Args:
   grantor_id: ID of user granting consent
   grantee_id: ID of user receiving consent
   scope: Detailed permission scope
   
  Returns:
   ConsentRecord: The new consent record with status PENDING
   
  Raises:
   ValueError: If request parameters are invalid
  """
  # Validate input
  if not grantor_id or not grantee_id:
   raise ValueError("Grantor and grantee IDs must be provided")
   
  if grantor_id == grantee_id:
   raise ValueError("Grantor and grantee must be different users")
   
  # Verify both users exist
  await self.identity_verifier.verify_user_exists(grantor_id)
  await self.identity_verifier.verify_user_exists(grantee_id)
  
  # Create consent record with PENDING status
  consent = ConsentRecord(
   grantor_id=grantor_id,
   grantee_id=grantee_id,
   scope=scope,
   status=ConsentStatus.PENDING,
   expires_at=(
    datetime.utcnow() + timedelta(days=30) 
    if not scope.temporal_limit 
    else scope.temporal_limit
   )
  )
  
  # Set verification hash
  consent.verification_hash = consent.calculate_verification_hash(self.secret_key)
  
  # Save to repository
  created_consent = await self.repository.create(consent)
  
  # Notify observers
  self._notify_observers("consent_requested", created_consent)
  
  # Track metrics
  domains_str = ",".join(d.value for d in scope.domains)
  metrics.increment(
   "consent.requested", 
   tags={"domains": domains_str, "recursion_depth": scope.recursion_depth}
  )
  
  logger.info(
   f"Consent requested from {grantor_id} to {grantee_id} "
   f"for domains: {domains_str}"
  )
  
  return created_consent
 
 @_traced("consent_engine.grant_consent")
 async def grant_consent(self, consent_id: str) -> ConsentRecord:
  """
  Grant a pending consent request
  
  Args:
   consent_id: ID of the consent record to grant
   
  Returns:
   ConsentRecord: The updated consent record
   
  Raises:
   NotFoundError: If consent record doesn't exist
   ValueError: If consent is not in PENDING status
  """
  # Get the consent record
  consent = await self.repository.get(consent_id)
  if not consent:
   raise NotFoundError(f"Consent record not found: {consent_id}")
   
  # Verify it's in PENDING status
  if consent.status != ConsentStatus.PENDING:
   raise ValueError(
    f"Cannot grant consent with status {consent.status}. "
    "Only PENDING consent can be granted."
   )
   
  # Update status
  consent.status = ConsentStatus.GRANTED
  consent.updated_at = datetime.utcnow()
  
  # Save to repository
  updated_consent = await self.repository.update(consent)
  
  # Notify observers
  self._notify_observers("consent_granted", updated_consent)
  
  # Track metrics
  domains_str = ",".join(d.value for d in consent.scope.domains)
  metrics.increment(
   "consent.granted", 
   tags={"domains": domains_str}
  )
  
  logger.info(
   f"Consent granted from {consent.grantor_id} to {consent.grantee_id} "
   f"for domains: {domains_str}"
  )
  
  return updated_consent
 
 @_traced("consent_engine.revoke_consent")
 async def revoke_consent(self, consent_id: str) -> ConsentRecord:
  """
  Revoke a previously granted consent
  
  Args:
   consent_id: ID of the consent record to revoke
   
  Returns:
   ConsentRecord: The updated consent record
   
  Raises:
   NotFoundError: If consent record doesn't exist
  """
  # Get the consent record
  consent = await self.repository.get(consent_id)
  if not consent:
   raise NotFoundError(f"Consent record not found: {consent_id}")
   
  # Update status
  consent.status = ConsentStatus.REVOKED
  consent.updated_at = datetime.utcnow()
  
  # Save to repository
  updated_consent = await self.repository.update(consent)
  
  # Notify observers
  self._notify_observers("consent_revoked", updated_consent)
  
  # Track metrics
  domains_str = ",".join(d.value for d in consent.scope.domains)
  metrics.increment(
   "consent.revoked", 
   tags={"domains": domains_str}
  )
  
  logger.info(
   f"Consent revoked from {consent.grantor_id} to {consent.grantee_id} "
   f"for domains: {domains_str}"
  )
  
  return updated_consent
 
 @_traced("consent_engine.deny_consent")
 async def deny_consent(self, consent_id: str) -> ConsentRecord:
  """
  Deny a pending consent request
  
  Args:
   consent_id: ID of the consent record to deny
   
  Returns:
   ConsentRecord: The updated consent record
   
  Raises:
   NotFoundError: If consent record doesn't exist
   ValueError: If consent is not in PENDING status
  """
  # Get the consent record
  consent = await self.repository.get(consent_id)
  if not consent:
   raise NotFoundError(f"Consent record not found: {consent_id}")
   
  # Verify it's in PENDING status
  if consent.status != ConsentStatus.PENDING:
   raise ValueError(
    f"Cannot deny consent with status {consent.status}. "
    "Only PENDING consent can be denied."
   )
   
  # Update status
  consent.status = ConsentStatus.DENIED
  consent.updated_at = datetime.utcnow()
  
  # Save to repository
  updated_consent = await self.repository.update(consent)
  
  # Notify observers
  self._notify_observers("consent_denied", updated_consent)
  
  # Track metrics
  domains_str = ",".join(d.value for d in consent.scope.domains)
  metrics.increment(
   "consent.denied", 
   tags={"domains": domains_str}
  )
  
  logger.info(
   f"Consent denied from {consent.grantor_id} to {consent.grantee_id} "
   f"for domains: {domains_str}"
  )
  
  return updated_consent
 
 @_traced("consent_engine.validate_consent")
 async def validate_consent(
  self,
  grantor_id: str,
  grantee_id: str,
  requested_domains: Set[ThoughtDomain],
  recursion_depth: int = 0
 ) -> bool:
  """
  Validate if consent exists for the specified thought domains
  
  Args:
   grantor_id: ID of user granting consent
   grantee_id: ID of user receiving consent
   requested_domains: Domains to validate consent for
   recursion_depth: Nested thought access depth required
   
  Returns:
   bool: True if valid consent exists, False otherwise
   
  Raises:
   ConsentValidationError: For specific validation failures
  """
  with Timer() as timer:
   # Verify domains are valid
   try:
    ThoughtDomain.validate_domains(set(d.value for d in requested_domains))
   except ValueError as e:
    raise InvalidDomainError(str(e))
    
   # Find consent records between these participants
   records = await self.repository.find_by_participants(grantor_id, grantee_id)
   
   # Filter for active records
   active_records = [r for r in records if r.status == ConsentStatus.GRANTED]
   
   if not active_records:
    logger.info(f"No active consent found from {grantor_id} to {grantee_id}")
    return False
    
   # Check for expired records
   now = datetime.utcnow()
   valid_records = []
   for record in active_records:
    if record.expires_at and record.expires_at <= now:
     # Mark as expired in database
     record.status = ConsentStatus.EXPIRED
     record.updated_at = now
     await self.repository.update(record)
     self._notify_observers("consent_expired", record)
     metrics.increment("consent.expired")
     logger.info(f"Consent {record.id} has expired")
    else:
     valid_records.append(record)
   
   if not valid_records:
    raise ExpiredConsentError("All consent records have expired")
   
   # Check domain coverage
   covered_domains = set()
   sufficient_depth = False
   
   for record in valid_records:
    covered_domains.update(record.scope.domains)
    if record.scope.recursion_depth >= recursion_depth:
     sufficient_depth = True
   
   # Verify all requested domains are covered
   missing_domains = set(requested_domains) - covered_domains
   if missing_domains:
    missing_str = ", ".join(d.value for d in missing_domains)
    logger.info(
     f"Insufficient consent from {grantor_id} to {grantee_id}. "
     f"Missing domains: {missing_str}"
    )
    raise InsufficientConsentError(
     f"Consent does not cover domains: {missing_str}"
    )
   
   # Verify recursion depth
   if not sufficient_depth:
    logger.info(
     f"Insufficient recursion depth from {grantor_id} to {grantee_id}. "
     f"Required: {recursion_depth}"
    )
    raise InsufficientConsentError(
     f"Consent does not allow recursion depth of {recursion_depth}"
    )
   
   logger.info(
    f"Consent validated from {grantor_id} to {grantee_id} "
    f"for {len(requested_domains)} domains with depth {recursion_depth}"
   )
   return True
  
  # The finally block below was orphaned - move timing to after return
  # Record timing metrics when method completes
  # Note: Timer context manager handles this automatically
 
 @contextmanager
 def transmission_session(
  self,
  grantor_id: str,
  grantee_id: str,
  domains: Set[ThoughtDomain],
  recursion_depth: int = 0
 ):
  """
  Context manager for thought transmission sessions
  
  Args:
   grantor_id: ID of user granting consent
   grantee_id: ID of user receiving consent
   domains: Domains to validate consent for
   recursion_depth: Nested thought access depth required
   
  Yields:
   Session object with transmission metadata
   
  Raises:
   ConsentValidationError: For consent validation failures
  """
  session_id = str(uuid.uuid4())
  start_time = time.monotonic()
  
  try:
   # Validate consent synchronously (blocks until validation complete)
   loop = asyncio.get_event_loop()
   loop.run_until_complete(self.validate_consent(
    grantor_id, grantee_id, domains, recursion_depth
   ))
   
   # Create session object
   session = {
    "id": session_id,
    "grantor_id": grantor_id,
    "grantee_id": grantee_id,
    "domains": domains,
    "recursion_depth": recursion_depth,
    "start_time": start_time,
    "transmitted_thoughts": 0
   }
   
   logger.info(f"Thought transmission session {session_id} started")
   metrics.increment("transmission.session.started")
   
   yield session
   
  except ConsentValidationError as e:
   logger.warning(
    f"Consent validation failed for {grantor_id} to {grantee_id}: {str(e)}"
   )
   metrics.increment("transmission.session.denied")
   raise
   
  finally:
   # Record session metrics
   elapsed = time.monotonic() - start_time
   metrics.timing(
    "transmission.session.duration", 
    elapsed,
    tags={
     "grantor": grantor_id,
     "grantee": grantee_id,
     "domain_count": len(domains)
    }
   )
   logger.info(f"Thought transmission session {session_id} ended after {elapsed:.2f}s")


# Circuit breaker implementation
class CircuitBreaker:
 """
 Circuit breaker pattern implementation for service resilience
 
 Monitors for failures in an operation and prevents the operation
 from being performed when failures exceed threshold.
 """
 def __init__(
  self,
  failure_threshold: int = 5,
  recovery_timeout: float = 30.0,
  expected_exception: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
  name: str = "default"
 ):
  """
  Initialize a new circuit breaker
  
  Args:
   failure_threshold: Number of failures before opening circuit
   recovery_timeout: Seconds before trying to close circuit
   expected_exception: Exception types to count as failures
   name: Identifier for this circuit breaker
  """
  self.failure_threshold = failure_threshold
  self.recovery_timeout = recovery_timeout
  self.expected_exception = expected_exception
  self.name = name
  
  self.failure_count = 0
  self.last_failure_time = 0
  self._state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
  self._lock = asyncio.Lock()
 
 @property
 def state(self) -> str:
  """Get the current state of the circuit breaker"""
  return self._state
  
 async def execute(self, func, *args, **kwargs):
  """
  Execute a function with circuit breaker protection
  
  Args:
   func: Async function to execute
   *args: Arguments to pass to the function
   **kwargs: Keyword arguments to pass to the function
   
  Returns:
   The result of the function execution
   
  Raises:
   CircuitOpenError: If circuit is open
   Any exception raised by the function
  """
  async with self._lock:
   if self._state == "OPEN":
    if time.time() - self.last_failure_time > self.recovery_timeout:
     logger.info(f"Circuit {self.name} trying half-open state")
     self._state = "HALF_OPEN"
    else:
     raise CircuitOpenError(f"Circuit {self.name} is OPEN")
  
  try:
   result = await func(*args, **kwargs)
   
   # Success - reset if in half-open state
   if self._state == "HALF_OPEN":
    async with self._lock:
     logger.info(f"Circuit {self.name} closing")
     self._state = "CLOSED"
     self.failure_count = 0
     
   return result
   
  except self.expected_exception as e:
   async with self._lock:
    self.failure_count += 1
    self.last_failure_time = time.time()
    
    if self._state == "HALF_OPEN" or self.failure_count >= self.failure_threshold:
     self._state = "OPEN"
     logger.warning(
      f"Circuit {self.name} opened after {self.failure_count} failures"
     )
     metrics.increment("circuit_breaker.opened", tags={"name": self.name})
     
   raise


class CircuitOpenError(Exception):
 """Exception raised when a circuit breaker is open"""
 pass


class ConsentLevel(int, enum.Enum):
    """Hierarchical consent level for quick classification."""
    NONE = 0
    BASIC = 1
    STANDARD = 2
    ENHANCED = 3
    FULL = 4


# Backward-compatibility alias — receiver.py imports ConsentDomain
ConsentDomain = ThoughtDomain


class InMemoryConsentRepository(ConsentRepository):
    """
    Thread-safe in-memory consent repository.

    No external database required — the default for Rosemary. All ConsentRecord
    objects are kept in a dict keyed by UUID, protected by an asyncio.Lock.
    """

    def __init__(self):
        self._store: Dict[str, ConsentRecord] = {}
        self._lock = asyncio.Lock()

    async def create(self, consent: ConsentRecord) -> ConsentRecord:
        async with self._lock:
            if consent.id in self._store:
                raise ConflictError(f"Consent record already exists: {consent.id}")
            self._store[consent.id] = consent
            return consent

    async def get(self, consent_id: str) -> Optional[ConsentRecord]:
        async with self._lock:
            return self._store.get(consent_id)

    async def find_by_participants(
        self, grantor_id: str, grantee_id: str
    ) -> List[ConsentRecord]:
        async with self._lock:
            return [
                r for r in self._store.values()
                if r.grantor_id == grantor_id and r.grantee_id == grantee_id
            ]

    async def find_by_grantor(self, grantor_id: str) -> List[ConsentRecord]:
        async with self._lock:
            return [r for r in self._store.values() if r.grantor_id == grantor_id]

    async def find_by_grantee(self, grantee_id: str) -> List[ConsentRecord]:
        async with self._lock:
            return [r for r in self._store.values() if r.grantee_id == grantee_id]

    async def update(self, consent: ConsentRecord) -> ConsentRecord:
        async with self._lock:
            if consent.id not in self._store:
                raise NotFoundError(f"Consent record not found: {consent.id}")
            self._store[consent.id] = consent
            return consent

    async def delete(self, consent_id: str) -> bool:
        async with self._lock:
            if consent_id not in self._store:
                raise NotFoundError(f"Consent record not found: {consent_id}")
            del self._store[consent_id]
            return True


class ConsentManagementEngine:
    """
    Self-contained consent management engine for NTP transmission control.

    Zero-dependency constructor — uses InMemoryConsentRepository internally.
    Provides check_consent / get_consent_level / grant_full_consent / revoke_consent
    as async methods consumed by NeuralReceiver and NeuralInterface.
    """

    def __init__(self):
        self._repo: ConsentRepository = InMemoryConsentRepository()
        self._logger = logging.getLogger(__name__ + ".ConsentManagementEngine")

    # ------------------------------------------------------------------ internal

    async def _active_records(
        self, grantor_id: str, grantee_id: str
    ) -> List[ConsentRecord]:
        """Return currently GRANTED, non-expired records between two parties."""
        records = await self._repo.find_by_participants(grantor_id, grantee_id)
        now = datetime.utcnow()
        valid: List[ConsentRecord] = []
        for r in records:
            if r.status != ConsentStatus.GRANTED:
                continue
            if r.expires_at and r.expires_at <= now:
                r.status = ConsentStatus.EXPIRED
                r.updated_at = now
                await self._repo.update(r)
                self._logger.debug("Consent %s expired", r.id)
                continue
            valid.append(r)
        return valid

    # ------------------------------------------------------------------ public API

    async def check_consent(
        self,
        sender_id: str,
        receiver_id: str,
        domain: "ThoughtDomain",
    ) -> bool:
        """Return True if sender has active consent to transmit domain to receiver."""
        records = await self._active_records(sender_id, receiver_id)
        for record in records:
            if domain in record.scope.domains:
                return True
        return False

    async def get_consent_level(
        self, sender_id: str, receiver_id: str
    ) -> ConsentLevel:
        """Return the highest ConsentLevel currently active from sender to receiver."""
        records = await self._active_records(sender_id, receiver_id)
        if not records:
            return ConsentLevel.NONE
        covered: Set[ThoughtDomain] = set()
        for r in records:
            covered.update(r.scope.domains)
        all_domains = set(ThoughtDomain)
        ratio = len(covered) / max(len(all_domains), 1)
        if ratio >= 1.0:
            return ConsentLevel.FULL
        elif ratio >= 0.7:
            return ConsentLevel.ENHANCED
        elif ratio >= 0.4:
            return ConsentLevel.STANDARD
        elif ratio > 0:
            return ConsentLevel.BASIC
        return ConsentLevel.NONE

    async def grant_full_consent(
        self,
        grantor_id: str,
        grantee_id: str,
        duration_hours: int = 24,
    ) -> ConsentRecord:
        """Grant all-domain consent from grantor to grantee. Convenience method."""
        expires = datetime.utcnow() + timedelta(hours=duration_hours)
        scope = ConsentScope(
            domains=set(ThoughtDomain),
            temporal_limit=expires,
            recursion_depth=5,
        )
        record = ConsentRecord(
            grantor_id=grantor_id,
            grantee_id=grantee_id,
            scope=scope,
            status=ConsentStatus.GRANTED,
            expires_at=expires,
        )
        record.verification_hash = record.calculate_verification_hash(
            secrets.token_hex(16)
        )
        created = await self._repo.create(record)
        self._logger.info(
            "Full consent granted: %s → %s for %dh", grantor_id, grantee_id, duration_hours
        )
        return created

    async def revoke_consent(self, grantor_id: str, grantee_id: str) -> int:
        """Revoke all active consent records between two parties. Returns count revoked."""
        records = await self._repo.find_by_participants(grantor_id, grantee_id)
        count = 0
        for r in records:
            if r.status == ConsentStatus.GRANTED:
                r.status = ConsentStatus.REVOKED
                r.updated_at = datetime.utcnow()
                await self._repo.update(r)
                count += 1
        if count:
            self._logger.info(
                "Consent revoked: %s → %s (%d records)", grantor_id, grantee_id, count
            )
        return count


# Example usage (for documentation purposes)
async def usage_example():
 """Example usage of the consent management system"""
 # Set up dependencies
 from infrastructure.security import IdentityVerifier, EncryptionService
 import asyncpg
 
 # Initialize components
 db_pool = await asyncpg.create_pool(
  host='localhost',
  port=5432,
  user='postgres',
  password='secret',
  database='biocognitive',
  min_size=5,
  max_size=20
 )
 
 encryption_service = EncryptionService()
 identity_verifier = IdentityVerifier()
 
 # Create repository and engine
 repository = DatabaseConsentRepository(db_pool, encryption_service)
 consent_engine = ConsentEngine(repository, identity_verifier)
 
 # Request consent
 scope = ConsentScope(
  domains={ThoughtDomain.COGNITIVE, ThoughtDomain.EMOTIONAL},
  recursion_depth=2,
  temporal_limit=datetime.utcnow() + timedelta(days=7)
 )
 
 consent = await consent_engine.request_consent(
  grantor_id="user123",
  grantee_id="user456",
  scope=scope
 )
 
 # Grant consent
 granted_consent = await consent_engine.grant_consent(consent.id)
 
 # Validate consent for a transmission
 domains = {ThoughtDomain.COGNITIVE, ThoughtDomain.EMOTIONAL}
 is_valid = await consent_engine.validate_consent(
  grantor_id="user123",
  grantee_id="user456",
  requested_domains=domains,
  recursion_depth=1
 )
 
 # Use context manager for a thought transmission session
 try:
  with consent_engine.transmission_session(
   grantor_id="user123",
   grantee_id="user456",
   domains=domains,
   recursion_depth=1
  ) as session:
   # Perform thought transmission within this context
   pass
 except ConsentValidationError as e:
  print(f"Transmission denied: {e}")
  
 # Revoke consent
 await consent_engine.revoke_consent(consent.id)


if __name__ == "__main__":
 # This block is for testing and demonstration only
 logging.basicConfig(level=logging.INFO)
 asyncio.run(usage_example())