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
- `public/member/` is the Clerk-admitted member PWA. Its detailed
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
| AutoPost Live mode and creator live-session service | Specified, not implemented | External AutoPost product/media adapter; separately authenticated durable creator backend |
| Provider-confirmed live catalog projection | Planned | Scoped backend observation; public-safe fields only |
| OpenClaw policy or worker authority in browser | Prohibited | Backend control plane |
| Hermes execution in browser | Prohibited | Governed worker plane |
| Protected decision finality by AI | Prohibited | Human review |

## Primary interfaces

See [INTERFACE.md](INTERFACE.md) for Python exports, HTTP routes, mutation
boundaries, and the RedDog integration seam.

## AutoPost private item capture (updated 2026-10-23)

For Shop clothing, GetK-style item evidence and multiple original photographs,
start with [AUTOPOST_ITEM_CAPTURE_HANDOFF.md](AUTOPOST_ITEM_CAPTURE_HANDOFF.md).
AutoPost remains the external capture/media owner. The intended path is private
local item draft, authenticated shared-media attachment, then a permitted item
projection inside this same Mall. Public Shop presentation is undecided.

The local draft types and integration obligations are specified; grouping UI,
group persistence, authenticated transfer/private writer and garment projection
remain unimplemented. The existing public GotJunk API and static media paths
must not receive private drafts. The [roadmap](ROADMAP.md#private-item-capture--2026-10-23)
names the next bounded slice; [doc_index.json](doc_index.json) makes this handoff
discoverable without claiming semantic-index activation.

## Mobile creator studio planning (updated 2026-10-18)

The intended outcome is a creator selecting Live in AutoPost, appearing in Play,
recovering from tested network interruptions and reusing a valid input for the
next show. [AutoPost](https://github.com/FOUNDUPS/autopost) already owns browser
camera/mic capture, local recording, review and operator-owned YouTube file upload.
Its proposed Live mode needs a continuous media adapter. The first proof evaluates
foreground WebRTC through an authenticated relay; native media integration follows
if device evidence justifies it. Mall owns discovery/playback projection, not the
camera. Existing upload and channel-specific automation do not establish a general
durable creator live service.

0102 consumes this bounded documentation collection before proposing a build:

- [Mobile studio contract](../docs/mobile_studio/PFMALL_MOBILE_STUDIO_CONTRACT.md):
  pain, AutoPost reuse/ownership, logical operations and acceptance criteria.
- [AutoPost Live audit and roadmap](https://github.com/FOUNDUPS/autopost/blob/main/ROADMAP.md#phase-4b--autopost-live-mode-planned):
  product-owned mode, capture/transport gaps and staged phone proof.
- [YouTube API constraints](../docs/mobile_studio/PFMALL_CREATOR_LIVE_API_CONSTRAINTS.md):
  dated quota, input reuse, OAuth, eligibility, recovery and playback constraints.
- [Machine outcome](../docs/mobile_studio/mobile_studio_outcome.v1.json): proposed
  slices, obstacles, unknowns and measurable results; no runtime admission.
- [Document manifest](../docs/mobile_studio/doc_index.json) and
  [documentation execution receipt](../docs/mobile_studio/wsp97_execution_receipt.json).

The phase sequence is in [ROADMAP.md](ROADMAP.md). Actual creator/channel access,
mobile behavior and provider calls remain unverified. No route, FoundUp identity,
payment system or deployed service is added by these documents.

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

## GotJunk listing read slice (2026-10-12)

Mall now contains a independently reviewable public-only GotJunk item projection
and `GET /pfmall/listings/search`. The endpoint defaults to **503** until
an independently secured publication-evidence provider is installed server-side;
it must not read raw legacy captures as public. `gotjunk_001` and
`/f/gotjunk_001` remain stable. No provider deployment, media storage
selection, browser search hookup, or production cutover is included.
See [ownership, tests and migration gates](GOTJUNK_LISTING_READ_SLICE.md).

## Second slice: privileged read adapter (2026-10-12)

`firestore_listing_provider.py` provides an **opt-in** server-injected
Firestore approval reader. It performs a separate reviewed-approval and
legacy-item join, checks owner/FoundUp and exact source revision, and returns
only evidence for the existing Mall public projection. It has no writes,
automatic SDK startup or deployment. Missing reviewer service, IAM and
configured provider mean live listings remain unavailable, not published.
