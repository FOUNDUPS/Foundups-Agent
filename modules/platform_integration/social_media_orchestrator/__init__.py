"""
Social Media Orchestrator Module
WSP 49 compliant module for unified social media management

Domain: platform_integration
Classification: Social Media Orchestration
WSP Compliance: WSP 3, WSP 11, WSP 22, WSP 49
"""

from importlib import import_module

__all__ = [
    'SocialMediaOrchestrator',
    'SimplePostingOrchestrator',
    'Platform',
    'SocialMediaEventRouter',
    'UnifiedPostingInterface'
]

__version__ = "1.0.0"
__author__ = "WSP Framework"
__description__ = "Unified social media orchestration for X/Twitter and LinkedIn platforms"


def __getattr__(name):
    """Preserve optional public exports while loading only a requested owner."""
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    try:
        if name == "SocialMediaOrchestrator":
            module = import_module(".src.social_media_orchestrator", __name__)
        elif name in {"SimplePostingOrchestrator", "Platform"}:
            module = import_module(".src.simple_posting_orchestrator", __name__)
        elif name == "SocialMediaEventRouter":
            module = import_module(".src.multi_account_manager", __name__)
        else:
            module = import_module(".src.unified_posting_interface", __name__)
        return getattr(module, name)
    except ImportError:
        return None
