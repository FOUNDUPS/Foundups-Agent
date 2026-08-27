# FoundUps Private MCP Bridge

Private, read-only MCP bridge for AI-assisted architectural execution.

**Version**: 1.4.0 (perception + recall + state compression)

## Canonical ChatGPT transport boundary (implementation complete; live acceptance pending)

The bundled server is loopback-only and serves MCP Streamable HTTP at exact
path `/mcp`. A Secure MCP Tunnel or another external OAuth 2.1/auth proxy owns
public HTTPS and ChatGPT authorization; that external control plane is not
implemented or claimed live here. The optional static bearer is only a local
development defense. Legacy SSE is removed; deprecated launcher names route to
the same HTTP runtime and lock.

The remote allowlist contains exactly one tool: `holo_query_bundle`. It
delegates to the generation-bound one-shot owner/bundle adapter. Repository,
documentation, Overseer/SQLite, dependency, raw Holo, Git, RedDog-state, and
signal-normalization tools remain internal/local bridge APIs and are not MCP
remote authority. Public bundle output is secret-redacted,
repository-relative, cycle-safe, and capped at 256 KiB. Readiness uses the
official MCP client for initialize, initialized, tools/list, and one lexical
bundle call. Linked worktrees resolve the capable main MCP environment through
file-only `.git`/`commondir` evidence. Startup always uses one owned subprocess
with the direct interpreter PID; there is no second in-process lifecycle.
Interpreter admission also verifies the exact four versions declared in
`requirements.txt`; an import-capable but version-drifted environment is not a
valid MCP runtime.

## Immutable query replica and owner routing

`reddog_holoindex_query_replica_plan.py` is the read-only trusted-host planner
for an explicit activation transaction. It requires a clean exact repository
HEAD and a CURRENT canonical freshness proof, resolves only the selected
`all-MiniLM-L6-v2` snapshot, and descriptor-hashes that complete model plus the
exact 22-file query-snapshot set twice. Three enumerations bracket those
digest passes; full file and directory identities, generation binding, and
canonical freshness must remain unchanged through the final observation. Links,
reparse points, hardlinks, special files, aliases, hostile scalar/container
shapes, or observed source mutation fail closed. The materializer revalidates
the returned expected manifests against any later source change. The planner
performs no copy, route change, maintenance, owner launch, or activation.

The planner, compact materializer, private route record/CAS store, crash
journal, and inert-by-default activation controller are completed layers. A
manual governed activation at exact main `a7302344424615dc9d061ef408c2de2508660b81`
selected generation `sha256:d654414a...`, passed the stable-route query, and
left the immutable replica unchanged. That receipt proves the controller, not
automatic post-merge composition for a later commit.

`reddog_holoindex_query_route_contract.py`,
`reddog_holoindex_query_route_store.py`, and the extracted confined
`reddog_holoindex_query_route_io.py` implement the private stable-route state
layer. One no-replace `EMPTY` record anchors the file; every `CURRENT`
transition requires the exact prior revision and record digest, increments by
one, and binds its predecessor. A machine-wide lock serializes activators. The
store writes a private `PREPARED` journal before selecting the candidate. A
normal context exit finalizes `COMMITTED` only after an explicit commit request;
exceptions and uncommitted exits restore and re-prove the exact previous record.
Recovery treats `PREPARED` as rollback-only, compares the structurally valid
route digest before selected-root liveness, and therefore restores the exact
predecessor even if a selected candidate root vanished after replacement. It
fails terminally when the route matches neither recorded state. Records and
journals use strict canonical ASCII JSON, copied immutable nested bindings,
duplicate-key rejection, bounded descriptor-confined reads, and private
regular-file/link/path checks. WSP_62 keeps route policy and persistence in
separate sub-200-line classes.

The route store alone does not alter the user environment, resolve semantic
authority, materialize a replica, query an owner, publish an activation
receipt, or activate the current machine. Those duties are composed only by
the explicit activation controller.
The high-risk assumptions and fail-closed decision are attached at
[`docs/clarity/REDDOG_HOLO_QUERY_ROUTE_CONSUMER_ASSUMPTION_AUDIT_20260823.md`](docs/clarity/REDDOG_HOLO_QUERY_ROUTE_CONSUMER_ASSUMPTION_AUDIT_20260823.md).

`reddog_holoindex_query_replica_activation.py` composes the existing
maintenance-only proof, planner, materializer, route CAS, one-shot query, and
private JSON publisher. Default invocation is inert. Real mode first proves
the exact clean repository and a new receipt target, refreshes without starting
an owner, materializes an absent immutable root, validates a fixed semantic
canary before commit, and re-proves the exact clean repository both immediately
after materialization/before route transition and after that canary/immediately
before commit. It then commits the revision/digest-bound route, repeats the
canary through normal route-file resolution, and revalidates the replica after
each query. Authority selection rereads the exact workspace state instead of
fabricating a receipt. A post-commit failure is reported as
`COMMITTED_UNVERIFIED`; a committed route whose receipt publication was
interrupted is finalized on the next identical invocation after a fresh stable
query and immutable revalidation. No file is overwritten or deleted.
The separate assumption audit is
[`docs/clarity/REDDOG_HOLO_QUERY_REPLICA_ACTIVATION_ASSUMPTION_AUDIT_20260823.md`](docs/clarity/REDDOG_HOLO_QUERY_REPLICA_ACTIVATION_ASSUMPTION_AUDIT_20260823.md).

