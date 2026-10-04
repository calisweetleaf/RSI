#include "rw/runtime.hpp"
#include <algorithm>
#include <climits>
#include <cmath>
#include <limits>
#include <numeric>
#if defined(__x86_64__) || defined(__i386__)
#include <immintrin.h>
#endif
extern "C" {
void dgeev_(const char *, const char *, const int *, double *, const int *, double *, double *,
            double *, const int *, double *, const int *, double *, const int *, int *);
void dgesvd_(const char *, const char *, const int *, const int *, double *, const int *, double *,
             double *, const int *, double *, const int *, double *, const int *, int *);
}
namespace rw {
namespace {
size_t product(size_t a, size_t b) {
    if (b && a > SIZE_MAX / b)
        throw ValidationError("matrix size overflow");
    return a * b;
}
void require(bool v, const char *m) {
    if (!v)
        throw ValidationError(m);
}
std::vector<double> column_major(const Matrix &m) {
    validate(m, "matrix");
    std::vector<double> a(m.data.size());
    for (size_t i = 0; i < m.rows; i++)
        for (size_t j = 0; j < m.cols; j++)
            a[j * m.rows + i] = m(i, j);
    return a;
}
struct SVD {
    std::vector<double> s, u, vt;
};
SVD svd(const Matrix &m, bool vectors) {
    require(m.rows > 0 && m.cols > 0 && m.rows <= INT_MAX && m.cols <= INT_MAX,
            "invalid SVD dimensions");
    int r = int(m.rows), c = int(m.cols), k = std::min(r, c), lda = r, ldu = vectors ? r : 1,
        ldvt = vectors ? k : 1, info = 0, lwork = -1;
    auto a = column_major(m);
    SVD s;
    s.s.resize(k);
    s.u.resize(vectors ? r * k : 1);
    s.vt.resize(vectors ? k * c : 1);
    char job = vectors ? 'S' : 'N';
    double query = 0;
    dgesvd_(&job, &job, &r, &c, a.data(), &lda, s.s.data(), s.u.data(), &ldu, s.vt.data(), &ldvt,
            &query, &lwork, &info);
    if (info || !std::isfinite(query) || query > INT_MAX)
        throw Error("LAPACK SVD workspace query failed");
    lwork = std::max(1, int(query));
    std::vector<double> work(lwork);
    dgesvd_(&job, &job, &r, &c, a.data(), &lda, s.s.data(), s.u.data(), &ldu, s.vt.data(), &ldvt,
            work.data(), &lwork, &info);
    if (info)
        throw Error("LAPACK SVD did not converge");
    return s;
}
void pair_sizes(const Vector &a, const Vector &b) {
    require(a.size() == b.size(), "paired arrays must have equal lengths");
}
void gamma_valid(double g) {
    require(std::isfinite(g) && g >= 0 && g < 1, "contraction factor must be in [0,1)");
}
} // namespace
Matrix::Matrix(size_t r, size_t c, float f) : rows(r), cols(c), data(product(r, c), f) {}
Matrix::Matrix(size_t r, size_t c, Vector v) : rows(r), cols(c), data(std::move(v)) {
    require(data.size() == product(r, c), "matrix payload shape mismatch");
}
Matrix Matrix::identity(size_t n) {
    Matrix m(n, n);
    for (size_t i = 0; i < n; i++)
        m(i, i) = 1;
    return m;
}
void validate(const Vector &v, const std::string &name, std::optional<size_t> n, double bound) {
    if (n && v.size() != *n)
        throw ValidationError(name + ": shape mismatch");
    for (float x : v)
        if (!std::isfinite(x) || std::abs(x) > bound)
            throw ValidationError(name + ": non-finite or out-of-range value");
}
void validate(const Matrix &m, const std::string &n) {
    if (m.data.size() != product(m.rows, m.cols))
        throw ValidationError(n + ": matrix shape mismatch");
    validate(m.data, n);
}
double norm(const Vector &v) {
    double s = 0;
    for (float x : v)
        s += double(x) * x;
    return std::sqrt(s);
}
Vector matvec(const Matrix &m, const Vector &v) {
    if (m.cols != v.size())
        throw ValidationError("matvec shape mismatch");
    Vector out(m.rows);
    for (size_t i = 0; i < m.rows; i++) {
        float sum = 0;
        for (size_t j = 0; j < m.cols; j++)
            sum += m(i, j) * v[j];
        out[i] = sum;
    }
    return out;
}
Matrix matmul(const Matrix &a, const Matrix &b) {
    if (a.cols != b.rows)
        throw ValidationError("matmul shape mismatch");
    Matrix c(a.rows, b.cols);
    for (size_t i = 0; i < a.rows; i++)
        for (size_t k = 0; k < a.cols; k++)
            for (size_t j = 0; j < b.cols; j++)
                c(i, j) += a(i, k) * b(k, j);
    return c;
}
std::vector<std::complex<double>> eigenvalues(const Matrix &m) {
    require(m.rows == m.cols && m.rows > 0 && m.rows <= INT_MAX,
            "eigenvalues require a nonempty square matrix");
    int n = int(m.rows), lda = n, one = 1, lwork = -1, info = 0;
    char no = 'N';
    auto a = column_major(m);
    std::vector<double> wr(n), wi(n);
    double unused = 0, query = 0;
    dgeev_(&no, &no, &n, a.data(), &lda, wr.data(), wi.data(), &unused, &one, &unused, &one, &query,
           &lwork, &info);
    if (info || !std::isfinite(query) || query > INT_MAX)
        throw Error("LAPACK eigensolver workspace query failed");
    lwork = std::max(1, int(query));
    std::vector<double> work(lwork);
    dgeev_(&no, &no, &n, a.data(), &lda, wr.data(), wi.data(), &unused, &one, &unused, &one,
           work.data(), &lwork, &info);
    if (info)
        throw Error("LAPACK eigensolver did not converge");
    std::vector<std::complex<double>> out(n);
    for (int i = 0; i < n; i++)
        out[i] = {wr[i], wi[i]};
    return out;
}
double spectral_radius(const Matrix &m) {
    double s = 0;
    for (auto x : eigenvalues(m))
        s = std::max(s, std::abs(x));
    return s;
}
double spectral_norm(const Matrix &m) {
    return svd(m, false).s.front();
}
size_t matrix_rank(const Matrix &m) {
    auto s = svd(m, false).s;
    double tol = std::max(m.rows, m.cols) * std::numeric_limits<float>::epsilon() * s.front();
    return std::count_if(s.begin(), s.end(), [&](double x) { return x > tol; });
}
Matrix stabilize_matrix(const Matrix &m, double max) {
    require(std::isfinite(max) && max > 0, "invalid singular value cap");
    auto s = svd(m, true);
    Matrix o(m.rows, m.cols);
    size_t k = s.s.size();
    for (size_t i = 0; i < m.rows; i++)
        for (size_t j = 0; j < m.cols; j++) {
            double x = 0;
            for (size_t q = 0; q < k; q++)
                x += s.u[q * m.rows + i] * std::min(s.s[q], max) * s.vt[j * k + q];
            o(i, j) = float(x);
        }
    return o;
}
std::string position_key(const Position &p) {
    std::string s;
    for (auto x : p) {
        if (!s.empty())
            s += '_';
        s += std::to_string(x);
    }
    return s;
}
Position add_position(const Position &a, const Position &b) {
    Position c{};
    for (size_t i = 0; i < 5; i++) {
        int64_t v = int64_t(a[i]) + b[i];
        if (v < INT32_MIN || v > INT32_MAX)
            throw ValidationError("position overflow");
        c[i] = int32_t(v);
    }
    return c;
}
#if defined(__x86_64__) || defined(__i386__)
__attribute__((target("avx2"))) static void add_avx(float *out, const float *b, const float *d,
                                                    const float *r, const float *p, const float *e,
                                                    size_t n) {
    size_t i = 0;
    for (; i + 8 <= n; i += 8) {
        auto x = _mm256_add_ps(_mm256_loadu_ps(b + i), _mm256_loadu_ps(d + i));
        x = _mm256_add_ps(x, _mm256_loadu_ps(r + i));
        x = _mm256_add_ps(x, _mm256_loadu_ps(p + i));
        x = _mm256_add_ps(x, _mm256_loadu_ps(e + i));
        _mm256_storeu_ps(out + i, x);
    }
    for (; i < n; i++)
        out[i] = b[i] + d[i] + r[i] + p[i] + e[i];
}
#endif
std::string simd_backend() {
#if defined(__x86_64__) || defined(__i386__)
    return __builtin_cpu_supports("avx2") ? "AVX2" : "scalar";
#else
    return "scalar";
#endif
}
void add_components(Vector &o, const Vector &b, const Vector &d, const Vector &r, const Vector &p,
                    const Vector &e, bool simd) {
    for (auto v : {&d, &r, &p, &e})
        pair_sizes(b, *v);
    o.resize(b.size());
#if defined(__x86_64__) || defined(__i386__)
    if (simd && __builtin_cpu_supports("avx2")) {
        add_avx(o.data(), b.data(), d.data(), r.data(), p.data(), e.data(), b.size());
        return;
    }
#else
    (void)simd;
#endif
    for (size_t i = 0; i < b.size(); i++)
        o[i] = b[i] + d[i] + r[i] + p[i] + e[i];
}
void Config::validate() const {
    require(max_recursion_depth > 0 && max_recursion_depth <= 100, "max depth must be 1..100");
    require(stability_check_interval > 0 && thread_pool_size > 0 && thread_pool_size <= 256,
            "invalid interval/thread count");
    require(std::isfinite(convergence_threshold) && convergence_threshold > 0,
            "invalid convergence threshold");
    require(ema_momentum >= 0 && ema_momentum <= 1 && damping_factor > 0 && damping_factor <= 1,
            "invalid EMA/damping");
    require(std::isfinite(max_growth_ratio) && max_growth_ratio > 0 &&
                std::isfinite(spectral_radius_threshold) && spectral_radius_threshold > 0,
            "invalid stability thresholds");
}
void PhaseTransformation::validate(size_t d) const {
    rw::validate(base_phase, "base phase", d);
    require(!scalar_amplitudes || harmonic_amplitudes.cols == 1,
            "scalar amplitudes must have one column");
    rw::validate(harmonic_amplitudes, "amplitudes");
    require(harmonic_amplitudes.cols == d || harmonic_amplitudes.cols == 1,
            "harmonic amplitude dimensions");
    rw::validate(frequencies, "frequencies", harmonic_amplitudes.rows);
    rw::validate(phase_offsets, "phase offsets", harmonic_amplitudes.rows);
}
Vector PhaseTransformation::evaluate(double t, bool bounds) const {
    require(std::isfinite(t) && std::abs(t) <= 1e6, "time must be finite and within source bound");
    Vector o = base_phase;
    for (size_t h = 0; h < frequencies.size(); h++) {
        float s = std::sin(float(frequencies[h] * t + phase_offsets[h]));
        for (size_t j = 0; j < o.size(); j++)
            o[j] += harmonic_amplitudes(h, harmonic_amplitudes.cols == 1 ? 0 : j) * s;
    }
    if (bounds)
        for (float &x : o)
            x = std::clamp(x, -1000.f, 1000.f);
    rw::validate(o, "phase result", {}, std::numeric_limits<double>::infinity());
    return o;
}
Vector DeltaComponent::evaluate(uint32_t depth, bool bounds) const {
    Vector o(base_delta.size());
    double factor = std::pow(depth_scaling, depth);
    for (size_t j = 0; j < o.size(); j++) {
        double v = base_delta[j] * factor * (adaptive_factor.empty() ? 1 : adaptive_factor[j]);
        if (bounds)
            v = std::clamp(v, -1000., 1000.);
        o[j] = float(v);
    }
    rw::validate(o, "delta result", {}, std::numeric_limits<double>::infinity());
    return o;
}
Metrics StabilityMetrics::as_map() const {
    return {{"spectral_radius", spectral_radius},
            {"lyapunov_coefficient", lyapunov_coefficient},
            {"error_bound", error_bound},
            {"convergence_rate", convergence_rate},
            {"fractal_dimension", fractal_dimension},
            {"self_similarity_metric", self_similarity_metric},
            {"information_capacity", information_capacity},
            {"compression_efficiency_proxy", compression_efficiency}};
}
Vector DynamicalSystemsAnalyzer::fixed_point(double a, const Vector &b) {
    require(std::isfinite(a) && std::abs(a) < 1, "fixed-point alpha must have magnitude <1");
    Vector o = b;
    for (auto &x : o)
        x = float(x / (1 - a));
    return o;
}
bool DynamicalSystemsAnalyzer::lyapunov_stable(const std::vector<Matrix> &m) {
    for (auto &a : m)
        if (norm(a.data) >= 1. / m.size())
            return false;
    return true;
}
double DynamicalSystemsAnalyzer::attractor_dimension(const std::vector<Matrix> &m) {
    if (m.empty())
        return 0;
    double s = 0, lambda = 0;
    for (auto &a : m) {
        s += std::log(norm(a.data) + 1e-8);
        for (auto e : eigenvalues(a))
            lambda = std::max(lambda, e.real());
    }
    double d = m.front().rows;
    if (lambda <= 0)
        return d;
    if (lambda == 1)
        throw ValidationError("attractor expression undefined at eigenvalue 1");
    return std::max(0., std::min(d, s / std::log(lambda)));
}
double DynamicalSystemsAnalyzer::capacity_amplification(double b, const Vector &bits,
                                                        const Vector &mult) {
    pair_sizes(bits, mult);
    double exponent = b;
    for (size_t i = 0; i < bits.size(); i++)
        exponent += bits[i] * mult[i];
    return std::exp2(exponent);
}
bool DynamicalSystemsAnalyzer::approximation_parameter_count(size_t d, size_t k, size_t depth) {
    return double(d) + double(k) * d * d * depth >= double(d) * (d + 1.);
}
double DynamicalSystemsAnalyzer::kolmogorov_expression(double full) {
    return full <= 1 ? 1 : full * std::log(full);
}
double DynamicalSystemsAnalyzer::uniform_convergence_bound(double g, double C, uint32_t n) {
    gamma_valid(g);
    require(C >= 0 && std::isfinite(C), "invalid bound constant");
    return C * std::pow(g, n) / (1 - g);
}
uint32_t DynamicalSystemsAnalyzer::convergence_steps(double e, double g, double C) {
    gamma_valid(g);
    require(e > 0 && std::isfinite(e) && C >= 0 && std::isfinite(C),
            "invalid convergence arguments");
    if (C == 0 || C / (1 - g) <= e)
        return 0;
    if (g == 0)
        return 1;
    double n = std::ceil(std::log(e * (1 - g) / C) / std::log(g));
    require(n <= UINT32_MAX, "required depth exceeds uint32");
    return uint32_t(std::max(1., n));
}
double DynamicalSystemsAnalyzer::computational_complexity(double n, double d, double e) {
    require(e > 0, "epsilon must be positive");
    return n * d * d + d * d * d * std::log(1 / e);
}
double DynamicalSystemsAnalyzer::error_accumulation_bound(double initial, const Vector &errors,
                                                          double decay) {
    require(decay >= 0 && decay <= 1, "invalid decay");
    double out = initial;
    for (size_t i = 0; i < errors.size(); i++)
        out += errors[i] * std::pow(1 - decay, errors.size() - i - 1);
    return out;
}
double DynamicalSystemsAnalyzer::error_correction_capacity(double g, double e) {
    gamma_valid(g);
    return (1 - g) * e / (1 + g);
}
double DynamicalSystemsAnalyzer::weight_space_dimension(double b, const Vector &d,
                                                        const Vector &s) {
    pair_sizes(d, s);
    for (size_t i = 0; i < d.size(); i++) {
        require(s[i] != -1, "singular dimension scaling");
        b += d[i] / std::pow(1 + s[i], 2);
    }
    return b;
}
double DynamicalSystemsAnalyzer::self_similarity(const std::vector<Matrix> &m) {
    if (m.empty())
        return 0;
    double s = 0;
    for (auto &a : m)
        if (std::pow(norm(a.data), 2) > 1e-8)
            s += 1;
    return s / m.size();
}
double DynamicalSystemsAnalyzer::multiscale_efficiency(
    double full, double base, const std::vector<std::pair<double, double>> &p, double d) {
    for (auto [n, s] : p) {
        require(s > 0, "scale must be positive");
        base += n * std::pow(s, -d);
    }
    return base == 0 ? INFINITY : full / base;
}
double DynamicalSystemsAnalyzer::minimum_description_length(const Vector &e, double mi) {
    return std::accumulate(e.begin(), e.end(), mi);
}
double DynamicalSystemsAnalyzer::information_capacity(double b, const Vector &bits,
                                                      const Vector &p) {
    pair_sizes(bits, p);
    for (size_t i = 0; i < bits.size(); i++)
        b += bits[i] * std::pow(p[i], i + 1);
    return b;
}
double DynamicalSystemsAnalyzer::compression_efficiency(double n, double q, double p, double pb,
                                                        double r, double rb, double b, double bb) {
    double den = p * pb + r * rb + b * bb;
    return den == 0 ? INFINITY : n * q / den;
}
} // namespace rw
