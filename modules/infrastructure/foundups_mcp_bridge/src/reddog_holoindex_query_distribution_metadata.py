"""Bounded wheel metadata and RECORD evidence for clean query candidates."""

from __future__ import annotations

import base64
import binascii
import csv
from dataclasses import dataclass
from email.parser import BytesParser
from email.policy import default as EMAIL_POLICY
import io
import re
import unicodedata
from typing import Any, Callable, Mapping

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version

from .reddog_holoindex_dependency_runtime_contract import digest_bytes
from .reddog_holoindex_runtime_abi_metadata import (
    RuntimeAbiMetadataError,
    _compatible_tag as compatible_windows_tag,
    _record_digest_matches as record_digest_matches,
    _record_path as canonical_record_path,
)


_NAME_PARTS = re.compile(r"[-_.]+")
_RESERVED = frozenset({
    "con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
})


class DistributionMetadataError(RuntimeError):
    """Stable fail-closed wheel-metadata or RECORD error."""


def _fail(code: str) -> None:
    raise DistributionMetadataError(code)


@dataclass(frozen=True)
class DistributionMetadataLimits:
    max_distributions: int
    max_record_rows: int
    max_total_record_rows: int
    max_metadata_bytes: int
    max_total_metadata_bytes: int


@dataclass(frozen=True)
class DistributionMetadata:
    name: str
    version: str
    dist_info: str
    metadata_path: str
    wheel_path: str
    record_path: str
    requirements: tuple[str, ...]
    provides_extras: tuple[str, ...]
    requires_python: str
    record_paths: tuple[str, ...]
    record_rows: tuple[Mapping[str, Any], ...]
    excluded_record_rows: tuple[Mapping[str, Any], ...]


@dataclass(frozen=True)
class DistributionCatalog:
    entries: Mapping[str, DistributionMetadata]
    owners_by_path: Mapping[str, tuple[str, ...]]


def build_distribution_catalog(
    inventory: Mapping[str, Mapping[str, Any]],
    read_bytes: Callable[[str], bytes],
    limits: DistributionMetadataLimits,
) -> DistributionCatalog:
    """Catalog broad dependency metadata and all local RECORD ownership claims."""

    metadata_paths = sorted(
        (row["path"] for row in inventory.values() if row["path"].endswith(".dist-info/METADATA")),
        key=str.casefold,
    )
    if not metadata_paths or len(metadata_paths) > limits.max_distributions:
        _fail("QUERY_DISTRIBUTION_CATALOG_INVALID")
    entries: dict[str, DistributionMetadata] = {}
    owners: dict[str, list[str]] = {}
    total_bytes = 0
    total_rows = 0
    for metadata_path in metadata_paths:
        entry, consumed_bytes, consumed_rows = _catalog_entry(
            metadata_path, inventory, read_bytes, limits,
        )
        total_bytes += consumed_bytes
        total_rows += consumed_rows
        if total_bytes > limits.max_total_metadata_bytes:
            _fail("QUERY_DISTRIBUTION_METADATA_LIMIT_EXCEEDED")
        if total_rows > limits.max_total_record_rows:
            _fail("QUERY_DISTRIBUTION_RECORD_LIMIT_EXCEEDED")
        if entry.name in entries:
            _fail("QUERY_DISTRIBUTION_NAME_AMBIGUOUS")
        entries[entry.name] = entry
        for path in entry.record_paths:
            owners.setdefault(path.casefold(), []).append(entry.name)
    return DistributionCatalog(
        entries,
        {path: tuple(sorted(names)) for path, names in owners.items()},
    )


def bind_selected_distribution_records(
    catalog: DistributionCatalog,
    selected: set[str],
    inventory: Mapping[str, Mapping[str, Any]],
    limits: DistributionMetadataLimits,
) -> DistributionCatalog:
    """Bind RECORD ownership only after the dependency closure is resolved."""

    if type(catalog) is not DistributionCatalog or not selected:
        _fail("QUERY_DISTRIBUTION_CATALOG_INVALID")
    entries = dict(catalog.entries)
    total_bytes = 0
    total_rows = 0
    for name in sorted(selected):
        entry = entries.get(name)
        if entry is None:
            _fail("QUERY_DISTRIBUTION_REQUIRED_MISSING")
        bound, consumed_bytes, consumed_rows = _bind_entry_record(entry, inventory, limits)
        total_bytes += consumed_bytes
        total_rows += consumed_rows
        if total_bytes > limits.max_total_metadata_bytes:
            _fail("QUERY_DISTRIBUTION_METADATA_LIMIT_EXCEEDED")
        if total_rows > limits.max_total_record_rows:
            _fail("QUERY_DISTRIBUTION_RECORD_LIMIT_EXCEEDED")
        entries[name] = bound
    return DistributionCatalog(entries, dict(catalog.owners_by_path))


