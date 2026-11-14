"""Exact contract for one inert, wheel-bound builder packaging source."""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping

from .reddog_holoindex_dependency_runtime_contract import (
    canonical_json_bytes,
    canonical_relative_path,
    dependency_tree_digest,
    digest_bytes,
    is_digest,
)


BUILDER_PACKAGING_SOURCE_INVENTORY_SCHEMA_VERSION = (
    "reddog_builder_packaging_source_inventory.v1"
)
BUILDER_PACKAGING_SOURCE_DESCRIPTOR_SCHEMA_VERSION = (
    "reddog_builder_packaging_source_descriptor.v1"
)
BUILDER_PACKAGING_SOURCE_GENERATION_SCHEMA_VERSION = (
    "reddog_builder_packaging_source_generation.v1"
)
BUILDER_PACKAGING_SOURCE_INVENTORY_NAME = (
    "reddog_builder_packaging_source_inventory.json"
)
BUILDER_PACKAGING_SOURCE_DESCRIPTOR_NAME = (
    "reddog_builder_packaging_source_descriptor.json"
)
BUILDER_PACKAGING_SOURCE_WHEEL_DIRECTORY = "wheel"
BUILDER_PACKAGING_SOURCE_SITE_PACKAGES_DIRECTORY = "site-packages"
BUILDER_PACKAGING_SOURCE_PUBLICATION_ORPHANS = (
    ".builder-packaging-source-publication-orphans"
)

_MAX_FILES = 128
_MAX_DIRECTORIES = 128
_MAX_DEPTH = 8
_MAX_PATH_BYTES = 512
_MAX_TOTAL_PATH_BYTES = 64 * 1024
_MAX_FILE_BYTES = 1024 * 1024
_MAX_TOTAL_BYTES = 4 * 1024 * 1024
_MAX_INVENTORY_BYTES = 512 * 1024
_MAX_DESCRIPTOR_BYTES = 32 * 1024
_INVENTORY_KEYS = frozenset({"schema_version", "directories", "files"})
_FILE_KEYS = frozenset({"path", "size", "sha256", "role"})
_DIGEST_FIELDS = (
    "generation_id", "inventory_digest", "wheel_sha256",
    "central_directory_digest", "member_set_digest", "metadata_digest",
    "wheel_metadata_digest", "record_digest", "owned_files_digest",
    "dependency_tree_digest",
)
_TRUE_FIELDS = (
    "strict_archive_verified", "record_ownership_verified",
    "source_only_topology_verified", "source_materialization_performed",
    "extraction_performed", "publication_performed",
    "wheel_to_tree_verified", "artifact_bytes_verified_at_publication",
)
_AUTHORITY_BOOL_FIELDS = (
    "reviewed_pin_match", "source_lease_held_through_publication",
)
_FALSE_FIELDS = (
    "official_provenance_authenticated", "signature_verified",
    "network_performed", "download_performed", "installation_performed",
    "import_authority_verified", "child_execution_authorized",
    "builder_runtime_authenticated", "preimport_loader_authority_verified",
    "native_loader_closure_verified", "subprocess_closure_verified",
    "exact_runtime_closure_verified", "deterministic_effects_verified",
    "write_denial_verified", "activation_eligible", "a_grade_verified",
    "retrieval_rsi_verified",
)
_DESCRIPTOR_KEYS = frozenset({
    "schema_version", "status", "generation_id", "inventory_file",
    "inventory_digest", "inventory_bytes", "wheel_directory", "wheel_file",
    "wheel_size", "wheel_sha256", "site_packages_directory",
    "central_directory_digest", "member_set_digest", "metadata_digest",
    "wheel_metadata_digest", "record_digest", "owned_files_digest",
    "dependency_tree_digest", "member_count", "directory_count",
    "expanded_bytes", *_AUTHORITY_BOOL_FIELDS, *_TRUE_FIELDS, *_FALSE_FIELDS,
})


class BuilderPackagingSourceContractError(RuntimeError):
    """Stable path-free source-contract failure."""


def _fail(code: str) -> None:
    raise BuilderPackagingSourceContractError(code)


