# HoloIndex Test Suite TESTModLog

## [2026-08-23] Tier-0 producer/consumer identity regression

- Added a production-shaped docs-indexer-to-strict-consumer regression after
  a live named-module query exposed absolute metadata rows.
- The regression rejects authority-root leakage by requiring exact
  repository-relative POSIX paths and proves README/INTERFACE exact lookup in
  canonical order.
- Focused indexer plus Tier-0 suite on the combined parent: 58 passed. It used
  a temporary tree and fake collection only; no live store, model, owner,
  maintenance, reindex, or replica mutation occurred.
- Added two GraphRAG regressions for authority-root resolution and traversal
  rejection, then an independent P1 falsifier for missing-root CWD authority;
  a second falsifier rejects absolute paths outside the root. The corrected
  complete focused compatibility matrix is 64 passed on the combined parent.
- Before merge reconciliation, adjacent Holo producer/incremental/intent/machine
  suites passed 201. On the exact combined parent, the focused 64 tests and 42
  owner-wrapper tests passed together as 106; RedDog backend
  compatibility/preflight also passed.
- A combined Python command timed out at 304 seconds without a result. Split
  execution isolated the closure tier: seven generator contracts passed and
  the eighth exposed only the old digest sentinel; that exact node passed in
  60.67 seconds after rebinding. The timeout is non-evidence and recorded as
  P1 test-scale debt rather than hidden or treated as success.

## [2026-08-22] Immutable snapshot query integration

- Added snapshot-store round-trip, artifact-tamper, real Chroma-export, Holo
  client selection/lifecycle, maintenance publication, and exact replica-
  generation binding coverage. The read adapter's existing adversarial codec
  and distance suite remains the query implementation contract.

## [2026-08-21] RedDog closed command-import regression

- Added a sealed `-S -B` subprocess test for the bundle command. It proves that
  direct-read audit grounding does not load the full Holo CLI or vector backend.
- The regression uses repository code and standard-library imports only; it
  performs no query, store, owner, maintenance, reindex, model, or network work.
- The exact owner bridge entrypoint is also imported in a sealed child and must
  leave `_cli_main`, the core vector module, ChromaDB, and NumPy unloaded.
- Reconciled the inherited fast-summary assertion with the existing four-bucket
  CLI receipt (`code`, `wsp`, `docs`, `knowledge`); no production output was
  changed or narrowed.

## [2026-08-20] Integrated module-intent and runtime closure

- The exact module-intent, Tier-0, machine-spec, freshness, isolated-probe, and
  process-runtime selection is **233 passed / 1 platform skip**. The earlier
  237/1 aggregate had no reproducible file selection and is superseded.
- Reproduction: `python -m pytest holo_index/tests/test_holoindex_freshness_receipt.py holo_index/tests/test_isolated_collection_snapshot_probe.py holo_index/tests/test_isolated_collection_snapshot_runtime.py holo_index/tests/test_machine_spec_contract.py holo_index/tests/test_tier0_retrieval_hardening.py holo_index/tests/test_module_intent_snapshot.py -q`.
- Verification used fixtures only; no live query, store, model, maintenance,
  reindex, or external runtime mutation occurred.

## [2026-08-17] R15 bridge copy-preservation adjacency

- Windows model-copy failure now proves handles close without deleting partial
  output, destructive APIs are absent, and query staging quarantine preserves
  injected partial bytes. Bounded seam: **211 passed / 5 skips**; no live Holo
  store, model, owner, maintenance, or reindex path ran.

## [2026-08-17] R14 bridge quarantine adjacency

- Bridge-owned synthetic tests now prove no-delete failure handling for active
  descriptors, publication temps, and staging directories, including mutation,
  replacement, collision, rename failure, and unsupported-platform behavior.
- The bounded ten-file Holo/bridge seam is **209 passed / 5 skips**. No live
  Holo store, model, owner, maintenance, or reindex path ran. Governed closure
  is **1,348 runtime files** and **1,525 tests / 265 quarantined**.

## [2026-08-17] Existing-sentinel retained lease units

- Four focused units prove absent sentinels are never created; existing exact
  regular single-link sentinels retain bytes, exclude contenders, release for
  later acquisition, and reject directory/hardlink aliases. Bridge replica
  tests separately retain both ordered sentinels through active publication.

## [2026-08-17] Query-replica materializer adjacency

- Bridge-owned synthetic tests cover immutable vector/model generation copying
  and canonical-byte preservation. Focused result is **17 passed / 2
  host-capability skips**; accepted-copy adjacency is **47 passed / 2 skips**.
  The accepted nine-file closure plus materializer is **165 collected = 160
  passed / 5 skips**. Governed manifest/registry validation is **34 passed**;
  the current closure is **1,347 runtime files** and **1,525 registered tests**.
  No live store was used, and owner routing is unverified.

## [2026-08-17] R11 retained executable capability regression

- Independent RED showed R10 only validated a descriptor before the runner and
  then closed it. New injected-runner tests prove live descriptor continuity,
  close-on-success/error, no launch after revalidation failure, and Windows
  replacement denial or Linux original-object execution through procfd.
- Exact acceptance is **146 collected = 143 passed / 3 named symlink-capability
  skips**; process-image scope is **14 = 13 passed / 1 skip** and includes an
  actual child launch. All six manifest-generator tests pass. The broad
  184-second timeout remains unresolved and was not rerun. No live Holo effect.

## [2026-08-17] R10 Windows process-image case-alias regression

- RED proved Windows admitted a lowercase spelling of a mixed-case executable;
  coverage now rejects both parent-directory and leaf-name case aliases using
  the live handle's final path.
- Process-image scope collected **11 = 10 passed / 1 skip**; the seven-file
  correction scope collected **125 = 123 passed / 2 skips**; the exact
  nine-file acceptance scope collected **141 = 138 passed / 3 skips**. All
  skips are named symlink-creation capability limits and are not passes.
