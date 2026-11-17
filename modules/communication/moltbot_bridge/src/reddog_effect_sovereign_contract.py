"""Effect consent evidence shapes, distinct parent policy restriction retained."""

from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class EffectSovereignAuthorizationEvidence:
    """Supplied assertions only; construction does not authenticate consent."""
    authorization_digest: str
    parent_authorization: SovereignAuthorizationEvidence
    parent_authority_request_digest: str
    target_signing_request_digest: str
    effect_request_digest: str
    consensus_policy_digest: str
    issued_at: int
    expires_at: int


@dataclass(frozen=True, slots=True)
class ParentBoundEffectSovereignAuthorizationEvidence(EffectSovereignAuthorizationEvidence):
    """Explicit v2 effect data preserving the authenticated parent's policy restriction."""


def _effect_sovereign_shape_valid(evidence, now) -> bool:
    from .reddog_elevated_authority_consensus_effect_context import _bounded_text
    from .reddog_signer_optional_authority_bindings import is_sha256_digest

    from .reddog_parent_consent_contract import ParentConsentEvidence
    from .reddog_elevated_authority_consensus_policy import SovereignAuthorizationEvidence
    if type(evidence) not in {EffectSovereignAuthorizationEvidence, ParentBoundEffectSovereignAuthorizationEvidence}:
        return False
    parent = evidence.parent_authorization
    modern = type(evidence) is ParentBoundEffectSovereignAuthorizationEvidence
    if type(parent) is not (ParentConsentEvidence if modern else SovereignAuthorizationEvidence):
        return False
    if modern and parent.consensus_policy_digest != evidence.consensus_policy_digest:
        return False
    times = (now, evidence.issued_at, evidence.expires_at, parent.expires_at)
    if not all(type(value) is int for value in times) or now < 0 or parent.expires_at <= 0:
        return False
    digests = (evidence.authorization_digest, evidence.parent_authority_request_digest,
               evidence.target_signing_request_digest, evidence.effect_request_digest,
               evidence.consensus_policy_digest, parent.authorization_digest, parent.authority_request_digest)
    names = ("principal_id", "principal_provider", "principal_public_key", "reddog_id",
             "reddog_public_key", "repo_full_name", "foundup_id", "work_order_id", "key_epoch")
    return (all(type(value) is str and is_sha256_digest(value) for value in digests)
            and all(_bounded_text(getattr(parent, name)) for name in names))


def _effect_sovereign_lifetime_matches(evidence, context, parent, target_payload, now) -> bool:
    return (0 <= evidence.issued_at <= context.issued_at <= now < context.expires_at
            <= evidence.expires_at <= min(evidence.parent_authorization.expires_at,
                parent.identity_expires_at, parent.work_authority_expires_at, target_payload['expires_at']))
