"""Tests for REDDOG_SIGNER_AND_DELEGATED_AUTHORITY_RUNTIME_PHASE1."""

from __future__ import annotations

import ast
import hashlib
import hmac
from pathlib import Path

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
    RevocationOracle,
    SignatureVerifier,
    verify_delegated_work_authority,
)

_NOW = 1000
_REPO = "FOUNDUPS/Foundups-Agent"
_FID = "paccess_001"
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
        "principal_id": "github:mjtrout",
        "principal_provider": "github",
        "principal_public_key": "pub:principal",
        "reddog_id": "reddog:abc123",
        "reddog_public_key": "pub:reddog",
        "repo_full_name": _REPO,
        "foundup_id": _FID,
        "allowed_paths": (f"modules/foundups/{_FID}/**",),
        "denied_paths": (),
        "requested_operation": "create_foundup",
        "permission_snapshot_digest": "sha256:snap-1",
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
    request = _request(**overrides)
    signer = _MockSigner()
    store = InMemoryAuthorityRuntimeStore()
    snapshot_resolver = _SnapshotResolver({request.permission_snapshot_digest: _snapshot()})
    result = issue_delegated_authority_runtime(
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


def test_default_signer_fails_closed() -> None:
    request = _request()
    result = issue_delegated_authority_runtime(
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
    result = issue_delegated_authority_runtime(
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


def test_low_authority_can_issue_without_cosign() -> None:
    result, _, _, _ = _issue(
        requested_operation="inspect_repo",
        consensus_receipt_digest=None,
        sovereign_authorization_digest=None,
    )
    assert result.accepted is True, result.receipt.rejection_reasons
    assert result.work_authority["authority_tier"] == "LOW"


def test_stale_permission_snapshot_rejects() -> None:
    request = _request()
    result = issue_delegated_authority_runtime(
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
    result = issue_delegated_authority_runtime(
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
    result, _, _, _ = _issue(allowed_paths=(".github/workflows/deploy.yml",))
    assert result.accepted is False
    assert RuntimeRejectCode.PATH_OUT_OF_SCOPE in result.receipt.rejection_reasons

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
    first = issue_delegated_authority_runtime(request=request, **kwargs)
    second = issue_delegated_authority_runtime(request=request, **kwargs)
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
    result = issue_delegated_authority_runtime(
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
    result = issue_delegated_authority_runtime(
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
    path = tmp_path / "authority-state.json"
    result = issue_delegated_authority_runtime(
        request=request,
        store=AtomicJsonAuthorityRuntimeStore(path),
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


def test_result_contains_no_secret_or_signing_material_labels() -> None:
    result, _, _, _ = _issue()
    blob = str(result.to_dict()).lower()
    assert "test-principal-secret" not in blob
    assert "test-reddog-secret" not in blob
    assert "private_key" not in blob
    assert result.receipt.no_signing_material_observed is True


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