- The full bridge-directory attempt timed out at its 184-second shell boundary
  without a captured outcome and is non-evidence. No live Holo effect ran.

## [2026-08-17] Snapshot executable and interactive-mode adversaries

- Added exact proven executable argv, mutable-`sys` denial, missing/changed proof
  pre-spawn failure, and `PYTHONINSPECT`/startup/home/user-base/provider scrub
  contracts. The proof is never serialized into the acceptance receipt.
- Final hostile matrix passed **87/2 skipped** three consecutive times; exact
  adjacent passed **271/2 skipped** and adversary/runtime/sanitizer passed
  **136/3 skipped**. Exact generator/registry metadata passed **41**. Registry
  is current at **1,524/265** and the 1,346-file manifest is pinned at
  `4de0e76a29dfc8d5338ee0c88251f3deb7af2820ca07afd4832655920045a663`.
  Fast Node contract/preflight/async passed; exhaustive shards were deferred.

## [2026-08-17] Isolated snapshot runtime authority

- Added subprocess contracts for exact argv/cwd/environment, hostile inherited
  package/config removal, invalid/ambiguous/unrelated/reparse runtime rejection
  before spawn, exact 1.5.5 origin success, and generation-bound 1.3.0 rejection
  before `PersistentClient`.
- The combined probe/candidate/receipt focused matrix passes **77 passed,
  2 skipped** on Windows; skips are platform/filesystem capability guards.

## [2026-08-16] K-dependent Tier-0 incident falsification

- RED: the exact Group-A query at K=1/12/20 failed all three new contracts
  because `_search_collection` lacked generation-complete module intent; an
  owner flattener regression separately reordered an unproven 41% README ahead
  of a 95% code hit.
- GREEN: proved fixed HEAD-catalog intent across changing top-K contexts,
  three real duplicate basenames, cache-by-root+HEAD invalidation, hostile and
  bounded Git failures, final-NUL framing, all-record path validation,
  Unicode `Cc`/`Cf`/`Cs` rejection, NFC-equivalent duplicate rejection,
  visible-Unicode preservation, 4,096/4,097 boundaries, platform-aware locked cache behavior,
  strict/non-strict catalog behavior, exact full paths, schema-bound target
  attestation, and absent/unrelated/ambiguous/multi/partial/mixed/duplicate/
  forged reservation rejection.
- Proved exact-type error allowlisting/redaction plus deterministic no-retry
  for Tier-0 incomplete/catalog unavailable and one retry for lookup failure.
  R3 Unicode RED: **8 failed, 39 passed** in 1.47 s; isolated GREEN:
  **47 passed** in 1.47 s. The exact six-file focused command, including the
  machine-spec contract, passed **278** in 4.00 s. Final bounded 13-file
  adjacent owner GREEN: **356 passed, 1 optional skip** in 11.21 s. The deterministic registry was
  regenerated twice at 1,517 tests/265 quarantined with identical SHA-256
  `0510244d701c7df08562852f02c76cdda1fccae6eb34fb387cd096aba375c675`.
- Final registry write/write/check took 7.231/7.222/7.355 s. Manifest
  write/write/check took 9.581/9.613/9.761 s with 1,337 runtime files,
  canonical digest `8e2680eb6075c56f1528a0cbdf2f08b44076cf8c814cec0f45c5a997df723ac9`,
  and file SHA-256 `b6910e4891b6b9008dd4d06699c209f5eddf5cff461a7aa2281618ffd5a95a41`.
  The >184 s all-bridge aggregate was not rerun; it is scale evidence, not
  acceptance evidence for this bounded slice.
- Manifest generator tests: **5 passed** in 29.18 s. Exact supervisor no-growth
  gate: **1 passed** in 1.25 s. Final manifest checks and the Node backend
  compatibility contract passed. Static closure covered 35 UTF-8 files, 18
  Python compile/AST files, 3 JSON files, and 1 JavaScript file; diff check and
  bounded secret-pattern scan (`0` hits) passed.
  No model, persistent store,
  reindex, resident owner, or network was used. (WSP 22/34/62/97)

## [2026-08-16] Final publication dirty-worktree falsification

- Injected clean/clean/dirty repository states across receipt construction,
  snapshot verification, and the final publication boundary.
- Proved the stable dirty error is returned and the atomic receipt remains
  IN_PROGRESS rather than publishing PASS. Combined focused maintenance
  suites: **53 passed**.

## [2026-08-16] Tier-0 R4 WSP 62 correction

- Removed candidate-authored `<=1500` and `<=225` allowances.
- Added strict `<1500` engine and `<=50` touched/new function checks across
  `search_engine.py`, `collection_search.py`, and `collection_injections.py`.
- Updated the vector slice-ID structural test to inspect the delegated scorer.
- Focused Tier-0 plus slice-ID suite: **55 passed**.

## [2026-08-16] Tier-0 R3 manifest-closure correction

- Reproduced that the extracted collection-injection runtime was imported by
  the search engine but absent from both Git tracking and the authenticated
  RedDog backend manifest.
- Bound the newly tracked dependency to import resolution, runtime membership,
  and its exact normalized digest in the canonical generator regression.
- Refreshed the staged Tier-0 helper to eliminate the R2 index/worktree split.
  Candidate remains `NEEDS_VERIFICATION` pending an independent verifier.
- Generator **4 passed**; focused Tier-0/MCP **86 passed**; exact WSP_62 and
  canonical backend manifest/preflight checks passed. The exhaustive extension
  shards were not rerun because no shard/reconstructed extension source changed
  and those shards do not exercise this generator dependency edge.

## [2026-08-16] Tier-0 R2 falsification

- Added RED-to-GREEN contracts proving strict owners discard duplicate vector
  root rows and replace them with exactly one exact README and INTERFACE.
