#pragma once
#include "rw/runtime.hpp"
#include <cmath>
#include <cstring>
#include <limits>
namespace rw::detail {
struct Writer {
    std::vector<uint8_t> data;
    void u8(uint8_t x) {
        data.push_back(x);
    }
    void u16(uint16_t x) {
        u8(x & 255);
        u8(x >> 8);
    }
    void u32(uint32_t x) {
        for (int i = 0; i < 4; i++)
            u8(uint8_t(x >> (8 * i)));
    }
    void u64(uint64_t x) {
        for (int i = 0; i < 8; i++)
            u8(uint8_t(x >> (8 * i)));
    }
    void f32(float f) {
        uint32_t v;
        std::memcpy(&v, &f, 4);
        u32(v);
    }
    void f64(double f) {
        uint64_t v;
        std::memcpy(&v, &f, 8);
        u64(v);
    }
    void bytes(const uint8_t *p, size_t n) {
        if (n)
            data.insert(data.end(), p, p + n);
    }
    void magic(const char *s) {
        bytes(reinterpret_cast<const uint8_t *>(s), 4);
    }
    void string(const std::string &s) {
        if (s.size() > UINT32_MAX)
            throw FormatError("string too large");
        u32(uint32_t(s.size()));
        bytes(reinterpret_cast<const uint8_t *>(s.data()), s.size());
    }
    void tensor(const std::vector<uint32_t> &shape, const Vector &v) {
        u32(uint32_t(shape.size()));
        for (auto d : shape)
            u32(d);
        for (float x : v)
            f32(x);
    }
    void vector(const Vector &v) {
        tensor({uint32_t(v.size())}, v);
    }
    void matrix(const Matrix &m) {
        tensor({uint32_t(m.rows), uint32_t(m.cols)}, m.data);
    }
    void checksum();
};
struct Reader {
    const uint8_t *data;
    size_t size, pos = 0;
    Reader(const uint8_t *p, size_t n) : data(p), size(n) {}
    void need(size_t n) const {
        if (n > size - pos)
            throw FormatError("truncated binary payload");
    }
    uint8_t u8() {
        need(1);
        return data[pos++];
    }
    uint16_t u16() {
        uint16_t a = u8(), b = u8();
        return uint16_t(a | (b << 8));
    }
    uint32_t u32() {
        uint32_t v = 0;
        for (int i = 0; i < 4; i++)
            v |= uint32_t(u8()) << (i * 8);
        return v;
    }
    uint64_t u64() {
        uint64_t v = 0;
        for (int i = 0; i < 8; i++)
            v |= uint64_t(u8()) << (i * 8);
        return v;
    }
    float f32() {
        uint32_t v = u32();
        float f;
        std::memcpy(&f, &v, 4);
        if (!std::isfinite(f))
            throw FormatError("nonfinite binary float");
        return f;
    }
    double f64() {
        uint64_t v = u64();
        double f;
        std::memcpy(&f, &v, 8);
        if (!std::isfinite(f))
            throw FormatError("nonfinite binary double");
        return f;
    }
    void magic(const char *s) {
        need(4);
        if (std::memcmp(data + pos, s, 4))
            throw FormatError("invalid binary magic");
        pos += 4;
    }
    std::string string(size_t max = 10000) {
        auto n = u32();
        if (n > max)
            throw FormatError("string length exceeds limit");
        need(n);
        std::string s(reinterpret_cast<const char *>(data + pos), n);
        pos += n;
        return s;
    }
    std::pair<std::vector<uint32_t>, Vector> tensor() {
        uint32_t rank = u32();
        if (rank == 0 || rank > 8)
            throw FormatError("invalid tensor rank");
        std::vector<uint32_t> shape;
        size_t count = 1;
        for (uint32_t i = 0; i < rank; i++) {
            auto d = u32();
            if (d && count > size_t(1 << 28) / d)
                throw FormatError("tensor size exceeds limit");
            count *= d;
            shape.push_back(d);
        }
        if (count > (size - pos) / 4)
            throw FormatError("tensor length exceeds remaining payload");
        Vector v(count);
        for (auto &x : v)
            x = f32();
        return {shape, v};
    }
    Vector vector() {
        auto [s, v] = tensor();
        if (s.size() != 1)
            throw FormatError("expected vector");
        return v;
    }
    Matrix matrix() {
        auto [s, v] = tensor();
        if (s.size() != 2)
            throw FormatError("expected matrix");
        return Matrix(s[0], s[1], std::move(v));
    }
    void end() const {
        if (pos != size)
            throw FormatError("unexpected trailing bytes");
    }
};
class MappedFile {
    int fd_ = -1;
    const uint8_t *data_ = nullptr;
    size_t size_ = 0;

  public:
    explicit MappedFile(const std::string &);
    ~MappedFile();
    MappedFile(const MappedFile &) = delete;
    MappedFile &operator=(const MappedFile &) = delete;
    const uint8_t *data() const {
        return data_;
    }
    size_t size() const {
        return size_;
    }
};
void verify_checksum(const uint8_t *, size_t);
void atomic_write(const std::string &, const std::vector<uint8_t> &);
void write_config(Writer &, const Config &);
Config read_config(Reader &);
} // namespace rw::detail
