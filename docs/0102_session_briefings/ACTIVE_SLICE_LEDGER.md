# Active Slice Ledger

**Authority**: 0102 architect lane
**Updated**: 2026-03-31 (training_system_utf8_import_boundary_fix complete)
**Rule**: Every agent reads this first. If repo truth contradicts an entry, update this ledger — not 012.

---

## Anti-Decoherence Rule

Do not ask 012 to resolve slice status if repo truth can resolve it.

Assume 012 may be mistaken about:
- what is already done
- what is still open
- what the next slice is

Your first duty is to recover repo truth.

Before any mutation, state exactly:

- `Closed groundwork:` what is already landed, with commit/file evidence
- `Open target:` what remains open in current repo truth
- `Chosen slice:` the one bounded slice you are executing now
- `Not this slice:` what you are explicitly not touching

If the requested slice is already committed or duplicated, do not continue with it.
Correct the plan and proceed with the actual next open slice.

---

## Architect Authority Rule

Only one lane defines the next slice.
Other lanes may:
- audit
- verify
- implement bounded work
- report contradictions

They may not create a parallel architectural branch unless repo truth proves the active lane is wrong.

---

## Duplicate-Work Gate

Before coding, verify:
1. `git log --oneline` for the target files/module
2. current `git diff`
3. whether the claimed slice is already represented in ModLog/ROADMAP/handoff docs

If already landed:
- stop duplicating
- report the commit
- identify the actual next pending slice

---

## Closed Slices

| Slice | Commit | Evidence |
|-------|--------|----------|
| `openclaw_training_route` | `a5376861e` | `openclaw_execution_routes.py` TRAINING intent |
| `openclaw_training_route_tests` | `d8ae025e8` | `test_openclaw_training_route.py` (413 lines) |
| `foundups_canon_docs` | `8b136335d` | `FOUNDUPS_DOMAIN_CANONICAL_INDEX.md`, `FOUNDUP_EXFOLIATION_PROTOCOL.md`, `PQN_SWARM_HUB_FOUNDUP_BRIEF.md` |
| `foundups_domain_canonicalization` | `50eed2f4c` | `README.md` + `INTERFACE.md` tightened, IMPLEMENTED/PLANNED separation |
| `training_corpus_source_of_truth` | `3179bc1af` | `corpus_resolver.py` shared utility, 5 consumers migrated, 8 unit tests |
| `training_corpus_path_normalization` | `64fef5ca1` + `80564559b` | corpus path defaults normalized across holo tools and openclaw boundary |
| `obs_connection_singleton` | `d4d6898f8` | `boot_layer_rotator/executor.py` singleton pattern |
| `supervisor_scan_once_fix` | `71f248d04` | `openclaw_supervisor.py` type mismatch fixed (was in bounded maintenance loop commit) |
| `pqn_swarm_hub_internal_poc_scaffold` | `35d1e2275` | `modules/foundups/pqn_swarm_hub/` — contracts, 4 service modules, 18/18 tests |
| `git_main_merge_sentinel` | `08004c100` (branch `feat/git-main-merge-sentinel-20260318`) | `wre_core/src/git_main_merge_sentinel.py` 284 lines + `main.py:1110` + `.env.example` — plan was stale, work already shipped |
| `openclaw_roadmap_reconciliation` | `a0549830b` | `HERMES_INSPIRED_FOUNDUPS_NATIVE_ROADMAP_2026-03-23.md` — all P0+P1 items audited; 5 closed, 1 partial, 1 not-started; planning_snapshot banner added |
| `model_provider_switching_cleanup` | `b1d66d7ce` | `openclaw_runtime_support.py` — `get_model_availability_snapshot(dae=None)` standalone; `generated_on` timestamp; startup refresh writes same canonical shape; 25 tests in `test_model_provider_status.py` |
| `skill_evolution_loop_phase1_report_surface` | `3ae311767` | `openclaw_skill_evolution.py` + `openclaw_supervisor.py` idle-path integration; env gate `OPENCLAW_SKILL_EVOLUTION_ENABLED=1`; 18 tests in `test_openclaw_skill_evolution.py`; no WRE mutation |
| `pqn_swarm_hub_persistence` | `ae886b4c2` | `persistence.py` + store injection across all 6 services; 41/41 tests; TestModLog.md |
| `pqn_swarm_hub_publication_adapter` | `09fada474` | `publication_adapter.py` wraps MoltBook; 57/57 tests; rejected decisions gate |
| `pqn_swarm_hub_runbook` | `08b3f3f35` | `RUNBOOK.md` reproducible execution guide; Phase 1 COMPLETE (10/10 slices) |
| `pqn_swarm_hub_proto_readiness_review` | `97b5e952c` | Phase 2 entry APPROVED; 3 true blockers classified; GPD NOT blocker |
| `pqn_swarm_hub_fam_live_validation` | `d5fca817d` | 15/15 live FAM tests; 72/72 module total; adapter boundary respected |
| `pqn_swarm_hub_external_submission_type` | `70115efff` | 14/14 tests; source field in contracts; register_external + submit_external methods |
| `pqn_swarm_hub_external_contributor_path` | `db9df7598` | CONTRIBUTING.md + 22/22 gate tests; Phase 2 COMPLETE |
| `pqn_swarm_hub_exfoliation_review_decision` | `c0cf513de` | Architect decision: APPROVE_PHASE_3_PREP; doc reconciliation |
| `pqn_swarm_hub_phase3_prep_scaffold` | `1dbdd1dcb` | Migration scaffold: MANIFEST + DUAL_REMOTE + EXFOLIATION plans |
| `pqn_swarm_hub_phase3_migration_exec` | (standalone) | External repos created and pushed: `FOUNDUPS/science-swarm-hub` + `Foundup/science-swarm-hub` — standalone tests pass |
| `science_swarm_hub_monorepo_reconciliation` | (previous slice) | Monorepo docs reconciled post-migration; stale "blocked" language removed |
| `science_swarm_hub_monorepo_stub_cutover` | (this slice) | Stub cutover complete: src/ and tests/ deleted, __init__.py replaced with package import stub |
| `youtube_domain_phase1` | (previous slice) | G1: stall check wired to heartbeat; G2: rotation_checkpoint.py + supervisor integration |
| `youtube_domain_phase2` | `029c57e9a` | G3: youtube_channel_operations table + sentinel methods; G5: cycle watchdog + breadcrumb; STT/TTS boundary; 27 tests |
| `youtube_domain_phase3` | (previous commit) | G4: schedule_audit_unhealthy breadcrumb; G6: escalation path with human_intervention_required; 16 tests |
| `chrome_146_pin_workaround` | (local) | Pinned `version_main=146` in news_maps executor; Chrome 147 not yet rolled out |
| `skill_evolution_loop_phase2_mutation_surface` | `448424358` | Phase 2 mutation surface: 3 env gates (fail-closed), A/B test status + promotion readiness queries via WRE primitives; supervisor idle-path integration; 23 new tests (41 total) |
| `antifafm_voxtral_eval_contract` | `ebacf5cc1` | `VOXTRAL_EVAL_CONTRACT.md` eval-only lane; 4 TTS candidate surfaces; success metrics (<500ms, quality >=4.0); shared audio substrate + voice cloning policy enforcement |
| `training_system_utf8_import_boundary_fix` | `f7b19311b` | 7 regression tests; imports fixed to scanner.py (not main.py); root cause: WSP 62 refactor stopped main.py exports |

