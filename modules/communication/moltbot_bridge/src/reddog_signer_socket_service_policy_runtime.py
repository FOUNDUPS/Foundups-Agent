"""Bounded policy and anchor composition for the isolated signer runtime."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    PrincipalAuthorityResolver,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_signing import (
    MIN_SOCKET_REQUEST_BYTES,
    ConversationScopeSignerPolicy,
)
from modules.communication.moltbot_bridge.src.reddog_signer_conversation_scope_anchor import (
    AtomicSignerConversationScopeAnchorStore,
    ConversationScopeAnchorStore,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)


FAIL_CONVERSATION_AUTH = "FAIL_SIGNER_RUNTIME_CONVERSATION_AUTH_INVALID"


@dataclass(frozen=True)
class ConversationScopeRuntimeBinding:
    policy: ConversationScopeSignerPolicy
    resolver: PrincipalAuthorityResolver
    anchor_store: ConversationScopeAnchorStore


def conversation_scope_config_reasons(
    config: Any, profile_public_keys: set[str]
) -> tuple[str, ...]:
    policy = _conversation_policy(config.conversation_scope_signer_policy)
    if config.conversation_scope_signer_policy is not None and policy is None:
        return (FAIL_CONVERSATION_AUTH,)
    if (config.conversation_scope_anchor_path is None) != (policy is None):
        return (FAIL_CONVERSATION_AUTH,)
    if policy is None:
        return ()
    if (
        policy.signer_public_key not in profile_public_keys
        or int(config.max_request_bytes) < MIN_SOCKET_REQUEST_BYTES
    ):
        return (FAIL_CONVERSATION_AUTH,)
    return ()


def build_conversation_scope_runtime_binding(
    config: Any, resolver: PrincipalAuthorityResolver | None
) -> tuple[ConversationScopeRuntimeBinding | None, tuple[str, ...]]:
    reasons = conversation_scope_config_reasons(config, {
        _profile_public_key(item) for item in _profiles(config)
    })
    policy = _conversation_policy(config.conversation_scope_signer_policy)
    if reasons or policy is None:
        return None, reasons
    if resolver is None:
        return None, (FAIL_CONVERSATION_AUTH,)
    try:
        repo = Path(config.repo_root).resolve()
        signer = validate_runtime_root_path(
            config.signer_runtime_root, repo_root=repo
        )
        path = validate_runtime_artifact_path(
            config.conversation_scope_anchor_path,
            repo_root=repo,
            allowed_root=signer,
        )
        if path.parent != signer:
            raise ValueError("conversation_anchor_parent")
        anchor = AtomicSignerConversationScopeAnchorStore(
            path, runtime_root=signer, repo_root=repo
        )
    except Exception:
        return None, (FAIL_CONVERSATION_AUTH,)
    return ConversationScopeRuntimeBinding(policy, resolver, anchor), ()


def conversation_scope_security_context(
    config: Any, repo: Path, signer: Path
) -> Mapping[str, Any]:
    policy = _conversation_policy(config.conversation_scope_signer_policy)
    if policy is None:
        return {"anchor_path": None, "policy": None}
    path = validate_runtime_artifact_path(
        config.conversation_scope_anchor_path,
        repo_root=repo,
        allowed_root=signer,
    )
    if path.parent != signer:
        raise ValueError("conversation_scope_security_context_invalid")
    return {"anchor_path": str(path), "policy": asdict(policy)}


def bind_conversation_scope_backend(
    key_result: Any, profile: Any, binding: ConversationScopeRuntimeBinding | None
) -> Any:
    if (
        binding is None
        or key_result.backend is None
        or _profile_public_key(profile) != binding.policy.signer_public_key
    ):
        return key_result
    return replace(
        key_result,
        backend=replace(
            key_result.backend,
            conversation_scope_signer_policy=binding.policy,
            conversation_scope_principal_resolver=binding.resolver,
            conversation_scope_anchor_store=binding.anchor_store,
        ),
    )


def _conversation_policy(value: Any) -> ConversationScopeSignerPolicy | None:
    policy = _policy(value, ConversationScopeSignerPolicy)
    if policy is None:
        return None
    values = (
        policy.issuer_principal_id, policy.issuer_principal_provider,
        policy.repo_full_name, policy.signer_public_key, policy.key_epoch,
    )
    return policy if (
        all(_ascii(item) for item in values)
        and "/" in policy.repo_full_name
        and 0 < policy.max_scope_ttl_seconds <= 86400
    ) else None


def _policy(value: Any, kind: type) -> Any:
    if isinstance(value, kind):
        return value
    if isinstance(value, Mapping):
        try:
            return kind(**dict(value))
        except (TypeError, ValueError):
            return None
    return None


def _profiles(config: Any) -> tuple[Any, ...]:
    return tuple(config.key_provider_profiles) or (
        (config.key_provider_profile,) if config.key_provider_profile else ()
    )


def _profile_public_key(profile: Any) -> str:
    if isinstance(profile, Mapping):
        return str(profile.get("expected_public_key") or "")
    return str(getattr(profile, "expected_public_key", "") or "")


def _ascii(value: Any) -> bool:
    return bool(isinstance(value, str) and value and value.isascii())


__all__ = [
    "ConversationScopeRuntimeBinding",
    "FAIL_CONVERSATION_AUTH",
    "bind_conversation_scope_backend",
    "build_conversation_scope_runtime_binding",
    "conversation_scope_config_reasons",
    "conversation_scope_security_context",
]
