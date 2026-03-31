# -*- coding: utf-8 -*-
"""
HoloIndex CLI package.

This package was extracted from the monolithic holo_index/cli.py.
It re-exports all public symbols for backward compatibility.

Consumers:
  - holo_index.py (root entrypoint): from holo_index.cli import main
  - tests/test_cli.py: from holo_index.cli import HoloIndex, QwenAdvisor, main
  - tests/test_fast_search_mode.py: from holo_index.cli import _is_fast_search_enabled, _render_fast_search_summary
  - wre_master_orchestrator holoindex_plugin: from holo_index.cli import HoloIndex
"""

# Re-export main entrypoint and public symbols from the core CLI module.
from holo_index._cli_main import main  # noqa: F401

# Re-export classes that consumers import from holo_index.cli
# HoloIndex is always available (from holo_index.core.holo_index)
from holo_index._cli_main import HoloIndex  # noqa: F401

# QwenAdvisor may be None when advisor dependencies are unavailable.
# Import the module-level name (which may be None) for backward compat.
try:
    from holo_index._cli_main import QwenAdvisor  # noqa: F401
except ImportError:
    QwenAdvisor = None  # type: ignore

# Re-export internal functions used by tests
from holo_index._cli_main import _is_fast_search_enabled  # noqa: F401
from holo_index._cli_main import _render_fast_search_summary  # noqa: F401
