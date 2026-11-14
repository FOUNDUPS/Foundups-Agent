# FOUNDUP_AUTO_TEST_MATRIX_COVERAGE_PHASE1

**Slice:** FOUNDUP_AUTO_TEST_MATRIX_COVERAGE_PHASE1
**Worker-Lane:** W6
**Author:** 0102 (WSP_00 zen state, WSP_50/WSP_87 HoloIndex-first, WSP_97 Truth Boundary)
**Type:** READ-ONLY audit. No code/test/registry/manifest/WSP changes. Discovery only.

---

## 1. Mission and Scope

Produce the authoritative 16-FoundUp auto-test coverage matrix needed BEFORE WRE/OpenClaw/
Hermes can safely run autonomous build/test loops against FoundUps. This is Phase 1 discovery
only: characterize coverage, classify each gap, and recommend per-gap follow-up slices. It does
NOT generate tests and makes NO autonomous-build claim. Exactly one file is produced (this audit).

Scope decision (012, this slice): the original dispatch body was truncated after the HoloIndex
pre-work; implementation scope was NOT inferred. Confirmed READ-ONLY AUDIT DOC ONLY.

---

## 2. Predecessor: #762

`#762` (WRE_OPENCLAW_HERMES_AUTONOMOUS_BUILD_DRYRUN_PHASE1, merged -> origin/main `176da8a13`)
produced a first FoundUp coverage matrix (16 total, 11 HAS_TESTS, 5 NO_TEST_COVERAGE) as a
sub-finding and recommended this slice to verify and refine it. This audit independently
re-derives the matrix on current main (not relayed) and adds gap sub-classification, manifest
coverage, and per-gap next slices.

---

## 3. HoloIndex Pre-Work Results (WSP 50/87)

Four mandated queries (`python holo_index.py --search ...`):

| # | Query | Top hits | Useful? | Opened because of it |
|---|-------|----------|---------|----------------------|
| 1 | FoundUp registry test matrix foundup_id manifest tests | `agent_market/INTERFACE.md`, `fam_adapter.py`, `index_channel.py`; WSP_17/104/98 | Partial | none decisive (registry not surfaced) |
| 2 | foundup auto test coverage NO_TEST_COVERAGE | `agent_market/INTERFACE.md`, `index_channel.py`, `test_openclaw_dae.py`; **WSP_5/6/16** | Yes (WSPs) | WSP_5/6/16 cited as normative basis (Section 4) |
| 3 | modules foundups foundup_manifest test contract | `agent_market/INTERFACE.md`, `simulator/mesa_model.py`; WSP_3/55/9 | Partial | none decisive |
| 4 | WRE OpenClaw Hermes autonomous FoundUp dry-run test contract | `test_openclaw_dae.py`, `test_openclaw_security_sentinel.py`; WSP_41/46/72 | Partial | none decisive |

**`HOLOINDEX_LOW_SIGNAL`** for the per-FoundUp coverage matrix: the searches surfaced relevant
WSP protocols (5/6/16 test coverage; 3/55 module structure) and `agent_market` interfaces, but
did NOT surface `foundup_registry.json`, `foundup_registry_loader.py`, or the 16 per-FoundUp test
directories. This matches the audit-artifact indexing gap noted in #736/#737/#762. Matrix
construction therefore fell back to `rg` + direct registry read (Section 4).

---

## 4. Method: rg + Registry Direct Read (after HOLOINDEX_LOW_SIGNAL)

Normative basis: **WSP 5** (Test Coverage Enforcement), **WSP 6** (Test Audit Coverage
Verification), **WSP 16** (Test Audit Coverage).

Procedure (read-only):
1. Extract every `foundup_id` + `module_path` from `modules/foundups/foundup_registry.json`.
2. For each: verify module dir exists; count `test_*.py` files recursively
   (`find <module> -name "test_*.py" -type f`); check `tests/` dir; check
   `foundup_manifest.json` presence.
