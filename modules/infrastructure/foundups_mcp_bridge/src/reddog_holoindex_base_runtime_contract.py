"""Strict contract for one inert HoloIndex Python base-runtime payload."""

from __future__ import annotations

import posixpath
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .reddog_holoindex_dependency_runtime_contract import (
    DependencyRuntimeContractError,
    canonical_json_bytes as _dependency_canonical_json_bytes,
    canonical_relative_path as _dependency_canonical_relative_path,
    digest_bytes,
    is_digest,
)


INVENTORY_SCHEMA_VERSION = "holoindex_base_runtime_inventory.v1"
DESCRIPTOR_SCHEMA_VERSION = "holoindex_base_runtime_descriptor.v1"
INVENTORY_NAME = "holoindex_base_runtime_inventory.json"
DESCRIPTOR_NAME = "holoindex_base_runtime_descriptor.json"
PAYLOAD_DIRECTORY = "python-runtime"

PLATFORM_TAG = "windows"
ADMITTED_PATH_ROOTS = (".", "DLLs", "Lib", "tcl")
EXCLUDED_PATH_ROOTS = tuple(sorted(
    ("Doc", "include", "Lib/site-packages", "libs", "LICENSE.txt", "NEWS.txt", "Scripts"),
    key=str.casefold,
))
INVENTORY_ROLES = (
    "python_executable",
    "python_native_extension",
    "python_runtime_configuration",
    "python_runtime_data",
    "python_runtime_library",
    "python_standard_library",
)
REQUIRED_INVENTORY_ROLES = (
    "python_executable",
    "python_native_extension",
    "python_runtime_data",
    "python_runtime_library",
    "python_standard_library",
)

_INVENTORY_KEYS = frozenset(
    {
        "schema_version",
        "platform_tag",
        "admitted_path_roots",
        "excluded_path_roots",
        "directories",
        "files",
    }
)
_FILE_KEYS = frozenset({"path", "size", "sha256", "role"})
_DESCRIPTOR_KEYS = frozenset(
    {
        "schema_version",
        "status",
        "generation_id",
        "inventory_file",
        "inventory_digest",
        "inventory_bytes",
        "base_runtime_tree_digest",
        "file_count",
        "directory_count",
        "total_bytes",
        "platform_tag",
        "admitted_path_roots",
        "excluded_path_roots",
        "inventory_roles",
        "required_inventory_roles",
        "artifact_bytes_verified_at_publication",
        "native_loader_closure_verified",
        "deterministic_effects_verified",
        "signature_verified",
        "write_denial_verified",
        "activation_eligible",
        "exact_runtime_closure_verified",
    }
)


class BaseRuntimeContractError(RuntimeError):
    """Stable fail-closed base-runtime contract error."""


def _fail(code: str) -> None:
    raise BaseRuntimeContractError(code)


@dataclass(frozen=True)
class BaseRuntimeLimits:
    max_files: int = 100_000
    max_directories: int = 30_000
    max_directory_depth: int = 32
    max_path_bytes: int = 512
    max_total_path_bytes: int = 8 * 1024 * 1024
    max_file_bytes: int = 2 * 1024 * 1024 * 1024
    max_total_bytes: int = 8 * 1024 * 1024 * 1024
    max_inventory_bytes: int = 32 * 1024 * 1024
    max_descriptor_bytes: int = 16 * 1024

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
            _fail("BASE_RUNTIME_LIMIT_INVALID")


@dataclass(frozen=True)
class BaseRuntimeBinding:
    generation_root: Path
    base_prefix_root: Path
    descriptor_path: Path
    descriptor_digest: str
    generation_id: str
    inventory_digest: str
    base_runtime_tree_digest: str
    file_count: int
    directory_count: int
    total_bytes: int
    artifact_bytes_verified_at_publication: bool
    native_loader_closure_verified: bool
    deterministic_effects_verified: bool
    signature_verified: bool
    write_denial_verified: bool
    activation_eligible: bool
    exact_runtime_closure_verified: bool

    @property
    def public_binding(self) -> Mapping[str, object]:
        return {
            "base_runtime_descriptor_digest": self.descriptor_digest,
            "base_runtime_generation_id": self.generation_id,
            "base_runtime_inventory_digest": self.inventory_digest,
            "base_runtime_tree_digest": self.base_runtime_tree_digest,
            "base_runtime_file_count": self.file_count,
            "base_runtime_directory_count": self.directory_count,
            "base_runtime_total_bytes": self.total_bytes,
            "base_runtime_artifact_bytes_verified": (
                self.artifact_bytes_verified_at_publication
            ),
            "base_runtime_native_loader_closure_verified": (
                self.native_loader_closure_verified
            ),
            "base_runtime_deterministic_effects_verified": (
                self.deterministic_effects_verified
            ),
            "base_runtime_signature_verified": self.signature_verified,
            "base_runtime_write_denial_verified": self.write_denial_verified,
            "base_runtime_activation_eligible": self.activation_eligible,
            "base_runtime_exact_closure_verified": self.exact_runtime_closure_verified,
        }


