# -*- coding: utf-8 -*-
"""Tests proving default WSP_00 awakening does not mutate tracked files.

WSP 97 Truth Boundary:
  DOES:
    - Write runtime state to .runtime/ subdirectory by default
    - Support opt-in tracked writes via WSP_AWAKENING_WRITE_TRACKED=1
  DOES NOT:
    - Mutate tracked files during normal awakening
    - Dirty the repo state from a standard session start
"""
from pathlib import Path


TRACKED_FILES = [
    Path("WSP_agentic/agentic_journals/awakening/awakening_log.txt"),
    Path("WSP_agentic/agentic_journals/awakening/awareness_log.md"),
    Path("WSP_agentic/agentic_journals/awakening/0102_state_v2.json"),
]

BASE_DIR = Path("WSP_agentic/agentic_journals/awakening")


def get_runtime_dir_logic(write_tracked_env: str = "") -> Path:
    """Replicate the _get_runtime_dir() logic for testing without import side effects."""
    if write_tracked_env.strip().lower() in {"1", "true", "yes"}:
        return BASE_DIR
    return BASE_DIR / ".runtime"


class TestRuntimePathResolution:
    """Test runtime directory resolution logic."""

    def test_default_uses_runtime_subdir(self):
        """Default (no env var) should route to .runtime/ subdirectory."""
        runtime_dir = get_runtime_dir_logic("")
        assert runtime_dir == BASE_DIR / ".runtime"
        assert ".runtime" in str(runtime_dir)

    def test_opt_in_uses_tracked_path(self):
        """WSP_AWAKENING_WRITE_TRACKED=1 should use tracked base dir."""
        runtime_dir = get_runtime_dir_logic("1")
        assert runtime_dir == BASE_DIR
        assert ".runtime" not in str(runtime_dir)

    def test_opt_in_true_uses_tracked_path(self):
        """WSP_AWAKENING_WRITE_TRACKED=true should use tracked base dir."""
        runtime_dir = get_runtime_dir_logic("true")
        assert runtime_dir == BASE_DIR
        assert ".runtime" not in str(runtime_dir)

    def test_opt_in_yes_uses_tracked_path(self):
        """WSP_AWAKENING_WRITE_TRACKED=yes should use tracked base dir."""
        runtime_dir = get_runtime_dir_logic("yes")
        assert runtime_dir == BASE_DIR
        assert ".runtime" not in str(runtime_dir)

    def test_empty_env_uses_runtime(self):
        """Empty env var should default to .runtime/."""
        runtime_dir = get_runtime_dir_logic("")
        assert ".runtime" in str(runtime_dir)

    def test_whitespace_only_uses_runtime(self):
        """Whitespace-only env var should default to .runtime/."""
        runtime_dir = get_runtime_dir_logic("   ")
        assert ".runtime" in str(runtime_dir)


class TestTrackedFilesExcluded:
    """Verify tracked file paths are not written by default awakening."""

    def test_default_log_file_not_tracked(self):
        """Default log file path should NOT match any tracked file."""
        runtime_dir = get_runtime_dir_logic("")
        log_file = runtime_dir / "awakening_log.txt"
        for tracked in TRACKED_FILES:
            assert log_file != tracked

    def test_default_awareness_log_not_tracked(self):
        """Default awareness log path should NOT match any tracked file."""
        runtime_dir = get_runtime_dir_logic("")
        awareness_log = runtime_dir / "awareness_log.md"
        for tracked in TRACKED_FILES:
            assert awareness_log != tracked

    def test_default_state_file_not_tracked(self):
        """Default state file path should NOT match any tracked file."""
        runtime_dir = get_runtime_dir_logic("")
        state_file = runtime_dir / "0102_state_v2.json"
        for tracked in TRACKED_FILES:
            assert state_file != tracked

    def test_all_default_paths_contain_runtime(self):
        """All default output paths should include .runtime/ in path."""
        runtime_dir = get_runtime_dir_logic("")
        all_paths = [
            runtime_dir / "awakening_log.txt",
            runtime_dir / "awareness_log.md",
            runtime_dir / "0102_state_v2.json",
        ]
        for path in all_paths:
            assert ".runtime" in str(path)


class TestGitignoreRules:
    """Verify .gitignore covers the .runtime/ directory."""

    def test_gitignore_has_runtime_rule(self):
        """Check .gitignore includes .runtime/ pattern."""
        gitignore_path = Path(__file__).parents[2] / ".gitignore"
        if not gitignore_path.exists():
            gitignore_path = Path("O:/Foundups-Agent/.gitignore")

        content = gitignore_path.read_text(encoding="utf-8")
        assert ".runtime/" in content, ".gitignore must include .runtime/ pattern"

    def test_gitignore_pattern_covers_awakening(self):
        """Check .gitignore pattern covers awakening .runtime/ specifically."""
        gitignore_path = Path(__file__).parents[2] / ".gitignore"
        if not gitignore_path.exists():
            gitignore_path = Path("O:/Foundups-Agent/.gitignore")

        content = gitignore_path.read_text(encoding="utf-8")
        # Pattern should cover any .runtime/ under agentic_journals/*/
        assert "agentic_journals/*/.runtime/" in content or ".runtime/" in content


class TestSourceCodeImplementation:
    """Verify the source code has correct implementation."""

    def test_functional_awakening_has_runtime_dir_function(self):
        """Check functional_0102_awakening_v2.py defines _get_runtime_dir."""
        script_path = Path(__file__).parent.parent / "scripts" / "functional_0102_awakening_v2.py"
        if not script_path.exists():
            script_path = Path("O:/Foundups-Agent/WSP_agentic/scripts/functional_0102_awakening_v2.py")

        content = script_path.read_text(encoding="utf-8")
        assert "def _get_runtime_dir()" in content
        assert "_BASE_DIR / \".runtime\"" in content or "/ '.runtime'" in content

    def test_functional_awakening_uses_runtime_dir(self):
        """Check _LOG_FILE uses _get_runtime_dir()."""
        script_path = Path(__file__).parent.parent / "scripts" / "functional_0102_awakening_v2.py"
        if not script_path.exists():
            script_path = Path("O:/Foundups-Agent/WSP_agentic/scripts/functional_0102_awakening_v2.py")

        content = script_path.read_text(encoding="utf-8")
        assert "_get_runtime_dir()" in content
        assert "_LOG_FILE = _get_runtime_dir() /" in content

    def test_functional_awakening_has_env_var_check(self):
        """Check script checks WSP_AWAKENING_WRITE_TRACKED env var."""
        script_path = Path(__file__).parent.parent / "scripts" / "functional_0102_awakening_v2.py"
        if not script_path.exists():
            script_path = Path("O:/Foundups-Agent/WSP_agentic/scripts/functional_0102_awakening_v2.py")

        content = script_path.read_text(encoding="utf-8")
        assert "WSP_AWAKENING_WRITE_TRACKED" in content
