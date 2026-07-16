"""Tests for REDDOG_RESIDENT_QUEUE_STAGE_HANDLER_REGISTRY_PHASE1."""

from __future__ import annotations

import ast
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    InMemoryResidentQueueChainResultsStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_stage_handler_registry import (
    RESIDENT_QUEUE_STAGE_HANDLER_REGISTRY_READY,
    build_reddog_resident_queue_stage_handler_registry,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_resident_queue_stage_handler_registry.py"
)
NOW_ISO = "2026-07-14T00:00:00+00:00"
ALL_STAGE_KEYS = (
    "authority_request",
    "authority_runtime",
    "authority_verification",
    "worker_dispatch_dryrun",
    "worker_dispatch_runtime",
    "work_order_invocation",
    "executor_plan",
    "execution_valve",
    "worktree_create",
    "bounded_worker_pilot",
    "slice_verifier",
    "verified_draft_pr_publish",
    "verified_outcome_ratchet",
    "held_out_regression_gate",
    "pattern_memory_admission",
)


class Dummy:
    def __call__(self, *args: object, **kwargs: object) -> object:
        return {}

    def load(self) -> dict[str, object]:
        return {}

    def commit(self, snapshot: object, *, expected_revision: object) -> str:
        return "sha256:dummy"


def _store() -> InMemoryResidentQueueChainResultsStore:
    return InMemoryResidentQueueChainResultsStore()


def _snapshot() -> dict[str, object]:
    return {
        "schema_version": "reddog_authoritative_work_state.v1",
        "freshness_receipts": [{"receipt_id": "fresh-1", "fresh": True}],
        "worker_claims": [],
        "wre_queue_items": [],
    }


def test_registry_registers_only_dependency_free_stages_with_default_bootstrap_dependencies() -> None:
    registry = build_reddog_resident_queue_stage_handler_registry(
        work_state_snapshot=_snapshot(),
        chain_results_store=_store(),
        authority_profile={"principal_id": "github:mjtrout"},
        now_iso=NOW_ISO,
    )

    assert registry.status == RESIDENT_QUEUE_STAGE_HANDLER_REGISTRY_READY
    assert registry.registered_stage_keys == ("authority_request", "worker_dispatch_dryrun")
    assert registry.registered_stage_count == 2
    assert set(registry.missing_stage_reasons) == set(ALL_STAGE_KEYS) - {
        "authority_request",
        "worker_dispatch_dryrun",
    }
    assert "missing_dependency:signer" in registry.missing_stage_reasons["authority_runtime"]
    assert registry.no_default_signer_created is True
    assert registry.no_default_runner_created is True
    assert registry.no_holoindex_reindex_performed is True


def test_registry_registers_all_stages_when_every_dependency_is_injected(tmp_path: Path) -> None:
    dummy = Dummy()
    registry = build_reddog_resident_queue_stage_handler_registry(
        work_state_snapshot=_snapshot(),
        chain_results_store=_store(),
        authority_profile={"principal_id": "github:mjtrout"},
        authority_store=dummy,
        signer=dummy,
        principal_resolver=dummy,
        snapshot_resolver=dummy,
        now_epoch=1783984309,
        signature_verifier=dummy,
        principal_key_resolver=dummy,
        nonce_store=dummy,
        revocation_oracle=dummy,
        work_order_resolver=dummy,
        worker_dispatch_writer=dummy,
        repo_root=tmp_path,
        valve_environment={"valve_worktree_create_enabled": True},
        worktree_runner=dummy,
        generic_writer_dryrun_result={"accepted": True},
        governed_shell_dryrun_result={"accepted": True},
        artifact_contents={"README.md": "content"},
        verifier_request={"verifier_id": "verifier-1"},
        publish_request={"publish_id": "publish-1"},
        draft_pr_runner=dummy,
        ratchet_request={"ratchet_id": "ratchet-1"},
        outcome_ratchet_store=dummy,
        held_out_gate_request={"gate_id": "gate-1"},
        admission_request={"admission_id": "admission-1"},
        pattern_memory_admission_sink=dummy,
        now_iso=NOW_ISO,
    )

    assert registry.registered_stage_keys == ALL_STAGE_KEYS
    assert registry.registered_stage_count == len(ALL_STAGE_KEYS)
    assert registry.missing_stage_reasons == {}


def test_registry_to_dict_omits_callable_handlers(tmp_path: Path) -> None:
    registry = build_reddog_resident_queue_stage_handler_registry(
        work_state_snapshot=_snapshot(),
        chain_results_store=_store(),
        authority_profile={"principal_id": "github:mjtrout"},
        now_iso=NOW_ISO,
    )

    payload = registry.to_dict()

    assert "handlers" not in payload
    assert payload["status"] == RESIDENT_QUEUE_STAGE_HANDLER_REGISTRY_READY
    assert payload["registered_stage_keys"] == ("authority_request", "worker_dispatch_dryrun")
    assert payload["no_repo_mutation_performed"] is True


