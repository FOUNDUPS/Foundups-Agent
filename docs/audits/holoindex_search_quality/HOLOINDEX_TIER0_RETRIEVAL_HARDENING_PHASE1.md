# HoloIndex Tier-0 Retrieval Hardening -- Phase 1

**Slice**: `HOLOINDEX_TIER0_RETRIEVAL_HARDENING_PHASE1`
**Self / role / origin**: `0102` / implementation worker / internal handoff
**Base commit**: `8649321ad18f8386d3192f5b32120826ca8caeff`
**Mode**: Search-time retrieval hardening; no reindex, service start, dependency,
or persistence mutation
**WSP lock**: WSP 00, CORE, 5, 6, 15, 22, 34, 50, 60, 76, 77, 84, 87,
97, 108

## R7 Governed Retrieval and Assumption Correction

The R7 owner query was admissible (`ok=true`, `CURRENT`, no index gap) at exact
HEAD, but its 39-52% results were adjacent WRE/Git/WSP artifacts and omitted the
staged governed projection and Fusion WSP_62 contract. Exact staged source and
Tier-0 docs therefore remained candidate authority. Two assumptions were
falsified before repair: distinct Git spellings implied distinct Windows files,
and the staged extension still fit its hard line ceiling. Real NTFS and direct
focused-contract reproductions disproved both. No query-time reindex or
authority-worktree mutation was performed.

## R6 Governed Git Assumption Correction

The current owner query was admissible (`ok=true`, `CURRENT`, no index gap) but
did not retrieve the exact staged RedDog Git modules; its 49.1-50.4% top hits
were adjacent WRE/moltbot controls and one stale renamed path. Exact staged
source therefore remained the candidate authority. Two assumptions were
falsified before repair: factory instances shared mutable projection policy,
and the final Git receipt preceded a third protected content capture. R6 binds
policy per frozen API and makes the forced Git receipt the absolute last
protected read. These are author observations pending independent verification.

## Assumption Audit: Module Tier-0 Owner Retrieval

### 1. Problem Statement

- **What**: The generation-bound RedDog HoloIndex owner omits a clearly
  targeted module's root `README.md` and `INTERFACE.md` from its bounded
  top-level hits, including when those filenames are explicit in the query.
- **Why**: WSP_CORE makes those two artifacts mandatory Tier-0 retrieval. A
  worker cannot truthfully claim the required start-of-work grounding when the
  supported owner path returns only symbols and tests.
- **Who**: Authorized by 012 through the root 0102 architect handoff for
  `HOLOINDEX_TIER0_RETRIEVAL_HARDENING_PHASE1`.

### 2. Governed Reproduction and Retrieval Evaluation

Both owner queries were run through
`scripts/reddog_holoindex_owner_query_once.py` at the exact base commit. Both
reported `ok=true`, `freshness=CURRENT`, `index_gap_detected=false`, the same
generation `sha256:615070413cec265682576fec83918d2198bc887e5fe6e6a313d1fc28c287ffac`,
and no query-time reindex or authority-worktree mutation.

| Query | Latency | Top-level result | Tier-0 result |
|---|---:|---|---|
| `RedDog moltbot_bridge worker supervisor Hermes verifier HoloIndex retrieval hardening` | 1281 ms | Six source symbols followed by tests | Missing README and INTERFACE |
| `moltbot_bridge README INTERFACE ROADMAP ModLog tests README requirements RedDog architecture` | 1297 ms | Tests and symbols only | Missing README and INTERFACE |
| `modules/communication/moltbot_bridge README.md INTERFACE.md module contract` | 1265 ms | Nine source symbols and one test | Missing README and INTERFACE |

Start-of-work retrieval evaluation:

- **Noise**: unrelated generic ModLogs/WSPs occur in typed buckets while the
  target module's root contracts are absent.
- **Ordering**: `flatten_hits()` globally orders by raw similarity; symbol and
  test similarity dominates document type and Tier-0 intent.
- **Missing artifacts**: both mandatory Tier-0 files are missing from all three
  bounded top-level owner results. The second query surfaces only
  `modules/communication/moltbot_bridge/tests/README.md` within its docs bucket.
- **Staleness risk**: low for this reproduction because the owner proved a
  CURRENT exact-HEAD generation with no gap. This is a ranking/candidate gap,
  not a stale-generation claim.
- **Duplication**: the Tier-0 contract already exists in
  `holo_index/cli/commands/bundle_json.py::_artifact_snapshot`; owner semantic
  retrieval does not consume that module-context rule.

