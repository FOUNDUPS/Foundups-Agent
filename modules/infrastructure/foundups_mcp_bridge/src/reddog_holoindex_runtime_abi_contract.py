"""Strict inert contract for composition-bound Windows/CPython ABI evidence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Mapping

from .reddog_holoindex_dependency_runtime_contract import (
    canonical_json_bytes,
    canonical_relative_path,
    digest_bytes,
    is_digest,
)


INVENTORY_SCHEMA_VERSION = "holoindex_runtime_abi_inventory.v1"
DESCRIPTOR_SCHEMA_VERSION = "holoindex_runtime_abi_attestation_descriptor.v1"
INVENTORY_NAME = "holoindex_runtime_abi_inventory.json"
DESCRIPTOR_NAME = "holoindex_runtime_abi_attestation_descriptor.json"
BASE_ROLE = "python_base_runtime"
DEPENDENCY_ROLE = "python_dependency_runtime"
TARGET = {
    "implementation": "cpython",
    "python_major": 3,
    "python_minor": 12,
    "python_abi_tag": "cp312",
    "stable_abi_tag": "abi3",
    "platform_tag": "win_amd64",
    "pe_machine": 0x8664,
    "pe_optional_magic": 0x20B,
}

_INVENTORY_KEYS = frozenset({
    "schema_version", "runtime_composition_generation_id", "target",
    "distributions", "native_files",
})
_DISTRIBUTION_KEYS = frozenset({
    "dist_info", "wheel_digest", "record_digest", "tags", "compatible_tags",
    "native_file_count", "native_paths_digest",
})
_NATIVE_KEYS = frozenset({
    "component_role", "path", "sha256", "size", "machine", "optional_magic",
    "image_kind", "normal_imports", "delay_imports", "internal_imports",
    "external_imports", "export_names_digest", "export_name_count",
    "export_ordinals_digest", "export_ordinal_count",
    "forwarded_export_names_digest", "forwarded_export_name_count",
    "forwarded_export_ordinals_digest", "forwarded_export_ordinal_count",
    "direct_python_link_libraries", "reachable_python_libraries",
    "python_abi_reachable", "distribution", "compatible_wheel_tag",
})
_IMPORT_KEYS = frozenset({
    "library", "names_digest", "name_count", "ordinals_digest", "ordinal_count",
})
_DESCRIPTOR_KEYS = frozenset({
    "schema_version", "status", "generation_id", "runtime_composition",
    "target", "inventory_file", "inventory_digest", "native_file_count",
    "native_total_bytes", "distribution_count", "normal_import_library_count",
    "delay_import_library_count", "external_import_library_count",
    "python_link_file_count", "artifact_bytes_independently_reverified",
    "declared_pe_metadata_verified", "declared_pe_machine_compatible",
    "wheel_tag_compatibility_verified", "record_ownership_verified",
    "declared_python_link_abi_verified", "native_loader_closure_verified",
    "deterministic_effects_verified", "preimport_bootstrap_verified",
    "signature_verified", "write_denial_verified", "activation_eligible",
    "exact_runtime_closure_verified",
})
_COMPOSITION_KEYS = frozenset({"generation_id", "descriptor_digest"})


class RuntimeAbiContractError(RuntimeError):
    """Stable fail-closed ABI contract error."""


def _fail(code: str) -> None:
    raise RuntimeAbiContractError(code)


@dataclass(frozen=True)
class RuntimeAbiLimits:
    max_native_files: int = 2_048
    max_distributions: int = 2_048
    max_native_file_bytes: int = 512 * 1024 * 1024
    max_total_native_bytes: int = 4 * 1024 * 1024 * 1024
    max_metadata_file_bytes: int = 2 * 1024 * 1024
    max_metadata_total_bytes: int = 64 * 1024 * 1024
    max_record_rows: int = 500_000
    max_total_import_libraries: int = 65_536
    max_total_import_thunk_entries: int = 1_000_000
    max_total_exports: int = 1_000_000
    max_total_name_bytes: int = 64 * 1024 * 1024
    max_total_graph_edges: int = 65_536
    max_inventory_bytes: int = 8 * 1024 * 1024
    max_descriptor_bytes: int = 64 * 1024

    def validate(self) -> None:
        if any(type(value) is not int or value <= 0 for value in vars(self).values()):
            _fail("RUNTIME_ABI_LIMIT_INVALID")


@dataclass(frozen=True)
class RuntimeAbiBinding:
    generation_root: Path
    descriptor_path: Path
    descriptor_digest: str
    inventory_path: Path
    inventory_digest: str
    generation_id: str
    runtime_composition_generation_id: str
    runtime_composition_descriptor_digest: str
    native_file_count: int
    native_total_bytes: int
    distribution_count: int
    artifact_bytes_independently_reverified: bool
    declared_pe_metadata_verified: bool
    declared_pe_machine_compatible: bool
    wheel_tag_compatibility_verified: bool
    record_ownership_verified: bool
    declared_python_link_abi_verified: bool
    native_loader_closure_verified: bool
    deterministic_effects_verified: bool
    preimport_bootstrap_verified: bool
    signature_verified: bool
    write_denial_verified: bool
    activation_eligible: bool
    exact_runtime_closure_verified: bool

    @property
    def public_binding(self) -> Mapping[str, object]:
        return {
            "runtime_abi_generation_id": self.generation_id,
            "runtime_abi_descriptor_digest": self.descriptor_digest,
            "runtime_abi_inventory_digest": self.inventory_digest,
            "runtime_composition_generation_id": self.runtime_composition_generation_id,
            "runtime_composition_descriptor_digest": (
                self.runtime_composition_descriptor_digest
            ),
            "native_file_count": self.native_file_count,
            "native_total_bytes": self.native_total_bytes,
            "distribution_count": self.distribution_count,
            **{
                name: getattr(self, name)
                for name in _TRUTH_FIELDS
            },
        }


@dataclass(frozen=True)
class RuntimeAbiMaterializationResult:
    binding: RuntimeAbiBinding
    reused_existing_generation: bool


_TRUTH_FIELDS = (
    "artifact_bytes_independently_reverified",
    "declared_pe_metadata_verified",
    "declared_pe_machine_compatible",
    "wheel_tag_compatibility_verified",
    "record_ownership_verified",
    "declared_python_link_abi_verified",
    "native_loader_closure_verified",
    "deterministic_effects_verified",
    "preimport_bootstrap_verified",
    "signature_verified",
    "write_denial_verified",
    "activation_eligible",
    "exact_runtime_closure_verified",
)


def runtime_abi_inventory(
    *, composition_generation_id: str,
    distributions: list[Mapping[str, Any]], native_files: list[Mapping[str, Any]],
) -> dict[str, Any]:
    value = {
        "schema_version": INVENTORY_SCHEMA_VERSION,
        "runtime_composition_generation_id": composition_generation_id,
        "target": dict(TARGET),
        "distributions": [dict(row) for row in distributions],
        "native_files": [dict(row) for row in native_files],
    }
    return validate_runtime_abi_inventory(value)


def validate_runtime_abi_inventory(
    value: object, limits: RuntimeAbiLimits = RuntimeAbiLimits(),
) -> dict[str, Any]:
    limits.validate()
    source = _exact(value, _INVENTORY_KEYS, "RUNTIME_ABI_INVENTORY_INVALID")
    if (
        source.get("schema_version") != INVENTORY_SCHEMA_VERSION
        or not is_digest(source.get("runtime_composition_generation_id"))
        or source.get("target") != TARGET
    ):
        _fail("RUNTIME_ABI_INVENTORY_INVALID")
    distributions = _distributions(source.get("distributions"), limits)
    native_files = _native_files(source.get("native_files"), limits)
    _validate_distribution_bindings(distributions, native_files)
    return {**dict(source), "distributions": distributions, "native_files": native_files}


def runtime_abi_descriptor(
    *, composition_generation_id: str, composition_descriptor_digest: str,
    inventory: Mapping[str, Any],
) -> dict[str, Any]:
    validated = validate_runtime_abi_inventory(inventory)
    if validated["runtime_composition_generation_id"] != composition_generation_id:
        _fail("RUNTIME_ABI_COMPOSITION_BINDING_INVALID")
    if not is_digest(composition_descriptor_digest):
        _fail("RUNTIME_ABI_COMPOSITION_BINDING_INVALID")
    native = validated["native_files"]
    identity = {
        "schema_version": DESCRIPTOR_SCHEMA_VERSION,
        "runtime_composition": {
            "generation_id": composition_generation_id,
            "descriptor_digest": composition_descriptor_digest,
        },
        "target": dict(TARGET),
        "inventory_file": INVENTORY_NAME,
        "inventory_digest": digest_bytes(canonical_json_bytes(validated)),
        "native_file_count": len(native),
        "native_total_bytes": sum(row["size"] for row in native),
        "distribution_count": len(validated["distributions"]),
        "normal_import_library_count": sum(len(row["normal_imports"]) for row in native),
        "delay_import_library_count": sum(len(row["delay_imports"]) for row in native),
        "external_import_library_count": sum(len(row["external_imports"]) for row in native),
        "python_link_file_count": sum(bool(row["reachable_python_libraries"]) for row in native),
    }
    return {
        **identity,
        "generation_id": digest_bytes(canonical_json_bytes(identity)),
        "status": "INERT",
        "artifact_bytes_independently_reverified": True,
        "declared_pe_metadata_verified": True,
        "declared_pe_machine_compatible": True,
        "wheel_tag_compatibility_verified": True,
        "record_ownership_verified": True,
        "declared_python_link_abi_verified": True,
        "native_loader_closure_verified": False,
        "deterministic_effects_verified": False,
        "preimport_bootstrap_verified": False,
        "signature_verified": False,
        "write_denial_verified": False,
        "activation_eligible": False,
        "exact_runtime_closure_verified": False,
    }


def validate_runtime_abi_descriptor(value: object) -> dict[str, Any]:
    source = _exact(value, _DESCRIPTOR_KEYS, "RUNTIME_ABI_DESCRIPTOR_INVALID")
    composition = _exact(
        source.get("runtime_composition"), _COMPOSITION_KEYS,
        "RUNTIME_ABI_COMPOSITION_BINDING_INVALID",
    )
    if (
        source.get("schema_version") != DESCRIPTOR_SCHEMA_VERSION
        or source.get("status") != "INERT" or source.get("target") != TARGET
        or source.get("inventory_file") != INVENTORY_NAME
        or not all(is_digest(composition.get(key)) for key in _COMPOSITION_KEYS)
        or not is_digest(source.get("inventory_digest"))
    ):
        _fail("RUNTIME_ABI_DESCRIPTOR_INVALID")
    numeric = _DESCRIPTOR_KEYS - _TRUTH_FIELDS_SET - {
        "schema_version", "status", "generation_id", "runtime_composition",
        "target", "inventory_file", "inventory_digest",
    }
    if any(type(source.get(name)) is not int or source[name] < 0 for name in numeric):
        _fail("RUNTIME_ABI_DESCRIPTOR_INVALID")
    identity = {key: source[key] for key in source if key not in {"generation_id", "status", *_TRUTH_FIELDS}}
    if (
        source["native_file_count"] == 0
        or source.get("generation_id") != digest_bytes(canonical_json_bytes(identity))
    ):
        _fail("RUNTIME_ABI_GENERATION_ID_INVALID")
    expected = {name: name in _EARNED_TRUE_FIELDS for name in _TRUTH_FIELDS}
    if any(source.get(name) is not truth for name, truth in expected.items()):
        _fail("RUNTIME_ABI_DESCRIPTOR_TRUTH_INVALID")
    return dict(source)


def _distributions(value: object, limits: RuntimeAbiLimits) -> list[dict[str, Any]]:
    if type(value) is not list or not value or len(value) > limits.max_distributions:
        _fail("RUNTIME_ABI_DISTRIBUTIONS_INVALID")
    rows: list[dict[str, Any]] = []
    for value_row in value:
        row = _exact(value_row, _DISTRIBUTION_KEYS, "RUNTIME_ABI_DISTRIBUTION_INVALID")
        dist = canonical_relative_path(row.get("dist_info"))
        tags = _strings(row.get("tags"), "RUNTIME_ABI_WHEEL_TAG_INVALID")
        compatible = _strings(row.get("compatible_tags"), "RUNTIME_ABI_WHEEL_TAG_INVALID")
        if (
            not dist.endswith(".dist-info") or "/" in dist or not tags or not compatible
            or not set(compatible) <= set(tags)
            or not is_digest(row.get("wheel_digest"))
            or not is_digest(row.get("record_digest"))
            or type(row.get("native_file_count")) is not int
            or row["native_file_count"] < 0
            or not is_digest(row.get("native_paths_digest"))
        ):
            _fail("RUNTIME_ABI_DISTRIBUTION_INVALID")
        rows.append({**dict(row), "dist_info": dist, "tags": tags, "compatible_tags": compatible})
    if _ordered_unique([row["dist_info"] for row in rows]) is False:
        _fail("RUNTIME_ABI_DISTRIBUTION_ORDER_INVALID")
    return rows


def _native_files(value: object, limits: RuntimeAbiLimits) -> list[dict[str, Any]]:
    if type(value) is not list or not value or len(value) > limits.max_native_files:
        _fail("RUNTIME_ABI_NATIVE_FILES_INVALID")
    rows = [_native_row(row, limits) for row in value]
    keys = [f"{row['component_role']}:{row['path']}" for row in rows]
    if not _ordered_unique(keys) or sum(row["size"] for row in rows) > limits.max_total_native_bytes:
        _fail("RUNTIME_ABI_NATIVE_ORDER_INVALID")
    return rows


def _native_row(value: object, limits: RuntimeAbiLimits) -> dict[str, Any]:
    row = _exact(value, _NATIVE_KEYS, "RUNTIME_ABI_NATIVE_ROW_INVALID")
    role = row.get("component_role")
    path = canonical_relative_path(row.get("path"))
    suffix = _path_suffix(path)
    _validate_native_identity(row, role, suffix, limits)
    normal = _imports(row.get("normal_imports"))
    delayed = _imports(row.get("delay_imports"))
    strings = {
        name: _strings(row.get(name), "RUNTIME_ABI_NATIVE_ROW_INVALID")
        for name in (
            "internal_imports", "external_imports",
            "direct_python_link_libraries", "reachable_python_libraries",
        )
    }
    for name in (
        "export_names_digest", "export_ordinals_digest",
        "forwarded_export_names_digest", "forwarded_export_ordinals_digest",
    ):
        if not is_digest(row.get(name)):
            _fail("RUNTIME_ABI_NATIVE_ROW_INVALID")
    for name in (
        "export_name_count", "export_ordinal_count",
        "forwarded_export_name_count", "forwarded_export_ordinal_count",
    ):
        if type(row.get(name)) is not int or row[name] < 0:
            _fail("RUNTIME_ABI_NATIVE_ROW_INVALID")
    distribution = row.get("distribution")
    wheel_tag = row.get("compatible_wheel_tag")
    if type(distribution) is not str or type(wheel_tag) is not str:
        _fail("RUNTIME_ABI_NATIVE_ROW_INVALID")
    if (role == DEPENDENCY_ROLE) is not bool(distribution and wheel_tag):
        _fail("RUNTIME_ABI_NATIVE_ROW_INVALID")
    _validate_native_links(row, path, suffix, normal + delayed, strings)
    return {
        **dict(row), "path": path, "normal_imports": normal,
        "delay_imports": delayed, **strings,
    }


def _validate_native_identity(
    row: Mapping[str, Any], role: object, suffix: str, limits: RuntimeAbiLimits,
) -> None:
    if (
        role not in {BASE_ROLE, DEPENDENCY_ROLE}
        or not is_digest(row.get("sha256"))
        or type(row.get("size")) is not int
        or not 0 < row["size"] <= limits.max_native_file_bytes
        or row.get("machine") != TARGET["pe_machine"]
        or row.get("optional_magic") != TARGET["pe_optional_magic"]
        or row.get("image_kind") not in {"dll", "executable"}
        or type(row.get("python_abi_reachable")) is not bool
        or suffix not in {".exe", ".dll", ".pyd"}
        or (row.get("image_kind") == "dll") is not (suffix in {".dll", ".pyd"})
    ):
        _fail("RUNTIME_ABI_NATIVE_ROW_INVALID")


def _validate_native_links(
    row: Mapping[str, Any], path: str, suffix: str,
    imports: list[dict[str, Any]], strings: Mapping[str, list[str]],
) -> None:
    libraries = {item["library"] for item in imports}
    internal = set(strings["internal_imports"])
    external = set(strings["external_imports"])
    direct_python = set(strings["direct_python_link_libraries"])
    reachable_python = set(strings["reachable_python_libraries"])
    if (
        internal & external or internal | external != libraries
        or not direct_python <= internal
        or not direct_python <= {"python3.dll", "python312.dll"}
        or not reachable_python <= {"python3.dll", "python312.dll"}
        or not direct_python <= reachable_python
        or row["python_abi_reachable"] is not bool(reachable_python)
        or (suffix == ".pyd" and not row["python_abi_reachable"])
        or (path.casefold() == "python.exe" and not row["python_abi_reachable"])
    ):
        _fail("RUNTIME_ABI_NATIVE_ROW_INVALID")


def _validate_distribution_bindings(
    distributions: list[dict[str, Any]], native_files: list[dict[str, Any]],
) -> None:
    owners = {row["dist_info"]: row for row in distributions}
    grouped: dict[str, list[str]] = {name: [] for name in owners}
    for row in native_files:
        owner = row["distribution"]
        if not owner:
            continue
        if owner not in owners or row["compatible_wheel_tag"] not in owners[owner]["compatible_tags"]:
            _fail("RUNTIME_ABI_DISTRIBUTION_BINDING_INVALID")
        grouped[owner].append(row["path"])
    for owner, paths in grouped.items():
        paths.sort(key=lambda item: (item.casefold(), item))
        expected = owners[owner]
        if (
            expected["native_file_count"] != len(paths)
            or expected["native_paths_digest"]
            != digest_bytes(canonical_json_bytes(paths))
        ):
            _fail("RUNTIME_ABI_DISTRIBUTION_BINDING_INVALID")


def _path_suffix(path: str) -> str:
    """Return the final suffix without importing host-path semantics."""

    return "." + path.rsplit(".", 1)[1].casefold() if "." in path.rsplit("/", 1)[-1] else ""


def stable_error_code(error: BaseException, fallback: str) -> str:
    """Return only a stable code; never propagate OS paths or private values."""

    candidate = str(error)
    if re.fullmatch(r"[A-Z][A-Z0-9_]*(?::[A-Z][A-Z0-9_]*)*", candidate):
        return candidate
    return fallback


def _imports(value: object) -> list[dict[str, Any]]:
    if type(value) is not list:
        _fail("RUNTIME_ABI_IMPORTS_INVALID")
    rows: list[dict[str, Any]] = []
    for item in value:
        row = _exact(item, _IMPORT_KEYS, "RUNTIME_ABI_IMPORT_INVALID")
        if (
            type(row.get("library")) is not str or not row["library"]
            or row["library"] != row["library"].casefold()
            or any(character in row["library"] for character in "/\\:")
            or not is_digest(row.get("names_digest"))
            or not is_digest(row.get("ordinals_digest"))
            or any(type(row.get(name)) is not int or row[name] < 0 for name in ("name_count", "ordinal_count"))
        ):
            _fail("RUNTIME_ABI_IMPORT_INVALID")
        rows.append(dict(row))
    if not _ordered_unique([row["library"] for row in rows]):
        _fail("RUNTIME_ABI_IMPORT_ORDER_INVALID")
    return rows


def _strings(value: object, code: str) -> list[str]:
    if type(value) is not list or any(type(item) is not str or not item for item in value):
        _fail(code)
    if value != sorted(value, key=lambda item: (item.casefold(), item)) or len(value) != len(set(value)):
        _fail(code)
    return list(value)


def _ordered_unique(values: list[str]) -> bool:
    return values == sorted(values, key=lambda item: (item.casefold(), item)) and len(values) == len(set(value.casefold() for value in values))


def _exact(value: object, keys: frozenset[str], code: str) -> Mapping[str, Any]:
    if type(value) is not dict or frozenset(value) != keys:
        _fail(code)
    return value


_EARNED_TRUE_FIELDS = frozenset(_TRUTH_FIELDS[:6])
_TRUTH_FIELDS_SET = frozenset(_TRUTH_FIELDS)


__all__ = [
    "BASE_ROLE", "DEPENDENCY_ROLE", "DESCRIPTOR_NAME", "DESCRIPTOR_SCHEMA_VERSION",
    "INVENTORY_NAME", "INVENTORY_SCHEMA_VERSION", "RuntimeAbiBinding",
    "RuntimeAbiContractError", "RuntimeAbiLimits", "RuntimeAbiMaterializationResult",
    "TARGET", "runtime_abi_descriptor", "runtime_abi_inventory",
    "stable_error_code", "validate_runtime_abi_descriptor",
    "validate_runtime_abi_inventory",
]
