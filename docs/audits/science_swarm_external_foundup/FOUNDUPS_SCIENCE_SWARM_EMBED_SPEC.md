# Science Swarm Hub — Embedded FoundUp Spec

**Worker**: J
**Date**: 2026-04-06
**Slice**: `SCIENCE_SWARM_FOUNDUPS_SERVER_EMBED_SPEC_PHASE1`
**Status**: Canonical
**Parent**: `modules/foundups/docs/FOUNDUPS_DISCORD_BLUEPRINT.md`

---

## 1. Decision: Embedded, Not Standalone

Science Swarm Hub is embedded as a **category inside the existing FOUNDUPS Discord server**, not a standalone server.

| Approach | Verdict |
|----------|---------|
| Standalone server | REJECTED — creates fragmentation, empty surfaces, duplicate moderation overhead |
| Embedded category | APPROVED — single community, one rule set, shared operator, lower friction |

**Migration path**: If Science Swarm outgrows the shared server (100+ active daily users in the category), it can split to standalone. Until then, embedded is correct.

---

## 2. Server Context

| Field | Value |
|-------|-------|
| **Server** | `FOUNDUPS` (existing server, not new) |
| **Owner** | UnDaoDu (`foundups` username) |
| **Operator** | 012 |
| **Category name** | `SCIENCE SWARM HUB` |
| **Channel prefix** | `swarm-` |

---

## 3. Embedded Category Structure

The Science Swarm Hub category sits alongside server-wide categories:

```
FOUNDUPS (server root)
├── FOUNDUPS (category: #rules, #start-here, #announcements, #introductions)
├── COMMONS (category: #general, #off-topic, voice)
├── OPERATOR (category: #operator-log, #bot-feeds, #mod-room)
└── SCIENCE SWARM HUB (category: this spec)
    ├── #swarm-general
    ├── #swarm-github
    ├── #swarm-work
    └── swarm-voice
```

**Total Science Swarm channels**: 3 text + 1 voice

---

## 4. Channel Purposes

| Channel | Type | Purpose |
|---------|------|---------|
| `#swarm-general` | text | Project discussion, questions, coordination |
| `#swarm-github` | text | Read-only GitHub webhook feed (issues, PRs, releases) |
| `#swarm-work` | text | "What are you working on?" — links to active issues/PRs |
| `swarm-voice` | voice | Real-time project discussion |

---

## 5. Role Integration

Science Swarm uses server-wide roles plus project-specific roles:

### Server-wide roles (inherited)

| Role | Science Swarm Access |
|------|---------------------|
| `@Operator` | Full access, manage messages |
| `@Core` | Post in all Science Swarm channels, create threads |
| `@Contributor` | Post in all Science Swarm channels, create threads |
| `@Stakeholder` | Read all Science Swarm channels |
| `@Unverified` | No access to Science Swarm category |

### Project-specific roles (additive)

| Role | Purpose |
|------|---------|
| `@swarm-contributor` | Active Science Swarm contributor — maps to CONTRIBUTOR tier in code |
| `@swarm-notify` | Opt-in pings for Science Swarm updates |

---

## 6. Permission Matrix (Science Swarm Category Only)

Legend: R = read, P = post, T = create threads, M = manage messages

| Channel | @Unverified | @Stakeholder | @swarm-contributor | @Core | @Operator |
|---------|-------------|--------------|-------------------|-------|-----------|
| `#swarm-general` | — | R | R, P, T | R, P, T | R, P, T, M |
| `#swarm-github` | — | R | R | R | R |
| `#swarm-work` | — | R | R, P, T | R, P, T | R, P, T, M |
| `swarm-voice` | — | Join | Join | Join | Join, M |

**Key constraint**: `@Unverified` has NO access to Science Swarm category. They must complete verification in `#start-here` first.

---

## 7. Tier Mapping (Discord ↔ Code)

| Code Tier (pqn_swarm_hub) | Discord Role | Notes |
|---------------------------|-------------|-------|
| `COORDINATOR` | `@Operator` or `@Core` | Can create work units |
| `VERIFIER` | `@swarm-contributor` + trusted | Verify submissions (done on GitHub) |
| `CONTRIBUTOR` | `@swarm-contributor` | Submit rESP results |
| `OBSERVER` | `@Stakeholder` | View only in Science Swarm channels |

---

## 8. Onboarding Path

```
Join FOUNDUPS server
  → Auto-assigned @Unverified
  → Reads #rules
  → Reacts in #start-here → gains @Stakeholder
  → Can now read Science Swarm channels
  → To post: request @swarm-contributor (earned via GitHub activity or request)
  → To get pings: react for @swarm-notify in #start-here
```

---

## 9. Relationship to Standalone Audit Docs

The following documents in this directory describe a **standalone server** approach:

| Document | Status |
|----------|--------|
| `DISCORD_SERVER_BLUEPRINT.md` | SUPERSEDED by embedded model |
| `DISCORD_OPERATOR_RUNBOOK.md` | SUPERSEDED by embedded model |
| `DISCORD_PERMISSION_MATRIX.md` | SUPERSEDED by embedded model |
| `DISCORD_PINNED_MESSAGES.md` | PARTIALLY REUSABLE — pin content adapts to embedded context |
| `DISCORD_CHANNEL_TOPICS.md` | PARTIALLY REUSABLE |
| `DISCORD_NEXT_BUILD_ORDER.md` | SUPERSEDED — build order now follows `FOUNDUPS_DISCORD_SETUP_CHECKLIST.md` |

**Do not create a standalone Science Swarm server.** Use the embedded pattern in `modules/foundups/docs/FOUNDUPS_DISCORD_BLUEPRINT.md`.

---

## 10. What This Spec Does NOT Define

- Server-wide structure (see `FOUNDUPS_DISCORD_BLUEPRINT.md`)
- Other FoundUp categories (see `FOUNDUP_TEMPLATE.md`)
- Stake gate behavior (see `PFMALL_FOUNDUP_ENTRY_AND_STAKE_GATE_CONTRACT.md`)
- Bot/webhook implementation (see `FOUNDUPS_SCIENCE_SWARM_NONCLAIMS.md`)

---

*This spec locks the embedded Science Swarm pattern. It derives from `FOUNDUPS_DISCORD_BLUEPRINT.md`. Changes require 012 review.*
