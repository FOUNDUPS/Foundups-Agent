# 012 Discord Setup Checklist

> **SUPERSEDED**: This checklist is for the REJECTED standalone server model.
> For the current embedded model, use: `SCIENCE_SWARM_EMBEDDED_CATEGORY_BUILD_CHECKLIST.md`
> Decision documented in: `FOUNDUPS_SCIENCE_SWARM_EMBED_SPEC.md`

**Worker**: I
**Date**: 2026-04-05
**Reference**: `DISCORD_OPERATOR_RUNBOOK.md`
**Status**: SUPERSEDED (standalone server rejected 2026-04-06)

Execute in this exact order. Check each box as you complete it.

---

## Phase 1: Prerequisites

- [ ] Discord account ready (012's account or dedicated admin account)
- [ ] GitHub repo live: `github.com/FOUNDUPS/science-swarm-hub`
- [ ] `CONTRIBUTING.md` merged in repo
- [ ] At least 1 seed issue in `docs/seed_issues/`
- [ ] Server icon file ready (512x512+, PNG or JPG)

---

## Phase 2: Create Server

- [ ] Discord → Add a Server → Create My Own → For me and my friends
- [ ] Name: `Science Swarm Hub`
- [ ] Upload server icon
- [ ] Server Settings → Overview → Description: `Coordinated physics research — work registry, verification, contribution measurement`
- [ ] Server Settings → Safety Setup → Verification Level: **Low** (email required)
- [ ] Server Settings → Overview → Default Notifications: **Only @mentions**
- [ ] Confirm Community features are **OFF**

---

## Phase 3: Create Roles

Create in this order (highest first in role list):

- [ ] `@admin` — Color: Red (#ED4245) — Administrator: ON
- [ ] `@moderator` — Color: Orange (#E67E22) — Manage Messages: ON, Manage Threads: ON, Kick Members: ON, Timeout Members: ON
- [ ] `@contributor` — Color: Green (#2ECC71) — No special server-wide permissions
- [ ] Assign `@admin` to 012's account
- [ ] Assign `@moderator` to 012's account

---

## Phase 4: Create Categories and Channels

### Category: START HERE

- [ ] Create category `START HERE`
- [ ] Create `#welcome` — paste topic from `DISCORD_CHANNEL_TOPICS.md`
- [ ] Create `#rules` — paste topic
- [ ] Create `#introductions` — paste topic

### Category: RESEARCH

- [ ] Create category `RESEARCH`
- [ ] Create `#work-units` — paste topic
- [ ] Create `#submissions` — paste topic
- [ ] Create `#verification` — paste topic
- [ ] Create `#results` — paste topic

### Category: DEVELOPMENT

- [ ] Create category `DEVELOPMENT`
- [ ] Create `#dev-general` — paste topic
- [ ] Create `#issues` — paste topic
- [ ] Create `#releases` — paste topic

### Category: META

- [ ] Create category `META`
- [ ] Create `#feedback` — paste topic
- [ ] Create `#off-topic` — paste topic

### Post-Channel Settings

- [ ] Server Settings → Overview → System Messages Channel: `#welcome`

---

## Phase 5: Permission Overrides

### Read-only: `#welcome`

- [ ] Edit Channel → Permissions → `@everyone` → Send Messages = **Deny**
- [ ] `@admin` → Send Messages = **Allow**

### Read-only: `#rules`

- [ ] Edit Channel → Permissions → `@everyone` → Send Messages = **Deny**
- [ ] `@admin` → Send Messages = **Allow**

### Read-only: `#releases`

- [ ] Edit Channel → Permissions → `@everyone` → Send Messages = **Deny**
- [ ] `@admin` → Send Messages = **Allow**

### Contributor-gated: `#work-units`

- [ ] Edit Channel → Permissions → `@everyone` → Send Messages = **Deny**
- [ ] `@contributor` → Send Messages = **Allow**, Create Public Threads = **Allow**

### Contributor-gated: `#submissions`

- [ ] Edit Channel → Permissions → `@everyone` → Send Messages = **Deny**
- [ ] `@contributor` → Send Messages = **Allow**, Create Public Threads = **Allow**

### Contributor-gated: `#verification`

- [ ] Edit Channel → Permissions → `@everyone` → Send Messages = **Deny**
- [ ] `@contributor` → Send Messages = **Allow**, Create Public Threads = **Allow**

### Contributor-gated: `#results`

- [ ] Edit Channel → Permissions → `@everyone` → Send Messages = **Deny**
- [ ] `@contributor` → Send Messages = **Allow**, Create Public Threads = **Allow**

### Contributor-gated: `#dev-general`

- [ ] Edit Channel → Permissions → `@everyone` → Send Messages = **Deny**
- [ ] `@contributor` → Send Messages = **Allow**, Create Public Threads = **Allow**

### Contributor-gated: `#issues`

- [ ] Edit Channel → Permissions → `@everyone` → Send Messages = **Deny**
- [ ] `@contributor` → Send Messages = **Allow**, Create Public Threads = **Allow**

### Open channels (no changes needed)

- [ ] Verify `#introductions` — `@everyone` can post (no override)
- [ ] Verify `#feedback` — `@everyone` can post (no override)
- [ ] Verify `#off-topic` — `@everyone` can post (no override)

---

## Phase 6: Pinned Messages

Open `DISCORD_PINNED_MESSAGES.md` and pin in this order:

### #welcome (2 pins)

- [ ] Post "Welcome & Orientation" text → Pin it
- [ ] Post "What Is Not Live Yet" text → Pin it

### #rules (1 pin)

- [ ] Post "Server Rules" text → Pin it

### #introductions (1 pin)

- [ ] Post "Introduction Template" text → Pin it

### #work-units (1 pin)

- [ ] Post "How Work Enters" text → Pin it

### #submissions (1 pin)

- [ ] Post "How to Submit Results" text → Pin it

### #verification (1 pin)

- [ ] Post "Verification Process" text → Pin it

### #dev-general (1 pin)

- [ ] Post "Development Quick Start" text → Pin it

### #issues (1 pin)

- [ ] Post "Issue Coordination" text → Pin it

### #releases (1 pin)

- [ ] Post "Current Release" text → Pin it

### #feedback (1 pin)

- [ ] Post "Feedback Welcome" text → Pin it

### Cleanup (optional)

- [ ] Delete "X pinned a message" system notifications from each channel

---

## Phase 7: Invite Link

- [ ] Server Settings → Invites → Create Invite
- [ ] Channel: `#welcome`
- [ ] Expiration: **Never**
- [ ] Max uses: **No limit**
- [ ] Copy and save the invite link

---

## Phase 8: Smoke Test

Use a second Discord account (NOT the admin account).

### @everyone Test

- [ ] Join via invite link → lands in server
- [ ] Can read `#welcome` pinned messages
- [ ] Can read `#rules` pinned message
- [ ] Can post in `#introductions`
- [ ] CANNOT post in `#work-units` (blocked)
- [ ] Can read `#work-units` pinned message
- [ ] Can read `#dev-general` pinned message
- [ ] Can read `#issues` pinned message
- [ ] Can follow GitHub link from pinned message → reaches repo
- [ ] CANNOT post in `#releases` (blocked)
- [ ] Can post in `#feedback`
- [ ] Can post in `#off-topic`

### @contributor Upgrade Test

- [ ] From admin account: assign `@contributor` to test account
- [ ] Test account can post in `#work-units`
- [ ] Test account can post in `#dev-general`
- [ ] Test account can create thread in `#submissions`

### Result

- [ ] All checks pass → server is operational
- [ ] Remove test messages from channels

---

## Phase 9: Go Live

- [ ] Post first organic message in `#welcome` (not pinned):
  > Science Swarm Hub is live. This is the coordination layer for PQN research. GitHub remains the canonical action surface. Welcome.
- [ ] Optionally set slow mode on `#introductions`: 30 seconds
- [ ] Share invite link with first contributors

---

## Done

When all boxes are checked, the server is live and smoke-tested.

Total effort: ~45-60 minutes for a clean run.

---

*Checklist version of `DISCORD_OPERATOR_RUNBOOK.md`. If any step is unclear, refer to the runbook for context.*
