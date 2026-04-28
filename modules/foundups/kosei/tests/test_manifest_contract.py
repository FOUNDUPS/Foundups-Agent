"""Kosei FoundUp Manifest Contract Tests

Validates that Kosei's foundup_manifest.json meets the canonical pfMALL
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


class TestKoseiManifestExists:
    """Kosei must have a valid foundup_manifest.json."""

    def test_kosei_manifest_exists(self):
        """foundup_manifest.json exists at module root."""
        assert MANIFEST_PATH.is_file(), f"Expected {MANIFEST_PATH} to exist"

    def test_kosei_manifest_valid_json(self):
        """foundup_manifest.json is valid JSON."""
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict), "Manifest must be a JSON object"


class TestKoseiManifestFields:
    """Kosei manifest must have required fields for pfMALL integration."""

    @pytest.fixture
    def manifest(self):
        """Load the Kosei manifest."""
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            return json.load(f)

    def test_kosei_entry_url_non_empty(self, manifest):
        """entry_url must be a non-empty string for shell embedding.

        WSP 97 truth boundary: This asserts the field exists and is truthy.
        It does NOT assert the URL is reachable (network test).
        """
        entry_url = manifest.get("entry_url")
        assert entry_url, "entry_url must be non-empty for launch_readiness=ready"
        assert isinstance(entry_url, str), "entry_url must be a string"

    def test_kosei_launch_readiness_ready(self, manifest):
        """launch_readiness must be 'ready' for Kosei.

        Kosei was verified embeddable on 2026-04-13 (BX4/BX5 workers).
        """
        assert manifest.get("launch_readiness") == "ready", (
            "Kosei launch_readiness must be 'ready' per BX5 verification"
        )

    def test_kosei_routing_prefix_canonical(self, manifest):
        """routing_prefix must follow WSP 104 canonical format.

        WSP 104: /f/{foundup_id} is the canonical FoundUp landing namespace.
        """
        routing_prefix = manifest.get("routing_prefix")
        assert routing_prefix == "/f/kosei", (
            f"routing_prefix must be '/f/kosei', got '{routing_prefix}'"
        )

    def test_kosei_data_namespace_valid(self, manifest):
        """data_namespace must follow idb_{foundup_id} convention.

        WSP 104: Tenant isolation requires scoped IndexedDB namespace.
        """
        data_namespace = manifest.get("data_namespace")
        assert data_namespace, "data_namespace must be set"
        assert data_namespace.startswith("idb_"), (
            f"data_namespace must start with 'idb_', got '{data_namespace}'"
        )

    def test_kosei_foundup_id_matches_namespace(self, manifest):
        """foundup_id must align with data_namespace suffix."""
        foundup_id = manifest.get("foundup_id")
        data_namespace = manifest.get("data_namespace")
        expected_namespace = f"idb_{foundup_id}"
        assert data_namespace == expected_namespace, (
            f"data_namespace '{data_namespace}' must match 'idb_{foundup_id}'"
        )