def read_bound_payload(
    path: str,
    inventory: Mapping[str, Mapping[str, Any]],
    read_bytes: Callable[[str], bytes],
    maximum: int,
) -> bytes:
    """Read and rehash one already-normalized inventory member."""

    row = inventory.get(path.casefold())
    if row is None:
        _fail("QUERY_DISTRIBUTION_PAYLOAD_UNBOUND")
    if row["size"] > maximum:
        _fail("QUERY_DISTRIBUTION_PAYLOAD_LIMIT_EXCEEDED")
    try:
        payload = read_bytes(path)
    except Exception:
        _fail("QUERY_DISTRIBUTION_PAYLOAD_UNAVAILABLE")
    if type(payload) is not bytes:
        _fail("QUERY_DISTRIBUTION_PAYLOAD_INVALID")
    if len(payload) != row["size"]:
        _fail("QUERY_DISTRIBUTION_PAYLOAD_SIZE_MISMATCH")
    if digest_bytes(payload) != row["sha256"]:
        _fail("QUERY_DISTRIBUTION_PAYLOAD_DIGEST_MISMATCH")
    return payload


def validate_selected_wheel(
    entry: DistributionMetadata,
    inventory: Mapping[str, Mapping[str, Any]],
    read_bytes: Callable[[str], bytes],
    maximum: int,
) -> tuple[str, ...]:
    """Require one valid CPython-3.12/Windows or pure-Python wheel dialect."""

    payload = read_bound_payload(entry.wheel_path, inventory, read_bytes, maximum)
    try:
        message = BytesParser(policy=EMAIL_POLICY).parsebytes(payload)
        wheel_versions = message.get_all("Wheel-Version", [])
        purelib = message.get_all("Root-Is-Purelib", [])
        tags = tuple(sorted(set(map(str, message.get_all("Tag", [])))))
    except (UnicodeError, ValueError):
        _fail("QUERY_DISTRIBUTION_WHEEL_INVALID")
    if wheel_versions != ["1.0"] or len(purelib) != 1 or purelib[0] not in {"true", "false"}:
        _fail("QUERY_DISTRIBUTION_WHEEL_INVALID")
    if not tags or any(not _valid_wheel_tag(tag) for tag in tags):
        _fail("QUERY_DISTRIBUTION_WHEEL_INVALID")
    if not any(compatible_windows_tag(tag) for tag in tags):
        _fail("QUERY_DISTRIBUTION_WHEEL_INCOMPATIBLE")
    return tags


def target_python_satisfies(entry: DistributionMetadata, python_full_version: str) -> bool:
    """Evaluate the exact target interpreter against Requires-Python."""

    if not entry.requires_python:
        return True
    try:
        return Version(python_full_version) in SpecifierSet(entry.requires_python)
    except (InvalidSpecifier, InvalidVersion):
        _fail("QUERY_DISTRIBUTION_REQUIRES_PYTHON_INVALID")


def _catalog_entry(
    metadata_path: str,
    inventory: Mapping[str, Mapping[str, Any]],
    read_bytes: Callable[[str], bytes],
    limits: DistributionMetadataLimits,
) -> tuple[DistributionMetadata, int, int]:
    dist_info = metadata_path.removesuffix("/METADATA")
    wheel_path, record_path = f"{dist_info}/WHEEL", f"{dist_info}/RECORD"
    metadata = read_bound_payload(
        metadata_path, inventory, read_bytes, limits.max_metadata_bytes,
    )
    name, version, requirements, extras, requires_python = _parse_metadata(metadata)
    _validate_dist_info_identity(dist_info, name, version)
    if any(path.casefold() not in inventory for path in (wheel_path, record_path)):
        _fail("QUERY_DISTRIBUTION_METADATA_FILE_MISSING")
    record = read_bound_payload(
        record_path, inventory, read_bytes, limits.max_metadata_bytes,
    )
    rows, excluded = _record_rows(record, record_path, limits.max_record_rows)
    paths = tuple(row["path"] for row in rows)
    return DistributionMetadata(
        name, version, dist_info, metadata_path, wheel_path, record_path,
        requirements, extras, requires_python, paths, rows, excluded,
    ), len(metadata) + len(record), len(rows) + len(excluded)


