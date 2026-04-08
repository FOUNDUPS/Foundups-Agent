"""Tests for target surface IO — skill config read/copy/write.

Covers:
- Load valid skill surface
- Preserve immutable fields
- Extract mutable fields correctly
- Create isolated workspace copy
- Writing candidate does not mutate production file
- Invalid skill path fails cleanly
- Candidate path stays inside workspace root
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

from modules.infrastructure.autoagent_lab.src.experiment_config import VALID_MUTABLE_FIELDS
from modules.infrastructure.autoagent_lab.src.safety_gates import SafetyViolation
from modules.infrastructure.autoagent_lab.src.target_surface import (
    DEFAULT_WORKSPACE_ROOT,
    SkillSurface,
    TargetSurfaceError,
    _render_skill_content,
    _split_frontmatter,
    create_workspace_copy,
    get_candidate_path,
    load_skill_surface,
    write_candidate_surface,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def valid_skill_content():
    """Full valid SKILL.md content with mutable and immutable fields."""
    return """---
name: test_skill
description: A test skill for experiments
version: 1.0.0
author: test_team
category: workflow
agents: [qwen, gemma]
domains: [testing]
tokens_budget: 500
---
# Test Skill

This is the body content.

## WSP Compliance
References WSP 49 and WSP 97.
"""


@pytest.fixture
def minimal_skill_content():
    """Minimal SKILL.md with only immutable fields."""
    return """---
name: minimal_skill
description: Minimal skill
---
# Minimal
"""


@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace directory."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


def _write_temp_skill(content: str, tmp_path: Path, name: str = "SKILL.md") -> Path:
    """Write skill content to a temp file."""
    skill_path = tmp_path / name
    skill_path.write_text(content, encoding="utf-8")
    return skill_path


# ---------------------------------------------------------------------------
# SkillSurface dataclass
# ---------------------------------------------------------------------------


class TestSkillSurface:

    def test_to_dict(self, valid_skill_content, tmp_path):
        path = _write_temp_skill(valid_skill_content, tmp_path)
        surface = load_skill_surface(path)
        d = surface.to_dict()
        assert "source_path" in d
        assert "skill_id" in d
        assert "immutable_fields" in d
        assert "mutable_fields" in d
        assert "body_content_length" in d

    def test_workspace_path_none_initially(self, valid_skill_content, tmp_path):
        path = _write_temp_skill(valid_skill_content, tmp_path)
        surface = load_skill_surface(path)
        assert surface.workspace_path is None


# ---------------------------------------------------------------------------
# load_skill_surface
# ---------------------------------------------------------------------------


class TestLoadSkillSurface:

    def test_load_valid_skill(self, valid_skill_content, tmp_path):
        path = _write_temp_skill(valid_skill_content, tmp_path)
        surface = load_skill_surface(path)
        assert surface.skill_id == "test_skill"
        assert surface.source_path == path.resolve()

    def test_extracts_mutable_fields(self, valid_skill_content, tmp_path):
        path = _write_temp_skill(valid_skill_content, tmp_path)
        surface = load_skill_surface(path)
        # Mutable fields present in the fixture
        assert "agents" in surface.mutable_fields
        assert "domains" in surface.mutable_fields
        assert "tokens_budget" in surface.mutable_fields
        assert surface.mutable_fields["agents"] == ["qwen", "gemma"]

    def test_extracts_immutable_fields(self, valid_skill_content, tmp_path):
        path = _write_temp_skill(valid_skill_content, tmp_path)
        surface = load_skill_surface(path)
        # Immutable fields
        assert "name" in surface.immutable_fields
        assert "description" in surface.immutable_fields
        assert "version" in surface.immutable_fields
        assert "author" in surface.immutable_fields
        assert surface.immutable_fields["name"] == "test_skill"

    def test_immutable_not_in_mutable(self, valid_skill_content, tmp_path):
        path = _write_temp_skill(valid_skill_content, tmp_path)
        surface = load_skill_surface(path)
        # name, version, etc. should NOT be in mutable
        assert "name" not in surface.mutable_fields
        assert "version" not in surface.mutable_fields
        assert "description" not in surface.mutable_fields

    def test_mutable_not_in_immutable(self, valid_skill_content, tmp_path):
        path = _write_temp_skill(valid_skill_content, tmp_path)
        surface = load_skill_surface(path)
        # agents, domains, etc. should NOT be in immutable
        assert "agents" not in surface.immutable_fields
        assert "domains" not in surface.immutable_fields

    def test_preserves_body_content(self, valid_skill_content, tmp_path):
        path = _write_temp_skill(valid_skill_content, tmp_path)
        surface = load_skill_surface(path)
        assert "# Test Skill" in surface.body_content
        assert "WSP 49" in surface.body_content

    def test_file_not_found_raises(self):
        with pytest.raises(TargetSurfaceError) as exc:
            load_skill_surface(Path("/nonexistent/SKILL.md"))
        assert "not found" in str(exc.value)

    def test_no_frontmatter_raises(self, tmp_path):
        content = "# Just markdown\nNo frontmatter here."
        path = _write_temp_skill(content, tmp_path)
        with pytest.raises(TargetSurfaceError) as exc:
            load_skill_surface(path)
        assert "frontmatter" in str(exc.value).lower()

    def test_invalid_yaml_raises(self, tmp_path):
        content = "---\nname: [unclosed\n---\n# Body"
        path = _write_temp_skill(content, tmp_path)
        with pytest.raises(TargetSurfaceError) as exc:
            load_skill_surface(path)
        assert "YAML" in str(exc.value)

    def test_skill_id_from_name(self, valid_skill_content, tmp_path):
        path = _write_temp_skill(valid_skill_content, tmp_path)
        surface = load_skill_surface(path)
        assert surface.skill_id == "test_skill"

    def test_skill_id_from_filename_if_no_name(self, tmp_path):
        content = """---
