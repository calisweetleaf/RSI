cmake_minimum_required(VERSION 3.16)
project(rta VERSION 2.0.0 LANGUAGES CXX)

# Header-only library: consume with target_link_libraries(x PRIVATE rta::rta)
add_library(rta INTERFACE)
add_library(rta::rta ALIAS rta)
target_include_directories(rta INTERFACE
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>)
target_compile_features(rta INTERFACE cxx_std_17)
find_package(Threads REQUIRED)            # eigen cache uses std::mutex
target_link_libraries(rta INTERFACE Threads::Threads)

option(RTA_BUILD_TESTS "Build the self-test suite and parity runner" ON)
option(RTA_BUILD_TOOLS "Build rta_inspect" ON)
option(RTA_SANITIZE    "Build tests with ASan + UBSan" OFF)

set(RTA_WARN -Wall -Wextra -Wpedantic -Wshadow -Wconversion)

# Explicit instantiation of all four dtypes: catches template errors that only
# appear for a given T, and gives a precompiled object if you want one.
add_library(rta_instantiate OBJECT src/instantiate.cpp)
target_link_libraries(rta_instantiate PRIVATE rta::rta)
target_compile_options(rta_instantiate PRIVATE ${RTA_WARN})

if(RTA_BUILD_TOOLS)
    add_executable(rta_inspect tools/rta_inspect.cpp)
    target_link_libraries(rta_inspect PRIVATE rta::rta)
    target_compile_options(rta_inspect PRIVATE ${RTA_WARN})
    install(TARGETS rta_inspect RUNTIME DESTINATION bin)
endif()

if(RTA_BUILD_TESTS)
    enable_testing()
    add_executable(test_rta tests/test_rta.cpp)
    target_link_libraries(test_rta PRIVATE rta::rta)
    target_compile_options(test_rta PRIVATE ${RTA_WARN})
    if(RTA_SANITIZE)
        target_compile_options(test_rta PRIVATE -fsanitize=address,undefined -fno-sanitize-recover=all -g)
        target_link_options(test_rta PRIVATE -fsanitize=address,undefined)
    endif()
    add_test(NAME test_rta COMMAND test_rta)

    add_executable(parity_runner tests/parity/parity_runner.cpp)
    target_link_libraries(parity_runner PRIVATE rta::rta)
    target_compile_options(parity_runner PRIVATE ${RTA_WARN})

    # Parity needs the Python reference; point RTA_PY_REFERENCE at recursive_tensor.py.
    set(RTA_PY_REFERENCE "" CACHE FILEPATH "Path to the Python reference recursive_tensor.py")
    find_package(Python3 COMPONENTS Interpreter)
    if(RTA_PY_REFERENCE AND Python3_FOUND)
        add_test(NAME parity
                 COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/tests/parity/parity.py
                         ${RTA_PY_REFERENCE} $<TARGET_FILE:parity_runner>)
    endif()
endif()

include(GNUInstallDirs)
install(DIRECTORY include/rta DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
install(FILES python/rta_numpy.py DESTINATION ${CMAKE_INSTALL_DATADIR}/rta/python)
install(TARGETS rta EXPORT rtaTargets)
install(EXPORT rtaTargets NAMESPACE rta:: DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/rta)
include(CMakePackageConfigHelpers)
file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/rtaConfig.cmake
     "include(CMakeFindDependencyMacro)\nfind_dependency(Threads)\ninclude(\${CMAKE_CURRENT_LIST_DIR}/rtaTargets.cmake)\n")
write_basic_package_version_file(${CMAKE_CURRENT_BINARY_DIR}/rtaConfigVersion.cmake COMPATIBILITY SameMajorVersion)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/rtaConfig.cmake ${CMAKE_CURRENT_BINARY_DIR}/rtaConfigVersion.cmake
        DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/rta)
