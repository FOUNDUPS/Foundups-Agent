"""Pure contract for one inert, clean Holo query-runtime candidate manifest.

This module validates declared identity only.  It performs no import, image
load, filesystem traversal, materialization, owner launch, or route mutation.
Those capabilities remain explicit false claims in every valid descriptor.
"""

from __future__ import annotations

from dataclasses import dataclass
import posixpath
import re
import unicodedata
from typing import Any, Mapping

from packaging.version import InvalidVersion, Version

from .reddog_holoindex_dependency_runtime_contract import (
    canonical_json_bytes,
    digest_bytes,
    is_digest,
)
from .reddog_holoindex_query_distribution_graph import DistributionProjection
from .reddog_holoindex_query_runtime_candidate_source import (
    CandidateSourceAuthorityError,
    validate_candidate_source_public_binding,
)
from .reddog_holoindex_query_runtime_candidate_record_contract import (
    CandidateRecordContractError,
    bind_excluded_record_entries,
    validate_excluded_record_entries,
)


INVENTORY_SCHEMA_VERSION = "holoindex_query_runtime_candidate_inventory.v1"
INVENTORY_NAME = "holoindex_query_runtime_candidate_inventory.json"

_INVENTORY_KEYS = frozenset({
    "schema_version", "runtime_composition", "backend_manifest_digest",
    "source_authority", "declaration_digest", "marker_environment",
    "marker_environment_digest",
    "projection_digest", "module_owners", "runtime_volumes",
    "launch_dialect", "components", "root_requirements", "distributions",
    "files", "excluded_record_entries", "dynamic_surfaces",
    "observed_import_trace",
})
_COMPOSITION_KEYS = frozenset({"generation_id", "descriptor_digest"})
_VOLUME_KEYS = frozenset({
    "base_runtime", "dependency_runtime", "temporary_runtime",
})
_LAUNCH_KEYS = frozenset({
    "implementation", "python_full_version", "platform_tag", "flags",
    "standalone_base_runtime_required", "stdlib_transport_required",
    "site_import_allowed", "pth_processing_allowed",
})
_COMPONENT_KEYS = frozenset({
    "base_generation_id", "base_descriptor_digest", "base_tree_digest",
    "dependency_generation_id", "dependency_descriptor_digest",
    "dependency_inventory_digest", "dependency_tree_digest",
})
_REQUIREMENT_KEYS = frozenset({"name", "version", "extras"})
_DISTRIBUTION_KEYS = frozenset({
    "name", "version", "dist_info", "metadata_digest", "wheel_digest",
    "record_digest", "direct", "required_by", "marker_results_digest",
    "excluded_record_entry_count", "excluded_record_entries_digest",
})
_FILE_KEYS = frozenset({"path", "size", "sha256", "distribution", "role"})
_DYNAMIC_KEYS = frozenset({"kind", "owner", "target", "declaration_digest"})
_MODULE_OWNER_KEYS = frozenset({"path", "distribution"})
_TRACE_KEYS = frozenset({
    "trace_digest", "module_count", "native_extension_count",
    "completeness_claimed",
})
_MARKER_KEYS = frozenset({
    "implementation_name", "implementation_version", "os_name",
    "platform_machine", "platform_python_implementation", "platform_release",
    "platform_system", "platform_version", "python_full_version",
    "python_version", "sys_platform",
})

_NORMALIZED_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
_PYTHON_VERSION = re.compile(r"3\.12\.[0-9]+\Z")
_RESERVED = frozenset({
    "con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
})
_FILE_ROLES = frozenset({
    "python_source", "python_extension", "native_library", "resource",
    "distribution_metadata", "declared_subprocess",
})
_DYNAMIC_KINDS = frozenset({
    "import_module", "entry_point", "namespace_portion", "ctypes", "cffi",
    "torch_library", "resource", "subprocess",
})
_CANDIDATE_LIMIT_CEILINGS = {
    "max_root_requirements": 64, "max_distributions": 512,
    "max_files": 100_000, "max_dynamic_surfaces": 4_096,
    "max_file_bytes": 1024 * 1024 * 1024,
    "max_total_bytes": 4 * 1024 * 1024 * 1024, "max_path_bytes": 512,
}


class CandidateContractError(RuntimeError):
    """Stable fail-closed candidate-manifest contract error."""


