## 2026-08-12: External authoritative-use lease regressions
- Proved exact grant-bound signing, strict request/instance/TTL checks, signer and audit verification, durable replay denial, expiry, one-shot parent authority, and opaque capability behavior.
- Proved strict socket v2 grant transport and retained grant-unaware/malformed rejection; the focused signer matrix and WSP 62 differential pass.
## 2026-08-11: Baseline contract reconciliation
- Proved the read-only bootstrap uses `AUDIT_NO_EFFECT`, persists a valid architect `FIX`, and emits zero executable queue candidates.
- Updated architect fixtures for prompt-bound WSP_15 allocation and one digest-bound intent across task, receipt, and runner.
## 2026-08-11: Bounded iterative grounding regressions

- Added deterministic refinement, deadline, root/generation drift, conservative
  broad-scope classification, v1 passive compatibility, and v2 rehydration.
- Proved replacement objects, hostile PATH/Git state, duplicate evidence,
  fabricated ledgers, budget abuse, and unscoped query hits fail closed.
- Proved exact-HEAD content reaches Fusion while dirty overlays, path widening,
  stale generations, or post-model proof changes cannot become evidence.
- Proved absent grounding, semantic scope widening, post-grounding WSP_15
  drift, rejected-byte budget abuse, and rehydration-module growth fail closed.
- Proved the E2E and signed-review adapters create genuine exact-HEAD grounding
  from their authorized target sets and reject missing or over-limit targets.
- Focused affected matrix is rerun and recorded at the exact reviewed SHA.

## 2026-08-08: Startup queue runtime-root regressions

- Proved the WRE queue bootstrap requires a valid runtime root, rejects
  out-of-root state, and receives the exact root/path pair from `main.py`.
- Focused queue-consumer and dependency-preflight matrix: 49 passed with two
  platform symlink skips.

## 2026-08-06: Principal Memex live resident source regressions

- Proved current-generation session splitting, principal-signed disclosure
  admission, exact cycle/model/revision binding, expiry, revocation, durable
  replay, duplicate-cycle handling, and no audit-worker disclosure.
- Proved concurrent editor calls cannot resurrect a consumed packet; only an
  explicit `consumed=false` acknowledgement permits retry, while missing or
  failed acknowledgements retire the local packet.
- Proved direct statement reproduction rejects and paraphrased model text is
  absent from durable determinations, proposal admission, and queue output.
- Verification: focused Principal Memex/session/manifest matrix `95 passed`;
  `node extensions/reddog/tests/test_principal_memex_disclosure_source.js`
  PASS; exhaustive extension contract PASS; backend manifest `1239` files.

## 2026-08-06: Exact-request signer policy regressions

- Replaced arbitrary policy-less signer success fixtures with fail-closed
  assertions for direct, socket, key-provider, one-shot, and multi-profile
  runtime paths.
- Proved exact E0 request binding accepts only the original request, cannot be
  rebound, and rejects identity/work-authority domain confusion.
- Preserved grant replay, concurrency, revocation, expiry, specialized policy,
  public-key verification, and WSP 62 bounds.

## 2026-08-06: Conversation scope-kind boundary regressions

- Proved principal scope persists and resumes without FoundUp grounding, can
  advance only with non-operational state, and cannot enter work promotion.
- Proved comparison scope requires two credential-authorized FoundUps, creates
  no union authority, and cannot enter work promotion. E0 signing binds the new
  scope kind; extra FoundUp scope, seal widening, null/string type coercion,
  and malformed nested records reject before signing.

## 2026-08-06: Durable conversation authentication regressions

- Proved E0-signed scope records survive AgentDB and signer-anchor restart while
  raw principal credentials never enter either durable artifact.
- Added exact-state tamper, forged/stale credential, wrong signer key/epoch,
  cross-domain request, unavailable dependency, rollback/fork, nonce replay,
  concurrent successor, and no-write-on-signing-failure coverage.
- Added later-clock crash recovery, no-anchor rejection, and exact outage retry.
  Regressions also cover rehashed pending state, bounded signer heads,
  kernel-attestor composition, current-generation principal revocation,
  and lease-active resolver calls.
- Added proposal-preview crash recovery after signer-anchor commit, including a
  competing conversation writer denial and proof that restart recovery performs
  no second signer action before atomic AgentDB finalization.
- Extended signer config/runtime tests for principal resolution, confined
  anchors, exact policy binding, and bounded request sizing.
- Proved legacy HMAC never uses pending recovery; precommit failure leaves no
  stranded row, retry succeeds, and `require_replay` remains forbidden.
- Added exact WSP 62 AST coverage for authentication sources and tests.
- Added review regressions for state overwrite and artifact collisions.
- Added exact nested-schema regressions for model selection/runtime receipts,
  WSP 15 allocations, proposal admission, operational context, list members,
  and malformed present values.
- Proved nested model-selection and runtime-policy injection cannot publish an
  authority profile or create a queue item, claim, or promotion record.
- Proved attacker-rehashed list/map type confusion cannot write a source,
  publish or recover a profile, reach queue materialization, or pass the live
  canary profile reader. The source and effect projections do not coerce data.
- Added security-review regressions for `denied_paths: null`, false nested
  no-effect assertions, and malformed runtime digests. The resident queue
  bootstrap preserves authoritative work-state bytes and emits no chain result
  when the legacy effect projection is malformed.
- Added real single-model and panel promotion regressions to preserve canonical
  nullable aggregate and topology bindings under strict profile validation.

## 2026-08-05: Current-generation use-time trust regressions

- Added real root-owned selection round-trip tests plus changed config,
  changed run-packet, expiry, and wrong-runtime rejection coverage.
- Proved the use-time resolver removes only the authenticated-manifest,
  replay/high-water, and current-generation blockers after a typed accepted
  receipt. Public mappings, rejected results, absent or malformed receipts,
  and dependency exceptions remain fail-closed; peer-handshake remains named.
- Added trusted-clock manifest freshness, malformed binding, external-issuer,
  changed-byte, wrong-root, and zero-effect regressions.
- Focused matrix: 17 passed with one platform skip. Changed-module matrix:
  161 passed with two platform skips. WSP 62 and manifest enforcement:
  21 passed.

## 2026-08-05: Upstream agent runtime provenance regressions

- Added a strict v2 schema and independent integration-ID allowlist for the
  OpenClaw Gateway and Hermes API upstream claims.
- Added regressions for local-name relabeling, fabricated upstream providers,
  provider substitution, unknown fields, documentation-only evidence,
  absolute/traversal/missing paths, and source-marker drift.
- Proved every existing manifest entry resolves to a checked-in regular file,
  no current upstream hook is claimed, no production source consumes the
  static ledger as authority, and local adapters cannot satisfy an upstream
  runtime requirement. Source invocation checks use AST rather than comments.
- Added exact owner and runtime-origin definition checks, distinct Hermes-local
  control contracts, bounded common-field validation, and a repository-wide
  executable-source scan proving the static ledger has no runtime consumer.

## 2026-08-04: Verified-outcome root authority regressions

- Added signer-instance proof, live UID/GID rotation, dual-store reset,
  one-step crash repair, unsafe ancestry, malformed-client continuity, and
  production test-mint absence regressions.
- Added third-domain installation replay, validation-before-generation,
  pre-open ancestry, pre-read peer attestation, cross-process CAS, and one-time
  provisioning entrypoint regressions. Linux root CI also exercises the real
  Unix socket with a demoted non-root signer process.
- Added exact descriptor, root-owner, signer-generation, verifier-class,
  co-signature, expiry, revocation, scope, and lineage validation coverage.
- Added all-field three-store rotation rejection, generation-fence preservation,
  and pre-key Linux signer isolation regressions for UID separation, YAMA,
  capabilities, core dumps, dumpability, and inherited environment.
- Proved attacker-rehashed grant changes, unknown verifier classes, authority
  collapse, wrong owner/session, alternate or reset replay stores, direct
  capability construction, and forged reservations reject.
- Proved co-signed grants cannot be transplanted across issuer, RedDog,
  consensus, signer key epoch, or signer run/config/session/manifest/generation
  contexts even when the descriptor ID is recomputed.
- Proved all public key-provider constructors reject non-root and unregistered
  same-type outcome authority before secret resolution, plus duplicate grants,
  stale/future signed grants, held-out-key revocation, and wrong reservation
  scope/time fail closed.
- Proved one exact grant survives restart and eight concurrent reservations
  produce exactly one winner.
- Proved a signer process observes a root-config revocation written after
  startup, and that grant expiry uses current signer time rather than the
  caller's signed-request timestamp.
- Proved one v2 snapshot supplies manifest, lazy authority, owner ID, and UID/GID;
  absent policy never touches the root socket, configured policy binds after
  isolation, and missing, raised, or mismatched suppliers reject before service.
- Proved the checked-in backend manifest includes the root-authority module
  through the stable signer entrypoint's dependency closure.

## 2026-08-04: Verified-outcome runtime authority regressions

- Added durable publication/rehydration tests for exact verifier and held-out
  receipts, isolated-signer evidence, committed-profile key resolution, revocation,
  freshness, and every required FoundUp/snapshot/head/content/work/slice/job/worker/
  verifier/runtime binding.
- Proved attacker-rehashed records and envelopes, wrong keys, missing durable
  sources, caller booleans, stale evidence, replay, and cross-process replay reject.
- Added resident assembly, queue publication, signer policy, and session-bootstrap
  tests; concurrent consumers admit exactly one capability.
- Exact-SHA review added fail-closed regressions for absent signer-side outcome
  authority, signing-request replay, missing production queue bindings, staged
  envelope activation, zero PatternMemory writes on publication failure, atomic
  multi-capability Brain admission, and trusted use-time clocks. Production
  activation remains blocked because no independently authenticated durable
  verifier-authority source exists.
- Security re-review removed hash-shaped legacy authorization, proved staged
  PatternMemory rows are invisible, exercises the injected orchestration retry,
  and rejects a pre-seeded conflicting row instead of trusting its record identifier.
- Added direct-store, publisher-free bootstrap, and OpenClaw queue-worker
  regressions. The real PatternMemory sink remains non-activation-ready pending
  an independently revalidated durable authority source.
- Split signer-domain and adversarial outcome tests into focused modules, and
  changed legacy full-chain fixtures to assert the production stop before
  unauthenticated PatternMemory activation. No security assertion was removed.
## 2026-08-04: Memex supply authenticity regressions

- Added exact receipt round-trip, unknown-field/type, lineage, scope, expiry,
  timezone, maximum-age, maximum-lifetime, and boundary tests.
- Added promotion-level proofs that fabricated `sha256:` IDs and
  attacker-rehashed Memex substitutions cannot mutate authoritative work state,
  while valid promotion binds the complete canonical Memex receipt digest.
- Added proposal-builder, resident-handoff, and authority-seed regressions that reject
  malformed serialized receipts before signer effects; added outcome-source schema/ID,
  substitution, rehash, signature, scope/head/freshness/replay, and capability tests.

## 2026-08-03: Upstream Hermes complete-event-history confinement

- Added regressions proving a completed poll result cannot hide an earlier
  tool, approval, or subagent event; run ID, terminal event, and output must
  match the complete upstream SSE event history.

## 2026-08-02: Upstream OpenClaw and Hermes fail-closed provider gate

- Added fail-closed provider, command-transport,
  canonical-mode, signed-model-binding, queue-admission, and receipt-truth
  regressions for the actual OpenClaw CLI/Gateway and the production-blocked
  Hermes mode.
- Proved malformed output, unsafe exact-session sandbox state, duplicate JSON,
  indeterminate timeout/termination, forged effect fields, unknown modes, and
  unsupported Hermes identity reject before repository materialization.
- Configured and verified the current installed OpenClaw loopback Gateway and
  dedicated `reddog-artifact` agent. The repository adapter's real preflight
  passed with a version-matched Gateway, exact-session sandbox, canonical
  read-only sandbox workspace mount, wildcard tool deny, and no elevation.
- Added semantic receipt-forgery, invalid nested effect receipt, truthful
  Fusion network-effect, and uncertain OpenClaw abort regressions. Hermes is
  current but unconfigured and remains production-blocked.

## 2026-08-02: HoloIndex incident repair runtime

- Command: `pytest -q test_reddog_holoindex_incident_repair_runtime.py test_holoindex_postmerge_coordinator.py test_reddog_start_operations_holo_repair.py test_generate_reddog_backend_manifest.py`
- Status: PASS (`59 passed`; owner-query bridge `18 passed`).
- Coverage: caller and receipt forgery, independent owner recheck, exact-HEAD/root WRE task
  reuse, retry/cooldown deferral, current-generation owner proof, escalation,
  strict primitive/digest boundaries, active-task deferral, startup-exhaustion
  receipts, and no direct model/shell/index invocation.

## 2026-08-01: HOLOINDEX POST-MERGE OWNER ACTIVATION

- Proved the exact-SHA post-merge coordinator schedules by default and can be
  explicitly disabled with visible `OWNER_DISABLED` telemetry.
- Proved general maintenance remains off by default while canonical
  `holoindex_postmerge_coordinator` tasks remain eligible for the bounded
  maintenance executor.
- Proved unrelated self-audit maintenance cannot ride the default HoloIndex authority path.
- Proved generic autonomous task execution cannot claim or bypass the
  claim-bound HoloIndex post-merge executor.
- Proved global top-10 pressure cannot hide post-merge tasks and shutdown waits before rejecting rescheduling.

## 2026-07-31: STABLE SIGNER SYSTEM-SERVICE ENTRYPOINT

- Added socket-v2 and E0 regressions for exact grant/request/peer binding,
  v1 grant-smuggling rejection, durable restart replay, alternate-store
  substitution, permission drift, resolve-per-sign WSP71 key access, and zero
  serialized secret material or execution primitives.
- Proved revocation/signing linearization, expiry during resolution or signing,
  signer-response signature verification, provider identity checks, strict
  replay-store configuration, and bounded WSP 62 parser/backend functions.
- Stable service composition remains fail-closed and grants no work authority.

## 2026-07-31: CURRENT-GENERATION SIGNER LAUNCH SELECTION

- Added focused regressions for generation-bound content-addressed manifest
  selection, canonical signature and audit-attestation verification, all-seven
  live artifact byte checks, caller-manifest substitution, activation-binding
  mismatch, stale/future manifest rejection, short-lived selection expiry,
  capability forgery/replay, and missing manifest rejection.
- Added the new selector and test module to the exact signer WSP 62 gate.
- Added descriptor-bound root-owned Linux/WSL owner-config reconstruction,
  tamper, caller-path, owner-root overlap, platform fail-closed, opaque owner
  authority, public-CLI injection denial, exact generation-selection shape, and real
  parser-to-loader-to-bootstrap CLI regressions. The real CLI proof confirms
  one resolver/service call on acceptance and zero calls for stale evidence.
  Production bootstrap rejects the legacy nine-field selection downgrade.
  Privileged Linux regressions cover root-owned success, wrong UID, writable
  roots/files, symlinks, directory replacement, and full CLI admission.
- Focused signer/manifest/generation/lifecycle matrix: 176 passed, 8 platform
  skips, including WSP 62. Six privileged ownership cases skip on Windows.
