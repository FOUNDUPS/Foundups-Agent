# foundups_mcp_bridge TestModLog

## [2026-08-30] Inert builder-runtime composition falsification

- Captured authentic RED collection before production code: the focused suite
  failed with `ModuleNotFoundError` for the absent coordinator module.
- Added 36 falsifiers for exact outer call order, complete dependency identity,
  exact result classes and booleans, stable path-free strings and exception
  graphs, stage short-circuiting, no rollback/delete, descriptor-only
  persistence, strict runtime nonclaims, first publication, exact reuse, and
  the public reviewed O: wheel with an exact synthetic base.
- The real binding exposed that the base payload root is `python-runtime`; this
  is retained as next-sprint process/candidate consumer debt rather than hidden
  by synthetic fixtures. Focused tests pass 36; the adjacent selection passes
  318 with six expected capability/opt-in skips. Generated-manifest coverage
  passes 8; WSP_97 coverage passes 74 with one expected skip. The registry is
  current at 1,637 / 269 quarantined and the 1,394-file backend digest is
  `5c081f20d5db...f9c6`. (WSP 6/15/50/62/84/97)

## [2026-08-29] Sequential builder/dependency composition falsification

- Added 19 focused falsifiers for exact source/dependency/source sequencing,
  live source authority at both observations, durable source identity excluding
  call-local publication truth, dependency-tree equality, a real dependency
  materializer call, source/tree drift, invalid dependency claims, strict bool
  and reuse handling, stable path-free failures, no rollback/deletion, and
  path-free public nonclaims.
- The initial authentic run exposed a Windows `Path` subtype rejection in the
  contract; replacing exact-class path checks with `isinstance(..., Path)` made
  valid Windows bindings admissible without weakening absolute-path checks.
  Independent hostile review then identified that the call-local publication
  field required exact-bool validation; a hostile `Path` falsifier closes that
  authority-leak surface. A second three-stage falsifier requires every reuse
  observation to be an exact boolean. The final physical falsifier runs the
  sealed public coordinator against the real reviewed O: wheel for first
  publication and complete reuse, with unchanged source bytes.
- Final evidence is **19 focused passes**, **246 / seven expected skips** across
  the exact 16-file adjacent builder/dependency surface, **58 generated
  registry/manifest passes**, and **66 / one expected skip** for the WSP_97
  validator. The registry is current at 1,636 tests / 269 quarantines; the
  backend closure is 1,391 files at `a5831a36d548...85509`.
  Extension compatibility and deterministic 67-file package-surface checks
  passed; no VSIX was emitted for this backend-only slice.
  (WSP 6/15/50/62/84/97)

## [2026-08-29] Wheel-bound packaging source phase 2C2a falsification

- Captured authentic RED collection before implementation: both new suites
  failed with `ModuleNotFoundError` for the absent source-contract module; no
  fixture or pytest configuration failed.
- Added 44 focused falsifiers for wheel-vs-tree generation identity, exact raw
  and extracted bytes, source lease duration, strict nonclaims, private byte
  authority, canonical contracts, mutation/ADS/hardlink/extra topology,
  store/limit/token rejection, pre/post-publication quarantine, valid/corrupt
  no-replace winners, reuse, two-thread convergence, quarantine failure cause
  preservation, O(depth) handle behavior across 105 sibling members, public
  authority/nonclaim completeness, O:/E: pre-mutation confinement, valid
  payload/token pre-mutation rejection, wheel ADS/hardlink/reparse and case
  alias rejection, unconditional scope-exit source reproof, and mutations
  between two consecutive complete verification passes, denied tail writes to
  descriptor/inventory/wheel/member files under retained handles, and rejection
  of a tail-added file by the terminal complete-topology proof. The final
  falsifier flips both unsigned persisted authority booleans and proves neither
  durable verification nor public reuse can inherit publication-time authority;
  only current live-source verification becomes true on reuse.
- The exact provisioned O: wheel passed first publication plus 200 full reuses
  in **105.09 seconds**. One wheel-bound generation remained, durable binding
  fields matched, only the first result carried publication-time lease
  authority, every call carried current-verification authority, process
  handle/RSS deltas stayed below fixed gates, no dependency runtime appeared,
  and the source SHA remained unchanged.
- The focused result is **44 passed / one expected opt-in skip**. Broader
  evidence passed: **227 / 7 expected skips** across the exact 15-file adjacent
  builder/dependency surface, **36 passed** for registry/manifest generation,
  **66 / 1 expected skip** for the WSP_97 validator, and both extension
  compatibility/package-surface checks. The final backend closure is 1,388
  files at `ff0fb87a...e60c6`. (WSP 6/15/50/62/84/97)

## [2026-08-29] Reviewed packaging wheel admission falsification

- Recorded an authentic RED collection failure before implementation:
  `ModuleNotFoundError` for the absent wheel-admission module. That evidence
  exists in the operator execution transcript; Git history alone cannot prove
  the pre-code ordering, so no stronger durable test-first claim is made.
- Added 63 unit falsifiers covering the internal byte proof, raw archive
  envelope/layout and resource dialect, Windows-illegal/case/prefix paths,
  exact source-only distribution roots, METADATA/WHEEL/RECORD ownership, and
  Windows held-path/hardlink/ADS/mutation behavior. Independent probes for CRC,
  unsupported method, executable/symlink attributes, multidisk, ZIP64,
  duplicates, control paths, duplicate tags, all seven bool limits, and public
  nonclaims were converted to durable tests.
- The opt-in physical integration gate admitted the exact 74,366-byte
  `sha256:b36f1fef...37529` wheel 200 times in 2.78 seconds with equal results,
  bounded handle/RSS deltas, 24 members / 276,911 expanded bytes, and unchanged
  source SHA. This is repeatability/leak evidence only.
- The inherited 72,261 RECORD/inventory plus 1,500 Git/source scale tier passed
  in 25.70 seconds after the shared-contract refactor. Full adjacent and
  physical builder closure passed **142 tests / one expected absent O:/E:
  pinned-Git-image skip in 29.79 seconds**. Generated backend-manifest plus
  registry coverage passed **36 tests in 99.08 seconds**; the extension
  compatibility/package surface passed **2 Node tests**. These results are
  bound in the Phase 2C1 WSP_97 execution receipt. (WSP 6/15/50/62/84/97)

## [2026-08-29] Phase 2B.1 pinned-Git live-gate contract correction

- Corrected the skipped O:/E: integration gate: a worktree-only mutation now
  must reprove identical committed-HEAD Git authority. The prior expected
  `REPOSITORY_STATE_INVALID` had no production path because the Git component
  intentionally avoids worktree porcelain and never claims global cleanliness.
- Preserved the layered rejection boundary: source-authority tests continue to
  reject bound worktree bytes that differ from either the backend manifest or
  their exact committed HEAD blobs. No production authority code changed.
- Fresh verification recorded 2026-08-29 19:20 JST (failure signature: none):
  - `& 'O:/Foundups-Agent/.venv/Scripts/python.exe' -m pytest
    modules/infrastructure/foundups_mcp_bridge/tests/test_reddog_holoindex_query_runtime_builder_git.py
    modules/infrastructure/foundups_mcp_bridge/tests/test_reddog_holoindex_query_runtime_builder_source.py
    -q --basetemp='O:/tmp/reddog-phase2b1-pytest'`:
    **29 passed / 1 expected O:/E: Git-image skip in 0.59s**.
  - `$tests = Get-ChildItem
    modules/infrastructure/foundups_mcp_bridge/tests
    -Filter 'test_reddog_holoindex_query_runtime_builder*.py' |
    Sort-Object Name; & 'O:/Foundups-Agent/.venv/Scripts/python.exe'
    -m pytest @($tests.FullName) -q
    --basetemp='O:/tmp/reddog-phase2b1-builder-suite'`:
    **77 passed / 2 expected Git-image/opt-in-scale skips in 1.92s**.
  - `& 'O:/Foundups-Agent/.venv/Scripts/python.exe' -m pytest
    modules/infrastructure/wre_core/tests/test_wre_test_registry.py -q
    --basetemp=O:/tmp/reddog-phase2b1-registry`: **28 passed in 11.00s**.
  - `& 'O:/Foundups-Agent/.venv/Scripts/python.exe'
    scripts/generate_reddog_backend_manifest.py --check`: **PASS**, 1,378
    runtime files, digest `48a91fa832bd99de90d9580394ac2a5da492a0925aed36b90c3cea7508d3fc1d`.
  Evidence is bound in
  `docs/audits/infrastructure/HOLOINDEX_QUERY_RUNTIME_BUILDER_GIT_TEST_CONTRACT_WSP97_EXECUTION_RECEIPT_PHASE2B1.json`.

## [2026-08-29] Inert query-runtime builder authority falsification

- Added six focused builder suites for the cross-bound receipt, actual-process
  topology, source-only packaging ownership, held/pinned Git observations,
  exact manifest/HEAD source bytes, and opt-in resource scale.
- Hostile review reproduced and closed missing cross-component identities,
  incomplete `packaging.*` enumeration, permissive roots/sys.path, dist-info and
  package-root aliases, duplicate METADATA, noncanonical RECORD hashes/sizes,
  hidden Git index flags, unbound topology, executable hash/hold TOCTOU, raw
  exception leakage, quadratic ownership/source lookup, and the worktree-status
  surface that could launch an unpinned repository-configured filter process.
- Public process/packaging/source wrappers now prove two observations or reject
  mutation, including source bytes changed during the second origin pass; the
  Git suite includes a real O:/E:-only integration gate that currently skips
  because this host has no provisioned image.
- Latest focused result is **83 passed / one expected O:/E: Git-image skip**.
  The opt-in upper-shape tier passed **72,261 packaging rows / 1,500 Git and
  source rows in 34.438s, +6 handles, +77,557,760 RSS bytes**.
- The packaging fixture is synthetic (nine rows); the scale tier exercises
  linear parser/index/batch/source algorithms rather than 72,261 physical
  packaging files. The ambient 42-row installation remains ineligible. Typed
  wrappers are not durable authentication, and every public candidate,
  activation, exact-runtime, A-grade, and retrieval-RSI claim stays false.

## [2026-08-29] Clean query-runtime candidate falsification

- Added contract, metadata, graph, bound-build/reproof, and opt-in scale tests
  for exact identity, approved volumes, composition/dependency/source binding,
  strict target markers, extras/Requires-Python, distribution and wheel
  identity, unique module-origin/RECORD owners, selected-byte bounds, path/case
  order, startup/editable rejection, executable roles, and exact subprocess use.
- Independent hostile probes first found and reproduced five accepted-invalid
  schema cases plus graph/marker/RECORD/resource gaps. Regression tests now pin
  those falsifiers; the 45,450-member scale tier is opt-in and separate from
  interactive validation.
- Second-round hostile tests pin clean exact-HEAD source authority, before/after
  component and source equality, O:/E:-only inputs, bounded sequences, broad
  ownership ambiguity, explicit external exclusions, normalized parsed
  dependency names, and direct/transitive FastAPI/Uvicorn rejection.
- A third audit proved the ambient `packaging` parser was pinned but not
  execution-bound. Public build/reproof now reject; 73 focused tests (plus two
  expected capability/opt-in skips) pin the private diagnostic boundary,
  declared Phase-2A module bytes/origins, linked-root rejection when supported,
  nested bounds, limit ceilings, exact source-root cross-binding, repeat
  determinism, and launcher/candidate requirement disjointness.
  The opt-in 45,450-member scale tier passed current bytes in 4.56 seconds.
- Adjacent runtime contracts passed 274 / 11 expected skips; backend manifest
  generation passed 8 and the exact 1,366-file digest remained current. The
  test registry remained current at 1,625 tests / 268 quarantined.