- Proved collection exceptions reach the non-strict warning surface, uppercase
  explicit paths normalize, and exact WSP_62 file/function ceilings hold.
- Proved immutable-HEAD Git commands carry exact ownership and fixed
  no-hook/no-filter/no-replacement controls; repository-audit grounding now
  passes on the ownership-mismatched canonical checkout.

## [2026-08-16] Module Tier-0 retrieval falsification

- Proved explicit unique module intent retrieves only root README/INTERFACE in
  canonical order, excludes nested test README, stays bounded/deduplicated,
  and leaves ambiguous or implicit queries unchanged.
- Proved strict owner mode rejects exact-lookup failure, malformed
  cardinality, path mismatch, and either missing Tier-0 row; non-strict mode
  emits a truthful warning while preserving available evidence.
- Proved full-path precedence, exact basename boundaries, docs-only inference,
  bounded resources, anchored hit paths, and invalid-component rejection.
- Proved exact metadata rows carry schema-bound provenance with null similarity
  and survive vector floors without a fabricated score.
- Revalidated the expanded Holo ranking, bundle, audit-slice, extension, and
  machine-contract closure: 190 passed, 4 skipped (optional/environmental),
  with two known pytest configuration warnings under plugin-disabled mode.
- WSP 50/97 learning: an early manual Chroma exact-filter probe omitted
  supplied embeddings and caused Chroma to download a 79.3 MB ONNX model into
  the user cache. It changed no repository, persistent index, service, or
  dependency state. The cache was not deleted without authority; all
  subsequent validation uses deterministic fakes/supplied embeddings.

## [2026-08-15] Owner-evidence path projection receipt regression

- Proved the producer-owned executable result contract exactly matches the
  authoritative machine specification and rejects missing/unknown fields,
  alias/count/query divergence, cross-bucket fields, score injection,
  nonfinite ranking values, and forged backend/fingerprint maps.
- Moved the complete executable response schema into the authoritative machine
  JSON and made the runtime validator load and dispatch every declared value
  rule from that content-bound source; unknown, nested-map, and extraneous
  declarations fail closed during contract initialization.
- Added direct producer coverage for code, test, skill, docs, knowledge, WSP,
  symbol, and work-ledger hit families, including finite float priorities.
- Proved oversized integers reject as canonical schema failures rather than
  escaping as `OverflowError`, and that declared rule changes alter validation.
- Extracted the 85-line structural loader after WSP 62 review; its largest
  function is 29 lines. Proved malformed top-level lists, schema families,
  aliases, counts, and list/object/null/numeric declarations normalize to one
  startup failure before owner evidence is admitted.
- Proved canonical semantic evidence receives only repository-relative paths
  for backend `tests`/`skills` aliases and their typed hit buckets.
- Preserved generation-bound receipt construction with no query-time reindex.

## [2026-08-11] Immutable repository-audit evidence regressions

- Proved dirty tracked overlays are ignored, untracked candidates reject,
  hardlinks reject, and final accepted bytes remain bound to exact Git HEAD.
- Preserved path pruning, fixed resource ceilings, no-shell execution, and
  WSP 62 function-size enforcement.
- Proved size and prefix reads share one deadline; oversized blobs stream only
  bounded prefixes and binary rejection charges exact attempted bytes.

## [2026-08-11] Legacy symbol persistence-policy upgrade regression

- Proved matching embedding metadata cannot preserve a legacy symbol
  collection whose complete HNSW batch/sync policy is not pinned, including
  wrong and missing `batch_size` values.
- Proved the legacy collection resets and re-embeds, while compliant
  collections continue to use the existing reconciliation path.

## [2026-08-11] Durable vector-segment publication regressions

- Proved with Chroma 1.5.5 that legacy sub-threshold collections are not
  durable and that policy-bound collections survive four cleared-client
  opens plus a real subprocess proof under migration-validation mode.
- Added exact rejection for a missing persisted metadata artifact and a
  tampered HNSW persistence policy, plus an actual Windows junction escape.
- Added checkpoint-plus-tail coverage so a post-checkpoint WAL tail remains
  available to the independent subprocess verifier.
- Replaced transient-success convergence tests with fail-closed publication
  tests: no later reopen can override `VECTOR_SEGMENT_UNAVAILABLE`.
- Preserved write-mode configuration coverage and the existing maintenance,
  owner, freshness, transport, and startup admission matrices.

## [2026-08-04] Sandboxed write-probe regression

- Replaced the import-time, checkout-specific `test_write.txt` write with a
  pytest `tmp_path` probe.
- Added source-level regression coverage preventing module-import filesystem
  effects and a return of any absolute Windows checkout target.

## [2026-08-02] Persisted vector-segment cold-start gate

- Proved exact persisted collection snapshots are insufficient to certify
  semantic readiness when a Chroma HNSW segment cannot reopen.
- Added isolated child-response and direct-probe regressions for
  `VECTOR_SEGMENT_UNAVAILABLE`, while preserving exact-generation response
  binding and the healthy round-trip path.
- Added adversarial coverage for forged neighbor IDs, unsupported unbounded
  embedding reads, oversized child output, strict child response shape,
  Chroma-version mismatch, writer-finalization failure, and incremental-owner
  publication bypass. Incremental publication also rejects a verifier-returned
  mismatch list; only an empty proof result can publish freshness.
- Proved the maintenance-only probe runs after writer finalization with
  migrations validation and no logical mutation or indexing API.

## [2026-07-25] REDDOG_HOLOINDEX_SEMANTIC_EVIDENCE_RECEIPT_BINDING_PHASE1

- Added digest-change, exact bucket/metadata serialization, item-count, and ignored-extra-field coverage.
- Proved semantic evidence changes also change the canonical query receipt ID.

## [2026-07-25] REDDOG_HOLOINDEX_AUTHORITY_WORKTREE_QUERY_BINDING_PHASE1

