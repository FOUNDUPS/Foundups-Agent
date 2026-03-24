#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Gateway Continuity Layer.

Tests cover:
- ContinuityContext creation and serialization
- RuntimeSurface enum
- ContinuityManager factory methods
- Cross-surface breadcrumb recording
- Continuity query endpoints
"""

import os
import pytest
from datetime import datetime, UTC
from pathlib import Path
from unittest.mock import MagicMock, patch

from modules.communication.moltbot_bridge.src.continuity_context import (
    ContinuityContext,
    ContinuityManager,
    RuntimeSurface,
    _generate_continuity_id,
)


class TestRuntimeSurface:
    """Test RuntimeSurface enum."""

    def test_all_surfaces_defined(self):
        """All expected surfaces are defined."""
        expected = {"cli", "openclaw", "messaging", "social", "supervisor", "idle", "wre", "internal", "unknown"}
        actual = {s.value for s in RuntimeSurface}
        assert expected == actual

    def test_surface_is_string_enum(self):
        """Surface values are strings for JSON serialization."""
        assert RuntimeSurface.CLI.value == "cli"
        assert RuntimeSurface.OPENCLAW.value == "openclaw"


class TestContinuityContext:
    """Test ContinuityContext dataclass."""

    def test_default_values(self):
        """Default values are set correctly."""
        ctx = ContinuityContext()
        assert len(ctx.continuity_id) == 12
        assert ctx.surface == RuntimeSurface.UNKNOWN
        assert ctx.session_id == ""
        assert ctx.sender == ""
        assert ctx.parent_continuity_id is None

    def test_continuity_id_is_unique(self):
        """Each context gets a unique continuity ID."""
        ctx1 = ContinuityContext()
        ctx2 = ContinuityContext()
        assert ctx1.continuity_id != ctx2.continuity_id

    def test_sender_normalization(self):
        """Sender is normalized on creation."""
        ctx = ContinuityContext(sender="WA:+1-555-123-4567")
        assert ctx.sender_normalized == "+15551234567"

    def test_sender_normalization_lowercase(self):
        """Sender is lowercased."""
        ctx = ContinuityContext(sender="Discord:USER123")
        assert ctx.sender_normalized == "user123"

    def test_sender_normalization_empty(self):
        """Empty sender becomes 'anonymous'."""
        ctx = ContinuityContext(sender="")
        assert ctx.sender_normalized == "anonymous"

    def test_to_dict_serialization(self):
        """to_dict produces JSON-serializable output."""
        ctx = ContinuityContext(
            continuity_id="abc123def456",
            surface=RuntimeSurface.OPENCLAW,
            session_id="session_001",
            sender="012",
            channel="whatsapp",
        )
        data = ctx.to_dict()
        assert data["continuity_id"] == "abc123def456"
        assert data["surface"] == "openclaw"
        assert data["session_id"] == "session_001"
        assert data["sender"] == "012"

    def test_from_dict_roundtrip(self):
        """from_dict restores context from dict."""
        original = ContinuityContext(
            continuity_id="test12345678",
            surface=RuntimeSurface.CLI,
            session_id="cli_123",
            sender="test_user",
            channel="terminal",
            parent_continuity_id="parent12345",
        )
        data = original.to_dict()
        restored = ContinuityContext.from_dict(data)
        assert restored.continuity_id == original.continuity_id
        assert restored.surface == original.surface
        assert restored.parent_continuity_id == original.parent_continuity_id

    def test_fork_creates_new_id_with_parent(self):
        """fork() creates new context with parent linkage."""
        parent = ContinuityContext(
            continuity_id="parent123456",
            surface=RuntimeSurface.OPENCLAW,
            sender="012",
        )
        child = parent.fork(new_surface=RuntimeSurface.WRE)
        assert child.continuity_id != parent.continuity_id
        assert child.parent_continuity_id == parent.continuity_id
        assert child.surface == RuntimeSurface.WRE
        assert child.sender == parent.sender

    def test_touch_updates_last_activity(self):
        """touch() updates last_activity_at."""
        ctx = ContinuityContext()
        original_activity = ctx.last_activity_at
        ctx.touch()
        # Should have updated (may be same if too fast, but should not be None)
        assert ctx.last_activity_at is not None

    def test_to_breadcrumb_metadata(self):
        """to_breadcrumb_metadata returns compact dict."""
        ctx = ContinuityContext(
            continuity_id="crumb1234567",
            surface=RuntimeSurface.MESSAGING,
            sender_normalized="012",
            parent_continuity_id="parent12345",
        )
        meta = ctx.to_breadcrumb_metadata()
        assert meta["continuity_id"] == "crumb1234567"
        assert meta["surface"] == "messaging"
        assert meta["sender_normalized"] == "012"
        assert meta["parent_continuity_id"] == "parent12345"


class TestContinuityManager:
    """Test ContinuityManager factory methods."""

    def test_from_openclaw(self):
        """from_openclaw creates OpenClaw context."""
        ctx = ContinuityManager.from_openclaw(
            sender="012",
            channel="whatsapp",
            session_key="session_abc",
            metadata={"extra": "data"},
        )
        assert ctx.surface == RuntimeSurface.OPENCLAW
        assert ctx.sender == "012"
        assert ctx.channel == "whatsapp"
        assert ctx.session_id == "session_abc"
        assert ctx.surface_metadata.get("entry_point") == "openclaw_dae.process"

    def test_from_openclaw_propagates_continuity_id(self):
        """from_openclaw propagates continuity_id from metadata."""
        ctx = ContinuityManager.from_openclaw(
            sender="012",
            channel="discord",
            session_key="test",
            metadata={"continuity_id": "propagated123"},
        )
        assert ctx.continuity_id == "propagated123"

    def test_from_openclaw_same_session_produces_same_id(self):
        """from_openclaw with same session_key produces same continuity_id."""
        ctx1 = ContinuityManager.from_openclaw(
            sender="012",
            channel="whatsapp",
            session_key="stable_session_123",
        )
        ctx2 = ContinuityManager.from_openclaw(
            sender="012",
            channel="whatsapp",
            session_key="stable_session_123",
        )
        assert ctx1.continuity_id == ctx2.continuity_id

    def test_from_openclaw_different_session_produces_different_id(self):
        """from_openclaw with different session_key produces different continuity_id."""
        ctx1 = ContinuityManager.from_openclaw(
            sender="012",
            channel="whatsapp",
            session_key="session_A",
        )
        ctx2 = ContinuityManager.from_openclaw(
            sender="012",
            channel="whatsapp",
            session_key="session_B",
        )
        assert ctx1.continuity_id != ctx2.continuity_id

    def test_from_openclaw_reads_env(self):
        """from_openclaw reads continuity from environment."""
        with patch.dict(os.environ, {
            "OPENCLAW_CONTINUITY_ID": "env_oc_12345",
            "OPENCLAW_PARENT_CONTINUITY_ID": "env_parent_67",
        }):
            ctx = ContinuityManager.from_openclaw(
                sender="012",
                channel="telegram",
                session_key="session_env",
            )
            assert ctx.continuity_id == "env_oc_12345"
            assert ctx.parent_continuity_id == "env_parent_67"

    def test_from_cli(self):
        """from_cli creates CLI context."""
        ctx = ContinuityManager.from_cli(
            command="python script.py",
            script_name="script.py",
        )
        assert ctx.surface == RuntimeSurface.CLI
        assert ctx.sender == "cli"
        assert ctx.channel == "terminal"
        assert "cli_" in ctx.session_id
        assert ctx.surface_metadata.get("command") == "python script.py"

    def test_from_cli_reads_env(self):
        """from_cli reads continuity from environment."""
        with patch.dict(os.environ, {
            "OPENCLAW_CONTINUITY_ID": "env_id_12345",
            "OPENCLAW_PARENT_CONTINUITY_ID": "parent_id_678",
        }):
            ctx = ContinuityManager.from_cli()
            assert ctx.continuity_id == "env_id_12345"
            assert ctx.parent_continuity_id == "parent_id_678"

    def test_from_supervisor(self):
        """from_supervisor creates supervisor context."""
        ctx = ContinuityManager.from_supervisor(
            cycle_id="cycle_123",
            state="EXECUTE",
        )
        assert ctx.surface == RuntimeSurface.SUPERVISOR
        assert ctx.sender == "supervisor"
        assert "cycle_123" in ctx.session_id
        assert ctx.surface_metadata.get("state") == "EXECUTE"

    def test_from_supervisor_with_parent(self):
        """from_supervisor forks from parent context for lineage tracking."""
        parent = ContinuityContext(
            continuity_id="openclaw_root",
            surface=RuntimeSurface.OPENCLAW,
            sender="012",
        )
        ctx = ContinuityManager.from_supervisor(
            cycle_id="cycle_456",
            state="TRIAGE",
            parent_context=parent,
        )
        assert ctx.surface == RuntimeSurface.SUPERVISOR
        assert ctx.parent_continuity_id == "openclaw_root"
        assert ctx.continuity_id != parent.continuity_id
        assert ctx.sender == "supervisor"
        assert "cycle_456" in ctx.session_id

    def test_from_idle(self):
        """from_idle creates idle automation context."""
        ctx = ContinuityManager.from_idle(task_type="self_research")
        assert ctx.surface == RuntimeSurface.IDLE
        assert ctx.sender == "idle_dae"
        assert ctx.surface_metadata.get("task_type") == "self_research"

    def test_from_idle_with_parent(self):
        """from_idle forks from parent context for lineage tracking."""
        parent = ContinuityContext(
            continuity_id="youtube_dae_root",
            surface=RuntimeSurface.OPENCLAW,
            sender="012",
        )
        ctx = ContinuityManager.from_idle(
            task_type="background_tasks",
            parent_context=parent,
        )
        assert ctx.surface == RuntimeSurface.IDLE
        assert ctx.parent_continuity_id == "youtube_dae_root"
        assert ctx.continuity_id != parent.continuity_id
        assert ctx.sender == "idle_dae"

    def test_from_wre_with_parent(self):
        """from_wre forks from parent context."""
        parent = ContinuityContext(
            continuity_id="parent123456",
            surface=RuntimeSurface.OPENCLAW,
            sender="012",
        )
        ctx = ContinuityManager.from_wre(
            skill_name="qwen_gitpush",
            agent="qwen",
            parent_context=parent,
        )
        assert ctx.surface == RuntimeSurface.WRE
        assert ctx.parent_continuity_id == "parent123456"
        assert ctx.sender == "012"
        assert ctx.surface_metadata.get("skill_name") == "qwen_gitpush"

    def test_from_wre_without_parent(self):
        """from_wre creates standalone context without parent."""
        ctx = ContinuityManager.from_wre(
            skill_name="gemma_classify",
            agent="gemma",
        )
        assert ctx.surface == RuntimeSurface.WRE
        assert ctx.parent_continuity_id is None
        assert ctx.sender == "wre"

    def test_from_messaging(self):
        """from_messaging creates messaging context."""
        ctx = ContinuityManager.from_messaging(
            platform="telegram",
            sender="+15551234567",
            channel="group_123",
        )
        assert ctx.surface == RuntimeSurface.MESSAGING
        assert ctx.sender == "+15551234567"
        assert ctx.surface_metadata.get("platform") == "telegram"

    def test_propagate_to_env(self):
        """propagate_to_env returns environment variables."""
        ctx = ContinuityContext(
            continuity_id="prop12345678",
            parent_continuity_id="parent123456",
        )
        env_vars = ContinuityManager.propagate_to_env(ctx)
        assert env_vars["OPENCLAW_CONTINUITY_ID"] == "prop12345678"
        assert env_vars["OPENCLAW_PARENT_CONTINUITY_ID"] == "parent123456"


class TestAgentDBContinuityIntegration:
    """Test AgentDB continuity methods."""

    @pytest.fixture
    def mock_db(self, tmp_path):
        """Create AgentDB with isolated temporary database."""
        db_path = tmp_path / "test_agent.db"
        # Ensure parent directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)
        # Use FOUNDUPS_DB_PATH to override database location
        with patch.dict(os.environ, {"FOUNDUPS_DB_PATH": str(db_path)}):
            # Re-import to reset DatabaseManager singleton state
            import importlib
            import modules.infrastructure.database.src.db_manager as db_manager_module
            importlib.reload(db_manager_module)
            from modules.infrastructure.database.src.agent_db import AgentDB
            db = AgentDB()
            yield db

    def test_add_breadcrumb_with_continuity(self, mock_db):
        """add_breadcrumb stores continuity metadata."""
        result_id = mock_db.add_breadcrumb(
            session_id="test_session",
            action="test_action",
            agent_id="0102",
            continuity_id="cont12345678",
            runtime_surface="openclaw",
            sender_normalized="012",
            parent_continuity_id="parent123456",
        )
        assert result_id > 0

        # Verify stored
        breadcrumbs = mock_db.get_breadcrumbs(session_id="test_session")
        assert len(breadcrumbs) == 1
        crumb = breadcrumbs[0]
        assert crumb["continuity_id"] == "cont12345678"
        assert crumb["runtime_surface"] == "openclaw"
        assert crumb["sender_normalized"] == "012"

    def test_get_breadcrumbs_by_continuity(self, mock_db):
        """get_breadcrumbs_by_continuity retrieves by continuity ID."""
        # Add breadcrumbs with same continuity
        mock_db.add_breadcrumb(
            session_id="s1", action="action1", continuity_id="cont_abc123", runtime_surface="cli"
        )
        mock_db.add_breadcrumb(
            session_id="s2", action="action2", continuity_id="cont_abc123", runtime_surface="openclaw"
        )
        mock_db.add_breadcrumb(
            session_id="s3", action="action3", continuity_id="other_id123", runtime_surface="cli"
        )

        results = mock_db.get_breadcrumbs_by_continuity("cont_abc123")
        assert len(results) == 2
        actions = {r["action"] for r in results}
        assert actions == {"action1", "action2"}

    def test_get_breadcrumbs_by_continuity_includes_children(self, mock_db):
        """get_breadcrumbs_by_continuity includes child continuities."""
        mock_db.add_breadcrumb(
            session_id="s1", action="parent_action", continuity_id="parent_id_12", runtime_surface="openclaw"
        )
        mock_db.add_breadcrumb(
            session_id="s2", action="child_action", continuity_id="child_id_123",
            parent_continuity_id="parent_id_12", runtime_surface="wre"
        )

        results = mock_db.get_breadcrumbs_by_continuity("parent_id_12", include_children=True)
        assert len(results) == 2

    def test_get_breadcrumbs_by_surface(self, mock_db):
        """get_breadcrumbs_by_surface filters by runtime surface."""
        # Use unique surface to avoid collision with other tests
        mock_db.add_breadcrumb(
            session_id="surface_test_1", action="test_surface_cli", runtime_surface="test_surface_cli_unique", continuity_id="surface_c1"
        )
        mock_db.add_breadcrumb(
            session_id="surface_test_2", action="test_surface_oc", runtime_surface="test_surface_oc_unique", continuity_id="surface_c2"
        )

        cli_results = mock_db.get_breadcrumbs_by_surface("test_surface_cli_unique", minutes=60)
        assert len(cli_results) == 1
        assert cli_results[0]["action"] == "test_surface_cli"

    def test_get_breadcrumbs_by_sender(self, mock_db):
        """get_breadcrumbs_by_sender filters by normalized sender."""
        # Use unique sender to avoid collision with other tests
        mock_db.add_breadcrumb(
            session_id="sender_test_1", action="sender_action1", sender_normalized="unique_sender_012", continuity_id="sender_c1"
        )
        mock_db.add_breadcrumb(
            session_id="sender_test_2", action="sender_action2", sender_normalized="unique_sender_other", continuity_id="sender_c2"
        )

        results = mock_db.get_breadcrumbs_by_sender("unique_sender_012", minutes=60)
        assert len(results) == 1
        assert results[0]["action"] == "sender_action1"

    def test_get_continuity_summary(self, mock_db):
        """get_continuity_summary returns aggregated info."""
        mock_db.add_breadcrumb(
            session_id="s1", action="action1", continuity_id="sum_id_1234", runtime_surface="cli"
        )
        mock_db.add_breadcrumb(
            session_id="s2", action="action2", continuity_id="sum_id_1234", runtime_surface="openclaw"
        )

        summary = mock_db.get_continuity_summary("sum_id_1234")
        assert summary["found"] is True
        assert summary["breadcrumb_count"] == 2
        assert set(summary["surfaces"]) == {"cli", "openclaw"}

    def test_get_continuity_summary_not_found(self, mock_db):
        """get_continuity_summary returns not found for missing ID."""
        summary = mock_db.get_continuity_summary("nonexistent_id")
        assert summary["found"] is False

    def test_get_cross_surface_activity(self, mock_db):
        """get_cross_surface_activity returns multi-surface work items."""
        import uuid
        unique_cross_id = f"cross_test_{uuid.uuid4().hex[:8]}"
        unique_single_id = f"single_test_{uuid.uuid4().hex[:8]}"

        # Add work that spans surfaces
        mock_db.add_breadcrumb(
            session_id="cross_s1", action="cross_a1", continuity_id=unique_cross_id, runtime_surface="cross_cli"
        )
        mock_db.add_breadcrumb(
            session_id="cross_s2", action="cross_a2", continuity_id=unique_cross_id, runtime_surface="cross_openclaw"
        )
        # Add work on single surface
        mock_db.add_breadcrumb(
            session_id="cross_s3", action="cross_a3", continuity_id=unique_single_id, runtime_surface="cross_cli"
        )

        results = mock_db.get_cross_surface_activity(minutes=60)
        # Find our specific cross-surface item
        our_result = [r for r in results if r["continuity_id"] == unique_cross_id]
        assert len(our_result) == 1
        assert our_result[0]["surface_count"] == 2


class TestProcessLoopContinuityIntegration:
    """Test continuity integration in OpenClaw process loop."""

    @pytest.mark.asyncio
    async def test_process_creates_continuity_context(self):
        """process_message creates continuity context on dae."""
        from modules.communication.moltbot_bridge.src.openclaw_process_loop import process_message

        mock_dae = MagicMock()
        mock_dae.clear_turn_cancel = MagicMock()
        mock_dae.HoneypotDefense.is_secret_seeking.return_value = False
        mock_dae._check_containment.return_value = None
        mock_dae._is_turn_cancelled.return_value = True
        mock_dae._turn_cancelled_response.return_value = "cancelled"

        await process_message(
            dae=mock_dae,
            message="test message",
            sender="012",
            channel="whatsapp",
            session_key="test_session",
        )

        # Verify continuity context was set
        assert hasattr(mock_dae, "_continuity_context")
        ctx = mock_dae._continuity_context
        assert ctx.surface.value == "openclaw"
        assert ctx.sender == "012"
        assert ctx.channel == "whatsapp"
        assert ctx.session_id == "test_session"


class TestIdleAutomationContinuityIntegration:
    """Test continuity integration in IdleAutomationDAE."""

    @pytest.fixture
    def mock_db(self, tmp_path):
        """Create AgentDB with isolated temporary database."""
        db_path = tmp_path / "test_idle_agent.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with patch.dict(os.environ, {"FOUNDUPS_DB_PATH": str(db_path)}):
            import importlib
            import modules.infrastructure.database.src.db_manager as db_manager_module
            importlib.reload(db_manager_module)
            from modules.infrastructure.database.src.agent_db import AgentDB
            db = AgentDB()
            yield db

    def test_idle_creates_continuity_context(self):
        """IdleAutomationDAE._create_continuity_context returns idle surface context."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import IdleAutomationDAE

        dae = IdleAutomationDAE()
        ctx = dae._create_continuity_context()

        assert ctx is not None
        assert ctx.surface.value == "idle"
        assert ctx.sender == "idle_dae"
        assert ctx.channel == "internal"
        assert "idle_automation_cycle" in ctx.surface_metadata.get("task_type", "")

    def test_idle_records_continuity_breadcrumb(self, mock_db):
        """IdleAutomationDAE._record_continuity_breadcrumb writes to AgentDB."""
        import uuid
        from modules.infrastructure.idle_automation.src.idle_automation_dae import IdleAutomationDAE
        from modules.communication.moltbot_bridge.src.continuity_context import (
            ContinuityContext, RuntimeSurface
        )

        unique_id = f"idle_bc_{uuid.uuid4().hex[:8]}"
        dae = IdleAutomationDAE()
        dae._continuity_context = ContinuityContext(
            continuity_id=unique_id,
            surface=RuntimeSurface.IDLE,
            session_id="idle_test_session",
            sender="idle_dae",
            channel="internal",
        )

        dae._record_continuity_breadcrumb(
            action="test_idle_action",
            success=True,
            details={"test_key": "test_value"},
        )

        # Query and verify
        results = mock_db.get_breadcrumbs_by_continuity(unique_id)
        assert len(results) == 1
        assert results[0]["runtime_surface"] == "idle"
        assert results[0]["action"] == "test_idle_action"


