# -*- coding: utf-8 -*-
"""Tests for FoundUp Registry Read-Only Loader.

Contract: MCP_FOUNDUP_SCOPE_REGISTRY_LOADER_SPEC_PHASE1
Section 9.1: Implementation Test Requirements

WSP 97 Labels:
  - READONLY_LOADER_ONLY
  - NO_REGISTRY_MUTATION
  - FAIL_CLOSED_REQUIRED
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import importlib.util
import sys

import pytest

# Direct module load to avoid broken __init__.py imports
_loader_path = Path(__file__).resolve().parent.parent / "src" / "foundup_registry_loader.py"
_spec = importlib.util.spec_from_file_location("foundup_registry_loader", _loader_path)
assert _spec is not None, f"Could not load spec from {_loader_path}"
_module = importlib.util.module_from_spec(_spec)
sys.modules["foundup_registry_loader"] = _module
assert _spec.loader is not None, "Spec has no loader"
_spec.loader.exec_module(_module)

FoundUpRegistryLoader = _module.FoundUpRegistryLoader
RegistryLoadError = _module.RegistryLoadError
get_entity_type = _module.get_entity_type
get_module_path = _module.get_module_path
is_valid_foundup_id = _module.is_valid_foundup_id
list_foundup_ids = _module.list_foundup_ids
load_registry = _module.load_registry

# Production registry path
REGISTRY_PATH = Path(__file__).resolve().parent.parent / "foundup_registry.json"


class TestLoadProductionRegistry:
    """Test loading the production registry."""

    def test_loads_production_registry(self):
        """Registry loads without error."""
        registry = load_registry()
        assert isinstance(registry, dict)
        assert "entities" in registry
        assert "schema_version" in registry

    def test_production_has_entities(self):
        """Production registry has at least 10 entities."""
        registry = load_registry()
        assert len(registry["entities"]) >= 10


class TestListFoundupIds:
    """Test list_foundup_ids function."""

    def test_lists_ids(self):
        """Returns tuple of foundup_ids."""
        ids = list_foundup_ids()
        assert isinstance(ids, tuple)
        assert len(ids) >= 10

    def test_lists_known_ids(self):
        """Known IDs are present."""
        ids = list_foundup_ids()
        assert "gotjunk_001" in ids
        assert "kosei" in ids
        assert "pfmall" in ids


class TestValidateFoundupId:
    """Test is_valid_foundup_id function."""

    def test_validates_known_id(self):
        """Known foundup_id returns True."""
        assert is_valid_foundup_id("gotjunk_001") is True
        assert is_valid_foundup_id("kosei") is True
        assert is_valid_foundup_id("pfmall") is True

    def test_rejects_unknown_id(self):
        """Unknown foundup_id returns False."""
        assert is_valid_foundup_id("nonexistent_xyz_999") is False
        assert is_valid_foundup_id("fake_foundup") is False

    def test_rejects_malformed_id_uppercase(self):
        """Uppercase ID returns False (pattern mismatch)."""
        assert is_valid_foundup_id("UPPERCASE") is False
        assert is_valid_foundup_id("GotJunk") is False

    def test_rejects_malformed_id_special_chars(self):
        """ID with special chars returns False."""
        assert is_valid_foundup_id("got-junk") is False
        assert is_valid_foundup_id("got.junk") is False
        assert is_valid_foundup_id("got junk") is False

    def test_rejects_empty_string(self):
        """Empty string returns False."""
        assert is_valid_foundup_id("") is False

    def test_rejects_non_string(self):
        """Non-string values return False."""
        assert is_valid_foundup_id(123) is False  # type: ignore
        assert is_valid_foundup_id(None) is False  # type: ignore
        assert is_valid_foundup_id(["gotjunk_001"]) is False  # type: ignore


class TestGetModulePath:
    """Test get_module_path function."""

    def test_returns_module_path_for_known_id(self):
        """Known ID returns module_path."""
        path = get_module_path("gotjunk_001")
        assert path == "modules/foundups/gotjunk"

    def test_returns_none_for_unknown_id(self):
        """Unknown ID returns None."""
        assert get_module_path("nonexistent_xyz") is None

    def test_returns_none_for_null_module_path(self):
        """External FoundUp with null module_path returns None."""
        # autopost is external_foundup with module_path: null
        path = get_module_path("autopost")
        assert path is None


class TestGetEntityType:
    """Test get_entity_type function."""

    def test_returns_entity_type_for_known_id(self):
        """Known ID returns entity_type."""
        assert get_entity_type("gotjunk_001") == "foundup"
        assert get_entity_type("pfmall") == "platform_layer"
        assert get_entity_type("autopost") == "external_foundup"

    def test_returns_none_for_unknown_id(self):
        """Unknown ID returns None."""
        assert get_entity_type("nonexistent_xyz") is None


class TestFailClosed:
    """Test fail-closed behavior."""

    def test_missing_registry_raises_file_not_found(self):
        """Missing registry path raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_registry(Path("/nonexistent/path/registry.json"))

    def test_missing_registry_loader_raises(self):
        """FoundUpRegistryLoader raises on missing file."""
        with pytest.raises(FileNotFoundError):
            FoundUpRegistryLoader(Path("/nonexistent/path/registry.json"))

    def test_malformed_json_raises(self):
        """Malformed JSON raises RegistryLoadError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{invalid json")
            f.flush()
            temp_path = Path(f.name)

        try:
            with pytest.raises(RegistryLoadError):
                load_registry(temp_path)
        finally:
            temp_path.unlink()

    def test_wrong_root_type_raises(self):
        """Registry with array root raises RegistryLoadError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(["not", "an", "object"], f)
            f.flush()
            temp_path = Path(f.name)

        try:
            with pytest.raises(RegistryLoadError, match="root must be an object"):
                load_registry(temp_path)
        finally:
            temp_path.unlink()

    def test_missing_entities_raises(self):
        """Registry without entities raises RegistryLoadError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"schema_version": "1.0.0"}, f)
            f.flush()
            temp_path = Path(f.name)

        try:
            with pytest.raises(RegistryLoadError, match="missing 'entities'"):
                load_registry(temp_path)
        finally:
            temp_path.unlink()

    def test_entities_not_array_raises(self):
        """Registry with entities not array raises RegistryLoadError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"entities": "not_an_array"}, f)
            f.flush()
            temp_path = Path(f.name)

        try:
            with pytest.raises(RegistryLoadError, match="'entities' must be an array"):
                load_registry(temp_path)
        finally:
            temp_path.unlink()