@dataclass(frozen=True)
class BaseRuntimeMaterializationResult:
    binding: BaseRuntimeBinding
    reused_existing_generation: bool


def canonical_json_bytes(value: Any) -> bytes:
    """Return the shared ASCII canonical JSON form under this error boundary."""

    try:
        return _dependency_canonical_json_bytes(value)
    except DependencyRuntimeContractError:
        _fail("BASE_RUNTIME_JSON_INVALID")


def canonical_relative_path(value: object) -> str:
    """Validate a portable relative path under this error boundary."""

    try:
        return _dependency_canonical_relative_path(value)
    except DependencyRuntimeContractError:
        _fail("BASE_RUNTIME_PATH_INVALID")


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if type(key) is not str or key in result:
            _fail("BASE_RUNTIME_JSON_DUPLICATE_KEY")
        result[key] = value
    return result


def parse_canonical_json(raw: str) -> dict[str, Any]:
    """Parse one canonical contract object and reject duplicate JSON keys."""

    import json

    if type(raw) is not str:
        _fail("BASE_RUNTIME_JSON_INVALID")
    try:
        value = json.loads(
            raw,
            object_pairs_hook=_strict_object,
            parse_constant=lambda _value: _fail("BASE_RUNTIME_JSON_INVALID"),
        )
    except BaseRuntimeContractError:
        raise
    except Exception:
        _fail("BASE_RUNTIME_JSON_INVALID")
    if type(value) is not dict or canonical_json_bytes(value).decode("ascii") != raw:
        _fail("BASE_RUNTIME_JSON_INVALID")
    return value


def base_runtime_tree_digest(
    directories: list[str] | tuple[str, ...], rows: list[Mapping[str, Any]],
) -> str:
    """Bind complete virtual topology, file bytes, and inventory roles."""

    files = [
        {
            "path": str(row["path"]),
            "role": str(row["role"]),
            "sha256": str(row["sha256"]),
            "size": int(row["size"]),
        }
        for row in rows
    ]
    payload = {
        "admitted_path_roots": list(ADMITTED_PATH_ROOTS),
        "directories": list(directories),
        "excluded_path_roots": list(EXCLUDED_PATH_ROOTS),
        "files": files,
        "platform_tag": PLATFORM_TAG,
    }
    return digest_bytes(canonical_json_bytes(payload))


def validate_inventory(
    value: object, limits: BaseRuntimeLimits = BaseRuntimeLimits(),
) -> dict[str, Any]:
    """Validate one complete, path-free virtual base-runtime inventory."""

    limits.validate()
    source = _exact_mapping(value, _INVENTORY_KEYS, "BASE_RUNTIME_INVENTORY_INVALID")
    _validate_root_lists(source)
    directories = source.get("directories")
    rows = source.get("files")
    if type(directories) is not list or type(rows) is not list or not rows:
        _fail("BASE_RUNTIME_INVENTORY_INVALID")
    normalized_directories = [canonical_relative_path(path) for path in directories]
    normalized_rows = [_validated_file_row(row) for row in rows]
    _validate_order_and_topology(normalized_directories, normalized_rows)
    _validate_inventory_limits(normalized_directories, normalized_rows, limits)
    return {
        "schema_version": INVENTORY_SCHEMA_VERSION,
        "platform_tag": PLATFORM_TAG,
        "admitted_path_roots": list(ADMITTED_PATH_ROOTS),
        "excluded_path_roots": list(EXCLUDED_PATH_ROOTS),
        "directories": normalized_directories,
        "files": normalized_rows,
    }


def validate_descriptor(value: object) -> dict[str, Any]:
    """Validate an inert descriptor without granting execution authority."""

    source = _exact_mapping(value, _DESCRIPTOR_KEYS, "BASE_RUNTIME_DESCRIPTOR_INVALID")
    if (
        source.get("schema_version") != DESCRIPTOR_SCHEMA_VERSION
        or source.get("status") != "INERT"
        or source.get("inventory_file") != INVENTORY_NAME
    ):
        _fail("BASE_RUNTIME_DESCRIPTOR_INVALID")
    _validate_descriptor_lists(source)
    _validate_descriptor_digests(source)
    _validate_descriptor_counts(source)
    _validate_descriptor_truth(source)
    return dict(source)


