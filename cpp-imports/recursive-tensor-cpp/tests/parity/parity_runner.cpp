// parity_runner -- executes a manifest of operations on .rta inputs and writes
// .rta outputs, so an independent implementation (tests/parity/parity.py,
// which drives the Python reference) can compare results.
//
// Manifest: one op per line, whitespace separated, '#' comments.
//   contract   A B axesA axesB OUT        (axes as comma lists)
//   expand     A dims OUT
//   project    A BASIS axes OUT          (BASIS is a rank-2 .rta)
//   transform  A M axis OUT
//   eigvals    A k OUT                   (values -> rank-1 f64)
//   svals      A k OUT
//   conv       A KERNEL axis OUT         (KERNEL rank-1 .rta)
//   entropy    A OUT
//   density    A resolution threshold OUT_EDGES OUT_HIST
//   compat     A B OUT
//   hyper      A curvature OUT
//   fractal    A c_real max_iter OUT     (constant c)
//   tucker     A OUT                     (reconstruction)
//   mps        A OUT                     (from_mps(to_mps(A)))
//   roundtrip  A OUT                     (load -> save)
#include "rta/rta.hpp"

#include <fstream>
#include <iostream>
#include <sstream>

using namespace rta;
using namespace rta::io;

static Axes parse_axes(const std::string& s) {
    Axes a;
    if (s == "-") return a;
    std::stringstream ss(s);
    std::string t;
    while (std::getline(ss, t, ',')) a.push_back(static_cast<std::size_t>(std::stoull(t)));
    return a;
}
static Shape parse_shape(const std::string& s) { return parse_axes(s); }

static void save_scalars(const std::vector<double>& v, const std::string& path) {
    save(RecursiveTensor<double>::from_dense({v.size()}, v), path);
}

template <class T>
static Matrix<work_t<T>> as_matrix(const RecursiveTensor<T>& m) {
    if (m.rank() != 2) throw ShapeError("matrix input must be rank 2");
    Matrix<work_t<T>> M(m.shape()[0], m.shape()[1]);
    for (std::size_t i = 0; i < M.rows; ++i)
        for (std::size_t j = 0; j < M.cols; ++j) M(i, j) = work_t<T>(m.get({i, j}));
    return M;
}

template <class T>
static void run(const std::vector<std::string>& w, const std::string& dir, RecursiveTensor<T> A) {
    auto P = [&](const std::string& n) { return dir + "/" + n; };
    const std::string& op = w[0];
    if (op == "contract") {
        auto B = load<T>(P(w[2]), true);
        save(A.contract(B, parse_axes(w[3]), parse_axes(w[4])), P(w[5]));
    } else if (op == "expand") {
        save(A.expand(parse_shape(w[2])), P(w[3]));
    } else if (op == "project") {
        auto B = load<T>(P(w[2]), true);
        Matrix<T> M(B.shape()[0], B.shape()[1]);
        for (std::size_t i = 0; i < M.rows; ++i)
            for (std::size_t j = 0; j < M.cols; ++j) M(i, j) = B.get({i, j});
        save(A.project(M, parse_axes(w[3])), P(w[4]));
    } else if (op == "transform") {
        auto B = load<T>(P(w[2]), true);
        Matrix<T> M(B.shape()[0], B.shape()[1]);
        for (std::size_t i = 0; i < M.rows; ++i)
            for (std::size_t j = 0; j < M.cols; ++j) M(i, j) = B.get({i, j});
        save(A.transform(M, parse_axes(w[3])), P(w[4]));
    } else if (op == "eigvals" || op == "svals") {
        auto r = A.compute_eigenstates(static_cast<std::size_t>(std::stoul(w[2])));
        save_scalars(r.values, P(w[3]));
    } else if (op == "conv") {
        auto K = load<T>(P(w[2]), true).to_dense();
        std::vector<T> k(K.volume());
        for (Extent i = 0; i < K.volume(); ++i) k[i] = K.get_linear(i);
        save(A.apply_temporal_convolution(k, std::stoll(w[3])), P(w[4]));
    } else if (op == "entropy") {
        save_scalars({A.compute_entropy()}, P(w[2]));
    } else if (op == "density") {
        auto h = A.compute_density_function(std::stoi(w[2]), std::stod(w[3]));
        save_scalars(h.edges, P(w[4]));
        save_scalars(h.density, P(w[5]));
    } else if (op == "compat") {
        auto B = load<T>(P(w[2]), true);
        save_scalars({A.compatibility(B)}, P(w[3]));
    } else if (op == "hyper") {
        save(A.to_hyperbolic_space(std::stod(w[2])), P(w[3]));
    } else if (op == "fractal") {
        const T c = scalar_cast<T>(std::stod(w[2]));
        save(A.fractal_iteration([c](const Index&, T) { return c; }, std::stoi(w[3])), P(w[4]));
    } else if (op == "tucker") {
        save(A.tucker_decomposition().reconstruct(), P(w[2]));
    } else if (op == "mps") {
        save(RecursiveTensor<T>::from_mps(A.to_mps()), P(w[2]));
    } else if (op == "roundtrip") {
        save(A, P(w[2]));
    } else {
        throw Error("unknown op " + op);
    }
}

int main(int argc, char** argv) {
    if (argc != 2) { std::cerr << "usage: parity_runner <case_dir>  (reads <case_dir>/manifest.txt)\n"; return 2; }
    const std::string dir = argv[1];
    std::ifstream mf(dir + "/manifest.txt");
    if (!mf) { std::cerr << "no manifest\n"; return 2; }
    std::string line;
    int ok = 0, bad = 0;
    while (std::getline(mf, line)) {
        if (line.empty() || line[0] == '#') continue;
        std::stringstream ss(line);
        std::vector<std::string> w;
        for (std::string t; ss >> t;) w.push_back(t);
        try {
            std::visit([&](auto&& A) { run(w, dir, std::move(A)); }, load_any(dir + "/" + w[1]));
            ++ok;
        } catch (const std::exception& e) {
            std::cerr << "ERROR [" << line << "]: " << e.what() << "\n";
            ++bad;
        }
    }
    std::cout << ok << " ops ok, " << bad << " errors\n";
    return bad ? 1 : 0;
}
