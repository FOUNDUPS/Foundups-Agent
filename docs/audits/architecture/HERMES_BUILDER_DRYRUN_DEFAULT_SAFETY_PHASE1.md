# HERMES_BUILDER_DRYRUN_DEFAULT_SAFETY_PHASE1

**Slice:** `HERMES_BUILDER_DRYRUN_DEFAULT_SAFETY_PHASE1`
**Priority:** **P0 — before WSP109 intake builder or any path that may reach Hermes**
**Author:** 0102 (WSP_97)
**Date:** 2026-07-04
**Type:** Targeted safety remediation
**WSP lock:** WSP_00, WSP_15, WSP_22, WSP_50, WSP_97

---

## 1. Problem (OBSERVED)

`HermesFoundUpBuilder.__init__` sets:

```python
self.dry_run = os.environ.get("HERMES_BUILDER_DRY_RUN", "0") == "1"
```

(`modules/foundups/agent/src/hermes_adapter.py:134`)

**Default when env unset:** `dry_run=False` — builder may perform real extraction/build paths unless callers force dry-run.

Contrast:

- `BuildPlanExecutor(dry_run=True)` default (`build_plan_executor.py:399`)
- `HermesJobExecutor(dry_run=True)` default (`hermes_job_executor.py:555`)
- `build_plan_generator` always emits `dry_run=True` plans (`build_plan_generator.py:423`)

**Label:** Hermes **adapter-level** default is the outlier and the **sharpest safety finding** in the FoundUp creation path audit.

---

## 2. Mission

Flip Hermes FoundUp Builder to **dry-run by default**. Real writes/delegation require **explicit opt-in** (env + policy flag + test assertion).

No change to OpenClaw genesis gate semantics. No FAM registration changes.

---

## 3. In Scope

| Change | Detail |
|--------|--------|
| Default `dry_run=True` | When `HERMES_BUILDER_DRY_RUN` unset |
| Explicit real-write opt-in | New env e.g. `HERMES_BUILDER_ALLOW_REAL_WRITES=1` AND `HERMES_BUILDER_DRY_RUN=0` both required |
| Job executor alignment | `execute_foundup_job` logs/policy_flags reflect builder default |
| Tests | Default-off real writes; opt-in path gated; existing dry-run tests green |
| Docs | `hermes_adapter` ModLog, INTERFACE, module README |

---

## 4. Out of Scope

- Enabling Hermes real delegation in `hermes_job_executor.py` (remains BLOCKED)
- WSP_109 intake packet builder (next slice)
- Scaffold contract / registry seed

---

## 5. Acceptance Criteria

| # | Criterion | Proof |
|---|-----------|-------|
| A1 | Fresh `HermesFoundUpBuilder()` has `dry_run is True` with no env | Unit test |
| A2 | `extract_foundup` / `build_foundup` with default builder emit `dry_run: true` in result dict | Unit test |
| A3 | Real-write path requires **both** opt-in env vars; otherwise `dry_run` stays True | Unit test |
| A4 | `execute_foundup_job(..., force_dry_run=False)` still respects builder default True unless double opt-in | Executor test |
| A5 | No test sets `HERMES_BUILDER_DRY_RUN=0` without explicit real-write opt-in marker | Grep CI guard |
| A6 | Full `modules/foundups/agent/tests/` green | pytest |

---

## 6. No-Weakening Argument

This slice **tightens** defaults only. It does not relax:

- AI Overseer security sentinel (`require_security_gate`)
- CABR validation on outputs
- OpenClaw genesis gate
- WRE execution valve closed-by-default

---

## 7. WSP_15 Priority

| Priority | Slice | Rationale |
|----------|-------|-----------|
| **P0** | This slice | Prevents accidental real Hermes writes while intake builder is authored |
| P1 | WSP109_INTAKE_PACKET_BUILDER_PHASE1 | Depends on safe builder default |
| P2 | FOUNDUP_SCAFFOLD_CONTRACT_PHASE1 | After intake gate proof |

---

## 8. Related

- Parent audit: `REDDOG_FOUNDUP_CREATION_EXECUTION_PATH_AUDIT_PHASE1.md`
- Next: `WSP109_INTAKE_PACKET_BUILDER_PHASE1.md`

---

## ADDENDUM A - HoloIndex Discoverability / Re-index Gate

Before implementation:

1. Run HoloIndex queries for:
   - Hermes builder dry-run default safety
   - HERMES_BUILDER_DRY_RUN default
   - WSP109 intake packet builder
   - FoundUpGenesisEnvelope builder
   - FoundUp scaffold contract
   - build_foundup extract_foundup

2. Record top hits and whether the new audit docs are discoverable.

3. If the new docs or target implementation files are not in top results, record:
   `HOLOINDEX_FOUNDUP_CREATION_AUDIT_DISCOVERABILITY_PHASE1`

4. Re-index is allowed only as an explicit worker/operator action, not inside RedDog runtime:
   - docs/WSP index
   - code index
   - symbols index
   - Skillz index if campaign/FoundUp Skillz are involved

5. No HoloIndex ranking-code changes in the Hermes safety slice unless local tests prove ranking
   code is the defect.

Acceptance:
- The implementation slice must list HoloIndex pre/post query results.
- Any INDEX_GAP must be recorded honestly in ROADMAP/ModLog.
- Do not claim RedDog recall success unless target files and relevant symbols are actually surfaced
  or direct-read targets are supplied.

---

## ADDENDUM B - Safety Before Intake

`HERMES_BUILDER_DRYRUN_DEFAULT_SAFETY_PHASE1` must land before any WSP109 intake builder path can
call, simulate, or test Hermes handoff behavior. Intake builder tests may verify OpenClaw gate
outcomes, but must not invoke Hermes real-write paths.
