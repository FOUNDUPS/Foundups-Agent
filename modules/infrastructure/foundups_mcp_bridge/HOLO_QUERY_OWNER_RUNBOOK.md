# HoloIndex Query Owner and Trusted Maintenance Runbook

## Purpose

The private query owner is the supported semantic-read boundary for the RedDog
operational consumers migrated in this POC. HoloQueryServiceSupervisor starts
exactly one process at literal `127.0.0.1`,
creates an ephemeral bearer token, and proves authenticated semantic health.
The owner exposes query and health routes only; it never indexes.

The trusted maintenance handshake is a separate host authority. When the
canonical seven-collection proof is absent or stale, it can stop only an owner
that this process owns, run one bounded full refresh, validate the exact new
receipt, and restart the query owner. The supported RedDog query adapter has no
HoloIndex write surface. This is an application contract, not an OS privilege
boundary; hard isolation requires a worker identity without store-write or
process-control permissions.

## Main Integration

Both interactive and headless RedDog preflights call
ensure_reddog_holoindex_operational() before Holo-dependent work. This includes
explicit read-only audit/research/decision E2E, report collection, audit task
enqueue, and OPENCLAW_AUTO_TASKS_ENABLED paths.

Defaults:

- REDDOG_HOLOINDEX_OWNER_AUTO_START=1
- REDDOG_HOLOINDEX_AUTO_MAINTENANCE=1
- HOLOINDEX_SSD_PATH resolves through the canonical storage contract

Set either flag to 0 only for an explicit diagnostic or externally supervised
deployment. If operational preflight fails, the Holo-dependent path fails
closed before worker dispatch.

An externally configured HOLOINDEX_QUERY_SERVICE_URL and
HOLOINDEX_QUERY_SERVICE_TOKEN are accepted only when:

- the URL uses HTTP with literal host `127.0.0.1` at the service root or query
  endpoint;
- the token contains at least 32 characters;
- authenticated health proves semantic readiness and a non-empty canary;
- the reported repository SHA, generation, and freshness-receipt digest match
  the expected binding; and
- every one of the seven baseline collections reports the exact active
  embedding-space fingerprint recorded in the freshness receipt.

A stale external owner is not terminated by this process. Maintenance returns
HOLOINDEX_MAINTENANCE_EXTERNAL_OWNER_UNSUPPORTED.

## Process-Private Handoff

Automatic startup retains the URL and token in a process-private handoff. It
does not export either value to os.environ. In-process RedDog adapters obtain a
fresh authenticated handoff through:

    resolve_reddog_holoindex_owner_handoff()

That resolver checks retained-supervisor process liveness; it does not issue a
health request before every query. A `QUERY_OWNER_POISONED` response causes
the supported private adapter to replace the owned process and retry once.
Explicitly configured external owners are never restarted by this process. A
dead owned process is replaced once; failure returns no handoff. Cleanup stops
the owned process and erases the private tuple. The compatibility
restore_environment argument does not imply that automatic startup edited the
environment.

Explicit environment configuration remains supported for an independently
supervised owner. The supervisor's environment_for_child() is also available
when a trusted host launches a separate restricted child process; callers must
not print, persist, or serialize that mapping.

## Embedding-Space Authority and Offline Cache

Phase 1 treats vector compatibility as a persisted proof, not an inference from
model name or vector dimension. Each of the seven baseline receipt entries must
contain a canonical sha256: embedding-space fingerprint. Query proof compares
that exact value, collection by collection, with the resident backend's active
map and the backend response metadata. A legacy receipt or collection with a
blank fingerprint is therefore stale and the trusted preflight requests full
maintenance; it is never grandfathered into CURRENT.

The private owner forces the authoritative sentence_transformers path by
setting HOLO_USE_TURBOQUANT=0. It also sets search_cache=None: the legacy
SearchCache key is not bound to the freshness generation and cannot safely
serve a resident owner across generation changes. Semantic startup is offline
and recognizes either a complete flat SentenceTransformer cache or a complete
Hugging Face cache at
models--sentence-transformers--all-MiniLM-L6-v2/snapshots/<revision>.
refs/main selects the revision when present. Without that ref, exactly one
complete snapshot may be selected; incomplete or ambiguous candidates fail
closed. Completeness requires the model/config/module artifacts and tokenizer
artifacts used by the fingerprint calculation.

## Trusted Full-Maintenance Sequence

The maintenance handshake performs this exact sequence:

