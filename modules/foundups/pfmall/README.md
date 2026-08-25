# p.fMALL Platform Layer

**Status**: Implemented platform shell with bounded read surfaces; resident RedDog integration is not implemented here.
**Entity type**: Platform layer, not a FoundUp and not an OpenClaw instance.

## Purpose

p.fMALL is the discovery and interaction shell for FoundUps and media. This
module owns manifest discovery, catalog projection, route resolution, optional
state-overlay presentation, static shell assets, and policy objects used by the
member Mall. It does not own a model, a durable RedDog conversation, worker
execution, or FoundUp business logic.

## Implemented surfaces

- `shell_core.py` validates `foundup_manifest.json` records, builds the catalog,
  resolves shell and `/f/{foundup_id}` routes, and merges advisory state
  overlays without overriding manifest identity.
- `api.py` exposes a stable read-only Python adapter for catalog listing,
  FoundUp lookup, and route resolution.
- `http_api.py` exposes an unauthenticated development/read surface and static
  shell UI through FastAPI.
- `member_catalog_export.py` explicitly generates
  `public/member/mall-catalog.json`; generation is a write operation and is
  never performed by the read API.
- `member_presentation.py` owns UI-only presentation overrides.
- `content_load_policy.py` defines bounded load-policy data contracts; it does
  not load content.
- `verification_gap_guard.py` allows advisory anomaly surfacing and blocks AI
  finality for protected decisions.
- `public/member/` is the admitted-user Firebase/PWA surface. Its detailed
  browser contract remains in `public/member/INTERFACE.md`.

## RedDog, OpenClaw, and Hermes boundary

The current browser concierge is a shell-local FAQ IIFE: it makes no network
call and is not an AI runtime. The `pfmall-control-dispatcher.js` message bridge
can control existing Mall presentation APIs, but it is not a conversation
transport and grants no resident identity, model credential, durable-session,
work-order, OpenClaw-policy, or Hermes-execution authority.

A production RedDog connection must arrive through a separately authenticated
adapter. RedDog/0102 owns the continuous product identity and governed
conversation state; OpenClaw supervises policy/control-plane admission; WRE
owns repository/process execution and verification; Hermes receives bounded
admitted leaf jobs. The browser remains an untrusted thin client. No text or
`postMessage` field can create those authorities.

## Current truth boundaries

| Capability | Status | Authority |
|---|---|---|
| Manifest discovery and validation | Implemented | Static manifest |
| Catalog/tile/route reads | Implemented | p.fMALL shell |
| Optional state overlay | Implemented contract | Advisory provider data |
| Member Mall UI and browser control dispatcher | Implemented | Presentation only |
| Shell-local RedDog FAQ concierge | Implemented legacy shim | Static guidance only |
| Authenticated resident RedDog conversation adapter | Specified, not implemented in p.fMALL | RedDog backend |
| OpenClaw policy or worker authority in browser | Prohibited | Backend control plane |
| Hermes execution in browser | Prohibited | Governed worker plane |
| Protected decision finality by AI | Prohibited | Human review |

## Primary interfaces

See [INTERFACE.md](INTERFACE.md) for Python exports, HTTP routes, mutation
boundaries, and the RedDog integration seam.

Canonical architecture documents remain under `modules/foundups/docs/`:

- `PFMALL_SHELL_CONTRACT.md`
- `PFMALL_FOUNDUP_MANIFEST_SCHEMA.md`
- `PFMALL_ROUTING_DISCOVERY_MODEL.md`
- `PFMALL_STATE_OVERLAY_CONTRACT.md`
- `PFMALL_DATA_ISOLATION_MODEL.md`
- `PFMALL_EXTERNAL_FOUNDUP_ROUTE_CONTRACT.md`
- `PFMALL_DEVICE_MODEL_ROUTING_CONTRACT.md`

## Verification

```powershell
python -m pytest modules/foundups/pfmall/tests -q
python -m pytest holo_index/tests/test_tier0_retrieval_hardening.py -q
python modules/infrastructure/wre_core/scripts/generate_test_registry.py --check
```

The Holo owner-query path must also report `ok=true`, `freshness=CURRENT`, and
`index_gap_detected=false` after a merged generation is rebuilt and activated.
Queries never repair or reindex the store.

## Known structural debt

This is a legacy flat Python package: source files are at the module root and
the module has no `src/`, `memory/`, or module-local `requirements.txt` yet.
That WSP 49/60/12 debt is recorded in [ROADMAP.md](ROADMAP.md). It must be
handled as a separate import-compatible migration, not hidden by this Tier-0
documentation repair.