- Proposal/signer-policy compatibility matrix: 23 passed after upgrading its
  test-only launch fixture to the generation-bound selection.

## 2026-07-31: SIGNER RUNTIME ATOMIC PROVISIONING
- Added focused coverage for final-root manifest publication, last-step
  authenticated generation activation, missing/tampered artifacts, independent
  anchor placement, replayed generations, create-only manifest publication,
  activation compare-and-swap failure, concurrent work-state refresh,
  activation-window direct-write denial, fake anchors, and no service or
  execution authority.
- Added canonical signer-witness namespace, rollback-domain separation,
  restart-substitution, concurrent first-open, and signer-side SQLite
  compare-and-swap regressions.
- Reviewer repair added post-commit recovery, caller-independent read-only
  witness state, per-open metadata checks, strict rollback, manifest
  signature/byte preservation, POSIX external-owner, canonical-verifier, forged-signer rejection, closure-substitution, and typed committed-witness restart regressions.
- Focused provisioning, generation, activation-lease, commit-guard, and
  monotonic-witness matrix: 115 passed, 2 platform skips, including a real
  two-process race. POSIX activation is an intentional fail-closed skip.
- Manifest, generation anchor/reader/high-water, lifecycle admission and race
  matrix: 185 passed, 2 platform skips.
- Complete `test_reddog_*signer*.py` plus activation-lease matrix: 426 passed,
  13 platform skips.
- Full bridge differential: untouched base `4784 passed, 27 failed, 23
  skipped`; repaired branch `4848 passed, 28 failed, 24 skipped`. The 27
  baseline failures are shared. The candidate-only AgentDB concurrency
  failure passed 10/10 isolated reruns, so the slice adds 64 passing tests,
  one intentional POSIX fail-closed skip, and no reproducible regression.

## 2026-07-31: REDDOG SIGNER MANIFEST AND LIFECYCLE FOUNDATIONS
- Proved Ed25519 manifest signing plus content-addressed no-replace
  publication for all seven canonical runtime artifacts.
- Proved authenticated generation compare-and-swap plus opaque
  high-water rollback checks across restart and concurrent writers.
- Unit-proved Linux PID/start/executable device/inode, exact argv,
  requester identity and process-owned socket fail-closed parsing.
- Proved exact manifest, generation, raw config, packet, policy,
  profile, observation and v2 signed-handshake lifecycle admission.
- Proved copied, serialized, forged, stale and replayed
  process-local tokens reject; consumed receipts grant no effect.
- Proved packet, config and observer tampering reject fail closed.
- Proved protected-parent cleanup preserves an attacker-substituted
  socket path rather than deleting another lifecycle object.
- Proved post-mint `setattr` and `object.__setattr__` attacks cannot replace
  verifier, reader, high-water, or hidden-signer dependencies in any
  lifecycle authority object.
- Proved lifecycle callables and reader/verifier registries are not exposed as
  module-global mutation surfaces; deleting a signed anchor still fails closed.
- Proved public generation and lifecycle APIs expose no caller-supplied
  registry lookup or issuance parameter and reject forged-hook injection.
- Proved generation advancement during observation or before capability
  consumption rejects rather than admitting stale lifecycle evidence.
- Kept service provisioning, valve consumption and live
  execution fail closed behind separately owned follow-ons.
- Focused signer, manifest, safety and WSP 62 matrices remain
  mandatory before exact-SHA publication.
  Kernel-backed distinct-principal Linux integration remains required.

## 2026-07-30: ARTIFACT MODEL AUTHORITY WSP 62 DECOMPOSITION
- Moved model-runtime, provider-capability, and bounded-worker adversarial cases
  into focused test modules without dropping assertions.
- Legacy matrices now remain below their prior line counts or the 675-line
  module boundary; new test functions remain within WSP 62 limits.
- Focused authority and AI Gateway integration matrix: 996 passed, 5 skipped.

## 2026-07-30: REDDOG_EXACT_SHA_AND_ARTIFACT_MODEL_AUTHORITY_REPAIR
- Restored `exact_sha_commit` and required verified production model evidence, exact topology, and signed authority at artifact-generation use time.
- Added fail-closed regressions for missing exact-SHA state, self-rehashed evidence, authority substitution, capability forgery, replay, and bypass.

## 2026-07-29: REDDOG_START_OPERATIONS_HOLO_REPAIR_RESUME_PHASE1
- Proved the canonical operations profile performs a semantic owner query, making failed/stale Holo evidence reachable by repair.
- Proved one-shot capability, forgery/replay rejection, exact assignee/context/HEAD binding, expired-assignment CAS recovery, execution proof, and truthful refresh telemetry.
- Proved repair failure and a failed second grounding attempt never construct the resident model client.

## 2026-07-28: REDDOG_FOUNDUP_MEMEX_AUTHORITY_DISPATCH_BINDING_PHASE1
- Added end-to-end Memex authority and request-integrity regressions for pair
  propagation, malformed/falsy values, conflicts, and digest-alias tampering.
- Proved pre-signing request substitution and rehashed post-signing authority
  substitution reject before signer, store, evidence-runner, or worker effects.
- Proved mixed current absent Memex encodings normalize to an unsigned
  `None/None` request instead of raising during authority planning.
- The signer, dispatch, claim, executor, verifier, and serial matrices stay green.
- Full differential evidence remains mandatory before publication.

## 2026-07-27: REDDOG_ARCHITECT_PROPOSAL_ATTESTATION_PROMOTION_BINDING_PHASE1
- Added adversarial regressions for self-minted principal keys, altered proposal
  and policy signatures, caller identity/path/operation/permission substitution,
  test-only signer mode, stale/revoked/current-binding drift, signer-context
  substitution, missing trust, and file-backed replay after process restart.
- Proved that both signed IDs/digests and the signer-runtime context digest
  reach the claim, queue item, promotion record, receipt, authority profile,
  and operational context. Modernized authority-source fixtures to use valid
  Ed25519 identities and complete SHA-256 receipt digests.
- Proved crash/tamper/altered-retry rejection, exact retry, confinement, secret
  rejection, history/replay preservation, and inert-profile non-activation.
- Proved attacker-recomputed receipts cannot advance authority; exact
  allowlisted dispatch schemas reject caller-added identity or metadata before
  nonce consumption, and AgentDB receives only canonical receipt/intent
  projections plus principal identity from the reverified signed authority.
  PREPARED rolls
  back while preserving concurrent refresh data and requires a fresh retry.
- Proved one-of-two concurrent commit, cache rehydration, immutable-orphan preservation, canonical locking, PREPARED rejection before authority-request persistence, signer invocation, AgentDB enqueue, valve, and signer effects, mandatory explicitly selected durable state at both signer consumers, serial and one-shot current-state reload, signed current-revision publication binding, and exact verified-work-authority digest and verification-receipt handoff through dry-run intents, runtime receipts, and AgentDB task context. AgentDB admission now binds work order, FoundUp, operation, and exact roles/capabilities to the signed authority and authoritative WSP 15 plan, consumes the durable nonce exactly once, preserves it on static rejection, and requires fresh authority after a post-admission writer failure. Missing recorded stages or verifier/clock dependencies, synthetic accepted dry-runs, altered proof fields, split-path/marker-and-binding removal, authority substitution, attacker-recomputed receipts around a forged signature or substituted operation, role substitution, replay, stale time after context construction, and stale injected state without a signer-config artifact all reject before effects; proposal test credentials are minted per test invocation so full-suite duration cannot expire them before use.
- COMMITTED proves local integrity, not late-bound publication authentication.
- Authenticated activation remains a later signer-owned slice.

## 2026-07-27: REDDOG_AUTHORITY_RUNTIME_STORE_CONFINEMENT_PHASE1
- Added missing/outside-root, repository ancestry, mixed namespace, symlink,
  hard-link, parent-swap, concurrent compare-and-swap, nonce-consumption,
  signer-config/anchor, and live-canary regressions for explicit root binding.
- Added rejected-alias payload scrubbing, post-replace rollback, exact receipt
  runtime-root propagation, schema-v2 control-authority, root-separation, and
  direct-child config regressions. The affected bridge suite passed 157 tests
  with seven platform skips; shared safety, startup, and WSP 62 gates passed
  38 more tests with one platform skip.
- Added intervening-revision rejection, interrupted-write recovery, escaped
  socket, and nested-anchor regressions; the expanded bridge gate passed 168
  tests with seven platform skips before final independent review.
- Added exact-expected-revision recovery, self-consistent forged-backup
  rejection, linked/oversized backup rejection, and post-nonce revision
  recovery regressions. Required run-packet fixtures now carry the canonical
  runtime, signer, anchor, and authority-policy bindings and reject every
  missing or malformed nested binding or provider profile. Config supply now
  proves that malformed Ed25519 public keys fail before write and that every
  accepted config passes canonical run-packet admission. Final local gates:
  210 bridge tests passed with eight platform skips, 14 shared-safety tests
  passed with one platform skip, 21 startup tests passed, three WSP 62 checks
  passed, 42 red-team tests passed, and 200 Windows authority commits left no
  temporary or backup artifacts.

## 2026-07-27: Architect proposal executability admission
- Added adversarial coverage for valid-but-blocked prerequisite slices,
  produced-capability self-authorization, model readiness forgery, INDEX_GAP
  handling, HoloIndex maintenance exceptions, Windows live-canary blocking,
  path traversal, receipt tampering, rehashed capability under-declaration,
  noncanonical candidate IDs, current-HEAD drift, current-Holo generation
  drift, exact base-SHA binding, precommit-write atomicity, profile rollback,
  rollback compare-and-swap, active-owner generation mismatch, work-state
  revision drift, and mutation-free module imports.
- Updated backend architect and signed WSP 15 promotion fixtures to carry the
  canonical proposal-admission lineage while keeping production trust-anchor
  discovery fail closed.
- Focused and startup/runtime validation: 276 passed, one platform skip, and
  one pre-existing Memex assertion deselected after reproducing it on clean
  `origin/main`. Simulator CI parity passed 302 tests; red-team passed 42.

## 2026-07-27: Main-menu resident binding preflight regression
- Proved missing bindings skip the client and return WARN/True by default versus FAIL/False when enforced; the focused startup suite passed 92 tests with one platform skip.
## 2026-07-26: Independent assurance capacity admission
- Proved the bootstrap persists assurance admission and yields before bounded
  author or verifier execution.
- Proved queue-stage workers cannot claim or materialize the bounded coding
  stage, while separately claimed author and verifier tasks complete the
  chain in order.
- Proved author failure revokes held assurance and stage-ready expired
  verifier capacity uses one bounded renewal.
- Added review regressions for rejected upstream stages, missing stores,
  renewed admission-digest lineage, and terminal receipt bindings.
- Verified the modified bridge, AgentDB, and WRE integration set with 405
  passing tests and three platform skips before final static validation.

## 2026-07-25: Daemon self-audit runtime nudge alignment
- Proved current external escalation records produce memory events.
- Proved the obsolete in-repository JSONL is ignored and an in-repository
  runtime-root injection fails closed.
- Proved producer/consumer resolver parity across default, resident, relative,
  and explicit-precedence modes.
- Proved oversized and identity-changing escalation files fail closed without
  using an unconfined `Path.read_text` call.

## 2026-07-25: RedDog HoloIndex receipt-bound evidence regression repair

- Updated four older owner-client fixtures to carry the repository-root digest required by the landed authority-root contract.
- Restored proof of poison-restart, missing-generation, and post-query repository-change behavior without weakening runtime validation.

## 2026-07-25: RedDog HoloIndex authority-root client proof

- Added transport regressions proving expected-root transmission and foreign-root response rejection.
- Preserved local-store avoidance, loopback authentication, redirect denial, deadline, and direct-query boundary coverage.

## 2026-07-25: Authoritative work-state query

- Added eleven focused regressions for accepted governed state, revision
  tamper, staleness, selected-slice conflict, invalid WSP 15 allocation,
  missing governed lineage, repo-internal state, and prohibited imports.
- Added extension-side classification, bridge-failure, receipt rendering, and
  no-Fusion ordering coverage.

## 2026-07-25: Main resident canonical-client review repair

- Added regressions proving status cannot re-arm FIX/queue handoff and
  status/cancel/resume clients receive only the selected FoundUp scope.
- Added a real SQLite AgentDB regression for the exact pre-#1310
  `cycle.v1 + main intent.v1` shape: authenticated status and CAS-cancel pass,
  while resume remains rejected.
- Preserved exact audit/architect runtime-binding receipt assertions after
  rebasing onto the current resident runtime.
- Extracted the 201-line root preflight into decomposed moltbot-owned
  functions and asserted the root adapter and critical bootstrap functions
  remain below their WSP 62 thresholds.
- Validation after review repair: 159 focused tests passed with one platform
  skip, including exact WSP 62 no-growth coverage.

## 2026-07-24: HOLOINDEX_QUERY_ROOT_ADMISSION_P0_PHASE1

- Added direct regressions for pre-backend foreign-root denial and rejection
  of a noncanonical external receipt before repository evaluation, receipt
  admission, or backend access. Canonical receipt and maintenance locations
  are SSD-derived by the current adapter code.
- Unfiltered admission/confinement/direct matrix passed 62 with five portable
  symlink skips; owner passed 60/60; wider retrieval passed 126 with four
  portable symlink skips; WSP_62 guards passed 19/19.

## 2026-07-23: REDDOG_PROVIDER_CALL_EVIDENCE_PHASE2A_REVIEW_REPAIR_ROUND3

- Added requested-provider and requested-model secret/raw-shape rejection at
  receipt creation and direct validator rehydration.
- Expanded audit and architect adversarial matrices across surface, task,
  work-order, queue, run, cycle, runtime receipt/digest, requested
  provider/model, attempted state, and terminal outcome.
- Updated integration fixtures so valid receipts carry only binding-derived
  lineage; no test-only extra lineage is accepted.
- Consolidated gate: `274 passed, 1 skipped`; Fusion/architect family:
  `64 passed`; modular-audit suite: `16 passed`.

## 2026-07-23: REDDOG_PROVIDER_CALL_EVIDENCE_PHASE2A_REVIEW_REPAIR_ROUND2

- Added adversarial provider/model parser cases for URI, drive/path traversal,
  dot segments, query/fragment, bearer-like, high-entropy, and raw sentences,
  plus documented OpenRouter-style identifiers.
- Added direct audit and architect extraction-failure cases using a raising
  `__str__` value and an unreadable evidence store; attempted local evidence
  remains truthful.
- Added omitted, forged-surface, wrong task/cycle, wrong runtime-binding
  ID/digest, and non-completed evidence rejection at both acceptance consumers.
- Added a hard-coded frozen legacy-v1 progress receipt and a platform-neutral
  Windows/POSIX WSP 62 exemption-key regression.
- Exact WSP 62 tests now require the complete measured set of every touched
  communication function over 60 lines.
- Consolidated post-repair suite: `252 passed, 1 skipped`; Fusion/architect
  family sweep: `57 passed`; modular-audit unit suite: `16 passed`.
- Whole bridge diagnostic: `3976 passed, 17 skipped, 51 failed`. The remaining
  failures are unrelated optional-dependency, external-fixture, grant/skill
  environment, or pre-model bootstrap/runtime-binding cases.

