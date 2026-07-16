"""Tests for RedDog context snapshot Fusion/assignment gate."""

from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path

from holo_index.freshness_receipt import CollectionFreshness, HoloIndexFreshnessReceipt
from modules.communication.moltbot_bridge.src.reddog_context_snapshot_fusion_assignment_gate import (
    FUSION_ASSIGNMENT_GATE_PASSED,
    FUSION_ASSIGNMENT_GATE_REJECTED,
    evaluate_context_snapshot_fusion_assignment_gate,
)
from modules.communication.moltbot_bridge.src.reddog_operational_context_snapshot import (
    build_evidence_bundle,
    build_operational_context_snapshot,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_context_snapshot_fusion_assignment_gate.py"
)
NOW = "2026-07-14T00:00:00+00:00"
HEAD = "9c31512a8b4d6e1f0a2b3c4d5e6f708192a3b4c5"
REVISION = "sha256:work-state-revision"


def _fresh_holo_receipt():
    return HoloIndexFreshnessReceipt(
        schema_version="holoindex_freshness_receipt.v1",
        generated_at=NOW,
        repo_root=str(REPO_ROOT),
        repo_head_sha=HEAD,
        ssd_path="E:/HoloIndex",
        source="ci_targeted_reindex",
        generation_id="sha256:holo-generation",
        collections=[
            CollectionFreshness(
                name="navigation_work_ledger",
                count=2,
                status="indexed",
                source="ci_targeted_reindex",
                repo_head_sha=HEAD,
                last_indexed_at=NOW,
                source_manifest_digest="sha256:work-ledger-manifest",
                indexed_paths_digest="sha256:work-ledger-paths",
                verification="PASS",
            ),
            CollectionFreshness(
                name="navigation_symbols",
                count=3,
                status="indexed",
                source="ci_targeted_reindex",
                repo_head_sha=HEAD,
                last_indexed_at=NOW,
                source_manifest_digest="sha256:symbols-manifest",
                indexed_paths_digest="sha256:symbols-paths",
                verification="PASS",
            ),
        ],
    )


def _snapshot_bundle():
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
            "selected_slice": "REDDOG_CONTEXT_SNAPSHOT_FUSION_AND_ASSIGNMENT_GATE_PHASE1",
            "refresh_receipt_id": "sha256:refresh",
            "worker_claims": [{"claim_id": "claim-1", "status": "ACTIVE"}],
            "wre_queue_items": [{"queue_item_id": "queue-1"}],
        },
        holoindex_receipt=_fresh_holo_receipt(),
        changed_paths=["docs/0102_session_briefings/work_ledger.schema.json"],
        breadcrumbs=[
            {
                "breadcrumb_id": "b1",
                "continuity_id": "cont-1",
                "timestamp": NOW,
            }
        ],
        breadcrumb_scope="cont-1",
        now_iso=NOW,
    )
    assert result.accepted is True
    assert result.snapshot is not None and result.context_view is not None
    bundle = build_evidence_bundle(
        snapshot=result.snapshot,
        context_view=result.context_view,
        report_digests=["sha256:repo-audit"],
    )
    return result.snapshot, result.context_view, bundle


def test_gate_accepts_exact_snapshot_context_and_evidence_binding() -> None:
    snapshot, context_view, bundle = _snapshot_bundle()

    decision = evaluate_context_snapshot_fusion_assignment_gate(
        snapshot=snapshot,
        context_view=context_view,
        evidence_bundle=bundle,
        current_repo_head_sha=HEAD,
        current_work_state_revision=REVISION,
        current_breadcrumb_high_watermark=snapshot.breadcrumbs_state["high_watermark"],
        requested_operation="audit_and_assign",
        prompt_text="audit current RedDog work state",
        now_iso="2026-07-14T00:01:00+00:00",
    )

    assert decision.accepted is True
    assert decision.status == FUSION_ASSIGNMENT_GATE_PASSED
    assert decision.fusion_allowed is True
    assert decision.assignment_allowed is True
    assert decision.determination_binding is not None
    assert decision.determination_binding.context_view_id == context_view.context_view_id
    assert decision.determination_binding.evidence_bundle_id == bundle.evidence_bundle_id
    assert decision.no_model_call_performed is True
    assert decision.no_worker_spawn_performed is True


def test_gate_rejects_before_fusion_when_snapshot_view_or_bundle_missing() -> None:
    decision = evaluate_context_snapshot_fusion_assignment_gate(
        snapshot=None,
        context_view=None,
        evidence_bundle=None,
        current_repo_head_sha=HEAD,
        current_work_state_revision=REVISION,
        requested_operation="audit",
    )

    assert decision.accepted is False
    assert decision.status == FUSION_ASSIGNMENT_GATE_REJECTED
    assert decision.fusion_allowed is False
    assert "missing_snapshot" in decision.rejection_reasons
    assert "missing_context_view" in decision.rejection_reasons
    assert "missing_evidence_bundle" in decision.rejection_reasons


