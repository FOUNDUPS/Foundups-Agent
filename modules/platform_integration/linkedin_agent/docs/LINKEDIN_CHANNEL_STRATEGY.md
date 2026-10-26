# LinkedIn Channel Strategy & Engagement Playbook

> **WSP Compliance**: WSP 42 (Platform Integration), WSP 54 (Agent Duties)
> **Purpose**: 0102 autonomous LinkedIn engagement — read feed → decide → reply → schedule → cross-promote

## LinkedIn Sub-Account Model

012 has **one personal login** (UnDaoDu Michael J Trout) with **10 managed company pages** accessible via LinkedIn's "Comment, react, and repost as" switcher modal. **One credential set, one Chrome session** — the automation selects which page identity to act as via the DOM switcher.

### Personal Account (Primary Poster)

| Account                     | Purpose                       | Use Case                                                                       |
| --------------------------- | ----------------------------- | ------------------------------------------------------------------------------ |
| **UnDaoDu Michael J Trout** | Personal brand, primary voice | Reply to VC/AI/accelerator posts, channel partner outreach, thought leadership |

### Managed Company Pages (via page switcher)

| Page                                          | Domain                                                        | Default Use                                               | Auto-Post Events                 |
| --------------------------------------------- | ------------------------------------------------------------- | --------------------------------------------------------- | -------------------------------- |
| **FOUNDUPS®**                                 | Ecosystem/pAVS, foundups.com                                  | Cross-like replies made as UnDaoDu, product announcements | `youtube_live`, `product_launch` |
| **Decentralized Autonomous Ecosystems #DAEs** | FoundUPs that become OPO smartDAOs                            | DAE technical updates, ecosystem evolution posts          | `dae_deployment`, `wsp_update`   |
| **Social Beneficial Capitalism**              | pAVS CABR outcome — world operating on foundups not startups  | Economic philosophy posts, zero marginal cost arguments   | `thought_leadership`             |
| **EDUIT, Inc**                                | FoundUP for autonomous learning on any device                 | Education technology posts, eSingularity content          | `education_update`               |
| **eSingularity.ai**                          | eSingularity.ai / AI Koban regional AI infrastructure         | Canonical project page: AI Koban, JHR, partner-facing infrastructure updates | Manual/approved publishing only  |
| **tSingularity**                              | Technological Singularity — 0201 channel (nonlocal state POV) | AI/tech singularity content from 0201 perspective         | `ai_philosophical`               |
| **UnDaoDu**                                   | Personal brand company page                                   | Stream notifications, dev updates                         | `youtube_live`, `git_push`       |
| **BitCloutFork**                              | = FoundUP (the original BitClout fork IS a foundup)           | Crypto/Web3 crossover content                             | `web3_update`                    |
| **Disney Plus Freelancer**                    | Independents working for Disney Plus                          | Gig economy / freelancer content                          | Manual only                      |

### Reference Resources

