#include "codec.hpp"
#include <cctype>
#include <cerrno>
#include <climits>
#include <fcntl.h>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <openssl/sha.h>
#include <sstream>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
namespace rw::detail {
void Writer::checksum() {
    unsigned char digest[32];
    SHA256(data.data(), data.size(), digest);
    bytes(digest, 32);
}
void verify_checksum(const uint8_t *p, size_t n) {
    if (n < 32)
        throw FormatError("missing SHA-256 checksum");
    unsigned char digest[32];
    SHA256(p, n - 32, digest);
    unsigned diff = 0;
    for (size_t i = 0; i < 32; i++)
        diff |= digest[i] ^ p[n - 32 + i];
    if (diff)
        throw FormatError("SHA-256 checksum mismatch");
}
MappedFile::MappedFile(const std::string &path) {
    fd_ = open(path.c_str(), O_RDONLY | O_CLOEXEC);
    if (fd_ < 0)
        throw Error("cannot open file: " + path);
    struct stat st{};
    if (fstat(fd_, &st) || !S_ISREG(st.st_mode) || st.st_size <= 0 ||
        uint64_t(st.st_size) > (uint64_t(1) << 30)) {
        close(fd_);
        fd_ = -1;
        throw FormatError("file must be regular, nonempty, and at most 1 GiB");
    }
    size_ = size_t(st.st_size);
    auto p = mmap(nullptr, size_, PROT_READ, MAP_PRIVATE, fd_, 0);
    if (p == MAP_FAILED) {
        close(fd_);
        fd_ = -1;
        throw Error("memory mapping failed");
    }
    data_ = static_cast<const uint8_t *>(p);
}
MappedFile::~MappedFile() {
    if (data_)
        munmap(const_cast<uint8_t *>(data_), size_);
    if (fd_ >= 0)
        close(fd_);
}
void atomic_write(const std::string &path, const std::vector<uint8_t> &data) {
    std::string temp = path + ".tmp.XXXXXX";
    std::vector<char> name(temp.begin(), temp.end());
    name.push_back(0);
    int fd = mkstemp(name.data());
    if (fd < 0)
        throw Error("cannot create temporary output: " + path);
    try {
        size_t done = 0;
        while (done < data.size()) {
            ssize_t n = write(fd, data.data() + done, data.size() - done);
            if (n < 0 && errno == EINTR)
                continue;
            if (n <= 0)
                throw Error("file write failed");
            done += size_t(n);
        }
        if (fsync(fd))
            throw Error("fsync failed");
        if (close(fd)) {
            fd = -1;
            throw Error("close failed");
        }
        fd = -1;
        if (rename(name.data(), path.c_str()))
            throw Error("atomic rename failed");
    } catch (...) {
        if (fd >= 0)
            close(fd);
        unlink(name.data());
        throw;
    }
}
void write_config(Writer &w, const Config &c) {
    c.validate();
    w.u32(c.max_recursion_depth);
    w.u32(c.stability_check_interval);
    w.u32(c.cache_size);
    w.u32(c.thread_pool_size);
    for (double x : {c.convergence_threshold, c.spectral_radius_threshold, c.max_growth_ratio,
                     c.ema_momentum, c.max_effective_norm, c.damping_factor})
        w.f64(x);
    w.u32(c.power_iter_steps);
    w.u32(c.min_history_length);
    w.u8(c.enable_simd);
}
Config read_config(Reader &r) {
    Config c;
    c.max_recursion_depth = r.u32();
    c.stability_check_interval = r.u32();
    c.cache_size = r.u32();
    c.thread_pool_size = r.u32();
    c.convergence_threshold = r.f64();
    c.spectral_radius_threshold = r.f64();
    c.max_growth_ratio = r.f64();
    c.ema_momentum = r.f64();
    c.max_effective_norm = r.f64();
    c.damping_factor = r.f64();
    c.power_iter_steps = r.u32();
    c.min_history_length = r.u32();
    auto flag = r.u8();
    if (flag > 1)
        throw FormatError("invalid config boolean");
    c.enable_simd = flag;
    c.validate();
    return c;
}
} // namespace rw::detail
namespace rw {
namespace {
// Strict numeric metadata object used by original Python RWGT serializer.
std::map<std::string, uint32_t> metadata(const std::string &s) {
    size_t p = 0;
    auto ws = [&]() {
        while (p < s.size() && std::isspace(static_cast<unsigned char>(s[p])))
            p++;
    };
    auto expect = [&](char c) {
        ws();
        if (p >= s.size() || s[p++] != c)
            throw FormatError("invalid RWGT metadata JSON");
    };
    std::map<std::string, uint32_t> m;
    expect('{');
    ws();
    if (p < s.size() && s[p] == '}') {
        p++;
        return m;
    }
    while (true) {
        expect('"');
        std::string key;
        while (p < s.size() && s[p] != '"') {
            char c = s[p++];
            if (c == '\\' || static_cast<unsigned char>(c) < 32)
                throw FormatError("unsupported metadata key escape");
            key += c;
        }
        expect('"');
        expect(':');
        ws();
        size_t begin = p;
        uint64_t value = 0;
        while (p < s.size() && std::isdigit(static_cast<unsigned char>(s[p]))) {
            value = value * 10 + unsigned(s[p++] - '0');
            if (value > UINT32_MAX)
                throw FormatError("metadata integer overflow");
        }
        if (begin == p || !m.emplace(key, uint32_t(value)).second)
            throw FormatError("invalid/duplicate metadata field");
        ws();
        if (p < s.size() && s[p] == '}') {
            p++;
            break;
        }
        expect(',');
    }
    ws();
    if (p != s.size())
        throw FormatError("trailing metadata JSON");
    return m;
}
Position position(detail::Reader &r) {
    auto v = r.vector();
    if (v.size() != 5)
        throw FormatError("position is not 5D");
    Position p{};
    for (size_t i = 0; i < 5; i++) {
        double x = v[i];
        if (x != std::trunc(x) || x < INT32_MIN || x > INT32_MAX)
            throw FormatError("non-integral or out-of-range position");
        p[i] = int32_t(x);
    }
    return p;
}
void write_position(detail::Writer &w, const Position &p) {
    Vector v;
    for (auto x : p) {
        float f = float(x);
        if (double(f) != double(x))
            throw FormatError("RWGT float32 position cannot exactly encode this coordinate");
        v.push_back(f);
    }
    w.vector(v);
}
} // namespace
std::vector<uint8_t> RecursiveWeightSerializer::encode(const RecursiveWeight &w, bool legacy) {
    w.validate();
    if (legacy) {
        bool loss = w.scale_factor != 1 || w.delta.depth_scaling != 1 || w.flags != 0;
        for (float x : w.delta.base_delta)
            loss |= x != 0;
        for (float x : w.delta.adaptive_factor)
            loss |= x != 1;
        if (loss)
            throw FormatError("RWGT 1.3 would discard scale, delta, or flags; use 1.4");
    }
    detail::Writer out;
    out.magic("RWGT");
    out.u16(legacy ? 0x0103 : 0x0104);
    std::string json = "{\"base_codebook_index\": " + std::to_string(w.base_codebook_index) +
                       ", \"dimension_size\": " + std::to_string(w.dimension()) +
                       ", \"num_references\": " + std::to_string(w.recursive_refs.size()) + "}";
    out.string(json);
    write_position(out, w.tensor_position);
    out.vector(w.phase.base_phase);
    if (w.phase.scalar_amplitudes)
        out.vector(w.phase.harmonic_amplitudes.data);
    else
        out.matrix(w.phase.harmonic_amplitudes);
    out.vector(w.phase.frequencies);
    out.vector(w.phase.phase_offsets);
    out.vector(w.error_preservation);
    for (auto &r : w.recursive_refs) {
        out.f32(float(r.contribution_weight));
        out.u32(uint32_t(r.temporal_offset));
        write_position(out, r.relative_position);
        out.matrix(r.transformation_matrix);
    }
    if (!legacy) {
        out.magic("RWEX");
        out.f64(w.scale_factor);
        out.f64(w.delta.depth_scaling);
        out.vector(w.delta.base_delta);
        out.vector(w.delta.adaptive_factor);
        detail::write_config(out, w.config);
        out.u32(w.flags);
    }
    out.checksum();
    return out.data;
}
RecursiveWeight RecursiveWeightSerializer::decode(const uint8_t *p, size_t n) {
    detail::verify_checksum(p, n);
    detail::Reader r(p, n - 32);
    r.magic("RWGT");
    auto version = r.u16();
    if (version != 0x0103 && version != 0x0104)
        throw FormatError("unsupported RWGT version");
    auto m = metadata(r.string());
    for (auto k : {"base_codebook_index", "dimension_size", "num_references"})
        if (!m.count(k))
            throw FormatError("missing RWGT metadata field");
    size_t d = m.at("dimension_size"), refs = m.at("num_references");
    if (d == 0 || d > (1 << 20) || refs > 50)
        throw FormatError("invalid weight dimensions/count");
    auto w = RecursiveWeight::neutral(d, m.at("base_codebook_index"));
    w.tensor_position = position(r);
    w.phase.base_phase = r.vector();
    auto [shape, amplitudes] = r.tensor();
    if (shape.size() == 1) {
        w.phase.scalar_amplitudes = true;
        w.phase.harmonic_amplitudes = Matrix(shape[0], 1, std::move(amplitudes));
    } else if (shape.size() == 2)
        w.phase.harmonic_amplitudes = Matrix(shape[0], shape[1], std::move(amplitudes));
    else
        throw FormatError("amplitudes require rank 1 or 2");
    w.phase.frequencies = r.vector();
    w.phase.phase_offsets = r.vector();
    w.error_preservation = r.vector();
    if (w.dimension() != d)
        throw FormatError("metadata dimension differs from error vector");
    for (size_t i = 0; i < refs; i++) {
        RecursiveReference ref;
        ref.contribution_weight = r.f32();
        ref.temporal_offset = int32_t(r.u32());
        ref.relative_position = position(r);
        ref.transformation_matrix = r.matrix();
        w.recursive_refs.push_back(std::move(ref));
    }
    if (version == 0x0104) {
        r.magic("RWEX");
        w.scale_factor = r.f64();
        w.delta.depth_scaling = r.f64();
        w.delta.base_delta = r.vector();
        w.delta.adaptive_factor = r.vector();
        w.config = detail::read_config(r);
        w.flags = r.u32();
    }
    r.end();
    w.validate();
    return w;
}
void RecursiveWeightSerializer::serialize_weight(const RecursiveWeight &w, const std::string &p,
                                                 bool legacy) {
    detail::atomic_write(p, encode(w, legacy));
}
RecursiveWeight RecursiveWeightSerializer::deserialize_weight(const std::string &p) {
    detail::MappedFile f(p);
    return decode(f.data(), f.size());
}
LegacyWeightHeader read_legacy_header(const std::string &p) {
    detail::MappedFile f(p);
    if (f.size() != 64)
        throw FormatError("legacy Python header must be exactly 64 bytes");
    detail::Reader r(f.data(), f.size());
    LegacyWeightHeader h;
    h.weight_id = r.u32();
    h.reference_dimension = r.u32();
    h.recursion_depth = r.u32();
    h.self_reference_strength = r.f32();
    h.evolution_codebook_id = r.u32();
    h.num_references = r.u32();
    h.flags = r.u32();
    h.base_pattern_index = r.u32();
    h.reference_table_index = r.u32();
    h.phase_data_index = r.u32();
    h.error_term_index = r.u32();
    for (auto &x : h.tensor_position)
        x = int32_t(r.u32());
    r.end();
    return h;
}
} // namespace rw
