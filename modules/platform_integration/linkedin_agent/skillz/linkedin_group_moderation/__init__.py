"""
LinkedIn Group Moderation DAE - EXTENDS existing OpenClawGroupMembershipDAE.

WSP 97 Compliant: Uses existing code, adds new functionality.

Existing (reused):
- GroupMemberRequest from openclaw_group_news
- GroupLanguageDetector from openclaw_group_news
- OpenClawGroupMembershipDAE._classify_member_account from openclaw_group_news

New functionality:
- is_cxo() - CxO detection for APPROVE_CONNECT
- build_enhanced_welcome_message() - 8-point ROI threat template
- moderate_post() - DELETE/COMMENT/KEEP decisions
- extract_profile_intel() - Profile intelligence extraction
"""

from .executor import (
    # Dataclasses
    TriageDecision,
    PostModerationDecision,
    ProfileIntel,
    # Functions
    is_cxo,
    triage_member,
    build_enhanced_welcome_message,
    moderate_post,
    extract_profile_intel,
    # Re-exported from existing (for convenience)
    LINKEDIN_GROUP_URL,
    LINKEDIN_GROUP_ADMIN_URL,
)

# Re-export existing classes for convenience
from modules.platform_integration.linkedin_agent.skillz.openclaw_group_news.executor import (
    GroupMemberRequest,
    GroupLanguageDetector,
    WelcomeMessageComposer,
    OpenClawGroupMembershipDAE,
)

__all__ = [
    # New dataclasses
    "TriageDecision",
    "PostModerationDecision",
    "ProfileIntel",
    # New functions
    "is_cxo",
    "triage_member",
    "build_enhanced_welcome_message",
    "moderate_post",
    "extract_profile_intel",
    # Constants
    "LINKEDIN_GROUP_URL",
    "LINKEDIN_GROUP_ADMIN_URL",
    # Re-exported existing
    "GroupMemberRequest",
    "GroupLanguageDetector",
    "WelcomeMessageComposer",
    "OpenClawGroupMembershipDAE",
]