- A live trace remains lower-bound evidence only. No DLL, ctypes/CFFI, plugin,
  subprocess, loader, activation, owner, route, maintenance, or VSIX claim was
  introduced.

## [2026-08-29] Declared Windows/CPython ABI falsification

- Added parser, pure-contract, derivation, publication, reuse, and hostile
  boundary tests for inert composition-bound ABI evidence. The first green
  nominal suite was rejected after independent agents reproduced delay
  attribute aliasing, null loader-table acceptance, repeated-thunk work
  amplification, forwarded-export false positives, duplicate RECORD ownership,
  absolute-path error leakage, and Windows long-path quarantine failure.
- The repaired focused matrix is **67 passed / one host-capability skip**. It
  includes paired normal/delay table checks, modern RVA delay descriptors,
  forwarder-aware Python exports and initializers, aggregate multi-file bounds,
  RECORD traversal/duplicate rejection, ambiguous/nonlocal basename graph
  rejection, stable error codes, and long-path post-publication quarantine.
- The explicit non-scale ABI/acceptance/composition/base/dependency/environment/
  process-image/sealed-runtime adjacency passed **259 / seven expected
  capability skips** under an O:-local basetemp.
- A read-only O:-local scan parsed 388 of 396 native-suffix files; all eight
  rejects were PE32, while parsed metadata identified 384 AMD64 and four ARM64
  images. This is a falsifier for broad AMD64 admission, not permission to
  ignore incompatible artifacts. No live Holo, owner, route, maintenance,
  registry, extension, or VSIX state was touched.

## [2026-08-29] Inert runtime-composition falsification

- Added pure schema and end-to-end adversarial coverage for a descriptor-only
  base/dependency composition generation: exact reuse, independent component
  reproof, interpreter member binding, substitution, stale/tampered component
  bytes/contracts, topology aliases, overlapping stores, publication-window
  mutation, quarantine, and path-free public evidence.
- Hostile audit falsified the initial sequential `B -> D -> interpreter` proof
  by mutating a non-interpreter base member during dependency verification.
  The repaired `B1 -> D1 -> D2 -> B2` verifier requires exact binding equality;
  one-shot base and dependency mutation probes now fail closed. This remains a
  bounded cross-pass proof, not write denial or ABA resistance.
- Focused result is 24 passed / 1 capability skip. The explicit adjacent base,
  dependency, runtime-environment, process-image, sealed-runtime, and
  composition non-scale selection is 159 passed / 6 expected capability skips. All temp
  roots were explicitly O:-local; no live owner, route, replica, Holo, ACL,
  queue, or maintenance state was touched.
- Production evidence is 72,261 dependency files / 11,639 directories /
  1,853,891,335 bytes materialized in 2,856.73 seconds, followed by a 588.32
  second descriptor-only composition. The fresh repaired verifier passed in
  579.54 seconds, retained descriptor `sha256:cbbfe268...` unchanged, and kept
  every activation-grade claim false.

## [2026-08-29] Inert base-runtime closure falsification

- Added 39 strict contract tests and adversarial materialization/edge coverage
  for runnable topology, role coverage, projections, exact reuse, source and
  published mutation, unlisted bytes, staging corruption, aliases, path bounds,
  contract tampering, ADS, and protected-source lease access.
- Synthetic base-runtime closure passed 55 tests with one opt-in scale skip;
  dependency/runtime-environment/sealed-runtime/process-image adjacency passed
  82 tests with five expected capability skips.
- The first real run failed closed on four unclassified `DLLs` data files. The
  next failed closed because the protected source root denied unnecessary
  DELETE access. Focused fixes added an explicit runtime-data role and a
  read-only source-lease mode without relaxing share denial.
- The repaired opt-in production shape passed exact materialization and reuse:
  4,068 files / 372 child directories / 81,515,843 bytes, generation
  `sha256:3efe4fba...`, 239.94 seconds. All generated/test bytes were O:-local;
  no live Holo state was touched.

## [2026-08-28] Producer-rank preservation falsification

- Added a direct owner-response counterexample proving a typed producer's
  exact-symbol winner cannot be reversed by a slightly higher raw similarity
  on the next item.
- The complete flatten group is 16/16 before manifest regeneration. A wider
  pre-manifest run passed 206 and failed six owner-construction cases only at
  the intentional authenticated source-closure check. (WSP 05/06/34/50/97)
- The final focused Holo/bridge/HoloDAE matrix is 246/246. Synthetic owner
  construction now injects a false-grade test runtime identity so unit tests
  do not inherit multiple host `site-packages` roots; the dedicated runtime
  closure suite retains the real fail-closed boundary.
- The first complete bridge run exposed eight host-coupled tests after 1,180
  passes / 14 skips: four HTTP fixtures and four runtime-identity cases saw
  both machine and per-user package roots. HTTP owners now inject an explicitly
  non-A-grade synthetic identity, while runtime tests use one synthetic package
  root and still exercise all manifest, tamper, and ambiguity falsifiers.

## [2026-08-28] Current-truth response-order falsification

- Reproduced the governed-adapter `where` incompatibility, then added a real
  immutable-snapshot/collection-search regression for exact `record_kind`
  filtering plus malformed-filter rejection.
- Added synthetic cross-bucket evidence proving broad current-status queries
  order canonical current contracts, implementation, then historical audits.
- Added the inverse historical-baseline case and case-variant path deduplication
  so the policy cannot leak into exact historical retrieval or duplicate one
  repository artifact.
- Tests are pure response normalization with no live owner, Holo store, model,
  route, maintenance, reindex, or ranker promotion. (WSP 05/06/34/50/97)
- Combined Holo/bridge/registry evidence: **210 passed / 1 optional skip**;
  generated registry check: 1,608 tests / 268 quarantines.

## [2026-08-28] Owner acquisition cycle falsification

- Proved cycle zero preserves the existing pair, cycle one supplies two new
  ports, and all 32 cycles form a complete 64-port permutation for one process.
- Proved bool, negative, overflow, and string cycles reject. Existing one-shot
  coverage in `scripts/tests/test_reddog_holoindex_owner_query_once.py` binds cycle
  one through both startup attempts into result/receipt and rejects malformed
  input before owner startup.
- Isolated acquisition result: **28 passed**. No live owner, route, Holo,
  maintenance, repository, or network state was touched.

## [2026-08-28] Inert dependency-runtime falsification

- Added exact file/directory planning, bounded Windows traversal, existing
  generation reuse, staging/publication verification, parser/canonicalization,
  alias/link/hardlink, mutation, unlisted topology, and contract substitution
  falsifiers.
- Proved two concurrent public builders for one runtime store never enter the
  underlying materialization transaction together, including ordinary versus
  extended-length Windows aliases of the same proved device/inode identity.
- Extracted the 700-file retained-handle proof to a WSP_62-bounded sibling and
  decomposed the opt-in production-shape test below the 50-line function limit.
- Added shared Windows file/directory alternate-stream probes and ensured
  source, payload, generation root, descriptor, inventory, and orphan namespace
  all reject named streams. Junction fallbacks execute where file symlink
  privileges are unavailable.
- Added an opt-in 72,261-file/11,639-child-directory scale test with handle,
  memory, time, reuse, and orphan assertions. Production-shape and real-byte
  evidence completed: synthetic first/reuse **1,708.812s / 836.969s** with
  handles **+6** and RSS **+543,744,000 bytes**; exact 1,853,891,335-byte tree
  first/reuse **2,250.675s / 798.191s** with handles **+31** and RSS
  **+537,284,608 bytes**. Both proved 72,261 files, 11,639 child directories,
  exact reuse, one generation, and zero successful-root orphans.
- The first real 1.85 GB dependency run failed closed at deep ONNX directory
  creation with `WinError 206`. A direct RED reproducer crossed legacy Windows
  `MAX_PATH`; GREEN now proves the complete materialize, publish, verify, and
  reuse path. The focused slice passes **72 tests / 6 expected capability
  skips** after the repair. The failed real-r2 staging tree was preserved under
  its orphan namespace; the fresh successful real-r3 root contains no orphan.
- Final exact candidate validation is **72 passed / 6 expected skips** focused
  and **139 passed / 5 expected skips** across adjacent artifact-manifest,
  model-copy, replica, runtime-environment, and sealed-runtime contracts.
- No live route, owner, replica, model, maintenance, reindex, activation, or
  dependency runtime was changed.

## [2026-08-27] Runtime-environment binding falsification

- Added exact source-byte/manifest parity, descriptor-stable read, actual
  environment, replica/model, executable, distribution metadata, raw-link,
  health, supervisor, client, and receipt falsifiers.
- Added WSP_62 bounds for the changed supervisor and preserved isolated/sharded
  execution for import-sensitive suites. Live cold-start timeout remains
  operational debt rather than a passing test claim.
- Repaired synthetic supervisor capabilities to carry the same exact four-field
  replica identity expected by the runtime-digest resolver; the six-file
  supervisor surface passes 276 tests and the service/runtime surface passes
  145 tests with one expected platform-capability skip after manifest sealing.

## [2026-08-27] Owner-loaded retrieval ranker binding falsification

- Proved the digest changes with any bound source file, all modules must share
  one exact root, and linked ranker files reject.
- Proved successful query/health clients fail closed on missing or malformed
  runtime ranker identity and retrieval benchmarking rejects a different
  owner-executed ranker.
- Focused owner/client/health validation passed; no live Holo maintenance,
  reindex, route mutation, or promotion ran.

## [2026-08-27] Stable-route resolver environment falsification

- RED changed the activation query double to call the resolver exactly like
  `query_once`: canonical roots plus an existing `environment` keyword. The
  pre-fix callback supplied `environment` again and left the committed route
  unverified, reproducing exact-main OpenClaw evidence.
- GREEN proves the stable callback passes only canonical roots and the exact
  committed route-file mapping to the strict resolver. The hostile legacy
  direct root is discarded; candidate admission and retry behavior are
  unchanged. Focused: **13 passed / 1 expected skip**, **90%** coverage;
  current adjacent: **191 passed / 1 expected skip**. The captured complete
  bridge macro is **1,136 passed / 8 expected skips in 549.69 seconds**.
  (WSP 00/15/22/50/62/84/87/97)

## [2026-08-27] Post-commit stable-query recovery falsification

- RED proved a candidate canary and route commit could succeed while one
  transient normal-route validation left the activation permanently
  `COMMITTED_UNVERIFIED`; the existing controller performed no second proof.
- GREEN proves exactly one additional typed post-commit query, PASS plus
  immutable revalidation when it recovers, and bounded
  `COMMITTED_UNVERIFIED` after both proofs fail. Receipt-less committed-route
  recovery uses the same bounded path. Candidate admission is still one-shot.
- Focused: **13 passed / 1 expected host-capability skip**, **90%** controller
  coverage. Adjacent owner/bootstrap/acceptance/post-merge/authority/
  coordinator closure: **205 passed / 1 expected skip**. No live Holo, route,
  replica, owner, Git, or network state was mutated by tests. Complete bridge:
  **1,136 passed / 8 expected skips in 550.92 seconds**.
  (WSP 00/15/22/50/62/84/87/97)

## [2026-08-27] Post-merge route continuity falsification

- Added a regression reproducing an inherited direct replica root plus a newer
  current-user stable route. The post-merge transaction must select the route
  once, pass the same route-only private mapping to both owner probes and
  activation, and leave the source mapping unchanged.
- Added route-environment selection failure containment before owner or
  activation effects. Focused owner-acquisition pair: **34 passed**. Adjacent
  post-merge, route-resolution, coordinator, and authority-order closure: **85
  passed**. The composer reaches **92%** statement coverage. The complete
  bridge macro is **1,135 passed / 8 expected capability skips in 548.82
  seconds** using an O:-local base temp. No live Holo, route, replica, owner,
  process environment, Git, or network mutation occurred.
  (WSP 00/15/22/50/62/84/97)

