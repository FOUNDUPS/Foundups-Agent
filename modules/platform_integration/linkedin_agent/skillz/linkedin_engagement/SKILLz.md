---
name: linkedin_engagement
description: WRE-bridged LinkedIn engagement skill wrapping the full linkedin_social_adapter action set
version: 1.0.0
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
# LinkedIn Engagement Skill (WRE Bridge)

Execute LinkedIn engagement actions through WRE's ReAct reasoning loop, enabling
self-improvement via A/B testing and outcome-driven skill evolution.

## Purpose

Bridge the proven `linkedin_social_adapter` (13 actions) into the WRE skill
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
