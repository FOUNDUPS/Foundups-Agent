# HoloIndex Query Owner and Trusted Maintenance Runbook

## Purpose

The private query owner is the supported semantic-read boundary for the RedDog
operational consumers migrated in this POC. HoloQueryServiceSupervisor starts
exactly one process at literal `127.0.0.1`,
creates an ephemeral bearer token, and proves authenticated semantic health.
The owner exposes query and health routes only; it never indexes.

Direct/resident bootstrap uses loopback port 8127 unless an exact built-in
port in 1..65535 is supplied. Independent supported one-shot callers select a
PID-sharded candidate in 8127..8190 and may advance once after a bounded
transient error including `HOLOINDEX_QUERY_SERVICE_PORT_IN_USE`. A port is never
ownership evidence: every owner still uses a process-private bearer and exact
authenticated binding. A known pre-existing listener is not adopted or killed;
a post-probe bind race must fail authenticated health and is not a hostile
same-user isolation claim. This is bounded multi-caller
availability, not horizontal scale. A per-user resident broker with
authenticated current-user local IPC is a separate scaling and security slice.

The trusted maintenance handshake is a separate host authority. When the
canonical seven-collection proof is absent or stale, it can stop only an owner
that this process owns, run one bounded full refresh, validate the exact new
receipt, and restart the query owner. The supported RedDog query adapter has no
HoloIndex write surface. This is an application contract, not an OS privilege
boundary; hard isolation requires a worker identity without store-write or
process-control permissions.

## Query-replica materialization and routing boundary

A separate Phase-1 materializer can create one immutable
`holoindex_query_replica.v1` generation. The trusted caller supplies the exact
canonical receipt/generation binding and exactly two sorted manifests: one
complete selected model snapshot whose resolver marker files are direct
children of that root, and the exact generation-bound 22-file snapshot set at
`vectors/query_snapshots/`. A complete legacy `vectors/` tree,
`chroma.sqlite3`, HNSW segments, extra or missing snapshot files, an inner/
outer path-size-digest mismatch, or a snapshot-set generation mismatch fail
before copy. Roots, receipt paths, and manifest paths must have one exact
NFC/POSIX representation before the replica root is changed. Point probes are
insufficient. The materializer
opens no new sentinel: it nonmutating-locks the existing authority-update
sentinel first and maintenance sentinel second, proves each exact regular
non-link/non-reparse identity and bytes, and retains both handles plus the
freshness-receipt descriptor through snapshot, copy, immutable generation
publication, active publication, final validation, and reverse-order release.
The sealed production entrypoint accepts no injected dependency authority.

The active descriptor is not an owner handoff and contains no bearer token.
Phase 2 verifies it into a process-private `QueryReplicaOwnerRoute`. Canonical
storage remains the freshness/receipt/lease authority; only the verified
immutable generation path reaches the semantic backend. The supervisor passes
both roots as explicit argv, removes ambient `HOLOINDEX_SSD_PATH`, reproves the
capability before spawn and health, and requires all four public replica
binding fields. Binding drift fails closed and forces replacement; responses
do not expose the private absolute path. Never point the owner at a
staging directory or infer activation from an inactive generation. Descriptor
publication failure leaves no active descriptor and can leave an immutable
orphan generation for future governed cleanup. If final validation fails after
active publication, Phase 1 atomically moves whatever occupies that active name
without replacement into its owned orphan root. Successful quarantine makes
the active name absent and records only a relative orphan path; rename failure
leaves the active name and reports a relative unsafe path. Failed publication
temps and staging trees are preserved the same way. Phase 1 deletes nothing;
Windows copy failure closes its capabilities but preserves bounded partial
bytes; the materializer then quarantines the enclosing staging root. A direct
copy caller owns its isolated partial destination. Retention or deletion of
these objects requires a later governed policy.

Complete replica verification is an admission operation, not a per-query
operation. The trusted route resolver hashes every descriptor artifact once,
and the isolated owner independently repeats that complete proof once. The
retained route/owner then checks the unchanged descriptor, manifest projection,
canonical repository/receipt/leases, and hashes the selected model plus the
exact `vectors/query_snapshots/` closure. New generations contain only those runtime
artifacts because the immutable in-memory backend has no Chroma/SQLite/HNSW
read surface. Any artifact or authority drift fails closed. Do not replace this
with a time-based cache and do not increase the 15-second query timeout. The
last full-tree exact-main replica measured 122--153 seconds for cold owner
queries; the narrow closure must receive a new exact-main live acceptance and
post-query immutable proof before its latency is claimed. Historical full-tree
descriptors require a coherent model, SQLite, and complete HNSW segment cores;
the full verifier can audit them, but retained runtime revalidation rejects
their non-narrow vector surface.

