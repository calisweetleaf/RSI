// rta/linalg.hpp — dependency-free dense linear algebra for the RTA core.
//
// All routines run in work precision W = double or std::complex<double>,
// regardless of the tensor's storage dtype. That keeps float32 tensors from
// losing eigen/SVD accuracy (numpy/LAPACK would also promote internally for
// the Python reference's eigh/svd paths on float64 inputs).
//
// Provided:
//   eigh_jacobi      Hermitian eigendecomposition (cyclic complex Jacobi)
//   svd_jacobi       thin SVD via one-sided (Hestenes) Jacobi, any m x n
//   orthonormalize   modified Gram-Schmidt with re-orthogonalization
//   lu_solve         Gaussian elimination with partial pivoting
//   eigs_subspace    top-k |lambda| eigenpairs of a Hermitian operator given
//                    only a block mat-vec (orthogonal iteration + Rayleigh-Ritz)
#pragma once

#include <algorithm>
#include <cmath>
#include <functional>
#include <numeric>
#include <optional>
#include <random>
#include <vector>

#include "types.hpp"

namespace rta {

template <class W>
struct Matrix {
    std::size_t rows = 0, cols = 0;
    std::vector<W> a;

    Matrix() = default;
    Matrix(std::size_t r, std::size_t c) : rows(r), cols(c), a(r * c, W(0)) {}
    W& operator()(std::size_t r, std::size_t c) { return a[r * cols + c]; }
    const W& operator()(std::size_t r, std::size_t c) const { return a[r * cols + c]; }

