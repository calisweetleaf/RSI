// rta/recursive_tensor.hpp — RecursiveTensor<T>: the RTA compute fabric.
//
// C++ port of recursive_tensor.py v2.1.0 (Morpheus / Somnus Sovereign Systems)
// plus the recursive-reference machinery from the RTA whitepaper (§2.4, §3.2.3)
// which the Python reference never implemented.
//
// A RecursiveTensor is NOT a weight or parameter container. It is a live
// compute object: storage (dense or sparse) + provenance (history, metadata)
// + self-reference (recursive references settled to a fixed point).
//
// Every behavioural difference from the Python reference is recorded in
// docs/PORTING_LEDGER.md with the reason. Nothing diverges silently.
//
// Thread-safety: const operations may run concurrently on one tensor
// (the eigenstate cache is internally locked). Mutation (set, settle,
// add_reference, ...) requires external synchronisation.
#pragma once

#include <algorithm>
#include <cmath>
#include <functional>
#include <map>
#include <memory>
#include <mutex>
#include <optional>
#include <random>
#include <sstream>
#include <string>
#include <tuple>
#include <unordered_map>
#include <utility>
#include <vector>

#include "linalg.hpp"
#include "types.hpp"

namespace rta {

inline constexpr const char* kVersion = "2.1.0-cpp";
inline constexpr double kPi = 3.14159265358979323846;

// ============================================================ enums & records
enum class Storage : std::uint8_t { Dense = 0, Sparse = 1 };

enum class Distribution : std::uint8_t {
    Normal = 0, Uniform = 1, PowerLaw = 2, ComplexGaussian = 3, Orthogonal = 4, Empty = 5, Explicit = 6
};
inline const char* distribution_name(Distribution d) {
    switch (d) {
        case Distribution::Normal: return "normal";
        case Distribution::Uniform: return "uniform";
        case Distribution::PowerLaw: return "power_law";
        case Distribution::ComplexGaussian: return "complex_gaussian";
        case Distribution::Orthogonal: return "orthogonal";
        case Distribution::Empty: return "empty";
        case Distribution::Explicit: return "explicit";
    }
    return "unknown";
}

enum class OpCode : std::uint16_t {
    Create = 0, Contract = 1, Expand = 2, Project = 3, Embed = 4, Transform = 5, Fractal = 6,
    Normalize = 7, ApplyFunction = 8, Add = 9, Multiply = 10, TemporalConvolution = 11,
    Hyperbolic = 12, Reduce = 13, Transpose = 14, Reshape = 15, SettleReferences = 16,
    Convert = 17, Densify = 18, Sparsify = 19, Tucker = 20, Mps = 21
};
inline const char* opcode_name(OpCode c) {
    switch (c) {
        case OpCode::Create: return "create";
        case OpCode::Contract: return "contract";
        case OpCode::Expand: return "expand";
        case OpCode::Project: return "project";
        case OpCode::Embed: return "embed";
        case OpCode::Transform: return "transform";
        case OpCode::Fractal: return "fractal";
        case OpCode::Normalize: return "normalize";
        case OpCode::ApplyFunction: return "apply_function";
        case OpCode::Add: return "add";
        case OpCode::Multiply: return "multiply";
        case OpCode::TemporalConvolution: return "temporal_convolution";
        case OpCode::Hyperbolic: return "hyperbolic";
        case OpCode::Reduce: return "reduce";
        case OpCode::Transpose: return "transpose";
        case OpCode::Reshape: return "reshape";
        case OpCode::SettleReferences: return "settle_references";
        case OpCode::Convert: return "convert";
        case OpCode::Densify: return "densify";
        case OpCode::Sparsify: return "sparsify";
        case OpCode::Tucker: return "tucker";
        case OpCode::Mps: return "mps";
    }
    return "unknown";
}

// One provenance step. `args` is op-specific integer payload (axes, sizes...);
// `peer` is the uuid of the other operand for binary ops (nil otherwise).
struct OpRecord {
    OpCode code = OpCode::Create;
    std::vector<std::int64_t> args;
    Uuid peer{};
    std::string label;
};

struct Metadata {
    double created_at = 0.0;
    double modified_at = 0.0;
    std::uint64_t operations_count = 0;
    std::string description;
    std::map<std::string, std::string> extra;
};

// Whitepaper §3.2.3. Indices stored as row-major linear offsets.
enum class RefType : std::uint8_t { Direct = 0, Transform = 1, Fractal = 2 };
struct RecursiveReference {
    Extent source = 0;
    Extent target = 0;
    RefType type = RefType::Direct;
    std::vector<double> params;          // Direct {w}; Transform {a, b}; Fractal {c_scale, escape}
    std::uint8_t iteration_axis = 0;     // recorded for the format; semantic hook
    std::uint8_t max_iterations = 16;
    double convergence_threshold = 1e-8;
};

enum class NormType { L1, L2, Inf };
enum class ReduceOp { Sum, Mean, Max, Min };

struct Histogram {
    std::vector<double> edges;    // resolution + 1
    std::vector<double> density;  // resolution
};
struct PersistencePair {
    int dimension = 0;
    double birth = 0.0;
    double death = 0.0;  // +inf for essential classes
};
struct SettleReport {
    int sweeps = 0;
    double max_delta = 0.0;
    bool converged = false;
};
struct EigenOptions {
    std::size_t dense_limit = 1024;  // n above this uses subspace iteration
    int max_iter = 1000;
    std::uint64_t seed = 0x5EEDu;
};

template <class T> class RecursiveTensor;

template <class T>
struct EigenResult {
    enum class Method : std::uint8_t { JacobiEigh = 0, SubspaceIteration = 1, JacobiSvd = 2 };
    std::vector<double> values;        // eigenvalues (Hermitian part) or singular values
    std::shared_ptr<const RecursiveTensor<T>> vectors;  // shape [k] + column-axis extents
    Method method = Method::JacobiEigh;
    bool converged = false;
    int refined = 0;                   // vectors touched by inverse-iteration refinement
    bool symmetrized = false;          // operator was replaced by its Hermitian part
};

template <class T>
struct TuckerResult {
    std::shared_ptr<RecursiveTensor<T>> core;
    std::vector<Matrix<T>> factors;  // factors[n] is extent_n x r_n
    RecursiveTensor<T> reconstruct() const;
};

template <class T>
struct ReduceResult {
    std::shared_ptr<RecursiveTensor<T>> values;
    std::vector<Extent> arg;  // arg-max/min along the axis (row-major over the kept axes); empty otherwise
};

namespace detail {

// Row-major split of a linear offset into two groups of axes.
struct Splitter {
    Shape shape;
    std::vector<Extent> coef1, coef2;  // per-axis coefficient (0 if axis not in group)
    Splitter(const Shape& s, const Axes& g1, const Axes& g2) : shape(s), coef1(s.size(), 0), coef2(s.size(), 0) {
        Extent c = 1;
        for (std::size_t i = g1.size(); i-- > 0;) { coef1[g1[i]] = c; c *= s[g1[i]]; }
        c = 1;
        for (std::size_t i = g2.size(); i-- > 0;) { coef2[g2[i]] = c; c *= s[g2[i]]; }
    }
    std::pair<Extent, Extent> operator()(Extent lin) const {
        Extent a = 0, b = 0;
        for (std::size_t ax = shape.size(); ax-- > 0;) {
            const Extent i = lin % shape[ax];
            lin /= shape[ax];
            a += i * coef1[ax];
            b += i * coef2[ax];
        }
        return {a, b};
    }
};

template <class T>
std::vector<T> permute_dense(const std::vector<T>& src, const Shape& shape, const Axes& perm, Shape* out_shape) {
    const std::size_t r = shape.size();
    Shape os(r);
    for (std::size_t i = 0; i < r; ++i) os[i] = shape[perm[i]];
    if (out_shape) *out_shape = os;
    const auto sst = strides_of(shape);
    std::vector<Extent> step(r);
    for (std::size_t i = 0; i < r; ++i) step[i] = sst[perm[i]];
    const Extent vol = volume_of(shape);
    std::vector<T> dst(vol);
    if (vol == 0) return dst;
    std::vector<Extent> ctr(r, 0);
    Extent off = 0;
    for (Extent o = 0; o < vol; ++o) {
        dst[o] = src[off];
        for (std::size_t d = r; d-- > 0;) {
            if (++ctr[d] < os[d]) { off += step[d]; break; }
            off -= step[d] * (os[d] - 1);
            ctr[d] = 0;
        }
    }
    return dst;
}

inline Axes complement(const Axes& axes, std::size_t rank) {
    std::vector<bool> in(rank, false);
    for (auto a : axes) in[a] = true;
    Axes out;
    for (std::size_t i = 0; i < rank; ++i) if (!in[i]) out.push_back(i);
    return out;
}

inline std::string cap_description(std::string s, std::size_t limit = 512) {
    if (s.size() <= limit) return s;
    const std::size_t half = (limit - 5) / 2;
    return s.substr(0, half) + " ... " + s.substr(s.size() - half);
}

template <class T>
struct EigenCacheSlot {
    struct State {
        std::mutex mu;
        std::map<std::string, std::shared_ptr<const EigenResult<T>>> entries;
    };
    std::unique_ptr<State> st = std::make_unique<State>();
    EigenCacheSlot() = default;
    EigenCacheSlot(const EigenCacheSlot&) : st(std::make_unique<State>()) {}
    EigenCacheSlot& operator=(const EigenCacheSlot&) { st = std::make_unique<State>(); return *this; }
    EigenCacheSlot(EigenCacheSlot&& o) : st(std::move(o.st)) { o.st = std::make_unique<State>(); }
    EigenCacheSlot& operator=(EigenCacheSlot&& o) {
        st = std::move(o.st);
        o.st = std::make_unique<State>();
        return *this;
    }
    void clear() {
        std::lock_guard<std::mutex> g(st->mu);
        st->entries.clear();
    }
};

}  // namespace detail

// ============================================================ RecursiveTensor
template <class T>
class RecursiveTensor {
    static_assert(std::is_same_v<T, float> || std::is_same_v<T, double> ||
                      std::is_same_v<T, std::complex<float>> || std::is_same_v<T, std::complex<double>>,
                  "RecursiveTensor supports float, double, complex<float>, complex<double>");

public:
    using value_type = T;
    using real_type = real_t<T>;
    using W = work_t<T>;
    using SparseMap = std::unordered_map<Extent, T>;
    using CFn = std::function<T(const Index&, const T&)>;
    using EmbedFn = std::function<std::vector<std::pair<Index, T>>(const Index&, const T&)>;

    static constexpr double kSparseKeep = 1e-10;  // Python's per-contribution drop threshold

