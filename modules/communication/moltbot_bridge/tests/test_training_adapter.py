#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the OpenClaw training adapter.

Validates deterministic command matching and status/batch responses.
"""

from __future__ import annotations

import asyncio
import io
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from modules.communication.moltbot_bridge.src.training_adapter import (
    try_training_command,
    _training_status,
    _trigger_training_batch,
)


# ---------------------------------------------------------------------------
# Command matching
# ---------------------------------------------------------------------------


class TestCommandMatching:
    """try_training_command returns a response for training commands, None otherwise."""

    @pytest.mark.parametrize(
        "message",
        [
            "training status",
            "training progress",
            "training metrics",
            "show training status",
            "get training progress",
            "check training metrics",
        ],
    )
    @pytest.mark.asyncio
    async def test_status_commands_match(self, message):
        with patch(
            "modules.communication.moltbot_bridge.src.training_adapter._training_status",
            return_value="mocked",
        ):
            result = await try_training_command(message)
            assert result is not None

    @pytest.mark.parametrize(
        "message",
        [
            "start training batch",
            "run training batch",
            "execute pattern training",
            "trigger batch training",
            "run pattern training",
        ],
    )
    @pytest.mark.asyncio
    async def test_batch_commands_match(self, message):
        with patch(
            "modules.communication.moltbot_bridge.src.training_adapter._trigger_training_batch",
            new_callable=AsyncMock,
            return_value="mocked",
        ):
            result = await try_training_command(message)
            assert result is not None

    @pytest.mark.parametrize(
        "message",
        [
            "is training due",
            "training due",
            "is training needed",
            "training pending",
        ],
    )
    @pytest.mark.asyncio
    async def test_due_commands_match(self, message):
        with patch(
            "modules.communication.moltbot_bridge.src.training_adapter._training_status",
            return_value="mocked",
        ):
            result = await try_training_command(message)
            assert result is not None

    @pytest.mark.parametrize(
        "message",
        [
            "hello",
            "what is the weather",
            "show schedules",
            "search for training data",
            "status of the system",
            "",
        ],
    )
    @pytest.mark.asyncio
    async def test_non_training_commands_return_none(self, message):
        assert await try_training_command(message) is None

    # --- false-positive regression (Finding 2) ---

    @pytest.mark.parametrize(
        "message",
        [
            "search training metrics",
            "find training status in memory",
            "search training batch results",
            "look up training progress from last week",
            "what training metrics are available",
        ],
    )
    @pytest.mark.asyncio
    async def test_search_phrasing_does_not_match(self, message):
        """Generic search queries that mention training must NOT trigger."""
        assert await try_training_command(message) is None


# ---------------------------------------------------------------------------
# Status reporting
# ---------------------------------------------------------------------------


class TestTrainingStatus:
    """_training_status returns correct state for each condition."""

    def test_disabled_when_env_off(self, monkeypatch):
        monkeypatch.setenv("AUTO_PATTERN_TRAINING", "0")
        result = _training_status()
        assert "DISABLED" in result

    def test_unavailable_when_pattern_memory_fails(self, monkeypatch):
        monkeypatch.setenv("AUTO_PATTERN_TRAINING", "1")
        with patch(
            "holo_index.qwen_advisor.pattern_memory.PatternMemory",
            side_effect=RuntimeError("no chromadb"),
        ):
            result = _training_status()
            assert "UNAVAILABLE" in result

    def test_complete_when_checkpoint_at_end(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AUTO_PATTERN_TRAINING", "1")

        # Create a real temp file with 1000 lines
        fake_txt = tmp_path / "012.txt"
        fake_txt.write_text("\n".join(f"line {i}" for i in range(1000)))

        mock_memory = MagicMock()
        mock_memory.get_stats.return_value = {
            "total_patterns": 42,
            "checkpoint_line": 1000,
            "sources": {"mcp_tool_executor": 30, "012_txt": 12},
            "verification_rate": 0.85,
            "verified_count": 36,
        }

        import modules.communication.moltbot_bridge.src.training_adapter as mod

        original_txt = mod._012_TXT
        try:
            mod._012_TXT = fake_txt
            with patch(
                "holo_index.qwen_advisor.pattern_memory.PatternMemory",
                return_value=mock_memory,
            ):
                result = _training_status()
                assert "COMPLETE" in result
                assert "42" in result  # pattern count
                assert "85" in result  # verification rate
        finally:
            mod._012_TXT = original_txt

    def test_due_when_lines_remaining(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AUTO_PATTERN_TRAINING", "1")

        # Create a real temp file with 2000 lines
        fake_txt = tmp_path / "012.txt"
        fake_txt.write_text("\n".join(f"line {i}" for i in range(2000)))

        mock_memory = MagicMock()
        mock_memory.get_stats.return_value = {
            "total_patterns": 10,
            "checkpoint_line": 500,
            "sources": {},
            "verification_rate": 0.5,
            "verified_count": 5,
        }

        import modules.communication.moltbot_bridge.src.training_adapter as mod

        original_txt = mod._012_TXT
        try:
            mod._012_TXT = fake_txt
            with patch(
                "holo_index.qwen_advisor.pattern_memory.PatternMemory",
                return_value=mock_memory,
            ):
                result = _training_status()
                assert "DUE" in result
                assert "1500" in result  # remaining lines
                assert "start training batch" in result.lower()
        finally:
            mod._012_TXT = original_txt


# ---------------------------------------------------------------------------
# Batch trigger (async)
# ---------------------------------------------------------------------------


class TestTriggerBatch:
    """_trigger_training_batch returns correct state for each outcome."""

    @pytest.mark.asyncio
    async def test_disabled_when_env_off(self, monkeypatch):
        monkeypatch.setenv("AUTO_PATTERN_TRAINING", "0")
        result = await _trigger_training_batch()
        assert "not started" in result.lower() or "disabled" in result.lower()

    @pytest.mark.asyncio
    async def test_success(self, monkeypatch):
        monkeypatch.setenv("AUTO_PATTERN_TRAINING", "1")
        mock_result = {
            "success": True,
            "patterns_stored": 5,
            "lines_processed": 1000,
        }

        mock_dae = MagicMock()

        async def fake_training():
            return mock_result

        mock_dae._execute_pattern_training = fake_training

        with patch(
            "modules.infrastructure.idle_automation.src.idle_automation_dae.IdleAutomationDAE",
            return_value=mock_dae,
        ):
            result = await _trigger_training_batch()
            assert "complete" in result.lower()
            assert "5" in result  # patterns stored

    @pytest.mark.asyncio
    async def test_already_complete(self, monkeypatch):
        monkeypatch.setenv("AUTO_PATTERN_TRAINING", "1")
        mock_result = {
            "success": False,
            "error": "Already processed (checkpoint: 5000, total: 5000)",
        }

        mock_dae = MagicMock()

        async def fake_training():
            return mock_result

        mock_dae._execute_pattern_training = fake_training

        with patch(
            "modules.infrastructure.idle_automation.src.idle_automation_dae.IdleAutomationDAE",
            return_value=mock_dae,
        ):
            result = await _trigger_training_batch()
            assert "already complete" in result.lower()

    @pytest.mark.asyncio
    async def test_error(self, monkeypatch):
        monkeypatch.setenv("AUTO_PATTERN_TRAINING", "1")
        with patch(
            "modules.infrastructure.idle_automation.src.idle_automation_dae.IdleAutomationDAE",
            side_effect=RuntimeError("import failed"),
        ):
            result = await _trigger_training_batch()
            assert "failed" in result.lower()


# ---------------------------------------------------------------------------
# Async integration through execute_query (Finding 1)
# ---------------------------------------------------------------------------


class TestAsyncIntegration:
    """Verify training adapter works when called from async execute_query."""

    @pytest.mark.asyncio
    async def test_batch_trigger_from_running_event_loop(self, monkeypatch):
        """The old asyncio.run() would fail here; await must work."""
        monkeypatch.setenv("AUTO_PATTERN_TRAINING", "1")
        mock_result = {
            "success": True,
            "patterns_stored": 3,
            "lines_processed": 500,
        }

        mock_dae = MagicMock()

        async def fake_training():
            return mock_result

        mock_dae._execute_pattern_training = fake_training

        with patch(
            "modules.infrastructure.idle_automation.src.idle_automation_dae.IdleAutomationDAE",
            return_value=mock_dae,
        ):
            # Simulate the execute_query call path: already inside event loop
            result = await try_training_command("start training batch")
            assert result is not None
            assert "complete" in result.lower()
            assert "3" in result
