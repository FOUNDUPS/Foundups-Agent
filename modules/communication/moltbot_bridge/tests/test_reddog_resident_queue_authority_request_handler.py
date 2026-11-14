"""Tests for REDDOG_RESIDENT_QUEUE_AUTHORITY_REQUEST_HANDLER_PHASE1."""

from __future__ import annotations

import ast
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_resident_queue_authority_request_handler import (
    AUTHORITY_REQUEST_STAGE_KEY,
    FAIL_ARCHITECT_FIX_PUBLICATION_NOT_COMMITTED,
    FAIL_DISPATCH_NEXT_ACTION_MISMATCH,
    FAIL_DISPATCH_STAGE_MISMATCH,
    FAIL_QUEUE_SELECTION_MISMATCH,
    build_reddog_resident_queue_authority_request_stage_handler,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    InMemoryResidentQueueChainResultsStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_next_stage_dispatch import (
    FAIL_RECORD_REJECTED,
    RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_ACCEPT,
    invoke_reddog_resident_queue_next_stage_dispatch,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    NEXT_QUEUE_AUTHORITY_REQUEST_DRYRUN,
    NEXT_QUEUE_AUTHORITY_RUNTIME_INVOKE,
)
from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    VALVE_OPEN_WORKTREE_CREATE,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authority_request_dryrun import (
    QUEUE_AUTHORITY_REQUEST_DRYRUN_ACCEPT,
    QUEUE_AUTHORITY_REQUEST_DRYRUN_REJECT,
)
from modules.communication.moltbot_bridge.tests.reddog_resident_queue_test_helpers import (
    with_architect_fix_publication,
    with_queue_wsp15_allocation,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_resident_queue_authority_request_handler.py"
)
NOW = "2026-07-14T00:00:00+00:00"
EXPIRES = "2026-07-14T01:00:00+00:00"


def _snapshot(**queue_overrides: object) -> dict[str, object]:
    queue_item = {
        "queue_item_id": "queue-1",
        "slice_id": "FOUNDUP_SCOPED_SAMPLE_PHASE1",
        "claim_id": "claim-1",
        "worker_id": "reddog-0102",
        "status": "QUEUED",
        "evidence_refs": ["claim:claim-1", "freshness:fresh-1"],
        "no_execution_performed": True,
    }
    queue_item.update(queue_overrides)
    queue_item = with_queue_wsp15_allocation(queue_item)
    return {
        "schema_version": "reddog_authoritative_work_state.v1",
        "freshness_receipts": [{"receipt_id": "fresh-1", "fresh": True}],
        "worker_claims": [
            {
                "claim_id": "claim-1",
                "slice_id": "FOUNDUP_SCOPED_SAMPLE_PHASE1",
                "worker_id": "reddog-0102",
                "status": "ACTIVE",
                "expires_at": EXPIRES,
                "freshness_receipt_id": "fresh-1",
            }
        ],
        "wre_queue_items": [queue_item],
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
        "base_ref": "main",
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


class _WorkOrderResolver:
    def resolve(self, *, work_order_id, queue_item_id, selected_slice):
        return {
            "work_order_id": work_order_id,
            "base_ref": "main",
            "branch_name": "feat/authority-request-binding",
        }


def _handler(**profile_overrides: object):
    return build_reddog_resident_queue_authority_request_stage_handler(
        work_state_snapshot=_snapshot(),
        authority_profile=_profile(**profile_overrides),
        work_order_resolver=_WorkOrderResolver(),
        now_iso=NOW,
    )


def test_handler_builds_authority_request_dryrun_without_signing() -> None:
    request = type(
        "Request",
        (),
        {
            "stage_key": AUTHORITY_REQUEST_STAGE_KEY,
            "next_action": NEXT_QUEUE_AUTHORITY_REQUEST_DRYRUN,
            "queue_item_id": "queue-1",
            "selected_slice": "FOUNDUP_SCOPED_SAMPLE_PHASE1",
        },
    )()

    result = dict(_handler()(request))

    assert result["accepted"] is True
    assert result["status"] == QUEUE_AUTHORITY_REQUEST_DRYRUN_ACCEPT
    assert result["signer_invoked"] is False
    assert result["no_signing_performed"] is True
    assert result["no_signer_state_mutation_performed"] is True
    assert result["no_worker_spawn_performed"] is True
    assert result["no_worktree_created"] is True
    assert result["no_shell_command_executed"] is True
    assert result["no_openclaw_enqueue_performed"] is True
    assert result["no_hermes_dispatch_performed"] is True
    assert result["no_repo_mutation_performed"] is True
    assert result["no_holoindex_reindex_performed"] is True
    assert result["no_pr_created"] is True
    assert result["no_reward_settlement_performed"] is True
    assert result["delegated_authority_request"]["requested_operation"] == "create_foundup"


def test_architect_fix_request_requires_current_committed_publication() -> None:
    committed, profile, queue_id, _ = with_architect_fix_publication(
        _snapshot(),
        _profile(),
    )
    prepared, _, _, _ = with_architect_fix_publication(
        _snapshot(),
        _profile(),
        state="STATE_PREPARED",
    )
    current = {"value": committed}
    handler = build_reddog_resident_queue_authority_request_stage_handler(
        work_state_snapshot=committed,
        authority_profile=profile,
        work_order_resolver=_WorkOrderResolver(),
        now_iso=NOW,
        work_state_supplier=lambda: current["value"],
    )
    request = type(
        "Request",
        (),
        {
            "stage_key": AUTHORITY_REQUEST_STAGE_KEY,
            "next_action": NEXT_QUEUE_AUTHORITY_REQUEST_DRYRUN,
            "queue_item_id": queue_id,
            "selected_slice": "FOUNDUP_SCOPED_SAMPLE_PHASE1",
        },
    )()

    accepted = dict(handler(request))
    current["value"] = prepared
    rejected = dict(handler(request))

    assert accepted["accepted"] is True
    assert accepted["delegated_authority_request"][
        "architect_fix_publication_receipt_id"
    ] == profile["promotion_publication_id"]
    assert accepted["delegated_authority_request"][
        "architect_fix_publication_binding_digest"
    ].startswith("sha256:")
    assert rejected["accepted"] is False
    assert FAIL_ARCHITECT_FIX_PUBLICATION_NOT_COMMITTED in rejected[
        "rejection_reasons"
    ]


def test_dispatcher_records_handler_result_and_advances_to_authority_runtime() -> None:
    store = InMemoryResidentQueueChainResultsStore()

    result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_snapshot(),
        store=store,
        handlers={AUTHORITY_REQUEST_STAGE_KEY: _handler()},
        now_iso=NOW,
    )

    assert result.accepted is True
    assert result.decision == RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_ACCEPT
    assert result.dispatched_stage == AUTHORITY_REQUEST_STAGE_KEY
    assert result.next_action == NEXT_QUEUE_AUTHORITY_RUNTIME_INVOKE
    state = store.load()
    stage = state["stage_results"][AUTHORITY_REQUEST_STAGE_KEY]
    assert stage["status"] == QUEUE_AUTHORITY_REQUEST_DRYRUN_ACCEPT
    assert stage["delegated_authority_request"]["foundup_id"] == "paccess_001"
    assert state["no_bridge_invoked"] is True
    assert state["no_authority_issued"] is True


def test_wrong_stage_rejects_and_dispatcher_does_not_record() -> None:
    request = type(
        "Request",
        (),
        {
            "stage_key": "authority_runtime",
            "next_action": NEXT_QUEUE_AUTHORITY_REQUEST_DRYRUN,
            "queue_item_id": "queue-1",
            "selected_slice": "FOUNDUP_SCOPED_SAMPLE_PHASE1",
        },
    )()

    result = dict(_handler()(request))

    assert result["accepted"] is False
    assert result["status"] == QUEUE_AUTHORITY_REQUEST_DRYRUN_REJECT
    assert FAIL_DISPATCH_STAGE_MISMATCH in result["rejection_reasons"]


def test_wrong_next_action_rejects() -> None:
    request = type(
        "Request",
        (),
        {
            "stage_key": AUTHORITY_REQUEST_STAGE_KEY,
            "next_action": NEXT_QUEUE_AUTHORITY_RUNTIME_INVOKE,
            "queue_item_id": "queue-1",
            "selected_slice": "FOUNDUP_SCOPED_SAMPLE_PHASE1",
        },
    )()

    result = dict(_handler()(request))

    assert result["accepted"] is False
    assert FAIL_DISPATCH_NEXT_ACTION_MISMATCH in result["rejection_reasons"]


def test_queue_selection_mismatch_rejects() -> None:
    request = type(
        "Request",
        (),
        {
            "stage_key": AUTHORITY_REQUEST_STAGE_KEY,
            "next_action": NEXT_QUEUE_AUTHORITY_REQUEST_DRYRUN,
            "queue_item_id": "missing-queue",
            "selected_slice": "FOUNDUP_SCOPED_SAMPLE_PHASE1",
        },
    )()

    result = dict(_handler()(request))

    assert result["accepted"] is False
    assert FAIL_QUEUE_SELECTION_MISMATCH in result["rejection_reasons"]


def test_profile_rejection_is_not_persisted_by_dispatcher() -> None:
    store = InMemoryResidentQueueChainResultsStore()

    result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_snapshot(),
        store=store,
        handlers={AUTHORITY_REQUEST_STAGE_KEY: _handler(principal_public_key="")},
        now_iso=NOW,
    )

    assert result.accepted is False
    assert FAIL_RECORD_REJECTED in result.rejection_reasons
    assert "FAIL_REQUIRED_FIELD:principal_public_key" in result.rejection_reasons
    assert store.load() == {}


def test_module_has_no_signer_runtime_execution_or_later_stage_imports() -> None:
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
        "replace",
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