    // ------------------------------------------------------------ construction
    // Python: RecursiveTensor(dimensions=shape_tuple, distribution=..., sparsity=...)
    explicit RecursiveTensor(Shape shape, Distribution dist = Distribution::Normal, double sparsity = 0.1,
                             std::optional<std::uint64_t> seed = std::nullopt)
        : shape_(std::move(shape)), distribution_(dist), sparsity_(sparsity), uuid_(Uuid::generate()) {
        volume_ = volume_of(shape_);
        init_metadata();
        std::mt19937_64 rng(seed ? *seed : (static_cast<std::uint64_t>(std::random_device{}()) << 32) ^ std::random_device{}());
        initialize(rng);
        history_.push_back({OpCode::Create, {static_cast<std::int64_t>(dist)}, {}, distribution_name(dist)});
    }

    // Python: RecursiveTensor(dimensions=int, rank=r) — square tensor.
    static RecursiveTensor square(Extent extent, std::size_t rank, Distribution dist = Distribution::Normal,
                                  double sparsity = 0.1, std::optional<std::uint64_t> seed = std::nullopt) {
        return RecursiveTensor(Shape(rank, extent), dist, sparsity, seed);
    }

    static RecursiveTensor zeros(Shape shape, Storage storage = Storage::Dense) {
        RecursiveTensor t(std::move(shape), Distribution::Empty, 1.0, 0);
        if (storage == Storage::Sparse) { t.dense_.clear(); t.dense_.shrink_to_fit(); t.storage_ = Storage::Sparse; }
        return t;
    }

    // Python: from_dict(ndarray)
    static RecursiveTensor from_dense(Shape shape, std::vector<T> data) {
        RecursiveTensor t(std::move(shape), Distribution::Empty, 1.0, 0);
        if (data.size() != t.volume_)
            throw ShapeError("from_dense: data size " + std::to_string(data.size()) + " != volume " +
                             std::to_string(t.volume_) + " of " + shape_str(t.shape_));
        t.dense_ = std::move(data);
        t.distribution_ = Distribution::Explicit;
        t.sparsity_ = 0.0;
        t.history_.back() = {OpCode::Create, {static_cast<std::int64_t>(Distribution::Explicit)}, {}, "explicit"};
        t.meta_.description = "RecursiveTensor.from_dense(dimensions=" + shape_str(t.shape_) + ")";
        return t;
    }

    // Python: from_dict({index_tuple: value}). Writes exactly the given cells.
    // Duplicate indices: last write wins (dict semantics).
    static RecursiveTensor from_cells(Shape shape, const std::vector<std::pair<Index, T>>& cells,
                                      Storage storage = Storage::Dense) {
        RecursiveTensor t = zeros(std::move(shape), storage);
        std::size_t filled = 0;
        SparseMap seen_guard;
        for (const auto& [idx, v] : cells) {
            const Extent lin = linearize(idx, t.shape_);
            if (storage == Storage::Dense) t.dense_[lin] = v;
            else t.sparse_[lin] = v;
            seen_guard[lin] = v;
        }
        filled = seen_guard.size();
        t.distribution_ = Distribution::Explicit;
        t.history_.back() = {OpCode::Create, {static_cast<std::int64_t>(Distribution::Explicit)}, {}, "explicit"};
        t.sparsity_ = t.volume_ == 0 ? 0.0 : 1.0 - static_cast<double>(filled) / static_cast<double>(t.volume_);
        t.meta_.description = "RecursiveTensor.from_cells(dimensions=" + shape_str(t.shape_) +
                              ", filled=" + std::to_string(filled) + ")";
        return t;
    }

    static RecursiveTensor from_sparse(Shape shape, SparseMap cells) {
        RecursiveTensor t = zeros(std::move(shape), Storage::Sparse);
        for (const auto& kv : cells)
            if (kv.first >= t.volume_) throw IndexError("from_sparse: linear offset out of range");
        t.sparse_ = std::move(cells);
        t.distribution_ = Distribution::Explicit;
        t.sparsity_ = t.volume_ == 0 ? 0.0 : 1.0 - static_cast<double>(t.sparse_.size()) / static_cast<double>(t.volume_);
        return t;
    }

    // Low-level assembly used by the .rta reader. Validates everything.
    struct Parts {
        Shape shape;
        Storage storage = Storage::Dense;
        std::vector<T> dense;
        std::vector<Extent> sparse_offsets;
        std::vector<T> sparse_values;
        Distribution distribution = Distribution::Explicit;
        double sparsity = 0.0;
        Uuid uuid{};
        Metadata meta;
        std::vector<OpRecord> history;
        std::vector<RecursiveReference> references;
    };
    static RecursiveTensor assemble(Parts p) {
        RecursiveTensor t = zeros(p.shape, p.storage);
        if (p.storage == Storage::Dense) {
            if (p.dense.size() != t.volume_) throw FormatError("assemble: dense payload size != volume");
            t.dense_ = std::move(p.dense);
        } else {
            if (p.sparse_offsets.size() != p.sparse_values.size()) throw FormatError("assemble: sparse index/value count mismatch");
            t.sparse_.reserve(p.sparse_offsets.size());
            for (std::size_t i = 0; i < p.sparse_offsets.size(); ++i) {
                if (p.sparse_offsets[i] >= t.volume_) throw FormatError("assemble: sparse offset out of range");
                t.sparse_[p.sparse_offsets[i]] = p.sparse_values[i];
            }
        }
        for (const auto& r : p.references)
            if (r.source >= t.volume_ || r.target >= t.volume_) throw FormatError("assemble: reference offset out of range");
        t.distribution_ = p.distribution;
        t.sparsity_ = p.sparsity;
        t.uuid_ = p.uuid.is_nil() ? Uuid::generate() : p.uuid;
        t.meta_ = std::move(p.meta);
        t.history_ = std::move(p.history);
        t.refs_ = std::move(p.references);
        return t;
    }

    // ------------------------------------------------------------ introspection
    const Shape& shape() const { return shape_; }
    std::size_t rank() const { return shape_.size(); }
    Extent volume() const { return volume_; }
    Storage storage() const { return storage_; }
    bool is_sparse() const { return storage_ == Storage::Sparse; }
    static constexpr DType dtype() { return dtype_of_v<T>; }
    Distribution distribution() const { return distribution_; }
    double sparsity() const { return sparsity_; }  // declared (Python semantics)
    std::size_t stored_count() const { return is_sparse() ? sparse_.size() : dense_.size(); }
    std::size_t nnz() const {
        std::size_t n = 0;
        for_each_stored([&](Extent, const T& v) { if (v != T(0)) ++n; });
        return n;
    }
    double measured_sparsity() const {
        return volume_ == 0 ? 0.0 : 1.0 - static_cast<double>(nnz()) / static_cast<double>(volume_);
    }
    const Uuid& uuid() const { return uuid_; }
    void set_uuid(const Uuid& u) { if (u.is_nil()) throw Error("uuid must not be nil"); uuid_ = u; }
    const Metadata& metadata() const { return meta_; }
    Metadata& metadata() { return meta_; }  // raw access; description cap not enforced here
    void set_description(const std::string& d) { meta_.description = detail::cap_description(d); }
    const std::vector<OpRecord>& history() const { return history_; }
    const std::vector<RecursiveReference>& references() const { return refs_; }
    std::size_t history_limit() const { return history_limit_; }
    void set_history_limit(std::size_t n) { history_limit_ = n; trim_history(); }
    const std::vector<T>& dense_data() const {
        if (is_sparse()) throw Error("dense_data(): tensor is sparse");
        return dense_;
    }
    const SparseMap& sparse_data() const {
        if (!is_sparse()) throw Error("sparse_data(): tensor is dense");
        return sparse_;
    }

    std::string describe() const {  // Python __str__
        std::ostringstream os;
        os << "RecursiveTensor<" << dtype_name(dtype()) << ">(dimensions=" << shape_str(shape_) << ", rank=" << rank();
        if (is_sparse()) {
            const double density = volume_ ? static_cast<double>(sparse_.size()) / static_cast<double>(volume_) : 0.0;
            os << ", format=sparse, nnz=" << sparse_.size() << ", density=" << std::scientific;
            os.precision(2);
            os << density;
        } else {
            os << ", format=dense";
        }
        os << ")";
        return os.str();
    }

    // ------------------------------------------------------------ element access
    T get(const Index& idx) const { return get_linear(linearize(idx, shape_)); }
    T get_linear(Extent lin) const {
        if (lin >= volume_) throw IndexError("linear offset out of range");
        if (is_sparse()) {
            auto it = sparse_.find(lin);
            return it == sparse_.end() ? T(0) : it->second;
        }
        return dense_[lin];
    }
    void set(const Index& idx, const T& v) { set_linear(linearize(idx, shape_), v); }
    void set_linear(Extent lin, const T& v) {
        if (lin >= volume_) throw IndexError("linear offset out of range");
        if (is_sparse()) {
            if (v == T(0)) sparse_.erase(lin); else sparse_[lin] = v;
        } else {
            dense_[lin] = v;
        }
        touch();
    }

    // f(Extent linear_offset, const T& value) over every *stored* cell.
    // Dense: every cell in row-major order. Sparse: stored cells, unordered.
    template <class F> void for_each_stored(F&& f) const {
        if (is_sparse()) { for (const auto& kv : sparse_) f(kv.first, kv.second); }
        else { for (Extent i = 0; i < dense_.size(); ++i) f(i, dense_[i]); }
    }
    // Sorted (canonical) view of sparse cells.
    std::vector<std::pair<Extent, T>> sorted_cells() const {
        std::vector<std::pair<Extent, T>> out;
        if (is_sparse()) {
            out.assign(sparse_.begin(), sparse_.end());
            std::sort(out.begin(), out.end(), [](const auto& a, const auto& b) { return a.first < b.first; });
        } else {
            for (Extent i = 0; i < dense_.size(); ++i) if (dense_[i] != T(0)) out.emplace_back(i, dense_[i]);
        }
        return out;
    }

