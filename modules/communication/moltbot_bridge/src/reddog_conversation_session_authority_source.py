"""Lease principal-signed conversational identity from the current generation.

The serialized credential arrives over the one-shot stdin payload, is removed
before AgentDB/model use, and is verified with current-generation public
material. The generation lease stays held through resident-cycle admission.
This grants conversational identity only, never work authority.
"""

from __future__ import annotations

import configparser
import re
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterator, Mapping

from modules.communication.moltbot_bridge.src.reddog_conversation_scope_authentication import (
    authenticate_signed_conversation_scope,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_capability import (
    AuthenticatedConversationScopeCapability,
    PrincipalContextReadConversationScopeCapability,
    VerifiedConversationScopeAuthority,
    consume_conversation_scope_capability,
    conversation_scope_authority_view,
    discard_conversation_scope_capability,
    split_conversation_scope_capability,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_contract import (
    canonical_digest,
)
from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    PrincipalAuthorityResolver,
)
from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_current_selection import (
    lease_owner_e0_current_selection,
)
from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_principal_authority import (
    load_current_generation_principal_authority_resolver,
)
from modules.communication.moltbot_bridge.src.reddog_signer_current_generation_config_loader import (
    load_current_generation_signer_config,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_client import (
    build_reddog_isolated_signer_socket_client,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_signing import (
    ConversationScopeSignerPolicy,
    ConversationScopeSigningContext,
)
from modules.communication.moltbot_bridge.src.reddog_principal_memex_live_resident_source_supply import (
    PrincipalMemexSessionAuthorization,
    discard_principal_memex_live_resident_source,
    issue_principal_memex_session_authorization,
)


OWNER_CONFIG_ENV = "REDDOG_SIGNER_SYSTEM_SERVICE_OWNER_CONFIG_PATH"
AUTHORITY_RECEIPT_SCHEMA = "reddog_conversation_session_authority_receipt.v1"


class ConversationSessionAuthoritySourceError(ValueError):
    """Stable public failure without credential or filesystem detail."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class VerifiedResidentConversationSession:
    principal_id: str
    principal_provider: str
    foundup_scope: tuple[str, ...]
    repo_full_name: str
    principal_record_digest: str
    session_binding_digest: str
    current_generation_manifest_id: str
    authority_receipt: Mapping[str, Any]
    authority: VerifiedConversationScopeAuthority
    principal_memex_authorization: PrincipalMemexSessionAuthorization | None = field(
        default=None, repr=False, compare=False
    )


@contextmanager
def lease_current_generation_conversation_session(
    *,
    repo_root: Path,
    intent: Mapping[str, Any],
    grounding_receipt_id: str,
    serialized_credential: str,
    owner_config_path: str,
    now_epoch: int,
    include_principal_scope_capability: bool = False,
) -> Iterator[VerifiedResidentConversationSession]:
    """Hold current-generation authority through one resident admission."""

    requested_foundup, intent_id = _required_intent_binding(
        intent, grounding_receipt_id
    )
    repo_full_name = _canonical_repo_full_name(repo_root)
    binding = canonical_digest(
        {
            "intent_id": intent_id,
            "grounding_receipt_id": grounding_receipt_id,
            "source_surface": str(intent.get("source_surface") or ""),
        }
    )
    authority: VerifiedConversationScopeAuthority | None = None
    principal_authorization: PrincipalMemexSessionAuthorization | None = None
    with lease_owner_e0_current_selection(
        owner_config_path=owner_config_path, repo_root=repo_root
    ) as selection:
        session, authority, principal_authorization = _authenticate_and_consume(
            repo_root=repo_root,
            selection=selection,
            serialized_credential=serialized_credential,
            repo_full_name=repo_full_name,
            intent=intent,
            requested_foundup=requested_foundup,
            grounding_receipt_id=grounding_receipt_id,
            session_binding=binding,
            now_epoch=now_epoch,
            include_principal_scope_capability=include_principal_scope_capability,
        )
        try:
            yield session
        finally:
            if authority is not None:
                discard_conversation_scope_capability(authority)
            if principal_authorization is not None:
                discard_principal_memex_live_resident_source(principal_authorization)


def owner_config_from_environment(environment: Mapping[str, str]) -> str:
    value = str(environment.get(OWNER_CONFIG_ENV, "") or "").strip()
    if not value:
        raise ConversationSessionAuthoritySourceError(
            "conversation_session_authority_source_missing"
        )
    return value


def _authenticate_and_consume(
    *, repo_root: Path, selection: Mapping[str, Any], serialized_credential: str,
    repo_full_name: str, intent: Mapping[str, Any], requested_foundup: str,
    grounding_receipt_id: str, session_binding: str, now_epoch: int,
    include_principal_scope_capability: bool,
) -> tuple[
    VerifiedResidentConversationSession,
    VerifiedConversationScopeAuthority,
    PrincipalMemexSessionAuthorization | None,
]:
    capability, credential, resolver, signing_context, runtime_root = _authenticate_scope(
        repo_root=repo_root, selection=selection,
        serialized_credential=serialized_credential,
        repo_full_name=repo_full_name, session_binding=session_binding,
        now_epoch=now_epoch,
        require_signing_context=include_principal_scope_capability,
    )
    foundup_capability, principal_capability = _scope_capabilities(
        capability, include_principal_scope_capability
    )
    authority = consume_conversation_scope_capability(
        foundup_capability, active_foundup_id=requested_foundup,
        discussion_foundup_ids=(requested_foundup,), now_epoch=int(now_epoch),
    )
    try:
        session = _verified_session(
            authority=authority, credential=credential, intent=intent,
            selection=selection, grounding_receipt_id=grounding_receipt_id,
            principal_capability=principal_capability, principal_resolver=resolver,
            runtime_root=runtime_root,
        )
    except Exception:
        discard_conversation_scope_capability(authority)
        discard_conversation_scope_capability(principal_capability)
        raise
    return session, authority, session.principal_memex_authorization


def _scope_capabilities(
    capability: AuthenticatedConversationScopeCapability, include_principal: bool,
) -> tuple[Any, PrincipalContextReadConversationScopeCapability | None]:
    if not include_principal:
        return capability, None
    children = split_conversation_scope_capability(capability)
    if children is None:
        raise ConversationSessionAuthoritySourceError(
            "conversation_session_scope_delegation_failed"
        )
    return children


def _authenticate_scope(
    *, repo_root: Path, selection: Mapping[str, Any], serialized_credential: str,
    repo_full_name: str, session_binding: str, now_epoch: int,
    require_signing_context: bool,
) -> tuple[
    Any, Any, PrincipalAuthorityResolver, ConversationScopeSigningContext | None,
    Path | None,
]:
    try:
        resolver = load_current_generation_principal_authority_resolver(
            repo_root=repo_root, selection=selection
        )
        signing_context, runtime_root = _conversation_signing_context(
            repo_root=repo_root,
            selection=selection,
            serialized_credential=serialized_credential,
            required=require_signing_context,
        )
        authenticated = authenticate_signed_conversation_scope(
            serialized_credential=serialized_credential,
            transport="editor",
            session_binding=session_binding,
            expected_repo_full_name=repo_full_name,
            principal_resolver=resolver,
            now_epoch=int(now_epoch),
            record_signing_context=signing_context,
        )
    except Exception as exc:
        raise ConversationSessionAuthoritySourceError(
            "conversation_session_authority_verification_failed"
        ) from exc
    if authenticated is None:
        raise ConversationSessionAuthoritySourceError(
            "conversation_session_authority_verification_failed"
        )
    capability, credential = authenticated
    return capability, credential, resolver, signing_context, runtime_root


def _verified_session(
    *, authority: Any, credential: Any, intent: Mapping[str, Any],
    selection: Mapping[str, Any], grounding_receipt_id: str,
    principal_capability: PrincipalContextReadConversationScopeCapability | None,
    principal_resolver: PrincipalAuthorityResolver,
    runtime_root: Path | None,
) -> VerifiedResidentConversationSession:
    if authority is None:
        raise ConversationSessionAuthoritySourceError(
            "conversation_session_authority_scope_rejected"
        )
    view = conversation_scope_authority_view(authority)
    if not isinstance(view, Mapping):
        discard_conversation_scope_capability(authority)
        raise ConversationSessionAuthoritySourceError(
            "conversation_session_authority_scope_rejected"
        )
    if str(intent.get("principal_ref") or "").strip() != credential.principal_id:
        discard_conversation_scope_capability(authority)
        raise ConversationSessionAuthoritySourceError(
            "conversation_session_expected_binding_mismatch"
        )
    receipt = _authority_receipt(
        credential=credential,
        selection=selection,
        view=view,
        grounding_receipt_id=grounding_receipt_id,
        intent_id=str(intent["intent_id"]),
    )
    principal_authorization = _principal_authorization(
        principal_capability=principal_capability,
        principal_resolver=principal_resolver,
        credential=credential,
        intent=intent,
        selection=selection,
        grounding_receipt_id=grounding_receipt_id,
        view=view,
        runtime_root=runtime_root,
    )
    session = VerifiedResidentConversationSession(
        principal_id=credential.principal_id,
        principal_provider=credential.principal_provider,
        foundup_scope=credential.foundup_scope,
        repo_full_name=credential.repo_full_name,
        principal_record_digest=str(view["principal_record_digest"]),
        session_binding_digest=str(view["session_binding_digest"]),
        current_generation_manifest_id=str(selection.get("manifest_id") or ""),
        authority_receipt=MappingProxyType(receipt),
        authority=authority,
        principal_memex_authorization=principal_authorization,
    )
    return session


def _principal_authorization(
    *, principal_capability: Any, principal_resolver: PrincipalAuthorityResolver,
    credential: Any, intent: Mapping[str, Any], selection: Mapping[str, Any],
    grounding_receipt_id: str, view: Mapping[str, Any], runtime_root: Path | None,
) -> PrincipalMemexSessionAuthorization | None:
    if principal_capability is None:
        return None
    if runtime_root is None:
        raise ConversationSessionAuthoritySourceError(
            "conversation_session_signer_config_unavailable"
        )
    return issue_principal_memex_session_authorization(
        capability=principal_capability,
        principal_resolver=principal_resolver,
        repo_full_name=credential.repo_full_name,
        intent_id=str(intent["intent_id"]),
        grounding_receipt_id=grounding_receipt_id,
        session_binding_digest=str(view["session_binding_digest"]),
        generation_manifest_id=str(selection.get("manifest_id") or ""),
        artifact_generation_digest=str(
            selection.get("artifact_generation_digest") or ""
        ),
        runtime_root=runtime_root,
    )


def _conversation_signing_context(
    *,
    repo_root: Path,
    selection: Mapping[str, Any],
    serialized_credential: str,
    required: bool,
) -> tuple[ConversationScopeSigningContext | None, Path | None]:
    try:
        config = load_current_generation_signer_config(
            repo_root=repo_root, selection=selection
        )
    except Exception:
        if not required:
            return None, None
        raise ConversationSessionAuthoritySourceError(
            "conversation_session_signer_config_unavailable"
        )
    policy = config.conversation_scope_signer_policy
    if isinstance(policy, Mapping):
        policy = ConversationScopeSignerPolicy(**dict(policy))
    if not isinstance(policy, ConversationScopeSignerPolicy):
        if not required:
            return None, None
        raise ConversationSessionAuthoritySourceError(
            "conversation_session_signer_policy_unavailable"
        )
    if not _has_exact_signer_profile(config=config, policy=policy):
        if not required:
            return None, None
        raise ConversationSessionAuthoritySourceError(
            "conversation_session_signer_profile_unavailable"
        )
    built = build_reddog_isolated_signer_socket_client(
        repo_root=repo_root,
        socket_path=config.socket_path,
        timeout_s=min(float(config.timeout_s), 30.0),
        max_response_bytes=int(config.max_response_bytes),
    )
    if built.accepted is not True or built.client is None:
        if not required:
            return None, None
        raise ConversationSessionAuthoritySourceError(
            "conversation_session_signer_socket_unavailable"
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


def _authority_receipt(
    *, credential: Any, selection: Mapping[str, Any], view: Mapping[str, Any],
    grounding_receipt_id: str, intent_id: str,
) -> dict[str, Any]:
    payload = {
        "schema_version": AUTHORITY_RECEIPT_SCHEMA,
        "credential_id": credential.credential_id,
        "credential_signature_digest": canonical_digest(
            {"credential_signature": credential.signature}
        ),
        "session_id": credential.session_id,
        "principal_id": credential.principal_id,
        "principal_provider": credential.principal_provider,
        "repo_full_name": credential.repo_full_name,
        "foundup_scope": list(credential.foundup_scope),
        "principal_record_digest": str(view["principal_record_digest"]),
        "session_binding_digest": str(view["session_binding_digest"]),
        "current_generation_manifest_id": str(selection.get("manifest_id") or ""),
        "artifact_generation_digest": str(
            selection.get("artifact_generation_digest") or ""
        ),
        "intent_id": intent_id,
        "grounding_receipt_id": grounding_receipt_id,
        "credential_issued_at": credential.issued_at,
        "credential_expires_at": credential.expires_at,
        "grants_work_authority": False,
    }
    return {**payload, "receipt_id": canonical_digest(payload)}


def _required_intent_binding(
    intent: Mapping[str, Any], grounding_receipt_id: str
) -> tuple[str, str]:
    requested = str(intent.get("foundup_id") or "").strip()
    intent_id = str(intent.get("intent_id") or "").strip()
    if not requested or not intent_id or not grounding_receipt_id:
        raise ConversationSessionAuthoritySourceError(
            "conversation_session_intent_binding_invalid"
        )
    return requested, intent_id


def _canonical_repo_full_name(repo_root: Path) -> str:
    config_path = _git_config_path(repo_root.resolve())
    # Git permits repeated branch-local keys. Scope this read to origin and let
    # ConfigParser mirror Git's last-value behavior for unrelated duplicates.
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    try:
        with config_path.open("r", encoding="utf-8") as handle:
            parser.read_file(handle)
        url = parser.get('remote "origin"', "url")
    except Exception as exc:
        raise ConversationSessionAuthoritySourceError(
            "conversation_session_repository_identity_unavailable"
        ) from exc
    match = re.fullmatch(
        r"(?:https://github\.com/|ssh://git@github\.com/|git@github\.com:)([^/\s]+)/([^/\s]+?)(?:\.git)?",
        url.strip(),
    )
    if match is None:
        raise ConversationSessionAuthoritySourceError(
            "conversation_session_repository_identity_unavailable"
        )
    return f"{match.group(1)}/{match.group(2)}"


def _git_config_path(repo_root: Path) -> Path:
    dot_git = repo_root / ".git"
    if dot_git.is_dir():
        return dot_git / "config"
    try:
        marker = dot_git.read_text(encoding="utf-8").strip()
        if not marker.startswith("gitdir:"):
            raise ValueError("gitdir marker missing")
        gitdir = Path(marker.split(":", 1)[1].strip())
        if not gitdir.is_absolute():
            gitdir = (repo_root / gitdir).resolve()
        common_text = (gitdir / "commondir").read_text(encoding="utf-8").strip()
        common = Path(common_text)
        if not common.is_absolute():
            common = (gitdir / common).resolve()
        return common / "config"
    except Exception as exc:
        raise ConversationSessionAuthoritySourceError(
            "conversation_session_repository_identity_unavailable"
        ) from exc


__all__ = [
    "AUTHORITY_RECEIPT_SCHEMA", "ConversationSessionAuthoritySourceError",
    "VerifiedResidentConversationSession",
    "lease_current_generation_conversation_session",
    "owner_config_from_environment",
]
