"""Tests for REDDOG_RESIDENT_QUEUE_AUTHORITY_RUNTIME_HANDLER_PHASE1."""

from __future__ import annotations

import ast
import hashlib
import hmac
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_resident_queue_authority_request_handler import (
    build_reddog_resident_queue_authority_request_stage_handler,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_authority_runtime_handler import (
    AUTHORITY_REQUEST_STAGE_KEY,
    AUTHORITY_RUNTIME_STAGE_KEY,
    FAIL_AUTHORITY_REQUEST_STAGE_MISSING,
    FAIL_DISPATCH_NEXT_ACTION_MISMATCH,
    FAIL_DISPATCH_STAGE_MISMATCH,
    build_reddog_resident_queue_authority_runtime_stage_handler,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    InMemoryResidentQueueChainResultsStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_next_stage_dispatch import (
    FAIL_RECORD_REJECTED,
    RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_ACCEPT,
    ResidentQueueStageDispatchRequest,
    invoke_reddog_resident_queue_next_stage_dispatch,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    NEXT_QUEUE_AUTHORITY_RUNTIME_INVOKE,
    NEXT_QUEUE_AUTHORITY_VERIFICATION_INVOKE,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    AUTHORITY_ISSUED,
    InMemoryAuthorityRuntimeStore,
    PrincipalAuthorityRecord,
    RuntimeRejectCode,
    SigningResponse,
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    PermissionSnapshot,
)
from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    VALVE_OPEN_WORKTREE_CREATE,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authority_runtime_invoke import (
    QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT,
    QUEUE_AUTHORITY_RUNTIME_INVOKE_REJECT,
)
from modules.communication.moltbot_bridge.src.reddog_wsp15_allocation_receipt import (
    allocate_reddog_wsp15_receipt,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_resident_queue_authority_runtime_handler.py"
)
NOW_ISO = "2026-07-14T00:00:00+00:00"
NOW = 1000
EXPIRES = "2026-07-14T01:00:00+00:00"
REPO = "FOUNDUPS/Foundups-Agent"
FID = "paccess_001"
_DEFAULT_SIGNER = object()


def _queue_wsp15_allocation_receipt() -> dict[str, object]:
    return allocate_reddog_wsp15_receipt(
        requested_operation="create_foundup",
        prompt_text="RedDog resident queue authority runtime worktree authority",
        changed_paths=("modules/communication/moltbot_bridge/src/reddog_resident_queue_authority_runtime_handler.py",),
        allowed_read_targets=("modules/communication/moltbot_bridge/src/reddog_resident_queue_authority_runtime_handler.py",),
    ).to_dict()


class _MockSigner:
    def __init__(self) -> None:
        self.secrets = {
            "pub:principal": b"principal-secret",
            "pub:reddog": b"reddog-secret",
        }
        self.requests = []

    def sign(self, request):
        self.requests.append(request)
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


class _SnapshotResolver:
    def resolve(self, digest: str):
        if digest == "sha256:snap-1":
            return PermissionSnapshot(
                evidence_digest="sha256:snap-1",
                expires_at=NOW + 600,
                can_write=True,
                repo_full_name=REPO,
            )
        return None


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
        "valve_state_required": VALVE_OPEN_WORKTREE_CREATE,
        "key_epoch": "epoch-1",
        "consensus_receipt_digest": "sha256:consensus",
        "sovereign_authorization_digest": "sha256:012-token",
    }


def _seed_authority_request(store: InMemoryResidentQueueChainResultsStore) -> None:
    handler = build_reddog_resident_queue_authority_request_stage_handler(
        work_state_snapshot=_snapshot(),
        authority_profile=_profile(),
        now_iso=NOW_ISO,
    )
    result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_snapshot(),
        store=store,
        handlers={AUTHORITY_REQUEST_STAGE_KEY: handler},
        now_iso=NOW_ISO,
    )
    assert result.accepted is True


