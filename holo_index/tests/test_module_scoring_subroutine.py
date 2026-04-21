# -*- coding: utf-8 -*-
"""
Tests for module_scoring_subroutine.py - Module Scoring Tests

Tests run in HOLO_SKIP_MODEL=1 mode.

WSP Compliance:
    WSP 5: Test Coverage
    WSP 15: Module Prioritization
    WSP 37: Module Scoring
"""
from pathlib import Path
from unittest.mock import MagicMock, patch
import tempfile

from holo_index.core.module_scoring_subroutine import ModuleScoringSubroutine


class TestModuleScoringSubroutineInit:
    """Tests for ModuleScoringSubroutine initialization"""

    def test_init_with_defaults(self):
        """Initializes with default project root"""
        subroutine = ModuleScoringSubroutine()
        assert subroutine.project_root is not None

    def test_init_with_custom_project_root(self):
        """Accepts custom project root"""
        custom_root = Path("/custom/path")
        subroutine = ModuleScoringSubroutine(project_root=custom_root)
        assert subroutine.project_root == custom_root

    def test_init_with_custom_scoring_file(self):
        """Accepts custom scoring file"""
        custom_file = Path("/custom/modules_to_score.yaml")
        subroutine = ModuleScoringSubroutine(scoring_file=custom_file)
        assert subroutine.scoring_file == custom_file


class TestResolveScoringFile:
    """Tests for _resolve_scoring_file method"""

    def test_resolve_returns_none_when_no_file_exists(self):
        """Returns None when no scoring file exists"""
        with tempfile.TemporaryDirectory() as tmpdir:
            subroutine = ModuleScoringSubroutine(project_root=Path(tmpdir))
            subroutine.scoring_file = subroutine._resolve_scoring_file()
            assert subroutine.scoring_file is None

    def test_resolve_finds_root_level_file(self):
        """Finds modules_to_score.yaml at project root"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            scoring_file = root / "modules_to_score.yaml"
            scoring_file.write_text("modules: []")

            subroutine = ModuleScoringSubroutine(project_root=root)
            subroutine.scoring_file = subroutine._resolve_scoring_file()

            assert subroutine.scoring_file == scoring_file

    def test_resolve_finds_modules_development_file(self):
        """Finds modules_to_score.yaml in modules/development"""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            modules_dev = root / "modules" / "development"
            modules_dev.mkdir(parents=True)
            scoring_file = modules_dev / "modules_to_score.yaml"
            scoring_file.write_text("modules: []")

            subroutine = ModuleScoringSubroutine(project_root=root)
            subroutine.scoring_file = subroutine._resolve_scoring_file()

            assert subroutine.scoring_file == scoring_file


class TestNormalize:
    """Tests for _normalize method"""

    def test_normalize_replaces_backslashes(self):
        """Replaces backslashes with forward slashes"""
        subroutine = ModuleScoringSubroutine()
        result = subroutine._normalize("path\\to\\module")
        assert result == "path/to/module"

    def test_normalize_strips_whitespace(self):
        """Strips leading and trailing whitespace"""
        subroutine = ModuleScoringSubroutine()
        result = subroutine._normalize("  path/to/module  ")
        assert result == "path/to/module"

    def test_normalize_lowercases(self):
        """Converts to lowercase"""
        subroutine = ModuleScoringSubroutine()
        result = subroutine._normalize("PATH/To/MODULE")
        assert result == "path/to/module"


class TestMatchTarget:
    """Tests for _match_target method"""

    def test_match_by_exact_name(self):
        """Matches entry by exact name"""
        subroutine = ModuleScoringSubroutine()
        entries = [
            {"name": "my_module", "path": "/some/path"},
            {"name": "other_module", "path": "/other/path"},
        ]

        result = subroutine._match_target("my_module", entries)

        assert result is not None
        assert result["name"] == "my_module"

    def test_match_by_exact_path(self):
        """Matches entry by exact path"""
        subroutine = ModuleScoringSubroutine()
        entries = [
            {"name": "my_module", "path": "modules/test/my_module"},
        ]

        result = subroutine._match_target("modules/test/my_module", entries)

        assert result is not None
        assert result["name"] == "my_module"

    def test_match_by_path_suffix(self):
        """Matches entry by path suffix"""
        subroutine = ModuleScoringSubroutine()
        entries = [
            {"name": "my_module", "path": "modules/ai_intelligence/my_module"},
        ]

        result = subroutine._match_target("my_module", entries)

        assert result is not None
        assert result["path"] == "modules/ai_intelligence/my_module"

    def test_match_returns_none_when_not_found(self):
        """Returns None when no match found"""
        subroutine = ModuleScoringSubroutine()
        entries = [
            {"name": "other_module", "path": "/other/path"},
        ]

        result = subroutine._match_target("nonexistent", entries)

        assert result is None

    def test_match_handles_empty_entries(self):
        """Handles empty entries list"""
        subroutine = ModuleScoringSubroutine()
        result = subroutine._match_target("module", [])
        assert result is None

    def test_match_handles_missing_fields(self):
        """Handles entries with missing name/path fields"""
        subroutine = ModuleScoringSubroutine()
        entries = [
            {"name": "module_a"},  # No path
            {"path": "some/path"},  # No name
        ]

        # Should still work with partial data
        result = subroutine._match_target("module_a", entries)
        assert result is not None


class TestLoadScoringMetadata:
    """Tests for _load_scoring_metadata method"""

    def test_returns_empty_dict_when_no_file(self):
        """Returns empty dict when scoring file is None"""
        subroutine = ModuleScoringSubroutine()
        subroutine.scoring_file = None
        result = subroutine._load_scoring_metadata()
        assert result == {}

    def test_returns_empty_dict_when_file_not_exists(self):
        """Returns empty dict when file doesn't exist"""
        subroutine = ModuleScoringSubroutine()
        subroutine.scoring_file = Path("/nonexistent/file.yaml")
        result = subroutine._load_scoring_metadata()
        assert result == {}

    def test_loads_metadata_from_valid_yaml(self):
        """Loads metadata from valid YAML file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_file = Path(tmpdir) / "modules_to_score.yaml"
            yaml_file.write_text("""
