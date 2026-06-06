# WRE_OPENCLAW_HERMES_AUTONOMOUS_BUILD_DRYRUN_PHASE1

**Slice:** WRE_OPENCLAW_HERMES_AUTONOMOUS_BUILD_DRYRUN_PHASE1
**Worker-Lane:** W6
**Author:** 0102 (WSP_00 zen state, WSP_97 Truth Boundary discipline)
**Type:** code/test characterization + minimal remediation (headless bootstrap seam).

---

## 1. Mission

Prove the repo can run a BOUNDED ONE-CYCLE dry-run of the headless autonomous seam through
the real WRE/OpenClaw/Hermes surfaces, and fix the headless bootstrap seam if broken. This is
NOT a claim of continuous autonomous coding, NOT a second orchestration layer, and NOT an
end-to-end live build. Where a part is mocked, it is labeled mocked.

**Honest scope statement (WSP 97):** this slice proves (a) the `main.py --headless` bootstrap
seam is fixed and dry-run-safe, and (b) the FoundUp->Hermes dry-run path is dry-run-safe.
It does NOT claim these two are wired into one end-to-end loop today (see Section 9).

---

## 2. WSP_15 Score and Priority

| Dimension | Score (1-5) | Rationale |
|-----------|-------------|-----------|
| Complexity | 2 | Minimal fix: reuse existing bootstrap; no new module |
| Importance | 4 | Headless autonomous mode is inoperative without it |
| Deferability | 4 | Broken seam blocks any headless autonomous cycle (low deferability) |
| Impact | 4 | Enables a bounded, dry-run-safe headless cycle |

**Total: 14/20 -> Priority P1.**

---

## 3. Runtime Topology Map

Verified stage-by-stage (file:line). `present` = wired into the `main.py --headless` path.

| Stage | Surface | present |
|-------|---------|---------|
| Mode routing | `main.py` __main__ L1414-1415: `--headless -> run_headless()`, bypassing `main()` | YES |
| WRE readiness gate (fail-closed) | `run_headless` L1334-1341 -> `run_connect_wre` L785 (dashboard health only) | YES |
| DAE launch-spec registration | `bootstrap_runtime_dae_launches` L1087-1223 (`register_launch_spec` L1204-1205 on the singleton broker) | **YES (after fix)** |
| Broker/supervisor construction | `run_headless` L1346-1364 -> `OpenClawSupervisor(broker=...)` | YES |
| Supervisor state machine | `openclaw_supervisor.run_cycle` L161 (observe->triage->plan->execute->verify->remember->escalate) | YES |
| OBSERVE reads broker status | `_observe` L448-489 (`broker.get_runtime_status("openclaw")` L452) | YES |
| TRIAGE | `_triage` L495-598 (restart L505-519; auto-tasks L524; maintenance L542; self-audit L587) | YES |
| **FoundUp job / test selection** | none in supervisor (grep `foundup_job\|FoundUpJob\|drain` = 0 matches) | **NO** |
| FoundUpJobConsumer | `foundup_job_consumer.FoundUpJobConsumer` L322 (`consume_one` L351, `_dispatch_to_hermes` L405) | present, **not in headless loop** |
| Hermes dry-run executor | `hermes_job_executor.execute` L1536 (dry_run short-circuit -> SIMULATED L1794-1820) | present, **not in headless loop** |
| FoundUp->Hermes entrypoint (out of band) | `run_wre.py` L436-439 `drain_openclaw_queue_dry_run` (separate CLI) | YES (separate) |

**Key topology truth:** the headless supervisor cycle and the FoundUp->Hermes dry-run pipeline
are SEPARATE. The supervisor selects restart / AgentDB auto-tasks / maintenance / self-audit,
not FoundUp builds. The FoundUp->Hermes dry-run is reachable only via `FoundUpJobConsumer`
(callers: `openclaw_foundup_orchestrator.py`, `receipt_emitter.py`, `run_wre.py`).

---

## 4. Existing Seams Reused (WSP 84)

- `bootstrap_runtime_dae_launches()` (main.py L1087) -- the canonical DAE-spec registration; the
  fix calls it instead of duplicating specs.
- `get_dae_launch_broker()` singleton (dae_launch_broker.py L418-423) -- shared broker the fix
  consumes after bootstrap populates it.