def test_registry_rejects_empty_mapping_dependencies() -> None:
    registry = build_reddog_resident_queue_stage_handler_registry(
        work_state_snapshot=_snapshot(),
        chain_results_store=_store(),
        authority_profile={},
        generic_writer_dryrun_result={},
        governed_shell_dryrun_result={},
        artifact_contents={},
        verifier_request={},
        publish_request={},
        ratchet_request={},
        held_out_gate_request={},
        admission_request={},
        now_iso=NOW_ISO,
    )

    assert registry.registered_stage_keys == ("worker_dispatch_dryrun",)
    assert "missing_dependency:authority_profile" in registry.missing_stage_reasons["authority_request"]
    assert "missing_dependency:worker_dispatch_writer" in (
        registry.missing_stage_reasons["worker_dispatch_runtime"]
    )
    assert "missing_dependency:generic_writer_dryrun_result" in registry.missing_stage_reasons["bounded_worker_pilot"]
    assert "missing_dependency:artifact_contents" in registry.missing_stage_reasons["bounded_worker_pilot"]
    assert "missing_dependency:artifact_generation_request" in registry.missing_stage_reasons["bounded_worker_pilot"]
    assert "missing_dependency:artifact_generator" in registry.missing_stage_reasons["bounded_worker_pilot"]
    assert "missing_dependency:verifier_request" in registry.missing_stage_reasons["slice_verifier"]
    assert "missing_dependency:evidence_producer_request" in registry.missing_stage_reasons["slice_verifier"]
    assert "missing_dependency:evidence_command_runner" in registry.missing_stage_reasons["slice_verifier"]


def test_registry_registers_bounded_worker_pilot_from_artifact_generation_dependencies(tmp_path: Path) -> None:
    dummy = Dummy()
    registry = build_reddog_resident_queue_stage_handler_registry(
        work_state_snapshot=_snapshot(),
        chain_results_store=_store(),
        authority_profile={"principal_id": "github:mjtrout"},
        work_order_resolver=dummy,
        repo_root=tmp_path,
        generic_writer_dryrun_result={"accepted": True},
        governed_shell_dryrun_result={"accepted": True},
        artifact_generation_request={"explicit_artifact_generation_requested": True},
        artifact_generator=dummy,
        now_iso=NOW_ISO,
    )

    assert "bounded_worker_pilot" in registry.registered_stage_keys
    assert "bounded_worker_pilot" not in registry.missing_stage_reasons
    assert registry.no_default_runner_created is True


def test_registry_registers_bounded_worker_pilot_from_pilot_dryrun_binding_dependencies(
    tmp_path: Path,
) -> None:
    dummy = Dummy()
    registry = build_reddog_resident_queue_stage_handler_registry(
        work_state_snapshot=_snapshot(),
        chain_results_store=_store(),
        authority_profile={"principal_id": "github:mjtrout"},
        work_order_resolver=dummy,
        repo_root=tmp_path,
        pilot_dryrun_binding_enabled=True,
        artifact_contents={"README.md": "content"},
        now_iso=NOW_ISO,
    )

    assert "bounded_worker_pilot" in registry.registered_stage_keys
    assert "bounded_worker_pilot" not in registry.missing_stage_reasons
    assert registry.no_default_runner_created is True


def test_registry_still_requires_external_pilot_dryruns_without_binding_flag(
    tmp_path: Path,
) -> None:
    dummy = Dummy()
    registry = build_reddog_resident_queue_stage_handler_registry(
        work_state_snapshot=_snapshot(),
        chain_results_store=_store(),
        authority_profile={"principal_id": "github:mjtrout"},
        work_order_resolver=dummy,
        repo_root=tmp_path,
        artifact_contents={"README.md": "content"},
        now_iso=NOW_ISO,
    )

    assert "bounded_worker_pilot" not in registry.registered_stage_keys
    assert "missing_dependency:generic_writer_dryrun_result" in (
        registry.missing_stage_reasons["bounded_worker_pilot"]
    )
    assert "missing_dependency:governed_shell_dryrun_result" in (
        registry.missing_stage_reasons["bounded_worker_pilot"]
    )


