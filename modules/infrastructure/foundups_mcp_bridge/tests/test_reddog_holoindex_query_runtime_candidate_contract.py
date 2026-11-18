"""Adversarial contract tests for the inert clean query-runtime candidate."""

from __future__ import annotations

from copy import deepcopy

import pytest

from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_candidate_contract import (
    CandidateContractError,
    candidate_inventory,
    validate_candidate_inventory,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_runtime_candidate_descriptor import (
    candidate_descriptor,
    validate_candidate_descriptor,
    validate_candidate_pair,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_distribution_graph import (
    DistributionProjection,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_dependency_runtime_contract import (
    canonical_json_bytes,
    digest_bytes,
)


DIGESTS = tuple(f"sha256:{index:064x}" for index in range(1, 50))
TARGET = {
    "implementation_name": "cpython", "implementation_version": "3.12.10",
    "os_name": "nt", "platform_machine": "AMD64",
    "platform_python_implementation": "CPython", "platform_release": "11",
    "platform_system": "Windows", "platform_version": "10.0",
    "python_full_version": "3.12.10", "python_version": "3.12",
    "sys_platform": "win32",
}


def _launch_and_components() -> tuple[dict[str, object], dict[str, str]]:
    launch = {
        "implementation": "cpython", "python_full_version": "3.12.10",
        "platform_tag": "win_amd64", "flags": ["-I", "-S", "-B"],
        "standalone_base_runtime_required": True,
        "stdlib_transport_required": True,
        "site_import_allowed": False, "pth_processing_allowed": False,
    }
    components = {
        "base_generation_id": DIGESTS[5],
        "base_descriptor_digest": DIGESTS[6], "base_tree_digest": DIGESTS[7],
        "dependency_generation_id": DIGESTS[8],
        "dependency_descriptor_digest": DIGESTS[9],
        "dependency_inventory_digest": DIGESTS[10],
        "dependency_tree_digest": DIGESTS[11],
    }
    return launch, components


def _candidate_rows() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    distributions = [{
        "name": "sentence-transformers", "version": "5.4.1",
        "dist_info": "sentence_transformers-5.4.1.dist-info",
        "metadata_digest": DIGESTS[12], "wheel_digest": DIGESTS[13],
        "record_digest": DIGESTS[14], "direct": True,
        "required_by": [], "marker_results_digest": DIGESTS[15],
        "excluded_record_entry_count": 0,
        "excluded_record_entries_digest": digest_bytes(canonical_json_bytes([])),
    }]
    files = [
        {
            "path": "sentence_transformers/__init__.py", "size": 12,
            "sha256": DIGESTS[16], "distribution": "sentence-transformers",
            "role": "python_source",
        },
        {
            "path": "sentence_transformers/backend.cp312-win_amd64.pyd",
            "size": 32, "sha256": DIGESTS[17],
            "distribution": "sentence-transformers", "role": "python_extension",
        },
        {
            "path": "sentence_transformers-5.4.1.dist-info/METADATA", "size": 21,
            "sha256": DIGESTS[12], "distribution": "sentence-transformers",
            "role": "distribution_metadata",
        },
        {
            "path": "sentence_transformers-5.4.1.dist-info/RECORD", "size": 22,
            "sha256": DIGESTS[14], "distribution": "sentence-transformers",
            "role": "distribution_metadata",
        },
        {
            "path": "sentence_transformers-5.4.1.dist-info/WHEEL", "size": 23,
            "sha256": DIGESTS[13], "distribution": "sentence-transformers",
            "role": "distribution_metadata",
        },
    ]
    files.sort(key=lambda row: str(row["path"]).casefold())
    return distributions, files


def _projection() -> DistributionProjection:
    distributions, files = _candidate_rows()
    excluded = []
    owners = [{
        "path": "sentence_transformers/__init__.py",
        "distribution": "sentence-transformers",
    }]
    marker_digest = digest_bytes(canonical_json_bytes(TARGET))
    identity = {
        "distributions": distributions, "files": files,
        "excluded_record_entries": excluded, "module_owners": owners,
        "marker_environment_digest": marker_digest,
    }
    return DistributionProjection(
        distributions, files, excluded, owners, TARGET, marker_digest,
        digest_bytes(canonical_json_bytes(identity)),
    )


def _inventory() -> dict[str, object]:
    launch, components = _launch_and_components()
    return candidate_inventory(
        runtime_composition={
            "generation_id": DIGESTS[0], "descriptor_digest": DIGESTS[1],
        },
        backend_manifest_digest=DIGESTS[2],
        source_authority={
            "repo_head_sha": "a" * 40, "repo_root_digest": DIGESTS[20],
            "repository_state_digest": DIGESTS[21],
            "verified_runtime_closure_digest": DIGESTS[22],
            "runtime_file_count": 10, "runtime_file_bytes": 100,
            "runtime_source_bytes_verified": True,
            "phase2a_module_set_digest": DIGESTS[23],
            "phase2a_module_count": 8, "phase2a_module_bytes": 80,
            "phase2a_module_set_verified": True,
        },
        declaration_digest=DIGESTS[3],
        projection=_projection(),
        runtime_volumes={
            "base_runtime": "O", "dependency_runtime": "O",
            "temporary_runtime": "O",
        },
        launch_dialect=launch, components=components,
        root_requirements=[{
            "name": "sentence-transformers", "version": "5.4.1", "extras": [],
        }],
        dynamic_surfaces=[{
            "kind": "import_module", "owner": "sentence-transformers",
            "target": "sentence_transformers.models.Transformer",
            "declaration_digest": DIGESTS[18],
        }],
        observed_import_trace={
            "trace_digest": DIGESTS[18], "module_count": 2,
            "native_extension_count": 1, "completeness_claimed": False,
        },
    )


def _descriptor() -> dict[str, object]:
    return candidate_descriptor(_inventory())


def _rebind_projection(value: dict[str, object]) -> None:
    marker_digest = digest_bytes(canonical_json_bytes(value["marker_environment"]))
    value["marker_environment_digest"] = marker_digest
    identity = {
        "distributions": value["distributions"], "files": value["files"],
        "excluded_record_entries": value["excluded_record_entries"],
        "module_owners": value["module_owners"],
        "marker_environment_digest": marker_digest,
    }
    value["projection_digest"] = digest_bytes(canonical_json_bytes(identity))


def _rebind_descriptor(value: dict[str, object]) -> None:
    excluded = {
        "generation_id", "status", "candidate_identity_validated",
        "python_import_closure_verified", "dynamic_load_closure_verified",
        "native_loader_closure_verified", "subprocess_closure_verified",
        "deterministic_effects_verified", "preimport_bootstrap_verified",
        "signature_verified", "write_denial_verified", "activation_eligible",
        "exact_runtime_closure_verified",
    }
    identity = {name: item for name, item in value.items() if name not in excluded}
    value["generation_id"] = digest_bytes(canonical_json_bytes(identity))


def test_valid_candidate_is_inert_and_only_manifest_truth_is_earned() -> None:
    inventory = _inventory()
    descriptor = _descriptor()

    assert validate_candidate_inventory(inventory) == inventory
    assert validate_candidate_descriptor(descriptor) == descriptor
    assert descriptor["status"] == "INERT_CANDIDATE"
    assert descriptor["candidate_identity_validated"] is True
    assert validate_candidate_pair(inventory, descriptor) == (inventory, descriptor)
    for field in (
        "python_import_closure_verified", "dynamic_load_closure_verified",
        "native_loader_closure_verified", "subprocess_closure_verified",
        "deterministic_effects_verified", "preimport_bootstrap_verified",
        "signature_verified", "write_denial_verified", "activation_eligible",
        "exact_runtime_closure_verified",
    ):
        assert descriptor[field] is False


@pytest.mark.parametrize(
    ("mutation", "code"),
    (
        (lambda value: value.update(extra=True), "QUERY_RUNTIME_CANDIDATE_INVENTORY_INVALID"),
        (lambda value: value["runtime_volumes"].update(base_runtime="C"), "QUERY_RUNTIME_CANDIDATE_VOLUME_INVALID"),
        (lambda value: value["launch_dialect"].update(site_import_allowed=True), "QUERY_RUNTIME_CANDIDATE_LAUNCH_INVALID"),
        (lambda value: value["launch_dialect"].update(flags=["-I", "-B"]), "QUERY_RUNTIME_CANDIDATE_LAUNCH_INVALID"),
        (lambda value: value["observed_import_trace"].update(completeness_claimed=True), "QUERY_RUNTIME_CANDIDATE_TRACE_INVALID"),
        (lambda value: value["root_requirements"][0].update(version=""), "QUERY_RUNTIME_CANDIDATE_REQUIREMENT_INVALID"),
        (lambda value: value["distributions"][0].update(direct=1), "QUERY_RUNTIME_CANDIDATE_DISTRIBUTION_INVALID"),
        (lambda value: value["files"][0].update(size=True), "QUERY_RUNTIME_CANDIDATE_FILE_INVALID"),
        (lambda value: value["dynamic_surfaces"][0].update(kind="unknown"), "QUERY_RUNTIME_CANDIDATE_DYNAMIC_SURFACE_INVALID"),
    ),
)
def test_inventory_rejects_hostile_shapes(mutation, code: str) -> None:
    value = deepcopy(_inventory())
    mutation(value)
    with pytest.raises(CandidateContractError, match=code):
        validate_candidate_inventory(value)


@pytest.mark.parametrize(
    "path",
    (
        "../escape.py", "/absolute.py", "C:/ambient.py", "//server/share/x.py",
        "pkg\\module.py", "pkg/file.py:stream", "pkg/con.py", "pkg/trailing. ",
        "pkg/\u0065\u0301.py",
    ),
)
def test_candidate_file_paths_reject_aliases_and_ambient_roots(path: str) -> None:
    value = deepcopy(_inventory())
    value["files"][0]["path"] = path
    with pytest.raises(CandidateContractError, match="QUERY_RUNTIME_CANDIDATE_PATH_INVALID"):
        validate_candidate_inventory(value)


def test_casefold_collisions_and_duplicate_distribution_ownership_reject() -> None:
    value = deepcopy(_inventory())
    duplicate = deepcopy(next(
        row for row in value["files"] if row["path"] == "sentence_transformers/__init__.py"
    ))
    duplicate["path"] = "SENTENCE_TRANSFORMERS/__init__.py"
    value["files"].append(duplicate)
    with pytest.raises(CandidateContractError, match="QUERY_RUNTIME_CANDIDATE_FILE_ORDER_INVALID"):
        validate_candidate_inventory(value)


def test_rows_must_be_deterministic_and_referentially_closed() -> None:
    value = deepcopy(_inventory())
    value["files"] = list(reversed(value["files"]))
    with pytest.raises(CandidateContractError, match="QUERY_RUNTIME_CANDIDATE_FILE_ORDER_INVALID"):
        validate_candidate_inventory(value)

    value = deepcopy(_inventory())
    value["files"][0]["distribution"] = "unbound-distribution"
    with pytest.raises(CandidateContractError, match="QUERY_RUNTIME_CANDIDATE_FILE_OWNER_INVALID"):
        validate_candidate_inventory(value)


def test_descriptor_rejects_overclaim_and_identity_substitution() -> None:
    value = deepcopy(_descriptor())
    value["activation_eligible"] = True
    with pytest.raises(CandidateContractError, match="QUERY_RUNTIME_CANDIDATE_DESCRIPTOR_TRUTH_INVALID"):
        validate_candidate_descriptor(value)


def test_cross_binding_and_accepted_invalid_regressions_fail_closed() -> None:
    value = deepcopy(_inventory())
    value["root_requirements"][0]["version"] = "5.4.2"
    with pytest.raises(CandidateContractError, match="DISTRIBUTION_CLOSURE_INVALID"):
        validate_candidate_inventory(value)

    value = deepcopy(_inventory())
    source = next(row for row in value["files"] if row["role"] == "python_source")
    source["role"] = "native_library"
    with pytest.raises(CandidateContractError, match="FILE_INVALID"):
        validate_candidate_inventory(value)

    value = deepcopy(_inventory())
    value["module_owners"] = []
    with pytest.raises(CandidateContractError, match="MODULE_OWNER_INVALID"):
        validate_candidate_inventory(value)

    value = deepcopy(_inventory())
    value["distributions"].append({
        **value["distributions"][0], "name": "orphan", "dist_info": "orphan-1.0.dist-info",
        "version": "1.0", "direct": False, "required_by": [],
    })
    value["distributions"].sort(key=lambda row: row["name"])
    with pytest.raises(CandidateContractError, match="DISTRIBUTION_CLOSURE_INVALID"):
        validate_candidate_inventory(value)


def test_metadata_projection_marker_and_descriptor_cross_counts_reject() -> None:
    value = deepcopy(_inventory())
    value["files"] = [row for row in value["files"] if not row["path"].endswith("/WHEEL")]
    with pytest.raises(CandidateContractError, match="DISTRIBUTION_METADATA_INVALID"):
        validate_candidate_inventory(value)

    value = deepcopy(_inventory())
    value["marker_environment"]["sys_platform"] = "linux"
    _rebind_projection(value)
    with pytest.raises(CandidateContractError, match="MARKER_ENVIRONMENT_INVALID"):
        validate_candidate_inventory(value)

    value = deepcopy(_descriptor())
    value["file_count"] = 0
    value["python_extension_count"] = 1
    _rebind_descriptor(value)
    with pytest.raises(CandidateContractError, match="DESCRIPTOR_INVALID"):
        validate_candidate_descriptor(value)

    value = deepcopy(_inventory())
    value["projection_digest"] = DIGESTS[0]
    with pytest.raises(CandidateContractError, match="PROJECTION_INVALID"):
        validate_candidate_inventory(value)

    value = deepcopy(_descriptor())
    value["backend_manifest_digest"] = DIGESTS[10]
    with pytest.raises(CandidateContractError, match="QUERY_RUNTIME_CANDIDATE_GENERATION_ID_INVALID"):
        validate_candidate_descriptor(value)


def test_every_bound_input_changes_generation_identity() -> None:
    baseline = _descriptor()["generation_id"]
    mutations = []
    for field in ("backend_manifest_digest", "declaration_digest"):
        value = deepcopy(_inventory())
        value[field] = DIGESTS[0]
        mutations.append(value)
    value = deepcopy(_inventory())
    next(row for row in value["files"] if row["role"] == "python_source")["sha256"] = DIGESTS[0]
    _rebind_projection(value)
    mutations.append(value)
    value = deepcopy(_inventory())
    value["marker_environment"]["platform_release"] = "12"
    _rebind_projection(value)
    mutations.append(value)
    value = deepcopy(_inventory())
    value["dynamic_surfaces"][0]["target"] += ".changed"
    mutations.append(value)

    assert all(candidate_descriptor(value)["generation_id"] != baseline for value in mutations)
