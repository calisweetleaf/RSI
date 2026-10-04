"""
Unified Sovereign Memory System (USMS)

A comprehensive production-ready memory architecture that merges three advanced systems:
1. Mycelial Temporal Lattice (MTL) - DAG-based memory with belief anchoring and auto-repair
2. Neural Memory Controller Architecture (NMCA) - Quantum-inspired techniques and thread safety
3. Sovereign Cognitive Lattice (SCL) - Chrono-Cognitive Lattice with epistemic weaving

This unified system preserves all core innovations while providing enterprise-grade
reliability, security, and performance.

Modified: 2026-07-14
Modified by: Codex for daeron
Justification: I hardened the canonical USMS identity, signing, authorization,
    and SQLite boundaries in place because wrapping them would leave insecure
    internal write paths reachable inside the source-of-truth kernel.
Provenance: implementation task "Production Completion Plan", USMS hardening
    workstream; verified by tests/test_usms_security_integrity.py.
Files: modules/unified_memory_system.py, tests/test_usms_security_integrity.py

Modified: 2026-09-11
Modified by: cursor-grok (daeron)
Justification: I repaired BinaryStorageManager._atomic_write because Windows
    cannot os.open() a directory as a POSIX directory fd. The sidecar write
    already fsyncs the file; skipping directory fsync on nt preserves the
    atomic replace contract without a wrapper that would fork storage.
Provenance: snapshots/v0.2/manifest.json -> domains.immune.edits[0]
Files: memory/unified_memory_system.py
"""

from __future__ import annotations

import hashlib
import math
import re
import uuid
import sqlite3
import json
import threading
import logging
import time
import datetime
import secrets
import zlib
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple, Set, Callable, Iterator
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from collections import deque, defaultdict
from contextlib import contextmanager, asynccontextmanager
from functools import wraps, lru_cache
import asyncio
import concurrent.futures
import psutil
import warnings
import copy
import bisect
import traceback
import os
import platform
import struct
import stat
import mmap
import tempfile
from filelock import FileLock

# Platform-specific imports
try:
    import fcntl
    from multiprocessing import Lock as MPLock
    UNIX_LOCKING_AVAILABLE = True
except ImportError:
    # Windows doesn't have fcntl - file locking handled by filelock
    UNIX_LOCKING_AVAILABLE = False

# Library imports are silent. Runtime handlers are attached only by explicit
# configuration or instance initialization under its owned runtime root.
logger = logging.getLogger("UnifiedSovereignMemory")
logger.addHandler(logging.NullHandler())
logger.propagate = False
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(threadName)s - %(funcName)s:%(lineno)d - %(message)s'


def configure_usms_console_logging(level: int = logging.INFO) -> None:
    """Attach the opt-in USMS console handler exactly once."""
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(
            handler, logging.FileHandler
        ) and not isinstance(handler, logging.NullHandler):
            handler.setLevel(level)
            return

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    console_handler.setLevel(level)
    logger.addHandler(console_handler)
    logger.setLevel(min(logging.DEBUG, level))


def configure_usms_file_logging(log_dir: Union[str, Path]) -> Path:
    """Attach a file logger under an explicit runtime directory."""
    resolved_log_dir = Path(log_dir).expanduser()
    resolved_log_dir.mkdir(parents=True, exist_ok=True)
    log_path = resolved_log_dir / "unified_sovereign_memory.log"
    resolved_log_path = log_path.resolve()

    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            handler_path = Path(handler.baseFilename).resolve()
            if handler_path == resolved_log_path:
                return log_path

    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.setLevel(logging.DEBUG)
    logger.info(f"Unified Sovereign Memory System file logging initialized at {log_path}")
    return log_path

# Cryptographic imports - mandatory for every sovereign operation.
try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
    from cryptography.hazmat.primitives import serialization
    from cryptography.exceptions import InvalidSignature
    CRYPTO_AVAILABLE = True
    CRYPTO_IMPORT_ERROR = None
    logger.info("Ed25519 cryptographic signatures enabled - production ready")
except ImportError as exc:
    CRYPTO_AVAILABLE = False
    CRYPTO_IMPORT_ERROR = exc
    logger.critical(
        "Ed25519 support is unavailable; sovereign identity operations will fail closed"
    )

# System constants
MEMORY_DB_PATH = Path("memory_store/unified_sovereign_memory.db")
MEMORY_PERSISTENCE_DIR = Path("memory_store/persistence")
MEMORY_BACKUP_DIR = Path("memory_store/backups")
MEMORY_LOG_DIR = Path("memory_store/logs")
MEMORY_LOCK_DIR = Path("memory_store/locks")
MEMORY_BINARY_DIR = Path("memory_store/binary_data")
MEMORY_CACHE_DIR = Path("memory_store/cache")

# Sidecars are untrusted persistence inputs during recovery.  These limits
# bound both on-disk reads and zlib expansion before NumPy/JSON allocation.
SEMANTIC_VECTOR_MAX_DIMENSIONS = 4_096
SEMANTIC_VECTOR_MAX_BYTES = SEMANTIC_VECTOR_MAX_DIMENSIONS * np.dtype(np.float32).itemsize
SEMANTIC_VECTOR_MAX_COMPRESSED_BYTES = 64 * 1024
JSON_SIDECAR_MAX_BYTES = 8 * 1024 * 1024
JSON_SIDECAR_MAX_COMPRESSED_BYTES = JSON_SIDECAR_MAX_BYTES + 64 * 1024


@dataclass(frozen=True)
class UnifiedMemoryPaths:
    """Resolved runtime paths for one USMS instance."""
    runtime_root: Path
    db_path: Path
    persistence_dir: Path
    backup_dir: Path
    log_dir: Path
    lock_dir: Path
    binary_dir: Path
    cache_dir: Path


def _normalize_runtime_root(runtime_root: Optional[Union[str, Path]]) -> Path:
    if runtime_root is None:
        return Path(".")
    return Path(runtime_root).expanduser()


def _runtime_path(runtime_root: Path, relative_path: Path) -> Path:
    if relative_path.is_absolute():
        return relative_path
    return runtime_root / relative_path


def resolve_memory_paths(
    runtime_root: Optional[Union[str, Path]] = None,
    db_path: Optional[Union[str, Path]] = None,
) -> UnifiedMemoryPaths:
    """Resolve all instance paths from an explicit runtime root."""
    root = _normalize_runtime_root(runtime_root)
    resolved_db_path = Path(db_path).expanduser() if db_path else MEMORY_DB_PATH
    return UnifiedMemoryPaths(
        runtime_root=root,
        db_path=_runtime_path(root, resolved_db_path),
        persistence_dir=_runtime_path(root, MEMORY_PERSISTENCE_DIR),
        backup_dir=_runtime_path(root, MEMORY_BACKUP_DIR),
        log_dir=_runtime_path(root, MEMORY_LOG_DIR),
        lock_dir=_runtime_path(root, MEMORY_LOCK_DIR),
        binary_dir=_runtime_path(root, MEMORY_BINARY_DIR),
        cache_dir=_runtime_path(root, MEMORY_CACHE_DIR),
    )


def ensure_memory_paths(paths: UnifiedMemoryPaths) -> None:
    """Create runtime directories for an initialized USMS instance."""
    for directory in [
        paths.db_path.parent,
        paths.persistence_dir,
        paths.backup_dir,
        paths.log_dir,
        paths.lock_dir,
        paths.binary_dir,
        paths.cache_dir,
    ]:
        directory.mkdir(parents=True, exist_ok=True)

# Schema versioning
CURRENT_SCHEMA_VERSION = 3
MIN_COMPATIBLE_VERSION = 1

# Memory layer constants
COLD_MEMORY = "cold_memory"
WARM_MEMORY = "warm_memory" 
HOT_MEMORY = "hot_memory"

# Quantum constants
DEFAULT_MAX_QUBITS = 128
CONSCIOUSNESS_THRESHOLD = 0.95
ENTROPY_THRESHOLD = 0.8
DEFAULT_BRANCH_COUNT = 3

# Performance constants
MAX_ACTIVE_CONTEXTS = 256
CONTEXT_TIMEOUT = 3600  # 1 hour
BACKUP_INTERVAL = 3600  # 1 hour
INTEGRITY_CHECK_INTERVAL = 300  # 5 minutes

# Memory relevance calculation weights
ALPHA = 0.4  # Frequency usage weight
BETA = 0.3   # Contextual utility weight
GAMMA = 0.2  # Cross domain connections weight
DELTA = 0.1  # Energy cost weight

# Default policy settings
DEFAULT_POLICY = {
    "anchor_threshold": 0.74,
    "anchor_support_min": 2,
    "contradiction_cosine": 0.82,
    # Canonical repair nodes must never be created from an untrained heuristic.
    # There is no approved repair policy or verifier in this release, so callers
    # must invoke an explicit, independently-authorized repair workflow instead.
    "repair_auto": False,
    "belief_half_life_days": 365.0,  # 1 year default
    "max_parents": 5,
    "coherence_network_threshold": 0.8,
    "epistemic_weaving_depth": 7,
    "consciousness_requirement": 0.85,
}

DEFAULT_BUSY_TIMEOUT_MS = 10_000
ACCESS_CONTROL_KEY = "access_control"
ACCESS_SCOPE_REGISTERED = "registered"
ACCESS_SCOPE_PRIVATE = "private"
ACCESS_SCOPE_EXPLICIT = "explicit"
VALID_ACCESS_SCOPES = frozenset(
    {ACCESS_SCOPE_REGISTERED, ACCESS_SCOPE_PRIVATE, ACCESS_SCOPE_EXPLICIT}
)


def _canonical_json_bytes(value: Any) -> bytes:
    """Serialize a JSON-shaped value into the one signed canonical form."""
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise MemoryIntegrityError(f"Value is not canonical JSON: {exc}") from exc

# Custom exceptions with proper hierarchy
class UnifiedMemoryError(Exception):
    """Base exception for all unified memory system errors."""
    pass

class MemoryIntegrityError(UnifiedMemoryError):
    """Raised when memory integrity is compromised."""
    pass

class CoherenceNetworkError(UnifiedMemoryError):
    """Raised when coherence network operations fail."""
    pass

class EpistemicWeavingError(UnifiedMemoryError):
    """Raised when epistemic weaving operations fail."""
    pass

class SovereignIdentityError(UnifiedMemoryError):
    """Raised when sovereign identity operations fail."""
    pass

class MemoryAccessError(UnifiedMemoryError):
    """Raised when memory access is denied or fails."""
    pass

class BeliefAnchoringError(UnifiedMemoryError):
    """Raised when belief anchoring operations fail."""
    pass

class CircuitBreakerError(UnifiedMemoryError):
    """Raised when circuit breaker prevents operation."""
    pass

class BinaryStorageError(UnifiedMemoryError):
    """Raised when binary storage operations fail."""
    pass

class ProcessCoordinationError(UnifiedMemoryError):
    """Raised when multi-process coordination fails."""
    pass

# Binary Storage and Process Coordination Classes

