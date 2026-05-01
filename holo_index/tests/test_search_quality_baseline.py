# -*- coding: utf-8 -*-
"""HIA3: HoloIndex Search Quality Baseline Tests

Measures search quality before BM25, Gemma reranking, or corrective RAG changes.
Records metrics truthfully - failures are expected and documented.

WSP 97: No overclaiming. Metrics reflect actual search performance.
"""

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

import pytest


@dataclass
class SentinelQuery:
    """A sentinel query with expected evidence rule."""
    query: str
    category: str
    evidence_rule: Dict[str, Any]
    description: str


SENTINEL_QUERIES: List[SentinelQuery] = [
    SentinelQuery(
        query="YouTube channel registry",
        category="code",
        evidence_rule={"path_contains": "youtube_channel_registry"},
        description="Find the YouTube channel registry module",
    ),
    SentinelQuery(
        query="demurrage economics simulator",
        category="code",
        evidence_rule={"path_contains": "demurrage"},
        description="Find the demurrage economics module",
    ),
    SentinelQuery(
        query="browser automation selenium",
        category="code",
        evidence_rule={"path_contains": "selenium"},
        description="Find Selenium browser automation code",
    ),
    SentinelQuery(
        query="WSP 97 truth distinction protocol",
        category="wsp",
        evidence_rule={"title_contains": "WSP 97"},
        description="Find WSP 97 system execution protocol",
    ),
    SentinelQuery(
        query="WSP 00 zen state attainment",
        category="wsp",
        evidence_rule={"title_contains": "WSP 00"},
        description="Find WSP 00 zen state protocol",
    ),
    SentinelQuery(
        query="module organization domains",
        category="wsp",
        evidence_rule={"path_contains": "WSP"},
        description="Find module organization WSP",
    ),
    SentinelQuery(
        query="execute_search function",
        category="symbol",
        evidence_rule={"path_contains": "search"},
        description="Find the execute_search function",
    ),
    SentinelQuery(
        query="HoloIndex class initialization",
        category="symbol",
        evidence_rule={"path_contains": "holo_index"},
        description="Find HoloIndex class",
    ),
    SentinelQuery(
        query="route_foundup_job router",
        category="symbol",
        evidence_rule={"path_contains": "foundup_job"},
        description="Find the FoundUpJob router",
    ),
    SentinelQuery(
        query="commit git workflow skill",
        category="skill",
        evidence_rule={"type_equals": "skillz"},
        description="Find commit-related skill",
    ),
    SentinelQuery(
        query="review pull request skill",
        category="skill",
        evidence_rule={"type_equals": "skillz"},
        description="Find PR review skill",
    ),
]


@dataclass
class QueryResult:
    """Result of running a single sentinel query."""
    query: str
    category: str
    description: str
    evidence_rule: Dict[str, Any]
    top_1_path: Optional[str]
    top_1_title: Optional[str]
    top_1_type: Optional[str]
    top_1_similarity: Optional[str]
    top_1_confidence: Optional[float]
    top_1_passes: bool
    top_5_passes: bool
    latency_ms: int
    error: Optional[str] = None


def _check_evidence_rule(result: Dict[str, Any], rule: Dict[str, Any]) -> bool:
    if not result:
        return False
    if "path_contains" in rule:
        path = (result.get("path") or result.get("location") or "").lower()
        if rule["path_contains"].lower() in path:
            return True
    if "title_contains" in rule:
        title = (result.get("title") or result.get("need") or "").lower()
        if rule["title_contains"].lower() in title:
            return True
    if "type_equals" in rule:
        if result.get("type") == rule["type_equals"]:
            return True
    return False


def run_sentinel_query(holo, sentinel: SentinelQuery) -> QueryResult:
    start = time.perf_counter()
    try:
        results = holo.search(sentinel.query, limit=5)
        latency_ms = int((time.perf_counter() - start) * 1000)
        all_hits = results.get("code", []) + results.get("wsps", []) + results.get("skills", [])
        top_1 = all_hits[0] if all_hits else None
        top_5 = all_hits[:5]
        top_1_passes = _check_evidence_rule(top_1, sentinel.evidence_rule) if top_1 else False
        top_5_passes = any(_check_evidence_rule(r, sentinel.evidence_rule) for r in top_5)
        return QueryResult(
            query=sentinel.query, category=sentinel.category, description=sentinel.description,
            evidence_rule=sentinel.evidence_rule,
            top_1_path=top_1.get("path") or top_1.get("location") if top_1 else None,
            top_1_title=top_1.get("title") or top_1.get("need") if top_1 else None,
            top_1_type=top_1.get("type") if top_1 else None,
            top_1_similarity=top_1.get("similarity") if top_1 else None,
            top_1_confidence=top_1.get("confidence") if top_1 else None,
            top_1_passes=top_1_passes, top_5_passes=top_5_passes, latency_ms=latency_ms,
        )
    except Exception as e:
        return QueryResult(
            query=sentinel.query, category=sentinel.category, description=sentinel.description,
            evidence_rule=sentinel.evidence_rule, top_1_path=None, top_1_title=None,
            top_1_type=None, top_1_similarity=None, top_1_confidence=None,
            top_1_passes=False, top_5_passes=False,
            latency_ms=int((time.perf_counter() - start) * 1000), error=str(e),
        )


