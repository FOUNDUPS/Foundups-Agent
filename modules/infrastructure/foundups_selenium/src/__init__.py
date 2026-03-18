"""
FoundUps Selenium - Browser Automation Infrastructure

Provides browser automation capabilities with anti-detection, telemetry, and session management.

Public API:
    - FoundUpsDriver: Enhanced Selenium WebDriver with telemetry
    - BrowserManager: Singleton browser session manager
    - get_browser_manager: Factory function for BrowserManager
    - TelemetryStore: Browser action telemetry storage
    - BrowserAdapter: Unified Selenium/MCP interface
    - get_browser_adapter: Factory function for BrowserAdapter

WSP Compliance:
    - WSP 3: Infrastructure domain placement
    - WSP 11: Public API exports
    - WSP 77: AI Overseer telemetry integration
"""

from .foundups_driver import FoundUpsDriver
from .browser_manager import BrowserManager, get_browser_manager
from .telemetry_store import TelemetryStore
from .foundup_typer import FoundupsTyper, get_typer
from .human_behavior import HumanBehavior, get_human_behavior
from .devtools_mcp_adapter import BrowserAdapter, get_browser_adapter, BrowserResult

__all__ = [
    "FoundUpsDriver",
    "BrowserManager",
    "get_browser_manager",
    "TelemetryStore",
    "FoundupsTyper",
    "get_typer",
    "HumanBehavior",
    "get_human_behavior",
    "BrowserAdapter",
    "get_browser_adapter",
    "BrowserResult",
]

__version__ = "1.1.0"
