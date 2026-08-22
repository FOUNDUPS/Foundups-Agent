# foundups_mcp_bridge Roadmap

## 2026-08-21: Streamable HTTP `/mcp` and governed Holo bundle

**Implemented locally; live ChatGPT/tunnel acceptance pending.** The canonical
loopback server now uses Streamable HTTP `/mcp`; official-client readiness
proves initialize, initialized, exact tools/list, and a store-free lexical
`holo_query_bundle` call. The remote allowlist is pruned to that one bounded
tool and carries conservative read-only annotations. Linked-worktree launch
selects a capability-proven main MCP environment using file-only common-dir
evidence. Legacy SSE is removed; deprecated SSE launcher names are aliases to
the same HTTP runtime/lock. Startup now has one canonical capability-proven
subprocess lifecycle with direct PID ownership; the former import-dependent
in-process branch and its shutdown race are removed.

Remaining operational work: configure and verify the external Secure MCP
Tunnel/OAuth control plane from ChatGPT, record a live connection/call receipt,
and decide whether currently local-only executable-backed tools can be safely
rerouted before any future remote admission. Static bearer auth is not a
substitute for ChatGPT OAuth.

### Remote admission audit

| Former remote name | Decision | Transitive reason |
|---|---|---|
| `holo_query_bundle` | ADMIT | Exact schema, governed one-shot adapter, secret-free 256 KiB projection, no-index proof. |
| `get_repo_tree` | LOCAL ONLY | Prefix-string confinement, recursive/symlink traversal, and multiplicative output were not remotely safe. |
| `read_file` | LOCAL ONLY | Prefix-string confinement did not exclude sibling roots, `.git`, disallowed suffixes, or special/link targets. |
| `get_wsp_docs` | LOCAL ONLY | Enumeration and output have no exact remote caps or shared confinement/redaction gate. |
| `get_module_docs` | LOCAL ONLY | Recursive module discovery and document reads are unbounded and accept unconstrained names. |
| `get_interface_doc` | LOCAL ONLY | Same unbounded recursive discovery/read boundary as module docs. |
| `get_test_docs` | LOCAL ONLY | Same discovery boundary and potentially two unbounded document bodies. |
| `get_modlog` | LOCAL ONLY | Reads full logs before slicing sections; caller limit and output bytes are not exact-bounded. |
| `get_violations` | LOCAL ONLY | JSON/log input and nested result shapes lack exact byte/container bounds. |
| `get_mission_history` | LOCAL ONLY | SQLite opened in default read-write mode and JSONL input is unbounded. |
| `get_pattern_memory` | LOCAL ONLY | JSON files/containers are unbounded and loaded mappings are mutated for projection. |
| `get_overseer_status` | LOCAL ONLY | SQLite opened in default read-write mode; JSON sources lack a remote projection gate. |
| `get_coordination_state` | LOCAL ONLY | SQLite opened in default read-write mode and may create sidecars. |
| `get_known_failure_patterns` | LOCAL ONLY | JSON/JSONL reads and nested records lack strict input/output byte bounds. |
| `get_module_dependencies` | LOCAL ONLY | Recursive AST scan/read and response size are unbounded; depth is not an enforced work cap. |
| `get_reverse_dependencies` | LOCAL ONLY | Repository-wide recursive AST scan and response size are unbounded. |

Pruning is the WSP_97/Occam correction: these functions remain available only
to trusted in-process callers. No SQLite, repository walker, or arbitrary file
reader crosses `/mcp`. Future admission requires its own bounded confinement,
redaction, resource, and side-effect proof.

## 2026-08-20: Main Integration and ChatGPT MCP Boundary

The immutable query-replica/acceptance stack is integrated with main's
FastMCP read-only allowlist, fail-closed auth, lifecycle, and bounded
maintenance diagnostics. The complete bridge suite now finishes naturally in
two independent unchanged-cap runs: **899 passed / 7 skipped** in 200.66 and
314.42 seconds; the final tree with its permanent cache receipt is **900 passed
/ 7 skipped** in 215.31 seconds. Following the integration-candidate WSP_62
split, the repaired tree is **901 passed / 7 skipped / 10 warnings** in 220.32
seconds. The earlier legacy-suite timeout is therefore closed through
test-only immutable-input snapshots; no runtime cache or larger timeout was
introduced. A live tunnel, ChatGPT custom app session, Holo model/store,
maintenance transaction, and post-commit exact-SHA acceptance remain explicit
operational work; local synthetic GREEN is not a live-service receipt.

## 2026-08-17: Verified Query Replica Owner Routing Phase 2

