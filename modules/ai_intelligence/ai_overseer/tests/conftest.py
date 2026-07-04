#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Global pytest configuration for AI Overseer tests."""

from __future__ import annotations

import os
import pytest

_ALLOWLIST = {
    "test_analysis.py",
    "test_planning.py",
    "test_execution.py",
    "test_mcp.py",
    "test_monitor_flow.py",
    "test_mixins_extended.py",
    "test_ii_agent_adapter.py",
    "test_openclaw_security_sentinel.py",
    "test_ai_overseer_openclaw_security.py",
    "test_openclaw_security_alerts.py",
    "test_security_correlator.py",
    "test_wsp_framework_sentinel.py",
    "test_m2m_compression_sentinel.py",
    "test_m2m_skill_shim.py",
    "test_ai_overseer_ironclaw_runtime.py",
    "test_wsp49_interface_gap_scanner.py",
    "test_vulnerability_scan_policy.py",
    "test_preflight_resolution.py",
    "test_foundup_genesis_validator.py",
    "test_autofix_executor_security.py",
    "test_foundup_launch_request.py",
    "test_intake_auth_provider.py",
    "test_intake_transport.py",
    "test_intake_packet_builder.py",
}

_HEAVY_TARGETS = [
    "test_ai_overseer.py",
    "test_ai_overseer_monitoring.py",
    "test_ai_overseer_unicode_fix.py",
    "test_daemon_monitoring_witness_loop.py",
    "holo_index",
    "modules",
]

collect_ignore = []
if os.getenv("AI_OVERSEER_HEAVY_TESTS") != "1":
    collect_ignore.extend(_HEAVY_TARGETS)


def pytest_collection_modifyitems(config, items):
    """Skip heavy legacy suites unless explicitly requested."""
    if os.getenv("AI_OVERSEER_HEAVY_TESTS") == "1":
        return

    skip_marker = pytest.mark.skip(
        reason="Heavy AI Overseer regression skipped (set AI_OVERSEER_HEAVY_TESTS=1 to enable)",
    )

    for item in items:
        if item.fspath.basename not in _ALLOWLIST:
            item.add_marker(skip_marker)
