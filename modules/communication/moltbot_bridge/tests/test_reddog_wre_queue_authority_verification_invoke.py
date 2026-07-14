"""Tests for REDDOG_WRE_QUEUE_AUTHORITY_VERIFICATION_INVOKE_PHASE1."""

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
    InMemoryAuthorityRuntimeStore,
    PrincipalAuthorityRecord,
    RuntimeRejectCode,
    SigningResponse,
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    InMemoryNonceStore,
    PermissionSnapshot,
    ReasonCode,
)
from modules.communication.moltbot_bridge.src.reddog_wre_execution_valve import (
    VALVE_OPEN_WORKTREE_CREATE,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authority_runtime_invoke import (
    invoke_reddog_wre_queue_authority_runtime,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authority_verification_invoke import (
    QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT,
    QUEUE_AUTHORITY_VERIFICATION_INVOKE_REJECT,
    QueueAuthorityVerificationInvokeReason,
    invoke_reddog_wre_queue_authority_verification,
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
    / "reddog_wre_queue_authority_verification_invoke.py"
)
NOW = 1000
REPO = "FOUNDUPS/Foundups-Agent"
FID = "paccess_001"


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
                expires_at=NOW + 600,
                can_write=True,
                repo_full_name=REPO,
            )
        return None


class _NoRevocation:
    def is_revoked(self, *, reddog_id: str, fingerprint: str, principal_id: str, key_epoch: str) -> bool:
        return False


def _queue_result():
    receipt = {
        "receipt_id": "wre_queue_consumer_1234",
        "queue_item_id": "queue-1",
        "slice_id": "FOUNDUP_SCOPED_SAMPLE_PHASE1",
        "claim_id": "claim-1",
        "worker_id": "reddog-main-bootstrap",
        "freshness_receipt_id": "fresh-1",
        "next_required_gate": NEXT_GATE_SIGNED_AUTHORITY_REQUIRED,
        "execution_ready": False,
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
    profile.update(overrides)
    return profile


def _runtime_result(**profile_overrides):
    signer = _MockSignerVerifier()
    dryrun = planner.plan_reddog_wre_queue_authority_request_dry_run(
        queue_consumer_result=_queue_result(),
        authority_profile=_profile(**profile_overrides),
    )
    assert dryrun.accepted is True, dryrun.rejection_reasons
    result = invoke_reddog_wre_queue_authority_runtime(
        explicit_queue_authority_runtime_requested=True,
        queue_authority_request_dryrun=dryrun.to_dict(),
        store=InMemoryAuthorityRuntimeStore(),
        signer=signer,
        principal_resolver=_PrincipalResolver(),
        snapshot_resolver=_SnapshotResolver(),
        now=NOW,
    )
    assert result.authority_result is not None
    assert result.authority_result.receipt.status == AUTHORITY_ISSUED
    return result, signer


def test_explicit_verification_missing_rejects() -> None:
    runtime, signer = _runtime_result()

    result = invoke_reddog_wre_queue_authority_verification(
        explicit_queue_authority_verification_requested=False,
        queue_authority_runtime_result=runtime.to_dict(),
        signature_verifier=signer,
        principal_key_resolver=_PrincipalKeyResolver(),
        nonce_store=InMemoryNonceStore(),
        snapshot_resolver=_SnapshotResolver(),
        revocation_oracle=_NoRevocation(),
        now=NOW,
        required_valve_state=VALVE_OPEN_WORKTREE_CREATE,
    )

    assert result.decision == QUEUE_AUTHORITY_VERIFICATION_INVOKE_REJECT
    assert QueueAuthorityVerificationInvokeReason.EXPLICIT_INVOKE_MISSING in result.rejection_reasons


def test_runtime_not_accepted_rejects_before_verification() -> None:
    runtime, signer = _runtime_result()
    payload = runtime.to_dict()
    payload["decision"] = "QUEUE_AUTHORITY_RUNTIME_INVOKE_REJECT"

    result = invoke_reddog_wre_queue_authority_verification(
        explicit_queue_authority_verification_requested=True,
        queue_authority_runtime_result=payload,
        signature_verifier=signer,
        principal_key_resolver=_PrincipalKeyResolver(),
        nonce_store=InMemoryNonceStore(),
        snapshot_resolver=_SnapshotResolver(),
        revocation_oracle=_NoRevocation(),
        now=NOW,
        required_valve_state=VALVE_OPEN_WORKTREE_CREATE,
    )

    assert result.decision == QUEUE_AUTHORITY_VERIFICATION_INVOKE_REJECT
    assert QueueAuthorityVerificationInvokeReason.AUTHORITY_RUNTIME_NOT_ACCEPTED in result.rejection_reasons


def test_missing_authority_payload_rejects() -> None:
    runtime, signer = _runtime_result()
    payload = runtime.to_dict()
    payload["authority_result"]["identity"] = None

    result = invoke_reddog_wre_queue_authority_verification(
        explicit_queue_authority_verification_requested=True,
        queue_authority_runtime_result=payload,
        signature_verifier=signer,
        principal_key_resolver=_PrincipalKeyResolver(),
        nonce_store=InMemoryNonceStore(),
        snapshot_resolver=_SnapshotResolver(),
        revocation_oracle=_NoRevocation(),
        now=NOW,
        required_valve_state=VALVE_OPEN_WORKTREE_CREATE,
    )

    assert result.decision == QUEUE_AUTHORITY_VERIFICATION_INVOKE_REJECT
    assert QueueAuthorityVerificationInvokeReason.AUTHORITY_PAYLOAD_MISSING in result.rejection_reasons


def test_verifies_issued_authority_without_execution() -> None:
    runtime, signer = _runtime_result()

    result = invoke_reddog_wre_queue_authority_verification(
        explicit_queue_authority_verification_requested=True,
        queue_authority_runtime_result=runtime.to_dict(),
        signature_verifier=signer,
        principal_key_resolver=_PrincipalKeyResolver(),
        nonce_store=InMemoryNonceStore(),
        snapshot_resolver=_SnapshotResolver(),
        revocation_oracle=_NoRevocation(),
        now=NOW,
        required_valve_state=VALVE_OPEN_WORKTREE_CREATE,
    )

    assert result.decision == QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT
    assert result.rejection_reasons == []
    assert result.verification_result is not None
    assert result.verification_result.accepted is True
    assert result.no_signing_performed is True
    assert result.no_authority_issued is True
    assert result.no_worker_spawn_performed is True
    assert result.no_worktree_created is True
    assert result.no_shell_command_executed is True
    assert result.no_openclaw_enqueue_performed is True
    assert result.no_hermes_dispatch_performed is True
    assert result.no_repo_mutation_performed is True
    assert result.no_holoindex_reindex_performed is True
    assert result.no_pr_created is True
    assert result.no_reward_settlement_performed is True


def test_wrong_valve_state_rejects() -> None:
    runtime, signer = _runtime_result()

    result = invoke_reddog_wre_queue_authority_verification(
        explicit_queue_authority_verification_requested=True,
        queue_authority_runtime_result=runtime.to_dict(),
        signature_verifier=signer,
        principal_key_resolver=_PrincipalKeyResolver(),
        nonce_store=InMemoryNonceStore(),
        snapshot_resolver=_SnapshotResolver(),
        revocation_oracle=_NoRevocation(),
        now=NOW,
        required_valve_state="VALVE_OPEN_LIVE_ENQUEUE",
    )

    assert result.decision == QUEUE_AUTHORITY_VERIFICATION_INVOKE_REJECT
    assert QueueAuthorityVerificationInvokeReason.SIGNATURE_VERIFIER_REJECTED in result.rejection_reasons
    assert ReasonCode.VALVE_STATE in result.rejection_reasons


def test_nonce_replay_rejects_second_verification() -> None:
    runtime, signer = _runtime_result()
    nonce_store = InMemoryNonceStore()
    first = invoke_reddog_wre_queue_authority_verification(
        explicit_queue_authority_verification_requested=True,
        queue_authority_runtime_result=runtime.to_dict(),
        signature_verifier=signer,
        principal_key_resolver=_PrincipalKeyResolver(),
        nonce_store=nonce_store,
        snapshot_resolver=_SnapshotResolver(),
        revocation_oracle=_NoRevocation(),
        now=NOW,
        required_valve_state=VALVE_OPEN_WORKTREE_CREATE,
    )
    second = invoke_reddog_wre_queue_authority_verification(
        explicit_queue_authority_verification_requested=True,
        queue_authority_runtime_result=runtime.to_dict(),
        signature_verifier=signer,
        principal_key_resolver=_PrincipalKeyResolver(),
        nonce_store=nonce_store,
        snapshot_resolver=_SnapshotResolver(),
        revocation_oracle=_NoRevocation(),
        now=NOW,
        required_valve_state=VALVE_OPEN_WORKTREE_CREATE,
    )

    assert first.decision == QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT
    assert second.decision == QUEUE_AUTHORITY_VERIFICATION_INVOKE_REJECT
    assert ReasonCode.NONCE_REPLAY in second.rejection_reasons


def test_module_has_no_shell_network_signing_issue_worktree_or_holoindex_imports() -> None:
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