def _fail(code: str) -> None:
    raise CandidateContractError(code)


@dataclass(frozen=True)
class CandidateLimits:
    max_root_requirements: int = 64
    max_distributions: int = 512
    max_files: int = 100_000
    max_dynamic_surfaces: int = 4_096
    max_file_bytes: int = 1024 * 1024 * 1024
    max_total_bytes: int = 4 * 1024 * 1024 * 1024
    max_path_bytes: int = 512

    def validate(self) -> None:
        if any(
            type(value) is not int or value <= 0
            or value > _CANDIDATE_LIMIT_CEILINGS[name]
            for name, value in vars(self).items()
        ):
            _fail("QUERY_RUNTIME_CANDIDATE_LIMIT_INVALID")


def candidate_inventory(
    *, runtime_composition: Mapping[str, Any], backend_manifest_digest: str,
    source_authority: Mapping[str, Any], declaration_digest: str,
    projection: DistributionProjection,
    runtime_volumes: Mapping[str, Any], launch_dialect: Mapping[str, Any],
    components: Mapping[str, Any], root_requirements: list[Mapping[str, Any]],
    dynamic_surfaces: list[Mapping[str, Any]],
    observed_import_trace: Mapping[str, Any],
    limits: CandidateLimits = CandidateLimits(),
) -> dict[str, Any]:
    """Build and validate one canonical inert candidate inventory."""

    if type(projection) is not DistributionProjection:
        _fail("QUERY_RUNTIME_CANDIDATE_PROJECTION_INVALID")
    return validate_candidate_inventory({
        "schema_version": INVENTORY_SCHEMA_VERSION,
        "runtime_composition": dict(runtime_composition),
        "backend_manifest_digest": backend_manifest_digest,
        "source_authority": dict(source_authority),
        "declaration_digest": declaration_digest,
        "marker_environment": dict(projection.marker_environment),
        "marker_environment_digest": projection.marker_environment_digest,
        "projection_digest": projection.projection_digest,
        "module_owners": [dict(row) for row in projection.module_owners],
        "runtime_volumes": dict(runtime_volumes),
        "launch_dialect": dict(launch_dialect), "components": dict(components),
        "root_requirements": [dict(row) for row in root_requirements],
        "distributions": [dict(row) for row in projection.distributions],
        "files": [dict(row) for row in projection.files],
        "excluded_record_entries": [
            dict(row) for row in projection.excluded_record_entries
        ],
        "dynamic_surfaces": [dict(row) for row in dynamic_surfaces],
        "observed_import_trace": dict(observed_import_trace),
    }, limits)


def validate_candidate_inventory(
    value: object, limits: CandidateLimits = CandidateLimits(),
) -> dict[str, Any]:
    """Validate exact shape, identity, order, and referential closure."""

    limits.validate()
    source = _exact(value, _INVENTORY_KEYS, "QUERY_RUNTIME_CANDIDATE_INVENTORY_INVALID")
    if source.get("schema_version") != INVENTORY_SCHEMA_VERSION:
        _fail("QUERY_RUNTIME_CANDIDATE_INVENTORY_INVALID")
    composition = _digest_mapping(
        source.get("runtime_composition"), _COMPOSITION_KEYS,
        "QUERY_RUNTIME_CANDIDATE_COMPOSITION_INVALID",
    )
    source_authority = _source_binding(source.get("source_authority"))
    for name in (
        "backend_manifest_digest", "declaration_digest",
        "marker_environment_digest", "projection_digest",
    ):
        if not is_digest(source.get(name)):
            _fail("QUERY_RUNTIME_CANDIDATE_BINDING_INVALID")
    volumes = _runtime_volumes(source.get("runtime_volumes"))
    launch = _launch_dialect(source.get("launch_dialect"))
    marker_environment = _marker_environment(source.get("marker_environment"), launch)
    components = _digest_mapping(
        source.get("components"), _COMPONENT_KEYS,
        "QUERY_RUNTIME_CANDIDATE_COMPONENT_INVALID",
    )
    requirements = _requirements(source.get("root_requirements"), limits)
    distributions = _distributions(source.get("distributions"), requirements, limits)
    files = _files(source.get("files"), distributions, limits)
    excluded = _excluded_binding(
        source.get("excluded_record_entries"), distributions, limits,
    )
    module_owners = _module_owners(source.get("module_owners"), files, limits)
    _validate_projection_identity(
        source, distributions, files, excluded, module_owners,
    )
    dynamic = _dynamic_surfaces(source.get("dynamic_surfaces"), distributions, limits)
    trace = _observed_trace(source.get("observed_import_trace"))
    return {
        **dict(source), "runtime_composition": composition,
        "source_authority": source_authority,
        "runtime_volumes": volumes, "launch_dialect": launch,
        "marker_environment": marker_environment,
        "components": components, "root_requirements": requirements,
        "distributions": distributions, "files": files,
        "excluded_record_entries": excluded,
        "module_owners": module_owners, "dynamic_surfaces": dynamic,
        "observed_import_trace": trace,
    }


