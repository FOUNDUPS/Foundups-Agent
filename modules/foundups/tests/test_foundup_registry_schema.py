# -*- coding: utf-8 -*-
"""Tests for FoundUp Canonical Registry Schema validation.

FOUNDUP_CANONICAL_REGISTRY_SCHEMA_PHASE1

These tests verify:
1. Schema validates correct registry entries
2. Example registry validates against schema
3. Invalid entity_type fails validation
4. Token symbol required when token_status is EXISTS
5. TOKEN_DEFERRED/UNKNOWN must be used for unknown tokens
6. VOTE can be SPECIFIED without IMPLEMENTED
7. move2japan can be access_service (not FoundUp)
8. External FoundUps require related_external_repo
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
