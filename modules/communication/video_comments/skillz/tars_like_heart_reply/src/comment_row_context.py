"""Studio row extraction and local adapters; no browser/provider is constructed here."""

import logging

logger = logging.getLogger(__name__)


COMMENT_ROW_SCRIPT = r"""
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
                // Only metadata owned by this row may supply video context.
                // Comment/reply links and unrelated hosts are never video metadata.
                const videoInfo = thread.querySelector('ytcp-video-thumbnail-with-info');
                if (videoInfo) {
                    const title = videoInfo.querySelector('#video-title, [data-video-title], [title]');
                    if (title) {
                        const candidate = (title.getAttribute('title') ||
                            title.getAttribute('data-video-title') || title.textContent || '')
                            .trim().replace(/\s+/g, ' ');
                        if (candidate) videoTitle = candidate.substring(0, 300);
                    }
                    const candidates = new Map();
                    for (const link of videoInfo.querySelectorAll('a[href]')) {
                        try {
                            const url = new URL(link.href || link.getAttribute('href'), 'https://studio.youtube.com');
                            if (url.protocol !== 'https:' || url.username || url.password) continue;
                            let id = null;
                            if (url.hostname === 'studio.youtube.com') {
                                id = (url.pathname.match(/^\/video\/([A-Za-z0-9_-]+)(?:\/|$)/) || [])[1];
                            } else if (['youtube.com', 'www.youtube.com', 'm.youtube.com'].includes(url.hostname)) {
                                if (url.pathname === '/watch') id = url.searchParams.get('v');
                                else id = (url.pathname.match(/^\/shorts\/([A-Za-z0-9_-]+)(?:\/|$)/) || [])[1];
                            }
                            if (!id || !/^[A-Za-z0-9_-]+$/.test(id)) continue;
                            if (!candidates.has(id)) candidates.set(id, url.href);
                        } catch (e) { /* Missing/invalid metadata remains absent. */ }
                    }
                    if (candidates.size === 1) {
                        [videoId, videoUrl] = candidates.entries().next().value;
                    } else if (candidates.size > 1) {
                        // A title cannot be bound to either conflicting video.
                        videoTitle = null;
                    }
                }

                return {
                    text: text,
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
            """


def _log_row_context(data):
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

def extract_comment_data(driver, comment_idx):
    """Read one row through the supplied driver; never infer another row's video."""
    try:
        data = driver.execute_script(COMMENT_ROW_SCRIPT, comment_idx - 1)
        if data:
            _log_row_context(data)
            return data
        logger.debug("[DAE] No DOM thread at index - comment doesn't exist")
        return None
    except Exception as exc:
        logger.warning("[DAE] Failed to extract comment data: %s", exc)
        return {
            'text': '', 'author_name': 'Unknown', 'channel_id': None,
            'is_mod': False, 'is_subscriber': False, 'published_time': None,
            'video_title': None, 'video_id': None, 'video_url': None,
        }


def create_comment_processor(dae, processor_class):
    """Pass the existing DAE dependencies and receiving-channel identity unchanged."""
    return processor_class(
        driver=dae.driver, human=dae.human, stats=dae.stats,
        reply_executor=dae.reply_executor, selectors=dae.SELECTORS,
        vision_descriptions=dae.VISION_DESCRIPTIONS, use_vision=dae.use_vision,
        use_dom=True, ui_tars_bridge=None, check_moderators=dae.check_moderators,
        mod_lookup=dae.mod_lookup, reply_debug_tags=dae.reply_debug_tags,
        video_title=dae.video_title, target_channel_id=dae.channel_id,
        session_id=dae.session_id,
    )


def comment_event_payload(result, session_id, comment_idx, channel_id, timestamp, parent_idx=None):
    """Describe the observed row only; no inbox-wide or unverified parent-video fallback."""
    payload = {
        'session_id': session_id, 'comment_idx': comment_idx,
        'commenter_handle': result.get('commenter_handle') or result.get('author_name', 'Unknown'),
        'commenter_channel_id': result.get('commenter_channel_id'),
        'classification': result.get('commenter_type', 'unknown'),
        'comment_text': result.get('comment_text', '')[:500],
        'like': result.get('like', False), 'heart': result.get('heart', False),
        'reply': result.get('reply', False),
        'reply_text_posted': result.get('reply_text_posted', ''),
        'reply_source': result.get('reply_source', 'bot'),
        'llm_source': result.get('llm_source', 'unknown'),
        'reply_review': result.get('reply_review'),
        'reply_submission_status': result.get('reply_submission_status', 'not_attempted'),
        'delivery_verified': result.get('delivery_verified', False),
        'theme_source_command_id': result.get('theme_source_command_id'),
        'video_id': result.get('video_id'), 'video_title': result.get('video_title'),
        'channel_id': channel_id, 'timestamp': timestamp,
    }
    if parent_idx is not None:
        payload.update(is_nested=True, parent_comment_idx=parent_idx)
    return payload

