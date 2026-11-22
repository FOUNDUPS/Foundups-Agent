# FoundUps Master Architecture

**Version**: 1.3.0

**Updated**: 2026-11-21 (shared dock and player-preference ownership; lifecycle gates unchanged)

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

### Play FoundUps product vocabulary and runtime invariant

**Play FoundUps Mall (p.fMALL)** names the PWA store/discovery shell. **Play FoundUps** names what a person does when interacting with a FoundUp. A FoundUp is a separately identified, manifest-declared experience/venture, not a mandate to duplicate the app runtime or backend.

The target is a reusable shell and governed services with per-FoundUp skins, task-specific AI context, entry routes, capabilities and isolated namespaces. Reuse gestures (touch/swipe/pinch/zoom), navigation, accessibility and shared platform adapters; backend agent, memory, RSI/WRE and optional blockchain services remain permissioned and server-side. Manifest capability declarations are requests/contracts, not proof of authorization. Existing separate PWAs and sites may remain independent deployments while the unified runtime is built; never claim universal composition is implemented.

FoundUps may connect through explicit, consented, versioned context and capability contracts while preserving separate identity and authorization. Refer to [manifest schema](PFMALL_FOUNDUP_MANIFEST_SCHEMA.md) and [Mall runtime](../pfmall/README.md).

