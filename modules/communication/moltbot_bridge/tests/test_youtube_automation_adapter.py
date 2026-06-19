"""
Tests for YouTube automation adapter command parsing and routing.
"""

import unittest
from unittest.mock import AsyncMock, patch

from modules.communication.moltbot_bridge.src.youtube_automation_adapter import (
    SUPPORTED_ACTIONS,
    _build_comments_command,
    _build_indexing_command,
    _build_live_schedule_signal_command,
    _build_scheduling_command,
    _parse_action_command,
    execute_youtube_action,
    handle_youtube_automation_intent,
)


class TestYouTubeAutomationAdapter(unittest.IsolatedAsyncioTestCase):
    def test_parse_valid_command(self):
        parsed = _parse_action_command(
            "youtube action comments channel=move2japan max_comments=2 like=true heart=true reply=false"
        )
        self.assertIsNotNone(parsed)
        action, params = parsed  # type: ignore[misc]
        self.assertEqual(action, "comments")
        self.assertEqual(params.get("channel"), "move2japan")
        self.assertEqual(params.get("max_comments"), "2")

    def test_parse_alias_command(self):
        parsed = _parse_action_command("yt action schedule channel=foundups max_videos=3")
        self.assertIsNotNone(parsed)
        action, params = parsed  # type: ignore[misc]
        self.assertEqual(action, "scheduling")
        self.assertEqual(params.get("channel"), "foundups")

    def test_parse_non_command(self):
        self.assertIsNone(_parse_action_command("show me system status"))

    def test_build_comments_command_flags(self):
        cmd = _build_comments_command(
            {
                "channel": "move2japan",
                "max_comments": "1",
                "like": "false",
                "heart": "true",
                "reply": "false",
                "dom_only": "true",
            }
        )
        command_text = " ".join(cmd)
        self.assertIn("run_skill", command_text)
        self.assertIn("--no-like", cmd)
        self.assertIn("--no-reply", cmd)
        self.assertIn("--dom-only", cmd)

    def test_build_indexing_command(self):
        cmd = _build_indexing_command({"channel": "undaodu", "batch_size": "5"})
        self.assertIn("modules.ai_intelligence.video_indexer.cli", cmd)
        self.assertIn("--channel", cmd)
        self.assertIn("--batch-size", cmd)

    def test_build_scheduling_command(self):
        cmd = _build_scheduling_command({"channel": "foundups", "max_videos": "4", "dry_run": "true"})
        self.assertIn("modules.platform_integration.youtube_shorts_scheduler.cli", cmd)
        self.assertIn("--channel", cmd)
        self.assertIn("--max-videos", cmd)
        self.assertIn("--dry-run", cmd)

    async def test_execute_comments_parses_json_result(self):
        fake_run = {
            "success": True,
            "returncode": 0,
            "command": ["python", "-m", "fake"],
            "stdout_tail": '{"stats": {"comments_processed": 1, "errors": 0}}',
            "stderr_tail": "",
        }
        with patch(
            "modules.communication.moltbot_bridge.src.youtube_automation_adapter._run_subprocess",
            return_value=fake_run,
        ):
            result = await execute_youtube_action("comments", {"channel": "move2japan"})
        self.assertTrue(result.get("success"))
        self.assertIsInstance(result.get("result"), dict)
        self.assertEqual(result.get("result", {}).get("stats", {}).get("comments_processed"), 1)

    async def test_handle_command_success(self):
        mock_result = {"success": True, "action": "scheduling", "returncode": 0}
        with patch(
            "modules.communication.moltbot_bridge.src.youtube_automation_adapter.execute_youtube_action",
            new=AsyncMock(return_value=mock_result),
        ):
            response = await handle_youtube_automation_intent(
                "youtube action scheduling channel=move2japan max_videos=2 dry_run=true",
                sender="@UnDaoDu",
            )
        self.assertIsNotNone(response)
        self.assertIn("YouTube action executed", response or "")
        self.assertIn('"success": true', (response or "").lower())

    async def test_handle_unsupported_action(self):
        response = await handle_youtube_automation_intent(
            "youtube action unknown_action",
            sender="@UnDaoDu",
        )
        self.assertIsNotNone(response)
        self.assertIn("not recognized", response or "")

    # --- live_schedule_signal routing (SHORTS_SKILLZ_AUTONOMOUS_REGISTRATION_PHASE1) ---

    def test_live_schedule_signal_is_supported(self):
        self.assertIn("live_schedule_signal", SUPPORTED_ACTIONS)

    def test_parse_live_schedule_signal_command(self):
        parsed = _parse_action_command(
            "youtube action live_schedule_signal channel=foundups connect=edge"
        )
        self.assertIsNotNone(parsed)
        action, params = parsed  # type: ignore[misc]
        self.assertEqual(action, "live_schedule_signal")
        self.assertEqual(params.get("channel"), "foundups")
        self.assertEqual(params.get("connect"), "edge")

    def test_parse_live_schedule_signal_alias(self):
        parsed = _parse_action_command("yt action shorts_live_schedule_signal channel=antifafm")
        self.assertIsNotNone(parsed)
        action, params = parsed  # type: ignore[misc]
        self.assertEqual(action, "live_schedule_signal")
        self.assertEqual(params.get("channel"), "antifafm")

    def test_build_live_schedule_signal_command(self):
        cmd = _build_live_schedule_signal_command(
            {"channel": "foundups", "connect": "edge", "low_view_threshold": "50"}
        )
        command_text = " ".join(cmd)
        self.assertIn(
            "modules.platform_integration.youtube_shorts_scheduler.skillz.shorts_live_schedule_signal.run_skill",
            command_text,
        )
        self.assertIn("--channel", cmd)
        self.assertIn("foundups", cmd)
        self.assertIn("--connect", cmd)
        self.assertIn("edge", cmd)
        self.assertIn("--low-view-threshold", cmd)
        self.assertIn("50", cmd)
        self.assertIn("--json", cmd)

    def test_build_live_schedule_signal_command_no_connect_omits_flag(self):
        cmd = _build_live_schedule_signal_command({"channel": "foundups"})
        # No connect -> the live browser flag is absent (offline/no-op by construction).
        self.assertNotIn("--connect", cmd)

    async def test_execute_live_schedule_signal_routes_and_parses_json(self):
        fake_run = {
            "success": True,
            "returncode": 0,
            "command": ["python", "-m", "fake"],
            "stdout_tail": '{"skill":"shorts_live_schedule_signal","success":true,"scheduled_count":131}',
            "stderr_tail": "",
        }
        with patch(
            "modules.communication.moltbot_bridge.src.youtube_automation_adapter._run_subprocess",
            return_value=fake_run,
        ) as run_mock:
            result = await execute_youtube_action(
                "live_schedule_signal", {"channel": "foundups", "connect": "edge"}
            )
        # Routed to the live-signal builder (not some other action's command).
        dispatched_cmd = run_mock.call_args.args[0]
        self.assertIn(
            "modules.platform_integration.youtube_shorts_scheduler.skillz.shorts_live_schedule_signal.run_skill",
            " ".join(dispatched_cmd),
        )
        self.assertEqual(result.get("action"), "live_schedule_signal")
        self.assertTrue(result.get("success"))
        self.assertEqual(result.get("result", {}).get("scheduled_count"), 131)


if __name__ == "__main__":
    unittest.main(verbosity=2)

