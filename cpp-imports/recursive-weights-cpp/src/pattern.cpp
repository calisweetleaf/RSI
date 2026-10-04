#include "rw/runtime.hpp"
#include <cmath>
#include <limits>
namespace rw {
uint32_t PatternLibrary::register_pattern(Pattern p) {
    if (!std::isfinite(p.scale_factor) || !std::isfinite(p.rotation_factor))
        throw ValidationError("invalid pattern factors");
    std::unique_lock<std::shared_mutex> l(mutex_);
    if (next_ == UINT32_MAX)
        throw ValidationError("pattern IDs exhausted");
    auto id = next_++;
    patterns_[id] = std::move(p);
    return id;
}
Pattern PatternLibrary::get(uint32_t id) const {
    std::shared_lock<std::shared_mutex> l(mutex_);
    auto i = patterns_.find(id);
    if (i == patterns_.end())
        throw ValidationError("unknown pattern ID");
    return i->second;
}
void PatternLibrary::update(uint32_t id, Pattern p) {
    if (!std::isfinite(p.scale_factor) || !std::isfinite(p.rotation_factor))
        throw ValidationError("invalid pattern factors");
    std::unique_lock<std::shared_mutex> l(mutex_);
    if (!patterns_.count(id))
        throw ValidationError("unknown pattern ID");
    patterns_[id] = std::move(p);
}
bool PatternLibrary::remove(uint32_t id) {
    std::unique_lock<std::shared_mutex> l(mutex_);
    return patterns_.erase(id);
}
std::map<uint32_t, Pattern> PatternLibrary::snapshot() const {
    std::shared_lock<std::shared_mutex> l(mutex_);
    return patterns_;
}
Vector PatternLibrary::evaluate(uint32_t id, const Vector &context, uint32_t seed,
                                const Custom &custom) const {
    auto p = get(id);
    validate(context, "pattern context");
    if (p.type == PatternType::Custom) {
        if (!custom)
            throw Unsupported("custom pattern requires a registered evaluator");
        auto out = custom(p, context, seed);
        validate(out, "custom pattern result", context.size());
        return out;
    }
    Vector out(context.size());
    std::mt19937 rng(seed);
    std::normal_distribution<double> normal(0, 1);
    for (size_t i = 0; i < out.size(); i++) {
        double x = context[i], s = p.scale_factor, v = 0;
        switch (p.type) {
        case PatternType::Constant:
            v = s;
            break;
        case PatternType::Linear:
            v = x * s;
            break;
        case PatternType::Sinusoidal:
            v = std::sin(x * s + p.rotation_factor);
            break;
        case PatternType::Exponential:
            v = std::exp(x * s);
            break;
        case PatternType::Polynomial:
            v = x * x * s;
            break;
        case PatternType::Logistic:
            v = 1 / (1 + std::exp(-x * s));
            break;
        case PatternType::Piecewise:
            v = x > 0 ? x * s : x * .1 * s;
            break;
        case PatternType::Stochastic:
            v = x + normal(rng) * s;
            break;
        case PatternType::Fractal:
            for (int octave = 0; octave < 3; octave++) {
                double k = std::pow(2, octave);
                v += std::sin(x * k * s) / k;
            }
            break;
        default:
            throw Unsupported("undefined pattern type");
        }
        out[i] = float(v);
    }
    validate(out, "pattern result", context.size(), std::numeric_limits<double>::infinity());
    return out;
}
} // namespace rw
