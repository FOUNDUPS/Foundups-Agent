# foundups_mcp_bridge - ModLog

## 2026-08-18 - FastMCP SSE Server: Fail-Closed Auth & Termination Failure Propagation

- Enforced server-level fail-closed authentication: `AuthMiddleware` and `build_asgi_app` raise `ValueError` upon construction if `require_auth=True` and `auth_token` is empty; `mcp_server.py` CLI exits with code 1.
- Fixed termination failure propagation in `launch.py`: `_active_runtime` is NEVER cleared when `_terminate_runtime()` times out or fails, retaining lock and handle for truthfulness.
- Implemented `REMOTE_READ_ONLY_ALLOWLIST` restricting remote registration to 33 pure read-only perception tools; mutation/dispatch tools are strictly absent from FastMCP.
- Prohibited `?token=` query param auth to prevent secret leakage in logs; enforced Bearer header auth.
- Renamed RedDog context tool to `get_reddog_analysis_context` with truthful docstrings and `source="reddog_context"`.
- Hardened protocol canary to validate protocol negotiation, required tool inventory, absence of forbidden tools, and inner tool result envelope.
- Added comprehensive unit tests in `tests/test_mcp_server_sse.py` (11/11 passed).
  (WSP 22/34/50/80/96/97)

## 2026-08-16 - Zero-limit reconciliation

- Closed the internal flattening edge where `limit=0` admitted one candidate.
- Added a direct regression while preserving positive-K Tier-0 reservation,
  global ordering, schema, freshness, and authentication behavior. (WSP 22/97)

## 2026-08-16 - Bounded Tier-0 owner-result reservation

- Added query-aware reservation for existing generation-bound module-root
  README/INTERFACE evidence after global score ordering and path projection.
- Required explicit query intent plus one uniquely evidenced module; ambiguous
  or implicit queries preserve existing score order.
- Kept reservation bounded by the caller limit, excluded nested test docs, and
  preserved response schema, authentication, receipt, admission, and service
  lifecycle contracts. (WSP 22/50/60/84/97)

## 2026-08-15 - Repository-relative Holo owner evidence

- Extended the existing owner-response normalizer so physical hit paths under
  the proven authority root become repository-relative before response and
  receipt use; absolute outside-root evidence now fails closed.
- Extracted host-independent lexical projection into the bounded
  `holo_query_path_projection` helper. It covers backend aliases plus
  `path`/`file`/`location`, rejects POSIX, rooted, drive-relative, traversal,
  foreign-root, control-character, ADS, and device-path ambiguity, and
  deep-copies backend evidence before use.
- Preserved canonical numeric and code-symbol location descriptors only when
  they bind to the same projected path; mismatched or ADS-like descriptors
  fail closed.
- Preserved the existing NAVIGATION `path[:descriptor] - annotation` producer
  grammar while discarding annotation prose from canonical path identity.
- Enforced the producer-owned executable search-result contract with explicit
  top-level,
  hit-field, scalar-type, collection, backend, and embedding-fingerprint
  allowlists. Unknown or nested fields cannot bypass path projection.
- Loaded that complete contract from the authoritative machine JSON, accepted
  the producer's finite float priorities, and content-bound the schema in the
  exact RedDog runtime manifest.
- Included work-ledger hits in global flattening and rebuilt empty semantic
  canaries as evidence-free failures rather than mutating success payloads.
- Consolidated owner responses onto the existing response builder so every
  failed query returns empty raw and flattened evidence. Stale, lexical,
  changed-generation, and malformed results cannot leak unprojected paths.
- Rejected terminal whitespace, Unicode control/format/alternate-whitespace
  characters, and cross-flavor rooted paths before lexical projection instead
  of normalizing ambiguous evidence into a valid path.
- Retained read-only query behavior with no index or repository mutation.

## 2026-08-06 - Linked-worktree owner dependency root

- Corrected the one-shot owner query to resolve the primary same-repository
  worktree for vetted Python dependencies instead of assuming every linked
  worktree carries its own `.venv`.