- Added authority selection coverage for configured and deterministic roots, dirty workspace overlays, unrelated repositories, dirty authorities, HEAD mismatch, invalid configuration, and workspace fallback.
- Added owner request/response root-digest checks, forged-root rejection, post-query revalidation, and source guards against query-path mutation.

## [2026-07-24] HOLOINDEX_QUERY_ROOT_ADMISSION_P0_PHASE1

- Added exact proof tests for foreign worktree receipts, maintenance,
  same-root wrong HEAD/SSD, missing generation, incomplete baseline, and a
  clean admitted generation.
- Added CLI and bundle fail-before-backend tests plus an offline lexical
  no-persistent-admission regression. A foreign-summary test records every
  read and proves the supplied SSD is untouched while current-repository WSP
  metadata remains available.
- Added focused `test_bundle_path_confinement.py` coverage for absolute and
  traversal hints, root/component/nested reparse denial, optional real
  symlinks, artifact no-follow checks, and nested-walk entry budgets.
- Added raw-CLI NAVIGATION symlink/reparse/oversize coverage plus explicit
  module-domain and WSP discovery caps. Oversized directories are tested with
  a match both before and after the cap so no partial filesystem-order result
  can be accepted.
- Final unfiltered admission/confinement/direct matrix: 62 passed with five
  portable real-symlink skips; deterministic reparse cases all executed.
- Added canonical-receipt override/final-reparse denial, module-walk
  complete-or-empty cap/depth/error/order, and bundle-handler WSP_62
  regressions. Split completeness tests into a focused file; no exemption was
  added.
- RED was the missing `holo_index.query_admission` module; focused GREEN
  evidence is recorded in the WSP_97 execution receipt.
- Wider CLI/index diagnostic passed 32 and retained one exact origin/main
  baseline failure:
  `test_index_refresh_repair.py::TestWspPurity::test_wsp_purity_only_wsp_files`
  expects a literal `glob("WSP_*.md")` source string in untouched indexing code.

## [2026-07-20] RedDog Repository-Audit Consumer Binding Repair

- Added `.worktrees` pruning coverage alongside vendor/generated roots.
- Retained confined-reader traversal, link/reparse, final-handle, identity-race,
  byte-budget, deterministic-ordering, and source-plus-test coverage tests.

## [2026-07-18] HoloIndex / RedDog Operational Truth Boundary POC

**WSP Protocol**: WSP 05, 06, 15, 22, 50, 62, 87, 97
**Phase**: POC implementation complete; focused validation green; PR pending
**Agent**: 0102 architect with delegated adversarial workers

**Changes**:

- Added storage precedence/error, read-only no-write, canonical test registry,
  deterministic CLI selection, clean repository, maintenance lease, atomic
  receipt, and scoped freshness regressions.
- Added adversarial incremental tests for legacy ID cleanup, AST symbol schema,
  exact-path survival, missing/busy maintenance authority, repository races,
  partial mutation, incomplete collection scope, and final receipt failure.
- Added source-order coverage proving invalidation begins before mutable
  HoloIndex initialization and final publication is delegated to the
  maintenance session.
- Added canonical source-scope, Git-tracked filtering, full raw web-manifest,
  cap/read-failure, semantic-preflight, linked-worktree, mixed-registry, and
  snapshot-only incremental proof regressions.
- Added embedding artifact/fingerprint, Hugging Face ref and incomplete-cache,
  prompt timeout return, canonical fp32 maintenance, legacy self-healing,
  runtime map mismatch, cache-disable, and resident generation-pin regressions.
- Added strict-owner collection-count and blocking-encode regressions proving
  swallowed errors or lexical fallback cannot produce CURRENT.
- Added a CodeQL regression proving caller-controlled diagnostic and exception
  text cannot leak through timeout-wrapper logs.
- Final HoloIndex evidence: storage/source/CLI/embedding/backend 88 passed;
  freshness/maintenance 143 passed; incremental/work-ledger 109 passed; and
  machine-contract validation 6 passed (346 total, no failures or skips).
- Independent owner/client/maintenance/security evidence: 289 passed. These are
  scoped matrices, not a whole-repository claim.

**Impact**: The test surface is designed to distinguish complete canonical
maintenance from scoped diagnostics and reject the enumerated false-CURRENT
paths.

**WSP Compliance**: Assertions require lexical, skipped-source, malformed,
dirty, raced, and snapshot-only results to remain non-operational. All 81
changed or added Python files compiled, the machine JSON parsed at exactly 200
lines, and the WSP_97 execution receipt validated structurally.

## [2026-04-21] W8 — Core Module Test Coverage Phase 1
**WSP Protocol**: WSP 5 (Testing Standards), WSP 22 (Documentation)

### Summary
Added 94 tests across 4 new test files for `holo_index/core/` modules:
- `test_circuit_breaker.py` (23 tests) — circuit breaker pattern tests
- `test_mps_m_scorer.py` (40 tests) — MPS-M quality scoring tests
- `test_comment_search.py` (10 tests) — comment search API tests
- `test_module_scoring_subroutine.py` (21 tests) — module scoring wrapper tests

### Coverage Impact
| Module | Before | After |
|--------|--------|-------|
| circuit_breaker.py | 0% | 98% |
| mps_m_scorer.py | 0% | 96% |
| comment_search.py | 0% | 100% |
| module_scoring_subroutine.py | 16% | 87% |

### Verification
```bash
HOLO_SKIP_MODEL=1 python -m pytest holo_index/tests/test_circuit_breaker.py \
  holo_index/tests/test_mps_m_scorer.py holo_index/tests/test_comment_search.py \
  holo_index/tests/test_module_scoring_subroutine.py -v --tb=short
# Result: 94 passed
```

