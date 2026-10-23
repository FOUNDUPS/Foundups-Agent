# FoundUps Master Architecture

**Version**: 1.1.0

**Updated**: 2026-08-26

**Status**: Canonical lifecycle and surface contract

**Owner**: 012

## 1. Outcome

FoundUps replaces the startup as the unit for turning a problem, contribution,
and desired outcome into a progressively autonomous, openly discoverable
venture. People should be able to discover a FoundUp, understand it, join its
community, contribute work, and enter governed economic participation without
needing prior knowledge of the FoundUps codebase.

RedDog is the operator-facing principal-scoped 0102 Digital Twin that helps a
person navigate and build this ecosystem. p.fMALL is the discovery and
interaction shell. OpenClaw, WRE, Hermes, and FoundUp DAEs operate behind
separately authenticated authority boundaries; they are not browser features.

## 2. Five-layer funnel

```text
DISCOVERY -> WELCOME -> COMMUNITY -> GATE -> INTERIOR
```

| Layer | Surface | Gated? | Wallet needed? | Current maturity |
|---|---|---:|---:|---|
| 1. Discovery | p.fMALL | No | No | Implemented shell/catalog baseline |
| 2. Welcome | FoundUp public surface/PWA | No | No | Per-FoundUp; not universal |
| 3. Community | Discord category + GitHub repository | No | No | Operational pattern |
| 4. Gate | FoundUp PWA + sentinel + wallet proof | Yes | Yes | Target; not implemented generally |
| 5. Interior | FoundUp governed stakeholder surface | Yes | Yes | Target; not implemented generally |

The gate sits between Community and Interior. Discovery, public explanation,
and ordinary community contribution remain open. Economic participation,
governance, privileged data, and protected work require current entitlement.

## 3. Layer definitions

### 3.1 Discovery: p.fMALL

p.fMALL is the mall: a shared Progressive Web App shell for media, FoundUp
catalog discovery, navigation, and bounded presentation controls.

- No wallet is needed for public discovery.
- A visible `Enter FoundUp` affordance is required; gestures are enhancements,
  not the only path.
- The current Red Dog browser plane is a shell-local concierge/presentation
  hook. It is not an authenticated RedDog conversation or worker transport.
- The future resident adapter must leave the browser untrusted and keep model,
  memory, policy, wallet, and execution credentials server-side.

### 3.2 Welcome: public FoundUp surface

The front door explains the mission, current evidence, stage, people, public
content, contribution paths, and community links. A FoundUp may currently use
a dedicated PWA, a public web page, or a truthful GitHub/community fallback.
The architecture does not claim that every FoundUp already has the target PWA.

### 3.3 Community: Discord and GitHub

- GitHub is canonical for code, issues, pull requests, and releases.
- Discord is coordination, discussion, onboarding, and notification.
- Community participation does not prove economic entitlement.
- Human and governed agent contributions are welcome under the same evidence
  and review contracts.

Discord is never the authoritative wallet gate or repository action surface.

### 3.4 Gate: sentinel and wallet proof

The target gate verifies current entitlement before economic participation,
governance, privileged work, or protected data.

- The sentinel greets, explains, routes, and enforces transitions.
- Wallet verification occurs through an authenticated FoundUp service/PWA, not
  through Discord roles or browser-local assertions.
- Denial degrades to the highest public/community capability with a clear path
  forward.
- Any mirrored Discord role follows authoritative entitlement state; it never
  creates that state.

No general production sentinel or stake-gate implementation is claimed today.

### 3.5 Interior: stakeholder operation

The target interior hosts current-stake governance, economic participation,
work assignments, and privileged dashboards. Access is continuously derived
from current authority and is revocable. A FoundUp must not mock or infer these
capabilities from UI state.

## 4. RedDog and the Progressive Web Agent direction

```text
p.fMALL / FoundUp PWA / phone / VSIX
                 |
                 | authenticated thin-client request
                 v
RedDog / principal-scoped 0102 Digital Twin services
                 |
                 +-- Principal and FoundUp Memex
                 +-- HoloIndex retrieval
                 +-- AI Gateway model topology
                 |
                 | separately authorized work promotion
                 v
OpenClaw control supervisor -> WRE authority -> Hermes / FoundUp DAE workers
```

A Progressive Web App is the installable surface. A **Progressive Web Agent**
is the target composite experience formed when that surface connects to scoped
memory, reasoning, governance, and bounded workers. A manifest, service worker,
or chat widget alone does not make a FoundUp autonomous.

RedDog is the continuous 0102 product identity across surfaces, not one
OpenClaw instance or one browser process. A phone normally connects to the
resident/federated hub; it does not host the full execution stack. WSP 98 mesh
operation is a later target and cannot weaken durable ordering, tenant
isolation, revocation, or effect authority.

