"""Bounded wheel/RECORD ownership and stable payload reads for ABI evidence."""

from __future__ import annotations

import base64
import csv
import io
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from modules.infrastructure.shared_utilities.runtime_artifact_confined_byte_reader import (
    confined_file_identity,
    secure_digest_confined_file_impl,
    secure_read_confined_bytes_impl,
)
from modules.infrastructure.shared_utilities.runtime_artifact_windows_streams import (
    require_unnamed_data_stream_only,
)

from .reddog_holoindex_dependency_runtime_contract import (
    canonical_json_bytes,
    digest_bytes,
)
from .reddog_holoindex_runtime_abi_contract import RuntimeAbiLimits


class RuntimeAbiMetadataError(RuntimeError):
    """Stable wheel, RECORD, or artifact-read error."""


def _fail(code: str) -> None:
    raise RuntimeAbiMetadataError(code)


@dataclass(frozen=True)
class DistributionEvidence:
    rows: tuple[Mapping[str, Any], ...]
    owner_by_path: Mapping[str, tuple[str, str]]


def distribution_evidence(
    root: Path, inventory_rows: list[Mapping[str, Any]],
    native_rows: list[Mapping[str, Any]], limits: RuntimeAbiLimits,
) -> DistributionEvidence:
    """Bind compatible wheel tags and exact RECORD ownership for native files."""

    by_path = {str(row["path"]).casefold(): row for row in inventory_rows}
    native = {str(row["path"]).casefold(): row for row in native_rows}
    wheel_paths = sorted(
        (str(row["path"]) for row in inventory_rows if str(row["path"]).endswith(".dist-info/WHEEL")),
        key=lambda value: (value.casefold(), value),
    )
    if not wheel_paths or len(wheel_paths) > limits.max_distributions:
        _fail("RUNTIME_ABI_DISTRIBUTION_SET_INVALID")
    evidence: list[Mapping[str, Any]] = []
    ownership: dict[str, list[tuple[str, bool]]] = {}
    total_metadata = 0
    native_tags: dict[str, str] = {}
    for wheel_path in wheel_paths:
        row, owned, total_metadata = _distribution_row(
            root, wheel_path, by_path, native, ownership, limits, total_metadata,
        )
        tag = _native_wheel_tag(tuple(row["compatible_tags"]), owned)
        for path in owned:
            native_tags[path.casefold()] = tag
        evidence.append(row)
    owners = _exact_native_owners(native, ownership, native_tags)
    return DistributionEvidence(tuple(evidence), owners)


def bound_payload(root: Path, row: Mapping[str, Any], maximum: int) -> bytes:
    """Read one inventory-bound regular file without accepting path substitution."""

    path = root / str(row["path"])
    before = os.lstat(path)
    identity = confined_file_identity(before)
    if (
        not stat.S_ISREG(before.st_mode) or int(before.st_size) != row["size"]
        or before.st_size <= 0 or before.st_size > maximum
    ):
        _fail("RUNTIME_ABI_ARTIFACT_INVALID")
    proof = secure_digest_confined_file_impl(
        path, allowed_root=root, expected_identity=identity, max_bytes=maximum,
    )
    payload, cursor = secure_read_confined_bytes_impl(
        path, allowed_root=root, max_bytes=int(before.st_size) + 1,
    )
    require_unnamed_data_stream_only(path)
    if (
        cursor != before.st_size or len(payload) != before.st_size
        or confined_file_identity(os.lstat(path)) != identity
        or proof.digest != row["sha256"] or digest_bytes(payload) != row["sha256"]
    ):
        _fail("RUNTIME_ABI_ARTIFACT_CHANGED")
    return payload


def _distribution_row(
    root: Path, wheel_path: str, by_path: Mapping[str, Mapping[str, Any]],
    native: Mapping[str, Mapping[str, Any]], ownership: dict[str, list[tuple[str, bool]]],
    limits: RuntimeAbiLimits, total_metadata: int,
) -> tuple[Mapping[str, Any], list[str], int]:
    dist = wheel_path.removesuffix("/WHEEL")
    record_path = f"{dist}/RECORD"
    wheel_row = by_path.get(wheel_path.casefold())
    record_row = by_path.get(record_path.casefold())
    if wheel_row is None or record_row is None or "/" in dist.removesuffix(".dist-info"):
        _fail("RUNTIME_ABI_DISTRIBUTION_METADATA_INCOMPLETE")
    wheel = bound_payload(root, wheel_row, limits.max_metadata_file_bytes)
    record = bound_payload(root, record_row, limits.max_metadata_file_bytes)
    total_metadata += len(wheel) + len(record)
    if total_metadata > limits.max_metadata_total_bytes:
        _fail("RUNTIME_ABI_DISTRIBUTION_METADATA_LIMIT_EXCEEDED")
    tags = _wheel_tags(wheel)
    compatible = tuple(tag for tag in tags if _compatible_tag(tag))
    if not compatible:
        _fail("RUNTIME_ABI_WHEEL_TAG_INCOMPATIBLE")
    _record_owners(record, dist, native, ownership, limits)
    owned = sorted(
        (path for path, owners in ownership.items() if any(owner == dist for owner, _ in owners)),
        key=lambda value: (value.casefold(), value),
    )
    return ({
        "dist_info": dist,
        "wheel_digest": str(wheel_row["sha256"]),
        "record_digest": str(record_row["sha256"]),
        "tags": list(tags),
        "compatible_tags": list(compatible),
        "native_file_count": len(owned),
        "native_paths_digest": digest_bytes(canonical_json_bytes(owned)),
    }, owned, total_metadata)


