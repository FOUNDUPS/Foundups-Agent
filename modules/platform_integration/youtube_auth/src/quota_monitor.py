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
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# America/Los_Angeles standard/daylight offsets (UTC hours).
# Used by the manual fallback when the stdlib `zoneinfo` tz database is
# unavailable on the host (e.g. Windows without the `tzdata` package).
_PACIFIC_STANDARD_OFFSET = -8   # PST = UTC-8
_PACIFIC_DAYLIGHT_OFFSET = -7   # PDT = UTC-7


def _us_pacific_offset_hours(utc_dt: datetime) -> int:
    """Return the US Pacific UTC offset (hours) for a UTC instant.

    Implements current US DST rules (Energy Policy Act of 2005):
    DST starts 2nd Sunday of March 02:00 local, ends 1st Sunday of
    November 02:00 local. This is a pure-stdlib fallback used only when
    `zoneinfo` cannot load 'America/Los_Angeles'. It is an approximation
    around the exact DST transition hour but is exact for daily-quota
    boundary purposes (midnight), which never falls in the ambiguous hour.
    """
    year = utc_dt.year

    def _nth_sunday(month: int, n: int) -> datetime:
        # First day of month in UTC
        d = datetime(year, month, 1)
        # weekday(): Mon=0 .. Sun=6 ; days until first Sunday
        first_sunday = 1 + ((6 - d.weekday()) % 7)
        day = first_sunday + (n - 1) * 7
        return datetime(year, month, day)

    # DST transitions occur at 02:00 LOCAL; approximate the instant in UTC
    # by adding the standard offset (the side we are leaving/entering for the
    # comparison boundary). Standard offset is -8, so 02:00 PT ~ 10:00 UTC.
    dst_start = _nth_sunday(3, 2).replace(hour=2) - timedelta(hours=_PACIFIC_STANDARD_OFFSET)
    dst_end = _nth_sunday(11, 1).replace(hour=2) - timedelta(hours=_PACIFIC_DAYLIGHT_OFFSET)

    if dst_start <= utc_dt < dst_end:
        return _PACIFIC_DAYLIGHT_OFFSET
    return _PACIFIC_STANDARD_OFFSET


