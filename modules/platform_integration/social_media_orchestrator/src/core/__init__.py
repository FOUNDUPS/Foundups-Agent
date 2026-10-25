"""
Core components for social media orchestration
Modular, single-responsibility services extracted from simple_posting_orchestrator.py
"""

from importlib import import_module

__all__ = [
    'DuplicatePreventionManager',
    'LiveStatusVerifier',
    'ChannelConfigurationManager',
    'LinkedInPage',
    'XAccount',
    'PlatformPostingService',
    'PostingResult',
    'PostingStatus',
    'BrowserManager',
    'get_browser_manager'
]

# Module version
__version__ = '1.1.0'


def __getattr__(name):
    """Keep receipt-only imports independent of browser/session initialization."""
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    if name == "DuplicatePreventionManager":
        module = import_module(".duplicate_prevention_manager", __name__)
    elif name == "LiveStatusVerifier":
        module = import_module(".live_status_verifier", __name__)
    elif name in {"ChannelConfigurationManager", "LinkedInPage", "XAccount"}:
        module = import_module(".channel_configuration_manager", __name__)
    elif name in {"PlatformPostingService", "PostingResult", "PostingStatus"}:
        module = import_module(".platform_posting_service", __name__)
    else:
        module = import_module("modules.infrastructure.foundups_selenium.src.browser_manager")
    return getattr(module, name)
