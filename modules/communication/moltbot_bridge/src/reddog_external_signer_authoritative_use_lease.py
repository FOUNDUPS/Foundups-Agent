"""External-signer adapter for one exact authoritative-use lease."""

from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
import time
from typing import Any, Callable, Mapping, Protocol

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
    def issue_grant(
        self, request: SigningRequest, *, elevated_consensus_signing_permit: Any = None
    ) -> Mapping[str, Any]:
        """Return the verified grant only after clean issuance lease exit."""


@dataclass(frozen=True, slots=True)
class ExternalSignerAuthoritativeUseLeaseIssuer:
    """Verify one external signer response and release an opaque capability."""

    signer: GrantAwareExternalSigner
    grant_provider: AuthoritativeUseLeaseGrantProvider
    replay_store: DurableSignerSecretGrantNonceStore
    current_generation_authority: SignerCurrentGenerationRuntimeAuthority
    effect_signing_authority: Any = None
    effect_proof_supplier: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None

    def issue_for_worktree(
        self, *, queue_item_id, selected_slice, work_order, executor_plan_result,
        valve_decision, signed_work_authority, identity, expected_bindings,
    ) -> AuthoritativeUseLease | None:
        """Request approval for the final checked decision, never a preview grant.

        Explicitly provisioned dependencies supply authentic effect evidence.
        This adapter discharges no other resident use-time rejection reason.
        """
        from .reddog_current_effect_signing_authority import CurrentEffectSigningAuthority
        from .reddog_effect_consensus_proof import (
            snapshot_effect_consensus_proof, discard_effect_signing_permit,
        )
        from .reddog_authoritative_use_lease_contract import (
            authoritative_use_effect_digest, digest_mapping,
            validate_authoritative_use_lease_request,
        )
        from .reddog_worktree_admission_capability import authoritative_worktree_effect_payload
        from .reddog_wre_execution_valve import VALVE_OPEN_WORKTREE_CREATE

        permit = None
        try:
            if (type(self.effect_signing_authority) is not CurrentEffectSigningAuthority
                    or not callable(self.effect_proof_supplier)
                    or type(queue_item_id) is not str or not queue_item_id.strip()
                    or type(selected_slice) is not str or not selected_slice.strip()
                    or valve_decision.get("valve_state") != VALVE_OPEN_WORKTREE_CREATE
                    or valve_decision.get("rejection_reasons") != []
                    or not signed_work_authority or not identity or not expected_bindings):
                return None
            effect = authoritative_worktree_effect_payload(
                queue_item_id, selected_slice, work_order, executor_plan_result, valve_decision)
            expected = dict(effect_kind="worktree_create", effect_payload=effect,
                effect_request_digest=authoritative_use_effect_digest("worktree_create", effect),
                work_authority_digest=digest_mapping(signed_work_authority),
                identity_digest=digest_mapping(identity),
                expected_bindings_digest=digest_mapping(expected_bindings))
            proof, _, _, target = snapshot_effect_consensus_proof(
                self.effect_proof_supplier(deepcopy(expected)))
            payload = validate_authoritative_use_lease_request(target, now_epoch=int(time.time()))
            if payload is None or any(payload[k] != v for k, v in expected.items()):
                return None
            if self.prepare_request(payload=payload, authority_tier=target.authority_tier) != target:
                return None
            permit = self.effect_signing_authority.prepare_permit(proof)
            if permit is None:
                return None
            return self.issue(payload=payload, authority_tier=target.authority_tier,
                              effect_signing_permit=permit)
        except Exception:
            return None
        finally:
            discard_effect_signing_permit(permit)

    def prepare_request(self, *, payload: Mapping[str, Any], authority_tier: str) -> SigningRequest | None:
        try:
            if (
                type(self.replay_store) is not DurableSignerSecretGrantNonceStore
                or type(self.current_generation_authority) is not SignerCurrentGenerationRuntimeAuthority
            ):
                return None
            request = build_authoritative_use_lease_request(
                _bind_replay_store(payload, self.replay_store),
                authority_tier=authority_tier,
            )
            return request
        except Exception:
            return None

    def issue(
        self,
        *,
        payload: Mapping[str, Any],
        authority_tier: str,
        effect_signing_permit=None,
    ) -> AuthoritativeUseLease | None:
        try:
            if (
                type(self.replay_store) is not DurableSignerSecretGrantNonceStore
                or type(self.current_generation_authority)
                is not SignerCurrentGenerationRuntimeAuthority
            ):
                return None
            now_epoch = int(time.time())
            request = self.prepare_request(
                payload=payload, authority_tier=authority_tier,
            )
            if request is None:
                return None
            grant = (self.grant_provider.issue_grant(request) if effect_signing_permit is None
                     else self.grant_provider.issue_grant(
                         request, elevated_consensus_signing_permit=effect_signing_permit))
            if not isinstance(grant, Mapping):
                return None
            response = self.signer.sign_with_secret_grant(request, grant)
            return _rehydrate_external_authoritative_use_lease(
                request=request,
                response=response,
                current_generation_authority=self.current_generation_authority,
                replay_store=self.replay_store,
                now_epoch=now_epoch,
            )
        except Exception:
            return None


def _bind_replay_store(
    payload: Mapping[str, Any], store: DurableSignerSecretGrantNonceStore
) -> dict[str, Any]:
    binding = {
        "replay_store_binding_digest": store.replay_store_binding_digest,
        "replay_store_id": store.replay_store_id,
        "replay_store_durability_receipt_id": store.durability_receipt_id,
        "replay_store_instance_digest": store.replay_store_instance_digest,
    }
    for key, value in binding.items():
        if key in payload and payload[key] != value:
            raise ValueError("authoritative_use_replay_store_mismatch")
    return {**dict(payload), **binding}


__all__ = [
    "AuthoritativeUseLeaseGrantProvider",
    "ExternalSignerAuthoritativeUseLeaseIssuer",
    "GrantAwareExternalSigner",
]
