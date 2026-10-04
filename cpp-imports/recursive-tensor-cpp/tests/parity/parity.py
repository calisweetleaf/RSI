"""Parity harness: Python reference (recursive_tensor.py) and NumPy ground truth
vs the C++ port, with every tensor crossing the boundary as .rta.

    python3 tests/parity/parity.py <path/to/recursive_tensor.py> <parity_runner binary>

Each case records which oracle it is checked against:
  REF    -- the Python reference implementation (semantics preserved)
  TRUTH  -- NumPy/SciPy ground truth, used where the reference is broken and
            the port intentionally diverges (see docs/PORTING_LEDGER.md).
Divergent reference outputs are still computed and reported as INFO lines so
the divergence is observed, not assumed.
"""
import importlib.util
import os
import subprocess
import sys
import tempfile
import warnings

import numpy as np
from scipy.signal import convolve

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "python"))
import rta_numpy as rn  # noqa: E402

warnings.filterwarnings("ignore")
import matplotlib  # noqa: E402

matplotlib.use("Agg")

ref_path, runner = sys.argv[1], sys.argv[2]
spec = importlib.util.spec_from_file_location("recursive_tensor", ref_path)
RT_MOD = importlib.util.module_from_spec(spec)
spec.loader.exec_module(RT_MOD)
RT = RT_MOD.RecursiveTensor

rng = np.random.default_rng(20260922)
work = tempfile.mkdtemp(prefix="rta_parity_")
manifest, checks = [], []


def py_dense(arr):
    t = RT(arr.shape, dtype=arr.dtype, distribution="uniform", sparsity=0.0)
    t.data = arr.copy()
    t.dimensions, t.rank = arr.shape, arr.ndim
    return t


def py_sparse(arr):
    t = py_dense(arr)
    t.data = {tuple(int(i) for i in idx): arr[idx] for idx in zip(*np.nonzero(arr))}
    return t


def put(name, arr, sparse=False):
    if sparse:
        lin = np.flatnonzero(arr)
        rn.save_sparse(os.path.join(work, name), arr.shape, lin, arr.reshape(-1)[lin])
    else:
        rn.save(os.path.join(work, name), arr)
    return name


def case(label, oracle, line, out, expected, tol, info=None, cmp=None):
    manifest.append(line)
    checks.append((label, oracle, out, np.asarray(expected), tol, info, cmp))


def rand(shape, dtype=np.float64, density=1.0):
    a = rng.standard_normal(shape)
    if np.issubdtype(dtype, np.complexfloating):
        a = a + 1j * rng.standard_normal(shape)
    a = a.astype(dtype)
    if density < 1.0:
        a[rng.random(shape) > density] = 0
    return a


def dense_of(pyt):
    return pyt.to_dense_array() if isinstance(pyt.data, dict) else pyt.data


# ---------------------------------------------------------------- contract
A, B = rand((3, 4, 5)), rand((5, 4, 2))
put("cA", A), put("cB", B)
case("contract dense/dense ((1,2),(1,0))", "REF", "contract cA cB 1,2 1,0 c_dd", "c_dd",
     py_dense(A).contract(py_dense(B), ((1, 2), (1, 0))).data, 1e-12)
As, Bs = rand((4, 6), density=0.4), rand((6, 3), density=0.4)
put("sA", As, True), put("sB", Bs, True)
try:
    info = dense_of(py_sparse(As).contract(py_sparse(Bs), ((1,), (0,))))
except Exception as e:  # reference sparse contract may throw
    info = f"reference raised {type(e).__name__}: {e}"
case("contract sparse/sparse", "TRUTH", "contract sA sB 1 0 c_ss", "c_ss", np.tensordot(As, Bs, ((1,), (0,))), 1e-12,
     info=info)
put("sAd", As)
case("contract dense/sparse mixed", "TRUTH", "contract sAd sB 1 0 c_ds", "c_ds", np.tensordot(As, Bs, ((1,), (0,))),
     1e-12)
Ac, Bc = rand((3, 4), np.complex128), rand((4, 5), np.complex128)
put("zA", Ac), put("zB", Bc)
case("contract complex128", "REF", "contract zA zB 1 0 c_zz", "c_zz",
     py_dense(Ac).contract(py_dense(Bc), ((1,), (0,))).data, 1e-12)

