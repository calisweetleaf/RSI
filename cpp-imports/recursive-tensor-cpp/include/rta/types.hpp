// rta/types.hpp — shapes, dtypes, index arithmetic, error types.
// Part of the RTA C++ core (port of recursive_tensor.py v2.1.0).
#pragma once

#include <array>
#include <chrono>
#include <complex>
#include <cstdint>
#include <cstring>
#include <limits>
#include <random>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <vector>

namespace rta {

using Extent = std::uint64_t;
using Shape = std::vector<Extent>;
using Index = std::vector<Extent>;
using Axes = std::vector<std::size_t>;

// ---------------------------------------------------------------- errors
struct Error : std::runtime_error { using std::runtime_error::runtime_error; };
struct ShapeError : Error { using Error::Error; };
struct IndexError : Error { using Error::Error; };
struct FormatError : Error { using Error::Error; };
struct DTypeError : Error { using Error::Error; };

// ---------------------------------------------------------------- dtypes
enum class DType : std::uint8_t { F32 = 0, F64 = 1, C64 = 2, C128 = 3 };

template <class T> struct is_complex : std::false_type {};
template <class U> struct is_complex<std::complex<U>> : std::true_type {};
template <class T> inline constexpr bool is_complex_v = is_complex<T>::value;

template <class T> struct real_of { using type = T; };
template <class U> struct real_of<std::complex<U>> { using type = U; };
template <class T> using real_t = typename real_of<T>::type;

// Work precision for linear algebra: always double (or complex<double>).
template <class T>
using work_t = std::conditional_t<is_complex_v<T>, std::complex<double>, double>;

template <class T> struct dtype_of;
template <> struct dtype_of<float> { static constexpr DType value = DType::F32; };
template <> struct dtype_of<double> { static constexpr DType value = DType::F64; };
template <> struct dtype_of<std::complex<float>> { static constexpr DType value = DType::C64; };
template <> struct dtype_of<std::complex<double>> { static constexpr DType value = DType::C128; };
template <class T> inline constexpr DType dtype_of_v = dtype_of<T>::value;

inline const char* dtype_name(DType d) {
    switch (d) {
        case DType::F32: return "float32";
        case DType::F64: return "float64";
        case DType::C64: return "complex64";
        case DType::C128: return "complex128";
    }
    return "unknown";
}
inline std::size_t dtype_size(DType d) {
    switch (d) {
        case DType::F32: return 4;
        case DType::F64: return 8;
        case DType::C64: return 8;
        case DType::C128: return 16;
    }
    throw DTypeError("unknown dtype code");
}

// Scalar helpers that work uniformly for real and complex T.
template <class T> inline double mag(const T& v) { return static_cast<double>(std::abs(v)); }
template <class T> inline T conj_of(const T& v) {
    if constexpr (is_complex_v<T>) return std::conj(v); else return v;
}
template <class T> inline double real_part(const T& v) {
    if constexpr (is_complex_v<T>) return static_cast<double>(v.real()); else return static_cast<double>(v);
}
template <class T> inline double imag_part(const T& v) {
    if constexpr (is_complex_v<T>) return static_cast<double>(v.imag()); else { (void)v; return 0.0; }
}
// Convert between any two supported scalar types (complex -> real drops imag).
template <class To, class From> inline To scalar_cast(const From& v) {
    if constexpr (is_complex_v<To>) {
        using R = real_t<To>;
        return To(static_cast<R>(real_part(v)), static_cast<R>(imag_part(v)));
    } else {
        return static_cast<To>(real_part(v));
    }
}

// ---------------------------------------------------------------- shapes
inline Extent checked_mul(Extent a, Extent b) {
    if (a != 0 && b > std::numeric_limits<Extent>::max() / a)
        throw ShapeError("shape volume overflows uint64");
    return a * b;
}

// Rank-0 tensors have volume 1 (a scalar). Any zero extent gives volume 0.
inline Extent volume_of(const Shape& s) {
    Extent v = 1;
    for (Extent e : s) v = checked_mul(v, e);
    return v;
}

inline std::vector<Extent> strides_of(const Shape& s) {
    std::vector<Extent> st(s.size(), 1);
    for (std::size_t i = s.size(); i-- > 1;) st[i - 1] = checked_mul(st[i], s[i] == 0 ? 1 : s[i]);
    return st;
}

inline std::string shape_str(const Shape& s) {
    std::string out = "(";
    for (std::size_t i = 0; i < s.size(); ++i) {
        out += std::to_string(s[i]);
        if (i + 1 < s.size() || s.size() == 1) out += ",";
        if (i + 1 < s.size()) out += " ";
    }
    return out + ")";
}

inline Extent linearize(const Index& idx, const Shape& shape) {
    if (idx.size() != shape.size())
        throw IndexError("index rank " + std::to_string(idx.size()) + " != tensor rank " +
                         std::to_string(shape.size()));
    Extent lin = 0;
    for (std::size_t a = 0; a < shape.size(); ++a) {
        if (idx[a] >= shape[a])
            throw IndexError("index " + std::to_string(idx[a]) + " out of bounds for axis " +
                             std::to_string(a) + " extent " + std::to_string(shape[a]));
        lin = lin * shape[a] + idx[a];
    }
    return lin;
}

inline Index delinearize(Extent lin, const Shape& shape) {
    Index idx(shape.size(), 0);
    for (std::size_t a = shape.size(); a-- > 0;) {
        idx[a] = lin % shape[a];
        lin /= shape[a];
    }
    return idx;
}

inline void validate_axes(const Axes& axes, std::size_t rank, const char* what) {
    std::vector<bool> seen(rank, false);
    for (std::size_t ax : axes) {
        if (ax >= rank)
            throw ShapeError(std::string(what) + ": axis " + std::to_string(ax) + " out of rank " +
                             std::to_string(rank));
        if (seen[ax]) throw ShapeError(std::string(what) + ": duplicate axis " + std::to_string(ax));
        seen[ax] = true;
    }
}

inline std::size_t normalize_axis(long long ax, std::size_t rank) {
    long long r = static_cast<long long>(rank);
    if (ax < 0) ax += r;
    if (ax < 0 || ax >= r)
        throw ShapeError("axis " + std::to_string(ax) + " out of rank " + std::to_string(rank));
    return static_cast<std::size_t>(ax);
}

// ---------------------------------------------------------------- uuid
struct Uuid {
    std::array<std::uint8_t, 16> bytes{};