    std::vector<T> to_dense_array() const {
        if (!is_sparse()) return dense_;
        std::vector<T> out(volume_, T(0));
        for (const auto& kv : sparse_) out[kv.first] = kv.second;
        return out;
    }
    RecursiveTensor to_dense() const {
        RecursiveTensor r = derive(shape_, Storage::Dense, OpCode::Densify, {}, "Dense view of ");
        r.dense_ = to_dense_array();
        r.refs_ = refs_;
        return r;
    }
    RecursiveTensor to_sparse(double threshold = 0.0) const {
        RecursiveTensor r = derive(shape_, Storage::Sparse, OpCode::Sparsify, {}, "Sparse view of ");
        for_each_stored([&](Extent lin, const T& v) { if (mag(v) > threshold) r.sparse_[lin] = v; });
        r.refs_ = refs_;
        return r;
    }
    template <class U> RecursiveTensor<U> astype() const {
        typename RecursiveTensor<U>::Parts p;
        p.shape = shape_;
        p.storage = storage_;
        if (is_sparse()) {
            for (const auto& [k, v] : sorted_cells()) { p.sparse_offsets.push_back(k); p.sparse_values.push_back(scalar_cast<U>(v)); }
        } else {
            p.dense.reserve(dense_.size());
            for (const T& v : dense_) p.dense.push_back(scalar_cast<U>(v));
        }
        p.distribution = distribution_;
        p.sparsity = sparsity_;
        p.meta = meta_;
        p.meta.description = detail::cap_description(std::string("Converted ") + dtype_name(dtype()) + "->" +
                                                     dtype_name(dtype_of_v<U>) + " " + meta_.description);
        p.history = history_;
        p.history.push_back({OpCode::Convert, {static_cast<std::int64_t>(dtype_of_v<U>)}, {}, ""});
        p.references = refs_;
        auto r = RecursiveTensor<U>::assemble(std::move(p));
        r.set_uuid(Uuid::generate());
        return r;
    }

    // ============================================================ core algebra
    // Python: contract(other, axes=((0,), (0,))) — generalized tensordot.
    RecursiveTensor contract(const RecursiveTensor& other, const Axes& a = {0}, const Axes& b = {0}) const {
        if (a.size() != b.size()) throw ShapeError("contract: axis lists differ in length");
        validate_axes(a, rank(), "contract(self)");
        validate_axes(b, other.rank(), "contract(other)");
        for (std::size_t i = 0; i < a.size(); ++i)
            if (shape_[a[i]] != other.shape_[b[i]])
                throw ShapeError("contract: extent mismatch self axis " + std::to_string(a[i]) + " (" +
                                 std::to_string(shape_[a[i]]) + ") vs other axis " + std::to_string(b[i]) + " (" +
                                 std::to_string(other.shape_[b[i]]) + ")");
        const Axes ka = detail::complement(a, rank());
        const Axes kb = detail::complement(b, other.rank());
        Shape rshape;
        Extent M = 1, K = 1, N = 1;
        for (auto ax : ka) { rshape.push_back(shape_[ax]); M *= shape_[ax]; }
        for (auto ax : kb) { rshape.push_back(other.shape_[ax]); N *= other.shape_[ax]; }
        for (auto ax : a) K *= shape_[ax];

        const bool sparse_out = is_sparse() && other.is_sparse();
        std::vector<std::int64_t> args{static_cast<std::int64_t>(a.size())};
        for (auto x : a) args.push_back(static_cast<std::int64_t>(x));
        for (auto x : b) args.push_back(static_cast<std::int64_t>(x));
        RecursiveTensor r = derive(rshape, sparse_out ? Storage::Sparse : Storage::Dense, OpCode::Contract, args,
                                   "Contraction of ", &other);

        if (!is_sparse() && !other.is_sparse()) {
            Axes pa = ka; pa.insert(pa.end(), a.begin(), a.end());
            Axes pb = b;  pb.insert(pb.end(), kb.begin(), kb.end());
            const auto A = detail::permute_dense(dense_, shape_, pa, nullptr);        // M x K
            const auto B = detail::permute_dense(other.dense_, other.shape_, pb, nullptr);  // K x N
            auto& C = r.dense_;
            for (Extent i = 0; i < M; ++i)
                for (Extent k = 0; k < K; ++k) {
                    const T aik = A[i * K + k];
                    if (aik == T(0)) continue;
                    const T* brow = B.data() + k * N;
                    T* crow = C.data() + i * N;
                    for (Extent j = 0; j < N; ++j) crow[j] += aik * brow[j];
                }
        } else if (is_sparse() && other.is_sparse()) {
            // Hash join on the contracted key: O(nnz_a + nnz_b + matches).
            detail::Splitter sa(shape_, ka, a), sb(other.shape_, b, kb);
            std::unordered_map<Extent, std::vector<std::pair<Extent, T>>> bykey;
            for (const auto& [lin, v] : other.sparse_) {
                auto [kk, n] = sb(lin);
                bykey[kk].emplace_back(n, v);
            }
            for (const auto& [lin, va] : sparse_) {
                auto [m, kk] = sa(lin);
                auto it = bykey.find(kk);
                if (it == bykey.end()) continue;
                for (const auto& [n, vb] : it->second) r.sparse_[m * N + n] += va * vb;
            }
        } else if (is_sparse()) {  // sparse A, dense B
            Axes pb = b; pb.insert(pb.end(), kb.begin(), kb.end());
            const auto B = detail::permute_dense(other.dense_, other.shape_, pb, nullptr);
            detail::Splitter sa(shape_, ka, a);
            auto& C = r.dense_;
            for (const auto& [lin, v] : sparse_) {
                auto [m, kk] = sa(lin);
                const T* brow = B.data() + kk * N;
                T* crow = C.data() + m * N;
                for (Extent j = 0; j < N; ++j) crow[j] += v * brow[j];
            }
        } else {  // dense A, sparse B
            Axes pa = ka; pa.insert(pa.end(), a.begin(), a.end());
            const auto A = detail::permute_dense(dense_, shape_, pa, nullptr);
            detail::Splitter sb(other.shape_, b, kb);
            auto& C = r.dense_;
            for (const auto& [lin, v] : other.sparse_) {
                auto [kk, n] = sb(lin);
                for (Extent m = 0; m < M; ++m) C[m * N + n] += A[m * K + kk] * v;
            }
        }
        return r;
    }

    // Python: expand(new_dimensions) — prepend leading modes; data at leading zeros.
    // Python constraint kept: cannot prepend more modes than the current rank.
    RecursiveTensor expand(const Shape& new_dims) const {
        if (new_dims.size() > rank()) throw ShapeError("expand: cannot expand to more dimensions than the current rank");
        for (auto d : new_dims) if (d == 0) throw ShapeError("expand: new extents must be >= 1");
        Shape rs = new_dims;
        rs.insert(rs.end(), shape_.begin(), shape_.end());
        std::vector<std::int64_t> args(new_dims.begin(), new_dims.end());
        RecursiveTensor r = derive(rs, storage_, OpCode::Expand, args, "Expanded ");
        // Leading zero coordinates leave the row-major offset unchanged.
        if (is_sparse()) r.sparse_ = sparse_;
        else std::copy(dense_.begin(), dense_.end(), r.dense_.begin());
        return r;
    }

    // Python: project(subspace_basis (k x n), axes). Rows are L2-normalized
    // (zero rows left as-is); each listed axis of extent n becomes extent k.
    RecursiveTensor project(const Matrix<T>& basis, const Axes& axes = {0}) const {
        validate_axes(axes, rank(), "project");
        Matrix<T> nb = basis;
        for (std::size_t i = 0; i < nb.rows; ++i) {
            double s = 0;
            for (std::size_t j = 0; j < nb.cols; ++j) s += mag(nb(i, j)) * mag(nb(i, j));
            const double n = s == 0.0 ? 1.0 : std::sqrt(s);
            for (std::size_t j = 0; j < nb.cols; ++j) nb(i, j) = scalar_cast<T>(scalar_cast<W>(nb(i, j)) / n);
        }
        for (auto ax : axes)
            if (nb.cols != shape_[ax])
                throw ShapeError("project: basis width " + std::to_string(nb.cols) + " != axis " + std::to_string(ax) +
                                 " extent " + std::to_string(shape_[ax]));
        std::vector<std::int64_t> args{static_cast<std::int64_t>(nb.rows), static_cast<std::int64_t>(nb.cols)};
        for (auto ax : axes) args.push_back(static_cast<std::int64_t>(ax));
        return apply_mode_products(nb, axes, OpCode::Project, args, "Projection of ");
    }
    RecursiveTensor project(const std::vector<T>& vec, const Axes& axes = {0}) const {
        Matrix<T> m(1, vec.size());
        m.a = vec;
        return project(m, axes);
    }

    // Python: transform(matrix, axes=None). n-mode product per axis, applied
    // sequentially (Python's sparse path summed independent per-axis maps).
    // Python constraint kept: rows <= cols (cannot expand an axis).
    RecursiveTensor transform(const Matrix<T>& M, std::optional<Axes> axes_opt = std::nullopt) const {
        Axes axes;
        if (axes_opt) axes = *axes_opt;
        else for (std::size_t i = 0; i < rank(); ++i) axes.push_back(i);
        validate_axes(axes, rank(), "transform");
        for (auto ax : axes) {
            if (M.cols != shape_[ax])
                throw ShapeError("transform: matrix cols " + std::to_string(M.cols) + " != axis " + std::to_string(ax) +
                                 " extent " + std::to_string(shape_[ax]));
        }
        if (M.rows > M.cols) throw ShapeError("transform: transformation matrix cannot expand tensor dimensions");
        std::vector<std::int64_t> args{static_cast<std::int64_t>(M.rows), static_cast<std::int64_t>(M.cols)};
        for (auto ax : axes) args.push_back(static_cast<std::int64_t>(ax));
        return apply_mode_products(M, axes, OpCode::Transform, args, "Transformation of ");
    }

    // Python: embed(embedding_function, new_rank). Honest version: the caller
    // declares the appended mode extents; fn maps (index, value) to cells in
    // that appended space. Result shape = shape + extra_shape.
    RecursiveTensor embed(const Shape& extra_shape, const EmbedFn& fn) const {
        if (!fn) throw Error("embed: embedding function must be callable");
        Shape rs = shape_;
        rs.insert(rs.end(), extra_shape.begin(), extra_shape.end());
        const Extent inner = volume_of(extra_shape);
        std::vector<std::int64_t> args(extra_shape.begin(), extra_shape.end());
        RecursiveTensor r = derive(rs, storage_, OpCode::Embed, args, "Embedding of ");
        for_each_stored([&](Extent lin, const T& v) {
            const Index idx = delinearize(lin, shape_);
            for (const auto& [eidx, ev] : fn(idx, v)) {
                const Extent e = linearize(eidx, extra_shape);
                const Extent out = lin * inner + e;
                if (r.is_sparse()) { if (mag(ev) > kSparseKeep) r.sparse_[out] = ev; }
                else r.dense_[out] = ev;
            }
        });
        return r;
    }
    // Scalar embedding: value goes to appended index 0 of a new length-1 mode.
    RecursiveTensor embed_scalar(const std::function<T(const T&, const Index&)>& fn) const {
        return embed({1}, [&](const Index& idx, const T& v) {
            return std::vector<std::pair<Index, T>>{{Index{0}, fn(v, idx)}};
        });
    }

