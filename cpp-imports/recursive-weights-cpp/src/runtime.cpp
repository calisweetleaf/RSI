#include "rw/runtime.hpp"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <future>
#include <limits>
#include <set>
#include <thread>
#include <tuple>
namespace rw {
namespace {
using Clock = std::chrono::steady_clock;
using Key = std::tuple<std::string, uint32_t, uint64_t, uint32_t, uint64_t, bool>;
uint64_t time_bits(double t) {
    if (t == 0)
        t = 0;
    uint64_t bits;
    std::memcpy(&bits, &t, 8);
    return bits;
}
void finite_result(const Vector &v) {
    validate(v, "effective weight", {}, std::numeric_limits<double>::infinity());
}
struct CacheEntry {
    Vector value;
    uint64_t accesses = 1, tick = 0;
    Clock::time_point created = Clock::now();
};
class TieredCache {
    std::mutex mutex_;
    std::map<Key, CacheEntry> l1_, l2_;
    size_t c1_, c2_;
    uint64_t tick_ = 0;
    CacheStats stats_;
    void trim() {
        while (l1_.size() > c1_) {
            auto v = std::min_element(l1_.begin(), l1_.end(), [](auto &a, auto &b) {
                return a.second.tick < b.second.tick;
            });
            if (c2_)
                l2_[v->first] = std::move(v->second);
            l1_.erase(v);
            stats_.evictions++;
        }
        while (l2_.size() > c2_) {
            auto v = std::min_element(l2_.begin(), l2_.end(), [](auto &a, auto &b) {
                return std::tie(a.second.accesses, a.second.tick) <
                       std::tie(b.second.accesses, b.second.tick);
            });
            l2_.erase(v);
            stats_.evictions++;
        }
    }

