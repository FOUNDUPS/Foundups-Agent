"""Tests for HOLOINDEX_INDEX_GAP_TO_WRE_WORKITEM_PHASE1."""

from __future__ import annotations

import ast
from pathlib import Path

from holo_index.index_gap_workitem import (
    ACTION_RETRIEVAL_QUALITY_SLICE,
    ACTION_RUNTIME_REPAIR,
    ACTION_TARGETED_REINDEX,
    ACTION_TOOL_CLASSIFIER_REPAIR,
    GAP_HOLOINDEX_LOW_SIGNAL,
    GAP_HOLOINDEX_RUNTIME_FAILURE,
    GAP_HOLOINDEX_STALE_INDEX,
    GAP_TOOL_CLASSIFIER_UNAVAILABLE,
    NO_INDEX_GAP,
    WORKITEM_PLANNED,
    classify_index_gap,
    plan_index_gap_work_item,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _scorecard(**overrides):
    base = {
        "query": "RedDog work focus",
        "index_gap_detected": True,
        "direct_read_fallback_used": True,
        "target_recall_ok": True,
        "direct_read_paths": [
            "modules/foundups/agent/src/create_foundup_dryrun.py",
            "docs/0102_session_briefings/work_ledger.schema.json",
        ],
        "required_targets_missing": [],
        "code_hits": [{"path": "modules/foundups/agent/src/context_bundle_builder.py"}],
    }
    base.update(overrides)
    return base


def test_stale_index_gap_plans_targeted_reindex_work_item() -> None:
    result = plan_index_gap_work_item(_scorecard())

    assert result.decision == WORKITEM_PLANNED
    assert result.gap_class == GAP_HOLOINDEX_STALE_INDEX
    assert result.work_item is not None
    item = result.work_item
    assert item.recommended_action == ACTION_TARGETED_REINDEX
    assert item.owner == "WRE_CI_INDEX_MAINTENANCE"
    assert item.priority == "P1"
    assert item.target_paths == [
        "modules/foundups/agent/src/create_foundup_dryrun.py",
        "docs/0102_session_briefings/work_ledger.schema.json",
    ]
    assert item.target_collections == ["navigation_symbols", "navigation_work_ledger"]
    assert item.live_wre_enqueue_performed is False
    assert item.no_reindex_performed is True
    assert item.no_agentdb_mutation_performed is True
    assert item.no_runtime_reindex_performed is True


def test_low_signal_gap_routes_to_retrieval_quality_not_reindex() -> None:
    scorecard = _scorecard(
        direct_read_fallback_used=False,
        target_recall_ok=False,
        direct_read_paths=[],
        required_targets_missing=["modules/x/missing.py"],
    )
    result = plan_index_gap_work_item(scorecard)

    assert result.decision == WORKITEM_PLANNED
    assert result.gap_class == GAP_HOLOINDEX_LOW_SIGNAL
    assert result.work_item is not None
    assert result.work_item.recommended_action == ACTION_RETRIEVAL_QUALITY_SLICE
    assert result.work_item.priority == "P2"


def test_runtime_failure_gap_routes_to_runtime_repair() -> None:
    result = plan_index_gap_work_item(
        _scorecard(direct_read_fetch_error="ENOBUFS", direct_read_paths=[]),
    )

    assert result.gap_class == GAP_HOLOINDEX_RUNTIME_FAILURE
    assert result.work_item is not None
    assert result.work_item.recommended_action == ACTION_RUNTIME_REPAIR


def test_tool_classifier_gap_routes_to_classifier_repair() -> None:
    result = plan_index_gap_work_item(
        _scorecard(tool_classifier_unavailable=True, direct_read_paths=[]),
    )

    assert result.gap_class == GAP_TOOL_CLASSIFIER_UNAVAILABLE
    assert result.work_item is not None
    assert result.work_item.recommended_action == ACTION_TOOL_CLASSIFIER_REPAIR


def test_no_gap_produces_no_work_item() -> None:
    result = plan_index_gap_work_item(
        _scorecard(index_gap_detected=False, direct_read_fallback_used=False, direct_read_paths=[]),
    )

    assert result.decision == NO_INDEX_GAP
    assert result.work_item is None


def test_result_id_is_deterministic_for_same_scorecard() -> None:
    first = plan_index_gap_work_item(_scorecard())
    second = plan_index_gap_work_item(_scorecard())

    assert first.work_item is not None and second.work_item is not None
    assert first.work_item.work_item_id == second.work_item.work_item_id
    assert first.work_item.scorecard_digest == second.work_item.scorecard_digest


def test_freshness_receipt_digest_is_recorded_without_receipt_body() -> None:
    receipt = {"schema_version": "holoindex_freshness_receipt.v1", "repo_head_sha": "abc123"}

    result = plan_index_gap_work_item(_scorecard(), freshness_receipt=receipt)

    assert result.work_item is not None
    assert result.work_item.freshness_receipt_digest
    assert "abc123" not in result.work_item.freshness_receipt_digest


def test_index_gap_event_stale_targets_are_merged_and_deduped() -> None:
    result = plan_index_gap_work_item(
        _scorecard(direct_read_paths=["modules/a.py"]),
        index_gap_event={"stale_targets": ["modules/a.py", "modules/b.py"]},
    )

    assert result.work_item is not None
    assert result.work_item.target_paths == ["modules/a.py", "modules/b.py"]
    assert result.work_item.target_collections == ["navigation_symbols"]


def test_classification_helpers_fail_closed_on_non_gap() -> None:
    assert classify_index_gap({}) is None
    assert classify_index_gap({"index_gap_detected": False}) is None


def test_module_has_no_live_execution_or_enqueue_imports() -> None:
    source = (REPO_ROOT / "holo_index" / "index_gap_workitem.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    banned_imports = {
        "subprocess",
        "requests",
        "modules.infrastructure.database.src.agent_db",
        "modules.communication.moltbot_bridge.src.openclaw_supervisor",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name not in banned_imports
        if isinstance(node, ast.ImportFrom):
            assert (node.module or "") not in banned_imports
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in {"create_autonomous_task", "get_autonomous_tasks"}
