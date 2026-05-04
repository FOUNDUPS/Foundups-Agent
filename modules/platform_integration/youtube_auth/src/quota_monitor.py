"""
YouTube API Quota Monitor
WSP-Compliant: Monitors quota usage and sends alerts

This module provides real-time quota monitoring, usage tracking, and alerting
when quota limits are approached or exceeded.
"""

# === UTF-8 ENFORCEMENT (WSP 90) ===
import sys
import io
if __name__ == '__main__' and sys.platform.startswith('win'):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except (OSError, ValueError):
        # Ignore if stdout/stderr already wrapped or closed
        pass
# === END UTF-8 ENFORCEMENT ===


import os
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class QuotaMonitor:
    """Monitors YouTube API quota usage and provides alerting."""
    
    # YouTube API quota costs (in quota units)
    QUOTA_COSTS = {
        # Read operations
        'channels.list': 1,
        'videos.list': 1,
        'search.list': 100,
        'liveChatMessages.list': 5,
        'liveStreams.list': 1,
        'liveBroadcasts.list': 1,
        
        # Write operations
        'liveChatMessages.insert': 200,
        'liveChatBans.insert': 200,
        'liveChatBans.delete': 50,
        'comments.insert': 50,
        'comments.update': 50,
        'comments.delete': 50,
    }
    
    def __init__(self, memory_dir: str = "memory"):
        """
        Initialize quota monitor.
        
        Args:
            memory_dir: Directory for storing quota tracking data
        """
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(exist_ok=True)
        
        self.quota_file = self.memory_dir / "quota_usage.json"
        self.alert_file = self.memory_dir / "quota_alerts.json"
        
        # Load existing data
        self.usage_data = self._load_usage_data()
        self.alerts = self._load_alerts()
        
        # Quota limits per credential set (YouTube default: 10,000 units/day)
        # Only 2 sets configured: Set 1 (UnDaoDu) and Set 10 (Foundups)
        self.daily_limits = {
            1: 10000,   # Set 1: UnDaoDu
            10: 10000,  # Set 10: Foundups
        }
        
        # Alert thresholds
        self.warning_threshold = 0.8  # Alert at 80% usage
        self.critical_threshold = 0.95  # Critical alert at 95% usage
        
    def _load_usage_data(self) -> Dict:
        """Load quota usage data from file."""
        if self.quota_file.exists():
            try:
                with open(self.quota_file, 'r', encoding="utf-8") as f:
                    data = json.load(f)
                return self._normalize_usage_data(data)
            except Exception as e:
                logger.error(f"Error loading quota data: {e}")

        # Initialize empty usage data
        return {
            'sets': {},
            'last_reset': datetime.now().isoformat()
        }

    def _normalize_usage_data(self, data: Dict) -> Dict:
        """Ensure quota usage data has required keys."""
        if not isinstance(data, dict):
            return {
                'sets': {},
                'last_reset': datetime.now().isoformat()
            }
        if not isinstance(data.get('sets'), dict):
            data['sets'] = {}
        if not data.get('last_reset'):
            data['last_reset'] = datetime.now().isoformat()

        # Migrate old set entries without 'operations' key (WSP 97 fix)
        for set_key, set_data in data['sets'].items():
            if isinstance(set_data, dict) and 'operations' not in set_data:
                set_data['operations'] = {}

        return data
    
    def _save_usage_data(self):
        """Save quota usage data to file."""
        try:
            with open(self.quota_file, 'w', encoding="utf-8") as f:
                json.dump(self.usage_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving quota data: {e}")
    
    def _load_alerts(self) -> List[Dict]:
        """Load alert history."""
        if self.alert_file.exists():
            try:
                with open(self.alert_file, 'r', encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading alerts: {e}")
        return []
    
    def _save_alert(self, alert: Dict):
        """Save an alert to history."""
        self.alerts.append(alert)
        # Keep only last 100 alerts
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]
        
        try:
            with open(self.alert_file, 'w', encoding="utf-8") as f:
                json.dump(self.alerts, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving alert: {e}")
    
    def track_api_call(self, credential_set: int, operation: str, units: Optional[int] = None):
        """
        Track an API call's quota usage.

        Args:
            credential_set: Which credential set was used (1=UnDaoDu or 10=Foundups)
            operation: The API operation (e.g., 'liveChatMessages.list')
            units: Optional manual quota units (if not in QUOTA_COSTS)
        """
        # Reset if new day (quotas reset at midnight Pacific Time)
        self._check_daily_reset()
        
        # Initialize set data if needed
        set_key = str(credential_set)
        if set_key not in self.usage_data['sets']:
            self.usage_data['sets'][set_key] = {
                'used': 0,
                'operations': {},
                'last_call': None
            }
        
        # Calculate quota cost
        if units is None:
            units = self.QUOTA_COSTS.get(operation, 1)
        
        # Update usage
        set_data = self.usage_data['sets'][set_key]
        set_data['used'] += units
        set_data['last_call'] = datetime.now().isoformat()
        
        # Track operation counts
        if operation not in set_data['operations']:
            set_data['operations'][operation] = {'count': 0, 'units': 0}
        set_data['operations'][operation]['count'] += 1
        set_data['operations'][operation]['units'] += units
        
        # Save data
        self._save_usage_data()
        
        # Check for alerts
        self._check_alerts(credential_set)
        
        logger.debug(f"[DATA] Set {credential_set}: {operation} used {units} units "
                    f"(Total: {set_data['used']}/{self.daily_limits[credential_set]})")
    
    def _check_daily_reset(self):
        """Check if quotas should reset (new day in Pacific Time)."""
        last_reset = datetime.fromisoformat(self.usage_data['last_reset'])
        now = datetime.now()
        
        # Check if it's been 24 hours
        if now - last_reset > timedelta(hours=24):
            logger.info("[U+1F4C5] Daily quota reset - clearing usage data")
            self.usage_data = {
                'sets': {},
                'last_reset': now.isoformat()
            }
            self._save_usage_data()
    
    def _check_alerts(self, credential_set: int):
        """Check if usage warrants an alert."""
        set_key = str(credential_set)
        if set_key not in self.usage_data['sets']:
            return
        
        used = self.usage_data['sets'][set_key]['used']
        limit = self.daily_limits[credential_set]
        usage_percent = used / limit
        
        alert = None
        if usage_percent >= self.critical_threshold:
            alert = {
                'timestamp': datetime.now().isoformat(),
                'credential_set': credential_set,
                'severity': 'CRITICAL',
                'usage_percent': usage_percent * 100,
                'used': used,
                'limit': limit,
                'message': f"[ALERT] CRITICAL: Set {credential_set} at {usage_percent*100:.1f}% quota usage!"
            }
            logger.critical(alert['message'])
            
        elif usage_percent >= self.warning_threshold:
            # Only alert once per threshold crossing
            recent_alerts = [a for a in self.alerts 
                           if a['credential_set'] == credential_set 
                           and datetime.fromisoformat(a['timestamp']) > datetime.now() - timedelta(hours=1)]
            
            if not any(a['severity'] == 'WARNING' for a in recent_alerts):
                alert = {
                    'timestamp': datetime.now().isoformat(),
                    'credential_set': credential_set,
                    'severity': 'WARNING',
                    'usage_percent': usage_percent * 100,
                    'used': used,
                    'limit': limit,
                    'message': f"[U+26A0]️ WARNING: Set {credential_set} at {usage_percent*100:.1f}% quota usage"
                }
                logger.warning(alert['message'])
        
        if alert:
            self._save_alert(alert)
            self._trigger_external_alert(alert)
    
    def _trigger_external_alert(self, alert: Dict):
        """
        Trigger external alerting mechanisms.
        
        Future: Send to Discord, email, SMS, etc.
        """
        # Write to alert file for external monitoring
        alert_trigger = self.memory_dir / "quota_alert_trigger.txt"
        try:
            with open(alert_trigger, 'w', encoding="utf-8") as f:
                f.write(json.dumps(alert, indent=2))
            logger.info(f"[U+1F4E2] Alert written to {alert_trigger}")
        except Exception as e:
            logger.error(f"Failed to write alert trigger: {e}")
    
    def get_usage_summary(self) -> Dict:
        """Get current usage summary for all credential sets."""
        self._check_daily_reset()
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_available': sum(self.daily_limits.values()),
            'total_used': 0,
            'sets': {}
        }
        
        for set_num in [1, 10]:  # Only sets 1 (UnDaoDu) and 10 (Foundups) are configured
            set_key = str(set_num)
            limit = self.daily_limits.get(set_num, 10000)

            if set_key in self.usage_data['sets']:
                used = self.usage_data['sets'][set_key]['used']
                summary['total_used'] += used
            else:
                used = 0

            summary['sets'][set_num] = {
                'used': used,
                'limit': limit,
                'available': limit - used,
                'usage_percent': (used / limit * 100) if limit > 0 else 0,
                'status': self._get_status(used, limit)
            }
        
        summary['total_available_remaining'] = summary['total_available'] - summary['total_used']
        summary['total_usage_percent'] = (summary['total_used'] / summary['total_available'] * 100) if summary['total_available'] > 0 else 0
        
        return summary
    
    def _get_status(self, used: int, limit: int) -> str:
        """Get status string for usage level."""
        if limit == 0:
            return "DISABLED"
        
        percent = used / limit
        if percent >= self.critical_threshold:
            return "CRITICAL"
        elif percent >= self.warning_threshold:
            return "WARNING"
        elif percent >= 0.5:
            return "MODERATE"
        else:
            return "HEALTHY"
    
    def get_best_credential_set(self) -> Optional[int]:
        """
        Get the credential set with most available quota.
        
        Returns:
            Credential set number (1-7) or None if all exhausted
        """
        self._check_daily_reset()
        
        best_set = None
        max_available = 0
        
        for set_num in [1, 10]:  # Only sets 1 (UnDaoDu) and 10 (Foundups) are configured
            set_key = str(set_num)
            limit = self.daily_limits.get(set_num, 10000)

            if set_key in self.usage_data['sets']:
                used = self.usage_data['sets'][set_key]['used']
            else:
                used = 0

            available = limit - used

            # Skip sets that are critically low
            if available > limit * (1 - self.warning_threshold) and available > max_available:
                max_available = available
                best_set = set_num
        
        if best_set:
            logger.info(f"[DATA] Best credential set: {best_set} ({max_available} units available)")
        else:
            logger.warning("[U+26A0]️ No credential sets have sufficient quota")
        
        return best_set
    
    def estimate_operations_remaining(self, credential_set: int, operation: str) -> int:
        """
        Estimate how many more operations can be performed.
        
        Args:
            credential_set: Credential set number
            operation: API operation name
            
        Returns:
            Number of operations remaining
        """
        set_key = str(credential_set)
        limit = self.daily_limits[credential_set]
        
        if set_key in self.usage_data['sets']:
            used = self.usage_data['sets'][set_key]['used']
        else:
            used = 0
        
        available = limit - used
        cost = self.QUOTA_COSTS.get(operation, 1)
        
        return available // cost
    
    def generate_report(self) -> str:
        """Generate a detailed quota usage report."""
        summary = self.get_usage_summary()
        
        report = []
        report.append("=" * 60)
        report.append("YOUTUBE API QUOTA USAGE REPORT")
        report.append(f"Generated: {summary['timestamp']}")
        report.append("=" * 60)
        report.append("")
        
        # Overall summary
        report.append(f"Total Quota: {summary['total_available']:,} units/day")
        report.append(f"Total Used:  {summary['total_used']:,} units ({summary['total_usage_percent']:.1f}%)")
        report.append(f"Remaining:   {summary['total_available_remaining']:,} units")
        report.append("")
        
        # Per-set details
        report.append("CREDENTIAL SET BREAKDOWN:")
        report.append("-" * 40)
        
        for set_num, data in summary['sets'].items():
            status_emoji = {
                'HEALTHY': '[OK]',
                'MODERATE': '[DATA]',
                'WARNING': '[U+26A0]️',
                'CRITICAL': '[ALERT]',
                'DISABLED': '[FAIL]'
            }.get(data['status'], '[U+2753]')
            
            report.append(f"Set {set_num}: {status_emoji} {data['status']}")
            report.append(f"  Used: {data['used']:,}/{data['limit']:,} ({data['usage_percent']:.1f}%)")
            
            # Show operation breakdown if available
            set_key = str(set_num)
            if set_key in self.usage_data['sets'] and 'operations' in self.usage_data['sets'][set_key]:
                ops = self.usage_data['sets'][set_key]['operations']
                if ops:
                    report.append("  Top operations:")
                    sorted_ops = sorted(ops.items(), key=lambda x: x[1]['units'], reverse=True)[:3]
                    for op_name, op_data in sorted_ops:
                        report.append(f"    - {op_name}: {op_data['count']} calls, {op_data['units']} units")
            report.append("")
        
        # Recent alerts
        if self.alerts:
            report.append("RECENT ALERTS:")
            report.append("-" * 40)
            recent = self.alerts[-5:]  # Last 5 alerts
            for alert in reversed(recent):
                report.append(f"{alert['timestamp']}: {alert['message']}")
            report.append("")
        
        report.append("=" * 60)
        
        return "\n".join(report)


# Example usage
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    monitor = QuotaMonitor()
    
    # Simulate some API calls
    monitor.track_api_call(1, 'liveChatMessages.list')
    monitor.track_api_call(1, 'liveChatMessages.insert')
    monitor.track_api_call(2, 'search.list')
    
    # Get usage summary
    summary = monitor.get_usage_summary()
    print(json.dumps(summary, indent=2))
    
    # Generate report
    print("\n" + monitor.generate_report())
    
    # Find best set
    best = monitor.get_best_credential_set()
    print(f"\nBest credential set: {best}")
    
    # Estimate remaining operations
    remaining = monitor.estimate_operations_remaining(1, 'liveChatMessages.list')
    print(f"Set 1 can do {remaining} more liveChatMessages.list calls")


def get_available_credential_sets():
    """
    Dynamically detect available credential sets from .env configuration.
    Returns list of set numbers that have both client secrets and token files configured.
    """
    from dotenv import load_dotenv
    load_dotenv()
    
    available_sets = []
    for i in range(1, 11):  # Check all possible sets 1-10
        client_secrets = os.getenv(f'GOOGLE_CLIENT_SECRETS_FILE_{i}')
        token_file = os.getenv(f'OAUTH_TOKEN_FILE_{i}')
        
        if client_secrets and token_file:
            # Verify files actually exist
            if os.path.exists(client_secrets):
                available_sets.append(i)
    
    logger.debug(f"Available credential sets detected: {available_sets}")
    return available_sets
