# Behavioral decisions and repairs

## Recurrence

The default uses the mathematical recurrence with all five components. Depth counts the remaining reference expansions. At zero it evaluates base + delta(0) + phase(time) + error. It never substitutes the default depth when a recursive call reaches zero. Cycles and self-references therefore terminate without changing the graph.

The Python's named keys (`weight_0`) do not match the position strings used for reference lookups. Native keys remain caller-controlled, while a separate spatial index resolves `T + relative_position`. More than one weight may occupy a position, but a reference to such a position is rejected as ambiguous. Missing references throw unless explicitly configured to skip. All reference matrices must be exactly d×d; truncation/padding is not used to disguise a malformed model.

## Equation and Python modes

| Operation | Equation default | Python compatibility |
|---|---|---|
| Phase/delta clamp | None; finite result required | [-1000,1000] |
| Explicit self-reference | Evaluated with depth minus one | Suppressed |
| Early termination | Requested finite depth respected | max weighted Frobenius norm / reference count heuristic |
| Error preservation | Additive vector | Additive, then whole output may be clamped to error-correction scalar |
| Effective value clamp | None; finite result required | [-10000,10000] |
| Periodic stability intervention | Metrics/history only | Clamp then damping factor |
| EMA | Recorded, not substituted for output | Recorded before periodic damping, like source |
| Caching | Time/depth/revision-aware | Disabled for stateful evaluations; available when history disabled |

The later Python `_compute_stability_metrics` definition shadows the earlier comprehensive one. Its stored spectral-radius object therefore remains at default zero. Python-mode output does not introduce the inactive 0.9 spectral-radius scale. Analysis APIs still compute actual metrics rather than returning fabricated positive fallback values.

For periodic guards, the native implementation uses actual singular-value spectral norms instead of the source's randomized power-iteration estimate. This affects guard decisions on non-normal matrices and is explicit. Histories are bounded to 64 effective states and 256 guard records. Cache hits are not counted as new computed states. Mutation invalidates dependent caches and resets runtime histories so stale state is not assigned to a changed model.

## Cache and concurrency

A cache key includes registry key, remaining depth, exact finite time bits, semantic mode, system revision, and strict-reference mode. Both +0 and -0 map to the same time key. Any committed weight/codebook mutation invalidates all tiers, including indirect dependents. Per-request memoization shares repeated subproblems. Cache values are owned copies, never borrowed mutable buffers.

The registry holds one shared lock during a batch or single evaluation; writers hold the exclusive lock. Cache and history have separate mutexes. Recursion never reacquires the registry lock. Python stateful batches execute sequentially to make guard history order deterministic. Equation batches use a bounded number of workers, with exceptions returned to the caller instead of zero-tensor substitutions. Layer projection/norm parameter mutation is caller-synchronized; the registry alone is internally synchronized.

## Mutation and evolution

Phase mutation ports noise scales, frequency/amplitude clamps, and signed `fmod` offsets. Reference mutation ports contribution clipping and SVD singular-value clipping at 0.95. Pattern mutation retains the later Python's error-vector mutation behavior. Parameters that the Python declares but does not use are retained as metadata; they do not acquire invented semantics.

The native RNG is `std::mt19937` with local normal distributions. A seed reproduces a result within the same native toolchain; it does not reproduce PyTorch/NumPy random streams or promise identical `normal_distribution` output across C++ standard libraries.

The supplied reference explicitly requires fitness-based selection and elitism. The later Python's genetic method ignores fitness and returns a random candidate. Native evolution implements the described selection. Annealing accepts improvements and uses exp((candidate-current)/temperature) for worse candidates, implementing the reference's stated strategy; the exact acceptance expression is a conventional completion of that strategy, not an equation quoted from the paper. Gradient descent accepts a caller gradient for the two parameter groups updated by the Python method (base phase and reference contributions); it does not fabricate random gradients. Momentum uses the declared parameter. Adaptive-mutation distributions remain undefined and are rejected if requested.

Mutation is copy-first. Source stabilization is applied; if it still fails the spectral criterion, the candidate is rejected rather than silently committed. Crossover validates harmonic shapes. Temporal coherence operates on equal-topology successive weights: vector deltas are norm-clipped by the caller threshold, then interpolated with the caller lambda. This makes the original abstract `magnitude`, `interpolate`, and continuous-reference operations explicit; it is not presented as a uniquely specified binary-level algorithm.

## Analysis

The scalar fixed-point expression is exposed as such. The weight's `compute_fixed_point_estimate` uses the Python mean-Frobenius contraction **proxy**, not an exact solution to arbitrary coupled matrix equations. `contraction_bound` separately supplies the sum of weighted Frobenius norms. Global system analysis builds the actual block reference matrix for zero-delay analysis; it does not infer global stability from the maximum of per-weight radii. Temporal offsets are reported and not certified by that zero-delay radius.

The supplied self-similarity ratio equals one for every nonzero matrix (numerator and denominator are the same squared Frobenius norm). That expression is retained, not replaced with a new similarity metric. Histogram-density entropy and correlation-based mutual information remain explicitly labeled proxies; undefined correlations are NaN, displayed as JSON null. Capacity/universal-approximation/complexity diagnostics are not theorem-proving procedures. Actual saved file sizes must be used for empirical storage claims.

## Persistence

Python RWGT 1.3 omitted scale, delta, flags, and config. Native RWGT 1.4 preserves them. Writing legacy 1.3 rejects non-default scale/delta/flags; its config is necessarily external. Float32 reference coefficients and float32 positional tensors follow the Python wire format; coordinates not exactly representable as float32 are rejected on save. Native in-memory coordinates are signed int32. Read validates SHA-256, ranks, lengths, counts, finite values, full payload consumption, and shapes before registry mutation.

Raw `.rw` headers contain metadata only. Neither dimension nor base/phase/matrix/error payloads can be reconstructed from those 64 bytes. They are readable as metadata and never turned into fabricated neutral/random weights.
