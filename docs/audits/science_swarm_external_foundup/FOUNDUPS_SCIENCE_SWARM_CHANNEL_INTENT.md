# Science Swarm Hub — Channel Intent (Embedded)

**Worker**: J
**Date**: 2026-04-06
**Slice**: `SCIENCE_SWARM_FOUNDUPS_SERVER_EMBED_SPEC_PHASE1`
**Parent**: `FOUNDUPS_SCIENCE_SWARM_EMBED_SPEC.md`

---

## 1. Category: SCIENCE SWARM HUB

This category is an embedded FoundUp category inside the FOUNDUPS Discord server.

---

## 2. Channel Set (Exact)

| # | Channel | Type | Day 1 |
|---|---------|------|-------|
| 1 | `#swarm-general` | text | YES |
| 2 | `#swarm-github` | text | YES |
| 3 | `#swarm-work` | text | YES |
| 4 | `swarm-voice` | voice | YES |

**Total**: 3 text + 1 voice = 4 channels

---

## 3. Channel-by-Channel Intent

### #swarm-general

| Field | Value |
|-------|-------|
| **Purpose** | Project discussion, questions, general coordination |
| **Who can read** | `@Stakeholder`, `@swarm-contributor`, `@Core`, `@Operator` |
| **Who can post** | `@swarm-contributor`, `@Core`, `@Operator` |
| **Threads** | Allowed |
| **Slow mode** | OFF |

**Topic** (copy-paste):
```
Science Swarm Hub — project discussion. GitHub is canonical. Discord is coordination.
```

**Pinned message** (copy-paste):
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

---

### #swarm-github

| Field | Value |
|-------|-------|
| **Purpose** | Read-only feed of GitHub activity (issues, PRs, releases) |
| **Who can read** | `@Stakeholder`, `@swarm-contributor`, `@Core`, `@Operator` |
| **Who can post** | Webhook only (no humans) |
| **Threads** | Disabled |
| **Slow mode** | OFF |

**Topic** (copy-paste):
```
GitHub webhook feed — read-only. All activity is on github.com/FOUNDUPS/science-swarm-hub
```

**Pinned message**: None (webhook content is self-explanatory)

**Webhook setup** (when implemented):
1. Go to GitHub repo Settings → Webhooks
2. Add Discord webhook URL (created in channel settings)
3. Events: Issues (opened, closed), PRs (opened, merged), Releases (published)

---

### #swarm-work

| Field | Value |
|-------|-------|
| **Purpose** | "What are you working on?" — links to active issues/PRs |
| **Who can read** | `@Stakeholder`, `@swarm-contributor`, `@Core`, `@Operator` |
| **Who can post** | `@swarm-contributor`, `@Core`, `@Operator` |
| **Threads** | Allowed |
| **Slow mode** | OFF |

**Topic** (copy-paste):
```
What are you working on? Link your GitHub issues and PRs here.
```

**Pinned message** (copy-paste):
```
How to find work:

1. Check GitHub Issues: github.com/FOUNDUPS/science-swarm-hub/issues
2. Look for "good first issue" labels
3. Browse docs/seed_issues/ in the repo for starter tasks
4. Claim an issue by commenting on it (avoids duplicate effort)
5. Post here when you start work

GitHub is canonical. This channel is for visibility and coordination.
```

---

### swarm-voice

| Field | Value |
|-------|-------|
| **Purpose** | Real-time voice discussion for Science Swarm |
| **Who can join** | `@Stakeholder`, `@swarm-contributor`, `@Core`, `@Operator` |
| **Video** | OFF by default |
| **User limit** | None |

No topic or pin needed.

---

## 4. Channels NOT Created

The embedded model uses fewer channels than the standalone spec. These are intentionally omitted:

| Standalone Channel | Reason for Omission |
|--------------------|---------------------|
| `#welcome` | Handled by server-wide `#start-here` |
| `#rules` | Handled by server-wide `#rules` |
| `#introductions` | Handled by server-wide `#introductions` |
| `#work-units` | Merged into `#swarm-work` |
| `#submissions` | Discussion happens on GitHub or `#swarm-general` |
| `#verification` | Discussion happens on GitHub or `#swarm-general` |
| `#results` | Announced in `#swarm-general` |
| `#dev-general` | Merged into `#swarm-general` |
| `#issues` | Merged into `#swarm-work` |
| `#releases` | Announced via `#swarm-github` webhook |
| `#feedback` | Handled by server-wide channels |
| `#off-topic` | Handled by server-wide `#off-topic` |

**Rationale**: Server-wide channels handle onboarding, rules, and off-topic. Per-FoundUp categories need only project-specific channels.

---

## 5. Adding More Channels Later

If Science Swarm grows and needs more channels:

1. Propose in `#swarm-general`
2. Operator reviews
3. If approved, add channel with `swarm-` prefix
4. Update this document

Do NOT add channels preemptively. Start minimal.

---

*This document defines the exact channel set for embedded Science Swarm. It derives from `FOUNDUPS_SCIENCE_SWARM_EMBED_SPEC.md`.*
