"""Tests for FOUNDUP_MEMEX_LEARNING_CANDIDATE_GATE_PHASE1."""

from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.foundup_memex_current_state import (
    assemble_foundup_memex_current_state,
)
from modules.communication.moltbot_bridge.src.foundup_memex_learning_candidate import (
    GATE_ACCEPTED,
    GATE_REJECTED,
    build_foundup_memex_learning_evidence,
    build_foundup_memex_learning_proposal,
    gate_foundup_memex_learning_candidates,
    verify_foundup_memex_learning_candidate_reconstruction,
)
from modules.communication.moltbot_bridge.src.foundup_memex_learning_candidate_contract import (
    MAX_REFERENCES_PER_PROPOSAL,
    MAX_STATEMENT_CHARS,
    MAX_SUPERSEDED_MEMORIES,
)
from modules.communication.moltbot_bridge.src.reddog_operational_context_snapshot import (
    build_operational_context_snapshot,
)
from modules.communication.moltbot_bridge.tests.holoindex_freshness_receipt_test_helpers import (
    build_fresh_holoindex_receipt,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
SOURCE_PATH = REPO_ROOT / "modules/communication/moltbot_bridge/src/foundup_memex_learning_candidate.py"
CONTRACT_PATH = REPO_ROOT / "modules/communication/moltbot_bridge/src/foundup_memex_learning_candidate_contract.py"
FOUNDUP_ID = "foundups-agent"
HEAD = "52e98c6652b3c8eb0818d2ec6718c005c7e55c79"
OBSERVED_AT = "2026-08-23T00:00:00+00:00"
GATE_TIME = "2026-08-23T00:01:00+00:00"


def _sha(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _digest(value) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


class _ExplodingDeepcopy:
    def __deepcopy__(self, _memo):
        raise RuntimeError("deepcopy must not execute")


class _ExplodingIterMapping(dict):
    def __iter__(self):
        raise RuntimeError("mapping iteration must fail closed")


def _view(*, outcomes=()):
    snapshot_result = build_operational_context_snapshot(
        repo_state={
            "head_sha": HEAD,
            "dirty_paths": (),
            "dirty_digest": _sha("clean"),
            "worktree_digest": _sha("worktrees"),
        },
        work_state_snapshot={
            "schema_version": "reddog_authoritative_work_state.v1",
            "revision": _sha("work-state"),
            "selected_slice": "FOUNDUP_MEMEX_LEARNING_CANDIDATE_GATE_PHASE1",
            "worker_claims": (),
            "wre_queue_items": (),
        },
        holoindex_receipt=build_fresh_holoindex_receipt(
            repo_root=REPO_ROOT,
            head_sha=HEAD,
            generated_at=OBSERVED_AT,
        ),
        changed_paths=[str(SOURCE_PATH.relative_to(REPO_ROOT)).replace("\\", "/")],
        now_iso=OBSERVED_AT,
        breadcrumbs=[
            {
                "breadcrumb_id": "breadcrumb-1",
                "continuity_id": FOUNDUP_ID,
                "task_id": "learning-candidate-poc",
                "timestamp": OBSERVED_AT,
            }
        ],
        breadcrumb_scope=FOUNDUP_ID,
        brain_state={
            "available": True,
            "signature_digest": _sha("brain"),
            "repo_head_sha": HEAD,
            "work_state_revision": _sha("work-state"),
        },
    )
    assert snapshot_result.accepted and snapshot_result.snapshot is not None
    result = assemble_foundup_memex_current_state(
        foundup_id=FOUNDUP_ID,
        snapshot=snapshot_result.snapshot,
        identity={
            "foundup_id": FOUNDUP_ID,
            "name": "Foundups Agent",
            "stage": "POC",
            "purpose": "Build governed FoundUp cognition.",
        },
        roadmap_state={
            "foundup_id": FOUNDUP_ID,
            "roadmap_id": "foundups-agent-roadmap",
            "version": "phase1",
            "content_digest": _sha("roadmap"),
            "active_item_ids": ("FOUNDUP_MEMEX_LEARNING_CANDIDATE_GATE_PHASE1",),
            "blocked_item_ids": (),
        },
        verified_outcomes=outcomes,
        now_iso=GATE_TIME,
        resident_mode=False,
        legacy_single_foundup_compatibility=True,
        policy_foundup_scope=(FOUNDUP_ID,),
    )
    assert result.accepted and result.view is not None
    return result.view


def _breadcrumb_evidence(view, *, polarity: str, statement: str):
    receipt = view.source_receipts["breadcrumbs"]
    return build_foundup_memex_learning_evidence(
        foundup_id=FOUNDUP_ID,
        snapshot_id=view.snapshot_id,
        source_class="breadcrumbs",
        source_receipt_id=receipt["content_digest"],
        source_revision=receipt["source_version"],
        observed_at=OBSERVED_AT,
        statement=statement,
        polarity=polarity,
    )


def _proposal(view, supporting, *, contradicting=(), supersedes=()):
    return build_foundup_memex_learning_proposal(
        foundup_id=FOUNDUP_ID,
        snapshot_id=view.snapshot_id,
        category="observed_pattern",
        statement="Repeated verified outcomes justify a candidate pattern.",
        supporting_evidence_ids=tuple(item.evidence_id for item in supporting),
        contradicting_evidence_ids=tuple(item.evidence_id for item in contradicting),
        supersedes_memory_ids=supersedes,
        proposed_salience=0.75,
        proposed_confidence=0.65,
        created_at=GATE_TIME,
    )


def test_gate_emits_deterministic_read_only_candidate_with_contradiction() -> None:
    view = _view()
    support = _breadcrumb_evidence(
        view, polarity="supporting", statement="The pattern passed two verified trials."
    )
    contradiction = _breadcrumb_evidence(
        view, polarity="contradicting", statement="One environment still contradicts the pattern."
    )
    proposal = _proposal(
        view,
        (support,),
        contradicting=(contradiction,),
        supersedes=(_sha("older-memory"),),
    )

    first = gate_foundup_memex_learning_candidates(
        view=view,
        evidence=(contradiction, support),
        proposals=(proposal,),
        created_at=GATE_TIME,
    )
    second = gate_foundup_memex_learning_candidates(
        view=view,
        evidence=(support, contradiction),
        proposals=(proposal,),
        created_at=GATE_TIME,
    )

    assert first.accepted is True and first.status == GATE_ACCEPTED
    assert first.to_dict() == second.to_dict()
    assert first.receipt["receipt_id"] == second.receipt["receipt_id"]
    with pytest.raises(TypeError):
        first.receipt["status"] = GATE_REJECTED
    candidate = first.candidates[0]
    assert candidate.contradicting_evidence_ids == (contradiction.evidence_id,)
    assert candidate.supersedes_memory_ids == (_sha("older-memory"),)
    assert candidate.runtime_admissible is False
    assert candidate.brain_write_authorized is False
    assert verify_foundup_memex_learning_candidate_reconstruction(
        candidate, proposal, (support, contradiction)
    )
    assert all(
        (
            first.no_persistence_performed,
            first.no_brain_write_performed,
            first.no_breadcrumb_write_performed,
            first.no_holoindex_mutation_performed,
            first.no_roadmap_mutation_performed,
            first.no_work_authority_granted,
        )
    )


def test_unbound_receipt_and_cross_foundup_scope_fail_closed() -> None:
    view = _view()
    evidence = build_foundup_memex_learning_evidence(
        foundup_id="other-foundup",
        snapshot_id=view.snapshot_id,
        source_class="breadcrumbs",
        source_receipt_id=_sha("forged-receipt"),
        source_revision=view.source_receipts["breadcrumbs"]["source_version"],
        observed_at=OBSERVED_AT,
        statement="Foreign evidence must not cross the FoundUp boundary.",
        polarity="supporting",
    )
    proposal = build_foundup_memex_learning_proposal(
        foundup_id="other-foundup",
        snapshot_id=view.snapshot_id,
        category="observed_pattern",
        statement="This proposal is outside the active FoundUp scope.",
        supporting_evidence_ids=(evidence.evidence_id,),
        proposed_salience=0.5,
        proposed_confidence=0.5,
        created_at=GATE_TIME,
    )

    result = gate_foundup_memex_learning_candidates(
        view=view, evidence=(evidence,), proposals=(proposal,), created_at=GATE_TIME
    )

    assert result.accepted is False and result.status == GATE_REJECTED
    assert result.candidates == ()
    assert "learning_evidence_scope_mismatch" in result.rejection_reasons
    assert "learning_proposal_scope_mismatch" in result.rejection_reasons
    assert result.receipt["brain_write_authorized"] is False


def test_governed_research_fails_closed_without_authenticated_authority() -> None:
    view = _view()
    research_receipt = _sha("governed-research")
    evidence = build_foundup_memex_learning_evidence(
        foundup_id=FOUNDUP_ID,
        snapshot_id=view.snapshot_id,
        source_class="governed_research",
        source_receipt_id=research_receipt,
        source_revision="research-corpus-v1",
        observed_at=OBSERVED_AT,
        statement="A governed external study supports the proposed pattern.",
        polarity="supporting",
    )
    proposal = _proposal(view, (evidence,))

    blocked = gate_foundup_memex_learning_candidates(
        view=view, evidence=(evidence,), proposals=(proposal,), created_at=GATE_TIME
    )
    caller_asserted = gate_foundup_memex_learning_candidates(
        view=view,
        evidence=(evidence,),
        proposals=(proposal,),
        created_at=GATE_TIME,
        governed_research_receipt_ids=(research_receipt,),
    )

    assert blocked.accepted is False
    assert blocked.rejection_reasons == (
        "learning_evidence_governed_research_authority_unavailable",
    )
    assert caller_asserted.accepted is False
    assert caller_asserted.rejection_reasons == blocked.rejection_reasons


def test_verified_outcome_evidence_binds_to_exact_outcome_and_head() -> None:
    outcome_digest = _sha("verified-outcome")
    view = _view(
        outcomes=(
            {
                "foundup_id": FOUNDUP_ID,
                "outcome_id": _sha("outcome-id"),
                "verification_receipt_id": _sha("verification"),
                "held_out_receipt_id": _sha("held-out"),
                "head_sha": HEAD,
                "accepted": True,
                "held_out_passed": True,
                "content_digest": outcome_digest,
            },
        )
    )
    evidence = build_foundup_memex_learning_evidence(
        foundup_id=FOUNDUP_ID,
        snapshot_id=view.snapshot_id,
        source_class="verified_outcome",
        source_receipt_id=outcome_digest,
        source_revision=HEAD,
        observed_at=OBSERVED_AT,
        statement="The held-out verified outcome supports the learned result.",
        polarity="supporting",
    )
    result = gate_foundup_memex_learning_candidates(
        view=view,
        evidence=(evidence,),
        proposals=(_proposal(view, (evidence,)),),
        created_at=GATE_TIME,
    )
    wrong_head = gate_foundup_memex_learning_candidates(
        view=view,
        evidence=(replace(evidence, source_revision="0" * 40),),
        proposals=(_proposal(view, (evidence,)),),
        created_at=GATE_TIME,
    )

    assert result.accepted is True
    assert wrong_head.accepted is False


def test_verified_outcome_receipt_collision_is_ambiguous_and_rejected() -> None:
    shared_digest = _sha("shared-verified-outcome")
    outcomes = tuple(
        {
            "foundup_id": FOUNDUP_ID,
            "outcome_id": _sha(f"outcome-{index}"),
            "verification_receipt_id": _sha(f"verification-{index}"),
            "held_out_receipt_id": _sha(f"held-out-{index}"),
            "head_sha": HEAD,
            "accepted": True,
            "held_out_passed": True,
            "content_digest": shared_digest,
        }
        for index in range(2)
    )
    view = _view(outcomes=outcomes)
    evidence = build_foundup_memex_learning_evidence(
        foundup_id=FOUNDUP_ID,
        snapshot_id=view.snapshot_id,
        source_class="verified_outcome",
        source_receipt_id=shared_digest,
        source_revision=HEAD,
        observed_at=OBSERVED_AT,
        statement="A colliding receipt cannot identify one outcome.",
        polarity="supporting",
    )
    result = gate_foundup_memex_learning_candidates(
        view=view,
        evidence=(evidence,),
        proposals=(_proposal(view, (evidence,)),),
        created_at=GATE_TIME,
    )

    assert result.accepted is False
    assert "learning_evidence_receipt_ambiguous" in result.rejection_reasons


def test_reconstruction_rejects_tampered_candidate_or_evidence() -> None:
    view = _view()
    evidence = _breadcrumb_evidence(
        view, polarity="supporting", statement="Original evidence remains reconstructable."
    )
    result = gate_foundup_memex_learning_candidates(
        view=view,
        evidence=(evidence,),
        proposals=(_proposal(view, (evidence,)),),
        created_at=GATE_TIME,
    )
    candidate = result.candidates[0]

    assert not verify_foundup_memex_learning_candidate_reconstruction(
        replace(candidate, evidence_manifest_digest=_sha("forged")),
        _proposal(view, (evidence,)),
        (evidence,),
    )
    assert not verify_foundup_memex_learning_candidate_reconstruction(
        candidate,
        _proposal(view, (evidence,)),
        (replace(evidence, statement="tampered"),),
    )


def test_reconstruction_is_bound_to_original_proposal_not_local_resigning() -> None:
    view = _view()
    evidence = _breadcrumb_evidence(
        view, polarity="supporting", statement="Original evidence remains authoritative."
    )
    proposal = _proposal(view, (evidence,))
    result = gate_foundup_memex_learning_candidates(
        view=view, evidence=(evidence,), proposals=(proposal,), created_at=GATE_TIME
    )
    candidate = result.candidates[0]
    altered = replace(candidate, statement="Locally rewritten candidate statement.")
    altered_payload = altered.to_dict()
    altered_payload.pop("candidate_id")
    altered = replace(altered, candidate_id=_digest(altered_payload))

    assert verify_foundup_memex_learning_candidate_reconstruction(
        candidate, proposal, (evidence,)
    )
    assert not verify_foundup_memex_learning_candidate_reconstruction(
        altered, proposal, (evidence,)
    )


def test_builders_emit_one_canonical_text_time_and_score_representation() -> None:
    view = _view()
    receipt = view.source_receipts["breadcrumbs"]
    evidence = build_foundup_memex_learning_evidence(
        foundup_id=FOUNDUP_ID,
        snapshot_id=view.snapshot_id,
        source_class="breadcrumbs",
        source_receipt_id=receipt["content_digest"],
        source_revision=receipt["source_version"],
        observed_at="2026-08-23T09:00:00+09:00",
        statement="  Repeated\u00a0outcome  ",
        polarity="supporting",
    )
    proposal = build_foundup_memex_learning_proposal(
        foundup_id=FOUNDUP_ID,
        snapshot_id=view.snapshot_id,
        category="observed_pattern",
        statement="  Fullwidth \uff21 normalizes.  ",
        supporting_evidence_ids=(evidence.evidence_id,),
        proposed_salience=0,
        proposed_confidence=1,
        created_at="2026-08-23T00:01:00+00:00",
    )

    assert evidence.observed_at == "2026-08-23T00:00:00Z"
    assert evidence.statement == "Repeated outcome"
    assert proposal.statement == "Fullwidth A normalizes."
    assert type(proposal.proposed_salience) is float
    assert type(proposal.proposed_confidence) is float
    assert proposal.created_at == "2026-08-23T00:01:00Z"

    with pytest.raises(ValueError, match="learning_identifier_not_canonical"):
        build_foundup_memex_learning_evidence(
            foundup_id=f" {FOUNDUP_ID}",
            snapshot_id=view.snapshot_id,
            source_class="breadcrumbs",
            source_receipt_id=receipt["content_digest"],
            source_revision=receipt["source_version"],
            observed_at=OBSERVED_AT,
            statement="Authority identifiers are never silently normalized.",
            polarity="supporting",
        )


def test_proposal_reference_and_supersession_inputs_are_bounded_before_dedup() -> None:
    view = _view()
    evidence = _breadcrumb_evidence(view, polarity="supporting", statement="Bounded input.")
    common = {
        "foundup_id": FOUNDUP_ID,
        "snapshot_id": view.snapshot_id,
        "category": "observed_pattern",
        "statement": "Oversized reference lists fail before normalization.",
        "proposed_salience": 0.5,
        "proposed_confidence": 0.5,
        "created_at": GATE_TIME,
    }
    with pytest.raises(ValueError, match="learning_sequence_count_invalid"):
        build_foundup_memex_learning_proposal(
            **common,
            supporting_evidence_ids=(evidence.evidence_id,) * (MAX_REFERENCES_PER_PROPOSAL + 1),
        )
    with pytest.raises(ValueError, match="learning_sequence_count_invalid"):
        build_foundup_memex_learning_proposal(
            **common,
            supporting_evidence_ids=(evidence.evidence_id,),
            supersedes_memory_ids=(_sha("old"),) * (MAX_SUPERSEDED_MEMORIES + 1),
        )


def test_view_requires_exact_invariants_and_assembly_receipt_identity() -> None:
    view = _view()
    evidence = _breadcrumb_evidence(view, polarity="supporting", statement="Scoped evidence.")
    proposal = _proposal(view, (evidence,))
    extra_invariant = replace(view, invariants={**view.invariants, "caller_asserted": True})
    tampered_receipt = dict(view.assembly_receipt)
    tampered_receipt["receipt_id"] = _sha("caller-resigned")
    bad_receipt = replace(view, assembly_receipt=tampered_receipt)

    extra_result = gate_foundup_memex_learning_candidates(
        view=extra_invariant, evidence=(evidence,), proposals=(proposal,), created_at=GATE_TIME
    )
    receipt_result = gate_foundup_memex_learning_candidates(
        view=bad_receipt, evidence=(evidence,), proposals=(proposal,), created_at=GATE_TIME
    )

    assert extra_result.accepted is False
    assert "learning_gate_view_invalid" in extra_result.rejection_reasons
    assert receipt_result.accepted is False
    assert "learning_gate_view_invalid" in receipt_result.rejection_reasons


def test_builders_reject_secrets_invalid_scores_and_future_evidence() -> None:
    view = _view()
    receipt = view.source_receipts["breadcrumbs"]
    with pytest.raises(ValueError, match="secret_material_forbidden"):
        build_foundup_memex_learning_evidence(
            foundup_id=FOUNDUP_ID,
            snapshot_id=view.snapshot_id,
            source_class="breadcrumbs",
            source_receipt_id=receipt["content_digest"],
            source_revision=receipt["source_version"],
            observed_at=OBSERVED_AT,
            statement="Use sk-example-secret in memory.",
            polarity="supporting",
        )
    evidence = _breadcrumb_evidence(
        view, polarity="supporting", statement="Safe evidence."
    )
    with pytest.raises(ValueError, match="salience_invalid"):
        build_foundup_memex_learning_proposal(
            foundup_id=FOUNDUP_ID,
            snapshot_id=view.snapshot_id,
            category="observed_pattern",
            statement="Invalid score must fail.",
            supporting_evidence_ids=(evidence.evidence_id,),
            proposed_salience=1.5,
            proposed_confidence=0.5,
            created_at=GATE_TIME,
        )
    with pytest.raises(ValueError, match="learning_score_invalid"):
        build_foundup_memex_learning_proposal(
            foundup_id=FOUNDUP_ID,
            snapshot_id=view.snapshot_id,
            category="observed_pattern",
            statement="Overflowing scores must fail.",
            supporting_evidence_ids=(evidence.evidence_id,),
            proposed_salience=10 ** 10000,
            proposed_confidence=0.5,
            created_at=GATE_TIME,
        )
    future = build_foundup_memex_learning_evidence(
        foundup_id=FOUNDUP_ID,
        snapshot_id=view.snapshot_id,
        source_class="breadcrumbs",
        source_receipt_id=receipt["content_digest"],
        source_revision=receipt["source_version"],
        observed_at="2026-08-23T00:02:00+00:00",
        statement="Future evidence must not enter this gate.",
        polarity="supporting",
    )
    result = gate_foundup_memex_learning_candidates(
        view=view,
        evidence=(future,),
        proposals=(_proposal(view, (future,)),),
        created_at=GATE_TIME,
    )
    assert result.accepted is False
    assert "learning_evidence_observed_in_future" in result.rejection_reasons


def test_gate_has_no_storage_network_execution_or_model_imports() -> None:
    forbidden = {
        "sqlite3", "subprocess", "socket", "requests", "httpx", "openai",
        "chromadb", "llama_cpp", "pathlib", "os",
    }
    for path in (SOURCE_PATH, CONTRACT_PATH):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        assert imported.isdisjoint(forbidden)
        assert len(path.read_text(encoding="utf-8").splitlines()) <= 500
        function_sizes = [
            node.end_lineno - node.lineno + 1
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        assert max(function_sizes, default=0) <= 60


def test_hostile_runtime_types_fail_closed_without_throwing() -> None:
    view = _view()
    evidence = _breadcrumb_evidence(
        view, polarity="supporting", statement="Typed evidence."
    )
    proposal = _proposal(view, (evidence,))

    bad_evidence = gate_foundup_memex_learning_candidates(
        view=view,
        evidence=(replace(evidence, statement=42),),
        proposals=(proposal,),
        created_at=GATE_TIME,
        governed_research_receipt_ids=(42,),
    )
    bad_proposal = gate_foundup_memex_learning_candidates(
        view=view,
        evidence=(evidence,),
        proposals=(replace(proposal, supporting_evidence_ids=42),),
        created_at=GATE_TIME,
    )

    assert bad_evidence.accepted is False
    assert "learning_evidence_type_invalid" in bad_evidence.rejection_reasons
    assert "learning_gate_research_receipt_invalid" in bad_evidence.rejection_reasons
    assert bad_proposal.accepted is False
    assert "learning_proposal_support_ids_invalid" in bad_proposal.rejection_reasons

    bad_evidence_container = gate_foundup_memex_learning_candidates(
        view=view, evidence=None, proposals=(proposal,), created_at=GATE_TIME
    )
    bad_proposal_container = gate_foundup_memex_learning_candidates(
        view=view, evidence=(evidence,), proposals=None, created_at=GATE_TIME
    )

    assert bad_evidence_container.accepted is False
    assert "learning_gate_evidence_count_invalid" in bad_evidence_container.rejection_reasons
    assert bad_proposal_container.accepted is False
    assert "learning_gate_proposal_count_invalid" in bad_proposal_container.rejection_reasons


def test_nested_hostile_values_and_mappings_fail_closed_without_callbacks() -> None:
    view = _view()
    evidence = _breadcrumb_evidence(view, polarity="supporting", statement="Typed evidence.")
    proposal = _proposal(view, (evidence,))
    accepted = gate_foundup_memex_learning_candidates(
        view=view, evidence=(evidence,), proposals=(proposal,), created_at=GATE_TIME
    )
    candidate = accepted.candidates[0]

    bad_view = gate_foundup_memex_learning_candidates(
        view=replace(view, invariants=_ExplodingIterMapping(view.invariants)),
        evidence=(evidence,), proposals=(proposal,), created_at=GATE_TIME,
    )
    bad_evidence = gate_foundup_memex_learning_candidates(
        view=view, evidence=(replace(evidence, statement=_ExplodingDeepcopy()),),
        proposals=(proposal,), created_at=GATE_TIME,
    )
    bad_proposal = gate_foundup_memex_learning_candidates(
        view=view, evidence=(evidence,),
        proposals=(replace(proposal, proposed_salience=_ExplodingDeepcopy()),),
        created_at=GATE_TIME,
    )
    oversized_text = gate_foundup_memex_learning_candidates(
        view=view,
        evidence=(replace(evidence, statement="x" * (MAX_STATEMENT_CHARS + 1)),),
        proposals=(proposal,),
        created_at=GATE_TIME,
    )

    assert bad_view.accepted is False
    assert "learning_gate_view_invalid" in bad_view.rejection_reasons
    assert bad_evidence.accepted is False
    assert "learning_evidence_type_invalid" in bad_evidence.rejection_reasons
    assert bad_proposal.accepted is False
    assert "learning_proposal_salience_invalid" in bad_proposal.rejection_reasons
    assert oversized_text.accepted is False
    assert "learning_evidence_statement_too_long" in oversized_text.rejection_reasons
    assert not verify_foundup_memex_learning_candidate_reconstruction(
        replace(
            candidate,
            supporting_evidence_ids=(_ExplodingDeepcopy(), _ExplodingDeepcopy()),
        ),
        proposal,
        (evidence,),
    )


def test_extreme_offset_dates_reject_without_overflow() -> None:
    view = _view()
    evidence = _breadcrumb_evidence(view, polarity="supporting", statement="Typed time.")
    proposal = _proposal(view, (evidence,))
    extreme_time = "0001-01-01T00:00:00+14:00"

    result = gate_foundup_memex_learning_candidates(
        view=view, evidence=(evidence,), proposals=(proposal,), created_at=extreme_time
    )

    assert result.accepted is False
    assert "learning_gate_created_at_invalid" in result.rejection_reasons
    with pytest.raises(ValueError, match="learning_time_invalid"):
        build_foundup_memex_learning_evidence(
            foundup_id=FOUNDUP_ID,
            snapshot_id=view.snapshot_id,
            source_class="breadcrumbs",
            source_receipt_id=view.source_receipts["breadcrumbs"]["content_digest"],
            source_revision=view.source_receipts["breadcrumbs"]["source_version"],
            observed_at=extreme_time,
            statement="An overflowing timestamp must reject.",
            polarity="supporting",
        )


def test_rehydrated_proposal_and_candidate_reference_counts_are_bounded() -> None:
    view = _view()
    evidence = _breadcrumb_evidence(view, polarity="supporting", statement="Bounded closure.")
    proposal = _proposal(view, (evidence,))
    result = gate_foundup_memex_learning_candidates(
        view=view, evidence=(evidence,), proposals=(proposal,), created_at=GATE_TIME
    )
    oversized_ids = tuple(
        _sha(f"oversized-reference-{index}")
        for index in range(MAX_REFERENCES_PER_PROPOSAL + 1)
    )
    bad_proposal = gate_foundup_memex_learning_candidates(
        view=view,
        evidence=(evidence,),
        proposals=(replace(proposal, supporting_evidence_ids=oversized_ids),),
        created_at=GATE_TIME,
    )

    assert bad_proposal.accepted is False
    assert "learning_proposal_evidence_count_invalid" in bad_proposal.rejection_reasons
    assert not verify_foundup_memex_learning_candidate_reconstruction(
        replace(result.candidates[0], supporting_evidence_ids=oversized_ids),
        proposal,
        (evidence,),
    )


def test_future_proposal_fails_closed() -> None:
    view = _view()
    evidence = _breadcrumb_evidence(
        view, polarity="supporting", statement="Evidence precedes the gate."
    )
    proposal = build_foundup_memex_learning_proposal(
        foundup_id=FOUNDUP_ID,
        snapshot_id=view.snapshot_id,
        category="observed_pattern",
        statement="A future proposal must not enter the current gate.",
        supporting_evidence_ids=(evidence.evidence_id,),
        proposed_salience=0.5,
        proposed_confidence=0.5,
        created_at="2026-08-23T00:02:00+00:00",
    )
    result = gate_foundup_memex_learning_candidates(
        view=view, evidence=(evidence,), proposals=(proposal,), created_at=GATE_TIME
    )
    assert result.accepted is False
    assert "learning_proposal_created_in_future" in result.rejection_reasons