- Existing env flags (`OPENCLAW_RESIDENT_AUTOSTART`, `OPENCLAW_SUPERVISOR_AUTOSTART`,
  `OPENCLAW_SUPERVISOR_ALLOW_RESTART`) -- the fix sets dry-run-safe defaults via `setdefault`,
  preserving operator opt-in.
- Existing dry-run coverage (cited, not duplicated): `test_foundup_registry_loader.py`,
  `test_foundup_registry_schema.py`, `test_foundup_job_consumer.py`, `test_hermes_job_executor.py`
  -- 105 passing, covering registry load + Hermes dry-run truth fields.

---

## 5. Tests Added

Extended `tests/test_main_runtime_bootstrap.py` (the existing main.py bootstrap harness):

| Test | Proves | Mocked |
|------|--------|--------|
| `test_run_headless_bootstraps_dae_specs_before_supervisor_cycle` | `--headless` (MAX_CYCLES=1) calls `bootstrap_runtime_dae_launches` BEFORE the supervisor cycle and hands the supervisor the shared broker (call-order asserted) | WRE readiness, bootstrap, broker, supervisor, sleep |
| `test_run_headless_fail_closed_when_wre_not_ready` | exits 1, never bootstraps/constructs supervisor when WRE not ready | WRE readiness |
| `test_run_headless_one_cycle_no_live_execution` | one mocked cycle; sets `RESIDENT_AUTOSTART/SUPERVISOR_AUTOSTART/SUPERVISOR_ALLOW_RESTART=0` (no live service) | all heavy seams |
| `test_supervisor_triage_escalates_not_live_starts_when_restart_disabled` | with restart disabled, `_triage` returns escalate `resident_openclaw_down_restart_disabled`, NOT the live `start_openclaw` action | broker/observer |

**Result: 9 passed** (5 pre-existing bootstrap + 4 new). No live process/network/model/OAuth/
GitHub-write/Docker. All non-pure seams are mocked (labeled above).

---

## 6. FoundUp Auto-Test Matrix

16 registered FoundUps (`foundup_registry.json`); each `foundup_id` mapped to a module path and
test status. Missing coverage is reported, not hidden.

| foundup_id | module_path | status |
|------------|-------------|--------|
| gotjunk_001 | modules/foundups/gotjunk | HAS_TESTS |
| kosei | modules/foundups/kosei | HAS_TESTS |
| voteballots | modules/foundups/voteballots | HAS_TESTS |
| trade | modules/foundups/trade | HAS_TESTS |
| magadoom_001 | modules/gamification/whack_a_magat | HAS_TESTS |
| antifafm_001 | modules/platform_integration/antifafm_broadcaster | HAS_TESTS |
| pfmall | modules/foundups/pfmall | HAS_TESTS |
| agent_market | modules/foundups/agent_market | HAS_TESTS |
| move2japan | modules/foundups/move2japan | HAS_TESTS |
| simulator | modules/foundups/simulator | HAS_TESTS |
| social_twin | modules/foundups/social_twin | HAS_TESTS |
| autopost | **ABSENT** | **NO_TEST_COVERAGE** |
| pqn_portal | modules/foundups/pqn_portal | **NO_TEST_COVERAGE** |
| science_swarm_hub | modules/foundups/pqn_swarm_hub | **NO_TEST_COVERAGE** |
| holoindex_prod_01 | modules/foundups/holoindex_prod_01 | **NO_TEST_COVERAGE** |
| shield | modules/foundups/shield | **NO_TEST_COVERAGE** |

**Coverage: 11/16 HAS_TESTS, 5/16 NO_TEST_COVERAGE** (autopost also has no module path).

---

## 7. Headless / main.py Binding Result

**Root cause (confirmed):** `--headless` routes directly to `run_headless()` (L1414-1415),
bypassing `main()`; `bootstrap_runtime_dae_launches()` is called ONLY from `main()` (L1260).
Pre-fix, `run_headless` built a FRESH empty `DAELaunchBroker()` (`_specs={}`), so the supervisor's
`_observe` read `registered=False` and `_triage` escalated `openclaw_runtime_not_registered`
(L502-503) **every cycle**, dead-looping with no plan/execute.