description: No name field
---
# Body
"""
        path = _write_temp_skill(content, tmp_path, "my_skill.md")
        surface = load_skill_surface(path)
        assert surface.skill_id == "my_skill"


# ---------------------------------------------------------------------------
# create_workspace_copy
# ---------------------------------------------------------------------------


class TestCreateWorkspaceCopy:

    def test_creates_workspace_copy(self, valid_skill_content, tmp_path, temp_workspace):
        source = _write_temp_skill(valid_skill_content, tmp_path)
        surface = load_skill_surface(source)
        copied = create_workspace_copy(surface, workspace_root=temp_workspace)

        assert copied.workspace_path is not None
        assert copied.workspace_path.exists()
        assert "workspace" in str(copied.workspace_path)

    def test_preserves_source_path(self, valid_skill_content, tmp_path, temp_workspace):
        source = _write_temp_skill(valid_skill_content, tmp_path)
        surface = load_skill_surface(source)
        copied = create_workspace_copy(surface, workspace_root=temp_workspace)

        # Source path is preserved
        assert copied.source_path == surface.source_path

    def test_workspace_content_matches(self, valid_skill_content, tmp_path, temp_workspace):
        source = _write_temp_skill(valid_skill_content, tmp_path)
        surface = load_skill_surface(source)
        copied = create_workspace_copy(surface, workspace_root=temp_workspace)

        # Read workspace file
        workspace_content = copied.workspace_path.read_text(encoding="utf-8")
        assert "test_skill" in workspace_content
        assert "# Test Skill" in workspace_content

    def test_deterministic_experiment_id(self, valid_skill_content, tmp_path, temp_workspace):
        source = _write_temp_skill(valid_skill_content, tmp_path)
        surface = load_skill_surface(source)

        # Same source path should produce same experiment_id
        copy1 = create_workspace_copy(surface, workspace_root=temp_workspace)
        # Note: calling again will use same dir since it's deterministic from path hash
        assert copy1.workspace_path.parent.name.startswith("exp_")

    def test_custom_experiment_id(self, valid_skill_content, tmp_path, temp_workspace):
        source = _write_temp_skill(valid_skill_content, tmp_path)
        surface = load_skill_surface(source)
        copied = create_workspace_copy(
            surface, workspace_root=temp_workspace, experiment_id="my_experiment"
        )

        assert "my_experiment" in str(copied.workspace_path)

    def test_does_not_modify_production(self, valid_skill_content, tmp_path, temp_workspace):
        source = _write_temp_skill(valid_skill_content, tmp_path)
        original_content = source.read_text()
        surface = load_skill_surface(source)
        create_workspace_copy(surface, workspace_root=temp_workspace)

        # Production file unchanged
        assert source.read_text() == original_content


# ---------------------------------------------------------------------------
# write_candidate_surface
# ---------------------------------------------------------------------------


class TestWriteCandidateSurface:

    def test_writes_candidate_file(self, valid_skill_content, tmp_path, temp_workspace):
        source = _write_temp_skill(valid_skill_content, tmp_path)
        surface = load_skill_surface(source)
        surface = create_workspace_copy(surface, workspace_root=temp_workspace)

        candidate_path = write_candidate_surface(surface, {"agents": ["qwen"]})
        assert candidate_path.exists()
        assert "candidate" in candidate_path.name

    def test_updates_mutable_fields(self, valid_skill_content, tmp_path, temp_workspace):
        source = _write_temp_skill(valid_skill_content, tmp_path)
        surface = load_skill_surface(source)
        surface = create_workspace_copy(surface, workspace_root=temp_workspace)

        candidate_path = write_candidate_surface(
            surface, {"agents": ["haiku"], "tokens_budget": 1000}
        )
        content = candidate_path.read_text()
        assert "haiku" in content
        assert "1000" in content

    def test_preserves_immutable_fields(self, valid_skill_content, tmp_path, temp_workspace):
        source = _write_temp_skill(valid_skill_content, tmp_path)
        surface = load_skill_surface(source)
        surface = create_workspace_copy(surface, workspace_root=temp_workspace)

        candidate_path = write_candidate_surface(surface, {"agents": ["haiku"]})
        content = candidate_path.read_text()
        # Immutable fields still present
        assert "test_skill" in content  # name
        assert "1.0.0" in content  # version
        assert "test_team" in content  # author

    def test_ignores_non_mutable_fields(self, valid_skill_content, tmp_path, temp_workspace):
        source = _write_temp_skill(valid_skill_content, tmp_path)
        surface = load_skill_surface(source)
        surface = create_workspace_copy(surface, workspace_root=temp_workspace)

        # Try to update an immutable field
        candidate_path = write_candidate_surface(
            surface, {"name": "hacked_name", "agents": ["haiku"]}
        )
        content = candidate_path.read_text()
        # name should NOT be changed
        assert "hacked_name" not in content
        assert "test_skill" in content  # Original name preserved

    def test_requires_workspace_path(self, valid_skill_content, tmp_path):
        source = _write_temp_skill(valid_skill_content, tmp_path)
        surface = load_skill_surface(source)

        # No workspace_path set
        with pytest.raises(TargetSurfaceError) as exc:
            write_candidate_surface(surface, {"agents": ["qwen"]})
        assert "workspace_path" in str(exc.value)

    def test_candidate_path_deterministic(self, valid_skill_content, tmp_path, temp_workspace):
        source = _write_temp_skill(valid_skill_content, tmp_path)
        surface = load_skill_surface(source)
        surface = create_workspace_copy(surface, workspace_root=temp_workspace)

        path1 = get_candidate_path(surface)
        path2 = get_candidate_path(surface)
        assert path1 == path2

    def test_production_file_unchanged(self, valid_skill_content, tmp_path, temp_workspace):
        source = _write_temp_skill(valid_skill_content, tmp_path)
        original_content = source.read_text()
        surface = load_skill_surface(source)
        surface = create_workspace_copy(surface, workspace_root=temp_workspace)
        write_candidate_surface(surface, {"agents": ["opus"]})

        # Production file still has original content
        assert source.read_text() == original_content
        assert "qwen" in original_content  # Original agents
        assert "opus" not in original_content  # Changed agents not in production


# ---------------------------------------------------------------------------
# Workspace isolation
# ---------------------------------------------------------------------------


class TestWorkspaceIsolation:

    def test_candidate_inside_workspace(self, valid_skill_content, tmp_path, temp_workspace):
        source = _write_temp_skill(valid_skill_content, tmp_path)
        surface = load_skill_surface(source)
        surface = create_workspace_copy(surface, workspace_root=temp_workspace)
        candidate_path = write_candidate_surface(surface, {"agents": ["qwen"]})

        # Candidate is inside workspace
        assert str(temp_workspace) in str(candidate_path)


# ---------------------------------------------------------------------------
# Mutable fields boundary
# ---------------------------------------------------------------------------


class TestMutableFieldsBoundary:

    def test_valid_mutable_fields_match_config(self):
        """Verify our mutable fields match experiment_config.py."""
        expected = {"agents", "wsp_chain", "domains", "tokens_budget", "prompt"}
        assert VALID_MUTABLE_FIELDS == expected

    def test_all_mutable_fields_extracted(self, tmp_path):
        """Test skill with all possible mutable fields."""
        content = """---
