# -*- coding: utf-8 -*-
import sys
import io
from importlib import import_module

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

#!/usr/bin/env python3
"""
HoloIndex Qwen Advisor - Modular AI Intelligence System

Clean API exports for the refactored HoloDAE architecture.

WSP Compliance: WSP 80 (Cube-Level DAE Orchestration)
"""

__all__ = [
    # Main components
    'HoloDAECoordinator',

    # Legacy functions
    'start_holodae',
    'stop_holodae',
    'get_holodae_status',
    'show_holodae_menu',

    # Models
    'WorkContext',
    'MonitoringResult',
    'HealthViolation',
    'PatternAlert',
    'MonitoringState',

    # Orchestration
    'QwenOrchestrator',

    # Arbitration
    'MPSArbitrator',
    'ArbitrationDecision',
    'MPSAnalysis',
    'PriorityLevel',
    'ActionType',

    # Services
    'FileSystemWatcher',
    'ContextAnalyzer',

    # UI
    'HoloDAEMenuSystem',
    'StatusDisplay'
]

__version__ = "2.0.0"  # Modular architecture version


def __getattr__(name: str):
    """Resolve the existing public API without loading services on leaf import."""
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    # Literal module names keep the governed backend manifest closure explicit.
    if name in {"HoloDAECoordinator", "start_holodae", "stop_holodae",
                "get_holodae_status", "show_holodae_menu"}:
        module = import_module("holo_index.qwen_advisor.holodae_coordinator")
    elif name == "WorkContext":
        module = import_module("holo_index.qwen_advisor.models.work_context")
    elif name in {"MonitoringResult", "HealthViolation", "PatternAlert", "MonitoringState"}:
        module = import_module("holo_index.qwen_advisor.models.monitoring_types")
    elif name == "QwenOrchestrator":
        module = import_module("holo_index.qwen_advisor.orchestration.qwen_orchestrator")
    elif name in {"MPSArbitrator", "ArbitrationDecision", "MPSAnalysis", "PriorityLevel", "ActionType"}:
        module = import_module("holo_index.qwen_advisor.arbitration.mps_arbitrator")
    elif name == "FileSystemWatcher":
        module = import_module("holo_index.qwen_advisor.services.file_system_watcher")
    elif name == "ContextAnalyzer":
        module = import_module("holo_index.qwen_advisor.services.context_analyzer")
    else:
        module = import_module("holo_index.qwen_advisor.ui.menu_system")
    value = getattr(module, name)
    globals()[name] = value
    return value


def __dir__():
    """Keep lazy public names discoverable without importing their owners."""
    return sorted(set(globals()) | set(__all__))
