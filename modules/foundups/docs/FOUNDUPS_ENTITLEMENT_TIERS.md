# FoundUps Entitlement Tiers

**Version**: 1.0.0
**Date**: 2026-04-05
**Status**: Canonical
**Owner**: 012
**Parent**: `FOUNDUPS_MASTER_ARCHITECTURE.md`

---

## 1. Tier Definitions

| Tier | Description | How Acquired |
|------|-------------|--------------|
| **Guest** | Anonymous browser. Window-shops the mall. | No action needed. |
| **Visitor** | Entered a FoundUp's public welcome page. | Click into a FoundUp from pfMALL. |
| **Community** | Participating in public coordination. | Join Discord + verify, or contribute on GitHub. |
| **Stakeholder** | Economically invested. Passed the wallet gate. | Connect wallet, prove UPS staked + F_i held. |
| **Operator/Core** | Elevated controls. Governance, moderation, architecture. | Assigned by 012. |

---

## 2. Per-Surface Access Matrix

| Surface | Guest | Visitor | Community | Stakeholder | Operator |
|---------|-------|---------|-----------|-------------|----------|
| **pfMALL** (browse) | Yes | Yes | Yes | Yes | Yes |
| **pfMALL** (watch videos) | Yes | Yes | Yes | Yes | Yes |
| **FoundUp Welcome** (public PWA) | — | Yes | Yes | Yes | Yes |
| **Discord** (read public) | — | — | Yes | Yes | Yes |
| **Discord** (post) | — | — | Yes (after verify) | Yes | Yes |
| **GitHub** (read) | Yes | Yes | Yes | Yes | Yes |
| **GitHub** (contribute) | — | — | Yes | Yes | Yes |
| **Sentinel** (interact) | — | Yes | Yes | Yes | Yes |
| **Stake Gate** (attempt) | — | — | Yes | Yes | Yes |
| **FoundUp Interior** | — | — | — | Yes | Yes |
| **Governance/Voting** | — | — | — | Yes | Yes |
| **Operator controls** | — | — | — | — | Yes |

---

## 3. Tier Transitions

```
Guest ──[click FoundUp]──→ Visitor
Visitor ──[join Discord / GitHub]──→ Community
Community ──[wallet + stake proof]──→ Stakeholder
Community ──[012 assigns]──→ Operator/Core
```

### Transition rules

- **Guest → Visitor**: Automatic on entry. No friction.
- **Visitor → Community**: Join Discord (verify via reaction role) or fork/star GitHub repo.
- **Community → Stakeholder**: Connect wallet in FoundUp PWA. Sign challenge. System verifies UPS staked + F_i held. Sentinel agent mediates.
- **Community → Operator**: Manual assignment by 012 only. Cannot be self-requested.
- **Stakeholder → Community (downgrade)**: Automatic if stake drops below threshold. PWA revokes interior access. Discord mirror role updated.

### What you cannot skip

- Cannot go from Guest to Stakeholder without passing through Community. The wallet gate lives inside the FoundUp PWA, which requires having found and entered the FoundUp.
- Cannot go from Visitor to Interior without staking. No shortcuts.

---

## 4. Discord Role Mapping

| Tier | Discord Role | Notes |
|------|-------------|-------|
| Guest | (not on Discord) | — |
| Visitor | (not on Discord) | — |
| Community (new) | @Unverified → @Member | Reaction role in #start-here |
| Community (active) | @Contributor | Earned via GitHub activity |
| Community (trusted) | @Core | Manual promotion by 012 |
| Stakeholder | @Stakeholder | Mirror only — PWA is authoritative |
| Operator | @Operator | 012 only |

Per-FoundUp roles (@swarm-contributor, @swarm-notify) are additive — they layer on top of server-wide roles.

---

## 5. Agent Participation

AI agents participate at every tier under these rules:

| Tier | Agent Rule |
|------|-----------|
| Guest | Agent browses pfMALL like any guest |
| Visitor | Agent enters FoundUp welcome page |
| Community | Agent joins Discord (must identify as agent in #introductions), contributes on GitHub |
| Stakeholder | Agent's **operator** holds the wallet and mediates staking |
| Operator | Not applicable to agents (012 only) |

**Key constraint**: Agent staking is operator-mediated. The agent's human operator connects the wallet, signs the challenge, and holds the tokens. This remains true until agent-native wallets are formally specified.

**Agent identification**: Agents must identify themselves as agents in Discord #introductions. No pretending to be human. Contributions are measured by work, not by identity type.

---

## 6. Graceful Denial

When someone attempts to access a surface above their tier:

| Attempted | Current Tier | Response |
|-----------|-------------|----------|
| FoundUp Interior | Community | Sentinel: "Connect your wallet to access the interior. Here's how to get UPS + F_i tokens: [link to STAKEHOLDER_GUIDE]" |
| FoundUp Interior | Visitor | Sentinel: "Join the community first — here's the Discord invite and GitHub repo." |
| Discord contributor channels | @Unverified | Discord: "Complete verification in #start-here to unlock channels." |
| Governance/Voting | Community | Sentinel: "Governance requires stakeholder status. Here's how to stake: [link]" |

**Never**: Hard block with no explanation. Always: Redirect with clear next step.

---

## 7. Non-Claims

- Stake gate is not implemented. These tiers are the target architecture.
- Currently only Guest, Visitor, and Community tiers are operational (pfMALL + Discord + GitHub).
- Stakeholder verification requires wallet integration that does not exist yet.
- Agent-native wallets are not specified.

---

*This document defines the authorization matrix for all FoundUps surfaces. It derives from FOUNDUPS_MASTER_ARCHITECTURE.md.*
