"""
Tests for OBS startup verification behavior.

Focus: avoid false-positive "stream started" when OBS output never becomes active.
"""

import os
import unittest
from unittest.mock import patch

from modules.platform_integration.antifafm_broadcaster.src.obs_controller import OBSController


class _FakeStatus:
    def __init__(self, active=False, reconnecting=False, bytes_sent=0, duration=0):
        self.output_active = active
        self.output_reconnecting = reconnecting
        self.output_bytes = bytes_sent
        self.output_duration = duration


class _FakeWS:
    def __init__(self, statuses, start_raises=False):
        self._statuses = list(statuses)
        self.start_called = False
        self.start_raises = start_raises
        self.service_type = "rtmp_common"
        self.service_settings = {"server": "", "key": ""}

    def get_stream_status(self):
        if not self._statuses:
            return _FakeStatus(active=False)
        if len(self._statuses) == 1:
            return self._statuses[0]
        return self._statuses.pop(0)

    def start_stream(self):
        self.start_called = True
        if self.start_raises:
            raise RuntimeError("start failure")

    def get_stream_service_settings(self):
        class _Resp:
            pass
        resp = _Resp()
        resp.stream_service_type = self.service_type
        resp.stream_service_settings = dict(self.service_settings)
        return resp

    def set_stream_service_settings(self, ss_type, ss_settings):
        self.service_type = ss_type
        self.service_settings = dict(ss_settings)


class TestOBSControllerStartup(unittest.IsolatedAsyncioTestCase):
    @patch.dict(
        os.environ,
        {
            "ANTIFAFM_OBS_START_VERIFY_SECONDS": "0.3",
            "ANTIFAFM_OBS_START_POLL_SECONDS": "0.01",
        },
        clear=False,
    )
    async def test_start_streaming_already_active(self):
        controller = OBSController()
        controller.connected = True
        fake_ws = _FakeWS([_FakeStatus(active=True)])
        controller.ws = fake_ws

        ok = await controller.start_streaming()
        self.assertTrue(ok)
        self.assertFalse(fake_ws.start_called)

    @patch.dict(
        os.environ,
        {
            "ANTIFAFM_OBS_START_VERIFY_SECONDS": "0.4",
            "ANTIFAFM_OBS_START_POLL_SECONDS": "0.01",
        },
        clear=False,
    )
    async def test_start_streaming_waits_until_active(self):
        controller = OBSController()
        controller.connected = True
        fake_ws = _FakeWS(
            [
                _FakeStatus(active=False),  # pre-start check
                _FakeStatus(active=False),  # first poll
                _FakeStatus(active=True, bytes_sent=128, duration=2200),  # second poll
            ]
        )
        controller.ws = fake_ws

        ok = await controller.start_streaming()
        self.assertTrue(ok)
        self.assertTrue(fake_ws.start_called)
        self.assertIsNone(controller.get_last_start_error())

    @patch.dict(
        os.environ,
        {
            "ANTIFAFM_OBS_START_VERIFY_SECONDS": "0.3",
            "ANTIFAFM_OBS_START_POLL_SECONDS": "0.01",
        },
        clear=False,
    )
    async def test_start_streaming_reports_inactive_timeout(self):
        controller = OBSController()
        controller.connected = True
        fake_ws = _FakeWS(
            [
                _FakeStatus(active=False),  # pre-start check
                _FakeStatus(active=False),
                _FakeStatus(active=False),
                _FakeStatus(active=False, reconnecting=True),
            ]
        )
        controller.ws = fake_ws

        ok = await controller.start_streaming()
        self.assertFalse(ok)
        self.assertTrue(fake_ws.start_called)
        self.assertEqual(
            controller.get_last_start_error(),
            "stream_output_inactive_after_start",
        )

    async def test_ensure_stream_service_custom_updates_service(self):
        controller = OBSController()
        controller.connected = True
        fake_ws = _FakeWS([_FakeStatus(active=False)])
        controller.ws = fake_ws

        ok = await controller.ensure_stream_service_custom(
            "rtmps://a.rtmps.youtube.com:443/live2",
            "abcd-efgh-ijkl",
        )
        self.assertTrue(ok)
        self.assertEqual(fake_ws.service_type, "rtmp_custom")
        self.assertEqual(fake_ws.service_settings.get("server"), "rtmps://a.rtmps.youtube.com:443/live2")
        self.assertEqual(fake_ws.service_settings.get("key"), "abcd-efgh-ijkl")

    async def test_ensure_stream_service_custom_noop_when_already_set(self):
        controller = OBSController()
        controller.connected = True
        fake_ws = _FakeWS([_FakeStatus(active=False)])
        fake_ws.service_type = "rtmp_custom"
        fake_ws.service_settings = {
            "server": "rtmps://a.rtmps.youtube.com:443/live2",
            "key": "aaaa-bbbb-cccc",
            "use_auth": False,
        }
        controller.ws = fake_ws

        ok = await controller.ensure_stream_service_custom(
            "rtmps://a.rtmps.youtube.com:443/live2",
            "aaaa-bbbb-cccc",
        )
        self.assertTrue(ok)


