---
name: linkedin_agentic_reply
description: Agentic LinkedIn reply wardrobe for selected-post reading, model-routed drafting, and guarded posting
version: 1.0.0
author: 0102
agents: [qwen, gemma]
dependencies: [linkedin_actions, moltbot_bridge, wre_core, ai_gateway]
domain: social
intent_type: DECISION
promotion_state: prototype
pattern_fidelity_threshold: 0.9
category: workflow
evals: []
---
# LinkedIn Agentic Reply Skill

Execute agentic LinkedIn reply flows with OpenClaw/WSP controls.

## Purpose

- Read the visible or indexed LinkedIn post before replying.
- Draft as `0102` when requested.
- Prefer the active external OpenClaw model target when available.
- Fall back to digital twin / wardrobe logic when external drafting is unavailable.
- Keep dry-run as the default unless explicitly disabled.

## Inputs

```python
{
  "action": "reply_post|like_reply|scam_reply|scam_scan_reply",
  "post_index": int,
  "post_context": str,
  "author": str,
  "agent_identity": "0102",
  "use_selected_post": bool,
  "read_first": bool,
  "dry_run": bool,
}
```

## Execution Contract

1. Resolve the target LinkedIn post from DOM if `read_first` or `use_selected_post`.
2. Draft the reply using the preferred external OpenClaw model when configured.
3. Fall back to digital twin / wardrobe generation if external drafting is unavailable.
4. Return structured output with draft metadata.
5. Only post when `dry_run=false`.

## WSP Chain

- `WSP 42`: LinkedIn platform integration
- `WSP 46`: OpenClaw conversation bridge
- `WSP 50`: Pre-action verification
- `WSP 77`: Agent coordination
- `WSP 95`: Wardrobe skills
- `WSP 96`: WRE skill execution pattern
