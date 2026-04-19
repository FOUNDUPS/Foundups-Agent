"""
Browser Reply Executor - Extracted from comment_engagement_dae.py

WSP 62 Refactoring: Reduces comment_engagement_dae.py from 2064 to ~1400 lines
Extracted reply execution logic (~600 lines total).

Pattern: Dependency injection (driver, human, selectors passed to constructor)
"""

import asyncio
import logging
import os
import random
from typing import Any, Dict, List

# YTR1: Import for stale element recovery
from selenium.common.exceptions import StaleElementReferenceException

logger = logging.getLogger(__name__)

# ADR-012: Import owned channels list for cross-comment loop prevention
from modules.communication.video_comments.skillz.tars_like_heart_reply.src.comment_processor import OWNED_CHANNELS

# Anti-detection: Human behavior simulation availability
try:
    from modules.infrastructure.foundups_selenium.src.human_behavior import get_human_behavior
    HUMAN_BEHAVIOR_AVAILABLE = True
except ImportError:
    HUMAN_BEHAVIOR_AVAILABLE = False


class BrowserReplyExecutor:
    """
    Handles all reply execution for YouTube Studio comments.
    
    Responsibilities:
    - Execute replies to top-level comments
    - Execute replies to nested comments  
    - Process all nested replies in a thread
    - Anti-detection: Human-like typing with typos
    """
    
    def __init__(self, driver, human, selectors, delay_multiplier=1.0):
        """
        Args:
            driver: Selenium WebDriver instance
            human: HumanBehavior instance (or None)
            selectors: Dict of DOM selectors
            delay_multiplier: Tempo multiplier (0.1=FAST, 0.25=MEDIUM, 1.0=012)
        """
        self.driver = driver
        self.human = human
        self.selectors = selectors
        self.delay_multiplier = delay_multiplier
        logger.info(f"[DAEMON][REPLY-EXECUTOR] Initialized with tempo multiplier: {delay_multiplier}x")

    async def process_nested_replies(
        self,
        parent_thread_idx: int,
        do_like: bool,
        do_heart: bool,
        use_intelligent_reply: bool
    ) -> List[Dict[str, Any]]:
        """
        Process nested replies within a comment thread.

        Addresses user's challenges:
        1. Skips if Move2Japan already replied (DOM detection)
        2. Uses relative selectors (no absolute positions)
        3. No expansion needed (Studio shows all replies)

        Args:
            parent_thread_idx: Index of parent thread (1-based)
            do_like: Whether to like replies
            do_heart: Whether to heart replies
            use_intelligent_reply: Whether to generate intelligent replies

        Returns:
            List of engagement results for each reply
        """
        # Check if nested reply engagement is enabled
        engage_nested = os.getenv("YT_ENGAGE_NESTED_REPLIES", "false").lower() in ("1", "true", "yes")
        if not engage_nested:
            return []

        max_nested = int(os.getenv("YT_MAX_NESTED_REPLIES", "5"))
        logger.info(f"[NESTED] Checking thread {parent_thread_idx} for nested replies (max: {max_nested})")

        results = []

        try:
            # Query nested replies using relative selectors (position-independent)
            nested_data = self.driver.execute_script("""
                const threadIdx = arguments[0];
                const threads = document.querySelectorAll('ytcp-comment-thread');
                const thread = threads[threadIdx];
                if (!thread) return {has_replies: false, error: 'Thread not found'};

                // Check for nested reply container
                const repliesContainer = thread.querySelector('ytcp-comment-replies');
                if (!repliesContainer) return {has_replies: false};

                // ADR-012: Check if ANY owned channel already replied (skip if so)
                // Prevents cross-comment loops between our channels
                const ownedChannels = ['Move2Japan', 'UnDaoDu', 'FoundUps', 'Foundups'];
                let channelBadge = null;
                for (const channel of ownedChannels) {
                    const badge = repliesContainer.querySelector(
                        `ytcp-comment-author[aria-label*="${channel}"]`
                    );
                    if (badge) {
                        channelBadge = badge;
                        break;
                    }
                }
                // Also check for creator badge (channel owner)
                if (!channelBadge) {
                    channelBadge = repliesContainer.querySelector(
                        '[class*="creator-badge"], [aria-label*="owner"]'
                    );
                }
                if (channelBadge) {
                    return {
                        has_replies: true,
                        channel_already_replied: true,
                        author: channelBadge.textContent.trim()
                    };
                }

                // Get all nested reply elements (relative to thread, not absolute positions!)
                const replyElements = repliesContainer.querySelectorAll(
                    'ytcp-comment-replies[class*="expanded"]'
                );

                // Extract reply data
                const replies = [];
                replyElements.forEach((replyEl, idx) => {
                    const authorEl = replyEl.querySelector('ytcp-comment-author');
                    const contentEl = replyEl.querySelector('[id*="content-text"]');

                    replies.push({
                        index: idx,
                        author: authorEl ? authorEl.textContent.trim() : 'Unknown',
                        text: contentEl ? contentEl.textContent.trim() : '',
                        has_like_btn: !!replyEl.querySelector('ytcp-icon-button[aria-label*="Like"]'),
                        has_heart_btn: !!replyEl.querySelector('ytcp-comment-creator-heart'),
                        has_reply_btn: !!replyEl.querySelector('[id*="reply-button"]')
                    });
                });

                return {
                    has_replies: replies.length > 0,
                    channel_already_replied: false,
                    reply_count: replies.length,
                    replies: replies
                };
            """, parent_thread_idx - 1)

            if not nested_data or not nested_data.get('has_replies'):
                logger.info(f"[NESTED] No nested replies in thread {parent_thread_idx}")
                return []

            if nested_data.get('channel_already_replied'):
                logger.info(f"[NESTED] Skipping thread {parent_thread_idx} - Owned channel already replied (ADR-012)")
                logger.info(f"[NESTED]   Author detected: {nested_data.get('author', 'Unknown')}")
                return []

            reply_count = nested_data.get('reply_count', 0)
            replies = nested_data.get('replies', [])

            logger.info(f"[NESTED] Found {reply_count} nested replies (will process up to {max_nested})")

            # Process each nested reply (limit to max_nested)
            for reply_data in replies[:max_nested]:
                reply_idx = reply_data['index']
                author = reply_data['author']
                text_preview = reply_data['text'][:50] + '...' if len(reply_data['text']) > 50 else reply_data['text']

                logger.info(f"[NESTED] Processing reply {reply_idx + 1}/{min(reply_count, max_nested)}")
                logger.info(f"[NESTED]   Author: {author}")
                logger.info(f"[NESTED]   Preview: {text_preview}")

                reply_result = {
                    'author_name': author,
                    'text': reply_data['text'],
                    'like': False,
                    'heart': False,
                    'reply': False,
                    'nested': True  # Mark as nested reply
                }

                # Like nested reply (relative selector within thread!)
                if do_like and reply_data['has_like_btn']:
                    like_success = self.driver.execute_script("""
                        const threadIdx = arguments[0];
                        const replyIdx = arguments[1];
                        const threads = document.querySelectorAll('ytcp-comment-thread');
                        const thread = threads[threadIdx];
                        if (!thread) return false;

                        const repliesContainer = thread.querySelector('ytcp-comment-replies');
                        if (!repliesContainer) return false;

                        const replyElements = repliesContainer.querySelectorAll(
                            'ytcp-comment-replies[class*="expanded"]'
                        );
                        const reply = replyElements[replyIdx];
                        if (!reply) return false;

                        const likeBtn = reply.querySelector('ytcp-icon-button[aria-label*="Like"]');
                        if (!likeBtn) return false;

                        likeBtn.click();
                        return true;
                    """, parent_thread_idx - 1, reply_idx)

                    reply_result['like'] = bool(like_success)
                    if like_success:
                        logger.info(f"[NESTED] ✅ Liked reply from {author}")
                        delay = (self.human.human_delay(0.8, 0.3) if self.human else 0.8) * self.delay_multiplier
                        await asyncio.sleep(delay)

                # Heart nested reply (same relative selector pattern)
                if do_heart and reply_data['has_heart_btn']:
                    heart_success = self.driver.execute_script("""
                        const threadIdx = arguments[0];
                        const replyIdx = arguments[1];
                        const threads = document.querySelectorAll('ytcp-comment-thread');
                        const thread = threads[threadIdx];
                        if (!thread) return false;

                        const repliesContainer = thread.querySelector('ytcp-comment-replies');
                        if (!repliesContainer) return false;

                        const replyElements = repliesContainer.querySelectorAll(
                            'ytcp-comment-replies[class*="expanded"]'
                        );
                        const reply = replyElements[replyIdx];
                        if (!reply) return false;

                        const heartBtn = reply.querySelector('ytcp-comment-creator-heart');
                        if (!heartBtn) return false;

                        heartBtn.click();
                        return true;
                    """, parent_thread_idx - 1, reply_idx)

                    reply_result['heart'] = bool(heart_success)
                    if heart_success:
                        logger.info(f"[NESTED] ❤️ Hearted reply from {author}")
                        delay = (self.human.human_delay(0.8, 0.3) if self.human else 0.8) * self.delay_multiplier
                        await asyncio.sleep(delay)

                # Reply to nested reply (if intelligent replies enabled)
                if use_intelligent_reply and reply_data['has_reply_btn']:
                    # Generate intelligent reply for nested conversation
                    try:
                        from .intelligent_reply_generator import generate_intelligent_reply
                        intelligent_reply = await generate_intelligent_reply(
                            comment_text=reply_data['text'],
                            author_name=author,
                            context={'is_nested_reply': True, 'parent_thread': parent_thread_idx}
                        )

                        if intelligent_reply:
                            # Open reply box and type (uses same logic as parent comments)
                            reply_posted = await self._execute_nested_reply(
                                parent_thread_idx,
                                reply_idx,
                                intelligent_reply
                            )
                            reply_result['reply'] = reply_posted
                            reply_result['reply_text'] = intelligent_reply if reply_posted else None

                            if reply_posted:
                                logger.info(f"[NESTED] 💬 Replied to {author}: {intelligent_reply[:50]}...")
                    except Exception as e:
                        logger.warning(f"[NESTED] Reply generation failed: {e}")

                results.append(reply_result)

            logger.info(f"[NESTED] Processed {len(results)} nested replies in thread {parent_thread_idx}")

        except Exception as e:
            logger.error(f"[NESTED] Error processing nested replies: {e}", exc_info=True)

        return results

    async def execute_nested_reply(self, parent_thread_idx: int, reply_idx: int, reply_text: str) -> bool:
        """Execute reply to a nested reply (relative positioning)."""
        try:
            # Open reply box for nested reply
            opened = self.driver.execute_script("""
                const threadIdx = arguments[0];
                const replyIdx = arguments[1];
                const threads = document.querySelectorAll('ytcp-comment-thread');
                const thread = threads[threadIdx];
                if (!thread) return false;

                const repliesContainer = thread.querySelector('ytcp-comment-replies');
                if (!repliesContainer) return false;

                const replyElements = repliesContainer.querySelectorAll(
                    'ytcp-comment-replies[class*="expanded"]'
                );
                const reply = replyElements[replyIdx];
                if (!reply) return false;

                const replyBtn = reply.querySelector('[id*="reply-button"] button');
                if (!replyBtn) return false;

                replyBtn.click();
                return true;
            """, parent_thread_idx - 1, reply_idx)

            if not opened:
                return False

            delay = (self.human.human_delay(1.5, 0.6) if self.human else 1.5) * self.delay_multiplier
            await asyncio.sleep(delay)

            # Type reply (same as parent comment logic)
            typed = self.driver.execute_script("""
                const threadIdx = arguments[0];
                const replyIdx = arguments[1];
                const text = arguments[2];
                const threads = document.querySelectorAll('ytcp-comment-thread');
                const thread = threads[threadIdx];
                if (!thread) return false;

                # Find the reply's textarea (it appears after clicking Reply button)
                const textarea = thread.querySelector('textarea[id*="textarea"]');
                if (!textarea) return false;

                textarea.value = text;
                textarea.dispatchEvent(new Event('input', {bubbles: true}));
                return true;
            """, parent_thread_idx - 1, reply_idx, reply_text)

            if not typed:
                return False

            # 2026-02-04: Reduced pre-submit delay from 1.0s→0.5s
            delay = (self.human.human_delay(0.5, 0.3) if self.human else 0.5) * self.delay_multiplier
            await asyncio.sleep(delay)

            # Submit reply
            submitted = self.driver.execute_script("""
                const threadIdx = arguments[0];
                const threads = document.querySelectorAll('ytcp-comment-thread');
                const thread = threads[threadIdx];
                if (!thread) return false;

                const submitBtn = thread.querySelector('[id*="submit-button"] button');
                if (!submitBtn) return false;

                submitBtn.click();
                return true;
            """, parent_thread_idx - 1)

            return bool(submitted)

        except Exception as e:
            logger.warning(f"[NESTED] Reply execution failed: {e}")
            return False

    async def execute_reply(self, comment_idx: int, reply_text: str) -> bool:
        """Execute reply flow: Open box -> Type -> Submit."""
        thread_selector = self.selectors["comment_thread"]
        try:
            from modules.infrastructure.foundups_selenium.src.human_behavior import get_0102_behavior_interface
            behavior_profile = get_0102_behavior_interface(default="0102")
        except Exception:
            behavior_profile = (os.getenv("YT_0102_BEHAVIOR_INTERFACE") or os.getenv("YT_BEHAVIOR_INTERFACE") or os.getenv("YT_BEHAVIOR_PROFILE") or os.getenv("WSP_BEHAVIOR_PROFILE") or "0102").upper()

        # Open reply box
        # Open reply box using Robust Shadow DOM piercing
        reply_open = self.driver.execute_script(
            """
            const threadSelector = arguments[0];
            const threadIndex = arguments[1];
            
            // Recursive Hidden Element Finder
            function findInShadow(root, selector, textFilter = null) {
                if (!root) return null;
                
                // Direct check (selector match)
                if (selector) {
                    const el = root.querySelector(selector);
                    if (el) return el;
                }
                
                // Text content check (if textFilter provided)
                if (textFilter && !selector) {
                    // Check buttons in this root
                    const buttons = root.querySelectorAll('button');
                    for (const btn of buttons) {
                        if ((btn.textContent || '').trim().toUpperCase() === textFilter.toUpperCase()) {
                            return btn;
                        }
                    }
                }
                
                // Recursion into children with shadowRoots
                const children = root.querySelectorAll('*');
                for (let child of children) {
                    if (child.shadowRoot) {
                        const found = findInShadow(child.shadowRoot, selector, textFilter);
                        if (found) return found;
                    }
                }
                return null;
            }

            const threads = document.querySelectorAll(threadSelector);
            const thread = threads[threadIndex];
            if (!thread) return {success: false, error: 'Thread not found'};
            
            const startNode = thread.shadowRoot || thread;

            // 0. TEST MODULE ALIGNMENT: Prioritize simple ID found in known-good test
            // The test uses #reply-button directly. It might be the custom element itself.
            let replyBtn = findInShadow(startNode, '#reply-button');
            
            // 1. Try complex selector-based finds if simple ID fails
            if (!replyBtn) replyBtn = findInShadow(startNode, 'ytcp-comment-button#reply-button button');
            if (!replyBtn) replyBtn = findInShadow(startNode, '#reply-button-end button');
            if (!replyBtn) replyBtn = findInShadow(startNode, 'ytcp-button#reply-button button');
            
            // Wrapper/Shadow Fallback
            if (!replyBtn) {
                 const wrapper = findInShadow(startNode, 'ytcp-comment-button#reply-button');
                 if (wrapper) {
                     // Try clicking the wrapper itself if it has the ID
                     replyBtn = wrapper; 
                 }
            }

            // 2. Try text-based find (ultimate fallback)
            if (!replyBtn) {
                replyBtn = findInShadow(startNode, null, 'REPLY');
            }

            if (!replyBtn) return {success: false, error: 'Reply button not found (Deep Shadow Search)'};
            
            try { 
                replyBtn.scrollIntoView({behavior: 'smooth', block: 'center'});
                
                // FORCE CLICK: Dispatch events manually to bypass custom element quirks
                const validEvents = ['mousedown', 'mouseup', 'click'];
                validEvents.forEach(type => {
                    const event = new MouseEvent(type, {
                        bubbles: true,
                        cancelable: true,
                        view: window
                    });
                    replyBtn.dispatchEvent(event);
                });
                
                // Standard click as backup
                replyBtn.click();
            } catch (e) {
                return {success: false, error: 'Click failed: ' + e.toString()};
            }
            return {success: true};
            """,
            thread_selector,
            comment_idx - 1,
        )

        if not reply_open or not reply_open.get("success"):
            if reply_open and reply_open.get("error"):
                logger.warning(f"[REPLY] DOM open failed: {reply_open.get('error')}")
            return False

        # Human-like delay after opening reply box
        # 2026-02-04: Reduced from 1.5s→0.6s base (speed optimization)
        if self.human:
            await asyncio.sleep(self.human.human_delay(0.6, 0.4) * self.delay_multiplier)
        else:
            await asyncio.sleep(0.6 * self.delay_multiplier)
        logger.info(f"[DAEMON][REPLY-EXEC] Reply box opened, waited {0.6 * self.delay_multiplier:.2f}s")

        logger.info("[HARD-THINK] Reply box OPENED. Looking for textarea via Shadow DOM...")

        # Robust Textarea Finder & Typer
        # 1. LOOP: Find the element (Shadow DOM robust) - Retry for up to 5s
        # 2. Focus & Clear
        # 3. Type (Human or Direct)
        
        textarea = None
        max_retries = 10 
        retry_interval = 0.5
        
        for attempt in range(1, max_retries + 1):
            textarea = self.driver.execute_script(
                """
                const threadSelector = arguments[0];
                const threadIndex = arguments[1];
                const threads = document.querySelectorAll(threadSelector);
                const thread = threads[threadIndex];
                if (!thread) return null;
                
                const startNode = thread.shadowRoot || thread;
                
                // Helper to find in shadow
                function findInShadow(root, selector) {
                    if (!root) return null;
                    const el = root.querySelector(selector);
                    if (el) return el;
                    const children = root.querySelectorAll('*');
                    for (let child of children) {
                        if (child.shadowRoot) {
                            const found = findInShadow(child.shadowRoot, selector);
                            if (found) return found;
                        }
                    }
                    return null;
                }

                // Try multiple selectors for textarea
                let textarea = findInShadow(startNode, '#contenteditable-textarea');
                if (!textarea) textarea = findInShadow(startNode, 'div#contenteditable-textarea');
                if (!textarea) textarea = findInShadow(startNode, 'ytcp-mention-input'); 
                if (!textarea) textarea = findInShadow(startNode, 'textarea');

                return textarea;
                """,
                thread_selector,
                comment_idx - 1
            )
            
            if textarea:
                break
            
            if attempt < max_retries:
                logger.info(f"[HARD-THINK] Waiting for textarea to render... (Attempt {attempt}/{max_retries})")
                await asyncio.sleep(retry_interval)
        
        if textarea:
            logger.info(f"[HARD-THINK] Textarea FOUND. Typing reply ({len(reply_text)} chars)...")

            # ANTI-DETECTION: "Reading/thinking" pause before typing
            # 2026-02-04: Reduced from 2s→0.8s base (speed optimization)
            if self.delay_multiplier >= 1.0:  # Only for standard tempo
                if self.human:
                    think_time = self.human.human_delay(0.8, 0.4)
                else:
                    think_time = random.uniform(0.5, 1.2)
                logger.info(f"[ANTI-DETECTION] 🤔 Thinking before typing: {think_time:.1f}s")
                await asyncio.sleep(think_time)

            # Click to focus (JS click to be safe)
            self.driver.execute_script("arguments[0].click();", textarea)

            # Clear existing
            self.driver.execute_script("arguments[0].textContent = '';", textarea)

            # For contenteditable divs (YouTube reply boxes), send_keys() is unreliable
            # Type character-by-character with JS injection (visual human-like typing)
            logger.info(f"[DAEMON][REPLY-EXEC] ⌨️ Typing reply character-by-character...")

            # Calculate delay per character
            # 2026-02-04: Further reduced from 0.096→0.055 (burst mode handles variance)
            if self.human and HUMAN_BEHAVIOR_AVAILABLE:
                base_char_delay = 0.055  # ~43% faster (was 0.096)
                char_delay = base_char_delay * self.delay_multiplier
            else:
                char_delay = 0.035  # ~45% faster fallback (was 0.064)

            # Type character-by-character with delays (visible human-like typing)
            # YTR1: Track stale recovery state
            stale_recovered = False

            try:
                # 0102 interface: burst typing + micro-edits (no fixed cadence signature)
                burst_mode = (random.random() < 0.55 and self.delay_multiplier >= 1.0)
                i = 0
                while i < len(reply_text):
                    if burst_mode:
                        # "Dice-on-dice" chunking: chunks vary per step (1-4 chars)
                        chunk_size = 1 + int((random.random() ** 2) * 3)  # skew small, sometimes 4
                    else:
                        chunk_size = 1

                    chunk = reply_text[i:i + chunk_size]

                    # YTR1: Wrap execute_script with stale element recovery (single retry)
                    try:
                        self.driver.execute_script(
                            """
                            const el = arguments[0];
                            const chunk = arguments[1];
                            el.textContent += chunk;
                            el.dispatchEvent(new Event('input', { bubbles: true }));
                            """,
                            textarea,
                            chunk,
                        )
                        i += chunk_size  # Only advance on success

                    except StaleElementReferenceException:
                        if stale_recovered:
                            # Already tried once - fail
                            logger.error(f"[REPLY-EXEC] ❌ Textarea stale again at char {i}/{len(reply_text)} - aborting")
                            return False

                        logger.warning(f"[REPLY-EXEC] ⚠️ Textarea stale at char {i}/{len(reply_text)} - attempting recovery")
                        stale_recovered = True
                        await asyncio.sleep(0.3)

                        # Re-find textarea using same Shadow DOM method
                        textarea = self.driver.execute_script(
                            """
                            const threadSelector = arguments[0];
                            const idx = arguments[1];
                            const threads = document.querySelectorAll(threadSelector);
                            if (!threads || threads.length <= idx) return null;
                            const startNode = threads[idx].shadowRoot || threads[idx];

                            function findInShadow(root, selector) {
                                if (!root) return null;
                                const el = root.querySelector(selector);
                                if (el) return el;
                                const children = root.querySelectorAll('*');
                                for (let child of children) {
                                    if (child.shadowRoot) {
                                        const found = findInShadow(child.shadowRoot, selector);
                                        if (found) return found;
                                    }
                                }
                                return null;
                            }

                            let ta = findInShadow(startNode, '#contenteditable-textarea');
                            if (!ta) ta = findInShadow(startNode, 'div#contenteditable-textarea');
                            if (!ta) ta = findInShadow(startNode, 'ytcp-mention-input');
                            if (!ta) ta = findInShadow(startNode, 'textarea');
                            return ta;
                            """,
                            thread_selector,
                            comment_idx - 1
                        )

                        if not textarea:
                            logger.error(f"[REPLY-EXEC] ❌ Could not re-find textarea after stale")
                            return False

                        # Check what's already typed and adjust position
                        current = self.driver.execute_script("return arguments[0].textContent || '';", textarea)
                        i = len(current)
                        logger.info(f"[REPLY-EXEC] ✓ Textarea recovered, resuming at char {i}/{len(reply_text)}")
                        continue  # Retry this iteration

                    last = chunk[-1] if chunk else ""
                    if last == ' ':
                        await asyncio.sleep(char_delay * random.uniform(1.2, 2.2))
                    elif last in '.,!?':
                        await asyncio.sleep(char_delay * random.uniform(2.0, 3.8))
                    else:
                        await asyncio.sleep(char_delay * random.uniform(0.55, 1.7))

                    # Occasional hesitation pause (human "thinking" in-stream)
                    # 2026-02-04: Reduced from 5%→2%, shorter pause (was 0.4-2.4s)
                    hesitation_rate = 0.02
                    if random.random() < hesitation_rate and self.delay_multiplier >= 1.0:
                        hesitate = random.uniform(0.3, 1.2)
                        logger.debug(f"[ANTI-DETECTION] Typing hesitation: {hesitate:.1f}s")
                        await asyncio.sleep(hesitate)

                    # Rare micro-edit: simulate a quick correction (contenteditable-safe backspace)
                    if random.random() < 0.01 and self.delay_multiplier >= 1.0:
                        self.driver.execute_script(
                            """
                            const el = arguments[0];
                            const t = el.textContent || '';
                            if (t.length > 3) {
                              el.textContent = t.slice(0, -1);
                              el.dispatchEvent(new Event('input', { bubbles: true }));
                            }
                            """,
                            textarea,
                        )
                        await asyncio.sleep(char_delay * random.uniform(2.0, 4.0))

                # Trigger final validation events after typing complete
                self.driver.execute_script(
                    """
                    const el = arguments[0];
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    el.dispatchEvent(new KeyboardEvent('keyup', {'key': 'a'}));
                    """,
                    textarea
                )
                logger.info(f"[DAEMON][REPLY-EXEC] ✅ Character-by-character typing complete")

            except Exception as e:
                logger.error(f"[DAEMON][REPLY-EXEC] ❌ JS injection failed: {e}")
                import traceback
                traceback.print_exc()
                return False

            # VERIFY text was entered
            entered_text = self.driver.execute_script("return arguments[0].textContent", textarea)

            if not entered_text or len(entered_text.strip()) < len(reply_text.strip()) * 0.5:
                logger.error(f"[DAEMON][REPLY-EXEC] ❌ Verification FAILED! Expected {len(reply_text)} chars, got {len(entered_text) if entered_text else 0}")
                logger.error(f"[DAEMON][REPLY-EXEC]   Expected: '{reply_text[:50]}...'")
                logger.error(f"[DAEMON][REPLY-EXEC]   Got: '{entered_text[:50] if entered_text else ''}...'")
                return False
            else:
                logger.info(f"[DAEMON][REPLY-EXEC] ✅ Verification PASSED ({len(entered_text)} chars entered)")

        else:
             logger.error("  [REPLY] [HARD-THINK] Failed to find textarea after opening box (Shadow DOM search returned null)")
             return False

        # Human-like delay before submit
        # 2026-02-04: Reduced from 0.8s→0.4s base
        if self.human:
            await asyncio.sleep(self.human.human_delay(0.4, 0.3) * self.delay_multiplier)
        else:
            await asyncio.sleep(0.4 * self.delay_multiplier)

        # Submit - HARDENED 2026-01-18: Multiple selector strategies + text-based fallback
        submit_result = self.driver.execute_script(
            """
            const threadSelector = arguments[0];
            const threadIndex = arguments[1];
            const threads = document.querySelectorAll(threadSelector);
            const thread = threads[threadIndex];
            if (!thread) return {success: false, error: 'Thread not found'};

            // Helper to find button by text content (case-insensitive)
            function findButtonByText(root, text) {
                if (!root) return null;
                const buttons = root.querySelectorAll('button, ytcp-button');
                for (const btn of buttons) {
                    const btnText = (btn.textContent || btn.innerText || '').trim().toLowerCase();
                    if (btnText === text.toLowerCase()) {
                        // Return the actual clickable element (button inside ytcp-button or the button itself)
                        return btn.querySelector('button') || btn;
                    }
                }
                return null;
            }

            // Helper to search in shadow DOM recursively
            function findInShadow(root, selector) {
                if (!root) return null;
                try {
                    const el = root.querySelector(selector);
                    if (el) return el;
                } catch(e) {}
                const children = root.querySelectorAll('*');
                for (const child of children) {
                    if (child.shadowRoot) {
                        const found = findInShadow(child.shadowRoot, selector);
                        if (found) return found;
                    }
                }
                return null;
            }

            let submitBtn = null;

            // Strategy 1: Direct ID selectors (legacy working paths)
            submitBtn = thread.querySelector('#submit-button button');
            if (!submitBtn) submitBtn = thread.querySelector('ytcp-button#submit-button button');
            if (!submitBtn) submitBtn = document.querySelector('ytcp-comment-creator #submit-button button');

            // Strategy 2: Look for Reply button in comment-creator section
            if (!submitBtn) {
                const creator = thread.querySelector('ytcp-comment-creator');
                if (creator) {
                    submitBtn = creator.querySelector('#submit-button button');
                    if (!submitBtn) submitBtn = findButtonByText(creator, 'Reply');
                }
            }

            // Strategy 3: Look in iron-pages or paper-button wrappers
            if (!submitBtn) submitBtn = thread.querySelector('iron-pages #submit-button button');
            if (!submitBtn) submitBtn = thread.querySelector('[slot="buttons"] button');

            // Strategy 4: Shadow DOM deep search
            if (!submitBtn) submitBtn = findInShadow(thread, '#submit-button button');

            // Strategy 5: Text-based fallback - find button with text "Reply"
            if (!submitBtn) {
                submitBtn = findButtonByText(thread, 'Reply');
            }

            // Strategy 6: Global search in comment creator (when thread scope fails)
            if (!submitBtn) {
                const globalCreator = document.querySelector('ytcp-comment-creator');
                if (globalCreator) {
                    submitBtn = globalCreator.querySelector('#submit-button button');
                    if (!submitBtn) submitBtn = findButtonByText(globalCreator, 'Reply');
                }
            }

            if (submitBtn && !submitBtn.disabled) {
                // FORCE CLICK: dispatch mouse events for custom element compatibility
                try {
                    submitBtn.scrollIntoView({behavior: 'instant', block: 'center'});
                    ['mousedown', 'mouseup', 'click'].forEach(type => {
                        submitBtn.dispatchEvent(new MouseEvent(type, {bubbles: true, cancelable: true, view: window}));
                    });
                } catch(e) {
                    submitBtn.click();
                }
                return {success: true, strategy: 'found'};
            }
            return {success: false, error: 'Submit button not found/disabled', searched: ['#submit-button', 'text:Reply', 'shadow-dom']};
            """,
            thread_selector,
            comment_idx - 1,
        )

        if not submit_result or not submit_result.get("success"):
            if submit_result and submit_result.get("error"):
                logger.warning(f"[REPLY] DOM submit failed: {submit_result.get('error')}")
            return False

        return True