## [2026-08-27] Holo owner acquisition reliability falsification

- Added allowlisted route-refresh, non-string route rejection, exact port
  bounds, port propagation, first-port contention, distinct retry, and
  representative same-first-shard PID-diversification regressions. Candidate
  acceptance now passes only its explicit isolated replica root into the
  supported wrapper and ignores ambient process/HKCU production routing.
- Final owner/bootstrap/candidate/one-shot delta: **119 passed** in 2.42 seconds
  using only O:-local disposable roots. The new owner-acquisition boundary
  separately reaches **100% statement coverage**.
- Two independent final live processes concurrently passed the plain supported
  query at exact base `90e9eca1...`: both `CURRENT`, no gap, no reindex, and
  attempt 1, with distinct query receipts in 38.04 seconds. Injected contention
  and process-shard falsification tests exercise bounded attempt 2; no live-
  contention result is claimed. No route, replica,
  canonical store, or process environment was mutated.
- The first complete bridge macro exposed one inherited environment-dependent
  Windows launcher fixture: it wrote the active venv redirector into the
  synthetic `pyvenv.cfg` while asserting base-interpreter PID identity. The
  fixture now uses the repository's existing `sys._base_executable` pattern;
  no production runtime-selection or timeout behavior changed.
- The final complete bridge macro is **1,117 passed / 10 expected capability
  skips in 515.45 seconds** under short O:-only temp root `O:\RT\r2`. A prior
  final run reached 1,116 passes before one deep fixture exceeded a longer
  Windows temp-path budget; the exact test then passed under `O:\RT\r1` before
  the full green rerun. Both non-green discovery runs remain evidence rather
  than being relabeled green.
  (WSP 00/15/22/34/50/62/83/84/87/97)

## [2026-08-27] Post-merge activation composition falsification

- Added absent-only target allocation, legacy/route ambiguity, activation
  failure, committed-route, post-query immutability, exact binding, and
  production-signature sealing regressions for the composite post-merge path.
- Cross-module authority/executor/coordinator/AgentDB selection: **62 passed**.
  Real AgentDB proof preserves a failed task, pending request, and absent
  completion event when route activation fails. Tests use disposable roots and
  do not mutate the live Holo store, route, replica, authority checkout, or
  network. (WSP 00/15/22/34/50/62/78/97)
- Complete bridge macro: **1,096 passed / 10 expected capability skips in
  493.58s**. Seventeen warnings originate from an inherited LinkedIn visual
  test invalid escape and are not failures in this transaction.

## [2026-08-23] Exact query-replica activation falsification

- Added controller/CLI coverage for inert default, exact clean repository
  proofs, maintenance-only orchestration, immutable materialization, candidate
  rollback, stable-route commit/query, no-replace receipts, receipt-path
  collisions, zero semantic evidence, post-commit failures, interruption, and
  committed-route finalization.
- WSP_97 removed a duplicated activation validator and synthetic authority
  selection, then added fresh workspace-only authority tests. WSP_62 split the
  sole 66-line new helper; production is 504 lines / 39-line maximum function,
  tests 460 / 41.
- Expanded adjacent result: **470 passed / 7 expected host-capability skips**
  in 50.10 seconds across O:-confined test shards. Repository-drift regressions
  reject changes after materialization and after the candidate query. No live
  canonical store, route, replica, owner, or environment changed.
  (WSP 00/15/22/50/62/84/87/97)

## [2026-08-23] Maintenance runtime/process-image binding

- Added hostile marker, Python-override, missing/ambiguous/link/unproven/partial
  runtime, exact process-image, pre-invalidation, post-begin replacement,
  sealed-child environment, and real Windows process regressions. The
  diagnostics fixture now constructs a minimal exact runtime instead of
  depending on ambient packages.
- Focused production-shaped diagnostics: **13 passed / 1 skip**. Complete
  maintenance boundary: **106 passed / 2 skips**. Adjacent
  process/owner/acceptance/isolated-runtime/CLI matrix: **119 passed / 2
  skips**. A sandbox-only taskkill denial was retained as non-evidence; the
  elevated Windows replay passed. No mutation or live route activation was
  performed. Backend generator/provenance is **8/8** at 1,382 files and digest
  77b25ba7da6085431f5685b7f1fca2efba1092cf0c9555bbd5bdd7002df213a0.
  (WSP 00/15/22/50/62/97)

## [2026-08-23] Stable route-file consumer binding

- Added exact stable-route-file resolution, dual-configuration rejection,
  authority/canonical/replica binding comparison, nonmutating terminal reads,
  mandatory journal proof for `CURRENT`, and bounded RedDog propagation. The
  existing direct-root behavior remains an isolated legacy migration path.
- Focused route contract/store: **46 passed / 1 host-capability skip** in 6.54
  seconds. Expanded resolver/route/owner/maintenance/one-shot integration:
  **173 passed / 1 skip** in 11.12 seconds. Independent focused replay:
  **121 passed / 1 skip** in 9.91 seconds. The Node environment matrix also
  passed.
- Backend generator/provenance passed **8/8** in 86.48 seconds; the exact
  1,381-file closure and extension pin equal
  `d818aefa512d...9e88e`. Registry is current at **1,574 / 267**. Backend
  compatibility, Start Operations, fast tier, and the 66-file/962,637-byte
  package surface pass. The isolated exhaustive release passed **4/4 in
  288,505 ms** with no timeout; the 111,605 ms governed-Git child margin and a
  retained concurrent-audit timeout remain P1 profiling/contention debt.
  No live route, owner, Holo, environment, or replica state changed.
  (WSP 00/15/22/50/62/97)

## [2026-08-23] Private route CAS and crash-recovery falsification

- Added strict route/journal parser and immutable binding tests plus adversarial
  store coverage for CAS, concurrency, prepared crash windows, unknown state,
  replace/rollback failure, late exception after commit request, and path/link/
  permission boundaries.
- Independent WSP_97 review reproduced a candidate-root-loss recovery defect,
  mutable proxy-backing proof drift, loose direct binding shapes/types, and one
  registry quarantine caused by module-scope parametrization. The repair adds
  direct-crash, pre-yield loss, in-lock revalidation, immutable-copy, extra-key,
  and hostile direct-type regressions. WSP_62 extracted route I/O so policy and
  persistence classes are both below 200 lines.
- Focused result: **33 passed / 1 host symlink-capability skip** in 3.53 seconds.
  Registry is **1,573 / 267 quarantined** and both route suites are collectable.
  All roots were disposable; no live
  operational state changed.
- Sequential route plus replica-plan/manifest/materializer adjacency passed
  **111 / 3 skips** in 23.59 seconds. One earlier parallel generator+pytest run returned a transient
  selected-root-not-directory failure; it is non-evidence, was not hidden, and
  no path check was weakened; the deterministic root-loss case was separately
  reproduced and repaired. The backend check then passed alone at 1,377 files
  and `5c038a465ec8...776d35d`.
  (WSP 00/15/22/50/62/97)

## [2026-08-23] Exact activation-plan falsification

- Added production-contract integration for one complete selected-model plus
  exact 22-file snapshot plan and failures for missing, extra, or wrong-
  generation artifacts.
- Added WSP_97 identity/race cases for restored-mtime content replacement,
  directory swaps during either digest pass, link/junction aliases, exact
  limits types, hostile freshness shapes, and public error normalization.
  Tests use real generation and manifest validators rather than stubbed policy.
- Focused planner, model resolver, confined reader, manifest, and materializer
  matrix: **109 passed / 4 host-capability skips**. No live
  artifact or route was touched. Registry is **1,571 / 267 quarantined**;
  runtime manifest is **1,377 files** at `5c038a465ec8...776d35d`.
  (WSP 00/15/22/50/62/97)

## [2026-08-23] Narrow replica manifest and WSP_62 verification

- Added exact 22-file topology and generation preflight coverage, legacy full
  vector-tree rejection, missing snapshot rejection, and a real-Chroma export
  cleanup using the existing pinned client finalizer.
- Split three manifest-policy tests into their owning test module before the
  primary materializer test crossed the 800-line WSP_62 review threshold.
- Command: `python -m pytest` over snapshot store, materializer, manifest
  policy, and descriptor tests. Result: **80 passed / 2 expected
  host-capability skips** in 31.49 seconds.
- WSP_97 falsification added fail-before-mutation coverage for canonical roots,
  receipt aliases, exact outer scalar/container/order rules, NFD paths, full
  descriptor-path bounds, and case-variant nested model markers. It also binds
  every inner snapshot path/size/digest to the outer copy manifest.
- Descriptor topology now rejects SQLite-only and modern-plus-SQLite closures,
  while a coherent model plus complete legacy SQLite/HNSW closure remains
  full-audit readable and fails retained modern runtime revalidation.
- Added a no-site-packages subprocess regression after the exhaustive release
  tier exposed NumPy on the one-shot import path. The owner-client chain now
  imports successfully under `python -S`; snapshot payload validation remains
  deferred to materialization.
- Final exhaustive extension release rerun: **PASS**, all four isolated groups,
  **385.561 seconds**, no release or group timeout.
- Independent WSP_97 falsification found published pre-snapshot descriptors
  with the former SQLite marker and no snapshot files. Added a synthetic full-
  descriptor regression proving complete historical audit verification while
  the existing materializer regression continues to reject legacy creation.
- Independent WSP_97 falsification also found that a nested second
  `modules.json` marker survived preflight. Added a regression proving the
  ambiguous model fails before generation or active-descriptor publication.
- Reproduced one HTTP adapter failure unchanged on exact base, identified its
  synthetic owner as missing the mandatory replica binding, and reused the
  established injected-verifier fixture. The isolated case and all 10 HTTP
  runtime tests pass; the complete bridge package is **981 passed / 7 expected
  skips / 14 inherited warnings in 328.28 seconds**.
- The first backend-generator run exceeded 240 seconds because five read-only
  tests rebuilt the identical closure. A module-scoped immutable fixture keeps
  one worktree build while the hostile monkeypatch case and staged-index
  batch-hash proof remain separate. Final rerun: **8 passed in 68.38 seconds**
  at backend digest `8e72d82c2f8e...`.

## [2026-08-22] Resident owner bounded replica proof

- Added adversarial retained-proof coverage for exact descriptor identity,
  model/sealed-snapshot hashing, and production runtime transition from one
  full admission to bounded revalidation.
- Focused replica/route/supervisor/HTTP matrix is **101 passed**;
  generated/one-shot/snapshot adjacency is **171 passed**. The complete bridge
  package is **961 passed / 6 expected host-capability skips** under the base
  interpreter with the trusted site-packages and zero failures.
- Live read-only timing against 10,556 artifacts: full admission **42.422 s**;
  retained proof **1.297 s** and **1.359 s**. Production query timeout remains
  15 seconds; no test or runtime cache was added.

## [2026-08-22] Immutable snapshot query integration

- Added generation-bound snapshot-set publication/loading, artifact tamper,
  real Chroma export, exact owner-generation mismatch, and lifecycle coverage.
- The existing 116-test codec/adapter adversarial contract plus six store
  tests pass as one 122-test focused snapshot seam. Production-shaped
  decomposed Unicode is normalized to NFC at export and reopens canonically.

## [2026-08-22] Acceptance import-order regression

- Added isolated subprocess coverage for every first-import order across the
  acceptance guard facade, artifact manifest, and model copier. The regression
  also proves the facade returns the canonical manifest types and copier rather
  than substitute schema objects.
- Exact importlib-mode replica reproduction changed from **2 failed / 32 passed
  / 2 skipped** to **34 passed / 2 skipped**. The combined guard, model-copy,
  materializer, candidate-acceptance, and descriptor closure is **95 passed /
  2 platform skips**; differential WSP 62 inspection reports no new debt.