R16 made route possession mandatory, R17 made replica capability exact, R18
made canonical fields exact, and R19 requires decoded health to be an exact
built-in `dict`. Reject Mapping substitutes, dict subclasses, and arbitrary
containers before reading or formatting them. Only a built-in four-tuple of
exact built-in, trimmed, printable strings is valid. Expected canonical fields alone may be empty wildcards;
actual canonical and replica fields are nonempty. Do not pass duck-typed
containers, subclasses, bytes, mappings, non-string/nested fields, whitespace,
NUL, control text, or wrong lengths. Expected malformation fails before every
side effect. Malformed actual health/proof fields return not-ready with
`HOLOINDEX_QUERY_SERVICE_BINDING_MISMATCH` without coercion or hostile method
calls. R21 makes the authenticated exchange enforce the same rule before
transport: canonical expectation parses first, then the mandatory exact
replica tuple. Invalid replica containers, fields, or lengths return the stable
binding mismatch without constructing HTTP; probe/rejection wrappers inherit
that boundary, and response helpers see only the retained parsed tuple. A
direct context-manager entry still must hold both roots, the
revalidation capability, and the exact binding in its constructor.

R20 also requires exact transport scalars before any conversion: host is the
literal built-in string `127.0.0.1`; token is a trimmed printable built-in
string of at least 32 characters; port is built-in int 1..65535; timeout is a
finite positive built-in int/float no greater than 300 seconds. Direct health
read validates the same token before request or header formatting.

R22 requires strict JSON conformance before any health field is trusted.
Duplicate object keys reject at the top level and every nested object; NaN,
Infinity, and `-Infinity` reject. Invalid UTF-8, malformed syntax, primitives,
oversize bodies, and parser recursion return unavailable rather than ready or a
terminal owner error. The client still reads at most 65,537 bytes and closes
the connection through the existing exchange lifecycle.

R23 treats `IncompleteRead`, bad status/remote disconnect, response-state, and
request-state HTTP exceptions as unavailable at the stage where they occur.
Timeout/OSError behavior is unchanged. Close always runs once after a
connection exists; an HTTP/OSError raised by close cannot mask an already
decided ready or unavailable proof. Other close exceptions are deliberately
not hidden, preventing cleanup code defects or resource failures from vanishing.

R24 acceptance uses a disposable slow loopback server only after supplying the
complete canonical root, query-replica root, verifier, and four-field replica
binding. The fixture proves verifier-before-spawn and verifier-before-health,
split storage argv, and removal of ambient `HOLOINDEX_SSD_PATH`. Context entry
uses the same `start()` gate: configured synthetic routes work and absent routes
fail with `HOLOINDEX_QUERY_REPLICA_REQUIRED` before spawn.

One-shot owner query `_owner_attempt`, maintenance `_start_owner`, and
promotion `_run_locked_promotion` now consume the same verified route
capability. The separate trusted-host activation controller can construct that
route only under explicit real mode, with a fixed semantic canary before and
after commit and a no-replace receipt. This source transaction has not itself
performed a live materialization or installed a user environment pointer;
ChatGPT-app MCP readiness remains a separate transport concern.

Three process-local route keys are allowlisted: authority root, stable route
file, and the legacy migration root. On Windows, the supported one-shot wrapper
rereads exactly two non-secret HKCU values: authority root and stable route
file. A non-empty current-user stable route supersedes and removes an inherited
process-local legacy root only in the route-only copied mapping. It does not
copy credentials or unrelated process configuration and does not mutate
`os.environ`. Precedence grants no authority; the unchanged strict route
resolver must still prove the complete route. Every process-owned second
attempt receives a diversified shard; the bounded retry set includes the full
`HOLOINDEX_QUERY_SERVICE_PORT_IN_USE` code, startup exit, poisoned-owner,
semantic-backend, and Tier-0 lookup failures.

For a linked-worktree caller, repository bytes still come from the selected
clean same-HEAD authority checkout. Runtime dependencies come from the primary
worktree proved by the same Git common directory, then pass the existing
checkout-local virtualenv validation. The primary worktree is dependency
provenance only; its HEAD and working-tree contents are not retrieval evidence.

## Main Integration

