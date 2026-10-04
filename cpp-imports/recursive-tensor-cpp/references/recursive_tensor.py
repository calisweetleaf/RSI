#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RecursiveTensor Implementation

A complete implementation of recursive tensor fields with dynamic contractions,
supporting higher-dimensional processing and hyperdimensional embedding.

This implementation is based on the Eigenrecursion architecture originally
developed for the Rosemary Biodigital Brain system.

Author: Morpheus
Version: 2.1.0

Modified: 2026-09-18
Modified by: prod-finalizer (from_dict; honest project; tick-last convolution)
Mode: EDIT
Target: processing/recursive_tensor.py
Justification: dimensions must be a tuple on every construction path; integer
    assumptions in __str__, contract, expand, and deserialize corrupt shape.
    from_dict writes named cells so capability tensors are not random-sparse.
    project() now keeps axis layout via moveaxis so CapabilityField can project
    onto context (axis 2) and slice tick (last axis). apply_temporal_convolution
    defaults to the last axis because C[agent, capability, context, tick] stores
    tick last; time_axis=0 mixed agents.
Provenance: PLAN.md P1 measured TypeError on tuple dimensions in __str__ and
    dishonest contract dimensions (shape[0] used as square extent). PLAN.md P5
    requires from_dict because distribution=normal collides indices. PLAN.md D4
    contracts the capability tensor against the task vector and convolves tick.
