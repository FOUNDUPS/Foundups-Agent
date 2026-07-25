# foundups_mcp_bridge TestModLog

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