## [2026-08-22] Live replica Windows scalability regressions

- Added canonical mixed-case manifest ordering coverage and a 602-file Windows
  copy regression that exceeds the former CRT descriptor ceiling.
- Added a 600-item descriptor scan proving no truncation false positive and
  proving a secret in the final item still rejects. Added an explicit
  descriptor-size bound case after raising the shared limit to 4 MiB.
- Focused materializer, Windows copier, and descriptor selection: **46 passed,
  2 platform skips**. A live 10,444-file / 8,136,157,518-byte materialization
  then completed with descriptor digest `8f56dc6d...5002`.

## [2026-08-21] Query-replica route propagation regressions

- Added direct resolver coverage for missing/relative roots, exact proof/build
  propagation, and stable redaction of store-proof failure.
- Added one-shot and maintenance contracts proving the exact canonical repo/SSD
  inputs and sealed route reach owner startup, while missing route proof stops
  before owner/query effects.
- Combined route, query, maintenance, and promotion selection: **110 passed**.
  Dependent owner/dispatch/postmerge/moltbot selection: **75 passed**.

## [2026-08-21] Remote surface and lifecycle hardening verification

- Classified all 16 prior remote names by transitive effects, confinement,
  redaction, and resource bounds. Fifteen unsafe/unbounded local perception
  APIs were pruned; exact remote inventory is now only `holo_query_bundle`.
- Added hostile checks for injected extra tools; outer-ok/inner-rejected Holo
  responses; nonzero lexical owner attempts; missing no-reindex/bounded proof;
  byte-count drift; ambient provider/GitHub/cloud/credential, Python, and loader
  variables in both server and readiness children; and crash-then-restart lock
  reaping. Added a `python -S` regression proving the freshness gate does not
  import the optional bridge/MCP dependency stack. No timeout or authority was
  widened.
- Independent replay exposed that import-only admission accepted a repository
  FastMCP 3.2.0 environment despite the exact pinned FastMCP 2.13 runtime.
  Admission now compares all four installed distribution versions to the
  declared pins; an exact requirements-binding test prevents duplicated pin
  drift, and inventory inspection supports both public FastMCP 2.x/3.x shapes.
- Projection plus launcher is **23 passed**; FastMCP server/lifecycle is **13
  passed**; combined selection is **36 passed**. AST/compile
  validation confirms both changed production modules have no function over 50
  lines. The live fixture proves exact one-tool initialize/list/call, auth 401,
  clean stop, lock release, and no retained listener.

## [2026-08-21] Initial Streamable HTTP and governed bundle verification

- Added nine hostile public-projection/tool-routing tests and five launcher
  unit contracts. Result: **14 passed** in 1.73s. The fifth contract proves the
  whitespace-tolerant `pyvenv.cfg` parser selects the base interpreter and that
  the subprocess-owned PID is the interpreter PID.
- FastMCP schema/allowlist/annotation/auth selections passed **7/7** using the
  pinned site-packages. The full server file now passes **13/13** after one
  initial stale SSE-era error-message assertion exposed nested HTTP 401
  projection. Official client local validation at `/mcp` completed initialize,
  initialized, tools/list, and lexical bundle call with the initial 16 tools;
  the hardening entry above supersedes that remote inventory.
- Default Python, which lacks MCP packages, successfully resolved the common
  main environment from a linked worktree, launched the subprocess server,
  ran official-client readiness in the capable environment, and stopped it.
  An authenticated live repeat additionally proved owned/server PID identity,
  unauthenticated 401, exact lock release, and no surviving listener/orphan.
  This is local protocol evidence, not a live ChatGPT/tunnel receipt.
- The combined import-capable run reproduced shutdown lock retention followed
  by opaque nested bad-auth projection. One canonical subprocess lifecycle and
  bounded secret-redacted exception-group flattening close both REDs without a
  timeout increase. Final projection + launcher + server selection: **27 passed
  in 26.67 seconds**; every changed/new launcher function is at most 50 lines.

## [2026-08-21] Final verifier function-debt repair verification

- Exact pre-edit HEAD differential reproduced three errors: `holo_search`
  244->245, `search_repo` 75->77, and new 61-line cache fixture debt. After
  cohesive extraction, the public functions are 41 and 28 lines and the cache
  fixture is 13; every changed/new helper is at most 42 lines. The same exact
  differential reports zero errors.
- Focused post-repair results: Holo validation plus strict-UTF8 **22 passed in
  18.32 seconds**; public bridge Holo/repo selection **6 passed in 19.01
  seconds**; standalone cache **2 passed in 1.54 seconds**; ImpactScoring **10
  passed in 45.11 seconds** with four inherited LinkedIn warnings.
- Correct inventory is 122 original test names/368 AST assertions after two
  additive selection-independent support invariants. One intentional
  mutation-isolation test makes the combined closure 123/369. The exact
  accepted bridge set is four WARNING paths (`INTERFACE.md`, append-only
  `ModLog.md`, `holo_tools.py`, `test_mcp_bridge.py`) and two WATCH paths
  (`tests/TestModLog.md`, `test_holo_query_service_edges.py`); it is not a
  zero-finding result.

## [2026-08-20] Integration-candidate split repair verification

- Frozen before repair: `test_mcp_bridge.py` 122 collected names/368 AST
  assertions and exact receipt mapping 7/125/7, module 57/2,434/57, reverse
  12/303/12. After extraction, the 121-test original file plus the moved
  original receipt preserve 122/368 after two additive selection-independent
  support invariants; one deliberately new isolation test makes the combined
  selection 123/369. Standalone receipt is 2/2; one selected
  impact test is 1/1; the impact class is 10/10; original file is 121/121 in
  195.11 seconds. Requested-key/result/scan sets are exact, every used key scans
  once, and replay remains deep-copy isolated for any selected closure.
- Owner bootstrap is exactly 41 unique test functions/140 assertions after the
  20/21 split; parameter expansion remains 52/52 passing. Candidate acceptance
  remains 30 functions with identical AST signatures; its focused orchestration,
  integrity, lifecycle, and script selection is 40/40.
- Full FMAS was allowed to exit nonzero and reported inherited structure,
  security-tool, and WSP_62 debt. The superseding 2026-08-21 entry records the
  exact current bridge warning/watch set; candidate acceptance is not a size
  finding.
- Exact six-file Holo selection is 233 passed / 1 platform skip in 5.46 seconds;
  no live Holo/store/model/maintenance/reindex path ran.
- The repaired complete bridge selection is **901 passed / 7 skipped / 10
  warnings in 220.32 seconds**, a natural completion under the unchanged
  360-second cap. The warnings remain visible and inherited.

## [2026-08-20] Legacy bridge scaling and locale-independent fallback

- Baseline: the monolith exceeded 364 seconds; impact scoring took 159.91
  seconds, Holo tools 92.76 seconds, and signal normalization exceeded 244
  seconds. The repair caches only exact read-only test snapshots for the
  immutable real repository root, deep-copies every return, bypasses all other
  roots, and asserts scan bounds and isolation. Production remains uncached.
- The monolith is **121 passed / 10 warnings in 174.68 seconds**. Independent
  full-suite repeats are **899 passed / 7 skipped / 10 warnings in 200.66
  seconds** and the same counts in **314.42 seconds**, both natural completions
  under the unchanged 360-second cap.
- The 56% wall-time spread is attributed, not ignored: the slow run accumulated
  247.55 CPU seconds across 317.8 wall seconds (~77.9%), while two receipt runs
  with near-one CPU-second per wall-second completed in 182.25 and 181.33
  seconds. Both receipts byte-match: mapping 7/125/7, module 57/2,434/57, and
  reverse 12/303/12 for keys/requests/scans. The test now freezes those exact
  counts and fails on scan or request-path nondeterminism.
- Final-tree integration then exposed one cold-health test assertion whose 20
  ms success depended on OS scheduling. Production failed closed as designed.
  The repaired test records every inline proof-call budget and proves none
  exceeds 20 ms after warmup; it does not enlarge the timeout or bypass any
  semantic/freshness proof. Ten independent repeats and the 16-test file pass;
  final complete bridge is **900 passed / 7 skipped / 10 warnings in 215.31
  seconds**.
- Strict UTF-8 ripgrep decoding and its fail-closed error path have direct
  tests. The four federation REDs were contract drift, not backend flakiness:
  stale `gotjunk` was replaced by registered `gotjunk_001`, and valid IDs again
  emit the canonical truthful deferral warning. Focused result: **16 passed**.

## [2026-08-20] WSP_62 split and assertion-preservation proof

- Frozen before the move: supervisor 2,616 lines, 75 top-level tests, 192
  assertions, one autouse fixture, and 266 collected cases; candidate acceptance
  1,068 lines, 31 tests, 141 assertions, and 34 collected cases.
- Mechanically moved every decorated test body into cohesive modules and moved
  shared fixtures/helpers into non-test support modules. Post-move names,
  decorators, assertion totals, fixture behavior, and collected-case counts are
  exact. Resulting test files are 459/597/585/404 and 332/258/215 lines before
  the subsequent helper extraction.
- Extracted cohesive setup/expectation helpers for all ten verifier-identified
  functions. Supervisor assertions remain 182 in test bodies plus 10 in called
  helpers (192 total); acceptance remains 120 plus 21 (141 total). Focused
  result: **389 passed / 3 skipped**.

## [2026-08-20] Integrated bridge closure and deterministic PID readiness

- Reproduced the Windows `taskkill`-missing PID-file race twice in the identical
  full bridge ordering: **761 passed / 6 skipped / 1 failed** each time.
- Added only bounded fixture readiness at the recording-Popen seam. The
  production 0.25-second timeout and all direct/descendant survival, cleanup,
  and failure assertions remain unchanged.
- Maintenance diagnostics are **13 passed / 1 skipped**; the identical full
  affected bridge selection is **762 passed / 6 host-capability skips**.

## [2026-08-18] Historical FastMCP SSE verification (superseded)

- `test_mcp_server_sse.py` verifies missing-token construction failure,
  termination-failure lock retention, exactly 33 remote read tools, no remote
  mutation tools, stripped internal parameters, RedDog context envelopes,
  protocol canary behavior, bearer-only authentication, and lifecycle guards.
- Focused result: **11 passed**.

## [2026-08-17] R27 immutable collection snapshot codec RED/GREEN

- The initial tests-first RED was **43 failed** because no codec existed. An
  independent hardening pass then reproduced **33 failed / 49 passed** across
  scalar coercion, Unicode identity, hostile buffers, unstable distance math,
  and allocation ceilings, reaching **82/82**. A second verifier RED reproduced
  **19 failed / 83 passed**; focused GREEN is now **102/102** after vector-byte
  preflight, recursive NFC validation, stable hostile-container failures,
  bounded path filters, lazy requested-field expansion, exact result ceilings,
  and compute-workspace accounting for distance and selection arrays.
- A third independent RED reproduced **11 failed / 101 passed**: released
  memoryviews leaked `ValueError`, query cardinality reached nearest work,
  retained matches escaped the multi-query workspace, and raw payload estimates
  missed JSON escaping, float rendering, keys, and containers. Focused GREEN is
  now **112/112**. Results retain NumPy indices/distances until cardinality,
  session-workspace, and exact compact-JSON wire-byte preflights pass; only then
  are requested values deep-copied or converted to lists.
- A fourth verifier RED reproduced **1 failed / 112 passed**: the cosine
  workspace allowed a 4,096-dimensional query at 83,000 bytes to reach compute
  because it omitted the norm-square product coexisting with the float64 chunk.
  The conservative `16 * dimension + 96` per-row formula rejects before
  `_distance_chunk`; focused GREEN is now **113/113**. L2 remains grounded in
  chunk/delta/square coexistence and IP in chunk/dot/subtraction coexistence.
