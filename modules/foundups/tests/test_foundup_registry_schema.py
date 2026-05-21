# -*- coding: utf-8 -*-
"""Tests for FoundUp Canonical Registry Schema validation.

FOUNDUP_CANONICAL_REGISTRY_SCHEMA_PHASE1
FOUNDUPS_PUBLIC_PORTFOLIO_STATUS_SCHEMA_PHASE1

WSP 97 Labels:
  - PUBLIC_PORTFOLIO_SCHEMA_ONLY
  - NO_RUNTIME_CHANGE
  - NO_ROUTE_CREATION
  - NO_PFMALL_CATALOG_MUTATION

These tests verify:
1. Schema validates correct registry entries
2. Example registry validates against schema
3. Invalid entity_type fails validation
4. Token symbol required when token_status is EXISTS
5. TOKEN_DEFERRED/UNKNOWN must be used for unknown tokens
6. VOTE can be SPECIFIED without IMPLEMENTED
7. move2japan can be access_service (not FoundUp)
8. External FoundUps require related_external_repo
9. Portfolio status fields are properly defined
10. Portfolio field constraints are enforced
"""

import json
from pathlib import Path

import pytest

try:
    import jsonschema
    from jsonschema import Draft202012Validator, ValidationError
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False


SCHEMA_PATH = Path(__file__).parent.parent / "foundup_registry.schema.json"
EXAMPLE_PATH = Path(__file__).parent.parent / "foundup_registry.example.json"
REGISTRY_PATH = Path(__file__).parent.parent / "foundup_registry.json"


