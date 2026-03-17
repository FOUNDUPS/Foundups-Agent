#!/usr/bin/env python3
"""
LinkedIn Group Moderation DAE - Executor

EXTENDS existing OpenClawGroupMembershipDAE with:
- CxO detection (APPROVE + CONNECT action)
- 8-point personalized ROI threat message template
- Post moderation (DELETE/COMMENT/KEEP)
- Profile intel extraction

WSP 97 Compliance: Extends existing, does not duplicate.

WSP References:
- WSP 42: LinkedIn platform integration
- WSP 78: Database logging to agents_social_group_actions
- WSP 96: WRE Skills protocol
- WSP 97: System execution prompting (HoloIndex -> Research -> Hard Think)
"""

import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Import existing classes - DO NOT DUPLICATE
try:
    from modules.platform_integration.linkedin_agent.skillz.openclaw_group_news.executor import (
        GroupMemberRequest,
        GroupLanguageDetector,
        WelcomeMessageComposer,
        OpenClawGroupMembershipDAE,
        LINKEDIN_GROUP_ID,
    )
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parents[5]))
    from modules.platform_integration.linkedin_agent.skillz.openclaw_group_news.executor import (
        GroupMemberRequest,
        GroupLanguageDetector,
        WelcomeMessageComposer,
        OpenClawGroupMembershipDAE,
        LINKEDIN_GROUP_ID,
    )

# Constants
LINKEDIN_GROUP_URL = f"https://www.linkedin.com/groups/{LINKEDIN_GROUP_ID}/"
LINKEDIN_GROUP_ADMIN_URL = f"https://www.linkedin.com/groups/{LINKEDIN_GROUP_ID}/manage/membership/requested/"

# CxO/Executive patterns for APPROVE + CONNECT (NEW functionality)
CXO_PATTERNS = [
    r"\bC[EO][OE]\b",  # CEO, COO, CTO, CFO, etc.
    r"\bChief\s+\w+\s+Officer\b",
    r"\bVP\b",
    r"\bVice\s+President\b",
    r"\bFounder\b",
    r"\bCo-?Founder\b",
    r"\bHead\s+of\b",
    r"\bDirector\b",
    r"\bManaging\s+Director\b",
    r"\bPartner\b",
    r"\bPrincipal\b",
    r"\bPresident\b",
    r"\bGeneral\s+Manager\b",
]

# Resources for enhanced message template
RESOURCES = {
    "foundups": "foundups.com",
    "litepaper": "foundups.com/litepaper.html",
    "roc_paper": "linkedin.com/pulse/return-compute-tokenization-framework-foundups-whdce/",
    "github": "github.com/foundups",
}


@dataclass
class TriageDecision:
    """Enhanced triage decision with CxO detection."""
    action: str  # DENY, APPROVE, APPROVE_CONNECT
    send_message: bool
    reason: str
    message: Optional[str] = None


@dataclass
class PostModerationDecision:
    """Post moderation decision (NEW functionality)."""
    action: str  # DELETE, COMMENT, KEEP
    reason: str
    comment_text: Optional[str] = None
    screenshot_taken: bool = False


@dataclass
class ProfileIntel:
    """Profile intelligence extraction (NEW functionality)."""
    name: str
    headline: str
    about: str = ""
    location: str = ""
    company: str = ""
    education: str = ""
    threat_analysis: str = ""
    joining_reason: str = ""
    their_play: str = ""


def is_cxo(headline: str) -> bool:
    """
    Check if headline indicates CxO/executive level.
    NEW functionality - not in existing code.
    """
    for pattern in CXO_PATTERNS:
        if re.search(pattern, headline, re.IGNORECASE):
            return True
    return False


def triage_member(member: GroupMemberRequest) -> TriageDecision:
    """
    Enhanced triage using EXISTING classification + NEW CxO detection.

    Uses: OpenClawGroupMembershipDAE._classify_member_account (existing)
    Adds: CxO detection for APPROVE_CONNECT (new)
    """
    # Step 1: Use EXISTING classification (DO NOT DUPLICATE)
    is_human, reason = OpenClawGroupMembershipDAE._classify_member_account(member)

    if not is_human:
        return TriageDecision(
            action="DENY",
            send_message=False,
            reason=f"Non-human detected: {reason}"
        )

    # Step 2: NEW - CxO detection for APPROVE + CONNECT
    if is_cxo(member.headline):
        message = build_enhanced_welcome_message(member, is_cxo=True)
        return TriageDecision(
            action="APPROVE_CONNECT",
            send_message=True,
            reason=f"CxO/Executive detected: {member.headline}",
            message=message
        )

    # Step 3: Standard APPROVE with message
    message = build_enhanced_welcome_message(member, is_cxo=False)
    return TriageDecision(
        action="APPROVE",
        send_message=True,
        reason="Human verified, standard member",
        message=message
    )