**R24 acceptance-closure correction implemented and synthetically validated;
independent verification and live integration pending.** R16-R19 made route,
binding, and health-container admission exact. R20 rejects hostile or coerced
host/token/port/timeout scalars before connection. One exact
container guard now admits only a built-in JSON dict before the generic binding
parser admits exact built-in four-tuples and
exact, trimmed, printable built-in strings. Only expected canonical fields may
be explicit empty wildcards; actual canonical and replica fields are nonempty.
R21 closes the remaining exchange-order gap: canonical expectation is parsed
first, replica expectation second, and only then transport is validated or an
HTTP object constructed. Malformed replica values and both wrappers return the
stable secret-free mismatch with zero connection and zero hostile calls; only
the retained parsed exact tuple reaches response validation.
R22 rejects duplicate JSON member names at every nesting level rather than
using last-wins semantics, rejects NaN and infinities, and fails closed on
Unicode, syntax, primitive, bounded-size, or recursion errors. Valid unique
JSON retains the same request/read/close and readiness contract.
R23 contains the stdlib `HTTPException` family at request, getresponse, and
bounded read. Targeted HTTP/OSError close failures preserve the prior ready or
unavailable decision; unexpected and resource exceptions are not suppressed.
R24 migrates the slow loopback acceptance fixture to the mandatory full route
and extracts shutdown/context lifecycle into a cohesive internal base. The
public supervisor remains below the 200-line class limit; context entry still
requires a full route.
One canonical verifier binds the active descriptor, immutable generation
manifest, canonical repository and freshness receipt, dual leases, and private
storage identity. A retained
`QueryReplicaOwnerRoute` separates canonical freshness authority from the
replica-only semantic backend. Capability proof runs before spawn and again
before authenticated health; health/reuse require all four public replica
fields and binding drift forces replacement rather than hot swap. Explicit
argv carries both roots and the child receives no ambient `HOLOINDEX_SSD_PATH`.

The live 10,556-file replica exposed that repeating its complete 8.29 GB proof
inside the 15-second request deadline was impossible. The resident path now
keeps complete admission at route resolution and again inside the isolated
owner, then revalidates the unchanged descriptor/authority plus only the model
and sealed snapshot artifacts reachable by the in-memory backend. Measured
runtime proofs were 1.297 and 1.359 seconds versus 42.422 seconds for complete
admission; no timeout was enlarged and SQLite/HNSW remain unreachable.

**Completed plumbing:** one-shot owner query `_owner_attempt`, maintenance
`_start_owner`, and promotion `_run_locked_promotion` now resolve and propagate
the explicit current replica capability without fallback or mutation.

**Still missing:** live authorized current-generation materialization and owner acceptance; ChatGPT-app MCP proof;
active/rollback retention; governed orphan deletion; and scale evidence for
Chroma lifecycle growth and registry/closure hashing. This author slice used
synthetic stores only and is not promotion evidence. R24 author validation is
317 passed / 1 host skip for lifecycle, 411 passed / 4 host-capability skips
for the exact closure, 96 passed / 3 skips for ten-file verifier adjacency,
and 3/3 for focused cold/context/WSP62 acceptance.
Governed generation is 1,360 runtime files at `fdf3643a2cb8...befc3592129e`; registry
totals remain 1,527 tests / 265 quarantined.

## 2026-08-17: Immutable Query Replica Materializer Phase 1

**R15 no-delete correction implemented; independent re-verification pending.** The first
Phase-1 candidate failed independent verification because point lease probes
and a receipt context ended before active publication. R13 fixed that race,
but independent R14 review then proved its inspect-then-delete rollback could
delete same-inode/same-size mutated content. R15 review found a second Windows
FileDisposition cleanup path reachable on failed model copy. Those deletion
APIs are now removed; handles close while partial bytes remain for staging
quarantine or direct-caller disposition. One
generation can be copied from an exact freshness/generation binding into a
private disjoint capability using the accepted descriptor/Windows-handle copy
primitives. The candidate retains noncreating authority-update then maintenance leases
and the receipt descriptor across both publications and final validation,
uses sealed production dependencies, requires direct-root model markers and
exact normalized manifests, and performs no content deletion. Failed temps,
staging, and active names move no-replace into an owned orphan root; move
failure preserves the source name. Synthetic tests cover those boundaries. Holo
retrieval remained quarantined and no live store was accessed.

**Phase-2 follow-up:** descriptor validation, owner activation, and
generation-change restart are implemented in the later section above.
Still missing: retain active + rollback generations;
define retention and deletion under a separately proven ownership policy;
and run a separately authorized live synthetic-to-operational acceptance. The
current owner still points at its configured storage root. This candidate is
not promotion evidence.

## 2026-08-17: R11 Launch-Capability Continuity Correction