### 3. Root Cause

1. `holo_index/core/search_engine.py::_search_collection` executes
   `collection.query(..., n_results=limit)` before keyword/path re-ranking.
   A target module's root contracts that fall outside the initial vector K can
   never be recovered by later ranking.
2. `modules/infrastructure/foundups_mcp_bridge/src/holo_query_service_response.py::flatten_hits`
   globally sorts surviving typed hits by raw similarity and applies the
   caller K again. It has no Tier-0 module-context reservation.
3. Bundle `--bundle-module-hint` has the correct Tier-0 inventory but is a
   separate explicit-hint surface; the RedDog owner request intentionally
   exposes only `query`, `limit`, `doc_type_filter`, and exact-SHA proof.

### 4. Assumptions

| ID | Assumption | Evidence | Confidence |
|---|---|---|---|
| A1 | A basename target is safe only when exact-boundary intent resolves uniquely against initial hit metadata; one validated full module path can resolve directly and takes precedence. | Adversarial tests cover `bridge`/`bridgework`, duplicate basenames, prefixed paths, full-path precedence, invalid components, and bounded input. | HIGH |
| A2 | Zero-to-two exact metadata gets for missing Tier-0 rows are safer and more scalable than increasing vector K or scanning the docs collection. | Chroma metadata is repository-relative; existing semantic rows are deduplicated and the bundle contract names exactly two required files. | HIGH |
| A3 | Injected candidates must come from the existing generation-bound `navigation_docs` collection, not mutable filesystem reads. | Owner receipts bind canonical semantic evidence to the current generation; filesystem-only projection would weaken source labeling. | HIGH |
| A4 | Reserving at most two top-level slots preserves code/test breadth at normal K while satisfying Tier-0 grounding. | At K=10, eight score-ranked non-Tier-0 slots remain; negative and low-K tests will pin bounded behavior. | HIGH |
| A5 | Queries without an explicit, uniquely resolved module must retain current global-score ordering. | Prevents generic research queries from receiving unrelated module docs inferred only from noisy hits. | HIGH |

### 5. Failure Modes

| ID | Failure Mode | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| F1 | A common word is mistaken for a module and unrelated contracts are promoted. | MED | HIGH | Require an exact normalized module basename/full path in the query plus one unique module path evidenced by returned hits. |
| F2 | A mutable checkout file is presented as generation-bound semantic evidence. | LOW | CRITICAL | Retrieve Tier-0 records only from the already admitted docs collection; do not read or synthesize owner hits from the filesystem. |
| F3 | Tier-0 reservation crowds out all implementation/test evidence at small K. | MED | HIGH | Cap reservations at `min(2, limit)` and preserve deterministic global score order for remaining slots; test K=1, K=2, and K=10. |
| F4 | Exact lookup becomes an unbounded docs scan. | LOW | HIGH | Use zero-to-two exact metadata-filtered gets only; no collection-wide `get()` and no increased vector K. |
| F5 | Missing/duplicate indexed Tier-0 rows corrupt aliases or response counts. | MED | HIGH | Deduplicate by normalized path, retain canonical response validation, and recompute bucket counts through the existing search payload. |
| F6 | Owner CURRENT/freshness or no-mutation truth changes. | LOW | CRITICAL | Leave admission, pre/post generation proof, receipt construction, and maintenance authority untouched; rerun owner and adjacent truth-boundary suites. |
| F7 | A `tests/README.md` is promoted as module Tier-0 README. | MED | HIGH | Match exact module-root paths only: `<module>/README.md` and `<module>/INTERFACE.md`. |

### 6. Alternatives Considered

| Alternative | Why Rejected |
|---|---|
| Raise every per-bucket `limit` or inflate owner K | The explicit path query still missed both contracts at K=10; broad over-fetch multiplies collection work and does not guarantee global top-K inclusion. |
| Add a `moltbot_bridge`/RedDog query special case | Vibecoding/overfit; it would not generalize to other modules and violates WSP 84. |
| Inject root docs directly from the authority checkout | Path existence would be current Git evidence but not semantic-generation evidence; top-level source labeling and receipt semantics would become ambiguous. |
| Add a second full semantic query for documentation | Doubles encoder/collection query work, increases latency, and still depends on vector recall. |
| Promote every README/INTERFACE hit globally | Creates noise for queries with no explicit module and can suppress relevant code/tests. |
| **Chosen: bounded module-intent Tier-0 candidate retrieval plus two-slot reservation** | Reuses the existing Tier-0 contract, remains generic and deterministic, reads only the admitted docs collection, and has constant extra work. |

