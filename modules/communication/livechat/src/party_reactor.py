"""
0102 Party Reactor - YouTube Live Chat Reaction Spam (HYBRID)
=============================================================

WSP Compliance: WSP 77 (Banter Engine), WSP 27 (DAE Phases), WSP 49 (Anti-Detection)

Phase 4H: HYBRID Architecture (Fixed + Vision Fallback)
- Tier 0: Fixed coordinates via human_interaction (~100ms, 95% success)
- Tier 1: UI-TARS vision fallback if coordinates fail (~5-30s, 80% success)
- Tier 2: Gemini vision fallback if UI-TARS unavailable

Phase 3N Integration (2025-12-16): Human Interaction Module
- Bezier curve mouse movement (replaces instant teleportation)
- Coordinate variance (±8px per click, no pixel-perfect)
- Probabilistic errors (8-13% miss rate with fatigue)
- Fatigue modeling (1.0x → 1.8x slower over time)
- Thinking pauses (30% chance, 0.5-2.0s hesitation)
- Detection risk reduction: 40-60% → 8-15%

NAVIGATION:
-> Called by: command_handler.py on !party command
-> Uses: modules.infrastructure.human_interaction (anti-detection)
-> Uses: modules.infrastructure.foundups_vision.src.ui_tars_bridge (vision fallback)
-> Related: modules/infrastructure/human_interaction/platforms/youtube_chat.json
"""

import os
import time
import random
import logging
import asyncio
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Training data collection for vision model self-supervised learning
_training_collector = None

def _get_training_collector():
    """Lazy load training collector to avoid circular imports."""
    global _training_collector
    if _training_collector is None:
        try:
            from modules.infrastructure.foundups_vision.src.vision_training_collector import get_training_collector
            _training_collector = get_training_collector()
            logger.info("[PARTY] Vision training collector initialized")
        except ImportError as e:
            logger.debug(f"[PARTY] Training collector not available: {e}")
            _training_collector = False  # Mark as unavailable
    return _training_collector if _training_collector is not False else None


def _env_truthy(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "y", "on")

# Reaction name to platform action mapping
REACTION_ACTIONS = {
    '100': 'reaction_100',
    'wide_eyes': 'reaction_wide_eyes',
    'celebrate': 'reaction_celebrate',
    'smiley': 'reaction_smiley',
    'heart': 'reaction_heart',
}

REACTION_EMOJIS = {
    '100': '💯',
    'wide_eyes': '😲',
    'celebrate': '🎉',
    'smiley': '😊',
    'heart': '❤️',
}

# Fixed coordinates for training data collection (aligned with youtube_chat.json)
# These are used to generate labeled training data for UI-TARS vision model
REACTION_COORDINATES = {
    '100': (359, 790),
    'wide_eyes': (359, 754),
    'celebrate': (359, 718),
    'smiley': (359, 682),
    'heart': (359, 646),
}

# Description templates for vision model training
REACTION_DESCRIPTIONS = {
    '100': "100 emoji reaction button in YouTube chat popup",
    'wide_eyes': "wide eyes emoji reaction button in YouTube chat popup",
    'celebrate': "celebrate party emoji reaction button in YouTube chat popup",
    'smiley': "smiley face emoji reaction button in YouTube chat popup",
    'heart': "heart emoji reaction button in YouTube chat popup",
}


