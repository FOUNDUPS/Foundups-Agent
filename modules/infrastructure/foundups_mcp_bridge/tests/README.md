# foundups_mcp_bridge Tests

## Inert dependency-runtime closure

- `test_reddog_holoindex_dependency_runtime.py` proves content addressing,
  exact reuse without recopy, source/destination mutation rejection, complete
  file/directory topology, bounded retained handles, aliases, hardlinks,
  preservation, and inert truth flags.
- `test_reddog_holoindex_dependency_runtime_edges.py` covers literal store and
  generation junctions, aggregate path bounds, Windows file/directory alternate
  streams, and the full generation contract envelope.
- `test_reddog_holoindex_dependency_runtime_contract.py` covers duplicate keys,
  noncanonical/truncated JSON, unknown keys, reordered rows, inventory
  substitution, direct public limit validation, and concurrent public-builder
  serialization across ordinary and extended-length Windows spellings of the
  same proved store.
- `test_reddog_holoindex_dependency_runtime_windows_copy_scale.py` keeps the
  700-file retained-handle proof separate from the primary adversarial suite;
  retained leases scale with path depth, not file count. It also drives a valid
  payload path beyond legacy Windows `MAX_PATH` through full materialization,
  post-publication verification, and exact reuse.
- `test_reddog_holoindex_dependency_runtime_scale.py` is an explicit opt-in
  production-shape soak for 72,261 files and 11,639 child directories. It must
  remain opt-in; ordinary unit collection does not represent that expensive
  proof. All tests use disposable O:-local roots and never touch the live Holo
  route, store, model, owner, or maintenance path.

Exact opt-in evidence on this slice:

- Synthetic production shape: 72,261 files / 11,639 child directories; first
  1,708.812s, reuse 836.969s, peak handles +6, peak RSS +543,744,000 bytes.
- Real installed payload: 72,261 files / 11,639 child directories /
  1,853,891,335 bytes; first 2,250.675s, reuse 798.191s, peak handles +31,
  peak RSS +537,284,608 bytes; one generation and zero successful-root orphans.
- Both are single-builder resource/reuse proofs, not query-latency or
  horizontal-throughput benchmarks.

## Exact retrieval runtime-environment binding

- Adversarial tests cover executable/source mutation, manifest parity, raw
  site-package link/reparse rejection, distribution metadata limits and
  collisions, required-environment mismatch, replica/model completeness, and
  secret/path-free public projection.
- Supervisor/health/client tests prove the authenticated child digest is
  captured and mismatches fail closed. Production A-grade assurance remains
  false until installed distribution payload bytes have an exact closure.

## Owner-loaded retrieval ranker binding

- Runtime-binding tests prove source changes alter the digest and reject mixed
  roots or linked ranker files.
- Owner, authenticated health, loopback-client, query-receipt, and retrieval
  benchmark tests require the owner-emitted digest and reject malformed or
  candidate-mismatched values.
- The tests use synthetic repositories/responses and do not reindex, mutate a
  route, start maintenance, or promote a ranker.

## Supported Holo owner acquisition reliability

- `test_reddog_holoindex_owner_acquisition_reliability.py` proves route-only
  current-user precedence, no secret/unrelated environment copying, no process
  mutation, exact owner-port validation/propagation, bounded contention retry,
  distinct per-process retry ports, and one representative same-first-shard
  PID pair that diverges on retry. The 4,032 ordered pairs are explicitly not
  globally unique. It also proves the root one-shot imports the exact shared
  attempt ceiling, operation ceiling, and transient set instead of maintaining
  a parallel policy. The focused isolated shard is **22 passed**.
- Existing one-shot, bootstrap, and candidate-acceptance suites prove the new
  environment and port seams preserve strict route, freshness, cleanup, and
  isolated-candidate behavior. Final delta result: **119 passed**; the new owner
  acquisition boundary independently passes the 90% WSP_5 gate at **100%
  statement coverage**.
- Production-shaped acceptance used two independent PowerShell processes with
  no manual environment repair. Both plain governed queries returned
  `CURRENT`, exact base `90e9eca1...`, no gap, and no reindex with distinct
  receipts in 38.04 seconds; both used attempt 1. Injected contention and
  process-shard falsification tests exercise the bounded second shard; no live-
  contention result is claimed.
- The complete bridge macro is **1,117 passed / 10 expected capability skips in
  515.45 seconds**. This is bounded two-caller evidence, not a throughput/scale
  claim.

## Post-merge query-replica composition

