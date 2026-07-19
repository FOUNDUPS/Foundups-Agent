"""Tests for FOUNDUP_BRAIN_CURRENT_STATE_ASSEMBLY_PHASE1."""

from __future__ import annotations

import ast
from pathlib import Path

from modules.communication.moltbot_bridge.src.foundup_brain_current_state import (
    FOUNDUP_BRAIN_VIEW_ACCEPTED,
    FOUNDUP_BRAIN_VIEW_REJECTED,
    assemble_foundup_brain_current_state,
)
from modules.communication.moltbot_bridge.src.reddog_operational_context_snapshot import (
    build_operational_context_snapshot,
)
from modules.communication.moltbot_bridge.tests.holoindex_freshness_receipt_test_helpers import (
    build_fresh_holoindex_receipt,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "foundup_brain_current_state.py"
)
NOW = "2026-07-14T00:00:00+00:00"
VALID_NOW = "2026-07-14T00:01:00+00:00"
EXPIRED_NOW = "2026-07-14T00:11:00+00:00"
HEAD = "52e98c6652b3c8eb0818d2ec6718c005c7e55c79"
REVISION = "sha256:foundup-brain-work-state"
FOUNDUP_ID = "foundups-agent"


def _snapshot(*, brain_available: bool = True, worker_claims=None, queue_items=None):
    holo_receipt = build_fresh_holoindex_receipt(
        repo_root=REPO_ROOT,
        head_sha=HEAD,
        generated_at=NOW,
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
            "worker_claims": (
                worker_claims
                if worker_claims is not None
                else [{"claim_id": "claim-1", "foundup_id": FOUNDUP_ID, "status": "ACTIVE"}]
            ),
            "wre_queue_items": queue_items if queue_items is not None else [],
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


def _assemble(**overrides):
    kwargs = {
        "foundup_id": FOUNDUP_ID,
        "snapshot": _snapshot(),
        "identity": _identity(),
        "roadmap_state": _roadmap(),
        "verified_outcomes": [_verified_outcome()],
        "now_iso": VALID_NOW,
        "policy_foundup_scope": (FOUNDUP_ID,),
    }
    kwargs.update(overrides)
    return assemble_foundup_brain_current_state(**kwargs)


def test_assembles_deterministic_read_only_foundup_brain_view() -> None:
    snapshot = _snapshot()
    first = _assemble(snapshot=snapshot)
    second = _assemble(snapshot=snapshot)
    assert first.accepted is True
    assert first.status == FOUNDUP_BRAIN_VIEW_ACCEPTED
    assert first.view is not None and second.view is not None
    assert first.view.foundup_id == FOUNDUP_ID
    assert first.view.snapshot_id == snapshot.snapshot_receipt_id
    assert first.view.foundup_brain_view_id == second.view.foundup_brain_view_id
    assert first.view.current_state["repo_head_sha"] == HEAD
    assert first.view.current_state["work_state_revision"] == REVISION
    assert first.view.current_state["breadcrumb_record_count"] == 1
    assert first.view.current_state["breadcrumb_scope"] == FOUNDUP_ID
    assert first.view.current_state["brain_signature_digest"] == "sha256:foundup-brain"
    assert first.view.current_state["active_work"][0]["foundup_id"] == FOUNDUP_ID
    assert first.view.assembly_receipt is not None
    assert first.view.assembly_receipt["policy_foundup_scope"] == (FOUNDUP_ID,)
    assert first.view.assembly_receipt["excluded_record_count"] == 0
    assert first.view.assembly_receipt["excluded_record_digest"].startswith("sha256:")
    assert first.view.learning_candidates == ()
    assert first.view.roadmap_signals == ()
    assert all(first.view.invariants.values())


def test_missing_brain_receipt_fails_closed_for_foundup_brain_poc() -> None:
    result = _assemble(snapshot=_snapshot(brain_available=False), verified_outcomes=[])
    assert result.accepted is False
    assert result.status == FOUNDUP_BRAIN_VIEW_REJECTED
    assert result.view is None
    assert "source_not_fresh:brain" in result.rejection_reasons


def test_cross_foundup_identity_roadmap_and_outcome_are_rejected() -> None:
    result = _assemble(
        identity=_identity("other-foundup"),
        roadmap_state=_roadmap("other-foundup"),
        verified_outcomes=[_verified_outcome("other-foundup")],
    )
    assert result.accepted is False
    assert "identity_foundup_id_mismatch" in result.rejection_reasons
    assert "roadmap_foundup_id_mismatch" in result.rejection_reasons
    assert "verified_outcome_foundup_id_mismatch" in result.rejection_reasons


def test_cross_foundup_work_claim_and_queue_item_are_excluded_not_leaked() -> None:
    snapshot = _snapshot(
        worker_claims=[{"claim_id": "foreign-claim", "foundup_id": "other-foundup"}],
        queue_items=[{"queue_item_id": "foreign-queue", "foundup_id": "other-foundup"}],
    )
    result = _assemble(snapshot=snapshot, verified_outcomes=[])
    assert result.accepted is True
    assert result.view is not None
    assert result.view.current_state["active_work"] == ()
    assert result.view.current_state["queued_work"] == ()
    assert result.view.assembly_receipt is not None
    assert result.view.assembly_receipt["excluded_record_count"] == 2
    assert result.view.assembly_receipt["excluded_record_digest"].startswith("sha256:")


def test_unscoped_work_record_fails_in_resident_mode() -> None:
    snapshot = _snapshot(worker_claims=[{"claim_id": "legacy-claim", "status": "ACTIVE"}])
    result = _assemble(snapshot=snapshot, verified_outcomes=[])
    assert result.accepted is False
    assert "worker_claim_missing_foundup_id" in result.rejection_reasons


def test_legacy_unscoped_work_record_requires_explicit_compatibility_mode() -> None:
    snapshot = _snapshot(worker_claims=[{"claim_id": "legacy-claim", "status": "ACTIVE"}])
    result = _assemble(
        snapshot=snapshot,
        verified_outcomes=[],
        legacy_single_foundup_compatibility=True,
    )
    assert result.accepted is True
    assert result.view is not None
    assert result.view.current_state["active_work"][0]["claim_id"] == "legacy-claim"
    assert (
        result.view.current_state["active_work"][0]["scope_origin"]
        == "legacy_single_foundup_compatibility"
    )


def test_mixed_foundup_snapshot_can_build_independent_views_without_leakage() -> None:
    snapshot = _snapshot(
        worker_claims=[
            {"claim_id": "a-claim", "foundup_id": FOUNDUP_ID, "status": "ACTIVE"},
            {"claim_id": "b-claim", "foundup_id": "foundup-b", "status": "ACTIVE"},
        ],
        queue_items=[
            {"queue_item_id": "a-queue", "foundup_id": FOUNDUP_ID},
            {"queue_item_id": "b-queue", "foundup_id": "foundup-b"},
        ],
    )

    view_a = _assemble(snapshot=snapshot, verified_outcomes=[])
    view_b = _assemble(
        foundup_id="foundup-b",
        snapshot=snapshot,
        identity=_identity("foundup-b"),
        roadmap_state=_roadmap("foundup-b"),
        verified_outcomes=[],
        policy_foundup_scope=("foundup-b",),
    )

    assert view_a.accepted is True and view_a.view is not None
    assert view_b.accepted is True and view_b.view is not None
    assert [item["claim_id"] for item in view_a.view.current_state["active_work"]] == ["a-claim"]
    assert [item["queue_item_id"] for item in view_a.view.current_state["queued_work"]] == ["a-queue"]
    assert [item["claim_id"] for item in view_b.view.current_state["active_work"]] == ["b-claim"]
    assert [item["queue_item_id"] for item in view_b.view.current_state["queued_work"]] == ["b-queue"]
    assert view_a.view.assembly_receipt["excluded_record_count"] == 2
    assert view_b.view.assembly_receipt["excluded_record_count"] == 2


def test_identity_roadmap_outcome_and_policy_scope_must_match_foundup() -> None:
    result = _assemble(
        identity={"name": "Foundups Agent"},
        roadmap_state={
            "roadmap_id": "foundups-agent-roadmap",
            "version": "phase1",
            "content_digest": "sha256:roadmap",
        },
        verified_outcomes=[
            {
                "outcome_id": "outcome-1",
                "verification_receipt_id": "sha256:verification",
                "held_out_receipt_id": "sha256:held-out",
                "head_sha": HEAD,
                "accepted": True,
                "held_out_passed": True,
                "content_digest": "sha256:outcome",
            }
        ],
        policy_foundup_scope=("other-foundup",),
    )
    assert result.accepted is False
    assert "identity_missing_foundup_id" in result.rejection_reasons
    assert "roadmap_missing_foundup_id" in result.rejection_reasons
    assert "verified_outcome_missing_foundup_id" in result.rejection_reasons
    assert "policy_foundup_scope_mismatch" in result.rejection_reasons


def test_missing_roadmap_binding_fails_closed() -> None:
    result = _assemble(roadmap_state={"foundup_id": FOUNDUP_ID}, verified_outcomes=[])
    assert result.accepted is False
    assert "missing_roadmap_id" in result.rejection_reasons
    assert "missing_roadmap_version" in result.rejection_reasons
    assert "missing_roadmap_content_digest" in result.rejection_reasons


def test_expired_snapshot_fails_closed() -> None:
    result = _assemble(now_iso=EXPIRED_NOW, verified_outcomes=[])
    assert result.accepted is False
    assert "snapshot_expired" in result.rejection_reasons


def test_unverified_or_incomplete_outcome_cannot_enter_current_brain_view() -> None:
    outcome = _verified_outcome()
    outcome["held_out_passed"] = False
    outcome["verification_receipt_id"] = ""
    result = _assemble(verified_outcomes=[outcome])
    assert result.accepted is False
    assert "unverified_outcome_rejected" in result.rejection_reasons
    assert "missing_verified_outcome_field:verification_receipt_id" in result.rejection_reasons


def test_secret_bearing_identity_metadata_is_rejected() -> None:
    identity = _identity()
    identity["purpose"] = "Use sk-example-secret in runtime"
    result = _assemble(identity=identity, verified_outcomes=[])
    assert result.accepted is False
    assert "secret_bearing_input_rejected" in result.rejection_reasons
    assert result.no_brain_write_performed is True
    assert result.no_holoindex_mutation_performed is True
    assert result.no_repo_mutation_performed is True


def test_source_ast_contains_no_execution_or_mutation_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert imports.isdisjoint({"subprocess", "socket", "requests", "sqlite3", "git", "openai"})
