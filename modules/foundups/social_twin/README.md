# Social Twin FoundUp

## Purpose
`social_twin` is the FoundUp productization path for the workflow we are already
prototyping internally:

- scan social feeds for aligned opportunities
- rank and queue posts for human review
- discuss and refine drafts in a lightweight control surface
- approve one action at a time
- execute replies, likes, reposts, and follow-up scheduling through existing
  platform automation

The first operating surface is LinkedIn, with Discord/Telegram as the review
and approval plane.

## Architecture Decision
This FoundUp should run as one product with two core 0102 roles:

1. `orchestrator_0102`
   - scans
   - ranks
   - builds the queue
   - manages approval state
   - chooses voice/entity/target

2. `engager_0102`
   - executes one approved action at a time
   - calls existing DOM/platform adapters
   - records outcome, amplification, and follow-up state

Optional later role:
- `amplifier_0102`
  - likes
  - repost scheduling
  - delayed follow-up checks

This is better than one overloaded 0102 because the control plane and action
plane have different risk profiles, runtime needs, and observability needs.

## Runtime Positioning

### What should run where
- `OpenClawDAE`: commander ingress and routing
- `Discord/Telegram`: human review and approval surface
- `LinkedIn/X/... adapters`: deterministic execution surface
- `HoloIndex + publishing memory`: doctrine and target retrieval
- `Qwen/OpenClaw/remote LLM`: orchestrator drafting and ranking assistance

### What should not be collapsed into one runtime
- feed ranking and live browser execution
- approval state and mutation side effects
- voice/chat interface and DOM automation

The orchestrator may use model-heavy reasoning. The engager should be as
deterministic as possible and use models only for bounded drafting fallbacks.

## Existing Repo Seams
- OpenClaw control plane:
  - `modules/communication/moltbot_bridge/src/openclaw_dae.py`
- Discord/Telegram channel path:
  - `modules/communication/moltbot_bridge/docs/CHANNEL_SETUP.md`
- Voice/local chat:
  - `modules/infrastructure/cli/src/openclaw_voice.py`
  - `modules/infrastructure/cli/src/openclaw_chat.py`
- LinkedIn feed scan + draft + execute:
  - `modules/infrastructure/browser_actions/src/linkedin_actions.py`
  - `modules/platform_integration/linkedin_agent/docs/LINKEDIN_DIGITAL_TWIN_FLOW.md`
- Article/account memory:
  - `modules/platform_integration/linkedin_agent/data/linkedin_publishing_map.json`
  - `modules/platform_integration/linkedin_agent/src/content/publishing_router.py`

## Scope of This PoC Module
- codify the control-plane vs action-plane split
- define queue and approval contracts
- define the FoundUp roadmap
- keep implementation additive and platform-first

## Out of Scope in This PoC
- full end-user hosted SaaS
- universal multi-platform execution
- remote voice synchronization from phone to local browser
- autonomous multi-agent reply swarms without human approval

## Status
- Phase: PoC architecture lock
- Version: 0.1.0
- Last updated: 2026-03-13

---

## Route Namespace

Canonical contract: `modules/foundups/docs/FOUNDUP_AI_HOOKS_AND_DAEMON_SURFACE_CONTRACT.md`. Routing follows **WSP 104** (`/f/{foundup_id}`).

| Field | Value |
|-------|-------|
| `foundup_id` | `social_twin` |
| `routing_prefix` | `/f/social_twin` |
| Landing route | `/f/social_twin` |
| App mount | `/f/social_twin/app` |

---

## App Mount

Shell contract: **`/f/social_twin/app`**. PoC stage — control plane via Discord/Telegram; pfMALL mount pending.

---

## AI Capability Hooks

Contract surface (implementation staged): `get_status`, `get_context`, `navigate`, `launch_capability`, shell handoff/return — see `FOUNDUP_AI_HOOKS_AND_DAEMON_SURFACE_CONTRACT.md`.

---

## DAEmon Outputs

Per **WSP 91** (when DAEMON workers attach): health status, last action, error state, recommended next action, queue/work state (scan queue, approval state, engagement execution), telemetry scoped by `foundup_id` / `data_namespace`.

---

## Data / Telemetry Namespace

| Field | Value |
|-------|-------|
| `foundup_id` | `social_twin` |
| `data_namespace` | `idb_social_twin` |
| Tenant bounds | Queue state, approval records, engagement logs — all tenant-scoped per WSP 104 |

---

## WSP References

- **WSP 91** — DAEMON observability (`WSP_knowledge/src/WSP_91_DAEMON_Observability_Protocol.md`)
- **WSP 104** — FoundUp route namespace (`WSP_knowledge/src/WSP_104_FoundUp_Route_Namespace_and_Tenant_Isolation_Protocol.md`)