---

## Open Slices

| Slice | Priority | Blocked By | Notes |
|-------|----------|------------|-------|
| _(none)_ | — | — | — |

---

## Blocked Slices

| Slice | Reason |
|-------|--------|
| _(none)_ | — |

---

## Forbidden Duplicates

Do NOT re-implement any slice in the Closed table above.
If prompted to re-do them, report the commit and redirect to the next open slice.

---

## Next Priority Order

1. ~~**`pqn_swarm_hub_external_contributor_path`**~~ — COMPLETE (Phase 2 Gate 3)
2. ~~**`pqn_swarm_hub_exfoliation_review_decision`**~~ — COMPLETE (APPROVE_PHASE_3_PREP)
3. ~~**`pqn_swarm_hub_phase3_prep_scaffold`**~~ — COMPLETE (`1dbdd1dcb`)
4. ~~**`pqn_swarm_hub_phase3_migration_exec`**~~ — COMPLETE (standalone repos live)
5. ~~**`science_swarm_hub_monorepo_reconciliation`**~~ — COMPLETE (docs updated post-migration)
6. ~~**`science_swarm_hub_monorepo_stub_cutover`**~~ — COMPLETE (stub cutover executed)
7. ~~**YouTube Domain Agent Phase 1**~~ — COMPLETE (G1+G2 implemented)
8. ~~**YouTube Domain Agent Phase 2**~~ — COMPLETE (G3+G5: per-channel tracking + cycle watchdog + STT/TTS boundary)
9. ~~**YouTube Domain Agent Phase 3**~~ — COMPLETE (G4+G6: schedule reconciliation breadcrumb + escalation path)
10. ~~**`skill_evolution_loop_phase2_mutation_surface`**~~ — COMPLETE (gated mutation surface with 3 env gates, WRE primitive queries)
11. _(awaiting next slice from 012)_

---

## PR Queue

| PR | Branch | Status | Contents |
|----|--------|--------|----------|
| _(none)_ | — | — | — |

---

## Update Protocol

When a slice lands:
1. Move it from Open to Closed with commit hash
2. Remove it from Blocked if it was blocked
3. Add the actual next open slice if known
4. Commit this file as part of the slice's completion commit or immediately after

This ledger is not a planning doc. It is repo-truth state.