**Fix (minimal, thin router preserved):** `run_headless` now reuses
`bootstrap_runtime_dae_launches()` (no duplicated specs) and consumes the shared singleton
`get_dae_launch_broker()`. It sets dry-run-safe `setdefault` defaults
(`OPENCLAW_RESIDENT_AUTOSTART=0`, `OPENCLAW_SUPERVISOR_AUTOSTART=0`,
`OPENCLAW_SUPERVISOR_ALLOW_RESTART=0`) so a one-cycle run registers specs (triage passes
`registered=True`) yet performs NO live launch (triage escalates `resident_openclaw_down_
restart_disabled` instead of `start_openclaw`). Auto-tasks/maintenance are already off by
default. Operator opts into live autonomy via the existing env flags.

**`HEADLESS_BOOTSTRAP_SEAM_FIXED`: YES** -- proven by 4 tests (Section 5), not asserted.

**Critic note addressed:** the adversarial pass found the initial fix closed the bootstrap
autostart door but left the supervisor restart side-door open (would live-launch the resident
on cycle 1). The final fix suppresses `OPENCLAW_SUPERVISOR_ALLOW_RESTART` by default and a guard
test proves triage escalates instead of starting a live service.

---

## 8. Dry-Run Evidence (FoundUp -> Hermes, separate seam)

The FoundUp->Hermes dry-run path is dry-run-safe (verified, covered by existing tests):
`FoundUpJobConsumer.__init__` defaults `dry_run=True` (L342) -> `consume_one` (L351) ->
`_dispatch_to_hermes` (L405) -> `execute_foundup_job` -> `get_executor(dry_run=True).execute`
(hermes L2344-2366) -> Step5 `if self.dry_run:` short-circuit returns `SIMULATED` (L1794-1820)
**before** any real `delegate_task` import (L1823) or the `BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED`
branch (L1843-1868, reachable only with `HERMES_DELEGATE_ENABLED` true AND `dry_run` false).

**WSP 97 truth fields stay false:** `real_execution_performed=False` (L448),
`verification_complete=False` (L449), `cabr_ready=False` (L450), `payout_ready=False` (L451) --
re-asserted in every SIMULATED/BLOCKED branch. Consumer-side: SIMULATED ->
`_emit_receipt_for_hermes_result` returns None (L614-626) -> `receipt_emission` stays None ->
the three verification properties resolve False. No CABR_READY, no PAYOUT_READY, no
verification_complete overclaim. This seam is NOT reached by `main.py --headless` (Section 3).

---

## 9. Gaps and Next Slices

1. **FoundUp job/test selection is not wired into the headless supervisor cycle.** The
   supervisor does restart/auto-task/maintenance/self-audit, not FoundUp builds. The
   FoundUp->Hermes dry-run is a SEPARATE entrypoint (`run_wre.py`). Wiring it into the cycle is
   future work -> **`WRE_AUTONOMOUS_BUILD_CONTEXT_BUNDLE_PHASE1`** (or a dedicated
   `WRE_HEADLESS_FOUNDUP_JOB_SELECTION` slice).
2. **5/16 FoundUps have NO_TEST_COVERAGE** (autopost, pqn_portal, science_swarm_hub,
   holoindex_prod_01, shield); autopost also lacks a module path ->
   **`FOUNDUP_AUTO_TEST_MATRIX_COVERAGE_PHASE1`**.
3. **Headless binding was fixed** -> a W10 readiness gate for the headless bootstrap ->
   **`WRE_HEADLESS_BOOTSTRAP_W10_GATE`**.
4. **Pre-existing (out of scope):** `test_openclaw_supervisor_p0.py::test_run_cycle_executes_
   and_completes_pending_autonomous_task` fails on clean `origin/main` (27d6d2c22) with this
   slice's changes stashed -- not caused by this fix; flagged for a separate slice.

**Recommended next slice:** `WRE_HEADLESS_BOOTSTRAP_W10_GATE` (binding fixed), with
`FOUNDUP_AUTO_TEST_MATRIX_COVERAGE_PHASE1` for the 5 coverage gaps.

---

## 10. Internal Review Verdict

