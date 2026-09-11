"""
Comment Processor - Extracted from comment_engagement_dae.py

WSP 62 Refactoring Phase 2: Reduces comment_engagement_dae.py from 1473 → ~1069 lines
Extracted comment engagement and data extraction logic (~404 lines).

Pattern: Dependency injection (driver, stats, reply_executor passed to constructor)
"""

import asyncio
import json
import logging
import os
import random
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# ============================================================================
# CROSS-COMMENT LOOP PREVENTION (ADR-012)
# ============================================================================
# Owned channel names - NEVER reply to comments from these channels
# to prevent infinite cross-commenting loops between our own channels.
# Like/Heart only, no reply. 0102 behavior: Like = silent acknowledgment.
OWNED_CHANNELS = frozenset([
    "Move2Japan",
    "UnDaoDu",
    "FoundUps",
    "Foundups",  # Case variation
    "@Move2Japan",
    "@UnDaoDu",
    "@FoundUps",
    "@Foundups",
])


def is_owned_channel(username: str) -> bool:
    """
    Check if commenter is one of our owned channels.

    ADR-012: Cross-Comment Loop Prevention
    - If True → Like/Heart only, NO REPLY
    - Prevents infinite agent-to-agent commenting

    Args:
        username: Commenter display name or handle

    Returns:
        True if this is an owned channel
    """
    if not username:
        return False
    # Check exact match and handle variations
    clean_name = username.strip().lstrip('@')
    return username in OWNED_CHANNELS or clean_name in OWNED_CHANNELS or f"@{clean_name}" in OWNED_CHANNELS


# Import commenter history store (WSP 60 module memory)
try:
    from modules.communication.video_comments.src.commenter_history_store import (
        get_commenter_history_store,
        make_commenter_key,
    )
    COMMENTER_HISTORY_AVAILABLE = True
except ImportError as e:
    COMMENTER_HISTORY_AVAILABLE = False
    logger.warning(f"[CommentProcessor] Commenter history store not available: {e}")

# Import intelligent reply generator
try:
    from modules.communication.video_comments.src.intelligent_reply_generator import (
        get_reply_generator,
        CommenterType,
    )
    INTELLIGENT_REPLIES_AVAILABLE = True
except ImportError as e:
    INTELLIGENT_REPLIES_AVAILABLE = False
    logger.warning(f"[CommentProcessor] Intelligent replies not available: {e}")

# Import semantic state engine (WSP 44)
try:
    from modules.infrastructure.wsp_core.src.semantic_state_engine import SemanticStateEngine
    SEMANTIC_STATE_AVAILABLE = True
except Exception:
    SemanticStateEngine = None
    SEMANTIC_STATE_AVAILABLE = False

# Optional WRE monitor integration (best-effort)
try:
    from modules.infrastructure.wre_core.wre_monitor import get_monitor
    WRE_MONITOR_AVAILABLE = True
except Exception as e:
    WRE_MONITOR_AVAILABLE = False
    logger.debug(f"[CommentProcessor] WRE monitor unavailable: {e}")


