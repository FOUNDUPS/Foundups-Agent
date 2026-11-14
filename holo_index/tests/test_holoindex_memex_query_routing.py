from __future__ import annotations

import ast
from pathlib import Path

from holo_index.memex_projection_adapter import (
    project_foundup_memex_to_holoindex_shadow,
)
from holo_index.memex_query_routing import (
    MEMEX_QUERY_SOURCE,
    build_memex_projection_query_receipt,
    projection_to_plain_dict,
)


MODULE_PATH = Path(__file__).parents[1] / "memex_query_routing.py"
FIXED_NOW = "2026-07-16T00:00:00+00:00"


def _projection():
    return project_foundup_memex_to_holoindex_shadow(
        memex_view={
            "schema_version": "foundup_brain_current_state.v1",
            "foundup_brain_view_id": "sha256:brain-view",
            "foundup_id": "foundups-agent",
            "snapshot_id": "snapshot-1",
            "snapshot_content_digest": "sha256:snapshot",
            "identity": {
                "foundup_id": "foundups-agent",
                "name": "Foundups Agent",
            },
            "current_state": {
                "selected_slice": "REDDOG_AUTHORITATIVE_WORK_STATE_REFRESH_RUNTIME_PHASE1",
                "runtime_gap": "authoritative work state reconciliation",
            },
            "roadmap_state": {
                "roadmap_id": "r1",
                "next_slice": "REDDOG_SIGNER_AND_DELEGATED_AUTHORITY_RUNTIME_PHASE1",
            },
            "verified_outcomes": [
                {
                    "outcome_id": "o1",
                    "accepted": True,
                    "finding": "Memex cannot prove current code without direct reads.",
                }
            ],
        },
        source_scope="foundup:foundups-agent",
        source_revision="abc123",
        allowed_foundup_ids=("foundups-agent",),
        holoindex_generation_id="generation-1",
        now_iso=FIXED_NOW,
    )


def test_memex_query_receipt_binds_projection_generation_and_source_class() -> None:
    projection = _projection()
    receipt = build_memex_projection_query_receipt(
        query="authoritative work state reconciliation",
        projection=projection,
    )

    assert receipt["source"] == MEMEX_QUERY_SOURCE
    assert receipt["source_class"] == "memex"
    assert receipt["ok"] is True
    assert receipt["freshness"] == "CURRENT"
    assert receipt["freshness_generation_id"] == "generation-1"
    assert receipt["freshness_receipt_digest"] == projection.receipt.receipt_id
    assert receipt["repo_head_sha"] == "abc123"
    assert receipt["no_holoindex_reindex_performed"] is True
    assert receipt["index_gap_detected"] is False
    assert receipt["hits"]
    assert receipt["hits"][0]["source_class"] == "memex"
    assert receipt["hits"][0]["path"].startswith("memex://sha256:brain-view/")
    assert receipt["hits"][0]["digest"].startswith("sha256:")
    assert "current_state" in receipt["hits"][0]["evidence_ref"]
    assert receipt["retrieval_verdict"] == "FOUND"
    verdicts = {item["target"]: item for item in receipt["per_target_retrieval_verdicts"]}
    assert verdicts["authoritative"]["verdict"] == "FOUND"
    assert verdicts["reconciliation"]["matched_evidence_refs"]


def test_memex_query_receipt_accepts_plain_projection_dict() -> None:
    projection = _projection()
    receipt = build_memex_projection_query_receipt(
        query="delegated authority",
        projection=projection_to_plain_dict(projection),
    )

    assert receipt["ok"] is True
    assert receipt["source_class"] == "memex"
    assert receipt["hits"]
    assert "roadmap_state" in receipt["hits"][0]["evidence_ref"]


def test_memex_query_miss_is_not_a_generation_gap() -> None:
    receipt = build_memex_projection_query_receipt(
        query="nonexistent asteroid result",
        projection=_projection(),
    )

    assert receipt["ok"] is True
    assert receipt["hits"] == []
    assert receipt["index_gap_detected"] is False
    assert receipt["retrieval_verdict"] == "MISS"
    assert all(
        item["verdict"] == "MISS"
        for item in receipt["per_target_retrieval_verdicts"]
    )
    assert receipt["stale_reasons"] == []


def test_memex_query_empty_query_fails_closed() -> None:
    receipt = build_memex_projection_query_receipt(query="", projection=_projection())

    assert receipt["ok"] is False
    assert receipt["freshness"] == "UNKNOWN"
    assert receipt["error"] == "empty_memex_query"
    assert receipt["hits"] == []


def test_memex_query_missing_projection_receipt_fails_closed() -> None:
    projection = _projection().to_dict()
    projection["receipt"] = None

    receipt = build_memex_projection_query_receipt(
        query="authoritative work state",
        projection=projection,
    )

    assert receipt["ok"] is False
    assert receipt["freshness"] == "UNKNOWN"
    assert receipt["error"] == "missing_projection_receipt"
    assert receipt["freshness_generation_id"] == ""
    assert receipt["index_gap_detected"] is False


def test_memex_query_rejected_projection_fails_closed() -> None:
    rejected = project_foundup_memex_to_holoindex_shadow(
        memex_view={"foundup_id": "other"},
        source_scope="foundup:foundups-agent",
        source_revision="abc123",
        allowed_foundup_ids=("foundups-agent",),
        now_iso=FIXED_NOW,
    )
    receipt = build_memex_projection_query_receipt(
        query="anything",
        projection=rejected,
    )

    assert receipt["ok"] is False
    assert "foundup_scope_not_authorized" in receipt["error"]
    assert receipt["hits"] == []


def test_memex_query_router_is_read_only_by_ast() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_imports = {
        "subprocess",
        "requests",
        "httpx",
        "sqlite3",
        "chromadb",
    }
    banned_calls = {
        "add",
        "upsert",
        "delete",
        "reset",
        "_reset_collection",
        "write_text",
        "write_bytes",
        "open",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned_imports
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_imports
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in banned_calls
            if isinstance(node.func, ast.Name):
                assert node.func.id not in banned_calls
