#include "rw/c_api.h"
#include "rw/runtime.hpp"
#include <algorithm>
struct rw_system {
    rw::RecursiveWeightSystem value;
};
namespace {
thread_local std::string error;
void require(bool ok) {
    if (!ok)
        throw rw::ValidationError("null argument or invalid buffer length");
}
template <class F> int guard(F f) {
    try {
        error.clear();
        f();
        return 0;
    } catch (const std::exception &e) {
        error = e.what();
        return -1;
    } catch (...) {
        error = "unknown native error";
        return -1;
    }
}
} // namespace
extern "C" {
rw_system *rw_create(void) {
    rw_system *p = nullptr;
    guard([&] { p = new rw_system; });
    return p;
}
void rw_destroy(rw_system *p) {
    delete p;
}
const char *rw_last_error(void) {
    return error.c_str();
}
int rw_load(rw_system *p, const char *path) {
    return guard([&] {
        require(p && path);
        p->value.load(path);
    });
}
int rw_save(const rw_system *p, const char *path) {
    return guard([&] {
        require(p && path);
        p->value.save(path);
    });
}
int rw_set_codebook(rw_system *p, const float *v, size_t rows, size_t cols) {
    return guard([&] {
        require(p && v && rows && cols && rows <= SIZE_MAX / cols);
        p->value.set_codebook(rw::Matrix(rows, cols, rw::Vector(v, v + rows * cols)));
    });
}
int rw_add_weight_file(rw_system *p, const char *key, const char *path) {
    return guard([&] {
        require(p && key && path);
        p->value.register_weight(key, rw::RecursiveWeightSerializer::deserialize_weight(path));
    });
}
int rw_remove_weight(rw_system *p, const char *key) {
    return guard([&] {
        require(p && key);
        if (!p->value.remove_weight(key))
            throw rw::ValidationError("unknown weight");
    });
}
int rw_weight_dimension(const rw_system *p, const char *key, size_t *d) {
    return guard([&] {
        require(p && key && d);
        *d = p->value.get_weight(key).dimension();
    });
}
int rw_evaluate(rw_system *p, const char *key, uint32_t depth, double time, int python, float *out,
                size_t n) {
    return guard([&] {
        require(p && key && out && (python == 0 || python == 1));
        require(n == p->value.get_weight(key).dimension());
        rw::EvaluationOptions o;
        o.depth = depth;
        o.time = time;
        o.semantics = python ? rw::Semantics::Python : rw::Semantics::Equation;
        auto v = p->value.reconstruct(key, o);
        require(v.size() == n);
        std::copy(v.begin(), v.end(), out);
    });
}
int rw_mutate(rw_system *p, const char *key, uint32_t type, double strength, uint32_t seed) {
    return guard([&] {
        require(p && key && type <= 3);
        rw::MutationParameters m;
        m.type = rw::MutationParameters::Type(type);
        m.strength = strength;
        m.seed = seed;
        p->value.mutate_weight(key, m);
    });
}
}
