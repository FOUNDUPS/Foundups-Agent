"""Tests for HOLOINDEX_QUERY_RECEIPT_AND_GENERATION_BINDING_PHASE1."""

from __future__ import annotations

from pathlib import Path

import pytest

from holo_index.freshness_receipt import (
    CollectionFreshness,
    HoloIndexFreshnessReceipt,
    write_freshness_receipt,
)
from holo_index.query_receipt import (
    SCHEMA_VERSION,
    SEMANTIC_EVIDENCE_SCHEMA_VERSION,
    SOURCE_CLASS_HOLOINDEX,
    build_query_receipt,
    canonical_semantic_evidence,
    load_generation_binding,
)
from modules.infrastructure.foundups_mcp_bridge.src.holo_query_path_projection import (
    project_result_hit,
)


def _freshness_receipt() -> HoloIndexFreshnessReceipt:
    return HoloIndexFreshnessReceipt(
        schema_version="holoindex_freshness_receipt.v1",
        generated_at="2026-07-16T00:00:00+00:00",
        repo_root="O:/Foundups-Agent",
        repo_head_sha="abc123",
        ssd_path="E:/HoloIndex",
        source="test",
        generation_id="sha256:generation",
        collections=[
            CollectionFreshness(
                name="navigation_code",
                count=1,
                status="indexed",
                source="test",
                repo_head_sha="abc123",
                last_indexed_at="2026-07-16T00:00:00+00:00",
                source_manifest_digest="sha256:manifest",
                indexed_paths_digest="sha256:paths",
                removed_paths_digest="sha256:removed",
                verification="PASS",
                proof_kind="complete_source_manifest",
            )
        ],
    )


def test_load_generation_binding_from_freshness_receipt(tmp_path: Path) -> None:
    path = tmp_path / "indexes" / "holoindex_freshness_receipt.json"
    write_freshness_receipt(_freshness_receipt(), path)

    binding = load_generation_binding(receipt_path=path)

    assert binding["freshness_generation_id"] == "sha256:generation"
    assert binding["freshness_receipt_digest"].startswith("sha256:")
    assert binding["freshness_receipt_path"] == str(path)
    assert binding["repo_head_sha"] == "abc123"


def test_query_receipt_binds_generation_and_hits() -> None:
    receipt = build_query_receipt(
        source="holoindex",
        source_class=SOURCE_CLASS_HOLOINDEX,
        query="RedDog operational loop",
        result={
            "ok": True,
            "query": "RedDog operational loop",
            "freshness": "CURRENT",
            "retrieval_runtime_ranker_digest": "sha256:" + "a" * 64,
            "hits": [{"path": "holo_index/query_receipt.py", "title": "query receipts", "score": 0.9}],
        },
        require_generation=True,
        generation_binding={
            "freshness_generation_id": "sha256:generation",
            "freshness_receipt_digest": "sha256:freshness",
            "freshness_receipt_path": "E:/HoloIndex/indexes/holoindex_freshness_receipt.json",
            "repo_head_sha": "abc123",
        },
    )

    assert receipt["schema_version"] == SCHEMA_VERSION
    assert receipt["receipt_id"].startswith("sha256:")
    assert receipt["freshness_generation_id"] == "sha256:generation"
    assert receipt["hits"][0]["source_class"] == SOURCE_CLASS_HOLOINDEX
    assert receipt["semantic_evidence_digest"].startswith("sha256:")
    assert receipt["semantic_evidence_count"] == 0
    assert receipt["no_holoindex_reindex_performed"] is True
    assert receipt["retrieval_runtime_ranker_digest"] == "sha256:" + "a" * 64


def test_canonical_semantic_evidence_binds_buckets_metadata_and_count() -> None:
    serialized, digest, count = canonical_semantic_evidence(
        {
            "code_hits": [
                {
                    "path": "holo_index/query_receipt.py",
                    "preview": "Canonical evidence binding.",
                }
            ],
            "docs_hits": [{"path": "docs/architecture.md", "title": "Architecture"}],
            "metadata": {"retrieval_mode": "semantic"},
            "untrusted_extra": [{"path": "ignored.py"}],
        }
    )

    assert f'"schema_version":"{SEMANTIC_EVIDENCE_SCHEMA_VERSION}"' in serialized
    assert '"untrusted_extra"' not in serialized
    assert digest.startswith("sha256:")
    assert count == 2


