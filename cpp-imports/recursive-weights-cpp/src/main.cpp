#include "rw/runtime.hpp"
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
using namespace rw;
namespace {
void metrics(const Metrics &m) {
    std::cout << '{';
    bool comma = false;
    for (auto &[k, v] : m) {
        if (comma)
            std::cout << ',';
        comma = true;
        std::cout << '"' << k << "\":";
        if (std::isfinite(v))
            std::cout << std::setprecision(12) << v;
        else
            std::cout << "null";
    }
    std::cout << "}\n";
}
void vector(const Vector &v) {
    std::cout << '[';
    for (size_t i = 0; i < v.size(); i++) {
        if (i)
            std::cout << ',';
        std::cout << std::setprecision(9) << v[i];
    }
    std::cout << "]\n";
}
uint32_t depth(const char *s) {
    size_t p = 0;
    auto n = std::stoul(s, &p);
    if (p != std::string(s).size() || n > 100)
        throw ValidationError("invalid depth");
    return uint32_t(n);
}
double time_value(const char *s) {
    size_t p = 0;
    double n = std::stod(s, &p);
    if (p != std::string(s).size() || !std::isfinite(n))
        throw ValidationError("invalid time");
    return n;
}
Matrix read_csv(const std::string &path) {
    std::ifstream f(path);
    if (!f)
        throw Error("cannot open codebook CSV");
    std::string line;
    Vector values;
    size_t rows = 0, cols = 0;
    while (std::getline(f, line)) {
        if (line.empty())
            continue;
        std::stringstream ss(line);
        std::string cell;
        size_t n = 0;
        while (std::getline(ss, cell, ',')) {
            size_t consumed = 0;
            float x = std::stof(cell, &consumed);
            while (consumed < cell.size() &&
                   std::isspace(static_cast<unsigned char>(cell[consumed])))
                consumed++;
            if (consumed != cell.size() || !std::isfinite(x))
                throw ValidationError("invalid codebook CSV cell");
            values.push_back(x);
            n++;
        }
        if (!rows)
            cols = n;
        if (n != cols)
            throw ValidationError("ragged codebook CSV");
        rows++;
    }
    if (!rows || !cols)
        throw ValidationError("empty codebook CSV");
    return Matrix(rows, cols, std::move(values));
}
void demo(const std::string &path) {
    Config c;
    c.max_recursion_depth = 16;
    RecursiveWeightSystem s(c);
    s.set_codebook(Matrix(2, 3, Vector{1, 2, 3, -1, .5, 2}));
    auto a = RecursiveWeight::neutral(3, 0, {0, 0, 0, 0, 0});
    a.config = c;
    a.phase.base_phase = {.1f, 0, -.1f};
    a.phase.harmonic_amplitudes = Matrix(1, 3, Vector{.2f, .1f, .3f});
    a.phase.frequencies = {.5f};
    a.phase.phase_offsets = {.2f};
    a.delta.base_delta = {.01f, .02f, .03f};
    a.delta.depth_scaling = .8;
    a.recursive_refs.push_back({{1, 0, 0, 0, 0}, .2, Matrix::identity(3), 1});
    auto b = RecursiveWeight::neutral(3, 1, {1, 0, 0, 0, 0});
    b.config = c;
    b.recursive_refs.push_back({{-1, 0, 0, 0, 0}, .1, Matrix::identity(3), 0});
    s.register_weight("a", a);
    s.register_weight("b", b);
    s.save(path);
    std::cout << "Created deterministic example archive: " << path << '\n';
}
} // namespace
int main(int argc, char **argv) {
    try {
        if (argc < 2) {
            std::cerr
                << "Usage: rw pack CODEBOOK.csv WEIGHT_DIRECTORY ARCHIVE | demo ARCHIVE | evaluate "
                   "ARCHIVE KEY DEPTH TIME [python] | inspect ARCHIVE | inspect-weight FILE | "
                   "convert-weight INPUT OUTPUT | inspect-legacy FILE\n";
            return 2;
        }
        std::string cmd = argv[1];
        if (cmd == "pack" && argc == 5) {
            RecursiveWeightSystem s;
            s.set_codebook(read_csv(argv[2]));
            s.load_weights_directory(argv[3]);
            auto result = s.validate_system();
            if (!result.valid)
                throw ValidationError(result.errors.front());
            s.save(argv[4]);
            return 0;
        }
        if (cmd == "demo" && argc == 3) {
            demo(argv[2]);
            return 0;
        }
        if (cmd == "evaluate" && (argc == 6 || argc == 7)) {
            RecursiveWeightSystem s;
            s.load(argv[2]);
            EvaluationOptions o;
            o.depth = depth(argv[4]);
            o.time = time_value(argv[5]);
            o.track_history = false;
            if (argc == 7) {
                if (std::string(argv[6]) != "python")
                    throw ValidationError("unknown semantics");
                o.semantics = Semantics::Python;
                o.strict_references = false;
            }
            vector(s.reconstruct(argv[3], o));
            return 0;
        }
        if (cmd == "inspect" && argc == 3) {
            RecursiveWeightSystem s;
            s.load(argv[2]);
            auto v = s.validate_system();
            Metrics m{{"weights", double(s.size())},
                      {"structurally_valid", v.valid ? 1. : 0.},
                      {"errors", double(v.errors.size())},
                      {"warnings", double(v.warnings.size())}};
            metrics(m);
            for (auto &e : v.errors)
                std::cerr << e << '\n';
            return v.valid ? 0 : 1;
        }
        if (cmd == "inspect-weight" && argc == 3) {
            metrics(RecursiveWeightSerializer::deserialize_weight(argv[2]).mathematical_summary());
            return 0;
        }
        if (cmd == "convert-weight" && argc == 4) {
            auto w = RecursiveWeightSerializer::deserialize_weight(argv[2]);
            RecursiveWeightSerializer::serialize_weight(w, argv[3]);
            return 0;
        }
        if (cmd == "inspect-legacy" && argc == 3) {
            auto h = read_legacy_header(argv[2]);
            metrics({{"weight_id", double(h.weight_id)},
                     {"recursion_depth", double(h.recursion_depth)},
                     {"self_reference_strength", h.self_reference_strength},
                     {"contains_numerical_payload", 0}});
            return 0;
        }
        throw ValidationError("unknown command or incorrect argument count");
    } catch (const std::exception &e) {
        std::cerr << "rw: " << e.what() << '\n';
        return 1;
    }
}
