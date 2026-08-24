# FoundUps MCP Bridge Interface

## Public API

### `holo_query_bundle(...) -> Dict[str, Any]`

Remote read-only MCP tool for one generation-bound Holo query plus lexical WSP
memory bundle. Request schema enforces query 1..16,000 chars, limit 1..20,
`semantic|lexical`, module hint <=512 chars, at most 40 non-empty include paths
of <=1,024 chars, and a strict boolean bundle-only flag. The one-shot adapter
revalidates the same bounds and never reindexes. Semantic rejection remains
typed; lexical/bundle-only calls perform zero owner attempts and zero Holo
store access. The `reddog_holo_query_bundle_mcp.v1` public projection removes
private roots/tokens, projects hit paths repository-relative, redacts bounded
text, rejects cycles/non-finite numbers/large integers/key collisions, and is
at most 256 KiB with exact encoded-byte telemetry.

### `build_asgi_app(...)`

Builds a loopback-only FastMCP Streamable HTTP application at `/mcp`; non-loopback hosts reject.
Optional bearer auth is local/dev defense, not ChatGPT OAuth; external exposure has no live receipt here.

### `materialize_query_replica(...) -> QueryReplicaResult`

Creates one immutable `holoindex_query_replica.v1` generation under a new `StoreProof` from exact bindings, limits, and sorted `model`/`snapshots` manifests.
Only the complete model and exact generation-bound 22-file `vectors/query_snapshots` closure is accepted; legacy `vectors/` and `chroma.sqlite3` reject.
Production is sealed/read-only at the source and retains sentinel identities/bytes plus the receipt descriptor through copy, publication, validation, and reverse release.

Manifests exactly equal enumerated sources. Before mutation, integers reject bool/float; paths use one bounded exact NFC/POSIX representation; ordering uses NFC+casefold identity; all 22 inner bindings equal the outer manifest.
Links, reparse points, hardlinks, special files, escapes, overlap, exhaustion, aliases, and ambiguous model markers fail.

Windows retains raw OS handles through final aggregate proof while using one transient CRT descriptor at a time; the 4 MiB descriptor bound fails closed.

Success no-replace publishes `generations/<digest>/` then immutable `holoindex_query_replica.active.json`, binding repository, receipt, generation, storage identities, UTC time, hashes, and sizes. Existing targets are never overwritten.
Final failure atomically no-replace quarantines whatever occupies this call's active name; success makes active absent and returns a relative orphan path. Rename failure leaves active and reports a relative unsafe path.
Publication temps and staging trees are preserved. Windows copy failure closes handles but leaves bounded partial output; the materializer quarantines its enclosing staging root. Direct `copy_model_snapshot` callers own their isolated partial destination. Phase 1 deletes nothing and has no retention, rollback, or live-discovery API.

### `build_query_replica_activation_plan(...) -> QueryReplicaActivationPlan`

Read-only trusted-host admission for explicit canonical roots, clean exact HEAD, CURRENT freshness, and the exact `all-MiniLM-L6-v2` model.
It returns canonical binding plus validated `model` and `snapshots` manifests after two descriptor-hash passes and a final identity enumeration.
Links, reparse points, hardlinks, special files, hostile values, or observed mutation fail with stable `QueryReplicaPlanError` codes.
It holds no post-return lease; materialization revalidates later source changes. It does not copy, maintain, launch, route, or activate.

### `QueryRouteStore`

Private trusted-host stable route state. `initialize_empty()` no-replace anchors revision 0; `load()` recovers any PREPARED transaction by exact rollback.
`load_readonly()` performs a terminal read under the same lock without
publication or recovery: no journal is valid only for `EMPTY`, `CURRENT`
requires the journal-selected digest, and `PREPARED` returns
`QUERY_ROUTE_TRANSITION_PENDING`. `load()` likewise rejects an unjournaled
`CURRENT` record with `QUERY_ROUTE_JOURNAL_REQUIRED`; explicit controller use
is the only recovery boundary.
`transition(candidate, expected_revision=..., expected_route_digest=...)` holds one machine-wide lock, journals before route replacement, and exposes a commit request finalized only on normal context exit.
Canonical bounded JSON, copied immutable binding maps, duplicate/type/path/link/private-file checks, revision+digest CAS, and exact reread proofs fail closed. PREPARED recovery compares raw structural state before selected-root liveness so a vanished candidate can be rolled back; an unknown third state remains terminal. Confined persistence is delegated to `QueryRouteRuntimeIO`. The store does not validate semantic authority, query, materialize, publish receipts, alter environment variables, or activate by itself.

### `build_query_replica_owner_route(...) -> QueryReplicaOwnerRoute`

