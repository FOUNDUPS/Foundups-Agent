"""Tests for FOUNDUP_BRAIN_CURRENT_STATE_ASSEMBLY_PHASE1."""

from __future__ import annotations

from pathlib import Path

from holo_index.freshness_receipt import CollectionFreshness, HoloIndexFreshnessReceipt
from modules.communication.moltbot_bridge.src.foundup_brain_current_state import (
    FOUNDUP_BRAIN_VIEW_ACCEPTED,
    FOUNDUP_BRAIN_VIEW_REJECTED,
    assemble_foundup_brain_current_state,
)
from modules.communication.moltbot_bridge.src.reddog_operational_context_snapshot import (
    build_operational_context_snapshot,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
NOW = "2026-07-14T00:00:00+00:00"
HEAD = "52e98c6652b3c8eb0818d2ec6718c005c7e55c79"
REVISION = "sha256:foundup-brain-work-state"
FOUNDUP_ID = "foundups-agent"


def _snapshot(*, brain_available: bool = True):
    holo_receipt = HoloIndexFreshnessReceipt(
        schema_version="holoindex_freshness_receipt.v1",
        generated_at=NOW,
        repo_root=str(REPO_ROOT),
        repo_head_sha=HEAD,
        ssd_path="E:/HoloIndex",
        source="ci_targeted_reindex",
        collections=[
            CollectionFreshness(
                name="navigation_work_ledger",
                count=3,
                status="indexed",
                source="ci_targeted_reindex",
                repo_head_sha=HEAD,
                last_indexed_at=NOW,
            ),
            CollectionFreshness(
                name="navigation_symbols",
                count=4,
                status="indexed",
                source="ci_targeted_reindex",
                repo_head_sha=HEAD,
                last_indexed_at=NOW,
            ),
        ],
    )
    result = build_operational_context_snapshot(
        repo_state={
            "head_sha": HEAD,
            "dirty_paths": (),
            "dirty_digest": "sha256:clean",
            "worktree_digest": "sha256:worktrees",
        },
        work_state_snapshot={
            "schema_version": "reddog_authoritative_work_state.v1",
            "revision": REVISION,
            "selected_slice": "FOUNDUP_BRAIN_CURRENT_STATE_ASSEMBLY_PHASE1",
            "worker_claims": [{"claim_id": "claim-1", "status": "ACTIVE"}],
            "wre_queue_items": [],
        },
        holoindex_receipt=holo_receipt,
        changed_paths=["modules/communication/moltbot_bridge/src/foundup_brain_current_state.py"],
        now_iso=NOW,
        breadcrumbs=[
            {
                "breadcrumb_id": "breadcrumb-1",
                "continuity_id": FOUNDUP_ID,
                "task_id": "brain-poc",
                "timestamp": NOW,
            }
        ],
        breadcrumb_scope=FOUNDUP_ID,
        brain_state=(
            {
                "available": True,
                "signature_digest": "sha256:foundup-brain",
                "repo_head_sha": HEAD,
                "work_state_revision": REVISION,
            }
            if brain_available
            else None
        ),
    )
    assert result.accepted is True
    assert result.snapshot is not None
    return result.snapshot


def _identity(foundup_id: str = FOUNDUP_ID):
    return {
        "foundup_id": foundup_id,
        "name": "Foundups Agent",
        "stage": "POC",
        "purpose": "Code out FoundUps as decentralized autonomous entities.",
        "outcome": "A FoundUp can know and evolve its current state.",
        "solution": "Compose existing Brain, Breadcrumb, work-state, and repository receipts.",
        "pain": "Project cognition is fragmented across independent sources.",
    }


def _roadmap(foundup_id: str = FOUNDUP_ID):
    return {
        "foundup_id": foundup_id,
        "roadmap_id": "foundups-agent-roadmap",
        "version": "phase1",
        "content_digest": "sha256:roadmap",
        "active_item_ids": ["FOUNDUP_BRAIN_CURRENT_STATE_ASSEMBLY_PHASE1"],
        "blocked_item_ids": [],
    }


def _verified_outcome(foundup_id: str = FOUNDUP_ID):
    return {
        "foundup_id": foundup_id,
        "outcome_id": "outcome-1",
        "verification_receipt_id": "sha256:verification",
        "held_out_receipt_id": "sha256:held-out",
        "head_sha": HEAD,
        "accepted": True,
        "held_out_passed": True,
        "content_digest": "sha256:outcome",
    }


def test_assembles_deterministic_read_only_foundup_brain_view() -> None:
    snapshot = _snapshot()

    first = assemble_foundup_brain_current_state(
        foundup_id=FOUNDUP_ID,
        snapshot=snapshot,
        identity=_identity(),
        roadmap_state=_roadmap(),
        verified_outcomes=[_verified_outcome()],
    )
    second = assemble_foundup_brain_current_state(
        foundup_id=FOUNDUP_ID,
        snapshot=snapshot,
        identity=_identity(),
        roadmap_state=_roadmap(),
        verified_outcomes=[_verified_outcome()],
    )

    assert first.accepted is True
    assert first.status == FOUNDUP_BRAIN_VIEW_ACCEPTED
    assert first.view is not None and second.view is not None
    assert first.view.foundup_id == FOUNDUP_ID
    assert first.view.snapshot_id == snapshot.snapshot_receipt_id
    assert first.view.foundup_brain_view_id == second.view.foundup_brain_view_id
    assert first.view.current_state["repo_head_sha"] == HEAD
    assert first.view.current_state["work_state_revision"] == REVISION
    assert first.view.current_state["breadcrumb_record_count"] == 1
    assert first.view.current_state["brain_signature_digest"] == "sha256:foundup-brain"
    assert first.view.learning_candidates == ()
    assert first.view.roadmap_signals == ()
    assert all(first.view.invariants.values())


def test_missing_brain_receipt_fails_closed_for_foundup_brain_poc() -> None:
    result = assemble_foundup_brain_current_state(
        foundup_id=FOUNDUP_ID,
        snapshot=_snapshot(brain_available=False),
        identity=_identity(),
        roadmap_state=_roadmap(),
    )

    assert result.accepted is False
    assert result.status == FOUNDUP_BRAIN_VIEW_REJECTED
    assert result.view is None
    assert "source_not_fresh:brain" in result.rejection_reasons


def test_cross_foundup_identity_roadmap_and_outcome_are_rejected() -> None:
    result = assemble_foundup_brain_current_state(
        foundup_id=FOUNDUP_ID,
        snapshot=_snapshot(),
        identity=_identity("other-foundup"),
        roadmap_state=_roadmap("other-foundup"),
        verified_outcomes=[_verified_outcome("other-foundup")],
    )

    assert result.accepted is False
    assert "identity_foundup_id_mismatch" in result.rejection_reasons
    assert "roadmap_foundup_id_mismatch" in result.rejection_reasons
    assert "verified_outcome_foundup_id_mismatch" in result.rejection_reasons


def test_unverified_outcome_cannot_enter_current_brain_view() -> None:
    outcome = _verified_outcome()
    outcome["held_out_passed"] = False

    result = assemble_foundup_brain_current_state(
        foundup_id=FOUNDUP_ID,
        snapshot=_snapshot(),
        identity=_identity(),
        roadmap_state=_roadmap(),
        verified_outcomes=[outcome],
    )

    assert result.accepted is False
    assert "unverified_outcome_rejected" in result.rejection_reasons


def test_secret_bearing_identity_metadata_is_rejected() -> None:
    identity = _identity()
    identity["purpose"] = "Use sk-example-secret in runtime"

    result = assemble_foundup_brain_current_state(
        foundup_id=FOUNDUP_ID,
        snapshot=_snapshot(),
        identity=identity,
        roadmap_state=_roadmap(),
    )

    assert result.accepted is False
    assert "secret_bearing_input_rejected" in result.rejection_reasons
    assert result.no_brain_write_performed is True
    assert result.no_holoindex_mutation_performed is True
    assert result.no_repo_mutation_performed is True