def test_semantic_evidence_uses_projected_owner_paths() -> None:
    test_hit = project_result_hit(
        {"location": r"E:\Agents\root\tests\test_a.py"}, r"E:\Agents\root"
    )
    skill_hit = project_result_hit(
        {"path": r"E:\Agents\root\skillz\a\SKILLz.md"}, r"E:\Agents\root"
    )
    raw = {"tests": [test_hit], "skills": [skill_hit],
           "test_hits": [test_hit], "skill_hits": [skill_hit]}
    serialized, _digest, count = canonical_semantic_evidence(raw)
    assert "E:/Agents/root" not in serialized
    assert "E:\\\\Agents\\\\root" not in serialized
    assert '"location":"tests/test_a.py"' in serialized
    assert '"path":"skillz/a/SKILLz.md"' in serialized
    assert count == 2


def test_canonical_semantic_evidence_rejects_oversized_payload() -> None:
    with pytest.raises(ValueError, match="semantic_evidence_too_large"):
        canonical_semantic_evidence(
            {"code_hits": [{"preview": "x" * 128}]},
            max_bytes=32,
        )


def test_query_receipt_digest_changes_when_semantic_evidence_changes() -> None:
    base = {
        "ok": True,
        "query": "RedDog operational loop",
        "freshness": "CURRENT",
        "hits": [],
        "raw_result": {
            "code_hits": [{"path": "holo_index/query_receipt.py", "preview": "before"}]
        },
    }
    binding = {
        "freshness_generation_id": "sha256:generation",
        "freshness_receipt_digest": "sha256:freshness",
        "repo_head_sha": "abc123",
    }

    before = build_query_receipt(
        source="holoindex",
        source_class=SOURCE_CLASS_HOLOINDEX,
        query="RedDog operational loop",
        result=base,
        require_generation=True,
        generation_binding=binding,
    )
    changed = build_query_receipt(
        source="holoindex",
        source_class=SOURCE_CLASS_HOLOINDEX,
        query="RedDog operational loop",
        result={
            **base,
            "raw_result": {
                "code_hits": [
                    {"path": "holo_index/query_receipt.py", "preview": "after"}
                ]
            },
        },
        require_generation=True,
        generation_binding=binding,
    )

    assert before["semantic_evidence_count"] == 1
    assert before["semantic_evidence_digest"] != changed["semantic_evidence_digest"]
    assert before["receipt_id"] != changed["receipt_id"]


def test_query_receipt_binds_observed_latency() -> None:
    binding = {
        "freshness_generation_id": "sha256:generation",
        "freshness_receipt_digest": "sha256:freshness",
        "repo_head_sha": "abc123",
    }
    base = {
        "ok": True,
        "query": "latency evidence",
        "freshness": "CURRENT",
        "hits": [],
        "latency_ms": 12.3456,
    }
    before = build_query_receipt(
        source="holoindex", source_class=SOURCE_CLASS_HOLOINDEX,
        query="latency evidence", result=base, require_generation=True,
        generation_binding=binding,
    )
    changed = build_query_receipt(
        source="holoindex", source_class=SOURCE_CLASS_HOLOINDEX,
        query="latency evidence", result={**base, "latency_ms": 99},
        require_generation=True, generation_binding=binding,
    )

    assert before["observed_latency_ms"] == 12.346
    assert before["receipt_id"] != changed["receipt_id"]


def test_query_receipt_respects_explicit_benchmark_hit_limit() -> None:
    hits = [{"path": f"module-{index}.py"} for index in range(12)]
    receipt = build_query_receipt(
        source="benchmark", source_class=SOURCE_CLASS_HOLOINDEX,
        query="deep ranking", result={
            "ok": True, "freshness": "CURRENT", "hits": hits,
        },
        require_generation=True,
        generation_binding={
            "freshness_generation_id": "sha256:generation",
            "freshness_receipt_digest": "sha256:freshness",
            "repo_head_sha": "abc123",
        },
        hit_limit=20,
    )

    assert len(receipt["hits"]) == 12