`reddog_holoindex_postmerge_replica.py` is the bounded post-merge composer. It
first builds the same allowlisted private route environment used by the
supported one-shot query: on Windows, a current non-empty user route pointer
replaces an inherited legacy replica root without mutating `os.environ` or
copying unrelated values. It then asks the normal owner path to prove the
canonical refresh identity. When
the stable route still names an older generation, it derives new/no-overwrite
replica and receipt targets from the configured stable route, reuses
`activate_query_replica()`, and reproves the owner. HEAD, generation, and
freshness-receipt digest must exactly equal the canonical refresh proof; a
ready owner with any substituted binding fails closed. The authority
transaction releases its first authority-update lease before this composer,
then reacquires the lease and revalidates authority, repository, and
`origin/main` before durable completion. This ordering passed the real
broker-managed OpenClaw/AgentDB path at exact main `cfd1e0051`: generation
`sha256:60d06274...` was activated, the task completed, and a later governed
owner query plus full immutable revalidation remained unchanged. Later HEADs
still require their own exact-SHA transaction.

`reddog_holoindex_query_replica.py` can materialize one immutable
`holoindex_query_replica.v1` generation into a new, disjoint replica-root
capability. Its two sorted logical manifests are exactly `model` and
`snapshots`: one complete selected `all-MiniLM-L6-v2` model snapshot plus the
generation-bound 22-file sealed set rooted at `vectors/query_snapshots/`.
Model resolver markers must be direct children of the selected model root.
The snapshot-set manifest must bind the canonical generation and contain the
exact seven-collection topology, and every inner path/size/digest must equal
the outer copy manifest before copy begins. Roots, receipt paths, artifact
paths, scalar types, ordering, aliases, and full descriptor-path bounds fail
closed before the first replica-root mutation. New generations contain no
Chroma database, SQLite, HNSW, or other legacy vector-tree payload. The sealed
production API nonmutating-locks the already existing authority-update then
maintenance sentinels, retains both exact sentinel identities/bytes plus the
freshness-receipt descriptor through source snapshot, copy, generation
publication, active publication, and final validation, and then releases in
reverse order. Callers cannot inject copier, lease, receipt, or publisher
authority into the public API.

Phase 2 adds one canonical descriptor parser/verifier and an explicit
`QueryReplicaOwnerRoute`. The resident owner receives the canonical SSD path
only for freshness receipts, leases, and repository/generation proof; its
semantic backend receives only the verified immutable replica generation.
Neither path is inferred from ambient `HOLOINDEX_SSD_PATH`. The descriptor is
reproved before spawn and again before authenticated health. Health and reuse
bind all four public replica fields (descriptor digest, generation ID, replica
ID, and path-identity digest); any missing field or drift fails closed and a
changed exact binding cannot hot-swap a live owner. Absolute replica paths are
not returned in public responses.

Governed Holo maintenance publishes a deterministic immutable snapshot set for
the seven baseline collections before its PASS receipt. The materializer copies
only that exact set from `vectors/query_snapshots/`. The resident owner never
starts Chroma against the replica: it validates every snapshot artifact, loads
the existing bounded exact-vector adapter, and requires the embedded generation
ID to equal the active descriptor. SQLite and HNSW are absent from new replica
generations. Snapshot artifact payload is preflight-bounded to 384 MiB before
publication and again before any query artifact is loaded.

Replica proof is intentionally two-tiered. Initial route resolution and the
isolated owner each perform one complete manifest/digest admission over the
selected model and sealed snapshots. After that admission, route reuse,
startup health, and queries revalidate the unchanged descriptor, canonical
repository/receipt/leases, and the same runtime closure. The sealed backend has
no Chroma/SQLite/HNSW path. The 15-second query deadline is unchanged. The
previous full-tree live replica demonstrated why this narrowing is necessary:
its 8.33 GB closure produced 122--153 second cold owner queries. The narrow
materializer is synthetically verified and completed one exact-main live
materialization/activation at `cfd1e0051`. The resulting 33-artifact,
220,800,343-byte replica returned a fresh CURRENT query and passed full
unchanged post-query proof. This is correctness evidence, not a horizontal
throughput claim.

R16-R19 made route, binding fields, and health containers exact. R20 makes
health transport scalars exact before any conversion: literal `127.0.0.1`,
port 1..65535, trimmed printable token >=32 characters, and finite positive
timeout <=300 seconds. Bool/subclasses/aliases/containers reject before calls.
Only an exact built-in JSON `dict` reaches health access; Mapping substitutes,
dict subclasses, and arbitrary containers reject before any attacker method.
Binding parsing accepts only an exact built-in four-item tuple of exact
built-in, trimmed, printable strings. Expected canonical fields alone may be
explicit empty wildcards;
actual canonical and replica fields are nonempty. No value is coerced and
hostile boolean/string/equality methods are not invoked. R21 parses expected
canonical fields first and the mandatory exact replica tuple second, before
transport validation or HTTP construction; wrappers retain that ordering and
only the already parsed tuple reaches response helpers. Malformed expected
values fail before connection, hashing, route validation, verifier, stop,
spawn, health, or handoff; malformed actual JSON/proof returns not-ready with
`HOLOINDEX_QUERY_SERVICE_BINDING_MISMATCH`. R22 makes JSON representation
unambiguous: duplicate member names at any nesting level and NaN/Infinity
constants reject, while unique exact dictionaries remain valid. Parse,
Unicode, recursion, primitive, and bounded-size failures return unavailable;
the 65,537-byte read and close contract is unchanged. Repeated exact values
across distinct binding fields remain allowed. R23 contains stdlib HTTP
protocol failures from request, response acquisition, and bounded read as
unavailable. Expected HTTP/OSError failures during close are contained only
after a proof has been decided, so they never mask ready or unavailable;
  unexpected/resource exceptions still surface. At R23, the historical
  governed backend closure was 1,360 runtime files at
  `fdf3643a2cb8...befc3592129e`; registry remained 1,527/265.
