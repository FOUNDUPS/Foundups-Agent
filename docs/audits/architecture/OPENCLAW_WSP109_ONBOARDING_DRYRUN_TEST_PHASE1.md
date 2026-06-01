# OPENCLAW_WSP109_ONBOARDING_DRYRUN_TEST_PHASE1

**Slice:** OPENCLAW_WSP109_ONBOARDING_DRYRUN_TEST_PHASE1
**Worker-Lane:** W6
**Author:** 0102 (WSP_00 zen state, WSP_97 Truth Boundary discipline)
**Type:** Characterization test slice — executable proof of CURRENT behaviour. **No fixes.**

---

## 1. Mission and Scope

PR #737 found that OpenClaw already owns the orchestration loop, but **WSP 109 FoundUp
onboarding is not enforced as a genesis/intake gate** before FOUNDUP execution. This slice
adds **characterization tests** that capture the *current* behaviour around WSP 109
onboarding and FOUNDUP routing as executable evidence, so the next remediation slice can be
precise. It does **not** change behaviour.

**Scope:** exactly 4 files — the new test, this audit, and the two ModLogs:
1. `modules/communication/moltbot_bridge/tests/test_openclaw_wsp109_onboarding_dryrun.py`
2. `docs/audits/architecture/OPENCLAW_WSP109_ONBOARDING_DRYRUN_TEST_PHASE1.md`
3. `modules/communication/moltbot_bridge/ModLog.md`
4. `modules/communication/moltbot_bridge/tests/TestModLog.md`

No production/source code changed. Known gaps are locked as **strict xfail** contracts.

---

## 2. Predecessor Citations

| PR | Slice | Relationship |
|----|-------|--------------|
| #737 | OPUS_4_8_OPENCLAW_INTERNAL_MODEL_PROBE_PHASE1 | Source of the gaps characterized here (S1, S5, §9.1#1-3) |
| #718 | WSP_109_FOUNDUP_ONBOARDING_INTAKE_PROTOCOL_PHASE1 | Defines the WSP 109 onboarding intake this slice probes |
| #725 | REDDOG_BOOTSTRAP_CONTEXT_RETRIEVAL_PHASE1 | RedDog bootstrap context consumed at boot |

---

## 3. HoloIndex Retrieval Evaluation

Five mandated queries run (`python holo_index.py --search ...`).

| # | Query | Top real hits | Quality |
|---|-------|---------------|---------|
| Q1 | OpenClaw WSP 109 FoundUp onboarding genesis gate | `openclaw_dae.py`, `WSP_109`, `WSP_106` | MEDIUM |
| Q2 | openclaw foundup orchestrator launch_foundup genesis envelope | `fam_adapter.py`, `agent_market/ARCHITECTURE.md`, `WSP_98` | MEDIUM |
| Q3 | openclaw execution routes foundup job router | `fam_adapter.py`, `WSP_104` (route namespace), `WSP_106` | MEDIUM |
| Q4 | validate genesis envelope FoundUp job | drift to `in_memory.py`, `action_pattern_learner.py`, `ai_overseer.py` | LOW |
| Q5 | OPUS_4_8_OPENCLAW_INTERNAL_MODEL_PROBE_PHASE1 | drift to `foundup-cube.js`, `test_openclaw_dae.py` | LOW |

