"""Root-owned current-generation selection for signer E0 admission."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
)

from modules.communication.moltbot_bridge.src.reddog_signer_system_service_manifest_selection_loader import (
    load_system_service_manifest_selection,
)

from .reddog_signer_owner_e0_admission_contract import (
    OwnerControlledE0ConsumptionReceipt,
)
from .reddog_signer_owner_e0_admission_validation import (
    load_selected_signer_config,
    require_policy_authorities,
    require_policy_config_binding,
    require_policy_runtime_paths,
    require_policy_selection_binding,
)
from .reddog_signer_owner_e0_capability_state import (
    freeze_owner_e0_policy,
    thaw_owner_e0_policy,
)
from .reddog_signer_owner_e0_policy_contract import (
    signer_owner_e0_authority_binding_digest,
    validated_signer_owner_e0_policy,
)
from .reddog_signer_owner_e0_principal_authority import (
    load_current_generation_principal_key_resolver,
)


def load_owner_e0_current_selection(
    *, owner_config_path: Path | str, repo_root: Path
) -> Mapping[str, Any]:
    capability, boundary = load_system_service_manifest_selection(
        owner_config_path=owner_config_path,
        repo_root=repo_root,
    )
    selected = boundary.consume(capability)
    if Path(str(selected.get("repo_root") or "")).resolve() != repo_root.resolve():
        raise ValueError("e0_selection_repo_root_mismatch")
    return selected


def validate_owner_e0_current_admission(
    *,
    owner_config_path: Path | str,
    repo_root: Path,
    policy: Mapping[str, Any],
) -> tuple[OwnerControlledE0ConsumptionReceipt, Mapping[str, Any]]:
    """Validate E0 inputs under the private current-generation lease."""

    capability, boundary = load_system_service_manifest_selection(
        owner_config_path=owner_config_path,
        repo_root=repo_root,
    )
    with boundary._lease_current(capability) as selected:
        if Path(str(selected.get("repo_root") or "")).resolve() != repo_root.resolve():
            raise ValueError("e0_selection_repo_root_mismatch")
        return _validate_selected(repo_root.resolve(), selected, policy)


def _validate_selected(
    repo_root: Path,
    selection: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> tuple[OwnerControlledE0ConsumptionReceipt, Mapping[str, Any]]:
    checked = validated_signer_owner_e0_policy(
        thaw_owner_e0_policy(policy), now_epoch=int(time.time())
    )
    require_policy_selection_binding(checked, selection)
    config = load_selected_signer_config(
        repo_root=repo_root,
        selection=selection,
        expected_authority_binding_digest=(
            signer_owner_e0_authority_binding_digest(checked)
        ),
    )
    profile = require_policy_config_binding(checked, config)
    resolver = load_current_generation_principal_key_resolver(
        repo_root=repo_root, selection=selection
    )
    require_policy_authorities(
        checked,
        principal_key_resolver=resolver,
        signature_verifier=Ed25519SignatureVerifier(),
    )
    require_policy_runtime_paths(
        checked,
        repo_root=repo_root,
        signer_runtime_root=Path(config.signer_runtime_root).resolve(),
    )
    _require_consensus_policy(checked)
    return _receipt(checked, selection, profile), freeze_owner_e0_policy(checked)


def _receipt(
    policy: Mapping[str, Any], selection: Mapping[str, Any], profile: Any
) -> OwnerControlledE0ConsumptionReceipt:
    return OwnerControlledE0ConsumptionReceipt(
        policy_id=str(policy["policy_id"]),
        manifest_id=str(selection["manifest_id"]),
        artifact_generation_digest=str(selection["artifact_generation_digest"]),
        config_digest=str(selection["config_digest"]),
        target_signer_agent_id=profile.signer_agent_id,
        target_signer_profile_id=profile.signer_profile_id,
    )


def _require_consensus_policy(policy: Mapping[str, Any]) -> None:
    tiers = set(policy["allowed_authority_tiers"])
    consensus = set(policy["consensus_required_tiers"])
    if tiers.intersection({"HIGH", "SOVEREIGN"}) - consensus:
        raise ValueError("signer_owner_e0_consensus_policy_invalid")


__all__ = [
    "load_owner_e0_current_selection",
    "validate_owner_e0_current_admission",
]
