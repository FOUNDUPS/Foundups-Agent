"""Per-use current-generation principal authority resolution for signer E0."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    PrincipalAuthorityRecord,
)
from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_principal_authority import (
    load_current_generation_principal_authority_resolver,
)


@dataclass(frozen=True)
class ManifestBoundCurrentPrincipalAuthorityResolver:
    """Lease and re-read the current signed generation for every resolution."""

    repo_root: Path
    boundary: Any
    clock: Callable[[], float] = field(default=time.time, repr=False)

    def resolve(
        self, principal_id: str, principal_provider: str
    ) -> PrincipalAuthorityRecord | None:
        return self._resolve("resolve", principal_id, principal_provider)

    def resolve_unique(self, principal_id: str) -> PrincipalAuthorityRecord | None:
        return self._resolve("resolve_unique", principal_id)

    def _resolve(self, method: str, *args: str) -> PrincipalAuthorityRecord | None:
        capability = self.boundary.select({}, now_epoch=int(self.clock()))
        with self.boundary._lease_current(capability) as selection:
            resolver = load_current_generation_principal_authority_resolver(
                repo_root=self.repo_root.resolve(), selection=selection
            )
            return getattr(resolver, method)(*args)


class _LeasedReviewerKeys:
    """Private projection usable only until its enclosing verification ends."""

    def __init__(self, records):
        self._records = dict(records)

    def resolve(self, principal_id, principal_provider):
        return self._records.get((principal_id, principal_provider))

    def close(self):
        self._records.clear()


def _project_reviewer_keys(*, authority, designation, records, policy, selection, parent, now):
    from .reddog_reviewer_designation_contract import (
        reviewer_designation_authority_digest, reviewer_designation_signing_input,
        validate_reviewer_designation, validate_reviewer_designation_authority,
    )
    from .reddog_ed25519_signature_verifier_backend import Ed25519SignatureVerifier
    from .reddog_elevated_authority_consensus_policy import elevated_consensus_policy_valid

    authority = validate_reviewer_designation_authority(authority)
    designation = validate_reviewer_designation(designation)
    shared = ("privilege", "issuer_principal_id", "issuer_principal_provider",
              "issuer_key_epoch", "repo_full_name", "foundup_id", "policy_digest",
              "decision_schema_version")
    if any(designation[name] != authority[name] for name in shared):
        raise ValueError("reviewer_designation_authority_mismatch")
    if (designation["owner_authority_digest"] != reviewer_designation_authority_digest(authority)
            or not elevated_consensus_policy_valid(policy)
            or authority["policy_digest"] != policy.policy_digest
            or authority["repo_full_name"] != parent.repo_full_name
            or authority["foundup_id"] != parent.foundup_id):
        raise ValueError("reviewer_designation_scope_mismatch")
    expiry = _reviewer_lifetime(authority, designation, selection, now)
    if Ed25519SignatureVerifier().verify(
        authority["issuer_public_key"], reviewer_designation_signing_input(designation),
        designation["signature"],
    ) is not True:
        raise ValueError("reviewer_designation_signature_invalid")
    projected = {}
    for entry in designation["reviewers"]:
        key = _project_reviewer_entry(entry, records, policy, authority, now, expiry)
        if key is not None:
            projected[(entry["principal_id"], entry["principal_provider"])] = key
    return _LeasedReviewerKeys(projected)


def _reviewer_lifetime(authority, designation, selection, now):
    if type(now) is not int or any(
        not item["issued_at"] <= now < item["expires_at"]
        for item in (authority, designation)
    ):
        raise ValueError("reviewer_designation_expired")
    expiries = [authority["expires_at"], designation["expires_at"],
                selection["manifest_expires_at"], selection["selection_expires_at"]]
    if any(type(value) is not int or value <= now for value in expiries):
        raise ValueError("reviewer_selection_expired")
    issued = selection["selection_issued_at"]
    if type(issued) is not int or not 0 <= issued <= now:
        raise ValueError("reviewer_selection_future")
    return min(expiries)


def _project_reviewer_entry(entry, records, policy, authority, now, expiry):
    from .reddog_elevated_authority_consensus_policy import ReviewerKeyAuthority

    pair = (entry["principal_id"], entry["principal_provider"])
    roles = {role for principal, provider, role in policy.reviewer_membership
             if (principal, provider) == pair}
    record = records.get(f"{pair[1]}|{pair[0]}")
    if (not roles or not roles.issubset(entry["authorized_roles"])
            or record is None or record.principal_id != pair[0]
            or record.principal_provider != pair[1]
            or record.principal_public_key != entry["public_key"]
            or authority["repo_full_name"] not in record.repo_scope
            or authority["foundup_id"] not in record.foundup_scope
            or not entry["issued_at"] <= now < entry["expires_at"]):
        return None
    return ReviewerKeyAuthority(entry["public_key"], entry["key_epoch"],
                                min(expiry, entry["expires_at"]))


from .reddog_current_effect_consent_verification import resolve_current_effect_sovereign_authorization


__all__ = ["ManifestBoundCurrentPrincipalAuthorityResolver", "resolve_current_effect_sovereign_authorization"]
