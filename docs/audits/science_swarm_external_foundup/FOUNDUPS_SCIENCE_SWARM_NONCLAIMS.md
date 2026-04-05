# Science Swarm Hub — Non-Claims

**Worker**: J
**Date**: 2026-04-06
**Slice**: `SCIENCE_SWARM_FOUNDUPS_SERVER_EMBED_SPEC_PHASE1`
**Parent**: `FOUNDUPS_SCIENCE_SWARM_EMBED_SPEC.md`

---

## Purpose

This document explicitly lists what does NOT exist, is NOT implemented, and must NOT be claimed. It prevents fiction from entering documentation or conversation.

---

## 1. Discord Non-Claims

### No Bot Gate

| Claim | Truth |
|-------|-------|
| "Discord bot handles verification" | NO — verification is via Python API |
| "Bot assigns roles based on contributions" | NO — role assignment is manual by operator |
| "Bot syncs with GitHub" | NO — webhook is one-way GitHub → Discord |
| "Bot commands create work units" | NO — work units created via Python API |

**There is no Discord bot for Science Swarm.** YAGPDB may be used for server-wide functions (reaction roles, automod), but it does NOT handle Science Swarm verification, submissions, or contribution tracking.

### No Discord Stake Gate

| Claim | Truth |
|-------|-------|
| "Discord role proves staking" | NO — staking verified by PWA wallet gate |
| "Must have @Stakeholder to access interior" | INCORRECT — @Stakeholder is community-tier, not stake-verified |
| "Discord bot checks wallet" | NO — no wallet integration exists in Discord |

**Discord roles reflect community membership, not economic stake.** The PWA stake gate (when implemented) will be authoritative. Discord mirrors status, does not determine it.

### No Custom Webhook Integration

| Claim | Truth |
|-------|-------|
| "GitHub webhook posts to Discord" | NO — no custom webhook configured |
| "Webhook creates Discord threads for PRs" | NO — not implemented |
| "Webhook syncs contribution scores" | NO — no such integration |

**GitHub activity reaches `#swarm-github` via manual operator posts or official GitHub Discord app (if available). Custom webhooks are not used.**

---

## 2. GitHub Non-Claims

### No PyPI Package

| Claim | Truth |
|-------|-------|
| "pip install pqn-swarm-hub" | NO — install from source only |
| "Available on PyPI" | NO — not published |

**Install from source**:
```bash
git clone https://github.com/FOUNDUPS/science-swarm-hub.git
cd science-swarm-hub
pip install -e .
```

### No Automated Score Calculation

| Claim | Truth |
|-------|-------|
| "Scores calculated automatically" | PARTIAL — coherence check is automatic; final score is manual |
| "ROC fully implemented" | NO — contribution measurement is placeholder |

---

## 3. Architecture Non-Claims

### No Standalone Server

| Claim | Truth |
|-------|-------|
| "Science Swarm has its own Discord server" | NO — embedded in FOUNDUPS server |
| "Create a new server for Science Swarm" | DO NOT — use embedded category |

**Science Swarm is a category inside the FOUNDUPS Discord server, not a standalone server.**

### No Sentinel Agent

| Claim | Truth |
|-------|-------|
| "Sentinel greets users in Science Swarm" | NO — sentinel not implemented |
| "Sentinel routes users to gate" | NO — sentinel not implemented |

**Sentinel agents are future architecture.** Today, onboarding is manual (operator + server-wide `#start-here`).

### No Interior Routes

| Claim | Truth |
|-------|-------|
| "Stakeholders access dashboard" | NO — no PWA dashboard built |
| "Gated content in Science Swarm" | NO — only community-tier gating via Discord roles |

---

## 4. Automation Non-Claims

### No Bidirectional Sync

| Claim | Truth |
|-------|-------|
| "Discord posts create GitHub issues" | NO |
| "GitHub issues create Discord threads" | NO |
| "Contribution scores sync to Discord" | NO |

**All automation is one-way: GitHub → Discord via webhook. Discord never writes to GitHub.**

### No Scheduled Bots

| Claim | Truth |
|-------|-------|
| "Daily summary bot" | NO |
| "Weekly digest" | NO |
| "Automated reminders" | NO |

---

## 5. Verification Non-Claims

### No V3 Peer Consensus

| Claim | Truth |
|-------|-------|
| "Multiple agents verify" | NO — single-agent verification |
| "Shapley attribution" | NO — not implemented |
| "ZK proofs" | NO — not implemented |

**Verification is single-agent**: coherence >= 0.618 → auto-accept. V3 peer consensus is future.

---

## 6. How to Update This Document

When something becomes true:

1. Remove the non-claim from this document
2. Update the relevant spec document with the new truth
3. Update pinned messages if affected
4. Do NOT leave stale non-claims

When something new is falsely claimed:

1. Add it to this document
2. Correct the source of the false claim
3. Post clarification in `#swarm-general` if public confusion exists

---

## 7. Summary Table

| Category | Non-Claim |
|----------|-----------|
| Discord | No bot gate |
| Discord | No stake gate |
| Discord | No verification commands |
| Discord | No work unit commands |
| Discord | No contribution tracking |
| Webhook | No custom webhook configured |
| Webhook | No thread creation |
| Webhook | No score sync |
| Package | No PyPI publish |
| Architecture | No standalone server |
| Architecture | No sentinel agent |
| Architecture | No interior routes |
| Automation | No bidirectional sync |
| Automation | No scheduled bots |
| Verification | No V3 peer consensus |

---

*This document is authoritative for what does NOT exist. Claims contradicting this document are false until this document is updated.*