- `test_reddog_holoindex_postmerge_replica.py` proves exact-current admission,
  normal-owner reuse, current-user route precedence over an inherited legacy
  root, source-environment immutability, route-selection failure containment,
  route-only configuration, absent-only replica/receipt allocation, activation
  failure truth, exact binding equality, and immutable post-query proof.
- The adjacent idle-automation authority-order suite proves the first authority
  lease is released before activation and reacquired for final Git/receipt
  binding. Public production entrypoints expose no effect-injection parameters.
- Focused cross-module result: **62 passed**. These are isolated proofs.
  Separately, automatic acceptance passed the real OpenClaw/AgentDB path at
  exact main `cfd1e0051`, followed by a CURRENT/no-gap/no-reindex owner query
  and unchanged full-replica proof. Later HEADs require their own evidence.
- The route-precedence repair is **34 passed** in its focused owner-acquisition
  pair and **85 passed** across post-merge, route-resolution, coordinator, and
  authority-order regressions. The composer reaches **92%** statement coverage;
  the complete bridge macro is **1,135 passed / 8 expected capability skips in
  548.82 seconds**. Live exact-main replay remains a separate gate.
- That separate live gate later completed at exact main `66526ae5`: the real
  OpenClaw/AgentDB task completed with retry count zero, three fresh-process
  queries and one pre-warmed query returned CURRENT/no-gap/no-reindex, and full
  verification retained all 33 replica artifacts unchanged. This is operational
  evidence, not a test result or horizontal throughput claim.

## Exact query-replica activation

- `test_reddog_holoindex_query_replica_activation.py` proves inert default,
  exact-repository-before-mutation ordering, fixed semantic candidate and
  stable-route canaries, rollback, revision/digest commit, immediate committed
  truth, replica revalidation, secret-free receipt publication, reserved and
  pre-existing receipt denial, fresh workspace-only authority selection,
  interrupted committed publication, and receipt-less committed-route
  finalization. It also proves exactly one typed post-commit recovery attempt,
  no candidate retry, terminal `COMMITTED_UNVERIFIED` after two failures, and
  the same recovery rule for receipt-less committed-route finalization. The
  production-shaped resolver regression supplies an existing caller
  `environment` and proves stable resolution replaces it with exactly the
  committed route-file capability; a legacy direct root cannot win.
- Current focused result is **13 passed / 1 expected host-capability skip** at
  **90%** activation-controller coverage. The adjacent post-merge, owner,
  candidate-acceptance, authority, and coordinator closure is **191 passed / 1
  expected skip**. The complete bridge macro is **1,136 passed / 8 expected
  skips in 549.69 seconds**. All test roots are disposable and O:-local.
- The CLI contract proves default inertness and explicit argument projection.
  The adjacent activation/route/planner/materializer/descriptor/maintenance/
  candidate-acceptance/authority/CLI suite is **470 passed / 7 host-capability
  skips** using only disposable O:-local test roots. No live route or Holo state
  was touched.

## Stable route-file owner resolution

- `test_reddog_holoindex_owner_replica_route_resolution.py` retains the legacy
  direct-root proofs and adds route-file rejection for relative/noncanonical
  values, direct-root ambiguity, exact committed selection, unjournaled
  `CURRENT`, `PREPARED`, and canonical or replica descriptor mismatch. Consumer
  failures preserve route/journal bytes and normalize private store errors.
- Focused route contract/store: **46 passed / 1 host-capability skip**. Expanded
  resolver, route, owner bootstrap, maintenance, and real one-shot suite:
  **173 passed / 1 skip**. Independent focused replay: **121 passed / 1 skip**.
  All route roots were disposable; no live environment, owner, Holo store, or
  replica was touched.

## Private route contract and store

- `test_reddog_holoindex_query_route_contract.py` proves canonical round trips,
  copied immutable nested bindings, direct-proof backing-map isolation,
  duplicate/noncanonical/non-finite/oversize JSON
  rejection, exact shapes and scalars, timestamp/path/digest/generation rules,
  hostile direct-construction errors, and journal predecessor/candidate chain
  integrity.
- `test_reddog_holoindex_query_route_store.py` proves no-replace idempotent
  initialization, exact revision+digest CAS, normal-exit commit, uncommitted and
  exceptional rollback, commit-request late failure, two concurrent activators,
  prepared recovery before/after route swap and after candidate-root loss,
  read-only PREPARED rejection, terminal digest admission, mandatory journal
  proof for `CURRENT`, in-lock candidate revalidation, unknown-state terminal failure,
  atomic-replace failure recovery, rollback failure recovery, lexical path/link
  rejection, and private-file mode where supported.