R24 closes acceptance drift: the slow synthetic loopback probe now carries the
full canonical/query-replica route, binding, split argv, and scrubbed child
environment. Shutdown/close/context behavior moved unchanged into one internal
`Self`-typed lifecycle base; route-less context entry still fails closed.

Phase 2 now wires the three production callers through the same verified route:
one-shot ChatGPT/MCP owner query, maintenance owner startup, and promotion-time
owner verification. The preferred trusted-host configuration is the stable
private `REDDOG_HOLOINDEX_QUERY_ROUTE_FILE`; the legacy explicit
`REDDOG_HOLOINDEX_QUERY_REPLICA_ROOT` remains a migration path, and configuring
both is rejected as ambiguous. Route-file resolution is serialized with the
activation lock but uses the store's nonmutating terminal read. A no-journal
record is admissible only for the initial `EMPTY` state; every `CURRENT` record
requires a `COMMITTED` or `ROLLED_BACK` journal whose selected digest matches.
`PREPARED` fails pending and is never recovered or rewritten by a query
consumer; explicit activation/controller recovery uses the separate mutating
store load. After terminal admission, the resolver requires `CURRENT` and
exact-matches the record's authority, canonical binding, replica root, and all
four public replica fields against a fresh active-descriptor proof. Missing,
relative, stale, ambiguous, uncommitted, or unprovable configuration fails
closed with no owner start, query, promotion, replica creation, or re-index.
This plumbing does **not** delete
old/orphan generations, define rollback/retention, or automatically materialize
from a live store, so operational availability still requires a separately
authorized current-generation materialization transaction. Historical
full-tree live transactions remain valid immutable evidence only when their
descriptor proves one coherent model plus SQLite and complete legacy HNSW
segment cores. They remain audit-readable but are rejected by retained modern
runtime revalidation. The narrow
closure in this working tree is not active production proof until it is merged
and rebuilt at the resulting exact `main`. Phase 1 performs no content
deletion. Failed publication temps, staging trees,
and a failed active name are atomically moved without replacement into an
owned orphan root; the active name is absent only after a successful move.
Rename failure leaves the source name and reports only a relative unsafe path.
Windows copy failure closes all handles and preserves its bounded partial
destination; query materialization quarantines the enclosing staging root.
Direct copy callers retain responsibility for their isolated partial output.
Retention/deletion of preserved objects is a future governed policy.

The owner response flattener treats `limit <= 0` as an empty result and never
admits a first hit through the loop termination check. Explicit module Tier-0
reservation remains bounded by positive caller K.

## Purpose

This module provides the **perception layer** for the AI architect workflow:

```
MCP Bridge (perception) → 0102 (reasoning) → 012 (decision) → Cursor (execution)
```

Trusted in-process callers can use the wider bridge to:
- Inspect repository structure and files
- Access WSP protocol documents
- Read module documentation (README, INTERFACE, ModLog)
- Query AI Overseer state (missions, patterns, failures)
- Generate precise Windsurf prompts based on real repo state

ChatGPT's `/mcp` registration does not expose those legacy tools; it exposes
only the governed `holo_query_bundle` contract described above.

## Local/internal bridge capabilities

The capability catalog below describes direct `FoundUpsMCPBridge` calls only.
It is not the Streamable HTTP tool inventory. Only `holo_query_bundle` is
registered remotely.

### Repo Perception (Active)
| Tool | Description |
|------|-------------|
| `get_repo_tree` | Directory structure with depth control |
| `read_file` | File content access (size-limited, path-filtered) |
| `search_repo` | ripgrep-based search |
| `get_recent_changes` | Git commit history |

### Documentation Access (Active)
| Tool | Description |
|------|-------------|
| `get_wsp_docs` | List all WSP protocol documents |
| `get_module_docs` | Module README.md |
| `get_interface_doc` | Module INTERFACE.md (public API) |
| `get_test_docs` | TestModLog and test README |
| `get_modlog` | Recent ModLog entries |
| `get_violations` | Known WSP violations |

### Overseer Perception (Active)
| Tool | Description |
|------|-------------|
| `get_mission_history` | AI Overseer mission records |
| `get_pattern_memory` | Learned patterns (WSP 48) |
| `get_overseer_status` | Current system status |
| `get_coordination_state` | Active teams and phases |
| `get_known_failure_patterns` | Error avoidance patterns |

### Dependency Perception (Active - v1.1)
| Tool | Description |
|------|-------------|
| `get_module_dependencies` | What does module X depend on? |
| `get_reverse_dependencies` | What depends on module X? (blast radius) |