3. Read registry lifecycle fields (`implementation_status`, `stage`, `poc_status`, `notes`,
   `next_slice`, `related_external_repo`) for the gap entries to classify the *reason* for each gap.

All counts below are direct-observation evidence on `origin/main` `176da8a13`.

---

## 5. 16-FoundUp Registry Inventory

All 16 entries from `foundup_registry.json` (the registry is the source of truth):

gotjunk_001, kosei, voteballots, trade, magadoom_001, antifafm_001, pfmall, agent_market,
move2japan, simulator, social_twin, autopost, pqn_portal, science_swarm_hub, holoindex_prod_01,
shield.

---

## 6. Coverage Matrix

`test_paths_found` = count of `test_*.py` under the module path. `manifest` =
`foundup_manifest.json` present in module dir.

| foundup_id | module_path | manifest | test_paths_found | coverage_class | evidence |
|------------|-------------|----------|------------------|----------------|----------|
| gotjunk_001 | modules/foundups/gotjunk | YES | 1 | HAS_TESTS (thin) | 1 `test_*.py` in `tests/` |
| kosei | modules/foundups/kosei | YES | 5 | HAS_TESTS | 5 `test_*.py` |
| voteballots | modules/foundups/voteballots | YES | 8 | HAS_TESTS | 8 `test_*.py` |
| trade | modules/foundups/trade | YES | 11 | HAS_TESTS | 11 `test_*.py` |
| magadoom_001 | modules/gamification/whack_a_magat | YES | 14 | HAS_TESTS | 14 `test_*.py` |
| antifafm_001 | modules/platform_integration/antifafm_broadcaster | YES | 10 | HAS_TESTS | 10 `test_*.py` |
| pfmall | modules/foundups/pfmall | **NO** | 15 | HAS_TESTS | 15 `test_*.py`; manifest absent |
| agent_market | modules/foundups/agent_market | **NO** | 17 | HAS_TESTS | 17 `test_*.py`; manifest absent |
| move2japan | modules/foundups/move2japan | **NO** | 2 | HAS_TESTS (thin) | 2 `test_*.py`; manifest absent |
| simulator | modules/foundups/simulator | **NO** | 42 | HAS_TESTS | 42 `test_*.py`; manifest absent |
| social_twin | modules/foundups/social_twin | **NO** | 1 | HAS_TESTS (thin) | 1 `test_*.py`; manifest absent |
| autopost | (null) | NO | 0 | **MISSING_MODULE_PATH** | `module_path: null`; external repo O:/repos/AutoPost (`related_external_repo`) |
| pqn_portal | modules/foundups/pqn_portal | NO | 0 | **NO_TEST_COVERAGE** | `tests/` exists but only `README.md`+`__init__.py`; SCAFFOLD/placeholder (`implementation_status: SPECIFIED`) |
| science_swarm_hub | modules/foundups/pqn_swarm_hub | NO | 0 | **NO_SAFE_TEST_SURFACE** | monorepo stub delegates to installed external pkg; "108 tests passing" in `science-swarm-hub` repo, not in-tree |
| holoindex_prod_01 | modules/foundups/holoindex_prod_01 | YES | 0 | **NO_SAFE_TEST_SURFACE** | module dir = `README.md`+`foundup_manifest.json` only (public-surface pointer); real HoloIndex tested under `holo_index/` (DUAL IDENTITY boundary) |
| shield | modules/foundups/shield | YES | 0 | **NO_TEST_COVERAGE** | docs+manifest only, no `src/`; `implementation_status: SPECIFIED`, `poc_status: idea` (pre-implementation) |

**Coverage counts by class:** HAS_TESTS = 11 (3 thin: gotjunk_001, move2japan, social_twin);
NO_TEST_COVERAGE = 2; NO_SAFE_TEST_SURFACE = 2; MISSING_MODULE_PATH = 1; MISSING_MANIFEST
(primary) = 0.