def _source_binding(value: object) -> dict[str, Any]:
    try:
        return validate_candidate_source_public_binding(value)
    except CandidateSourceAuthorityError:
        _fail("QUERY_RUNTIME_CANDIDATE_SOURCE_BINDING_INVALID")


def _excluded_binding(
    value: object, distributions: list[dict[str, Any]], limits: CandidateLimits,
) -> list[dict[str, Any]]:
    try:
        rows = validate_excluded_record_entries(
            value, distributions, max_files=limits.max_files,
            max_path_bytes=limits.max_path_bytes,
            max_file_bytes=limits.max_file_bytes,
        )
        bind_excluded_record_entries(distributions, rows)
        return rows
    except CandidateRecordContractError as exc:
        _fail(str(exc))


def _runtime_volumes(value: object) -> dict[str, str]:
    source = _exact(value, _VOLUME_KEYS, "QUERY_RUNTIME_CANDIDATE_VOLUME_INVALID")
    if any(source.get(name) not in {"O", "E"} for name in _VOLUME_KEYS):
        _fail("QUERY_RUNTIME_CANDIDATE_VOLUME_INVALID")
    return dict(source)


def _launch_dialect(value: object) -> dict[str, Any]:
    source = _exact(value, _LAUNCH_KEYS, "QUERY_RUNTIME_CANDIDATE_LAUNCH_INVALID")
    expected = {
        "implementation": "cpython", "platform_tag": "win_amd64",
        "flags": ["-I", "-S", "-B"], "standalone_base_runtime_required": True,
        "stdlib_transport_required": True, "site_import_allowed": False,
        "pth_processing_allowed": False,
    }
    if (
        any(source.get(name) != wanted for name, wanted in expected.items())
        or type(source.get("python_full_version")) is not str
        or _PYTHON_VERSION.fullmatch(source["python_full_version"]) is None
    ):
        _fail("QUERY_RUNTIME_CANDIDATE_LAUNCH_INVALID")
    return dict(source)


def _marker_environment(value: object, launch: Mapping[str, Any]) -> dict[str, str]:
    source = _exact(
        value, _MARKER_KEYS, "QUERY_RUNTIME_CANDIDATE_MARKER_ENVIRONMENT_INVALID"
    )
    expected = {
        "implementation_name": "cpython", "implementation_version": launch["python_full_version"],
        "os_name": "nt", "platform_machine": "AMD64",
        "platform_python_implementation": "CPython", "platform_system": "Windows",
        "python_full_version": launch["python_full_version"],
        "python_version": "3.12", "sys_platform": "win32",
    }
    if (
        any(source.get(name) != wanted for name, wanted in expected.items())
        or any(type(item) is not str or not item or len(item) > 256 for item in source.values())
    ):
        _fail("QUERY_RUNTIME_CANDIDATE_MARKER_ENVIRONMENT_INVALID")
    return dict(source)


def _requirements(value: object, limits: CandidateLimits) -> list[dict[str, Any]]:
    if type(value) is not list or not value or len(value) > limits.max_root_requirements:
        _fail("QUERY_RUNTIME_CANDIDATE_REQUIREMENT_INVALID")
    rows = [_requirement(row) for row in value]
    if not _ordered_unique([row["name"] for row in rows]):
        _fail("QUERY_RUNTIME_CANDIDATE_REQUIREMENT_ORDER_INVALID")
    return rows