- Preserved the clean exact-HEAD authority checkout as the only repository
  evidence source and retained read-only/no-reindex query behavior.
- Real acceptance moved from `SEMANTIC_BACKEND_UNAVAILABLE` to a generation-
  bound `CURRENT` result against the post-merge authority receipt.

## 2026-08-01 - Authority-worktree owner runtime binding

- Bound the one-shot semantic owner to the selected clean authority checkout
  for repository bytes while retaining the calling workspace as the validated
  checkout-local Python dependency root.
- Added regressions for both dirty-workspace authority selection and clean
  workspace operation. This closes the authority checkout's
  `SEMANTIC_BACKEND_UNAVAILABLE` failure without weakening generation binding.

## 2026-08-01 - Global owner-hit ranking for retrieval evaluation

- Flattened typed semantic hit buckets into one deterministic descending-score
  order before applying the result limit. Missing/non-finite scores retain
  stable bucket and source-position ordering.
- Deduplication now occurs after global ordering, so the strongest occurrence
  of a path is retained for Recall@K, MRR, and nDCG@K evaluation.
- Reused the extracted response normalizer from the legacy service wrapper and
  added cross-bucket score/dedup regression coverage.

## 2026-07-30 - Canonical Holo runtime dependency binding

- OBSERVED: the auto-owned query service stayed alive but returned authenticated
  `SEMANTIC_BACKEND_UNAVAILABLE`; its sanitized base-interpreter child could not
  import dependencies installed only in the canonical workspace virtualenv.
  The supervisor discarded HTTP 503 and retried until its 300-second deadline.
- Nonsealed trusted-host maintenance and owner startup now share one validated
  checkout-local `.venv/Lib/site-packages` binding. Validation covers
  containment, `pyvenv.cfg`, base interpreter, Python major/minor, and disabled
  system-site packages. User-site and inherited Python import overrides remain
  disabled.
- Sealed runtime startup remains bound to its separately bridge-validated
  dependency path and does not trust the workspace virtualenv. The manifest
  authenticates runtime source/bootstrap bytes, not every dependency file.
- Authenticated terminal health failures, including semantic backend
  unavailability, now fail immediately. Owner reuse also binds the runtime root
  so a changed dependency authority replaces the retained owner.
- Real-process validation produced exact-generation `READY` in about 14
  seconds; the same child without the dependency binding returned
  `SEMANTIC_BACKEND_UNAVAILABLE` in about one second instead of timing out.

## 2026-07-29 - Cold semantic owner startup probe alignment

- OBSERVED: one automatic startup exhausted its 300-second lifecycle deadline;
  a subsequent in-process exact-generation owner returned semantic `CURRENT`
  in about 35 seconds. The owner contract allowed 270 seconds for that cold
  canary while the supervisor abandoned each exchange after 30 seconds. This
  mismatch is corrected without claiming it was the only factor in the earlier
  startup failure.
- Startup health exchanges now inherit the owner's existing 270-second cold
  warmup allowance while remaining bounded by the unchanged total startup
  deadline. Ordinary post-start health probes remain capped at 30 seconds.
- The readiness loop is isolated from process ownership. A real authenticated
  HTTP regression proves a scaled cold response succeeds only under the
  startup budget, while the ordinary probe times out; one process is spawned
  and cleanup is bounded. The touched supervisor class and `start()` now meet
  WSP 62 limits, and inherited module debt is reduced from 688 to 675 lines.
- Authentication, exact repository/generation binding, no-reindex authority,
  owner poisoning, and cleanup behavior are unchanged.

## 2026-07-29 - Sealed RedDog Holo process boundary

- RedDog-owned Holo maintenance and query-owner processes now execute from the
  backend-manifest source copy through the verified Python bootstrap instead of
  importing executable code from the audited live checkout; repository reads
  remain bound to the separately validated exact-HEAD target checkout.
- Child environments remove provider credentials, RedDog authority values, and
  Python import overrides. Legacy non-RedDog callers retain their prior command
  path; an invalid runtime or bootstrap digest fails before process creation.

