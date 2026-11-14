"""Positive distribution projection for an inert Holo query candidate.

The graph operates only on content-bound dependency-inventory rows and caller
bytes.  It imports no candidate package and claims no loader completeness.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Callable, Mapping, Sequence

from packaging.markers import Marker
from packaging.requirements import InvalidRequirement, Requirement
from packaging.version import InvalidVersion, Version

from .reddog_holoindex_dependency_runtime_contract import (
    canonical_json_bytes,
    canonical_relative_path,
    digest_bytes,
    is_digest,
)
from .reddog_holoindex_query_distribution_metadata import (
    DistributionCatalog,
    DistributionMetadata,
    DistributionMetadataError,
    DistributionMetadataLimits,
    bind_selected_distribution_records,
    build_distribution_catalog,
    normalize_distribution_name,
    read_bound_payload,
    target_python_satisfies,
    validate_selected_wheel,
)


_TARGET_ENVIRONMENT_KEYS = frozenset({
    "implementation_name", "implementation_version", "os_name",
    "platform_machine", "platform_python_implementation", "platform_release",
    "platform_system", "platform_version", "python_full_version",
    "python_version", "sys_platform",
})
_ROW_KEYS = frozenset({"path", "size", "sha256", "role"})
_FORBIDDEN_NAMES = frozenset({"sitecustomize.py", "usercustomize.py"})
_FORBIDDEN_SUFFIXES = frozenset({
    ".bat", ".cmd", ".com", ".egg-link", ".ps1", ".pth", ".pyc", ".pyw", ".zip",
})
_NATIVE_SUFFIXES = frozenset({".pyd", ".dll"})
_GRAPH_LIMIT_CEILINGS = {
    "max_distributions": 512, "max_files": 100_000,
    "max_record_rows": 500_000, "max_total_record_rows": 1_000_000,
    "max_metadata_bytes": 4 * 1024 * 1024,
    "max_total_metadata_bytes": 128 * 1024 * 1024,
    "max_requirement_edges": 8_192, "max_module_origins": 4_096,
    "max_declared_subprocesses": 128, "max_extras_per_distribution": 64,
    "max_selected_file_bytes": 1024 * 1024 * 1024,
    "max_total_selected_bytes": 4 * 1024 * 1024 * 1024,
}


class DistributionGraphError(RuntimeError):
    """Stable fail-closed distribution projection error."""


def _fail(code: str) -> None:
    raise DistributionGraphError(code)


@dataclass(frozen=True)
class DistributionGraphLimits:
    max_distributions: int = 512
    max_files: int = 100_000
    max_record_rows: int = 500_000
    max_total_record_rows: int = 1_000_000
    max_metadata_bytes: int = 4 * 1024 * 1024
    max_total_metadata_bytes: int = 128 * 1024 * 1024
    max_requirement_edges: int = 8_192
    max_module_origins: int = 4_096
    max_declared_subprocesses: int = 128
    max_extras_per_distribution: int = 64
    max_selected_file_bytes: int = 1024 * 1024 * 1024
    max_total_selected_bytes: int = 4 * 1024 * 1024 * 1024

    def validate(self) -> None:
        if any(
            type(value) is not int or value <= 0
            or value > _GRAPH_LIMIT_CEILINGS[name]
            for name, value in vars(self).items()
        ):
            _fail("QUERY_DISTRIBUTION_GRAPH_LIMIT_INVALID")


@dataclass(frozen=True)
class DistributionProjection:
    distributions: list[Mapping[str, Any]]
    files: list[Mapping[str, Any]]
    excluded_record_entries: list[Mapping[str, Any]]
    module_owners: list[Mapping[str, str]]
    marker_environment: Mapping[str, str]
    marker_environment_digest: str
    projection_digest: str


def derive_distribution_projection(
    *, inventory_rows: Sequence[Mapping[str, Any]],
    read_bytes: Callable[[str], bytes], root_requirements: Sequence[Mapping[str, Any]],
    module_origins: Sequence[str], marker_environment: Mapping[str, str],
    declared_subprocess_paths: Sequence[str] = (),
    limits: DistributionGraphLimits = DistributionGraphLimits(),
) -> DistributionProjection:
    """Derive one exact, bounded selected-RECORD payload projection."""

    limits.validate()
    inventory = _inventory_index(inventory_rows, limits)
    environment = _marker_environment(marker_environment)
    roots = _root_requirements(root_requirements, limits)
    subprocesses = _ordered_paths(
        declared_subprocess_paths, limits.max_declared_subprocesses, False,
    )
    metadata_limits = DistributionMetadataLimits(
        limits.max_distributions, limits.max_record_rows,
        limits.max_total_record_rows, limits.max_metadata_bytes,
        limits.max_total_metadata_bytes,
    )
    try:
        catalog = build_distribution_catalog(
            inventory, read_bytes, metadata_limits,
        )
    except DistributionMetadataError as exc:
        _fail(str(exc))
    selected, required_by, marker_rows = _requires_dist_closure(
        roots, catalog.entries, environment, limits,
    )
    try:
        catalog = bind_selected_distribution_records(
            catalog, selected, inventory, metadata_limits,
        )
    except DistributionMetadataError as exc:
        _fail(str(exc))
    owners = _module_owners(module_origins, catalog, inventory, limits)
    if any(row["distribution"] not in selected for row in owners):
        _fail("QUERY_DISTRIBUTION_MODULE_OWNER_OUTSIDE_CLOSURE")
    try:
        distributions, files, excluded = _selected_payload(
            selected, required_by, marker_rows, roots, catalog, inventory,
            read_bytes, subprocesses, limits,
        )
    except DistributionMetadataError as exc:
        _fail(str(exc))
    return _projection(distributions, files, excluded, owners, environment)


def _projection(
    distributions: list[Mapping[str, Any]], files: list[Mapping[str, Any]],
    excluded: list[Mapping[str, Any]], owners: list[Mapping[str, str]],
    environment: Mapping[str, str],
) -> DistributionProjection:
    marker_digest = digest_bytes(canonical_json_bytes(environment))
    identity = {
        "distributions": distributions,
        "files": files,
        "excluded_record_entries": excluded,
        "module_owners": owners,
        "marker_environment_digest": marker_digest,
    }
    return DistributionProjection(
        distributions, files, excluded, owners, environment, marker_digest,
        digest_bytes(canonical_json_bytes(identity)),
    )


def _inventory_index(
    rows: Sequence[Mapping[str, Any]], limits: DistributionGraphLimits,
) -> dict[str, dict[str, Any]]:
    if not isinstance(rows, (list, tuple)) or not rows or len(rows) > limits.max_files:
        _fail("QUERY_DISTRIBUTION_INVENTORY_INVALID")
    result: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for value in rows:
        if type(value) is not dict or frozenset(value) != _ROW_KEYS:
            _fail("QUERY_DISTRIBUTION_INVENTORY_INVALID")
        path = _path(value.get("path"), "QUERY_DISTRIBUTION_INVENTORY_PATH_INVALID")
        size = value.get("size")
        if (
            type(size) is not int or size < 0 or not is_digest(value.get("sha256"))
            or value.get("role") != "dependency_payload"
        ):
            _fail("QUERY_DISTRIBUTION_INVENTORY_INVALID")
        key = path.casefold()
        if key in result:
            _fail("QUERY_DISTRIBUTION_INVENTORY_COLLISION")
        result[key] = {**dict(value), "path": path}
        order.append(key)
    if order != sorted(order):
        _fail("QUERY_DISTRIBUTION_INVENTORY_ORDER_INVALID")
    return result


def _root_requirements(
    values: Sequence[Mapping[str, Any]], limits: DistributionGraphLimits,
) -> dict[str, tuple[str, tuple[str, ...]]]:
    if not isinstance(values, (list, tuple)) or not values or len(values) > limits.max_distributions:
        _fail("QUERY_DISTRIBUTION_ROOT_REQUIREMENT_INVALID")
    result: dict[str, tuple[str, tuple[str, ...]]] = {}
    order: list[str] = []
    for value in values:
        if type(value) is not dict or frozenset(value) != {"name", "version", "extras"}:
            _fail("QUERY_DISTRIBUTION_ROOT_REQUIREMENT_INVALID")
        name = _name(value["name"])
        version, extras = value["version"], value["extras"]
        if type(version) is not str or type(extras) is not list:
            _fail("QUERY_DISTRIBUTION_ROOT_REQUIREMENT_INVALID")
        try:
            Version(version)
        except InvalidVersion:
            _fail("QUERY_DISTRIBUTION_ROOT_REQUIREMENT_INVALID")
        normalized = tuple(_name(extra) for extra in extras)
        if (
            len(normalized) > limits.max_extras_per_distribution
            or tuple(sorted(normalized)) != normalized or len(set(normalized)) != len(normalized)
        ):
            _fail("QUERY_DISTRIBUTION_ROOT_REQUIREMENT_INVALID")
        if name in result:
            _fail("QUERY_DISTRIBUTION_ROOT_REQUIREMENT_INVALID")
        result[name], order = (version, normalized), [*order, name]
    if order != sorted(order):
        _fail("QUERY_DISTRIBUTION_ROOT_REQUIREMENT_ORDER_INVALID")
    return result


def _requires_dist_closure(
    roots: Mapping[str, tuple[str, tuple[str, ...]]],
    catalog: Mapping[str, DistributionMetadata], environment: Mapping[str, str],
    limits: DistributionGraphLimits,
) -> tuple[set[str], dict[str, set[str]], dict[str, list[Mapping[str, Any]]]]:
    _validate_root_versions_and_extras(roots, catalog)
    selected: set[str] = set()
    required_by: dict[str, set[str]] = {name: set() for name in roots}
    active_extras = {name: set(extras) for name, (_version, extras) in roots.items()}
    pending = list(reversed(sorted(roots)))
    marker_rows: dict[str, list[Mapping[str, Any]]] = {}
    edge_count = 0
    while pending:
        name = pending.pop()
        entry = catalog.get(name)
        if entry is None:
            _fail("QUERY_DISTRIBUTION_REQUIRED_MISSING")
        extras = active_extras.get(name, set())
        if not extras <= set(entry.provides_extras):
            _fail("QUERY_DISTRIBUTION_EXTRA_UNPROVIDED")
        if not target_python_satisfies(entry, environment["python_full_version"]):
            _fail("QUERY_DISTRIBUTION_REQUIRES_PYTHON_UNSATISFIED")
        signature = (name, tuple(sorted(extras)))
        previous = marker_rows.get(name)
        if name in selected and previous and previous[0].get("_signature") == signature:
            continue
        selected.add(name)
        decisions: list[Mapping[str, Any]] = [{"_signature": signature}]
        for raw in entry.requirements:
            edge_count += 1
            if edge_count > limits.max_requirement_edges:
                _fail("QUERY_DISTRIBUTION_REQUIREMENT_LIMIT_EXCEEDED")
            requirement = _requirement(raw)
            accepted = _marker_accepts(requirement.marker, environment, extras)
            decisions.append({
                "requirement": str(requirement), "selected": accepted,
                "active_extras": sorted(extras),
            })
            if accepted:
                _add_dependency(
                    name, requirement, catalog, active_extras, required_by, pending, selected,
                    limits,
                )
        marker_rows[name] = decisions
    return selected, required_by, marker_rows


def _add_dependency(
    parent: str, requirement: Requirement,
    catalog: Mapping[str, DistributionMetadata], active_extras: dict[str, set[str]],
    required_by: dict[str, set[str]], pending: list[str], selected: set[str],
    limits: DistributionGraphLimits,
) -> None:
    try:
        dependency = normalize_distribution_name(requirement.name)
    except DistributionMetadataError:
        _fail("QUERY_DISTRIBUTION_NAME_INVALID")
    target = catalog.get(dependency)
    if target is None:
        _fail("QUERY_DISTRIBUTION_REQUIRED_MISSING")
    if requirement.specifier and Version(target.version) not in requirement.specifier:
        _fail("QUERY_DISTRIBUTION_VERSION_UNSATISFIED")
    requested = {_name(extra) for extra in requirement.extras}
    if len(requested) > limits.max_extras_per_distribution or not requested <= set(target.provides_extras):
        _fail("QUERY_DISTRIBUTION_EXTRA_UNPROVIDED")
    required_by.setdefault(dependency, set()).add(parent)
    before = set(active_extras.get(dependency, set()))
    active_extras.setdefault(dependency, set()).update(requested)
    if dependency not in selected or before != active_extras[dependency]:
        pending.append(dependency)


def _module_owners(
    origins: Sequence[str], catalog: DistributionCatalog,
    inventory: Mapping[str, Mapping[str, Any]], limits: DistributionGraphLimits,
) -> list[Mapping[str, str]]:
    paths = _ordered_paths(origins, limits.max_module_origins, True)
    result: list[Mapping[str, str]] = []
    for origin in paths:
        if origin.casefold() not in inventory:
            _fail("QUERY_DISTRIBUTION_MODULE_ORIGIN_UNBOUND")
        owners = catalog.owners_by_path.get(origin.casefold(), ())
        if len(owners) != 1:
            _fail("QUERY_DISTRIBUTION_MODULE_OWNER_MISSING" if not owners else "QUERY_DISTRIBUTION_MODULE_OWNER_AMBIGUOUS")
        result.append({"path": origin, "distribution": owners[0]})
    return result


def _selected_payload(
    selected: set[str], required_by: Mapping[str, set[str]],
    marker_rows: Mapping[str, list[Mapping[str, Any]]],
    roots: Mapping[str, tuple[str, tuple[str, ...]]], catalog: DistributionCatalog,
    inventory: Mapping[str, Mapping[str, Any]], read_bytes: Callable[[str], bytes],
    subprocesses: tuple[str, ...], limits: DistributionGraphLimits,
) -> tuple[
    list[Mapping[str, Any]], list[Mapping[str, Any]], list[Mapping[str, Any]],
]:
    paths = sorted(
        {path for name in selected for path in catalog.entries[name].record_paths},
        key=str.casefold,
    )
    if len(paths) > limits.max_files:
        _fail("QUERY_DISTRIBUTION_FILE_LIMIT_EXCEEDED")
    if any(inventory[path.casefold()]["size"] > limits.max_selected_file_bytes for path in paths):
        _fail("QUERY_DISTRIBUTION_PAYLOAD_LIMIT_EXCEEDED")
    if sum(inventory[path.casefold()]["size"] for path in paths) > limits.max_total_selected_bytes:
        _fail("QUERY_DISTRIBUTION_PAYLOAD_LIMIT_EXCEEDED")
    rows, used_subprocesses = _selected_rows(
        paths, selected, catalog, inventory, read_bytes, subprocesses, limits,
    )
    if set(subprocesses) != used_subprocesses:
        _fail("QUERY_DISTRIBUTION_SUBPROCESS_DECLARATION_UNUSED")
    distributions = []
    excluded: list[Mapping[str, Any]] = []
    for name in sorted(selected):
        entry = catalog.entries[name]
        validate_selected_wheel(entry, inventory, read_bytes, limits.max_metadata_bytes)
        decisions = [row for row in marker_rows[name] if "requirement" in row]
        distribution_excluded = [
            {**dict(row), "distribution": name} for row in entry.excluded_record_rows
        ]
        excluded.extend(distribution_excluded)
        distributions.append({
            "name": name, "version": entry.version, "dist_info": entry.dist_info,
            "metadata_digest": inventory[entry.metadata_path.casefold()]["sha256"],
            "wheel_digest": inventory[entry.wheel_path.casefold()]["sha256"],
            "record_digest": inventory[entry.record_path.casefold()]["sha256"],
            "direct": name in roots, "required_by": sorted(required_by.get(name, set())),
            "marker_results_digest": digest_bytes(canonical_json_bytes(decisions)),
            "excluded_record_entry_count": len(distribution_excluded),
            "excluded_record_entries_digest": digest_bytes(
                canonical_json_bytes(distribution_excluded)
            ),
        })
    return distributions, rows, sorted(
        excluded, key=lambda row: (str(row["path"]).casefold(), str(row["distribution"])),
    )


def _selected_rows(
    paths: Sequence[str], selected: set[str], catalog: DistributionCatalog,
    inventory: Mapping[str, Mapping[str, Any]], read_bytes: Callable[[str], bytes],
    subprocesses: tuple[str, ...], limits: DistributionGraphLimits,
) -> tuple[list[Mapping[str, Any]], set[str]]:
    rows: list[Mapping[str, Any]] = []
    used_subprocesses: set[str] = set()
    for path in paths:
        owners = catalog.owners_by_path.get(path.casefold(), ())
        if len(owners) != 1 or owners[0] not in selected:
            _fail("QUERY_DISTRIBUTION_FILE_OWNER_AMBIGUOUS")
        payload = read_bound_payload(
            path, inventory, read_bytes, limits.max_selected_file_bytes,
        )
        role = _file_role(path, payload, subprocesses)
        if role == "declared_subprocess":
            used_subprocesses.add(path)
        bound = inventory[path.casefold()]
        rows.append({
            "path": path, "size": bound["size"], "sha256": bound["sha256"],
            "distribution": owners[0], "role": role,
        })
    return rows, used_subprocesses


def _file_role(path: str, payload: bytes, subprocesses: tuple[str, ...]) -> str:
    pure = PurePosixPath(path)
    suffix = pure.suffix.casefold()
    if pure.name.casefold() in _FORBIDDEN_NAMES or suffix in _FORBIDDEN_SUFFIXES:
        _fail("QUERY_DISTRIBUTION_STARTUP_SURFACE_FORBIDDEN")
    if any(part.casefold().endswith(".egg") for part in pure.parts):
        _fail("QUERY_DISTRIBUTION_STARTUP_SURFACE_FORBIDDEN")
    if path.casefold().endswith(".dist-info/direct_url.json"):
        _fail("QUERY_DISTRIBUTION_DIRECT_INSTALL_FORBIDDEN")
    if payload.startswith(b"MZ") and suffix not in {*_NATIVE_SUFFIXES, ".exe"}:
        _fail("QUERY_DISTRIBUTION_EXECUTABLE_SUFFIX_MISMATCH")
    if suffix == ".exe":
        if path not in subprocesses:
            _fail("QUERY_DISTRIBUTION_SUBPROCESS_UNDECLARED")
        return "declared_subprocess"
    if ".dist-info/" in path.casefold():
        return "distribution_metadata"
    if suffix == ".py":
        return "python_source"
    if suffix == ".pyd":
        return "python_extension"
    if suffix == ".dll":
        return "native_library"
    return "resource"


def _marker_environment(value: Mapping[str, str]) -> dict[str, str]:
    if type(value) is not dict or frozenset(value) != _TARGET_ENVIRONMENT_KEYS:
        _fail("QUERY_DISTRIBUTION_MARKER_ENVIRONMENT_INVALID")
    if any(type(item) is not str or not item or len(item) > 256 for item in value.values()):
        _fail("QUERY_DISTRIBUTION_MARKER_ENVIRONMENT_INVALID")
    expected = {
        "implementation_name": "cpython", "os_name": "nt",
        "platform_machine": "AMD64", "platform_python_implementation": "CPython",
        "platform_system": "Windows", "python_version": "3.12", "sys_platform": "win32",
    }
    if any(value.get(key) != wanted for key, wanted in expected.items()):
        _fail("QUERY_DISTRIBUTION_MARKER_ENVIRONMENT_INVALID")
    try:
        full = Version(value["python_full_version"])
        implementation = Version(value["implementation_version"])
    except InvalidVersion:
        _fail("QUERY_DISTRIBUTION_MARKER_ENVIRONMENT_INVALID")
    if full.release[:2] != (3, 12) or implementation != full:
        _fail("QUERY_DISTRIBUTION_MARKER_ENVIRONMENT_INVALID")
    return dict(value)


def _marker_accepts(
    marker: Marker | None, environment: Mapping[str, str], extras: set[str],
) -> bool:
    if marker is None:
        return True
    candidates = sorted(extras) if extras else [""]
    try:
        return any(marker.evaluate({**dict(environment), "extra": extra}) for extra in candidates)
    except Exception:
        _fail("QUERY_DISTRIBUTION_MARKER_INVALID")


def _validate_root_versions_and_extras(
    roots: Mapping[str, tuple[str, tuple[str, ...]]],
    catalog: Mapping[str, DistributionMetadata],
) -> None:
    for name, (version, extras) in roots.items():
        entry = catalog.get(name)
        if entry is None:
            _fail("QUERY_DISTRIBUTION_REQUIRED_MISSING")
        if Version(entry.version) != Version(version):
            _fail("QUERY_DISTRIBUTION_ROOT_VERSION_MISMATCH")
        if not set(extras) <= set(entry.provides_extras):
            _fail("QUERY_DISTRIBUTION_EXTRA_UNPROVIDED")


def _ordered_paths(values: Sequence[str], maximum: int, nonempty: bool) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)) or len(values) > maximum or (nonempty and not values):
        _fail("QUERY_DISTRIBUTION_PATH_SET_INVALID")
    paths = tuple(_path(value, "QUERY_DISTRIBUTION_PATH_SET_INVALID") for value in values)
    keys = tuple(path.casefold() for path in paths)
    if keys != tuple(sorted(keys)) or len(keys) != len(set(keys)):
        _fail("QUERY_DISTRIBUTION_PATH_SET_INVALID")
    return paths


def _path(value: object, code: str) -> str:
    try:
        path = canonical_relative_path(value)
    except Exception:
        _fail(code)
    if any(part[-1:] in {" ", "."} for part in path.split("/")):
        _fail(code)
    return path


def _name(value: object) -> str:
    try:
        normalized = normalize_distribution_name(value)
    except DistributionMetadataError:
        _fail("QUERY_DISTRIBUTION_NAME_INVALID")
    if value != normalized:
        _fail("QUERY_DISTRIBUTION_NAME_INVALID")
    return normalized


def _requirement(value: str) -> Requirement:
    try:
        requirement = Requirement(value)
    except InvalidRequirement:
        _fail("QUERY_DISTRIBUTION_REQUIREMENT_INVALID")
    if requirement.url is not None:
        _fail("QUERY_DISTRIBUTION_DIRECT_REQUIREMENT_FORBIDDEN")
    return requirement


__all__ = [
    "DistributionGraphError", "DistributionGraphLimits", "DistributionProjection",
    "derive_distribution_projection",
]
