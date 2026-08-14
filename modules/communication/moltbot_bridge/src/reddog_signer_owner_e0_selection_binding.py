"""Current-generation and role binding for owner E0 admission."""

from __future__ import annotations

from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    constant_time_compare,
)


def require_policy_selection_binding(
    policy: Mapping[str, Any], selection: Mapping[str, Any]
) -> None:
    """Bind policy to one selection with an independent generation key."""

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
    generation_key = selection.get("generation_public_key")
    role_keys = {
        str(policy["grant_authority_public_key"]),
        str(policy["revocation_authority_public_key"]),
        str(policy["target_signer_public_key"]),
    }
    if (
        type(generation_key) is not str
        or not generation_key
        or not generation_key.isascii()
        or any(
            constant_time_compare(generation_key, candidate)
            for candidate in role_keys
        )
    ):
        raise ValueError("e0_generation_authority_not_independent")


__all__ = ["require_policy_selection_binding"]
