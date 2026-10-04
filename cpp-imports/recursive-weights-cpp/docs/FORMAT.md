# Archive formats

The authoritative byte-level implementation is src/serialization.cpp, src/codec.hpp, and the system/layer serializers in src/runtime.cpp and src/layer.cpp.

All numeric fields are explicitly little-endian. Tensor payloads contain a uint32 rank, uint32 dimensions, and float32 elements. Readers validate bounds, shapes and finite values. Archives carry a trailing SHA-256 digest of the preceding bytes. SHA-256 detects corruption; it does not authenticate a producer.

- RWGT 1.3 reads the supplied Python's standalone weight format: JSON metadata, position and phase/error tensors, then recursive references. Its omissions cannot be recovered from a file.
- RWGT 1.4 adds a native extension preserving scale, delta parameters, configuration and flags. It is a new format extension, not a claim of existing Python reader compatibility.
- RWGS stores a complete native registry, codebook, configuration, keys, weight payloads and mutation history. Live cache/EMA state is not persisted.
- RWLY stores native layer projection, bias, normalization parameters and an embedded registry.
- The older 64-byte .rw header is metadata-only. Inspection does not reconstruct missing numerical tensors.

Memory-mapped files are parsed into owned runtime values. The disk layout is not a native C++ struct layout or zero-copy tensor ABI. Writers use temporary files and atomic replacement.