    // Python: fractal_iteration(c_function, max_iter). z <- z^2 + c(idx, z0)
    // per cell with escape at |z| > escape_radius (Python dense path had no
    // per-element escape and ran values to inf).
    RecursiveTensor fractal_iteration(const CFn& c_fn, int max_iter = 10, double escape_radius = 2.0) const {
        if (!c_fn) throw Error("fractal_iteration: c_function must be callable");
        RecursiveTensor r = derive(shape_, storage_, OpCode::Fractal, {max_iter}, "Fractal iteration of ");
        auto iterate = [&](Extent lin, T z) {
            const T c = c_fn(delinearize(lin, shape_), z);
            for (int i = 0; i < max_iter; ++i) {
                z = z * z + c;
                if (mag(z) > escape_radius) break;
            }
            return z;
        };
        if (is_sparse()) {
            for (const auto& [lin, v] : sparse_) {
                const T z = iterate(lin, v);
                if (mag(z) > kSparseKeep) r.sparse_[lin] = z;
            }
        } else {
            for (Extent i = 0; i < volume_; ++i) r.dense_[i] = iterate(i, dense_[i]);
        }
        r.meta_.description += " (" + std::to_string(max_iter) + " steps)";
        return r;
    }

    // ============================================================ eigenrecursion
    // Python: compute_eigenstates(axes=(row_axes, col_axes), k, threshold).
    // Square matricization -> Hermitian part -> dominant-|lambda| eigenpairs,
    // verified by Rayleigh quotient with one inverse-iteration refinement.
    // Rectangular -> top-k singular values / right singular vectors.
    EigenResult<T> compute_eigenstates(const Axes& rows, const Axes& cols, std::size_t k = 6,
                                       double threshold = 1e-8, const EigenOptions& opt = {}) const {
        if (k == 0) throw ShapeError("compute_eigenstates: k must be >= 1");
        Axes all = rows;
        all.insert(all.end(), cols.begin(), cols.end());
        validate_axes(all, rank(), "compute_eigenstates");
        if (all.size() != rank()) throw ShapeError("compute_eigenstates: row and column axes must cover every axis");
        std::ostringstream key;
        key << "r";
        for (auto x : rows) key << x << ",";
        key << "c";
        for (auto x : cols) key << x << ",";
        key << "k" << k << "t" << threshold << "d" << opt.dense_limit << "s" << opt.seed;
        {
            std::lock_guard<std::mutex> g(cache_.st->mu);
            auto it = cache_.st->entries.find(key.str());
            if (it != cache_.st->entries.end()) return *it->second;
        }
        auto res = std::make_shared<EigenResult<T>>(solve_eigen(rows, cols, k, threshold, opt));
        {
            std::lock_guard<std::mutex> g(cache_.st->mu);
            cache_.st->entries[key.str()] = res;
        }
        return *res;
    }
    // Python default axes: rank 2 -> ((0),(1)); rank 1 -> ((0),()); rank>=3 -> (all but last, last).
    EigenResult<T> compute_eigenstates(std::size_t k = 6, double threshold = 1e-8, const EigenOptions& opt = {}) const {
        if (rank() == 0) throw ShapeError("compute_eigenstates: rank-0 tensor has no matricization");
        Axes rows, cols;
        if (rank() == 1) rows = {0};
        else { for (std::size_t i = 0; i + 1 < rank(); ++i) rows.push_back(i); cols = {rank() - 1}; }
        return compute_eigenstates(rows, cols, k, threshold, opt);
    }

    // ============================================================ statistics
    // Python: compute_density_function(resolution, threshold) -> (edges, hist)
    // numpy.histogram(density=True) semantics over values with |v| > threshold.
    Histogram compute_density_function(int resolution = 50, double threshold = 0.01) const {
        if (resolution <= 0) throw Error("compute_density_function: resolution must be positive");
        std::vector<double> vals;
        for_each_stored([&](Extent, const T& v) {
            const double x = is_complex_v<T> ? mag(v) : real_part(v);
            if (std::abs(x) > threshold) vals.push_back(x);
        });
        Histogram h;
        h.edges.resize(static_cast<std::size_t>(resolution) + 1);
        h.density.assign(static_cast<std::size_t>(resolution), 0.0);
        double lo = 0.0, hi = 1.0;
        if (!vals.empty()) {
            lo = *std::min_element(vals.begin(), vals.end());
            hi = *std::max_element(vals.begin(), vals.end());
            if (lo == hi) { lo -= 0.5; hi += 0.5; }
        }
        const double w = (hi - lo) / resolution;
        for (int i = 0; i <= resolution; ++i) h.edges[static_cast<std::size_t>(i)] = lo + w * i;
        if (vals.empty()) return h;
        for (double x : vals) {
            auto bin = static_cast<long long>((x - lo) / w);
            if (bin >= resolution) bin = resolution - 1;
            if (bin < 0) bin = 0;
            h.density[static_cast<std::size_t>(bin)] += 1.0;
        }
        for (auto& d : h.density) d /= (static_cast<double>(vals.size()) * w);
        return h;
    }

    // Shannon entropy (nats) of the magnitude distribution of nonzero cells.
    // Storage-invariant (Python's sparse and dense paths disagreed).
    double compute_entropy() const {
        double total = 0;
        std::vector<double> m;
        for_each_stored([&](Extent, const T& v) { const double a = mag(v); if (a > 0) { m.push_back(a); total += a; } });
        if (m.empty() || total <= 0) return 0.0;
        double h = 0;
        for (double a : m) {
            const double p = std::clamp(a / total, 1e-12, 1.0);
            h -= p * std::log(p);
        }
        return h;
    }

    // Entry-wise norms (Python's dense path called matrix norms by accident).
    double norm(NormType t = NormType::L2) const {
        double acc = 0;
        for_each_stored([&](Extent, const T& v) {
            const double a = mag(v);
            if (t == NormType::L1) acc += a;
            else if (t == NormType::L2) acc += a * a;
            else acc = std::max(acc, a);
        });
        return t == NormType::L2 ? std::sqrt(acc) : acc;
    }
    RecursiveTensor normalize(NormType t = NormType::L2) const {
        const double n = norm(t);
        RecursiveTensor r = derive(shape_, storage_, OpCode::Normalize, {static_cast<std::int64_t>(t)}, "Normalized ");
        const W inv = n > 0 ? W(1.0 / n) : W(1.0);
        if (is_sparse()) for (const auto& [k, v] : sparse_) r.sparse_[k] = scalar_cast<T>(scalar_cast<W>(v) * inv);
        else for (Extent i = 0; i < volume_; ++i) r.dense_[i] = scalar_cast<T>(scalar_cast<W>(dense_[i]) * inv);
        r.refs_ = refs_;
        return r;
    }

    // Python: apply_function(func, threshold). Sparse: maps *stored* cells only
    // (implicit zeros stay zero). Dense: maps every cell. Cells with
    // |f(v)| <= threshold are dropped (sparse) / zeroed (dense).
    RecursiveTensor apply_function(const std::function<T(const T&)>& f, std::optional<double> threshold = std::nullopt,
                                   const std::string& label = "unnamed_function") const {
        if (!f) throw Error("apply_function: func must be callable");
        RecursiveTensor r = derive(shape_, storage_, OpCode::ApplyFunction, {}, "Function " + label + " applied to ");
        r.history_.back().label = label;
        if (is_sparse()) {
            for (const auto& [k, v] : sparse_) {
                const T nv = f(v);
                if (!threshold || mag(nv) > *threshold) r.sparse_[k] = nv;
            }
        } else {
            for (Extent i = 0; i < volume_; ++i) {
                const T nv = f(dense_[i]);
                r.dense_[i] = (threshold && mag(nv) <= *threshold) ? T(0) : nv;
            }
        }
        r.refs_ = refs_;
        return r;
    }

    // Python: compute_dict_compatibility(other) — score in [0, 1].
    double compatibility(const RecursiveTensor& other) const {
        if (!is_sparse() && !other.is_sparse()) {
            if (volume_ != other.volume_) throw ShapeError("compatibility: dense tensors differ in size");
            W dot(0);
            double n1 = 0, n2 = 0;
            for (Extent i = 0; i < volume_; ++i) {
                const W x = scalar_cast<W>(dense_[i]), y = scalar_cast<W>(other.dense_[i]);
                dot += conj_of(x) * y;
                n1 += std::norm(std::complex<double>(real_part(x), imag_part(x)));
                n2 += std::norm(std::complex<double>(real_part(y), imag_part(y)));
            }
            n1 = std::sqrt(n1); n2 = std::sqrt(n2);
            if (n1 > 0 && n2 > 0) return std::abs(dot) / (n1 * n2);
            return (n1 == 0 && n2 == 0) ? 1.0 : 0.0;
        }
        std::unordered_map<Extent, T> d1, d2;
        for_each_stored([&](Extent k, const T& v) { if (!is_sparse() ? v != T(0) : true) d1[k] = v; });
        other.for_each_stored([&](Extent k, const T& v) { if (!other.is_sparse() ? v != T(0) : true) d2[k] = v; });
        if (d1.empty() && d2.empty()) return 1.0;
        if (d1.empty() || d2.empty()) return 0.0;
        std::size_t common = 0;
        double sim_sum = 0;
        for (const auto& [k, v1] : d1) {
            auto it = d2.find(k);
            if (it == d2.end()) continue;
            ++common;
            const T v2 = it->second;
            if constexpr (is_complex_v<T>) {
                const double a1 = mag(v1), a2 = mag(v2);
                const double mag_sim = 1.0 - std::min(1.0, std::abs(a1 - a2) / std::max({a1, a2, 1e-10}));
                const double ph = std::abs(std::arg(scalar_cast<std::complex<double>>(v1)) -
                                           std::arg(scalar_cast<std::complex<double>>(v2)));
                const double phase_sim = 1.0 - std::min(ph, 2 * kPi - ph) / kPi;
                sim_sum += 0.7 * mag_sim + 0.3 * phase_sim;
            } else {
                const double mx = std::max(mag(v1), mag(v2));
                sim_sum += mx > 1e-10 ? 1.0 - std::min(1.0, mag(v1 - v2) / mx) : 1.0;
            }
        }
        const std::size_t uni = d1.size() + d2.size() - common;
        const double key_sim = static_cast<double>(common) / static_cast<double>(uni);
        if (common == 0) return key_sim;
        return 0.5 * key_sim + 0.5 * (sim_sum / static_cast<double>(common));
    }