### 7. WSP 15 Priority Receipt

| Dimension | Score | Reason |
|---|---:|---|
| Complexity | 5 | Retrieval/ranking, owner flattening, immutable-HEAD ownership, governed Git storage/config controls, and authenticated release closure cross security-sensitive seams. |
| Importance | 5 | Tier-0 contracts are mandatory pre-work grounding. |
| Deferability | 5 | Current RedDog audits can silently proceed without the mandatory module contracts. |
| Impact | 5 | The owner path is the supported retrieval boundary for RedDog workers. |
| **MPS total** | **20 / P0** | Execute before further RedDog implementation slices that rely on owner grounding. |

### 8. Decision Record

- **Decision**: PROCEED
- **Owner**: 0102 implementation worker
- **Timestamp**: 2026-08-15T21:19:31Z
- **Truth boundary**: Search-time candidate/ranking hardening only. No reindex,
  Chroma mutation API, dependency, service topology, request schema,
  authentication, freshness, or promotion-authority change.

### 9. Acceptance / Falsification Gates

1. Focused tests must fail on the base behavior and pass only when:
   generic explicit module intent retrieves exact module-root Tier-0 docs;
   ambiguous/no-module queries retain existing ordering; `tests/README.md`
   never substitutes; reservations are bounded/deterministic.
2. Existing T1 ranking and owner response/semantic proof tests must remain
   green.
3. Both original governed owner queries must return CURRENT/no-gap and include
   `modules/communication/moltbot_bridge/README.md` plus
   `modules/communication/moltbot_bridge/INTERFACE.md` in bounded top-level
   hits while retaining implementation/test evidence.
4. Git diff must show no indexing, receipt, admission, maintenance, dependency,
   WSP framework, or service-topology mutation.

### 10. WSP 50/97 Learning Event

During pre-implementation verification, a disposable Chroma
`EphemeralClient` exact-filter probe omitted supplied embeddings. Chroma
therefore downloaded a 79.3 MB ONNX model into the user cache. The probe
confirmed exact `where={"path": ...}` behavior and changed no repository,
persistent HoloIndex store, resident service, or project dependency state, but
the cache download was unnecessary. It was not deleted because deletion was
not authorized. All implementation tests after that event use deterministic
fake collections and supplied fake embeddings, with no model, network, store,
or filesystem mutation.

The original candidate used neutral distance `1.5`, which rendered as a false
`40.0%` vector similarity and was then removed by a `0.5` vector floor. That
design was rejected. Exact metadata rows now carry schema-bound
`retrieval_provenance: exact_metadata` with `similarity: null`, bypass the
vector floor, and are ordered only by the explicit Tier-0 contract.

## Annex A: Governed Git `safe.directory` Reconciliation

### A.1 Observed finding and boundary

The exhaustive RedDog contract reproduced
`[git context unavailable: Git configuration unreadable]` on the canonical
checkout. RedDog correctly erased inherited/global Git configuration, but the
host's ownership mismatch had previously been admitted only by a global
`safe.directory`. The sanitized subprocess therefore could not read local Git
configuration, repository discovery fell back to a physical walk, and the
20,000-entry cap reported a truncated audit manifest.

The candidate supplies `-c safe.directory=<canonicalRoot>` as one argument
only when the no-override ownership probe fails and the exact-root probe
succeeds. Owned repositories execute content commands without an undisclosed
override. The immutable-HEAD Python reader uses the same exact command-scoped
admission after its fixed trusted-Git/root boundary. Neither path writes config
or uses `*`.
The readiness receipt records whether an ownership mismatch was observed and
whether the command-scoped override was applied. This is a new
security-sensitive behavior; it is **NEEDS_VERIFICATION** until an independent
verifier accepts the final candidate and is not claimed as non-downgrading.

### A.2 Assumptions and evidence