class BinaryStorageManager:
    """
    Optimizes storage of heavy JSON fields using binary formats and compression.
    Reduces storage footprint by 60-80% and improves I/O performance.
    """
    
    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Binary storage manager initialized at {storage_dir}")

    def _atomic_write(self, storage_path: Path, payload: bytes) -> None:
        """Durably replace one sidecar without exposing a partial file."""
        temporary_fd, temporary_name = tempfile.mkstemp(
            prefix=f".{storage_path.name}.",
            suffix=".tmp",
            dir=self.storage_dir,
        )
        try:
            with os.fdopen(temporary_fd, "wb") as temporary_file:
                temporary_file.write(payload)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_name, storage_path)
            if os.name != "nt":
                directory_fd = os.open(self.storage_dir, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
        except BaseException:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
            raise

    def _resolve_reference(self, ref_id: str, suffix: str) -> Path:
        """Resolve a content reference while rejecting traversal and malformed ids."""
        if not isinstance(ref_id, str) or not re.fullmatch(
            r"[A-Za-z0-9_-]+_[0-9a-f]{24}", ref_id
        ):
            raise BinaryStorageError(f"Malformed binary storage reference: {ref_id}")
        storage_root = self.storage_dir.resolve()
        storage_path = storage_root / f"{ref_id}{suffix}"
        try:
            storage_path.parent.relative_to(storage_root)
        except ValueError as exc:
            raise BinaryStorageError(
                f"Binary storage reference escapes its root: {ref_id}"
            ) from exc
        return storage_path

    @staticmethod
    def _decompress_bounded(
        compressed_data: bytes,
        *,
        maximum_output_bytes: int,
        description: str,
    ) -> bytes:
        """Decompress one complete zlib stream without allocating past its cap."""
        decompressor = zlib.decompressobj()
        output = decompressor.decompress(
            compressed_data,
            maximum_output_bytes + 1,
        )
        if len(output) > maximum_output_bytes or decompressor.unconsumed_tail:
            raise BinaryStorageError(
                f"{description} exceeds {maximum_output_bytes} decompressed bytes"
            )
        if not decompressor.eof:
            raise BinaryStorageError(f"{description} is truncated or incomplete")
        if decompressor.unused_data:
            raise BinaryStorageError(f"{description} has trailing compressed data")
        remaining = maximum_output_bytes - len(output)
        tail = decompressor.flush(remaining + 1)
        if len(tail) > remaining:
            raise BinaryStorageError(
                f"{description} exceeds {maximum_output_bytes} decompressed bytes"
            )
        return output + tail

    def _read_regular_sidecar(
        self,
        ref_id: str,
        suffix: str,
        *,
        maximum_bytes: int,
    ) -> bytes:
        """Read one bounded regular sidecar without following symbolic links."""
        storage_path = self._resolve_reference(ref_id, suffix)
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(storage_path, flags)
        except FileNotFoundError as exc:
            raise BinaryStorageError(
                f"Binary storage file not found: {ref_id}"
            ) from exc
        except OSError as exc:
            raise BinaryStorageError(
                f"Binary storage file cannot be opened safely: {ref_id}"
            ) from exc
        try:
            file_status = os.fstat(descriptor)
            if not stat.S_ISREG(file_status.st_mode):
                raise BinaryStorageError(
                    f"Binary storage path is not a regular file: {ref_id}"
                )
            if file_status.st_size > maximum_bytes:
                raise BinaryStorageError(
                    f"Binary storage file exceeds {maximum_bytes} bytes: {ref_id}"
                )
            with os.fdopen(descriptor, "rb", closefd=False) as handle:
                payload = handle.read(maximum_bytes + 1)
            if len(payload) > maximum_bytes:
                raise BinaryStorageError(
                    f"Binary storage file grew beyond {maximum_bytes} bytes: {ref_id}"
                )
            if len(payload) != file_status.st_size:
                raise BinaryStorageError(
                    f"Binary storage file changed while reading: {ref_id}"
                )
            return payload
        finally:
            os.close(descriptor)
    
    def store_semantic_vector(self, node_id: str, vector: List[float]) -> str:
        """Store semantic vector as binary data, return reference ID."""
        try:
            if not vector:
                return ""
            
            # Convert to numpy array and serialize
            array = np.array(vector, dtype=np.float32)
            if array.ndim != 1 or array.size > SEMANTIC_VECTOR_MAX_DIMENSIONS:
                raise BinaryStorageError(
                    "Semantic vector exceeds the production dimension bound"
                )
            binary_data = array.tobytes()
            
            # Compress using zlib
            compressed_data = zlib.compress(binary_data, level=6)
            
            # Generate storage reference
            ref_id = f"sv_{node_id}_{hashlib.sha256(binary_data).hexdigest()[:24]}"
            storage_path = self._resolve_reference(ref_id, ".bin")
            
            self._atomic_write(storage_path, compressed_data)
            
            logger.debug(f"Stored semantic vector {ref_id} ({len(binary_data)} -> {len(compressed_data)} bytes)")
            return ref_id
            
        except (OSError, TypeError, ValueError, zlib.error) as e:
            logger.error(f"Failed to store semantic vector for {node_id}: {e}")
            raise BinaryStorageError(f"Semantic vector storage failed: {e}") from e
    
    def load_semantic_vector(self, ref_id: str) -> List[float]:
        """Load semantic vector from binary storage."""
        try:
            if not ref_id:
                return []
            
            compressed_data = self._read_regular_sidecar(
                ref_id,
                ".bin",
                maximum_bytes=SEMANTIC_VECTOR_MAX_COMPRESSED_BYTES,
            )
            binary_data = self._decompress_bounded(
                compressed_data,
                maximum_output_bytes=SEMANTIC_VECTOR_MAX_BYTES,
                description=f"Semantic vector {ref_id}",
            )
            expected_digest = ref_id.rpartition("_")[2]
            actual_digest = hashlib.sha256(binary_data).hexdigest()[:24]
            if not expected_digest or not secrets.compare_digest(
                expected_digest, actual_digest
            ):
                raise BinaryStorageError(
                    f"Semantic vector checksum mismatch: {ref_id}"
                )
            if not binary_data or len(binary_data) % np.dtype(np.float32).itemsize:
                raise BinaryStorageError(
                    f"Semantic vector byte length is invalid: {ref_id}"
                )
            array = np.frombuffer(binary_data, dtype=np.float32)
            vector = array.tolist()
            return np.asarray(vector, dtype=np.float32).astype(float).tolist()

        except BinaryStorageError:
            raise
        except (OSError, ValueError, zlib.error) as e:
            logger.error(f"Failed to load semantic vector {ref_id}: {e}")
            raise BinaryStorageError(
                f"Semantic vector load failed for {ref_id}: {e}"
            ) from e
    
    def store_json_compressed(self, node_id: str, data: Dict[str, Any], data_type: str) -> str:
        """Store JSON data with compression, return reference ID."""
        try:
            if not data:
                return ""
            
            # Serialize to JSON
            json_data = _canonical_json_bytes(data)
            if len(json_data) > JSON_SIDECAR_MAX_BYTES:
                raise BinaryStorageError(
                    f"JSON sidecar exceeds {JSON_SIDECAR_MAX_BYTES} bytes"
                )
            
            # Compress using zlib
            compressed_data = zlib.compress(json_data, level=6)
            
            # Generate storage reference
            ref_id = f"{data_type}_{node_id}_{hashlib.sha256(json_data).hexdigest()[:24]}"
            storage_path = self._resolve_reference(ref_id, ".json.gz")
            
            self._atomic_write(storage_path, compressed_data)
            
            logger.debug(f"Stored {data_type} {ref_id} ({len(json_data)} -> {len(compressed_data)} bytes)")
            return ref_id
            
        except (MemoryIntegrityError, OSError, TypeError, ValueError, zlib.error) as e:
            logger.error(f"Failed to store {data_type} for {node_id}: {e}")
            raise BinaryStorageError(f"JSON storage failed: {e}") from e
    
    def load_json_compressed(self, ref_id: str) -> Dict[str, Any]:
        """Load JSON data from compressed storage."""
        try:
            if not ref_id:
                return {}
            
            compressed_data = self._read_regular_sidecar(
                ref_id,
                ".json.gz",
                maximum_bytes=JSON_SIDECAR_MAX_COMPRESSED_BYTES,
            )
            json_data = self._decompress_bounded(
                compressed_data,
                maximum_output_bytes=JSON_SIDECAR_MAX_BYTES,
                description=f"Compressed JSON {ref_id}",
            )
            expected_digest = ref_id.rpartition("_")[2]
            actual_digest = hashlib.sha256(json_data).hexdigest()[:24]
            if not expected_digest or not secrets.compare_digest(
                expected_digest, actual_digest
            ):
                raise BinaryStorageError(f"Compressed JSON checksum mismatch: {ref_id}")
            loaded_data = json.loads(json_data.decode("utf-8"))
            if not isinstance(loaded_data, dict):
                raise BinaryStorageError(f"Compressed JSON is not an object: {ref_id}")
            return loaded_data

        except BinaryStorageError:
            raise
        except (OSError, UnicodeDecodeError, ValueError, zlib.error) as e:
            logger.error(f"Failed to load compressed JSON {ref_id}: {e}")
            raise BinaryStorageError(
                f"Compressed JSON load failed for {ref_id}: {e}"
            ) from e

class MultiProcessCoordinator:
    """
    Manages multi-process coordination using file-based locking and shared state.
    Ensures process-safe operations while maintaining performance.
    """
    
    def __init__(self, lock_dir: Path):
        self.lock_dir = lock_dir
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        self._file_locks = {}
        self._process_id = os.getpid()
        self._lock_timeout = 30.0
        logger.info(f"Multi-process coordinator initialized for PID {self._process_id}")
    
    @contextmanager
    def database_lock(self, operation: str = "general"):
        """Context manager for database operations with process-safe locking."""
        lock_file = self.lock_dir / f"db_{operation}.lock"
        file_lock = FileLock(str(lock_file), timeout=self._lock_timeout)
        
        logger.debug(f"Acquiring database lock for {operation} (PID {self._process_id})")
        try:
            file_lock.acquire()
        except Exception as e:
            logger.error(f"Database lock failed for {operation}: {e}")
            raise ProcessCoordinationError(
                f"Database lock acquisition failed: {e}"
            ) from e
        try:
            yield
        finally:
            try:
                file_lock.release()
            except Exception as e:
                logger.error(f"Database lock release failed for {operation}: {e}")
                raise ProcessCoordinationError(
                    f"Database lock release failed: {e}"
                ) from e
        logger.debug(f"Released database lock for {operation} (PID {self._process_id})")
    
    @contextmanager
    def node_lock(self, node_id: str):
        """Context manager for node-specific operations."""
        # Use hash to avoid filesystem issues with long node IDs
        node_hash = hashlib.sha256(node_id.encode()).hexdigest()[:24]
        lock_file = self.lock_dir / f"node_{node_hash}.lock"
        file_lock = FileLock(str(lock_file), timeout=self._lock_timeout)
        
        logger.debug(f"Acquiring node lock for {node_id[:12]} (PID {self._process_id})")
        try:
            file_lock.acquire()
        except Exception as e:
            logger.error(f"Node lock failed for {node_id[:12]}: {e}")
            raise ProcessCoordinationError(f"Node lock acquisition failed: {e}") from e
        try:
            yield
        finally:
            try:
                file_lock.release()
            except Exception as e:
                logger.error(f"Node lock release failed for {node_id[:12]}: {e}")
                raise ProcessCoordinationError(
                    f"Node lock release failed: {e}"
                ) from e
        logger.debug(f"Released node lock for {node_id[:12]} (PID {self._process_id})")
    
    def create_process_marker(self) -> str:
        """Create a marker file indicating this process is active."""
        try:
            marker_id = f"process_{self._process_id}_{int(time.time())}"
            marker_file = self.lock_dir / f"{marker_id}.marker"
            
            with open(marker_file, 'w') as f:
                json.dump({
                    'pid': self._process_id,
                    'start_time': time.time(),
                    'hostname': platform.node()
                }, f)
            
            logger.info(f"Created process marker {marker_id}")
            return marker_id
            
        except Exception as e:
            logger.error(f"Failed to create process marker: {e}")
            raise ProcessCoordinationError(f"Process marker creation failed: {e}")
    
    def cleanup_process_marker(self, marker_id: str):
        """Clean up process marker on shutdown."""
        try:
            marker_file = self.lock_dir / f"{marker_id}.marker"
            if marker_file.exists():
                marker_file.unlink()
                logger.info(f"Cleaned up process marker {marker_id}")
        except Exception as e:
            logger.warning(f"Failed to cleanup process marker {marker_id}: {e}")
    
    def get_active_processes(self) -> List[Dict[str, Any]]:
        """Get list of currently active processes."""
        try:
            processes = []
            for marker_file in self.lock_dir.glob("process_*.marker"):
                try:
                    with open(marker_file, 'r') as f:
                        process_info = json.load(f)
                    
                    # Check if process is still alive
                    try:
                        if psutil.pid_exists(process_info['pid']):
                            processes.append(process_info)
                        else:
                            # Cleanup stale marker
                            marker_file.unlink()
                            logger.debug(f"Removed stale process marker {marker_file.name}")
                    except (psutil.NoSuchProcess, OSError):
                        marker_file.unlink()
                        
                except Exception as e:
                    logger.warning(f"Error reading process marker {marker_file}: {e}")
            
            return processes
            
        except Exception as e:
            logger.error(f"Failed to get active processes: {e}")
            return []

# Enums for system states and types
class MemoryLayerEnum(str, Enum):
    """Memory layers with different access characteristics."""
    COLD = COLD_MEMORY
    WARM = WARM_MEMORY
    HOT = HOT_MEMORY

class MemoryAccessLevelEnum(str, Enum):
    """Fine-grained memory access permissions."""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"
    MODIFY_METADATA = "modify_metadata"
    LINK = "link"
    UNLINK = "unlink"
    COHERENCE_BIND = "coherence_bind"
    EPISTEMIC_WEAVE = "epistemic_weave"

class CircuitBreakerState(Enum):
    """Circuit breaker states for fault tolerance."""
    CLOSED = auto()    # Normal operation
    OPEN = auto()      # Blocking operations
    HALF_OPEN = auto() # Testing recovery

class NodeKindEnum(str, Enum):
    """Types of memory nodes in the unified system."""
    EVENT = "event"
    BELIEF = "belief"
    META = "meta"
    REPAIR = "repair"
    SNAPSHOT = "snapshot"
    COHERENCE_STATE = "coherence_state"
    EPISTEMIC_LINK = "epistemic_link"
    COGNITIVE_STRAND = "cognitive_strand"

class LinkageTypeEnum(str, Enum):
    """Types of relationships between memory nodes."""
    TEMPORAL_PARENT = "temporal_parent"
    CAUSAL_PARENT = "causal_parent"
    EPISTEMIC_PARENT = "epistemic_parent"
    SEMANTIC_SIMILAR = "semantic_similar"
    CONTRADICTION = "contradiction"
    SYNTHESIS = "synthesis"
    COHERENCE_BOUND = "coherence_bound"

# Core data structures
@dataclass
class UnifiedMemoryNode:
    """
    Unified memory node structure that combines features from all three systems:
    - MTL's Block with semantic vectors and belief anchoring
    - NMCA's MemoryNode with coherence network processing and thread safety
    - SCL's CognitiveStrand with multi-dimensional linkage
    """
    node_id: str
    author_id: str
    kind: NodeKindEnum
    timestamp: str
    content: Dict[str, Any]
    
    # MTL features
    semantic_vector: List[float]
    meta_patch: Dict[str, Any]
    parents: List[str]
    
    # NMCA features
    frequency_usage: float
    contextual_utility: float
    cross_domain_connections: int
    energy_cost: float
    last_access_timestamp: float
    access_count: int
    
    # SCL features
    linkage_manifest: Dict[LinkageTypeEnum, List[str]]
    belief_state_hash: str
    sovereign_pubkey: str
    signature: str
    
    # Unified features
    coherence_state: Optional[Dict[str, Any]] = None
    coherence_binding_ids: List[str] = field(default_factory=list)
    consciousness_level: float = 0.0
    integrity_hash: str = ""
    
    # Quantum-inspired features (optional)
    quantum_state: Optional[Dict[str, Any]] = None
    entanglement_ids: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize computed fields and validate data."""
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        
        if not self.linkage_manifest:
            self.linkage_manifest = {}
        
        if self.last_access_timestamp == 0:
            self.last_access_timestamp = time.time()
        
        if not self.integrity_hash:
            self.integrity_hash = self._compute_integrity_hash()
        
        # Validate required fields
        if not all([self.node_id, self.author_id, self.kind, self.content]):
            raise ValueError("Missing required fields in UnifiedMemoryNode")
        
        logger.debug(f"Created unified memory node: {self.node_id[:12]}...")

    def signature_payload(self) -> bytes:
        """Return the immutable canonical payload authorized by the node author."""
        return _canonical_json_bytes(
            {
                "node_id": self.node_id,
                "author_id": self.author_id,
                "kind": self.kind.value,
                "timestamp": self.timestamp,
                "content": self.content,
                "semantic_vector": [round(value, 6) for value in self.semantic_vector],
                "meta_patch": self.meta_patch,
                "parents": self.parents,
                "linkage_manifest": {
                    key.value: targets
                    for key, targets in sorted(
                        self.linkage_manifest.items(), key=lambda item: item[0].value
                    )
                },
                "belief_state_hash": self.belief_state_hash,
                "sovereign_pubkey": self.sovereign_pubkey,
            }
        )
    
    def _compute_integrity_hash(self) -> str:
        """Compute a digest over the signed payload and mutable node references."""
        data = {
            "signature_payload_sha512": hashlib.sha512(
                self.signature_payload()
            ).hexdigest(),
            "signature": self.signature,
            "quantum_state": self.quantum_state,
            "entanglement_ids": self.entanglement_ids,
        }
        return hashlib.sha512(_canonical_json_bytes(data)).hexdigest()
    
    def calculate_relevance(self, policy: Optional[Dict[str, Any]] = None) -> float:
        """Calculate unified relevance score with belief decay support."""
        try:
            policy = policy or {}
            
            # MTL semantic relevance
            semantic_factor = np.mean(np.abs(self.semantic_vector)) if self.semantic_vector else 0.5
            
            # NMCA relevance calculation with time decay
            current_time = time.time()
            age_factor = max(0.1, min(1.0, 1.0 / (1.0 + 0.01 * (current_time - self.last_access_timestamp) / 3600)))
            
            # Apply belief decay if configured
            belief_decay_factor = 1.0
            if hasattr(self, 'belief_half_life_days') and self.belief_half_life_days > 0:
                decay_timestamp = getattr(self, 'belief_decay_timestamp', current_time)
                days_elapsed = (current_time - decay_timestamp) / (24 * 3600)
                
                # Exponential decay: value = initial * (0.5)^(days_elapsed / half_life)
                if days_elapsed > 0:
                    belief_decay_factor = pow(0.5, days_elapsed / self.belief_half_life_days)
                    logger.debug(f"Applied belief decay to {self.node_id[:12]}: {belief_decay_factor:.4f} "
                               f"(days: {days_elapsed:.2f}, half-life: {self.belief_half_life_days})")
            elif policy.get('belief_half_life_days', 0) > 0:
                # Use policy default if node doesn't have individual setting
                days_elapsed = (current_time - self.last_access_timestamp) / (24 * 3600)
                if days_elapsed > 0:
                    half_life = policy['belief_half_life_days']
                    belief_decay_factor = pow(0.5, days_elapsed / half_life)
                    logger.debug(f"Applied policy belief decay to {self.node_id[:12]}: {belief_decay_factor:.4f} "
                               f"(days: {days_elapsed:.2f}, half-life: {half_life})")
            
            nmca_relevance = (
                ALPHA * self.frequency_usage +
                BETA * self.contextual_utility +
                GAMMA * self.cross_domain_connections -
                DELTA * self.energy_cost
            ) * age_factor * belief_decay_factor
            
            # SCL epistemic relevance based on linkage depth
            linkage_depth = sum(len(links) for links in self.linkage_manifest.values())
            epistemic_factor = min(1.0, linkage_depth / 10.0)
            
            # Consciousness weighting
            consciousness_weight = max(0.1, self.consciousness_level)
            
            # Combined relevance
            unified_relevance = (
                0.3 * semantic_factor +
                0.4 * nmca_relevance +
                0.2 * epistemic_factor +
                0.1 * consciousness_weight
            )
            
            logger.debug(f"Calculated unified relevance for {self.node_id[:12]}: {unified_relevance:.4f} "
                        f"(decay_factor: {belief_decay_factor:.4f})")
            return max(0.0, min(1.0, unified_relevance))
            
        except Exception as e:
            logger.error(f"Error calculating relevance for node {self.node_id[:12]}: {e}")
            return 0.5  # Default relevance
    
    def record_access(self):
        """Record access to this node, updating usage statistics."""
        try:
            self.last_access_timestamp = time.time()
            self.access_count += 1
            self.frequency_usage = min(1.0, self.frequency_usage + 0.01)
            logger.debug(f"Recorded access to node {self.node_id[:12]}, count: {self.access_count}")
        except Exception as e:
            logger.error(f"Error recording access for node {self.node_id[:12]}: {e}")
    
    def add_link(self, link_type: LinkageTypeEnum, target_id: str):
        """Add a new link to another node."""
        try:
            if link_type not in self.linkage_manifest:
                self.linkage_manifest[link_type] = []
            
            if target_id not in self.linkage_manifest[link_type]:
                self.linkage_manifest[link_type].append(target_id)
                self.cross_domain_connections += 1
                logger.debug(f"Added {link_type.value} link from {self.node_id[:12]} to {target_id[:12]}")
                
        except Exception as e:
            logger.error(f"Error adding link from {self.node_id[:12]} to {target_id[:12]}: {e}")
            raise MemoryIntegrityError(f"Failed to add link: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary for serialization."""
        try:
            return {
                "node_id": self.node_id,
                "author_id": self.author_id,
                "kind": self.kind.value,
                "timestamp": self.timestamp,
                "content": self.content,
                "semantic_vector": self.semantic_vector,
                "meta_patch": self.meta_patch,
                "parents": self.parents,
                "frequency_usage": self.frequency_usage,
                "contextual_utility": self.contextual_utility,
                "cross_domain_connections": self.cross_domain_connections,
                "energy_cost": self.energy_cost,
                "last_access_timestamp": self.last_access_timestamp,
                "access_count": self.access_count,
                "linkage_manifest": {k.value: v for k, v in self.linkage_manifest.items()},
                "belief_state_hash": self.belief_state_hash,
                "sovereign_pubkey": self.sovereign_pubkey,
                "signature": self.signature,
                "coherence_state": self.coherence_state,
                "coherence_binding_ids": self.coherence_binding_ids,
                "consciousness_level": self.consciousness_level,
                "integrity_hash": self.integrity_hash
            }
        except Exception as e:
            logger.error(f"Error converting node {self.node_id[:12]} to dict: {e}")
            raise MemoryIntegrityError(f"Failed to serialize node: {e}")

@dataclass
class SovereignIdentity:
    """
    Unified sovereign identity combining cryptographic identity with agent characteristics.
    Integrates MTL's Agent, NMCA's identity features, and SCL's SovereignID.
    """
    agent_name: str
    agent_id: str
    public_key: str
    creation_timestamp: float
    trust_level: float = 1.0
    authentication_method: str = "ed25519"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Private fields (not serialized)
    _private_key: str = field(default="", repr=False)
    _secret: str = field(default="", repr=False)
    
    def __post_init__(self):
        """Initialize and validate an Ed25519 identity, failing closed."""
        if not CRYPTO_AVAILABLE:
            detail = f": {CRYPTO_IMPORT_ERROR}" if CRYPTO_IMPORT_ERROR else ""
            raise SovereignIdentityError(
                f"Ed25519 support is required for sovereign identities{detail}"
            )
        if not self.agent_name or not self.agent_name.strip():
            raise SovereignIdentityError("Sovereign agent_name must be non-empty")

        self.agent_name = self.agent_name.strip()
        self.authentication_method = "ed25519"
        self._init_ed25519_keys()

        if not self.agent_id:
            identity_material = (
                f"ed25519::{self.agent_name}::{self.public_key}"
            ).encode("utf-8")
            self.agent_id = hashlib.sha256(identity_material).hexdigest()

        if len(self.agent_id) != 64 or any(
            character not in "0123456789abcdef" for character in self.agent_id.lower()
        ):
            raise SovereignIdentityError("Sovereign agent_id must be 32-byte hex")
        
        if not hasattr(self, 'creation_timestamp') or self.creation_timestamp == 0:
            self.creation_timestamp = time.time()

        self.agent_id = self.agent_id.lower()
        self.public_key = self.public_key.lower()
    
    def _init_ed25519_keys(self):
        """Initialize a valid Ed25519 keypair and reject mismatched key material."""
        try:
            if self._private_key:
                private_bytes = bytes.fromhex(self._private_key)
                private_key = Ed25519PrivateKey.from_private_bytes(private_bytes)
            else:
                if self.public_key:
                    raise SovereignIdentityError(
                        "A live sovereign identity requires its private key when a public key is supplied"
                    )
                private_key = Ed25519PrivateKey.generate()
                self._private_key = private_key.private_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PrivateFormat.Raw,
                    encryption_algorithm=serialization.NoEncryption(),
                ).hex()

            derived_public_key = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            ).hex()
            if self.public_key and not secrets.compare_digest(
                self.public_key.lower(), derived_public_key
            ):
                raise SovereignIdentityError(
                    "Supplied Ed25519 public key does not match the private key"
                )
            self.public_key = derived_public_key
        except (ValueError, TypeError) as exc:
            raise SovereignIdentityError(f"Invalid Ed25519 private key: {exc}") from exc
    
    def sign(self, message: Union[str, bytes]) -> str:
        """Sign a message with Ed25519 and never fall back to a forgeable digest."""
        try:
            if isinstance(message, str):
                message = message.encode("utf-8")
            if not isinstance(message, bytes):
                raise SovereignIdentityError("Signed message must be str or bytes")
            if not CRYPTO_AVAILABLE:
                raise SovereignIdentityError("Ed25519 support is unavailable")

            private_key = Ed25519PrivateKey.from_private_bytes(
                bytes.fromhex(self._private_key)
            )
            signature = private_key.sign(message).hex()
            logger.debug(f"Ed25519 signed message for {self.agent_name}")
            return signature
        except (ValueError, TypeError, SovereignIdentityError) as exc:
            logger.error(f"Error signing message for {self.agent_name}: {exc}")
            if isinstance(exc, SovereignIdentityError):
                raise
            raise SovereignIdentityError(f"Failed to sign message: {exc}") from exc
    
    def attest_belief(self, node_id: str, belief: float, rationale: str = "") -> Dict[str, Any]:
        """
        Create a belief attestation for a memory node.
        Combines MTL's attestation with SCL's coherence checking.
        """
        try:
            belief = max(0.0, min(1.0, float(belief)))
            rationale_hash = hashlib.sha256(rationale.encode()).hexdigest() if rationale else ""
            
            attestation_data = {
                "node_id": node_id,
                "agent_id": self.agent_id,
                "belief": belief,
                "rationale_hash": rationale_hash,
                "timestamp": time.time()
            }
            
            payload = _canonical_json_bytes(attestation_data)
            signature = self.sign(payload)
            
            attestation = {
                "attestation_id": hashlib.sha256(payload).hexdigest(),
                "node_id": node_id,
                "agent_id": self.agent_id,
                "belief": belief,
                "rationale_hash": rationale_hash,
                "signature": signature,
                "timestamp": attestation_data["timestamp"]
            }
            
            logger.info(f"Created belief attestation for node {node_id[:12]} by {self.agent_name}")
            return attestation
            
        except Exception as e:
            logger.error(f"Error creating belief attestation: {e}")
            raise SovereignIdentityError(f"Failed to create attestation: {e}")
    
    @staticmethod
    def verify_signature(public_key: str, message: Union[str, bytes], signature: str) -> bool:
        """Verify an exact Ed25519 signature and reject every legacy placeholder."""
        try:
            if isinstance(message, str):
                message = message.encode("utf-8")
            if not CRYPTO_AVAILABLE or not isinstance(message, bytes):
                return False
            if len(public_key) != 64 or len(signature) != 128:
                return False

            public_key_obj = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key))
            public_key_obj.verify(bytes.fromhex(signature), message)
            logger.debug("Ed25519 signature verified successfully")
            return True
        except (ValueError, TypeError, InvalidSignature) as exc:
            logger.debug(f"Ed25519 verification failed: {exc}")
            return False

