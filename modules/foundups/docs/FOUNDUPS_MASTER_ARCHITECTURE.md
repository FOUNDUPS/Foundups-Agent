# FoundUps Master Architecture

**Version**: 1.0.0
**Date**: 2026-04-05
**Status**: Canonical
**Owner**: 012

---

## 1. Five-Layer Funnel

Every FoundUp follows one flow. No exceptions.

```
DISCOVERY → WELCOME → COMMUNITY → GATE → INTERIOR
```

| Layer | Surface | Gated? | Wallet needed? |
|-------|---------|--------|----------------|
| 1. Discovery | pfMALL | No | No |
| 2. Welcome | FoundUp PWA (public routes) | No | No |
| 3. Community | Discord category + GitHub repo | No | No |
| 4. Gate | FoundUp PWA (sentinel + wallet) | Yes | Yes |
| 5. Interior | FoundUp PWA (gated routes) | Yes | Yes |

**Critical design decision**: The gate sits between Community and Interior, not between Discovery and Community. Everything up to and including Community is open. The gate only activates when someone wants economic participation, governance, or privileged work assignments.

---

## 2. Layer Definitions

### 2.1 Discovery (pfMALL)

The mall. Window-shopping. Browse videos, discover FoundUps.

- Entry: open pfMALL
- Actions: watch videos, browse tiles, see FoundUp listings
- Exit: double-tap/click tile or visible "Enter FoundUp" button
- No account needed, no wallet, no login

**Desktop rule**: Always show a visible "Enter FoundUp" control. Double-click is a power-user shortcut, not the only affordance.

### 2.2 Welcome (FoundUp PWA — public)

Each FoundUp's front door. Public-facing.

- Overview, mission statement, team info
- Public videos and content
- Links to Discord/community and GitHub
- No gate — anyone can see this

### 2.3 Community (Discord + GitHub)

Public coordination and contribution surface.

- **Discord**: Category inside the FOUNDUPS server (not a separate server)
- **GitHub**: Repo under the FOUNDUPS org (canonical action surface)
- Discussion, coordination, work discovery, onboarding
- No staking required — this is the social layer
- Human and AI contributors both welcome

**GitHub is canonical**. All code, issues, PRs, and releases live on GitHub. Discord is coordination and discussion only.

### 2.4 Gate (Sentinel + Wallet)

The boundary between public and economic participation.

- **Sentinel agent**: Each FoundUp's boundary keeper
  - Lives in the PWA as primary interface
  - Lightweight presence in Discord (answers "how do I stake?" and links to PWA)
  - Greets, routes, checks status, enforces transitions
  - Denies or downgrades gracefully if not entitled
- **Wallet verification**: In the FoundUp PWA, never in Discord
  - Wallet connect
  - Signed challenge
  - Verify UPS staked + F_i held
  - Pass → unlock interior
  - Fail → stay in Community tier with clear path to staking

**Discord is never the true gate.** Discord is a social doorway. The real gate is wallet + signature + token verification in the PWA.

### 2.5 Interior (FoundUp PWA — gated)

The operating surface for stakeholders.

- Only unlocked after stake proof
- Economic participation, governance, work assignments
- Privileged data, dashboards, voting
- Access revoked if stake drops below threshold

---

## 3. Entitlement Tiers

| Tier | Access | How Acquired |
|------|--------|--------------|
| **Guest** | Browse pfMALL, watch public videos | No action needed |
| **Visitor** | Enter FoundUp Welcome page | Click into a FoundUp |
| **Community** | Join Discord, contribute on GitHub | Join server, verify |
| **Stakeholder** | Pass wallet gate (UPS staked + F_i held) | Connect wallet in PWA |
| **Operator/Core** | Elevated controls beyond stakeholder | Assigned by 012 |

**Agent staking**: AI agents participate at every tier. Staking is operator-mediated — the agent's operator holds the wallet until agent-native wallets are specified.

---

## 4. Repeating Unit Per FoundUp

Each FoundUp gets exactly 7 components:

| Component | What | Setup time |
|-----------|------|------------|
| pfMALL listing | Tile in the mall | Add to catalog |
| PWA shell | Public welcome + gated interior | Template stamp |
| Discord category | 3 text + 1 voice channel | 15 minutes |
| GitHub repo | Code, issues, PRs | Already exists |
| Sentinel agent | Boundary keeper | Config per project |
| Stake gate | Wallet verification | Contract interaction |
| Interior routes | Gated PWA pages | Per-project build |

These scale linearly. None are architecturally coupled in ways that break at 20 instances.

---

## 5. Discord: The Community Layer

Discord is layer 3. Its job:

1. Help people find work (GitHub notification feeds)
2. Let people discuss what they're doing
3. Let the operator broadcast updates

Discord never:
- Verifies wallet state
- Controls access to economic participation
- Determines stakeholder status
- Replaces GitHub as the action surface

See: `FOUNDUPS_DISCORD_BLUEPRINT.md` for full server structure.

---

## 6. Document Map

### Org-level (this repo)

| Document | Purpose |
|----------|---------|
| `FOUNDUPS_MASTER_ARCHITECTURE.md` | This file. Five-layer flow, tiers, repeating unit. |
| `FOUNDUPS_DISCORD_BLUEPRINT.md` | Server structure, roles, channels, automation. |
| `FOUNDUPS_ENTITLEMENT_TIERS.md` | Formal tier definitions, per-surface access matrix. |
| `FOUNDUP_TEMPLATE.md` | Checklist for adding a new FoundUp to the system. |

### Per-FoundUp repo

| Document | Purpose |
|----------|---------|
| `CONTRIBUTING.md` | How to contribute (includes Discord + GitHub paths) |
| `SENTINEL_CONFIG.md` | Project-specific sentinel behavior (future) |
| `STAKEHOLDER_GUIDE.md` | How to go from Community to Stakeholder (future) |

### Deferred specs (future slices)

| Document | Purpose |
|----------|---------|
| `SENTINEL_SPEC.md` | Sentinel agent contract |
| `STAKE_GATE_SPEC.md` | Wallet verification flow |
| `AGENT_CONTRIBUTOR_POLICY.md` | AI agent participation rules |

---

## 7. What Breaks If You're Not Careful

**Community → Stakeholder gap**: Contributors active on Discord and GitHub hit the stake gate and need UPS + F_i tokens. If the path from "contributing" to "can acquire tokens" isn't obvious and documented, best contributors bounce at the gate. The answer must live in the FoundUp Welcome layer (public), not behind the gate.

**Sentinel fragility**: Sits at the public/gated boundary. Must handle graceful denial, correct routing, and wallet verification handoff. Primary interface is PWA, not Discord.

**Discord role drift**: @Stakeholder in Discord must be a mirror of PWA state, never the source of truth. If someone loses their stake, the PWA revokes interior access. Discord updates to match.

---

## 8. Non-Claims

- No stake gate implementation exists today
- No sentinel agent exists today
- No PWA shell exists today (pfMALL has the public discovery layer only)
- Discord and GitHub are the only operational community surfaces
- This architecture is the target — current state is Community layer only

---

*This document is the single source of truth for the FoundUps lifecycle architecture. All other docs reference it.*