def to_pacific(dt: datetime) -> datetime:
    """Convert a datetime to America/Los_Angeles wall-clock time.

    Prefers stdlib `zoneinfo`; falls back to a manual US-DST calculation
    when the tz database is unavailable. A naive input is treated as local
    system time (matching the historical behaviour of datetime.now()).

    Returns a tz-aware datetime in Pacific time.
    """
    if dt.tzinfo is None:
        dt = dt.astimezone()  # attach local system tz
    try:
        from zoneinfo import ZoneInfo
        return dt.astimezone(ZoneInfo("America/Los_Angeles"))
    except Exception:
        # tzdata unavailable - manual fallback
        utc_dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        offset = _us_pacific_offset_hours(utc_dt)
        pacific_tz = timezone(timedelta(hours=offset))
        return dt.astimezone(pacific_tz)

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
    
    def __init__(self, memory_dir: str = "memory",
                 now_provider: Optional[Callable[[], datetime]] = None):
        """
        Initialize quota monitor.

        Args:
            memory_dir: Directory for storing quota tracking data
            now_provider: Optional callable returning the current datetime.
                Defaults to datetime.now. Injectable for deterministic tests
                (no real wall-clock / network dependency).
        """
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(exist_ok=True)

        self.quota_file = self.memory_dir / "quota_usage.json"
        self.alert_file = self.memory_dir / "quota_alerts.json"

        # Injectable clock (WSP 97: deterministic, verifiable time handling)
        self._now_provider = now_provider or datetime.now

        # Real Google quota signals (quotaExceeded / 403) reported per
        # credential set. A drift-corrupted LOCAL counter alone must NEVER
        # raise CRITICAL (WSP 97 truth signaling); only a real signal or a
        # reconciled local counter at/above threshold may alert.
        self._google_quota_signals: Dict[int, Dict] = {}

        # Load existing data (reconciles drift on load - WSP 97)
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

    def _now(self) -> datetime:
        """Current local datetime via injectable provider (WSP 97)."""
        return self._now_provider()

    def _now_pacific(self) -> datetime:
        """Current America/Los_Angeles wall-clock time (tz-aware)."""
        return to_pacific(self._now())

    def _load_usage_data(self) -> Dict:
        """Load quota usage data from file."""
        if self.quota_file.exists():
            try:
                with open(self.quota_file, 'r', encoding="utf-8") as f:
                    data = json.load(f)
                return self._normalize_usage_data(data)
            except Exception as e:
                logger.error(f"Error loading quota data: {e}")

        # Initialize empty usage data (last_reset anchored to Pacific time)
        return {
            'sets': {},
            'last_reset': self._now_pacific().isoformat()
        }

    def _normalize_usage_data(self, data: Dict) -> Dict:
        """Ensure quota usage data has required keys."""
        if not isinstance(data, dict):
            return {
                'sets': {},
                'last_reset': self._now_pacific().isoformat()
            }
        if not isinstance(data.get('sets'), dict):
            data['sets'] = {}
        if not data.get('last_reset'):
            data['last_reset'] = self._now_pacific().isoformat()

        # Migrate old set entries without 'operations' key (WSP 97 fix)
        for set_key, set_data in data['sets'].items():
            if isinstance(set_data, dict) and 'operations' not in set_data:
                set_data['operations'] = {}

        # Reconcile drift: the stored 'used' counter must equal the sum of
        # per-operation units. A drifted (e.g. corrupted/inflated) counter
        # is a WSP 97 truth violation - it can make the monitor emit a
        # CRITICAL "~99% quota" alert from a stale local number rather than
        # a real Google quotaExceeded. On load, trust the operations ledger
        # and reconcile 'used' down/up to match it.
        for set_key, set_data in data['sets'].items():
            if not isinstance(set_data, dict):
                continue
            operations = set_data.get('operations') or {}
            used_from_ops = 0
            for op in operations.values():
                if isinstance(op, dict):
                    try:
                        used_from_ops += int(op.get('units', 0) or 0)
                    except (TypeError, ValueError):
                        continue
            try:
                current_used = int(set_data.get('used', 0) or 0)
            except (TypeError, ValueError):
                current_used = 0

            if abs(current_used - used_from_ops) > 1:
                logger.warning(
                    f"[QUOTA-DRIFT] set {set_key} used={current_used} "
                    f"ops_sum={used_from_ops}; reconciling to {used_from_ops}"
                )
                set_data['used'] = used_from_ops

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
        set_data['last_call'] = self._now().isoformat()
        
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
        """Reset quotas when the Pacific-Time calendar day rolls over.

        YouTube/Google daily quota resets at midnight America/Los_Angeles,
        NOT on a rolling-24h-from-last_reset basis. We therefore compare the
        Pacific calendar DATE of the last reset against the Pacific calendar
        date of now: if now is a later PT day, the quota has reset.

        Pacific time is derived via stdlib zoneinfo when available and a
        manual US-DST fallback otherwise (see to_pacific()). last_reset is
        persisted as Pacific wall-clock isoformat.
        """
        now_pt = self._now_pacific()

        raw_last_reset = self.usage_data.get('last_reset')
        try:
            last_reset_dt = datetime.fromisoformat(raw_last_reset)
        except (TypeError, ValueError):
            # Corrupt/absent timestamp: re-anchor to now, do not wipe usage.
            self.usage_data['last_reset'] = now_pt.isoformat()
            self._save_usage_data()
            return

        last_reset_pt = to_pacific(last_reset_dt)

        if now_pt.date() > last_reset_pt.date():
            logger.info("[QUOTA-RESET] New Pacific-Time day - clearing quota usage data")
            self.usage_data = {
                'sets': {},
                'last_reset': now_pt.isoformat()
            }
            self._save_usage_data()
    
    def report_quota_signal(self, credential_set: int, signal: str = 'quotaExceeded'):
        """Record a REAL Google quota signal for a credential set (WSP 97).

        Call this when the YouTube API itself reports exhaustion
        (HTTP 403 with reason 'quotaExceeded' / 'dailyLimitExceeded'). This
        is the authoritative truth signal: unlike the local counter it cannot
        drift. It forces a CRITICAL alert and is recorded so subsequent
        _check_alerts() calls treat the set as genuinely exhausted until the
        Pacific-Time daily reset clears it.

        Args:
            credential_set: Credential set number that received the signal.
            signal: The Google reason string (for the audit trail).
        """
        self._google_quota_signals[credential_set] = {
            'signal': signal,
            'timestamp': self._now().isoformat(),
        }
        logger.warning(
            f"[QUOTA-SIGNAL] Real Google quota signal '{signal}' for set {credential_set}"
        )
        self._check_alerts(credential_set)

    def _has_real_quota_signal(self, credential_set: int) -> bool:
        """Whether a real Google quota signal is currently active for a set.

        Signals are cleared on the Pacific-Time daily reset (which rebuilds
        usage_data); a signal older than the current last_reset is stale.
        """
        sig = self._google_quota_signals.get(credential_set)
        if not sig:
            return False
        try:
            sig_dt = to_pacific(datetime.fromisoformat(sig['timestamp']))
            last_reset_dt = to_pacific(datetime.fromisoformat(self.usage_data['last_reset']))
            # Stale if it predates the current PT day's reset.
            if sig_dt.date() < last_reset_dt.date():
                self._google_quota_signals.pop(credential_set, None)
                return False
        except (TypeError, ValueError, KeyError):
            pass
        return True

    def _check_alerts(self, credential_set: int):
        """Emit quota alerts under WSP 97 truth gating.

        A CRITICAL/WARNING alert is emitted ONLY when at least one of:
          - a REAL Google quota signal is active (report_quota_signal), OR
          - the RECONCILED local 'used' counter is >= the threshold.

        Because the local counter is reconciled to the operations ledger on
        load, a drift-corrupted counter alone can no longer trigger a false
        CRITICAL: it is corrected before this check ever runs.
        """
        set_key = str(credential_set)
        used = 0
        if set_key in self.usage_data['sets']:
            used = self.usage_data['sets'][set_key].get('used', 0)

        limit = self.daily_limits.get(credential_set, 10000)
        usage_percent = (used / limit) if limit > 0 else 0

        real_signal = self._has_real_quota_signal(credential_set)

        alert = None
        # CRITICAL: real Google signal OR reconciled local usage >= critical.
        if real_signal or usage_percent >= self.critical_threshold:
            trigger = 'google_signal' if real_signal else 'local_counter'
            alert = {
                'timestamp': self._now().isoformat(),
                'credential_set': credential_set,
                'severity': 'CRITICAL',
                'usage_percent': usage_percent * 100,
                'used': used,
                'limit': limit,
                'trigger': trigger,
                'message': f"[ALERT] CRITICAL: Set {credential_set} at {usage_percent*100:.1f}% quota usage!"
            }
            logger.critical(alert['message'])

        # WARNING: only on reconciled local usage (no real signal needed,
        # but a drift-corrupted counter is already reconciled away above).
        elif usage_percent >= self.warning_threshold:
            # Only alert once per threshold crossing (within the last hour).
            now = self._now()
            recent_alerts = [
                a for a in self.alerts
                if a['credential_set'] == credential_set
                and datetime.fromisoformat(a['timestamp']) > now - timedelta(hours=1)
            ]

            if not any(a['severity'] == 'WARNING' for a in recent_alerts):
                alert = {
                    'timestamp': now.isoformat(),
                    'credential_set': credential_set,
                    'severity': 'WARNING',
                    'usage_percent': usage_percent * 100,
                    'used': used,
                    'limit': limit,
                    'trigger': 'local_counter',
                    'message': f"[WARNING] Set {credential_set} at {usage_percent*100:.1f}% quota usage"
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
            'timestamp': self._now().isoformat(),
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
