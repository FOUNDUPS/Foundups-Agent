"""Tests for REDDOG_MAIN_RESIDENT_QUEUE_RUNTIME_DEPENDENCY_BUNDLE_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_main_resident_queue_runtime_dependency_bundle import (
    JsonPermissionSnapshotResolver,
    JsonPrincipalAuthorityResolver,
    REDDOG_RUNTIME_DEPENDENCY_BUNDLE_NOT_REQUESTED,
    REDDOG_RUNTIME_DEPENDENCY_BUNDLE_READY,
    REDDOG_RUNTIME_DEPENDENCY_BUNDLE_REJECT,
    load_reddog_main_resident_queue_runtime_dependency_bundle,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    RuntimeRejectCode,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authority_runtime_invoke import (
    invoke_reddog_wre_queue_authority_runtime,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_main_resident_queue_runtime_dependency_bundle.py"
)
NOW = 1000
REPO = "FOUNDUPS/Foundups-Agent"
FID = "paccess_001"


def _repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    return path


def _write_json(tmp_path: Path, name: str, payload: object) -> Path:
    path = tmp_path / "runtime" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _snapshots() -> dict[str, object]:
    return {
        "snapshots": {
            "sha256:snap-1": {
                "evidence_digest": "sha256:snap-1",
                "expires_at": NOW + 600,
                "can_write": True,
                "repo_full_name": REPO,
            }
        }
    }


def _principals() -> dict[str, object]:
    return {
        "principals": {
            "github:mjtrout": {
                "principal_id": "github:mjtrout",
                "principal_provider": "github",
                "principal_public_key": "pub:principal",
                "repo_scope": [REPO],
                "foundup_scope": [FID],
                "verified_subject_digest": "sha256:verified-subject",
                "reward_account": "reward:012",
                "owner_dae": "dae:012",
            }
        }
    }


def _authority_request_result() -> dict[str, object]:
    return {
        "accepted": True,
        "status": "QUEUE_AUTHORITY_REQUEST_DRYRUN_ACCEPT",
        "delegated_authority_request": {
            "work_order_id": "wre-queue-1",
            "principal_id": "github:mjtrout",
            "principal_provider": "github",
            "principal_public_key": "pub:principal",
            "reddog_id": "reddog:abc123",
            "reddog_public_key": "pub:reddog",
            "repo_full_name": REPO,
            "foundup_id": FID,
            "allowed_paths": [f"modules/foundups/{FID}/**"],
            "denied_paths": [],
            "requested_operation": "create_foundup",
            "permission_snapshot_digest": "sha256:snap-1",
            "identity_nonce": "identity-nonce-0001",
            "work_authority_nonce": "workauth-nonce-0001",
            "issued_at": NOW - 5,
            "identity_expires_at": NOW + 3600,
            "work_authority_expires_at": NOW + 300,
            "valve_state_required": "VALVE_OPEN_WORKTREE_CREATE",
            "key_epoch": "epoch-1",
            "consensus_receipt_digest": "sha256:consensus",
            "sovereign_authorization_digest": "sha256:012-token",
        },
    }


def test_bundle_not_requested_does_not_create_runtime_dependencies(tmp_path: Path) -> None:
    bundle = load_reddog_main_resident_queue_runtime_dependency_bundle(
        repo_root=_repo(tmp_path),
        authority_state_path=None,
    )

    assert bundle.accepted is True
    assert bundle.status == REDDOG_RUNTIME_DEPENDENCY_BUNDLE_NOT_REQUESTED
    assert bundle.requested is False
    assert bundle.authority_store is None
    assert bundle.signer is None
    assert bundle.no_real_signer_configured is True


def test_bundle_rejects_partial_configuration(tmp_path: Path) -> None:
    bundle = load_reddog_main_resident_queue_runtime_dependency_bundle(
        repo_root=_repo(tmp_path),
        authority_state_path=None,
        now_epoch=NOW,
    )

    assert bundle.accepted is False
    assert bundle.status == REDDOG_RUNTIME_DEPENDENCY_BUNDLE_REJECT
    assert "runtime_dependency_bundle_partial_configuration" in bundle.rejection_reasons


def test_bundle_rejects_paths_inside_repo(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    inside = repo / "authority.json"

    bundle = load_reddog_main_resident_queue_runtime_dependency_bundle(
        repo_root=repo,
        authority_state_path=inside,
    )

    assert bundle.accepted is False
    assert "authority_runtime_state_path_inside_repo" in bundle.rejection_reasons


def test_bundle_loads_outside_repo_resolvers_and_fail_closed_signer(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    authority_state = tmp_path / "runtime" / "authority-state.json"
    snapshot_path = _write_json(tmp_path, "snapshots.json", _snapshots())
    principal_path = _write_json(tmp_path, "principals.json", _principals())

    bundle = load_reddog_main_resident_queue_runtime_dependency_bundle(
        repo_root=repo,
        authority_state_path=authority_state,
        permission_snapshots_path=snapshot_path,
        principal_authority_records_path=principal_path,
        now_epoch=NOW,
    )

    assert bundle.accepted is True
    assert bundle.status == REDDOG_RUNTIME_DEPENDENCY_BUNDLE_READY
    assert bundle.signer_mode == "fail_closed"
    assert bundle.permission_snapshots_loaded == 1
    assert bundle.principal_records_loaded == 1
    assert isinstance(bundle.snapshot_resolver, JsonPermissionSnapshotResolver)
    assert isinstance(bundle.principal_resolver, JsonPrincipalAuthorityResolver)
    assert bundle.no_private_key_loaded is True
    assert bundle.no_holoindex_reindex_performed is True

    result = invoke_reddog_wre_queue_authority_runtime(
        explicit_queue_authority_runtime_requested=True,
        queue_authority_request_dryrun=_authority_request_result(),
        store=bundle.authority_store,
        signer=bundle.signer,
        principal_resolver=bundle.principal_resolver,
        snapshot_resolver=bundle.snapshot_resolver,
        now=NOW,
    )
    assert result.decision == "QUEUE_AUTHORITY_RUNTIME_INVOKE_REJECT"
    assert RuntimeRejectCode.SIGNER_NOT_CONFIGURED in result.rejection_reasons
    assert result.no_repo_mutation_performed is True


def test_bundle_has_no_shell_network_holoindex_private_key_or_live_runner_imports() -> None:
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
        "worktree_pr_runner",
        "reddog_wre_worktree_runner",
        "pattern_memory",
    }
    banned_calls = {"eval", "exec", "compile", "__import__"}
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
