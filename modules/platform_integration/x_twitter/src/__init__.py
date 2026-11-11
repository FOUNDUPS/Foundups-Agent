"""
X Twitter DAE Communication Node Source Module

First decentralized autonomous entity communication node implementing
WSP 26-29 compliance with entangled authentication, autonomous communication,
and smart DAO evolution capabilities with WRE integration.
"""

from importlib import import_module

__version__ = "1.0.0"
__all__ = [
    'XTwitterDAENode',
    'DAEIdentity',
    'DAEIdentityState', 
    'AuthenticationLevel',
    'CommunicationMode',
    'SocialEngagementToken',
    'AutonomousPost',
    'CABRInteraction',
    'DAEAuthenticator',
    'CABREngine',
    'create_x_twitter_dae_node',
    'test_x_twitter_dae'
]


def __getattr__(name):
    """Keep the verified API leaf independent of the legacy DAE bootstrap."""
    if name in __all__:
        return getattr(import_module(".x_twitter_dae", __name__), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
