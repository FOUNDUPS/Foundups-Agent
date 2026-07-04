# FOUNDUP_SCAFFOLD_CONTRACT_PHASE1

**Slice:** `FOUNDUP_SCAFFOLD_CONTRACT_PHASE1`
**Author:** 0102 (WSP_97)
**Date:** 2026-07-04
**Type:** Contract / spec — **queued after intake builder**
**Status:** **SPECIFIED_NOT_IMPLEMENTED** (do not start before `WSP109_INTAKE_PACKET_BUILDER_PHASE1` gate proof)
**WSP lock:** WSP_00, WSP_15, WSP_22, WSP_49, WSP_97, WSP_109

---

## 1. Mission

Define the **`create_foundup`** execution contract:

1. Canonical **FoundUpJob** action semantics (`create_foundup` vs existing `build_foundup` / `extract_foundup`)
2. **WSP-49 monorepo scaffold** artifact set (README, INTERFACE, ROADMAP, ModLog, tests/README, src/, tests/, requirements.txt, memory/README)
3. Mapping: **intake packet → scaffold tree → registry seed** (dry-run plan first, real writes later behind valve)

---

## 2. Why Queued (Updated Decision)

Swarm + 0.3.41 audit established envelope schema and validator are **testable now**. Scaffold contract remains necessary but **not first**:

```text
Intake packet (WSP_109) → genesis gate PASS → THEN scaffold contract → THEN build/extract jobs
```

Starting with scaffold contract before intake builder would duplicate specification work without proving the gate accepts populated envelopes.

---

## 3. Scope (When Started)

### In scope

| Deliverable | Detail |
|-------------|--------|
| Action taxonomy | Document `create_foundup`, `build_foundup`, `extract_foundup`, `validate_foundup` boundaries |
| Scaffold manifest | JSON/dataclass: paths, template sources, WSP-49 compliance checklist |
| Dry-run planner | Emit planned files + gates; `real_execution_performed=False` |
| Registry seed plan | Catalog entry fields; no write in Phase 1 |
| Tests | Contract tests only; no Hermes real delegation |

### Out of scope (Phase 1)

- Live registry mutation
- DNS / public routes / tokens
- Hermes real terminal execution
- RedDog auto-scaffold from chat without validated envelope

---

## 4. Open Questions (Resolve in Slice Kickoff)

| # | Question | Default hypothesis |
|---|----------|-------------------|
| Q1 | Is `create_foundup` a new canonical action or alias to `build_foundup`? | New action = scaffold-only; `build_foundup` = Hermes extract/build sink |
| Q2 | Where does scaffold template live? | `modules/infrastructure/wre_core/templates/wsp49_foundup/` |
| Q3 | Who consumes scaffold plan? | `build_plan_generator` extension or dedicated `scaffold_plan_executor` dry-run |

---

## 5. Dependencies

| Prerequisite | Reason |
|--------------|--------|
| `HERMES_BUILDER_DRYRUN_DEFAULT_SAFETY_PHASE1` | Safe defaults before any build path |
| `WSP109_INTAKE_PACKET_BUILDER_PHASE1` | Valid envelope input contract |
| RedDog 0.3.41+ senses spine | Audit evidence for execution path docs |

---

## 6. Acceptance Preview (Draft)

- Dry-run scaffold plan lists all WSP-49 mandatory files for a sample `foundup_id`
- Plan references envelope `foundup_id` + acceptance_criteria
- `build_foundup` vs `extract_foundup` documented with file:line citations in INTERFACE
- No file writes in Phase 1 contract slice

---

## 7. Related

- Parent audit: `REDDOG_FOUNDUP_CREATION_EXECUTION_PATH_AUDIT_PHASE1.md`
- Intake builder: `WSP109_INTAKE_PACKET_BUILDER_PHASE1.md`
- Manifest readiness: `FOUNDUP_MANIFEST_READINESS_AUDIT_PHASE1.md`
