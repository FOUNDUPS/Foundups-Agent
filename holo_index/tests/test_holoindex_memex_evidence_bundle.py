from __future__ import annotations

import ast
from pathlib import Path

from holo_index.memex_evidence_bundle import (
    build_memex_content_evidence_bundle,
)
from holo_index.memex_projection_adapter import project_foundup_memex_to_holoindex_shadow
from holo_index.memex_query_routing import build_memex_projection_query_receipt


MODULE_PATH = Path(__file__).parents[1] / "memex_evidence_bundle.py"
FIXED_NOW = "2026-07-16T00:00:00+00:00"


def _projection():
    result = project_foundup_memex_to_holoindex_shadow(
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
                "selected_slice": "REDDOG_MEMEX_CONTENT_BEARING_EVIDENCE_BUNDLE_PHASE1",
                "runtime_gap": "content-bearing Memex evidence",
            },
            "roadmap_state": {
                "next_slice": "REDDOG_TYPED_EVIDENCE_CITATION_POLICY_PHASE1",
            },
        },
        source_scope="foundup:foundups-agent",
        source_revision="abc123",
        allowed_foundup_ids=("foundups-agent",),
        access_policy_digest="sha256:" + "2" * 64,
        holoindex_generation_id="generation-1",
        now_iso=FIXED_NOW,
    )
    assert result.accepted is True
    return result


def test_memex_content_evidence_bundle_includes_hit_text_with_trust_boundary() -> None:
    projection = _projection()
    receipt = build_memex_projection_query_receipt(
        query="content-bearing Memex evidence",
        projection=projection,
    )

    result = build_memex_content_evidence_bundle(
        query_receipt=receipt,
        projection=projection,
    )

    assert result.accepted is True
    assert result.bundle is not None
    assert result.bundle["schema_version"] == "holoindex_memex_content_evidence_bundle.v1"
    assert result.bundle["projection_receipt_id"] == projection.receipt.receipt_id
    assert result.bundle["query_receipt_id"] == receipt["receipt_id"]
    assert result.bundle["record_count"] == len(result.bundle["records"])
    record = result.bundle["records"][0]
    assert record["source_class"] == "memex"
    assert record["text"]
    assert record["content_digest"].startswith("sha256:")
    assert record["trust_boundary"] == "memex_memory_not_current_code_proof"
    assert result.bundle["no_holoindex_write_performed"] is True
    assert result.bundle["no_memex_write_performed"] is True


def test_memex_content_evidence_bundle_truncates_bounded_text() -> None:
    projection = _projection()
    receipt = build_memex_projection_query_receipt(
        query="content-bearing Memex evidence",
        projection=projection,
    )

    result = build_memex_content_evidence_bundle(
        query_receipt=receipt,
        projection=projection,
        max_record_chars=12,
    )

    assert result.accepted is True
    assert result.bundle is not None
    assert len(result.bundle["records"][0]["text"]) == 12
    assert result.bundle["records"][0]["text_truncated"] is True


def test_memex_content_evidence_bundle_rejects_receipt_projection_mismatch() -> None:
    projection = _projection()
    receipt = dict(
        build_memex_projection_query_receipt(
            query="content-bearing Memex evidence",
            projection=projection,
        )
    )
    receipt["freshness_receipt_digest"] = "sha256:other"

    result = build_memex_content_evidence_bundle(
        query_receipt=receipt,
        projection=projection,
    )

    assert result.accepted is False
    assert "query_projection_receipt_mismatch" in result.rejection_reasons


def test_memex_content_evidence_bundle_rejects_hit_not_in_projection() -> None:
    projection = _projection()
    receipt = dict(
        build_memex_projection_query_receipt(
            query="content-bearing Memex evidence",
            projection=projection,
        )
    )
    receipt["hits"] = [dict(receipt["hits"][0])]
    receipt["hits"][0]["evidence_ref"] = "memex:missing:missing:identity"

    result = build_memex_content_evidence_bundle(
        query_receipt=receipt,
        projection=projection,
    )

    assert result.accepted is False
    assert "query_hit_not_in_projection" in result.rejection_reasons


def test_memex_content_evidence_bundle_is_read_only_by_ast() -> None:
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
