"""
MCPA4 honesty tests for pAVS MCP Server (S3).

Verifies that every response from the placeholder surface carries the
canonical truth flag so clients cannot mistake hardcoded data for real
backend output. Anchored to:

  - WSP 97 (truth distinction)
  - WSP 96 Annex A.5 conformance gate (C3: truthful meta.source)
  - MCPA1 audit findings (S3 = PLACEHOLDER_STUB)

These tests do NOT require any live transport or backend.
"""

from __future__ import annotations

import asyncio

import pytest

from modules.infrastructure.pavs_mcp.src import server as pavs_server
from modules.infrastructure.pavs_mcp.src.server import (
    IMPLEMENTATION_STATUS,
    PAVSMCPServer,
    PLACEHOLDER_BANNER,
    _truth_meta,
)


# ---------------------------------------------------------------------------
# Module-level truth boundary constants
# ---------------------------------------------------------------------------


class TestTruthBoundaryConstants:
    """The module-level truth boundary surface must be honest and stable."""

    def test_implementation_status_is_placeholder_stub(self):
        assert IMPLEMENTATION_STATUS == "placeholder_stub"

    def test_placeholder_banner_contains_required_strings(self):
        required_phrases = [
            "PLACEHOLDER_STUB",
            "implementation_status : placeholder_stub",
            "auth_enforcement      : NONE",
            "tool_data             : HARDCODED / FAKE",
            "server_transport      : NONE",
            "DO NOT USE FOR REAL TENANTS",
            "Slice 4",
            "Slice 6",
        ]
        for phrase in required_phrases:
            assert phrase in PLACEHOLDER_BANNER, (
                f"PLACEHOLDER_BANNER missing required phrase: {phrase!r}"
            )

    def test_truth_meta_has_required_fields(self):
        meta = _truth_meta()
        for key in (
            "implementation_status",
            "real_backend",
            "data_source",
            "auth_enforced",
            "canonical_owner",
            "warning",
            "wsp_reference",
            "generated_at",
        ):
            assert key in meta, f"_truth_meta() missing key: {key}"

    def test_truth_meta_values_are_truthful(self):
        meta = _truth_meta()
        assert meta["implementation_status"] == "placeholder_stub"
        assert meta["real_backend"] is False
        assert meta["data_source"] == "hardcoded_placeholder"
        assert meta["auth_enforced"] is False
        assert meta["canonical_owner"] is False
        assert "PLACEHOLDER_STUB" in meta["warning"]
        assert "WSP 96" in meta["wsp_reference"]

    def test_truth_meta_returns_independent_dicts(self):
        """Each call must return a fresh dict so callers can mutate safely."""
        a = _truth_meta()
        b = _truth_meta()
        a["test_mutation"] = True
        assert "test_mutation" not in b


# ---------------------------------------------------------------------------
# handle_tool_call truth-flag injection (the core MCPA4 contract)
# ---------------------------------------------------------------------------


def _run(coro):
    """Helper to run an async coroutine in a sync test."""
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture
def server():
    """Fresh PAVSMCPServer instance per test."""
    return PAVSMCPServer()


class TestHoloSearchTruthFlag:
    """holo_search responses must carry the placeholder_stub truth flag."""

    def test_holo_search_response_carries_truth_meta(self, server):
        result = _run(
            server.handle_tool_call(
                "holo_search",
                {"query": "WSP 97 audit", "limit": 5},
            )
        )

        # Envelope shape
        assert "result" in result, "Successful tool call must carry 'result'"
        assert "meta" in result, "MCPA4: every response must carry 'meta'"

        meta = result["meta"]
        assert meta["implementation_status"] == "placeholder_stub"
        assert meta["real_backend"] is False
        assert meta["canonical_owner"] is False
        assert meta["tool"] == "holo_search"

    def test_holo_search_payload_uses_canonical_envelope(self, server):
        """MCPA1 Slice 4: holo_search MUST return the WSP 96 Annex A.3
        not_implemented envelope, not the legacy `matches[]` shape."""
        result = _run(
            server.handle_tool_call(
                "holo_search",
                {"query": "anything"},
            )
        )
        inner = result["result"]
        # The legacy `matches[]` key must be GONE per Annex A.3.
        assert "matches" not in inner, (
            "Legacy `matches[]` key must not appear in canonical envelope"
        )
        # The canonical envelope keys must be present.
        assert inner["status"] == "not_implemented"
        assert "data" in inner
        assert "error" in inner
        assert "meta" in inner
        # Outer truth flag (from handle_tool_call wrapper) still asserts placeholder.
        assert result["meta"]["data_source"] == "hardcoded_placeholder"


