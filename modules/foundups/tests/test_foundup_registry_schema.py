# -*- coding: utf-8 -*-
"""Tests for FoundUp Registry Schema with Portfolio Fields.

FOUNDUPS_PUBLIC_PORTFOLIO_STATUS_SCHEMA_PHASE1

WSP 97 Labels:
  - PUBLIC_PORTFOLIO_SCHEMA_ONLY
  - NO_RUNTIME_CHANGE
  - NO_ROUTE_CREATION
  - NO_PFMALL_CATALOG_MUTATION
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "foundup_registry.schema.json"
EXAMPLE_PATH = Path(__file__).resolve().parent.parent / "foundup_registry.example.json"
REGISTRY_PATH = Path(__file__).resolve().parent.parent / "foundup_registry.json"


@pytest.fixture
def schema():
    """Load the registry schema."""
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def example():
    """Load the example registry."""
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def registry():
    """Load the production registry."""
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


class TestSchemaStructure:
    """Test schema has required portfolio field definitions."""

    def test_schema_has_portfolio_status_enum(self, schema):
        """PortfolioStatus enum exists with required values."""
        defs = schema.get("$defs", {})
        assert "PortfolioStatus" in defs
        ps = defs["PortfolioStatus"]
        assert ps["type"] == "string"
        assert "not_portfolio" in ps["enum"]
        assert "portfolio_candidate" in ps["enum"]
        assert "portfolio_ready" in ps["enum"]
        assert "portfolio_featured" in ps["enum"]

    def test_schema_has_poc_landing_status_enum(self, schema):
        """PocLandingStatus enum exists with required values."""
        defs = schema.get("$defs", {})
        assert "PocLandingStatus" in defs
        pls = defs["PocLandingStatus"]
        assert pls["type"] == "string"
        assert "none" in pls["enum"]
        assert "placeholder" in pls["enum"]
        assert "functional" in pls["enum"]
        assert "polished" in pls["enum"]

    def test_schema_entry_has_portfolio_fields(self, schema):
        """RegistryEntry has all required portfolio properties."""
        entry_props = schema["$defs"]["RegistryEntry"]["properties"]

        required_fields = [
            "portfolio_status",
            "poc_landing_status",
            "website_url",
            "poc_url",
            "app_url",
            "github_url",
            "docs_url",
            "screenshot_url",
            "public_summary",
            "portfolio_priority",
            "portfolio_ready",
            "portfolio_evidence_docs",
        ]

        for field in required_fields:
            assert field in entry_props, f"Missing portfolio field: {field}"

    def test_portfolio_ready_is_boolean(self, schema):
        """portfolio_ready field is boolean type."""
        entry_props = schema["$defs"]["RegistryEntry"]["properties"]
        assert entry_props["portfolio_ready"]["type"] == "boolean"
        assert entry_props["portfolio_ready"]["default"] is False

    def test_url_fields_allow_null_or_string(self, schema):
        """URL fields allow null or string."""
        entry_props = schema["$defs"]["RegistryEntry"]["properties"]
        url_fields = ["website_url", "poc_url", "app_url", "github_url", "docs_url", "screenshot_url"]

        for field in url_fields:
            field_def = entry_props[field]
            assert field_def["type"] == ["string", "null"], f"{field} should allow string or null"

    def test_portfolio_priority_allows_null_or_integer(self, schema):
        """portfolio_priority allows null or integer 1-100."""
        entry_props = schema["$defs"]["RegistryEntry"]["properties"]
        pp = entry_props["portfolio_priority"]
        assert pp["type"] == ["integer", "null"]
        assert pp["minimum"] == 1
        assert pp["maximum"] == 100

    def test_public_summary_max_length(self, schema):
        """public_summary has 280 char max length."""
        entry_props = schema["$defs"]["RegistryEntry"]["properties"]
        ps = entry_props["public_summary"]
        assert ps["maxLength"] == 280


@pytest.mark.skipif(not HAS_JSONSCHEMA, reason="jsonschema not installed")
class TestSchemaValidation:
    """Test that example and registry validate against schema."""

    def test_example_validates(self, schema, example):
        """Example registry validates against schema."""
        jsonschema.validate(instance=example, schema=schema)

    def test_registry_validates(self, schema, registry):
        """Production registry validates against schema."""
        jsonschema.validate(instance=registry, schema=registry)


class TestExamplePortfolioFields:
    """Test example has portfolio fields populated correctly."""

    def test_gotjunk_is_portfolio_candidate(self, example):
        """gotjunk_001 should be portfolio_candidate (has PoC)."""
        gotjunk = next(e for e in example["entities"] if e["foundup_id"] == "gotjunk_001")
        assert gotjunk["portfolio_status"] == "portfolio_candidate"
        assert gotjunk["poc_landing_status"] == "functional"
        assert gotjunk["portfolio_ready"] is False  # Not yet marked ready

    def test_voteballots_not_portfolio_ready(self, example):
        """voteballots should NOT be portfolio_ready (no public implementation)."""
        vote = next(e for e in example["entities"] if e["foundup_id"] == "voteballots")
        assert vote["portfolio_status"] == "not_portfolio"
        assert vote["portfolio_ready"] is False
        assert vote["poc_landing_status"] == "none"

    def test_platform_layer_not_portfolio(self, example):
        """Platform layers (pfmall) should not be in portfolio."""
        pfmall = next(e for e in example["entities"] if e["foundup_id"] == "pfmall")
        assert pfmall["portfolio_status"] == "not_portfolio"
        assert pfmall["portfolio_ready"] is False


class TestRegistryPortfolioConsistency:
    """Test production registry portfolio field consistency."""

    def test_all_entities_have_portfolio_ready_boolean(self, registry):
        """Every entity should have portfolio_ready as boolean."""
        for entity in registry["entities"]:
            fid = entity["foundup_id"]
            if "portfolio_ready" in entity:
                assert isinstance(entity["portfolio_ready"], bool), f"{fid} portfolio_ready not boolean"

    def test_portfolio_ready_requires_evidence(self, registry):
        """Entries with portfolio_ready=True should have evidence docs."""
        for entity in registry["entities"]:
            if entity.get("portfolio_ready") is True:
                evidence = entity.get("portfolio_evidence_docs", [])
                assert len(evidence) > 0, f"{entity['foundup_id']} is portfolio_ready but has no evidence"

    def test_no_invented_urls(self, registry):
        """URLs should be null or real, not invented placeholders."""
        placeholder_markers = ["DEFERRED", "TODO", "PLACEHOLDER", "example.com"]
        url_fields = ["website_url", "poc_url", "app_url", "github_url", "docs_url", "screenshot_url"]

        for entity in registry["entities"]:
            for field in url_fields:
                val = entity.get(field)
                if val is not None:
                    for marker in placeholder_markers:
                        assert marker.lower() not in val.lower(), \
                            f"{entity['foundup_id']}.{field} has placeholder URL"
