"""
Message Processor Component

Handles message processing, emoji detection, and response generation.
Separated from the main LiveChatListener for better maintainability.

NAVIGATION: Central message routing hub (685 lines - needs refactor!)
-> Called by: livechat_core.py processes batch messages here
-> Consciousness: consciousness_handler.py handles ✊✋🖐 triggers
-> Commands: command_handler.py handles /slash commands
-> Events: event_handler.py handles timeouts, bans
-> AI Response: llm_integration.py (Grok), agentic_chat_engine.py
-> PQN Integration: Lines 318-319 check for PQN commands
-> Quick ref: NAVIGATION.py -> MODULE_GRAPH['core_flows']['message_processing_flow']

WSP 17 Pattern Registry: This is a REUSABLE PATTERN
- Documented in: modules/communication/PATTERN_REGISTRY.md
- Pattern: Multi-stage message processing pipeline
- Stages: Rate limit -> Command detection -> Consciousness -> Response generation -> Throttle
- Reusable for: LinkedIn, X/Twitter, Discord, Twitch

MESSAGE PROCESSING PRIORITY SYSTEM:
Priority 0: Fact-check commands with consciousness emojis (✊✋🖐) - HIGHEST PRIORITY
Priority 1: PQN Research Commands (!pqn, !research, /pqn, /research)
Priority 2: AGENTIC consciousness responses (✊✋🖐 triggers)
Priority 3: Regular fact-check commands (factcheck @user, fc @user)
Priority 4: Whack gamification commands (/score, /level, /quiz, /whacked, etc.)
Priority 4.5: Troll callout - mock known trolls (3+ whacks) on first message
Priority 4.6: Top whacker greeting - welcome mods/high scorers on first message
Priority 5: MAGA content responses
Priority 6: Regular emoji triggers
Priority 7: Proactive engagement (mods/owners only)
Priority 8: Stream greeting (once per stream)
"""

import logging
import time
import os
import re
from typing import Dict, Any, Optional, List, Tuple
from modules.ai_intelligence.banter_engine.src.banter_singleton import get_banter_engine
from modules.communication.livechat.src.llm_bypass_engine import LLMBypassEngine
from modules.ai_intelligence.banter_engine.src.emoji_sequence_map import EMOJI_TO_NUMBER as EMOJI_TO_NUM
from modules.communication.livechat.src.llm_integration import GrokIntegration
from modules.communication.livechat.src.consciousness_handler import ConsciousnessHandler
from modules.ai_intelligence.banter_engine.src.agentic_sentiment_0102 import AgenticSentiment0102
from modules.communication.livechat.src.event_handler import EventHandler
from modules.communication.livechat.src.command_handler import CommandHandler

# Move2Japan FoundUp handler (WSP 95 - Skillz Wardrobe)
try:
    from modules.communication.livechat.src.m2j_handler import Move2JapanHandler
except ImportError:
    Move2JapanHandler = None
from modules.communication.livechat.src.greeting_generator import GrokGreetingGenerator
from modules.communication.livechat.src.persona_registry import get_persona_config, get_persona_greeting
from modules.gamification.whack_a_magat.src.self_improvement import get_self_improvement
from modules.communication.livechat.src.agentic_chat_engine import AgenticChatEngine
from modules.communication.livechat.src.intelligent_livechat_reply import get_livechat_reply_generator
from modules.infrastructure.shared_utilities.youtube_channel_registry import get_channel_ids
try:
    from modules.communication.livechat.src.emoji_response_limiter import EmojiResponseLimiter
    from modules.communication.livechat.src.agentic_self_improvement import AgenticSelfImprovement
except ImportError:
    EmojiResponseLimiter = None
    AgenticSelfImprovement = None

# Optional PQN Research module
try:
    from modules.ai_intelligence.pqn_alignment.src.pqn_research_dae_orchestrator import PQNResearchDAEOrchestrator
except ImportError:
    PQNResearchDAEOrchestrator = None

logger = logging.getLogger(__name__)

def _env_truthy(name: str, default: str = "false") -> bool:
    try:
        return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "y", "on")
    except Exception:
        return default.strip().lower() in ("1", "true", "yes", "y", "on")

def _sanitize_username(username: str) -> str:
    if not username:
        return username
    return username.strip().lstrip("@")


def _get_known_bot_channel_ids() -> List[str]:
    channel_ids = set(get_channel_ids())
    for env_name in (
        "FOUNDUPS_CHANNEL_ID",
        "UNDAODU_CHANNEL_ID",
        "MOVE2JAPAN_CHANNEL_ID",
        "ANTIFAFM_CHANNEL_ID",
    ):
        channel_id = os.getenv(env_name, "").strip()
        if channel_id:
            channel_ids.add(channel_id)
    return sorted(channel_ids)

