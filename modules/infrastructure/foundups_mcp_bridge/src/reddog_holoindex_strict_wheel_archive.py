"""Bounded raw ZIP dialect for the reviewed RedDog builder wheel."""

from __future__ import annotations

import binascii
from dataclasses import dataclass
import hashlib
import json
import stat
import struct
import zlib

from .reddog_holoindex_packaging_distribution_contract import (
    PACKAGING_DIST_INFO,
)


_EOCD = struct.Struct("<4s4H2LH")
_CENTRAL = struct.Struct("<4s6H3L5H2L")
_LOCAL = struct.Struct("<4s5H3L2H")
_EOCD_SIGNATURE = b"PK\x05\x06"
_CENTRAL_SIGNATURE = b"PK\x01\x02"
_LOCAL_SIGNATURE = b"PK\x03\x04"
_FORBIDDEN_SUFFIXES = (
    ".pyc", ".pyo", ".pyd", ".dll", ".exe", ".zip", ".egg-link", ".pth",
)
_FORBIDDEN_NAMES = {"direct_url.json", "sitecustomize.py", "usercustomize.py"}
_RESERVED_STEMS = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


class StrictWheelArchiveError(RuntimeError):
    """Stable fail-closed strict-wheel parser error."""


def _fail(code: str) -> None:
    raise StrictWheelArchiveError(code)


@dataclass(frozen=True)
class StrictWheelLimits:
    max_archive_bytes: int = 128 * 1024
    max_members: int = 128
    max_name_bytes: int = 512
    max_depth: int = 8
    max_member_bytes: int = 1024 * 1024
    max_expanded_bytes: int = 4 * 1024 * 1024
    max_compression_ratio: int = 64

    def validate(self) -> None:
        values = (
            self.max_archive_bytes, self.max_members, self.max_name_bytes,
            self.max_depth, self.max_member_bytes, self.max_expanded_bytes,
            self.max_compression_ratio,
        )
        ceilings = (128 * 1024, 128, 512, 8, 1024 * 1024, 4 * 1024 * 1024, 64)
        if any(type(value) is not int or value <= 0 for value in values):
            _fail("STRICT_WHEEL_LIMIT_INVALID")
        if any(value > ceiling for value, ceiling in zip(values, ceilings, strict=True)):
            _fail("STRICT_WHEEL_LIMIT_INVALID")


@dataclass(frozen=True)
class StrictWheelMember:
    path: str
    payload: bytes
    compressed_size: int
    crc32: int


@dataclass(frozen=True)
class StrictWheelArchive:
    members: tuple[StrictWheelMember, ...]
    central_directory_digest: str
    member_set_digest: str
    expanded_bytes: int
    compressed_bytes: int


@dataclass(frozen=True)
class _CentralRow:
    name: bytes
    version_needed: int
    flags: int
    method: int
    modified_time: int
    modified_date: int
    crc32: int
    compressed_size: int
    uncompressed_size: int
    local_offset: int


def parse_strict_wheel_archive(
    raw: bytes, *, limits: StrictWheelLimits = StrictWheelLimits(),
) -> StrictWheelArchive:
    """Parse one canonical non-ZIP64, deflate-only wheel byte image."""

    if type(limits) is not StrictWheelLimits:
        _fail("STRICT_WHEEL_LIMIT_INVALID")
    limits.validate()
    if type(raw) is not bytes or not raw or len(raw) > limits.max_archive_bytes:
        _fail("STRICT_WHEEL_ARCHIVE_SIZE_INVALID")
    eocd_offset, count, central_offset, central_size = _parse_eocd(raw, limits)
    rows, central_bytes = _parse_central(
        raw, count=count, offset=central_offset, size=central_size, limits=limits,
    )
    if central_offset + central_size != eocd_offset:
        _fail("STRICT_WHEEL_CENTRAL_BOUNDS_INVALID")
    _require_path_set(rows)
    members, local_end = _parse_local_members(raw, rows, limits)
    if local_end != central_offset:
        _fail("STRICT_WHEEL_LOCAL_LAYOUT_INVALID")
    expanded = sum(len(member.payload) for member in members)
    compressed = sum(member.compressed_size for member in members)
    identities = tuple(
        (member.path, len(member.payload), _digest(member.payload))
        for member in sorted(members, key=lambda item: item.path.casefold())
    )
    return StrictWheelArchive(
        members=members,
        central_directory_digest=_digest(central_bytes),
        member_set_digest=_digest(json.dumps(
            identities, separators=(",", ":"), ensure_ascii=True,
        ).encode("ascii")),
        expanded_bytes=expanded,
        compressed_bytes=compressed,
    )