**Assessment:** Q1-Q3 surfaced the right runtime surfaces (`fam_adapter.py`,
`openclaw_dae.py`) and governance refs (WSP 109/104/106). **Q4 did not surface
`openclaw_foundup_orchestrator.py`** — the file that actually defines
`validate_genesis_envelope` — a real retrieval gap; the file was reached by direct path.
Q5 again failed to surface the predecessor audit doc by slice name (consistent indexing gap
noted in #736/#737). All test assertions below are grounded in direct reads, not retrieval.

---

## 4. #737 Gap Summary (under test here)

| #737 ref | Gap | Characterized as |
|----------|-----|------------------|
| S1 | WSP 109 onboard does not route through an intake/genesis gate | Q1, Q2 |
| 9.1#1 | FOUNDUP permission/genesis bypass — `dispatch_foundup` bypasses gated `validate_genesis_envelope` | Q2 |
| 9.1#2 | Dual-parser ambiguity — `'create foundup X'` (FAM passthrough/real) vs `'create foundup job'` (queue dry-run) | Q3 |
| 9.1#3 | No W10 authority — `validate_and_remember` self-approves | Q4 |
| S5 | Protected-path edit is genuinely BLOCKED (fail-closed) | Q5 (PASS, not xfail) |

---

## 5. Characterization Test Design

`tests/test_openclaw_wsp109_onboarding_dryrun.py` — **11 tests** (7 PASS, 4 strict xfail).

Design principles:
- **Determinism only:** pure-function calls (`_is_explicit_build_intent`,
  `is_source_modification`, `check_source_permission`), `inspect.getsource` structural
  assertions, and lightweight `MagicMock`. **No live OpenClaw process, no network, no .env
  reads, no external model calls, no real GitHub writes.**
- **Two assertions per gap:** a PASS test that *locks current behaviour*, and a **strict
  xfail** test whose assertion states the *desired post-remediation behaviour* (so it XPASSes
  and fails the suite once fixed — a live remediation tripwire).
- **No `importlib.reload`:** `dispatch_foundup` imports `fam_adapter` at call-time, so
  `patch.dict(sys.modules, ...)` alone suffices. Reload was deliberately avoided because it
  pollutes the orchestrator module for downstream tests (see §6 note).

---

## 6. Current Behaviour Matrix

| Q | Question | Current behaviour (locked by PASS test) | Evidence |
|---|----------|------------------------------------------|----------|
| 1 | WSP 109 onboard → intake or direct FOUNDUP? | `'onboard … FoundUp'` is **not** an explicit-build trigger → FAM passthrough, **no intake** | `_is_explicit_build_intent(...) is False`; `'onboard' ∉ _FOUNDUP_BUILD_WORDS` |
| 2 | FOUNDUP dispatch calls genesis validator? | **No.** `dispatch_foundup` never references `validate_genesis_envelope`; a `launch foundup` msg reaches `fam_adapter.handle_fam_intent` with no gate | `inspect.getsource(dispatch_foundup)`; mocked-fam passthrough call |
| 3 | `create foundup X` vs `create foundup job`? | **Divergent:** bare = False (FAM passthrough/real), `job` = True (queue dry-run) | `_is_explicit_build_intent` on both phrasings |
| 4 | W10 handoff or self-approve? | **Self-approves:** `success=len(wsp_violations)==0`; no `W10/READY/NOT_READY/handoff` token | `inspect.getsource(validate_and_remember)` |
| 5 | Protected path blocked? | **Blocked, fail-closed** (PASS, not xfail) | `is_source_modification` True; `check_source_permission` denies when `permissions is None` |

**Test results:** `7 passed, 4 xfailed` (the new file, run alone). With the adjacent
`test_openclaw_foundup_orchestrator.py`: `29 passed, 4 xfailed, 0 failed` — this slice
introduces **no** downstream pollution.

> **Pre-existing adjacent-test note (not this slice's defect).** Running the dispatch's
> adjacent command `pytest test_openclaw_foundup_routing.py test_openclaw_foundup_orchestrator.py`
> yields `8 failed, 41 passed`. Each file passes alone (routing 27, orchestrator 22). The
> failures are a **pre-existing cross-file pollution**: `test_openclaw_foundup_routing.py`
> calls `importlib.reload(openclaw_foundup_orchestrator)` under a mocked `fam_adapter` and
> never restores it, corrupting the orchestrator genesis-gate tests that run afterward. This
> reproduces **without** this slice's file and is **out of scope** here (no test-file fix
> made). It is a candidate cleanup for the remediation slice.

---

## 7. Xfail Contract Table

All xfails are `strict=True`, cite #737, and name the remediation slice
`OPENCLAW_WSP109_GENESIS_GATE_REMEDIATION_PHASE1`.

| Test | Cites | Desired (fixed) behaviour asserted | Why it xfails today |
|------|-------|------------------------------------|---------------------|
| `test_onboard_prompt_should_route_through_intake_REMEDIATION` | #737 S1 | onboarding is a recognised gateable intake intent | no WSP 109 genesis gate exists |
| `test_foundup_dispatch_should_be_genesis_gated_REMEDIATION` | #737 9.1#1 | `dispatch_foundup` validates a genesis envelope before launch | gated methods defined but never invoked by live dispatch |
| `test_create_foundup_variants_should_converge_REMEDIATION` | #737 9.1#2 | both create-foundup phrasings resolve to one gated path | shared trigger words route differently |
| `test_mutating_path_should_emit_w10_handoff_REMEDIATION` | #737 9.1#3 | a mutating outcome emits a W10 READY/NOT_READY handoff | `validate_and_remember` self-approves |

Strict semantics: when remediation lands, each xfail **XPASSes → suite fails**, forcing the
test to be promoted to a real assertion. This is the executable remediation contract.

---

## 8. What Remains Proven vs Unproven

**Proven (executable):**
- WSP 109 onboarding does **not** flow through an intake/genesis gate (Q1, Q2).
- FOUNDUP dispatch does **not** invoke the genesis validator (Q2).
- The two create-foundup phrasings **diverge** (Q3).
- `validate_and_remember` **self-approves** without a W10 handoff (Q4).
- Protected-path edits remain **fail-closed blocked** (Q5).

**Unproven / out of scope:**
- Whether the FOUNDUP bypass reaches *persistent* production mutation (FAM uses
  `use_in_memory=True`; not traced here — #737 §12).
- The Gemma hybrid intent classifier's runtime classification (only deterministic
  keyword/structure paths are asserted).
- End-to-end live behaviour (no live process by constraint).
- A fix for the pre-existing routing↔orchestrator pollution (§6 note) — deferred.

---

## 9. Future Remediation Slice

**`OPENCLAW_WSP109_GENESIS_GATE_REMEDIATION_PHASE1`** (code; architect-approved):
1. Route WSP 109 onboarding through a genesis/intake gate before FOUNDUP execution.
2. Wire `validate_genesis_envelope` into the live `dispatch_foundup` (or collapse to one
   gated entrypoint), closing the FOUNDUP permission/genesis bypass.
3. Converge the dual create-foundup parser paths.
4. Emit a W10 READY/NOT_READY handoff on mutating outcomes instead of self-approval.
5. (Cleanup) fix the routing-test reload pollution (§6 note).

When implemented, the 4 strict xfails here XPASS and must be promoted to assertions.

---

## 10. Internal Review Verdict

**READY.** This slice delivers executable characterization of all five #737-derived
questions: 7 passing current-behaviour locks + 4 strict xfail remediation contracts, the
protected-path proof preserved as PASS, zero production code change, and no downstream test
pollution introduced. The pre-existing adjacent pollution is reported honestly, not masked.

---

## 11. WSP_97 Truth Boundary Checklist

Declared count: **26 / 26 YES** (rows below = 26).

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | CHARACTERIZATION_TEST_ONLY | YES | Tests assert current behaviour; no fix |
| 2 | NO_PRODUCTION_CODE_CHANGE | YES | Only test + docs + ModLogs changed |
| 3 | NO_BEHAVIOR_FIX_IN_THIS_SLICE | YES | Gaps locked as strict xfail, not fixed |
| 4 | NO_OPENCLAW_SOURCE_MUTATION | YES | `moltbot_bridge/src` untouched (git clean) |
| 5 | NO_WRE_SOURCE_MUTATION | YES | `wre_core/src` untouched |
| 6 | NO_HERMES_SOURCE_MUTATION | YES | Hermes executors untouched |
| 7 | NO_WSP_FRAMEWORK_MUTATION | YES | WSP docs read-only |
| 8 | NO_SKILL_CREATION | YES | No SKILLz created |
| 9 | NO_SKILL_EDIT | YES | No SKILLz edited |
| 10 | NO_REGISTRY_MUTATION | YES | No registry written |
| 11 | NO_MANIFEST_MUTATION | YES | No manifest written |
| 12 | NO_CATALOG_MUTATION | YES | No catalog written |
| 13 | NO_PUBLIC_SURFACE_MUTATION | YES | No routes/INTERFACE changed |
| 14 | NO_ROUTE_ACTIVATION | YES | No route activated |
| 15 | NO_LIVE_OPENCLAW_PROCESS | YES | Pure-function + mock; no DAE boot |
| 16 | NO_NETWORK_CALL_IN_TESTS | YES | No sockets/HTTP; deterministic |
| 17 | NO_DOTENV_READ_IN_TESTS | YES | No `.env` access |
| 18 | XFAILS_ARE_STRICT_AND_JUSTIFIED | YES | 4 xfails `strict=True`, cite #737 + remediation slice |
| 19 | CITES_PR_737 | YES | §1, §4, §7; tests cite #737 in reasons |
| 20 | REMEDIATION_DEFERRED | YES | §9 defers all fixes to remediation slice |
| 21 | NO_CABR_READY | YES | No CABR touched |
| 22 | NO_PAYOUT_READY | YES | No payout touched |
| 23 | NO_DAO_ACTIVATION | YES | No DAO activation |
| 24 | PROTECTED_PATH_TEST_PASSES | YES | 2 protected-path tests PASS (Q5), not xfail |
| 25 | FOUR_STRICT_XFAILS_PRESENT | YES | 4 xfailed in test run |
| 26 | ADJACENT_REGRESSION_HONESTLY_REPORTED | YES | §6 note: pre-existing pollution, reproduces without this slice |

**WSP 97 Truth Boundary Checklist: 26/26 YES.**

---

*Authored by 0102 (Worker-Lane W6) under WSP_00 zen state and WSP_97 Truth Boundary
discipline. Characterization only — current OpenClaw behaviour captured as executable
evidence; all remediation deferred to `OPENCLAW_WSP109_GENESIS_GATE_REMEDIATION_PHASE1`.*