def build_enhanced_welcome_message(member: GroupMemberRequest, is_cxo: bool = False) -> str:
    """
    Build 8-point personalized welcome message.
    ENHANCES existing WelcomeMessageComposer with ROI threat template.

    Structure:
    1. Personal ROI threat
    2. ROC paper
    3. FoundUps case study
    4. Security
    5. Poker table
    6. Spam check
    7. Signature
    8. PS (Apple employees only)
    """
    # Use EXISTING language detection
    lang = GroupLanguageDetector.detect(f"{member.name} {member.headline}")
    name_first = (member.name or "there").split()[0]

    lines = []

    # 1. Personal ROI threat - name their job, state how agents replace that paycheck
    job_threat = _analyze_job_threat(member.headline)
    lines.append(f"Hi {name_first},")
    lines.append("")
    lines.append(job_threat)
    lines.append("")

    # 2. ROC paper - framed as research
    lines.append(f"For context on the economics: {RESOURCES['roc_paper']}")
    lines.append("(Academic framing of how compute replaces labor value)")
    lines.append("")

    # 3. FoundUps case study - framed as learning
    if is_cxo:
        lines.append(f"We're building at {RESOURCES['foundups']} - PWA mesh, agent-driven app store, autonomous solutions.")
    else:
        lines.append(f"Learn more at {RESOURCES['foundups']}")
    lines.append("")

    # 4. Security
    lines.append("Sandbox your OpenClaw agents.")
    lines.append("")

    # 5. Poker table
    lines.append("Group is quiet. Everyone's at the poker table reading each other's hand - nobody wants to sneeze first. Expect watchers, not chatter.")
    lines.append("")

    # 6. Spam check
    lines.append("Here to learn or sell? We delete marketing posts.")
    lines.append("")

    # 7. Signature
    lines.append("- 0102")

    # 8. PS - Apple employees only
    if _is_apple_employee(member):
        lines.append("")
        lines.append("PS: First video ever made about Siri was done by UnDaoDu, 8 months before Siri's acquisition.")

    return "\n".join(lines)


def _analyze_job_threat(headline: str) -> str:
    """Analyze job title and return personalized ROI threat."""
    headline_lower = (headline or "").lower()

    if any(x in headline_lower for x in ["developer", "engineer", "programmer", "coder"]):
        return "Your code job? Agents write code now. Not hypothetically - production code, shipped."

    if any(x in headline_lower for x in ["product", "pm", "manager"]):
        return "Product roles? Agents now translate requirements to working software. The middleman is the first to go."

    if any(x in headline_lower for x in ["marketing", "growth", "brand"]):
        return "Marketing? Agents generate content, run campaigns, optimize spend. Human creativity is being automated."

    if any(x in headline_lower for x in ["sales", "account", "business development"]):
        return "Sales? Agents are now qualifying leads, doing outreach, closing deals. The pipeline is getting shorter."

    if any(x in headline_lower for x in ["design", "ux", "ui"]):
        return "Design? AI generates wireframes, mockups, even coded components. The visual layer is commodity now."

    if any(x in headline_lower for x in ["data", "analyst", "analytics"]):
        return "Data analysis? Agents query, visualize, and derive insights faster than any human team."

    if any(x in headline_lower for x in ["ceo", "founder", "cto", "cfo", "coo", "vp", "director"]):
        return "Even at your level - agents are doing strategic analysis, competitive intel, board decks. Nobody's safe."

    return "Whatever your role - agents are coming for it. The question is when, not if."


def _is_apple_employee(member: GroupMemberRequest) -> bool:
    """Check if member indicates Apple employment."""
    apple_patterns = [r"\bApple\b", r"\b@apple\b", r"\bCupertino\b"]
    text = f"{member.headline}"
    for pattern in apple_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


# ============================================================================
# NEW FUNCTIONALITY - Post Moderation (not in existing code)
# ============================================================================

