"""Exact inert-generation contract for Holo dependency payloads."""

from __future__ import annotations

import hashlib
import json
import posixpath
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


INVENTORY_SCHEMA_VERSION = "holoindex_dependency_payload_inventory.v1"
DESCRIPTOR_SCHEMA_VERSION = "holoindex_dependency_payload_descriptor.v1"
INVENTORY_NAME = "holoindex_dependency_payload_inventory.json"
DESCRIPTOR_NAME = "holoindex_dependency_payload_descriptor.json"
SITE_PACKAGES_DIRECTORY = "site-packages"
MAX_INVENTORY_BYTES = 32 * 1024 * 1024
MAX_DESCRIPTOR_BYTES = 16 * 1024
MAX_DIRECTORIES = 20_000
MAX_DIRECTORY_DEPTH = 32
MAX_PATH_BYTES = 512
MAX_TOTAL_PATH_BYTES = 8 * 1024 * 1024
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
_INVENTORY_KEYS = frozenset({"schema_version", "directories", "files"})
_FILE_KEYS = frozenset({"path", "size", "sha256", "role"})
_DESCRIPTOR_KEYS = frozenset(
    {
        "schema_version",
        "status",
        "generation_id",
        "inventory_file",
        "inventory_digest",
        "inventory_bytes",
        "dependency_tree_digest",
        "file_count",
        "directory_count",
        "total_bytes",
        "site_packages_directory",
        "artifact_bytes_verified_at_publication",
        "write_denial_verified",
        "activation_eligible",
    }
)


class DependencyRuntimeContractError(RuntimeError):
    """Stable fail-closed dependency-runtime contract error."""


def _fail(code: str) -> None:
    raise DependencyRuntimeContractError(code)


@dataclass(frozen=True)
class DependencyRuntimeLimits:
    max_files: int = 100_000
    max_directories: int = MAX_DIRECTORIES
    max_directory_depth: int = MAX_DIRECTORY_DEPTH
    max_path_bytes: int = MAX_PATH_BYTES
    max_total_path_bytes: int = MAX_TOTAL_PATH_BYTES
    max_file_bytes: int = 1024 * 1024 * 1024
    max_total_bytes: int = 4 * 1024 * 1024 * 1024
    max_inventory_bytes: int = MAX_INVENTORY_BYTES
    max_descriptor_bytes: int = MAX_DESCRIPTOR_BYTES

    def validate(self) -> None:
        values = (
            self.max_files,
            self.max_directories,
            self.max_directory_depth,
            self.max_path_bytes,
            self.max_total_path_bytes,
            self.max_file_bytes,
            self.max_total_bytes,
            self.max_inventory_bytes,
            self.max_descriptor_bytes,
        )
        if any(type(value) is not int or value <= 0 for value in values):
            _fail("DEPENDENCY_RUNTIME_LIMIT_INVALID")


@dataclass(frozen=True)
class DependencyRuntimeBinding:
    generation_root: Path
    site_packages_root: Path
    descriptor_path: Path
    descriptor_digest: str
    generation_id: str
    inventory_digest: str
    dependency_tree_digest: str
    file_count: int
    directory_count: int
    total_bytes: int
    artifact_bytes_verified_at_publication: bool
    write_denial_verified: bool
    activation_eligible: bool

    @property
    def public_binding(self) -> Mapping[str, object]:
        return {
            "dependency_runtime_descriptor_digest": self.descriptor_digest,
            "dependency_runtime_generation_id": self.generation_id,
            "dependency_runtime_inventory_digest": self.inventory_digest,
            "dependency_runtime_file_count": self.file_count,
            "dependency_runtime_directory_count": self.directory_count,
            "dependency_runtime_total_bytes": self.total_bytes,
            "dependency_runtime_activation_eligible": self.activation_eligible,
        }


@dataclass(frozen=True)
class DependencyRuntimeMaterializationResult:
    binding: DependencyRuntimeBinding
    reused_existing_generation: bool


def canonical_json_bytes(value: Any) -> bytes:
    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii") + b"\n"
    except (TypeError, ValueError):
        _fail("DEPENDENCY_RUNTIME_JSON_INVALID")
    return encoded


def digest_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def dependency_tree_digest(
    directories: tuple[str, ...] | list[str], rows: list[Mapping[str, Any]],
) -> str:
    files = [
        {
            "path": str(row["path"]),
            "size": int(row["size"]),
            "sha256": str(row["sha256"]).removeprefix("sha256:"),
        }
        for row in rows
    ]
    payload = json.dumps(
        {"directories": list(directories), "files": files},
        sort_keys=True, separators=(",", ":"),
    )
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def is_digest(value: object) -> bool:
    return type(value) is str and _DIGEST.fullmatch(value) is not None


