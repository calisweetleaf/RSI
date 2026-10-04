CXX ?= g++
CPPFLAGS += -Iinclude
CXXFLAGS ?= -O2 -g
CXXFLAGS += -std=c++17 -Wall -Wextra -Wpedantic -pthread -fPIC
LDLIBS += -Wl,-l:liblapack.so.3 -Wl,-l:libblas.so.3 -lcrypto -pthread
SOURCES := $(wildcard src/*.cpp)
OBJECTS := $(patsubst src/%.cpp,build/%.o,$(filter-out src/main.cpp,$(SOURCES)))
.PHONY: all test clean sanitize
all: build/librw.a build/librw.so build/rw
build:
	mkdir -p build
build/%.o: src/%.cpp include/rw/runtime.hpp src/codec.hpp | build
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c $< -o $@
build/librw.a: $(OBJECTS)
	ar rcs $@ $^
build/librw.so: $(OBJECTS)
	$(CXX) -shared $(CXXFLAGS) $^ $(LDLIBS) -o $@
build/rw: src/main.cpp build/librw.a
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $< build/librw.a $(LDLIBS) -o $@
build/tests: tests/test_runtime.cpp build/librw.a
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $< build/librw.a $(LDLIBS) -o $@
test: build/tests
	./build/tests
sanitize:
	$(MAKE) clean
	$(MAKE) CXXFLAGS='-O1 -g -std=c++17 -Wall -Wextra -pthread -fPIC -fsanitize=address,undefined -fno-omit-frame-pointer' test
clean:
	rm -rf build
