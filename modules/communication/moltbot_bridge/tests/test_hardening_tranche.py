#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for hardening tranche: SOURCE tier, rate limiting, COMMAND fallback.

WSP Compliance:
  WSP 71  : Secrets Management - Permission fail-closed
  WSP 95  : WRE Skills Wardrobe Protocol - Security gates

Test Coverage:
  1. SOURCE tier enforcement via AgentPermissionManager
  2. Webhook rate limiting (token bucket)
  3. COMMAND graceful degradation when WRE unavailable
"""

import asyncio
import time
from unittest.mock import ANY, MagicMock, patch, AsyncMock

import pytest


# ---------------------------------------------------------------------------
# SOURCE Tier Enforcement Tests
# ---------------------------------------------------------------------------


def test_source_tier_blocked_when_permission_manager_unavailable():
    """SOURCE tier: blocked when permission manager not loaded (fail-closed)."""
    from modules.communication.moltbot_bridge.src.openclaw_dae import (
        OpenClawDAE, AutonomyTier, OpenClawIntent, IntentCategory
    )

    dae = OpenClawDAE()

    intent = OpenClawIntent(
        raw_message="edit source file",
        sender="undaodu",
        channel="test",
        session_key="test",
        category=IntentCategory.COMMAND,
        confidence=0.9,
        is_authorized_commander=True,
        extracted_task="edit source file",
        target_domain="wre",
    )

    # Mock the permissions property to return None (simulating unavailable manager)
    with patch.object(type(dae), 'permissions', new_callable=lambda: property(lambda self: None)):
        granted, reason = dae._check_source_permission(intent)

    assert granted is False
    assert "unavailable" in reason.lower()


def test_source_tier_blocked_when_permission_check_fails():
    """SOURCE tier: blocked when permission check returns denied."""
    from modules.communication.moltbot_bridge.src.openclaw_dae import (
        OpenClawDAE, AutonomyTier, OpenClawIntent, IntentCategory
    )

    dae = OpenClawDAE()

    # Mock permission manager that denies
    mock_result = MagicMock()
    mock_result.allowed = False
    mock_result.reason = "Agent not in allowlist"

    mock_permissions = MagicMock()
    mock_permissions.check_permission.return_value = mock_result
    dae._permissions = mock_permissions

    intent = OpenClawIntent(
        raw_message="edit source file",
        sender="undaodu",
        channel="test",
        session_key="test",
        category=IntentCategory.COMMAND,
        confidence=0.9,
        is_authorized_commander=True,
        extracted_task="edit source file",
        target_domain="wre",
    )

    granted, reason = dae._check_source_permission(intent)

    assert granted is False
    assert "not in allowlist" in reason


def test_source_tier_allowed_when_permission_check_passes():
    """SOURCE tier: allowed when permission check returns granted."""
    from modules.communication.moltbot_bridge.src.openclaw_dae import (
        OpenClawDAE, OpenClawIntent, IntentCategory
    )

    dae = OpenClawDAE()

    # Mock permission manager that grants
    mock_result = MagicMock()
    mock_result.allowed = True
    mock_result.reason = "granted"

    mock_permissions = MagicMock()
    mock_permissions.check_permission.return_value = mock_result
    dae._permissions = mock_permissions

    intent = OpenClawIntent(
        raw_message="edit source file",
        sender="undaodu",
        channel="test",
        session_key="test",
        category=IntentCategory.COMMAND,
        confidence=0.9,
        is_authorized_commander=True,
        extracted_task="edit source file",
        target_domain="wre",
    )

    granted, reason = dae._check_source_permission(intent)

    assert granted is True
    assert "granted" in reason.lower()


def test_source_tier_blocked_on_permission_check_exception():
    """SOURCE tier: blocked when permission check throws exception (fail-closed)."""
    from modules.communication.moltbot_bridge.src.openclaw_dae import (
        OpenClawDAE, OpenClawIntent, IntentCategory
    )

    dae = OpenClawDAE()

    # Mock permission manager that throws
    mock_permissions = MagicMock()
    mock_permissions.check_permission.side_effect = RuntimeError("Connection failed")
    dae._permissions = mock_permissions

    intent = OpenClawIntent(
        raw_message="edit source file",
        sender="undaodu",
        channel="test",
        session_key="test",
        category=IntentCategory.COMMAND,
        confidence=0.9,
        is_authorized_commander=True,
        extracted_task="edit source file",
        target_domain="wre",
    )

    granted, reason = dae._check_source_permission(intent)

    assert granted is False
    assert "error" in reason.lower()


def test_permission_denied_event_emitted():
    """Permission denied event: emitted on SOURCE denial."""
    from modules.communication.moltbot_bridge.src.openclaw_dae import (
        OpenClawDAE, AutonomyTier, OpenClawIntent, IntentCategory
    )

    dae = OpenClawDAE()

    intent = OpenClawIntent(
        raw_message="edit source file",
        sender="undaodu",
        channel="test",
        session_key="test",
        category=IntentCategory.COMMAND,
        confidence=0.9,
        is_authorized_commander=True,
        extracted_task="edit source file",
        target_domain="wre",
    )

    # Should not raise, just emit event
    dae._emit_permission_denied_event(intent, AutonomyTier.SOURCE, "test reason")

    # Verify dedupe history populated
    assert hasattr(dae, "_permission_denied_history")
    assert len(dae._permission_denied_history) == 1


def test_permission_denied_event_deduped():
    """Permission denied event: duplicate within window suppressed."""
    from modules.communication.moltbot_bridge.src.openclaw_dae import (
        OpenClawDAE, AutonomyTier, OpenClawIntent, IntentCategory
    )

    dae = OpenClawDAE()

    intent = OpenClawIntent(
        raw_message="edit source file",
        sender="undaodu",
        channel="test",
        session_key="test",
        category=IntentCategory.COMMAND,
        confidence=0.9,
        is_authorized_commander=True,
        extracted_task="edit source file",
        target_domain="wre",
    )

    # Emit twice
    dae._emit_permission_denied_event(intent, AutonomyTier.SOURCE, "test reason")
    dae._emit_permission_denied_event(intent, AutonomyTier.SOURCE, "test reason")

    # Should still be just 1 entry (second was deduped)
    assert len(dae._permission_denied_history) == 1


# ---------------------------------------------------------------------------
# Webhook Rate Limiting Tests
# ---------------------------------------------------------------------------


def test_token_bucket_allows_within_capacity():
    """Token bucket: allows requests within capacity."""
    from modules.communication.moltbot_bridge.src.webhook_receiver import TokenBucket

    bucket = TokenBucket(rate=1.0, capacity=5.0)

    # Should allow 5 requests immediately
    for _ in range(5):
        assert bucket.consume() is True

    # 6th should be blocked
    assert bucket.consume() is False


def test_token_bucket_refills_over_time():
    """Token bucket: refills tokens over time."""
    from modules.communication.moltbot_bridge.src.webhook_receiver import TokenBucket

    bucket = TokenBucket(rate=10.0, capacity=5.0)  # 10 tokens/sec

    # Consume all tokens
    for _ in range(5):
        bucket.consume()

    # Wait 0.5 sec (should add 5 tokens)
    time.sleep(0.5)

    # Should allow at least some requests
    assert bucket.consume() is True


def test_rate_limiter_blocks_sender_exceeding_limit():
    """Rate limiter: blocks sender exceeding per-sender limit."""
    from modules.communication.moltbot_bridge.src.webhook_receiver import WebhookRateLimiter

    limiter = WebhookRateLimiter()
    limiter.sender_capacity = 2  # Only 2 burst allowed

    # First 2 should pass
    allowed1, _ = limiter.check("sender1", "channel1")
    allowed2, _ = limiter.check("sender1", "channel1")
    assert allowed1 is True
    assert allowed2 is True

    # 3rd should be blocked
    allowed3, reason = limiter.check("sender1", "channel1")
    assert allowed3 is False
    assert "sender rate limit" in reason


def test_rate_limiter_allows_different_senders():
    """Rate limiter: different senders have separate buckets."""
    from modules.communication.moltbot_bridge.src.webhook_receiver import WebhookRateLimiter

    limiter = WebhookRateLimiter()
    limiter.sender_capacity = 1

    # Exhaust sender1's bucket
    limiter.check("sender1", "channel1")
    allowed1, _ = limiter.check("sender1", "channel1")
    assert allowed1 is False

    # sender2 should still be allowed
    allowed2, _ = limiter.check("sender2", "channel1")
    assert allowed2 is True


def test_rate_limiter_blocks_channel_exceeding_limit():
    """Rate limiter: blocks when channel limit exceeded."""
    from modules.communication.moltbot_bridge.src.webhook_receiver import WebhookRateLimiter

    limiter = WebhookRateLimiter()
    limiter.sender_capacity = 100  # High sender limit
    limiter.channel_capacity = 2  # Low channel limit

    # First 2 pass
    limiter.check("sender1", "channel1")
    limiter.check("sender2", "channel1")

    # 3rd blocked by channel limit (different sender)
    allowed, reason = limiter.check("sender3", "channel1")
    assert allowed is False
    assert "channel rate limit" in reason


def test_rate_limiting_can_be_disabled():
    """Rate limiting: can be disabled via env var."""
    import os
    from modules.communication.moltbot_bridge.src.webhook_receiver import is_rate_limiting_enabled

    original = os.environ.get("OPENCLAW_RATE_LIMIT_ENABLED")
    try:
        os.environ["OPENCLAW_RATE_LIMIT_ENABLED"] = "0"
        assert is_rate_limiting_enabled() is False

        os.environ["OPENCLAW_RATE_LIMIT_ENABLED"] = "1"
        assert is_rate_limiting_enabled() is True
    finally:
        if original is None:
            os.environ.pop("OPENCLAW_RATE_LIMIT_ENABLED", None)
        else:
            os.environ["OPENCLAW_RATE_LIMIT_ENABLED"] = original


# ---------------------------------------------------------------------------
# COMMAND Graceful Degradation Tests
# ---------------------------------------------------------------------------


def test_command_returns_advisory_when_wre_unavailable():
    """COMMAND: returns advisory fallback when WRE is None."""
    from modules.communication.moltbot_bridge.src.openclaw_dae import (
        OpenClawDAE, OpenClawIntent, IntentCategory
    )

    dae = OpenClawDAE()

    intent = OpenClawIntent(
        raw_message="run tests",
        sender="undaodu",
        channel="test",
        session_key="test",
        category=IntentCategory.COMMAND,
        confidence=0.9,
        is_authorized_commander=True,
        extracted_task="run tests",
        target_domain="wre",
    )

    # Mock the wre property to return None (simulating WRE unavailable)
    async def _run():
        with patch.object(type(dae), 'wre', new_callable=lambda: property(lambda self: None)):
            return await dae._execute_command(intent)

    result = asyncio.run(_run())

    assert "Advisory Mode" in result
    assert "WRE unavailable" in result
    assert "run tests" in result


def test_command_returns_advisory_on_wre_exception():
    """COMMAND: returns advisory fallback when WRE throws exception."""
    from modules.communication.moltbot_bridge.src.openclaw_dae import (
        OpenClawDAE, OpenClawIntent, IntentCategory
    )

    dae = OpenClawDAE()

    # Mock WRE that throws
    mock_wre = MagicMock()
    mock_wre.execute.side_effect = RuntimeError("WRE crashed")
    dae._wre = mock_wre

    intent = OpenClawIntent(
        raw_message="run tests",
        sender="undaodu",
        channel="test",
        session_key="test",
        category=IntentCategory.COMMAND,
        confidence=0.9,
        is_authorized_commander=True,
        extracted_task="run tests",
        target_domain="wre",
    )

    async def _run():
        return await dae._execute_command(intent)

    result = asyncio.run(_run())

    assert "Advisory Mode" in result
    assert "WRE crashed" in result


def test_command_advisory_fallback_includes_options():
    """COMMAND advisory: includes actionable options."""
    from modules.communication.moltbot_bridge.src.openclaw_dae import (
        OpenClawDAE, OpenClawIntent, IntentCategory
    )

    dae = OpenClawDAE()

    intent = OpenClawIntent(
        raw_message="deploy to production",
        sender="undaodu",
        channel="test",
        session_key="test",
        category=IntentCategory.COMMAND,
        confidence=0.9,
        is_authorized_commander=True,
        extracted_task="deploy to production",
        target_domain="wre",
    )

    result = dae._command_advisory_fallback(intent)

    assert "CLI execution" in result
    assert "Retry later" in result
    assert "Query mode" in result
    assert "deploy to production" in result


def test_command_advisory_fallback_includes_error_detail():
    """COMMAND advisory: includes error detail when provided."""
    from modules.communication.moltbot_bridge.src.openclaw_dae import (
        OpenClawDAE, OpenClawIntent, IntentCategory
    )

    dae = OpenClawDAE()

    intent = OpenClawIntent(
        raw_message="run tests",
        sender="undaodu",
        channel="test",
        session_key="test",
        category=IntentCategory.COMMAND,
        confidence=0.9,
        is_authorized_commander=True,
        extracted_task="run tests",
        target_domain="wre",
    )

    result = dae._command_advisory_fallback(intent, error="Connection refused")

    assert "Error detail" in result
    assert "Connection refused" in result


def test_command_executes_normally_when_wre_available():
    """COMMAND: executes normally when WRE is available and succeeds."""
    from modules.communication.moltbot_bridge.src.openclaw_dae import (
        OpenClawDAE, OpenClawIntent, IntentCategory
    )

    dae = OpenClawDAE()

    # Mock WRE that succeeds
    mock_wre = MagicMock()
    mock_wre.execute.return_value = "Task completed successfully"
    dae._wre = mock_wre

    intent = OpenClawIntent(
        raw_message="run tests",
        sender="undaodu",
        channel="test",
        session_key="test",
        category=IntentCategory.COMMAND,
        confidence=0.9,
        is_authorized_commander=True,
        extracted_task="run tests",
        target_domain="wre",
    )

    async def _run():
        return await dae._execute_command(intent)

    result = asyncio.run(_run())

    assert "Command executed via WRE" in result
    assert "Task completed successfully" in result
    assert "Advisory Mode" not in result


def test_command_prefers_execute_skill_when_existing_wre_skill_available():
    """COMMAND: prefers execute_skill() when an existing WRE skill is available."""
    from modules.communication.moltbot_bridge.src.openclaw_dae import (
        OpenClawDAE, OpenClawIntent, IntentCategory
    )

    dae = OpenClawDAE()

    mock_loader = MagicMock()
    mock_loader.has_skill.side_effect = lambda name: name in {"qwen_gitpush", "openclaw_executor"}
    mock_loader.registry = {
        "skills": {
            "qwen_gitpush": {"agents": ["qwen", "gemma"]},
            "openclaw_executor": {"agents": ["qwen"]},
        }
    }

    mock_wre = MagicMock()
    mock_wre.skills_loader = mock_loader
    mock_wre.find_skill_candidates.return_value = ["qwen_gitpush", "openclaw_executor"]
    mock_wre.select_skill_tot.return_value = ("qwen_gitpush", {"tot_confidence": 0.91})
    mock_wre.execute_skill.return_value = {"output": "Skill pipeline completed", "success": True}
    mock_wre.execute.return_value = "legacy execute path"
    dae._wre = mock_wre

    intent = OpenClawIntent(
        raw_message="git commit and push changes",
        sender="undaodu",
        channel="test",
        session_key="test",
        category=IntentCategory.COMMAND,
        confidence=0.9,
        is_authorized_commander=True,
        extracted_task="git commit and push changes",
        target_domain="wre",
    )

    async def _run():
        return await dae._execute_command(intent)

    result = asyncio.run(_run())

    assert "qwen_gitpush" in result
    assert "Skill pipeline completed" in result
    mock_wre.execute_skill.assert_called_once_with(
        skill_name="qwen_gitpush",
        agent="qwen",
        input_context=ANY,
    )
    assert mock_wre.execute_skill.call_args.kwargs["input_context"]["task"] == "git commit and push changes"
    mock_wre.execute.assert_not_called()


def test_command_uses_openclaw_executor_when_no_specific_skill_matches():
    """COMMAND: falls back to existing openclaw_executor skill before legacy execute()."""
    from modules.communication.moltbot_bridge.src.openclaw_dae import (
        OpenClawDAE, OpenClawIntent, IntentCategory
    )

    dae = OpenClawDAE()

    mock_loader = MagicMock()
    mock_loader.has_skill.side_effect = lambda name: name == "openclaw_executor"
    mock_loader.registry = {
        "skills": {
            "openclaw_executor": {"agents": ["qwen", "gemma"]},
        }
    }

    mock_wre = MagicMock()
    mock_wre.skills_loader = mock_loader
    mock_wre.find_skill_candidates.return_value = []
    mock_wre.execute_skill.return_value = {
        "output": "OpenClaw executor handled the command",
        "success": True,
    }
    mock_wre.execute.return_value = "legacy execute path"
    dae._wre = mock_wre

    intent = OpenClawIntent(
        raw_message="run tests and summarize failures",
        sender="undaodu",
        channel="test",
        session_key="test",
        category=IntentCategory.COMMAND,
        confidence=0.9,
        is_authorized_commander=True,
        extracted_task="run tests and summarize failures",
        target_domain="wre",
    )

    async def _run():
        return await dae._execute_command(intent)

    result = asyncio.run(_run())

    assert "openclaw_executor" in result
    assert "OpenClaw executor handled the command" in result
    mock_wre.execute_skill.assert_called_once_with(
        skill_name="openclaw_executor",
        agent="qwen",
        input_context=ANY,
    )
    mock_wre.execute.assert_not_called()