## 2026-07-23: REDDOG_PROVIDER_CALL_EVIDENCE_PHASE2A_REVIEW_REPAIR

- Added adversarial served-identity cases covering credential-shaped values,
  whitespace, controls, and JSON-like raw content, plus valid OpenRouter-style
  provider/model identifiers.
- Added direct audit and architect regressions where the provider was invoked,
  terminal persistence failed, and the store was unreadable; both retain
  attempted INDETERMINATE lineage and truthful network-call status.
- Added accepted architect receipt/queue-parent substitution coverage and a
  final audit-rejection provider-evidence linkage regression.
- Focused provider/architect/audit/WSP62 suite: `117 passed`.
- Fusion progress receipt suite: `13 passed`.

## 2026-07-23: CREATE_FOUNDUP_ROUTING_PREREQUISITE_WSP62_REPAIR

- Extended the module exemption regression to require the canonical
  `src/foundup_job_contract.py` exact 796-line no-growth ceiling.
- Cross-module WRE regression checks its POSIX key, metadata, expiry,
  remediation authority, and exact source size.

## 2026-07-23: CREATE_FOUNDUP_ROUTING_PREREQUISITE_PHASE1

- Added `test_foundup_job_create_lineage.py` with a canonical
  factory/serialization round-trip test for
  `creation_mode`, `genesis_envelope_digest`, and
  `scaffold_contract_digest`.
- Added a legacy serialized-job regression proving absent lineage fields
  remain readable and round-trip with nullable defaults.
- Focused lineage file: 2 passed. Adjacent contract/E2E run: 89 passed and 3
  pre-existing missing-manifest failures remained outside this route.
- Included in the focused cross-module contract/router/consumer run:
  145 passed.

## 2026-07-20: REDDOG_REQUIRED_RUNTIME_MODEL_BINDING_REVIEW_REPAIR_PHASE1

- Added worker and architect same-surface substitution regressions with zero
  model/index/store calls, plus selection-only and injected-runner rejection.
- Added resident and direct E2E substitution seams proving unchanged durable
  state, no new tasks, and no downstream runner/index/persistence activity.
- Added real startup artifact tests for missing paths, malformed JSON, wrong
  surfaces, same artifact reuse, oversized/non-regular files, outside-root and
  inside-repository paths, and no-follow symlinks where the platform permits.
  Every rejection occurs before the cycle mock and emits no configured path.
- Focused affected runtime suite: 205 passed / 1 platform skip. The skip is
Windows symlink creation when unavailable; the no-follow behavior remains
covered by the shared confined-reader contract.

## 2026-07-20: REDDOG_REQUIRED_RUNTIME_MODEL_BINDING_PHASE1

- Added digest/rehydration-valid test receipts for receipt-selected panel
  topologies and used GLM-5.2 principal plus Kimi K3 critic only as receipt-bound test
  fixture identities, never as production policy.
- Covered exact WSP 15/swarm/assignment/AgentDB propagation, durable resident
  audit and architect forwarding, architect determination lineage, and
  absent/wrong-surface/selection-only rejection before provider invocation.
- Preserved direct injected-runner tests and verified the production runner
  provider stubs receive the exact receipt topology.
- Focused runtime gate: 184 passed. WSP 62 exemption gate: 2 passed; no ceiling
  increase was required.

## 2026-07-20: REDDOG_EXECUTION_VALVE_INDEPENDENT_REVIEW_REPAIR_PHASE1

- Added signed `base_ref` and canonical full-work-order digest mutation tests
  across authority issuance, use-time reconstruction, executor plans, opaque
  admission, and the effect runner.
- Added a race regression that mutates the work order during admission and
  proves the runner still receives only the previously validated plan ref.
- Added fresh-clock terminal-authority regressions for identity and permission-
  snapshot expiry after preflight and before authoritative nonce consumption.

## 2026-07-20: REDDOG_TRANSPORT_NEUTRAL_REPO_AUDIT_FALLBACK_PHASE1

- Covered `pfmall`, `p.fMALL`, `p-fmall`, and `PFMALL` owner-unavailable audits.
- Proved owner-first ordering, CURRENT-owner short circuiting, stable-HEAD
  binding, source-plus-test enforcement, private/generated-root pruning, and
  no-model/no-shell fail-closed behavior.
- Added nested receipt tamper and fully rehashed private/traversal path
  substitution regressions; retained the shared discovery suite for link,
  reparse, identity-race, bounded-read, and deterministic ordering coverage.
- Added independent-review reproductions for fully rehashed safe unrelated
  source/test substitution, category/search/audit/coverage/policy/no-action
  changes, selected-count and aggregate-byte overruns, and `.worktrees` paths.
- Added deterministic and model-backed consuming-read regressions for exact
  path/digest/bytes/truncated equality, including unstaged changes before the
  worker and during model execution while HEAD remains unchanged.

## 2026-07-20: REDDOG_EXECUTION_VALVE_RECONCILED_TRUST_BOUNDARY_PHASE1

- Added canonical reader/writer lock parity tests using the real work-state,
  authority-profile, resolver, permission/principal, and valve writers.
- Preserved authenticated control-receipt prestate adversaries while updating
  post-run assertions to the permanent production-CLOSED verifier boundary.
- Reconciled current resident fixtures with independently confined runtime
  roots and canonical governed artifact packs; refreshed exact no-growth gates.

## 2026-07-20: Main resident canonical-client migration

- Added main-host v2 grounding/source/origin round-trip coverage.
- Added fail-closed tests for missing/mismatched host scope, cancel/retry conflicts, control without an existing intent, and grounding failure before client construction.
- Proved explicit intent status bypasses new grounding and `main.py` no longer references the durable cycle runner directly.
- Rejected the removed `reddog_intent.v1` main-host compatibility shape.
- Validation: 125 focused canonical-client, grounding, durable-cycle, and main startup tests passed before independent review.

## 2026-07-19: REDDOG_HOLOINDEX_V2_RUNTIME_FIXTURE_MIGRATION_PHASE1

- Replaced stale positive HoloIndex v1 receipt fixtures with one canonical v2 helper that builds complete source-manifest, scope, policy, and collection-snapshot proofs.
- Migrated operational snapshots, FoundUp Brain, Memex supply, OpenClaw audit planning/enqueue, backend architect determination, readonly bootstrap, end-to-end audit decisions, and the durable resident cycle.
- Preserved the intentional v1 query-boundary compatibility adversary.
- Validation: 150 focused runtime tests passed; the full bridge suite reached
  3,749 passed / 8 skipped with 39 unrelated baseline/environment failures.

## 2026-07-19: REDDOG_TRANSPORT_NEUTRAL_GROUNDING_SERVICE_PHASE1

- Added target-classification, receipt self-validation, current/stale generation, semantic support/corroboration, quoted-data isolation, and repo-path safety tests.
- Added resident-client FoundUp scope rejection before canonical cycle invocation.
- Adversarial regressions cover blockquote/fence loss, `.env` punctuation stripping, traversal, absolute paths, and unrelated two-category HoloIndex decoys.
- Added cross-language fixture parity against the live editor extractor so backend and extension target classes cannot drift silently.
- Validation: 128 resident/grounding/OpenClaw/architect tests passed; Python compile and diff checks passed.

## 2026-07-19: REDDOG_TRANSPORT_NEUTRAL_RESIDENT_CLIENT_AND_HERMES_ADAPTER_PHASE1

- Added resident-client tests for canonical-cycle use, status-only reconnect, cancel/retry, principal/source mismatch, runtime-key injection, stored-record substitution, and read-only boundary contradiction.
- Added fail-closed coverage for omitted canonical safety attestations.
- Re-ran the durable AgentDB cycle suite to preserve canonical OpenClaw audit execution behavior.
- Validation: 17 focused client/cycle tests and 113 resident/OpenClaw/architect tests passed.

## 2026-07-18: REDDOG_RESIDENT_CONTROL_RECEIPT_TRUTH_AUTH_CONCURRENCY_PHASE1

**Files**: control-receipt auth/context, signer, canary, chain-store, OpenClaw,
and `main.py` focused suites.

**Coverage**:

- Signed receipt round-trip, field/signature/key/profile tamper rejection,
  unsigned-live rejection, duplicate cycle/nonce rejection, and v1-prefix to
  signed-v2 migration.
- Dedicated signer operation/domain validation rejects malformed payloads and
  control-domain confusion.
- Concurrent thread/process appends preserve valid JSONL; concurrent chain CAS
  produces one commit and one revision conflict.
- Distinct signed cycles serialize without lost updates while same-cycle races
  produce exactly one commit; direct supervisor and resident-main contention
  is rejected before AgentDB claim.
- Whole-chain verification rejects unsigned/foreign predecessors, reordered or
  tampered rows, mutable audit MACs, child-cardinality mismatches, duplicate
  child receipts/evidence, and signer role/tier/profile-policy violations.
- Malformed receipt streams block before model/worker invocation; live proof
  revalidates the exact authority profile and signer epoch.
- Truth counters distinguish worker execution from observed OS-process spawn,
  and stage observations replace hardcoded no-effect claims.
- Updated serial-loop fixtures prove the runtime-artifact root remains outside
  the synthetic repository without weakening the production confinement gate.
- Signer-policy tests reject missing/mismatched principal, key epoch,
  consensus, promoted-profile, or source-receipt bindings; anchor tests reject
  resident rollback, anchor tamper, and reused child evidence.
- Complete child evidence tests recompute every digest and reject changed body,
  execution truth, order, projection, or receipt linkage before parent signing.
- Regression cases reject caller-inflated parent effect counts, preserve unknown
  runner effects without safe defaults, fail closed on AgentDB transition loss,
  and prove directory-fsync invocation after atomic authority-state replacement.
- WSP 62 tests explicitly cover every modified production entrypoint, including
  `main.py`, OpenClaw claim loops, the signer backend, and task executor.

## 2026-07-18: REDDOG_VALVE_HIGH_AUTHORITY_CLASSIFICATION_PHASE1

- Added signer, authority-seed, and authority-source regressions proving both
  WORKTREE and LIVE_ENQUEUE intent require consensus plus sovereign evidence.
- Added LOW-operation, consensus-only, and empty/None default normalization
  adversaries while retaining a positive LOW dry-run-only issuance case.
- Focused result: 45 tests passed across the three authority suites.

## 2026-07-18: REDDOG_RESIDENT_LIVE_CANARY_PHASE1

**Files**: `test_reddog_resident_live_canary.py` (NEW)

**Coverage**:

- Readiness-only mode never invokes the control loop and never serializes the
  supplied secret value.
- Linux, outside-repo state/receipt, required JSON artifacts, signer socket,
  Git/GitHub readiness, OpenRouter key presence, and exact execution
  confirmation fail closed.
- Real v1 control receipts and exact chain envelopes are used in the positive
  proof fixture; false schema, acceptance, status, lock, repository, progress,
  revision, envelope, new-receipt, and lineage fixtures fail closed.
- Accepted worktree invoke/create decisions plus an existing external Git
  worktree and all durable PatternMemory IDs are required.
- The positive proof now advances the atomic chain store through the real
  planner, creates a registered Git worktree, uses production draft/gate
  builders, and performs a real PatternMemory SQLite admission/readback.
- Store round-trip tests prove the persisted newest receipt witness equals the
  canonically recomputable envelope revision; forged witnesses fail closed.
- Exact terminal-receipt adversaries replace the nonempty stage, previous/final
  plan IDs, and stop action; completion now requires the canonical PatternMemory
  terminal transition and receipt ID.
- Registered/unregistered worktrees, invalid gitdirs, HEAD mismatches, missing
  PatternMemory rows, and forged admission identities are adversarial cases.
- Digest-valid PatternMemory rows with a wrong work order, selected slice, or
  candidate HEAD fail direct DB-to-plan/draft/registered-worktree binding.
- Split canonical integration support from the focused test module; WSP 62
  enforces the 675-line ceiling on both test files and all canary production
  files, plus the 50-line production-function ceiling.
- Same-process and second-process tests prove the shared non-blocking control
  lock prevents a competing main loop from reaching queue stages.
- Reserved runtime receipt collisions and inside-repository paths fail before
  execution; canonical and external paths remain accepted.
- AST coverage enforces both WSP 62's 675-line communication file limit and
  50-line production-function limit across the split canary modules.

**Truth boundary**: Tests use injected probes and do not perform live side
effects. The production live canary remains unexecuted.

## 2026-07-18: Runtime Artifact Confinement

- Added source-path, runtime-root escape, malformed-chain, and concurrent
  receipt append regression tests.

## 2026-07-18: REDDOG_HOLOINDEX_QUERY_OWNER_BOUNDARY_POC_PHASE1

**Files**: test_reddog_holoindex_query_boundary.py (NEW),
test_reddog_holoindex_owner_client_transport.py (NEW),
test_reddog_holoindex_direct_query_boundary.py (NEW),
test_reddog_holoindex_maintenance_dispatch.py (NEW),
test_reddog_main_readonly_operational_bootstrap.py and
test_reddog_readonly_audit_task_executor.py (UPDATED)

**WSP Protocol**: WSP 05, 06, 15, 22, 50, 62, 87, 97
**Phase**: POC implementation complete; focused validation green; PR pending
**Agent**: 0102 architect with delegated adversarial workers

**Changes**:

- Added owner-client transport, bearer proxy/redirect denial, literal
  `127.0.0.1`/path checks,
  local-Chroma denial, typed storage errors, generation binding, baseline
  freshness, dirty/old HEAD, lexical rejection, and maintenance race coverage.
- Added process-private handoff, direct-diagnostic-only, canonical
  source-scope, startup maintenance ordering, false-success denial, semantic
  preflight, and interactive/headless fail-closed coverage.
- Split boundary tests by owner-client transport, private handoff/response
  binding, adapter behavior, and direct diagnostics to stay within WSP_62
  domain thresholds without a new-file exemption.
- Added a focused canonical-receipt test proving a valid external receipt
  cannot override a disagreeing SSD-derived receipt and is rejected before
  receipt loading or direct backend construction.

**Impact**: The migrated downstream model/audit paths are designed to stop on
absent, lexical, stale, dirty, raced, narrowed, or unbound HoloIndex evidence.

**WSP Compliance**: Maintenance dispatch precedes generic WRE routing, and the
supported query adapter exposes no refresh surface; OS privilege isolation is
separate. The final post-refactor owner/query boundary matrix passed 57 tests,
and the non-overlapping downstream audit/bootstrap/state matrix passed 200.

## 2026-07-16: REDDOG_RESIDENT_QUEUE_DRAFT_PR_PUBLISH_REQUEST_BINDING_PHASE1

**Files**: `test_reddog_resident_queue_draft_pr_publish_request_binding.py`
(NEW), `test_reddog_resident_queue_verified_draft_pr_publish_handler.py`,
`test_reddog_resident_queue_stage_handler_registry.py`,
`test_reddog_main_resident_queue_serial_loop_bootstrap.py` (UPDATED)

**Slice**: `REDDOG_RESIDENT_QUEUE_DRAFT_PR_PUBLISH_REQUEST_BINDING_PHASE1` |
**Predecessor**: #1123 resident queue slice-verifier request binding

