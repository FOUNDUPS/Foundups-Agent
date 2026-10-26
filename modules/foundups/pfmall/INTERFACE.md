# p.fMALL Interface

**Contract status**: Implemented shell interfaces with later dated slices;
mobile creator seam below is specified only (updated 2026-10-18).
**Boundary**: p.fMALL is a platform/presentation layer, not a FoundUp, model
host, OpenClaw instance, or Hermes worker.

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
- `VALID_READINESS`

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

## Linux image candidate

`Dockerfile.intake`: linux/amd64, fixed8080, nonroot10001:10001, exec-form
Uvicorn factory command and existing trust/resource options. Set the absolute
`PFMALL_CLERK_POLICY_FILE` to an independently administered readonly JSON mount;
the image contains no policy or credentials. Missing/invalid policy stops startup.
The public route contract remains exactly proposal plus minimal health.
`requirements-container.lock` is the Linux CPython3.12 runtime wheel closure;
it does not replace either optional profile or the umbrella requirements.
`PFMALL_TEST_CONTAINER_IMAGE` is a test-only opt-in requiring an immutable image
ID; ordinary tests keep the original process transport. Hosted qualification
uses readonly rootfs/policy, dropped capabilities, no-new-privileges,256MiB,
one CPU,64pids and127.0.0.1 host publication. Bridge networking permits egress.
Actual image/security/cloud/session acceptance is tracked separately; no deployed
service, new public API, repository admission or token authority is introduced.

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

## Browser/member interface

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
