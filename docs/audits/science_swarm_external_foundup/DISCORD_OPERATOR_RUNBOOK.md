# Science Swarm Hub — Discord Operator Runbook

**Worker**: I
**Date**: 2026-04-05
**Slice**: `SCIENCE_SWARM_DISCORD_OPERATOR_RUNBOOK_PHASE1`
**Operator**: 012
**Status**: Manual setup — no bot, no webhook, no automation

---

## 1. Document Set

This runbook references five companion documents. Read them in order:

| # | Document | Purpose |
|---|----------|---------|
| 1 | `DISCORD_SERVER_BLUEPRINT.md` | Server identity, categories, channels, settings |
| 2 | `DISCORD_PERMISSION_MATRIX.md` | Roles, permissions, channel overrides |
| 3 | `DISCORD_CHANNEL_TOPICS.md` | Copy-paste topic text for each channel |
| 4 | `DISCORD_PINNED_MESSAGES.md` | Copy-paste pinned messages for each channel |
| 5 | `012_DISCORD_SETUP_CHECKLIST.md` | Step-by-step execution checklist |

**Source of truth**: `DISCORD_SERVER_BLUEPRINT.md` defines all structure. Other docs derive from it.

---

## 2. Prerequisites

Before starting:

- [ ] Discord account (012's personal or a dedicated admin account)
- [ ] GitHub repo live at `github.com/FOUNDUPS/science-swarm-hub`
- [ ] `CONTRIBUTING.md` merged in the repo (contributor guide)
- [ ] `docs/seed_issues/` populated with at least 1 seed issue
- [ ] Server icon ready (FoundUps logo or placeholder image, 512x512 minimum)

---

## 3. Server Creation

1. Open Discord → "Add a Server" → "Create My Own" → "For me and my friends"
2. Server name: `Science Swarm Hub`
3. Upload server icon
4. Open Server Settings:
   - **Overview**: Set description to "Coordinated physics research — work registry, verification, contribution measurement"
   - **Safety Setup / Verification Level**: Low (email required)
   - **Default Notification Settings**: Only @mentions
   - **Community**: Leave OFF (do not enable Community features)
   - **System Messages Channel**: Will point to `#welcome` after channel creation

---

## 4. Role Creation

Create roles in this order (top to bottom in Discord role list):

| Order | Role | Color | Permissions |
|-------|------|-------|-------------|
| 1 | `@admin` | Red (#ED4245) | Administrator = ON |
| 2 | `@moderator` | Orange (#E67E22) | Manage Messages, Manage Threads, Kick Members, Timeout Members |
| 3 | `@contributor` | Green (#2ECC71) | No special server-wide permissions (channel overrides grant posting) |
| 4 | `@everyone` | Default | View Channels = ON, Send Messages = ON (overridden per channel) |

Assign `@admin` and `@moderator` to 012's account.

---

## 5. Category and Channel Creation

Create categories and channels in this exact order:

### Category: START HERE

| Channel | Topic (from CHANNEL_TOPICS.md) |
|---------|-------------------------------|
| `#welcome` | Copy from CHANNEL_TOPICS.md → #welcome |
| `#rules` | Copy from CHANNEL_TOPICS.md → #rules |
| `#introductions` | Copy from CHANNEL_TOPICS.md → #introductions |

### Category: RESEARCH

| Channel | Topic |
|---------|-------|
| `#work-units` | Copy from CHANNEL_TOPICS.md → #work-units |
| `#submissions` | Copy from CHANNEL_TOPICS.md → #submissions |
| `#verification` | Copy from CHANNEL_TOPICS.md → #verification |
| `#results` | Copy from CHANNEL_TOPICS.md → #results |

### Category: DEVELOPMENT

| Channel | Topic |
|---------|-------|
| `#dev-general` | Copy from CHANNEL_TOPICS.md → #dev-general |
| `#issues` | Copy from CHANNEL_TOPICS.md → #issues |
| `#releases` | Copy from CHANNEL_TOPICS.md → #releases |

### Category: META

| Channel | Topic |
|---------|-------|
| `#feedback` | Copy from CHANNEL_TOPICS.md → #feedback |
| `#off-topic` | Copy from CHANNEL_TOPICS.md → #off-topic |

**After creating channels**: Set System Messages Channel to `#welcome` in Server Settings → Overview.

---

## 6. Permission Overrides

Apply these channel-level overrides. Reference: `DISCORD_PERMISSION_MATRIX.md` → Implementation Notes.

### Read-only channels (`#welcome`, `#rules`, `#releases`)

For each channel:
1. Edit Channel → Permissions
2. `@everyone` → Send Messages = **Deny**
3. `@admin` → Send Messages = **Allow**

### Research + Dev channels (`#work-units`, `#submissions`, `#verification`, `#results`, `#dev-general`, `#issues`)

For each channel:
1. Edit Channel → Permissions
2. `@everyone` → Send Messages = **Deny**
3. `@contributor` → Send Messages = **Allow**, Create Public Threads = **Allow**
4. `@moderator` inherits from `@contributor` plus Manage Messages (from role)

### Open channels (`#introductions`, `#feedback`, `#off-topic`)

No overrides needed. `@everyone` default permissions allow posting.

---

## 7. Pinned Messages

Open each channel listed in `DISCORD_PINNED_MESSAGES.md` and:

1. Post the message text (copy from the doc)
2. Pin the message
3. Delete the "X pinned a message" system notification (optional, keeps channel clean)

Channels that need pins (10 of 12):

| Channel | Number of pins |
|---------|---------------|
| `#welcome` | 2 (orientation + what's not live) |
| `#rules` | 1 |
| `#introductions` | 1 |
| `#work-units` | 1 |
| `#submissions` | 1 |
| `#verification` | 1 |
| `#dev-general` | 1 |
| `#issues` | 1 |
| `#releases` | 1 |
| `#feedback` | 1 |

No pins: `#results`, `#off-topic`

---

## 8. Invite Link

Create a permanent invite link:

1. Server Settings → Invites → Create Invite
2. Channel: `#welcome`
3. Expiration: Never
4. Max uses: No limit
5. Copy the link

Store this link — it goes in the GitHub repo README and CONTRIBUTING.md when ready.

---

## 9. Smoke Test

**Scenario**: A new contributor joins, orients, finds work, and reaches GitHub.

### Setup
- Use a second Discord account (alt account, or ask a trusted person)
- Do NOT assign any roles to this account — it joins as `@everyone`

### Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Join via invite link | Lands in server, sees all categories and channels |
| 2 | Read `#welcome` | Sees pinned orientation message and "what's not live" status |
| 3 | Read `#rules` | Sees pinned rules including GitHub-canonical and no-PyPI notes |
| 4 | Post in `#introductions` | Message sends successfully (open channel) |
| 5 | Try to post in `#work-units` | **BLOCKED** — `@everyone` cannot send messages |
| 6 | Read `#work-units` | Can read pinned message about how work units work |
| 7 | Read `#dev-general` | Sees pinned dev quick start with clone instructions |
| 8 | Read `#issues` | Sees pinned message pointing to "good first issue" labels |
| 9 | Follow GitHub link | Reaches `github.com/FOUNDUPS/science-swarm-hub` |
| 10 | Try to post in `#releases` | **BLOCKED** — read-only channel |
| 11 | Post in `#feedback` | Message sends successfully (open channel) |
| 12 | Post in `#off-topic` | Message sends successfully (open channel) |

### Role Upgrade Test

| Step | Action | Expected Result |
|------|--------|-----------------|
| 13 | Admin assigns `@contributor` to test account | Role appears on profile |
| 14 | Post in `#work-units` | Message sends successfully |
| 15 | Post in `#dev-general` | Message sends successfully |
| 16 | Create thread in `#submissions` | Thread created successfully |

### Pass Criteria

- Steps 1-12: All pass → `@everyone` permissions correct
- Steps 13-16: All pass → `@contributor` permissions correct
- Any failure → check `DISCORD_PERMISSION_MATRIX.md` → fix override → retest

---

## 10. Day-1 Operator Actions (Post-Setup)

After the server is live and smoke-tested:

1. **Post welcome message** in `#welcome` (not pinned — organic first post):
   > Science Swarm Hub is live. This is the coordination layer for PQN research. GitHub remains the canonical action surface. Welcome.

2. **Set slow mode** if needed:
   - `#introductions`: 30 seconds (prevents spam)
   - All other channels: OFF (research discussion should flow freely)

3. **Contributor onboarding** (when someone wants to contribute):
   - Verify they've read #rules and #welcome pins
   - Assign `@contributor` role
   - Point them to CONTRIBUTING.md in the repo

4. **Do NOT**:
   - Install any Discord bots
   - Create webhooks
   - Enable Community features
   - Add more roles (wait until 10+ active contributors)
   - Claim PyPI is live

---

## 11. Ongoing Maintenance

| Frequency | Action |
|-----------|--------|
| Per release | Update `#releases` pin with new version |
| Per release | Update `#welcome` "What Is Not Live Yet" pin |
| As needed | Assign `@contributor` to approved participants |
| As needed | Promote trusted contributors to `@moderator` |
| Monthly | Review channel topics for accuracy |
| If PyPI ships | Update `#rules`, `#welcome`, `#releases`, `#dev-general` pins |

---

## 12. Escalation

| Situation | Action |
|-----------|--------|
| Spam/abuse | Timeout (moderator) or kick (moderator). Ban only if repeated. |
| Fake submission claims | Point to rule 2. Remove message if blatant. |
| Someone claims PyPI exists | Correct immediately — link to source install instructions |
| Bot request | Decline. Reference non-claims in DISCORD_SERVER_BLUEPRINT.md |
| Feature request for Discord | Discuss in #feedback, do not implement same-day |

---

## 13. Non-Claims Reminder

These statements must remain true:

- No Discord bot exists or is planned
- No webhooks connect Discord to GitHub
- No automated notifications
- GitHub is the canonical action surface for all code, issues, PRs, and releases
- Discord is a coordination and discussion layer only
- No PyPI package is published — install from source only
- The server has no Community features enabled

If any of these change, update ALL pinned messages and channel topics that reference them.

---

*This runbook is the operational guide for 012. The checklist version is in `012_DISCORD_SETUP_CHECKLIST.md`.*