## 2026-07-29 - Windows virtualenv owner launch correction

- OBSERVED: RedDog's repository virtualenv launched the HoloIndex owner through
  a transient Windows redirector, so the real service process did not have the
  supervisor as its direct parent and the fail-closed watchdog exited before
  semantic health could complete.
- The supervisor now launches the base interpreter as its direct child only
  for the current Windows virtualenv and explicitly carries that virtualenv's
  approved site-packages path.
- Exact parent-process monitoring, authenticated loopback health, generation
  binding, and no-reindex authority are unchanged.

## 2026-07-27 - Promotion-time HoloIndex owner binding

- Added a read-only exact-binding verifier for RedDog promotion gates.
- The verifier accepts only an already-running owned or configured query owner
  that proves the expected repository root, HEAD, generation, and on-disk
  freshness-receipt digest.
- No owner startup, HoloIndex mutation, re-index, or query authority was added.

## 2026-07-26 - HoloIndex authority update transaction

- Added a distinct cross-process authority-update lease around exact-SHA,
  non-rewind detached worktree updates.
- Re-derives the queued authority-root digest and shared Git identity inside
  that lease before any fetch, switch, owner, or index effect.
- Reused the existing trusted maintenance handshake and `MaintenanceSession`
  for SSD mutation and atomic freshness publication.
- Added fail-closed supersession cleanup so a newly stale owner is stopped and
  no completion is published for an obsolete SHA.
- Added a durable authority blocker marker when both newer-HEAD advancement
  and canonical receipt invalidation fail.

## 2026-07-26 - HoloIndex exact-binding startup proof consolidation

- OBSERVED: exact-HEAD maintenance succeeded, but automatic owner bootstrap
  intermittently failed because it ran a second semantic health canary after
  the supervisor had already proved readiness; the duplicate five-second
  probe passed only 7/10 repeated live starts.
- The supervisor startup loop now proves the requested repository HEAD,
  repository-root digest, generation, and freshness-receipt digest in one
  authoritative authenticated health exchange and retains the actual returned
  binding with the live process.
- The process-private handoff validates process liveness, endpoint/token
  shape, and the retained exact binding without issuing a duplicate semantic
  query. Ten repeated live starts passed after the correction. Query-time
  pre/post freshness proof, authentication, loopback restriction, and
  no-reindex authority remain unchanged.
- An authenticated ready owner proving a different binding is now a terminal
  startup rejection instead of consuming the full retry window.

## 2026-07-25 - HoloIndex parent-process lifecycle correction

- OBSERVED: the blocking stdin watchdog introduced in v0.4.19 allowed the HTTP socket to listen but prevented semantic health from completing beyond 120 seconds on Windows; the same owner without that reader returned CURRENT in about 12 seconds.
- Replaced the stdin reader with an exact parent-process watcher: Windows waits on a process handle, POSIX observes the original parent relationship, and failed binding exits closed.
- Restored child stdin to `DEVNULL`; tokens remain environment-only and no query/index authority changed.

## 2026-07-25 - HoloIndex auto-owner semantic probe budget

- Raised only the auto-owner health-probe socket window from one to 30 seconds after an observed 11.22-second semantic canary repeatedly exhausted the legacy probe.
- Kept the 300-second total startup budget and all semantic, freshness, generation, authentication, cleanup, and no-reindex requirements unchanged.

## 2026-07-25 - HoloIndex owner lifecycle hardening

- Added a bounded pre-spawn port-availability gate before expensive semantic owner initialization.
- Added a private stdin parent-liveness watchdog so abruptly terminated supervisors do not leave orphaned loopback owners.
- Kept tokens process-private and made no change to query, index, repository, or network authority.

## 2026-07-25 - HoloIndex owner repository-root binding

- Added the canonical repository-root digest to freshness snapshots and owner responses.
- Owner queries now accept an expected root digest and reject a configured service rooted at a different worktree before semantic retrieval.
- No owner indexing or repository mutation authority was added.

## 2026-07-19 - RedDog HoloIndex owner binding probe