def test_gate_rejects_mismatched_context_view_and_evidence_bundle() -> None:
    snapshot, context_view, bundle = _snapshot_bundle()
    bad_view = replace(context_view, snapshot_receipt_id="sha256:wrong")
    bad_bundle = replace(bundle, context_view_id="sha256:wrong-context")

    decision = evaluate_context_snapshot_fusion_assignment_gate(
        snapshot=snapshot,
        context_view=bad_view,
        evidence_bundle=bad_bundle,
        current_repo_head_sha=HEAD,
        current_work_state_revision=REVISION,
        requested_operation="audit",
        now_iso="2026-07-14T00:01:00+00:00",
    )

    assert decision.accepted is False
    assert "context_view_snapshot_mismatch" in decision.rejection_reasons
    assert "evidence_bundle_context_view_mismatch" in decision.rejection_reasons


def test_gate_rejects_head_work_state_or_breadcrumb_change() -> None:
    snapshot, context_view, bundle = _snapshot_bundle()

    decision = evaluate_context_snapshot_fusion_assignment_gate(
        snapshot=snapshot,
        context_view=context_view,
        evidence_bundle=bundle,
        current_repo_head_sha="new-head",
        current_work_state_revision="new-revision",
        current_breadcrumb_high_watermark="new-watermark",
        requested_operation="audit",
        now_iso="2026-07-14T00:01:00+00:00",
    )

    assert decision.accepted is False
    assert "repo_head_changed" in decision.rejection_reasons
    assert "work_state_revision_changed" in decision.rejection_reasons
    assert "breadcrumb_high_watermark_changed" in decision.rejection_reasons


def test_gate_rejects_empty_evidence_bundle() -> None:
    snapshot, context_view, bundle = _snapshot_bundle()
    empty_bundle = replace(bundle, report_digests=(), external_research_receipts=())

    decision = evaluate_context_snapshot_fusion_assignment_gate(
        snapshot=snapshot,
        context_view=context_view,
        evidence_bundle=empty_bundle,
        current_repo_head_sha=HEAD,
        current_work_state_revision=REVISION,
        current_breadcrumb_high_watermark=snapshot.breadcrumbs_state["high_watermark"],
        requested_operation="audit",
        now_iso="2026-07-14T00:01:00+00:00",
    )

    assert decision.accepted is False
    assert "empty_evidence_bundle" in decision.rejection_reasons


def test_gate_rejects_expired_snapshot() -> None:
    snapshot, context_view, bundle = _snapshot_bundle()

    decision = evaluate_context_snapshot_fusion_assignment_gate(
        snapshot=snapshot,
        context_view=context_view,
        evidence_bundle=bundle,
        current_repo_head_sha=HEAD,
        current_work_state_revision=REVISION,
        current_breadcrumb_high_watermark=snapshot.breadcrumbs_state["high_watermark"],
        requested_operation="audit",
        now_iso="2026-07-14T00:20:00+00:00",
    )

    assert decision.accepted is False
    assert "snapshot_expired" in decision.rejection_reasons


def test_gate_determination_id_is_deterministic_for_same_inputs() -> None:
    snapshot, context_view, bundle = _snapshot_bundle()
    kwargs = {
        "snapshot": snapshot,
        "context_view": context_view,
        "evidence_bundle": bundle,
        "current_repo_head_sha": HEAD,
        "current_work_state_revision": REVISION,
        "current_breadcrumb_high_watermark": snapshot.breadcrumbs_state["high_watermark"],
        "requested_operation": "audit",
        "prompt_text": "same prompt",
        "now_iso": "2026-07-14T00:01:00+00:00",
    }

    first = evaluate_context_snapshot_fusion_assignment_gate(**kwargs)
    second = evaluate_context_snapshot_fusion_assignment_gate(**kwargs)

    assert first.determination_binding is not None
    assert second.determination_binding is not None
    assert first.determination_binding.determination_id == second.determination_binding.determination_id
    assert first.to_dict() == second.to_dict()


def test_gate_module_has_no_runtime_wiring_or_execution() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_tokens = (
        "openclaw_supervisor",
        "hermes_job_executor",
        "create_autonomous_task",
        "subprocess",
        "requests",
        "execute_skill",
        "callFusion",
        "extension.js",
    )
    for token in forbidden_tokens:
        assert token not in source
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in {"write_text", "mkdir", "commit"}
