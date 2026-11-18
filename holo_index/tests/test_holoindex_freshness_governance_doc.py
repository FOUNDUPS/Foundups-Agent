#!/usr/bin/env python3
"""Static decision-doc test for HOLOINDEX_FRESHNESS_AND_SCALING_GOVERNANCE_PHASE1.

Slice: HOLOINDEX_FRESHNESS_AND_SCALING_GOVERNANCE_PHASE1 (decision-only audit)
WSP:   50, 84, 97

This is a DECISION-ONLY audit: no runtime code, no re-index, no ranking change. The test asserts the
doc records the ruling's load-bearing anchors (RedDog query-only; the search-time auto-refresh hazard;
the invariant-holds-but-unguarded finding; the WRE-owns-maintenance owner model; the 5 sequenced
slices) and stays ASCII-clean, so the governance record cannot silently drift.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DOC = REPO_ROOT / "docs" / "audits" / "infrastructure" / "HOLOINDEX_FRESHNESS_AND_SCALING_GOVERNANCE_PHASE1.md"


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC.exists(), f"missing audit doc: {DOC}"
    return DOC.read_text(encoding="utf-8")


@pytest.mark.parametrize("anchor", [
    # decision-only boundary
    "DECISION ONLY",
    "no runtime mutation, no re-index run, no ranking-code change",
    # the resolved contradiction: RedDog query path is read-only by architecture
    "if handle_bundle_json(args): return",
    "_cli_main.py:746-747",
    "RedDog's runtime query path (`--bundle-json`) is READ-ONLY",
    # the auto-refresh hazard is documented, not hidden
    "_cli_main.py:1135-1196",
    "search-time AUTO-REFRESH",
    # the load-bearing finding
    "holds by ARCHITECTURE + CONVENTION, NOT a hard guard",
    # owner model
    "RedDog runtime:** QUERY ONLY",
    "WRE:** OWNS index maintenance",
    # direct-read masks stale index (ties to #934/#935)
    "MASK a chronically stale index",
    # the 5 sequenced slices
    "HOLOINDEX_READONLY_QUERY_GUARD_PHASE1",
    "HOLOINDEX_FRESHNESS_RECEIPT_PHASE1",
    "HOLOINDEX_INDEX_GAP_TO_WRE_WORKITEM_PHASE1",
    "HOLOINDEX_CI_FRESHNESS_GATE_PHASE1",
    "HOLOINDEX_INCREMENTAL_PER_FOUNDUP_INDEX_PHASE1",
    # scaling + security anchors
    "delete-by-`foundup_id`",
    "Single canonical store",
    # CoR-refute correction: the existing (dormant) WRE holoindex plugin write surface is enumerated
    "holoindex_plugin.py",
    "holo_singleton_manager",
    "index_all()` at :220 is a latent AttributeError",
    # WSP_97 checklist
    "AUDIT_ONLY_NO_RUNTIME_MUTATION | YES",
    "REDDOG_QUERY_PATH_READ_ONLY_VERIFIED",
])
def test_doc_contains_anchor(doc_text: str, anchor: str) -> None:
    assert anchor in doc_text, f"governance anchor missing: {anchor!r}"


def test_doc_is_decision_only_not_implementation(doc_text: str) -> None:
    # the doc must NOT claim to have implemented / run re-indexing (it is a decision record)
    lowered = doc_text.lower()
    assert "no re-index run" in lowered
    assert "audit -- decision only" in lowered or "decision only" in lowered


def test_doc_is_ascii_clean() -> None:
    raw = DOC.read_bytes()
    assert not [i for i, b in enumerate(raw) if b > 127], "audit doc must be ASCII-clean (WSP_97)"
    assert raw.count(0) == 0