def _bind_entry_record(
    entry: DistributionMetadata,
    inventory: Mapping[str, Mapping[str, Any]],
    limits: DistributionMetadataLimits,
) -> tuple[DistributionMetadata, int, int]:
    for row in entry.record_rows:
        bound = inventory.get(str(row["path"]).casefold())
        if bound is None:
            _fail("QUERY_DISTRIBUTION_RECORD_PATH_UNBOUND")
        if row["path"] == entry.record_path:
            if row["record_digest"] or row["record_size"]:
                _fail("QUERY_DISTRIBUTION_RECORD_BINDING_INVALID")
        elif not record_digest_matches(row["record_digest"], row["record_size"], bound):
            _fail("QUERY_DISTRIBUTION_RECORD_BINDING_INVALID")
    paths = entry.record_paths
    required = {
        entry.metadata_path.casefold(), entry.wheel_path.casefold(),
        entry.record_path.casefold(),
    }
    if not required <= {path.casefold() for path in paths}:
        _fail("QUERY_DISTRIBUTION_RECORD_METADATA_INCOMPLETE")
    installed = {
        row["path"].casefold() for row in inventory.values()
        if row["path"].casefold().startswith(entry.dist_info.casefold() + "/")
    }
    recorded = {
        path.casefold() for path in paths
        if path.casefold().startswith(entry.dist_info.casefold() + "/")
    }
    if installed != recorded:
        _fail("QUERY_DISTRIBUTION_RECORD_METADATA_INCOMPLETE")
    return entry, 0, len(paths) + len(entry.excluded_record_rows)


def _parse_metadata(
    payload: bytes,
) -> tuple[str, str, tuple[str, ...], tuple[str, ...], str]:
    try:
        message = BytesParser(policy=EMAIL_POLICY).parsebytes(payload)
        names, versions = message.get_all("Name", []), message.get_all("Version", [])
        python_values = message.get_all("Requires-Python", [])
        if len(names) != 1 or len(versions) != 1 or len(python_values) > 1:
            _fail("QUERY_DISTRIBUTION_METADATA_INVALID")
        name, version = normalize_distribution_name(str(names[0])), str(versions[0]).strip()
        Version(version)
        requirements = tuple(str(value).strip() for value in message.get_all("Requires-Dist", []))
        extras = tuple(sorted({normalize_distribution_name(str(value)) for value in message.get_all("Provides-Extra", [])}))
        requires_python = str(python_values[0]).strip() if python_values else ""
        if any(not value for value in requirements) or (python_values and not requires_python):
            _fail("QUERY_DISTRIBUTION_METADATA_INVALID")
        if requires_python:
            SpecifierSet(requires_python)
        return name, version, requirements, extras, requires_python
    except DistributionMetadataError:
        raise
    except (InvalidSpecifier, InvalidVersion, UnicodeError, ValueError):
        _fail("QUERY_DISTRIBUTION_METADATA_INVALID")


def _record_rows(
    payload: bytes,
    record_path: str,
    maximum_rows: int,
) -> tuple[tuple[Mapping[str, Any], ...], tuple[Mapping[str, Any], ...]]:
    result: list[Mapping[str, Any]] = []
    excluded: list[Mapping[str, Any]] = []
    seen: set[str] = set()
    try:
        rows = csv.reader(io.StringIO(payload.decode("utf-8"), newline=""), strict=True)
        for count, row in enumerate(rows, 1):
            if count > maximum_rows or len(row) != 3:
                _fail("QUERY_DISTRIBUTION_RECORD_INVALID")
            scope, path = _resolve_record_path(row[0])
            key = f"{scope}:{path.casefold()}"
            if key in seen:
                _fail("QUERY_DISTRIBUTION_RECORD_DUPLICATE_PATH")
            seen.add(key)
            if scope == "external_prefix":
                excluded.append(_external_record_row(path, row[1], row[2]))
                continue
            if path == record_path:
                if row[1] or row[2]:
                    _fail("QUERY_DISTRIBUTION_RECORD_BINDING_INVALID")
            else:
                _declared_record_identity(row[1], row[2], allow_blank=False)
            result.append({
                "path": path, "record_digest": row[1], "record_size": row[2],
            })
    except DistributionMetadataError:
        raise
    except (RuntimeAbiMetadataError, csv.Error, UnicodeError, ValueError):
        _fail("QUERY_DISTRIBUTION_RECORD_INVALID")
    return (
        tuple(sorted(result, key=lambda item: str(item["path"]).casefold())),
        tuple(sorted(excluded, key=lambda item: str(item["path"]).casefold())),
    )