- OBSERVED: a canonical seven-collection HoloIndex receipt and owner health
  payload were both CURRENT at the exact repository HEAD, but the post-start
  binding probe failed because the semantic health canary took 1.016 seconds
  against a fixed 1.0-second socket timeout.
- Increased only the authenticated loopback health/binding response window to
  a bounded five seconds. Query deadlines, startup budget, receipt binding,
  token secrecy, loopback restriction, and fail-closed health checks remain
  unchanged.
- Added a regression proving a semantic health response just above one second
  is accepted without making unbounded or unauthenticated probes.

## 2026-07-18 - HoloIndex private query owner and host supervisor POC

**WSP Protocol**: WSP 00, 05, 06, 15, 22, 49, 50, 62, 87, 96, 97
**Phase**: POC implementation; focused validation/PR evidence pending
**Agent**: 0102 architect for 012 with delegated audit/test workers

**Changes**:

- Added a query/health-only HoloIndex owner with bearer authentication,
  literal-127.0.0.1 binding, bounded payloads/results/timeouts, serialized semantic
  backend access, exact clean-HEAD proof, and complete baseline freshness
  validation.
- Added stdlib HTTP transport with optional FastAPI adapter; neither surface
  exposes indexing.
- Added fail-closed maintenance probing and permanent owner poisoning after a
  backend timeout.
- Added HoloQueryServiceSupervisor: hidden argv-only owner process, ephemeral
  48-byte token, authenticated semantic readiness, bounded termination/kill,
  child environment handoff, and secret-free errors.
- Added the host bootstrap boundary, process-private authenticated handoff,
  poisoned-owner replacement, and operator runbook. Automatic credentials are
  never written to the parent environment.
- Added a trusted-host semantic maintenance handshake: clean exact HEAD, owned-owner
  stop policy, sanitized argv-only index-all, complete canonical seven-scope
  proof, recheck, and generation-bound restart.
- Health now requires repository/generation binding and a non-empty semantic
  canary; query success re-proves repository state after backend return.
- Bound CURRENT to an exact per-collection embedding-space fingerprint for all
  seven baseline collections. Blank legacy fingerprints now require canonical
  maintenance, and owner semantic proof compares receipt, runtime, and response
  maps.
- Forced the resident owner to authoritative sentence_transformers, added
  complete Hugging Face snapshot-cache discovery, and disabled the
  generation-unbound legacy SearchCache.
- Separated the first-health 270-second cold warmup, <=30-second owner queries,
  and 300-second supervisor startup. Response-body reads have an absolute
  deadline; stdlib connect/header progress retains the documented
  trusted/cooperative-loopback POC assumption.
- Model-backed cross-lane direct reads now receive clean exact-HEAD proof after
  reading and again immediately before report acceptance.

**Impact**: The infrastructure module supplies one supervised query process and
one separately authorized trusted-host maintenance handshake for the migrated
RedDog operational consumers. The supported adapter has no write surface, but
this is not proof of OS privilege isolation or migration of legacy
`src/holo_tools.py` direct-store access. Full refresh still assumes an
exclusive writer window, and abrupt host death can orphan the owner.
The HTTP boundary also assumes no hostile same-user loopback port squatter or
deliberate header trickle; connect/header parsing is inactivity-bounded even
though owner work and response-body reads are deadline-bounded.

**WSP Compliance**: Focused infrastructure thresholds and split-test gates will
be recorded after validation, including any architect exemptions. ROADMAP.md
records historical WSP_62 debt; no global compliance claim is made.

## 2026-05-08 - S64: S1 / S2 federation-scope request parity

**Author**: 0102 (Worker W1)
**WSP**: 97 (Truth Boundaries), 96 (MCP Governance — Annex A.2)
**Slice**: `S64_S1_S2_FOUNDUP_SCOPE_REQUEST_PARITY_PHASE1`
**Closes (MCPA6 audit drift)**: D7, D8, D14, D15 (cross-surface parity portion); D19 fully

### Why

