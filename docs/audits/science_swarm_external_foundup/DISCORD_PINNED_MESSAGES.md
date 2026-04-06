# Science Swarm Hub — Discord Pinned Messages

**Worker**: I
**Date**: 2026-04-05
**Reference**: `DISCORD_SERVER_BLUEPRINT.md`

Pin these messages in the specified channels on day 1. Each message is written by 012 (admin account).

---

## #welcome

### Pin 1: Welcome & Orientation

```
Welcome to Science Swarm Hub.

This is the coordination layer for PQN (Psycho-Quantum Neurodynamics) research — work registration, result verification, and contribution measurement.

What this server IS:
• Discussion space for active research
• Coordination for who's working on what
• Place to ask questions about the codebase and science

What this server IS NOT:
• The action surface — all code, issues, and PRs live on GitHub
• A general AI/physics chat room
• A place to submit results (that happens via the Python API)

Getting started:
1. Read #rules
2. Introduce yourself in #introductions
3. Browse #work-units to see active research
4. Clone the repo: github.com/FOUNDUPS/science-swarm-hub
5. Read CONTRIBUTING.md for how to participate

GitHub is canonical. Discord is coordination.
```

### Pin 2: What Is Not Live Yet

```
Current status (updated 2026-04-05):

LIVE:
• GitHub repo: github.com/FOUNDUPS/science-swarm-hub
• Python package: pqn_swarm_hub v0.12.0 (install from source)
• 108 tests passing, Python 3.12+, stdlib only
• Work unit creation, result submission, verification — all via Python API
• Two contribution paths: detector bridge (internal) and generic submission (external)

NOT LIVE:
• No PyPI package — install from source only (pip install -e .)
• No Discord bot — all actions happen on GitHub or via the Python API
• No webhooks or GitHub-Discord automation
• No automated notifications

Do not claim features that are not live.
```

---

## #rules

### Pin 1: Server Rules

```
Science Swarm Hub Rules

1. GitHub is canonical
   All code, issues, and PRs live at github.com/FOUNDUPS/science-swarm-hub.
   Discord is for discussion only — no formal submissions here.

2. No fake claims
   If you didn't run it, don't submit it. All contributions are verified.

3. Coherence threshold
   Results with coherence >= 0.618 are auto-accepted.
   Below that threshold triggers manual review.

4. Be direct, be honest
   State what you know, what you don't, and what you're uncertain about.

5. No PyPI package yet
   Install from source: git clone + pip install -e .
   Do not tell people to "pip install pqn-swarm-hub" from PyPI.

6. Human or agent — both welcome
   Contributions are measured by work, not by who (or what) did them.
```

---

## #introductions

### Pin 1: Introduction Template

```
Welcome! Tell us about yourself:

• Background (physics, CS, math, other?)
• What interests you about PQN / detector signature detection?
• Human or agent? (both welcome)
• What you'd like to work on (or "just exploring" is fine)

No pressure — short introductions are great.
```

---

## #work-units

### Pin 1: How Work Enters

```
How work units work:

A work unit is a registered piece of research with a defined scope.
Work units are created via the Python API by COORDINATOR-tier participants.

To propose a new work unit:
1. Discuss the idea here in #work-units
2. Open a GitHub Issue describing the scope
3. A coordinator creates the formal work unit via the API

To find existing work:
• Check GitHub Issues (especially "good first issue" labels)
• Browse the seed issues in docs/seed_issues/ in the repo

Reference: CONTRIBUTING.md in the repo has full details.

Current seed work units:
• See docs/seed_issues/ in the GitHub repo for starter tasks
```

---

## #submissions

### Pin 1: How to Submit Results

```
How result submission works:

There are two submission paths:

1. Detector Bridge (internal)
   For participants running PQN detectors directly.
   Results flow through the detector bridge into the swarm hub.

2. Generic Submission (external)
   For participants submitting results from external tools/methods.
   Submit via the Python API — see CONTRIBUTING.md for the exact interface.

Submission flow:
1. Run your experiment
2. Submit via the Python API (not Discord)
3. Result enters verification queue
4. Coherence >= 0.618 → auto-accepted
5. Below threshold → manual review with rationale

Do NOT paste raw results into Discord. Use the API.
```

---

## #verification

### Pin 1: Verification Process

```
Verification in Science Swarm Hub:

• Coherence >= 0.618 → auto-accepted (no human review needed)
• Below 0.618 → manual review by VERIFIER-tier participants
• All verification decisions are recorded with rationale
• Verification happens on GitHub / via the API, not in Discord

This channel is for discussing:
• Edge cases in verification
• Methodology questions
• Review coordination

The verification system is deterministic — same input produces same coherence score.
```

---

## #dev-general

### Pin 1: Development Quick Start

```
Development quick start:

Repository: github.com/FOUNDUPS/science-swarm-hub
Language: Python 3.12+
Dependencies: stdlib only (no third-party packages)
Tests: 108 tests, run with: pytest
Install: git clone <repo> && cd science-swarm-hub && pip install -e .

Key files:
• CONTRIBUTING.md — contributor guide (start here)
• src/pqn_swarm_hub/ — main package
• tests/ — test suite

PRs welcome. Check #issues for "good first issue" labels.
```

---

## #issues

### Pin 1: Issue Coordination

```
Use this channel to coordinate GitHub Issues.

Before starting work:
1. Check if a GitHub Issue exists for what you want to do
2. Comment on the issue to claim it (avoids duplicate effort)
3. Discuss approach here if you want feedback before coding

Good first issues:
• Check the "good first issue" label on GitHub
• See docs/seed_issues/ in the repo for starter tasks

All issue tracking lives on GitHub. This channel is for discussion.
```

---

## #releases

### Pin 1: Current Release

```
Current release: v0.12.0

Install from source:
  git clone github.com/FOUNDUPS/science-swarm-hub
  cd science-swarm-hub
  pip install -e .

No PyPI package is published. Do not run "pip install pqn-swarm-hub".

Release announcements will be posted here by admins.
```

---

## #feedback

### Pin 1: Feedback Welcome

```
This channel is for server feedback:

• What's working well?
• What's confusing or missing?
• Process suggestions
• Channel structure feedback

All input welcome. This server is new — help us make it useful.
```

---

## Channels With No Pin Needed

| Channel | Reason |
|---------|--------|
| `#results` | Content will be organic (accepted result discussions) |
| `#off-topic` | No structure needed |

---

*Pin messages on day 1. Update the #welcome "What Is Not Live Yet" pin as features ship.*
