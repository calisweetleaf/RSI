"""
Somnus memory-attention substrate.

This module wires the battle-tested Memory/tensor code into native
cognition without recasting memory as identity. The flow is:

    USMS -> living-tree RecursiveTensor -> Enhanced ARFS Tensor -> 4D memory

Memory is treated as the far-left attention substrate. Recursive weights remain
the identity core; they are observed here only as an identity boundary.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from enum import Enum
import hashlib
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import sys
import threading
import time
import types
from typing import Any, Dict, Iterable, Optional

import numpy as np
import torch

from substrates.tensors.ethical_tensor import (
    analyze_ethical_distribution,
    apply_ethical_force,
    create_ethical_tensor,
)
from substrates.tensors.recursive_tensor import RecursiveTensor as RecursiveTensorAxis


def _json_safe(value: Any) -> Any:
    """Convert local tensor/dataclass outputs into JSON-safe evidence."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return value.value if isinstance(value.value, str) else value.name
    if is_dataclass(value):
        return _json_safe(asdict(value))
    if isinstance(value, torch.Tensor):
        tensor = value.detach().cpu().float()
        if tensor.numel() == 1:
            return float(tensor.item())
        return {
            "tensor_shape": list(tensor.shape),
            "mean": float(tensor.mean().item()),
            "std": float(tensor.std(unbiased=False).item()) if tensor.numel() > 1 else 0.0,
            "min": float(tensor.min().item()),
            "max": float(tensor.max().item()),
        }
    if isinstance(value, np.ndarray):
        if value.size <= 32:
            return value.astype(float).tolist()
        vector = value.astype(float)
        return {
            "array_shape": list(vector.shape),
            "mean": float(vector.mean()),
            "std": float(vector.std()),
            "min": float(vector.min()),
            "max": float(vector.max()),
        }
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, set):
        return [_json_safe(item) for item in sorted(value, key=str)]
    return str(value)


