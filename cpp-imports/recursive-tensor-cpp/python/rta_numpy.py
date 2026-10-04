"""rta_numpy -- independent NumPy reader/writer for the RTNZ v2.0 (.rta) format.

Written from docs/RTA_FORMAT.md, not from the C++ source, so that the two
implementations cross-check each other. Zero dependencies beyond NumPy.

    arr = rta_numpy.load("x.rta")            # dense ndarray (sparse is densified)
    shape, lin, vals = rta_numpy.load_sparse("x.rta")
    rta_numpy.save("y.rta", arr)             # dense
    rta_numpy.save_sparse("z.rta", shape, lin_offsets, values)

Reads every section kind; REFS and HIST are parsed only to the extent of
being skipped safely (the Python side is a payload feeder, not a runtime).
"""
from __future__ import annotations

import os
import struct
import time
import uuid as _uuid
import zlib

import numpy as np

MAGIC = b"RTNZ"
MAJOR, MINOR = 2, 0
HEADER_BYTES = 128
SECTION_HEADER_BYTES = 32
ALIGN = 64
CRITICAL = 1

FLAG_SPARSE, FLAG_REFS, FLAG_HISTORY, FLAG_META = 1, 2, 4, 8
DTYPES = {0: np.dtype("<f4"), 1: np.dtype("<f8"), 2: np.dtype("<c8"), 3: np.dtype("<c16")}
DTYPE_CODE = {np.dtype(np.float32): 0, np.dtype(np.float64): 1,
              np.dtype(np.complex64): 2, np.dtype(np.complex128): 3}
TAG = {n: struct.unpack("<I", n.encode())[0] for n in ("SHAP", "DENS", "SIDX", "SVAL", "REFS", "HIST", "META", "END ")}
KNOWN = set(TAG.values())


class FormatError(ValueError):
    pass


def _crc(b: bytes) -> int:
    return zlib.crc32(b) & 0xFFFFFFFF  # IEEE 802.3, same polynomial as the C++ side


# ------------------------------------------------------------------ read
def _parse(path):
    buf = open(path, "rb").read()
    if len(buf) < HEADER_BYTES:
        raise FormatError("file shorter than header")
    if buf[:4] != MAGIC:
        raise FormatError("bad magic")
    (major, minor, hbytes, flags, dt, st, dist, enc, rank, _pad, volume, nnz, sparsity) = struct.unpack_from(
        "<HHIIBBBBHHQQd", buf, 4)
    if major != MAJOR:
        raise FormatError(f"unsupported major {major}")
    if struct.unpack_from("<I", buf, 124)[0] != _crc(buf[:124]):
        raise FormatError("header CRC mismatch")
    if dt not in DTYPES or st > 1 or enc != 0:
        raise FormatError("bad dtype/storage/encoding")
    if bool(flags & FLAG_SPARSE) != (st == 1):
        raise FormatError("sparse flag disagrees with storage")
    hdr = dict(major=major, minor=minor, flags=flags, dtype=DTYPES[dt], storage=st, distribution=dist,
               rank=rank, volume=volume, nnz=nnz, sparsity=sparsity,
               uuid=str(_uuid.UUID(bytes=bytes(buf[48:64]))))
    sections, pos = {}, hbytes
    while True:
        if pos + SECTION_HEADER_BYTES > len(buf):
            raise FormatError("missing END (truncated)")
        tag, sflags, pbytes, count, crc, _ = struct.unpack_from("<IIQQII", buf, pos)
        start = pos + SECTION_HEADER_BYTES
        if pbytes > len(buf) - start:
            raise FormatError("section overruns file")
        payload = buf[start:start + pbytes]
        if _crc(payload) != crc:
            raise FormatError(f"section {struct.pack('<I', tag)!r} CRC mismatch")
        if tag not in KNOWN and (sflags & CRITICAL):
            raise FormatError(f"unknown critical section {struct.pack('<I', tag)!r}")
        if tag in KNOWN:
            sections[tag] = (payload, count)
        if tag == TAG["END "]:
            break
        pos = (start + pbytes + ALIGN - 1) // ALIGN * ALIGN
    shape = tuple(int(x) for x in np.frombuffer(sections[TAG["SHAP"]][0], "<u8")) if rank else ()
    return hdr, shape, sections


def _meta(sections):
    if TAG["META"] not in sections:
        return "", {}
    p = sections[TAG["META"]][0]
    o = 0

    def s():
        nonlocal o
        n = struct.unpack_from("<I", p, o)[0]
        o += 4
        v = p[o:o + n].decode("utf-8")
        o += n
        return v

    desc = s()
    n = struct.unpack_from("<I", p, o)[0]
    o += 4
    extra = {}
    for _ in range(n):
        k = s()
        extra[k] = s()
    return desc, extra


