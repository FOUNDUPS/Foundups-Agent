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
    split_foundup_conversation_scope_capability_pair,
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
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_signing import (
    ConversationScopeSigningContext,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_session_signing_context import (
    ConversationSessionSigningContextError,
    load_conversation_session_signing_context as _conversation_signing_context,
)
from modules.communication.moltbot_bridge.src.reddog_principal_memex_live_resident_source_supply import (
    PrincipalMemexSessionAuthorization,
    discard_principal_memex_live_resident_source,
    issue_principal_memex_session_authorization,
)


OWNER_CONFIG_ENV = "REDDOG_SIGNER_SYSTEM_SERVICE_OWNER_CONFIG_PATH"
AUTHORITY_RECEIPT_SCHEMA = "reddog_conversation_session_authority_receipt.v1"
SESSION_SOURCE_REJECTION_REASONS = frozenset(
    {
        "conversation_session_authority_source_missing",
        "conversation_session_scope_delegation_failed",
        "conversation_session_authority_verification_failed",
        "conversation_session_authority_scope_rejected",
        "conversation_session_expected_binding_mismatch",
        "conversation_session_signer_config_unavailable",
        "conversation_session_signer_policy_unavailable",
        "conversation_session_signer_profile_unavailable",
        "conversation_session_signer_socket_unavailable",
        "conversation_session_intent_binding_invalid",
        "conversation_session_repository_identity_unavailable",
    }
)


class ConversationSessionAuthoritySourceError(ValueError):
    """Stable public failure without credential or filesystem detail."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def public_conversation_session_authority_reason(
    error: ConversationSessionAuthoritySourceError, *, unavailable_reason: str,
) -> str:
    """Project only an allowlisted session-source reason."""

    return (
        error.reason
        if type(error.reason) is str
        and error.reason in SESSION_SOURCE_REJECTION_REASONS
        else unavailable_reason
    )


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
    secondary_authority: VerifiedConversationScopeAuthority | None = field(
        default=None, repr=False, compare=False
    )
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
    include_secondary_foundup_authority: bool = False,
    require_record_signing_context: bool = False,
) -> Iterator[VerifiedResidentConversationSession]:
    """Hold current-generation authority through one resident admission."""

    requested_foundup, intent_id = _required_intent_binding(
        intent, grounding_receipt_id
    )
    repo_full_name = _canonical_repo_full_name(repo_root)
    binding = _session_binding(intent, intent_id, grounding_receipt_id)
    authority: VerifiedConversationScopeAuthority | None = None
    secondary_authority: VerifiedConversationScopeAuthority | None = None
    principal_authorization: PrincipalMemexSessionAuthorization | None = None
    with lease_owner_e0_current_selection(
        owner_config_path=owner_config_path, repo_root=repo_root
    ) as selection:
        session, authority, secondary_authority, principal_authorization = (
            _authenticate_and_consume(
                repo_root=repo_root, selection=selection,
                serialized_credential=serialized_credential,
                repo_full_name=repo_full_name, intent=intent,
                requested_foundup=requested_foundup,
                grounding_receipt_id=grounding_receipt_id,
                session_binding=binding, now_epoch=now_epoch,
                include_principal_scope_capability=include_principal_scope_capability,
                include_secondary_foundup_authority=include_secondary_foundup_authority,
                require_record_signing_context=require_record_signing_context,
            )
        )
        try:
            yield session
        finally:
            if authority is not None:
                discard_conversation_scope_capability(authority)
            if secondary_authority is not None:
                discard_conversation_scope_capability(secondary_authority)
            if principal_authorization is not None:
                discard_principal_memex_live_resident_source(principal_authorization)


def owner_config_from_environment(environment: Mapping[str, str]) -> str:
    value = str(environment.get(OWNER_CONFIG_ENV, "") or "").strip()
    if not value:
        raise ConversationSessionAuthoritySourceError(
            "conversation_session_authority_source_missing"
        )
    return value


def _session_binding(
    intent: Mapping[str, Any], intent_id: str, grounding_receipt_id: str,
) -> str:
    return canonical_digest(
        {
            "intent_id": intent_id, "grounding_receipt_id": grounding_receipt_id,
            "source_surface": str(intent.get("source_surface") or ""),
        }
    )


def _authenticate_and_consume(
    *, repo_root: Path, selection: Mapping[str, Any], serialized_credential: str,
    repo_full_name: str, intent: Mapping[str, Any], requested_foundup: str,
    grounding_receipt_id: str, session_binding: str, now_epoch: int,
    include_principal_scope_capability: bool, include_secondary_foundup_authority: bool,
    require_record_signing_context: bool,
) -> tuple[
    VerifiedResidentConversationSession,
    VerifiedConversationScopeAuthority,
    VerifiedConversationScopeAuthority | None,
    PrincipalMemexSessionAuthorization | None,
]:
    capability, credential, resolver, signing_context, runtime_root = _authenticate_scope(
        repo_root=repo_root, selection=selection,
        serialized_credential=serialized_credential,
        repo_full_name=repo_full_name, session_binding=session_binding,
        now_epoch=now_epoch,
        require_signing_context=(
            include_principal_scope_capability or require_record_signing_context
        ),
    )
    foundup_capability, secondary_capability, principal_capability = _scope_capabilities(
        capability, include_principal_scope_capability,
        include_secondary_foundup_authority,
    )
    authority = consume_conversation_scope_capability(
        foundup_capability, active_foundup_id=requested_foundup,
        discussion_foundup_ids=(requested_foundup,), now_epoch=int(now_epoch),
    )
    secondary_authority = consume_conversation_scope_capability(
        secondary_capability, active_foundup_id=requested_foundup,
        discussion_foundup_ids=(requested_foundup,), now_epoch=int(now_epoch),
    ) if secondary_capability is not None else None
    try:
        session = _verified_session(
            authority=authority, secondary_authority=secondary_authority,
            credential=credential, intent=intent,
            selection=selection, grounding_receipt_id=grounding_receipt_id,
            principal_capability=principal_capability, principal_resolver=resolver,
            runtime_root=runtime_root,
        )
    except Exception:
        discard_conversation_scope_capability(authority)
        discard_conversation_scope_capability(secondary_authority)
        discard_conversation_scope_capability(principal_capability)
        raise
    return (
        session, authority, secondary_authority,
        session.principal_memex_authorization,
    )


def _scope_capabilities(
    capability: AuthenticatedConversationScopeCapability, include_principal: bool,
    include_secondary: bool,
) -> tuple[Any, Any | None, PrincipalContextReadConversationScopeCapability | None]:
    if include_principal and include_secondary:
        discard_conversation_scope_capability(capability)
        raise ConversationSessionAuthoritySourceError(
            "conversation_session_scope_delegation_failed"
        )
    if include_secondary:
        children = split_foundup_conversation_scope_capability_pair(capability)
        if children is None:
            raise ConversationSessionAuthoritySourceError(
                "conversation_session_scope_delegation_failed"
            )
        return children[0], children[1], None
    if not include_principal:
        return capability, None, None
    children = split_conversation_scope_capability(capability)
    if children is None:
        raise ConversationSessionAuthoritySourceError(
            "conversation_session_scope_delegation_failed"
        )
    return children[0], None, children[1]


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
    except ConversationSessionSigningContextError as exc:
        raise ConversationSessionAuthoritySourceError(exc.reason) from exc
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
    *, authority: Any, secondary_authority: Any, credential: Any,
    intent: Mapping[str, Any],
    selection: Mapping[str, Any], grounding_receipt_id: str,
    principal_capability: PrincipalContextReadConversationScopeCapability | None,
    principal_resolver: PrincipalAuthorityResolver, runtime_root: Path | None,
) -> VerifiedResidentConversationSession:
    view = _authority_view_or_raise(authority, secondary_authority)
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
    return VerifiedResidentConversationSession(
        principal_id=credential.principal_id,
        principal_provider=credential.principal_provider,
        foundup_scope=credential.foundup_scope,
        repo_full_name=credential.repo_full_name,
        principal_record_digest=str(view["principal_record_digest"]),
        session_binding_digest=str(view["session_binding_digest"]),
        current_generation_manifest_id=str(selection.get("manifest_id") or ""),
        authority_receipt=MappingProxyType(receipt),
        authority=authority,
        secondary_authority=secondary_authority,
        principal_memex_authorization=principal_authorization,
    )


def _authority_view_or_raise(
    authority: Any, secondary_authority: Any,
) -> Mapping[str, Any]:
    secondary_valid = (
        secondary_authority is None
        or conversation_scope_authority_view(secondary_authority) is not None
    )
    view = conversation_scope_authority_view(authority)
    if authority is None or not secondary_valid or not isinstance(view, Mapping):
        discard_conversation_scope_capability(authority)
        raise ConversationSessionAuthoritySourceError(
            "conversation_session_authority_scope_rejected"
        )
    return view


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
    "SESSION_SOURCE_REJECTION_REASONS",
    "VerifiedResidentConversationSession",
    "lease_current_generation_conversation_session",
    "owner_config_from_environment", "public_conversation_session_authority_reason",
]