    // ============================================================ arithmetic
    RecursiveTensor operator+(const RecursiveTensor& o) const {
        if (shape_ != o.shape_) throw ShapeError("add: shapes differ " + shape_str(shape_) + " vs " + shape_str(o.shape_));
        const bool sp = is_sparse() && o.is_sparse();
        RecursiveTensor r = derive(shape_, sp ? Storage::Sparse : Storage::Dense, OpCode::Add, {}, "Addition of ", &o);
        if (sp) {
            r.sparse_ = sparse_;
            for (const auto& [k, v] : o.sparse_) r.sparse_[k] += v;
        } else {
            r.dense_ = to_dense_array();
            o.for_each_stored([&](Extent k, const T& v) { r.dense_[k] += v; });
        }
        r.refs_ = refs_;
        return r;
    }
    // Mathematically honest: a nonzero scalar densifies a sparse tensor.
    RecursiveTensor operator+(const T& s) const {
        const bool keep_sparse = is_sparse() && s == T(0);
        RecursiveTensor r = derive(shape_, keep_sparse ? Storage::Sparse : Storage::Dense, OpCode::Add, {}, "Scalar addition to ");
        if (keep_sparse) r.sparse_ = sparse_;
        else { r.dense_ = to_dense_array(); for (auto& v : r.dense_) v += s; }
        r.refs_ = refs_;
        return r;
    }
    // Element-wise (Hadamard) product. Any sparse operand -> sparse result.
    RecursiveTensor operator*(const RecursiveTensor& o) const {
        if (shape_ != o.shape_) throw ShapeError("multiply: shapes differ " + shape_str(shape_) + " vs " + shape_str(o.shape_));
        const bool sp = is_sparse() || o.is_sparse();
        RecursiveTensor r = derive(shape_, sp ? Storage::Sparse : Storage::Dense, OpCode::Multiply, {}, "Element-wise multiplication of ", &o);
        if (!sp) {
            for (Extent i = 0; i < volume_; ++i) r.dense_[i] = dense_[i] * o.dense_[i];
        } else {
            if (is_sparse() && o.is_sparse()) {          // key intersection (Python)
                for (const auto& [k, v] : sparse_) {
                    auto it = o.sparse_.find(k);
                    if (it != o.sparse_.end()) r.sparse_[k] = v * it->second;
                }
            } else if (is_sparse()) {                    // every stored key of the sparse side
                for (const auto& [k, v] : sparse_) r.sparse_[k] = v * o.dense_[k];
            } else {
                for (const auto& [k, v] : o.sparse_) r.sparse_[k] = dense_[k] * v;
            }
        }
        r.refs_ = refs_;
        return r;
    }
    RecursiveTensor operator*(const T& s) const {
        RecursiveTensor r = derive(shape_, storage_, OpCode::Multiply, {}, "Scalar multiplication of ");
        if (is_sparse()) for (const auto& [k, v] : sparse_) r.sparse_[k] = v * s;
        else for (Extent i = 0; i < volume_; ++i) r.dense_[i] = dense_[i] * s;
        r.refs_ = refs_;
        return r;
    }
    RecursiveTensor operator-(const RecursiveTensor& o) const { return *this + (o * T(-1)); }

    // ============================================================ structural (whitepaper §4.1)
    RecursiveTensor transpose(const Axes& perm) const {
        if (perm.size() != rank()) throw ShapeError("transpose: permutation length != rank");
        validate_axes(perm, rank(), "transpose");
        Shape rs(rank());
        for (std::size_t i = 0; i < rank(); ++i) rs[i] = shape_[perm[i]];
        std::vector<std::int64_t> args(perm.begin(), perm.end());
        RecursiveTensor r = derive(rs, storage_, OpCode::Transpose, args, "Transpose of ");
        if (is_sparse()) {
            const auto rst = strides_of(rs);
            for (const auto& [k, v] : sparse_) {
                const Index idx = delinearize(k, shape_);
                Extent out = 0;
                for (std::size_t i = 0; i < rank(); ++i) out += idx[perm[i]] * rst[i];
                r.sparse_[out] = v;
            }
        } else {
            r.dense_ = detail::permute_dense(dense_, shape_, perm, nullptr);
        }
        return r;
    }
    RecursiveTensor swap_axes(std::size_t a, std::size_t b) const {
        Axes p(rank());
        for (std::size_t i = 0; i < rank(); ++i) p[i] = i;
        if (a >= rank() || b >= rank()) throw ShapeError("swap_axes: axis out of range");
        std::swap(p[a], p[b]);
        return transpose(p);
    }
    // Row-major reshape; volume must match. Linear offsets are invariant.
    RecursiveTensor reshape(const Shape& ns) const {
        if (volume_of(ns) != volume_) throw ShapeError("reshape: volume mismatch " + shape_str(shape_) + " -> " + shape_str(ns));
        std::vector<std::int64_t> args(ns.begin(), ns.end());
        RecursiveTensor r = derive(ns, storage_, OpCode::Reshape, args, "Reshape of ");
        if (is_sparse()) r.sparse_ = sparse_; else r.dense_ = dense_;
        return r;
    }
    // Whitepaper T.reshape(axis, [p0, p1, ...]): split one axis into several.
    RecursiveTensor split_axis(std::size_t axis, const Shape& parts) const {
        if (axis >= rank()) throw ShapeError("split_axis: axis out of range");
        if (volume_of(parts) != shape_[axis]) throw ShapeError("split_axis: parts do not multiply to the axis extent");
        Shape ns(shape_.begin(), shape_.begin() + static_cast<long>(axis));
        ns.insert(ns.end(), parts.begin(), parts.end());
        ns.insert(ns.end(), shape_.begin() + static_cast<long>(axis) + 1, shape_.end());
        return reshape(ns);
    }

    // Whitepaper T.reduce(op, dim). Implicit sparse zeros participate.
    // Max/Min compare real values (real T) or magnitudes (complex T).
    ReduceResult<T> reduce(ReduceOp op, std::size_t axis) const {
        if (axis >= rank()) throw ShapeError("reduce: axis out of range");
        const Extent n = shape_[axis];
        if ((op == ReduceOp::Max || op == ReduceOp::Min) && n == 0) throw ShapeError("reduce: max/min over empty axis");
        Shape rs;
        for (std::size_t i = 0; i < rank(); ++i) if (i != axis) rs.push_back(shape_[i]);
        const bool want_arg = op == ReduceOp::Max || op == ReduceOp::Min;
        RecursiveTensor r = derive(rs, (op == ReduceOp::Sum || op == ReduceOp::Mean) ? storage_ : Storage::Dense,
                                   OpCode::Reduce, {static_cast<std::int64_t>(op), static_cast<std::int64_t>(axis)}, "Reduction of ");
        ReduceResult<T> out;
        auto key = [&](const T& v) { return is_complex_v<T> ? mag(v) : real_part(v); };
        auto better = [&](const T& a, const T& b) { return op == ReduceOp::Max ? key(a) > key(b) : key(a) < key(b); };
        Axes kept = detail::complement({axis}, rank());
        detail::Splitter sp(shape_, kept, {axis});
        const Extent outer = volume_of(rs);
        if (op == ReduceOp::Sum || op == ReduceOp::Mean) {
            const W scale = op == ReduceOp::Mean ? W(n ? 1.0 / static_cast<double>(n) : 0.0) : W(1.0);
            for_each_stored([&](Extent lin, const T& v) {
                auto [o, t] = sp(lin);
                (void)t;
                if (r.is_sparse()) r.sparse_[o] += v; else r.dense_[o] += v;
            });
            if (op == ReduceOp::Mean) {
                if (r.is_sparse()) for (auto& kv : r.sparse_) kv.second = scalar_cast<T>(scalar_cast<W>(kv.second) * scale);
                else for (auto& v : r.dense_) v = scalar_cast<T>(scalar_cast<W>(v) * scale);
            }
        } else {
            out.arg.assign(outer, 0);
            if (!is_sparse()) {
                std::vector<bool> init(outer, false);
                for (Extent lin = 0; lin < volume_; ++lin) {
                    auto [o, t] = sp(lin);
                    if (!init[o] || better(dense_[lin], r.dense_[o]) ) { r.dense_[o] = dense_[lin]; out.arg[o] = t; init[o] = true; }
                }
            } else {
                std::unordered_map<Extent, std::vector<std::pair<Extent, T>>> fibers;
                for (const auto& [lin, v] : sparse_) { auto [o, t] = sp(lin); fibers[o].emplace_back(t, v); }
                for (Extent o = 0; o < outer; ++o) {
                    std::vector<std::pair<Extent, T>> f;
                    if (auto it = fibers.find(o); it != fibers.end()) f = it->second;
                    std::sort(f.begin(), f.end(), [](const auto& x, const auto& y) { return x.first < y.first; });
                    if (f.size() < n) {  // an implicit zero exists; add it at its first index
                        Extent miss = 0;
                        for (const auto& e : f) { if (e.first == miss) ++miss; else break; }
                        f.insert(std::lower_bound(f.begin(), f.end(), miss,
                                                  [](const auto& e, Extent m) { return e.first < m; }),
                                 {miss, T(0)});
                    }
                    T best = f.front().second;       // numpy: first occurrence wins ties
                    Extent barg = f.front().first;
                    for (const auto& [t, v] : f) if (better(v, best)) { best = v; barg = t; }
                    r.dense_[o] = best;
                    out.arg[o] = barg;
                }
            }
        }
        if (!want_arg) out.arg.clear();
        out.values = std::make_shared<RecursiveTensor>(std::move(r));
        return out;
    }

    // ============================================================ decompositions
    // Python: tucker_decomposition(ranks). HOSVD; default rank min(extent, 5).
    TuckerResult<T> tucker_decomposition(std::optional<std::vector<std::size_t>> ranks_opt = std::nullopt) const {
        std::vector<std::size_t> ranks;
        if (ranks_opt) ranks = *ranks_opt;
        else for (auto e : shape_) ranks.push_back(static_cast<std::size_t>(std::min<Extent>(e, 5)));
        if (ranks.size() != rank()) throw ShapeError("tucker: ranks must match the number of modes");
        const auto dense = to_dense_array();
        TuckerResult<T> out;
        for (std::size_t mode = 0; mode < rank(); ++mode) {
            Axes perm{mode};
            for (std::size_t i = 0; i < rank(); ++i) if (i != mode) perm.push_back(i);
            const auto unf = detail::permute_dense(dense, shape_, perm, nullptr);
            const std::size_t m = static_cast<std::size_t>(shape_[mode]);
            const std::size_t n = m ? unf.size() / m : 0;
            Matrix<W> A(m, n);
            for (std::size_t i = 0; i < unf.size(); ++i) A.a[i] = scalar_cast<W>(unf[i]);
            auto s = svd_jacobi(A);
            const std::size_t r = std::min(ranks[mode], s.U.cols);
            Matrix<T> F(m, r);
            for (std::size_t i = 0; i < m; ++i)
                for (std::size_t j = 0; j < r; ++j) F(i, j) = scalar_cast<T>(s.U(i, j));
            out.factors.push_back(std::move(F));
        }
        RecursiveTensor core = to_dense();
        for (std::size_t mode = 0; mode < rank(); ++mode) {
            Matrix<T> Fh = out.factors[mode].conj_transpose();  // r x extent
            core = core.mode_product_raw(Fh, mode);
        }
        core.history_ = history_;
        core.push_op({OpCode::Tucker, std::vector<std::int64_t>(ranks.begin(), ranks.end()), {}, ""});
        core.meta_.description = detail::cap_description("Tucker core of " + meta_.description);
        out.core = std::make_shared<RecursiveTensor>(std::move(core));
        return out;
    }

