"""Bounded execution of an already validated delegated-authority signing plan."""

from __future__ import annotations

from typing import Any

from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_capability import (
    VerifiedElevatedAuthorityConsensusCapability,
    VerifiedElevatedAuthoritySigningPermit,
    discard_elevated_authority_signing_permit,
    prepare_elevated_authority_signing_permit,
)
from modules.communication.moltbot_bridge.src.reddog_signer_authority_store_commit import (
    commit_issued_authority,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    AUTHORITY_ISSUED,
    AUTHORITY_SCHEMA_VERSION,
    HIGH_AUTHORITY_TIER,
    AuthorityRuntimeStore,
    DelegatedAuthorityRuntimeReceipt,
    DelegatedAuthorityRuntimeRequest,
    DelegatedAuthorityRuntimeResult,
    IsolatedSignerClient,
    RuntimeRejectCode,
    SigningRequest,
    SigningResponse,
    _canonical_digest,
    _rejection_result,
    _validate_signing_response,
)
from modules.communication.moltbot_bridge.src.reddog_work_authority_digest import (
    canonical_work_authority_digest,
)


def execute_signing_plan(
    *,
    request: DelegatedAuthorityRuntimeRequest,
    store: AuthorityRuntimeStore,
    signer: IsolatedSignerClient,
    authority_tier: str,
    elevated_consensus_capability: VerifiedElevatedAuthorityConsensusCapability | None,
    signing_plan: tuple[dict[str, Any], dict[str, Any], SigningRequest, SigningRequest],
    principal_fingerprint: str,
    reddog_fingerprint: str,
    now: int,
) -> DelegatedAuthorityRuntimeResult:
    identity, work_authority, identity_request, workauth_request = signing_plan
    permit = _prepare_permit(
        request, authority_tier, elevated_consensus_capability,
        identity_request, workauth_request, now,
    )
    if authority_tier == HIGH_AUTHORITY_TIER and permit is None:
        return _reject(request, now, RuntimeRejectCode.ELEVATED_CONSENSUS_NOT_VERIFIED)
    identity_sign, workauth_sign, rejection = _sign_pair(
        signer, request, authority_tier, permit, identity_request,
        workauth_request, principal_fingerprint, reddog_fingerprint,
    )
    if rejection:
        return _reject(request, now, rejection)
    identity["signature"] = identity_sign.signature
    work_authority["signature"] = workauth_sign.signature
    return _commit(
        store, request, identity, work_authority,
        identity_sign, workauth_sign, now,
    )


def _prepare_permit(
    request: DelegatedAuthorityRuntimeRequest,
    tier: str,
    capability: VerifiedElevatedAuthorityConsensusCapability | None,
    identity_request: SigningRequest,
    workauth_request: SigningRequest,
    now: int,
) -> VerifiedElevatedAuthoritySigningPermit | None:
    if tier != HIGH_AUTHORITY_TIER:
        return None
    return prepare_elevated_authority_signing_permit(
        capability,
        authority_request=request,
        signing_requests=(identity_request, workauth_request),
        now=now,
    )


def _sign_pair(
    signer: IsolatedSignerClient,
    request: DelegatedAuthorityRuntimeRequest,
    tier: str,
    permit: VerifiedElevatedAuthoritySigningPermit | None,
    identity_request: SigningRequest,
    workauth_request: SigningRequest,
    principal_fingerprint: str,
    reddog_fingerprint: str,
) -> tuple[SigningResponse, SigningResponse, str | None]:
    identity = _sign_request(signer, identity_request, tier, permit)
    rejection = _validate_signing_response(
        identity,
        expected_public_key=request.principal_public_key,
        expected_fingerprint=principal_fingerprint,
        expected_key_epoch=request.key_epoch,
    )
    workauth = SigningResponse(accepted=False)
    if not rejection:
        workauth = _sign_request(signer, workauth_request, tier, permit)
        rejection = _validate_signing_response(
            workauth,
            expected_public_key=request.reddog_public_key,
            expected_fingerprint=reddog_fingerprint,
            expected_key_epoch=request.key_epoch,
        )
    if rejection:
        discard_elevated_authority_signing_permit(permit)
    return identity, workauth, rejection


def _sign_request(
    signer: IsolatedSignerClient,
    request: SigningRequest,
    tier: str,
    permit: VerifiedElevatedAuthoritySigningPermit | None,
) -> SigningResponse:
    if tier != HIGH_AUTHORITY_TIER:
        return signer.sign(request)
    elevated_sign = getattr(signer, "sign_with_elevated_consensus", None)
    if not callable(elevated_sign) or permit is None:
        return _sign_reject()
    try:
        response = elevated_sign(request, permit)
    except Exception:
        response = None
    return response if type(response) is SigningResponse else _sign_reject()


def _commit(
    store: AuthorityRuntimeStore,
    request: DelegatedAuthorityRuntimeRequest,
    identity: dict[str, Any],
    work_authority: dict[str, Any],
    identity_sign: SigningResponse,
    workauth_sign: SigningResponse,
    now: int,
) -> DelegatedAuthorityRuntimeResult:
    identity_digest = "sha256:" + _canonical_digest(identity)
    workauth_digest = canonical_work_authority_digest(work_authority)
    receipt_id = _receipt_id(request, identity_digest, workauth_digest, now)
    try:
        revision = commit_issued_authority(
            store, request=request, identity_digest=identity_digest,
            work_authority_digest=workauth_digest, receipt_id=receipt_id,
            schema_version=AUTHORITY_SCHEMA_VERSION, issued_status=AUTHORITY_ISSUED,
        )
    except Exception:
        return _reject(request, now, RuntimeRejectCode.STORE_COMMIT_FAILED)
    receipt = DelegatedAuthorityRuntimeReceipt(
        receipt_id=receipt_id, status=AUTHORITY_ISSUED, generated_at=now,
        work_order_id=request.work_order_id, principal_id=request.principal_id,
        reddog_id=request.reddog_id, identity_digest=identity_digest,
        work_authority_digest=workauth_digest, store_revision=revision,
        signer_audit_macs=(identity_sign.audit_mac, workauth_sign.audit_mac),
        rejection_reasons=(),
    )
    return DelegatedAuthorityRuntimeResult(
        accepted=True, receipt=receipt, identity=identity,
        work_authority=work_authority,
    )


def _receipt_id(
    request: DelegatedAuthorityRuntimeRequest,
    identity_digest: str,
    workauth_digest: str,
    now: int,
) -> str:
    payload = {
        "status": AUTHORITY_ISSUED,
        "work_order_id": request.work_order_id,
        "identity_digest": identity_digest,
        "work_authority_digest": workauth_digest,
        "generated_at": now,
    }
    return "authority-runtime-" + _canonical_digest(payload)[:16]


def _reject(
    request: DelegatedAuthorityRuntimeRequest, now: int, code: str
) -> DelegatedAuthorityRuntimeResult:
    return _rejection_result(now=now, request=request, reasons=[code])


def _sign_reject() -> SigningResponse:
    return SigningResponse(
        accepted=False,
        rejection_code=RuntimeRejectCode.ELEVATED_CONSENSUS_NOT_VERIFIED,
        no_secret_material_returned=True,
    )

__all__ = ["execute_signing_plan"]
