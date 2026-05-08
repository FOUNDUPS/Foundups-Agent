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

    def test_holo_search_payload_remains_visible(self, server):
        """The fake payload still returns (so callers can inspect shape) but
        the truth flag in meta makes it unmistakably fake."""
        result = _run(
            server.handle_tool_call(
                "holo_search",
                {"query": "anything"},
            )
        )
        # The placeholder body returns a 'matches' list — confirm shape unchanged
        # since MCPA4 is non-architectural.
        assert "matches" in result["result"]
        # And the truth flag is present so the matches[] cannot be mistaken
        # for real data.
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
