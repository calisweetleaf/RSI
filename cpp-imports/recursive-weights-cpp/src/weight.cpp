#include "rw/runtime.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <numeric>
namespace rw {
namespace {
constexpr double pi = 3.14159265358979323846;
void require(bool x, const char *m) {
    if (!x)
        throw ValidationError(m);
}
double log_elements(size_t n) {
    return n ? std::log2(double(n)) : 0;
}
Vector all_weights(const RecursiveWeight &w) {
    Vector a = w.phase.base_phase;
    a.insert(a.end(), w.phase.harmonic_amplitudes.data.begin(),
             w.phase.harmonic_amplitudes.data.end());
    for (auto &r : w.recursive_refs) {
        a.push_back(float(r.contribution_weight));
        a.insert(a.end(), r.transformation_matrix.data.begin(), r.transformation_matrix.data.end());
    }
    return a;
}
// Deliberately retains numpy.histogram(density=True) behavior as a labeled source proxy.
double density_entropy(const Vector &a) {
    if (a.empty())
        return 0;
    auto [lo, hi] = std::minmax_element(a.begin(), a.end());
    double l = *lo, h = *hi;
    if (l == h) {
        l -= .5;
        h += .5;
    }
    double width = (h - l) / 50;
    std::array<size_t, 50> counts{};
    for (float x : a) {
        size_t b = std::min(size_t((x - l) / width), size_t(49));
        counts[b]++;
    }
    double e = 0;
    for (auto n : counts)
        if (n) {
            double p = n / (a.size() * width);
            e -= p * std::log(p + 1e-10);
        }
    return e;
}
void noise(Vector &v, std::mt19937 &rng, double sigma) {
    require(std::isfinite(sigma) && sigma >= 0, "invalid mutation deviation");
    std::normal_distribution<double> dist(0, 1);
    for (float &x : v)
        x += float(dist(rng) * sigma);
}
void compatible(const RecursiveWeight &a, const RecursiveWeight &b) {
    require(a.dimension() == b.dimension(), "crossover dimension mismatch");
    require(a.phase.harmonic_amplitudes.rows == b.phase.harmonic_amplitudes.rows &&
                a.phase.harmonic_amplitudes.cols == b.phase.harmonic_amplitudes.cols,
            "crossover harmonic shape mismatch");
}
} // namespace
RecursiveWeight RecursiveWeight::neutral(size_t d, uint32_t b, Position p) {
    require(d > 0, "dimension must be positive");
    RecursiveWeight w;
    w.base_codebook_index = b;
    w.tensor_position = p;
    w.phase.base_phase = Vector(d);
    w.phase.harmonic_amplitudes = Matrix(0, d);
    w.error_preservation = Vector(d);
    w.delta.base_delta = Vector(d);
    w.delta.adaptive_factor = Vector(d, 1);
    return w;
}
void RecursiveWeight::validate() const {
    config.validate();
    require(dimension() > 0, "empty weight");
    rw::validate(error_preservation, "error");
    phase.validate(dimension());
    rw::validate(delta.base_delta, "delta", dimension());
    if (!delta.adaptive_factor.empty())
        rw::validate(delta.adaptive_factor, "adaptive factor", dimension());
    require(std::isfinite(delta.depth_scaling), "invalid delta scaling");
    require(std::isfinite(scale_factor) && std::abs(scale_factor) <= 100, "invalid scale factor");
    require(recursive_refs.size() <= 50, "source maximum 50 references exceeded");
    for (auto &r : recursive_refs) {
        require(std::isfinite(r.contribution_weight) && std::abs(r.contribution_weight) <= 10,
                "invalid reference contribution");
        rw::validate(r.transformation_matrix, "reference matrix");
        require(r.transformation_matrix.rows == dimension() &&
                    r.transformation_matrix.cols == dimension(),
                "reference must be d x d");
    }
}
Vector RecursiveWeight::compute_phase_value(double t, Semantics mode) const {
    return phase.evaluate(t, mode == Semantics::Python);
}
Vector RecursiveWeight::compute_delta_value(uint32_t d, Semantics mode) const {
    return delta.evaluate(d, mode == Semantics::Python);
}
Matrix RecursiveWeight::compute_jacobian_matrix() const {
    Matrix j(dimension(), dimension());
    for (auto &r : recursive_refs)
        for (size_t i = 0; i < j.data.size(); i++)
            j.data[i] += float(r.contribution_weight * r.transformation_matrix.data[i]);
    return j;
}
double RecursiveWeight::contraction_bound() const {
    double n = 0;
    for (auto &r : recursive_refs)
        n += std::abs(r.contribution_weight) * norm(r.transformation_matrix.data);
    return n;
}
double RecursiveWeight::estimate_contraction_factor() const {
    return contraction_bound() / std::max(size_t(1), recursive_refs.size());
}
StabilityMetrics RecursiveWeight::get_stability_metrics() const {
    validate();
    StabilityMetrics m;
    m.spectral_radius = recursive_refs.empty() ? 0 : rw::spectral_radius(compute_jacobian_matrix());
    m.lyapunov_coefficient = contraction_bound() - 1;
    double gamma = estimate_contraction_factor();
    m.error_bound = gamma < 1 ? (norm(error_preservation) + 1) / (1 - gamma) : INFINITY;
    m.convergence_rate = gamma == 0 ? INFINITY : gamma < 1 ? -std::log(gamma) : 0;
    m.fractal_dimension = dimension();
    std::vector<Matrix> matrices;
    m.information_capacity = log_elements(dimension());
    for (size_t i = 0; i < recursive_refs.size(); i++) {
        auto &r = recursive_refs[i];
        m.fractal_dimension +=
            matrix_rank(r.transformation_matrix) / std::pow(1 + std::abs(r.contribution_weight), 2);
        matrices.push_back(r.transformation_matrix);
        m.information_capacity += log_elements(r.transformation_matrix.data.size()) *
                                  std::pow(std::abs(r.contribution_weight), i + 1);
    }
    m.self_similarity_metric = DynamicalSystemsAnalyzer::self_similarity(matrices);
    m.compression_efficiency = DynamicalSystemsAnalyzer::compression_efficiency(
        dimension(), 32, 1, log_elements(dimension()), recursive_refs.size(), 32 * dimension(), 1,
        32);
    return m;
}
Vector RecursiveWeight::compute_fixed_point_estimate(const Matrix &c, double t) const {
    require(base_codebook_index < c.rows && c.cols == dimension(), "codebook shape/index mismatch");
    double g = estimate_contraction_factor();
    require(g < 1, "source fixed-point proxy requires gamma < 1");
    auto p = compute_phase_value(t);
    auto d = compute_delta_value(0);
    Vector out(dimension());
    for (size_t j = 0; j < out.size(); j++)
        out[j] =
            float((c(base_codebook_index, j) * scale_factor + d[j] + p[j] + error_preservation[j]) /
                  (1 - g));
    return out;
}
Vector RecursiveWeight::apply_recursive_transformation(const Vector &input) const {
    rw::validate(input, "recursive transform input", dimension());
    Vector p = input;
    for (size_t j = 0; j < p.size(); j++)
        p[j] += phase.base_phase[j];
    for (size_t i = 0; i < phase.frequencies.size() && i < p.size(); i++) {
        require(phase.harmonic_amplitudes.cols == 1,
                "Python state transform only defines scalar harmonic amplitudes; use "
                "phase.evaluate for vector harmonics");
        p[i] += phase.harmonic_amplitudes(i, 0) *
                std::sin(phase.frequencies[i] * p[i] + phase.phase_offsets[i]);
    }
    Vector out = p;
    for (auto &r : recursive_refs) {
        auto v = matvec(r.transformation_matrix, p);
        for (size_t j = 0; j < out.size(); j++)
            out[j] += float(r.contribution_weight * v[j]);
    }
    for (size_t j = 0; j < out.size(); j++)
        out[j] += error_preservation[j];
    return out;
}
Metrics RecursiveWeight::information_theoretic_bounds() const {
    auto a = all_weights(*this);
    double entropy = density_entropy(a), mi = 0;
    Vector rv;
    for (auto &r : recursive_refs)
        rv.insert(rv.end(), r.transformation_matrix.data.begin(),
                  r.transformation_matrix.data.end());
    size_t n = std::min(rv.size(), phase.base_phase.size());
    if (n > 1) {
        double ma = 0, mb = 0;
        for (size_t i = 0; i < n; i++) {
            ma += phase.base_phase[i];
            mb += rv[i];
        }
        ma /= n;
        mb /= n;
        double va = 0, vb = 0, cov = 0;
        for (size_t i = 0; i < n; i++) {
            double x = phase.base_phase[i] - ma, y = rv[i] - mb;
            va += x * x;
            vb += y * y;
            cov += x * y;
        }
        if (va > 0 && vb > 0) {
            double corr = std::clamp(cov / std::sqrt(va * vb), -1., 1.);
            mi = -.5 * std::log(1 - corr * corr + 1e-10);
        } else
            mi = std::numeric_limits<double>::quiet_NaN();
    }
    double signal = std::pow(norm(phase.base_phase), 2) / dimension(),
           noise_power = std::pow(norm(error_preservation), 2) / dimension();
    return {{"density_histogram_entropy_proxy", entropy},
            {"correlation_mutual_information_proxy", mi},
            {"channel_capacity", .5 * std::log2(1 + signal / (noise_power + 1e-10))},
            {"information_density_proxy", entropy / std::max(size_t(1), a.size())},
            {"total_information_proxy", entropy + mi}};
}
Metrics RecursiveWeight::mathematical_summary() const {
    auto m = get_stability_metrics().as_map();
    double bits = 32, mdlr = 0, ref_elements = 0, lognorm = 0;
    for (auto &r : recursive_refs) {
        double elems = r.transformation_matrix.data.size();
        bits += log_elements(size_t(elems)) * std::abs(r.contribution_weight);
        mdlr += log_elements(size_t(elems));
        ref_elements += elems;
        double n = norm(r.transformation_matrix.data);
        if (n > 0)
            lognorm += std::log(n);
    }
    double gamma = estimate_contraction_factor();
    m["mean_frobenius_contraction_proxy"] = gamma;
    m["sum_frobenius_contraction_bound"] = contraction_bound();
    m["capacity_amplification_proxy"] = std::exp2(bits);
    m["universal_approximation_parameter_heuristic"] =
        (config.max_recursion_depth >= 3 && recursive_refs.size() >= 2 &&
         phase.frequencies.size() >= 1 && ref_elements >= dimension() * 2);
    double K = dimension() * 32.;
    double krw = 32 + phase.frequencies.size() * 32 + ref_elements * 32 +
                 (dimension() > 1 ? log_elements(dimension()) : 1);
    m["kolmogorov_reduction_proxy"] = K / (krw * (K > 1 ? std::log(K) : 1));
    m["minimum_description_length_proxy"] =
        (base_codebook_index ? std::log2(base_codebook_index + 1.) : 1) + mdlr +
        (phase.frequencies.empty() ? 1 : std::log2(phase.frequencies.size() * 3.)) +
        .5 * std::log2(recursive_refs.size() + 2.);
    size_t n = 1 + 2 * dimension() + phase.harmonic_amplitudes.data.size() +
               phase.frequencies.size() + phase.phase_offsets.size();
    for (auto &r : recursive_refs)
        n += r.transformation_matrix.data.size() + 7;
    m["mdl_score_bits"] = std::max(double(n) * 32, dimension() * 32.);
    m["attractor_dimension_proxy"] =
        recursive_refs.empty() ? 0
        : gamma <= 0           ? double(dimension())
        : gamma == 1 ? std::numeric_limits<double>::quiet_NaN()
                     : std::max(0., std::min(double(dimension()), lognorm / std::log(gamma)));
    auto info = information_theoretic_bounds();
    m.insert(info.begin(), info.end());
    return m;
}
Metrics RecursiveWeight::optimization_potential() const {
    double phase_e = phase.base_phase.size(), h = phase.harmonic_amplitudes.data.size(), r = 0;
    for (auto &ref : recursive_refs)
        r += ref.transformation_matrix.data.size();
    double ops = phase_e * 4 + h * 3 + r * 2, speedup = 1 + std::min((phase_e + h) / 16., 1.) * 7,
           total = phase_e + h + r, warp = total / (std::ceil(total / 32) * 32),
           shared = (phase_e + h) * 4;
    double se = shared <= 49152 ? shared / 49152 : 49152 / shared,
           div = recursive_refs.empty() ? 0 : .2;
    return {{"vectorizable_operations", ops},
            {"parallel_potential", 1},
            {"simd_speedup_estimate", speedup},
            {"memory_efficiency_proxy", .5},
            {"overall_acceleration_proxy", ops * speedup},
            {"thread_divergence_proxy", div},
            {"memory_coalescing_proxy", 1},
            {"warp_utilization_proxy", warp},
            {"shared_memory_efficiency_proxy", se},
            {"gpu_suitability_proxy", (1 + warp + se) / 3 * (1 - div)}};
}
RecursiveWeight RecursiveWeight::mutate(const MutationParameters &p) const {
    validate();
    require(p.strength >= 0 && std::isfinite(p.strength), "invalid mutation strength");
    require(p.type <= MutationParameters::Type::Comprehensive, "invalid mutation type");
    RecursiveWeight w = *this;
    std::mt19937 rng(p.seed);
    bool all = p.type == MutationParameters::Type::Comprehensive;
    if (all || p.type == MutationParameters::Type::Phase) {
        noise(w.phase.base_phase, rng, p.strength);
        noise(w.phase.harmonic_amplitudes.data, rng, p.strength * p.amplitude_multiplier);
        noise(w.phase.frequencies, rng, p.strength * p.frequency_multiplier);
        noise(w.phase.phase_offsets, rng, p.strength);
        for (float &x : w.phase.harmonic_amplitudes.data)
            x = std::clamp(x, -10.f, 10.f);
        for (float &x : w.phase.frequencies)
            x = std::clamp(x, .01f, 100.f);
        for (float &x : w.phase.phase_offsets)
            x = float(std::fmod(x + p.phase_shift, 2 * pi));
    }
    if (all || p.type == MutationParameters::Type::Reference) {
        std::normal_distribution<double> dist(0, 1);
        require(p.weight_scaling >= 0, "negative weight mutation scale");
        for (auto &r : w.recursive_refs) {
            r.contribution_weight = std::clamp(
                r.contribution_weight + dist(rng) * p.strength * p.weight_scaling, -10., 10.);
            noise(r.transformation_matrix.data, rng, p.matrix_perturbation);
            r.transformation_matrix = stabilize_matrix(r.transformation_matrix);
        }
    }
    if (all || p.type == MutationParameters::Type::Pattern) {
        noise(w.error_preservation, rng, p.strength * .1);
        for (float &x : w.error_preservation)
            x = std::clamp(x, -1.f, 1.f);
    }
    if (!w.verify_post_mutation_stability())
        w.stabilize();
    w.validate();
    return w;
}
bool RecursiveWeight::verify_post_mutation_stability() const {
    try {
        validate();
        return recursive_refs.empty() || spectral_radius(compute_jacobian_matrix()) < 1;
    } catch (const ValidationError &) {
        return false;
    }
}
void RecursiveWeight::stabilize() {
    for (auto &r : recursive_refs) {
        if (std::abs(r.contribution_weight) > 1)
            r.contribution_weight *= .5;
        r.transformation_matrix = stabilize_matrix(r.transformation_matrix);
    }
    for (float &x : error_preservation)
        x = std::clamp(x, -1.f, 1.f);
    if (!verify_post_mutation_stability())
        throw ValidationError(
            "source stabilization did not produce a stable weight; mutation not committed");
}
std::pair<RecursiveWeight, RecursiveWeight>
RecursiveWeight::crossover(const RecursiveWeight &other, double rate, uint32_t seed) const {
    compatible(*this, other);
    require(rate >= 0 && rate <= 1, "crossover rate outside [0,1]");
    RecursiveWeight a = *this, b = other;
    std::mt19937 rng(seed);
    std::uniform_real_distribution<double> u(0, 1);
    if (u(rng) < rate)
        std::swap(a.phase.harmonic_amplitudes, b.phase.harmonic_amplitudes);
    if (u(rng) < rate)
        std::swap(a.phase.frequencies, b.phase.frequencies);
    for (size_t i = 0; i < std::min(a.recursive_refs.size(), b.recursive_refs.size()); i++) {
        if (u(rng) < rate)
            std::swap(a.recursive_refs[i].contribution_weight,
                      b.recursive_refs[i].contribution_weight);
        if (u(rng) < rate)
            std::swap(a.recursive_refs[i].transformation_matrix,
                      b.recursive_refs[i].transformation_matrix);
    }
    return {a, b};
}
double RecursiveWeight::compute_fitness(const FitnessFunction &target) const {
    auto m = get_stability_metrics();
    double b = (1 / (1 + m.spectral_radius) + 1 / (1 + std::abs(m.lyapunov_coefficient)) +
                std::min(1., m.information_capacity / 1000) +
                std::min(1., m.compression_efficiency / 10)) /
               4;
    return target ? .7 * b + .3 * target(*this) : b;
}
std::vector<RecursiveWeight> evolve_population(const std::vector<RecursiveWeight> &weights,
                                               const EvolutionParameters &p,
                                               const FitnessFunction &fit) {
    require(bool(fit), "evolution requires a fitness function");
    require(p.elite_count > 0 && p.elite_count <= weights.size() && p.tournament_size > 0,
            "invalid population selection configuration");
    require(p.crossover_rate >= 0 && p.crossover_rate <= 1 && p.mutation_rate >= 0 &&
                p.mutation_rate <= 1,
            "invalid evolution probability");
    std::vector<std::pair<double, size_t>> scores;
    for (size_t i = 0; i < weights.size(); i++) {
        double f = fit(weights[i]);
        require(std::isfinite(f), "fitness must be finite");
        scores.emplace_back(f, i);
    }
    std::stable_sort(scores.begin(), scores.end(),
                     [](auto a, auto b) { return a.first > b.first; });
    std::vector<RecursiveWeight> out;
    for (size_t i = 0; i < p.elite_count; i++)
        out.push_back(weights[scores[i].second]);
    std::mt19937 rng(p.seed);
    std::uniform_real_distribution<double> u(0, 1);
    auto select = [&]() {
        std::vector<size_t> indices(scores.size());
        std::iota(indices.begin(), indices.end(), 0);
        std::shuffle(indices.begin(), indices.end(), rng);
        size_t best = indices[0];
        for (size_t i = 1; i < std::min(size_t(p.tournament_size), indices.size()); i++)
            if (scores[indices[i]].first > scores[best].first)
                best = indices[i];
        return weights[scores[best].second];
    };
    while (out.size() < weights.size()) {
        auto a = select(), b = select();
        if (u(rng) < p.crossover_rate)
            a = a.crossover(b, .5, rng()).first;
        if (u(rng) < p.mutation_rate) {
            MutationParameters mp;
            mp.seed = rng();
            a = a.mutate(mp);
        }
        out.push_back(std::move(a));
    }
    return out;
}
EvolutionResult evolve(const RecursiveWeight &seed, const EvolutionParameters &p,
                       const FitnessFunction &fit, const GradientFunction &gradient) {
    require(p.generations > 0, "evolution needs at least one generation");
    require(bool(fit), "evolution requires fitness");
    require(!p.adaptive_mutation,
            "adaptive mutation distribution is not specified in supplied source");
    EvolutionResult out{seed, {}};
    std::mt19937 rng(p.seed);
    std::uniform_real_distribution<double> u(0, 1);
    auto score = [&](const RecursiveWeight &w) {
        double v = fit(w);
        require(std::isfinite(v), "fitness must be finite");
        return v;
    };
    double best = score(seed);
    if (p.algorithm == EvolutionParameters::Operator::GradientDescent) {
        require(bool(gradient),
                "gradient_descent requires actual gradients; random source gradients are not used");
        RecursiveWeight velocity = seed;
        auto zero = [](Vector &v) { std::fill(v.begin(), v.end(), 0); };
        zero(velocity.phase.base_phase);
        for (auto &r : velocity.recursive_refs)
            r.contribution_weight = 0;
        for (uint32_t i = 0; i < p.generations; i++) {
            auto g = gradient(out.weight);
            g.validate();
            compatible(out.weight, g);
            require(g.recursive_refs.size() == out.weight.recursive_refs.size(),
                    "gradient reference shape mismatch");
            for (size_t j = 0; j < out.weight.dimension(); j++) {
                velocity.phase.base_phase[j] =
                    float(p.momentum * velocity.phase.base_phase[j] + g.phase.base_phase[j]);
                out.weight.phase.base_phase[j] -=
                    float(p.learning_rate * velocity.phase.base_phase[j]);
            }
            for (size_t j = 0; j < out.weight.recursive_refs.size(); j++) {
                velocity.recursive_refs[j].contribution_weight =
                    p.momentum * velocity.recursive_refs[j].contribution_weight +
                    g.recursive_refs[j].contribution_weight;
                out.weight.recursive_refs[j].contribution_weight =
                    std::clamp(out.weight.recursive_refs[j].contribution_weight -
                                   p.learning_rate * velocity.recursive_refs[j].contribution_weight,
                               -1., 1.);
            }
            out.weight.validate();
            out.fitness_history.push_back(score(out.weight));
        }
        return out;
    }
    if (p.algorithm == EvolutionParameters::Operator::Genetic) {
        require(p.population_size >= 2 && p.elite_count <= p.population_size,
                "invalid population size");
        std::vector<RecursiveWeight> pop{seed};
        while (pop.size() < p.population_size) {
            MutationParameters mp;
            mp.seed = rng();
            mp.strength = .01 + u(rng) * .49;
            pop.push_back(seed.mutate(mp));
        }
        for (uint32_t i = 0; i < p.generations; i++) {
            auto pp = p;
            pp.seed = rng();
            pop = evolve_population(pop, pp, fit);
            for (auto &w : pop) {
                double f = score(w);
                if (f > best) {
                    best = f;
                    out.weight = w;
                }
            }
            out.fitness_history.push_back(best);
        }
        return out;
    }
    require(p.algorithm == EvolutionParameters::Operator::SimulatedAnnealing,
            "unknown evolution operator");
    require(p.decay_rate > 0 && p.decay_rate <= 1, "invalid annealing decay");
    auto current = seed;
    double current_fit = best, temperature = 1;
    for (uint32_t i = 0; i < p.generations; i++) {
        MutationParameters mp;
        mp.strength = temperature * .1;
        mp.seed = rng();
        auto candidate = current.mutate(mp);
        double f = score(candidate);
        if (f >= current_fit || u(rng) < std::exp((f - current_fit) / temperature)) {
            current = candidate;
            current_fit = f;
            if (f > best) {
                out.weight = current;
                best = f;
            }
        }
        out.fitness_history.push_back(best);
        if (p.temperature_schedule == EvolutionParameters::Schedule::Exponential)
            temperature = std::max(1e-12, temperature * p.decay_rate);
        else if (p.temperature_schedule == EvolutionParameters::Schedule::Linear)
            temperature = std::max(.01, temperature - .01);
    }
    return out;
}
void enforce_temporal_coherence(std::vector<RecursiveWeight> &ws, double lambda, double threshold) {
    require(lambda >= 0 && lambda <= 1 && threshold >= 0, "invalid coherence settings");
    for (size_t i = 1; i < ws.size(); i++) {
        auto &a = ws[i - 1];
        auto &b = ws[i];
        compatible(a, b);
        require(a.recursive_refs.size() == b.recursive_refs.size(),
                "coherence requires matching reference topology");
        auto blend = [&](const Vector &x, Vector &y) {
            require(x.size() == y.size(), "coherence shape mismatch");
            double length = 0;
            for (size_t j = 0; j < x.size(); j++)
                length += std::pow(y[j] - x[j], 2);
            double s = std::sqrt(length);
            double factor = s > threshold && s > 0 ? threshold / s : 1;
            for (size_t j = 0; j < x.size(); j++)
                y[j] = float(x[j] + (1 - lambda) * factor * (y[j] - x[j]));
        };
        blend(a.phase.base_phase, b.phase.base_phase);
        blend(a.phase.harmonic_amplitudes.data, b.phase.harmonic_amplitudes.data);
        blend(a.phase.frequencies, b.phase.frequencies);
        blend(a.phase.phase_offsets, b.phase.phase_offsets);
        for (size_t j = 0; j < a.recursive_refs.size(); j++) {
            blend(a.recursive_refs[j].transformation_matrix.data,
                  b.recursive_refs[j].transformation_matrix.data);
            double diff =
                b.recursive_refs[j].contribution_weight - a.recursive_refs[j].contribution_weight;
            b.recursive_refs[j].contribution_weight =
                a.recursive_refs[j].contribution_weight +
                (1 - lambda) * std::clamp(diff, -threshold, threshold);
        }
        b.validate();
    }
}
EigenrecursiveResult
compute_cognitive_eigenstate(Vector state, const std::function<Vector(const Vector &)> &transform,
                             double epsilon, uint32_t max_iterations,
                             const std::function<Metrics(const Vector &, const Vector &)> &metric) {
    require(bool(transform) && epsilon > 0 && max_iterations > 0,
            "invalid eigenrecursive operator or limits");
    EigenrecursiveResult r;
    for (uint32_t i = 0; i < max_iterations; i++) {
        auto next = transform(state);
        rw::validate(next, "cognitive next state", state.size());
        Vector diff = next;
        for (size_t j = 0; j < diff.size(); j++)
            diff[j] -= state[j];
        auto m = metric ? metric(state, next) : Metrics{};
        double distance = norm(diff);
        m["distance"] = distance;
        m["iteration"] = i;
        r.trace.push_back(m);
        state = std::move(next);
        r.iterations = i + 1;
        if (distance < epsilon) {
            r.converged = true;
            break;
        }
    }
    r.fixed_point = std::move(state);
    return r;
}
} // namespace rw
