# -*- coding: utf-8 -*-
"""HIA_FEDERATION_METADATA_TAGGING_PHASE2: Federation Metadata Tests

Tests that verify resolve_foundup_metadata() correctly tags files with
federation metadata (foundup_id, tenant_id, source_scope, external_repo).

WSP 97: These tests verify metadata correctness at the unit level.
        No ChromaDB, no live index, no LLM.
WSP 87: Keep tests focused on resolve_foundup_metadata() behavior.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from holo_index.core.indexing_engine import (
    resolve_foundup_metadata,
    _read_foundup_id_from_manifest,
    _FOUNDUP_MANIFEST_CACHE,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def clear_manifest_cache():
    """Clear the manifest cache before each test."""
    _FOUNDUP_MANIFEST_CACHE.clear()
    yield
    _FOUNDUP_MANIFEST_CACHE.clear()


PROJECT_ROOT = Path("O:/Foundups-Agent")


# =============================================================================
# Core FoundUp Path Resolution
# =============================================================================


class TestResolveFoundupMetadata:
    """Test resolve_foundup_metadata() path-to-FoundUp mapping."""

    def test_trade_foundup_path(self):
        """Trade FoundUp files should resolve to foundup_id='trade'."""
        path = PROJECT_ROOT / "modules" / "foundups" / "trade" / "src" / "trade_engine.py"
        result = resolve_foundup_metadata(path, PROJECT_ROOT)

        assert result["foundup_id"] == "trade"
        assert result["source_scope"] == "internal_foundup"
        assert result["tenant_id"] == "core"
        assert result["external_repo"] is False

    def test_kosei_foundup_path(self):
        """Kosei FoundUp files should resolve to foundup_id='kosei'."""
        path = PROJECT_ROOT / "modules" / "foundups" / "kosei" / "src" / "contracts.py"
        result = resolve_foundup_metadata(path, PROJECT_ROOT)

        assert result["foundup_id"] == "kosei"
        assert result["source_scope"] == "internal_foundup"

    def test_gotjunk_foundup_path(self):
        """GotJunk FoundUp uses manifest foundup_id='gotjunk_001' (not dir name)."""
        path = PROJECT_ROOT / "modules" / "foundups" / "gotjunk" / "src" / "gotjunk.py"
        result = resolve_foundup_metadata(path, PROJECT_ROOT)

        assert result["foundup_id"] == "gotjunk_001"
        assert result["source_scope"] == "internal_foundup"

    def test_voteballots_foundup_path(self):
        """VoteBallots FoundUp resolves to foundup_id='voteballots'."""
        path = PROJECT_ROOT / "modules" / "foundups" / "voteballots" / "src" / "vote.py"
        result = resolve_foundup_metadata(path, PROJECT_ROOT)

        assert result["foundup_id"] == "voteballots"
        assert result["source_scope"] == "internal_foundup"


# =============================================================================
# Core (non-FoundUp) Path Resolution
# =============================================================================


class TestCorePathResolution:
    """Test that non-FoundUp paths resolve to 'core'."""

    def test_holo_index_core_path(self):
        """HoloIndex core files should resolve to 'core'."""
        path = PROJECT_ROOT / "holo_index" / "core" / "search_engine.py"
        result = resolve_foundup_metadata(path, PROJECT_ROOT)

        assert result["foundup_id"] == "core"
        assert result["source_scope"] == "core"
        assert result["tenant_id"] == "core"
        assert result["external_repo"] is False

    def test_wsp_framework_path(self):
        """WSP framework files should resolve to 'core'."""
        path = PROJECT_ROOT / "WSP_framework" / "src" / "WSP_97_System_Execution_Prompting_Protocol.md"
        result = resolve_foundup_metadata(path, PROJECT_ROOT)

        assert result["foundup_id"] == "core"
        assert result["source_scope"] == "core"

    def test_infrastructure_module_path(self):
        """Infrastructure modules should resolve to 'core' (not a FoundUp)."""
        path = PROJECT_ROOT / "modules" / "infrastructure" / "wre_core" / "src" / "wre_master_orchestrator.py"
        result = resolve_foundup_metadata(path, PROJECT_ROOT)

        assert result["foundup_id"] == "core"
        assert result["source_scope"] == "core"

    def test_docs_path(self):
        """Top-level docs should resolve to 'core'."""
        path = PROJECT_ROOT / "docs" / "audits" / "some_audit.md"
        result = resolve_foundup_metadata(path, PROJECT_ROOT)

        assert result["foundup_id"] == "core"
        assert result["source_scope"] == "core"

    def test_knowledge_path(self):
        """Knowledge/papers should resolve to 'core'."""
        path = PROJECT_ROOT / "WSP_knowledge" / "docs" / "Papers" / "some_paper.md"
        result = resolve_foundup_metadata(path, PROJECT_ROOT)

        assert result["foundup_id"] == "core"
        assert result["source_scope"] == "core"

    def test_scripts_path(self):
        """Scripts directory should resolve to 'core'."""
        path = PROJECT_ROOT / "scripts" / "deploy.py"
        result = resolve_foundup_metadata(path, PROJECT_ROOT)

        assert result["foundup_id"] == "core"
        assert result["source_scope"] == "core"


# =============================================================================
# External Repo Guard
# =============================================================================


class TestExternalRepoGuard:
    """Test that external_repo is always False for current indexing."""

    def test_foundup_path_not_external(self):
        """FoundUp files are internal, not external."""
        path = PROJECT_ROOT / "modules" / "foundups" / "trade" / "README.md"
        result = resolve_foundup_metadata(path, PROJECT_ROOT)
        assert result["external_repo"] is False

    def test_core_path_not_external(self):
        """Core files are internal, not external."""
        path = PROJECT_ROOT / "holo_index" / "core" / "indexing_engine.py"
        result = resolve_foundup_metadata(path, PROJECT_ROOT)
        assert result["external_repo"] is False


# =============================================================================
# Tenant ID
# =============================================================================


class TestTenantId:
    """Test that tenant_id defaults to 'core' for all paths."""

    def test_foundup_tenant_is_core(self):
        """FoundUp tenant_id is 'core' (Phase 2 default, future: per-FoundUp)."""
        path = PROJECT_ROOT / "modules" / "foundups" / "trade" / "src" / "trade.py"
        result = resolve_foundup_metadata(path, PROJECT_ROOT)
        assert result["tenant_id"] == "core"

    def test_core_tenant_is_core(self):
        """Core tenant_id is 'core'."""
        path = PROJECT_ROOT / "holo_index" / "core" / "search_engine.py"
        result = resolve_foundup_metadata(path, PROJECT_ROOT)
        assert result["tenant_id"] == "core"


# =============================================================================
# Manifest Fallback
# =============================================================================


class TestManifestFallback:
    """Test fallback when manifest is missing or malformed."""

    def test_missing_manifest_uses_dir_name(self, tmp_path):
        """FoundUp without manifest falls back to directory name as foundup_id."""
        # Create a path that looks like a FoundUp but has no manifest
        foundup_dir = tmp_path / "modules" / "foundups" / "phantom"
        foundup_dir.mkdir(parents=True)
        file_path = foundup_dir / "src" / "phantom.py"

        result = resolve_foundup_metadata(file_path, tmp_path)

        assert result["foundup_id"] == "phantom"
        assert result["source_scope"] == "internal_foundup"

    def test_malformed_manifest_uses_dir_name(self, tmp_path):
        """FoundUp with malformed manifest falls back to directory name."""
        foundup_dir = tmp_path / "modules" / "foundups" / "broken"
        foundup_dir.mkdir(parents=True)
        manifest = foundup_dir / "foundup_manifest.json"
        manifest.write_text("not valid json", encoding="utf-8")
        file_path = foundup_dir / "src" / "broken.py"

        result = resolve_foundup_metadata(file_path, tmp_path)

        assert result["foundup_id"] == "broken"
        assert result["source_scope"] == "internal_foundup"

    def test_manifest_without_foundup_id_uses_dir_name(self, tmp_path):
        """Manifest missing foundup_id field falls back to directory name."""
        foundup_dir = tmp_path / "modules" / "foundups" / "noid"
        foundup_dir.mkdir(parents=True)
        manifest = foundup_dir / "foundup_manifest.json"
        manifest.write_text(json.dumps({"name": "NoID FoundUp"}), encoding="utf-8")
        file_path = foundup_dir / "src" / "noid.py"

        result = resolve_foundup_metadata(file_path, tmp_path)

        assert result["foundup_id"] == "noid"
        assert result["source_scope"] == "internal_foundup"


# =============================================================================
# Manifest Cache
# =============================================================================


class TestManifestCache:
    """Test manifest caching behavior."""

    def test_cache_prevents_rereading(self, tmp_path):
        """Second call for same FoundUp uses cached manifest."""
        foundup_dir = tmp_path / "modules" / "foundups" / "cached"
        foundup_dir.mkdir(parents=True)
        manifest = foundup_dir / "foundup_manifest.json"
        manifest.write_text(json.dumps({"foundup_id": "cached_001"}), encoding="utf-8")

        file1 = foundup_dir / "src" / "a.py"
        file2 = foundup_dir / "src" / "b.py"

        r1 = resolve_foundup_metadata(file1, tmp_path)
        r2 = resolve_foundup_metadata(file2, tmp_path)

        assert r1["foundup_id"] == "cached_001"
        assert r2["foundup_id"] == "cached_001"

        # Cache should have exactly one entry for this manifest
        manifest_key = str(foundup_dir / "foundup_manifest.json")
        assert manifest_key in _FOUNDUP_MANIFEST_CACHE


# =============================================================================
# Return Shape
# =============================================================================


class TestReturnShape:
    """Test that return dict always has the expected keys."""

    def test_foundup_return_keys(self):
        """FoundUp path returns all 4 federation keys."""
        path = PROJECT_ROOT / "modules" / "foundups" / "trade" / "x.py"
        result = resolve_foundup_metadata(path, PROJECT_ROOT)

        assert set(result.keys()) == {"foundup_id", "tenant_id", "source_scope", "external_repo"}

    def test_core_return_keys(self):
        """Core path returns all 4 federation keys."""
        path = PROJECT_ROOT / "holo_index" / "core" / "x.py"
        result = resolve_foundup_metadata(path, PROJECT_ROOT)

        assert set(result.keys()) == {"foundup_id", "tenant_id", "source_scope", "external_repo"}


# =============================================================================
# Windows Path Handling
# =============================================================================


class TestWindowsPathHandling:
    """Test that backslash paths resolve correctly on Windows."""

    def test_backslash_foundup_path(self):
        """Path with backslashes should still resolve FoundUp correctly."""
        path = Path("O:\\Foundups-Agent\\modules\\foundups\\trade\\src\\trade.py")
        result = resolve_foundup_metadata(path, PROJECT_ROOT)

        assert result["foundup_id"] == "trade"
        assert result["source_scope"] == "internal_foundup"

    def test_backslash_core_path(self):
        """Path with backslashes for core files."""
        path = Path("O:\\Foundups-Agent\\holo_index\\core\\search_engine.py")
        result = resolve_foundup_metadata(path, PROJECT_ROOT)

        assert result["foundup_id"] == "core"
        assert result["source_scope"] == "core"