1. Resolve the canonical repository and store identities.
2. Prove a clean Git HEAD, including linked-worktree commondir resolution.
   Phase 1 additionally requires an exclusive repository-writer window for
   refresh; the HoloIndex lease coordinates migrated writers but cannot stop
   an unleased legacy writer or prove a transient edit-and-revert never
   occurred.
3. Load and evaluate the receipt for seven canonical source-scope manifests
   and seven non-empty canonical embedding-space fingerprints. A blank legacy
   fingerprint makes the receipt stale and continues to refresh.
4. Return immediately only if the exact HEAD, store, repository, generation,
   and proofs are current.
5. Reject a stale externally configured owner; stop only an auto-owned owner.
6. Launch an argv-only, shell-false, bounded:

       python -B holo_index.py --index-all --ssd <canonical-store>

7. Sanitize semantic-bypass, source-narrowing, and source-cap environment
   variables. Force authoritative sentence_transformers; offline startup
   accepts a complete flat or Hugging Face snapshot cache only.
8. Require semantic initialization before collection reset. The maintenance
   session writes an IN_PROGRESS invalidation before mutable access.
9. Require all seven collections to finish with complete canonical
   source-manifest proofs, exact embedding-space fingerprints, and no failed
   source.
   A logical collection snapshot mismatch is never retried. A first-open
   `VECTOR_SEGMENT_UNAVAILABLE` result may continue only after two consecutive
   fresh-process proofs of the unchanged receipt, including collection
   snapshots and nearest-neighbor queries, within the original probe timeout.
10. Re-prove the same clean HEAD, reload the atomic receipt, and validate its
    repository/store identities and generation.
11. Start the private owner with the exact SHA, repository-root digest,
    generation, and receipt digest supplied to one authenticated semantic
    startup exchange. Retain the actual returned binding with the live process;
    do not launch a duplicate semantic canary merely to export the
    process-private handoff.

Refresh/index/proof failures preserve a non-current state and return a stable
secret-free code. If refresh and receipt publication succeed but subsequent
owner startup or health fails, the persisted receipt can remain CURRENT while
the operational preflight still returns false. A snapshot-only incremental
receipt cannot satisfy this sequence.

## Lifecycle Truth Table

| Event | Behavior | Operator action |
|---|---|---|
| Exact receipt and authenticated semantic owner are ready | Return operational | Permit Holo-dependent RedDog work |
| Receipt stale and owner is auto-owned | Stop owner, refresh, validate, restart | Observe the returned generation |
| Receipt stale and owner is externally configured | Fail without stopping it | Refresh/restart through its external supervisor |
| Semantic backend unavailable | Abort before collection reset | Restore the cached/approved backend |
| Repository dirty or HEAD changes | Leave/emit invalidation and fail | Restore a clean exact checkout, then retry |
| Backend query times out | Poison owner permanently | Private adapter replaces the owned owner and retries once; external supervisor owns external recovery |
| Owner startup/health fails after successful refresh | Keep the valid CURRENT receipt but return non-operational | Repair owner lifecycle, then re-run authenticated health; do not needlessly restamp the store |
| Controlled host exit or cleanup runs | Stop owned process and erase handoff | Treat old token as invalid |
| Auto-owning host dies abruptly | The v0.4.21+ owner waits on its exact supervisor process and exits; manually launched and pre-v0.4.21 owners have no such proof | Confirm the owned process exited, then re-run authenticated preflight; remediate only a verified legacy/manual owner |

## Timeout and Transport Boundary

The owner intentionally separates cold startup from normal request latency:

- the first authenticated health canary has a 270-second semantic warmup
  budget (configurable only up to 300 seconds);
- each auto-supervisor health request has a 30-second socket window, bounded
  by the remaining total startup budget;
- after a successful canary, health and query work use the ordinary owner query
  budget, which cannot exceed 30 seconds (15 seconds by default); and
- the supervisor has a 300-second total startup budget in which the child must
  become authenticated, semantic, and ready.

Queue wait, repository/freshness proof, backend search, and post-query proof
share the applicable owner deadline. The RedDog client also applies one
monotonic deadline to repository proof and response-body reads; it shortens the
live socket timeout as that deadline approaches. Python's stdlib HTTP
connect-and-header phase, however, exposes a socket inactivity timeout rather
than a strict total wall-clock deadline. Therefore Phase 1 assumes a trusted,
cooperative literal-loopback peer and no hostile same-user port squatter or
deliberate header trickle. Do not describe this as a hostile-local transport
boundary. A production slice must add peer/process identity and an enforceable
total connect/header/body deadline (or replace TCP loopback with suitable local
IPC).