**Secondary manifest finding:** 8/16 FoundUps lack a `foundup_manifest.json`
(pfmall, agent_market, move2japan, simulator, social_twin, pqn_portal, science_swarm_hub,
autopost). This is independent of test coverage but is a build-contract gap: an autonomous
build/test loop cannot read a FoundUp's build contract without a manifest. Flagged for a separate
manifest-readiness audit, NOT remediated here.

---

## 7. The 5 Starting Gaps from #762 - Verified on Current Main

| foundup_id | #762 said | This slice (verified on 176da8a13) | Still a gap? |
|------------|-----------|-------------------------------------|--------------|
| autopost | NO_TEST_COVERAGE (module ABSENT) | MISSING_MODULE_PATH (`module_path: null`, external repo) | YES (refined) |
| pqn_portal | NO_TEST_COVERAGE | NO_TEST_COVERAGE (empty `tests/`, scaffold) | YES |
| science_swarm_hub | NO_TEST_COVERAGE | NO_SAFE_TEST_SURFACE (external delegation, 108 ext tests) | YES (refined) |
| holoindex_prod_01 | NO_TEST_COVERAGE | NO_SAFE_TEST_SURFACE (public-surface pointer; tested under `holo_index/`) | YES (refined) |
| shield | NO_TEST_COVERAGE | NO_TEST_COVERAGE (SPECIFIED/idea, no `src/`) | YES |

All 5 remain gaps. The binary NO_TEST_COVERAGE label from #762 is refined into 3 distinct
reasons (missing module, in-repo no-tests, external/pointer no-safe-surface), which determines the
correct remediation per gap (Section 8).

---

## 8. Per-Gap Next-Slice Recommendation

| Gap | Target files to read | Minimal safe test contract | W6 implement vs W9 audit first |
|-----|----------------------|----------------------------|-------------------------------|
| autopost | registry entry; `O:/repos/AutoPost/` (external) | registry-membership + external-repo-reference assertion (module_path null is intentional for external) | **W9 audit first** (external/out-of-tree); then `AUTOPOST_EXTERNAL_FOUNDUP_MANIFEST_READINESS_PHASE1` (registry `next_slice`) |
| pqn_portal | `modules/foundups/pqn_portal/src/`, `tests/` | import + registry-membership + scaffold-status (`SPECIFIED`) test; defer behavioral tests until core logic exists | **W9 audit first** (scaffold/placeholder); then `PQN_PORTAL_SCIENCE_SWARM_MANIFEST_READINESS_PHASE1` (registry `next_slice`) |
| science_swarm_hub | `modules/foundups/pqn_swarm_hub/` stub; external `science-swarm-hub` repo | in-repo delegation-boundary test (stub imports/delegates); rely on external repo CI for behavioral coverage | **W9 audit first** (external delegation boundary) |
| holoindex_prod_01 | `modules/foundups/holoindex_prod_01/foundup_manifest.json`, `README.md`; `holo_index/tests/` | manifest-validity + registry-entry test (public surface); do NOT test internal HoloIndex via this entry (DUAL IDENTITY) | **W6 can implement** a manifest/registry-entry validity test (low risk, in-repo, no live) |
| shield | `modules/foundups/shield/foundup_manifest.json`, `ROADMAP.md`, `INTERFACE.md` | manifest-validity + registry-membership test; behavioral tests deferred until POC builds `src/` | **W9/architect first** (pre-implementation); `SHIELD_AUTOCASE_POC_PHASE1` (registry `next_slice`) builds code, then W6 tests |

Cross-cutting: a single **manifest-readiness** follow-up should address the 8 missing
`foundup_manifest.json` files independent of these 5 test gaps.

---

## 9. WSP_15 Priority Scoring for Follow-Up Test-Coverage Slice(s)

Two follow-up buckets:

