"""Bounded, canonical inputs for inert query-runtime candidate derivation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .reddog_holoindex_dependency_runtime_contract import (
    canonical_json_bytes,
    digest_bytes,
)
from .reddog_holoindex_query_distribution_graph import DistributionGraphLimits
from .reddog_holoindex_query_runtime_candidate_contract import CandidateLimits


class CandidateInputError(RuntimeError):
    """Stable fail-closed candidate input error."""


def _fail(code: str) -> None:
    raise CandidateInputError(code)


@dataclass(frozen=True)
class CandidateDeclarations:
    roots: tuple[Mapping[str, Any], ...]
    raw_surfaces: tuple[Mapping[str, Any], ...]
    origins: tuple[str, ...]
    subprocesses: tuple[str, ...]
    digest: str


def bounded_candidate_declarations(
    root_requirements: Sequence[Mapping[str, Any]],
    dynamic_surfaces: Sequence[Mapping[str, Any]],
    module_origins: Sequence[str],
    declared_subprocess_paths: Sequence[str],
    candidate_limits: CandidateLimits,
    graph_limits: DistributionGraphLimits,
) -> CandidateDeclarations:
    """Validate declaration shapes and sizes before canonicalization."""

    roots = _bounded_mapping_sequence(
        root_requirements, candidate_limits.max_root_requirements,
        {"name", "version", "extras"}, "QUERY_RUNTIME_CANDIDATE_REQUIREMENT_INVALID",
    )
    surfaces = _bounded_mapping_sequence(
        dynamic_surfaces, candidate_limits.max_dynamic_surfaces,
        {"kind", "owner", "target"}, "QUERY_RUNTIME_CANDIDATE_DECLARATION_INVALID",
    )
    origins = _bounded_strings(
        module_origins, graph_limits.max_module_origins,
        "QUERY_RUNTIME_CANDIDATE_MODULE_ORIGIN_INVALID", nonempty=True,
        max_bytes=candidate_limits.max_path_bytes,
    )
    subprocesses = _bounded_strings(
        declared_subprocess_paths, graph_limits.max_declared_subprocesses,
        "QUERY_RUNTIME_CANDIDATE_SUBPROCESS_INVALID", nonempty=False,
        max_bytes=candidate_limits.max_path_bytes,
    )
    roots = _bounded_roots(roots, graph_limits.max_extras_per_distribution)
    surfaces = _bounded_surfaces(surfaces)
    digest = digest_bytes(canonical_json_bytes({
        "root_requirements": roots, "module_origins": origins,
        "dynamic_surfaces": surfaces, "declared_subprocess_paths": subprocesses,
    }))
    return CandidateDeclarations(
        tuple(roots), tuple(surfaces), tuple(origins), tuple(subprocesses), digest,
    )


def bounded_composition_inputs(
    value: Mapping[str, Any], max_binding_arguments: int,
) -> dict[str, Any]:
    """Validate composition verifier inputs before invoking that verifier."""

    required = {
        "composition_store_root", "generation_root", "base_runtime_store_root",
        "base_generation_root", "dependency_runtime_store_root",
        "dependency_generation_root", "canonical_store", "repo_roots",
    }
    allowed = required | {
        "composition_limits", "base_limits", "dependency_limits",
        "expected_generation_id",
    }
    if (
        type(value) is not dict or len(value) > max_binding_arguments
        or not required <= set(value) or not set(value) <= allowed
    ):
        _fail("QUERY_RUNTIME_CANDIDATE_COMPOSITION_INPUT_INVALID")
    result = dict(value)
    _bounded_composition_paths(result, required - {"repo_roots"})
    roots = result["repo_roots"]
    if (
        not isinstance(roots, (list, tuple)) or not roots or len(roots) > 16
        or any(not _approved_path_value(path) for path in roots)
    ):
        _fail("QUERY_RUNTIME_CANDIDATE_COMPOSITION_INPUT_INVALID")
    result["repo_roots"] = tuple(roots)
    expected = result.get("expected_generation_id")
    if expected is not None and not _bounded_text(expected, 71):
        _fail("QUERY_RUNTIME_CANDIDATE_COMPOSITION_INPUT_INVALID")
    return result


def bounded_source_inputs(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate source verifier inputs before invoking that verifier."""

    if type(value) is not dict or frozenset(value) != {
        "source_root", "expected_repo_head_sha",
    }:
        _fail("QUERY_RUNTIME_CANDIDATE_SOURCE_INPUT_INVALID")
    head = value.get("expected_repo_head_sha")
    if (
        not _approved_path_value(value.get("source_root"))
        or type(head) is not str or len(head) != 40
        or any(character not in "0123456789abcdef" for character in head)
    ):
        _fail("QUERY_RUNTIME_CANDIDATE_SOURCE_INPUT_INVALID")
    return dict(value)


