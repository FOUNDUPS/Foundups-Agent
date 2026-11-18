"""Load the exact E0 signer context for resident conversation state."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_conversation_scope_signing import (
    ConversationScopeSignerPolicy,
    ConversationScopeSigningContext,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_client import (
    build_reddog_isolated_signer_socket_client,
)
from modules.communication.moltbot_bridge.src.reddog_signer_current_generation_config_loader import (
    load_current_generation_signer_config,
)


class ConversationSessionSigningContextError(ValueError):
    """Stable failure raised when a required E0 signer is unavailable."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def load_conversation_session_signing_context(
    *,
    repo_root: Path,
    selection: Mapping[str, Any],
    serialized_credential: str,
    required: bool,
) -> tuple[ConversationScopeSigningContext | None, Path | None]:
    """Return the current exact signer context or fail closed when required."""

    try:
        config = load_current_generation_signer_config(
            repo_root=repo_root, selection=selection
        )
    except Exception as exc:
        if not required:
            return None, None
        raise ConversationSessionSigningContextError(
            "conversation_session_signer_config_unavailable"
        ) from exc
    policy = config.conversation_scope_signer_policy
    if isinstance(policy, Mapping):
        policy = ConversationScopeSignerPolicy(**dict(policy))
    if not isinstance(policy, ConversationScopeSignerPolicy):
        return _unavailable(
            required, "conversation_session_signer_policy_unavailable"
        )
    if not _has_exact_signer_profile(config=config, policy=policy):
        return _unavailable(
            required, "conversation_session_signer_profile_unavailable"
        )
    built = build_reddog_isolated_signer_socket_client(
        repo_root=repo_root,
        socket_path=config.socket_path,
        timeout_s=min(float(config.timeout_s), 30.0),
        max_response_bytes=int(config.max_response_bytes),
    )
    if built.accepted is not True or built.client is None:
        return _unavailable(
            required, "conversation_session_signer_socket_unavailable"
        )
    return (
        ConversationScopeSigningContext(
            signer=built.client,
            signer_public_key=policy.signer_public_key,
            key_epoch=policy.key_epoch,
            serialized_session_credential=serialized_credential,
        ),
        Path(config.runtime_root).resolve(),
    )


def _unavailable(required: bool, reason: str) -> tuple[None, None]:
    if required:
        raise ConversationSessionSigningContextError(reason)
    return None, None


def _has_exact_signer_profile(
    *, config: Any, policy: ConversationScopeSignerPolicy
) -> bool:
    profiles = tuple(config.key_provider_profiles) or (
        (config.key_provider_profile,) if config.key_provider_profile else ()
    )
    matches = tuple(
        item
        for item in profiles
        if _profile_field(item, "expected_public_key") == policy.signer_public_key
        and _profile_field(item, "expected_key_epoch") == policy.key_epoch
    )
    return len(matches) == 1


def _profile_field(profile: Any, name: str) -> str:
    if isinstance(profile, Mapping):
        return str(profile.get(name) or "")
    return str(getattr(profile, name, "") or "")


__all__ = [
    "ConversationSessionSigningContextError",
    "load_conversation_session_signing_context",
]
