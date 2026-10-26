"""Crash recovery for E0-signed conversation proposal publication."""

from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_authenticated_conversation_scope_state import (
    advance_authenticated_conversation_scope,
    create_authenticated_conversation_scope,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_request import (
    ConversationScopeAdvanceRequest,
    ConversationScopeCreateRequest,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_work_promotion import (
    commit_pending_conversation_work_proposal,
    prepare_conversation_work_context,
)
from modules.communication.moltbot_bridge.tests.reddog_conversation_scope_signing_test_support import (
    ChangingAuditMacBuilder,
    CrashBeforeFinalizeTransactions,
    capability,
    context,
    credential,
)
from modules.communication.moltbot_bridge.tests.reddog_conversation_scope_test_support import (
    FOCUS,
    digest,
    item,
    state_patch,
)
from modules.communication.moltbot_bridge.tests.test_reddog_architect_fix_signed_wsp15_work_order_promotion import (
    _rebind_determination_admission,
)
from modules.communication.moltbot_bridge.tests.test_reddog_conversation_work_promotion import (
    FOUNDUP_ID,
    NOW,
    ROOT,
    _grounding,
    _normalized_determination,
    _store,
)


class _CrashAfterSignerStore:
    def __init__(self, delegate: object) -> None:
        self.delegate = delegate

    def load(self, conversation_id: str):
        return self.delegate.load(conversation_id)

    def pending_transactions(self) -> CrashBeforeFinalizeTransactions:
        return CrashBeforeFinalizeTransactions(self.delegate.pending_transactions())

    def compare_and_swap(self, *_args: object, **_kwargs: object):
        raise RuntimeError("simulated_process_crash_after_signer_commit")


def _e0_scope_and_cycle(
    path: Path, signing_context: object, serialized: str, determination: dict
):
    admission = determination["proposal_admission"]
    grounding = _grounding(admission)
    created = create_authenticated_conversation_scope(
        store=_store(path),
        capability=capability(signing_context, serialized),
        repo_root=ROOT,
        request=ConversationScopeCreateRequest(
            work_focus=FOCUS,
            grounding_receipt=grounding,
            discussion_foundup_ids=(FOUNDUP_ID,),
            conversation_nonce="conversation-work-crash-recovery",
            turn_id=digest({"turn": "proposal-crash-source"}),
            active_topic="TRADE runtime",
            current_objective="Recover one exact signed proposal publication.",
            accepted_decisions=(
                item("Use current repository evidence.", "repository_fact"),
            ),
            repository_evidence_refs=("code:trade",),
            source_snapshot_id=admission["snapshot_receipt_id"],
            source_snapshot_digest=admission["snapshot_content_digest"],
            ttl_seconds=200,
        ),
        now_epoch=NOW,
    )
    assert created.accepted is True, created.rejection_reasons
    intent = {
        "schema_version": "reddog_intent.v2",
        "intent_id": digest({"intent": created.conversation_id}),
        "principal_id": "principal_012",
        "foundup_id": FOUNDUP_ID,
        "work_focus": FOCUS,
        "grounding_receipt": grounding,
        "submits_executable_authority": False,
    }
    cycle = {
        "intent_id": intent["intent_id"],
        "intent_digest": digest(
            {"schema_version": "reddog_resident_intent_binding.v1", "intent": intent}
        ),
        "intent": intent,
        "snapshot_id": admission["snapshot_receipt_id"],
        "_store_integrity_valid": True,
    }
    return created, cycle


def _bound_context(
    path: Path,
    store: object,
    signing_context: object,
    serialized: str,
    conversation_id: str,
    cycle: dict,
):
    return prepare_conversation_work_context(
        store=store,
        capability=capability(signing_context, serialized, NOW + 1),
        conversation_id=conversation_id,
        expected_revision=0,
        resident_cycle=cycle,
        now_epoch=NOW + 1,
    )


def _crash_after_signer_commit(
    path: Path, signing_context: object, serialized: str,
    determination: dict, created: object, cycle: dict, signer_clock: list[int],
) -> dict:
    crash_context = _bound_context(
        path,
        _CrashAfterSignerStore(_store(path)),
        signing_context,
        serialized,
        created.conversation_id,
        cycle,
    )
    binding = crash_context.binding.to_dict()
    determination = _rebind_determination_admission(
        determination,
        {
            "conversation_binding_present": True,
            **{key: value for key, value in binding.items() if key != "schema_version"},
        },
    )

    signer_clock[0] = NOW + 2
    with pytest.raises(RuntimeError, match="simulated_process_crash"):
        commit_pending_conversation_work_proposal(
            context=crash_context.context,
            architect_determination=determination,
            now_epoch=NOW + 2,
        )
    return determination


def _assert_pending_blocks_competitor(
    path: Path, signing_context: object, serialized: str,
    determination: dict, created: object, cycle: dict,
    audit_builder: ChangingAuditMacBuilder, expected_audit_calls: int,
) -> None:
    current = _store(path).load(created.conversation_id)["record"]
    competing = advance_authenticated_conversation_scope(
        store=_store(path),
        capability=capability(signing_context, serialized, NOW + 3),
        repo_root=ROOT,
        request=ConversationScopeAdvanceRequest(
            conversation_id=created.conversation_id,
            expected_revision=0,
            work_focus=FOCUS,
            grounding_receipt=cycle["intent"]["grounding_receipt"],
            state_patch=state_patch(current["turn_id"]),
            expected_source_snapshot_id=determination["snapshot_receipt_id"],
            expected_source_snapshot_digest=determination["snapshot_content_digest"],
        ),
        now_epoch=NOW + 3,
    )
    assert competing.accepted is False
    assert competing.rejection_reasons == ("conversation_scope_pending_conflict",)
    assert _store(path).load(created.conversation_id)["record"][
        "conversation_revision"
    ] == 0
    assert audit_builder.calls == expected_audit_calls


def _recover_proposal(
    path: Path, signing_context: object, serialized: str,
    determination: dict, created: object, cycle: dict, signer_clock: list[int],
):
    retry_context = _bound_context(
        path, _store(path), signing_context, serialized, created.conversation_id, cycle
    )
    signer_clock[0] = NOW + 7
    return commit_pending_conversation_work_proposal(
        context=retry_context.context,
        architect_determination=determination,
        now_epoch=NOW + 7,
    )


def test_proposal_signer_commit_crash_recovers_without_anchor_fork(
    tmp_path: Path,
) -> None:
    path = tmp_path / "conversation.sqlite"
    serialized = credential()
    audit_builder = ChangingAuditMacBuilder()
    signer_clock = [NOW]
    signing_context, anchor = context(
        serialized, clock=signer_clock, audit_builder=audit_builder
    )
    determination = _normalized_determination()
    created, cycle = _e0_scope_and_cycle(
        path, signing_context, serialized, determination
    )
    determination = _crash_after_signer_commit(
        path, signing_context, serialized, determination, created, cycle, signer_clock
    )

    assert (
        _store(path).load(created.conversation_id)["record"]["conversation_revision"]
        == 0
    )
    assert anchor.load()["heads"][created.conversation_id]["conversation_revision"] == 1
    calls_after_crash = audit_builder.calls
    signer_clock[0] = NOW + 3
    _assert_pending_blocks_competitor(
        path, signing_context, serialized, determination,
        created, cycle, audit_builder, calls_after_crash,
    )
    recovered = _recover_proposal(
        path, signing_context, serialized, determination, created, cycle, signer_clock
    )

    assert recovered.accepted is True
    assert recovered.conversation_revision == 1
    assert audit_builder.calls == calls_after_crash
    assert anchor.load()["heads"][created.conversation_id]["conversation_revision"] == 1
