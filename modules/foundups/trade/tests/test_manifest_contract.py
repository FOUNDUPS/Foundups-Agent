"""Trade FoundUp Manifest Contract Tests

Validates that Trade's foundup_manifest.json meets the canonical pfMALL
FoundUp contract requirements for shell integration.

WSP References:
- WSP 97: System Execution Prompting Protocol (truth boundaries)
- WSP 104: FoundUp Route Namespace and Tenant Isolation Protocol

Contract: modules/foundups/docs/FOUNDUP_AI_HOOKS_AND_DAEMON_SURFACE_CONTRACT.md
"""
import json
from pathlib import Path

import pytest

MODULE_ROOT = Path(__file__).parent.parent
MANIFEST_PATH = MODULE_ROOT / "foundup_manifest.json"


class TestTradeManifestExists:
    """Trade must have a valid foundup_manifest.json."""

    def test_trade_manifest_exists(self):
        """foundup_manifest.json exists at module root."""
        assert MANIFEST_PATH.is_file(), f"Expected {MANIFEST_PATH} to exist"

    def test_trade_manifest_valid_json(self):
        """foundup_manifest.json is valid JSON."""
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict), "Manifest must be a JSON object"


class TestTradeManifestFields:
    """Trade manifest must have required fields for pfMALL integration."""

    @pytest.fixture
    def manifest(self):
        """Load the Trade manifest."""
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            return json.load(f)

    def test_trade_foundup_id(self, manifest):
        """foundup_id must be 'trade'."""
        assert manifest.get("foundup_id") == "trade"

    def test_trade_routing_prefix_canonical(self, manifest):
        """routing_prefix must follow WSP 104 canonical format.

        WSP 104: /f/{foundup_id} is the canonical FoundUp landing namespace.
        """
        routing_prefix = manifest.get("routing_prefix")
        assert routing_prefix == "/f/trade", (
            f"routing_prefix must be '/f/trade', got '{routing_prefix}'"
        )

    def test_trade_data_namespace_valid(self, manifest):
        """data_namespace must follow idb_{foundup_id} convention.

        WSP 104: Tenant isolation requires scoped IndexedDB namespace.
        """
        data_namespace = manifest.get("data_namespace")
        assert data_namespace == "idb_trade", (
            f"data_namespace must be 'idb_trade', got '{data_namespace}'"
        )

    def test_trade_lifecycle_stage_incubating(self, manifest):
        """lifecycle_stage must be 'incubating' for Phase 0."""
        assert manifest.get("lifecycle_stage") == "incubating"

    def test_trade_tier_f0_dae(self, manifest):
        """tier must be 'F0_DAE' for internal seed."""
        assert manifest.get("tier") == "F0_DAE"

    def test_trade_launch_readiness_discoverable_only(self, manifest):
        """launch_readiness must be 'discoverable_only' for Phase 0."""
        assert manifest.get("launch_readiness") == "discoverable_only"

    def test_trade_is_invite_only(self, manifest):
        """is_invite_only must be true for F0_DAE."""
        assert manifest.get("is_invite_only") is True

    def test_trade_entry_url_null(self, manifest):
        """entry_url should be null for incubating FoundUp.

        WSP 97 truth boundary: No deployed app yet.
        """
        assert manifest.get("entry_url") is None

    def test_trade_required_subscription_tier_free(self, manifest):
        """required_subscription_tier should be 'free' for incubating."""
        assert manifest.get("required_subscription_tier") == "free"

    def test_trade_cabr_contract_default(self, manifest):
        """cabr_contract should have default values."""
        cabr = manifest.get("cabr_contract", {})
        assert cabr.get("v1_gate") == "default"
        assert cabr.get("v2_proof") == "default"
        assert cabr.get("v3_score_min") == 0.5


class TestTradeManifestCapabilities:
    """Trade capabilities should be intelligence/simulation focused."""

    @pytest.fixture
    def manifest(self):
        """Load the Trade manifest."""
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            return json.load(f)

    def test_trade_capabilities_present(self, manifest):
        """capabilities must be present and non-empty."""
        capabilities = manifest.get("capabilities")
        assert capabilities is not None
        assert isinstance(capabilities, list)
        assert len(capabilities) > 0

    def test_trade_no_execution_capabilities(self, manifest):
        """capabilities must NOT include execution-related terms.

        WSP 97 truth boundary: No real trading capabilities in Phase 0.
        """
        capabilities = manifest.get("capabilities", [])
        execution_terms = [
            "execution", "trading", "order", "wallet", "signing",
            "deposit", "withdraw", "swap"
        ]
        for cap in capabilities:
            for term in execution_terms:
                assert term not in cap.lower(), (
                    f"Capability '{cap}' implies execution (contains '{term}')"
                )


class TestTradeManifestAgentRoutes:
    """Trade agent_routes should be query-only in Phase 0."""

    @pytest.fixture
    def manifest(self):
        """Load the Trade manifest."""
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            return json.load(f)

    def test_trade_agent_routes_query_only(self, manifest):
        """agent_routes should only include query routes in Phase 0."""
        routes = manifest.get("agent_routes", [])
        # Query routes are safe
        safe_routes = ["openclaw_query", "openclaw_search"]

        for route in routes:
            assert route in safe_routes, (
                f"Route '{route}' may imply execution capability"
            )