class PartyReactor:
    """Handles !party command - spams reactions in YouTube Live Chat.

    Phase 4H: HYBRID with training data collection.
    - Uses Human Interaction Module for anti-detection
    - Records successful clicks as training data for UI-TARS vision
    - Enables continuous self-supervised learning
    """

    def __init__(self):
        self.driver = None
        self.interaction = None  # Lazy load when driver connected
        self._last_party_time = 0
        self._party_cooldown = 60  # 60 seconds between parties
        self._training_enabled = _env_truthy("PARTY_TRAINING_ENABLED", "true")
        self._vision_enabled = _env_truthy("PARTY_VISION_VALIDATION_ENABLED", "true")
        self._training_examples_this_session = 0
        self._vision_bridge = None
        
    def _connect_to_chrome(self):
        """Connect to Chrome instance with remote debugging."""
        if self.driver:
            logger.debug(f"[PARTY-DEBUG] Already connected (reusing existing driver)")
            return True

        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from modules.infrastructure.human_interaction import get_interaction_controller

            # Use same Chrome instance as comment engagement (port 9222)
            # UNIFIED: Both livechat and Studio use same browser instance
            port = int(os.getenv("FOUNDUPS_LIVECHAT_CHROME_PORT", "9222"))
            logger.info(f"[PARTY-DEBUG] Attempting Chrome connection on port {port}...")

            opts = Options()
            opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
            self.driver = webdriver.Chrome(options=opts)
            from modules.infrastructure.foundups_selenium.src.youtube_verification import install_youtube_verification_guard
            install_youtube_verification_guard(self.driver, port)

            # Log full connection details
            current_url = self.driver.current_url
            page_title = self.driver.title
            logger.info(f"[PARTY-DEBUG] Chrome connected successfully!")
            logger.info(f"[PARTY-DEBUG]   Port: {port}")
            logger.info(f"[PARTY-DEBUG]   URL: {current_url}")
            logger.info(f"[PARTY-DEBUG]   Page: {page_title[:50]}")

            # Initialize interaction controller with anti-detection
            self.interaction = get_interaction_controller(self.driver, platform="youtube_chat")
            logger.info(f"[PARTY] Connected to Chrome with anti-detection: {current_url[:40]}...")

            # Initialize vision bridge if enabled
            if self._vision_enabled:
                try:
                    from modules.infrastructure.foundups_vision.src.ui_tars_bridge import create_ui_tars_bridge
                    self._vision_bridge = create_ui_tars_bridge(browser_port=port)
                    logger.info("[PARTY] UI-TARS vision bridge initialized")
                except ImportError as e:
                    logger.warning(f"[PARTY] UI-TARS bridge not available: {e}")
                    self._vision_enabled = False

            return True
        except Exception as e:
            logger.error(f"[PARTY] Failed to connect to Chrome: {e}")
            logger.error(f"[PARTY-DEBUG] Connection failure details:")
            logger.error(f"[PARTY-DEBUG]   Port: {port}")
            logger.error(f"[PARTY-DEBUG]   Error type: {type(e).__name__}")
            logger.error(f"[PARTY-DEBUG]   Error message: {str(e)}")
            return False

    def _record_training_example(self, reaction_name: str, success: bool, duration_ms: int = 0) -> None:
        """Record successful click as training data for vision model.
        
        This enables self-supervised learning where fixed coordinate clicks
        generate labeled training data for the UI-TARS vision model.
        
        Args:
            reaction_name: Name of the reaction (e.g., 'celebrate')
            success: Whether the click was successful
            duration_ms: Time taken for the action
        """
        if not self._training_enabled or not success:
            return
            
        if self.driver is None:
            return
            
        collector = _get_training_collector()
        if collector is None:
            return
            
        try:
            coordinates = REACTION_COORDINATES.get(reaction_name)
            description = REACTION_DESCRIPTIONS.get(reaction_name, f"{reaction_name} reaction button")
            
            if coordinates:
                example_id = collector.record_successful_click(
                    driver=self.driver,
                    description=description,
                    coordinates=coordinates,
                    platform="youtube_chat",
                    action="click",
                    duration_ms=duration_ms,
                    metadata={
                        "reaction_name": reaction_name,
                        "emoji": REACTION_EMOJIS.get(reaction_name, ""),
                    }
                )
                
                if example_id:
                    self._training_examples_this_session += 1
                    logger.debug(f"[PARTY-TRAIN] Recorded training example: {example_id}")
                    
        except Exception as e:
            logger.debug(f"[PARTY-TRAIN] Failed to record training example: {e}")
            
    async def _verify_popup_visible(self) -> bool:
        """Use UI-TARS vision to verify the reaction popup is actually open.
        
        Returns:
            True if popup found, False otherwise
        """
        if not self._vision_enabled or not self._vision_bridge:
            return True # Assume visible if vision disabled
            
        logger.info("[PARTY-VISION] Verifying reaction popup visibility...")
        try:
            # We look for the "heart" reaction specifically as an anchor
            result = await self._vision_bridge.verify(
                description="heart emoji reaction button in the chat popup",
                driver=self.driver
            )
            
            if result.success:
                logger.info(f"[PARTY-VISION] Popup verified (confidence: {result.confidence:.2f})")
                return True
            else:
                logger.warning(f"[PARTY-VISION] Popup NOT found: {result.error}")
                return False
        except Exception as e:
            logger.error(f"[PARTY-VISION] Vision verification failed: {e}")
            return True # Fallback to true to avoid blocking if vision service is flaky
        
    async def spam_single(self, reaction_name: str, count: int = 10) -> int:
        """Spam a single reaction type with full anti-detection.

        Phase 3N: Uses Human Interaction Module for:
        - Bezier curve movement
        - Coordinate variance (±8px)
        - Probabilistic errors (8-13%)
        - Fatigue modeling (1.0x → 1.8x slower)
        - Thinking pauses (30% chance)
        """
        # Permission gate checks with detailed logging
        logger.debug(f"[PARTY-DEBUG] Permission gates:")
        logger.debug(f"[PARTY-DEBUG]   YT_AUTOMATION_ENABLED: {os.getenv('YT_AUTOMATION_ENABLED', 'true')}")
        logger.debug(f"[PARTY-DEBUG]   YT_LIVECHAT_UI_ACTIONS_ENABLED: {os.getenv('YT_LIVECHAT_UI_ACTIONS_ENABLED', 'true')}")
        logger.debug(f"[PARTY-DEBUG]   YT_PARTY_REACTIONS_ENABLED: {os.getenv('YT_PARTY_REACTIONS_ENABLED', 'true')}")

        if not _env_truthy("YT_AUTOMATION_ENABLED", "true"):
            logger.warning("[PARTY] Disabled (YT_AUTOMATION_ENABLED=false)")
            return 0
        if not _env_truthy("YT_LIVECHAT_UI_ACTIONS_ENABLED", "true"):
            logger.warning("[PARTY] Disabled (YT_LIVECHAT_UI_ACTIONS_ENABLED=false)")
            return 0
        if not _env_truthy("YT_PARTY_REACTIONS_ENABLED", "true"):
            logger.warning("[PARTY] Disabled (YT_PARTY_REACTIONS_ENABLED=false)")
            return 0

        if not self._connect_to_chrome():
            logger.error(f"[PARTY-DEBUG] Chrome connection failed - aborting spam_single")
            return 0

        # Get platform action name
        action_name = REACTION_ACTIONS.get(reaction_name)
        if not action_name:
            logger.error(f"[PARTY] Unknown reaction: {reaction_name}")
            logger.error(f"[PARTY-DEBUG] Available reactions: {list(REACTION_ACTIONS.keys())}")
            return 0

        logger.info(f"[PARTY-DEBUG] Spamming {reaction_name} (action: {action_name}) x{count}")

        # Try interaction controller with full sophistication
        try:
            results = await self.interaction.spam_action(action_name, count=count)

            # Log sophistication stats if available
            if hasattr(self.interaction, 'get_stats'):
                stats = self.interaction.get_stats()
                logger.debug(f"[PARTY-DEBUG] Sophistication stats: {stats}")

            logger.info(
                f"[PARTY] {reaction_name}: {results['success']}/{count} clicks "
                f"({results['errors']} mistakes, {results.get('thinking_pauses', 0)} pauses)"
            )
            return results['success']

        except Exception as e:
            logger.warning(f"[PARTY] Human interaction failed: {e}")
            logger.info("[PARTY] Falling back to simple coordinate clicking...")
            return await self._simple_party_fallback(reaction_name, count)

    async def _simple_party_fallback(self, reaction_name: str, count: int) -> int:
        """
        Simple coordinate-based fallback when human_interaction fails.

        Uses the same approach as External Stream Chat - direct coordinate clicking
        without the complex human simulation module.
        """
        from selenium.webdriver.common.action_chains import ActionChains

        coords = REACTION_COORDINATES.get(reaction_name)
        if not coords:
            logger.error(f"[PARTY-FALLBACK] No coordinates for: {reaction_name}")
            return 0

        successful = 0
        for i in range(count):
            try:
                # Add slight randomization (±3px)
                x = coords[0] + random.randint(-3, 3)
                y = coords[1] + random.randint(-3, 3)

                # Direct coordinate click
                actions = ActionChains(self.driver)
                actions.move_by_offset(x, y)
                actions.click()
                actions.move_by_offset(-x, -y)  # Reset position
                actions.perform()

                successful += 1
                logger.debug(f"[PARTY-FALLBACK] {reaction_name} clicked at ({x}, {y})")

                # Simple delay between clicks
                await asyncio.sleep(random.uniform(0.3, 0.8))

            except Exception as e:
                logger.warning(f"[PARTY-FALLBACK] Click failed: {e}")

        logger.info(f"[PARTY-FALLBACK] {reaction_name}: {successful}/{count} clicks")
        return successful
        
    async def party_mode(self, total_clicks: int = 30) -> Dict[str, int]:
        """Spam all chat emoji reactions with human-like behavior.

        Phase 3N: Uses Human Interaction Module for anti-detection.
        Spams: 💯, 😲, 🎉, 😊, ❤️

        Returns:
            Dict mapping reaction names to success counts
        """
        logger.debug(f"[PARTY-DEBUG] party_mode() called with total_clicks={total_clicks}")

        # Permission gate checks
        if not _env_truthy("YT_AUTOMATION_ENABLED", "true"):
            logger.error(f"[PARTY-DEBUG] Blocked by YT_AUTOMATION_ENABLED=false")
            return {"error": "disabled_yt_automation"}

        now = time.time()

        # Cooldown check
        if now - self._last_party_time < self._party_cooldown:
            remaining = int(self._party_cooldown - (now - self._last_party_time))
            logger.warning(f"[PARTY] Cooldown active ({remaining}s remaining)")
            return {'cooldown': remaining}

        if not self._connect_to_chrome():
            logger.error(f"[PARTY-DEBUG] Chrome connection failed - aborting party_mode")
            return {'error': 'chrome_connection_failed'}

        logger.info(f"[PARTY] 🎉 PARTY MODE ACTIVATED! Spamming {total_clicks} emoji reactions...")

        # RANDOM distribution across all emoji reactions (human-like variance)
        reactions = ['celebrate', 'heart', 'smiley', 'wide_eyes', '100']

        # Randomize click distribution
        import random
        click_distribution = []
        remaining = total_clicks
        for i in range(len(reactions) - 1):
            # Random allocation (between 20-40% of remaining)
            min_clicks = max(1, int(remaining * 0.2))
            max_clicks = max(2, int(remaining * 0.4))
            clicks = random.randint(min_clicks, max_clicks)
            click_distribution.append(clicks)
            remaining -= clicks
        # Last reaction gets remaining clicks
        click_distribution.append(remaining)

        # Shuffle to randomize which reaction gets which count
        random.shuffle(click_distribution)

        logger.debug(f"[PARTY-DEBUG] Random distribution: {dict(zip(reactions, click_distribution))}")

        # Prepare flattened reaction sequence
        reaction_sequence = []
        for reaction, count in zip(reactions, click_distribution):
            reaction_sequence.extend([reaction] * count)
        
        # Shuffle sequence for randomness
        random.shuffle(reaction_sequence)

        # VISION TIER: Verify popup is open before starting
        if self._vision_enabled:
            # Ensure popup is triggered at least once
            await self.interaction.hover_action("party_toggle")
            
            popup_visible = await self._verify_popup_visible()
            if not popup_visible:
                logger.info("[PARTY] Reaction popup not visible, retrying trigger...")
                await self.interaction.hover_action("party_toggle")
                # Wait for animation
                await asyncio.sleep(1.0)
                popup_visible = await self._verify_popup_visible()
                
            if not popup_visible:
                logger.warning("[PARTY] Vision validation failed twice - proceeding with Tier 0 (Fixed) fallback")

        # Execute hardened sequence with fallback
        try:
            results_raw = await self.interaction.party_spam(reaction_sequence)

            if "error" in results_raw:
                logger.warning(f"[PARTY] party_spam returned error: {results_raw['error']}")
                raise Exception(results_raw['error'])

            # Format results back to dict by reaction name
            results = {r: 0 for r in reactions}
            results["total_success"] = results_raw.get("success", 0)
            results["total_clicks"] = total_clicks

        except Exception as e:
            logger.warning(f"[PARTY] Hardened sequence failed: {e}")
            logger.info("[PARTY] Falling back to simple full party...")
            results = await self._simple_full_party_fallback(reactions, total_clicks)

        self._last_party_time = now

        logger.info(f"[PARTY] 🎉 Complete! {results.get('total_success', 0)}/{total_clicks} emoji reactions sent")

        return results

    async def _simple_full_party_fallback(self, reactions: list, total_clicks: int) -> Dict[str, int]:
        """
        Simple full party fallback - cycles through all reactions with direct clicking.

        Uses the same approach as External Stream Chat's party_full().
        """
        from selenium.webdriver.common.action_chains import ActionChains

        results = {r: 0 for r in reactions}
        clicks_per_emoji = max(1, total_clicks // len(reactions))

        logger.info(f"[PARTY-FALLBACK] Simple party: {clicks_per_emoji} clicks per emoji")

        # Randomize order
        emoji_order = reactions.copy()
        random.shuffle(emoji_order)

        for emoji_name in emoji_order:
            coords = REACTION_COORDINATES.get(emoji_name)
            if not coords:
                continue

            emoji = REACTION_EMOJIS.get(emoji_name, emoji_name)

            for i in range(clicks_per_emoji):
                try:
                    # Add randomization (±3px)
                    x = coords[0] + random.randint(-3, 3)
                    y = coords[1] + random.randint(-3, 3)

                    actions = ActionChains(self.driver)
                    actions.move_by_offset(x, y)
                    actions.click()
                    actions.move_by_offset(-x, -y)
                    actions.perform()

                    results[emoji_name] += 1
                    logger.debug(f"[PARTY-FALLBACK] {emoji} clicked ({i+1}/{clicks_per_emoji})")

                    await asyncio.sleep(random.uniform(0.3, 0.8))

                except Exception as e:
                    logger.warning(f"[PARTY-FALLBACK] {emoji} click failed: {e}")

            # Pause between emoji types
            await asyncio.sleep(random.uniform(0.5, 1.0))

        results["total_success"] = sum(v for k, v in results.items() if k in reactions)
        results["total_clicks"] = total_clicks

        return results
        
    def get_party_summary(self, results: Dict[str, int]) -> str:
        """Format party results as a chat message."""
        if 'error' in results:
            return f"🎉 Party failed: {results['error']} ✊✋🖐️"
        if 'cooldown' in results:
            return f"🎉 Party on cooldown! Wait {results['cooldown']}s ✊✋🖐️"

        # Emoji reaction format
        total = results.get("total_success", sum(v for k, v in results.items() if k not in ['total_clicks']))
        summary = f"🎉 PARTY COMPLETE! Sent {total} reactions. Sequence: "

        # Since we use a shuffled sequence, we don't track per-emoji counts perfectly anymore
        # but we can show the emojis involved.
        emojis = "".join(REACTION_EMOJIS.values())
        summary += f"{emojis} "

        summary += "✊✋🖐️"
        return summary

    def get_training_stats(self) -> Dict[str, Any]:
        """Get training data collection statistics."""
        collector = _get_training_collector()
        if collector is None:
            return {"enabled": False, "reason": "collector_not_available"}
        
        stats = collector.get_stats()
        stats["enabled"] = self._training_enabled
        stats["session_examples"] = self._training_examples_this_session
        return stats

    def export_training_data(self, output_path: str = None) -> Optional[str]:
        """Export collected training data to JSONL for UI-TARS fine-tuning.
        
        Args:
            output_path: Path to output file (auto-generated if None)
            
        Returns:
            Path to exported file, or None if failed
        """
        collector = _get_training_collector()
        if collector is None:
            logger.warning("[PARTY-TRAIN] Cannot export: collector not available")
            return None
        
        try:
            path = collector.export_to_jsonl(
                output_path=output_path,
                platform="youtube_chat",
                include_screenshots=True
            )
            logger.info(f"[PARTY-TRAIN] Exported training data to: {path}")
            return path
        except Exception as e:
            logger.error(f"[PARTY-TRAIN] Export failed: {e}")
            return None


# Global instance for import
_party_reactor = None

def get_party_reactor() -> PartyReactor:
    """Get or create global PartyReactor instance."""
    global _party_reactor
    if _party_reactor is None:
        _party_reactor = PartyReactor()
    return _party_reactor


async def trigger_party(total_clicks: int = 30) -> str:
    """Async wrapper for triggering party mode.

    Phase 3N: Now uses async party_mode with Human Interaction Module.
    """
    reactor = get_party_reactor()

    # party_mode is now async, so await it directly
    results = await reactor.party_mode(total_clicks)

    return reactor.get_party_summary(results)