def load_sparse(path):
    """-> (shape, sorted linear offsets uint64, values) regardless of storage."""
    hdr, shape, sec = _parse(path)
    dt = hdr["dtype"]
    if hdr["storage"] == 1:
        lin = np.frombuffer(sec[TAG["SIDX"]][0], "<u8").copy()
        vals = np.frombuffer(sec[TAG["SVAL"]][0], dt).copy()
    else:
        dense = np.frombuffer(sec[TAG["DENS"]][0], dt)
        lin = np.nonzero(dense)[0].astype(np.uint64)
        vals = dense[lin].copy()
    return shape, lin, vals.astype(dt.newbyteorder("="))


def load(path, with_info=False):
    hdr, shape, sec = _parse(path)
    dt = hdr["dtype"]
    vol = int(np.prod(shape)) if shape else 1
    if hdr["storage"] == 1:
        out = np.zeros(vol, dt.newbyteorder("="))
        lin = np.frombuffer(sec[TAG["SIDX"]][0], "<u8")
        out[lin.astype(np.int64)] = np.frombuffer(sec[TAG["SVAL"]][0], dt)
    else:
        out = np.frombuffer(sec[TAG["DENS"]][0], dt).astype(dt.newbyteorder("="))
    arr = out.reshape(shape)
    if with_info:
        desc, extra = _meta(sec)
        hdr.update(description=desc, extra=extra, sparse=hdr["storage"] == 1)
        return arr, hdr
    return arr


# ------------------------------------------------------------------ write
def _section(tag, payload, count, critical=True):
    head = struct.pack("<IIQQII", TAG[tag], CRITICAL if critical else 0, len(payload), count, _crc(payload), 0)
    return head + payload


def _write(path, shape, dtype, storage, nnz, body_sections, description="", extra=None, sparsity=0.0):
    dtype = np.dtype(dtype)
    if dtype not in DTYPE_CODE:
        raise FormatError(f"unsupported dtype {dtype}")
    extra = extra or {}
    meta = struct.pack("<I", len(description.encode())) + description.encode() + struct.pack("<I", len(extra))
    for k, v in extra.items():
        for s in (k, v):
            b = str(s).encode()
            meta += struct.pack("<I", len(b)) + b
    secs = [_section("SHAP", np.asarray(shape, "<u8").tobytes(), len(shape))] + body_sections
    secs += [_section("META", meta, len(extra), critical=False), _section("END ", b"", 0)]
    now = time.time()
    flags = (FLAG_SPARSE if storage else 0) | FLAG_META
    vol = int(np.prod(shape)) if len(shape) else 1
    h = MAGIC + struct.pack("<HHIIBBBBHHQQd", MAJOR, MINOR, HEADER_BYTES, flags, DTYPE_CODE[dtype], storage, 6, 0,
                            len(shape), 0, vol, nnz, float(sparsity))
    h += _uuid.uuid4().bytes + struct.pack("<ddQQ", now, now, 0, len(secs))
    h = h.ljust(124, b"\0")
    h += struct.pack("<I", _crc(h))
    out = bytearray(h)
    for s in secs:
        out += s
        out += b"\0" * ((-len(out)) % ALIGN)
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(out)
    os.replace(tmp, path)


def save(path, arr, description="", extra=None):
    arr = np.ascontiguousarray(arr)
    dt = arr.dtype.newbyteorder("<")
    _write(path, arr.shape, arr.dtype, 0, arr.size,
           [_section("DENS", arr.astype(dt).tobytes(), arr.size)], description, extra)


def save_sparse(path, shape, lin, values, description="", extra=None):
    lin = np.asarray(lin, np.uint64)
    values = np.asarray(values)
    order = np.argsort(lin, kind="stable")
    lin, values = lin[order], values[order]
    if len(lin) > 1 and np.any(np.diff(lin) == 0):
        raise FormatError("duplicate sparse offsets")
    dt = values.dtype.newbyteorder("<")
    vol = int(np.prod(shape)) if len(shape) else 1
    _write(path, tuple(shape), values.dtype, 1, len(lin),
           [_section("SIDX", lin.astype("<u8").tobytes(), len(lin)),
            _section("SVAL", values.astype(dt).tobytes(), len(values))],
           description, extra, sparsity=len(lin) / vol if vol else 0.0)
