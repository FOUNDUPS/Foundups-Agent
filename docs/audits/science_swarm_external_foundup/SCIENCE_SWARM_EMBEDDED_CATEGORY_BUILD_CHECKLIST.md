# Science Swarm Embedded Category — Build Checklist

**Worker**: BF
**Date**: 2026-04-09
**Status**: Operator-Ready
**Parent**: `FOUNDUPS_SCIENCE_SWARM_EMBED_SPEC.md`

---

## Scope

This checklist creates the **Science Swarm Hub embedded category** inside the existing FOUNDUPS Discord server. It does NOT create a new server.

**Pre-requisite**: FOUNDUPS server exists with server-wide categories (FOUNDUPS, COMMONS, OPERATOR) already set up per `FOUNDUPS_DISCORD_BLUEPRINT.md`.

---

## Phase 1: Pre-Checks

- [ ] Logged into Discord as `@Operator` (012)
- [ ] In FOUNDUPS server (guild ID `412646632992014336`)
- [ ] Server-wide roles exist: `@Operator`, `@Core`, `@Contributor`, `@Stakeholder`, `@Unverified`
- [ ] `#start-here` channel exists (for role reactions)

---

## Phase 2: Create Project Roles

Server Settings → Roles → Create Role

### @swarm-contributor

- [ ] Name: `swarm-contributor`
- [ ] Color: Green (#57F287)
- [ ] Display role members separately: OFF
- [ ] Allow anyone to @mention: ON
- [ ] No special permissions (inherits from @everyone)
- [ ] Position: Below `@Contributor`, above `@Stakeholder`

### @swarm-notify

- [ ] Name: `swarm-notify`
- [ ] Color: None (default)
- [ ] Display role members separately: OFF
- [ ] Allow anyone to @mention: ON
- [ ] No special permissions
- [ ] Position: Below `@swarm-contributor`

---

## Phase 3: Create Category

- [ ] Right-click channel list → Create Category
- [ ] Name: `SCIENCE SWARM HUB` (all caps)
- [ ] Position: After OPERATOR category

### Category Permissions (defaults)

- [ ] Edit Category → Permissions → `@Unverified` → View Channel = **Deny**
- [ ] `@Stakeholder` → View Channel = **Allow** (read-only default)

---

## Phase 4: Create Channels

All channels inside SCIENCE SWARM HUB category.

### #swarm-general (text)

- [ ] Create Text Channel → Name: `swarm-general`
- [ ] Topic: `Science Swarm Hub — project discussion. GitHub is canonical. Discord is coordination.`
- [ ] Permissions:
  - `@Stakeholder` → Send Messages = **Deny** (read-only)
  - `@swarm-contributor` → Send Messages = **Allow**, Create Public Threads = **Allow**
  - `@Core` → Send Messages = **Allow**, Create Public Threads = **Allow**
  - `@Operator` → Send Messages = **Allow**, Create Public Threads = **Allow**, Manage Messages = **Allow**

### #swarm-github (text)

- [ ] Create Text Channel → Name: `swarm-github`
- [ ] Topic: `GitHub activity feed — read-only. All activity is on github.com/FOUNDUPS/science-swarm-hub`
- [ ] Permissions:
  - `@everyone` → Send Messages = **Deny** (read-only for all)
  - `@Operator` → Send Messages = **Allow** (operator-only posting)
- [ ] Threads: **Disabled** (Edit Channel → Thread Archive Duration → None)

### #swarm-work (text)

- [ ] Create Text Channel → Name: `swarm-work`
- [ ] Topic: `What are you working on? Link your GitHub issues and PRs here.`
- [ ] Permissions:
  - `@Stakeholder` → Send Messages = **Deny** (read-only)
  - `@swarm-contributor` → Send Messages = **Allow**, Create Public Threads = **Allow**
  - `@Core` → Send Messages = **Allow**, Create Public Threads = **Allow**
  - `@Operator` → Send Messages = **Allow**, Create Public Threads = **Allow**, Manage Messages = **Allow**

### swarm-voice (voice)

- [ ] Create Voice Channel → Name: `swarm-voice`
- [ ] Permissions: Inherit from category (all verified users can join)

---

## Phase 5: Pin Messages

### #swarm-general — 1 pin

Post and pin:

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

- [ ] Posted and pinned
- [ ] Delete "X pinned a message" system notification

### #swarm-work — 1 pin

Post and pin:

```
How to find work:

1. Check GitHub Issues: github.com/FOUNDUPS/science-swarm-hub/issues
2. Look for "good first issue" labels
3. Browse docs/seed_issues/ in the repo for starter tasks
4. Claim an issue by commenting on it (avoids duplicate effort)
5. Post here when you start work

GitHub is canonical. This channel is for visibility and coordination.
```

- [ ] Posted and pinned
- [ ] Delete "X pinned a message" system notification

### #swarm-github — no pin

No pinned message needed (feed content is self-explanatory).

---

## Phase 6: Update #start-here

In server-wide `#start-here` channel, update the role-reaction message:

- [ ] Add reaction option for Science Swarm: react with designated emoji to gain `@swarm-notify`
- [ ] Update pinned welcome message to list Science Swarm as active FoundUp

---

## Phase 7: Smoke Test

Use a second Discord account (NOT the operator account).

### @Stakeholder Test

- [ ] Account has `@Stakeholder` role (no `@swarm-contributor`)
- [ ] Can see SCIENCE SWARM HUB category
- [ ] Can read `#swarm-general` but CANNOT post
- [ ] Can read `#swarm-github` but CANNOT post
- [ ] Can read `#swarm-work` but CANNOT post
- [ ] Can join `swarm-voice`

### @swarm-contributor Test

- [ ] From operator account: assign `@swarm-contributor` to test account
- [ ] Test account CAN post in `#swarm-general`
- [ ] Test account CAN post in `#swarm-work`
- [ ] Test account CAN create thread in `#swarm-general`
- [ ] Test account CANNOT post in `#swarm-github`

### @Unverified Test

- [ ] Account with only `@Unverified` (no `@Stakeholder`)
- [ ] CANNOT see SCIENCE SWARM HUB category at all

### Cleanup

- [ ] Remove test messages from channels
- [ ] Remove test role assignments (unless keeping test account as contributor)

---

## Phase 8: Done

- [ ] All checkboxes completed
- [ ] Post in `#operator-log`:
  > SCIENCE SWARM HUB category created. 3 text channels + 1 voice. Permissions set per FOUNDUPS_SCIENCE_SWARM_EMBED_SPEC.md.

**Total effort**: ~20-30 minutes for a clean run.

---

## Appendix: Channel Summary

| Channel | Type | Who can post |
|---------|------|--------------|
| `#swarm-general` | text | @swarm-contributor, @Core, @Operator |
| `#swarm-github` | text | @Operator only (read-only feed) |
| `#swarm-work` | text | @swarm-contributor, @Core, @Operator |
| `swarm-voice` | voice | Anyone with @Stakeholder+ can join |

---

## Appendix: Role Summary

| Role | Purpose | Assignment |
|------|---------|------------|
| `@swarm-contributor` | Active Science Swarm contributor | Manual by operator (earned via GitHub activity) |
| `@swarm-notify` | Opt-in pings for Science Swarm updates | Self-assign via #start-here reaction |

---

## Supersedes

This checklist supersedes `012_DISCORD_SETUP_CHECKLIST.md` for Science Swarm. That checklist was for the REJECTED standalone server model.

---

*Execute this checklist once. The result is a working Science Swarm Hub embedded category in the FOUNDUPS Discord server.*
