#include "codec.hpp"
#include "rw/runtime.hpp"
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <numeric>
namespace rw {
namespace {
Matrix projection(const Matrix &x, const Matrix &w, const Vector &b) {
    if (x.cols != w.cols || b.size() != w.rows)
        throw ValidationError("layer projection shape mismatch");
    validate(x, "layer input");
    validate(w, "projection");
    validate(b, "projection bias", w.rows);
    Matrix o(x.rows, w.rows);
    for (size_t i = 0; i < x.rows; i++)
        for (size_t j = 0; j < w.rows; j++) {
            float sum = b[j];
            for (size_t k = 0; k < x.cols; k++)
                sum += x(i, k) * w(j, k);
            o(i, j) = sum;
        }
    return o;
}
Matrix stack(RecursiveWeightSystem &registry, const EvaluationOptions &o) {
    auto keys = registry.keys();
    if (keys.empty())
        throw ValidationError("layer has no weights");
    auto values = registry.batch_compute(keys, o);
    size_t d = values.at(keys.front()).size();
    Matrix m(keys.size(), d);
    for (size_t i = 0; i < keys.size(); i++)
        for (size_t j = 0; j < d; j++)
            m(i, j) = values.at(keys[i])[j];
    return m;
}
LayerOutput mix(const Matrix &p, const Matrix &w, const Vector &gamma, const Vector &beta,
                double eps) {
    if (p.cols != w.cols)
        throw ValidationError("layer/weight dimensions mismatch");
    validate(gamma, "layer norm weight", p.cols);
    validate(beta, "layer norm bias", p.cols);
    if (!(eps > 0 && std::isfinite(eps)))
        throw ValidationError("invalid layer norm epsilon");
    LayerOutput out{Matrix(p.rows, p.cols), Matrix(p.rows, w.rows), w};
    for (size_t i = 0; i < p.rows; i++) {
        double maxlog = -INFINITY;
        for (size_t k = 0; k < w.rows; k++) {
            float logit = 0;
            for (size_t j = 0; j < p.cols; j++)
                logit += p(i, j) * w(k, j);
            out.attention(i, k) = logit;
            maxlog = std::max(maxlog, double(logit));
        }
        double total = 0;
        for (size_t k = 0; k < w.rows; k++) {
            out.attention(i, k) = float(std::exp(out.attention(i, k) - maxlog));
            total += out.attention(i, k);
        }
        for (size_t k = 0; k < w.rows; k++)
            out.attention(i, k) = float(out.attention(i, k) / total);
        double mean = 0;
        for (size_t j = 0; j < p.cols; j++) {
            float v = p(i, j);
            for (size_t k = 0; k < w.rows; k++)
                v += out.attention(i, k) * w(k, j);
            out.output(i, j) = v;
            mean += v;
        }
        mean /= p.cols;
        double var = 0;
        for (size_t j = 0; j < p.cols; j++)
            var += std::pow(out.output(i, j) - mean, 2);
        double inv = 1 / std::sqrt(var / p.cols + eps);
        for (size_t j = 0; j < p.cols; j++)
            out.output(i, j) = float((out.output(i, j) - mean) * inv * gamma[j] + beta[j]);
    }
    validate(out.output, "layer result");
    return out;
}
} // namespace
RecursiveWeightLayer::RecursiveWeightLayer(size_t in, size_t out, size_t n, Config c, uint32_t seed)
    : registry(c), input_projection(out, in), input_bias(out), norm_weight(out, 1), norm_bias(out) {
    if (!in || !out || !n || n > 1000)
        throw ValidationError("invalid layer dimensions/count");
    std::mt19937 rng(seed);
    std::normal_distribution<float> normal(0, 1);
    std::uniform_real_distribution<float> uniform(0, 1);
    Matrix cb(n, out);
    for (float &x : cb.data)
        x = normal(rng) * .02f;
    registry.set_codebook(cb);
    std::uniform_real_distribution<float> linear(-1 / std::sqrt(float(in)),
                                                 1 / std::sqrt(float(in)));
    for (float &x : input_projection.data)
        x = linear(rng);
    for (float &x : input_bias)
        x = linear(rng);
    std::uniform_int_distribution<int> offset(-2, 2);
    for (size_t i = 0; i < n; i++) {
        Position p{int32_t(i % 5), int32_t(i / 5 % 5), int32_t(i / 25 % 5), int32_t(i / 125 % 5),
                   int32_t(i / 625 % 5)};
        auto w = RecursiveWeight::neutral(out, uint32_t(i), p);
        w.config = c;
        size_t harmonics = std::min(size_t(5), i + 1);
        w.phase.harmonic_amplitudes = Matrix(harmonics, out);
        w.phase.frequencies = Vector(harmonics);
        w.phase.phase_offsets = Vector(harmonics);
        for (float &x : w.phase.base_phase)
            x = normal(rng) * .1f;
        for (float &x : w.phase.harmonic_amplitudes.data)
            x = normal(rng) * .05f;
        for (float &x : w.phase.frequencies)
            x = uniform(rng) * 2;
        for (float &x : w.phase.phase_offsets)
            x = uniform(rng) * 6.283185307f;
        size_t refs = std::min(size_t(4), std::max(size_t(2), i % 5));
        for (size_t j = 0; j < refs; j++) {
            RecursiveReference r;
            for (auto &x : r.relative_position)
                x = offset(rng);
            r.transformation_matrix = Matrix::identity(out);
            for (float &x : r.transformation_matrix.data)
                x += normal(rng) * .01f;
            r.contribution_weight = .1 / (j + 1);
            r.temporal_offset = int32_t(j);
            w.recursive_refs.push_back(std::move(r));
        }
        registry.register_weight("weight_" + std::to_string(i), w);
    }
}
LayerOutput RecursiveWeightLayer::forward(const Matrix &x, EvaluationOptions o) {
    return mix(projection(x, input_projection, input_bias), stack(registry, o), norm_weight,
               norm_bias, norm_epsilon);
}
Matrix RecursiveWeightLayer::compute_layer_jacobian(const Vector &x, EvaluationOptions o) {
    validate(x, "Jacobian input", input_projection.cols);
    Matrix input(1, x.size(), x);
    auto p = projection(input, input_projection, input_bias);
    auto weights = stack(registry, o);
    auto mixed = mix(p, weights, norm_weight, norm_bias, norm_epsilon);
    size_t d = p.cols;
    Vector mean_weight(d), z(d);
    for (size_t j = 0; j < d; j++) {
        for (size_t k = 0; k < weights.rows; k++)
            mean_weight[j] += mixed.attention(0, k) * weights(k, j);
        z[j] = p(0, j) + mean_weight[j];
    }
    Matrix mixer = Matrix::identity(d);
    for (size_t a = 0; a < d; a++)
        for (size_t b = 0; b < d; b++) {
            double covariance = 0;
            for (size_t k = 0; k < weights.rows; k++)
                covariance += mixed.attention(0, k) * weights(k, a) * weights(k, b);
            mixer(a, b) += float(covariance - mean_weight[a] * mean_weight[b]);
        }
    double mean = std::accumulate(z.begin(), z.end(), 0.) / d, var = 0;
    for (float v : z)
        var += std::pow(v - mean, 2);
    double inv = 1 / std::sqrt(var / d + norm_epsilon);
    Matrix ln(d, d);
    for (size_t a = 0; a < d; a++)
        for (size_t b = 0; b < d; b++)
            ln(a, b) = float(
                norm_weight[a] * inv *
                ((a == b ? 1. : 0.) - 1. / d - (z[a] - mean) * (z[b] - mean) * inv * inv / d));
    return matmul(matmul(ln, mixer), input_projection);
}
Metrics RecursiveWeightLayer::analyze_attention_patterns(const Matrix &x, EvaluationOptions o) {
    auto out = forward(x, o);
    double entropy = 0, concentration = 0, max = 0;
    for (size_t i = 0; i < out.attention.rows; i++) {
        double e = 0, m = 0;
        for (size_t j = 0; j < out.attention.cols; j++) {
            double p = out.attention(i, j);
            e -= p * std::log(p + 1e-8);
            m = std::max(m, p);
        }
        entropy += e;
        concentration += 1 / std::max(e, 1e-8);
        max += m;
    }
    double rows = double(out.attention.rows);
    if (!rows)
        throw ValidationError("attention analysis requires nonempty batch");
    return {{"attention_entropy", entropy / rows},
            {"attention_concentration", concentration / rows},
            {"max_attention", max / rows}};
}
std::map<uint32_t, Metrics>
RecursiveWeightLayer::analyze_recursive_flow(const Matrix &x, const std::vector<uint32_t> &depths) {
    std::map<uint32_t, Metrics> r;
    for (auto d : depths) {
        EvaluationOptions o;
        o.depth = d;
        o.time = 1;
        o.strict_references = false;
        auto v = forward(x, o).output.data;
        double mean = std::accumulate(v.begin(), v.end(), 0.) / v.size(), var = 0, zeros = 0;
        for (float a : v) {
            var += std::pow(a - mean, 2);
            zeros += std::abs(a) < 1e-6;
        }
        r[d] = {{"output_norm", norm(v)},
                {"output_variance", v.size() > 1 ? var / (v.size() - 1) : 0},
                {"output_sparsity", zeros / v.size()}};
    }
    return r;
}
void RecursiveWeightLayer::save(const std::string &path) const {
    auto bytes = registry.serialize_system_binary();
    detail::Writer w;
    w.magic("RWLY");
    w.u16(0x0100);
    w.matrix(input_projection);
    w.vector(input_bias);
    w.vector(norm_weight);
    w.vector(norm_bias);
    w.f64(norm_epsilon);
    w.u64(bytes.size());
    w.bytes(bytes.data(), bytes.size());
    w.checksum();
    detail::atomic_write(path, w.data);
}
void RecursiveWeightLayer::load(const std::string &path) {
    detail::MappedFile f(path);
    detail::verify_checksum(f.data(), f.size());
    detail::Reader r(f.data(), f.size() - 32);
    r.magic("RWLY");
    if (r.u16() != 0x0100)
        throw FormatError("unsupported layer version");
    auto projection = r.matrix();
    auto bias = r.vector(), gamma = r.vector(), beta = r.vector();
    double epsilon = r.f64();
    validate(bias, "layer bias", projection.rows);
    validate(gamma, "layer gamma", projection.rows);
    validate(beta, "layer beta", projection.rows);
    if (!projection.rows || !projection.cols || epsilon <= 0)
        throw FormatError("invalid layer configuration");
    auto size = r.u64();
    r.need(size);
    RecursiveWeightSystem check;
    check.deserialize_system_binary(r.data + r.pos, size);
    if (check.codebook().cols != projection.rows)
        throw FormatError("layer registry dimensions mismatch");
    size_t offset = r.pos;
    r.pos += size;
    r.end();
    registry.deserialize_system_binary(r.data + offset, size);
    input_projection = std::move(projection);
    input_bias = std::move(bias);
    norm_weight = std::move(gamma);
    norm_bias = std::move(beta);
    norm_epsilon = epsilon;
}
} // namespace rw
