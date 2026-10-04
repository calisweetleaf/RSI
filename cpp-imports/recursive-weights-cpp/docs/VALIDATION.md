# Delivery status

This archive is a reviewable implementation checkpoint, not a claim that every proposed capability in the papers is complete or that all departures from the Python have been approved.

Earlier runs in this session passed 161 native assertions and 240 independent NumPy comparisons across dimensions 1, 3, 8, and 17. The differential run reported maximum absolute error 5.960464477539063e-08 and four legacy interoperability cases. The reference is an independent NumPy transcription, not execution of the original PyTorch module. PyTorch was unavailable.

Native coverage includes recursive/self/cyclic references, depth/time-sensitive caching, phase and delta evaluation, serialization and corrupt/truncated input rejection, mutations, evolution, concurrent reads, patterns, layer Jacobians against finite differences, and callback-based eigenrecursive state updates.

ASan/UBSan, CMake builds, GPU execution, and full end-to-end training have not been verified. A sanitizer target is supplied, but its presence is not a successful test result.

Read SEMANTICS.md before treating this as a faithful port: it records deliberate repairs and inferred algorithm choices. In particular, FP64 spectral workspaces, conventional annealing acceptance, and explicit temporal-coherence operations are implementation choices requiring author review. The user has challenged floating-point assumptions. No numerical representation change has been made in response pending alignment on the intended execution model.

The originals are preserved byte-for-byte in provenance/. SOURCE_SHA256.txt records their hashes.
