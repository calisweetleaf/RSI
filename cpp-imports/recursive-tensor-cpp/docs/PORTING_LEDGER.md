# Porting ledger — recursive_tensor.py v2.1.0 → C++17

Rule: keep intentional semantics, fix bugs. "Parity" = `tests/parity/parity.py`
(REF = matches Python, TRUTH = matches NumPy/SciPy where Python is wrong;
divergences marked "observed" were measured, not assumed).

| Area | Python behaviour | C++ behaviour | Parity |
|---|---|---|---|
| Storage | dense ndarray, dict, or scipy csr for rank ≤ 2 | dense vector or one sparse hash map (linear offset → value) for every rank | — |
| Rank-0 | volume ambiguous | volume 1 | — |
| Op side effects | result ops mutate the *source* history/metadata | source untouched; result carries history | — |
| contract | tensordot / dict join | GEMM via permute; sparse hash join; mixed direct | REF dense/complex; TRUTH sparse |
| expand | leading modes, data at index 0 | same | REF |
| project | row-normalised basis, moveaxis | same | REF dense + sparse |
| transform | raises (int vs tuple compare); sparse summed independent axes | per-axis n-mode products, composed | TRUTH; reference raises (observed) |
| embed | output dims not honest | explicit `extra_shape` | — |
| fractal | dense path has no per-element escape | per-element escape at radius 2 | REF (non-escaping) |
| eigenstates | symmetrises only if not allclose; sparse matricised column-major | always Hermitian part (flag set), row-major, Rayleigh check + 1 inverse-iteration refine; axes must cover all; k ≥ 1 | REF sym / non-sym / complex / SVD |
| normalize | matrix-norm bug for rank 2 | entrywise norms | — |
| entropy | dense drops v ≤ 0, sparse keeps them | unified over \|v\| | REF positive; TRUTH mixed (Python off 0.55, observed) |
| density | numpy histogram density | same | REF |
| compatibility | as written | same | REF dense + sparse |
| temporal conv | sparse path ignores gaps | exact convolution across gaps | REF dense odd/even/axis0; TRUTH sparse (Python off 0.81, observed) |
| hyperbolic | complex64 result | complex of source precision | REF (2e-6, Python's complex64) |
| to_mps | invalid cores | proper TT-SVD cores (r, d, r′) + from_mps | TRUTH round trip |
| tucker | default ranks TypeError | default min(extent, 5), HOSVD | TRUTH reconstruction |
| homology | gudhi | union-find H0 with filtration max(dist, f_u, f_v), optional H1; returns (birth, death) | — |
| scalar add | on sparse | nonzero scalar densifies (honest) | — |
| references | not implemented | whitepaper Def 3 / Thm 2: Gauss-Seidel settle to fixed point | — |
| provenance | unbounded | history cap 4096, description cap 512 | — |
| serialization | JSON / gzip / pickle / chunked | RTNZ v2 `.rta` binary only | numpy↔C++ round trip exact |

Omitted: matplotlib visualisation, torch/GPU, networkx, gradient tracking,
`synchronize_with_breath`.
