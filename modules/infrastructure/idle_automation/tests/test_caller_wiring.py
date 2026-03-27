#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for auto_moderator -> idle_automation caller wiring.

Validates that the production caller path propagates continuity
context (triggering_session) so background idle work can be
correlated to the originating livechat/stream session.
"""

from __future__ import annotations

import gc
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# run_idle_automation convenience function wiring
# ---------------------------------------------------------------------------


class TestRunIdleAutomationWiring:
    """run_idle_automation() propagates triggering_session to the DAE."""

    @pytest.mark.asyncio
    async def test_triggering_session_stored_before_run(self):
        """When triggering_session is passed, set_triggering_session() is
        called before run_idle_tasks()."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            run_idle_automation,
        )

        call_order = []

        with patch(
            "modules.infrastructure.idle_automation.src.idle_automation_dae.IdleAutomationDAE"
        ) as MockDAE:
            mock_dae = MagicMock()

            def record_set(session_id):
                call_order.append(("set_triggering_session", session_id))

            async def record_run(**kwargs):
                call_order.append(("run_idle_tasks", kwargs))
                return {"overall_success": True, "duration": 0.1}

            mock_dae.set_triggering_session = record_set
            mock_dae.run_idle_tasks = record_run
            MockDAE.return_value = mock_dae

            result = await run_idle_automation(triggering_session="video_abc123")

        assert result["overall_success"] is True
        assert len(call_order) == 2
        assert call_order[0] == ("set_triggering_session", "video_abc123")
        assert call_order[1][0] == "run_idle_tasks"
        assert call_order[1][1].get("parent_context") is None

    @pytest.mark.asyncio
    async def test_no_triggering_session_when_none(self):
        """When triggering_session is None, set_triggering_session() is NOT called."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            run_idle_automation,
        )

        with patch(
            "modules.infrastructure.idle_automation.src.idle_automation_dae.IdleAutomationDAE"
        ) as MockDAE:
            mock_dae = MagicMock()
            mock_dae.set_triggering_session = MagicMock()

            async def fake_run(**kwargs):
                return {"overall_success": True, "duration": 0.1}

            mock_dae.run_idle_tasks = fake_run
            MockDAE.return_value = mock_dae

            await run_idle_automation(triggering_session=None)

        mock_dae.set_triggering_session.assert_not_called()

    @pytest.mark.asyncio
    async def test_parent_context_takes_precedence_over_triggering_session(self):
        """When parent_context is provided, triggering_session is ignored."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            run_idle_automation,
        )
        from modules.communication.moltbot_bridge.src.continuity_context import (
            ContinuityContext,
            RuntimeSurface,
        )

        parent = ContinuityContext(
            continuity_id="explicit_parent",
            surface=RuntimeSurface.OPENCLAW,
        )

        with patch(
            "modules.infrastructure.idle_automation.src.idle_automation_dae.IdleAutomationDAE"
        ) as MockDAE:
            mock_dae = MagicMock()
            mock_dae.set_triggering_session = MagicMock()

            async def fake_run(**kwargs):
                return {"overall_success": True, "duration": 0.1}

            mock_dae.run_idle_tasks = fake_run
            MockDAE.return_value = mock_dae

            await run_idle_automation(
                parent_context=parent,
                triggering_session="video_should_be_ignored",
            )

        # set_triggering_session should NOT be called when parent_context exists
        mock_dae.set_triggering_session.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_string_triggering_session_not_stored(self):
        """Empty string triggering_session is treated as absent."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            run_idle_automation,
        )

        with patch(
            "modules.infrastructure.idle_automation.src.idle_automation_dae.IdleAutomationDAE"
        ) as MockDAE:
            mock_dae = MagicMock()
            mock_dae.set_triggering_session = MagicMock()

            async def fake_run(**kwargs):
                return {"overall_success": True, "duration": 0.1}

            mock_dae.run_idle_tasks = fake_run
            MockDAE.return_value = mock_dae

            await run_idle_automation(triggering_session="")

        mock_dae.set_triggering_session.assert_not_called()


# ---------------------------------------------------------------------------
# Auto Moderator caller site — source wiring
# ---------------------------------------------------------------------------


class TestAutoModeratorCallerSite:
    """Verify AutoModeratorDAE passes _last_stream_id to run_idle_automation."""

    def test_last_stream_id_propagated(self):
        """The production call site passes self._last_stream_id as triggering_session."""
        from pathlib import Path

        source = Path(
            "modules/communication/livechat/src/auto_moderator_dae.py"
        ).read_text(encoding="utf-8")

        assert "triggering_session=self._last_stream_id" in source, (
            "auto_moderator_dae.py must pass self._last_stream_id as "
            "triggering_session to run_idle_automation()"
        )

    def test_breadcrumb_written_before_idle_handoff(self):
        """The production call site writes a breadcrumb with _last_stream_id
        as session_id BEFORE calling run_idle_automation."""
        from pathlib import Path

        source = Path(
            "modules/communication/livechat/src/auto_moderator_dae.py"
        ).read_text(encoding="utf-8")

        # Breadcrumb write must appear
        assert "stream_ended_idle_handoff" in source, (
            "auto_moderator_dae.py must write a breadcrumb before idle handoff"
        )
        assert "session_id=self._last_stream_id" in source, (
            "breadcrumb must use _last_stream_id as session_id"
        )

        # Breadcrumb must come BEFORE run_idle_automation
        bc_pos = source.index("stream_ended_idle_handoff")
        idle_pos = source.index("run_idle_automation")
        assert bc_pos < idle_pos, (
            "breadcrumb must be written before run_idle_automation is called"
        )


# ---------------------------------------------------------------------------
# Production-path integration: breadcrumb -> recovery -> correlated lineage
# ---------------------------------------------------------------------------


class TestBreadcrumbRecoveryIntegration:
    """Prove that a livechat breadcrumb written with _last_stream_id can be
    recovered by idle DAE's _try_recover_origin_continuity(), producing
    real cross-surface lineage."""

    @pytest.fixture()
    def mock_db(self, tmp_path):
        """Provide a real AgentDB with a temp SQLite database."""
        import os
        os.environ["AGENT_DB_PATH"] = str(tmp_path / "test_agent.db")
        from modules.infrastructure.database.src.agent_db import AgentDB
        db = AgentDB()
        yield db
        # Cleanup
        del db
        gc.collect()
        os.environ.pop("AGENT_DB_PATH", None)

    def test_idle_recovers_livechat_breadcrumb(self, mock_db):
        """End-to-end: write breadcrumb with video_id session -> idle recovery
        finds it and produces a parent-linked context."""
        from modules.communication.moltbot_bridge.src.continuity_context import (
            ContinuityManager,
            _derive_continuity_from_session,
        )
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        video_id = f"video_{uuid.uuid4().hex[:8]}"
        stream_continuity_id = _derive_continuity_from_session(video_id)

        # 1. Write the breadcrumb (same as auto_moderator caller site)
        mock_db.add_breadcrumb(
            session_id=video_id,
            action="stream_ended_idle_handoff",
            agent_id="auto_moderator_dae",
            continuity_id=stream_continuity_id,
            runtime_surface="openclaw",
            sender_normalized="livechat",
            data={"video_id": video_id},
        )

        # 2. Create idle DAE and set triggering session (same as run_idle_automation)
        dae = IdleAutomationDAE()
        dae.set_triggering_session(video_id)

        # 3. Recovery should find the breadcrumb and return a context
        recovered = dae._try_recover_origin_continuity()
        assert recovered is not None, (
            f"Expected to recover origin continuity for session {video_id}"
        )
        assert recovered.continuity_id == stream_continuity_id

        # 4. Fork an idle context from recovered origin — proves real lineage
        idle_ctx = ContinuityManager.from_idle(
            task_type="background_tasks",
            parent_context=recovered,
        )
        assert idle_ctx.parent_continuity_id == stream_continuity_id
        assert idle_ctx.continuity_id != stream_continuity_id  # new ID

    def test_no_false_lineage_without_breadcrumb(self, mock_db):
        """When no breadcrumb exists for the video_id, idle creates
        an independent root — no false correlation."""
        from modules.infrastructure.idle_automation.src.idle_automation_dae import (
            IdleAutomationDAE,
        )

        video_id = f"video_{uuid.uuid4().hex[:8]}"

        dae = IdleAutomationDAE()
        dae.set_triggering_session(video_id)

        # Recovery should return None (no breadcrumb for this video)
        recovered = dae._try_recover_origin_continuity()
        assert recovered is None, (
            "Should not produce lineage when no breadcrumb exists"
        )