def compute_aggregate_metrics(results: List[QueryResult]) -> Dict[str, Any]:
    total = len(results)
    if total == 0:
        return {}
    top_1_pass_count = sum(1 for r in results if r.top_1_passes)
    top_5_pass_count = sum(1 for r in results if r.top_5_passes)
    latencies = sorted([r.latency_ms for r in results])
    confidences = [r.top_1_confidence for r in results if r.top_1_confidence is not None]
    p50_idx = int(len(latencies) * 0.5)
    p95_idx = min(int(len(latencies) * 0.95), len(latencies) - 1)
    return {
        "total_queries": total,
        "top_1_pass_count": top_1_pass_count,
        "top_1_pass_rate": round(top_1_pass_count / total, 4),
        "top_5_pass_count": top_5_pass_count,
        "top_5_pass_rate": round(top_5_pass_count / total, 4),
        "confidence_min": round(min(confidences), 4) if confidences else None,
        "confidence_avg": round(sum(confidences) / len(confidences), 4) if confidences else None,
        "confidence_max": round(max(confidences), 4) if confidences else None,
        "latency_min_ms": min(latencies),
        "latency_p50_ms": latencies[p50_idx],
        "latency_p95_ms": latencies[p95_idx],
        "latency_max_ms": max(latencies),
    }


def generate_baseline_metrics():
    os.environ["HOLO_USE_TURBOQUANT"] = "0"
    os.environ["HOLO_EMIT_CONFIDENCE"] = "1"
    from holo_index.core.holo_index import HoloIndex
    holo = HoloIndex(quiet=True)
    results = [run_sentinel_query(holo, s) for s in SENTINEL_QUERIES]
    aggregate = compute_aggregate_metrics(results)
    baseline = {
        "generated_at_utc": datetime.utcnow().isoformat() + "Z",
        "holo_use_turboquant": "0",
        "holo_emit_confidence": "1",
        "corpus_doc_count": holo.get_code_entry_count() + holo.get_wsp_entry_count() + holo.get_symbol_entry_count(),
        "sentinel_query_count": len(SENTINEL_QUERIES),
        "aggregate": aggregate,
        "query_results": [asdict(r) for r in results],
    }
    output_path = Path("docs/audits/holoindex_search_quality/hia3_baseline_metrics.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(baseline, indent=2))
    print(f"Top-1 pass rate: {aggregate['top_1_pass_rate']:.1%}")
    print(f"Top-5 pass rate: {aggregate['top_5_pass_rate']:.1%}")
    return baseline


BASELINE_PATH = Path("docs/audits/holoindex_search_quality/hia3_baseline_metrics.json")


class TestBaselineMetricsExist:
    def test_baseline_file_exists(self):
        assert BASELINE_PATH.exists(), f"Run generate_baseline_metrics() first"

    def test_baseline_is_valid_json(self):
        if not BASELINE_PATH.exists():
            pytest.skip("Baseline not yet generated")
        data = json.loads(BASELINE_PATH.read_text())
        assert isinstance(data, dict)

    def test_baseline_has_required_fields(self):
        if not BASELINE_PATH.exists():
            pytest.skip("Baseline not yet generated")
        data = json.loads(BASELINE_PATH.read_text())
        for field in ["generated_at_utc", "aggregate", "query_results"]:
            assert field in data

    def test_aggregate_has_metrics(self):
        if not BASELINE_PATH.exists():
            pytest.skip("Baseline not yet generated")
        data = json.loads(BASELINE_PATH.read_text())
        agg = data.get("aggregate", {})
        for metric in ["total_queries", "top_1_pass_rate", "top_5_pass_rate", "latency_p50_ms"]:
            assert metric in agg


class TestSentinelQuerySet:
    def test_query_set_non_empty(self):
        assert len(SENTINEL_QUERIES) > 0

    def test_all_categories_covered(self):
        categories = {s.category for s in SENTINEL_QUERIES}
        assert {"code", "wsp", "symbol", "skill"} <= categories


class TestBaselineMetricsValues:
    def test_top_5_pass_rate_recorded(self):
        if not BASELINE_PATH.exists():
            pytest.skip("Baseline not yet generated")
        data = json.loads(BASELINE_PATH.read_text())
        rate = data["aggregate"].get("top_5_pass_rate")
        assert rate is not None and 0.0 <= rate <= 1.0

    def test_query_results_match_sentinel_count(self):
        if not BASELINE_PATH.exists():
            pytest.skip("Baseline not yet generated")
        data = json.loads(BASELINE_PATH.read_text())
        assert len(data["query_results"]) == data["sentinel_query_count"]


class TestNoLLMRequired:
    def test_no_gemma_import_in_baseline(self):
        import inspect
        source = inspect.getsource(__import__(__name__))
        assert "from holo_index.qwen_advisor.gemma_rag_inference" not in source

    def test_no_qwen_import_in_baseline(self):
        import inspect
        source = inspect.getsource(__import__(__name__))
        assert "from holo_index.qwen_advisor.llm_engine" not in source


if __name__ == "__main__":
    generate_baseline_metrics()