## Cross-Lane Direct-Read Proof

HoloIndex discovery identifies candidates, but the model-backed audit worker
still reads allowed repository files directly to construct its evidence
bundle. After those reads, it proves that the repository is clean and at the
exact HEAD in the HoloIndex query receipt. It repeats the same proof after the
model output is validated and immediately before report acceptance. Either a
dirty state or a different HEAD rejects the report as
REPOSITORY_STATE_CHANGED; a model response cannot bless raced file evidence.

## Security Invariants

- The supported Phase-1 bind and URL host are literal IPv4 loopback
  `127.0.0.1`; `localhost`, alternate `127/8` literals, and IPv6 are rejected.
- Owner and maintenance processes use argv lists with shell=False.
- Tokens are generated with secrets.token_urlsafe(48), are absent from
  arguments and logs, and are never placed in the parent environment.
- Standard streams are disconnected; Windows launches are hidden.
- Redirects are not followed.
- Proxy discovery is disabled for bearer-bearing owner requests.
- Query success requires clean exact HEAD before and after retrieval, a stable
  generation/receipt digest, seven canonical proofs, seven exact
  embedding-space fingerprints, semantic metadata, and at least one semantic
  canary result.
- Owner work, response-body reads, refresh, supervisor startup, and shutdown
  are bounded as described above; stdlib connect/header progress retains the
  explicit cooperative-loopback limitation.

## Concatenation Gate

| Annex contract | Phase-1 mapping | Continuity/proof boundary |
|---|---|---|
| Launch | Interactive/headless RedDog preflight calls the owner bootstrap | Operational result is required before a migrated consumer dispatches |
| Ingress | RedDog owner adapter -> authenticated `127.0.0.1` query/health routes | Bounded request schema; exact caller HEAD enters the query |
| Continuity | The query inherits the calling RedDog work-order/snapshot continuity; the private URL/token tuple is secret lifecycle state, not a continuity record | Cross-surface work continues through existing `continuity_context.py` and RedDog receipts; no competing continuity ID is created |
| State | Canonical HoloIndex store + atomic freshness receipt hold index-generation evidence only | Autonomous task/breadcrumb/event durability remains in canonical AgentDB surfaces; no hidden scheduler or memory authority is created |
| Execution | Trusted-host maintenance executes the exact plan; startup may route its request through governed WRE dispatch | Lease, invalidation, exact plan, complete manifests; the query adapter never becomes an execution plane |
| Supervision | HoloQueryServiceSupervisor/bootstrap owns child readiness, poison replacement, and bounded controlled cleanup | Abrupt host death remains an explicit orphan limitation |
| Smoke | Post-merge activation enters through a migrated RedDog consumer | Exact merge SHA, semantic canary, inherited continuity, and secret-free query receipt |

This table is an operational checklist, not a protocol and not a claim that
unrestricted autonomous FoundUp construction is complete.

## Verification

    python -B -m pytest -q modules/infrastructure/foundups_mcp_bridge/tests/test_holo_query_service.py modules/infrastructure/foundups_mcp_bridge/tests/test_holo_query_service_runtime_safety.py modules/infrastructure/foundups_mcp_bridge/tests/test_holo_query_service_edges.py modules/infrastructure/foundups_mcp_bridge/tests/test_holo_query_service_fastapi_adapter.py modules/infrastructure/foundups_mcp_bridge/tests/test_holo_query_service_http.py
    python -B -m pytest -q modules/infrastructure/foundups_mcp_bridge/tests/test_holo_query_service_supervisor.py modules/infrastructure/foundups_mcp_bridge/tests/test_reddog_holoindex_owner_bootstrap.py modules/infrastructure/foundups_mcp_bridge/tests/test_reddog_holoindex_main_preflight.py modules/infrastructure/foundups_mcp_bridge/tests/test_reddog_holoindex_maintenance_handshake.py
    python -B -m pytest -q modules/communication/moltbot_bridge/tests/test_reddog_main_readonly_operational_bootstrap.py modules/communication/moltbot_bridge/tests/test_reddog_holoindex_maintenance_dispatch.py modules/communication/moltbot_bridge/tests/test_reddog_holoindex_query_boundary.py modules/communication/moltbot_bridge/tests/test_reddog_holoindex_direct_query_boundary.py

The implementation is governed by WSP_00, WSP_15, WSP_22, WSP_50, WSP_62,
WSP_87, and WSP_97. Historical WSP_62 debt remains registered in ROADMAP.md;
this runbook makes no global repository compliance claim.
