# -*- coding: utf-8 -*-
import sys
import io


"""
# === UTF-8 ENFORCEMENT (WSP 90) ===
# Prevent UnicodeEncodeError on Windows systems
# Only apply when running as main script, not during import
if __name__ == '__main__' and sys.platform.startswith('win'):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except (OSError, ValueError):
        # Ignore if stdout/stderr already wrapped or closed
        pass
# === END UTF-8 ENFORCEMENT ===

Delay Utilities Module
Infrastructure utilities for intelligent delay calculation and throttling

WSP 3: Infrastructure Domain - Shared delay/throttling utilities
WSP 49: Module structure with clear responsibilities
WSP 62: Focused delay and throttling policies

Extracted from stream_resolver.py vibecoded functionality
"""

import logging
import random
from typing import Optional

logger = logging.getLogger(__name__)

class DelayUtils:
    """
    Delay calculation utilities extracted from stream_resolver.py

    Provides centralized delay calculation functionality for:
    - Exponential backoff with jitter
    - Activity-based throttling
    - Intelligent retry delays
    """

    # Class constants for delay calculation
    MIN_DELAY = 5.0
    MAX_DELAY = 1800.0  # 30 minutes
    JITTER_FACTOR = 0.1  # 10% jitter
    EXPONENTIAL_BACKOFF_BASE = 2.0
    MAX_BACKOFF_DELAY = 300.0  # 5 minutes

    ACTIVITY_POLL_DELAYS_SECONDS = (60, 120, 240, 480, 960, 1920, 3600)

    @staticmethod
    def calculate_activity_poll_delay(
        previous_delay_seconds: int = 60, *, activity: Optional[bool] = None
    ) -> int:
        """Return the next exact activity-poll delay, without sleeping or I/O.

        The initial call returns 60 seconds. After a successful complete read,
        False doubles the previous delay up to 3600 seconds; True resets to 60.
        Only a new, accepted message is activity: replayed IDs and own ACKs are
        excluded by the caller. None means no successful observation (including
        read/auth failures) and preserves the delay, not an empty result.

        This policy owns no cursor, deduplication, checkpoint or scheduler.
        An admitted caller must persist those atomically with its next deadline
        and restore the prior interval rather than defaulting on every poll.
        """
        if (
            type(previous_delay_seconds) is not int
            or previous_delay_seconds not in DelayUtils.ACTIVITY_POLL_DELAYS_SECONDS
        ):
            raise ValueError("invalid_activity_poll_delay_seconds")
        if activity is not None and type(activity) is not bool:
            raise ValueError("activity_must_be_bool_or_none")
        if activity is None:
            return previous_delay_seconds
        if activity:
            return 60
        return min(previous_delay_seconds * 2, 3600)

    @staticmethod
    def calculate_enhanced_delay(
        active_users: int = 0,
        previous_delay: Optional[float] = None,
        consecutive_failures: int = 0,
        retry_count: int = 0,
        force_dev_delay: bool = False
    ) -> float:
        """
        Enhanced delay calculation with exponential backoff and circuit breaker awareness.
        Intelligently scales from 5 seconds to 30 minutes based on activity.

        Args:
            active_users: Number of active users in chat (0 if unknown)
            previous_delay: Previous delay used (for smoothing)
            consecutive_failures: Number of consecutive failed attempts
            retry_count: Current retry attempt number
            force_dev_delay: Force 1 second delay for testing

        Returns:
            Delay in seconds
        """
        if force_dev_delay:
            return 1.0  # Force 1 second delay for fast testing

        # Progressive delay calculation based on consecutive failures
        # This creates intelligent throttling that scales to 30 minutes
        if consecutive_failures == 0:
            # First check - quick 5 second delay
            base_delay = DelayUtils.MIN_DELAY
        elif consecutive_failures <= 5:
            # First 5 failures: 5s -> 10s -> 20s -> 30s -> 45s -> 60s
            base_delay = DelayUtils.MIN_DELAY * (1.5 ** consecutive_failures)
        elif consecutive_failures <= 10:
            # Next 5 failures: 90s -> 120s -> 180s -> 240s -> 300s (5 min)
            base_delay = 60 + (30 * (consecutive_failures - 5))
        elif consecutive_failures <= 15:
            # Next 5 failures: 360s -> 480s -> 600s -> 900s -> 1200s (20 min)
            base_delay = 300 + ((consecutive_failures - 10) * 180)
        else:
            # After 15 failures: scale up to 30 minutes (1800s)
            base_delay = min(1200 + ((consecutive_failures - 15) * 120), DelayUtils.MAX_DELAY)

        # If we have active users (stream is live), override with activity-based delay
        if active_users > 0:
            if active_users > 1000:  # High activity
                base_delay = DelayUtils.MIN_DELAY
            elif active_users > 100:  # Medium activity
                base_delay = DelayUtils.MIN_DELAY * 2
            elif active_users > 10:  # Low activity
                base_delay = DelayUtils.MIN_DELAY * 4
            else:  # Very low activity but stream exists
                base_delay = 30  # Check every 30 seconds when stream is quiet

        # Apply exponential backoff for API errors/retries
        if retry_count > 0:
            backoff_multiplier = DelayUtils.EXPONENTIAL_BACKOFF_BASE ** retry_count
            base_delay *= backoff_multiplier
            base_delay = min(base_delay, DelayUtils.MAX_BACKOFF_DELAY)

        # Smooth transitions using previous delay to prevent jarring changes
        if previous_delay is not None and previous_delay > 0:
            # Weighted average: 70% previous, 30% new for smooth transitions
            smoothing_factor = 0.3
            base_delay = (base_delay * smoothing_factor) + (previous_delay * 0.7)

        # Add random jitter for human-like behavior (prevents synchronized requests)
        jitter = base_delay * DelayUtils.JITTER_FACTOR
        delay = base_delay + random.uniform(-jitter, jitter)

        # Ensure delay stays within bounds
        delay = max(DelayUtils.MIN_DELAY, min(delay, DelayUtils.MAX_DELAY))

        # Log the delay calculation for transparency
        if delay >= 60:
            logger.info(f"[THROTTLE] Intelligent throttle: {delay/60:.1f} minutes (failures: {consecutive_failures}, retry: {retry_count})")
        else:
            logger.debug(f"[DELAY] Delay: {delay:.1f}s (failures: {consecutive_failures}, retry: {retry_count})")

        return delay

    @staticmethod
    def calculate_circuit_breaker_delay(
        failure_count: int,
        timeout_seconds: int = 300
    ) -> float:
        """
        Calculate delay for circuit breaker timeout.

        Args:
            failure_count: Number of consecutive failures
            timeout_seconds: Base timeout in seconds

        Returns:
            Delay before attempting reset
        """
        # Exponential backoff for circuit breaker resets
        if failure_count <= 3:
            return timeout_seconds
        else:
            return timeout_seconds * (2 ** (failure_count - 3))

    @staticmethod
    def add_jitter_to_delay(base_delay: float, jitter_percent: float = 0.1) -> float:
        """
        Add random jitter to a base delay.

        Args:
            base_delay: Base delay in seconds
            jitter_percent: Percentage of jitter to add (0.1 = 10%)

        Returns:
            Delay with jitter applied
        """
        jitter = base_delay * jitter_percent
        return base_delay + random.uniform(-jitter, jitter)


# Convenience functions for backward compatibility
def calculate_enhanced_delay(
    active_users: int = 0,
    previous_delay: Optional[float] = None,
    consecutive_failures: int = 0,
    retry_count: int = 0,
    force_dev_delay: bool = False
) -> float:
    """Backward compatibility function."""
    return DelayUtils.calculate_enhanced_delay(
        active_users, previous_delay, consecutive_failures,
        retry_count, force_dev_delay
    )
