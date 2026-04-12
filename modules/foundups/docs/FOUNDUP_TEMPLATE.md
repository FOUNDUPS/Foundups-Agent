# FoundUp Template — Adding a New FoundUp

**Version**: 1.0.0
**Date**: 2026-04-05
**Status**: Canonical
**Owner**: 012
**Parent**: `FOUNDUPS_MASTER_ARCHITECTURE.md`

---

## Purpose

Checklist for adding a new FoundUp to the system. Each FoundUp gets 7 components following the five-layer architecture.

---

## Prerequisites

Before adding a FoundUp:

- [ ] GitHub repo exists under the FOUNDUPS org
- [ ] `CONTRIBUTING.md` exists in the repo
- [ ] Project has a clear one-line description
- [ ] Short prefix chosen (e.g., `swarm-`, `[project]-`) — max 8 characters
- [ ] 012 has approved the FoundUp for Community layer

---

## Component 1: pfMALL Listing

- [ ] Add entry to `mall-video-catalog.json` (or equivalent catalog)
- [ ] Tile image / thumbnail ready
- [ ] FoundUp brief exists in `modules/foundups/docs/`
- [ ] "Enter FoundUp" control routes to Welcome page

---

## Component 2: FoundUp PWA Shell (public routes)

- [ ] Welcome page with: overview, mission, team, public videos
- [ ] Links to Discord category and GitHub repo
- [ ] No gate on public routes
- [ ] Visible entry controls (not just gesture-based)

---

## Component 3: Discord Category

Time: ~15 minutes

### Channels

- [ ] Create category: `[FOUNDUP NAME]` (UPPER CASE)
- [ ] Create `#[prefix]-general` — project discussion
- [ ] Create `#[prefix]-github` — read-only webhook feed
- [ ] Create `#[prefix]-work` — "what are you working on?"
- [ ] Create `[prefix]-voice` — voice channel

### Roles

- [ ] Create `@[prefix]-contributor` — active project contributor
- [ ] Create `@[prefix]-notify` — opt-in update pings

### Permissions

For `#[prefix]-general` and `#[prefix]-work`:
- [ ] `@Unverified` → deny all
- [ ] `@Stakeholder` → read only
- [ ] `@[prefix]-contributor` → send messages, create threads
- [ ] `@Core` → send messages, create threads
- [ ] `@Operator` → send messages, create threads, manage messages

For `#[prefix]-github`:
- [ ] Everyone except webhooks → read only

For `[prefix]-voice`:
- [ ] `@Unverified` → deny
- [ ] `@Stakeholder` and above → join

### Pins and integration

- [ ] Pin project overview in `#[prefix]-general`
- [ ] Add GitHub webhook to `#[prefix]-github`
- [ ] Add reaction role option in `#start-here` for `@[prefix]-notify`

---

## Component 4: GitHub Repo

- [ ] Repo exists at `github.com/FOUNDUPS/[repo-name]`
- [ ] `CONTRIBUTING.md` includes Discord link and community onboarding path
- [ ] At least 1 "good first issue" or seed issue exists
- [ ] README has project overview matching Discord pin

---

## Component 5: Sentinel Agent (future)

- [ ] `SENTINEL_CONFIG.md` in FoundUp repo
- [ ] Greeting flow defined
- [ ] Public routing logic defined
- [ ] Stakeholder verification handoff to PWA defined
- [ ] Graceful denial messages defined

**Status**: Not implemented. Create config doc for future activation.

---

## Component 6: Stake Gate (future)

- [ ] Wallet connect integration
- [ ] UPS staking threshold defined for this FoundUp
- [ ] F_i token requirement defined
- [ ] Challenge-response signing flow
- [ ] Pass/fail/downgrade behavior defined

**Status**: Not implemented. Define thresholds for future activation.

---

## Component 7: Interior Routes (future)

- [ ] Gated PWA pages defined
- [ ] Governance/voting surfaces defined
- [ ] Privileged work assignment surfaces defined
- [ ] Access revocation on stake loss defined

**Status**: Not implemented. Spec when gate is ready.

---

## Verification

After completing available components:

- [ ] New member can discover FoundUp in pfMALL
- [ ] New member can read Welcome page
- [ ] New member can join Discord and find the FoundUp category
- [ ] New member can find work on GitHub
- [ ] GitHub webhook posts to `#[prefix]-github`
- [ ] Reaction role in `#start-here` works for `@[prefix]-notify`

---

## First Instance: Science Swarm Hub

| Component | Status |
|-----------|--------|
| pfMALL listing | Catalog entry exists |
| PWA shell | Not built (public GitHub repo serves as Welcome) |
| Discord category | Ready to create (see `FOUNDUPS_DISCORD_BLUEPRINT.md`) |
| GitHub repo | Live at `github.com/FOUNDUPS/science-swarm-hub` |
| Sentinel agent | Not built |
| Stake gate | Not built |
| Interior routes | Not built |

**Operational today**: Components 3 (Discord) and 4 (GitHub).

---

*Use this template each time a new FoundUp is added. Update the template if the pattern changes.*

---

## Required README Sections (WSP 91 + WSP 104 Compliance)

Every FoundUp with `module.json` or `foundup_manifest.json` MUST include these sections in its README.md. See `FOUNDUP_AI_HOOKS_AND_DAEMON_SURFACE_CONTRACT.md` for the full contract.

---

## Route Namespace

Canonical contract: `modules/foundups/docs/FOUNDUP_AI_HOOKS_AND_DAEMON_SURFACE_CONTRACT.md`. Routing follows **WSP 104** (`/f/{foundup_id}`).

| Field | Value |
|-------|-------|
| `foundup_id` | `{your_id}` |
| `routing_prefix` | `/f/{your_id}` |
| Landing route | `/f/{your_id}` |
| App mount | `/f/{your_id}/app` |

---

## App Mount

Shell contract: **`/f/{foundup_id}/app`**. State current hosting (pfMALL mount, external, or not yet deployed).

---

## AI Capability Hooks

Contract surface (implementation staged): `get_status`, `get_context`, `navigate`, `launch_capability`, shell handoff/return — see `FOUNDUP_AI_HOOKS_AND_DAEMON_SURFACE_CONTRACT.md`.

---

## DAEmon Outputs

Per **WSP 91** (when DAEMON workers attach): health status, last action, error state, recommended next action, queue/work state, telemetry scoped by `foundup_id` / `data_namespace`.

---

## Data / Telemetry Namespace

| Field | Value |
|-------|-------|
| `foundup_id` | `{your_id}` |
| `data_namespace` | `idb_{your_id}` or manifest field |
| Tenant bounds | Cache, storage, telemetry stay tenant-scoped per WSP 104 |

---

## WSP References

- **WSP 91** — DAEMON observability (`WSP_knowledge/src/WSP_91_DAEMON_Observability_Protocol.md`)
- **WSP 104** — FoundUp route namespace (`WSP_knowledge/src/WSP_104_FoundUp_Route_Namespace_and_Tenant_Isolation_Protocol.md`)