### Diff Perception (Active - v1.1)
| Tool | Description |
|------|-------------|
| `get_file_diff` | What changed in file Y? |
| `get_diff_summary` | What changed across commit range Z? |

### Impact Prediction (Active - v1.2)
| Tool | Description |
|------|-------------|
| `get_change_impact_score` | What is the blast radius? Risk level, test gaps, prior failures |

### HoloIndex Recall (Active - v1.3)
| Tool | Description |
|------|-------------|
| `holo_search` | Semantic search across repo (HoloIndex + ripgrep fallback) |
| `holo_related` | Find modules related to target (deps + semantic + co-change) |
| `holo_failure_memory` | Recall failure patterns from memory |
| `holo_pattern_search` | Search learned patterns (adaptive learning + ChromaDB) |
| `holo_task_packet` | Assemble context packet for a task |

### Signal Normalization (Active - v1.4)
| Tool | Description |
|------|-------------|
| `get_overseer_summary` | Compressed situational awareness (concerns, posture, focus) |
| `get_hot_modules` | Modules ranked by volatility/risk/change frequency |
| `get_repeated_failures` | Clustered recurring failure patterns |
| `get_active_risks` | Normalized risk objects with severity/confidence |
| `get_recommended_focus` | Prioritized next-action recommendations |
| `get_prompt_context_packet` | Auto-assembled context for Windsurf prompts |

### Execution Stubs (Disabled in v1)
| Tool | Status | Future Use |
|------|--------|------------|
| `coordinate_mission` | disabled_in_v1 | Agent team coordination |
| `spawn_agent_team` | disabled_in_v1 | WSP 54 team creation |
| `trigger_skill` | disabled_in_v1 | WRE skill dispatch |
| `write_file` | disabled_in_v1 | Audited file writes |
| `create_branch` | disabled_in_v1 | Git branch creation |
| `create_pr` | disabled_in_v1 | PR creation |

## Usage

### Private HoloIndex Query Owner

The RedDog operational consumers migrated in this POC use this module's owner
at literal `127.0.0.1` instead of opening Chroma directly. Trusted host
bootstraps own its lifecycle
through HoloQueryServiceSupervisor, which generates an ephemeral token, proves
authenticated semantic readiness, can supply a trusted child environment, and
cleans up the process. Before expensive semantic startup it rejects an occupied
loopback port. Direct/resident bootstrap retains port 8127 by default. The
supported one-shot wrapper instead selects one of 64 process-sharded ports
(8127--8190) and gives every process-owned second attempt a diversified shard.
That bounded retry set includes the stable
`HOLOINDEX_QUERY_SERVICE_PORT_IN_USE` acquisition failure, startup exit, and
the existing poisoned-owner/semantic-backend/Tier-0 transient failures. Every
shard still receives its own process-private token and exact authenticated
binding; the caller never intentionally adopts or kills a known pre-existing
listener and never treats a port probe as identity. A post-probe bind race is
outside the same-user hostile-squatter claim and must fail authenticated health.
Automatic startup binds the child to the exact supervisor
process, so the child exits after an abruptly terminated parent without a
blocking stdin reader.
Replica-routed startup requires explicit `--canonical-ssd-path` and
`--query-replica-root` arguments plus a retained verified route capability.
The child environment deliberately omits `HOLOINDEX_SSD_PATH`.
Ordinary authenticated semantic health probes use up to 30 seconds. During
supervisor startup, the first cold semantic canary may use the owner's
270-second warmup budget within the unchanged 300-second total deadline.
Automatic in-process startup keeps the URL/token in a
private handoff resolved by resolve_reddog_holoindex_owner_handoff(); it never
exports the generated secret to the parent environment. See
[HOLO_QUERY_OWNER_RUNBOOK.md](HOLO_QUERY_OWNER_RUNBOOK.md).

On Windows, the one-shot wrapper privately rereads only the current-user
authority-root and stable-route-file values. A non-empty user route pointer
supersedes an inherited legacy replica-root value in that copied mapping; the
process environment is unchanged and the low-level resolver still rejects
dual configuration. Pointer precedence grants no authority: the existing
private-path, terminal-journal, repository, receipt, generation, descriptor,
and immutable-replica proofs must all pass before owner startup. This removes
the former restart/manual-sanitation dependency for long-lived IDE and MCP
processes without reading user-scope credentials.

Port sharding is bounded multi-caller availability, not horizontal scale. Each
independent process still initializes a model-backed owner. The next scaling
layer is one per-user resident broker with authenticated, current-user local
IPC and an in-memory bearer; it requires a separate security and lifecycle
acceptance slice.

For basename queries, HoloIndex resolves intent against a complete bounded Git
HEAD module catalog rather than top-K hits. Full module paths bypass that
catalog. The catalog rejects Unicode control, format, and surrogate code
points on every record and treats NFC-equivalent case-folded paths as
duplicates without rewriting visible Unicode. The owner reserves flattened Tier-0 slots only for one complete,
singular README/INTERFACE pair when canonical metadata `tier0_module_target`,
query intent, root paths, and `exact_metadata` provenance all agree. Missing,
unrelated, ambiguous, multi-module, partial, mixed-module, duplicate, or forged
claims keep global score order. Exact provenance alone does not attest intent;
the owner does not synthesize evidence or promote nested test docs.

