#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for WRE Skills Loader - Skills 2.0 Hygiene

WSP Compliance: WSP 5 (Test Coverage), WSP 96 (WRE Skills)
"""

import pytest
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
from datetime import datetime, timezone, timedelta

from modules.infrastructure.wre_core.skillz.wre_skills_loader import (
    WRESkillsLoader,
    SkillMetadata,
    SkillHygieneStatus,
)


class TestSkillHygieneStatus:
    """Test SkillHygieneStatus dataclass."""

    def test_healthy_skill(self):
        """Healthy skill has is_healthy=True and no issues."""
        status = SkillHygieneStatus(
            skill_name="test_skill",
            is_healthy=True,
        )
        assert status.is_healthy is True
        assert status.is_retired is False
        assert status.issues == []

    def test_retired_skill(self):
        """Retired skill has is_healthy=False."""
        status = SkillHygieneStatus(
            skill_name="old_skill",
            is_healthy=False,
            is_retired=True,
            retirement_date="2020-01-01",
            issues=["Skill retired on 2020-01-01"],
        )
        assert status.is_healthy is False
        assert status.is_retired is True
        assert "retired" in status.issues[0].lower()


class TestWRESkillsLoaderHygiene:
    """Test WRE Skills Loader hygiene functionality."""

    @pytest.fixture
    def tmp_skill_dir(self, tmp_path):
        """Create a temporary skill directory with test skills."""
        skills_dir = tmp_path / "skillz"
        skills_dir.mkdir()

        # Create a valid skill
        valid_skill_dir = skills_dir / "valid_skill"
        valid_skill_dir.mkdir()
        (valid_skill_dir / "SKILLz.md").write_text("""---
name: valid_skill
description: A valid test skill
version: 1.0
agents: [qwen]
primary_agent: qwen
intent_type: DECISION
promotion_state: production
category: workflow
evals:
  - name: test_eval
    input: "test"
    expected: "result"
retirement_date: null
---
# Valid Skill

This is a valid skill.
""")

        # Create a retired skill
        retired_skill_dir = skills_dir / "retired_skill"
        retired_skill_dir.mkdir()
        (retired_skill_dir / "SKILLz.md").write_text("""---
name: retired_skill
description: A retired skill
version: 1.0
agents: [qwen]
primary_agent: qwen
intent_type: DECISION
promotion_state: production
category: workflow
evals: []
retirement_date: "2020-01-01"
---
# Retired Skill

This skill is retired.
""")

        # Create a skill with invalid category
        invalid_cat_dir = skills_dir / "invalid_category_skill"
        invalid_cat_dir.mkdir()
        (invalid_cat_dir / "SKILLz.md").write_text("""---
name: invalid_category_skill
description: A skill with invalid category
version: 1.0
agents: [qwen]
primary_agent: qwen
intent_type: DECISION
promotion_state: production
category: bad_category
evals: []
retirement_date: null
---
# Invalid Category Skill
""")

        # Create a skill without category
        no_cat_dir = skills_dir / "no_category_skill"
        no_cat_dir.mkdir()
        (no_cat_dir / "SKILLz.md").write_text("""---
