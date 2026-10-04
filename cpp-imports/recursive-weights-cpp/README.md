# Recursive Weights — native C++ runtime

A standalone C++17 implementation of Daeron's Recursive Weights material supplied on 2026-10-02. The six original inputs are preserved in `provenance/`. This library has no Python or PyTorch runtime dependency.

The implementation follows Definition 1.1.6:

$$W(i,t)=C[B]\,s+\Delta_i+\sum_j c_jR_jW_j(i-1,t-\tau_j)+\Phi(t)+\varepsilon$$

$$\Phi(t)=\Phi_0+\sum_h a_h\sin(\omega_ht+\phi_h),\qquad
\Delta_i=\Delta_0\,q^i\odot A.$$

It includes recursive graph evaluation, signed 5D spatial references, temporal offsets, vector/scalar harmonics, depth-dependent deltas, error preservation, mutation and evolutionary search, spectral/SVD analysis, a native mixing layer, persistent archives, C and C++ interfaces, a CLI, and tests.

## Build on Linux

Dependencies: a C++17 compiler, Make, LAPACK/BLAS runtime libraries, and OpenSSL development headers. On Ubuntu/Debian the development packages are `build-essential liblapack-dev libblas-dev libssl-dev`; CMake is optional.

```bash
make -j2
make test
```

Outputs:

- `build/librw.a`: static C++ library.
- `build/librw.so`: shared library, including a C ABI.
- `build/rw`: native CLI.

The Makefile can link installed versioned LAPACK/BLAS runtime libraries even without their development symlinks. For other distributions, override `LDLIBS` or use CMake:

```bash
cmake -S . -B cmake-build -DCMAKE_BUILD_TYPE=Release
cmake --build cmake-build -j2
ctest --test-dir cmake-build --output-on-failure
```

The verified platform is Linux x86-64. POSIX memory mapping and atomic file replacement are used. CMake is supplied; validation in this environment used Make.

## Run

```bash
./build/rw demo example.rwgs
./build/rw inspect example.rwgs
./build/rw evaluate example.rwgs a 3 1.0
```

`demo` creates a deterministic example, not a trained model. No trained weights or codebook were supplied with the source material.

To package existing numerical weights, supply their real codebook as a headerless CSV with one vector per row:

```bash
./build/rw pack codebook.csv weights_directory model.rwgs
./build/rw evaluate model.rwgs weight_0 3 1.0
```

`pack` reads `.rwgt` files, uses each filename stem as its registry key, validates spatial references, and writes a complete archive. `inspect-weight FILE` prints analysis of an individual weight. `convert-weight INPUT OUTPUT` reads Python RWGT 1.3 and writes lossless native RWGT 1.4. `inspect-legacy FILE` reads the older 64-byte metadata-only header; it cannot reconstruct numerical components that were never written.

## C++ use

```cpp
#include <rw/runtime.hpp>

rw::RecursiveWeightSystem system;
system.set_codebook(rw::Matrix(1, 2, rw::Vector{1, 2}));
auto weight = rw::RecursiveWeight::neutral(2);
weight.recursive_refs.push_back({{}, 0.5, rw::Matrix::identity(2), 0});
system.register_weight("self", weight);
rw::EvaluationOptions options;
options.depth = 3;
auto value = system.reconstruct("self", options); // [1.875, 3.75]
system.save("system.rwgs");
```

All weights are copied into the registry. Reading a weight returns a copy; call `register_weight` to commit an edited copy. This gives cache invalidation and concurrency a definite mutation boundary. `mutate_weight` performs and records a transaction. `evolve_weight` runs caller fitness/gradient callbacks without holding registry locks and rejects the commit if the system changed meanwhile.

The C ABI is in `include/rw/c_api.h`. It copies inputs, writes to caller-owned output buffers, catches exceptions, and exposes a thread-local error message. The native library owns no Python interpreter.

## Numerical behavior

`Semantics::Equation` is the default and implements the supplied recurrence directly. Depth zero is a real base case. Self-references and cycles are permitted because every edge decreases depth. Error preservation is additive. Unresolvable references throw by default; set `strict_references=false` for the Python's missing-reference skip behavior.

`Semantics::Python` explicitly enables the later Python class's phase/delta clamps, early termination heuristic, self-reference suppression, and effective-weight error clamp. It also enables periodic damping when history tracking is active. This mode repairs addressing, malformed shapes, and concurrency rather than reproducing stale cache entries or silent random/zero substitutes. It is not bug-for-bug emulation. See `docs/SEMANTICS.md` for every material difference.

Vectors/matrices and recurrence outputs are FP32. LAPACK spectral/SVD analysis uses FP64 workspaces for numerical robustness. AVX2 component addition is selected at runtime, with scalar fallback. Batch reconstruction uses bounded native worker threads. The delivered acceleration path is CPU; there is no claimed working CUDA backend.

The layer computes projection → softmax mixing over reconstructed weights → residual addition → layer normalization. Input shape `[batch, sequence, input_dim]` is represented as a contiguous matrix `[batch*sequence, input_dim]`. Output rows preserve that order. Its full per-token input Jacobian is analytic and tested against finite differences. It is an inference/runtime layer, not a replacement for the entire PyTorch autograd engine.

## Validation and source authority

```bash
make test
python3 tests/differential.py  # NumPy required only for this independent test
make sanitize                # ASan + UBSan; rebuild release afterward
```

Read:

- `docs/TRACEABILITY.md`: source-to-implementation mapping, precedence, and scope boundaries.
- `docs/SEMANTICS.md`: repairs and explicit behavior decisions.
- `docs/FORMAT.md`: standalone archive layouts and compatibility.
- `docs/VALIDATION.md`: measured test results and their limits.

The mathematical diagnostic formulas are implemented as formulas, with proxy/heuristic labels where appropriate. Executing a formula is not presented as proving the associated theorem. Undefined scientific operators in the eigenrecursive paper are caller callbacks; no substitute consciousness metric has been invented.