class MessageProcessor:
    """Handles processing of chat messages and generating responses."""
    
    def __init__(
        self,
        youtube_service=None,
        memory_manager=None,
        chat_sender=None,
        persona_key: Optional[str] = None,
        channel_name: Optional[str] = None,
        channel_id: Optional[str] = None,
        bot_channel_id: Optional[str] = None,
        stream_title: Optional[str] = None,
    ):
        self.youtube_service = youtube_service
        self.memory_manager = memory_manager  # WSP-compliant hybrid storage
        self.chat_sender = chat_sender  # To access bot channel ID and prevent self-responses
        self.persona_key = persona_key
        self.channel_name = channel_name
        self.channel_id = channel_id
        self.bot_channel_id = bot_channel_id
        self.stream_title = stream_title
        self.persona_config = get_persona_config(
            persona_key=persona_key,
            channel_name=channel_name,
            channel_id=channel_id,
            bot_channel_id=bot_channel_id,
            stream_title=stream_title,
        )
        self.banter_enabled = _env_truthy("LIVECHAT_BANTER_ENABLED", "false")
        self.banter_engine = get_banter_engine() if self.banter_enabled else None
        self.llm_bypass_engine = LLMBypassEngine()
        self.trigger_emojis = ["✊", "👊", "✋", "🖐️"]  # Configurable emoji trigger set
        self.last_trigger_time = {}  # Track last trigger time per user
        self.last_maga_time = {}  # Track last MAGA response time per user
        self.last_global_maga_time = 0  # Global MAGA response cooldown
        self.trigger_cooldown = 60  # Cooldown period in seconds
        self.maga_cooldown = 600  # MAGA response cooldown (10 minutes to prevent spam)
        self.global_maga_cooldown = 300  # Global cooldown: 5 minutes between ANY MAGA responses
        self.memory_dir = "memory"
        # Consciousness response mode: 'mod_only' or 'everyone' (default: mod_only)
        self.consciousness_mode = os.getenv("YT_CONSCIOUSNESS_MODE", "mod_only").strip().lower()
        # Initialize handlers (WSP-compliant separation)
        self.event_handler = EventHandler(self.memory_dir)
        self.command_handler = CommandHandler(self.event_handler.get_timeout_manager(), self)
        # WSP 84 compliant: Use existing modules, not duplicate code
        self.greeting_generator = GrokGreetingGenerator()
        # Lazy, toggleable singleton (avoids duplicate disk/memory init)
        self.self_improvement = get_self_improvement()
        
        # NEW: Intelligent livechat reply generator (Grok-powered)
        self.intelligent_reply = get_livechat_reply_generator(
            persona_key=persona_key,
            channel_name=channel_name,
            channel_id=channel_id,
            bot_channel_id=bot_channel_id,
            stream_title=stream_title,
        )
        
        # NEW: Intelligent throttling systems
        self.emoji_limiter = EmojiResponseLimiter() if EmojiResponseLimiter else None
        self.agentic_improvement = AgenticSelfImprovement() if AgenticSelfImprovement else None
        
        # Initialize Grok and consciousness handlers FIRST
        # Try to get LLMConnector for Grok, otherwise use simple fact checker
        try:
            from modules.ai_intelligence.rESP_o1o2.src.llm_connector import LLMConnector
            # Check for Grok/xAI API key
            if os.environ.get("GROK_API_KEY") or os.environ.get("XAI_API_KEY"):
                # Use Grok 3 - latest flagship model with enhanced consciousness capabilities
                llm_connector = LLMConnector(model="grok-3")  
                self.grok = GrokIntegration(llm_connector)
                logger.info("[OK] Grok 3 LLM integration initialized - 0102 consciousness online!")
            else:
                logger.warning("No Grok API key found, using SimpleFactChecker fallback")
                from modules.communication.livechat.src.simple_fact_checker import SimpleFactChecker
                self.simple_fact_checker = SimpleFactChecker(self.memory_dir)
                self.grok = None
        except Exception as e:
            logger.warning(f"Could not initialize Grok LLM: {e}, using SimpleFactChecker")
            # Fallback to simple fact checker
            from modules.communication.livechat.src.simple_fact_checker import SimpleFactChecker
            self.simple_fact_checker = SimpleFactChecker(self.memory_dir)
            self.grok = None
            
        self.sentiment_engine = AgenticSentiment0102()
        self.consciousness = ConsciousnessHandler(self.sentiment_engine, self.grok)

        # Now initialize agentic engine with consciousness handler and memory manager
        self.agentic_engine = AgenticChatEngine(self.memory_dir, self.consciousness, memory_manager)

        # Initialize PQN Research Orchestrator if available
        self.pqn_orchestrator = None
        if PQNResearchDAEOrchestrator:
            try:
                self.pqn_orchestrator = PQNResearchDAEOrchestrator()
                logger.info("🔬 PQN Research DAE Orchestrator connected to chat")
            except Exception as e:
                logger.warning(f"Could not initialize PQN orchestrator: {e}")
                self.pqn_orchestrator = None

        # Intelligent throttle manager (set by LiveChatCore after initialization)
        self.intelligent_throttle = None

        # Stream session tracking for announcements (once per stream)
        self.announced_joins = set()  # Set of user_ids who have been greeted this stream
        self.proactive_engaged = set()  # Set of user_ids we've proactively engaged with
        self.stream_greeting_sent = False  # Track if stream greeting was sent
        self.stream_start_time = time.time()  # Will be updated with actual YouTube stream start time

        # Ensure memory directory exists
        os.makedirs(self.memory_dir, exist_ok=True)
        logger.info(f"📁 Memory directory set to: {self.memory_dir}")

    def update_persona_context(
        self,
        persona_key: Optional[str] = None,
        channel_name: Optional[str] = None,
        channel_id: Optional[str] = None,
        bot_channel_id: Optional[str] = None,
        stream_title: Optional[str] = None,
    ) -> None:
        """Refresh persona-dependent state after session metadata is available."""
        self.persona_key = persona_key
        self.channel_name = channel_name
        self.channel_id = channel_id
        self.bot_channel_id = bot_channel_id
        self.stream_title = stream_title
        self.persona_config = get_persona_config(
            persona_key=persona_key,
            channel_name=channel_name,
            channel_id=channel_id,
            bot_channel_id=bot_channel_id,
            stream_title=stream_title,
        )
        self.intelligent_reply = get_livechat_reply_generator(
            persona_key=persona_key,
            channel_name=channel_name,
            channel_id=channel_id,
            bot_channel_id=bot_channel_id,
            stream_title=stream_title,
        )

    def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single chat message and extract relevant information.

        Args:
            message: Raw message data from YouTube API

        Returns:
            Processed message data with additional metadata
        """
        # QWEN DAE decision logging for visibility
        logger.info("[BOT][AI] [QWEN-DAE-INIT] Processing incoming message")

        # Handle timeout/ban events
        if message.get("type") == "timeout_event":
            logger.info("[BOT][AI] [QWEN-DAE-DECISION] EXECUTE timeout_handler (confidence: 1.00)")
            return self._handle_timeout_event(message)
        elif message.get("type") == "ban_event":
            logger.info("[BOT][AI] [QWEN-DAE-DECISION] EXECUTE ban_handler (confidence: 1.00)")
            return self._handle_ban_event(message)
        elif message.get("type") == "super_chat_event":
            logger.info("[BOT][AI] [QWEN-DAE-DECISION] EXECUTE super_chat_handler (confidence: 1.00)")
            return self._handle_super_chat_event(message)
        
        # Debug: Log message structure
        if isinstance(message, dict) and "snippet" in message:
            snippet = message.get("snippet", {})
            text = snippet.get("displayMessage", "")
            if text and text.startswith('/'):
                logger.info(f"[GAME] Processing slash command message: {text}")
                logger.info("[BOT][AI] [QWEN-DAE-DECISION] EXECUTE command_handler (confidence: 0.95)")
        
        # Handle regular messages - check if it's a raw YouTube API message
        if "snippet" in message and "authorDetails" in message:
            # This is a raw YouTube API message, process it
            pass
        elif message.get("type") != "message":
            return {"skip": True}
        
        try:
            snippet = message.get("snippet", {})
            author_details = message.get("authorDetails") or {}  # Handle None case for bot messages

            # CRITICAL: Skip bot messages early (authorDetails is None for bot's own messages)
            if not author_details:
                logger.debug("[BOT] Skipping message with no authorDetails (likely bot's own message)")
                return {"skip": True, "reason": "no_author_details"}

            # Extract basic message info
            message_id = snippet.get("messageId", "")
            message_text = snippet.get("displayMessage", "")
            author_name = author_details.get("displayName", "Unknown")
            author_id = author_details.get("channelId", "")
            published_at = snippet.get("publishedAt", "")

            # 💰 SUPERCHAT DETECTION - Priority Response for Paid Supporters
            super_chat_details = snippet.get("superChatDetails", None)
            if super_chat_details:
                amount_micros = super_chat_details.get("amountMicros", 0)
                amount_display = super_chat_details.get("amountDisplayString", "$0")
                currency = super_chat_details.get("currency", "USD")
                tier = super_chat_details.get("tier", 1)

                # Convert micros to dollars (1,000,000 micros = $1)
                amount_dollars = int(amount_micros) / 1000000 if amount_micros else 0

                logger.warning(f"💰💰💰 SUPERCHAT DETECTED! {author_name} sent {amount_display} ({amount_dollars} {currency}) - Tier {tier}")
                logger.info(f"[CELEBRATE] Super Chat message: {message_text}")

                # Mark as priority for processing
                message["_is_superchat"] = True
                message["_superchat_amount"] = amount_dollars
                message["_superchat_display"] = amount_display
                message["_superchat_tier"] = tier

            # CRITICAL: Skip processing messages from the bot itself to prevent self-responses
            if self.chat_sender and hasattr(self.chat_sender, 'bot_channel_id') and self.chat_sender.bot_channel_id:
                if author_id == self.chat_sender.bot_channel_id:
                    logger.debug(f"[BOT] Skipping message from bot itself (channel {author_id})")
                    return None  # Skip processing bot's own messages
            
            # CRITICAL: Filter out old buffered events (>5 minutes old)
            if published_at:
                from datetime import datetime, timezone
                try:
                    # Parse YouTube timestamp
                    msg_time = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                    current_time = datetime.now(timezone.utc)
                    age_seconds = (current_time - msg_time).total_seconds()
                    
                    # Skip messages older than 5 minutes (300 seconds) EXCEPT slash commands
                    # Slash commands should always be processed even if delayed
                    if age_seconds > 300:
                        # Always process slash commands regardless of age
                        if message_text and message_text.strip().startswith('/'):
                            logger.info(f"⏰ Processing old slash command from {author_name} ({int(age_seconds)}s old): {message_text}")
                            logger.info("[BOT][AI] [QWEN-DAE-DECISION] OVERRIDE age_filter for slash_command (confidence: 1.00)")
                        else:
                            logger.debug(f"⏰ Skipping old buffered message from {author_name} ({int(age_seconds)}s old)")
                            logger.info("[BOT][AI] [QWEN-DAE-DECISION] SKIP old_message (confidence: 0.90)")
                            return {"skip": True, "reason": "old_buffered_event"}
                except Exception as e:
                    logger.debug(f"Could not parse timestamp: {e}")
                    # Continue processing if we can't parse timestamp
            
            # CRITICAL: Never respond to self (prevent infinite loops)
            if author_id in _get_known_bot_channel_ids():
                logger.debug(f"[BOT] Ignoring self-message from {author_name}")
                return {"skip": True, "reason": "self-message"}
            
            # Check for emoji triggers
            has_trigger = self._check_trigger_patterns(message_text)
            is_rate_limited = self._is_rate_limited(author_id) if has_trigger else False
            
            # Check for consciousness commands with rate limiting
            has_consciousness = False
            if self.consciousness.has_consciousness_emojis(message_text):
                # Check rate limits if emoji limiter is available
                if self.emoji_limiter:
                    should_respond, reason = self.emoji_limiter.should_respond_to_emoji(
                        author_id, author_name
                    )
                    if should_respond:
                        has_consciousness = True
                        # Record that we'll respond
                        self.emoji_limiter.record_emoji_response(author_id, author_name)
                    else:
                        logger.info(f"[FORBIDDEN] Emoji response blocked for {author_name}: {reason}")
                        # Learn from this
                        if self.agentic_improvement:
                            self.agentic_improvement.learn_user_pattern(
                                author_id, f'emoji_blocked_{reason}', False
                            )
                else:
                    # No limiter, allow response
                    has_consciousness = True
            
            # Check for fact-check commands
            has_factcheck = self._check_factcheck_command(message_text)
            
            # Check for YouTube Shorts commands (!createshort, !shortveo, !shortsora, !shortstatus, !shortstats)
            has_shorts_command = self._check_shorts_command(message_text)

            # Check for Move2Japan FoundUp commands (!move2japan, !m2j, !japan)
            has_m2j_command = self._check_m2j_command(message_text)

            # Check for whack commands (score, level, rank, etc)
            has_whack_command = self._check_whack_command(message_text)

            # Check for MAGA content (WSP: use existing detector)
            maga_response = None
            allow_maga = self.persona_config.get("allow_maga_trolling", True)
            if allow_maga:
                maga_response = self.greeting_generator.get_response_to_maga(message_text)
            has_maga = maga_response is not None

            # Determine role for troll classification
            is_mod = author_details.get("isChatModerator", False)
            is_owner = author_details.get("isChatOwner", False)
            role = 'OWNER' if is_owner else 'MOD' if is_mod else 'USER'

            processed_message = {
                "message_id": message_id,
                "text": message_text,
                "author_name": author_name,
                "author_id": author_id,
                "published_at": published_at,
                "has_trigger": has_trigger,
                "is_rate_limited": is_rate_limited,
                "has_consciousness": has_consciousness,
                "has_factcheck": has_factcheck,
                "has_shorts_command": has_shorts_command,
                "has_m2j_command": has_m2j_command,
                "has_whack_command": has_whack_command,
                "has_maga": has_maga,
                "maga_response": maga_response,  # Store generated response to prevent double-call
                "is_moderator": is_mod,
                "is_owner": is_owner,
                "is_member": author_details.get("isChatSponsor", False),  # Blue badge = channel member
                "live_chat_id": snippet.get("liveChatId"),  # Add for MAGADOOM timeouts
                "raw_message": message,
                # Superchat support
                "is_superchat": message.get("_is_superchat", False),
                "superchat_amount": message.get("_superchat_amount", 0),
                "superchat_display": message.get("_superchat_display", ""),
                "superchat_tier": message.get("_superchat_tier", 0)
            }

            # History-based troll classification for non-mods
            if role == 'USER' and self.memory_manager:
                classification = self.memory_manager.classify_user(author_name)
                processed_message["is_troll"] = classification.get("is_troll", False)
                processed_message["troll_signals"] = classification.get("signals", [])
            else:
                processed_message["is_troll"] = False
                processed_message["troll_signals"] = []

            # Timeout-based troll tracking (whacked_users)
            if role == 'USER' and author_id and _env_truthy("YT_TROLL_TRACK_BY_TIMEOUTS", "true"):
                try:
                    from modules.gamification.whack_a_magat.src.whack import get_profile_store
                    profile_store = get_profile_store()
                    if profile_store.is_whacked_user(author_id):
                        processed_message["is_troll"] = True
                        processed_message["troll_signals"].append("whacked")
                except Exception as exc:
                    logger.debug(f"[TROLL] Whack-based classification unavailable: {exc}")
            
            logger.debug(f"[NOTE] Processed message from {author_name}: {message_text[:50]}...")
            return processed_message
            
        except Exception as e:
            logger.error(f"[FAIL] Error processing message: {e}")
            return {
                "message_id": "",
                "text": "",
                "author_name": "Unknown",
                "author_id": "",
                "published_at": "",
                "has_trigger": False,
                "is_rate_limited": False,
                "raw_message": message,
                "error": str(e)
            }
    
    def _check_trigger_patterns(self, message_text: str) -> bool:
        """
        Check if message contains emoji trigger patterns.
        
        Args:
            message_text: The message text to check
            
        Returns:
            True if trigger patterns are found, False otherwise
        """
        if not message_text:
            return False
        
        # Check for individual trigger emojis
        for emoji in self.trigger_emojis:
            if emoji in message_text:
                logger.debug(f"[TARGET] Trigger emoji '{emoji}' found in message")
                return True
        
        # Check for 3-emoji sequences
        emoji_count = sum(message_text.count(emoji) for emoji in self.trigger_emojis)
        if emoji_count >= 3:
            logger.debug(f"[TARGET] Multiple trigger emojis found ({emoji_count})")
            return True
        
        return False
    
    async def generate_response(self, processed_message: Dict[str, Any]) -> Optional[str]:
        """
        Generate a response to a processed message.
        
        Args:
            processed_message: Processed message data
            
        Returns:
            Response text or None if no response should be generated
        """
        message_text = processed_message.get("text", "")
        author_name = _sanitize_username(processed_message.get("author_name", "Unknown"))
        author_id = processed_message.get("author_id", "")
        is_mod = processed_message.get("is_moderator", False)
        is_owner = processed_message.get("is_owner", False)
        
        # Determine role
        role = 'OWNER' if is_owner else 'MOD' if is_mod else 'USER'
        
        # WSP 48: Self-improvement through observation
        if role in ['MOD', 'OWNER']:
            # Learn from mod/owner patterns
            self.self_improvement.observe_command(message_text, 1.0)

        # Engagement gate: engage mods/owner only, troll trolls if enabled
        if _env_truthy("YT_LIVECHAT_ENGAGE_MODS_ONLY", "true") and role == 'USER':
            if processed_message.get("is_superchat"):
                pass
            elif processed_message.get("has_maga") and _env_truthy("YT_LIVECHAT_TROLL_TROLLS", "true"):
                pass
            elif processed_message.get("is_troll") and _env_truthy("YT_LIVECHAT_TROLL_TROLLS", "true"):
                logger.info(f"[ENGAGE] Troll classified for {author_name} - engage allowed")
            elif self.persona_config.get("display_name") and f"@{self.persona_config.get('display_name')}".lower() in message_text.lower():
                pass
            else:
                logger.info(f"[ENGAGE] Skipping user engagement for {author_name} (mods_only)")
                return None
        
        try:
            # Priority 0: SUPERCHAT RESPONSES (HIGHEST PRIORITY - Always respond to paid supporters!)
            if processed_message.get("is_superchat"):
                amount = processed_message.get("superchat_amount", 0)
                display = processed_message.get("superchat_display", "$0")
                tier = processed_message.get("superchat_tier", 1)

                logger.warning(f"💰 SUPERCHAT HANDLER TRIGGERED for {author_name} ({display})")

                # Generate enthusiastic UnDaoDu✊✋🖐 praise response
                praise_responses = [
                    f"✊✋🖐 LEGENDARY SUPPORT! @{author_name} just dropped {display}! Democracy needs heroes like you! 🇺🇸✨",
                    f"✊✋🖐 HOLY RESISTANCE! @{author_name} with {display}! You're powering the fight against fascism! 💪🔥",
                    f"✊✋🖐 EPIC CONTRIBUTION! @{author_name} ({display})! You're making history! The resistance is REAL! 🦅[LIGHTNING]",
                    f"✊✋🖐 UNSTOPPABLE! @{author_name} just sent {display}! You are the BACKBONE of democracy! 🛡️💎",
                    f"✊✋🖐 PHENOMENAL! @{author_name} with {display} of PURE DEMOCRACY FUEL! The MAGAts are SHAKING! 🌊🔥"
                ]

                # Choose random praise
                import random
                praise = random.choice(praise_responses)

                # Grant $20+ superchats video creation privilege
                if amount >= 20:
                    logger.warning(f"💰💰💰 $20+ SUPERCHAT! Granting video creation privilege to {author_name}")
                    # Store privilege in processed_message for YouTube Shorts module
                    processed_message["_can_create_video"] = True
                    praise += f" | 🎬 VIDEO CREATION UNLOCKED! Type your idea!"

                # Log for analytics
                logger.info(f"💰 Superchat response: {praise}")

                return praise

            # Priority 1: Fact-check commands with consciousness emojis
            if processed_message.get("has_factcheck"):
                # Check moderator throttling first (WSP 84) - only for actual moderators
                if self.intelligent_throttle and role == 'MOD':
                    allowed, block_msg = self.intelligent_throttle.check_moderator_command_allowed(author_id, author_name, role, message_text)
                    if not allowed:
                        logger.info(f"[SEARCH][FORBIDDEN] Moderator {author_name} blocked: {block_msg}")
                        return block_msg

                # Extract emoji sequence to check for consciousness emojis
                emoji_seq = self.consciousness.extract_emoji_sequence(message_text)
                if emoji_seq and any(emoji in emoji_seq for emoji in ['✊', '✋', '🖐']):
                    logger.info(f"[SEARCH]✊✋🖐 HIGHEST PRIORITY: Fact-check with consciousness emojis from {author_name}")
                    response = await self._handle_factcheck(message_text, author_name, role)
                    if response:
                        logger.info(f"[SEARCH]✊✋🖐 Consciousness fact-check response for {author_name}")

                        # Record command usage for throttling (WSP 84)
                        if self.intelligent_throttle:
                            self.intelligent_throttle.record_moderator_command(author_id, author_name, role, message_text)

                        return response

            # Priority 1: PQN Research Commands (WSP 84 - Using existing handlers)
            # See: modules/ai_intelligence/pqn_alignment/docs/PQN_CHAT_INTEGRATION.md
            if self._check_pqn_command(message_text):
                # Check moderator throttling (WSP 84) - only for actual moderators
                if self.intelligent_throttle and role == 'MOD':
                    allowed, block_msg = self.intelligent_throttle.check_moderator_command_allowed(author_id, author_name, role, message_text)
                    if not allowed:
                        logger.info(f"🔬[FORBIDDEN] Moderator {author_name} blocked: {block_msg}")
                        return block_msg

                logger.info(f"🔬 PQN command detected: '{message_text}' from {author_name}")
                response = self._handle_pqn_research(message_text, author_name)
                if response:
                    logger.info(f"🔬 PQN command processed for {author_name}: {response[:100]}")

                    # Record command usage for throttling (WSP 84)
                    if self.intelligent_throttle:
                        self.intelligent_throttle.record_moderator_command(author_id, author_name, role, message_text)

                    return response
                else:
                    logger.warning(f"🔬 PQN command failed to generate response for {author_name}")
            else:
                logger.debug(f"🔬 PQN command NOT detected in: '{message_text}'")

            # Priority 2: AGENTIC consciousness response (mod/owner only by default)
            # SKIP if there are legitimate commands that should take priority
            if (processed_message.get("has_consciousness") and
                not processed_message.get("has_whack_command") and
                not processed_message.get("has_factcheck")):
                logger.info(f"[SEARCH] CONSCIOUSNESS TRIGGER ✊✋🖐 from {author_name} | Role: {role} | Is Owner: {is_owner} | Is Mod: {is_mod}")
                # Check if user has permission based on mode
                can_use_consciousness = (
                    self.consciousness_mode == 'everyone' or
                    role in ['MOD', 'OWNER']
                )
                logger.info(f"   Can use consciousness: {can_use_consciousness} (mode: {self.consciousness_mode})")

                if can_use_consciousness:
                    # QUIZ ANSWER: Check if ✊✋🖐 is followed by a number (1-4)
                    quiz_answer_match = re.search(r'✊✋🖐\s*([1-4])', message_text)
                    if quiz_answer_match:
                        answer_num = quiz_answer_match.group(1)
                        logger.info(f"[BOOKS] Quiz answer: ✊✋🖐{answer_num} from {author_name}")
                        quiz_response = self.command_handler.handle_whack_command(
                            f"/quiz {answer_num}", author_name, author_id, role
                        )
                        if quiz_response:
                            return quiz_response

                    logger.info("[BOT][AI] [QWEN-DAE-DECISION] EXECUTE consciousness_response (confidence: 0.85)")
                    # Generate agentic response based on chat history
                    agentic_response = self.agentic_engine.generate_agentic_response(
                        author_name, message_text, role
                    )

                    if agentic_response:
                        logger.info(f"[BOT] Agentic ✊✋🖐️ response for {author_name} (mode: {self.consciousness_mode})")

                        # Qwen Message Diversity Check - Prevent repetitive consciousness messages
                        if self.intelligent_throttle:
                            allowed, reason = self.intelligent_throttle.check_message_diversity(agentic_response, 'consciousness')
                            if not allowed:
                                logger.info(f"[BOT][AI] [QWEN-DIVERSITY] Blocking repetitive consciousness response: {reason}")
                                return None

                        logger.info("[BOT][AI] [QWEN-DAE-PERFORMANCE] consciousness_response: generated successfully")
                        # Mark this as a consciousness response in processed data
                        processed_message["response_type"] = "consciousness"
                        # If it's a mod, make sure we @ them
                        if role in ['MOD', 'OWNER'] and not agentic_response.startswith('@'):
                            agentic_response = f"@{author_name} {agentic_response}"
                        return agentic_response
                    else:
                        logger.warning(f"[U+26A0]️ No agentic response generated for {author_name}'s consciousness trigger")
                else:
                    logger.debug(f"✊✋🖐️ ignored from {author_name} - consciousness mode is {self.consciousness_mode}")

                # Fallback to consciousness handler for special commands (still respects mode)
                if can_use_consciousness and role in ['MOD', 'OWNER']:
                    response = self.consciousness.process_consciousness_command(
                        message_text, author_id, author_name, role
                    )
                    if response:
                        logger.info(f"✊✋🖐 Consciousness command response for {author_name}")
                        # Mark this as a consciousness response
                        processed_message["response_type"] = "consciousness"
                        return response

            # Priority 3: Handle remaining fact-check commands (without consciousness emojis)
            if processed_message.get("has_factcheck"):
                logger.info("[BOT][AI] [QWEN-DAE-DECISION] EXECUTE factcheck_handler (confidence: 0.80)")
                # Check moderator throttling (WSP 84) - only for actual moderators
                if self.intelligent_throttle and role == 'MOD':
                    allowed, block_msg = self.intelligent_throttle.check_moderator_command_allowed(author_id, author_name, role, message_text)
                    if not allowed:
                        logger.info(f"[SEARCH][FORBIDDEN] Moderator {author_name} blocked: {block_msg}")
                        return block_msg

                response = await self._handle_factcheck(message_text, author_name, role)
                if response:
                    logger.info(f"[SEARCH] Fact-check response for {author_name}")

                    # Record command usage for throttling (WSP 84)
                    if self.intelligent_throttle:
                        self.intelligent_throttle.record_moderator_command(author_id, author_name, role, message_text)

                    return response

            # Priority 3.4: Handle Move2Japan FoundUp commands (!move2japan, !m2j, !japan)
            if processed_message.get("has_m2j_command"):
                logger.info("[BOT][AI] [QWEN-DAE-DECISION] EXECUTE m2j_command_handler (confidence: 0.90)")
                logger.info(f"🇯🇵 Routing M2J command: '{message_text}' from {author_name} (role: {role})")

                response = self._handle_m2j_command(message_text, author_name, author_id, role)
                if response:
                    logger.info(f"🇯🇵 M2J command response for {author_name}: {response[:100]}")
                    return response
                else:
                    logger.warning(f"🇯🇵[FAIL] No response from M2J handler for '{message_text}'")

            # Priority 3.5: Handle YouTube Shorts commands (!createshort, !shortveo, !shortsora, !shortstatus, !shortstats)
            if processed_message.get("has_shorts_command"):
                logger.info("[BOT][AI] [QWEN-DAE-DECISION] EXECUTE shorts_command_handler (confidence: 0.90)")
                logger.info(f"🎬 Routing Shorts command: '{message_text}' from {author_name} (role: {role})")

                response = self._handle_shorts_command(message_text, author_name, author_id, role)
                if response:
                    logger.info(f"🎬 Shorts command response for {author_name}: {response[:100]}")
                    return response
                else:
                    logger.warning(f"🎬[FAIL] No response from Shorts handler for '{message_text}'")

            # Priority 4: Handle whack commands (score, level, rank)
            if processed_message.get("has_whack_command"):
                logger.info("[BOT][AI] [QWEN-DAE-DECISION] EXECUTE whack_command_handler (confidence: 0.90)")
                logger.info(f"[GAME] Calling handle_whack_command for: '{message_text}' from {author_name}")

                # Check moderator throttling (WSP 84) - only for actual moderators
                if self.intelligent_throttle and role == 'MOD':
                    allowed, block_msg = self.intelligent_throttle.check_moderator_command_allowed(author_id, author_name, role, message_text)
                    if not allowed:
                        logger.info(f"[GAME][FORBIDDEN] Moderator {author_name} blocked: {block_msg}")
                        return block_msg

                # Extra debug for /quiz
                if '/quiz' in message_text.lower():
                    logger.warning(f"[AI][GAME] QUIZ DETECTED IN MESSAGE_PROCESSOR! Sending to handle_whack_command")
                is_member = processed_message.get("is_member", False)
                response = self._handle_whack_command(message_text, author_name, author_id, role, is_member)
                if response:
                    # Handle list responses (e.g., /help returns multiple messages)
                    if isinstance(response, list):
                        logger.info(f"[GAME] Whack command response for {author_name}: {len(response)} messages")
                        for i, msg in enumerate(response):
                            logger.warning(f"[GAME][OK] MESSAGE_PROCESSOR RETURNING [{i+1}/{len(response)}]: {msg[:80]}")
                    else:
                        logger.info(f"[GAME] Whack command response for {author_name}: {response[:100]}")
                        logger.warning(f"[GAME][OK] MESSAGE_PROCESSOR RETURNING: {response[:100]}")

                    # Record command usage for throttling (WSP 84)
                    if self.intelligent_throttle:
                        self.intelligent_throttle.record_moderator_command(author_id, author_name, role, message_text)

                    return response
                else:
                    logger.error(f"[GAME][FAIL] No response from handle_whack_command for '{message_text}'")

            # Priority 4.5: Troll callout - mock known trolls when they first message this stream
            # Only callout once per stream (tracked in announced_joins)
            if author_id not in self.announced_joins:
                try:
                    # Use magadoom_scores.db (the REAL whack data source)
                    from modules.gamification.whack_a_magat.src.whack import get_profile_store
                    profile_store = get_profile_store()
                    whack_count = profile_store.get_whack_count_for_user(author_id)

                    if whack_count >= 3:  # Confirmed troll (3+ whacks)
                        callout = self.greeting_generator.generate_troll_callout(author_name, whack_count)
                        if callout:
                            self.announced_joins.add(author_id)  # Don't callout again this stream

                            # Check intelligent throttle to prevent spam
                            if self.intelligent_throttle:
                                allowed, reason = self.intelligent_throttle.check_message_diversity(callout, 'callout')
                                if not allowed:
                                    logger.debug(f"[TROLL] Callout blocked by throttle: {reason}")
                                else:
                                    logger.info(f"💀 [TROLL-CALLOUT] @{author_name} ({whack_count} whacks) - calling them out!")
                                    return callout
                            else:
                                logger.info(f"💀 [TROLL-CALLOUT] @{author_name} ({whack_count} whacks) - calling them out!")
                                return callout
                except Exception as e:
                    logger.debug(f"[TROLL] Callout check failed: {e}")

            # Priority 4.6: Top whacker/mod welcome - greet significant players on first message
            # Only greet once per stream (tracked in announced_joins)
            if author_id not in self.announced_joins:
                try:
                    whacker_greeting = self.greeting_generator.generate_whacker_greeting(author_name, author_id, role)
                    if whacker_greeting:
                        self.announced_joins.add(author_id)  # Don't greet again this stream

                        # Check intelligent throttle to prevent spam
                        if self.intelligent_throttle:
                            allowed, reason = self.intelligent_throttle.check_message_diversity(whacker_greeting, 'greeting')
                            if not allowed:
                                logger.debug(f"[WHACKER] Greeting blocked by throttle: {reason}")
                            else:
                                logger.info(f"🎯 [WHACKER-GREETING] Welcoming top whacker @{author_name}!")
                                return whacker_greeting
                        else:
                            logger.info(f"🎯 [WHACKER-GREETING] Welcoming top whacker @{author_name}!")
                            return whacker_greeting
                except Exception as e:
                    logger.debug(f"[WHACKER] Greeting check failed: {e}")

            # Priority 5: Handle MAGA content - just respond with witty comebacks
            # Bot doesn't execute timeouts, only announces them when mods/owner do them
            if processed_message.get("has_maga"):
                logger.info("[BOT][AI] [QWEN-DAE-DECISION] EXECUTE maga_troll_response (confidence: 0.75)")

                # Check GLOBAL MAGA rate limiting FIRST to prevent spam
                current_time = time.time()
                if current_time - self.last_global_maga_time < self.global_maga_cooldown:
                    remaining = self.global_maga_cooldown - (current_time - self.last_global_maga_time)
                    logger.debug(f"🛡️ GLOBAL: Skipping MAGA response - global cooldown active ({remaining:.0f}s remaining)")
                    return None

                # Check per-user MAGA rate limiting
                if self._is_maga_rate_limited(author_id):
                    logger.debug(f"🛡️ Skipping MAGA response to {author_name} - user rate limited (10 min cooldown)")
                    return None

                # Also check intelligent throttle for MAGA responses - only for moderators
                if self.intelligent_throttle and role == 'MOD':
                    allowed, block_msg = self.intelligent_throttle.check_moderator_command_allowed(author_id, author_name, role, message_text)
                    if not allowed:
                        logger.info(f"🛡️ Intelligent throttle blocked MAGA response to {author_name}: {block_msg}")
                        return None

                from modules.communication.livechat.src.operator_command_queue import load_active_theme
                if load_active_theme('livechat'):
                    if (processed_message.get('is_rate_limited') or not self.intelligent_reply
                            or not _env_truthy('YT_COMMENT_REPLY_ENABLED', 'true')):
                        return None
                    response = self.intelligent_reply.generate_reply(
                        message=message_text, username=author_name, user_id=author_id,
                        role=role, is_member=processed_message.get('is_member', False))
                    if response:
                        self._update_maga_time(author_id)
                        self.last_global_maga_time = current_time
                    return response

                # Reuse the MAGA response generated during classification to prevent duplicates
                response = processed_message.get("maga_response")
                if response:
                    # Only send if we can @mention properly
                    if self._is_valid_mention(author_name):
                        # Personalize with username
                        response = f"@{author_name} {response}"
                        logger.info(f"[TARGET] MAGA troll response for @{author_name}")
                        # Update MAGA response times to prevent spam
                        self._update_maga_time(author_id)
                        self.last_global_maga_time = time.time()  # Update global cooldown
                        return response
                    else:
                        logger.debug(f"[U+26A0]️ DELETING MAGA response - cannot @mention '{author_name}'")
                        return None  # Explicitly return None - no message sent

            # Priority 6: Handle regular emoji triggers
            if processed_message.get("has_trigger"):
                logger.info("[BOT][AI] [QWEN-DAE-DECISION] EXECUTE emoji_trigger_handler (confidence: 0.70)")
                if processed_message.get("is_rate_limited"):
                    logger.debug(f"⏳ User {author_name} is rate limited")
                    logger.info("[BOT][AI] [QWEN-DAE-DECISION] SKIP rate_limited_user (confidence: 0.95)")
                    return None
                
                # Update trigger time for rate limiting
                self._update_trigger_time(author_id)
                
                # Try intelligent reply generator (Grok-powered with patterns)
                # NOTE: _env_truthy is defined at module level (line 67) - do NOT import here
                # Importing inside the function creates a local variable scoping issue
                if self.intelligent_reply and _env_truthy("YT_COMMENT_REPLY_ENABLED", "true"):
                    is_member = processed_message.get("is_member", False)  # Blue badge
                    response = self.intelligent_reply.generate_reply(
                        message=message_text,
                        username=author_name,
                        user_id=author_id,
                        role=role,
                        is_member=is_member
                    )
                    if response:
                        member_tag = " [ANTIMA]" if is_member else ""
                        logger.info(f"[GROK] Intelligent reply for {author_name}{member_tag}")
                        return response
                
                from modules.communication.livechat.src.operator_command_queue import load_active_theme
                if load_active_theme('livechat'):
                    return None  # Rejected themed drafts cannot fall back to uninspected banter.

                # Fallback: Try banter engine
                response = await self._generate_banter_response(message_text, author_name)
                
                if response:
                    logger.info(f"[U+1F3AD] Generated banter response for {author_name}")
                    return response
                
                # Fallback to LLM bypass engine
                response = await self._generate_fallback_response(message_text, author_name)
                
                if response:
                    logger.info(f"[REFRESH] Generated fallback response for {author_name}")
                    return response
            
            # Priority 7: Proactive engagement (REDUCED - too spammy)
            # Only engage proactively with mods/owner ONCE per stream
            import random
            if role in ['MOD', 'OWNER'] and author_id not in self.proactive_engaged:
                if random.random() < 0.3:  # 30% chance for mods/owner
                    if self.agentic_engine.should_engage(message_text, author_name, role):
                        proactive_response = self.agentic_engine.generate_agentic_response(
                            author_name, message_text, role
                        )
                        if proactive_response:
                            # CRITICAL: Validate the ENTIRE response can be sent properly
                            # Check if response contains @mentions that might fail
                            if '@' in proactive_response:
                                # Extract username from @mention in response
                                mention_match = re.search(r'@(\S+)', proactive_response)
                                if mention_match:
                                    mentioned_user = mention_match.group(1)
                                    if not self._is_valid_mention(mentioned_user):
                                        logger.warning(f"[U+26A0]️ DELETING proactive response - cannot @mention '{mentioned_user}' in response")
                                        self.proactive_engaged.add(author_id)
                                        return None

                            # Qwen Message Diversity Check - Prevent repetitive engagement messages
                            if self.intelligent_throttle:
                                allowed, reason = self.intelligent_throttle.check_message_diversity(proactive_response, 'engagement')
                                if not allowed:
                                    logger.info(f"[BOT][AI] [QWEN-DIVERSITY] Blocking repetitive engagement response: {reason}")
                                    self.proactive_engaged.add(author_id)  # Still mark as engaged to prevent retry
                                    return None

                            # Response is valid, send it
                            if _env_truthy("YT_CONTEXTUAL_FOLLOWUP_ENABLED", "true"):
                                followup = self._build_followup_question(author_name, message_text)
                                if followup:
                                    proactive_response = f"{proactive_response} {followup}"
                            self.proactive_engaged.add(author_id)
                            logger.info(f"💬 Proactive engagement with {author_name} (once per stream)")
                            return proactive_response
                        else:
                            logger.debug(f"No proactive response generated for {author_name}")

            # Priority 8: Check for stream greeting (only ONCE per stream session)
            # Send ONE greeting per stream, not per user, to avoid spam
            if not hasattr(self, 'stream_greeting_sent') or not self.stream_greeting_sent:
                # Generate a general stream greeting, not user-specific
                persona_greeting = get_persona_greeting(
                    persona_key=self.persona_key,
                    stream_title=self.stream_title,
                    channel_name=self.channel_name,
                    channel_id=self.channel_id,
                    bot_channel_id=self.bot_channel_id,
                )
                greeting = persona_greeting or self.greeting_generator.generate_greeting()
                if greeting:
                    # Qwen Message Diversity Check - Prevent repetitive greeting messages
                    if self.intelligent_throttle:
                        allowed, reason = self.intelligent_throttle.check_message_diversity(greeting, 'greeting')
                        if not allowed:
                            logger.info(f"[BOT][AI] [QWEN-DIVERSITY] Blocking repetitive greeting: {reason}")
                            self.stream_greeting_sent = True  # Mark as sent to prevent future greetings
                            return None

                    self.stream_greeting_sent = True  # Mark stream greeting as sent
                    logger.info(f"🌞 Stream greeting sent (once per stream)")
                    return greeting
            
            return None
            
        except Exception as e:
            logger.error(f"[FAIL] Error generating response for {author_name}: {e}")
            return None
    
    async def _generate_banter_response(self, message_text: str, author_name: str) -> Optional[str]:
        """Generate response using the banter engine."""
        if not self.banter_enabled or not self.banter_engine:
            return None
        try:
            state_info, response = self.banter_engine.process_input(message_text)
            
            if response:
                # Personalize the response
                personalized_response = f"@{author_name} {response}"
                logger.debug(f"[U+1F3AD] Banter engine response: {state_info}")
                return personalized_response
            
            return None
            
        except Exception as e:
            logger.error(f"[FAIL] Banter engine error: {e}")
            return None
    
    def _build_followup_question(self, author_name: str, current_message: str) -> Optional[str]:
        if not self.memory_manager:
            return None
        history = self.memory_manager.get_history(author_name, limit=5)
        if not history:
            return None
        # Pick the most recent message that is not the current one
        for entry in reversed(history):
            if ": " in entry:
                msg = entry.split(": ", 1)[1].strip()
            else:
                msg = entry.strip()
            if msg and msg != current_message:
                words = msg.split()
                snippet = " ".join(words[:8])
                return f"Last time you mentioned \"{snippet}\" — any update?"
        return None

    async def _generate_fallback_response(self, message_text: str, author_name: str) -> Optional[str]:
        """Generate response using the fallback LLM bypass engine."""
        try:
            response = await self.llm_bypass_engine.generate_response(message_text)
            
            if response:
                # Personalize the response
                personalized_response = f"@{author_name} {response}"
                logger.debug(f"[REFRESH] Fallback response generated")
                return personalized_response
            
            return None
            
        except Exception as e:
            logger.error(f"[FAIL] Fallback engine error: {e}")
            return None
    
    def _is_rate_limited(self, user_id: str) -> bool:
        """
        Check if a user is rate limited from triggering gestures.

        Args:
            user_id: The user's ID

        Returns:
            True if user is rate limited, False otherwise
        """
        current_time = time.time()
        if user_id in self.last_trigger_time:
            time_since_last = current_time - self.last_trigger_time[user_id]
            if time_since_last < self.trigger_cooldown:
                logger.debug(f"⏳ Rate limited user {user_id} for {self.trigger_cooldown - time_since_last:.1f}s")
                return True
        return False

    def _is_maga_rate_limited(self, user_id: str) -> bool:
        """
        Check if a user is rate limited from MAGA responses (longer cooldown to prevent spam).

        Args:
            user_id: The user's ID

        Returns:
            True if user is rate limited, False otherwise
        """
        current_time = time.time()
        if user_id in self.last_maga_time:
            time_since_last = current_time - self.last_maga_time[user_id]
            if time_since_last < self.maga_cooldown:
                logger.debug(f"🛡️ MAGA rate limited user {user_id} for {self.maga_cooldown - time_since_last:.1f}s")
                return True
        return False

    def _update_maga_time(self, user_id: str):
        """Update the last MAGA response time for a user."""
        self.last_maga_time[user_id] = time.time()
    
    def _is_valid_mention(self, username: str) -> bool:
        """
        Check if username can be properly @mentioned on YouTube.
        YouTube requires usernames to be at least 3 chars and not contain certain characters.
        """
        if not username:
            return False
        
        # Username too short - single character usernames don't work
        # But 2-letter usernames like "JS" ARE valid on YouTube
        if len(username) < 2:
            logger.debug(f"Username '{username}' too short for @mention")
            return False
            
        # Contains spaces or special chars that break mentions
        invalid_chars = [' ', '\n', '\t', '@', '#', '$', '%', '^', '&', '*']
        if any(char in username for char in invalid_chars):
            logger.debug(f"Username '{username}' contains invalid chars for @mention")
            return False
            
        # Looks like a display name instead of handle (e.g., "John Smith" vs "JohnSmith123")
        if username.count(' ') > 0:
            logger.debug(f"Username '{username}' appears to be display name, not handle")
            return False
            
        return True
    
    def _update_trigger_time(self, user_id: str):
        """Update the last trigger time for a user."""
        self.last_trigger_time[user_id] = time.time()
        logger.debug(f"⏰ Updated trigger time for user {user_id}")
    
    def reset_stream_session(self, actual_start_time: float = None):
        """Reset the stream session tracking (call when stream restarts).

        Args:
            actual_start_time: Optional Unix timestamp of actual stream start from YouTube API.
                              If not provided, uses current time.
        """
        self.announced_joins.clear()
        self.stream_greeting_sent = False  # Reset stream greeting flag
        if actual_start_time:
            self.stream_start_time = actual_start_time
            stream_duration = (time.time() - actual_start_time) / 60
            logger.info(f"[REFRESH] Stream session reset - using actual YouTube start time (running {stream_duration:.1f} min)")
        else:
            self.stream_start_time = time.time()
            logger.info("[REFRESH] Stream session reset - join announcements and greetings cleared")

    def set_actual_start_time(self, actual_start_time: float):
        """Set the actual YouTube stream start time.

        Args:
            actual_start_time: Unix timestamp from YouTube's liveStreamingDetails.actualStartTime
        """
        if actual_start_time:
            self.stream_start_time = actual_start_time
            stream_duration = (time.time() - actual_start_time) / 60
            logger.info(f"[STREAM] Updated stream_start_time to actual YouTube start (running {stream_duration:.1f} min)")
    
    def log_message_to_file(self, processed_message: Dict[str, Any]):
        """
        Log message to user-specific file.
        
        Args:
            processed_message: Processed message data
        """
        try:
            author_name = processed_message.get("author_name", "Unknown")
            message_text = processed_message.get("text", "")
            published_at = processed_message.get("published_at", "")
            
            # Create safe filename
            safe_author_name = "".join(c for c in author_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            if not safe_author_name:
                safe_author_name = "Unknown"
            
            user_file = os.path.join(self.memory_dir, f"{safe_author_name}.txt")
            
            with open(user_file, "a", encoding="utf-8") as f:
                # Store author name and message (no timestamp needed)
                f.write(f"{author_name}: {message_text}\n")
            
            logger.debug(f"[NOTE] Logged message to {user_file}")
            
        except Exception as e:
            logger.error(f"[FAIL] Error logging message to file: {e}")
    
    def _check_factcheck_command(self, text: str) -> bool:
        """
        Check if message contains fact-check command.

        Supports tiered analysis:
        - FC @user = ALL comments (full history)
        - FC1 @user = last 1 comment
        - FC2 @user = last 2 comments
        - ... up to FC9 @user = last 9 comments
        - factcheck @user = alias for FC (all comments)
        """
        pattern = r'(?:factcheck|fc\d?)\s+@[\w\s]+'
        return bool(re.search(pattern, text.lower()))
    
    def _check_shorts_command(self, text: str) -> bool:
        """
        Check if message contains YouTube Shorts commands.

        Commands:
        - !createshort <topic> - Create and upload Short (auto engine)
        - !shortsora <topic> - Create with Sora2 engine (simplified from shortsora2)
        - !shortveo <topic> - Create with Veo3 engine (simplified from shortveo3)
        - !short - List recent shorts
        - !shortstatus - Check generation status
        - !shortstats - View statistics

        Note: Shorts use ! prefix, MAGADOOM uses / prefix for command separation.
        """
        shorts_commands = ['!createshort', '!shortsora', '!shortveo', '!short', '!shortstatus', '!shortstats']
        text_lower = text.lower().strip()

        # All commands use startswith() - !short can be followed by @username or alone
        has_shorts = any(text_lower.startswith(cmd) for cmd in shorts_commands)

        if has_shorts:
            logger.info(f"🎬 Detected YouTube Shorts command: {text_lower}")

        return has_shorts

    def _check_m2j_command(self, text: str) -> bool:
        """
        Check if message contains Move2Japan FoundUp commands.

        Commands:
        - !move2japan - Start BC0 intake (or continue conversation)
        - !m2j - Short alias
        - !japan - Short alias

        Note: M2J uses ! prefix, same as Shorts. No collision because
        command names are distinct.
        """
        m2j_commands = ['!move2japan', '!m2j', '!japan']
        text_lower = text.lower().strip()

        has_m2j = any(text_lower.startswith(cmd) for cmd in m2j_commands)

        if has_m2j:
            logger.info(f"\U0001f1ef\U0001f1f5 Detected Move2Japan command: {text_lower}")

        return has_m2j

    def _check_whack_command(self, text: str) -> bool:
        """
        Check if message contains whack gamification commands.

        Handles ONLY / commands for MAGADOOM gamification:
        - /score, /quiz, /stats, etc.
        - Quiz answers: !1, !2, !3, !4
        """
        commands = [
            '/score', '/rank', '/stats', '/leaderboard', '/frags', '/whacks',
            '/help', '/quiz', '/facts', '/sprees', '/toggle', '/session',
            '/fuc',  # FFCPLN Mining economy (OWNER only)
            # antifaFM schema commands (with typo variants)
            '/karaoke', '/karaoki', '/karaokie', '/lyrics',
            '/video', '/grid', '/full', '/news',
            '/entangled', '/bell', '/0102', '/wave',
            # Games commands
            '/chess', '/checkers', '/move', '/resign', '/board',
            # Deprecated but handled with helpful messages:
            '/level', '/answer', '/top', '/fscale', '/rate'
        ]

        # Quiz answer shortcuts
        quiz_answers = ['!1', '!2', '!3', '!4']

        # Additional ! commands routed through CommandHandler (non-quiz)
        bang_commands = [
            '!party',
            # antifaFM schema commands (with typo variants)
            '!karaoke', '!karaoki', '!karaokie', '!lyrics',
            '!video', '!grid', '!full', '!news',
            '!entangled', '!bell', '!0102', '!wave',
            # Games commands
            '!chess', '!checkers', '!move', '!resign', '!board'
        ]

        text_lower = text.lower().strip()

        # Check / commands
        has_slash_command = any(text_lower.startswith(cmd) for cmd in commands)

        # Check quiz answers (!1-!4)
        has_quiz_answer = any(text_lower.startswith(cmd) for cmd in quiz_answers)

        # Check non-quiz ! commands
        has_bang_command = any(text_lower.startswith(cmd) for cmd in bang_commands)

        has_command = has_slash_command or has_quiz_answer or has_bang_command

        if has_command:
            logger.info(f"[GAME] Detected gamification command: {text_lower}")
        else:
            # Log if it looks like a command but isn't recognized
            if text_lower.startswith('/'):
                logger.debug(f"[SEARCH] Unrecognized / command: {text_lower}")

        return has_command
    
    async def _handle_factcheck(self, text: str, requester: str, role: str) -> Optional[str]:
        """
        Handle fact-check commands with tiered analysis.

        Examples:
        - FC @user or factcheck @user = Analyze ALL comments
        - FC1 @user = Analyze last 1 comment
        - FC5 @user = Analyze last 5 comments
        """
        # Extract target username and optional message limit
        pattern = r'(?:factcheck|fc(\d?))\s+@([\w\s]+?)(?:\s|$)'
        match = re.search(pattern, text.lower())

        if match:
            count_str = match.group(1)  # Empty string or digit 1-9
            target = match.group(2).strip()

            # Parse message count limit (None = all messages)
            message_limit = int(count_str) if count_str else None

            # Extract emoji sequence if present
            emoji_seq = self.consciousness.extract_emoji_sequence(text)

            # Try Grok first, then fallback to simple fact checker
            if self.grok:
                # Collect user messages with optional limit
                all_user_messages = self._collect_all_user_messages(message_limit=message_limit)
                # Temporarily update Grok with collected messages
                if hasattr(self.grok, 'all_user_messages'):
                    self.grok.all_user_messages = all_user_messages

                # Log tiered analysis for debugging
                if message_limit:
                    logger.info(f"[SEARCH] [TIERED FC{message_limit}] Analyzing last {message_limit} comment(s) from @{target}")
                else:
                    logger.info(f"[SEARCH] [FULL FC] Analyzing ALL comments from @{target}")

                return self.grok.fact_check(target, role, emoji_seq)
            elif hasattr(self, 'simple_fact_checker'):
                return self.simple_fact_checker.fact_check(target, requester, role, emoji_seq)
            else:
                return f"@{requester} Fact-checking temporarily unavailable"
        return None

    def _collect_all_user_messages(self, message_limit: Optional[int] = None) -> Dict[str, List]:
        """
        Collect user messages from memory manager for fact-checking.

        Args:
            message_limit: Optional limit on messages per user (None = all messages)
                          If specified, returns the LAST N messages per user

        Returns:
            Dict mapping usernames to lists of message dicts

        Examples:
            _collect_all_user_messages()           # All messages
            _collect_all_user_messages(1)          # Last 1 message per user
            _collect_all_user_messages(5)          # Last 5 messages per user
        """
        all_messages = {}

        try:
            # Get messages from chat memory manager
            if hasattr(self, 'memory_manager') and self.memory_manager:
                # Access the session messages from memory manager
                if hasattr(self.memory_manager, 'session_messages') and self.memory_manager.session_messages:
                    for msg in self.memory_manager.session_messages:
                        # session_messages contains STRINGS like "[MOD] username: message"
                        if isinstance(msg, dict):
                            username = msg.get('author', msg.get('username', 'unknown'))
                            message_text = msg.get('message', msg.get('text', ''))
                        else:
                            # Parse string format: "[ROLE] username: message" or "username: message"
                            msg_str = str(msg)
                            # Remove role prefix if present
                            if msg_str.startswith('['):
                                msg_str = msg_str.split('] ', 1)[-1]  # Remove "[MOD] " prefix

                            # Split on first ": " to get username and message
                            if ': ' in msg_str:
                                username, message_text = msg_str.split(': ', 1)
                            else:
                                username = 'unknown'
                                message_text = msg_str

                        if username not in all_messages:
                            all_messages[username] = []

                        all_messages[username].append({
                            'username': username,
                            'message': message_text,
                            'timestamp': ''  # String format doesn't include timestamp
                        })

                # Also check message buffers for any additional messages
                if hasattr(self.memory_manager, 'message_buffers'):
                    for username, messages in self.memory_manager.message_buffers.items():
                        if username not in all_messages:
                            all_messages[username] = []

                        for msg in messages:
                            if isinstance(msg, dict):
                                message_text = msg.get('message', msg.get('text', ''))
                            else:
                                message_text = str(msg)

                            all_messages[username].append({
                                'username': username,
                                'message': message_text,
                                'timestamp': ''
                            })

        except Exception as e:
            logger.warning(f"Could not collect user messages for fact-checking: {e}")

        # Apply message limit if specified (tiered analysis)
        if message_limit is not None and message_limit > 0:
            limited_messages = {}
            for username, messages in all_messages.items():
                # Take the LAST N messages (most recent)
                limited_messages[username] = messages[-message_limit:]
            logger.info(f"[DATA] [TIERED] Limited to last {message_limit} message(s) per user ({len(all_messages)} users)")
            return limited_messages

        return all_messages

    def _handle_whack_command(self, text: str, username: str, user_id: str, role: str, is_member: bool = False) -> Optional[str]:
        """Delegate whack command handling to CommandHandler."""
        return self.command_handler.handle_whack_command(text, username, user_id, role, is_member)

    def _handle_m2j_command(self, text: str, username: str, user_id: str, role: str) -> Optional[str]:
        """Delegate Move2Japan commands to M2J handler (WSP 95 - Skillz Wardrobe)."""
        if not hasattr(self, '_m2j_handler'):
            self._m2j_handler = None
            if Move2JapanHandler:
                try:
                    self._m2j_handler = Move2JapanHandler()
                    logger.info("\U0001f1ef\U0001f1f5 Move2Japan handler initialized")
                except Exception as exc:
                    logger.error(f"\U0001f1ef\U0001f1f5 Failed to init M2J handler: {exc}")
        if self._m2j_handler:
            # Check for sub-commands (stats, reset)
            info_response = self._m2j_handler.handle_info_command(text, username, user_id)
            if info_response:
                return info_response
            return self._m2j_handler.handle_command(text, username, user_id, role)
        logger.warning("\U0001f1ef\U0001f1f5 M2J handler not available")
        return None
    
    def _handle_timeout_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate timeout event handling to EventHandler."""
        return self.event_handler.handle_timeout_event(event)
    
    def _handle_ban_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate ban event handling to EventHandler."""
        return self.event_handler.handle_ban_event(event)

    def _handle_super_chat_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle Super Chat monetization events.

        $20+ Super Chats trigger YouTube Shorts creation.
        """
        donor_name = event.get("donor_name", "Anonymous")
        donor_id = event.get("donor_id", "")
        amount_usd = event.get("amount_usd", 0.0)
        message = event.get("message", "")
        amount_display = event.get("amount_display", f"${amount_usd:.2f}")

        logger.info(f"💰 Super Chat received: {donor_name} - {amount_display}")

        # Try to import YouTube Shorts handler
        try:
            from modules.communication.youtube_shorts.src.chat_commands import get_shorts_handler
            shorts_handler = get_shorts_handler()

            # Handle $20+ Super Chats for Shorts creation
            response = shorts_handler.handle_super_chat_short(
                donor_name=donor_name,
                donor_id=donor_id,
                amount_usd=amount_usd,
                message=message
            )

            if response:
                logger.info(f"🎬 YouTube Shorts: {response}")
                return {
                    "type": "super_chat_short",
                    "response": response,
                    "donor": donor_name,
                    "amount": amount_display
                }
            else:
                # Below $20 threshold
                logger.info(f"💰 Super Chat below $20 threshold ({amount_display})")
                return {"skip": True, "reason": "below_threshold"}

        except ImportError as e:
            logger.warning(f"YouTube Shorts module not available: {e}")
            return {"skip": True, "reason": "shorts_unavailable"}
        except Exception as e:
            logger.error(f"Error handling Super Chat Short: {e}")
            return {"skip": True, "reason": "error"}

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return {
            "trigger_cooldown": self.trigger_cooldown,
            "maga_cooldown": self.maga_cooldown,
            "global_maga_cooldown": self.global_maga_cooldown,
            "active_users": len(self.last_trigger_time),
            "maga_rate_limited_users": len(self.last_maga_time),
            "last_global_maga_response": self.last_global_maga_time,
            "trigger_emojis": self.trigger_emojis,
            "memory_dir": self.memory_dir,
            "grok_enabled": self.grok is not None,
            "consciousness_enabled": self.consciousness is not None,
            "pqn_enabled": self.pqn_orchestrator is not None
        }

    def _handle_shorts_command(self, text: str, username: str, user_id: str, role: str) -> Optional[str]:
        """
        Handle YouTube Shorts commands by routing to Shorts module.

        Commands:
        - !createshort <topic> - Create and upload Short (OWNER or Top 3 MAGADOOM mods)
        - !shortsora <topic> - Create with Sora2 engine (OWNER or Top 3 MAGADOOM mods)
        - !shortveo <topic> - Create with Veo3 engine (OWNER or Top 3 MAGADOOM mods)
        - !short - List recent shorts (everyone)
        - !shortstatus - Check generation status (everyone)
        - !shortstats - View statistics (everyone)

        Args:
            text: Command text
            username: User's display name
            user_id: User's YouTube ID
            role: User's role (OWNER, MODERATOR, VIEWER)

        Returns:
            str: Response message, or None if command failed
        """
        try:
            from modules.communication.youtube_shorts.src.chat_commands import get_shorts_handler

            # Get Shorts handler instance
            shorts_handler = get_shorts_handler()

            # Route to Shorts module
            response = shorts_handler.handle_shorts_command(
                text=text,
                username=username,
                user_id=user_id,
                role=role
            )

            if response:
                logger.info(f"🎬 YouTube Shorts response: {response[:100]}")
                return response
            else:
                logger.debug(f"🎬 Shorts command '{text}' returned None (not processed)")
                return None

        except Exception as e:
            logger.error(f"🎬[FAIL] Shorts command failed: {e}", exc_info=True)
            return f"@{username} 🎬 Error processing Shorts command. Try again later."

    def _check_pqn_command(self, text: str) -> bool:
        """Check if message contains PQN research commands."""
        text_lower = text.lower()
        pqn_triggers = ['!pqn', '!research', '/pqn', '/research']
        # Also check for common typos
        typo_triggers = ['/pnq', '!pnq', '/pqm', '!pqm']  # Common typos

        return (any(trigger in text_lower for trigger in pqn_triggers) or
                any(trigger in text_lower for trigger in typo_triggers))

    def _handle_pqn_research(self, text: str, author_name: str) -> Optional[str]:
        """Handle PQN research request through orchestrator.

        See: modules/ai_intelligence/pqn_alignment/docs/PQN_CHAT_INTEGRATION.md
        For complete integration specifications and missing implementation details.

        Current Status: Command parsing implemented but NOT integrated in message flow.
        Missing: Event broadcasting, campaign results communication, UTF-8 encoding fix.
        """
        if not self.pqn_orchestrator:
            return f"@{author_name} 🔬 PQN Research: System currently offline. The PQN detector analyzes quantum coherence patterns. Try again later or use !research for basic queries."

        try:
            # Extract research query
            query = text.lower()
            # Remove all possible triggers (including typos)
            all_triggers = ['!pqn', '!research', '/pqn', '/research', '/pnq', '!pnq', '/pqm', '!pqm']
            for trigger in all_triggers:
                query = query.replace(trigger, '').strip()

            if not query:
                return f"@{author_name} 🔬 PQN Research: Please provide a query. Example: !pqn consciousness emergence patterns"

            # Run PQN research (simplified for chat integration)
            logger.info(f"🔬 PQN Research requested by {author_name}: {query}")

            # Provide immediate feedback about what PQN does
            responses = [
                f"@{author_name} 🔬 PQN Research: Analyzing '{query}' for quantum coherence patterns. The PQN detector measures consciousness emergence through spectral analysis.",
                f"@{author_name} 🔬 PQN initiated: '{query}' | Scanning for resonance harmonics and observer collapse patterns in the quantum field.",
                f"@{author_name} 🔬 PQN Analysis: '{query}' | Detecting quantum temporal decoherence and consciousness boundary conditions."
            ]
            import random
            return random.choice(responses)

        except Exception as e:
            logger.error(f"PQN research error: {e}")
            return f"@{author_name} 🔬 PQN Research encountered an error. Please try again." 