- Result: **46 passed / 1 symlink-capability skip** with the route contract
  using disposable roots only.
  Both files are collectable in the 1,574-test / 267-quarantined registry.
  No live route, Holo store, replica, owner, environment, or receipt was touched.

## Exact activation-plan admission

- `test_reddog_holoindex_query_replica_plan.py` covers strict repository/store/
  HEAD/model boundaries, CURRENT binding stability, exact two-manifest output,
  and production generation/22-file snapshot-manifest integration.
- Adversarial cases include same-size content replacement with restored mtime,
  directory identity replacement during either digest pass, model/snapshot
  link or junction aliases, exact-limit type rejection, missing/extra/wrong-
  generation snapshots, hostile binding shapes, and stable public failure
  normalization.
- Adjacent confined-reader and model-resolver tests prove descriptor/path
  identity stability and planner-only preservation of unresolved source-path
  evidence. Result: **109 passed / 4 host-capability skips**. All fixtures are
  disposable; no canonical store, live owner, route, replica, or maintenance
  state is changed.

## Narrow generation-bound query-replica closure

- Snapshot-store preflight verifies the exact seven-collection/22-file
  manifest, canonical generation binding, inner/outer path-size-digest
  equality, and size bounds without loading vectors. Injected link-component
  and non-string generation cases prove the
  path/scalar gate independently of host symlink privileges.
- Materializer tests reject the legacy full `vectors/` closure, wrong snapshot
  generation, missing artifacts, a nested second-model marker, and all prior
  path/link/resource failures. Canonical root/receipt/file aliases, malformed
  scalars, NFD paths, full path bounds, and case-variant model markers prove the
  replica root remains pristine on static rejection.
  The synthetic success fixture now copies 26 artifacts: four model markers and
  22 sealed snapshot files.
- WSP_62 moved manifest-policy cases into
  `test_reddog_holoindex_query_replica_manifest.py`; the primary materializer
  test remains below 800 lines. A `python -S` subprocess proves replica policy
  and the owner-client import path do not require NumPy/site packages until
  materialization. Focused result: **80 passed / 2 expected
  host-capability skips** after adding a historical full-descriptor audit
  regression; the modern materializer still rejects that legacy closure.
- The final exhaustive extension release rerun passed all four isolated groups
  in **385.561 seconds** with no release or group timeout.
- The HTTP runtime fixture injects the established exact replica verifier, so
  its synthetic owner exercises the complete binding required by the live
  client. Complete package result: **981 passed / 7 expected skips / 14
  inherited warnings in 328.28 seconds**.
- The backend-generator contract builds one immutable worktree closure for its
  five read-only assertions; hostile monkeypatch generation and the staged-index
  blob/digest proof remain independent. Final result: **8 passed in 68.38 seconds**
  after the repeated-build form exceeded a 240-second cap.

## Resident owner bounded replica revalidation

- Descriptor tests prove that retained admission rereads the exact active
  descriptor/manifest and rejects model, sealed-snapshot, or unlisted runtime
  artifact drift without opening legacy vector storage.
- Runtime routing proves exactly one complete admission switches to bounded
  revalidation; injected synthetic verifiers retain their existing behavior.
- The HTTP entry point proves only the isolated-root capability before owner
  construction; the owner performs the independent full descriptor admission
  and retains the stable `HOLOINDEX_QUERY_REPLICA_INVALID` failure.
- Focused result: **101 passed**; generated/one-shot/snapshot adjacency is
  **171 passed**; the complete bridge package is **961 passed / 6 expected
  host-capability skips**. Real read-only timing was 42.422 seconds complete
  versus 1.297 and 1.359 seconds retained, under the unchanged 15-second
  request deadline.

## Streamable HTTP and public Holo bundle contracts

- `test_holo_query_bundle_public.py` covers secret/absolute-path redaction,
  repository-relative paths, cycles, key collisions/schema overwrite, finite
  numbers, signed-63-bit integers, total size, exact byte telemetry, exact
  one-shot routing, and typed semantic/exception failures.
- `test_mcp_launcher_http.py` covers worktree common-dir runtime selection,
  Windows base-interpreter PID ownership, exact readiness schema, forged
  nonzero child rejection, exact direct tool inventory, complete lexical
  bundle proof, closed server/readiness child environments, dead-handle lock
  reaping, exact dependency-version admission, loopback-only bind, and
  optional-dev-bearer failure boundaries.
