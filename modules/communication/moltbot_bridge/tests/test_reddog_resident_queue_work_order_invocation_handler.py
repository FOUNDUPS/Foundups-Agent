"""Tests for REDDOG_RESIDENT_QUEUE_WORK_ORDER_INVOCATION_HANDLER_PHASE1."""

from __future__ import annotations

import ast
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_resident_queue_authority_request_handler import (
    AUTHORITY_REQUEST_STAGE_KEY,
    build_reddog_resident_queue_authority_request_stage_handler,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_authority_runtime_handler import (
    AUTHORITY_RUNTIME_STAGE_KEY,
    build_reddog_resident_queue_authority_runtime_stage_handler,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_authority_verification_handler import (
    AUTHORITY_VERIFICATION_STAGE_KEY,
    build_reddog_resident_queue_authority_verification_stage_handler,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    InMemoryResidentQueueChainResultsStore,
    record_resident_queue_stage_result,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_next_stage_dispatch import (
    FAIL_RECORD_REJECTED,
    RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_ACCEPT,
    ResidentQueueStageDispatchRequest,
    invoke_reddog_resident_queue_next_stage_dispatch,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    NEXT_QUEUE_EXECUTOR_PLAN_DRYRUN,
    NEXT_QUEUE_WORK_ORDER_INVOCATION,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_worker_dispatch_dryrun_handler import (
    WORKER_DISPATCH_DRYRUN_STAGE_KEY,
    build_reddog_resident_queue_worker_dispatch_dryrun_stage_handler,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_worker_dispatch_runtime_handler import (
    WORKER_DISPATCH_RUNTIME_STAGE_KEY,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_work_order_invocation_handler import (
    FAIL_AUTHORITY_RUNTIME_STAGE_MISSING,
    FAIL_AUTHORITY_VERIFICATION_STAGE_MISSING,
    FAIL_DISPATCH_NEXT_ACTION_MISMATCH,
    FAIL_DISPATCH_STAGE_MISMATCH,
    FAIL_WORK_ORDER_MISSING,
    WORK_ORDER_INVOCATION_STAGE_KEY,
    build_reddog_resident_queue_work_order_invocation_stage_handler,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    InMemoryAuthorityRuntimeStore,
    PrincipalAuthorityRecord,
    RuntimeRejectCode,
    SigningResponse,
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    InMemoryNonceStore,
    PermissionSnapshot,
)
from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    VALVE_OPEN_WORKTREE_CREATE,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_verified_authority_work_order_invoke import (
    QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_ACCEPT,
    QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_REJECT,
    QueueVerifiedAuthorityWorkOrderInvokeReason,
)
from modules.communication.moltbot_bridge.src.reddog_wsp15_allocation_receipt import (
    allocate_reddog_wsp15_receipt,
)
from modules.communication.moltbot_bridge.tests.reddog_resident_queue_test_helpers import (
    WORKER_DISPATCH_RUNTIME_STAGE_RESULT,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_resident_queue_work_order_invocation_handler.py"
)
NOW_ISO = "2026-07-14T00:00:00+00:00"
NOW_SECONDS = 1000
NOW_DT = datetime(2026, 7, 14, 0, 0, 0, tzinfo=timezone.utc)
EXPIRES = "2026-07-14T01:00:00+00:00"
WORK_ORDER_ID = "wre-queue-work-order-invocation-001"
REPO = "FOUNDUPS/Foundups-Agent"
FID = "paccess_001"
ALLOWED = [f"modules/foundups/{FID}/**"]
DENIED: list[str] = []
OPERATION = "create_foundup"


def _queue_wsp15_allocation_receipt() -> dict[str, object]:
    return allocate_reddog_wsp15_receipt(
        requested_operation=OPERATION,
        prompt_text="RedDog resident queue work order invocation worktree authority",
        changed_paths=("modules/communication/moltbot_bridge/src/reddog_resident_queue_work_order_invocation_handler.py",),
        allowed_read_targets=("modules/communication/moltbot_bridge/src/reddog_resident_queue_work_order_invocation_handler.py",),
    ).to_dict()


class _MockSignerVerifier:
    def __init__(self) -> None:
        self.secrets = {
            "pub:principal": b"principal-secret",
            "pub:reddog": b"reddog-secret",
        }

    def sign(self, request):
        secret = self.secrets.get(request.signer_public_key)
        if secret is None:
            return SigningResponse(
                accepted=False,
                rejection_code=RuntimeRejectCode.SIGNER_NOT_CONFIGURED,
            )
        signature = hmac.new(secret, request.signing_input.encode("utf-8"), hashlib.sha256).hexdigest()
        audit = hmac.new(secret, request.payload_digest.encode("utf-8"), hashlib.sha256).hexdigest()
        return SigningResponse(
            accepted=True,
            signature=signature,
            signer_public_key=request.signer_public_key,
            key_fingerprint=public_key_fingerprint(request.signer_public_key),
            key_epoch=request.key_epoch,
            audit_mac="audit:" + audit,
            boundary_attested=True,
            requester_identity_attested=True,
            signer_loads_no_untrusted_code=True,
            no_secret_material_returned=True,
        )

    def verify(self, public_key: str, signing_input: str, signature: str) -> bool:
        secret = self.secrets.get(public_key)
        if secret is None:
            return False
        expected = hmac.new(secret, signing_input.encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)


class _PrincipalResolver:
    def resolve(self, principal_id: str, principal_provider: str):
        if principal_id == "github:mjtrout" and principal_provider == "github":
            return PrincipalAuthorityRecord(
                principal_id="github:mjtrout",
                principal_provider="github",
                principal_public_key="pub:principal",
                repo_scope=(REPO,),
                foundup_scope=(FID,),
                verified_subject_digest="sha256:verified-subject",
                reward_account="reward:012",
                owner_dae="dae:012",
            )
        return None


class _PrincipalKeyResolver:
    def resolve(self, principal_id: str, principal_provider: str):
        if principal_id == "github:mjtrout" and principal_provider == "github":
            return "pub:principal"
        return None


class _SnapshotResolver:
    def resolve(self, digest: str):
        if digest == "sha256:snap-1":
            return PermissionSnapshot(
                evidence_digest="sha256:snap-1",
                expires_at=NOW_SECONDS + 600,
                can_write=True,
                repo_full_name=REPO,
            )
        return None


class _NoRevocation:
    def is_revoked(self, *, reddog_id: str, fingerprint: str, principal_id: str, key_epoch: str) -> bool:
        return False


class _Resolver:
    def __init__(self, work_order: dict[str, object] | None) -> None:
        self.work_order = work_order
        self.calls: list[dict[str, object | None]] = []

    def resolve(self, *, work_order_id: str, queue_item_id: str | None, selected_slice: str | None):
        self.calls.append(
            {
                "work_order_id": work_order_id,
                "queue_item_id": queue_item_id,
                "selected_slice": selected_slice,
            }
        )
        return self.work_order or {}


def _future_expiry(minutes: int = 30) -> str:
    return (NOW_DT + timedelta(minutes=minutes)).replace(microsecond=0).isoformat()


def _fresh_captured() -> str:
    return (NOW_DT - timedelta(seconds=30)).replace(microsecond=0).isoformat()


def _snapshot() -> dict[str, object]:
    allocation = _queue_wsp15_allocation_receipt()
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
                "evidence_refs": [
                    "claim:claim-1",
                    "freshness:fresh-1",
                    f"wsp15_allocation:{allocation['receipt_id']}",
                ],
                "wsp15_allocation_receipt": allocation,
                "no_execution_performed": True,
            }
        ],
    }


def _profile() -> dict[str, object]:
    return {
        "work_order_id": WORK_ORDER_ID,
        "principal_id": "github:mjtrout",
        "principal_provider": "github",
        "principal_public_key": "pub:principal",
        "reddog_id": "reddog:abc123",
        "reddog_public_key": "pub:reddog",
        "repo_full_name": REPO,
        "foundup_id": FID,
        "allowed_paths": ALLOWED,
        "denied_paths": DENIED,
        "requested_operation": OPERATION,
        "permission_snapshot_digest": "sha256:snap-1",
        "identity_nonce": "identity-nonce-0001",
        "work_authority_nonce": "workauth-nonce-0001",
        "issued_at": NOW_SECONDS - 5,
        "identity_expires_at": NOW_SECONDS + 3600,
        "work_authority_expires_at": NOW_SECONDS + 300,
        "valve_state_required": VALVE_OPEN_WORKTREE_CREATE,
        "key_epoch": "epoch-1",
        "consensus_receipt_digest": "sha256:consensus",
        "sovereign_authorization_digest": "sha256:012-token",
    }


def _work_order(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
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
        "requested_operation": OPERATION,
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
            "holoindex_query": "RedDog resident queue work-order invocation handler",
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


def _seed_verified_authority(chain_store: InMemoryResidentQueueChainResultsStore, signer: _MockSignerVerifier) -> None:
    request_handler = build_reddog_resident_queue_authority_request_stage_handler(
        work_state_snapshot=_snapshot(),
        authority_profile=_profile(),
        now_iso=NOW_ISO,
    )
    request_result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_snapshot(),
        store=chain_store,
        handlers={AUTHORITY_REQUEST_STAGE_KEY: request_handler},
        now_iso=NOW_ISO,
    )
    assert request_result.accepted is True

    runtime_handler = build_reddog_resident_queue_authority_runtime_stage_handler(
        chain_results_store=chain_store,
        authority_store=InMemoryAuthorityRuntimeStore(),
        signer=signer,
        principal_resolver=_PrincipalResolver(),
        snapshot_resolver=_SnapshotResolver(),
        now=NOW_SECONDS,
    )
    runtime_result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_snapshot(),
        store=chain_store,
        handlers={AUTHORITY_RUNTIME_STAGE_KEY: runtime_handler},
        now_iso=NOW_ISO,
    )
    assert runtime_result.accepted is True

    verification_handler = build_reddog_resident_queue_authority_verification_stage_handler(
        chain_results_store=chain_store,
        signature_verifier=signer,
        principal_key_resolver=_PrincipalKeyResolver(),
        nonce_store=InMemoryNonceStore(),
        snapshot_resolver=_SnapshotResolver(),
        revocation_oracle=_NoRevocation(),
        now=NOW_SECONDS,
        required_valve_state=VALVE_OPEN_WORKTREE_CREATE,
    )
    verification_result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_snapshot(),
        store=chain_store,
        handlers={AUTHORITY_VERIFICATION_STAGE_KEY: verification_handler},
        now_iso=NOW_ISO,
    )
    assert verification_result.accepted is True

    dispatch_handler = build_reddog_resident_queue_worker_dispatch_dryrun_stage_handler(
        work_state_snapshot=_snapshot(),
        chain_results_store=chain_store,
    )
    dispatch_result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_snapshot(),
        store=chain_store,
        handlers={WORKER_DISPATCH_DRYRUN_STAGE_KEY: dispatch_handler},
        now_iso=NOW_ISO,
    )
    assert dispatch_result.accepted is True

    runtime_result = record_resident_queue_stage_result(
        work_state_snapshot=_snapshot(),
        store=chain_store,
        stage_key=WORKER_DISPATCH_RUNTIME_STAGE_KEY,
        stage_result=WORKER_DISPATCH_RUNTIME_STAGE_RESULT,
        now_iso=NOW_ISO,
    )
    assert runtime_result.accepted is True