Health transport requires exact built-ins: literal `127.0.0.1`, port 1..65535, printable token >=32, and finite positive timeout <=300.
JSON is an exact dict with unique keys at every depth and no NaN/Infinity; parse, Unicode, recursion, primitive, and oversize failures return unavailable. Bindings are exact four-tuples; only expected canonical fields may be empty wildcards.
Exchange parses canonical then mandatory replica expectation before transport/HTTP. Binding malformation returns mismatch; HTTP/OSError failures return unavailable, and targeted close failures preserve the proof. Context entry calls `start()`, so a complete route remains mandatory.
`ensure_reddog_holoindex_owner(..., query_replica_route=route)` passes split roots,
reproves before spawn/health, and denies ambient/public paths or reuse drift.
Its optional `startup_timeout_seconds` is exact-positive and bounds configured
health plus process startup/probe/shutdown for a caller-supplied operation
deadline. Invalid timeout types fail closed; absence retains the host default.

### `resolve_query_replica_owner_route(...) -> QueryReplicaOwnerRoute`

Trusted-host resolver preferring `REDDOG_HOLOINDEX_QUERY_ROUTE_FILE`; the
legacy `REDDOG_HOLOINDEX_QUERY_REPLICA_ROOT` remains supported only when the
route-file value is absent. Both present is an ambiguity failure. The route
file must be absolute, private, canonical, and selected under its serialized
store. Its `CURRENT` authority root, canonical HEAD/root/generation/receipt,
replica root, and four public replica fields must exactly match a fresh active-
descriptor proof. The legacy value must be an explicit absolute path to an
existing store disjoint from canonical repository and SSD roots. The resolver
never infers a replica from `HOLOINDEX_SSD_PATH`, materializes, recovers a
transition, rewrites route state, or re-indexes. Configuration, terminal route
admission, descriptor, or binding failure is reduced to
`HOLOINDEX_QUERY_REPLICA_REQUIRED` without publishing a private path.

The one-shot semantic adapter and maintenance handshake resolve this route
before owner startup; promotion resolves it before read-only owner binding
verification. All three pass the same capability into the existing owner API.

Initial resolution hashes the complete narrow descriptor; modern admission
requires the vector surface to equal exactly the 22 snapshots. A retained route
revalidates its identity/bytes, manifest projection, authority, and only the
selected model plus `vectors/query_snapshots/`. The isolated owner independently
admits the full closure before using the same bounded proof. No TTL/cache or
deadline changes; descriptor, authority, model, or snapshot drift fails closed.
The full verifier can audit a historical coherent model plus SQLite/HNSW
closure, but retained runtime revalidation rejects that legacy surface.

### `verify_reddog_holoindex_owner_binding(...) -> bool`

Read-only promotion-time proof that the already-running private query owner
serves the exact repository root, repository HEAD, HoloIndex generation,
on-disk freshness-receipt digest, and mandatory current replica route supplied
by the caller. It never starts or re-indexes; missing route or mismatch returns
`False`.
Successful owner evidence is deep-copied and projected onto repository-relative
POSIX paths before raw, flattened, semantic-evidence, or receipt use. Unknown
rooted, drive-qualified, traversal, and outside-root paths fail closed. The
owner imports the producer-owned executable contract and accepts only
canonical search-result fields, scalar hit values, known collection/backend
mappings, and digest-shaped embedding fingerprints.
Unknown or nested evidence fields reject the complete response.

`flatten_hits(result, limit, query=...)` returns no hits when `limit <= 0`.
For a positive limit and one explicit module, it reserves exact module-root
README/INTERFACE evidence before filling remaining slots by global score.

### FoundUpsMCPBridge (local/internal only)

Main bridge class for trusted in-process tool access. Registration here does
not grant Streamable HTTP authority; the remote server admits only
`holo_query_bundle`.

Construct with `FoundUpsMCPBridge(repo_root=...)`. `list_tools()` reports the
local registry, `call_tool(name, **kwargs)` invokes a local tool, and
`get_status()` reports bridge capabilities. All return the legacy MCPResponse
envelope documented below; none changes the remote allowlist.

---

### HoloIndexQueryOwnerService

The supported private RedDog owner exports:

    from modules.infrastructure.foundups_mcp_bridge.src.holo_query_service import (
        HoloIndexQueryOwnerService,
        create_holo_query_app,
        create_stdlib_server,
    )

The production backend is the immutable seven-collection snapshot set emitted
by governed maintenance and copied as the exact 22-file snapshot closure inside
the verified replica generation. It
supports only the Chroma-shaped read subset used by HoloIndex. Backend creation
fails closed when the snapshot generation differs from the active replica;
query startup/search never starts Chroma or opens replica SQLite/HNSW files.
The owner performs one complete replica admission, then uses the retained
bounded proof above before and after semantic retrieval. Runtime proof never
substitutes for initial complete narrow-manifest admission.

HTTP exposes authenticated `POST /holoindex/v1/query` and
`GET /holoindex/v1/health` only; there is no indexing API. Both require
`Authorization: Bearer` via `HOLOINDEX_QUERY_SERVICE_TOKEN`, accept only the
literal `127.0.0.1` Phase-1 bind, and reject hostnames, alternate `127/8`
literals, and IPv6. Requests, results, and execution are bounded.

Query requires `query` and `expected_repo_head_sha`; `limit` and
`doc_type_filter` are optional. Success requires semantic retrieval, exact
repository SHA, stable generation/receipt digest, seven verified baseline
manifests, and the same nonblank embedding fingerprint in each receipt entry,
resident backend, and response. Lexical fallback, stale or missing proof,
generation change, and backend failure fail closed. Successful paths are
projected beneath the proven root before flattening, hashing, or receipt use;
rooted, traversal, outside-root, Unicode-control/format/alternate-whitespace,
or malformed evidence rejects the whole response. Every failed response has
empty raw and flattened evidence.

