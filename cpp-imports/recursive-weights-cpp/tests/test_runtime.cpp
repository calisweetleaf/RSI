#include "rw/runtime.hpp"
#include <cmath>
#include <filesystem>
#include <fstream>
#include <future>
#include <iostream>
#include <unistd.h>
using namespace rw;
static int checks = 0;
void check(bool c, const char *m) {
    checks++;
    if (!c)
        throw Error(m);
}
void near(double a, double b, double tol = 1e-5) {
    checks++;
    if (!std::isfinite(a) || std::abs(a - b) > tol)
        throw Error("numeric mismatch: " + std::to_string(a) + " != " + std::to_string(b));
}
void near(const Vector &a, const Vector &b, double tol = 1e-5) {
    check(a.size() == b.size(), "vector shape");
    for (size_t i = 0; i < a.size(); i++)
        near(a[i], b[i], tol);
}
template <class F> void rejects(F f) {
    bool threw = false;
    try {
        f();
    } catch (const std::exception &) {
        threw = true;
    }
    check(threw, "expected rejection");
}
int main() {
    auto dir = std::filesystem::temp_directory_path() / ("rw-tests-" + std::to_string(getpid()));
    std::filesystem::create_directories(dir);
    try {
        Config c;
        c.max_recursion_depth = 100;
        c.cache_size = 8;
        RecursiveWeightSystem s(c);
        s.set_codebook(Matrix(2, 2, Vector{2, 4, 10, 20}));
        auto a = RecursiveWeight::neutral(2, 0),
             b = RecursiveWeight::neutral(2, 1, {1, 0, 0, 0, 0});
        a.config = c;
        b.config = c;
        a.recursive_refs.push_back({{1, 0, 0, 0, 0}, .25, Matrix::identity(2), 0});
        b.recursive_refs.push_back({{-1, 0, 0, 0, 0}, .5, Matrix::identity(2), 0});
        s.register_weight("a", a);
        s.register_weight("b", b);
        EvaluationOptions o;
        o.track_history = false;
        near(s.reconstruct("a", o), {2, 4});
        o.depth = 1;
        near(s.reconstruct("a", o), {4.5, 9});
        o.depth = 2;
        near(s.reconstruct("a", o), {4.75, 9.5});
        check(s.detect_recursion_loops("a"), "cycle not detected");
        o.depth = 20;
        near(s.reconstruct("a", o), {float(4.5 / .875), float(9 / .875)}, 2e-5);
        auto system_stability = s.analyze_system_stability();
        near(system_stability.at("zero_delay_global_spectral_radius"), std::sqrt(.125), 1e-6);
        // Same ID, different depths and time must never share an incorrect cached value.
        b.phase.harmonic_amplitudes = Matrix(1, 2, Vector{1, 2});
        b.phase.frequencies = {1};
        b.phase.phase_offsets = {0};
        s.register_weight("b", b);
        o.depth = 1;
        o.time = 0;
        near(s.reconstruct("a", o), {4.5, 9});
        o.time = 1.5707963267948966;
        near(s.reconstruct("a", o), {4.75, 9.5});
        a.recursive_refs[0].temporal_offset = 1;
        s.register_weight("a", a);
        o.time = 1;
        near(s.reconstruct("a", o), {4.5, 9});
        s.set_codebook(Matrix(2, 2, Vector{4, 8, 20, 40}));
        near(s.reconstruct("a", o), {9, 18});
        // Independent spatial addressing, self recurrence, zero depth and error preservation.
        RecursiveWeightSystem self(c);
        self.set_codebook(Matrix(1, 2, Vector{1, 2}));
        auto w = RecursiveWeight::neutral(2);
        w.config = c;
        w.recursive_refs.push_back({{}, .5, Matrix::identity(2), 0});
        self.register_weight("self", w);
        o.time = 0;
        o.depth = 3;
        near(self.reconstruct("self", o), {1.875, 3.75});
        o.semantics = Semantics::Python;
        near(self.reconstruct("self", o), {1, 2});
        o.semantics = Semantics::Equation;
        w.error_preservation = {.2f, -.1f};
        self.register_weight("self", w);
        o.depth = 0;
        near(self.reconstruct("self", o), {1.2f, 1.9f});
        o.semantics = Semantics::Python;
        double cap = (1 - std::sqrt(.5)) * std::sqrt(.05) / (1 + std::sqrt(.5));
        near(self.reconstruct("self", o), {float(cap), float(cap)});
        o.semantics = Semantics::Equation;
        // Delta, harmonics, scalar versus vector amplitudes.
        a = RecursiveWeight::neutral(2);
        a.delta.base_delta = {1, 2};
        a.delta.adaptive_factor = {2, 3};
        a.delta.depth_scaling = .5;
        near(a.compute_delta_value(2), {.5, 1.5});
        a.phase.harmonic_amplitudes = Matrix(1, 2, Vector{2, 3});
        a.phase.frequencies = {1};
        a.phase.phase_offsets = {0};
        near(a.compute_phase_value(1.5707963267948966), {2, 3});
        a.phase.harmonic_amplitudes = Matrix(1, 1, Vector{2});
        near(a.compute_phase_value(1.5707963267948966), {2, 2});
        // LAPACK nonsymmetric complex eigenspectrum, SVD cap, rank.
        Matrix rotation(2, 2, Vector{0, -.5, .5, 0});
        near(spectral_radius(rotation), .5);
        near(spectral_norm(rotation), .5);
        auto st = stabilize_matrix(Matrix(2, 2, Vector{3, 0, 0, .2}));
        near(st.data, {.95f, 0, 0, .2f});
        check(matrix_rank(Matrix(2, 2, Vector{1, 2, 2, 4})) == 1, "matrix rank");
        near(DynamicalSystemsAnalyzer::fixed_point(.5, {1, 2}), {2, 4});
        near(DynamicalSystemsAnalyzer::uniform_convergence_bound(.5, 1, 3), .25);
        check(DynamicalSystemsAnalyzer::convergence_steps(.01, .5, 1) == 8, "convergence depth");
        check(DynamicalSystemsAnalyzer::convergence_steps(.01, 0, 1) == 1, "zero contraction");
        near(DynamicalSystemsAnalyzer::error_accumulation_bound(1, {2, 3}, .5), 5);
        near(DynamicalSystemsAnalyzer::compression_efficiency(10, 32, 1, 32, 1, 32, 1, 32),
             320. / 96);
        near(DynamicalSystemsAnalyzer::self_similarity({Matrix::identity(2)}), 1);
        // Complete state round-trip; legacy format interop and loss rejection.
        a.scale_factor = 2;
        a.flags = Evolutive;
        a.config = c;
        a.tensor_position = {-2, 3, 0, 0, 0};
        a.error_preservation = {.005f, -.004f};
        auto bytes = RecursiveWeightSerializer::encode(a);
        auto round = RecursiveWeightSerializer::decode(bytes.data(), bytes.size());
        near(round.scale_factor, 2);
        near(round.delta.base_delta, a.delta.base_delta);
        near(round.delta.depth_scaling, .5);
        check(round.tensor_position == a.tensor_position, "position round trip");
        check(round.flags == a.flags, "flags round trip");
        check(round.config.max_recursion_depth == 100, "config round trip");
        rejects([&] { RecursiveWeightSerializer::encode(a, true); });
        auto neutral = RecursiveWeight::neutral(2);
        auto old = RecursiveWeightSerializer::encode(neutral, true);
        near(RecursiveWeightSerializer::decode(old.data(), old.size()).error_preservation, {0, 0});
        for (size_t n : {size_t(0), size_t(4), bytes.size() - 1})
            rejects([&] { RecursiveWeightSerializer::decode(bytes.data(), n); });
        auto corrupted = bytes;
        corrupted[20] ^= 1;
        rejects([&] { RecursiveWeightSerializer::decode(corrupted.data(), corrupted.size()); });
        auto archive = (dir / "system.rwgs").string();
        s.save(archive);
        RecursiveWeightSystem loaded;
        loaded.load(archive);
        o.depth = 2;
        o.time = 3;
        near(loaded.reconstruct("a", o), s.reconstruct("a", o));
        check(loaded.validate_system().valid, "loaded registry invalid");
        // Mutation deterministic within the native RNG and no aliasing of the source.
        MutationParameters mp;
        mp.type = MutationParameters::Type::Phase;
        mp.seed = 123;
        auto mutated = a.mutate(mp);
        near(mutated.phase.base_phase, a.mutate(mp).phase.base_phase, 0);
        check(mutated.phase.base_phase != a.phase.base_phase, "mutation ineffective");
        auto original = s.get_weight("a");
        s.mutate_weight("a", mp);
        check(s.mutation_history("a").size() == 1, "mutation history");
        check(s.get_weight("a").phase.base_phase != original.phase.base_phase, "registry mutation");
        s.save(archive);
        loaded.load(archive);
        check(loaded.mutation_history("a").size() == 1, "persisted mutation history");
        // Parallel requests and explicit missing/ambiguous reference failures.
        auto batch = s.batch_compute({"a", "b"}, o);
        near(batch.at("a"), s.reconstruct("a", o));
        std::vector<std::future<Vector>> jobs;
        for (int i = 0; i < 8; i++)
            jobs.push_back(std::async(std::launch::async, [&] { return s.reconstruct("a", o); }));
        for (auto &f : jobs)
            near(f.get(), batch.at("a"));
        rejects([&] { s.batch_compute({"unknown"}, o); });
        s.remove_weight("b");
        rejects([&] { s.reconstruct("a", o); });
        o.strict_references = false;
        check(s.reconstruct("a", o).size() == 2, "missing reference permissive mode");
        s.register_weight("b", b);
        s.register_weight("duplicate", b);
        rejects([&] { s.reconstruct("a", o); });
        s.remove_weight("duplicate");
        o.strict_references = true;
        // Cache capacity is bounded across many time values.
        for (int i = 0; i < 40; i++) {
            o.time = i / 10.;
            s.reconstruct("a", o);
        }
        auto cs = s.cache_stats();
        check(cs.l1_entries + cs.l2_entries <= 8, "cache capacity leak");
        check(cs.hits > 0, "cache not exercised");
        // Pattern equations, callbacks, and numerical validation.
        PatternLibrary patterns;
        for (int type = 0; type < 9; type++) {
            Pattern p;
            p.type = PatternType(type);
            p.scale_factor = .5;
            auto id = patterns.register_pattern(p);
            auto v = patterns.evaluate(id, {-.2f, .4f});
            check(v.size() == 2, "pattern output shape");
            if (type == 1)
                near(v, {-.1f, .2f});
        }
        Pattern custom;
        custom.type = PatternType::Custom;
        auto id = patterns.register_pattern(custom);
        rejects([&] { patterns.evaluate(id, {1}); });
        near(patterns.evaluate(id, {1}, 42, [](auto &, auto &x, auto) { return x; }), {1});
        // Genetic selection must actually use fitness, preserving the best individual.
        EvolutionParameters ep;
        ep.generations = 3;
        ep.population_size = 5;
        auto seed = RecursiveWeight::neutral(2);
        auto fit = [](const RecursiveWeight &w) {
            double n = 0;
            for (float x : w.phase.base_phase)
                n += (x - .5) * (x - .5);
            return -n;
        };
        auto ev = evolve(seed, ep, fit);
        check(fit(ev.weight) >= fit(seed), "genetic selection regressed best");
        check(ev.fitness_history.size() == 3, "evolution history");
        ep.algorithm = EvolutionParameters::Operator::GradientDescent;
        rejects([&] { evolve(seed, ep, fit); });
        ep.learning_rate = .1;
        ep.momentum = 0;
        auto gd = evolve(seed, ep, fit, [](const RecursiveWeight &w) {
            auto g = RecursiveWeight::neutral(w.dimension());
            for (size_t i = 0; i < w.dimension(); i++)
                g.phase.base_phase[i] = 2 * (w.phase.base_phase[i] - .5f);
            return g;
        });
        check(fit(gd.weight) > fit(seed), "gradient descent failed");
        ep.algorithm = EvolutionParameters::Operator::SimulatedAnnealing;
        check(fit(evolve(seed, ep, fit).weight) >= fit(seed), "annealing lost best");
        // Layer Jacobian against central differences, plus full model reload.
        RecursiveWeightLayer layer(2, 3, 3, {}, 7);
        EvaluationOptions lo;
        lo.depth = 0;
        lo.track_history = false;
        Matrix x(1, 2, Vector{.2f, -.3f});
        auto jac = layer.compute_layer_jacobian(x.data, lo);
        for (size_t j = 0; j < 2; j++) {
            auto plus = x, minus = x;
            plus(0, j) += .001f;
            minus(0, j) -= .001f;
            auto yp = layer.forward(plus, lo).output, ym = layer.forward(minus, lo).output;
            for (size_t i = 0; i < 3; i++)
                near(jac(i, j), (yp(0, i) - ym(0, i)) / .002, 5e-4);
        }
        auto lp = (dir / "layer.rwly").string();
        layer.save(lp);
        auto y = layer.forward(x, lo).output.data;
        RecursiveWeightLayer restored(1, 1, 1);
        restored.load(lp);
        near(restored.forward(x, lo).output.data, y, 1e-6);
        // Eigenrecursive state must advance every iteration (missing in source pseudocode).
        auto eigen = compute_cognitive_eigenstate(
            {0}, [](const Vector &v) { return Vector{1 + .5f * v[0]}; }, 1e-6, 100);
        check(eigen.converged, "eigenstate convergence");
        near(eigen.fixed_point, {2}, 2e-6);
        check(eigen.iterations > 1, "state was not advanced");
        rejects([&] {
            auto bad = seed;
            bad.phase.frequencies = {1};
            bad.validate();
        });
        rejects([&] {
            auto bad = c;
            bad.stability_check_interval = 0;
            bad.validate();
        });
        rejects([&] {
            o.depth = 101;
            s.reconstruct("a", o);
        });
        std::cout << "PASS " << checks
                  << " assertions; recurrence, temporal/cache, spectral/SVD, mutation/evolution, "
                     "binary, concurrency, layer Jacobian, eigenstate\n";
        std::filesystem::remove_all(dir);
        return 0;
    } catch (const std::exception &e) {
        std::cerr << "FAIL after " << checks << " checks: " << e.what() << "; artifacts " << dir
                  << '\n';
        return 1;
    }
}
