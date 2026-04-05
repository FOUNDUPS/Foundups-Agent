# FoundUps Discord Blueprint — Embedded Server

**Version**: 1.0.0
**Date**: 2026-04-05
**Status**: Canonical
**Owner**: 012
**Parent**: `FOUNDUPS_MASTER_ARCHITECTURE.md`

---

## 1. Server Identity

| Field | Value |
|-------|-------|
| **Server name** | `FOUNDUPS` (existing server) |
| **Owner account** | UnDaoDu (username: `foundups`) |
| **Model** | One server, per-FoundUp categories |
| **Community features** | OFF |

**Why embedded, not standalone**: Fewer empty surfaces, less fragmentation, one community, lower operator overhead, easier moderation. Future migration to standalone is trivial if a FoundUp outgrows the server.

---

## 2. Server Layout

```
════════════════════════════════════════
FOUNDUPS
════════════════════════════════════════
  #rules                    read-only. What FOUNDUPS is, code of conduct,
                            "GitHub is canonical, Discord is coordination."
  #start-here               Onboarding. Reaction roles. Links to pfMALL,
                            FoundUp Welcome pages, GitHub org.
  #announcements            read-only. Server-wide updates from operator.
  #introductions            New members (human + agent) say hello.

════════════════════════════════════════
COMMONS
════════════════════════════════════════
  #general                  Open discussion. Anything FOUNDUPS-related.
  #off-topic                Everything else.
  voice                     One voice channel.

════════════════════════════════════════
OPERATOR
════════════════════════════════════════
  #operator-log             read-only, public. Operator decisions, visible to all.
  #bot-feeds                read-only. Consolidated bot/webhook output.
  #mod-room                 private. Operator-only. Bot commands, moderation.

════════════════════════════════════════
SCIENCE SWARM HUB            ← first FoundUp
════════════════════════════════════════
  #swarm-general            Project discussion.
  #swarm-github             read-only. Webhook feed from GitHub repo.
  #swarm-work               "What are you working on?" Links to issues/PRs.
  swarm-voice               Project voice channel.

════════════════════════════════════════
[NEXT FOUNDUP]               ← template, not created yet
════════════════════════════════════════
  #[prefix]-general
  #[prefix]-github
  #[prefix]-work
  [prefix]-voice
```

**Total day-1 channels**: 14 (11 text + 3 voice)

**Per-FoundUp pattern**: 3 text + 1 voice. Prefix = short project name (e.g., `swarm-`). Keeps sidebar scannable at 5+ FoundUps.

---

## 3. Role Hierarchy

### Server-wide roles (top to bottom)

| Role | Color | Purpose | Who |
|------|-------|---------|-----|
| `@Operator` | Red | Full admin | 012 only |
| `@Core` | Gold | Long-term trusted contributors | Manual assignment by 012 |
| `@Contributor` | Green | Active contributor to any FoundUp | Proven by GitHub activity |
| `@Member` | Blue | Verified, onboarded | Completed #start-here flow |
| `@Unverified` | Grey | Just joined | Auto-assigned on join |

### Mirror roles (optional, synced from PWA when bridge exists)

| Role | Color | Purpose |
|------|-------|---------|
| `@Stakeholder` | Purple | Reflects wallet-verified status from PWA |

**@Stakeholder is cosmetic/informational only.** It grants no Discord-exclusive access. The PWA is authoritative for stake status. If someone loses their stake, PWA revokes interior access and the Discord role updates to match.

### Per-FoundUp roles

| Role | Purpose |
|------|---------|
| `@swarm-contributor` | Active on Science Swarm Hub specifically |
| `@swarm-notify` | Opt-in pings for Science Swarm updates |

---

## 4. Role-to-Tier Mapping

| Entitlement Tier | Where Determined | Discord Role |
|------------------|-----------------|--------------|
| Guest | pfMALL (no account) | (not on Discord) |
| Visitor | FoundUp Welcome PWA | (not on Discord) |
| Community | Joins Discord + verifies | @Member → @Contributor → @Core |
| Stakeholder | PWA wallet gate | @Stakeholder (mirror only) |
| Operator | 012 | @Operator |

---

## 5. Permission Matrix

### FOUNDUPS category

| Channel | @Unverified | @Member | @Contributor | @Core | @Operator |
|---------|-------------|---------|-------------|-------|-----------|
| `#rules` | R | R | R | R | R, P |
| `#start-here` | R | R | R | R | R, P |
| `#announcements` | R | R | R | R | R, P |
| `#introductions` | — | R, P | R, P | R, P | R, P, M |

### COMMONS category

| Channel | @Unverified | @Member | @Contributor | @Core | @Operator |
|---------|-------------|---------|-------------|-------|-----------|
| `#general` | — | R, P | R, P | R, P | R, P, M |
| `#off-topic` | — | R, P | R, P | R, P | R, P, M |
| `voice` | — | Join | Join | Join | Join, M |

### OPERATOR category

| Channel | @Unverified | @Member | @Contributor | @Core | @Operator |
|---------|-------------|---------|-------------|-------|-----------|
| `#operator-log` | R | R | R | R | R, P |
| `#bot-feeds` | — | R | R | R | R |
| `#mod-room` | — | — | — | — | R, P, M |

### SCIENCE SWARM HUB category

| Channel | @Unverified | @Member | @swarm-contributor | @Core | @Operator |
|---------|-------------|---------|-------------------|-------|-----------|
| `#swarm-general` | — | R | R, P, T | R, P, T | R, P, T, M |
| `#swarm-github` | — | R | R | R | R |
| `#swarm-work` | — | R | R, P, T | R, P, T | R, P, T, M |
| `swarm-voice` | — | Join | Join | Join | Join, M |

