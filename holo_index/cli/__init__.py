# -*- coding: utf-8 -*-
"""
HoloIndex CLI package.

This package was extracted from the monolithic holo_index/cli.py.
It re-exports public symbols for backward compatibility without importing the
semantic backend when a bounded command module is imported directly.

Consumers:
  - holo_index.py (root entrypoint): from holo_index.cli import main
  - tests/test_cli.py: from holo_index.cli import HoloIndex, QwenAdvisor, main
  - tests/test_fast_search_mode.py: from holo_index.cli import _is_fast_search_enabled, _render_fast_search_summary
  - wre_master_orchestrator holoindex_plugin: from holo_index.cli import HoloIndex
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "HoloIndex",
    "QwenAdvisor",
    "_is_fast_search_enabled",
    "_render_fast_search_summary",
    "main",
]

_LAZY_EXPORTS = frozenset(__all__) - {"main"}


def main(*args: Any, **kwargs: Any) -> Any:
    """Run the full CLI, loading semantic dependencies only on invocation."""
    from holo_index._cli_main import main as _main

    return _main(*args, **kwargs)


def __getattr__(name: str) -> Any:
    """Resolve legacy semantic exports without taxing command-only imports."""
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from holo_index import _cli_main

    value = getattr(_cli_main, name)
    globals()[name] = value
    return value