@pytest.fixture
def schema():
    """Load the registry schema."""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def example_registry():
    """Load the example registry."""
    with open(EXAMPLE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def production_registry():
    """Load the production registry."""
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def validator(schema):
    """Create a JSON Schema validator."""
    if not JSONSCHEMA_AVAILABLE:
        pytest.skip("jsonschema not installed")
    return Draft202012Validator(schema)


class TestSchemaStructure:
    """Test schema file structure and definitions."""

    def test_schema_file_exists(self):
        """Schema file exists at expected path."""
        assert SCHEMA_PATH.exists(), f"Schema not found at {SCHEMA_PATH}"

    def test_schema_is_valid_json(self, schema):
        """Schema is valid JSON."""
        assert "$schema" in schema
        assert "$defs" in schema
        assert "properties" in schema

    def test_schema_has_required_defs(self, schema):
        """Schema has all required type definitions."""
        required_defs = [
            "EntityType",
            "ImplementationStatus",
            "TokenStatus",
            "PublicSurfaceStatus",
            "LifecycleStage",
            "RegistryEntry",
        ]
        for def_name in required_defs:
            assert def_name in schema["$defs"], f"Missing $defs/{def_name}"

    def test_entity_type_enum_has_access_service(self, schema):
        """EntityType enum includes access_service (per move2japan audit)."""
        entity_types = schema["$defs"]["EntityType"]["enum"]
        assert "access_service" in entity_types

    def test_implementation_status_enum_complete(self, schema):
        """ImplementationStatus enum has all required values."""
        expected = [
            "SPECIFIED",
            "IMPLEMENTED",
            "TESTED",
            "RUNTIME_ENFORCED",
            "DOC_ONLY",
            "SIMULATOR_ONLY",
            "REVIEW_ONLY",
            "GATED_NOT_ENABLED",
            "DEPRECATED",
            "UNKNOWN",
        ]
        actual = schema["$defs"]["ImplementationStatus"]["enum"]
        for status in expected:
            assert status in actual, f"Missing status: {status}"

    def test_token_status_enum_has_deferred(self, schema):
        """TokenStatus enum includes TOKEN_DEFERRED."""
        token_statuses = schema["$defs"]["TokenStatus"]["enum"]
        assert "TOKEN_DEFERRED" in token_statuses
        assert "EXISTS" in token_statuses
        assert "NOT_APPLICABLE" in token_statuses
        assert "UNKNOWN" in token_statuses

    # Portfolio schema tests (7 new tests)
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


@pytest.mark.skipif(not JSONSCHEMA_AVAILABLE, reason="jsonschema not installed")
class TestExampleRegistryValidation:
    """Test that example registry validates against schema."""

    def test_example_file_exists(self):
        """Example registry file exists."""
        assert EXAMPLE_PATH.exists(), f"Example not found at {EXAMPLE_PATH}"

    def test_example_validates_against_schema(self, validator, example_registry):
        """Example registry validates against schema."""
        errors = list(validator.iter_errors(example_registry))
        if errors:
            error_messages = [f"{e.json_path}: {e.message}" for e in errors]
            pytest.fail(f"Validation errors:\n" + "\n".join(error_messages))

    def test_example_has_required_fields(self, example_registry):
        """Example registry has required top-level fields."""
        assert "schema_version" in example_registry
        assert "last_updated" in example_registry
        assert "entities" in example_registry

    def test_example_has_entities(self, example_registry):
        """Example registry has at least one entity."""
        assert len(example_registry["entities"]) > 0


@pytest.mark.skipif(not JSONSCHEMA_AVAILABLE, reason="jsonschema not installed")
class TestInvalidEntityTypeRejection:
    """Test that invalid entity types are rejected."""

    def test_invalid_entity_type_fails(self, validator, schema):
        """Invalid entity_type value fails validation."""
        invalid_registry = {
            "schema_version": "1.0.0",
            "last_updated": "2026-05-18T00:00:00Z",
            "entities": [
                {
                    "foundup_id": "test_invalid",
                    "display_name": "Test Invalid",
                    "entity_type": "INVALID_TYPE",  # Invalid
                    "module_path": "modules/test",
                    "implementation_status": "SPECIFIED",
                    "token_status": "TOKEN_DEFERRED",
                }
            ],
        }
        errors = list(validator.iter_errors(invalid_registry))
        assert len(errors) > 0, "Invalid entity_type should fail validation"


@pytest.mark.skipif(not JSONSCHEMA_AVAILABLE, reason="jsonschema not installed")
class TestTokenStatusValidation:
    """Test token status validation rules."""

    def test_exists_requires_symbol(self, validator):
        """token_status EXISTS requires token_symbol."""
        invalid_registry = {
            "schema_version": "1.0.0",
            "last_updated": "2026-05-18T00:00:00Z",
            "entities": [
                {
                    "foundup_id": "test_no_symbol",
                    "display_name": "Test No Symbol",
                    "entity_type": "foundup",
                    "module_path": "modules/test",
                    "stage": "incubating",
                    "tier": "F0_DAE",
                    "implementation_status": "IMPLEMENTED",
                    "token_status": "EXISTS",
                    # Missing token_symbol
                }
            ],
        }
        errors = list(validator.iter_errors(invalid_registry))
        assert len(errors) > 0, "EXISTS without token_symbol should fail"

    def test_deferred_allows_null_symbol(self, validator):
        """TOKEN_DEFERRED allows null token_symbol."""
        valid_registry = {
            "schema_version": "1.0.0",
            "last_updated": "2026-05-18T00:00:00Z",
            "entities": [
                {
                    "foundup_id": "test_deferred",
                    "display_name": "Test Deferred",
                    "entity_type": "skeleton_candidate",
                    "module_path": "modules/test",
                    "implementation_status": "SPECIFIED",
                    "token_status": "TOKEN_DEFERRED",
                    "token_symbol": None,
                }
            ],
        }
        errors = list(validator.iter_errors(valid_registry))
        assert len(errors) == 0, "TOKEN_DEFERRED with null symbol should pass"


@pytest.mark.skipif(not JSONSCHEMA_AVAILABLE, reason="jsonschema not installed")
class TestVoteSpecifiedNotImplemented:
    """Test VOTE can be SPECIFIED without being IMPLEMENTED."""

    def test_vote_specified_validates(self, validator):
        """VOTE entry with SPECIFIED status validates."""
        vote_entry = {
            "schema_version": "1.0.0",
            "last_updated": "2026-05-18T00:00:00Z",
            "entities": [
                {
                    "foundup_id": "voteballots",
                    "display_name": "Vote/Ballots",
                    "entity_type": "skeleton_candidate",
                    "module_path": "modules/foundups/voteballots",
                    "implementation_status": "SPECIFIED",
                    "token_status": "EXISTS",
                    "token_symbol": "VOTE",
                }
            ],
        }
        errors = list(validator.iter_errors(vote_entry))
        assert len(errors) == 0, "VOTE SPECIFIED entry should validate"


@pytest.mark.skipif(not JSONSCHEMA_AVAILABLE, reason="jsonschema not installed")
class TestMove2JapanAccessService:
    """Test move2japan as access_service (not FoundUp)."""

    def test_access_service_validates(self, validator):
        """move2japan as access_service validates."""
        m2j_entry = {
            "schema_version": "1.0.0",
            "last_updated": "2026-05-18T00:00:00Z",
            "entities": [
                {
                    "foundup_id": "move2japan",
                    "display_name": "Move2Japan",
                    "entity_type": "access_service",
                    "module_path": "modules/foundups/move2japan",
                    "implementation_status": "IMPLEMENTED",
                    "token_status": "TOKEN_DEFERRED",
                }
            ],
        }
        errors = list(validator.iter_errors(m2j_entry))
        assert len(errors) == 0, "access_service entry should validate"

    def test_access_service_no_tier_required(self, validator):
        """access_service does not require tier field."""
        m2j_entry = {
            "schema_version": "1.0.0",
            "last_updated": "2026-05-18T00:00:00Z",
            "entities": [
                {
                    "foundup_id": "move2japan",
                    "display_name": "Move2Japan",
                    "entity_type": "access_service",
                    "module_path": "modules/foundups/move2japan",
                    "implementation_status": "IMPLEMENTED",
                    "token_status": "TOKEN_DEFERRED",
                    # No tier field - should be fine for access_service
                }
            ],
        }
        errors = list(validator.iter_errors(m2j_entry))
        assert len(errors) == 0


@pytest.mark.skipif(not JSONSCHEMA_AVAILABLE, reason="jsonschema not installed")
class TestExternalFoundupRequiresRepo:
    """Test external_foundup requires related_external_repo."""

    def test_external_requires_repo(self, validator):
        """external_foundup without repo fails validation."""
        invalid_external = {
            "schema_version": "1.0.0",
            "last_updated": "2026-05-18T00:00:00Z",
            "entities": [
                {
                    "foundup_id": "autopost",
                    "display_name": "AutoPost",
                    "entity_type": "external_foundup",
                    "module_path": None,
                    "stage": "incubating",
                    "tier": "F0_DAE",
                    "implementation_status": "IMPLEMENTED",
                    "token_status": "TOKEN_DEFERRED",
                    # Missing related_external_repo
                }
            ],
        }
        errors = list(validator.iter_errors(invalid_external))
        assert len(errors) > 0, "external_foundup without repo should fail"

    def test_external_with_repo_validates(self, validator):
        """external_foundup with repo validates."""
        valid_external = {
            "schema_version": "1.0.0",
            "last_updated": "2026-05-18T00:00:00Z",
            "entities": [
                {
                    "foundup_id": "autopost",
                    "display_name": "AutoPost",
                    "entity_type": "external_foundup",
                    "module_path": None,
                    "stage": "incubating",
                    "tier": "F0_DAE",
                    "implementation_status": "IMPLEMENTED",
                    "token_status": "TOKEN_DEFERRED",
                    "related_external_repo": "https://github.com/FOUNDUPS/autopost.git",
                }
            ],
        }
        errors = list(validator.iter_errors(valid_external))
        assert len(errors) == 0


@pytest.mark.skipif(not JSONSCHEMA_AVAILABLE, reason="jsonschema not installed")
class TestFoundupRequiresTierAndStage:
    """Test foundup entity_type requires tier and stage."""

    def test_foundup_requires_tier(self, validator):
        """foundup without tier fails validation."""
        invalid_foundup = {
            "schema_version": "1.0.0",
            "last_updated": "2026-05-18T00:00:00Z",
            "entities": [
                {
                    "foundup_id": "test_foundup",
                    "display_name": "Test FoundUp",
                    "entity_type": "foundup",
                    "module_path": "modules/test",
                    "implementation_status": "IMPLEMENTED",
                    "token_status": "EXISTS",
                    "token_symbol": "TEST",
                    # Missing tier and stage
                }
            ],
        }
        errors = list(validator.iter_errors(invalid_foundup))
        assert len(errors) > 0, "foundup without tier should fail"

    def test_foundup_with_tier_and_stage_validates(self, validator):
        """foundup with tier and stage validates."""
        valid_foundup = {
            "schema_version": "1.0.0",
            "last_updated": "2026-05-18T00:00:00Z",
            "entities": [
                {
                    "foundup_id": "gotjunk_001",
                    "display_name": "GotJunk",
                    "entity_type": "foundup",
                    "module_path": "modules/foundups/gotjunk",
                    "stage": "proto",
                    "tier": "F0_DAE",
                    "implementation_status": "IMPLEMENTED",
                    "token_status": "EXISTS",
                    "token_symbol": "JUNK",
                }
            ],
        }
        errors = list(validator.iter_errors(valid_foundup))
        assert len(errors) == 0


@pytest.mark.skipif(not JSONSCHEMA_AVAILABLE, reason="jsonschema not installed")
class TestProductionRegistryValidation:
    """Test production registry validates against schema."""

    def test_production_file_exists(self):
        """Production registry file exists."""
        assert REGISTRY_PATH.exists(), f"Registry not found at {REGISTRY_PATH}"

    def test_production_validates_against_schema(self, validator, production_registry):
        """All production registry entries validate against schema."""
        errors = list(validator.iter_errors(production_registry))
        if errors:
            error_messages = [f"{e.json_path}: {e.message}" for e in errors]
            pytest.fail(f"Validation errors:\n" + "\n".join(error_messages))

    def test_production_has_expected_entity_count(self, production_registry):
        """Production registry has expected number of entities."""
        assert len(production_registry["entities"]) >= 10, (
            "Expected at least 10 entities from manifests and audits"
        )

    def test_production_entity_ids_unique(self, production_registry):
        """All entity IDs in production registry are unique."""
        ids = [e["foundup_id"] for e in production_registry["entities"]]
        assert len(ids) == len(set(ids)), "Duplicate foundup_id found"

    def test_production_has_manifest_foundups(self, production_registry):
        """Production registry includes manifest-bearing FoundUps."""
        ids = {e["foundup_id"] for e in production_registry["entities"]}
        expected_manifest_ids = {"gotjunk_001", "kosei", "voteballots", "trade"}
        for expected in expected_manifest_ids:
            assert expected in ids, f"Missing manifest FoundUp: {expected}"

    def test_production_external_foundups_have_repos(self, production_registry):
        """External FoundUps have related_external_repo populated."""
        for entity in production_registry["entities"]:
            if entity.get("entity_type") == "external_foundup":
                assert entity.get("related_external_repo"), (
                    f"{entity['foundup_id']} is external but missing repo"
                )

    def test_production_foundups_have_tier_and_stage(self, production_registry):
        """FoundUp entities have tier and stage."""
        for entity in production_registry["entities"]:
            if entity.get("entity_type") == "foundup":
                assert entity.get("tier"), f"{entity['foundup_id']} missing tier"
                assert entity.get("stage"), f"{entity['foundup_id']} missing stage"

    def test_production_token_exists_has_symbol(self, production_registry):
        """Entries with token_status EXISTS have token_symbol."""
        for entity in production_registry["entities"]:
            if entity.get("token_status") == "EXISTS":
                assert entity.get("token_symbol"), (
                    f"{entity['foundup_id']} has EXISTS but no token_symbol"
                )


class TestNoInventedTokens:
    """Test that example registry does not invent tokens."""

    def test_example_uses_known_tokens_only(self, example_registry):
        """Example registry only uses documented token symbols."""
        known_tokens = {"JUNK", "KOSEI", "VOTE", "TRADE", "DOOM", "ANTI"}

        for entity in example_registry["entities"]:
            token = entity.get("token_symbol")
            if token is not None:
                assert token in known_tokens, (
                    f"Unknown token {token} for {entity['foundup_id']}. "
                    f"Use TOKEN_DEFERRED for unknown tokens."
                )

    def test_deferred_tokens_have_null_symbol(self, example_registry):
        """TOKEN_DEFERRED entries have null token_symbol."""
        for entity in example_registry["entities"]:
            if entity.get("token_status") == "TOKEN_DEFERRED":
                assert entity.get("token_symbol") is None, (
                    f"{entity['foundup_id']} has TOKEN_DEFERRED but non-null symbol"
                )


# ============================================================================
# Portfolio Schema Tests (FOUNDUPS_PUBLIC_PORTFOLIO_STATUS_SCHEMA_PHASE1)
# ============================================================================


@pytest.mark.skipif(not JSONSCHEMA_AVAILABLE, reason="jsonschema not installed")
class TestSchemaValidation:
    """Test that example and registry validate against schema."""

    def test_example_validates(self, validator, example_registry):
        """Example registry validates against schema."""
        jsonschema.validate(instance=example_registry, schema=validator.schema)

    def test_registry_validates(self, validator, production_registry):
        """Production registry validates against schema."""
        jsonschema.validate(instance=production_registry, schema=validator.schema)


class TestExamplePortfolioFields:
    """Test example has portfolio fields populated correctly."""

    def test_gotjunk_is_portfolio_candidate(self, example_registry):
        """gotjunk_001 should be portfolio_candidate (has PoC)."""
        gotjunk = next(e for e in example_registry["entities"] if e["foundup_id"] == "gotjunk_001")
        assert gotjunk["portfolio_status"] == "portfolio_candidate"
        assert gotjunk["poc_landing_status"] == "functional"
        assert gotjunk["portfolio_ready"] is False  # Not yet marked ready

    def test_voteballots_not_portfolio_ready(self, example_registry):
        """voteballots should NOT be portfolio_ready (no public implementation)."""
        vote = next(e for e in example_registry["entities"] if e["foundup_id"] == "voteballots")
        assert vote["portfolio_status"] == "not_portfolio"
        assert vote["portfolio_ready"] is False
        assert vote["poc_landing_status"] == "none"

    def test_platform_layer_not_portfolio(self, example_registry):
        """Platform layers (pfmall) should not be in portfolio."""
        pfmall = next(e for e in example_registry["entities"] if e["foundup_id"] == "pfmall")
        assert pfmall["portfolio_status"] == "not_portfolio"
        assert pfmall["portfolio_ready"] is False


class TestRegistryPortfolioConsistency:
    """Test production registry portfolio field consistency."""

    def test_all_entities_have_portfolio_ready_boolean(self, production_registry):
        """Every entity should have portfolio_ready as boolean."""
        for entity in production_registry["entities"]:
            fid = entity["foundup_id"]
            if "portfolio_ready" in entity:
                assert isinstance(entity["portfolio_ready"], bool), f"{fid} portfolio_ready not boolean"

    def test_portfolio_ready_requires_evidence(self, production_registry):
        """Entries with portfolio_ready=True should have evidence docs."""
        for entity in production_registry["entities"]:
            if entity.get("portfolio_ready") is True:
                evidence = entity.get("portfolio_evidence_docs", [])
                assert len(evidence) > 0, f"{entity['foundup_id']} is portfolio_ready but has no evidence"

    def test_no_invented_urls(self, production_registry):
        """URLs should be null or real, not invented placeholders."""
        placeholder_markers = ["DEFERRED", "TODO", "PLACEHOLDER", "example.com"]
        url_fields = ["website_url", "poc_url", "app_url", "github_url", "docs_url", "screenshot_url"]

        for entity in production_registry["entities"]:
            for field in url_fields:
                val = entity.get(field)
                if val is not None:
                    for marker in placeholder_markers:
                        assert marker.lower() not in val.lower(), \
                            f"{entity['foundup_id']}.{field} has placeholder URL"

    def test_portfolio_candidates_have_poc_url_or_app_url(self, production_registry):
        """Portfolio candidates should have at least poc_url or app_url."""
        for entity in production_registry["entities"]:
            if entity.get("portfolio_status") == "portfolio_candidate":
                has_url = entity.get("poc_url") or entity.get("app_url")
                assert has_url, f"{entity['foundup_id']} is portfolio_candidate but has no poc_url or app_url"