  public:
    explicit TieredCache(size_t size)
        : c1_(size ? std::max(size_t(1), size / 4) : 0), c2_(size - c1_) {}
    std::optional<Vector> get(const Key &k) {
        std::lock_guard<std::mutex> l(mutex_);
        auto fetch = [&](auto &cache) -> std::optional<CacheEntry> {
            auto i = cache.find(k);
            if (i == cache.end())
                return {};
            if (Clock::now() - i->second.created > std::chrono::seconds(60)) {
                cache.erase(i);
                return {};
            }
            i->second.tick = ++tick_;
            i->second.accesses++;
            return i->second;
        };
        if (auto e = fetch(l1_)) {
            stats_.hits++;
            return e->value;
        }
        if (auto e = fetch(l2_)) {
            l2_.erase(k);
            l1_[k] = *e;
            trim();
            stats_.hits++;
            return e->value;
        }
        stats_.misses++;
        return {};
    }
    void put(const Key &k, const Vector &v) {
        std::lock_guard<std::mutex> l(mutex_);
        if (!c1_)
            return;
        l2_.erase(k);
        l1_[k] = {v, 1, ++tick_, Clock::now()};
        trim();
    }
    void clear() {
        std::lock_guard<std::mutex> l(mutex_);
        l1_.clear();
        l2_.clear();
    }
    void reconfigure(size_t size) {
        std::lock_guard<std::mutex> l(mutex_);
        c1_ = size ? std::max(size_t(1), size / 4) : 0;
        c2_ = size - c1_;
        l1_.clear();
        l2_.clear();
    }
    CacheStats stats() {
        std::lock_guard<std::mutex> l(mutex_);
        auto s = stats_;
        s.l1_entries = l1_.size();
        s.l2_entries = l2_.size();
        return s;
    }
};
Vector python_bounds(Vector v, const RecursiveWeight &w) {
    for (float &x : v)
        x = std::clamp(x, -1e4f, 1e4f);
    double err = norm(w.error_preservation), g = w.estimate_contraction_factor();
    if (err > .01 && g < 1) {
        float cap = float((1 - g) * err / (1 + g));
        for (float &x : v)
            x = std::clamp(x, -cap, cap);
    } // final Python class leaves _stability_metrics.spectral_radius at zero due to method override
    return v;
}
} // namespace
struct RecursiveWeightSystem::Impl {
    Config config;
    mutable std::shared_mutex registry_mutex;
    Matrix codebook;
    std::map<std::string, RecursiveWeight> weights;
    std::map<Position, std::vector<std::string>> positions;
    std::map<std::string, std::vector<MutationParameters>> mutations;
    mutable std::mutex state_mutex;
    std::map<std::string, RuntimeSnapshot> states;
    TieredCache cache;
    uint64_t revision = 0;
    std::atomic<uint64_t> calls{0}, nodes{0};
    std::atomic<int64_t> elapsed_ns{0};
    explicit Impl(Config c) : config(c), cache(c.cache_size) {
        config.validate();
    }
    void changed() {
        revision++;
        cache.clear();
        std::lock_guard<std::mutex> lock(state_mutex);
        states.clear();
    }
    void rebuild_positions() {
        positions.clear();
        for (auto &[key, w] : weights)
            positions[w.tensor_position].push_back(key);
    }
    std::optional<std::string> resolve(const RecursiveWeight &w, const RecursiveReference &r,
                                       bool strict) const {
        auto p = add_position(w.tensor_position, r.relative_position);
        auto i = positions.find(p);
        if (i == positions.end()) {
            if (strict)
                throw ValidationError("missing reference at " + position_key(p));
            return {};
        }
        if (i->second.size() != 1)
            throw ValidationError("ambiguous reference at " + position_key(p));
        return i->second.front();
    }
    Vector evaluate(const std::string &key, EvaluationOptions options,
                    std::map<Key, Vector> &memo) {
        auto it = weights.find(key);
        if (it == weights.end())
            throw ValidationError("weight not found: " + key);
        const auto &w = it->second;
        if (options.depth > w.config.max_recursion_depth ||
            options.depth > config.max_recursion_depth)
            throw ValidationError("recursion depth exceeds configured limit");
        if (!std::isfinite(options.time) || std::abs(options.time) > 1e6)
            throw ValidationError("invalid evaluation time");
        if (options.semantics != Semantics::Equation && options.semantics != Semantics::Python)
            throw ValidationError("unknown semantics");
        bool py = options.semantics == Semantics::Python;
        if (py) {
            double g = 0;
            for (auto &r : w.recursive_refs)
                g = std::max(g,
                             std::abs(r.contribution_weight) * norm(r.transformation_matrix.data));
            g /= std::max(size_t(1), w.recursive_refs.size());
            if (g >= 1 ||
                (g > 0 &&
                 options.depth >=
                     std::ceil(std::log(w.config.convergence_threshold * (1 - g)) / std::log(g))))
                options.depth = 0;
        }
        if (w.base_codebook_index >= codebook.rows || codebook.cols != w.dimension())
            throw ValidationError("codebook missing or incompatible for " + key);
        Key ck{key,
               options.depth,
               time_bits(options.time),
               uint32_t(options.semantics),
               revision,
               options.strict_references};
        // Stateful Python guards must run on every real evaluation. Equation memoization is pure.
        bool memoize = !py || !options.track_history;
        if (memoize) {
            auto mi = memo.find(ck);
            if (mi != memo.end())
                return mi->second;
            if (options.use_cache)
                if (auto v = cache.get(ck)) {
                    memo[ck] = *v;
                    return *v;
                }
        }
        Vector base(w.dimension());
        for (size_t j = 0; j < base.size(); j++)
            base[j] = float(codebook(w.base_codebook_index, j) * w.scale_factor);
        auto delta = w.compute_delta_value(options.depth, options.semantics),
             phase = w.compute_phase_value(options.time, options.semantics);
        Vector refs(w.dimension());
        if (options.depth)
            for (auto &r : w.recursive_refs) {
                auto target = resolve(w, r, options.strict_references);
                if (!target)
                    continue;
                if (py && *target == key)
                    continue;
                auto sub = options;
                sub.depth--;
                sub.time -= r.temporal_offset;
                auto value = evaluate(*target, sub, memo);
                auto transformed = matvec(r.transformation_matrix, value);
                for (size_t j = 0; j < refs.size(); j++)
                    refs[j] += float(r.contribution_weight * transformed[j]);
            }
        Vector output;
        add_components(output, base, delta, refs, phase, w.error_preservation,
                       config.enable_simd && w.config.enable_simd);
        if (py)
            output = python_bounds(std::move(output), w);
        finite_result(output);
        nodes++;
        if (options.track_history) {
            std::lock_guard<std::mutex> lock(state_mutex);
            auto &s = states[key];
            s.computations++;
            if (s.ema.empty())
                s.ema = output;
            else
                for (size_t j = 0; j < output.size(); j++)
                    s.ema[j] = float(w.config.ema_momentum * s.ema[j] +
                                     (1 - w.config.ema_momentum) * output[j]);
            s.effective_history.push_back(s.ema);
            if (s.effective_history.size() > 64)
                s.effective_history.pop_front();
            if (s.computations % w.config.stability_check_interval == 0) {
                double growth = s.last.empty() ? 1 : norm(output) / (norm(s.last) + 1e-8),
                       bound = 0;
                for (auto &r : w.recursive_refs)
                    bound = std::max(bound, std::abs(r.contribution_weight) *
                                                spectral_norm(r.transformation_matrix));
                bool stable = growth <= w.config.max_growth_ratio &&
                              bound <= w.config.spectral_radius_threshold && bound <= 1;
                s.stability_history.push_back({{"stable", stable ? 1. : 0.},
                                               {"growth_ratio", growth},
                                               {"spectral_bound", bound},
                                               {"contraction_proxy", bound}});
                if (s.stability_history.size() > 256)
                    s.stability_history.pop_front();
                s.state = stable ? Stability::Stable : Stability::Unstable;
                if (!stable && py) {
                    output = python_bounds(std::move(output), w);
                    for (float &x : output)
                        x *= float(w.config.damping_factor);
                }
                s.last = output;
            }
        }
        if (memoize) {
            memo[ck] = output;
            if (options.use_cache)
                cache.put(ck, output);
        }
        return output;
    }
};
RecursiveWeightSystem::RecursiveWeightSystem(Config c) : impl_(std::make_unique<Impl>(c)) {}
RecursiveWeightSystem::~RecursiveWeightSystem() = default;
void RecursiveWeightSystem::set_codebook(Matrix c) {
    validate(c, "codebook");
    if (!c.rows || !c.cols)
        throw ValidationError("codebook must be nonempty");
    std::unique_lock<std::shared_mutex> l(impl_->registry_mutex);
    for (auto &[k, w] : impl_->weights)
        if (w.dimension() != c.cols || w.base_codebook_index >= c.rows)
            throw ValidationError("new codebook incompatible with " + k);
    impl_->codebook = std::move(c);
    impl_->changed();
}
Matrix RecursiveWeightSystem::codebook() const {
    std::shared_lock<std::shared_mutex> l(impl_->registry_mutex);
    return impl_->codebook;
}
void RecursiveWeightSystem::register_weight(std::string key, RecursiveWeight w) {
    if (key.empty())
        throw ValidationError("empty weight key");
    w.validate();
    std::unique_lock<std::shared_mutex> l(impl_->registry_mutex);
    if (impl_->weights.size() >= 10000 && !impl_->weights.count(key))
        throw ValidationError("registry capacity exceeded");
    if (impl_->codebook.rows &&
        (w.base_codebook_index >= impl_->codebook.rows || w.dimension() != impl_->codebook.cols))
        throw ValidationError("weight incompatible with codebook");
    impl_->weights[std::move(key)] = std::move(w);
    impl_->rebuild_positions();
    impl_->changed();
}
RecursiveWeight RecursiveWeightSystem::get_weight(const std::string &key) const {
    std::shared_lock<std::shared_mutex> l(impl_->registry_mutex);
    auto i = impl_->weights.find(key);
    if (i == impl_->weights.end())
        throw ValidationError("unknown weight: " + key);
    return i->second;
}
bool RecursiveWeightSystem::has_weight(const std::string &key) const {
    std::shared_lock<std::shared_mutex> l(impl_->registry_mutex);
    return impl_->weights.count(key);
}
bool RecursiveWeightSystem::remove_weight(const std::string &key) {
    std::unique_lock<std::shared_mutex> l(impl_->registry_mutex);
    bool removed = impl_->weights.erase(key);
    if (removed) {
        impl_->mutations.erase(key);
        impl_->rebuild_positions();
        impl_->changed();
    }
    return removed;
}
std::vector<std::string> RecursiveWeightSystem::keys() const {
    std::shared_lock<std::shared_mutex> l(impl_->registry_mutex);
    std::vector<std::string> k;
    for (auto &x : impl_->weights)
        k.push_back(x.first);
    return k;
}
size_t RecursiveWeightSystem::size() const {
    std::shared_lock<std::shared_mutex> l(impl_->registry_mutex);
    return impl_->weights.size();
}
Vector RecursiveWeightSystem::reconstruct(const std::string &key, EvaluationOptions options) {
    auto start = Clock::now();
    std::shared_lock<std::shared_mutex> l(impl_->registry_mutex);
    std::map<Key, Vector> memo;
    auto v = impl_->evaluate(key, options, memo);
    impl_->calls++;
    impl_->elapsed_ns +=
        std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now() - start).count();
    return v;
}
std::map<std::string, Vector>
RecursiveWeightSystem::batch_compute(const std::vector<std::string> &keys,
                                     EvaluationOptions options) {
    std::shared_lock<std::shared_mutex> l(impl_->registry_mutex);
    for (auto &k : keys)
        if (!impl_->weights.count(k))
            throw ValidationError("unknown batch weight: " + k);
    std::vector<Vector> values(keys.size());
    std::atomic<size_t> next{0};
    std::exception_ptr failure;
    std::mutex error_mutex;
    auto worker = [&]() {
        try {
            std::map<Key, Vector> memo;
            for (;;) {
                size_t i = next.fetch_add(1);
                if (i >= keys.size())
                    break;
                values[i] = impl_->evaluate(keys[i], options, memo);
            }
        } catch (...) {
            std::lock_guard<std::mutex> e(error_mutex);
            if (!failure)
                failure = std::current_exception();
        }
    };
    auto start = Clock::now();
    size_t threads = std::min(keys.size(), size_t(impl_->config.thread_pool_size));
    if (options.semantics == Semantics::Python && options.track_history)
        threads = std::min(size_t(1), threads);
    std::vector<std::thread> pool;
    try {
        for (size_t i = 1; i < threads; i++)
            pool.emplace_back(worker);
    } catch (...) {
        for (auto &t : pool)
            t.join();
        throw;
    }
    worker();
    for (auto &t : pool)
        t.join();
    if (failure)
        std::rethrow_exception(failure);
    std::map<std::string, Vector> out;
    for (size_t i = 0; i < keys.size(); i++)
        out[keys[i]] = std::move(values[i]);
    impl_->calls += keys.size();
    impl_->elapsed_ns +=
        std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now() - start).count();
    return out;
}
void RecursiveWeightSystem::mutate_weight(const std::string &key, const MutationParameters &p) {
    std::unique_lock<std::shared_mutex> l(impl_->registry_mutex);
    auto i = impl_->weights.find(key);
    if (i == impl_->weights.end())
        throw ValidationError("unknown mutation target");
    auto w = i->second.mutate(p);
    i->second = std::move(w);
    impl_->mutations[key].push_back(p);
    impl_->changed();
}
void RecursiveWeightSystem::evolve_weight(const std::string &key, const EvolutionParameters &p,
                                          const FitnessFunction &f, const GradientFunction &g) {
    RecursiveWeight seed;
    uint64_t revision;
    {
        std::shared_lock<std::shared_mutex> l(impl_->registry_mutex);
        auto i = impl_->weights.find(key);
        if (i == impl_->weights.end())
            throw ValidationError("unknown evolution target");
        seed = i->second;
        revision = impl_->revision;
    }
    auto result = evolve(seed, p, f, g);
    std::unique_lock<std::shared_mutex> l(impl_->registry_mutex);
    if (revision != impl_->revision)
        throw Error("system changed while evolution was running; result not committed");
    impl_->weights.at(key) = std::move(result.weight);
    impl_->changed();
}
std::vector<MutationParameters>
RecursiveWeightSystem::mutation_history(const std::string &key) const {
    std::shared_lock<std::shared_mutex> l(impl_->registry_mutex);
    auto i = impl_->mutations.find(key);
    return i == impl_->mutations.end() ? std::vector<MutationParameters>{} : i->second;
}
void RecursiveWeightSystem::clear_all_caches() {
    impl_->cache.clear();
}
CacheStats RecursiveWeightSystem::cache_stats() const {
    return impl_->cache.stats();
}
RuntimeSnapshot RecursiveWeightSystem::runtime_snapshot(const std::string &key) const {
    std::lock_guard<std::mutex> l(impl_->state_mutex);
    auto i = impl_->states.find(key);
    return i == impl_->states.end() ? RuntimeSnapshot{} : i->second;
}
ValidationResult RecursiveWeightSystem::validate_system() const {
    std::shared_lock<std::shared_mutex> l(impl_->registry_mutex);
    ValidationResult result;
    for (auto &[k, w] : impl_->weights) {
        try {
            w.validate();
            if (w.base_codebook_index >= impl_->codebook.rows ||
                w.dimension() != impl_->codebook.cols)
                throw ValidationError("codebook mismatch");
            for (auto &r : w.recursive_refs)
                impl_->resolve(w, r, true);
            if (w.contraction_bound() >= 1)
                result.warnings.push_back(k + ": sum-norm contraction bound is not < 1");
        } catch (const std::exception &e) {
            result.errors.push_back(k + ": " + e.what());
        }
    }
    result.valid = result.errors.empty();
    return result;
}
Metrics RecursiveWeightSystem::analyze_system_stability(size_t limit) const {
    std::shared_lock<std::shared_mutex> l(impl_->registry_mutex);
    if (impl_->weights.empty())
        return {{"total_weights", 0}};
    size_t d = impl_->codebook.cols;
    if (!d || impl_->weights.size() > limit / d)
        throw ValidationError("global Jacobian exceeds caller limit or lacks codebook");
    std::map<std::string, size_t> offsets;
    size_t off = 0;
    for (auto &[k, w] : impl_->weights) {
        offsets[k] = off;
        off += w.dimension();
    }
    Matrix j(off, off);
    double maxbound = 0;
    bool temporal = false;
    for (auto &[k, w] : impl_->weights) {
        double bound = 0;
        for (auto &r : w.recursive_refs) {
            auto dest = impl_->resolve(w, r, true);
            size_t row = offsets[k], col = offsets.at(*dest);
            for (size_t a = 0; a < d; a++)
                for (size_t b = 0; b < d; b++)
                    j(row + a, col + b) +=
                        float(r.contribution_weight * r.transformation_matrix(a, b));
            bound += std::abs(r.contribution_weight) * norm(r.transformation_matrix.data);
            temporal |= r.temporal_offset != 0;
        }
        maxbound = std::max(maxbound, bound);
    }
    double radius = spectral_radius(j);
    return {{"total_weights", double(impl_->weights.size())},
            {"zero_delay_global_spectral_radius", radius},
            {"maximum_sum_norm_bound", maxbound},
            {"has_temporal_offsets", temporal ? 1. : 0.},
            {"depth_contraction_certified", maxbound < 1 ? 1. : 0.},
            {"zero_delay_stable", !temporal && radius < 1 ? 1. : 0.}};
}
size_t RecursiveWeightSystem::optimize_recursive_references(double target) {
    if (!(target > 0 && target < 1))
        throw ValidationError("target spectral radius must be (0,1)");
    std::unique_lock<std::shared_mutex> l(impl_->registry_mutex);
    size_t count = 0;
    for (auto &[k, w] : impl_->weights) {
        double radius = w.recursive_refs.empty() ? 0 : spectral_radius(w.compute_jacobian_matrix());
        if (radius > target) {
            for (auto &r : w.recursive_refs)
                r.contribution_weight *= target / radius;
            count++;
        }
    }
    if (count)
        impl_->changed();
    return count;
}
bool RecursiveWeightSystem::detect_recursion_loops(const std::string &key, uint32_t depth) const {
    std::shared_lock<std::shared_mutex> l(impl_->registry_mutex);
    if (depth > 100)
        throw ValidationError("loop traversal depth >100");
    std::set<std::string> path;
    std::function<bool(const std::string &, uint32_t)> visit = [&](const std::string &k,
                                                                   uint32_t d) {
        if (!d)
            return false;
        if (path.count(k))
            return true;
        auto it = impl_->weights.find(k);
        if (it == impl_->weights.end())
            throw ValidationError("unknown loop traversal weight");
        path.insert(k);
        for (auto &r : it->second.recursive_refs) {
            auto target = impl_->resolve(it->second, r, true);
            if (visit(*target, d - 1))
                return true;
        }
        path.erase(k);
        return false;
    };
    return visit(key, depth);
}
Metrics RecursiveWeightSystem::performance_summary() const {
    auto c = cache_stats();
    return {{"requests", double(impl_->calls.load())},
            {"computed_nodes", double(impl_->nodes.load())},
            {"elapsed_seconds", impl_->elapsed_ns.load() / 1e9},
            {"cache_hits", double(c.hits)},
            {"cache_misses", double(c.misses)},
            {"cache_hit_rate", c.hits + c.misses ? double(c.hits) / (c.hits + c.misses) : 0},
            {"cache_entries", double(c.l1_entries + c.l2_entries)}};
}
void RecursiveWeightSystem::precompute(const std::vector<std::string> &k, EvaluationOptions o) {
    batch_compute(k, o);
}
std::map<double, Vector> RecursiveWeightSystem::multiscale(const std::string &k,
                                                           const std::vector<double> &scales,
                                                           uint32_t d) {
    std::map<double, Vector> r;
    for (double s : scales) {
        EvaluationOptions o;
        o.depth = d;
        o.time = s;
        r[s] = reconstruct(k, o);
    }
    return r;
}
std::map<uint32_t, Metrics> RecursiveWeightSystem::analyze_depth(const std::string &k, uint32_t max,
                                                                 double t) {
    std::map<uint32_t, Metrics> r;
    Vector prev;
    for (uint32_t i = 0; i <= max; i++) {
        EvaluationOptions o;
        o.depth = i;
        o.time = t;
        auto v = reconstruct(k, o);
        double mean = 0;
        for (float x : v)
            mean += x;
        mean /= v.size();
        double var = 0;
        for (float x : v)
            var += (x - mean) * (x - mean);
        Metrics m{{"output_norm", norm(v)},
                  {"output_mean", mean},
                  {"output_std", v.size() > 1 ? std::sqrt(var / (v.size() - 1)) : 0}};
        if (!prev.empty()) {
            Vector diff = v;
            for (size_t j = 0; j < v.size(); j++)
                diff[j] -= prev[j];
            m["convergence_error"] = norm(diff);
            m["relative_change"] = norm(diff) / (norm(prev) + 1e-8);
        }
        r[i] = m;
        prev = std::move(v);
    }
    return r;
}
RecursiveWeightSystem &get_registry() {
    static RecursiveWeightSystem s;
    return s;
}
} // namespace rw
#include "codec.hpp"
#include <filesystem>
namespace rw {
std::vector<uint8_t> RecursiveWeightSystem::serialize_system_binary() const {
    std::shared_lock<std::shared_mutex> l(impl_->registry_mutex);
    detail::Writer w;
    w.magic("RWGS");
    w.u16(0x0100);
    detail::write_config(w, impl_->config);
    w.matrix(impl_->codebook);
    w.u32(uint32_t(impl_->weights.size()));
    for (auto &[k, weight] : impl_->weights) {
        w.string(k);
        auto bytes = RecursiveWeightSerializer::encode(weight);
        w.u64(bytes.size());
        w.bytes(bytes.data(), bytes.size());
        auto i = impl_->mutations.find(k);
        w.u32(i == impl_->mutations.end() ? 0 : uint32_t(i->second.size()));
        if (i != impl_->mutations.end())
            for (auto &p : i->second) {
                w.u32(uint32_t(p.type));
                w.u32(p.seed);
                for (double x :
                     {p.strength, p.temperature, p.frequency_multiplier, p.amplitude_multiplier,
                      p.phase_shift, p.weight_scaling, p.matrix_perturbation, p.blend_factor})
                    w.f64(x);
                w.u32(p.target_pattern_id);
            }
    }
    w.checksum();
    return w.data;
}
void RecursiveWeightSystem::deserialize_system_binary(const uint8_t *data, size_t size) {
    detail::verify_checksum(data, size);
    detail::Reader r(data, size - 32);
    r.magic("RWGS");
    if (r.u16() != 0x0100)
        throw FormatError("unsupported system version");
    auto cfg = detail::read_config(r);
    auto cb = r.matrix();
    validate(cb, "archive codebook");
    auto count = r.u32();
    if (count > 10000)
        throw FormatError("too many weights");
    std::map<std::string, RecursiveWeight> weights;
    std::map<std::string, std::vector<MutationParameters>> history;
    for (uint32_t i = 0; i < count; i++) {
        auto k = r.string();
        if (k.empty() || weights.count(k))
            throw FormatError("empty/duplicate archive key");
        uint64_t len = r.u64();
        if (len > r.size - r.pos)
            throw FormatError("weight payload length overflow");
        auto weight = RecursiveWeightSerializer::decode(r.data + r.pos, size_t(len));
        r.pos += size_t(len);
        if (weight.dimension() != cb.cols || weight.base_codebook_index >= cb.rows)
            throw FormatError("archive codebook mismatch");
        weights.emplace(k, std::move(weight));
        auto nh = r.u32();
        if (nh > 1000000)
            throw FormatError("mutation history too large");
        for (uint32_t j = 0; j < nh; j++) {
            MutationParameters p;
            auto type = r.u32();
            if (type > 3)
                throw FormatError("invalid mutation type");
            p.type = MutationParameters::Type(type);
            p.seed = r.u32();
            p.strength = r.f64();
            p.temperature = r.f64();
            p.frequency_multiplier = r.f64();
            p.amplitude_multiplier = r.f64();
            p.phase_shift = r.f64();
            p.weight_scaling = r.f64();
            p.matrix_perturbation = r.f64();
            p.blend_factor = r.f64();
            p.target_pattern_id = r.u32();
            history[k].push_back(p);
        }
    }
    r.end();
    std::unique_lock<std::shared_mutex> l(impl_->registry_mutex);
    impl_->weights = std::move(weights);
    impl_->codebook = std::move(cb);
    impl_->mutations = std::move(history);
    impl_->config = cfg;
    impl_->cache.reconfigure(cfg.cache_size);
    impl_->rebuild_positions();
    impl_->changed();
}
void RecursiveWeightSystem::save(const std::string &path) const {
    detail::atomic_write(path, serialize_system_binary());
}
void RecursiveWeightSystem::load(const std::string &path) {
    detail::MappedFile f(path);
    deserialize_system_binary(f.data(), f.size());
}
void RecursiveWeightSystem::save_weights_directory(const std::string &path) const {
    std::filesystem::create_directories(path);
    std::shared_lock<std::shared_mutex> l(impl_->registry_mutex);
    size_t i = 0;
    for (auto &[k, w] : impl_->weights)
        RecursiveWeightSerializer::serialize_weight(
            w,
            (std::filesystem::path(path) / ("weight_" + std::to_string(i++) + ".rwgt")).string());
}
size_t RecursiveWeightSystem::load_weights_directory(const std::string &path) {
    std::vector<std::filesystem::path> files;
    for (auto &e : std::filesystem::directory_iterator(path))
        if (e.is_regular_file() && e.path().extension() == ".rwgt")
            files.push_back(e.path());
    std::sort(files.begin(), files.end());
    std::map<std::string, RecursiveWeight> loaded;
    for (auto &p : files)
        loaded.emplace(p.stem().string(),
                       RecursiveWeightSerializer::deserialize_weight(p.string()));
    std::unique_lock<std::shared_mutex> l(impl_->registry_mutex);
    auto next = impl_->weights;
    for (auto &[k, w] : loaded) {
        if (impl_->codebook.rows && (w.dimension() != impl_->codebook.cols ||
                                     w.base_codebook_index >= impl_->codebook.rows))
            throw ValidationError("directory weight/codebook mismatch");
        next[k] = w;
    }
    if (next.size() > 10000)
        throw ValidationError("registry capacity exceeded");
    impl_->weights = std::move(next);
    impl_->rebuild_positions();
    impl_->changed();
    return loaded.size();
}
} // namespace rw