def _requirement(value: object) -> dict[str, Any]:
    row = _exact(value, _REQUIREMENT_KEYS, "QUERY_RUNTIME_CANDIDATE_REQUIREMENT_INVALID")
    name, version = _name(row.get("name")), row.get("version")
    extras = row.get("extras")
    if (
        not _valid_version(version)
        or type(extras) is not list or not _ordered_unique(extras)
        or any(_name(extra) != extra for extra in extras)
    ):
        _fail("QUERY_RUNTIME_CANDIDATE_REQUIREMENT_INVALID")
    return {"name": name, "version": version, "extras": list(extras)}


def _distributions(
    value: object, requirements: list[dict[str, Any]], limits: CandidateLimits,
) -> list[dict[str, Any]]:
    if type(value) is not list or not value or len(value) > limits.max_distributions:
        _fail("QUERY_RUNTIME_CANDIDATE_DISTRIBUTION_INVALID")
    rows = [_distribution(row) for row in value]
    names = [row["name"] for row in rows]
    if not _ordered_unique(names):
        _fail("QUERY_RUNTIME_CANDIDATE_DISTRIBUTION_ORDER_INVALID")
    known = set(names)
    root_versions = {row["name"]: row["version"] for row in requirements}
    roots = set(root_versions)
    if not roots <= known:
        _fail("QUERY_RUNTIME_CANDIDATE_DISTRIBUTION_CLOSURE_INVALID")
    for row in rows:
        if (
            not set(row["required_by"]) <= known
            or row["name"] in row["required_by"]
            or row["direct"] is not (row["name"] in roots)
            or (
                row["direct"]
                and Version(row["version"]) != Version(root_versions[row["name"]])
            )
            or (not row["direct"] and not row["required_by"])
        ):
            _fail("QUERY_RUNTIME_CANDIDATE_DISTRIBUTION_CLOSURE_INVALID")
    reachable = set(roots)
    while True:
        admitted = {
            row["name"] for row in rows if set(row["required_by"]) & reachable
        }
        expanded = reachable | admitted
        if expanded == reachable:
            break
        reachable = expanded
    if reachable != known:
        _fail("QUERY_RUNTIME_CANDIDATE_DISTRIBUTION_CLOSURE_INVALID")
    return rows


def _distribution(value: object) -> dict[str, Any]:
    row = _exact(
        value, _DISTRIBUTION_KEYS, "QUERY_RUNTIME_CANDIDATE_DISTRIBUTION_INVALID"
    )
    name, version = _name(row.get("name")), row.get("version")
    owners = row.get("required_by")
    if (
        not _valid_version(version)
        or type(row.get("direct")) is not bool
        or type(owners) is not list or not _ordered_unique(owners)
        or any(_name(owner) != owner for owner in owners)
        or any(not is_digest(row.get(field)) for field in (
            "metadata_digest", "wheel_digest", "record_digest",
            "marker_results_digest", "excluded_record_entries_digest",
        ))
        or type(row.get("excluded_record_entry_count")) is not int
        or row["excluded_record_entry_count"] < 0
    ):
        _fail("QUERY_RUNTIME_CANDIDATE_DISTRIBUTION_INVALID")
    dist_info = _path(row.get("dist_info"))
    if "/" in dist_info or not dist_info.endswith(".dist-info"):
        _fail("QUERY_RUNTIME_CANDIDATE_DISTRIBUTION_INVALID")
    return {
        **dict(row), "name": name, "version": version,
        "dist_info": dist_info, "required_by": list(owners),
    }


def _files(
    value: object, distributions: list[dict[str, Any]], limits: CandidateLimits,
) -> list[dict[str, Any]]:
    if type(value) is not list or not value or len(value) > limits.max_files:
        _fail("QUERY_RUNTIME_CANDIDATE_FILE_INVALID")
    rows = [_file(row, limits) for row in value]
    if not _ordered_unique([row["path"] for row in rows]):
        _fail("QUERY_RUNTIME_CANDIDATE_FILE_ORDER_INVALID")
    owners = {row["name"] for row in distributions}
    if any(row["distribution"] not in owners for row in rows):
        _fail("QUERY_RUNTIME_CANDIDATE_FILE_OWNER_INVALID")
    if {row["distribution"] for row in rows} != owners:
        _fail("QUERY_RUNTIME_CANDIDATE_FILE_OWNER_INVALID")
    if sum(row["size"] for row in rows) > limits.max_total_bytes:
        _fail("QUERY_RUNTIME_CANDIDATE_FILE_LIMIT_INVALID")
    _validate_distribution_metadata_rows(rows, distributions)
    return rows