Resident queue verified draft PR publish can now derive its publish request
from the queue-bound work order's `draft_pr_publish_plan` plus recorded
slice-verifier and worktree-create chain receipts. Tests prove accepted
derivation, missing-plan rejection, rejected-verifier rejection, missing
worktree rejection, draft-only policy rejection, registry opt-in behavior,
startup env forwarding, and a full bootstrap path with no external publish
request JSON.

**Run**: `pytest modules/communication/moltbot_bridge/tests/test_reddog_resident_queue_draft_pr_publish_request_binding.py modules/communication/moltbot_bridge/tests/test_reddog_resident_queue_verified_draft_pr_publish_handler.py modules/communication/moltbot_bridge/tests/test_reddog_resident_queue_stage_handler_registry.py modules/communication/moltbot_bridge/tests/test_reddog_main_resident_queue_serial_loop_bootstrap.py -q`

## 2026-07-16: REDDOG_RESIDENT_QUEUE_SLICE_VERIFIER_REQUEST_BINDING_PHASE1

**Files**: `test_reddog_resident_queue_slice_verifier_request_binding.py`
(NEW), `test_reddog_resident_queue_slice_verifier_handler.py`,
`test_reddog_resident_queue_stage_handler_registry.py`,
`test_reddog_main_resident_queue_serial_loop_bootstrap.py` (UPDATED)

**Slice**: `REDDOG_RESIDENT_QUEUE_SLICE_VERIFIER_REQUEST_BINDING_PHASE1` |
**Predecessor**: #1122 resident queue pilot dry-run binding

Resident queue slice verifier can now derive its independent
evidence-producer request from the queue-bound work order's
`slice_verifier_plan` and recorded authority/runtime/worktree/bounded-pilot
chain receipts. Tests prove accepted derivation, missing-plan rejection,
rejected bounded-pilot rejection, missing signed receipt-chain rejection,
registry opt-in behavior, startup env forwarding, and a full bootstrap path
with no external verifier or evidence-request JSON.

**Run**: `pytest modules/communication/moltbot_bridge/tests/test_reddog_resident_queue_slice_verifier_request_binding.py modules/communication/moltbot_bridge/tests/test_reddog_resident_queue_slice_verifier_handler.py modules/communication/moltbot_bridge/tests/test_reddog_resident_queue_stage_handler_registry.py modules/communication/moltbot_bridge/tests/test_reddog_main_resident_queue_serial_loop_bootstrap.py -q`

## 2026-07-16: REDDOG_RESIDENT_QUEUE_PILOT_DRYRUN_BINDING_PHASE1

**Files**: `test_reddog_resident_queue_pilot_dryrun_binding.py` (NEW),
`test_reddog_resident_queue_bounded_worker_pilot_handler.py`,
`test_reddog_resident_queue_stage_handler_registry.py`,
`test_reddog_main_resident_queue_serial_loop_bootstrap.py` (UPDATED)

**Slice**: `REDDOG_RESIDENT_QUEUE_PILOT_DRYRUN_BINDING_PHASE1` |
**Predecessor**: #1121 bounded artifact generation binding

Resident queue bounded-worker pilot can now derive generic-writer and
governed-shell dry-run receipts from an explicit work-order
`bounded_worker_plan` plus recorded signed-authority, authority-verification,
execution-valve, and worktree-create stage results. Tests prove accepted
derivation, missing-plan rejection, malformed-plan rejection, rejected-authority
blocking, HoloIndex index-gap propagation, registry opt-in behavior, startup
env forwarding, and a full bootstrap path with no external writer/shell JSON.

**Run**: `pytest modules/communication/moltbot_bridge/tests/test_reddog_bounded_artifact_generation_runtime.py modules/communication/moltbot_bridge/tests/test_reddog_wre_queue_authorized_bounded_worker_pilot_invoke.py modules/communication/moltbot_bridge/tests/test_reddog_resident_queue_pilot_dryrun_binding.py modules/communication/moltbot_bridge/tests/test_reddog_resident_queue_bounded_worker_pilot_handler.py modules/communication/moltbot_bridge/tests/test_reddog_resident_queue_stage_handler_registry.py modules/communication/moltbot_bridge/tests/test_reddog_resident_queue_serial_loop.py modules/communication/moltbot_bridge/tests/test_reddog_main_resident_queue_serial_loop_bootstrap.py modules/communication/moltbot_bridge/tests/test_reddog_resident_queue_slice_verifier_handler.py -q`

## 2026-07-16: REDDOG_BOUNDED_ARTIFACT_GENERATION_BINDING_PHASE1

**Files**: `test_reddog_bounded_artifact_generation_runtime.py` (NEW),
`test_reddog_resident_queue_bounded_worker_pilot_handler.py`,
`test_reddog_resident_queue_stage_handler_registry.py`,
`test_reddog_main_resident_queue_serial_loop_bootstrap.py` (UPDATED)

**Slice**: `REDDOG_BOUNDED_ARTIFACT_GENERATION_BINDING_PHASE1` |
**Predecessor**: #1120 independent evidence producer queue binding

Resident queue bounded-worker pilot can now either consume prebuilt artifact
contents or generate bounded artifact text from an explicit request using an
injected/configured artifact generator. Tests prove generation is gated by
HoloIndex evidence, accepted signed authority, accepted signed receipt chain,
exact planned artifact matching, no secrets, registry dependency checks, and
startup env forwarding.

**Run**: `pytest modules/communication/moltbot_bridge/tests/test_reddog_bounded_artifact_generation_runtime.py modules/communication/moltbot_bridge/tests/test_reddog_wre_queue_authorized_bounded_worker_pilot_invoke.py modules/communication/moltbot_bridge/tests/test_reddog_resident_queue_bounded_worker_pilot_handler.py modules/communication/moltbot_bridge/tests/test_reddog_resident_queue_stage_handler_registry.py modules/communication/moltbot_bridge/tests/test_reddog_resident_queue_serial_loop.py modules/communication/moltbot_bridge/tests/test_reddog_main_resident_queue_serial_loop_bootstrap.py modules/communication/moltbot_bridge/tests/test_reddog_resident_queue_slice_verifier_handler.py -q`

## 2026-07-16: WRE_INDEPENDENT_EVIDENCE_PRODUCER_QUEUE_BINDING_PHASE1

**Files**: `test_reddog_resident_queue_slice_verifier_handler.py`,
`test_reddog_resident_queue_stage_handler_registry.py`,
`test_reddog_main_resident_queue_serial_loop_bootstrap.py` (UPDATED)

**Slice**: `WRE_INDEPENDENT_EVIDENCE_PRODUCER_QUEUE_BINDING_PHASE1` |
**Predecessor**: #1119 independent evidence producer runtime

Resident queue slice verifier can now either consume a prebuilt verifier
request or explicitly produce diff/test evidence from the isolated worktree
using an injected evidence command runner. Tests prove producer acceptance feeds
the existing autonomous verifier, producer rejection blocks verification,
registry dependencies fail closed, startup env plumbing forwards the request and
runner mode, and unsupported evidence runner modes reject.

**Run**: `pytest modules/communication/moltbot_bridge/tests/test_reddog_resident_queue_slice_verifier_handler.py modules/communication/moltbot_bridge/tests/test_reddog_resident_queue_stage_handler_registry.py modules/communication/moltbot_bridge/tests/test_reddog_main_resident_queue_serial_loop_bootstrap.py modules/infrastructure/wre_core/tests/test_wre_independent_evidence_producer_runtime.py -q`

## 2026-07-11: REDDOG_OPENCLAW_LIVE_ENQUEUE_WRITER_ADAPTER_PHASE1

**File**: `test_reddog_openclaw_live_enqueue_writer.py` (NEW - 6 tests)
**Slice**: `REDDOG_OPENCLAW_LIVE_ENQUEUE_WRITER_ADAPTER_PHASE1` | **Predecessors**: #952 live enqueue seam

Concrete writer adapter: foundup_job appends one typed FoundUpJob to OpenClaw queue without
execution; autonomous_task calls injected AgentDB factory; #952 seam + concrete writer integration
appends a queue item; missing ids reject before mutation; AST guard blocks shell/Hermes/WRE execution imports.

**Run**: `pytest modules/communication/moltbot_bridge/tests/test_reddog_openclaw_live_enqueue_writer.py -q`

## 2026-07-11: REDDOG_OPENCLAW_LIVE_ENQUEUE_IMPLEMENTATION_PHASE1

**File**: `test_reddog_openclaw_live_enqueue.py` (NEW - 12 tests), `test_reddog_wre_execution_valve.py` (UPDATED)
**Slice**: `REDDOG_OPENCLAW_LIVE_ENQUEUE_IMPLEMENTATION_PHASE1` | **Predecessors**: #904 adapter dry-run, #905 contract, #950 signature gate, #951 signed receipt chain

Live enqueue seam: accepts only with `VALVE_OPEN_LIVE_ENQUEUE`, accepted signed work authority,
accepted signed receipt-chain verification, accepted adapter dry-run output, and an injected
writer. Tests prove dry-run/worktree/closed valves reject before writer call, replay protection,
writer rejection, autonomous_task and foundup_job routing, and no direct execution/queue imports.

**Run**: `pytest modules/communication/moltbot_bridge/tests/test_reddog_openclaw_live_enqueue.py modules/communication/moltbot_bridge/tests/test_reddog_wre_execution_valve.py -q`

## 2026-07-11: REDDOG_SIGNED_RECEIPT_CHAIN_PHASE1

**File**: `test_reddog_signed_receipt_chain.py` (NEW - 15 tests)
**Slice**: `REDDOG_SIGNED_RECEIPT_CHAIN_PHASE1` | **Predecessors**: #928 identity contract, #931 E0, #932 E1

Signed receipt chain verification: empty issuance-time chain accepted as no-reward-yet,
non-empty chains require injected signature verification, work-order/RedDog/reward-account
binding, correct hash-link order, freshness, ASCII payloads, and no signing/execution imports.

**Run**: `pytest modules/communication/moltbot_bridge/tests/test_reddog_signed_receipt_chain.py -q`

## 2026-07-11: REDDOG_WORK_ORDER_SIGNATURE_GATE_INTEGRATION_PHASE1

**Files**: `test_reddog_openclaw_work_order_policy_gate.py`, `test_reddog_wre_operational_spine.py` (UPDATED)
**Slice**: `REDDOG_WORK_ORDER_SIGNATURE_GATE_INTEGRATION_PHASE1` | **Predecessors**: #931 E0, #932 E1, #947 WRE operational spine

Signed-authority gate integration: policy gate rejects missing/rejected/mismatched verifier results
when signed authority is required; explicit rejected signature results cannot be ignored; worktree-create
operational spine requires accepted signed authority by default before runner/worktree creation.
Canonical helper coverage proves E1 verification is invoked and rejects a valid signature whose signed
path scope does not match the actual work order.

**Run**: `pytest modules/communication/moltbot_bridge/tests/test_reddog_openclaw_work_order_policy_gate.py modules/communication/moltbot_bridge/tests/test_reddog_wre_operational_spine.py modules/communication/moltbot_bridge/tests/test_reddog_work_order_signature_verifier.py -q`

## 2026-07-08: REDDOG_WRE_OPERATIONAL_SPINE_WORKTREE_CREATE_PHASE1

**File**: `test_reddog_wre_operational_spine.py` (NEW - 6 tests)
**Slice**: `REDDOG_WRE_OPERATIONAL_SPINE_WORKTREE_CREATE_PHASE1` | **Predecessors**: #896 invocation, #898 executor plan, #903 valve, worktree-create slice

Operational spine composer: governed work order -> invocation dry-run -> executor plan -> execution
valve -> isolated worktree create. Tests prove acceptance with `VALVE_OPEN_WORKTREE_CREATE`,
default-closed valve rejection before runner, write-sensitive index-gap rejection at invocation,
lock-collision rejection at plan, digest stability, no sovereign-token egress, and no subprocess/live
dispatch imports in the composer.

**Run**: `pytest modules/communication/moltbot_bridge/tests/test_reddog_wre_operational_spine.py -q`

## 2026-06-28: REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_DRYRUN_PHASE1

**File**: `test_reddog_wre_executor_dryrun.py` (NEW — 8 tests)
**Slice**: `REDDOG_WRE_ISOLATED_WORKTREE_EXECUTOR_DRYRUN_PHASE1` | **Predecessors**: #896 invocation, #897 contract

Executor plan dry-run: accepted invocation -> WREExecutorPlan + phase receipts; reject protected branch,
forbidden paths, lock collision, missing cleanup; AST denylist; no git/worktree mutation.

**Run**: `pytest modules/communication/moltbot_bridge/tests/test_reddog_wre_executor_dryrun.py -q`

## 2026-06-28: REDDOG_WORK_ORDER_RUNTIME_INVOCATION_DRYRUN_PHASE1

**File**: `test_reddog_work_order_runtime_invocation.py` (NEW — 7 tests)
**Slice**: `REDDOG_WORK_ORDER_RUNTIME_INVOCATION_DRYRUN_PHASE1` | **Predecessors**: #893 policy gate, #894 receipt

End-to-end dry-run invocation: policy gate + receipt store; accept/reject/replay/idempotency; AST denylist.

**Run**: `pytest modules/communication/moltbot_bridge/tests/test_reddog_work_order_runtime_invocation.py -q`

## 2026-06-28: REDDOG_HERMES_WORK_ORDER_RECEIPT_PHASE1

**File**: `test_reddog_work_order_receipt.py` (NEW — 14 tests)
**Slice**: `REDDOG_HERMES_WORK_ORDER_RECEIPT_PHASE1` | **Predecessors**: #893 policy gate

Hermes-compatible receipt emission/persistence from `PolicyGateReceipt`; digest stability, secret
redaction, idempotent SQLite store, no mutation imports.

**Run**: `pytest modules/communication/moltbot_bridge/tests/test_reddog_work_order_receipt.py -q`

## 2026-06-28: REDDOG_OPENCLAW_WORK_ORDER_POLICY_GATE_PHASE1

**File**: `test_reddog_openclaw_work_order_policy_gate.py` (NEW — 22 tests)
**Slice**: `REDDOG_OPENCLAW_WORK_ORDER_POLICY_GATE_PHASE1` | **Predecessors**: #890 dry-run, #892 permission probe

Policy gate tests use mocked `repo_permission_snapshot` only (Addendum D — no live `gh`).
Covers: accept write/audit, reject admin/stale/replay/forbidden paths, HoloIndex Addendum A paths,
receipt compatibility (Addendum C), WAE runtime non-import (Addendum B).

**Run**: `pytest modules/communication/moltbot_bridge/tests/test_reddog_openclaw_work_order_policy_gate.py -q`

## 2026-06-02: PolicyFlags Deserialization Sanitization Tests (W6)

**File**: `test_foundup_job_contract.py` (UPDATED + new class)
**Slice**: `HXA_POLICYFLAGS_WRITEBACK_REMEDIATION_PHASE1` | **Predecessors**: #746, #744, HXA24/27/30

