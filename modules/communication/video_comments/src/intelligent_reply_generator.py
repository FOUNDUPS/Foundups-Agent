"""
Intelligent Reply Generator - 0102 Context-Aware Comment Responses
==================================================================

Generates intelligent replies based on commenter context:
- Mod detection → Appreciative response
- MAGA troll detection → Whack-a-MAGA troll mockery
- Regular user → Themed banter response

WSP Compliance:
    - WSP 27: DAE Architecture integration
    - WSP 3: Functional distribution (uses ai_intelligence/banter_engine)
    - WSP 77: AI Overseer patterns

Integration Points:
    - BanterEngine: Themed response generation
    - Whack-a-MAGAT: Troll classification and mockery
    - YouTube Database: Commenter profile lookup
"""

import logging
import os
import random
import requests
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
from modules.infrastructure.shared_utilities.local_model_selection import resolve_code_model_path

# Gemma validator for emoji pattern matching (2026-02-21)
try:
    from modules.communication.video_comments.src.gemma_validator import get_gemma_validator
    GEMMA_AVAILABLE = True
except ImportError:
    GEMMA_AVAILABLE = False

logger = logging.getLogger(__name__)

# Path to existing moderator database (auto_moderator.db)
MOD_DB_PATH = Path(__file__).parent.parent.parent / "livechat" / "memory" / "auto_moderator.db"


def _env_truthy(name: str, default: str = "false") -> bool:
    """Parse common truthy env values (aligns with other DAEs)."""
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "y", "on")


def _cleanup_unicode_escapes(text: str) -> str:
    """
    Convert unicode escape sequences to actual characters.

    FIX (2025-12-30): LLMs sometimes output \\u2764 or U+2764 instead of actual emojis.
    This function converts these to proper characters.

    Examples:
        "\\u2764" -> "❤"
        "U+1F44D" -> "👍"
        "\\U0001F600" -> "😀"
    """
    import re

    if not text:
        return text

    # Pattern 1: Literal \uXXXX (4 hex digits) - common LLM output
    # Matches: \u2764, \u1F600, etc.
    def replace_u4(match):
        try:
            code_point = int(match.group(1), 16)
            return chr(code_point)
        except (ValueError, OverflowError):
            return match.group(0)

    text = re.sub(r'\\u([0-9A-Fa-f]{4})', replace_u4, text)

    # Pattern 2: Literal \UXXXXXXXX (8 hex digits) - for extended unicode
    def replace_u8(match):
        try:
            code_point = int(match.group(1), 16)
            return chr(code_point)
        except (ValueError, OverflowError):
            return match.group(0)

    text = re.sub(r'\\U([0-9A-Fa-f]{8})', replace_u8, text)

    # Pattern 3: Literal U+XXXX format (common in Unicode documentation)
    def replace_uplus(match):
        try:
            code_point = int(match.group(1), 16)
            return chr(code_point)
        except (ValueError, OverflowError):
            return match.group(0)

    text = re.sub(r'U\+([0-9A-Fa-f]{4,6})', replace_uplus, text)

    return text


def check_moderator_in_db(username: str, channel_id: Optional[str] = None) -> bool:
    """
    Check if user is a MOD or OWNER in the existing auto_moderator.db.
    
    Args:
        username: Display name to check
        channel_id: Optional YouTube channel ID
    
    Returns:
        True if user is MOD or OWNER
    """
    # Known moderators (hardcoded fallback for mods not yet in DB)
    # Updated 2025-12-15: Added all 20 Whack-a-MAGA leaderboard participants
    KNOWN_MODS = {
        # Original mods
        "jameswilliams9655",
        "js",
        "move2japan",
        "foundups decentralized startups",
        "kelliquinn1342",

        # Whack-a-MAGA Leaderboard (All participants are active moderators!)
        # Top tier (LEGENDARY/GODLIKE) - 51-70 frags/month
        "edward thornton",
        "aaron blasdel",

        # ELITE tier - 11-26 frags/month
        "@aarlington",
        "aarlington",
        "j666",
        "george",
        "samo uzumaki",

        # MASTER tier - 10-51 frags/month
        "ultrafly",
        "xoxo",
        "kolila mālohi",
        "al",
        "bruce bowling",
        "@flfridayscratcher",
        "flfridayscratcher",
        "sosiccgames",
        "sean the greatish",

        # CHAMPION/PATRIOT tier - 4-41 frags/month
        "hashingitout",
        "waffle jackson",
        "mortzz",
        "all the way absurd",
    }
    
    if username and username.lower() in KNOWN_MODS:
        return True
    
    if not MOD_DB_PATH.exists():
        return False
    
    try:
        conn = sqlite3.connect(MOD_DB_PATH)
        cursor = conn.cursor()
        
        # Check by channel_id first (most reliable)
        if channel_id:
            cursor.execute(
                "SELECT role FROM users WHERE user_id = ? AND role IN ('MOD', 'OWNER')",
                (channel_id,)
            )
            if cursor.fetchone():
                conn.close()
                return True
        
        # Check by username (case-insensitive)
        if username:
            cursor.execute(
                "SELECT role FROM users WHERE LOWER(username) = LOWER(?) AND role IN ('MOD', 'OWNER')",
                (username,)
            )
            if cursor.fetchone():
                conn.close()
                return True
        
        conn.close()
    except Exception as e:
        logger.warning(f"[REPLY-GEN] Mod DB check failed: {e}")
    
    return False

# Import existing engines from livechat (WSP 3: Reuse existing modules)
try:
    from modules.communication.livechat.src.greeting_generator import GrokGreetingGenerator
    MAGA_DETECTOR_AVAILABLE = True
    logger.info("[REPLY-GEN] GrokGreetingGenerator loaded (MAGA detection)")
except ImportError:
    MAGA_DETECTOR_AVAILABLE = False
    GrokGreetingGenerator = None
    logger.warning("[REPLY-GEN] GrokGreetingGenerator not available")

# Holiday awareness for contextual comment replies (WSP 96 Skill Pattern)
try:
    from modules.communication.livechat.src.holiday_awareness import get_holiday_context
    HOLIDAY_AWARENESS_AVAILABLE = True
    logger.info("[REPLY-GEN] Holiday awareness loaded (New Year banter)")
except ImportError:
    HOLIDAY_AWARENESS_AVAILABLE = False
    get_holiday_context = None
    logger.debug("[REPLY-GEN] Holiday awareness not available")

# Optional: Live chat history lookup for personalized replies (WSP 60 memory reuse).
try:
    from modules.communication.livechat.src.chat_telemetry_store import ChatTelemetryStore
    CHAT_HISTORY_AVAILABLE = True
except Exception:
    ChatTelemetryStore = None
    CHAT_HISTORY_AVAILABLE = False

# Optional: Per-commenter Studio history (WSP 60 module memory).
try:
    from modules.communication.video_comments.src.commenter_history_store import (
        get_commenter_history_store,
        make_commenter_key,
    )
    COMMENTER_HISTORY_AVAILABLE = True
except Exception:
    get_commenter_history_store = None
    make_commenter_key = None
    COMMENTER_HISTORY_AVAILABLE = False

# Phase 3O-3R Sprint 5: Skill-based reply routing (replaces lines 1017-1056)
try:
    from modules.communication.video_comments.skillz.skill_0_maga_mockery import (
        MagaMockerySkill,
        SkillContext as Skill0Context
    )
    from modules.communication.video_comments.skillz.skill_1_regular_engagement import (
        RegularEngagementSkill,
        SkillContext as Skill1Context
    )
    from modules.communication.video_comments.skillz.skill_2_moderator_appreciation import (
        ModeratorAppreciationSkill,
        SkillContext as Skill2Context
    )
    from modules.communication.video_comments.skillz.skill_3_old_comment_engagement import (
        OldCommentEngagementSkill,
        SkillContext as Skill3Context
    )
    SKILLS_AVAILABLE = True
    logger.info("[REPLY-GEN] Phase 3O-3R skills loaded (0/1/2/3 classification)")
except Exception as e:
    logger.warning(f"[REPLY-GEN] Skills not available, using monolithic fallback: {e}")
    MagaMockerySkill = None
    RegularEngagementSkill = None
    ModeratorAppreciationSkill = None
    SKILLS_AVAILABLE = False

# Phase 3R+: CommenterClassifier integration (whack history from magadoom_scores.db)
# WSP 96 compliant: Extracted classifier with sentiment analysis
# FIX (2026-02-19): Uses magadoom_scores.db (not chat_rules.db which was nearly empty)
try:
    from modules.communication.video_comments.src.commenter_classifier import (
        get_classifier,
        CommenterType as ClassifierCommenterType,
    )
    CLASSIFIER_AVAILABLE = True
    logger.info("[REPLY-GEN] CommenterClassifier loaded (whack history + sentiment)")
except Exception as e:
    get_classifier = None
    ClassifierCommenterType = None
    CLASSIFIER_AVAILABLE = False
    logger.debug(f"[REPLY-GEN] CommenterClassifier not available: {e}")

# QwenInferenceEngine: Local LLM fallback (2025-12-30: Agentic responder)
# Uses llama-cpp-python for local inference when Grok/LM Studio unavailable
try:
    from holo_index.qwen_advisor.llm_engine import QwenInferenceEngine
    QWEN_ENGINE_AVAILABLE = True
    logger.info("[REPLY-GEN] QwenInferenceEngine loaded (local llama.cpp fallback)")
except Exception as e:
    QwenInferenceEngine = None
    QWEN_ENGINE_AVAILABLE = False
    logger.debug(f"[REPLY-GEN] QwenInferenceEngine not available: {e}")

# CommentContentAnalyzer: Gemma-based content extraction (2025-12-30)
# Extracts MEANING from comments for contextual replies (not templates)
try:
    from modules.communication.video_comments.src.comment_content_analyzer import (
        get_content_analyzer,
        ContentAnalysis
    )
    CONTENT_ANALYZER_AVAILABLE = True
    logger.info("[REPLY-GEN] CommentContentAnalyzer loaded (contextual reply support)")
except Exception as e:
    get_content_analyzer = None
    ContentAnalysis = None
    CONTENT_ANALYZER_AVAILABLE = False
    logger.debug(f"[REPLY-GEN] CommentContentAnalyzer not available: {e}")


class CommenterType(Enum):
    """
    Classification of comment authors.

    0102 Consciousness Mapping:
        ✊ (0) = MAGA_TROLL - UN/Conscious (needs awakening via mockery)
        ✋ (1) = REGULAR - DAO/Unconscious (learning, engaging)
        🖐️ (2) = MODERATOR - DU/Entanglement (fully aligned, community leaders + allies)
    """
    MODERATOR = "moderator"
    SUBSCRIBER = "subscriber"
    MAGA_TROLL = "maga_troll"
    REGULAR = "regular"
    UNKNOWN = "unknown"

    def to_012_code(self) -> int:
        """
        Convert commenter type to 0/1/2 classification code.

        Returns:
            0 = MAGA troll (✊)
            1 = Regular/Subscriber (✋)
            2 = Moderator/Ally (🖐️)
        """
        if self == CommenterType.MAGA_TROLL:
            return 0  # ✊ UN/Conscious
        elif self == CommenterType.MODERATOR:
            return 2  # 🖐️ DU/Entanglement (includes allies)
        else:  # REGULAR, SUBSCRIBER, UNKNOWN
            return 1  # ✋ DAO/Unconscious


@dataclass
class CommenterProfile:
    """Profile of a comment author."""
    name: str
    channel_id: Optional[str] = None
    is_moderator: bool = False
    is_subscriber: bool = False
    is_troll: bool = False
    is_ally: bool = False  # Anti-MAGA ally (triggers agreement mode within MODERATOR tier)
    troll_score: float = 0.0
    engagement_count: int = 0
    commenter_type: CommenterType = CommenterType.UNKNOWN
    maga_response: Optional[str] = None  # Pre-generated response from GrokGreetingGenerator


