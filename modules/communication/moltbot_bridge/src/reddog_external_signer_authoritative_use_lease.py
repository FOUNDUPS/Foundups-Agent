"""External-signer adapter for one exact authoritative-use lease."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Mapping, Protocol

from modules.communication.moltbot_bridge.src.reddog_authoritative_use_lease import (
    AuthoritativeUseLease,
    _rehydrate_external_authoritative_use_lease,
)
from modules.communication.moltbot_bridge.src.reddog_authoritative_use_lease_contract import (
    build_authoritative_use_lease_request,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningRequest,
    SigningResponse,
)
from modules.communication.moltbot_bridge.src.reddog_signer_current_generation_runtime_binding import (
    SignerCurrentGenerationRuntimeAuthority,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_durable_nonce_store import (
    DurableSignerSecretGrantNonceStore,
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
    replay_store: DurableSignerSecretGrantNonceStore
    current_generation_authority: SignerCurrentGenerationRuntimeAuthority

    def issue(
        self,
        *,
        payload: Mapping[str, Any],
        authority_tier: str,
    ) -> AuthoritativeUseLease | None:
        try:
            if (
                type(self.replay_store) is not DurableSignerSecretGrantNonceStore
                or type(self.current_generation_authority)
                is not SignerCurrentGenerationRuntimeAuthority
            ):
                return None
            now_epoch = int(time.time())
            current_generation = self.current_generation_authority.resolve(
                now_epoch=now_epoch
            )
            request = build_authoritative_use_lease_request(
                payload, authority_tier=authority_tier
            )
            grant = self.grant_provider(request)
            if not isinstance(grant, Mapping):
                return None
            response = self.signer.sign_with_secret_grant(request, grant)
        except Exception:
            return None
        return _rehydrate_external_authoritative_use_lease(
            request=request,
            response=response,
            current_generation=current_generation,
            replay_store=self.replay_store,
            now_epoch=now_epoch,
        )


__all__ = [
    "AuthoritativeUseLeaseGrantProvider",
    "ExternalSignerAuthoritativeUseLeaseIssuer",
    "GrantAwareExternalSigner",
]
