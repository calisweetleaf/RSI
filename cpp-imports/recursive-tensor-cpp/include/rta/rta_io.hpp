// rta/rta_io.hpp — .rta binary serialization (RTNZ v2.0).
//
// Layout (all integers little-endian; see docs/RTA_FORMAT.md):
//   [128-byte header]  magic "RTNZ", version 2.0, dtype, storage, rank, volume,
//                      nnz, sparsity, uuid, timestamps, op count, header CRC32
//   [sections]         each 64-byte aligned: 32-byte section header
//                      (tag, flags, payload_bytes, element_count, crc32)
//                      then payload (32-byte aligned), zero padded to 64.
//   Sections: SHAP (required, first) · DENS | SIDX+SVAL · REFS · HIST · META · END
//
// Readers skip unknown non-critical sections (forward compatible) and reject
// unknown critical ones. Every section payload is CRC32-checked.
// Writes are atomic (temp file + rename).
#pragma once

#include <algorithm>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <variant>

#include "recursive_tensor.hpp"

namespace rta::io {

inline constexpr std::uint16_t kMajor = 2;
inline constexpr std::uint16_t kMinor = 0;
inline constexpr std::uint32_t kHeaderBytes = 128;
inline constexpr std::uint32_t kSectionHeaderBytes = 32;
inline constexpr std::size_t kSectionAlign = 64;

enum FileFlags : std::uint32_t { kFlagSparse = 1u, kFlagRefs = 2u, kFlagHistory = 4u, kFlagMeta = 8u };
enum SectionFlags : std::uint32_t { kSectionCritical = 1u };

constexpr std::uint32_t fourcc(const char (&s)[5]) {
    return static_cast<std::uint32_t>(static_cast<unsigned char>(s[0])) |
           (static_cast<std::uint32_t>(static_cast<unsigned char>(s[1])) << 8) |
           (static_cast<std::uint32_t>(static_cast<unsigned char>(s[2])) << 16) |
           (static_cast<std::uint32_t>(static_cast<unsigned char>(s[3])) << 24);
}
inline constexpr std::uint32_t kTagShape = fourcc("SHAP");
inline constexpr std::uint32_t kTagDense = fourcc("DENS");
inline constexpr std::uint32_t kTagSparseIdx = fourcc("SIDX");
inline constexpr std::uint32_t kTagSparseVal = fourcc("SVAL");
inline constexpr std::uint32_t kTagRefs = fourcc("REFS");
inline constexpr std::uint32_t kTagHistory = fourcc("HIST");
inline constexpr std::uint32_t kTagMeta = fourcc("META");
inline constexpr std::uint32_t kTagEnd = fourcc("END ");

inline std::string tag_str(std::uint32_t t) {
    std::string s(4, ' ');
    for (int i = 0; i < 4; ++i) s[static_cast<std::size_t>(i)] = static_cast<char>((t >> (8 * i)) & 0xFF);
    return s;
}

// ------------------------------------------------------------ CRC32 (IEEE)
inline std::uint32_t crc32_update(std::uint32_t crc, const std::uint8_t* p, std::size_t n) {
    static const auto table = [] {
        std::array<std::uint32_t, 256> t{};
        for (std::uint32_t i = 0; i < 256; ++i) {
            std::uint32_t c = i;
            for (int k = 0; k < 8; ++k) c = (c & 1u) ? 0xEDB88320u ^ (c >> 1) : c >> 1;
            t[i] = c;
        }
        return t;
    }();
    crc = ~crc;
    for (std::size_t i = 0; i < n; ++i) crc = table[(crc ^ p[i]) & 0xFFu] ^ (crc >> 8);
    return ~crc;
}
inline std::uint32_t crc32(const std::uint8_t* p, std::size_t n) { return crc32_update(0, p, n); }

inline bool host_little_endian() {
    const std::uint16_t x = 1;
    std::uint8_t b;
    std::memcpy(&b, &x, 1);
    return b == 1;
}

// ------------------------------------------------------------ byte buffers
struct ByteWriter {
    std::vector<std::uint8_t> b;
    template <class I> void put_int(I v) {
        using U = std::make_unsigned_t<I>;
        U u = static_cast<U>(v);
        for (std::size_t i = 0; i < sizeof(I); ++i) b.push_back(static_cast<std::uint8_t>((u >> (8 * i)) & 0xFFu));
    }
    void put_f64(double d) { std::uint64_t u; std::memcpy(&u, &d, 8); put_int(u); }
    void put_bytes(const void* p, std::size_t n) { auto c = static_cast<const std::uint8_t*>(p); b.insert(b.end(), c, c + n); }
    void put_str(const std::string& s) { put_int(static_cast<std::uint32_t>(s.size())); put_bytes(s.data(), s.size()); }
    void pad_to(std::size_t align) { while (b.size() % align) b.push_back(0); }
};

struct ByteReader {
    const std::uint8_t* p;
    std::size_t n, pos = 0;
    std::string where;
    ByteReader(const std::uint8_t* d, std::size_t len, std::string w) : p(d), n(len), where(std::move(w)) {}
    void need(std::size_t k) const {
        if (k > n - pos) throw FormatError(where + ": truncated (need " + std::to_string(k) + " bytes at " + std::to_string(pos) + ")");
    }
    template <class I> I get_int() {
        need(sizeof(I));
        using U = std::make_unsigned_t<I>;
        U u = 0;
        for (std::size_t i = 0; i < sizeof(I); ++i) u |= static_cast<U>(static_cast<U>(p[pos + i]) << (8 * i));
        pos += sizeof(I);
        return static_cast<I>(u);
    }
    double get_f64() { auto u = get_int<std::uint64_t>(); double d; std::memcpy(&d, &u, 8); return d; }
    std::string get_str() {
        auto len = get_int<std::uint32_t>();
        need(len);
        std::string s(reinterpret_cast<const char*>(p + pos), len);
        pos += len;
        return s;
    }
    void get_bytes(void* dst, std::size_t k) { need(k); if (k) std::memcpy(dst, p + pos, k); pos += k; }
    void align(std::size_t a) { const std::size_t np = (pos + a - 1) / a * a; need(np - pos); pos = np; }
};

// Scalars to/from little-endian bytes (component-wise for complex).
template <class T>
void append_values_le(std::vector<std::uint8_t>& out, const T* v, std::size_t count) {
    const std::size_t sz = sizeof(T);
    const std::size_t start = out.size();
    out.resize(start + count * sz);
    if (count == 0) return;
    std::memcpy(out.data() + start, v, count * sz);
    if (!host_little_endian()) {
        const std::size_t comp = sizeof(real_t<T>);
        for (std::size_t off = start; off < out.size(); off += comp) std::reverse(out.begin() + static_cast<long>(off), out.begin() + static_cast<long>(off + comp));
    }
}
template <class T>
std::vector<T> read_values_le(const std::uint8_t* p, std::size_t count) {
    std::vector<T> v(count);
    if (count) std::memcpy(v.data(), p, count * sizeof(T));
    if (!host_little_endian()) {
        auto* b = reinterpret_cast<std::uint8_t*>(v.data());
        const std::size_t comp = sizeof(real_t<T>);
        for (std::size_t off = 0; off < count * sizeof(T); off += comp) std::reverse(b + off, b + off + comp);
    }
    return v;
}

// ------------------------------------------------------------ inspection
struct SectionInfo {
    std::uint32_t tag = 0;
    std::uint32_t flags = 0;
    std::uint64_t offset = 0;         // file offset of the section header
    std::uint64_t payload_bytes = 0;
    std::uint64_t element_count = 0;
    std::uint32_t crc = 0;
    bool crc_ok = false;
};
struct HeaderInfo {
    std::uint16_t major = 0, minor = 0;
    std::uint32_t header_bytes = 0, flags = 0;
    DType dtype = DType::F32;
    Storage storage = Storage::Dense;
    Distribution distribution = Distribution::Explicit;
    std::uint8_t index_encoding = 0;
    std::uint16_t rank = 0;
    std::uint64_t volume = 0, nnz = 0, section_count = 0, operations_count = 0;
    double sparsity = 0, created_at = 0, modified_at = 0;
    Uuid uuid{};
};
struct FileInfo {
    HeaderInfo header;
    std::vector<SectionInfo> sections;
    std::uint64_t file_bytes = 0;
};

namespace detail {

inline std::vector<std::uint8_t> read_file(const std::string& path) {
    std::ifstream f(path, std::ios::binary | std::ios::ate);
    if (!f) throw FormatError("cannot open " + path);
    const auto size = static_cast<std::size_t>(f.tellg());
    f.seekg(0);
    std::vector<std::uint8_t> buf(size);
    if (size && !f.read(reinterpret_cast<char*>(buf.data()), static_cast<std::streamsize>(size)))
        throw FormatError("short read on " + path);
    return buf;
}

inline HeaderInfo parse_header(const std::vector<std::uint8_t>& buf) {
    if (buf.size() < kHeaderBytes) throw FormatError("file shorter than the RTNZ header");
    if (std::memcmp(buf.data(), "RTNZ", 4) != 0) throw FormatError("bad magic (not an RTNZ/.rta file)");
    ByteReader r(buf.data(), buf.size(), "header");
    r.pos = 4;
    HeaderInfo h;
    h.major = r.get_int<std::uint16_t>();
    h.minor = r.get_int<std::uint16_t>();
    if (h.major != kMajor)
        throw FormatError("unsupported RTNZ major version " + std::to_string(h.major) + " (reader is " + std::to_string(kMajor) + ".x)");
    h.header_bytes = r.get_int<std::uint32_t>();
    if (h.header_bytes < kHeaderBytes || h.header_bytes % kSectionAlign) throw FormatError("invalid header size");
    const std::uint32_t stored_crc = [&] { ByteReader c(buf.data(), buf.size(), "header"); c.pos = 124; return c.get_int<std::uint32_t>(); }();
    if (crc32(buf.data(), 124) != stored_crc) throw FormatError("header CRC mismatch");
    h.flags = r.get_int<std::uint32_t>();
    const auto dt = r.get_int<std::uint8_t>();
    if (dt > 3) throw FormatError("unknown dtype code " + std::to_string(dt));
    h.dtype = static_cast<DType>(dt);
    const auto st = r.get_int<std::uint8_t>();
    if (st > 1) throw FormatError("unknown storage code");
    h.storage = static_cast<Storage>(st);
    const auto dist = r.get_int<std::uint8_t>();
    if (dist > 6) throw FormatError("unknown distribution code");
    h.distribution = static_cast<Distribution>(dist);
    h.index_encoding = r.get_int<std::uint8_t>();
    if (h.index_encoding != 0) throw FormatError("unsupported index encoding " + std::to_string(h.index_encoding));
    h.rank = r.get_int<std::uint16_t>();
    (void)r.get_int<std::uint16_t>();
    h.volume = r.get_int<std::uint64_t>();
    h.nnz = r.get_int<std::uint64_t>();
    h.sparsity = r.get_f64();
    r.get_bytes(h.uuid.bytes.data(), 16);
    h.created_at = r.get_f64();
    h.modified_at = r.get_f64();
    h.operations_count = r.get_int<std::uint64_t>();
    h.section_count = r.get_int<std::uint64_t>();
    if (((h.flags & kFlagSparse) != 0) != (h.storage == Storage::Sparse)) throw FormatError("sparse flag disagrees with storage code");
    return h;
}

// Walk sections; returns (info, payload pointer) pairs. Verifies CRCs and bounds.
inline std::vector<std::pair<SectionInfo, const std::uint8_t*>> walk_sections(const std::vector<std::uint8_t>& buf, const HeaderInfo& h,
                                                                              bool throw_on_crc = true) {
    std::vector<std::pair<SectionInfo, const std::uint8_t*>> out;
    std::size_t pos = h.header_bytes;
    bool ended = false;
    while (!ended) {
        if (pos + kSectionHeaderBytes > buf.size()) throw FormatError("missing END section (truncated file)");
        ByteReader r(buf.data(), buf.size(), "section@" + std::to_string(pos));
        r.pos = pos;
        SectionInfo s;
        s.offset = pos;
        s.tag = r.get_int<std::uint32_t>();
        s.flags = r.get_int<std::uint32_t>();
        s.payload_bytes = r.get_int<std::uint64_t>();
        s.element_count = r.get_int<std::uint64_t>();
        s.crc = r.get_int<std::uint32_t>();
        (void)r.get_int<std::uint32_t>();
        const std::size_t pstart = pos + kSectionHeaderBytes;
        if (s.payload_bytes > buf.size() - pstart) throw FormatError("section " + tag_str(s.tag) + " overruns file");
        s.crc_ok = crc32(buf.data() + pstart, static_cast<std::size_t>(s.payload_bytes)) == s.crc;
        if (!s.crc_ok && throw_on_crc) throw FormatError("section " + tag_str(s.tag) + " CRC mismatch");
        out.emplace_back(s, buf.data() + pstart);
        if (s.tag == kTagEnd) ended = true;
        const std::size_t end = pstart + static_cast<std::size_t>(s.payload_bytes);
        pos = (end + kSectionAlign - 1) / kSectionAlign * kSectionAlign;
        // Inter-section padding is not CRC-covered, so it must be verified zero:
        // otherwise a flipped byte there would be silently accepted.
        if (!ended) {
            const std::size_t pad_end = std::min(pos, buf.size());
            for (std::size_t q = end; q < pad_end; ++q)
                if (buf[q] != 0) throw FormatError("non-zero padding after section " + tag_str(s.tag));
        }
        if (out.size() > 1u << 20) throw FormatError("too many sections");
    }
    return out;
}

class FileBuilder {
public:
    explicit FileBuilder(std::ostream& os) : os_(os) {}
    void begin(const std::vector<std::uint8_t>& header) { write(header.data(), header.size()); }
    void section(std::uint32_t tag, std::uint32_t flags, std::uint64_t count, const std::vector<std::uint8_t>& payload) {
        ByteWriter h;
        h.put_int(tag);
        h.put_int(flags);
        h.put_int(static_cast<std::uint64_t>(payload.size()));
        h.put_int(count);
        h.put_int(crc32(payload.data(), payload.size()));
        h.put_int(static_cast<std::uint32_t>(0));
        write(h.b.data(), h.b.size());
        write(payload.data(), payload.size());
        static const std::uint8_t zeros[kSectionAlign] = {};
        const std::size_t pad = (kSectionAlign - pos_ % kSectionAlign) % kSectionAlign;
        write(zeros, pad);
        ++sections_;
    }
    std::uint64_t sections() const { return sections_; }

private:
    void write(const std::uint8_t* p, std::size_t n) {
        os_.write(reinterpret_cast<const char*>(p), static_cast<std::streamsize>(n));
        if (!os_) throw FormatError("write failed");
        pos_ += n;
    }
    std::ostream& os_;
    std::size_t pos_ = 0;
    std::uint64_t sections_ = 0;
};

}  // namespace detail

// ------------------------------------------------------------ write
template <class T>
void write(const RecursiveTensor<T>& t, std::ostream& os) {
    const bool sparse = t.is_sparse();
    std::vector<std::pair<Extent, T>> cells;
    if (sparse) cells = t.sorted_cells();  // canonical order -> deterministic bytes
    const std::uint64_t nnz = sparse ? cells.size() : t.volume();
    std::uint32_t flags = sparse ? kFlagSparse : 0u;
    if (!t.references().empty()) flags |= kFlagRefs;
    if (!t.history().empty()) flags |= kFlagHistory;
    flags |= kFlagMeta;
    if (t.rank() > 0xFFFF) throw FormatError("rank exceeds format limit 65535");

    const std::uint64_t n_sections = 2 + (sparse ? 2 : 1) + (t.references().empty() ? 0 : 1) + (t.history().empty() ? 0 : 1);  // SHAP,data,[REFS],[HIST],META + END counted below
    ByteWriter h;
    h.put_bytes("RTNZ", 4);
    h.put_int(kMajor);
    h.put_int(kMinor);
    h.put_int(kHeaderBytes);
    h.put_int(flags);
    h.put_int(static_cast<std::uint8_t>(RecursiveTensor<T>::dtype()));
    h.put_int(static_cast<std::uint8_t>(t.storage()));
    h.put_int(static_cast<std::uint8_t>(t.distribution()));
    h.put_int(static_cast<std::uint8_t>(0));  // index encoding: sorted linear u64
    h.put_int(static_cast<std::uint16_t>(t.rank()));
    h.put_int(static_cast<std::uint16_t>(0));
    h.put_int(t.volume());
    h.put_int(nnz);
    h.put_f64(t.sparsity());
    h.put_bytes(t.uuid().bytes.data(), 16);
    h.put_f64(t.metadata().created_at);
    h.put_f64(t.metadata().modified_at);
    h.put_int(t.metadata().operations_count);
    h.put_int(n_sections + 1);
    while (h.b.size() < 124) h.b.push_back(0);
    h.put_int(crc32(h.b.data(), 124));

    detail::FileBuilder fb(os);
    fb.begin(h.b);

    ByteWriter shp;
    for (Extent e : t.shape()) shp.put_int(static_cast<std::uint64_t>(e));
    fb.section(kTagShape, kSectionCritical, t.rank(), shp.b);

    if (sparse) {
        ByteWriter idx;
        idx.b.reserve(cells.size() * 8);
        std::vector<T> vals;
        vals.reserve(cells.size());
        for (const auto& [k, v] : cells) { idx.put_int(static_cast<std::uint64_t>(k)); vals.push_back(v); }
        fb.section(kTagSparseIdx, kSectionCritical, cells.size(), idx.b);
        std::vector<std::uint8_t> vb;
        append_values_le(vb, vals.data(), vals.size());
        fb.section(kTagSparseVal, kSectionCritical, vals.size(), vb);
    } else {
        std::vector<std::uint8_t> vb;
        append_values_le(vb, t.dense_data().data(), t.dense_data().size());
        fb.section(kTagDense, kSectionCritical, t.volume(), vb);
    }

    if (!t.references().empty()) {
        ByteWriter rw;
        for (const auto& r : t.references()) {
            rw.put_int(static_cast<std::uint8_t>(r.type));
            rw.put_int(r.iteration_axis);
            rw.put_int(r.max_iterations);
            rw.put_int(static_cast<std::uint8_t>(0));
            rw.put_int(static_cast<std::uint32_t>(r.params.size()));
            rw.put_f64(r.convergence_threshold);
            rw.put_int(static_cast<std::uint64_t>(r.source));
            rw.put_int(static_cast<std::uint64_t>(r.target));
            for (double p : r.params) rw.put_f64(p);
        }
        fb.section(kTagRefs, kSectionCritical, t.references().size(), rw.b);
    }
    if (!t.history().empty()) {
        ByteWriter hw;
        for (const auto& op : t.history()) {
            hw.put_int(static_cast<std::uint16_t>(op.code));
            hw.put_int(static_cast<std::uint16_t>(0));
            hw.put_int(static_cast<std::uint32_t>(op.args.size()));
            hw.put_bytes(op.peer.bytes.data(), 16);
            hw.put_int(static_cast<std::uint32_t>(op.label.size()));
            hw.put_int(static_cast<std::uint32_t>(0));
            for (auto a : op.args) hw.put_int(static_cast<std::int64_t>(a));
            hw.put_bytes(op.label.data(), op.label.size());
            hw.pad_to(8);
        }
        fb.section(kTagHistory, 0, t.history().size(), hw.b);
    }
    ByteWriter mw;
    mw.put_str(t.metadata().description);
    mw.put_int(static_cast<std::uint32_t>(t.metadata().extra.size()));
    for (const auto& [k, v] : t.metadata().extra) { mw.put_str(k); mw.put_str(v); }
    fb.section(kTagMeta, 0, t.metadata().extra.size(), mw.b);
    fb.section(kTagEnd, kSectionCritical, 0, {});
}

// Atomic save: write <path>.tmp then rename over <path>.
template <class T>
void save(const RecursiveTensor<T>& t, const std::string& path) {
    namespace fs = std::filesystem;
    const fs::path p(path);
    if (p.has_parent_path()) fs::create_directories(p.parent_path());
    const std::string tmp = path + ".tmp";
    {
        std::ofstream f(tmp, std::ios::binary | std::ios::trunc);
        if (!f) throw FormatError("cannot open " + tmp + " for writing");
        write(t, f);
        f.flush();
        if (!f) throw FormatError("flush failed on " + tmp);
    }
    std::error_code ec;
    fs::rename(tmp, p, ec);
    if (ec) { fs::remove(tmp); throw FormatError("rename failed: " + ec.message()); }
}

// ------------------------------------------------------------ read
using AnyTensor = std::variant<RecursiveTensor<float>, RecursiveTensor<double>,
                               RecursiveTensor<std::complex<float>>, RecursiveTensor<std::complex<double>>>;

namespace detail {
template <class T>
RecursiveTensor<T> decode(const std::vector<std::uint8_t>& buf, const HeaderInfo& h) {
    typename RecursiveTensor<T>::Parts p;
    p.storage = h.storage;
    p.distribution = h.distribution;
    p.sparsity = h.sparsity;
    p.uuid = h.uuid;
    p.meta.created_at = h.created_at;
    p.meta.modified_at = h.modified_at;
    p.meta.operations_count = h.operations_count;
    bool have_shape = false, have_data = false, have_idx = false, have_val = false;
    for (const auto& [s, data] : walk_sections(buf, h)) {
        ByteReader r(data, static_cast<std::size_t>(s.payload_bytes), tag_str(s.tag));
        if (s.tag == kTagShape) {
            if (s.element_count != h.rank || s.payload_bytes != 8ull * h.rank) throw FormatError("SHAP size disagrees with rank");
            for (std::uint64_t i = 0; i < h.rank; ++i) p.shape.push_back(r.get_int<std::uint64_t>());
            if (volume_of(p.shape) != h.volume) throw FormatError("SHAP volume disagrees with header volume");
            have_shape = true;
        } else if (!have_shape && s.tag != kTagEnd) {
            throw FormatError("section " + tag_str(s.tag) + " precedes SHAP");
        } else if (s.tag == kTagDense) {
            if (h.storage != Storage::Dense) throw FormatError("DENS section in a sparse file");
            if (s.element_count != h.volume || s.payload_bytes != h.volume * sizeof(T)) throw FormatError("DENS size disagrees with volume/dtype");
            p.dense = read_values_le<T>(data, static_cast<std::size_t>(h.volume));
            have_data = true;
        } else if (s.tag == kTagSparseIdx) {
            if (h.storage != Storage::Sparse) throw FormatError("SIDX section in a dense file");
            if (s.element_count != h.nnz || s.payload_bytes != 8ull * h.nnz) throw FormatError("SIDX size disagrees with nnz");
            p.sparse_offsets.resize(static_cast<std::size_t>(h.nnz));
            for (auto& o : p.sparse_offsets) o = r.get_int<std::uint64_t>();
            for (std::size_t i = 0; i < p.sparse_offsets.size(); ++i) {
                if (p.sparse_offsets[i] >= h.volume) throw FormatError("SIDX offset out of range");
                if (i && p.sparse_offsets[i] <= p.sparse_offsets[i - 1]) throw FormatError("SIDX offsets not strictly ascending");
            }
            have_idx = true;
        } else if (s.tag == kTagSparseVal) {
            if (s.element_count != h.nnz || s.payload_bytes != h.nnz * sizeof(T)) throw FormatError("SVAL size disagrees with nnz/dtype");
            p.sparse_values = read_values_le<T>(data, static_cast<std::size_t>(h.nnz));
            have_val = true;
        } else if (s.tag == kTagRefs) {
            for (std::uint64_t i = 0; i < s.element_count; ++i) {
                RecursiveReference ref;
                const auto ty = r.get_int<std::uint8_t>();
                if (ty > 2) throw FormatError("unknown reference type");
                ref.type = static_cast<RefType>(ty);
                ref.iteration_axis = r.get_int<std::uint8_t>();
                ref.max_iterations = r.get_int<std::uint8_t>();
                (void)r.get_int<std::uint8_t>();
                const auto np = r.get_int<std::uint32_t>();
                ref.convergence_threshold = r.get_f64();
                ref.source = r.get_int<std::uint64_t>();
                ref.target = r.get_int<std::uint64_t>();
                r.need(8ull * np);
                for (std::uint32_t j = 0; j < np; ++j) ref.params.push_back(r.get_f64());
                p.references.push_back(std::move(ref));
            }
        } else if (s.tag == kTagHistory) {
            for (std::uint64_t i = 0; i < s.element_count; ++i) {
                OpRecord op;
                op.code = static_cast<OpCode>(r.get_int<std::uint16_t>());
                (void)r.get_int<std::uint16_t>();
                const auto na = r.get_int<std::uint32_t>();
                r.get_bytes(op.peer.bytes.data(), 16);
                const auto ll = r.get_int<std::uint32_t>();
                (void)r.get_int<std::uint32_t>();
                r.need(8ull * na);
                for (std::uint32_t j = 0; j < na; ++j) op.args.push_back(r.get_int<std::int64_t>());
                r.need(ll);
                op.label.assign(reinterpret_cast<const char*>(data + r.pos), ll);
                r.pos += ll;
                r.align(8);
                p.history.push_back(std::move(op));
            }
        } else if (s.tag == kTagMeta) {
            p.meta.description = r.get_str();
            const auto ne = r.get_int<std::uint32_t>();
            for (std::uint32_t j = 0; j < ne; ++j) { auto k = r.get_str(); p.meta.extra[k] = r.get_str(); }
        } else if (s.tag == kTagEnd) {
            // done
        } else if (s.flags & kSectionCritical) {
            throw FormatError("unknown critical section " + tag_str(s.tag));
        }
    }
    if (!have_shape) throw FormatError("missing SHAP section");
    if (h.storage == Storage::Dense && !have_data) throw FormatError("missing DENS section");
    if (h.storage == Storage::Sparse && !(have_idx && have_val)) throw FormatError("missing SIDX/SVAL section");
    return RecursiveTensor<T>::assemble(std::move(p));
}
}  // namespace detail

inline AnyTensor load_any(const std::string& path) {
    const auto buf = detail::read_file(path);
    const auto h = detail::parse_header(buf);
    switch (h.dtype) {
        case DType::F32: return detail::decode<float>(buf, h);
        case DType::F64: return detail::decode<double>(buf, h);
        case DType::C64: return detail::decode<std::complex<float>>(buf, h);
        case DType::C128: return detail::decode<std::complex<double>>(buf, h);
    }
    throw FormatError("unreachable dtype");
}

// Load as T. If the file's dtype differs: convert when allowed, else throw.
template <class T>
RecursiveTensor<T> load(const std::string& path, bool allow_convert = false) {
    AnyTensor any = load_any(path);
    return std::visit([&](auto&& t) -> RecursiveTensor<T> {
        using U = typename std::decay_t<decltype(t)>::value_type;
        if constexpr (std::is_same_v<U, T>) {
            return std::move(t);
        } else {
            if (!allow_convert)
                throw DTypeError(std::string("file dtype ") + dtype_name(dtype_of_v<U>) + " != requested " + dtype_name(dtype_of_v<T>));
            RecursiveTensor<T> r = t.template astype<T>();
            r.set_uuid(t.uuid());  // same logical tensor, different precision
            return r;
        }
    }, any);
}

// Header + section table without decoding payloads. CRC failures are reported, not thrown.
inline FileInfo inspect(const std::string& path) {
    const auto buf = detail::read_file(path);
    FileInfo fi;
    fi.file_bytes = buf.size();
    fi.header = detail::parse_header(buf);
    for (const auto& [s, d] : detail::walk_sections(buf, fi.header, false)) { (void)d; fi.sections.push_back(s); }
    return fi;
}

}  // namespace rta::io