`flatten_hits(result, limit, query=...)` reserves README then INTERFACE only
when canonical `metadata.tier0_module_target`, query intent, one complete root
pair, and both rows' `exact_metadata` provenance agree. Reservation is bounded
by positive K and creates no evidence. Missing, unrelated, partial, mixed,
duplicate, forged, ambiguous, multi-module, and no-module claims keep global
score order; nested test docs are never Tier-0. The producer's bounded HEAD
catalog, not flattened top-K hits, establishes intent, rejects Unicode
`Cc`/`Cf`/`Cs`, and compares duplicate identity as `NFC(path).casefold()`
without rewriting visible Unicode.

Exact producer errors are `HOLOINDEX_MODULE_INTENT_SNAPSHOT_UNAVAILABLE`
(HTTP 503), `HOLOINDEX_TIER0_INCOMPLETE` (HTTP 409), and
`HOLOINDEX_TIER0_LOOKUP_FAILED` (HTTP 503). Unknown/free-text metadata becomes
`SEMANTIC_BACKEND_UNAVAILABLE`. The owner forces authoritative
`sentence_transformers`, disables TurboQuant and the generation-unbound
SearchCache, and rejects incomplete/ambiguous offline model caches.

Dependency validation, cache layout, cold-start/request budgets, transport
limits, supervision, and maintenance belong to [README.md](README.md#private-holoindex-query-owner)
and [HOLO_QUERY_OWNER_RUNBOOK.md](HOLO_QUERY_OWNER_RUNBOOK.md).

Launch requires explicit split storage authority:

    python -m modules.infrastructure.foundups_mcp_bridge.src.holo_query_service --host 127.0.0.1 --port 8127 --canonical-ssd-path <canonical> --query-replica-root <verified-root>

### HoloQueryServiceSupervisor

Trusted host bootstraps use this lifecycle API instead of distributing a
manually selected bearer token:

    from modules.infrastructure.foundups_mcp_bridge.src.holo_query_service_supervisor import (
        HoloQueryServiceSupervisor,
        HoloQueryServiceSupervisorError,
    )

    with HoloQueryServiceSupervisor(
        repo_root=route.canonical_repo_root, canonical_ssd_path=route.canonical_ssd_path,
        query_replica_root=route.replica_root_proof.path, replica_capability_verifier=route.revalidate,
        expected_replica_binding=route.expected_replica_binding,
    ) as owner:
        child_environment = owner.environment_for_child()

Route-less or malformed context entry raises `HOLOINDEX_QUERY_REPLICA_REQUIRED`
before side effects. `start()` returns only after authenticated health proves semantic readiness. `environment_for_child()` returns a new mapping with
HOLOINDEX_QUERY_SERVICE_URL and the per-process
HOLOINDEX_QUERY_SERVICE_TOKEN; it never mutates the host environment. stop()
invalidates the handoff, terminates the owner, and kills it after a bounded
grace period. Startup failures raise HoloQueryServiceSupervisorError with a
stable secret-free code. An occupied fixed port fails before process spawn,
and a parent-process watcher exits an auto-owned child when its exact supervisor
process dies without consuming stdin. Ordinary authenticated health probes use
a bounded 30-second response window. Supervisor startup permits the first cold
semantic canary to use the owner's 270-second warmup budget inside the
300-second total startup deadline. The readiness loop is isolated in
`holo_query_owner_startup.py`; process ownership, authenticated validation,
exact binding, and child handoff remain in the supervisor. This supported
adapter boundary does not itself
remove OS filesystem/process privileges from a child; the trusted host must
configure those permissions separately.

Authenticated health responses that prove a terminal semantic backend error
fail immediately with that stable error code. They are not retried until the
startup deadline. Transient connection failures remain bounded retries.

The host bootstrap must retain the supervisor for the RedDog consumer's
lifetime. A private-adapter QUERY_OWNER_POISONED response replaces the owned
process and retries once; explicitly configured external owners are never
restarted here. See
[HOLO_QUERY_OWNER_RUNBOOK.md](HOLO_QUERY_OWNER_RUNBOOK.md).

### RedDog HoloIndex Owner Bootstrap

`ensure_reddog_holoindex_owner()`, `resolve_reddog_holoindex_owner_handoff()`,
and `cleanup_reddog_holoindex_owner()` own the process-lifetime policy. Results
contain only readiness, status, and a stable error, never URL/token. The policy respects an
existing literal-127.0.0.1 HTTP URL/token, honors
REDDOG_HOLOINDEX_OWNER_AUTO_START=0, otherwise resolves the canonical
HOLOINDEX_SSD_PATH and starts one retained supervisor.

Successful automatic startup stores the URL/token only in a process-private
handoff; it does not modify os.environ. In-process RedDog adapters call
resolve_reddog_holoindex_owner_handoff(), which checks the retained supervisor
process rather than health-probing before every query. It replaces a dead
owned process once before returning either the private tuple or None. Poison
replacement is triggered by the actual query response. Explicit environment
configuration remains the boundary for an independently supervised owner.

Configured-service acceptance requires a token of at least 32 characters, an
HTTP URL using literal `127.0.0.1` at the root or
/holoindex/v1/query path, and the exact
authenticated semantic health response. When expected values are supplied,
health must also match the exact repository SHA, freshness generation, and
freshness-receipt digest.
Invalid or unready explicit configuration returns a stable failure without
overwriting either value.

`cleanup_reddog_holoindex_owner()` stops the auto-owned process and erases its
private handoff; `restore_environment` is compatibility-only.

`scripts/reddog_holoindex_owner_query_once.py` resolves query authority before
owner startup. It first rehydrates the exact selected-root/store freshness
proof; a root-bound receipt mismatch returns `freshness_repo_root_mismatch`
with `owner_attempts=0`, no retry, and no owner/backend call. Process-owned
`STARTED` and `REUSED` owners are cleaned after the one-shot query.

`run_candidate_acceptance(...)` performs two direct private-owner queries,
cleans the owner, executes one supported-wrapper activation, and requires final
receipt/collection rehydration before PASS. Its secret-free receipt records
counts and one-way digests, never owner credentials, responses, or paths. The public import surface remains in the orchestrator; pure query/activation validation and receipt/finalization proof are cohesive internal modules. The
snapshot child uses the one validated dependency root and a retained exact
process-image capability: Windows denies replacement through launch; Linux
executes `/proc/self/fd/<fd>` with `pass_fds`; unsupported platforms fail
closed. Exact subprocess, stable-error, and proof-lifetime details are
canonical in [HOLO_QUERY_OWNER_RUNBOOK.md](HOLO_QUERY_OWNER_RUNBOOK.md).

### RedDog HoloIndex Trusted Maintenance Handshake

Interactive/headless operational preflights and startup maintenance dispatch
call `ensure_reddog_holoindex_operational(repo_root=..., owner_runtime_root=...,
requested=...)`. With `REDDOG_HOLOINDEX_AUTO_MAINTENANCE=1` (default), the
trusted host may refresh a stale canonical store only from a clean exact Git
HEAD. It stops only an auto-owned owner, strips semantic bypass and source
narrowing, runs one bounded argv-only full refresh, proves all seven baseline
collections, and rechecks HEAD. Both fresh-receipt and post-refresh startup
resolve the mandatory `QueryReplicaOwnerRoute`; missing, ambiguous, drifted, or
uncommitted route state fails as `HOLOINDEX_QUERY_REPLICA_REQUIRED` before
owner construction. Governed WRE reaches maintenance authority only through
the explicit exact-SHA authority transaction below.

The one-shot owner wrapper accepts authority only from the checkout named by
`REDDOG_HOLOINDEX_AUTHORITY_REPO_ROOT`: a dedicated clean checkout, immutable
under an exclusive repository-writer window through refresh/publication. The
active caller worktree is invalid. Child stdout is drained to at most 16 KiB
in memory; stderr and disk capture are disabled. Only an explicitly
allowlisted stable code from the final JSON line crosses the boundary; detail,
forged/malformed/oversized output, paths, and logs reduce to
`HOLOINDEX_MAINTENANCE_REFRESH_FAILED`. Windows timeout makes a bounded exact-PID
`taskkill /T /F` attempt; missing, denied, or timed-out `taskkill` falls back to bounded direct-child kill/wait. POSIX signals the exact new process group but cannot
contain a descendant that starts a new session. Such an escaped descendant may retain
stdout and the daemon reader until it exits. This is cooperative trusted-host
best-effort containment, not a hostile-process or OS-privilege guarantee; never
assume the whole tree is gone.

Optional `owner_runtime_root` supplies the trusted `.venv` for nonsealed
refresh/start; inherited `PYTHONPATH` and user-site packages stay disabled.
The launcher passes one independently validated site-packages path through
`HOLOINDEX_MAINTENANCE_PROBE_SITE_PACKAGES`, distinct from ambient
`PYTHONPATH`. Before lease acquisition or invalidation, `MaintenanceSession`
revalidates that exact non-link path against its virtualenv and proves the
actual current-process image. The typed path/proof pair stays process-local and
is passed unchanged to `verify_collection_snapshots_isolated`; it is never
serialized, logged, or returned. Missing marker retains the runtime-free
contract only when no governed runtime input was supplied. A governed
invalid/ambiguous/link runtime returns
`HOLOINDEX_FINAL_COLLECTION_SNAPSHOT_PROBE_FAILED` before spawn rather than
omitting the marker. Child-side changed or partial authority fails single-shot
with the same code and detail `RUNTIME_DEPENDENCY_UNAVAILABLE`.

The SSD lease coordinates migrated writers, not unleased legacy writers or a
transient edit/revert. Clean exact HEAD is therefore re-proved after final
snapshot verification immediately before PASS publication; failure preserves
IN_PROGRESS. Later owner startup/health failure may leave CURRENT persisted
while the operational result remains false.

### Exact-SHA Authority Worktree Transaction

`advance_reddog_holoindex_authority()` is the trusted WRE effect boundary for
post-merge refresh. It acquires a separate cross-process authority-update
lease, fetches and proves the requested `origin/main` SHA, rejects non-forward
updates, stops the process-owned query service, switches the dedicated clean
worktree in detached mode, and invokes the existing maintenance handshake.
Before any Git effect it re-derives the authority-root digest and common Git
directory under that lease, rejecting any path substitution since queuing.
The inner `MaintenanceSession` remains responsible for SSD invalidation,
refresh, final receipt publication, and its own writer lease.

If main advances during refresh, the owner is stopped and the authority
checkout advances to the newer unindexed HEAD (or the current generation is
explicitly invalidated). No stale completion is published.
If both advancement and canonical invalidation fail, a fixed authority
blocker marker makes repository-state admission fail closed; only the same
leased transaction may clear it after switching to the exact target.

`rehydrate_canonical_freshness_proof()` is read-only. It starts no owner and
opens no persistent index; it reuses canonical query admission to prove exact
HEAD, repo/SSD identity, baseline collections, maintenance-lock state,
generation, and receipt digest.

For model-backed cross-lane audits, HoloIndex supplies candidate discovery and
an exact receipt HEAD while the worker directly reads only its allowlisted
paths. The worker re-proves that clean exact HEAD after the direct reads and a
second time immediately before accepting the report. Either proof failure
returns REJECT_REPOSITORY_STATE_CHANGED.

A stale externally configured owner returns
HOLOINDEX_MAINTENANCE_EXTERNAL_OWNER_UNSUPPORTED and is never terminated by
this process. Any semantic, source-completeness, repository-race, receipt, or
restart failure remains non-operational. See
[HOLO_QUERY_OWNER_RUNBOOK.md](HOLO_QUERY_OWNER_RUNBOOK.md).

Scope note: one-shot query, maintenance start, and promotion verification now
consume the same mandatory verified route. The separate activation controller
that creates/materializes/commits a new route and emits its secret-free receipt
is not implemented by these consumers.
The legacy `src/holo_tools.py` MCP surface still opens the HoloIndex store
directly and remains a registered migration item; Phase 1 does not claim that
all repository consumers cross this boundary. Normal cleanup is bounded, and
auto-owned v0.4.21+ children terminate when their exact supervisor process exits.
Manually launched and pre-v0.4.21 owners do not inherit that parent-death proof.

---

## Local/internal tool reference (not remotely registered)

The legacy perception APIs below remain direct `FoundUpsMCPBridge` surfaces.
They are not registered at `/mcp`; their remote-admission disposition and
transitive reasons are recorded in `ROADMAP.md#remote-admission-audit`.

### Repo Perception

#### `get_repo_tree(path=".", depth=3)`

Get directory tree structure.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| path | str | "." | Relative path to start |
| depth | int | 3 | Max traversal depth |

#### `read_file(path)`

Read file content.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| path | str | Yes | Relative file path |

**Limits:** 200KB max, blocked patterns filtered

#### `search_repo(query, path=".", top_k=20)`

Search repository using ripgrep.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| query | str | - | Search regex |
| path | str | "." | Search scope |
| top_k | int | 20 | Max results |

#### `get_recent_changes(limit=50)`

Get git commit history.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | int | 50 | Max commits |

---

### Documentation Access

#### `get_wsp_docs()`

List all WSP protocol documents.

#### `get_module_docs(module_name)`

Get module README.md.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| module_name | str | Yes | Module name |

#### `get_interface_doc(module_name)`

Get module INTERFACE.md.

#### `get_test_docs(module_name)`

Get module test documentation.

#### `get_modlog(limit=20)`

Get recent ModLog entries from root and key modules.

#### `get_violations(limit=20)`

Get known WSP violations and audit issues.

---

### Overseer Perception

#### `get_mission_history(limit=20)`

Get AI Overseer mission records.

**Sources:** SQLite `overseer.db`, JSONL history

#### `get_pattern_memory(limit=50)`

Get learned patterns (WSP 48).

**Sources:** `adaptive_learning/*.json`

#### `get_overseer_status()`

Get current Overseer system status.

**Returns:**
```python
{
    "available": bool,
    "db_exists": bool,
    "pattern_memory_exists": bool,
    "security_monitor_active": bool,
    "wsp_audit_status": {...},
    "last_mission": {...},
}
```

#### `get_coordination_state()`

Get active teams and recent phases.

#### `get_known_failure_patterns(limit=30)`

Get error patterns for avoidance.

---

### Dependency Perception (v1.1)

#### `get_module_dependencies(module_name, include_external=True, max_depth=1)`

Get dependencies for a FoundUps module.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| module_name | str | - | Module name (e.g., "ai_overseer") |
| include_external | bool | True | Include external package dependencies |
| max_depth | int | 1 | Depth of internal dependency traversal |

**Returns:**
```python
{
    "module": str,
    "module_path": str,
    "files_analyzed": int,
    "internal_dependencies": [
        {"module": str, "imported_by": [str], "import_count": int, "confidence": str}
    ],
    "external_dependencies": [
        {"package": str, "imported_by": [str], "import_count": int}
    ],
    "declared_requirements": [str],
}
```

**Confidence values:** `direct_import`, `manifest_declared`, `search_inferred`

#### `get_reverse_dependencies(module_name, search_scope="modules")`

Find modules that depend on the specified module (blast radius analysis).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| module_name | str | - | Module to find dependents of |
| search_scope | str | "modules" | Scope: "modules" or "all" |

**Returns:**
```python
{
    "module": str,
    "dependents": [
        {"module": str, "import_details": [...], "import_count": int}
    ],
    "dependent_count": int,
    "blast_radius": str,  # "isolated", "low", "medium", "high", "critical"
}
```

---

### Diff Perception (v1.1)

#### `get_file_diff(path, commit_range=None)`

Get diff for a specific file.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| path | str | - | Relative file path |
| commit_range | str | None | Git commit range (e.g., "HEAD~3..HEAD") |

**Behavior:**
- If `commit_range` provided: diff across that range
- If omitted: working tree vs HEAD

**Returns:**
```python
{
    "path": str,
    "commit_range": str,
    "has_changes": bool,
    "diff": str,  # Truncated if > 500 lines or 100KB
    "stats": {"additions": int, "deletions": int, "total_changes": int},
    "truncated": bool,
    "commit_info": [{"hash": str, "author": str, "message": str}],
}
```

**Security:** Blocks .env, credentials, secrets, .pem, .key files

#### `get_diff_summary(commit_range, path=".", group_by_module=True)`

Get summary of changes across a commit range.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| commit_range | str | - | Git commit range |
| path | str | "." | Scope path |
| group_by_module | bool | True | Group files by module/domain |

**Returns:**
```python
{
    "commit_range": str,
    "commit_count": int,
    "files_changed": int,
    "overall_stats": {"files_changed": int, "insertions": int, "deletions": int},
    "changed_files": [{"path": str, "status": str}],
    "grouped_by_module": {"domain/module": [str]},
    "commit_messages": [str],
}
```

---

### Impact Prediction (v1.2)

#### `get_change_impact_score(target_type, target)`

Compute blast-radius and risk score for a change target.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| target_type | str | Yes | "module", "file", "diff", or "commit_range" |
| target | str | Yes | Module name, file path, or commit range |

**Returns:**
```python
{
    "target_type": str,
    "target": str,
    "affected_modules": [
        {
            "module": str,
            "risk_weight": float,  # 1.0 = base, higher = more critical
            "is_primary": bool,    # Directly changed vs reverse dep
            "is_critical": bool,   # In CRITICAL_MODULES list
            "internal_dep_count": int,
        }
    ],
    "risk_level": "low" | "medium" | "high" | "critical",
    "risk_score": float,  # 0-1 composite score
    "risk_factors": [str],  # Explanations for risk level
    "test_coverage": {
        "covered": int,
        "total": int,
        "gaps": [str],  # Module names without tests
        "coverage_ratio": float,
    },
    "prior_failures": [
        {
            "pattern": str,
            "last_seen": str,
            "frequency": int,
        }
    ],
    "confidence": float,  # 0-1 based on data completeness
    "confidence_factors": [str],  # What reduced confidence
}
```

**Risk Level Thresholds:**
- `low`: score < 0.3
- `medium`: score 0.3-0.5
- `high`: score 0.5-0.7
- `critical`: score >= 0.85

**Risk Factors Considered:**
1. Number of affected modules (0-0.3)
2. Critical module involvement (0-0.25)
3. Test coverage gaps (0-0.25)
4. Prior failure patterns (0-0.2)

**Critical Modules** (elevated risk weight):
- shared_utilities (1.5x)
- database (1.4x)
- wre_core (1.3x)
- ai_overseer (1.2x)
- foundups_selenium (1.2x)

**Confidence Reduction:**
- No test coverage data: -0.2
- No prior failure data: -0.15
- HoloIndex not available: -0.1
- Many affected modules (>10): -0.1
- Limited dependency resolution: -0.1

---

### HoloIndex Recall (v1.3)

#### `holo_search(query, scope="all", top_k=10)`

Semantic search across the repository using HoloIndex.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| query | str | - | Search query |
| scope | str | "all" | Filter: "all", "code", "wsp", "test", "skill" |
| top_k | int | 10 | Maximum results |

**Returns:**
```python
{
    "query": str,
    "scope": str,
    "hits": [
        {
            "type": "code" | "wsp" | "test" | "skill",
            "path": str,
            "relevance": float,  # 0-1 semantic similarity
            "preview": str,
        }
    ],
    "hit_count": int,
    "fallback_note": str,  # Present if using ripgrep fallback
}
```

**Fallback:** Uses ripgrep text search if HoloIndex unavailable.

#### `holo_related(target, relation_type="all", limit=10)`

Find modules related to target via multiple signals.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| target | str | - | Module name or file path |
| relation_type | str | "all" | "dependency", "co_change", "failure", "all" |
| limit | int | 10 | Maximum results |

**Returns:**
```python
{
    "target": str,
    "relation_type": str,
    "related": [
        {
            "module": str,
            "relation": "depends_on" | "depended_by" | "semantic_similar" | "co_changed",
            "strength": float,  # 0-1 relation strength
        }
    ],
    "related_count": int,
    "sources_used": [str],  # e.g., ["dependencies", "holoindex_semantic", "co_change"]
}
```

**Sources:** Dependency graph, HoloIndex semantic search, git co-change analysis.

#### `holo_failure_memory(query, limit=10)`

Recall failure patterns from memory.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| query | str | - | Search query for failures |
| limit | int | 10 | Maximum results |

**Returns:**
```python
{
    "query": str,
    "failures": [
        {
            "pattern": str,
            "module": str,
            "last_seen": str,
            "frequency": int,
            "severity": str,
            "source": "adaptive_learning" | "holoindex" | "modlog",
        }
    ],
    "failure_count": int,
    "sources_used": [str],
}
```

**Sources:** AI Overseer adaptive learning, HoloIndex, ModLog scanning.

#### `holo_pattern_search(query, limit=10)`

Search learned patterns.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| query | str | - | Pattern search query |
| limit | int | 10 | Maximum results |

**Returns:**
```python
{
    "query": str,
    "patterns": [
        {
            "name": str,
            "type": "learned_pattern" | "012_pattern" | "wsp_pattern",
            "data_preview": str,
            "relevance": float,
        }
    ],
    "pattern_count": int,
    "sources_used": [str],
}
```

**Sources:** adaptive_learning/*.json, ChromaDB PatternMemory, WSP protocols.

#### `holo_task_packet(task_description, include_patterns=True, include_failures=True)`

Assemble context packet for a task.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| task_description | str | - | Description of the task |
| include_patterns | bool | True | Include relevant patterns |
| include_failures | bool | True | Include failure warnings |

**Returns:**
```python
{
    "task": str,
    "relevant_modules": [
        {"module": str, "path": str, "relevance": float}
    ],
    "relevant_docs": [
        {"module": str, "doc_type": str, "excerpt": str}
    ],
    "relevant_patterns": [...],
    "known_risks": [
        {"risk": str, "module": str, "severity": str}
    ],
    "suggested_wsp": [
        {"title": str, "path": str, "summary": str}
    ],
    "confidence": float,  # 0-1 based on data completeness
}
```

**Use case:** Pre-task context assembly for better prompts.

---

### Signal Normalization (v1.4)

#### `get_overseer_summary()`

Get compressed overseer situational awareness.

**Returns:**
```python
{
    "top_concerns": [
        {"type": str, "summary": str, "severity": str}
    ],
    "mission_activity": {
        "total": int,
        "by_status": dict,
        "completion_rate": float,
    },
    "failure_clusters": [...],
    "hot_modules": [...],
    "system_posture": "stable" | "degraded" | "critical" | "drifting" | "unmonitored",
    "recommended_focus": [...],
}
```

**Confidence sources:** overseer_status, mission_history, failure_patterns, hot_modules, recommended_focus

#### `get_hot_modules(limit=10)`

Get modules ranked by recent volatility and risk.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | int | 10 | Maximum modules to return |

**Returns:**
```python
{
    "modules": [
        {
            "module": str,
            "heat_score": float,  # Heuristic score
            "factors": [str],     # What contributed to score
            "change_count": int,
            "failure_count": int,
            "dependency_count": int,
            "is_critical": bool,
        }
    ],
    "total_scored": int,
    "scoring_note": str,
}
```

**Scoring inputs:** change frequency, critical module status, failure association, dependency centrality

#### `get_repeated_failures(limit=10)`

Get clustered recurring failure patterns.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | int | 10 | Maximum clusters to return |

**Returns:**
```python
{
    "clusters": [
        {
            "signature": str,
            "count": int,
            "total_frequency": int,
            "modules": [str],
            "last_seen": str,
            "severity": str,
            "samples": [...],
        }
    ],
    "total_clusters": int,
    "total_failures_analyzed": int,
}
```

**Sources:** known_failures, holo_failure_memory

#### `get_active_risks(limit=10)`

Get normalized active risk objects.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | int | 10 | Maximum risks to return |

**Returns:**
```python
{
    "risks": [
        {
            "risk_type": str,  # See taxonomy below
            "scope": str,
            "severity": "low" | "medium" | "high" | "critical",
            "confidence": float,
            "evidence_sources": [str],
            "why_it_matters": str,
        }
    ],
    "total_risks": int,
    "risk_taxonomy": [str],
}
```

**Risk taxonomy:**
- `regression_risk`: Risk of breaking existing functionality
- `coordination_risk`: Risk from multi-agent coordination
- `dependency_risk`: Risk from module dependency chains
- `repeated_failure_risk`: Risk from recurring failure patterns
- `drift_risk`: Risk from state or architecture drift
- `context_gap_risk`: Risk from incomplete information

#### `get_recommended_focus(limit=10)`

Get prioritized next-action recommendations.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | int | 10 | Maximum items to return |

**Returns:**
```python
{
    "focus_items": [
        {
            "focus": str,           # What to do
            "why_now": str,         # Why it's urgent
            "priority": int,        # 1=critical, 2=high, 3=medium, 4=low
            "suggested_context": [str],  # Modules/files to load
        }
    ],
    "total_items": int,
    "priority_note": str,
}
```

#### `get_prompt_context_packet(task_description=None)`

Assemble compressed context for Windsurf prompt.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| task_description | str | None | Optional task for relevance filtering |

**Returns:**
```python
{
    "system_posture": str,
    "hot_modules": [{"module": str, "score": float}],
    "active_risks": [{"type": str, "scope": str, "severity": str}],
    "repeated_failures": [{"signature": str, "count": int}],
    "recommended_focus": [{"focus": str, "priority": int}],
    "suggested_files": [str],
    "suggested_wsp": [{"title": str, "path": str}],
    "task_relevance": {
        "task": str,
        "relevant_modules": [str],
        "suggested_wsp": [str],
    } | None,
}
```

**Use case:** Auto-prepare state for next Windsurf prompt. Answers: what should I worry about? what is unstable? what should I load first?

---

### RedDog Context Tools (v1.5, local/internal only)

#### `get_reddog_state()`

Returns a read-only RedDog external-state snapshot with active worker lanes,
open research threads, recent slice lineage, and the live Git commit/branch.
The response uses the ordinary perception envelope and `meta.source="reddog"`.

#### `get_reddog_analysis_context(prompt, target_module=None)`

Assembles a read-only, repository-grounded context packet for 0102 analysis.
It includes the prompt, optional target module, Git state, system posture,
active context, and an optional module-documentation excerpt. The response
uses `meta.source="reddog_context"`; it grants no execution authority.

### FastMCP Streamable HTTP Server (v1.6)

The loopback-only remote surface registers exactly one name in
`REMOTE_READ_ONLY_ALLOWLIST`: `holo_query_bundle`. Repository/documentation,
Overseer/SQLite, dependency, mutation, ambient executable-backed repository,
raw Holo, RedDog-state, signal, and execution tools are not remotely
registered. The
exact MCP route is `/mcp`; optional bearer authentication is a local
development defense. Public HTTPS and OAuth 2.1 authorization remain the
responsibility of an external tunnel/control plane.

```python
from modules.infrastructure.foundups_mcp_bridge.src.mcp_server import (
    REMOTE_READ_ONLY_ALLOWLIST,
    build_mcp_server,
    build_asgi_app,
)
from modules.infrastructure.foundups_mcp_bridge.scripts.launch import (
    run_mcp_bridge_http,
    stop_mcp_bridge_http,
    get_mcp_bridge_status,
    verify_mcp_readiness,
)
```

#### FastMCP lifecycle API

- `build_mcp_server(repo_root=None)` registers only the remote read allowlist
  and removes internal `repo_root` parameters from published tool schemas.
- `build_asgi_app(repo_root=None, auth_token=None, require_auth=True)` raises
  `ValueError` when authentication is required without a nonblank token.
- `run_mcp_bridge_http(...)` owns one direct-PID subprocess and the instance
  lock, and returns `running` only after the protocol canary succeeds. It uses
  the same capability-proven interpreter path whether the parent can import
  FastMCP or not; no in-process server lifecycle is selected.
- `stop_mcp_bridge_http(timeout_sec=5.0)` is idempotent; on a termination
  timeout it retains the lock/runtime handle and reports
  `stop_timeout_still_running`.
- `get_mcp_bridge_status()` reports the current owned runtime state.
- `verify_mcp_readiness(...)` uses the official Streamable HTTP MCP client for
  initialize, `tools/list`, exact allowlist verification, and one safe lexical
  `holo_query_bundle` call before claiming readiness.
- The deprecated SSE-named launch functions are aliases to this same runtime;
  no SSE route exists.

---

### Execution Stubs (v1 Disabled)

These tools return `{"status": "disabled_in_v1"}` with schema information.

| Tool | Future Use |
|------|------------|
| `coordinate_mission` | WSP 77 agent coordination |
| `spawn_agent_team` | WSP 54 team creation |
| `trigger_skill` | WRE skill dispatch |
| `write_file` | Audited file writes |
| `create_branch` | Git branch creation |
| `create_pr` | PR creation |

---

## Response Format

### Success
```python
{
    "status": "ok",
    "data": Any,
    "meta": {
        "timestamp": "ISO8601",
        "source": str,
        # tool-specific metadata
    }
}
```

### Error
```python
{
    "status": "error",
    "error": str,
    "meta": {...}
}
```

### Disabled (v1)
```python
{
    "status": "disabled_in_v1",
    "error": "Tool 'X' is disabled in v1...",
    "data": {
        "tool": str,
        "schema": Dict  # Parameter/return schema
    }
}
```

---

## Security Constraints

- Remote registration is exactly `holo_query_bundle`.
- Its request and public response have exact schema/resource bounds.
- Server and readiness children inherit a closed OS/runtime environment plus
  exact repository, dependency, and optional local-token fields.
- No repository walker, arbitrary file read, SQLite access, write, dispatch,
  or execution API is remotely registered.