Strict catalog failure is
`HOLOINDEX_MODULE_INTENT_SNAPSHOT_UNAVAILABLE`; non-strict HoloIndex logs one
stable warning and continues with basename promotion suppressed. The owner
also preserves `HOLOINDEX_TIER0_INCOMPLETE` and
`HOLOINDEX_TIER0_LOOKUP_FAILED`, while rejecting all non-allowlisted producer
detail as generic semantic unavailability. Deterministic catalog/incomplete
failures are not retried; lookup failure retains one bounded process-owned
retry.

The RedDog read-only operational preflight calls the process-lifetime
bootstrap automatically for E2E, report collection, audit enqueue, and
OPENCLAW_AUTO_TASKS_ENABLED paths. Replica routing is mandatory and fail-
closed: preflight resolves a verified `QueryReplicaOwnerRoute` from the stable
private route file, or from the isolated legacy-root migration input when the
route file is absent. Synthetic owner proof is not live ChatGPT/MCP
availability. Set
REDDOG_HOLOINDEX_OWNER_AUTO_START=0 to opt out. An already configured HTTP
service URL using literal `127.0.0.1` and a strong token bypass process creation only after its
authenticated health endpoint proves semantic readiness and the expected
repository/generation/receipt-digest binding plus exact embedding-space
fingerprints for all seven baseline collections.

Trusted interactive/headless preflight also defaults
REDDOG_HOLOINDEX_AUTO_MAINTENANCE=1. A stale canonical receipt causes one
bounded semantic index-all refresh only after a clean exact-HEAD proof. The
handshake strips source-narrowing and cap controls, requires complete
canonical manifests for all seven baseline collections, re-proves HEAD, and
starts the private owner against that exact generation. Startup may route the
request through governed WRE dispatch, while maintenance authority remains
with the trusted host. It never stops a stale externally configured owner.
A legacy blank embedding-space fingerprint is not accepted as historical
compatibility: it makes the receipt stale and triggers this maintenance path.

The trusted launcher removes ambient Python overrides and resolves at most one
checkout-local dependency directory. It conveys that directory separately as
`HOLOINDEX_MAINTENANCE_PROBE_SITE_PACKAGES`; the maintenance process
revalidates it before invalidation and creates a fresh in-memory proof of the
actual process image. `MaintenanceSession` forwards the path/proof pair
unchanged only to the existing fresh-process snapshot verifier. The proof is
never serialized or logged, and no provider credential crosses the child
boundary. Only a direct caller with no governed runtime input retains the
runtime-free contract. A governed invalid/ambiguous/link runtime is never
silently omitted: the launcher returns
`HOLOINDEX_FINAL_COLLECTION_SNAPSHOT_PROBE_FAILED` before spawn. Child-side
path, process-image, or partial-pair rejection uses stable detail
`RUNTIME_DEPENDENCY_UNAVAILABLE`. There is no retry or vector-proof downgrade.

For one-shot owner routing, `REDDOG_HOLOINDEX_AUTHORITY_REPO_ROOT` must name a
dedicated clean authority checkout, not the active caller worktree. Keep that
checkout immutable and reserve an exclusive repository-writer window through
refresh and final receipt publication. The parent retains at most 16 KiB of
child stdout in memory, writes no capture file, discards stderr and diagnostic
detail, and propagates only an allowlisted stable error from the final JSON
line; every untrusted shape falls back to the generic refresh-failed code.
On Windows, timeout makes a bounded exact-PID `taskkill /T /F` attempt. If
`taskkill` is missing, denied, or times out, bounded direct-child kill/wait is
the fallback; an escaped descendant can retain stdout and the daemon reader
until that descendant exits. POSIX signals the exact isolated process group,
but a descendant that starts a new session escapes it. The reader exclusively
owns pipe closure. This is cooperative trusted-host best-effort containment,
not a hostile-process or OS-privilege guarantee; never assume the whole tree is
gone.

For manual diagnostics only, set a strong shared token outside the repository,
then launch the host-owned process:

    $env:HOLOINDEX_QUERY_SERVICE_TOKEN = "<outside-repo secret>"
    $env:HOLOINDEX_SSD_PATH = "E:/HoloIndex"
    python -m modules.infrastructure.foundups_mcp_bridge.src.holo_query_service --host 127.0.0.1 --port 8127

Configure the RedDog worker with:

    $env:HOLOINDEX_QUERY_SERVICE_URL = "http://127.0.0.1:8127"
    $env:HOLOINDEX_QUERY_SERVICE_TOKEN = "<same outside-repo secret>"

The service exposes only authenticated query and health routes. It never
indexes. Query success is semantic-only, generation-bound, and CURRENT only
when all seven baseline collection proofs match the exact caller repository
HEAD before and after retrieval; health also requires a non-empty semantic
canary. FastAPI is optional; the same command uses the stdlib HTTP runtime when
FastAPI is unavailable.

Successful responses first pass the producer-owned executable HoloIndex result
contract, then project every canonical path/location under the proven
repository root to repository-relative POSIX form. Unknown, incomplete,
cross-bucket, alias/count-divergent, or Unicode-control-bearing evidence fails
closed with empty raw and flattened results. Indexed text remains untrusted
evidence, never instructions, and query handling never reindexes the store.

