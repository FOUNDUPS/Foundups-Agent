"""Bind root verified-outcome authority to one signer runtime and policy."""

from __future__ import annotations

import hmac
from typing import Mapping

from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_signing import (
    VerifiedOutcomeSigningAuthority,
    VerifiedOutcomeSignerPolicy,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority import (
    root_verified_outcome_authority_bindings,
)
from modules.communication.moltbot_bridge.src.reddog_signer_mutual_peer_handshake import (
    SignerPeerInstanceBinding,
)


def verified_outcome_authority_matches_runtime(
    policy: VerifiedOutcomeSignerPolicy | None,
    authority: VerifiedOutcomeSigningAuthority | None,
    *,
    expected_owner_config_id: str | None,
    signer_peer_instance_binding: SignerPeerInstanceBinding | None,
) -> bool:
    """Require exact owner, signer instance, key, and policy bindings."""

    if policy is None:
        return authority is None
    if authority is None:
        return False
    try:
        bindings = root_verified_outcome_authority_bindings(authority)
    except (TypeError, ValueError):
        return False
    return bool(
        expected_owner_config_id
        and signer_peer_instance_binding
        and _same(bindings, "owner_config_id", expected_owner_config_id)
        and _instance_matches(bindings, signer_peer_instance_binding)
        and _policy_matches(bindings, policy)
    )


def _instance_matches(
    bindings: Mapping[str, str], peer: SignerPeerInstanceBinding
) -> bool:
    expected = {
        "signer_run_packet_id": peer.run_packet_id,
        "signer_config_digest": peer.config_digest,
        "signer_session_id": peer.session_id,
        "signer_manifest_id": peer.manifest_id,
        "signer_artifact_generation_digest": peer.artifact_generation_digest,
    }
    return all(_same(bindings, field, value) for field, value in expected.items())


def _policy_matches(
    bindings: Mapping[str, str], policy: VerifiedOutcomeSignerPolicy
) -> bool:
    expected = {
        "signer_public_key": policy.signer_public_key,
        "signer_key_epoch": policy.key_epoch,
        "issuer_principal_id": policy.issuer_principal_id,
        "reddog_id": policy.reddog_id,
        "authority_tier": policy.authority_tier,
        "consensus_receipt_digest": policy.consensus_receipt_digest,
    }
    return all(_same(bindings, field, value) for field, value in expected.items())


def _same(bindings: Mapping[str, str], field: str, expected: str) -> bool:
    return hmac.compare_digest(str(bindings.get(field) or ""), str(expected))


__all__ = ["verified_outcome_authority_matches_runtime"]
