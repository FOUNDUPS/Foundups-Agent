"""AgentDB lifecycle tests for authenticated RedDog conversation scope."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_authenticated_conversation_scope_state import (
    advance_authenticated_conversation_scope,
    create_authenticated_conversation_scope,
    resume_authenticated_conversation_scope,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_store import (
    AgentDbConversationScopeStore,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_request import (
    ConversationScopeAdvanceRequest,
    ConversationScopeCreateRequest,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_contract import (
    validate_record,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_work_promotion import (
    prepare_conversation_work_context,
)
from modules.communication.moltbot_bridge.tests.reddog_conversation_scope_test_support import (
    FOCUS,
    HOLO_GENERATION,
    NOW,
    SNAPSHOT_DIGEST,
    SNAPSHOT_ID,
    TestAgentDb,
    Resolver,
    capability,
    digest,
    grounding_receipt,
    item,
    state_patch,
)


def _store(path: Path) -> AgentDbConversationScopeStore:
    return AgentDbConversationScopeStore(lambda: TestAgentDb(path))


def _create(path: Path, **overrides):
    scope_capability = overrides.pop("_capability", capability())
    values = {
        "work_focus": FOCUS,
        "grounding_receipt": grounding_receipt(),
        "discussion_foundup_ids": ("trade",),
        "conversation_nonce": "conversation-one",
        "turn_id": digest({"turn": "first"}),
        "active_topic": "TRADE runtime",
        "current_objective": "Identify the next grounded implementation slice.",
        "accepted_decisions": (item("Use current repository evidence.", "repository_fact"),),
        "rejected_options": (),
        "open_questions": (item("What is the next bounded slice?", "unresolved"),),
        "repository_evidence_refs": ("code:trade",),
        "source_snapshot_id": SNAPSHOT_ID,
        "source_snapshot_digest": SNAPSHOT_DIGEST,
    }
    values.update(overrides)
    return create_authenticated_conversation_scope(
        store=_store(path), capability=scope_capability,
        repo_root=Path(__file__).resolve().parents[4],
        request=ConversationScopeCreateRequest(**values), now_epoch=NOW,
    )


def _resume(path: Path, conversation_id: str, **overrides):
    values = {
        "store": _store(path),
        "capability": capability(),
        "conversation_id": conversation_id,
        "expected_head_sha": grounding_receipt()["holoindex_repo_head_sha"],
        "expected_holoindex_generation_id": HOLO_GENERATION,
        "expected_source_snapshot_id": SNAPSHOT_ID,
        "expected_source_snapshot_digest": SNAPSHOT_DIGEST,
        "now_epoch": NOW + 1,
    }
    values.update(overrides)
    return resume_authenticated_conversation_scope(**values)


def test_v2_record_is_not_inferred_or_upgraded(tmp_path: Path) -> None:
    created = _create(tmp_path / "scope.sqlite")
    stored = _store(tmp_path / "scope.sqlite").load(created.conversation_id)["record"]

    assert validate_record(
        {**stored, "schema_version": "reddog_authenticated_conversation_scope.v2"}
    ) == ("conversation_scope_record_shape_invalid",)


def test_create_restart_resume_and_projection_are_bounded(tmp_path: Path) -> None:
    result = _create(tmp_path / "scope.sqlite")
    assert result.accepted is True
    resumed = _resume(tmp_path / "scope.sqlite", result.conversation_id)
    assert resumed.accepted is True
    assert resumed.projection["authority_effect"] == "none"
    assert resumed.projection["source_snapshot_id"] == SNAPSHOT_ID
    assert "principal_id" not in resumed.projection
    assert resumed.no_work_authority_granted is True
    assert resumed.no_worker_dispatch_performed is True


def test_duplicate_conversation_and_raw_secret_material_do_not_persist(tmp_path: Path) -> None:
    path = tmp_path / "scope.sqlite"
    first = _create(path)
    second = _create(path)
    assert first.accepted is True
    assert second.accepted is False
    row = TestAgentDb(path).db.execute_query(
        "SELECT scope_json FROM reddog_conversation_scopes"
    )[0]["scope_json"]
    assert "sess.v1" not in row
    assert "conversation-scope-test-secret" not in row
    assert "principal-public-key" not in row


def test_advance_uses_revision_cas_and_clears_pending_proposal(tmp_path: Path) -> None:
    path = tmp_path / "scope.sqlite"
    created = _create(path)
    current = _store(path).load(created.conversation_id)["record"]
    result = advance_authenticated_conversation_scope(
        store=_store(path),
        capability=capability(),
        repo_root=Path(__file__).resolve().parents[4],
        request=ConversationScopeAdvanceRequest(
            conversation_id=created.conversation_id, expected_revision=0,
            work_focus=FOCUS, grounding_receipt=grounding_receipt(),
            state_patch=state_patch(current["turn_id"]),
            expected_source_snapshot_id=SNAPSHOT_ID,
            expected_source_snapshot_digest=SNAPSHOT_DIGEST,
        ),
        now_epoch=NOW + 2,
    )
    assert result.accepted is True
    assert result.conversation_revision == 1
    advanced = _store(path).load(created.conversation_id)["record"]
    stale = advance_authenticated_conversation_scope(
        store=_store(path),
        capability=capability(),
        repo_root=Path(__file__).resolve().parents[4],
        request=ConversationScopeAdvanceRequest(
            conversation_id=created.conversation_id, expected_revision=0,
            work_focus=FOCUS, grounding_receipt=grounding_receipt(),
            state_patch=state_patch(advanced["turn_id"]),
            expected_source_snapshot_id=SNAPSHOT_ID,
            expected_source_snapshot_digest=SNAPSHOT_DIGEST,
        ),
        now_epoch=NOW + 3,
    )
    assert stale.accepted is False
    assert "conversation_scope_revision_conflict" in stale.rejection_reasons


def test_parent_turn_mismatch_and_cross_foundup_grounding_reject(tmp_path: Path) -> None:
    path = tmp_path / "scope.sqlite"
    created = _create(path)
    bad_parent = dict(state_patch(digest({"turn": "wrong"})))
    rejected = advance_authenticated_conversation_scope(
        store=_store(path), capability=capability(),
        repo_root=Path(__file__).resolve().parents[4],
        request=ConversationScopeAdvanceRequest(
            conversation_id=created.conversation_id, expected_revision=0,
            work_focus=FOCUS, grounding_receipt=grounding_receipt(),
            state_patch=bad_parent, expected_source_snapshot_id=SNAPSHOT_ID,
            expected_source_snapshot_digest=SNAPSHOT_DIGEST,
        ), now_epoch=NOW + 2,
    )
    assert rejected.accepted is False
    other_focus = "Assess the GotJunk FoundUp runtime using current repository evidence."
    rejected = advance_authenticated_conversation_scope(
        store=_store(path),
        capability=capability(resolver=Resolver(foundup_scope=("trade", "gotjunk_001"))),
        repo_root=Path(__file__).resolve().parents[4],
        request=ConversationScopeAdvanceRequest(
            conversation_id=created.conversation_id, expected_revision=0,
            work_focus=other_focus,
            grounding_receipt=grounding_receipt("gotjunk_001", focus=other_focus),
            state_patch=state_patch(digest({"turn": "first"})),
            expected_source_snapshot_id=SNAPSHOT_ID,
            expected_source_snapshot_digest=SNAPSHOT_DIGEST,
        ),
        now_epoch=NOW + 2,
    )
    assert rejected.accepted is False


def test_stale_head_holo_snapshot_and_expiry_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "scope.sqlite"
    created = _create(path, ttl_seconds=10)
    for override in (
        {"expected_head_sha": "0" * 40},
        {"expected_holoindex_generation_id": "sha256:" + "0" * 64},
        {"expected_source_snapshot_digest": "sha256:" + "0" * 64},
        {"now_epoch": NOW + 10},
    ):
        assert _resume(path, created.conversation_id, **override).accepted is False


def test_wrong_principal_transport_and_key_rotation_reject(tmp_path: Path) -> None:
    path = tmp_path / "scope.sqlite"
    created = _create(path)
    assert _resume(path, created.conversation_id, capability=capability(principal_id="other-principal")).accepted is False
    assert _resume(path, created.conversation_id, capability=capability(transport="api")).accepted is False
    assert _resume(
        path,
        created.conversation_id,
        capability=capability(resolver=Resolver(public_key="ed25519:rotated-key")),
    ).accepted is False


def test_concurrent_updates_commit_exactly_one_revision(tmp_path: Path) -> None:
    path = tmp_path / "scope.sqlite"
    created = _create(path)
    current = _store(path).load(created.conversation_id)["record"]
    grounding = grounding_receipt()

    def update(label: str):
        patch = dict(state_patch(current["turn_id"]))
        patch["turn_id"] = digest({"turn": label})
        return advance_authenticated_conversation_scope(
            store=_store(path), capability=capability(),
            repo_root=Path(__file__).resolve().parents[4],
            request=ConversationScopeAdvanceRequest(
                conversation_id=created.conversation_id, expected_revision=0,
                work_focus=FOCUS, grounding_receipt=grounding, state_patch=patch,
                expected_source_snapshot_id=SNAPSHOT_ID,
                expected_source_snapshot_digest=SNAPSHOT_DIGEST,
            ), now_epoch=NOW + 2,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(update, ("concurrent-a", "concurrent-b")))
    assert sum(result.accepted for result in results) == 1
    assert _store(path).load(created.conversation_id)["record"]["conversation_revision"] == 1


def test_database_unavailability_fails_closed() -> None:
    class BrokenAgentDb:
        @property
        def db(self):
            raise RuntimeError("database unavailable")

    result = create_authenticated_conversation_scope(
        store=AgentDbConversationScopeStore(BrokenAgentDb),
        capability=capability(), repo_root=Path(__file__).resolve().parents[4],
        request=ConversationScopeCreateRequest(
            work_focus=FOCUS, grounding_receipt=grounding_receipt(),
            discussion_foundup_ids=("trade",), conversation_nonce="database-failure",
            turn_id=digest({"turn": "db-failure"}), active_topic="TRADE runtime",
            current_objective="Remain fail closed.",
        ), now_epoch=NOW,
    )
    assert result.accepted is False
    assert "conversation_scope_store_unavailable" in result.rejection_reasons


def test_invented_repository_evidence_cannot_enter_scope(tmp_path: Path) -> None:
    result = _create(
        tmp_path / "scope.sqlite",
        accepted_decisions=(item("Unsupported claim.", "repository_fact"),),
        repository_evidence_refs=("invented/path.py:999",),
    )
    assert result.accepted is False
    assert "conversation_scope_input_invalid" in result.rejection_reasons


def _principal_values() -> dict[str, object]:
    return {
        "scope_kind": "principal",
        "work_focus": "Discuss the principal's cross-FoundUp operating principles.",
        "grounding_receipt": {},
        "discussion_foundup_ids": (),
        "active_topic": "Principal operating principles",
        "current_objective": "Clarify an operator preference without granting work authority.",
        "accepted_decisions": (item("Audit before implementation."),),
        "open_questions": (item("Which FoundUp should receive this principle?", "unresolved"),),
        "repository_evidence_refs": (),
        "source_snapshot_id": "",
        "source_snapshot_digest": "",
    }


def test_principal_scope_is_authenticated_durable_and_not_grounded(
    tmp_path: Path,
) -> None:
    path = tmp_path / "principal.sqlite"
    created = _create(path, **_principal_values())

    assert created.accepted is True
    assert created.projection["scope_kind"] == "principal"
    assert created.projection["authorized_foundup_id"] == ""
    assert created.projection["discussion_foundup_ids"] == []
    assert created.projection["repository_evidence_refs"] == []
    resumed = _resume(
        path,
        created.conversation_id,
        expected_head_sha="",
        expected_holoindex_generation_id="",
        expected_source_snapshot_id="",
        expected_source_snapshot_digest="",
    )
    assert resumed.accepted is True
    assert resumed.no_work_authority_granted is True


def test_principal_scope_advances_without_repository_authority(
    tmp_path: Path,
) -> None:
    path = tmp_path / "principal-advance.sqlite"
    created = _create(path, **_principal_values())
    current = _store(path).load(created.conversation_id)["record"]
    patch = {
        "turn_id": digest({"turn": "principal-second"}),
        "parent_turn_id": current["turn_id"],
        "discussion_foundup_ids": [],
        "active_topic": "Principal operating principles",
        "current_objective": "Preserve the clarified preference as conversation state.",
        "accepted_decisions": [item("Audit before implementation.")],
        "rejected_options": [],
        "open_questions": [],
        "repository_evidence_refs": [],
    }
    advanced = advance_authenticated_conversation_scope(
        store=_store(path),
        capability=capability(),
        repo_root=Path(__file__).resolve().parents[4],
        request=ConversationScopeAdvanceRequest(
            conversation_id=created.conversation_id,
            expected_revision=0,
            work_focus=str(_principal_values()["work_focus"]),
            grounding_receipt={},
            state_patch=patch,
            expected_source_snapshot_id="",
            expected_source_snapshot_digest="",
        ),
        now_epoch=NOW + 2,
    )
    assert advanced.accepted is True
    assert advanced.projection["scope_kind"] == "principal"


def test_nonfoundup_scope_rejects_grounding_and_kind_mutation(
    tmp_path: Path,
) -> None:
    values = _principal_values()
    values["grounding_receipt"] = grounding_receipt()
    assert _create(tmp_path / "grounded-principal.sqlite", **values).accepted is False

    path = tmp_path / "principal-kind.sqlite"
    created = _create(path, **_principal_values())
    current = _store(path).load(created.conversation_id)["record"]
    changed = advance_authenticated_conversation_scope(
        store=_store(path), capability=capability(),
        repo_root=Path(__file__).resolve().parents[4],
        request=ConversationScopeAdvanceRequest(
            conversation_id=created.conversation_id, expected_revision=0,
            work_focus=str(_principal_values()["work_focus"]), grounding_receipt={},
            state_patch={
                "scope_kind": "foundup",
                "turn_id": digest({"turn": "kind-change"}),
                "parent_turn_id": current["turn_id"],
                "discussion_foundup_ids": [],
                "active_topic": "Invalid mutation",
                "current_objective": "Attempt an authority promotion.",
                "repository_evidence_refs": [],
            },
            expected_source_snapshot_id="", expected_source_snapshot_digest="",
        ), now_epoch=NOW + 2,
    )
    assert changed.accepted is False
    assert "conversation_scope_input_invalid" in changed.rejection_reasons


def test_comparison_scope_requires_two_authorized_foundups_and_grants_no_union(
    tmp_path: Path,
) -> None:
    resolver = Resolver(foundup_scope=("trade", "gotjunk_001"))
    values = {
        **_principal_values(),
        "scope_kind": "comparison",
        "discussion_foundup_ids": ("trade", "gotjunk_001"),
        "_capability": capability(resolver=resolver),
    }
    created = _create(tmp_path / "comparison.sqlite", **values)
    assert created.accepted is True
    assert created.projection["scope_kind"] == "comparison"
    assert created.projection["authorized_foundup_id"] == ""
    work = prepare_conversation_work_context(
        store=_store(tmp_path / "comparison.sqlite"),
        capability=capability(resolver=resolver),
        conversation_id=created.conversation_id,
        expected_revision=0,
        resident_cycle={},
        now_epoch=NOW + 1,
    )
    assert work.accepted is False
    assert work.rejection_reasons == (
        "conversation_work_scope_kind_not_authorized",
    )

    one = {**values, "discussion_foundup_ids": ("trade",), "_capability": capability(resolver=resolver)}
    assert _create(tmp_path / "one.sqlite", **one).accepted is False
    outside = {
        **values,
        "_capability": capability(resolver=Resolver(foundup_scope=("trade",))),
    }
    assert _create(tmp_path / "outside.sqlite", **outside).accepted is False


def test_foundup_scope_rejects_extra_authorized_discussion_foundups(
    tmp_path: Path,
) -> None:
    resolver = Resolver(foundup_scope=("trade", "gotjunk_001"))
    created = _create(
        tmp_path / "widened-foundup.sqlite",
        discussion_foundup_ids=("trade", "gotjunk_001"),
        _capability=capability(resolver=resolver),
    )

    assert created.accepted is False
    assert "conversation_scope_access_denied" in created.rejection_reasons
    assert _store(tmp_path / "widened-foundup.sqlite").load(
        created.conversation_id
    )["record"] is None


def test_principal_scope_cannot_enter_conversation_work_promotion(
    tmp_path: Path,
) -> None:
    path = tmp_path / "principal-work.sqlite"
    created = _create(path, **_principal_values())
    result = prepare_conversation_work_context(
        store=_store(path),
        capability=capability(),
        conversation_id=created.conversation_id,
        expected_revision=0,
        resident_cycle={},
        now_epoch=NOW + 1,
    )
    assert result.accepted is False
    assert result.rejection_reasons == (
        "conversation_work_scope_kind_not_authorized",
    )
