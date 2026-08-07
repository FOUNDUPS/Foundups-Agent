# -*- coding: utf-8 -*-
from typing import Any


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

Idle Automation Module
WSP 3: Infrastructure Domain - System Automation
Provides autonomous background task execution during idle periods.
"""

__all__ = [
    'IdleAutomationDAE',
    'run_idle_automation',
    'SelfResearchRefresher',
]


def __getattr__(name: str) -> Any:
    """Load public runtime exports without burdening contract imports."""
    if name in {"IdleAutomationDAE", "run_idle_automation"}:
        from .src import idle_automation_dae

        return getattr(idle_automation_dae, name)
    if name == "SelfResearchRefresher":
        from .src.self_research_refresh import SelfResearchRefresher

        return SelfResearchRefresher
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__version__ = "1.0.0"
__wsp_compliance__ = "WSP 3, 27, 35, 48, 60, 70"
