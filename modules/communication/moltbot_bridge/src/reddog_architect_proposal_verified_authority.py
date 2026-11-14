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
from datetime import datetime, timezone
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
from modules.communication.moltbot_bridge.src.reddog_operational_memex_supply_receipt import (
    OperationalMemexSupplyReceipt,
    rehydrate_operational_memex_supply_receipt,
)


VERIFIED_ARCHITECT_PROPOSAL_AUTHORITY_SCHEMA_VERSION = (
    "verified_reddog_architect_proposal_promotion_authority.v3"
)
RETAINED_PROPOSAL_INPUTS_SCHEMA = "reddog_proposal_verification_inputs.v1"
MAX_RETAINED_PROPOSAL_BYTES = 262144
_RETAINED_MEMBERS = frozenset({
    "attestation", "original_authority_profile", "proposal_admission",
    "determination", "queue_candidate", "memex_supply_receipt",
})


def snapshot_retained_architect_proposal_inputs(value: Any) -> dict[str, Any]:
    """Detach bounded public evidence. Structural validity is not authenticity."""
    from modules.communication.moltbot_bridge.src.reddog_authority_profile_rehydration import (
        rehydrate_authority_profile_source,
    )
    from modules.communication.moltbot_bridge.src.reddog_authority_profile_safety import (
        authority_profile_secret_field_paths,
    )
    _check_retained_json(value)
    if (type(value) is not dict or set(value) != _RETAINED_MEMBERS | {"schema_version"}
            or value.get("schema_version") != RETAINED_PROPOSAL_INPUTS_SCHEMA
            or any(type(value[key]) is not dict for key in _RETAINED_MEMBERS)):
        raise ValueError("retained_proposal_fields_invalid")
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True, allow_nan=False)
    if len(encoded.encode("utf-8")) > MAX_RETAINED_PROPOSAL_BYTES:
        raise ValueError("retained_proposal_size_exceeded")
    bundle = json.loads(encoded)
    if authority_profile_secret_field_paths(bundle):
        raise ValueError("retained_proposal_secret_field")
    profile = rehydrate_authority_profile_source(bundle["original_authority_profile"])
    _verify_authority_profile_receipt(profile)
    attestation = bundle["attestation"]
    if type(attestation.get("signature")) is not str or not attestation["signature"]:
        raise ValueError("retained_proposal_signature_missing")
    payload = rehydrate_architect_proposal_authenticity_payload(
        {key: item for key, item in attestation.items() if key != "signature"},
    )
    memex = _retained_memex(bundle, payload.issued_at)
    expected = _rebuild_payload(
        payload=payload, proposal_admission=bundle["proposal_admission"],
        determination=bundle["determination"], queue_candidate=bundle["queue_candidate"],
        memex_supply_receipt=memex, authority_profile=profile,
    )
    if payload != expected:
        raise ValueError("retained_proposal_payload_mismatch")
    return bundle


def _check_retained_json(value: Any) -> None:
    pending, count = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        count += 1
        if depth > 20 or count > 8192:
            raise ValueError("retained_proposal_structure_exceeded")
        if type(item) is dict:
            if len(item) > 8192 or any(type(key) is not str for key in item):
                raise ValueError("retained_proposal_mapping_invalid")
            if "proposal_verification_inputs" in item:
                raise ValueError("retained_proposal_nested_bundle")
            pending.extend((child, depth + 1) for child in item.values())
        elif type(item) in (list, tuple):
            if len(item) > 8192:
                raise ValueError("retained_proposal_structure_exceeded")
            pending.extend((child, depth + 1) for child in item)
        elif item is not None and type(item) not in (str, int, float, bool):
            raise ValueError("retained_proposal_not_plain_json")


def _retained_memex(bundle: Mapping[str, Any], now_epoch: int):
    if type(now_epoch) is not int:
        raise ValueError("retained_proposal_time_invalid")
    profile, proposal = bundle["original_authority_profile"], bundle["proposal_admission"]
    determination = bundle["determination"]
    return rehydrate_operational_memex_supply_receipt(
        bundle["memex_supply_receipt"],
        expected_foundup_id=profile["foundup_id"],
        expected_principal_id=profile["principal_id"],
        expected_snapshot_receipt_id=determination["snapshot_receipt_id"],
        expected_snapshot_content_digest=determination["snapshot_content_digest"],
        expected_holoindex_generation_id=proposal["holoindex_generation_id"],
        expected_source_revision=proposal["work_state_revision"],
        now_iso=datetime.fromtimestamp(now_epoch, timezone.utc).isoformat(),
    )


def verify_retained_architect_proposal_authority(
    value: Any, *, signer_runtime_config: SignerSocketServiceRuntimeWiringConfig,
    principal_key_resolver: PrincipalKeyResolver, now_epoch: int,
    revoked_key_epochs: frozenset[str] = frozenset(),
) -> ArchitectProposalAuthorityBinding:
    """Reverify at caller-supplied time/trust; this does not grant live authority."""
    bundle = snapshot_retained_architect_proposal_inputs(value)
    return verify_architect_proposal_promotion_authority(
        attestation=bundle["attestation"],
        proposal_admission=bundle["proposal_admission"],
        determination=bundle["determination"], queue_candidate=bundle["queue_candidate"],
        memex_supply_receipt=_retained_memex(bundle, now_epoch),
        authority_profile=bundle["original_authority_profile"],
        signer_runtime_config=signer_runtime_config,
        principal_key_resolver=principal_key_resolver, now_epoch=now_epoch,
        revoked_key_epochs=revoked_key_epochs,
    )


