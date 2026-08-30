"""Path-free evidence contract for one held builder child execution."""

from __future__ import annotations

from dataclasses import dataclass
import json
from types import MappingProxyType
from typing import Any, Mapping

from .reddog_bounded_child_process import CHILD_STDOUT_MAX_BYTES
from .reddog_holoindex_dependency_runtime_contract import (
    canonical_json_bytes,
    digest_bytes,
)
from .reddog_holoindex_query_runtime_builder_contract import (
    validate_process_authority,
)


CHILD_OUTPUT_SCHEMA_VERSION = "holoindex_query_builder_child_output.v1"
EVIDENCE_SCHEMA_VERSION = "holoindex_query_builder_child_evidence.v1"
_CHILD_OUTPUT_KEYS = frozenset({
    "schema_version", "status", "process_authority",
})
_TRUE_EVIDENCE_FIELDS = (
    "held_executable_launch_verified",
    "single_child_execution_verified",
    "bounded_output_verified",
    "serialized_process_observation_validated",
    "runtime_composition_stable_around_child_verified",
)
_FALSE_EVIDENCE_FIELDS = (
    "builder_process_capability_preserved",
    "authenticated_producer_verified",
    "preimport_loader_verified",
    "loaded_module_origins_verified",
    "abi_compatibility_verified",
    "native_loader_closure_verified",
    "subprocess_closure_verified",
    "deterministic_effects_verified",
    "signature_verified",
    "persistent_write_denial_verified",
    "activation_eligible",
    "a_grade_verified",
    "retrieval_rsi_verified",
)
_EVIDENCE_KEYS = frozenset({
    "schema_version", "status", "generation_id", "process_authority",
    *_TRUE_EVIDENCE_FIELDS, *_FALSE_EVIDENCE_FIELDS,
})
_EVIDENCE_SEAL = object()


class QueryRuntimeBuilderChildContractError(RuntimeError):
    """Stable fail-closed child evidence error."""


def _fail(code: str) -> None:
    raise QueryRuntimeBuilderChildContractError(code)


@dataclass(frozen=True)
class BuilderProcessChildEvidence:
    """Validated observation only; never a process-authority capability."""

    _binding: Mapping[str, Any]
    _seal: object = None

    def __post_init__(self) -> None:
        if self._seal is not _EVIDENCE_SEAL:
            _fail("QUERY_BUILDER_CHILD_EVIDENCE_CONSTRUCTION_INVALID")

    @property
    def public_binding(self) -> Mapping[str, Any]:
        return dict(self._binding)


def _exact(value: object, keys: frozenset[str], code: str) -> dict[str, Any]:
    if type(value) is not dict or frozenset(value) != keys:
        _fail(code)
    return dict(value)


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if type(key) is not str or key in result:
            _fail("QUERY_BUILDER_CHILD_OUTPUT_JSON_INVALID")
        result[key] = value
    return result


def child_process_output(process_authority: object) -> dict[str, Any]:
    """Create the only child payload allowed over stdout."""

    return {
        "schema_version": CHILD_OUTPUT_SCHEMA_VERSION,
        "status": "OBSERVED_PROCESS_AUTHORITY",
        "process_authority": validate_process_authority(process_authority),
    }


def child_process_output_bytes(process_authority: object) -> bytes:
    return canonical_json_bytes(child_process_output(process_authority))


def validate_child_process_output(value: object) -> dict[str, Any]:
    source = _exact(
        value, _CHILD_OUTPUT_KEYS, "QUERY_BUILDER_CHILD_OUTPUT_INVALID",
    )
    if (
        source.get("schema_version") != CHILD_OUTPUT_SCHEMA_VERSION
        or source.get("status") != "OBSERVED_PROCESS_AUTHORITY"
    ):
        _fail("QUERY_BUILDER_CHILD_OUTPUT_INVALID")
    source["process_authority"] = validate_process_authority(
        source.get("process_authority")
    )
    return source


def parse_child_process_output(raw: object) -> dict[str, Any]:
    """Require exactly one canonical ASCII JSON line with no duplicate keys."""

    if (
        type(raw) is not bytes or len(raw) > CHILD_STDOUT_MAX_BYTES
        or not raw.endswith(b"\n")
        or raw.count(b"\n") != 1 or b"\r" in raw or not raw[:-1]
    ):
        _fail("QUERY_BUILDER_CHILD_OUTPUT_BYTES_INVALID")
    try:
        text = raw[:-1].decode("ascii")
        value = json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=lambda _value: _fail(
                "QUERY_BUILDER_CHILD_OUTPUT_JSON_INVALID"
            ),
        )
    except QueryRuntimeBuilderChildContractError:
        raise
    except (TypeError, UnicodeError, ValueError):
        _fail("QUERY_BUILDER_CHILD_OUTPUT_JSON_INVALID")
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        _fail("QUERY_BUILDER_CHILD_OUTPUT_JSON_INVALID")
    return validate_child_process_output(value)


def _build_builder_process_child_evidence(
    process_authority: object,
) -> BuilderProcessChildEvidence:
    process = validate_process_authority(process_authority)
    identity = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "process_authority": process,
        **{name: True for name in _TRUE_EVIDENCE_FIELDS},
    }
    binding = validate_builder_process_child_evidence({
        **identity,
        "status": "INERT_CHILD_EVIDENCE",
        "generation_id": digest_bytes(canonical_json_bytes(identity)),
        **{name: False for name in _FALSE_EVIDENCE_FIELDS},
    })
    return BuilderProcessChildEvidence(MappingProxyType(binding), _EVIDENCE_SEAL)


def validate_builder_process_child_evidence(value: object) -> dict[str, Any]:
    source = _exact(
        value, _EVIDENCE_KEYS, "QUERY_BUILDER_CHILD_EVIDENCE_INVALID",
    )
    if (
        source.get("schema_version") != EVIDENCE_SCHEMA_VERSION
        or source.get("status") != "INERT_CHILD_EVIDENCE"
        or any(source.get(name) is not True for name in _TRUE_EVIDENCE_FIELDS)
        or any(source.get(name) is not False for name in _FALSE_EVIDENCE_FIELDS)
    ):
        _fail("QUERY_BUILDER_CHILD_EVIDENCE_TRUTH_INVALID")
    process = validate_process_authority(source.get("process_authority"))
    identity = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "process_authority": process,
        **{name: True for name in _TRUE_EVIDENCE_FIELDS},
    }
    if source.get("generation_id") != digest_bytes(canonical_json_bytes(identity)):
        _fail("QUERY_BUILDER_CHILD_EVIDENCE_ID_INVALID")
    return {**source, "process_authority": process}


__all__ = [
    "BuilderProcessChildEvidence", "CHILD_OUTPUT_SCHEMA_VERSION",
    "EVIDENCE_SCHEMA_VERSION", "QueryRuntimeBuilderChildContractError",
    "child_process_output_bytes",
    "parse_child_process_output", "validate_builder_process_child_evidence",
]