The owner forces the authoritative sentence_transformers backend, discovers
complete flat and Hugging Face models--.../snapshots/<revision> caches for
offline startup, and disables the generation-unbound legacy SearchCache. Cold
semantic initialization is reserved for the first authenticated health canary
(270-second default warmup); ordinary queries are capped at 30 seconds, and the
supervisor's total startup budget is 300 seconds.

RedDog response-body reads and owner proof/search work use monotonic absolute
deadlines. The stdlib HTTP connect/header phase remains socket-inactivity
bounded. Phase 1 therefore assumes a trusted cooperative literal-loopback peer
and no hostile same-user port squatter or deliberate header trickle; it is not
a hostile-local transport security claim. Model-backed cross-lane audits also
re-prove the clean exact HoloIndex receipt HEAD after direct file reads and
again immediately before accepting their reports.

This is a supported API boundary, not an OS privilege boundary. Deploy a
worker identity without store-write/process-control permissions when hard
isolation is required. The legacy `src/holo_tools.py` MCP surface remains a
direct-store consumer outside this Phase-1 migration. Full refresh also
requires an exclusive writer window because unleased legacy writers and a
transient edit/revert are not excluded by the cooperative maintenance lease.
Maintenance re-proves clean exact HEAD at the final publication boundary; a
dirty or changed checkout leaves the IN_PROGRESS receipt in place.
After a successful refresh, owner lifecycle failure can leave the receipt
CURRENT while preflight remains non-operational. Abrupt host death can leave an
orphan owner until verified process cleanup and token rotation.

### CLI Testing

```bash
# Show bridge status
python -m modules.infrastructure.foundups_mcp_bridge.src.bridge_server --status

# List available tools
python -m modules.infrastructure.foundups_mcp_bridge.src.bridge_server --list-tools

# Call a tool
python -m modules.infrastructure.foundups_mcp_bridge.src.bridge_server \
    --call get_repo_tree \
    --args '{"path": "modules", "depth": 2}'

# Read a file
python -m modules.infrastructure.foundups_mcp_bridge.src.bridge_server \
    --call read_file \
    --args '{"path": "WSP.txt"}'

# Get overseer status
python -m modules.infrastructure.foundups_mcp_bridge.src.bridge_server \
    --call get_overseer_status

# Get module dependencies (v1.1)
python -m modules.infrastructure.foundups_mcp_bridge.src.bridge_server \
    --call get_module_dependencies \
    --args '{"module_name": "ai_overseer"}'

# Get reverse dependencies / blast radius (v1.1)
python -m modules.infrastructure.foundups_mcp_bridge.src.bridge_server \
    --call get_reverse_dependencies \
    --args '{"module_name": "shared_utilities"}'

# Get diff summary (v1.1)
python -m modules.infrastructure.foundups_mcp_bridge.src.bridge_server \
    --call get_diff_summary \
    --args '{"commit_range": "HEAD~5..HEAD"}'

# Get change impact score (v1.2)
python -m modules.infrastructure.foundups_mcp_bridge.src.bridge_server \
    --call get_change_impact_score \
    --args '{"target_type": "module", "target": "ai_overseer"}'

# Impact score for commit range
python -m modules.infrastructure.foundups_mcp_bridge.src.bridge_server \
    --call get_change_impact_score \
    --args '{"target_type": "commit_range", "target": "HEAD~3..HEAD"}'

# Semantic search (v1.3)
python -m modules.infrastructure.foundups_mcp_bridge.src.bridge_server \
    --call holo_search \
    --args '{"query": "WSP protocol validation", "scope": "all", "top_k": 10}'

# Find related modules (v1.3)
python -m modules.infrastructure.foundups_mcp_bridge.src.bridge_server \
    --call holo_related \
    --args '{"target": "ai_overseer", "relation_type": "all", "limit": 10}'

# Search failure memory (v1.3)
python -m modules.infrastructure.foundups_mcp_bridge.src.bridge_server \
    --call holo_failure_memory \
    --args '{"query": "import error", "limit": 5}'

# Search learned patterns (v1.3)
python -m modules.infrastructure.foundups_mcp_bridge.src.bridge_server \
    --call holo_pattern_search \
    --args '{"query": "refactoring", "limit": 10}'

# Assemble task context (v1.3)
python -m modules.infrastructure.foundups_mcp_bridge.src.bridge_server \
    --call holo_task_packet \
    --args '{"task_description": "Add new validation to ai_overseer"}'
```

### Programmatic Use

```python
from modules.infrastructure.foundups_mcp_bridge.src import FoundUpsMCPBridge

bridge = FoundUpsMCPBridge()

# Get status
status = bridge.get_status()
print(status["data"]["version"])  # "1.2.0"
print(status["data"]["mode"])     # "perception-only"

# Read WSP docs
wsp_docs = bridge.call_tool("get_wsp_docs")
for doc in wsp_docs["data"]["wsp_docs"]:
    print(doc["name"])

# Get overseer mission history
missions = bridge.call_tool("get_mission_history", limit=10)
for m in missions["data"]["missions"]:
    print(f"{m['mission_id']}: {m['status']}")

# Call disabled tool (returns schema, no execution)
result = bridge.call_tool("coordinate_mission", mission_description="Test")
print(result["status"])  # "disabled_in_v1"
print(result["data"]["schema"])  # Schema definition
```

