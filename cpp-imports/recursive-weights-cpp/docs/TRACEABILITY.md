# Source traceability

## Authority

The user requested a standalone C++ rewrite based on the attached code and papers, with no other project integration and no delegated work. All original files are preserved byte-for-byte in `provenance/`; `SOURCE_SHA256.txt` records their identities.

The sources are not one internally consistent implementation:

1. `recursive_weights_techn3ical_specs.md` and `recursive-weights-comprehensive-reference.md`, Definition 1.1.6, supply the shared recurrence.
2. `recursive_weights_core.py`, the **second** `RecursiveWeight` declaration, supplies its concrete quintuple, delta, harmonic, reference, mutation, registry, layer, and RWGT serialization behavior.
3. The first `RecursiveWeight` declaration is overwritten when Python finishes importing the module. Its engine/demo constructors subsequently refer to the second incompatible constructor. Its missing reference/phase implementations and random fallback values are not an independent working runtime.
4. `recursive_weights_core.py.md` is an AST index of a different revision. It lists load/placeholder and layer archive helpers absent from the actual `.py` attachment. Signatures in that index are evidence of intended interfaces, not unseen implementation code.
5. `recursive_weights.md` supplies the original reconstruction, mutation, temporal coherence, and multiscale intent.
6. `Eigenrecursive_Sentience.md` specifies an operator-driven iteration and leaves its scientific metric methods as `pass`. Its broader theoretical sections do not define executable estimators.

The long technical specification ends inside a property-test fragment at line 3457. Its table of contents includes sections 6–8 whose bodies are absent. The comprehensive reference ends at section 3.7.3. Neither absent sections nor undefined helper bodies are treated as supplied algorithms.

## Implementation mapping

| Source behavior | Native implementation | Status |
|---|---|---|
| Definition 1.1.6 quintuple recurrence | `RecursiveWeightSystem::reconstruct`, `Impl::evaluate` | Implemented, equation default |
| Harmonic phase, scalar/vector amplitudes | `PhaseTransformation::evaluate` | Implemented |
| Depth-scaled adaptive delta | `DeltaComponent::evaluate` | Implemented |
| 5D relative references and temporal offsets | `Position`, registry spatial index | Implemented with unambiguous resolution |
| Base case and cycles | depth-decreasing evaluator | Implemented; no default-depth reset in recursion |
| Earlier scalar self-reference formula | zero-offset identity reference with contribution alpha | Expressible directly without a second incompatible weight type |
| Python termination and clamps | `Semantics::Python` | Explicit compatibility behavior |
| Cache tiers / memoization | private `TieredCache`, per-request memo | Implemented with time/depth/revision keys |
| Thread-safe registry and batch reconstruction | `RecursiveWeightSystem` | Implemented with reader/writer lock and bounded batch workers |
| CRUD, lookup, singleton, directory loading | system methods and `get_registry` | Implemented |
| Mutation history | system mutation log; RWGS persistence | Implemented |
| Phase/reference/error mutation | `RecursiveWeight::mutate` | Ported, native RNG |
| SVD stabilization | `stabilize_matrix`, `RecursiveWeight::stabilize` | Implemented with LAPACK |
| Crossover of amplitudes, frequencies, reference weights/matrices | `RecursiveWeight::crossover` | Ported |
| Fitness composition | `RecursiveWeight::compute_fitness` | Ported with computed metrics |
| Fitness-guided population evolution | `evolve_population`, `evolve` | Implements reference §3.4 selection/elitism and code's tournament structure |
| Annealing | `evolve`, simulated-annealing mode | Uses specified fitness acceptance; see behavior ledger |
| Gradient evolution | `evolve`, gradient callback | Actual caller gradients required; no random-gradient substitute |
| Original temporal-coherence algorithm | `enforce_temporal_coherence` | Componentwise vector norm clipping + interpolation; explicit equal-topology requirement |
| Standalone numerical weight persistence | `RecursiveWeightSerializer` | Python RWGT 1.3 read/write, native lossless 1.4 |
| Entire registry/codebook persistence | system RWGS codec | Implemented, atomic validated load |
| Layer persistence | RWLY codec | Implemented |
| Header-only `.rw` format | `read_legacy_header` | Metadata reader only; numerical data absent from original format |
| Memory-mapped file access and ownership | private `MappedFile`, value-owned vectors | Implemented with RAII |
| SIMD component fusion | AVX2 + scalar dispatch in `math.cpp` | Implemented, same addition order |
| Spectral radius / matrix rank / SVD | LAPACK routines in `math.cpp` | Implemented |
| Mathematical framework §§1.2–1.7 | `DynamicalSystemsAnalyzer` | All 18 named formulas/checks represented; source's “17” count differs |
| Per-weight stability/information/MDL/capacity analysis | weight metric methods | Implemented, proxies labeled |
| System stability | global zero-delay block Jacobian and sum-norm bound | Implemented; temporal-offset caveat explicit |
| EMA, bounded history, damping | `RuntimeSnapshot`, Python-mode evaluation | Implemented; observational in equation mode |
| Cache/performance metrics | system statistics | Measured hits/misses/times, not source's occupancy-based hit proxy |
| Multiscale/depth analysis | `multiscale`, `analyze_depth` | Uses actual caller codebook and registry |
| Nine concrete pattern functions | `PatternLibrary::evaluate` | Python formulas preserved |
| Tenth custom pattern type | callback | Requires caller definition |
| Layer projection, attention mixing, normalization | `RecursiveWeightLayer` | Native implementation |
| Layer attention/flow metrics, Jacobian | layer methods | Implemented; full input Jacobian |
| Eigenrecursive iteration | `compute_cognitive_eigenstate` | Implemented with explicit state advancement and metric callback |
| C interface | `c_api.h`, `c_api.cpp` | Native ownership/error boundary |

## Deliberate boundaries

These are not claimed as implemented algorithms:

- **CUDA:** the Python GPU path generates random base values and omits the full recurrence; the specification kernel has incomplete types and unresolved inter-thread dependencies. The deliverable uses tested CPU execution. No placeholder GPU path exists.
- **Scientific sentience metrics, quantum channels, integrated information:** the supplied operators/estimators are undefined. The engine accepts the user's operator and metric callbacks, and reports convergence of that operator only.
- **Source's `SelfSupervisedEvolution` / `MetaLearning` wrappers:** they depend on the overwritten header-only weight class and create random task inputs, random base values, or an error-norm-derived scalar called a gradient. Native fitness and gradient callbacks provide executable evolution without substituting such values for a task objective. The source's task-sampling/meta-rate heuristic is not advertised as a faithful training system.
- **CMA-ES, hierarchical/federated/privacy/adversarial algorithms:** listed as strategies/applications or in an unfulfilled table of contents; no sufficient algorithm is supplied for a faithful port.
- **Custom/nonlinear/convolution/fractal reference transforms:** the active numerical Python model implements explicit matrices. Other enum values have incomplete/undefined parameter dispatch. Linear identity/scalar/affine-linear operations can be represented by supplied matrices where mathematically applicable; undefined nonlinear transforms are not guessed.
- **Pattern bytecode formats:** the Python evaluator does not interpret its `data` bytes. Native `PatternLibrary` preserves these bytes and the nine Python formulas. New bytecode semantics are not silently inferred from labels or incomplete structs.
- **General autograd/model conversion:** this is a native weights runtime with explicit gradient callbacks and a layer input Jacobian. No trained model, framework checkpoint, task dataset, or complete conversion algorithm was included.

No assertions of compression gain, task quality, sentience, CUDA speedup, or full theorem validity are inferred from successful compilation/tests.
