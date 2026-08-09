"""Tests for REDDOG_SIGNER_AND_DELEGATED_AUTHORITY_RUNTIME_PHASE1."""

from __future__ import annotations

import ast
import hashlib
import hmac
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src import (
    reddog_progressive_execution_stage_policy as stage_policy,
)
from modules.communication.moltbot_bridge.src import reddog_signer_delegated_authority_runtime as r
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    AUTHORITY_ISSUED,
    AtomicJsonAuthorityRuntimeStore,
    DelegatedAuthorityRuntimeRequest,
    InMemoryAuthorityRuntimeStore,
    PrincipalAuthorityRecord,
    RuntimeRejectCode,
    SigningResponse,
    issue_delegated_authority_runtime,
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    InMemoryNonceStore,
    PermissionSnapshot,
    PrincipalKeyResolver,
    ReasonCode,
    RevocationOracle,
    SignatureVerifier,
    verify_delegated_work_authority,
)
from modules.communication.moltbot_bridge.src.reddog_queue_authority_admission import (
    _admit_current_queue_authority,
)
from modules.communication.moltbot_bridge.src.reddog_work_authority_digest import (
    canonical_work_authority_digest,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_binding import (
    canonical_full_work_order_digest,
)
from modules.communication.moltbot_bridge.src.reddog_signed_authority_worker_dispatch_dryrun import (
    plan_reddog_signed_authority_worker_dispatch_dry_run,
)
from modules.communication.moltbot_bridge.src.reddog_worker_dispatch_authority_binding import (
    recorded_authority_verification_binding,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authority_runtime_invoke import (
    QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authority_verification_invoke import (
    QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.tests.reddog_signed_worker_dispatch_test_support import (
    bounded_allocation,
    signed_audit_stage_binding,
    signed_stage_binding,
)

_NOW = 1000
_REPO = "FOUNDUPS/Foundups-Agent"
_FID = "paccess_001"
_MEMEX_DIGEST = "sha256:" + ("d" * 64)
_VALVE = "VALVE_OPEN_WORKTREE_CREATE"

class _MockSigner(SignatureVerifier):
    """Test-only signer/verifier. Production module never signs or imports crypto."""

    def __init__(self) -> None:
        self._secrets = {
            "pub:principal": b"test-principal-secret",
            "pub:reddog": b"test-reddog-secret",
        }
        self.requests = []

    def sign(self, request):
        self.requests.append(request)
        secret = self._secrets.get(request.signer_public_key)
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
        secret = self._secrets.get(public_key)
        if secret is None or not isinstance(signature, str):
            return False
        expected = hmac.new(secret, signing_input.encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

class _BoundarylessSigner(_MockSigner):
    def sign(self, request):
        response = super().sign(request)
        return SigningResponse(
            accepted=response.accepted,
            signature=response.signature,
            signer_public_key=response.signer_public_key,
            key_fingerprint=response.key_fingerprint,
            key_epoch=response.key_epoch,
            audit_mac=response.audit_mac,
            boundary_attested=False,
            requester_identity_attested=True,
            signer_loads_no_untrusted_code=True,
            no_secret_material_returned=True,
        )


class _PrincipalResolver(PrincipalKeyResolver):
    def __init__(self, record: PrincipalAuthorityRecord) -> None:
        self.record = record

    def resolve(self, principal_id: str, principal_provider: str):
        if principal_id == self.record.principal_id and principal_provider == self.record.principal_provider:
            return self.record
        return None


class _PrincipalKeyResolver(PrincipalKeyResolver):
    def resolve(self, principal_id: str, principal_provider: str):
        if principal_id == "github:mjtrout" and principal_provider == "github":
            return "pub:principal"
        return None


class _SnapshotResolver:
    def __init__(self, mapping) -> None:
        self.mapping = mapping

    def resolve(self, digest: str):
        return self.mapping.get(digest)


class _NoRevocation(RevocationOracle):
    def is_revoked(self, *, reddog_id: str, fingerprint: str, principal_id: str, key_epoch: str) -> bool:
        return False


def _principal() -> PrincipalAuthorityRecord:
    return PrincipalAuthorityRecord(
        principal_id="github:mjtrout",
        principal_provider="github",
        principal_public_key="pub:principal",
        repo_scope=(_REPO,),
        foundup_scope=(_FID,),
        verified_subject_digest="sha256:verified-subject",
        reward_account="reward:012",
        owner_dae="dae:012",
        principal_wallet=None,
    )


def _request(**overrides) -> DelegatedAuthorityRuntimeRequest:
    payload = {
        "work_order_id": "wo-paccess-001",
        "work_order_digest": "sha256:" + ("a" * 64),
        "base_ref": "main",
        "principal_id": "github:mjtrout",
        "principal_provider": "github",
        "principal_public_key": "pub:principal",
        "reddog_id": "reddog:abc123",
        "reddog_public_key": "pub:reddog",
        "repo_full_name": _REPO,
        "foundup_id": _FID,
        "allowed_paths": (f"modules/foundups/{_FID}/src/worker.py",),
        "denied_paths": (),
        "requested_operation": "edit_foundup_module",
        "permission_snapshot_digest": "sha256:snap-1",
        "wsp15_allocation_receipt_id": "sha256:wsp15-allocation",
        "wsp15_allocation_digest": "sha256:wsp15-allocation-digest",
        "wsp15_priority": "P0",
        "wsp15_mps_total": 20,
        "wsp15_reasoning_tier": "ULTRA",
        **signed_stage_binding(
            requested_operation="edit_foundup_module",
            changed_paths=(f"modules/foundups/{_FID}/src/worker.py",),
        ),
        "model_selection_receipt_id": "sha256:model-selection",
        "model_selection_digest": "sha256:model-selection-digest",
        "model_runtime_binding_receipt_id": "reddog_model_runtime_binding:abc123",
        "model_runtime_binding_digest": "sha256:model-runtime-binding",
        "model_runtime_binding_verification_receipt_id": "model_runtime_binding_verification:abc123",
        "model_runtime_binding_verification_digest": "sha256:model-runtime-binding-verification",
        "memex_supply_receipt_id": "sha256:memex-supply",
        "memex_supply_digest": _MEMEX_DIGEST,
        "identity_nonce": "identity-nonce-0001",
        "work_authority_nonce": "workauth-nonce-0001",
        "issued_at": _NOW - 5,
        "identity_expires_at": _NOW + 3600,
        "work_authority_expires_at": _NOW + 300,
        "valve_state_required": _VALVE,
        "key_epoch": "epoch-1",
        "consensus_receipt_digest": "sha256:consensus",
        "sovereign_authorization_digest": "sha256:012-dao-token",
    }
    payload.update(overrides)
    if "queue_consumer_receipt" not in overrides:
        stage = payload["progressive_policy_stage_receipt"]
        payload["queue_consumer_receipt"] = {
            "queue_item_id": "queue-1",
            "slice_id": stage["selected_slice"],
            "claim_id": "claim-1",
            "worker_id": "reddog-0102",
            "wsp15_allocation_receipt": dict(
                payload["wsp15_allocation_receipt"]
            ),
            "wsp15_allocation_receipt_id": payload[
                "wsp15_allocation_receipt_id"
            ],
            "wsp15_allocation_digest": payload["wsp15_allocation_digest"],
            "progressive_policy_stage_receipt_id": payload[
                "progressive_policy_stage_receipt_id"
            ],
            "progressive_policy_stage_digest": payload[
                "progressive_policy_stage_digest"
            ],
            "progressive_policy_stage_receipt": dict(stage),
            "model_selection_receipt_id": payload[
                "model_selection_receipt_id"
            ],
            "model_selection_digest": payload["model_selection_digest"],
            "model_runtime_binding_receipt_id": payload[
                "model_runtime_binding_receipt_id"
            ],
            "model_runtime_binding_digest": payload[
                "model_runtime_binding_digest"
            ],
            "model_runtime_binding_verification_receipt_id": payload[
                "model_runtime_binding_verification_receipt_id"
            ],
            "model_runtime_binding_verification_digest": payload[
                "model_runtime_binding_verification_digest"
            ],
            "memex_supply_receipt_id": payload["memex_supply_receipt_id"],
            "memex_supply_digest": payload["memex_supply_digest"],
        }
    if "queue_consumer_receipt_digest" not in overrides:
        payload["queue_consumer_receipt_digest"] = (
            canonical_full_work_order_digest(payload["queue_consumer_receipt"])
        )
    return DelegatedAuthorityRuntimeRequest(**payload)


def _snapshot(can_write=True, digest="sha256:snap-1", expires_at=_NOW + 600):
    return PermissionSnapshot(
        evidence_digest=digest,
        expires_at=expires_at,
        can_write=can_write,
        can_admin=False,
        repo_full_name=_REPO,
    )


def _issue(**overrides):
    if not any(key.startswith("progressive_policy_stage_") for key in overrides):
        operation = str(overrides.get("requested_operation", "edit_foundup_module"))
        paths = tuple(overrides.get("allowed_paths", (f"modules/foundups/{_FID}/src/worker.py",)))
        overrides = {**signed_stage_binding(requested_operation=operation, changed_paths=paths), **overrides}
    request = _request(**overrides)
    signer = _MockSigner()
    store = InMemoryAuthorityRuntimeStore()
    snapshot_resolver = _SnapshotResolver({request.permission_snapshot_digest: _snapshot()})
    result = _issue_authority(
        request=request,
        store=store,
        signer=signer,
        principal_resolver=_PrincipalResolver(_principal()),
        snapshot_resolver=snapshot_resolver,
        now=_NOW,
    )
    return result, signer, store, snapshot_resolver


def test_runtime_issues_records_accepted_by_existing_verifier() -> None:
    result, signer, _, snapshot_resolver = _issue()

    assert result.accepted is True
    assert result.receipt.status == AUTHORITY_ISSUED
    assert result.identity and result.work_authority
    assert result.receipt.signer_audit_macs and len(result.receipt.signer_audit_macs) == 2
    assert result.receipt.no_execution_performed is True
    assert result.receipt.no_openclaw_enqueue_performed is True
    assert signer.requests[0].signer_role == "principal"
    assert signer.requests[1].signer_role == "reddog"
    assert result.work_authority["wsp15_allocation_receipt_id"] == (
        result.work_authority["wsp15_allocation_receipt"]["receipt_id"]
    )
    assert result.work_authority["work_order_digest"] == "sha256:" + ("a" * 64)
    assert result.work_authority["base_ref"] == "main"
    assert result.work_authority["wsp15_allocation_digest"] == (
        result.work_authority["progressive_policy_stage_receipt"][
            "wsp15_allocation_digest"
        ]
    )
    assert result.work_authority["model_runtime_binding_receipt_id"] == (
        "reddog_model_runtime_binding:abc123"
    )
    assert result.work_authority["model_runtime_binding_digest"] == (
        "sha256:model-runtime-binding"
    )
    assert result.work_authority["model_selection_receipt_id"] == (
        "sha256:model-selection"
    )
    assert result.work_authority["model_selection_digest"] == (
        "sha256:model-selection-digest"
    )
    assert result.work_authority["memex_supply_receipt_id"] == (
        "sha256:memex-supply"
    )
    assert result.work_authority["memex_supply_digest"] == _MEMEX_DIGEST

    verified = verify_delegated_work_authority(
        work_authority=result.work_authority,
        identity=result.identity,
        signature_verifier=signer,
        principal_key_resolver=_PrincipalKeyResolver(),
        nonce_store=InMemoryNonceStore(),
        snapshot_resolver=snapshot_resolver,
        revocation_oracle=_NoRevocation(),
        now=_NOW,
        required_valve_state=_VALVE,
    )
    assert verified.accepted is True, verified.reason_codes


def _authoritative_queue_item(request):
    receipt = request.queue_consumer_receipt
    return {
        "queue_item_id": receipt["queue_item_id"],
        "slice_id": receipt["slice_id"],
        "claim_id": receipt["claim_id"],
        "worker_id": receipt["worker_id"],
        "status": "QUEUED",
        "wsp15_allocation_receipt": dict(request.wsp15_allocation_receipt),
        "progressive_policy_stage_receipt_id": (
            request.progressive_policy_stage_receipt_id
        ),
        "progressive_policy_stage_digest": (
            request.progressive_policy_stage_digest
        ),
        "progressive_policy_stage_receipt": dict(
            request.progressive_policy_stage_receipt
        ),
        "independent_verifier_required": request.progressive_policy_stage_receipt[
            "independent_verifier_required"
        ],
        "no_execution_performed": True,
        **{
            field: receipt.get(field)
            for field in (
                "model_selection_receipt_id",
                "model_selection_digest",
                "model_runtime_binding_receipt_id",
                "model_runtime_binding_digest",
                "model_runtime_binding_verification_receipt_id",
                "model_runtime_binding_verification_digest",
                "memex_supply_receipt_id",
                "memex_supply_digest",
            )
        },
    }


def _issue_authority(*, request, **kwargs):
    admission = _admit_current_queue_authority(
        request=request,
        authoritative_queue_item=_authoritative_queue_item(request),
    )
    return issue_delegated_authority_runtime(
        request=request,
        queue_authority_admission=admission,
        **kwargs,
    )


def test_changed_signed_wsp15_allocation_digest_rejects() -> None:
    result, signer, _, snapshot_resolver = _issue()

    assert result.accepted is True
    assert result.identity and result.work_authority
    result.work_authority["wsp15_allocation_digest"] = "sha256:changed-after-signing"

    verified = verify_delegated_work_authority(
        work_authority=result.work_authority,
        identity=result.identity,
        signature_verifier=signer,
        principal_key_resolver=_PrincipalKeyResolver(),
        nonce_store=InMemoryNonceStore(),
        snapshot_resolver=snapshot_resolver,
        revocation_oracle=_NoRevocation(),
        now=_NOW,
        required_valve_state=_VALVE,
    )

    assert verified.accepted is False
    assert ReasonCode.MALFORMED_PAYLOAD in verified.reason_codes


def test_changed_signed_work_order_lineage_rejects() -> None:
    for field, value in (
        ("base_ref", "release"),
        ("work_order_digest", "sha256:" + ("f" * 64)),
        ("queue_consumer_receipt_digest", "sha256:" + ("e" * 64)),
    ):
        result, signer, _, snapshot_resolver = _issue()
        assert result.identity and result.work_authority
        result.work_authority[field] = value

        verified = verify_delegated_work_authority(
            work_authority=result.work_authority,
            identity=result.identity,
            signature_verifier=signer,
            principal_key_resolver=_PrincipalKeyResolver(),
            nonce_store=InMemoryNonceStore(),
            snapshot_resolver=snapshot_resolver,
            revocation_oracle=_NoRevocation(),
            now=_NOW,
            required_valve_state=_VALVE,
        )

        assert verified.accepted is False
        assert ReasonCode.WORKAUTH_SIGNATURE_INVALID in verified.reason_codes


def test_malformed_queue_consumer_receipt_digest_rejects_before_signing() -> None:
    result, _, _, _ = _issue(
        queue_consumer_receipt_digest="sha256:not-a-canonical-digest"
    )

    assert result.accepted is False
    assert RuntimeRejectCode.MALFORMED_REQUEST in result.receipt.rejection_reasons


def test_changed_signed_runtime_binding_digest_rejects() -> None:
    result, signer, _, snapshot_resolver = _issue()

    assert result.accepted is True
    assert result.identity and result.work_authority
    result.work_authority["model_runtime_binding_digest"] = "sha256:changed-after-signing"

    verified = verify_delegated_work_authority(
        work_authority=result.work_authority,
        identity=result.identity,
        signature_verifier=signer,
        principal_key_resolver=_PrincipalKeyResolver(),
        nonce_store=InMemoryNonceStore(),
        snapshot_resolver=snapshot_resolver,
        revocation_oracle=_NoRevocation(),
        now=_NOW,
        required_valve_state=_VALVE,
    )

    assert verified.accepted is False
    assert ReasonCode.WORKAUTH_SIGNATURE_INVALID in verified.reason_codes


def test_changed_signed_architect_publication_binding_rejects() -> None:
    result, signer, store, snapshot_resolver = _issue(
        architect_fix_publication_receipt_id="sha256:" + "4" * 64,
        architect_fix_publication_binding_digest="sha256:" + "5" * 64,
    )

    assert result.accepted is True
    assert result.identity and result.work_authority
    issued = store.load()["issued_authorities"][result.work_authority["work_order_id"]]
    assert issued["architect_fix_publication_receipt_id"] == "sha256:" + "4" * 64
    result.work_authority[
        "architect_fix_publication_binding_digest"
    ] = "sha256:" + "6" * 64

    verified = verify_delegated_work_authority(
        work_authority=result.work_authority,
        identity=result.identity,
        signature_verifier=signer,
        principal_key_resolver=_PrincipalKeyResolver(),
        nonce_store=InMemoryNonceStore(),
        snapshot_resolver=snapshot_resolver,
        revocation_oracle=_NoRevocation(),
        now=_NOW,
        required_valve_state=_VALVE,
    )

    assert verified.accepted is False
    assert ReasonCode.WORKAUTH_SIGNATURE_INVALID in verified.reason_codes


def test_malformed_runtime_binding_field_rejects_before_signing() -> None:
    result, _, _, _ = _issue(model_runtime_binding_receipt_id="not-a-runtime-binding")

    assert result.accepted is False
    assert RuntimeRejectCode.MALFORMED_REQUEST in result.receipt.rejection_reasons


def test_malformed_memex_binding_rejects_before_signing() -> None:
    result, signer, _, _ = _issue(memex_supply_digest="sha256:not-canonical")

    assert result.accepted is False
    assert RuntimeRejectCode.MALFORMED_REQUEST in result.receipt.rejection_reasons
    assert signer.requests == []


def test_default_signer_fails_closed() -> None:
    request = _request()
    result = _issue_authority(
        request=request,
        store=InMemoryAuthorityRuntimeStore(),
        principal_resolver=_PrincipalResolver(_principal()),
        snapshot_resolver=_SnapshotResolver({request.permission_snapshot_digest: _snapshot()}),
        now=_NOW,
    )
    assert result.accepted is False
    assert RuntimeRejectCode.SIGNER_NOT_CONFIGURED in result.receipt.rejection_reasons


def test_unknown_principal_fails_closed() -> None:
    request = _request(principal_id="github:attacker")
    result = _issue_authority(
        request=request,
        store=InMemoryAuthorityRuntimeStore(),
        signer=_MockSigner(),
        principal_resolver=_PrincipalResolver(_principal()),
        snapshot_resolver=_SnapshotResolver({request.permission_snapshot_digest: _snapshot()}),
        now=_NOW,
    )
    assert result.accepted is False
    assert RuntimeRejectCode.PRINCIPAL_NOT_VERIFIED in result.receipt.rejection_reasons


def test_high_authority_requires_consensus_and_sovereign_authorization() -> None:
    result, _, _, _ = _issue(consensus_receipt_digest=None)
    assert result.accepted is False
    assert RuntimeRejectCode.HIGH_AUTHORITY_NEEDS_COSIGN in result.receipt.rejection_reasons


def test_worktree_valve_intent_is_high_authority_even_for_low_operation() -> None:
    result, _, _, _ = _issue(
        consensus_receipt_digest=None,
        sovereign_authorization_digest=None,
    )
    assert result.accepted is False
    assert RuntimeRejectCode.HIGH_AUTHORITY_NEEDS_COSIGN in result.receipt.rejection_reasons


def test_live_enqueue_valve_intent_is_high_authority_even_for_low_operation() -> None:
    result, _, _, _ = _issue(
        valve_state_required="VALVE_OPEN_LIVE_ENQUEUE",
        consensus_receipt_digest=None,
        sovereign_authorization_digest=None,
    )
    assert result.accepted is False
    assert RuntimeRejectCode.HIGH_AUTHORITY_NEEDS_COSIGN in result.receipt.rejection_reasons


def test_high_authority_rejects_consensus_without_sovereign_authorization() -> None:
    result, _, _, _ = _issue(sovereign_authorization_digest=None)
    assert result.accepted is False
    assert RuntimeRejectCode.HIGH_AUTHORITY_NEEDS_COSIGN in result.receipt.rejection_reasons


def test_low_authority_can_issue_without_cosign() -> None:
    result, _, _, _ = _issue(
        valve_state_required="VALVE_OPEN_DRYRUN_ONLY",
        consensus_receipt_digest=None,
        sovereign_authorization_digest=None,
    )
    assert result.accepted is True, result.receipt.rejection_reasons
    assert result.work_authority["authority_tier"] == "LOW"


def test_stale_permission_snapshot_rejects() -> None:
    request = _request()
    result = _issue_authority(
        request=request,
        store=InMemoryAuthorityRuntimeStore(),
        signer=_MockSigner(),
        principal_resolver=_PrincipalResolver(_principal()),
        snapshot_resolver=_SnapshotResolver({request.permission_snapshot_digest: _snapshot(expires_at=_NOW - 120)}),
        now=_NOW,
    )
    assert result.accepted is False
    assert RuntimeRejectCode.SNAPSHOT_STALE_OR_MISSING in result.receipt.rejection_reasons


def test_permission_snapshot_must_grant_operation() -> None:
    request = _request()
    result = _issue_authority(
        request=request,
        store=InMemoryAuthorityRuntimeStore(),
        signer=_MockSigner(),
        principal_resolver=_PrincipalResolver(_principal()),
        snapshot_resolver=_SnapshotResolver({request.permission_snapshot_digest: _snapshot(can_write=False)}),
        now=_NOW,
    )
    assert result.accepted is False
    assert RuntimeRejectCode.SNAPSHOT_INSUFFICIENT in result.receipt.rejection_reasons


def test_scope_and_path_validation_fail_closed() -> None:
    binding = signed_stage_binding()
    result, _, _, _ = _issue(
        **binding, allowed_paths=(".github/workflows/deploy.yml",)
    )
    assert result.accepted is False
    assert RuntimeRejectCode.MALFORMED_REQUEST in result.receipt.rejection_reasons

    result, _, _, _ = _issue(foundup_id="other_002")
    assert result.accepted is False
    assert RuntimeRejectCode.SCOPE_EXCEEDED in result.receipt.rejection_reasons


def test_nonce_replay_rejects_before_second_issue() -> None:
    request = _request()
    store = InMemoryAuthorityRuntimeStore()
    kwargs = dict(
        store=store,
        signer=_MockSigner(),
        principal_resolver=_PrincipalResolver(_principal()),
        snapshot_resolver=_SnapshotResolver({request.permission_snapshot_digest: _snapshot()}),
        now=_NOW,
    )
    first = _issue_authority(request=request, **kwargs)
    second = _issue_authority(request=request, **kwargs)
    assert first.accepted is True
    assert second.accepted is False
    assert RuntimeRejectCode.NONCE_REPLAY in second.receipt.rejection_reasons


def test_revoked_reddog_or_epoch_rejects() -> None:
    fingerprint = public_key_fingerprint("pub:reddog")
    store = InMemoryAuthorityRuntimeStore(
        {
            "revocations": {
                "principal_ids": [],
                "reddog_ids": [],
                "reddog_fingerprints": [fingerprint],
                "key_epochs": [],
            }
        }
    )
    request = _request()
    result = _issue_authority(
        request=request,
        store=store,
        signer=_MockSigner(),
        principal_resolver=_PrincipalResolver(_principal()),
        snapshot_resolver=_SnapshotResolver({request.permission_snapshot_digest: _snapshot()}),
        now=_NOW,
    )
    assert result.accepted is False
    assert RuntimeRejectCode.REVOKED in result.receipt.rejection_reasons


def test_signer_boundary_attestation_is_required() -> None:
    request = _request()
    result = _issue_authority(
        request=request,
        store=InMemoryAuthorityRuntimeStore(),
        signer=_BoundarylessSigner(),
        principal_resolver=_PrincipalResolver(_principal()),
        snapshot_resolver=_SnapshotResolver({request.permission_snapshot_digest: _snapshot()}),
        now=_NOW,
    )
    assert result.accepted is False
    assert RuntimeRejectCode.SIGNER_BOUNDARY_NOT_ATTESTED in result.receipt.rejection_reasons


def test_json_store_commits_authority_receipt(tmp_path) -> None:
    request = _request()
    repo = tmp_path / "repo"
    repo.mkdir()
    runtime = tmp_path / "runtime"
    path = runtime / "authority-state.json"
    result = _issue_authority(
        request=request,
        store=AtomicJsonAuthorityRuntimeStore(
            path,
            allowed_root=runtime,
            repo_root=repo,
        ),
        signer=_MockSigner(),
        principal_resolver=_PrincipalResolver(_principal()),
        snapshot_resolver=_SnapshotResolver({request.permission_snapshot_digest: _snapshot()}),
        now=_NOW,
    )
    assert result.accepted is True
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert request.work_order_id in content
    assert result.receipt.store_revision


def test_json_store_compare_and_swap_is_serialized_across_store_instances(
    tmp_path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    runtime = tmp_path / "runtime"
    path = runtime / "authority-state.json"
    barrier = threading.Barrier(2)

    def commit(index: int) -> str:
        barrier.wait(timeout=5)
        try:
            AtomicJsonAuthorityRuntimeStore(
                path,
                allowed_root=runtime,
                repo_root=repo,
            ).commit(
                {"writer": index}, expected_revision=None
            )
        except RuntimeError as exc:
            return str(exc)
        return "committed"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(commit, (1, 2)))

    assert sorted(outcomes) == ["committed", "revision_conflict"]
    assert AtomicJsonAuthorityRuntimeStore(
        path,
        allowed_root=runtime,
        repo_root=repo,
    ).load()["writer"] in {1, 2}


def test_json_store_fsyncs_parent_directory_after_atomic_replace(
    tmp_path, monkeypatch
) -> None:
    from modules.communication.moltbot_bridge.src import (
        reddog_authority_runtime_store as store_module,
    )

    observed = []
    monkeypatch.setattr(
        store_module,
        "_fsync_parent_directory",
        lambda path: observed.append(path),
    )
    repo = tmp_path / "repo"
    repo.mkdir()
    runtime = tmp_path / "runtime"
    target = runtime / "authority-state.json"

    AtomicJsonAuthorityRuntimeStore(
        target,
        allowed_root=runtime,
        repo_root=repo,
    ).commit(
        {"writer": 1}, expected_revision=None
    )

    assert observed == [runtime]


def test_json_store_parent_swap_cannot_redirect_atomic_replace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    runtime = tmp_path / "runtime"
    outside = tmp_path / "outside"
    outside.mkdir()
    target = runtime / "authority-state.json"
    displaced = tmp_path / "runtime-displaced"
    swap_attempted = False
    swap_succeeded = False

    def attempt_swap() -> None:
        nonlocal swap_attempted, swap_succeeded
        if not swap_attempted:
            swap_attempted = True
            try:
                runtime.rename(displaced)
                runtime.symlink_to(outside, target_is_directory=True)
                swap_succeeded = True
            except OSError:
                pass

    if os.name == "nt":
        from modules.communication.moltbot_bridge.src import (
            reddog_authority_runtime_store_windows as windows_store,
        )

        real_windows_rename = windows_store._rename_handle

        def adversarial_windows_rename(*args, **kwargs):
            attempt_swap()
            return real_windows_rename(*args, **kwargs)

        monkeypatch.setattr(
            windows_store,
            "_rename_handle",
            adversarial_windows_rename,
        )
    else:
        from modules.communication.moltbot_bridge.src import (
            reddog_authority_runtime_store_posix as posix_store,
        )

        real_replace = posix_store._replace_entry

        def adversarial_replace(*args, **kwargs):
            attempt_swap()
            return real_replace(*args, **kwargs)

        monkeypatch.setattr(posix_store, "_replace_entry", adversarial_replace)
    store = AtomicJsonAuthorityRuntimeStore(
        target,
        allowed_root=runtime,
        repo_root=repo,
    )
    rejection: ValueError | None = None
    try:
        try:
            store.commit({"writer": 1}, expected_revision=None)
        except ValueError as exc:
            rejection = exc
    finally:
        if swap_succeeded:
            runtime.unlink()
            displaced.rename(runtime)

    assert swap_attempted is True
    if swap_succeeded:
        assert rejection is not None
        assert "parent_changed" in str(rejection)
        assert not target.exists()
    else:
        assert rejection is None
        assert json.loads(target.read_text(encoding="utf-8"))["writer"] == 1
    assert not (outside / target.name).exists()


def test_json_store_load_rejects_symlink_state_file(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    target = runtime / "target.json"
    target.write_text("{}", encoding="utf-8")
    link = runtime / "authority-state.json"
    try:
        link.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    with pytest.raises(ValueError, match="symlink_forbidden|path_link_rejected"):
        AtomicJsonAuthorityRuntimeStore(
            link,
            allowed_root=runtime,
            repo_root=repo,
        ).load()


def test_json_store_load_rejects_linked_parent_state_file(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    target = runtime / "target"
    target.mkdir()
    (target / "authority.json").write_text("{}", encoding="utf-8")
    linked = runtime / "linked"
    try:
        linked.symlink_to(target, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    with pytest.raises((OSError, ValueError)):
        AtomicJsonAuthorityRuntimeStore(
            linked / "authority.json",
            allowed_root=runtime,
            repo_root=repo,
        ).load()


def test_json_store_load_rejects_hard_linked_state_file(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    linked = runtime / "authority.json"
    try:
        os.link(outside, linked)
    except OSError as exc:
        pytest.skip(f"hard-link creation unavailable: {exc}")

    with pytest.raises(ValueError, match="target_link_count"):
        AtomicJsonAuthorityRuntimeStore(
            linked,
            allowed_root=runtime,
            repo_root=repo,
        ).load()


def test_json_store_windows_rejects_hard_linked_temporary_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if os.name != "nt":
        pytest.skip("Windows handle replacement only")
    from modules.communication.moltbot_bridge.src import (
        reddog_authority_runtime_store_windows as windows_store,
    )

    repo = tmp_path / "repo"
    repo.mkdir()
    runtime = tmp_path / "runtime"
    target = runtime / "authority.json"
    captured = tmp_path / "captured.json"
    real_write = windows_store._write_handle

    def write_and_link(handle: int, payload: bytes) -> None:
        real_write(handle, payload)
        os.link(windows_store._handle_path(handle), captured)

    monkeypatch.setattr(windows_store, "_write_handle", write_and_link)

    with pytest.raises(ValueError, match="temp_link_count"):
        AtomicJsonAuthorityRuntimeStore(
            target,
            allowed_root=runtime,
            repo_root=repo,
        ).commit({"writer": 1}, expected_revision=None)

    assert not target.exists()
    assert captured.exists()
    assert captured.read_bytes() == b"\x00" * captured.stat().st_size


def test_json_store_atomic_failure_preserves_previous_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    runtime = tmp_path / "runtime"
    target = runtime / "authority.json"
    store = AtomicJsonAuthorityRuntimeStore(
        target,
        allowed_root=runtime,
        repo_root=repo,
    )
    revision = store.commit({"writer": 1}, expected_revision=None)

    def reject_replace(*args, **kwargs) -> None:
        raise OSError("injected")

    if os.name == "nt":
        from modules.communication.moltbot_bridge.src import (
            reddog_authority_runtime_store_windows as windows_store,
        )

        monkeypatch.setattr(
            windows_store,
            "_rename_handle",
            reject_replace,
        )
    else:
        from modules.communication.moltbot_bridge.src import (
            reddog_authority_runtime_store_posix as posix_store,
        )

        monkeypatch.setattr(
            posix_store,
            "_write_descriptor",
            reject_replace,
        )

    with pytest.raises(OSError, match="injected"):
        store.commit({"writer": 2}, expected_revision=revision)

    assert store.load()["writer"] == 1


def test_json_store_rejects_intervening_revision_before_replace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    runtime = tmp_path / "runtime"
    target = runtime / "authority.json"
    store = AtomicJsonAuthorityRuntimeStore(
        target,
        allowed_root=runtime,
        repo_root=repo,
    )
    revision = store.commit({"writer": 1}, expected_revision=None)

    if os.name == "nt":
        from modules.communication.moltbot_bridge.src import (
            reddog_authority_runtime_store_windows as platform_store,
        )
    else:
        from modules.communication.moltbot_bridge.src import (
            reddog_authority_runtime_store_posix as platform_store,
        )

    original = platform_store._require_target_revision if os.name == "nt" else (
        platform_store._require_target_witness
    )
    calls = 0

    def mutate_before_second_check(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            external = {"writer": "external"}
            external["revision"] = hashlib.sha256(
                json.dumps(
                    external,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=True,
                ).encode("utf-8")
            ).hexdigest()
            target.write_text(
                json.dumps(external, sort_keys=True),
                encoding="utf-8",
            )
        return original(*args, **kwargs)

    monkeypatch.setattr(
        platform_store,
        "_require_target_revision" if os.name == "nt" else "_require_target_witness",
        mutate_before_second_check,
    )

    with pytest.raises(RuntimeError, match="revision_conflict"):
        store.commit({"writer": 2}, expected_revision=revision)

    assert store.load()["writer"] == "external"


def test_json_store_rejects_target_alias_created_at_replace_seam(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    runtime = tmp_path / "runtime"
    target = runtime / "authority.json"
    captured = tmp_path / "captured-authority.json"
    store = AtomicJsonAuthorityRuntimeStore(
        target,
        allowed_root=runtime,
        repo_root=repo,
    )
    revision = store.commit({"writer": 1}, expected_revision=None)

    if os.name == "nt":
        from modules.communication.moltbot_bridge.src import (
            reddog_authority_runtime_store_windows as platform_store,
        )
    else:
        from modules.communication.moltbot_bridge.src import (
            reddog_authority_runtime_store_posix as platform_store,
        )
    original = platform_store._require_backup_identity
    injected = False

    def alias_before_identity_check(*args, **kwargs):
        nonlocal injected
        if not injected:
            injected = True
            os.link(target, captured)
        return original(*args, **kwargs)

    monkeypatch.setattr(
        platform_store,
        "_require_backup_identity",
        alias_before_identity_check,
    )

    with pytest.raises((RuntimeError, ValueError)):
        store.commit({"writer": 2}, expected_revision=revision)

    assert injected is True
    assert json.loads(captured.read_text(encoding="utf-8"))["writer"] == 1
    captured.unlink()
    assert store.load()["writer"] == 1


def test_json_store_recovers_interrupted_backup_and_temp(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    runtime = tmp_path / "runtime"
    target = runtime / "authority.json"
    store = AtomicJsonAuthorityRuntimeStore(
        target,
        allowed_root=runtime,
        repo_root=repo,
    )
    revision = store.commit({"writer": 1}, expected_revision=None)
    backup = runtime / f".{target.name}.{'a' * 32}.bak"
    temp = runtime / f".{target.name}.{'b' * 32}.tmp"
    os.link(target, backup)
    temp.write_text("interrupted", encoding="utf-8")

    next_revision = store.commit({"writer": 2}, expected_revision=revision)

    assert store.load() == {"writer": 2, "revision": next_revision}
    assert not backup.exists()
    assert not temp.exists()


def test_json_store_recovers_only_revision_valid_lone_backup(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    runtime = tmp_path / "runtime"
    target = runtime / "authority.json"
    store = AtomicJsonAuthorityRuntimeStore(
        target,
        allowed_root=runtime,
        repo_root=repo,
    )
    revision = store.commit({"writer": 1}, expected_revision=None)
    backup = runtime / f".{target.name}.{'c' * 32}.bak"
    os.replace(target, backup)
    if os.name != "nt":
        os.chmod(backup, 0)

    with pytest.raises(
        ValueError,
        match="recovery_revision_required",
    ):
        store.load()

    assert backup.exists()
    next_revision = store.commit({"writer": 2}, expected_revision=revision)

    assert store.load() == {"writer": 2, "revision": next_revision}
    assert target.exists()
    assert not backup.exists()


def test_json_store_rejects_self_consistent_but_unauthorized_lone_backup(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    target = runtime / "authority.json"
    backup = runtime / f".{target.name}.{'d' * 32}.bak"
    forged = {"writer": "forged"}
    forged["revision"] = hashlib.sha256(
        json.dumps(
            forged,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()
    backup.write_text(
        json.dumps(forged),
        encoding="utf-8",
    )
    store = AtomicJsonAuthorityRuntimeStore(
        target,
        allowed_root=runtime,
        repo_root=repo,
    )

    with pytest.raises(RuntimeError, match="revision_conflict"):
        store.commit({"writer": 2}, expected_revision="e" * 64)

    assert not target.exists()
    assert backup.exists()


def test_json_store_rejects_linked_lone_recovery_backup(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    runtime = tmp_path / "runtime"
    target = runtime / "authority.json"
    store = AtomicJsonAuthorityRuntimeStore(
        target,
        allowed_root=runtime,
        repo_root=repo,
    )
    revision = store.commit({"writer": 1}, expected_revision=None)
    backup = runtime / f".{target.name}.{'f' * 32}.bak"
    os.replace(target, backup)
    alias = tmp_path / "backup-alias.json"
    os.link(backup, alias)

    with pytest.raises(
        (ValueError, RuntimeError),
        match="(link_count|snapshot_invalid|revision_conflict)",
    ):
        store.commit({"writer": 2}, expected_revision=revision)

    assert not target.exists()
    assert backup.exists()
    assert alias.exists()


def test_json_store_rejects_oversized_lone_recovery_backup_before_json_read(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    target = runtime / "authority.json"
    backup = runtime / f".{target.name}.{'1' * 32}.bak"
    with backup.open("wb") as handle:
        handle.truncate((8 * 1024 * 1024) + 1)
    store = AtomicJsonAuthorityRuntimeStore(
        target,
        allowed_root=runtime,
        repo_root=repo,
    )

    with pytest.raises(
        (ValueError, RuntimeError),
        match="(snapshot_invalid|target_too_large|revision_conflict)",
    ):
        store.commit({"writer": 2}, expected_revision="2" * 64)

    assert not target.exists()
    assert backup.exists()


def test_json_store_nonce_revision_remains_recoverable_with_exact_commitment(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    runtime = tmp_path / "runtime"
    target = runtime / "authority.json"
    store = AtomicJsonAuthorityRuntimeStore(
        target,
        allowed_root=runtime,
        repo_root=repo,
    )
    store.commit({"writer": 1}, expected_revision=None)
    assert store.consume_verified_work_authority_nonce("nonce-001") is True
    committed = store.load()
    nonce_revision = committed["revision"]
    backup = runtime / f".{target.name}.{'e' * 32}.bak"
    os.replace(target, backup)
    if os.name != "nt":
        os.chmod(backup, 0)

    next_revision = store.commit(
        {
            "writer": 2,
            "verified_work_authority_nonces": ["nonce-001"],
        },
        expected_revision=nonce_revision,
    )

    assert store.load() == {
        "writer": 2,
        "verified_work_authority_nonces": ["nonce-001"],
        "revision": next_revision,
    }


def test_json_store_post_replace_verification_failure_restores_previous_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    runtime = tmp_path / "runtime"
    target = runtime / "authority.json"
    store = AtomicJsonAuthorityRuntimeStore(
        target,
        allowed_root=runtime,
        repo_root=repo,
    )
    revision = store.commit({"writer": 1}, expected_revision=None)

    if os.name == "nt":
        from modules.communication.moltbot_bridge.src import (
            reddog_authority_runtime_store_windows as platform_store,
        )

        original = platform_store._verify_or_scrub
        calls = 0

        def reject_after_replace(handle: int, size: int) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise ValueError("injected_post_replace_failure")
            original(handle, size)

        monkeypatch.setattr(platform_store, "_verify_or_scrub", reject_after_replace)
    else:
        from modules.communication.moltbot_bridge.src import (
            reddog_authority_runtime_store_posix as platform_store,
        )

        original = platform_store._require_entry_identity
        calls = 0

        def reject_after_replace(*args, **kwargs) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise ValueError("injected_post_replace_failure")
            original(*args, **kwargs)

        monkeypatch.setattr(
            platform_store,
            "_require_entry_identity",
            reject_after_replace,
        )

    with pytest.raises(ValueError, match="injected_post_replace_failure"):
        store.commit({"writer": 2}, expected_revision=revision)

    assert store.load()["writer"] == 1


def test_json_store_rejects_nonexistent_target_outside_allowed_root(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    runtime = tmp_path / "runtime"
    outside = tmp_path / "outside" / "authority.json"

    with pytest.raises(ValueError, match="outside_runtime_root"):
        AtomicJsonAuthorityRuntimeStore(
            outside,
            allowed_root=runtime,
            repo_root=repo,
        )

    assert not outside.exists()


def test_json_store_rejects_relative_security_roots(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    runtime = tmp_path / "runtime"

    with pytest.raises(ValueError, match="repo_root_not_absolute"):
        AtomicJsonAuthorityRuntimeStore(
            runtime / "authority.json",
            allowed_root=runtime,
            repo_root=Path("relative-repo"),
        )
    with pytest.raises(ValueError, match="store_root_not_absolute"):
        AtomicJsonAuthorityRuntimeStore(
            runtime / "authority.json",
            allowed_root=Path("relative-runtime"),
            repo_root=repo,
        )


def test_json_store_rejects_runtime_root_inside_or_around_repo(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    with pytest.raises(ValueError, match="(?:path|root)_inside_repo"):
        AtomicJsonAuthorityRuntimeStore(
            repo / "runtime" / "authority.json",
            allowed_root=repo / "runtime",
            repo_root=repo,
        )
    with pytest.raises(ValueError, match="root_contains_repo"):
        AtomicJsonAuthorityRuntimeStore(
            tmp_path / "authority.json",
            allowed_root=tmp_path,
            repo_root=repo,
        )


@pytest.mark.parametrize(
    "path",
    [
        r"\\?\C:\runtime\authority.json",
        r"\\.\C:\runtime\authority.json",
        r"//?\\C:\\runtime\\authority.json",
        r"//server/share/runtime/authority.json",
        r"\??\C:\runtime\authority.json",
    ],
)
def test_json_store_rejects_windows_device_paths(
    tmp_path: Path,
    path: str,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    runtime = tmp_path / "runtime"

    with pytest.raises(ValueError, match="path_invalid"):
        AtomicJsonAuthorityRuntimeStore(
            path,
            allowed_root=runtime,
            repo_root=repo,
        )


def test_result_contains_no_secret_or_signing_material_labels() -> None:
    result, _, _, _ = _issue()
    blob = str(result.to_dict()).lower()
    assert "test-principal-secret" not in blob
    assert "test-reddog-secret" not in blob
    assert "private_key" not in blob
    assert result.receipt.no_signing_material_observed is True


@pytest.mark.parametrize(
    "field",
    ("progressive_policy_stage_receipt_id", "progressive_policy_stage_digest"),
)
def test_malformed_progressive_stage_digest_is_rejected(field: str) -> None:
    result, _, _, _ = _issue(**{field: "sha256:not-canonical"})

    assert result.accepted is False
    assert result.receipt.status == "DELEGATED_AUTHORITY_REJECTED"
    assert result.receipt.rejection_reasons == ("REJECT_MALFORMED_REQUEST",)


def test_audit_stage_can_sign_only_pathless_readonly_authority() -> None:
    binding = signed_audit_stage_binding()
    receipt = binding["progressive_policy_stage_receipt"]
    overrides = {
        **binding,
        "requested_operation": receipt["requested_operation"],
        "allowed_paths": (),
        "wsp15_allocation_receipt_id": receipt["wsp15_allocation_receipt_id"],
        "wsp15_allocation_digest": receipt["wsp15_allocation_digest"],
        "valve_state_required": "VALVE_OPEN_DRYRUN_ONLY",
        "consensus_receipt_digest": None,
        "sovereign_authorization_digest": None,
    }

    accepted, signer, _, _ = _issue(**overrides)
    widened = f"modules/foundups/{_FID}/**"
    rejected, rejected_signer, _, _ = _issue(
        **{**overrides, "allowed_paths": (widened,), "denied_paths": (widened,)}
    )

    assert accepted.accepted is True
    assert len(signer.requests) == 2
    assert accepted.work_authority["allowed_paths"] == []
    assert rejected.accepted is False
    assert RuntimeRejectCode.MALFORMED_REQUEST in rejected.receipt.rejection_reasons
    assert rejected_signer.requests == []


def test_bounded_stage_cannot_widen_signed_authority_paths() -> None:
    exact = f"modules/foundups/{_FID}/src/worker.py"
    binding = signed_stage_binding(
        requested_operation="bounded_module_fix",
        changed_paths=(exact,),
    )
    receipt = binding["progressive_policy_stage_receipt"]

    result, signer, _, _ = _issue(
        **binding,
        requested_operation=receipt["requested_operation"],
        allowed_paths=(f"modules/foundups/{_FID}/**",),
    )

    assert result.accepted is False
    assert RuntimeRejectCode.MALFORMED_REQUEST in result.receipt.rejection_reasons
    assert signer.requests == []


def _attacker_rehashed_stage_binding(path: str) -> dict[str, object]:
    allocation = bounded_allocation(changed_paths=(path,))
    stage = dict(signed_stage_binding()["progressive_policy_stage_receipt"])
    stage.update(
        requested_operation=allocation["requested_operation"],
        changed_paths=(path,),
        wsp15_allocation_receipt_id=allocation["receipt_id"],
        wsp15_allocation_digest=(
            stage_policy.canonical_reddog_wsp15_allocation_digest(allocation)
        ),
        complexity=allocation["complexity"],
        risk_classes=(),
        would_block_reasons=(),
        rejection_reasons=(),
    )
    stage["receipt_id"] = stage_policy._digest(stage_policy._unsigned(stage))
    return {
        "wsp15_allocation_receipt": allocation,
        "wsp15_allocation_receipt_id": allocation["receipt_id"],
        "wsp15_allocation_digest": stage["wsp15_allocation_digest"],
        "wsp15_priority": allocation["priority"],
        "wsp15_mps_total": allocation["mps_total"],
        "wsp15_reasoning_tier": allocation["reasoning_tier"],
        "progressive_policy_stage_receipt_id": stage["receipt_id"],
        "progressive_policy_stage_digest": stage_policy._digest(stage),
        "progressive_policy_stage_receipt": stage,
    }


@pytest.mark.parametrize(
    "path",
    (
        f"modules/foundups/{_FID}/src/**",
        f"modules/foundups/{_FID}/src/security_policy.py",
        "modules/foundups/trade/src/scoring_integration.py",
    ),
)
def test_attacker_rehashed_stage_cannot_reach_signer(path: str) -> None:
    binding = _attacker_rehashed_stage_binding(path)
    result, signer, store, _ = _issue(
        **binding,
        requested_operation=binding["wsp15_allocation_receipt"][
            "requested_operation"
        ],
        allowed_paths=(path,),
    )

    assert result.accepted is False
    assert RuntimeRejectCode.MALFORMED_REQUEST in result.receipt.rejection_reasons
    assert signer.requests == []
    assert store.load().get("issued_authorities", []) == []


def test_rehashed_selected_slice_cannot_replace_authoritative_queue_truth() -> None:
    original = _request()
    authoritative_item = _authoritative_queue_item(original)
    payload = original.to_dict()
    stage = dict(payload["progressive_policy_stage_receipt"])
    stage["selected_slice"] = "REDDOG_BOUNDED_FIX_PHASE1"
    stage["receipt_id"] = stage_policy._digest(stage_policy._unsigned(stage))
    payload["progressive_policy_stage_receipt"] = stage
    payload["progressive_policy_stage_receipt_id"] = stage["receipt_id"]
    payload["progressive_policy_stage_digest"] = stage_policy._digest(stage)
    queue_receipt = dict(payload["queue_consumer_receipt"])
    queue_receipt.update(
        slice_id=stage["selected_slice"],
        progressive_policy_stage_receipt=stage,
        progressive_policy_stage_receipt_id=stage["receipt_id"],
        progressive_policy_stage_digest=payload[
            "progressive_policy_stage_digest"
        ],
    )
    payload["queue_consumer_receipt"] = queue_receipt
    payload["queue_consumer_receipt_digest"] = canonical_full_work_order_digest(
        queue_receipt
    )
    attacker_request = DelegatedAuthorityRuntimeRequest(**payload)
    admission = _admit_current_queue_authority(
        request=attacker_request,
        authoritative_queue_item=authoritative_item,
    )
    signer = _MockSigner()
    store = InMemoryAuthorityRuntimeStore()

    result = issue_delegated_authority_runtime(
        request=attacker_request,
        queue_authority_admission=admission,
        store=store,
        signer=signer,
        principal_resolver=_PrincipalResolver(_principal()),
        snapshot_resolver=_SnapshotResolver(
            {attacker_request.permission_snapshot_digest: _snapshot()}
        ),
        now=_NOW,
    )

    assert admission is None
    assert result.accepted is False
    assert RuntimeRejectCode.MALFORMED_REQUEST in result.receipt.rejection_reasons
    assert signer.requests == []
    assert store.load().get("issued_authorities", []) == []


def test_signer_runtime_rejects_missing_or_replayed_queue_admission() -> None:
    request = _request()
    admission = _admit_current_queue_authority(
        request=request,
        authoritative_queue_item=_authoritative_queue_item(request),
    )
    kwargs = {
        "request": request,
        "store": InMemoryAuthorityRuntimeStore(),
        "signer": _MockSigner(),
        "principal_resolver": _PrincipalResolver(_principal()),
        "snapshot_resolver": _SnapshotResolver(
            {request.permission_snapshot_digest: _snapshot()}
        ),
        "now": _NOW,
    }

    first = issue_delegated_authority_runtime(
        queue_authority_admission=admission,
        **kwargs,
    )
    signer_requests_after_first = list(kwargs["signer"].requests)
    store_after_first = kwargs["store"].load()
    replay = issue_delegated_authority_runtime(
        queue_authority_admission=admission,
        **kwargs,
    )
    missing = issue_delegated_authority_runtime(
        queue_authority_admission=None,
        **kwargs,
    )

    assert first.accepted is True
    assert replay.accepted is False
    assert missing.accepted is False
    assert replay.receipt.rejection_reasons == (
        RuntimeRejectCode.MALFORMED_REQUEST,
    )
    assert missing.receipt.rejection_reasons == (
        RuntimeRejectCode.MALFORMED_REQUEST,
    )
    assert kwargs["signer"].requests == signer_requests_after_first
    assert kwargs["store"].load() == store_after_first


def test_audit_authority_signs_verifies_and_reaches_readonly_dispatch() -> None:
    binding = signed_audit_stage_binding()
    stage = binding["progressive_policy_stage_receipt"]
    issued, signer, _, snapshot_resolver = _issue(
        **binding,
        requested_operation=stage["requested_operation"],
        allowed_paths=(),
        denied_paths=(),
        valve_state_required="VALVE_OPEN_DRYRUN_ONLY",
        consensus_receipt_digest=None,
        sovereign_authorization_digest=None,
    )
    assert issued.accepted and issued.identity and issued.work_authority
    verified = verify_delegated_work_authority(
        work_authority=issued.work_authority,
        identity=issued.identity,
        signature_verifier=signer,
        principal_key_resolver=_PrincipalKeyResolver(),
        nonce_store=InMemoryNonceStore(),
        snapshot_resolver=snapshot_resolver,
        revocation_oracle=_NoRevocation(),
        now=_NOW,
        required_valve_state="VALVE_OPEN_DRYRUN_ONLY",
    )
    assert verified.accepted is True, verified.reason_codes
    runtime = {
        "decision": QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT,
        "authority_result": issued.to_dict(),
    }
    verification = {
        "decision": QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT,
        "verified_work_authority_digest": canonical_work_authority_digest(
            issued.work_authority
        ),
        "verification_result": verified.to_dict(),
    }
    verification.update(recorded_authority_verification_binding(runtime, verification))
    dispatch = plan_reddog_signed_authority_worker_dispatch_dry_run(
        explicit_signed_authority_worker_dispatch_dryrun_requested=True,
        queue_authority_verification_result=verification,
        queue_authority_runtime_result=runtime,
        wsp15_allocation_receipt=binding["wsp15_allocation_receipt"],
    )

    assert dispatch.accepted is True, dispatch.rejection_reasons
    assert dispatch.no_worker_spawn_performed is True
    assert dispatch.receipt is not None
    assert dispatch.receipt.requested_operation.startswith(
        "signed_0102_readonly_review:"
    )


def test_ast_denies_execution_crypto_keygen_network_and_runtime_wiring() -> None:
    src = Path(r.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    forbidden_imports = {
        "subprocess",
        "socket",
        "requests",
        "urllib",
        "cryptography",
        "nacl",
        "ecdsa",
        "web3",
        "eth_account",
        "bitcoin",
        "wallet",
        "secrets",
    }
    assert not (imported & forbidden_imports), f"forbidden import(s): {imported & forbidden_imports}"

    called = set()
    attrs = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                called.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                called.add(node.func.attr)
        if isinstance(node, ast.Attribute):
            attrs.add(node.attr)
    forbidden_calls = {"eval", "exec", "compile", "__import__", "system", "popen", "run", "Popen"}
    assert not (called & forbidden_calls)
    forbidden_attrs = {"execute", "enqueue", "openclaw_supervisor", "hermes_job_executor", "wre_core"}
    assert not (attrs & forbidden_attrs)