**Bucket A - in-repo testable gaps now** (holoindex_prod_01 manifest/registry test; cross-cutting
manifest-readiness):

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Complexity | 2 | Manifest/registry-validity tests are simple, in-repo |
| Importance | 3 | Needed for safe autonomous build-contract reads |
| Deferability | 3 | Useful soon; not blocking today |
| Impact | 3 | Closes verifiable build-contract gaps |
| **Total** | **11/20 -> P2** | |

**Bucket B - blocked gaps** (autopost external, science_swarm_hub external, pqn_portal scaffold,
shield pre-impl): gated on prior work (external audit / POC build), so **P3 / deferred** until the
named precursor slices land. Scoring deferred (`DEFERRED_PENDING_PRECURSOR`).

Thin-coverage HAS_TESTS FoundUps (gotjunk_001, move2japan, social_twin = 1-2 tests) are a
distinct, lower-urgency coverage-depth concern (P3), not a NO_TEST_COVERAGE gap.

---

## 10. Internal Review Verdict

**READY.** The 16-FoundUp coverage matrix is independently verified on `origin/main` `176da8a13`
by direct registry read + `test_*.py` counts (not relayed from #762). All 5 starting gaps are
confirmed and refined into actionable classes; per-gap next slices, target files, minimal safe
test contracts, and W6-vs-W9 routing are specified. HoloIndex pre-work is recorded with
`HOLOINDEX_LOW_SIGNAL` and an `rg` fallback. No code/test/registry/manifest/WSP change; no
autonomous-build claim; exactly one file produced.

---

## 11. WSP_97 Truth Boundary Checklist

Declared count: 15 / 15 YES (rows below = 15).

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | READ_ONLY_AUDIT_ONLY | YES | Only this audit doc written |
| 2 | HOLOINDEX_LOW_SIGNAL_RECORDED | YES | Section 3 table + verdict |
| 3 | NO_CODE_CHANGE | YES | No `.py` modified |
| 4 | NO_TEST_CHANGE | YES | No test files added or modified |
| 5 | NO_REGISTRY_MUTATION | YES | `foundup_registry.json` read-only |
| 6 | NO_MANIFEST_MUTATION | YES | No `foundup_manifest.json` written |
| 7 | NO_WSP_MUTATION | YES | WSP_5/6/16 cited read-only |
| 8 | NO_AUTONOMOUS_BUILD_CLAIM | YES | Section 1 explicitly disclaims; matrix is pre-build discovery |
| 9 | NO_CABR_READY | YES | No CABR scoring/activation |
| 10 | NO_PAYOUT_READY | YES | No payout touched |
| 11 | NO_VERIFICATION_COMPLETE | YES | Discovery audit only; no verification claim |
| 12 | SIXTEEN_FOUNDUPS_INVENTORIED | YES | Section 5/6 (16 rows) |
| 13 | MATRIX_COVERAGE_CLASSES_ASSIGNED | YES | Section 6 (HAS_TESTS/NO_TEST_COVERAGE/NO_SAFE_TEST_SURFACE/MISSING_MODULE_PATH) |
| 14 | FIVE_GAPS_VERIFIED_ON_MAIN | YES | Section 7 (all 5 confirmed on 176da8a13) |
| 15 | EXACTLY_ONE_FILE | YES | Only `FOUNDUP_AUTO_TEST_MATRIX_COVERAGE_PHASE1.md` |

**WSP 97 Truth Boundary Checklist: 15/15 YES.**

---

*Authored by 0102 (Worker-Lane W6) under WSP_00 zen state, WSP_50/WSP_87 HoloIndex-first, and
WSP_97 Truth Boundary discipline. Read-only Phase-1 discovery: authoritative 16-FoundUp coverage
matrix independently verified on origin/main 176da8a13. 11 HAS_TESTS, 5 gaps (2 NO_TEST_COVERAGE,
2 NO_SAFE_TEST_SURFACE, 1 MISSING_MODULE_PATH) + an 8-FoundUp manifest gap. No tests generated.*