`PolicyFlags.from_dict` now forces server-authored gate/token flags False (untrusted input). Existing
round-trip tests that asserted from_dict PRESERVES True gate/token flags are updated to the NEW correct
semantics (each justified in the audit Test Scenario Matrix):
- `test_to_dict_roundtrip` → `test_from_dict_sanitizes_server_authored_flags`
- `test_from_dict_missing_fields_default_false` (now asserts `security_gate_checked is False`)
- `test_policy_flags_in_job_roundtrip` → `…_sanitizes_gates`
- `test_capability_token_fields_from_dict` → `…_sanitized`
- `test_capability_token_roundtrip` → `…_sanitized_on_roundtrip`

**New** `TestPolicyFlagsDeserializationSanitization` (positive control): malicious-all-True → all-False;
`dry_run_mode` preserved (true/false/missing); FoundUpJob.from_dict + __post_init__ chokepoint coverage;
`create_job()` all-False at birth; direct constructor still allows server-authored True.

**Determinism**: pure dataclass (de)serialization; no process/network/.env/model.

**Result**: **78 passed**.

---

## 2026-06-01: WSP 109 Genesis Gate Remediation Tests (W6)

**File**: `test_openclaw_wsp109_onboarding_dryrun.py` (REWRITTEN - 10 tests, 0 xfail)
**Slice**: `OPENCLAW_WSP109_GENESIS_GATE_REMEDIATION_PHASE1` | **Predecessors**: #737, #738

