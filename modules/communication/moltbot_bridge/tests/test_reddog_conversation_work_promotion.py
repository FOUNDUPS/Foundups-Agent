"""End-to-end guards for conversation-bound architect proposal promotion."""

from __future__ import annotations

import copy
import pickle
from datetime import datetime, timezone
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_architect_proposal_admission_contract import (
    validate_architect_proposal_executability_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_architect_proposal_executability_admission import (
    evaluate_architect_proposal_executability,
)
from modules.communication.moltbot_bridge.src.reddog_authenticated_conversation_scope_state import (
    advance_authenticated_conversation_scope,
    create_authenticated_conversation_scope,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_request import (
    ConversationScopeAdvanceRequest,
    ConversationScopeCreateRequest,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_store import (
    AgentDbConversationScopeStore,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_work_promotion import (
    AuthenticatedConversationWorkContext,
    VerifiedPendingConversationProposalCapability,
    commit_pending_conversation_work_proposal,
    consume_pending_conversation_proposal_capability,
    prepare_conversation_work_context,
    verify_pending_conversation_work_proposal,
)
from modules.communication.moltbot_bridge.src.reddog_backend_architect_determination_runtime import (
    ArchitectDeterminationReason,
    InMemoryArchitectDeterminationStore,
    run_reddog_backend_architect_determination_runtime,
)
from modules.communication.moltbot_bridge.tests.reddog_conversation_scope_test_support import (
    FOCUS,
    NOW,
    Resolver,
    TestAgentDb,
    capability,
    digest,
    grounding_receipt,
    item,
    state_patch,
)
from modules.communication.moltbot_bridge.tests.test_reddog_architect_fix_signed_wsp15_work_order_promotion import (
    _authority_profile,
    _determination,
    _memex_supply,
    _promote,
    _rebind_determination_admission,
)
from modules.communication.moltbot_bridge.tests.test_reddog_backend_architect_determination_runtime import (
    FakeArchitectRunner,
    _build_inputs,
    _model_output,
)
from modules.communication.moltbot_bridge.tests import (
    test_reddog_backend_architect_determination_runtime as backend_test,
)
from modules.communication.moltbot_bridge.tests.architect_proposal_test_helpers import (
    runtime_kwargs as _runtime_kwargs,
)
from modules.communication.moltbot_bridge.tests.architect_proposal_promotion_test_helpers import (
    build_proposal_runtime_inputs,
)
from modules.communication.moltbot_bridge.tests.test_reddog_architect_proposal_executability_admission import (
    _policy,
)
from modules.communication.moltbot_bridge.tests.holoindex_freshness_receipt_test_helpers import (
    build_fresh_holoindex_receipt,
)


ROOT = Path(__file__).resolve().parents[4]
FOUNDUP_ID = "trade"
SNAPSHOT_ID = "sha256:" + "8" * 64
SNAPSHOT_DIGEST = "sha256:" + "9" * 64


def _store(path: Path) -> AgentDbConversationScopeStore:
    return AgentDbConversationScopeStore(lambda: TestAgentDb(path))


def _grounding(admission: dict) -> dict:
    value = grounding_receipt()
    value.update(
        {
            "holoindex_repo_head_sha": admission["repo_head_sha"],
            "holoindex_generation_id": admission["holoindex_generation_id"],
            "holoindex_freshness_receipt_digest": admission[
                "holoindex_freshness_receipt_digest"
            ],
        }
    )
    value.pop("receipt_id", None)
    value["receipt_id"] = digest(value)
    return value


def _scope_and_cycle(path: Path, admission: dict):
    grounding = _grounding(admission)
    created = create_authenticated_conversation_scope(
        store=_store(path),
        capability=capability(resolver=Resolver(foundup_scope=(FOUNDUP_ID,))),
        repo_root=ROOT,
        request=ConversationScopeCreateRequest(
            work_focus=FOCUS,
            grounding_receipt=grounding,
            discussion_foundup_ids=(FOUNDUP_ID,),
            conversation_nonce="conversation-work-promotion",
            turn_id=digest({"turn": "proposal-source"}),
            active_topic="TRADE runtime",
            current_objective="Promote one exact grounded proposal.",
            accepted_decisions=(
                item("Use current repository evidence.", "repository_fact"),
            ),
            repository_evidence_refs=("code:trade",),
            source_snapshot_id=admission["snapshot_receipt_id"],
            source_snapshot_digest=admission["snapshot_content_digest"],
        ),
        now_epoch=NOW,
    )
    assert created.accepted is True
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
            {
                "schema_version": "reddog_resident_intent_binding.v1",
                "intent": intent,
            }
        ),
        "intent": intent,
        "snapshot_id": admission["snapshot_receipt_id"],
        "_store_integrity_valid": True,
    }
    return created, cycle


def _normalized_determination() -> dict:
    determination = _determination()
    current_head = grounding_receipt()["holoindex_repo_head_sha"]
    holo_receipt = build_fresh_holoindex_receipt(
        repo_root=ROOT,
        head_sha=current_head,
        generated_at="2026-07-16T00:00:00+00:00",
    )
    determination["snapshot_receipt_id"] = SNAPSHOT_ID
    determination["snapshot_content_digest"] = SNAPSHOT_DIGEST
    return _rebind_determination_admission(
        determination,
        {
            "snapshot_receipt_id": SNAPSHOT_ID,
            "snapshot_content_digest": SNAPSHOT_DIGEST,
            "repo_head_sha": current_head,
            "holoindex_generation_id": holo_receipt.generation_id,
            "holoindex_freshness_receipt_digest": digest(holo_receipt.to_dict()),
        },
    )


def _bound_determination(path: Path):
    determination = _normalized_determination()
    admission = determination["proposal_admission"]
    created, cycle = _scope_and_cycle(path, admission)
    context_result = prepare_conversation_work_context(
        store=_store(path),
        capability=capability(),
        conversation_id=created.conversation_id,
        expected_revision=0,
        resident_cycle=cycle,
        now_epoch=NOW + 1,
    )
    assert context_result.accepted is True
    binding = context_result.binding.to_dict()
    updates = {
        "conversation_binding_present": True,
        **{key: value for key, value in binding.items() if key != "schema_version"},
    }
    rebound = _rebind_determination_admission(determination, updates)
    return created, cycle, context_result, rebound


def _promotion_authority_inputs(determination: dict) -> tuple[dict, dict]:
    admission = determination["proposal_admission"]
    return (
        _authority_profile(foundup_id=FOUNDUP_ID),
        _memex_supply(
            foundup_id=FOUNDUP_ID,
            snapshot_receipt_id=admission["snapshot_receipt_id"],
            snapshot_content_digest=admission["snapshot_content_digest"],
            holoindex_generation_id=admission["holoindex_generation_id"],
            policy_issued_at=datetime.fromtimestamp(
                NOW - 10, timezone.utc
            ).isoformat(),
            policy_expires_at=datetime.fromtimestamp(
                NOW + 590, timezone.utc
            ).isoformat(),
        ),
    )


def _promote_bound(determination: dict, **overrides):
    admission = determination["proposal_admission"]
    profile, memex = _promotion_authority_inputs(determination)
    holo_receipt = build_fresh_holoindex_receipt(
        repo_root=ROOT,
        head_sha=admission["repo_head_sha"],
        generated_at="2026-07-16T00:00:00+00:00",
    )
    args = {
        "architect_determination": determination,
        "authority_profile": profile,
        "memex_supply_receipt": memex,
        "current_repo_head_sha": admission["repo_head_sha"],
        "current_holoindex_receipt": holo_receipt,
        "now_iso": datetime.fromtimestamp(NOW + 3, timezone.utc).isoformat(),
        "_test_now_epoch": NOW + 3,
    }
    args.update(overrides)
    return _promote(**args)


def test_context_binds_exact_scope_intent_and_proposal_preview(tmp_path: Path) -> None:
    path = tmp_path / "conversation.sqlite"
    created, _, context_result, determination = _bound_determination(path)

    committed = commit_pending_conversation_work_proposal(
        context=context_result.context,
        architect_determination=determination,
        now_epoch=NOW + 2,
    )

    assert committed.accepted is True
    assert committed.conversation_revision == 1
    assert committed.projection["pending_work_proposal_id"] == (
        determination["proposal_admission"]["receipt_id"]
    )
    assert committed.no_work_authority_granted is True
    assert committed.no_worker_dispatch_performed is True
    assert created.conversation_id == committed.conversation_id


def test_pending_capability_is_required_for_promotion(tmp_path: Path) -> None:
    path = tmp_path / "conversation.sqlite"
    _, _, context_result, determination = _bound_determination(path)
    committed = commit_pending_conversation_work_proposal(
        context=context_result.context,
        architect_determination=determination,
        now_epoch=NOW + 2,
    )
    assert committed.accepted is True

    rejected, _ = _promote_bound(determination)
    assert rejected.accepted is False
    assert any("CONVERSATION_PROPOSAL_AUTHORITY" in reason for reason in rejected.rejection_reasons)


def test_bad_signature_does_not_consume_one_use_pending_capability(
    tmp_path: Path,
) -> None:
    path = tmp_path / "conversation.sqlite"
    _, _, context_result, determination = _bound_determination(path)
    committed = commit_pending_conversation_work_proposal(
        context=context_result.context,
        architect_determination=determination,
        now_epoch=NOW + 2,
    )
    assert committed.accepted is True
    pending = verify_pending_conversation_work_proposal(
        store=_store(path),
        capability=capability(),
        architect_determination=determination,
        now_epoch=NOW + 3,
    )
    profile, memex = _promotion_authority_inputs(determination)
    attestation, runtime_config, resolver = build_proposal_runtime_inputs(
        determination,
        profile,
        memex,
        now_epoch=NOW + 3,
    )
    forged = dict(attestation)
    forged["signature"] = "forged"
    bad_signature, _ = _promote_bound(
        determination,
        pending_conversation_proposal_capability=pending,
        authority_profile=profile,
        memex_supply_receipt=memex,
        proposal_authenticity_attestation=forged,
        signer_runtime_config=runtime_config,
        principal_key_resolver=resolver,
    )
    assert bad_signature.accepted is False
    assert any(
        "PROPOSAL_AUTHENTICITY" in reason
        for reason in bad_signature.rejection_reasons
    )
    accepted, _ = _promote_bound(
        determination,
        pending_conversation_proposal_capability=pending,
    )
    assert accepted.accepted is True
    assert consume_pending_conversation_proposal_capability(
        pending,
        proposal_admission=determination["proposal_admission"],
        now_epoch=NOW + 3,
    ) is False


def test_tampered_binding_and_stale_context_fail_without_pending_state(tmp_path: Path) -> None:
    path = tmp_path / "conversation.sqlite"
    created, cycle, context_result, determination = _bound_determination(path)
    tampered = _rebind_determination_admission(
        determination,
        {"authorized_foundup_id": "gotjunk_001"},
    )
    result = commit_pending_conversation_work_proposal(
        context=context_result.context,
        architect_determination=tampered,
        now_epoch=NOW + 2,
    )
    assert result.accepted is False
    assert not _store(path).load(created.conversation_id)["record"][
        "pending_work_proposal_id"
    ]

    fresh = prepare_conversation_work_context(
        store=_store(path), capability=capability(),
        conversation_id=created.conversation_id, expected_revision=0,
        resident_cycle=cycle, now_epoch=NOW + 3,
    )
    current = _store(path).load(created.conversation_id)["record"]
    advance_authenticated_conversation_scope(
        store=_store(path), capability=capability(), repo_root=ROOT,
        request=ConversationScopeAdvanceRequest(
            conversation_id=created.conversation_id, expected_revision=0,
            work_focus=FOCUS, grounding_receipt=cycle["intent"]["grounding_receipt"],
            state_patch=state_patch(current["turn_id"]),
            expected_source_snapshot_id=determination["snapshot_receipt_id"],
            expected_source_snapshot_digest=determination["snapshot_content_digest"],
        ), now_epoch=NOW + 4,
    )
    stale = commit_pending_conversation_work_proposal(
        context=fresh.context,
        architect_determination=determination,
        now_epoch=NOW + 5,
    )
    assert stale.accepted is False
    assert "conversation_work_scope_changed" in stale.rejection_reasons


def test_cross_foundup_profile_rejects_without_consuming_pending_capability(
    tmp_path: Path,
) -> None:
    path = tmp_path / "conversation.sqlite"
    _, _, prepared, determination = _bound_determination(path)
    committed = commit_pending_conversation_work_proposal(
        context=prepared.context,
        architect_determination=determination,
        now_epoch=NOW + 2,
    )
    assert committed.accepted is True
    pending = verify_pending_conversation_work_proposal(
        store=_store(path),
        capability=capability(),
        architect_determination=determination,
        now_epoch=NOW + 3,
    )
    _, memex = _promotion_authority_inputs(determination)
    wrong_profile = _authority_profile(foundup_id="gotjunk_001")
    wrong_memex = dict(memex)
    wrong_memex.pop("receipt_id")
    wrong_memex["foundup_id"] = "gotjunk_001"
    wrong_memex = _memex_supply(**wrong_memex)
    attestation, runtime_config, resolver = build_proposal_runtime_inputs(
        determination,
        wrong_profile,
        wrong_memex,
        now_epoch=NOW + 3,
    )
    rejected, _ = _promote_bound(
        determination,
        authority_profile=wrong_profile,
        memex_supply_receipt=wrong_memex,
        proposal_authenticity_attestation=attestation,
        signer_runtime_config=runtime_config,
        principal_key_resolver=resolver,
        pending_conversation_proposal_capability=pending,
    )
    assert rejected.accepted is False
    assert any(
        "CONVERSATION_PROPOSAL_AUTHORITY" in reason
        for reason in rejected.rejection_reasons
    )
    accepted, _ = _promote_bound(
        determination,
        pending_conversation_proposal_capability=pending,
    )
    assert accepted.accepted is True


def test_concurrent_preview_contexts_allow_one_cas_commit(tmp_path: Path) -> None:
    path = tmp_path / "conversation.sqlite"
    created, cycle, first, determination = _bound_determination(path)
    second = prepare_conversation_work_context(
        store=_store(path),
        capability=capability(),
        conversation_id=created.conversation_id,
        expected_revision=0,
        resident_cycle=cycle,
        now_epoch=NOW + 1,
    )
    first_result = commit_pending_conversation_work_proposal(
        context=first.context,
        architect_determination=determination,
        now_epoch=NOW + 2,
    )
    second_result = commit_pending_conversation_work_proposal(
        context=second.context,
        architect_determination=determination,
        now_epoch=NOW + 2,
    )
    assert first_result.accepted is True
    assert second_result.accepted is False
    assert second_result.rejection_reasons == ("conversation_work_scope_changed",)


def test_resident_cycle_principal_foundup_snapshot_and_digest_are_required(
    tmp_path: Path,
) -> None:
    determination = _normalized_determination()
    admission = determination["proposal_admission"]
    created, cycle = _scope_and_cycle(tmp_path / "conversation.sqlite", admission)
    for updates in (
        {"_store_integrity_valid": False},
        {"snapshot_id": digest({"snapshot": "wrong"})},
        {"intent_digest": digest({"intent": "forged"})},
        {"intent": {**cycle["intent"], "principal_id": "other"}},
        {"intent": {**cycle["intent"], "foundup_id": "gotjunk_001"}},
    ):
        result = prepare_conversation_work_context(
            store=_store(tmp_path / "conversation.sqlite"),
            capability=capability(), conversation_id=created.conversation_id,
            expected_revision=0, resident_cycle={**cycle, **updates},
            now_epoch=NOW + 1,
        )
        assert result.accepted is False


def test_ordinary_conversation_advance_invalidates_pending_preview(tmp_path: Path) -> None:
    path = tmp_path / "conversation.sqlite"
    created, cycle, context_result, determination = _bound_determination(path)
    committed = commit_pending_conversation_work_proposal(
        context=context_result.context,
        architect_determination=determination,
        now_epoch=NOW + 2,
    )
    current = _store(path).load(created.conversation_id)["record"]
    advanced = advance_authenticated_conversation_scope(
        store=_store(path), capability=capability(), repo_root=ROOT,
        request=ConversationScopeAdvanceRequest(
            conversation_id=created.conversation_id, expected_revision=1,
            work_focus=FOCUS, grounding_receipt=cycle["intent"]["grounding_receipt"],
            state_patch=state_patch(current["turn_id"]),
            expected_source_snapshot_id=determination["snapshot_receipt_id"],
            expected_source_snapshot_digest=determination["snapshot_content_digest"],
        ), now_epoch=NOW + 3,
    )
    assert committed.accepted and advanced.accepted
    assert advanced.projection["pending_work_proposal_id"] == ""
    assert verify_pending_conversation_work_proposal(
        store=_store(path), capability=capability(),
        architect_determination=determination, now_epoch=NOW + 4,
    ) is None


def test_admission_evaluator_binds_context_and_rejects_rehash_tamper() -> None:
    inputs = _build_inputs()
    binding_body = {
        "schema_version": "reddog_conversation_work_binding.v1",
        "conversation_id": digest({"conversation": 1}),
        "conversation_revision": 2,
        "conversation_revision_receipt_id": digest({"revision": 2}),
        "conversation_scope_record_digest": digest({"record": 2}),
        "authorized_foundup_id": "trade",
        "resident_intent_id": digest({"intent": 2}),
        "resident_intent_digest": digest({"intent-body": 2}),
        "conversation_grounding_receipt_id": digest({"grounding": 2}),
        "snapshot_receipt_id": inputs["snapshot"].snapshot_receipt_id,
        "snapshot_content_digest": inputs["snapshot"].snapshot_content_digest,
        "repo_head_sha": inputs["snapshot"].repo_state["head_sha"],
        "holoindex_generation_id": inputs["snapshot"].holoindex_state[
            "generation_id"
        ],
        "holoindex_freshness_receipt_digest": inputs["snapshot"].holoindex_state[
            "receipt_digest"
        ],
    }
    binding = {
        **binding_body,
        "conversation_binding_digest": digest(binding_body),
    }
    output = _model_output(
        inputs["allocation"], inputs["reports"][0]["evidence_refs"][0]
    )
    receipt = evaluate_architect_proposal_executability(
        model_output=output, snapshot=inputs["snapshot"],
        reports=inputs["reports"],
        report_bundle_id=inputs["report_collection"].validation.bundle.bundle_id,
        wsp15_allocation_receipt=inputs["allocation"], policy=_policy(),
        conversation_binding=binding,
    )
    assert receipt.conversation_binding_present is True
    assert validate_architect_proposal_executability_receipt(receipt.to_dict()) == receipt
    tampered = receipt.to_dict()
    tampered["authorized_foundup_id"] = "gotjunk_001"
    tampered.pop("receipt_id")
    tampered["receipt_id"] = digest(tampered)
    try:
        validate_architect_proposal_executability_receipt(tampered)
    except ValueError:
        pass
    else:
        raise AssertionError("self-rehashed conversation binding was accepted")


def test_context_capability_cannot_be_constructed_or_replayed(tmp_path: Path) -> None:
    path = tmp_path / "conversation.sqlite"
    _, _, context_result, determination = _bound_determination(path)
    first = commit_pending_conversation_work_proposal(
        context=context_result.context,
        architect_determination=determination,
        now_epoch=NOW + 2,
    )
    second = commit_pending_conversation_work_proposal(
        context=context_result.context,
        architect_determination=determination,
        now_epoch=NOW + 3,
    )
    assert first.accepted is True
    assert second.accepted is False
    assert "invalid_or_replayed" in second.rejection_reasons[0]


def _backend_case(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    current_head = grounding_receipt()["holoindex_repo_head_sha"]
    monkeypatch.setattr(backend_test, "HEAD", current_head)
    inputs = _build_inputs()
    snapshot = inputs["snapshot"]
    source = {
        "snapshot_receipt_id": snapshot.snapshot_receipt_id,
        "snapshot_content_digest": snapshot.snapshot_content_digest,
        "repo_head_sha": snapshot.repo_state["head_sha"],
        "holoindex_generation_id": snapshot.holoindex_state["generation_id"],
        "holoindex_freshness_receipt_digest": snapshot.holoindex_state[
            "receipt_digest"
        ],
    }
    created, cycle = _scope_and_cycle(tmp_path / "conversation.sqlite", source)
    prepared = prepare_conversation_work_context(
        store=_store(tmp_path / "conversation.sqlite"),
        capability=capability(),
        conversation_id=created.conversation_id,
        expected_revision=0,
        resident_cycle=cycle,
        now_epoch=NOW + 1,
    )
    evidence_ref = inputs["reports"][0]["evidence_refs"][0]
    runner = FakeArchitectRunner(
        _model_output(inputs["allocation"], evidence_ref)
    )
    return inputs, created, prepared, runner, evidence_ref


def test_backend_accepts_current_authenticated_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs, created, prepared, runner, _ = _backend_case(tmp_path, monkeypatch)
    accepted = run_reddog_backend_architect_determination_runtime(
        **_runtime_kwargs(inputs),
        wsp15_allocation_receipt=inputs["allocation"],
        store=InMemoryArchitectDeterminationStore(),
        model_runner=runner,
        now_iso=backend_test.NOW,
        conversation_work_context=prepared.context,
    )
    assert accepted.accepted is True
    assert accepted.receipt.proposal_admission.conversation_binding_present is True
    assert runner.calls[0]["binding"]["conversation_work_binding"][
        "conversation_id"
    ] == created.conversation_id
    assert "accepted_decisions" not in runner.calls[0]["context"]


def test_backend_rejects_fake_context_before_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs, _, _, _, evidence_ref = _backend_case(tmp_path, monkeypatch)
    fake_runner = FakeArchitectRunner(
        _model_output(inputs["allocation"], evidence_ref)
    )
    rejected = run_reddog_backend_architect_determination_runtime(
        **_runtime_kwargs(inputs),
        wsp15_allocation_receipt=inputs["allocation"],
        store=InMemoryArchitectDeterminationStore(),
        model_runner=fake_runner,
        now_iso=backend_test.NOW,
        conversation_work_context=object(),
    )
    assert rejected.accepted is False
    assert ArchitectDeterminationReason.CONVERSATION_CONTEXT_INVALID in (
        rejected.rejection_reasons
    )
    assert fake_runner.calls == []


def test_opaque_capabilities_reject_construction_copy_and_pickle(
    tmp_path: Path,
) -> None:
    for capability_type in (
        AuthenticatedConversationWorkContext,
        VerifiedPendingConversationProposalCapability,
    ):
        with pytest.raises(TypeError):
            capability_type()

    path = tmp_path / "conversation.sqlite"
    _, _, prepared, _ = _bound_determination(path)
    for operation in (copy.copy, copy.deepcopy, pickle.dumps):
        with pytest.raises(TypeError):
            operation(prepared.context)


def test_pending_capability_rejects_after_scope_changes(tmp_path: Path) -> None:
    path = tmp_path / "conversation.sqlite"
    created, cycle, prepared, determination = _bound_determination(path)
    committed = commit_pending_conversation_work_proposal(
        context=prepared.context,
        architect_determination=determination,
        now_epoch=NOW + 2,
    )
    assert committed.accepted is True
    pending = verify_pending_conversation_work_proposal(
        store=_store(path),
        capability=capability(),
        architect_determination=determination,
        now_epoch=NOW + 3,
    )
    current = _store(path).load(created.conversation_id)["record"]
    advanced = advance_authenticated_conversation_scope(
        store=_store(path),
        capability=capability(),
        repo_root=ROOT,
        request=ConversationScopeAdvanceRequest(
            conversation_id=created.conversation_id,
            expected_revision=1,
            work_focus=FOCUS,
            grounding_receipt=cycle["intent"]["grounding_receipt"],
            state_patch=state_patch(current["turn_id"]),
            expected_source_snapshot_id=determination["snapshot_receipt_id"],
            expected_source_snapshot_digest=determination[
                "snapshot_content_digest"
            ],
        ),
        now_epoch=NOW + 4,
    )
    assert advanced.accepted is True
    assert consume_pending_conversation_proposal_capability(
        pending,
        proposal_admission=determination["proposal_admission"],
        now_epoch=NOW + 4,
    ) is False
