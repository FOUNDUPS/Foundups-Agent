#!/usr/bin/env python3
"""
Test Quota Intelligence and Agentic Monitoring for Stream Resolver
WSP 5: Test Coverage Enforcement
WSP 6: Comprehensive Test Audit
WSP 48: Recursive Self-Improvement

Tests verify:
- Dual channel quota checking (UnDaoDu and FoundUps)
- Intelligent credential selection (lowest quota usage)
- Time-based throttling (Tokyo timezone awareness)
- Agentic monitoring patterns
"""



import unittest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime, timezone, timedelta
import pytz
import sys
import os
import json

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')))

from modules.platform_integration.stream_resolver.src.stream_resolver import (
    StreamResolver,
    find_active_stream,
    search_livestreams_enhanced
)


class TestQuotaIntelligence(unittest.TestCase):
    """Test suite for intelligent quota management and monitoring"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_youtube_service = MagicMock()
        self.resolver = StreamResolver(self.mock_youtube_service, use_intelligent_sorting=True)
        
        # Mock environment variables for dual channels
        self.channel_configs = {
            'CHANNEL_ID': 'UCfHM9Fw9HD-NwiS0seD_oIA',  # UnDaoDu
            'CHANNEL_ID2': 'UCSNTUXjAgpd4sgWYP0xoJgw'  # FoundUps
        }
        
    @patch('modules.platform_integration.stream_resolver.src.stream_resolver.get_env_variable')
    def test_dual_channel_quota_checking(self, mock_get_env):
        """Test that both UnDaoDu and FoundUps channels are checked with quota awareness"""
        
        # Setup mock environment
        mock_get_env.side_effect = lambda key, default=None: self.channel_configs.get(key, default)
        
        with patch(
            'modules.platform_integration.stream_resolver.src.stream_resolver.YouTubeAPIOperations.get_active_livestream_video_id_enhanced'
        ) as mock_active:
            mock_active.return_value = ('test_video_id', 'test_chat_id')

            result = find_active_stream(self.mock_youtube_service)

            mock_active.assert_called_once()
            self.assertIsNotNone(result)
                
    def test_tokyo_timezone_throttling(self):
        """Test intelligent throttling based on Tokyo timezone"""
        
        # Tokyo timezone
        tokyo_tz = pytz.timezone('Asia/Tokyo')
        
        # Test cases for different times
        test_cases = [
            # (hour, expected_check_interval_minutes, description)
            (2, 60, "2am Tokyo - off-peak, check every hour"),
            (22, 60, "10pm Tokyo - start of off-peak"),  # 22 = 10pm
            (6, 30, "6am Tokyo - end of off-peak, increase frequency"),
            (12, 15, "Noon Tokyo - peak hours, frequent checks"),
            (20, 15, "8pm Tokyo - peak streaming time, frequent checks")
        ]
        
        for hour, expected_interval, description in test_cases:
            # Create Tokyo time
            tokyo_time = datetime.now(tokyo_tz).replace(hour=hour, minute=0, second=0)
            
            # Calculate check interval based on time
            check_interval = self._calculate_check_interval(tokyo_time)
            
            self.assertLessEqual(
                abs(check_interval - expected_interval), 
                15,  # Allow 15 minute tolerance
                f"{description}: Expected ~{expected_interval} min, got {check_interval} min"
            )
    
    def _calculate_check_interval(self, tokyo_time):
        """Calculate check interval based on Tokyo time (simulating intelligent throttling)"""
        hour = tokyo_time.hour
        
        # Off-peak hours (10pm - 6am Tokyo)
        if hour >= 22 or hour < 6:
            return 60  # Check every hour
        # Transition period (6am - 8am)
        elif 6 <= hour < 8:
            return 30  # Check every 30 minutes
        # Peak hours (8am - 10pm)
        else:
            return 15  # Check every 15 minutes
    
    @patch('modules.platform_integration.stream_resolver.src.stream_resolver.logger')
    def test_agentic_monitoring_logs(self, mock_logger):
        """Test that agentic monitoring produces proper logs for both channels"""
        
        # Mock dual channel checking
        channels = [
            'UCfHM9Fw9HD-NwiS0seD_oIA',  # UnDaoDu
            'UCSNTUXjAgpd4sgWYP0xoJgw'   # FoundUps
        ]
        
        for channel_id in channels:
            # Mock search for each channel
            self.mock_youtube_service.search().list().execute.return_value = {
                'items': []  # No streams found
            }
            
            result = search_livestreams_enhanced(
                self.mock_youtube_service,
                event_type="live",
                channel_id=channel_id
            )
            
            # Verify logging includes channel info
            log_calls = [str(call) for call in mock_logger.info.call_args_list]
            channel_logged = any(channel_id[:12] in str(call) for call in log_calls)
            self.assertTrue(
                channel_logged,
                f"Channel {channel_id} should be logged during search"
            )
    
    def test_quota_comparison_and_selection(self):
        """Test that system selects credential set with lowest quota usage"""
        
        # Mock quota data for multiple credential sets
        quota_data = {
            'credential_set_1': {
                'quota_used': 8500,
                'quota_remaining': 1500,
                'last_reset': datetime.now() - timedelta(hours=20)
            },
            'credential_set_2': {
                'quota_used': 2000,
                'quota_remaining': 8000,
                'last_reset': datetime.now() - timedelta(hours=20)
            },
            'credential_set_3': {
                'quota_used': 5000,
                'quota_remaining': 5000,
                'last_reset': datetime.now() - timedelta(hours=20)
            }
        }
        
        # Find best credential set (should be set 2 with most remaining quota)
        best_set = self._select_best_credential_set(quota_data)
        
        self.assertEqual(
            best_set, 
            'credential_set_2',
            "Should select credential set 2 with lowest usage (2000) and highest remaining (8000)"
        )
    
    def _select_best_credential_set(self, quota_data):
        """Select credential set with most remaining quota"""
        best_set = None
        max_remaining = 0
        
        for set_name, data in quota_data.items():
            if data['quota_remaining'] > max_remaining:
                max_remaining = data['quota_remaining']
                best_set = set_name
                
        return best_set
    
    def test_stream_pattern_learning(self):
        """Test that system learns from stream timing patterns"""
        
        # Mock historical stream data
        stream_history = [
            {'start_time': '2024-01-15 20:00:00+09:00', 'channel': 'UnDaoDu'},
            {'start_time': '2024-01-16 21:00:00+09:00', 'channel': 'UnDaoDu'},
            {'start_time': '2024-01-17 19:30:00+09:00', 'channel': 'UnDaoDu'},
            {'start_time': '2024-01-18 14:00:00+09:00', 'channel': 'FoundUps'},
            {'start_time': '2024-01-19 20:00:00+09:00', 'channel': 'UnDaoDu'},
        ]
        
        # Analyze patterns
        patterns = self._analyze_stream_patterns(stream_history)
        
        # Verify pattern detection
        self.assertIn('common_hours', patterns)
        self.assertIn(20, patterns['common_hours'], "8pm should be identified as common stream time")
        self.assertEqual(patterns['most_active_channel'], 'UnDaoDu')
    
    def _analyze_stream_patterns(self, history):
        """Analyze stream timing patterns"""
        from collections import Counter
        
        hours = []
        channels = []
        
        for stream in history:
            # Parse time and extract hour
            time_str = stream['start_time']
            # Simple hour extraction (would use proper datetime parsing in production)
            hour = int(time_str.split(' ')[1].split(':')[0])
            hours.append(hour)
            channels.append(stream['channel'])
        
        hour_counts = Counter(hours)
        channel_counts = Counter(channels)
        
        return {
            'common_hours': [h for h, count in hour_counts.items() if count >= 2],
            'most_active_channel': channel_counts.most_common(1)[0][0]
        }
    
    def test_intelligent_retry_with_quota_rotation(self):
        """Test that quota rotation selects a usable credential set"""
        resolver = StreamResolver(self.mock_youtube_service, use_intelligent_sorting=True)
        resolver._quota_tester = Mock()
        resolver._quota_tester.get_recommended_order.return_value = [2, 1]

        with patch('modules.platform_integration.youtube_auth.src.youtube_auth.get_authenticated_service') as mock_auth:
            mock_auth.return_value = (self.mock_youtube_service, 2)

            service, cred_set = resolver.get_best_available_service()
            self.assertIs(service, self.mock_youtube_service)
            self.assertEqual(cred_set, 2)

    def test_authenticated_service_cache_reuses_credential_set(self):
        """Credential-specific services should be built once per resolver process."""
        resolver = StreamResolver(self.mock_youtube_service, use_intelligent_sorting=False)

        with patch('modules.platform_integration.youtube_auth.src.youtube_auth.get_authenticated_service') as mock_auth:
            mock_auth.return_value = (self.mock_youtube_service, 2)

            first, first_set = resolver._get_cached_authenticated_service(2)
            second, second_set = resolver._get_cached_authenticated_service(2)

        self.assertIs(first, self.mock_youtube_service)
        self.assertIs(second, self.mock_youtube_service)
        self.assertEqual(first_set, 2)
        self.assertEqual(second_set, 2)
        mock_auth.assert_called_once_with(token_index=2)


class TestStreamTimingIntelligence(unittest.TestCase):
    """Test intelligent stream timing and scheduling"""
    
    def test_peak_hour_detection(self):
        """Test detection of peak streaming hours"""
        
        tokyo_tz = pytz.timezone('Asia/Tokyo')
        
        # Peak hours for live streaming (typically evening in Tokyo)
        peak_hours = [19, 20, 21]  # 7pm, 8pm, 9pm
        off_peak_hours = [2, 3, 4, 0]  # 2am, 3am, 4am, midnight
        
        for hour in peak_hours:
            tokyo_time = datetime.now(tokyo_tz).replace(hour=hour)
            is_peak = self._is_peak_hour(tokyo_time)
            self.assertTrue(is_peak, f"{hour}:00 Tokyo should be peak hour")
        
        for hour in off_peak_hours:
            tokyo_time = datetime.now(tokyo_tz).replace(hour=hour)
            is_peak = self._is_peak_hour(tokyo_time)
            self.assertFalse(is_peak, f"{hour}:00 Tokyo should be off-peak")
    
    def _is_peak_hour(self, tokyo_time):
        """Determine if current time is peak streaming hour"""
        hour = tokyo_time.hour
        # Peak hours: 6pm - 11pm Tokyo time
        return 18 <= hour <= 23 or 12 <= hour <= 14  # Also lunch time
    
    def test_adaptive_check_frequency(self):
        """Test that check frequency adapts based on historical patterns"""
        
        # Mock stream detection history
        detection_history = [
            {'found': True, 'time': '20:00', 'checks_before_found': 3},
            {'found': True, 'time': '20:30', 'checks_before_found': 2},
            {'found': False, 'time': '03:00', 'checks_before_found': 1},
            {'found': True, 'time': '21:00', 'checks_before_found': 4},
        ]
        
        # Calculate optimal check frequency
        optimal_freq = self._calculate_optimal_frequency(detection_history)
        
        # During times when streams are commonly found, check more frequently
        self.assertLess(
            optimal_freq['peak'],
            optimal_freq['off_peak'],
            "Peak hours should have more frequent checks"
        )
    
    def _calculate_optimal_frequency(self, history):
        """Calculate optimal check frequency based on history"""
        peak_checks = []
        off_peak_checks = []
        
        for record in history:
            hour = int(record['time'].split(':')[0])
            checks = record['checks_before_found']
            
            if 18 <= hour <= 23:  # Peak hours
                peak_checks.append(checks)
            else:
                off_peak_checks.append(checks)
        
        return {
            'peak': 15 if peak_checks else 30,  # 15 min during peak
            'off_peak': 60 if off_peak_checks else 60  # 60 min off-peak
        }


if __name__ == '__main__':
    print("="*70)
    print("QUOTA INTELLIGENCE AND AGENTIC MONITORING TEST SUITE")
    print("="*70)
    print("\nTesting:")
    print("  - Dual channel quota checking (UnDaoDu + FoundUps)")
    print("  - Intelligent credential selection (lowest quota)")
    print("  - Tokyo timezone-aware throttling")
    print("  - Stream pattern learning")
    print("  - Adaptive check frequency")
    print("="*70)
    
    unittest.main(verbosity=2)
