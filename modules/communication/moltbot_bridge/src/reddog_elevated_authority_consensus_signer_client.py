"""Consensus-aware adapter over the existing external secret-grant signer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_capability import (
    VerifiedElevatedAuthoritySigningPermit,
    consume_elevated_authority_signing_permit,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    RuntimeRejectCode,
    SigningRequest,
    SigningResponse,
)


class ElevatedConsensusGrantLease(Protocol):
    def __enter__(self) -> Mapping[str, Any]: ...

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None: ...


@dataclass(frozen=True, slots=True)
class ElevatedConsensusGrantProviderIdentity:
    authority_principal_id: str
    authority_principal_provider: str
    authority_public_key: str
    authority_key_epoch: str
    authority_service_id: str


class ElevatedConsensusGrantProvider(Protocol):
    def elevated_consensus_provider_identity(
        self,
    ) -> ElevatedConsensusGrantProviderIdentity: ...

    def lease(
        self,
        request: SigningRequest,
        *,
        elevated_consensus_signing_permit: VerifiedElevatedAuthoritySigningPermit,
    ) -> ElevatedConsensusGrantLease: ...


class GrantAwareSigner(Protocol):
    def sign_with_secret_grant(
        self, request: SigningRequest, secret_access_grant: Mapping[str, Any]
    ) -> SigningResponse: ...


@dataclass(frozen=True, slots=True)
class ElevatedConsensusExternalSignerClient:
    """Release one secret grant only after exact consensus-permit admission."""

    signer: GrantAwareSigner
    principal_grant_provider: ElevatedConsensusGrantProvider
    reddog_grant_provider: ElevatedConsensusGrantProvider

    def __post_init__(self) -> None:
        try:
            principal = self.principal_grant_provider.elevated_consensus_provider_identity()
            reddog = self.reddog_grant_provider.elevated_consensus_provider_identity()
        except Exception as exc:
            raise ValueError("elevated_consensus_grant_provider_identity_invalid") from exc
        if not _independent_providers(principal, reddog):
            raise ValueError("elevated_consensus_grant_providers_not_independent")

    def sign(self, request: SigningRequest) -> SigningResponse:
        return _reject(RuntimeRejectCode.ELEVATED_CONSENSUS_NOT_VERIFIED)

    def sign_with_elevated_consensus(
        self,
        request: SigningRequest,
        permit: VerifiedElevatedAuthoritySigningPermit,
    ) -> SigningResponse:
        try:
            provider = _provider_for_role(self, request.signer_role)
            with provider.lease(
                request,
                elevated_consensus_signing_permit=permit,
            ) as grant:
                if not isinstance(grant, Mapping):
                    return _reject(RuntimeRejectCode.ELEVATED_CONSENSUS_NOT_VERIFIED)
                return self.signer.sign_with_secret_grant(request, grant)
        except Exception:
            return _reject(RuntimeRejectCode.ELEVATED_CONSENSUS_NOT_VERIFIED)


def _provider_for_role(
    client: ElevatedConsensusExternalSignerClient, signer_role: str
) -> ElevatedConsensusGrantProvider:
    if signer_role == "principal":
        return client.principal_grant_provider
    if signer_role == "reddog":
        return client.reddog_grant_provider
    raise ValueError("elevated_consensus_signer_role_invalid")


def _independent_providers(principal: Any, reddog: Any) -> bool:
    if not all(
        type(value) is ElevatedConsensusGrantProviderIdentity
        for value in (principal, reddog)
    ):
        return False
    principal_authority = (
        principal.authority_principal_id,
        principal.authority_principal_provider,
    )
    reddog_authority = (
        reddog.authority_principal_id,
        reddog.authority_principal_provider,
    )
    return (
        principal_authority != reddog_authority
        and principal.authority_public_key != reddog.authority_public_key
        and principal.authority_service_id != reddog.authority_service_id
    )


def admit_secret_grant_consensus(
    request: SigningRequest,
    permit: VerifiedElevatedAuthoritySigningPermit | None,
    *,
    now: int,
) -> Mapping[str, Any] | None:
    """Return signer-verifiable proof or reject LOW/elevated ambiguity."""

    if request.authority_tier == "LOW":
        if permit is not None or request.consensus_receipt_digest is not None:
            raise ValueError("secret_grant_consensus_invalid")
        return None
    proof = consume_elevated_authority_signing_permit(
        permit, signing_request=request, now=now
    )
    if proof is None:
        raise ValueError("secret_grant_consensus_invalid")
    return proof


def _reject(code: str) -> SigningResponse:
    return SigningResponse(
        accepted=False,
        rejection_code=code,
        no_secret_material_returned=True,
    )


__all__ = [
    "ElevatedConsensusExternalSignerClient",
    "ElevatedConsensusGrantProviderIdentity",
    "admit_secret_grant_consensus",
]