def _record_owners(
    payload: bytes, dist: str, native: Mapping[str, Mapping[str, Any]],
    ownership: dict[str, list[tuple[str, bool]]], limits: RuntimeAbiLimits,
) -> None:
    try:
        rows = csv.reader(io.StringIO(payload.decode("utf-8"), newline=""), strict=True)
        seen: set[str] = set()
        for count, row in enumerate(rows, 1):
            if count > limits.max_record_rows or len(row) != 3:
                _fail("RUNTIME_ABI_RECORD_INVALID")
            key = _record_path(row[0]).casefold()
            if key in seen:
                _fail("RUNTIME_ABI_RECORD_DUPLICATE_PATH")
            seen.add(key)
            if key in native:
                exact = _record_digest_matches(row[1], row[2], native[key])
                ownership.setdefault(key, []).append((dist, exact))
    except (csv.Error, UnicodeError, ValueError):
        _fail("RUNTIME_ABI_RECORD_INVALID")


def _record_path(value: str) -> str:
    if type(value) is not str or not value or "\x00" in value or ":" in value:
        _fail("RUNTIME_ABI_RECORD_INVALID")
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        _fail("RUNTIME_ABI_RECORD_INVALID")
    return normalized


def _record_digest_matches(
    digest: str, size: str, inventory_row: Mapping[str, Any],
) -> bool:
    if not digest and not size:
        return False
    if not digest.startswith("sha256=") or not size.isdecimal():
        _fail("RUNTIME_ABI_RECORD_DIGEST_INVALID")
    expected = base64.urlsafe_b64encode(
        bytes.fromhex(str(inventory_row["sha256"])[7:])
    ).rstrip(b"=").decode("ascii")
    if digest[7:] != expected or int(size) != inventory_row["size"]:
        _fail("RUNTIME_ABI_RECORD_DIGEST_INVALID")
    return True


def _wheel_tags(payload: bytes) -> tuple[str, ...]:
    try:
        lines = payload.decode("utf-8").splitlines()
    except UnicodeError:
        _fail("RUNTIME_ABI_WHEEL_METADATA_INVALID")
    tags = sorted(
        {line[5:].strip() for line in lines if line.startswith("Tag: ")},
        key=lambda value: (value.casefold(), value),
    )
    if not tags or any(not re.fullmatch(r"[a-z0-9_.]+-[a-z0-9_.]+-[a-z0-9_.]+", tag) for tag in tags):
        _fail("RUNTIME_ABI_WHEEL_METADATA_INVALID")
    return tuple(tags)


def _compatible_tag(tag: str) -> bool:
    python, abi, platform = tag.split("-")
    python_tags, abi_tags, platforms = python.split("."), abi.split("."), platform.split(".")
    if not set(platforms) & {"any", "win_amd64"}:
        return False
    if "none" in abi_tags:
        return bool(set(python_tags) & {"py3", "py312", "cp312"})
    if "cp312" in abi_tags:
        return "cp312" in python_tags and "win_amd64" in platforms
    if "abi3" not in abi_tags or "win_amd64" not in platforms:
        return False
    return any(
        value.startswith("cp3") and value[3:].isdigit()
        and 2 <= int(value[3:]) <= 12 for value in python_tags
    )


def _native_wheel_tag(compatible: tuple[str, ...], owned: list[str]) -> str:
    if not owned:
        return ""
    needs_python_abi = any(path.casefold().endswith(".pyd") for path in owned)
    for tag in compatible:
        _python, abi, platform = tag.split("-")
        if "win_amd64" in platform.split(".") and (
            not needs_python_abi or set(abi.split(".")) & {"cp312", "abi3"}
        ):
            return tag
    _fail("RUNTIME_ABI_WHEEL_TAG_INCOMPATIBLE")


def _exact_native_owners(
    native: Mapping[str, Mapping[str, Any]],
    ownership: Mapping[str, list[tuple[str, bool]]], native_tags: Mapping[str, str],
) -> Mapping[str, tuple[str, str]]:
    result: dict[str, tuple[str, str]] = {}
    for path in native:
        owners = ownership.get(path, [])
        exact_owners = sorted({owner for owner, exact in owners if exact})
        if len(exact_owners) != 1 or any(owner not in exact_owners for owner, _ in owners):
            _fail("RUNTIME_ABI_RECORD_OWNERSHIP_INVALID")
        result[path] = (exact_owners[0], native_tags.get(path, ""))
        if not result[path][1]:
            _fail("RUNTIME_ABI_WHEEL_TAG_INCOMPATIBLE")
    return result


__all__ = [
    "DistributionEvidence", "RuntimeAbiMetadataError", "bound_payload",
    "distribution_evidence",
]