def _parse_eocd(
    raw: bytes, limits: StrictWheelLimits,
) -> tuple[int, int, int, int]:
    if len(raw) < _EOCD.size:
        _fail("STRICT_WHEEL_EOCD_INVALID")
    offset = len(raw) - _EOCD.size
    values = _EOCD.unpack_from(raw, offset)
    signature, disk, start_disk, disk_count, count = values[:5]
    central_size, central_offset, comment_size = values[5:]
    if signature != _EOCD_SIGNATURE or comment_size != 0:
        _fail("STRICT_WHEEL_EOCD_INVALID")
    if disk != 0 or start_disk != 0 or disk_count != count:
        _fail("STRICT_WHEEL_MULTIDISK_REJECTED")
    if count <= 0 or count > limits.max_members or count == 0xFFFF:
        _fail("STRICT_WHEEL_MEMBER_COUNT_INVALID")
    if central_size == 0xFFFFFFFF or central_offset == 0xFFFFFFFF:
        _fail("STRICT_WHEEL_ZIP64_REJECTED")
    return offset, count, central_offset, central_size


def _parse_central(
    raw: bytes, *, count: int, offset: int, size: int, limits: StrictWheelLimits,
) -> tuple[tuple[_CentralRow, ...], bytes]:
    end = offset + size
    if offset <= 0 or size <= 0 or end > len(raw) - _EOCD.size:
        _fail("STRICT_WHEEL_CENTRAL_BOUNDS_INVALID")
    cursor, rows = offset, []
    for _index in range(count):
        if cursor + _CENTRAL.size > end:
            _fail("STRICT_WHEEL_CENTRAL_TRUNCATED")
        values = _CENTRAL.unpack_from(raw, cursor)
        row, consumed = _central_row(raw, cursor, end, values, limits)
        rows.append(row)
        cursor += consumed
    if cursor != end:
        _fail("STRICT_WHEEL_CENTRAL_LAYOUT_INVALID")
    return tuple(rows), raw[offset:end]


def _central_row(
    raw: bytes, cursor: int, end: int, values: tuple[object, ...],
    limits: StrictWheelLimits,
) -> tuple[_CentralRow, int]:
    if values[0] != _CENTRAL_SIGNATURE:
        _fail("STRICT_WHEEL_CENTRAL_SIGNATURE_INVALID")
    made, needed, flags, method, mtime, mdate = (int(value) for value in values[1:7])
    crc32, compressed, expanded = (int(value) for value in values[7:10])
    name_size, extra_size, comment_size, disk, internal = (
        int(value) for value in values[10:15]
    )
    external, local_offset = int(values[15]), int(values[16])
    consumed = _CENTRAL.size + name_size + extra_size + comment_size
    if cursor + consumed > end or extra_size or comment_size or disk or internal:
        _fail("STRICT_WHEEL_CENTRAL_METADATA_INVALID")
    if made != 0x0314 or needed != 20:
        _fail("STRICT_WHEEL_VERSION_INVALID")
    if flags != 0:
        _fail("STRICT_WHEEL_FLAGS_INVALID")
    if method != 8 or external & 0xFFFF or external >> 16 != (stat.S_IFREG | 0o644):
        _fail("STRICT_WHEEL_MEMBER_TYPE_INVALID")
    _require_sizes(compressed, expanded, limits)
    name = raw[cursor + _CENTRAL.size:cursor + _CENTRAL.size + name_size]
    _validate_name(name, limits)
    return _CentralRow(
        name, needed, flags, method, mtime, mdate, crc32, compressed, expanded,
        local_offset,
    ), consumed


def _require_sizes(compressed: int, expanded: int, limits: StrictWheelLimits) -> None:
    if compressed <= 0 or expanded < 0 or expanded > limits.max_member_bytes:
        _fail("STRICT_WHEEL_MEMBER_SIZE_INVALID")
    if expanded > compressed * limits.max_compression_ratio:
        _fail("STRICT_WHEEL_COMPRESSION_RATIO_INVALID")


def _validate_name(raw: bytes, limits: StrictWheelLimits) -> str:
    if not raw or len(raw) > limits.max_name_bytes:
        _fail("STRICT_WHEEL_PATH_INVALID")
    try:
        name = raw.decode("ascii")
    except UnicodeDecodeError:
        _fail("STRICT_WHEEL_PATH_INVALID")
    parts = name.split("/")
    if (
        name.startswith("/") or "\\" in name or ":" in name
        or len(parts) > limits.max_depth
        or any(part in {"", ".", ".."} for part in parts)
    ):
        _fail("STRICT_WHEEL_PATH_INVALID")
    for part in parts:
        if (
            part.endswith((".", " "))
            or part.split(".", 1)[0].upper() in _RESERVED_STEMS
            or any(character in '<>"|?*' for character in part)
        ):
            _fail("STRICT_WHEEL_PATH_INVALID")
        if any(ord(character) < 0x20 or ord(character) == 0x7F for character in part):
            _fail("STRICT_WHEEL_PATH_INVALID")
    lowered = name.casefold()
    if lowered.endswith(_FORBIDDEN_SUFFIXES) or parts[-1].casefold() in _FORBIDDEN_NAMES:
        _fail("STRICT_WHEEL_SOURCE_ONLY_REQUIRED")
    return name