S63 added `foundup_id` / `include_shared` to S2, and S62 did the same for S1.
Both surfaces emitted truthful "tenant scoping not yet enforced" warnings,
but the warning text was duplicated as separate string literals. Per WSP 97,
contract consumers should be able to match a single canonical phrase rather
than two near-identical strings that could drift over time. This slice
extracts the warning into a shared template constant on each side and adds
parity tests that fail if either side drifts.

### Changes (S2 side)

- `src/holo_tools.py`:
  - Added `FEDERATION_SCOPE_WARNING_TEMPLATE` constant (byte-identical to
    the S1 mirror in `foundups-mcp-p1/servers/holo_index/canonical_search.py`).
  - Added `federation_scope_warning(surface)` formatter.
  - `holo_search` now emits `federation_scope_warning(S2_SURFACE_ID)` instead
    of an inline string literal.

- `tests/test_mcp_bridge.py`:
  - Added `TestS64FederationScopeParity` class (8 tests): S2 template token
    presence, canonical phrasing fragments, `federation_scope_warning("S2")`
    shape, no-foundup-id-echoes-null pair (with and without explicit
    `include_shared`), with-foundup-id echo + warning emission, byte-for-byte
    template match in the runtime warning, and a cross-surface parity test
    that imports S1's template and asserts byte equality.

### Behavior boundaries (what did NOT change)

- No federation auth implementation (still deferred to MCPA1 Slice 6).
- Envelope shape from S63 unchanged.
- The runtime warning text is byte-identical to what S63 emitted — only
  the source of the string changed (template constant instead of inline
  literal).
- S3 (pavs_mcp) and MCP Manager untouched.

### Tests

```
PYTHONPATH=. python -m pytest \
  modules/infrastructure/foundups_mcp_bridge/tests/test_mcp_bridge.py \
  -k "holo_search or AnnexAConformance or FederationScopeParity" -q
-> 34 passed (26 from S63 + 8 new S64 parity tests)
```

---

## 2026-05-08 - S63: S2 holo_search → WSP 96 Annex A request/meta conformance

**Author**: 0102 (Worker W1)
**WSP**: 97 (Truth Boundaries), 96 (MCP Governance — Annex A.2/A.3)
**Slice**: `S63_S2_ANNEX_A_RENAME_AND_META_PHASE1`
**Closes (MCPA6 audit drift)**: D12, D13, D14, D15, D16, D17, D18

### Why

Per MCPA6 conformance audit (`docs/audits/mcp_system/MCPA6_MCP_CONFORMANCE_AUDIT.md`),
S2 was the closest of the three `holo_search` surfaces to the WSP 96 Annex A
canonical contract — but still drifted on field naming (`scope` vs
`doc_type_filter`, `top_k` vs `limit`), lacked the federation request fields
(`foundup_id`, `include_shared`), did not tag responses with `meta.surface`,
returned a flat string error instead of the canonical `error.code` object,
and used a hardcoded `0.5` relevance for ripgrep fallback instead of the
Annex A.3 0.6 cap policy. This slice closes those gaps without rewriting
S2 architecture.

### Changes