def canonical_relative_path(value: object) -> str:
    if type(value) is not str or not value or len(value) > 2048:
        _fail("DEPENDENCY_RUNTIME_PATH_INVALID")
    if (
        value.startswith("/")
        or "\\" in value
        or ":" in value
        or posixpath.normpath(value) != value
        or any(part in {"", ".", ".."} for part in value.split("/"))
        or unicodedata.normalize("NFC", value) != value
        or any(unicodedata.category(char) in {"Cc", "Cf", "Cs"} for char in value)
    ):
        _fail("DEPENDENCY_RUNTIME_PATH_INVALID")
    return value


def validate_inventory(value: object) -> dict[str, Any]:
    source = _exact_mapping(value, _INVENTORY_KEYS, "DEPENDENCY_RUNTIME_INVENTORY_INVALID")
    if source.get("schema_version") != INVENTORY_SCHEMA_VERSION:
        _fail("DEPENDENCY_RUNTIME_INVENTORY_SCHEMA_INVALID")
    rows = source.get("files")
    if type(rows) is not list or not rows:
        _fail("DEPENDENCY_RUNTIME_INVENTORY_INVALID")
    directories = source.get("directories")
    if type(directories) is not list:
        _fail("DEPENDENCY_RUNTIME_INVENTORY_INVALID")
    normalized_directories = [canonical_relative_path(row) for row in directories]
    normalized = [_validated_file_row(row) for row in rows]
    directory_keys = tuple(_path_key(path) for path in normalized_directories)
    keys = tuple(_path_key(row["path"]) for row in normalized)
    if (
        directory_keys != tuple(sorted(directory_keys))
        or len(directory_keys) != len(set(directory_keys))
        or keys != tuple(sorted(keys))
        or len(keys) != len(set(keys))
        or set(directory_keys) & set(keys)
    ):
        _fail("DEPENDENCY_RUNTIME_INVENTORY_ORDER_INVALID")
    return {
        "schema_version": INVENTORY_SCHEMA_VERSION,
        "directories": normalized_directories,
        "files": normalized,
    }


def validate_descriptor(value: object) -> dict[str, Any]:
    source = _exact_mapping(value, _DESCRIPTOR_KEYS, "DEPENDENCY_RUNTIME_DESCRIPTOR_INVALID")
    if (
        source.get("schema_version") != DESCRIPTOR_SCHEMA_VERSION
        or source.get("status") != "INERT"
        or source.get("inventory_file") != INVENTORY_NAME
        or source.get("site_packages_directory") != SITE_PACKAGES_DIRECTORY
    ):
        _fail("DEPENDENCY_RUNTIME_DESCRIPTOR_INVALID")
    for name in (
        "generation_id",
        "inventory_digest",
        "dependency_tree_digest",
    ):
        if not is_digest(source.get(name)):
            _fail("DEPENDENCY_RUNTIME_DESCRIPTOR_DIGEST_INVALID")
    for name in ("inventory_bytes", "file_count"):
        if type(source.get(name)) is not int or int(source[name]) <= 0:
            _fail("DEPENDENCY_RUNTIME_DESCRIPTOR_COUNT_INVALID")
    if type(source.get("total_bytes")) is not int or source["total_bytes"] < 0:
        _fail("DEPENDENCY_RUNTIME_DESCRIPTOR_COUNT_INVALID")
    if type(source.get("directory_count")) is not int or source["directory_count"] < 0:
        _fail("DEPENDENCY_RUNTIME_DESCRIPTOR_COUNT_INVALID")
    expected_flags = {
        "artifact_bytes_verified_at_publication": True,
        "write_denial_verified": False,
        "activation_eligible": False,
    }
    if any(source.get(name) is not expected for name, expected in expected_flags.items()):
        _fail("DEPENDENCY_RUNTIME_DESCRIPTOR_TRUTH_INVALID")
    return dict(source)


def _exact_mapping(value: object, keys: frozenset[str], code: str) -> dict[str, Any]:
    if type(value) is not dict or frozenset(value) != keys:
        _fail(code)
    return value


def _validated_file_row(value: object) -> dict[str, Any]:
    source = _exact_mapping(value, _FILE_KEYS, "DEPENDENCY_RUNTIME_FILE_INVALID")
    path = canonical_relative_path(source.get("path"))
    if (
        type(source.get("size")) is not int
        or int(source["size"]) < 0
        or not is_digest(source.get("sha256"))
        or source.get("role") != "dependency_payload"
    ):
        _fail("DEPENDENCY_RUNTIME_FILE_INVALID")
    return {
        "path": path,
        "size": int(source["size"]),
        "sha256": str(source["sha256"]),
        "role": "dependency_payload",
    }


def _path_key(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold()


__all__ = [
    "DESCRIPTOR_NAME",
    "DESCRIPTOR_SCHEMA_VERSION",
    "DependencyRuntimeBinding",
    "DependencyRuntimeContractError",
    "DependencyRuntimeLimits",
    "DependencyRuntimeMaterializationResult",
    "INVENTORY_NAME",
    "INVENTORY_SCHEMA_VERSION",
    "SITE_PACKAGES_DIRECTORY",
    "dependency_tree_digest",
    "canonical_json_bytes",
    "canonical_relative_path",
    "digest_bytes",
    "is_digest",
    "validate_descriptor",
    "validate_inventory",
]