def _handler(
    *,
    chain_store: InMemoryResidentQueueChainResultsStore,
    resolver: _Resolver | None = None,
):
    return build_reddog_resident_queue_work_order_invocation_stage_handler(
        chain_results_store=chain_store,
        work_order_resolver=resolver or _Resolver(_work_order()),
        now=NOW_DT,
        seen_nonces=set(),
    )


def test_dispatcher_records_work_order_invocation_and_advances_to_executor_plan() -> None:
    chain_store = InMemoryResidentQueueChainResultsStore()
    signer = _MockSignerVerifier()
    _seed_verified_authority(chain_store, signer)
    resolver = _Resolver(_work_order())

    result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_snapshot(),
        store=chain_store,
        handlers={
            WORK_ORDER_INVOCATION_STAGE_KEY: _handler(
                chain_store=chain_store,
                resolver=resolver,
            )
        },
        now_iso=NOW_ISO,
    )

    assert result.accepted is True
    assert result.decision == RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_ACCEPT
    assert result.dispatched_stage == WORK_ORDER_INVOCATION_STAGE_KEY
    assert result.next_action == NEXT_QUEUE_EXECUTOR_PLAN_DRYRUN
    assert resolver.calls == [
        {
            "work_order_id": WORK_ORDER_ID,
            "queue_item_id": "queue-1",
            "selected_slice": "REDDOG_TEST_SLICE_PHASE1",
        }
    ]
    state = chain_store.load()
    stage = state["stage_results"][WORK_ORDER_INVOCATION_STAGE_KEY]
    assert stage["decision"] == QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_ACCEPT
    assert stage["invocation_result"]["work_order_id"] == WORK_ORDER_ID
    assert stage["invocation_result"]["no_execution_performed"] is True
    assert stage["no_worker_spawn_performed"] is True
    assert stage["no_openclaw_enqueue_performed"] is True
    assert stage["no_hermes_dispatch_performed"] is True
    assert stage["no_repo_mutation_performed"] is True
    assert state["no_repo_mutation_performed"] is True