    // TT-SVD: cores[i] has shape (r_{i-1}, d_i, r_i), r_0 = r_N = 1.
    // (Python's to_mps did not fold the bond into the next physical index and
    // did not produce a valid MPS.) Truncation: max_bond and relative cutoff.
    std::vector<RecursiveTensor> to_mps(std::optional<std::size_t> max_bond = std::nullopt, double rel_cutoff = 0.0) const {
        if (rank() == 0) throw ShapeError("to_mps: rank-0 tensor");
        std::vector<RecursiveTensor> cores;
        std::vector<W> cur;
        for (const T& v : to_dense_array()) cur.push_back(scalar_cast<W>(v));
        std::size_t rprev = 1;
        for (std::size_t i = 0; i + 1 < rank(); ++i) {
            const std::size_t d = static_cast<std::size_t>(shape_[i]);
            const std::size_t rows = rprev * d;
            const std::size_t cols = rows ? cur.size() / rows : 0;
            Matrix<W> A(rows, cols);
            A.a = cur;
            auto s = svd_jacobi(A);
            std::size_t r = s.S.size();
            if (max_bond) r = std::min(r, *max_bond);
            if (rel_cutoff > 0 && !s.S.empty())
                while (r > 1 && s.S[r - 1] < rel_cutoff * s.S[0]) --r;
            r = std::max<std::size_t>(r, 1);
            std::vector<T> core(rows * r);
            for (std::size_t a = 0; a < rows; ++a)
                for (std::size_t b = 0; b < r; ++b) core[a * r + b] = scalar_cast<T>(s.U(a, b));
            RecursiveTensor c = from_dense({rprev, d, r}, std::move(core));
            c.meta_.description = "MPS core " + std::to_string(i) + " of " + meta_.description;
            c.push_op({OpCode::Mps, {static_cast<std::int64_t>(i)}, uuid_, ""});
            cores.push_back(std::move(c));
            // next = diag(S) V^H  (r x cols)
            std::vector<W> next(r * cols);
            for (std::size_t a = 0; a < r; ++a)
                for (std::size_t b = 0; b < cols; ++b) next[a * cols + b] = s.S[a] * conj_of(s.V(b, a));
            cur = std::move(next);
            rprev = r;
        }
        std::vector<T> last;
        for (const W& v : cur) last.push_back(scalar_cast<T>(v));
        RecursiveTensor c = from_dense({rprev, shape_.back(), 1}, std::move(last));
        c.push_op({OpCode::Mps, {static_cast<std::int64_t>(rank() - 1)}, uuid_, ""});
        cores.push_back(std::move(c));
        return cores;
    }
    static RecursiveTensor from_mps(const std::vector<RecursiveTensor>& cores) {
        if (cores.empty()) throw ShapeError("from_mps: no cores");
        RecursiveTensor acc = cores[0].to_dense();
        for (std::size_t i = 1; i < cores.size(); ++i) acc = acc.contract(cores[i].to_dense(), {acc.rank() - 1}, {0});
        Shape s(acc.shape_.begin() + 1, acc.shape_.end() - 1);  // drop boundary bonds of size 1
        return from_dense(s, acc.to_dense_array());
    }

    // ============================================================ geometry & signal
    // Python: to_hyperbolic_space(curvature). Poincare-ball position of each
    // (normalized) index sets a phase rotation: v -> |v| exp(i(arg v + kappa d)).
    RecursiveTensor<std::complex<real_type>> to_hyperbolic_space(double curvature = -1.0) const {
        using C = std::complex<real_type>;
        typename RecursiveTensor<C>::Parts p;
        p.shape = shape_;
        p.storage = storage_;
        p.distribution = distribution_;
        p.sparsity = sparsity_;
        p.meta = meta_;
        p.meta.description = detail::cap_description("Hyperbolic transformation of " + meta_.description);
        p.meta.extra["hyperbolic"] = "true";
        p.meta.extra["curvature"] = std::to_string(curvature);
        p.meta.operations_count = meta_.operations_count + 1;
        p.meta.modified_at = unix_now();
        p.history = history_;
        p.history.push_back({OpCode::Hyperbolic, {}, {}, std::to_string(curvature)});
        auto map_one = [&](Extent lin, const T& v) -> C {
            const Index idx = delinearize(lin, shape_);
            std::vector<double> x(rank());
            double n2 = 0;
            for (std::size_t a = 0; a < rank(); ++a) { x[a] = static_cast<double>(idx[a]) / static_cast<double>(shape_[a]); n2 += x[a] * x[a]; }
            double nrm = std::sqrt(n2);
            if (nrm >= 1.0) { for (auto& e : x) e /= (nrm + 1e-8); n2 = 0; for (auto e : x) n2 += e * e; }
            const double dist = std::acosh(1.0 + 2.0 * n2 / ((1.0 - n2) * 1.0 + 1e-8));
            const double phase = is_complex_v<T> ? std::arg(scalar_cast<std::complex<double>>(v)) : 0.0;
            const std::complex<double> z = std::polar(mag(v), phase + curvature * dist);
            return C(static_cast<real_type>(z.real()), static_cast<real_type>(z.imag()));
        };
        if (is_sparse()) {
            for (const auto& [k, v] : sorted_cells()) { p.sparse_offsets.push_back(k); p.sparse_values.push_back(map_one(k, v)); }
        } else {
            p.dense.resize(volume_);
            for (Extent i = 0; i < volume_; ++i) p.dense[i] = map_one(i, dense_[i]);
        }
        auto r = RecursiveTensor<C>::assemble(std::move(p));
        r.set_uuid(Uuid::generate());
        return r;
    }

    // Python: apply_temporal_convolution(kernel, time_axis=None -> last axis).
    // numpy/scipy 'same' convolution along one axis with zero boundary, for
    // both storages (Python's sparse path ignored gaps between stored ticks).
    RecursiveTensor apply_temporal_convolution(const std::vector<T>& kernel, std::optional<long long> time_axis = std::nullopt) const {
        if (rank() < 1) throw ShapeError("cannot convolve a rank-0 tensor");
        if (kernel.empty()) throw Error("convolution kernel must be non-empty");
        const std::size_t axis = time_axis ? normalize_axis(*time_axis, rank()) : rank() - 1;
        const Extent N = shape_[axis];
        const long long K = static_cast<long long>(kernel.size());
        const long long off = (K - 1) / 2;
        Extent inner = 1;
        for (std::size_t i = axis + 1; i < rank(); ++i) inner *= shape_[i];
        RecursiveTensor r = derive(shape_, storage_, OpCode::TemporalConvolution, {static_cast<std::int64_t>(axis)}, "Temporal convolution of ");
        auto emit = [&](Extent lin, const T& v) {
            const Extent t = (lin / inner) % (N ? N : 1);
            const Extent base = lin - t * inner;
            for (long long j = 0; j < K; ++j) {
                const long long to = static_cast<long long>(t) + j - off;
                if (to < 0 || to >= static_cast<long long>(N)) continue;
                const Extent o = base + static_cast<Extent>(to) * inner;
                if (r.is_sparse()) r.sparse_[o] += kernel[static_cast<std::size_t>(j)] * v;
                else r.dense_[o] += kernel[static_cast<std::size_t>(j)] * v;
            }
        };
        for_each_stored([&](Extent lin, const T& v) { if (v != T(0)) emit(lin, v); });
        if (r.is_sparse())
            for (auto it = r.sparse_.begin(); it != r.sparse_.end();) {
                if (mag(it->second) <= kSparseKeep) it = r.sparse_.erase(it); else ++it;
            }
        return r;
    }

    // ============================================================ topology
    // Python: persistent_homology(max_dimension). Points = nonzero cells,
    // vertex filtration |v|, edges between cells closer than `radius` with
    // filtration max(dist, f_u, f_v). Union-find with the elder rule gives
    // H0 exactly; H1 on a 1-skeleton is only essential cycles (gudhi omits
    // the top dimension by default, so include_cycles defaults to false).
    std::vector<PersistencePair> persistent_homology(int max_dimension = 1, double radius = 2.0,
                                                     double min_persistence = 0.01, bool include_cycles = false) const {
        std::vector<std::pair<Extent, double>> pts;
        for_each_stored([&](Extent lin, const T& v) {
            const double a = mag(v);
            if (is_sparse() ? true : a > 1e-6) pts.emplace_back(lin, a);
        });
        std::sort(pts.begin(), pts.end());
        const std::size_t n = pts.size();
        std::vector<Index> coords(n);
        for (std::size_t i = 0; i < n; ++i) coords[i] = delinearize(pts[i].first, shape_);
        auto dist = [&](std::size_t i, std::size_t j) {
            double s = 0;
            for (std::size_t a = 0; a < rank(); ++a) {
                const double d = static_cast<double>(coords[i][a]) - static_cast<double>(coords[j][a]);
                s += d * d;
            }
            return std::sqrt(s);
        };
        struct Edge { double f; std::size_t u, v; };
        std::vector<Edge> edges;
        const long long R = static_cast<long long>(std::ceil(radius)) - 1;
        double lattice_cost = 1;
        for (std::size_t a = 0; a < rank(); ++a) lattice_cost *= static_cast<double>(2 * std::max(R, 0LL) + 1);
        if (R >= 0 && lattice_cost < static_cast<double>(n)) {
            std::unordered_map<Extent, std::size_t> where;
            for (std::size_t i = 0; i < n; ++i) where[pts[i].first] = i;
            std::vector<long long> o(rank(), -R);
            for (std::size_t i = 0; i < n; ++i) {
                std::fill(o.begin(), o.end(), -R);
                while (true) {
                    Index nb(rank());
                    bool ok = true;
                    for (std::size_t a = 0; a < rank() && ok; ++a) {
                        const long long c = static_cast<long long>(coords[i][a]) + o[a];
                        if (c < 0 || c >= static_cast<long long>(shape_[a])) ok = false; else nb[a] = static_cast<Extent>(c);
                    }
                    if (ok) {
                        auto it = where.find(linearize(nb, shape_));
                        if (it != where.end() && it->second > i) {
                            const double d = dist(i, it->second);
                            if (d < radius) edges.push_back({std::max({d, pts[i].second, pts[it->second].second}), i, it->second});
                        }
                    }
                    std::size_t a = 0;
                    while (a < rank() && ++o[a] > R) { o[a] = -R; ++a; }
                    if (a == rank()) break;
                }
            }
        } else {
            for (std::size_t i = 0; i < n; ++i)
                for (std::size_t j = i + 1; j < n; ++j) {
                    const double d = dist(i, j);
                    if (d < radius) edges.push_back({std::max({d, pts[i].second, pts[j].second}), i, j});
                }
        }
        std::sort(edges.begin(), edges.end(), [](const Edge& a, const Edge& b) { return a.f < b.f; });
        std::vector<std::size_t> parent(n);
        std::iota(parent.begin(), parent.end(), 0);
        std::vector<double> birth(n);
        for (std::size_t i = 0; i < n; ++i) birth[i] = pts[i].second;
        std::function<std::size_t(std::size_t)> find = [&](std::size_t x) {
            while (parent[x] != x) { parent[x] = parent[parent[x]]; x = parent[x]; }
            return x;
        };
        std::vector<PersistencePair> out;
        const double inf = std::numeric_limits<double>::infinity();
        for (const auto& e : edges) {
            std::size_t a = find(e.u), b = find(e.v);
            if (a == b) {
                if (include_cycles && max_dimension >= 1) out.push_back({1, e.f, inf});
                continue;
            }
            if (birth[a] > birth[b] || (birth[a] == birth[b] && a > b)) std::swap(a, b);  // a is elder
            if (e.f - birth[b] > min_persistence) out.push_back({0, birth[b], e.f});
            parent[b] = a;
        }
        for (std::size_t i = 0; i < n; ++i) if (find(i) == i) out.push_back({0, birth[i], inf});
        std::sort(out.begin(), out.end(), [](const auto& x, const auto& y) {
            return x.dimension != y.dimension ? x.dimension < y.dimension : x.birth < y.birth;
        });
        return out;
    }

