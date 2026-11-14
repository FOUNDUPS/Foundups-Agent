"""Shared exact ``packaging==26.0`` METADATA/WHEEL/RECORD semantics."""

from __future__ import annotations

import base64
import csv
from dataclasses import dataclass
from email.parser import BytesParser
import hashlib
import io
import json
import re
from typing import Mapping


PACKAGING_DISTRIBUTION_NAME = "packaging"
PACKAGING_DISTRIBUTION_VERSION = "26.0"
PACKAGING_DIST_INFO = "packaging-26.0.dist-info"
PACKAGING_WHEEL_TAG = "py3-none-any"
_RECORD_SIZE = re.compile(r"(?:0|[1-9][0-9]*)\Z")


class PackagingDistributionContractError(RuntimeError):
    """Stable fail-closed distribution-contract error."""


def _fail(code: str) -> None:
    raise PackagingDistributionContractError(code)


@dataclass(frozen=True)
class PackagingDistributionProof:
    distribution_name: str
    distribution_version: str
    wheel_tag: str
    metadata_digest: str
    wheel_metadata_digest: str
    record_digest: str
    owned_files_digest: str
    owned_file_count: int
    owned_file_bytes: int
    record_ownership_verified: bool = True
    source_only_topology_verified: bool = True


def digest_bytes(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def validate_packaging_metadata(raw: bytes) -> None:
    """Require one exact normalized distribution name and version."""

    message = _headers(raw, "PACKAGING_DISTRIBUTION_METADATA_INVALID")
    if (
        message.get_all("Name", []) != [PACKAGING_DISTRIBUTION_NAME]
        or message.get_all("Version", []) != [PACKAGING_DISTRIBUTION_VERSION]
    ):
        _fail("PACKAGING_DISTRIBUTION_METADATA_INVALID")


def validate_packaging_wheel_metadata(raw: bytes) -> None:
    """Require the exact pure-Python wheel contract used by the builder."""

    message = _headers(raw, "PACKAGING_DISTRIBUTION_WHEEL_INVALID")
    expected = {
        "Wheel-Version": ["1.0"],
        "Root-Is-Purelib": ["true"],
        "Tag": [PACKAGING_WHEEL_TAG],
    }
    if any(message.get_all(name, []) != value for name, value in expected.items()):
        _fail("PACKAGING_DISTRIBUTION_WHEEL_INVALID")


def parse_packaging_record(
    raw: bytes, record_path: str,
) -> tuple[tuple[str, int, str], ...]:
    """Parse strict RECORD rows into path, size, and hex digest tuples."""

    try:
        text = raw.decode("utf-8")
        rows = tuple(csv.reader(io.StringIO(text, newline=""), strict=True))
    except (UnicodeDecodeError, csv.Error):
        _fail("PACKAGING_DISTRIBUTION_RECORD_INVALID")
    parsed = tuple(_parse_record_row(row, raw, record_path) for row in rows)
    if sum(row[0] == record_path for row in parsed) != 1:
        _fail("PACKAGING_DISTRIBUTION_RECORD_INVALID")
    paths = tuple(row[0] for row in parsed)
    if len(paths) != len(set(paths)) or len(paths) != len({path.casefold() for path in paths}):
        _fail("PACKAGING_DISTRIBUTION_RECORD_OWNERSHIP_INVALID")
    return parsed


def prove_packaging_distribution_members(
    members: Mapping[str, bytes],
) -> PackagingDistributionProof:
    """Cross-bind exact archive members to packaging metadata and RECORD."""

    if type(members) is not dict or not members:
        _fail("PACKAGING_DISTRIBUTION_MEMBERS_INVALID")
    metadata_path = f"{PACKAGING_DIST_INFO}/METADATA"
    wheel_path = f"{PACKAGING_DIST_INFO}/WHEEL"
    record_path = f"{PACKAGING_DIST_INFO}/RECORD"
    for required in (metadata_path, wheel_path, record_path):
        if required not in members or type(members[required]) is not bytes:
            _fail("PACKAGING_DISTRIBUTION_MEMBER_MISSING")
    validate_packaging_metadata(members[metadata_path])
    validate_packaging_wheel_metadata(members[wheel_path])
    record_rows = parse_packaging_record(members[record_path], record_path)
    _bind_record_members(members, record_rows, record_path)
    owned = tuple(
        (path, len(payload), digest_bytes(payload))
        for path, payload in sorted(members.items(), key=lambda row: row[0].casefold())
    )
    return PackagingDistributionProof(
        distribution_name=PACKAGING_DISTRIBUTION_NAME,
        distribution_version=PACKAGING_DISTRIBUTION_VERSION,
        wheel_tag=PACKAGING_WHEEL_TAG,
        metadata_digest=digest_bytes(members[metadata_path]),
        wheel_metadata_digest=digest_bytes(members[wheel_path]),
        record_digest=digest_bytes(members[record_path]),
        owned_files_digest=digest_bytes(_canonical_json_bytes(owned)),
        owned_file_count=len(owned),
        owned_file_bytes=sum(row[1] for row in owned),
    )


def _headers(raw: bytes, code: str):
    if type(raw) is not bytes or not raw or b"\x00" in raw:
        _fail(code)
    try:
        message = BytesParser().parsebytes(raw, headersonly=True)
    except Exception:
        _fail(code)
    if message.defects:
        _fail(code)
    return message


def _parse_record_row(
    row: list[str], raw: bytes, record_path: str,
) -> tuple[str, int, str]:
    if len(row) != 3 or not row[0]:
        _fail("PACKAGING_DISTRIBUTION_RECORD_INVALID")
    if row[0] == record_path:
        if row[1:] != ["", ""]:
            _fail("PACKAGING_DISTRIBUTION_RECORD_INVALID")
        return row[0], len(raw), digest_bytes(raw)
    if not row[1].startswith("sha256=") or _RECORD_SIZE.fullmatch(row[2]) is None:
        _fail("PACKAGING_DISTRIBUTION_RECORD_UNHASHED_MEMBER")
    return row[0], int(row[2]), _record_digest(row[1][7:])


def _record_digest(value: str) -> str:
    try:
        padded = (value + "=" * (-len(value) % 4)).encode("ascii")
        raw = base64.b64decode(padded, altchars=b"-_", validate=True)
    except (ValueError, TypeError, UnicodeError):
        _fail("PACKAGING_DISTRIBUTION_RECORD_INVALID")
    canonical = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    if len(raw) != 32 or canonical != value:
        _fail("PACKAGING_DISTRIBUTION_RECORD_INVALID")
    return "sha256:" + raw.hex()


def _bind_record_members(
    members: Mapping[str, bytes], rows: tuple[tuple[str, int, str], ...],
    record_path: str,
) -> None:
    by_path = {path: (size, digest) for path, size, digest in rows}
    if set(by_path) != set(members):
        _fail("PACKAGING_DISTRIBUTION_RECORD_OWNERSHIP_INVALID")
    for path, payload in members.items():
        expected = by_path[path]
        if path == record_path:
            continue
        if expected != (len(payload), digest_bytes(payload)):
            _fail("PACKAGING_DISTRIBUTION_RECORD_OWNERSHIP_INVALID")


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("ascii") + b"\n"


__all__ = [
    "PACKAGING_DIST_INFO",
    "PACKAGING_DISTRIBUTION_NAME",
    "PACKAGING_DISTRIBUTION_VERSION",
    "PACKAGING_WHEEL_TAG",
    "PackagingDistributionContractError",
    "PackagingDistributionProof",
    "parse_packaging_record",
    "prove_packaging_distribution_members",
    "validate_packaging_metadata",
    "validate_packaging_wheel_metadata",
]
