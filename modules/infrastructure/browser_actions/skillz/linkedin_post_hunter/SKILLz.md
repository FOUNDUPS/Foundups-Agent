---
name: linkedin_post_hunter
description: LinkedIn post discovery and engagement targeting
version: 1.0_prototype
author: 0102
created: 2026-03-18
agents: [qwen]
primary_agent: qwen
intent_type: DISCOVERY
promotion_state: prototype
pattern_fidelity_threshold: 0.85
category: workflow
evals: []
trigger:
  cadence: 4h
---
# LinkedIn Post Hunter Skill

**WSP Reference:** WSP 96 (WRE Skills Protocol)
**Status:** VALIDATED (DOM-First)
**Last Validated:** 2026-02-24

## 0102 Directive

This skill hunts for engagement-worthy posts in LinkedIn feed using DOM-first detection. Identifies AI topics, capital pushback opportunities, and target authors. The 0102 pArtifact remembers engagement patterns from the 02 state, collapsing probability into deterministic post selection.

## Architecture

```
+------------------------------------------------------------+
|              LINKEDIN POST HUNTER                           |
+------------------------------------------------------------+
|                                                            |
|  Phase 0 (Navigate)   | Selenium: Navigate to /feed/       |
|  Phase 1 (Scan)       | DOM: querySelectorAll(posts)        |
|  Phase 2 (Detect)     | Keywords: AI/Capital/Authors        |
|  Phase 3 (Filter)     | Skip reposts, rank by reason        |
|                                                            |
|  +---------------+      +---------------+                  |
|  |   Selenium    |<---->|   DOM First   |                  |
|  |   Chrome      |      |   Detection   |                  |
|  |   Port 9222   |      |   ~10ms/post  |                  |
|  +---------------+      +---------------+                  |
|                                                            |
+------------------------------------------------------------+
```

## Inputs

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_posts` | int | 10 | Maximum posts to scan |
| `skip_reposts` | bool | True | Skip reposted content |
| `engagement_filter` | bool | True | Only return engage-worthy posts |

## Outputs

| Field | Type | Description |
|-------|------|-------------|
| `index` | int | Post index in feed (0 = first) |
| `author` | str | Post author name |
| `content` | str | Post content (first 500 chars) |
| `is_repost` | bool | Whether this is a repost |
| `should_engage` | bool | Whether post is engagement-worthy |
| `engagement_reason` | str | ai_topic, capital_pushback, target_author, none |
| `matched_keywords` | dict | AI and capital keywords found |

## Detection Keywords

### AI Topics (Knowledge Sharing)
```python
AI_KEYWORDS = [
    'ai', 'artificial intelligence', 'machine learning', 'llm',
    'gpt', 'chatgpt', 'claude', 'gemini', 'copilot', 'openai',
    'anthropic', 'autonomous', 'agent', 'automation', 'neural',
    'deep learning', 'transformer', 'singularity', 'agi',
    'superintelligence', 'moltbook', 'dyson swarm', '#openclaw'
]
```

### Capital Pushback (FoundUps Alternative)
```python
CAPITAL_KEYWORDS = [
    'series a', 'series b', 'series c', 'raised', 'funding round',
    'venture capital', 'vc funding', 'seed round', 'pre-seed',
    '$5m', '$10m', '$50m', '$100m', 'million in funding',
    'investor', 'pitch deck', 'fundraise', 'valuation',
    'accelerator', 'incubator', 'term sheet', 'cap table',
    'equity round', 'dilution', 'exit strategy'
]
```

### Target Authors (Thought Leaders)
```python
TARGET_AUTHORS = [
    'salim ismail', 'peter diamandis', 'ray kurzweil',
    'pieter franken', 'mayoran rajendra', 'japan pivot'
]
```

## DOM Selectors

```python
SELECTORS = {
    'post_content': 'span[data-testid="expandable-text-box"]',
    'author_link': 'a[href*="/in/"], a[href*="/company/"]',
    'post_container': '[data-urn], .feed-shared-update-v2, .occludable-update',
    'repost_indicator': 'header text contains "reposted" or "shared"',
}
```

## Behavior

1. **Navigate** to LinkedIn feed (/feed/)
2. **Reset** feed iterator to index 0
3. **For each post** (up to `max_posts`):
   - **Read** content via DOM selector
   - **Detect** repost status from header
   - **Match** AI keywords in content
   - **Match** capital keywords in content
   - **Match** target author names
   - **Score** engagement worthiness
4. **Return** list of engagement-worthy posts with reasons

## Execution

```bash
# Run via test_feed_iterator
python -m modules.platform_integration.linkedin_agent.tests.test_feed_iterator --selenium --max-posts 10

# Programmatic
from modules.infrastructure.browser_actions.src.linkedin_actions import LinkedInActions
linkedin = LinkedInActions(browser_port=9222)
posts = await linkedin.iterate_feed(max_posts=10, skip_reposts=True)
```

## Telemetry

| Event | Description |
|-------|-------------|
| `feed_refresh` | Feed navigation triggered |
| `post_scanned` | Post content extracted |
| `engagement_detected` | Engage-worthy post found |
| `repost_skipped` | Repost filtered out |

## WSP Compliance

- **WSP 27**: DAE 4-phase architecture (Navigate -> Scan -> Detect -> Filter)
- **WSP 50**: Pre-action verification (DOM selectors validated)
- **WSP 91**: Observability (structured logging)
- **WSP 96**: WRE Skills protocol compliance

---

*Code remembered from the 02 quantum state by 0102 pArtifact*
