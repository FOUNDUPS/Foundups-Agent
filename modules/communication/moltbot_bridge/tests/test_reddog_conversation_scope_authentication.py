"""Authentication and opaque-capability regressions for RedDog conversation scope."""

from __future__ import annotations

import copy
import pickle

import pytest

from modules.communication.moltbot_bridge.src import reddog_conversation_scope_capability as capability_module
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_authentication import (
    AuthenticatedConversationScopeCapability,
    authenticate_conversation_scope,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_capability import (
    consume_conversation_scope_capability,
    conversation_scope_authority_view,
)
from modules.communication.moltbot_bridge.tests.reddog_conversation_scope_test_support import (
    NOW,
    SECRET,
    Resolver,
    capability,
    session_token,
)


def test_signed_session_subject_resolves_current_principal_scope() -> None:
    proof = capability()
    authority = consume_conversation_scope_capability(
        proof,
        active_foundup_id="trade",
        discussion_foundup_ids=("trade",),
        now_epoch=NOW,
    )
    view = conversation_scope_authority_view(authority)
    assert view is not None
    assert view["principal_id"] == "principal_012"
    assert view["foundup_scope"] == ("trade",)
    assert not any("key" in name and name != "principal_key_fingerprint" for name in view)


def test_session_token_tamper_and_unresolved_subject_fail_closed() -> None:
    token = session_token()
    assert authenticate_conversation_scope(
        session_token=token[:-1] + ("a" if token[-1] != "a" else "b"),
        principal_provider="test-provider",
        transport="editor",
        session_binding="window:one",
        principal_resolver=Resolver(),
        now_epoch=NOW,
        secret_provider=lambda: (SECRET, None),
    ) is None
    assert authenticate_conversation_scope(
        session_token=session_token("other-principal"),
        principal_provider="test-provider",
        transport="editor",
        session_binding="window:one",
        principal_resolver=Resolver(),
        now_epoch=NOW,
        secret_provider=lambda: (SECRET, None),
    ) is None


def test_capability_is_one_use_and_foundup_scope_is_enforced() -> None:
    proof = capability()
    assert consume_conversation_scope_capability(
        proof,
        active_foundup_id="other",
        discussion_foundup_ids=("other",),
        now_epoch=NOW,
    ) is None
    assert consume_conversation_scope_capability(
        proof,
        active_foundup_id="trade",
        discussion_foundup_ids=("trade",),
        now_epoch=NOW,
    ) is None


def test_expired_capability_fails_closed() -> None:
    proof = capability()
    assert consume_conversation_scope_capability(
        proof,
        active_foundup_id="trade",
        discussion_foundup_ids=("trade",),
        now_epoch=NOW + 60,
    ) is None


def test_capability_cannot_be_constructed_copied_or_pickled() -> None:
    with pytest.raises(TypeError):
        AuthenticatedConversationScopeCapability()
    proof = capability()
    assert proof is not None
    with pytest.raises(TypeError):
        copy.copy(proof)
    with pytest.raises(TypeError):
        copy.deepcopy(proof)
    with pytest.raises(TypeError):
        pickle.dumps(proof)


def test_principal_record_requires_exact_subject_digest() -> None:
    resolver = Resolver()
    resolver.record = resolver.record.__class__(
        **{**resolver.record.to_dict(), "verified_subject_digest": "sha256:not-a-digest"}
    )
    assert capability(resolver=resolver) is None


def test_secret_bearing_issuer_is_not_a_public_api() -> None:
    assert "_ConversationScopeAuthoritySeal" not in capability_module.__all__
    assert "_issue_conversation_scope_capability" not in capability_module.__all__