@dataclass
class CircuitBreaker:
    """
    Enterprise-grade circuit breaker for fault tolerance.
    Prevents cascading failures in the unified memory system.
    """
    name: str
    max_failures: int = 5
    reset_timeout: int = 60
    half_open_max_calls: int = 3
    
    _failure_count: int = field(default=0, init=False)
    _last_failure_time: float = field(default=0.0, init=False)
    _state: CircuitBreakerState = field(default=CircuitBreakerState.CLOSED, init=False)
    _half_open_successes: int = field(default=0, init=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False)
    
    def __post_init__(self):
        """Initialize circuit breaker logging."""
        logger.info(f"Initialized circuit breaker '{self.name}' - max_failures: {self.max_failures}, timeout: {self.reset_timeout}s")
    
    @property
    def state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        with self._lock:
            self._check_timeout()
            return self._state
    
    def _check_timeout(self):
        """Check if we should transition from OPEN to HALF_OPEN."""
        if self._state == CircuitBreakerState.OPEN:
            if time.time() - self._last_failure_time >= self.reset_timeout:
                self._state = CircuitBreakerState.HALF_OPEN
                self._half_open_successes = 0
                logger.info(f"Circuit breaker '{self.name}' transitioned to HALF_OPEN")
    
    def record_success(self):
        """Record successful operation."""
        with self._lock:
            if self._state == CircuitBreakerState.HALF_OPEN:
                self._half_open_successes += 1
                if self._half_open_successes >= self.half_open_max_calls:
                    self._state = CircuitBreakerState.CLOSED
                    self._failure_count = 0
                    logger.info(f"Circuit breaker '{self.name}' transitioned to CLOSED")
            elif self._state == CircuitBreakerState.CLOSED and self._failure_count > 0:
                self._failure_count = max(0, self._failure_count - 1)
    
    def record_failure(self):
        """Record failed operation."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._state == CircuitBreakerState.HALF_OPEN:
                self._state = CircuitBreakerState.OPEN
                logger.warning(f"Circuit breaker '{self.name}' transitioned to OPEN (failure during HALF_OPEN)")
            elif self._failure_count >= self.max_failures:
                self._state = CircuitBreakerState.OPEN
                logger.warning(f"Circuit breaker '{self.name}' OPENED due to {self._failure_count} failures")
    
    def reset(self):
        """Manually reset circuit breaker."""
        with self._lock:
            self._failure_count = 0
            self._state = CircuitBreakerState.CLOSED
            self._half_open_successes = 0
            logger.info(f"Circuit breaker '{self.name}' manually reset")
    
    @contextmanager
    def protected_call(self):
        """Context manager for protected operations."""
        with self._lock:
            if self._state == CircuitBreakerState.OPEN:
                raise CircuitBreakerError(f"Circuit breaker '{self.name}' is OPEN")
            
            if self._state == CircuitBreakerState.HALF_OPEN and self._half_open_successes >= self.half_open_max_calls:
                raise CircuitBreakerError(f"Circuit breaker '{self.name}' HALF_OPEN call limit exceeded")
        
        try:
            yield
            self.record_success()
        except Exception as e:
            self.record_failure()
            logger.error(f"Operation failed in circuit breaker '{self.name}': {e}")
            raise

class UnifiedMemorySystem:
    """
    The unified sovereign memory system combining all three architectures:
    - MTL's DAG-based memory with belief anchoring and auto-repair
    - NMCA's quantum-inspired techniques with thread safety
    - SCL's epistemic weaving with multi-dimensional linkage
    
    This system provides enterprise-grade memory management with:
    - Thread-safe operations with circuit breakers
    - Quantum-inspired state management
    - Belief anchoring and auto-repair
    - Epistemic weaving and causal tracking
    - Comprehensive audit trails and integrity checking
    """
    
    def __init__(self, 
                 db_path: Optional[str] = None,
                 config: Optional[Dict[str, Any]] = None,
                 enable_quantum_features: bool = True,
                 max_qubits: int = DEFAULT_MAX_QUBITS):
        """
        Initialize the unified memory system.
        
        Args:
            db_path: Path to the SQLite database
            config: Configuration dictionary
            enable_quantum_features: Whether to enable quantum-inspired features
            max_qubits: Maximum number of qubits for quantum operations
        """
        try:
            if not CRYPTO_AVAILABLE:
                detail = f": {CRYPTO_IMPORT_ERROR}" if CRYPTO_IMPORT_ERROR else ""
                raise SovereignIdentityError(
                    f"USMS requires Ed25519 cryptography and cannot start{detail}"
                )

            # Initialize basic attributes
            self.config = config or {}
            runtime_root = self.config.get("runtime_root", self.config.get("runtime_dir"))
            self.paths = resolve_memory_paths(runtime_root=runtime_root, db_path=db_path)
            ensure_memory_paths(self.paths)
            if self.config.get("console_logging", False):
                configure_usms_console_logging()
            configure_usms_file_logging(self.paths.log_dir)
            self.runtime_root = self.paths.runtime_root
            self.db_path = str(self.paths.db_path)
            self.busy_timeout_ms = int(
                self.config.get("sqlite_busy_timeout_ms", DEFAULT_BUSY_TIMEOUT_MS)
            )
            if self.busy_timeout_ms < 1:
                raise ValueError("sqlite_busy_timeout_ms must be positive")
            self.enable_quantum_features = enable_quantum_features
            self.internal_backups_enabled = bool(
                self.config.get("internal_backups_enabled", False)
            )
            if self.internal_backups_enabled:
                raise MemoryIntegrityError(
                    "Legacy USMS database-only backups are disabled because they "
                    "omit canonical sidecars; use MemoryArchiveService.create_backup()"
                )
            self.max_qubits = max_qubits
            self._start_time = time.time()
            
            # Thread safety
            self.main_lock = threading.RLock()
            self.db_lock = threading.RLock()
            self.quantum_lock = threading.RLock()
            self.repair_lock = threading.RLock()
            
            # System state
            self.policy = {**DEFAULT_POLICY, **self.config.get('policy', {})}
            self._validate_repair_policy()
            self.active_contexts = {}
            self.entanglements = {}
            self.attestations = {}
            self.anchored_nodes = set()
            
            # Circuit breakers for different operations
            self.circuit_breakers = {
                'database': CircuitBreaker('database_operations', max_failures=3, reset_timeout=30),
                'quantum': CircuitBreaker('quantum_operations', max_failures=5, reset_timeout=60),
                'repair': CircuitBreaker('auto_repair', max_failures=10, reset_timeout=120),
                'weaving': CircuitBreaker('epistemic_weaving', max_failures=7, reset_timeout=90)
            }
            
            # Performance monitoring
            self.operation_counts = defaultdict(int)
            self.last_integrity_check = time.time()
            self.last_backup = time.time()
            
            # Background task management
            self._shutdown_event = threading.Event()
            self._background_threads = []
            
            # Initialize binary storage and multi-process coordination
            self.binary_storage = BinaryStorageManager(self.paths.binary_dir)
            self.process_coordinator = MultiProcessCoordinator(self.paths.lock_dir)
            self._process_marker = self.process_coordinator.create_process_marker()
            
            # Initialize database with process coordination
            with self.circuit_breakers['database'].protected_call():
                with self.process_coordinator.database_lock("initialization"):
                    self._init_database()
                    self._install_genesis_if_needed()
                    self._hydrate_anchors()
            
            # Start background tasks
            self._start_background_tasks()
            
            logger.info(f"Unified Sovereign Memory System initialized - DB: {self.db_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Unified Memory System: {e}")
            if hasattr(self, "_process_marker") and hasattr(
                self, "process_coordinator"
            ):
                try:
                    self.process_coordinator.cleanup_process_marker(
                        self._process_marker
                    )
                except (OSError, ProcessCoordinationError):
                    logger.exception("Failed to clean process marker after startup error")
            raise UnifiedMemoryError(f"System initialization failed: {e}")

    @contextmanager
    def _database_connection(
        self,
        database_path: Optional[Union[str, Path]] = None,
        *,
        initialize_journal: bool = False,
    ) -> Iterator[sqlite3.Connection]:
        """Open one configured SQLite connection and always close it.

        WAL is a database-level setting, not a per-operation connection
        setting.  Reissuing ``PRAGMA journal_mode=WAL`` from every process and
        every short-lived connection can race SQLite's journal transition with
        active readers/writers.  Only the process-coordinated schema
        initialization path may establish WAL; normal connections inherit the
        already-verified database mode.
        """
        target_path = str(database_path or self.db_path)
        connection = sqlite3.connect(
            target_path,
            timeout=self.busy_timeout_ms / 1000.0,
        )
        try:
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute(f"PRAGMA busy_timeout={self.busy_timeout_ms}")
            connection.execute("PRAGMA temp_store=MEMORY")
            if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
                raise MemoryIntegrityError("SQLite foreign-key enforcement is unavailable")
            configured_timeout = connection.execute(
                "PRAGMA busy_timeout"
            ).fetchone()[0]
            if configured_timeout != self.busy_timeout_ms:
                raise MemoryIntegrityError("SQLite busy timeout was not applied")
            if Path(target_path).resolve() == Path(self.db_path).resolve():
                if initialize_journal:
                    journal_mode = connection.execute(
                        "PRAGMA journal_mode"
                    ).fetchone()[0]
                    if str(journal_mode).lower() != "wal":
                        journal_mode = connection.execute(
                            "PRAGMA journal_mode=WAL"
                        ).fetchone()[0]
                    if str(journal_mode).lower() != "wal":
                        raise MemoryIntegrityError("SQLite WAL mode is required")
                connection.execute("PRAGMA synchronous=FULL")
                connection.execute("PRAGMA cache_size=-65536")
            yield connection
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()
    
    def _init_database(self):
        """Initialize the unified database schema."""
        try:
            with self._database_connection(initialize_journal=True) as conn:
                # Check and handle schema versioning
                self._handle_schema_versioning(conn)
                
                # Main nodes table (combines all three systems with optimized storage)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS unified_nodes (
                        node_id TEXT PRIMARY KEY,
                        author_id TEXT NOT NULL,
                        kind TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        content TEXT NOT NULL,
                        semantic_vector_ref TEXT NOT NULL,
                        meta_patch_ref TEXT NOT NULL,
                        parents TEXT NOT NULL,
                        frequency_usage REAL DEFAULT 0.0,
                        contextual_utility REAL DEFAULT 0.0,
                        cross_domain_connections INTEGER DEFAULT 0,
                        energy_cost REAL DEFAULT 0.0,
                        last_access_timestamp REAL NOT NULL,
                        access_count INTEGER DEFAULT 0,
                        linkage_manifest_ref TEXT NOT NULL,
                        belief_state_hash TEXT NOT NULL,
                        sovereign_pubkey TEXT NOT NULL,
                        signature TEXT NOT NULL,
                        quantum_state TEXT,
                        entanglement_ids TEXT,
                        consciousness_level REAL DEFAULT 0.0,
                        integrity_hash TEXT NOT NULL,
                        belief_decay_timestamp REAL DEFAULT 0.0,
                        belief_half_life_days REAL DEFAULT 0.0,
                        FOREIGN KEY (author_id) REFERENCES sovereign_identities(agent_id)
                            ON UPDATE RESTRICT ON DELETE RESTRICT
                    )
                """)
                
                # Linkage/edges table for graph queries
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS node_links (
                        source_id TEXT NOT NULL,
                        target_id TEXT NOT NULL,
                        link_type TEXT NOT NULL,
                        strength REAL DEFAULT 0.5,
                        creation_timestamp REAL NOT NULL,
                        last_accessed REAL NOT NULL,
                        metadata TEXT,
                        PRIMARY KEY (source_id, target_id, link_type),
                        FOREIGN KEY (source_id) REFERENCES unified_nodes(node_id),
                        FOREIGN KEY (target_id) REFERENCES unified_nodes(node_id)
                    )
                """)
                
                # Attestations table (MTL belief system)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS attestations (
                        attestation_id TEXT PRIMARY KEY,
                        node_id TEXT NOT NULL,
                        agent_id TEXT NOT NULL,
                        belief REAL NOT NULL,
                        rationale_hash TEXT,
                        signature TEXT NOT NULL,
                        timestamp REAL NOT NULL,
                        FOREIGN KEY (node_id) REFERENCES unified_nodes(node_id)
                            ON UPDATE RESTRICT ON DELETE CASCADE,
                        FOREIGN KEY (agent_id) REFERENCES sovereign_identities(agent_id)
                            ON UPDATE RESTRICT ON DELETE RESTRICT
                    )
                """)
                
                # Anchors table (MTL anchoring system)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS anchors (
                        node_id TEXT PRIMARY KEY,
                        timestamp REAL NOT NULL,
                        score REAL NOT NULL,
                        anchor_type TEXT DEFAULT 'belief',
                        metadata TEXT,
                        FOREIGN KEY (node_id) REFERENCES unified_nodes(node_id)
                    )
                """)
                
                # Quantum entanglements table (NMCA quantum features)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS quantum_entanglements (
                        entanglement_id TEXT PRIMARY KEY,
                        branch_ids TEXT NOT NULL,
                        entanglement_strength REAL NOT NULL,
                        creation_timestamp REAL NOT NULL,
                        metadata TEXT,
                        state_vector TEXT
                    )
                """)
                
                # Sovereign identities table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS sovereign_identities (
                        agent_id TEXT PRIMARY KEY,
                        agent_name TEXT NOT NULL UNIQUE,
                        public_key TEXT NOT NULL UNIQUE,
                        creation_timestamp REAL NOT NULL,
                        trust_level REAL DEFAULT 1.0,
                        authentication_method TEXT DEFAULT 'cryptographic',
                        metadata TEXT
                    )
                """)
                
                # System events and audit log
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS system_events (
                        event_id TEXT PRIMARY KEY,
                        event_type TEXT NOT NULL,
                        timestamp REAL NOT NULL,
                        agent_id TEXT,
                        details TEXT,
                        success BOOLEAN DEFAULT TRUE
                    )
                """)
                
                # Create indexes for performance
                indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_nodes_author ON unified_nodes(author_id)",
                    "CREATE INDEX IF NOT EXISTS idx_nodes_kind ON unified_nodes(kind)",
                    "CREATE INDEX IF NOT EXISTS idx_nodes_timestamp ON unified_nodes(timestamp)",
                    "CREATE INDEX IF NOT EXISTS idx_links_source ON node_links(source_id)",
                    "CREATE INDEX IF NOT EXISTS idx_links_target ON node_links(target_id)",
                    "CREATE INDEX IF NOT EXISTS idx_links_type ON node_links(link_type)",
                    "CREATE INDEX IF NOT EXISTS idx_attestations_node ON attestations(node_id)",
                    "CREATE INDEX IF NOT EXISTS idx_attestations_agent ON attestations(agent_id)",
                    "CREATE INDEX IF NOT EXISTS idx_events_type ON system_events(event_type)",
                    "CREATE INDEX IF NOT EXISTS idx_events_timestamp ON system_events(timestamp)"
                ]
                
                for index_sql in indexes:
                    conn.execute(index_sql)
                
                conn.commit()
                logger.debug("Database schema initialized successfully")
                
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise MemoryIntegrityError(f"Failed to initialize database: {e}")
    
    def _install_genesis_if_needed(self):
        """Install genesis node if database is empty."""
        try:
            with self._database_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(1) FROM unified_nodes")
                count = cursor.fetchone()[0]
                
                if count == 0:
                    logger.info("Installing genesis node")
                    
                    # Create system sovereign
                    system_sovereign = SovereignIdentity(
                        agent_name="system_genesis",
                        agent_id="",
                        public_key="",
                        creation_timestamp=time.time()
                    )
                    
                    # Register the sovereign
                    self.register_sovereign(system_sovereign)
                    
                    # Create genesis node
                    genesis_content = {
                        "summary": "Genesis node for Unified Sovereign Memory System",
                        "description": "Initial policy and system initialization",
                        "version": "1.0.0",
                        "capabilities": [
                            "belief_anchoring",
                            "quantum_processing", 
                            "epistemic_weaving",
                            "auto_repair",
                            "thread_safety"
                        ]
                    }
                    
                    genesis_node = UnifiedMemoryNode(
                        node_id=str(uuid.uuid4()),
                        author_id=system_sovereign.agent_id,
                        kind=NodeKindEnum.META,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        content=genesis_content,
                        semantic_vector=self._text_to_semantic_vector("genesis system initialization", dims=12),
                        meta_patch=self.policy,
                        parents=[],
                        frequency_usage=1.0,
                        contextual_utility=1.0,
                        cross_domain_connections=0,
                        energy_cost=0.0,
                        last_access_timestamp=time.time(),
                        access_count=1,
                        linkage_manifest={},
                        belief_state_hash=hashlib.sha256("genesis_verified".encode()).hexdigest(),
                        sovereign_pubkey=system_sovereign.public_key,
                        signature="",
                        consciousness_level=1.0
                    )
                    genesis_node.signature = system_sovereign.sign(
                        genesis_node.signature_payload()
                    )
                    genesis_node.integrity_hash = genesis_node._compute_integrity_hash()
                    
                    # Store genesis node
                    self._store_node(genesis_node)
                    self._anchor_node(genesis_node.node_id, 1.0, "genesis")
                    
                    logger.info(f"Genesis node installed: {genesis_node.node_id}")
                    
        except Exception as e:
            logger.error(f"Failed to install genesis: {e}")
            raise UnifiedMemoryError(f"Genesis installation failed: {e}")
    
    def _hydrate_anchors(self):
        """Load anchored nodes from database into memory on startup."""
        try:
            with self._database_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT node_id FROM anchors")
                rows = cursor.fetchall()
                
                for (node_id,) in rows:
                    self.anchored_nodes.add(node_id)
                
                logger.info(f"Hydrated {len(self.anchored_nodes)} anchored nodes from database")
                
        except Exception as e:
            logger.error(f"Failed to hydrate anchors: {e}")
            # Continue startup even if anchor hydration fails

    def _require_registered_identity(
        self,
        identity: Optional[SovereignIdentity],
    ) -> tuple[str, str, str]:
        """Authenticate a live identity against its immutable registry row."""
        if identity is None:
            raise MemoryAccessError("An authenticated sovereign identity is required")
        if not isinstance(identity, SovereignIdentity):
            raise MemoryAccessError("Requester is not a SovereignIdentity")

        with self._database_connection() as connection:
            row = connection.execute(
                """
                SELECT agent_id, agent_name, public_key
                FROM sovereign_identities
                WHERE agent_id = ?
                """,
                (identity.agent_id,),
            ).fetchone()

        if row is None:
            raise MemoryAccessError(
                f"Sovereign identity is not registered: {identity.agent_id[:12]}"
            )

        registered_id, registered_name, registered_public_key = row
        identity_matches = (
            secrets.compare_digest(registered_id, identity.agent_id)
            and secrets.compare_digest(registered_name, identity.agent_name)
            and secrets.compare_digest(registered_public_key, identity.public_key)
        )
        if not identity_matches:
            raise MemoryAccessError("Requester identity does not match its registry row")

        challenge = b"usms-request-auth-v1\x00" + secrets.token_bytes(32)
        try:
            challenge_signature = identity.sign(challenge)
        except SovereignIdentityError as exc:
            raise MemoryAccessError(
                "Requester could not prove possession of its private key"
            ) from exc
        if not SovereignIdentity.verify_signature(
            registered_public_key, challenge, challenge_signature
        ):
            raise MemoryAccessError("Requester failed Ed25519 proof of possession")
        return registered_id, registered_name, registered_public_key

    @staticmethod
    def _node_access_allowed(
        node: UnifiedMemoryNode,
        requester_id: str,
    ) -> bool:
        """Evaluate the node's signed access-control metadata."""
        raw_access_control = node.meta_patch.get(ACCESS_CONTROL_KEY, {})
        if not isinstance(raw_access_control, dict):
            return False

        scope = raw_access_control.get("scope", ACCESS_SCOPE_REGISTERED)
        allowed_agent_ids = raw_access_control.get("allowed_agent_ids", [])
        if not isinstance(allowed_agent_ids, list) or any(
            not isinstance(agent_id, str) for agent_id in allowed_agent_ids
        ):
            return False

        if requester_id == node.author_id:
            return True
        if scope == ACCESS_SCOPE_REGISTERED:
            return True
        if scope == ACCESS_SCOPE_PRIVATE:
            return False
        if scope == ACCESS_SCOPE_EXPLICIT:
            return requester_id in allowed_agent_ids
        return False

    def _require_node_access(
        self,
        node: UnifiedMemoryNode,
        requester: Optional[SovereignIdentity],
    ) -> None:
        """Authenticate a requester and enforce one node's signed scope."""
        requester_id, _, _ = self._require_registered_identity(requester)
        if not self._node_access_allowed(node, requester_id):
            raise MemoryAccessError(
                f"Sovereign {requester_id[:12]} is not authorized for node {node.node_id[:12]}"
            )

    def _node_exists(self, node_id: str) -> bool:
        """Return whether a canonical node id exists without disclosing its content."""
        with self._database_connection() as connection:
            row = connection.execute(
                "SELECT 1 FROM unified_nodes WHERE node_id = ?",
                (node_id,),
            ).fetchone()
        return row is not None

    def _load_node(
        self,
        node_id: str,
        *,
        record_access: bool = False,
    ) -> Optional[UnifiedMemoryNode]:
        """Load and cryptographically validate a node for trusted internal use."""
        with self._database_connection() as connection:
            row = connection.execute(
                "SELECT * FROM unified_nodes WHERE node_id = ?",
                (node_id,),
            ).fetchone()
            if row is None:
                return None

            node = self._row_to_node(row)
            if record_access:
                node.record_access()
                connection.execute(
                    """
                    UPDATE unified_nodes
                    SET last_access_timestamp = ?, access_count = ?, frequency_usage = ?
                    WHERE node_id = ?
                    """,
                    (
                        node.last_access_timestamp,
                        node.access_count,
                        node.frequency_usage,
                        node.node_id,
                    ),
                )
                connection.commit()
            return node
    
    def _handle_schema_versioning(self, conn):
        """Handle database schema versioning and migrations."""
        try:
            # Create schema_version table if it doesn't exist
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_timestamp REAL NOT NULL,
                    description TEXT,
                    checksum TEXT
                )
            """)
            
            # Get current schema version from database
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(version) FROM schema_version")
            result = cursor.fetchone()
            current_version = result[0] if result and result[0] is not None else 0
            
            logger.debug(f"Current schema version: {current_version}, Target version: {CURRENT_SCHEMA_VERSION}")
            
            # Check compatibility
            if current_version > CURRENT_SCHEMA_VERSION:
                raise MemoryIntegrityError(
                    f"Database schema version {current_version} is newer than supported version {CURRENT_SCHEMA_VERSION}"
                )
            
            if current_version < MIN_COMPATIBLE_VERSION and current_version > 0:
                raise MemoryIntegrityError(
                    f"Database schema version {current_version} is too old (minimum supported: {MIN_COMPATIBLE_VERSION})"
                )
            
            # Apply migrations if needed
            if current_version < CURRENT_SCHEMA_VERSION:
                self._apply_schema_migrations(conn, current_version, CURRENT_SCHEMA_VERSION)
            
        except Exception as e:
            logger.error(f"Schema versioning failed: {e}")
            raise MemoryIntegrityError(f"Schema versioning error: {e}")
    
    def _apply_schema_migrations(self, conn, from_version: int, to_version: int):
        """Apply database schema migrations."""
        try:
            logger.info(f"Applying schema migrations from version {from_version} to {to_version}")
            
            migrations = {
                0: self._migrate_to_v1,
                1: self._migrate_to_v2,
                2: self._migrate_to_v3,
            }
            
            for version in range(from_version, to_version):
                target_version = version + 1
                migration_func = migrations.get(version)
                
                if migration_func:
                    logger.info(f"Applying migration to version {target_version}")
                    migration_func(conn)
                    
                    # Record the migration
                    conn.execute("""
                        INSERT OR REPLACE INTO schema_version 
                        (version, applied_timestamp, description, checksum)
                        VALUES (?, ?, ?, ?)
                    """, (
                        target_version,
                        time.time(),
                        f"Migration to schema version {target_version}",
                        hashlib.sha256(f"v{target_version}_migration".encode()).hexdigest()
                    ))
                    
                    logger.info(f"Successfully migrated to schema version {target_version}")
                else:
                    logger.warning(f"No migration function found for version {version} -> {target_version}")
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Schema migration failed: {e}")
            conn.rollback()
            raise MemoryIntegrityError(f"Migration failed: {e}")
    
    def _migrate_to_v1(self, conn):
        """Migration to schema version 1 (baseline)."""
        # This is the baseline schema - no changes needed
        # All tables are created in _init_database
        pass
    
    def _migrate_to_v2(self, conn):
        """Migration to schema version 2 - add belief decay support."""
        try:
            # Check if unified_nodes table exists first
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='unified_nodes'")
            table_exists = cursor.fetchone() is not None
            
            if not table_exists:
                logger.debug("unified_nodes table doesn't exist yet - skipping migration")
                return
                
            # Add belief_decay column to unified_nodes if it doesn't exist
            cursor.execute("PRAGMA table_info(unified_nodes)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'belief_decay_timestamp' not in columns:
                conn.execute("""
                    ALTER TABLE unified_nodes 
                    ADD COLUMN belief_decay_timestamp REAL DEFAULT 0.0
                """)
                logger.debug("Added belief_decay_timestamp column")
            
            if 'belief_half_life_days' not in columns:
                conn.execute("""
                    ALTER TABLE unified_nodes 
                    ADD COLUMN belief_half_life_days REAL DEFAULT 0.0
                """)
                logger.debug("Added belief_half_life_days column")
            
            # Update existing nodes with initial decay values
            conn.execute("""
                UPDATE unified_nodes 
                SET belief_decay_timestamp = last_access_timestamp,
                    belief_half_life_days = 365.0  -- Default 1 year half-life
                WHERE belief_decay_timestamp = 0.0
            """)
            
        except Exception as e:
            logger.error(f"Migration to v2 failed: {e}")
            raise

    def _migrate_to_v3(self, conn: sqlite3.Connection) -> None:
        """Reject legacy canonical records and rebuild only an empty secure schema."""
        table_exists = conn.execute(
            """
            SELECT 1 FROM sqlite_master
            WHERE type = 'table' AND name = 'unified_nodes'
            """
        ).fetchone()
        if table_exists is None:
            return

        node_count = conn.execute("SELECT COUNT(*) FROM unified_nodes").fetchone()[0]
        if node_count:
            raise MemoryIntegrityError(
                "Schema v3 cannot authenticate legacy node signatures. "
                "Export and re-ingest the v2 archive with registered Ed25519 identities."
            )

        # There is no canonical data to preserve. Rebuild the security-sensitive
        # tables so fresh v3 DDL installs immutable identity and FK constraints.
        for table_name in (
            "node_links",
            "attestations",
            "anchors",
            "quantum_entanglements",
            "unified_nodes",
            "sovereign_identities",
        ):
            conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
    
    def _start_background_tasks(self):
        """Start background maintenance tasks with actual threading."""
        try:
            # Integrity checking thread
            integrity_thread = threading.Thread(
                target=self._integrity_check_loop,
                name="IntegrityChecker",
                daemon=True
            )
            integrity_thread.start()
            self._background_threads.append(integrity_thread)
            
            # DB-only legacy backups omit binary sidecars. Production composition
            # disables them and uses the complete signed BackupManager bundle.
            if self.internal_backups_enabled:
                backup_thread = threading.Thread(
                    target=self._backup_loop,
                    name="BackupManager",
                    daemon=True
                )
                backup_thread.start()
                self._background_threads.append(backup_thread)
            
            # Cleanup and maintenance thread
            cleanup_thread = threading.Thread(
                target=self._cleanup_loop,
                name="CleanupManager",
                daemon=True
            )
            cleanup_thread.start()
            self._background_threads.append(cleanup_thread)
            
            logger.info(f"Started {len(self._background_threads)} background tasks")
            
        except Exception as e:
            logger.warning(f"Some background tasks failed to start: {e}")
    
    def _integrity_check_loop(self):
        """Background thread for periodic integrity checking."""
        logger.info("Integrity check loop started")
        
        while not self._shutdown_event.is_set():
            try:
                # Check if enough time has passed
                if time.time() - self.last_integrity_check >= INTEGRITY_CHECK_INTERVAL:
                    logger.debug("Running periodic integrity sweep")
                    self._integrity_sweep()
                    self.last_integrity_check = time.time()
                
                # Sleep for a short interval to check shutdown
                self._shutdown_event.wait(30)
                
            except Exception as e:
                logger.error(f"Error in integrity check loop: {e}")
                self._shutdown_event.wait(60)  # Wait longer after error
        
        logger.info("Integrity check loop stopped")
    
    def _backup_loop(self):
        """Background thread for periodic backups."""
        logger.info("Backup loop started")
        
        while not self._shutdown_event.is_set():
            try:
                # Check if enough time has passed
                if time.time() - self.last_backup >= BACKUP_INTERVAL:
                    logger.debug("Running periodic backup")
                    
                    with self.circuit_breakers['database'].protected_call():
                        success = self.backup_system()
                        if success:
                            logger.debug("Periodic backup completed successfully")
                        else:
                            logger.warning("Periodic backup failed")
                
                # Sleep for backup interval or until shutdown
                self._shutdown_event.wait(min(BACKUP_INTERVAL, 300))  # Check at least every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in backup loop: {e}")
                self._shutdown_event.wait(300)  # Wait 5 minutes after error
        
        logger.info("Backup loop stopped")
    
    def _cleanup_loop(self):
        """Background thread for maintenance and cleanup tasks."""
        logger.info("Cleanup loop started")
        
        while not self._shutdown_event.is_set():
            try:
                # Clean up old contexts
                current_time = time.time()
                expired_contexts = [
                    ctx_id for ctx_id, ctx_data in self.active_contexts.items()
                    if current_time - ctx_data.get('timestamp', current_time) > CONTEXT_TIMEOUT
                ]
                
                for ctx_id in expired_contexts:
                    self.active_contexts.pop(ctx_id, None)
                
                if expired_contexts:
                    logger.debug(f"Cleaned up {len(expired_contexts)} expired contexts")
                
                # Circuit breaker maintenance
                for name, breaker in self.circuit_breakers.items():
                    if breaker.state.name != 'CLOSED':
                        logger.debug(f"Circuit breaker '{name}' state: {breaker.state.name}")
                
                # Log system health
                if hasattr(self, '_calculate_consciousness_level'):
                    consciousness = self._calculate_consciousness_level()
                    if consciousness < 0.5:
                        logger.warning(f"Low system consciousness level: {consciousness:.3f}")
                
                # Sleep for cleanup interval or until shutdown
                self._shutdown_event.wait(600)  # Run every 10 minutes
                
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                self._shutdown_event.wait(300)  # Wait 5 minutes after error
        
        logger.info("Cleanup loop stopped")
    
    def _validate_link_integrity(self, row: tuple) -> bool:
        """Verify one link against its source manifest or creator signature."""
        try:
            (
                source_id,
                target_id,
                link_type,
                strength,
                creation_timestamp,
                metadata_json,
            ) = row
            metadata = json.loads(metadata_json) if metadata_json else {}
            if not isinstance(metadata, dict):
                return False

            source_node = self._load_node(source_id)
            if source_node is None or not self._node_exists(target_id):
                return False
            try:
                linkage_type = LinkageTypeEnum(link_type)
            except ValueError:
                return False
            if target_id not in source_node.linkage_manifest.get(linkage_type, []):
                return False

            if metadata.get("auto_generated") is True:
                return True

            creator_id = metadata.get("creator")
            creator_public_key = metadata.get("creator_public_key")
            signature = metadata.get("creator_signature")
            stored_payload = metadata.get("signature_payload")
            expected_payload = {
                "source_id": source_id,
                "target_id": target_id,
                "link_type": link_type,
                "strength": float(strength),
                "creation_timestamp": creation_timestamp,
                "creator_id": creator_id,
            }
            if stored_payload != expected_payload:
                return False

            with self._database_connection() as connection:
                identity_row = connection.execute(
                    "SELECT public_key FROM sovereign_identities WHERE agent_id = ?",
                    (creator_id,),
                ).fetchone()
            if identity_row is None or not isinstance(creator_public_key, str):
                return False
            if not secrets.compare_digest(identity_row[0], creator_public_key):
                return False
            if creator_id != source_node.author_id:
                return False
            return SovereignIdentity.verify_signature(
                creator_public_key,
                _canonical_json_bytes(expected_payload),
                signature,
            )
        except (
            BinaryStorageError,
            MemoryIntegrityError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
            sqlite3.Error,
        ):
            return False

    def _integrity_sweep(self) -> List[Dict[str, Any]]:
        """Perform integrity verification on system data."""
        try:
            integrity_issues = []
            nodes_checked = 0
            
            with self._database_connection() as conn:
                cursor = conn.cursor()
                
                # Check a batch of recent nodes to avoid performance impact
                cursor.execute("""
                    SELECT * FROM unified_nodes 
                    ORDER BY last_access_timestamp DESC 
                    LIMIT 100
                """)
                rows = cursor.fetchall()
                
                for row in rows:
                    try:
                        nodes_checked += 1
                        node = self._row_to_node(row)
                        
                        # Verify integrity hash
                        expected_hash = node._compute_integrity_hash()
                        if node.integrity_hash != expected_hash:
                            integrity_issues.append({
                                'type': 'integrity_hash_mismatch',
                                'node_id': node.node_id,
                                'expected': expected_hash,
                                'actual': node.integrity_hash
                            })
                            logger.warning(f"Integrity hash mismatch for node {node.node_id[:12]}")
                        
                        # The row converter already verifies the Ed25519 signature;
                        # retain an explicit shape check for diagnostics.
                        if not node.signature or len(node.signature) != 128:
                            integrity_issues.append({
                                'type': 'invalid_signature_format',
                                'node_id': node.node_id,
                                'signature_length': len(node.signature) if node.signature else 0
                            })
                            logger.warning(f"Invalid signature format for node {node.node_id[:12]}")
                        
                        # Verify required fields
                        required_fields = ['node_id', 'author_id', 'kind', 'content', 'timestamp']
                        for field in required_fields:
                            if not getattr(node, field, None):
                                integrity_issues.append({
                                    'type': 'missing_required_field',
                                    'node_id': node.node_id,
                                    'field': field
                                })
                                logger.warning(f"Missing required field '{field}' for node {node.node_id[:12]}")
                        
                        # Verify semantic vector
                        if not node.semantic_vector or len(node.semantic_vector) == 0:
                            integrity_issues.append({
                                'type': 'invalid_semantic_vector',
                                'node_id': node.node_id
                            })
                            logger.warning(f"Invalid semantic vector for node {node.node_id[:12]}")
                        
                    except Exception as e:
                        integrity_issues.append({
                            'type': 'node_processing_error',
                            'node_id': row[0] if row else 'unknown',
                            'error': str(e)
                        })
                        logger.error(f"Error processing node during integrity sweep: {e}")
                
                # Check for orphaned links
                cursor.execute("""
                    SELECT COUNT(*) FROM node_links l
                    LEFT JOIN unified_nodes n1 ON l.source_id = n1.node_id
                    LEFT JOIN unified_nodes n2 ON l.target_id = n2.node_id
                    WHERE n1.node_id IS NULL OR n2.node_id IS NULL
                """)
                orphaned_links = cursor.fetchone()[0] or 0
                
                if orphaned_links > 0:
                    integrity_issues.append({
                        'type': 'orphaned_links',
                        'count': orphaned_links
                    })
                    logger.warning(f"Found {orphaned_links} orphaned links")

                cursor.execute(
                    """
                    SELECT source_id, target_id, link_type, strength,
                           creation_timestamp, metadata
                    FROM node_links
                    ORDER BY creation_timestamp DESC
                    LIMIT 1000
                    """
                )
                for link_row in cursor.fetchall():
                    if not self._validate_link_integrity(link_row):
                        integrity_issues.append(
                            {
                                "type": "invalid_link_signature",
                                "source_id": link_row[0],
                                "target_id": link_row[1],
                                "link_type": link_row[2],
                            }
                        )

                cursor.execute(
                    """
                    SELECT a.attestation_id, a.node_id, a.agent_id, a.belief,
                           a.rationale_hash, a.signature, a.timestamp,
                           i.public_key
                    FROM attestations AS a
                    LEFT JOIN sovereign_identities AS i
                      ON i.agent_id = a.agent_id
                    ORDER BY a.timestamp DESC
                    LIMIT 1000
                    """
                )
                for attestation_row in cursor.fetchall():
                    (
                        attestation_id,
                        attested_node_id,
                        attesting_agent_id,
                        belief,
                        rationale_hash,
                        attestation_signature,
                        attestation_timestamp,
                        attester_public_key,
                    ) = attestation_row
                    attestation_payload = {
                        "node_id": attested_node_id,
                        "agent_id": attesting_agent_id,
                        "belief": belief,
                        "rationale_hash": rationale_hash,
                        "timestamp": attestation_timestamp,
                    }
                    valid_attestation = (
                        attester_public_key is not None
                        and self._node_exists(attested_node_id)
                        and SovereignIdentity.verify_signature(
                            attester_public_key,
                            _canonical_json_bytes(attestation_payload),
                            attestation_signature,
                        )
                    )
                    if not valid_attestation:
                        integrity_issues.append(
                            {
                                "type": "invalid_attestation_signature",
                                "attestation_id": attestation_id,
                                "node_id": attested_node_id,
                                "agent_id": attesting_agent_id,
                            }
                        )
                
                # Check for duplicate node IDs
                cursor.execute("""
                    SELECT node_id, COUNT(*) as count 
                    FROM unified_nodes 
                    GROUP BY node_id 
                    HAVING count > 1
                """)
                duplicates = cursor.fetchall()
                
                if duplicates:
                    for node_id, count in duplicates:
                        integrity_issues.append({
                            'type': 'duplicate_node_id',
                            'node_id': node_id,
                            'count': count
                        })
                        logger.error(f"Duplicate node ID found: {node_id[:12]} (count: {count})")
            
            # Log results
            if integrity_issues:
                logger.warning(f"Integrity sweep found {len(integrity_issues)} issues in {nodes_checked} nodes")
                
                # Log detailed issues (limit output)
                for issue in integrity_issues[:5]:  # Only log first 5 to avoid spam
                    logger.debug(f"Integrity issue: {issue}")
                
                if len(integrity_issues) > 5:
                    logger.debug(f"... and {len(integrity_issues) - 5} more issues")
                
                # Record integrity event
                self._log_system_event("integrity_sweep_issues", None, {
                    "issues_found": len(integrity_issues),
                    "nodes_checked": nodes_checked,
                    "issue_types": list(set(issue['type'] for issue in integrity_issues))
                })
            else:
                logger.debug(f"Integrity sweep passed: {nodes_checked} nodes verified")

            return integrity_issues

        except (sqlite3.Error, MemoryIntegrityError, BinaryStorageError) as e:
            logger.error(f"Integrity sweep failed: {e}")
            return [{"type": "integrity_sweep_failure", "error": str(e)}]
    
    # Core memory operations
    
    def create_memory_node(self, 
                          author: SovereignIdentity,
                          kind: NodeKindEnum,
                          content: Dict[str, Any],
                          parents: Optional[List[str]] = None,
                          linkage_manifest: Optional[Dict[LinkageTypeEnum, List[str]]] = None,
                          semantic_context: Optional[str] = None,
                          access_scope: str = ACCESS_SCOPE_REGISTERED,
                          allowed_agent_ids: Optional[List[str]] = None) -> UnifiedMemoryNode:
        """
        Create a new unified memory node combining features from all systems.
        
        Args:
            author: Sovereign identity creating the node
            kind: Type of memory node
            content: Node content/payload
            parents: Parent node IDs (MTL-style)
            linkage_manifest: Multi-dimensional linkage (SCL-style)
            semantic_context: Context for semantic vector generation
            access_scope: Registered, private, or explicit visibility
            allowed_agent_ids: Additional registered identities allowed to read
            
        Returns:
            Created UnifiedMemoryNode
        """
        try:
            with self.main_lock:
                # ``policy`` is a legacy mutable mapping.  Validate this before
                # allocating a node id, writing sidecars, or committing SQLite
                # state so a post-construction policy mutation cannot leave a
                # caller with a failed operation that nevertheless persisted.
                self._validate_repair_policy()
                self._require_registered_identity(author)
                if access_scope not in VALID_ACCESS_SCOPES:
                    raise MemoryAccessError(
                        f"Unsupported node access scope: {access_scope}"
                    )

                raw_allowed_ids = allowed_agent_ids or []
                if any(not isinstance(agent_id, str) for agent_id in raw_allowed_ids):
                    raise MemoryAccessError("allowed_agent_ids must contain strings")
                allowed_ids = sorted(set(raw_allowed_ids))
                if allowed_ids:
                    with self._database_connection() as connection:
                        registered_allowed_ids = {
                            row[0]
                            for row in connection.execute(
                                "SELECT agent_id FROM sovereign_identities"
                            ).fetchall()
                        }
                    unknown_allowed_ids = set(allowed_ids) - registered_allowed_ids
                    if unknown_allowed_ids:
                        raise MemoryAccessError(
                            "Node allowlist contains unregistered identities"
                        )

                parent_ids = list(parents or [])
                if any(not isinstance(parent_id, str) for parent_id in parent_ids):
                    raise MemoryIntegrityError("Parent node ids must be strings")
                manifest = linkage_manifest or {}
                referenced_ids = set(parent_ids)
                for link_type, target_ids in manifest.items():
                    if not isinstance(link_type, LinkageTypeEnum):
                        raise MemoryIntegrityError("Linkage keys must be LinkageTypeEnum")
                    if not isinstance(target_ids, list) or any(
                        not isinstance(target_id, str) for target_id in target_ids
                    ):
                        raise MemoryIntegrityError(
                            "Linkage target ids must be lists of strings"
                        )
                    referenced_ids.update(target_ids)
                missing_ids = sorted(
                    node_id for node_id in referenced_ids if not self._node_exists(node_id)
                )
                if missing_ids:
                    raise MemoryIntegrityError(
                        "Cannot create a node with dangling references: "
                        + ", ".join(node_id[:12] for node_id in missing_ids)
                    )

                # Generate semantic vector
                semantic_text = semantic_context or self._extract_semantic_text(content, kind)
                semantic_vector = self._text_to_semantic_vector(semantic_text)
                
                # Calculate consciousness level if quantum features enabled
                consciousness_level = 0.0
                if self.enable_quantum_features:
                    consciousness_level = self._calculate_consciousness_level()
                
                node_id = str(uuid.uuid4())
                node_timestamp = datetime.now(timezone.utc).isoformat()

                # Create the unsigned node, then authorize its complete canonical payload.
                node = UnifiedMemoryNode(
                    node_id=node_id,
                    author_id=author.agent_id,
                    kind=kind,
                    timestamp=node_timestamp,
                    content=content,
                    semantic_vector=semantic_vector,
                    meta_patch={
                        ACCESS_CONTROL_KEY: {
                            "scope": access_scope,
                            "owner_id": author.agent_id,
                            "allowed_agent_ids": allowed_ids,
                        }
                    },
                    parents=parent_ids,
                    frequency_usage=0.1,  # Initial usage
                    contextual_utility=0.5,  # Default utility
                    cross_domain_connections=0,
                    energy_cost=0.1,  # Base cost
                    last_access_timestamp=time.time(),
                    access_count=0,
                    linkage_manifest=manifest,
                    belief_state_hash=self._compute_belief_state_hash(content, author),
                    sovereign_pubkey=author.public_key,
                    signature="",
                    consciousness_level=consciousness_level
                )
                node.signature = author.sign(node.signature_payload())
                node.integrity_hash = node._compute_integrity_hash()
                
                # Validate node integrity
                if not self._validate_node_integrity(node):
                    raise MemoryIntegrityError("Node failed integrity validation")
                
                # Store the node
                with self.circuit_breakers['database'].protected_call():
                    self._store_node(node)
                
                # Create linkages
                if manifest:
                    self._create_linkages(node.node_id, manifest)
                
                # Log the operation
                self._log_system_event("node_created", author.agent_id, {
                    "node_id": node.node_id,
                    "kind": kind.value,
                    "parents": parent_ids,
                    "linkage_count": sum(len(links) for links in manifest.values())
                })
                
                logger.info(f"Created memory node {node.node_id[:12]} by {author.agent_name}")
                return node
                
        except UnifiedMemoryError:
            raise
        except Exception as e:
            logger.error(f"Failed to create memory node: {e}")
            raise UnifiedMemoryError(f"Node creation failed: {e}")
    
    def retrieve_memory_node(self, node_id: str, requester: Optional[SovereignIdentity] = None) -> Optional[UnifiedMemoryNode]:
        """
        Retrieve a memory node by ID with access control and usage tracking.
        
        Args:
            node_id: ID of the node to retrieve
            requester: Identity requesting the node
            
        Returns:
            UnifiedMemoryNode if found and accessible, None otherwise
        """
        with self.main_lock:
            requester_id, _, _ = self._require_registered_identity(requester)
            with self.circuit_breakers['database'].protected_call():
                node = self._load_node(node_id)
                if node is None:
                    logger.debug(f"Node {node_id[:12]} not found")
                    return None
                if not self._node_access_allowed(node, requester_id):
                    raise MemoryAccessError(
                        f"Sovereign {requester_id[:12]} is not authorized for node {node_id[:12]}"
                    )

                node.record_access()
                with self._database_connection() as connection:
                    connection.execute(
                        """
                        UPDATE unified_nodes
                        SET last_access_timestamp = ?, access_count = ?, frequency_usage = ?
                        WHERE node_id = ?
                        """,
                        (
                            node.last_access_timestamp,
                            node.access_count,
                            node.frequency_usage,
                            node_id,
                        ),
                    )
                    connection.commit()

                self.operation_counts['retrieval'] += 1
                logger.debug(f"Retrieved node {node_id[:12]}")
                return node
    
    def attest_belief(self, node_id: str, attester: SovereignIdentity, belief: float, rationale: str = "") -> bool:
        """
        Create a belief attestation for a node (MTL-style belief anchoring).
        
        Args:
            node_id: ID of node to attest to
            attester: Identity providing the attestation
            belief: Belief score (0.0 to 1.0)
            rationale: Reasoning for the belief
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.main_lock:
                self._require_registered_identity(attester)
                node = self._load_node(node_id)
                if node is None:
                    raise MemoryIntegrityError(
                        f"Cannot attest nonexistent node {node_id[:12]}"
                    )
                self._require_node_access(node, attester)

                # Create attestation
                attestation = attester.attest_belief(node_id, belief, rationale)
                signed_attestation = {
                    "node_id": attestation["node_id"],
                    "agent_id": attestation["agent_id"],
                    "belief": attestation["belief"],
                    "rationale_hash": attestation["rationale_hash"],
                    "timestamp": attestation["timestamp"],
                }
                if not SovereignIdentity.verify_signature(
                    attester.public_key,
                    _canonical_json_bytes(signed_attestation),
                    attestation["signature"],
                ):
                    raise MemoryIntegrityError("Attestation Ed25519 signature is invalid")
                
                # Store attestation
                with self.circuit_breakers['database'].protected_call():
                    with self._database_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO attestations
                            (attestation_id, node_id, agent_id, belief, rationale_hash, signature, timestamp)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            attestation["attestation_id"],
                            attestation["node_id"],
                            attestation["agent_id"],
                            attestation["belief"],
                            attestation["rationale_hash"],
                            attestation["signature"],
                            attestation["timestamp"]
                        ))
                        conn.commit()
                
                # Check for anchoring
                stability_score = self._calculate_stability_score(node_id)
                if self._should_anchor_node(node_id, stability_score):
                    self._anchor_node(node_id, stability_score, "belief")
                
                logger.info(f"Belief attestation recorded for {node_id[:12]} by {attester.agent_name}: {belief}")
                return True
                
        except UnifiedMemoryError:
            raise
        except (sqlite3.Error, TypeError, ValueError) as e:
            logger.error(f"Failed to attest belief: {e}")
            raise MemoryIntegrityError(f"Belief attestation failed: {e}") from e
    
    def create_epistemic_link(self, 
                            source_id: str, 
                            target_id: str, 
                            link_type: LinkageTypeEnum,
                            strength: float = 0.5,
                            creator: Optional[SovereignIdentity] = None) -> bool:
        """
        Create an epistemic link between nodes (SCL-style weaving).
        
        Args:
            source_id: Source node ID
            target_id: Target node ID  
            link_type: Type of linkage
            strength: Link strength (0.0 to 1.0)
            creator: Identity creating the link
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.main_lock:
                with self.circuit_breakers['weaving'].protected_call():
                    self._require_registered_identity(creator)
                    source_node = self._load_node(source_id)
                    target_node = self._load_node(target_id)
                    if source_node is None or target_node is None:
                        raise MemoryIntegrityError(
                            "Cannot create a dangling epistemic link: "
                            f"{source_id[:12]} -> {target_id[:12]}"
                        )
                    self._require_node_access(source_node, creator)
                    self._require_node_access(target_node, creator)
                    if creator is None or creator.agent_id != source_node.author_id:
                        raise MemoryAccessError(
                            "Only the source-node author may mutate its signed linkage manifest"
                        )
                    if not np.isfinite(strength) or not 0.0 <= strength <= 1.0:
                        raise MemoryIntegrityError("Link strength must be between 0.0 and 1.0")

                    creation_timestamp = time.time()
                    link_payload = {
                        "source_id": source_id,
                        "target_id": target_id,
                        "link_type": link_type.value,
                        "strength": float(strength),
                        "creation_timestamp": creation_timestamp,
                        "creator_id": creator.agent_id,
                    }
                    link_signature = creator.sign(_canonical_json_bytes(link_payload))
                    source_node.add_link(link_type, target_id)
                    source_node.signature = creator.sign(source_node.signature_payload())
                    source_node.integrity_hash = source_node._compute_integrity_hash()
                    if not self._validate_node_integrity(source_node):
                        raise MemoryIntegrityError(
                            "Re-signed source node failed integrity validation"
                        )
                    linkage_manifest_ref = self.binary_storage.store_json_compressed(
                        source_node.node_id,
                        {
                            key.value: targets
                            for key, targets in source_node.linkage_manifest.items()
                        },
                        "linkage",
                    )

                    # Commit the signed node mutation and link edge atomically in SQLite.
                    with self._database_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO node_links
                            (source_id, target_id, link_type, strength, creation_timestamp, last_accessed, metadata)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            source_id,
                            target_id,
                            link_type.value,
                            strength,
                            creation_timestamp,
                            creation_timestamp,
                            json.dumps({
                                "creator": creator.agent_id,
                                "creator_public_key": creator.public_key,
                                "creator_signature": link_signature,
                                "signature_payload": link_payload,
                                "creation_context": "epistemic_weaving",
                            })
                        ))
                        cursor.execute(
                            """
                            UPDATE unified_nodes
                            SET linkage_manifest_ref = ?, cross_domain_connections = ?,
                                signature = ?, integrity_hash = ?
                            WHERE node_id = ?
                            """,
                            (
                                linkage_manifest_ref,
                                source_node.cross_domain_connections,
                                source_node.signature,
                                source_node.integrity_hash,
                                source_node.node_id,
                            ),
                        )
                        conn.commit()
                    
                    logger.info(f"Created epistemic link {link_type.value}: {source_id[:12]} -> {target_id[:12]}")
                    return True
                    
        except UnifiedMemoryError:
            raise
        except (sqlite3.Error, TypeError, ValueError) as e:
            logger.error(f"Failed to create epistemic link: {e}")
            raise MemoryIntegrityError(f"Epistemic link creation failed: {e}") from e
    
    def quantum_entangle_nodes(self, node_ids: List[str], creator: SovereignIdentity) -> Optional[str]:
        """
        Create quantum entanglement between multiple nodes (NMCA-style quantum features).
        
        Args:
            node_ids: List of node IDs to entangle
            creator: Identity creating the entanglement
            
        Returns:
            Entanglement ID if successful, None otherwise
        """
        if not self.enable_quantum_features:
            logger.warning("Quantum features disabled - cannot create entanglement")
            return None
        
        try:
            with self.quantum_lock:
                with self.circuit_breakers['quantum'].protected_call():
                    self._require_registered_identity(creator)
                    # Validate all nodes exist
                    nodes = []
                    for node_id in node_ids:
                        node = self._load_node(node_id)
                        if not node:
                            logger.warning(f"Cannot entangle - node not found: {node_id[:12]}")
                            return None
                        self._require_node_access(node, creator)
                        nodes.append(node)
                    
                    # Generate entanglement
                    entanglement_id = str(uuid.uuid4())
                    entanglement_strength = self._calculate_entanglement_strength(nodes)
                    
                    # Create quantum state vector
                    state_vector = self._generate_entangled_state_vector(nodes)
                    
                    # Store entanglement
                    with self._database_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO quantum_entanglements
                            (entanglement_id, branch_ids, entanglement_strength, creation_timestamp, metadata, state_vector)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            entanglement_id,
                            json.dumps(node_ids),
                            entanglement_strength,
                            time.time(),
                            json.dumps({
                                "creator": creator.agent_id,
                                "node_count": len(node_ids),
                                "creation_method": "explicit_entanglement"
                            }),
                            json.dumps(state_vector.tolist() if hasattr(state_vector, 'tolist') else state_vector)
                        ))
                        conn.commit()
                    
                    # Update nodes with entanglement reference
                    for node in nodes:
                        node.entanglement_ids.append(entanglement_id)
                        self._update_node_entanglements(node)
                    
                    self.entanglements[entanglement_id] = {
                        "node_ids": node_ids,
                        "strength": entanglement_strength,
                        "state_vector": state_vector,
                        "creator": creator.agent_id,
                        "timestamp": time.time()
                    }
                    
                    logger.info(f"Created quantum entanglement {entanglement_id[:12]} for {len(node_ids)} nodes")
                    return entanglement_id
                    
        except Exception as e:
            logger.error(f"Failed to create quantum entanglement: {e}")
            return None
    
    def auto_repair_contradictions(self, pivot_node_id: Optional[str] = None) -> List[str]:
        """Reject unverified heuristic repair instead of minting canonical nodes.

        ``pivot_node_id`` is retained only for source compatibility.  There is
        currently no authorized repair verifier, repair identity, or policy
        contract capable of deciding that a contradiction should become a new
        canonical repair record.  Returning an empty list here would make a
        requested repair indistinguishable from a completed no-op, so this
        boundary always fails loudly.
        """
        if pivot_node_id is not None and (
            not isinstance(pivot_node_id, str) or not pivot_node_id
        ):
            raise MemoryIntegrityError("repair pivot node id must be non-empty text")
        raise MemoryIntegrityError(
            "Automatic heuristic repair is unavailable for canonical memory; "
            "no repair nodes were created."
        )
    
    def register_sovereign(self, sovereign: SovereignIdentity) -> bool:
        """
        Register a new sovereign identity in the system.
        
        Args:
            sovereign: Sovereign identity to register
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.main_lock:
                challenge = b"usms-registration-v1\x00" + secrets.token_bytes(32)
                if not SovereignIdentity.verify_signature(
                    sovereign.public_key,
                    challenge,
                    sovereign.sign(challenge),
                ):
                    raise SovereignIdentityError(
                        "Sovereign failed Ed25519 proof of possession"
                    )

                with self.circuit_breakers['database'].protected_call():
                    with self._database_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            """
                            SELECT agent_id, agent_name, public_key
                            FROM sovereign_identities
                            WHERE agent_id = ? OR agent_name = ? OR public_key = ?
                            """,
                            (
                                sovereign.agent_id,
                                sovereign.agent_name,
                                sovereign.public_key,
                            ),
                        )
                        existing_rows = cursor.fetchall()
                        exact_identity = (
                            sovereign.agent_id,
                            sovereign.agent_name,
                            sovereign.public_key,
                        )
                        if existing_rows:
                            if len(existing_rows) == 1 and existing_rows[0] == exact_identity:
                                logger.debug(
                                    f"Sovereign already registered: {sovereign.agent_name}"
                                )
                                return True
                            raise SovereignIdentityError(
                                "Immutable sovereign identity collision for agent id, name, or public key"
                            )

                        cursor.execute("""
                            INSERT INTO sovereign_identities
                            (agent_id, agent_name, public_key, creation_timestamp, trust_level, authentication_method, metadata)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            sovereign.agent_id,
                            sovereign.agent_name,
                            sovereign.public_key,
                            sovereign.creation_timestamp,
                            sovereign.trust_level,
                            sovereign.authentication_method,
                            json.dumps(sovereign.metadata)
                        ))
                        conn.commit()
                
                logger.info(f"Registered sovereign: {sovereign.agent_name} ({sovereign.agent_id[:12]})")
                return True
                
        except SovereignIdentityError:
            raise
        except (sqlite3.Error, TypeError, ValueError) as e:
            logger.error(f"Failed to register sovereign {sovereign.agent_name}: {e}")
            raise SovereignIdentityError(f"Sovereign registration failed: {e}") from e
    
    # Utility and helper methods
    
    def _text_to_semantic_vector(self, text: str, dims: int = 12) -> List[float]:
        """Generate semantic vector from text (MTL approach)."""
        try:
            h = hashlib.sha512(text.encode("utf-8")).digest()
            buf = (h * ((dims * 8) // len(h) + 1))[: dims * 8]
            vector = []
            
            for i in range(0, len(buf), 8):
                chunk = int.from_bytes(buf[i : i + 8], byteorder="big", signed=False)
                vector.append((chunk / 2**63) - 1.0)
            
            return np.asarray(vector, dtype=np.float32).astype(float).tolist()
            
        except Exception as e:
            logger.error(f"Error generating semantic vector: {e}")
            return [0.0] * dims
    
    def _extract_semantic_text(self, content: Dict[str, Any], kind: NodeKindEnum) -> str:
        """Extract text for semantic vector generation."""
        try:
            if "summary" in content:
                return f"{kind.value}::{content['summary']}"
            elif "title" in content:
                return f"{kind.value}::{content['title']}"
            elif "claim" in content:
                return f"{kind.value}::{content['claim']}"
            else:
                # Fallback to stringified content
                content_str = json.dumps(content, sort_keys=True)[:256]
                return f"{kind.value}::{content_str}"
        except Exception as e:
            logger.error(f"Error extracting semantic text: {e}")
            return f"{kind.value}::default"
    
    def _compute_belief_state_hash(self, content: Dict[str, Any], author: SovereignIdentity) -> str:
        """Compute belief state hash (SCL coherence checking)."""
        try:
            belief_data = {
                "content": content,
                "author": author.agent_id,
                "timestamp": time.time(),
                "coherence_verified": True  # In production, this would be actual coherence check
            }
            return hashlib.sha256(json.dumps(belief_data, sort_keys=True).encode()).hexdigest()
        except Exception as e:
            logger.error(f"Error computing belief state hash: {e}")
            return hashlib.sha256(b"default_belief_state").hexdigest()
    
    def _validate_node_integrity(self, node: UnifiedMemoryNode) -> bool:
        """Verify canonical digest, registry binding, Ed25519 signature, and shape."""
        try:
            required_fields = (
                "node_id",
                "author_id",
                "kind",
                "content",
                "sovereign_pubkey",
                "signature",
                "integrity_hash",
            )
            for field_name in required_fields:
                if not getattr(node, field_name, None):
                    logger.error(f"Missing required field: {field_name}")
                    return False

            expected_hash = node._compute_integrity_hash()
            if not secrets.compare_digest(node.integrity_hash, expected_hash):
                logger.error(f"Integrity hash mismatch for node {node.node_id[:12]}")
                return False

            with self._database_connection() as connection:
                author_row = connection.execute(
                    """
                    SELECT public_key FROM sovereign_identities
                    WHERE agent_id = ?
                    """,
                    (node.author_id,),
                ).fetchone()
            if author_row is None:
                logger.error(f"Node author is not registered: {node.author_id[:12]}")
                return False

            registered_public_key = author_row[0]
            if not secrets.compare_digest(
                registered_public_key, node.sovereign_pubkey
            ):
                logger.error(f"Node public key is not bound to author {node.author_id[:12]}")
                return False
            if not SovereignIdentity.verify_signature(
                registered_public_key,
                node.signature_payload(),
                node.signature,
            ):
                logger.error(f"Invalid Ed25519 signature for node {node.node_id[:12]}")
                return False

            if (
                not node.semantic_vector
                or len(node.semantic_vector) > SEMANTIC_VECTOR_MAX_DIMENSIONS
                or not all(
                np.isfinite(value) for value in node.semantic_vector
                )
            ):
                logger.error("Invalid semantic vector")
                return False
            canonical_vector = (
                np.asarray(node.semantic_vector, dtype=np.float32)
                .astype(float)
                .tolist()
            )
            if node.semantic_vector != canonical_vector:
                logger.error("Semantic vector is not in canonical float32 form")
                return False

            access_control = node.meta_patch.get(ACCESS_CONTROL_KEY, {})
            if access_control:
                if not isinstance(access_control, dict):
                    logger.error("Invalid node access-control metadata")
                    return False
                if access_control.get("scope") not in VALID_ACCESS_SCOPES:
                    logger.error("Invalid node access scope")
                    return False
                if access_control.get("owner_id") != node.author_id:
                    logger.error("Node access-control owner does not match author")
                    return False
                allowed_agent_ids = access_control.get("allowed_agent_ids", [])
                if not isinstance(allowed_agent_ids, list) or any(
                    not isinstance(agent_id, str) for agent_id in allowed_agent_ids
                ):
                    logger.error("Invalid node access allowlist")
                    return False

            return True

        except (MemoryIntegrityError, sqlite3.Error, TypeError, ValueError) as e:
            logger.error(f"Node integrity validation failed: {e}")
            return False
    
    def _store_node(self, node: UnifiedMemoryNode):
        """Store a node in the database with optimized binary storage."""
        try:
            if not self._validate_node_integrity(node):
                raise MemoryIntegrityError(
                    f"Refusing to store invalid canonical node {node.node_id[:12]}"
                )
            with self.process_coordinator.database_lock("store_node"):
                # Store heavy data in binary format
                semantic_vector_ref = self.binary_storage.store_semantic_vector(node.node_id, node.semantic_vector)
                meta_patch_ref = self.binary_storage.store_json_compressed(node.node_id, node.meta_patch, "meta")
                linkage_manifest_ref = self.binary_storage.store_json_compressed(
                    node.node_id, 
                    {k.value: v for k, v in node.linkage_manifest.items()}, 
                    "linkage"
                )
                
                with self._database_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO unified_nodes
                        (node_id, author_id, kind, timestamp, content, semantic_vector_ref, meta_patch_ref, parents,
                         frequency_usage, contextual_utility, cross_domain_connections, energy_cost,
                         last_access_timestamp, access_count, linkage_manifest_ref, belief_state_hash,
                         sovereign_pubkey, signature, quantum_state, entanglement_ids, consciousness_level,
                         integrity_hash, belief_decay_timestamp, belief_half_life_days)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        node.node_id, node.author_id, node.kind.value, node.timestamp,
                        json.dumps(node.content), semantic_vector_ref, meta_patch_ref, json.dumps(node.parents),
                        node.frequency_usage, node.contextual_utility, node.cross_domain_connections,
                        node.energy_cost, node.last_access_timestamp, node.access_count,
                        linkage_manifest_ref, node.belief_state_hash, node.sovereign_pubkey, node.signature,
                        json.dumps(node.quantum_state) if node.quantum_state else None,
                        json.dumps(node.entanglement_ids), node.consciousness_level,
                        node.integrity_hash,
                        getattr(node, 'belief_decay_timestamp', time.time()),
                        getattr(node, 'belief_half_life_days', self.policy.get('belief_half_life_days', 365.0))
                    ))
                    conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to store node {node.node_id[:12]}: {e}")
            raise MemoryIntegrityError(f"Node storage failed: {e}")
    
    def _row_to_node(self, row: tuple) -> UnifiedMemoryNode:
        """Convert database row to UnifiedMemoryNode with optimized binary storage loading."""
        try:
            # Handle schema evolution - detect format by number of columns
            if len(row) == 22:  # Legacy format (direct JSON storage)
                (node_id, author_id, kind, timestamp, content, semantic_vector_data, meta_patch_data, parents,
                 frequency_usage, contextual_utility, cross_domain_connections, energy_cost,
                 last_access_timestamp, access_count, linkage_manifest_data, belief_state_hash,
                 sovereign_pubkey, signature, quantum_state, entanglement_ids, consciousness_level,
                 integrity_hash) = row
                belief_decay_timestamp = time.time()
                belief_half_life_days = 365.0
                
                # Legacy direct JSON parsing
                semantic_vector = json.loads(semantic_vector_data) if semantic_vector_data else []
                meta_patch = json.loads(meta_patch_data) if meta_patch_data else {}
                linkage_dict = json.loads(linkage_manifest_data) if linkage_manifest_data else {}
                
            elif len(row) == 24:  # Current optimized format (binary storage references)
                (node_id, author_id, kind, timestamp, content, semantic_vector_ref, meta_patch_ref, parents,
                 frequency_usage, contextual_utility, cross_domain_connections, energy_cost,
                 last_access_timestamp, access_count, linkage_manifest_ref, belief_state_hash,
                 sovereign_pubkey, signature, quantum_state, entanglement_ids, consciousness_level,
                 integrity_hash, belief_decay_timestamp, belief_half_life_days) = row
                
                # Load from binary storage
                semantic_vector = self.binary_storage.load_semantic_vector(semantic_vector_ref)
                meta_patch = self.binary_storage.load_json_compressed(meta_patch_ref)
                linkage_dict = self.binary_storage.load_json_compressed(linkage_manifest_ref)
                
            else:  # Handle intermediate formats
                logger.warning(f"Unknown row format with {len(row)} columns for node {row[0] if row else 'unknown'}")
                # Default to legacy parsing attempt
                (node_id, author_id, kind, timestamp, content, semantic_vector_data, meta_patch_data, parents,
                 frequency_usage, contextual_utility, cross_domain_connections, energy_cost,
                 last_access_timestamp, access_count, linkage_manifest_data, belief_state_hash,
                 sovereign_pubkey, signature, quantum_state, entanglement_ids, consciousness_level,
                 integrity_hash, belief_decay_timestamp, belief_half_life_days) = row[:24]
                
                semantic_vector = json.loads(semantic_vector_data) if semantic_vector_data else []
                meta_patch = json.loads(meta_patch_data) if meta_patch_data else {}
                linkage_dict = json.loads(linkage_manifest_data) if linkage_manifest_data else {}
            
            # Parse remaining JSON fields
            content = json.loads(content) if content else {}
            parents = json.loads(parents) if parents else []
            quantum_state = json.loads(quantum_state) if quantum_state else None
            entanglement_ids = json.loads(entanglement_ids) if entanglement_ids else []
            
            # Convert linkage manifest keys back to enums
            linkage_manifest = {
                LinkageTypeEnum(k): v for k, v in linkage_dict.items()
            } if linkage_dict else {}
            
            node = UnifiedMemoryNode(
                node_id=node_id,
                author_id=author_id,
                kind=NodeKindEnum(kind),
                timestamp=timestamp,
                content=content,
                semantic_vector=semantic_vector,
                meta_patch=meta_patch,
                parents=parents,
                frequency_usage=frequency_usage,
                contextual_utility=contextual_utility,
                cross_domain_connections=cross_domain_connections,
                energy_cost=energy_cost,
                last_access_timestamp=last_access_timestamp,
                access_count=access_count,
                linkage_manifest=linkage_manifest,
                belief_state_hash=belief_state_hash,
                sovereign_pubkey=sovereign_pubkey,
                signature=signature,
                quantum_state=quantum_state,
                entanglement_ids=entanglement_ids,
                consciousness_level=consciousness_level,
                integrity_hash=integrity_hash
            )
            
            # Add belief decay attributes
            node.belief_decay_timestamp = belief_decay_timestamp
            node.belief_half_life_days = belief_half_life_days

            if not self._validate_node_integrity(node):
                raise MemoryIntegrityError(
                    f"Canonical node failed validation: {node.node_id[:12]}"
                )
            
            return node
            
        except Exception as e:
            logger.error(f"Failed to convert row to node: {e}")
            raise MemoryIntegrityError(f"Node deserialization failed: {e}")
    
    def _calculate_consciousness_level(self) -> float:
        """Calculate cognitive consciousness level based on memory network coherence and self-consistency."""
        try:
            # Cognitive metrics - based on memory network properties, not hardware resources
            
            # 1. Memory Network Coherence - how well connected and consistent the memory graph is
            network_coherence = self._calculate_network_coherence()
            
            # 2. Epistemic Consistency - how contradictory are the beliefs in the system
            epistemic_consistency = self._calculate_epistemic_consistency()
            
            # 3. Temporal Coherence - how well does the system maintain temporal logic
            temporal_coherence = self._calculate_temporal_coherence()
            
            # 4. Self-Reference Integrity - how well the system understands itself
            self_reference_integrity = self._calculate_self_reference_integrity()
            
            # 5. Cognitive Depth - complexity and sophistication of reasoning chains
            cognitive_depth = self._calculate_cognitive_depth()
            
            # System health baseline (reduced weight - only for basic operational capacity)
            system_health = self._calculate_basic_system_health()
            
            # Weighted consciousness calculation emphasizing cognitive over system metrics
            consciousness = (
                0.25 * network_coherence +       # How coherent is the memory network
                0.20 * epistemic_consistency +   # How consistent are beliefs
                0.20 * temporal_coherence +      # How logical is temporal reasoning
                0.15 * self_reference_integrity + # How well does system know itself
                0.10 * cognitive_depth +         # How sophisticated is reasoning
                0.10 * system_health            # Basic operational capacity
            )
            
            result = max(0.0, min(1.0, consciousness))
            logger.debug(f"Consciousness calculation - Network: {network_coherence:.3f}, "
                        f"Epistemic: {epistemic_consistency:.3f}, Temporal: {temporal_coherence:.3f}, "
                        f"Self-Ref: {self_reference_integrity:.3f}, Depth: {cognitive_depth:.3f}, "
                        f"System: {system_health:.3f}, Final: {result:.3f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating consciousness level: {e}")
            return 0.5  # Default consciousness level
    
    def _calculate_network_coherence(self) -> float:
        """Calculate how coherent and well-connected the memory network is."""
        try:
            with self._database_connection() as conn:
                cursor = conn.cursor()
                
                # Get total nodes and connections
                cursor.execute("SELECT COUNT(*) FROM unified_nodes")
                total_nodes = cursor.fetchone()[0]
                
                if total_nodes < 2:
                    return 0.5  # Not enough data
                
                cursor.execute("SELECT COUNT(*) FROM node_links")
                total_links = cursor.fetchone()[0]
                
                # Network density (connections per node)
                density = total_links / max(1, total_nodes) if total_nodes > 0 else 0
                density_score = min(1.0, density / 3.0)  # Normalize to expected 3 links per node
                
                # Check for strongly connected components vs isolated nodes
                cursor.execute("""
                    SELECT COUNT(*) FROM unified_nodes n 
                    WHERE NOT EXISTS (
                        SELECT 1 FROM node_links l 
                        WHERE l.source_id = n.node_id OR l.target_id = n.node_id
                    )
                """)
                isolated_nodes = cursor.fetchone()[0]
                connectivity_score = 1.0 - (isolated_nodes / max(1, total_nodes))
                
                return (density_score * 0.6 + connectivity_score * 0.4)
                
        except Exception as e:
            logger.debug(f"Network coherence calculation failed: {e}")
            return 0.5
    
    def _calculate_epistemic_consistency(self) -> float:
        """Calculate how consistent the belief system is (fewer contradictions = higher score)."""
        try:
            with self._database_connection() as conn:
                cursor = conn.cursor()
                
                # Count belief nodes
                cursor.execute("SELECT COUNT(*) FROM unified_nodes WHERE kind = 'belief'")
                belief_count = cursor.fetchone()[0]
                
                if belief_count < 2:
                    return 1.0  # No contradictions possible
                
                # Count contradiction/repair relationships
                cursor.execute("""
                    SELECT COUNT(*) FROM node_links 
                    WHERE link_type IN ('contradiction', 'repair')
                """)
                contradiction_count = cursor.fetchone()[0]
                
                # Higher consistency = fewer contradictions relative to beliefs
                consistency_ratio = 1.0 - min(1.0, contradiction_count / max(1, belief_count))
                
                return max(0.1, consistency_ratio)
                
        except Exception as e:
            logger.debug(f"Epistemic consistency calculation failed: {e}")
            return 0.5
    
    def _calculate_temporal_coherence(self) -> float:
        """Calculate how well temporal relationships make logical sense."""
        try:
            with self._database_connection() as conn:
                cursor = conn.cursor()
                
                # Check for temporal paradoxes (effects before causes)
                cursor.execute("""
                    SELECT COUNT(*) FROM node_links l
                    JOIN unified_nodes source ON l.source_id = source.node_id
                    JOIN unified_nodes target ON l.target_id = target.node_id
                    WHERE l.link_type = 'causal_parent'
                    AND source.timestamp > target.timestamp
                """)
                paradox_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM node_links WHERE link_type = 'causal_parent'")
                causal_link_count = cursor.fetchone()[0]
                
                if causal_link_count == 0:
                    return 0.8  # No causal links, but not necessarily bad
                
                temporal_coherence = 1.0 - (paradox_count / max(1, causal_link_count))
                return max(0.0, temporal_coherence)
                
        except Exception as e:
            logger.debug(f"Temporal coherence calculation failed: {e}")
            return 0.5
    
    def _calculate_self_reference_integrity(self) -> float:
        """Calculate how well the system understands and references itself."""
        try:
            with self._database_connection() as conn:
                cursor = conn.cursor()
                
                # Count self-referential nodes (meta blocks, repair blocks, snapshots)
                cursor.execute("""
                    SELECT COUNT(*) FROM unified_nodes 
                    WHERE kind IN ('meta', 'repair', 'snapshot')
                """)
                self_ref_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM unified_nodes")
                total_nodes = cursor.fetchone()[0]
                
                if total_nodes == 0:
                    return 0.0
                
                # Healthy self-reference ratio (about 10-20% of nodes should be self-referential)
                self_ref_ratio = self_ref_count / total_nodes
                optimal_ratio = 0.15  # 15% is optimal
                
                # Score based on how close to optimal ratio
                if self_ref_ratio <= optimal_ratio:
                    score = self_ref_ratio / optimal_ratio
                else:
                    # Penalize too much self-reference (narcissistic system)
                    score = max(0.1, 1.0 - (self_ref_ratio - optimal_ratio) / optimal_ratio)
                
                return min(1.0, score)
                
        except Exception as e:
            logger.debug(f"Self-reference integrity calculation failed: {e}")
            return 0.5
    
    def _calculate_cognitive_depth(self) -> float:
        """Calculate the depth and sophistication of reasoning chains."""
        try:
            with self._database_connection() as conn:
                cursor = conn.cursor()
                
                # Find longest reasoning chains (epistemic parent chains)
                cursor.execute("""
                    WITH RECURSIVE reasoning_chains AS (
                        SELECT n.node_id, n.author_id, 1 as depth
                        FROM unified_nodes n
                        WHERE NOT EXISTS (
                            SELECT 1
                            FROM node_links l
                            WHERE l.target_id = n.node_id
                              AND l.link_type = 'epistemic_parent'
                        )
                        
                        UNION ALL
                        
                        SELECT parent.node_id, parent.author_id, rc.depth + 1
                        FROM node_links l
                        JOIN unified_nodes parent ON parent.node_id = l.target_id
                        JOIN reasoning_chains rc ON l.source_id = rc.node_id
                        WHERE l.link_type = 'epistemic_parent'
                          AND rc.depth < 10
                    )
                    SELECT MAX(depth) as max_depth, AVG(depth) as avg_depth
                    FROM reasoning_chains
                """)
                
                result = cursor.fetchone()
                max_depth = result[0] if result[0] else 1
                avg_depth = result[1] if result[1] else 1
                
                # Normalize depth scores
                depth_sophistication = min(1.0, (max_depth - 1) / 9.0)  # Max depth of 10 = score of 1
                average_sophistication = min(1.0, (avg_depth - 1) / 4.0)  # Avg depth of 5 = score of 1
                
                return (depth_sophistication * 0.6 + average_sophistication * 0.4)
                
        except Exception as e:
            logger.debug(f"Cognitive depth calculation failed: {e}")
            return 0.3
    
    def _calculate_basic_system_health(self) -> float:
        """Calculate basic operational system health (minimal hardware dependency)."""
        try:
            # Simple system health - just enough to ensure basic operation
            memory_info = psutil.virtual_memory()
            memory_ok = 1.0 if memory_info.available > (1024 * 1024 * 100) else 0.5  # 100MB available
            
            # Database accessibility
            db_ok = 1.0
            try:
                with self._database_connection() as conn:
                    conn.execute("SELECT 1").fetchone()
            except Exception:
                db_ok = 0.0
            
            return (memory_ok * 0.3 + db_ok * 0.7)
            
        except Exception as e:
            logger.debug(f"Basic system health calculation failed: {e}")
            return 0.5
    
    def _calculate_stability_score(self, node_id: str) -> float:
        """Calculate belief stability score for a node (MTL approach)."""
        try:
            with self._database_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT agent_id, belief FROM attestations WHERE node_id = ?
                """, (node_id,))
                rows = cursor.fetchall()
                
                if not rows:
                    return 0.0
                
                # Calculate mean belief from distinct agents
                agent_beliefs = {}
                for agent_id, belief in rows:
                    agent_beliefs[agent_id] = float(belief)
                
                if len(agent_beliefs) == 0:
                    return 0.0
                
                stability = sum(agent_beliefs.values()) / len(agent_beliefs)
                return stability
                
        except Exception as e:
            logger.error(f"Error calculating stability score: {e}")
            return 0.0
    
    def _should_anchor_node(self, node_id: str, stability_score: float) -> bool:
        """Determine if a node should be anchored."""
        try:
            # Check policy thresholds
            anchor_threshold = self.policy.get("anchor_threshold", 0.74)
            min_support = self.policy.get("anchor_support_min", 2)
            
            if stability_score < anchor_threshold:
                return False
            
            # Count distinct supporters
            with self._database_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(DISTINCT agent_id) FROM attestations 
                    WHERE node_id = ? AND belief >= ?
                """, (node_id, anchor_threshold))
                supporter_count = cursor.fetchone()[0] or 0
                
                return supporter_count >= min_support
                
        except Exception as e:
            logger.error(f"Error checking anchor eligibility: {e}")
            return False
    
    def _anchor_node(self, node_id: str, score: float, anchor_type: str = "belief"):
        """Anchor a node with the given score."""
        if not isinstance(node_id, str) or not node_id:
            raise MemoryIntegrityError("Anchor node_id must be non-empty text")
        if not isinstance(score, (int, float)) or isinstance(score, bool):
            raise MemoryIntegrityError("Anchor score must be numeric")
        score = float(score)
        if not math.isfinite(score) or not 0.0 <= score <= 1.0:
            raise MemoryIntegrityError("Anchor score must be finite and between 0 and 1")
        if not isinstance(anchor_type, str) or not anchor_type.strip():
            raise MemoryIntegrityError("Anchor type must be non-empty text")
        try:
            with self._database_connection() as conn:
                cursor = conn.cursor()
                node_exists = cursor.execute(
                    "SELECT 1 FROM unified_nodes WHERE node_id = ?",
                    (node_id,),
                ).fetchone()
                if node_exists is None:
                    raise MemoryIntegrityError(
                        f"Cannot anchor nonexistent node {node_id[:12]}"
                    )
                cursor.execute("""
                    INSERT OR REPLACE INTO anchors
                    (node_id, timestamp, score, anchor_type, metadata)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    node_id,
                    time.time(),
                    score,
                    anchor_type,
                    json.dumps({
                        "anchoring_reason": anchor_type,
                        "system_consciousness": self._calculate_consciousness_level()
                    })
                ))
                conn.commit()
                
                self.anchored_nodes.add(node_id)
                logger.info(f"Anchored node {node_id[:12]} with score {score:.3f}")
                
        except UnifiedMemoryError:
            raise
        except (sqlite3.Error, TypeError, ValueError) as e:
            logger.error(f"Failed to anchor node {node_id[:12]}: {e}")
            raise MemoryIntegrityError(f"Anchor persistence failed: {e}") from e
    
    def _create_linkages(self, node_id: str, linkage_manifest: Dict[LinkageTypeEnum, List[str]]):
        """Create database linkages from linkage manifest."""
        try:
            with self._database_connection() as conn:
                cursor = conn.cursor()
                
                for link_type, target_ids in linkage_manifest.items():
                    for target_id in dict.fromkeys(target_ids):
                        target_exists = cursor.execute(
                            "SELECT 1 FROM unified_nodes WHERE node_id = ?",
                            (target_id,),
                        ).fetchone()
                        if target_exists is None:
                            raise MemoryIntegrityError(
                                f"Refusing dangling linkage to {target_id[:12]}"
                            )
                        cursor.execute("""
                            INSERT INTO node_links
                            (source_id, target_id, link_type, strength, creation_timestamp, last_accessed, metadata)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            node_id,
                            target_id,
                            link_type.value,
                            0.5,  # Default strength
                            time.time(),
                            time.time(),
                            json.dumps({"auto_generated": True})
                        ))
                
                conn.commit()
                
        except UnifiedMemoryError:
            raise
        except (sqlite3.Error, TypeError, ValueError) as e:
            logger.error(f"Failed to create linkages for {node_id[:12]}: {e}")
            raise MemoryIntegrityError(f"Linkage persistence failed: {e}") from e
    
    def _validate_repair_policy(self) -> None:
        """Reject unsupported automatic canonical repair before any mutation.

        The legacy implementation advertised an automatic repair scheduler but
        only emitted a log line.  Worse, its separate repair routine can derive
        canonical repair nodes from heuristic contradiction similarity.  Neither
        behavior is an authority-preserving production operation.  Automatic
        repair therefore remains deliberately unavailable until a separately
        approved repair policy, verifier, and provenance contract exist.
        """
        repair_auto = self.policy.get("repair_auto", False)
        if type(repair_auto) is not bool:
            raise MemoryIntegrityError("policy repair_auto must be a boolean")
        if repair_auto:
            raise MemoryIntegrityError(
                "Automatic heuristic repair is unavailable for canonical memory; "
                "set policy repair_auto to false and use an explicitly approved "
                "repair workflow."
            )

    def _schedule_repair_check(self, node_id: str) -> None:
        """Fail loud rather than counterfeit an asynchronous repair transition."""
        if not isinstance(node_id, str) or not node_id:
            raise MemoryIntegrityError("repair-check node id must be non-empty text")
        raise MemoryIntegrityError(
            "Automatic repair scheduling is unavailable for canonical memory; "
            "no repair was queued."
        )
    
    def _detect_contradictions(self, pivot_node_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Detect contradictions in the memory system."""
        try:
            contradictions = []
            
            # Get nodes to check for contradictions
            with self._database_connection() as conn:
                cursor = conn.cursor()
                
                if pivot_node_id:
                    # Focus around pivot node
                    cursor.execute("""
                        SELECT * FROM unified_nodes 
                        WHERE kind IN ('belief', 'event') 
                        AND (node_id = ? OR node_id IN (
                            SELECT target_id FROM node_links WHERE source_id = ?
                        ))
                        ORDER BY timestamp DESC LIMIT 50
                    """, (pivot_node_id, pivot_node_id))
                else:
                    # Check recent nodes
                    cursor.execute("""
                        SELECT * FROM unified_nodes 
                        WHERE kind IN ('belief', 'event')
                        ORDER BY timestamp DESC LIMIT 100
                    """, )
                
                rows = cursor.fetchall()
                nodes = [self._row_to_node(row) for row in rows]
            
            # Find contradictory pairs
            contradiction_threshold = self.policy.get("contradiction_cosine", 0.82)
            
            for i in range(len(nodes)):
                for j in range(i + 1, len(nodes)):
                    node_a, node_b = nodes[i], nodes[j]
                    
                    # Calculate semantic similarity
                    similarity = self._cosine_similarity(node_a.semantic_vector, node_b.semantic_vector)
                    
                    if similarity < contradiction_threshold:
                        continue
                    
                    # Check for opposing polarity
                    polarity_a = node_a.content.get("polarity", 0)
                    polarity_b = node_b.content.get("polarity", 0)
                    
                    if isinstance(polarity_a, (int, float)) and isinstance(polarity_b, (int, float)):
                        if polarity_a * polarity_b < 0:  # Opposite signs
                            contradictions.append({
                                "source": node_a.to_dict(),
                                "target": node_b.to_dict(),
                                "similarity": similarity,
                                "polarity_conflict": True
                            })
            
            return contradictions[:10]  # Limit to prevent explosion
            
        except Exception as e:
            logger.error(f"Error detecting contradictions: {e}")
            return []
    
    def _cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """Calculate cosine similarity between vectors."""
        try:
            if not vec_a or not vec_b or len(vec_a) != len(vec_b):
                return 0.0
            
            dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
            norm_a = sum(a * a for a in vec_a) ** 0.5
            norm_b = sum(b * b for b in vec_b) ** 0.5
            
            if norm_a == 0 or norm_b == 0:
                return 0.0
            
            return dot_product / (norm_a * norm_b)
            
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0
    
    def _already_bridged(self, node_a_id: str, node_b_id: str) -> bool:
        """Check if two nodes are already bridged by a repair node."""
        try:
            with self._database_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM node_links l1
                    JOIN node_links l2 ON l1.source_id = l2.source_id
                    JOIN unified_nodes n ON l1.source_id = n.node_id
                    WHERE n.kind = 'repair'
                    AND ((l1.target_id = ? AND l2.target_id = ?) OR (l1.target_id = ? AND l2.target_id = ?))
                """, (node_a_id, node_b_id, node_b_id, node_a_id))
                
                count = cursor.fetchone()[0] or 0
                return count > 0
                
        except Exception as e:
            logger.error(f"Error checking if bridged: {e}")
            return False
    
    def _create_repair_node(self, source_node: Dict[str, Any], target_node: Dict[str, Any], similarity: float) -> Optional[str]:
        """Create a repair node to resolve contradiction."""
        try:
            # Create system sovereign for repair operations
            system_sovereign = SovereignIdentity(
                agent_name="system_repair",
                agent_id=hashlib.sha256(b"system_repair").hexdigest()[:64],
                public_key="",
                creation_timestamp=time.time()
            )
            
            # Determine repair strategy
            source_anchored = source_node["node_id"] in self.anchored_nodes
            target_anchored = target_node["node_id"] in self.anchored_nodes
            
            if source_anchored and not target_anchored:
                repair_strategy = "override_source"
            elif target_anchored and not source_anchored:
                repair_strategy = "override_target"
            else:
                repair_strategy = "coexist"
            
            # Create repair content
            repair_content = {
                "summary": f"Repair synthesis: {repair_strategy}",
                "contradiction_pair": [source_node["node_id"], target_node["node_id"]],
                "similarity_score": similarity,
                "repair_strategy": repair_strategy,
                "source_summary": source_node["content"].get("summary", ""),
                "target_summary": target_node["content"].get("summary", ""),
                "resolution": f"Detected contradiction resolved via {repair_strategy} strategy"
            }
            
            # Create repair node
            repair_node = self.create_memory_node(
                author=system_sovereign,
                kind=NodeKindEnum.REPAIR,
                content=repair_content,
                parents=[source_node["node_id"], target_node["node_id"]],
                linkage_manifest={
                    LinkageTypeEnum.CAUSAL_PARENT: [source_node["node_id"], target_node["node_id"]],
                    LinkageTypeEnum.SYNTHESIS: [source_node["node_id"], target_node["node_id"]]
                },
                semantic_context=f"repair::{repair_strategy}::{similarity:.3f}"
            )
            
            logger.info(f"Created repair node {repair_node.node_id[:12]} for contradiction")
            return repair_node.node_id
            
        except Exception as e:
            logger.error(f"Failed to create repair node: {e}")
            return None
    
    def _calculate_entanglement_strength(self, nodes: List[UnifiedMemoryNode]) -> float:
        """Calculate quantum entanglement strength between nodes."""
        try:
            if len(nodes) < 2:
                return 0.0
            
            # Calculate average semantic similarity
            total_similarity = 0.0
            pairs = 0
            
            for i in range(len(nodes)):
                for j in range(i + 1, len(nodes)):
                    similarity = self._cosine_similarity(nodes[i].semantic_vector, nodes[j].semantic_vector)
                    total_similarity += similarity
                    pairs += 1
            
            avg_similarity = total_similarity / pairs if pairs > 0 else 0.0
            
            # Factor in consciousness levels
            avg_consciousness = sum(node.consciousness_level for node in nodes) / len(nodes)
            
            # Combine factors
            entanglement_strength = (avg_similarity * 0.7) + (avg_consciousness * 0.3)
            
            return max(0.0, min(1.0, entanglement_strength))
            
        except Exception as e:
            logger.error(f"Error calculating entanglement strength: {e}")
            return 0.5
    
    def _generate_entangled_state_vector(self, nodes: List[UnifiedMemoryNode]) -> np.ndarray:
        """Generate quantum state vector for entangled nodes."""
        try:
            if not nodes:
                return np.array([])
            
            # Combine semantic vectors
            combined_vector = []
            for node in nodes:
                combined_vector.extend(node.semantic_vector)
            
            # Convert to numpy array and normalize
            state_vector = np.array(combined_vector)
            norm = np.linalg.norm(state_vector)
            
            if norm > 0:
                state_vector = state_vector / norm
            
            return state_vector
            
        except Exception as e:
            logger.error(f"Error generating entangled state vector: {e}")
            return np.array([0.0])
    
    def _update_node_entanglements(self, node: UnifiedMemoryNode):
        """Update node's entanglement IDs in database."""
        try:
            node.integrity_hash = node._compute_integrity_hash()
            with self._database_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE unified_nodes 
                    SET entanglement_ids = ?, integrity_hash = ?
                    WHERE node_id = ?
                """, (
                    json.dumps(node.entanglement_ids),
                    node.integrity_hash,
                    node.node_id
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to update node entanglements: {e}")
    
    def _log_system_event(self, event_type: str, agent_id: Optional[str], details: Dict[str, Any]):
        """Log system events for audit trail."""
        try:
            with self._database_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO system_events
                    (event_id, event_type, timestamp, agent_id, details, success)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    str(uuid.uuid4()),
                    event_type,
                    time.time(),
                    agent_id,
                    json.dumps(details),
                    True
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to log system event: {e}")
    
    # Query and analysis methods
    
    def get_node_lineage(
        self,
        node_id: str,
        lineage_type: LinkageTypeEnum = LinkageTypeEnum.EPISTEMIC_PARENT,
        requester: Optional[SovereignIdentity] = None,
    ) -> List[UnifiedMemoryNode]:
        """
        Trace the lineage of a node following specific link types.
        
        Args:
            node_id: Starting node ID
            lineage_type: Type of lineage to follow
            requester: Authenticated identity requesting the lineage
            
        Returns:
            List of nodes in lineage order
        """
        self._require_registered_identity(requester)
        lineage = []
        current_id = node_id
        visited = set()

        while current_id and current_id not in visited:
            visited.add(current_id)

            node = self.retrieve_memory_node(current_id, requester=requester)
            if not node:
                break

            lineage.append(node)

            parent_ids = node.linkage_manifest.get(lineage_type, [])
            current_id = parent_ids[0] if parent_ids else None

        logger.debug(f"Retrieved lineage of {len(lineage)} nodes for {node_id[:12]}")
        return lineage
    
    def get_sovereign_timeline(
        self,
        sovereign_id: str,
        limit: int = 100,
        requester: Optional[SovereignIdentity] = None,
    ) -> List[UnifiedMemoryNode]:
        """
        Get chronological timeline of nodes created by a sovereign.
        
        Args:
            sovereign_id: Sovereign agent ID
            limit: Maximum number of nodes to return
            requester: Authenticated identity requesting the timeline
            
        Returns:
            List of nodes in chronological order
        """
        requester_id, _, _ = self._require_registered_identity(requester)
        with self._database_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM unified_nodes
                WHERE author_id = ?
                ORDER BY timestamp ASC
                LIMIT ?
                """,
                (sovereign_id, limit),
            ).fetchall()

        nodes = [self._row_to_node(row) for row in rows]
        authorized_nodes = [
            node for node in nodes if self._node_access_allowed(node, requester_id)
        ]
        logger.debug(
            f"Retrieved timeline of {len(authorized_nodes)} nodes for sovereign {sovereign_id[:12]}"
        )
        return authorized_nodes
    
    def search_nodes_by_content(
        self,
        query: str,
        limit: int = 50,
        requester: Optional[SovereignIdentity] = None,
    ) -> List[UnifiedMemoryNode]:
        """
        Search nodes by content using semantic similarity.
        
        Args:
            query: Search query
            limit: Maximum results to return
            requester: Authenticated identity requesting search results
            
        Returns:
            List of matching nodes ordered by relevance
        """
        requester_id, _, _ = self._require_registered_identity(requester)
        query_vector = self._text_to_semantic_vector(query)

        with self._database_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM unified_nodes ORDER BY timestamp DESC LIMIT 1000"
            ).fetchall()

        scored_nodes = []
        for row in rows:
            node = self._row_to_node(row)
            if not self._node_access_allowed(node, requester_id):
                continue
            similarity = self._cosine_similarity(query_vector, node.semantic_vector)
            relevance = node.calculate_relevance(self.policy)
            combined_score = (similarity * 0.7) + (relevance * 0.3)
            scored_nodes.append((combined_score, node))

        scored_nodes.sort(key=lambda item: item[0], reverse=True)
        results = [node for _, node in scored_nodes[:limit]]
        logger.info(f"Search for '{query}' returned {len(results)} results")
        return results

    def list_nodes(
        self,
        requester: SovereignIdentity,
        limit: int = 100,
        offset: int = 0,
    ) -> List[UnifiedMemoryNode]:
        """List an authenticated requester's authorized canonical nodes."""
        requester_id, _, _ = self._require_registered_identity(requester)
        if not 1 <= limit <= 1_000:
            raise ValueError("limit must be between 1 and 1000")
        if offset < 0:
            raise ValueError("offset must be non-negative")

        authorized_nodes: List[UnifiedMemoryNode] = []
        authorized_seen = 0
        database_offset = 0
        batch_size = min(1_000, max(256, limit * 2))

        while len(authorized_nodes) < limit:
            with self._database_connection() as connection:
                rows = connection.execute(
                    """
                    SELECT * FROM unified_nodes
                    ORDER BY timestamp ASC, node_id ASC
                    LIMIT ? OFFSET ?
                    """,
                    (batch_size, database_offset),
                ).fetchall()
            if not rows:
                break
            database_offset += len(rows)

            for row in rows:
                node = self._row_to_node(row)
                if not self._node_access_allowed(node, requester_id):
                    continue
                if authorized_seen < offset:
                    authorized_seen += 1
                    continue
                authorized_nodes.append(node)
                if len(authorized_nodes) == limit:
                    break

        return authorized_nodes
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        try:
            stats = {}
            
            with self._database_connection() as conn:
                cursor = conn.cursor()
                
                # Node counts by type
                cursor.execute("SELECT kind, COUNT(*) FROM unified_nodes GROUP BY kind")
                stats["nodes_by_type"] = dict(cursor.fetchall())
                
                # Total nodes
                cursor.execute("SELECT COUNT(*) FROM unified_nodes")
                stats["total_nodes"] = cursor.fetchone()[0]
                
                # Anchored nodes
                cursor.execute("SELECT COUNT(*) FROM anchors")
                stats["anchored_nodes"] = cursor.fetchone()[0]
                
                # Links
                cursor.execute("SELECT COUNT(*) FROM node_links")
                stats["total_links"] = cursor.fetchone()[0]
                
                # Entanglements
                cursor.execute("SELECT COUNT(*) FROM quantum_entanglements")
                stats["quantum_entanglements"] = cursor.fetchone()[0]
                
                # Recent activity (last 24 hours)
                day_ago = time.time() - 86400
                cursor.execute("SELECT COUNT(*) FROM unified_nodes WHERE last_access_timestamp > ?", (day_ago,))
                stats["active_nodes_24h"] = cursor.fetchone()[0]
                
                # System health
                stats["consciousness_level"] = self._calculate_consciousness_level()
                stats["operation_counts"] = dict(self.operation_counts)
                stats["circuit_breaker_states"] = {
                    name: breaker.state.name for name, breaker in self.circuit_breakers.items()
                }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error generating system statistics: {e}")
            return {"error": str(e)}
    
    def backup_system(self, backup_path: Optional[str] = None) -> bool:
        """Reject the removed database-only backup API.

        Canonical nodes require the SQLite database *and* their exact binary
        sidecar closure. A standalone database file is not restorable and must
        never be reported as a successful system backup.
        """
        del backup_path
        raise MemoryIntegrityError(
            "USMS database-only backup is unsafe and unsupported; use "
            "MemoryArchiveService.create_backup() for a verified sidecar-aware bundle"
        )
    
    # Public API Methods
    
    def anchor_node(
        self,
        node_id: str,
        score: float,
        anchor_type: str = "belief",
        requester: Optional[SovereignIdentity] = None,
    ) -> bool:
        """Anchor an owned node after sovereign proof-of-possession."""
        try:
            if not isinstance(node_id, str) or not node_id:
                raise MemoryIntegrityError("Anchor node_id must be non-empty text")
            if not isinstance(score, (int, float)) or isinstance(score, bool):
                raise MemoryIntegrityError("Anchor score must be numeric")
            normalized_score = float(score)
            if not math.isfinite(normalized_score) or not 0.0 <= normalized_score <= 1.0:
                raise MemoryIntegrityError(
                    "Anchor score must be finite and between 0 and 1"
                )
            if not isinstance(anchor_type, str) or not anchor_type.strip():
                raise MemoryIntegrityError("Anchor type must be non-empty text")
            with self.main_lock:
                requester_id, _, _ = self._require_registered_identity(requester)
                node = self._load_node(node_id)
                if node is None:
                    raise MemoryIntegrityError(
                        f"Cannot anchor nonexistent node {node_id[:12]}"
                    )
                self._require_node_access(node, requester)
                if node.author_id != requester_id:
                    raise MemoryAccessError(
                        "Only the canonical node author may request a manual anchor"
                    )
                with self.circuit_breakers['database'].protected_call():
                    with self.process_coordinator.database_lock("anchor_node"):
                        self._anchor_node(node_id, normalized_score, anchor_type)
                return True
        except UnifiedMemoryError:
            raise
        except (sqlite3.Error, TypeError, ValueError) as e:
            logger.error(f"Failed to anchor node {node_id[:12]}: {e}")
            raise MemoryIntegrityError(f"Manual anchoring failed: {e}") from e
    
    def perform_epistemic_weaving(self, node_id: str, requester: SovereignIdentity, max_depth: int = 5) -> Dict[str, Any]:
        """Public API for epistemic weaving operations."""
        try:
            with self.circuit_breakers['weaving'].protected_call():
                return self._perform_epistemic_weaving(node_id, requester, max_depth)
        except Exception as e:
            logger.error(f"Epistemic weaving failed for node {node_id[:12]}: {e}")
            return {"error": str(e), "weaving_depth": 0, "connections": []}
    
    def _perform_epistemic_weaving(self, node_id: str, requester: SovereignIdentity, max_depth: int = 5) -> Dict[str, Any]:
        """Internal implementation of epistemic weaving."""
        try:
            # Basic implementation - in full system this would be more complex
            node = self.retrieve_memory_node(node_id, requester)
            if not node:
                return {"error": "Node not found", "weaving_depth": 0, "connections": []}
            
            connections = []
            visited = set()
            queue = [(node_id, 0)]
            
            while queue and len(connections) < max_depth * 10:
                current_id, depth = queue.pop(0)
                
                if current_id in visited or depth >= max_depth:
                    continue
                
                visited.add(current_id)
                current_node = self.retrieve_memory_node(current_id, requester)
                
                if current_node:
                    # Add parent connections
                    for parent_id in current_node.parents:
                        if parent_id not in visited:
                            connections.append({
                                "source": current_id,
                                "target": parent_id,
                                "type": "temporal_parent",
                                "depth": depth + 1
                            })
                            queue.append((parent_id, depth + 1))
                    
                    # Add linkage connections
                    for link_type, targets in current_node.linkage_manifest.items():
                        for target_id in targets:
                            if target_id not in visited:
                                connections.append({
                                    "source": current_id,
                                    "target": target_id,
                                    "type": link_type.value,
                                    "depth": depth + 1
                                })
                                queue.append((target_id, depth + 1))
            
            return {
                "weaving_depth": max_depth,
                "connections": connections,
                "visited_nodes": len(visited),
                "total_connections": len(connections)
            }
            
        except Exception as e:
            logger.error(f"Epistemic weaving internal error: {e}")
            return {"error": str(e), "weaving_depth": 0, "connections": []}
    
    def shutdown(self):
        """Gracefully shutdown the system."""
        try:
            logger.info("Shutting down Unified Sovereign Memory System")
            
            # Signal background threads to stop
            self._shutdown_event.set()
            
            # Wait for background threads to complete
            shutdown_timeout = 30  # 30 seconds timeout
            for thread in self._background_threads:
                try:
                    thread.join(timeout=shutdown_timeout / len(self._background_threads))
                    if thread.is_alive():
                        logger.warning(f"Background thread {thread.name} did not shutdown gracefully")
                    else:
                        logger.debug(f"Background thread {thread.name} shutdown completed")
                except Exception as e:
                    logger.error(f"Error shutting down thread {thread.name}: {e}")
            
            # The production archive service owns complete sidecar-aware backups.
            if self.internal_backups_enabled:
                try:
                    self.backup_system()
                    logger.debug("Final backup completed")
                except Exception as e:
                    logger.error(f"Failed to create final backup: {e}")
            
            # Clean up process coordination
            try:
                if hasattr(self, '_process_marker') and hasattr(self, 'process_coordinator'):
                    self.process_coordinator.cleanup_process_marker(self._process_marker)
                    logger.debug("Process marker cleaned up")
            except Exception as e:
                logger.error(f"Failed to cleanup process marker: {e}")
            
            # Log shutdown
            try:
                self._log_system_event("system_shutdown", None, {
                    "uptime": time.time() - getattr(self, '_start_time', time.time()),
                    "total_operations": sum(self.operation_counts.values()),
                    "background_threads_count": len(self._background_threads)
                })
            except Exception as e:
                logger.error(f"Failed to log shutdown event: {e}")
            
            logger.info("Unified Sovereign Memory System shutdown complete")
            owned_log = (self.paths.log_dir / "unified_sovereign_memory.log").resolve()
            for handler in list(logger.handlers):
                if not isinstance(handler, logging.FileHandler):
                    continue
                if Path(handler.baseFilename).resolve() != owned_log:
                    continue
                handler.flush()
                handler.close()
                logger.removeHandler(handler)
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

