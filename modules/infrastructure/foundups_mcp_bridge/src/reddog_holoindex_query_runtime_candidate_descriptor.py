"""Path-free identity and strict nonclaims for an inert query candidate."""

from __future__ import annotations

from typing import Any, Mapping

from .reddog_holoindex_dependency_runtime_contract import (
    canonical_json_bytes,
    digest_bytes,
    is_digest,
)
from .reddog_holoindex_query_runtime_candidate_contract import (
    CandidateContractError,
    CandidateLimits,
    INVENTORY_NAME,
    validate_candidate_inventory,
)
from .reddog_holoindex_query_runtime_candidate_source import (
    CandidateSourceAuthorityError,
    validate_candidate_source_public_binding,
)


DESCRIPTOR_SCHEMA_VERSION = "holoindex_query_runtime_candidate_descriptor.v1"
DESCRIPTOR_NAME = "holoindex_query_runtime_candidate_descriptor.json"
_COMPOSITION_KEYS = frozenset({"generation_id", "descriptor_digest"})
_DESCRIPTOR_KEYS = frozenset({
    "schema_version", "status", "generation_id", "inventory_file",
    "inventory_digest", "runtime_composition", "backend_manifest_digest",
    "source_authority",
    "declaration_digest", "marker_environment_digest", "projection_digest",
    "distribution_count", "module_owner_count", "file_count",
    "excluded_record_entry_count", "total_bytes",
    "python_extension_count", "native_library_count", "dynamic_surface_count",
    "candidate_identity_validated", "python_import_closure_verified",
    "dynamic_load_closure_verified", "native_loader_closure_verified",
    "subprocess_closure_verified", "deterministic_effects_verified",
    "preimport_bootstrap_verified", "signature_verified", "write_denial_verified",
    "activation_eligible", "exact_runtime_closure_verified",
})
_FALSE_CLAIMS = (
    "python_import_closure_verified", "dynamic_load_closure_verified",
    "native_loader_closure_verified", "subprocess_closure_verified",
    "deterministic_effects_verified", "preimport_bootstrap_verified",
    "signature_verified", "write_denial_verified", "activation_eligible",
    "exact_runtime_closure_verified",
)


def _fail(code: str) -> None:
    raise CandidateContractError(code)


def candidate_descriptor(
    inventory: Mapping[str, Any], limits: CandidateLimits = CandidateLimits(),
) -> dict[str, Any]:
    """Derive a content identity without promoting runtime truth."""

    validated = validate_candidate_inventory(inventory, limits)
    files = validated["files"]
    identity = {
        "schema_version": DESCRIPTOR_SCHEMA_VERSION, "inventory_file": INVENTORY_NAME,
        "inventory_digest": digest_bytes(canonical_json_bytes(validated)),
        "runtime_composition": dict(validated["runtime_composition"]),
        "backend_manifest_digest": validated["backend_manifest_digest"],
        "source_authority": dict(validated["source_authority"]),
        "declaration_digest": validated["declaration_digest"],
        "marker_environment_digest": validated["marker_environment_digest"],
        "projection_digest": validated["projection_digest"],
        "distribution_count": len(validated["distributions"]),
        "module_owner_count": len(validated["module_owners"]),
        "excluded_record_entry_count": len(validated["excluded_record_entries"]),
        "file_count": len(files), "total_bytes": sum(row["size"] for row in files),
        "python_extension_count": _role_count(files, "python_extension"),
        "native_library_count": _role_count(files, "native_library"),
        "dynamic_surface_count": len(validated["dynamic_surfaces"]),
    }
    return validate_candidate_descriptor({
        **identity, "status": "INERT_CANDIDATE",
        "generation_id": digest_bytes(canonical_json_bytes(identity)),
        "candidate_identity_validated": True,
        **{name: False for name in _FALSE_CLAIMS},
    })


def validate_candidate_descriptor(value: object) -> dict[str, Any]:
    """Validate descriptor identity and strict Phase-2A nonclaims."""

    if type(value) is not dict or frozenset(value) != _DESCRIPTOR_KEYS:
        _fail("QUERY_RUNTIME_CANDIDATE_DESCRIPTOR_INVALID")
    source = dict(value)
    composition = source.get("runtime_composition")
    try:
        validate_candidate_source_public_binding(source.get("source_authority"))
    except CandidateSourceAuthorityError:
        _fail("QUERY_RUNTIME_CANDIDATE_DESCRIPTOR_INVALID")
    digest_fields = (
        "generation_id", "inventory_digest", "backend_manifest_digest",
        "declaration_digest", "marker_environment_digest", "projection_digest",
    )
    numeric = (
        "distribution_count", "module_owner_count", "file_count",
        "excluded_record_entry_count", "total_bytes",
        "python_extension_count", "native_library_count", "dynamic_surface_count",
    )
    if (
        type(composition) is not dict or frozenset(composition) != _COMPOSITION_KEYS
        or any(not is_digest(composition.get(name)) for name in _COMPOSITION_KEYS)
        or source.get("schema_version") != DESCRIPTOR_SCHEMA_VERSION
        or source.get("status") != "INERT_CANDIDATE"
        or source.get("inventory_file") != INVENTORY_NAME
        or any(not is_digest(source.get(name)) for name in digest_fields)
        or any(type(source.get(name)) is not int or source[name] < 0 for name in numeric)
        or any(source.get(name, 0) == 0 for name in (
            "distribution_count", "module_owner_count", "file_count", "total_bytes",
        ))
        or source.get("python_extension_count", 0) > source.get("file_count", 0)
        or source.get("native_library_count", 0) > source.get("file_count", 0)
    ):
        _fail("QUERY_RUNTIME_CANDIDATE_DESCRIPTOR_INVALID")
    if source.get("candidate_identity_validated") is not True or any(
        source.get(name) is not False for name in _FALSE_CLAIMS
    ):
        _fail("QUERY_RUNTIME_CANDIDATE_DESCRIPTOR_TRUTH_INVALID")
    excluded = {"generation_id", "status", "candidate_identity_validated", *_FALSE_CLAIMS}
    identity = {name: source[name] for name in source if name not in excluded}
    if source["generation_id"] != digest_bytes(canonical_json_bytes(identity)):
        _fail("QUERY_RUNTIME_CANDIDATE_GENERATION_ID_INVALID")
    return source


def validate_candidate_pair(
    inventory: Mapping[str, Any], descriptor: Mapping[str, Any],
    limits: CandidateLimits = CandidateLimits(),
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Recompute and require the exact descriptor for one inventory."""

    validated_inventory = validate_candidate_inventory(inventory, limits)
    validated_descriptor = validate_candidate_descriptor(descriptor)
    if validated_descriptor != candidate_descriptor(validated_inventory, limits):
        _fail("QUERY_RUNTIME_CANDIDATE_PAIR_MISMATCH")
    return validated_inventory, validated_descriptor


def _role_count(files: list[Mapping[str, Any]], role: str) -> int:
    return sum(row["role"] == role for row in files)


__all__ = [
    "DESCRIPTOR_NAME", "DESCRIPTOR_SCHEMA_VERSION", "candidate_descriptor",
    "validate_candidate_descriptor", "validate_candidate_pair",
]
