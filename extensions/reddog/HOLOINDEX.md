# HoloIndex - reddog

Local retrieval manifest for the RedDog extension thin-client lane.

## Source Files (Tier 0 recall targets)

- `extension.js` - main extension entry; Copy MD, Run Trace, Work Trail, redaction handoff
- `holoindex_generation_bound_query.js` - owner-receipt acceptance, semantic-bucket replacement, and generation metadata
- `package.json` - Node manifest and version

## Bridge (cross-path recall)

- `scripts/advisory_model_once.py` - OpenRouter bridge and redaction gate (repo root)
- `scripts/reddog_holoindex_owner_query_once.py` - authenticated generation-bound owner query bridge (repo root)
- `modules/communication/moltbot_bridge/src/reddog_public_policy.py` - public guest origins, caps, and unsigned Lick Verification input; no identity or private authority
- `modules/communication/moltbot_bridge/src/reddog_public_session_gate.py` - injected AgentDB SQLite guest quotas, expiry, replay, withdrawal and concurrency accounting
- `modules/communication/moltbot_bridge/src/reddog_public_http.py` - opt-in public-only ASGI router; unmounted until host/responder/ingress proof

## Documentation

- `ARCHITECTURE.md` - canonical RedDog/0102 identity boundary: 012 <-> RedDog surface/proxy <-> 0102 digital twin/orchestrator; attention firewall and recursive co-development invariants
- `docs/REDDOG_PUBLIC_SURFACE_ADMISSION.md` - bounded guest admission for AutoPost, foundups.com and eSingularity.ai; implementation evidence, 3V Verification linkage and live activation gaps
- `docs/prompts/WSP97_REDDOG_PUBLIC_SURFACE_REMOTE_PROMPT.md` - next host/mobile/site integration work order; HoloIndex requery/repair, existing database/host reuse, no knowledge-answer unlock
- `docs/CONTACT_MEMORY_ARCHITECTURE.md` - principal-scoped relationship memory: encrypted capture, entity/event graph, semantic retrieval, provenance, AutoPost ingest, Breadcrumb/Brain/Memex projection linkage, and Lick encounter/identity linkage
- `docs/MOSH_PIT_ACTIVITY_MEMORY_ARCHITECTURE.md` - Mosh Pit as a reverse-chronological projection over Breadcrumbs + Brain/Memex; actor attribution, open-loop recall, Git evidence, STT normalization, disclosure views, and RedDog status/history retrieval contract
- `docs/MEMEX_PROJECTION_EMITTER_ARCHITECTURE.md` - secure read-only projection/emitter layer for RedDog/founder views; principal+FoundUp+disclosure authorization, deterministic JSON/Markdown rendering, sink isolation, and threat model
- `docs/prompts/WSP97_M2M_MEMEX_EMITTER_IMPLEMENTATION_PROMPT.md` - implementation work order: WSP_00 intake, WSP 97/HoloIndex ownership discovery, bounded M2M slices, fail-closed security tests, no parallel memory store, no external mutation authority
- `README.md`, `INTERFACE.md`, `ModLog.md`, `ROADMAP.md`
- `docs/REDDOG_EXTERNAL_ACCEPTANCE_BASELINE_PHASE1.md` - acceptance baseline pack
- `docs/acceptance/` - baseline artifact storage

## Symbols (high-value recall)

- `buildCopyMarkdown`, `buildRunTraceSection`, `holoIndexMetaFromBundle`, `evaluateTargetRecall`
- `isGenerationBoundHoloQueryAccepted`, `mergeGenerationBoundHoloResult`, `buildMetaFromBundle`
- `PublicPolicy`, `PublicSessionGate`, `PublicSurfaceBinding`, `lick_verification_evidence`

## Memory / history recall targets

- `docs/MOSH_PIT_WAVE_MVP.md` - activity-only expandable feed, open-source research, stakeholder access and exact candidate/live boundaries
- `modules/communication/moltbot_bridge/src/mosh_pit_projection.py` - local read-only candidate over authorized breadcrumb snapshots; no production source
- `modules/communication/moltbot_bridge/src/mosh_pit_render.py` - escaped, folded HTML over approved projection fields
- `modules/communication/moltbot_bridge/skillz/reddog_mosh_pit/SKILLz.md` - registered prototype activity curation discipline

When the principal asks "what have we done?", "where were we?", "what is still open?", "show the timeline", or equivalent, recall these before inventing a new memory surface:

- `modules/communication/moltbot_bridge/src/openclaw_memory_queries.py` - existing `query_past_work`, decision, Breadcrumb, and unresolved-work retrieval surfaces; canonical runtime extension point for unified FoundUp activity/timeline queries
- `modules/communication/moltbot_bridge/src/foundup_memex_current_state.py` - canonical FoundUp Memex current-state surface
- `modules/communication/moltbot_bridge/src/foundup_brain_current_state.py` - durable Brain consolidation component inside Memex; active/queued work + Breadcrumb state + verified outcomes
- `WSP_framework/src/WSP_60_Module_Memory_Architecture.md` - normative memory model; Breadcrumbs are multi-agent discovery/activity trails

Target composition:

```text
Breadcrumb history + Brain/Memex current/open state + relevant evidence
-> authorized Memex Projection Emitter
-> project-scoped Mosh Pit / compact status projection
-> RedDog / founder view
```

The emitter is a read-only projection service, not another memory store. Private event/evidence data remains outside the public repository and must be principal-scoped, disclosure-filtered, and fail-closed.
