#!/usr/bin/env python3
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

WRE Integration Layer - Connects DAEs to Recursive Learning
WSP 48: Recursive Self-Improvement Protocol

This module bridges the gap between DAEs and the WRE learning system.
When DAEs encounter errors or successes, they report here for learning.
"""

import logging
import traceback
from typing import Any, Dict, Optional
from pathlib import Path
import asyncio
import json
from datetime import datetime

from .learning import RecursiveLearningEngine
from .core import ErrorPattern, PatternType

# WSP 87: Fingerprint system deprecated - use NAVIGATION.py instead
# from .wre_fingerprint_integration import WREFingerprintIntegration  # DEPRECATED
WREFingerprintIntegration = None  # Navigation now uses NAVIGATION.py

logger = logging.getLogger(__name__)

# Global learning engine instance
_learning_engine: Optional[RecursiveLearningEngine] = None


def get_learning_engine() -> RecursiveLearningEngine:
    """Get or create the global learning engine instance."""
    global _learning_engine
    if _learning_engine is None:
        _learning_engine = RecursiveLearningEngine()
        logger.info("[WRE] Recursive Learning Engine initialized")
    return _learning_engine


class WREIntegration:
    """
    Integration layer for DAEs to report to WRE.
    Provides simple methods that DAEs can call.
    """

    def __init__(self):
        self.engine = get_learning_engine()
        self.error_count = 0
        self.success_count = 0
        self.patterns_found = 0

        # Add fingerprint integration if available
        self.fingerprint_nav = None
        if WREFingerprintIntegration:
            try:
                self.fingerprint_nav = WREFingerprintIntegration()
                logger.info(f"[WRE] Fingerprint navigation enabled for {self.fingerprint_nav.current_dae}")
            except Exception as e:
                logger.warning(f"[WRE] Could not enable fingerprint navigation: {e}")

    def record_error(self, error: Exception, context: Dict[str, Any] = None) -> Optional[Dict]:
        """
        Record an error for learning.

        Args:
            error: The exception that occurred
            context: Additional context (module, operation, etc.)

        Returns:
            Solution if one exists, None otherwise
        """
        try:
            self.error_count += 1

            # Reuse is a proposal; efficiency stays unmeasured without receipts.
            if self.fingerprint_nav:
                fingerprint_solution = self.fingerprint_nav.apply_pattern_from_fingerprint(error)
                if fingerprint_solution:
                    logger.info(f"[WRE] Found solution via fingerprints: {fingerprint_solution.get('message')}")
                    self.patterns_found += 1
                    return fingerprint_solution

            # Add caller context
            if context is None:
                context = {}

            # Get calling module from stack
            import inspect
            frame = inspect.currentframe()
            if frame and frame.f_back:
                caller_info = inspect.getframeinfo(frame.f_back)
                context['caller_module'] = caller_info.filename
                context['caller_function'] = caller_info.function
                context['caller_line'] = caller_info.lineno

            # Process error asynchronously
            loop = asyncio.new_event_loop()
            improvement = loop.run_until_complete(
                self.engine.process_error(error, context)
            )
            loop.close()

            # Check if we have a solution
            if improvement and improvement.solution_id in self.engine.solutions:
                solution = self.engine.solutions[improvement.solution_id]
                logger.info(f"[WRE] Found solution: {solution.description}")

                # Store in fingerprint memory for next time
                if self.fingerprint_nav:
                    self.fingerprint_nav.update_pattern_memory(
                        str(error),
                        {'solution': solution.implementation, 'confidence': solution.confidence}
                    )

                return {
                    'solution': solution.implementation,
                    'confidence': solution.confidence,
                    'description': solution.description
                }

            return None

        except Exception as e:
            logger.error(f"[WRE] Failed to record error: {e}")
            return None

    def record_success(self, operation: str, context: Dict[str, Any] = None, tokens_used: int = 0):
        """
        Record a successful operation for positive reinforcement.

        Args:
            operation: Name/ID of the operation
            context: Additional context
            tokens_used: Caller-reported token count. It is stored as
                unverified context and is not converted into savings.
        """
        try:
            self.success_count += 1

            # Store success pattern
            success_data = {
                'operation': operation,
                'timestamp': datetime.now().isoformat(),
                'reported_tokens_unverified': tokens_used,
                'context': context or {}
            }

            # Save to success patterns
            success_file = self.engine.memory_root / 'successes.json'
            successes = []
            if success_file.exists():
                with open(success_file, 'r') as f:
                    successes = json.load(f)

            successes.append(success_data)

            # Keep last 100 successes
            if len(successes) > 100:
                successes = successes[-100:]

            with open(success_file, 'w') as f:
                json.dump(successes, f, indent=2)

            logger.debug(f"[WRE] Recorded success: {operation}")

        except Exception as e:
            logger.error(f"[WRE] Failed to record success: {e}")

    def get_optimized_approach(self, operation: str) -> Optional[Dict]:
        """
        Get an optimized approach for an operation based on learned patterns.

        Args:
            operation: The operation about to be performed

        Returns:
            Optimized approach if available
        """
        try:
            # First check fingerprint patterns for instant optimization
            if self.fingerprint_nav:
                # Check if we have patterns for this operation type
                for pattern_key in self.fingerprint_nav.pattern_memory:
                    if operation.lower() in pattern_key.lower():
                        pattern = self.fingerprint_nav.pattern_memory[pattern_key]
                        return {
                            'approach': 'fingerprint_pattern',
                            'solution': pattern.get('solution'),
                            'expected_savings': None,
                            'token_reduction_measured': False,
                            'confidence': 0.9
                        }

            # Check if we have learned optimizations for this operation
            for improvement in self.engine.improvements.values():
                if operation in improvement.target and improvement.applied:
                    return {
                        'approach': improvement.after_state,
                        'expected_savings': None,
                        'token_reduction_measured': False,
                        'confidence': improvement.metrics.get('confidence', 0.5)
                    }

            return None

        except Exception as e:
            logger.error(f"[WRE] Failed to get optimized approach: {e}")
            return None

    def get_statistics(self) -> Dict[str, Any]:
        """Get current learning statistics."""
        stats = {
            'errors_recorded': self.error_count,
            'successes_recorded': self.success_count,
            'patterns_extracted': len(self.engine.error_patterns),
            'solutions_available': len(self.engine.solutions),
            'improvements_applied': self.engine.metrics['improvements_applied'],
            'tokens_saved': None,
            'token_reduction_measured': False,
            'learning_velocity': self.engine.metrics['learning_velocity'],
            'fingerprint_patterns_found': self.patterns_found
        }

        # Add fingerprint statistics if available
        if self.fingerprint_nav:
            summary = self.fingerprint_nav.get_module_summary()
            stats['fingerprint_stats'] = {
                'current_dae': summary['dae'],
                'modules_tracked': summary['total_modules'],
                'unused_modules': summary['unused_modules'],
                'token_efficiency': None,
                'token_reduction_measured': False,
            }

        return stats


# Global integration instance
_wre_integration: Optional[WREIntegration] = None


def get_wre_integration() -> WREIntegration:
    """Get or create the global WRE integration instance."""
    global _wre_integration
    if _wre_integration is None:
        _wre_integration = WREIntegration()
    return _wre_integration


# Convenience functions for DAEs to use
def record_error(error: Exception, context: Dict[str, Any] = None) -> Optional[Dict]:
    """Record an error to WRE. Returns solution if available."""
    return get_wre_integration().record_error(error, context)


def record_success(operation: str, context: Dict[str, Any] = None, tokens_used: int = 0):
    """Record a successful operation to WRE."""
    get_wre_integration().record_success(operation, context, tokens_used)


def get_optimized_approach(operation: str) -> Optional[Dict]:
    """Get optimized approach for an operation from WRE."""
    return get_wre_integration().get_optimized_approach(operation)