def verify_retained_proposal_work_binding(
    value, *, work_order, work_authority, principal_identity, signer_identity,
    signer_runtime_config, principal_key_resolver, now_epoch,
    revoked_key_epochs=frozenset(),
):
    """Bind verified retained evidence to exact work; caller owns current trust."""
    from .reddog_work_order_binding import canonical_full_work_order_digest
    from .reddog_operational_memex_supply_freshness import DEFAULT_MAX_AGE_SECONDS
    bundle = snapshot_retained_architect_proposal_inputs(value)
    work = json.loads(json.dumps(work_order, allow_nan=False))
    authority = json.loads(json.dumps(work_authority, allow_nan=False))
    work_digest = canonical_full_work_order_digest(work)
    if authority.get("work_order_digest") != work_digest:
        raise ValueError("retained_proposal_work_not_authorized")
    verified = verify_retained_architect_proposal_authority(bundle,
        signer_runtime_config=signer_runtime_config, principal_key_resolver=principal_key_resolver,
        now_epoch=now_epoch, revoked_key_epochs=revoked_key_epochs)
    _verify_retained_work_fields(bundle, work, authority, principal_identity, signer_identity, verified)
    authorization = signer_runtime_config.proposal_policy_authorization
    authorization = authorization if isinstance(authorization, Mapping) else authorization.to_dict()
    memex = _retained_memex(bundle, now_epoch)
    deadline = min(bundle["attestation"]["expires_at"], authorization["expires_at"],
        int(datetime.fromisoformat(memex.policy_expires_at.replace("Z", "+00:00")).timestamp()),
        int(datetime.fromisoformat(memex.policy_issued_at.replace("Z", "+00:00")).timestamp()) + DEFAULT_MAX_AGE_SECONDS)
    if now_epoch >= deadline:
        raise ValueError("retained_proposal_work_evidence_expired")
    return dict(memex_work_order_digest=work_digest, memex_evidence_digest=_digest(bundle),
                memex_valid_until=deadline)


def _verify_retained_work_fields(bundle, work, authority, identity, signer, verified):
    profile = bundle["original_authority_profile"]
    if (signer.get("signer_profile_id") != "reddog-work-authority"
            or signer.get("signer_public_key") != verified.reddog_public_key
            or signer.get("key_epoch") != verified.key_epoch
            or authority.get("principal_id") != verified.principal_id
            or any(identity.get(key) != getattr(verified, key) for key in
                   ("principal_id", "principal_provider", "principal_public_key"))):
        raise ValueError("retained_proposal_current_signer_mismatch")
    common = dict(repo_full_name=profile["repo_full_name"], foundup_id=profile["foundup_id"],
        memex_supply_receipt_id=verified.memex_supply_receipt_id, memex_supply_digest=verified.memex_supply_digest)
    expected = dict(common, proposal_authenticity_attestation_id=verified.attestation_id,
        proposal_authenticity_attestation_digest=verified.attestation_digest,
        proposal_policy_authorization_id=verified.policy_authorization_id,
        proposal_policy_authorization_digest=verified.policy_authorization_digest,
        proposal_signer_runtime_context_digest=verified.signer_runtime_context_digest)
    if (any(work.get(key) != item for key, item in expected.items())
            or any(authority.get(key) != item for key, item in common.items())):
        raise ValueError("retained_proposal_signed_work_binding_mismatch")


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
    memex_supply_receipt_id: str
    memex_supply_digest: str


def verify_architect_proposal_promotion_authority(
    *,
    attestation: Mapping[str, Any],
    proposal_admission: Mapping[str, Any],
    determination: Mapping[str, Any],
    queue_candidate: Mapping[str, Any],
    memex_supply_receipt: OperationalMemexSupplyReceipt,
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
        memex_supply_receipt=memex_supply_receipt,
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
        memex_supply_receipt_id=verified_attestation.payload.memex_supply_receipt_id,
        memex_supply_digest=verified_attestation.payload.memex_supply_digest,
    )


def _verification_inputs(
    *,
    attestation: Mapping[str, Any],
    proposal_admission: Mapping[str, Any],
    determination: Mapping[str, Any],
    queue_candidate: Mapping[str, Any],
    memex_supply_receipt: OperationalMemexSupplyReceipt,
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
        memex_supply_receipt=memex_supply_receipt,
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
    memex_supply_receipt: OperationalMemexSupplyReceipt,
    authority_profile: Mapping[str, Any],
) -> ArchitectProposalAuthenticityPayload:
    profile = _mapping(authority_profile)
    return build_architect_proposal_authenticity_payload(
        proposal_admission=_mapping(proposal_admission),
        determination=_mapping(determination),
        queue_candidate=_mapping(queue_candidate),
        memex_supply_receipt=memex_supply_receipt,
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
