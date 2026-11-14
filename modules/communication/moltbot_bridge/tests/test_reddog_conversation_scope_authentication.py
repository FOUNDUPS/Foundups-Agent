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
    FoundUpConversationScopeCapability,
    PrincipalContextReadConversationScopeCapability,
    consume_conversation_scope_capability,
    conversation_scope_authority_view,
    split_conversation_scope_capability,
    split_foundup_conversation_scope_capability_pair,
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


def test_capability_split_is_exactly_once_and_retires_root() -> None:
    root = capability()
    children = split_conversation_scope_capability(root)
    assert children is not None
    foundup, principal = children
    assert type(foundup) is FoundUpConversationScopeCapability
    assert type(principal) is PrincipalContextReadConversationScopeCapability
    assert split_conversation_scope_capability(root) is None
    assert consume_conversation_scope_capability(
        root,
        active_foundup_id="trade",
        discussion_foundup_ids=("trade",),
        now_epoch=NOW,
    ) is None


@pytest.mark.parametrize("scope_kind", ("foundup", "comparison"))
def test_principal_child_rejects_nonprincipal_scope(scope_kind: str) -> None:
    children = split_conversation_scope_capability(capability())
    assert children is not None
    principal = children[1]
    active = "trade" if scope_kind == "foundup" else ""
    discussions = ("trade",) if scope_kind == "foundup" else ("trade", "other")
    assert consume_conversation_scope_capability(
        principal,
        active_foundup_id=active,
        discussion_foundup_ids=discussions,
        scope_kind=scope_kind,
        now_epoch=NOW,
    ) is None
    assert consume_conversation_scope_capability(
        principal,
        active_foundup_id="",
        discussion_foundup_ids=(),
        scope_kind="principal",
        now_epoch=NOW,
    ) is None


def test_foundup_child_rejects_principal_scope() -> None:
    children = split_conversation_scope_capability(capability())
    assert children is not None
    foundup = children[0]
    assert consume_conversation_scope_capability(
        foundup,
        active_foundup_id="",
        discussion_foundup_ids=(),
        scope_kind="principal",
        now_epoch=NOW,
    ) is None
    assert consume_conversation_scope_capability(
        foundup,
        active_foundup_id="trade",
        discussion_foundup_ids=("trade",),
        now_epoch=NOW,
    ) is None


def test_capability_split_children_are_independently_one_use() -> None:
    children = split_conversation_scope_capability(capability())
    assert children is not None
    foundup, principal = children
    assert consume_conversation_scope_capability(
        foundup,
        active_foundup_id="trade",
        discussion_foundup_ids=("trade",),
        now_epoch=NOW,
    ) is not None
    assert consume_conversation_scope_capability(
        principal,
        active_foundup_id="",
        discussion_foundup_ids=(),
        scope_kind="principal",
        now_epoch=NOW,
    ) is not None


def test_foundup_pair_split_issues_distinct_one_use_siblings() -> None:
    root = capability()
    children = split_foundup_conversation_scope_capability_pair(root)
    assert children is not None
    assert children[0] is not children[1]
    assert split_foundup_conversation_scope_capability_pair(root) is None
    for child in children:
        authority = consume_conversation_scope_capability(
            child, active_foundup_id="trade",
            discussion_foundup_ids=("trade",), now_epoch=NOW,
        )
        assert authority is not None
        assert conversation_scope_authority_view(authority) is not None
        assert consume_conversation_scope_capability(
            child, active_foundup_id="trade",
            discussion_foundup_ids=("trade",), now_epoch=NOW,
        ) is None
def test_failed_split_is_atomic(monkeypatch) -> None:
    class _FailSecond(dict):
        issued: list[object] = []

        def __setitem__(self, key, value) -> None:
            self.issued.append(key)
            if len(self.issued) == 2:
                raise RuntimeError("injected_split_failure")
            super().__setitem__(key, value)

    delegated = _FailSecond()
    monkeypatch.setattr(capability_module, "_DELEGATED_CAPABILITIES", delegated)
    root = capability()
    assert split_conversation_scope_capability(root) is None
    assert len(delegated.issued) == 2
    assert delegated == {}
    leaked_child = delegated.issued[0]
    assert consume_conversation_scope_capability(
        leaked_child,
        active_foundup_id="trade",
        discussion_foundup_ids=("trade",),
        now_epoch=NOW,
    ) is None
    # A partial delegation failure retires the root as well as both children;
    # no credential-derived authority remains reusable after the failed split.
    assert split_conversation_scope_capability(root) is None


def test_split_children_reject_construction_copy_pickle_and_secret_repr() -> None:
    for child_type in (
        FoundUpConversationScopeCapability,
        PrincipalContextReadConversationScopeCapability,
    ):
        with pytest.raises(TypeError):
            child_type()
    children = split_conversation_scope_capability(capability())
    assert children is not None
    for child in children:
        assert repr(child) == f"<{type(child).__name__} opaque>"
        for operation in (copy.copy, copy.deepcopy, pickle.dumps):
            with pytest.raises(TypeError):
                operation(child)


def test_principal_record_requires_exact_subject_digest() -> None:
    resolver = Resolver()
    resolver.record = resolver.record.__class__(
        **{**resolver.record.to_dict(), "verified_subject_digest": "sha256:not-a-digest"}
    )
    assert capability(resolver=resolver) is None


def test_secret_bearing_issuer_is_not_a_public_api() -> None:
    assert "_ConversationScopeAuthoritySeal" not in capability_module.__all__
    assert "_issue_conversation_scope_capability" not in capability_module.__all__