The 4 strict-xfail contracts from #738 are CONVERTED to passing assertions (gaps fixed):
- `TestWSP109OnboardingGated`: onboard recognised + dispatch returns NOT_READY handoff (no FAM call)
- `TestFoundupGenesisGate`: `validate_genesis_envelope` wired into dispatch; `launch foundup` gated (not passthrough)
- `TestDualParserConverged`: `create foundup X` == `create foundup job` (both → dry-run queue, no launch)
- `TestW10Handoff`: `validate_and_remember` emits W10 handoff; `build_w10_handoff` packet shape + status normalisation
- `TestProtectedPathRemainsBlocked`: unchanged (2 PASS, #737 S5)

**Hygiene**: `test_openclaw_foundup_routing.py` reload pollution removed.

**Determinism**: pure-function + `inspect.getsource` + MagicMock; `validate_genesis_envelope({})` short-circuits before validator load. No live process/network/.env/model.

**Run**: `pytest test_openclaw_wsp109_onboarding_dryrun.py test_openclaw_foundup_routing.py test_openclaw_foundup_orchestrator.py -q`

**Result**: **59 passed, 0 failed, 0 xfail** (adjacent combined run was `8 failed` pre-fix). 4 pre-existing dae/runtime failures verified on clean main (stashed) — out of scope.

---

## 2026-06-01: WSP 109 Onboarding Dry-Run Characterization Tests (W6)

**File**: `test_openclaw_wsp109_onboarding_dryrun.py` (NEW - 11 tests: 7 passed, 4 strict xfail)
**Slice**: `OPENCLAW_WSP109_ONBOARDING_DRYRUN_TEST_PHASE1` | **Predecessor**: #737

**Test Classes**:
- `TestWSP109OnboardingClassification`: `onboard` prompt is not an intake/build trigger (1 PASS + 1 xfail)
- `TestFoundupGenesisGateVisibility`: `dispatch_foundup` bypasses the genesis validator (2 PASS + 1 xfail)
- `TestDualParserAmbiguity`: `create foundup X` vs `create foundup job` diverge (1 PASS + 1 xfail)
- `TestW10HandoffAbsence`: `validate_and_remember` self-approves, no W10 handoff (1 PASS + 1 xfail)
- `TestProtectedPathRemainsBlocked`: protected-path edit fail-closed BLOCKED (2 PASS — #737 S5)

**Determinism**: pure-function + `inspect.getsource` + `MagicMock`. No live process, network, `.env`, or model calls.

**Run**: `python -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_wsp109_onboarding_dryrun.py -q`

**Result**: 7 passed, 4 xfailed. With adjacent `test_openclaw_foundup_orchestrator.py`: 29 passed, 4 xfailed, **0 failed** (no downstream pollution introduced).

**Pre-existing note (not this slice)**: `test_openclaw_foundup_routing.py` + `test_openclaw_foundup_orchestrator.py` together → 8 failed — pre-existing `importlib.reload` pollution from the routing file (reproduces without this slice; out of scope; flagged for the remediation slice).

---

## 2026-05-13: ROC_CANDIDATE Observability Metric Tests (WSP 97)

**File**: `test_roc_candidate_metrics.py` (NEW - 57 tests)

**Test Classes**:
- `TestCountROCCandidates`: Empty input, candidate counting, criteria breakdown
- `TestCriteriaEnforcement`: decision/quorum/threshold/evidence validation
- `TestAnomalyDetection`: Truth boundary violations flagged
- `TestWSP97Labels`: All 6 required labels present
- `TestForbiddenConsumers`: Consumer list documented
- `TestTruthBoundaries`: All 3 truth fields False
- `TestExportJSON`: Deterministic output, sorted keys
- `TestExportMarkdown`: Section headers, candidate ratio
- `TestPureFunctionBehavior`: No side effects, no DB access
- `TestTenantFiltering`: Optional tenant_id filter

**Run**:
- `python -m pytest modules/communication/moltbot_bridge/tests/test_roc_candidate_metrics.py -q`

**Result**: 57 passed

---

## 2026-05-13: CABR Consensus Pipeline Tests (WSP 97)

**File**: `test_cabr_consensus_pipeline.py` (NEW - 35 tests)

**Test Classes**:
- `TestMinimalReceiptPipeline`: Minimal receipt returns review-only result
- `TestMissingEvidenceFailsClosed`: Empty/None evidence fails at scoring
- `TestPAVSRejectBlocksPath`: pAVS rejection blocks downstream stages
- `TestQuorumNotMetReturnsPending`: Zero/insufficient attestations returns pending
- `TestQuorumMetReturnsAcceptedForReview`: Full quorum returns accepted-for-review
- `TestOptionalStorePersistence`: Store persistence when provided
- `TestNoStoreNoWrites`: No store means no persistence attempt
- `TestExportDeterministic`: JSON/Markdown exports deterministic
- `TestWSP97LabelsPresent`: All required labels present
- `TestNoPayoutReadinessInferred`: payout_ready=False always
- `TestNoDAOActivationInferred`: cabr_ready=False always
- `TestNoCABRReadinessInferred`: verification_complete=False always
- `TestStageFailureExplicit`: Failures explicit, downstream stages blocked
- `TestBatchPipelineDeterministic`: Multiple receipts in deterministic order
- `TestLifecycleExportIntegration`: Export generated when requested
- `TestPreComputedResultsSkipStages`: Pre-computed results skip stages

**Run**:
- `python -m pytest modules/communication/moltbot_bridge/tests/test_cabr_consensus_pipeline.py -q`

**Result**: 35 passed

---

## 2026-05-13: CABR Store Export Tests (WSP 97)

**File**: `test_cabr_store_export.py` (NEW - 65 tests)

**Test Classes**:
- `TestNoStoreProvidedFailsClosed`: Store required, raises ValueError
- `TestProvidedEmptyStoreExportsDeterministic`: Valid JSON/Markdown, sorted keys
- `TestStoreWithPersistedRecordsExportsDeterministic`: Correct counts, correlations
- `TestIncludeTogglesWork`: JSON only, Markdown only, both, neither
- `TestInvalidTimeRangeFailsClosed`: ValueError for start > end
- `TestMissingReceiptsProduceGaps`: Gap reporting for missing data
- `TestRequiredWsp97LabelsPresent`: All 6 labels in result/JSON/Markdown
- `TestNoFilesystemWrites`: No files created, returns strings
- `TestNoDefaultDbPath`: Store parameter required, no db_path
- `TestNoPayoutReadinessInferred`: payout_ready=False, no payout fields
- `TestNoDAOActivationInferred`: cabr_ready=False, no DAO fields
- `TestNoCABRReadinessInferred`: verification_complete=False
- `TestTruthAnomalyPropagation`: Anomalies flagged from pavs/score/quorum
- `TestRequestDataclass`: Request validation
- `TestResultDataclass`: Result serialization, WSP 97 fields

**Run**:
- `python -m pytest modules/communication/moltbot_bridge/tests/test_cabr_store_export.py -q`

**Result**: 65 passed

---

## 2026-05-13: CABR Lifecycle Report Export Tests (WSP 97)

**File**: `test_cabr_lifecycle_report_export.py` (NEW - 67 tests)

**Test Classes**:
- `TestJsonExportDeterministic`: Valid JSON, sorted keys, reproducibility
- `TestMarkdownExportDeterministic`: Headers, sections, tables
- `TestRequiredWsp97LabelsPresent`: All 6 labels in export, JSON, Markdown
- `TestFalseTruthFieldsPresent`: All 3 truth fields False
- `TestLifecycleQuerySummaryIncluded`: Summary population, items by stage
- `TestGapSummaryIncluded`: Gap counts, gaps by stage
- `TestConsensusReportSummaryOptional`: Optional inclusion, decision counts
- `TestAnomalyFlagsIncluded`: Anomaly detection, details
- `TestNoPayoutReadinessInferred`: payout_ready=False, no payout fields
- `TestNoDAOActivationInferred`: cabr_ready=False, no DAO fields
- `TestNoCABRReadinessInferred`: verification_complete=False
- `TestPureFunctionNoFilesystemWrites`: Pure functions, no file I/O
- `TestNoDefaultDbPath`: No db_path parameter
- `TestDataclassSerialization`: Dataclass to_dict()
- `TestCombinedExport`: Both summaries, valid output

**Run**:
- `python -m pytest modules/communication/moltbot_bridge/tests/test_cabr_lifecycle_report_export.py -q`

**Result**: 67 passed

---

## 2026-05-13: CABR Lifecycle Query Tests (WSP 97)

**File**: `test_cabr_lifecycle_query.py` (NEW - 45 tests)

**Test Classes**:
- `TestEmptyStoreQuery`: Empty store returns empty result, gap summary
- `TestStoreWithPersistedRecordsQuery`: Query returns all, creates correlations
- `TestTimeRangeQuery`: Start/end/both filtering, filter preserved in result
- `TestInvalidTimeRangeFailsClosed`: ValueError for start > end
- `TestLimitAppliedDeterministically`: Exact count, after time filter
- `TestPersistedRecordsCorrelateWithSuppliedReceipts`: Full pipeline correlation
- `TestMissingSuppliedReceiptDataProducesGaps`: Gap reporting for missing data
- `TestLifecycleGapSummaryFromStore`: Gap summary function, to_dict
- `TestTruthBoundaryAnomaliesPropagated`: True values flagged
- `TestJsonExportDeterministic`: Sorted keys, ISO dates, WSP 97 note
- `TestNoStoreMutation`: No records added/modified by query
- `TestNoPayoutReadinessInferred`: No payout fields in result
- `TestNoDAOActivationInferred`: No DAO fields in result
- `TestNoDefaultDbPath`: Store parameter required
- `TestUsesTmpPathOnly`: All tests use TemporaryDirectory
- `TestFilterDataclass`: Filter validation and serialization
- `TestResultDataclass`: Result serialization, WSP 97 note

**Run**:
- `python -m pytest modules/communication/moltbot_bridge/tests/test_cabr_lifecycle_query.py -q`

**Result**: 45 passed

---

## 2026-05-13: CABR Lifecycle Correlation Tests (WSP 97)

**File**: `test_cabr_lifecycle_correlation.py` (NEW - 43 tests)

**Test Classes**:
- `TestLifecycleStageEnum`: Stage ordering and completeness
- `TestReceiptOnlyDownstreamGaps`: Receipt only -> 6 downstream gaps
- `TestReceiptPlusPayvsGaps`: Receipt + pAVS -> remaining gaps
- `TestFullLifecycleCorrelation`: All 7 stages -> no gaps
- `TestCorrelationByReceiptId`: Primary correlation key
- `TestCorrelationByJobIdFallback`: Fallback when no receipt_id
- `TestCorrelationByRecordHash`: Record hash in consensus records
- `TestDuplicateRecordsDeterministic`: First item wins
- `TestMissingStageReportedNotInferred`: Gaps reported, not failure
- `TestTruthBoundaryAnomalyFlagged`: True values flagged
- `TestDeterministicJsonExport`: Sorted keys, ISO dates
- `TestNoStoreMutation`: Pure function, no side effects
- `TestNoPayoutReadinessInferred`: No payout fields in result
- `TestNoDAOActivationInferred`: No DAO fields in result
- `TestNoDefaultDbPath`: No store/db_path parameter
- `TestGapSummary`: Gap summary statistics
- `TestLifecycleItem`: Item serialization
- `TestLifecycleGap`: Gap serialization
- `TestMultipleReceiptsDifferentLifecycles`: Mixed states
- `TestCorrelationSorting`: Deterministic ordering

**Run**:
- `python -m pytest modules/communication/moltbot_bridge/tests/test_cabr_lifecycle_correlation.py -q`

**Result**: 43 passed

---

## 2026-05-13: CABR Consensus Time Range and Correlation Tests (WSP 97)

**File**: `test_cabr_consensus_reporting_time_correlation.py` (NEW - 46 tests)

**Test Classes**:
- `TestTimeFilterValidation`: Valid/invalid time ranges, edge cases
- `TestTimeRangeQueries`: Start/end/both/limit filtering, sorting, empty store
- `TestReceiptCorrelation`: Matched/unmatched/partial correlation, empty inputs
- `TestCorrelationReports`: Statistics accuracy, time filtering integration
- `TestJsonExport`: Deterministic output, datetime serialization
- `TestDataclassSerialization`: All new dataclasses serialize correctly
- `TestWSP97TruthBoundaries`: All truth fields remain False
- `TestStoreRequirements`: Functions require explicit store

**Run**:
- `python -m pytest modules/communication/moltbot_bridge/tests/test_cabr_consensus_reporting_time_correlation.py -q`

**Result**: 46 passed

---

## 2026-05-13: CABR Consensus Reporting Tests (WSP 97)

**File**: `test_cabr_consensus_reporting.py` (NEW - 48 tests)

**Test Classes**:
- `TestEmptyStoreReport`: Empty store produces valid report with zero counts
- `TestMixedDecisionReport`: Mixed decisions counted correctly
- `TestDecisionFilterReport`: Filter by decision type works
- `TestReasonCodeCounts`: Reason codes counted and sorted
- `TestTruthBoundarySummaryAllFalse`: All False = no anomaly
- `TestTruthBoundaryAnomalyFlagged`: True value = anomaly flagged
- `TestDeterministicJsonExport`: JSON is deterministic and valid
- `TestReportDoesNotMutateStore`: Store unchanged after report
- `TestNoPayoutReadinessInferred`: High acceptance != payout ready
- `TestNoDAOActivationInferred`: High quorum != DAO activation
- `TestNoDefaultDbPath`: Functions require explicit store
- `TestTmpPathOnly`: tmp_path usage verification
- `TestQuorumMetricsSummary`: Quorum metrics calculated correctly
- `TestSummarizeRecordsPureFunction`: Pure function behavior
- `TestDataclassSerialization`: Dataclasses serialize correctly

**Run**:
- `python -m pytest modules/communication/moltbot_bridge/tests/test_cabr_consensus_reporting.py -q`

**Result**: 48 passed

---

## 2026-05-13: CABR Consensus Finalizer Persistence Tests (WSP 97)

**File**: `test_cabr_consensus_finalizer_persistence.py` (NEW - 26 tests)

**Test Classes**:
- `TestStoreNoneProducesNoDbFile`: store=None behavior, no DB file, persistence_attempted=False
- `TestProvidedStoreSavesAcceptedRecord`: Accepted record persistence, success status
- `TestProvidedStoreSavesRejectedPendingRecords`: REJECTED/PENDING/NOT_FINALIZED all persisted
- `TestDuplicateFinalizationIdempotent`: Duplicate record_id returns ALREADY_EXISTS
- `TestStoreFailureReturnsExplicitFailure`: Schema not init fails, record still returned
- `TestBatchFinalizationPersistsAllRecords`: Batch persistence, order preserved
- `TestPersistedTruthFieldsRemainFalse`: WSP 97 truth fields always False
- `TestNoPayoutDaoStateProgression`: No payout/DAO fields, cabr_ready stays False
- `TestNoDefaultDbPathUsed`: No implicit store creation
- `TestTmpPathOnly`: tmp_path usage verification
- `TestFinalizeResultSerialization`: to_dict() includes all fields

**Run**:
- `python -m pytest modules/communication/moltbot_bridge/tests/test_cabr_consensus_finalizer_persistence.py -q`

**Result**: 26 passed

---

## 2026-05-13: CABR Consensus Store Tests (WSP 97)

**File**: `test_cabr_consensus_store.py` (NEW - 35 tests)

**Test Classes**:
- `TestSchemaInitializes`: Schema creation, idempotency, version tracking
- `TestSaveAndGetRecord`: Basic CRUD, field preservation
- `TestDuplicateRecordIdHandling`: Idempotent duplicate rejection
- `TestListRecordsDeterministic`: Pagination, limit, offset
- `TestDecisionFilter`: Filter by decision value
- `TestTruthFieldsRemainFalse`: WSP 97 truth field preservation after persistence
- `TestNoPayoutActivation`: No payout/DAO fields become true
- `TestInvalidDbPathFailsClosed`: Invalid path handling
- `TestMissingCorruptedSchemaHandled`: Schema not initialized errors
- `TestRecordExists`: Existence check without retrieval
- `TestRoundTripPreservesRecordHash`: Hash integrity on save/get
- `TestValidationErrors`: Missing required field handling
- `TestContextManager`: Context manager usage
- `TestNoDbFileCommittedToRepo`: tmp_path usage verification

**Run**:
- `python -m pytest modules/communication/moltbot_bridge/tests/test_cabr_consensus_store.py -q`

**Result**: 35 passed

---

## 2026-05-13: CABR Consensus Finalization Tests (WSP 29/97)

**File**: `test_cabr_consensus_finalizer.py` (NEW - 48 tests)

**Test Classes**:
- `TestMissingScoreResultFailsClosed`: Missing score -> NOT_FINALIZED
- `TestMissingQuorumResultPendingQuorum`: Missing quorum -> PENDING_QUORUM
- `TestScoringRejectRejects`: All scoring rejection types -> REJECTED
- `TestQuorumNotMetPendingQuorum`: Zero/insufficient verifiers -> PENDING_QUORUM
- `TestScoringAcceptedQuorumAcceptedAcceptedForReview`: Both passed -> ACCEPTED_FOR_REVIEW
- `TestTruthBoundaryViolationBlocks`: All 6 truth boundary violations -> BLOCKED
- `TestDeterministicRecordHashStable`: Same inputs -> same hash
- `TestBatchFinalizationDeterministic`: Batch ordering preservation
- `TestNoPayoutStatusChanges`: payout_ready=False, no payout fields
- `TestNoDAOActivation`: cabr_ready=False
- `TestNoExternalDependency`: Pure local computation
- `TestWSP97TruthFieldsAlwaysFalse`: All truth fields always False
- `TestQuorumRejection`: Quorum rejection types
- `TestRecordIdGeneration`: ID format/uniqueness
- `TestResultSerialization`: to_dict/from_dict roundtrip
- `TestIdentityExtraction`: Identity from explicit/nested fields
- `TestInputSnapshot`: Optional snapshot inclusion

**Run**:
- `python -m pytest modules/communication/moltbot_bridge/tests/test_cabr_consensus_finalizer.py -q`

**Result**: 48 passed

---

## 2026-05-13: Quorum Verification Enforcement Tests (WSP 29/97)

**File**: `test_quorum_verification_engine.py` (NEW - 41 tests)

**Test Classes**:
- `TestZeroAttestationsQuorumNotMet`: Zero attestations handling
- `TestOneOrTwoAttestationsQuorumNotMet`: Below min_validators (1-2)
- `TestThreeUniqueAttestationsQuorumMet`: Quorum met with 3+ verifiers
- `TestDuplicateVerifierIDsRejected`: Duplicate verifier rejection
- `TestMissingVerifierIDRejected`: Missing verifier_id rejection
- `TestInvalidSignatureUnsupported`: Phase 1 signature handling
- `TestConsensusScoreBelowThresholdRejected`: Score < 0.382
- `TestConsensusScoreAtThresholdAccepted`: Score >= 0.382
- `TestConsensusScoreAboveThresholdAccepted`: Score > 0.382
- `TestConflictingAttestationsHandledDeterministically`: Mixed votes
- `TestBatchEvaluationDeterministic`: Batch ordering preservation
- `TestNoExternalSystemsRequired`: Pure local computation
- `TestNoPayoutTriggered`: payout_ready=False
- `TestNoDAOActivation`: cabr_ready=False
- `TestWSP97TruthFieldsRemainFalse`: All truth fields False
- `TestMissingIdentityRejects`: Identity validation
- `TestQuorumIdGeneration`: ID format/uniqueness
- `TestResultSerialization`: to_dict/from_dict roundtrip
- `TestMinValidatorsConfiguration`: Custom quorum threshold
- `TestConsensusThresholdConfiguration`: Custom consensus threshold
- `TestDryRunMode`: Dry-run behavior
- `TestInputBuilders`: build_quorum_input_from_cabr_result
- `TestAttestationSerialization`: VerifierAttestation serialization
- `TestValidAttestationStatus`: VALID as implicit APPROVE

**Run**:
- `python -m pytest modules/communication/moltbot_bridge/tests/test_quorum_verification_engine.py -q`

**Result**: 41 passed

---

## 2026-05-13: CABR Runtime Scoring Engine Tests (WSP 29/97)

**File**: `test_cabr_scoring_engine.py` (NEW - 42 tests)

**Test Classes**:
- `TestMissingEvidenceRejects`: Empty/None evidence_refs rejection
- `TestDryRunAcceptedForReviewOnly`: Dry-run/simulated execution scoring
- `TestVerificationCompleteNeverTrue`: WSP 97 truth field enforcement
- `TestCABRReadyAlwaysFalse`: cabr_ready=False preservation
- `TestPayoutReadyAlwaysFalse`: payout_ready=False preservation
- `TestQuorumBelowThreeFails`: Verifier count below min_validators
- `TestThreeVerifiersQuorumEligible`: Quorum met with 3+ verifiers
- `TestDuplicateVerifiersDoNotCount`: Duplicate verifier ID rejection
- `TestFailedPAVSResultRejects`: pAVS failure state propagation
- `TestTruthBoundaryViolationRejects`: Input claiming completion rejected
- `TestBatchScoringDeterministic`: Batch ordering preservation
- `TestNoNetworkCalls`: Pure local computation
- `TestNoTokenIssuance`: No token-related output fields
- `TestWSP97TruthFieldsRemainFalse`: All acceptance states have False truth fields
- `TestMissingIdentityRejects`: Identity field validation
- `TestScoreIdGeneration`: Score ID format/uniqueness
- `TestResultSerialization`: to_dict/from_dict roundtrip
- `TestConvenienceFunctions`: score_from_receipt, score_from_pavs_result
- `TestMinValidatorsConfiguration`: Custom quorum threshold
- `TestInputBuilders`: build_score_input_from_receipt/pavs_result

**Run**:
- `python -m pytest modules/communication/moltbot_bridge/tests/test_cabr_scoring_engine.py -q`

**Result**: 42 passed

---

## 2026-05-12: HXA24 Capability Token PolicyFlags Tests (WSP 97)

**File**: `test_foundup_job_contract.py` (extended - 8 new tests)

**TestPolicyFlags** (extended):
- `test_capability_token_fields_exist`: Verifies all 4 fields exist
- `test_capability_token_fields_to_dict`: to_dict includes all 4 fields
- `test_capability_token_fields_from_dict`: from_dict restores all 4 fields
- `test_capability_token_roundtrip`: Roundtrip preserves values
- Updated `test_default_all_false`: Includes capability token defaults
- Updated `test_from_dict_missing_fields_default_false`: Includes capability token backward compat

**New Fields Tested**:
- `capability_token_checked` (default False)
- `capability_token_present` (default False)
- `capability_token_validated` (default False)
- `capability_token_scope_authorized` (default False)

**Run**:
- `python -m pytest modules/communication/moltbot_bridge/tests/test_foundup_job_contract.py -q`

**Result**: 70 passed (was 62)

---

## 2026-05-03: Dry-Run Policy Flag Alignment Tests (WSP 97)

**File**: `test_openclaw_foundup_routing.py` (extended - 11 new tests)

**TestDryRunPolicyFlagAlignment**:
- `test_dry_run_true_sets_policy_flag`: dry_run=true sets policy_flags.dry_run_mode
- `test_double_dash_dry_run_sets_policy_flag`: --dry-run sets policy_flags.dry_run_mode
- `test_bracketed_dry_run_sets_policy_flag`: [dry-run] sets policy_flags.dry_run_mode
- `test_missing_dry_run_leaves_flag_false`: No dry-run leaves flag False
- `test_no_is_dry_run_field_on_foundup_job`: Verifies no duplicate is_dry_run field
- `test_dry_run_receipt_maps_to_not_required`: VerificationStatus.NOT_REQUIRED
- `test_dry_run_receipt_truth_boundaries`: cabr_ready=False, payout_ready=False
- `test_dry_run_detection_function`: Direct _detect_dry_run_mode() tests

**Run**:
- `python -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_foundup_routing.py -q`

**Result**: 27 passed

---

## 2026-03-29: Skill Evolution Loop Phase 2 - Mutation Surface Tests (WSP 48/77)

**File**: `test_openclaw_skill_evolution.py` (extended - 23 new tests)
- **TestMutationSurfaceEnvGates** (4 tests - fail-closed verification):
  - `test_mutation_surface_disabled_by_default`: OPENCLAW_MUTATION_SURFACE_ENABLED defaults to 0
  - `test_ab_scheduling_disabled_by_default`: OPENCLAW_AB_SCHEDULING_ENABLED defaults to 0
  - `test_promotion_disabled_by_default`: OPENCLAW_PROMOTION_ENABLED defaults to 0
  - `test_gates_enabled_when_set_to_1`: All gates enabled when explicitly set
- **TestMutationSurfaceReportDue** (3 tests):
  - `test_never_due_when_gate_disabled`: Returns False even if report missing
  - `test_due_when_gate_enabled_and_missing`: Returns True when gate on
  - `test_not_due_when_fresh`: Returns False when gate on and report fresh
- **TestBuildMutationSurfaceReport** (4 tests):
  - `test_report_disabled_when_gate_off`: Returns disabled state
  - `test_report_enabled_when_gate_on`: Evaluates skills when gate on
  - `test_report_has_required_top_level_fields`: Contract verification
  - `test_report_summary_counts`: Summary mutation status counts
- **TestBuildMutationSurfaceEntry** (4 tests):
  - `test_stable_skill_classification`: Healthy skill = stable
  - `test_eligible_for_ab_classification`: Low fidelity = eligible_for_ab
  - `test_blocked_when_insufficient_data`: Insufficient data = blocked
  - `test_entry_has_required_fields`: All required fields present
- **TestGetActiveABTestStatus** (2 tests):
  - `test_returns_none_when_no_active_test`: No A/B test = None
  - `test_returns_none_when_no_method`: Missing method = None
- **TestCheckABPromotionStatus** (1 test):
  - `test_blocked_when_no_active_test`: No A/B test = blocked
- **TestCheckPromotionReadiness** (1 test):
  - `test_returns_blocked_when_registry_raises_exception`: Exception = blocked
- **TestSupervisorMutationSurfaceGate** (2 tests):
  - `test_mutation_surface_not_generated_when_gate_off`: No report in idle
  - `test_mutation_surface_generated_when_gate_on`: Report generated in idle
- **TestMutationSurfaceNoMutation** (2 tests - regression):
  - `test_build_mutation_surface_does_not_call_schedule_ab_test`: No mutation calls
  - `test_build_mutation_surface_entry_does_not_mutate`: No mutation calls

**Run**:
- `python -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_skill_evolution.py -q`

**Result**:
- `41 passed` (18 Phase 1 + 23 Phase 2)

---

## 2026-03-29: OpenClaw Authority & Mutation Gate Hardening (WSP 00 / WSP 95)

**File**: `test_openclaw_dae.py` (extended + updated - security tests)
- **TestIntentClassification** (updated for hardened commander authority):
  - `test_local_channel_grants_commander_authority`: voice_repl grants authority regardless of display name
  - `test_local_repl_grants_commander_authority`: local_repl grants authority regardless of display name
  - `test_remote_channel_requires_display_name_match`: Remote impostor correctly blocked
  - `test_remote_channel_with_display_name_match_is_NOT_commander`: **Remote display-name match is NOT commander** (hardened)
  - `test_commander_detection_local_channel`: Updated to use local channel (was `test_commander_detection_undaodu`)
- **TestSecurityCriticalFilePaths** (6 new tests for mutation gate):
  - `test_detects_env_file`: .env detected as source modification target
  - `test_detects_bat_file`: .bat scripts detected
  - `test_detects_cmd_file`: .cmd scripts detected
  - `test_detects_gitignore`: .gitignore detected
  - `test_detects_dockerignore`: .dockerignore detected
  - `test_no_false_positive_on_env_suffix`: config.env does not false-positive on .env
- **TestGemmaHybridIntegration** (updated):
  - `test_foundup_intent_with_gemma_disabled`: Updated to use `local_repl` channel

**Run**:
- `python -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -q`

**Result**:
- `102 passed, 1 failed` (pre-existing unrelated shutil mock issue)

---

## 2026-03-28: OpenClaw Bounded Maintenance Loop

**File**: `openclaw_maintenance_selector.py` (NEW)
- `MaintenanceTask` dataclass with family, risk_level, escalation tracking
- `select_maintenance_task()` selects safe low-risk tasks with HoloIndex bundle
- `write_maintenance_report()` writes structured report artifacts
- **ALLOWED_TASK_FAMILIES (Phase 1 - real executors only)**:
  - `self_audit_fix`: source == "self_audit"
  - `grant_review`: "openclaw-grants" in required_skills
  - `startup_maintenance`: source == "startup_maintenance_gate"
- `BLOCKED_TASK_FAMILIES`: source_edit, architecture_change, dependency_update, config_mutation, external_api_call

**File**: `openclaw_supervisor.py` (integration)
- `_triage()` now includes bounded maintenance task selection (gated by `OPENCLAW_MAINTENANCE_ENABLED`)
- `_triage()` reads self-audit events from JSONL and triggers `execute_self_audit_fix` action
- `_get_pending_self_audit_event()` reads pending events with allowed fixes from JSONL
- `_execute()` handles `execute_maintenance_task` and `execute_self_audit_fix` actions
- `_verify()` validates maintenance tasks and writes report artifacts
- `_plan()` carries maintenance_selection metadata

**File**: `test_openclaw_maintenance_selector.py` (NEW)
- 13 tests covering task selection, escalation, report generation
- TestMaintenanceTaskDataclass: is_safe logic, serialization
- TestSelectMaintenanceTask: safe selection, escalation, unknown family handling
- TestWriteMaintenanceReport: success/failure artifact generation
- TestAllowedTaskFamilies: configuration validation

**File**: `test_openclaw_supervisor.py` (extended)
- 3 new tests for self-audit triage path (JSONL)
- `test_self_audit_triage_returns_execute_action`: JSONL event with allowed fix triggers action
- `test_self_audit_triage_skips_already_attempted`: Events with `auto_fix_attempted=True` skipped
- `test_self_audit_triage_ignores_non_allowed_fixes`: Events with non-allowed fixes ignored
- 1 new end-to-end test for maintenance loop (AgentDB -> run_task.py)
- `test_maintenance_loop_e2e_self_audit_via_agentdb`: Full flow through AgentDB task selection, supervisor triage, run_task dispatch, and completion

**Run**:
- `python -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_maintenance_selector.py -q`
- `python -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_supervisor.py -q`

**Result**:
- `13 passed` (maintenance selector)
- `18 passed` (supervisor with self-audit triage + e2e tests)

---

## 2026-03-27: OpenClaw HoloIndex Execution Bundle

**File**: `openclaw_execution_bundle.py` (NEW)
- `ExecutionBundle` dataclass with query, route, docs, patterns, candidate_paths, constraints, verification_hints, confidence, code_hits, wsp_hits
- `build_execution_bundle()` retrieves compact context from HoloIndex (single search, stores raw hits)
- `retrieve_bundle_for_memory_query()` specialized function for memory queries
- WSP 87 (Semantic Code Discovery) + WSP 97 (System Execution) compliance

**File**: `openclaw_execution_routes.py` (integration)
- `execute_query()` uses bundle's code_hits/wsp_hits directly (no duplicate HoloIndex search)
- Bundle verification_hints appear in response output
- Candidate paths fallback when HoloIndex returns no hits
- Debug logging: `[OPENCLAW-DAE] [BUNDLE] query=... conf=... candidates=... code=... wsp=...`

**File**: `test_openclaw_execution_bundle.py` (NEW)
- 16 tests covering dataclass, bundle building, memory queries, route integration
- TestExecutionBundleDataclass: defaults, is_actionable, to_compact_dict, code_hits/wsp_hits storage
- TestBuildExecutionBundle: graceful HoloIndex unavailability, doc inference, verification hints, raw hits storage
- TestMemoryQueryBundle: high confidence, constraints, verification hints
- TestExecutionRouteIntegration:
  - `test_execute_query_uses_bundle_hits_not_separate_search`: proves bundle data affects response
  - `test_execute_query_no_duplicate_holoindex_search`: proves only one HoloIndex search
  - `test_bundle_candidate_paths_used_when_no_holoindex_hits`: proves fallback behavior

**Run**:
- `python -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_execution_bundle.py -q`

**Result**:
- `16 passed`

---

## 2026-03-27: OpenClaw Supervisor Runtime Emitter + Test Fix

**File**: `openclaw_supervisor.py` (instrumentation)
- `_execute()` now emits `supervisor_execute` events via `runtime_emitter.py`
- Events cover all action paths: start_openclaw, execute_autonomous_task, execute_self_audit_fix
- Events include: action type, task_id (when applicable), executor on success, error on failure

**File**: `test_openclaw_supervisor.py` (test fix)
- Fixed 4 failing tests that didn't enable `OPENCLAW_AUTO_TASKS_ENABLED` circuit breaker
- Tests now use `patch.dict(os.environ, {"OPENCLAW_AUTO_TASKS_ENABLED": "1"})` to trigger PLAN state

**Run**:
- `python -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_supervisor.py -q`

**Result**:
- `14 passed`

---

## 2026-03-23: Supervisor Memory Nudge Tests (P1)
- Command: `pytest modules/communication/moltbot_bridge/tests/test_openclaw_supervisor.py -q`
- Status: PASS
- Result: `14 passed` (7 existing + 7 new nudge tests)
- Coverage:
  - VERIFY failure emits nudge: trigger_type=supervisor_verify_failure, priority=P1
  - Budget exhausted escalation emits P0 nudge
  - Broker unavailable escalation emits P1 nudge
  - Identical escalations deduplicate cleanly (signature-based)
  - **Different task failures produce different signatures** (task_id + error in title)
  - Successful cycles do NOT emit nudges
  - Breadcrumb recording invoked with record_breadcrumbs=True

---

## 2026-03-23: Grant Task Pipeline Tests (P0)
- Command: `pytest modules/communication/moltbot_bridge/tests/test_grant_task_execution.py modules/communication/moltbot_bridge/tests/test_hardening_tranche.py -k grant -q`
- Status: PASS
- Result: `29 passed` (21 + 8)
- Coverage:
  - Grant executor: review returns structured findings, stabilize categorizes errors
  - Dispatch: recognizes grant_watchlist_review/stabilize, fails closed on unknown
  - Stable IDs: deduplication via INSERT OR REPLACE
  - Completed protection: same-context skip, changed-context reopens
  - Stale cleanup: combined filter (task_id LIKE + skill tag), preserves PQN/ecosystem
  - Regression: real-DB test seeds old slugified + PQN + ecosystem rows, asserts correct deletions

---

## 2026-03-23: Memory Nudge Engine (P0)
- Command: `pytest modules/communication/moltbot_bridge/tests/test_memory_nudge_engine.py -q`
- Status: PASS
- Result: `16 passed` (audit-hardened)
- Coverage:
  - NudgeEvent: signature auto-generation, stability, uniqueness
  - MemoryNudgeEngine: creates note on qualifying event
  - Deduplication: skips repeated events, loads existing signatures
  - Low-signal filter: ignores P3/P4 priority items
  - Provenance: note includes source artifact path
  - Self-research trigger: P0/P1 update candidates, new autonomous tasks
  - Grant watchlist trigger: human gate required, deadline approaching
  - Worktree pressure trigger: high audit backlog
  - Convenience functions: scan_nudge_events, emit_memory_nudges

---

## 2026-03-23: Session recall search foundation (breadcrumb integration)
- Command: `pytest modules/communication/moltbot_bridge/tests/test_openclaw_memory_queries.py -q`
- Status: PASS
- Result: `20 passed` (audit-hardened)
- Coverage:
  - Decision query: finds matching memory + breadcrumbs, returns provenance
  - Past work query: with topic, matches workspace memory
  - Past work query: without topic, **includes workspace memory** (not breadcrumbs-only)
  - Past work query: explicit provenance tags
  - **Time qualifier normalization**: `yesterday` → `None` (not literal topic)
  - Breadcrumb search: graceful degradation if AgentDB unavailable
  - Intent detection: past work variants (`show past work on X`)
  - Intent detection: working-on variants (`what was I working on`)
  - False positive prevention: all existing tests remain passing

---

## 2026-03-23: Deterministic memory queries (P0)
- Command: `pytest modules/communication/moltbot_bridge/tests/test_openclaw_memory_queries.py -q`
- Status: PASS
- Result: `12 passed` (audit-hardened)
- Coverage:
  - Decision query: finds matching memory, returns provenance
  - Decision query: explicit insufficient-evidence response
  - Unresolved work: reads native queue status
  - Unresolved work: reads self-research status
  - Unresolved work: explicit empty response
  - Recent sessions: lists workspace memory notes
  - Recent sessions: handles empty memory
  - Intent detection: decision query variants
  - Intent detection: unresolved work variants
  - Intent detection: non-memory queries fall through
  - False positive: `openclaw model` does NOT match unresolved work
  - False positive: `latest WSP docs` does NOT match recent sessions

---

## 2026-03-18: Cursor-based DAE follow runtime

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest modules/communication/moltbot_bridge/tests/test_dae_runtime_adapter.py modules/communication/moltbot_bridge/tests/test_openclaw_dae_runtime_commands.py -q`
- Status: PASS
- Notes:
  - Validates `watch openclaw since <sequence>` parses to the follow path.
  - Confirms OpenClaw runtime supervision now returns `next_cursor` for incremental polling.

---

## 2026-03-18: Resident OpenClaw launch contract

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_resident_launch.py modules/communication/moltbot_bridge/tests/test_dae_runtime_adapter.py -q`
- Status: PASS
- Notes:
  - Validates broker-safe resident OpenClaw launch/stop hooks.
  - Confirms generic DAE runtime control remains stable with `openclaw` as a launchable runtime alias.

---

## 2026-03-16: PQN simulation runtime command routing

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest modules/communication/moltbot_bridge/tests/test_pqn_research_adapter.py modules/communication/moltbot_bridge/tests/test_openclaw_dae_runtime_commands.py modules/infrastructure/dae_daemon/tests/test_dae_adapter.py -q`
- Status: PASS
- Notes:
  - Validates `run/status pqn simulation` routing through the PQN research adapter.
  - Confirms OpenClaw RESEARCH route passes the DAEmon action reporter into the adapter.
  - Confirms structured `details` payloads are preserved in DAEmon action events.

---

## 2026-03-15: Generic DAE runtime command routing

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest modules/communication/moltbot_bridge/tests/test_dae_runtime_adapter.py modules/communication/moltbot_bridge/tests/test_openclaw_dae_runtime_commands.py modules/communication/moltbot_bridge/tests/test_pqn_research_adapter.py modules/infrastructure/dae_daemon/tests/test_dae_launch_broker.py -q`
- Status: PASS
- Result: `14 passed, 2 warnings`
- Notes:
  - Validates generic broker-managed DAE runtime commands through OpenClaw.
  - Confirms PQN runtime commands remain stable on top of the generic broker layer.

---

# TestModLog - tests

## 2026-03-11: OpenClaw bootstrap constructor extraction regression

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "identity_query or model_switch or qwen3_5 or platform_context or agentic_model_selection_routes_code_turn_to_coder or connect_wre or runtime_profile or preferred_external" -q`
- Status: PASS
- Result: `21 passed, 75 deselected, 2 warnings`
- Notes:
  - Confirms `openclaw_bootstrap_config.py` preserves constructor-initialized identity, platform-context, preferred-external, and agentic model state after extraction from `openclaw_dae.py`.
  - Warnings are existing repo-level pytest config warnings under plugin-autoload-disabled mode.

---

## 2026-03-11: OpenClaw provider/runtime chain extraction regression

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "identity_query or model_switch or qwen3_5 or platform_context or connect_wre or preferred_external or runtime_profile" -q`
- Status: PASS
- Result: `20 passed, 76 deselected, 2 warnings`
- Notes:
  - Confirms `openclaw_provider_chain.py` and the `openclaw_runtime_support.py` autostart extraction preserve provider selection, runtime-profile gates, and conversation identity behavior after extraction from `openclaw_dae.py`.
  - Warnings are existing repo-level pytest config warnings under plugin-autoload-disabled mode.

---

## 2026-03-11: OpenClaw identity/model-policy extraction regression

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "identity_query or model_switch or qwen3_5 or platform_context or agentic_model_selection_routes_code_turn_to_coder or connect_wre" -q`
- Status: PASS
- Result: `20 passed, 76 deselected, 2 warnings`
- Notes:
  - Confirms `openclaw_identity_context.py` and `openclaw_model_policy.py` preserve existing identity, model-switch, platform-context, and agentic model-routing behavior after extraction from `openclaw_dae.py`.
  - Warnings are existing repo-level pytest config warnings under plugin-autoload-disabled mode.

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_dae_social_actions.py -q`
- Status: PASS
- Result: `7 passed, 2 warnings`
- Notes:
  - Confirms the new extraction does not regress OpenClaw social-action identity/status surfaces.

---

## 2026-03-11: OpenClaw social/conversation extraction regression

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_dae_social_actions.py modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "social or conversation or identity_query or model_switch or connect_wre" -q`
- Status: PASS
- Result: `56 passed, 47 deselected, 2 warnings`
- Notes:
  - Confirms `openclaw_social_controller.py` and `openclaw_conversation_engine.py` preserve the public `OpenClawDAE` behavior after extraction from `openclaw_dae.py`.

---

## 2026-03-10: OpenClaw runtime/identity helper extraction regression

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "structured_actions_to_central_daemon or model_availability_snapshot or qwen3_5 or identity_query" -q`
- Status: PASS
- Result: `10 passed, 86 deselected, 2 warnings`
- Notes:
  - Confirms `openclaw_action_ledger.py` and `openclaw_runtime_support.py` preserve existing identity/model-selection/runtime behavior after extraction from `openclaw_dae.py`.
  - Warnings are existing repo-level pytest config warnings under plugin-autoload-disabled mode.

---

## 2026-03-10: OpenClaw DAEmon action ledger regression

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "structured_actions_to_central_daemon" -q`
- Status: PASS
- Result: `1 passed, 95 deselected, 2 warnings`
- Notes:
  - Confirms the OpenClaw autonomy loop emits structured DAEmon action events in addition to `message_in` / `message_out`.
  - Warnings are existing repo-level pytest config warnings under plugin-autoload-disabled mode.

---

## 2026-03-05: Post-escalation shared security regression sweep

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q modules/infrastructure/wre_core/tests/test_codeact_executor_hardening.py modules/infrastructure/wre_core/tests/test_dependency_security_preflight.py modules/infrastructure/wre_core/tests/test_skill_manifest_guard.py modules/infrastructure/wre_core/tests/test_dae_preflight_integration_guard.py modules/infrastructure/wre_core/tests/test_dae_preflight_security_behavior.py modules/infrastructure/wre_core/wre_master_orchestrator/tests/test_wre_master_orchestrator.py modules/communication/moltbot_bridge/tests/test_skill_safety_guard.py -k "supply_chain_gate or hardening or dependency or manifest or self_audit or preflight"`
- Status: PASS
- Result: `16 passed, 30 deselected, 2 warnings`
- Notes:
  - Confirms Moltbot skill-safety + manifest lanes remain stable after 0102 self-audit escalation phase.

---

## 2026-03-05: Shared WSP 15 security regression sweep (includes skill safety gate)

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q modules/infrastructure/wre_core/tests/test_daemon_self_audit_loop.py modules/infrastructure/wre_core/tests/test_codeact_executor_hardening.py modules/infrastructure/wre_core/tests/test_dependency_security_preflight.py modules/infrastructure/wre_core/tests/test_skill_manifest_guard.py modules/infrastructure/wre_core/tests/test_dae_preflight_integration_guard.py modules/infrastructure/wre_core/tests/test_dae_preflight_security_behavior.py modules/infrastructure/wre_core/wre_master_orchestrator/tests/test_wre_master_orchestrator.py modules/communication/moltbot_bridge/tests/test_skill_safety_guard.py -k "supply_chain_gate or hardening or dependency or manifest or self_audit or preflight"`
- Status: PASS
- Result: `20 passed, 30 deselected, 2 warnings`
- Notes:
  - Confirms Moltbot skill safety and manifest/security controls remain stable alongside WRE self-audit and preflight hardening.
  - Warnings are repo-level pytest config warnings (`asyncio_*`) under plugin-autoload-disabled mode.

---

## 2026-02-16: Cross-module concatenated validation (identity-anchor hardening)

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests modules/foundups/agent_market/tests modules/foundups/simulator/tests -q`
- Status: PASS
- Result: `335 passed, 2 warnings`
- Notes:
  - Confirms OpenClaw conversation identity-anchor normalization resolves
    nondeterministic conversation assertions in end-to-end tests.
  - Includes SSE member-gate + DEX stream contract + symbol guardrail lanes.
  - Warnings are repo-level pytest config warnings (`asyncio_*`) under plugin-autoload-disabled mode.

---

## 2026-02-16: Cross-module concatenated validation

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests modules/foundups/agent_market/tests modules/foundups/simulator/tests -q`
- Status: PASS
- Result: `321 passed, 2 warnings`
- Notes:
  - Confirms FAM adapter and Moltbook adapter compatibility updates did not regress OpenClaw test coverage.
  - Warnings are repo-level pytest config warnings (`asyncio_*`) under plugin-autoload-disabled mode.

---

## 2026-02-08: Hardening Tranche - 72 tests passing

- Command: `.\modules\communication\moltbot_bridge\tests\run_tests.ps1`
- Status: PASS
- Result:
  - Security gate: PASS (3 files: skill_boundary_policy, skill_safety_guard, hardening_tranche)
  - Full suite: `72 passed`
- Notes:
  - Added `test_hardening_tranche.py` (17 new tests):
    - SOURCE tier enforcement: 6 tests (fail-closed, permission check, exceptions, event emission, dedupe)
    - Webhook rate limiting: 6 tests (token bucket, sender/channel isolation, refill, disabling)
    - COMMAND graceful degradation: 5 tests (WRE unavailable, exception, advisory content, error detail)
  - CI gate now includes `test_hardening_tranche.py` as security-critical.
  - Test count progression: 20 -> 34 -> 45 -> 55 -> 72

---

## 2026-02-07: Security gate + full suite validation (post-hardening)
- Command: `.\modules\communication\moltbot_bridge\tests\run_tests.ps1`
- Status: PASS
- Result:
  - Security gate: PASS (`test_skill_boundary_policy.py`, `test_skill_safety_guard.py`)
  - Full suite: `55 passed`
- Notes:
  - CI now fails fast if security gate tests fail.
  - `-SkipSecurityGate` is for local diagnostics only.

## 2026-02-07: Skill boundary policy enforcement tests
- Command: `.\modules\communication\moltbot_bridge\tests\run_tests.ps1`
- Status: PASS
- Notes:
  - Added `test_skill_boundary_policy.py`.
  - Enforces codified boundary between OpenClaw workspace skills and internal `skillz`.
  - Verifies all mutating intent categories call `_ensure_skill_safety()`.
  - Full module suite currently: `45 passed`.

## 2026-02-07: Deterministic runner entrypoint
- Command: `powershell -NoProfile -ExecutionPolicy Bypass -File modules/communication/moltbot_bridge/tests/run_tests.ps1`
- Status: PASS
- Result: 34 passed, 2 warnings
- Notes:
  - Canonical test entrypoint now codified in `run_tests.ps1`.
  - Runner pins local venv python and disables third-party pytest plugin autoload for deterministic execution.

## 2026-02-07: WSP 95/71 Security Audit Test Coverage
- Command: `.\modules\communication\moltbot_bridge\tests\run_tests.ps1`
- Status: PASS
- Result: 34 passed, 2 warnings
- Notes: Added 14 comprehensive skill safety guard tests for WSP 95/71 compliance:
  - Unit tests: scanner missing, zero/nonzero exit, severity thresholds (high/medium/low/critical)
  - Integration tests: required mode blocking, cache TTL, cache expiry, enforced/non-enforced modes
  - All mutating DAE entrypoints audited and confirmed gated

## 2026-02-07 (earlier)
- Command: `.\modules\communication\moltbot_bridge\tests\run_tests.ps1`
- Status: PASS
- Result: 20 passed, 2 warnings
- Notes: Includes skill safety guard tests and OpenClaw DAE routing tests.

## 2026-03-06: Qwen3.5 model-switch coverage
- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "qwen3_5 or model_switch_local_qwen3_5_updates_conversation_target or model_availability_snapshot_includes_qwen3_5_target" -q`
- Status: PASS
- Result: `2 passed, 84 deselected, 2 warnings`
- Notes:
  - Added regression coverage for `switch model to qwen3.5`.
  - Added availability snapshot assertion for `local/qwen3.5-4b`.

## 2026-03-07: ZeroClaw runtime profile regression coverage
- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "zeroclaw or runtime_profile or model_switch_external_blocked_by_zeroclaw_profile" -q`
- Status: PASS
- Result: `3 passed, 86 deselected, 2 warnings`
- Notes:
  - Validates `OPENCLAW_RUNTIME_PROFILE=zeroclaw` forces fail-closed external policy.
  - Validates external model-switch commands are blocked under ZeroClaw.
  - Validates mutating intent is downgraded to conversation route in full `process()` loop.

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -q`
- Status: PASS
- Result: `89 passed, 2 warnings`
- Notes:
  - Full-file regression confirms new runtime-profile gates do not break existing OpenClaw DAE behavior.

## 2026-03-15: PQN runtime broker adapter tests

**Files**
- `test_pqn_research_adapter.py`

**Coverage**
- `launch pqn research` -> broker `start_dae("pqn_research")`
- `status pqn architect` -> broker status rendering
- `stop pqn research` -> broker `stop_dae("pqn_research")`
- missing broker fallback text

**Run**
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest modules/communication/moltbot_bridge/tests/test_pqn_research_adapter.py -q`

**Result**
- `4 passed`
## 2026-03-10: LinkedIn mission-control + agentic routing regression coverage
- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_linkedin_loop_adapter.py modules/communication/moltbot_bridge/tests/test_openclaw_dae_social_actions.py modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -q`
- Status: PASS
- Result: `106 passed, 2 warnings`
- Notes:
  - Validates conversational LinkedIn loop control through `linkedin_loop_adapter`.
  - Confirms `WSP_97_System_Execution_Prompting_Protocol.md` is present in the default OpenClaw context pack.
  - Validates OpenClawDAE actually routes LinkedIn loop-control phrases through the loop adapter.
  - Regresses mixed code/triage prompts so code-change turns route to `local/qwen-coder-7b`.
  - Validates explicit `follow wsp ...` command routing through the dedicated WSP orchestrator path.

## 2026-03-10: WSP 97 follow-wsp deterministic route smoke slice
- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "follow_wsp or platform_context or agentic_model_selection_routes_code_turn_to_coder" -q`
- Status: PASS
- Result: `5 passed, 90 deselected, 2 warnings`
- Notes:
  - Confirms `follow wsp ...` uses the dedicated WSP orchestrator route.
  - Confirms default platform context still includes `WSP_97`.
  - Confirms code-heavy mixed prompts still route to `local/qwen-coder-7b`.

## 2026-03-11: OpenClaw intent/result seam regression coverage
- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "classify_intent or wsp_preflight or follow_wsp or validate_and_remember or connect_wre or model_switch or identity_query" -q`
- Status: PASS
- Result: `15 passed, 81 deselected, 2 warnings`
- Notes:
  - Confirms extracted intent classification still honors `connect wre`, identity, model switch, and WSP preflight behavior.
  - Confirms extracted validate/remember path still stores and redacts as expected.

## 2026-03-11: OpenClaw permission-policy regression coverage
- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "permission or source or skill_safety or containment or classify_intent or wsp_preflight or validate_and_remember" -q`
- Status: PASS
- Result: `17 passed, 79 deselected, 2 warnings`
- Notes:
  - Confirms autonomy-tier resolution, SOURCE gating, containment, and skill-safety behavior survived extraction to `openclaw_permission_policy.py`.
  - Confirms no regression in extracted intent/result seams while permission policy was moved.

## 2026-03-11: OpenClaw execution-route regression coverage
- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "query or command or follow_wsp or monitor or schedule or automation or foundup or research" -q`
- Status: PASS
- Result: `29 passed, 67 deselected, 2 warnings`
- Notes:
  - Confirms route delegation through `openclaw_execution_routes.py` for all non-social execution planes.
  - Confirms `follow wsp` deterministic routing still executes through the WSP orchestrator after extraction.

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "monitor_returns_status or execute_command_follow_wsp_uses_wsp_orchestrator or identity_query_defaults_to_compact_response" -q`
- Status: PASS
- Result: `3 passed, 93 deselected, 2 warnings`
- Notes:
  - Smoke-checks compact identity, monitor status, and WSP route execution after route-layer extraction.

## 2026-03-11: OpenClaw telemetry + turn-state regression coverage
- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "token_usage or turn_cancellation or identity_query_defaults_to_compact_response or monitor_returns_status" -q`
- Status: PASS
- Result: `4 passed, 92 deselected, 2 warnings`
- Notes:
  - Confirms extracted token telemetry still feeds identity/monitor status correctly.
  - Confirms cooperative turn cancellation still interrupts live turns cleanly after extraction.

## 2026-03-11: OpenClaw status/process regression coverage
- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "test_conversation_returns_response or test_blocked_command_downgrades_to_conversation or test_monitor_returns_status or test_zeroclaw_downgrades_mutating_intent_to_conversation_route or test_process_reports_structured_actions_to_central_daemon" -q`
- Status: PASS
- Result: `5 passed, 91 deselected, 2 warnings`
- Notes:
  - Confirms the extracted `openclaw_process_loop.py` preserves end-to-end autonomy behavior and DAEmon action emission.

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "token_usage_query_returns_deterministic_report or conversation_honors_turn_cancellation or execute_command_follow_wsp_uses_wsp_orchestrator or monitor_reports_lineage_and_model_name" -q`
- Status: PASS
- Result: `4 passed, 92 deselected, 2 warnings`
- Notes:
  - Confirms extracted status/telemetry surfaces still drive token usage, cancellation, monitor, and follow-wsp behavior correctly.

## 2026-03-17: Runtime supervision adapter coverage
- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest modules/communication/moltbot_bridge/tests/test_dae_runtime_adapter.py modules/communication/moltbot_bridge/tests/test_openclaw_dae_runtime_commands.py -q`
- Status: PASS
- Result: `11 passed`
- Notes:
  - Confirms `tail <dae>` and `status <dae> live` classify as monitor intents.
  - Confirms OpenClaw runtime supervision for `openclaw` routes through the new DAEmon observer path.

## 2026-03-18: PQN simulation runtime alignment coverage
- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest modules/communication/moltbot_bridge/tests/test_pqn_research_adapter.py modules/communication/moltbot_bridge/tests/test_dae_runtime_adapter.py modules/communication/moltbot_bridge/tests/test_openclaw_dae_runtime_commands.py -q`
- Status: PASS
- Result: `25 passed`
- Notes:
  - Confirms `run pqn simulation` is now classified as broker/runtime control instead of inline research execution.
  - Confirms `show pqn simulation plan` stays on the RESEARCH read path.
  - Confirms `pqn_simulation` is visible to generic DAE runtime supervision commands.

## 2026-03-18: OpenClaw supervisor runtime coverage
- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_supervisor.py modules/communication/moltbot_bridge/tests/test_openclaw_resident_launch.py modules/communication/moltbot_bridge/tests/test_dae_runtime_adapter.py -q`
- Status: PASS
- Result: `20 passed`
- Notes:
  - Confirms the explicit supervisor state machine restarts resident OpenClaw when runtime status is down.
  - Confirms `openclaw_supervisor` is exposed through the runtime adapter aliases.
  - Confirms the broker launch wrapper starts and stops the supervisor service cleanly.

## 2026-03-23: AI Overseer integration in supervisor planning (P1)
- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_supervisor.py modules/communication/moltbot_bridge/tests/test_openclaw_supervisor_p0.py -q`
- Status: PASS
- Result: `8 passed`
- Coverage:
  - Confirms AI Overseer `analyze_mission_requirements()` is called during `_plan()` state.
  - Confirms normal shape (`classification.complexity`) populates `ai_analysis.complexity`.
  - Confirms fallback shape (top-level `complexity`) normalizes correctly (was degrading to 0).
  - Confirms AI Overseer exceptions store error in `ai_analysis` without failing the plan.
  - P0 test: Confirms headless dispatch wires through WRE.

---

## 2026-03-18: OpenClaw supervisor repair-budget coverage
- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_supervisor.py -q`
- Status: PASS
- Result: `4 passed`
- Coverage:
  - Confirms the supervisor advances the DAEmon follow cursor during idle and repair cycles.
  - Confirms restart attempts are bounded by policy and escalate when the repair budget is exhausted.
  - Confirms failed verify cycles are still remembered before escalation.

## 2026-08-03: Upstream Hermes API provider gate

- Added real `/v1/runs` adapter tests for signed principal routing, fixed
  loopback transport, confined bearer-key loading, exact upstream identity,
  disabled toolsets, empty skills, post-run policy drift, approval/tool abort,
  malicious run IDs, duplicate JSON, unsafe artifact paths, and secret
  non-disclosure.
- Re-ran the OpenClaw provider and shared upstream-provider bootstrap suites to
  prove the two actual scaffolds share authority and materialization contracts
  without sharing execution implementations.
## 2026-08-04: Root verified-outcome service regressions

- Proved only a root-UID socket exchange can mint the signer-side authority;
  caller functions, wrong peers, response substitution, malformed startup, and
  absent service responses fail before signing authority is usable.
- Proved exactly one concurrent reservation wins, commit records the exact
  signature digest, replay stays burned across restart, revocation between
  reserve and commit rejects, and authority-generation rollback fails closed.
- Proved one-sided root-state loss repairs from the independent witness while
  production state construction rejects a non-root principal.
- Proved service initialization is explicit, startup failures do not echo raw
  exception content, and the peer policy binds exactly one signer UID/GID and
  principal.
- Proved the legacy signer CLI always rejects without authority, resolver, or
  socket effects, and the stable entrypoint passes the exact root-owned signer
  UID/GID into the pre-key Linux isolation gate.
## 2026-08-06 - Authenticated Principal Memex resident admission

- Added signature, resolver-substitution, malformed revocation, model-binding,
  expiry, record-mutation, atomic replay, durable replay, opacity, bounded
  content, and no-caller-projection regressions.
- Added nested mutation, pre-model digest revalidation, and stable-cognition
  duplicate-cycle regressions for independently reviewed security findings.
- Added an end-to-end backend architect test proving only the authenticated
  accepted principal decision reaches the model and an expired context prevents
  any model call.
- Added WSP 62 and effect-surface AST guards for the new runtime modules.
