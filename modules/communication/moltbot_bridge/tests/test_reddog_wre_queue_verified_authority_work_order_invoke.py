"""Tests for REDDOG_WRE_QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOCATION_PHASE1."""

from __future__ import annotations

import ast
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_work_order_receipt import (
    RedDogWorkOrderReceiptStore,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_runtime_invocation import (
    INVOCATION_ACCEPT,
    INVOCATION_REJECT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authority_runtime_invoke import (
    QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authority_verification_invoke import (
    QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT,
    QUEUE_AUTHORITY_VERIFICATION_INVOKE_REJECT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_verified_authority_work_order_invoke import (
    QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_ACCEPT,
    QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_REJECT,
    QueueVerifiedAuthorityWorkOrderInvokeReason,
    invoke_reddog_wre_queue_verified_authority_work_order,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_wre_queue_verified_authority_work_order_invoke.py"
)
NOW = datetime(2026, 7, 14, 12, 0, 0, tzinfo=timezone.utc)
WORK_ORDER_ID = "wre-queue-verified-authority-work-order-001"
REPO = "FOUNDUPS/Foundups-Agent"
FID = "paccess_001"
ALLOWED = [f"modules/foundups/{FID}/**"]
DENIED = [".env", ".git/**"]


def _future_expiry(minutes: int = 30) -> str:
    return (NOW + timedelta(minutes=minutes)).replace(microsecond=0).isoformat()


def _fresh_captured() -> str:
    return (NOW - timedelta(seconds=30)).replace(microsecond=0).isoformat()


def _verification_result(
    *,
    decision: str = QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT,
    accepted: bool = True,
    work_order_id: str = WORK_ORDER_ID,
    reason_codes: list[str] | None = None,
):
    return {
        "decision": decision,
        "rejection_reasons": [],
        "verification_result": {
            "accepted": accepted,
            "reason_codes": list(reason_codes or []),
            "work_order_id": work_order_id,
        },
        "no_signing_performed": True,
        "no_authority_issued": True,
        "no_worker_spawn_performed": True,
        "no_worktree_created": True,
        "no_shell_command_executed": True,
        "no_openclaw_enqueue_performed": True,
        "no_hermes_dispatch_performed": True,
        "no_repo_mutation_performed": True,
        "no_holoindex_reindex_performed": True,
        "no_pr_created": True,
        "no_reward_settlement_performed": True,
    }


def _work_authority(**overrides):
    payload = {
        "work_order_id": WORK_ORDER_ID,
        "principal_id": "github:mjtrout",
        "reddog_id": "reddog:abc123",
        "repo_full_name": REPO,
        "foundup_id": FID,
        "requested_operation": "feature_slice",
        "allowed_paths": ALLOWED,
        "denied_paths": DENIED,
        "permission_snapshot_digest": "sha256:snap-1",
        "valve_state_required": "VALVE_OPEN_WORKTREE_CREATE",
        "issued_at": 1000,
        "expires_at": 1300,
        "nonce": "workauth-nonce-0001",
        "key_epoch": "epoch-1",
        "signer_public_key": "pub:reddog",
        "signature": "signed",
    }
    payload.update(overrides)
    return payload


def _runtime_result(*, accepted: bool = True, status: str = "AUTHORITY_ISSUED", **authority_overrides):
    return {
        "decision": QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT,
        "rejection_reasons": [],
        "authority_result": {
            "accepted": accepted,
            "receipt": {
                "status": status,
                "work_order_id": WORK_ORDER_ID,
                "receipt_id": "authority-runtime-receipt-001",
            },
            "work_authority": _work_authority(**authority_overrides),
        },
    }


def _work_order(**overrides):
    payload = {
        "work_order_id": WORK_ORDER_ID,
        "created_at": _fresh_captured(),
        "red_dog_instance_id": "reddog-main-bootstrap",
        "authenticated_principal": "github:mjtrout",
        "principal_provider": "github",
        "repo_full_name": REPO,
        "repo_permission_snapshot": {
            "permission_level": "write",
            "captured_at": _fresh_captured(),
            "source": "mock",
            "digest": "sha256:snap-1",
        },
        "requested_operation": "feature_slice",
        "authority_tier": "source",
        "allowed_paths": ALLOWED,
        "denied_paths": DENIED,
        "branch_name": "feat/paccess-001-work-order",
        "base_ref": "main",
        "task_summary": "FoundUp scoped worker invocation receipt validation.",
        "wsp_applicability": ["WSP_34", "WSP_50", "WSP_97"],
        "holoindex_evidence_refs": [
            "modules/communication/moltbot_bridge/src/reddog_work_order_runtime_invocation.py"
        ],
        "skillz_candidates": [],
        "required_tests": ["pytest modules/communication/moltbot_bridge/tests"],
        "required_policy_gates": ["openclaw_policy_gate", "signed_work_order_authority"],
        "required_reviewers": [],
        "sentinel_checks": [],
        "rollback_plan": "No live execution performed in this slice.",
        "expiry": _future_expiry(),
        "nonce": "work-order-nonce-0001",
        "evidence_digest": "sha256:" + ("a" * 64),
        "advisory_only_source_packet": {
            "work_focus_digest": "sha256:" + ("b" * 64),
            "wsp_prompt_digest": "sha256:" + ("c" * 64),
            "copy_md_run_trace_digest": "sha256:" + ("d" * 64),
        },
        "holoindex_evidence": {
            "holoindex_query": "RedDog queue verified authority work order invoke",
            "holoindex_status": "bundle_json_ok",
            "code_hits": [
                "modules/communication/moltbot_bridge/src/reddog_work_order_runtime_invocation.py"
            ],
            "wsp_hits": ["WSP_framework/src/WSP_34_Git_Operations_Protocol.md"],
            "skillz_hits": [],
            "direct_read_fallback_used": True,
            "index_gap_detected": False,
            "applicable_wsps": ["WSP_34", "WSP_97"],
            "evidence_refs": [
                "modules/communication/moltbot_bridge/src/reddog_openclaw_work_order_policy_gate.py"
            ],
            "retrieval_quality": "HIGH",
            "skillz_gap_detected": False,
        },
    }
    payload.update(overrides)
    return payload


def test_verified_queue_authority_invokes_existing_work_order_dryrun_and_stores_receipt() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        with RedDogWorkOrderReceiptStore(Path(tmp) / "receipts.db") as store:
            result = invoke_reddog_wre_queue_verified_authority_work_order(
                explicit_queue_work_order_invocation_requested=True,
                queue_authority_verification_result=_verification_result(),
                queue_authority_runtime_result=_runtime_result(),
                work_order=_work_order(),
                seen_nonces=set(),
                receipt_store=store,
                now=NOW,
            )

            assert result.decision == QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_ACCEPT
            assert result.rejection_reasons == []
            assert result.invocation_result is not None
            assert result.invocation_result.decision == INVOCATION_ACCEPT
            assert "signed_work_order_authority" in result.invocation_result.gates_checked
            assert result.no_worker_spawn_performed is True
            assert result.no_worktree_created is True
            assert result.no_shell_command_executed is True
            assert result.no_openclaw_enqueue_performed is True
            assert result.no_hermes_dispatch_performed is True
            assert result.no_repo_mutation_performed is True
            assert result.no_holoindex_reindex_performed is True
            assert result.no_pr_created is True
            assert result.no_reward_settlement_performed is True
            loaded = store.get_by_policy_digest(result.invocation_result.policy_gate_receipt_digest)
            assert loaded is not None
            assert loaded.work_order_id == WORK_ORDER_ID


def test_explicit_invoke_missing_rejects() -> None:
    result = invoke_reddog_wre_queue_verified_authority_work_order(
        explicit_queue_work_order_invocation_requested=False,
        queue_authority_verification_result=_verification_result(),
        queue_authority_runtime_result=_runtime_result(),
        work_order=_work_order(),
        now=NOW,
    )

    assert result.decision == QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_REJECT
    assert QueueVerifiedAuthorityWorkOrderInvokeReason.EXPLICIT_INVOKE_MISSING in result.rejection_reasons
    assert result.invocation_result is None


def test_rejected_verification_blocks_before_work_order_invocation() -> None:
    result = invoke_reddog_wre_queue_verified_authority_work_order(
        explicit_queue_work_order_invocation_requested=True,
        queue_authority_verification_result=_verification_result(
            decision=QUEUE_AUTHORITY_VERIFICATION_INVOKE_REJECT,
            accepted=False,
            reason_codes=["BAD_SIGNATURE"],
        ),
        queue_authority_runtime_result=_runtime_result(),
        work_order=_work_order(),
        now=NOW,
    )

    assert result.decision == QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_REJECT
    assert (
        QueueVerifiedAuthorityWorkOrderInvokeReason.AUTHORITY_VERIFICATION_NOT_ACCEPTED
        in result.rejection_reasons
    )
    assert "BAD_SIGNATURE" in result.rejection_reasons
    assert result.invocation_result is None


def test_unissued_runtime_authority_rejects() -> None:
    result = invoke_reddog_wre_queue_verified_authority_work_order(
        explicit_queue_work_order_invocation_requested=True,
        queue_authority_verification_result=_verification_result(),
        queue_authority_runtime_result=_runtime_result(status="AUTHORITY_REJECTED"),
        work_order=_work_order(),
        now=NOW,
    )

    assert result.decision == QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_REJECT
    assert (
        QueueVerifiedAuthorityWorkOrderInvokeReason.AUTHORITY_RUNTIME_NOT_ACCEPTED
        in result.rejection_reasons
    )
    assert result.invocation_result is None


def test_work_order_id_mismatch_rejects_before_invocation() -> None:
    result = invoke_reddog_wre_queue_verified_authority_work_order(
        explicit_queue_work_order_invocation_requested=True,
        queue_authority_verification_result=_verification_result(),
        queue_authority_runtime_result=_runtime_result(),
        work_order=_work_order(work_order_id="wo-other"),
        now=NOW,
    )

    assert result.decision == QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_REJECT
    assert (
        f"{QueueVerifiedAuthorityWorkOrderInvokeReason.AUTHORITY_WORK_ORDER_BINDING_MISMATCH}:work_order_id"
        in result.rejection_reasons
    )
    assert result.invocation_result is None


def test_path_scope_mismatch_rejects_before_invocation() -> None:
    result = invoke_reddog_wre_queue_verified_authority_work_order(
        explicit_queue_work_order_invocation_requested=True,
        queue_authority_verification_result=_verification_result(),
        queue_authority_runtime_result=_runtime_result(allowed_paths=["modules/**"]),
        work_order=_work_order(),
        now=NOW,
    )

    assert result.decision == QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_REJECT
    assert (
        f"{QueueVerifiedAuthorityWorkOrderInvokeReason.AUTHORITY_WORK_ORDER_BINDING_MISMATCH}:allowed_paths"
        in result.rejection_reasons
    )
    assert result.invocation_result is None


def test_work_order_policy_rejection_is_preserved() -> None:
    result = invoke_reddog_wre_queue_verified_authority_work_order(
        explicit_queue_work_order_invocation_requested=True,
        queue_authority_verification_result=_verification_result(),
        queue_authority_runtime_result=_runtime_result(),
        work_order=_work_order(
            repo_permission_snapshot={
                "permission_level": "write",
                "captured_at": (NOW - timedelta(hours=2)).replace(microsecond=0).isoformat(),
                "source": "mock",
                "digest": "sha256:snap-1",
            }
        ),
        seen_nonces=set(),
        now=NOW,
    )

    assert result.decision == QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_REJECT
    assert (
        QueueVerifiedAuthorityWorkOrderInvokeReason.WORK_ORDER_INVOCATION_REJECTED
        in result.rejection_reasons
    )
    assert "stale_permission_snapshot" in result.rejection_reasons
    assert result.invocation_result is not None
    assert result.invocation_result.decision == INVOCATION_REJECT


def test_result_serializes_nested_invocation_result() -> None:
    result = invoke_reddog_wre_queue_verified_authority_work_order(
        explicit_queue_work_order_invocation_requested=True,
        queue_authority_verification_result=_verification_result(),
        queue_authority_runtime_result=_runtime_result(),
        work_order=_work_order(),
        seen_nonces=set(),
        now=NOW,
    )

    payload = result.to_dict()
    assert payload["decision"] == QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_ACCEPT
    assert payload["invocation_result"]["work_order_id"] == WORK_ORDER_ID
    assert payload["invocation_result"]["no_execution_performed"] is True


def test_module_has_no_execution_or_authority_issue_imports() -> None:
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
    }
    banned_calls = {"eval", "exec", "compile", "__import__"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in banned_calls

    source = MODULE_PATH.read_text(encoding="utf-8")
    forbidden_tokens = (
        "issue_delegated_authority_runtime(",
        "verify_delegated_work_authority(",
        "git ",
        "gh ",
        "worktree add",
        "openclaw_supervisor",
        "hermes_job_executor",
        "holo_index.py --index",
    )
    for token in forbidden_tokens:
        assert token not in source