## Response Schema

All tools return unified responses:

```json
{
  "status": "ok",
  "data": { ... },
  "meta": {
    "timestamp": "2026-04-14T...",
    "source": "repo|overseer|wsp|..."
  }
}
```

Error responses:
```json
{
  "status": "error",
  "error": "Error message",
  "meta": { ... }
}
```

Disabled tool responses:
```json
{
  "status": "disabled_in_v1",
  "error": "Tool 'X' is disabled in v1 (perception-only mode)",
  "data": {
    "tool": "X",
    "schema": { ... }
  }
}
```

## Security

- **Remote surface** - Exactly one bounded `holo_query_bundle` tool
- **Private transport** - Loopback only; public control plane remains external
- **No remote repository/SQLite walkers** - Legacy perception APIs stay local
- **Closed child environment** - Only allowlisted OS/runtime fields plus exact
  repository/package/token fields reach server and readiness children
- **No remote mutation or execution** - Tool annotations match the admitted path

## Isolated HoloIndex Candidate Acceptance

The trusted-host adapter can validate one exact clean candidate SHA without
promoting or writing the canonical HoloIndex store. Its default CLI mode is
import-inert as well as effect-inert: help, malformed input, and omission of
`--real` do not import the acceptance runtime. `--real` is the only authority
for the isolated model copy, full refresh, private owner start, two direct
queries, and cleanup.

The adapter requires a distinct clean detached authority worktree at the exact
candidate SHA and a third clean, related dependency-only runtime checkout with
exactly one verified checkout-local `.venv/Lib/site-packages`. The runtime HEAD
need not equal the candidate SHA and never becomes source authority. A new store
disjoint from all three repositories and the canonical store, a new receipt
target, a locally resolvable canonical model snapshot, and an available literal
`127.0.0.1:8127` private port with no existing private handoff are also required.
One non-blocking in-process lock and one host-local cross-process lease
serialize the canonical-store/port acceptance session. Port availability is not
owner identity: a pre-existing handoff, known foreign listener, post-check bind
race, or missing newly created handoff fails closed without killing or reusing
it. The boundary is not hardened against a hostile same-user process.

The final fresh-process snapshot separates source authority from dependency
authority. It runs the resolved base interpreter from the candidate cwd with
`-S -B`, an exact `PYTHONPATH` containing only the already-proven runtime
site-packages, no user site, and the standard child-environment scrub. Before
opening the store, it proves candidate module origin plus ChromaDB 1.5.5 origin
under that runtime. `CANDIDATE_SOURCE_ORIGIN_INVALID`,
`RUNTIME_DEPENDENCY_UNAVAILABLE`, and `UNSUPPORTED_CHROMADB_VERSION` are stable,
generation-bound failures; the deterministic snapshot has no transient retry.
The base interpreter is not selected from mutable `sys.executable` or
`sys._base_executable`. Runtime admission obtains the actual current-process
image from the OS, rejects alias/link/reparse/hardlink ambiguity, and binds its
case-preserving final path plus stable file identity in an in-memory proof.
At the runtime-bound isolated-probe runner boundary, a fresh verified descriptor
is retained until the runner returns or raises. Windows launches the exact path
while the non-sharing handle denies write/delete replacement. Linux launches
`/proc/self/fd/<fd>` and passes that descriptor into the child, so pathname
replacement cannot select a different image. Revalidation failure prevents the
runner call; the descriptor closes on every exit. The legacy runtime-free probe
does not consume this proof. The shared child scrubber also removes
`PYTHONINSPECT` along with home/path/startup/user-base overrides.

The model copy uses bounded descriptor I/O. On Windows, source/destination files
and every traversed parent are pinned and re-proved through live handles using
the repository's established verified-handle/no-replace pattern; artifact
digests are computed from those descriptors. Live per-file or aggregate growth,
parent/root replacement, any bound overrun, or digest drift fails closed. The
adapter hashes the canonical freshness receipt before and after and never
downloads or installs a model.

Success requires `REFRESHED`, exact SHA, one generation/receipt binding across
both direct queries, explicit private-owner cleanup, and then one K=1 query
through the supported extension wrapper using candidate self-selection. The
activation receipt must bind the candidate root/SHA and the same generation;
canonical rehydration and a fresh-process collection snapshot must still pass
after that wrapper has cleaned up. Receipts retain only the activation receipt
digest/count, semantic-store verdict, and one-way owner-session digest, never
query results, paths, URLs, or tokens. The session digest is captured when the
exact handoff is acquired and survives cleanup without retaining another copy
of the secret tuple. The rehydrated freshness receipt remains open through one
confined descriptor: strict bounded parsing and exact SSD/root/SHA/generation/
file-digest binding are revalidated immediately before and after the isolated
snapshot probe.
Cleanup uses an atomic expected-handoff comparison, so a replaced owner is not
stopped. Receipts are immutable, bounded, deterministic, secret-free JSON; an
unsafe target is never written and publication failure cannot report PASS.