def _exact_mapping(value: object, keys: frozenset[str], code: str) -> dict[str, Any]:
    if type(value) is not dict or frozenset(value) != keys:
        _fail(code)
    return value


def _validate_root_lists(source: Mapping[str, Any]) -> None:
    if (
        source.get("platform_tag") != PLATFORM_TAG
        or type(source.get("admitted_path_roots")) is not list
        or tuple(source["admitted_path_roots"]) != ADMITTED_PATH_ROOTS
        or type(source.get("excluded_path_roots")) is not list
        or tuple(source["excluded_path_roots"]) != EXCLUDED_PATH_ROOTS
        or source.get("schema_version") != INVENTORY_SCHEMA_VERSION
    ):
        _fail("BASE_RUNTIME_ROOT_CONTRACT_INVALID")


def _validated_file_row(value: object) -> dict[str, Any]:
    source = _exact_mapping(value, _FILE_KEYS, "BASE_RUNTIME_FILE_INVALID")
    path = canonical_relative_path(source.get("path"))
    role = source.get("role")
    try:
        expected_role = base_runtime_file_role(path)
    except BaseRuntimeContractError:
        _fail("BASE_RUNTIME_FILE_INVALID")
    if (
        role not in INVENTORY_ROLES
        or role != expected_role
        or type(source.get("size")) is not int
        or int(source["size"]) < 0
        or not is_digest(source.get("sha256"))
    ):
        _fail("BASE_RUNTIME_FILE_INVALID")
    return {
        "path": path,
        "size": int(source["size"]),
        "sha256": str(source["sha256"]),
        "role": str(role),
    }