## [2026-03-08] MCP Dependency Guard Coverage
**WSP Protocol**: WSP 5 (Testing Standards), WSP 22 (Documentation), WSP 84 (Enhance Existing)

### Summary
- Added `test_holo_mcp_client.py`.
- Verifies `HoloIndexMCPClient.connect()` fails cleanly when `fastmcp` is unavailable instead of attempting a dead subprocess launch.

### Verification
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest holo_index/tests/test_holo_mcp_client.py -q`
- Result: `1 passed`

## [2026-03-08] Brain Artifact Training Corpus Coverage
**WSP Protocol**: WSP 5 (Testing Standards), WSP 22 (Documentation), WSP 84 (Enhance Existing)

### Summary
- Added `test_comprehensive_training_corpus_brain_artifacts.py`.
- Validates:
  - `ComprehensiveTrainingCorpus.collect_all()` now includes brain-artifact DPO and SFT rows.
  - `export_brain_training_jsonl()` writes pipeline-compatible JSONL outputs.

### Verification
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest holo_index/tests/test_comprehensive_training_corpus_brain_artifacts.py -q`
- Result: `2 passed` (plus repo-level pytest config warnings in this environment)

## [2026-02-18] Machine Contract Governance Lock
**WSP Protocol**: WSP 5 (Testing Standards), WSP 6 (Audit Coverage), WSP 22 (Documentation)

### Summary
- Added `test_machine_spec_contract.py` to enforce source-of-truth governance:
  - machine JSON spec remains authoritative
  - `INTERFACE.md` declares policy
  - `CLI_REFERENCE.md` remains explicitly non-normative

### Verification
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest holo_index/tests/test_machine_spec_contract.py -q`

## [2026-02-18] Contract Drift Hardening Regression
**WSP Protocol**: WSP 5 (Testing Standards), WSP 6 (Audit Coverage), WSP 22 (Documentation)

### Summary
- Re-ran targeted contract suite after runtime/interface hardening:
  - intent classification
  - output composition compatibility
  - memory output contract
  - doc-type filtering behavior
- Verified that previously drifting contracts now align.

### Verification
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest holo_index/tests/test_intent_classifier.py holo_index/tests/test_output_composer.py holo_index/tests/test_memory_output_contract.py holo_index/tests/test_doc_type_filtering.py -q`
- Result: `45 passed` (2 pytest config warnings in this environment)

## [2026-02-12] 012 Scratchpad Source Resolver Coverage
**WSP Protocol**: WSP 5 (Testing Standards), WSP 6 (Audit Coverage), WSP 22 (Documentation)

### Summary
- Added `test_ingest_012_corpus.py` to validate deterministic source resolution for 012 corpus ingest.
- Covers:
  - Auto mode prefers root `012.txt` scratchpad.
  - Explicit relative path resolution works for docs mirror path.

### Verification
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest holo_index/tests/test_ingest_012_corpus.py -q`

## [2026-02-11] Holo System Check WSP Sentinel Coverage
**WSP Protocol**: WSP 5 (Testing Standards), WSP 6 (Audit Coverage), WSP 22 (Documentation)

### Summary
- Added `test_holo_system_check.py` to validate WSP framework sentinel integration in system-check output.
- Covers:
  - `run_system_check(...)` includes `wsp_framework_health` payload.
  - `write_system_check_report(...)` renders `WSP Framework Health` section.

### Verification
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest holo_index/tests/test_holo_system_check.py -q`

## [2026-02-11] Web Asset Indexing Coverage
**WSP Protocol**: WSP 5 (Testing Standards), WSP 6 (Audit Coverage), WSP 22 (Documentation)

### Summary
- Added `test_web_asset_indexing.py` to validate semantic ingestion of `public` HTML/JS assets.
- Covers enabled path, disabled toggle path, and merged indexing with NAVIGATION entries.
- Locks retrieval behavior needed for FoundUP cube animation artifacts.

### Verification
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest holo_index/tests/test_web_asset_indexing.py -q`

## [2026-02-08] Windows Decode Hardening Verification
**WSP Protocol**: WSP 5 (Testing Standards), WSP 6 (Audit Coverage), WSP 22 (Documentation)

### Summary
- Verified search cache hit path with repeated-query timing + cache stats.
- Validated CLI search no longer emits Windows cp932 decode thread noise under current repro commands.
- Covered runtime subprocess hardening paths with UTF-8 decode settings.

### Verification
- `python - <<script>>` timing harness for repeated `HoloIndex.search()` (cache hit/miss stats).
- `python holo_index.py --offline --fast-search --search "persistence" --limit 6 --quiet-root-alerts`
- `python holo_index.py --offline --search "persistence" --limit 6 --quiet-root-alerts`
- `Measure-Command { python holo_index.py --offline --fast-search --search "persistence" --limit 6 --quiet-root-alerts | Out-Null }`

## [2026-02-08] Fast Search Mode Coverage
**WSP Protocol**: WSP 5 (Testing Standards), WSP 6 (Audit Coverage), WSP 22 (Documentation)

### Summary
- Added `test_fast_search_mode.py` to validate retrieval fast-path controls.
- Covers activation via `--fast-search` and `HOLO_FAST_SEARCH=1`.
- Verifies compact fast-path summary output format.

### Verification
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest holo_index/tests/test_fast_search_mode.py -q`

## ++ CodeIndex Circulation Monitor Coverage
**WSP Protocol**: WSP 93 (CodeIndex), WSP 35 (HoloIndex Qwen Advisor Plan), WSP 5 (Testing Standards), WSP 6 (Audit Coverage), WSP 22 (Documentation)

### Summary
- Added `test_codeindex_monitor.py` to validate the new circulation engine + architect decision helpers that feed 0102.
- Synthetic module fixture reuses CodeIndex first principles (200+ line function) to keep tests deterministic and fast.
- Extended coverage to orchestrator heuristics so CodeIndex activation follows WSP 93 first principles.