| ID | Assumption | Mechanical evidence | Status |
|---|---|---|---|
| G1 | Only one canonical directory can enter the override. | Input must be an absolute bounded string without controls or `..`; `path.resolve`, `realpath`, `lstat` directory/non-symlink checks, and exact canonical equality run before Git. | OBSERVED |
| G2 | Git metadata is confined before trust override. | `registeredGitMetadata()` retains exact `.git`/linked-worktree topology, regular-file, realpath, hardlink, object/ref traversal, and entry-cap checks. | OBSERVED |
| G3 | A path cannot inject Git options. | `safe.directory=` plus the canonical root is one `execFileSync` argv element after `-c`; shell parsing is absent. Control-bearing paths reject before construction. | OBSERVED |
| G4 | The override has no durable/wildcard scope. | Tests require `safe_directory_scope` in `{none, command}`, `config_write_performed=false`, and `safe_directory_wildcard=false`; source rejects canonical `*` and contains no `safe.directory=*`. | OBSERVED |
| G5 | Ownership mismatch remains visible. | The sanitized no-override local-config probe runs first. If only the exact-root probe succeeds, readiness records `ownership_mismatch_observed=true`, `safe_directory_override_applied=true`, and reason `ownership_override_required`. | OBSERVED |

### A.3 Failure modes and mitigations

| Failure mode | Impact | Mitigation / falsifier |
|---|---|---|
| Traversal, newline, NUL, symlink, junction, or non-directory root reaches Git. | Arbitrary repository trust. | Reject before Git; adversarial traversal/control/symlink-reparse contracts require stable unavailable evidence. |
| `safe.directory=*` or a config write broadens trust. | Global trust downgrade. | No wildcard literal, one per-command `-c` argument, sanitized environment, and no config mutation API. |
| Ownership probe fails for a reason other than mismatch. | False readiness. | Exact-root probe must then succeed; if both fail, readiness is `ownership_unproven` and Git context stays unavailable. |
| Local/worktree config contains includes, filters, external attributes, worktree redirects, partial-clone, or diff commands. | Code execution or evidence substitution. | Existing risky-setting enumeration runs with `--no-includes` after ownership proof and remains fail closed. Existing hostile config suite is retained. |
| Readiness cache hides a later hostile config mutation. | Stale admission. | Ownership posture alone is observed; risky local/worktree configuration and Git storage are revalidated on every governed operation. |

### A.4 Alternatives considered

| Alternative | Decision |
|---|---|
| Keep inherited global config to obtain `safe.directory`. | Rejected: would re-admit unrelated includes, filters, and global behavior. |
| Use `safe.directory=*`. | Rejected: broad trust expansion. |
| Persist `git config --add safe.directory`. | Rejected: external durable mutation and global scope. |
| Continue physical-walk fallback. | Rejected for accepted repository audits: it included untracked dependency trees, hit the cap, and truthfully blocked completeness. |
| Exact canonical per-command override plus explicit readiness evidence. | Candidate: narrowest usable mechanism; awaits independent verification. |

## Annex B: R2 WSP_97 Falsification and Scale Reconciliation

The fresh verifier returned REVISE. R2 reproduced every objection before
repair: cached loose-object hardlinks remained admitted; duplicate initial
Tier-0 vector rows bypassed exact validation; non-strict lookup exceptions did
not warn; `limit=0` returned one flattened hit; full explicit paths retained
query casing; `search_engine.py` and `_search_collection` exceeded their exact
WSP_62 exemptions; governed Git omitted graft/shallow/info/config controls and
reported no override while content commands always supplied one; and the
repository-audit extension contract failed because Python immutable-HEAD Git
commands did not carry the exact ownership admission.

The R2 candidate replaces strict vector Tier-0 rows with exactly one exact
metadata README and INTERFACE, extracts bounded collection injection logic,
and closes the zero-limit/case/warning contracts. Governed Git storage now
binds every object/ref file's identity, timestamps, size, and link count plus
HEAD/index/packed-refs/config/config.worktree/shallow/info attributes/exclude.
Grafts, alternates, and cross-common metadata remain denied. Content commands
pin hooks, attributes, excludes, external diff, replacement objects, lazy
fetch, optional locks, stat policy, worktree, and configuration includes.

The fingerprint is metadata-only; it never hashes object contents. A real
checkout with 6,707 object-tree entries measured 2,101 ms for first full
validation and 368/369 ms for warm fingerprints. A synthetic 5,000-loose-
object fixture measured 3,300 ms first and 590/567 ms warm. Per-file stat is
necessary to observe an external hardlink because creating that link does not
change the Git object's parent-directory mtime. Production now obtains status,
stat, and diff from one validated session/change enumeration; on the dirty
checkout this measured 3,033 ms first and 1,385/1,286 ms warm instead of three
repeated validation/enumeration passes. The 20,000-entry ceiling remains an
explicit fail-closed scale bound. These are author measurements, not
independent acceptance.

### 11. Candidate Validation Status