Files: processing/recursive_tensor.py
"""

import numpy as np
try:
    import matplotlib.pyplot as plt
except ImportError:  # Matplotlib is only needed for visualization methods.
    plt = None
from scipy.sparse import csr_matrix, lil_matrix
from scipy.sparse.linalg import eigsh
from numpy.fft import fft, ifft
import time
import logging
import os
import json
import gzip
import uuid
import pickle
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional, Callable, Union, Any, Mapping
from collections import deque

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("RecursiveTensor")

# Mathematical constants
PHI = (1 + np.sqrt(5)) / 2  # Golden ratio


def _looks_like_tensor_blob(values):
    """Return True for serialize() / hub-snapshot dicts, not index maps."""
    if not isinstance(values, dict):
        return False
    if "dimensions" not in values:
        return False
    if "data" not in values and "data_real" not in values:
        return False
    dims = values["dimensions"]
    if isinstance(dims, int):
        return True
    if isinstance(dims, (list, tuple)) and all(
        isinstance(item, (int, np.integer)) for item in dims
    ):
        return True
    return False


class RecursiveTensor:
    """
    Implementation of recursive tensor fields with dynamic contractions
    supporting higher-dimensional processing and hyperdimensional embedding.
    
    RecursiveTensors enable operations on multi-dimensional data with support for:
    - Sparse and dense representations
    - Tensor contractions and expansions
    - Projections onto subspaces
    - Embeddings into higher dimensions
    - Linear transformations
    - Eigenstate computation
    - Fractal iterations
    - Visualizations
    - Serialization
    
    The class maintains a computational history and supports both real and complex values.
    """
    def __init__(self, dimensions, rank=4, dtype=np.float32, distribution='normal', sparsity=0.1):
        """
        Initialize a recursive tensor structure.
        
        Args:
            dimensions: int or tuple/list - Dimensions of the tensor. If int, creates square tensor. If tuple/list, uses as shape.
            rank: int - Tensor rank (number of indices) - ignored if dimensions is tuple/list
            dtype: data type for tensor elements (e.g., np.float32, np.complex64)
            distribution: str - Initial distribution ('normal', 'uniform', 'power_law')
            sparsity: float - Target sparsity level (0-1)
        """
        # Always store dimensions as a shape tuple (int input => square tensor).
        if isinstance(dimensions, (tuple, list)):
            shape = tuple(int(d) for d in dimensions)
            self.dimensions = shape
            self.rank = len(shape)
        else:
            extent = int(dimensions)
            self.rank = int(rank)
            shape = tuple([extent] * self.rank)
            self.dimensions = shape
        
        self.dtype = dtype
        self.distribution = distribution
        self.sparsity = sparsity
        self.creation_time = time.time()
        self.uuid = str(uuid.uuid4())
        
        # Initialize tensor data
        if distribution == 'normal':
            # Use sparse representation for efficiency
            total_elements = int(np.prod(shape) * (1-sparsity))
            values = np.random.normal(0, 1/np.sqrt(np.prod(shape)), total_elements)
            indices = np.array([np.random.randint(0, dim, total_elements) for dim in shape]).T
            self.data = self._construct_sparse_tensor(indices, values, shape)
        elif distribution == 'uniform':
            self.data = np.random.uniform(-0.01, 0.01, shape).astype(dtype)
        elif distribution == 'power_law':
            # Power law initialization for scale-free properties
            base = np.random.power(2.5, shape).astype(dtype) * 0.1
            signs = np.random.choice([-1, 1], shape)
            self.data = base * signs
        elif distribution == 'complex_gaussian':
            real_part = np.random.normal(0, 1/np.sqrt(2*np.prod(shape)), shape)
            imag_part = np.random.normal(0, 1/np.sqrt(2*np.prod(shape)), shape)
            self.data = (real_part + 1j * imag_part).astype(np.complex64)
        elif distribution == 'orthogonal':
            if self.rank >= 2:
                random_matrix = np.random.normal(0, 1, (shape[0], shape[0]))
                q, _ = np.linalg.qr(random_matrix)
                
                # Extend to full tensor
                full_tensor = np.zeros(shape)
                for i in range(shape[0]):
                    idx = (i,) + (0,) * (self.rank - 1)
                    for j in range(shape[0]):
                        idx2 = (i, j) + (0,) * (self.rank - 2)
                        if self.rank >= 2:
                            full_tensor[idx2] = q[i, j]
                self.data = full_tensor
            else:
                # Fall back to normal for rank < 2
                self.data = np.random.normal(0, 1/np.sqrt(np.prod(shape)), shape).astype(dtype)
        elif distribution in ('empty', 'zeros'):
            # Honest explicit construction path: no random index sampling.
            # Capability tensors and from_dict both require this.
            self.data = np.zeros(shape, dtype=dtype)
            self.sparsity = 1.0
        else:
            raise ValueError(f"Unknown distribution type: {distribution}")
        
        # Core operations dictionary: maps operation names to functions
        self.operations = {
            'contract': self.contract,
            'expand': self.expand,
            'project': self.project,
            'embed': self.embed,
            'transform': self.transform
        }
        
        # Computational history for recursive operations
        self.operation_history = []
        
        # Eigenstate cache for efficiency
        self._eigenstate_cache = {}
        
        # Metadata for tracking
        self.metadata = {
            "id": self.uuid,  # Added id
            "created_at": self.creation_time,  # Renamed 'created' to 'created_at'
            "modified": self.creation_time,
            "operations_count": 0,
            "description": f"RecursiveTensor({self.dimensions}, rank={self.rank})"
        }
        
        logger.debug(f"Created {distribution} RecursiveTensor with dimensions={dimensions}, rank={rank}")

    @classmethod
    def from_dict(cls, values, dimensions=None, dtype=np.float32, uuid_value=None):
        """Construct a RecursiveTensor from an explicit index mapping.

        The ``distribution='normal'`` path samples random indices, so collisions
        leave actual nonzeros below target — fine for random init, useless for
        an explicitly constructed capability tensor. This constructor writes
        exactly the supplied cells. ``dimensions`` must be a shape tuple so
        axis identity is honest (P1).

        ``values`` may also be a tensor blob:
        - a full ``serialize()`` dict (uuid + rank + sparsity + dtype) delegates
          to ``deserialize``;
        - a hub snapshot dict with ``dimensions`` + ``data`` / ``data_format``
          (no uuid) writes those cells onto an empty tensor. Fletcher's
          ``CapabilityTensorIndex.from_snapshot`` uses this shape.
        """
        if _looks_like_tensor_blob(values):
            return cls._from_tensor_blob(values, dtype=dtype, uuid_value=uuid_value)
        if isinstance(values, np.ndarray):
            array = np.array(values, copy=True)
            if dimensions is None:
                dimensions = tuple(int(n) for n in array.shape)
            shape = tuple(int(d) for d in dimensions)
            if tuple(array.shape) != shape:
                raise ValueError(
                    f"from_dict ndarray shape {array.shape} != dimensions {shape}"
                )
            tensor = cls(shape, dtype=dtype, distribution="empty", sparsity=1.0)
            cls._apply_uuid(tensor, uuid_value)
            tensor.data = array.astype(dtype, copy=False)
            tensor.sparsity = 0.0
            return tensor
        if dimensions is None:
            raise ValueError(
                "from_dict requires a shape tuple so axis identity is honest",
            )
        if isinstance(dimensions, int):
            raise ValueError(
                "from_dict refuses integer dimensions; pass a shape tuple "
                "(P1: dimensions is always a shape tuple)",
            )
        shape = tuple(int(d) for d in dimensions)
        if any(extent < 0 for extent in shape):
            raise ValueError("from_dict dimensions must be non-negative")
        tensor = cls(shape, dtype=dtype, distribution="empty", sparsity=1.0)
        cls._apply_uuid(tensor, uuid_value)
        if not isinstance(values, Mapping):
            raise TypeError("from_dict values must be a mapping of index -> number")
        dense = np.zeros(shape, dtype=dtype)
        filled = 0
        for key, raw in values.items():
            if isinstance(key, str) and key.startswith("_"):
                continue
            if isinstance(key, (list, tuple)):
                idx = tuple(int(part) for part in key)
            elif isinstance(key, int) and len(shape) == 1:
                idx = (int(key),)
            else:
                raise TypeError(
                    f"from_dict index must be a tuple (got {type(key).__name__})",
                )
            if len(idx) != len(shape):
                raise ValueError(
                    f"index rank {len(idx)} does not match dimensions rank {len(shape)}",
                )
            for axis, (coord, extent) in enumerate(zip(idx, shape)):
                if coord < 0 or coord >= extent:
                    raise IndexError(
                        f"index {idx} out of bounds for axis {axis} extent {extent}",
                    )
            dense[idx] = dtype(raw) if not np.iscomplexobj(np.array(raw)) else raw
            filled += 1
        tensor.data = dense
        tensor.sparsity = 0.0 if tensor._volume() == 0 else 1.0 - (filled / tensor._volume())
        tensor.metadata["description"] = (
            f"RecursiveTensor.from_dict(dimensions={shape}, filled={filled})"
        )
        return tensor

    @staticmethod
    def _apply_uuid(tensor, uuid_value):
        if uuid_value is None:
            return
        if not isinstance(uuid_value, str) or not uuid_value:
            raise ValueError("uuid_value must be a non-empty string")
        tensor.uuid = uuid_value
        tensor.metadata["id"] = uuid_value

    @classmethod
    def _from_tensor_blob(cls, blob, dtype=np.float32, uuid_value=None):
        """Materialize a serialize() or hub-snapshot blob without resampling."""
        complete = all(
            key in blob for key in ("uuid", "rank", "sparsity", "dtype", "data_format")
        )
        if complete:
            tensor = cls.deserialize(blob)
            cls._apply_uuid(tensor, uuid_value)
            return tensor
        dims = blob["dimensions"]
        if isinstance(dims, int):
            raise ValueError(
                "from_dict blob refuses integer dimensions; pass a shape tuple",
            )
        shape = tuple(int(d) for d in dims)
        if any(extent < 0 for extent in shape):
            raise ValueError("from_dict dimensions must be non-negative")
        raw_dtype = blob.get("dtype", dtype)
        if isinstance(raw_dtype, str):
            resolved_dtype = np.dtype(raw_dtype)
        else:
            resolved_dtype = np.dtype(raw_dtype)
        tensor = cls(shape, dtype=resolved_dtype, distribution="empty", sparsity=1.0)
        blob_uuid = blob.get("uuid")
        cls._apply_uuid(
            tensor,
            uuid_value if uuid_value is not None else (
                blob_uuid if isinstance(blob_uuid, str) and blob_uuid else None
            ),
        )
        data_format = str(blob.get("data_format", "dense"))
        is_complex = bool(blob.get("complex", False))
        if data_format == "sparse":
            cells = blob.get("data", [])
            sparse = {}
            if is_complex:
                for item in cells:
                    sparse[tuple(item[0])] = complex(item[1], item[2])
            else:
                for item in cells:
                    sparse[tuple(item[0])] = item[1]
            tensor.data = sparse
            volume = tensor._volume()
            tensor.sparsity = 0.0 if volume == 0 else 1.0 - (len(sparse) / volume)
        elif is_complex and "data_real" in blob:
            real_part = np.array(blob["data_real"])
            imag_part = np.array(blob["data_imag"])
            if tuple(real_part.shape) != shape:
                raise ValueError(
                    f"from_dict blob data_real shape {real_part.shape} != dimensions {shape}"
                )
            tensor.data = real_part + 1j * imag_part
            tensor.sparsity = 0.0
        else:
            if "data" not in blob:
                raise ValueError("from_dict blob requires 'data' for dense format")
            array = np.array(blob["data"], dtype=resolved_dtype)
            if tuple(array.shape) != shape:
                raise ValueError(
                    f"from_dict blob data shape {array.shape} != dimensions {shape}"
                )
            tensor.data = array
            tensor.sparsity = 0.0
        if "distribution" in blob:
            tensor.distribution = blob["distribution"]
        tensor.metadata["description"] = (
            f"RecursiveTensor.from_dict(blob, dimensions={shape})"
        )
        return tensor

    def to_dense_array(self):
        """Return an owned dense ndarray with this tensor's declared shape."""
        if isinstance(self.data, np.ndarray):
            return np.array(self.data, copy=True)
        volume_shape = tuple(self.dimensions)
        if hasattr(self.data, "toarray"):
            dense = np.asarray(self.data.toarray())
            if dense.shape == volume_shape:
                return dense
            out = np.zeros(volume_shape, dtype=self.dtype)
            slices = tuple(slice(0, min(a, b)) for a, b in zip(dense.shape, volume_shape))
            out[slices] = dense[slices]
            return out
        if isinstance(self.data, dict):
            out = np.zeros(volume_shape, dtype=self.dtype)
            for idx, val in self.data.items():
                out[tuple(idx)] = val
            return out
        return np.asarray(self.data)

    @property
    def shape(self):
        """Return the shape of the tensor as a tuple."""
        return tuple(self.dimensions)

    def _volume(self) -> int:
        """Return the number of cells in the full dense shape."""
        if not self.dimensions:
            return 0
        return int(np.prod(self.dimensions))
    
    def _construct_sparse_tensor(self, indices, values, shape):
        """
        Construct a sparse tensor representation from indices and values
        
        Args:
            indices: array of indices
            values: array of values
            shape: target tensor shape
            
        Returns:
            Sparse tensor representation (matrix or dictionary)
        """
        if len(shape) <= 2:
            # For rank 2 or less, use scipy sparse matrix
            rows, cols = indices[:, 0], indices[:, 1]
            return csr_matrix((values, (rows, cols)), shape=shape[:2])
        else:
            # For higher ranks, use dictionary-based sparse representation
            tensor = {}
            for idx, val in zip(map(tuple, indices), values):
                if abs(val) > 1e-6:  # Threshold to maintain sparsity
                    tensor[idx] = val
            return tensor
    
    def _sparse_to_dense(self, sparse_dict):
        """
        Convert sparse dictionary representation to dense tensor
        
        Args:
            sparse_dict: Dictionary-based sparse tensor
            
        Returns:
            numpy.ndarray: Dense tensor
        """
        # Determine shape from the keys
        if not sparse_dict:
            return np.zeros(self.shape, dtype=self.dtype)
            
        max_indices = tuple(max(idx[i] for idx in sparse_dict.keys()) + 1 
                           for i in range(len(next(iter(sparse_dict.keys())))))
        dense = np.zeros(max_indices, dtype=self.dtype)
        for idx, val in sparse_dict.items():
            dense[idx] = val
        return dense
    
    def contract(self, other_tensor, axes=((0,), (0,))):
        """
        Contract this tensor with another tensor along specified axes.
        
        Args:
            other_tensor: RecursiveTensor or numpy.ndarray
            axes: tuple of axis specifications for contraction
            
        Returns:
            RecursiveTensor: Result of contraction
        """
        self.operation_history.append(('contract', id(other_tensor), axes))
        self.metadata["operations_count"] += 1
        self.metadata["modified"] = time.time()
        
        # Handle different tensor types
        if isinstance(other_tensor, RecursiveTensor):
            other_data = other_tensor.data
        else:
            other_data = other_tensor
            
        # Perform tensor contraction
        if isinstance(self.data, dict) or isinstance(other_data, dict):
            # Sparse tensor contraction
            result_data = self._sparse_tensor_contract(self.data, other_data, axes)
        else:
            # Ensure both inputs are numpy arrays for tensordot
            data1 = self.data.toarray() if hasattr(self.data, 'toarray') else self.data
            data2 = other_data.toarray() if hasattr(other_data, 'toarray') else other_data
            result_data = np.tensordot(data1, data2, axes)
        
        # Honest result shape: ndarray shape, or remaining mode sizes for sparse.
        if isinstance(result_data, np.ndarray):
            result_dims = tuple(result_data.shape)
        else:
            if isinstance(other_tensor, RecursiveTensor):
                other_shape = other_tensor.shape
            elif hasattr(other_data, "shape"):
                other_shape = tuple(other_data.shape)
            else:
                other_shape = self.shape
            kept_self = [self.shape[i] for i in range(len(self.shape)) if i not in axes[0]]
            kept_other = [other_shape[i] for i in range(len(other_shape)) if i not in axes[1]]
            result_dims = tuple(kept_self + kept_other)
            if not result_dims and isinstance(result_data, dict):
                # Full contraction to a scalar-like sparse payload.
                result_dims = ()

        if result_dims:
            result = RecursiveTensor(
                result_dims,
                dtype=self.dtype,
                distribution=self.distribution,
                sparsity=self.sparsity,
            )
        else:
            result = RecursiveTensor(
                1,
                rank=0,
                dtype=self.dtype,
                distribution=self.distribution,
                sparsity=self.sparsity,
            )
            result.dimensions = ()
            result.rank = 0
        result.data = result_data
        # Guarantee dimensions track the actual payload shape after overwrite.
        if isinstance(result_data, np.ndarray):
            result.dimensions = tuple(result_data.shape)
            result.rank = result_data.ndim
        else:
            result.dimensions = result_dims
            result.rank = len(result_dims)
        result.metadata = self.metadata.copy()
        result.metadata["description"] = f"Contraction of {self.metadata['description']} with {getattr(other_tensor, 'metadata', {}).get('description', 'external tensor')}"
        if isinstance(other_tensor, RecursiveTensor):
            result.operation_history = self.operation_history.copy()
            result.operation_history.extend(other_tensor.operation_history)
        return result

    def _sparse_tensor_contract(self, tensor1, tensor2, axes):
        """
        Custom implementation of tensor contraction for sparse representations
        
        Args:
            tensor1: First tensor (sparse dict or ndarray)
            tensor2: Second tensor (sparse dict or ndarray)
            axes: Axes to contract
            
        Returns:
            Contracted tensor (sparse dict or ndarray)
        """
        if isinstance(tensor1, dict) and isinstance(tensor2, dict):
            result = {}
            for idx1, val1 in tensor1.items():
                for idx2, val2 in tensor2.items():
                    if all(idx1[ax1] == idx2[ax2] for ax1, ax2 in zip(axes[0], axes[1])):
                        result_idx = self._compute_result_idx(idx1, idx2, axes)
                        result[result_idx] = result.get(result_idx, 0) + val1 * val2
            return result
        else:
            if isinstance(tensor1, dict):
                tensor1 = self._sparse_to_dense(tensor1)
            if isinstance(tensor2, dict):
                tensor2 = self._sparse_to_dense(tensor2)
            return np.tensordot(tensor1, tensor2, axes)
    
    def _compute_result_idx(self, idx1, idx2, axes):
        """
        Helper to compute the resulting index in tensor contraction
        
        Args:
            idx1: Index from first tensor
            idx2: Index from second tensor
            axes: Contraction axes
            
        Returns:
            tuple: Resulting index
        """
        remaining_idx1 = [i for j, i in enumerate(idx1) if j not in axes[0]]
        remaining_idx2 = [i for j, i in enumerate(idx2) if j not in axes[1]]
        return tuple(remaining_idx1 + remaining_idx2)
    
    def expand(self, new_dimensions):
        """
        Expand tensor to higher dimensions through tensor product with basis.
        
        Args:
            new_dimensions: int or tuple - target dimension(s) to expand to
            
        Returns:
            RecursiveTensor: Expanded tensor
        """
        if isinstance(new_dimensions, int):
            new_dimensions = (new_dimensions,)
        if len(new_dimensions) > self.rank:
            raise ValueError("Cannot expand to more dimensions than the current rank")
        self.operation_history.append(('expand', new_dimensions))
        self.metadata["operations_count"] += 1
        self.metadata["modified"] = time.time()
        self.metadata["description"] = f"Expanded {self.metadata['description']} to {new_dimensions}"
        new_dimensions = tuple(int(d) for d in new_dimensions)
        if isinstance(self.data, dict):
            new_data = {}
            for idx, val in self.data.items():
                new_idx = (0,) * len(new_dimensions) + idx
                new_data[new_idx] = val
        else:
            new_data = self.create_tensor_expansion(new_dimensions)

        result_dims = new_dimensions + self.shape
        result = RecursiveTensor(
            result_dims,
            dtype=self.dtype,
            distribution=self.distribution,
            sparsity=self.sparsity,
        )
        result.data = new_data
        result.dimensions = result_dims
        result.rank = len(result_dims)
        result.operation_history = self.operation_history.copy()
        result.metadata = self.metadata.copy()
        result.metadata["description"] = f"Expanded {self.metadata['description']} to include {new_dimensions} dimensions"
        return result

    def create_tensor_expansion(self, new_dimensions):
        """Embed dense data into a larger shape with leading modes (zeros elsewhere)."""
        expansion_shape = tuple(new_dimensions) + tuple(self.data.shape)
        new_data = np.zeros(expansion_shape, dtype=self.dtype)
        leading = tuple(0 for _ in new_dimensions)
        new_data[leading] = self.data
        return new_data

    def project(self, subspace_basis, axes=(0,)):
        """
        Project tensor onto a subspace defined by basis vectors.

        ``subspace_basis`` is (k, n) with ``n`` equal to the projected axis
        extent. A 1-D vector is treated as a single basis row (k=1). Each
        listed axis is replaced by the k basis coordinates. Layout is
        preserved with moveaxis so projecting a non-leading axis (context=2,
        tick=last) does not scramble agent/capability cells.

        Args:
            subspace_basis: array-like basis vectors
            axes: tuple - axes to project along

        Returns:
            RecursiveTensor: Projected tensor whose ``dimensions`` match data.
        """
        self.operation_history.append(('project', getattr(subspace_basis, 'shape', None), axes))
        self.metadata["operations_count"] += 1
        self.metadata["modified"] = time.time()
        self.metadata["description"] = f"Projection of {self.metadata['description']} onto subspace"
        if not isinstance(subspace_basis, np.ndarray):
            subspace_basis = np.array(subspace_basis, dtype=np.float64)
        if subspace_basis.ndim == 1:
            subspace_basis = np.reshape(subspace_basis, (1, -1))
        if subspace_basis.ndim != 2:
            raise ValueError("subspace_basis must be 1-D or 2-D (k, n)")
        norms = np.linalg.norm(subspace_basis, axis=1, keepdims=True)
        norms = np.where(norms == 0.0, 1.0, norms)
        normalized_basis = subspace_basis / norms
        axis_tuple = tuple(axes) if isinstance(axes, (tuple, list)) else (axes,)

        if isinstance(self.data, dict):
            projected_data = self._sparse_project(normalized_basis, axis_tuple)
            result_dims = list(self.dimensions)
            for ax in axis_tuple:
                result_dims[ax] = int(normalized_basis.shape[0])
            result_dims = tuple(int(n) for n in result_dims)
        else:
            projected_data = np.array(self.data, copy=True)
            for ax in axis_tuple:
                ax = int(ax)
                if ax < 0:
                    ax = projected_data.ndim + ax
                n = int(projected_data.shape[ax])
                if int(normalized_basis.shape[1]) != n:
                    raise ValueError(
                        f"basis width {normalized_basis.shape[1]} != axis {ax} extent {n}"
                    )
                moved = np.moveaxis(projected_data, ax, 0)
                rest = moved.shape[1:]
                projected = normalized_basis @ moved.reshape(n, -1)
                k = int(normalized_basis.shape[0])
                projected_data = np.moveaxis(
                    projected.reshape((k,) + rest), 0, ax,
                )
            result_dims = tuple(int(n) for n in projected_data.shape)

        result = RecursiveTensor(
            result_dims,
            dtype=self.dtype,
            distribution=self.distribution,
            sparsity=self.sparsity,
        )
        result.data = projected_data
        result.dimensions = result_dims
        result.rank = len(result_dims)
        result.operation_history = self.operation_history.copy()
        result.metadata = self.metadata.copy()
        result.metadata["description"] = f"Projection of {self.metadata['description']} onto subspace"
        return result
    
    def _sparse_project(self, basis, axes):
        """
        Project sparse tensor data onto basis
        
        Args:
            basis: Normalized basis vectors
            axes: Axes to project along
            
        Returns:
            dict: Projected sparse tensor
        """
        if len(axes) > 1:
            result = self.data.copy() if isinstance(self.data, dict) else {idx: val for idx, val in np.ndenumerate(self.data) if val != 0}
            for ax in axes:
                result = self._sparse_project_single_axis(result, basis, ax)
            return result
        else:
            return self._sparse_project_single_axis(self.data, basis, axes[0])
    
    def _sparse_project_single_axis(self, sparse_data, basis, axis):
        """
        Project sparse tensor data onto basis along a single axis
        
        Args:
            sparse_data: Sparse tensor data (dictionary)
            basis: Normalized basis vectors
            axis: Axis to project along
            
        Returns:
            dict: Projected sparse tensor
        """
        result = {}
        
        for idx, val in sparse_data.items():
            for b_idx, basis_vec in enumerate(basis):
                proj_idx = list(idx)
                proj_idx[axis] = b_idx
                proj_idx = tuple(proj_idx)
                
                proj_val = val * basis_vec[idx[axis]]
                if abs(proj_val) > 1e-10:  
                    result[proj_idx] = result.get(proj_idx, 0) + proj_val
                
        return result
    
    def embed(self, embedding_function, new_rank=None):
        """
        Embed tensor in higher-dimensional space using embedding function.
        
        Args:
            embedding_function: Callable - function to compute embedding
            new_rank: int - rank of resulting tensor (default: self.rank + 1)
            
        Returns:
            RecursiveTensor: Embedded tensor
        """
        if new_rank is None:
            new_rank = self.rank + 1
            
        self.operation_history.append(('embed', new_rank))
        self.metadata["operations_count"] += 1
        self.metadata["modified"] = time.time()
        
        result = RecursiveTensor(self.dimensions, 
                               rank=new_rank, 
                               dtype=self.dtype,
                               distribution=self.distribution,
                               sparsity=self.sparsity)
        
        if callable(embedding_function):
            if isinstance(self.data, dict):
                embedded_data = {}
                for idx, val in self.data.items():
                    embedded_val = embedding_function(val, idx)
                    if isinstance(embedded_val, dict):  
                        for e_idx, e_val in embedded_val.items():
                            if abs(e_val) > 1e-10:  
                                embedded_data[idx + e_idx] = e_val
                    else: 
                        if isinstance(embedded_val, (int, float, complex, np.number)):
                            if abs(embedded_val) > 1e-10:
                                embedded_data[idx + (0,)] = embedded_val
                result.data = embedded_data
            else:
                result.data = embedding_function(self.data)
        else:
            raise TypeError("embedding_function must be callable")
        
        result.operation_history = self.operation_history.copy()
        result.metadata = self.metadata.copy()
        result.metadata["description"] = f"Embedding of {self.metadata['description']} to rank {new_rank}"
            
        return result
    
    def transform(self, transformation_matrix, axes=None):
        """
        Apply linear transformation to tensor.
        
        Args:
            transformation_matrix: array-like transformation matrix
            axes: tuple - axes to transform (default: all)
            
        Returns:
            RecursiveTensor: Transformed tensor
        """
        if axes is None:
            axes = tuple(range(self.rank))
            
        self.operation_history.append(('transform', transformation_matrix.shape if hasattr(transformation_matrix, 'shape') else None, axes))
        self.metadata["operations_count"] += 1
        self.metadata["modified"] = time.time()
        
        if not isinstance(transformation_matrix, np.ndarray):
            transformation_matrix = np.array(transformation_matrix)
        if transformation_matrix.ndim != 2:
            raise ValueError("Transformation matrix must be 2D")
        if transformation_matrix.shape[1] != self.dimensions:
            raise ValueError("Transformation matrix must match tensor dimensions")
        if transformation_matrix.shape[0] > self.dimensions:
            raise ValueError("Transformation matrix cannot expand tensor dimensions")
        if isinstance(self.data, dict):
            transformed_data = self._sparse_transform(transformation_matrix, axes)
        else:
            transformed_data = self.data.copy()
            for ax in axes:
                tensor_shape = transformed_data.shape
                reshaped = transformed_data.swapaxes(0, ax).reshape(tensor_shape[ax], -1)
                transformed = transformation_matrix @ reshaped
                new_shape = list(tensor_shape)
                new_shape[ax] = transformation_matrix.shape[0]
                transformed_data = transformed.reshape(new_shape).swapaxes(0, ax)
        
        result = RecursiveTensor(self.dimensions, 
                               rank=self.rank, 
                               dtype=self.dtype,
                               distribution=self.distribution,
                               sparsity=self.sparsity)
        result.data = transformed_data
        result.operation_history = self.operation_history.copy()
        result.metadata = self.metadata.copy()
        result.metadata["description"] = f"Transformation of {self.metadata['description']}"

        return result
    
    def _sparse_transform(self, matrix, axes):
        """
        Apply transformation to sparse tensor
        
        Args:
            matrix: Transformation matrix
            axes: Axes to transform
            
        Returns:
            dict: Transformed sparse tensor
        """
        result = {}
        
        for idx, val in self.data.items():
            for ax in axes:
                ax_idx = idx[ax]
                
                for out_idx in range(matrix.shape[0]):
                    trans_val = matrix[out_idx, ax_idx] * val
                    if abs(trans_val) > 1e-10:  
                        new_idx = list(idx)
                        new_idx[ax] = out_idx
                        new_idx = tuple(new_idx)
                        result[new_idx] = result.get(new_idx, 0) + trans_val
                        
        return result
    
    def compute_eigenstates(self, axes=None, k=6, convergence_threshold=1e-8):
        """
        Compute dominant eigenstates using the Eigenrecursion theorem.
        
        This method implements the recursive stability protocol described in the
        Eigenrecursion theorem, ensuring convergence to stable eigenstates through
        iterative refinement and fixed-point detection.
        
        Args:
            axes: tuple of tuples - axes to flatten for eigendecomposition, or None for auto
            k: int - number of eigenstates to compute
            convergence_threshold: float - threshold for eigenrecursion convergence
            
        Returns:
            tuple: (eigenvalues, eigenvectors) following eigenrecursion convergence
        """
        if axes is None:
            if self.rank <= 2:
                axes = ((0,), (1,)) if self.rank == 2 else ((0,), ())
            else:
                # For higher rank, flatten all but last axis into rows, last axis into columns
                axes = (tuple(range(self.rank-1)), (self.rank-1,))
        
        cache_key = (axes, k, convergence_threshold)
        if cache_key in self._eigenstate_cache:
            return self._eigenstate_cache[cache_key]
        
        # Step 1: Construct matrix representation for eigenrecursion
        if isinstance(self.data, dict):
            matrix = self._sparse_to_matrix(axes)
        else:
            # Flatten tensor along specified axes for eigenrecursion
            matrix_shape = [
                np.prod([self.data.shape[ax] for ax in axes[0]]),
                np.prod([self.data.shape[ax] for ax in axes[1]])
            ]
            matrix = self.data.transpose(axes[0] + axes[1]).reshape(matrix_shape)
        
        # Step 2: Apply eigenrecursion protocol for convergence
        if matrix.shape[0] == matrix.shape[1]:
            # Square matrix - use eigendecomposition
            if isinstance(matrix, csr_matrix) or matrix.shape[0] > 1000:
                try:
                    # Sparse eigenvalue computation with eigenrecursion refinement
                    eigenvalues, eigenvectors = eigsh(
                        matrix, 
                        k=min(k, matrix.shape[0]-1), 
                        which='LM',
                        tol=convergence_threshold
                    )
                except Exception:
                    if isinstance(matrix, csr_matrix):
                        matrix = matrix.toarray()
                    eigenvalues, eigenvectors = self._eigenrecursion_solve(
                        matrix, k, convergence_threshold
                    )
            else:
                # Dense eigenvalue computation with eigenrecursion
                eigenvalues, eigenvectors = self._eigenrecursion_solve(
                    matrix, k, convergence_threshold
                )
        else:
            # Rectangular matrix - use SVD
            if isinstance(matrix, csr_matrix):
                matrix = matrix.toarray()
            
            U, s, Vt = np.linalg.svd(matrix, full_matrices=False)
            eigenvalues = s[:k]
            eigenvectors = Vt[:k].T  # Use right singular vectors as "eigenvectors"
        
        # Step 3: Eigenrecursion convergence verification
        # For square matrices, verify eigenvalue accuracy; for rectangular, SVD is already converged
        if matrix.shape[0] == matrix.shape[1]:
            eigenvalues, eigenvectors = self._verify_eigenrecursion_convergence(
                matrix, eigenvalues, eigenvectors, convergence_threshold
            )
        
        # Step 4: Reshape eigenvectors back to tensor structure
        eigenvectors = self._reshape_eigenvectors_to_tensor(
            eigenvectors, axes, k
        )
        
        self._eigenstate_cache[cache_key] = (eigenvalues, eigenvectors)
        return eigenvalues, eigenvectors
    
    def _eigenrecursion_solve(self, matrix, k, threshold):
        """
        Solve eigenvalue problem using eigenrecursion theorem principles.
        
        Implements the recursive stability protocol to ensure convergence
        to true eigenstates through iterative refinement.
        """
        # Ensure matrix is Hermitian for real eigenvalues
        if not np.allclose(matrix, matrix.conj().T):
            matrix = (matrix + matrix.conj().T) / 2
            
        eigenvalues, eigenvectors = np.linalg.eigh(matrix)
        
        # Sort by magnitude for dominant eigenstates
        idx = np.argsort(np.abs(eigenvalues))[::-1][:k]
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]
        
        return eigenvalues, eigenvectors
    
    def _verify_eigenrecursion_convergence(self, matrix, eigenvalues, eigenvectors, threshold):
        """
        Verify eigenrecursion convergence using fixed-point detection.
        
        Implements the stability protocol from the Eigenrecursion theorem
        to ensure computed eigenstates are true fixed points.
        """
        # Check eigenvalue accuracy using Rayleigh quotient
        for i in range(len(eigenvalues)):
            v = eigenvectors[:, i]
            rayleigh_quotient = np.vdot(v, matrix @ v) / np.vdot(v, v)
            
            # Apply eigenrecursion refinement if needed
            if abs(rayleigh_quotient - eigenvalues[i]) > threshold:
                # Refine using inverse iteration
                shifted_matrix = matrix - eigenvalues[i] * np.eye(matrix.shape[0])
                try:
                    refined_v = np.linalg.solve(shifted_matrix, v)
                    refined_v = refined_v / np.linalg.norm(refined_v)
                    eigenvectors[:, i] = refined_v
                    
                    # Recompute eigenvalue
                    eigenvalues[i] = np.vdot(refined_v, matrix @ refined_v)
                except np.linalg.LinAlgError:
                    # Singular matrix - use original eigenvector
                    pass
        
        return eigenvalues, eigenvectors
    
    def _reshape_eigenvectors_to_tensor(self, eigenvectors, axes, k):
        """
        Reshape eigenvectors back to tensor structure following eigenrecursion.
        
        Maps the flattened eigenvectors back to the original tensor space
        while preserving the eigenrecursion convergence properties.
        """
        if len(axes[1]) == 0:
            # Handle edge case
            return eigenvectors.T
            
        # Compute target shape for eigenvectors
        if isinstance(self.data, dict):
            # Sparse tensor case
            target_shape = [k] + [self.dimensions[ax] for ax in axes[1]]
        else:
            # Dense tensor case
            target_shape = [k] + [self.data.shape[ax] for ax in axes[1]]
        
        # Reshape each eigenvector
        reshaped_eigenvectors = []
        for i in range(k):
            vec = eigenvectors[:, i]
            tensor_vec = vec.reshape([self.dimensions[ax] for ax in axes[1]] if isinstance(self.data, dict) else [self.data.shape[ax] for ax in axes[1]])
            reshaped_eigenvectors.append(tensor_vec)
        
        return np.array(reshaped_eigenvectors)
    
    def _sparse_to_matrix(self, axes):
        """
        Convert sparse tensor to matrix representation for eigenrecursion.
        
        Optimized sparse conversion that preserves the tensor structure
        needed for eigenrecursion convergence analysis.
        """
        if isinstance(self.dimensions, (tuple, list)):
            dim1 = int(np.prod([self.dimensions[ax] for ax in axes[0]]))
            dim2 = int(np.prod([self.dimensions[ax] for ax in axes[1]]))
        else:
            # Legacy behavior for integer dimensions
            dim1 = self.dimensions ** len(axes[0])
            dim2 = self.dimensions ** len(axes[1])
        
        matrix = lil_matrix((dim1, dim2))
        
        for idx, val in self.data.items():
            # Map tensor indices to matrix indices using eigenrecursion indexing
            if isinstance(self.dimensions, (tuple, list)):
                row_idx = sum(idx[ax] * int(np.prod([self.dimensions[i] for i in axes[0][:j]])) 
                             for j, ax in enumerate(axes[0]))
                col_idx = sum(idx[ax] * int(np.prod([self.dimensions[i] for i in axes[1][:j]])) 
                             for j, ax in enumerate(axes[1]))
            else:
                # Legacy behavior
                row_idx = sum(idx[ax] * (self.dimensions ** i) 
                             for i, ax in enumerate(axes[0]))
                col_idx = sum(idx[ax] * (self.dimensions ** i) 
                             for i, ax in enumerate(axes[1]))
            matrix[row_idx, col_idx] = val
            
        return matrix.tocsr()
    
    def fractal_iteration(self, c_function, max_iter=10):
        """
        Apply fractal iteration to tensor values following Mandelbrot-Julia pattern.
        
        Args:
            c_function: Callable - function to generate c parameter
            max_iter: int - maximum iterations
            
        Returns:
            RecursiveTensor: Result of fractal iteration
        """
        self.operation_history.append(('fractal', max_iter))
        self.metadata["operations_count"] += 1
        self.metadata["modified"] = time.time()
        
        result = RecursiveTensor(self.dimensions, 
                               rank=self.rank, 
                               dtype=self.dtype,
                               distribution=self.distribution,
                               sparsity=self.sparsity)
        
        if isinstance(self.data, dict):
            result_data = {}
            for idx, z_val in self.data.items():
                c_val = c_function(idx, z_val)
                for _ in range(max_iter):
                    z_val = z_val**2 + c_val
                    if abs(z_val) > 2:
                        break
                if abs(z_val) > 1e-10:  
                    result_data[idx] = z_val
            result.data = result_data
        else:
            z = self.data.copy()
            c = c_function(None, z)  
            
            for _ in range(max_iter):
                z = z**2 + c
                if np.issubdtype(z.dtype, np.complexfloating):
                    escaped = np.abs(z) > 2
                    if np.all(escaped):
                        break
            
            result.data = z
        
        result.operation_history = self.operation_history.copy()
        result.metadata = self.metadata.copy()
        result.metadata["description"] = f"Fractal iteration of {self.metadata['description']} ({max_iter} steps)"
            
        return result
    def visualize_slice(self, axes=(0, 1), slice_indices=None, cmap='viridis', title=None, show=True):
        """
        Visualize a 2D slice of the tensor
        
        Args:
            axes: tuple - which two axes to use for the 2D visualization
            slice_indices: dict - indices for other axes
            cmap: str - matplotlib colormap name
            title: str - plot title
            show: bool - whether to display the plot (or just return the figure)
            
        Returns:
            matplotlib.figure.Figure: Figure object with the visualization
        """
        if self.rank < 2:
            raise ValueError("Tensor must have rank >= 2 for 2D visualization")
            
        if slice_indices is None:
            slice_indices = {i: 0 for i in range(self.rank) if i not in axes}
        
        if isinstance(self.data, dict):
            slice_matrix = np.zeros((self.dimensions, self.dimensions))
            for idx, val in self.data.items():
                if all(idx[ax] == slice_idx for ax, slice_idx in slice_indices.items()):
                    if len(idx) > max(axes) and idx[axes[0]] < self.dimensions and idx[axes[1]] < self.dimensions:
                        slice_matrix[idx[axes[0]], idx[axes[1]]] = val
        else:
            slice_idx = tuple(slice(None) if i in axes else slice_indices.get(i, 0) 
                             for i in range(self.rank))
            slice_matrix = self.data[slice_idx]
        
        plt.figure(figsize=(10, 8))
        if np.iscomplexobj(slice_matrix):
            im = plt.imshow(np.abs(slice_matrix), cmap=cmap)
            plt.colorbar(im, label='Magnitude')
        else:
            im = plt.imshow(np.real(slice_matrix), cmap=cmap)
            plt.colorbar(im, label='Value')
        
        plt.title(title or f"Tensor Slice along axes {axes}")
        plt.xlabel(f"Axis {axes[1]}")
        plt.ylabel(f"Axis {axes[0]}")
        plt.tight_layout()
        
        if show:
            plt.show()
            
        return plt.gcf()
    def visualize_eigenspectrum(self, axes=(0, 1), k=10, show=True):
        """
        Visualize the eigenvalue spectrum of the tensor
        
        Args:
            axes: tuple - axes to use for eigendecomposition
            k: int - number of eigenvalues to show
            show: bool - whether to display the plot
            
        Returns:
            matplotlib.figure.Figure: Figure with eigenspectrum visualization
        """
        eigenvalues, _ = self.compute_eigenstates(axes=axes, k=k)
        
        plt.figure(figsize=(10, 6))
        plt.plot(range(1, len(eigenvalues)+1), np.abs(eigenvalues), 'o-', markersize=8)
        plt.yscale('log')
        plt.grid(True, which='both', linestyle='--', alpha=0.6)
        plt.xlabel('Eigenvalue Index')
        plt.ylabel('Absolute Eigenvalue')
        plt.title('Eigenvalue Spectrum')
        
        if show:
            plt.show()
            
        return plt.gcf()
    
    def plot_operation_history(self, show=True):
        """
        Visualize the operation history of this tensor
        
        Args:
            show: bool - whether to display the plot
            
        Returns:
            matplotlib.figure.Figure: Figure with operation history visualization
        """
        if not self.operation_history:
            print("No operation history available")
            return None
        
        op_counts = {}
        for op in self.operation_history:
            op_type = op[0]
            op_counts[op_type] = op_counts.get(op_type, 0) + 1
        
        plt.figure(figsize=(10, 6))
        plt.bar(op_counts.keys(), op_counts.values())
        plt.ylabel('Count')
        plt.title('Tensor Operation History')
        plt.grid(True, alpha=0.3)
        
        if show:
            plt.show()
            
        return plt.gcf()
    
    def compute_density_function(self, resolution=50, threshold=0.01):
        """
        Compute density function of tensor values
        
        Args:
            resolution: int - number of bins for histogram
            threshold: float - threshold for including values
            
        Returns:
            tuple: (bin_edges, histogram)
        """
        if isinstance(self.data, dict):
            values = np.array(list(self.data.values()))
        else:
            values = self.data.flatten()
        
        if np.iscomplexobj(values):
            values = np.abs(values)
        
        filtered_values = values[np.abs(values) > threshold]
        
        hist, bin_edges = np.histogram(filtered_values, bins=resolution, density=True)
        
        return bin_edges, hist
    
    def visualize_density(self, resolution=50, threshold=0.01, show=True):
        """
        Visualize density function of tensor values
        
        Args:
            resolution: int - number of bins for histogram
            threshold: float - threshold for including values
            show: bool - whether to display the plot
            
        Returns:
            matplotlib.figure.Figure: Figure with density visualization
        """
        bin_edges, hist = self.compute_density_function(resolution, threshold)
        
        plt.figure(figsize=(10, 6))
        plt.stairs(hist, bin_edges)
        plt.xlabel('Value')
        plt.ylabel('Density')
        plt.title('Tensor Value Distribution')
        plt.grid(True, alpha=0.3)
        
        if show:
            plt.show()
            
        return plt.gcf()
    
    def compute_entropy(self):
        """
        Compute the information entropy of the tensor
        
        Returns:
            float: entropy value
        """
        if isinstance(self.data, dict):
            values = []
            for val in self.data.values():
                # Handle PyTorch tensors by detaching gradients
                try:
                    import torch
                    if isinstance(val, torch.Tensor):
                        if val.requires_grad:
                            values.append(val.detach().cpu().numpy())
                        else:
                            values.append(val.cpu().numpy())
                    else:
                        values.append(val)
                except ImportError:
                    values.append(val)
            values = np.array(values)
            if values.size == 0:
                return 0.0
        else:
            values = self.data.flatten()
            if values.size == 0:
                return 0.0
            values = values[values > 0]
        if np.iscomplexobj(values):
            values = np.abs(values)

        prob_dist = values / np.sum(values) if np.sum(values) > 0 else values
        prob_dist = np.clip(prob_dist, 1e-12, 1.0)
        entropy = -np.sum(prob_dist * np.log(prob_dist))

        return entropy
    
    def normalize(self, norm_type=2):
        """
        Normalize the tensor
        
        Args:
            norm_type: int or str - type of normalization (1, 2, 'inf', 'fro')
            
        Returns:
            RecursiveTensor: normalized tensor
        """
        result = RecursiveTensor(self.dimensions, 
                               rank=self.rank, 
                               dtype=self.dtype,
                               distribution=self.distribution,
                               sparsity=self.sparsity)
                               
        if isinstance(self.data, dict):
            values = []
            for val in self.data.values():
                # Handle PyTorch tensors in sparse data
                try:
                    import torch
                    if isinstance(val, torch.Tensor):
                        if val.requires_grad:
                            values.append(val.detach().numpy())
                        else:
                            values.append(val.numpy())
                    else:
                        values.append(val)
                except ImportError:
                    values.append(val)
            
            values = np.array(values)
            if values.size == 0:
                result.data = {}
                return result
                
            if norm_type == 2:
                norm = np.sqrt(np.sum(np.abs(values)**2))
            elif norm_type == 1:
                norm = np.sum(np.abs(values))
            elif norm_type == 'inf':
                norm = np.max(np.abs(values))
            else:
                norm = np.sqrt(np.sum(np.abs(values)**2))
                
            if norm > 0:
                result.data = {}
                for idx, val in self.data.items():
                    try:
                        import torch
                        if isinstance(val, torch.Tensor):
                            result.data[idx] = val / norm
                        else:
                            result.data[idx] = val / norm
                    except ImportError:
                        result.data[idx] = val / norm
            else:
                result.data = self.data.copy()
        else:
            # Handle PyTorch tensors
            try:
                import torch
                if isinstance(self.data, torch.Tensor):
                    if self.data.requires_grad:
                        # Detach and convert to numpy for computation
                        data_np = self.data.detach().numpy()
                    else:
                        data_np = self.data.numpy()
                    
                    if self.data.size == 0:
                        result.data = torch.zeros_like(self.data)
                        return result
                        
                    norm = np.linalg.norm(data_np, ord=norm_type)
                    if norm > 0:
                        result.data = self.data / norm
                    else:
                        result.data = self.data.clone()
                else:
                    # NumPy array
                    if self.data.size == 0:
                        result.data = np.zeros_like(self.data)
                        return result
                        
                    norm = np.linalg.norm(self.data, ord=norm_type)
                    if norm > 0:
                        result.data = self.data / norm
                    else:
                        result.data = self.data.copy()
            except ImportError:
                # Fallback for numpy-only case
                if self.data.size == 0:
                    result.data = np.zeros_like(self.data)
                    return result
                    
                norm = np.linalg.norm(self.data, ord=norm_type)
                if norm > 0:
                    result.data = self.data / norm
                else:
                    result.data = self.data.copy()
        
        result.operation_history = self.operation_history.copy()
        result.operation_history.append(('normalize', norm_type))
        result.metadata = self.metadata.copy()
        result.metadata["description"] = f"Normalized {self.metadata['description']}"
        
        return result
    
    def apply_function(self, func, threshold=None):
        """
        Apply a function elementwise to the tensor
        
        Args:
            func: callable - function to apply
            threshold: float - threshold for filtering values (optional)
            
        Returns:
            RecursiveTensor: transformed tensor
        """
        result = RecursiveTensor(self.dimensions, 
                               rank=self.rank, 
                               dtype=self.dtype,
                               distribution=self.distribution,
                               sparsity=self.sparsity)
        
        if isinstance(self.data, dict):
            result_data = {}
            for idx, val in self.data.items():
                new_val = func(val)
                if threshold is None or abs(new_val) > threshold:
                    result_data[idx] = new_val
            result.data = result_data
        else:
            result.data = func(self.data)
            if threshold is not None:
                result.data[np.abs(result.data) <= threshold] = 0
        
        result.operation_history = self.operation_history.copy()
        result.operation_history.append(('apply_function', func.__name__ if hasattr(func, '__name__') else 'unnamed_function'))
        result.metadata = self.metadata.copy()
        result.metadata["description"] = f"Function {func.__name__ if hasattr(func, '__name__') else 'unnamed_function'} applied to {self.metadata['description']}"
        result.sparsity = self.sparsity

        return result
    
    def compute_dict_compatibility(self, other_tensor):
        """
        Compute compatibility score between this tensor and another
        
        Args:
            other_tensor: RecursiveTensor - tensor to compare with
            
        Returns:
            float: compatibility score (0-1)
        """
        if not isinstance(other_tensor, RecursiveTensor):
            raise TypeError("Can only compute compatibility with another RecursiveTensor")
        
        data1 = self.data
        data2 = other_tensor.data
        
        if isinstance(data1, dict) and not isinstance(data2, dict):
            data2 = {idx: val for idx, val in np.ndenumerate(data2) if val != 0}
        elif not isinstance(data1, dict) and isinstance(data2, dict):
            data1 = {idx: val for idx, val in np.ndenumerate(data1) if val != 0}
            
        if isinstance(data1, dict) and isinstance(data2, dict):
            keys1 = set(data1.keys())
            keys2 = set(data2.keys())
            if not keys1 and not keys2:
                return 1.0

            if not keys1 or not keys2:
                return 0.0

            common_keys = keys1.intersection(keys2)
            all_keys = keys1.union(keys2)
            key_similarity = len(common_keys) / len(all_keys)
            
            value_similarities = []
            for key in common_keys:
                val1 = data1[key]
                val2 = data2[key]
                
                if np.iscomplexobj(val1) or np.iscomplexobj(val2):
                    mag_sim = 1.0 - min(1.0, abs(abs(val1) - abs(val2)) / max(abs(val1), abs(val2), 1e-10))
                    
                    phase1 = np.angle(val1)
                    phase2 = np.angle(val2)
                    phase_diff = min(abs(phase1 - phase2), 2*np.pi - abs(phase1 - phase2)) / np.pi
                    phase_sim = 1.0 - phase_diff
                    
                    value_similarities.append(0.7 * mag_sim + 0.3 * phase_sim)
                else:
                    if max(abs(val1), abs(val2)) > 1e-10:
                        value_similarities.append(1.0 - min(1.0, abs(val1 - val2) / max(abs(val1), abs(val2))))
                    else:
                        value_similarities.append(1.0)
            
            if value_similarities:
                value_similarity = sum(value_similarities) / len(value_similarities)
                return 0.5 * key_similarity + 0.5 * value_similarity
            else:
                return key_similarity
        
        elif not isinstance(data1, dict) and not isinstance(data2, dict):
            data1_flat = data1.flatten()
            data2_flat = data2.flatten()
            
            norm1 = np.linalg.norm(data1_flat)
            norm2 = np.linalg.norm(data2_flat)
            
            if norm1 > 0 and norm2 > 0:
                dot_product = np.abs(np.vdot(data1_flat, data2_flat))
                return float(dot_product / (norm1 * norm2))
            elif norm1 == 0 and norm2 == 0:
                return 1.0  
            else:
                return 0.0  
        
        return 0.0
    
    def serialize(self):
        """
        Serialize tensor to dictionary
        
        Returns:
            dict: Serialized representation of the tensor
        """
        tensor_dict = {
            'dimensions': self.dimensions,
            'rank': self.rank,
            'distribution': self.distribution,
            'sparsity': self.sparsity,
            'operation_history': self.operation_history,
            'metadata': self.metadata,
            'version': '2.1.0',
            'timestamp': time.time(),
            'uuid': self.uuid
        }
        
        if isinstance(self.data, dict):
            tensor_dict['data_format'] = 'sparse'
            
            if np.iscomplexobj(next(iter(self.data.values()), 0)):
                tensor_dict['data'] = [
                    [list(idx), float(val.real), float(val.imag)] 
                    for idx, val in self.data.items()
                ]
                tensor_dict['complex'] = True
            else:
                tensor_dict['data'] = [
                    [list(idx), float(val)] 
                    for idx, val in self.data.items()
                ]
                tensor_dict['complex'] = False
        else:
            tensor_dict['data_format'] = 'dense'
            if np.iscomplexobj(self.data):
                tensor_dict['data_real'] = self.data.real.tolist()
                tensor_dict['data_imag'] = self.data.imag.tolist()
                tensor_dict['complex'] = True
            else:
                tensor_dict['data'] = self.data.tolist()
                tensor_dict['complex'] = False
        
        tensor_dict['dtype'] = np.dtype(self.dtype).name
            
        return tensor_dict
    
    @classmethod
    def deserialize(cls, tensor_dict):
        """
        Create tensor from serialized dictionary
        
        Args:
            tensor_dict: dict - Dictionary from serialize() method
            
        Returns:
            RecursiveTensor: Reconstructed tensor object
        """
        dimensions = tensor_dict['dimensions']
        rank = tensor_dict['rank']
        distribution = tensor_dict['distribution']
        sparsity = tensor_dict['sparsity']
        if isinstance(dimensions, (list, tuple)):
            dimensions = tuple(int(d) for d in dimensions)
        else:
            # Legacy int payload: square tensor of the recorded rank.
            dimensions = tuple([int(dimensions)] * int(rank))
        tensor = cls(
            dimensions=dimensions,
            rank=rank,
            distribution=distribution,
            sparsity=sparsity
        )
        raw_dtype = tensor_dict['dtype']
        raw_dtype_s = str(raw_dtype)
        if raw_dtype_s.startswith("<class"):
            raw_dtype_s = raw_dtype_s.replace("<class '", "").replace("'>", "").rsplit(".", 1)[-1]
        tensor.dtype = np.dtype(raw_dtype_s)
        tensor.data = tensor_dict['data']
        tensor.distribution = tensor_dict['distribution']
        tensor.sparsity = tensor_dict['sparsity']
        tensor.operation_history = tensor_dict['operation_history']
        tensor.metadata = tensor_dict.get('metadata', {
            "created": time.time(),
            "modified": time.time(),
            "operations_count": 0,
            "description": f"Deserialized RecursiveTensor({dimensions}, rank={rank})"
        })
        tensor.uuid = tensor_dict.get('uuid', str(uuid.uuid4()))

        is_complex = tensor_dict.get('complex', False)

        if tensor_dict['data_format'] == 'sparse':
            if is_complex:
                tensor.data = {
                    tuple(item[0]): complex(item[1], item[2]) 
                    for item in tensor_dict['data']
                }
            else:
                tensor.data = {
                    tuple(item[0]): item[1]
                    for item in tensor_dict['data']
                }
        else:
            if is_complex:
                real_part = np.array(tensor_dict['data_real'])
                imag_part = np.array(tensor_dict['data_imag'])
                tensor.data = real_part + 1j * imag_part
            else:
                tensor.data = np.array(tensor_dict['data'])
        
        return tensor

    def save(self, filepath, format='json', compress=True):
        """
        Save tensor to file
        
        Args:
            filepath: Path to save file
            format: 'json' or 'pickle' - serialization format
            compress: Whether to use gzip compression
            
        Returns:
            str: Path to saved file
        """
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        data = self.serialize()
        
        data['save_timestamp'] = time.time()
        data['filepath'] = str(filepath)
        
        mode = 'wb' if format == 'pickle' or compress else 'w'
        
        if compress:
            if not filepath.endswith('.gz'):
                filepath += '.gz'
            
            if format == 'json':
                with gzip.open(filepath, 'wt', encoding='utf-8') as f:
                    f.write(json.dumps(data))
            else: 
                with gzip.open(filepath, 'wb') as f:
                    pickle.dump(data, f)
        else:
            with open(filepath, mode) as f:
                if format == 'json':
                    json.dump(data, f, indent=2)
                else:  # pickle
                    pickle.dump(data, f)
        
        logger.info(f"Tensor saved to {filepath} (format: {format}, compressed: {compress})")
        return filepath
    
    @classmethod
    def load(cls, filepath):
        """
        Load tensor from file
        
        Args:
            filepath: Path to load file from
            
        Returns:
            RecursiveTensor: Loaded tensor
        """
        # Determine if file is compressed
        is_compressed = filepath.endswith('.gz')
        
        # Open with appropriate method
        try:
            if is_compressed:
                # Try JSON first (most common) - use text mode for JSON
                try:
                    with gzip.open(filepath, 'rt', encoding='utf-8') as f:
                        data = json.loads(f.read())
                except (json.JSONDecodeError, UnicodeDecodeError):
                    # Fall back to pickle which requires binary mode
                    with gzip.open(filepath, 'rb') as f:
                        data = pickle.load(f)
            else:
                with open(filepath, 'r') as f:
                    try:
                        data = json.load(f)
                    except json.JSONDecodeError:
                        # Fall back to pickle
                        f.close()
                        with open(filepath, 'rb') as f:
                            data = pickle.load(f)
                            
            # Handle version compatibility
            if 'version' in data and data['version'] != '2.1.0':
                logger.warning(f"Loading tensor with different version: {data['version']}")
                # Here you could add version-specific conversion logic
            
            # Deserialize
            tensor = cls.deserialize(data)
            logger.info(f"Tensor loaded from {filepath}")
            return tensor
            
        except Exception as e:
            logger.error(f"Error loading tensor from {filepath}: {e}")
            raise
    
    def save_chunked(self, filepath, chunk_size=1000):
        """
        Save very large tensor in chunks to avoid memory issues
        
        Args:
            filepath: Path to save file
            chunk_size: Number of elements per chunk
            
        Returns:
            str: Path to manifest file
        """
        # Create parent directories if they don't exist
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        # Get serialized data
        data = self.serialize()
        
        # Handle chunking differently for sparse vs dense
        if data['data_format'] == 'sparse':
            # For sparse tensors, split the data array into chunks
            chunks = []
            total_elements = len(data['data'])
            chunk_count = (total_elements + chunk_size - 1) // chunk_size
            
            for i in range(chunk_count):
                chunk_data = data.copy()
                
                if data.get('complex', False):
                    # Complex data has [idx, real, imag] format
                    start_idx = i * chunk_size
                    end_idx = min((i + 1) * chunk_size, total_elements)
                    chunk_data['data'] = data['data'][start_idx:end_idx]
                else:
                    # Real data has [idx, val] format
                    start_idx = i * chunk_size
                    end_idx = min((i + 1) * chunk_size, total_elements)
                    chunk_data['data'] = data['data'][start_idx:end_idx]
                
                chunk_data['chunk_id'] = i
                chunk_data['total_chunks'] = chunk_count
                
                chunk_path = f"{filepath}.chunk{i}"
                with gzip.open(chunk_path, 'wb') as f:
                    f.write(json.dumps(chunk_data).encode('utf-8'))
                
                chunks.append(chunk_path)
            
            # Save manifest
            manifest = {
                'tensor_id': self.uuid,
                'dimensions': self.dimensions,
                'rank': self.rank,
                'chunks': chunks,
                'total_chunks': len(chunks),
                'timestamp': time.time(),
                'data_format': 'sparse',
                'complex': data.get('complex', False)
            }
            
            manifest_path = f"{filepath}.manifest"
            with open(manifest_path, 'w') as f:
                json.dump(manifest, f, indent=2)
                
            return manifest_path
        else:
            # For dense tensors, it's more complicated - just use normal save with compression
            return self.save(filepath, compress=True)
    
    @classmethod
    def load_chunked(cls, manifest_path):
        """
        Load tensor from chunked files
        
        Args:
            manifest_path: Path to manifest file
            
        Returns:
            RecursiveTensor: Loaded tensor
        """
        # Load manifest
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        # Create tensor instance
        tensor = cls(
            dimensions=manifest['dimensions'],
            rank=manifest['rank']
        )
        
        # Load chunks
        if manifest['data_format'] == 'sparse':
            is_complex = manifest.get('complex', False)
            
            # Initialize empty data dictionary
            tensor.data = {}
            
            # Load each chunk
            for chunk_path in manifest['chunks']:
                with gzip.open(chunk_path, 'rb') as f:
                    chunk_data = json.loads(f.read().decode('utf-8'))
                
                # Add data from this chunk
                if is_complex:
                    # Complex data has [idx, real, imag] format
                    for item in chunk_data['data']:
                        tensor.data[tuple(item[0])] = complex(item[1], item[2])
                else:
                    # Real data has [idx, val] format
                    for item in chunk_data['data']:
                        tensor.data[tuple(item[0])] = item[1]
        
        # Set UUID from manifest
        tensor.uuid = manifest['tensor_id']
        
        return tensor
    
    def __add__(self, other):
        """
        Add two tensors (element-wise addition)
        
        Args:
            other: RecursiveTensor or scalar
            
        Returns:
            RecursiveTensor: Result of addition
        """
        result = RecursiveTensor(self.dimensions, 
                               rank=self.rank, 
                               dtype=self.dtype,
                               distribution=self.distribution,
                               sparsity=self.sparsity)
        
        if isinstance(other, RecursiveTensor):
            # Tensor + Tensor
            if self.rank != other.rank or self.dimensions != other.dimensions:
                raise ValueError("Tensors must have the same rank and dimensions for addition")
                
            if isinstance(self.data, dict) and isinstance(other.data, dict):
                # Both sparse
                result.data = self.data.copy()
                for idx, val in other.data.items():
                    result.data[idx] = result.data.get(idx, 0) + val
            elif isinstance(self.data, dict):
                # self is sparse, other is dense
                result.data = other.data.copy()
                for idx, val in self.data.items():
                    result.data[idx] += val
            elif isinstance(other.data, dict):
                # self is dense, other is sparse
                result.data = self.data.copy()
                for idx, val in other.data.items():
                    result.data[idx] += val
            else:
                # Both dense
                result.data = self.data + other.data
        else:
            # Tensor + scalar
            if isinstance(self.data, dict):
                # Sparse case
                result.data = {idx: val + other for idx, val in self.data.items()}
            else:
                # Dense case
                result.data = self.data + other
        
        # Update metadata
        result.operation_history = self.operation_history.copy()
        result.operation_history.append(('add', id(other) if isinstance(other, RecursiveTensor) else 'scalar'))
        result.metadata = self.metadata.copy()
        result.metadata["operations_count"] += 1
        result.metadata["modified"] = time.time()
        
        if isinstance(other, RecursiveTensor):
            result.metadata["description"] = f"Addition of {self.metadata['description']} and {other.metadata['description']}"
        else:
            result.metadata["description"] = f"Addition of {self.metadata['description']} and scalar {other}"
        
        return result
    
    def __mul__(self, other):
        """
        Multiply tensor by scalar or element-wise multiply with another tensor
        
        Args:
            other: scalar or RecursiveTensor
            
        Returns:
            RecursiveTensor: Result of multiplication
        """
        result = RecursiveTensor(self.dimensions, 
                               rank=self.rank, 
                               dtype=self.dtype,
                               distribution=self.distribution,
                               sparsity=self.sparsity)
        
        if isinstance(other, RecursiveTensor):
            if self.rank != other.rank or self.dimensions != other.dimensions:
                raise ValueError("Tensors must have the same rank and dimensions for element-wise multiplication")
                
            if isinstance(self.data, dict) and isinstance(other.data, dict):
                result.data = {}
                for idx in set(self.data.keys()).intersection(other.data.keys()):
                    result.data[idx] = self.data[idx] * other.data[idx]
            elif isinstance(self.data, dict):
                result.data = {}
                for idx, val in self.data.items():
                    if isinstance(other.data, np.ndarray) and all(i < other.data.shape[d] for d, i in enumerate(idx) if d < len(other.data.shape)):
                        result.data[idx] = val * other.data[idx]
            elif isinstance(other.data, dict):
                result.data = {}
                for idx, val in other.data.items():
                    if isinstance(self.data, np.ndarray) and all(i < self.data.shape[d] for d, i in enumerate(idx) if d < len(self.data.shape)):
                        result.data[idx] = self.data[idx] * val
            else:
                result.data = self.data * other.data
        else:
            if isinstance(self.data, dict):
                # Sparse case
                result.data = {idx: val * other for idx, val in self.data.items()}
            else:
                result.data = self.data * other
        
        result.operation_history = self.operation_history.copy()
        result.operation_history.append(('multiply', id(other) if isinstance(other, RecursiveTensor) else 'scalar'))
        result.metadata = self.metadata.copy()
        result.metadata["operations_count"] += 1
        result.metadata["modified"] = time.time()
        
        if isinstance(other, RecursiveTensor):
            result.metadata["description"] = f"Element-wise multiplication of {self.metadata['description']} and {other.metadata['description']}"
        else:
            result.metadata["description"] = f"Scalar multiplication of {self.metadata['description']} by {other}"
        
        return result

    def __getitem__(self, indices):
        """
        Get tensor element or slice
        
        Args:
            indices: tuple - indices to access
            
        Returns:
            Value or sub-tensor
        """
        if isinstance(self.data, dict):
            if isinstance(indices, tuple):
                return self.data.get(indices, 0)
            else:
                return self.data.get((indices,), 0)
        else:
            return self.data[indices]
    
    def __setitem__(self, indices, value):
        """
        Set tensor element or slice
        
        Args:
            indices: tuple - indices to set
            value: new value
        """
        if isinstance(self.data, dict):
            if value == 0:
                if indices in self.data:
                    del self.data[indices]
            else:
                self.data[indices] = value
        else:
            self.data[indices] = value
            
        self.metadata["modified"] = time.time()
    
    def __str__(self):
        """String representation of tensor"""
        if isinstance(self.data, dict):
            nnz = len(self.data)
            volume = self._volume()
            density = (nnz / volume) if volume > 0 else 0.0
            return f"RecursiveTensor(dimensions={self.dimensions}, rank={self.rank}, format=sparse, nnz={nnz}, density={density:.2e})"
        else:
            return f"RecursiveTensor(dimensions={self.dimensions}, rank={self.rank}, shape={self.data.shape}, format=dense)"
    
    def __repr__(self):
        """Detailed representation of tensor"""
        return str(self)
        
    def tucker_decomposition(self, ranks=None):
        """
        Perform Tucker decomposition of the tensor.
        
        Args:
            ranks: list - target rank for each mode
            
        Returns:
            tuple: (core_tensor, factor_matrices)
        """
        if ranks is None:
            ranks = [min(self.dimensions, 5)] * self.rank
            
        if isinstance(self.data, dict):
            dense_data = self._sparse_to_dense(self.data)
        else:
            dense_data = self.data
        if len(ranks) != self.rank:
            raise ValueError("Ranks must match the number of modes in the tensor")
        factors = []
        
        for mode in range(self.rank):
            unfolded = np.moveaxis(dense_data, mode, 0)
            unfolded = unfolded.reshape(dense_data.shape[mode], -1)
            
            U, _, _ = np.linalg.svd(unfolded, full_matrices=False)
            
            factors.append(U[:, :ranks[mode]])
        
        core = dense_data.copy()
        for mode, factor in enumerate(factors):
            core = np.tensordot(core, factor, axes=([0], [0]))
        return core, factors

    
    def to_mps(self, max_bond_dimension=None):
        """
        Convert tensor to Matrix Product State representation.
        
        Args:
            max_bond_dimension: int - maximum bond dimension
            
        Returns:
            list: MPS tensors
        """
        if isinstance(self.data, dict):
            dense_data = self._sparse_to_dense(self.data)
        else:
            dense_data = self.data
            
        mps_tensors = []
        
        current = dense_data
        
        for i in range(self.rank - 1):
            shape = current.shape
            current = current.reshape(shape[0], -1)
            
            U, S, V = np.linalg.svd(current, full_matrices=False)
            
            # Truncate if needed
            if max_bond_dimension and len(S) > max_bond_dimension:
                U = U[:, :max_bond_dimension]
                S = S[:max_bond_dimension]
                V = V[:max_bond_dimension, :]
            
            # Create MPS tensor
            mps_tensor = U.reshape(shape[0], -1)
            mps_tensors.append(mps_tensor)
            
            # Update current tensor
            current = np.diag(S) @ V
            current = current.reshape(-1, *shape[1:])
        
        # Add last tensor
        mps_tensors.append(current)
        
        return mps_tensors

    def enable_gradient_tracking(self):
        """
        Enable tracking of gradients for tensor operations.
        Useful for integration with neural networks.
        
        Returns:
            RecursiveTensor: Tensor with gradient tracking
        """
        try:
            import torch
            
            # Create gradient-enabled tensor
            result = RecursiveTensor(self.dimensions, 
                                    rank=self.rank, 
                                    dtype=self.dtype,
                                    distribution=self.distribution,
                                    sparsity=self.sparsity)
            
            if isinstance(self.data, dict):
                # Convert sparse tensor to PyTorch tensor with gradients
                indices = np.array(list(self.data.keys())).T
                values = np.array(list(self.data.values()))
                
                if indices.size > 0:
                    torch_indices = torch.LongTensor(indices)
                    torch_values = torch.FloatTensor(values)
                    
                    # Create sparse torch tensor
                    shape = tuple([self.dimensions] * self.rank)
                    torch_tensor = torch.sparse.FloatTensor(torch_indices, torch_values, shape)
                    torch_tensor = torch_tensor.requires_grad_()
                    
                    result.data = torch_tensor
                else:
                    result.data = {}
            else:
                # Convert dense tensor to PyTorch tensor with gradients
                torch_tensor = torch.tensor(self.data, dtype=torch.float32, requires_grad=True)
                result.data = torch_tensor
            
            # Mark that this tensor has gradient tracking
            result.metadata["has_gradients"] = True
            result.metadata["description"] = f"Gradient-enabled {self.metadata['description']}"
            
            return result
        except ImportError:
            logger.warning("PyTorch not available - gradient tracking requires PyTorch")
            return self

    def persistent_homology(self, max_dimension=1):
        """
        Compute persistent homology of the tensor.
        
        Args:
            max_dimension: int - maximum homology dimension
            
        Returns:
            dict: Persistence diagrams
        """
        try:
            import gudhi as gd
            
            if isinstance(self.data, dict):
                # Use sparse points as filtration
                points = np.array(list(self.data.keys()))
                values = np.array(list(self.data.values()))
            else:
                # Extract points from dense tensor
                points = np.array(np.where(np.abs(self.data) > 1e-6)).T
                values = self.data[tuple(points.T)]
            
            # Create a simplex tree
            st = gd.SimplexTree()
            
            # Add vertices
            for i, point in enumerate(points):
                st.insert([i], filtration=abs(values[i]))
            
            # Add edges based on proximity
            for i in range(len(points)):
                for j in range(i+1, len(points)):
                    # Use Euclidean distance for filtration
                    dist = np.linalg.norm(points[i] - points[j])
                    if dist < 2:  # Only connect nearby points
                        st.insert([i, j], filtration=dist)
            
            # Compute persistence
            st.persistence(min_persistence=0.01)
            
            # Get persistence diagrams
            diagrams = {}
            for dim in range(max_dimension + 1):
                pairs = st.persistence_pairs_in_dimension(dim)
                diagrams[dim] = np.array(pairs)
            
            return diagrams
        except ImportError:
            logger.warning("GUDHI not available - persistent homology requires GUDHI package")
            return None

    def to_gpu(self):
        """
        Move tensor to GPU for accelerated computation.
        Requires CuPy or PyTorch.
        
        Returns:
            RecursiveTensor: GPU-accelerated tensor
        """
        result = RecursiveTensor(self.dimensions, 
                               rank=self.rank, 
                               dtype=self.dtype,
                               distribution=self.distribution,
                               sparsity=self.sparsity)
        
        try:
            import cupy as cp
            
            if isinstance(self.data, dict):
                # For sparse tensors, we need to handle differently
                # Create COO format for cupy
                indices = list(self.data.keys())
                values = list(self.data.values())
                
                # Create dense tensor on GPU for now (sparse tensor support is limited)
                gpu_tensor = cp.zeros((self.dimensions,) * self.rank, dtype=self.dtype)
                for idx, val in zip(indices, values):
                    gpu_tensor[idx] = val
                    
                result.data = gpu_tensor
            else:
                # Move dense tensor to GPU
                result.data = cp.array(self.data)
                
            result.metadata["on_gpu"] = True
            result.metadata["description"] = f"GPU-accelerated {self.metadata['description']}"
            return result
        
        except ImportError:
            try:
                import torch
                
                if isinstance(self.data, dict):
                    # Create COO tensor for PyTorch
                    indices = np.array(list(self.data.keys())).T
                    values = np.array(list(self.data.values()))
                    
                    if indices.size > 0:
                        torch_indices = torch.LongTensor(indices).cuda()
                        torch_values = torch.FloatTensor(values).cuda()
                        
                        shape = tuple([self.dimensions] * self.rank)
                        result.data = torch.sparse.FloatTensor(torch_indices, torch_values, shape)
                    else:
                        result.data = {}
                else:
                    # Move dense tensor to GPU
                    result.data = torch.tensor(self.data).cuda()
                    
                result.metadata["on_gpu"] = True
                result.metadata["description"] = f"GPU-accelerated {self.metadata['description']}"
                return result
                
            except ImportError:
                logger.warning("Neither CuPy nor PyTorch available - GPU acceleration not possible")
                return self

    def visualize_tensor_network(self, show=True):
        """
        Visualize tensor as a network diagram.
        
        Args:
            show: bool - whether to display the plot
            
        Returns:
            matplotlib.figure.Figure: Network visualization
        """
        try:
            import networkx as nx
            import matplotlib.pyplot as plt
            
            # Create graph
            G = nx.Graph()
            
            # Add nodes for each dimension
            for i in range(self.rank):
                G.add_node(f"dim_{i}", type="dimension", size=self.dimensions)
            
            # Add central tensor node
            G.add_node("tensor", type="tensor", size=len(self.data) if isinstance(self.data, dict) else self.data.size)
            
            # Connect tensor to dimensions
            for i in range(self.rank):
                G.add_edge("tensor", f"dim_{i}")
            
            # Get positions using spring layout
            pos = nx.spring_layout(G)
            
            # Create plot
            plt.figure(figsize=(10, 8))
            
            # Draw dimension nodes as blue circles
            dim_nodes = [n for n in G.nodes if G.nodes[n]['type'] == 'dimension']
            nx.draw_networkx_nodes(G, pos, nodelist=dim_nodes, node_color='skyblue', 
                                  node_size=[G.nodes[n]['size'] * 10 for n in dim_nodes])
            
            # Draw tensor node as red square
            tensor_node = [n for n in G.nodes if G.nodes[n]['type'] == 'tensor']
            nx.draw_networkx_nodes(G, pos, nodelist=tensor_node, node_color='red', 
                                  node_shape='s', node_size=500)
            
            # Draw edges
            nx.draw_networkx_edges(G, pos, width=2.0, alpha=0.7)
            
            # Draw labels
            nx.draw_networkx_labels(G, pos, font_weight='bold')
            
            plt.title(f"Tensor Network Representation - Rank {self.rank}")
            plt.axis('off')
            
            if show:
                plt.show()
                
            return plt.gcf()
        
        except ImportError:
            logger.warning("NetworkX not available - tensor network visualization requires NetworkX")
            return None

    def to_hyperbolic_space(self, curvature=-1.0):
        """
        Transform tensor to hyperbolic space representation.
        Useful for hierarchical data modeling.
        
        Args:
            curvature: float - hyperbolic space curvature
            
        Returns:
            RecursiveTensor: Hyperbolic space representation
        """
        result = RecursiveTensor(self.dimensions, 
                               rank=self.rank, 
                               dtype=np.complex64,  # Hyperbolic space uses complex numbers
                               distribution=self.distribution,
                               sparsity=self.sparsity)
        dim_scale = np.asarray(self.dimensions, dtype=np.float64)
        
        # Define Poincaré ball model transformation
        def to_poincare(x):
            norm = np.linalg.norm(x)
            if norm >= 1.0:
                # Project to unit ball
                x = x / (norm + 1e-8)
            return x
        
        # Define hyperbolic distance
        def hyperbolic_distance(x, y):
            x_norm = np.linalg.norm(x)
            y_norm = np.linalg.norm(y)
            numerator = 2 * np.linalg.norm(x - y) ** 2
            denominator = (1 - x_norm**2) * (1 - y_norm**2)
            return np.arccosh(1 + numerator / (denominator + 1e-8))
        
        if isinstance(self.data, dict):
            # Transform sparse tensor
            result.data = {}
            
            # Get normalized indices
            indices = np.array(list(self.data.keys()))
            if indices.size > 0:
                # Normalize indices to be in [0,1] (elementwise against shape tuple)
                normalized_indices = indices / dim_scale
                
                # Transform to Poincaré ball model
                for idx, val in self.data.items():
                    norm_idx = np.array(idx, dtype=np.float64) / dim_scale
                    poincare_idx = to_poincare(norm_idx)
                    
                    # Store with original indices but hyperbolic value
                    magnitude = abs(val)
                    phase = np.angle(val) if np.iscomplexobj(val) else 0
                    
                    # Compute hyperbolic value using distance from origin
                    hyp_distance = hyperbolic_distance(poincare_idx, np.zeros_like(poincare_idx))
                    
                    # Create complex value with phase
                    hyp_val = magnitude * np.exp(1j * (phase + curvature * hyp_distance))
                    result.data[idx] = hyp_val
            
        else:
            # For dense tensor, we need to create a new tensor with hyperbolic coordinates
            result.data = np.zeros(self.data.shape, dtype=np.complex64)

            # Process each index (ndindex yields tuples; do not iterate a stacked array)
            for idx in np.ndindex(self.data.shape):
                norm_idx = np.array(idx, dtype=np.float64) / dim_scale
                poincare_idx = to_poincare(norm_idx)

                val = self.data[idx]
                magnitude = abs(val)
                phase = np.angle(val) if np.iscomplexobj(val) else 0

                # Compute hyperbolic value
                hyp_distance = hyperbolic_distance(poincare_idx, np.zeros_like(poincare_idx))
                hyp_val = magnitude * np.exp(1j * (phase + curvature * hyp_distance))

                result.data[idx] = hyp_val
        
        result.metadata["hyperbolic"] = True
        result.metadata["curvature"] = curvature
        result.metadata["description"] = f"Hyperbolic transformation of {self.metadata['description']}"
        
        return result

    def apply_temporal_convolution(self, kernel, time_axis=None):
        """
        Apply convolution along the temporal dimension.

        Default ``time_axis`` is the last axis. Capability layout is
        C[agent, capability, context, tick]; tick is last. Pass 0 explicitly
        only for a time-first tensor. Negative axes are normalized.

        Args:
            kernel: array - convolution kernel
            time_axis: int | None - axis representing time (None => last)

        Returns:
            RecursiveTensor: Result of temporal convolution
        """
        if self.rank < 1:
            raise ValueError("cannot convolve a rank-0 tensor")
        if time_axis is None:
            axis = self.rank - 1
        else:
            axis = int(time_axis)
            if axis < 0:
                axis = self.rank + axis
        if axis < 0 or axis >= self.rank:
            raise ValueError(f"time_axis {time_axis!r} out of rank {self.rank}")
        kernel = np.asarray(kernel)
        if kernel.size == 0:
            raise ValueError("convolution kernel must be non-empty")

        result = RecursiveTensor(
            self.dimensions,
            rank=self.rank,
            dtype=self.dtype,
            distribution=self.distribution,
            sparsity=self.sparsity,
        )

        if isinstance(self.data, dict):
            result.data = {}
            grouped_indices = {}
            for idx, val in self.data.items():
                non_time_idx = idx[:axis] + idx[axis + 1:]
                if non_time_idx not in grouped_indices:
                    grouped_indices[non_time_idx] = {}
                grouped_indices[non_time_idx][idx[axis]] = val

            for non_time_idx, time_values in grouped_indices.items():
                times = np.array(list(time_values.keys()))
                values = np.array(list(time_values.values()))
                sort_idx = np.argsort(times)
                times = times[sort_idx]
                values = values[sort_idx]
                convolved = np.convolve(values, kernel, mode='same')
                for i, t in enumerate(times):
                    full_idx = non_time_idx[:axis] + (t,) + non_time_idx[axis:]
                    if abs(convolved[i]) > 1e-10:
                        result.data[full_idx] = convolved[i]
        else:
            kernel_shape = [1] * self.rank
            kernel_shape[axis] = int(kernel.size)
            kernel_nd = np.reshape(kernel.astype(self.data.dtype, copy=False), kernel_shape)
            from scipy.signal import convolve
            result.data = np.asarray(
                convolve(self.data, kernel_nd, mode='same'),
                dtype=self.dtype,
            )
            result.dimensions = tuple(int(n) for n in result.data.shape)
            result.rank = result.data.ndim

        result.operation_history = self.operation_history.copy()
        result.operation_history.append(('temporal_convolution', axis))
        result.metadata = self.metadata.copy()
        result.metadata["description"] = f"Temporal convolution of {self.metadata['description']}"
        return result

    def visualize_3d_tensor_field(self, axes=(0, 1, 2), slice_indices=None, cmap='viridis', title=None, show=True):
        """
        Visualize 3D tensor field as a volumetric plot or isosurface.

        Args:
            axes: tuple - which three axes to use for 3D visualization
            slice_indices: dict - indices for other axes
            cmap: str - matplotlib colormap name
            title: str - plot title
            show: bool - whether to display the plot

        Returns:
            matplotlib.figure.Figure: Figure with 3D tensor field visualization
        """
        try:
            from mpl_toolkits.mplot3d import Axes3D
            import matplotlib.pyplot as plt
            from matplotlib.colors import Normalize

            if self.rank < 3:
                raise ValueError("Tensor must have rank >= 3 for 3D visualization")

            if slice_indices is None:
                slice_indices = {i: 0 for i in range(self.rank) if i not in axes}

            # Extract 3D slice
            if isinstance(self.data, dict):
                # For sparse tensors, create a 3D grid
                tensor_3d = np.zeros((self.dimensions, self.dimensions, self.dimensions))
                for idx, val in self.data.items():
                    if all(idx[ax] == slice_idx for ax, slice_idx in slice_indices.items()):
                        if all(idx[axis] < self.dimensions for axis in axes):
                            tensor_3d[idx[axes[0]], idx[axes[1]], idx[axes[2]]] = abs(val)
            else:
                slice_idx = tuple(slice(None) if i in axes else slice_indices.get(i, 0)
                                 for i in range(self.rank))
                tensor_3d = np.abs(self.data[slice_idx])

            fig = plt.figure(figsize=(12, 10))
            ax = fig.add_subplot(111, projection='3d')

            # Create meshgrid for 3D plotting
            x, y, z = np.meshgrid(range(self.dimensions), range(self.dimensions), range(self.dimensions), indexing='ij')

            # Flatten arrays for scatter plot
            x_flat = x.flatten()
            y_flat = y.flatten()
            z_flat = z.flatten()
            values_flat = tensor_3d.flatten()

            # Filter out zero values for cleaner visualization
            mask = values_flat > 1e-6
            x_flat = x_flat[mask]
            y_flat = y_flat[mask]
            z_flat = z_flat[mask]
            values_flat = values_flat[mask]

            if len(values_flat) > 0:
                # Normalize colors
                norm = Normalize(vmin=values_flat.min(), vmax=values_flat.max())
                colors = plt.cm.get_cmap(cmap)(norm(values_flat))

                # Create scatter plot
                scatter = ax.scatter(x_flat, y_flat, z_flat, c=values_flat,
                                   cmap=cmap, alpha=0.6, s=20)

                # Add colorbar
                plt.colorbar(scatter, ax=ax, shrink=0.8, label='Magnitude')

            ax.set_xlabel(f'Axis {axes[0]}')
            ax.set_ylabel(f'Axis {axes[1]}')
            ax.set_zlabel(f'Axis {axes[2]}')
            ax.set_title(title or f'3D Tensor Field Visualization - Axes {axes}')

            if show:
                plt.show()

            return fig

        except ImportError:
            logger.warning("matplotlib or mpl_toolkits not available - 3D visualization requires matplotlib")
            return None

    def visualize_tensor_evolution(self, evolution_steps=10, cmap='plasma', title=None, show=True):
        """
        Visualize tensor evolution over time or iterations.

        Args:
            evolution_steps: int - number of evolution steps to visualize
            cmap: str - matplotlib colormap name
            title: str - plot title
            show: bool - whether to display the plot

        Returns:
            matplotlib.figure.Figure: Figure with tensor evolution visualization
        """
        try:
            import matplotlib.pyplot as plt
            import matplotlib.animation as animation

            fig, axes = plt.subplots(2, 3, figsize=(15, 10))
            axes = axes.flatten()

            # Generate evolution data (simplified fractal iteration)
            evolution_data = [self.data.copy()]
            current_tensor = self

            for step in range(evolution_steps):
                # Apply simple evolution (could be fractal iteration, contraction, etc.)
                evolved = current_tensor.apply_function(lambda x: x * 0.9 + 0.1 * np.sin(step * 0.1))
                evolution_data.append(evolved.data)
                current_tensor = evolved

            def animate(frame):
                for i, ax in enumerate(axes):
                    ax.clear()

                    if frame < len(evolution_data):
                        data = evolution_data[frame]
                        if isinstance(data, dict):
                            # Convert sparse to dense for visualization
                            dense_data = np.zeros((self.dimensions, self.dimensions))
                            for idx, val in data.items():
                                if len(idx) >= 2 and idx[0] < self.dimensions and idx[1] < self.dimensions:
                                    dense_data[idx[0], idx[1]] = abs(val)
                        else:
                            dense_data = np.abs(data.reshape(self.dimensions, self.dimensions) if data.ndim > 1 else data)

                        im = ax.imshow(dense_data, cmap=cmap, aspect='equal')
                        ax.set_title(f'Step {frame}')
                        ax.axis('off')

                        if i == 0:  # Add colorbar to first subplot
                            plt.colorbar(im, ax=ax, shrink=0.8)

                fig.suptitle(title or f'Tensor Evolution - Frame {frame}/{len(evolution_data)-1}')

            # Create animation
            anim = animation.FuncAnimation(fig, animate, frames=len(evolution_data),
                                         interval=500, repeat=True)

            if show:
                plt.show()

            return fig

        except ImportError:
            logger.warning("matplotlib not available - tensor evolution visualization requires matplotlib")
            return None

    def visualize_phase_space(self, axes=(0, 1), resolution=50, title=None, show=True):
        """
        Visualize tensor in phase space representation.

        Args:
            axes: tuple - axes to use for phase space
            resolution: int - resolution for phase space grid
            title: str - plot title
            show: bool - whether to display the plot

        Returns:
            matplotlib.figure.Figure: Figure with phase space visualization
        """
        try:
            import matplotlib.pyplot as plt

            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

            # Extract data for phase space
            if isinstance(self.data, dict):
                values = np.array(list(self.data.values()))
                indices = np.array(list(self.data.keys()))
            else:
                values = self.data.flatten()
                indices = np.array(np.ndindex(self.data.shape))

            # Real vs Imaginary parts (for complex tensors)
            if np.iscomplexobj(values):
                real_parts = np.real(values)
                imag_parts = np.imag(values)

                # Phase space plot
                ax1.scatter(real_parts, imag_parts, alpha=0.6, s=10)
                ax1.set_xlabel('Real Part')
                ax1.set_ylabel('Imaginary Part')
                ax1.set_title('Complex Phase Space')
                ax1.grid(True, alpha=0.3)

                # Magnitude distribution
                magnitudes = np.abs(values)
                ax2.hist(magnitudes, bins=resolution, alpha=0.7, edgecolor='black')
                ax2.set_xlabel('Magnitude')
                ax2.set_ylabel('Frequency')
                ax2.set_title('Magnitude Distribution')
                ax2.grid(True, alpha=0.3)
            else:
                # For real tensors, show value distribution and spatial distribution
                ax1.hist(values, bins=resolution, alpha=0.7, edgecolor='black')
                ax1.set_xlabel('Value')
                ax1.set_ylabel('Frequency')
                ax1.set_title('Value Distribution')
                ax1.grid(True, alpha=0.3)

                # Spatial distribution (first two dimensions)
                if len(indices) > 0 and indices.shape[1] >= 2:
                    x_coords = indices[:, axes[0]] if axes[0] < indices.shape[1] else indices[:, 0]
                    y_coords = indices[:, axes[1]] if axes[1] < indices.shape[1] else indices[:, min(1, indices.shape[1]-1)]

                    scatter = ax2.scatter(x_coords, y_coords, c=values, cmap='viridis', alpha=0.6, s=20)
                    ax2.set_xlabel(f'Axis {axes[0]}')
                    ax2.set_ylabel(f'Axis {axes[1]}')
                    ax2.set_title('Spatial Distribution')
                    plt.colorbar(scatter, ax=ax2, shrink=0.8, label='Value')

            fig.suptitle(title or 'Tensor Phase Space Analysis')

            if show:
                plt.show()

            return fig

        except ImportError:
            logger.warning("matplotlib not available - phase space visualization requires matplotlib")
            return None

    def visualize_correlation_matrix(self, title=None, show=True):
        """
        Visualize correlation matrix between tensor dimensions.

        Args:
            title: str - plot title
            show: bool - whether to display the plot

        Returns:
            matplotlib.figure.Figure: Figure with correlation matrix visualization
        """
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns

            # Convert tensor to matrix form for correlation analysis
            if isinstance(self.data, dict):
                # For sparse tensors, create unfolded matrices
                unfolded_matrices = []
                for mode in range(self.rank):
                    matrix = np.zeros((self.dimensions, self.dimensions**(self.rank-1)))
                    for idx, val in self.data.items():
                        row = idx[mode]
                        col = sum(idx[i] * (self.dimensions**i) for i in range(self.rank) if i != mode)
                        if col < matrix.shape[1]:
                            matrix[row, col] = val
                    unfolded_matrices.append(matrix)
            else:
                # For dense tensors, unfold along each mode
                unfolded_matrices = []
                for mode in range(self.rank):
                    unfolded = np.moveaxis(self.data, mode, 0)
                    shape = unfolded.shape
                    matrix = unfolded.reshape(shape[0], -1)
                    unfolded_matrices.append(matrix)

            # Compute correlations between unfolded matrices
            correlations = np.zeros((self.rank, self.rank))
            for i in range(self.rank):
                for j in range(self.rank):
                    if i != j:
                        # Compute correlation between unfolded matrices
                        mat1 = unfolded_matrices[i]
                        mat2 = unfolded_matrices[j]

                        # Flatten and compute correlation
                        flat1 = mat1.flatten()
                        flat2 = mat2.flatten()

                        if np.std(flat1) > 0 and np.std(flat2) > 0:
                            corr = np.corrcoef(flat1, flat2)[0, 1]
                            correlations[i, j] = corr
                        else:
                            correlations[i, j] = 0
                    else:
                        correlations[i, j] = 1.0

            # Visualize correlation matrix
            fig, ax = plt.subplots(figsize=(10, 8))
            sns.heatmap(correlations, annot=True, cmap='coolwarm', center=0,
                       xticklabels=[f'Mode {i}' for i in range(self.rank)],
                       yticklabels=[f'Mode {i}' for i in range(self.rank)],
                       ax=ax)
            ax.set_title(title or 'Tensor Mode Correlation Matrix')

            if show:
                plt.show()

            return fig

        except ImportError:
            logger.warning("matplotlib and/or seaborn not available - correlation matrix visualization requires matplotlib and seaborn")
            return None

    def create_comprehensive_visualization_dashboard(self, save_path=None):
        """
        Create a comprehensive visualization dashboard for the tensor.

        Args:
            save_path: str - path to save the dashboard (optional)

        Returns:
            dict: Dictionary containing all visualization figures
        """
        dashboard = {}

        try:
            # 1. Basic slice visualization
            dashboard['slice'] = self.visualize_slice(show=False)

            # 2. Eigenspectrum
            dashboard['eigenspectrum'] = self.visualize_eigenspectrum(show=False)

            # 3. Value distribution
            dashboard['density'] = self.visualize_density(show=False)

            # 4. Operation history
            dashboard['history'] = self.plot_operation_history(show=False)

            # 5. Tensor network (if rank >= 2)
            if self.rank >= 2:
                dashboard['network'] = self.visualize_tensor_network(show=False)

            # 6. Phase space analysis
            if self.rank >= 2:
                dashboard['phase_space'] = self.visualize_phase_space(show=False)

            # 7. Correlation matrix (if rank >= 2)
            if self.rank >= 2:
                dashboard['correlation'] = self.visualize_correlation_matrix(show=False)

            # 8. 3D visualization (if rank >= 3)
            if self.rank >= 3:
                dashboard['3d_field'] = self.visualize_3d_tensor_field(show=False)

            # Save dashboard if path provided
            if save_path:
                import matplotlib.pyplot as plt
                for name, fig in dashboard.items():
                    if fig is not None:
                        fig.savefig(f"{save_path}/tensor_{name}.png", dpi=300, bbox_inches='tight')
                        plt.close(fig)

            return dashboard

        except Exception as e:
            logger.warning(f"Error creating visualization dashboard: {e}")
            return dashboard

    # Add layout property for matplotlib compatibility
    @property
    def layout(self):
        """
        Layout property for matplotlib compatibility.
        Returns basic layout information about the tensor.
        """
        return {
            'dimensions': self.dimensions,
            'rank': self.rank,
            'shape': self.shape,
            'dtype': self.dtype,
            'sparsity': self.sparsity,
            'size': len(self.data) if isinstance(self.data, dict) else self.data.size
        }

    def synchronize_with_breath(self, phase) -> Dict[str, Any]:
        """
        Synchronize recursive tensor with breath phase.
        
        Args:
            phase: BreathPhase enum value from SacredBreathSynchronizer
            
        Returns:
            Dict containing synchronization results
        """
        # Import constants if not already available
        try:
            from holy_tau_phase import PHI, SACRED_RATIO, BreathPhase
        except ImportError:
            # Fallback constants if holy_tau_phase is not available
            PHI = (1 + np.sqrt(5)) / 2
            SACRED_RATIO = PHI / (2 * np.pi)
            # Define BreathPhase enum locally if needed
            class BreathPhase:
                INHALE = "INHALE"
                PAUSE_RISING = "PAUSE_RISING"
                HOLD = "HOLD"
                PAUSE_FALLING = "PAUSE_FALLING"
                EXHALE = "EXHALE"
                REST = "REST"
                DREAM = "DREAM"
        
        # Phase-specific scaling factors (aligned with sacred ratios)
        phase_factor = {
            BreathPhase.INHALE: PHI,
            BreathPhase.PAUSE_RISING: PHI**0.5,
            BreathPhase.HOLD: 1.0,
            BreathPhase.PAUSE_FALLING: PHI**(-0.5),
            BreathPhase.EXHALE: PHI**(-1),
            BreathPhase.REST: SACRED_RATIO,
            BreathPhase.DREAM: PHI**2
        }.get(phase, 1.0)
        
        # Apply phase-modulated transformation to tensor data
        if isinstance(self.data, dict):
            # Sparse tensor case
            for idx, val in self.data.items():
                self.data[idx] = val * phase_factor
        else:
            # Dense tensor case
            self.data *= phase_factor
        
        # Recompute eigenstates if needed (for stability during HOLD/DREAM phases)
        if hasattr(phase, 'name') and phase.name in ['HOLD', 'DREAM']:
            self.compute_eigenstates()
        
        # Update metadata
        self.metadata["operations_count"] += 1
        self.metadata["modified"] = time.time()
        self.metadata["description"] = f"Synchronized with breath phase {phase}"
        
        return {
            'phase': phase.name if hasattr(phase, 'name') else str(phase),
            'phase_factor': phase_factor,
            'eigenstate_stability': 0.0  # Placeholder, eigenstates not cached in this implementation
        }


# Example usage
if __name__ == "__main__":
    # Example 1: Create and visualize a recursive tensor
    tensor = RecursiveTensor(
        dimensions=(10, 10, 10),
        rank=3,
        dtype=np.float32,
        distribution='uniform',
        sparsity='dense'
    )

    print("Created tensor:", tensor)
    print("Tensor layout:", tensor.layout)

    # Example 2: Comprehensive visualization
    try:
        dashboard = tensor.create_comprehensive_visualization_dashboard()
        print(f"Created {len(dashboard)} visualizations")
    except Exception as e:
        print(f"Visualization error: {e}")
