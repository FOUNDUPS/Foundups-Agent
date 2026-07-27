"""Verify signed architect-proposal authority at promotion use time.

The proposal attestation and policy authorization are cryptographic evidence,
not opaque Python capabilities. Promotion accepts them only after rebuilding
the exact proposal payload and verifying the active isolated-signer runtime
against an independently supplied principal-key resolver.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_architect_proposal_authenticity import (
    ArchitectProposalAuthenticityPayload,
    ArchitectProposalIntegrityContext,
    build_architect_proposal_authenticity_payload,
    rehydrate_architect_proposal_authenticity_payload,
    verify_architect_proposal_attestation_integrity,
)
from modules.communication.moltbot_bridge.src.reddog_architect_proposal_runtime_authorization import (
    verify_architect_proposal_runtime_authorization,
)
from modules.communication.moltbot_bridge.src.reddog_authority_profile_source_artifact_supply import (
    canonical_authority_profile_source_digest,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_runtime_wiring import (
    SignerSocketServiceRuntimeWiringConfig,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    PrincipalKeyResolver,
)


VERIFIED_ARCHITECT_PROPOSAL_AUTHORITY_SCHEMA_VERSION = (
    "verified_reddog_architect_proposal_promotion_authority.v2"
)


@dataclass(frozen=True)
class ArchitectProposalAuthorityBinding:
    """Verified signed evidence bound to one active signer runtime."""

    principal_id: str
    principal_provider: str
    principal_public_key: str
    reddog_id: str
    reddog_public_key: str
    key_epoch: str
    authority_profile_source_receipt_id: str
    attestation_id: str
    attestation_digest: str
    policy_authorization_id: str
    policy_authorization_digest: str
    signer_instance_id: str
    replay_store_binding_digest: str
    security_context_digest: str
    signer_runtime_context_digest: str


def verify_architect_proposal_promotion_authority(
    *,
    attestation: Mapping[str, Any],
    proposal_admission: Mapping[str, Any],
    determination: Mapping[str, Any],
    queue_candidate: Mapping[str, Any],
    authority_profile: Mapping[str, Any],
    signer_runtime_config: SignerSocketServiceRuntimeWiringConfig,
    principal_key_resolver: PrincipalKeyResolver,
    now_epoch: int,
    revoked_key_epochs: frozenset[str] = frozenset(),
) -> ArchitectProposalAuthorityBinding:
    """Verify both signatures against current records and active runtime trust."""

    serialized, expected_payload, authorization = _verification_inputs(
        attestation=attestation,
        proposal_admission=proposal_admission,
        determination=determination,
        queue_candidate=queue_candidate,
        authority_profile=authority_profile,
        signer_runtime_config=signer_runtime_config,
        principal_key_resolver=principal_key_resolver,
        now_epoch=now_epoch,
    )
    verified_attestation = _verify_attestation(
        serialized,
        expected_payload=expected_payload,
        now_epoch=now_epoch,
        revoked_key_epochs=revoked_key_epochs,
    )
    _verify_runtime_identity(authorization, expected_payload, authority_profile)
    return _authority_binding(verified_attestation, authorization, signer_runtime_config)


def _authority_binding(
    verified_attestation: Any,
    authorization: Any,
    signer_runtime_config: SignerSocketServiceRuntimeWiringConfig,
) -> ArchitectProposalAuthorityBinding:
    return ArchitectProposalAuthorityBinding(
        principal_id=authorization.principal_id,
        principal_provider=authorization.principal_provider,
        principal_public_key=authorization.principal_public_key,
        reddog_id=authorization.reddog_id,
        reddog_public_key=authorization.reddog_public_key,
        key_epoch=authorization.key_epoch,
        authority_profile_source_receipt_id=(
            authorization.authority_profile_source_receipt_id
        ),
        attestation_id=verified_attestation.payload.attestation_id,
        attestation_digest=_digest(verified_attestation.to_dict()),
        policy_authorization_id=authorization.authorization_id,
        policy_authorization_digest=_digest(authorization.to_dict()),
        signer_instance_id=authorization.signer_instance_id,
        replay_store_binding_digest=authorization.replay_store_binding_digest,
        security_context_digest=authorization.security_context_digest,
        signer_runtime_context_digest=_runtime_context_digest(
            authorization, signer_runtime_config
        ),
    )


def _verification_inputs(
    *,
    attestation: Mapping[str, Any],
    proposal_admission: Mapping[str, Any],
    determination: Mapping[str, Any],
    queue_candidate: Mapping[str, Any],
    authority_profile: Mapping[str, Any],
    signer_runtime_config: SignerSocketServiceRuntimeWiringConfig,
    principal_key_resolver: PrincipalKeyResolver,
    now_epoch: int,
) -> tuple[Mapping[str, Any], ArchitectProposalAuthenticityPayload, Any]:
    serialized = _mapping(attestation)
    profile = _mapping(authority_profile)
    if not serialized or not profile:
        raise ValueError("architect_proposal_authority_input_missing")
    _verify_authority_profile_receipt(profile)
    payload = rehydrate_architect_proposal_authenticity_payload(
        {key: value for key, value in serialized.items() if key != "signature"}
    )
    expected = _rebuild_payload(
        payload=payload,
        proposal_admission=proposal_admission,
        determination=determination,
        queue_candidate=queue_candidate,
        authority_profile=profile,
    )
    policy, authorization = verify_architect_proposal_runtime_authorization(
        signer_runtime_config,
        principal_key_resolver=principal_key_resolver,
        now_epoch=int(now_epoch),
    )
    if policy.expected_payload != expected:
        raise ValueError("architect_proposal_runtime_policy_mismatch")
    return serialized, expected, authorization


def _verify_authority_profile_receipt(
    profile: Mapping[str, Any],
) -> None:
    receipt_id = _required_text(
        profile, "authority_profile_source_receipt_id"
    )
    unsigned = {
        key: value
        for key, value in profile.items()
        if key != "authority_profile_source_receipt_id"
    }
    if receipt_id != canonical_authority_profile_source_digest(unsigned):
        raise ValueError("architect_proposal_authority_profile_receipt_invalid")


def _verify_attestation(
    attestation: Mapping[str, Any],
    *,
    expected_payload: ArchitectProposalAuthenticityPayload,
    now_epoch: int,
    revoked_key_epochs: frozenset[str],
):
    return verify_architect_proposal_attestation_integrity(
        attestation,
        context=ArchitectProposalIntegrityContext(
            expected_payload=expected_payload,
            now_epoch=int(now_epoch),
            revoked_key_epochs=frozenset(revoked_key_epochs),
        ),
    )


def _verify_runtime_identity(
    authorization: Any,
    payload: ArchitectProposalAuthenticityPayload,
    authority_profile: Mapping[str, Any],
) -> None:
    expected = {
        "principal_id": authorization.principal_id,
        "principal_provider": authorization.principal_provider,
        "principal_public_key": authorization.principal_public_key,
        "reddog_id": authorization.reddog_id,
        "reddog_public_key": authorization.reddog_public_key,
        "key_epoch": authorization.key_epoch,
        "authority_profile_source_receipt_id": (
            authorization.authority_profile_source_receipt_id
        ),
    }
    if any(
        _required_text(authority_profile, key) != value
        for key, value in expected.items()
    ):
        raise ValueError("architect_proposal_runtime_identity_mismatch")
    if any(
        (
            authorization.principal_id != payload.requester_principal_id,
            authorization.reddog_id != payload.reddog_id,
            authorization.reddog_public_key != payload.signer_public_key,
            authorization.key_epoch != payload.key_epoch,
            authorization.authority_profile_source_receipt_id
            != payload.authority_profile_source_receipt_id,
        )
    ):
        raise ValueError("architect_proposal_runtime_identity_mismatch")


def _runtime_context_digest(
    authorization: Any,
    config: SignerSocketServiceRuntimeWiringConfig,
) -> str:
    return _digest(
        {
            "signer_instance_id": authorization.signer_instance_id,
            "replay_store_binding_digest": (
                authorization.replay_store_binding_digest
            ),
            "security_context_digest": authorization.security_context_digest,
            "proposal_replay_high_water_durability_receipt_id": str(
                config.proposal_replay_high_water_durability_receipt_id or ""
            ),
        }
    )


def _rebuild_payload(
    *,
    payload: ArchitectProposalAuthenticityPayload,
    proposal_admission: Mapping[str, Any],
    determination: Mapping[str, Any],
    queue_candidate: Mapping[str, Any],
    authority_profile: Mapping[str, Any],
) -> ArchitectProposalAuthenticityPayload:
    profile = _mapping(authority_profile)
    return build_architect_proposal_authenticity_payload(
        proposal_admission=_mapping(proposal_admission),
        determination=_mapping(determination),
        queue_candidate=_mapping(queue_candidate),
        requester_principal_id=_required_text(profile, "principal_id"),
        reddog_id=_required_text(profile, "reddog_id"),
        signer_public_key=_required_text(profile, "reddog_public_key"),
        key_epoch=_required_text(profile, "key_epoch"),
        consensus_receipt_digest=_required_text(
            profile, "consensus_receipt_digest"
        ),
        authority_profile_source_receipt_id=_required_text(
            profile, "authority_profile_source_receipt_id"
        ),
        nonce=payload.nonce,
        issued_at=payload.issued_at,
        expires_at=payload.expires_at,
    )


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _required_text(value: Mapping[str, Any], key: str) -> str:
    text = str(value.get(key) or "").strip()
    if not text:
        raise ValueError(f"architect_proposal_authority_{key}_missing")
    return text


def _digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = [
    "ArchitectProposalAuthorityBinding",
    "VERIFIED_ARCHITECT_PROPOSAL_AUTHORITY_SCHEMA_VERSION",
    "verify_architect_proposal_promotion_authority",
]