def _external_record_row(path: str, digest: str, size: str) -> Mapping[str, Any]:
    allow_blank = path.casefold().endswith(".pyc")
    declared_digest, declared_size = _declared_record_identity(
        digest, size, allow_blank=allow_blank,
    )
    return {
        "path": path, "size": declared_size, "sha256": declared_digest,
        "reason": "external_distribution_payload_excluded",
    }


def _resolve_record_path(value: str) -> tuple[str, str]:
    if (
        type(value) is not str or not value or len(value) > 2048
        or "\\" in value or "\x00" in value or ":" in value
        or value.startswith("/") or unicodedata.normalize("NFC", value) != value
        or any(unicodedata.category(character) in {"Cc", "Cf", "Cs"} for character in value)
    ):
        _fail("QUERY_DISTRIBUTION_RECORD_INVALID")
    parts = value.split("/")
    if any(
        part in {"", "."} or part[-1:] in {" ", "."}
        or part.split(".", 1)[0].casefold() in _RESERVED
        for part in parts if part != ".."
    ):
        _fail("QUERY_DISTRIBUTION_RECORD_INVALID")
    anchor = ["@prefix", "Lib", "site-packages"]
    resolved = list(anchor)
    for part in parts:
        if part == "..":
            if len(resolved) <= 1:
                _fail("QUERY_DISTRIBUTION_RECORD_EXTERNAL_PATH_INVALID")
            resolved.pop()
        else:
            resolved.append(part)
    if resolved[:3] == anchor and len(resolved) > len(anchor):
        return "site_packages", canonical_record_path("/".join(resolved[3:]))
    if len(resolved) <= 1:
        _fail("QUERY_DISTRIBUTION_RECORD_EXTERNAL_PATH_INVALID")
    return "external_prefix", "/".join(resolved)


def _declared_record_identity(
    digest: str, size: str, *, allow_blank: bool,
) -> tuple[str, int | None]:
    if not digest and not size and allow_blank:
        return "", None
    if not digest.startswith("sha256=") or not size.isdecimal():
        _fail("QUERY_DISTRIBUTION_RECORD_DIGEST_INVALID")
    encoded = digest[7:]
    try:
        decoded = base64.b64decode(
            encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True,
        )
    except (ValueError, binascii.Error):
        _fail("QUERY_DISTRIBUTION_RECORD_DIGEST_INVALID")
    canonical = base64.urlsafe_b64encode(decoded).rstrip(b"=").decode("ascii")
    if len(decoded) != 32 or encoded != canonical:
        _fail("QUERY_DISTRIBUTION_RECORD_DIGEST_INVALID")
    return f"sha256:{decoded.hex()}", int(size)


def _validate_dist_info_identity(dist_info: str, name: str, version: str) -> None:
    leaf = dist_info.removesuffix(".dist-info")
    if "/" in leaf or "-" not in leaf:
        _fail("QUERY_DISTRIBUTION_DIST_INFO_IDENTITY_INVALID")
    directory_name, directory_version = leaf.rsplit("-", 1)
    try:
        matches = (
            normalize_distribution_name(directory_name) == name
            and Version(directory_version) == Version(version)
        )
    except InvalidVersion:
        matches = False
    if not matches:
        _fail("QUERY_DISTRIBUTION_DIST_INFO_IDENTITY_INVALID")


def normalize_distribution_name(value: object) -> str:
    if type(value) is not str or not value.strip():
        _fail("QUERY_DISTRIBUTION_NAME_INVALID")
    normalized = _NAME_PARTS.sub("-", value.strip()).lower()
    if not normalized or len(normalized) > 256:
        _fail("QUERY_DISTRIBUTION_NAME_INVALID")
    return normalized


def _valid_wheel_tag(value: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9_.]+-[a-z0-9_.]+-[a-z0-9_.]+", value))


__all__ = [
    "DistributionCatalog", "DistributionMetadata", "DistributionMetadataError",
    "DistributionMetadataLimits", "bind_selected_distribution_records",
    "build_distribution_catalog",
    "normalize_distribution_name", "read_bound_payload", "target_python_satisfies",
    "validate_selected_wheel",
]