def _require_distribution_path(name: str) -> None:
    if name.startswith("packaging/"):
        leaf = name.rsplit("/", 1)[-1]
        if not (leaf.endswith(".py") or leaf == "py.typed"):
            _fail("STRICT_WHEEL_DISTRIBUTION_SET_INVALID")
        return
    if name.startswith(f"{PACKAGING_DIST_INFO}/"):
        return
    _fail("STRICT_WHEEL_DISTRIBUTION_SET_INVALID")


def _require_path_set(rows: tuple[_CentralRow, ...]) -> None:
    names = tuple(row.name.decode("ascii") for row in rows)
    folded = tuple(name.casefold() for name in names)
    if len(folded) != len(set(folded)):
        _fail("STRICT_WHEEL_PATH_COLLISION")
    path_set = set(folded)
    for path in folded:
        parts = path.split("/")
        if any("/".join(parts[:index]) in path_set for index in range(1, len(parts))):
            _fail("STRICT_WHEEL_PATH_COLLISION")
    for name in names:
        _require_distribution_path(name)
    required = {
        "packaging/__init__.py", "packaging/version.py",
        f"{PACKAGING_DIST_INFO}/metadata".casefold(),
        f"{PACKAGING_DIST_INFO}/wheel".casefold(),
        f"{PACKAGING_DIST_INFO}/record".casefold(),
    }
    if not required <= path_set:
        _fail("STRICT_WHEEL_DISTRIBUTION_MEMBER_MISSING")


def _parse_local_members(
    raw: bytes, rows: tuple[_CentralRow, ...], limits: StrictWheelLimits,
) -> tuple[tuple[StrictWheelMember, ...], int]:
    cursor, expanded_total, members = 0, 0, []
    for row in rows:
        if row.local_offset != cursor or cursor + _LOCAL.size > len(raw):
            _fail("STRICT_WHEEL_LOCAL_LAYOUT_INVALID")
        values = _LOCAL.unpack_from(raw, cursor)
        payload, cursor = _local_payload(raw, cursor, row, values)
        expanded_total += len(payload)
        if expanded_total > limits.max_expanded_bytes:
            _fail("STRICT_WHEEL_EXPANDED_SIZE_INVALID")
        members.append(StrictWheelMember(
            row.name.decode("ascii"), payload, row.compressed_size, row.crc32,
        ))
    return tuple(members), cursor


def _local_payload(
    raw: bytes, cursor: int, row: _CentralRow, values: tuple[object, ...],
) -> tuple[bytes, int]:
    if values[0] != _LOCAL_SIGNATURE:
        _fail("STRICT_WHEEL_LOCAL_SIGNATURE_INVALID")
    expected = (
        row.version_needed, row.flags, row.method, row.modified_time,
        row.modified_date, row.crc32, row.compressed_size, row.uncompressed_size,
    )
    if tuple(int(value) for value in values[1:9]) != expected:
        _fail("STRICT_WHEEL_HEADER_MISMATCH")
    name_size, extra_size = int(values[9]), int(values[10])
    name_start = cursor + _LOCAL.size
    data_start = name_start + name_size + extra_size
    data_end = data_start + row.compressed_size
    if extra_size or raw[name_start:name_start + name_size] != row.name or data_end > len(raw):
        _fail("STRICT_WHEEL_HEADER_MISMATCH")
    payload = _inflate(raw[data_start:data_end], row.uncompressed_size)
    if (binascii.crc32(payload) & 0xFFFFFFFF) != row.crc32:
        _fail("STRICT_WHEEL_CRC_MISMATCH")
    return payload, data_end


def _inflate(compressed: bytes, expected_size: int) -> bytes:
    try:
        decoder = zlib.decompressobj(-zlib.MAX_WBITS)
        payload = decoder.decompress(compressed, expected_size + 1)
        if len(payload) > expected_size or decoder.unconsumed_tail:
            _fail("STRICT_WHEEL_DEFLATE_INVALID")
        tail = decoder.flush(max(expected_size + 1 - len(payload), 1))
    except zlib.error:
        _fail("STRICT_WHEEL_DEFLATE_INVALID")
    if (
        len(payload) + len(tail) != expected_size or not decoder.eof
        or decoder.unused_data or decoder.unconsumed_tail
    ):
        _fail("STRICT_WHEEL_DEFLATE_INVALID")
    return payload + tail


def _digest(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


__all__ = [
    "StrictWheelArchive",
    "StrictWheelArchiveError",
    "StrictWheelLimits",
    "StrictWheelMember",
    "parse_strict_wheel_archive",
]
