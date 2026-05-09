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
import json
import tempfile
from pathlib import Path

import pytest

from modules.infrastructure.pavs_mcp.src import server as pavs_server
from modules.infrastructure.pavs_mcp.src.server import (
    FoundUpRegistration,
    IMPLEMENTATION_STATUS,
    PAVSMCPServer,
    PLACEHOLDER_BANNER,
    RegistryStore,
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
            "REAL_TRANSPORT",  # MCPA8: transport is real
            "PLACEHOLDER_BACKENDS",  # MCPA8: backends still placeholder
            "implementation_status : placeholder_stub",
            "auth_enforcement      : BASIC",  # MCPA1 Slice 6: now enforced
            "scope_enforcement     : YES",    # MCPA1 Slice 6: cross-tenant rejected
            "tool_data             : HARDCODED / FAKE",
            "server_transport      : HTTP_JSON",  # MCPA8: real transport
            "registry_persistence  : LOCAL_JSON",  # MCPA1 Slice 7: persisted
            "DO NOT USE FOR PRODUCTION TRAFFIC",
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


def _register_and_get_key(server, foundup_id="test_foundup"):
    """Helper to register a FoundUp and return the api_key."""
    result = _run(server.handle_tool_call(
        "foundup_register",
        {
            "foundup_id": foundup_id,
            "repo_url": f"https://github.com/test/{foundup_id}",
            "owner_pubkey": "ed25519_test_pubkey",
        },
    ))
    return result["result"]["api_key"]


@pytest.fixture
def server():
    """Fresh PAVSMCPServer instance per test."""
    return PAVSMCPServer()


@pytest.fixture
def authed_server():
    """PAVSMCPServer with a registered FoundUp, returns (server, api_key)."""
    srv = PAVSMCPServer()
    api_key = _register_and_get_key(srv, "test_foundup")
    return srv, api_key


class TestHoloSearchTruthFlag:
    """holo_search responses must carry the placeholder_stub truth flag."""

    def test_holo_search_response_carries_truth_meta(self, authed_server):
        server, api_key = authed_server
        result = _run(
            server.handle_tool_call(
                "holo_search",
                {"query": "WSP 97 audit", "limit": 5},
                api_key=api_key,
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

    def test_holo_search_payload_uses_canonical_envelope(self, authed_server):
        """MCPA1 Slice 4: holo_search MUST return the WSP 96 Annex A.3
        not_implemented envelope, not the legacy `matches[]` shape."""
        server, api_key = authed_server
        result = _run(
            server.handle_tool_call(
                "holo_search",
                {"query": "anything"},
                api_key=api_key,
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
    "tool_name,arguments,is_bootstrap",
    [
        ("cabr_validate", {"content": "x", "context": {}}, False),
        ("gemma_classify", {"text": "x", "categories": ["a", "b"]}, False),
        ("qwen_plan", {"objective": "x", "constraints": {}}, False),
        ("fam_emit", {"foundup_id": "test_foundup", "event_type": "test", "payload": {}}, False),
        ("pattern_recall", {"skill": "x", "min_fidelity": 0.5}, False),
        ("pattern_store", {"skill": "x", "outcome": {}}, False),
        ("holo_search", {"query": "x"}, False),
        ("foundup_register", {"foundup_id": "new_x", "repo_url": "y", "owner_pubkey": "z"}, True),
    ],
)
def test_every_tool_response_carries_truth_flag(tool_name, arguments, is_bootstrap):
    server = PAVSMCPServer()
    # MCPA1 Slice 6: Protected tools need auth; bootstrap tools do not
    api_key = None
    if not is_bootstrap:
        api_key = _register_and_get_key(server, "test_foundup")
    result = _run(server.handle_tool_call(tool_name, arguments, api_key=api_key))

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

    def test_internal_error_response_carries_truth_meta(self, authed_server):
        """Force a tool to raise so we hit the INTERNAL_ERROR branch."""
        server, api_key = authed_server

        async def boom(**_kwargs):
            raise RuntimeError("simulated failure")

        # Replace one tool with a raising stub. Safe to mutate directly: the
        # fixture builds a fresh PAVSMCPServer per test, so this does
        # not leak across cases.
        server._tools["holo_search"] = boom

        result = _run(server.handle_tool_call("holo_search", {"query": "x"}, api_key=api_key))

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
    """MCPA1 Slice 6: Auth is now enforced. Tests verify enforcement behavior."""

    def test_unregistered_api_key_rejected(self, server):
        """Unregistered api_key is rejected with UNKNOWN_API_KEY."""
        result = _run(
            server.handle_tool_call(
                "holo_search",
                {"query": "x"},
                api_key="fp_definitely_not_registered",
            )
        )

        # Auth is enforced — unregistered key rejected
        assert "error" in result
        assert result["error"]["code"] == "UNKNOWN_API_KEY"
        assert result["meta"]["auth_enforced"] is True

    def test_registered_api_key_accepted(self, authed_server):
        """Registered api_key allows the call."""
        server, api_key = authed_server
        result = _run(
            server.handle_tool_call(
                "holo_search",
                {"query": "x"},
                api_key=api_key,
            )
        )

        # Auth enforced and passed
        assert "result" in result
        assert result["meta"]["auth_enforced"] is True

    def test_missing_api_key_rejected(self, server):
        """Missing api_key rejected with MISSING_API_KEY."""
        result = _run(
            server.handle_tool_call("holo_search", {"query": "x"})
        )

        assert "error" in result
        assert result["error"]["code"] == "MISSING_API_KEY"
        assert result["meta"]["auth_enforced"] is True


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
        # MCPA1 Slice 6: Need to register with matching foundup_id
        api_key = _register_and_get_key(srv, "kosei")
        wrapped = _run(
            srv.handle_tool_call(
                "holo_search",
                {"query": "x", "foundup_id": "kosei"},
                api_key=api_key,
            )
        )
        inner = wrapped["result"]
        assert inner["status"] == "not_implemented"
        assert inner["data"]["foundup_id"] == "kosei"
        assert inner["meta"]["surface"] == "S3"
        # Outer wrapper still adds its own truth meta (MCPA4 contract)
        assert wrapped["meta"]["implementation_status"] == "placeholder_stub"


# ---------------------------------------------------------------------------
# MCPA1 Slice 6 — Federation Auth/Scope Enforcement
# ---------------------------------------------------------------------------


class TestFederationAuth:
    """MCPA1 Slice 6: API key validation and scope enforcement tests."""

    @pytest.fixture
    def srv(self):
        return PAVSMCPServer()

    def _register_foundup(self, srv, foundup_id="test_foundup"):
        """Helper to register a FoundUp and return the api_key."""
        result = _run(srv.handle_tool_call(
            "foundup_register",
            {
                "foundup_id": foundup_id,
                "repo_url": f"https://github.com/test/{foundup_id}",
                "owner_pubkey": "ed25519_test_pubkey_placeholder",
            },
        ))
        assert "result" in result
        return result["result"]["api_key"]

    # ----- Bootstrap tool (foundup_register) remains unauthenticated -----

    def test_foundup_register_accepts_no_api_key(self, srv):
        """foundup_register is a bootstrap tool — no auth required."""
        result = _run(srv.handle_tool_call(
            "foundup_register",
            {
                "foundup_id": "new_foundup",
                "repo_url": "https://github.com/test/new",
                "owner_pubkey": "pubkey123",
            },
            api_key=None,
        ))
        assert "result" in result
        assert "api_key" in result["result"]
        # meta.auth_enforced should be False for bootstrap tools
        assert result["meta"]["auth_enforced"] is False

    # ----- Protected tools reject missing API key -----

    def test_protected_tool_rejects_missing_api_key(self, srv):
        """Protected tools require api_key."""
        result = _run(srv.handle_tool_call(
            "holo_search",
            {"query": "test"},
            api_key=None,
        ))
        assert "error" in result
        assert result["error"]["code"] == "MISSING_API_KEY"
        assert result["meta"]["auth_enforced"] is True

    def test_cabr_validate_rejects_missing_api_key(self, srv):
        """cabr_validate is protected."""
        result = _run(srv.handle_tool_call(
            "cabr_validate",
            {"content": "test"},
            api_key=None,
        ))
        assert "error" in result
        assert result["error"]["code"] == "MISSING_API_KEY"

    # ----- Protected tools reject unknown API key -----

    def test_protected_tool_rejects_unknown_api_key(self, srv):
        """Unknown api_key is rejected."""
        result = _run(srv.handle_tool_call(
            "holo_search",
            {"query": "test"},
            api_key="fp_definitely_not_registered_key",
        ))
        assert "error" in result
        assert result["error"]["code"] == "UNKNOWN_API_KEY"
        assert result["meta"]["auth_enforced"] is True

    # ----- Registered API key is accepted -----

    def test_registered_api_key_accepted(self, srv):
        """Valid registered api_key allows tool call."""
        api_key = self._register_foundup(srv, "my_foundup")

        result = _run(srv.handle_tool_call(
            "holo_search",
            {"query": "test"},
            api_key=api_key,
        ))
        assert "result" in result
        assert result["meta"]["auth_enforced"] is True
        assert result["meta"]["registered_foundup_id"] == "my_foundup"

    # ----- Cross-tenant foundup_id rejected -----

    def test_cross_tenant_foundup_id_rejected(self, srv):
        """Requesting a different foundup_id than registered is rejected."""
        api_key = self._register_foundup(srv, "foundup_a")

        result = _run(srv.handle_tool_call(
            "holo_search",
            {"query": "test", "foundup_id": "foundup_b"},
            api_key=api_key,
        ))
        assert "error" in result
        assert result["error"]["code"] == "CROSS_TENANT_VIOLATION"
        assert result["error"]["registered_foundup_id"] == "foundup_a"
        assert result["error"]["requested_foundup_id"] == "foundup_b"
        assert result["meta"]["auth_enforced"] is True

    def test_fam_emit_cross_tenant_rejected(self, srv):
        """fam_emit with wrong foundup_id is rejected."""
        api_key = self._register_foundup(srv, "foundup_x")

        result = _run(srv.handle_tool_call(
            "fam_emit",
            {
                "foundup_id": "foundup_y",
                "event_type": "test",
                "payload": {},
            },
            api_key=api_key,
        ))
        assert "error" in result
        assert result["error"]["code"] == "CROSS_TENANT_VIOLATION"

    # ----- Matching foundup_id is accepted -----

    def test_matching_foundup_id_accepted(self, srv):
        """Own foundup_id in request is accepted."""
        api_key = self._register_foundup(srv, "my_foundup")

        result = _run(srv.handle_tool_call(
            "holo_search",
            {"query": "test", "foundup_id": "my_foundup"},
            api_key=api_key,
        ))
        assert "result" in result
        assert result["meta"]["registered_foundup_id"] == "my_foundup"

    def test_fam_emit_matching_foundup_id_accepted(self, srv):
        """fam_emit with matching foundup_id succeeds."""
        api_key = self._register_foundup(srv, "my_foundup")

        result = _run(srv.handle_tool_call(
            "fam_emit",
            {
                "foundup_id": "my_foundup",
                "event_type": "test",
                "payload": {"key": "value"},
            },
            api_key=api_key,
        ))
        assert "result" in result
        assert "event_id" in result["result"]

    # ----- No foundup_id argument is OK (uses caller identity) -----

    def test_no_foundup_id_argument_ok(self, srv):
        """Tools without foundup_id argument still work."""
        api_key = self._register_foundup(srv, "my_foundup")

        result = _run(srv.handle_tool_call(
            "gemma_classify",
            {"text": "test text", "categories": ["a", "b"]},
            api_key=api_key,
        ))
        assert "result" in result
        assert result["meta"]["auth_enforced"] is True

    # ----- Meta flags are truthful -----

    def test_meta_auth_enforced_true_for_protected_tools(self, srv):
        """Protected tools set auth_enforced=True."""
        api_key = self._register_foundup(srv, "test")

        result = _run(srv.handle_tool_call(
            "pattern_recall",
            {"skill": "test_skill"},
            api_key=api_key,
        ))
        assert result["meta"]["auth_enforced"] is True

    def test_meta_auth_enforced_false_for_bootstrap_tools(self, srv):
        """Bootstrap tools set auth_enforced=False."""
        result = _run(srv.handle_tool_call(
            "foundup_register",
            {
                "foundup_id": "new",
                "repo_url": "https://test",
                "owner_pubkey": "key",
            },
        ))
        assert result["meta"]["auth_enforced"] is False

    def test_meta_registered_foundup_id_present_on_success(self, srv):
        """Successful auth includes registered_foundup_id in meta."""
        api_key = self._register_foundup(srv, "tracked_foundup")

        result = _run(srv.handle_tool_call(
            "qwen_plan",
            {"objective": "test"},
            api_key=api_key,
        ))
        assert result["meta"]["registered_foundup_id"] == "tracked_foundup"

    # ----- Registration creates proper bindings -----

    def test_registration_creates_api_key_binding(self, srv):
        """foundup_register creates api_key -> foundup_id mapping."""
        result = _run(srv.handle_tool_call(
            "foundup_register",
            {
                "foundup_id": "bound_foundup",
                "repo_url": "https://test",
                "owner_pubkey": "key",
            },
        ))
        api_key = result["result"]["api_key"]

        # Verify internal state
        assert srv._api_key_to_foundup[api_key] == "bound_foundup"
        assert "bound_foundup" in srv.registrations
        assert srv.registrations["bound_foundup"].api_key == api_key

    def test_registration_stores_owner_pubkey(self, srv):
        """Registration stores owner_pubkey for future verification."""
        result = _run(srv.handle_tool_call(
            "foundup_register",
            {
                "foundup_id": "keyed_foundup",
                "repo_url": "https://test",
                "owner_pubkey": "ed25519_test_key_abc123",
            },
        ))

        assert srv.registrations["keyed_foundup"].owner_pubkey == "ed25519_test_key_abc123"

    # ----- All protected tools enforce auth -----

    @pytest.mark.parametrize("tool_name,arguments", [
        ("cabr_validate", {"content": "x"}),
        ("gemma_classify", {"text": "x", "categories": ["a"]}),
        ("qwen_plan", {"objective": "x"}),
        ("fam_emit", {"foundup_id": "x", "event_type": "t", "payload": {}}),
        ("pattern_recall", {"skill": "x"}),
        ("pattern_store", {"skill": "x", "outcome": {}}),
        ("holo_search", {"query": "x"}),
    ])
    def test_all_protected_tools_reject_missing_api_key(self, tool_name, arguments):
        """Every non-bootstrap tool rejects calls without api_key."""
        srv = PAVSMCPServer()
        result = _run(srv.handle_tool_call(tool_name, arguments, api_key=None))

        assert "error" in result, f"{tool_name} should reject missing api_key"
        assert result["error"]["code"] == "MISSING_API_KEY"


# ---------------------------------------------------------------------------
# MCPA7: Registry Persistence Tests
# ---------------------------------------------------------------------------


class TestRegistryPersistence:
    """Tests for durable JSON-based registry persistence (MCPA7)."""

    def test_registration_persists_to_file(self, tmp_path):
        """Registrations are written to disk on register."""
        registry_path = tmp_path / "registrations.json"
        srv = PAVSMCPServer(registry_path=registry_path)

        _run(srv.handle_tool_call(
            "foundup_register",
            {
                "foundup_id": "persisted_foundup",
                "repo_url": "https://github.com/test/repo",
                "owner_pubkey": "ed25519_test_key",
            },
        ))

        assert registry_path.exists()
        data = json.loads(registry_path.read_text())
        assert "registrations" in data
        assert "persisted_foundup" in data["registrations"]
        assert data["registrations"]["persisted_foundup"]["repo_url"] == "https://github.com/test/repo"

    def test_registration_survives_restart(self, tmp_path):
        """Registrations survive server restart (new server instance)."""
        registry_path = tmp_path / "registrations.json"

        # First server instance: register a FoundUp
        srv1 = PAVSMCPServer(registry_path=registry_path)
        result1 = _run(srv1.handle_tool_call(
            "foundup_register",
            {
                "foundup_id": "survivor_foundup",
                "repo_url": "https://github.com/test/survivor",
                "owner_pubkey": "key123",
            },
        ))
        api_key = result1["result"]["api_key"]

        # Second server instance: should load the registration
        srv2 = PAVSMCPServer(registry_path=registry_path)
        assert "survivor_foundup" in srv2.registrations
        assert srv2._api_key_to_foundup[api_key] == "survivor_foundup"

        # Tool call should work with the persisted API key
        result2 = _run(srv2.handle_tool_call(
            "holo_search",
            {"query": "test"},
            api_key=api_key,
        ))
        assert "result" in result2
        assert result2["meta"]["registered_foundup_id"] == "survivor_foundup"

    def test_corrupt_registry_starts_empty(self, tmp_path):
        """Corrupt registry file is handled gracefully (start empty)."""
        registry_path = tmp_path / "registrations.json"
        registry_path.write_text("not valid json {{{")

        srv = PAVSMCPServer(registry_path=registry_path)

        assert len(srv.registrations) == 0
        assert srv._registry_store.load_error is not None
        assert "JSON decode error" in srv._registry_store.load_error

    def test_missing_registry_starts_empty(self, tmp_path):
        """Missing registry file starts empty (no error)."""
        registry_path = tmp_path / "nonexistent" / "registrations.json"

        srv = PAVSMCPServer(registry_path=registry_path)

        assert len(srv.registrations) == 0
        assert srv._registry_store.load_error is None

    def test_env_var_override(self, tmp_path, monkeypatch):
        """PAVS_REGISTRY_PATH env var overrides default path."""
        custom_path = tmp_path / "custom_registry.json"
        monkeypatch.setenv("PAVS_REGISTRY_PATH", str(custom_path))

        # Create server without explicit path (should use env var)
        store = RegistryStore()
        store.register(FoundUpRegistration(
            foundup_id="env_foundup",
            repo_url="https://test",
            api_key="fp_test_key",
            owner_pubkey="key",
        ))

        assert custom_path.exists()
        data = json.loads(custom_path.read_text())
        assert "env_foundup" in data["registrations"]

    def test_reregistration_replaces_existing(self, tmp_path):
        """Re-registering same foundup_id replaces the old registration."""
        registry_path = tmp_path / "registrations.json"
        srv = PAVSMCPServer(registry_path=registry_path)

        # First registration
        result1 = _run(srv.handle_tool_call(
            "foundup_register",
            {
                "foundup_id": "reregister_test",
                "repo_url": "https://github.com/test/v1",
                "owner_pubkey": "key1",
            },
        ))
        api_key_1 = result1["result"]["api_key"]

        # Second registration (same foundup_id)
        result2 = _run(srv.handle_tool_call(
            "foundup_register",
            {
                "foundup_id": "reregister_test",
                "repo_url": "https://github.com/test/v2",
                "owner_pubkey": "key2",
            },
        ))
        api_key_2 = result2["result"]["api_key"]

        # Old API key should no longer work
        assert api_key_1 not in srv._api_key_to_foundup

        # New API key should work
        assert srv._api_key_to_foundup[api_key_2] == "reregister_test"
        assert srv.registrations["reregister_test"].repo_url == "https://github.com/test/v2"

    def test_atomic_write_creates_parent_dirs(self, tmp_path):
        """Registry store creates parent directories if they don't exist."""
        registry_path = tmp_path / "nested" / "deep" / "registrations.json"
        srv = PAVSMCPServer(registry_path=registry_path)

        _run(srv.handle_tool_call(
            "foundup_register",
            {
                "foundup_id": "nested_foundup",
                "repo_url": "https://test",
                "owner_pubkey": "key",
            },
        ))

        assert registry_path.exists()
        assert registry_path.parent.exists()
