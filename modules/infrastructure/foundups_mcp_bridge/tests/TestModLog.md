# foundups_mcp_bridge TestModLog

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