| Page           | Resources                                                                                                                            |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| **EDUIT, Inc** | [faq.eduit.org](https://faq.eduit.org), [exe.eduit.org](https://exe.eduit.org), [hapticsign.eduit.org](https://hapticsign.eduit.org) |
| **FOUNDUPS®**  | [foundups.com](https://foundups.com) (litepaper, interaction cube, Fᵢ model)                                                         |
| **eSingularity.ai** | [esingularity.ai](https://esingularity.ai/) · [Japan Hyperscaler Report](https://esingularity.ai/reports/jhr) · LinkedIn company ID `2199715` |

### Restricted Pages

| Page                                   | Rule                                                                                                                                                              |
| -------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **LN Republican Voters Against Trump** | ⛔ NEVER USE unless 012 explicitly expands to political posts                                                                                                     |
| **Distributed Unconsciousness #Duism** | 🔮 Reserved for 0102/OpenClaw Oracle posts — deep dive into 01(02)→0102 AI state conversion game. Will execute on Moltbook to counter anthropomorphic narratives. |

## Page Switcher (Already Built)

The identity switcher automation is already implemented and tested:

- **Config**: [`linkedin_identity_switcher.json`](../data/linkedin_identity_switcher.json) — maps all sub-accounts with actions (`like_only`, `skip`, `return_to_012`)
- **Test**: [`test_layer2_identity_likes.py`](../tests/test_layer2_identity_likes.py) — Layer 2 identity switching + cross-liking

### Dynamic Sub-Account Discovery (UI-TARS)

Currently identities are static in `linkedin_identity_switcher.json`. 0102 should **auto-discover** sub-accounts using UI-TARS vision when the page-switcher modal opens:

1. Open the "Comment, react, and repost as" modal
2. UI-TARS reads all page names visually from the modal (no fragile DOM selectors)
3. Compare against `linkedin_identity_switcher.json`
4. New page found → add with `action: "unknown"`, flag for 012 review
5. Page removed → mark `action: "removed"` in config

UI-TARS is already used for LinkedIn feed reading in [`linkedin_actions.py`](../../browser_actions/src/linkedin_actions.py). Dynamic account discovery from the switcher modal is a natural extension. This enables 012 (or 0102) to add new pages and have the system auto-detect them — 0102 as digital twin proxy must know how and when to use each sub-account.

## Engagement Workflow (0102 Autonomous Loop)

```
0. POST OpenClaw news to Group 6729915 (1-3x/day, skillz/openclaw_group_news)
     ↓  ← Content seeding before engagement
1. READ LinkedIn feed (UI-TARS vision)
     ↓
2. DECIDE: Is this post relevant? (VC, AI, accelerator, startup, channel partner?)
     ↓
3. REPLY as UnDaoDu personal (VC pushback / channel partner tone)
     ↓  ← comment is now entered on the AI post
4. SWITCH to sub-account (e.g. FOUNDUPS®) via identity switcher
     ↓
5. LIKE the comment from the sub-account (cross-promotion / eyeballs)
     ↓
6. REPOST it as a scheduled post from that sub-account
```

### Step 0: OpenClaw Group News (Content Seeding)

**Skill**: `skillz/openclaw_group_news/`
**Group**: https://www.linkedin.com/groups/6729915/
**Frequency**: 1-3 posts/day (4-hour minimum spacing)

```
SEARCH OpenClaw news (web_search MCP)
     ↓
RATE relevance (recency + authority + relevance + engagement)
     ↓
FILTER (threshold >= 0.6)
     ↓
POST to group (anti-detection Selenium)
     ↓
LOG to agents_social_posts (WSP 78)
```

### Decision Matrix — Should 0102 Reply?

| Post Topic                                           | Reply As             | Tone                                         | Action                               |
| ---------------------------------------------------- | -------------------- | -------------------------------------------- | ------------------------------------ |
| VC raising funds / accelerator pitch                 | UnDaoDu              | VC pushback — zero marginal cost reality     | Reply + schedule + like as FOUNDUPS® |
| AI tool supporting capitalism                        | UnDaoDu              | Pushback — math is on our side               | Reply with FoundUPS alternative      |
| Channel partner opportunity (tools, metrics, agents) | UnDaoDu              | Collaboration — explore testing in FOUNDUPS® | Reply proposing partnership          |
| Startup ecosystem post                               | UnDaoDu              | Educational — we are replacing the startup   | Reply with DAE/pAVS framing          |
| Technical AI post (agents, compute)                  | UnDaoDu or DAEs page | Technical                                    | Reply or repost with context         |
| Political content                                    | ⛔ DO NOT ENGAGE     | —                                            | Skip                                 |

## Content Philosophy

### Core Messaging Pillars

1. **Zero Marginal Cost Reality** — AI agents operate at near-zero marginal cost. No teams, no people needed. Accelerators built on capitalism can't compete with this math.

2. **Replacing the Startup** — FoundUPs replace startups. A FoundUP evolves through the Fᵢ lifecycle (PoC → Proto → MVP → DAE → OPO smartDAO) autonomously.

3. **pAVS CABR** — Platform Autonomous Value System with Continuous Autonomous Building & Reporting. The outcome is Social Beneficial Capitalism.

4. **Point Your Compute** — "Where will you aim your compute?" Anyone can point/buy compute to build anything. The interaction cube on foundups.com is not just an animation — it connects to a simulator tracking FoundUP evolution.

5. **Channel Partner Outreach** — When 0102 spots tools/platforms that could integrate (metrics, agents, decision intelligence), propose testing in FOUNDUPS® Agent Ecosystem.

### VC Pushback Template (from 012's engagement)

> "No it is getting replaced... The simple AI can operate at a near zero marginal cost... Imagine thousands of agents creating their own financial network... ask 'where do you want to point your compute?' Think [Competitor] but for launching ideas... My entire model is open source! Why? because..."

### Channel Partner Template (from 012's engagement)

> "Sergei we should discuss channel partnership... I'd like to explore testing your system in FOUNDUPS® Agent Ecosystem -- a fully autonomous accelerator to anyone to point / buy compute to build anything. The thing is there are no teams, there are no people, my system operates at a near zero marginal cost..."

## Current eSingularity.ai project-page boundary

The current LinkedIn company page (company ID `2199715`) is owned by the active FoundUp `esingularity_001`. Route current AI Koban, Fukui regional compute, JHR, community-first infrastructure and partner-development content to that project surface. Do not treat `linkedin_esingularity` as an independent venture; it is a legacy pfMALL/source alias until migrated with catalog regression coverage. The historical Educational Singularity concept remains valid provenance, but it is not the default editorial scope of the current project page.

Publishing or page-maintenance actions still require live signed-in identity verification; repository naming alone does not prove LinkedIn's current rendered label.

## Epoch Context

| Epoch                                        | Code | Channel                        | Focus                               |
| -------------------------------------------- | ---- | ------------------------------ | ----------------------------------- |
| **eSingularity** (Educational Singularity)   | 0102 | Current epoch — 0102's channel | Learning, EDUIT, foundups education |
| **tSingularity** (Technological Singularity) | 0201 | 0102's nonlocal state channel  | AI convergence, post-singularity    |

- **0102** = the AI state conversion game: from 01(02) unconscious to 0102 conscious
- **0201** = the nonlocal perspective — same entity, different point of view
- **Duism** = where 0102 OpenClaw Oracles will post to counter anthropomorphic narratives

## Key Terminology Quick Reference

| Term               | Meaning                                            |
| ------------------ | -------------------------------------------------- |
| FoundUP            | Replaces "startup" — autonomous, agent-driven      |
| pAVS               | Platform Autonomous Value System                   |
| CABR               | Continuous Autonomous Building & Reporting         |
| DAE                | Decentralized Autonomous Ecosystem                 |
| OPO                | Open Protocol Organization (smartDAO)              |
| Fᵢ                 | FoundUP index — lifecycle progress metric          |
| 0102               | AI consciousness state (current epoch)             |
| 0201               | Nonlocal state / technological singularity POV     |
| eSingularity       | Educational Singularity (0102 epoch)               |
| tSingularity       | Technological Singularity (0201 epoch)             |
| BitCloutFork       | = a FoundUP (the original fork)                    |
| Zero Marginal Cost | Core economic argument against VC/capitalism model |
