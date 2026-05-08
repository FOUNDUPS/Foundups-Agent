"""S62: Canonical Annex A holo_search adapter tests for S1.

Tests target ``canonical_search.canonical_holo_search()`` and its helpers
directly. The adapter is intentionally decoupled from the FastMCP-decorated
``server.py`` so envelope construction, request mapping, similarity scaling,
and error paths can be verified without standing up a FastMCP server.

Anchors:
  - WSP 97 (truth distinction)
  - WSP 96 Annex A.2 request schema
  - WSP 96 Annex A.3 response envelope
  - MCPA6 audit drift IDs D1-D11 (S1 portion)
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest


# Ensure the foundups-mcp-p1/servers/holo_index directory is importable so we
# can pull in `canonical_search` without touching `server.py` (which imports
# FastMCP, an optional dependency in the local venv).
_HOLO_INDEX_SERVER_DIR = Path(__file__).resolve().parents[1]
if str(_HOLO_INDEX_SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(_HOLO_INDEX_SERVER_DIR))


from canonical_search import (  # noqa: E402  (sys.path manipulation above)
    ANNEX_A_FALLBACK_RELEVANCE_CAP,
    ANNEX_A_LIMIT_DEFAULT,
    ANNEX_A_LIMIT_MAX,
    S1_SURFACE_ID,
    build_error_envelope,
    build_ok_envelope,
    canonical_holo_search,
    distance_to_similarity,
)


def _run(coro):
    """Run an async coroutine in a sync test."""
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture
def stub_backend():
    """A stub HoloIndex backend with a configurable .search side_effect."""
    backend = MagicMock()

    def _default(*_a, **_kw):
        return {
            "code_hits": [],
            "wsp_hits": [],
            "test_hits": [],
            "skill_hits": [],
            "docs_hits": [],
            "knowledge_hits": [],
            "metadata": {"engine_version": "holoindex_test_stub"},
        }

    backend.search.side_effect = _default
    return backend


# ---------------------------------------------------------------------------
# Annex A.2 request fields
# ---------------------------------------------------------------------------


class TestCanonicalRequestFields:
    """Annex A.2: holo_search MUST accept all five canonical request fields."""

    def test_query_required_and_echoed(self, stub_backend):
        result = _run(canonical_holo_search(stub_backend, query="WSP 97 audit"))
        assert result["status"] == "ok"
        assert result["data"]["query"] == "WSP 97 audit"

    def test_limit_default_passed_to_backend(self, stub_backend):
        _run(canonical_holo_search(stub_backend, query="x"))
        call_kwargs = stub_backend.search.call_args.kwargs
        assert call_kwargs["limit"] == ANNEX_A_LIMIT_DEFAULT == 10

    def test_limit_clamped_above_50(self, stub_backend):
        result = _run(canonical_holo_search(stub_backend, query="x", limit=999))
        warnings = result["data"]["metadata"]["warnings"]
        assert any("clamp" in w.lower() and "50" in w for w in warnings), (
            f"expected clamp warning naming 50; got {warnings}"
        )
        # Backend MUST receive the clamped limit, not the request value
        call_kwargs = stub_backend.search.call_args.kwargs
        assert call_kwargs["limit"] == 50

    def test_limit_clamped_below_1(self, stub_backend):
        result = _run(canonical_holo_search(stub_backend, query="x", limit=0))
        warnings = result["data"]["metadata"]["warnings"]
        assert any("clamp" in w.lower() for w in warnings)
        call_kwargs = stub_backend.search.call_args.kwargs
        assert call_kwargs["limit"] == 1

    def test_invalid_limit_falls_back_to_default(self, stub_backend):
        result = _run(
            canonical_holo_search(stub_backend, query="x", limit="not_a_number")
        )
        assert result["status"] == "ok"
        warnings = result["data"]["metadata"]["warnings"]
        assert any("invalid limit" in w.lower() for w in warnings)

    def test_doc_type_filter_passed_through_to_backend(self, stub_backend):
        _run(canonical_holo_search(stub_backend, query="x", doc_type_filter="wsp"))
        call_kwargs = stub_backend.search.call_args.kwargs
        assert call_kwargs["doc_type_filter"] == "wsp"

    def test_doc_type_filter_echoed_in_data(self, stub_backend):
        result = _run(
            canonical_holo_search(stub_backend, query="x", doc_type_filter="wsp")
        )
        assert result["data"]["doc_type_filter"] == "wsp"

    def test_foundup_id_accepted_and_echoed(self, stub_backend):
        result = _run(
            canonical_holo_search(stub_backend, query="x", foundup_id="gotjunk")
        )
        assert result["data"]["foundup_id"] == "gotjunk"

    def test_include_shared_with_foundup_id_echoed(self, stub_backend):
        result = _run(
            canonical_holo_search(
                stub_backend,
                query="x",
                foundup_id="kosei",
                include_shared=False,
            )
        )
        assert result["data"]["include_shared"] is False

    def test_include_shared_null_when_no_foundup_id(self, stub_backend):
        result = _run(
            canonical_holo_search(stub_backend, query="x", include_shared=False)
        )
        assert result["data"]["include_shared"] is None

    def test_foundup_id_unenforced_warning_surfaces(self, stub_backend):
        result = _run(
            canonical_holo_search(stub_backend, query="x", foundup_id="gotjunk")
        )
        warnings = result["data"]["metadata"]["warnings"]
        assert any(
            "foundup_id" in w and "not yet enforced" in w for w in warnings
        ), f"expected unenforced-tenant warning; got {warnings}"


# ---------------------------------------------------------------------------
# Annex A.3 response envelope shape
# ---------------------------------------------------------------------------


class TestCanonicalResponseEnvelope:
    """Annex A.3: response shape must be {status, data, meta} with explicit fields."""

    def test_top_level_status_present(self, stub_backend):
        result = _run(canonical_holo_search(stub_backend, query="x"))
        assert "status" in result
        assert result["status"] == "ok"

    def test_top_level_data_block_present(self, stub_backend):
        result = _run(canonical_holo_search(stub_backend, query="x"))
        assert "data" in result
        for key in (
            "query",
            "doc_type_filter",
            "foundup_id",
            "include_shared",
            "hits",
            "hit_count",
            "metadata",
        ):
            assert key in result["data"], f"data.{key} missing"

    def test_top_level_meta_block_present(self, stub_backend):
        result = _run(canonical_holo_search(stub_backend, query="x"))
        assert "meta" in result
        for key in ("timestamp", "source", "tool", "surface", "confidence"):
            assert key in result["meta"], f"meta.{key} missing"

    def test_meta_surface_is_s1(self, stub_backend):
        result = _run(canonical_holo_search(stub_backend, query="x"))
        assert result["meta"]["surface"] == "S1"

    def test_meta_tool_is_holo_search(self, stub_backend):
        result = _run(canonical_holo_search(stub_backend, query="x"))
        assert result["meta"]["tool"] == "holo_search"

    def test_meta_source_is_holoindex_on_success(self, stub_backend):
        result = _run(canonical_holo_search(stub_backend, query="x"))
        assert result["meta"]["source"] == "holoindex"

    def test_data_metadata_canonical_keys_present(self, stub_backend):
        result = _run(canonical_holo_search(stub_backend, query="x"))
        meta = result["data"]["metadata"]
        for key in (
            "retrieval_mode",
            "engine_version",
            "collections_searched",
            "warnings",
        ):
            assert key in meta, f"data.metadata.{key} missing"

    def test_data_metadata_retrieval_mode_truthful(self, stub_backend):
        result = _run(canonical_holo_search(stub_backend, query="x"))
        assert result["data"]["metadata"]["retrieval_mode"] == "semantic"

    def test_legacy_split_keys_absent_from_data(self, stub_backend):
        """The legacy `code_results`/`wsp_results` split MUST NOT appear in
        the canonical envelope. All hits live in unified `hits[]`."""
        result = _run(canonical_holo_search(stub_backend, query="x"))
        assert "code_results" not in result["data"]
        assert "wsp_results" not in result["data"]
        assert "total_results" not in result["data"]

    def test_quantum_decoration_absent_from_data(self, stub_backend):
        """Legacy `quantum_coherence` and `bell_state_alignment` decoration
        fields MUST NOT appear in the canonical envelope (Annex A.3 D6)."""
        result = _run(canonical_holo_search(stub_backend, query="x"))
        result_str = repr(result).lower()
        assert "quantum_coherence" not in result_str
        assert "bell_state_alignment" not in result_str


# ---------------------------------------------------------------------------
# Unified hit shape
# ---------------------------------------------------------------------------


class TestUnifiedHitShape:
    """Annex A.3: hits[] is a single array with `type` discriminator."""

    def test_hits_unified_with_type_discriminator(self, stub_backend):
        stub_backend.search.side_effect = lambda *_a, **_kw: {
            "code_hits": [
                {
                    "path": "modules/foo.py",
                    "preview": "code1",
                    "distance": 0.2,
                    "line": 10,
                }
            ],
            "wsp_hits": [
                {
                    "path": "WSP_framework/src/WSP_97.md",
                    "title": "WSP 97",
                    "summary": "summary97",
                    "distance": 0.3,
                }
            ],
            "skill_hits": [
                {
                    "path": ".claude/skills/foo/SKILL.md",
                    "name": "foo",
                    "preview": "skill1",
                    "distance": 0.5,
                }
            ],
            "metadata": {"engine_version": "test"},
        }

        result = _run(canonical_holo_search(stub_backend, query="anything", limit=10))
        hits = result["data"]["hits"]
        types = {h["type"] for h in hits}
        assert types == {"code", "wsp", "skill"}, (
            f"expected unified hits across types; got {types}"
        )
        for h in hits:
            assert "type" in h
            assert "path" in h
            # Every hit in this test had a usable distance, so relevance present
            assert "relevance" in h

    def test_hit_count_matches_hits_length(self, stub_backend):
        stub_backend.search.side_effect = lambda *_a, **_kw: {
            "code_hits": [{"path": "a.py", "distance": 0.1}],
            "wsp_hits": [{"path": "b.md", "distance": 0.2}],
            "metadata": {},
        }
        result = _run(canonical_holo_search(stub_backend, query="x"))
        assert result["data"]["hit_count"] == len(result["data"]["hits"])

    def test_hits_sorted_by_relevance_desc(self, stub_backend):
        stub_backend.search.side_effect = lambda *_a, **_kw: {
            "code_hits": [
                {"path": "low.py", "distance": 4.0},  # low relevance
                {"path": "high.py", "distance": 0.1},  # high relevance
                {"path": "mid.py", "distance": 1.0},
            ],
            "metadata": {},
        }
        result = _run(canonical_holo_search(stub_backend, query="x"))
        relevances = [h["relevance"] for h in result["data"]["hits"]]
        assert relevances == sorted(relevances, reverse=True)


# ---------------------------------------------------------------------------
# Relevance transform (Annex A.3 rule)
# ---------------------------------------------------------------------------


class TestRelevanceTransform:
    """Annex A.3: relevance = 1 / (1 + distance) for ChromaDB cosine distance."""

    def test_distance_zero_yields_one(self):
        assert distance_to_similarity(0) == 1.0

    def test_distance_one_yields_half(self):
        assert distance_to_similarity(1.0) == pytest.approx(0.5)

    def test_distance_three_yields_quarter(self):
        # 1 / (1 + 3) = 0.25
        # But 3.0 > 1.0 so the special-case "already similarity" branch is skipped,
        # falling through to the formula.
        assert distance_to_similarity(3.0) == pytest.approx(0.25)

    def test_formula_applied_uniformly_no_passthrough(self):
        """Per Annex A.3, the formula is applied uniformly — there is no
        special "already similarity" passthrough branch. ChromaDB cosine
        distance ranges over [0..2]; a value of 0.5 means similarity
        1/(1+0.5) ≈ 0.667, not 0.5."""
        # distance 0.5 → 1/(1.5) ≈ 0.6667
        assert distance_to_similarity(0.5) == pytest.approx(0.6667, abs=0.01)
        # distance 0.85 → 1/(1.85) ≈ 0.5405
        assert distance_to_similarity(0.85) == pytest.approx(0.5405, abs=0.01)

    def test_invalid_returns_none(self):
        assert distance_to_similarity("not_a_number") is None
        assert distance_to_similarity(None) is None
        assert distance_to_similarity(-1) is None
        assert distance_to_similarity([]) is None

    def test_relevance_in_unit_interval_on_real_results(self, stub_backend):
        stub_backend.search.side_effect = lambda *_a, **_kw: {
            "code_hits": [
                {"path": "a.py", "distance": 0.5},
                {"path": "b.py", "distance": 2.0},
            ],
            "metadata": {},
        }
        result = _run(canonical_holo_search(stub_backend, query="x"))
        for hit in result["data"]["hits"]:
            rel = hit["relevance"]
            assert 0.0 <= rel <= 1.0, f"relevance must be in [0..1]; got {rel}"

    def test_no_raw_distance_in_canonical_hits(self, stub_backend):
        """The legacy practice of returning raw `distance` MUST NOT leak
        into the canonical envelope (Annex A.3 D5)."""
        stub_backend.search.side_effect = lambda *_a, **_kw: {
            "code_hits": [{"path": "a.py", "distance": 5.0}],
            "metadata": {},
        }
        result = _run(canonical_holo_search(stub_backend, query="x"))
        for hit in result["data"]["hits"]:
            assert "distance" not in hit

    def test_relevance_omitted_when_unavailable(self, stub_backend):
        """WSP 97: surfaces that cannot compute similarity MUST omit the
        field rather than fabricate one."""
        stub_backend.search.side_effect = lambda *_a, **_kw: {
            # No `distance`, no `similarity` — engine produced no signal.
            "code_hits": [{"path": "a.py", "preview": "x"}],
            "metadata": {},
        }
        result = _run(canonical_holo_search(stub_backend, query="x"))
        assert len(result["data"]["hits"]) == 1
        assert "relevance" not in result["data"]["hits"][0], (
            "relevance MUST be omitted when not computable, not fabricated"
        )


# ---------------------------------------------------------------------------
# Empty-query rejection (Annex A.3 EMPTY_QUERY error)
# ---------------------------------------------------------------------------


class TestEmptyQueryRejection:
    """Annex A.2: empty/whitespace query MUST return EMPTY_QUERY error."""

    def test_empty_string_rejected(self, stub_backend):
        result = _run(canonical_holo_search(stub_backend, query=""))
        assert result["status"] == "error"
        assert isinstance(result["error"], dict)
        assert result["error"]["code"] == "EMPTY_QUERY"

    def test_whitespace_only_rejected(self, stub_backend):
        result = _run(canonical_holo_search(stub_backend, query="   \t\n   "))
        assert result["status"] == "error"
        assert result["error"]["code"] == "EMPTY_QUERY"

    def test_empty_query_meta_carries_surface(self, stub_backend):
        result = _run(canonical_holo_search(stub_backend, query=""))
        assert result["meta"]["surface"] == "S1"
        assert result["meta"]["tool"] == "holo_search"

    def test_empty_query_does_not_call_backend(self, stub_backend):
        _run(canonical_holo_search(stub_backend, query=""))
        # The backend MUST NOT be invoked when the request is rejected up front.
        assert not stub_backend.search.called


# ---------------------------------------------------------------------------
# Backend error handling
# ---------------------------------------------------------------------------


class TestBackendErrorHandling:
    """Backend exceptions surface as canonical BACKEND_UNAVAILABLE error."""

    def test_backend_exception_returns_canonical_error(self, stub_backend):
        stub_backend.search.side_effect = RuntimeError("boom")
        result = _run(canonical_holo_search(stub_backend, query="x"))
        assert result["status"] == "error"
        assert result["error"]["code"] == "BACKEND_UNAVAILABLE"
        assert "boom" in result["error"]["message"]
        assert result["meta"]["surface"] == "S1"

    def test_backend_returns_non_dict_handled(self, stub_backend):
        """If the backend returns something other than a dict, the adapter
        emits a BACKEND_UNAVAILABLE rather than crashing."""
        stub_backend.search.side_effect = lambda *_a, **_kw: "not a dict"
        result = _run(canonical_holo_search(stub_backend, query="x"))
        assert result["status"] == "error"
        assert result["error"]["code"] == "BACKEND_UNAVAILABLE"


# ---------------------------------------------------------------------------
# Module constants (defensive)
# ---------------------------------------------------------------------------


class TestModuleConstants:
    """Defensive: prevent accidental constant removal."""

    def test_surface_id_constant_is_s1(self):
        assert S1_SURFACE_ID == "S1"

    def test_limit_max_is_50(self):
        assert ANNEX_A_LIMIT_MAX == 50

    def test_limit_default_is_10(self):
        assert ANNEX_A_LIMIT_DEFAULT == 10

    def test_fallback_relevance_cap_is_06(self):
        assert ANNEX_A_FALLBACK_RELEVANCE_CAP == 0.6


# ---------------------------------------------------------------------------
# Envelope builders (unit-tested independently)
# ---------------------------------------------------------------------------


class TestEnvelopeBuilders:
    """build_ok_envelope and build_error_envelope produce conformant shapes."""

    def test_build_ok_envelope_basic_shape(self):
        result = build_ok_envelope(
            query="q",
            doc_type_filter="all",
            foundup_id=None,
            include_shared=True,
            hits=[],
            engine_metadata={},
            retrieval_mode="semantic",
            source="holoindex",
            confidence=0.8,
            warnings=[],
        )
        assert result["status"] == "ok"
        assert result["data"]["query"] == "q"
        assert result["meta"]["surface"] == "S1"
        assert result["meta"]["tool"] == "holo_search"

    def test_build_error_envelope_basic_shape(self):
        result = build_error_envelope(
            code="EMPTY_QUERY",
            message="why",
        )
        assert result["status"] == "error"
        assert result["error"]["code"] == "EMPTY_QUERY"
        assert result["error"]["message"] == "why"
        assert result["meta"]["surface"] == "S1"

    def test_build_error_envelope_with_details(self):
        result = build_error_envelope(
            code="BACKEND_UNAVAILABLE",
            message="boom",
            details={"upstream": "ChromaDB"},
        )
        assert result["error"]["details"] == {"upstream": "ChromaDB"}


# ---------------------------------------------------------------------------
# Direct invocation example (slice spec required)
# ---------------------------------------------------------------------------


class TestDirectInvocationExample:
    """Slice spec: one direct invocation showing canonical request + envelope."""

    def test_direct_canonical_call_full_shape(self, stub_backend):
        stub_backend.search.side_effect = lambda *_a, **_kw: {
            "code_hits": [
                {"path": "modules/example.py", "preview": "def f(): ...", "distance": 0.4, "line": 10},
            ],
            "wsp_hits": [
                {"path": "WSP_framework/src/WSP_96_*.md", "title": "WSP 96",
                 "summary": "MCP Governance + Annex A canonical contract", "distance": 0.2},
            ],
            "metadata": {"engine_version": "holoindex_v1", "collections_searched": ["navigation_code", "navigation_wsp"]},
        }

        result = _run(
            canonical_holo_search(
                stub_backend,
                query="WSP 96 holo_search",
                limit=5,
                doc_type_filter="all",
                foundup_id="gotjunk",
                include_shared=True,
            )
        )

        # Annex A.3 shape
        assert result["status"] == "ok"
        assert result["data"]["query"] == "WSP 96 holo_search"
        assert result["data"]["doc_type_filter"] == "all"
        assert result["data"]["foundup_id"] == "gotjunk"
        assert result["data"]["include_shared"] is True
        assert result["data"]["hit_count"] == 2
        # Unified hits
        types = {h["type"] for h in result["data"]["hits"]}
        assert types == {"code", "wsp"}
        # Relevance transformed (no raw distance)
        for h in result["data"]["hits"]:
            assert 0 <= h["relevance"] <= 1
            assert "distance" not in h
        # Truthful metadata
        assert result["data"]["metadata"]["retrieval_mode"] == "semantic"
        assert result["data"]["metadata"]["engine_version"] == "holoindex_v1"
        # Truthful warning surfaces unenforced foundup_id
        assert any(
            "foundup_id" in w and "not yet enforced" in w
            for w in result["data"]["metadata"]["warnings"]
        )
        # Meta block
        assert result["meta"]["surface"] == "S1"
        assert result["meta"]["tool"] == "holo_search"
        assert result["meta"]["source"] == "holoindex"