**Correction dynamically validated; independent promotion review pending.**
Independent R10 review proved that point-in-time path/identity revalidation
closed its descriptor before `subprocess.run`, leaving a replacement interval.
R11 opens a fresh verified capability at the runtime-bound runner boundary and
retains it through runner return or exception. Windows denies write/delete
replacement while launching the exact case-proved path; Linux launches the
retained object through `/proc/self/fd/<fd>` plus `pass_fds`. The exact nine-file
closure collected 146 tests: 143 passed and three explicit symlink-capability
tests skipped. An actual child-launch smoke also passed. The 184-second broad
bridge timeout remains unresolved scale evidence and was not rerun. HoloIndex
remained quarantined; no live Holo, owner, maintenance, reindex, MCP, model,
canonical-store, commit, push, or promotion effect ran.

## 2026-08-17: R10 Windows Exact-Case Executable Correction

**Superseded after independent review found a pre-launch replacement gap.**
R9 file-identity/final-path admission still accepted a case-only parent or
leaf alias because all path comparisons used `normcase`. R10 used a live
descriptor only during point validation, then required its case-preserving final
path to match every non-anchor component. The exact nine-file acceptance closure
collected 141 tests: 138 passed and three filesystem-capability symlink tests
skipped. No live acceptance, owner, maintenance, reindex, MCP, model, or
canonical-store operation ran. `INTERFACE.md` is 999 lines after deduplicating
owner/bootstrap guidance. R9 is not promotion evidence by itself.

## 2026-08-17: R9 Process-Image Authority Closure

**Superseded by R10/R11; no R9 live acceptance run.** R8 independent review
proved mutable interpreter selection and inherited interactive mode remained
open. R9 binds the OS process image and descriptor identity through runtime
admission and point-in-time pre-spawn revalidation, while the shared sanitizer
drops `PYTHONINSPECT`. Semantic/generation/freshness/single-attempt contracts
remain unchanged. ChromaDB lifecycle-row scale debt remains open.

## 2026-08-17: R8 Trusted Snapshot Runtime Closure

**Implementation complete; no R8 live acceptance run.** The final isolated
snapshot now consumes the already-proven dependency runtime instead of ambient
user-site packages, validates ChromaDB 1.5.5 origin/version before store open,
and preserves typed generation-bound failures with no retry. The retained R7
FAIL remains evidence, not a retry target or live-PASS claim. ChromaDB
`acquire_write` lifecycle-row growth remains unresolved P0 scale debt; no
semantic, freshness, or generation contract was weakened.

## 2026-08-17: R6 Receipt Continuity Closure

**Implementation complete; no R6 live acceptance run.** The acceptance receipt
now proves a retained one-way private-owner session identity, while the
post-activation freshness receipt is confined, descriptor-held, strictly
parsed, and identity/digest-bound across the semantic snapshot probe. The
ChromaDB `acquire_write` lifecycle-row scale debt remains open without any
weakened semantic or generation proof.

## 2026-08-17: R5 Supported-Wrapper Activation Hardening

**Implementation complete; live activation not run in this code slice.** The
one-shot wrapper now rejects a freshness/root mismatch before owner startup or
retry. Candidate acceptance keeps exactly two direct queries, cleans the
private owner, then requires one candidate-self-selected supported-wrapper
query plus unchanged generation/root/receipt and collection snapshots.

The `b482fdaed4932a15b2b195c256761cfd1053f053` PASS is historical pre-R5
evidence only and cannot satisfy the new contract. Detached same-SHA authority
is not interchangeable with the receipt-bound candidate root. ChromaDB 1.5.5
adds an `acquire_write` lifecycle row on every `PersistentClient` open even in
logical read-only operation. Semantic correctness is re-proved, but the
unbounded metadata-row growth has no throughput/storage cap and remains P0
scale debt. A future bounded slice must measure, compact, or replace this
lifecycle behavior without weakening generation and collection proofs.

## 2026-08-17: Isolated Exact-SHA Candidate Acceptance

**Implementation and R3 hardening complete; one real attempt failed and no live
acceptance exists.** The immutable receipt for
`fb72cbd99bc9499545823fa1849fc4597b8d71ec` is FAIL with
`NEW_PRIVATE_OWNER_HANDOFF_MISSING`, zero queries, unchanged canonical receipt,
and SHA-256 `f9b5e18ce62e63af3bbbf0e0f3d36def5614216fafadca8872703f519be43a78`.
R3 proved that a primary `HOLOINDEX_MAINTENANCE_REFRESH_FAILED` result was masked
and that the source worktrees had no verified runtime dependencies. Stable
operational errors now precede missing-handoff validation; an explicit clean,
related, dependency-only runtime checkout supplies exactly one verified local
site-packages path. The default CLI remains import-inert until valid `--real`.
The failed store remains immutable evidence and cannot be retried or promoted.
Remaining operational work is a separately authorized post-commit `--real` run
using clean exact-SHA candidate/authority worktrees, the verified runtime root,
and entirely new store and receipt targets. No live PASS or capacity claim exists.