- `test_mcp_server_sse.py` retains its historical filename but now tests the
  canonical `/mcp` Streamable HTTP server. It proves exact remote pruning,
  annotations/input-schema caps, auth, protocol lifecycle, and lexical safe
  call. Deprecated SSE-named launch functions are aliases only; no SSE route is
  claimed. The exact remote inventory is one tool: `holo_query_bundle`.
  Tool inventory inspection is exercised through both supported FastMCP 2.x
  and 3.x public APIs, while production startup remains exact-pin bound.

## Deterministic legacy bridge scaling

- Pre-repair full bridge validation completed naturally twice under the unchanged
  360-second cap: **899 passed / 7 skipped** in 200.66 seconds and 314.42
  seconds. After adding the permanent cache receipt, final full bridge is
  **900 passed / 7 skipped** in 215.31 seconds. After the integration-candidate
  WSP_62 split, the repaired full bridge is **901 passed / 7 skipped / 10
  warnings** in 220.32 seconds. The pre-split legacy monolith alone was **122
  passed** in 181.33 seconds; its current split closure is 123 tests.
- Speedup state is test-only and exact-input keyed. It is restricted to the
  resolved immutable repository root, returns deep copies, bypasses temporary
  and foreign roots, and proves one underlying scan per used key. Runtime bridge
  behavior has no new cache.
- The receipt now lives in `test_repository_analysis_cache.py` and self-populates
  without ordering dependence. Two pre-repair receipts completed in 182.25 and 181.33 seconds with the
  same exact keys/requests/scans: mapping 7/125/7, module 57/2,434/57, reverse
  12/303/12. The slower 314.42-second full run received only ~77.9% CPU/wall,
  identifying concurrent host contention rather than cache nondeterminism.
- `test_repo_tools_encoding.py` proves ripgrep JSON always requests strict
  UTF-8 decoding and that invalid bytes fail closed. Ten pre-existing LinkedIn
  invalid-escape warnings remain visible in each full run.
- Cold-health warmup coverage records the exact post-warmup proof budgets
  inline, eliminating scheduler jitter while retaining the strict 20 ms bound;
  the production timeout remains unchanged.
- `repository_analysis_cache_support.py` owns selection-independent fixtures.
  The original 122 test names own 368 AST assertions after two additive,
  selection-independent support invariants; one intentionally new mutation-
  isolation test brings the combined cache/bridge selection to 123 tests/369
  assertions.

## WSP_62-focused lifecycle and acceptance ownership

- `test_holo_query_service_supervisor.py` owns startup/runtime selection;
  `_bindings.py`, `_health.py`, and `_lifecycle.py` own canonical/replica
  binding, authenticated health, and lifecycle/live-probe behavior. Shared
  doubles and payload builders live in non-test
  `holo_query_service_supervisor_support.py`.
- `test_reddog_holoindex_candidate_acceptance.py` owns configuration and owner
  handoff; `_lifecycle.py` and `_integrity.py` own cleanup/session and binding/
  integrity behavior. Shared synthetic proofs live in non-test
  `reddog_holoindex_candidate_acceptance_support.py`.
- `test_reddog_holoindex_owner_bootstrap_configuration.py` owns 20 configuration
  and adversarial binding tests; `test_reddog_holoindex_owner_bootstrap.py`
  retains 21 lifecycle tests. Shared fakes/cleanup live in non-test
  `reddog_holoindex_owner_bootstrap_support.py`.
- The split preserves the exact pre-move test, decorator, assertion, fixture,
  and collected-case inventories. Focused validation is **389 passed / 3
  unchanged host-capability skips**. This is bounded bridge evidence, not a
  repository-wide FMAS-green claim.

## Integrated main and replica/acceptance closure

- The affected bridge selection is **762 passed / 6 platform skips**.
- `test_mcp_server_sse.py` retains a historical filename and owns the one-tool
  read-only FastMCP allowlist, optional local bearer auth, Streamable HTTP
  readiness canary, and truthful termination/lock lifecycle.
- `test_reddog_holoindex_maintenance_diagnostics.py` owns bounded child output,
  stable error projection, process-tree timeout behavior, and the bounded PID
  readiness fixture used by Windows fallback tests.
- All owner, replica, snapshot, and candidate-acceptance tests use disposable
  synthetic state. They do not establish a live ChatGPT app, tunnel, Holo
  store, model, maintenance, or reindex receipt.

## R27 immutable collection snapshot codec and read adapter