@dataclass(frozen=True)
class BuilderPackagingSourceLimits:
    max_files: int = _MAX_FILES
    max_directories: int = _MAX_DIRECTORIES
    max_directory_depth: int = _MAX_DEPTH
    max_path_bytes: int = _MAX_PATH_BYTES
    max_total_path_bytes: int = _MAX_TOTAL_PATH_BYTES
    max_file_bytes: int = _MAX_FILE_BYTES
    max_total_bytes: int = _MAX_TOTAL_BYTES
    max_inventory_bytes: int = _MAX_INVENTORY_BYTES
    max_descriptor_bytes: int = _MAX_DESCRIPTOR_BYTES

    def validate(self) -> None:
        values = tuple(self.__dict__.values())
        ceilings = (
            _MAX_FILES, _MAX_DIRECTORIES, _MAX_DEPTH, _MAX_PATH_BYTES,
            _MAX_TOTAL_PATH_BYTES, _MAX_FILE_BYTES, _MAX_TOTAL_BYTES,
            _MAX_INVENTORY_BYTES, _MAX_DESCRIPTOR_BYTES,
        )
        if any(type(value) is not int or value <= 0 for value in values):
            _fail("BUILDER_PACKAGING_SOURCE_LIMIT_INVALID")
        if any(value > ceiling for value, ceiling in zip(values, ceilings, strict=True)):
            _fail("BUILDER_PACKAGING_SOURCE_LIMIT_INVALID")


@dataclass(frozen=True)
class BuilderPackagingSourceBinding:
    generation_root: Path
    site_packages_root: Path
    wheel_path: Path
    descriptor_path: Path
    descriptor_digest: str
    generation_id: str
    inventory_digest: str
    wheel_sha256: str
    member_set_digest: str
    dependency_tree_digest: str
    member_count: int
    directory_count: int
    expanded_bytes: int
    reviewed_pin_match: bool
    source_lease_held_through_publication: bool
    source_lease_held_through_current_verification: bool

    def with_live_source_authority(
        self, *, verified: bool, published: bool,
    ) -> "BuilderPackagingSourceBinding":
        return replace(
            self, reviewed_pin_match=(verified and self.reviewed_pin_match),
            source_lease_held_through_publication=(verified and published),
            source_lease_held_through_current_verification=verified,
        )

    @property
    def public_binding(self) -> Mapping[str, object]:
        binding = {
            "builder_packaging_source_descriptor_digest": self.descriptor_digest,
            "builder_packaging_source_generation_id": self.generation_id,
            "builder_packaging_source_inventory_digest": self.inventory_digest,
            "builder_packaging_source_wheel_sha256": self.wheel_sha256,
            "builder_packaging_source_member_set_digest": self.member_set_digest,
            "builder_packaging_source_dependency_tree_digest": self.dependency_tree_digest,
            "builder_packaging_source_member_count": self.member_count,
            "builder_packaging_source_directory_count": self.directory_count,
            "builder_packaging_source_expanded_bytes": self.expanded_bytes,
            "builder_packaging_source_reviewed_pin_match": self.reviewed_pin_match,
            "builder_packaging_source_source_lease_held_through_publication": (
                self.source_lease_held_through_publication
            ),
            "builder_packaging_source_source_lease_held_through_current_verification": (
                self.source_lease_held_through_current_verification
            ),
        }
        binding.update(
            {f"builder_packaging_source_{name}": True for name in _TRUE_FIELDS}
        )
        binding.update(
            {f"builder_packaging_source_{name}": False for name in _FALSE_FIELDS}
        )
        return binding


@dataclass(frozen=True)
class BuilderPackagingSourceMaterializationResult:
    binding: BuilderPackagingSourceBinding
    reused_existing_generation: bool


@dataclass(frozen=True)
class BuilderPackagingSourcePlan:
    payload: Any
    inventory: dict[str, Any]
    inventory_raw: bytes
    dependency_tree_digest: str
    generation_id: str
    directories: tuple[str, ...]


def absolute_builder_packaging_source_store_path(value: Path | str) -> Path:
    raw = str(value or "")
    if not raw or "\x00" in raw or not Path(raw).is_absolute():
        _fail("BUILDER_PACKAGING_SOURCE_STORE_PATH_INVALID")
    path = Path(os.path.abspath(raw))
    if path.drive.casefold() not in {"o:", "e:"}:
        _fail("BUILDER_PACKAGING_SOURCE_STORE_VOLUME_INVALID")
    return path


def stable_builder_packaging_source_error(error: BaseException, fallback: str) -> str:
    """Return only a stable code; never expose paths or private values."""

    candidate = str(error)
    if re.fullmatch(r"[A-Z][A-Z0-9_]*(?::[A-Z][A-Z0-9_]*)*", candidate):
        return candidate
    return fallback