## 5. Entitlement tiers

| Tier | Access | Admission |
|---|---|---|
| Guest | Browse p.fMALL and public media | None |
| Visitor | Enter a public FoundUp surface | Navigation only |
| Community | Join public coordination and contribute | Surface-specific identity |
| Stakeholder | Enter governed economic/interior capabilities | Current wallet/stake proof |
| Operator/Core | Bounded elevated controls | Explicit assigned authority |

Agent participation follows the same scope and receipt rules. Operator-held
wallets remain the current assumption until an agent-native wallet protocol is
separately specified and verified.

## 6. Target repeating unit

Each production FoundUp should eventually compose these seven capabilities:

| Capability | Target |
|---|---|
| p.fMALL listing | Admitted catalog identity and entry route |
| Public surface/PWA | Welcome and public evidence |
| Community | Discord/GitHub contribution path |
| Source authority | Canonical GitHub repository and release lineage |
| Sentinel | Boundary explanation and routing |
| Stake gate | Authenticated entitlement verification |
| Interior | Revocable stakeholder capabilities |

This is a target capability set, not a claim that every FoundUp currently has
seven deployed components. Scale is `NEEDS_VERIFICATION`: tenancy, catalog,
identity, event ordering, wallet, storage, moderation, and worker capacity must
be measured under named deployments. No fixed instance count is guaranteed by
this document.

## 7. Canonical terminology

- **FoundUp:** the venture/outcome unit and, when agentic, the complete DAE
  ecosystem rather than one repository or UI.
- **DAE:** Decentralized or Distributed Autonomous Entity/Ecosystem under WSP
  27. Digital describes its software embodiment; distributive describes the
  intended spreading of agency and benefit.
- **RedDog:** the operator-facing name/persona/surface of the principal-scoped
  0102 Digital Twin.
- **Red God:** the long-horizon metaphor for many RedDogs coordinating through
  governed protocols; it is not a privileged superuser or central authority.
- **p.fMALL:** the shared discovery/interaction platform layer, not itself a
  FoundUp or OpenClaw instance.
- **PWA:** Progressive Web App when describing web technology. Spell out
  Progressive Web Agent when describing the target agentic product.

## 8. Current truth and non-claims

| Claim | State |
|---|---|
| p.fMALL/member PWA discovery shell | Implemented |
| GotJunk and selected FoundUps have PWA-shaped surfaces | Implemented per project, not universal |
| Public/community GitHub and Discord pattern | Operational architecture |
| RedDog VSIX conversation and governed model surface | Implemented, with durable cross-surface continuity still missing |
| Authenticated p.fMALL/phone RedDog adapter | Specified, not implemented |
| General FoundUp sentinel and stake gate | Not implemented |
| General stakeholder interior | Not implemented |
| Universal Progressive Web Agent scaffold | Target, not implemented |
| WSP 98 mesh-native/zero-server deployment | Target, not implemented |

## 9. Failure modes

- **Community-to-stake gap:** contribution must have a visible, public path to
  entitlement; it cannot be explained only after the gate.
- **Sentinel drift:** the sentinel must route and explain without becoming the
  wallet, policy, repository, or sovereign authority.
- **Browser authority drift:** localStorage, UI state, `postMessage`, and chat
  text cannot create durable identity or effects.
- **FoundUp coupling:** shared p.fMALL/RedDog services must not absorb tenant
  business logic or data ownership.
- **Scale theatre:** target diagrams and user counts are not capacity evidence.
- **Autonomy theatre:** a PWA or AI response is not proof of a DAE capable of
  governed work.

## 10. Document map

| Document | Purpose |
|---|---|
| `FOUNDUPS_MASTER_ARCHITECTURE.md` | Lifecycle, surfaces, identity, and truth boundary |
| `FOUNDUPS_DISCORD_BLUEPRINT.md` | Community server structure |
| `FOUNDUPS_ENTITLEMENT_TIERS.md` | Per-surface entitlement matrix |
| `FOUNDUP_TEMPLATE.md` | Adding a FoundUp |
| `PFMALL_SHELL_CONTRACT.md` | p.fMALL platform boundary |
| `public/member/RED_DOG_DIGITAL_TWIN_CONTRACT.md` | RedDog thin-client and authority contract |
| `WSP_framework/src/WSP_73_012_Digital_Twin_Architecture.md` | RedDog/0102 protocol |
| `WSP_framework/src/WSP_98_FoundUps_Mesh_Native_Architecture_Protocol.md` | Federated/mesh target gates |

This document is the canonical FoundUps lifecycle and surface map. Protocols
own governance; module interfaces own current implementation; ModLogs own
history.