- Focused synthetic contract is **116/116**. The first hardening RED was **33
  failed / 49 passed**; the second verifier RED was **19 failed / 83 passed**.
  The third verifier RED was **11 failed / 101 passed**.
  The fourth verifier RED was **1 failed / 112 passed**; a 4,096-dimensional
  cosine query under an 83,000-byte workspace reached distance computation.
  The fifth verifier RED was **2 failed / 114 passed**: four-row cosine and L2
  reductions exposed another full input-sized reduction scratch.
  It proves deterministic canonical
  manifest/JSONL bytes, sorted unique IDs, contiguous little-endian float32
  vectors, exact numeric admission, Unicode-scalar/NFC identity, strict
  bounds/digests/schema, exact contiguous buffer validation before conversion,
  mutation-isolated buffer loading, vector-size preflight before NumPy, hostile
  public-container normalization to the stable error type, and recursive NFC
  enforcement without silent normalization.
- The path-free adapter covers the Holo read subset: `name`, `metadata`,
  `count()`, paged/ID/path `get()`, and nested `query()`. Squared-L2,
  `1-cosine`, and `1-inner-product` distances, stable ID tie ordering, exact
  include shapes, stable float64 computation for admitted float32 extremes,
  explicit zero-vector cosine behavior, and workspace-bounded dynamic vector
  chunks are synthetic-GREEN. Path filters use the same bounded Unicode/NFC
  contract; result fields are lazy, cardinality is rejected before nearest
  work, and `max_result_bytes` is the exact compact-JSON wire-byte ceiling—not
  a Python heap estimate. Escapes, scalar rendering, keys, and all response
  containers are counted before deepcopy/tolist. Multi-query retained NumPy
  match arrays share the compute/session workspace ceiling.
  Cosine counts simultaneous chunk, norm-square product, and reduction scratch
  plus row temporaries (`24 * dimension + 96`). L2 counts chunk, delta, square,
  and reduction scratch (`32 * dimension + 32`). An explicit IP equality/
  off-by-one control preserves its probed chunk/dot/subtraction formula.
- One instrumented test performs 100 warm queries after load with **zero file
  opens and zero SHA-256 calls**. Exact adjacency is freshness/module-intent
  **87/87** plus owner/embedding-generation **36/36** = **123/123**. Combined
  focused plus adjacency evidence is **239/239**; the preceding truthful
  aggregate was **236/236**.
- This slice does not export a snapshot from Chroma, route an owner to it, load
  a model, alter maintenance, or prove live Holo/MCP operation. Those remain
  RED integration work.

## R24 acceptance closure and WSP62 extraction

- Wider RED was **2 failed / 94 passed / 3 skips**: route-less cold start and
  supervisor class span203. Focused GREEN is **3/3** after route-complete slow
  loopback fixture migration and cohesive lifecycle-base extraction.
- Ten-file verifier adjacency is **96 passed / 3 unchanged platform skips**.
  Supervisor is **265/1**, lifecycle **317/1**, exact closure **411/4**.
- Generated closure is 1,360 files at `fdf3643a2cb8...befc3592129e`;
  registry remains 1,527/265.
- Fixture proves verify/spawn/verify, split storage argv, scrubbed environment,
  complete response binding, configured context success, and route-less context
  rejection. It uses no real Holo/store/model.

## R23 HTTP exception and close precedence

- Local IncompleteRead escaped while close ran. Expanded RED/GREEN is **7
  failed / 7 passed -> 14/14** for HTTP protocol exceptions at request,
  getresponse, and read; timeout/OSError controls; and targeted close failures.
- Exact stage event prefixes and one close are asserted. HTTP/OSError close
  failures preserve both a ready result and a prior unavailable result; broad
  exception suppression is absent.
- Combined R16-R23 is **214/214**; lifecycle is **316 passed / 1 host skip**;
  exact closure is **410 passed / 4 unchanged host-capability skips**. Generated
  closure is 1,360 files at `6f93d87356f6...cb1db09f33a`; registry is 1,527/265.

## R22 strict health JSON conformance

- Fake HTTP RED was ready under duplicate-`ok` last-wins. Expanded RED/GREEN is
  **24 failed / 10 passed -> 34/34** across all 19 security-relevant key
  positions, nested duplicates, NaN/infinities, depth 64/2,000, primitives,
  syntax, UTF-8, oversize/status failures, and one unique JSON control.
- Invalid representations never produce ready/terminal evidence. Each admitted
  transport performs the same request, read limit 65,537, and single close.
- Combined R16-R22 is **200/200**; lifecycle is **302 passed / 1 host skip**;
  exact closure is **396 passed / 4 unchanged host-capability skips**. Generated
  closure is 1,360 files at `bc54dadeb9d1...5693a2e91e`; registry is 1,527/265.

