"""
Social Media Orchestrator - Unified social media management system
WSP Compliance: WSP 3, WSP 11, WSP 22, WSP 49, WSP 42
"""

from importlib import import_module

__all__ = [
    # Main orchestrator
    'SocialMediaOrchestrator',
    'create_social_media_orchestrator',
    
    # Exceptions
    'OrchestrationError',
    'AuthenticationError', 
    'ContentError',
    'SchedulingError',
    
    # Data classes
    'PostResult',
    'ScheduledPost',
    
    # Core components
    'OAuthCoordinator',
    'ContentOrchestrator',
    'SchedulingEngine',
    
    # Platform adapters
    'BasePlatformAdapter',
    'TwitterAdapter',
    'LinkedInAdapter'
]

# Module metadata
__version__ = '1.0.0'
__description__ = 'Unified social media orchestration system for FoundUps'
__author__ = 'FoundUps Development Team'


def __getattr__(name):
    """Resolve public symbols without bootstrapping siblings on a leaf import."""
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    if name in {"SocialMediaOrchestrator", "OrchestrationError", "AuthenticationError",
                "ContentError", "SchedulingError", "PostResult", "create_social_media_orchestrator"}:
        module = import_module(".social_media_orchestrator", __name__)
    elif name == "OAuthCoordinator":
        module = import_module(".oauth", __name__)
    elif name == "ContentOrchestrator":
        module = import_module(".content", __name__)
    elif name in {"SchedulingEngine", "ScheduledPost"}:
        module = import_module(".scheduling", __name__)
    else:
        module = import_module(".platform_adapters", __name__)
    return getattr(module, name)
