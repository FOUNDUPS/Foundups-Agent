"""Studio row extraction and local adapters; no browser/provider is constructed here."""

import logging

logger = logging.getLogger(__name__)


COMMENT_IDENTITY_SCRIPT = r"""
function rowOriginalComment(row) {
    if (!row) return null;
    const selector = 'ytcp-comment-view-model, ytcp-comment-view, ytcp-comment';
    if (row.matches && row.matches(selector)) return row;
    for (const node of row.querySelectorAll(selector)) {
        if (node.closest && !node.closest('ytcp-comment-replies') &&
            node.closest('ytcp-comment-thread') === row) return node;
    }
    return row;
}
function rowOwnsNode(row, original, node, threadLevel = false) {
    if (!row || !original || !node || !node.closest || !row.contains(node) ||
        node.closest('ytcp-comment-replies') || node.closest('ytcp-comment-thread') !== row) return false;
    const owner = node.closest('ytcp-comment-view-model, ytcp-comment-view, ytcp-comment');
    if (original === row) return !owner;
    if (original.contains(node)) return owner === original;
    return threadLevel && !owner;
}
function trustedRowUrl(raw, hosts, protocols = ['https:']) {
    if (typeof raw !== 'string' || !raw.trim()) return null;
    try {
        const url = new URL(raw, 'https://studio.youtube.com');
        return protocols.includes(url.protocol) && hosts.includes(url.hostname) &&
            !url.username && !url.password && !url.port ? url : null;
    } catch (e) { return null; }
}
function rowVideoLink(link) {
    const url = trustedRowUrl(link.getAttribute('href') || link.href,
        ['studio.youtube.com', 'youtube.com', 'www.youtube.com', 'm.youtube.com']);
    if (!url) return null;
    let id = null;
    if (url.hostname === 'studio.youtube.com')
        id = (url.pathname.match(/^\/video\/([A-Za-z0-9_-]+)(?:\/|$)/) || [])[1];
    else if (url.pathname === '/watch') id = url.searchParams.get('v');
    else id = (url.pathname.match(/^\/shorts\/([A-Za-z0-9_-]+)(?:\/|$)/) || [])[1];
    return id && /^[A-Za-z0-9_-]+$/.test(id) ? {id, url: url.href} : null;
}
function rowThumbnailId(image) {
    const raw = image.getAttribute('src');
    if (!raw || !raw.startsWith('https://')) return null;
    const url = trustedRowUrl(raw, ['i.ytimg.com']);
    return url && !url.search && !url.hash &&
        (url.pathname.match(/^\/vi\/([A-Za-z0-9_-]{11})\/default\.jpg$/) || [])[1] || null;
}
function rowVideoMetadata(row) {
    const original = rowOriginalComment(row), ids = new Set(), urls = new Map(), titles = new Set();
    let legacyTitle = null;
    for (const info of row.querySelectorAll('ytcp-video-thumbnail-with-info, ytcp-comment-video-thumbnail#video-thumbnail')) {
        const modern = info.matches('ytcp-comment-video-thumbnail#video-thumbnail');
        if (!rowOwnsNode(row, original, info, !modern)) continue;
        const local = new Set();
        for (const link of info.querySelectorAll('a[href]')) {
            if (!rowOwnsNode(row, original, link, !modern)) continue;
            const identity = rowVideoLink(link);
            if (identity) {
                local.add(identity.id); ids.add(identity.id);
                if (!urls.has(identity.id)) urls.set(identity.id, identity.url);
            }
        }
        if (modern) for (const image of info.querySelectorAll('ytcp-img-with-fallback#video-thumbnail img#img-with-fallback')) {
            if (!rowOwnsNode(row, original, image)) continue;
            const id = rowThumbnailId(image);
            if (id) { local.add(id); ids.add(id); }
        }
        const title = info.querySelector(modern ? '#video-title' : '#video-title, [data-video-title], [title]');
        const text = title && rowOwnsNode(row, original, title, !modern) &&
            (title.getAttribute('title') || title.getAttribute('data-video-title') || title.textContent || '')
            .trim().replace(/\s+/g, ' ').substring(0, 300);
        if (text && local.size === 1) titles.add(text);
        if (text && !modern && local.size === 0) legacyTitle = text;
    }
    if (ids.size > 1) return {video_id: null, video_title: null, video_url: null};
    const id = ids.size === 1 ? ids.values().next().value : null;
    return {video_id: id, video_title: titles.size === 1 ? titles.values().next().value :
        (ids.size === 0 ? legacyTitle : null), video_url: id && urls.get(id) || null};
}
function rowVideoIdentity(row) { return rowVideoMetadata(row).video_id; }
function rowAuthorIdentity(row) {
    const original = rowOriginalComment(row);
    let identity = null;
    for (const author of original.querySelectorAll('#author-text, yt-formatted-string.author-text, a#name, .author-name, ytcp-comment-author')) {
        if (!rowOwnsNode(row, original, author)) continue;
        const handle = (author.textContent || '').trim().replace(/\s+/g, ' ');
        if (!handle) continue;
        const link = author.matches('a[href]') ? author : author.querySelector('a[href]');
        if (link && !rowOwnsNode(row, original, link)) return null;
        const url = link && trustedRowUrl(link.getAttribute('href') || link.href,
            ['studio.youtube.com', 'youtube.com', 'www.youtube.com', 'm.youtube.com'], ['https:', 'http:']);
        if (link && !url) return null;
        if (author.matches('a#name') && !url) return null;
        if (url && !/^\/(?:channel\/[A-Za-z0-9_-]+|@[^/]+)\/?$/.test(url.pathname)) return null;
        const candidate = {author_name: handle.replace(/^@/, ''), author_handle: handle,
            channel_id: url && (url.pathname.match(/^\/channel\/([^/]+)(?:\/|$)/) || [])[1] || null,
            author_url: url ? url.origin + url.pathname : null};
        if (identity && (candidate.author_name !== identity.author_name ||
            candidate.channel_id !== identity.channel_id || candidate.author_url !== identity.author_url)) return null;
        identity = candidate;
    }
    return identity;
}
function rowContentElement(row) {
    const original = rowOriginalComment(row);
    for (const selector of ['yt-formatted-string#content-text, #content-text', '#content, .comment-text, ytcp-comment-renderer'])
        for (const node of original.querySelectorAll(selector))
            if (rowOwnsNode(row, original, node)) return node;
    return null;
}

function normalizedHandle(value) {
    if (typeof value !== 'string') return null;
    const handle = value.trim().toLowerCase();
    return /^@[^\/?#\s@]+$/.test(handle) ? handle : null;
}
function nativeReceivingMatches(expected) {
    if (!expected || !/^UC[A-Za-z0-9_-]{22}$/.test(expected._target_channel_id || '') ||
        !normalizedHandle(expected._target_channel_handle)) return false;
    try {
        const values = [
            window.ytcfg && typeof window.ytcfg.get === 'function' ? window.ytcfg.get('CHANNEL_ID') : null,
            window.yt && window.yt.config_ ? window.yt.config_.CHANNEL_ID : null
        ].filter(value => value !== undefined && value !== null);
        return values.length > 0 && values.every(value => typeof value === 'string' && value === expected._target_channel_id);
    } catch (e) { return false; }
}
function rowRequiresNativeProof(row) {
    const original = rowOriginalComment(row);
    return Array.from(original.querySelectorAll('ytcp-comment-video-thumbnail#video-thumbnail, a#name'))
        .some(node => rowOwnsNode(row, original, node));
}

function commentIdentity(row, nested = false) {
    if (!row) return null;
    const original = rowOriginalComment(row);
    const candidates = new Set();
    for (const node of [row, original]) {
        for (const attr of ['data-comment-id', 'comment-id']) {
            const id = typeof node.getAttribute === 'function' ? node.getAttribute(attr) : null;
            if (id && /^[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)?$/.test(id)) candidates.add(id);
        }
    }
    for (const link of original.querySelectorAll('a[href]')) {
        if (link.closest && (link.closest('ytcp-video-thumbnail-with-info, ytcp-comment-video-thumbnail') || (!nested && !rowOwnsNode(row, original, link)))) continue;
        try {
            const url = new URL(link.href, 'https://studio.youtube.com');
            if (!['studio.youtube.com', 'youtube.com', 'www.youtube.com', 'm.youtube.com'].includes(url.hostname)) continue;
            const id = url.searchParams.get('lc') || url.searchParams.get('commentId');
            if (id && /^[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)?$/.test(id)) candidates.add(id);
        } catch (e) {}
    }
    return candidates.size === 1 ? candidates.values().next().value : null;
}
function matchesCommentTarget(row, expected) {
    if (location.origin !== 'https://studio.youtube.com') return false;
    if (!row || !row.isConnected || !expected || !expected.text || !expected.author_name ||
        !expected.comment_id || !expected.video_id || commentIdentity(row) !== expected.comment_id ||
        rowVideoIdentity(row) !== expected.video_id) return false;
    const norm = value => (value || '').replace(/\s+/g, ' ').trim();
    const exact = value => (value || '').replace(/\r\n/g, '\n').trim();
    const text = rowContentElement(row), author = rowAuthorIdentity(row);
    if (!text || !author || exact(text.textContent) !== exact(expected.text) ||
        norm(author.author_handle).replace(/^@/, '') !== norm(expected.author_handle || expected.author_name).replace(/^@/, '')) return false;
    if (!expected._target_channel_id || !location.pathname.startsWith('/channel/' + expected._target_channel_id + '/')) return false;
    if (expected.channel_id && author.channel_id !== expected.channel_id) return false;
    if (expected.author_url && author.author_url !== expected.author_url) return false;
    if (rowRequiresNativeProof(row) && !nativeReceivingMatches(expected)) return false;
    return true;
}
"""


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

                // Use the same owned original-comment identity at extraction and Submit.
                const contentText = rowContentElement(thread);
                const text = contentText ? contentText.textContent.trim() : '';
                const author = rowAuthorIdentity(thread);
                const authorName = author ? author.author_name : 'Unknown';
                const authorHandle = author ? author.author_handle : 'Unknown';
                const channelId = author ? author.channel_id : null;

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

                // Modern thumbnail identity and legacy anchors share one scoped owner.
                const video = rowVideoMetadata(thread);

                return {
                    comment_id: commentIdentity(thread),
                    text: text,
                    author_name: authorName,
                    author_handle: authorHandle,
                    channel_id: channelId,
                    author_url: author ? author.author_url : null,
                    is_mod: isMod,
                    is_subscriber: isSubscriber,
                    published_time: publishedTime,
                    video_title: video.video_title,
                    video_id: video.video_id,
                    video_url: video.video_url
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
        data = driver.execute_script(COMMENT_IDENTITY_SCRIPT + COMMENT_ROW_SCRIPT, comment_idx - 1)
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
        use_dom=True, ui_tars_bridge=getattr(dae, 'ui_tars_bridge', None), check_moderators=dae.check_moderators,
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