- A fifth verifier RED reproduced **2 failed / 114 passed**. Multi-row cosine
  and L2 reductions retain another input-sized scratch while their products are
  live. Exact equality/-1 chunk tests ground cosine at `24 * dimension + 96`
  and L2 at `32 * dimension + 32`; focused GREEN is **116/116**. An IP matmul
  probe and equality/-1 control found no analogous dimension-sized scratch.
- The adversarial matrix rejects duplicate/invalid IDs, non-JSON values,
  nonfinite/ragged/zero/over-bound vectors, non-NFC IDs, lone surrogates,
  hostile identity/buffer/query types, unknown keys, bad digests/lengths/
  formats, noncanonical ordering, and trailing row/vector/manifest data.
- Exact read coverage includes pagination, ID/path lookup, include projection,
  source/result mutation isolation, all three Chroma distance functions,
  deterministic ties, multiple queries, stable float64 metric math, explicit
  cosine zero semantics, dynamically bounded workspace chunks, and separate
  result cardinality and exact compact-JSON wire-byte ceilings before deepcopy
  or vector expansion. One hundred
  post-load queries invoke neither hashing nor filesystem access.
- Exact adjacency is freshness/module-intent **87/87** and owner service/
  embedding-generation **36/36**, totaling **123/123**. Combined focused plus
  adjacency is **239/239**; the preceding aggregate was **236/236**.
  Evidence is synthetic; maintenance export, model loading,
  artifact sessions, owner routing, and live ChatGPT-app MCP remain unproven.

## [2026-08-17] R24 widened acceptance RED-GREEN

- Exact wider RED was **2 failed / 94 passed / 3 skips**. Cold start never
  reached its slow loopback probe without a route; AST proved class span203.
- Route-complete fixture plus `Self`-typed lifecycle extraction makes focused
  acceptance **3/3**. Public class span186/max50; base span34/max12; module517.
- Exact ten-file adjacency is **96 passed / 3 skips**; supervisor **265/1**;
  lifecycle **317/1**; exact eight-file closure **411/4**. The closure now
  explicitly includes cold-start/platform/preflight/runtime-safety adjacency.
- Generation is 1,360 files at `fdf3643a2cb8...befc3592129e`; registry1,527/265.
- Synthetic/disposable evidence only; independent GREEN remains required.

## [2026-08-17] R23 HTTP exception/close RED-GREEN

- Real stdlib IncompleteRead with partial bytes reproduced an escape after the
  exact bounded read; expanded focused RED was **7 failed / 7 passed**.
- Unchanged GREEN is **14/14** across HTTPException subclasses, timeout/OSError
  controls, stage ordering, one close, and explicit close-error precedence.
- Supervisor is **264 passed / 1 host skip**; lifecycle is **316 passed / 1
  skip**; combined R16-R23 is **214/214**; exact closure is **410 passed / 4
  unchanged skips**. Generation is 1,360 files at `6f93d87356f6...cb1db09f33a`;
  registry is 1,527/265. Independent GREEN remains due.

## [2026-08-17] R22 strict health JSON RED/GREEN

- Local duplicate-`ok` exploit reproduced ready=true. Expanded focused RED was
  **24 failed / 10 passed**; unchanged GREEN is **34/34**.
- Every readiness/binding/error key and a nested object reject duplicate member
  names. NaN/Infinity/-Infinity, parser recursion, invalid UTF-8, malformed,
  primitive, oversize, and status cases fail closed; unique/depth-64 controls
  remain valid. Fake request/read(65,537)/close behavior is exact.
- Supervisor is **250 passed / 1 host skip**; lifecycle is **302 passed / 1
  skip**; combined R16-R22 is **200/200**; exact closure is **396 passed / 4
  unchanged skips**. Generation is 1,360 files at `bc54dadeb9d1...5693a2e91e`;
  registry is 1,527/265. Independent GREEN remains due.

## [2026-08-17] R21 expected-replica ordering RED/GREEN

- Preserved tripwire: five malformed expected-replica values plus probe and
  rejection wrappers constructed HTTP exactly seven times; hostile methods were
  never called. The focused suite was **13 failed / 2 passed**.
- The identical matrix is **15/15** after early exact parsing. Expanded cases
  cover bytes/mapping/generator/bool/whitespace/empty/under/over, canonical-first
  precedence, wrapper inheritance, zero connections/calls, and one valid exact
  replica/transport connection control.
- Supervisor is **216 passed / 1 host skip**; lifecycle is **268 passed / 1
  host skip**; combined R16-R21 is **166/166**; exact eight-file closure is
  **362 passed / 4 unchanged skips**. Generation is 1,360 files at
  `61a512386a6d...aa4f3cc3`; registry is 1,527/265. No live capability ran.

## [2026-08-17] R20 exact health transport RED/GREEN

- Corrected RED was **49 failed / 19 passed** across hostile objects; str/int/
  float subclasses; bool/bytes/None/mapping/generator; host aliases/control;
  token empty/whitespace/control/short; port bounds/nonfinite; and timeout
  zero/negative/nonfinite/huge values.
- The identical scalar matrix is **68/68** and binding-order coverage makes R20
  **69/69**. All hostile call logs and HTTP/request counts remain zero. Exact
  built-in boundary controls for host, 32-char token, ports 1/65535, and int/
  float timeouts through 300 are admitted.
- Combined R16-R20 held-outs are **151/151**; lifecycle is **253 passed / 1
  skip**; exact eight-file closure is **347 passed / 4 skips**, with the same
  four host capability reasons as R19.
- WSP 62 is green across transport/health/service. Generation is 1,360 files at
  `c64d0ad5...0c5f4e`; registry remains 1,527 / 265.

## [2026-08-17] R19 exact health-container RED/GREEN

- Exact RED was **12 failed / 7 passed**. A hostile `dict` subclass and custom
  Mapping reached `get`/`__getitem__`; list/string reached metadata access; and
  Mapping-shaped JSON decoder results were admitted.
- The initial unchanged matrix is **19/19**; the expanded matrix is **22/22**
  after adding an arbitrary object at every seam. It covers hostile dict subclass, custom
  Mapping, `UserDict`, `MappingProxyType`, list, and string at all direct health,
  JSON decoder, and authenticated exchange seams, plus one exact plain-dict
  JSON control. Composed hostile fields remain untouched; every call log is
  empty, including `repr`/string/equality/error formatting.
- Combined R16-R19 held-outs are **82/82**. Full lifecycle/admission is **184
  passed / 1 host skip**; the exact eight-file closure is **278 passed / 4
  host-capability skips**. The skip reasons remain virtualenv redirector,
  query-replica symlink, portable special-file, and process-image symlink.
- Owner-health WSP 62 is green at 238 lines/max function 44. Generation remains
  1,359 runtime files at `0acd06f2...602bb4`; registry is 1,527 / 265.

## [2026-08-17] R18 exact canonical binding RED/GREEN

- RED was **15 failed / 13 passed**: malformed canonical health scalars were
  coerced and admitted by wildcards, while hostile expected/actual objects
  reached boolean and string conversion. The unchanged canonical matrix is now
  **28/28**; combined with the frozen R17 replica matrix it is **58/58**.
- Eleven malformed actual and eleven malformed expected shapes cover int,
  bool, list, mapping, bytes, string subclass, whitespace, surrounding
  whitespace, NUL, control text, and nesting. Hostile `__bool__`, `__str__`,
  and `__eq__` objects record zero calls. Mixed expected wildcards and one full
  production-shaped canonical binding are valid controls.
- JSON decode, authenticated exchange, startup proof, configured health,
  requested-binding hashing, route kwargs, supervisor start, verify/ensure,
  and private handoff all fail at their first boundary. Exact lifecycle/
  adversarial evidence is **162 passed / 1 host skip**.
- The exact eight-file bounded closure is **256 passed / 4 host-capability
  skips** in 11.33s. Skips are the Windows virtualenv redirector, unavailable
  query-replica symlink, unavailable portable special-file fixture, and an
  unavailable process-image symlink. Synthetic evidence only.
- WSP 62 AST inventory is green across all eight R18 production files; no
  function exceeds 50 lines. Generation is 1,359 runtime files at
  `3ae56612...8ceef4`; registry totals remain 1,527 / 265.

## [2026-08-17] R17 exact-type replica binding RED/GREEN

- Held-out RED was **15 failed / 11 passed**: duck-typed start admission
  accepted strings/lists and related malformed shapes; expected health could
  concatenate invalid objects into tuples; actual fields were string-coerced.
- The identical expected-binding matrix is now **30/30** across string, list,
  tuple/string subclasses, bytes, mapping, generator, int/bool, whitespace,
  empty, wrong-length, and nested cases. Supervisor failures occur before
  verifier, stop, spawn, health, or another side effect.
- Actual-health coverage rejects int, bool, list, mapping, string subclass, and
  surrounding whitespace without coercion. Exact duplicate fields and a full
  digest-shaped four-tuple are positive controls. Malformed ready proofs,
  routes, configured health, and private handoff also fail at their first seam.
- Final lifecycle/adversarial matrix is **125 passed / 1 host skip** in 4.40s;
  the bounded eight-module closure is **220 passed / 3 host skips** in 11.07s.
  All tests use synthetic state; independent verification is pending.
- Manifest generation is 1,358 runtime files at `430936e3...561cbb`.
  Registry totals remain 1,527 / 265 because R17 added cases to existing test
  functions/modules rather than new registry entries. Currentness passes and
  all six manifest/digest/pin contracts pass in 41.94s.

## [2026-08-17] R16 missing-route and wildcard-health RED/GREEN

- Initial held-out command was **2 failed**: `_health_contract_ready` returned
  true without replica fields, and configured `ensure` called health without a
  route. After the narrow admission fix the identical pair is **2 passed**.
- Migrating route-less fixtures first yielded **29 passed / 50 failed / 1
  skip**; centralized full synthetic route fixtures preserved downstream
  lifecycle assertions without weakening production defaults.
- Final lifecycle/adversarial matrix is **84 passed / 1 host skip** in 4.36s.
  The bounded owner/service/HTTP/descriptor/materializer closure is **182
  passed / 3 host skips** in 11.08s. Malformed/partial routes fail before
  spawn; configured full route, reuse, restart, saved-route corruption, and
  cleanup are covered. Independent verification remains pending.
- Regenerated manifest/registry closure is 1,357 runtime files and 1,527 tests /
  265 quarantined. Digest `ff8651ad...f577b` is aligned with the extension and
  the identical six-contract suite passes in 43.71s.

## [2026-08-17] Phase 2 owner-routing RED/GREEN

- Initial bootstrap adjacency exposed 14 failures from the new replica keyword
  crossing legacy fakes and empty configured-health calls. Compatibility was
  retained only for injected legacy seams; production default startup requires
  a verified replica and explicit split storage argv.
- Added exact reuse/drift/swap/order/argv/environment/health tests plus strict
  descriptor and service-routing contracts. WSP 62 extraction then moved the
  single request validator, configured-owner validation, and replica backend
  runtime without duplicating security decisions.
- Final focused result: **222 passed / 3 skips** in 10.57 seconds. The skips are
  the inapplicable Windows virtualenv redirector regression fixture, unavailable
  symlink creation, and unavailable portable special-file fixture. Synthetic
  validation only; independent promotion and live acceptance remain pending.
- Widened adjacency first reported **2 failed / 86 passed / 1 skip** in 3.88s:
  both transition fixtures assumed one probe per logical gate, so the new
  authority-update-plus-maintenance pair reached `held` before the intended
  receipt/backend boundary. Exact two-test correction passed in 1.63s and the
  unchanged widened command passed **88 / 1 skip** in 3.51s.
