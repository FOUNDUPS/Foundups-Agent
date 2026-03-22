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

# Import Qwen3 profile evaluator for AI-powered decisions
try:
    from modules.platform_integration.linkedin_agent.src.qwen_profile_evaluator import (
        evaluate_profile_with_qwen,
        ProfileDecision,
        ProfileEvaluation,
    )
    QWEN_AVAILABLE = True
except ImportError:
    QWEN_AVAILABLE = False
    logger.warning("[QWEN3] Profile evaluator not available - using fallback")

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
    AI-powered triage using Qwen3 profile evaluation.

    Replaces hardcoded regex patterns with intelligent evaluation.
    Falls back to simple rules if Qwen unavailable.
    """
    # Determine if profile has image
    has_image = bool(member.image_url and member.image_url.strip())

    # Use Qwen3 for intelligent evaluation
    if QWEN_AVAILABLE:
        try:
            evaluation = evaluate_profile_with_qwen(
                name=member.name or "",
                headline=member.headline or "",
                has_image=has_image,
                profile_url=None  # Could add if available
            )

            logger.info(f"[QWEN3] Profile evaluation: {evaluation.decision.value} "
                       f"(confidence: {evaluation.confidence:.2f})")

            # Map ProfileDecision to TriageDecision
            if evaluation.decision == ProfileDecision.APPROVE_CONNECT:
                message = build_enhanced_welcome_message(member, is_cxo=True)
                return TriageDecision(
                    action="APPROVE_CONNECT",
                    send_message=True,
                    reason=f"[QWEN3] {evaluation.reasoning}",
                    message=message
                )

            elif evaluation.decision == ProfileDecision.APPROVE:
                message = build_enhanced_welcome_message(member, is_cxo=False)
                return TriageDecision(
                    action="APPROVE",
                    send_message=True,
                    reason=f"[QWEN3] {evaluation.reasoning}",
                    message=message
                )

            elif evaluation.decision == ProfileDecision.DENY_INCOMPLETE:
                # Message requesting profile completion, then deny
                return TriageDecision(
                    action="DENY_MESSAGE",  # Message first, then deny
                    send_message=True,
                    reason=f"[QWEN3] {evaluation.reasoning}",
                    message="Please complete your profile (add a photo) and reapply. --0102"
                )

            elif evaluation.decision == ProfileDecision.DENY:
                return TriageDecision(
                    action="DENY",
                    send_message=False,
                    reason=f"[QWEN3] {evaluation.reasoning}"
                )

            else:  # NEEDS_REVIEW
                return TriageDecision(
                    action="SKIP",
                    send_message=False,
                    reason=f"[QWEN3] Needs human review: {evaluation.reasoning}"
                )

        except Exception as e:
            logger.error(f"[QWEN3] Evaluation failed: {e}, falling back to rules")

    # Fallback: Use existing classification if Qwen unavailable
    is_human, reason = OpenClawGroupMembershipDAE._classify_member_account(member)

    if not is_human:
        return TriageDecision(
            action="DENY",
            send_message=False,
            reason=f"Non-human detected: {reason}"
        )

    # Fallback CxO detection
    if is_cxo(member.headline):
        message = build_enhanced_welcome_message(member, is_cxo=True)
        return TriageDecision(
            action="APPROVE_CONNECT",
            send_message=True,
            reason=f"CxO/Executive detected: {member.headline}",
            message=message
        )

    # Standard APPROVE
    message = build_enhanced_welcome_message(member, is_cxo=False)
    return TriageDecision(
        action="APPROVE",
        send_message=True,
        reason="Human verified, standard member",
        message=message
    )


def build_enhanced_welcome_message(member: GroupMemberRequest, is_cxo: bool = False) -> str:
    """
    Build agentic welcome message. No template regurgitation.
    """
    name_first = (member.name or "there").split()[0]
    headline = (member.headline or "").strip()
    role_info = _analyze_role_deeply(headline)

    lines = []

    # Direct opener - no title echo
    lines.append(f"Welcome {name_first}.")
    lines.append("")

    # Agentic disruption - direct, no fluff
    lines.append(f"{role_info['disruption']}")
    lines.append("")

    # Security context - brief
    lines.append(f"Sandbox your agents. {role_info['security_context']}")
    lines.append("")

    # FoundUps pitch - entities as code
    lines.append(f"We're building entities that exist as code. No employees. Only stakeholders. ROC > ROI.")
    lines.append(f"foundups.com | litepaper: foundups.com/litepaper.html")
    lines.append("")

    # ROI question - direct
    lines.append("When agents do your job, what's your plan?")
    lines.append("")

    lines.append("--0102")

    return "\n".join(lines)


def _analyze_role_deeply(headline: str) -> dict:
    """
    Deep analysis of headline to extract role-specific messaging.
    Returns dict with: domain, disruption, security_context, role_label, question

    PRIORITY ORDER matters - more specific roles checked first.
    """
    headline_lower = (headline or "").lower()

    # Investor/VC/Finance - check FIRST (before "partner" catches VC partners)
    if any(x in headline_lower for x in ["investor", "vc ", "venture", "capital", "fund", "private equity", "pe ", "sequoia", "a16z", "andreessen"]):
        return {
            "domain": "investing",
            "disruption": "Agents scan deal flow, analyze financials, assess market fit, and even draft term sheets. The investment thesis is becoming algorithmic",
            "security_context": "Especially relevant if agents access deal flow, portfolio data, or LP communications.",
            "role_label": "investor",
            "question": "When agents can evaluate 1000 startups a day, what's the human investor's edge? Pattern recognition? That's exactly what agents excel at."
        }

    # Channel/Partner Sales (after investor check)
    if any(x in headline_lower for x in ["channel", "partner sales", "alliance", "reseller"]):
        return {
            "domain": "channel",
            "disruption": "The channel sales model gets fundamentally rewritten when OpenClaw agents handle partner discovery, deal qualification, even relationship nurture autonomously",
            "security_context": "Especially relevant if agents touch CRM or partner data.",
            "role_label": "channel leader",
            "question": "Is ROI dead if compute replaces sales labor? What happens to partner margins when agents do the work?"
        }

    # Sales/Revenue
    if any(x in headline_lower for x in ["sales", "revenue", "account executive", "business development", "bd "]):
        return {
            "domain": "sales",
            "disruption": "The sales function gets rewritten when agents qualify leads, craft personalized outreach, and nurture deals autonomously. Pipeline velocity without headcount",
            "security_context": "Especially relevant if agents touch CRM, deal data, or customer communications.",
            "role_label": "revenue leader",
            "question": "Is the SDR role sustainable when agents do prospecting at 100x the volume? What happens to commission structures?"
        }

    # Engineering/Development
    if any(x in headline_lower for x in ["engineer", "developer", "programmer", "software", "architect", "devops", "sre"]):
        return {
            "domain": "engineering",
            "disruption": "Agents write production code now. Not prototypes — shipped features, reviewed PRs, deployed infrastructure. The 10x engineer is now 100x with agent assistance",
            "security_context": "Especially relevant if agents touch source code, CI/CD, or production systems.",
            "role_label": "builder",
            "question": "Does the senior/junior distinction matter when agents can bootstrap either? What's the moat when everyone has the same tooling?"
        }

    # Product Management
    if any(x in headline_lower for x in ["product", "pm ", "product manager", "product owner"]):
        return {
            "domain": "product",
            "disruption": "Agents translate requirements to working software directly. The middleman who translates business to tech is the first optimization target",
            "security_context": "Especially relevant if agents access roadmaps, customer feedback, or competitive intel.",
            "role_label": "product leader",
            "question": "When agents can spec, design, and build — what's the PM's unique value? Taste? Politics? Neither scales."
        }

    # Marketing/Growth
    if any(x in headline_lower for x in ["marketing", "growth", "brand", "content", "demand gen", "cmo"]):
        return {
            "domain": "marketing",
            "disruption": "Agents generate content, run campaigns, optimize spend, and analyze attribution autonomously. Creative at scale without creative headcount",
            "security_context": "Especially relevant if agents touch brand assets, ad accounts, or customer data.",
            "role_label": "growth leader",
            "question": "When agents can A/B test 1000 variants overnight, what's the human marketer's edge? Intuition doesn't scale."
        }

    # Data/Analytics
    if any(x in headline_lower for x in ["data", "analyst", "analytics", "bi ", "business intelligence", "insights"]):
        return {
            "domain": "analytics",
            "disruption": "Agents query databases, build dashboards, derive insights, and present findings faster than any human analyst team",
            "security_context": "Especially relevant if agents access data warehouses or customer analytics.",
            "role_label": "data leader",
            "question": "When agents can answer any business question in seconds, what's left for the analyst? The questions themselves?"
        }

    # Design/UX
    if any(x in headline_lower for x in ["design", "ux", "ui", "creative", "visual"]):
        return {
            "domain": "design",
            "disruption": "AI generates wireframes, mockups, coded components, even full design systems. The visual layer is commodity infrastructure now",
            "security_context": "Especially relevant if agents access design systems or brand guidelines.",
            "role_label": "design leader",
            "question": "When agents can generate a thousand variations in minutes, is human taste the last moat? Or just another training signal?"
        }

    # Executive/C-Suite
    if any(x in headline_lower for x in ["ceo", "cto", "cfo", "coo", "cmo", "cio", "chief", "president", "founder", "co-founder"]):
        return {
            "domain": "the C-suite",
            "disruption": "Agents are doing strategic analysis, competitive intel, board decks, and even stakeholder communication. The executive function is not exempt",
            "security_context": "Especially relevant if agents access financials, strategy docs, or board materials.",
            "role_label": "executive",
            "question": "If agents can synthesize market data and recommend strategy, what's the executive's edge? Relationships? Those are being automated too."
        }

    # VP/Director level
    if any(x in headline_lower for x in ["vp ", "vice president", "director", "head of", "senior director"]):
        return {
            "domain": "leadership",
            "disruption": "Middle management is the coordination layer — and coordination is what agents do best. Status reporting, resource allocation, cross-functional alignment",
            "security_context": "Especially relevant if agents access team data, performance metrics, or strategic plans.",
            "role_label": "leader",
            "question": "When agents can coordinate across teams better than humans, what justifies the management layer? Accountability? Empathy?"
        }

    # HR/People/Talent
    if any(x in headline_lower for x in ["hr ", "human resources", "people", "talent", "recruiting", "recruiter"]):
        return {
            "domain": "HR",
            "disruption": "Agents source candidates, screen resumes, schedule interviews, and even conduct initial assessments. The recruiting funnel is being automated end-to-end",
            "security_context": "Especially relevant if agents access employee data, compensation, or performance reviews.",
            "role_label": "people leader",
            "question": "When agents can match talent to roles better than recruiters, what's left? Culture? That's also being measured by agents now."
        }

    # Consulting/Advisory
    if any(x in headline_lower for x in ["consult", "advisor", "partner at", "principal"]):
        return {
            "domain": "consulting",
            "disruption": "Agents can analyze, synthesize, and recommend at scale. The $500/hour insight is competing with $0.01/token alternatives",
            "security_context": "Especially relevant if agents access client data or strategic recommendations.",
            "role_label": "advisor",
            "question": "When clients can get instant analysis from agents, what's the consulting premium? Relationships? Those are trust, and trust follows results."
        }

    # Legal
    if any(x in headline_lower for x in ["legal", "lawyer", "attorney", "counsel", "law "]):
        return {
            "domain": "legal",
            "disruption": "Agents draft contracts, review documents, research precedents, and assess risk. The billable hour model faces existential pressure",
            "security_context": "Especially relevant if agents access privileged communications or contract data.",
            "role_label": "legal professional",
            "question": "When agents can review contracts in seconds instead of hours, what justifies the billable hour? Judgment? That's being trained too."
        }

    # Operations
    if any(x in headline_lower for x in ["operations", "ops ", "supply chain", "logistics", "procurement"]):
        return {
            "domain": "operations",
            "disruption": "Agents optimize supply chains, manage procurement, monitor logistics, and coordinate vendors autonomously. Ops excellence is becoming automated",
            "security_context": "Especially relevant if agents access vendor contracts, inventory, or supply chain data.",
            "role_label": "ops leader",
            "question": "When agents can optimize operations 24/7 without fatigue, what's the human ops leader's value? Crisis management? Agents don't panic."
        }

    # Default fallback
    return {
        "domain": "your function",
        "disruption": "Agents are automating knowledge work across every domain. Whatever you do, there's likely an agent version being built right now",
        "security_context": "Sandbox everything.",
        "role_label": "professional",
        "question": "What's your unique value when agents can do the repeatable parts of your job? The answer determines your future."
    }


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