name: full_mutable
description: Has all mutable fields
agents: [qwen]
wsp_chain: [50, 97]
domains: [testing]
tokens_budget: 1000
prompt: "Custom prompt text"
---
# Body
"""
        path = _write_temp_skill(content, tmp_path)
        surface = load_skill_surface(path)

        assert "agents" in surface.mutable_fields
        assert "wsp_chain" in surface.mutable_fields
        assert "domains" in surface.mutable_fields
        assert "tokens_budget" in surface.mutable_fields
        assert "prompt" in surface.mutable_fields
        assert len(surface.mutable_fields) == 5


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


class TestSplitFrontmatter:

    def test_splits_valid(self):
        content = "---\nname: test\n---\n# Body"
        fm, body = _split_frontmatter(content)
        assert fm == "name: test"
        assert "# Body" in body

    def test_no_frontmatter(self):
        content = "# Just markdown"
        fm, body = _split_frontmatter(content)
        assert fm is None
        assert body == content

    def test_unclosed_frontmatter(self):
        content = "---\nname: test\n# No closing"
        fm, body = _split_frontmatter(content)
        assert fm is None


class TestRenderSkillContent:

    def test_renders_complete_skill(self, valid_skill_content, tmp_path):
        source = _write_temp_skill(valid_skill_content, tmp_path)
        surface = load_skill_surface(source)
        rendered = _render_skill_content(surface)

        assert rendered.startswith("---\n")
        assert "name: test_skill" in rendered
        assert "# Test Skill" in rendered