- `src/holo_tools.py`:
  - Added module-level constants `S2_SURFACE_ID`, `ANNEX_A_LIMIT_MAX`,
    `ANNEX_A_LIMIT_DEFAULT`, `ANNEX_A_FALLBACK_RELEVANCE_CAP`.
  - Added `_build_s2_error_envelope()` helper producing the Annex A.3
    `{code, message, details?}` error shape (the generic `error_response()`
    keeps returning a flat string for the other tools — no cross-tool drift).
  - Added `_build_s2_ok_envelope()` helper producing the canonical Annex A.3
    ok envelope with `data.metadata.retrieval_mode`, `data.metadata.warnings`,
    `meta.surface = "S2"`, etc.
  - Rewrote `holo_search` signature to accept the five canonical Annex A.2
    request fields (`query`, `limit`, `doc_type_filter`, `foundup_id`,
    `include_shared`). Legacy `scope` and `top_k` retained as deprecated
    aliases; canonical names win when both are supplied.
  - Empty-query rejection now returns `error.code = "EMPTY_QUERY"` with a
    truthful message naming Annex A.2.
  - Limit is clamped to Annex A.2 [1..50] with a truthful warning when the
    clamp applies; invalid types fall back to default 10 with a warning.
  - Lexical fallback path now caps every hit's `relevance` at
    `ANNEX_A_FALLBACK_RELEVANCE_CAP = 0.6` per Annex A.3.
  - `data.metadata` block now always carries `retrieval_mode`,
    `engine_version`, `collections_searched`, and `warnings`. Engine
    metadata is merged in without overriding canonical keys.
  - `meta.surface = "S2"` and `meta.tool = "holo_search"` emitted on both
    ok and error responses.
  - Federation field acceptance is truthful: `foundup_id` is echoed but
    surfaces an Annex A.2/Slice-6 "tenant scoping not yet enforced" warning;
    `include_shared` is echoed as `None` when `foundup_id` is null so callers
    cannot infer a scope decision was made.
  - Imports `MCPResponse` from `response_schema` (was importing
    `ok_response`/`error_response` only).

- `tests/test_mcp_bridge.py`:
  - Updated `test_holo_search_empty_query_error` to assert the canonical
    `error.code = "EMPTY_QUERY"` shape and `meta.surface = "S2"`.
  - Added `TestS2HoloSearchAnnexAConformance` class with 22 focused tests
    covering: canonical field names accepted, foundup_id/include_shared
    echo semantics, legacy aliases (`scope`, `top_k`) still work with
    truthful warnings, canonical wins over alias when both supplied,
    Annex A.2 limit bounds (clamp warnings), `meta.surface`, `meta.tool`,
    `meta.source` truthfulness, `data.metadata` canonical keys, empty-query
    canonical error, whitespace-query rejection, foundup_id unenforced
    warning, fallback relevance ≤ 0.6 cap, BACKEND_UNAVAILABLE error
    envelope, and direct `holo_tools.holo_search()` invocation.

- `ModLog.md` (NEW): this entry.

### Behavior boundaries (what did NOT change)

- S1 (`foundups-mcp-p1/servers/holo_index/server.py`) untouched.
- S3 (`pavs_mcp/src/server.py`) untouched.
- MCP Manager untouched.
- `error_response()` and `ok_response()` helpers in `response_schema.py`
  unchanged — only `holo_search` builds the canonical structured error.
  Other bridge tools keep the legacy flat-string error shape.
- Other tools in `holo_tools.py` (`holo_related`, `holo_failure_memory`,
  `holo_pattern_search`, `holo_task_packet`) are untouched per slice scope
  (deferred until they have a canonical Annex A entry of their own).
- No federation auth implementation. `foundup_id` is accepted and echoed
  but tenant scoping is NOT enforced — explicitly tracked as MCPA1 Slice 6.
- No real-relevance computation change in the semantic path — Annex A's
  `1/(1+distance)` rule was already approximated by `_parse_similarity`
  which converts "85.1%" → 0.851. Only the fallback path needed the cap.

### Tests

```
PYTHONPATH=. python -m pytest \
  modules/infrastructure/foundups_mcp_bridge/tests/test_mcp_bridge.py \
  -k "holo_search or AnnexAConformance" -q
-> 26 passed, 87 deselected
```

### Tracked follow-ups

- MCPA1 Slice 6 (`MCP_FEDERATION_AUTH_AND_SCOPE_PHASE1`) — actually
  enforce `foundup_id` tenant scoping. The truthful "not yet enforced"
  warning surfaced by this slice will flip to a real authority check.
- MCPA6 Slice 6.2 — bring S1 (`semantic_code_search`) into the same
  envelope conformance applied here to S2.
- The four other holo_* tools in this module (`holo_related`,
  `holo_failure_memory`, `holo_pattern_search`, `holo_task_packet`)
  remain on the legacy `ok_response` envelope. WSP 96 Annex A only
  defines `holo_search` today; those tools get their own annex when
  they have a canonical contract.