def _path_key(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold()


def _under(path: str, root: str) -> bool:
    path_key = _path_key(path)
    root_key = _path_key(root)
    return path_key == root_key or path_key.startswith(root_key + "/")


def _is_root_file(path: str) -> bool:
    return "/" not in path


def base_runtime_file_role(path: str) -> str:
    """Classify one admitted Windows base-prefix file without path rewriting."""

    path = canonical_relative_path(path)
    lowered = path.casefold()
    if any(_under(path, root) for root in EXCLUDED_PATH_ROOTS):
        _fail("BASE_RUNTIME_PATH_EXCLUDED")
    if _is_root_file(path) and lowered.startswith("python") and lowered.endswith(".exe"):
        return "python_executable"
    prefixes = ("python", "vcruntime140")
    if _is_root_file(path) and lowered.startswith(prefixes) and lowered.endswith(".dll"):
        return "python_runtime_library"
    if _is_root_file(path) and lowered.endswith((".cfg", "._pth")):
        return "python_runtime_configuration"
    if (_under(path, "DLLs") or _under(path, "Lib")) and lowered.endswith((".dll", ".pyd")):
        return "python_native_extension"
    if _under(path, "DLLs") or _under(path, "tcl"):
        return "python_runtime_data"
    if _under(path, "Lib"):
        return "python_standard_library"
    _fail("BASE_RUNTIME_FILE_ROLE_INVALID")


def _validate_order_and_topology(
    directories: list[str], rows: list[dict[str, Any]],
) -> None:
    directory_keys = tuple(_path_key(path) for path in directories)
    file_keys = tuple(_path_key(row["path"]) for row in rows)
    if (
        directory_keys != tuple(sorted(directory_keys))
        or file_keys != tuple(sorted(file_keys))
        or len(directory_keys) != len(set(directory_keys))
        or len(file_keys) != len(set(file_keys))
        or set(directory_keys) & set(file_keys)
    ):
        _fail("BASE_RUNTIME_INVENTORY_ORDER_INVALID")
    _validate_topology(directories, rows)


def _validate_topology(directories: list[str], rows: list[dict[str, Any]]) -> None:
    directory_set = set(directories)
    admitted_directories = {root for root in ADMITTED_PATH_ROOTS if root != "."}
    if not admitted_directories.issubset(directory_set):
        _fail("BASE_RUNTIME_TOPOLOGY_INVALID")
    for path in directories:
        parent = posixpath.dirname(path)
        if (
            any(_under(path, root) for root in EXCLUDED_PATH_ROOTS)
            or not any(_under(path, root) for root in admitted_directories)
            or (parent and parent not in directory_set)
        ):
            _fail("BASE_RUNTIME_TOPOLOGY_INVALID")
    roles = {row["role"] for row in rows}
    for row in rows:
        parent = posixpath.dirname(row["path"])
        if parent and parent not in directory_set:
            _fail("BASE_RUNTIME_TOPOLOGY_INVALID")
    if not set(REQUIRED_INVENTORY_ROLES).issubset(roles):
        _fail("BASE_RUNTIME_ROLE_COVERAGE_INVALID")


def _validate_inventory_limits(
    directories: list[str], rows: list[dict[str, Any]], limits: BaseRuntimeLimits,
) -> None:
    paths = tuple(directories) + tuple(row["path"] for row in rows)
    encoded_sizes = tuple(len(path.encode("utf-8")) for path in paths)
    if (
        len(rows) > limits.max_files
        or len(directories) > limits.max_directories
        or any(len(path.split("/")) > limits.max_directory_depth for path in paths)
        or any(size > limits.max_path_bytes for size in encoded_sizes)
        or sum(encoded_sizes) > limits.max_total_path_bytes
        or any(row["size"] > limits.max_file_bytes for row in rows)
        or sum(row["size"] for row in rows) > limits.max_total_bytes
    ):
        _fail("BASE_RUNTIME_INVENTORY_BOUND_INVALID")


def _validate_descriptor_lists(source: Mapping[str, Any]) -> None:
    expected = (
        ("admitted_path_roots", ADMITTED_PATH_ROOTS),
        ("excluded_path_roots", EXCLUDED_PATH_ROOTS),
        ("inventory_roles", INVENTORY_ROLES),
        ("required_inventory_roles", REQUIRED_INVENTORY_ROLES),
    )
    if source.get("platform_tag") != PLATFORM_TAG or any(
        type(source.get(name)) is not list or tuple(source[name]) != values
        for name, values in expected
    ):
        _fail("BASE_RUNTIME_DESCRIPTOR_ROOT_CONTRACT_INVALID")


def _validate_descriptor_digests(source: Mapping[str, Any]) -> None:
    names = ("generation_id", "inventory_digest", "base_runtime_tree_digest")
    if any(not is_digest(source.get(name)) for name in names):
        _fail("BASE_RUNTIME_DESCRIPTOR_DIGEST_INVALID")
    if source["generation_id"] != source["base_runtime_tree_digest"]:
        _fail("BASE_RUNTIME_DESCRIPTOR_BINDING_INVALID")


def _validate_descriptor_counts(source: Mapping[str, Any]) -> None:
    positive = ("inventory_bytes", "file_count", "directory_count")
    if any(type(source.get(name)) is not int or int(source[name]) <= 0 for name in positive):
        _fail("BASE_RUNTIME_DESCRIPTOR_COUNT_INVALID")
    if type(source.get("total_bytes")) is not int or int(source["total_bytes"]) < 0:
        _fail("BASE_RUNTIME_DESCRIPTOR_COUNT_INVALID")


def _validate_descriptor_truth(source: Mapping[str, Any]) -> None:
    expected = {
        "artifact_bytes_verified_at_publication": True,
        "native_loader_closure_verified": False,
        "deterministic_effects_verified": False,
        "signature_verified": False,
        "write_denial_verified": False,
        "activation_eligible": False,
        "exact_runtime_closure_verified": False,
    }
    if any(source.get(name) is not value for name, value in expected.items()):
        _fail("BASE_RUNTIME_DESCRIPTOR_TRUTH_INVALID")


__all__ = [
    "ADMITTED_PATH_ROOTS",
    "DESCRIPTOR_NAME",
    "DESCRIPTOR_SCHEMA_VERSION",
    "EXCLUDED_PATH_ROOTS",
    "INVENTORY_NAME",
    "INVENTORY_ROLES",
    "INVENTORY_SCHEMA_VERSION",
    "PAYLOAD_DIRECTORY",
    "PLATFORM_TAG",
    "REQUIRED_INVENTORY_ROLES",
    "BaseRuntimeBinding",
    "BaseRuntimeContractError",
    "BaseRuntimeLimits",
    "BaseRuntimeMaterializationResult",
    "base_runtime_file_role",
    "base_runtime_tree_digest",
    "canonical_json_bytes",
    "canonical_relative_path",
    "digest_bytes",
    "is_digest",
    "parse_canonical_json",
    "validate_descriptor",
    "validate_inventory",
]