name: no_category_skill
description: A skill without category
version: 1.0
agents: [qwen]
primary_agent: qwen
intent_type: DECISION
promotion_state: production
evals: []
retirement_date: null
---
# No Category Skill
""")

        return tmp_path

    @pytest.fixture
    def loader_with_registry(self, tmp_skill_dir):
        """Create loader with registry pointing to test skills."""
        registry = {
            "version": "2.0",
            "skills": {
                "valid_skill": {
                    "location": "skillz/valid_skill",
                    "primary_agent": "qwen",
                    "promotion_state": "production",
                },
                "retired_skill": {
                    "location": "skillz/retired_skill",
                    "primary_agent": "qwen",
                    "promotion_state": "production",
                },
                "invalid_category_skill": {
                    "location": "skillz/invalid_category_skill",
                    "primary_agent": "qwen",
                    "promotion_state": "production",
                },
                "no_category_skill": {
                    "location": "skillz/no_category_skill",
                    "primary_agent": "qwen",
                    "promotion_state": "production",
                },
            }
        }

        registry_path = tmp_skill_dir / "skills_registry_v2.json"
        registry_path.write_text(json.dumps(registry))

        return WRESkillsLoader(
            registry_path=registry_path,
            repo_root=tmp_skill_dir,
        )

    def test_check_skill_hygiene_valid(self, loader_with_registry):
        """Valid skill passes hygiene check."""
        status = loader_with_registry.check_skill_hygiene("valid_skill")

        assert status.is_healthy is True
        assert status.is_retired is False
        assert status.missing_category is False
        assert status.category == "workflow"

    def test_check_skill_hygiene_retired(self, loader_with_registry):
        """Retired skill fails hygiene check."""
        status = loader_with_registry.check_skill_hygiene("retired_skill")

        assert status.is_healthy is False
        assert status.is_retired is True
        assert status.retirement_date == "2020-01-01"
        assert any("retired" in issue.lower() for issue in status.issues)

    def test_check_skill_hygiene_invalid_category(self, loader_with_registry):
        """Skill with invalid category fails hygiene check."""
        status = loader_with_registry.check_skill_hygiene("invalid_category_skill")

        assert status.is_healthy is False
        assert status.missing_category is True
        assert any("category" in issue.lower() for issue in status.issues)

    def test_check_skill_hygiene_missing_category(self, loader_with_registry):
        """Skill without category fails hygiene check."""
        status = loader_with_registry.check_skill_hygiene("no_category_skill")

        assert status.is_healthy is False
        assert status.missing_category is True

    def test_load_skill_blocks_retired(self, loader_with_registry):
        """load_skill raises error for retired skills."""
        with pytest.raises(ValueError) as exc_info:
            loader_with_registry.load_skill("retired_skill", "qwen", enforce_hygiene=True)

        assert "retired" in str(exc_info.value).lower()

    def test_load_skill_bypass_hygiene(self, loader_with_registry):
        """load_skill with enforce_hygiene=False allows retired skills."""
        # Should not raise
        content = loader_with_registry.load_skill("retired_skill", "qwen", enforce_hygiene=False)
        assert "Retired Skill" in content

    def test_load_skill_valid_passes(self, loader_with_registry):
        """load_skill works for valid skills."""
        content = loader_with_registry.load_skill("valid_skill", "qwen", enforce_hygiene=True)
        assert "Valid Skill" in content

    def test_list_healthy_skills(self, loader_with_registry):
        """list_healthy_skills excludes retired and invalid category skills."""
        healthy = loader_with_registry.list_healthy_skills()

        # Only valid_skill should pass - retired and invalid category excluded
        assert "valid_skill" in healthy
        assert "retired_skill" not in healthy
        assert "invalid_category_skill" not in healthy
        assert "no_category_skill" not in healthy

    def test_discover_healthy_skills(self, loader_with_registry):
        """discover_healthy_skills returns only healthy skills."""
        healthy = loader_with_registry.discover_healthy_skills()

        names = [s.name for s in healthy]
        assert "valid_skill" in names
        assert "retired_skill" not in names
        assert "invalid_category_skill" not in names
        assert "no_category_skill" not in names  # Missing category excluded

    def test_discover_healthy_skills_excludes_no_category(self, loader_with_registry):
        """Regression: skills with missing category excluded from discover_healthy_skills."""
        # This tests the gap where missing category was normalized to "workflow"
        # before the hygiene filter, causing no_category_skill to pass
        healthy = loader_with_registry.discover_healthy_skills()
        names = [s.name for s in healthy]

        # no_category_skill has no category field - should be excluded
        assert "no_category_skill" not in names

        # But check_skill_hygiene should also flag it as unhealthy
        status = loader_with_registry.check_skill_hygiene("no_category_skill")
        assert status.is_healthy is False
        assert status.missing_category is True


class TestCheckoutLocalSkillResolution:
    """Skill execution paths must stay inside the loader's exact checkout."""

    @staticmethod
    def _loader(tmp_path, skill_name, location):
        registry_path = tmp_path / "skills_registry_v2.json"
        registry_path.write_text(
            json.dumps(
                {
                    "version": "2.0",
                    "skills": {
                        skill_name: {
                            "location": location,
                            "primary_agent": "qwen",
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        return WRESkillsLoader(
            registry_path=registry_path,
            repo_root=tmp_path,
        )

    def test_default_repo_root_is_loader_checkout(self):
        loader = WRESkillsLoader()

        assert loader.repo_root == Path(__file__).resolve().parents[4]

    def test_checked_in_registry_locations_are_portable(self):
        loader = WRESkillsLoader()

        for skill_info in loader.registry["skills"].values():
            location = skill_info["location"]
            assert not PureWindowsPath(location).drive
            assert not PureWindowsPath(location).is_absolute()
            assert not PurePosixPath(location).is_absolute()
            assert ".." not in PurePosixPath(location).parts

    def test_relative_location_resolves_inside_injected_checkout(self, tmp_path):
        skill_dir = tmp_path / "skillz" / "local_skill"
        skill_dir.mkdir(parents=True)
        expected = skill_dir / "SKILLz.md"
        expected.write_text("# Local skill\n", encoding="utf-8")
        loader = self._loader(tmp_path, "local_skill", "skillz/local_skill")

        assert loader.resolve_skill_file("local_skill") == expected.resolve()

    def test_absolute_location_cannot_cross_into_another_checkout(self, tmp_path):
        checkout = tmp_path / "checkout"
        checkout.mkdir()
        foreign = tmp_path / "foreign" / "skillz" / "foreign_skill"
        foreign.mkdir(parents=True)
        (foreign / "SKILLz.md").write_text("# Foreign skill\n", encoding="utf-8")
        loader = self._loader(
            checkout,
            "foreign_skill",
            str(foreign),
        )

        with pytest.raises(ValueError, match="checkout-relative"):
            loader.resolve_skill_file("foreign_skill")

    def test_parent_traversal_location_fails_closed(self, tmp_path):
        loader = self._loader(
            tmp_path,
            "escaping_skill",
            "../foreign/escaping_skill",
        )

        with pytest.raises(ValueError, match="checkout-relative"):
            loader.resolve_skill_file("escaping_skill")

    @pytest.mark.parametrize(
        "location",
        [
            "C:foreign/skill",
            "C:/foreign/skill",
            r"\\server\share\skill",
            r"\\?\C:\foreign\skill",
            r"\rooted\skill",
            "/foreign/skill",
        ],
    )
    def test_windows_and_posix_absolute_forms_fail_closed(
        self,
        tmp_path,
        location,
    ):
        loader = self._loader(tmp_path, "escaping_skill", location)

        with pytest.raises(ValueError, match="checkout-relative"):
            loader.resolve_skill_file("escaping_skill")

    def test_missing_registered_location_cannot_use_same_name_fallback(
        self,
        tmp_path,
    ):
        decoy = (
            tmp_path
            / "modules"
            / "test_domain"
            / "test_module"
            / "skillz"
            / "local_skill"
        )
        decoy.mkdir(parents=True)
        (decoy / "SKILLz.md").write_text("# Decoy\n", encoding="utf-8")
        loader = self._loader(
            tmp_path,
            "local_skill",
            "registered/missing/local_skill",
        )

        with pytest.raises(FileNotFoundError) as exc_info:
            loader.resolve_skill_file("local_skill")

        assert "registered" in str(exc_info.value)
        assert "test_domain" not in str(exc_info.value)

    def test_symlinked_location_cannot_escape_checkout(self, tmp_path):
        outside = tmp_path / "outside"
        outside.mkdir()
        checkout = tmp_path / "checkout"
        checkout.mkdir()
        link = checkout / "linked_skill"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError:
            pytest.skip("directory symlinks are unavailable on this host")
        loader = self._loader(checkout, "linked_skill", "linked_skill")

        with pytest.raises(ValueError, match="escapes"):
            loader.resolve_skill_file("linked_skill")

    def test_production_skill_resolves_inside_current_checkout(self):
        loader = WRESkillsLoader()

        resolved = loader.resolve_skill_file("qwen_gitpush")

        resolved.relative_to(loader.repo_root)
        assert resolved.name == "SKILLz.md"


class TestIsRetired:
    """Test _is_retired helper method."""

    @pytest.fixture
    def loader(self):
        """Create minimal loader for testing."""
        # Create with a non-existent registry - it will return empty registry
        return WRESkillsLoader(registry_path=Path("/nonexistent/path"))

    def test_null_values(self, loader):
        """Null/empty values are not retired."""
        assert loader._is_retired(None) is False
        assert loader._is_retired("null") is False
        assert loader._is_retired("") is False

    def test_future_date(self, loader):
        """Future date is not retired."""
        future = (datetime.now(timezone.utc) + timedelta(days=365)).strftime("%Y-%m-%d")
        assert loader._is_retired(future) is False

    def test_past_date(self, loader):
        """Past date is retired."""
        past = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%d")
        assert loader._is_retired(past) is True

    def test_iso_datetime_format(self, loader):
        """ISO datetime format is handled."""
        past = "2020-01-01T00:00:00+00:00"
        assert loader._is_retired(past) is True

        future = "2099-12-31T23:59:59+00:00"
        assert loader._is_retired(future) is False

    def test_invalid_format(self, loader):
        """Invalid format returns False (safe default)."""
        assert loader._is_retired("not-a-date") is False
        assert loader._is_retired(12345) is False


class TestSkillMetadataHygieneFields:
    """Test Skills 2.0 fields in SkillMetadata."""

    def test_default_values(self):
        """Default hygiene field values."""
        metadata = SkillMetadata(
            name="test",
            description="test",
            primary_agent="qwen",
            intent_type="DECISION",
            promotion_state="production",
            location=Path("test"),
            pattern_fidelity_threshold=0.90,
        )

        assert metadata.category == "workflow"
        assert metadata.retirement_date == ""
        assert metadata.has_evals is False

    def test_explicit_values(self):
        """Explicit hygiene field values."""
        metadata = SkillMetadata(
            name="test",
            description="test",
            primary_agent="qwen",
            intent_type="DECISION",
            promotion_state="production",
            location=Path("test"),
            pattern_fidelity_threshold=0.90,
            category="capability-uplift",
            retirement_date="2099-01-01",
            has_evals=True,
        )

        assert metadata.category == "capability-uplift"
        assert metadata.retirement_date == "2099-01-01"
        assert metadata.has_evals is True


class TestSelectorUsesHealthySkills:
    """Regression: SkillSelector uses healthy skills, not full registry."""

    def test_selector_uses_list_healthy_skills(self):
        """Selector prefers list_healthy_skills over list_skills."""
        from modules.infrastructure.wre_core.src.skill_selector import SkillSelector

        # Mock loader that tracks which method was called
        class MockLoader:
            def __init__(self):
                self.called_method = None

            def list_healthy_skills(self):
                self.called_method = "list_healthy_skills"
                return ["healthy_gitpush"]

            def list_skills(self):
                self.called_method = "list_skills"
                return ["healthy_gitpush", "retired_gitpush"]

        mock_loader = MockLoader()
        selector = SkillSelector(skills_loader=mock_loader)

        # Call find_candidates_for_intent
        candidates = selector.find_candidates_for_intent("git push")

        # Should have called list_healthy_skills, not list_skills
        assert mock_loader.called_method == "list_healthy_skills"

    def test_selector_excludes_retired_skills(self):
        """Selector does not return retired skills in candidates."""
        from modules.infrastructure.wre_core.src.skill_selector import SkillSelector

        class MockLoader:
            def list_healthy_skills(self):
                # Only returns healthy skills
                return ["healthy_gitpush"]

            @property
            def registry(self):
                return {
                    "skills": {
                        "healthy_gitpush": {"description": "git push automation"},
                        "retired_gitpush": {"description": "old git push skill"},
                    }
                }

        mock_loader = MockLoader()
        selector = SkillSelector(skills_loader=mock_loader)

        candidates = selector.find_candidates_for_intent("git push")

        # Only healthy skill should be in candidates
        assert "healthy_gitpush" in candidates
        assert "retired_gitpush" not in candidates


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