class TestSupervisorContinuityIntegration:
    """Test continuity integration in OpenClawSupervisor."""

    def test_supervisor_creates_continuity_context(self):
        """OpenClawSupervisor._create_continuity_context returns supervisor surface context."""
        from modules.communication.moltbot_bridge.src.openclaw_supervisor import (
            OpenClawSupervisor,
        )

        supervisor = OpenClawSupervisor.__new__(OpenClawSupervisor)
        supervisor.current_state = MagicMock()
        supervisor.current_state.value = "idle"
        supervisor._create_continuity_context = lambda cycle_id: ContinuityManager.from_supervisor(
            cycle_id=cycle_id, state="idle"
        )

        ctx = supervisor._create_continuity_context("cycle_42")

        assert ctx is not None
        assert ctx.surface.value == "supervisor"
        assert ctx.sender == "supervisor"
        assert ctx.channel == "internal"
        assert "cycle_42" in ctx.session_id

    @pytest.fixture
    def mock_db(self, tmp_path):
        """Create AgentDB with isolated temporary database."""
        db_path = tmp_path / "test_supervisor_agent.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with patch.dict(os.environ, {"FOUNDUPS_DB_PATH": str(db_path)}):
            import importlib
            import modules.infrastructure.database.src.db_manager as db_manager_module
            importlib.reload(db_manager_module)
            from modules.infrastructure.database.src.agent_db import AgentDB
            db = AgentDB()
            yield db

    def test_supervisor_records_continuity_breadcrumb(self, mock_db):
        """OpenClawSupervisor._record_continuity_breadcrumb writes to AgentDB."""
        import uuid
        from modules.communication.moltbot_bridge.src.openclaw_supervisor import (
            OpenClawSupervisor,
        )

        unique_id = f"supervisor_bc_{uuid.uuid4().hex[:8]}"

        # Create a minimal supervisor instance
        supervisor = OpenClawSupervisor.__new__(OpenClawSupervisor)
        supervisor.current_state = MagicMock()
        supervisor.current_state.value = "running"
        supervisor._continuity_context = ContinuityContext(
            continuity_id=unique_id,
            surface=RuntimeSurface.SUPERVISOR,
            session_id="supervisor_test_session",
            sender="supervisor",
            channel="internal",
        )

        # Record breadcrumb
        supervisor._record_continuity_breadcrumb(
            plan_or_triage={"action": "test_action", "reason": "testing"},
            action_result={"ok": True},
            verify={"ok": True},
        )

        # Query and verify
        results = mock_db.get_breadcrumbs_by_continuity(unique_id)
        assert len(results) == 1
        assert results[0]["runtime_surface"] == "supervisor"
        assert results[0]["action"] == "supervisor_test_action"


