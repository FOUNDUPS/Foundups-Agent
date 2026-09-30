# AutoAgent Lab — Layer 3 Cutoff & Reactivation Gate

**Date**: 2026-04-21
**Author**: W6
**Slice**: AUTOAGENT-LAB-PARK-NOTE
**Status**: PARKED (after Layer 3)

This briefing records the current cutoff state of the AutoAgent Lab lane and the explicit gate that must be cleared before any worker resumes Layer 4 implementation. It is a coordination record, not a spec change.

---

## 1. Current layer state

| Layer | Name | Status | Evidence |
|-------|------|--------|----------|
| L1 | Scaffold + Config + Safety Gates | **DONE** | V0.1.0 (2026-04-07, worker AD) — `modules/infrastructure/autoagent_lab/src/experiment_config.py`, `src/safety_gates.py`, `config/experiment_spec_template.yaml`, with matching tests. Recorded in `modules/infrastructure/autoagent_lab/ModLog.md` V0.1.0 entry. |
| L2 | Eval Harness | **DONE** | V0.2.0 (2026-04-07, worker AE) — `src/eval_harness.py`, `tests/test_eval_harness.py`. Recorded in ModLog V0.2.0 entry. |
| L3 | Target Surface IO | **DONE** | V0.3.0 (2026-04-08, worker AJ; rescued and landed by W6) — `src/target_surface.py` (33 tests). **PR #410**, merge commit **`9b0ee293098b2829e3d13467e10a55f669dc324d`**, merged 2026-04-21T11:58:34Z. |
| L4 | Experiment Runner (Core Loop) | **SPECIFIED_NOT_STARTED** | Spec in `docs/audits/autoagent_wre/AUTOAGENT_BUILD_ORDER.md` §"Layer 4". No `src/experiment_runner.py` or `src/diff_recorder.py` present on main. |
| L5 | CLI + OpenClaw Hook | **SPECIFIED_NOT_STARTED** | Spec in `AUTOAGENT_BUILD_ORDER.md` §"Layer 5". No `src/cli.py` present on main; the README's Quick Start command does not work yet. |

---

## 2. Reason for parking

The lane is being parked — not cancelled — for the following reasons:

1. **Absent from `ACTIVE_SLICE_LEDGER.md`.** A grep of `docs/0102_session_briefings/ACTIVE_SLICE_LEDGER.md` returns zero matches for "autoagent" or "AutoAgent". The coordination layer does not currently track this lane as active.
2. **Lane went silent after early April.** Layers 1–3 were delivered by three different workers (AD, AE, AJ) between 2026-04-07 and 2026-04-08, after which no further AutoAgent Lab work appeared in session briefings or the ledger until W6 surfaced an orphaned L3 commit during the `feat/pfmall-pwa-hardening` rescue.
3. **L3 was recovered from branch contamination.** The Layer 3 commit (`d0de6ef37`) sat on the accumulated `feat/pfmall-pwa-hardening` branch rather than being shipped on its own rescue branch. W6 extracted it as PR #410; the fact that recovery was necessary is itself evidence that the lane was not under active coordination.
4. **Current architect priorities lie elsewhere.** p.fMALL documentation reconciliation and the HoloIndex / TurboQuant truth path are the currently-prioritized lanes. Reactivating AutoAgent Lab would compete with those without explicit authorization.

---

## 3. Reactivation gate

Before any worker resumes Layer 4 implementation, **both** of the following must be true:

1. The architect has added a row for AutoAgent Lab to `ACTIVE_SLICE_LEDGER.md` (ledger edits are out of scope for this park note).
2. The architect has explicitly assigned the slice `AUTOAGENT_LAB_LAYER4_EXPERIMENT_RUNNER` to a worker window, with an assignment prompt of the normal form.

Until both conditions hold, workers must not branch, implement, or PR Layer 4 or Layer 5 work for AutoAgent Lab — even opportunistically from adjacent slices.

---

## 4. Next slice if reactivated

Slice id: `AUTOAGENT_LAB_LAYER4_EXPERIMENT_RUNNER`

Expected files (per `AUTOAGENT_BUILD_ORDER.md` §"Layer 4" PR plan):

- `modules/infrastructure/autoagent_lab/src/experiment_runner.py`
- `modules/infrastructure/autoagent_lab/src/diff_recorder.py`
- `modules/infrastructure/autoagent_lab/tests/test_experiment_runner.py`
- Optional: `modules/infrastructure/autoagent_lab/tests/test_diff_recorder.py` — architect decision at assignment time.
- `modules/infrastructure/autoagent_lab/INTERFACE.md` — extend with the runner / recorder surface.
- `modules/infrastructure/autoagent_lab/ModLog.md` — new V0.4.0 entry.

Scope notes for the future assignment prompt (captured here only so the assigning architect does not need to re-derive them):

- Composition of existing L1 safety gates, L2 eval_harness, L3 target_surface. No new safety surface.
- Mutation strategy is **deterministic** per `AUTOAGENT_BUILD_ORDER.md` §"Mutation Strategy" — field swap, WSP chain edit, tokens_budget adjust, prompt variation. LLM-generated mutations are Phase 3+, not Layer 4.
- `diff_recorder` output format is specified only as "summary + diff artifact" in the build order; a micro-decision is required at assignment time (recommended default: JSONL per-iteration records under `workspace/exp_<id>/iterations.jsonl` plus a terminal summary JSON).
- Score-regression gate (L1 `check_score_regression`) drives the keep/discard decision. Budget (L1 `IterationBudget`) drives the stop condition. No new gates.

---

## 5. What this briefing does **not** do

- Does not implement Layer 4 or Layer 5.
- Does not edit `ACTIVE_SLICE_LEDGER.md`.
- Does not modify any file under `modules/infrastructure/autoagent_lab/`.
- Does not re-scope or amend `AUTOAGENT_BUILD_ORDER.md`.
- Does not touch p.fMALL, HoloIndex, or TurboQuant artifacts.

This is a single-file coordination record.

---

## 6. Cross-references

- Build order: `docs/audits/autoagent_wre/AUTOAGENT_BUILD_ORDER.md`
- Integration spec: `docs/audits/autoagent_wre/AUTOAGENT_WRE_INTEGRATION_SPEC.md`
- Eval & safety: `docs/audits/autoagent_wre/AUTOAGENT_EVAL_AND_SAFETY_GATES.md`
- Target-surface boundary: `docs/audits/autoagent_wre/AUTOAGENT_TARGET_SURFACE_BOUNDARY.md`
- Module ModLog: `modules/infrastructure/autoagent_lab/ModLog.md`
- Rescue PR: GitHub PR #410 — merge commit `9b0ee293098b2829e3d13467e10a55f669dc324d`