Both interactive and headless RedDog preflights call
ensure_reddog_holoindex_operational() before Holo-dependent work. This includes
explicit read-only audit/research/decision E2E, report collection, audit task
enqueue, and OPENCLAW_AUTO_TASKS_ENABLED paths.

Defaults:

- REDDOG_HOLOINDEX_OWNER_AUTO_START=1
- REDDOG_HOLOINDEX_AUTO_MAINTENANCE=1
- direct/resident owner port 8127; supported one-shots use 8127--8190
- canonical freshness storage resolves through the canonical storage contract;
  semantic storage comes only from the verified route generation

`REDDOG_HOLOINDEX_AUTHORITY_REPO_ROOT` must identify a dedicated clean
authority checkout, never the active caller worktree. Keep that checkout
immutable for the complete query/maintenance proof window. Full refresh also
requires an exclusive repository-writer window: do not edit, switch, merge,
or run an unleased writer against that checkout while maintenance is active.
The maintenance lease serializes participating store writers; it is not a
repository lock and cannot prove away a transient edit-and-revert.

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
- all four replica descriptor/generation/identity/path-identity fields exactly
  match the current verified route; and
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

For the supported one-shot wrapper,
`HOLOINDEX_QUERY_SERVICE_PORT_IN_USE` and startup exit join the existing
bounded transient retry reasons. Each process's second attempt differs from its
own first PID-derived shard. The mapping has 4,032 ordered pairs, so processes
separated by that period can still collide on both candidates. The
two-attempt/64-port cap is deliberate and permits terminal contention.

## Isolated Candidate Acceptance

The retained R7 attempt at `220fdd9febbac00ddde9acbf7d8673ef0888b367`
failed after 917.4 seconds. Its immutable 1,155-byte FAIL receipt has SHA-256
`305a53b7c63b64762bb3706fb03bec76c35c3358fbc4a607c89567c7a6c1bd78`,
records two direct queries plus one activation query and unchanged canonical
state, and remains audit evidence only. The exact cause was dependency-authority
drift: the snapshot child inherited user-site ChromaDB 1.3.0 instead of the
validated runtime's 1.5.5. R8 binds the trusted site-packages path in memory,
uses the base interpreter with `-S -B`, and proves origin/version before opening
the store. Do not reuse the failed R7 store or receipt. Any future authorized
attempt requires a new target and still cannot claim PASS until its immutable
receipt says PASS. R8 itself performs no live attempt.

R8 independent verification subsequently proved that mutable Python executable
attributes and inherited `PYTHONINSPECT` could still affect the snapshot child.
R9 corrects both without a live run: acceptance admits only an OS-derived,
descriptor-identity-bound process image, point-re-proves it before spawn,
and uses the existing shared scrubber to remove interactive mode. Never replace
this proof with `sys.executable`, `sys._base_executable`, or a second sanitizer.
R9 establishes no live PASS and does not authorize reuse of the R7 targets.

R10 added exact-case Windows path admission, but still closed its proof handle
before launch and therefore did not close the replacement interval. R11
supersedes that boundary: the runtime-bound probe retains the same freshly
verified executable object through runner return. Windows holds the exact-case,
non-write/non-delete-sharing handle through actual child creation; Linux runs
`/proc/self/fd/<fd>` with that exact descriptor in `pass_fds`. Unsupported POSIX
systems without `/proc` process-image authority fail closed. The capability
closes on both success and error. R10/R11 add no broad-suite, live-acceptance,
or promotion evidence.

This adapter is a trusted-host acceptance boundary, not a query-worker API. It
exists to test a committed candidate without rebuilding or contaminating the
canonical store. The default command is deliberately inert:

```powershell
python scripts/reddog_holoindex_candidate_acceptance.py `
  --candidate-root O:\candidate-clean `
  --authority-root O:\authority-detached `
  --runtime-root O:\Foundups-Agent `
  --canonical-store E:\HoloIndex `
  --isolated-store O:\new-isolated-holo-store `
  --receipt-path O:\new-receipts\candidate-acceptance.json `
  --expected-sha 0000000000000000000000000000000000000000
