"""Path-free contract for inert query evidence-builder authority proofs.

This contract binds independently reproducible component observations.  It
does not authorize candidate publication, execution, materialization, route
changes, activation, A-grade admission, or retrieval RSI promotion.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Any, Mapping

from .reddog_holoindex_dependency_runtime_contract import (
    canonical_json_bytes,
    digest_bytes,
    is_digest,
)


SCHEMA_VERSION = "holoindex_query_runtime_builder_authority.v1"

_PROCESS_KEYS = frozenset({
    "runtime_composition_generation_id",
    "runtime_composition_descriptor_digest",
    "builder_source_root_digest",
    "dependency_runtime_inventory_digest",
    "process_image_content_digest",
    "process_image_size",
    "launch_state_digest",
    "sys_path_digest",
    "actual_process_image_verified",
    "isolation_verified",
    "native_loaded_image_closure_verified",
})
_PACKAGING_KEYS = frozenset({
    "distribution_name",
    "distribution_version",
    "dependency_inventory_digest",
    "record_digest",
    "owned_files_digest",
    "owned_file_count",
    "owned_file_bytes",
    "loaded_origins_digest",
    "loaded_module_count",
    "record_ownership_verified",
    "source_only_topology_verified",
    "bytecode_cache_absent",
    "loaded_origin_metadata_verified",
})
_SOURCE_KEYS = frozenset({
    "repo_head_sha",
    "repo_root_digest",
    "backend_manifest_digest",
    "observed_source_manifest_digest",
    "observed_loaded_sources_digest",
    "loaded_source_count",
    "loaded_source_bytes",
    "git_executable_content_digest",
    "repository_state_digest",
    "manifest_bytes_verified",
    "observed_loaded_source_metadata_verified",
    "pinned_git_executable_verified",
    "repository_topology_snapshot_verified",
    "git_environment_sanitized",
})
_RECEIPT_KEYS = frozenset({
    "schema_version",
    "status",
    "generation_id",
    "process_authority",
    "packaging_authority",
    "source_authority",
    "component_contracts_validated",
    "cross_pass_equality_verified",
    "governed_candidate_evidence_authority",
    "dynamic_load_closure_verified",
    "native_loader_closure_verified",
    "subprocess_closure_verified",
    "preimport_loader_verified",
    "deterministic_effects_verified",
    "signature_verified",
    "write_denial_verified",
    "activation_eligible",
    "exact_runtime_closure_verified",
    "holoindex_a_grade",
    "retrieval_quality_rsi_operational",
})
_FALSE_CLAIMS = (
    "cross_pass_equality_verified",
    "governed_candidate_evidence_authority",
    "dynamic_load_closure_verified",
    "native_loader_closure_verified",
    "subprocess_closure_verified",
    "preimport_loader_verified",
    "deterministic_effects_verified",
    "signature_verified",
    "write_denial_verified",
    "activation_eligible",
    "exact_runtime_closure_verified",
    "holoindex_a_grade",
    "retrieval_quality_rsi_operational",
)
_CAPABILITY_SEAL = object()


class QueryRuntimeBuilderContractError(RuntimeError):
    """Stable fail-closed builder-authority contract error."""


def _fail(code: str) -> None:
    raise QueryRuntimeBuilderContractError(code)


class _BuilderAuthorityCapability:
    __slots__ = ("_binding", "_seal")

    def __init__(
        self, binding: Mapping[str, Any], *, _seal: object | None = None,
    ) -> None:
        if _seal is not _CAPABILITY_SEAL:
            _fail("QUERY_BUILDER_AUTHORITY_CAPABILITY_INVALID")
        self._binding = MappingProxyType(dict(binding))
        self._seal = _seal

    @property
    def public_binding(self) -> Mapping[str, Any]:
        return dict(self._binding)


class BuilderProcessAuthority(_BuilderAuthorityCapability):
    """Verifier-minted actual-process authority capability."""


class BuilderPackagingAuthority(_BuilderAuthorityCapability):
    """Verifier-minted source-only packaging authority capability."""


class BuilderSourceAuthority(_BuilderAuthorityCapability):
    """Verifier-minted authenticated source authority capability."""


def _process_authority_capability(
    binding: Mapping[str, Any],
) -> BuilderProcessAuthority:
    return BuilderProcessAuthority(
        validate_process_authority(binding), _seal=_CAPABILITY_SEAL,
    )


def _packaging_authority_capability(
    binding: Mapping[str, Any],
) -> BuilderPackagingAuthority:
    return BuilderPackagingAuthority(
        validate_packaging_authority(binding), _seal=_CAPABILITY_SEAL,
    )


def _source_authority_capability(
    binding: Mapping[str, Any],
) -> BuilderSourceAuthority:
    return BuilderSourceAuthority(
        validate_source_authority(binding), _seal=_CAPABILITY_SEAL,
    )


def builder_authority_receipt(
    *, process_authority: BuilderProcessAuthority,
    packaging_authority: BuilderPackagingAuthority,
    source_authority: BuilderSourceAuthority,
) -> dict[str, Any]:
    """Create the only valid Phase-2B inert proof-authority receipt."""

    process = _capability_binding(process_authority, BuilderProcessAuthority)
    packaging = _capability_binding(packaging_authority, BuilderPackagingAuthority)
    source = _capability_binding(source_authority, BuilderSourceAuthority)
    identity = {
        "schema_version": SCHEMA_VERSION,
        "process_authority": process,
        "packaging_authority": packaging,
        "source_authority": source,
    }
    return validate_builder_authority_receipt({
        **identity,
        "status": "INERT_PROOF_AUTHORITY",
        "generation_id": digest_bytes(canonical_json_bytes(identity)),
        "component_contracts_validated": True,
        **{name: False for name in _FALSE_CLAIMS},
    })


def validate_builder_authority_receipt(value: object) -> dict[str, Any]:
    """Validate identity and force every unearned operational claim false."""

    source = _exact(value, _RECEIPT_KEYS, "QUERY_BUILDER_RECEIPT_INVALID")
    if (
        source.get("schema_version") != SCHEMA_VERSION
        or source.get("status") != "INERT_PROOF_AUTHORITY"
        or source.get("component_contracts_validated") is not True
        or any(source.get(name) is not False for name in _FALSE_CLAIMS)
    ):
        _fail("QUERY_BUILDER_RECEIPT_TRUTH_INVALID")
    process = validate_process_authority(source.get("process_authority"))
    packaging = validate_packaging_authority(source.get("packaging_authority"))
    authority = validate_source_authority(source.get("source_authority"))
    _validate_component_compatibility(process, packaging, authority)
    identity = {
        "schema_version": SCHEMA_VERSION,
        "process_authority": process,
        "packaging_authority": packaging,
        "source_authority": authority,
    }
    if source.get("generation_id") != digest_bytes(canonical_json_bytes(identity)):
        _fail("QUERY_BUILDER_GENERATION_ID_INVALID")
    return {**dict(source), **identity}


def validate_process_authority(value: object) -> dict[str, Any]:
    source = _exact(value, _PROCESS_KEYS, "QUERY_BUILDER_PROCESS_BINDING_INVALID")
    for name in (
        "runtime_composition_generation_id",
        "runtime_composition_descriptor_digest",
        "builder_source_root_digest",
        "dependency_runtime_inventory_digest",
        "process_image_content_digest",
        "launch_state_digest",
        "sys_path_digest",
    ):
        if not is_digest(source.get(name)):
            _fail("QUERY_BUILDER_PROCESS_BINDING_INVALID")
    if (
        type(source.get("process_image_size")) is not int
        or source["process_image_size"] <= 0
        or source.get("actual_process_image_verified") is not True
        or source.get("isolation_verified") is not True
        or source.get("native_loaded_image_closure_verified") is not False
    ):
        _fail("QUERY_BUILDER_PROCESS_BINDING_INVALID")
    return dict(source)


def _validate_component_compatibility(
    process: Mapping[str, Any], packaging: Mapping[str, Any],
    source: Mapping[str, Any],
) -> None:
    if (
        process["builder_source_root_digest"] != source["repo_root_digest"]
        or process["dependency_runtime_inventory_digest"]
        != packaging["dependency_inventory_digest"]
    ):
        _fail("QUERY_BUILDER_COMPONENT_IDENTITY_MISMATCH")


def validate_packaging_authority(value: object) -> dict[str, Any]:
    source = _exact(value, _PACKAGING_KEYS, "QUERY_BUILDER_PACKAGING_BINDING_INVALID")
    if (
        source.get("distribution_name") != "packaging"
        or source.get("distribution_version") != "26.0"
        or any(not is_digest(source.get(name)) for name in (
            "dependency_inventory_digest", "record_digest",
            "owned_files_digest", "loaded_origins_digest",
        ))
        or any(
            type(source.get(name)) is not int or source[name] <= 0
            for name in ("owned_file_count", "owned_file_bytes", "loaded_module_count")
        )
        or any(source.get(name) is not True for name in (
            "record_ownership_verified", "source_only_topology_verified",
            "bytecode_cache_absent", "loaded_origin_metadata_verified",
        ))
    ):
        _fail("QUERY_BUILDER_PACKAGING_BINDING_INVALID")
    return dict(source)


def validate_source_authority(value: object) -> dict[str, Any]:
    source = _exact(value, _SOURCE_KEYS, "QUERY_BUILDER_SOURCE_BINDING_INVALID")
    head = source.get("repo_head_sha")
    if (
        type(head) is not str or len(head) != 40
        or any(char not in "0123456789abcdef" for char in head)
        or any(not is_digest(source.get(name)) for name in (
            "repo_root_digest", "backend_manifest_digest",
            "observed_source_manifest_digest", "observed_loaded_sources_digest",
            "git_executable_content_digest", "repository_state_digest",
        ))
        or any(
            type(source.get(name)) is not int or source[name] <= 0
            for name in ("loaded_source_count", "loaded_source_bytes")
        )
        or any(source.get(name) is not True for name in (
            "manifest_bytes_verified", "observed_loaded_source_metadata_verified",
            "pinned_git_executable_verified", "repository_topology_snapshot_verified",
            "git_environment_sanitized",
        ))
    ):
        _fail("QUERY_BUILDER_SOURCE_BINDING_INVALID")
    return dict(source)


def _exact(value: object, keys: frozenset[str], code: str) -> dict[str, Any]:
    if type(value) is not dict or frozenset(value) != keys:
        _fail(code)
    return dict(value)


def _capability_binding(
    value: object, capability_type: type[_BuilderAuthorityCapability],
) -> dict[str, Any]:
    if type(value) is not capability_type or value._seal is not _CAPABILITY_SEAL:
        _fail("QUERY_BUILDER_AUTHORITY_CAPABILITY_INVALID")
    validators = {
        BuilderProcessAuthority: validate_process_authority,
        BuilderPackagingAuthority: validate_packaging_authority,
        BuilderSourceAuthority: validate_source_authority,
    }
    return validators[capability_type](dict(value._binding))


__all__ = [
    "BuilderPackagingAuthority",
    "BuilderProcessAuthority",
    "BuilderSourceAuthority",
    "QueryRuntimeBuilderContractError",
    "SCHEMA_VERSION",
    "builder_authority_receipt",
    "validate_builder_authority_receipt",
    "validate_packaging_authority",
    "validate_process_authority",
    "validate_source_authority",
]
