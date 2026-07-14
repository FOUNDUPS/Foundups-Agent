"""Tests for REDDOG_MAIN_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_PHASE1."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from unittest.mock import patch

from modules.communication.moltbot_bridge.src.reddog_main_resident_queue_serial_loop_bootstrap import (
    REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_APPLIED,
    REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_NOT_READY,
    run_reddog_main_resident_queue_serial_loop_bootstrap,
)
from modules.communication.moltbot_bridge.src.reddog_main_resident_queue_runtime_dependency_bundle import (
    REDDOG_RUNTIME_DEPENDENCY_BUNDLE_READY,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    RuntimeRejectCode,
)
from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    VALVE_OPEN_WORKTREE_CREATE,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_main_resident_queue_serial_loop_bootstrap.py"
)
NOW = "2026-07-14T00:00:00+00:00"
EXPIRES = "2026-07-14T01:00:00+00:00"


def _snapshot() -> dict[str, object]:
    return {
        "schema_version": "reddog_authoritative_work_state.v1",
        "freshness_receipts": [{"receipt_id": "fresh-1", "fresh": True}],
        "worker_claims": [
            {
                "claim_id": "claim-1",
                "slice_id": "REDDOG_TEST_SLICE_PHASE1",
                "worker_id": "reddog-0102",
                "status": "ACTIVE",
                "expires_at": EXPIRES,
                "freshness_receipt_id": "fresh-1",
            }
        ],
        "wre_queue_items": [
            {
                "queue_item_id": "queue-1",
                "slice_id": "REDDOG_TEST_SLICE_PHASE1",
                "claim_id": "claim-1",
                "worker_id": "reddog-0102",
                "status": "QUEUED",
                "evidence_refs": ["claim:claim-1", "freshness:fresh-1"],
                "no_execution_performed": True,
            }
        ],
    }


def _profile(**overrides: object) -> dict[str, object]:
    profile = {
        "principal_id": "github:mjtrout",
        "principal_provider": "github",
        "principal_public_key": "pub:principal",
        "reddog_id": "reddog:abc123",
        "reddog_public_key": "pub:reddog",
        "repo_full_name": "FOUNDUPS/Foundups-Agent",
        "foundup_id": "paccess_001",
        "allowed_paths": ["modules/foundups/paccess_001/**"],
        "denied_paths": ["modules/foundups/paccess_001/secrets/**"],
        "requested_operation": "create_foundup",
        "permission_snapshot_digest": "sha256:snap-1",
        "identity_nonce": "identity-nonce-0001",
        "work_authority_nonce": "workauth-nonce-0001",
        "issued_at": 1000,
        "identity_expires_at": 4600,
        "work_authority_expires_at": 1300,
        "valve_state_required": VALVE_OPEN_WORKTREE_CREATE,
        "key_epoch": "epoch-1",
        "consensus_receipt_digest": "sha256:consensus",
        "sovereign_authorization_digest": "sha256:012-token",
    }
    profile.update(overrides)
    return profile


def _snapshots() -> dict[str, object]:
    return {
        "snapshots": {
            "sha256:snap-1": {
                "evidence_digest": "sha256:snap-1",
                "expires_at": 1600,
                "can_write": True,
                "repo_full_name": "FOUNDUPS/Foundups-Agent",
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
                "repo_scope": ["FOUNDUPS/Foundups-Agent"],
                "foundup_scope": ["paccess_001"],
                "verified_subject_digest": "sha256:verified-subject",
                "reward_account": "reward:012",
                "owner_dae": "dae:012",
            }
        }
    }


def _write_runtime_json(tmp_path: Path, name: str, payload: object) -> Path:
    path = tmp_path / "runtime" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    return path


def test_bootstrap_serial_loop_applies_one_stage_with_existing_dependencies(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())
    profile = _write_runtime_json(tmp_path, "profile.json", _profile())
    chain = tmp_path / "runtime" / "chain_results.json"

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=chain,
        authority_profile_path=profile,
        now_iso=NOW,
        requested_queue_item_id="queue-1",
        max_steps=1,
    )

    assert result.accepted is True
    assert result.status == REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_APPLIED
    assert result.queue_item_id == "queue-1"
    assert result.selected_slice == "REDDOG_TEST_SLICE_PHASE1"
    assert result.steps_run == 1
    assert result.dispatched_stages == ("authority_request",)
    assert result.next_action == "RUN_QUEUE_AUTHORITY_RUNTIME_INVOKE"
    assert result.store_revision is not None
    assert result.no_repo_mutation_performed is True
    assert result.no_holoindex_reindex_performed is True
    stored = json.loads(chain.read_text(encoding="utf-8"))
    assert stored["stage_results"]["authority_request"]["status"] == "QUEUE_AUTHORITY_REQUEST_DRYRUN_ACCEPT"


def test_bootstrap_serial_loop_fails_closed_when_later_dependency_missing(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())
    profile = _write_runtime_json(tmp_path, "profile.json", _profile())
    chain = tmp_path / "runtime" / "chain_results.json"

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=chain,
        authority_profile_path=profile,
        now_iso=NOW,
        requested_queue_item_id="queue-1",
        max_steps=2,
    )

    assert result.accepted is False
    assert result.status == REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_NOT_READY
    assert result.steps_run == 1
    assert result.dispatched_stages == ("authority_request",)
    assert "FAIL_DISPATCH_REJECTED" in result.rejection_reasons
    assert "FAIL_HANDLER_MISSING" in result.rejection_reasons
    assert "stage:authority_runtime" in result.rejection_reasons


def test_bootstrap_serial_loop_invokes_fail_closed_authority_runtime_bundle(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())
    profile = _write_runtime_json(tmp_path, "profile.json", _profile())
    snapshots = _write_runtime_json(tmp_path, "snapshots.json", _snapshots())
    principals = _write_runtime_json(tmp_path, "principals.json", _principals())
    chain = tmp_path / "runtime" / "chain_results.json"
    authority_state = tmp_path / "runtime" / "authority_state.json"

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=chain,
        authority_profile_path=profile,
        authority_state_path=authority_state,
        permission_snapshots_path=snapshots,
        principal_authority_records_path=principals,
        now_iso=NOW,
        now_epoch=1000,
        requested_queue_item_id="queue-1",
        max_steps=2,
    )

    assert result.accepted is False
    assert result.status == REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_NOT_READY
    assert result.runtime_dependency_bundle_status == REDDOG_RUNTIME_DEPENDENCY_BUNDLE_READY
    assert result.runtime_dependency_bundle_requested is True
    assert result.steps_run == 1
    assert result.dispatched_stages == ("authority_request",)
    assert "FAIL_DISPATCH_REJECTED" in result.rejection_reasons
    assert "FAIL_RECORD_REJECTED" in result.rejection_reasons
    assert "FAIL_STAGE_REJECTED:authority_runtime" in result.rejection_reasons
    assert "REJECT_DELEGATED_AUTHORITY_RUNTIME_REJECTED" in result.rejection_reasons
    assert RuntimeRejectCode.SIGNER_NOT_CONFIGURED in result.rejection_reasons
    stored = json.loads(chain.read_text(encoding="utf-8"))
    assert "authority_runtime" not in stored["stage_results"]
    assert stored["stage_results"]["authority_request"]["status"] == "QUEUE_AUTHORITY_REQUEST_DRYRUN_ACCEPT"


def test_bootstrap_rejects_missing_authority_profile(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    state = _write_runtime_json(tmp_path, "work_state.json", _snapshot())

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=state,
        chain_results_path=tmp_path / "runtime" / "chain_results.json",
        authority_profile_path=None,
        now_iso=NOW,
    )

    assert result.accepted is False
    assert "missing_authority_profile_path" in result.rejection_reasons


def test_bootstrap_rejects_inputs_inside_repo(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    inside_state = repo / "work_state.json"
    inside_state.write_text(json.dumps(_snapshot()), encoding="utf-8")

    result = run_reddog_main_resident_queue_serial_loop_bootstrap(
        repo_root=repo,
        work_state_path=inside_state,
        chain_results_path=tmp_path / "runtime" / "chain_results.json",
        authority_profile_path=tmp_path / "runtime" / "profile.json",
        now_iso=NOW,
    )

    assert result.accepted is False
    assert "work_state_path_inside_repo" in result.rejection_reasons


def test_main_serial_loop_preflight_is_disabled_by_default() -> None:
    import main

    with patch.dict("os.environ", {}, clear=True):
        assert main.run_reddog_resident_queue_serial_loop_preflight(REPO_ROOT) is True


def test_main_serial_loop_preflight_passes_when_bootstrap_applies(tmp_path: Path) -> None:
    import main

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_main_resident_queue_serial_loop_bootstrap.run_reddog_main_resident_queue_serial_loop_bootstrap",
        return_value=type(
            "Result",
            (),
            {
                "accepted": True,
                "status": REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_APPLIED,
                "queue_item_id": "queue-1",
                "selected_slice": "REDDOG_TEST_SLICE_PHASE1",
                "steps_run": 1,
                "dispatched_stages": ("authority_request",),
                "next_action": "RUN_QUEUE_AUTHORITY_RUNTIME_INVOKE",
                "chain_results_path": str(tmp_path / "chain.json"),
                "store_revision": "sha256:revision",
                "rejection_reasons": (),
            },
        )(),
    ) as mocked:
        with patch.dict(
            "os.environ",
            {
                "REDDOG_RESIDENT_QUEUE_SERIAL_LOOP": "1",
                "REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_MAX_STEPS": "1",
                "REDDOG_AUTHORITATIVE_WORK_STATE_PATH": str(tmp_path / "state.json"),
                "REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH": str(tmp_path / "chain.json"),
                "REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH": str(tmp_path / "profile.json"),
                "REDDOG_AUTHORITY_RUNTIME_STATE_PATH": str(tmp_path / "authority_state.json"),
                "REDDOG_PERMISSION_SNAPSHOTS_PATH": str(tmp_path / "snapshots.json"),
                "REDDOG_PRINCIPAL_AUTHORITY_RECORDS_PATH": str(tmp_path / "principals.json"),
                "REDDOG_RESIDENT_QUEUE_NOW_EPOCH": "1000",
                "REDDOG_WRE_QUEUE_ITEM_ID": "queue-1",
            },
            clear=True,
        ):
            assert main.run_reddog_resident_queue_serial_loop_preflight(REPO_ROOT) is True

    assert mocked.call_args.kwargs["work_state_path"] == str(tmp_path / "state.json")
    assert mocked.call_args.kwargs["chain_results_path"] == str(tmp_path / "chain.json")
    assert mocked.call_args.kwargs["authority_profile_path"] == str(tmp_path / "profile.json")
    assert mocked.call_args.kwargs["authority_state_path"] == str(tmp_path / "authority_state.json")
    assert mocked.call_args.kwargs["permission_snapshots_path"] == str(tmp_path / "snapshots.json")
    assert mocked.call_args.kwargs["principal_authority_records_path"] == str(tmp_path / "principals.json")
    assert mocked.call_args.kwargs["requested_queue_item_id"] == "queue-1"
    assert mocked.call_args.kwargs["now_epoch"] == 1000
    assert mocked.call_args.kwargs["max_steps"] == 1


def test_main_serial_loop_preflight_blocks_when_enforced() -> None:
    import main

    with patch(
        "modules.communication.moltbot_bridge.src.reddog_main_resident_queue_serial_loop_bootstrap.run_reddog_main_resident_queue_serial_loop_bootstrap",
        return_value=type(
            "Result",
            (),
            {
                "accepted": False,
                "status": REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_BOOTSTRAP_NOT_READY,
                "queue_item_id": None,
                "selected_slice": None,
                "steps_run": 0,
                "dispatched_stages": (),
                "next_action": None,
                "chain_results_path": None,
                "store_revision": None,
                "rejection_reasons": ("missing_authority_profile_path",),
            },
        )(),
    ):
        with patch.dict(
            "os.environ",
            {
                "REDDOG_RESIDENT_QUEUE_SERIAL_LOOP": "1",
                "REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_ENFORCED": "1",
            },
            clear=True,
        ):
            assert main.run_reddog_resident_queue_serial_loop_preflight(REPO_ROOT) is False


def test_module_has_no_shell_network_holoindex_or_later_stage_imports() -> None:
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
        "reddog_signer_delegated_authority_runtime",
        "reddog_wre_queue_authority_runtime_invoke",
        "reddog_wre_queue_authority_verification_invoke",
        "reddog_wre_queue_authorized",
        "reddog_wre_queue_verified_authority_work_order_invoke",
        "reddog_wre_worktree_runner",
        "worktree_pr_runner",
        "pattern_memory",
        "openclaw_supervisor",
        "hermes_job_executor",
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
