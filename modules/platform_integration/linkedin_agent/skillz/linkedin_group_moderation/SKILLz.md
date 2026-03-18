---
name: linkedin_group_moderation
description: LinkedIn OpenClaw Group moderation - membership triage, post moderation, profile intel
version: 1.0.0
author: 0102
agents: [qwen, selenium]
dependencies: [browser_actions, anti_detection_poster]
domain: platform_integration
intent_type: MODERATION
promotion_state: prototype
rate_limit: 50_per_session
linkedin_group: https://www.linkedin.com/groups/6729915/
linkedin_admin: https://www.linkedin.com/groups/6729915/manage/membership/requested/
category: workflow
evals: []
---
# LinkedIn Group Moderation DAE

**Purpose**: Autonomous moderation of OpenClaw LinkedIn Group - membership triage, post moderation, profile intelligence.

**Position in Flow**: This skill runs as admin operations BEFORE content posting.

---

## State

| Key | Value |
|-----|-------|
| Operator | 012 (UnDaoDu Michael J Trout) |
| Agent | 0102 (012's digital twin state) |
| Signature | `— 0102 ` |
| Group | linkedin.com/groups/6729915/ |
| Admin | linkedin.com/groups/6729915/manage/membership/requested/ |

## Resources

- foundups.com
- foundups.com/litepaper.html
- linkedin.com/pulse/return-compute-tokenization-framework-foundups-whdce/
- github.com/foundups

---

## FLOW 1: Moderate Posts

**Trigger**: Navigate to group feed

**Decision Tree**:
```
For each post:
  IF marketing/promo/clickbait → DELETE (screenshot first)
  ELIF engagement-farming → COMMENT (call out)
  ELSE → KEEP (genuine content)
```

**Actions**:
1. Navigate group feed
2. For each post: DELETE / COMMENT / KEEP decision
3. Screenshot before delete (evidence)
4. Report actions to 012

---

## FLOW 2: Process Membership Requests

### Step 1 — Read Queue

Navigate admin page → extract from Results list (depth 5+):
- Name
- Headline
- Degree (1st/2nd/3rd)
- Photo status (has photo / default silhouette)
- Profile URL

### Step 2 — Triage Decision

| Condition | Action |
|-----------|--------|
| No photo (default gray silhouette) | **DENY, no message** |
| Photo + CxO/VP/Founder/Head of | **APPROVE + MESSAGE + CONNECT** |
| Photo + other title | **APPROVE + MESSAGE** |
| Animated/cartoon avatar | Counts as "has photo" |

### Step 3 — Build Personalized Message

**Language Detection**: From profile location/headline. Write in detected language.

**8-Point Message Structure**:

1. **Personal ROI threat** — Name their job, state how agents replace that paycheck specifically
2. **ROC paper** — `linkedin.com/pulse/return-compute-tokenization-framework-foundups-whdce/` — framed as research, not promotion
3. **FoundUps case study** — `foundups.com` — framed as learning. For high-value: mention PWA mesh, agent-driven app store, autonomous solution
4. **Security** — "Sandbox your OpenClaw agents." One line.
5. **Poker table** — "Group is quiet. Everyone's at the poker table reading each other's hand — nobody wants to sneeze first. Expect watchers, not chatter."
6. **Spam check** — "Here to learn or sell? We delete marketing posts."
7. **Signature** — `— 0102 `
8. **PS** — Apple employees only: "First video ever made about Siri was done by UnDaoDu, 8 months before Siri's acquisition."

### Step 4 — Execute

```
Click "..." → Message → paste message → Send
→ Approve/Deny based on triage
→ (CxO only: also Connect)
→ Next request
```

### Draft Mode (Browser Blocked)

If browser extension conflict blocks execution:
- Read profiles
- Output messages as text
- 012 pastes manually

---

## FLOW 3: Write Article

1. Parallel tab research via Google search
2. Navigate group → "Start a post"
3. `type` action (not form_input — composer is a DIV)
4. `key: Return Return` for paragraph breaks
5. **DO NOT post** — 012 posts and adds signature

---

## FLOW 4: Profile Intel

**Trigger**: Navigate to `/in/{username}/`

**Extract**:
- Headline
- About
- Location
- Company
- Education

**Determine**:
- Why are they joining?
- What's their play?
- What paycheck is threatened?

---

## Browser Recovery

Extension conflict on LinkedIn admin pages is persistent. Fixes in order:

1. Navigate to google.com → wait 3s → navigate back
2. New tab → navigate fresh
3. Close all LinkedIn messaging overlays from feed page first
4. If all blocked → draft mode (0102 drafts, 012 executes)

---

## Session Resume Protocol

1. Receive flow activation from 012
2. Navigate admin page → count queue → read list
3. Check linkedin.com/messaging/ for already-sent messages
4. Resume from first unprocessed request

---

## CLI Integration

Access via main.py menu:
```
Option 4: Social Media DAE (012 Digital Twin)
  └── Option 4: LinkedIn Group Moderation DAE
      ├── 1. Process Membership Queue
      ├── 2. Moderate Posts
      ├── 3. Profile Intel
      └── 0. Back
```

---

## WSP Compliance

- **WSP 42**: LinkedIn platform integration standards
- **WSP 50**: Pre-action verification (check queue state)
- **WSP 77**: Agent coordination
- **WSP 78**: All actions logged to `agents_social_group_actions`
- **WSP 96**: WRE skill execution pattern
- **WSP 97**: System execution prompting (HoloIndex → Research → Hard Think → First Principles → Build → Follow WSP)

---

## Executor Interface

```python
from modules.platform_integration.linkedin_agent.skillz.linkedin_group_moderation import (
    read_membership_queue,
    triage_member,
    build_welcome_message,
    moderate_post,
    extract_profile_intel
)

# Read queue
queue = read_membership_queue(max_depth=10)

# Triage and process
for member in queue:
    decision = triage_member(member)  # APPROVE/DENY/APPROVE_CONNECT
    if decision != 'DENY':
        message = build_welcome_message(member, decision)
        # Execute or draft based on browser state
```

---

## Rate Limiting

| Constraint | Value | Reason |
|------------|-------|--------|
| Messages/session | 50 | LinkedIn limits |
| Min interval | 3s | Human-like |
| Connect/day | 20 | LinkedIn connection limits |

---

## Changelog

### v1.0.0 (2026-03-15)
- Initial skill creation from 012 operational flows
- 4 flows: Moderate Posts, Process Membership, Write Article, Profile Intel
- 8-point personalized message template
- Triage decision tree
- Browser recovery protocol
- Session resume protocol

---

**Skill Status**: PROTOTYPE
