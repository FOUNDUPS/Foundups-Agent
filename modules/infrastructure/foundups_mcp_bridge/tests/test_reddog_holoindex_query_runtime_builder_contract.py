from __future__ import annotations

import copy

import pytest

from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_builder_contract import (
    QueryRuntimeBuilderContractError,
    _packaging_authority_capability,
    _process_authority_capability,
    _source_authority_capability,
    builder_authority_receipt,
    validate_builder_authority_receipt,
)


_INVALID_DIGEST = "sha256:0000000000000000000000000000000000000000000000000000000000000000"


def _digest(char: str) -> str:
    return "sha256:" + char * 64


def _components():
    process = {
        "runtime_composition_generation_id": _digest("1"),
        "runtime_composition_descriptor_digest": _digest("2"),
        "builder_source_root_digest": _digest("a"),
        "dependency_runtime_inventory_digest": _digest("6"),
        "process_image_content_digest": _digest("3"),
        "process_image_size": 42,
        "launch_state_digest": _digest("4"),
        "sys_path_digest": _digest("5"),
        "actual_process_image_verified": True,
        "isolation_verified": True,
        "native_loaded_image_closure_verified": False,
    }
    packaging = {
        "distribution_name": "packaging",
        "distribution_version": "26.0",
        "dependency_inventory_digest": _digest("6"),
        "record_digest": _digest("7"),
        "owned_files_digest": _digest("8"),
        "owned_file_count": 12,
        "owned_file_bytes": 1000,
        "loaded_origins_digest": _digest("9"),
        "loaded_module_count": 6,
        "record_ownership_verified": True,
        "source_only_topology_verified": True,
        "bytecode_cache_absent": True,
        "loaded_origin_metadata_verified": True,
    }
    source = {
        "repo_head_sha": "a" * 40,
        "repo_root_digest": _digest("a"),
        "backend_manifest_digest": _digest("b"),
        "observed_source_manifest_digest": _digest("c"),
        "observed_loaded_sources_digest": _digest("d"),
        "loaded_source_count": 4,
        "loaded_source_bytes": 2000,
        "git_executable_content_digest": _digest("e"),
        "repository_state_digest": _digest("f"),
        "manifest_bytes_verified": True,
        "observed_loaded_source_metadata_verified": True,
        "pinned_git_executable_verified": True,
        "repository_topology_snapshot_verified": True,
        "git_environment_sanitized": True,
    }
    return process, packaging, source


def _capabilities():
    process, packaging, source = _components()
    return (
        _process_authority_capability(process),
        _packaging_authority_capability(packaging),
        _source_authority_capability(source),
    )


def test_receipt_is_deterministic_and_inert() -> None:
    process, packaging, source = _capabilities()
    first = builder_authority_receipt(
        process_authority=process,
        packaging_authority=packaging,
        source_authority=source,
    )
    second = builder_authority_receipt(
        process_authority=process,
        packaging_authority=packaging,
        source_authority=source,
    )
    assert first == second
    assert first["status"] == "INERT_PROOF_AUTHORITY"
    assert first["component_contracts_validated"] is True
    assert first["activation_eligible"] is False
    assert first["exact_runtime_closure_verified"] is False
    assert first["holoindex_a_grade"] is False
    assert first["retrieval_quality_rsi_operational"] is False


@pytest.mark.parametrize(
    "field",
    [
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
    ],
)
def test_receipt_rejects_unearned_claims(field: str) -> None:
    receipt = builder_authority_receipt(
        process_authority=_capabilities()[0],
        packaging_authority=_capabilities()[1],
        source_authority=_capabilities()[2],
    )
    changed = copy.deepcopy(receipt)
    changed[field] = True
    with pytest.raises(QueryRuntimeBuilderContractError, match="RECEIPT_TRUTH_INVALID"):
        validate_builder_authority_receipt(changed)


def test_receipt_rejects_identity_mutation_and_extra_fields() -> None:
    process, packaging, source = _capabilities()
    receipt = builder_authority_receipt(
        process_authority=process,
        packaging_authority=packaging,
        source_authority=source,
    )
    changed = copy.deepcopy(receipt)
    changed["source_authority"]["repo_head_sha"] = "b" * 40
    with pytest.raises(QueryRuntimeBuilderContractError, match="GENERATION_ID_INVALID"):
        validate_builder_authority_receipt(changed)
    changed = copy.deepcopy(receipt)
    changed["unexpected"] = False
    with pytest.raises(QueryRuntimeBuilderContractError, match="RECEIPT_INVALID"):
        validate_builder_authority_receipt(changed)


def test_receipt_builder_rejects_raw_component_mappings() -> None:
    process, packaging, source = _components()
    with pytest.raises(QueryRuntimeBuilderContractError, match="CAPABILITY_INVALID"):
        builder_authority_receipt(
            process_authority=process,  # type: ignore[arg-type]
            packaging_authority=packaging,  # type: ignore[arg-type]
            source_authority=source,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("builder_source_root_digest", _INVALID_DIGEST),
        ("dependency_runtime_inventory_digest", _INVALID_DIGEST),
    ],
)
def test_receipt_rejects_cross_component_substitution(field: str, value: str) -> None:
    process, packaging, source = _components()
    process[field] = value
    with pytest.raises(QueryRuntimeBuilderContractError, match="COMPONENT_IDENTITY_MISMATCH"):
        builder_authority_receipt(
            process_authority=_process_authority_capability(process),
            packaging_authority=_packaging_authority_capability(packaging),
            source_authority=_source_authority_capability(source),
        )