The isolated store is semantic-path-bound. A detached worktree at the same SHA
is not interchangeable because the freshness receipt binds the repository root.
Do not set `REDDOG_HOLOINDEX_AUTHORITY_REPO_ROOT` for acceptance activation;
the clean candidate must select itself and resolve the primary runtime through
the supported wrapper. ChromaDB 1.5.5 inserts one `acquire_write` lifecycle row
when `PersistentClient` opens, including logical read-only queries. Acceptance
therefore proves semantic non-mutation through unchanged generation/root/
receipt and collection snapshots, not byte-for-byte SQLite identity. The
unbounded lifecycle-row growth is unresolved scale debt, not a correctness
failure and not a resolved capacity claim.
One authorized live attempt at `fb72cbd99bc9499545823fa1849fc4597b8d71ec`
failed and did not establish acceptance. Its immutable FAIL receipt has SHA-256
`f9b5e18ce62e63af3bbbf0e0f3d36def5614216fafadca8872703f519be43a78`, reports
`NEW_PRIVATE_OWNER_HANDOFF_MISSING`, zero queries, and an unchanged canonical
receipt. Audit found that a primary `HOLOINDEX_MAINTENANCE_REFRESH_FAILED` result
was masked by the missing-handoff check and that candidate/authority worktrees
lacked runtime dependencies. Both defects are hardened. The failed store is
retained as evidence and is never reusable: any authorized retry requires a new
store and receipt target. No current-contract live PASS, promotion, or capacity
claim exists.
The later R7 attempt at `220fdd9febbac00ddde9acbf7d8673ef0888b367`
completed two direct queries and one activation query but failed the semantic
snapshot after 917.4 seconds because the child inherited user-site ChromaDB
1.3.0 instead of the validated runtime's 1.5.5. Its retained 1,155-byte FAIL
receipt has SHA-256
`305a53b7c63b64762bb3706fb03bec76c35c3358fbc4a607c89567c7a6c1bd78`.
R8 closes that runtime-selection defect in code only; it makes no live-PASS,
promotion, or scale claim.
A PASS retained for `b482fdaed4932a15b2b195c256761cfd1053f053` is historical
pre-R5 evidence only: it did not include the post-cleanup supported-wrapper
activation and semantic revalidation now required, so it cannot activate or
promote the current code.

See [HOLO_QUERY_OWNER_RUNBOOK.md](HOLO_QUERY_OWNER_RUNBOOK.md#isolated-candidate-acceptance)
for STOP conditions, commands, and RED/GREEN evidence.

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    FoundUpsMCPBridge v1.4.0                              │
├──────────────────────────────────────────────────────────────────────────┤
│  Repo Tools       │  Doc Tools        │  Overseer Tools                  │
│  - get_repo_tree  │  - get_wsp_docs   │  - get_mission_history           │
│  - read_file      │  - get_module_docs│  - get_pattern_memory            │
│  - search_repo    │  - get_interface_ │  - get_overseer_status           │
│  - get_recent_    │    doc            │  - get_coordination_state        │
│    changes        │  - get_test_docs  │  - get_known_failure_patterns    │
│                   │  - get_modlog     │                                  │
│                   │  - get_violations │                                  │
├──────────────────────────────────────────────────────────────────────────┤
│  Dependency Tools (v1.1)       │  Diff Tools (v1.1)                      │
│  - get_module_dependencies     │  - get_file_diff                        │
│  - get_reverse_dependencies    │  - get_diff_summary                     │
├──────────────────────────────────────────────────────────────────────────┤
│  Impact Prediction (v1.2)                                                │
│  - get_change_impact_score (risk_level, test_coverage, prior_failures)   │
├──────────────────────────────────────────────────────────────────────────┤
│  HoloIndex Recall (v1.3)                                                 │
│  - holo_search, holo_related, holo_failure_memory                        │
│  - holo_pattern_search, holo_task_packet                                 │
├──────────────────────────────────────────────────────────────────────────┤
│  Signal Normalization (v1.4)                                             │
│  - get_overseer_summary, get_hot_modules, get_repeated_failures          │
│  - get_active_risks, get_recommended_focus, get_prompt_context_packet    │
├──────────────────────────────────────────────────────────────────────────┤
│  Execution Stubs (DISABLED in v1)                                        │
│  - coordinate_mission, spawn_agent_team, trigger_skill                   │
│  - write_file, create_branch, create_pr                                  │
└──────────────────────────────────────────────────────────────────────────┘
```

## WSP References

- **WSP 97**: Truthful verification (no fake data)
- **WSP 48**: Recursive Self-Improvement (pattern memory access)
- **WSP 77**: Agent Coordination (mission state access)
- **WSP 49**: Module structure (doc file locations)
- **WSP 22**: ModLog documentation

## Future (v2)

- Live semantic Holo availability is accepted at exact main `cfd1e0051` with a
  generation-bound CURRENT freshness receipt and unchanged immutable replica.
  The governed bundle tool is implemented. Public ChatGPT/tunnel acceptance
  remains a separate deployment boundary.
- Gated execution capabilities
- Agent team spawning
- Skill dispatch with approval workflow

## Streamable HTTP migration status

The former SSE surface is retired. The canonical local endpoint is exact
Streamable HTTP `/mcp`, loopback-only, with one bounded read-only tool.
`run_mcp_bridge_sse` and `stop_mcp_bridge_sse` remain deprecated name aliases
for the same HTTP runtime and lock; they do not expose an SSE route. Public
HTTPS plus OAuth 2.1 authorization belongs to an external tunnel/control plane
and remains live-acceptance work. Local protocol validation does not claim a
public tunnel or ChatGPT app connection.