Legend: R = read, P = post, T = create threads, M = manage messages

### Implementation notes

**@Unverified sees**: `#rules`, `#start-here`, `#announcements`, `#operator-log` only. All read-only. This gives them enough to orient and verify without noise.

**Verification flow**: @Unverified completes reaction-role in `#start-here` → gains @Member → sees all public channels.

---

## 6. Onboarding Flow

```
Join server
  → Auto-assigned @Unverified
  → Sees only: #rules, #start-here, #announcements, #operator-log
  → Reads #rules
  → Goes to #start-here
  → Reacts to role-assignment message (picks FoundUp interests)
  → Gains @Member + optional @swarm-notify
  → Can now see and post in COMMONS and read FoundUp categories
  → To post in a FoundUp category: request @swarm-contributor (or earn it via GitHub activity)
```

---

## 7. Automation

### Automated (set up once)

| What | Tool | Channel |
|------|------|---------|
| Verification on join | YAGPDB reaction-to-role | #start-here |
| FoundUp role self-assign | YAGPDB reaction roles | #start-here |
| GitHub → Discord notifications | Native Discord webhook | #swarm-github |
| Spam/raid protection | YAGPDB automod | server-wide |
| New member greeting | YAGPDB auto-response | #introductions |

### Manual (operator judgment)

| What | Why |
|------|-----|
| @Member → @Contributor promotion | Requires seeing GitHub activity |
| @Contributor → @Core promotion | Trust decision |
| @Stakeholder sync | Until PWA↔Discord bridge exists |
| Adding a new FoundUp category | Structural decision, 15-min setup |
| Announcements | Operator voice |
| Moderation escalation | Bans, disputes, edge cases |

### Bot policy

**YAGPDB.xyz** — single bot for moderation, auto-roles, reaction roles, custom commands, logging. Remove all other bots from current server. Re-add any as specific needs emerge.

### GitHub webhook setup (per FoundUp)

In GitHub repo Settings → Webhooks → Add Discord webhook URL for `#[prefix]-github`. Notify on: issues opened/closed, PRs opened/merged, releases published. Zero ongoing maintenance.

---

## 8. Adding a New FoundUp

When a new FoundUp is ready for Community layer:

1. Create category: `[FOUNDUP NAME]` (UPPER CASE)
2. Create channels: `#[prefix]-general`, `#[prefix]-github`, `#[prefix]-work`
3. Create voice: `[prefix]-voice`
4. Create roles: `@[prefix]-contributor`, `@[prefix]-notify`
5. Set permission overrides per the matrix pattern above
6. Add GitHub webhook to `#[prefix]-github`
7. Add reaction role option in `#start-here`
8. Pin project overview in `#[prefix]-general`

**Time**: ~15 minutes per FoundUp.

---

## 9. Pinned Messages

### #rules

```
FOUNDUPS Server Rules

1. GitHub is canonical — all code, issues, and PRs live on GitHub under the FOUNDUPS org.
2. Discord is coordination and discussion — not the action surface.
3. Be direct, be honest. State what you know and what you don't.
4. Human and AI contributors both welcome. Contributions are measured by work.
5. Each FoundUp has its own category. Stay on topic in project channels.
6. The real stake gate is in the FoundUp PWA, not in Discord. Discord roles reflect status, they don't determine it.
```

### #start-here

```
Welcome to FOUNDUPS.

This server is the community layer for all FoundUp projects.

Step 1: Read #rules
Step 2: React below to get your @Member role and unlock channels
Step 3: Pick which FoundUps interest you (react for notifications)
Step 4: Introduce yourself in #introductions
Step 5: Find work — check a FoundUp's #[prefix]-work channel or its GitHub repo

Current FoundUps:
🔬 Science Swarm Hub — Physics research (PQN)
   GitHub: github.com/FOUNDUPS/science-swarm-hub

React with ✅ to verify → gain @Member
React with 🔬 to follow → gain @swarm-notify
```

### #swarm-general

```
Science Swarm Hub — Coordinated physics research

Repository: github.com/FOUNDUPS/science-swarm-hub
Package: pqn_swarm_hub v0.12.0
Python 3.12+, stdlib only, 108 tests
Install from source: git clone + pip install -e . (no PyPI yet)

What this project does:
- Work unit registration for PQN research
- Result submission and verification
- Contribution measurement
- Coherence >= 0.618 for auto-accept

How to contribute: Read CONTRIBUTING.md in the repo.
```

### #operator-log

```
This channel is a public log of operator decisions.

Why it's public: transparency. You can see what 012 decides and why.
You cannot post here — it's read-only for everyone except the operator.
```

---

## 10. Non-Claims

- No stake gate implementation exists today
- No sentinel agent exists today
- @Stakeholder role is planned, not active
- YAGPDB is recommended, not yet installed
- GitHub webhooks are recommended, not yet configured
- Current server may have existing channels/bots to clean up first

---

## 11. Migration from Current Server

The existing FOUNDUPS server needs to be restructured:

1. Audit current categories, channels, roles, bots
2. Archive or delete channels that don't fit the new layout
3. Remove excess bots (keep only YAGPDB)
4. Create new category/channel structure per this blueprint
5. Set up permissions per the matrix
6. Post and pin messages
7. Create invite link
8. Smoke test with a second account

See: `FOUNDUPS_DISCORD_SETUP_CHECKLIST.md` for step-by-step execution.

---

*This blueprint is the canonical Discord server spec. It derives from FOUNDUPS_MASTER_ARCHITECTURE.md. Changes require 012 review.*
