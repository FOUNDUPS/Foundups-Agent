#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for WRE Skills Discovery (Phase 2)

WSP Compliance: WSP 5 (Test Coverage), WSP 96 (WRE Skills)
"""

import pytest
from pathlib import Path
from modules.infrastructure.wre_core.skillz.wre_skills_discovery import (
    WRESkillsDiscovery,
    DiscoveredSkill
)


class TestWRESkillsDiscovery:
    """Test suite for WRE Skills Discovery"""

    @pytest.fixture
    def discovery(self):
        """Create WRE Skills Discovery instance"""
        return WRESkillsDiscovery()

    def test_initialization(self, discovery):
        """Test discovery initializes with correct repo root"""
        assert discovery is not None
        assert discovery.repo_root.exists()
        assert (discovery.repo_root / "AGENTS.md").is_file()
        assert (discovery.repo_root / "modules").is_dir()

    def test_discover_all_skills(self, discovery):
        """Test discover all skills from filesystem"""
        skills = discovery.discover_all_skills()

        assert isinstance(skills, list)
        assert len(skills) >= 0  # May be 0 if no skills in test environment

        # If skills found, verify structure
        if skills:
            skill = skills[0]
            assert isinstance(skill, DiscoveredSkill)
            assert skill.skill_name
            assert isinstance(skill.agents, list)
            assert skill.skill_path.exists()

    def test_discover_by_agent_qwen(self, discovery):
        """Test discover Qwen skills"""
        qwen_skills = discovery.discover_by_agent("qwen")

        assert isinstance(qwen_skills, list)

        # If found, verify all are Qwen skills
        for skill in qwen_skills:
            assert "qwen" in skill.agents or skill.agents[0] == "qwen"

    def test_discover_by_agent_gemma(self, discovery):
        """Test discover Gemma skills"""
        gemma_skills = discovery.discover_by_agent("gemma")

        assert isinstance(gemma_skills, list)

        # If found, verify all are Gemma skills
        for skill in gemma_skills:
            assert "gemma" in skill.agents or skill.agents[0] == "gemma"

    def test_discover_by_module(self, discovery):
        """Test discover skills by module path"""
        # Try discovering skills from git_push_dae module
        git_push_skills = discovery.discover_by_module("modules/infrastructure/git_push_dae")

        assert isinstance(git_push_skills, list)

        # If found, verify path contains module
        for skill in git_push_skills:
            assert "git_push_dae" in str(skill.skill_path)

    def test_discover_production_ready(self, discovery):
        """Test discover production-ready skills"""
        prod_skills = discovery.discover_production_ready(min_fidelity=0.90)

        assert isinstance(prod_skills, list)

        # If found, verify promotion state
        for skill in prod_skills:
            assert skill.promotion_state == "production"

    def test_promotion_state_inference_prototype(self, discovery):
        """Test promotion state inference for prototype skills"""
        # Prototype skills should be in .claude/skills/
        path = Path(".claude/skills/test_prototype/SKILL.md")
        state = discovery._infer_promotion_state(path)
        assert state == "prototype"

    def test_promotion_state_inference_production(self, discovery):
        """Test promotion state inference for production skills"""
        # Production skills should be in modules/*/skillz/
        path = Path("modules/infrastructure/test/skillz/test_skill/SKILLz.md")
        state = discovery._infer_promotion_state(path)
        assert state == "production"

    def test_parse_agents_string(self, discovery):
        """Test parse agents from string format"""
        agents_str = "Qwen 1.5B, Gemma 270M"
        agents = discovery._parse_agents(agents_str)

        assert "qwen" in agents
        assert "gemma" in agents

    def test_parse_agents_list(self, discovery):
        """Test parse agents from list format (YAML)"""
        agents_list = ["qwen", "gemma"]
        agents = discovery._parse_agents(agents_list)

        assert "qwen" in agents
        assert "gemma" in agents

    def test_parse_agents_empty(self, discovery):
        """Test parse agents with empty input"""
        agents = discovery._parse_agents(None)
        assert agents == []

        agents = discovery._parse_agents("")
        assert agents == []

    def test_parse_wsp_chain(self, discovery):
        """Test WSP chain extraction from content"""
        content = """
        This skill follows WSP 96 and WSP 77 for agent coordination.
        Also references WSP 50 for pre-action verification.
        """
        wsp_chain = discovery._parse_wsp_chain(content)

        assert "WSP 96" in wsp_chain
        assert "WSP 77" in wsp_chain
        assert "WSP 50" in wsp_chain

    def test_parse_wsp_chain_deduplicate(self, discovery):
        """Test WSP chain deduplication"""
        content = "WSP 96, WSP 96, WSP 77, WSP 77"
        wsp_chain = discovery._parse_wsp_chain(content)

        # Should deduplicate
        assert wsp_chain.count("WSP 96") == 1
        assert wsp_chain.count("WSP 77") == 1

    def test_export_discovered_to_registry(self, discovery, tmp_path):
        """Test export discovered skills to registry JSON"""
        # Create mock skills
        skills = [
            DiscoveredSkill(
                skill_path=Path("test/skills/skill1/SKILL.md"),
                skill_name="test_skill_1",
                agents=["qwen"],
                intent_type="DECISION",
                version="1.0.0",
                promotion_state="prototype",
                wsp_chain=["WSP 96"],
                metadata={"description": "Test skill"}
            )
        ]

        output_path = tmp_path / "test_registry.json"
        discovery.export_discovered_to_registry(output_path, skills)

        # Verify file created
        assert output_path.exists()

        # Verify content
        import json
        with open(output_path, 'r') as f:
            registry = json.load(f)

        assert registry["version"] == "2.0"
        assert "test_skill_1" in registry["skills"]
        assert registry["skills"]["test_skill_1"]["primary_agent"] == "qwen"

    def test_watcher_start_stop(self, discovery):
        """Test filesystem watcher start/stop"""
        # Start watcher
        discovery.start_watcher(interval_seconds=1)
        assert discovery._watcher_running is True
        assert discovery._watcher_thread.is_alive()

        # Stop watcher
        discovery.stop_watcher()
        assert discovery._watcher_running is False

    def test_watcher_callback(self, discovery):
        """Test filesystem watcher callback"""
        callback_called = []

        def test_callback(skills):
            callback_called.append(len(skills))

        # Start watcher with callback
        discovery.start_watcher(interval_seconds=1, on_change_callback=test_callback)

        # Wait a bit for callback
        import time
        time.sleep(2)

        # Stop watcher
        discovery.stop_watcher()

        # Callback should have been called at least once
        assert len(callback_called) >= 1


class TestDiscoveredSkillDataclass:
    """Test DiscoveredSkill dataclass"""

    def test_discovered_skill_creation(self):
        """Test creating DiscoveredSkill"""
        skill = DiscoveredSkill(
            skill_path=Path("test/SKILL.md"),
            skill_name="test_skill",
            agents=["qwen"],
            intent_type="DECISION",
            version="1.0.0",
            promotion_state="prototype",
            wsp_chain=["WSP 96"],
            metadata={}
        )

        assert skill.skill_name == "test_skill"
        assert skill.agents == ["qwen"]
        assert skill.promotion_state == "prototype"

    def test_discovered_skill_hygiene_fields(self):
        """Test Skills 2.0 hygiene fields on DiscoveredSkill."""
        skill = DiscoveredSkill(
            skill_path=Path("test/SKILL.md"),
            skill_name="test_skill",
            agents=["qwen"],
            intent_type="DECISION",
            version="1.0.0",
            promotion_state="production",
            wsp_chain=["WSP 96"],
            metadata={},
            category="workflow",
            retirement_date="",
            has_evals=True,
        )

        assert skill.category == "workflow"
        assert skill.retirement_date == ""
        assert skill.has_evals is True


class TestSkillsHygiene:
    """Test Skills 2.0 hygiene filtering."""

    @pytest.fixture
    def discovery(self):
        """Create WRE Skills Discovery instance."""
        return WRESkillsDiscovery()

    def test_is_retired_null(self, discovery):
        """Null retirement_date means not retired."""
        assert discovery._is_retired(None) is False
        assert discovery._is_retired("null") is False
        assert discovery._is_retired("") is False

    def test_is_retired_future_date(self, discovery):
        """Future retirement_date means not retired."""
        assert discovery._is_retired("2099-12-31") is False
        assert discovery._is_retired("2099-12-31T23:59:59+00:00") is False

    def test_is_retired_past_date(self, discovery):
        """Past retirement_date means retired."""
        assert discovery._is_retired("2020-01-01") is True
        assert discovery._is_retired("2020-01-01T00:00:00+00:00") is True

    def test_is_retired_invalid_format(self, discovery):
        """Invalid format returns False (not retired)."""
        assert discovery._is_retired("not-a-date") is False
        assert discovery._is_retired(12345) is False

    def test_discover_healthy_skills_excludes_retired(self, discovery, tmp_path, monkeypatch):
        """discover_healthy_skills excludes retired skills."""
        # Create mock skills - one active, one retired
        active_skill = DiscoveredSkill(
            skill_path=tmp_path / "active/SKILLz.md",
            skill_name="active_skill",
            agents=["qwen"],
            intent_type="DECISION",
            version="1.0.0",
            promotion_state="production",
            wsp_chain=[],
            metadata={},
            category="workflow",
            retirement_date="",
            has_evals=True,
        )
        retired_skill = DiscoveredSkill(
            skill_path=tmp_path / "retired/SKILLz.md",
            skill_name="retired_skill",
            agents=["qwen"],
            intent_type="DECISION",
            version="1.0.0",
            promotion_state="production",
            wsp_chain=[],
            metadata={},
            category="workflow",
            retirement_date="2020-01-01",
            has_evals=True,
        )

        # Mock discover_all_skills to return our test skills
        monkeypatch.setattr(discovery, "discover_all_skills", lambda: [active_skill, retired_skill])

        healthy = discovery.discover_healthy_skills()

        assert len(healthy) == 1
        assert healthy[0].skill_name == "active_skill"

    def test_discover_healthy_skills_excludes_invalid_category(self, discovery, tmp_path, monkeypatch):
        """discover_healthy_skills excludes skills with invalid category."""
        valid_skill = DiscoveredSkill(
            skill_path=tmp_path / "valid/SKILLz.md",
            skill_name="valid_skill",
            agents=["qwen"],
            intent_type="DECISION",
            version="1.0.0",
            promotion_state="production",
            wsp_chain=[],
            metadata={},
            category="workflow",
            retirement_date="",
            has_evals=True,
        )
        invalid_category_skill = DiscoveredSkill(
            skill_path=tmp_path / "invalid/SKILLz.md",
            skill_name="invalid_category_skill",
            agents=["qwen"],
            intent_type="DECISION",
            version="1.0.0",
            promotion_state="production",
            wsp_chain=[],
            metadata={},
            category="invalid_category",  # Not workflow or capability-uplift
            retirement_date="",
            has_evals=True,
        )

        monkeypatch.setattr(discovery, "discover_all_skills", lambda: [valid_skill, invalid_category_skill])

        healthy = discovery.discover_healthy_skills()

        assert len(healthy) == 1
        assert healthy[0].skill_name == "valid_skill"

    def test_discover_healthy_skills_allows_capability_uplift(self, discovery, tmp_path, monkeypatch):
        """discover_healthy_skills allows capability-uplift category."""
        uplift_skill = DiscoveredSkill(
            skill_path=tmp_path / "uplift/SKILLz.md",
            skill_name="uplift_skill",
            agents=["qwen"],
            intent_type="DECISION",
            version="1.0.0",
            promotion_state="production",
            wsp_chain=[],
            metadata={},
            category="capability-uplift",
            retirement_date="",
            has_evals=True,
        )

        monkeypatch.setattr(discovery, "discover_all_skills", lambda: [uplift_skill])

        healthy = discovery.discover_healthy_skills()

        assert len(healthy) == 1
        assert healthy[0].category == "capability-uplift"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
