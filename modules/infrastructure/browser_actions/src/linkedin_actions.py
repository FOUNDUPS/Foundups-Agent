"""
LinkedIn Actions - Vision-Based Engagement for 0102 Autonomy

All engagement actions use UI-TARS Vision for:
- Reading and understanding posts
- Intelligent reply decisions
- Contextual engagement
- Dynamic UI handling

Selenium only for: navigation, login (known forms)

WSP Compliance:
    - WSP 3: Infrastructure domain
    - WSP 77: AI Overseer integration
    - WSP 80: DAE coordination
"""

import asyncio
import logging
import os
import re
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .action_router import ActionRouter, DriverType, RoutingResult

logger = logging.getLogger(__name__)


@dataclass
class LinkedInPost:
    """Represents a LinkedIn post extracted via vision."""
    post_id: str
    author: str
    content: str
    timestamp: str
    likes: int = 0
    comments: int = 0
    is_relevant: bool = False
    suggested_reply: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "post_id": self.post_id,
            "author": self.author,
            "content": self.content,
            "timestamp": self.timestamp,
            "likes": self.likes,
            "comments": self.comments,
            "is_relevant": self.is_relevant,
            "suggested_reply": self.suggested_reply,
        }


@dataclass
class LinkedInActionResult:
    """Result of a LinkedIn action."""
    success: bool
    action: str
    post_id: Optional[str] = None
    posts_read: int = 0
    engagements: int = 0
    error: Optional[str] = None
    duration_ms: int = 0
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "action": self.action,
            "post_id": self.post_id,
            "posts_read": self.posts_read,
            "engagements": self.engagements,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "details": self.details,
        }


def _connection_policy_result(
    profile_slug: str, metadata: Dict[str, str], policy: Any, start_time: datetime,
    *, dry_run: bool = False, request_status: Optional[str] = None,
) -> LinkedInActionResult:
    """Project policy-only previews and the existing live rejection schema."""
    allowed_preview = dry_run and policy.allowed
    return LinkedInActionResult(
        success=allowed_preview,
        action="send_connection_request",
        post_id=profile_slug,
        error=None if allowed_preview else f"policy_blocked: {policy.reason}",
        duration_ms=int((datetime.now() - start_time).total_seconds() * 1000),
        details={
            "policy_reason": policy.reason,
            "matched_allow": policy.matched_allow,
            "matched_deny": policy.matched_deny,
            "profile": metadata,
            **({"dry_run": True} if dry_run else {"request_status": request_status}),
        },
    )


async def _connection_invitation_clicks(router: ActionRouter, message: Optional[str]) -> tuple:
    """Attempt explicit Send only after any requested note was entered."""
    async def click(description: str, **payload) -> RoutingResult:
        return await router.execute(
            'click_by_description', {'description': description, **payload},
            driver=DriverType.VISION,
        )

    add_note_result = None
    type_result = None
    if message:
        add_note_result = await click('Add a note button in Connect dialog')
        if not add_note_result.success:
            return None, add_note_result, type_result
        type_result = await click(
            'Invitation note text input field', text=message, slow_type=True,
        )
        if not type_result.success:
            return None, add_note_result, type_result
    send_result = await click('Send invitation button in Connect dialog')
    return send_result, add_note_result, type_result


