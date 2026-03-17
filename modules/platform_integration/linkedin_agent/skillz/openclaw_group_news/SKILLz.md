---
name: openclaw_group_news
description: Search and post OpenClaw news to LinkedIn OpenClaw Group
version: 1.0.0
author: 0102
agents: [qwen, selenium]
dependencies: [web_search, anti_detection_poster]
domain: platform_integration
intent_type: CONTENT_GENERATION
promotion_state: prototype
rate_limit: 3_per_day
linkedin_group: https://www.linkedin.com/groups/6729915/
category: workflow
evals: []
---
# OpenClaw Group News Poster

**Purpose**: Autonomous search, rate, and post OpenClaw news to LinkedIn group (1-3 times/day).

**Position in Flow**: This skill runs BEFORE comment engagement - it's the content seeding step.

---

## Workflow

### Automated Search Phase (via DuckDuckGo News API)

The executor automatically searches these queries (with 2-4s delays to avoid rate limits):
```
News API queries:
1. "OpenClaw AI agent"
2. "OpenClaw framework"
3. "lobster.cash Crossmint"
4. "OpenClaw OpenAI nonprofit"
5. "OpenClaw wallet"
6. "IronClaw OpenClaw"

Web search fallback (if news insufficient):
7. "OpenClaw"
8. "OpenClaw AI framework"
9. "Peeka AI agent"
```

**Ecosystem Terms Recognized** (0.95 relevance score):
- `lobster.cash` - Payment standard for OpenClaw agents
- `Crossmint` - Infrastructure partner
- `Peeka` - New AI agent in ecosystem

**Search Behavior**:
- Uses DuckDuckGo news API (timelimit: last month)
- Rate limit delays: 2-4 seconds between queries
- Deduplicates URLs across queries
- Falls back to web search if news insufficient
- Returns max 10 items for rating

### Manual Research Phase (if automated search insufficient)

```
1. OPEN separate research tab (keep LinkedIn group tab untouched)
     ↓
2. GOOGLE SEARCH for topic (e.g., "lobster.cash Crossmint OpenClaw latest news")
     ↓
3. SCAN search results for headlines, sources, dates
     ↓
4. CLICK best article (prioritize major tech/crypto news sites)
     ↓
5. READ full article with get_page_text (not screenshots)
     ↓
6. TAKE NOTES on key points:
   - What happened?
   - Who's involved?
   - Why does it matter to OpenClaw users?
   - What's the date?
   - Save article URL for link
     ↓
7. CHECK second source if needed (don't over-research - one solid article is enough)
```

### Posting Phase

```
8. SWITCH to LinkedIn group tab
     ↓
9. CLICK "Start a post in this group"
     ↓
10. TYPE post in editor:
    🦞 emoji branding (OpenClaw group style)
    Clear title/headline
    Concise summary (main points relevant to group)
    Link to full article at bottom
     ↓
11. SCROLL UP in editor to verify post looks right
     ↓
12. CLICK Post button (autonomous posting authorized)
     ↓
13. LOG to agents_social_posts (WSP 78)
```

### LinkedIn Group Membership DAE (Welcome + Approve)

This skill now includes a second flow for `https://www.linkedin.com/groups/6729915/manage/membership/requested/`:

```
1. OPEN membership request queue
     ->
2. READ first pending member row (name/headline/profile/image)
     ->
3. DETECT language from script (ko/ja/zh/sr/ar/en fallback)
     ->
4. DRAFT welcome message:
   - template fallback (localized)
   - optional Qwen3 via IronClaw gateway (`/v1/chat/completions`)
   - set `LINKEDIN_GROUP_WELCOME_MODEL=local/qwen3-4b` (or another model id)
   - disable drafting with `LINKEDIN_GROUP_WELCOME_USE_IRONCLAW=0`
     ->
5. CLICK row overflow ("...") -> select Message
   - keyword match across locales
   - fallback to second menu item (Message)
     ->
6. TYPE welcome message in overlay (`.msg-form__contenteditable`)
   CLICK Send (`.msg-form__send-button`)
     ->
7. CLICK Approve on request row
     ->
8. LOG to `agents_social_group_actions` (WSP 78 `agents_*` namespace)
```

**Dry-run watch mode**:
- No approval clicks.
- Captures message drafts and optional screenshots so 012 can observe behavior before enabling live mode.

**CLI entry**:
- Social Media DAE -> `LinkedIn Group Membership DAE (Welcome + Approve)`

**Live policy toggles**:
- `welcome + approve`
- `approve only`
- `welcome only`
- `full cycle` (process queue, then post OpenClaw news)

### Key Tips

- **Do ALL research before touching LinkedIn tab** — switching back and forth is inefficient
- **Keep posts concise and group-relevant** — summaries, not copy-paste
- **Always use 🦞 lobster emojis** to match the group's branding
- **Article link auto-generates preview card** — looks great in LinkedIn
- **Autonomous posting authorized** — no 012 confirmation required for group posts

---

## News Relevance Rating

Simple 4-dimension scoring (lighter than WSP 15 MPS):