**Shared interaction requirement, PFDOCK-20261121:** every FoundUp and fractal
view consumes the same floating Search Dock and player-preference contract,
including Play and HPC. The dock's `+` exposes the AI list first, then Video
settings; deliberate video-tile tap defaults to Floating, with selectable
WikiTube/Fullscreen destinations and configurable expansion/return gestures.
Rotation restores the originating Floating presentation; rotation lock is an
open proposal. The [shared navigation contract, section 14](PFMALL_MALL_NAVIGATION_CONTRACT.md#14-shared-search-dock-and-video-preferences)
owns the exact decisions, unresolved defaults, state/provider boundaries and
acceptance. HPC qualifies this common behavior first; current v26 work is
partial, and universal integration or cross-origin settings sync is not proved.

### Fractal views of the same work

**Design contract, reconciled 2026-11-19.** The fractal is a recursive navigation
and composition model: open an entity to inspect its parts, follow a relationship
to another entity, or open a leaf's permitted artifact. The same interaction
repeats at different scales. It does not promise unlimited depth in memory,
infinite resources, or a working implementation of every proposed view.

#### Identity, composition and relationships

A stable tile ID identifies a logical subject. Names, locations, implementations
and evidence can change while that identity remains. A report issue, an adapter,
a FoundUp and a WSP_80 orchestration cube can each have a tile. A visual cube or
container alone has no orchestration authority; only a scoped orchestration
cube carries the contract in [WSP_80](../../../WSP_framework/src/WSP_80_Cube_Level_DAE_Orchestration_Protocol.md).
Manifest registration remains owned by the FoundUp registry. Inventorying a
candidate does not register, deploy or activate it.

The primary containment relation supplies an acyclic browse hierarchy and
direct-entry ancestry. Other relationships cross that hierarchy. A shared
component has one ID even when multiple FoundUps or views refer to it.
Containment does not transfer ownership, execution authority or economic rights.
Real dependency cycles must be recorded and assessed by their owner, not
discarded solely to make a display tree.

| Relationship | Meaning and evidence requirement |
|---|---|
| Contains / member of | Structural placement or declared cube/FoundUp membership; identify the declaring owner. |
| Calls / reads from / depends on | Trace the actual caller, registration, route, data contract or other integration; mark inference and unknowns. |
| Reuses / overlaps | Identify compatible capability and behavior; independent review is needed before recommending consolidation. |
| Runs through / evaluates | Distinguish scaffold, model, harness and evaluator; a declared route is not an observed execution. |
| Produces receipt / verified by | Link the exact run, evidence and verifier, including disagreements and limits. |
| Lifecycle / descendant / economic | Link separately owned stage gates or economic records; no transition or payment is inferred from a tile edge. |

These are semantic requirements, not a new JSON schema. Reconcile them with the
existing pinned Fractal Tile Graph schema and projector when the reported local
artifacts are accessible. Reuse supported fields and aliases; preserve an
unsupported relation in the audit ledger rather than inventing an accepted API.

#### Inventory and evidence

Account for every discovered candidate, including partial, unintegrated,
documented-only, proposed, archived and inaccessible items. Preserve the
enumeration denominator, exclusions and unresolved identity associations.
The three audit questions are purpose; evidence of functionality and integration;
and use, reuse or overlap. These assessments have separate fields:

| Assessment | What it establishes |
|---|---|
| Functionality | Behavior supported by implementation, a test outcome or an observation in a named environment. |
| Integration | Actual callers, adapters and dependencies, with separate evidence for an observed connection. |
| Availability and execution | Installed, configured, callable, tested, observed running, fixture-only, inaccessible or proposed; statuses may coexist for different environments. |
| Maturity | Venture lifecycle evidence and approved gates; a working module alone does not establish a paying-customer MVP. |
| Priority | Canonical [WSP_15](../../../WSP_framework/src/WSP_15_Module_Prioritization_Scoring_System.md) dimensions and 4–20 score/P0–P4 band. Completeness and any optional Mall rescue ranking are separate. |

A test file proves that a test exists, not that it passed. A passing receipt
is bound to its source and environment, not every later revision. Zero static
imports creates an orphan candidate; dynamic registration, standalone entrypoints
and external consumers still require investigation. Color is a presentation
summary with a legend, not a substitute for these independent assessments or an
access-control decision.

#### Views and work observations

The target 3D build view, 2D Mall field and supported 0102 conversation project
the same identified entities. Co-building, community spaces such as HPC,
portfolio/licensing research, domain markets such as Akiya and WikiTube/media
are views over those entities. An All Mall overview adds a view, not a sixth
independent engine. A view does not prove licensing readiness, property status,
live playback or a worker's availability.

Each artifact reference binds its repository, path and exact source revision,
or a base revision plus recorded overlay digest. The graph/projection revision
identifies the inventory snapshot and stays distinct from source revisions.
A work ID identifies an occurrence; a tile identifies its subject. Their
many-to-many association requires a permitted work order, source change,
receipt or equivalent evidence. A worker label, lease, animation or aggregate
progress count alone cannot identify the changed component.

Pass only permitted focus, actual caller history, work reference and graph
revision to the concierge. Navigation restores the caller across shared edges.
Simulated, stale, unmapped and restricted observations retain those labels.
Public discovery exposes only the permitted published projection; architect
views can expose authorized source, tests, private receipts and roadmap gaps.
Private paths and receipt content must not enter public exports, public search
or history, or unauthorized agent context. Selection and camera motion are navigation. Approved graph
changes require a separate authenticated, revision-checked write path.

The first visualization acceptance path is
`Tools → Benchmark → harness/evaluator → supported module or model/scaffold configuration → run receipt → pinned test/source → Back`.
Use real IDs where evidence exists and expose missing owners/adapters as gaps.
The complementary builder path follows an observed work record to its component
and pinned evidence. The [navigation contract](PFMALL_MALL_NAVIGATION_CONTRACT.md#13-fractal-work-navigation),
[Mall roadmap](../pfmall/ROADMAP.md#fractal-tile-graph-and-agent-work-navigation)
and [Simulator roadmap](../simulator/ROADMAP.md#linking-observed-work-to-mall-tiles)
own acceptance and sequencing.

#### Implementation boundary at the documentation audit

| Evidence class | Bounded conclusion |
|---|---|
| Inspected repository source | Main `7432d31e5a68544d2bbab6715f02f64b0b5b6f85` contains existing catalog, navigation and cube/work-observation owners. Presence does not establish a live PC route. |
| Reported local work | Carbon's report names commit `121c5066687c5ab7571ef52382e5d9c68494cc36`, a Fractal Tile Graph and local HPC → AutoPost → Back checks. This documentation audit could not retrieve that commit or independently replay its private receipts. |
| Target / specified | Full 2D/3D/conversation graph navigation, evidence-bound builder drill-down, the Tools branch and later authorized co-building. Local media/voice fixtures are not live playback or live Simulator wiring. |

The [documentation audit](https://github.com/FOUNDUPS/Foundups-Agent/blob/dc7c34aa6444aa1fc37de1217f99f0e75e4d2f0b/docs/audits/architecture/PFMALL_FRACTAL_DOCUMENTATION_AUDIT_20261119.md)
retains the source provenance, count discrepancies and next evidence needed.

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

- **Open landing (`play.foundups.com`)**: `play.foundups.com` mounts the open
  guest p.fMALL discovery surface across all catalog FoundUps (just as
  `hpc.foundups.com` mounts the dedicated single-FoundUp HPC Shorts projection)
  without Clerk or Firestore admission reads.
- **Admission and safe return (v26 candidate)**: public browsing and static
  FoundUp metadata are separate from protected member or editor actions. The
  candidate retains the existing same-origin Play sign-in gate, OAuth callback,
  invite path and bounded intent restoration; admission does not auto-submit or
  grant editor permission. The requested public levels 1–2 / protected level 3+
  policy is not an implemented graph ACL, and contribution remains unavailable
  until its authoritative service can check identity, membership and editor
  scope. Cross-origin contribution return fails closed. See the current
  [phone source boundary](PFMALL_MALL_NAVIGATION_CONTRACT.md#2026-11-21--v26-phone-candidate-unreleased).
  The older blanket apex-portal wording remains
  [historical source](https://github.com/FOUNDUPS/Foundups-Agent/blob/2a65e7983acb489084cecf1229fcfd582f68f19b/modules/foundups/docs/FOUNDUPS_MASTER_ARCHITECTURE.md#L61),
  not a new instruction to gate every public FoundUp view.
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
| Fractal graph at reported local `121c50666` | Reported local candidate; not present in inspected main and not independently replayed in this audit |
| Unified 2D/3D/voice graph and Tools → Benchmark walkthrough | Specified; navigation, artifact binding and live execution need separate acceptance |

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
| [Mall navigation](PFMALL_MALL_NAVIGATION_CONTRACT.md#13-fractal-work-navigation) | Stable-target drill-down, caller restoration and revision-bound evidence |
| [Mall roadmap](../pfmall/ROADMAP.md#fractal-tile-graph-and-agent-work-navigation) | Census, parallel benchmark sampling, visualization and later reconciliation |
| [Audit benchmark dispatch](../../../docs/operations/RSI_SWARM_DISPATCH.md#fractal-census-and-bounded-comparison--2026-11-19) | Existing scaffold/model/research owners and bounded comparison contracts |
| [Fractal documentation audit](https://github.com/FOUNDUPS/Foundups-Agent/blob/dc7c34aa6444aa1fc37de1217f99f0e75e4d2f0b/docs/audits/architecture/PFMALL_FRACTAL_DOCUMENTATION_AUDIT_20261119.md) | Dated provenance, owner coverage, corrections and unresolved evidence |
| `FOUNDUPS_DISCORD_BLUEPRINT.md` | Community server structure |
| `FOUNDUPS_ENTITLEMENT_TIERS.md` | Per-surface entitlement matrix |
| `FOUNDUP_TEMPLATE.md` | Adding a FoundUp |
| `PFMALL_SHELL_CONTRACT.md` | p.fMALL platform boundary |
| [`../pfmall/AUTOPOST_ITEM_CAPTURE_HANDOFF.md`](../pfmall/AUTOPOST_ITEM_CAPTURE_HANDOFF.md) | AutoPost original photos, private item grouping and shared Mall attachment; specification and implementation gates |
| `public/member/RED_DOG_DIGITAL_TWIN_CONTRACT.md` | RedDog thin-client and authority contract |
| `WSP_framework/src/WSP_73_012_Digital_Twin_Architecture.md` | RedDog/0102 protocol |
| `WSP_framework/src/WSP_98_FoundUps_Mesh_Native_Architecture_Protocol.md` | Federated/mesh target gates |

This document is the canonical FoundUps lifecycle and surface map. Protocols
own governance; module interfaces own current implementation; ModLogs own
history.
