"""Pytest configuration for video_indexer tests.

Gates LIVE-BROWSER tests behind an explicit opt-in flag so that automated /
default pytest runs never drive the operator's signed-in Chrome session on
port 9222.

Several tests in this package attach to a REAL signed-in Chrome via
``debuggerAddress`` (127.0.0.1:9222) and call ``driver.get(...)`` to navigate
to a hardcoded video (``8_DUQaqY6Tc``). On the operator's machine that opens
tabs in their live browser. To prevent that, every test marked
``@pytest.mark.live_browser`` is SKIPPED by default and only runs when the
``--run-live`` command-line option is passed.

WSP Compliance:
    - WSP 5: Test Coverage (gate, do not delete coverage)
    - WSP 50: Pre-Action Verification
    - WSP 84: Code Reuse (standard pytest marker + skip pattern)
"""

import pytest


def pytest_addoption(parser):
    """Register the --run-live opt-in flag (default: live-browser tests skipped)."""
    parser.addoption(
        "--run-live",
        action="store_true",
        default=False,
        help=(
            "Run live-browser tests that attach to a signed-in Chrome on port "
            "9222 and navigate the operator's session. Off by default."
        ),
    )


def pytest_configure(config):
    """Register the live_browser marker so it is not an unknown-mark warning."""
    config.addinivalue_line(
        "markers",
        "live_browser: test attaches to a signed-in Chrome on port 9222 and "
        "drives the operator's live browser session; skipped unless --run-live "
        "is passed.",
    )


def pytest_collection_modifyitems(config, items):
    """Auto-skip every live_browser item unless --run-live was passed."""
    if config.getoption("--run-live"):
        return

    skip_live = pytest.mark.skip(
        reason=(
            "live-browser test: needs a signed-in Chrome on 9222; pass "
            "--run-live to run"
        )
    )
    for item in items:
        if "live_browser" in item.keywords:
            item.add_marker(skip_live)