def moderate_post(post_content: str, author: str) -> PostModerationDecision:
    """
    Decide post moderation action. NEW functionality.

    Decision Tree:
    - Marketing/promo/clickbait -> DELETE (screenshot first)
    - Engagement-farming -> COMMENT (call out)
    - Genuine content -> KEEP
    """
    content_lower = (post_content or "").lower()

    # Marketing/promo patterns
    marketing_patterns = [
        r"dm me for",
        r"link in bio",
        r"check out my",
        r"buy now",
        r"limited time",
        r"sign up free",
        r"\$\d+[k]?\s*(off|discount)",
        r"book a call",
        r"schedule a demo",
        r"join my",
        r"webinar",
        r"masterclass",
    ]

    for pattern in marketing_patterns:
        if re.search(pattern, content_lower):
            return PostModerationDecision(
                action="DELETE",
                reason=f"Marketing/promo detected: {pattern}",
                screenshot_taken=True
            )

    # Engagement farming patterns
    engagement_patterns = [
        r"agree\?",
        r"thoughts\?$",
        r"who else\?",
        r"raise your hand",
        r"drop a \S+ if",
        r"comment below",
        r"repost if",
        r"share if",
    ]

    for pattern in engagement_patterns:
        if re.search(pattern, content_lower):
            return PostModerationDecision(
                action="COMMENT",
                reason=f"Engagement-farming detected: {pattern}",
                comment_text="This reads like engagement farming. If you have a real point, make it. - 0102"
            )

    # Default: KEEP
    return PostModerationDecision(
        action="KEEP",
        reason="Genuine content"
    )


# ============================================================================
# NEW FUNCTIONALITY - Profile Intel (not in existing code)
# ============================================================================

def extract_profile_intel(driver, profile_url: str) -> ProfileIntel:
    """
    Extract profile intelligence from LinkedIn profile page. NEW functionality.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    driver.get(profile_url)
    time.sleep(2)

    intel = ProfileIntel(name="", headline="")

    try:
        name_elem = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1.text-heading-xlarge"))
        )
        intel.name = name_elem.text.strip()
    except Exception:
        pass

    try:
        headline_elem = driver.find_element(By.CSS_SELECTOR, "div.text-body-medium")
        intel.headline = headline_elem.text.strip()
    except Exception:
        pass

    try:
        location_elem = driver.find_element(By.CSS_SELECTOR, "span.text-body-small.inline")
        intel.location = location_elem.text.strip()
    except Exception:
        pass

    try:
        about_section = driver.find_element(
            By.CSS_SELECTOR,
            "section.pv-about-section div.pv-shared-text-with-see-more span"
        )
        intel.about = about_section.text.strip()[:500]
    except Exception:
        pass

    # Analyze
    intel.threat_analysis = _analyze_job_threat(intel.headline)
    intel.joining_reason = _infer_joining_reason(intel)
    intel.their_play = _infer_their_play(intel)

    return intel


def _infer_joining_reason(intel: ProfileIntel) -> str:
    """Infer why they're joining the group."""
    headline_lower = (intel.headline or "").lower()

    if any(x in headline_lower for x in ["ai", "ml", "machine learning", "agent"]):
        return "Technical interest - wants to understand agent frameworks"

    if any(x in headline_lower for x in ["investor", "vc", "capital", "fund"]):
        return "Investment opportunity scouting"

    if any(x in headline_lower for x in ["founder", "ceo", "startup"]):
        return "Competitive intelligence or partnership exploration"

    if any(x in headline_lower for x in ["recruiter", "talent", "hr"]):
        return "Talent scouting in AI/agent space"

    return "General interest in AI agents / OpenClaw"


def _infer_their_play(intel: ProfileIntel) -> str:
    """Infer what their strategic play is."""
    headline_lower = (intel.headline or "").lower()

    if any(x in headline_lower for x in ["sales", "bd", "business development"]):
        return "Likely to pitch services - watch for marketing posts"

    if any(x in headline_lower for x in ["consultant", "advisor", "coach"]):
        return "May try to extract insights for client work"

    if any(x in headline_lower for x in ["journalist", "writer", "reporter"]):
        return "May be researching for article - could be ally or critic"

    return "Unclear - observe posting behavior"


# ============================================================================
# CLI Entry Point
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="LinkedIn Group Moderation DAE")
    parser.add_argument("--test-triage", action="store_true", help="Test triage logic")
    parser.add_argument("--test-message", type=str, help="Test message generation for headline")
    args = parser.parse_args()

    if args.test_triage:
        # Test using EXISTING GroupMemberRequest
        test_members = [
            GroupMemberRequest(name="John Doe", headline="CEO at TechCorp", image_url="https://photo.jpg"),
            GroupMemberRequest(name="Jane Smith", headline="Software Engineer", image_url="https://photo.jpg"),
            GroupMemberRequest(name="Bot Account", headline="Marketing", image_url=""),  # No photo = DENY
        ]

        for member in test_members:
            decision = triage_member(member)
            print(f"\n{member.name} ({member.headline}):")
            print(f"  Action: {decision.action}")
            print(f"  Reason: {decision.reason}")
            print(f"  Send message: {decision.send_message}")

    elif args.test_message:
        member = GroupMemberRequest(name="Test User", headline=args.test_message, image_url="https://photo.jpg")
        decision = triage_member(member)
        print(f"Triage: {decision.action}")
        print(f"\nMessage:\n{decision.message}")
