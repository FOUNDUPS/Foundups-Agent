---
name: linkedin_engagement
description: Master LinkedIn activity router for full operations or scoped messages, connections, groups, feed, newsletters, publishing and continuity; retains the WRE bridge
version: 1.2.0
author: 0102
agents: [qwen]
dependencies: [linkedin_social_adapter, browser_actions, wre_core]
domain: social
intent_type: DECISION
promotion_state: prototype
pattern_fidelity_threshold: 0.85
owning_module: modules/platform_integration/linkedin_agent
required_assets:
  - modules/communication/moltbot_bridge/src/linkedin_social_adapter.py
  - modules/infrastructure/browser_actions/src/linkedin_actions.py
executor: executor.py
category: workflow
evals: []
---
# LinkedIn Master Activity Skill (Existing WRE Bridge)

For every invocation, read [master activity routing](../../docs/LINKEDIN_ACTIVITY_ROUTING.md), select only the requested activities and read their child SKILLz.md files. “Run LinkedIn” selects the full cycle; “check messages” selects inbox only. Finish with continuity. This is instruction-level routing; the existing executor remains an action bridge, not an implementation of every child workflow.

Before selecting an action, read [LinkedIn review workflow](../../docs/LINKEDIN_REVIEW_WORKFLOW.md). The current full cycle starts with connection triage, then messages (Focused + Other), notifications, group queues and relevant feed; urgent commitments may override order. Route membership to [linkedin_group_moderation](../linkedin_group_moderation/SKILLz.md) and Good/Bad/Ugly automation discussions to [openclaw_group_news](../openclaw_group_news/SKILLz.md). Do not instantiate a competing LinkedIn orchestrator.

Read/research/draft within scope. Every send, post, like, connection, moderation or access change requires exact human authorization and verified results. APS ranks work; it does not grant authority. Existing live executor routes are not certified safe by this documentation update.

Execute LinkedIn engagement actions through WRE's ReAct reasoning loop, enabling
self-improvement via A/B testing and outcome-driven skill evolution.

## Purpose

Bridge the existing `linkedin_social_adapter` (13 actions) into the WRE skill
execution pipeline so that:

- Skills are discoverable by `WRESkillsDiscovery`
- Execution flows through `execute_skill()` → ReAct loop → adapter
- Outcomes feed PatternMemory for learning and evolution
- `evolve_skill()` can generate improved strategies

## Supported Actions

| Action               | Description                          |
| -------------------- | ------------------------------------ |
| `read_feed`          | Read and extract LinkedIn feed posts |
| `like_post`          | Like a specific post                 |
| `reply_post`         | Reply to a post (dry_run default)    |
| `like_reply`         | Like and reply combo                 |
| `scam_reply`         | Anti-scam callout reply              |
| `scam_scan`          | Scan for suspicious posts            |
| `scam_scan_reply`    | Scan + auto-reply to scams           |
| `engagement_session` | Full engagement cycle                |
| `connect`            | Send connection requests             |
| `digital_twin`       | Digital Twin engagement mode         |
| `group_post`         | Post to LinkedIn group               |

## Execution Contract

Preflight the entire call chain before using the steps below. Known audit gap: nested `dry_run=false` can survive wrapper defaults, and some direct action routes do not enforce dry-run. Do not invoke a live route for a review-only task or treat a simulation as a verified send. In Work, use the advertised browser skill for browser interaction, not repository browser/session adapters.

1. Parse task dict for `action` and `params` keys.
2. Delegate to `execute_linkedin_action(action, params)` from adapter.
3. Return structured result for PatternMemory storage.
4. Default to `dry_run=true` unless explicitly overridden.

## WSP Chain

- `WSP 42`: LinkedIn platform integration
- `WSP 50`: Pre-action verification
- `WSP 77`: Agent coordination
- `WSP 95`: Wardrobe skills
- `WSP 96`: WRE skill execution pattern
