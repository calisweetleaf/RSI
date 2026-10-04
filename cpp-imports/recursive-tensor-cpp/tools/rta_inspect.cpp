// rta_inspect -- print the structure of a .rta (RTNZ v2) file.
//
//   rta_inspect FILE [--values N] [--history]
//
// Exit status: 0 = file loads cleanly, 1 = structural/CRC problem, 2 = usage.
// Section listing is produced even when a CRC fails, so corrupt files can be
// diagnosed rather than just rejected.
#include "rta/rta.hpp"

#include <cstring>
#include <iomanip>
#include <iostream>

using namespace rta;

static const char* dist_name(Distribution d) {
    static const char* n[] = {"normal", "uniform", "power_law", "complex_gaussian", "orthogonal", "empty", "explicit"};
    const auto i = static_cast<std::size_t>(d);
    return i < 7 ? n[i] : "?";
}

template <class T>
static void dump(const RecursiveTensor<T>& t, std::size_t n, bool hist) {
    const auto& m = t.metadata();
    std::cout << "description  \"" << m.description << "\"\n";
    for (const auto& [k, v] : m.extra) std::cout << "  extra      " << k << " = " << v << "\n";
    if (!t.references().empty()) std::cout << "references   " << t.references().size() << "\n";
    if (hist) {
        std::cout << "history      " << t.history().size() << " records\n";
        for (const auto& op : t.history()) {
            std::cout << "  op " << std::setw(3) << static_cast<int>(op.code) << "  args[";
            for (std::size_t i = 0; i < op.args.size(); ++i) std::cout << (i ? "," : "") << op.args[i];
            std::cout << "]";
            if (!op.peer.is_nil()) std::cout << " peer=" << op.peer.str();
            if (!op.label.empty()) std::cout << " \"" << op.label << "\"";
            std::cout << "\n";
        }
    }
    if (n == 0) return;
    std::cout << "values (first " << n << " stored, linear offset: value)\n";
    std::size_t shown = 0;
    std::cout << std::setprecision(9);
    for (const auto& [lin, v] : t.sorted_cells()) {
        if (shown++ >= n) break;
        std::cout << "  " << std::setw(10) << lin << ": " << v << "\n";
    }
}

int main(int argc, char** argv) {
    if (argc < 2) { std::cerr << "usage: rta_inspect FILE [--values N] [--history]\n"; return 2; }
    std::size_t nvals = 0;
    bool hist = false;
    for (int i = 2; i < argc; ++i) {
        if (!std::strcmp(argv[i], "--values") && i + 1 < argc) nvals = std::stoul(argv[++i]);
        else if (!std::strcmp(argv[i], "--history")) hist = true;
        else { std::cerr << "unknown option " << argv[i] << "\n"; return 2; }
    }
    try {
        const auto fi = io::inspect(argv[1]);
        const auto& h = fi.header;
        std::cout << "file         " << argv[1] << "  (" << fi.file_bytes << " bytes)\n"
                  << "format       RTNZ " << h.major << "." << h.minor << "\n"
                  << "uuid         " << h.uuid.str() << "\n"
                  << "dtype        " << dtype_name(h.dtype) << "\n"
                  << "storage      " << (h.storage == Storage::Sparse ? "sparse" : "dense")
                  << "   distribution " << dist_name(h.distribution) << "\n"
                  << "rank         " << h.rank << "   volume " << h.volume << "   nnz " << h.nnz
                  << "   sparsity " << h.sparsity << "\n"
                  << "ops          " << h.operations_count << "\n"
                  << std::fixed << std::setprecision(3) << "created      " << h.created_at
                  << "   modified " << h.modified_at << "\n" << std::defaultfloat
                  << "sections     " << fi.sections.size() << " (header declares " << h.section_count << ")\n";
        bool crc_ok = true;
        for (const auto& s : fi.sections) {
            std::cout << "  " << io::tag_str(s.tag) << "  @" << std::setw(8) << s.offset << "  "
                      << std::setw(10) << s.payload_bytes << " B  n=" << std::setw(8) << s.element_count
                      << ((s.flags & 1u) ? "  critical" : "          ") << "  crc " << (s.crc_ok ? "ok" : "BAD") << "\n";
            crc_ok = crc_ok && s.crc_ok;
        }
        if (!crc_ok) { std::cout << "status       CORRUPT (section CRC failure)\n"; return 1; }
        std::visit([&](auto&& t) {
            std::cout << "shape        (";
            for (std::size_t i = 0; i < t.rank(); ++i) std::cout << (i ? ", " : "") << t.shape()[i];
            std::cout << ")\n";
            dump(t, nvals, hist);
        }, io::load_any(argv[1]));
        std::cout << "status       OK\n";
        return 0;
    } catch (const std::exception& e) {
        std::cout << "status       ERROR: " << e.what() << "\n";
        return 1;
    }
}