# Demonstration and testing
if __name__ == "__main__":
    print("=== Unified Sovereign Memory System Demonstration ===")
    
    # Initialize the system
    print("\n1. Initializing Unified Memory System...")
    memory_system = UnifiedMemorySystem()
    
    # Create test sovereigns
    print("\n2. Creating Sovereign Identities...")
    alice = SovereignIdentity("Alice", "", "", time.time())
    bob = SovereignIdentity("Bob", "", "", time.time())
    
    memory_system.register_sovereign(alice)
    memory_system.register_sovereign(bob)
    print(f"   - Alice: {alice.agent_id[:12]}...")
    print(f"   - Bob: {bob.agent_id[:12]}...")
    
    # Create initial memory nodes
    print("\n3. Creating Memory Nodes...")
    
    # Alice creates an observation
    observation = memory_system.create_memory_node(
        author=alice,
        kind=NodeKindEnum.EVENT,
        content={
            "summary": "Observed anomalous network traffic",
            "details": "Detected unusual packet patterns on port 443",
            "polarity": 0,
            "confidence": 0.85
        },
        semantic_context="network security observation traffic anomaly"
    )
    print(f"   - Alice created observation: {observation.node_id[:12]}...")
    
    # Bob creates a belief about the observation
    belief = memory_system.create_memory_node(
        author=bob,
        kind=NodeKindEnum.BELIEF,
        content={
            "summary": "Network traffic indicates potential threat",
            "claim": "The observed traffic pattern suggests a coordinated attack",
            "details": "Pattern matches known APT signatures",
            "polarity": -1,  # Negative (threat)
            "confidence": 0.75
        },
        linkage_manifest={
            LinkageTypeEnum.CAUSAL_PARENT: [observation.node_id]
        },
        semantic_context="security threat assessment belief"
    )
    print(f"   - Bob created threat belief: {belief.node_id[:12]}...")
    
    # Alice creates a contradictory belief
    counter_belief = memory_system.create_memory_node(
        author=alice,
        kind=NodeKindEnum.BELIEF,
        content={
            "summary": "Network traffic appears benign",
            "claim": "The traffic pattern is likely legitimate user behavior",
            "details": "Timing aligns with scheduled backup operations",
            "polarity": 1,  # Positive (benign)
            "confidence": 0.80
        },
        linkage_manifest={
            LinkageTypeEnum.CAUSAL_PARENT: [observation.node_id],
            LinkageTypeEnum.CONTRADICTION: [belief.node_id]
        },
        semantic_context="security benign assessment belief"
    )
    print(f"   - Alice created counter-belief: {counter_belief.node_id[:12]}...")
    
    # Test belief attestation
    print("\n4. Testing Belief Attestation...")
    alice_attests = memory_system.attest_belief(belief.node_id, alice, 0.3, "Skeptical due to timing analysis")
    bob_attests = memory_system.attest_belief(belief.node_id, bob, 0.9, "High confidence in threat assessment")
    print(f"   - Alice attested belief: {alice_attests}")
    print(f"   - Bob attested belief: {bob_attests}")
    
    # Test quantum entanglement
    print("\n5. Testing Quantum Entanglement...")
    if memory_system.enable_quantum_features:
        entanglement_id = memory_system.quantum_entangle_nodes(
            [observation.node_id, belief.node_id, counter_belief.node_id],
            alice
        )
        print(f"   - Created quantum entanglement: {entanglement_id[:12] if entanglement_id else 'Failed'}...")
    
    # Test epistemic linking
    print("\n6. Testing Epistemic Linking...")
    link_success = memory_system.create_epistemic_link(
        belief.node_id,
        counter_belief.node_id,
        LinkageTypeEnum.CONTRADICTION,
        strength=0.8,
        creator=bob
    )
    print(f"   - Created epistemic link: {link_success}")
    
    # Test auto-repair
    print("\n7. Testing Auto-Repair...")
    repair_nodes = memory_system.auto_repair_contradictions()
    print(f"   - Auto-repair created {len(repair_nodes)} repair nodes")
    
    # Test queries
    print("\n8. Testing Queries...")
    
    # Search by content
    search_results = memory_system.search_nodes_by_content(
        "network traffic security",
        requester=alice,
    )
    print(f"   - Content search returned {len(search_results)} results")
    
    # Get lineage
    lineage = memory_system.get_node_lineage(
        counter_belief.node_id,
        LinkageTypeEnum.CAUSAL_PARENT,
        requester=alice,
    )
    print(f"   - Causal lineage has {len(lineage)} nodes")
    
    # Get timeline
    alice_timeline = memory_system.get_sovereign_timeline(
        alice.agent_id,
        requester=alice,
    )
    print(f"   - Alice's timeline has {len(alice_timeline)} nodes")
    
    # System statistics
    print("\n9. System Statistics:")
    stats = memory_system.get_system_statistics()
    for key, value in stats.items():
        if isinstance(value, dict):
            print(f"   - {key}:")
            for sub_key, sub_value in value.items():
                print(f"     * {sub_key}: {sub_value}")
        else:
            print(f"   - {key}: {value}")
    
    # Shutdown
    print("\n10. Shutting Down System...")
    memory_system.shutdown()
    
    print("\n=== Unified Sovereign Memory System Demonstration Complete ===")
    print("\nKey Features Demonstrated:")
    print("- Multi-dimensional memory nodes combining MTL, NMCA, and SCL features")
    print("- Belief anchoring and attestation system")
    print("- Quantum-inspired entanglement operations")  
    print("- Epistemic weaving and linkage creation")
    print("- Automatic contradiction detection and repair")
    print("- Thread-safe operations with circuit breakers")
    print("- Comprehensive querying and analysis")
    print("- Enterprise-grade logging and audit trails")
    print("- Graceful system lifecycle management")
