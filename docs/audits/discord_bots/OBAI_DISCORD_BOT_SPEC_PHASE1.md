# OBAI Discord Bot Spec — Phase 1

Worker: Z
Date: 2026-04-07
Slice: OBAI_DISCORD_BOT_SPEC_PHASE1
Status: Canonical
Repo: Foundups-Agent

## 1. Identity

OBAI is a non-admin community helper bot for the FOUNDUPS Discord server.

| Field | Value |
|-------|-------|
| Bot name | OBAI |
| App ID | 1127122752776699915 |
| Role | Helper / explainer / observer / structured responder |
| Server | FOUNDUPS (412646632992014336) |
| Admin | NO — never |
| Moderation | NO — never |

OBAI is NOT 0102. They are separate identities, separate tokens, separate runtimes.

## 2. Architecture Decision

**RECOMMEND: STANDALONE_OBAI_GATEWAY_BOT**

OBAI will be a new standalone Discord gateway bot module, not a sub-runtime
or sibling of moltbot_bridge.

### Justification

| Factor | Verdict |
|--------|---------|
| Codebase fit | moltbot_bridge is 0102's runtime. Its config says "You are 0102." Its INTERFACE.md describes OpenClawDAE. No OBAI identity exists in it. |
| Operational simplicity | Separate process = separate failure domain. OBAI crash does not affect 0102. |
| Permission safety | 0102 runs with ADMINISTRATOR. OBAI must never touch admin APIs. Separate process enforces this at the OS level. |
| Future extensibility | OBAI can evolve its own interaction patterns without touching 0102's control plane. |
| Identity separation | Dual-bot spec requires distinct identities. Shared runtime risks identity bleed. |

### Proposed Module Path

```
modules/communication/obai_discord_bot/
├── README.md
├── INTERFACE.md
├── config/
│   └── obai_config.json
├── src/
│   └── obai_gateway.py       # Discord gateway client (discord.py or raw)
│   └── obai_thread_handler.py # Thread participation logic
│   └── obai_commands.py       # Slash command registration
│   └── obai_formatter.py      # Structured response formatting
└── docs/
    └── OBAI_DISCORD_BOT_SPEC_PHASE1.md  (symlink or copy)
```

### Environment

```
DISCORD_BOT_TOKEN_OBAI=<token>    # OBAI-specific, NOT shared with 0102
OBAI_GUILD_ID=412646632992014336
OBAI_LOG_LEVEL=info
```

## 3. Gateway Connection

OBAI connects to Discord via the Gateway API (WebSocket), not webhooks.

| Setting | Value |
|---------|-------|
| Library | discord.py (recommended) or raw gateway |
| Intents | Guilds, GuildMessages, MessageContent, GuildMessageReactions |
| Privileged intents | Message Content (enabled in Developer Portal) |
| Sharding | Not required (single small server) |
| Reconnect | Automatic with exponential backoff |

## 4. Allowed Channels

| Channel | Can read | Can post | Can create threads | Notes |
|---------|----------|----------|--------------------|-------|
| #swarm-general | YES | YES | YES | Primary discussion surface |
| #swarm-work | YES | NO (main) | YES (threads) | Main channel locked; OBAI participates in threads only |
| Work threads | YES | YES | — | Primary interaction surface |
| #swarm-github | YES | NO | NO | Read-only feed channel |
| #start-here | NO | NO | NO | Server-wide onboarding, not OBAI's scope |
| Operator channels | NO | NO | NO | Admin-only, OBAI excluded |

## 5. Interaction Patterns

### Trigger Model: Passive Unless Invoked

OBAI does NOT speak unless spoken to.

| Trigger | Behavior |
|---------|----------|
| @OBAI mention in message | Reply in same channel/thread |
| @OBAI mention in thread | Reply in thread |
| `/obai` slash command | Structured response |
| Unprompted posting | NEVER — OBAI does not initiate |
| Scheduled summaries | NEVER — non-claim preserved |
| DMs | NEVER — OBAI does not accept or send DMs |

### Slash Commands (Phase 1)

| Command | Description |
|---------|-------------|
| `/obai help` | List available commands |
| `/obai explain <topic>` | Explain a Science Swarm concept |
| `/obai link <issue_number>` | Link to a GitHub issue (read-only) |
| `/obai status` | Report OBAI's own status (uptime, version) |

## 6. Response Format

All OBAI responses follow this structure:

```
[OBAI] <response body>

---
<source links if applicable>
<escalation note if applicable>
```

### Rules

- Identity prefix: Always `[OBAI]` at the start
- Length: Concise. Target 1-3 short paragraphs in threads. No walls of text.
- Evidence: Link to GitHub issues, PRs, docs when referencing them
- Escalation: If a question exceeds OBAI's scope, say so explicitly and direct to operator or #swarm-general
- Formatting: Use Discord markdown (bold, code blocks, links). No custom embeds in Phase 1.
- Tone: Helpful, neutral, factual. Not chatty, not authoritative.

## 7. Non-Claims (What OBAI Does NOT Do)

| Claim | Truth |
|-------|-------|
| "OBAI verifies contributions" | NO — verification is via Python API |
| "OBAI assigns roles" | NO — role management is operator-only |
| "OBAI scores contributions" | NO — CABR/3V not wired to Discord |
| "OBAI creates GitHub issues" | NO — OBAI is read-only for GitHub |
| "OBAI moderates channels" | NO — no moderation powers |
| "OBAI manages server settings" | NO — no admin powers |
| "OBAI syncs data to GitHub" | NO — one-way GitHub->Discord only |
| "OBAI handles wallet/stake verification" | NO — no wallet integration |
| "OBAI sends scheduled digests" | NO — passive unless invoked |
| "OBAI is 0102" | NO — separate identity, separate token, separate runtime |

These non-claims align with FOUNDUPS_SCIENCE_SWARM_NONCLAIMS.md.

## 8. Relationship to 0102

| Dimension | 0102 | OBAI |
|-----------|------|------|
| Role | Admin / operator / infrastructure | Helper / explainer / observer |
| Permissions | ADMINISTRATOR | Limited helper set (311452617792) |
| Runtime | moltbot_bridge / OpenClawDAE | obai_discord_bot (new standalone) |
| Token env var | DISCORD_BOT_TOKEN_0102 | DISCORD_BOT_TOKEN_OBAI |
| Can kick/ban | YES | NO |
| Can manage roles | YES | NO |
| Can modify channels | YES | NO |
| Can post anywhere | YES | Only allowed channels |
| Identity prefix | [0102] | [OBAI] |

OBAI may escalate to 0102 via a future internal channel. In Phase 1, escalation means: OBAI tells the user to contact the operator.

## 9. Update to Non-Claims Document

The following non-claim in FOUNDUPS_SCIENCE_SWARM_NONCLAIMS.md is now partially outdated:

> "No custom webhook configured" -> NOW PARTIALLY TRUE

A GitHub webhook from science-swarm-hub to #swarm-github is now live (configured 2026-04-07, events: pushes, pull_requests, issues, issue_comments). The NONCLAIMS doc should be updated to reflect this. However, this webhook is ops wiring, not canonical architecture — it should be documented as operational tooling, not as a bot feature.

## 10. Acceptance Checklist

- [x] OBAI role is explicit (helper/explainer/observer)
- [x] Permission boundary is explicit (no admin, no mod, no roles)
- [x] Allowed channel/thread behavior is explicit (table in S4)
- [x] Non-claims are explicit (table in S7)
- [x] Future bridge points are explicit (see OBAI_FUTURE_BRIDGE_POINTS.md)
- [x] No code changes
- [x] Architecture recommendation justified