def _runtime_handler(
    *,
    chain_store: InMemoryResidentQueueChainResultsStore,
    authority_store: InMemoryAuthorityRuntimeStore | None = None,
    signer: object | None = _DEFAULT_SIGNER,
):
    return build_reddog_resident_queue_authority_runtime_stage_handler(
        chain_results_store=chain_store,
        authority_store=authority_store or InMemoryAuthorityRuntimeStore(),
        signer=_MockSigner() if signer is _DEFAULT_SIGNER else signer,
        principal_resolver=_PrincipalResolver(),
        snapshot_resolver=_SnapshotResolver(),
        now=NOW,
    )


def test_dispatcher_records_authority_runtime_result_and_advances_to_verification() -> None:
    chain_store = InMemoryResidentQueueChainResultsStore()
    _seed_authority_request(chain_store)
    authority_store = InMemoryAuthorityRuntimeStore()
    signer = _MockSigner()

    result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_snapshot(),
        store=chain_store,
        handlers={
            AUTHORITY_RUNTIME_STAGE_KEY: _runtime_handler(
                chain_store=chain_store,
                authority_store=authority_store,
                signer=signer,
            )
        },
        now_iso=NOW_ISO,
    )

    assert result.accepted is True
    assert result.decision == RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_ACCEPT
    assert result.dispatched_stage == AUTHORITY_RUNTIME_STAGE_KEY
    assert result.next_action == NEXT_QUEUE_AUTHORITY_VERIFICATION_INVOKE
    assert len(signer.requests) == 2
    state = chain_store.load()
    stage = state["stage_results"][AUTHORITY_RUNTIME_STAGE_KEY]
    assert stage["decision"] == QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT
    assert stage["authority_result"]["receipt"]["status"] == AUTHORITY_ISSUED
    assert stage["no_worker_spawn_performed"] is True
    assert stage["no_openclaw_enqueue_performed"] is True
    assert state["no_repo_mutation_performed"] is True


def test_missing_authority_request_stage_rejects_direct_handler_call() -> None:
    handler = _runtime_handler(chain_store=InMemoryResidentQueueChainResultsStore())
    request = ResidentQueueStageDispatchRequest(
        stage_key=AUTHORITY_RUNTIME_STAGE_KEY,
        next_action=NEXT_QUEUE_AUTHORITY_RUNTIME_INVOKE,
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(AUTHORITY_REQUEST_STAGE_KEY,),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_AUTHORITY_RUNTIME_INVOKE_REJECT
    assert FAIL_AUTHORITY_REQUEST_STAGE_MISSING in result["rejection_reasons"]


def test_wrong_stage_rejects_direct_handler_call() -> None:
    handler = _runtime_handler(chain_store=InMemoryResidentQueueChainResultsStore())
    request = ResidentQueueStageDispatchRequest(
        stage_key="authority_request",
        next_action=NEXT_QUEUE_AUTHORITY_RUNTIME_INVOKE,
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_AUTHORITY_RUNTIME_INVOKE_REJECT
    assert FAIL_DISPATCH_STAGE_MISMATCH in result["rejection_reasons"]


def test_wrong_next_action_rejects_direct_handler_call() -> None:
    handler = _runtime_handler(chain_store=InMemoryResidentQueueChainResultsStore())
    request = ResidentQueueStageDispatchRequest(
        stage_key=AUTHORITY_RUNTIME_STAGE_KEY,
        next_action="RUN_QUEUE_AUTHORITY_REQUEST_DRYRUN",
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(AUTHORITY_REQUEST_STAGE_KEY,),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_AUTHORITY_RUNTIME_INVOKE_REJECT
    assert FAIL_DISPATCH_NEXT_ACTION_MISMATCH in result["rejection_reasons"]


def test_runtime_rejection_is_not_recorded_by_dispatcher() -> None:
    chain_store = InMemoryResidentQueueChainResultsStore()
    _seed_authority_request(chain_store)

    result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_snapshot(),
        store=chain_store,
        handlers={
            AUTHORITY_RUNTIME_STAGE_KEY: _runtime_handler(
                chain_store=chain_store,
                signer=None,
            )
        },
        now_iso=NOW_ISO,
    )

    assert result.accepted is False
    assert FAIL_RECORD_REJECTED in result.rejection_reasons
    assert RuntimeRejectCode.SIGNER_NOT_CONFIGURED in result.rejection_reasons
    assert AUTHORITY_RUNTIME_STAGE_KEY not in chain_store.load()["stage_results"]


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