def test_fresh_query_without_generation_is_stale_not_fresh() -> None:
    receipt = build_query_receipt(
        source="holoindex",
        source_class=SOURCE_CLASS_HOLOINDEX,
        query="RedDog operational loop",
        result={
            "ok": True,
            "query": "RedDog operational loop",
            "freshness": "CURRENT",
            "hits": [{"path": "holo_index/query_receipt.py"}],
        },
        require_generation=True,
    )

    assert receipt["ok"] is True
    assert receipt["freshness"] == "UNKNOWN"
    assert receipt["index_gap_detected"] is True
    assert "missing_holoindex_generation_id" in receipt["stale_reasons"]


def test_query_receipt_does_not_claim_reindex_or_command_authority() -> None:
    receipt = build_query_receipt(
        source="holoindex",
        source_class=SOURCE_CLASS_HOLOINDEX,
        query="status",
        result={"ok": False, "freshness": "UNKNOWN", "hits": [], "error": "offline"},
        require_generation=True,
    )

    assert receipt["no_holoindex_reindex_performed"] is True
    assert "command" not in receipt
    assert "subprocess" not in receipt


def test_query_receipt_binds_valid_owner_acquisition_telemetry() -> None:
    receipt = build_query_receipt(
        source="holoindex_owner_service",
        source_class=SOURCE_CLASS_HOLOINDEX,
        query="owner readiness",
        result={
            "ok": False,
            "freshness": "UNKNOWN",
            "error": "SEMANTIC_BACKEND_UNAVAILABLE",
            "owner_attempts": 2,
            "owner_retry_performed": True,
            "owner_retry_reason": "SEMANTIC_BACKEND_UNAVAILABLE",
            "owner_acquisition_cycle": 1,
        },
        require_generation=True,
    )

    assert receipt["owner_attempts"] == 2
    assert receipt["owner_retry_performed"] is True
    assert receipt["owner_retry_reason"] == "SEMANTIC_BACKEND_UNAVAILABLE"
    assert receipt["owner_acquisition_cycle"] == 1


@pytest.mark.parametrize("cycle", [True, -1, 32, "1"])
def test_query_receipt_omits_invalid_owner_acquisition_cycle(cycle: object) -> None:
    receipt = build_query_receipt(
        source="holoindex_owner_service",
        source_class=SOURCE_CLASS_HOLOINDEX,
        query="owner readiness",
        result={"ok": False, "freshness": "UNKNOWN", "error": "offline",
                "owner_acquisition_cycle": cycle},
        require_generation=True,
    )
    assert "owner_acquisition_cycle" not in receipt


def test_query_receipt_preserves_adapter_stale_reasons() -> None:
    receipt = build_query_receipt(
        source="holoindex",
        source_class=SOURCE_CLASS_HOLOINDEX,
        query="WSP 97 evidence",
        result={
            "ok": True,
            "freshness": "STALE",
            "hits": [{"path": "WSP_framework/src/WSP_97_Truth_Boundary_Protocol.md"}],
            "stale_reasons": [
                "stale_repo_head_sha",
                "collection_verification_not_pass:navigation_wsp",
                "stale_repo_head_sha",
            ],
            "freshness_generation_id": "sha256:generation",
            "freshness_receipt_digest": "sha256:freshness",
        },
        require_generation=True,
    )

    assert receipt["ok"] is True
    assert receipt["freshness"] == "STALE"
    assert receipt["stale_reasons"] == [
        "stale_repo_head_sha",
        "collection_verification_not_pass:navigation_wsp",
    ]
    assert receipt["index_gap_detected"] is True


def test_stale_query_receipt_sets_index_gap_with_generation_proof() -> None:
    receipt = build_query_receipt(
        source="holoindex",
        source_class=SOURCE_CLASS_HOLOINDEX,
        query="research evidence",
        result={
            "ok": True,
            "freshness": "STALE",
            "hits": [],
            "freshness_generation_id": "sha256:generation",
            "freshness_receipt_digest": "sha256:freshness",
        },
        require_generation=True,
    )

    assert receipt["freshness_generation_id"] == "sha256:generation"
    assert receipt["freshness_receipt_digest"] == "sha256:freshness"
    assert receipt["index_gap_detected"] is True
