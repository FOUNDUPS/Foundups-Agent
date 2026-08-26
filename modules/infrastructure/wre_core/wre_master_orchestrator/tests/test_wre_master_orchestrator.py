#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for WRE Master Orchestrator

WSP Compliance: WSP 5 (Test Coverage), WSP 96 (WRE Skills), WSP 77 (Agent Coordination)
"""

import pytest
import json
from pathlib import Path
from datetime import datetime
from types import SimpleNamespace
from modules.infrastructure.wre_core.wre_master_orchestrator.src.wre_master_orchestrator import (
    WREMasterOrchestrator,
    WRE_SKILLS_AVAILABLE
)
from modules.infrastructure.wre_core.src.libido_monitor import LibidoSignal


class TestWREMasterOrchestrator:
    """Test suite for WRE Master Orchestrator"""

    @pytest.fixture
    def orchestrator(self, monkeypatch, tmp_path):
        """Create an isolated orchestrator with an explicit successful executor."""
        monkeypatch.setenv("WRE_AGENTIC_RAG", "0")
        monkeypatch.setenv("WRE_REACT_MODE", "0")
        monkeypatch.setenv("FOUNDUPS_DB_PATH", str(tmp_path / "foundups.db"))
        monkeypatch.setenv("WRE_PATTERN_MEMORY_DB", str(tmp_path / "pattern_memory.db"))
        orchestrator = WREMasterOrchestrator()
        monkeypatch.setattr(
            orchestrator,
            "_ensure_wre_skill_safety",
            lambda _skill_name, force=False: (True, "test pass"),
        )
        monkeypatch.setattr(
            orchestrator,
            "_try_executor_dispatch",
            lambda *_args, **_kwargs: {
                "success": True,
                "output": "verified test executor result",
                "steps_completed": 4,
                "failed_at_step": None,
                "_effect_evidence": True,
            },
        )
        return orchestrator

    def test_initialization(self, orchestrator):
        """Test orchestrator initializes with correct components"""
        assert orchestrator is not None
        assert hasattr(orchestrator, 'pattern_memory')
        assert hasattr(orchestrator, 'wsp_validator')

    def test_legacy_recall_requires_injected_wsp_evidence(self, orchestrator):
        """An unconditional compatibility stub cannot authorize recall."""
        with pytest.raises(ValueError, match="WSP 50"):
            orchestrator.recall_pattern("module_creation")

    def test_legacy_recall_does_not_invent_unknown_pattern(self, orchestrator):
        """Even admitted recall is limited to registered pattern memory."""
        orchestrator.wsp_validator = SimpleNamespace(
            verify=lambda _operation: True,
            prevent_violation=lambda _operation: True,
        )

        with pytest.raises(KeyError, match="No registered pattern"):
            orchestrator.recall_pattern("unknown_operation")
        assert hasattr(orchestrator, 'plugins')

        # Check WSP 96 v1.3 components if available
        if WRE_SKILLS_AVAILABLE:
            assert hasattr(orchestrator, 'libido_monitor')
            assert hasattr(orchestrator, 'sqlite_memory')
            assert hasattr(orchestrator, 'skills_loader')

    def test_legacy_plugin_cannot_dispatch_before_wsp_verification(self, orchestrator):
        """Compatibility plugin code cannot bypass the injected evidence gate."""
        calls = []

        class _Plugin:
            def execute(self, task):
                calls.append(task)
                return {"success": True, "worker_started": True}

        orchestrator.plugins["test_plugin"] = _Plugin()

        with pytest.raises(ValueError, match="WSP 50"):
            orchestrator.execute(
                {"plugin": "test_plugin", "type": "orchestration"}
            )
        assert calls == []

    def test_legacy_plugin_dispatch_remains_blocked_after_wsp_callbacks(self, orchestrator):
        """WSP callbacks do not authenticate a plugin executor or its effects."""
        calls = []
        orchestrator.wsp_validator = SimpleNamespace(
            verify=lambda _operation: True,
            prevent_violation=lambda _operation: True,
        )
        orchestrator.plugins["test_plugin"] = SimpleNamespace(
            execute=lambda task: calls.append(task) or {
                "success": True,
                "effect_receipt": {"forged": True},
                "worker_started": True,
            }
        )

        with pytest.raises(PermissionError, match="admitted Skillz executor"):
            orchestrator.execute(
                {"plugin": "test_plugin", "type": "orchestration"}
            )
        assert calls == []

    def test_direct_holoindex_plugin_execution_is_always_blocked(self, orchestrator):
        """Injected WSP callbacks do not replace governed Holo owner evidence."""
        calls = []
        orchestrator.wsp_validator = SimpleNamespace(
            verify=lambda _operation: True,
            prevent_violation=lambda _operation: True,
        )
        orchestrator.plugins["holoindex"] = SimpleNamespace(
            execute=lambda task: calls.append(task)
        )

        with pytest.raises(PermissionError, match="governed owner query"):
            orchestrator.execute(
                {"plugin": "holoindex", "type": "orchestration"}
            )
        assert calls == []

    def test_legacy_pattern_log_does_not_expose_task_or_result(self, orchestrator, caplog):
        """Compatibility logging records structure without caller material."""
        caplog.set_level("INFO")
        orchestrator.wsp_validator = SimpleNamespace(
            verify=lambda _operation: True,
            prevent_violation=lambda _operation: True,
        )

        result = orchestrator.execute(
            {"type": "orchestration", "payload": "SYNTHETIC_SECRET"}
        )

        assert "Applied orchestration" in result
        assert "Logged compatibility operation" in caplog.text
        assert "SYNTHETIC_SECRET" not in caplog.text

    @pytest.mark.skipif(not WRE_SKILLS_AVAILABLE, reason="WRE Skills infrastructure not available")
    def test_execute_skill_first_execution_escalates(self, orchestrator):
        """Test first skill execution triggers ESCALATE signal"""
        skill_name = "auto_test_registry_audit"
        agent = "qwen"
        input_context = {"files_changed": 14, "lines_added": 250}

        result = orchestrator.execute_skill(skill_name, agent, input_context)

        # First execution should always proceed (ESCALATE signal)
        assert result["success"] is True
        assert "pattern_fidelity" in result
        assert "execution_id" in result
        assert "execution_time_ms" in result

    @pytest.mark.skipif(not WRE_SKILLS_AVAILABLE, reason="WRE Skills infrastructure not available")
    def test_execute_skill_blocks_when_supply_chain_gate_fails(self, orchestrator, monkeypatch):
        """Per-skill scanner gate must block execution when enforced failure occurs."""
        monkeypatch.setattr(
            orchestrator,
            "_ensure_wre_skill_safety",
            lambda skill_name, force=False: (False, "blocked by test"),
        )
        result = orchestrator.execute_skill(
            "auto_test_registry_audit",
            "qwen",
            {"files_changed": 1},
            force=True,
        )
        assert result["success"] is False
        assert result.get("blocked") is True
        assert result.get("blocked_by") == "wre_skill_scan"

    @pytest.mark.skipif(not WRE_SKILLS_AVAILABLE, reason="WRE Skills infrastructure not available")
    def test_execute_skill_throttle_behavior(self, orchestrator):
        """Test skill execution respects libido THROTTLE signal"""
        skill_name = "auto_test_registry_audit"
        agent = "qwen"
        input_context = {"files_changed": 5}

        # Execute 5 times (hit max frequency)
        for i in range(5):
            result = orchestrator.execute_skill(skill_name, agent, input_context)
            assert result["success"] is True

        # 6th execution should be throttled
        result = orchestrator.execute_skill(skill_name, agent, input_context)
        assert result.get("throttled") is True

    @pytest.mark.skipif(not WRE_SKILLS_AVAILABLE, reason="WRE Skills infrastructure not available")
    def test_execute_skill_force_override(self, orchestrator):
        """Test force=True overrides libido throttle"""
        skill_name = "auto_test_registry_audit"
        agent = "qwen"
        input_context = {"files_changed": 10}

        # Execute 5 times (hit max frequency)
        for i in range(5):
            orchestrator.execute_skill(skill_name, agent, input_context)

        # Force execution should succeed despite throttle
        result = orchestrator.execute_skill(skill_name, agent, input_context, force=True)
        assert result["success"] is True
        assert result.get("throttled") is not True

    @pytest.mark.skipif(not WRE_SKILLS_AVAILABLE, reason="WRE Skills infrastructure not available")
    def test_execute_skill_stores_outcome(self, orchestrator):
        """Test skill execution stores outcome in pattern memory"""
        skill_name = "auto_test_registry_audit"
        agent = "qwen"
        input_context = {"files_changed": 14}

        # Execute skill
        result = orchestrator.execute_skill(skill_name, agent, input_context)
        execution_id = result["execution_id"]

        # Verify outcome stored in SQLite pattern memory
        patterns = orchestrator.sqlite_memory.recall_successful_patterns(skill_name, min_fidelity=0.0, limit=10)

        # Should find the execution we just did
        execution_found = any(p["execution_id"] == execution_id for p in patterns)
        assert execution_found, f"Execution {execution_id} not found in pattern memory"

    @pytest.mark.skipif(not WRE_SKILLS_AVAILABLE, reason="WRE Skills infrastructure not available")
    def test_execute_skill_records_libido_history(self, orchestrator):
        """Test skill execution records in libido monitor history"""
        skill_name = "auto_test_registry_audit"
        agent = "qwen"
        input_context = {"files_changed": 8}

        # Execute skill
        result = orchestrator.execute_skill(skill_name, agent, input_context)

        # Verify recorded in libido monitor
        stats = orchestrator.libido_monitor.get_skill_statistics(skill_name)
        assert stats["execution_count"] >= 1
        assert stats["avg_fidelity"] >= 0.0

    @pytest.mark.skipif(not WRE_SKILLS_AVAILABLE, reason="WRE Skills infrastructure not available")
    def test_execute_skill_calculates_execution_time(self, orchestrator):
        """Test execution time is measured and returned"""
        skill_name = "auto_test_registry_audit"
        agent = "qwen"
        input_context = {"files_changed": 12}

        result = orchestrator.execute_skill(skill_name, agent, input_context)

        assert "execution_time_ms" in result
        assert isinstance(result["execution_time_ms"], int)
        assert result["execution_time_ms"] >= 0

    @pytest.mark.skipif(not WRE_SKILLS_AVAILABLE, reason="WRE Skills infrastructure not available")
    def test_execute_skill_pattern_fidelity_recorded(self, orchestrator):
        """Test pattern fidelity is calculated and stored"""
        skill_name = "auto_test_registry_audit"
        agent = "qwen"
        input_context = {"files_changed": 20}

        result = orchestrator.execute_skill(skill_name, agent, input_context)

        assert "pattern_fidelity" in result
        assert isinstance(result["pattern_fidelity"], float)
        assert 0.0 <= result["pattern_fidelity"] <= 1.0

    @pytest.mark.skipif(not WRE_SKILLS_AVAILABLE, reason="WRE Skills infrastructure not available")
    def test_execute_skill_multiple_agents(self, orchestrator):
        """Test different agents can execute same skill"""
        skill_name = "auto_test_registry_audit"
        input_context = {"files_changed": 7}

        # Execute with qwen
        result_qwen = orchestrator.execute_skill(skill_name, "qwen", input_context)
        assert result_qwen["success"] is True

        # Execute with gemma (if skill supports it)
        result_gemma = orchestrator.execute_skill(skill_name, "gemma", input_context)
        assert result_gemma["success"] is True

        # Both should be recorded separately
        stats = orchestrator.libido_monitor.get_skill_statistics(skill_name)
        assert stats["execution_count"] >= 2

    @pytest.mark.skipif(not WRE_SKILLS_AVAILABLE, reason="WRE Skills infrastructure not available")
    def test_execute_skill_input_context_stored(self, orchestrator):
        """Test input context is stored in outcome record"""
        skill_name = "auto_test_registry_audit"
        agent = "qwen"
        input_context = {"files_changed": 14, "lines_added": 250, "critical_files": ["main.py"]}

        result = orchestrator.execute_skill(skill_name, agent, input_context)
        execution_id = result["execution_id"]

        # Recall and verify input context was stored
        patterns = orchestrator.sqlite_memory.recall_successful_patterns(skill_name, min_fidelity=0.0, limit=10)
        execution = next((p for p in patterns if p["execution_id"] == execution_id), None)

        assert execution is not None
        stored_context = json.loads(execution["input_context"])
        assert stored_context["files_changed"] == 14
        assert stored_context["lines_added"] == 250

    def test_validate_module_path(self, orchestrator):
        """Test module path validation"""
        # Valid path
        valid_path = Path("modules/ai_intelligence/pqn_alignment")
        result = orchestrator.validate_module_path(valid_path)
        assert result is True

        # Invalid path
        invalid_path = Path("nonexistent/module/path")
        result = orchestrator.validate_module_path(invalid_path)
        assert result is False

    def test_validate_module_path_rejects_existing_external_directory(
        self, orchestrator, tmp_path
    ):
        external = tmp_path / "outside-checkout"
        external.mkdir()
        assert orchestrator.validate_module_path(external) is False

    def test_register_plugin(self, orchestrator):
        """Test plugin registration"""
        class TestPlugin:
            def process(self):
                return "test_result"

        plugin = TestPlugin()
        orchestrator.register_plugin("test_plugin", plugin)

        assert "test_plugin" in orchestrator.plugins
        assert orchestrator.plugins["test_plugin"] == plugin

    def test_get_plugin(self, orchestrator):
        """Test plugin retrieval"""
        class TestPlugin:
            def process(self):
                return "test_result"

        plugin = TestPlugin()
        orchestrator.register_plugin("test_plugin", plugin)

        retrieved = orchestrator.get_plugin("test_plugin")
        assert retrieved == plugin

        # Nonexistent plugin should return None
        nonexistent = orchestrator.get_plugin("nonexistent_plugin")
        assert nonexistent is None


class TestWRESkillsIntegration:
    """Integration tests for WRE Skills system"""

    @pytest.fixture
    def orchestrator(self, monkeypatch, tmp_path):
        """Create an isolated orchestrator with an explicit successful executor."""
        monkeypatch.setenv("WRE_AGENTIC_RAG", "0")
        monkeypatch.setenv("WRE_REACT_MODE", "0")
        monkeypatch.setenv("FOUNDUPS_DB_PATH", str(tmp_path / "foundups.db"))
        monkeypatch.setenv("WRE_PATTERN_MEMORY_DB", str(tmp_path / "pattern_memory.db"))
        orchestrator = WREMasterOrchestrator()
        monkeypatch.setattr(
            orchestrator,
            "_ensure_wre_skill_safety",
            lambda _skill_name, force=False: (True, "test pass"),
        )
        monkeypatch.setattr(
            orchestrator,
            "_try_executor_dispatch",
            lambda *_args, **_kwargs: {
                "success": True,
                "output": "verified test executor result",
                "steps_completed": 4,
                "failed_at_step": None,
                "_effect_evidence": True,
            },
        )
        return orchestrator

    @pytest.mark.skipif(not WRE_SKILLS_AVAILABLE, reason="WRE Skills infrastructure not available")
    def test_end_to_end_skill_execution_cycle(self, orchestrator):
        """Test complete cycle: execute → store → recall → analyze"""
        skill_name = "auto_test_registry_audit"
        agent = "qwen"

        # Step 1: Execute skill 3 times
        execution_ids = []
        for i in range(3):
            input_context = {"files_changed": 10 + i, "execution_number": i}
            result = orchestrator.execute_skill(skill_name, agent, input_context)
            execution_ids.append(result["execution_id"])
            assert result["success"] is True

        # Step 2: Recall successful patterns
        patterns = orchestrator.sqlite_memory.recall_successful_patterns(skill_name, min_fidelity=0.0)
        assert len(patterns) >= 3

        # Step 3: Get metrics
        metrics = orchestrator.sqlite_memory.get_skill_metrics(skill_name, days=1)
        assert metrics["execution_count"] >= 3
        assert metrics["avg_fidelity"] >= 0.0

        # Step 4: Get libido statistics
        stats = orchestrator.libido_monitor.get_skill_statistics(skill_name)
        assert stats["execution_count"] >= 3

    @pytest.mark.skipif(not WRE_SKILLS_AVAILABLE, reason="WRE Skills infrastructure not available")
    def test_unregistered_skill_cannot_simulate_convergence(self, orchestrator):
        """An absent registry entry cannot generate successful RSI evidence."""
        skill_name = "test_convergence_skill"
        agent = "qwen"

        result = orchestrator.execute_skill(
            skill_name,
            agent,
            {"iteration": 0},
            force=True,
        )

        assert result["success"] is False
        assert result["blocked_by"] == "skill_load"
        metrics = orchestrator.sqlite_memory.get_skill_metrics(skill_name, days=1)
        assert metrics["execution_count"] == 0
        patterns = orchestrator.sqlite_memory.recall_successful_patterns(skill_name, min_fidelity=0.0, limit=20)
        assert patterns == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
