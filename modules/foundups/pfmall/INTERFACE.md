# p.fMALL Interface

## 2026-11-25 — Optional member-card projection

VOTE's two reviewed records reuse the existing fixed field, HTML5 player branch,
search dock, queue and return state. The shared
[typed-media contract](../../../public/member/INTERFACE.md#2026-11-25--optional-vote-member-cards)
owns strict local asset admission, common-stage containment, image-animation
fallback diagnostics, reduced-motion and cleanup. VOTE starts in tiles; HPC's
theater/Home selection, YouTube guards and protected application entry remain
unchanged. Collection discovery does not authorize scores, voting or membership.

## 2026-11-25 — Scoped navigation and hidden selection candidate

Use the [current shared contract](../../../public/member/INTERFACE.md#2026-11-25--scoped-home-shared-theater-dock-and-hidden-selection)
for explicit scoped Home, one borrowed dock below the app queue, distinct
actions/contribution plus controls and selection-only next-hidden. State and
queue owners remain shared. Historical next/reveal and detached search records
below do not override this revision. Source implementation, controlled tests,
real media, independent review, device acceptance and release remain separate.

## 2026-11-23 — Clean video gestures and local DAEmon candidate

**IMPLEMENTED_CANDIDATE.** Shared owners now supply clean app video surfaces,
configurable right-swipe queue/reveal actions, full-height external gesture grip
and opt-in bounded current-tab DAEmon. See the [shared member interaction contract](../../../public/member/INTERFACE.md#2026-11-23--clean-video-gestures-and-local-daemon-candidate) and
[canonical media incident](MEDIA_PLAYBACK_INCIDENT_HPC.md).
Native provider controls and ordinary desktop theater remain; physical phone
and production acceptance are open. No model, mic or backend service is added.

## 2026-11-22 — Floating controls, preferences and camera contract

Candidate additions to the existing shared owners, pending final qualification:

- `mallVideoPlayer.openPinchDestination()` selects WikiTube (default) or app
  Full Video from `pinchOutDestination`. `requestPlay()` refuses hidden playback
  and reuses the existing provider recovery command. These APIs do not request
  native YouTube/iOS fullscreen.
- `pfmall_video_options_v1` preserves existing fields and gains validated
  `pinchOutDestination` (`wikitube`/`full-video`), optional `pinchInDestination`
  and optional `swipeUpDestination` (`wikitube`/`mall`). Old records migrate on
  read without writes. Unselected return choices retain existing behavior.
- The persistent app-owned grip/side edges support drag and application gestures
  without overlaying the iframe. Keyboard arrows move the floating card; Enter
  opens shared Video actions. Right tuck pauses and makes the player inert;
  its video-height rail restores the same paused provider. Reveal-on-selection
  remains a separate existing preference.
- `mallVideoProjection.cameraDestination()` produces the canonical public
  AutoPost URL. Only bounded canonical HTTPS Mall callers become `return_to`.
  No account, token, media bytes or private state crosses the handoff.
- Red Dog opens the canonical conversation owner; unavailable builds show an
  in-page return control. No alternate navigation or false microphone capture
  is substituted for an unavailable AI service.

See [the incident](MEDIA_PLAYBACK_INCIDENT_HPC.md) for provider, deployment and
device limits. AutoPost owns its separately tested return parser and footer.

## 2026-11-21 — v26 phone candidate (unreleased)

Build v25 remains the frozen comparison at its existing preview. Build v26 uses a
separate source receipt and preview channel; no production redirect or release is
part of this change. Phone-layout browser fixtures are separate from physical
Safari and installed-PWA evidence. The principal has opened v25 on an iPhone 11;
v26 physical playback, audio and uninterrupted three-clip transitions are NOT_RUN.

The shared pre-Fractal shell keeps one provider and one actionable bottom Search
Dock while entering/leaving WikiTube or app Full Video. A fully hidden parked
player pauses. Native YouTube controls and native fullscreen are not intercepted.
The leading + retains discovery controls, AutoPost and Video Options; the trailing
+ is Add FoundUp on Play and Add Video in the HPC pilot. Video preferences affect
app controls and qualified visible playback, never promise provider autoplay.

Play public browsing and static FoundUp details correspond to the currently
available public discovery surfaces. The requested future levels 1–2 public /
level 3+ member policy is not a deployed graph ACL. The separate Fractal runtime
`22374b161570b2cd0e265e1c2b8c1009fb599394` is not imported. Contributions remain
unavailable until an authoritative service verifies current identity, membership
and per-FoundUp editor permission (012 initially for HPC). A successful existing
invite check only restores a manual review; it does not publish or grant editor
permission. No six-month checkout is activated. Cross-origin HPC-to-Play
contribution return is not connected and fails closed.

The existing same-origin Play `/?signin=required` gate and `/sso-callback/` are
preserved. Valid legacy `enter` links resolve public metadata rather than being
silently intercepted as a Mall view. Auth/callback, deep links and existing invite
flows are excluded from public landing normalization. Apex-to-Play routing is a
pure tested plan only; no live apex redirect is installed.

The full HPC banner opens <https://hasan4speaker.com/>. The distinct Mall return
opens Play; Voice Your Opinion / Contact Congress retains
<https://vote.mtrout.com/contact>. Vote/Contact whole-banner return links to HPC
remain a different navigation contract.

Browse AI is a separate compatibility pilot: no model is preloaded, no automatic
cloud fallback, and no model capability is claimed. The explicit, checksum-bound
41-byte WASM addition fixture is not an AI model. Actual model selection/download
and WebGPU qualification remain later work, including same-runtime Safari/PWA
checks. This dependency does not block the phone UI candidate.


**Contract status**: Implemented shell interfaces with later dated slices;
mobile creator seam below is specified only (updated 2026-10-18).
**Boundary**: p.fMALL is a platform/presentation layer, not a FoundUp, model
host, OpenClaw instance, or Hermes worker.

The [member shell](../../../public/member/INTERFACE.md#public-video-projection)
owns the shared video UI. The [HPC media incident](MEDIA_PLAYBACK_INCIDENT_HPC.md)
records provider and layout constraints, reproduction and regression evidence.

## Fractal projection seam — specified 2026-11-19

The [master architecture](../docs/FOUNDUPS_MASTER_ARCHITECTURE.md#fractal-views-of-the-same-work)
and [navigation contract](../docs/PFMALL_MALL_NAVIGATION_CONTRACT.md#13-fractal-work-navigation)
own the proposed shared graph projection. This section adds no Python export,
HTTP route or browser command. Reuse the recovered graph schema and projector
when their pinned evidence is available; missing graph artifacts remain an
explicit gap in the [documentation audit](../../../docs/audits/architecture/PFMALL_FRACTAL_DOCUMENTATION_AUDIT_20261119.md).

The projection must retain a component's stable ID across views and distinguish
its primary containment from dependency, reuse and work relationships. Record
the graph snapshot revision separately from the artifact's source commit or
base commit plus overlay digest. An unavailable pinned artifact stays
unavailable rather than silently opening current main. Functionality and
integration evidence are independent; census inclusion does not require either
to be proven.

Public projections expose approved fields and artifacts. Architect projections
may link private PC paths or receipts only within authorized scope. Navigation
retains the caller, lens and selection and rechecks access on return. A Tools →
Benchmark path or builder selection is a navigation target, not execution or
mutation authority. Existing read/write boundaries below remain authoritative.

## Python package exports

`modules.foundups.pfmall` exports the following shell-core surface:

- `create_pfmall_shell(search_paths=None, state_provider=None) -> PfmallShell`
- `discover_manifests(search_paths) -> list[Path]`
- `load_manifest(source) -> FoundUpManifest | None`
- `validate_manifest(data) -> list[str]`
- `resolve_route(path, catalog) -> RouteTarget`
- `build_foundup_tile(manifest, overlay) -> FoundUpTile`
- `FoundUpManifest`, `FoundUpTile`, `FoundUpStateOverlay`
- `RouteKind`, `RouteTarget`, `ShellCatalog`, `ShellConfig`, `PfmallShell`
- `VALID_READINESS`, `VALID_CATEGORIES` (`media`, `ai-education`, `ai-research`, `startup`, `community`, `marketplace`, `games`, `science`, `thought-leadership`, `infrastructure`)

`load_manifest(source)` validates required identity, tier, lifecycle, category,
readiness, and WSP 104 `routing_prefix` / `data_namespace` rules, coalescing
explicit JSON `null` values on optional string/list/dict fields to safe empty
defaults so valid manifests never expose `None` on typed string/collection
attributes.

The package also exports the read-adapter surface:

- `get_default_shell() -> PfmallShell`
- `list_foundups(category=None, shell=None) -> list[dict]`
- `get_foundup(foundup_id, shell=None) -> dict | None`
- `resolve_foundup_route(path, shell=None) -> dict`
- `reset_default_shell() -> None` — test-only process-cache reset
- `DEFAULT_SEARCH_PATHS`

`get_default_shell()` lazily boots and caches one process-local shell. This is
runtime convenience, not durable state or cross-process authority.

## Optional server profile

`requirements-server.txt` includes the HTTP profile plus minimal pinned Uvicorn,
h11 and click. Use its ordinary CLI with the isolated `intake_host:create_app`
factory, explicit app directory and resource/trust options in README. No new
launcher or public API is added. Real-loopback tests identify the child and its
port0 listener, exercise HTTP draft/rejection/body limits, and reap the process.
They establish neither container/cloud readiness, a real Clerk identity nor OS
confinement. The imported development app still requires real tracked static files.

## Shell-core invariants

1. A manifest is static identity and remains authoritative for identity,
   routing, tier, lifecycle declaration, and capabilities.
2. A state overlay is optional and advisory. Provider failure degrades to a
   manifest-only tile; overlay values never rewrite the manifest.
3. Route resolution returns one of `shell`, `foundup`, or `not_found`.
4. `/f/{foundup_id}` is a public routing identifier, not authentication or
   authorization.
5. Invalid or unreadable manifests are omitted; no synthetic valid record is
   fabricated.

## HTTP read surface

`modules.foundups.pfmall.http_api:app` exposes:

| Method and path | Result |
|---|---|
| `GET /pfmall/health` | Shell boot state and catalog count |
| `GET /pfmall/catalog` | Catalog tiles; optional `category` query |
| `GET /pfmall/foundups/{foundup_id}` | One tile or HTTP 404 |
| `GET /pfmall/resolve-route?path=...` | Route result |
| `GET /pfmall/tile-graph?scope=public_mall\|012_architect` | Public projection (with `ETag` / `304`) or 012-authenticated architect graph |
| `POST /pfmall/tile-graph/patches` | Default 503; explicit server `ClerkIntakePolicy` + `TileGraphAuthPolicy` + `TileGraphStore` |
| `GET /pfmall/ui/...` | Static shell UI |
| `GET /pfmall/static/...` | Static assets |
| `GET /f/{foundup_id...}` | HTTP 307 to the shell handoff UI |

These GET routes have no authentication. They are read-only except for
process-local lazy shell caching and are not a production authority boundary.
Any public deployment requiring private catalog data must add authentication
outside this module before admission.

### Explicitly configured member draft intake — 2026-10-26

`POST /pfmall/proposals` is a separate authenticated draft surface. By default
it returns503 `{"detail":"intake_unavailable"}`. Only the server may set
`app.state.clerk_intake_policy` to the exact immutable `ClerkIntakePolicy` type
from `foundup_genesis.clerk_intake`; configuration accepts issuer, nonempty tuple
of HTTPS frontend origins, and a single canonical SubjectPublicKeyInfo
RSA2048–4096 public PEM (CRLF or omitted final newline supported; extra documents/
private material/trailers rejected). No environment, body,
UID, invite flag or forwarded host selects this policy. Optional dependencies
are listed in this module's requirements; ordinary unconfigured imports do not
load JWT/crypto packages. The existing GET contracts remain public.

Send `Content-Type: application/json`, one `Authorization: Bearer <session>` and
one matching allowed `Origin`. Cookies and HMAC invites cannot authenticate this
route. Duplicate security headers, unsupported content/encoding, malformed or
oversized declared length reject400. Actual streamed bytes are capped at16KiB
before decoding, with a5-second application read deadline; these are not TCP,
OS memory, hard CPU or proxy admission guarantees. UTF-8 charset may be explicit.
The complete existing LaunchRequest allowlist runs before the verifier.

The genesis-owned adapter verifies real RS256 signatures against the configured
public key and exact issuer/Origin/azp, signed v2 user/session claims, required
integer iat/nbf/exp, zero clock skew and TTL<=120seconds. Any aud, sts or act claim
is unsupported and rejected; this profile has no audience or impersonation mode.
All authentication failures return401 `{"detail":"not_authorized"}`; body/wire
failures return400 `{"detail":"invalid_request"}`. Responses use `no-store`.
There is no online session-revocation or membership lookup; later privileged
claim use must establish fresh current-session/revocation evidence separately.

Success201 is `{"status":"DRAFT_ONLY","genesis_envelope":{...}}` from the existing
mapper, with IDEA/UNBOUND and external_repo_requestedFalse. requested_by is a
domain-distinct hash of the verified issuer and case-sensitive subject, not a
body handle; raw subject/session/bearer/key are not returned. This is a returned
draft, not durable nomination/admission, repository/issuer control, registry or
catalog publication, work dispatch, token creation, voice or model execution.
No public deployment is established. The backend policy and real member-token
smoke test, current membership/revocation, challenge+atomic receipt owner,
rate/abuse limits and release qualification remain separate prerequisites.

### Isolated proposal host factory — 2026-10-26

`modules.foundups.pfmall.intake_host.create_app()` constructs a separate FastAPI
application with only `POST /pfmall/proposals` and `GET /healthz`. OpenAPI/docs,
catalog/static and FoundUp handoff routes are absent. The POST is the same
`http_api.foundup_proposal` function; policy lookup uses `request.app.state`,
keeping factory instances and the development app independent.

Trusted server environment must set `PFMALL_CLERK_POLICY_FILE` to an absolute
regular-file target. Read at most16KiB UTF-8 JSON; require a unique-field object
with exactly `issuer`, `authorized_parties` (list) and `public_key_pem`. Convert
parties to the existing tuple policy and reuse canonical public-RSA validation.
Missing/unreadable/oversized/invalid configuration stops construction with
`RuntimeError("intake_configuration_invalid")`, without values or fallback policy.
This is administrator configuration, never selected by a request/header/cookie.

`GET /healthz` returns200 `{"status":"ready"}` with `Cache-Control: no-store`
after valid local configuration. It is not an online identity/provider probe.
There is no dotenv/JWKS request or credential/key material generation. Local file
integrity/custody remains the administrator's obligation; no sealed inode claim.
Existing draft-only authentication, wire/body bounds and generic failures apply.
Container/serving profile, cloud IAM/cost limits, real session, same-origin
browser, abuse/revocation and release qualification remain required. This factory
does not persist drafts, establish project ownership or grant execution/tokens.

## Explicit write surface

`export_mall_catalog(output_path=..., shell=None) -> Path` is a separate,
explicit generation command. It writes the projected member catalog and is not
called by catalog reads or Holo queries.

`export_fractal_tile_graph(output_path=..., store=None, repo_root=...) -> Path`
writes the schema-validated `public_mall` projection to
`public/member/fractal_tile_graph.public.json` (from live `TileGraphStore`
state when supplied, or built directly from tracked repository files).

### Fractal Tile Graph, Authenticated Atomic Patch API & Sprint 2 Benchmark Hierarchy

- **Schemas**: `schemas/fractal_tile_graph.schema.json` (`fractal_tile_graph.v1`)
  and `schemas/tile_graph_patch.schema.json` (`tile_graph_patch.v1`).
- **Dual scoring & graph builder (`fractal_tile_graph.py`)**:
  `compute_wsp15_canonical`, `compute_reusability`, `compute_mall_rescue_score`,
  `validate_tile_graph`, `project_public_tile_graph`, `build_repo_fractal_tile_graph`,
  and typed `dag_edges` (`calls`, `reads_from`, `evaluates`, `runs_through`,
  `produces_receipt`, `verified_by`). Tracks post-census `HEAD` files cleanly as
  `VERIFIED_AT_TRACKED_HEAD_REVISION` separately from feature-local files.
- **Atomic SQLite WAL Store (`tile_graph_store.py`)**: `TileGraphAuthPolicy`,
  `TileGraphStore`, optimistic `base_graph_etag` concurrency (`409`), idempotent
  `patch_id` replay, tenant/architect scoping, WSP 71 leak checks, and
  `regenerate_from_catalog` replay survival.
- **Context Helpers (`tile_graph_context.py`)**: `get_breadcrumbs`,
  `build_tile_context`, `search_tiles`, `get_rescue_queue`, `get_cobuilding_context`,
  `build_reddog_tile_briefing`, `query_tools_benchmark_readback`, and `walk_fractal_path`.

## Browser/member interface

`play.foundups.com` enters the shared browser shell as the open guest p.fMALL
discovery landing across all catalog FoundUps without Clerk or Firestore
account reads, while `hpc.foundups.com` enters as a single-FoundUp guest video
projection (returning to `play.foundups.com`). Entering any FoundUp from
`play.foundups.com` (`Enter FoundUp` on tiles, floating/WikiTube player,
quick-view cards, or direct `/member/foundup.html` / `/f/{id}/app` paths)
passes through the `foundups.com` Member Portal
(`https://foundups.com/member/?enter={foundup_id}`), enforcing Clerk sign-in,
invite validation, and `@username` claim before opening the admitted FoundUp
entry view. On `foundups.com`, `/members` redirects to `/member/` and the HPC
query mounts its projection after member admission. The public video catalog
contains the reviewed lane and the aggregate catalog contains its discovery
card. WSP 104 app handoff and server checks own capability authorization.
See [HPC's interface](../hpc/INTERFACE.md).

The ordinary invited Mall uses the adaptive poster grid on fresh wide
fine-pointer visits. It hands the selected lane to the shared full player
and keeps the grid's scroll and focus through dismissal. Saved layouts
take precedence. The [navigation contract](../docs/PFMALL_MALL_NAVIGATION_CONTRACT.md#46-desktop-poster-browsing)
defines how desktop poster selection, category rows and card quick views work.

The static homepage's FX anchor targets the existing `/f/` public directory.
Its project/ticker search consumes only the scope-free public projection; no
Python/HTTP API or router is added. See
[`Public FX directory`](../../../public/member/INTERFACE.md#public-fx-directory--2026-10-25)
for matching and truth boundaries. A displayed symbol is not a chain receipt,
price, liquidity or trading capability.

The authoritative member-runtime details are in `public/member/INTERFACE.md`.
The browser control dispatcher accepts bounded presentation commands and emits
truthful `ok`, `denied`, or `error` responses. It must use the published Mall
runtime APIs and must not fall back to direct DOM selectors or fabricate
success.

The dispatcher is not the resident RedDog conversation interface. It carries
no durable conversation, identity proof, model credential, work order,
OpenClaw policy, or Hermes execution authority.

The distinct public guest client at `public/js/reddog-public-client.js` accepts
only an explicitly configured same-origin `/api/reddog/public` root. Its member
adapter exposes availability and opens a native consent dialog without issuing
a request. A turn uses the canonical public nonce/revision/message contract and
may add only the validated public route `foundup_id`; account and private context
are never payload fields. Session and transcript state are cleared when the
account/selection binding revision changes. This guest API has effect ceiling
`NONE` and is not the authenticated resident interface below.

## RedDog integration seam

A future production adapter may translate authenticated RedDog results into
the existing browser control contract. Admission order is:

```text
untrusted browser intent
  -> authenticated resident RedDog conversation boundary
  -> OpenClaw policy/admission
  -> Hermes execution only for an admitted work order
  -> bounded result/projection back to p.fMALL
```

The following rules are mandatory:

- PFMall does not infer resident identity or durable scope from browser text,
  local storage, URL parameters, or `postMessage` fields.
- The current FAQ concierge must not be described as AI or as OpenClaw.
- The browser dispatcher must not be reused as the conversation transport.
- OpenClaw selects/governs work; Hermes executes admitted work. Naming an
  artifact or worker `Hermes` is not evidence of Hermes execution.
- RedDog must authenticate scope and re-check mutable state at the backend
  boundary; PFMall receives only the least-authority projection it needs.
- Local/browser models may advise or surface anomalies but cannot finalize a
  protected decision.

## Proposed mobile creator seam (updated 2026-10-18)

**SPECIFIED_NOT_IMPLEMENTED.** This section adds no callable endpoint or browser
command. The unauthenticated read API and presentation dispatcher cannot accept
creator credentials or perform broadcast writes.

The creator-facing Live mode belongs to external
[AutoPost](https://github.com/FOUNDUPS/autopost), which already owns capture and
recorded-file publishing. AutoPost composes the selected browser/native media
adapter; this Mall interface consumes the permitted observation/projection.
The foreground browser/relay proof and optional OBS contribution do not move
camera code, provider tokens or relay credentials into the Mall browser.

The [mobile studio contract](../docs/mobile_studio/PFMALL_MOBILE_STUDIO_CONTRACT.md)
defines logical `PrepareSession`, `CreateBroadcast`, `ResolveInput`, `BindInput`,
`StartLive`, `InspectSession` and `EndLive` operations for a future authenticated
adapter. It also specifies request identity, principal/channel scope, consent,
revision checks, durable reconciliation and uncertainty handling. Implementations
must independently verify every claim at the backend boundary.

An attended AutoPost browser can use a valid Google grant for a bounded REST
lifecycle proof. That proof has explicit expiry/reload limits and is not the
durable shared backend specified here. AutoPost's local author signature or Lick
receipt is not creator/channel authorization. Media export requires explicit
creator intent; local End remains effective if provider control is unreachable.

Play receives only an admitted public projection: creator identity, broadcast
ID, title, approved watch/embed URLs, observed lifecycle, freshness and archive
state. Tokens, ingest secrets and raw provider responses are excluded. Encoder
connectivity, active ingest, a live broadcast and successful player playback are
separate observations. Missing/stale evidence is unknown; a player-open event is
not proof of a publicly live show.

See the [API constraints register](../docs/mobile_studio/PFMALL_CREATOR_LIVE_API_CONSTRAINTS.md)
for channel/embedding eligibility and service limits, and the
[machine outcome](../docs/mobile_studio/mobile_studio_outcome.v1.json) for the
proposed handoff. A future implementation must update this interface with its
actual authentication, schema and transport after a bounded slice is admitted.

## Private AutoPost item attachment (specified 2026-10-23)

**SPECIFIED_NOT_IMPLEMENTED.** The
[item capture handoff](AUTOPOST_ITEM_CAPTURE_HANDOFF.md) defines the shared
ownership and acceptance contract. AutoPost's local `AutoPostItemDraft`
(`autopost.item-draft.v1`) groups original photo references under one item;
the type does not create a writer, transport, permission or callable route.

A future adapter in the existing platform service owner must authenticate the
principal, authorize the target FoundUp/item, validate uploaded bytes and bind
private media references server-side. Scoped draft/revision retries must be
idempotent; conflicts and partial failures remain visible. Mall may acknowledge
attachment only after trusted durable storage evidence exists.

`GET /pfmall/listings/search` remains public-only GotJunk discovery. It cannot
ingest these drafts or provide owner/private search. Static `/media/` and
`/member/media/` are not private media stores. Browser identity claims, a local
draft state or a GetK `public_browse` default cannot authorize publication.

No route is added by this specification. C1 local grouping, C2 authenticated
attachment and C3 private presentation are tracked separately in [ROADMAP.md](ROADMAP.md#private-item-capture--2026-10-23).

## Verification-gap guard

`verification_gap_guard.py` exposes advisory event and policy types:

- `ProtectedClass`, `AnomalyType`, `AgentAction`
- `VerificationGapEvent`, `BlockedActionResult`
- `is_protected_action`, `requires_human_review`, `block_protected_action`
- `create_gap_event`

Protected actions are fail-closed. Unknown actions are blocked. This module
does not implement fraud detection, payout execution, ledger writes, identity
suspension, or human-review finality.

## Content-load policy

`content_load_policy.py` provides `TileLoadState`, `ContentTrustSignal`,
`ContentLoadPolicy`, and `TileLoadContext`. These are policy/data contracts;
they do not fetch, render, or execute content.

## Failure and truth taxonomy

| Condition | Required result |
|---|---|
| Missing FoundUp | `None`, `not_found`, or HTTP 404 at the documented layer |
| Invalid manifest | Validation errors / omitted record |
| Overlay unavailable | Manifest-only result with unknown overlay values |
| Browser policy refusal | `denied` |
| Malformed/unknown browser command or unavailable API | `error` |
| Protected or unknown AI action | Blocked and routed to human review |
| Missing authenticated resident RedDog adapter | Feature unavailable; never shell-local authority |

## Canonical related contracts

- `modules/foundups/docs/PFMALL_SHELL_CONTRACT.md`
- `modules/foundups/docs/PFMALL_ROUTING_DISCOVERY_MODEL.md`
- `modules/foundups/docs/PFMALL_STATE_OVERLAY_CONTRACT.md`
- `modules/foundups/docs/PFMALL_DATA_ISOLATION_MODEL.md`
- `modules/foundups/docs/PFMALL_EXTERNAL_FOUNDUP_ROUTE_CONTRACT.md`
- `public/member/INTERFACE.md`

## GotJunk public listing discovery (first review slice, 2026-10-12)

`GET /pfmall/listings/search?q=...&category=...&limit=...` is an
**unauthenticated, public-only** read surface for `gotjunk_001`. The server
must supply a trusted `app.state.listing_evidence_provider` that independently
joins an item with a server-owned publication approval. No such production
provider is installed; unconfigured or failed lookup returns **HTTP 503**.
Cross-FoundUp and owner-scoped requests return **HTTP 403**. A configured
provider returns only approved public `source_item_id`, `foundup_id`,
`source_collection`, `title`, `category`, and `deep_link`; no
media URLs, private locations or arbitrary captured descriptions.

This endpoint is not the member JavaScript search feature, authenticated
private search, an upload service, or a deployment claim. Publication approvals
must not be imported from untrusted legacy client fields. See
[GOTJUNK_LISTING_READ_SLICE.md](GOTJUNK_LISTING_READ_SLICE.md).

## Server-injected GotJunk publication reader (second review slice)

`FirestoreGotJunkPublicationProvider(client, expected_project_id=...)`
(`firestore_listing_provider.py`) implements the existing
`ListingEvidenceProvider` for two **server-controlled** collections:
`gotjunk_items` and `gotjunk_public_approvals`. The latter is intentionally
not readable or writable through browser Firebase rules (default catch-all
deny). It must be independently populated by an authorized reviewer service,
not a seller-controlled status field. Reviews require matching FoundUp,
item/owner, reviewer distinct from owner, explicit `privacyReviewed=true`, fixed `fieldAllowlistVersion=public_listing_v1`, and exact source `updatedAt` revision.
Changes to source items automatically invalidate the approval read.

This adapter **does not** initialize Firebase credentials, create approvals,
configure `app.state.listing_evidence_provider`, install a production
publisher, or deploy. A trusted server bootstrap with explicit matching
project and IAM must inject the client and activate the provider after
security and deployment gates; otherwise HTTP search remains 503. Firebase
Admin client libraries and deployment configuration remain external.