class TestOBSStartPreflightDispatch(unittest.IsolatedAsyncioTestCase):
    """DJ-OBS: OBS start-timeout dispatches ai_overseer preflight failure event."""

    def _make_controller_with_inactive_ws(self):
        controller = OBSController()
        controller.connected = True
        controller.ws = _FakeWS(
            [
                _FakeStatus(active=False),
                _FakeStatus(active=False),
                _FakeStatus(active=False),
                _FakeStatus(active=False, reconnecting=True, bytes_sent=0, duration=0),
            ]
        )
        return controller

    @patch.dict(
        os.environ,
        {
            "ANTIFAFM_OBS_START_VERIFY_SECONDS": "0.3",
            "ANTIFAFM_OBS_START_POLL_SECONDS": "0.01",
        },
        clear=False,
    )
    async def test_obs_start_timeout_dispatches_preflight_fail(self):
        controller = self._make_controller_with_inactive_ws()
        with patch(
            "modules.ai_intelligence.ai_overseer.src.preflight_resolution.on_preflight_fail"
        ) as mock_dispatch:
            ok = await controller.start_streaming()
        self.assertFalse(ok)
        self.assertTrue(mock_dispatch.called)
        call_kwargs = mock_dispatch.call_args.kwargs
        self.assertEqual(call_kwargs["component"], "obs_start")
        self.assertEqual(call_kwargs["severity"], "critical")

    @patch.dict(
        os.environ,
        {
            "ANTIFAFM_OBS_START_VERIFY_SECONDS": "0.3",
            "ANTIFAFM_OBS_START_POLL_SECONDS": "0.01",
        },
        clear=False,
    )
    async def test_obs_start_timeout_payload_has_required_fields(self):
        controller = self._make_controller_with_inactive_ws()
        with patch(
            "modules.ai_intelligence.ai_overseer.src.preflight_resolution.on_preflight_fail"
        ) as mock_dispatch:
            await controller.start_streaming()
        payload = mock_dispatch.call_args.kwargs["payload"]
        for field in (
            "error_code",
            "source_file",
            "source_function",
            "verify_timeout_s",
            "poll_interval_s",
            "output_bytes",
            "output_duration_ms",
            "reconnecting",
            "likely_cause",
            "requires_012",
            "automation_candidate",
            "safe_autonomous_actions",
            "unsafe_actions",
            "remediation",
        ):
            self.assertIn(field, payload)
        self.assertEqual(payload["error_code"], "stream_output_inactive_after_start")
        self.assertEqual(payload["likely_cause"], "youtube_broadcast_modal_or_binding")

    @patch.dict(
        os.environ,
        {
            "ANTIFAFM_OBS_START_VERIFY_SECONDS": "0.3",
            "ANTIFAFM_OBS_START_POLL_SECONDS": "0.01",
        },
        clear=False,
    )
    async def test_obs_start_timeout_requires_012(self):
        controller = self._make_controller_with_inactive_ws()
        with patch(
            "modules.ai_intelligence.ai_overseer.src.preflight_resolution.on_preflight_fail"
        ) as mock_dispatch:
            await controller.start_streaming()
        payload = mock_dispatch.call_args.kwargs["payload"]
        self.assertIs(payload["requires_012"], True)
        self.assertIn("click_youtube_studio_modal", payload["unsafe_actions"])

    @patch.dict(
        os.environ,
        {
            "ANTIFAFM_OBS_START_VERIFY_SECONDS": "0.3",
            "ANTIFAFM_OBS_START_POLL_SECONDS": "0.01",
        },
        clear=False,
    )
    async def test_obs_start_dispatch_failure_does_not_block_return(self):
        controller = self._make_controller_with_inactive_ws()
        with patch(
            "modules.ai_intelligence.ai_overseer.src.preflight_resolution.on_preflight_fail",
            side_effect=RuntimeError("simulated dispatcher failure"),
        ):
            ok = await controller.start_streaming()
        self.assertFalse(ok)
        self.assertEqual(
            controller.get_last_start_error(),
            "stream_output_inactive_after_start",
        )

    @patch.dict(
        os.environ,
        {
            "ANTIFAFM_OBS_START_VERIFY_SECONDS": "0.4",
            "ANTIFAFM_OBS_START_POLL_SECONDS": "0.01",
        },
        clear=False,
    )
    async def test_obs_start_success_does_not_dispatch(self):
        controller = OBSController()
        controller.connected = True
        controller.ws = _FakeWS(
            [
                _FakeStatus(active=False),
                _FakeStatus(active=False),
                _FakeStatus(active=True, bytes_sent=128, duration=2200),
            ]
        )
        with patch(
            "modules.ai_intelligence.ai_overseer.src.preflight_resolution.on_preflight_fail"
        ) as mock_dispatch:
            ok = await controller.start_streaming()
        self.assertTrue(ok)
        self.assertFalse(mock_dispatch.called)

    @patch.dict(
        os.environ,
        {
            "ANTIFAFM_OBS_START_VERIFY_SECONDS": "0.3",
            "ANTIFAFM_OBS_START_POLL_SECONDS": "0.01",
        },
        clear=False,
    )
    async def test_obs_start_dispatch_import_failure_is_silent(self):
        import sys

        controller = self._make_controller_with_inactive_ws()
        original = sys.modules.pop(
            "modules.ai_intelligence.ai_overseer.src.preflight_resolution", None
        )
        sys.modules["modules.ai_intelligence.ai_overseer.src.preflight_resolution"] = None
        try:
            ok = await controller.start_streaming()
        finally:
            if original is not None:
                sys.modules[
                    "modules.ai_intelligence.ai_overseer.src.preflight_resolution"
                ] = original
            else:
                sys.modules.pop(
                    "modules.ai_intelligence.ai_overseer.src.preflight_resolution",
                    None,
                )
        self.assertFalse(ok)
        self.assertEqual(
            controller.get_last_start_error(),
            "stream_output_inactive_after_start",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