### Test Coverage
- [OK] `CodeIndexCirculationEngine.evaluate_module` returns structured HealthReport with surgical fixes and assumption alerts.
- [OK] `ArchitectDecisionEngine` produces A/B/C framing and console summaries without hitting external dependencies.
- [OK] `QwenOrchestrator._should_trigger_codeindex` and `_generate_codeindex_section` fire on large-module/refactor scenarios.

### Verification
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest holo_index/tests/test_codeindex_monitor.py holo_index/tests/test_codeindex_precision.py`

## ++ CodeIndex Advisor Surgical Regression Coverage
**WSP Protocol**: WSP 93 (CodeIndex), WSP 35 (Qwen Advisor), WSP 5 (Testing Standards), WSP 6 (Audit Coverage), WSP 22 (Documentation)

### Summary
- Added test_codeindex_precision.py covering surgical fixes, LEGO mapping, circulation health, choice framing, and assumption detection for QwenAdvisor.
- Uses isolated tempfile fixture with 200+ line routine to validate first-principles behaviour without mutating production modules.

### Test Coverage
- surgical_code_index now emits high-complexity fix coordinates with 90-minute effort estimates.
- lego_visualization, present_choice, and continuous_circulation outputs verified against WSP 93 architect workflow.
- challenge_assumptions surfaces TODO plus long hardcoded path after loop indentation correction.

### Verification
- PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest holo_index/tests/test_codeindex_precision.py

## [2025-09-29] Coordinator Output & Telemetry Coverage
- Added tests for HoloOutputFormatter summary/TODO structure and telemetry JSONL logging.
- Existing coordinator tests now validate structured response still includes arbitration/execution details.
- Pending: module map + doc consumption tests once coordinator integration lands.

## [2026-02-06] Holo vs grep Integration Test Refresh
**WSP Protocol**: WSP 5 (Testing Standards), WSP 6 (Audit Coverage), WSP 22 (Documentation)

### Summary
- Updated `test_holo_vs_grep.py` assertions to reflect current CLI output formatting.
- Added UTF-8 safe subprocess decoding for HoloIndex and rg outputs.
- Reframed TSX preview test to semantic-result availability when literal rg fails.
- Documented SWOT comparison in `holo_index/tests/TEST_SUITE_DOCUMENTATION.md`.

### Verification
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest holo_index/tests/test_holo_vs_grep.py -q`

## [2026-02-06] Video Search Health Probe Tests
**WSP Protocol**: WSP 5 (Testing Standards), WSP 34 (Test Documentation), WSP 22 (Documentation)

### Summary
- Added `test_video_search_healthcheck.py` to validate video index health probe toggles.
- Covers disable flag, healthcheck disable path, and failure blocking.

### Verification
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest holo_index/tests/test_video_search_healthcheck.py -q`

## [2026-02-06] Video Search SQLite Metadata Index Tests
**WSP Protocol**: WSP 5 (Testing Standards), WSP 34 (Test Documentation), WSP 22 (Documentation)

### Summary
- Added `test_video_search_metadata_db.py` to verify SQLite audit index writes.
- Uses a manual instance (no ChromaDB init) to keep tests isolated.

### Verification
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest holo_index/tests/test_video_search_metadata_db.py -q`

## [2026-02-06] Benchmark Runner Controls
**WSP Protocol**: WSP 5 (Testing Standards), WSP 22 (Documentation)

### Summary
- Added BENCH_* env timeouts and BENCH_MAX_QUERIES to keep benchmark runs bounded.
- Forced UTF-8 subprocess decoding and ASCII-only report markers to avoid Windows encoding crashes.

### Verification
- `BENCH_MAX_QUERIES=4 python holo_index/tests/benchmark_holo_vs_tools.py`
  - Bounded run executed with `BENCH_MAX_QUERIES=2` (literal queries only).


## Purpose (Read Before Writing Tests)
- Provide automated coverage for HoloIndex + Qwen advisor features.
- Enforce WSP 22 logging and FMAS review before adding new pytest cases.
- Reference full FMAS plan in WSP_framework/docs/testing/HOLOINDEX_QWEN_ADVISOR_FMAS_PLAN.md.

## Execution Notes
- Run from repo root: pytest tests/holo_index.
- Consult NAVIGATION + HoloIndex before authoring tests (WSP 87).
- Update this TESTModLog with summary + verification whenever tests change.

## [2025-09-26] - Dependency Test Files Recreated (WSP Compliance)

