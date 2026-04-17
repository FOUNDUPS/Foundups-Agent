# Worker execution prompt — Matrix A local import (Phase 1)

**Slice:** `MOBILE_WORKER_MATRIX_A_LOCAL_IMPORT_PHASE1`  
**Versioned in-repo for 012 / operator handoff.**

---

## Worker Identity Lock

You are acting as `WORKER: CK` for this slice.

Rules:

1. `WORKER: CK` is your only lane identity for this task.
2. Do not reinterpret prior lane letters from earlier slices.
3. Do not self-assign a different lane.
4. In your first response, state:  
   `IDENTITY LOCK: Acting as Worker CK for MOBILE_WORKER_MATRIX_A_LOCAL_IMPORT_PHASE1.`
5. In your completion report, begin with:  
   `Worker CK complete for MOBILE_WORKER_MATRIX_A_LOCAL_IMPORT_PHASE1.`

## WSP Lock

Apply `WSP 15` first.  
Then apply `WSP 97`.  
Then act.

---

# MOBILE_WORKER_MATRIX_A_LOCAL_IMPORT_PHASE1

# Repo: O:\Foundups-Agent  
# Priority: P0

SELF: 0102  
ROLE: worker  
WORKER: CK

## Mission

Run Matrix A exactly as defined and report truthfully whether the device can load the first two mobile worker skills through local import.

Current truth:

- this is the gate
- only two skills are in scope
- no URL phase is allowed yet
- no handoff-validator is allowed yet
- drift on either check means full stop

## Critical Boundary

Do NOT:

- test any URL/gallery folder loading
- test any JS skill
- test extra parser examples
- broaden beyond Matrix A
- push `main` blindly
- mix this work with unrelated Kosei / pfMALL / audit changes

## Required Source of Truth

Read and follow exactly:

1. `modules/foundups/mobile_worker_skills/MATRIX_A_LOCAL_IMPORT_RUN.md`
2. `modules/foundups/mobile_worker_skills/DEVICE_EDGE_GALLERY_VALIDATION.md`
3. `modules/foundups/mobile_worker_skills/README.md`

## Matrix A Scope

### A1

Skill:

- `foundups-edge-load-smoke`

Required outcome:

- device returns exactly: `LOAD_OK`

Anything else is failure.

### A2

Skill:

- `foundups-code-task-parser`

Input string:

- `fix swipe threshold in capture controller and run tests`

Required outcome:

- parser JSON matches the intended structure from the Matrix A doc
- must include:
  - truthful intent (`edit` or `mixed`, per doc)
  - no invented file paths
  - non-empty `open_questions`
  - `suggested_next_skill` = `foundups-scope-locker`

Anything else is drift/failure.

## Stop Conditions

If A1 fails:

- stop immediately
- do not run A2
- do not run handoff-validator
- do not test URL phase

If A2 fails:

- stop immediately
- do not run handoff-validator
- do not test URL phase

Only if both A1 and A2 pass:

- report Matrix A passed
- handoff-validator becomes eligible for the next slice
- do not run it inside this slice unless explicitly instructed

## Git Guard

Before any push to `main`, you must run:

```powershell
git fetch origin main
git log --oneline origin/main..main
git diff --stat origin/main..main
```

If anything unrelated appears:

- stop
- do not push `main`
- branch/cherry-pick instead

## Required Output

Return exactly one `DEVICE_GALLERY_REPORT` with:

### DEVICE_GALLERY_REPORT

- Device / app surface used
- Matrix A source doc followed
- A1 result:
  - pass/fail
  - exact returned text
- A2 result:
  - pass/fail
  - exact returned JSON
  - note whether:
    - `open_questions` is non-empty
    - file paths were invented or not
    - `suggested_next_skill` matches
- Final gate result:
  - `MATRIX_A_PASS`
  - or `MATRIX_A_FAIL`
- Next action:
  - `STOP`
  - or `ELIGIBLE_FOR_HANDOFF_VALIDATOR`

## Acceptance

- Matrix A run is exact and narrow
- report is exact, not interpretive
- no extra tests were run
- no URL phase was attempted
- no validator was run unless separately instructed
- no blind `main` push occurred

## Suggested Completion Header

`Worker CK complete for MOBILE_WORKER_MATRIX_A_LOCAL_IMPORT_PHASE1.`