- Post-reconciliation WSP_62 validation covers the 274-line context,
  147-line readiness, and 162-line storage modules; every scanned function is
  at most 30 lines. `search_engine.py` is exactly 1,500 lines and
  `_search_collection` is within its exact 225-line exemption. This is author
  evidence, not independent approval.
- The R2 final 18-shard exhaustive extension contract passed with 6,944 source
  lines and 1,229 assertion calls in 370.4 seconds, including repair-evidence
  and judgment-verifier bridge end-to-end checks. That cost is viable as a
  serialized release/CI tier, not as a per-query or "fast" gate; focused and
  closure-wide validation should be exposed as separate cached CI tiers.
- `extensions/reddog/package.json` still has no `scripts` object. This is not a
  runtime or VSIX requirement because the checked-in test README supplies the
  direct commands, but it leaves the documented tiers undiscoverable through
  `npm test`/`npm run`. Adding thin wrappers is a separate operationalization
  change and was not folded into this security/retrieval reconciliation.
- The source package version is 0.4.101 with VS Code engine `^1.74.0`; no VSIX
  artifact was built or published by this slice. `vsce ls --tree` confirmed
  both governed Git helpers and the new hardening test are package-included.
- Focused Tier-0/machine-contract suite: **82 passed**; combined Tier-0,
  producer schema, and owner service-edge suite: **141 passed**.
- Expanded Holo ranking/bundle/audit/extension/machine-contract closure:
  **190 passed, 4 skipped**. Owner service/lifecycle closure: **165 passed,
  1 skipped**. Adjacent RedDog/OpenClaw closure: **82 passed**.
- Strict mode fails closed for incomplete pairs, collection exceptions,
  malformed cardinality, and returned-path mismatch. Non-strict mode preserves
  existing results and emits an incomplete-Tier0 warning.
- Invalid traversal, hidden, whitespace, control-bearing, and terminal-dot
  module components are rejected before exact lookup.
- Live governed acceptance remains **BLOCKED UNTIL COMMIT/PUBLICATION**. The
  currently resident/canonical owner is generation-bound to base commit
  `8649321ad18f8386d3192f5b32120826ca8caeff` and therefore does not load this
  uncommitted candidate. This slice does not restart the resident service,
  commit, reindex, or publish a generation; pre-existing owner results must
  not be represented as post-fix evidence.
- A final governed lifecycle check ran the exact explicit-path query in
  1406 ms and returned `ok=true`, `freshness=CURRENT`,
  `index_gap_detected=false`, no mutation/reindex, authority SHA
  `8649321ad18f8386d3192f5b32120826ca8caeff`, and generation
  `sha256:615070413cec265682576fec83918d2198bc887e5fe6e6a313d1fc28c287ffac`.
  It still omitted README/INTERFACE, exactly as expected from the committed
  base owner. This is lifecycle/base evidence and explicitly **not** candidate
  acceptance evidence.

## Annex C: R3 Authenticated Manifest-Closure Correction

The R2 author handoff missed a release-blocking closure defect. The tracked
`holo_index/core/search_engine.py` imported
`holo_index/core/collection_injections.py`, but the extracted dependency was
untracked. Because the canonical generator intentionally resolves only Git-
tracked local modules, the working-tree suite could pass while the generated
manifest omitted the file. Before correction,
`git ls-files --error-unmatch holo_index/core/collection_injections.py`
failed and the manifest contained no `collection_injections` entry.

This remains a WSP_15 **20/P0** correction: Complexity 5, Importance 5,
Deferability 5, Impact 5. The smallest non-downgrading move was to stage only
the imported runtime module, refresh the already-staged Tier-0 helper so its
index blob includes the R2 case-folding fix, and run the canonical generator.
The extraction was not removed and the generator was not weakened to trust
untracked files.

The regenerated closure contains 1,335 runtime files. It binds
`holo_index/core/collection_injections.py` to normalized SHA-256
`9dca36d9c2823cfa1fec316422d5b7434d4b4263a3192550365aa73b042d1383`
and has canonical manifest digest
`4e173152775ebff0d58dd421b9de14446d0c6f05ad509c12c30afe3be7cde796`.
A focused generator regression now proves the relative import is parsed, the
dependency is Git-tracked and resolves locally, the runtime closure contains
it, and its manifest digest matches current content. This is author evidence;
the candidate remains **NEEDS_VERIFICATION**.

R3 author validation:

- Generator regression: **4 passed**.
- Canonical manifest `--check`: PASS, digest
  `4e173152775ebff0d58dd421b9de14446d0c6f05ad509c12c30afe3be7cde796`,
  `runtime_files=1335`.
- Focused Tier-0/MCP edge suite: **86 passed** with two expected warnings from
  plugin-disabled pytest configuration.
- Backend compatibility/preflight: PASS, including the independent manifest,
  runtime-integrity, async, work-state, model-binding, and health contracts.
- Exact WSP_62: `search_engine.py=1500`, `_search_collection=205` under its
  225-line exemption; `collection_injections.py=98` with largest Python
  function 45 lines; `tier0_retrieval.py=123` with largest function 21 lines.
- `git diff --check`, staged diff check, Python/JavaScript syntax checks: PASS.

The 370-second exhaustive shard runner was not repeated. No shard, shard
manifest, reconstructed `extension.js`, or exhaustive assertion changed in
R3, and a source search found no exhaustive reference to the backend manifest
generator or the new dependency. The changed authenticated surface ran its
own stronger gates: canonical generation/check, generator regression, backend
preflight, and focused Python behavior. Re-running unrelated shards would add
cost without covering this edge. An initial local WSP_62 probe incorrectly
applied the JavaScript 30-line function limit to a Python helper and failed at
45 lines; the protocol's actual Python limit is 50, and the corrected exact
probe passed. No product change was made for that probe error.

## Annex D: R4 TOCTOU, WSP 62, and Promotion-Closure Correction

Fresh verification found three release blockers and each was reproduced before
repair:

1. Hardlinking `.git/HEAD` after validation and before the first content
   `ls-files` changed `nlink` to two, but the candidate still released all
   status/stat/diff projections.
2. `search_engine.py` grew from HEAD 1,465 lines to exactly 1,500 and the new
   test self-authorized a 205-line `_search_collection` with `<=1500` and
   `<=225` assertions.
3. Only two candidate files were staged while 48 tracked modifications and six
   untracked candidate paths remained outside the promotion snapshot.

R4 binds each governed snapshot to matching start and forced-uncached final
storage receipts. Projection is computed before the final gate; after that
gate, only receipt comparison and return of the already-rendered object occur.
Before-first HEAD hardlink, between-command config hardlink, and
immediately-before-final `info/exclude` mutation fixtures now make the entire
snapshot unavailable with a truthful reason.

The storage receipt is one invariant-validating fingerprint traversal with a
fixed 20,000-entry cap. Measurements after eliminating a redundant traversal:

| Fixture | Cold | Warm | Forced final | Directory scans per receipt |
|---|---:|---:|---:|---:|
| Current repository | 505 ms | 464 ms | 483 ms | 378 |
| 5,000 synthetic Git entries | 650 ms | 633 ms | 643 ms | 56 |

Cost is O(N) in Git storage entries and bounded by the cap. A released snapshot
intentionally pays two receipts, because omitting the final fresh receipt
reopens the reproduced race. This is viable for bounded local repositories but
is not constant-time; very large loose-object stores should be packed before
they approach the cap.

The first clean exhaustive rerun exceeded its 420-second release ceiling.
WSP_97 isolation showed shard 16 was the dominant increment and that each
FoundUp authority context issued four independent `gitOutput` calls. Because
each command correctly paid an initial and forced-final metadata receipt, one
context repeated the O(N) traversal eight times. Direct measurements were
5.07-5.30 seconds per target extraction with no warm improvement.

R4 therefore adds a bounded multi-command read, not a receipt cache. The four
commands execute after one start receipt and before one forced-uncached final
receipt; a changed fingerprint replaces every result with an unavailable
projection. An adversarial fixture mutates `info/exclude` after command one and
proves whole-batch failure. Target extraction then measured 1.73-1.93 seconds,
and the clean, uninstrumented 18-shard exhaustive suite passed in 289.65 seconds
under the unchanged 420-second ceiling. The scaling correction removes six
redundant traversals per authority context without changing the O(N) bound or
the TOCTOU invariant.

Vector collection orchestration is now in `core/collection_search.py`.
`search_engine.py` is 1,368 lines, `_search_collection` is 9 lines, the largest
new extraction helper is 37 lines, and the largest Tier-0 injection helper is
45 lines. Tests enforce `<1500` and `<=50`; there is no candidate exemption.

Promotion closure is author evidence only until the final explicit stage,
manifest regeneration, index-based digest proof, and independent verifier.
Version remains 0.4.101 and the candidate remains **NEEDS_VERIFICATION**.
