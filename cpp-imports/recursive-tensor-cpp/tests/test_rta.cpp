// tests/test_rta.cpp — self-contained test suite for the RTA C++ core.
// No framework: CHECK counts failures; exit code = number of failures.
#include <cstdio>
#include <iostream>

#include "rta/rta.hpp"

using namespace rta;
using cf = std::complex<float>;
using cd = std::complex<double>;

static int g_fail = 0, g_pass = 0;
#define CHECK(cond)                                                                 \
    do {                                                                            \
        if (cond) ++g_pass;                                                         \
        else { ++g_fail; std::printf("  FAIL %s:%d  %s\n", __FILE__, __LINE__, #cond); } \
    } while (0)
#define CHECK_THROWS(expr, E)                                                       \
    do {                                                                            \
        bool thrown_ = false;                                                       \
        try { (void)(expr); } catch (const E&) { thrown_ = true; }                  \
        CHECK(thrown_);                                                             \
    } while (0)
#define SECTION(name) std::printf("[%s]\n", name)

template <class T> double maxdiff(const RecursiveTensor<T>& a, const RecursiveTensor<T>& b) {
    if (a.shape() != b.shape()) return 1e300;
    auto x = a.to_dense_array(), y = b.to_dense_array();
    double m = 0;
    for (std::size_t i = 0; i < x.size(); ++i) m = std::max(m, mag(x[i] - y[i]));
    return m;
}
template <class T> RecursiveTensor<T> rand_dense(Shape s, std::uint64_t seed) {
    std::mt19937_64 rng(seed);
    std::normal_distribution<double> nd;
    std::vector<T> v(volume_of(s));
    for (auto& x : v) {
        if constexpr (is_complex_v<T>) x = T(static_cast<real_t<T>>(nd(rng)), static_cast<real_t<T>>(nd(rng)));
        else x = static_cast<T>(nd(rng));
    }
    return RecursiveTensor<T>::from_dense(s, v);
}
template <class T> RecursiveTensor<T> rand_sparse(Shape s, double density, std::uint64_t seed) {
    auto d = rand_dense<T>(s, seed);
    std::mt19937_64 rng(seed ^ 0xABCDEF);
    std::uniform_real_distribution<double> u(0, 1);
    auto arr = d.to_dense_array();
    for (auto& x : arr) if (u(rng) > density) x = T(0);
    return RecursiveTensor<T>::from_dense(s, arr).to_sparse();
}

// Naive reference tensordot on dense arrays (independent of the engine).
template <class T>
std::vector<T> naive_contract(const RecursiveTensor<T>& A, const RecursiveTensor<T>& B, const Axes& a, const Axes& b, Shape& out) {
    const Axes ka = rta::detail::complement(a, A.rank()), kb = rta::detail::complement(b, B.rank());
    out.clear();
    for (auto x : ka) out.push_back(A.shape()[x]);
    for (auto x : kb) out.push_back(B.shape()[x]);
    std::vector<T> r(volume_of(out), T(0));
    auto ad = A.to_dense_array(), bd = B.to_dense_array();
    for (Extent la = 0; la < A.volume(); ++la) {
        const Index ia = delinearize(la, A.shape());
        for (Extent lb = 0; lb < B.volume(); ++lb) {
            const Index ib = delinearize(lb, B.shape());
            bool ok = true;
            for (std::size_t i = 0; i < a.size(); ++i) if (ia[a[i]] != ib[b[i]]) { ok = false; break; }
            if (!ok) continue;
            Index io;
            for (auto x : ka) io.push_back(ia[x]);
            for (auto x : kb) io.push_back(ib[x]);
            r[out.empty() ? 0 : linearize(io, out)] += ad[la] * bd[lb];
        }
    }
    return r;
}

void test_construction() {
    SECTION("construction");
    RecursiveTensor<float> n({6, 5, 4}, Distribution::Normal, 0.9, 42);
    CHECK(n.is_sparse());
    CHECK(n.stored_count() <= static_cast<std::size_t>(120 * 0.1) + 1);
    CHECK(n.stored_count() > 0);
    RecursiveTensor<float> n2({6, 5, 4}, Distribution::Normal, 0.9, 42);
    CHECK(maxdiff(n, n2) == 0.0);  // seeded determinism
    auto sq = RecursiveTensor<double>::square(4, 3, Distribution::Uniform, 0.1, 1);
    CHECK((sq.shape() == Shape{4, 4, 4}));
    bool in_range = true;
    for (double v : sq.dense_data()) in_range &= std::abs(v) <= 0.01;
    CHECK(in_range);
    RecursiveTensor<double> pl({10, 10}, Distribution::PowerLaw, 0.0, 3);
    bool pl_ok = true;
    for (double v : pl.dense_data()) pl_ok &= std::abs(v) <= 0.1;
    CHECK(pl_ok);
    CHECK_THROWS(RecursiveTensor<float>({3, 3}, Distribution::ComplexGaussian, 0, 1), DTypeError);
    RecursiveTensor<cf> cg({3, 3}, Distribution::ComplexGaussian, 0, 1);
    CHECK(std::abs(cg.dense_data()[0].imag()) > 0);
    RecursiveTensor<double> orth({5, 7, 2}, Distribution::Orthogonal, 0, 9);
    double err = 0;  // rows of T[:, :5, 0] orthonormal
    for (Extent i = 0; i < 5; ++i)
        for (Extent j = 0; j < 5; ++j) {
            double d = 0;
            for (Extent c = 0; c < 5; ++c) d += orth.get({i, c, 0}) * orth.get({j, c, 0});
            err = std::max(err, std::abs(d - (i == j ? 1.0 : 0.0)));
        }
    CHECK(err < 1e-12);
    CHECK_THROWS(RecursiveTensor<double>({5, 3}, Distribution::Orthogonal, 0, 1), ShapeError);
    auto z = RecursiveTensor<double>::zeros({3, 0, 2});
    CHECK(z.volume() == 0);
    auto s0 = RecursiveTensor<double>::zeros({});
    CHECK(s0.volume() == 1);  // rank-0 scalar
}

void test_access() {
    SECTION("access / from_cells");
    auto t = RecursiveTensor<float>::from_cells({2, 3, 4}, {{{1, 2, 3}, 5.f}, {{0, 0, 0}, 1.f}, {{1, 2, 3}, 7.f}});
    CHECK(t.get({1, 2, 3}) == 7.f);  // last write wins
    CHECK(t.nnz() == 2);
    CHECK(std::abs(t.sparsity() - (1.0 - 2.0 / 24)) < 1e-12);
    CHECK_THROWS(t.get({2, 0, 0}), IndexError);
    CHECK_THROWS(t.get({0, 0}), IndexError);
    auto s = t.to_sparse();
    s.set({1, 2, 3}, 0.f);
    CHECK(s.stored_count() == 1);  // sparse zero-set erases
    CHECK(maxdiff(t.to_sparse().to_dense(), t) == 0);
}

template <class T> void test_contract_t(const char* name) {
    SECTION(name);
    auto A = rand_dense<T>({3, 4, 5}, 1), B = rand_dense<T>({5, 4, 2}, 2);
    auto As = rand_sparse<T>({3, 4, 5}, 0.4, 3), Bs = rand_sparse<T>({5, 4, 2}, 0.4, 4);
    for (auto [a, b] : std::vector<std::pair<Axes, Axes>>{{{2}, {0}}, {{1, 2}, {1, 0}}, {{0}, {2}}}) {
        if (A.shape()[a[0]] != B.shape()[b[0]]) continue;
        for (auto* X : {&A, &As})
            for (auto* Y : {&B, &Bs}) {
                Shape os;
                auto ref = naive_contract(*X, *Y, a, b, os);
                auto got = X->contract(*Y, a, b);
                CHECK(got.shape() == os);
                double m = 0;
                auto g = got.to_dense_array();
                for (std::size_t i = 0; i < g.size(); ++i) m = std::max(m, mag(g[i] - ref[i]));
                CHECK(m < 1e-4);
                CHECK(got.is_sparse() == (X->is_sparse() && Y->is_sparse()));
            }
    }
    // full contraction -> rank 0
    auto full = A.contract(A, {0, 1, 2}, {0, 1, 2});
    CHECK(full.rank() == 0 && full.volume() == 1);
    T ss(0);
    for (const T& v : A.dense_data()) ss += v * v;
    CHECK(mag(full.get({}) - ss) < 1e-3);
    CHECK_THROWS(A.contract(B, {0}, {0}), ShapeError);  // extent mismatch 3 vs 5
    CHECK_THROWS(A.contract(B, {0, 0}, {0, 1}), ShapeError);
}

void test_expand_project_transform() {
    SECTION("expand / project / transform");
    auto A = rand_dense<double>({3, 4}, 5);
    auto E = A.expand({2});
    CHECK((E.shape() == Shape{2, 3, 4}));
    CHECK(E.get({0, 1, 2}) == A.get({1, 2}) && E.get({1, 1, 2}) == 0.0);
    CHECK(maxdiff(A.to_sparse().expand({2}), E) == 0);
    CHECK_THROWS(A.expand({2, 2, 2}), ShapeError);

    auto X = rand_dense<double>({2, 5, 3, 4}, 6);
    Matrix<double> B(2, 3);
    for (auto& v : B.a) v = 0.3 + static_cast<double>(&v - B.a.data()) * 0.7;
    auto P = X.project(B, {2});
    CHECK((P.shape() == Shape{2, 5, 2, 4}));
    // manual check on one cell
    double n0 = std::sqrt(B(0, 0) * B(0, 0) + B(0, 1) * B(0, 1) + B(0, 2) * B(0, 2));
    double manual = (B(0, 0) * X.get({1, 2, 0, 3}) + B(0, 1) * X.get({1, 2, 1, 3}) + B(0, 2) * X.get({1, 2, 2, 3})) / n0;
    CHECK(std::abs(P.get({1, 2, 0, 3}) - manual) < 1e-12);
    CHECK(maxdiff(X.to_sparse().project(B, {2}), P) < 1e-9);
    CHECK_THROWS(X.project(B, {1}), ShapeError);
    auto pv = X.project(std::vector<double>{1, 1, 1, 1}, {3});
    CHECK((pv.shape() == Shape{2, 5, 3, 1}));

    Matrix<double> M(2, 3);
    M.a = {1, 2, 3, 4, 5, 6};
    auto Y = rand_dense<double>({3, 3}, 7);
    auto T1 = Y.transform(M);  // both axes: M Y M^T
    CHECK((T1.shape() == Shape{2, 2}));
    double m01 = 0;
    for (int i = 0; i < 3; ++i) for (int j = 0; j < 3; ++j) m01 += M(0, i) * Y.get({Extent(i), Extent(j)}) * M(1, j);
    CHECK(std::abs(T1.get({0, 1}) - m01) < 1e-12);
    CHECK(maxdiff(Y.to_sparse().transform(M), T1) < 1e-9);  // sequential composition in sparse too
    Matrix<double> big(4, 3);
    CHECK_THROWS(Y.transform(big), ShapeError);
}

void test_embed_fractal() {
    SECTION("embed / fractal");
    auto A = rand_dense<double>({2, 3}, 8);
    auto E = A.embed({2}, [](const Index&, const double& v) {
        return std::vector<std::pair<Index, double>>{{{0}, v}, {{1}, v * v}};
    });
    CHECK((E.shape() == Shape{2, 3, 2}));
    CHECK(E.get({1, 2, 1}) == A.get({1, 2}) * A.get({1, 2}));
    auto Es = A.embed_scalar([](const double& v, const Index&) { return 2 * v; });
    CHECK((Es.shape() == Shape{2, 3, 1}) && Es.get({0, 1, 0}) == 2 * A.get({0, 1}));

    auto C = RecursiveTensor<cd>::from_dense({2}, {cd(0.1, 0.1), cd(1.5, 1.5)});
    auto F = C.fractal_iteration([](const Index&, const cd&) { return cd(-0.1, 0.2); }, 50);
    CHECK(std::abs(F.get({0})) < 2.0);   // bounded orbit
    CHECK(std::abs(F.get({1})) > 2.0);   // escaped, stopped (not inf)
    CHECK(std::isfinite(std::abs(F.get({1}))));
    auto Fs = C.to_sparse().fractal_iteration([](const Index&, const cd&) { return cd(-0.1, 0.2); }, 50);
    CHECK(maxdiff(Fs, F) < 1e-12);
}

void test_linalg() {
    SECTION("linalg: eigh / svd / lu");
    std::mt19937_64 rng(11);
    std::normal_distribution<double> nd;
    for (std::size_t n : {1u, 2u, 7u, 30u}) {
        Matrix<cd> H(n, n);
        for (std::size_t i = 0; i < n; ++i)
            for (std::size_t j = i; j < n; ++j) {
                cd v(nd(rng), i == j ? 0 : nd(rng));
                H(i, j) = v;
                H(j, i) = std::conj(v);
            }
        auto e = eigh_jacobi(H);
        CHECK(e.converged);
        double res = 0, orth = 0;
        for (std::size_t k = 0; k < n; ++k) {
            for (std::size_t i = 0; i < n; ++i) {
                cd hv(0);
                for (std::size_t j = 0; j < n; ++j) hv += H(i, j) * e.vectors(j, k);
                res = std::max(res, std::abs(hv - e.values[k] * e.vectors(i, k)));
            }
            for (std::size_t l = 0; l < n; ++l) {
                cd d(0);
                for (std::size_t i = 0; i < n; ++i) d += std::conj(e.vectors(i, k)) * e.vectors(i, l);
                orth = std::max(orth, std::abs(d - (k == l ? 1.0 : 0.0)));
            }
        }
        CHECK(res < 1e-10);
        CHECK(orth < 1e-10);
    }
    for (auto [m, n] : std::vector<std::pair<std::size_t, std::size_t>>{{6, 4}, {4, 6}, {5, 5}, {1, 3}}) {
        Matrix<cd> A(m, n);
        for (auto& v : A.a) v = cd(nd(rng), nd(rng));
        auto s = svd_jacobi(A);
        double rec = 0;
        for (std::size_t i = 0; i < m; ++i)
            for (std::size_t j = 0; j < n; ++j) {
                cd acc(0);
                for (std::size_t k = 0; k < s.S.size(); ++k) acc += s.U(i, k) * s.S[k] * std::conj(s.V(j, k));
                rec = std::max(rec, std::abs(acc - A(i, j)));
            }
        CHECK(rec < 1e-10);
        bool sorted = true;
        for (std::size_t k = 1; k < s.S.size(); ++k) sorted &= s.S[k - 1] >= s.S[k];
        CHECK(sorted);
    }
    Matrix<double> L(3, 3);
    L.a = {4, 1, 0, 1, 3, 1, 0, 1, 2};
    auto x = lu_solve(L, std::vector<double>{1, 2, 3});
    CHECK(x.has_value());
    CHECK(std::abs(4 * (*x)[0] + (*x)[1] - 1) < 1e-12);
    Matrix<double> Sg(2, 2);
    Sg.a = {1, 2, 2, 4};
    CHECK(!lu_solve(Sg, std::vector<double>{1, 1}).has_value());
}

void test_eigenstates() {
    SECTION("compute_eigenstates");
    // Symmetric 3x3x... as a rank-3 tensor (2*3) x 6 matricization
    const std::size_t n = 6;
    std::mt19937_64 rng(5);
    std::normal_distribution<double> nd;
    std::vector<double> m(n * n);
    for (std::size_t i = 0; i < n; ++i) for (std::size_t j = i; j < n; ++j) m[i * n + j] = m[j * n + i] = nd(rng);
    auto T = RecursiveTensor<double>::from_dense({2, 3, 6}, m);
    auto r = T.compute_eigenstates(3);  // default axes: (0,1) x (2)
    CHECK(r.method == EigenResult<double>::Method::JacobiEigh);
    CHECK(!r.symmetrized);
    CHECK((r.vectors->shape() == Shape{3, 6}));
    for (std::size_t k = 0; k < 3; ++k) {
        double res = 0;
        for (std::size_t i = 0; i < n; ++i) {
            double hv = 0;
            for (std::size_t j = 0; j < n; ++j) hv += m[i * n + j] * r.vectors->get({k, j});
            res = std::max(res, std::abs(hv - r.values[k] * r.vectors->get({k, i})));
        }
        CHECK(res < 1e-9);
    }
    CHECK(std::abs(r.values[0]) >= std::abs(r.values[1]) && std::abs(r.values[1]) >= std::abs(r.values[2]));
    // Subspace path agrees with Jacobi.
    EigenOptions small;
    small.dense_limit = 2;
    auto rs = T.to_sparse().compute_eigenstates({0, 1}, {2}, 3, 1e-12, small);
    CHECK(rs.method == EigenResult<double>::Method::SubspaceIteration);
    for (std::size_t k = 0; k < 3; ++k) CHECK(std::abs(rs.values[k] - r.values[k]) < 1e-8);
    // Non-Hermitian input is symmetrized and flagged.
    auto NS = RecursiveTensor<double>::from_dense({2, 2}, {1, 2, 0, 1});
    auto rn = NS.compute_eigenstates(2);
    CHECK(rn.symmetrized);
    CHECK(std::abs(std::abs(rn.values[0]) - 2.0) < 1e-12);  // eig of [[1,1],[1,1]] = {2,0}
    // Rectangular -> SVD
    auto R = rand_dense<double>({4, 3}, 12);
    auto rr = R.compute_eigenstates(2);
    CHECK(rr.method == EigenResult<double>::Method::JacobiSvd);
    CHECK((rr.vectors->shape() == Shape{2, 3}));
    // Cache invalidates on mutation.
    auto c1 = T.compute_eigenstates(1);
    T.set({0, 0, 0}, 100.0);
    auto c2 = T.compute_eigenstates(1);
    CHECK(std::abs(c1.values[0] - c2.values[0]) > 1.0);
    CHECK_THROWS(T.compute_eigenstates(Axes{0}, Axes{2}), ShapeError);  // must cover all axes
    CHECK_THROWS(T.compute_eigenstates(std::size_t{0}), ShapeError);
    // Large-ish complex Hermitian via subspace iteration, dominant values
    const std::size_t N = 64;
    std::vector<cd> h(N * N);
    for (std::size_t i = 0; i < N; ++i) h[i * N + i] = cd(static_cast<double>(i), 0);  // eigenvalues 0..63
    auto HT = RecursiveTensor<cd>::from_dense({N, N}, h).to_sparse();
    EigenOptions o2;
    o2.dense_limit = 8;
    auto rh = HT.compute_eigenstates({0}, {1}, 3, 1e-12, o2);
    CHECK(std::abs(rh.values[0] - 63) < 1e-6 && std::abs(rh.values[1] - 62) < 1e-6);
}

void test_stats() {
    SECTION("density / entropy / norms / compatibility");
    auto A = RecursiveTensor<double>::from_dense({4}, {0.5, 1.0, 1.0, 0.001});
    auto h = A.compute_density_function(2, 0.01);
    CHECK(h.edges.size() == 3 && std::abs(h.edges[0] - 0.5) < 1e-15 && std::abs(h.edges[2] - 1.0) < 1e-15);
    CHECK(std::abs(h.density[0] - 1.0 / 3 / 0.25) < 1e-12 && std::abs(h.density[1] - 2.0 / 3 / 0.25) < 1e-12);
    auto U = RecursiveTensor<double>::from_dense({4}, {1, 1, 1, 1});
    CHECK(std::abs(U.compute_entropy() - std::log(4.0)) < 1e-12);
    CHECK(std::abs(U.to_sparse().compute_entropy() - std::log(4.0)) < 1e-12);  // storage invariant
    auto Q = RecursiveTensor<double>::from_dense({2, 2}, {3, -4, 0, 0});
    CHECK(std::abs(Q.norm(NormType::L2) - 5) < 1e-12 && Q.norm(NormType::L1) == 7 && Q.norm(NormType::Inf) == 4);
    CHECK(std::abs(Q.normalize().norm() - 1) < 1e-12);
    CHECK(maxdiff(Q.to_sparse().normalize(NormType::L1), Q.normalize(NormType::L1)) < 1e-15);
    CHECK(std::abs(Q.compatibility(Q) - 1) < 1e-12);
    auto Z = RecursiveTensor<double>::zeros({2, 2});
    CHECK(Z.compatibility(Z) == 1.0 && Q.compatibility(Z) == 0.0);
    auto Qs = Q.to_sparse();
    auto Q2 = RecursiveTensor<double>::from_dense({2, 2}, {3, 0, 0, 1}).to_sparse();
    // keys {0,1} vs {0,3}: jaccard 1/3, value sim at key 0 = 1  => 0.5/3 + 0.5
    CHECK(std::abs(Qs.compatibility(Q2) - (0.5 / 3 + 0.5)) < 1e-12);
    auto af = Q.apply_function([](const double& x) { return x * 2; }, 5.0, "double");
    CHECK(af.get({0, 0}) == 6 && af.get({0, 1}) == -8 && af.history().back().label == "double");
    auto af2 = Q.apply_function([](const double& x) { return x * 2; }, 7.0);
    CHECK(af2.get({0, 0}) == 0);
}

void test_arith_struct() {
    SECTION("arithmetic / transpose / reshape / reduce");
    auto A = rand_dense<double>({3, 4}, 20), B = rand_dense<double>({3, 4}, 21);
    auto As = rand_sparse<double>({3, 4}, 0.5, 22), Bs = rand_sparse<double>({3, 4}, 0.5, 23);
    CHECK(maxdiff(A + Bs, Bs + A) < 1e-15);
    CHECK((As + Bs).is_sparse() && !(As + B).is_sparse());
    CHECK(maxdiff((As + Bs).to_dense(), As.to_dense() + Bs.to_dense()) < 1e-15);
    CHECK(maxdiff(A * Bs, (A * Bs.to_dense())) < 1e-15);
    CHECK((As * B).is_sparse());
    auto sp1 = As + 1.0;
    CHECK(!sp1.is_sparse() && sp1.get({0, 0}) == As.get({0, 0}) + 1.0);  // honest scalar add
    CHECK((As + 0.0).is_sparse());
    CHECK(maxdiff(A - A, RecursiveTensor<double>::zeros({3, 4})) == 0);
    CHECK((2.0 * A).get({1, 1}) == 2 * A.get({1, 1}));
    CHECK_THROWS(A + rand_dense<double>({4, 3}, 1), ShapeError);

    auto X = rand_sparse<double>({2, 3, 4}, 0.5, 30);
    auto Tp = X.transpose({2, 0, 1});
    CHECK((Tp.shape() == Shape{4, 2, 3}) && Tp.get({3, 1, 2}) == X.get({1, 2, 3}));
    CHECK(maxdiff(X.to_dense().transpose({2, 0, 1}), Tp) == 0);
    auto Rs = X.reshape({6, 4});
    CHECK(Rs.get({5, 3}) == X.get({1, 2, 3}));
    CHECK_THROWS(X.reshape({5, 5}), ShapeError);
    auto Sp = X.split_axis(2, {2, 2});
    CHECK((Sp.shape() == Shape{2, 3, 2, 2}) && Sp.get({1, 2, 1, 1}) == X.get({1, 2, 3}));

    for (auto op : {ReduceOp::Sum, ReduceOp::Mean, ReduceOp::Max, ReduceOp::Min})
        for (std::size_t ax = 0; ax < 3; ++ax) {
            auto rd = X.to_dense().reduce(op, ax), rsps = X.reduce(op, ax);
            CHECK(maxdiff(*rd.values, *rsps.values) < 1e-14);
            CHECK(rd.arg == rsps.arg);  // incl. implicit-zero arg positions
        }
    auto S = X.reduce(ReduceOp::Sum, 1);
    double manual = X.get({1, 0, 2}) + X.get({1, 1, 2}) + X.get({1, 2, 2});
    CHECK(std::abs(S.values->get({1, 2}) - manual) < 1e-14);
    auto neg = RecursiveTensor<double>::from_cells({1, 3}, {{{0, 1}, -2.0}, {{0, 2}, 3.0}}, Storage::Sparse);
    auto mx = neg.reduce(ReduceOp::Max, 1), mn = neg.reduce(ReduceOp::Min, 1);
    CHECK(mx.arg[0] == 2 && mn.arg[0] == 1);
    auto neg2 = RecursiveTensor<double>::from_cells({1, 3}, {{{0, 1}, -2.0}, {{0, 2}, -3.0}}, Storage::Sparse);
    CHECK(neg2.reduce(ReduceOp::Max, 1).arg[0] == 0);  // implicit zero is the max
}

void test_decompositions() {
    SECTION("tucker / mps");
    auto X = rand_dense<double>({3, 4, 5}, 40);
    auto tk = X.tucker_decomposition(std::vector<std::size_t>{3, 4, 5});
    CHECK((tk.core->shape() == Shape{3, 4, 5}));
    CHECK(maxdiff(tk.reconstruct(), X) < 1e-10);
    auto tk2 = X.tucker_decomposition();  // default min(extent,5)
    CHECK((tk2.core->shape() == Shape{3, 4, 5}));
    auto small = X.tucker_decomposition(std::vector<std::size_t>{2, 2, 2});
    CHECK((small.core->shape() == Shape{2, 2, 2}));
    CHECK(maxdiff(small.reconstruct(), X) > 1e-3);  // lossy

    auto C = rand_dense<cd>({2, 3, 4, 2}, 41);
    auto tc = C.tucker_decomposition(std::vector<std::size_t>{2, 3, 4, 2});
    CHECK(maxdiff(tc.reconstruct(), C) < 1e-10);  // complex uses conj-transpose

    auto cores = X.to_mps();
    CHECK(cores.size() == 3 && cores[0].shape()[0] == 1 && cores[2].shape()[2] == 1);
    CHECK(cores[0].shape()[2] == cores[1].shape()[0]);
    CHECK(maxdiff(RecursiveTensor<double>::from_mps(cores), X) < 1e-10);
    auto trunc = X.to_mps(std::size_t{2});
    for (auto& c : trunc) CHECK(c.shape()[0] <= 2 && c.shape()[2] <= 2);
    CHECK(maxdiff(RecursiveTensor<double>::from_mps(trunc), X) > 1e-3);
    auto cm = C.to_mps();
    CHECK(maxdiff(RecursiveTensor<cd>::from_mps(cm), C) < 1e-10);
}

void test_geometry_signal() {
    SECTION("hyperbolic / temporal convolution / homology");
    auto A = rand_dense<float>({3, 4}, 50);
    auto H = A.to_hyperbolic_space(-1.0);
    static_assert(std::is_same_v<decltype(H)::value_type, std::complex<float>>);
    double md = 0;
    for (Extent i = 0; i < A.volume(); ++i) md = std::max(md, double(std::abs(std::abs(H.get_linear(i)) - std::abs(A.get_linear(i)))));
    CHECK(md < 1e-6);  // magnitude preserved
    CHECK(H.metadata().extra.at("hyperbolic") == "true");
    // origin cell has zero distance -> phase unchanged (real positive stays real)
    auto o = RecursiveTensor<double>::from_dense({2, 2}, {2.0, 0, 0, 0}).to_hyperbolic_space(-1);
    CHECK(std::abs(o.get({0, 0}) - cd(2, 0)) < 1e-12);
    CHECK(maxdiff(A.to_sparse().to_hyperbolic_space(-1).to_dense(), H) < 1e-6);

    // 'same' convolution along last axis, numpy semantics:
    // np.convolve([1,2,3,4],[1,0,-1],'same') = [2, 2, 2, -3]
    auto S = RecursiveTensor<double>::from_dense({2, 4}, {1, 2, 3, 4, 0, 0, 0, 0});
    auto cv = S.apply_temporal_convolution({1, 0, -1});
    CHECK(cv.get({0, 0}) == 2 && cv.get({0, 1}) == 2 && cv.get({0, 2}) == 2 && cv.get({0, 3}) == -3);
    // np.convolve([1,2,3,4],[1,1],'same') = [1,3,5,7]
    auto cv2 = S.apply_temporal_convolution({1, 1});
    CHECK(cv2.get({0, 0}) == 1 && cv2.get({0, 3}) == 7);
    // gap-aware sparse: ticks 0 and 3 stored; kernel [1,1] must not merge them
    auto G = RecursiveTensor<double>::from_cells({1, 4}, {{{0, 0}, 1.0}, {{0, 3}, 1.0}}, Storage::Sparse);
    auto gc = G.apply_temporal_convolution({1, 1});
    CHECK(maxdiff(gc, G.to_dense().apply_temporal_convolution({1, 1})) == 0);
    CHECK(gc.get({0, 1}) == 1.0 && gc.get({0, 3}) == 1.0);
    auto ax0 = rand_dense<double>({5, 3}, 51);
    CHECK(maxdiff(ax0.apply_temporal_convolution({0.25, 0.5, 0.25}, 0),
                  ax0.to_sparse().apply_temporal_convolution({0.25, 0.5, 0.25}, -2)) < 1e-14);

    // Homology: two separated clusters in a 1x10 line -> 2 essential H0 classes
    auto L = RecursiveTensor<double>::from_cells({1, 10}, {{{0, 0}, 1.0}, {{0, 1}, 1.0}, {{0, 7}, 1.0}, {{0, 8}, 1.0}}, Storage::Sparse);
    auto ph = L.persistent_homology();
    int essential = 0;
    for (auto& p : ph) if (p.dimension == 0 && std::isinf(p.death)) ++essential;
    CHECK(essential == 2);
    auto Ld = L.to_dense();
    CHECK(Ld.persistent_homology().size() == ph.size());
    // cycle: 2x2 block has a 4-cycle plus diagonals (dist sqrt2 < 2)
    auto sq = RecursiveTensor<double>::from_dense({2, 2}, {1, 1, 1, 1});
    auto pc = sq.persistent_homology(1, 2.0, 0.01, true);
    int h1 = 0;
    for (auto& p : pc) h1 += p.dimension == 1;
    CHECK(h1 == 3);  // 6 edges - 3 tree edges
}

void test_references() {
    SECTION("recursive references / fixed point");
    auto T = RecursiveTensor<double>::zeros({3});
    // x0 = 0.5*x0 + 1  -> fixed point 2 ; x1 = x0 (direct) ; x2 = 0.25*x1 + 0.5 -> 1
    T.add_reference({0}, {0}, RefType::Transform, {0.5, 1.0});
    T.add_reference({0}, {1}, RefType::Direct);
    T.add_reference({1}, {2}, RefType::Transform, {0.25, 0.5});
    auto rep = T.settle_references(200, 1e-13);
    CHECK(rep.converged);
    CHECK(std::abs(T.get({0}) - 2) < 1e-12 && std::abs(T.get({1}) - 2) < 1e-12 && std::abs(T.get({2}) - 1) < 1e-12);
    CHECK(T.history().back().code == OpCode::SettleReferences);
    auto D = RecursiveTensor<double>::zeros({1});
    D.add_reference({0}, {0}, RefType::Transform, {2.0, 1.0});  // expansive: diverges
    CHECK(!D.settle_references(20, 1e-12).converged);
    auto Fz = RecursiveTensor<cd>::from_dense({2}, {cd(0, 0), cd(-0.1, 0.1)});
    Fz.add_reference({1}, {0}, RefType::Fractal, {1.0, 2.0}, 64, 1e-14);
    auto fr = Fz.settle_references(50, 1e-12);
    CHECK(fr.converged);  // z = z^2 + c attracting fixed point for small c
    const cd z = Fz.get({0}), c(-0.1, 0.1);
    CHECK(std::abs(z * z + c - z) < 1e-9);
    CHECK_THROWS(T.add_reference({5}, {0}, RefType::Direct), IndexError);
}

template <class T> void io_roundtrip(const RecursiveTensor<T>& t, const std::string& path) {
    io::save(t, path);
    auto back = io::load<T>(path);
    CHECK(back.shape() == t.shape());
    CHECK(back.storage() == t.storage());
    CHECK(maxdiff(back, t) == 0.0);  // bit-exact values
    CHECK(back.uuid() == t.uuid());
    CHECK(back.metadata().description == t.metadata().description);
    CHECK(back.metadata().extra == t.metadata().extra);
    CHECK(back.history().size() == t.history().size());
    CHECK(back.references().size() == t.references().size());
    CHECK(back.metadata().operations_count == t.metadata().operations_count);
    CHECK(back.distribution() == t.distribution());
    CHECK(back.sparsity() == t.sparsity());
}

void test_io() {
    SECTION(".rta serialization");
    const std::string dir = "/tmp/rta_test";
    std::filesystem::create_directories(dir);
    auto f = rand_dense<float>({3, 4, 5}, 60).contract(rand_dense<float>({5, 2}, 61), {2}, {0});
    f.metadata().extra["role"] = "capability";
    io_roundtrip(f, dir + "/f32_dense.rta");
    io_roundtrip(rand_sparse<double>({7, 1, 9, 3}, 0.2, 62), dir + "/f64_sparse.rta");
    io_roundtrip(rand_dense<cf>({4, 4}, 63), dir + "/c64_dense.rta");
    auto cs = rand_sparse<cd>({5, 6}, 0.3, 64);
    cs.add_reference({0, 0}, {1, 1}, RefType::Fractal, {1.0, 2.0}, 8, 1e-9, 1);
    io_roundtrip(cs, dir + "/c128_sparse_refs.rta");
    io_roundtrip(RecursiveTensor<double>::zeros({}), dir + "/scalar.rta");
    io_roundtrip(RecursiveTensor<double>::zeros({3, 0}), dir + "/empty.rta");
    io_roundtrip(RecursiveTensor<float>::zeros({10, 10}, Storage::Sparse), dir + "/sparse_nnz0.rta");

    auto back = io::load<double>(dir + "/f64_sparse.rta");
    CHECK(back.references().empty());
    const auto& h0 = back.history();
    CHECK(!h0.empty() && h0.back().code == OpCode::Sparsify);

    // determinism: same tensor -> identical bytes
    io::save(cs, dir + "/a.rta");
    io::save(cs, dir + "/b.rta");
    CHECK(io::detail::read_file(dir + "/a.rta") == io::detail::read_file(dir + "/b.rta"));

    // dtype policy
    CHECK_THROWS(io::load<float>(dir + "/c64_dense.rta"), DTypeError);
    auto conv = io::load<double>(dir + "/f32_dense.rta", true);
    CHECK(maxdiff(conv, f.astype<double>()) == 0);
    auto any = io::load_any(dir + "/c128_sparse_refs.rta");
    CHECK(std::holds_alternative<RecursiveTensor<cd>>(any));

    // inspect
    auto info = io::inspect(dir + "/c128_sparse_refs.rta");
    CHECK(info.header.dtype == DType::C128 && info.header.storage == Storage::Sparse);
    std::vector<std::string> tags;
    for (auto& s : info.sections) tags.push_back(io::tag_str(s.tag));
    CHECK((tags == std::vector<std::string>{"SHAP", "SIDX", "SVAL", "REFS", "HIST", "META", "END "}));
    CHECK(info.header.section_count == info.sections.size());
    for (auto& s : info.sections) CHECK(s.crc_ok && s.offset % 64 == 0 && (s.offset + 32) % 32 == 0);

    // corruption: flip one payload byte -> CRC failure; flip header -> header CRC
    auto bytes = io::detail::read_file(dir + "/f32_dense.rta");
    auto flip = [&](std::size_t pos, const std::string& name) {
        auto b = bytes;
        b[pos] ^= 0x40;
        std::ofstream o(dir + "/" + name, std::ios::binary);
        o.write(reinterpret_cast<const char*>(b.data()), static_cast<std::streamsize>(b.size()));
    };
    auto finfo = io::inspect(dir + "/f32_dense.rta");
    flip(finfo.sections[1].offset + 40, "corrupt_payload.rta");
    CHECK_THROWS(io::load<float>(dir + "/corrupt_payload.rta"), FormatError);
    CHECK(!io::inspect(dir + "/corrupt_payload.rta").sections[1].crc_ok);
    // padding byte between SHAP and the next section (not CRC-covered) -> must still be rejected
    flip(finfo.sections[0].offset + 32 + finfo.sections[0].payload_bytes + 1, "corrupt_pad.rta");
    CHECK_THROWS(io::load<float>(dir + "/corrupt_pad.rta"), FormatError);
    flip(20, "corrupt_header.rta");
    CHECK_THROWS(io::load<float>(dir + "/corrupt_header.rta"), FormatError);
    {  // truncated
        std::ofstream o(dir + "/trunc.rta", std::ios::binary);
        o.write(reinterpret_cast<const char*>(bytes.data()), static_cast<std::streamsize>(bytes.size() - 70));
    }
    CHECK_THROWS(io::load<float>(dir + "/trunc.rta"), FormatError);
    {  // wrong magic
        auto b = bytes;
        b[0] = 'X';
        std::ofstream o(dir + "/magic.rta", std::ios::binary);
        o.write(reinterpret_cast<const char*>(b.data()), static_cast<std::streamsize>(b.size()));
    }
    CHECK_THROWS(io::load<float>(dir + "/magic.rta"), FormatError);

    // forward compat: splice an unknown non-critical section before END -> still loads;
    // same section marked critical -> rejected.
    auto splice = [&](std::uint32_t flags) {
        auto fi = io::inspect(dir + "/f32_dense.rta");
        const std::size_t end_off = fi.sections.back().offset;
        std::vector<std::uint8_t> out(bytes.begin(), bytes.begin() + static_cast<long>(end_off));
        std::ostringstream ss;
        io::detail::FileBuilder fb(ss);
        std::vector<std::uint8_t> payload{1, 2, 3, 4, 5};
        fb.section(io::fourcc("XTRA"), flags, 5, payload);
        auto s = ss.str();
        out.insert(out.end(), s.begin(), s.end());
        out.insert(out.end(), bytes.begin() + static_cast<long>(end_off), bytes.end());
        std::ofstream o(dir + "/spliced.rta", std::ios::binary);
        o.write(reinterpret_cast<const char*>(out.data()), static_cast<std::streamsize>(out.size()));
    };
    splice(0);
    CHECK(maxdiff(io::load<float>(dir + "/spliced.rta"), f) == 0);
    splice(io::kSectionCritical);
    CHECK_THROWS(io::load<float>(dir + "/spliced.rta"), FormatError);
    CHECK(!std::filesystem::exists(dir + "/a.rta.tmp"));  // atomic write cleaned up
}

void test_provenance() {
    SECTION("provenance: history, description caps, uuid");
    {
        auto a = RecursiveTensor<double>::from_dense({2}, {1, 2});
        a.set_description("");
        auto b = a.contract(a, {0}, {0});
        CHECK(b.metadata().description.rfind("Contraction of tensor ", 0) == 0);
    }
    auto a = rand_dense<double>({2, 2}, 70);
    auto b = rand_dense<double>({2, 2}, 71);
    auto c = a.contract(b, {1}, {0});
    CHECK(c.history().back().code == OpCode::Contract && c.history().back().peer == b.uuid());
    CHECK(c.uuid() != a.uuid());
    CHECK(c.metadata().operations_count == a.metadata().operations_count + 1);
    // exponential-growth guard: repeated self-contraction
    auto x = a;
    for (int i = 0; i < 40; ++i) x = x.contract(x, {1}, {0}).normalize();
    CHECK(x.history().size() <= x.history_limit());
    CHECK(x.metadata().description.size() <= 512);
    x.set_history_limit(5);
    CHECK(x.history().size() == 5);
}

int main() {
    test_construction();
    test_access();
    test_contract_t<float>("contract<float>");
    test_contract_t<cd>("contract<complex<double>>");
    test_expand_project_transform();
    test_embed_fractal();
    test_linalg();
    test_eigenstates();
    test_stats();
    test_arith_struct();
    test_decompositions();
    test_geometry_signal();
    test_references();
    test_io();
    test_provenance();
    std::printf("\n%d passed, %d failed\n", g_pass, g_fail);
    return g_fail;
}
