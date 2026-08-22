# p.fMALL Interface

**Contract status**: Current implementation truth as of 2026-08-23.
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

This FastAPI surface has no authentication. It is read-only except for
process-local lazy shell caching and is not a production authority boundary.
Any public deployment requiring private catalog data must add authentication
outside this module before admission.

## Explicit write surface

`export_mall_catalog(output_path=..., shell=None) -> Path` is a separate,
explicit generation command. It writes the projected member catalog and is not
called by catalog reads or Holo queries.

## Browser/member interface

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
