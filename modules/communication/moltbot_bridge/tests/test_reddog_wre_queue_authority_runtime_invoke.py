"""Tests for REDDOG_WRE_QUEUE_AUTHORITY_RUNTIME_INVOKE_PHASE1."""

from __future__ import annotations

import ast
import hashlib
import hmac
from pathlib import Path

from modules.communication.moltbot_bridge.src import (
    reddog_wre_queue_authority_request_dryrun as planner,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    AUTHORITY_ISSUED,
    DelegatedAuthorityRuntimeRequest,
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
    QueueAuthorityRuntimeInvokeReason,
    invoke_reddog_wre_queue_authority_runtime,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_consumer_dryrun import (
    NEXT_GATE_SIGNED_AUTHORITY_REQUIRED,
    WRE_QUEUE_CONSUMER_DRYRUN_READY,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_wre_queue_authority_runtime_invoke.py"
)
NOW = 1000
REPO = "FOUNDUPS/Foundups-Agent"
FID = "paccess_001"


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


def _queue_result():
    receipt = {
        "receipt_id": "wre_queue_consumer_1234",
        "queue_item_id": "queue-1",
        "slice_id": "FOUNDUP_SCOPED_SAMPLE_PHASE1",
        "claim_id": "claim-1",
        "worker_id": "reddog-main-bootstrap",
        "freshness_receipt_id": "fresh-1",
        "wsp15_allocation_receipt_id": "sha256:wsp15-allocation",
        "wsp15_allocation_digest": "sha256:wsp15-allocation-digest",
        "wsp15_priority": "P0",
        "wsp15_mps_total": 20,
        "reasoning_tier": "ULTRA",
        "model_runtime_binding_receipt_id": "reddog_model_runtime_binding:abc123",
        "model_runtime_binding_digest": "sha256:model-runtime-binding",
        "next_required_gate": NEXT_GATE_SIGNED_AUTHORITY_REQUIRED,
        "execution_ready": False,
        "no_queue_mutation_performed": True,
    }
    return {
        "accepted": True,
        "status": WRE_QUEUE_CONSUMER_DRYRUN_READY,
        "rejection_reasons": [],
        "receipt": receipt,
        "selected_queue_item_id": "queue-1",
        "selected_slice": "FOUNDUP_SCOPED_SAMPLE_PHASE1",
        "next_required_gate": NEXT_GATE_SIGNED_AUTHORITY_REQUIRED,
        "execution_ready": False,
    }


def _profile(**overrides):
    profile = {
        "principal_id": "github:mjtrout",
        "principal_provider": "github",
        "principal_public_key": "pub:principal",
        "reddog_id": "reddog:abc123",
        "reddog_public_key": "pub:reddog",
        "repo_full_name": REPO,
        "foundup_id": FID,
        "base_ref": "main",
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
        "model_runtime_binding_receipt_id": "reddog_model_runtime_binding:abc123",
        "model_runtime_binding_digest": "sha256:model-runtime-binding",
    }
    profile.update(overrides)
    return profile


def _dryrun():
    work_order = {
        "work_order_id": "wre-queue-" + hashlib.sha256(b"queue-1").hexdigest()[:16],
        "base_ref": "main",
        "branch_name": "feat/runtime-authority-binding",
    }
    return planner.plan_reddog_wre_queue_authority_request_dry_run(
        queue_consumer_result=_queue_result(),
        authority_profile=_profile(),
        work_order=work_order,
    ).to_dict()


def test_explicit_invoke_missing_rejects_before_signer_call() -> None:
    signer = _MockSigner()

    result = invoke_reddog_wre_queue_authority_runtime(
        explicit_queue_authority_runtime_requested=False,
        queue_authority_request_dryrun=_dryrun(),
        store=InMemoryAuthorityRuntimeStore(),
        signer=signer,
        principal_resolver=_PrincipalResolver(),
        snapshot_resolver=_SnapshotResolver(),
        now=NOW,
    )

    assert result.decision == QUEUE_AUTHORITY_RUNTIME_INVOKE_REJECT
    assert QueueAuthorityRuntimeInvokeReason.EXPLICIT_INVOKE_MISSING in result.rejection_reasons
    assert signer.requests == []


def test_rejected_dryrun_rejects_before_signer_call() -> None:
    signer = _MockSigner()
    dryrun = _dryrun()
    dryrun["accepted"] = False

    result = invoke_reddog_wre_queue_authority_runtime(
        explicit_queue_authority_runtime_requested=True,
        queue_authority_request_dryrun=dryrun,
        store=InMemoryAuthorityRuntimeStore(),
        signer=signer,
        principal_resolver=_PrincipalResolver(),
        snapshot_resolver=_SnapshotResolver(),
        now=NOW,
    )

    assert result.decision == QUEUE_AUTHORITY_RUNTIME_INVOKE_REJECT
    assert QueueAuthorityRuntimeInvokeReason.REQUEST_DRYRUN_NOT_ACCEPTED in result.rejection_reasons
    assert signer.requests == []


def test_invalid_request_payload_rejects_before_signer_call() -> None:
    signer = _MockSigner()
    dryrun = _dryrun()
    dryrun["delegated_authority_request"] = {"work_order_id": "incomplete"}

    result = invoke_reddog_wre_queue_authority_runtime(
        explicit_queue_authority_runtime_requested=True,
        queue_authority_request_dryrun=dryrun,
        store=InMemoryAuthorityRuntimeStore(),
        signer=signer,
        principal_resolver=_PrincipalResolver(),
        snapshot_resolver=_SnapshotResolver(),
        now=NOW,
    )

    assert result.decision == QUEUE_AUTHORITY_RUNTIME_INVOKE_REJECT
    assert QueueAuthorityRuntimeInvokeReason.REQUEST_PAYLOAD_INVALID in result.rejection_reasons
    assert signer.requests == []


def test_substituted_valid_request_rejects_before_signer_or_store_effect() -> None:
    signer = _MockSigner()
    store = InMemoryAuthorityRuntimeStore()
    initial_state = store.load()
    dryrun = _dryrun()
    request = dryrun["delegated_authority_request"]
    request["memex_supply_receipt_id"] = "memex-supply-attacker"
    request["memex_supply_digest"] = "sha256:" + "7" * 64

    result = invoke_reddog_wre_queue_authority_runtime(
        explicit_queue_authority_runtime_requested=True,
        queue_authority_request_dryrun=dryrun,
        store=store,
        signer=signer,
        principal_resolver=_PrincipalResolver(),
        snapshot_resolver=_SnapshotResolver(),
        now=NOW,
    )

    assert result.decision == QUEUE_AUTHORITY_RUNTIME_INVOKE_REJECT
    assert (
        QueueAuthorityRuntimeInvokeReason.REQUEST_DIGEST_MISMATCH
        in result.rejection_reasons
    )
    assert signer.requests == []
    assert store.load() == initial_state


def test_falsy_non_string_request_substitution_rejects_without_effect() -> None:
    for value in (0, False, [], {}):
        signer = _MockSigner()
        store = InMemoryAuthorityRuntimeStore()
        initial_state = store.load()
        dryrun = _dryrun()
        dryrun["delegated_authority_request"]["memex_supply_receipt_id"] = value

        result = invoke_reddog_wre_queue_authority_runtime(
            explicit_queue_authority_runtime_requested=True,
            queue_authority_request_dryrun=dryrun,
            store=store,
            signer=signer,
            principal_resolver=_PrincipalResolver(),
            snapshot_resolver=_SnapshotResolver(),
            now=NOW,
        )

        assert result.decision == QUEUE_AUTHORITY_RUNTIME_INVOKE_REJECT
        assert (
            QueueAuthorityRuntimeInvokeReason.REQUEST_PAYLOAD_INVALID
            in result.rejection_reasons
        )
        assert signer.requests == []
        assert store.load() == initial_state


def test_default_signer_rejection_is_preserved() -> None:
    result = invoke_reddog_wre_queue_authority_runtime(
        explicit_queue_authority_runtime_requested=True,
        queue_authority_request_dryrun=_dryrun(),
        store=InMemoryAuthorityRuntimeStore(),
        signer=None,
        principal_resolver=_PrincipalResolver(),
        snapshot_resolver=_SnapshotResolver(),
        now=NOW,
    )

    assert result.decision == QUEUE_AUTHORITY_RUNTIME_INVOKE_REJECT
    assert QueueAuthorityRuntimeInvokeReason.AUTHORITY_RUNTIME_REJECTED in result.rejection_reasons
    assert RuntimeRejectCode.SIGNER_NOT_CONFIGURED in result.rejection_reasons
    assert result.authority_result is not None
    assert result.authority_result.accepted is False


def test_invokes_injected_signer_and_issues_authority_without_execution() -> None:
    signer = _MockSigner()
    store = InMemoryAuthorityRuntimeStore()

    result = invoke_reddog_wre_queue_authority_runtime(
        explicit_queue_authority_runtime_requested=True,
        queue_authority_request_dryrun=_dryrun(),
        store=store,
        signer=signer,
        principal_resolver=_PrincipalResolver(),
        snapshot_resolver=_SnapshotResolver(),
        now=NOW,
    )

    assert result.decision == QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT
    assert result.rejection_reasons == []
    assert result.authority_result is not None
    assert result.authority_result.accepted is True
    assert result.authority_result.receipt.status == AUTHORITY_ISSUED
    assert result.authority_result.receipt.no_execution_performed is True
    assert result.authority_result.receipt.no_worker_spawn_performed is True
    assert result.authority_result.receipt.no_openclaw_enqueue_performed is True
    assert result.authority_result.work_authority is not None
    assert result.authority_result.work_authority["model_runtime_binding_receipt_id"] == (
        "reddog_model_runtime_binding:abc123"
    )
    assert len(signer.requests) == 2
    state = store.load()
    assert state["issued_authorities"]
    assert result.no_worker_spawn_performed is True
    assert result.no_worktree_created is True
    assert result.no_shell_command_executed is True
    assert result.no_openclaw_enqueue_performed is True
    assert result.no_hermes_dispatch_performed is True
    assert result.no_repo_mutation_performed is True
    assert result.no_holoindex_reindex_performed is True
    assert result.no_pr_created is True
    assert result.no_reward_settlement_performed is True


def test_payload_round_trips_into_runtime_request_type() -> None:
    dryrun = _dryrun()
    request = dryrun["delegated_authority_request"]

    typed = DelegatedAuthorityRuntimeRequest(
        work_order_id=str(request["work_order_id"]),
        work_order_digest=str(request["work_order_digest"]),
        base_ref=str(request["base_ref"]),
        principal_id=str(request["principal_id"]),
        principal_provider=str(request["principal_provider"]),
        principal_public_key=str(request["principal_public_key"]),
        reddog_id=str(request["reddog_id"]),
        reddog_public_key=str(request["reddog_public_key"]),
        repo_full_name=str(request["repo_full_name"]),
        foundup_id=str(request["foundup_id"]),
        allowed_paths=tuple(request["allowed_paths"]),
        denied_paths=tuple(request["denied_paths"]),
        requested_operation=str(request["requested_operation"]),
        permission_snapshot_digest=str(request["permission_snapshot_digest"]),
        queue_consumer_receipt_digest=str(request["queue_consumer_receipt_digest"]),
        wsp15_allocation_receipt_id=str(request["wsp15_allocation_receipt_id"]),
        wsp15_allocation_digest=str(request["wsp15_allocation_digest"]),
        wsp15_priority=str(request["wsp15_priority"]),
        wsp15_mps_total=int(request["wsp15_mps_total"]),
        wsp15_reasoning_tier=str(request["wsp15_reasoning_tier"]),
        model_runtime_binding_receipt_id=str(request["model_runtime_binding_receipt_id"]),
        model_runtime_binding_digest=str(request["model_runtime_binding_digest"]),
        identity_nonce=str(request["identity_nonce"]),
        work_authority_nonce=str(request["work_authority_nonce"]),
        issued_at=int(request["issued_at"]),
        identity_expires_at=int(request["identity_expires_at"]),
        work_authority_expires_at=int(request["work_authority_expires_at"]),
        valve_state_required=str(request["valve_state_required"]),
        key_epoch=str(request["key_epoch"]),
        consensus_receipt_digest=str(request["consensus_receipt_digest"]),
        sovereign_authorization_digest=str(request["sovereign_authorization_digest"]),
    )

    assert typed.to_dict() == request


def test_module_has_no_shell_network_worktree_openclaw_hermes_or_holoindex_imports() -> None:
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