# ---------------------------------------------------------------------------
# Truth flag must be present on ALL tool responses (WSP 96 Annex A.5 C3)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "tool_name,arguments",
    [
        ("cabr_validate", {"content": "x", "context": {}}),
        ("gemma_classify", {"text": "x", "categories": ["a", "b"]}),
        ("qwen_plan", {"objective": "x", "constraints": {}}),
        ("fam_emit", {"foundup_id": "x", "event_type": "test", "payload": {}}),
        ("pattern_recall", {"skill": "x", "min_fidelity": 0.5}),
        ("pattern_store", {"skill": "x", "outcome": {}}),
        ("holo_search", {"query": "x"}),
        ("foundup_register", {"foundup_id": "x", "repo_url": "y", "owner_pubkey": "z"}),
    ],
)
def test_every_tool_response_carries_truth_flag(tool_name, arguments):
    server = PAVSMCPServer()
    result = _run(server.handle_tool_call(tool_name, arguments))

    assert "meta" in result, f"{tool_name}: response missing 'meta' block"
    assert result["meta"]["implementation_status"] == "placeholder_stub", (
        f"{tool_name}: meta.implementation_status must be placeholder_stub"
    )
    assert result["meta"]["real_backend"] is False, (
        f"{tool_name}: meta.real_backend must be False"
    )
    assert result["meta"]["tool"] == tool_name, (
        f"{tool_name}: meta.tool must echo tool name"
    )


# ---------------------------------------------------------------------------
# Unknown / errored calls also carry the truth flag (no silent omission)
# ---------------------------------------------------------------------------


class TestErrorPathHonesty:
    """Even error responses must carry the truth meta block."""

    def test_unknown_tool_response_carries_truth_meta(self, server):
        result = _run(server.handle_tool_call("does_not_exist", {}))

        assert "error" in result
        assert result["error"]["code"] == "UNKNOWN_TOOL"
        # WSP 97: error responses must NOT silently omit the truth boundary.
        assert "meta" in result
        assert result["meta"]["implementation_status"] == "placeholder_stub"

    def test_internal_error_response_carries_truth_meta(self, server):
        """Force a tool to raise so we hit the INTERNAL_ERROR branch."""

        async def boom(**_kwargs):
            raise RuntimeError("simulated failure")

        # Replace one tool with a raising stub. Safe to mutate directly: the
        # `server` fixture builds a fresh PAVSMCPServer per test, so this does
        # not leak across cases.
        server._tools["holo_search"] = boom

        result = _run(server.handle_tool_call("holo_search", {"query": "x"}))

        assert "error" in result
        assert result["error"]["code"] == "INTERNAL_ERROR"
        assert "simulated failure" in result["error"]["message"]
        # Truth meta still present
        assert "meta" in result
        assert result["meta"]["implementation_status"] == "placeholder_stub"


# ---------------------------------------------------------------------------
# Auth-not-enforced honesty: api_key parameter is accepted but ignored
# ---------------------------------------------------------------------------


class TestAuthHonesty:
    """The api_key parameter must be accepted (back-compat) but explicitly
    surfaced as not-enforced via meta.auth_enforced=False."""

    def test_api_key_is_ignored_but_meta_says_so(self, server):
        result_with_key = _run(
            server.handle_tool_call(
                "holo_search",
                {"query": "x"},
                api_key="fp_definitely_not_registered",
            )
        )
        result_without_key = _run(
            server.handle_tool_call("holo_search", {"query": "x"})
        )

        # Both succeed identically — proving auth is NOT enforced
        assert "result" in result_with_key
        assert "result" in result_without_key

        # And both meta blocks declare auth_enforced=False truthfully
        assert result_with_key["meta"]["auth_enforced"] is False
        assert result_without_key["meta"]["auth_enforced"] is False


# ---------------------------------------------------------------------------
# Module attribute presence (defensive: prevents accidental constant removal)
# ---------------------------------------------------------------------------


