"""External-signer adapter for one exact authoritative-use lease."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol

from modules.communication.moltbot_bridge.src.reddog_authoritative_use_lease import (
    AuthoritativeUseLease,
    rehydrate_external_authoritative_use_lease,
)
from modules.communication.moltbot_bridge.src.reddog_authoritative_use_lease_contract import (
    build_authoritative_use_lease_request,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
    SigningResponse,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    SignatureVerifier,
)


class GrantAwareExternalSigner(Protocol):
    def sign_with_secret_grant(
        self, request: SigningRequest, secret_access_grant: Mapping[str, Any]
    ) -> SigningResponse:
        """Sign only after the external boundary consumes the exact grant."""


class AuthoritativeUseLeaseGrantProvider(Protocol):
    def __call__(self, request: SigningRequest) -> Mapping[str, Any] | None:
        """Return a root-authorized grant bound to this exact request."""


@dataclass(frozen=True, slots=True)
class ExternalSignerAuthoritativeUseLeaseIssuer:
    """Verify one external signer response and release an opaque capability."""

    signer: GrantAwareExternalSigner
    grant_provider: AuthoritativeUseLeaseGrantProvider
    signature_verifier: SignatureVerifier
    consume_evidence_once: Callable[[str], bool]
    trusted_now_epoch: Callable[[], int]

    def issue(
        self,
        *,
        payload: Mapping[str, Any],
        authority_tier: str,
        consume_authority_once: Callable[[], bool],
    ) -> AuthoritativeUseLease | None:
        try:
            request = build_authoritative_use_lease_request(
                payload, authority_tier=authority_tier
            )
            grant = self.grant_provider(request)
            if not isinstance(grant, Mapping):
                return None
            response = self.signer.sign_with_secret_grant(request, grant)
        except Exception:
            return None
        return rehydrate_external_authoritative_use_lease(
            request=request,
            response=response,
            signature_verifier=self.signature_verifier,
            consume_evidence_once=self.consume_evidence_once,
            consume_authority_once=consume_authority_once,
            trusted_now_epoch=self.trusted_now_epoch,
        )


__all__ = [
    "AuthoritativeUseLeaseGrantProvider",
    "ExternalSignerAuthoritativeUseLeaseIssuer",
    "GrantAwareExternalSigner",
]
