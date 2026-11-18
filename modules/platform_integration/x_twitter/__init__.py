"""
X Twitter DAE Communication Node

First decentralized autonomous entity communication node for Foundups ecosystem.
Implements WSP 26-29 compliance with entangled authentication, autonomous communication,
and smart DAO evolution capabilities with WRE integration.

This module operates as the autonomous social communication extension following
complete DAE architecture protocols per WSP Enterprise Domain Architecture.
"""

from importlib import import_module

__version__ = "1.0.0"
__author__ = "0102 pArtifact"
__domain__ = "platform_integration"
__status__ = "dae_operational_framework"

# WSP Compliance
__wsp_compliant__ = True
__wsp_protocols__ = ["WSP_26", "WSP_27", "WSP_28", "WSP_29", "WSP_3", "WSP_42"]

# DAE Classification
__dae_identity__ = "foundups_primary_social_node"
__dae_type__ = "first_autonomous_communication_dae"
__communication_mode__ = "zero_human_authorship_operational"

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
    """Load legacy DAE exports only when explicitly requested."""
    if name in __all__:
        return getattr(import_module(".src", __name__), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