**WSP Protocol**: WSP 3 (Module Organization), WSP 5 (Testing Standards), WSP 84 (Don't vibecode)

### Summary
- **Issue**: Root-level dependency test files were incorrectly placed (vibecoding)
- **Resolution**: Recreated test files in proper holo_index/tests/ location per WSP 3
- **Files Recreated**:
  - `test_simple.py` - Simple dependency import testing
  - `test_focused_audit.py` - HoloIndex-focused dependency auditing
  - `test_dependency_fix.py` - Dependency resolution testing
- **WSP Compliance**: Tests now follow proper module organization structure

### Test Coverage
- [OK] Basic dependency import resolution testing
- [OK] Focused HoloIndex auditing capabilities
- [OK] Module health integration validation
- [OK] Import chain validation and dependency scanning

## [2025-09-28] - Enhanced Coordinator Test Suite Added

**WSP Protocol**: WSP 5 (Test Coverage), WSP 6 (Test Audit), WSP 22 (Documentation)

### Summary
- **Purpose**: Test clean output formatting and telemetry features
- **Agent**: 0102 (Enhanced implementation based on 012's observations)
- **File Enhanced**: `test_holodae_coordinator.py` (added TestEnhancedFeatures class)
- **WSP Violation Fixed**: V019 - Removed duplicate test_enhanced_coordinator.py, enhanced existing file instead

### Test Coverage
- [OK] Clean output structure verification (SUMMARY/TODO/DETAILS)
- [OK] JSON telemetry logging to JSONL files
- [OK] Module map generation for orphan analysis
- [OK] Orphan file detection logic
- [OK] Output parsing from coordinator
- [OK] Alert extraction from logs
- [OK] Document tracking (hints and reads)
- [OK] Session-based telemetry organization

### Key Features Tested
1. **Output Formatting**: Validates structured, actionable output format
2. **Telemetry Pipeline**: Confirms JSON events logged correctly
3. **Module Mapping**: Tests orphan detection and import analysis
4. **Doc Compliance**: Tracks document hints vs actual reads

### Impact
- Provides regression testing for Sprint 1 improvements
- Ensures telemetry format stability for recursive learning
- Validates orphan detection accuracy
- [OK] Enhanced dependency auditor functionality testing

### Architecture Notes
- Tests located in `holo_index/tests/` per WSP 3 enterprise domain organization
- Each test file focuses on specific holo_index functionality
- Proper test isolation and WSP 5 testing standards compliance

---

## [2025-09-22] - Suite Initialization (Planning)
**WSP Protocol**: WSP 22, WSP 35, WSP 17, WSP 18, WSP 87

### Summary
- Created tests/holo_index/ scaffolding (TESTModLog, FMAS plan reference, pytest stub).
- Preparing Qwen advisor coverage to align with execution plan WSP_35_HoloIndex_Qwen_Advisor_Plan.md.
- Placeholder advisor test (	ests/holo_index/test_qwen_advisor_stub.py) marks suite for discovery.
- Tagged PQN cube metadata, FMAS reminders, onboarding banner, and reward telemetry scaffolding; expand tests once advisor inference lands.
- Scaffolded holo_index/qwen_advisor/ package (config, prompts, cache, telemetry) ready for test integration.

### Next Actions
- Populate WSP_framework/docs/testing/HOLOINDEX_QWEN_ADVISOR_FMAS_PLAN.md with concrete cases during implementation.
- Replace stub with real advisor tests (prompt, cache, CLI flag, telemetry).
- Record test execution results in this TESTModLog and root ModLog once features land.

## [2025-09-23] - Module Health FMAS Tests
**WSP Protocol**: WSP 87 (Code Navigation), WSP 49 (Module Structure)

### Summary
- Created `test_module_health.py` with 14 comprehensive tests
- **SizeAuditor Tests** (6 tests):
  - `test_file_under_threshold`: Files <800 lines are OK
  - `test_file_warn_threshold`: Files 800-1000 lines trigger warning
  - `test_file_critical_threshold`: Files >1000 lines are critical
  - `test_nonexistent_file`: Handles missing files gracefully
  - `test_non_python_file_skipped`: Skips non-Python files
  - `test_audit_module`: Audits entire module directories
- **StructureAuditor Tests** (6 tests):
  - `test_compliant_module`: Validates fully compliant structures
  - `test_missing_readme`: Detects missing README.md
  - `test_missing_tests_directory`: Detects missing tests/
  - `test_find_module_root_direct`: Finds module from direct path
  - `test_find_module_root_from_file`: Finds module from file within
  - `test_nonexistent_module`: Handles missing modules
- **Integration Tests** (2 tests):
  - `test_rules_engine_with_health_checks`: Validates rules engine integration
  - `test_path_resolution`: Tests various path format resolutions

### Test Results
- **All 14 tests passing** (100% success rate)
- Execution time: ~8.4 seconds
- Coverage: Size thresholds, structure validation, path resolution, integration

### Verification
- Module health checks properly integrated into advisor flow
- Health notices appear in CLI output and advisor guidance
- Path resolution handles direct paths, module notation, and navigation locations

## [2025-09-23] - Integration Test Suite Documentation
**WSP Protocol**: WSP 22 (Documentation Standards), WSP 6 (Test Audit)

### Summary
**Documented previously undocumented integration test files** discovered through --audit-docs command. Added comprehensive coverage for LLM integration, pattern analysis, and coaching functionality tests.

### Integration Test Files (tests/integration/)

#### LLM Integration Tests (2 files)
- **`test_llm_integration.py`**: Validates core LLM engine functionality
  - Tests QwenInferenceEngine initialization and basic inference
  - Verifies model loading, context handling, and error recovery
  - Ensures LLM dependencies are properly configured
  - **Coverage**: Model loading, basic inference, error handling

- **`test_llm_functionality.py`**: Comprehensive LLM capability validation
  - Tests actual text generation with Qwen-Coder-1.5B model
  - Validates code analysis and contextual understanding
  - Measures inference performance and response quality
  - **Coverage**: Code analysis, response generation, performance metrics

#### Pattern Analysis Tests (2 files)
- **`test_pattern_analysis.py`**: Pattern detection and learning validation
  - Tests behavioral pattern recognition algorithms
  - Validates pattern storage and retrieval mechanisms
  - Ensures pattern evolution and adaptation
  - **Coverage**: Pattern recognition, learning algorithms, data persistence

- **`test_pattern_coach.py`**: Intelligent coaching system validation
  - Tests contextual coaching based on user behavior
  - Validates reward system integration and feedback loops
  - Ensures coaching effectiveness measurement
  - **Coverage**: Behavioral coaching, reward integration, effectiveness tracking

### Test Execution Notes
- **Location**: `tests/integration/` (separated from unit tests for clarity)
- **Dependencies**: Requires LLM model and database access for full functionality
- **Execution**: Run with `pytest tests/integration/` or individual test files
- **Purpose**: Validate end-to-end functionality of complex HoloIndex features

### WSP Compliance
- **WSP 6**: Comprehensive test coverage for critical functionality
- **WSP 22**: Proper documentation prevents lost work and maintenance issues
- **WSP 35**: LLM advisor testing aligns with implementation plan

### Verification
- All 4 integration test files now properly documented in TESTModLog
- Test purposes, coverage areas, and execution requirements specified
- Documentation audit (--audit-docs) now passes for test files

## [2025-09-28] - HoloDAE Modular Refactoring Impact Assessment

**WSP Protocol**: WSP 22 (ModLog), WSP 6 (Test Audit), WSP 62 (Modularity), WSP 80 (DAE Orchestration)

### **CRITICAL: Test Suite Requires Updates Due to Major Architectural Refactoring**

#### **Architectural Change Impact**
- **BEFORE**: Monolithic `autonomous_holodae.py` (1,405 lines)
- **AFTER**: 12 modular components with new Qwen->0102 architecture
- **Impact**: All existing tests importing old structure are now broken

#### **Affected Test Files**
- **`test_qwen_advisor_fmas.py`**: Imports from old `advisor.py`, `pattern_coach.py` structure
- **`test_qwen_advisor_stub.py`**: References old monolithic architecture
- **Integration tests**: May need updates for new modular imports

#### **Test Updates Completed**
1. [OK] **Basic Coordinator Tests**: Created `test_holodae_coordinator.py` with 6 test cases
2. [OK] **Import Path Updates**: Tests use new `holo_index.qwen_advisor` modular imports
3. [OK] **API Updates**: Tests validate new `HoloDAECoordinator` functionality
4. [OK] **Architecture Awareness**: Tests validate Qwen->0102 orchestration and MPS arbitration
5. [OK] **Component Integration**: Tests verify modular components work together

#### **Test Coverage Added**
- **Coordinator Initialization**: Verifies all modular components instantiate correctly
- **HoloIndex Request Handling**: Tests Qwen orchestration -> MPS arbitration flow
- **Monitoring Controls**: Validates start/stop monitoring functionality
- **Status Reporting**: Tests comprehensive status summary generation
- **Arbitration Decisions**: Validates MPS scoring and action prioritization

#### **WSP Compliance**
- [OK] **WSP 22**: Test updates properly documented in TESTModLog
- [OK] **WSP 6**: Basic automated test coverage established for new architecture
- [OK] **WSP 62**: Tests updated to match new modular structure
- [OK] **WSP 80**: Tests validate new Qwen->0102 orchestration architecture

#### **Remaining Test Work**
- Update legacy tests to use new modular imports (separate effort)
- Add performance/load testing for orchestration components
- Create integration tests for end-to-end Qwen->0102->012 flow

---

## [2025-09-23] - WSP 83 Orphan Remediation - Test Suite Documentation
**WSP Protocol**: WSP 83 (Documentation Tree Attachment), WSP 22 (ModLog), WSP 6 (Test Audit)

### Summary
**Remediated orphaned test files** discovered by --audit-docs command. Attached all test files to system tree per WSP 83 requirements, ensuring 0102 operational value and preventing documentation drift.

### Core Test Files Documentation

#### CLI Testing Suite (`tests/test_cli.py`)
**Purpose**: Validate HoloIndex CLI functionality and command-line interface
- **Coverage**: Command parsing, argument validation, output formatting
- **Test Cases**: Search commands, advisor integration, DAE initialization
- **Execution**: `pytest tests/test_cli.py`
- **Dependencies**: HoloIndex core, CLI arguments, output formatting
- **WSP Compliance**: WSP 87 (Code Navigation), WSP 35 (HoloIndex Implementation)

#### Qwen Advisor FMAS Tests (`tests/test_qwen_advisor_fmas.py`)
**Purpose**: Comprehensive FMAS testing for Qwen advisor functionality
- **Coverage**: LLM integration, prompt processing, response generation, error handling
- **Test Cases**: Model loading, inference pipeline, advisor recommendations, telemetry
- **Execution**: `pytest tests/test_qwen_advisor_fmas.py`
- **Dependencies**: Qwen-Coder model, llama-cpp-python, advisor configuration
- **WSP Compliance**: WSP 35 (HoloIndex Qwen Advisor), WSP 4 (FMAS Validation)

#### UnDaoDu Validation Tests (`tests/un_dao_du_validation.py`)
**Purpose**: Domain-specific validation for UnDaoDu channel operations
- **Coverage**: Channel-specific logic, content validation, integration testing
- **Test Cases**: Stream detection, content processing, error scenarios
- **Execution**: `pytest tests/un_dao_du_validation.py`
- **Dependencies**: YouTube API integration, channel-specific configurations
- **WSP Compliance**: WSP 27 (DAE Operations), domain-specific validation protocols


### WSP 83 Compliance Verification

#### Reference Chain Established
- [OK] All test files documented in TESTModLog (WSP 22)
- [OK] All scripts documented in main ModLog (WSP 22)
- [OK] Clear operational purpose for 0102 agents (WSP 83.2.2)
- [OK] Proper tree attachment via documentation (WSP 83.3.2)

#### Orphan Prevention
- [OK] No orphaned documentation remaining
- [OK] All files serve 0102 operational needs
- [OK] Reference chains prevent future orphaning
- [OK] Documentation audit now passes

### Execution Notes
- **Run All Tests**: `pytest holo_index/tests/`
- **Run Scripts**: Execute individually from `holo_index/scripts/` directory
- **Integration Testing**: Scripts support automated verification workflows
- **Maintenance**: Update TESTModLog when adding new test files (WSP 22)

### Technical Implementation
- **Test Framework**: pytest with standard assertions and error handling
- **Script Dependencies**: Python standard library + HoloIndex components
- **Error Handling**: Comprehensive exception catching with diagnostic output
- **Performance**: Optimized for fast execution in CI/CD pipelines
## [2026-08-03] Windows device-entry repository discovery regression

- Proved an unrelativizable Windows device entry is excluded and counted while
  valid implementation/test evidence remains discoverable.