## 2026-08-16: K-Invariant Tier-0 Owner Diagnostics

**Complete:** removed hit-conditioned owner reordering. Flattening now reserves
only when canonical nullable `tier0_module_target`, query relation, and one
complete exact pair agree. Missing, unrelated, ambiguous, multi-module,
partial, mixed, duplicate, and forged claims preserve scoring. Three stable
producer failures retain distinct HTTP/retry semantics without exposing text.

**R3 correction:** the upstream HEAD catalog now rejects Unicode
control/format/surrogate records and canonically equivalent duplicate paths.
The exact six-file focused command includes the machine-spec contract and
passes 278 tests; the adjacent owner matrix passes 356 with one optional skip.
R4 removed duplicated operational detail from the public interface and linked
its existing README/runbook owners, reducing `INTERFACE.md` from 1,010 to 971
lines without changing endpoint, error, Tier-0, or security semantics.

**Deferred:** live exact-SHA owner validation, maintenance, and receipt
publication. The uncommitted candidate cannot truthfully validate against the
03c generation and does not restart/reindex the resident owner.

## 2026-08-16: Explicit-Module Tier-0 Owner Projection

**Complete:** global owner flattening now reserves at most two existing exact
root README/INTERFACE hits for explicit uniquely evidenced module queries,
after generation-bound Holo retrieval and path projection. Low-K,
ambiguous-query, and adversarial lookup behavior is pinned by focused tests.

**Deferred:** post-commit exact-SHA maintenance/publication and live governed
owner acceptance. The resident owner is not restarted by this change.

## Current P0: HoloIndex / RedDog Operational Truth Boundary POC

**Priority:** 20 / P0 under WSP_15
**Phase:** Implementation present; focused validation/PR evidence pending
**Owner:** 0102 architect for 012

The Phase-1 target is one query/health-only HoloIndex owner, one trusted-host
maintenance handshake, process-private bearer handoff, exact clean-HEAD and generation
binding, semantic-only health, and complete canonical proof for all seven
baseline collections.

Acceptance will require the focused HoloIndex, owner lifecycle, HTTP, RedDog
boundary, startup-dispatch, and operational-consumer matrices plus static
contract checks. The persistent store is not current for the merge SHA until
the post-merge activation run completes.

## Post-Merge Activation

1. Use a clean main checkout at the merge SHA.
2. Run the trusted full-maintenance handshake against the canonical store.
3. Require seven complete canonical source-scope proofs at the exact SHA.
4. Start the private owner and require an authenticated semantic canary bound
   to the receipt generation.
5. Run one activation-style RedDog query and retain only secret-free receipt
   identifiers and result metadata.
6. Stop the owned process and confirm no maintenance lease or invalidation is
   left behind.

## Next Operational Slices

- Bind the resident RedDog/WRE control loop to the owner handoff without
  granting query workers index-write authority.
- Add durable maintenance-request receipts and retry/backoff policy owned by
  WRE, not by the query process.
- Add post-merge scheduled refresh and generation-health monitoring.
- Migrate or explicitly retire the legacy `src/holo_tools.py` direct-store
  HoloIndex consumer.
- Replace the cooperative-writer/exclusive-window POC assumption with an
  immutable exact-commit source snapshot, and add orphan-process reclamation
  for abrupt host death.
- Add semantic recall/capacity gates for representative FoundUp creation,
  repair, and enhancement tasks.
- Prove governed build-to-test-to-draft-PR recursion in isolated worktrees
  before considering unattended merge authority.

## WSP_62 Remediation Register

The exact post-repair HEAD differential has zero errors and this non-zero
accepted bridge set only:

- WARNING: `INTERFACE.md` 1,054 lines.
- WARNING: append-only `ModLog.md` 1,277 lines.
- WARNING: `src/holo_tools.py` 1,094 lines. Its candidate-grown `holo_search`
  is now a 41-line orchestrator with cohesive helpers, so the function error is
  closed while the file-level warning remains visible.
- WARNING: `tests/test_mcp_bridge.py` 1,313 lines. Cache scaffolding is already
  extracted, but the file remains a warning below its applied 1,425-line
  candidate ceiling.
- WATCH: append-only `tests/TestModLog.md` 917 lines.
- WATCH: `tests/test_holo_query_service_edges.py` 787 lines.

No other bridge path is part of the accepted warning/watch set. Owner bootstrap
and candidate acceptance remain decomposed below their applicable thresholds.

No global WSP_62 compliance claim is made until those historical items are
completed and the repository-wide FMAS size gate is green. The RedDog npm
release tier is extension-scoped and does not satisfy this gate.