    static Matrix identity(std::size_t n) {
        Matrix m(n, n);
        for (std::size_t i = 0; i < n; ++i) m(i, i) = W(1);
        return m;
    }
    Matrix conj_transpose() const {
        Matrix t(cols, rows);
        for (std::size_t r = 0; r < rows; ++r)
            for (std::size_t c = 0; c < cols; ++c) t(c, r) = conj_of(a[r * cols + c]);
        return t;
    }
    template <class U>
    Matrix<U> cast() const {
        Matrix<U> m(rows, cols);
        for (std::size_t i = 0; i < a.size(); ++i) m.a[i] = scalar_cast<U>(a[i]);
        return m;
    }
};

template <class W>
Matrix<W> matmul(const Matrix<W>& A, const Matrix<W>& B) {
    if (A.cols != B.rows) throw ShapeError("matmul: inner dimensions differ");
    Matrix<W> C(A.rows, B.cols);
    for (std::size_t i = 0; i < A.rows; ++i)
        for (std::size_t k = 0; k < A.cols; ++k) {
            const W aik = A(i, k);
            if (aik == W(0)) continue;
            const W* brow = &B.a[k * B.cols];
            W* crow = &C.a[i * C.cols];
            for (std::size_t j = 0; j < B.cols; ++j) crow[j] += aik * brow[j];
        }
    return C;
}

namespace detail {

// Rotation that annihilates the off-diagonal of the Hermitian 2x2 block
//   [[app, apq], [conj(apq), aqq]]
// Returned as (c, s, u) where the unitary W acts on columns p,q:
//   W e_p = c e_p - s conj(u) e_q
//   W e_q = s e_p + c conj(u) e_q
// Derivation: D = diag(.., conj(u) at q) makes the block real symmetric with
// off-diagonal g = |apq|; then a real Jacobi rotation zeroes it.
template <class W>
struct Rot {
    double c = 1.0, s = 0.0;
    W u = W(1);
};

template <class W>
inline Rot<W> hermitian_rotation(double app, double aqq, const W& apq) {
    Rot<W> r;
    const double g = std::abs(apq);
    if (g == 0.0) return r;
    r.u = apq / g;
    const double theta = (aqq - app) / (2.0 * g);
    const double t = (theta >= 0 ? 1.0 : -1.0) / (std::abs(theta) + std::sqrt(theta * theta + 1.0));
    r.c = 1.0 / std::sqrt(t * t + 1.0);
    r.s = t * r.c;
    return r;
}

// Apply W to columns p,q of an (rows x cols) row-major buffer.
template <class W>
inline void rotate_cols(W* m, std::size_t rows, std::size_t cols, std::size_t p, std::size_t q,
                        const Rot<W>& r) {
    const W cu = conj_of(r.u);
    for (std::size_t k = 0; k < rows; ++k) {
        W& xp = m[k * cols + p];
        W& xq = m[k * cols + q];
        const W a = xp, b = xq;
        xp = r.c * a - r.s * cu * b;
        xq = r.s * a + r.c * cu * b;
    }
}
// Apply W^H to rows p,q.
template <class W>
inline void rotate_rows(W* m, std::size_t cols, std::size_t p, std::size_t q, const Rot<W>& r) {
    W* rp = m + p * cols;
    W* rq = m + q * cols;
    for (std::size_t k = 0; k < cols; ++k) {
        const W a = rp[k], b = rq[k];
        rp[k] = r.c * a - r.s * r.u * b;
        rq[k] = r.s * a + r.c * r.u * b;
    }
}

}  // namespace detail

// ------------------------------------------------------------ eigh (Jacobi)
template <class W>
struct EighResult {
    std::vector<double> values;  // unsorted, paired with columns of vectors
    Matrix<W> vectors;           // columns are orthonormal eigenvectors
    int sweeps = 0;
    bool converged = false;
};

// Hermitian eigendecomposition. Input must be Hermitian (caller symmetrizes).
template <class W>
EighResult<W> eigh_jacobi(Matrix<W> A, double tol = 1e-14, int max_sweeps = 64) {
    if (A.rows != A.cols) throw ShapeError("eigh_jacobi: matrix must be square");
    const std::size_t n = A.rows;
    EighResult<W> out;
    out.vectors = Matrix<W>::identity(n);
    double fro = 0.0;
    for (const W& v : A.a) fro += std::norm(std::complex<double>(real_part(v), imag_part(v)));
    fro = std::sqrt(fro);
    const double floor = tol * (fro > 0 ? fro : 1.0);

    for (int sweep = 0; sweep < max_sweeps; ++sweep) {
        double off = 0.0;
        for (std::size_t p = 0; p < n; ++p)
            for (std::size_t q = p + 1; q < n; ++q) off += 2.0 * std::norm(std::complex<double>(real_part(A(p, q)), imag_part(A(p, q))));
        off = std::sqrt(off);
        out.sweeps = sweep;
        if (off <= floor) { out.converged = true; break; }
        for (std::size_t p = 0; p < n; ++p)
            for (std::size_t q = p + 1; q < n; ++q) {
                const W apq = A(p, q);
                if (std::abs(apq) <= floor * 1e-3 / static_cast<double>(n + 1)) continue;
                auto r = detail::hermitian_rotation<W>(real_part(A(p, p)), real_part(A(q, q)), apq);
                detail::rotate_cols(A.a.data(), n, n, p, q, r);
                detail::rotate_rows(A.a.data(), n, p, q, r);
                detail::rotate_cols(out.vectors.a.data(), n, n, p, q, r);
                A(p, q) = W(0);
                A(q, p) = W(0);
                A(p, p) = W(real_part(A(p, p)));
                A(q, q) = W(real_part(A(q, q)));
            }
    }
    if (!out.converged) {
        double off = 0.0;
        for (std::size_t p = 0; p < n; ++p)
            for (std::size_t q = p + 1; q < n; ++q) off += 2.0 * std::abs(A(p, q)) * std::abs(A(p, q));
        out.converged = std::sqrt(off) <= floor;
        out.sweeps = max_sweeps;
    }
    out.values.resize(n);
    for (std::size_t i = 0; i < n; ++i) out.values[i] = real_part(A(i, i));
    return out;
}

// ------------------------------------------------------------ orthonormalize
// Modified Gram-Schmidt on the columns of M, twice (numerically robust).
// Columns that collapse are replaced by a unit vector orthogonal to the rest.
template <class W>
void orthonormalize(Matrix<W>& M) {
    const std::size_t m = M.rows, k = M.cols;
    auto col_dot = [&](std::size_t i, std::size_t j) {
        W s(0);
        for (std::size_t r = 0; r < m; ++r) s += conj_of(M(r, i)) * M(r, j);
        return s;
    };
    std::size_t fill = 0;  // next canonical basis vector to try for collapsed columns
    for (std::size_t j = 0; j < k; ++j) {
        for (int pass = 0; pass < 2; ++pass)
            for (std::size_t i = 0; i < j; ++i) {
                const W d = col_dot(i, j);
                for (std::size_t r = 0; r < m; ++r) M(r, j) -= d * M(r, i);
            }
        double nrm = std::sqrt(std::abs(real_part(col_dot(j, j))));
        while (nrm < 1e-12 && fill < m) {
            for (std::size_t r = 0; r < m; ++r) M(r, j) = W(r == fill ? 1 : 0);
            ++fill;
            for (int pass = 0; pass < 2; ++pass)
                for (std::size_t i = 0; i < j; ++i) {
                    const W d = col_dot(i, j);
                    for (std::size_t r = 0; r < m; ++r) M(r, j) -= d * M(r, i);
                }
            nrm = std::sqrt(std::abs(real_part(col_dot(j, j))));
        }
        if (nrm < 1e-12) continue;  // k > m: cannot complete; leave zero column
        for (std::size_t r = 0; r < m; ++r) M(r, j) /= nrm;
    }
}

// ------------------------------------------------------------ SVD (Hestenes)
template <class W>
struct SvdResult {
    Matrix<W> U;               // m x r, orthonormal columns
    std::vector<double> S;     // r singular values, descending
    Matrix<W> V;               // n x r, orthonormal columns (A = U diag(S) V^H)
    int sweeps = 0;
    bool converged = false;
};

namespace detail {
template <class W>
SvdResult<W> svd_tall(Matrix<W> A, double tol, int max_sweeps) {  // requires rows >= cols
    const std::size_t m = A.rows, n = A.cols;
    SvdResult<W> out;
    Matrix<W> V = Matrix<W>::identity(n);
    for (int sweep = 0; sweep < max_sweeps; ++sweep) {
        bool rotated = false;
        for (std::size_t p = 0; p < n; ++p)
            for (std::size_t q = p + 1; q < n; ++q) {
                double alpha = 0, beta = 0;
                W gamma(0);
                for (std::size_t r = 0; r < m; ++r) {
                    const W ap = A(r, p), aq = A(r, q);
                    alpha += std::norm(std::complex<double>(real_part(ap), imag_part(ap)));
                    beta += std::norm(std::complex<double>(real_part(aq), imag_part(aq)));
                    gamma += conj_of(ap) * aq;
                }
                if (std::abs(gamma) <= tol * std::sqrt(alpha * beta) || std::abs(gamma) < 1e-300) continue;
                rotated = true;
                auto rot = hermitian_rotation<W>(alpha, beta, gamma);
                rotate_cols(A.a.data(), m, n, p, q, rot);
                rotate_cols(V.a.data(), n, n, p, q, rot);
            }
        out.sweeps = sweep + 1;
        if (!rotated) { out.converged = true; break; }
    }
    std::vector<double> s(n);
    for (std::size_t j = 0; j < n; ++j) {
        double acc = 0;
        for (std::size_t r = 0; r < m; ++r) acc += std::norm(std::complex<double>(real_part(A(r, j)), imag_part(A(r, j))));
        s[j] = std::sqrt(acc);
    }
    std::vector<std::size_t> order(n);
    std::iota(order.begin(), order.end(), 0);
    std::stable_sort(order.begin(), order.end(), [&](std::size_t a, std::size_t b) { return s[a] > s[b]; });
    out.U = Matrix<W>(m, n);
    out.V = Matrix<W>(n, n);
    out.S.resize(n);
    const double smax = n ? s[order[0]] : 0.0;
    for (std::size_t j = 0; j < n; ++j) {
        const std::size_t src = order[j];
        out.S[j] = s[src];
        for (std::size_t r = 0; r < n; ++r) out.V(r, j) = V(r, src);
        if (s[src] > smax * 1e-15 && s[src] > 0)
            for (std::size_t r = 0; r < m; ++r) out.U(r, j) = A(r, src) / s[src];
    }
    orthonormalize(out.U);  // completes columns for zero singular values
    return out;
}
}  // namespace detail

template <class W>
SvdResult<W> svd_jacobi(const Matrix<W>& A, double tol = 1e-15, int max_sweeps = 64) {
    if (A.rows >= A.cols) return detail::svd_tall(A, tol, max_sweeps);
    // A = (A^H)^H ; A^H = U' S V'^H  =>  A = V' S U'^H
    auto t = detail::svd_tall(A.conj_transpose(), tol, max_sweeps);
    SvdResult<W> out;
    out.U = std::move(t.V);
    out.V = std::move(t.U);
    out.S = std::move(t.S);
    out.sweeps = t.sweeps;
    out.converged = t.converged;
    return out;
}

// ------------------------------------------------------------ LU solve
template <class W>
std::optional<std::vector<W>> lu_solve(Matrix<W> A, std::vector<W> b) {
    const std::size_t n = A.rows;
    if (A.cols != n || b.size() != n) throw ShapeError("lu_solve: dimension mismatch");
    double scale = 0;
    for (const W& v : A.a) scale = std::max(scale, std::abs(v));
    const double eps = std::numeric_limits<double>::epsilon() * static_cast<double>(n) * (scale > 0 ? scale : 1.0);
    for (std::size_t k = 0; k < n; ++k) {
        std::size_t piv = k;
        double best = std::abs(A(k, k));
        for (std::size_t r = k + 1; r < n; ++r)
            if (std::abs(A(r, k)) > best) { best = std::abs(A(r, k)); piv = r; }
        if (best <= eps) return std::nullopt;  // numerically singular
        if (piv != k) {
            for (std::size_t c = 0; c < n; ++c) std::swap(A(k, c), A(piv, c));
            std::swap(b[k], b[piv]);
        }
        for (std::size_t r = k + 1; r < n; ++r) {
            const W f = A(r, k) / A(k, k);
            if (f == W(0)) continue;
            for (std::size_t c = k; c < n; ++c) A(r, c) -= f * A(k, c);
            b[r] -= f * b[k];
        }
    }
    std::vector<W> x(n);
    for (std::size_t i = n; i-- > 0;) {
        W s = b[i];
        for (std::size_t c = i + 1; c < n; ++c) s -= A(i, c) * x[c];
        x[i] = s / A(i, i);
    }
    return x;
}

// ------------------------------------------------------------ subspace iteration
// Top-k eigenpairs by |lambda| of an n x n Hermitian operator H, given
// apply(X) -> H X for an n x m block. This is the "eigenrecursion" loop made
// literal: X_{t+1} = orth(H X_t) iterated to a fixed point of the Ritz values.
template <class W>
struct SubspaceResult {
    std::vector<double> values;  // sorted by |lambda| descending, length k
    Matrix<W> vectors;           // n x k
    int iterations = 0;
    bool converged = false;
};

template <class W>
SubspaceResult<W> eigs_subspace(std::size_t n, const std::function<Matrix<W>(const Matrix<W>&)>& apply,
                                std::size_t k, double tol, int max_iter, std::uint64_t seed) {
    k = std::min(k, n);
    const std::size_t m = std::min(n, std::max<std::size_t>(2 * k, k + 8));
    std::mt19937_64 rng(seed);
    std::normal_distribution<double> nd(0.0, 1.0);
    Matrix<W> X(n, m);
    for (auto& v : X.a) {
        if constexpr (is_complex_v<W>) v = W(nd(rng), nd(rng)); else v = nd(rng);
    }
    orthonormalize(X);
    SubspaceResult<W> out;
    std::vector<double> prev(k, 0.0);
    for (int it = 0; it < max_iter; ++it) {
        Matrix<W> Z = apply(X);
        Matrix<W> Hs = matmul(X.conj_transpose(), Z);  // m x m Rayleigh quotient
        for (std::size_t i = 0; i < m; ++i)             // enforce Hermitian
            for (std::size_t j = i + 1; j < m; ++j) {
                const W avg = (Hs(i, j) + conj_of(Hs(j, i))) * 0.5;
                Hs(i, j) = avg;
                Hs(j, i) = conj_of(avg);
            }
        auto e = eigh_jacobi(Hs);
        std::vector<std::size_t> order(m);
        std::iota(order.begin(), order.end(), 0);
        std::stable_sort(order.begin(), order.end(),
                         [&](std::size_t a, std::size_t b) { return std::abs(e.values[a]) > std::abs(e.values[b]); });
        Matrix<W> S(m, m);
        for (std::size_t j = 0; j < m; ++j)
            for (std::size_t r = 0; r < m; ++r) S(r, j) = e.vectors(r, order[j]);
        double scale = 1e-300, delta = 0;
        for (std::size_t i = 0; i < k; ++i) {
            const double v = e.values[order[i]];
            scale = std::max(scale, std::abs(v));
            delta = std::max(delta, std::abs(v - prev[i]));
            prev[i] = v;
        }
        out.iterations = it + 1;
        Matrix<W> ritz = matmul(X, S);  // current Ritz vectors (orthonormal)
        if (it > 0 && delta <= tol * scale) {
            out.converged = true;
            out.values.assign(prev.begin(), prev.end());
            out.vectors = Matrix<W>(n, k);
            for (std::size_t r = 0; r < n; ++r)
                for (std::size_t j = 0; j < k; ++j) out.vectors(r, j) = ritz(r, j);
            return out;
        }
        X = matmul(Z, S);  // advance: H X rotated into Ritz order
        orthonormalize(X);
        if (it + 1 == max_iter) {
            out.values.assign(prev.begin(), prev.end());
            out.vectors = Matrix<W>(n, k);
            for (std::size_t r = 0; r < n; ++r)
                for (std::size_t j = 0; j < k; ++j) out.vectors(r, j) = ritz(r, j);
        }
    }
    return out;
}

}  // namespace rta