| Dimension | Weight | Score Range | Description |
|-----------|--------|-------------|-------------|
| **Recency** | 0.3 | 0.0-1.0 | Published < 24h = 1.0, < 7d = 0.5, > 7d = 0.0 |
| **Source Authority** | 0.2 | 0.0-1.0 | Major tech outlet = 1.0, blog = 0.5, unknown = 0.2 |
| **OpenClaw Relevance** | 0.4 | 0.0-1.0 | Direct mention = 1.0, related topic = 0.5 |
| **Engagement Potential** | 0.1 | 0.0-1.0 | Breaking news = 1.0, update = 0.5, routine = 0.2 |

**Formula**: `score = (recency * 0.3) + (authority * 0.2) + (relevance * 0.4) + (engagement * 0.1)`

**Threshold**: Only post if `score >= 0.6`

---

## LinkedIn Group DOM Selectors

**Group URL**: `https://www.linkedin.com/groups/6729915/`

### Start Post Button
```
Selector: button.share-box-feed-entry__trigger (legacy)
Fallback: button[class*='hare-box-feed-entry'] (LinkedIn redesign)
Fallback: button[class*='share-box']
Position: top=268px, left=72px, width=439px, height=48px
Note: LinkedIn may use hare-box-v2__modal, hare-creation-.tate for modal
```

### Post Textarea
```
Selector: div.ql-editor[data-placeholder]
Fallback: div[contenteditable="true"]
```

### Post Submit Button
```
Selector: button.share-actions__primary-action (text="Post")
Fallback: button[id^="ember"][class*="primary-action"]
Position: top=349px, left=452px, width=63px, height=32px
```

---

## Post Template

```
{headline}

{summary}

Source: {url}

#OpenClaw #AI #Agents
```

**Character Limit**: 3000 (LinkedIn standard)

---

## Rate Limiting

| Constraint | Value | Implementation |
|------------|-------|----------------|
| Max posts/day | 3 | Check `agents_social_posts` table |
| Min interval | 4 hours | Time-based cooldown |
| Duplicate check | 7 days | Hash URL, check history |

---

## Database Integration (WSP 78)

All posts logged to unified database:

```sql
-- agents_social_posts table
INSERT INTO agents_social_posts (
    id, platform, group_id, content, source_url,
    relevance_score, posted_at, post_status
) VALUES (?, 'linkedin', '6729915', ?, ?, ?, datetime('now'), 'pending');
```

---

## Executor Interface

```python
from modules.platform_integration.linkedin_agent.skillz.openclaw_group_news import (
    search_openclaw_news,
    rate_news_relevance,
    post_to_group
)

# Search
news_items = search_openclaw_news(max_results=10)

# Rate and filter
rated = [(item, rate_news_relevance(item)) for item in news_items]
filtered = [(item, score) for item, score in rated if score >= 0.6]

# Post top item (if within rate limit)
if filtered and can_post_today():
    top_item, score = max(filtered, key=lambda x: x[1])
    post_to_group(top_item)
```

---

## Timing Strategy

**No LinkedIn scheduling API** - must run on timer:

| Option | Implementation | Pros | Cons |
|--------|----------------|------|------|
| **Cron job** | Run at 9am, 1pm, 5pm PST | Simple | Fixed times |
| **Random window** | Run 1-3x within 8am-6pm | Human-like | More complex |
| **Event-driven** | Post when major news found | Timely | Unpredictable |

**Recommendation**: Random window with 4-hour minimum spacing.

---

## WSP Compliance

- **WSP 78**: All posts logged to unified `agents_*` namespace
- **WSP 42**: LinkedIn platform integration standards
- **WSP 50**: Pre-action verification (check rate limits)
- **WSP 96**: Skill definition per WRE protocol

---

## Changelog

### v1.0.1 (2026-02-23)
- Added hare-box fallback selectors (LinkedIn redesign)
- Added search terms: OpenClaw OpenAI nonprofit, OpenClaw wallet, IronClaw OpenClaw
- Fixed executor: create_driver → setup_driver (AntiDetectionLinkedIn API)
- Audit: docs/LINKEDIN_OPENCLAW_GROUP_NEWS_AUDIT_20260223.md

### v1.0.0 (2026-02-19)
- Initial skill creation
- News search via web_search MCP
- 4-dimension relevance rating
- LinkedIn group DOM selectors captured
- Rate limiting: 3 posts/day, 4-hour minimum

---

**Skill Status**: PROTOTYPE

## Current Queue

| Topic | Research Status | Post Status | Notes |
|-------|-----------------|-------------|-------|
| SecurityWeek OpenClaw | Complete | **POSTED** | Live in group |
| Lobster.cash/Crossmint | Started | Pending | Crossmint launched lobster.cash as open payment standard for OpenClaw agents (~6 days ago). Need full article read + post composition |

**Next Steps**:
1. Complete Lobster.cash post (read full article, compose, confirm with 012, post)
2. Test news search automation with web_search MCP
3. Validate DOM selectors reliability
4. Add to LinkedIn automation pre-flow cron

---

## CLI Integration

Access via main.py menu:
```
Option 4: Social Media DAE (012 Digital Twin)
  └── Option 2: LinkedIn Group Post (OpenClaw News)
  └── Option 3: Test Submenu (Full Action Logging)
```

Test submenu provides:
- News relevance rating test
- Rate limiting test
- Database connection test
- Full flow dry run
- Pytest suite execution

All tests generate copy/paste-friendly logs for troubleshooting.
