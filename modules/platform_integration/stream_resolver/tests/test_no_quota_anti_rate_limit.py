#!/usr/bin/env python3
"""
Test Suite for No-Quota Stream Checker Anti-Rate-Limiting Features
WSP 87: Comprehensive tests for enhanced anti-detection measures
"""



import unittest
from unittest.mock import Mock, patch, MagicMock, call
import requests
import time
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.no_quota_stream_checker import NoQuotaStreamChecker


class TestAntiRateLimiting(unittest.TestCase):
    """Test anti-rate-limiting features of NoQuotaStreamChecker"""

    def setUp(self):
        """Set up test fixtures"""
        self.checker = NoQuotaStreamChecker()

    def test_user_agent_rotation(self):
        """Test that User-Agent rotates randomly"""
        # Get multiple headers
        headers_list = [self.checker._get_random_headers() for _ in range(10)]
        user_agents = [h['User-Agent'] for h in headers_list]

        # Should have multiple different User-Agents
        unique_agents = set(user_agents)
        self.assertGreater(len(unique_agents), 1, "User-Agent should rotate")

        # All should be from our pool
        for agent in unique_agents:
            self.assertIn(agent, self.checker.USER_AGENTS)

    def test_headers_completeness(self):
        """Test that all required headers are present"""
        headers = self.checker._get_random_headers()

        # Check all required headers
        required_headers = [
            'User-Agent',
            'Accept',
            'Accept-Language',
            'Accept-Encoding',
            'Connection',
        ]

        for header in required_headers:
            self.assertIn(header, headers, f"Missing required header: {header}")

    def test_anti_detection_delay(self):
        """Test that delays are properly randomized"""
        delays = []

        # Mock time.sleep to capture delays
        with patch('time.sleep') as mock_sleep:
            for _ in range(10):
                self.checker._anti_detection_delay()

            # Get all delay values
            delays = [call[0][0] for call in mock_sleep.call_args_list]

        # All delays should be between 10.0 and 18.0 seconds by default
        for delay in delays:
            self.assertGreaterEqual(delay, 10.0, "Delay too short")
            self.assertLessEqual(delay, 18.0, "Delay too long")

        # Delays should vary (not all the same)
        unique_delays = set(delays)
        self.assertGreater(len(unique_delays), 5, "Delays should be randomized")

    def test_retry_strategy_setup(self):
        """Test that retry strategy is properly configured"""
        # Check that HTTPAdapter is mounted
        self.assertIsNotNone(self.checker.session.adapters)

        # Check both http and https adapters
        http_adapter = self.checker.session.get_adapter('http://example.com')
        https_adapter = self.checker.session.get_adapter('https://example.com')

        self.assertIsNotNone(http_adapter)
        self.assertIsNotNone(https_adapter)

        # Check retry configuration
        self.assertIsNotNone(http_adapter.max_retries)
        self.assertEqual(http_adapter.max_retries.total, 2)
        self.assertNotIn(429, http_adapter.max_retries.status_forcelist)
        self.assertIn(500, http_adapter.max_retries.status_forcelist)
        self.assertIn(502, http_adapter.max_retries.status_forcelist)
        self.assertIn(503, http_adapter.max_retries.status_forcelist)
        self.assertIn(504, http_adapter.max_retries.status_forcelist)

    @patch('requests.Session.get')
    def test_check_video_with_anti_detection(self, mock_get):
        """Test that video checking uses anti-detection measures"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = 'https://www.youtube.com/watch?v=test_video_id'
        mock_response.headers = {}
        mock_response.text = '''
            <html>
                <title>Test Video - YouTube</title>
                <script>var ytInitialData = {"contents": {}};</script>
            </html>
        '''
        mock_get.return_value = mock_response

        # Mock the delay
        with patch.object(self.checker, '_anti_detection_delay') as mock_delay:
            result = self.checker.check_video_is_live('test_video_id')

            # Delay should be called
            mock_delay.assert_called_once()

            # Headers should be set
            call_args = mock_get.call_args
            self.assertIn('headers', call_args[1])
            headers = call_args[1]['headers']
            self.assertIn('User-Agent', headers)

    @patch('requests.Session.get')
    @patch('modules.platform_integration.youtube_auth.src.youtube_auth.get_authenticated_service')
    def test_rate_limit_handling(self, mock_auth, mock_get):
        """Test handling of 429 rate limit errors (treated as CAPTCHA trigger)."""
        # Mock 429 response
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.url = 'https://www.youtube.com/watch?v=test_video_id'
        mock_response.headers = {}
        mock_get.return_value = mock_response
        mock_auth.side_effect = RuntimeError("auth unavailable in unit test")

        with patch.object(self.checker, '_anti_detection_delay'), patch.object(self.checker, '_register_captcha_hit') as mock_captcha:
            mock_captcha.return_value = 42.0
            result = self.checker.check_video_is_live('test_video_id')

            # Should handle error gracefully
            self.assertFalse(result['live'])
            self.assertIn('method', result)
            mock_captcha.assert_called_once()

    @patch('requests.Session.get')
    def test_channel_check_with_delays(self, mock_get):
        """Test that channel checking uses /live and does not follow watch redirects."""
        channel_response = Mock()
        channel_response.status_code = 302
        channel_response.url = 'https://www.youtube.com/channel/test_channel_id/live'
        channel_response.headers = {"Location": "/watch?v=dQw4w9WgXcQ"}
        mock_get.return_value = channel_response

        with patch.object(self.checker, '_anti_detection_delay'), patch.object(self.checker, 'check_video_is_live') as mock_check_video:
            mock_check_video.return_value = {"live": True, "video_id": "dQw4w9WgXcQ", "method": "api"}
            result = self.checker.check_channel_for_live('test_channel_id')

        self.assertIsNotNone(result)
        self.assertTrue(result.get("live"))
        self.assertEqual(result.get("video_id"), "dQw4w9WgXcQ")
        self.assertFalse(mock_get.call_args[1].get("allow_redirects", True))

    def test_cookie_persistence(self):
        """Test that cookies are persisted in session"""
        # Check cookie jar exists
        self.assertIsNotNone(self.checker.session.cookies)
        self.assertIsInstance(self.checker.session.cookies, requests.cookies.RequestsCookieJar)

    def test_timeout_values(self):
        """Test that timeout values are appropriate"""
        with patch('requests.Session.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.url = 'https://www.youtube.com/watch?v=test_id'
            mock_response.headers = {}
            mock_response.text = '<html></html>'
            mock_get.return_value = mock_response

            with patch.object(self.checker, '_anti_detection_delay'):
                self.checker.check_video_is_live('test_id')

                # Check timeout matches the explicit channel/video request timeout
                call_args = mock_get.call_args
                self.assertEqual(call_args[1]['timeout'], self.checker.request_timeout_sec)

    @patch('requests.Session.get')
    def test_exponential_backoff_on_errors(self, mock_get):
        """Test that exponential backoff works for repeated errors"""
        # This is handled by urllib3.util.retry.Retry internally
        # We can verify the configuration
        adapter = self.checker.session.get_adapter('https://youtube.com')
        retry = adapter.max_retries

        # Check backoff factor
        self.assertEqual(retry.backoff_factor, 15)
        self.assertTrue(retry.respect_retry_after_header)

        # Check status codes that trigger retry
        self.assertIn(500, retry.status_forcelist)
        self.assertIn(502, retry.status_forcelist)
        self.assertIn(503, retry.status_forcelist)
        self.assertIn(504, retry.status_forcelist)
        self.assertNotIn(429, retry.status_forcelist)


class TestLiveStreamDetection(unittest.TestCase):
    """Test live stream detection logic"""

    def setUp(self):
        """Set up test fixtures"""
        self.checker = NoQuotaStreamChecker()

    @patch('requests.Session.get')
    @patch('modules.platform_integration.youtube_auth.src.youtube_auth.get_authenticated_service')
    def test_live_stream_detection(self, mock_auth, mock_get):
        """Test detection of actually live streams"""
        # Mock response with live indicators
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''
            <html>
                <title>LIVE NOW - Test Stream - YouTube</title>
                <script>
                    "isLiveNow":true
                    "BADGE_STYLE_TYPE_LIVE_NOW"
                    "watching now</span>"
                    "label":"LIVE"
                    var ytInitialData = {"contents": {}};
                </script>
            </html>
        '''
        mock_response.url = 'https://www.youtube.com/watch?v=live_video_id'
        mock_response.headers = {}
        mock_get.return_value = mock_response
        mock_auth.side_effect = RuntimeError("auth unavailable in unit test")

        with patch.object(self.checker, '_anti_detection_delay'):
            result = self.checker.check_video_is_live('live_video_id')

            # Should detect as live
            self.assertTrue(result['live'], "Should detect live stream")

    @patch('requests.Session.get')
    def test_ended_stream_detection(self, mock_get):
        """Test detection of ended streams"""
        # Mock response with ended indicators
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''
            <html>
                <title>Was Live - Test Stream - YouTube</title>
                <script>
                    "isLiveContent":false
                    "liveBroadcastDetails":{"hasDisplayedEndscreen":true
                    var ytInitialData = {"contents": {}};
                </script>
            </html>
        '''
        mock_get.return_value = mock_response

        with patch.object(self.checker, '_anti_detection_delay'):
            result = self.checker.check_video_is_live('ended_video_id')

            # Should detect as not live
            self.assertFalse(result['live'], "Should detect ended stream")


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system"""

    @patch('requests.Session.get')
    @patch('modules.platform_integration.youtube_auth.src.youtube_auth.get_authenticated_service')
    def test_full_stream_check_workflow(self, mock_auth, mock_get):
        """Test complete workflow from channel to live detection"""
        checker = NoQuotaStreamChecker()

        # Mock channel redirects to live video
        channel_response = Mock()
        channel_response.status_code = 200
        channel_response.url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        channel_response.headers = {}

        # Mock live video response
        video_response = Mock()
        video_response.status_code = 200
        video_response.url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        video_response.headers = {}
        video_response.text = '''
            <html>
                <title>LIVE - Stream - YouTube</title>
                <script>
                    "isLiveNow":true
                    "BADGE_STYLE_TYPE_LIVE_NOW"
                    "watching now</span>"
                </script>
            </html>
        '''

        mock_get.side_effect = [channel_response, video_response]
        mock_service = MagicMock()
        mock_service._credential_set = 1
        mock_service.videos.return_value.list.return_value.execute.return_value = {
            "items": [
                {
                    "snippet": {
                        "channelId": "test_channel",
                        "liveBroadcastContent": "live",
                    },
                    "liveStreamingDetails": {},
                }
            ]
        }
        mock_auth.return_value = mock_service

        with patch.object(checker, '_anti_detection_delay'):
            result = checker.check_channel_for_live('test_channel')

            # Should find live stream
            self.assertIsNotNone(result)
            self.assertTrue(result['live'])
            self.assertEqual(result['video_id'], 'dQw4w9WgXcQ')


def run_tests():
    """Run all tests with detailed output"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestAntiRateLimiting))
    suite.addTests(loader.loadTestsFromTestCase(TestLiveStreamDetection))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))

    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return success status
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
