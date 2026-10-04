// Explicit instantiation of every supported dtype: forces the compiler to
// type-check the entire template surface, not just what tests happen to call.
#include "rta/rta.hpp"
template class rta::RecursiveTensor<float>;
template class rta::RecursiveTensor<double>;
template class rta::RecursiveTensor<std::complex<float>>;
template class rta::RecursiveTensor<std::complex<double>>;
template void rta::io::save(const rta::RecursiveTensor<float>&, const std::string&);
template void rta::io::save(const rta::RecursiveTensor<double>&, const std::string&);
template void rta::io::save(const rta::RecursiveTensor<std::complex<float>>&, const std::string&);
template void rta::io::save(const rta::RecursiveTensor<std::complex<double>>&, const std::string&);
template rta::RecursiveTensor<float> rta::io::load<float>(const std::string&, bool);
template rta::RecursiveTensor<std::complex<double>> rta::io::load<std::complex<double>>(const std::string&, bool);
