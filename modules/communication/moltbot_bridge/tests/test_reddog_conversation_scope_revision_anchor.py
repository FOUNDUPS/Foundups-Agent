"""Monotonic signer-anchor regression for conversation revisions."""

from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_authenticated_conversation_scope_state import (
    advance_authenticated_conversation_scope,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_request import (
    ConversationScopeAdvanceRequest,
)
from modules.communication.moltbot_bridge.tests.reddog_conversation_scope_test_support import (
    FOCUS,
    SNAPSHOT_DIGEST,
    SNAPSHOT_ID,
    digest,
    grounding_receipt,
)
from modules.communication.moltbot_bridge.tests.reddog_conversation_scope_signing_test_support import (
    NOW,
    REPO_ROOT,
    capability,
    context,
    create,
    credential,
    store,
)


def test_signed_revision_advances_monotonic_anchor(tmp_path: Path) -> None:
    serialized = credential()
    signing_context, anchor = context(serialized)
    path = tmp_path / "scope.sqlite"
    created = create(path, signing_context, serialized)
    current = store(path).load(created.conversation_id)["record"]
    advanced = advance_authenticated_conversation_scope(
        store=store(path),
        capability=capability(signing_context, serialized, NOW),
        repo_root=REPO_ROOT,
        request=ConversationScopeAdvanceRequest(
            conversation_id=created.conversation_id,
            expected_revision=0,
            work_focus=FOCUS,
            grounding_receipt=grounding_receipt(),
            state_patch={
                "turn_id": digest({"turn": "signed-second"}),
                "parent_turn_id": current["turn_id"],
                "active_topic": "TRADE runtime",
                "current_objective": "Implement the grounded slice.",
                "repository_evidence_refs": ("code:trade",),
            },
            expected_source_snapshot_id=SNAPSHOT_ID,
            expected_source_snapshot_digest=SNAPSHOT_DIGEST,
        ),
        now_epoch=NOW,
    )

    assert advanced.accepted is True, advanced.rejection_reasons
    persisted = store(path).load(created.conversation_id)["record"]
    head = anchor.load()["heads"][created.conversation_id]
    assert advanced.conversation_revision == head["conversation_revision"] == 1
    assert head["record_auth_nonce"] == persisted["record_auth_nonce"]
    assert "nonces" not in head
    assert len(head) == 12
