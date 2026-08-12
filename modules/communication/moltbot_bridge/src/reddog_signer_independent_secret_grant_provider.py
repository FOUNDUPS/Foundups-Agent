"""Current-generation provider for independently signed secret grants."""

from __future__ import annotations

import secrets
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping

from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    IsolatedSignerClient,
    SigningRequest,
)
from modules.communication.moltbot_bridge.src.reddog_signer_independent_secret_grant_binding import (
    build_secret_grant_authority_policy,
    resolve_secret_grant_target_binding,
)
from modules.communication.moltbot_bridge.src.reddog_signer_independent_secret_grant_verification import (
    require_final_secret_grant,
    require_secret_grant_signer_response,
)
from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_current_selection import (
    lease_validated_owner_e0_current_admission,
)
from modules.communication.moltbot_bridge.src.reddog_signer_resolve_per_sign_backend import (
    ResolvePerSignBinding,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_access_grant_contract import (
    GRANT_SCHEMA,
    MAX_GRANT_TTL_SECONDS,
    signer_secret_access_grant_id,
    signer_secret_access_request_digest,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_durable_nonce_store import (
    DurableSignerSecretGrantNonceStore,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_issuance import (
    build_secret_grant_signing_request,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_authority_policy import (
    SignerSecretGrantAuthorityPolicy,
)


@dataclass(frozen=True, slots=True)
class IndependentGrantAuthorityBinding:
    """Public client binding for a separately hosted grant signer service."""

    client: IsolatedSignerClient
    principal_id: str
    principal_provider: str
    public_key: str
    key_epoch: str
    requester_principal_id: str


@dataclass(frozen=True, slots=True)
class IndependentSignerSecretGrantProvider:
    """Issue one grant while holding the target signer's generation fence."""

    repo_root: Path
    owner_config_path: Path
    owner_policy: Mapping[str, Any]
    replay_store: DurableSignerSecretGrantNonceStore
    grant_authority: IndependentGrantAuthorityBinding
    clock: Callable[[], int] = lambda: int(time.time())
    nonce_factory: Callable[[], str] = lambda: secrets.token_hex(32)
    ttl_seconds: int = 30

    @contextmanager
    def lease(self, request: SigningRequest) -> Iterator[Mapping[str, Any]]:
        """Keep E0 current-generation admission pinned through target use."""

        if type(request) is not SigningRequest:
            raise ValueError("secret_grant_request_invalid")
        with lease_validated_owner_e0_current_admission(
            owner_config_path=self.owner_config_path,
            repo_root=self.repo_root.resolve(),
            policy=self.owner_policy,
        ) as owner:
            grant = self._issue(request, owner)
            yield grant

    def _issue(self, request: SigningRequest, owner: Any) -> Mapping[str, Any]:
        now = self._now()
        binding = self._resolve_binding(owner)
        policy = self._authority_policy(owner, binding)
        grant = self._unsigned_grant(request, binding, owner.policy, now)
        sign_request = build_secret_grant_signing_request(
            grant,
            policy=policy,
            consensus_receipt_digest=request.consensus_receipt_digest,
        )
        response = self.grant_authority.client.sign(sign_request)
        require_secret_grant_signer_response(
            response,
            sign_request,
            authority_public_key=self.grant_authority.public_key,
            authority_key_epoch=self.grant_authority.key_epoch,
        )
        signed = {**grant, "signature": response.signature}
        require_final_secret_grant(
            signed, request, binding, owner.resolver, now_epoch=now
        )
        return signed

    def _resolve_binding(self, owner: Any) -> ResolvePerSignBinding:
        return resolve_secret_grant_target_binding(owner.policy, self.replay_store)

    def _authority_policy(
        self, owner: Any, binding: ResolvePerSignBinding
    ) -> SignerSecretGrantAuthorityPolicy:
        policy = owner.policy
        authority = self.grant_authority
        return build_secret_grant_authority_policy(
            policy,
            binding,
            self.replay_store,
            authority_principal_id=authority.principal_id,
            authority_principal_provider=authority.principal_provider,
            authority_public_key=authority.public_key,
            authority_key_epoch=authority.key_epoch,
            requester_principal_id=authority.requester_principal_id,
        )

    def _unsigned_grant(
        self,
        request: SigningRequest,
        binding: ResolvePerSignBinding,
        owner_policy: Mapping[str, Any],
        now: int,
    ) -> dict[str, Any]:
        nonce = self._nonce()
        expires = min(
            now + self._ttl(),
            int(owner_policy["expires_at"]),
        )
        if expires <= now:
            raise ValueError("secret_grant_expired")
        grant = {
            "schema_version": GRANT_SCHEMA,
            **asdict(binding),
            "signing_request_digest": signer_secret_access_request_digest(
                request.to_dict()
            ),
            "requested_operation": request.requested_operation,
            "authority_tier": request.authority_tier,
            "attested_peer_principal_id": request.requester_principal_id,
            "nonce": nonce,
            "issued_at": now,
            "expires_at": expires,
            "grant_id": "",
            "signature": "pending-signature",
        }
        grant["grant_id"] = signer_secret_access_grant_id(grant)
        return grant

    def _now(self) -> int:
        value = self.clock()
        if type(value) is not int or value < 0:
            raise ValueError("secret_grant_clock_invalid")
        return value

    def _ttl(self) -> int:
        if type(self.ttl_seconds) is not int or not 0 < self.ttl_seconds <= MAX_GRANT_TTL_SECONDS:
            raise ValueError("secret_grant_ttl_invalid")
        return self.ttl_seconds

    def _nonce(self) -> str:
        value = self.nonce_factory()
        if (
            type(value) is not str
            or not 16 <= len(value) <= 128
            or not value.isascii()
            or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._:-" for char in value)
        ):
            raise ValueError("secret_grant_nonce_invalid")
        return value
__all__ = [
    "IndependentGrantAuthorityBinding",
    "IndependentSignerSecretGrantProvider",
]
