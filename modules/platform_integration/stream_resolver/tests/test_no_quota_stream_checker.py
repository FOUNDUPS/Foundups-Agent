#!/usr/bin/env python3
"""
Test suite for NoQuotaStreamChecker
WSP 34: Comprehensive test coverage for stream checking functionality
"""



import unittest
from unittest.mock import patch, MagicMock, mock_open
import json
import time
import sys
import os

from modules.platform_integration.stream_resolver.src.no_quota_stream_checker import NoQuotaStreamChecker


class TestNoQuotaStreamChecker(unittest.TestCase):
    """Test suite for NoQuotaStreamChecker functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.checker = NoQuotaStreamChecker()
        self.test_video_id = "dQw4w9WgXcQ"
        self.test_channel_id = "UCBR8-60-B28hp2BmDPdVsXQ"

    def tearDown(self):
        """Clean up test fixtures."""
        pass

    @patch('requests.Session.get')
    def test_check_video_is_live_success(self, mock_get):
        """Test successful video live check."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.text = '<html><body>Live</body></html>'
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = self.checker.check_video_is_live(self.test_video_id)

        self.assertIsInstance(result, dict)
        self.assertIn('live', result)
        mock_get.assert_called_once()

    @patch('requests.Session.get')
    def test_check_video_is_live_not_live(self, mock_get):
        """Test video not live scenario."""
        # Mock response indicating not live
        mock_response = MagicMock()
        mock_response.text = '<html><body>Not Live</body></html>'
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = self.checker.check_video_is_live(self.test_video_id)

        self.assertIsInstance(result, dict)
        self.assertFalse(result.get('live', True))

    @patch('requests.Session.get')
    @patch.object(NoQuotaStreamChecker, "check_video_is_live")
    def test_check_channel_for_live_success(self, mock_check_video, mock_get):
        """Test successful channel live check."""
        # Mock /live redirect to a watch URL (do not follow redirects in implementation)
        mock_response = MagicMock()
        mock_response.status_code = 302
        mock_response.url = f"https://www.youtube.com/channel/{self.test_channel_id}/live"
        mock_response.headers = {"Location": f"/watch?v={self.test_video_id}"}
        mock_get.return_value = mock_response

        mock_check_video.return_value = {"live": True, "video_id": self.test_video_id, "method": "api"}

        result = self.checker.check_channel_for_live(self.test_channel_id)

        self.assertIsInstance(result, dict)
        self.assertTrue(result.get("live"))
        self.assertEqual(result.get("video_id"), self.test_video_id)
        mock_get.assert_called()
        called_url = mock_get.call_args[0][0]
        self.assertTrue(str(called_url).endswith("/live"))
        self.assertFalse(mock_get.call_args[1].get("allow_redirects", True))

    @patch('requests.Session.get')
    @patch.object(NoQuotaStreamChecker, "_anti_detection_delay")
    @patch.object(NoQuotaStreamChecker, "check_video_is_live")
    def test_check_channel_no_api_trusts_live_indicators(self, mock_check_video, mock_delay, mock_get):
        """Test no-API mode trusts strong /live indicators."""
        os.environ["YT_STREAM_API_VERIFY"] = "false"
        self.addCleanup(lambda: os.environ.pop("YT_STREAM_API_VERIFY", None))

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = f"https://www.youtube.com/channel/{self.test_channel_id}/live"
        mock_response.headers = {}
        mock_response.text = '"isLiveNow":true "BADGE_STYLE_TYPE_LIVE_NOW" "videoId":"dQw4w9WgXcQ"'
        mock_get.return_value = mock_response

        result = self.checker.check_channel_for_live(self.test_channel_id)

        self.assertIsInstance(result, dict)
        self.assertTrue(result.get("live"))
        self.assertEqual(result.get("video_id"), "dQw4w9WgXcQ")
        mock_check_video.assert_not_called()

    @patch('requests.Session.get')
    @patch.object(NoQuotaStreamChecker, "_anti_detection_delay")
    @patch.object(NoQuotaStreamChecker, "check_video_is_live")
    def test_check_channel_streams_fallback_when_live_quiet(self, mock_check_video, mock_delay, mock_get):
        """Test /streams fallback when /live has no strong indicators."""
        live_response = MagicMock()
        live_response.status_code = 200
        live_response.url = f"https://www.youtube.com/channel/{self.test_channel_id}/live"
        live_response.headers = {}
        live_response.text = "<html><body>Channel home</body></html>"

        streams_response = MagicMock()
        streams_response.status_code = 200
        streams_response.url = f"https://www.youtube.com/channel/{self.test_channel_id}/streams"
        streams_response.headers = {}
        streams_response.text = '"BADGE_STYLE_TYPE_LIVE_NOW" "videoId":"live123"'

        mock_get.side_effect = [live_response, streams_response]
        mock_check_video.return_value = {"live": True, "video_id": "live123"}

        result = self.checker.check_channel_for_live(self.test_channel_id)

        self.assertIsInstance(result, dict)
        self.assertTrue(result.get("live"))
        self.assertEqual(result.get("video_id"), "live123")
        self.assertGreaterEqual(mock_get.call_count, 2)

    def test_get_random_headers(self):
        """Test random header generation."""
        headers = self.checker._get_random_headers()

        self.assertIsInstance(headers, dict)
        self.assertIn('User-Agent', headers)
        self.assertIn('Accept', headers)

    def test_anti_detection_delay(self):
        """Test anti-detection delay functionality."""
        start_time = time.time()
        self.checker._anti_detection_delay(min_delay=0.1, max_delay=0.2)
        end_time = time.time()

        # Should have delayed for at least 0.1 seconds
        self.assertGreater(end_time - start_time, 0.05)

    def test_is_channel_rate_limited_not_limited(self):
        """Test channel rate limit check when not limited."""
        is_limited, remaining = self.checker._is_channel_rate_limited(self.test_channel_id)
        self.assertFalse(is_limited)
        self.assertEqual(remaining, 0.0)

    def test_register_rate_limit(self):
        """Test rate limit registration."""
        cooldown = self.checker._register_rate_limit(self.test_channel_id, "TestChannel")
        self.assertIsInstance(cooldown, float)
        self.assertGreater(cooldown, 0)

    @patch('time.sleep')
    def test_rate_limit_behavior(self, mock_sleep):
        """Test behavior after rate limit registration."""
        # Register rate limit
        self.checker._register_rate_limit(self.test_channel_id)

        # Check that channel is now rate limited
        is_limited, _ = self.checker._is_channel_rate_limited(self.test_channel_id)
        self.assertTrue(is_limited)

    @patch('modules.platform_integration.stream_resolver.src.no_quota_stream_checker.LIVE_STATUS_VERIFIER_AVAILABLE', False)
    @patch('requests.Session.get')
    def test_fallback_behavior(self, mock_get):
        """Test fallback behavior when LiveStatusVerifier is unavailable."""
        # This should work without the API verifier and without touching the network.
        mock_response = MagicMock()
        mock_response.text = '<html><body>Not Live</body></html>'
        mock_response.status_code = 200
        mock_response.url = f"https://www.youtube.com/watch?v={self.test_video_id}"
        mock_response.headers = {}
        mock_get.return_value = mock_response

        result = self.checker.check_video_is_live(self.test_video_id)
        self.assertIsInstance(result, dict)

    @patch('requests.Session.get')
    @patch('modules.platform_integration.youtube_auth.src.youtube_auth.get_authenticated_service')
    def test_request_timeout_handling(self, mock_auth, mock_get):
        """Test handling of request timeouts."""
        from requests.exceptions import Timeout

        mock_get.side_effect = Timeout("Request timed out")
        mock_auth.side_effect = RuntimeError("auth unavailable in unit test")

        result = self.checker.check_video_is_live(self.test_video_id)

        self.assertIsInstance(result, dict)
        self.assertFalse(result.get('live', True))

    @patch('modules.platform_integration.youtube_auth.src.youtube_auth.get_authenticated_service')
    def test_api_verification_reuses_cached_service(self, mock_auth):
        """API verification should not rebuild the YouTube service per video check."""
        mock_service = MagicMock()
        mock_service._credential_set = 10
        mock_service.videos.return_value.list.return_value.execute.return_value = {
            "items": [
                {
                    "snippet": {
                        "channelId": self.test_channel_id,
                        "liveBroadcastContent": "none",
                    },
                    "liveStreamingDetails": {},
                }
            ]
        }
        mock_auth.return_value = mock_service

        first = self.checker.check_video_is_live(self.test_video_id, scraping_prefilter=False)
        second = self.checker.check_video_is_live("abc123def45", scraping_prefilter=False)

        self.assertFalse(first.get("live"))
        self.assertFalse(second.get("live"))
        mock_auth.assert_called_once()

    @patch('requests.Session.get')
    @patch.object(NoQuotaStreamChecker, "_anti_detection_delay")
    @patch.object(NoQuotaStreamChecker, "check_video_is_live")
    def test_channel_mismatch_is_recommended_debug_not_warning(self, mock_check_video, mock_delay, mock_get):
        """Recommended streams from other channels are expected, not warnings."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = f"https://www.youtube.com/channel/{self.test_channel_id}/live"
        mock_response.headers = {}
        mock_response.text = '"BADGE_STYLE_TYPE_LIVE_NOW" "videoId":"dQw4w9WgXcQ"'
        mock_get.return_value = mock_response
        mock_check_video.return_value = {
            "live": True,
            "video_id": self.test_video_id,
            "method": "api",
            "channel_id": "UCOTHERCHANNEL1234567890",
        }

        with patch('modules.platform_integration.stream_resolver.src.no_quota_stream_checker.logger.warning') as mock_warning, \
             patch('modules.platform_integration.stream_resolver.src.no_quota_stream_checker.logger.debug') as mock_debug:
            result = self.checker.check_channel_for_live(self.test_channel_id)

        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("status"), "stale_indicator")
        mock_warning.assert_not_called()
        self.assertTrue(any("[RECOMMENDED]" in str(call) for call in mock_debug.call_args_list))

    @patch('requests.Session.get')
    @patch.object(NoQuotaStreamChecker, "_anti_detection_delay")
    @patch.object(NoQuotaStreamChecker, "check_video_is_live")
    def test_stale_indicator_returned_when_live_dom_has_no_verified_stream(self, mock_check_video, mock_delay, mock_get):
        """Live-looking DOM without verified live videos is reported as stale, not live."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = f"https://www.youtube.com/channel/{self.test_channel_id}/live"
        mock_response.headers = {}
        mock_response.text = '"isLiveNow":true "BADGE_STYLE_TYPE_LIVE_NOW" "videoId":"dQw4w9WgXcQ"'
        mock_get.return_value = mock_response
        mock_check_video.return_value = {"live": False, "method": "api", "status": "none"}

        result = self.checker.check_channel_for_live(self.test_channel_id)

        self.assertIsInstance(result, dict)
        self.assertFalse(result.get("live"))
        self.assertEqual(result.get("status"), "stale_indicator")
        self.assertEqual(result.get("confidence"), 0.3)
        self.assertEqual(result.get("source"), "no_quota_live_page")

    def test_session_configuration(self):
        """Test that session is properly configured."""
        self.assertIsNotNone(self.checker.session)
        self.assertTrue(hasattr(self.checker.session, 'get'))

    def test_lazy_live_verifier_loading(self):
        """Test lazy loading of LiveStatusVerifier."""
        self.assertFalse(self.checker._live_verifier_initialized)
        self.checker._get_live_verifier()
        self.assertTrue(self.checker._live_verifier_initialized)

    def test_get_live_verifier_caching(self):
        """Test that LiveStatusVerifier is cached after first load."""
        # First call
        verifier1 = self.checker._get_live_verifier()

        # Second call should return cached result
        verifier2 = self.checker._get_live_verifier()

        # Should be the same object (cached)
        self.assertIs(verifier1, verifier2)

    def test_timeout_env_parsing_invalid_falls_back(self):
        """Malformed YT_STREAM_REQUEST_TIMEOUT_SEC falls back to 30."""
        import os
        old_val = os.environ.get("YT_STREAM_REQUEST_TIMEOUT_SEC")
        try:
            os.environ["YT_STREAM_REQUEST_TIMEOUT_SEC"] = "not_a_number"
            result = NoQuotaStreamChecker._parse_timeout_env()
            self.assertEqual(result, 30.0)
        finally:
            if old_val is None:
                os.environ.pop("YT_STREAM_REQUEST_TIMEOUT_SEC", None)
            else:
                os.environ["YT_STREAM_REQUEST_TIMEOUT_SEC"] = old_val

    def test_timeout_env_parsing_negative_falls_back(self):
        """Negative YT_STREAM_REQUEST_TIMEOUT_SEC falls back to 30."""
        import os
        old_val = os.environ.get("YT_STREAM_REQUEST_TIMEOUT_SEC")
        try:
            os.environ["YT_STREAM_REQUEST_TIMEOUT_SEC"] = "-5"
            result = NoQuotaStreamChecker._parse_timeout_env()
            self.assertEqual(result, 30.0)
        finally:
            if old_val is None:
                os.environ.pop("YT_STREAM_REQUEST_TIMEOUT_SEC", None)
            else:
                os.environ["YT_STREAM_REQUEST_TIMEOUT_SEC"] = old_val

    def test_timeout_env_parsing_clamps_to_max(self):
        """Excessive YT_STREAM_REQUEST_TIMEOUT_SEC is clamped to 120."""
        import os
        old_val = os.environ.get("YT_STREAM_REQUEST_TIMEOUT_SEC")
        try:
            os.environ["YT_STREAM_REQUEST_TIMEOUT_SEC"] = "999"
            result = NoQuotaStreamChecker._parse_timeout_env()
            self.assertEqual(result, 120.0)
        finally:
            if old_val is None:
                os.environ.pop("YT_STREAM_REQUEST_TIMEOUT_SEC", None)
            else:
                os.environ["YT_STREAM_REQUEST_TIMEOUT_SEC"] = old_val


class TestNoQuotaStreamCheckerIntegration(unittest.TestCase):
    """Integration tests for NoQuotaStreamChecker."""

    def setUp(self):
        """Set up integration test fixtures."""
        self.checker = NoQuotaStreamChecker()

    def test_initialization(self):
        """Test proper initialization."""
        self.assertIsInstance(self.checker, NoQuotaStreamChecker)
        self.assertIsNotNone(self.checker.session)

    @patch('requests.adapters.HTTPAdapter.send')
    def test_session_retry_configuration(self, mock_send):
        """Test that session retry strategy is properly configured."""
        # This is more of a configuration test
        # The actual retry logic is tested in HTTP adapter
        self.assertIsNotNone(self.checker.session)
        self.assertTrue(hasattr(self.checker.session, 'mount'))


if __name__ == '__main__':
    unittest.main()