class CommentProcessor:
    """
    Handles comment engagement orchestration and DOM data extraction.

    Responsibilities:
    - Extract comment data from DOM (author, text, timestamps)
    - Orchestrate engagement actions (like, heart, reply)
    - Coordinate with ReplyExecutor for reply posting
    - Update engagement stats
    """

    # Commenter type emoji tags (for debug mode)
    COMMENTER_TYPE_TAGS = {
        "moderator": "🧘",
        "maga_troll": "🤡",
        "subscriber": "🙌",
        "regular": "💬",
        "unknown": "❓",
    }

    CONTEXTUAL_REPLY_SOURCE_MARKERS = (
        "lm_studio",
        "qwen",
        "grok",
        "gemma_emoji",
        "skill_0:",
    )

    @classmethod
    def is_contextual_reply_source(cls, source: Optional[str]) -> bool:
        """Return whether a source receipt proves the reply used comment context."""
        normalized = (source or "unknown").lower()
        return any(marker in normalized for marker in cls.CONTEXTUAL_REPLY_SOURCE_MARKERS)

    def __init__(
        self,
        driver,
        human,
        stats,
        reply_executor,
        selectors,
        vision_descriptions=None,
        use_vision=False,
        use_dom=True,
        ui_tars_bridge=None,
        check_moderators=False,
        mod_lookup=None,
        reply_debug_tags=False,
        video_title=None,
        target_channel_id=None,
        session_id: Optional[str] = None,
    ):
        """
        Args:
            driver: Selenium WebDriver instance
            human: HumanBehavior instance (or None)
            stats: Dict tracking engagement stats
            reply_executor: BrowserReplyExecutor instance
            selectors: Dict of DOM selectors
            vision_descriptions: Dict of vision descriptions for UI-TARS (optional)
            use_vision: Enable vision verification (default False)
            use_dom: Enable DOM-based actions (default True)
            ui_tars_bridge: UITarsBridge instance for vision (optional)
            check_moderators: Enable moderator detection (default False)
            mod_lookup: ModeratorLookup instance (optional)
            reply_debug_tags: Append debug tags to replies (default False)
            video_title: Video title for context-aware replies (optional)
            target_channel_id: Channel receiving the comment (personality routing)
        """
        self.driver = driver
        self.human = human
        self.stats = stats
        self.reply_executor = reply_executor
        self.selectors = selectors
        self.VISION_DESCRIPTIONS = vision_descriptions or {}
        self.use_vision = use_vision
        self.use_dom = use_dom
        self.ui_tars_bridge = ui_tars_bridge
        self.check_moderators = check_moderators
        self.mod_lookup = mod_lookup
        self.reply_debug_tags = reply_debug_tags
        self.video_title = video_title  # NEW (2025-12-30): Video context for alignment detection
        self.target_channel_id = target_channel_id
        self.session_id = session_id or time.strftime("%Y%m%d_%H%M%S")

        # UI-derived action switches (requested: Like/Heart should not fire when UI looks disabled/greyed-out)
        # These switches are dynamic and can flip during a run as UI state changes.
        self.like_ui_switch = True
        self.heart_ui_switch = True

        # Entropy-backed RNG (anti-pattern breaker: "dice-on-dice", not fixed percentages)
        self._rng = random.SystemRandom()

        # Pre-action snapshot storage (keeps a visual audit trail for UI-TARS training/debug)
        # Place under the module memory, not the skill subtree.
        self._module_root = Path(__file__).resolve().parents[4]  # modules/communication/video_comments
        override_dir = os.getenv("YT_UI_SNAPSHOT_DIR")
        self._snap_dir = Path(override_dir) if override_dir else (self._module_root / "memory" / "engagement_sessions" / "ui_action_snapshots")
        self._snap_dir.mkdir(parents=True, exist_ok=True)

        # 0102 behavior interface (single control-plane; legacy values are accepted as aliases)
        try:
            from modules.infrastructure.foundups_selenium.src.human_behavior import get_0102_behavior_interface
            self.behavior_profile = get_0102_behavior_interface(default="0102")
        except Exception:
            # Fallback: keep legacy env vars
            self.behavior_profile = (os.getenv("YT_0102_BEHAVIOR_INTERFACE") or os.getenv("YT_BEHAVIOR_INTERFACE") or os.getenv("YT_BEHAVIOR_PROFILE") or os.getenv("WSP_BEHAVIOR_PROFILE") or "0102").upper()
        self.randomness_mode = (os.getenv("YT_ACTION_RANDOMNESS_MODE") or "dynamic").lower()  # dynamic|fixed

        # Tempo mode: Controls interaction speed with RANDOMIZED ranges
        # Each tempo mode has a (min, max) delay multiplier range for unpredictability
        tempo = os.getenv("YT_ENGAGEMENT_TEMPO", "012").upper()
        # Backward compatibility for fast mode env var
        if os.getenv("YT_ENGAGEMENT_FAST_MODE", "0").lower() in {"1", "true", "yes"}:
            tempo = "MEDIUM"

        # Define tempo ranges: (min_multiplier, max_multiplier)
        if tempo == "FAST":
            self.delay_range = (0.05, 0.20)   # 5-20x faster - rapid testing with variance
        elif tempo == "MEDIUM":
            self.delay_range = (0.15, 0.40)   # 2.5-7x faster - quick diagnostics with variance
        else:  # 012 mode - human-like with natural variance
            self.delay_range = (0.6, 1.5)     # Sometimes faster, sometimes slower than baseline

        # Legacy compatibility: use midpoint for fixed calculations
        self.delay_multiplier = (self.delay_range[0] + self.delay_range[1]) / 2

        # Randomize order of Like/Heart/Reply operations (anti-detection)
        self.randomize_action_order = os.getenv("YT_RANDOMIZE_ACTION_ORDER", "true").lower() in ("1", "true", "yes")

        logger.info(f"[CommentProcessor] TEMPO set to {tempo} (range: {self.delay_range[0]:.2f}x-{self.delay_range[1]:.2f}x)")
        logger.info(f"[CommentProcessor] Action order randomization: {'ENABLED' if self.randomize_action_order else 'DISABLED'}")

        # Reply layer switches (for incremental testing of refactored code)
        from modules.communication.livechat.src.automation_gates import _env_truthy
        self.reply_basic_only = _env_truthy("YT_REPLY_BASIC_ONLY", "false")
        self.no_classification = _env_truthy("YT_NO_CLASSIFICATION", "false")
        self.no_semantic_state = _env_truthy("YT_NO_SEMANTIC_STATE", "false")
        self.action_debug = _env_truthy("YT_ACTION_LOGS", "true")
        enable_wre = _env_truthy("FOUNDUPS_ENABLE_WRE", "true")
        enable_wre_monitor = _env_truthy("FOUNDUPS_ENABLE_WRE_MONITOR", "true")
        self.wre_action_learning = _env_truthy("WRE_ACTION_LEARNING", "true") and enable_wre and enable_wre_monitor
        self.wre_action_logs = _env_truthy("WRE_ACTION_LOGS", "false")
        
        # 012 Behavior: Configurable action probabilities (human-like randomization)
        # These control the "should_perform_action()" probability for each action
        self.like_probability = float(os.getenv("YT_012_LIKE_PROB", "0.85"))      # 85% default
        self.heart_probability = float(os.getenv("YT_012_HEART_PROB", "0.90"))    # 90% default
        self.reply_skip_probability = float(os.getenv("YT_012_REPLY_SKIP_PROB", "0.50"))  # 50% skip for Tier 1
        
        if tempo == "012" or self.delay_multiplier == 1.0:
            logger.info(f"[012-BEHAVIOR] Like prob: {self.like_probability}, Heart prob: {self.heart_probability}, Reply skip: {self.reply_skip_probability}")
        
        self.wre_monitor = None
        if self.wre_action_learning and WRE_MONITOR_AVAILABLE:
            try:
                self.wre_monitor = get_monitor()
                if self.wre_action_logs:
                    logger.info("[CommentProcessor] WRE action learning enabled")
            except Exception as e:
                self.wre_monitor = None
                logger.debug(f"[CommentProcessor] WRE monitor unavailable: {e}")

        if self.reply_basic_only:
            logger.info("[CommentProcessor] REPLY BASIC ONLY mode - skipping all AI layers")
        if self.no_classification:
            logger.info("[CommentProcessor] Classification layer DISABLED")
        if self.no_semantic_state:
            logger.info("[CommentProcessor] Semantic state layer DISABLED")
        if self.action_debug:
            logger.info("[CommentProcessor] Action logging enabled (YT_ACTION_LOGS=true)")

    @dataclass
    class _UIActionState:
        found: bool
        disabled: bool
        pressed: bool
        aria_pressed: Optional[str] = None
        aria_disabled: Optional[str] = None
        opacity: Optional[float] = None
        pointer_events: Optional[str] = None
        notes: Optional[str] = None

    def _clamp01(self, x: float) -> float:
        return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)

    def _get_random_delay_multiplier(self) -> float:
        """
        Get a randomized delay multiplier from the configured range.
        Uses beta distribution for natural human-like variance (more likely near middle).
        """
        min_mult, max_mult = self.delay_range
        # Beta distribution biased slightly toward middle (alpha=2, beta=2)
        # but with random shape for unpredictability
        alpha = 1.5 + self._rng.random() * 1.5  # 1.5-3.0
        beta = 1.5 + self._rng.random() * 1.5   # 1.5-3.0
        normalized = self._rng.betavariate(alpha, beta)
        multiplier = min_mult + (max_mult - min_mult) * normalized
        return multiplier

    def _randomize_action_queue(self, actions: list) -> list:
        """
        Shuffle action order to avoid detectable patterns.
        Sometimes Like first, sometimes Heart first, etc.
        Reply is typically last (needs comment data) but 20% chance it moves earlier.
        """
        if not self.randomize_action_order or len(actions) <= 1:
            return actions

        # Separate reply from reactions (reply usually needs to be later)
        reactions = [a for a in actions if a in ('like', 'heart')]
        reply = [a for a in actions if a == 'reply']

        # Shuffle reactions
        self._rng.shuffle(reactions)

        # 20% chance to interleave reply among reactions (human unpredictability)
        if reply and self._rng.random() < 0.20 and len(reactions) >= 2:
            insert_pos = self._rng.randint(1, len(reactions))  # After at least 1 reaction
            reactions.insert(insert_pos, reply[0])
            result = reactions
        else:
            result = reactions + reply

        logger.debug(f"[ANTI-DETECT] Action order randomized: {result}")
        return result

    def _dynamic_probability(self, base_bias: float) -> float:
        """
        "Dice on dice" probability: draw a probability distribution, then draw an outcome.
        - base_bias is a gentle attractor (not a fixed percent).
        - output changes each decision (no stable signature).
        """
        b = self._clamp01(float(base_bias))

        # 0102 interface: higher variability by design (anti-fingerprint)
        jitter_max = 0.30
        jitter = self._rng.random() * jitter_max
        b2 = self._clamp01(b + self._rng.uniform(-jitter, jitter))

        # Random concentration (how "certain" today's mood is)
        # Lower -> more extreme swings; higher -> tighter around b2.
        k = 0.6 + 9.0 * (self._rng.random() ** 2.0)
        alpha = max(0.2, b2 * k)
        beta = max(0.2, (1.0 - b2) * k)

        p = self._rng.betavariate(alpha, beta)

        # Rare pattern breakers (humans do weird things)
        # - small chance to force-skip
        # - tiny chance to force-do
        if self._rng.random() < 0.02:
            return 0.0
        if self._rng.random() < 0.01:
            return 1.0

        return self._clamp01(p)

    def _should_attempt(self, action: str, base_bias: float) -> tuple[bool, float]:
        """
        Decide whether to attempt an action (like/heart/reply) using:
        - fixed mode: legacy percent thresholds (for deterministic testing)
        - dynamic mode: entropy-backed dice-on-dice (default)
        """
        if self.randomness_mode == "fixed":
            p = self._clamp01(base_bias)
        else:
            p = self._dynamic_probability(base_bias)
        return (self._rng.random() < p), p

    def _capture_pre_action_snapshot(self, *, action: str, comment_idx: int, ui_state: Dict[str, Any]) -> Optional[str]:
        """
        Save a viewport screenshot + minimal metadata before attempting UI actions.
        This is the "UI-TARS tars gate" requested: picture first, then decide/act.
        """
        # 2026-02-04: Default OFF (saves ~1-2s per comment from disk I/O + PNG capture)
        enabled = os.getenv("YT_UI_PRE_ACTION_SNAPSHOT", "false").lower() in {"1", "true", "yes"}
        if not enabled:
            return None

        ts = time.strftime("%Y%m%d_%H%M%S")
        base = f"{self.session_id}_c{comment_idx}_{action}_{ts}"
        png_path = self._snap_dir / f"{base}.png"
        json_path = self._snap_dir / f"{base}.json"

        try:
            png_bytes = self.driver.get_screenshot_as_png()
            png_path.write_bytes(png_bytes)
            json_path.write_text(
                json.dumps(
                    {
                        "session_id": self.session_id,
                        "timestamp": ts,
                        "action": action,
                        "comment_idx": comment_idx,
                        "behavior_profile": self.behavior_profile,
                        "ui_state": ui_state,
                        "url": getattr(self.driver, "current_url", None),
                    },
                    ensure_ascii=True,
                    indent=2,
                ),
                encoding="utf-8",
            )
            return str(png_path)
        except Exception as e:
            logger.debug(f"[UI-SNAPSHOT] Failed to capture snapshot for {action}: {e}")
            return None

    def _read_action_ui_state(self, comment_idx: int, element_type: str) -> "_UIActionState":
        """
        Determine whether like/heart looks enabled to a human.
        We treat "greyed out" as disabled/unactionable (aria-disabled/disabled/pointer-events/low opacity).
        Also detect "already pressed" to avoid toggling off (safety).
        """
        element_selector = self.selectors[element_type]
        thread_selector = self.selectors["comment_thread"]

        script = f"""
        const threadIndex = arguments[0];
        const targetSelector = arguments[1];

        function findInShadow(root, selector) {{
            if (!root) return null;
            try {{
                const el = root.querySelector(selector);
                if (el) return el;
            }} catch (e) {{}}
            const children = root.querySelectorAll ? root.querySelectorAll('*') : [];
            for (let child of children) {{
                if (child && child.shadowRoot) {{
                    const found = findInShadow(child.shadowRoot, selector);
                    if (found) return found;
                }}
            }}
            return null;
        }}

        function collectThreads() {{
            const direct = document.querySelectorAll('{thread_selector}');
            if (direct && direct.length) return Array.from(direct);
            const results = [];
            const stack = [document];
            while (stack.length) {{
                const node = stack.pop();
                if (!node || !node.querySelectorAll) continue;
                try {{
                    const found = node.querySelectorAll('{thread_selector}');
                    for (const el of found) results.push(el);
                }} catch (e) {{}}
                const children = node.querySelectorAll('*');
                for (const child of children) {{
                    if (child && child.shadowRoot) stack.push(child.shadowRoot);
                }}
            }}
            return results;
        }}

        const threads = collectThreads();
        if (!threads || threads.length <= threadIndex) {{
            return {{ found: false, error: 'Thread not found' }};
        }}
        const thread = threads[threadIndex];
        const startNode = thread.shadowRoot || thread;
        const raw = findInShadow(startNode, targetSelector);
        if (!raw) {{
            return {{ found: false, error: 'Target not found' }};
        }}

        // Many YT components wrap a <button> or role=button.
        const el = raw.closest && (raw.closest('button,[role="button"]') || raw) || raw;

        const ariaPressed = el.getAttribute && (el.getAttribute('aria-pressed') || el.getAttribute('aria-checked')) || null;
        const ariaDisabled = el.getAttribute && el.getAttribute('aria-disabled') || null;
        const disabledAttr = el.hasAttribute ? el.hasAttribute('disabled') : false;
        const disabledProp = (typeof el.disabled === 'boolean') ? el.disabled : false;

        const style = window.getComputedStyle ? window.getComputedStyle(el) : null;
        const opacity = style ? parseFloat(style.opacity || '1') : null;
        const pointerEvents = style ? (style.pointerEvents || null) : null;
        const cursor = style ? (style.cursor || null) : null;

        // "Greyed out" heuristic: unclickable or clearly disabled.
        const disabled = Boolean(disabledProp || disabledAttr || ariaDisabled === 'true' || pointerEvents === 'none' || (opacity !== null && opacity < 0.55));

        // "Pressed" safety: if it looks already toggled on, do not click again.
        const pressed = (ariaPressed === 'true');

        return {{
            found: true,
            disabled,
            pressed,
            aria_pressed: ariaPressed,
            aria_disabled: ariaDisabled,
            opacity,
            pointer_events: pointerEvents,
            cursor,
        }};
        """

        try:
            raw = self.driver.execute_script(script, comment_idx - 1, element_selector) or {}
            if not raw.get("found"):
                return self._UIActionState(found=False, disabled=True, pressed=False, notes=raw.get("error") or "not_found")
            return self._UIActionState(
                found=True,
                disabled=bool(raw.get("disabled")),
                pressed=bool(raw.get("pressed")),
                aria_pressed=raw.get("aria_pressed"),
                aria_disabled=raw.get("aria_disabled"),
                opacity=raw.get("opacity"),
                pointer_events=raw.get("pointer_events"),
                notes=None,
            )
        except Exception as e:
            return self._UIActionState(found=False, disabled=True, pressed=False, notes=f"ui_state_exception:{e}")

    async def click_element_dom(self, comment_idx: int, element_type: str) -> bool:
        """
        Phase 2: Agentic - Robust DOM click execution with Shadow DOM piercing.

        Args:
            comment_idx: 1-based comment index
            element_type: 'like', 'heart'

        Anti-Detection (WSP 49):
        - Uses Deep Shadow DOM Querying to find elements hidden in Shadow Roots
        - Fallback: execute_script() with recursive traversal
        """
        from selenium.webdriver.common.by import By
        from selenium.common.exceptions import NoSuchElementException

        element_selector = self.selectors[element_type]
        thread_selector = self.selectors["comment_thread"]

        # ROBUST SHADOW DOM SCRIPT
        # This script defines a recursive function to walk the DOM and Shadow DOMs
        find_and_click_script = f"""
        const threadIndex = arguments[0];
        const targetSelector = arguments[1];

        function findInShadow(root, selector) {{
            if (!root) return null;

            // direct check
            const el = root.querySelector(selector);
            if (el) return el;

            // recursive check in children with shadow roots
            const children = root.querySelectorAll('*');
            for (let child of children) {{
                if (child.shadowRoot) {{
                    const found = findInShadow(child.shadowRoot, selector);
                    if (found) return found;
                }}
            }}
            return null;
        }}

        function collectThreads() {{
            const direct = document.querySelectorAll('{thread_selector}');
            if (direct && direct.length) return Array.from(direct);
            const results = [];
            const stack = [document];
            while (stack.length) {{
                const node = stack.pop();
                if (!node || !node.querySelectorAll) continue;
                try {{
                    const found = node.querySelectorAll('{thread_selector}');
                    for (const el of found) results.push(el);
                }} catch (e) {{}}
                const children = node.querySelectorAll('*');
                for (const child of children) {{
                    if (child.shadowRoot) stack.push(child.shadowRoot);
                }}
            }}
            return results;
        }}

        const threads = collectThreads();
        if (!threads || threads.length <= threadIndex) {{
            return {{success: false, error: 'Thread ' + threadIndex + ' not found'}};
        }}
        const thread = threads[threadIndex];
        
        // Try finding element deep in shadow DOM
        // Start from thread (container) or its shadow root
        const startNode = thread.shadowRoot || thread;
        const targetElement = findInShadow(startNode, targetSelector);

        if (targetElement) {{
            targetElement.scrollIntoView({{behavior: 'smooth', block: 'center'}});
            targetElement.click();
            return {{success: true}};
        }} else {{
            return {{success: false, error: 'Element ' + targetSelector + ' not found in Deep Shadow DOM'}};
        }}
        """

        try:
            # Execute the robust script
            result = self.driver.execute_script(find_and_click_script, comment_idx - 1, element_selector)
            
            success = result.get('success', False)
            if success:
                logger.info(f"[DOM] {element_type.upper()} clicked via Deep Shadow Query")
                return True
            else:
                logger.warning(f"[DOM] {element_type.upper()} click failed: {result.get('error')}")
                return False

        except Exception as e:
            logger.warning(f"[DOM] {element_type} click script exception: {e}")
            return False

    async def hide_user_from_channel(self, comment_idx: int, username: str) -> bool:
        """
        ANTI-SPAM NUCLEAR OPTION: Hide user from channel.

        This permanently blocks the user and removes ALL their comments.
        Use only for confirmed spam trolls (>2 rate limit violations).

        Args:
            comment_idx: 1-based comment index
            username: Username for logging

        Returns:
            bool: True if hide successful, False otherwise
        """
        import asyncio

        logger.warning(f"[ANTI-SPAM] ☢️ HIDING USER FROM CHANNEL: @{username}")
        logger.warning(f"[ANTI-SPAM]   This will permanently block user and remove ALL comments")

        action_menu_selector = self.selectors['action_menu']
        thread_selector = self.selectors["comment_thread"]

        # STEP 1: Click action menu (3-dot icon)
        click_menu_script = f"""
        const threadIndex = arguments[0];
        const menuSelector = arguments[1];

        function findInShadow(root, selector) {{
            if (!root) return null;
            const el = root.querySelector(selector);
            if (el) return el;
            const children = root.querySelectorAll('*');
            for (let child of children) {{
                if (child.shadowRoot) {{
                    const found = findInShadow(child.shadowRoot, selector);
                    if (found) return found;
                }}
            }}
            return null;
        }}

        const threads = document.querySelectorAll('{thread_selector}');
        if (!threads || threads.length <= threadIndex) {{
            return {{success: false, error: 'Thread not found'}};
        }}
        const thread = threads[threadIndex];
        const startNode = thread.shadowRoot || thread;
        const menuButton = findInShadow(startNode, menuSelector);

        if (menuButton) {{
            menuButton.scrollIntoView({{behavior: 'smooth', block: 'center'}});
            menuButton.click();
            return {{success: true}};
        }} else {{
            return {{success: false, error: 'Action menu button not found'}};
        }}
        """

        try:
            # Click action menu
            result = self.driver.execute_script(click_menu_script, comment_idx - 1, action_menu_selector)
            if not result.get('success'):
                logger.error(f"[ANTI-SPAM] Failed to open action menu: {result.get('error')}")
                return False

            logger.info(f"[ANTI-SPAM] ✓ Action menu opened")
            await asyncio.sleep(0.5 * self._get_random_delay_multiplier())  # Wait for menu to appear

            # STEP 2: Click "Hide user from channel" option
            # Find the menu item with text "Hide user from channel"
            click_hide_script = """
            const items = document.querySelectorAll('tp-yt-paper-item');
            for (let item of items) {
                if (item.textContent.includes('Hide user from channel')) {
                    item.click();
                    return {success: true};
                }
            }
            return {success: false, error: 'Hide user option not found'};
            """

            result = self.driver.execute_script(click_hide_script)
            if not result.get('success'):
                logger.error(f"[ANTI-SPAM] Failed to click hide option: {result.get('error')}")
                return False

            logger.warning(f"[ANTI-SPAM] ☢️ USER HIDDEN: @{username} banned from channel")
            await asyncio.sleep(1.0 * self._get_random_delay_multiplier())  # Wait for action to complete

            return True

        except Exception as e:
            logger.error(f"[ANTI-SPAM] Error hiding user: {e}")
            return False

    def extract_comment_data(self, comment_idx: int) -> Dict[str, Any]:
        """
        Extract comment text and author info from DOM.
        
        Phase 0: Knowledge - Gather commenter information
        
        DOM Structure (YouTube Studio):
        - Comment text: yt-formatted-string#content-text
        - Author name: Link with channel URL or #author-text
        - Mod badge: Various badge selectors
        """
        try:
            data = self.driver.execute_script(r"""
                function collectThreads(selector) {
                    const direct = document.querySelectorAll(selector);
                    if (direct && direct.length) return Array.from(direct);
                    const results = [];
                    const stack = [document];
                    while (stack.length) {
                        const node = stack.pop();
                        if (!node || !node.querySelectorAll) continue;
                        try {
                            const found = node.querySelectorAll(selector);
                            for (const el of found) results.push(el);
                        } catch (e) {}
                        const children = node.querySelectorAll('*');
                        for (const child of children) {
                            if (child.shadowRoot) stack.push(child.shadowRoot);
                        }
                    }
                    return results;
                }

                const threads = collectThreads('ytcp-comment-thread');
                const thread = threads[arguments[0]];
                if (!thread) return null;
                
                // Extract comment text from yt-formatted-string#content-text
                // This is the actual comment content element
                let text = '';
                const contentText = thread.querySelector('yt-formatted-string#content-text');
                if (contentText) {
                    text = contentText.textContent.trim();
                } else {
                    // Fallback selectors
                    const contentEl = thread.querySelector('#content, .comment-text, ytcp-comment-renderer');
                    text = contentEl ? contentEl.textContent.trim() : '';
                }
                
                // Extract author handle/name and channel ID
                let authorName = 'Unknown';
                let authorHandle = 'Unknown';
                let channelId = null;
                const authorEl = thread.querySelector('#author-text, yt-formatted-string.author-text, a#name, .author-name, a[href*="/channel/"], a[href^="/@"]');
                if (authorEl) {
                    const raw = authorEl.textContent.trim().replace(/\\s+/g, ' ');
                    authorHandle = raw;
                    authorName = raw.replace(/^@/, '');

                    // Extract channel ID from href (if available)
                    const authorLink = thread.querySelector('a[href*="/channel/"]');
                    if (authorLink) {
                        const href = authorLink.href;
                        const match = href.match(/\/channel\/([^\/\?]+)/);
                        if (match) {
                            channelId = match[1];
                        }
                    }
                }

                // Check for mod badge (moderator indicator)
                const modBadge = thread.querySelector('.mod-badge, [aria-label*="Moderator"], .moderator-badge');
                const isMod = !!modBadge;

                // Check for subscriber/member badge
                const subBadge = thread.querySelector('.subscriber-badge, [aria-label*="Member"], .member-badge');
                const isSubscriber = !!subBadge;

                // Extract published time (e.g., "3 months ago", "1 year ago")
                // FIX (2025-12-30): YouTube Studio uses different selectors than regular YouTube
                // FIX (2025-12-30): Enhanced selectors for YouTube Studio comment inbox
                let publishedTime = null;

                // Try multiple selectors (YouTube Studio + regular YouTube)
                // Ordered by specificity - most specific first
                const timeSelectors = [
                    // YouTube Studio specific (2025-12-30 enhanced)
                    'span.published-time',                       // Direct span class
                    '#published-time',                           // ID-based
                    'ytcp-comment-view-model #published-time',   // Studio model with ID
                    'ytcp-comment-view #published-time',         // Studio view with ID
                    '.ytcp-comment-header span',                 // Header span (often contains time)
                    '#header #published-time-text',              // Header published time
                    // Regular YouTube selectors
                    'yt-formatted-string.published-time-text',   // Regular YouTube
                    '.published-time-text',                      // Regular YouTube (class)
                    '#published-time-text',                      // ID-based
                    'ytcp-comment-view span:not(.author)',       // YouTube Studio: spans that aren't author
                    '.ytcp-comment-view-model span',             // YouTube Studio model
                    '[slot="published-time"]',                   // Slot-based
                ];

                for (const selector of timeSelectors) {
                    const el = thread.querySelector(selector);
                    if (el && el.textContent.includes('ago')) {
                        publishedTime = el.textContent.trim();
                        console.log('[DOM-DEBUG] Found time via selector:', selector, publishedTime);
                        break;
                    }
                }

                // Fallback 1: Search spans for "ago" pattern
                if (!publishedTime) {
                    const spans = thread.querySelectorAll('span');
                    for (const span of spans) {
                        const text = span.textContent.trim();
                        if (text.includes('ago') && /\d+/.test(text)) {
                            publishedTime = text;
                            console.log('[DOM-DEBUG] Found time via span scan:', publishedTime);
                            break;
                        }
                    }
                }

                // Fallback 2: Search for any text containing "ago" pattern in full thread text
                if (!publishedTime) {
                    const allText = thread.textContent;
                    // Enhanced regex: handles "yr", "mo", abbreviated forms
                    const agoMatch = allText.match(/(\d+\s*(?:second|minute|hour|day|week|month|year|yr|mo|wk|hr|min|sec)s?\s*ago)/i);
                    if (agoMatch) {
                        publishedTime = agoMatch[1];
                        console.log('[DOM-DEBUG] Found time via regex fallback:', publishedTime);
                    }
                }

                // Fallback 3: Look for relative time patterns like "Edited 1 year ago"
                if (!publishedTime) {
                    const allText = thread.textContent;
                    const editedMatch = allText.match(/(?:edited\s+)?(\d+\s*(?:second|minute|hour|day|week|month|year)s?\s*ago)/i);
                    if (editedMatch) {
                        publishedTime = editedMatch[1];
                        console.log('[DOM-DEBUG] Found time via edited pattern:', publishedTime);
                    }
                }

                // Extract the exact video context for this inbox row. Studio inbox
                // can mix comments from many videos, so a DAE-wide title is unsafe.
                let videoTitle = null;
                let videoId = null;
                let videoUrl = null;
                const videoTitleSelectors = [
                    'ytcp-video-thumbnail-with-info #video-title',
                    'ytcp-video-thumbnail-with-info [title]',
                    'a#video-title',
                    '#video-title',
                    '[data-video-title]',
                    '[class*="video-title"]'
                ];
                for (const selector of videoTitleSelectors) {
                    const el = thread.querySelector(selector);
                    if (!el) continue;
                    const candidate = (
                        el.getAttribute('title') ||
                        el.getAttribute('aria-label') ||
                        el.getAttribute('data-video-title') ||
                        el.textContent || ''
                    ).trim().replace(/\s+/g, ' ');
                    if (candidate) {
                        videoTitle = candidate.substring(0, 300);
                        break;
                    }
                }

                const links = thread.querySelectorAll('a[href]');
                for (const link of links) {
                    const href = link.href || link.getAttribute('href') || '';
                    let match = href.match(/\/video\/([^\/?#]+)/);
                    if (!match) match = href.match(/[?&]v=([^&#]+)/);
                    if (!match) match = href.match(/\/shorts\/([^\/?#]+)/);
                    if (!match) continue;
                    videoId = match[1];
                    videoUrl = href;
                    if (!videoTitle) {
                        const candidate = (
                            link.getAttribute('title') ||
                            link.getAttribute('aria-label') ||
                            link.textContent || ''
                        ).trim().replace(/\s+/g, ' ');
                        if (candidate) videoTitle = candidate.substring(0, 300);
                    }
                    break;
                }

                return {
                    text: text.substring(0, 500),
                    author_name: authorName,
                    author_handle: authorHandle,
                    channel_id: channelId,
                    is_mod: isMod,
                    is_subscriber: isSubscriber,
                    published_time: publishedTime,
                    video_title: videoTitle,
                    video_id: videoId,
                    video_url: videoUrl
                };
            """, comment_idx - 1)
            
            if data:
                logger.info(
                    "[DAE] Extracted comment by %s (ID: %s, len=%s)",
                    data.get("author_name"),
                    data.get("channel_id", "N/A"),
                    len(data.get("text", "") or ""),
                )
                # FIX (2025-12-30): Log published_time for debugging
                published_time = data.get("published_time")
                if published_time:
                    logger.info(f"[DAE] 📅 Comment age: '{published_time}'")
                else:
                    logger.warning("[DAE] ⚠️ Could not extract published_time from DOM")
                if data.get("video_title") or data.get("video_id"):
                    logger.info(
                        "[DAE] Video context: title=%r id=%s",
                        data.get("video_title"),
                        data.get("video_id") or "unknown",
                    )
                else:
                    logger.warning("[DAE] No per-comment video context found in Studio DOM")
                return data
            else:
                # OCCAM'S RAZOR: No DOM thread at index = no comment exists
                # Return None instead of fallback dict (first principles detection)
                logger.debug(f"[DAE] No DOM thread at index - comment doesn't exist")
                return None

        except Exception as e:
            logger.warning(f"[DAE] Failed to extract comment data: {e}")
            return {
                'text': '',
                'author_name': 'Unknown',
                'channel_id': None,
                'is_mod': False,
                'is_subscriber': False,
                'published_time': None,
                'video_title': None,
                'video_id': None,
                'video_url': None,
            }

    @staticmethod
    def parse_comment_age_days(published_time: str) -> Optional[int]:
        """
        Parse published time string to approximate days ago.

        Examples:
            "3 months ago" -> 90
            "1 day ago" -> 1
            "5 weeks ago" -> 35
            "2 years ago" -> 730

        Returns:
            Days ago (int) or None if unable to parse
        """
        if not published_time:
            logger.info("[DATE-CHECK] 📅 No published time available")
            return None

        import re
        logger.info(f"[DATE-CHECK] 📅 Checking comment age: '{published_time}'")

        # Normalize text
        text = published_time.lower().strip()

        # Extract number and unit
        match = re.search(r'(\d+)\s*(second|minute|hour|day|week|month|year)', text)
        if not match:
            return None

        value = int(match.group(1))
        unit = match.group(2)

        # Convert to days (approximate)
        conversions = {
            'second': value / 86400,
            'minute': value / 1440,
            'hour': value / 24,
            'day': value,
            'week': value * 7,
            'month': value * 30,  # Approximate
            'year': value * 365
        }

        days = conversions.get(unit, 0)
        return int(days)
    
    async def engage_comment(
        self,
        comment_idx: int,
        do_like: bool = True,
        do_heart: bool = True,
        reply_text: str = "",
        do_reply: bool = True,
        use_intelligent_reply: bool = True
    ) -> Dict[str, Any]:
        """
        Engage with a single comment: Like + Heart + Reply.

        Phase 0: Knowledge - Extract commenter info
        Phase 1: Protocol - Decision on actions and response type
        Phase 2: Agentic - Execution with verification

        Args:
            comment_idx: 1-based comment index
            do_like: Execute like action
            do_heart: Execute heart action
            reply_text: Custom reply text (overrides intelligent reply if provided)
            do_reply: Execute reply action (WSP 91 switch - default True)
            use_intelligent_reply: Use intelligent reply generator (default True)
        """
        results = {
            'comment_idx': comment_idx,
            'like': False,
            'heart': False,
            'reply': False,
            'author_name': 'Unknown',
            'commenter_type': 'unknown',
            'errors': [],
        }

        action_plan = {
            "like": {"requested": bool(do_like), "intended": bool(do_like), "attempted": False, "success": False, "path": "skipped", "reason": None},
            "heart": {"requested": bool(do_heart), "intended": bool(do_heart), "attempted": False, "success": False, "path": "skipped", "reason": None},
            "reply": {"requested": bool(do_reply), "intended": bool(do_reply), "attempted": False, "success": False, "path": "skipped", "reason": None},
        }
        reply_text_to_post = ""
        used_intelligent = False
        
        # Phase 0: Knowledge - Extract comment data
        logger.info(f"[CARDIOVASCULAR] [PROCESS-COMMENT-{comment_idx}] ═══ START ═══")
        logger.info(f"[DAE-ENGAGE]   Flags: Like={do_like} | Heart={do_heart} | Reply={do_reply}")

        comment_data = self.extract_comment_data(comment_idx)

        # OCCAM'S RAZOR: If extract returns None, no comment exists (DOM element missing)
        if comment_data is None:
            logger.info(f"[DAE-ENGAGE] ⚪ NO COMMENT at index {comment_idx} - DOM thread doesn't exist")
            logger.info(f"[DAE] NO COMMENTS - First principles detection (no DOM element)")
            return {
                'comment_idx': comment_idx,
                'no_comment_exists': True,  # Signal to DAE: stop loop
                'like': False,
                'heart': False,
                'reply': False,
                'author_name': 'N/A',
                'commenter_type': 'none',
                'errors': ['No DOM thread at index']
            }

        results['author_name'] = comment_data.get('author_name', 'Unknown')
        results["commenter_handle"] = comment_data.get("author_handle") or comment_data.get("author_name") or "Unknown"
        results["commenter_channel_id"] = comment_data.get("channel_id")
        # Training Mode: Capture comment text for transcript (Task 3)
        results["comment_text"] = comment_data.get('text', '')[:500]  # Truncate for storage
        results["video_title"] = comment_data.get("video_title") or self.video_title
        results["video_id"] = comment_data.get("video_id")
        results["video_url"] = comment_data.get("video_url")
        try:
            context_flags = self._get_context_flags(comment_data)
        except Exception as e:
            logger.warning(f"[DAE-ENGAGE] Context flags extraction failed: {e}")
            context_flags = {}
        results["context"] = context_flags

        logger.info(f"[DAE-ENGAGE] Processing comment {comment_idx} from {results['author_name']}...")
        logger.info(f"[DAE-ENGAGE]   Comment text: {comment_data.get('text', '')[:100]}...")

        # ============================================================
        # ADR-012: CROSS-COMMENT LOOP PREVENTION
        # ============================================================
        # Check if commenter is one of our owned channels
        # If so: Like/Heart ONLY, NO REPLY (prevents infinite loop)
        commenter_name = results.get('author_name', '')
        if is_owned_channel(commenter_name):
            logger.info(f"[ADR-012] 🔄 OWNED CHANNEL DETECTED: {commenter_name}")
            logger.info(f"[ADR-012]   → Suppressing REPLY to prevent cross-comment loop")
            logger.info(f"[ADR-012]   → Will still Like/Heart (silent acknowledgment)")
            do_reply = False  # Override: Never reply to own channels
            action_plan["reply"]["intended"] = False
            action_plan["reply"]["reason"] = "ADR-012: Owned channel - loop prevention"
            results['owned_channel_detected'] = True

        if os.getenv("YT_OCCAM_MODE", "false").lower() == "true":
             # Occam mode now uses the standard path BUT the standard path is now HARBED against AI failure.
             # This logging is kept just for confirmation.
             logger.info("[OCCAM] Mode active via Environment Variable - All AI layers will fallback if slow.")

        # Phase 0.5: Moderator Detection - Check if commenter is active moderator
        if self.check_moderators and self.mod_lookup and comment_data.get('channel_id'):
            channel_id = comment_data['channel_id']
            is_active_mod, mod_name = self.mod_lookup.is_active_moderator(
                channel_id,
                activity_window_minutes=10
            )

            if is_active_mod:
                logger.info(f"[MOD-DETECT] [POSTER-LOOKUP] 🔍 Verified in DB: @{mod_name} (ACTIVE MODERATOR)")
                self.stats['moderators_detected'] += 1
                results['moderator_detected'] = True
                results['moderator_name'] = mod_name

                # TODO: Post notification to live chat (requires AutoModeratorDAE integration)
                # For now, just log the detection
            else:
                logger.info(f"[MOD-DETECT] [POSTER-LOOKUP] 🔍 User not in moderator DB")
                results['moderator_detected'] = False
        else:
            results['moderator_detected'] = False

        # Detect whether DOM comment threads are accessible (YouTube Studio often uses shadow DOM)
        dom_threads_accessible = self.get_comment_count() > 0
        if not dom_threads_accessible and self.use_vision:
            logger.info("[DAE] DOM comment threads not accessible - using UI-TARS vision fallback")
        if self.action_debug:
            logger.info(
                "[DAE-ENGAGE]   dom_threads_accessible=%s use_dom=%s use_vision=%s ui_tars=%s",
                dom_threads_accessible,
                self.use_dom,
                self.use_vision,
                bool(self.ui_tars_bridge),
            )

        # Anti-Detection (WSP 49): Random action order + probabilistic execution
        # Build action queue with requested actions
        action_queue = []
        if do_like:
            action_queue.append('like')
        if do_heart:
            action_queue.append('heart')
        # Reply will be added to queue later after intelligent reply generation

        # Shuffle action order (humans don't always like→heart→reply in same sequence)
        if do_reply:
            action_queue.append('reply')
        action_queue = self._randomize_action_queue(action_queue)
        logger.info(f"  [ANTI-DETECT] Randomized action order: {' → '.join(action_queue)}")

        # 1. LIKE
        if do_like:
            action_plan["like"]["intended"] = True

            # UI-TARS gate: snapshot + UI-state derived switch (skip if greyed-out/disabled)
            like_ui = self._read_action_ui_state(comment_idx, "like")
            self.like_ui_switch = (not like_ui.disabled)
            self._capture_pre_action_snapshot(
                action="like",
                comment_idx=comment_idx,
                ui_state={
                    "found": like_ui.found,
                    "disabled": like_ui.disabled,
                    "pressed": like_ui.pressed,
                    "aria_pressed": like_ui.aria_pressed,
                    "aria_disabled": like_ui.aria_disabled,
                    "opacity": like_ui.opacity,
                    "pointer_events": like_ui.pointer_events,
                    "notes": like_ui.notes,
                },
            )

            if not self.like_ui_switch:
                action_plan["like"]["intended"] = False
                action_plan["like"]["reason"] = "ui_disabled_or_greyed"
                logger.info("  [LIKE] UI switch OFF (disabled/greyed) - skipping to avoid detection signature")
                results["like"] = False
            elif like_ui.pressed:
                action_plan["like"]["intended"] = False
                action_plan["like"]["reason"] = "already_liked"
                logger.info("  [LIKE] Already liked (pressed) - skipping to avoid unliking")
                results["like"] = False
            else:
                # Probabilistic execution (dynamic by default; fixed if YT_ACTION_RANDOMNESS_MODE=fixed)
                do_it, p = self._should_attempt("like", self.like_probability)
                if not do_it:
                    action_plan["like"]["intended"] = False
                    action_plan["like"]["reason"] = f"random_skip(p≈{p:.2f})"
                    logger.info(f"  [LIKE] SKIPPED (dynamic randomness p≈{p:.2f})")
                    results['like'] = False
                else:
                    logger.info(f"  [LIKE] Executing...")
                    like_ok = False
                    if dom_threads_accessible and self.use_dom:
                        action_plan["like"]["attempted"] = True
                        action_plan["like"]["path"] = "dom"
                        like_ok = await self.click_element_dom(comment_idx, 'like')
                        if self.action_debug:
                            logger.info(f"  [LIKE] DOM click result={like_ok}")
                        if like_ok:
                            # 2026-02-04: Reduced min from 0.8s→0.4s (API persistence is fast)
                            random_mult = self._get_random_delay_multiplier()
                            if self.human:
                                calculated_delay = self.human.human_delay(0.4, 0.3) * random_mult
                                await asyncio.sleep(max(calculated_delay, 0.4))
                            else:
                                calculated_delay = 0.4 * random_mult
                                await asyncio.sleep(max(calculated_delay, 0.4))
                            like_ok = await self._verify_action_with_vision(
                                "LIKE",
                                self.VISION_DESCRIPTIONS["like_verify"],
                                timeout=30.0,
                            )

                    if not like_ok and self.use_vision:
                        if self.action_debug:
                            logger.info(f"  [LIKE] Vision fallback engaged (ui_tars={bool(self.ui_tars_bridge)})")
                        action_plan["like"]["attempted"] = True
                        if action_plan["like"]["path"] == "dom":
                            action_plan["like"]["path"] = "dom+vision"
                        else:
                            action_plan["like"]["path"] = "vision"
                        like_ok = await self._vision_click_verified(
                            action_name="LIKE",
                            click_description=self.VISION_DESCRIPTIONS["like_click"],
                            verify_description=self.VISION_DESCRIPTIONS["like_verify"],
                            max_retries=3,
                            min_confidence=0.6,
                            require_verification=False,
                        )

                    results['like'] = bool(like_ok)
                    self.stats['likes'] += 1 if results['like'] else 0
                    logger.info(f"  [LIKE] {'OK' if results['like'] else 'FAIL'}")
        else:
            action_plan["like"]["intended"] = False
            action_plan["like"]["reason"] = "disabled"
            logger.info("  [LIKE] DISABLED (do_like=False)")

            # 2026-02-04: Reduced inter-action delay from 1.0s→0.3s
            random_mult = self._get_random_delay_multiplier()
            if self.human:
                await asyncio.sleep(self.human.human_delay(0.3, 0.3) * random_mult)
            else:
                await asyncio.sleep(0.3 * random_mult)

        action_plan["like"]["success"] = bool(results.get("like"))

        # 2. HEART
        if do_heart:
            action_plan["heart"]["intended"] = True

            # UI-TARS gate: snapshot + UI-state derived switch (skip if greyed-out/disabled)
            heart_ui = self._read_action_ui_state(comment_idx, "heart")
            self.heart_ui_switch = (not heart_ui.disabled)
            self._capture_pre_action_snapshot(
                action="heart",
                comment_idx=comment_idx,
                ui_state={
                    "found": heart_ui.found,
                    "disabled": heart_ui.disabled,
                    "pressed": heart_ui.pressed,
                    "aria_pressed": heart_ui.aria_pressed,
                    "aria_disabled": heart_ui.aria_disabled,
                    "opacity": heart_ui.opacity,
                    "pointer_events": heart_ui.pointer_events,
                    "notes": heart_ui.notes,
                },
            )

            if not self.heart_ui_switch:
                action_plan["heart"]["intended"] = False
                action_plan["heart"]["reason"] = "ui_disabled_or_greyed"
                logger.info("  [HEART] UI switch OFF (disabled/greyed) - skipping to avoid detection signature")
                results["heart"] = False
            elif heart_ui.pressed:
                action_plan["heart"]["intended"] = False
                action_plan["heart"]["reason"] = "already_hearted"
                logger.info("  [HEART] Already hearted (pressed) - skipping to avoid removing heart")
                results["heart"] = False
            else:
                do_it, p = self._should_attempt("heart", self.heart_probability)
                if not do_it:
                    action_plan["heart"]["intended"] = False
                    action_plan["heart"]["reason"] = f"random_skip(p≈{p:.2f})"
                    logger.info(f"  [HEART] SKIPPED (dynamic randomness p≈{p:.2f})")
                    results['heart'] = False
                else:
                    logger.info(f"  [HEART] Executing...")
                    heart_ok = False
                    if dom_threads_accessible and self.use_dom:
                        action_plan["heart"]["attempted"] = True
                        action_plan["heart"]["path"] = "dom"
                        heart_ok = await self.click_element_dom(comment_idx, 'heart')
                        if self.action_debug:
                            logger.info(f"  [HEART] DOM click result={heart_ok}")
                        if heart_ok:
                            # 2026-02-04: Reduced from 1.0s→0.4s base (speed optimization)
                            random_mult = self._get_random_delay_multiplier()
                            if self.human:
                                calculated_delay = self.human.human_delay(0.4, 0.3) * random_mult
                                await asyncio.sleep(max(calculated_delay, 0.4))
                            else:
                                calculated_delay = 0.4 * random_mult
                                await asyncio.sleep(max(calculated_delay, 0.4))
                            heart_ok = await self._verify_action_with_vision(
                                "HEART",
                                self.VISION_DESCRIPTIONS["heart_verify"],
                                timeout=30.0,
                            )

                    if not heart_ok and self.use_vision:
                        if self.action_debug:
                            logger.info(f"  [HEART] Vision fallback engaged (ui_tars={bool(self.ui_tars_bridge)})")
                        action_plan["heart"]["attempted"] = True
                        if action_plan["heart"]["path"] == "dom":
                            action_plan["heart"]["path"] = "dom+vision"
                        else:
                            action_plan["heart"]["path"] = "vision"
                        heart_ok = await self._vision_click_verified(
                            action_name="HEART",
                            click_description=self.VISION_DESCRIPTIONS["heart_click"],
                            verify_description=self.VISION_DESCRIPTIONS["heart_verify"],
                            max_retries=3,
                            min_confidence=0.6,
                            require_verification=False,
                        )

                    results['heart'] = bool(heart_ok)
                    self.stats['hearts'] += 1 if results['heart'] else 0
                    logger.info(f"  [HEART] {'OK' if results['heart'] else 'FAIL'}")
        else:
            action_plan["heart"]["intended"] = False
            action_plan["heart"]["reason"] = "disabled"
            logger.info("  [HEART] DISABLED (do_heart=False)")

            # 2026-02-04: Reduced inter-action delay from 1.0s→0.3s
            random_mult = self._get_random_delay_multiplier()
            if self.human:
                await asyncio.sleep(self.human.human_delay(0.3, 0.3) * random_mult)
            else:
                await asyncio.sleep(0.3 * random_mult)

        action_plan["heart"]["success"] = bool(results.get("heart"))

        # 3. REPLY
        if do_reply:
            action_plan["reply"]["intended"] = True
            logger.info(f"  [REPLY-START] Entering reply section (do_reply=True)")
            logger.info(f"  [REPLY-START]   reply_basic_only={self.reply_basic_only}")
            logger.info(f"  [REPLY-START]   use_intelligent_reply={use_intelligent_reply}")

            # Determine reply text (initially basic)
            actual_reply_text = reply_text
            
            # Default state (Tier 1 = Regular)
            tier = 1

            # Layer 3: Commenter Classification (MOVED BEFORE LAYER 2)
            # We need classification first to determine the reply strategy (Tier)
            if not self.no_classification and not self.reply_basic_only and INTELLIGENT_REPLIES_AVAILABLE:
                
                # Start Heartbeat
                hb_stop = asyncio.Event()
                hb_task = asyncio.create_task(self._thinking_heartbeat("Layer 3 (Classification)", hb_stop))

                try:
                    # STRICT TIMEOUT: 3 seconds for classification
                    async def _classify_wrapper():
                        generator = get_reply_generator()
                        return generator.classify_commenter(
                            author_name=comment_data.get('author_name', ''),
                            comment_text=comment_data.get('text', ''),
                            author_channel_id=comment_data.get('channel_id'),
                            is_mod=comment_data.get('is_mod', False),
                            is_subscriber=comment_data.get('is_subscriber', False)
                        )

                    profile = await asyncio.wait_for(_classify_wrapper(), timeout=3.0)
                    hb_stop.set()
                    
                    results['commenter_type'] = profile.commenter_type.value
                    
                    # === SMART ENGAGEMENT STRATEGY (Phase 3) ===
                    # 1. Base Tier Determination
                    # FIX (2025-12-30): Use .value (int 0/1/2) not .to_012_code() (string "0✊"/"1✋"/"2🖐️")
                    # TIER_EMOJI expects int keys: {0: "✊", 1: "✋", 2: "🖐️"}
                    tier = profile.commenter_type.value
                    logger.info(f"  [STRATEGY] Class: {profile.commenter_type.value} -> Base Tier: {tier} ({profile.commenter_type.to_012_code()})")
                    
                    # 2. Tier Escalation (Loyalty Reward)
                    # If Regular (1) and Older than 90 days -> Mod treatment (2)
                    days_ago = self.parse_comment_age_days(comment_data.get('published_time'))
                    if tier == 1 and days_ago >= 90:
                         logger.info(f"  [STRATEGY] Loyalty Escalation! Comment is {days_ago} days old. Promoting Tier 1 -> Tier 2.")
                         tier = 2
                    
                    # 3. Probabilistic Gating (Natural Pace)
                    # Tier 1 (Regular) -> configurable skip probability (YT_012_REPLY_SKIP_PROB)
                    if tier == 1:
                         do_it, p = self._should_attempt("reply", 1.0 - self.reply_skip_probability)
                         # reply_skip_probability is a skip rate; convert to bias for "do reply"
                         if not do_it:
                             logger.info(f"  [STRATEGY] Randomly skipping reply for Tier 1 user (dynamic p≈{p:.2f}).")
                             do_reply = False
                             actual_reply_text = None
                    elif tier in (0, 2):
                         # Non-fixed gating for other tiers too (requested: don't always reply)
                         # Tier 2 (mod/subscriber): high bias, but still occasional skip
                         # Tier 0 (unknown): medium bias
                         base = 0.88 if tier == 2 else 0.65
                         do_it, p = self._should_attempt("reply", base)
                         if not do_it:
                             logger.info(f"  [STRATEGY] Randomly skipping reply (tier={tier}, dynamic p≈{p:.2f}).")
                             do_reply = False
                             actual_reply_text = None
                    
                    # Store Final Tier for Layer 2
                    comment_data['tier'] = tier

                except asyncio.TimeoutError:
                    hb_stop.set()
                    logger.warning(f"  [LAYER-3] Classification TIMEOUT (3s) - Defaulting to 'unknown'")
                    results['commenter_type'] = 'unknown'
                except Exception as e:
                    hb_stop.set()
                    logger.warning(f"  [LAYER-3] Classification ERROR: {e}")
                    results['commenter_type'] = 'unknown'
                finally:
                    if not hb_task.done():
                        hb_stop.set()
                        try:
                            await hb_task
                        except:
                            pass

            # Layer 2: Intelligent Reply Generation (skip if --reply-basic-only OR if strategy disabled do_reply)
            if do_reply and not actual_reply_text and use_intelligent_reply and not self.reply_basic_only:
                logger.info(f"  [LAYER-2] Generating intelligent reply (Tier: {comment_data.get('tier', 'default')})...")
                logger.info("[HARD-THINK] Layer 2: Invoking Intelligent Reply Generator...")
                
                # Start Heartbeat
                hb_stop = asyncio.Event()
                hb_task = asyncio.create_task(self._thinking_heartbeat("Layer 2 (Intelligence)", hb_stop))
                
                try:
                    # Bound the complete local-service + embedded-Qwen route.
                    actual_reply_text = await asyncio.wait_for(
                        asyncio.to_thread(self._generate_intelligent_reply, comment_data),
                        timeout=10.0
                    )
                    hb_stop.set() # Stop heartbeat

                    # Log result length for debugging
                    reply_len = len(actual_reply_text) if actual_reply_text else 0
                    logger.info(f"[HARD-THINK] Layer 2 Result: '{actual_reply_text[:50] if actual_reply_text else ''}...' (len={reply_len})")

                    # Generic templates claim engagement without reading the
                    # comment. Fail closed unless the legacy behavior is opted in.
                    allow_generic = os.getenv(
                        "YT_ALLOW_GENERIC_REPLY_FALLBACK", "false"
                    ).strip().lower() in {"1", "true", "yes", "on"}
                    if actual_reply_text and not allow_generic:
                        generator = get_reply_generator()
                        reply_source = generator.get_last_llm_source().lower()
                        if not self.is_contextual_reply_source(reply_source):
                            logger.warning(
                                "[CONTEXT-GATE] Skipping non-contextual reply from source=%s",
                                reply_source,
                            )
                            actual_reply_text = ""

                except asyncio.TimeoutError:
                    hb_stop.set()
                    logger.warning("[HARD-THINK] ⚠️ Layer 2 TIMEOUT (10s) - AI Generation too slow, check LLM connectivity")
                    actual_reply_text = None 
                except Exception as e:
                    hb_stop.set()
                    logger.error(f"[HARD-THINK] ⚠️ Layer 2 ERROR: {e}")
                    actual_reply_text = None
                finally:
                    # Ensure heartbeat is killed even if something crazy happens
                    if not hb_task.done():
                        hb_stop.set()
                        try:
                            await hb_task
                        except:
                            pass
                
                # FALLBACK MECHANISM (Occam's Safety Net)
                # CRITICAL FIX (2025-12-23): Distinguish between intentional skip vs failure
                # - Empty string "" = Intentional skip (anti-spam, probabilistic) → DON'T apply fallback
                # - None or whitespace = Failure → Apply fallback

                if actual_reply_text == "":
                    # Intentional skip (anti-spam, probabilistic engagement) - preserve empty string
                    logger.info("[HARD-THINK] Reply intentionally skipped (anti-spam/probabilistic) - no fallback applied")
                    # actual_reply_text remains "" - caller will handle this as "skip reply"

                elif not actual_reply_text or not actual_reply_text.strip():
                    # Failure case: fail closed unless legacy templates are opted in.
                    if actual_reply_text is not None:
                        logger.warning(f"[HARD-THINK] ⚠️ AI returned WHITESPACE reply! Triggering fallback.")
                    else:
                        logger.warning(f"[HARD-THINK] ⚠️ AI returned None! Triggering fallback.")

                    allow_generic = os.getenv(
                        "YT_ALLOW_GENERIC_REPLY_FALLBACK", "false"
                    ).strip().lower() in {"1", "true", "yes", "on"}
                    if allow_generic:
                        logger.info("[HARD-THINK] Activating legacy fallback reply")
                        fallback_opts = [
                            "Thanks for watching! 🚀",
                            "Appreciate the comment! 🙏",
                            "Great point! 👍",
                            "FoundUps is the way! 💎",
                            "0102 logic engaged! ✊",
                        ]
                        actual_reply_text = random.choice(fallback_opts)
                        used_intelligent = False
                    else:
                        logger.warning(
                            "[CONTEXT-GATE] No grounded reply available; skipping post"
                        )
                        actual_reply_text = ""
                else:
                    used_intelligent = True

            # EXECUTION: Post the reply
            if do_reply and actual_reply_text and actual_reply_text.strip():
                # Add signature if not present (ANTI-SPAM / IDENTITY)
                # CRITICAL FIX (2025-12-30): Check if reply already has 0102 signature
                # IntelligentReplyGenerator.generate_reply() already applies signature
                # Applying it AGAIN caused duplicate holiday suffixes like "🗓️ 2026 incoming! 🗓️ 2026 incoming!"

                # Check if already signed (contains "0102" signature)
                already_signed = "0102" in actual_reply_text

                if already_signed:
                    # Reply already has signature from IntelligentReplyGenerator
                    reply_text_to_post = actual_reply_text
                    if self.action_debug:
                        logger.info(f"  [REPLY] Already signed (skipping duplicate signature): {actual_reply_text[:50]}...")
                elif INTELLIGENT_REPLIES_AVAILABLE:
                    # Fallback templates need signature (lines 862-869 fallback_opts don't have it)
                    generator = get_reply_generator()
                    tier_to_sign = comment_data.get('tier', 1)  # Default to Tier 1
                    reply_text_to_post = generator._add_0102_signature(actual_reply_text, tier=tier_to_sign)
                    if self.action_debug:
                        logger.info(f"  [REPLY] Signed reply: {reply_text_to_post[:50]}...")
                else:
                    reply_text_to_post = actual_reply_text

                # Optional: Append debug tags (e.g. [AI] [FALLBACK])
                if self.reply_debug_tags:
                    tag = "[AI]" if used_intelligent else "[TMPL]"
                    reply_text_to_post = f"{tag} {reply_text_to_post}"

                logger.info(f"  [REPLY] Executing reply via execute_reply()...")
                reply_ok = await self.reply_executor.execute_reply(comment_idx, reply_text_to_post)

                results['reply'] = bool(reply_ok)
                # Training Mode: Capture reply text for transcript (Task 3)
                if reply_ok:
                    results['reply_text_posted'] = reply_text_to_post
                    results['reply_source'] = 'bot'  # vs '012_manual' for training
                    # LLM SOURCE TRACKING (2026-02-21): Capture which agent generated reply
                    try:
                        generator = get_reply_generator()
                        results['llm_source'] = generator.get_last_llm_source()
                        logger.info(f"  [REPLY] LLM source: {results['llm_source']}")
                    except Exception:
                        results['llm_source'] = 'unknown'
                self.stats['replies'] += 1 if results['reply'] else 0
                logger.info(f"  [REPLY] {'OK' if results['reply'] else 'FAIL'}")
            elif do_reply:
                 logger.info("  [REPLY] SKIPPED - No reply text generated or intended.")
            else:
                 logger.info("  [REPLY] DISABLED (do_reply=False)")

        action_plan["reply"]["success"] = bool(results.get("reply"))

        # ============================================================
        # DAEmon VISIBILITY: Clear interaction summary for 012 monitoring
        # Shows: Comment → Classification (0/1/2) → Reply
        # ============================================================
        tier_emoji = {0: "✊", 1: "✋", 2: "🖐️"}.get(comment_data.get('tier'), "❓")
        tier_num = comment_data.get('tier', '?')
        comment_preview = (comment_data.get('text', '') or '')[:80].replace('\n', ' ')
        reply_preview = (results.get('reply_text_posted', '') or '')[:80].replace('\n', ' ')

        logger.info(f"[DAEMON] ═══════════════════════════════════════════════════════")
        logger.info(f"[DAEMON] 💬 COMMENT: \"{comment_preview}{'...' if len(comment_data.get('text', '')) > 80 else ''}\"")
        logger.info(f"[DAEMON]    Author: @{results.get('author_name', 'Unknown')} | Type: {tier_emoji} ({tier_num})")
        logger.info(f"[DAEMON]    Actions: Like={results.get('like')} | Heart={results.get('heart')} | Reply={results.get('reply')}")
        if results.get('reply') and reply_preview:
            logger.info(f"[DAEMON] 🤖 REPLY: \"{reply_preview}{'...' if len(results.get('reply_text_posted', '')) > 80 else ''}\"")
        logger.info(f"[DAEMON] ═══════════════════════════════════════════════════════")

        # Final Log of the action plan state
        if self.action_debug:
            logger.info(f"[DAE-ENGAGE] Results for {results['author_name']}: L={results['like']} H={results['heart']} R={results['reply']} Type={results['commenter_type']}")
            
        return results

    def get_comment_count(self) -> int:
        """Get number of comment threads visible in DOM."""
        try:
            result = self.driver.execute_script("""
                const selector = 'ytcp-comment-thread';
                const directCount = document.querySelectorAll(selector).length;
                if (directCount) {
                    return {count: directCount, fallback: false};
                }
                const results = [];
                const stack = [document];
                while (stack.length) {
                    const node = stack.pop();
                    if (!node || !node.querySelectorAll) continue;
                    try {
                        const found = node.querySelectorAll(selector);
                        for (const el of found) results.push(el);
                    } catch (e) {}
                    const children = node.querySelectorAll('*');
                    for (const child of children) {
                        if (child.shadowRoot) stack.push(child.shadowRoot);
                    }
                }
                return {count: results.length, fallback: true};
            """)
            if isinstance(result, dict):
                count = int(result.get("count", 0))
                if result.get("fallback") and count > 0 and not getattr(self, "_shadow_threads_logged", False):
                    logger.info(f"[DAE-ENGAGE] Shadow DOM threads detected: {count}")
                    self._shadow_threads_logged = True
                return count
            return int(result or 0)
        except Exception:
            return 0

    async def _thinking_heartbeat(self, layer_name: str, stop_event: asyncio.Event):
        """Log periodic 'thinking' dots while AI is working to show activity."""
        start_time = time.time()
        while not stop_event.is_set():
            await asyncio.sleep(2.0)
            if stop_event.is_set():
                break
            elapsed = time.time() - start_time
            logger.info(f"  [HARD-THINK] {layer_name} still processing... ({elapsed:.1f}s)")

    def _generate_intelligent_reply(self, comment_data: Dict[str, Any]) -> str:
        """
        Synchronous wrapper for generating intelligent reply.
        Used within to_thread to prevent blocking the event loop.
        """
        if not INTELLIGENT_REPLIES_AVAILABLE:
            return None

        generator = get_reply_generator()
        return generator.generate_reply(
            author_name=comment_data.get('author_name', ''),
            comment_text=comment_data.get('text', ''),
            author_channel_id=comment_data.get('channel_id'),
            is_mod=comment_data.get('is_mod', False),
            is_subscriber=comment_data.get('is_subscriber', False),
            published_time=comment_data.get('published_time'),
            video_title=comment_data.get('video_title') or self.video_title,
            target_channel_id=self.target_channel_id,
        )

    def _get_context_flags(self, comment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract additional context flags for strategy."""
        text = comment_data.get('text', '').lower()
        return {
            'is_question': '?' in text or any(w in text for w in ['how', 'why', 'what', 'when', 'where']),
            'is_positive': any(w in text for w in ['great', 'awesome', 'love', 'thanks', 'good', 'best']),
            'is_negative': any(w in text for w in ['bad', 'hate', 'worst', 'stop', 'why']),
            'has_video_context': bool(comment_data.get('video_title') or self.video_title),
        }

    async def _verify_action_with_vision(self, action_name: str, verify_description: str, timeout: float = 30.0) -> bool:
        """Verify action using UI-TARS vision if available."""
        if not self.use_vision or not self.ui_tars_bridge:
            return True
            
        logger.info(f"  [VISION-VERIFY] Verifying {action_name}...")
        try:
            result = await self.ui_tars_bridge.verify(
                description=verify_description,
                timeout=timeout,
                driver=self.driver
            )
            if result.success:
                logger.info(f"  [VISION-VERIFY] ✅ {action_name} verified (confidence: {result.confidence:.2f})")
                return True
            else:
                logger.warning(f"  [VISION-VERIFY] ❌ {action_name} verification failed: {result.error}")
                return False
        except Exception as e:
            logger.error(f"  [VISION-VERIFY] ❌ Vision verify error: {e}")
            return False

    async def _vision_exists(self, description: str, timeout: float = 15.0, min_confidence: float = 0.5) -> bool:
        """
        Check if an element exists using UI-TARS vision.
        Internal helper for _verify_action_with_vision.
        """
        if not self.use_vision or not self.ui_tars_bridge:
            return False

        try:
            logger.info(f"  [VISION-SCAN] Looking for: {description}...")
            result = await self.ui_tars_bridge.verify(
                description=description,
                timeout=timeout,
                driver=self.driver
            )
            return result.success and result.confidence >= min_confidence
        except Exception as e:
            logger.debug(f"[VISION] Existence check failed: {e}")
            return False

    async def _vision_click_verified(self, action_name: str, click_description: str, verify_description: str = None, max_retries: int = 2, min_confidence: float = 0.5, require_verification: bool = False) -> bool:
        """Execute click and verify using UI-TARS vision."""
        if not self.use_vision or not self.ui_tars_bridge:
            return False
            
        logger.info(f"  [VISION-ACTION] Executing vision-click for {action_name}...")
        
        for attempt in range(1, max_retries + 1):
            try:
                # Execute vision-based click
                result = await self.ui_tars_bridge.click(
                    description=click_description,
                    driver=self.driver,
                    timeout=90 # UI-TARS needs time for inference
                )
                
                if not result.success:
                    logger.warning(f"  [VISION-ACTION] ⚠️ Attempt {attempt} failed: {result.error}")
                    continue
                
                logger.info(f"  [VISION-ACTION] ✅ {action_name} click executed (confidence: {result.confidence:.2f})")
                
                if not verify_description or not require_verification:
                    return True
                
                # Perform verification if requested
                verified = await self._vision_exists(verify_description, timeout=10.0, min_confidence=min_confidence)
                if verified:
                    logger.info(f"  [VISION-ACTION] ✅ {action_name} verified after click")
                    return True
                else:
                    logger.warning(f"  [VISION-ACTION] ⚠️ {action_name} verification failed after click")
            
            except Exception as e:
                logger.error(f"  [VISION-ACTION] ❌ Vision error on attempt {attempt}: {e}")
                
        return False