- Manifest contracts first reported **2 failed / 4 passed** in 42.31s because
  the prior digest remained pinned in the test and extension compatibility
  constant. After binding both generated-contract consumers (final digest
  `3a6577...fb13` after WSP 62 extraction),
  the identical file first passed **6/6** in 42.70s and the final staged tree
  passed **6/6** in 43.43s. Repeated closure hashing is retained as scale
  evidence, not hidden as a runtime failure.

## [2026-08-17] R15 Windows copy-deletion RED/GREEN

- Preserved verifier RED: R14 tests covered active, publication-temp, and
  staging quarantine but did not falsify the Windows FileDisposition cleanup
  reachable inside failed model copy.
- Updated old deletion expectations to require partial file/tree preservation
  after handle closure. Added deterministic source/import/export absence proof
  and a dynamic query failure that verifies partial bytes inside the quarantined
  staging root. R14 mutation/replacement and dual-lease tests remain unchanged.
- Focused model/guard/query result: **70 passed / 2 skips**. Bounded ten-file
  seam: **211 passed / 5 skips** in 7.82 seconds, with two known config warnings.
  Governed closure is **1,348 runtime files**, digest
  `c0d1ada803675ce926d62567266a7d77d68adc9f41d924e5197c10d03f31ce3f`,
  and **1,525 tests / 265 quarantined**. These are candidate-author results,
  not promotion evidence.

## [2026-08-17] R14 no-delete rollback RED/GREEN

- Preserved verifier RED: R13's documented cleanup contracts failed because an
  active file could be mutated in place after content verification and before
  unlink; publication temps and staging were also deleted on failure.
- Replaced deletion assertions with preservation contracts for same-inode/
  same-size mutation, name replacement, no-replace collision, rename failure,
  unsupported platforms, failed publication temps, and staging directories.
  Normal success proves the orphan root stays empty; failure evidence contains
  relative paths only.
- Focused query + guard result: **62 passed / 2 skips**. Bounded ten-file seam:
  **209 passed / 5 skips** in 8.13 seconds, with two known disabled-plugin
  warnings. Governed closure is **1,348 runtime files**, digest
  `ab4e43666520dba537c76a0431354c79ac28fb48b9c8d178ddb7120e3c775400`,
  and **1,525 tests / 265 quarantined**. These are candidate-author results,
  not promotion evidence.

## [2026-08-17] R13 retained-publication RED/GREEN

- Preserved verifier RED: a lease could transition after point proof and before
  active publication. Initial API-cut migration also produced **16 failures**,
  all the expected removed `QueryReplicaDependencies` import; the publication
  split first produced **6 failures**, all old tests patching moved private
  helpers. Tests were retargeted to the new owner without weakening behavior.
- New lock unit scope is **4 passed**. Replica scope is **27 passed / 2 host
  skips**; accepted guard adjacency is **57 passed / 2 skips**. It proves both
  sentinels exclude contenders through active publish and release on success or
  error, final-failure active cleanup, refusal to delete replaced state,
  direct-root model markers, sealed public dependencies, exact integers, and
  normalized case/Unicode aliases. Widened closure is **204 passed / 5 skips**
  in 7.95 seconds. Manifest/registry is **34 passed** in 49.94 seconds; current
  closure is **1,348 runtime files**, digest
  `7a1bb08f72dd434d92b077b1093d6c5818d3bc1355bf8a03cd32835bd2a8799b`,
  and **1,525 tests / 265 quarantined**. Both derived checks are current;
  broad-suite execution remains intentionally excluded.

## [2026-08-17] Immutable query replica materializer RED/GREEN

- Added synthetic adversarial coverage for exact manifests and per-file
  source-before/source-after/destination hashes, receipt/generation and lease
  races, overlap, links/reparse/hardlinks/special files, all resource bounds,
  no-overwrite publication, copy/hash failure, descriptor failure, cleanup
  containment, deterministic success, and unchanged canonical bytes.
- Focused new suite: **17 passed / 2 host-capability skips** in 1.16 seconds.
  Combined new suite plus accepted guard adjacency: **47 passed / 2 skips** in
  1.49 seconds after WSP 62 decomposition. The exact accepted nine-file closure
  plus the materializer collected **165 = 160 passed / 5 host-capability
  skips** in 6.43 seconds, with two expected disabled-plugin config warnings.
  These are candidate-author results, not independent promotion evidence.
- After staging made the new helper and test visible to the governed closures,
  both derived checks are current: backend runtime count **1,347**, digest
  `8a24beccd17f1438e6948ea0bf10115748f055479c40a05841eb7cf90b668929`,
  and test registry **1,525 total / 265 quarantined**. The exact manifest plus
  registry suite is **34 passed** in 51.95 seconds with the same two expected
  disabled-plugin config warnings.

## [2026-08-17] R11 launch-capability continuity RED/GREEN

- Independent RED proved R10's descriptor was closed after point revalidation
  and before the runner call. Tests now inspect the real descriptor inside an
  injected runner, prove close-on-success and close-on-error, prove no runner
  call after revalidation failure, and exercise replacement during launch.
  Windows must deny replacement while its handle is retained; Linux may replace
  the pathname but the `/proc/self/fd/<fd>` command and `pass_fds` remain bound
  to the original object. An actual proven-interpreter subprocess smoke passes.
- Exact nine-file acceptance is **146 collected = 143 passed / 3 named
  symlink-capability skips** in 5.43 seconds. Process-image scope is **14
  collected = 13 passed / 1 skip**. The full six manifest-generator tests pass
  **6/6** in 40.48 seconds with two disabled-plugin config warnings; canonical
  runtime count/digest is **1,346** / `61a5b14f8f13dbb93ce91d7fab473bec72bccc7060fdf9250db3305037a6ee77`.
- The 184-second broad bridge timeout was not rerun and remains unresolved scale
  evidence. Holo remained quarantined; no live acceptance/runtime effect ran.

## [2026-08-17] R10 Windows exact-case executable RED/GREEN

- RED: the focused Windows leaf-case alias regression failed because
  `prove_process_executable_path()` admitted `python.exe` for a filesystem
  entry named `PyThOn.ExE`. The same `normcase` boundary also covered parent
  components, so the correction parameterizes both directory and file aliases.
- GREEN: a point-in-time executable descriptor exposes the case-preserving final
  path to a dedicated validator. It accepts anchor case equivalence and requires
  exact remaining components; R11 later retains a fresh descriptor through the
  runner. Process-image scope collected **11 = 10 passed /
  1 file-symlink capability skip**.
- Focused seven-file scope collected **125 = 123 passed / 2 skips**. Exact
  nine-file acceptance scope collected **141 = 138 passed / 3 skips**. The
  skips were explicitly `file symlink unavailable`, `symlink creation
  unavailable` for the receipt fixture, and `directory symlink unavailable`;
  they are not counted as passes. Two pytest configuration warnings reflect
  intentionally disabled external plugins and do not alter outcomes.
- AST parsing passed for all three corrected paths. Registry `--check` reports
  **1,524 tests / 265 quarantined**. Backend-manifest write/check reports
  **1,346 runtime files** with digest
  `e925b311f81e561bb975c073ced84b09528fabaddf9c613490e2d4465e0961d9`.
  The six-test generator run was **5 passed / 1 failed** on its stale test
  digest; the first focused rerun then exposed the stale extension constant.
  After updating both exact consumers, that focused regression passed **1/1**;
  the entire six-test file was not rerun and is not claimed green.
  The full bridge-directory run exceeded the 184-second shell budget without a
  captured result and is recorded as non-evidence, not PASS or FAIL. Holo query
  access stayed quarantined and no live acceptance/runtime effect ran.

## [2026-08-17] R9 executable-authority and sanitizer RED/GREEN

- RED first failed collection because no process-image proof module existed.
  The first implementation then exposed six Windows failures because the
  existing directory lease requested unavailable parent mutation rights.
- GREEN reuses the narrower verified regular-file handle and proves actual OS
  process-image resolution, mutable `sys` field immunity, exact spawn argv,
  alias/symlink/junction/reparse/hardlink/replacement/missing-proof rejection,
  descriptor identity/final-path revalidation immediately before spawn, and
  in-memory-only proof propagation. The shared sanitizer directly proves
  removal of `PYTHONHOME`, `PYTHONPATH`, `PYTHONSTARTUP`, `PYTHONUSERBASE`,
  `PYTHONINSPECT`, RedDog-private values, and provider secrets before the probe
  installs one exact trusted `PYTHONPATH` plus `PYTHONNOUSERSITE=1`.
- Final strengthened focused result was stable for three consecutive runs:
  **87 passed, 2 platform/filesystem skips** each. The exact 14-file adjacent
  tier passed **271 with 2 skips**; the nine-file adversary/runtime/sanitizer
  tier passed **136 with 3 skips**. Metadata provenance was exactly
  `python -m pytest -q` over
  `scripts/tests/test_generate_reddog_backend_manifest.py` (6),
  `holo_index/tests/test_holoindex_test_registry_indexing.py` (7), and
  `modules/infrastructure/wre_core/tests/test_wre_test_registry.py` (28):
  **41 passed in 53.68s** under `C:\Python312\python.exe`, without `-B` or an
  inline environment override. Registry write/write/check is current at
  **1,524/265**; manifest write/write/check is current at **1,346 files** and
  canonical digest
  `4de0e76a29dfc8d5338ee0c88251f3deb7af2820ca07afd4832655920045a663`.
  Fast Node contract/preflight/async suites passed. R9 does not claim the
  exhaustive extension shard runner or a live PASS.

## [2026-08-17] R8 trusted snapshot-runtime RED/GREEN

- RED was **7 failed / 32 passed / 1 skipped**: candidate acceptance did not
  forward its validated runtime proof, the child inherited ambient packages,
  and dependency failures were flattened.
- Focused GREEN proves exact base-interpreter argv/candidate cwd, `-S -B`, one
  exact trusted site-packages path, hostile environment scrubbing, no-user-site,
  ChromaDB 1.5.5 origin before store open, generation-bound 1.3.0 rejection,
  typed stable-error propagation, no runtime-path receipt disclosure, and
  pre/post descriptor revalidation even under `BaseException`.
- No test reads, mutates, reuses, or upgrades the retained R7 failed store or
  receipt. The focused 77-pass/2-skip matrix passed three consecutive runs;
  the exact 14-file adjacent matrix passed **271/271 with 2 platform skips**,
  and the seven-file acceptance adversary/probe matrix passed **118/118 with
  2 platform skips**. Fast Node compatibility/contract/preflight/async groups
  passed. Registry write/write/check is **1,523/265**; manifest
  write/write/check is **1,345 files** at canonical digest
  `8ab41b5ebd22cdfa9fb0ec8ca736ce38f17dd233fb3ff7d9ae0fd2ef7a551941`.
  The 300-second exhaustive extension shard runner was not run in R8 and is not
  claimed; it remains available to the independent verifier.

## [2026-08-17] R6 descriptor receipt proof RED/GREEN

- Filesystem-proof RED was **8 failed / 1 skipped** because the focused helper
  did not exist. GREEN proved exact descriptor/digest continuity, strict bounded
  parsing and bindings, hardlink/link denial, replacement detection or Windows
  replacement exclusion, and close-on-exception: **9 passed / 1 skipped**.
- Candidate integration RED was **28 failed / 2 passed** because no proof opener
  dependency existed. GREEN additionally proves pre/post-probe revalidation,
  `KeyboardInterrupt` cleanup/finalization, immediate secret-free owner-session
  digest retention, empty pre-owner FAIL evidence, and fail-closed ownership
  drift. The focused combined suite passes **42 passed / 1 skipped**.