def test_missing_authority_runtime_stage_rejects_direct_handler_call() -> None:
    handler = _handler(chain_store=InMemoryResidentQueueChainResultsStore())
    request = ResidentQueueStageDispatchRequest(
        stage_key=WORK_ORDER_INVOCATION_STAGE_KEY,
        next_action=NEXT_QUEUE_WORK_ORDER_INVOCATION,
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(AUTHORITY_REQUEST_STAGE_KEY,),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_REJECT
    assert FAIL_AUTHORITY_RUNTIME_STAGE_MISSING in result["rejection_reasons"]


def test_missing_authority_verification_stage_rejects_direct_handler_call() -> None:
    chain_store = InMemoryResidentQueueChainResultsStore()
    signer = _MockSignerVerifier()
    request_handler = build_reddog_resident_queue_authority_request_stage_handler(
        work_state_snapshot=_snapshot(),
        authority_profile=_profile(),
        now_iso=NOW_ISO,
    )
    assert invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_snapshot(),
        store=chain_store,
        handlers={AUTHORITY_REQUEST_STAGE_KEY: request_handler},
        now_iso=NOW_ISO,
    ).accepted is True
    runtime_handler = build_reddog_resident_queue_authority_runtime_stage_handler(
        chain_results_store=chain_store,
        authority_store=InMemoryAuthorityRuntimeStore(),
        signer=signer,
        principal_resolver=_PrincipalResolver(),
        snapshot_resolver=_SnapshotResolver(),
        now=NOW_SECONDS,
    )
    assert invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_snapshot(),
        store=chain_store,
        handlers={AUTHORITY_RUNTIME_STAGE_KEY: runtime_handler},
        now_iso=NOW_ISO,
    ).accepted is True
    handler = _handler(chain_store=chain_store)
    request = ResidentQueueStageDispatchRequest(
        stage_key=WORK_ORDER_INVOCATION_STAGE_KEY,
        next_action=NEXT_QUEUE_WORK_ORDER_INVOCATION,
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(AUTHORITY_REQUEST_STAGE_KEY, AUTHORITY_RUNTIME_STAGE_KEY),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_REJECT
    assert FAIL_AUTHORITY_VERIFICATION_STAGE_MISSING in result["rejection_reasons"]


def test_missing_work_order_rejects_direct_handler_call() -> None:
    chain_store = InMemoryResidentQueueChainResultsStore()
    signer = _MockSignerVerifier()
    _seed_verified_authority(chain_store, signer)
    handler = _handler(chain_store=chain_store, resolver=_Resolver(None))
    request = ResidentQueueStageDispatchRequest(
        stage_key=WORK_ORDER_INVOCATION_STAGE_KEY,
        next_action=NEXT_QUEUE_WORK_ORDER_INVOCATION,
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(AUTHORITY_REQUEST_STAGE_KEY, AUTHORITY_RUNTIME_STAGE_KEY, AUTHORITY_VERIFICATION_STAGE_KEY),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_REJECT
    assert FAIL_WORK_ORDER_MISSING in result["rejection_reasons"]
    assert f"work_order_id:{WORK_ORDER_ID}" in result["rejection_reasons"]


def test_wrong_stage_rejects_direct_handler_call() -> None:
    handler = _handler(chain_store=InMemoryResidentQueueChainResultsStore())
    request = ResidentQueueStageDispatchRequest(
        stage_key=AUTHORITY_VERIFICATION_STAGE_KEY,
        next_action=NEXT_QUEUE_WORK_ORDER_INVOCATION,
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(AUTHORITY_REQUEST_STAGE_KEY, AUTHORITY_RUNTIME_STAGE_KEY),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_REJECT
    assert FAIL_DISPATCH_STAGE_MISMATCH in result["rejection_reasons"]


def test_wrong_next_action_rejects_direct_handler_call() -> None:
    handler = _handler(chain_store=InMemoryResidentQueueChainResultsStore())
    request = ResidentQueueStageDispatchRequest(
        stage_key=WORK_ORDER_INVOCATION_STAGE_KEY,
        next_action="RUN_QUEUE_AUTHORITY_VERIFICATION_INVOKE",
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(AUTHORITY_REQUEST_STAGE_KEY, AUTHORITY_RUNTIME_STAGE_KEY),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_REJECT
    assert FAIL_DISPATCH_NEXT_ACTION_MISMATCH in result["rejection_reasons"]


def test_work_order_binding_rejection_is_not_recorded_by_dispatcher() -> None:
    chain_store = InMemoryResidentQueueChainResultsStore()
    signer = _MockSignerVerifier()
    _seed_verified_authority(chain_store, signer)

    result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_snapshot(),
        store=chain_store,
        handlers={
            WORK_ORDER_INVOCATION_STAGE_KEY: _handler(
                chain_store=chain_store,
                resolver=_Resolver(_work_order(allowed_paths=["modules/foundups/other/**"])),
            )
        },
        now_iso=NOW_ISO,
    )

    assert result.accepted is False
    assert FAIL_RECORD_REJECTED in result.rejection_reasons
    assert (
        f"{QueueVerifiedAuthorityWorkOrderInvokeReason.AUTHORITY_WORK_ORDER_BINDING_MISMATCH}:allowed_paths"
        in result.rejection_reasons
    )
    assert WORK_ORDER_INVOCATION_STAGE_KEY not in chain_store.load()["stage_results"]


def test_module_has_no_shell_network_worktree_openclaw_hermes_holoindex_or_later_stage_imports() -> None:
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
        "reddog_wre_queue_authorized",
        "reddog_wre_queue_authorized_executor_plan_dryrun",
        "reddog_wre_queue_authorized_execution_valve_invoke",
        "reddog_wre_queue_authorized_worktree_create_invoke",
        "reddog_wre_queue_authorized_bounded_worker_pilot_invoke",
        "reddog_wre_queue_authorized_slice_verifier_invoke",
        "reddog_wre_queue_authorized_verified_draft_pr_publish_invoke",
        "reddog_wre_queue_authorized_verified_outcome_ratchet_invoke",
        "reddog_wre_queue_authorized_held_out_regression_gate_invoke",
        "reddog_wre_queue_authorized_pattern_memory_admission_invoke",
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
