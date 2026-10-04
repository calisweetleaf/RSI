# RTNZ v2.0 — the `.rta` binary format

Little-endian throughout. IEEE CRC-32 (zlib polynomial). Two independent
implementations exist and are cross-checked: `include/rta/rta_io.hpp` (C++)
and `python/rta_numpy.py` (NumPy).

## Layout

```
[ header 128 B ][ section ][ pad→64 ][ section ][ pad→64 ] ... [ END ]
```

Every section starts at a 64-byte-aligned file offset. Section header is 32 B,
so payloads start at offset ≡ 32 (mod 64). Padding bytes MUST be zero and are
verified on load (padding is not CRC-covered, so this is the only integrity
check it gets).

## Header (128 bytes)

| off | type   | field |
|-----|--------|-------|
| 0   | 4×u8   | magic `RTNZ` |
| 4   | u16    | major = 2 (readers reject other majors) |
| 6   | u16    | minor = 0 (additive changes only) |
| 8   | u32    | header_bytes = 128 (multiple of 64; bytes past 128 reserved) |
| 12  | u32    | flags: 1 sparse, 2 refs, 4 history, 8 meta |
| 16  | u8     | dtype: 0 f32, 1 f64, 2 c64, 3 c128 |
| 17  | u8     | storage: 0 dense, 1 sparse (must agree with flag bit 1) |
| 18  | u8     | distribution: 0 normal,1 uniform,2 power_law,3 complex_gaussian,4 orthogonal,5 empty,6 explicit |
| 19  | u8     | index_encoding: 0 = sorted linear u64 (only value defined) |
| 20  | u16    | rank |
| 22  | u16    | reserved 0 |
| 24  | u64    | volume (product of extents; rank-0 → 1) |
| 32  | u64    | nnz (sparse: stored cells; dense: volume) |
| 40  | f64    | sparsity |
| 48  | 16 B   | uuid (RFC 4122 v4) |
| 64  | f64    | created (unix seconds) |
| 72  | f64    | modified |
| 80  | u64    | operations_count |
| 88  | u64    | section_count (including END) |
| 96  | 28 B   | zero |
| 124 | u32    | CRC-32 of bytes 0..123 |

## Section header (32 bytes)

| off | type | field |
|-----|------|-------|
| 0  | u32 | tag (FourCC, LE) |
| 4  | u32 | flags: bit0 CRITICAL |
| 8  | u64 | payload_bytes |
| 16 | u64 | element_count |
| 24 | u32 | CRC-32 of payload |
| 28 | u32 | zero |

Unknown section + CRITICAL → reject. Unknown non-critical → skip.
This is the forward-compatibility contract.

## Sections

| tag | crit | payload |
|-----|------|---------|
| `SHAP` | yes | rank × u64 extents. Must come first. Volume must match header. |
| `DENS` | yes | volume × dtype, row-major. Complex = (re, im) pairs. |
| `SIDX` | yes | nnz × u64 row-major linear offsets, strictly ascending, < volume |
| `SVAL` | yes | nnz × dtype, aligned with SIDX |
| `REFS` | yes | recursive references (below) |
| `HIST` | no  | operation provenance (below) |
| `META` | no  | u32 len + utf8 description; u32 n; n × (u32 len + key, u32 len + value) |
| `END ` | yes | empty; terminates the file |

Sparse files are canonical: sorted offsets, so identical tensors serialize
to identical bytes (apart from uuid/timestamps).

### REFS record (variable, element_count records)
`u8 type (0 direct,1 transform,2 fractal) | u8 iteration_axis | u8 max_iterations | u8 0 | u32 nparams | f64 convergence_threshold | u64 source_offset | u64 target_offset | nparams × f64`

### HIST record (padded to 8)
`u16 opcode | u16 0 | u32 nargs | 16 B peer uuid | u32 label_len | u32 0 | nargs × i64 | label bytes | pad→8`

## Changes from the whitepaper's RTNZ v1

v1 stored rank-5 `uint16` index tuples. v2 stores `u64` linear offsets:
no rank cap, no 65535 per-axis cap, 8 B per cell instead of 10 B at rank 5,
and sorted order gives deterministic bytes and binary-searchable lookup.
