"""
Shell Bridge Interceptor Tests

Tests for public/member/js/shell-bridge-interceptor.js
Validates postMessage handling per EXTERNAL_FOUNDUP_BRIDGE_CONTRACT.md

Contract: holo_index/docs/EXTERNAL_FOUNDUP_BRIDGE_CONTRACT.md
WSP References: WSP 11 (Interface Contract), WSP 97 (Execution Discipline)
"""
import json
import os
import re
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JS_PATH = os.path.join(ROOT, "js", "shell-bridge-interceptor.js")


def _read_js():
    """Read the interceptor JS file."""
    with open(JS_PATH, encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# File Existence Tests
# ---------------------------------------------------------------------------


class TestInterceptorExists:
    """Test that the interceptor file exists and is properly structured."""

    def test_interceptor_file_exists(self):
        """shell-bridge-interceptor.js exists."""
        assert os.path.isfile(JS_PATH), "js/shell-bridge-interceptor.js must exist"

    def test_interceptor_is_iife(self):
        """Interceptor is wrapped in IIFE for encapsulation."""
        js = _read_js()
        assert "(function()" in js or "(function ()" in js
        assert "'use strict'" in js or '"use strict"' in js

    def test_interceptor_has_init(self):
        """Interceptor has init function."""
        js = _read_js()
        assert "function init()" in js

    def test_interceptor_adds_message_listener(self):
        """Interceptor adds message event listener."""
        js = _read_js()
        assert "addEventListener" in js
        assert "'message'" in js or '"message"' in js


# ---------------------------------------------------------------------------
# Message Type Validation Tests
# ---------------------------------------------------------------------------


class TestMessageTypeHandling:
    """Test that message types are correctly validated."""

    def test_checks_agent_request_type(self):
        """Interceptor checks for type === 'agent_request'."""
        js = _read_js()
        assert "agent_request" in js
        # Should check data.type
        assert "data.type" in js or 'type !== "agent_request"' in js or "type !== 'agent_request'" in js

    def test_ignores_non_object_messages(self):
        """Interceptor ignores non-object messages."""
        js = _read_js()
        assert "typeof data" in js or "!data" in js

    def test_has_handle_message_function(self):
        """Interceptor has handleMessage function."""
        js = _read_js()
        assert "handleMessage" in js or "function handleMessage" in js


# ---------------------------------------------------------------------------
# Route Handler Tests
# ---------------------------------------------------------------------------


class TestRouteHandling:
    """Test route handling per bridge contract."""

    def test_has_openclaw_search_route(self):
        """Interceptor handles 'openclaw_search' route."""
        js = _read_js()
        assert "openclaw_search" in js

    def test_handlers_object_exists(self):
        """Interceptor has handlers object/map."""
        js = _read_js()
        assert "handlers" in js or "var handlers" in js

    def test_dispatch_request_function_exists(self):
        """Interceptor has dispatchRequest function."""
        js = _read_js()
        assert "dispatchRequest" in js

    def test_unknown_route_returns_error(self):
        """Interceptor returns error for unknown routes."""
        js = _read_js()
        assert "unknown_route" in js


# ---------------------------------------------------------------------------
# Action Handler Tests (per Section 2.1, 2.2 of contract)
# ---------------------------------------------------------------------------


class TestActionHandlers:
    """Test action handlers match contract Section 2.1 and 2.2."""

    def test_semantic_search_action_handled(self):
        """Interceptor handles 'semantic_search' action."""
        js = _read_js()
        assert "semantic_search" in js

    def test_wsp_lookup_action_handled(self):
        """Interceptor handles 'wsp_lookup' action."""
        js = _read_js()
        assert "wsp_lookup" in js

    def test_unknown_action_returns_error(self):
        """Interceptor returns error for unknown actions."""
        js = _read_js()
        assert "unknown_action" in js

    def test_semantic_search_extracts_query(self):
        """Semantic search handler extracts query parameter."""
        js = _read_js()
        assert "payload.query" in js or 'query"' in js

    def test_semantic_search_extracts_limit(self):
        """Semantic search handler extracts limit parameter."""
        js = _read_js()
        assert "payload.limit" in js or "limit" in js

    def test_wsp_lookup_extracts_protocol_number(self):
        """WSP lookup handler extracts protocol_number parameter."""
        js = _read_js()
        assert "protocol_number" in js


# ---------------------------------------------------------------------------
# Response Format Tests (per Section 3.1 of contract)
# ---------------------------------------------------------------------------


class TestResponseFormat:
    """Test response format matches contract Section 3.1."""

    def test_response_has_agent_response_type(self):
        """Responses use type: 'agent_response'."""
        js = _read_js()
        assert "agent_response" in js

    def test_response_has_status_field(self):
        """Responses include status field."""
        js = _read_js()
        # Check for status: 'success' or status: 'error'
        assert "status:" in js or '"status"' in js
        assert "'success'" in js or '"success"' in js
        assert "'error'" in js or '"error"' in js

    def test_response_has_data_field(self):
        """Responses include data field."""
        js = _read_js()
        assert "data:" in js or '"data"' in js

    def test_semantic_search_response_has_results(self):
        """Semantic search response includes results array."""
        js = _read_js()
        assert "results" in js

    def test_semantic_search_response_has_quantum_coherence(self):
        """Semantic search response includes quantum_coherence."""
        js = _read_js()
        assert "quantum_coherence" in js

    def test_response_has_service_field(self):
        """Responses include service identifier for FoundUp iframe filtering."""
        js = _read_js()
        assert "ROUTE_SERVICE_MAP" in js
        assert "'holoindex'" in js or '"holoindex"' in js

    def test_service_injected_in_dispatch(self):
        """dispatchRequest injects service from ROUTE_SERVICE_MAP."""
        js = _read_js()
        assert "response.service" in js


# ---------------------------------------------------------------------------
# Origin Validation Tests
# ---------------------------------------------------------------------------


class TestOriginValidation:
    """Test origin validation for security."""

    def test_validates_origin(self):
        """Interceptor validates message origin."""
        js = _read_js()
        assert "origin" in js
        assert "isAllowedOrigin" in js or "allowedOrigins" in js

    def test_has_allowed_origins_list(self):
        """Interceptor has configurable allowed origins."""
        js = _read_js()
        assert "allowedOrigins" in js

    def test_allows_same_origin(self):
        """Interceptor allows same-origin messages."""
        js = _read_js()
        assert "window.location.origin" in js

    def test_rejects_disallowed_origin(self):
        """Interceptor logs/ignores disallowed origins."""
        js = _read_js()
        # Should have logic to skip disallowed origins
        assert "disallowed" in js.lower() or "!isAllowedOrigin" in js


# ---------------------------------------------------------------------------
# Stub Mode Tests
# ---------------------------------------------------------------------------


class TestStubMode:
    """Test stub/simulation mode for Phase 1."""

    def test_has_stub_indicator(self):
        """Stub responses are marked as such."""
        js = _read_js()
        assert "stub" in js.lower()

    def test_stub_responses_delayed(self):
        """Stub responses use setTimeout for realism."""
        js = _read_js()
        assert "setTimeout" in js

    def test_backend_hookpoint_exists(self):
        """Backend integration hookpoint exists."""
        js = _read_js()
        assert "shellBridgeBackend" in js

    def test_backend_search_hookpoint(self):
        """Backend search hookpoint defined."""
        js = _read_js()
        assert "shellBridgeBackend.search" in js or "shellBridgeBackend" in js


# ---------------------------------------------------------------------------
# Public API Tests
# ---------------------------------------------------------------------------


class TestPublicAPI:
    """Test public API exposed on window."""

    def test_exposes_window_api(self):
        """Interceptor exposes window.shellBridgeInterceptor."""
        js = _read_js()
        assert "window.shellBridgeInterceptor" in js

    def test_add_allowed_origin_method(self):
        """API has addAllowedOrigin method."""
        js = _read_js()
        assert "addAllowedOrigin" in js

    def test_set_backend_method(self):
        """API has setBackend method."""
        js = _read_js()
        assert "setBackend" in js

    def test_register_shell_bridge_backend_method(self):
        """Explicit registration API (truthful seam)."""
        js = _read_js()
        assert "registerShellBridgeBackend" in js

    def test_clear_shell_bridge_backend_method(self):
        """Clear returns to stub mode."""
        js = _read_js()
        assert "clearShellBridgeBackend" in js

    def test_get_shell_bridge_backend_status_method(self):
        """Status introspection for stub vs registered (no false live claims)."""
        js = _read_js()
        assert "getShellBridgeBackendStatus" in js

    def test_backend_registration_state_tracked(self):
        """Registration mode is tracked separately from window reference."""
        js = _read_js()
        assert "backendRegistration" in js

    def test_get_config_method(self):
        """API has getConfig method."""
        js = _read_js()
        assert "getConfig" in js


# ---------------------------------------------------------------------------
# VM runtime (node) — registration + stub vs real paths
# ---------------------------------------------------------------------------


class TestVMRuntimeShellBridge:
    """Node vm exercises registration + stub paths (focused runtime proof)."""

    @pytest.mark.skipif(not shutil.which("node"), reason="node not on PATH")
    def test_shell_bridge_interceptor_vm_script_passes(self):
        mjs = os.path.join(os.path.dirname(__file__), "shell_bridge_interceptor_vm.mjs")
        proc = subprocess.run(
            ["node", mjs],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr


# ---------------------------------------------------------------------------
# HTML Integration Tests
# ---------------------------------------------------------------------------


class TestHTMLIntegration:
    """Test that interceptor is included in shell HTML files."""

    def test_included_in_index_html(self):
        """Interceptor is included in index.html."""
        index_path = os.path.join(ROOT, "index.html")
        with open(index_path, encoding="utf-8") as f:
            html = f.read()
        assert "shell-bridge-interceptor.js" in html

    def test_included_in_foundup_html(self):
        """Interceptor is included in foundup.html."""
        foundup_path = os.path.join(ROOT, "foundup.html")
        with open(foundup_path, encoding="utf-8") as f:
            html = f.read()
        assert "shell-bridge-interceptor.js" in html

    def test_loaded_before_concierge(self):
        """Interceptor loaded before concierge scripts."""
        index_path = os.path.join(ROOT, "index.html")
        with open(index_path, encoding="utf-8") as f:
            html = f.read()

        interceptor_pos = html.find("shell-bridge-interceptor.js")
        concierge_pos = html.find("red-dog-concierge.js")

        assert interceptor_pos > 0, "Interceptor must be in HTML"
        assert concierge_pos > 0, "Concierge must be in HTML"
        assert interceptor_pos < concierge_pos, "Interceptor must load before concierge"