def test_registry_registers_slice_verifier_from_evidence_producer_dependencies(tmp_path: Path) -> None:
    dummy = Dummy()
    registry = build_reddog_resident_queue_stage_handler_registry(
        work_state_snapshot=_snapshot(),
        chain_results_store=_store(),
        authority_profile={"principal_id": "github:mjtrout"},
        repo_root=tmp_path,
        evidence_producer_request={"explicit_evidence_production_requested": True},
        evidence_command_runner=dummy,
        now_iso=NOW_ISO,
    )

    assert "slice_verifier" in registry.registered_stage_keys
    assert "slice_verifier" not in registry.missing_stage_reasons
    assert registry.no_default_runner_created is True


def test_registry_registers_slice_verifier_from_request_binding_dependencies(tmp_path: Path) -> None:
    dummy = Dummy()
    registry = build_reddog_resident_queue_stage_handler_registry(
        work_state_snapshot=_snapshot(),
        chain_results_store=_store(),
        authority_profile={"principal_id": "github:mjtrout"},
        work_order_resolver=dummy,
        repo_root=tmp_path,
        evidence_command_runner=dummy,
        slice_verifier_request_binding_enabled=True,
        now_iso=NOW_ISO,
    )

    assert "slice_verifier" in registry.registered_stage_keys
    assert "slice_verifier" not in registry.missing_stage_reasons
    assert registry.no_default_runner_created is True


def test_registry_binding_slice_verifier_requires_resolver_repo_and_runner(tmp_path: Path) -> None:
    dummy = Dummy()
    registry = build_reddog_resident_queue_stage_handler_registry(
        work_state_snapshot=_snapshot(),
        chain_results_store=_store(),
        authority_profile={"principal_id": "github:mjtrout"},
        evidence_command_runner=dummy,
        slice_verifier_request_binding_enabled=True,
        now_iso=NOW_ISO,
    )

    assert "slice_verifier" not in registry.registered_stage_keys
    assert "missing_dependency:work_order_resolver" in registry.missing_stage_reasons["slice_verifier"]
    assert "missing_dependency:repo_root" in registry.missing_stage_reasons["slice_verifier"]
    assert "missing_dependency:evidence_command_runner" not in registry.missing_stage_reasons["slice_verifier"]


def test_registry_registers_draft_pr_publish_from_request_binding_dependencies(tmp_path: Path) -> None:
    dummy = Dummy()
    registry = build_reddog_resident_queue_stage_handler_registry(
        work_state_snapshot=_snapshot(),
        chain_results_store=_store(),
        authority_profile={"principal_id": "github:mjtrout"},
        work_order_resolver=dummy,
        draft_pr_runner=dummy,
        draft_pr_publish_request_binding_enabled=True,
        now_iso=NOW_ISO,
    )

    assert "verified_draft_pr_publish" in registry.registered_stage_keys
    assert "verified_draft_pr_publish" not in registry.missing_stage_reasons
    assert registry.no_default_runner_created is True


def test_registry_binding_draft_pr_publish_requires_resolver_and_runner() -> None:
    registry = build_reddog_resident_queue_stage_handler_registry(
        work_state_snapshot=_snapshot(),
        chain_results_store=_store(),
        authority_profile={"principal_id": "github:mjtrout"},
        draft_pr_publish_request_binding_enabled=True,
        now_iso=NOW_ISO,
    )

    assert "verified_draft_pr_publish" not in registry.registered_stage_keys
    reasons = registry.missing_stage_reasons["verified_draft_pr_publish"]
    assert "missing_dependency:work_order_resolver" in reasons
    assert "missing_dependency:draft_pr_runner" in reasons
    assert "missing_dependency:publish_request" not in reasons


def test_registry_has_no_shell_network_holoindex_or_default_client_construction() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_import_roots = {
        "subprocess",
        "requests",
        "urllib",
        "http",
        "socket",
        "sqlite3",
        "holo_index",
        "git",
        "hmac",
        "secrets",
    }
    banned_import_fragments = {
        "openclaw_supervisor",
        "hermes_job_executor",
        "modules.infrastructure.wre_core.src.pattern_memory",
        "worktree_pr_runner",
        "reddog_wre_worktree_runner",
    }
    banned_calls = {
        "eval",
        "exec",
        "compile",
        "__import__",
        "open",
        "AtomicJsonAuthorityRuntimeStore",
        "AtomicJsonResidentQueueChainResultsStore",
        "RealRedDogWorktreeRunner",
        "PatternMemory",
    }
    banned_attrs = {
        "system",
        "popen",
        "spawn",
        "run",
        "Popen",
        "check_call",
        "check_output",
        "unlink",
        "remove",
        "rmdir",
        "rename",
        "replace",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned_import_roots
                assert all(fragment not in alias.name for fragment in banned_import_fragments)
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_import_roots
            assert all(fragment not in node.module for fragment in banned_import_fragments)
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in banned_calls
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in banned_attrs