class TestReadOnly:
    """Test that loader is read-only."""

    def test_no_mutation_methods(self):
        """Loader has no mutation methods."""
        loader = FoundUpRegistryLoader()
        assert not hasattr(loader, "add_entry")
        assert not hasattr(loader, "remove_entry")
        assert not hasattr(loader, "update_entry")
        assert not hasattr(loader, "save")
        assert not hasattr(loader, "write")

    def test_registry_file_unchanged_after_operations(self):
        """Registry file is not modified by loader operations."""
        # Get file hash before
        original_content = REGISTRY_PATH.read_bytes()

        # Perform various operations
        loader = FoundUpRegistryLoader()
        _ = loader.list_foundup_ids()
        _ = loader.is_valid_foundup_id("gotjunk_001")
        _ = loader.get_module_path("gotjunk_001")
        _ = loader.get_entity_type("gotjunk_001")
        _ = loader.get_registry()

        # Verify file unchanged
        after_content = REGISTRY_PATH.read_bytes()
        assert original_content == after_content


class TestLoaderClass:
    """Test FoundUpRegistryLoader class directly."""

    def test_path_property(self):
        """Loader exposes path property."""
        loader = FoundUpRegistryLoader()
        assert loader.path == REGISTRY_PATH

    def test_custom_path(self):
        """Loader accepts custom path."""
        loader = FoundUpRegistryLoader(REGISTRY_PATH)
        assert loader.path == REGISTRY_PATH

    def test_entity_missing_foundup_id_raises(self):
        """Entity without foundup_id raises RegistryLoadError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"entities": [{"name": "no_id"}]}, f)
            f.flush()
            temp_path = Path(f.name)

        try:
            with pytest.raises(RegistryLoadError, match="missing 'foundup_id'"):
                FoundUpRegistryLoader(temp_path)
        finally:
            temp_path.unlink()


class TestModuleFunctions:
    """Test module-level convenience functions."""

    def test_functions_use_default_registry(self):
        """Module functions work with default registry."""
        # These should all work without explicit path
        ids = list_foundup_ids()
        assert len(ids) > 0

        valid = is_valid_foundup_id("gotjunk_001")
        assert valid is True

        path = get_module_path("gotjunk_001")
        assert path is not None

        etype = get_entity_type("gotjunk_001")
        assert etype is not None

    def test_functions_accept_custom_path(self):
        """Module functions accept custom path."""
        ids = list_foundup_ids(path=REGISTRY_PATH)
        assert len(ids) > 0