## R21 expected-replica exchange ordering

- Exact pre-edit reproduction reached `HTTPConnection` seven times for five
  malformed replica shapes and two wrappers; hostile call count was zero.
- Focused RED/GREEN is **13 failed / 2 passed -> 15/15**. String, list, tuple
  subclass, hostile object, partial, bytes, mapping, generator, bool element,
  whitespace, empty, and over-length expectations all return binding mismatch
  before connection. Canonical malformation has deterministic first precedence.
- Full lifecycle is **268 passed / 1 host skip**; exact eight-file closure is
  **362 passed / 4 unchanged host-capability skips**; combined R16-R21
  held-outs are **166/166**. Generated closure is 1,360 files at
  `61a512386a6d...aa4f3cc3`; registry is 1,527/265. Evidence is synthetic.

## R20 exact health transport scalars

- RED **49 failed / 19 passed**; GREEN is **69/69** including binding-before-
  transport ordering. Invalid/hostile host, token, port, and timeout values
  invoke no methods, connection, request, or formatting.
- Valid exact controls cover literal IPv4 loopback, 32-character token, ports
  1/65535, and finite positive int/float timeouts through 300 seconds.
- Combined R16-R20 held-outs are **151/151**; lifecycle is **253 passed / 1
  skip**; exact closure is **347 passed / 4 host-capability skips**.
- Generated closure is 1,360 runtime files at `c64d0ad5...0c5f4e`; registry
  remains 1,527 tests / 265 quarantined. Evidence is synthetic only.

## R19 exact health-payload container

- RED was **12 failed / 7 passed**: Mapping admission reached hostile container
  methods or admitted non-exact JSON objects. Core GREEN is **19/19** and the
  arbitrary-object-expanded matrix is **22/22**.
- Hostile dict subclass, custom Mapping, `UserDict`, `MappingProxyType`, list,
  string, nested hostile fields, direct health functions, JSON decoding, and
  authenticated exchange all reject with empty call logs. Exact plain JSON
  dictionaries remain admitted controls.
- Combined R16-R19 held-outs are **82/82**; lifecycle/admission is **184 passed /
  1 host skip**; the exact closure is **278 passed / 4 host-capability skips**.
  Evidence is synthetic and does not prove live ChatGPT-app MCP availability.
- Generated closure remains 1,359 runtime files at `0acd06f2...602bb4`; the
  registry remains 1,527 tests / 265 quarantined.

## R18 exact canonical-binding types

- Initial canonical matrix was **15 failed / 13 passed**. Malformed actual
  fields could be coerced and hostile expected/actual values reached conversion.
- The unchanged canonical matrix is **28/28** and the frozen R17 replica matrix
  plus R18 is **58/58**. Eleven malformed actual and expected shapes, hostile
  zero-call objects, JSON, startup, configured, route, verify/ensure, hashing,
  and handoff seams are covered with two exact positive controls.
- Lifecycle/adversarial evidence is **162 passed / 1 host skip**. The exact
  bounded closure is **256 passed / 4 host-capability skips**: virtualenv
  redirector, two symlink capabilities, and portable special-file creation.
  All evidence is synthetic, not live ChatGPT-app MCP availability.
- Generated closure is 1,359 runtime files at `3ae56612...8ceef4`; registry
  totals remain 1,527 tests / 265 quarantined.

## R17 exact replica-binding types

- Initial type matrix was **15 failed / 11 passed**. Start admitted duck-typed
  containers/fields, expected health could raise `TypeError`, and actual health
  values were coerced to strings.
- The identical expanded expected matrix is **30/30**. Actual int/bool/list/
  mapping/string-subclass/whitespace values reject without coercion; duplicate
  exact strings and digest-shaped production values remain accepted controls.
- Startup proof, route, configured-health, and private-handoff seams use the
  same parser. Author evidence is **125 passed / 1 host skip** for lifecycle/
  adversarial coverage and **220 passed / 3 host skips** for the bounded
  closure. It is synthetic, not live ChatGPT-app MCP evidence.
- Generated closure is 1,358 runtime files at `430936e3...561cbb`; registry
  totals remain 1,527 tests / 265 quarantined.

## R16 mandatory owner-route admission

- Held-out REDs proved that empty expected replica binding admitted health and
  configured startup reached health without a route. Regression tests now
  require failure before health/spawn.
- Adversarial coverage includes absent, malformed, partial, and revalidation-
  failed routes; partial actual health; full-route configured/reuse/restart;
  missing saved route; private handoff; and bounded cleanup.