**READY.** The headless bootstrap seam is fixed by reusing the existing bootstrap path (no
second layer; critic `second_layer_drift=false`), proven by 4 mocked tests (9 passing total).
The fix is dry-run-safe by default (no live launch; restart side-door closed and guard-tested).
The FoundUp->Hermes dry-run truth boundary is verified (all four WSP 97 fields false) via the
existing seam. Claims are bounded to a one-cycle dry-run; mocked parts are labeled; the
not-yet-wired FoundUp->headless gap and a pre-existing failure are reported, not hidden.

---

## 11. WSP_97 Truth Boundary Checklist

Declared count: 22 / 22 YES (rows below = 22).

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | CHARACTERIZATION_AND_MINIMAL_FIX_ONLY | YES | main.py run_headless fix + tests; no new module |
| 2 | HEADLESS_ONE_CYCLE_TESTABLE_MAX_CYCLES_1 | YES | test_run_headless_bootstraps... uses OPENCLAW_HEADLESS_MAX_CYCLES=1 |
| 3 | HEADLESS_REGISTERS_SPECS_BEFORE_CYCLE | YES | call-order assert [bootstrap, run_cycle]; Section 7 |
| 4 | FAIL_CLOSED_WHEN_WRE_NOT_READY | YES | test_run_headless_fail_closed... returns 1, no bootstrap |
| 5 | SUPERVISOR_ONE_MOCKED_CYCLE_NO_LIVE_MUTATION | YES | test_run_headless_one_cycle_no_live_execution |
| 6 | NO_LIVE_SERVICE_LAUNCH_RESTART_GUARD | YES | test_supervisor_triage_escalates_not_live_starts... |
| 7 | FOUNDUP_REGISTRY_LOADS_IDS_MAPPED | YES | Section 6 matrix (16); existing test_foundup_registry_loader passes |
| 8 | MISSING_TESTS_REPORTED_NOT_HIDDEN | YES | 5 NO_TEST_COVERAGE listed (autopost module ABSENT) |
| 9 | FOUNDUP_DRYRUN_REACHES_HERMES_NO_REAL_DELEGATE | YES | Section 8; existing test_foundup_job_consumer/test_hermes_job_executor pass |
| 10 | TRUTH_FIELDS_FALSE_NO_CABR_PAYOUT_VERIFICATION | YES | Section 8 (L448-451 + re-asserted SIMULATED/BLOCKED) |
| 11 | NO_LIVE_PROCESS_NETWORK_MODEL_IN_TESTS | YES | all heavy seams mocked (Section 5) |
| 12 | NO_LIVE_HERMES_DELEGATION | YES | HERMES_DELEGATE_ENABLED off; dry_run short-circuit L1795 |
| 13 | NO_OAUTH_NO_NOUS_PORTAL | YES | no OAuth/portal call in fix or tests |
| 14 | NO_DOCKER_START | YES | no container start |
| 15 | NO_GITHUB_WRITE_FROM_RUNTIME | YES | no git/PR action in fix or tests |
| 16 | NO_SECOND_ORCHESTRATION_LAYER | YES | critic second_layer_drift=false; reuses bootstrap |
| 17 | MAIN_PY_THIN_ROUTER_PRESERVED | YES | run_headless calls bootstrap; no logic duplicated |
| 18 | NO_WSP_MUTATION | YES | no WSP file changed |
| 19 | NO_FOUNDUP_PRODUCTION_BEHAVIOR_CHANGE | YES | only run_headless default env posture changed |
| 20 | NO_OVERCLAIM_CONTINUOUS_AUTONOMY | YES | claim bounded one-cycle dry-run only (Section 1) |
| 21 | MOCKED_PARTS_LABELED | YES | Section 5 mocked column; Section 8 labels seam |
| 22 | PREEXISTING_FAILURE_REPORTED | YES | Section 9 item 4 (verified on clean main via stash) |

**WSP 97 Truth Boundary Checklist: 22/22 YES.**

---

*Authored by 0102 (Worker-Lane W6) under WSP_00 zen state and WSP_97 Truth Boundary discipline.
Headless bootstrap seam fixed by reusing the existing bootstrap path; bounded one-cycle dry-run
proven via mocked tests. The FoundUp->Hermes dry-run is a verified but separate seam, not yet
wired into the headless loop.*