    static Uuid generate() {
        std::random_device rd;
        Uuid u;
        for (std::size_t i = 0; i < 16; i += 4) {
            std::uint32_t r = rd();
            std::memcpy(&u.bytes[i], &r, 4);
        }
        u.bytes[6] = static_cast<std::uint8_t>((u.bytes[6] & 0x0F) | 0x40);  // version 4
        u.bytes[8] = static_cast<std::uint8_t>((u.bytes[8] & 0x3F) | 0x80);  // RFC 4122 variant
        return u;
    }
    bool is_nil() const {
        for (auto b : bytes) if (b) return false;
        return true;
    }
    std::string str() const {
        static const char* hex = "0123456789abcdef";
        std::string s;
        for (std::size_t i = 0; i < 16; ++i) {
            if (i == 4 || i == 6 || i == 8 || i == 10) s += '-';
            s += hex[bytes[i] >> 4];
            s += hex[bytes[i] & 0xF];
        }
        return s;
    }
    static Uuid parse(const std::string& s) {
        Uuid u;
        std::size_t bi = 0;
        auto nib = [](char c) -> int {
            if (c >= '0' && c <= '9') return c - '0';
            if (c >= 'a' && c <= 'f') return c - 'a' + 10;
            if (c >= 'A' && c <= 'F') return c - 'A' + 10;
            return -1;
        };
        for (std::size_t i = 0; i < s.size() && bi < 16;) {
            if (s[i] == '-') { ++i; continue; }
            if (i + 1 >= s.size()) break;
            int hi = nib(s[i]), lo = nib(s[i + 1]);
            if (hi < 0 || lo < 0) throw Error("invalid uuid string: " + s);
            u.bytes[bi++] = static_cast<std::uint8_t>((hi << 4) | lo);
            i += 2;
        }
        if (bi != 16) throw Error("invalid uuid string: " + s);
        return u;
    }
    bool operator==(const Uuid& o) const { return bytes == o.bytes; }
    bool operator!=(const Uuid& o) const { return !(*this == o); }
};

inline double unix_now() {
    using namespace std::chrono;
    return duration<double>(system_clock::now().time_since_epoch()).count();
}

}  // namespace rta
