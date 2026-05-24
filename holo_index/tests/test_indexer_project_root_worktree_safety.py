# -*- coding: utf-8 -*-
"""Regression tests for HOLOINDEX_INDEXER_PROJECT_ROOT_WORKTREE_SAFETY_PHASE1.

These tests verify the fix for the worktree path filter bug where running
--index-docs from a worktree under .claude/worktrees/ would reject ALL files
because the absolute path contained .claude (a dot-prefixed component).

The fix: check dot-prefix against the relative path from base, not absolute.

Test matrix:
- Test A: Worktree path NOT rejected (relative path has no dotfiles)
- Test B: Main repo path NOT rejected (relative path has no dotfiles)
- Test C: Dotfile INSIDE docs tree IS rejected (.draft/foo.md)
- Test D: Hidden file IS rejected (.DS_Store)
- Test E: Path outside base IS rejected (fail-closed)

All tests use synthetic paths (tmp_path or in-memory). No Chroma writes.
"""

from pathlib import Path
import pytest


class TestWorktreeSafety:
    """Regression tests for worktree path filter safety."""

    def test_a_worktree_path_not_rejected(self, tmp_path: Path):
        """Test A: File in worktree is NOT rejected when relative path is clean.

        Simulates: <repo>/.claude/worktrees/<slice>/docs/audits/architecture/example.md
        Base: <repo>/.claude/worktrees/<slice>/docs
        Expected: NOT rejected (relative path audits/architecture/example.md has no dotfiles)
        """
        from holo_index.core.indexing_engine import _has_dotfile_in_relative_path

        # Simulate worktree structure
        worktree_root = tmp_path / ".claude" / "worktrees" / "test-slice"
        docs_base = worktree_root / "docs"
        target_file = docs_base / "audits" / "architecture" / "example.md"

        # Create the path structure
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.touch()

        # The fix should NOT reject this file
        result = _has_dotfile_in_relative_path(target_file, docs_base)
        assert result is False, (
            f"Worktree file should NOT be rejected. "
            f"File: {target_file}, Base: {docs_base}"
        )

    def test_b_main_repo_path_not_rejected(self, tmp_path: Path):
        """Test B: File in main repo is NOT rejected.

        Simulates: <repo>/docs/audits/architecture/example.md
        Base: <repo>/docs
        Expected: NOT rejected (relative path audits/architecture/example.md has no dotfiles)
        """
        from holo_index.core.indexing_engine import _has_dotfile_in_relative_path

        # Simulate main repo structure
        docs_base = tmp_path / "docs"
        target_file = docs_base / "audits" / "architecture" / "example.md"

        # Create the path structure
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.touch()

        # Should NOT be rejected
        result = _has_dotfile_in_relative_path(target_file, docs_base)
        assert result is False, (
            f"Main repo file should NOT be rejected. "
            f"File: {target_file}, Base: {docs_base}"
        )

    def test_c_dotfile_inside_docs_tree_rejected(self, tmp_path: Path):
        """Test C: Dotfile INSIDE docs tree IS rejected.

        Simulates: <base>/.draft/foo.md
        Base: <base>
        Expected: REJECTED (relative path .draft/foo.md has dotfile component)

        This is a regression guard: the intent of skipping dotfiles inside
        the docs tree must still work.
        """
        from holo_index.core.indexing_engine import _has_dotfile_in_relative_path

        # Simulate dotfile directory inside docs tree
        docs_base = tmp_path / "docs"
        target_file = docs_base / ".draft" / "foo.md"

        # Create the path structure
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.touch()

        # MUST be rejected (dotfile inside docs tree)
        result = _has_dotfile_in_relative_path(target_file, docs_base)
        assert result is True, (
            f"Dotfile inside docs tree should be REJECTED. "
            f"File: {target_file}, Base: {docs_base}"
        )

    def test_d_hidden_file_rejected(self, tmp_path: Path):
        """Test D: Hidden file (.DS_Store) IS rejected.

        Simulates: <base>/docs/.DS_Store
        Base: <base>/docs
        Expected: REJECTED (relative path .DS_Store is a dotfile)

        This is a regression guard: hidden files must still be skipped.
        """
        from holo_index.core.indexing_engine import _has_dotfile_in_relative_path

        # Simulate hidden file in docs tree
        docs_base = tmp_path / "docs"
        target_file = docs_base / ".DS_Store"

        # Create the path structure
        docs_base.mkdir(parents=True, exist_ok=True)
        target_file.touch()

        # MUST be rejected (hidden file)
        result = _has_dotfile_in_relative_path(target_file, docs_base)
        assert result is True, (
            f"Hidden file should be REJECTED. "
            f"File: {target_file}, Base: {docs_base}"
        )

    def test_e_path_outside_base_rejected(self, tmp_path: Path):
        """Test E: Path outside base IS rejected (fail-closed).

        Simulates: file_path not under base (ValueError from relative_to)
        Expected: REJECTED (fail-closed when relative_to fails)
        """
        from holo_index.core.indexing_engine import _has_dotfile_in_relative_path

        # Create two unrelated paths
        base = tmp_path / "docs"
        outside_file = tmp_path / "other" / "file.md"

        base.mkdir(parents=True, exist_ok=True)
        outside_file.parent.mkdir(parents=True, exist_ok=True)
        outside_file.touch()

        # MUST be rejected (outside base = fail-closed)
        result = _has_dotfile_in_relative_path(outside_file, base)
        assert result is True, (
            f"File outside base should be REJECTED (fail-closed). "
            f"File: {outside_file}, Base: {base}"
        )

    def test_nested_dotfile_directory_rejected(self, tmp_path: Path):
        """Nested dotfile directory inside docs tree IS rejected.

        Simulates: <base>/audits/.hidden/subdir/file.md
        Base: <base>
        Expected: REJECTED (relative path has .hidden component)
        """
        from holo_index.core.indexing_engine import _has_dotfile_in_relative_path

        docs_base = tmp_path / "docs"
        target_file = docs_base / "audits" / ".hidden" / "subdir" / "file.md"

        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.touch()

        result = _has_dotfile_in_relative_path(target_file, docs_base)
        assert result is True, (
            f"Nested dotfile directory should be REJECTED. "
            f"File: {target_file}, Base: {docs_base}"
        )

    def test_deep_worktree_path_not_rejected(self, tmp_path: Path):
        """Deep worktree path with clean relative path is NOT rejected.

        Simulates: <repo>/.claude/worktrees/very-long-slice-name/docs/a/b/c/d.md
        Base: <repo>/.claude/worktrees/very-long-slice-name/docs
        Expected: NOT rejected (relative path a/b/c/d.md has no dotfiles)
        """
        from holo_index.core.indexing_engine import _has_dotfile_in_relative_path

        worktree_root = tmp_path / ".claude" / "worktrees" / "very-long-slice-name"
        docs_base = worktree_root / "docs"
        target_file = docs_base / "a" / "b" / "c" / "d.md"

        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.touch()

        result = _has_dotfile_in_relative_path(target_file, docs_base)
        assert result is False, (
            f"Deep worktree file should NOT be rejected. "
            f"File: {target_file}, Base: {docs_base}"
        )
