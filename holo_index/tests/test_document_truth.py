"""Current-truth authority classification regressions."""

from __future__ import annotations

import pytest

from holo_index.core import search_engine
from holo_index.document_truth import (
    CURRENT_TRUTH,
    HISTORICAL_RECORD,
    IMPLEMENTATION_EVIDENCE,
    UNCLASSIFIED,
    VISION,
    classify_document_truth,
    current_truth_rank,
    query_requests_current_truth,
)


@pytest.mark.parametrize(
    ("item", "expected"),
    [
        ({"path": "holo_index/README.md", "type": "module_readme"}, CURRENT_TRUTH),
        ({"path": "WSP_framework/src/WSP_48_RSI.md", "type": "wsp_protocol"}, CURRENT_TRUTH),
        ({"path": "holo_index/core/search_engine.py", "type": "symbol"}, IMPLEMENTATION_EVIDENCE),
        ({"path": "modules/infrastructure/audit_logger.py", "type": "symbol"}, IMPLEMENTATION_EVIDENCE),
        ({"path": "holo_index/cleanup_strategy.py", "type": "code"}, IMPLEMENTATION_EVIDENCE),
        ({"path": "docs/audits/holoindex/REPORT.md", "type": "documentation"}, HISTORICAL_RECORD),
        ({"path": "docs/audits/holoindex/audit_repair.py", "type": "code"}, HISTORICAL_RECORD),
        ({"path": "holo_index/docs/audits/PARALLEL_SYSTEMS_AUDIT.md", "type": "documentation"}, HISTORICAL_RECORD),
        ({"path": "modules/example/docs/audits/REPORT.md", "type": "documentation"}, HISTORICAL_RECORD),
        ({"path": "holo_index/docs/README.md", "type": "readme"}, HISTORICAL_RECORD),
        ({"path": "holo_index/docs/CLEANUP_REPORT.md", "type": "documentation"}, HISTORICAL_RECORD),
        ({"path": "holo_index/CLI_REFERENCE.md", "type": "documentation"}, UNCLASSIFIED),
        ({"path": "holo_index/ModLog.md", "type": "modlog"}, HISTORICAL_RECORD),
        ({"path": "modules/infrastructure/foundups_vision/README.md", "type": "readme"}, VISION),
        ({"path": "notes.txt", "type": "other"}, UNCLASSIFIED),
    ],
)
def test_document_truth_class_is_low_cardinality(item: dict, expected: str) -> None:
    assert classify_document_truth(item) == expected


@pytest.mark.parametrize(
    "query",
    [
        "Is HoloIndex RSI working and what is missing?",
        "current HoloIndex A grade status",
        "what is HoloIndex doing now",
    ],
)
def test_broad_state_questions_request_current_truth(query: str) -> None:
    assert query_requests_current_truth(query)


@pytest.mark.parametrize(
    "query",
    [
        "historical HoloIndex baseline",
        "latest historical HoloIndex baseline",
        "what was HoloIndex status in 2025",
        "HoloIndex status last year",
        "HoloIndex status before 2026",
        "HoloIndex status yesterday",
        "HOLOINDEX_T1_RANKING_QUALITY_PHASE1",
        "PR #1582 evidence",
        "current status for pr 1532",
        "current status CFZ4",
        "current status hxa22",
        "semantic ranking algorithm",
    ],
)
def test_history_exact_targets_and_general_queries_preserve_semantic_order(
    query: str,
) -> None:
    assert not query_requests_current_truth(query)


def test_current_truth_rank_orders_contract_then_code_then_history() -> None:
    query = "Is HoloIndex RSI working and what remains missing?"
    assert current_truth_rank(query, {"path": "holo_index/README.md"}) == 4
    assert current_truth_rank(query, {"path": "holo_index/core/search_engine.py"}) == 3
    assert current_truth_rank(query, {"path": "notes.txt"}) == 2
    assert current_truth_rank(query, {"path": "docs/audits/holoindex/OLD.md"}) == 0


def test_current_truth_docs_search_oversamples_then_deduplicates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[int] = []
    candidates = [
        {"path": "holo_index/README.md"},
        {"path": "HOLO_INDEX/README.md"},
        {"path": "holo_index/INTERFACE.md"},
        {"path": "docs/audits/holoindex/OLD.md"},
    ]

    def search(*_args, **kwargs):
        observed.append(_args[3])
        return candidates

    monkeypatch.setattr(search_engine, "_search_collection", search)
    results = search_engine._docs_search(
        object(), object(), "current HoloIndex status", 2, (), None, (),
    )

    assert observed == [8, 8]
    assert [item["path"] for item in results] == [
        "holo_index/README.md",
        "holo_index/INTERFACE.md",
    ]


def test_historical_docs_search_does_not_oversample(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[int] = []

    def search(*_args, **kwargs):
        observed.append(_args[3])
        return []

    monkeypatch.setattr(search_engine, "_search_collection", search)
    assert search_engine._docs_search(
        object(), object(), "historical HoloIndex baseline", 3, (), None, (),
    ) == []
    assert observed == [3]


def test_current_docs_search_ranks_authority_before_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidates = [
        {"path": "docs/audits/holoindex/OLD_ONE.md"},
        {"path": "holo_index/docs/audits/OLD_TWO.md"},
        {"path": "holo_index/README.md"},
        {"path": "holo_index/INTERFACE.md"},
    ]
    monkeypatch.setattr(search_engine, "_search_collection", lambda *_a, **_k: candidates)

    results = search_engine._docs_search(
        object(), object(), "current HoloIndex status", 2, (), None, (),
    )

    assert [item["path"] for item in results] == [
        "holo_index/README.md", "holo_index/INTERFACE.md",
    ]


def test_current_docs_search_preserves_diversity_under_duplicate_sections(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    section_candidates = [
        {"path": "holo_index/README.md", "section": index}
        for index in range(60)
    ]
    summary_candidates = [
        {"path": "holo_index/README.md"},
        {"path": "holo_index/INTERFACE.md"},
        {"path": "holo_index/ROADMAP.md"},
    ]
    observed: list[tuple[int, bool]] = []

    def search(*args, **kwargs):
        candidate_limit = args[3]
        summary_only = bool(kwargs.get("metadata_where"))
        observed.append((candidate_limit, summary_only))
        pool = summary_candidates if summary_only else section_candidates
        return pool[:candidate_limit]

    monkeypatch.setattr(search_engine, "_search_collection", search)

    results = search_engine._docs_search(
        object(), object(), "current HoloIndex status", 3, (), None, (),
    )

    assert [item["path"] for item in results] == [
        "holo_index/README.md", "holo_index/INTERFACE.md", "holo_index/ROADMAP.md",
    ]
    assert observed == [(12, False), (12, True)]