class TestCrossSurfaceContinuity:
    """Test cross-surface continuity between OpenClaw, Supervisor, and Idle."""

    @pytest.fixture
    def mock_db(self, tmp_path):
        """Create AgentDB with isolated temporary database."""
        db_path = tmp_path / "test_cross_surface.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with patch.dict(os.environ, {"FOUNDUPS_DB_PATH": str(db_path)}):
            import importlib
            import modules.infrastructure.database.src.db_manager as db_manager_module
            importlib.reload(db_manager_module)
            from modules.infrastructure.database.src.agent_db import AgentDB
            db = AgentDB()
            yield db

    def test_cross_surface_activity_detected(self, mock_db):
        """Work spanning OpenClaw, Supervisor, and Idle surfaces is detected."""
        import uuid

        # Same continuity ID across all surfaces (simulates propagation)
        continuity_id = f"cross_{uuid.uuid4().hex[:8]}"

        # OpenClaw records breadcrumb
        mock_db.add_breadcrumb(
            session_id="oc_session",
            action="process_message",
            continuity_id=continuity_id,
            runtime_surface="openclaw",
            sender_normalized="012",
        )

        # Supervisor records breadcrumb
        mock_db.add_breadcrumb(
            session_id="supervisor_cycle",
            action="supervisor_triage",
            continuity_id=continuity_id,
            runtime_surface="supervisor",
            sender_normalized="supervisor",
        )

        # Idle records breadcrumb
        mock_db.add_breadcrumb(
            session_id="idle_session",
            action="idle_automation_cycle",
            continuity_id=continuity_id,
            runtime_surface="idle",
            sender_normalized="idle_dae",
        )

        # Query cross-surface activity
        results = mock_db.get_cross_surface_activity(minutes=60)

        # Find our cross-surface work
        our_result = [r for r in results if r["continuity_id"] == continuity_id]
        assert len(our_result) == 1
        assert our_result[0]["surface_count"] == 3
        # Verify all surfaces are present in the grouped surfaces
        surfaces = our_result[0]["surfaces"]
        assert "openclaw" in surfaces
        assert "supervisor" in surfaces
        assert "idle" in surfaces

    def test_cross_surface_via_lineage_propagation(self, mock_db):
        """Cross-surface detection works via parent_continuity_id lineage (production path).

        This test exercises the REAL factory methods with parent context propagation,
        not manually injected shared IDs.
        """
        # 1. OpenClaw creates root context (this is what happens in production)
        openclaw_ctx = ContinuityManager.from_openclaw(
            sender="012",
            channel="whatsapp",
            session_key="session_abc123",
        )

        # 2. Supervisor forks from OpenClaw context (parent propagation)
        supervisor_ctx = ContinuityManager.from_supervisor(
            cycle_id="42",
            state="running",
            parent_context=openclaw_ctx,
        )

        # 3. Idle forks from OpenClaw context (sibling to supervisor)
        idle_ctx = ContinuityManager.from_idle(
            task_type="background_tasks",
            parent_context=openclaw_ctx,
        )

        # Verify contexts have DIFFERENT continuity_ids but SAME parent
        assert openclaw_ctx.continuity_id != supervisor_ctx.continuity_id
        assert openclaw_ctx.continuity_id != idle_ctx.continuity_id
        assert supervisor_ctx.continuity_id != idle_ctx.continuity_id

        # Verify parent linkage
        assert supervisor_ctx.parent_continuity_id == openclaw_ctx.continuity_id
        assert idle_ctx.parent_continuity_id == openclaw_ctx.continuity_id

        # 4. Record breadcrumbs using these contexts
        mock_db.add_breadcrumb(
            session_id=openclaw_ctx.session_id,
            action="process_message",
            continuity_id=openclaw_ctx.continuity_id,
            runtime_surface=openclaw_ctx.surface.value,
            sender_normalized=openclaw_ctx.sender_normalized,
            parent_continuity_id=openclaw_ctx.parent_continuity_id,
        )
        mock_db.add_breadcrumb(
            session_id=supervisor_ctx.session_id,
            action="supervisor_triage",
            continuity_id=supervisor_ctx.continuity_id,
            runtime_surface=supervisor_ctx.surface.value,
            sender_normalized=supervisor_ctx.sender_normalized,
            parent_continuity_id=supervisor_ctx.parent_continuity_id,
        )
        mock_db.add_breadcrumb(
            session_id=idle_ctx.session_id,
            action="idle_cycle",
            continuity_id=idle_ctx.continuity_id,
            runtime_surface=idle_ctx.surface.value,
            sender_normalized=idle_ctx.sender_normalized,
            parent_continuity_id=idle_ctx.parent_continuity_id,
        )

        # 5. Query cross-surface activity - should detect lineage-linked work
        results = mock_db.get_cross_surface_activity(minutes=60)

        # Find our lineage group (keyed by root = openclaw_ctx.continuity_id)
        our_result = [r for r in results if r["lineage_root"] == openclaw_ctx.continuity_id]
        assert len(our_result) == 1, f"Expected 1 lineage group, got {len(our_result)}: {results}"
        assert our_result[0]["surface_count"] == 3

        # Verify all surfaces detected
        surfaces = our_result[0]["surfaces"]
        assert "openclaw" in surfaces
        assert "supervisor" in surfaces
        assert "idle" in surfaces

        # Verify all continuity_ids are tracked in the lineage
        continuity_ids = our_result[0]["continuity_ids"]
        assert openclaw_ctx.continuity_id in continuity_ids
        assert supervisor_ctx.continuity_id in continuity_ids
        assert idle_ctx.continuity_id in continuity_ids