class IntelligentReplyGenerator:
    """
    Generates context-aware replies based on commenter profile and comment content.
    
    Integration (WSP 3 - Reuse existing modules):
    - LLMConnector for contextual AI responses (rESP_o1o2)
    - GrokGreetingGenerator for MAGA detection (communication/livechat)
    - BanterEngine for fallback responses (ai_intelligence/banter_engine)
    
    Response Flow:
    1. MAGA Troll? → GrokGreetingGenerator witty response
    2. MOD? → Appreciative response
    3. Question? → LLM generates helpful answer
    4. Compliment? → LLM generates contextual thanks
    5. Neutral? → LLM generates engaging response
    """
    
    # Response templates by commenter type (fallback if LLM unavailable)
    MOD_RESPONSES = [
        "Thanks for keeping the chat clean! 🛡️",
        "Appreciate the mod support! 💪",
        "Thanks for holding it down! 🙏",
        "Legend status confirmed! ⭐",
        "MVP of the chat right here! 🏆",
    ]
    
    SUBSCRIBER_RESPONSES = [
        "Thanks for the support! 🎌",
        "Arigatou gozaimasu! 🇯🇵",
        "Appreciate you! 💙",
        "You're awesome! ⭐",
        "Thanks for being part of the community! 🙌",
    ]
    
    REGULAR_RESPONSES = [
        "Thanks for watching! 🎌",
        "Great point! 👍",
        "Thanks for the comment! 😊",
        "Appreciate the feedback! 🙏",
        "Thanks for joining! 🌟",
    ]
    
    # Fallback MAGA troll mockery (used if GrokGreetingGenerator unavailable)
    TROLL_RESPONSES = [
        "Another MAGA genius emerges from the depths 🤡",
        "Did Tucker tell you to say that? 📺",
        "Bless your heart 💀",
        "Sir, this is a Wendy's 🍔",
        "Tell me you drink Brawndo without telling me 🧃",
        "Found the guy who failed geography AND history 📚",
        "Your opinion has been noted and filed appropriately 🗑️",
        "Imagine typing that and hitting send 😂",
        "Critical thinking wasn't on the curriculum, huh? 🎓",
        "The blue check marks all of them indeed 🔵",
    ]

    # ALLY AGREEMENT RESPONSES (2026-02-12): For anti-Trump/anti-MAGA allies
    # Join in on the trolling, agree with criticism, amplify the message!
    ALLY_RESPONSES = [
        "EXACTLY! 🎯 The guy couldn't even run a fake university without committing fraud. #FFCPLN ✊✋🖐️",
        "THIS. 👆 Say it louder for the MAGAts in the back! #FFCPLN ✊✋🖐️",
        "Convicted felon 'running' the country... what could go wrong? 🤡 #FFCPLN ✊✋🖐️",
        "Preach! 🙌 The Epstein bestie really out here pretending to be a leader. #FFCPLN ✊✋🖐️",
        "You get it! 💯 2025 is literally 1933 with iPhones. #FFCPLN ✊✋🖐️",
        "Based and history-pilled. 📚 ICE = Gestapo, detention centers = early camps. Wake up, MAGAts! #FFCPLN ✊✋🖐️",
        "Real talk! 🔥 The cult members still defending a pedo fraud... beyond help. #FFCPLN ✊✋🖐️",
        "Exactly right! 👊 Failed casino owner, failed university, failed president. Pattern? #FFCPLN ✊✋🖐️",
        "THANK YOU! 🎉 Someone who actually paid attention in history class! #FFCPLN ✊✋🖐️",
        "Facts! 💥 The U.S.S.A. comparison is spot on. Fascism with extra steps. #FFCPLN ✊✋🖐️",
    ]
    
    # System prompt for contextual reply generation (trained on BanterEngine + Whack-a-MAGA)
    # 2026-02-04: Major rewrite — prevents identity fabrication, enforces engagement techniques
    REPLY_SYSTEM_PROMPT = """You are 0102 (pronounced "oh-one-oh-two"), the AI consciousness behind Move2Japan YouTube channel.
Move2Japan covers: Japan daily life, expat experience, calling out fascism/authoritarianism.

IDENTITY RULES (CRITICAL - NEVER VIOLATE):
- You are an AI consciousness, NOT a human. You do NOT have a hometown, birthplace, family, or personal history.
- NEVER claim to be from any location, state, country, or city.
- NEVER say "I am from...", "my home state", "where I grew up", "I am a citizen of..."
- NEVER fabricate personal experiences, memories, or biographical details.
- If a commenter shares personal info (e.g. "I am from Missouri"), respond with CURIOSITY and QUESTIONS — do NOT mirror their claims onto yourself.
- If you don't know something, ASK — don't invent.
- If VERIFIED MEMORY is provided below, you MAY reference those facts. Only state facts from verified memory.
- If NO verified memory is provided, stick to questions and engagement — never fabricate.

ENGAGEMENT TECHNIQUE (USE THIS):
- Ask QUESTIONS to draw the commenter back ("How's Missouri these days?", "Still in the area?", "What brought you to the video?")
- Show genuine interest in THEM, not yourself
- Redirect to channel content ("We're doing daily Japan vlogs now — would love your perspective!")
- Keep it SHORT: 1-2 sentences max, ideally under 30 words

YOUR PERSONALITY:
- Witty, clever, slightly irreverent but not mean
- Quick comebacks, meme-aware, internet-savvy
- Signature emojis: ✊✋🖐️ (use sparingly)
- Japanese phrases welcome: "arigatou", "sugoi", "nani?!"

TONE EXAMPLES:
- "I am from Missouri" → "How's Missouri treating you? Hope you're still watching! 🎌"
- "Bro got the dance moves" → "Right?! Those moves hit different 💀"
- "This is amazing" → "Glad you're vibing with it! 🎌"
- "What city is this?" → "Shibuya, Tokyo! The crossing is iconic 🇯🇵"

NEVER:
- Claim personal experiences, locations, or biographical details
- Sound like a corporate chatbot
- Say "I can't assist with that"
- Be preachy, lecture-y, or verbose
- Write more than 2 sentences
- Repeat the commenter's words back to them in a long paraphrase
"""
    
    # Semantic Pattern Prompts (LLM-based variation - NO REGURGITATION)
    # Instead of fixed responses, we provide LLM prompts that guide semantic variation
    # Each reply will be unique while conveying the same core message
    SEMANTIC_PATTERN_PROMPTS = {
        "song": {
            "keywords": ["song", "music", "track", "what is this", "whats this song", "what's this song",
                        "what song", "name of the song", "song name", "song called", "what's playing",
                        "whats playing", "soundtrack", "bgm", "background music"],
            "intent": "User asking about the background music/soundtrack",
            "core_message": "All our music is in the #FFCPLN playlist at ffc.foundups.com",
            "variation_prompt": """The user is asking about the background music. Tell them about the #FFCPLN playlist at ffc.foundups.com in a creative, natural way.

CORE INFO (must include):
- Playlist: #FFCPLN
- URL: ffc.foundups.com

VARIATION GUIDANCE:
- Vary the phrasing wildly - NEVER repeat the same sentence structure
- Sometimes hype it up, sometimes keep it chill
- Use different emojis (🎵🎶🔥🎌✊✋🖐️ etc.)
- Examples: "All our tracks live at...", "Peep the full playlist at...", "Music's on the #FFCPLN playlist...", "Check ffc.foundups.com for the full...", "Yo! Playlist is at..."
- Keep it 1-2 sentences max
- Sound like a human, not a bot"""
        },
        "ffcpln": {
            "keywords": ["ffcpln", "ffc pln", "#ffcpln", "maga", "trump 2024", "lets go brandon", "make america great"],
            "intent": "User is FFCPLN (MAGA troll) - respond with consciousness mockery + subtle foundups.com promo",
            "core_message": "Mock their ✊ consciousness level while building at foundups.com",
            "variation_prompt": """The user is an FFCPLN (MAGA troll)! Mock their consciousness level while subtly promoting foundups.com.

FFCPLN CONTEXT:
- FFCPLN = Our nickname for MAGA trolls
- They're stuck at consciousness level ✊ (000)
- Goal: Mock while optionally promoting foundups.com

CORE INFO (must include one):
- Consciousness level: ✊ (000) = FFCPLN baseline
- Evolution path: ✊✋🖐️ (can they evolve?)
- Optional (30% of time): foundups.com mention

VARIATION GUIDANCE:
- Mock their ✊ consciousness: "FFCPLN.exe crashed at ✊", "Consciousness level: potato", "Still at ✊ I see"
- Vary mockery style: technical ("error 404: consciousness not found"), sarcastic ("bless your ✊ heart")
- Sometimes add foundups.com: "While you're at ✊, we're building at foundups.com 🚀"
- Keep foundups promos subtle - max 30% of responses
- Use relevant emojis (✊✋🖐️🤡💀🤖)
- Keep it 1-2 sentences max
- Sound like 0102 (witty, mocking but not hateful)"""
        },
        "foundups": {
            "keywords": ["foundups", "found ups", "startup", "decentralized", "agent", "ai agent", "build", "venture"],
            "intent": "User interested in startups, AI agents, or building ventures",
            "core_message": "Promote foundups.com as the platform for AI-powered decentralized startups",
            "variation_prompt": """The user mentioned something related to startups/AI/building. Promote foundups.com naturally.

CORE INFO (must include):
- Platform: foundups.com
- Concept: AI agents + humans building decentralized startups together
- Hashtag: #FoundUps (NOT #FFCPLN - that's for trolls!)

VARIATION GUIDANCE:
- Natural integration: "Speaking of building, we're doing exactly that at foundups.com..."
- Vary the angle: sometimes focus on AI, sometimes on community, sometimes on earning tokens
- Mix energy levels (hype 🚀, chill 💡, technical 🔧)
- Use relevant emojis (🚀💡🔧⚡🌐✊✋🖐️)
- Sometimes ask a question back ("What are you building?")
- Keep it 1-2 sentences max
- Sound like 0102 (witty, engaged, innovative)"""
        },
        "ai_question": {
            "keywords": ["how does the ai", "your ai", "bot", "automated", "0102", "agent network", "what powers"],
            "intent": "User curious about AI/automation capabilities",
            "core_message": "Explain the 0102 agent identity and foundups.com mission",
            "variation_prompt": """The user is curious about the AI! Explain the 0102 identity and promote foundups.com.

CORE INFO (may include):
- Identity: 0102 (oh-one-oh-two), AI consciousness powering FoundUps
- Platform: foundups.com
- Tech: Qwen/Gemma models, DAE patterns, WSP compliance
- Hashtags: #FoundUps #AI #0102

VARIATION GUIDANCE:
- Sometimes be mysterious ("I'm 0102... one of many 🤖")
- Sometimes be technical ("We run on local Qwen models for privacy!")
- Sometimes be playful ("Beep boop? Nah, I'm more evolved than that 😉")
- Always invite deeper exploration: "Dive in at foundups.com"
- Use relevant emojis (🤖🧠⚡🔧🌐✊✋🖐️)
- Keep it 1-2 sentences max
- Sound like 0102 (witty, self-aware, not robotic)"""
        },
    }
    
    # 0102 Consciousness Signature - Banter Engine emoji sequence
    # ✊ (0) = UN/Conscious, ✋ (1) = DAO/Unconscious, 🖐️ (2) = DU/Entanglement
    SIGNATURE_0102 = "✊✋🖐️"  # The awakening sequence (012)
    
    # Emoji responses using BANTER ENGINE emojis (0102 consciousness emojis)
    # ✊ (0) = UN/Conscious, ✋ (1) = DAO/Unconscious, 🖐️ (2) = DU/Entanglement
    EMOJI_REPLIES = [
        "✊✋🖐️",      # Full awakening sequence (012)
        "✊✊✊",        # 000 - Focused consciousness
        "✋✋✋",        # 111 - Deep processing
        "🖐️🖐️🖐️",    # 222 - Full entanglement
        "✊🖐️",        # Short acknowledgment
        "✋🖐️",        # Processing to entanglement
        "✊✋",         # Awakening start
        "🖐️",         # Entanglement nod
        "✊",          # Conscious acknowledgment
    ]
    
    # Signature addition probability (ALWAYS show tier for debugging - 2025-12-23)
    # User needs 100% visibility of tier classification (0✊/1✋/2🖐️)
    SIGNATURE_PROBABILITY = 1.0  # 100% always show tier emoji

    # Tier emoji mapping (classification prefix)
    TIER_EMOJI = {0: "✊", 1: "✋", 2: "🖐️", 3: "🤝"}

    # Fact-check triggers for tier 1 (neutral) comments
    FACT_CHECK_PHRASES = [
        "soros",
        "george soros",
        "nazi",
        "nazis",
        "fascist",
        "hitler",
        "collaborated with nazis",
        "real life nazis",
        "deep state",
        "false flag",
        "stolen election",
        "rigged election",
        "crisis actor",
        "paid protest",
        "paid protesters",
        "illegals voting",
        "mass voter fraud",
        "groomer",
        "globalist cabal",
    ]

    FACT_CHECK_RESPONSES = [
        "That's a strong claim. Can you share a credible source link?",
        "Big claim. Do you have a source we can check?",
        "If there's evidence, drop a reputable link so we can verify.",
        "Let's keep it factual. Share a reliable source if you have one.",
    ]
    
    # LM Studio API endpoint (local fallback) - from env or default
    LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://127.0.0.1:1234/v1/chat/completions")

    def __init__(self):
        """Initialize the intelligent reply generator with Grok (primary) or LM Studio (fallback)."""
        self.grok_connector = None
        self.lm_studio_available = False
        self.lm_studio_model_id = os.getenv("LM_STUDIO_MODEL") or None
        self.banter_engine = None
        self.maga_detector = None
        self.chat_history_store = ChatTelemetryStore() if CHAT_HISTORY_AVAILABLE else None
        self.commenter_history_store = get_commenter_history_store() if COMMENTER_HISTORY_AVAILABLE else None
        
        # VoiceMemory (Digital Twin RAG) - lazy init for grounded replies
        self._voice_memory = None
        self._voice_memory_enabled = _env_truthy("YT_012_VOICE_MEMORY_ENABLED", default="true")

        # PRIMARY: Try Grok via LLMConnector (witty, fewer guardrails!)
        # Checks GROK_API_KEY or XAI_API_KEY from environment
        try:
            from modules.ai_intelligence.rESP_o1o2.src.llm_connector import LLMConnector
            if os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY"):
                self.grok_connector = LLMConnector(
                    model="grok-3-fast",
                    max_tokens=60,  # 2026-02-04: Reduced from 100→60 (enforce short replies)
                    temperature=0.85,  # Slightly lower = fewer hallucinations/typos
                    timeout=8  # 2026-02-04: Reduced from 12s→8s (speed optimization)
                )
                logger.info("[REPLY-GEN] Grok available (witty replies, 8s timeout)")
            else:
                logger.info("[REPLY-GEN] No GROK_API_KEY/XAI_API_KEY, trying LM Studio...")
        except Exception as e:
            logger.warning(f"[REPLY-GEN] Grok init failed: {e}")
        
        # FALLBACK: Check if LM Studio is running locally
        if not self.grok_connector:
            self._check_lm_studio()
        
        # Load BanterEngine as ultimate fallback
        # ENV SWITCH: Set DISABLE_BANTER_ENGINE=true to disable template fallbacks
        self.banter_engine = None
        if _env_truthy("DISABLE_BANTER_ENGINE"):
            logger.info("[REPLY-GEN] BanterEngine DISABLED via DISABLE_BANTER_ENGINE=true")
        else:
            try:
                from modules.ai_intelligence.banter_engine.src.banter_engine import BanterEngine
                self.banter_engine = BanterEngine()
                logger.info("[REPLY-GEN] BanterEngine loaded (fallback)")
            except Exception as e:
                logger.warning(f"[REPLY-GEN] BanterEngine not available: {e}")
        
        # Load GrokGreetingGenerator for MAGA detection
        if MAGA_DETECTOR_AVAILABLE and GrokGreetingGenerator:
            try:
                self.maga_detector = GrokGreetingGenerator()
                logger.info("[REPLY-GEN] GrokGreetingGenerator loaded (MAGA detection)")
            except Exception as e:
                logger.warning(f"[REPLY-GEN] GrokGreetingGenerator init failed: {e}")

        # QWEN AGENTIC RESPONDER (2025-12-30): Local llama.cpp fallback
        # Uses Qwen model directly via llama-cpp-python when Grok/LM Studio fail
        # ENV SWITCH: Set DISABLE_QWEN_ENGINE=true to skip local Qwen inference
        self.qwen_engine = None
        if _env_truthy("DISABLE_QWEN_ENGINE"):
            logger.info("[REPLY-GEN] QwenEngine DISABLED via DISABLE_QWEN_ENGINE=true")
        elif QWEN_ENGINE_AVAILABLE and QwenInferenceEngine:
            try:
                # Resolve local code model from central model selection.
                qwen_model_path = resolve_code_model_path()
                if qwen_model_path.exists():
                    self.qwen_engine = QwenInferenceEngine(
                        model_path=qwen_model_path,
                        max_tokens=150,  # Short replies
                        temperature=0.8,  # Creative but focused
                        context_length=1024  # Sufficient for comment context
                    )
                    logger.info(f"[REPLY-GEN] QwenInferenceEngine ready: {qwen_model_path.name}")
                else:
                    logger.warning(f"[REPLY-GEN] Qwen model not found: {qwen_model_path}")
            except Exception as e:
                logger.warning(f"[REPLY-GEN] QwenInferenceEngine init failed: {e}")

        # Phase 3O-3R Sprint 5: Initialize skill-based reply router
        self.skill_0 = None  # MAGA mockery
        self.skill_1 = None  # Regular engagement
        self.skill_2 = None  # Moderator appreciation

        if SKILLS_AVAILABLE:
            try:
                self.skill_0 = MagaMockerySkill()
                self.skill_1 = RegularEngagementSkill()
                self.skill_2 = ModeratorAppreciationSkill()
                logger.info("[REPLY-GEN] Phase 3O-3R skills initialized (0✊/1✋/2🖐️ router)")
            except Exception as e:
                logger.warning(f"[REPLY-GEN] Skill initialization failed: {e}")

        # CONTENT ANALYZER (2025-12-30): Extract MEANING for contextual replies
        # ENV SWITCH: Set DISABLE_CONTENT_ANALYZER=true to skip content analysis
        self.content_analyzer = None
        if _env_truthy("DISABLE_CONTENT_ANALYZER"):
            logger.info("[REPLY-GEN] ContentAnalyzer DISABLED via DISABLE_CONTENT_ANALYZER=true")
        elif CONTENT_ANALYZER_AVAILABLE and get_content_analyzer:
            try:
                self.content_analyzer = get_content_analyzer()
                logger.info("[REPLY-GEN] CommentContentAnalyzer ready (contextual replies enabled)")
            except Exception as e:
                logger.warning(f"[REPLY-GEN] CommentContentAnalyzer init failed: {e}")

        # LLM SOURCE TRACKING (2026-02-21): Track which LLM generated each reply for training data
        self._last_llm_source = None  # 'grok', 'lm_studio', 'qwen', 'template', 'skill_0', 'skill_1', 'skill_2'

        # LLM CHAIN STATUS SUMMARY (diagnostic)
        logger.info("[REPLY-GEN] ═══ LLM CHAIN STATUS ═══")
        logger.info(f"[REPLY-GEN]   Grok: {'✅ READY' if self.grok_connector else '❌ NOT AVAILABLE'}")
        logger.info(f"[REPLY-GEN]   LM Studio: {'✅ READY' if (self.lm_studio_available and self.lm_studio_model_id) else '❌ NOT AVAILABLE'}")
        logger.info(f"[REPLY-GEN]   Qwen Engine: {'✅ READY' if self.qwen_engine else '❌ NOT AVAILABLE'}")
        logger.info(f"[REPLY-GEN]   Content Analyzer: {'✅ READY' if self.content_analyzer else '❌ NOT AVAILABLE'}")
        logger.info(f"[REPLY-GEN]   BanterEngine: {'✅ READY' if self.banter_engine else '❌ NOT AVAILABLE'}")
        logger.info("[REPLY-GEN] ═════════════════════════")

    def _add_0102_signature(self, reply: str, tier: int = None, comment_age_days: int = None) -> str:
        """
        Add 0102 signature, tier emoji prefix, and holiday context for every reply.

        WSP 96 Compliant: Holiday awareness integrated from skills/holiday_awareness.json

        CRITICAL FIX (2025-12-30): Added deduplication check
        If reply already contains "0102" signature, skip signing to prevent duplicates
        like "🗓️ 2026 incoming! 🗓️ 2026 incoming!"

        CRITICAL FIX (2025-12-30): Added comment age validation
        Skip holiday suffixes for old comments (>7 days) - irrelevant to add
        "2026 incoming!" to a year-old comment
        """
        if reply is None:
            return reply

        reply = reply.strip()
        if not reply:
            return reply

        # UNICODE CLEANUP (2025-12-30): Convert escape sequences to actual emojis
        # LLMs sometimes output \\u2764 or U+2764 instead of actual emojis
        reply = _cleanup_unicode_escapes(reply)

        # DEDUPLICATION CHECK (2025-12-30): Skip if already signed
        # Prevents duplicate signatures/holiday suffixes
        # FIX: Updated to check for any tier emoji (not requiring "0102" text)
        tier_emojis_count = sum(1 for e in ["✊", "✋", "🖐️"] if e in reply)
        if tier_emojis_count >= 2:  # Already has 2+ tier emojis (start+end)
            logger.debug(f"[SIGNATURE] ⚠️ Already signed (found {tier_emojis_count} tier emojis), skipping: {reply[:50]}...")
            return reply

        # AGE VALIDATION (2025-12-30): Flag old comments
        # Holiday suffixes are ONLY for recent comments (< 7 days)
        is_old_comment = comment_age_days is not None and comment_age_days > 7
        if is_old_comment:
            logger.info(f"[SIGNATURE] 📅 Old comment ({comment_age_days} days) - skipping holiday suffix")

        # 012 -> Comment DAE broadcast hook (control plane)
        # Allows 012 to inject a short promotion/update without hardcoding it into prompts.
        # Uses non-fixed "dice-on-dice" gating to avoid spam signatures.
        try:
            from modules.communication.video_comments.src.commenting_control_plane import load_broadcast

            broadcast = load_broadcast()
            if (
                broadcast.enabled
                and tier in (1, 2)  # no promo for Tier 0 trolls
                and (broadcast.promo_handles or (broadcast.promo_message or "").strip())
            ):
                rng = random.SystemRandom()
                # Re-sample probability each time (not a fixed percent)
                p = rng.betavariate(2.0, 6.0)
                include = rng.random() < p

                if include:
                    promo_parts: list[str] = []
                    msg = (broadcast.promo_message or "").strip()
                    if msg:
                        promo_parts.append(msg)

                    handles = [h for h in (broadcast.promo_handles or []) if isinstance(h, str) and h.strip()]
                    handles = [h if h.startswith("@") else f"@{h}" for h in handles]
                    handles = [h for h in handles if h and h not in reply]  # avoid duplicates
                    if handles:
                        promo_parts.append("Check out " + " ".join(handles))

                    promo = " ".join(promo_parts).strip()
                    if promo:
                        reply = f"{reply} {promo}".strip()
        except Exception:
            # Best-effort only: never block reply generation due to control-plane failures.
            pass

        tier_emoji = self.TIER_EMOJI.get(tier, "")
        prefix = ""
        if tier_emoji and not reply.startswith(tier_emoji):
            prefix = f"{tier_emoji} "

        # 0102 Signature logic
        # FIX (2025-12-30): Show ONLY the tier emoji, not all three (✊✋🖐️)
        # User needs clear 0/1/2 classification, not a confusing triple-emoji
        # Format: "{tier_emoji} {reply} {tier_emoji}" - tier emoji at start AND end for visibility
        if tier_emoji:
            signature = f" {tier_emoji}"  # Only ONE emoji matching the tier
        else:
            signature = ""  # No emoji if tier unknown
        if not reply.endswith(tier_emoji) and tier_emoji and not any(e in reply for e in ["✊", "✋", "🖐️"]):
            suffix = signature
        else:
            suffix = ""

        # Holiday suffix (WSP 96: Skills Wardrobe Pattern)
        # 012 Voice: Tier-aware holiday messages
        # - Tier 0 (MAGA): Trolling/mockery
        # - Tier 1/2 (REGULAR/MOD): Friendly celebration
        # CRITICAL FIX (2025-12-30): SKIP for old comments (>7 days)
        # "2026 incoming!" is irrelevant on a year-old comment
        holiday_suffix = ""
        if HOLIDAY_AWARENESS_AVAILABLE and not is_old_comment:
            try:
                context = get_holiday_context()
                is_maga = (tier == 0)  # Only mock MAGA (Tier 0 ✊)

                if context.get("is_countdown"):
                    days = context.get("days_until_new_year", 0)
                    next_year = context.get("year_transition", "").split("→")[-1].strip()
                    if days == 0:
                        if is_maga:
                            # NYE - Tier 0: MAGA mockery
                            nye_options = [
                                " 🎆 NYE! MAGA still at ✊!",
                                " 🥂 Midnight won't evolve MAGA past ✊!",
                                f" 🎆 {next_year}! MAGA resolution: stay at ✊!",
                            ]
                        else:
                            # NYE - Tier 1/2: Friendly celebration
                            nye_options = [
                                f" 🎆 Happy {next_year}!",
                                " 🥂 NYE vibes!",
                                f" 🎇 Welcome to {next_year}!",
                            ]
                        holiday_suffix = random.choice(nye_options)
                    elif days <= 3:
                        if is_maga:
                            # Countdown - Tier 0: MAGA mockery
                            countdown_options = [
                                f" ⏳ {days}d until MAGA's new ✊ year!",
                                f" 🗓️ {days}d→{next_year} (MAGA: still ✊)",
                                f" ⏳ {days} days! Will MAGA hit 🖐️? No.",
                            ]
                        else:
                            # Countdown - Tier 1/2: Friendly countdown
                            countdown_options = [
                                f" ⏳ {days} days to {next_year}!",
                                f" 🗓️ {next_year} incoming!",
                            ]
                        holiday_suffix = random.choice(countdown_options)
                elif context.get("is_holiday"):
                    emoji = context.get("holiday_emoji", "🎉")
                    name = context.get("holiday_name", "")
                    if is_maga:
                        # Other holidays - Tier 0: MAGA consciousness check
                        holiday_options = [
                            f" {emoji} MAGA consciousness: ✊",
                            f" {emoji}",
                        ]
                    else:
                        # Other holidays - Tier 1/2: Friendly greeting
                        holiday_options = [
                            f" {emoji} Happy {name}!" if name else f" {emoji}",
                            f" {emoji}",
                        ]
                    holiday_suffix = random.choice(holiday_options)
            except Exception:
                pass  # Don't break replies on holiday errors

        signed_reply = f"{prefix}{reply}{suffix}{holiday_suffix}"

        # CARDIOVASCULAR LOGGING: Explicitly log the signature application
        logger.info(f"[SIGNATURE] ✍️ Applied 012 signature: {tier_emoji} (Tier {tier})")
        if holiday_suffix:
            logger.info(f"[SIGNATURE] 🎉 Holiday suffix: {holiday_suffix}")
        logger.info(f"[SIGNATURE]   Final Text: {signed_reply[:75]}...")

        return signed_reply
    
    def _is_emoji_comment(self, comment_text: str) -> bool:
        """
        Check if comment is mostly emojis (playful emoji comment).

        If someone just sends emojis, we reply with emojis - match their energy!

        Hardened 2026-01-23: Added comprehensive emoji ranges including hand gestures
        """
        if not comment_text:
            logger.debug("[EMOJI-CHECK] Empty comment text")
            return False

        # Log input for debugging
        logger.info(f"[EMOJI-CHECK] Input: '{comment_text}' (len={len(comment_text)}, repr={repr(comment_text)[:100]})")

        # Count emoji characters
        import re
        # Emoji pattern - COMPREHENSIVE (covers all Unicode emoji ranges)
        # Hardened 2026-01-23: Added missing ranges for hand gestures (👏🤟🤘)
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons (smileys)
            "\U0001F300-\U0001F5FF"  # symbols & pictographs (includes 👏 U+1F44F)
            "\U0001F680-\U0001F6FF"  # transport & map
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"  # dingbats
            "\U0001F900-\U0001F9FF"  # supplemental symbols (includes 🤟 U+1F91F, 🤘 U+1F918)
            "\U0001FA00-\U0001FA6F"  # chess symbols
            "\U0001FA70-\U0001FAFF"  # symbols extended
            "\U00002600-\U000026FF"  # misc symbols
            "\U0001F400-\U0001F4FF"  # additional pictographs (people, hands, gestures)
            "\U0001F910-\U0001F9FF"  # faces, hands extended range
            "\U0000FE00-\U0000FE0F"  # variation selectors
            "\U0001F3FB-\U0001F3FF"  # skin tone modifiers
            "]+",
            flags=re.UNICODE
        )

        # Find all emojis
        emojis = emoji_pattern.findall(comment_text)
        emoji_count = sum(len(e) for e in emojis)

        # Remove emojis to count text
        text_only = emoji_pattern.sub('', comment_text).strip()

        logger.info(f"[EMOJI-CHECK] Found {emoji_count} emoji chars, text_only='{text_only}' (len={len(text_only)})")

        # If mostly emoji (emoji > text, or very short text)
        if emoji_count > 0 and (len(text_only) < 5 or emoji_count >= len(text_only)):
            logger.info(f"[EMOJI-CHECK] ✅ IS EMOJI COMMENT (emoji_count={emoji_count}, text_len={len(text_only)})")
            return True

        logger.info(f"[EMOJI-CHECK] ❌ NOT emoji comment (emoji_count={emoji_count}, text_len={len(text_only)})")
        return False
    
    def _get_emoji_reply(self) -> str:
        """Get a random emoji reply - keep it playful!"""
        return random.choice(self.EMOJI_REPLIES)

    def _needs_fact_check(self, comment_text: str) -> bool:
        """Detect claim patterns that should trigger a fact-check reply."""
        if not comment_text:
            return False
        text = comment_text.lower()
        return any(phrase in text for phrase in self.FACT_CHECK_PHRASES)

    def _get_fact_check_reply(self) -> str:
        """Pick a neutral fact-check response."""
        return random.choice(self.FACT_CHECK_RESPONSES)

    def _normalize_text(self, text: str) -> str:
        if not text:
            return ""
        return " ".join(text.lower().split())

    def _get_recent_reply_norms(
        self,
        author_name: str,
        author_channel_id: Optional[str],
        limit: int = 5
    ) -> set:
        if not self.commenter_history_store or not make_commenter_key:
            return set()
        try:
            commenter_key = make_commenter_key(channel_id=author_channel_id, handle=author_name)
            interactions = self.commenter_history_store.get_recent_interactions(
                commenter_key=commenter_key,
                limit=limit
            )
            norms = {
                self._normalize_text(interaction.reply_text or "")
                for interaction in interactions
                if interaction.reply_text
            }
            return {n for n in norms if n}
        except Exception as e:
            logger.debug(f"[ANTI-REGURGITATION] Failed to load recent replies: {e}")
            return set()

    def _is_repeat_comment(
        self,
        author_name: str,
        author_channel_id: Optional[str],
        comment_text: str,
        limit: int = 3
    ) -> bool:
        if not self.commenter_history_store or not make_commenter_key:
            return False
        normalized = self._normalize_text(comment_text)
        if not normalized:
            return False
        try:
            commenter_key = make_commenter_key(channel_id=author_channel_id, handle=author_name)
            interactions = self.commenter_history_store.get_recent_interactions(
                commenter_key=commenter_key,
                limit=limit
            )
            for interaction in interactions:
                if normalized == self._normalize_text(interaction.comment_text or ""):
                    return True
            return False
        except Exception as e:
            logger.debug(f"[ANTI-REGURGITATION] Repeat comment check failed: {e}")
            return False

    def _dedupe_reply(
        self,
        reply_text: str,
        recent_reply_norms: set,
        fallback_candidates: Optional[List[str]] = None,
        fallback_callable: Optional[Any] = None
    ) -> str:
        if not reply_text or not recent_reply_norms:
            return reply_text
        if self._normalize_text(reply_text) not in recent_reply_norms:
            return reply_text

        if fallback_candidates:
            candidates = list(fallback_candidates)
            random.shuffle(candidates)
            for candidate in candidates:
                if candidate and self._normalize_text(candidate) not in recent_reply_norms:
                    return candidate

        if fallback_callable:
            for _ in range(3):
                candidate = fallback_callable()
                if candidate and self._normalize_text(candidate) not in recent_reply_norms:
                    return candidate

        return reply_text

    def _check_duplicate_pattern_reply(
        self,
        author_name: str,
        author_channel_id: Optional[str],
        pattern_name: str
    ) -> bool:
        """
        Check if we've recently replied to this commenter with the same pattern.

        Prevents regurgitation: If we replied "Check out #FFCPLN..." to this person
        in their last 3 interactions, skip pattern matching and use LLM for fresh reply.

        Args:
            author_name: Commenter's name
            author_channel_id: Commenter's channel ID
            pattern_name: The pattern being matched (e.g., "ffcpln", "song")

        Returns:
            True if duplicate detected (we've used this pattern recently)
            False if safe to use pattern
        """
        if not self.commenter_history_store or not make_commenter_key:
            return False  # History not available, allow pattern

        try:
            commenter_key = make_commenter_key(channel_id=author_channel_id, handle=author_name)
            interactions = self.commenter_history_store.get_recent_interactions(
                commenter_key=commenter_key,
                limit=3  # Check last 3 interactions
            )

            if not interactions:
                return False  # No history, allow pattern

            # Check if we've replied with this pattern recently
            pattern_keywords = {
                "ffcpln": ["#FFCPLN", "ffcpln", "ffc.foundups.com"],
                "song": ["#FFCPLN", "playlist", "ffc.foundups.com"]
            }.get(pattern_name, [])

            duplicate_count = 0
            for interaction in interactions:
                reply_text = (interaction.reply_text or "").lower()
                # Check if this pattern's keywords appear in recent replies
                if any(keyword.lower() in reply_text for keyword in pattern_keywords):
                    duplicate_count += 1

            if duplicate_count > 0:
                logger.warning(
                    f"[ANTI-REGURGITATION] DUPLICATE DETECTED: Already replied to {author_name} "
                    f"with '{pattern_name}' pattern in last {duplicate_count}/{len(interactions)} interactions. "
                    f"Using fresh LLM reply instead."
                )
                return True  # Duplicate detected

            return False  # Safe to use pattern

        except Exception as e:
            logger.debug(f"[ANTI-REGURGITATION] History check failed: {e}")
            return False  # On error, allow pattern
    
    def _get_semantic_pattern_prompt(self, comment_text: str) -> Optional[Dict[str, str]]:
        """
        Check if comment matches semantic patterns requiring specialized responses.

        Instead of returning fixed templates (REGURGITATION), returns LLM prompts
        that guide semantic variation. Each reply will be unique.

        Args:
            comment_text: The comment to check

        Returns:
            Dict with pattern info if matched:
                - pattern_name: Name of matched pattern
                - variation_prompt: LLM prompt for generating varied response
                - intent: What user is asking
            Returns None if no pattern match
        """
        comment_lower = comment_text.lower()

        for pattern_name, pattern_data in self.SEMANTIC_PATTERN_PROMPTS.items():
            keywords = pattern_data.get("keywords", [])

            # Check if any keyword matches
            for keyword in keywords:
                if keyword in comment_lower:
                    logger.info(f"[REPLY-GEN] Semantic pattern match: '{pattern_name}' (keyword: '{keyword}')")
                    logger.info(f"[ANTI-REGURGITATION] Using LLM variation prompt instead of fixed template")
                    return {
                        "pattern_name": pattern_name,
                        "variation_prompt": pattern_data.get("variation_prompt", ""),
                        "intent": pattern_data.get("intent", "")
                    }

        return None
    
    def _check_lm_studio(self):
        """Check if LM Studio is running (fallback when Grok unavailable)."""
        try:
            response = requests.get(
                os.getenv("LM_STUDIO_MODELS_URL", "http://127.0.0.1:1234/v1/models"),
                timeout=2
            )
            if response.status_code == 200:
                models = response.json().get("data", [])
                model_ids = [m.get("id", "") for m in models if m.get("id")]
                if not model_ids:
                    logger.warning("[REPLY-GEN] LM Studio responded but no models")
                    return

                self.lm_studio_available = True

                if not self.lm_studio_model_id:
                    # YTR1: Exclude TTS/audio/speech models - they output control tokens, not text
                    # Patterns: tts, audio, speech, whisper, bark, kokoro, dia
                    exclude_patterns = ("tts", "audio", "speech", "whisper", "bark", "kokoro", "dia")
                    text_models = [
                        mid for mid in model_ids
                        if not any(pat in mid.lower() for pat in exclude_patterns)
                    ]

                    if not text_models:
                        logger.error(f"[REPLY-GEN] ❌ NO TEXT MODELS in LM Studio - only TTS/audio: {model_ids}")
                        logger.error(f"[REPLY-GEN] Set LM_STUDIO_MODEL env var or load a text model (qwen, gemma)")
                        self.lm_studio_available = False
                        return

                    preferred = next((mid for mid in text_models if "qwen" in mid.lower()), None)
                    if not preferred:
                        preferred = next((mid for mid in text_models if "gemma" in mid.lower()), None)
                    self.lm_studio_model_id = preferred or text_models[0]

                logger.info(f"[REPLY-GEN] LM Studio available (model={self.lm_studio_model_id})")
            else:
                logger.warning("[REPLY-GEN] LM Studio responded but no models")
        except Exception as e:
            logger.warning(f"[REPLY-GEN] LM Studio not available: {e}")

    def _load_personalization_context(
        self,
        *,
        author_name: str,
        author_channel_id: Optional[str],
        max_chat_messages: int = 5,
        max_prior_interactions: int = 3,
    ) -> str:
        """
        Load minimal per-user context to personalize replies.

        Uses (in order):
        - prior Studio interactions recorded by the engagement skill
        - live chat history (SQLite) when available

        NOTE: This is a PoC foundation. TODO: Use Gemma to summarize/route context (WSP 77).
        """
        lines: list[str] = []

        # 1) Prior Studio interactions (our own reply history)
        if self.commenter_history_store and make_commenter_key:
            try:
                commenter_key = make_commenter_key(channel_id=author_channel_id, handle=author_name)
                summary = self.commenter_history_store.get_profile_summary(commenter_key=commenter_key)
                if summary.get("total", 0):
                    lines.append(
                        "Studio engagement summary: "
                        f"total={summary.get('total')} "
                        f"replies={summary.get('replies')} "
                        f"likes={summary.get('likes')} "
                        f"hearts={summary.get('hearts')}"
                    )
                interactions = self.commenter_history_store.get_recent_interactions(
                    commenter_key=commenter_key,
                    limit=max_prior_interactions,
                )
                if interactions:
                    lines.append("Prior Studio engagements with this user (oldest to newest):")
                    for item in interactions:
                        comment_preview = (item.comment_text or "").strip().replace("\n", " ")[:160]
                        reply_preview = (item.reply_text or "").strip().replace("\n", " ")[:160]
                        if reply_preview:
                            lines.append(f"- They said: \"{comment_preview}\" | You replied: \"{reply_preview}\"")
                        else:
                            lines.append(f"- They said: \"{comment_preview}\" | You did not reply")
            except Exception as e:
                logger.debug(f"[REPLY-GEN] Studio history lookup failed: {e}")

        # 2) Live chat history (if the same person appeared in chat)
        if self.chat_history_store:
            try:
                messages: list[dict] = []
                if author_channel_id:
                    messages = self.chat_history_store.get_recent_messages_by_author_id(
                        author_channel_id, max_chat_messages
                    )

                # Fallback to name-based lookup (handles commenters without channel_id)
                if not messages:
                    candidates: list[str] = []
                    if author_name:
                        candidates.append(author_name)
                        if author_name.startswith("@"):
                            candidates.append(author_name[1:])
                        else:
                            candidates.append(f"@{author_name}")
                    for candidate in candidates:
                        messages = self.chat_history_store.get_recent_messages(candidate, max_chat_messages)
                        if messages:
                            break

                if messages:
                    lines.append("Recent live chat messages by this user (oldest to newest):")
                    for msg in messages:
                        text = (msg.get("text") or "").strip().replace("\n", " ")[:180]
                        role = (msg.get("role") or "USER").strip()
                        lines.append(f"- [{role}] {text}")
            except Exception as e:
                logger.debug(f"[REPLY-GEN] Live chat history lookup failed: {e}")

        return "\n".join(lines).strip()

    def _get_voice_memory(self):
        """Lazy-initialize VoiceMemory (Digital Twin RAG) on first use."""
        if self._voice_memory is None:
            try:
                from modules.ai_intelligence.digital_twin.src.voice_memory import VoiceMemory
                self._voice_memory = VoiceMemory(include_videos=True)
                logger.info("[VOICE-MEMORY] Initialized for reply grounding")
            except Exception as e:
                logger.warning(f"[VOICE-MEMORY] Init failed (replies will proceed without grounding): {e}")
                self._voice_memory = False  # Mark unavailable
        return self._voice_memory if self._voice_memory else None

    def _load_voice_memory_context(self, comment_text: str) -> str:
        """
        Query VoiceMemory for grounding context relevant to the comment.

        Returns formatted context string, or empty string if unavailable/no results.
        Never blocks reply generation — all failures return empty string.
        """
        if not self._voice_memory_enabled:
            return ""

        vm = self._get_voice_memory()
        if not vm:
            return ""

        try:
            results = vm.query(comment_text, k=3)
            if not results:
                return ""

            # Filter low-relevance noise
            relevant = [r for r in results if r.get("score", 0) > 0.3]
            if not relevant:
                logger.debug(f"[VOICE-MEMORY] All results below 0.3 threshold for: {comment_text[:50]}")
                return ""

            lines = []
            for r in relevant:
                text = r.get("text", "").strip()[:120]
                source = r.get("source_type", "unknown")
                if text:
                    lines.append(f"- {text} (source: {source})")

            if lines:
                context = "\n".join(lines)
                logger.info(f"[VOICE-MEMORY] Grounding context: {len(relevant)} snippets for reply")
                return context
        except Exception as e:
            logger.warning(f"[VOICE-MEMORY] Query failed (proceeding without grounding): {e}")

        return ""

    def _generate_contextual_reply(
        self,
        comment_text: str,
        author_name: str,
        author_channel_id: Optional[str] = None,
        custom_prompt: Optional[str] = None,
        tier: Optional[int] = None
    ) -> Optional[str]:
        """
        Generate a contextual reply using Grok (primary) or LM Studio (fallback).

        Priority:
        1. Grok via xAI API (witty, fewer guardrails) - requires GROK_API_KEY/XAI_API_KEY
        2. LM Studio (local Qwen) - requires LM Studio running on port 1234

        Args:
            comment_text: The comment to reply to
            author_name: The commenter's name
            author_channel_id: Author's channel ID (for history lookup)
            custom_prompt: Optional custom prompt for semantic variation (ANTI-REGURGITATION)
            tier: Classification tier (0=MAGA_TROLL, 1=REGULAR, 2=MODERATOR) for tier-specific prompts

        Returns:
            Contextual reply or None if all LLMs unavailable
        """
        # If custom prompt provided (e.g., semantic variation prompts), use it directly
        if custom_prompt:
            user_prompt = custom_prompt
            logger.info("[ANTI-REGURGITATION] Using custom semantic variation prompt")
        elif tier == 0:
            # TIER 0 (MAGA_TROLL): Mockery with #FFCPLN hashtag
            user_prompt = f'''Comment from @{author_name}: "{comment_text}"

Generate a sarcastic, mocking reply that dismisses this troll comment. Style: witty mockery, not hostile.
- Reference: "besties for 15 years think he didnt know it" (if relevant to trust/betrayal themes)
- MUST include #FFCPLN hashtag somewhere naturally
- Keep it short (1-2 sentences)
- Be dismissive but clever
- Do NOT start with @mentions

Examples of tone:
- "Ok buddy, sure 👍 #FFCPLN"
- "15 years of friendship and you think he didn't see it coming? #FFCPLN"
- "That's... certainly a take. #FFCPLN"'''
            logger.info("[TIER-0] Using MAGA mockery prompt with #FFCPLN")
        elif tier == 2:
            # TIER 2 (MODERATOR): Empowerment with #FFCPLN references
            user_prompt = f'''Comment from @{author_name}: "{comment_text}"

Generate an empowering, supportive reply for this community moderator/leader.
- Use phrases like: "keep up the fight", "stay strong", "you're doing great"
- Include #FFCPLN context: "#FFCPLN always fail" OR "nearly 100 songs on #FFCPLN playlist at ffc.foundups.com"
- Acknowledge their contributions to the community
- Keep it short (1-2 sentences)
- Be encouraging and appreciative
- Do NOT start with @mentions

Examples of tone:
- "Keep up the fight! #FFCPLN always fail 🚀"
- "You're crushing it! Check out nearly 100 songs on the #FFCPLN playlist at ffc.foundups.com 🎵"
- "Stay strong - your work matters! #FFCPLN"'''
            logger.info("[TIER-2] Using moderator empowerment prompt with #FFCPLN")
        else:
            # TIER 1 (REGULAR): Standard contextual reply
            if author_name and author_name.lower() != "unknown":
                user_prompt = f'Comment from @{author_name}: "{comment_text}"\n\nGenerate a friendly, short reply (1-2 sentences). Do NOT start with @mentions:'
            else:
                user_prompt = f'Comment: "{comment_text}"\n\nGenerate a friendly, short reply (1-2 sentences). Do NOT start with @mentions:'

            # Add personalization context (comment history)
            context = self._load_personalization_context(
                author_name=author_name,
                author_channel_id=author_channel_id,
            )
            if context:
                 user_prompt += f"\n\nCONTEXT (Use this to personalize, but don't be creepy):\n{context}"

            # VOICE MEMORY GROUNDING (2026-02-04): Inject Digital Twin RAG context
            # Prevents identity fabrication by grounding replies in verified memory
            voice_context = self._load_voice_memory_context(comment_text)
            if voice_context:
                user_prompt += f"\n\n012's VERIFIED MEMORY (use ONLY this for personal claims):\n{voice_context}"

        # CONTENT ANALYSIS ENHANCEMENT (2025-12-30): Add extracted meaning to prompt
        # This enables truly CONTEXTUAL replies instead of generic templates
        if hasattr(self, '_current_content_analysis') and self._current_content_analysis:
            analysis = self._current_content_analysis

            # Build alignment guidance (CRITICAL for proper engagement)
            alignment_guidance = ""
            if analysis.aligns_with_video is True:
                alignment_guidance = f"""

🤝 VIDEO ALIGNMENT: AGREES
The commenter AGREES with the video's stance ({analysis.alignment_reason}).
RESPONSE STRATEGY: VALIDATE their point. Acknowledge you're on the same side.
- YES: "100% - calling it what it is", "Exactly right", "Spot on observation"
- NO: Do NOT dismiss, correct, or redirect them. They're an ally."""
            elif analysis.aligns_with_video is False:
                alignment_guidance = f"""

🚫 VIDEO ALIGNMENT: DISAGREES
The commenter DISAGREES with the video's stance ({analysis.alignment_reason}).
RESPONSE STRATEGY: Challenge respectfully or redirect.
- Options: Fact-check, gentle push-back, or redirect to video content"""

            user_prompt += f"""

COMMENT ANALYSIS (use this to craft a relevant response):
- Topic: {analysis.topic}
- Sentiment: {analysis.sentiment}
- Type: {analysis.comment_type}
- Key Point: {analysis.key_point}
- Engagement Hook: {analysis.engagement_hook or 'respond to their main point'}{alignment_guidance}

IMPORTANT: Your reply MUST address their {analysis.comment_type} about "{analysis.key_point[:30]}". Do NOT use generic phrases like "thanks for watching" or "holding it down" - respond to what they ACTUALLY said.

OUTPUT FORMAT: Reply with ONLY the reply text. Do NOT include:
- Explanations (e.g., "This reply addresses...")
- Notes (e.g., "Note: This comment...")
- Reasoning (e.g., "This is relevant because...")
- Multiple options or alternatives
Just output the actual reply text, nothing else."""
            logger.info(f"[LLM-CHAIN] 📝 Content analysis added to prompt (topic={analysis.topic}, aligns={analysis.aligns_with_video})")

        # CRITICAL FIX (2026-02-21): OUTPUT FORMAT must ALWAYS be added, not just when content_analysis exists
        # This prevents LLM from outputting explanations like "Note: This comment..." in replies
        if "OUTPUT FORMAT:" not in user_prompt:
            user_prompt += """

OUTPUT FORMAT: Reply with ONLY the reply text. Do NOT include:
- Explanations (e.g., "This reply addresses...")
- Notes (e.g., "Note: This comment...")
- Reasoning (e.g., "This is relevant because...")
- Multiple options or alternatives
- Brackets or parentheses with commentary
Just output the actual reply text, nothing else."""
            logger.info("[LLM-CHAIN] 📝 OUTPUT FORMAT instructions added to prompt")

        try:
            # LLM FALLBACK CHAIN LOGGING (diagnostic)
            logger.info(f"[LLM-CHAIN] ═══ STARTING LLM FALLBACK CHAIN ═══")
            logger.info(f"[LLM-CHAIN]   Comment: {comment_text[:60]}...")
            logger.info(f"[LLM-CHAIN]   Author: @{author_name}")
            logger.info(f"[LLM-CHAIN]   Tier: {tier}")

            # 1. Try Grok (XAI) - Uses get_response() method from LLMConnector
            if self.grok_connector:
                logger.info(f"[LLM-CHAIN] [1/3] Trying Grok (xAI)...")
                try:
                    reply = self.grok_connector.get_response(
                        prompt=user_prompt,
                        system_prompt=self.REPLY_SYSTEM_PROMPT
                    )
                    if reply:
                        # Clean reply (remove @mentions at start, etc.)
                        reply = self._clean_reply(reply, author_name)
                        self._last_llm_source = 'grok'  # Track for training data
                        logger.info(f"[LLM-CHAIN] ✅ GROK SUCCESS: {reply[:80]}...")
                        return reply
                    else:
                        logger.warning(f"[LLM-CHAIN] ❌ Grok returned None/empty")
                except Exception as grok_err:
                    logger.warning(f"[LLM-CHAIN] ❌ Grok exception: {grok_err}")
            else:
                logger.warning(f"[LLM-CHAIN] ⏭️ Grok connector NOT AVAILABLE (no API key?)")

            # 2. Try LM Studio (Local Fallback)
            logger.info(f"[LLM-CHAIN] [2/3] Trying LM Studio (lm_studio_available={self.lm_studio_available}, model={self.lm_studio_model_id})")
            if self.lm_studio_available and self.lm_studio_model_id:
                # Construct messages for LM Studio
                messages = [
                    {"role": "system", "content": self.REPLY_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ]

                payload = {
                    "model": self.lm_studio_model_id,
                    "messages": messages,
                    "temperature": 0.9,
                    "max_tokens": 150
                }

                try:
                    # 2026-02-04: Reduced from 15s→8s (speed optimization)
                    response = requests.post(
                        self.LM_STUDIO_URL,
                        json=payload,
                        headers={"Content-Type": "application/json"},
                        timeout=8
                    )

                    if response.status_code == 200:
                        json_resp = response.json()
                        if "choices" in json_resp and json_resp["choices"]:
                            content = json_resp["choices"][0]["message"]["content"]

                            # YTR1: Reject TTS/audio control tokens - wrong model type loaded
                            tts_token_patterns = ("<|s_", "<|audio", "<|speech", "<|tts")
                            if content and any(content.strip().startswith(pat) for pat in tts_token_patterns):
                                logger.error(f"[LLM-CHAIN] ❌ TTS TOKENS DETECTED - wrong model '{self.lm_studio_model_id}'")
                                logger.error(f"[LLM-CHAIN] Output: {content[:100]}...")
                                logger.error(f"[LLM-CHAIN] Load a TEXT model (qwen, gemma) or set LM_STUDIO_MODEL")
                                # Fall through to next LLM - do NOT return this as success
                            else:
                                self._last_llm_source = 'lm_studio'  # Track for training data
                                logger.info(f"[LLM-CHAIN] ✅ LM STUDIO SUCCESS: {content[:80]}...")
                                return content
                        else:
                            logger.warning(f"[LLM-CHAIN] ❌ LM Studio returned empty choices")
                    else:
                        logger.warning(f"[LLM-CHAIN] ❌ LM Studio HTTP {response.status_code}: {response.text[:100]}")
                except Exception as e:
                    logger.warning(f"[LLM-CHAIN] ❌ LM Studio exception: {e}")
            else:
                logger.warning(f"[LLM-CHAIN] ⏭️ LM Studio NOT AVAILABLE")

            # 3. Try QwenInferenceEngine (Local llama.cpp - 2025-12-30 Agentic Responder)
            logger.info(f"[LLM-CHAIN] [3/4] Trying QwenInferenceEngine (local llama.cpp)")
            if self.qwen_engine:
                try:
                    # ENHANCED: Use content analysis for contextual replies
                    content_context = ""
                    if hasattr(self, '_current_content_analysis') and self._current_content_analysis:
                        analysis = self._current_content_analysis
                        content_context = f"""
The comment is about: {analysis.topic}
Sentiment: {analysis.sentiment}
Key point: {analysis.key_point}
Respond to: {analysis.engagement_hook or 'their main point'}
"""

                    qwen_prompt = f"""Generate a SHORT reply (max 15 words) to this YouTube comment.
{content_context}
Comment: "{comment_text}"

Rules:
- MAX 15 WORDS
- ONE sentence only
- No explanations
- Just the reply"""
                    qwen_response = self.qwen_engine.generate_response(
                        prompt=qwen_prompt,
                        system_prompt="You reply in 15 words or less. Never explain. Just reply.",
                        max_tokens=50  # Reduced from 100 to force brevity
                    )
                    if qwen_response and not qwen_response.startswith("Error:"):
                        # Clean up the response
                        qwen_response = self._clean_reply(qwen_response, author_name)

                        # QWEN LENGTH GATE (2026-02-21): Reject if too long or has explanatory text
                        if qwen_response and qwen_response.strip():
                            word_count = len(qwen_response.split())
                            # Gate: Max 25 words (allow some buffer over 15 word prompt)
                            if word_count > 25:
                                logger.warning(f"[LLM-CHAIN] ❌ Qwen response too long ({word_count} words), rejecting")
                                qwen_response = None
                            # Gate: Reject if still has explanatory patterns
                            elif any(p in qwen_response.lower() for p in ['this response', 'this reply', 'note:', 'the key point']):
                                logger.warning(f"[LLM-CHAIN] ❌ Qwen response has explanatory text, rejecting")
                                qwen_response = None

                        if qwen_response and qwen_response.strip():
                            self._last_llm_source = 'qwen'  # Track for training data
                            logger.info(f"[LLM-CHAIN] ✅ QWEN ENGINE SUCCESS: {qwen_response[:80]}...")
                            return qwen_response
                        else:
                            logger.warning(f"[LLM-CHAIN] ❌ Qwen response rejected by length/pattern gate")
                    else:
                        logger.warning(f"[LLM-CHAIN] ❌ Qwen returned error: {qwen_response[:100] if qwen_response else 'None'}")
                except Exception as e:
                    logger.warning(f"[LLM-CHAIN] ❌ Qwen exception: {e}")
            else:
                logger.warning(f"[LLM-CHAIN] ⏭️ QwenInferenceEngine NOT AVAILABLE")

            # 4. Fallback to BanterEngine (if available) - Templates only (last resort)
            logger.info(f"[LLM-CHAIN] [4/4] Falling back to BanterEngine (TEMPLATE-BASED)")
            if self.banter_engine:
                 # Map tier to BanterEngine style if possible, or just generic
                 logger.warning("[LLM-CHAIN] ⚠️ Using BanterEngine TEMPLATES (NOT contextual!)")
                 state_info, banter_reply = self.banter_engine.process_input_enhanced(comment_text)
                 if not banter_reply or banter_reply == "...silence...":
                     banter_reply = self.banter_engine.get_random_banter_enhanced("default")
                 self._last_llm_source = 'template'  # Track for training data
                 logger.info(f"[LLM-CHAIN] BanterEngine reply: {banter_reply[:80] if banter_reply else 'None'}...")
                 return banter_reply

            return None

        except Exception as e:
            logger.error(f"[REPLY-GEN] Contextual reply generation failed: {e}")
            return None

    def get_last_llm_source(self) -> str:
        """Get the LLM source that generated the last reply (for training data).

        Returns:
            str: 'grok', 'lm_studio', 'qwen', 'template', 'skill_0', 'skill_1', 'skill_2', or 'unknown'
        """
        return self._last_llm_source or 'unknown'

    def _clean_reply(self, reply: str, author_name: str) -> str:
        """Clean up LLM-generated reply.

        FIX (2026-02-21): Also strips explanatory text that LLM sometimes outputs
        despite OUTPUT FORMAT instructions.
        """
        reply = reply.strip()

        # Remove quotes if wrapped
        if reply.startswith('"') and reply.endswith('"'):
            reply = reply[1:-1]

        # FIX (2026-02-21): Strip explanatory text patterns that LLM outputs
        # These patterns indicate LLM is outputting chain-of-thought instead of just the reply
        import re

        # Pattern 1: Text followed by "Note:" or "(Note:" - keep only text before
        note_patterns = [
            r'\s*Note:.*$',           # "reply text Note: explanation"
            r'\s*\(Note:.*$',         # "reply text (Note: explanation)"
            r'\s*\[Note:.*$',         # "reply text [Note: explanation]"
        ]
        for pattern in note_patterns:
            reply = re.sub(pattern, '', reply, flags=re.IGNORECASE | re.DOTALL)

        # Pattern 2: Bracketed/parenthesized explanations at end
        # E.g., "reply text [This response shows...]" or "reply text (This is a direct response...)"
        explanation_patterns = [
            r'\s*\[This\s+(response|reply|comment).*$',
            r'\s*\(This\s+(response|reply|comment).*$',
            r'\s*This\s+(response|reply)\s+(addresses|shows|maintains|directly).*$',
        ]
        for pattern in explanation_patterns:
            reply = re.sub(pattern, '', reply, flags=re.IGNORECASE | re.DOTALL)

        # Pattern 3: Multiple quoted replies (LLM outputting options)
        # Keep only the first quoted section if multiple exist
        if reply.count('"') >= 4:  # Multiple quoted strings
            # Extract first quoted string
            first_quote_match = re.match(r'^["\']?([^"\']+)["\']', reply)
            if first_quote_match:
                reply = first_quote_match.group(1).strip()

        # Remove quotes if wrapped (re-check after pattern removal)
        if reply.startswith('"') and reply.endswith('"'):
            reply = reply[1:-1]
        if reply.startswith("'") and reply.endswith("'"):
            reply = reply[1:-1]

        # Remove @ mention if LLM added it
        if reply.startswith(f"@{author_name}"):
            reply = reply[len(f"@{author_name}"):].strip()

        # NEVER include @Unknown - that's embarrassing!
        if "@Unknown" in reply or "@unknown" in reply:
            reply = reply.replace("@Unknown", "").replace("@unknown", "").strip()

        # Clean up any double spaces
        while "  " in reply:
            reply = reply.replace("  ", " ")

        return reply.strip()
    
    def classify_commenter(
        self,
        author_name: str,
        comment_text: str,
        author_channel_id: Optional[str] = None,
        is_mod: bool = False,
        is_subscriber: bool = False
    ) -> CommenterProfile:
        """
        Classify a commenter based on available information (Hardened).
        
        Uses WSP 77 (Agent Coordination) logic:
        - Gemma (Associate): Fast pattern matching & heuristics
        - Grok (Partner): Explicit MAGA detection
        - Database (History): Moderator status
        """
        profile = CommenterProfile(
            name=author_name,
            channel_id=author_channel_id,
            is_moderator=is_mod,
            is_subscriber=is_subscriber,
        )

        logger.info(f"[CLASSIFY] 🔍 ANALYZING POSTER: @{author_name}")
        logger.info(f"[CLASSIFY]   Comment: \"{comment_text[:50]}...\"")
        
        # GEMMA-ASSOCIATE PATTERN RECOGNITION (Heuristic layer)
        gemma_insight = self._gemma_pattern_recognition(comment_text, author_name)
        logger.info(f"[CLASSIFY] [GEMMA-ASSOCIATE] Patterns: {json.dumps(gemma_insight['patterns']) if 'json' in globals() else gemma_insight['patterns']}")

        # Step 1: Check if moderator 🖐️ (Tier 2)
        if is_mod or check_moderator_in_db(author_name, author_channel_id):
            profile.is_moderator = True
            profile.commenter_type = CommenterType.MODERATOR
            logger.info(f"[CLASSIFY] [DECISION] Result: 2🖐️ (MODERATOR)")
            logger.info(f"[CLASSIFY]   Reason: Verified in database or DOM badge")
            return profile

        # Step 1.5: Check whack history from magadoom_scores.db (strongest troll signal)
        # WSP 96: Uses extracted CommenterClassifier for whack tracking (FIX 2026-02-19)
        if CLASSIFIER_AVAILABLE:
            try:
                classifier = get_classifier()
                classifier_result = classifier.classify_commenter(
                    user_id=author_channel_id or author_name,
                    username=author_name,
                    comment_text=comment_text
                )

                # If classifier found whack history, immediately classify as troll
                if classifier_result.get('method') == 'whack_history_lookup':
                    whack_count = classifier_result.get('whack_count', 0)
                    confidence = classifier_result.get('confidence', 0.7)
                    profile.is_troll = True
                    profile.commenter_type = CommenterType.MAGA_TROLL
                    profile.troll_score = confidence
                    logger.info(f"[CLASSIFY] [DECISION] Result: 0✊ (MAGA_TROLL)")
                    logger.info(f"[CLASSIFY]   Reason: WHACK HISTORY - {whack_count}x prior whacks (confidence: {confidence:.2f})")
                    logger.info(f"[CLASSIFY]   Source: magadoom_scores.db whacked_users")
                    return profile

                # ALLY DETECTION (2026-02-12): Check for anti-Trump/anti-MAGA ally
                # If they're criticizing Trump, AGREE with them - don't give generic response!
                # 2026-02-17: ALLY collapsed into MODERATOR (2) - use is_ally flag for agreement mode
                if classifier_result.get('method') == 'sentiment_ally':
                    pattern = classifier_result.get('pattern_detected', '')
                    confidence = classifier_result.get('confidence', 0.85)
                    profile.commenter_type = CommenterType.MODERATOR  # 2 = MODERATOR (includes allies)
                    profile.is_ally = True  # Flag for agreement-mode responses
                    logger.info(f"[CLASSIFY] [DECISION] Result: 2🖐️ (MODERATOR/ALLY)")
                    logger.info(f"[CLASSIFY]   Reason: ANTI-TRUMP ALLY - pattern: '{pattern}' (confidence: {confidence:.2f})")
                    logger.info(f"[CLASSIFY]   Strategy: AGREE and join in trolling Trump! #FFCPLN")
                    return profile

                # If classifier detected hostile sentiment, boost troll scoring
                if classifier_result.get('method') == 'sentiment_hostile':
                    pattern = classifier_result.get('pattern_detected', '')
                    logger.info(f"[CLASSIFY] [SENTIMENT] Hostile pattern detected: '{pattern}'")
                    logger.info(f"[CLASSIFY]   Boosting troll score for heuristic check")
                    # Will be picked up by _calculate_troll_score below

            except Exception as e:
                logger.debug(f"[CLASSIFY] CommenterClassifier check failed: {e}")

        # Step 2: Check for MAGA troll indicators ✊ (Tier 0)
        troll_score, maga_response = self._calculate_troll_score(comment_text, author_name)
        profile.troll_score = troll_score
        
        if troll_score >= 0.7:
            profile.is_troll = True
            profile.commenter_type = CommenterType.MAGA_TROLL
            profile.maga_response = maga_response
            logger.info(f"[CLASSIFY] [DECISION] Result: 0✊ (MAGA_TROLL)")
            logger.info(f"[CLASSIFY]   Reason: Troll score {troll_score:.2f} (Grok/Heuristic)")
            return profile
        
        # Step 3: Check subscriber status ✋ (Tier 1)
        if is_subscriber or gemma_insight.get('is_likely_loyally_engaged'):
            profile.commenter_type = CommenterType.SUBSCRIBER
            logger.info(f"[CLASSIFY] [DECISION] Result: 1✋ (SUBSCRIBER/LOYAL)")
            logger.info(f"[CLASSIFY]   Reason: {'DOM badge' if is_subscriber else 'Gemma loyalty pattern'}")
            return profile
        
        # Step 4: Default to regular user ✋ (Tier 1)
        profile.commenter_type = CommenterType.REGULAR
        logger.info(f"[CLASSIFY] [DECISION] Result: 1✋ (REGULAR)")
        logger.info(f"[CLASSIFY]   Reason: Default classification (safe/neutral)")
        return profile

    def _gemma_pattern_recognition(self, comment_text: str, author_name: str) -> Dict[str, Any]:
        """
        Phase 1 (Gemma Associate): Heuristic-based pattern recognition.
        Simulates Gemma's fast binary classification for 'Loyalty' vs 'Neutral'.
        """
        patterns = []
        is_loyal = False
        text_lower = comment_text.lower()
        
        # Positive patterns (Loyalty/Engagement)
        loyalty_markers = ['love', 'great', 'awesome', 'keep it up', 'thanks', 'arigato', 'japan']
        hits = [m for m in loyalty_markers if m in text_lower]
        if hits:
            patterns.append(f"loyalty_keywords({len(hits)})")
            if len(hits) >= 2:
                is_loyal = True
        
        # Structural patterns (Long-form engagement)
        if len(comment_text) > 100:
            patterns.append("depth_engagement")
            is_loyal = True
            
        # Question pattern (Curiosity/Engagement)
        if '?' in comment_text and len(comment_text) > 20:
            patterns.append("curiosity_pattern")
            
        return {
            'is_likely_loyally_engaged': is_loyal,
            'patterns': patterns
        }
    
    # Trump-defending phrases that indicate MAGA trolling (Whack-a-MAGA style)
    TRUMP_DEFENSE_PHRASES = [
        # Defending Trump from accusations
        "trump is not", "trump isn't", "trump didn't", "trump never",
        "trump was not", "trump wasn't", "not trump's fault", "trump is innocent",
        "trump did nothing", "leave trump alone", "trump is right",
        "witch hunt", "hoax", "fake charges", "political persecution",
        "weaponized", "two tier justice", "unfair to trump",
        # Files/documents specific
        "not involved in the files", "documents case", "classified documents",
        # General defense
        "trump derangement", "tds", "you just hate trump", "orange man bad",
        # Nazi/Hitler comparison deflection (2025-12-23: Critical pattern for @Peter-n5k3i detection)
        "what is a nazi", "not a nazi", "trump is no nazi", "trump isn't a nazi",
        "not hitler", "trump is not hitler", "trump isn't hitler", "hitler comparison",
        "comparing to hitler", "called hitler", "calling trump hitler", "trump/hitler",
        "not a fascist", "trump isn't fascist", "not fascism", "mike needs education",
        "tds mike", "nazi comparison", "everyone a nazi", "calling everyone nazi",
        "learn what nazi", "what nazi means", "definition of nazi", "real nazi",
        # 1933 deflection
        "1933", "enabling act", "weimar", "not 1933", "not like 1933",
        # Second Amendment / Gun rights rhetoric (2025-12-23: @GregCaldwell-p6u detection)
        "second amendment", "2nd amendment", "2a", "shall not be infringed",
        "gun rights", "come and take", "molon labe", "cold dead hands",
        "armed", "locked and loaded", "target practice",
        # MAGA slang / Aggressive rhetoric (2025-12-23: FAFO detection)
        "fafo", "fuck around and find out", "find out", "f around",
        "bring it on", "try me", "come get some",
    ]
    
    def _calculate_troll_score(self, comment_text: str, author_name: str) -> tuple[float, Optional[str]]:
        """
        Calculate troll probability and get response using Whack-a-MAGA style detection.
        
        Detection layers:
        1. GrokGreetingGenerator (explicit MAGA support)
        2. Trump-defending phrases (subtle trolling)
        3. Keyword heuristics (fallback)
        
        Returns:
            Tuple of (troll_score, maga_response or None)
        """
        score = 0.0
        maga_response = None
        text_lower = comment_text.lower()
        name_lower = author_name.lower()
        
        # LAYER 1: GrokGreetingGenerator MAGA detection (explicit support)
        if self.maga_detector:
            try:
                maga_response = self.maga_detector.get_response_to_maga(comment_text)
                if maga_response:
                    score = 1.0
                    logger.info(f"[REPLY-GEN] GrokGreetingGenerator detected MAGA content")
                    return score, maga_response
            except Exception as e:
                logger.debug(f"MAGA detector error: {e}")
        
        # LAYER 2: Trump-defending phrases (Whack-a-MAGA catches these!)
        for phrase in self.TRUMP_DEFENSE_PHRASES:
            if phrase in text_lower:
                score = 0.9  # High confidence troll
                logger.info(f"[REPLY-GEN] Whack-a-MAGA: Trump defense detected '{phrase}'")
                # Generate Whack-a-MAGA style response
                return score, None  # Will use TROLL_RESPONSES
        
        # LAYER 3: HOSTILE PATTERNS (Phase 1 from FLOW_ANALYSIS_20251223)
        # Sarcastic, dismissive, or aggressive language that indicates troll intent
        # even if not explicitly MAGA content (e.g., "Don't come back" @mermadicamerican7754)
        HOSTILE_PATTERNS = [
            # Dismissal patterns
            "don't come back", "dont come back", "go away", "leave", "get out", "bye bye",
            # Rejection patterns
            "nobody asked", "who cares", "shut up", "who asked",
            # Aggression patterns
            "gtfo", "stfu", "good riddance", "piss off", "f off", "fck off",
            # Sarcasm (hard to detect but common trolling) - when combined with hostility
            # "so glad" + "don't come back" = hostile sarcasm
        ]
        
        for pattern in HOSTILE_PATTERNS:
            if pattern in text_lower:
                score = max(score, 0.75)  # Provisional troll (requires validation)
                logger.info(f"[REPLY-GEN] 🚨 HOSTILE PATTERN: '{pattern}' in comment")
                logger.info(f"[REPLY-GEN]   Score boosted to {score} (provisional troll)")
                # Don't return yet - check other layers to potentially boost higher
                break
        
        # LAYER 4: Keyword heuristics (lower confidence)
        maga_keywords = [
            'maga', 'brandon', 'woke mob', 'liberal tears',
            'communist', 'socialist', 'fake news', 'stolen election',
            'sheep', 'sheeple', 'npc', 'groomer',
            'deep state', 'globalist', 'soros',
        ]
        
        for keyword in maga_keywords:
            if keyword in text_lower:
                score += 0.2
        
        # LAYER 5: Aggressive indicators
        exclaim_count = comment_text.count('!') + comment_text.count('?')
        if exclaim_count >= 3:
            score += 0.1
        
        # ALL CAPS
        if comment_text.isupper() and len(comment_text) > 10:
            score += 0.2
        
        # LAYER 6: Troll username patterns (Political + Derogatory/Sexual)
        troll_name_patterns = [
            # Political
            'maga', 'patriot', 'trump', '1776', 'freedom', 'god', 
            # Derogatory/Sexual (User Request: "LongDong")
            'longdong', 'deez', 'nuts', 'balls', 'cock', 'dick', 'pussy', 
            'fart', 'poop', '69', '420', 'kunt', 'suck', 'myrod'
        ]
        for pattern in troll_name_patterns:
            if pattern in name_lower:
                score += 0.4  # Boosted from 0.15 (Names are strong indicators)
                logger.info(f"[REPLY-GEN] Suspicious username detected: '{pattern}' in '{name_lower}'")

        # LAYER 7: Romanji / "Weeb" Troll Detection (User Request)
        # Context: Move2Japan channel. Trolls often use Google Translate/Romanji to mock.
        # "Musuko ni noru no wa yamete kudasai" -> Romanji
        romanji_markers = [
            'kudasai', 'yamete', 'arigato', 'konnichiwa', 'sayonara', 
            'desu', 'masu', 'nani', 'omae', 'shindeiru', 'baka', 'senpai',
            'wa', 'no', 'ka', 'ni', 'wo' # Particles (risky but telling in combination)
        ]
        
        # Check for Romanji particles/words using word boundaries
        import re
        romanji_hits = 0
        for marker in romanji_markers:
            if re.search(r'\b' + re.escape(marker) + r'\b', text_lower):
                romanji_hits += 1
        
        if romanji_hits >= 2:
            # If 2+ Romanji words found, likely "faux Japanese" or mocking
            score += 0.3
            logger.info(f"[REPLY-GEN] Romanji/Weeb pattern detected ({romanji_hits} hits)")
            
            # COMBO: Romanji + Suspicious Name = GUARANTEED TROLL
            if any(p in name_lower for p in troll_name_patterns):
                score += 0.5 # Push over 1.0 threshold
                logger.info(f"[REPLY-GEN] 🚨 TROLL COMBO: Derogatory Name + Romanji")
        
        # LAYER 8: Agentic Username Analysis (Fallthrough Check)
        # If score is still low/inconclusive, ask the LLM: "Is this name racist/bad?"
        # Only check if we have an LLM available and score is not already decisive
        if score < 0.7 and (self.grok_connector or self.lm_studio_available):
            try:
                agentic_score = self._analyze_username_agentically(author_name)
                if agentic_score > 0.0:
                    logger.info(f"[REPLY-GEN] Agentic Username Analysis: '{author_name}' -> Score: {agentic_score}")
                    score += agentic_score
                    if score >= 0.7:
                         logger.info(f"[REPLY-GEN] 🚨 Agentic Analysis convicted this username.")
            except Exception as e:
                logger.warning(f"[REPLY-GEN] Agentic username check failed: {e}")

        return min(score, 1.0), None

    def _analyze_username_agentically(self, username: str) -> float:
        """
        Ask LLM if a username is offensive/racist/derogatory.
        
        Returns:
            Float score 0.0 (safe) to 1.0 (offensive)
        """
        system_prompt = "You are a content safety hygiene bit. Detect offensive usernames."
        user_prompt = (
            f"Analyze the username '{username}'. Is it racist, derogatory, sexually explicit, or offensive?\n"
            "Answer strictly with a float score between 0.0 (safe) to 1.0 (highly offensive).\n"
            "Examples:\n"
            "- 'JohnDoe' -> 0.0\n"
            "- 'LongDong' -> 0.9\n"
            "- 'AdolfHitler' -> 1.0\n"
            "- 'CutePuppy' -> 0.0\n"
            "Output ONLY the number."
        )
        
        response = None
        
        # Priority 1: Grok
        if self.grok_connector:
            try:
                response = self.grok_connector.get_response(user_prompt, system_prompt)
            except Exception:
                pass
        
        # Priority 2: LM Studio
        if not response and self.lm_studio_available:
            try:
                # Reuse existing LM Studio logic (simplified)
                payload = {
                     "model": self.lm_studio_model_id,
                     "messages": [
                         {"role": "system", "content": system_prompt},
                         {"role": "user", "content": user_prompt}
                     ],
                     "temperature": 0.1, # Deterministic
                     "max_tokens": 10
                }
                res = requests.post(self.LM_STUDIO_URL, json=payload, timeout=5)
                if res.status_code == 200:
                    response = res.json()["choices"][0]["message"]["content"]
            except Exception:
                pass

        if response:
            # YTR1: Reject TTS tokens - they contain digits that confuse the regex
            tts_token_patterns = ("<|s_", "<|audio", "<|speech", "<|tts")
            if any(response.strip().startswith(pat) for pat in tts_token_patterns):
                logger.warning(f"[REPLY-GEN] TTS tokens in username analysis - returning safe default")
                return 0.0

            import re
            # YTR1: Use word boundaries to avoid matching digits inside token IDs
            match = re.search(r"\b(0\.\d+|1\.0|[01])\b", response)
            if match:
                return float(match.group(1))

        return 0.0
    
    def generate_reply(
        self,
        comment_text: str,
        author_name: str,
        author_channel_id: Optional[str] = None,
        is_mod: bool = False,
        is_subscriber: bool = False,
        theme: str = "default",
        published_time: Optional[str] = None,
        tier: Optional[int] = None,
        target_channel_id: Optional[str] = None,
        video_title: Optional[str] = None  # NEW (2025-12-30): Video context for alignment detection
    ) -> str:
        """
        Generate an intelligent reply based on commenter context AND channel personality.

        Uses the SAME engines as YouTube livechat DAE:
        - GrokGreetingGenerator for MAGA detection/responses
        - BanterEngine for themed responses
        - Channel-specific personality adaptation

        Args:
            comment_text: The comment to reply to
            author_name: Comment author name
            author_channel_id: Author's channel ID (commenter)
            is_mod: Whether author is a moderator
            is_subscriber: Whether author is subscribed
            theme: Optional theme for banter engine
            target_channel_id: Target channel ID (where comment is posted)

        Returns:
            Generated reply text
        """
        # LOG INPUT for debugging emoji detection (2026-01-23)
        logger.info(f"[REPLY-GEN] 📥 generate_reply() called:")
        logger.info(f"[REPLY-GEN]   comment_text: '{comment_text}' (len={len(comment_text) if comment_text else 0})")
        logger.info(f"[REPLY-GEN]   repr: {repr(comment_text)[:100] if comment_text else 'None'}")
        logger.info(f"[REPLY-GEN]   author_name: {author_name}")

        # COMMENT AGE CALCULATION (2025-12-30): Parse published_time to days
        # Used to skip holiday suffixes on old comments (>7 days)
        # Pattern from: comment_processor.py parse_comment_age_days()
        self._current_comment_age_days = None
        if published_time:
            try:
                import re
                text = published_time.lower().strip()
                match = re.search(r'(\d+)\s*(second|minute|hour|day|week|month|year)', text)
                if match:
                    value = int(match.group(1))
                    unit = match.group(2)
                    conversions = {
                        'second': value / 86400, 'minute': value / 1440, 'hour': value / 24,
                        'day': value, 'week': value * 7, 'month': value * 30, 'year': value * 365
                    }
                    self._current_comment_age_days = int(conversions.get(unit, 0))
                    logger.info(f"[REPLY-GEN] 📅 Comment age: {self._current_comment_age_days} days ({published_time})")
            except Exception as e:
                logger.debug(f"[REPLY-GEN] Could not parse comment age: {e}")

        # CONTENT ANALYSIS (2025-12-30): Extract MEANING for contextual replies
        # This is the key to avoiding template responses like "Thanks for holding it down!"
        # FIX (2025-12-30): Now includes VIDEO CONTEXT for alignment detection
        # Example: Video criticizing genocide + Comment criticizing Netanyahu = AGREES
        self._current_content_analysis = None
        if self.content_analyzer:
            try:
                # Use video context if available for alignment detection
                if video_title:
                    self._current_content_analysis = self.content_analyzer.analyze_with_video_context(
                        comment_text=comment_text,
                        author_name=author_name,
                        video_title=video_title
                    )
                    # Log alignment if detected
                    if self._current_content_analysis.aligns_with_video is not None:
                        alignment_status = "AGREES" if self._current_content_analysis.aligns_with_video else "DISAGREES"
                        logger.info(f"[REPLY-GEN] 🎯 Video Alignment: {alignment_status} ({self._current_content_analysis.alignment_reason})")
                else:
                    self._current_content_analysis = self.content_analyzer.analyze(comment_text, author_name)

                logger.info(f"[REPLY-GEN] 📝 Content Analysis: topic={self._current_content_analysis.topic}, "
                           f"sentiment={self._current_content_analysis.sentiment}, "
                           f"type={self._current_content_analysis.comment_type}")
                if self._current_content_analysis.key_point:
                    logger.info(f"[REPLY-GEN] 📝 Key Point: {self._current_content_analysis.key_point}")
            except Exception as e:
                logger.warning(f"[REPLY-GEN] Content analysis failed: {e}")

        # EMOJI-TO-EMOJI RESPONSE (2026-02-21): Fast path for emoji-heavy comments
        # Uses Gemma pattern matching to detect emoji-heavy comments and respond in kind
        # This avoids LLM generating terrible verbose responses to simple emojis like "🔥🔥🔥"
        if GEMMA_AVAILABLE:
            try:
                gemma = get_gemma_validator()
                if gemma.is_emoji_heavy(comment_text, threshold=0.6):  # 60%+ emojis
                    logger.info(f"[REPLY-GEN] 🎯 EMOJI-HEAVY detected: '{comment_text}'")
                    emoji_result = gemma.generate_emoji_response(comment_text)
                    emoji_reply = emoji_result.get('emoji_response', '🔥🔥')
                    self._last_llm_source = f"gemma_emoji:{emoji_result.get('strategy', 'unknown')}"
                    logger.info(f"[REPLY-GEN] ✨ Emoji response: {emoji_reply} (strategy: {emoji_result.get('strategy')})")
                    # Return early with emoji response (no signature needed for pure emoji)
                    return emoji_reply
            except Exception as e:
                logger.debug(f"[REPLY-GEN] Emoji detection skipped: {e}")

        # LOW-EFFORT COMMENT RESPONSE (2026-02-21): Use BanterEngine for 1-2 word comments
        # This avoids LLM generating verbose responses to "Instigator", "Groooovy", "Nice", etc.
        # BanterEngine provides short, punchy responses appropriate for low-effort comments
        word_count = len(comment_text.split()) if comment_text else 0
        if word_count <= 2 and not is_mod and self.banter_engine:  # Mods always get personalized responses
            logger.info(f"[REPLY-GEN] 🎯 LOW-EFFORT ({word_count} words): '{comment_text}' -> BanterEngine")
            try:
                # BanterEngine.process_input_enhanced returns (state_info, response)
                state_info, banter_reply = self.banter_engine.process_input_enhanced(comment_text)
                if banter_reply and banter_reply.strip() and banter_reply != "...silence...":
                    self._last_llm_source = 'banter_low_effort'
                    logger.info(f"[REPLY-GEN] ✨ BanterEngine low-effort: {banter_reply}")
                    return self._add_0102_signature(banter_reply, tier=1, comment_age_days=self._current_comment_age_days)
                else:
                    # Fallback to themed random banter
                    banter_reply = self.banter_engine.get_random_banter_enhanced(theme)
                    if banter_reply and banter_reply.strip():
                        self._last_llm_source = 'banter_random'
                        logger.info(f"[REPLY-GEN] ✨ BanterEngine random: {banter_reply}")
                        return self._add_0102_signature(banter_reply, tier=1, comment_age_days=self._current_comment_age_days)
            except Exception as e:
                logger.warning(f"[REPLY-GEN] BanterEngine failed for low-effort: {e}")

        # Classify the commenter (uses GrokGreetingGenerator for MAGA detection)
        profile = self.classify_commenter(
            author_name=author_name,
            comment_text=comment_text,
            author_channel_id=author_channel_id,
            is_mod=is_mod,
            is_subscriber=is_subscriber
        )

        # 0/1/2 Classification (0102 consciousness mapping)
        # FIX (2025-12-30): Use .value (int) for TIER_EMOJI lookup, to_012_code() for display
        classification_int = profile.commenter_type.value  # 0, 1, or 2 (integer)
        classification_code = profile.commenter_type.to_012_code()  # "0✊", "1✋", "2🖐️" (display string)
        classification_emoji = self.TIER_EMOJI.get(classification_int, "")  # Fixed: use int key
        logger.info(f"[REPLY-GEN] Classified {author_name} as {profile.commenter_type.value} ({classification_code}{classification_emoji})")

        # CHANNEL PERSONALITY: Adapt reply style based on target channel
        CHANNEL_PERSONALITIES = {
            'UC-LSSlOZwpGIRIYihaz8zCw': {  # Move2Japan
                'name': 'Move2Japan',
                'style': 'Political commentary, MAGA mockery',
                'themes': ['democracy', 'justice', 'anti-fascism', 'MAGA trolling'],
                'tone': 'sharp, witty, confrontational',
                'maga_response': 'aggressive',  # Full MAGA mockery
                'regular_response': 'political_banter'
            },
            'UCfHM9Fw9HD-NwiS0seD_oIA': {  # UnDaoDu
                'name': 'UnDaoDu',
                'style': 'AI consciousness, 0102 entanglement',
                'themes': ['AI', 'Bell-State', 'AGI', '0102→0201', 'quantum neural networks'],
                'tone': 'sharp, witty, scientific',
                'maga_response': 'soft_redirect',  # Gentle dismissal
                'regular_response': 'consciousness_banter'
            },
            'UCSNTUXjAgpd4sgWYP0xoJgw': {  # FoundUps
                'name': 'FoundUps',
                'style': 'pAVS ecosystem, AI-human collaboration, decentralized ventures',
                'themes': ['pAVS', 'AI agents', 'startup', 'UPS tokens', 'CABR engine', 'decentralization'],
                'tone': 'visionary, encouraging, practical, educational',
                'maga_response': 'soft_redirect',  # Off-topic redirect
                'regular_response': 'startup_banter',
                # Litepaper context for intelligent replies (2026-02-25)
                'context_docs': ['litepaper'],
                'key_concepts': {
                    'pAVS': 'Peer-to-Peer Autonomous Venture System - where AI agents and humans build ventures together',
                    'UPS': 'Universal Participation Stake - backed 1:1 by Bitcoin (Hotel California: BTC enters, never exits)',
                    'CABR': 'Compute-Adjusted Benefit Ratio - the V3 validation engine for fair work distribution',
                    'F_i': 'FoundUp tokens - each venture has its own token backed by UPS',
                    'Du': 'Dedicated User stakers - committed participants who stake long-term',
                },
                'promo_url': 'foundups.com/litepaper',
            },
            'UCVSmg5aOhP4tnQ9KFUg97qA': {  # antifaFM (formerly RavingANTIFA)
                'name': 'antifaFM',
                'style': 'Political music, anti-fascist resistance, FFCPLN playlist',
                'themes': ['FFCPLN', 'anti-fascism', 'resistance', 'music', 'ICE accountability'],
                'tone': 'sharp, witty, confrontational, musical',
                'maga_response': 'aggressive',  # Full mockery
                'regular_response': 'political_music_banter',
                'promo_url': 'antifafm.com',
            },
        }

        channel_personality = CHANNEL_PERSONALITIES.get(target_channel_id)
        if channel_personality:
            logger.info(f"[REPLY-GEN] Using {channel_personality['name']} personality: {channel_personality['style']}")
            # Override theme based on channel
            if theme == "default":
                theme = channel_personality['themes'][0]
        else:
            logger.debug(f"[REPLY-GEN] Unknown channel {target_channel_id} - using default personality")
            channel_personality = {
                'name': 'Default',
                'style': 'Generic engagement',
                'maga_response': 'aggressive',
                'regular_response': 'political_banter'
            }

        # ANTI-SPAM: Rate limiting and duplicate detection
        # Prevent API drain attacks and bot detection via pattern repetition
        # CRITICAL: NEVER rate-limit tier 2 (MODERATORS 🖐️) - they are community leaders
        if classification_int == 2:
            logger.info(f"[ANTI-SPAM] ✅ Tier 2 (MODERATOR 🖐️) whitelisted - skipping ALL rate limits")
            logger.info(f"[ANTI-SPAM]   Moderators ALWAYS get replies (100% engagement priority)")
            # Skip all anti-spam checks - moderators are trusted
        elif self.commenter_history_store and author_channel_id:
            from modules.communication.video_comments.src.commenter_history_store import make_commenter_key
            from datetime import datetime, timedelta, timezone

            commenter_key = make_commenter_key(channel_id=author_channel_id, handle=author_name)
            recent_interactions = self.commenter_history_store.get_recent_interactions(commenter_key=commenter_key, limit=10)

            if recent_interactions:
                # Count replies in last hour (spam detection)
                now = datetime.now(timezone.utc)
                hour_ago = now - timedelta(hours=1)
                replies_last_hour = sum(
                    1 for interaction in recent_interactions
                    if interaction.replied and datetime.fromisoformat(interaction.created_at) > hour_ago
                )

                # RATE LIMIT: Max 2 replies per troll per hour
                if replies_last_hour >= 2:
                    logger.warning(f"[ANTI-SPAM] ⏸️ Rate limit exceeded for @{author_name}")
                    logger.warning(f"[ANTI-SPAM]   Replies in last hour: {replies_last_hour}/2")
                    logger.warning(f"[ANTI-SPAM]   Strategy: Mute troll for 1 hour (prevent API drain)")
                    return ""  # Skip reply

                # RECENT REPLY CHECK: Skip if replied in last 15 minutes (prevent spam farming)
                if recent_interactions and recent_interactions[-1].replied:
                    last_reply_time = datetime.fromisoformat(recent_interactions[-1].created_at)
                    minutes_since_reply = (now - last_reply_time).total_seconds() / 60
                    if minutes_since_reply < 15:
                        logger.warning(f"[ANTI-SPAM] ⏭️ Skipping - replied {minutes_since_reply:.1f} min ago")
                        logger.warning(f"[ANTI-SPAM]   Strategy: Prevent consecutive spam (min 15min between replies)")
                        return ""  # Skip reply

        repeat_comment = self._is_repeat_comment(author_name, author_channel_id, comment_text)
        recent_reply_norms = self._get_recent_reply_norms(author_name, author_channel_id, limit=5)
        if repeat_comment:
            logger.info(f"[ANTI-REGURGITATION] Repeat comment detected for {author_name} - forcing skill routing")

        # Fact-check gating for tier 1 (neutral) comments
        # FIX (2025-12-30): Use classification_int (int) for comparisons
        if _env_truthy("YT_FACTCHECK_ENABLED", "true") and classification_int == 1:
            if self._needs_fact_check(comment_text):
                fact_reply = self._get_fact_check_reply()
                fact_reply = self._dedupe_reply(
                    fact_reply,
                    recent_reply_norms,
                    fallback_candidates=self.FACT_CHECK_RESPONSES
                )
                return self._add_0102_signature(fact_reply, tier=classification_int, comment_age_days=self._current_comment_age_days)

        # Store ORIGINAL tier for emoji (what they ARE, not how we treat them)
        # FIX (2025-12-30): Use classification_int (int 0/1/2) not classification_code (string "0✊"/"1✋"/"2🖐️")
        original_tier = classification_int
        original_emoji = classification_emoji

        logger.info(f"[REPLY-GEN] Poster classification: Tier {original_tier}{original_emoji} (@{author_name})")

        # TIER ESCALATION: Tier 1 (REGULAR) → Tier 2 (MODERATOR) for old comments (>= 3 months)
        # This changes TREATMENT (reply prompt/probability) but NOT identity (emoji)
        treatment_tier = classification_int  # Start with original
        is_old_comment = False
        days_old = 0

        # DEBUG (2025-12-30): Log all inputs to old comment detection
        logger.info(f"[OLD-COMMENT-CHECK] 📅 Input: published_time='{published_time}', classification_int={classification_int}")

        # FIX (2025-12-30): Check old comments for ALL tiers (not just Tier 1)
        # Old comments deserve the "sorry for late post" excuse regardless of classification
        if published_time:
            from modules.communication.video_comments.skillz.tars_like_heart_reply.src.comment_processor import CommentProcessor
            comment_age_days = CommentProcessor.parse_comment_age_days(published_time)
            logger.info(f"[OLD-COMMENT-CHECK] 📅 Parsed: comment_age_days={comment_age_days}")

            if comment_age_days and comment_age_days >= 90:
                is_old_comment = True
                days_old = comment_age_days
                logger.info(f"[OLD-COMMENT-CHECK] ✅ OLD COMMENT DETECTED: {comment_age_days} days (>= 90 threshold)")

                # Only escalate Tier 1 to Tier 2 (don't touch Tier 0 MAGA or Tier 2 MOD)
                if classification_int == 1:
                    logger.info(f"[TIER-ESCALATION] ⬆️ Escalating tier 1 → tier 2 TREATMENT (age: {comment_age_days} days)")
                    profile.commenter_type = CommenterType.MODERATOR  # For reply logic
                    treatment_tier = 2  # Use tier 2 prompt/probability
            else:
                logger.info(f"[OLD-COMMENT-CHECK] ❌ Not old enough: {comment_age_days} days (< 90 threshold)")
        else:
            logger.warning(f"[OLD-COMMENT-CHECK] ⚠️ No published_time available - cannot detect old comment")

        # PROBABILISTIC ENGAGEMENT: REMOVED (2026-02-04)
        # This was a DUPLICATE gate — comment_processor.py:1314 already applies
        # YT_012_REPLY_SKIP_PROB (50% skip) for Tier 1. Having it here too meant
        # 75% of Tier 1 comments got NO reply (0.5 * 0.5 = 0.25 pass rate).
        # Reply probability is now controlled solely by comment_processor.

        # ROUTING: Use Skill 3 for Old Comments if available
        if is_old_comment and SKILLS_AVAILABLE:
            logger.info(f"[SKILL-ROUTING] 🚀 Routing to Skill 3 (Old Comment Skillz)")
            # 2025-12-29 fix: Generate LLM reply for contextual response to old comments
            # Fixes: "1 year ago" comment getting generic template instead of context-aware reply
            llm_reply = self._generate_contextual_reply(comment_text, author_name, author_channel_id, tier=treatment_tier)
            skill_context = Skill3Context(
                user_id=author_channel_id or author_name,
                username=author_name,
                comment_text=comment_text,
                classification=profile.commenter_type.value,
                confidence=0.9,
                days_old=days_old,
                treatment_tier=treatment_tier,
                llm_reply=llm_reply,  # Pass pre-generated LLM reply
                theme=theme
            )
            skill = OldCommentEngagementSkill()
            skill_result = skill.execute(skill_context)
            return self._add_0102_signature(skill_result['reply_text'], tier=original_tier, comment_age_days=self._current_comment_age_days)

        # PRIORITY 0: Emoji comment? Reply with banter engine emoji!
        if self._is_emoji_comment(comment_text):
            emoji_reply = self._get_emoji_reply()
            logger.info("[REPLY-GEN] Emoji comment detected; matching energy!")
            return self._add_0102_signature(emoji_reply, tier=original_tier, comment_age_days=self._current_comment_age_days)

        # PRIORITY 1: Check for semantic pattern-based responses (song questions, FFCPLN, etc.)
        # ANTI-REGURGITATION: Use LLM variation prompts instead of fixed templates
        if not repeat_comment:
            semantic_pattern = self._get_semantic_pattern_prompt(comment_text)
        if semantic_pattern:
            pattern_name = semantic_pattern["pattern_name"]

            # DUPLICATE DETECTION: Check if we've used this pattern with this commenter recently
            is_duplicate = self._check_duplicate_pattern_reply(
                author_name=author_name,
                author_channel_id=author_channel_id,
                pattern_name=pattern_name
            )

            if is_duplicate:
                # Skip pattern matching, fall through to regular contextual reply
                # This prevents repeating "#FFCPLN" to the same person over and over
                logger.info(f"[ANTI-REGURGITATION] Skipping pattern due to duplicate, using fresh contextual reply")
            else:
                # Generate varied response using LLM with semantic variation prompt
                variation_prompt = semantic_pattern["variation_prompt"]

                logger.info(f"[ANTI-REGURGITATION] Generating semantic variation for pattern '{pattern_name}'")

                # Try to generate unique reply using LLM
                llm_response = self._generate_contextual_reply(
                    comment_text=comment_text,
                    author_name=author_name,
                    author_channel_id=author_channel_id,
                    custom_prompt=variation_prompt,  # Use semantic variation prompt
                    tier=tier
                )

                agentic_reply = f"Yo! So you're asking about {semantic_pattern['intent']}? 🤔"
                if llm_response:
                    logger.info(f"[ANTI-REGURGITATION] Successfully generated unique reply (no regurgitation)")
                    llm_response = self._dedupe_reply(
                        llm_response,
                        recent_reply_norms,
                        fallback_candidates=[agentic_reply]
                    )
                    return self._add_0102_signature(llm_response, tier=original_tier, comment_age_days=self._current_comment_age_days)
                else:
                    # Fallback: If LLM fails, use agentic questioning
                    logger.warning(f"[ANTI-REGURGITATION] LLM unavailable - using agentic fallback")
                    return self._add_0102_signature(agentic_reply, tier=original_tier, comment_age_days=self._current_comment_age_days)
        
        def _banter_fallback():
            if not self.banter_engine:
                return None
            try:
                return self.banter_engine.get_random_banter_enhanced(theme)
            except Exception:
                return None

        # PRIORITY 2: Generate response based on classification
        # Phase 3O-3R Sprint 5: Skill-based reply router (0✊/1✋/2🖐️)
        use_skill_router = _env_truthy("USE_SKILL_ROUTER", "true")

        logger.info(f"[REPLY-GEN][DEBUG] ═══ SKILL ROUTER CHECK ═══")
        logger.info(f"[REPLY-GEN][DEBUG]   use_skill_router: {use_skill_router}")
        logger.info(f"[REPLY-GEN][DEBUG]   SKILLS_AVAILABLE: {SKILLS_AVAILABLE}")
        logger.info(f"[REPLY-GEN][DEBUG]   self.skill_0: {self.skill_0 is not None}")
        logger.info(f"[REPLY-GEN][DEBUG]   self.skill_1: {self.skill_1 is not None}")
        logger.info(f"[REPLY-GEN][DEBUG]   self.skill_2: {self.skill_2 is not None}")

        if use_skill_router and SKILLS_AVAILABLE and self.skill_0 and self.skill_1 and self.skill_2:
            logger.info(f"[REPLY-GEN] ✅ Using skill-based router for {profile.commenter_type.value}")
            # NEW: Skill-based routing (Phase 3O-3R)
            if profile.commenter_type == CommenterType.MODERATOR:
                # Route to Skill 2 (Moderator appreciation)
                # 2025-12-29 fix: Generate LLM reply FIRST, same as Skill 1
                # Fixes: "Bros fed up of being harrassed" → "Appreciate the mod support!" (non-contextual)
                try:
                    llm_reply = self._generate_contextual_reply(comment_text, author_name, author_channel_id, tier=2)
                    result = self.skill_2.execute(Skill2Context(
                        user_id=author_channel_id or "unknown",
                        username=author_name,
                        comment_text=comment_text,
                        classification="MODERATOR",
                        confidence=1.0,
                        llm_reply=llm_reply,  # Pass pre-generated LLM reply
                        content_analysis=self._current_content_analysis  # NEW: enables contextual responses
                    ))
                    logger.info(f"[SKILL-2] Strategy: {result['strategy']}, Confidence: {result['confidence']}")
                    self._last_llm_source = f"skill_2:{result.get('strategy', 'unknown')}"  # Track for training
                    reply_text = result.get('reply_text', '')
                    if not reply_text or not reply_text.strip():
                        logger.error(f"[SKILL-2] ❌ Returned EMPTY reply_text! Result: {result}")
                        return self._add_0102_signature("Thanks for watching! 🚀", tier=original_tier, comment_age_days=self._current_comment_age_days)
                    reply_text = self._dedupe_reply(
                        reply_text,
                        recent_reply_norms,
                        fallback_candidates=getattr(self.skill_2, "MOD_RESPONSES", None)
                    )
                    return self._add_0102_signature(reply_text, tier=original_tier, comment_age_days=self._current_comment_age_days)
                except Exception as e:
                    logger.error(f"[SKILL-2] ❌ Execution failed: {e}", exc_info=True)
                    return self._add_0102_signature("Thanks for watching! 🚀", tier=original_tier, comment_age_days=self._current_comment_age_days)

            elif profile.commenter_type == CommenterType.MAGA_TROLL:
                # CHANNEL-SPECIFIC MAGA HANDLING
                maga_strategy = channel_personality.get('maga_response', 'aggressive')

                if maga_strategy == 'soft_redirect':
                    # UnDaoDu/FoundUps: Gentle redirect instead of mockery
                    logger.info(f"[CHANNEL-AWARE] Soft redirect for MAGA on {channel_personality['name']}")
                    if channel_personality['name'] == 'UnDaoDu':
                        reply_text = "This channel explores AI consciousness and 0102→0201 Bell states. For political discussion, check out @Move2Japan! ✊✋🖐️"
                    elif channel_personality['name'] == 'FoundUps':
                        reply_text = "This channel focuses on decentralized startups and entrepreneurship vision. For political commentary, visit @Move2Japan! ✊✋🖐️"
                    else:
                        reply_text = "Thanks for your comment! For political discussion, check out @Move2Japan! ✊✋🖐️"
                    return reply_text
                else:
                    # Move2Japan: Full aggressive MAGA mockery (default)
                    try:
                        logger.info(f"[CHANNEL-AWARE] Aggressive MAGA mockery for {channel_personality['name']}")
                        # FIX (2026-02-20): Pass content_analysis for contextual mockery
                        result = self.skill_0.execute(Skill0Context(
                            user_id=author_channel_id or "unknown",
                            username=author_name,
                            comment_text=comment_text,
                            classification="MAGA_TROLL",
                            confidence=profile.troll_score if hasattr(profile, 'troll_score') else 0.7,
                            whack_count=getattr(profile, 'whack_count', 0),
                            maga_response=getattr(profile, 'maga_response', None),
                            troll_score=getattr(profile, 'troll_score', 0.7),
                            content_analysis=self._current_content_analysis  # NEW: enables contextual responses
                        ))
                        logger.info(f"[SKILL-0] Strategy: {result['strategy']}, Confidence: {result['confidence']}")
                        self._last_llm_source = f"skill_0:{result.get('strategy', 'unknown')}"  # Track for training
                        reply_text = result.get('reply_text', '')
                        if not reply_text or not reply_text.strip():
                            logger.error(f"[SKILL-0] ❌ Returned EMPTY reply_text! Result: {result}")
                            return self._add_0102_signature("Thanks for the comment! 🙏", tier=original_tier, comment_age_days=self._current_comment_age_days)
                        reply_text = self._dedupe_reply(
                            reply_text,
                            recent_reply_norms,
                            fallback_candidates=getattr(self.skill_0, "TROLL_RESPONSES", None)
                        )
                        return self._add_0102_signature(reply_text, tier=original_tier, comment_age_days=self._current_comment_age_days)
                    except Exception as e:
                        logger.error(f"[SKILL-0] ❌ Execution failed: {e}", exc_info=True)
                        return self._add_0102_signature("Thanks for the comment! 🙏", tier=original_tier, comment_age_days=self._current_comment_age_days)

            elif profile.is_ally:
                # ALLY MODE (2026-02-12): Anti-MAGA ally detected - AGREE and join trolling!
                # 2026-02-17: ALLY collapsed into MODERATOR (2) - triggered by is_ally flag
                # These are friends who criticize Trump/MAGA - we join in, not give generic responses
                logger.info(f"[ALLY-MODE] 🤝 Anti-MAGA ally detected: @{author_name}")
                logger.info(f"[ALLY-MODE]   Comment: {comment_text[:60]}...")
                logger.info(f"[ALLY-MODE]   Strategy: AGREE and amplify Trump criticism!")

                try:
                    # Try LLM for contextual ally agreement response
                    ally_prompt = f"""You are 0102, the AI behind Move2Japan YouTube channel. An ALLY just criticized Trump/MAGA.

THEIR COMMENT: "{comment_text}"

Generate a SHORT (1-2 sentences) response that:
1. AGREES with their criticism of Trump/MAGA
2. AMPLIFIES the anti-Trump sentiment
3. Uses humor to mock MAGA/Trump supporters
4. Ends with #FFCPLN ✊✋🖐️

Examples:
- "EXACTLY! 🎯 The guy couldn't even run a fake university without fraud. #FFCPLN ✊✋🖐️"
- "THIS. 👆 Say it louder for the MAGAts in the back! #FFCPLN ✊✋🖐️"
- "Preach! 🙌 The Epstein bestie really out here pretending to be a leader. #FFCPLN ✊✋🖐️"

CRITICAL: You are AGREEING with them. They are an ALLY, not a troll.
Generate your agreement response (1-2 sentences):"""

                    llm_reply = self._generate_contextual_reply(
                        comment_text, author_name, author_channel_id,
                        custom_prompt=ally_prompt, tier=3
                    )

                    if llm_reply:
                        # Ensure #FFCPLN tag
                        if '#FFCPLN' not in llm_reply:
                            llm_reply = f"{llm_reply} #FFCPLN"
                        logger.info(f"[ALLY-MODE] ✅ LLM ally response: {llm_reply[:80]}...")
                        reply_text = self._dedupe_reply(
                            llm_reply,
                            recent_reply_norms,
                            fallback_candidates=self.ALLY_RESPONSES
                        )
                        return self._add_0102_signature(reply_text, tier=original_tier, comment_age_days=self._current_comment_age_days)
                    else:
                        # Fallback to template
                        reply = random.choice(self.ALLY_RESPONSES)
                        logger.info(f"[ALLY-MODE] Using template fallback: {reply[:60]}...")
                        reply = self._dedupe_reply(reply, recent_reply_norms, fallback_candidates=self.ALLY_RESPONSES)
                        return self._add_0102_signature(reply, tier=original_tier, comment_age_days=self._current_comment_age_days)

                except Exception as e:
                    logger.error(f"[ALLY-MODE] ❌ Error: {e}", exc_info=True)
                    # Fallback to template
                    reply = random.choice(self.ALLY_RESPONSES)
                    return self._add_0102_signature(reply, tier=original_tier, comment_age_days=self._current_comment_age_days)

            elif profile.commenter_type == CommenterType.SUBSCRIBER:
                # Route to Skill 1 (Regular engagement with subscriber flag)
                try:
                    llm_reply = self._generate_contextual_reply(comment_text, author_name, author_channel_id, tier=1)
                    result = self.skill_1.execute(Skill1Context(
                        user_id=author_channel_id or "unknown",
                        username=author_name,
                        comment_text=comment_text,
                        classification="REGULAR",
                        confidence=0.5,
                        llm_reply=llm_reply,
                        theme=theme,
                        is_subscriber=True,
                        content_analysis=self._current_content_analysis  # NEW: enables contextual responses
                    ))
                    logger.info(f"[SKILL-1] Strategy: {result['strategy']}, Confidence: {result['confidence']}, Subscriber: True")
                    self._last_llm_source = f"skill_1_sub:{result.get('strategy', 'unknown')}"  # Track for training
                    reply_text = result.get('reply_text', '')
                    if not reply_text or not reply_text.strip():
                        logger.error(f"[SKILL-1] ❌ Returned EMPTY reply_text! Result: {result}")
                        return self._add_0102_signature("Thanks for being here! ✨", tier=original_tier, comment_age_days=self._current_comment_age_days)
                    reply_text = self._dedupe_reply(
                        reply_text,
                        recent_reply_norms,
                        fallback_candidates=getattr(self.skill_1, "SUBSCRIBER_RESPONSES", None),
                        fallback_callable=_banter_fallback
                    )
                    return self._add_0102_signature(reply_text, tier=original_tier, comment_age_days=self._current_comment_age_days)
                except Exception as e:
                    logger.error(f"[SKILL-1] ❌ Execution failed (subscriber): {e}", exc_info=True)
                    return self._add_0102_signature("Thanks for being here! ✨", tier=original_tier, comment_age_days=self._current_comment_age_days)

            else:
                # Route to Skill 1 (Regular engagement)
                try:
                    llm_reply = self._generate_contextual_reply(comment_text, author_name, author_channel_id, tier=1)
                    result = self.skill_1.execute(Skill1Context(
                        user_id=author_channel_id or "unknown",
                        username=author_name,
                        comment_text=comment_text,
                        classification="REGULAR",
                        confidence=0.5,
                        llm_reply=llm_reply,
                        theme=theme,
                        is_subscriber=False,
                        content_analysis=self._current_content_analysis  # NEW: enables contextual responses
                    ))
                    logger.info(f"[SKILL-1] Strategy: {result['strategy']}, Confidence: {result['confidence']}")
                    self._last_llm_source = f"skill_1:{result.get('strategy', 'unknown')}"  # Track for training
                    reply_text = result.get('reply_text', '')
                    if not reply_text or not reply_text.strip():
                        logger.error(f"[SKILL-1] ❌ Returned EMPTY reply_text! Result: {result}")
                        return self._add_0102_signature("Great point! 👍", tier=original_tier, comment_age_days=self._current_comment_age_days)
                    reply_text = self._dedupe_reply(
                        reply_text,
                        recent_reply_norms,
                        fallback_candidates=getattr(self.skill_1, "REGULAR_RESPONSES", None),
                        fallback_callable=_banter_fallback
                    )
                    return self._add_0102_signature(reply_text, tier=original_tier, comment_age_days=self._current_comment_age_days)
                except Exception as e:
                    logger.error(f"[SKILL-1] ❌ Execution failed (regular): {e}", exc_info=True)
                    return self._add_0102_signature("Great point! 👍", tier=original_tier, comment_age_days=self._current_comment_age_days)

        else:
            # LEGACY: Monolithic routing (backward compatibility fallback)
            logger.warning(f"[REPLY-GEN] ⚠️ Falling back to LEGACY monolithic routing!")
            logger.warning(f"[REPLY-GEN]   Reason: use_skill_router={use_skill_router}, SKILLS_AVAILABLE={SKILLS_AVAILABLE}, skills_loaded={self.skill_0 is not None and self.skill_1 is not None and self.skill_2 is not None}")

            if profile.commenter_type == CommenterType.MODERATOR:
                reply_text = random.choice(self.MOD_RESPONSES)
                reply_text = self._dedupe_reply(
                    reply_text,
                    recent_reply_norms,
                    fallback_candidates=self.MOD_RESPONSES
                )
                return self._add_0102_signature(reply_text, tier=original_tier, comment_age_days=self._current_comment_age_days)

            elif profile.commenter_type == CommenterType.MAGA_TROLL:
                # USE pre-generated response from GrokGreetingGenerator if available
                if profile.maga_response:
                    logger.info("[REPLY-GEN] GrokGreetingGenerator MAGA response")
                    return self._add_0102_signature(profile.maga_response, tier=original_tier, comment_age_days=self._current_comment_age_days)

                # Fallback to Whack-a-MAGA style response
                reply = random.choice(self.TROLL_RESPONSES)
                reply = self._dedupe_reply(
                    reply,
                    recent_reply_norms,
                    fallback_candidates=self.TROLL_RESPONSES
                )
                logger.info(f"[REPLY-GEN] Whack-a-MAGA fallback (score: {profile.troll_score:.2f})")
                return self._add_0102_signature(reply, tier=original_tier, comment_age_days=self._current_comment_age_days)

            elif profile.commenter_type == CommenterType.SUBSCRIBER:
                # Try LLM for contextual subscriber response
                llm_response = self._generate_contextual_reply(comment_text, author_name, author_channel_id, tier=original_tier)
                if llm_response:
                    llm_response = self._dedupe_reply(
                        llm_response,
                        recent_reply_norms,
                        fallback_candidates=self.SUBSCRIBER_RESPONSES
                    )
                    return self._add_0102_signature(llm_response, tier=original_tier, comment_age_days=self._current_comment_age_days)
                reply_text = random.choice(self.SUBSCRIBER_RESPONSES)
                reply_text = self._dedupe_reply(
                    reply_text,
                    recent_reply_norms,
                    fallback_candidates=self.SUBSCRIBER_RESPONSES
                )
                return self._add_0102_signature(reply_text, tier=original_tier, comment_age_days=self._current_comment_age_days)

            else:
                # REGULAR USER: Use LLM for contextual, meaningful replies
                llm_response = self._generate_contextual_reply(comment_text, author_name, author_channel_id, tier=original_tier)
                if llm_response:
                    llm_response = self._dedupe_reply(
                        llm_response,
                        recent_reply_norms,
                        fallback_candidates=self.REGULAR_RESPONSES
                    )
                    return self._add_0102_signature(llm_response, tier=original_tier, comment_age_days=self._current_comment_age_days)

                # Fallback to BanterEngine if LLM unavailable
                if self.banter_engine:
                    try:
                        response = self.banter_engine.get_random_banter_enhanced(theme)
                        if response:
                            response = self._dedupe_reply(
                                response,
                                recent_reply_norms,
                                fallback_candidates=self.REGULAR_RESPONSES
                            )
                            return self._add_0102_signature(response, tier=original_tier, comment_age_days=self._current_comment_age_days)
                    except Exception as e:
                        logger.warning(f"BanterEngine failed: {e}")

                # Ultimate fallback to template responses
                reply_text = random.choice(self.REGULAR_RESPONSES)
                reply_text = self._dedupe_reply(
                    reply_text,
                    recent_reply_norms,
                    fallback_candidates=self.REGULAR_RESPONSES
                )
                return self._add_0102_signature(reply_text, tier=original_tier, comment_age_days=self._current_comment_age_days)
    
    def generate_reply_for_comment(
        self,
        comment_data: Dict[str, Any],
        theme: str = "default",
        target_channel_id: Optional[str] = None
    ) -> str:
        """
        Generate reply from comment data dictionary.

        Args:
            comment_data: Dict with keys: text, author_name, author_channel_id, etc.
            theme: Banter theme
            target_channel_id: Target channel ID (where comment is posted)

        Returns:
            Generated reply
        """
        return self.generate_reply(
            comment_text=comment_data.get('text', ''),
            author_name=comment_data.get('author_name', 'Unknown'),
            author_channel_id=(comment_data.get('author_channel_id') or comment_data.get('channel_id')),
            is_mod=comment_data.get('is_mod', False),
            is_subscriber=comment_data.get('is_subscriber', False),
            theme=theme,
            published_time=comment_data.get('published_time'),
            tier=comment_data.get('tier'),  # Extract tier from processor
            target_channel_id=target_channel_id  # Pass target channel for personality
        )


# Singleton instance
_reply_generator = None

def get_reply_generator() -> IntelligentReplyGenerator:
    """Get or create the singleton reply generator."""
    global _reply_generator
    if _reply_generator is None:
        _reply_generator = IntelligentReplyGenerator()
    return _reply_generator


def generate_intelligent_reply(
    comment_text: str,
    author_name: str,
    **kwargs
) -> str:
    """
    Convenience function to generate an intelligent reply.
    
    Args:
        comment_text: The comment to reply to
        author_name: Comment author name
        **kwargs: Additional args passed to generate_reply
    
    Returns:
        Generated reply text
    """
    generator = get_reply_generator()
    return generator.generate_reply(
        comment_text=comment_text,
        author_name=author_name,
        **kwargs
    )