- Author results: **84 passed / 1 host skip** for lifecycle/adversarial tests,
  **182 passed / 3 host skips** for the bounded owner/service/HTTP/descriptor/
  materializer closure, and **2/2** for the held-out pair. All are synthetic;
  they do not prove ChatGPT-app MCP or live owner availability.
- Generated closure remains 1,357 runtime files and 1,527 tests / 265
  quarantined; its digest is `ff8651ad...f577b` and all six contracts pass.

## Phase 2 verified replica routing

- `test_reddog_holoindex_query_replica_descriptor.py` proves strict descriptor,
  manifest, canonical receipt/repository, lease, storage-identity, alias, and
  mutation rejection using synthetic trees only.
- `test_holo_query_service_replica_routing.py` proves the backend receives only
  the verified generation while freshness stays canonical and public responses
  contain no private absolute path.
- Owner bootstrap/supervisor tests prove exact-binding reuse, four independent
  drift replacements, active swap termination, capability-before-spawn/health
  order, complete four-field health admission, explicit split argv, and absence
  of ambient `HOLOINDEX_SSD_PATH`.
- Final focused closure: **222 passed / 3 skips** in 10.57 seconds. Skips are an
  inapplicable Windows virtualenv redirector, unavailable symlink creation, and
  the unavailable portable special-file fixture on Windows. No real process,
  live Holo/store/model/MCP/maintenance/reindex, or `E:` path is used.
- Widened adjacency is **88 passed / 1 symlink-capability skip** in 3.51s.
  Manifest/registry closure is 1,357 runtime files and 1,527 tests; its six
  digest/staged-index contracts pass in 43.43s.

## R15 no-delete query-replica publication

`test_reddog_holoindex_query_replica.py` uses synthetic stores only. It proves
authority-update then maintenance sentinel exclusion is retained through active
publication, exact sentinel bytes survive, capabilities release on every path,
and final failure quarantines the active name without replacement. Same-inode/
same-size mutation, name replacement, collision, rename failure, unsupported
platform, publication-temp preservation, and staging preservation are covered.
It also covers sealed production dependencies, direct-root model markers,
exact integer schema fields, and normalized path/NFC/casefold aliases. Existing
sentinel acquisition units live in HoloIndex freshness-receipt tests. No test
opens a live Holo store.

Windows model-copy tests prove failed partial files and directories survive
after all handles close, the destructive APIs are absent from source/exports,
and query-level failure quarantines partial staging bytes intact.

This directory owns unit, contract, transport, lifecycle, and adversarial
coverage for the infrastructure bridge. Tests must be deterministic and must
not start or alter a resident HoloIndex owner unless a test explicitly owns
the disposable process fixture.

## Query replica materializer

- `test_reddog_holoindex_query_replica.py` uses only synthetic temp trees. It
  covers exact valid copy, canonical-byte preservation, deterministic
  descriptor ordering, source-hash change, receipt/generation swap, lease
  transition, overlap, link/reparse/hardlink/special rejection, resource
  bounds, preexisting targets, copy/hash/publication failure, and confined
  no-delete staging quarantine. Windows also proves a 622-file copy retains raw
  handles without exhausting CRT descriptors; large descriptor scans cover all
  600 items and still reject a secret in the final item.
- It never reads a live Holo store, starts an owner, loads a model, uses a
  network, or performs maintenance. Real symlink/FIFO cases may skip when the
  host cannot create them; injected reparse/special coverage remains mandatory.

## HoloIndex owner suites

- `test_holo_query_service_edges.py`: response normalization, global
  flattening, deduplication, zero-limit emptiness, canonical target/query/pair
  Tier-0 reservation, and missing/unrelated/ambiguous/multi/partial/mixed/
  duplicate/forged rejection.
- `test_holo_query_service.py` and
  `test_holo_query_service_embedding_generation.py`: semantic owner and
  generation/embedding binding.
- `test_holo_query_service_http.py` and
  `test_holo_query_service_fastapi_adapter.py`: authenticated transport.
- `test_holo_query_service_supervisor*.py`: private owner lifecycle, cold
  startup, and platform behavior.
- `test_holo_query_service_runtime_safety.py`: runtime confinement and
  mutation-safety boundaries.
- `test_reddog_holoindex_maintenance_handshake.py`: trusted refresh command,
  repository/receipt validation, exact query-replica route propagation, and
  owner restart orchestration; it also proves governed invalid runtime fails
  before spawn, child rejection precedes invalidation, and post-begin marker
  replacement cannot alter the process-local capability.