def validated_builder_packaging_source_token(value: object) -> str:
    if (
        type(value) is not str or len(value) != 32
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _fail("BUILDER_PACKAGING_SOURCE_TOKEN_INVALID")
    return value


def builder_packaging_source_entry_exists(path: Path) -> bool:
    try:
        os.lstat(path)
        return True
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise BuilderPackagingSourceContractError(
            "BUILDER_PACKAGING_SOURCE_GENERATION_LOOKUP_FAILED"
        ) from exc


def validate_builder_packaging_source_inventory(value: object) -> dict[str, Any]:
    source = _exact_mapping(
        value, _INVENTORY_KEYS, "BUILDER_PACKAGING_SOURCE_INVENTORY_INVALID"
    )
    if source.get("schema_version") != BUILDER_PACKAGING_SOURCE_INVENTORY_SCHEMA_VERSION:
        _fail("BUILDER_PACKAGING_SOURCE_INVENTORY_SCHEMA_INVALID")
    directories = source.get("directories")
    files = source.get("files")
    if type(directories) is not list or type(files) is not list or not files:
        _fail("BUILDER_PACKAGING_SOURCE_INVENTORY_INVALID")
    normalized_directories = [_relative(value) for value in directories]
    normalized_files = [_file_row(value) for value in files]
    _require_canonical_order(normalized_directories, normalized_files)
    return {
        "schema_version": BUILDER_PACKAGING_SOURCE_INVENTORY_SCHEMA_VERSION,
        "directories": normalized_directories,
        "files": normalized_files,
    }


def validate_builder_packaging_source_descriptor(value: object) -> dict[str, Any]:
    source = _exact_mapping(
        value, _DESCRIPTOR_KEYS, "BUILDER_PACKAGING_SOURCE_DESCRIPTOR_INVALID"
    )
    if not _descriptor_fixed_fields(source):
        _fail("BUILDER_PACKAGING_SOURCE_DESCRIPTOR_INVALID")
    if any(not is_digest(source.get(name)) for name in _DIGEST_FIELDS):
        _fail("BUILDER_PACKAGING_SOURCE_DESCRIPTOR_DIGEST_INVALID")
    _require_positive_counts(source)
    if any(source.get(name) is not True for name in _TRUE_FIELDS):
        _fail("BUILDER_PACKAGING_SOURCE_DESCRIPTOR_TRUTH_INVALID")
    if any(type(source.get(name)) is not bool for name in _AUTHORITY_BOOL_FIELDS):
        _fail("BUILDER_PACKAGING_SOURCE_DESCRIPTOR_TRUTH_INVALID")
    if any(source.get(name) is not False for name in _FALSE_FIELDS):
        _fail("BUILDER_PACKAGING_SOURCE_DESCRIPTOR_TRUTH_INVALID")
    return dict(source)


def require_builder_packaging_source_authority(
    descriptor: Mapping[str, Any], required: bool,
    wheel_size: int, wheel_sha256: str,
) -> None:
    if type(required) is not bool:
        _fail("BUILDER_PACKAGING_SOURCE_AUTHORITY_INVALID")
    if required and (
        descriptor.get("wheel_size") != wheel_size
        or descriptor.get("wheel_sha256") != "sha256:" + wheel_sha256
    ):
        _fail("BUILDER_PACKAGING_SOURCE_AUTHORITY_REQUIRED")


def derive_builder_packaging_source_generation_id(
    *, wheel_filename: str, wheel_size: int, wheel_sha256: str,
    central_directory_digest: str, member_set_digest: str,
    metadata_digest: str, wheel_metadata_digest: str, record_digest: str,
    owned_files_digest: str, dependency_tree_digest_value: str,
    member_count: int, directory_count: int, expanded_bytes: int,
) -> str:
    payload = {
        "schema_version": BUILDER_PACKAGING_SOURCE_GENERATION_SCHEMA_VERSION,
        "wheel_filename": _relative(wheel_filename), "wheel_size": wheel_size,
        "wheel_sha256": wheel_sha256,
        "central_directory_digest": central_directory_digest,
        "member_set_digest": member_set_digest, "metadata_digest": metadata_digest,
        "wheel_metadata_digest": wheel_metadata_digest,
        "record_digest": record_digest, "owned_files_digest": owned_files_digest,
        "dependency_tree_digest": dependency_tree_digest_value,
        "member_count": member_count, "directory_count": directory_count,
        "expanded_bytes": expanded_bytes,
    }
    _validate_generation_identity_payload(payload)
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("ascii")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def build_builder_packaging_source_inventory(
    directories: tuple[str, ...], members: tuple[Mapping[str, object], ...],
    limits: BuilderPackagingSourceLimits,
) -> tuple[dict[str, Any], str]:
    limits.validate()
    rows = [
        {"path": row["path"], "size": row["size"],
         "sha256": row["sha256"], "role": "packaging_wheel_member"}
        for row in members
    ]
    value = validate_builder_packaging_source_inventory({
        "schema_version": BUILDER_PACKAGING_SOURCE_INVENTORY_SCHEMA_VERSION,
        "directories": list(directories), "files": rows,
    })
    _validate_inventory_limits(value, limits)
    return value, dependency_tree_digest(value["directories"], value["files"])


def build_builder_packaging_source_plan(
    *, payload: Any, wheel_filename: str,
    limits: BuilderPackagingSourceLimits,
) -> BuilderPackagingSourcePlan:
    directories = _member_directories(payload)
    inventory, tree_digest = build_builder_packaging_source_inventory(
        directories, _member_rows(payload), limits,
    )
    proof = payload.proof
    generation_id = derive_builder_packaging_source_generation_id(
        wheel_filename=wheel_filename, wheel_size=len(payload.wheel_bytes),
        wheel_sha256=digest_bytes(payload.wheel_bytes),
        central_directory_digest=proof.central_directory_digest,
        member_set_digest=proof.member_set_digest,
        metadata_digest=proof.metadata_digest,
        wheel_metadata_digest=proof.wheel_metadata_digest,
        record_digest=proof.record_digest,
        owned_files_digest=proof.owned_files_digest,
        dependency_tree_digest_value=tree_digest,
        member_count=len(payload.members), directory_count=len(directories),
        expanded_bytes=sum(len(member.payload) for member in payload.members),
    )
    return BuilderPackagingSourcePlan(
        payload, inventory, canonical_json_bytes(inventory), tree_digest,
        generation_id, directories,
    )


def _member_rows(payload: Any) -> tuple[dict[str, object], ...]:
    rows = tuple(
        {
            "path": member.path, "size": len(member.payload),
            "sha256": digest_bytes(member.payload),
        }
        for member in payload.members
    )
    return tuple(sorted(rows, key=lambda row: str(row["path"]).casefold()))


def _member_directories(payload: Any) -> tuple[str, ...]:
    directories: set[str] = set()
    for member in payload.members:
        parts = Path(member.path).parts[:-1]
        for depth in range(1, len(parts) + 1):
            directories.add(Path(*parts[:depth]).as_posix())
    return tuple(sorted(directories, key=str.casefold))


def _descriptor_fixed_fields(source: Mapping[str, Any]) -> bool:
    return (
        source.get("schema_version") == BUILDER_PACKAGING_SOURCE_DESCRIPTOR_SCHEMA_VERSION
        and source.get("status") == "INERT_SOURCE"
        and source.get("inventory_file") == BUILDER_PACKAGING_SOURCE_INVENTORY_NAME
        and source.get("wheel_directory") == BUILDER_PACKAGING_SOURCE_WHEEL_DIRECTORY
        and source.get("site_packages_directory")
        == BUILDER_PACKAGING_SOURCE_SITE_PACKAGES_DIRECTORY
        and type(source.get("wheel_file")) is str
        and _relative(source["wheel_file"]) == source["wheel_file"]
    )


def _require_positive_counts(source: Mapping[str, Any]) -> None:
    positive = ("inventory_bytes", "wheel_size", "member_count", "expanded_bytes")
    nonnegative = ("directory_count",)
    if any(type(source.get(name)) is not int or source[name] <= 0 for name in positive):
        _fail("BUILDER_PACKAGING_SOURCE_DESCRIPTOR_COUNT_INVALID")
    if any(type(source.get(name)) is not int or source[name] < 0 for name in nonnegative):
        _fail("BUILDER_PACKAGING_SOURCE_DESCRIPTOR_COUNT_INVALID")


def _validate_generation_identity_payload(payload: Mapping[str, Any]) -> None:
    digests = tuple(value for key, value in payload.items() if key.endswith("digest") or key.endswith("sha256"))
    counts = (payload["wheel_size"], payload["member_count"], payload["expanded_bytes"])
    if any(not is_digest(value) for value in digests):
        _fail("BUILDER_PACKAGING_SOURCE_GENERATION_IDENTITY_INVALID")
    if any(type(value) is not int or value <= 0 for value in counts):
        _fail("BUILDER_PACKAGING_SOURCE_GENERATION_IDENTITY_INVALID")
    if type(payload["directory_count"]) is not int or payload["directory_count"] < 0:
        _fail("BUILDER_PACKAGING_SOURCE_GENERATION_IDENTITY_INVALID")


def _validate_inventory_limits(
    inventory: Mapping[str, Any], limits: BuilderPackagingSourceLimits,
) -> None:
    directories = inventory["directories"]
    files = inventory["files"]
    paths = tuple(directories) + tuple(row["path"] for row in files)
    sizes = tuple(len(path.encode("utf-8")) for path in paths)
    if (
        len(files) > limits.max_files
        or len(directories) > limits.max_directories
        or any(len(Path(path).parts) > limits.max_directory_depth for path in paths)
        or any(size > limits.max_path_bytes for size in sizes)
        or sum(sizes) > limits.max_total_path_bytes
        or any(row["size"] > limits.max_file_bytes for row in files)
        or sum(row["size"] for row in files) > limits.max_total_bytes
    ):
        _fail("BUILDER_PACKAGING_SOURCE_INVENTORY_BOUND_INVALID")
    if len(canonical_json_bytes(inventory)) > limits.max_inventory_bytes:
        _fail("BUILDER_PACKAGING_SOURCE_INVENTORY_BOUND_INVALID")


def _exact_mapping(value: object, keys: frozenset[str], code: str) -> dict[str, Any]:
    if type(value) is not dict or frozenset(value) != keys:
        _fail(code)
    return value


def _relative(value: object) -> str:
    try:
        return canonical_relative_path(value)
    except Exception as exc:
        raise BuilderPackagingSourceContractError(
            "BUILDER_PACKAGING_SOURCE_PATH_INVALID"
        ) from exc


def _file_row(value: object) -> dict[str, Any]:
    source = _exact_mapping(value, _FILE_KEYS, "BUILDER_PACKAGING_SOURCE_FILE_INVALID")
    if (
        type(source.get("size")) is not int or source["size"] < 0
        or not is_digest(source.get("sha256"))
        or source.get("role") != "packaging_wheel_member"
    ):
        _fail("BUILDER_PACKAGING_SOURCE_FILE_INVALID")
    return {"path": _relative(source.get("path")), "size": source["size"],
            "sha256": source["sha256"], "role": source["role"]}


def _require_canonical_order(
    directories: list[str], files: list[dict[str, Any]],
) -> None:
    directory_keys = tuple(value.casefold() for value in directories)
    file_keys = tuple(row["path"].casefold() for row in files)
    if (
        directory_keys != tuple(sorted(directory_keys))
        or file_keys != tuple(sorted(file_keys))
        or len(directory_keys) != len(set(directory_keys))
        or len(file_keys) != len(set(file_keys))
        or set(directory_keys) & set(file_keys)
    ):
        _fail("BUILDER_PACKAGING_SOURCE_INVENTORY_ORDER_INVALID")


__all__ = [
    "BUILDER_PACKAGING_SOURCE_DESCRIPTOR_NAME",
    "BUILDER_PACKAGING_SOURCE_INVENTORY_NAME",
    "BUILDER_PACKAGING_SOURCE_PUBLICATION_ORPHANS",
    "BUILDER_PACKAGING_SOURCE_SITE_PACKAGES_DIRECTORY",
    "BUILDER_PACKAGING_SOURCE_WHEEL_DIRECTORY",
    "BuilderPackagingSourceBinding", "BuilderPackagingSourceContractError",
    "BuilderPackagingSourceLimits", "BuilderPackagingSourceMaterializationResult",
    "BuilderPackagingSourcePlan",
    "absolute_builder_packaging_source_store_path",
    "builder_packaging_source_entry_exists",
    "build_builder_packaging_source_inventory",
    "build_builder_packaging_source_plan",
    "derive_builder_packaging_source_generation_id",
    "require_builder_packaging_source_authority",
    "stable_builder_packaging_source_error",
    "validate_builder_packaging_source_descriptor",
    "validate_builder_packaging_source_inventory",
    "validated_builder_packaging_source_token",
]