# ---------------------------------------------------------------- expand / project / transform
E = rand((3, 4))
put("eA", E)
case("expand dense (2,3)", "REF", "expand eA 2,3 e_out", "e_out", py_dense(E).expand((2, 3)).data, 0)
Es = rand((3, 4), density=0.5)
put("eS", Es, True)
case("expand sparse (2,)", "REF", "expand eS 2 e_sout", "e_sout", dense_of(py_sparse(Es).expand((2,))), 0)
P, Bas = rand((3, 4, 5)), rand((2, 4))
put("pA", P), put("pB", Bas)
case("project axis 1 onto 2 rows", "REF", "project pA pB 1 p_out", "p_out", py_dense(P).project(Bas, (1,)).data, 1e-12)
Ps, Bas2 = rand((3, 4, 5), density=0.3), rand((3, 5))
put("pS", Ps, True), put("pB2", Bas2)
case("project sparse axis 2", "REF", "project pS pB2 2 p_sout", "p_sout",
     dense_of(py_sparse(Ps).project(Bas2, (2,))), 1e-12)
T3, M = rand((3, 4, 5)), rand((2, 4))
put("tA", T3), put("tM", M)
try:
    info = py_dense(T3).transform(M, (1,)).data
except Exception as e:
    info = f"reference raised {type(e).__name__}: {e}"
case("transform axis 1 (n-mode product)", "TRUTH", "transform tA tM 1 t_out", "t_out",
     np.moveaxis(np.tensordot(M, T3, (1, 1)), 0, 1), 1e-12, info=info)

# ---------------------------------------------------------------- eigen
S = rand((8, 8))
S = S + S.T
put("eigS", S)
vals, _ = py_dense(S).compute_eigenstates(k=4)
case("eigenvalues symmetric 8x8, k=4", "REF", "eigvals eigS 4 eig_out", "eig_out", np.real(vals), 1e-10)
N = rand((6, 6))
put("eigN", N)
vals, _ = py_dense(N).compute_eigenstates(k=3)
case("eigenvalues non-symmetric (Hermitian part)", "REF", "eigvals eigN 3 eigN_out", "eigN_out", np.real(vals), 1e-10)
H = rand((6, 6), np.complex128)
H = H + H.conj().T
put("eigH", H)
vals, _ = py_dense(H).compute_eigenstates(k=3)
case("eigenvalues complex Hermitian", "REF", "eigvals eigH 3 eigH_out", "eigH_out", np.real(vals), 1e-10)
R = rand((5, 3))
put("svR", R)
vals, _ = py_dense(R).compute_eigenstates(k=2)
case("singular values rectangular 5x3", "REF", "svals svR 2 sv_out", "sv_out", vals, 1e-10)

# ---------------------------------------------------------------- temporal convolution
C = rand((3, 9))
put("tcA", C)
for nm, k in (("odd", [0.25, 0.5, 0.25]), ("even", [0.1, 0.2, 0.3, 0.4])):
    put(f"k_{nm}", np.asarray(k))
    case(f"temporal conv dense, {nm} kernel, last axis", "REF", f"conv tcA k_{nm} -1 tc_{nm}", f"tc_{nm}",
         py_dense(C).apply_temporal_convolution(np.asarray(k)).data, 1e-12)
C0 = rand((6, 3))
put("tc0", C0)
case("temporal conv dense axis 0", "REF", "conv tc0 k_odd 0 tc_ax0", "tc_ax0",
     py_dense(C0).apply_temporal_convolution(np.asarray([0.25, 0.5, 0.25]), time_axis=0).data, 1e-12)
Cs = rand((3, 12), density=0.35)
put("tcS", Cs, True)
case("temporal conv sparse with gaps", "TRUTH", "conv tcS k_odd -1 tc_s", "tc_s",
     convolve(Cs, np.asarray([0.25, 0.5, 0.25]).reshape(1, -1), mode="same"), 1e-12,
     info=dense_of(py_sparse(Cs).apply_temporal_convolution(np.asarray([0.25, 0.5, 0.25]))))

# ---------------------------------------------------------------- statistics
Pos = np.abs(rand((4, 5))) + 0.01
put("entP", Pos)
case("entropy strictly positive dense", "REF", "entropy entP ent_out", "ent_out", [py_dense(Pos).compute_entropy()],
     1e-12)
