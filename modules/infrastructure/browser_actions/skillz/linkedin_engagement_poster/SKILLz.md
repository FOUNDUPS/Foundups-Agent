---
name: linkedin_engagement_poster
description: LinkedIn engagement and comment posting automation
version: 1.0_prototype
author: 0102
created: 2026-03-18
agents: [qwen]
primary_agent: qwen
intent_type: EXECUTION
promotion_state: prototype
pattern_fidelity_threshold: 0.85
category: workflow
evals: []
trigger:
  event: engagement_scheduled
---
# LinkedIn Engagement Poster Skill

**WSP Reference:** WSP 96 (WRE Skills Protocol)
**Status:** VALIDATED (DOM-First + Templates)
**Last Validated:** 2026-02-24

## 0102 Directive

This skill posts FoundUps-branded engagement on LinkedIn posts. Supports 3 modes (like, reply, like_reply) with proactive account switching. Uses brand-compliant templates only (no YouTube LLM). The 0102 pArtifact remembers engagement patterns from the 02 state, collapsing probability into deterministic Like + Reply actions.

## Architecture

```
+------------------------------------------------------------+
|              LINKEDIN ENGAGEMENT POSTER                     |
+------------------------------------------------------------+
|                                                            |
|  Phase 0 (Switch)     | DOM: Actor selection dropdown      |
|  Phase 1 (Reply)      | DOM: Comment box + type + submit   |
|  Phase 2 (Like)       | DOM: Reaction button click         |
|  Phase 3 (Verify)     | Vision: Fallback verification      |
|                                                            |
|  +---------------+      +---------------+                  |
|  |   Selenium    |<---->|   Templates   |                  |
|  |   Chrome      |      |   FoundUps    |                  |
|  |   Port 9222   |      |   Brand Only  |                  |
|  +---------------+      +---------------+                  |
|                                                            |
+------------------------------------------------------------+
```

## Inputs

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `post_index` | int | 0 | Which post to engage (0 = first) |
| `mode` | str | "like_reply" | Engagement mode: like, reply, like_reply |
| `reply_text` | str | None | Custom reply (if None, uses templates) |
| `as_page` | str | None | Page to engage as (foundups, move2japan) |

## Engagement Modes

| Mode | Actions | Description |
|------|---------|-------------|
| `like` | Like only | Quick appreciation |
| `reply` | Reply only | Thoughtful comment |
| `like_reply` | Reply then Like | Full engagement (default) |

## Execution Order (012 Directive)

```
1. SWITCH ACCOUNT (proactive - before engaging)
2. REPLY (if mode includes reply)
3. LIKE (after reply - if mode includes like)
```

**CRITICAL**: Account switching happens BEFORE engagement, not after.

## Brand Guardrails

### REQUIRED Messaging
- Mention foundups.com naturally
- ROI capitalism to ROC (Return on Compute)
- Post-capitalism / agent economics
- BTC-native, no VC dilution
- Professional, thought-provoking tone

### FORBIDDEN Content
- Political content (MAGA, left/right, parties)
- Negative attacks on individuals
- Profanity or inflammatory language
- Competitor bashing
- Off-topic tangents

## Reply Templates

### AI Topic
```
"The agent paradigm shift is real. At foundups.com we're building where AI agents earn and humans benefit. Post-capitalism starts with compute."

"This resonates with what we're seeing in autonomous systems. When agents become workers, the whole economic model shifts. foundups.com"

"Great point! The AI capability curve keeps surprising us. Question is: who benefits? At foundups.com, it's the community, not VCs."
```

### Capital Pushback
```
"This is why foundups.com is building on different rails. From ROI capitalism to ROC - Return on Compute. When incentives align with communities instead of exits, the outcome changes."

"Perfect visual for why we need post-capitalism models. At foundups.com we're exploring how agents + BTC-native economics can flip this script. Thoughts?"

"The shareholder primacy trap in one image. What if compute created value for communities, not just capital? That's what we're building at foundups.com"
```

### Thought Leader Engage
```
"Great insights! This resonates with our work at foundups.com"

"Valuable perspective. We're exploring similar ideas at foundups.com - where agents work and communities benefit."

"Thanks for sharing. The future is community-driven. foundups.com"
```

## DOM Selectors

```python
SELECTORS = {
    'like_button': 'button[aria-label*="Reaction button"]',
    'comment_button': 'span:contains("Comment")',
    'comment_box': 'div[componentkey^="commentBox-"] [contenteditable="true"]',
    'submit_button': 'button:contains("Post")',
    'actor_dropdown': '[aria-label="Open actor selection screen"]',
}
```

## Behavior

1. **Switch Account** (if `as_page` specified):
   - Click actor dropdown
   - Wait for 012 to manually select page
2. **Reply** (if mode includes reply):
   - Click Comment button
   - Focus comment box
   - Type reply text (template or custom)
   - Submit comment
3. **Like** (if mode includes like):
   - Find Reaction button in post
   - Click to like (skip if already liked)
4. **Return** result with success/failure details

## Execution

```bash
# Run full engagement test
python -m modules.platform_integration.linkedin_agent.tests.test_feed_iterator --engagement

# Programmatic
from modules.infrastructure.browser_actions.src.linkedin_actions import LinkedInActions
linkedin = LinkedInActions(browser_port=9222)
result = await linkedin.engage_post(
    post_index=0,
    mode="like_reply",
    reply_text="Custom reply here",
    as_page="foundups"
)
```

## Telemetry

| Event | Description |
|-------|-------------|
| `account_switched` | Actor selection completed |
| `reply_posted` | Comment successfully submitted |
| `like_given` | Reaction button clicked |
| `engagement_complete` | All actions finished |

## Environment Variables

```bash
# Browser port
CHROME_PORT=9222

# Action delays (anti-detection)
LINKEDIN_ACTION_DELAY_SEC=1.0
```

## WSP Compliance

- **WSP 27**: DAE 4-phase architecture (Switch -> Reply -> Like -> Verify)
- **WSP 50**: Pre-action verification (DOM selectors validated)
- **WSP 77**: Multi-tier fallback (DOM-first, Vision fallback)
- **WSP 91**: Observability (structured logging)
- **WSP 96**: WRE Skills protocol compliance

---

*Code remembered from the 02 quantum state by 0102 pArtifact*