modules:
  - name: test_module
    path: modules/test/test_module
    active: true
""", encoding="utf-8")

            subroutine = ModuleScoringSubroutine()
            subroutine.scoring_file = yaml_file
            result = subroutine._load_scoring_metadata()

            assert "test_module" in result
            assert result["test_module"]["active"] is True

    def test_handles_yaml_parse_error(self):
        """Returns empty dict on YAML parse error"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_file = Path(tmpdir) / "invalid.yaml"
            yaml_file.write_text("invalid: yaml: content: [", encoding="utf-8")

            subroutine = ModuleScoringSubroutine()
            subroutine.scoring_file = yaml_file
            result = subroutine._load_scoring_metadata()

            assert result == {}


class TestScore:
    """Tests for score method"""

    def test_returns_error_when_engine_unavailable(self):
        """Returns error when WSP37ScoringEngine is None"""
        with patch("holo_index.core.module_scoring_subroutine.WSP37ScoringEngine", None):
            subroutine = ModuleScoringSubroutine()
            result = subroutine.score()
            assert "error" in result
            assert "unavailable" in result["error"]

    def test_returns_error_when_no_scoring_file(self):
        """Returns error when scoring file not found"""
        # Create mock engine so we get past first check
        mock_engine_class = MagicMock()
        with patch("holo_index.core.module_scoring_subroutine.WSP37ScoringEngine", mock_engine_class):
            subroutine = ModuleScoringSubroutine()
            subroutine.scoring_file = None
            result = subroutine.score()
            assert "error" in result
            assert "not found" in result["error"]
