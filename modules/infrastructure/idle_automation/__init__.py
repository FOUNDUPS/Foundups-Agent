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

Idle Automation Module
WSP 3: Infrastructure Domain - System Automation
Provides autonomous background task execution during idle periods.
"""

from .src.idle_automation_dae import IdleAutomationDAE, run_idle_automation
from .src.self_research_refresh import SelfResearchRefresher

__all__ = [
    'IdleAutomationDAE',
    'run_idle_automation',
    'SelfResearchRefresher',
]

__version__ = "1.0.0"
__wsp_compliance__ = "WSP 3, 27, 35, 48, 60, 70"