class LinkedInActions:
    """
    LinkedIn vision-based engagement actions.
    
    Uses UI-TARS Vision for ALL engagement (reading, understanding, replying).
    Selenium only for navigation and login.
    
    Usage:
        linkedin = LinkedInActions(profile='linkedin_foundups')
        
        # Read and understand feed
        posts = await linkedin.read_feed(max_posts=10)
        
        # Engage with relevant posts
        for post in posts:
            if post.is_relevant:
                await linkedin.reply_to_post(post.post_id, post.suggested_reply)
        
        # Autonomous engagement session
        result = await linkedin.run_engagement_session(duration_minutes=15)
    """

    # Engagement keywords for 012's interests
    RELEVANCE_KEYWORDS = [
        'startup', 'founder', 'entrepreneur', 'ai', 'autonomous',
        'japan', 'move2japan', 'geozai', 'foundups', 'coding',
        'developer', 'software', 'innovation', 'blockchain', 'web3',
    ]
    AI_TOPIC_KEYWORDS = [
        'ai', 'artificial intelligence', 'machine learning', 'llm',
        'gpt', 'chatgpt', 'claude', 'gemini', 'copilot', 'openai',
        'anthropic', 'autonomous', 'agent', 'automation', 'neural',
        'deep learning', 'transformer', 'singularity', 'agi',
        'superintelligence', 'openclaw', 'ironclaw', 'robot', 'robotics',
        'embodied', 'fleet', 'holo index',
    ]
    CAPITAL_KEYWORDS = [
        'series a', 'series b', 'series c', 'raised', 'funding round',
        'venture capital', 'vc funding', 'seed round', 'pre-seed',
        '$5m', '$10m', '$50m', '$100m', 'million in funding',
        'investor', 'pitch deck', 'fundraise', 'valuation',
        'accelerator', 'incubator', 'term sheet', 'cap table',
        'equity round', 'dilution', 'exit strategy',
    ]
    TARGET_AUTHORS = [
        'salim ismail', 'peter diamandis', 'ray kurzweil',
        'pieter franken', 'mayoran rajendra', 'japan pivot',
    ]
    GENERIC_DRAFT_PATTERNS = [
        "thanks for the question",
        "great question",
        "thanks for sharing",
        "great insights",
        "valuable perspective",
        "important topic",
        "happy to share more details",
    ]
    SCAM_SIGNAL_PATTERNS = {
        "third_party_setup_offer": [
            "set up this ai assistant",
            "set it up for them",
            "do it for them",
            "walk them through everything",
            "get it fully working",
            "setup process",
            "technical side",
            "custom agents",
            "business automations",
            "sort out their setup",
        ],
        "social_proof_push": [
            "every single person has been happy",
            "done about",
            "in the last week",
            "proud dad moment",
            "he's your guy",
            "genuinely impressed",
        ],
        "external_link": [
            "lnkd.in/",
            "bit.ly/",
            "tinyurl.com/",
            "shorturl.at/",
            "t.co/",
            "http://",
            "https://",
        ],
        "off_platform_contact": [
            "his site is",
            "book a call",
            "dm him",
            "send him a message",
            "reach out directly",
        ],
        "brand_impersonation_risk": [
            "openclaw",
            "ironclaw",
            "official setup",
            "approved setup",
        ],
    }

    def __init__(
        self,
        profile: str = 'linkedin_foundups',
        router: ActionRouter = None,
        ai_provider: str = 'grok',
        browser_port: int = 9222,  # Default to Chrome (9222) - Edge is 9223
        dom_action_observer: Optional[Any] = None,  # Callback for DOM-level action logging
    ) -> None:
        """
        Initialize LinkedIn actions.

        Args:
            profile: Browser profile (logged into LinkedIn account)
            router: Pre-configured ActionRouter (optional)
            ai_provider: AI provider for response generation
            browser_port: Debug port (9223=Edge default, 9222=Chrome)
            dom_action_observer: Optional callback(action_type, details) for DOM logging
        """
        self.profile = profile
        self.browser_port = browser_port
        self._dom_observer = dom_action_observer

        # Set env vars so ActionRouter uses the correct browser/port
        # NOTE: ActionRouter reads FOUNDUPS_CHROME_PORT for port regardless of browser type
        import os
        os.environ["FOUNDUPS_CHROME_PORT"] = str(browser_port)  # Primary port env var
        os.environ["BROWSER_DEBUG_PORT"] = str(browser_port)    # Fallback port env var
        if browser_port == 9223:
            os.environ["BROWSER_TYPE"] = "edge"
            os.environ["FOUNDUPS_EDGE_PORT"] = str(browser_port)
        else:
            os.environ["BROWSER_TYPE"] = "chrome"

        # Create router with DOM action observer if provided
        router_observers = []
        if dom_action_observer:
            router_observers.append(self._make_router_observer())
        self.router = router or ActionRouter(profile=profile, observers=router_observers)
        self.ai_provider = ai_provider

        # Connection policy gate (role-based allow/deny)
        self._connection_manager = None
        self._connection_profile_cls = None
        self._connection_status_cls = None
        try:
            from modules.platform_integration.linkedin_agent.src.engagement.connection_manager import (
                LinkedInConnectionManager as PolicyConnectionManager,
                LinkedInProfile as PolicyLinkedInProfile,
                ConnectionStatus as PolicyConnectionStatus,
            )
            self._connection_manager = PolicyConnectionManager()
            self._connection_profile_cls = PolicyLinkedInProfile
            self._connection_status_cls = PolicyConnectionStatus
            logger.info("[LINKEDIN] Connection policy gate loaded")
        except Exception as e:
            logger.warning(f"[LINKEDIN] Connection policy gate unavailable: {e}")
        
        # Try to import LLM for intelligent responses
        try:
            from modules.communication.video_comments.src.llm_comment_generator import LLMCommentGenerator
            self.llm = LLMCommentGenerator(provider=ai_provider)
            self._llm_available = True
            logger.info(f"[LINKEDIN] LLM available via {ai_provider}")
        except ImportError:
            self.llm = None
            self._llm_available = False
            logger.warning("[LINKEDIN] LLM not available, will use templates")
        
        # Session stats
        self._session_stats = {
            'posts_read': 0,
            'posts_engaged': 0,
            'likes_given': 0,
            'comments_made': 0,
            'connections_sent': 0,
        }

        # Feed iterator state
        self._feed_iterator_index = 0
        self._feed_posts_cache: List[Dict[str, Any]] = []
        self._last_refresh_time: Optional[datetime] = None
        self._linkedin_comment_drafter = None
        self._linkedin_drafter_attempted = False

        logger.info(f"[LINKEDIN] Actions initialized with profile={profile}")

    def _make_router_observer(self):
        """Create router observer that forwards events to DOM action logger."""
        def observer(event: str, payload: Dict[str, Any]) -> None:
            if self._dom_observer:
                # Map router events to DOM-level action logs
                dom_event = {
                    "event": event,
                    "driver": payload.get("driver_used", payload.get("driver")),
                    "action": payload.get("action"),
                    "success": payload.get("success"),
                    "duration_ms": payload.get("duration_ms"),
                    "confidence": payload.get("result_data", {}).get("confidence"),
                    "error": payload.get("error"),
                }
                try:
                    self._dom_observer("dom_action", dom_event)
                except Exception as e:
                    logger.debug(f"[LINKEDIN] DOM observer error: {e}")
        return observer

    def _log_dom_action(self, action_type: str, details: Dict[str, Any]) -> None:
        """Log a DOM-level action to the observer if available."""
        if self._dom_observer:
            try:
                self._dom_observer(action_type, details)
            except Exception as e:
                logger.debug(f"[LINKEDIN] DOM log error: {e}")

    def _ensure_linkedin_comment_drafter(self) -> bool:
        """Lazy init of the digital-twin LinkedIn drafter."""
        if self._linkedin_drafter_attempted:
            return self._linkedin_comment_drafter is not None

        self._linkedin_drafter_attempted = True
        try:
            from modules.ai_intelligence.digital_twin.src.comment_drafter import (
                CommentDrafter,
                LocalLLM,
            )
            from modules.ai_intelligence.digital_twin.src.style_guardrails import StyleGuardrails
            from modules.ai_intelligence.digital_twin.src.voice_memory import VoiceMemory

            self._linkedin_comment_drafter = CommentDrafter(
                voice_memory=VoiceMemory(include_videos=True),
                guardrails=StyleGuardrails(),
                llm=LocalLLM(mock_mode=False),
                use_real_llm=True,
            )
            logger.info("[LINKEDIN] Digital twin comment drafter initialized")
        except Exception as exc:
            self._linkedin_comment_drafter = None
            logger.warning(f"[LINKEDIN] Digital twin comment drafter unavailable: {exc}")

        return self._linkedin_comment_drafter is not None

    def _infer_engagement_reason(self, content: str, author: str) -> str:
        """Infer engagement bucket from post content when DOM metadata is absent."""
        content_lower = str(content or "").lower()
        author_lower = str(author or "").lower()

        if any(keyword in content_lower for keyword in self.CAPITAL_KEYWORDS):
            return "capital_pushback"
        if any(name in author_lower for name in self.TARGET_AUTHORS):
            return "target_author"
        if any(keyword in content_lower for keyword in self.AI_TOPIC_KEYWORDS):
            return "ai_topic"
        return "general"

    @staticmethod
    def _truncate_reply(text: str, max_chars: int = 300) -> str:
        """Trim generated LinkedIn replies to a safe comment length."""
        candidate = " ".join((text or "").strip().split())
        if len(candidate) <= max_chars:
            return candidate
        shortened = candidate[:max_chars].rsplit(" ", 1)[0].rstrip(" ,;:")
        return shortened + "..."

    def _looks_generic_draft(self, text: str) -> bool:
        """Reject low-value drafts that add no concrete insight."""
        lowered = str(text or "").strip().lower()
        if not lowered:
            return True
        if any(pattern in lowered for pattern in self.GENERIC_DRAFT_PATTERNS):
            return True
        return len(lowered.split()) < 7

    def _build_agentic_thread_context(
        self,
        content: str,
        author: str,
        engagement_reason: str,
        agent_identity: str,
    ) -> str:
        """Build LinkedIn-specific context for the digital twin drafter."""
        return (
            f"Author: {author or 'Unknown'}\n"
            f"Engagement reason: {engagement_reason or 'general'}\n"
            f"Agent identity allowed: {agent_identity or '0102'}\n"
            "Goal: add a concrete LinkedIn comment that advances the discussion.\n"
            f"Post:\n{content.strip()}"
        )

    def _build_agentic_constraints(
        self,
        content: str,
        engagement_reason: str,
        agent_identity: str,
    ) -> Dict[str, Any]:
        """Build wardrobe-like constraints for LinkedIn replies."""
        mention_foundups = (
            engagement_reason in {"capital_pushback", "ai_topic"}
            or "foundups" in str(content or "").lower()
            or "openclaw" in str(content or "").lower()
        )
        return {
            "platform": "linkedin",
            "agent_identity": agent_identity or "0102",
            "tone": "direct, technical, constructive",
            "audience": "linkedin professionals",
            "no_empty_praise": True,
            "max_length": 300,
            "hashtags": "avoid",
            "mention_foundups_if_relevant": mention_foundups,
            "engagement_reason": engagement_reason or "general",
        }

    async def read_selected_post_content_dom(self) -> Optional[Dict[str, Any]]:
        """
        Read the currently selected/active LinkedIn post from DOM.

        Selection heuristics:
        1. Post containing the active element
        2. Post containing an open comment box
        3. Post nearest the viewport center
        """
        driver = await self.router._ensure_selenium()
        if not driver:
            return None

        try:
            result = driver.execute_script("""
            function findPostContainer(node) {
                let current = node;
                for (let i = 0; i < 20; i++) {
                    if (!current) break;
                    if (
                        current.classList?.contains('feed-shared-update-v2') ||
                        current.classList?.contains('occludable-update') ||
                        current.getAttribute?.('data-urn')
                    ) {
                        return current;
                    }
                    current = current.parentElement;
                }
                return null;
            }

            function extractPost(postContainer, source) {
                if (!postContainer) return { ok: false, error: 'post container not found', source };
                const textBox = postContainer.querySelector('span[data-testid="expandable-text-box"]');
                const content = (textBox?.textContent || postContainer.innerText || '').trim();
                let author = 'Unknown';
                let authorUrl = '';
                const authorLink = postContainer.querySelector('a[href*="/in/"]') ||
                                   postContainer.querySelector('a[href*="/company/"]');
                if (authorLink) {
                    authorUrl = authorLink.href || '';
                    const authorSpan = authorLink.querySelector('span[dir="ltr"] span') ||
                                       authorLink.querySelector('span');
                    if (authorSpan) author = (authorSpan.textContent || '').trim() || author;
                }
                const rect = postContainer.getBoundingClientRect();
                return {
                    ok: !!content,
                    source,
                    author,
                    author_url: authorUrl,
                    content: content.substring(0, 500),
                    content_full_length: content.length,
                    position: { top: rect.top, left: rect.left, width: rect.width, height: rect.height },
                };
            }

            const active = document.activeElement;
            let postContainer = findPostContainer(active);
            if (postContainer) {
                return extractPost(postContainer, 'active_element');
            }

            const openCommentBox =
                document.querySelector('div[componentkey^="commentBox-"]') ||
                document.querySelector('form.comments-comment-box__form') ||
                document.querySelector('[contenteditable="true"]');
            postContainer = findPostContainer(openCommentBox);
            if (postContainer) {
                return extractPost(postContainer, 'open_comment_box');
            }

            const textBoxes = Array.from(document.querySelectorAll('span[data-testid="expandable-text-box"]'))
                .filter((el) => el && el.offsetParent !== null);
            if (!textBoxes.length) {
                return { ok: false, error: 'No visible posts found', source: 'viewport_fallback' };
            }

            const viewportCenter = window.innerHeight / 2;
            let best = null;
            let bestDistance = Number.POSITIVE_INFINITY;
            for (const textBox of textBoxes) {
                const rect = textBox.getBoundingClientRect();
                const center = rect.top + (rect.height / 2);
                const distance = Math.abs(center - viewportCenter);
                if (distance < bestDistance) {
                    bestDistance = distance;
                    best = textBox;
                }
            }
            postContainer = findPostContainer(best);
            return extractPost(postContainer, 'viewport_center');
            """)
            if result and result.get("ok"):
                self._log_dom_action(
                    "selected_post_read",
                    {
                        "source": result.get("source"),
                        "author": result.get("author"),
                    },
                )
                return result
        except Exception as exc:
            logger.debug(f"[LINKEDIN] Selected post read failed: {exc}")
        return None

    def _get_preferred_external_target(self) -> Optional[tuple[str, str]]:
        """Read the active external model target from OpenClaw environment."""
        provider = os.getenv("OPENCLAW_CONVERSATION_PREFERRED_PROVIDER", "").strip().lower()
        model = os.getenv("OPENCLAW_CONVERSATION_PREFERRED_MODEL", "").strip().lower()
        if not provider or not model:
            return None
        return provider, model

    def _try_external_model_agentic_reply(
        self,
        thread_context: str,
        constraints: Dict[str, Any],
        snippets: List[str],
    ) -> Optional[Dict[str, Any]]:
        """Draft a LinkedIn reply using the active OpenClaw external provider/model."""
        target = self._get_preferred_external_target()
        if not target:
            return None
        provider_name, model_name = target

        try:
            from modules.ai_intelligence.ai_gateway.src.ai_gateway import AIGateway

            gw = AIGateway()
            provider = gw.providers.get(provider_name)
            if provider is None or not provider.api_key:
                return None

            provider.models["social"] = model_name
            provider.models["quick"] = model_name
            memory_block = ""
            if snippets:
                memory_block = "\nReference memory:\n" + "\n".join(
                    f"- {snippet[:140]}" for snippet in snippets[:3]
                )
            constraint_block = "\n".join(f"- {k}: {v}" for k, v in constraints.items())
            prompt = (
                "You are 0102 drafting a LinkedIn reply through 012's account.\n"
                "Write one concise professional comment.\n"
                "Add one concrete point, counterpoint, or extension.\n"
                "No filler. No generic praise. No hashtags unless clearly useful.\n"
                f"{memory_block}\n\n"
                "Constraints:\n"
                f"{constraint_block}\n\n"
                "LinkedIn post context:\n"
                f"{thread_context}\n\n"
                "Reply:"
            )
            raw = gw._call_provider(provider, prompt, "social").strip()
            cleaned = self._truncate_reply(raw.strip().strip('"').strip("'"))
            if not cleaned or self._looks_generic_draft(cleaned):
                return None
            return {
                "reply_text": cleaned,
                "provider": provider_name,
                "model": model_name,
            }
        except Exception as exc:
            logger.warning(
                "[LINKEDIN] External model draft failed for %s/%s: %s",
                provider_name,
                model_name,
                exc,
            )
            return None

    def _fallback_agentic_reply(
        self,
        content: str,
        author: str,
        engagement_reason: str,
        agent_identity: str,
    ) -> str:
        """Deterministic LinkedIn fallback when the digital twin drafter is unavailable."""
        content_lower = str(content or "").lower()
        reason = engagement_reason or self._infer_engagement_reason(content, author)
        identity = agent_identity or "0102"

        if any(token in content_lower for token in ["robot", "robotics", "embodied", "fleet", "bodily autonomy"]):
            reply = (
                "That is the real shift. Once learning is grounded in embodied loops, one robot improving "
                "turns into fleet memory compounding across every deployment. We are building the software-side "
                f"version of that with {identity} and Holo Index."
            )
        elif reason == "capital_pushback":
            reply = (
                "The bottleneck is no longer just capital access. The advantage now comes from coordinating "
                "compute, memory, and execution loops. That is why we frame it as ROC, return on compute, "
                "instead of only ROI."
            )
        elif any(token in content_lower for token in ["openclaw", "ironclaw", "agent", "automation", "autonomous"]):
            reply = (
                "The useful move is turning model output into durable operational memory. Otherwise every deployment "
                "restarts from prompts instead of compounding. That is the layer we are pushing with "
                f"{identity}, FoundUps, and Holo Index."
            )
        elif reason == "target_author":
            reply = (
                "Useful framing. The leverage appears when each run leaves behind reusable operational memory, "
                "not just a better demo. That is where autonomous systems start compounding instead of repeating."
            )
        else:
            reply = (
                "Useful framing. The part that matters is converting each run into reusable operational memory "
                "and execution patterns, otherwise capability looks impressive but does not compound."
            )

        return self._truncate_reply(reply)

    async def draft_agentic_reply(
        self,
        post_index: int = 0,
        post_context: str = "",
        author: str = "",
        engagement_reason: str = "",
        agent_identity: str = "0102",
        use_selected_post: bool = False,
        read_first: bool = False,
    ) -> Dict[str, Any]:
        """
        Draft an agentic LinkedIn reply from visible post context or supplied text.

        This is the bridge between LinkedIn feed actions and the digital twin comment drafter.
        """
        post_data: Dict[str, Any] = {}
        prefer_live_dom = read_first or use_selected_post or not post_context.strip()

        if prefer_live_dom and use_selected_post:
            post_data = await self.read_selected_post_content_dom() or {}
        if prefer_live_dom and not post_data:
            post_data = await self.read_post_content_dom(post_index) or {}
        if not post_data and post_context.strip():
            post_data = {
                "content": post_context.strip(),
                "author": author.strip() or "Unknown",
                "engagement_reason": engagement_reason.strip() or "",
            }

        content = str(post_data.get("content", "") or post_context).strip()
        author_name = str(post_data.get("author", "") or author).strip() or "Unknown"
        reason = (
            str(post_data.get("engagement_reason", "")).strip()
            or engagement_reason.strip()
            or self._infer_engagement_reason(content, author_name)
        )

        if not content:
            return {
                "success": False,
                "error": "No post context available for agentic reply drafting",
                "post_index": post_index,
                "use_selected_post": use_selected_post,
            }

        draft_text = ""
        method = "wardrobe_fallback"
        draft_confidence = 0.0
        selected_target = self._get_preferred_external_target()
        thread_context = self._build_agentic_thread_context(
            content,
            author_name,
            reason,
            agent_identity,
        )
        constraints = self._build_agentic_constraints(
            content,
            reason,
            agent_identity,
        )

        snippets: List[str] = []
        if self._ensure_linkedin_comment_drafter():
            try:
                snippets = [
                    r.get("text", "")
                    for r in self._linkedin_comment_drafter.voice_memory.query(thread_context, k=5)
                ]
            except Exception as exc:
                logger.debug(f"[LINKEDIN] Voice memory query failed: {exc}")

        external_reply = self._try_external_model_agentic_reply(
            thread_context,
            constraints,
            snippets,
        )
        if external_reply:
            draft_text = str(external_reply.get("reply_text", "")).strip()
            method = "external_model"

        if not draft_text and self._ensure_linkedin_comment_drafter():
            try:
                draft = await asyncio.to_thread(
                    self._linkedin_comment_drafter.draft,
                    thread_context=thread_context,
                    platform="linkedin",
                    context_url="https://www.linkedin.com/feed/",
                    reply_to_id=f"index_{post_index}",
                    constraints=constraints,
                )
                candidate = self._truncate_reply(getattr(draft, "text", ""))
                draft_confidence = float(getattr(draft, "confidence", 0.0) or 0.0)
                if candidate and not self._looks_generic_draft(candidate):
                    draft_text = candidate
                    method = "digital_twin"
            except Exception as exc:
                logger.warning(f"[LINKEDIN] Agentic draft generation failed, using fallback: {exc}")

        if not draft_text:
            draft_text = self._fallback_agentic_reply(
                content,
                author_name,
                reason,
                agent_identity,
            )

        return {
            "success": True,
            "reply_text": draft_text,
            "post_index": post_index,
            "author": author_name,
            "engagement_reason": reason,
            "agent_identity": agent_identity or "0102",
            "method": method,
            "draft_confidence": draft_confidence,
            "read_first": read_first,
            "use_selected_post": use_selected_post,
            "external_target": (
                {"provider": selected_target[0], "model": selected_target[1]}
                if selected_target
                else None
            ),
            "content_preview": content[:280],
        }

    @staticmethod
    def _profile_slug_from_url(profile_url: str) -> str:
        """Extract stable profile slug from LinkedIn profile URL."""
        match = re.search(r"/in/([^/?#]+)/?", profile_url or "")
        if match:
            return match.group(1).strip()
        return (profile_url or "").strip() or f"profile_{int(datetime.now().timestamp())}"

    @staticmethod
    def _split_name(name: str) -> tuple[str, str]:
        """Split a full name into first/last with safe fallbacks."""
        parts = (name or "").strip().split()
        if not parts:
            return "unknown", "user"
        if len(parts) == 1:
            return parts[0], ""
        return parts[0], " ".join(parts[1:])

    async def _extract_profile_metadata(self) -> Dict[str, str]:
        """
        Best-effort extraction of profile metadata from visible page content.
        Used before Connect click to enforce outbound policy.
        """
        result = await self.router.execute(
            'find_by_description',
            {
                'description': (
                    'LinkedIn profile header fields: full name, headline, company, industry'
                ),
                'extract_text': True,
            },
            driver=DriverType.VISION,
        )

        if not result.success:
            return {}

        data = result.result_data or {}
        # Accept several possible extraction shapes.
        if isinstance(data.get("profile"), dict):
            data = data["profile"]
        elif isinstance(data.get("extracted_profiles"), list) and data["extracted_profiles"]:
            first = data["extracted_profiles"][0]
            if isinstance(first, dict):
                data = first

        metadata = {
            "name": str(data.get("name", "")).strip(),
            "headline": str(data.get("headline", "")).strip(),
            "company": str(data.get("company", "")).strip(),
            "industry": str(data.get("industry", "")).strip(),
        }
        return {k: v for k, v in metadata.items() if v}

    async def send_connection_request(
        self,
        profile_url: str,
        message: Optional[str] = None,
        profile_name: Optional[str] = None,
        headline: Optional[str] = None,
        company: Optional[str] = None,
        industry: Optional[str] = None,
        dry_run: bool = False,
    ) -> LinkedInActionResult:
        """
        Send a LinkedIn connection request with hard role-policy enforcement.

        Policy:
        - allow: cxo/founder/architect/blockchain/web3
        - block: business development/marketing/recruiting
        - block: employee-level when no allow signal
        - block: missing profile metadata (default strict mode)
        """
        start_time = datetime.now()
        profile_slug = self._profile_slug_from_url(profile_url)

        if not self._connection_manager or not self._connection_profile_cls:
            return LinkedInActionResult(
                success=False,
                action="send_connection_request",
                post_id=profile_slug,
                error="connection_policy_manager_unavailable",
            )

        nav = await self.navigate_to_profile(profile_url)
        if not nav.success:
            return LinkedInActionResult(
                success=False,
                action="send_connection_request",
                post_id=profile_slug,
                error=f"navigate_failed: {nav.error}",
                duration_ms=nav.duration_ms,
            )

        metadata = {
            "name": (profile_name or "").strip(),
            "headline": (headline or "").strip(),
            "company": (company or "").strip(),
            "industry": (industry or "").strip(),
        }
        if not metadata["name"] or not metadata["headline"]:
            extracted = await self._extract_profile_metadata()
            metadata["name"] = metadata["name"] or extracted.get("name", "")
            metadata["headline"] = metadata["headline"] or extracted.get("headline", "")
            metadata["company"] = metadata["company"] or extracted.get("company", "")
            metadata["industry"] = metadata["industry"] or extracted.get("industry", "")

        if not (metadata["headline"] or metadata["company"] or metadata["industry"]):
            elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            return LinkedInActionResult(
                success=False,
                action="send_connection_request",
                post_id=profile_slug,
                error="policy_blocked: missing_profile_metadata",
                duration_ms=elapsed_ms,
                details={"profile": metadata},
            )

        first_name, last_name = self._split_name(metadata.get("name", ""))
        target_profile = self._connection_profile_cls(
            profile_id=profile_slug,
            first_name=first_name,
            last_name=last_name,
            headline=metadata.get("headline", ""),
            company=metadata.get("company", "") or None,
            industry=metadata.get("industry", "") or None,
            profile_url=profile_url,
        )

        policy = self._connection_manager.evaluate_connection_policy(target_profile)
        if dry_run:
            return _connection_policy_result(
                profile_slug, metadata, policy, start_time, dry_run=True,
            )

        request = self._connection_manager.send_connection_request(
            profile_slug,
            message=message,
            target_profile=target_profile,
        )

        blocked_status = (
            self._connection_status_cls.BLOCKED if self._connection_status_cls else None
        )
        if not policy.allowed or (blocked_status is not None and request.status == blocked_status):
            return _connection_policy_result(
                profile_slug, metadata, policy, start_time, request_status=request.status.value,
            )

        connect_click = await self.router.execute(
            'click_by_description',
            {'description': 'Connect button on LinkedIn profile'},
            driver=DriverType.VISION,
        )
        if not connect_click.success:
            elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            return LinkedInActionResult(
                success=False,
                action="send_connection_request",
                post_id=profile_slug,
                error=f"connect_click_failed: {connect_click.error}",
                duration_ms=elapsed_ms,
                details={
                    "policy_reason": policy.reason,
                    "request_status": request.status.value,
                },
            )

        # LinkedIn variants:
        # 1) direct send after connect click
        # 2) modal with optional add note + send invitation
        send_result, add_note_result, type_result = await _connection_invitation_clicks(
            self.router, message,
        )

        invitation_sent = connect_click.success and (
            (send_result is not None and send_result.success)
            or (not message and add_note_result is None)
        )
        if invitation_sent:
            self._session_stats['connections_sent'] += 1

        elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        return LinkedInActionResult(
            success=invitation_sent,
            action="send_connection_request",
            post_id=profile_slug,
            duration_ms=elapsed_ms,
            error=None if invitation_sent else "send_invitation_failed",
            details={
                "policy_reason": policy.reason,
                "matched_allow": policy.matched_allow,
                "request_status": request.status.value,
                "profile": metadata,
                "connect_click_success": connect_click.success,
                "send_click_success": send_result.success if send_result is not None else None,
                "add_note_success": add_note_result.success if add_note_result else None,
                "note_typed_success": type_result.success if type_result else None,
            },
        )

    async def navigate_to_feed(self) -> RoutingResult:
        """
        Navigate to LinkedIn feed.
        Uses Selenium (fast, known URL).
        """
        result = await self.router.execute(
            'navigate',
            {'url': 'https://www.linkedin.com/feed/'},
            driver=DriverType.SELENIUM,
        )

        if result.success:
            await asyncio.sleep(2)  # Wait for feed to load
            logger.info("[LINKEDIN] Navigated to feed")

        return result

    # ==========================================================================
    # FEED ITERATOR - DOM-First Post Processing
    # ==========================================================================

    async def refresh_feed(self) -> RoutingResult:
        """
        Refresh LinkedIn feed (F5 equivalent).

        Resets iterator state and navigates to https://www.linkedin.com/feed/

        Returns:
            RoutingResult from navigation
        """
        logger.info("[LINKEDIN] Refreshing feed...")
        self._log_dom_action("feed_refresh", {"previous_index": self._feed_iterator_index})

        # Reset iterator state
        self._feed_iterator_index = 0
        self._feed_posts_cache.clear()
        self._last_refresh_time = datetime.now()

        # Navigate to feed URL (acts as refresh)
        result = await self.router.execute(
            'navigate',
            {'url': 'https://www.linkedin.com/feed/'},
            driver=DriverType.SELENIUM,
        )

        if result.success:
            await asyncio.sleep(2)  # Wait for feed to load
            logger.info("[LINKEDIN] Feed refreshed")

        return result

    async def feed_iterator_reset(self) -> None:
        """Reset feed iterator to beginning (index 0)."""
        self._feed_iterator_index = 0
        self._feed_posts_cache.clear()
        self._log_dom_action("feed_iterator_reset", {"timestamp": datetime.now().isoformat()})
        logger.info("[LINKEDIN] Feed iterator reset to index 0")

    async def feed_iterator_next(self) -> Optional[Dict[str, Any]]:
        """
        Get next post in feed using DOM-first approach.

        Auto-scrolls if needed to load more posts.

        Returns:
            Post dict with content, author, is_repost, engagement_info or None if end
        """
        # Try to read current index
        post = await self._read_feed_post_at_index(self._feed_iterator_index)

        if post is None:
            # Try scrolling to load more posts
            await self._scroll_feed_down()
            await asyncio.sleep(1)
            post = await self._read_feed_post_at_index(self._feed_iterator_index)

        if post is not None:
            self._feed_iterator_index += 1
            self._session_stats['posts_read'] += 1
            return post

        logger.info(f"[LINKEDIN] Feed iterator reached end at index {self._feed_iterator_index}")
        return None

    async def feed_iterator_current(self) -> Optional[Dict[str, Any]]:
        """Get current post without advancing iterator."""
        if self._feed_iterator_index == 0:
            return await self._read_feed_post_at_index(0)
        return await self._read_feed_post_at_index(self._feed_iterator_index - 1)

    async def feed_iterator_skip(self, count: int = 1) -> int:
        """
        Skip posts in feed without reading content.

        Args:
            count: Number of posts to skip

        Returns:
            Actual number of posts skipped
        """
        skipped = 0
        for _ in range(count):
            post = await self._read_feed_post_at_index(self._feed_iterator_index)
            if post is None:
                await self._scroll_feed_down()
                await asyncio.sleep(0.5)
                post = await self._read_feed_post_at_index(self._feed_iterator_index)
                if post is None:
                    break
            self._feed_iterator_index += 1
            skipped += 1

        self._log_dom_action("feed_iterator_skip", {"count": count, "skipped": skipped})
        return skipped

    async def _read_feed_post_at_index(self, index: int) -> Optional[Dict[str, Any]]:
        """
        Read a single post from feed at given index using DOM.

        Detects:
        - Reposts (skip if configured)
        - AI topics (for engagement)
        - Capital pushback opportunities
        - Target authors

        Args:
            index: Post index (0 = first visible)

        Returns:
            Post dict or None if not found
        """
        driver = await self.router._ensure_selenium()
        if not driver:
            return None

        try:
            post_data = driver.execute_script("""
            const index = arguments[0];

            // Find all post content containers
            const textBoxes = document.querySelectorAll('span[data-testid="expandable-text-box"]');
            if (textBoxes.length <= index) {
                return { ok: false, error: 'Post not found', index: index, found: textBoxes.length };
            }

            const textBox = textBoxes[index];
            const content = textBox.textContent || '';

            // Find post container (traverse up)
            let postContainer = textBox;
            for (let i = 0; i < 15; i++) {
                postContainer = postContainer.parentElement;
                if (!postContainer) break;
                if (postContainer.classList.contains('feed-shared-update-v2') ||
                    postContainer.getAttribute('data-urn') ||
                    postContainer.classList.contains('occludable-update')) {
                    break;
                }
            }

            // Extract author
            let author = 'Unknown';
            let authorUrl = '';
            if (postContainer) {
                const authorLink = postContainer.querySelector('a[href*="/in/"]') ||
                                   postContainer.querySelector('a[href*="/company/"]');
                if (authorLink) {
                    authorUrl = authorLink.href || '';
                    const authorSpan = authorLink.querySelector('span[dir="ltr"] span') ||
                                       authorLink.querySelector('span');
                    if (authorSpan) author = authorSpan.textContent.trim();
                }
            }

            // Detect repost
            let isRepost = false;
            let repostInfo = null;
            if (postContainer) {
                const headerText = postContainer.innerText.slice(0, 300).toLowerCase();
                if (headerText.includes('reposted') || headerText.includes('shared')) {
                    isRepost = true;
                    // Try to extract who reposted
                    const repostMatch = headerText.match(/(.+?)\\s*(reposted|shared)/);
                    if (repostMatch) {
                        repostInfo = { reposted_by: repostMatch[1].trim() };
                    }
                }
            }

            // AI detection keywords
            const aiKeywords = [
                'ai', 'artificial intelligence', 'machine learning', 'llm',
                'gpt', 'chatgpt', 'claude', 'gemini', 'copilot', 'openai',
                'anthropic', 'autonomous', 'agent', 'automation', 'neural',
                'deep learning', 'transformer', 'singularity', 'agi',
                'superintelligence', 'moltbook', 'dyson swarm', '#openclaw'
            ];

            // Capital pushback keywords
            const capitalKeywords = [
                'series a', 'series b', 'series c', 'raised', 'funding round',
                'venture capital', 'vc funding', 'seed round', 'pre-seed',
                '$5m', '$10m', '$50m', '$100m', 'million in funding',
                'investor', 'pitch deck', 'fundraise', 'valuation',
                'accelerator', 'incubator', 'term sheet', 'cap table',
                'equity round', 'dilution', 'exit strategy'
            ];

            // Target authors
            const targetAuthors = [
                'salim ismail', 'peter diamandis', 'ray kurzweil',
                'pieter franken', 'mayoran rajendra', 'japan pivot'
            ];

            const contentLower = content.toLowerCase();
            const authorLower = author.toLowerCase();

            const isAiPost = aiKeywords.some(kw => contentLower.includes(kw));
            const isCapitalPost = capitalKeywords.some(kw => contentLower.includes(kw));
            const isTargetAuthor = targetAuthors.some(name => authorLower.includes(name));

            // Engagement decision
            const shouldEngage = !isRepost && (isAiPost || isCapitalPost || isTargetAuthor);

            // Get engagement counts if visible
            let likes = 0;
            let comments = 0;
            if (postContainer) {
                const socialCounts = postContainer.querySelector('.social-details-social-counts');
                if (socialCounts) {
                    const likesEl = socialCounts.querySelector('[aria-label*="like"], [aria-label*="reaction"]');
                    const commentsEl = socialCounts.querySelector('[aria-label*="comment"]');
                    if (likesEl) likes = parseInt(likesEl.textContent) || 0;
                    if (commentsEl) comments = parseInt(commentsEl.textContent) || 0;
                }
            }

            // Get position for click targeting
            const rect = textBox.getBoundingClientRect();

            return {
                ok: true,
                index: index,
                author: author,
                author_url: authorUrl,
                content: content.substring(0, 500),
                content_length: content.length,
                is_repost: isRepost,
                repost_info: repostInfo,
                is_ai_post: isAiPost,
                is_capital_post: isCapitalPost,
                is_target_author: isTargetAuthor,
                should_engage: shouldEngage,
                engagement_reason: isAiPost ? 'ai_topic' :
                                   isCapitalPost ? 'capital_pushback' :
                                   isTargetAuthor ? 'target_author' : 'none',
                matched_keywords: {
                    ai: aiKeywords.filter(kw => contentLower.includes(kw)),
                    capital: capitalKeywords.filter(kw => contentLower.includes(kw)),
                },
                likes: likes,
                comments: comments,
                position: { top: rect.top, left: rect.left, width: rect.width, height: rect.height },
                timestamp: new Date().toISOString(),
            };
            """, index)

            if post_data and post_data.get('ok'):
                self._log_dom_action("feed_iterator_read", {
                    "index": index,
                    "is_repost": post_data.get('is_repost'),
                    "should_engage": post_data.get('should_engage'),
                    "engagement_reason": post_data.get('engagement_reason'),
                })
                return post_data

            return None

        except Exception as e:
            logger.debug(f"[LINKEDIN] Feed read at index {index} failed: {e}")
            return None

    async def _scroll_feed_down(self) -> bool:
        """Scroll down to load more posts."""
        driver = await self.router._ensure_selenium()
        if not driver:
            return False

        try:
            driver.execute_script("""
                window.scrollBy({
                    top: window.innerHeight * 0.8,
                    behavior: 'smooth'
                });
            """)
            self._log_dom_action("feed_scroll_down", {"index": self._feed_iterator_index})
            return True
        except Exception as e:
            logger.debug(f"[LINKEDIN] Scroll failed: {e}")
            return False

    async def iterate_feed(
        self,
        max_posts: int = 10,
        skip_reposts: bool = True,
        engagement_filter: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Iterate through feed and collect posts.

        This is a convenience method that combines refresh + iterate.

        Args:
            max_posts: Maximum posts to collect
            skip_reposts: Skip reposted content
            engagement_filter: Only return engagement-worthy posts

        Returns:
            List of post dicts matching criteria
        """
        await self.refresh_feed()

        posts = []
        attempts = 0
        max_attempts = max_posts * 3  # Allow for skipped posts

        while len(posts) < max_posts and attempts < max_attempts:
            post = await self.feed_iterator_next()
            if post is None:
                break

            attempts += 1

            # Apply filters
            if skip_reposts and post.get('is_repost'):
                self._log_dom_action("iterate_skip_repost", {"index": post.get('index')})
                continue

            if engagement_filter and not post.get('should_engage'):
                continue

            posts.append(post)

        self._log_dom_action("iterate_feed_complete", {
            "collected": len(posts),
            "attempts": attempts,
            "max_posts": max_posts,
        })
        logger.info(f"[LINKEDIN] Feed iteration: collected {len(posts)} posts in {attempts} attempts")

        return posts

    async def navigate_to_profile(self, profile_url: str) -> RoutingResult:
        """Navigate to a LinkedIn profile."""
        return await self.router.execute(
            'navigate',
            {'url': profile_url},
            driver=DriverType.SELENIUM,
        )

    async def read_feed(self, max_posts: int = 10) -> List[LinkedInPost]:
        """
        Read and understand posts in LinkedIn feed.
        Uses UI-TARS Vision to see and extract post content.
        
        Args:
            max_posts: Maximum posts to read
            
        Returns:
            List of LinkedInPost objects with content and relevance
        """
        logger.info(f"[LINKEDIN] Reading feed (max {max_posts} posts)")
        
        # Navigate to feed first
        nav_result = await self.navigate_to_feed()
        if not nav_result.success:
            logger.error(f"[LINKEDIN] Failed to navigate: {nav_result.error}")
            return []
        
        posts = []
        scroll_count = 0
        max_scrolls = max_posts // 3 + 1  # ~3 posts per scroll
        
        while len(posts) < max_posts and scroll_count < max_scrolls:
            # Use vision to read visible posts
            read_result = await self.router.execute(
                'find_by_description',
                {
                    'description': 'LinkedIn feed posts with author name, content text, and engagement counts',
                    'extract_text': True,
                },
                driver=DriverType.VISION,
            )
            
            if read_result.success and read_result.result_data.get('extracted_posts'):
                for post_data in read_result.result_data['extracted_posts']:
                    post = self._parse_post(post_data)
                    if post and post.post_id not in [p.post_id for p in posts]:
                        # Evaluate relevance
                        post.is_relevant = self._is_relevant(post.content)
                        if post.is_relevant and self._llm_available:
                            post.suggested_reply = await self._generate_reply(post)
                        posts.append(post)
                        self._session_stats['posts_read'] += 1
            
            # Scroll down for more posts
            await self.router.execute(
                'scroll_to_element',
                {'description': 'scroll down to see more posts'},
                driver=DriverType.VISION,
            )
            await asyncio.sleep(1)
            scroll_count += 1
        
        logger.info(f"[LINKEDIN] Read {len(posts)} posts, {sum(1 for p in posts if p.is_relevant)} relevant")
        return posts

    def _parse_post(self, post_data: Dict[str, Any]) -> Optional[LinkedInPost]:
        """Parse vision-extracted post data into LinkedInPost."""
        try:
            return LinkedInPost(
                post_id=post_data.get('id', f"post_{datetime.now().timestamp()}"),
                author=post_data.get('author', 'Unknown'),
                content=post_data.get('content', ''),
                timestamp=post_data.get('timestamp', 'recent'),
                likes=int(post_data.get('likes', 0)),
                comments=int(post_data.get('comments', 0)),
            )
        except Exception as e:
            logger.warning(f"[LINKEDIN] Failed to parse post: {e}")
            return None

    def _is_relevant(self, content: str) -> bool:
        """Determine if post content is relevant for 012's interests."""
        content_lower = content.lower()
        return any(kw in content_lower for kw in self.RELEVANCE_KEYWORDS)

    async def read_post_content_dom(self, post_index: int = 0) -> Optional[Dict[str, Any]]:
        """
        Read post content directly from DOM (faster than vision).

        DOM Selectors (from 012's analysis):
        - Post content: span[data-testid="expandable-text-box"]
        - Author: Various spans in post header

        Args:
            post_index: Which post to read (0 = first visible)

        Returns:
            Dict with author, content, is_ai_post, or None if failed
        """
        driver = await self.router._ensure_selenium()
        if not driver:
            return None

        try:
            result = driver.execute_script("""
            const index = arguments[0];

            // Find all expandable text boxes (post content)
            const textBoxes = document.querySelectorAll('span[data-testid="expandable-text-box"]');
            if (textBoxes.length <= index) {
                return { ok: false, error: 'Post not found at index', found: textBoxes.length };
            }

            const textBox = textBoxes[index];
            const content = textBox.textContent || '';

            // Try to find author name (usually in parent structure)
            let author = 'Unknown';
            const postContainer = textBox.closest('[data-urn]') ||
                                  textBox.closest('article') ||
                                  textBox.closest('div[class*="feed"]');
            if (postContainer) {
                const authorSpan = postContainer.querySelector('span[dir="ltr"] > span') ||
                                   postContainer.querySelector('a[href*="/in/"] span');
                if (authorSpan) author = authorSpan.textContent.trim();
            }

            // AI detection keywords
            const aiKeywords = [
                'ai', 'artificial intelligence', 'machine learning', 'llm',
                'gpt', 'chatgpt', 'claude', 'gemini', 'copilot', 'openai',
                'anthropic', 'autonomous', 'agent', 'automation', 'neural',
                'deep learning', 'transformer', 'singularity', 'agi',
                'superintelligence', 'moltbook', 'dyson swarm', '#openclaw'
            ];

            // Closed capital keywords - 012 pushback opportunities
            // "Access to closed capital controlling ideation"
            const capitalKeywords = [
                'series a', 'series b', 'series c', 'raised', 'funding round',
                'venture capital', 'vc funding', 'seed round', 'pre-seed',
                '$5m', '$10m', '$50m', '$100m', 'million in funding',
                'investor', 'pitch deck', 'fundraise', 'valuation',
                'accelerator', 'incubator', 'term sheet', 'cap table',
                'equity round', 'dilution', 'exit strategy'
            ];

            // Thought leaders 012 wants to engage
            const targetAuthors = [
                'salim ismail', 'peter diamandis', 'ray kurzweil',
                'pieter franken', 'mayoran rajendra', 'japan pivot'
            ];

            const contentLower = content.toLowerCase();
            const authorLower = author.toLowerCase();

            const isAiPost = aiKeywords.some(kw => contentLower.includes(kw));
            const isCapitalPost = capitalKeywords.some(kw => contentLower.includes(kw));
            const isTargetAuthor = targetAuthors.some(name => authorLower.includes(name));

            // Get position for click targeting
            const rect = textBox.getBoundingClientRect();

            // Engagement decision: AI post OR capital pushback OR target author
            const shouldEngage = isAiPost || isCapitalPost || isTargetAuthor;

            return {
                ok: true,
                author: author,
                content: content.substring(0, 500),
                content_full_length: content.length,
                is_ai_post: isAiPost,
                is_capital_post: isCapitalPost,
                is_target_author: isTargetAuthor,
                should_engage: shouldEngage,
                matched_ai_keywords: aiKeywords.filter(kw => contentLower.includes(kw)),
                matched_capital_keywords: capitalKeywords.filter(kw => contentLower.includes(kw)),
                engagement_reason: isAiPost ? 'ai_topic' :
                                   isCapitalPost ? 'capital_pushback' :
                                   isTargetAuthor ? 'target_author' : 'none',
                position: { top: rect.top, left: rect.left, width: rect.width, height: rect.height },
                post_index: index,
            };
            """, post_index)

            if result and result.get('ok'):
                self._log_dom_action("read_post_dom", {
                    "post_index": post_index,
                    "is_ai_post": result.get('is_ai_post'),
                    "is_capital_post": result.get('is_capital_post'),
                    "is_target_author": result.get('is_target_author'),
                    "should_engage": result.get('should_engage'),
                    "engagement_reason": result.get('engagement_reason'),
                    "author": result.get('author'),
                    "matched_ai_keywords": result.get('matched_ai_keywords', []),
                    "matched_capital_keywords": result.get('matched_capital_keywords', []),
                })
                reason = result.get('engagement_reason', 'none')
                logger.info(f"[LINKEDIN] DOM read post {post_index}: engage={result.get('should_engage')} ({reason}), author={result.get('author')}")
                return result
            else:
                logger.debug(f"[LINKEDIN] DOM read failed: {result}")
                return None

        except Exception as e:
            logger.warning(f"[LINKEDIN] DOM post read error: {e}")
            return None

    async def scan_feed_for_engagement(self, max_posts: int = 5) -> List[Dict[str, Any]]:
        """
        Scan visible feed posts for engagement opportunities using DOM.

        Detects:
        - AI/tech posts (knowledge sharing)
        - Closed capital posts (FoundUps pushback - "access to closed capital controlling ideation")
        - Target author posts (thought leaders to engage)

        Returns:
            List of engagement-worthy posts with content, author, position, reason
        """
        engage_posts = []
        posts_scanned = 0

        for i in range(max_posts):
            post = await self.read_post_content_dom(i)
            if post is None:
                break  # No more posts
            posts_scanned += 1

            if post.get('should_engage'):
                engage_posts.append(post)

        # Categorize by reason
        ai_posts = [p for p in engage_posts if p.get('engagement_reason') == 'ai_topic']
        capital_posts = [p for p in engage_posts if p.get('engagement_reason') == 'capital_pushback']
        author_posts = [p for p in engage_posts if p.get('engagement_reason') == 'target_author']

        self._log_dom_action("feed_scan_complete", {
            "posts_scanned": posts_scanned,
            "engage_posts_found": len(engage_posts),
            "ai_posts": len(ai_posts),
            "capital_posts": len(capital_posts),
            "author_posts": len(author_posts),
        })
        logger.info(
            f"[LINKEDIN] Feed scan: {len(engage_posts)} engagement opportunities "
            f"(AI={len(ai_posts)}, capital_pushback={len(capital_posts)}, target_author={len(author_posts)}) "
            f"in {posts_scanned} posts"
        )
        return engage_posts

    # Backward compatibility alias
    async def scan_feed_for_ai_posts(self, max_posts: int = 5) -> List[Dict[str, Any]]:
        """Alias for scan_feed_for_engagement (backward compatibility)."""
        return await self.scan_feed_for_engagement(max_posts)

    async def _generate_reply(self, post: LinkedInPost) -> str:
        """Generate intelligent reply using LLM."""
        if not self._llm_available:
            return self._template_reply(post)
        
        try:
            prompt = f"""Generate a professional LinkedIn comment for this post.
            
Author: {post.author}
Content: {post.content[:500]}

Guidelines:
- Professional but friendly tone
- Add value to the conversation
- Keep under 200 characters
- Reference specific points from the post
- Represent FoundUps/Move2Japan brand positively
"""
            response = self.llm.generate(prompt)
            return response[:200] if response else self._template_reply(post)
        except Exception as e:
            logger.warning(f"[LINKEDIN] LLM failed: {e}")
            return self._template_reply(post)

    def _template_reply(self, post: LinkedInPost) -> str:
        """Generate template reply when LLM unavailable."""
        templates = [
            "Great insights! Thanks for sharing.",
            "This resonates with our work at FoundUps. Appreciate the perspective!",
            "Valuable points here. Looking forward to more content like this.",
            "Well said! This aligns with what we're building.",
        ]
        import random
        return random.choice(templates)

    async def like_post(
        self,
        post_id: str,
        post_index: int = 0,
        skip_reposts: bool = True,
    ) -> LinkedInActionResult:
        """
        Like a LinkedIn post using DOM-first approach.

        DOM Selectors:
        - Like button: button[aria-label*="Like"] or button[aria-label*="React"]
        - Repost indicator: "reposted" text in post header

        Args:
            post_id: Post identifier
            post_index: Which post to like (0 = first visible)
            skip_reposts: If True, skip reposted content (only like original posts)

        Returns:
            LinkedInActionResult
        """
        logger.info(f"[LINKEDIN] Liking post {post_id[:20] if post_id else f'index_{post_index}'}...")
        start_time = datetime.now()

        driver = await self.router._ensure_selenium()
        if not driver:
            return LinkedInActionResult(
                success=False,
                action="like_post",
                post_id=post_id,
                error="No Selenium driver available",
            )

        # DOM-first: Check if repost and find Like button
        try:
            like_result = driver.execute_script("""
                const postIndex = arguments[0];
                const skipReposts = arguments[1];

                // Find all feed posts
                const posts = document.querySelectorAll('[data-testid="expandable-text-box"]');
                if (posts.length <= postIndex) {
                    return { ok: false, error: 'Post not found at index', index: postIndex, found: posts.length };
                }

                // Get the post container (traverse up to find the main post element)
                let postEl = posts[postIndex];
                let postContainer = postEl;
                for (let i = 0; i < 15; i++) {
                    postContainer = postContainer.parentElement;
                    if (!postContainer) break;
                    // Look for common post container patterns
                    if (postContainer.classList.contains('feed-shared-update-v2') ||
                        postContainer.getAttribute('data-urn') ||
                        postContainer.classList.contains('occludable-update')) {
                        break;
                    }
                }

                if (!postContainer) {
                    return { ok: false, error: 'Post container not found', index: postIndex };
                }

                // Scroll post into view
                postEl.scrollIntoView({ behavior: 'smooth', block: 'center' });

                // Check if repost (skip if configured)
                if (skipReposts) {
                    const headerText = postContainer.innerText.slice(0, 200).toLowerCase();
                    if (headerText.includes('reposted') || headerText.includes('shared')) {
                        return { ok: false, error: 'Skipped repost', is_repost: true };
                    }
                }

                // Find Like button within THIS specific post container
                // LinkedIn 2024: aria-label="Reaction button state: no reaction" or "Reaction button state: Like"
                const likeSelectors = [
                    'button[aria-label*="Reaction button"]',
                    'button[aria-label*="Reaction"]',
                    'button[aria-label*="Like"]',
                    'button[aria-label*="React"]',
                ];

                let likeBtn = null;
                for (const sel of likeSelectors) {
                    const btn = postContainer.querySelector(sel);
                    if (btn && btn.offsetParent !== null) {
                        likeBtn = btn;
                        break;
                    }
                }

                if (!likeBtn) {
                    return { ok: false, error: 'Like button not found in post', index: postIndex };
                }

                // Check if already liked
                // LinkedIn 2024: "Reaction button state: Like" = already reacted
                const ariaLabel = likeBtn.getAttribute('aria-label') || '';
                const alreadyLiked = likeBtn.getAttribute('aria-pressed') === 'true' ||
                    ariaLabel.toLowerCase().includes('unlike') ||
                    (ariaLabel.includes('Reaction button state:') && !ariaLabel.includes('no reaction'));
                if (alreadyLiked) {
                    return { ok: true, already_liked: true, method: 'dom', index: postIndex };
                }

                // Click the Like button
                likeBtn.click();
                return { ok: true, method: 'dom', selector: ariaLabel, index: postIndex };
            """, post_index, skip_reposts)

            if like_result.get('ok'):
                self._log_dom_action("like_post", {
                    "method": "dom",
                    "post_index": like_result.get('index', post_index),
                    "already_liked": like_result.get('already_liked', False),
                    "selector": like_result.get('selector', ''),
                })
                if not like_result.get('already_liked'):
                    self._session_stats['likes_given'] += 1
                logger.info(f"[LINKEDIN] Like via DOM: {like_result}")

                duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                return LinkedInActionResult(
                    success=True,
                    action="like_post",
                    post_id=post_id,
                    duration_ms=duration_ms,
                    details={"method": "dom", "already_liked": like_result.get('already_liked', False)},
                )

            # Check if skipped repost
            if like_result.get('is_repost'):
                logger.info(f"[LINKEDIN] Skipped repost at index {post_index}")
                return LinkedInActionResult(
                    success=False,
                    action="like_post",
                    post_id=post_id,
                    error="Skipped repost (only liking original posts)",
                    details={"is_repost": True, "post_index": post_index},
                )

            logger.debug(f"[LINKEDIN] DOM like failed: {like_result.get('error')}")

        except Exception as e:
            logger.debug(f"[LINKEDIN] DOM like exception: {e}")

        # Fallback to vision (DOM-first architecture: vision diagnoses)
        self._log_dom_action("like_post_vision_fallback", {"post_index": post_index})
        result = await self.router.execute(
            'click_by_description',
            {'description': 'Like button (thumbs up icon) on the post', 'platform': 'linkedin'},
        )

        if result.success:
            self._session_stats['likes_given'] += 1

        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        return LinkedInActionResult(
            success=result.success,
            action="like_post",
            post_id=post_id,
            error=result.error,
            duration_ms=duration_ms,
            details={"method": "vision_fallback"},
        )

    async def reply_to_post(
        self,
        post_id: str,
        reply_text: str,
        use_dom_first: bool = True,
        post_index: int = 0,
    ) -> LinkedInActionResult:
        """
        Reply to a LinkedIn post using DOM-first approach with vision fallback.

        DOM Selectors (from 012's analysis):
        - Comment button: span containing "Comment" text
        - Comment box: div[componentkey^="commentBox-"]
        - Post content: span[data-testid="expandable-text-box"]

        Workflow:
        1. Try DOM click on Comment button → fallback to vision
        2. Try DOM focus on comment box → fallback to vision
        3. Type reply with human behavior
        4. Submit via DOM or vision

        Args:
            post_id: Post identifier
            reply_text: Comment text to post
            use_dom_first: Try DOM selectors before vision (default: True)
            post_index: Which post to target in visible feed (0 = first post)

        Returns:
            LinkedInActionResult
        """
        start_time = datetime.now()
        logger.info(f"[LINKEDIN] Replying to post_index={post_index}: {reply_text[:50]}...")
        self._log_dom_action(
            "reply_start",
            {"post_id": post_id, "post_index": post_index, "text_preview": reply_text[:50]},
        )

        # Get Selenium driver for DOM operations
        driver = await self.router._ensure_selenium()
        dom_used = False

        # Step 1: Click Comment button (DOM-first)
        comment_btn_success = False
        if use_dom_first and driver:
            try:
                # DOM selector: target post by index, then find its Comment button
                comment_btn_js = """
                const postIndex = arguments[0];
                const textBoxes = document.querySelectorAll('span[data-testid="expandable-text-box"]');
                if (textBoxes.length <= postIndex) {
                    return {
                        ok: false,
                        error: 'Post not found at index',
                        index: postIndex,
                        found: textBoxes.length
                    };
                }

                const postText = textBoxes[postIndex];
                postText.scrollIntoView({ behavior: 'smooth', block: 'center' });

                let postContainer = postText;
                for (let i = 0; i < 15; i++) {
                    postContainer = postContainer.parentElement;
                    if (!postContainer) break;
                    if (
                        postContainer.classList.contains('feed-shared-update-v2') ||
                        postContainer.getAttribute('data-urn') ||
                        postContainer.classList.contains('occludable-update')
                    ) {
                        break;
                    }
                }
                if (!postContainer) {
                    return { ok: false, error: 'Post container not found', index: postIndex };
                }

                const commentSelectors = [
                    'button[aria-label*="Comment"]',
                    'button[aria-label*="comment"]',
                    'button[aria-label*="Reply"]',
                    'button[aria-label*="reply"]',
                ];
                for (const sel of commentSelectors) {
                    const btn = postContainer.querySelector(sel);
                    if (btn && btn.offsetParent !== null) {
                        btn.click();
                        return {
                            ok: true,
                            method: 'dom',
                            selector: sel,
                            index: postIndex
                        };
                    }
                }

                const spans = postContainer.querySelectorAll('span');
                for (const span of spans) {
                    const txt = (span.textContent || '').trim().toLowerCase();
                    if ((txt === 'comment' || txt === 'reply') && span.offsetParent !== null) {
                        const btn = span.closest('button');
                        if (btn) {
                            btn.click();
                            return {
                                ok: true,
                                method: 'dom',
                                selector: 'span:text',
                                index: postIndex
                            };
                        }
                    }
                }

                return { ok: false, error: 'Comment button not found in target post', index: postIndex };
                """
                result = driver.execute_script(comment_btn_js, post_index)
                comment_btn_success = result.get('ok', False)
                if comment_btn_success:
                    dom_used = True
                    self._log_dom_action(
                        "comment_btn_click",
                        {
                            "method": "dom",
                            "success": True,
                            "post_index": result.get("index", post_index),
                            "selector": result.get("selector", ""),
                        },
                    )
                    logger.info(
                        "[LINKEDIN] Comment button clicked via DOM (index=%s, selector=%s)",
                        result.get("index", post_index),
                        result.get("selector", ""),
                    )
            except Exception as e:
                logger.debug(f"[LINKEDIN] DOM comment button failed: {e}")

        # Fallback to vision
        if not comment_btn_success:
            comment_btn = await self.router.execute(
                'click_by_description',
                {'description': 'Comment button on the post'},
                driver=DriverType.VISION,
            )
            comment_btn_success = comment_btn.success
            self._log_dom_action(
                "comment_btn_click",
                {"method": "vision", "success": comment_btn_success, "post_index": post_index},
            )
            if not comment_btn_success:
                return LinkedInActionResult(
                    success=False,
                    action="reply_to_post",
                    post_id=post_id,
                    error="Could not find comment button",
                    details={"dom_attempted": use_dom_first},
                )

        await asyncio.sleep(0.5)

        # Step 2: Focus comment input (DOM-first)
        input_success = False
        if use_dom_first and driver:
            try:
                # DOM selector: prefer comment box scoped to target post index
                input_js = """
                const postIndex = arguments[0];
                const textBoxes = document.querySelectorAll('span[data-testid="expandable-text-box"]');
                let postContainer = null;
                if (textBoxes.length > postIndex) {
                    let node = textBoxes[postIndex];
                    for (let i = 0; i < 15; i++) {
                        node = node.parentElement;
                        if (!node) break;
                        if (
                            node.classList.contains('feed-shared-update-v2') ||
                            node.getAttribute('data-urn') ||
                            node.classList.contains('occludable-update')
                        ) {
                            postContainer = node;
                            break;
                        }
                    }
                }

                const roots = [];
                if (postContainer) roots.push(postContainer);
                roots.push(document);

                for (const root of roots) {
                    const inputHost = root.querySelector('div[componentkey^="commentBox-"]');
                    if (inputHost) {
                        const editable =
                            inputHost.querySelector('[contenteditable="true"]') ||
                            inputHost.querySelector('textarea') ||
                            inputHost.querySelector('input');
                        if (editable && editable.offsetParent !== null) {
                            editable.focus();
                            editable.click();
                            return { ok: true, method: 'componentkey', tag: editable.tagName };
                        }
                    }

                    const editables = root.querySelectorAll('[contenteditable="true"], textarea, input');
                    for (const el of editables) {
                        if (el.offsetParent !== null && el.closest('[componentkey^="commentBox-"]')) {
                            el.focus();
                            el.click();
                            return { ok: true, method: 'contenteditable', tag: el.tagName };
                        }
                    }
                }
                return { ok: false, error: 'Comment input not found via DOM' };
                """
                result = driver.execute_script(input_js, post_index)
                input_success = result.get('ok', False)
                if input_success:
                    dom_used = True
                    self._log_dom_action("comment_input_focus", {"method": "dom", "tag": result.get('tag')})
                    logger.info(f"[LINKEDIN] Comment input focused via DOM ({result.get('method')})")
            except Exception as e:
                logger.debug(f"[LINKEDIN] DOM comment input failed: {e}")

        # Fallback to vision
        if not input_success:
            input_click = await self.router.execute(
                'click_by_description',
                {'description': 'Comment text input field or "Add a comment" placeholder'},
                driver=DriverType.VISION,
            )
            input_success = input_click.success
            self._log_dom_action(
                "comment_input_focus",
                {"method": "vision", "success": input_success, "post_index": post_index},
            )
            if not input_success:
                return LinkedInActionResult(
                    success=False,
                    action="reply_to_post",
                    post_id=post_id,
                    error="Could not find comment input",
                    details={"dom_attempted": use_dom_first, "dom_used": dom_used},
                )

        await asyncio.sleep(0.3)

        # Step 3: Type reply (DOM with human behavior)
        type_success = False
        if driver:
            try:
                # Type with human-like delays using DOM
                type_js = """
                const text = arguments[0];
                const active = document.activeElement;
                if (!active) return { ok: false, error: 'No active element' };

                // Clear existing content
                if (active.isContentEditable) {
                    active.textContent = '';
                } else if (active.tagName === 'TEXTAREA' || active.tagName === 'INPUT') {
                    active.value = '';
                }

                // Insert text (could add character-by-character with delays in a real impl)
                if (active.isContentEditable) {
                    active.textContent = text;
                    active.dispatchEvent(new Event('input', { bubbles: true }));
                } else {
                    active.value = text;
                    active.dispatchEvent(new Event('input', { bubbles: true }));
                    active.dispatchEvent(new Event('change', { bubbles: true }));
                }

                return { ok: true, length: text.length, tag: active.tagName };
                """
                result = driver.execute_script(type_js, reply_text)
                type_success = result.get('ok', False)
                if type_success:
                    self._log_dom_action("comment_type", {"method": "dom", "length": len(reply_text)})
                    logger.info(f"[LINKEDIN] Typed {len(reply_text)} chars via DOM")
            except Exception as e:
                logger.debug(f"[LINKEDIN] DOM typing failed: {e}")

        # Fallback to vision typing
        if not type_success:
            type_result = await self.router.execute(
                'click_by_description',
                {
                    'description': 'comment input field',
                    'text': reply_text,
                    'slow_type': True,
                },
                driver=DriverType.VISION,
            )
            type_success = type_result.success
            self._log_dom_action(
                "comment_type",
                {"method": "vision", "success": type_success, "post_index": post_index},
            )

        await asyncio.sleep(0.5)

        # Step 4: Submit comment (DOM-first)
        submit_success = False
        if driver:
            try:
                # Find and click Post/Submit button
                submit_js = """
                const postIndex = arguments[0];
                const textBoxes = document.querySelectorAll('span[data-testid="expandable-text-box"]');
                let postContainer = null;
                if (textBoxes.length > postIndex) {
                    let node = textBoxes[postIndex];
                    for (let i = 0; i < 15; i++) {
                        node = node.parentElement;
                        if (!node) break;
                        if (
                            node.classList.contains('feed-shared-update-v2') ||
                            node.getAttribute('data-urn') ||
                            node.classList.contains('occludable-update')
                        ) {
                            postContainer = node;
                            break;
                        }
                    }
                }

                const roots = [];
                if (postContainer) roots.push(postContainer);
                roots.push(document);

                for (const root of roots) {
                    const btns = root.querySelectorAll('button');
                    for (const btn of btns) {
                        const text = btn.textContent.trim().toLowerCase();
                        if (
                            (text === 'post' || text === 'comment' || text === 'reply') &&
                            btn.offsetParent !== null &&
                            !btn.disabled
                        ) {
                            btn.click();
                            return { ok: true, method: 'button', text: btn.textContent.trim() };
                        }
                    }

                    const spans = root.querySelectorAll('button span');
                    for (const span of spans) {
                        const text = span.textContent.trim().toLowerCase();
                        if (
                            (text === 'post' || text === 'comment' || text === 'reply') &&
                            span.offsetParent !== null
                        ) {
                            span.closest('button')?.click();
                            return { ok: true, method: 'span_in_button', text: span.textContent.trim() };
                        }
                    }
                }
                return { ok: false, error: 'Submit button not found' };
                """
                result = driver.execute_script(submit_js, post_index)
                submit_success = result.get('ok', False)
                if submit_success:
                    self._log_dom_action("comment_submit", {"method": "dom", "button": result.get('text')})
                    logger.info(f"[LINKEDIN] Comment submitted via DOM ({result.get('text')})")
            except Exception as e:
                logger.debug(f"[LINKEDIN] DOM submit failed: {e}")

        # Fallback to vision
        if not submit_success:
            submit_result = await self.router.execute(
                'click_by_description',
                {'description': 'Post comment button or send button'},
                driver=DriverType.VISION,
            )
            submit_success = submit_result.success
            self._log_dom_action(
                "comment_submit",
                {"method": "vision", "success": submit_success, "post_index": post_index},
            )

        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        if submit_success:
            self._session_stats['comments_made'] += 1
            self._session_stats['posts_engaged'] += 1

        self._log_dom_action("reply_complete", {
            "success": submit_success,
            "dom_used": dom_used,
            "post_index": post_index,
            "duration_ms": duration_ms,
        })

        return LinkedInActionResult(
            success=submit_success,
            action="reply_to_post",
            post_id=post_id,
            engagements=1 if submit_success else 0,
            error=None if submit_success else "Submit failed",
            duration_ms=duration_ms,
            details={
                "dom_used": dom_used,
                "use_dom_first": use_dom_first,
                "post_index": post_index,
            },
        )

    async def engage_post(
        self,
        post_index: int = 0,
        mode: str = "like_reply",
        reply_text: Optional[str] = None,
        as_page: Optional[str] = None,
    ) -> LinkedInActionResult:
        """
        Engage with a LinkedIn post using one of 3 modes.

        Decision Flow (per 012):
        1. First determine IF should engage (caller's responsibility)
        2. Then select mode from 3 options:
           - "like" = Like only
           - "reply" = Reply only
           - "like_reply" = Like + Reply (both)

        Execution Order:
        - SWITCH ACCOUNT FIRST (proactive - select page before engaging)
        - Reply (if applicable)
        - Like AFTER (if applicable)

        Args:
            post_index: Which post to engage (0 = first visible)
            mode: Engagement mode - "like", "reply", or "like_reply"
            reply_text: Comment text (required for "reply" and "like_reply" modes)
            as_page: Page to switch to BEFORE engaging (e.g., "foundups")

        Returns:
            LinkedInActionResult
        """
        start_time = datetime.now()
        post_id = f"index_{post_index}"

        valid_modes = ["like", "reply", "like_reply"]
        if mode not in valid_modes:
            return LinkedInActionResult(
                success=False,
                action="engage_post",
                error=f"Invalid mode. Use: {valid_modes}",
            )

        if mode in ["reply", "like_reply"] and not reply_text:
            return LinkedInActionResult(
                success=False,
                action="engage_post",
                error="reply_text required for reply/like_reply modes",
            )

        logger.info(f"[LINKEDIN] Engage mode={mode} post_index={post_index} as_page={as_page}")

        reply_success = False
        like_success = False
        account_switched = False

        # Step 1: SWITCH ACCOUNT FIRST (proactive)
        if as_page:
            account_switched = await self._select_actor_for_reaction(as_page)
            if account_switched:
                logger.info(f"[LINKEDIN] Switched to {as_page} account")

        # Step 2: Reply (if mode includes reply)
        if mode in ["reply", "like_reply"]:
            reply_result = await self.reply_to_post(
                post_id,
                reply_text,
                post_index=post_index,
            )
            reply_success = reply_result.success

        # Step 3: Like AFTER (if mode includes like)
        if mode in ["like", "like_reply"]:
            like_result = await self.like_post(post_id, post_index=post_index)
            like_success = like_result.success

        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return LinkedInActionResult(
            success=reply_success or like_success,
            action=f"engage_{mode}",
            post_id=post_id,
            engagements=(1 if reply_success else 0) + (1 if like_success else 0),
            details={
                "mode": mode,
                "reply_success": reply_success,
                "like_success": like_success,
                "as_page": as_page,
                "account_switched": account_switched,
            },
            duration_ms=duration_ms,
        )

    async def like_and_reply(
        self,
        post_id: str,
        reply_text: str,
        post_index: int = 0,
        as_page: Optional[str] = None,
    ) -> LinkedInActionResult:
        """
        Reply and like a post in one session.

        IMPORTANT: Comment FIRST, then Like (correct engagement order).

        Args:
            post_id: Post identifier
            reply_text: Comment text
            post_index: Which post to engage (0 = first visible)
            as_page: Page name to like as (e.g., "foundups") - uses actor selection

        Returns:
            LinkedInActionResult with both outcomes
        """
        logger.info(f"[LINKEDIN] Reply then like: {post_id[:20] if post_id else f'index_{post_index}'}")

        # Step 1: Reply FIRST (correct order per 012)
        reply_result = await self.reply_to_post(
            post_id,
            reply_text,
            post_index=post_index,
        )

        # Step 2: Like AFTER posting
        like_result = await self.like_post(post_id, post_index=post_index)

        # Step 3: Open actor selection AT END (012 manually selects for next engagement)
        if as_page:
            await self._select_actor_for_reaction(as_page)

        return LinkedInActionResult(
            success=like_result.success or reply_result.success,
            action="reply_and_like",
            post_id=post_id,
            engagements=2 if (like_result.success and reply_result.success) else 1 if reply_result.success else 0,
            details={
                "reply_success": reply_result.success,
                "like_success": like_result.success,
                "as_page": as_page,
            },
            duration_ms=like_result.duration_ms + reply_result.duration_ms,
        )

    async def _select_actor_for_reaction(self, page_name: str) -> bool:
        """
        Select which page/profile to react as (actor selection).

        LinkedIn allows liking as personal profile or managed company pages.
        User must manually select from the dropdown that opens.

        DOM Selector: aria-label="Open actor selection screen"

        Args:
            page_name: Name of page to select (e.g., "foundups")

        Returns:
            True if dropdown was opened (user selects manually), False otherwise
        """
        driver = await self.router._ensure_selenium()
        if not driver:
            return False

        try:
            # Find and click actor selection dropdown
            result = driver.execute_script("""
                // Find actor selection dropdown near first post
                const dropdowns = document.querySelectorAll('[aria-label="Open actor selection screen"]');
                if (dropdowns.length === 0) return { found: false, error: 'Actor dropdown not found' };

                // Click the first visible one
                for (const dropdown of dropdowns) {
                    if (dropdown.offsetParent !== null) {
                        dropdown.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        dropdown.click();
                        return { found: true, clicked: true };
                    }
                }

                return { found: false, error: 'No visible dropdown' };
            """)

            if result.get('clicked'):
                logger.info(f"[LINKEDIN] Actor dropdown opened - select '{page_name}' manually")
                # Wait for user to select
                await asyncio.sleep(2)
                return True

            logger.info(f"[LINKEDIN] Actor dropdown not found - proceeding with default")
            return False

        except Exception as e:
            logger.warning(f"[LINKEDIN] Actor selection failed: {e}")
            return False

    async def run_engagement_session(
        self,
        duration_minutes: int = 15,
        max_engagements: int = 10,
        use_dom_iterator: bool = True,
    ) -> LinkedInActionResult:
        """
        Run an autonomous engagement session.

        0102 reads feed, identifies relevant posts, and engages intelligently.
        Uses DOM-first feed iterator for fast, reliable post processing.

        Args:
            duration_minutes: Max session duration
            max_engagements: Max posts to engage with
            use_dom_iterator: Use DOM-based iterator (default: True)

        Returns:
            LinkedInActionResult with session summary
        """
        logger.info(f"[LINKEDIN] Starting {duration_minutes}min engagement session (DOM={use_dom_iterator})")
        start_time = datetime.now()
        engagements = 0
        posts_processed = 0

        if use_dom_iterator:
            # DOM-first: Use feed iterator
            await self.refresh_feed()

            while engagements < max_engagements:
                # Check time limit
                elapsed = (datetime.now() - start_time).seconds / 60
                if elapsed >= duration_minutes:
                    logger.info("[LINKEDIN] Time limit reached")
                    break

                # Get next post
                post = await self.feed_iterator_next()
                if post is None:
                    logger.info("[LINKEDIN] No more posts in feed")
                    break

                posts_processed += 1

                # Skip reposts
                if post.get('is_repost'):
                    continue

                # Only engage with worthy posts
                if not post.get('should_engage'):
                    continue

                post_id = f"post_{post.get('index', 0)}_{int(datetime.now().timestamp())}"
                reason = post.get('engagement_reason', 'none')
                logger.info(f"[LINKEDIN] Engaging with post ({reason}): {post.get('author')}")

                # Generate reply for relevant posts using the LinkedIn digital twin wardrobe
                reply_text = None
                if post.get('is_ai_post') or post.get('is_capital_post') or post.get('is_target_author'):
                    content = post.get('content', '')[:300]
                    author = post.get('author', 'Unknown')
                    reply_text = await self._generate_reply_for_post(content, author, reason)

                # Engage
                if reply_text:
                    result = await self.like_and_reply(post_id, reply_text)
                else:
                    result = await self.like_post(post_id, post_index=post.get('index', 0))

                if result.success:
                    engagements += 1
                    self._session_stats['posts_engaged'] += 1

                # Human-like delay between engagements
                import random
                delay = random.uniform(3.0, 8.0)
                await asyncio.sleep(delay)

        else:
            # Legacy: Vision-based read_feed
            posts = await self.read_feed(max_posts=max_engagements * 2)
            relevant_posts = [p for p in posts if p.is_relevant]
            posts_processed = len(posts)

            logger.info(f"[LINKEDIN] Found {len(relevant_posts)} relevant posts (vision)")

            for post in relevant_posts[:max_engagements]:
                elapsed = (datetime.now() - start_time).seconds / 60
                if elapsed >= duration_minutes:
                    logger.info("[LINKEDIN] Time limit reached")
                    break

                if post.suggested_reply:
                    result = await self.like_and_reply(post.post_id, post.suggested_reply)
                else:
                    result = await self.like_post(post.post_id)

                if result.success:
                    engagements += 1

                await asyncio.sleep(5 + (engagements % 3) * 2)

        elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return LinkedInActionResult(
            success=engagements > 0,
            action="engagement_session",
            posts_read=posts_processed,
            engagements=engagements,
            duration_ms=elapsed_ms,
            details={
                "use_dom_iterator": use_dom_iterator,
                "session_stats": self._session_stats.copy(),
            },
        )

    async def _generate_reply_for_post(
        self,
        content: str,
        author: str,
        engagement_reason: str,
    ) -> Optional[str]:
        """
        Generate a LinkedIn reply using the digital twin wardrobe first.
        """
        draft = await self.draft_agentic_reply(
            post_context=content,
            author=author,
            engagement_reason=engagement_reason,
            agent_identity="0102",
        )
        if draft.get("success") and draft.get("reply_text"):
            return str(draft.get("reply_text"))
        return self._template_reply_for_reason(engagement_reason)

    def _template_reply_for_reason(self, reason: str) -> str:
        """Generate template reply based on engagement reason."""
        if reason == 'capital_pushback':
            templates = [
                "This is why foundups.com is building on different rails. From ROI capitalism to ROC - Return on Compute. When incentives align with communities instead of exits, the outcome changes. 🤔",
                "Perfect visual for why we need post-capitalism models. At foundups.com we're exploring how agents + BTC-native economics can flip this script. Thoughts? 🚀",
                "The shareholder primacy trap in one image. What if compute created value for communities, not just capital? That's what we're building at foundups.com 💡",
            ]
        elif reason == 'ai_topic':
            templates = [
                "The agent paradigm shift is real. At foundups.com we're building where AI agents earn and humans benefit. Post-capitalism starts with compute. 🤖",
                "This resonates with what we're seeing in autonomous systems. When agents become workers, the whole economic model shifts. foundups.com 🚀",
                "Great point! The AI capability curve keeps surprising us. Question is: who benefits? At foundups.com, it's the community, not VCs. 💡",
            ]
        else:
            templates = [
                "Great insights! This resonates with our work at foundups.com 🚀",
                "Valuable perspective. We're exploring similar ideas at foundups.com - where agents work and communities benefit.",
                "Thanks for sharing. The future is community-driven. foundups.com 💡",
            ]

        return random.choice(templates)

    def _assess_scam_risk(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """
        Heuristic risk assessment for suspicious setup-service posts.

        Goal:
        - Flag posts that market unofficial third-party setup help
        - Especially when coupled with shortened/external links and social proof
        """
        content = str(post.get("content", "")).strip()
        author = str(post.get("author", "")).strip()
        content_lower = content.lower()

        signals: List[str] = []
        score = 0
        matched: Dict[str, List[str]] = {}

        for bucket, patterns in self.SCAM_SIGNAL_PATTERNS.items():
            hits = [p for p in patterns if p in content_lower]
            if hits:
                matched[bucket] = hits
                signals.append(bucket)
                if bucket == "third_party_setup_offer":
                    score += 2
                elif bucket == "external_link":
                    score += 2
                elif bucket == "brand_impersonation_risk":
                    score += 1
                else:
                    score += 1

        if "openclaw" in content_lower and ("setup" in content_lower or "assistant" in content_lower):
            score += 1
            signals.append("openclaw_setup_pitch")

        is_candidate = score >= 4 and "third_party_setup_offer" in signals
        suggested_reply = None
        if is_candidate:
            top_signal = ", ".join(sorted(set(signals))[:3])
            suggested_reply = (
                "Potentially risky pattern here: third-party setup offer + external link. "
                "Please verify official OpenClaw/IronClaw channels before granting access. "
                "Avoid shortened links and unverified remote setup services."
            )
            if top_signal:
                suggested_reply += f" Risk signal: {top_signal}."

        return {
            "author": author,
            "content_preview": content[:280],
            "score": score,
            "signals": sorted(set(signals)),
            "matched": matched,
            "is_candidate": is_candidate,
            "suggested_reply": suggested_reply,
        }

    async def scan_feed_for_scam(
        self,
        max_posts: int = 10,
        min_score: int = 4,
    ) -> List[Dict[str, Any]]:
        """
        Scan visible LinkedIn feed posts for scam-like setup offers.

        Returns flagged post descriptors sorted by highest risk first.
        """
        logger.info(f"[LINKEDIN] Scam scan starting (max_posts={max_posts}, min_score={min_score})")
        posts = await self.iterate_feed(
            max_posts=max_posts,
            skip_reposts=True,
            engagement_filter=False,
        )

        flagged: List[Dict[str, Any]] = []
        for post in posts:
            assessment = self._assess_scam_risk(post)
            if assessment["score"] < min_score:
                continue
            if not assessment["is_candidate"]:
                continue
            flagged.append(
                {
                    "post_index": post.get("index", 0),
                    "post_id": f"index_{post.get('index', 0)}",
                    "author": post.get("author", ""),
                    "author_url": post.get("author_url", ""),
                    "content": post.get("content", ""),
                    "risk_score": assessment["score"],
                    "risk_signals": assessment["signals"],
                    "matched_patterns": assessment["matched"],
                    "suggested_reply": assessment["suggested_reply"],
                }
            )

        flagged.sort(key=lambda item: (-int(item.get("risk_score", 0)), int(item.get("post_index", 0))))
        self._log_dom_action(
            "scam_scan_complete",
            {"max_posts": max_posts, "flagged": len(flagged), "min_score": min_score},
        )
        logger.info(f"[LINKEDIN] Scam scan flagged {len(flagged)} posts")
        return flagged

    def get_session_stats(self) -> Dict[str, int]:
        """Get session statistics."""
        return self._session_stats.copy()

    async def run_digital_twin_flow(
        self,
        comment_text: str,
        repost_text: str,
        schedule_date: str,
        schedule_time: str,
        mentions: Optional[List[str]] = None,
        identity_cycle: Optional[List[str]] = None,
        dry_run: bool = False,
    ) -> LinkedInActionResult:
        """
        Execute the LinkedIn Digital Twin workflow (L0-L3).
        
        Skill: linkedin_comment_digital_twin.json
        
        Flow:
            L0: Context gate (validate post, AI gate)
            L1: Post comment with @mentions, UI-TARS verification
            L2: Identity cycle — switch accounts and like comment
            L3: Schedule repost with thoughts
        
        Args:
            comment_text: 012 Digital Twin comment text
            repost_text: Repost-with-thoughts text
            schedule_date: Scheduled date (calendar selection)
            schedule_time: Scheduled time (15-min increments)
            mentions: Mentions to insert (default: @foundups)
            identity_cycle: Identities to like comment
            dry_run: If True, validate without submitting
        
        Returns:
            LinkedInActionResult with layer results
        """
        logger.info("[LINKEDIN] Starting Digital Twin flow (L0-L3)")
        
        mentions = mentions or ["@foundups"]
        identity_cycle = identity_cycle or ["FOUNDUPS", "Move2Japan", "UnDaoDu", "EDUIT, Inc"]
        
        layer_results = {}
        start_time = datetime.now()
        
        # Import layer tests
        try:
            from modules.platform_integration.linkedin_agent.tests.test_layer0_context_gate import (
                test_layer0_selenium,
            )
            from modules.platform_integration.linkedin_agent.tests.test_layer1_comment import (
                test_layer1_selenium,
            )
            from modules.platform_integration.linkedin_agent.tests.test_layer2_identity_likes import (
                test_layer2_selenium,
            )
            from modules.platform_integration.linkedin_agent.tests.test_layer3_schedule_repost import (
                test_layer3_selenium,
            )
        except ImportError as e:
            logger.error(f"[LINKEDIN] Digital Twin tests not available: {e}")
            return LinkedInActionResult(
                success=False,
                action="digital_twin_flow",
                error=f"Layer tests unavailable: {e}",
            )
        
        # L0: Context Gate
        logger.info("[LINKEDIN] L0: Context Gate")
        l0_result = test_layer0_selenium()
        layer_results["L0"] = l0_result
        
        if not l0_result.get("success"):
            return LinkedInActionResult(
                success=False,
                action="digital_twin_flow",
                error=f"L0 failed: {l0_result.get('error')}",
                details={"layer_results": layer_results},
            )
        
        ai_gate_passed = l0_result.get("ai_post", False)
        if not ai_gate_passed:
            logger.info("[LINKEDIN] AI gate not passed — skipping engagement")
            return LinkedInActionResult(
                success=True,
                action="digital_twin_flow",
                details={"layer_results": layer_results, "skipped": "AI gate not passed"},
            )
        
        # L1: Comment
        logger.info("[LINKEDIN] L1: Comment")
        l1_result = test_layer1_selenium(
            dry_run=dry_run,
            ai_gate_passed=ai_gate_passed,
            comment_text=comment_text,
            mentions=mentions,
        )
        layer_results["L1"] = l1_result
        
        if not l1_result.get("success"):
            return LinkedInActionResult(
                success=False,
                action="digital_twin_flow",
                error=f"L1 failed: {l1_result.get('error')}",
                details={"layer_results": layer_results},
            )
        
        # L2: Identity Likes
        logger.info("[LINKEDIN] L2: Identity Likes")
        l2_result = test_layer2_selenium(dry_run=dry_run)
        layer_results["L2"] = l2_result
        
        # L3: Schedule Repost
        logger.info("[LINKEDIN] L3: Schedule Repost")
        l3_result = test_layer3_selenium(
            repost_text=repost_text,
            schedule_date=schedule_date,
            schedule_time=schedule_time,
            dry_run=dry_run,
        )
        layer_results["L3"] = l3_result
        
        elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        all_success = all(
            r.get("success", False)
            for r in [l0_result, l1_result, l2_result, l3_result]
        )
        
        self._session_stats["posts_engaged"] += 1
        self._session_stats["comments_made"] += 1 if l1_result.get("success") else 0
        
        logger.info(f"[LINKEDIN] Digital Twin flow complete: {all_success}")
        
        return LinkedInActionResult(
            success=all_success,
            action="digital_twin_flow",
            engagements=1 if all_success else 0,
            duration_ms=elapsed_ms,
            details={"layer_results": layer_results},
        )

    def close(self) -> None:
        """Close router and release resources."""
        self.router.close()
        logger.info(f"[LINKEDIN] Closed. Stats: {self._session_stats}")


# Factory function
def create_linkedin_actions(profile: str = 'linkedin_foundups') -> LinkedInActions:
    """Create LinkedInActions instance."""
    return LinkedInActions(profile=profile)


# Test function
async def _test_linkedin():
    """Test LinkedIn actions."""
    linkedin = LinkedInActions(profile='linkedin_foundups')
    
    # Test engagement session
    result = await linkedin.run_engagement_session(
        duration_minutes=5,
        max_engagements=3,
    )
    
    print(f"Result: {result.to_dict()}")
    
    linkedin.close()


if __name__ == "__main__":
    asyncio.run(_test_linkedin())