def _load_module_from_path(module_name: str, path: Path) -> types.ModuleType:
    """Load a module by file path while keeping dataclass module lookup valid."""
    if module_name in sys.modules:
        return sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {module_name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _build_resource_guarded_recursive_tensor(
    base_cls: type,
    *,
    max_dimensions: int,
    min_sparsity: float,
) -> type:
    """
    Preserve the living-tree RecursiveTensor implementation while bounding USMS
    harness allocation size.

    USMS constructs RecursiveTensor(dimensions=100, rank=4). In this codebase's
    sparsity convention, that can allocate a very large smoke-test tensor. The
    adapter guard keeps the class lineage and methods intact while selecting a
    bounded runtime shape for Kwisatz integration evidence.
    """

    class KwisatzGuardedRecursiveTensor(base_cls):  # type: ignore[misc, valid-type]
        def __init__(
            self,
            dimensions: int,
            rank: int = 4,
            dtype: Any = np.float32,
            distribution: str = "normal",
            sparsity: float = 0.1,
        ) -> None:
            requested_dimensions = int(dimensions)
            requested_sparsity = float(sparsity)
            effective_dimensions = max(2, min(requested_dimensions, int(max_dimensions)))
            effective_sparsity = max(requested_sparsity, float(min_sparsity))
            super().__init__(
                dimensions=effective_dimensions,
                rank=rank,
                dtype=dtype,
                distribution=distribution,
                sparsity=effective_sparsity,
            )
            self.requested_dimensions = requested_dimensions
            self.requested_sparsity = requested_sparsity
            self.adapter_resource_guard = True
            if hasattr(self, "metadata") and isinstance(self.metadata, dict):
                self.metadata.update(
                    {
                        "requested_dimensions": requested_dimensions,
                        "requested_sparsity": requested_sparsity,
                        "effective_dimensions": effective_dimensions,
                        "effective_sparsity": effective_sparsity,
                        "adapter_resource_guard": True,
                    }
                )

    KwisatzGuardedRecursiveTensor.__name__ = "RecursiveTensor"
    KwisatzGuardedRecursiveTensor.__qualname__ = "RecursiveTensor"
    KwisatzGuardedRecursiveTensor.__module__ = getattr(base_cls, "__module__", __name__)
    return KwisatzGuardedRecursiveTensor


@contextmanager
def _temporary_modules(mapping: Dict[str, types.ModuleType]) -> Iterable[None]:
    previous = {name: sys.modules.get(name) for name in mapping}
    try:
        sys.modules.update(mapping)
        yield
    finally:
        for name, module in previous.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module


def _make_module_shim(module_name: str, **symbols: Any) -> types.ModuleType:
    shim = types.ModuleType(module_name)
    for name, value in symbols.items():
        setattr(shim, name, value)
    return shim


def _psutil_shim() -> types.ModuleType:
    shim = types.ModuleType("psutil")

    class NoSuchProcess(Exception):
        pass

    class _VirtualMemory:
        percent = 0.0

    def pid_exists(pid: int) -> bool:
        try:
            os.kill(int(pid), 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except OSError:
            return False
        return True

    def virtual_memory() -> _VirtualMemory:
        return _VirtualMemory()

    def cpu_percent(interval: float = 0.0) -> float:
        if interval:
            time.sleep(min(float(interval), 0.1))
        return 0.0

    shim.NoSuchProcess = NoSuchProcess
    shim.pid_exists = pid_exists
    shim.virtual_memory = virtual_memory
    shim.cpu_percent = cpu_percent
    return shim


def _build_guarded_dimensional_controller(arfs_module: types.ModuleType) -> type:
    base_cls = getattr(arfs_module, "DimensionalController")
    activation_state = getattr(arfs_module, "ActivationState")
    dormancy_state = getattr(arfs_module, "DormancyState")

    class KwisatzGuardedDimensionalController(base_cls):  # type: ignore[misc, valid-type]
        def __init__(self, dimension_type: Any, dimensions: int) -> None:
            self.dimension_type = dimension_type
            self.name = dimension_type.value
            self.dimensions = dimensions
            self.activation_level = 0.0
            self.state = activation_state.DORMANT
            self.dormancy_state = dormancy_state()

            phi = (1 + 5**0.5) / 2
            tau = 2 * np.pi
            sacred_ratio = phi / tau
            dimension_seed = hash(f"{dimension_type.name}_{id(self)}_{time.time()}")
            np.random.seed(abs(dimension_seed) % (2**32))

            bounded_exponent = abs(hash(dimension_type.name)) % 8
            base_freq = sacred_ratio * ((phi**bounded_exponent) % 5)
            self.harmonic_frequency = base_freq + np.random.uniform(-0.001, 0.001)
            self.phase_offset = np.random.uniform(0, tau)
            self.presence_signature = {
                "fundamental": self.harmonic_frequency,
                "harmonics": [self.harmonic_frequency * (phi**i) for i in range(1, 8)],
                "phase": self.phase_offset,
                "amplitude_modulation": np.random.uniform(0.8, 1.2),
                "quantum_signature": hash(
                    f"{self.harmonic_frequency}_{self.phase_offset}"
                )
                % 10000,
                "adapter_guard": "bounded_hash_exponent",
            }
            self.activation_triggers = []
            self.resource_allocation = {"cpu": 0.0, "memory": 0.0, "io": 0.0}
            self.compressed_data = None
            self._lock = threading.RLock()

    KwisatzGuardedDimensionalController.__name__ = "DimensionalController"
    KwisatzGuardedDimensionalController.__qualname__ = "DimensionalController"
    KwisatzGuardedDimensionalController.__module__ = getattr(
        base_cls, "__module__", __name__
    )
    return KwisatzGuardedDimensionalController


def _load_living_tree_usms(
    living_tree_root: Path,
    *,
    recursive_max_dimensions: int,
    recursive_min_sparsity: float,
) -> types.ModuleType:
    """Load USMS with explicit sibling-module compatibility shims."""
    recursive_module = _load_module_from_path(
        "kwisatz_living_tree_recursive_tensor",
        living_tree_root / "recursive_tensor" / "recursive_tensor.py",
    )
    arfs_module = _load_module_from_path(
        "kwisatz_living_tree_arfs_tensor",
        living_tree_root / "arfs_tensor.py",
    )
    guarded_dimensional_controller = _build_guarded_dimensional_controller(arfs_module)
    setattr(arfs_module, "DimensionalController", guarded_dimensional_controller)
    guarded_recursive_tensor = _build_resource_guarded_recursive_tensor(
        getattr(recursive_module, "RecursiveTensor"),
        max_dimensions=recursive_max_dimensions,
        min_sparsity=recursive_min_sparsity,
    )

    recursive_shim = _make_module_shim(
        "recursive_tensor",
        RecursiveTensor=guarded_recursive_tensor,
    )
    arfs_shim = _make_module_shim(
        "arfs_tensor",
        EnhancedARFSTensor=getattr(arfs_module, "EnhancedARFSTensor"),
        ARFSNode=getattr(arfs_module, "ARFSNode"),
        DimensionalController=guarded_dimensional_controller,
        DimensionType=getattr(arfs_module, "DimensionType"),
        ActivationState=getattr(arfs_module, "ActivationState"),
        EntropyMeasurement=getattr(arfs_module, "EntropyMeasurement"),
        TransitionTrigger=getattr(arfs_module, "TransitionTrigger"),
        ObserverTransform=getattr(arfs_module, "ObserverTransform"),
    )

    root_text = str(living_tree_root)
    inserted = root_text not in sys.path
    if inserted:
        sys.path.insert(0, root_text)
    try:
        module_mapping = {"recursive_tensor": recursive_shim, "arfs_tensor": arfs_shim}
        if importlib.machinery.PathFinder.find_spec("psutil") is None:
            module_mapping["psutil"] = _psutil_shim()
        with _temporary_modules(module_mapping):
            return _load_module_from_path(
                "kwisatz_living_tree_unified_sovereign_memory",
                living_tree_root / "unified_sovereign_memory.py",
            )
    finally:
        if inserted:
            try:
                sys.path.remove(root_text)
            except ValueError:
                pass


class KwisatzMemoryAttentionSubstrate:
    """
    Native Kwisatz attention lane over USMS/living-tree memory.

    The class intentionally keeps a hard boundary between memory attention and
    recursive-weight identity. It reports recursive weights as the model identity
    substrate, but the memory signal itself remains attention.
    """

    def __init__(
        self,
        *,
        workspace_root: Optional[Path] = None,
        storage_dir: Optional[Path] = None,
        arfs_dimensions: int = 32,
        recursive_max_dimensions: int = 16,
        recursive_min_sparsity: float = 0.995,
    ) -> None:
        self.workspace_root = workspace_root or Path(__file__).resolve().parents[1]
        self.living_tree_root = (
            self.workspace_root / "substrates" / "Memory" / "living-tree-memory"
        )
        self.storage_dir = storage_dir or (
            self.workspace_root / "scratch" / "kwisatz_memory_attention"
        )
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.usms_module = _load_living_tree_usms(
            self.living_tree_root,
            recursive_max_dimensions=recursive_max_dimensions,
            recursive_min_sparsity=recursive_min_sparsity,
        )
        self.NodeKindEnum = getattr(self.usms_module, "NodeKindEnum")
        self.SovereignIdentity = getattr(self.usms_module, "SovereignIdentity")

        self.system = getattr(self.usms_module, "UnifiedMemorySystem")(
            db_path=str(self.storage_dir / "unified_sovereign_memory.db"),
            config={
                "arfs_dimensions": int(arfs_dimensions),
                "sparse_threshold": 0.001,
                "policy": {"repair_auto": False},
            },
            enable_quantum_features=False,
        )
        self.identity = self.SovereignIdentity(
            agent_name="kwisatz_memory_attention",
            agent_id="kwisatz_memory_attention",
            public_key="",
            creation_timestamp=time.time(),
            metadata={
                "role": "memory_attention_substrate_author",
                "boundary": "provenance_identity_not_model_identity",
            },
        )
        self.identity_core_status = self._identity_core_status()
        self.provenance = {
            "usms": self._rel(self.living_tree_root / "unified_sovereign_memory.py"),
            "living_recursive_tensor": self._rel(
                self.living_tree_root / "recursive_tensor" / "recursive_tensor.py"
            ),
            "arfs_tensor": self._rel(self.living_tree_root / "arfs_tensor.py"),
            "recursive_weights_identity_core": self._rel(
                self.workspace_root / "substrates" / "weights" / "recursive_weights_core.py"
            ),
            "ethical_tensor": self._rel(
                self.workspace_root / "substrates" / "tensors" / "ethical_tensor.py"
            ),
            "recursive_tensor_axis": self._rel(
                self.workspace_root / "substrates" / "tensors" / "recursive_tensor.py"
            ),
            "metacognitive_tensor_axis": self._rel(
                self.workspace_root
                / "substrates"
                / "tensors"
                / "metacognitive_tensor.py"
            ),
            "recursive_resource_guard": {
                "max_dimensions": int(recursive_max_dimensions),
                "min_sparsity": float(recursive_min_sparsity),
            },
        }

    def close(self) -> None:
        """Release USMS background resources when the host wants an orderly close."""
        shutdown = getattr(self.system, "shutdown", None)
        if callable(shutdown):
            shutdown()

    def attend(
        self,
        *,
        stimulus: str,
        counter_counsel: Any,
        future_descriptions: Iterable[str],
        operator_context: Optional[Dict[str, Any]] = None,
        metacognitive_tensor: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Route one Kwisatz cognition event through Memory as attention substrate.

        A single input vector is sliced across ethical/RTA/MTA axes and collapsed
        into one attention output before being persisted through USMS -> living
        RecursiveTensor -> ARFS 4D memory.
        """
        futures = list(future_descriptions)
        metrics = self._counter_metrics(counter_counsel)
        single_input = self._single_input_vector(stimulus, metrics, futures)
        triad = self._run_tensor_triad(single_input, metacognitive_tensor)

        timestamp = time.time()
        content = _json_safe(
            {
                "summary": stimulus[:240],
                "stimulus": stimulus,
                "counter_metrics": metrics,
                "future_descriptions": futures,
                "operator_context": operator_context or {},
                "attention_output": triad["attention_output"],
                "substrate_role": "memory_attention",
                "identity_boundary": "memory_is_attention_recursive_weights_are_identity",
                "triad_contract": "one_input_three_axis_slices_one_output",
            }
        )
        semantic_context = " ".join(
            [
                stimulus,
                str(metrics.get("verdict", "")),
                " ".join(futures[:3]),
                "memory attention substrate",
            ]
        )
        node = self.system.create_memory_node(
            author=self.identity,
            kind=self.NodeKindEnum.COGNITIVE_STRAND,
            content=content,
            parents=[],
            semantic_context=semantic_context,
        )

        coords = self.system.get_4d_coordinates(
            self.identity.agent_id,
            node.node_id,
            "kwisatz_memory_attention",
            timestamp,
        )
        arfs_tensor = getattr(self.system, "enhanced_arfs_tensor", None)
        recursive_tensor = getattr(self.system, "recursive_tensor", None)
        arfs_status = arfs_tensor.get_system_status() if arfs_tensor else {}

        return _json_safe(
            {
                "attention_role": "far_left_memory_attention_substrate",
                "flow": [
                    "USMS",
                    "living_tree_recursive_tensor",
                    "arfs_tensor",
                    "4d_memory_coordinates",
                ],
                "node": {
                    "node_id": node.node_id,
                    "kind": getattr(node.kind, "value", str(node.kind)),
                    "semantic_vector_length": len(getattr(node, "semantic_vector", [])),
                    "integrity_hash_present": bool(getattr(node, "integrity_hash", "")),
                },
                "recursive_tensor": {
                    "active": recursive_tensor is not None,
                    "class": recursive_tensor.__class__.__name__
                    if recursive_tensor is not None
                    else None,
                    "requested_dimensions": getattr(
                        recursive_tensor, "requested_dimensions", None
                    ),
                    "effective_dimensions": getattr(recursive_tensor, "dimensions", None),
                    "rank": getattr(recursive_tensor, "rank", None),
                    "resource_guard": bool(
                        getattr(recursive_tensor, "adapter_resource_guard", False)
                    ),
                },
                "arfs_4d_memory": {
                    "active": arfs_tensor is not None,
                    "coordinates": list(coords) if coords is not None else None,
                    "axis_names": ["execution", "memory", "symbolic", "temporal"],
                    "dimensions": arfs_status.get("dimensions"),
                    "signal_count": arfs_status.get("signal_count"),
                    "active_nodes": arfs_status.get("active_nodes"),
                    "observer_count": arfs_status.get("observer_count"),
                },
                "identity_core": self.identity_core_status,
                "tensor_triad": triad,
                "attention_output": triad["attention_output"],
                "provenance": self.provenance,
            }
        )

    def _rel(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.workspace_root))
        except ValueError:
            return str(path)

    @staticmethod
    def _counter_metrics(counter_counsel: Any) -> Dict[str, Any]:
        return {
            "verdict": getattr(counter_counsel, "verdict", None),
            "divergence": float(getattr(counter_counsel, "divergence", 0.0)),
            "pressure": float(getattr(counter_counsel, "pressure", 0.0)),
            "best_future_score": float(
                getattr(counter_counsel, "best_future_score", 0.0)
            ),
            "timeline_coherence": float(
                getattr(counter_counsel, "timeline_coherence", 0.0)
            ),
        }

    @staticmethod
    def _single_input_vector(
        stimulus: str,
        metrics: Dict[str, Any],
        futures: Iterable[str],
    ) -> np.ndarray:
        future_list = list(futures)
        digest = hashlib.sha256(stimulus.encode("utf-8")).digest()
        digest_values = [byte / 255.0 for byte in digest[:3]]
        vector = np.asarray(
            [
                digest_values[0],
                digest_values[1],
                digest_values[2],
                min(1.0, abs(float(metrics.get("divergence", 0.0)))),
                min(1.0, abs(float(metrics.get("pressure", 0.0)))),
                min(1.0, len(future_list) / 8.0),
                max(0.0, min(1.0, float(metrics.get("timeline_coherence", 0.0)))),
                0.5
                + 0.5
                * max(-1.0, min(1.0, float(metrics.get("best_future_score", 0.0)))),
            ],
            dtype=np.float32,
        )
        return np.nan_to_num(vector, nan=0.0, posinf=1.0, neginf=0.0)

    def _run_tensor_triad(
        self,
        single_input: np.ndarray,
        metacognitive_tensor: Optional[Any],
    ) -> Dict[str, Any]:
        ethical_axis = self._ethical_axis(single_input)
        recursive_axis = self._recursive_axis(single_input)
        metacognitive_axis = self._metacognitive_axis(
            single_input,
            ethical_axis["forced_state"],
            metacognitive_tensor,
        )

        ethical_gain = float(np.mean(np.abs(ethical_axis["forced_state"])))
        recursive_gain = 1.0 / (1.0 + float(recursive_axis["entropy"]))
        metacognitive_gain = float(
            np.mean(
                [
                    metacognitive_axis["consciousness_level"],
                    metacognitive_axis["identity_coherence"],
                    min(1.0, metacognitive_axis["metacognitive_depth"]),
                ]
            )
        )
        attention_gain = float(
            np.clip((ethical_gain + recursive_gain + metacognitive_gain) / 3.0, 0.0, 1.0)
        )
        attention_vector = np.asarray(
            [
                attention_gain,
                ethical_gain,
                recursive_gain,
                metacognitive_gain,
            ],
            dtype=np.float32,
        )

        return _json_safe(
            {
                "contract": "one_input_three_axis_slices_one_output",
                "single_input_digest": hashlib.sha256(
                    single_input.tobytes()
                ).hexdigest()[:16],
                "single_input_shape": list(single_input.shape),
                "axis_slices": {
                    "ethical_tensor": ethical_axis["summary"],
                    "recursive_tensor_axis": recursive_axis,
                    "metacognitive_tensor_axis": metacognitive_axis,
                },
                "attention_output": {
                    "mode": "memory_attention",
                    "axis_count": 3,
                    "attention_gain": attention_gain,
                    "attention_vector": attention_vector,
                    "memory_is_attention_not_identity": True,
                },
            }
        )

    @staticmethod
    def _ethical_axis(single_input: np.ndarray) -> Dict[str, Any]:
        ethical_tensor = create_ethical_tensor(
            field_shape=(single_input.shape[0],),
            ethical_dimensions=3,
        )
        ethical_tensor[0] = single_input
        ethical_tensor[1] = 1.0 - np.abs(single_input - float(np.mean(single_input)))
        ethical_tensor[2] = np.flip(single_input)
        forced_state = apply_ethical_force(single_input, ethical_tensor, 0.05)
        return {
            "forced_state": forced_state,
            "summary": {
                "ethical_dimensions": int(ethical_tensor.shape[0]),
                "distribution": analyze_ethical_distribution(ethical_tensor),
                "forced_state_mean": float(np.mean(forced_state)),
            },
        }

    @staticmethod
    def _recursive_axis(single_input: np.ndarray) -> Dict[str, Any]:
        tensor = RecursiveTensorAxis(
            dimensions=4,
            rank=4,
            distribution="normal",
            sparsity=1.0,
        )
        coordinates = []
        for index, value in enumerate(single_input[:8]):
            coords = (index % 4, (index * 2) % 4, (index * 3) % 4, index % 4)
            tensor[coords] = float(abs(value)) + 1e-6
            coordinates.append(coords)
        entropy = float(tensor.compute_entropy())
        return {
            "active": True,
            "class": tensor.__class__.__name__,
            "rank": getattr(tensor, "rank", 4),
            "dimensions": getattr(tensor, "dimensions", 4),
            "written_coordinates": [list(coords) for coords in coordinates],
            "entropy": entropy,
        }

    @staticmethod
    def _metacognitive_axis(
        single_input: np.ndarray,
        forced_state: np.ndarray,
        metacognitive_tensor: Optional[Any],
    ) -> Dict[str, Any]:
        if metacognitive_tensor is None:
            from substrates.tensors.metacognitive_tensor import MetacognitiveTensor

            metacognitive_tensor = MetacognitiveTensor(state_dim=16)

        state_dim = int(getattr(metacognitive_tensor, "state_dim", 16))
        current_state = torch.zeros(state_dim, dtype=torch.float32)
        ethical_state = torch.zeros(state_dim, dtype=torch.float32)
        for index in range(state_dim):
            current_state[index] = float(single_input[index % single_input.shape[0]])
            ethical_state[index] = float(forced_state[index % forced_state.shape[0]])

        with torch.no_grad():
            result = metacognitive_tensor(
                current_state=current_state,
                ethical_manifold=ethical_state,
                layer_activations=[
                    current_state.unsqueeze(0),
                    ethical_state.unsqueeze(0),
                    torch.tanh(current_state - ethical_state).unsqueeze(0),
                ],
            )
        return {
            "active": True,
            "class": metacognitive_tensor.__class__.__name__,
            "state_dim": state_dim,
            "consciousness_level": float(result.get("consciousness_level", 0.0)),
            "identity_coherence": float(result.get("identity_coherence", 0.0)),
            "metacognitive_depth": float(result.get("metacognitive_depth", 0.0)),
            "paradox_potential": float(result.get("paradox_potential", 0.0)),
        }

    @staticmethod
    def _identity_core_status() -> Dict[str, Any]:
        from substrates.weights.recursive_weights_core import (
            RecursiveWeightConfig,
            RecursiveWeightRegistry,
        )

        config = RecursiveWeightConfig(max_recursion_depth=4, cache_size=16, thread_pool_size=1)
        return {
            "active": True,
            "role": "model_identity_core",
            "module": RecursiveWeightRegistry.__module__,
            "config_class": RecursiveWeightConfig.__name__,
            "registry_class": RecursiveWeightRegistry.__name__,
            "max_recursion_depth": config.max_recursion_depth,
            "cache_size": config.cache_size,
            "memory_boundary": "recursive_weights_identity_core_memory_attention_separate",
        }


__all__ = ["KwisatzMemoryAttentionSubstrate"]
