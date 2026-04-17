"""
HoloIndex External FoundUp Bridge Contract Verification Tests

Verifies bridge_stub.py, foundup_manifest.json, mall-catalog.json,
connector.js, and shell-bridge-interceptor.js against
EXTERNAL_FOUNDUP_BRIDGE_CONTRACT.md.

Worker: CY
Slice: HOLOINDEX_EXTERNAL_BRIDGE_CONTRACT_VERIFICATION_PHASE1
WSP References: WSP 11 (Interface), WSP 97 (Execution Discipline)
"""
import json
import os
import sys

import pytest

# Paths
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
ADAPTER_DIR = os.path.join(REPO_ROOT, "holo_index", "foundup_adapter")
MANIFEST_PATH = os.path.join(REPO_ROOT, "holo_index", "foundup_manifest.json")
CATALOG_PATH = os.path.join(REPO_ROOT, "public", "member", "mall-catalog.json")
UI_DIR = os.path.join(REPO_ROOT, "public", "f", "holoindex_prod_01")
CONNECTOR_PATH = os.path.join(UI_DIR, "js", "connector.js")
CONTRACT_PATH = os.path.join(
    REPO_ROOT, "holo_index", "docs", "EXTERNAL_FOUNDUP_BRIDGE_CONTRACT.md"
)
INTERCEPTOR_PATH = os.path.join(
    REPO_ROOT, "public", "member", "js", "shell-bridge-interceptor.js"
)

