"""Validation helpers for owner-controlled E0 composition admission."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_signer_key_provider_dryrun import (
    PROVIDER_MODE_WSP71_PERMISSIONED,
    SignerKeyProviderProfile,
    validate_signer_key_provider_profile,
)
from modules.communication.moltbot_bridge.src.reddog_signer_current_generation_config_loader import (
    load_current_generation_signer_config_payload,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    PrincipalKeyResolver,
    SignatureVerifier,
    constant_time_compare,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)
from .reddog_signer_owner_e0_policy_contract import (
    canonical_signer_owner_e0_policy_input,
    signer_key_reference_digest,
)
from .reddog_signer_secret_grant_revocation_authority_binding import (
    revocation_authority_binding_from_policy,
)


def load_selected_signer_config(
    *,
    repo_root: Path,
    selection: Mapping[str, Any],
    expected_authority_binding_digest: str,
) -> Any:
    payload, config = load_current_generation_signer_config_payload(
        repo_root=repo_root, selection=selection
    )
    if not constant_time_compare(
        str(payload.get("owner_e0_authority_binding_digest") or ""),
        expected_authority_binding_digest,
    ):
        raise ValueError("e0_policy_authority_binding_mismatch")
    return config


def require_policy_selection_binding(
    policy: Mapping[str, Any], selection: Mapping[str, Any]
) -> None:
    bindings = {
        "owner_config_id": "owner_config_id",
        "manifest_id": "manifest_id",
        "artifact_generation_digest": "artifact_generation_digest",
        "config_digest": "config_digest",
        "generation": "generation",
        "generation_revision": "generation_revision",
    }
    if any(policy[left] != selection[right] for left, right in bindings.items()):
        raise ValueError("e0_policy_generation_binding_mismatch")
def require_policy_authorities(
    policy: Mapping[str, Any],
    *,
    principal_key_resolver: PrincipalKeyResolver,
    signature_verifier: SignatureVerifier,
) -> None:
    authorities: list[tuple[str, str]] = []
    for prefix in ("grant_authority", "revocation_authority"):
        principal = str(policy[f"{prefix}_principal_id"])
        provider = str(policy[f"{prefix}_principal_provider"])
        public_key = str(policy[f"{prefix}_public_key"])
        try:
            trusted = principal_key_resolver.resolve(principal, provider)
        except Exception:
            trusted = None
        if not isinstance(trusted, str) or not constant_time_compare(trusted, public_key):
            raise ValueError("e0_policy_authority_untrusted")
        if constant_time_compare(public_key, str(policy["target_signer_public_key"])):
            raise ValueError("e0_policy_self_authority_rejected")
        authorities.append((principal, public_key))
    grant_authority, revocation_authority = authorities
    if (
        grant_authority[0] == revocation_authority[0]
        or constant_time_compare(grant_authority[1], revocation_authority[1])
    ):
        raise ValueError("e0_policy_authorities_not_independent")
    requester = str(policy["grant_requester_principal_id"])
    if requester in {
        grant_authority[0],
        revocation_authority[0],
        str(policy["target_signer_agent_id"]),
    }:
        raise ValueError("e0_policy_requester_not_independent")
    try:
        verified = signature_verifier.verify(
            str(policy["grant_authority_public_key"]),
            canonical_signer_owner_e0_policy_input(policy),
            str(policy["signature"]),
        ) is True
    except Exception:
        verified = False
    if not verified:
        raise ValueError("e0_policy_signature_invalid")
def require_policy_config_binding(policy: Mapping[str, Any], config: Any) -> Any:
    if (
        config.provider_mode != PROVIDER_MODE_WSP71_PERMISSIONED
        or config.allow_test_only_key_material is not False
        or config.permission_snapshot_fresh is not True
    ):
        raise ValueError("e0_config_not_production")
    profiles = _profiles(config)
    matches = [
        item for item in profiles
        if item.signer_agent_id == policy["target_signer_agent_id"]
        and item.signer_profile_id == policy["target_signer_profile_id"]
    ]
    if len(matches) != 1:
        raise ValueError("e0_target_profile_invalid")
    profile = matches[0]
    expected = (
        (profile.expected_public_key, policy["target_signer_public_key"]),
        (profile.expected_key_fingerprint, policy["target_signer_key_fingerprint"]),
        (profile.expected_key_epoch, policy["target_signer_key_epoch"]),
        (policy["target_signer_generation_id"], policy["artifact_generation_digest"]),
        (profile.permission_snapshot_digest, policy["permission_snapshot_digest"]),
        (
            signer_key_reference_digest(profile.signing_key_ref),
            policy["signing_key_ref_hash"],
        ),
        (
            signer_key_reference_digest(profile.audit_mac_key_ref),
            policy["audit_mac_key_ref_hash"],
        ),
    )
    if any(not constant_time_compare(str(left), str(right)) for left, right in expected):
        raise ValueError("e0_target_profile_binding_mismatch")
    if not constant_time_compare(
        public_key_fingerprint(profile.expected_public_key),
        str(policy["target_signer_key_fingerprint"]),
    ):
        raise ValueError("e0_target_profile_binding_mismatch")
    return profile


def require_policy_runtime_paths(
    policy: Mapping[str, Any], *, repo_root: Path, signer_runtime_root: Path
) -> None:
    roots: list[Path] = []
    for prefix in ("replay", "revocation"):
        root = validate_runtime_root_path(policy[f"{prefix}_root"], repo_root=repo_root)
        path = validate_runtime_artifact_path(
            policy[f"{prefix}_path"], repo_root=repo_root, allowed_root=root
        )
        overlaps_signer_root = (
            root == signer_runtime_root
            or root in signer_runtime_root.parents
            or signer_runtime_root in root.parents
        )
        if path.parent != root or overlaps_signer_root:
            raise ValueError("e0_policy_runtime_path_invalid")
        roots.append(root)
    if roots[0] == roots[1] or roots[0] in roots[1].parents or roots[1] in roots[0].parents:
        raise ValueError("e0_policy_runtime_roots_not_disjoint")
    binding = revocation_authority_binding_from_policy(
        policy, repo_root=repo_root, signer_runtime_root=signer_runtime_root
    )
    if any(_paths_overlap(binding.witness_root, root) for root in roots):
        raise ValueError("e0_policy_runtime_roots_not_disjoint")


def _paths_overlap(left: str | Path, right: str | Path) -> bool:
    first, second = Path(left).resolve(), Path(right).resolve()
    return first == second or first in second.parents or second in first.parents


def _profiles(config: Any) -> tuple[SignerKeyProviderProfile, ...]:
    values = tuple(config.key_provider_profiles) or (config.key_provider_profile,)
    profiles: list[SignerKeyProviderProfile] = []
    for value in values:
        profile = value if type(value) is SignerKeyProviderProfile else SignerKeyProviderProfile(**dict(value))
        if validate_signer_key_provider_profile(profile):
            raise ValueError("e0_target_profile_invalid")
        profiles.append(profile)
    return tuple(profiles)


__all__ = [
    "load_selected_signer_config",
    "require_policy_authorities",
    "require_policy_config_binding",
    "require_policy_runtime_paths",
    "require_policy_selection_binding",
]