- `test_reddog_sealed_holo_runtime.py`: sealed/nonsealed runtime selection,
  hostile environment replacement, missing/ambiguous/link/partial authority,
  direct runtime-free compatibility, and exact process-image binding.
- `test_reddog_holoindex_owner_replica_route_resolution.py`: explicit absolute
  replica-root configuration, existing isolated-store proof, exact route build,
  and stable fail-closed error reduction.
- `test_reddog_holoindex_maintenance_diagnostics.py`: bounded child-output
  capture, strict stable-error propagation, cooperative descendant containment,
  failed-`taskkill`/escaped-session limits, exact-PID test cleanup, and secret-free
  failure behavior.
- `test_reddog_holoindex_acceptance_guards.py`: clean worktree authority,
  distinct clean related dependency runtime with verified local site-packages,
  disjoint/reparse-safe store, TOCTOU identity, canonical digest, and immutable
  secret-free publication contracts.
- `test_reddog_holoindex_acceptance_model_copy.py`: live per-file/aggregate
  bounds, descriptor artifact parity, and Windows proven-handle parent/root
  replacement rejection.
- `test_reddog_holoindex_acceptance_receipt_proof.py`: canonical-path,
  link/reparse/hardlink, bounded strict JSON/schema, descriptor identity/digest,
  exact SSD/root/SHA/generation binding, replacement, and revalidation proof.
- `holo_index/tests/test_isolated_collection_snapshot_runtime.py`: exact trusted
  runtime argv/cwd/environment, hostile environment scrub, pre-spawn runtime
  path rejection, package-origin proof, and pre-store version rejection.
- `test_reddog_holoindex_process_image.py`: actual OS process-image resolution,
  descriptor identity/final-path continuity, mutable-`sys` immunity, and
  missing/alias/link/reparse/hardlink/replacement denial, including Windows
  case-only parent-directory and leaf-name aliases under final-path casing.
- `test_reddog_holoindex_candidate_acceptance.py`: exact orchestration order,
  REFRESHED/direct-query binding, cleanup-before-supported activation,
  activation receipt/root/generation checks, post-activation rehydration and
  collection snapshots, environment restoration, atomic owned cleanup,
  canonical non-contamination, session locking, literal-port races, stable-error
  precedence, runtime forwarding/digest, and private-handoff ownership.
- `test_reddog_holoindex_candidate_acceptance_script.py`: default-inert CLI,
  required sixth absolute runtime path, pre-import parsing, explicit real-mode
  activation, stable JSON, and exit-code contracts.

## Focused execution

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
python -m pytest `
  holo_index/tests/test_tier0_retrieval_hardening.py `
  holo_index/tests/test_module_intent_snapshot.py `
  holo_index/tests/test_machine_spec_contract.py `
  modules/infrastructure/foundups_mcp_bridge/tests/test_holo_query_service.py `
  modules/infrastructure/foundups_mcp_bridge/tests/test_holo_query_service_edges.py `
  scripts/tests/test_reddog_holoindex_owner_query_once.py `
  -q
```

This focused matrix proves K=1/12/20 intent stability, low-K reservation,
catalog failure policy, Unicode-category/NFC duplicate rejection,
machine-spec binding, stable error/retry classification, ambiguous ordering,
invalid component rejection, strict fail-closed behavior for lookup exception,
cardinality corruption, and returned-path mismatch, plus non-strict safe
degradation. Tier-0 retrieval tests use fake collections and supplied fake
embeddings. They must not download models, mutate the persistent vector store,
reindex, or restart the resident RedDog owner. Record behavioral additions and
validation results in `TestModLog.md` per WSP 34.

The one-shot wrapper suite also proves pre-owner root-mismatch rejection with
zero attempts and process-owned `STARTED`/`REUSED` cleanup. Candidate acceptance
tests are dependency-injected; their activation and snapshot proofs never open
a real persistent store.

The R11 exact acceptance command uses the nine process-image, model-copy,
guard, receipt-proof, candidate, candidate-CLI, sealed-runtime, snapshot-probe,
and snapshot-runtime files listed above. On Windows it collected 146 tests:
143 passed and three symlink-creation capability tests skipped. New launch tests
prove a descriptor is live inside the injected runner, closes on success/error,
blocks launch after failed revalidation, and denies or survives path replacement
without changing the executed object. An actual retained-capability child smoke
also passes. Treat
collection, pass, and skip counts as separate fields; privilege-dependent skips
must never be restated as passes.

The exact six-file command above passed 278 tests in 4.00 s on the R3 candidate.