```

It returns stable `NOT_RUN` without importing the acceptance runtime; malformed
input also exits before that import boundary. Only an explicit `--real`
authorizes effects. Never add `--real` until every precondition below is
independently verified:

1. Candidate and authority are distinct clean linked worktrees sharing one Git
   common directory at the exact supplied SHA; authority is detached.
2. Runtime root is a third distinct, clean, non-reparse checkout sharing that
   Git common directory. Its HEAD is dependency-only, not source authority, and
   exactly one checkout-local `.venv/Lib/site-packages` must be verified.
3. The isolated store does not exist, its parent already exists, and it is
   disjoint from the canonical store and all three repositories in both directions.
4. The receipt target is new, outside canonical/source roots, and its existing
   parent contains no symlink, junction, or reparse component.
5. The canonical SentenceTransformer snapshot resolves locally. Acceptance
   never downloads or installs a model.
6. Literal loopback port 8127 is free and no process-private owner handoff is
   present. Port availability alone is not ownership proof.
7. The canonical freshness receipt exists as a confined private regular file
   within its explicit byte bound.

STOP without `--real` if a worktree is dirty/unrelated/branch-attached, a SHA
differs, any path overlaps or changes identity, a reparse/link/special file is
observed, a model bound/digest fails, a listener or handoff already exists, the
canonical receipt cannot be confined, or the receipt target is not provably
new. A failed acceptance store or receipt is evidence, not a retry target. Do
not kill an unknown listener, repair canonical state, weaken freshness, reuse a
failed store, retry a failed query, or install/download a model from this procedure.

The real-mode boundary acquires a non-blocking process lock and a host-local
cross-process maintenance lease keyed by the canonical-store/port pair before
preflight. A second session stops before preflight. A pre-existing private
handoff or listener stops before maintenance; a listener that wins after the
initial port check remains `OWNER_PORT_NOT_AVAILABLE`; an operational response
without a newly created private handoff is never reused. None of these paths may
clean up or kill a foreign owner.

Real mode applies `HOLOINDEX_SSD_PATH` only inside the dedicated CLI process,
restores its exact prior value in `finally`, and is not safe for concurrent
in-process/library use. It invokes the existing operational handshake with
  `repo_root=candidate`, `owner_runtime_root=runtime`, `requested=True`, and
  `auto_maintenance=True`. Acceptance requires:

- `ready=True`, `status=REFRESHED`, `refreshed=True`, exact SHA, and non-empty
  generation and freshness-receipt digests;
- a new private owner handoff after the refresh;
- exactly one K=1 query and one K=12 query, with no outer retry, both returning
  `ok=True`, `CURRENT`, `index_gap_detected=False`, exact SHA, the same
  generation/receipt, and `no_holoindex_reindex_performed=True`;
- cleanup of the exact private handoff before activation, with no remaining
  handoff;
- one K=1 activation through `scripts/reddog_holoindex_owner_query_once.py`
  using candidate self-selection and primary-runtime resolution; and
- a valid activation receipt plus final `rehydrate_canonical_freshness_proof`
  and fresh-process collection-snapshot proof at the same candidate root, SHA,
  generation, receipt digest, collection counts, and embedding spaces.

The K=12 query is frozen as:

```text
HoloDAE PQN training system UTF8 hygiene MCP testing unicode tools pfmall Tier0 contracts
```

Every model traversal/mutation and later effect revalidates the isolated-store
identity. Cleanup supplies the exact acquired handoff to an atomic comparison
under the owner lock; a replaced handoff returns failure without stopping the
replacement. After cleanup the environment is restored, then the canonical
receipt bytes are rehashed and must equal the pre-run digest. Isolated state is
never promoted.

Do not set `REDDOG_HOLOINDEX_AUTHORITY_REPO_ROOT` for acceptance activation.
The supported command semantics are equivalent to the following only after the
private owner has been cleaned and while `HOLOINDEX_SSD_PATH` names the isolated
store:

```powershell
Remove-Item Env:REDDOG_HOLOINDEX_AUTHORITY_REPO_ROOT -ErrorAction SilentlyContinue
'{"query":"trusted-host isolated Holo candidate acceptance linked worktree dedicated store receipt model digest port ownership maintenance session","limit":1}' |
  python <candidate-root>\scripts\reddog_holoindex_owner_query_once.py