    // ============================================================ recursive references
    // Whitepaper Def. 3: T(i) = f(T(g(i))). Each reference is one (g, f) edge.
    void add_reference(const Index& source, const Index& target, RefType type, std::vector<double> params = {},
                       std::uint8_t max_iterations = 16, double convergence_threshold = 1e-8, std::uint8_t iteration_axis = 0) {
        RecursiveReference r;
        r.source = linearize(source, shape_);
        r.target = linearize(target, shape_);
        r.type = type;
        r.params = std::move(params);
        r.max_iterations = max_iterations;
        r.convergence_threshold = convergence_threshold;
        r.iteration_axis = iteration_axis;
        if (iteration_axis >= std::max<std::size_t>(rank(), 1)) throw ShapeError("add_reference: iteration_axis out of rank");
        refs_.push_back(std::move(r));
        touch();
    }
    void clear_references() { refs_.clear(); touch(); }

    // Whitepaper Thm. 2 made operational: Gauss-Seidel sweeps over the
    // references until max |delta| <= tol (a fixed point S with f(S) = S).
    // Converges when the induced map is contractive; otherwise reports
    // converged=false after max_sweeps. Mutates this tensor.
    SettleReport settle_references(int max_sweeps = 100, double tol = 1e-10) {
        SettleReport rep;
        if (refs_.empty()) { rep.converged = true; return rep; }
        for (int s = 0; s < max_sweeps; ++s) {
            double md = 0;
            for (const auto& ref : refs_) {
                const T old = get_linear(ref.target);
                const T nv = evaluate_reference(ref);
                md = std::max(md, mag(nv - old));
                set_linear_nohist(ref.target, nv);
            }
            rep.sweeps = s + 1;
            rep.max_delta = md;
            if (!(md > tol)) { rep.converged = !std::isnan(md); break; }
        }
        touch();
        push_op({OpCode::SettleReferences, {rep.sweeps, rep.converged ? 1 : 0}, {}, ""});
        meta_.operations_count++;
        return rep;
    }

    // Raw n-mode product with no normalization/validation beyond shapes.
    RecursiveTensor mode_product_raw(const Matrix<T>& M, std::size_t axis) const {
        if (axis >= rank() || M.cols != shape_[axis]) throw ShapeError("mode_product: shape mismatch");
        Shape rs = shape_;
        rs[axis] = M.rows;
        RecursiveTensor r = derive(rs, storage_, OpCode::Transform, {static_cast<std::int64_t>(M.rows), static_cast<std::int64_t>(M.cols), static_cast<std::int64_t>(axis)}, "Mode product of ");
        mode_product_into(M, axis, r, false);
        return r;
    }

private:
    Shape shape_;
    Extent volume_ = 0;
    Storage storage_ = Storage::Dense;
    std::vector<T> dense_;
    SparseMap sparse_;
    Distribution distribution_ = Distribution::Normal;
    double sparsity_ = 0.0;
    Uuid uuid_{};
    Metadata meta_;
    std::vector<OpRecord> history_;
    std::vector<RecursiveReference> refs_;
    std::size_t history_limit_ = 4096;
    mutable detail::EigenCacheSlot<T> cache_;

    template <class U> friend class RecursiveTensor;

    void init_metadata() {
        meta_.created_at = unix_now();
        meta_.modified_at = meta_.created_at;
        meta_.operations_count = 0;
        meta_.description = "RecursiveTensor(" + shape_str(shape_) + ", rank=" + std::to_string(rank()) + ")";
    }
    void touch() {
        meta_.modified_at = unix_now();
        cache_.clear();
    }
    void trim_history() {
        if (history_limit_ && history_.size() > history_limit_)
            history_.erase(history_.begin(), history_.begin() + static_cast<long>(history_.size() - history_limit_));
    }
    void push_op(OpRecord r) {
        history_.push_back(std::move(r));
        trim_history();
    }
    void set_linear_nohist(Extent lin, const T& v) {
        if (is_sparse()) { if (v == T(0)) sparse_.erase(lin); else sparse_[lin] = v; }
        else dense_[lin] = v;
    }

    // Construct an (all-zero) result tensor inheriting provenance.
    RecursiveTensor derive(const Shape& rshape, Storage st, OpCode code, std::vector<std::int64_t> args,
                           const std::string& prefix, const RecursiveTensor* peer = nullptr) const {
        RecursiveTensor r;
        r.shape_ = rshape;
        r.volume_ = volume_of(rshape);
        r.storage_ = st;
        if (st == Storage::Dense) r.dense_.assign(r.volume_, T(0));
        r.distribution_ = distribution_;
        r.sparsity_ = sparsity_;
        r.uuid_ = Uuid::generate();
        r.meta_ = meta_;
        r.meta_.created_at = unix_now();
        r.meta_.modified_at = r.meta_.created_at;
        r.meta_.operations_count = meta_.operations_count + 1;
        // Empty descriptions are named by short uuid so provenance text stays readable.
        auto name_of = [](const RecursiveTensor& t) {
            return t.meta_.description.empty() ? "tensor " + t.uuid_.str().substr(0, 8) : t.meta_.description;
        };
        std::string d = prefix + name_of(*this);
        if (peer) d += " with " + name_of(*peer);
        r.meta_.description = detail::cap_description(d);
        r.history_limit_ = history_limit_;
        r.history_ = history_;
        if (peer) r.history_.insert(r.history_.end(), peer->history_.begin(), peer->history_.end());
        r.push_op({code, std::move(args), peer ? peer->uuid_ : Uuid{}, ""});
        return r;
    }
    RecursiveTensor() = default;  // for derive()

    void mode_product_into(const Matrix<T>& M, std::size_t axis, RecursiveTensor& r, bool sparse_threshold) const {
        const Extent n = shape_[axis], m = M.rows;
        Extent inner = 1;
        for (std::size_t i = axis + 1; i < rank(); ++i) inner *= shape_[i];
        if (!is_sparse()) {
            const Extent block = n * inner;
            const Extent outer = block ? volume_ / block : 0;
            for (Extent o = 0; o < outer; ++o)
                for (Extent i = 0; i < m; ++i) {
                    T* dst = r.dense_.data() + (o * m + i) * inner;
                    for (Extent j = 0; j < n; ++j) {
                        const T w = M(static_cast<std::size_t>(i), static_cast<std::size_t>(j));
                        if (w == T(0)) continue;
                        const T* src = dense_.data() + (o * n + j) * inner;
                        for (Extent q = 0; q < inner; ++q) dst[q] += w * src[q];
                    }
                }
        } else {
            for (const auto& [lin, v] : sparse_) {
                const Extent q = lin % inner;
                const Extent j = (lin / inner) % n;
                const Extent o = lin / (inner * n);
                for (Extent i = 0; i < m; ++i) {
                    const T c = M(static_cast<std::size_t>(i), static_cast<std::size_t>(j)) * v;
                    if (sparse_threshold ? mag(c) > kSparseKeep : c != T(0)) r.sparse_[(o * m + i) * inner + q] += c;
                }
            }
        }
    }

    RecursiveTensor apply_mode_products(const Matrix<T>& M, const Axes& axes, OpCode code,
                                        std::vector<std::int64_t> args, const std::string& prefix) const {
        RecursiveTensor cur = *this;
        for (auto ax : axes) {
            Shape rs = cur.shape_;
            rs[ax] = M.rows;
            RecursiveTensor nxt = cur.derive(rs, storage_, code, {}, "");
            cur.mode_product_into(M, ax, nxt, true);
            cur = std::move(nxt);
        }
        // Rebuild provenance as a single step from *this*.
        RecursiveTensor r = derive(cur.shape_, storage_, code, std::move(args), prefix);
        if (is_sparse()) r.sparse_ = std::move(cur.sparse_); else r.dense_ = std::move(cur.dense_);
        return r;
    }

    T evaluate_reference(const RecursiveReference& ref) const {
        const T src = get_linear(ref.source);
        auto p = [&](std::size_t i, double def) { return i < ref.params.size() ? ref.params[i] : def; };
        switch (ref.type) {
            case RefType::Direct:
                return scalar_cast<T>(scalar_cast<W>(src) * p(0, 1.0));
            case RefType::Transform:
                return scalar_cast<T>(scalar_cast<W>(src) * p(0, 1.0) + W(p(1, 0.0)));
            case RefType::Fractal: {
                W z = scalar_cast<W>(get_linear(ref.target));
                const W c = scalar_cast<W>(src) * p(0, 1.0);
                const double escape = p(1, 2.0);
                for (int i = 0; i < ref.max_iterations; ++i) {
                    const W nz = z * z + c;
                    const double d = std::abs(nz - z);
                    z = nz;
                    if (std::abs(z) > escape || d < ref.convergence_threshold) break;
                }
                return scalar_cast<T>(z);
            }
        }
        return src;
    }

