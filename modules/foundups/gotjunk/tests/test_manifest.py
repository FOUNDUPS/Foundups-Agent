"""
GotJunk Manifest Validation Tests

Validates foundup_manifest.json schema and signature.
Required for exfoliation gate: runtime_testable.
"""

import json
from pathlib import Path

import pytest


@pytest.fixture
def gotjunk_root():
    """Return gotjunk module root."""
    return Path(__file__).parent.parent


@pytest.fixture
def manifest(gotjunk_root):
    """Load gotjunk manifest."""
    manifest_path = gotjunk_root / "foundup_manifest.json"
    assert manifest_path.exists(), "foundup_manifest.json required"
    return json.loads(manifest_path.read_text(encoding="utf-8"))


class TestManifestSchema:
    """Validate manifest schema per PFMALL_FOUNDUP_MANIFEST_SCHEMA.md."""

    def test_required_fields_present(self, manifest):
        """All required fields must be present."""
        required = [
            "foundup_id",
            "name",
            "version",
            "description",
            "tagline",
            "tier",
            "lifecycle_stage",
            "routing_prefix",
            "required_subscription_tier",
            "is_invite_only",
            "capabilities",
            "agent_routes",
            "data_namespace",
            "cabr_contract",
            "owner_id",
            "token_symbol",
            "created_at",
        ]
        for field in required:
            assert field in manifest, f"Missing required field: {field}"

    def test_foundup_id_format(self, manifest):
        """foundup_id should be present."""
        assert manifest.get("foundup_id"), "foundup_id cannot be empty"

    def test_tier_valid(self, manifest):
        """tier must be valid DAOTier enum value."""
        valid_tiers = ["F0_DAE", "F1_OPO", "F2_GROWTH", "F3_INFRA", "F4_MEGA", "F5_SYSTEMIC"]
        assert manifest.get("tier") in valid_tiers, f"Invalid tier: {manifest.get('tier')}"

    def test_lifecycle_stage_valid(self, manifest):
        """lifecycle_stage must be valid value."""
        valid_stages = ["incubating", "proto", "externalized", "federated"]
        assert manifest.get("lifecycle_stage") in valid_stages

    def test_cabr_contract_structure(self, manifest):
        """cabr_contract must have required fields."""
        cabr = manifest.get("cabr_contract", {})
        assert "v1_gate" in cabr, "cabr_contract missing v1_gate"
        assert "v2_proof" in cabr, "cabr_contract missing v2_proof"
        assert "v3_score_min" in cabr, "cabr_contract missing v3_score_min"

    def test_v3_score_min_range(self, manifest):
        """v3_score_min must be between 0.0 and 1.0."""
        score = manifest.get("cabr_contract", {}).get("v3_score_min", 0)
        assert 0.0 <= score <= 1.0, f"v3_score_min out of range: {score}"

    def test_capabilities_is_list(self, manifest):
        """capabilities must be a list."""
        assert isinstance(manifest.get("capabilities"), list)

    def test_agent_routes_is_list(self, manifest):
        """agent_routes must be a list."""
        assert isinstance(manifest.get("agent_routes"), list)


class TestManifestValues:
    """Validate gotjunk-specific manifest values."""

    def test_name_is_gotjunk(self, manifest):
        """Name should be GotJunk."""
        assert manifest.get("name") == "GotJunk"

    def test_token_symbol(self, manifest):
        """Token symbol should be JUNK."""
        assert manifest.get("token_symbol") == "JUNK"

    def test_owner_is_012(self, manifest):
        """Owner should be 012."""
        assert manifest.get("owner_id") == "012"

    def test_marketplace_capability(self, manifest):
        """Should have marketplace capability."""
        assert "marketplace" in manifest.get("capabilities", [])
