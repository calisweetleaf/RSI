# rta — RecursiveTensor, C++17, header-only

Port of `recursive_tensor.py` v2.1.0 with the `.rta` (RTNZ v2) binary format.
No dependencies beyond the standard library and threads.

```cpp
#include <rta/rta.hpp>
rta::RecursiveTensor<double> t({8, 8, 4}, rta::Distribution::Normal, 0.2, /*seed*/7);
auto c = t.contract(t, {2}, {2});
rta::io::save(c, "c.rta");
auto u = rta::io::load<double>("c.rta");
```

Python side (payload feeder, NumPy only): `python/rta_numpy.py` — `save`, `save_sparse`, `load`, `load_sparse`.

## Build
```
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DRTA_PY_REFERENCE=/path/recursive_tensor.py
cmake --build build -j && (cd build && ctest --output-on-failure)
cmake --install build --prefix ~/.local     # then find_package(rta 2.0) → rta::rta
```
Without CMake: `g++ -std=c++17 -O2 -Iinclude your.cpp -pthread`.

Tools: `rta_inspect FILE [--values N] [--history]`.

Status at handoff: 334/334 self-tests (clean under ASan+UBSan), 28/28 parity,
zero warnings at -Wall -Wextra -Wpedantic -Wshadow -Wconversion.
See docs/RTA_FORMAT.md and docs/PORTING_LEDGER.md.
