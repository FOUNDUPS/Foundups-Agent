"""Compatibility guards for legacy HMAC conversation persistence."""

from __future__ import annotations

from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_conversation_scope_capability import (
    consume_conversation_scope_capability,
    sign_record_with_scope_authority,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_request import (
    ConversationScopeAdvanceRequest,
    ConversationScopeCreateRequest,
)
from modules.communication.moltbot_bridge.src.reddog_authenticated_conversation_scope_state import (
    create_authenticated_conversation_scope,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_advance import (
    advance_authenticated_conversation_scope,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_work_promotion import (
    commit_pending_conversation_work_proposal,
    prepare_conversation_work_context,
)
from modules.communication.moltbot_bridge.tests.reddog_conversation_scope_test_support import (
    FOCUS,
    NOW,
    Resolver,
    TestAgentDb,
    capability,
    digest,
    item,
    state_patch,
)
from modules.communication.moltbot_bridge.tests.test_reddog_architect_fix_signed_wsp15_work_order_promotion import (
    _rebind_determination_admission,
)
from modules.communication.moltbot_bridge.tests.test_reddog_conversation_work_promotion import (
    FOUNDUP_ID,
    ROOT,
    _grounding,
    _normalized_determination,
    _bound_determination as _setup_bound_determination,
    _store,
)


class PendingForbiddenStore:
    def __init__(self, delegate: object, *, crash_on_cas: bool = False) -> None:
        self.delegate = delegate
        self.crash_on_cas = crash_on_cas

    def load(self, conversation_id: str):
        return self.delegate.load(conversation_id)

    def create(self, record: object):
        return self.delegate.create(record)

    def compare_and_swap(self, *args: object, **kwargs: object):
        if self.crash_on_cas:
            raise RuntimeError("simulated_hmac_precommit_crash")
        return self.delegate.compare_and_swap(*args, **kwargs)

    def pending_transactions(self):
        raise AssertionError("legacy_hmac_must_not_use_pending_transactions")


def _work_context(path: Path, store: object, created: object, cycle: dict):
    return prepare_conversation_work_context(
        store=store,
        capability=capability(),
        conversation_id=created.conversation_id,
        expected_revision=0,
        resident_cycle=cycle,
        now_epoch=NOW + 1,
    )


def _rebind_determination(context: object, determination: dict) -> dict:
    binding = context.binding.to_dict()
    return _rebind_determination_admission(
        determination,
        {
            "conversation_binding_present": True,
            **{key: value for key, value in binding.items() if key != "schema_version"},
        },
    )


def test_legacy_hmac_create_uses_direct_atomic_store(tmp_path: Path) -> None:
    path = tmp_path / "conversation.sqlite"
    admission = _normalized_determination()["proposal_admission"]
    grounding = _grounding(admission)
    created = create_authenticated_conversation_scope(
        store=PendingForbiddenStore(_store(path)),
        capability=capability(resolver=Resolver(foundup_scope=(FOUNDUP_ID,))),
        repo_root=ROOT,
        request=ConversationScopeCreateRequest(
            work_focus=FOCUS,
            grounding_receipt=grounding,
            discussion_foundup_ids=(FOUNDUP_ID,),
            conversation_nonce="legacy-hmac-direct-create",
            turn_id=digest({"turn": "legacy-hmac-create"}),
            active_topic="TRADE runtime",
            current_objective="Persist without a pending recovery row.",
            accepted_decisions=(item("Use current evidence."),),
            repository_evidence_refs=("code:trade",),
            source_snapshot_id=admission["snapshot_receipt_id"],
            source_snapshot_digest=admission["snapshot_content_digest"],
        ),
        now_epoch=NOW,
    )
    assert created.accepted is True, created.rejection_reasons


def test_legacy_hmac_advance_uses_direct_cas_without_pending(tmp_path: Path) -> None:
    path = tmp_path / "conversation.sqlite"
    created, cycle, _context, _determination = _setup_bound_determination(path)
    current = _store(path).load(created.conversation_id)["record"]
    result = advance_authenticated_conversation_scope(
        store=PendingForbiddenStore(_store(path)),
        capability=capability(),
        repo_root=Path(__file__).resolve().parents[4],
        request=ConversationScopeAdvanceRequest(
            conversation_id=created.conversation_id,
            expected_revision=0,
            work_focus=FOCUS,
            grounding_receipt=cycle["intent"]["grounding_receipt"],
            state_patch=state_patch(current["turn_id"]),
            expected_source_snapshot_id=current["source_snapshot_id"],
            expected_source_snapshot_digest=current["source_snapshot_digest"],
        ),
        now_epoch=NOW + 2,
    )
    assert result.accepted is True


def test_legacy_hmac_proposal_crash_retries_without_pending_row(
    tmp_path: Path,
) -> None:
    path = tmp_path / "conversation.sqlite"
    created, cycle, _context, determination = _setup_bound_determination(path)
    crash_store = PendingForbiddenStore(_store(path), crash_on_cas=True)
    context = _work_context(path, crash_store, created, cycle)
    determination = _rebind_determination(context, determination)

    with pytest.raises(RuntimeError, match="simulated_hmac_precommit_crash"):
        commit_pending_conversation_work_proposal(
            context=context.context,
            architect_determination=determination,
            now_epoch=NOW + 2,
        )
    rows = TestAgentDb(path).db.execute_query(
        "SELECT name FROM sqlite_master WHERE name = ?",
        ("reddog_conversation_scope_pending",),
    )
    assert rows == []

    retry = _work_context(path, PendingForbiddenStore(_store(path)), created, cycle)
    recovered = commit_pending_conversation_work_proposal(
        context=retry.context,
        architect_determination=_rebind_determination(retry, determination),
        now_epoch=NOW + 3,
    )
    assert recovered.accepted is True
    assert recovered.conversation_revision == 1


def test_legacy_hmac_require_replay_remains_forbidden() -> None:
    token = capability()
    authority = consume_conversation_scope_capability(
        token,
        active_foundup_id="trade",
        discussion_foundup_ids=("trade",),
        now_epoch=NOW,
    )
    assert sign_record_with_scope_authority(
        authority, {"record_auth_scheme": "hmac-sha256-v1"}, require_replay=True
    ) is None