```

A detached same-SHA checkout fails truthfully when the receipt is bound to the
candidate path; it is not interchangeable authority. The adapter performs this
activation internally and stores only its receipt digest/count.

ChromaDB 1.5.5 currently inserts one `acquire_write` lifecycle row whenever a
`PersistentClient` opens, including supported logical read-only queries and
snapshot probes. The SQLite file can therefore change while canonical receipt,
generation, collection contents/counts, and embedding bindings remain stable.
This is known unbounded scale debt with no present cap; it is not semantic
mutation, not a correctness failure, and not resolved by this acceptance slice.
Do not substitute a bytewise-store-equality claim for the required semantic
rehydration and collection proof.

On Windows, the bounded copy is proven through live file and directory handles,
ported from the repository's existing authority-runtime-store Windows helper.
Handles use read-only sharing to exclude replacement; each resolved handle path,
identity, size, type, and parent chain is re-proved. Copy and artifact hashing
both use the held descriptors, avoiding a second path open. Newly owned files
and directories are cleaned through their proven handles. Source growth beyond
the per-file or aggregate limit and source/destination parent or root replacement
stop before unsafe continuation. POSIX retains descriptor/identity rechecks and
exclusive writer-window assumptions; neither platform claims hostile-kernel
containment.

The final JSON receipt is deterministic, bounded, secret-free, atomically
published, and immutable. Unsafe targets receive no file. A replace/fsync
failure cannot leave or report PASS. Operational failures retain a FAIL receipt
only when that receipt target independently passes the same path guards.

RED/GREEN provenance is cumulative. R1 captured 15 missing-guard, six
missing-orchestrator, three missing-CLI, one missing atomic-cleanup, and two
finalization failures before production. R2 Layer C added four failing contracts
for live per-file growth, live aggregate growth, Windows source-parent/root swap,
and Windows destination-parent/root swap; the integrated run then exposed a
path-reopen `MODEL_DIGEST_MISMATCH`, corrected by descriptor hashing. Its WSP 62
review also forced the 669-line copy module and 60/58/57-line functions into
cohesive bounded files/functions without weakening a contract. R2 Layer D added
three failing contracts before correcting the default CLI import boundary, the
port-race stable error, and rejection of an operational response lacking a new
private handoff. R3 captured one masked-error RED, then nine runtime-root REDs
and five CLI REDs. Stable operational failures now win before handoff proof, and
the dependency runtime is distinct, clean, related, non-reparse, and locally
verified. The R3 focused code matrix passed **57/57** and CLI passed **6/6**.

One live attempt did run at `fb72cbd99bc9499545823fa1849fc4597b8d71ec`.
It failed: immutable receipt SHA-256
`f9b5e18ce62e63af3bbbf0e0f3d36def5614216fafadca8872703f519be43a78`
records `NEW_PRIVATE_OWNER_HANDOFF_MISSING`, zero direct queries, and unchanged
canonical receipt. Audit proved the primary refresh failure had been masked.
The failed store is retained and cannot be reused; retry needs a new store and
receipt. There is no current-contract live PASS, promotion, or capacity claim.
Any retained PASS for `b482fdaed4932a15b2b195c256761cfd1053f053` is historical
pre-R5 evidence only and does not satisfy the activation contract above.

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
10. Re-prove the same clean HEAD after receipt construction and once more at
    the final publication boundary, then atomically publish/reload the receipt
    and validate its repository/store identities and generation.
11. Construct and retain the verified replica route, then start the private
    owner with the exact SHA, repository-root digest, generation, receipt
    digest, and four replica fields supplied to one authenticated semantic
    startup exchange. This route construction is implemented by the activation
    controller and accepted at exact main as recorded in the roadmap. Retain
    the returned binding with the live process; do not launch a duplicate
    semantic canary merely to export the process-private handoff.

Refresh/index/proof failures preserve a non-current state. Child stdout is
drained into a bounded 16 KiB in-memory buffer, stderr is discarded, and no
capture file is created. For a nonzero exit, only an allowlisted stable error
code in the final JSON line may cross the parent boundary; optional detail is
validated but discarded. Malformed, forged, oversized, or free-text output
returns `HOLOINDEX_MAINTENANCE_REFRESH_FAILED`. On Windows, timeout makes a
bounded exact-PID `taskkill /T /F` attempt. If `taskkill` is missing, denied, or
times out, bounded direct-child kill/wait is the fallback; an escaped descendant
may retain stdout and the daemon reader until that descendant exits. POSIX signals
the exact isolated process group, but cannot contain a descendant that starts a
new session. Only the reader closes its pipe. This is cooperative trusted-host
best-effort containment, not a hostile-process or OS-privilege guarantee; never
assume the whole tree is gone. If refresh and receipt publication succeed but subsequent
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
| Independent one-shot finds its PID shard occupied | Treat listener as foreign; try one per-process distinct shard | Accept success only after private-token exact-binding health; pair collisions and terminal contention remain fail-closed |
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