def _file(value: object, limits: CandidateLimits) -> dict[str, Any]:
    row = _exact(value, _FILE_KEYS, "QUERY_RUNTIME_CANDIDATE_FILE_INVALID")
    path, owner = _path(row.get("path")), _name(row.get("distribution"))
    if (
        len(path.encode("utf-8")) > limits.max_path_bytes
        or type(row.get("size")) is not int or row["size"] < 0
        or row["size"] > limits.max_file_bytes
        or not is_digest(row.get("sha256")) or row.get("role") not in _FILE_ROLES
        or not _role_matches_path(path, row.get("role"))
    ):
        _fail("QUERY_RUNTIME_CANDIDATE_FILE_INVALID")
    return {**dict(row), "path": path, "distribution": owner}


def _role_matches_path(path: str, role: object) -> bool:
    suffix = posixpath.splitext(path)[1].casefold()
    if ".dist-info/" in path.casefold():
        expected = "distribution_metadata"
    else:
        expected = {
            ".py": "python_source", ".pyd": "python_extension",
            ".dll": "native_library", ".exe": "declared_subprocess",
        }.get(suffix, "resource")
    return role == expected


def _validate_distribution_metadata_rows(
    files: list[dict[str, Any]], distributions: list[dict[str, Any]],
) -> None:
    by_path = {row["path"].casefold(): row for row in files}
    for distribution in distributions:
        prefix = distribution["dist_info"]
        expected = {
            f"{prefix}/METADATA": distribution["metadata_digest"],
            f"{prefix}/WHEEL": distribution["wheel_digest"],
            f"{prefix}/RECORD": distribution["record_digest"],
        }
        for path, digest in expected.items():
            row = by_path.get(path.casefold())
            if (
                row is None or row["distribution"] != distribution["name"]
                or row["sha256"] != digest or row["role"] != "distribution_metadata"
            ):
                _fail("QUERY_RUNTIME_CANDIDATE_DISTRIBUTION_METADATA_INVALID")


def _module_owners(
    value: object, files: list[dict[str, Any]], limits: CandidateLimits,
) -> list[dict[str, str]]:
    if type(value) is not list or not value or len(value) > limits.max_dynamic_surfaces:
        _fail("QUERY_RUNTIME_CANDIDATE_MODULE_OWNER_INVALID")
    rows: list[dict[str, str]] = []
    file_owners = {row["path"].casefold(): row["distribution"] for row in files}
    for item in value:
        row = _exact(item, _MODULE_OWNER_KEYS, "QUERY_RUNTIME_CANDIDATE_MODULE_OWNER_INVALID")
        path, distribution = _path(row.get("path")), _name(row.get("distribution"))
        if file_owners.get(path.casefold()) != distribution:
            _fail("QUERY_RUNTIME_CANDIDATE_MODULE_OWNER_INVALID")
        rows.append({"path": path, "distribution": distribution})
    if not _ordered_unique([row["path"] for row in rows]):
        _fail("QUERY_RUNTIME_CANDIDATE_MODULE_OWNER_INVALID")
    return rows


def _validate_projection_identity(
    source: Mapping[str, Any], distributions: list[dict[str, Any]],
    files: list[dict[str, Any]], excluded: list[dict[str, Any]],
    module_owners: list[dict[str, str]],
) -> None:
    marker_digest = digest_bytes(canonical_json_bytes(source["marker_environment"]))
    identity = {
        "distributions": distributions,
        "files": files,
        "excluded_record_entries": excluded,
        "module_owners": module_owners,
        "marker_environment_digest": marker_digest,
    }
    if (
        source["marker_environment_digest"] != marker_digest
        or source["projection_digest"] != digest_bytes(canonical_json_bytes(identity))
    ):
        _fail("QUERY_RUNTIME_CANDIDATE_PROJECTION_INVALID")