    void initialize(std::mt19937_64& rng) {
        const double vol = static_cast<double>(volume_);
        switch (distribution_) {
            case Distribution::Normal: {
                storage_ = Storage::Sparse;
                const auto count = static_cast<Extent>(vol * (1.0 - sparsity_));
                if (volume_ == 0 || count == 0) break;
                std::normal_distribution<double> nd(0.0, 1.0 / std::sqrt(vol));
                std::vector<std::uniform_int_distribution<Extent>> ax;
                for (Extent e : shape_) ax.emplace_back(0, e - 1);
                sparse_.reserve(static_cast<std::size_t>(count));
                for (Extent c = 0; c < count; ++c) {
                    const double v = nd(rng);
                    Extent lin = 0;
                    for (std::size_t a = 0; a < rank(); ++a) lin = lin * shape_[a] + ax[a](rng);
                    if (std::abs(v) > 1e-6) sparse_[lin] = scalar_cast<T>(v);  // collisions overwrite (dict)
                }
                break;
            }
            case Distribution::Uniform: {
                storage_ = Storage::Dense;
                std::uniform_real_distribution<double> ud(-0.01, 0.01);
                dense_.resize(volume_);
                for (auto& v : dense_) v = scalar_cast<T>(ud(rng));
                break;
            }
            case Distribution::PowerLaw: {
                storage_ = Storage::Dense;
                std::uniform_real_distribution<double> ud(0.0, 1.0);
                dense_.resize(volume_);
                for (auto& v : dense_) {
                    const double base = std::pow(ud(rng), 1.0 / 2.5) * 0.1;  // numpy.random.power(2.5)
                    v = scalar_cast<T>(ud(rng) < 0.5 ? -base : base);
                }
                break;
            }
            case Distribution::ComplexGaussian: {
                if constexpr (!is_complex_v<T>) {
                    throw DTypeError("complex_gaussian distribution requires a complex dtype");
                } else {
                    storage_ = Storage::Dense;
                    std::normal_distribution<double> nd(0.0, 1.0 / std::sqrt(2.0 * vol));
                    dense_.resize(volume_);
                    for (auto& v : dense_) v = T(static_cast<real_type>(nd(rng)), static_cast<real_type>(nd(rng)));
                }
                break;
            }
            case Distribution::Orthogonal: {
                storage_ = Storage::Dense;
                dense_.assign(volume_, T(0));
                if (rank() >= 2) {
                    const std::size_t n0 = static_cast<std::size_t>(shape_[0]);
                    if (shape_[1] < shape_[0])
                        throw ShapeError("orthogonal init requires shape[1] >= shape[0] (Python IndexError path)");
                    std::normal_distribution<double> nd(0.0, 1.0);
                    Matrix<W> Q(n0, n0);
                    for (auto& v : Q.a) v = W(nd(rng));
                    orthonormalize(Q);
                    const auto st = strides_of(shape_);
                    for (std::size_t i = 0; i < n0; ++i)
                        for (std::size_t j = 0; j < n0; ++j) dense_[i * st[0] + j * st[1]] = scalar_cast<T>(Q(i, j));
                } else {
                    std::normal_distribution<double> nd(0.0, 1.0 / std::sqrt(std::max(vol, 1.0)));
                    for (auto& v : dense_) v = scalar_cast<T>(nd(rng));
                }
                break;
            }
            case Distribution::Empty:
            case Distribution::Explicit:
                storage_ = Storage::Dense;
                dense_.assign(volume_, T(0));
                sparsity_ = 1.0;
                break;
        }
    }

    // ------------------------------------------------------------ eigen engine
    EigenResult<T> solve_eigen(const Axes& rows, const Axes& cols, std::size_t k, double thr, const EigenOptions& opt) const {
        Extent nr = 1, nc = 1;
        for (auto a : rows) nr *= shape_[a];
        for (auto a : cols) nc *= shape_[a];
        const std::size_t R = static_cast<std::size_t>(nr), Cn = static_cast<std::size_t>(nc);
        EigenResult<T> out;
        Shape vshape;
        for (auto a : cols) vshape.push_back(shape_[a]);
        if (vshape.empty()) vshape.push_back(nc);  // rank-1 case: vectors of length n_cols
        detail::Splitter sp(shape_, rows, cols);

        auto finish = [&](const Matrix<W>& vecs, const std::vector<double>& vals, std::size_t keff) {
            Shape s{static_cast<Extent>(keff)};
            s.insert(s.end(), vshape.begin(), vshape.end());
            std::vector<T> data(keff * vecs.rows);
            for (std::size_t j = 0; j < keff; ++j)
                for (std::size_t i = 0; i < vecs.rows; ++i) data[j * vecs.rows + i] = scalar_cast<T>(vecs(i, j));
            auto vt = std::make_shared<RecursiveTensor>(from_dense(s, std::move(data)));
            vt->meta_.description = detail::cap_description("Eigenstates of " + meta_.description);
            out.vectors = vt;
            out.values.assign(vals.begin(), vals.begin() + static_cast<long>(keff));
        };

        if (R != Cn) {  // rectangular -> SVD
            Matrix<W> A(R, Cn);
            for_each_stored([&](Extent lin, const T& v) { auto [r, c] = sp(lin); A(r, c) = scalar_cast<W>(v); });
            auto s = svd_jacobi(A);
            const std::size_t keff = std::min(k, s.S.size());
            out.method = EigenResult<T>::Method::JacobiSvd;
            out.converged = s.converged;
            finish(s.V, s.S, keff);
            return out;
        }

        const std::size_t n = R;
        if (n == 0) { out.converged = true; finish(Matrix<W>(0, 0), {}, 0); return out; }
        const std::size_t keff = std::min(k, n);
        if (n <= opt.dense_limit) {
            Matrix<W> A(n, n);
            for_each_stored([&](Extent lin, const T& v) { auto [r, c] = sp(lin); A(r, c) = scalar_cast<W>(v); });
            // Hermitian part (numpy.allclose(A, A^H) default tolerances decide).
            bool herm = true;
            for (std::size_t i = 0; i < n && herm; ++i)
                for (std::size_t j = 0; j < n; ++j) {
                    const W d = A(i, j) - conj_of(A(j, i));
                    if (std::abs(d) > 1e-8 + 1e-5 * std::abs(A(j, i))) { herm = false; break; }
                }
            Matrix<W> H(n, n);
            for (std::size_t i = 0; i < n; ++i)
                for (std::size_t j = 0; j < n; ++j) H(i, j) = (A(i, j) + conj_of(A(j, i))) * 0.5;
            out.symmetrized = !herm;
            auto e = eigh_jacobi(H);
            std::vector<std::size_t> order(n);
            std::iota(order.begin(), order.end(), 0);
            std::stable_sort(order.begin(), order.end(), [&](std::size_t a, std::size_t b) { return std::abs(e.values[a]) > std::abs(e.values[b]); });
            Matrix<W> V(n, keff);
            std::vector<double> vals(keff);
            for (std::size_t j = 0; j < keff; ++j) {
                vals[j] = e.values[order[j]];
                for (std::size_t i = 0; i < n; ++i) V(i, j) = e.vectors(i, order[j]);
            }
            // Eigenrecursion verification: Rayleigh quotient against the solved
            // (Hermitian) operator; one inverse-iteration step on mismatch.
            for (std::size_t j = 0; j < keff; ++j) {
                std::vector<W> v(n), Hv(n, W(0));
                for (std::size_t i = 0; i < n; ++i) v[i] = V(i, j);
                for (std::size_t i = 0; i < n; ++i) for (std::size_t c = 0; c < n; ++c) Hv[i] += H(i, c) * v[c];
                W num(0); double den = 0;
                for (std::size_t i = 0; i < n; ++i) { num += conj_of(v[i]) * Hv[i]; den += std::norm(std::complex<double>(real_part(v[i]), imag_part(v[i]))); }
                const double rq = real_part(num) / (den > 0 ? den : 1.0);
                if (std::abs(rq - vals[j]) > thr) {
                    Matrix<W> S = H;
                    for (std::size_t i = 0; i < n; ++i) S(i, i) -= W(vals[j]);
                    auto sol = lu_solve(S, v);
                    if (sol) {
                        double nn = 0;
                        for (auto& x : *sol) nn += std::norm(std::complex<double>(real_part(x), imag_part(x)));
                        nn = std::sqrt(nn);
                        if (nn > 0) {
                            for (std::size_t i = 0; i < n; ++i) V(i, j) = (*sol)[i] / nn;
                            std::vector<W> Hw(n, W(0));
                            for (std::size_t i = 0; i < n; ++i) for (std::size_t c = 0; c < n; ++c) Hw[i] += H(i, c) * V(c, j);
                            W q(0);
                            for (std::size_t i = 0; i < n; ++i) q += conj_of(V(i, j)) * Hw[i];
                            vals[j] = real_part(q);
                            ++out.refined;
                        }
                    }
                }
            }
            out.method = EigenResult<T>::Method::JacobiEigh;
            out.converged = e.converged;
            finish(V, vals, keff);
            return out;
        }

        // Large operator: subspace iteration on the Hermitian part, matrix-free.
        std::vector<std::tuple<std::size_t, std::size_t, W>> trip;
        trip.reserve(stored_count());
        for_each_stored([&](Extent lin, const T& v) { if (v != T(0)) { auto [r, c] = sp(lin); trip.emplace_back(r, c, scalar_cast<W>(v)); } });
        std::function<Matrix<W>(const Matrix<W>&)> apply = [&](const Matrix<W>& X) {
            Matrix<W> Y(n, X.cols);
            for (const auto& [r, c, v] : trip) {
                const W half = v * 0.5, halfc = conj_of(v) * 0.5;
                for (std::size_t j = 0; j < X.cols; ++j) {
                    Y(r, j) += half * X(c, j);
                    Y(c, j) += halfc * X(r, j);
                }
            }
            return Y;
        };
        auto s = eigs_subspace<W>(n, apply, keff, std::max(thr, 1e-12), opt.max_iter, opt.seed);
        out.method = EigenResult<T>::Method::SubspaceIteration;
        out.converged = s.converged;
        out.symmetrized = true;
        finish(s.vectors, s.values, keff);
        return out;
    }
};

// scalar * tensor
template <class T> RecursiveTensor<T> operator*(const T& s, const RecursiveTensor<T>& t) { return t * s; }

template <class T>
RecursiveTensor<T> TuckerResult<T>::reconstruct() const {
    RecursiveTensor<T> x = core->to_dense();
    for (std::size_t mode = 0; mode < factors.size(); ++mode) x = x.mode_product_raw(factors[mode], mode);
    return x;
}

}  // namespace rta