Mix = rand((4, 5))
put("entM", Mix)
case("entropy mixed-sign (unified over |v|)", "TRUTH", "entropy entM entM_out", "entM_out",
     [(lambda p: -np.sum(np.clip(p, 1e-12, 1) * np.log(np.clip(p, 1e-12, 1))))(np.abs(Mix.ravel()) / np.abs(Mix).sum())],
     1e-12, info=[py_dense(Mix).compute_entropy()])
D = rand((10, 10))
put("den", D)
edges, hist = py_dense(D).compute_density_function(20, 0.05)
case("density edges", "REF", "density den 20 0.05 den_e den_h", "den_e", edges, 1e-12)
checks.append(("density histogram", "REF", "den_h", hist, 1e-10, None, None))
X, Y = rand((4, 5)), rand((4, 5))
put("cmX", X), put("cmY", Y)
case("compatibility dense", "REF", "compat cmX cmY cm_out", "cm_out", [py_dense(X).compute_dict_compatibility(py_dense(Y))],
     1e-12)
Xs, Ys = rand((4, 5), density=0.5), rand((4, 5), density=0.5)
put("cmXs", Xs, True), put("cmYs", Ys, True)
case("compatibility sparse", "REF", "compat cmXs cmYs cms_out", "cms_out",
     [py_sparse(Xs).compute_dict_compatibility(py_sparse(Ys))], 1e-12)

# ---------------------------------------------------------------- geometry / fractal / decompositions
Hy = rand((3, 4, 2))
put("hyA", Hy)
case("hyperbolic, curvature -1 (ref is complex64)", "REF", "hyper hyA -1 hy_out", "hy_out",
     py_dense(Hy).to_hyperbolic_space(-1.0).data, 2e-6)
Fz = rand((3, 4)) * 0.3
put("frA", Fz)
case("fractal, constant c=-0.2, non-escaping", "REF", "fractal frA -0.2 10 fr_out", "fr_out",
     py_dense(Fz).fractal_iteration(lambda idx, z: -0.2, 10).data, 1e-12)
Tk = rand((4, 3, 5))
put("tkA", Tk)
case("tucker full-rank reconstruction", "TRUTH", "tucker tkA tk_out", "tk_out", Tk, 1e-10)
case("mps round trip", "TRUTH", "mps tkA mps_out", "mps_out", Tk, 1e-10)
Rz = rand((2, 3, 4), np.complex64, density=0.5)
put("rtS", Rz, True)
case("format round trip complex64 sparse (numpy->C++->numpy)", "TRUTH", "roundtrip rtS rt_out", "rt_out", Rz, 0)

# ---------------------------------------------------------------- run
with open(os.path.join(work, "manifest.txt"), "w") as f:
    f.write("\n".join(manifest) + "\n")
proc = subprocess.run([runner, work], capture_output=True, text=True)
sys.stdout.write(proc.stdout)
sys.stderr.write(proc.stderr)

fails = 0
for label, oracle, out, exp, tol, info, _ in checks:
    try:
        got = rn.load(os.path.join(work, out))
    except Exception as e:
        print(f"FAIL  [{oracle:5}] {label}: cannot read output ({e})")
        fails += 1
        continue
    exp = np.asarray(exp)
    if got.shape != exp.shape and got.size == exp.size:
        got = got.reshape(exp.shape)
    ok = got.shape == exp.shape and np.allclose(got, exp, rtol=0, atol=tol if tol else 0) if tol else (
            got.shape == exp.shape and np.array_equal(got, exp))
    err = float(np.max(np.abs(got - exp))) if got.shape == exp.shape and got.size else float("nan")
    print(f"{'ok  ' if ok else 'FAIL'}  [{oracle:5}] {label}  max|diff|={err:.2e}")
    fails += not ok
    if info is not None:
        if isinstance(info, str):
            print(f"      INFO reference: {info}")
        else:
            info = np.asarray(info)
            same = info.shape == exp.shape and np.allclose(info, exp, atol=1e-8)
            print(f"      INFO reference {'agrees with' if same else 'DIVERGES from'} ground truth"
                  + ("" if same or info.shape != exp.shape else f" (max|diff|={np.max(np.abs(info - exp)):.2e})"))
print(f"\n{len(checks) - fails}/{len(checks)} parity checks passed   (workdir {work})")
sys.exit(1 if fails else 0)