def _dynamic_surfaces(
    value: object, distributions: list[dict[str, Any]], limits: CandidateLimits,
) -> list[dict[str, Any]]:
    if type(value) is not list or len(value) > limits.max_dynamic_surfaces:
        _fail("QUERY_RUNTIME_CANDIDATE_DYNAMIC_SURFACE_INVALID")
    rows = [_dynamic_surface(row) for row in value]
    keys = [f"{row['kind']}:{row['owner']}:{row['target']}" for row in rows]
    if not _ordered_unique(keys):
        _fail("QUERY_RUNTIME_CANDIDATE_DYNAMIC_SURFACE_ORDER_INVALID")
    owners = {row["name"] for row in distributions}
    if any(row["owner"] not in owners for row in rows):
        _fail("QUERY_RUNTIME_CANDIDATE_DYNAMIC_SURFACE_OWNER_INVALID")
    return rows


def _dynamic_surface(value: object) -> dict[str, Any]:
    row = _exact(value, _DYNAMIC_KEYS, "QUERY_RUNTIME_CANDIDATE_DYNAMIC_SURFACE_INVALID")
    owner, target = _name(row.get("owner")), row.get("target")
    if (
        row.get("kind") not in _DYNAMIC_KINDS or type(target) is not str
        or not target or len(target.encode("utf-8")) > 1024
        or unicodedata.normalize("NFC", target) != target
        or any(unicodedata.category(char) in {"Cc", "Cf", "Cs"} for char in target)
        or not is_digest(row.get("declaration_digest"))
    ):
        _fail("QUERY_RUNTIME_CANDIDATE_DYNAMIC_SURFACE_INVALID")
    return {**dict(row), "owner": owner}


def _observed_trace(value: object) -> dict[str, Any]:
    row = _exact(value, _TRACE_KEYS, "QUERY_RUNTIME_CANDIDATE_TRACE_INVALID")
    if (
        not is_digest(row.get("trace_digest"))
        or type(row.get("module_count")) is not int or row["module_count"] < 0
        or type(row.get("native_extension_count")) is not int
        or row["native_extension_count"] < 0
        or row["native_extension_count"] > row["module_count"]
        or row.get("completeness_claimed") is not False
    ):
        _fail("QUERY_RUNTIME_CANDIDATE_TRACE_INVALID")
    return dict(row)


def _digest_mapping(value: object, keys: frozenset[str], code: str) -> dict[str, str]:
    source = _exact(value, keys, code)
    if any(not is_digest(source.get(name)) for name in keys):
        _fail(code)
    return dict(source)


def _name(value: object) -> str:
    if type(value) is not str:
        _fail("QUERY_RUNTIME_CANDIDATE_NAME_INVALID")
    normalized = re.sub(r"[-_.]+", "-", value).lower()
    if value != normalized or _NORMALIZED_NAME.fullmatch(value) is None:
        _fail("QUERY_RUNTIME_CANDIDATE_NAME_INVALID")
    return value


def _valid_version(value: object) -> bool:
    if type(value) is not str or not value or len(value) > 256:
        return False
    try:
        Version(value)
        return True
    except InvalidVersion:
        return False


def _path(value: object) -> str:
    if type(value) is not str or not value or len(value) > 2048:
        _fail("QUERY_RUNTIME_CANDIDATE_PATH_INVALID")
    parts = value.split("/")
    if (
        value.startswith("/") or "\\" in value or ":" in value
        or posixpath.normpath(value) != value
        or unicodedata.normalize("NFC", value) != value
        or any(part in {"", ".", ".."} or part[-1:] in {" ", "."} for part in parts)
        or any(part.split(".", 1)[0].casefold() in _RESERVED for part in parts)
        or any(unicodedata.category(char) in {"Cc", "Cf", "Cs"} for char in value)
    ):
        _fail("QUERY_RUNTIME_CANDIDATE_PATH_INVALID")
    return value


def _exact(value: object, keys: frozenset[str], code: str) -> dict[str, Any]:
    if type(value) is not dict or frozenset(value) != keys:
        _fail(code)
    return value


def _ordered_unique(values: list[str]) -> bool:
    if any(type(value) is not str for value in values):
        return False
    keys = [unicodedata.normalize("NFC", value).casefold() for value in values]
    return keys == sorted(keys) and len(keys) == len(set(keys))


__all__ = [
    "CandidateContractError", "CandidateLimits", "INVENTORY_NAME",
    "INVENTORY_SCHEMA_VERSION", "candidate_inventory", "validate_candidate_inventory",
]