def test_module_exports_required_truth_constants():
    """If a future refactor removes these, the test suite fails loudly."""
    assert hasattr(pavs_server, "IMPLEMENTATION_STATUS")
    assert hasattr(pavs_server, "PLACEHOLDER_BANNER")
    assert hasattr(pavs_server, "_truth_meta")


# ---------------------------------------------------------------------------
# MCPA1 Slice 4 — Canonical not_implemented envelope (WSP 96 Annex A.3)
# ---------------------------------------------------------------------------


class TestNotImplementedEnvelope:
    """MCPA1 Slice 4: S3 holo_search must return WSP 96 Annex A.3 envelope.

    Closes MCPA6 drift items D20 (fabricated data), D21 (no envelope),
    D22 (fabricated relevance score), D23 (domain vs doc_type_filter),
    D24 (missing federation fields), D25 (no empty-query / canonical shape).
    """

    @pytest.fixture
    def srv(self):
        return PAVSMCPServer()

    # ----- Status field -----

    def test_status_is_not_implemented(self, srv):
        result = _run(srv.holo_search(query="anything"))
        assert result["status"] == "not_implemented"

    def test_no_legacy_matches_key(self, srv):
        result = _run(srv.holo_search(query="x"))
        assert "matches" not in result, (
            "Legacy `matches[]` key must not appear (WSP 96 Annex A.3)"
        )

    # ----- Zero fabrication (the heart of this slice) -----

    def test_no_fabricated_hits(self, srv):
        result = _run(srv.holo_search(query="WSP 97"))
        assert result["data"]["hits"] == [], (
            "Placeholder surface MUST return empty hits[] (no fabrication)"
        )
        assert result["data"]["hit_count"] == 0

    def test_no_fabricated_relevance_or_score(self, srv):
        """Walk the entire response and ensure no relevance/score values exist."""
        result = _run(srv.holo_search(query="x"))
        forbidden_keys = {"relevance", "score", "distance", "similarity"}

        def walk(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    assert k not in forbidden_keys, (
                        f"Found forbidden fabricated key {k!r} = {v!r}"
                    )
                    walk(v)
            elif isinstance(obj, list):
                for item in obj:
                    walk(item)

        walk(result)

    def test_no_fabricated_paths_or_files(self, srv):
        """Ensure the legacy `example.py` / `example_function` mock data is gone."""
        result = _run(srv.holo_search(query="x"))
        result_str = repr(result).lower()
        # Legacy fake values from the pre-Slice-4 placeholder body
        legacy_markers = [
            "example.py",
            "example_function",
            "agent_market/src/example",
        ]
        for marker in legacy_markers:
            assert marker not in result_str, (
                f"Legacy fabricated marker {marker!r} found in response"
            )

    # ----- Error block -----

    def test_error_code_is_not_implemented(self, srv):
        result = _run(srv.holo_search(query="x"))
        assert result["error"]["code"] == "NOT_IMPLEMENTED"

    def test_error_includes_delegate_to(self, srv):
        result = _run(srv.holo_search(query="x"))
        assert result["error"]["delegate_to"] in ("S1", "S2")

    def test_error_message_names_canonical_owners(self, srv):
        result = _run(srv.holo_search(query="x"))
        msg = result["error"]["message"]
        # The error message must point callers to a real canonical owner.
        assert "S2" in msg or "foundups_mcp_bridge" in msg
        assert "S3" in msg  # explicitly say WHICH surface declined

    # ----- Data block: request echo + canonical shape -----

    def test_data_echoes_query(self, srv):
        result = _run(srv.holo_search(query="some query text"))
        assert result["data"]["query"] == "some query text"

    def test_data_echoes_doc_type_filter(self, srv):
        result = _run(srv.holo_search(query="x", doc_type_filter="wsp"))
        assert result["data"]["doc_type_filter"] == "wsp"

    def test_data_echoes_foundup_id(self, srv):
        result = _run(srv.holo_search(query="x", foundup_id="gotjunk"))
        assert result["data"]["foundup_id"] == "gotjunk"

    def test_data_include_shared_only_meaningful_with_foundup_id(self, srv):
        """include_shared echoes the request value only when foundup_id is set,
        otherwise null — so callers cannot infer a scope decision was made."""
        without = _run(srv.holo_search(query="x", include_shared=False))
        assert without["data"]["include_shared"] is None

        with_id = _run(
            srv.holo_search(query="x", foundup_id="kosei", include_shared=False)
        )
        assert with_id["data"]["include_shared"] is False

    def test_data_metadata_warnings_present(self, srv):
        result = _run(srv.holo_search(query="x"))
        warnings = result["data"]["metadata"]["warnings"]
        assert isinstance(warnings, list)
        # Must explicitly state placeholder status
        assert any("placeholder" in w.lower() for w in warnings)

    def test_data_metadata_retrieval_mode_truthful(self, srv):
        """retrieval_mode must be 'none' — never 'semantic' since no backend ran."""
        result = _run(srv.holo_search(query="x"))
        assert result["data"]["metadata"]["retrieval_mode"] == "none"

    # ----- Meta block: surface, tool, truth flags -----

    def test_meta_surface_is_s3(self, srv):
        result = _run(srv.holo_search(query="x"))
        assert result["meta"]["surface"] == "S3"

    def test_meta_tool_is_holo_search(self, srv):
        result = _run(srv.holo_search(query="x"))
        assert result["meta"]["tool"] == "holo_search"

    def test_meta_carries_truth_flag(self, srv):
        result = _run(srv.holo_search(query="x"))
        assert result["meta"]["implementation_status"] == "placeholder_stub"
        assert result["meta"]["real_backend"] is False
        assert result["meta"]["canonical_owner"] is False

    # ----- Canonical request fields acceptance -----

    def test_accepts_all_canonical_request_fields(self, srv):
        """Per Annex A.2: query, limit, doc_type_filter, foundup_id, include_shared."""
        result = _run(
            srv.holo_search(
                query="WSP 97 audit",
                limit=20,
                doc_type_filter="wsp",
                foundup_id="gotjunk",
                include_shared=False,
            )
        )
        assert result["status"] == "not_implemented"
        assert result["data"]["query"] == "WSP 97 audit"
        assert result["data"]["doc_type_filter"] == "wsp"
        assert result["data"]["foundup_id"] == "gotjunk"
        assert result["data"]["include_shared"] is False

    # ----- Limit bound enforcement (Annex A.2) -----

    def test_limit_clamped_above_50(self, srv):
        result = _run(srv.holo_search(query="x", limit=999))
        # Clamped silently to 50 but surfaced truthfully in warnings
        warnings = result["data"]["metadata"]["warnings"]
        assert any("clamp" in w.lower() and "50" in w for w in warnings)

    def test_limit_clamped_below_1(self, srv):
        result = _run(srv.holo_search(query="x", limit=0))
        warnings = result["data"]["metadata"]["warnings"]
        assert any("clamp" in w.lower() for w in warnings)

    def test_invalid_limit_falls_back_to_default(self, srv):
        """Garbage `limit` does not crash; falls back to default 10."""
        result = _run(srv.holo_search(query="x", limit="not_a_number"))
        assert result["status"] == "not_implemented"

    # ----- Back-compat: legacy `domain` alias still works -----

    def test_legacy_domain_alias_accepted(self, srv):
        """Legacy callers passing `domain` instead of `doc_type_filter` still work,
        and a warning is surfaced naming the canonical field."""
        result = _run(srv.holo_search(query="x", domain="code"))
        assert result["data"]["doc_type_filter"] == "code"
        warnings = result["data"]["metadata"]["warnings"]
        assert any("doc_type_filter" in w for w in warnings)

    def test_canonical_doc_type_filter_wins_over_domain(self, srv):
        """If both new and legacy params are passed, canonical wins."""
        result = _run(
            srv.holo_search(query="x", doc_type_filter="wsp", domain="code")
        )
        assert result["data"]["doc_type_filter"] == "wsp"

    # ----- handle_tool_call wrapping still emits canonical envelope -----

    def test_via_handle_tool_call_inner_envelope_canonical(self, srv):
        """Through the dispatch path, the canonical envelope is intact under .result."""
        wrapped = _run(
            srv.handle_tool_call(
                "holo_search",
                {"query": "x", "foundup_id": "kosei"},
            )
        )
        inner = wrapped["result"]
        assert inner["status"] == "not_implemented"
        assert inner["data"]["foundup_id"] == "kosei"
        assert inner["meta"]["surface"] == "S3"
        # Outer wrapper still adds its own truth meta (MCPA4 contract)
        assert wrapped["meta"]["implementation_status"] == "placeholder_stub"