def _bounded_composition_paths(value: Mapping[str, Any], names: set[str]) -> None:
    if any(not _approved_path_value(value.get(name)) for name in names):
        _fail("QUERY_RUNTIME_CANDIDATE_COMPOSITION_INPUT_INVALID")


def _approved_path_value(value: object) -> bool:
    if not isinstance(value, (Path, str)):
        return False
    raw = str(value)
    path = Path(raw)
    return bool(
        raw and len(raw) <= 2048 and "\x00" not in raw and path.is_absolute()
        and path.drive.rstrip(":").upper() in {"O", "E"}
        and not any(part in {".", ".."} for part in path.parts)
    )


def _bounded_mapping_sequence(
    value: Sequence[Mapping[str, Any]], maximum: int, keys: set[str], code: str,
) -> list[dict[str, Any]]:
    if not isinstance(value, (list, tuple)) or len(value) > maximum:
        _fail(code)
    rows: list[dict[str, Any]] = []
    for row in value:
        if type(row) is not dict or set(row) != keys:
            _fail(code)
        rows.append(dict(row))
    return rows


def _bounded_roots(
    rows: list[dict[str, Any]], maximum_extras: int,
) -> list[dict[str, Any]]:
    if not rows:
        _fail("QUERY_RUNTIME_CANDIDATE_REQUIREMENT_INVALID")
    result: list[dict[str, Any]] = []
    for row in rows:
        extras = row.get("extras")
        if (
            not _bounded_text(row.get("name"), 256)
            or not _bounded_text(row.get("version"), 256)
            or type(extras) is not list or len(extras) > maximum_extras
            or any(not _bounded_text(extra, 256) for extra in extras)
        ):
            _fail("QUERY_RUNTIME_CANDIDATE_REQUIREMENT_INVALID")
        result.append({**row, "extras": list(extras)})
    return result


def _bounded_surfaces(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for row in rows:
        if (
            not _bounded_text(row.get("kind"), 64)
            or not _bounded_text(row.get("owner"), 256)
            or not _bounded_text(row.get("target"), 1024)
        ):
            _fail("QUERY_RUNTIME_CANDIDATE_DECLARATION_INVALID")
    return rows


def _bounded_strings(
    value: Sequence[str], maximum: int, code: str, *, nonempty: bool,
    max_bytes: int,
) -> list[str]:
    if (
        not isinstance(value, (list, tuple)) or len(value) > maximum
        or (nonempty and not value)
        or any(not _bounded_text(item, max_bytes) for item in value)
    ):
        _fail(code)
    return list(value)


def _bounded_text(value: object, maximum: int) -> bool:
    return bool(
        type(value) is str and value
        and len(value) <= maximum and len(value.encode("utf-8")) <= maximum
    )


__all__ = [
    "CandidateDeclarations", "CandidateInputError",
    "bounded_candidate_declarations", "bounded_composition_inputs",
    "bounded_source_inputs",
]