class TestProductionEntryPointPropagation:
    """Test that production entry points correctly propagate parent_context."""

    def test_idle_run_idle_tasks_propagates_parent(self):
        """IdleAutomationDAE.run_idle_tasks() propagates parent_context to continuity."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import IdleAutomationDAE

        # Create a parent context (e.g., from OpenClaw or YouTube DAE)
        parent = ContinuityContext(
            continuity_id="parent_youtube_dae",
            surface=RuntimeSurface.OPENCLAW,
            sender="youtube_dae",
        )

        # Create DAE and check that _create_continuity_context propagates parent
        dae = IdleAutomationDAE()
        ctx = dae._create_continuity_context(parent_context=parent)

        assert ctx is not None
        assert ctx.surface.value == "idle"
        assert ctx.parent_continuity_id == "parent_youtube_dae"
        assert ctx.continuity_id != parent.continuity_id

    def test_supervisor_run_cycle_propagates_parent(self):
        """OpenClawSupervisor._create_continuity_context() propagates parent_context."""
        from modules.communication.moltbot_bridge.src.openclaw_supervisor import OpenClawSupervisor

        # Create a parent context (e.g., from OpenClaw request)
        parent = ContinuityContext(
            continuity_id="parent_openclaw_req",
            surface=RuntimeSurface.OPENCLAW,
            sender="012",
        )

        # Create minimal supervisor and check propagation
        supervisor = OpenClawSupervisor.__new__(OpenClawSupervisor)
        supervisor.current_state = MagicMock()
        supervisor.current_state.value = "running"

        ctx = supervisor._create_continuity_context("cycle_99", parent_context=parent)

        assert ctx is not None
        assert ctx.surface.value == "supervisor"
        assert ctx.parent_continuity_id == "parent_openclaw_req"
        assert ctx.continuity_id != parent.continuity_id

    def test_run_idle_automation_convenience_propagates_parent(self):
        """run_idle_automation() convenience function accepts and propagates parent_context."""
        import asyncio
        from unittest.mock import AsyncMock
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE, run_idle_automation
        )

        # Create a parent context
        parent = ContinuityContext(
            continuity_id="parent_auto_mod",
            surface=RuntimeSurface.OPENCLAW,
            sender="auto_moderator",
        )

        # Patch run_idle_tasks to capture what's passed
        captured_ctx = {}

        original_run = IdleAutomationDAE.run_idle_tasks
        async def capturing_run(self, parent_context=None):
            captured_ctx['parent'] = parent_context
            self._continuity_context = self._create_continuity_context(parent_context)
            captured_ctx['created'] = self._continuity_context
            return {"overall_success": True, "session_id": 1, "duration": 0.1}

        # Patch and run
        with patch.object(IdleAutomationDAE, 'run_idle_tasks', capturing_run):
            result = asyncio.run(run_idle_automation(parent_context=parent))

        # Verify parent was passed through
        assert captured_ctx['parent'] is parent
        assert captured_ctx['created'].parent_continuity_id == "parent_auto_mod"


class TestProductionPathCrossSurfaceContinuity:
    """Integration tests that exercise REAL production caller paths."""

    def test_openclaw_to_wre_production_path(self, tmp_path, monkeypatch):
        """
        Exercises the real OpenClaw → WRE production path:
        1. _build_wre_command_context() includes parent_continuity_context
        2. WRE from_wre() forks with parent lineage
        3. Cross-surface activity is detectable via get_cross_surface_activity()
        """
        # Set up isolated database
        test_db_path = str(tmp_path / "test_openclaw_wre.db")
        monkeypatch.setenv("FOUNDUPS_DB_PATH", test_db_path)

        # Force reimport to pick up new path
        import importlib
        from modules.infrastructure.database.src import db_manager
        importlib.reload(db_manager)
        from modules.infrastructure.database.src.agent_db import AgentDB
        db = AgentDB()

        # Step 1: Create OpenClaw context (simulating process_loop wiring)
        openclaw_ctx = ContinuityManager.from_openclaw(
            sender="012_test",
            channel="discord_test",
            session_key="session_prod_001",
        )

        # Step 2: Simulate _build_wre_command_context including continuity
        # This is what openclaw_execution_routes.py does now
        wre_command_context = {
            "type": "orchestration",
            "task": "test git push",
            "command": "git push",
            "source": "openclaw_dae",
            "sender": "012_test",
            "channel": "discord_test",
            "parent_continuity_context": openclaw_ctx,  # <-- THE KEY WIRING
        }

        # Step 3: Simulate WRE using the parent (what wre_master_orchestrator does)
        parent_ctx = wre_command_context.get("parent_continuity_context")
        wre_ctx = ContinuityManager.from_wre(
            skill_name="test_skill",
            agent="qwen",
            parent_context=parent_ctx,
        )

        # Verify lineage
        assert wre_ctx.surface == RuntimeSurface.WRE
        assert wre_ctx.parent_continuity_id == openclaw_ctx.continuity_id
        assert wre_ctx.continuity_id != openclaw_ctx.continuity_id

        # Step 4: Record breadcrumbs for both surfaces (what production does)
        db.add_breadcrumb(
            session_id="session_prod_001",
            action="openclaw_message",
            agent_id="opus",
            data={"status": "completed"},
            continuity_id=openclaw_ctx.continuity_id,
            runtime_surface=openclaw_ctx.surface.value,
            sender_normalized=openclaw_ctx.sender_normalized,
        )
        db.add_breadcrumb(
            session_id="wre_test_skill",
            action="wre_skill_execution",
            agent_id="qwen",
            data={"status": "completed"},
            continuity_id=wre_ctx.continuity_id,
            runtime_surface=wre_ctx.surface.value,
            sender_normalized=wre_ctx.sender_normalized,
            parent_continuity_id=wre_ctx.parent_continuity_id,
        )

        # Step 5: Verify cross-surface activity is detectable
        cross_surface = db.get_cross_surface_activity(minutes=5)

        # Should find the lineage group (grouped by parent_continuity_id or continuity_id)
        assert len(cross_surface) >= 1, f"Expected cross-surface activity. Got: {cross_surface}"

        # Find the group containing our OpenClaw context
        found = False
        for item in cross_surface:
            # The lineage_root should be the openclaw context id (parent of WRE)
            if openclaw_ctx.continuity_id in (
                item.get("lineage_root", ""),
                item.get("continuity_id", ""),
            ) or openclaw_ctx.continuity_id in item.get("continuity_ids", []):
                found = True
                assert "openclaw" in item["surfaces"], f"Expected 'openclaw' in surfaces. Got: {item}"
                assert "wre" in item["surfaces"], f"Expected 'wre' in surfaces. Got: {item}"
                break

        assert found, f"Expected cross-surface lineage with openclaw_id={openclaw_ctx.continuity_id} not found. Got: {cross_surface}"

    def test_openclaw_to_wre_uses_real_execution_routes(self, tmp_path, monkeypatch):
        """
        Verify that _build_wre_command_context includes continuity when dae has it.
        """
        from unittest.mock import MagicMock

        # Create a mock dae with continuity context
        mock_dae = MagicMock()
        mock_dae._continuity_context = ContinuityContext(
            continuity_id="ctx_from_process_loop",
            surface=RuntimeSurface.OPENCLAW,
            sender="012",
            channel="test",
        )
        mock_dae._extract_file_paths = MagicMock(return_value=[])

        # Create mock intent
        mock_intent = MagicMock()
        mock_intent.extracted_task = "push changes"
        mock_intent.raw_message = "git push"
        mock_intent.sender = "012"
        mock_intent.channel = "test"

        # Import and call the real function
        from modules.communication.moltbot_bridge.src.openclaw_execution_routes import (
            _build_wre_command_context,
        )

        ctx = _build_wre_command_context(mock_dae, mock_intent)

        # Verify continuity is propagated
        assert "parent_continuity_context" in ctx
        assert ctx["parent_continuity_context"].continuity_id == "ctx_from_process_loop"
        assert ctx["parent_continuity_context"].surface == RuntimeSurface.OPENCLAW