sys.path.insert(0, ADAPTER_DIR)
sys.path.insert(0, os.path.join(ADAPTER_DIR))
# bridge_stub.py lives in holo_index/foundup_adapter/
_stub_path = os.path.join(ADAPTER_DIR, "bridge_stub.py")
import importlib.util
_spec = importlib.util.spec_from_file_location("bridge_stub", _stub_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
BridgeStub = _mod.BridgeStub


# ---------------------------------------------------------------------------
# BridgeStub sendMessage Tests
# ---------------------------------------------------------------------------


class TestBridgeStubSemanticSearch:
    """BridgeStub.sendMessage() with semantic_search action."""

    def test_semantic_search_returns_results(self):
        stub = BridgeStub()
        resp = json.loads(
            stub.sendMessage(
                json.dumps(
                    {
                        "route": "openclaw_search",
                        "payload": {
                            "action": "semantic_search",
                            "query": "WSP 97",
                            "limit": 3,
                        },
                    }
                )
            )
        )
        assert "results" in resp
        assert isinstance(resp["results"], list)
        assert len(resp["results"]) > 0

    def test_semantic_search_has_quantum_coherence(self):
        stub = BridgeStub()
        resp = json.loads(
            stub.sendMessage(
                json.dumps(
                    {
                        "route": "openclaw_search",
                        "payload": {"action": "semantic_search", "query": "test"},
                    }
                )
            )
        )
        assert "quantum_coherence" in resp
        assert isinstance(resp["quantum_coherence"], (int, float))

    def test_semantic_search_has_truthful_stub_marker(self):
        """stub field MUST be True when response is simulated."""
        stub = BridgeStub()
        resp = json.loads(
            stub.sendMessage(
                json.dumps(
                    {
                        "route": "openclaw_search",
                        "payload": {"action": "semantic_search", "query": "test"},
                    }
                )
            )
        )
        assert resp.get("stub") is True, (
            "BridgeStub must return stub: true (not false) — simulated responses "
            "must not overclaim backend connectivity"
        )

    def test_semantic_search_result_has_content_path_relevance(self):
        stub = BridgeStub()
        resp = json.loads(
            stub.sendMessage(
                json.dumps(
                    {
                        "route": "openclaw_search",
                        "payload": {"action": "semantic_search", "query": "test"},
                    }
                )
            )
        )
        result = resp["results"][0]
        assert "content" in result
        assert "path" in result
        assert "relevance" in result


class TestBridgeStubUnknownRoute:
    """Unknown route/action returns error envelope."""

    def test_unknown_route_returns_error(self):
        stub = BridgeStub()
        resp = json.loads(
            stub.sendMessage(
                json.dumps(
                    {
                        "route": "nonexistent_route",
                        "payload": {"action": "foo"},
                    }
                )
            )
        )
        assert "error" in resp

    def test_unknown_action_returns_error(self):
        stub = BridgeStub()
        resp = json.loads(
            stub.sendMessage(
                json.dumps(
                    {
                        "route": "openclaw_search",
                        "payload": {"action": "nonexistent_action"},
                    }
                )
            )
        )
        assert "error" in resp


# ---------------------------------------------------------------------------
# Manifest Tests
# ---------------------------------------------------------------------------


class TestManifestTruth:
    """foundup_manifest.json points to tracked UI scaffold."""

    def test_manifest_valid_json(self):
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            manifest = json.load(f)
        assert isinstance(manifest, dict)

    def test_manifest_has_foundup_id(self):
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            manifest = json.load(f)
        assert manifest["foundup_id"] == "holoindex_prod_01"

    def test_manifest_entry_point_exists(self):
        """Manifest entry_point points to a file that exists in the repo."""
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            manifest = json.load(f)
        entry = manifest.get("entry_point", "")
        entry_path = os.path.join(REPO_ROOT, entry)
        assert os.path.isfile(entry_path), (
            f"Manifest entry_point '{entry}' does not exist at {entry_path}"
        )

    def test_manifest_routing_prefix_matches_catalog(self):
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            manifest = json.load(f)
        with open(CATALOG_PATH, encoding="utf-8") as f:
            catalog = json.load(f)
        holo_entry = next(
            (e for e in catalog if e["foundup_id"] == "holoindex_prod_01"), None
        )
        assert holo_entry is not None, "holoindex_prod_01 must be in mall-catalog.json"
        assert manifest["routing_prefix"] == holo_entry["routing_prefix"]

    def test_manifest_capabilities_match_contract(self):
        """Manifest capabilities match contract Section 2 actions."""
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            manifest = json.load(f)
        caps = manifest.get("capabilities", [])
        assert "semantic_search" in caps
        assert "wsp_lookup" in caps


# ---------------------------------------------------------------------------
# Catalog Tests
# ---------------------------------------------------------------------------


class TestCatalogBinding:
    """mall-catalog.json contains holoindex_prod_01 with correct fields."""

    def test_catalog_valid_json(self):
        with open(CATALOG_PATH, encoding="utf-8") as f:
            catalog = json.load(f)
        assert isinstance(catalog, list)

    def test_holoindex_in_catalog(self):
        with open(CATALOG_PATH, encoding="utf-8") as f:
            catalog = json.load(f)
        ids = [e["foundup_id"] for e in catalog]
        assert "holoindex_prod_01" in ids

    def test_holoindex_launch_readiness_discoverable_only(self):
        with open(CATALOG_PATH, encoding="utf-8") as f:
            catalog = json.load(f)
        entry = next(e for e in catalog if e["foundup_id"] == "holoindex_prod_01")
        assert entry["launch_readiness"] == "discoverable_only"

    def test_holoindex_routing_prefix(self):
        with open(CATALOG_PATH, encoding="utf-8") as f:
            catalog = json.load(f)
        entry = next(e for e in catalog if e["foundup_id"] == "holoindex_prod_01")
        assert entry["routing_prefix"] == "/f/holoindex_prod_01"

    def test_holoindex_no_entry_url_while_stub(self):
        """No entry_url while bridge is stub-only — would overclaim readiness."""
        with open(CATALOG_PATH, encoding="utf-8") as f:
            catalog = json.load(f)
        entry = next(e for e in catalog if e["foundup_id"] == "holoindex_prod_01")
        assert "entry_url" not in entry, (
            "entry_url must not exist in catalog while bridge is stub-only"
        )


# ---------------------------------------------------------------------------
# UI Connector Tests
# ---------------------------------------------------------------------------


class TestConnectorContract:
    """connector.js emits correct postMessage payloads per contract."""

    def _read_connector(self):
        with open(CONNECTOR_PATH, encoding="utf-8") as f:
            return f.read()

    def test_connector_emits_agent_request_type(self):
        js = self._read_connector()
        assert "type: 'agent_request'" in js or '"type": "agent_request"' in js

    def test_connector_uses_openclaw_search_route(self):
        js = self._read_connector()
        assert "route: 'openclaw_search'" in js or '"route": "openclaw_search"' in js

    def test_connector_sends_semantic_search_action(self):
        js = self._read_connector()
        assert "action: 'semantic_search'" in js or '"action": "semantic_search"' in js

    def test_connector_sends_query_field(self):
        js = self._read_connector()
        assert "query:" in js or '"query"' in js

    def test_connector_posts_to_parent(self):
        js = self._read_connector()
        assert "window.parent.postMessage" in js


# ---------------------------------------------------------------------------
# Contract Doc vs Implementation Alignment
# ---------------------------------------------------------------------------


class TestContractDocAlignment:
    """Contract doc and implementation agree on service/field names."""

    def _read_contract(self):
        with open(CONTRACT_PATH, encoding="utf-8") as f:
            return f.read()

    def _read_interceptor(self):
        with open(INTERCEPTOR_PATH, encoding="utf-8") as f:
            return f.read()

    def test_contract_defines_agent_request_type(self):
        contract = self._read_contract()
        assert '"type": "agent_request"' in contract

    def test_contract_defines_agent_response_type(self):
        contract = self._read_contract()
        assert '"type": "agent_response"' in contract

    def test_contract_defines_openclaw_search_route(self):
        contract = self._read_contract()
        assert '"route": "openclaw_search"' in contract or "openclaw_search" in contract

    def test_contract_response_has_results_field(self):
        contract = self._read_contract()
        assert '"results"' in contract

    def test_contract_response_has_quantum_coherence(self):
        contract = self._read_contract()
        assert '"quantum_coherence"' in contract or "quantum_coherence" in contract

    def test_interceptor_handles_openclaw_search(self):
        js = self._read_interceptor()
        assert "openclaw_search" in js

    def test_interceptor_handles_semantic_search(self):
        js = self._read_interceptor()
        assert "semantic_search" in js

    def test_interceptor_handles_wsp_lookup(self):
        js = self._read_interceptor()
        assert "wsp_lookup" in js

    def test_interceptor_stub_marks_stub_true(self):
        """Interceptor stub responses must include stub: true."""
        js = self._read_interceptor()
        assert "stub: true" in js

    def test_contract_response_has_service_field(self):
        """Contract Section 3.1 defines service field in response."""
        contract = self._read_contract()
        assert '"service": "holoindex"' in contract

    def test_interceptor_has_route_service_map(self):
        """Interceptor maps routes to service identifiers."""
        js = self._read_interceptor()
        assert "ROUTE_SERVICE_MAP" in js

    def test_interceptor_injects_service_in_response(self):
        """Interceptor sets response.service from ROUTE_SERVICE_MAP."""
        js = self._read_interceptor()
        assert "response.service" in js

    def test_interceptor_maps_openclaw_to_holoindex(self):
        """openclaw_search route maps to 'holoindex' service."""
        js = self._read_interceptor()
        assert "'openclaw_search'" in js
        assert "'holoindex'" in js


# ---------------------------------------------------------------------------
# Connector Response Handler Tests
# ---------------------------------------------------------------------------


class TestConnectorResponsePath:
    """connector.js response handler matches interceptor service field."""

    def _read_connector(self):
        with open(CONNECTOR_PATH, encoding="utf-8") as f:
            return f.read()

    def _read_interceptor(self):
        with open(INTERCEPTOR_PATH, encoding="utf-8") as f:
            return f.read()

    def test_connector_checks_service_holoindex(self):
        """Connector filters responses by service === 'holoindex'."""
        js = self._read_connector()
        assert "service" in js
        assert "'holoindex'" in js or '"holoindex"' in js

    def test_connector_checks_agent_response_type(self):
        """Connector checks for type === 'agent_response'."""
        js = self._read_connector()
        assert "'agent_response'" in js or '"agent_response"' in js

    def test_interceptor_and_connector_agree_on_service_name(self):
        """Interceptor ROUTE_SERVICE_MAP and connector filter use same service name."""
        connector = self._read_connector()
        interceptor = self._read_interceptor()
        # Both must reference 'holoindex' as the service identifier
        assert "'holoindex'" in interceptor
        assert "'holoindex'" in connector or '"holoindex"' in connector

    def test_connector_reads_data_from_response(self):
        """Connector reads response data from event.data.data (per contract Section 3.1)."""
        js = self._read_connector()
        assert "event.data.data" in js


# ---------------------------------------------------------------------------
# File Tracking Tests
# ---------------------------------------------------------------------------


class TestRepoTracking:
    """All external FoundUp bundle files are repo-tracked."""

    REQUIRED_FILES = [
        "holo_index/foundup_manifest.json",
        "holo_index/foundup_adapter/bridge_stub.py",
        "holo_index/docs/EXTERNAL_FOUNDUP_BRIDGE_CONTRACT.md",
        "public/f/holoindex_prod_01/index.html",
        "public/f/holoindex_prod_01/js/connector.js",
        "public/f/holoindex_prod_01/css/style.css",
        "public/member/js/shell-bridge-interceptor.js",
        "public/member/mall-catalog.json",
    ]

    @pytest.mark.parametrize("relpath", REQUIRED_FILES)
    def test_file_exists(self, relpath):
        full = os.path.join(REPO_ROOT, relpath)
        assert os.path.isfile(full), f"{relpath} must exist in repo"