- R5's exact adjacent Windows command used `C:\Python312\python.exe` (CPython
  3.12.2, non-venv) with `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `-B -m pytest -q`,
  and these 13 module files plus one script file:
  `test_holo_query_service.py`,
  `test_holo_query_service_embedding_generation.py`,
  `test_holo_query_service_fastapi_adapter.py`,
  `test_holo_query_service_runtime_safety.py`,
  `test_holo_query_service_supervisor.py`,
  `test_holo_query_service_supervisor_cold_start.py`,
  `test_holo_query_service_supervisor_platform.py`,
  `test_holo_query_service_edges.py`, `test_holo_query_service_http.py`,
  `test_reddog_holoindex_main_preflight.py`,
  `test_reddog_holoindex_maintenance_diagnostics.py`,
  `test_reddog_holoindex_maintenance_handshake.py`, and
  `test_reddog_holoindex_owner_bootstrap.py`, plus
  `scripts/tests/test_reddog_holoindex_owner_query_once.py`. Its exact result was **273
  collected = 271 passed, 2 skipped**. The skip predicates were the POSIX
  new-session escape contract (`os.name == "nt"`) and Windows virtualenv
  redirector regression (the interpreter was not in a venv). No R6 live PASS
  exists. Registry write/write/check is **1,522/265** at SHA-256
  `35d0b1b37af6b27c4929ea732a96b2846d670628cfa4015268fe8ab1bb6780b3`;
  manifest write/write/check is **1,345 files** at canonical digest
  `e50257c3cfcbfd45ff00d72afa20e82b9cb8aed72b54481e5429de87df4b7c8a`.
  (WSP 15/22/50/62/87/97)

## [2026-08-17] R5 supported-wrapper activation RED/GREEN

- Wrapper RED failed because no preflight seam existed. GREEN proves an exact
  root-bound freshness mismatch returns with `owner_attempts=0`, no retry, and
  no owner/backend call. Successful `REUSED` process ownership now cleans up.
- Acceptance RED failed because no supported activation dependency existed.
  GREEN pins direct queries x2, private cleanup, supported activation x1,
  receipt integrity, exact SHA/generation/receipt/root, no leaked handoff,
  post-activation rehydration, and isolated collection snapshots. Drift,
  malformed/tampered receipts, exception, `KeyboardInterrupt`, and collection
  mismatch fail closed.
- WSP 62 extraction is behavior-preserving: `query_once` is 35 lines; every
  modified wrapper helper is at most 35 lines and every candidate function is
  at most 50. Focused wrapper plus acceptance tests pass **58/58**; the hostile
  13-test subset passed three times; the base-interpreter adjacent matrix
  collected **273 = 271 passed, two skipped**. A venv run produced four known Windows
  redirector PID-observation failures; the exact diagnostics file passed 13
  with one platform skip under `C:\Python312\python.exe`, the documented
  interpreter for that contract. Registry write/write/check stayed
  **1,521/265** at SHA-256 `3115b7602af5e5b1e89403be218113b3f83f933ed3516539cc94701115402a55`.
  Manifest write/write/check stayed deterministic at **1,344 files**, canonical
  digest `8929b8c0a9818dc4159e3aee7f8a394043950289331dfa075c371a25b6bda423`;
  its six Python tests and Node compatibility/preflight passed. Tests used
  injected/disposable state only; no live owner, model, refresh, reindex,
  persistent-store, canonical receipt, or promotion effect ran.
  (WSP 22/34/50/62/87/97)

## [2026-08-17] R3 live-failure acceptance RED/GREEN

- Immutable live evidence remained read-only: retained store and FAIL receipt
  for `fb72cbd99bc9499545823fa1849fc4597b8d71ec`; receipt SHA-256
  `f9b5e18ce62e63af3bbbf0e0f3d36def5614216fafadca8872703f519be43a78`.
- Layer A RED was **1 failed / 17 passed**: missing handoff masked exact
  `HOLOINDEX_MAINTENANCE_REFRESH_FAILED`. GREEN was **18/18**, including success
  without handoff and both present-handoff cleanup paths.
- Runtime-root RED was **9 failed / 39 passed**: missing required config plus
  absent distinct/clean/related/non-reparse/local-dependency guards. GREEN was
  **48/48**; the expanded candidate/guard/sealed-runtime matrix passed **57/57**.
  The injected public handshake-to-acceptance failure chain stayed FAIL with no
  query. An actual Windows probe found no trusted packages in the candidate
  worktree and exactly one in `O:/Foundups-Agent`.
- CLI RED was **5 failed / 1 passed**; GREEN was **6/6**. Default/malformed paths
  remain import-inert, runtime root is required and absolute, and `--real`
  forwards six absolute paths exactly once. No test ran live maintenance,
  service, model, store, receipt, or reindex effects. (WSP 22/62/97)
- Frozen closure on `C:\Python312\python.exe` (CPython 3.12.2, Windows,
  `sys.prefix == sys.base_prefix`) used `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` and
  `python -B -m pytest -q`. The affected 16-file set collected **238: 236 passed
  / 2 skipped**: `test_holo_query_service.py`,
  `test_holo_query_service_embedding_generation.py`,
  `test_holo_query_service_fastapi_adapter.py`,
  `test_holo_query_service_runtime_safety.py`,
  `test_holo_query_service_supervisor.py`,
  `test_holo_query_service_supervisor_cold_start.py`,
  `test_holo_query_service_supervisor_platform.py`,
  `test_reddog_holoindex_acceptance_guards.py`,
  `test_reddog_holoindex_acceptance_model_copy.py`,
  `test_reddog_holoindex_candidate_acceptance.py`,
  `test_reddog_holoindex_candidate_acceptance_script.py`,
  `test_reddog_holoindex_main_preflight.py`,
  `test_reddog_holoindex_maintenance_diagnostics.py`,
  `test_reddog_holoindex_maintenance_handshake.py`,
  `test_reddog_holoindex_owner_bootstrap.py`, and
  `test_reddog_sealed_holo_runtime.py`, all under this `tests/` directory.
  The adjacent 13-file set collected **245: 243 passed / 2 skipped**: the first
  seven query-service files above through
  `test_holo_query_service_supervisor_platform.py`, plus
  `test_holo_query_service_edges.py`, `test_holo_query_service_http.py`,
  `test_reddog_holoindex_main_preflight.py`,
  `test_reddog_holoindex_maintenance_diagnostics.py`,
  `test_reddog_holoindex_maintenance_handshake.py`, and
  `test_reddog_holoindex_owner_bootstrap.py`. Both sets skipped the POSIX
  new-session escape contract because `os.name == "nt"` and the Windows
  virtualenv redirector regression because this interpreter is not in a venv.
  Tier-0/query ordering **279 passed**; hostile subset **17/17** in
  1.86/1.87/1.85 s. Manifest
  generator **6 passed**, Node compatibility/preflight passed, registry and
  manifest checks were current, Python AST **10**, JSON **2**, JS syntax, diff,
  zero bounded secret-pattern hits, and WSP 62 limits all passed.

## [2026-08-17] Isolated candidate acceptance RED/GREEN

- R1 RED was **15** absent-guard, **6** absent-orchestrator, **3** absent-CLI,
  one missing expected-handoff, and two finalization failures before production.
- R2 Layer C RED was **4/4**: live per-file growth, live aggregate growth,
  Windows source-parent/root replacement, and destination-parent/root
  replacement were not contained. The first integrated GREEN exposed a
  path-reopen `MODEL_DIGEST_MISMATCH`; descriptor hashing then proved the same
  held source/destination objects without downgrading Windows sharing.
- Layer C WSP 62 review rejected a 669-line copy module and 60/58/57-line
  functions. Decomposition produced dedicated descriptor and Windows helpers;
  candidate and touched production functions are now at or below 50 lines.
- R2 Layer D RED was **3 failed / 18 passed** before correcting non-real CLI
  imports, port-race error preservation, and missing-new-handoff rejection.
  GREEN was **22/22** focused and **82/82** affected acceptance/owner/CLI in
  2.21 s. The four import/race tests passed **4/4** three consecutive times
  (1.49/1.49/1.54 s).
- Final cross-package RED stopped at collection: after the Moltbot owner-client
  test loaded its module package, the nested `moltbot_bridge/scripts` shadowed
  the repository-root `scripts` namespace. Binding the one-shot query test to
  the exact root scripts directory made the same ordered pair **48/48** and the
  final combined 13-file matrix **212 passed / 2 optional skipped** in 19.44 s.
  A 17-test hostile Windows/port/handoff/session/import subset passed three
  consecutive runs in 1.90/1.81/1.81 s.
- Registry write/write/check was deterministic at **1,521 tests / 265
  quarantined**, file SHA-256
  `3115b7602af5e5b1e89403be218113b3f83f933ed3516539cc94701115402a55`.
  Manifest write/write/check was deterministic at **1,344
  runtime files**; its expanded contract contains all seven acceptance runtime
  paths and canonical digest `a8e3a647abb0c5446670a31fb3ea8e160c9d4eda60c0a110a46918c03f9834b5`.
- Tests are dependency-injected and disposable-filesystem only. They did not
  rebuild/query a real store, start/stop a resident owner, copy/download/install
  a model, touch the canonical receipt, or publish/promote isolated state.
  (WSP 22/34/62/97)

## [2026-08-17] WSP 62 documentation correction verification

- R4 changed documentation only. `INTERFACE.md` is 971 lines versus the R3
  verifier-observed 1,010, and every candidate-touched ordinary README or
  INTERFACE remains below the 1,000-line Markdown threshold.
- Exact parser suite: **47 passed** in 1.56 s. Exact source/function/class
  no-growth guards: **2 passed** in 1.49 s. Manifest generator: **5 passed**
  in 29.29 s; registry/manifest checks and Node compatibility passed.
- The R3 278-test focused and 356-pass/1-skip adjacent matrices were not rerun
  or relabeled as R4 evidence because no code, tests, or contracts changed.
  (WSP 22/34/62/97)

## [2026-08-16] K-invariant owner boundary falsification

- RED: allowlisted producer errors were collapsed to generic semantic backend
  failure, and unproven README evidence was promoted ahead of a higher-score
  code hit by owner-side top-K inference.
- GREEN: catalog/incomplete/lookup codes retain 503/409/503 status and empty
  evidence; forged/free-text metadata remains generic. Deterministic failures
  do not retry; lookup failure retries once.
- Proved reservation requires canonical target attestation, query relation,
  and one complete exact pair. Missing, unrelated, ambiguous, multi-module,
  partial, mixed, duplicate, and forged claims retain global order even beside
  a 99% unrelated hit. R3 Unicode RED was **8 failed, 39 passed** in 1.47 s;
  isolated GREEN was **47 passed** in 1.47 s. The exact focused command now
  includes the machine-spec contract and passed **278** in 4.00 s.
- Final bounded command covering Holo incident/schema tests plus owner service,
  edges, embedding, runtime safety, supervisor/cold-start/platform, HTTP,
  FastAPI, and wrapper: **356 passed, 1 optional skip** in 11.21 s. No resident
  owner, persistent store, model, network, exhaustive aggregate, or reindex
  was used. The >184 s all-bridge run remains scale evidence only.
- Unicode falsification covers U+0085, U+202E, U+2066, U+200C, U+200D,
  U+FEFF, a direct surrogate, NFC/NFD-equivalent duplicates, invalid UTF-8,
  and visible accented/CJK/symbol controls.
- Registry write/write/check was 7.231/7.222/7.355 s at 1,517 tests/265
  quarantined with SHA-256 `0510244d701c7df08562852f02c76cdda1fccae6eb34fb387cd096aba375c675`.
  Manifest write/write/check was 9.581/9.613/9.761 s at 1,337 files, canonical
  digest `8e2680eb6075c56f1528a0cbdf2f08b44076cf8c814cec0f45c5a997df723ac9`.
- Manifest generator: **5 passed** in 29.18 s; exact supervisor no-growth:
  **1 passed** in 1.25 s; Node compatibility contract passed. Static closure:
  35 UTF-8, 18 Python compile/AST, 3 JSON, 1 JavaScript, clean diff, and zero
  bounded secret-pattern hits.
  (WSP 22/34/62/97)

## [2026-08-16] Maintenance diagnostic falsification

- Proved exact allowlisted child errors survive the final-JSON boundary while
  detail, prior logs, and secret-shaped text never enter the parent result.
- Proved free text, malformed/duplicate-key JSON, forged codes, extra schema
  fields, and oversized output fall back to the generic refresh failure;
  timeout retains its fixed code.
- Reproduced a 0.1-second timeout taking 3.109 seconds when a descendant held
  stdout. Successful cooperative tree termination reduced the same reproducer
  to 0.265 seconds; the success-path regression proves both PIDs exit, the pipe
  closes, and no reader remains.
- Added missing, denied, and hung Windows `taskkill` regressions proving bounded
  caller/direct-child return while truthfully exposing the escaped descendant,
  retained stdout, and live daemon reader until exact-PID test cleanup.
- Added a POSIX new-session escape regression proving an escaped descendant is
  outside the exact process group, followed by exact-PID cleanup and no-leak proof.
- Proved the production runner retains exactly the 16 KiB cap without a disk
  capture. Focused bridge/Holo maintenance suites: **53 passed**; manifest
  generator contract: **5 passed**.

## [2026-08-16] Zero-limit falsification

- Reproduced `flatten_hits(..., 0)` returning one item and pinned the repaired
  empty-result contract alongside positive-limit and Tier-0 ordering tests.

## [2026-08-16] Tier-0 owner-result reservation

- Proved explicit unique module queries reserve root README then INTERFACE at
  K=1/K=2 while larger K retains score-ranked implementation evidence.
- Proved nested test README is not substituted and no-module queries retain
  prior global score order.
- Revalidated owner semantic proof, service edges, supervisor/query boundary,
  transport, receipt binding, and adjacent RedDog/OpenClaw closures: 165
  owner tests passed with 1 optional skip; 82 adjacent tests passed.

## [2026-08-15] Owner-response repository path projection

- Proved typed semantic buckets become repository-relative before flattened,
  raw, semantic-evidence, and receipt use.
- Proved absolute outside-root evidence fails closed with no returned payload.
- Added host-independent Windows/POSIX, backend-alias, `location`, traversal,
  drive-qualified, and backend-mutation isolation regressions.
- Proved null, empty, and non-string path fields fail closed rather than
  becoming fabricated string evidence.
- Proved control characters plus Windows ADS, reserved-device, wildcard, and
  trailing-dot/space path forms fail closed before evidence use.
- Proved live-shaped `path` plus `location=path:Symbol()` evidence remains
  citable only when both fields identify the same repository-relative file.
- Proved canonical NAVIGATION symbol and plain-path annotations are removed
  from location identity while empty or control-bearing annotations reject.
- Proved unknown buckets, malformed bucket types, non-mapping/pathless hits,
  and malformed metadata fail closed with no raw or flattened evidence.
- Proved unknown or nested hit fields, non-scalar hit values, unknown
  collection-map keys, invalid backend identifiers, and forged embedding
  fingerprints cannot cross the canonical producer schema.
- Proved the producer contract exactly matches the checked-in machine-language
  specification, including aliases, counts, query identity, ranking fields,
  per-bucket shapes, and finite numeric values.
- Extracted one shared canonical response fixture after WSP 62 review; existing
  service, edge, embedding, HTTP, receipt, and machine-contract suites retain
  ownership of their behavior instead of duplicating a new test module.
- Proved every failed owner response is evidence-free, including lexical,
  stale-repository, changed-generation, timeout, and malformed-evidence paths.
- Added terminal-space/tab/newline and Windows-root-on-POSIX regressions after
  independent security review found permissive pre-validation normalization.
- Added C1, non-breaking-space, and bidirectional-format regressions after the
  final security review found non-ASCII control channels.
- Added real producer-float parity, work-ledger global flattening, evidence-free
  empty-canary failure, and ambiguous lowercase ADS-suffix regressions after
  exact-SHA security review.
- Added owner-boundary regressions proving oversized priority/confidence values
  return `QUERY_EVIDENCE_INVALID` with no raw or flattened evidence.

## [2026-08-06] Linked-worktree owner dependency root

- Proved the query adapter passes a separately resolved primary worktree to
  owner bootstrap while retaining the selected authority root for query bytes.
- Proved missing or unrelated primary candidates fall back to the workspace,
  and the resolver contains no checkout, reset, index, or cleanup mutation.

## [2026-07-30] Canonical Holo runtime dependency binding

- Proved nonsealed owner and maintenance children accept only the canonical
  checkout-local virtualenv after interpreter, version, containment, and
  system-site validation.
- Proved sealed refresh ignores the workspace dependency path, attacker
  `PYTHONPATH` is replaced, and owner reuse is bound to the runtime root.
- Proved authenticated HTTP 503 backend failures terminate startup immediately
  while transient connection failures retain bounded retry behavior.
- Revalidated exact-SHA authority transaction propagation, owner lifecycle,
  startup preflight, and post-merge coordination.

## [2026-07-29] Cold semantic owner startup probe alignment

- Added a supervisor regression modeling a 35-second cold semantic canary and
  proving startup grants it the bounded warmup window instead of repeatedly
  abandoning it at the ordinary 30-second probe limit.
- Retained ordinary probe, total startup deadline, exact-binding, process
  cleanup, and secret-nondisclosure coverage.

## [2026-07-29] Sealed RedDog Holo process boundary

- Proved required sealed commands select manifest-copied Holo entrypoints and
  never the live checkout scripts while repository reads resolve to the
  authorized target checkout rather than the sealed source copy.
- Proved substituted or tampered bootstrap/runtime paths fail closed and provider,
  repository-authority, and Python import-override values do not enter Holo
  subprocess environments.
- Revalidated maintenance and owner-supervisor lifecycle behavior.

## [2026-07-27] Promotion-time owner binding

- Proved configured-owner exact binding without process startup.
- Proved an owned query owner serving another generation is rejected.

## [2026-07-25] HoloIndex parent-process watchdog

- Replaced pipe-EOF tests with injected and real parent-process termination coverage.
- Proved the public parent PID is passed in argv, stdin is `DEVNULL`, and existing semantic probe/lifecycle tests remain green.

## [2026-07-25] HoloIndex owner semantic probe budget

- Added a real delayed loopback health response proving the bounded probe accepts semantic readiness after more than one second.
- Retained timeout, secret-nondisclosure, port-conflict, and parent-watchdog regressions.

## [2026-07-25] HoloIndex owner lifecycle hardening

- Added mocked and real-socket port-conflict coverage.
- Added mocked and real-subprocess parent-pipe EOF cleanup coverage.

## [2026-07-25] HoloIndex owner repository-root binding

- Added matching-root success and mismatched-root fail-before-backend tests.
- Re-ran the owner service, HTTP, runtime-safety, embedding, and supervisor suites.

## [2026-07-20] Receipt-v2 maintenance fixture integrity repair

**WSP Protocol:** WSP 00, 22, 50, 62, 97

**Observed:** The second owner runbook group produced 3 failures and 61
passes. Its maintenance fixture still declared receipt schema v1, used a
literal generation, emitted only the seven query collections, and omitted the
v2 source-policy and collection-snapshot proof digests. Production correctly
treated the supposedly fresh fixture as stale and rejected refresh-published
fixtures whose baseline proofs were incomplete.

**Change:** Kept production validation unchanged. The maintenance fixture now
emits all receipt-v2 collection entries, supplies format-valid policy and
snapshot digests, computes the generation with the production helper, and
self-checks with the production integrity validator. A blank legacy embedding
fingerprint remains integrity-bound but semantically stale, so its test still
proves that maintenance refreshes it.

**Validation:** The exact second runbook group passes 64 tests. Adjacent
freshness-receipt, maintenance-session, CLI-maintenance, and incremental-index
suites pass 84 tests. The changed Python test module remains below the WSP 62
800-line warning threshold; no exemption is required.

## [2026-07-20] Receipt-v2 owner fixture integrity repair

**WSP Protocol:** WSP 00, 22, 50, 62, 97

**Observed:** The first owner runbook group produced 23 failures and 38 passes.
The shared owner and HTTP fixtures still emitted the pre-v2 literal
`generation-1`, only the seven query collections, and placeholder proof
digests. Production correctly rejected those fixtures as
`invalid_freshness_receipt_integrity` before reaching the semantic and timeout
behaviors under test.

**Change:** Kept production validation unchanged. The synthetic receipt helper
now includes every v2 receipt collection, uses format-valid proof digests, and
computes its generation with the production integrity algorithm after test
repository/store identity normalization. The HTTP suite reuses that helper so
the transport and core fixtures cannot drift independently.

**Validation:** The exact first runbook group passes 61 tests. The adjacent
embedding/generation and production freshness-receipt suites pass 39 tests.
Changed Python test modules remain below the WSP 62 800-line warning threshold;
no exemption is required.

## [2026-07-18] HoloIndex / RedDog Operational Truth Boundary POC

**WSP Protocol:** WSP 05, 06, 15, 22, 50, 62, 87, 96, 97
**Phase:** POC implementation complete; focused validation green; PR pending
**Agent:** 0102 architect with delegated adversarial workers

**Changes:**

- Added freshness-gate tests for missing, malformed, stale, wrong-repository,
  wrong-store, incomplete-manifest, active-maintenance, and generation-race
  states.
- Added owner tests for semantic-only retrieval, non-empty semantic canary,
  exact clean-HEAD checks around search, stable generation binding, bounded
  requests/results, timeout poisoning, and no indexing surface.
- Split owner-service contract, embedding/generation, runtime-safety, edge,
  HTTP, and FastAPI coverage into cohesive companion modules. Split supervisor
  lifecycle from platform-launch/constructor-bound coverage, and kept
  interactive/headless policy in test_reddog_holoindex_main_preflight.py so
  every owning test module remains within WSP_62 infrastructure thresholds.
- Added FastAPI and dependency-free HTTP transport tests for bearer
  authentication, route restriction, loopback binding, and status mapping.
- Added supervisor/bootstrap tests for hidden argv-only launch, strong
  ephemeral tokens, authenticated health, expected HEAD/generation binding,
  process-private handoff, poisoned-owner replacement, and bounded cleanup.
- Added trusted-maintenance tests for clean exact HEAD, owned-versus-external
  owner policy, environment sanitization, semantic preflight, complete
  seven-collection proof, and restart only after a verified refresh.
- Added exact seven-collection embedding-space checks, including blank legacy
  fingerprint maintenance, receipt/runtime/response mismatch rejection,
  authoritative sentence-transformers selection, and disabled owner
  SearchCache. The focused cross-module matrix separately covers complete,
  incomplete, ref-selected, and ambiguous Hugging Face snapshot caches in the
  HoloIndex-owned tests.
- Added separate cold-health warmup versus ordinary-query deadline coverage,
  supervisor startup bounds, and absolute response-body deadline coverage. The
  stdlib connect/header inactivity limitation remains an explicit POC
  assumption rather than a tested hostile-local guarantee.
- Added model-backed worker regressions that reject repository changes after
  cross-lane direct reads and immediately before report acceptance.

**Impact:** The migrated RedDog operational consumers are designed to use one
serialized semantic query service while the supported adapter exposes no
HoloIndex write surface. This does not claim OS privilege isolation or cover
legacy direct-store consumers.

**WSP Compliance:** Tests are deterministic and network-local, use synthetic
tokens, preserve failure truth, and make no production-readiness claim. The
final post-refactor infrastructure matrix passed 133 tests; the companion
owner-client and downstream RedDog matrices passed 57 and 200 respectively.
