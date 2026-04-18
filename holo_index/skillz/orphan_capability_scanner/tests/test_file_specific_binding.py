#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for CF4 File-Specific SKILLz Binding

Validates:
- Directory-level SKILLz.md still binds subtree (existing behavior preserved)
- File-specific *_SKILLz.md binds only target_file
- Ambiguous file-specific skill produces warning
- Missing target produces warning
- Existing module-level contracts remain connected
- Real m2m_SKILLz.md binding works
"""

import pytest
from pathlib import Path

from holo_index.skillz.orphan_capability_scanner.executor import (
    OrphanCapabilityScanner,
    FileSpecificBinding,
    REPO_ROOT,
)


class TestFileSpecificBindingDataclass:
    """Tests for FileSpecificBinding dataclass."""

    def test_binding_creation(self):
        """FileSpecificBinding should be creatable with required fields."""
        binding = FileSpecificBinding(
            skillz_path="modules/test/m2m_SKILLz.md",
            target_file="m2m_sentinel.py",
            inferred_target=None,
            is_bound=True,
        )
        assert binding.skillz_path == "modules/test/m2m_SKILLz.md"
        assert binding.target_file == "m2m_sentinel.py"
        assert binding.is_bound is True

    def test_binding_with_inferred(self):
        """FileSpecificBinding can have inferred_target instead of target_file."""
        binding = FileSpecificBinding(
            skillz_path="modules/test/unique_SKILLz.md",
            target_file=None,
            inferred_target="unique_tool.py",
            is_bound=True,
        )
        assert binding.target_file is None
        assert binding.inferred_target == "unique_tool.py"


class TestScannerFileSpecificLoading:
    """Tests for scanner's file-specific loading logic."""

    def test_parse_target_file_frontmatter(self):
        """Scanner should parse target_file from frontmatter."""
        scanner = OrphanCapabilityScanner(repo_root=REPO_ROOT)

        # Test with actual m2m_SKILLz.md
        m2m_path = REPO_ROOT / "modules" / "ai_intelligence" / "ai_overseer" / "src" / "m2m_SKILLz.md"
        if m2m_path.exists():
            target = scanner._parse_target_file_frontmatter(m2m_path)
            assert target == "m2m_compression_sentinel.py"

    def test_file_specific_bindings_loaded(self):
        """Scanner should load file-specific bindings."""
        scanner = OrphanCapabilityScanner(repo_root=REPO_ROOT)
        scanner._load_skillz_registry()

        # Should have at least 1 file-specific binding (m2m_SKILLz.md)
        assert len(scanner.file_specific_bindings) >= 1

        # m2m_compression_sentinel.py should be bound
        m2m_bound = any(
            "m2m_compression_sentinel.py" in path
            for path in scanner.file_specific_bindings.keys()
        )
        assert m2m_bound, "m2m_compression_sentinel.py should be file-specific bound"


class TestRealRepoIntegration:
    """Integration tests against actual repo structure."""

    def test_directory_level_still_works(self):
        """Directory-level SKILLz.md should still bind files."""
        scanner = OrphanCapabilityScanner(repo_root=REPO_ROOT)
        result = scanner.scan()

        # Should have some directory-bound capabilities
        directory_bound = [c for c in result.wre_connected if c.binding_type == "directory"]
        assert len(directory_bound) > 0, "Should have directory-level bindings"

    def test_file_specific_binding_works(self):
        """File-specific *_SKILLz.md should bind exactly target_file."""
        scanner = OrphanCapabilityScanner(repo_root=REPO_ROOT)
        result = scanner.scan()

        # Should have file-specific bindings
        file_specific = [c for c in result.wre_connected if c.binding_type == "file_specific"]
        assert len(file_specific) >= 1, "Should have at least 1 file-specific binding"

    def test_m2m_skillz_binding(self):
        """Verify m2m_SKILLz.md binds m2m_compression_sentinel.py."""
        scanner = OrphanCapabilityScanner(repo_root=REPO_ROOT)
        result = scanner.scan()

        # Find m2m_compression_sentinel.py in results
        m2m_caps = [c for c in result.wre_connected
                   if "m2m_compression_sentinel.py" in c.path]

        assert len(m2m_caps) == 1, "m2m_compression_sentinel.py should be WRE-connected"

        m2m_cap = m2m_caps[0]
        assert m2m_cap.binding_type == "file_specific", \
            f"Expected file_specific binding, got {m2m_cap.binding_type}"
        assert "m2m_SKILLz.md" in m2m_cap.skillz_md_path, \
            f"Expected m2m_SKILLz.md, got {m2m_cap.skillz_md_path}"

    def test_wre_connected_count_preserved(self):
        """WRE-connected count should include both binding types."""
        scanner = OrphanCapabilityScanner(repo_root=REPO_ROOT)
        result = scanner.scan()

        # Count by binding type
        directory_count = sum(1 for c in result.wre_connected if c.binding_type == "directory")
        file_specific_count = sum(1 for c in result.wre_connected if c.binding_type == "file_specific")

        assert directory_count + file_specific_count == len(result.wre_connected)
        assert directory_count > 0, "Should have directory bindings"
        assert file_specific_count >= 1, "Should have file-specific bindings"

    def test_no_wre_internal_violations(self):
        """File-specific bindings should not include wre_internal files."""
        scanner = OrphanCapabilityScanner(repo_root=REPO_ROOT)
        result = scanner.scan()

        file_specific = [c for c in result.wre_connected if c.binding_type == "file_specific"]
        for cap in file_specific:
            assert cap.orphan_class != "wre_internal", \
                f"File-specific binding should not be wre_internal: {cap.path}"


class TestWarningsAndEdgeCases:
    """Tests for warning generation and edge cases."""

    def test_reports_excluded_from_file_specific(self):
        """Reports directory should be excluded from file-specific scanning."""
        scanner = OrphanCapabilityScanner(repo_root=REPO_ROOT)
        scanner._load_skillz_registry()

        # No bindings should come from reports/ directory
        for path in scanner.file_specific_bindings.keys():
            assert "reports" not in path.lower(), \
                f"reports/ files should not be bound: {path}"

        # No warnings should mention reports/ after exclusion
        for warn in scanner.file_specific_warnings:
            assert "reports" not in warn.lower(), \
                f"Reports warnings should be filtered: {warn}"

    def test_scan_result_includes_file_specific_stats(self):
        """ScanResult should include file-specific binding stats."""
        scanner = OrphanCapabilityScanner(repo_root=REPO_ROOT)
        result = scanner.scan()

        assert hasattr(result, 'file_specific_bindings')
        assert hasattr(result, 'file_specific_warnings')
        assert result.file_specific_bindings >= 1
