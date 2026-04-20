# Active Slice Ledger

**Authority**: 0102 architect lane
**Updated**: 2026-04-21 (LEDGER-RECON3 post-PR-queue-cleanup)
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
| `pfmall_architecture_and_template_contract` | `a4eb171f1` | `PFMALL_ARCHITECTURE_CONTRACT.md` — template structure, state overlay design |
| `pfmall_state_overlay_contract` | `14e8c6063` | `PFMALL_STATE_OVERLAY_CONTRACT.md` — state provider interface, overlay lifecycle |
| `openclaw_pfmall_catalog_integration` | `fd583820c` | OpenClaw catalog integration for p.fMALL template discovery |
| `pfmall_state_provider_poc` | `6670ae433` | p.fMALL state provider PoC implementation |
| `holoindex_cli_extraction` | `e3d9fd181` | HoloIndex CLI command structure extracted from monolith |
| `holoindex_cli_compatibility_hardening` | `c724f574c` + `9db825088` | CLI test compatibility hardened; accidental cli.py re-creation removed |
| `dj_ai_resolution_hook_contract_phase1` | `1c0ee3f01` (PR #383) | `preflight_resolution.py` + 12 tests + main.py DEP-SECURITY and WSP-FRAMEWORK emitters wired |
| `dj_obs_antifafm_preflight_emitter_phase1` | `fde9d64a4` | `obs_controller.py` start-timeout dispatch (component=obs_start, severity=critical, 14-field AF2 payload) + 6 tests in `test_obs_controller_startup.py` |
| `antifafm_af1_af2_readiness_briefings` | PR #388 | AF1 internal readiness audit + AF2 OBS escalation spec persisted |
| `fca1_ag2_main_dae_ai_overseer_hooks_audit` | `1eb5c08de` (PR #389) | `FCA1_AG2_MAIN_DAE_AI_OVERSEER_HOOKS_AUDIT_PHASE1.md` — 9-preflight matrix, 5 WSP 97 violations, DJ2-A…F sequence |
| `youtube_auth_oauth_operator_assist_skillz` | `c35186e26` (PR #390) | OAuth operator-assist SKILLz contracts (YT2) |
| `yt2_set1_reauth_operator_runbook` | `ce2e27d81` (PR #386) | Set 1 reauth operator runbook |
| `ytr1_video_comments_runtime_hardening` | `95a685e25` (PR #387) | Reply runtime model + Selenium handling hardened |
| `hermes_de2_gotjunk_extraction_validation` | `d6eb3db59` (PR #385) | DE2 gotjunk extraction validation gate briefing |
| `hermes_de3_di1_briefings` | `729910d3f` (PR #391) | DE3 boundary cleanup + DI1 decision gate briefings |
| `gotjunk_cloud_run_autonomous_deploy` | `8851af3ed` (PR #392) | Autonomous Cloud Run deploy workflow |
| `dj2_a_wre_dashboard_insufficient_data_warn` | `904c3bb2f` (PR #393) | WRE dashboard INSUFFICIENT_DATA now dispatches as WARN (DJ2-A closed) |
| `pqn_wsp97_prototype_downgrade` | `343848ad5` (PR #394) | Doc-only PQN skills downgraded to prototype per WSP 97 |
| `ledger_reconciliation_phase1` | `7bc4499ee` (PR #395) | `ACTIVE_SLICE_LEDGER.md` reconciled from 2026-03-31 to 2026-04-20 repo truth; 13 closed entries added; FX1/BH1/DJ2-C–F/PMCTRL1 queued; SoftProto archived |
| `fam_ideation1_foundup_outcome_backpropagation_contract_phase1` | `dcc9ddfdd` (PR #403) | WSP 27 §8.1 FoundUp Ideation / Genesis Contract. Defines `OutcomeContract` + structured `AcceptanceCriterion` + `BackpropagationPlan` + `FoundUpGenesisEnvelope`. WSP 97 truth gates (documented→scaffold→executable→verified). `blocked_outcome_drift` decoherence state. WSP 80 boundary. Both WSP 27 copies (framework + knowledge) synchronized. Status: documented-state spec only. |
| `fx1_holoindex_truth_restoration` | `9a89fedeb` (PR #398) | HoloIndex retrieval mode surfaced; offline fallbacks hardened; WSP 97 truth layer restored. |
| `dj2_c_oauth_preflight_dispatch` | `d0d51e21a` (PR #399) | OAuth preflight WARN paths dispatch to AI Overseer; 2 sites wired in `main.py`. |
| `bh2_pr_scope_guard` | `d5a392700` (PR #397) | `tools/pr_scope_guard/pr_scope_guard.py` prevents mixed-scope PRs; briefing at `BH2_BRANCH_HYGIENE_SCOPE_GUARD_PHASE1.md`. |
| `yt_cleanup1_stream_resolver_collection_fix` | `67ffbe8da` (PR #400) | stream_resolver test collection restored (42 collect, 30/42 pass); pytz dep + import fixes; 12 failures deferred to YT-CLEANUP2. |
| `btc_arch1_architecture_memo` | `53523c88b` (PR #402) | `FOUNDUPS_BTC_RESERVE_TOKEN_ARCHITECTURE.md` strategic memo; Hotel California reserve + I_i bonding curve + UPS backing. |
| `pmctrl1_pfmall_agent_control_dispatcher` | `108c0a47f` (PR #405) | `pfmall-control-dispatcher.js` Layer 1+2; device policy denial; briefing `PMCTRL1_PFMALL_AGENT_CONTROL_CONTRACT_PHASE1.md`. |
| `dupool_truth1_du_pool_ii_truth_alignment` | `ede4bd4b6` (PR #406) | Du pool staker model clarified; I_i bonding curve frozen; regulatory-safe terminology alignment. |

---

## Open Slices

| Slice | Priority | Blocked By | Notes |
|-------|----------|------------|-------|
| `bh1_branch_hygiene_forensics` | HIGH | — | Commit `fde9d64a4` (DJ-OBS) appears in `origin/main` with no matching PR number in `gh pr list`. Investigate provenance + enforce branch/PR matching. No briefing yet. |
| `dj2_b_ironclaw_skip_intentionality_assertion` | MEDIUM | — | Whitelist known-good backend strings; unrecognised backend → dispatch severity=medium, likely_cause=`unexpected_backend_string_skipped_runtime_probe`. Touches `main.py`. |
| `dj2_d_brain_artifact_missing_dir_event` | LOW | — | Dispatch on `preflight=PASS (missing)` with severity=low, automation_candidate=False. Touches `main.py`. |
| `dj2_e_git_merge_sentinel_import_failure_event` | LOW | — | Dispatch on ImportError branch. severity=low. Preserve return behaviour. Touches `main.py`. |
| `dj2_f_openclaw_security_fail_dispatch` | HIGH | — | Mirror DEP-SECURITY wiring at passed=False. severity=high default. Touches `main.py`. |
| `yt_cleanup2_stream_resolver_api_contract_rebase` | MEDIUM | — | Remaining 12 test failures in stream_resolver due to old API-contract assertions; needs rebase against current codebase. Deferred from YT-CLEANUP1. |
| `legal_ii1_bonding_curve_review_packet` | unassigned | — | I_i / Iᵢ bonding curve legal review packet preparation. Regulatory framing, UBA terminology, Du pool staker model. Follows DUPOOL-TRUTH1 freeze. |
| `fam_ideation2_envelope_schema_validator` | unassigned | — | Typed `FoundUpGenesisEnvelope` dataclass + schema validator. Includes DAG validation (cycle detection, missing preconditions, orphan postconditions) + structured `AcceptanceCriterion {observable, method, oracle, pass_condition}` enforcement. Specified in WSP 27 §8.1.10 slice 2. No worker assigned. |
| `fam_ideation3_ai_overseer_truth_sentinel` | unassigned | — | AI Overseer WSP 97 field-status drift sentinel. Detects `wsp_97_field_status_map` inconsistencies vs repo truth + `outcome_contract_decoherence` per WSP 27 §8.1.7.1. Dispatches `component=foundup_genesis`. **Hard ordering constraint**: MUST land before any `LaunchOrchestrator.accept_envelope()` implementation (IDEATION4) so no envelope enters FAM with undetected-lie state. No worker assigned. |

---

## Blocked Slices

| Slice | Reason |
|-------|--------|
| _(none)_ | — |

---

## Deferred Slices

| Slice | Reason |
|-------|--------|
| `de4_hermes_extraction_next_sandbox` | Deferred pending DE2/DE3/DI1 downstream outcomes |

---

## Archive / Reconcile-Needed

| Track | Status | Action | Blocked By |
|-------|--------|--------|------------|
| `softproto` | ARCHIVE_RECONCILE_NEEDED | read-only reconciliation only, not implementation | PMCTRL1 contract stabilization |

**SoftProto scope** (2026-04-01 architecture prompts):
- `docs/0102_session_briefings/SOFTPROTO_{A,B,C,D}_*_PROMPT_2026-04-01.md` (gateway / mall / concierge-reddog / guardrails audits)
- `docs/0102_session_briefings/SOFTPROTO_SVELTE_SPIKE_PHASE1_PROMPT_2026-04-01.md`
- `modules/foundups/docs/SOFTPROTO_*_CONTRACT.md` + `SOFTPROTO_FOUNDATION_ARCHITECTURE_2026-04-01.md` + `SOFTPROTO_ROLLOUT_PLAN_2026-04-01.md`

**Architect read**: SoftProto's old concerns (module registry, command paths, validation envelopes, guarded interiors, gestures/overrides, mall/concierge/RedDog audits) overlap with newer active work — PMCTRL1 (pfMALL browser agent control), WRE/SKILLz command surfaces, RedDog/0102 control hooks, Hermes extraction boundary, FoundUp manifest/INTERFACE contracts.

**Not an active implementation lane.** Do not revive as priority wave until reconciled against PMCTRL1 and current WRE contracts.

**Next reconciliation slice (if/when needed)**: `SOFTPROTO-RECON1` — read-only audit; decide which SoftProto contracts are superseded by PMCTRL1/WRE/Hermes and which should be preserved. No code edits.

---

## Forbidden Duplicates

Do NOT re-implement any slice in the Closed table above.
If prompted to re-do them, report the commit and redirect to the next open slice.

---

## Next Priority Order

Serialisation requirement (per FCA1-AG2 audit §9): DJ2-B…F each edit `main.py`; run one PR at a time unless a shared `_emit_preflight_fail()` helper is extracted first. DJ2-C merged (#399), unblocking the rest.

1. **BH1** — Branch hygiene forensics (resolve `fde9d64a4` provenance before next main-touching slice)
2. **DJ2-F** — OpenClaw Security fail dispatch (highest-severity remaining hook gap)
3. **DJ2-B** — IronClaw skip intentionality assertion
4. **DJ2-D** — Brain artifact missing-dir event
5. **DJ2-E** — Git merge sentinel ImportError event
6. **YT-CLEANUP2** — stream_resolver API-contract test rebase (12 remaining failures)
7. **LEGAL-Ii1** — I_i bonding curve legal review packet (unassigned)
8. **FAM-IDEATION2** — typed `FoundUpGenesisEnvelope` schema + validator (unassigned)
9. **FAM-IDEATION3** — AI Overseer WSP 97 drift sentinel (unassigned; hard-gated before IDEATION4)

---

## PR Queue

| PR | Branch | Status | Contents |
|----|--------|--------|----------|
| _(CLEAR)_ | — | — | All PRs #397–#406 merged. FX1, DJ2-C, BH2, YT-CLEANUP1, BTC-ARCH1, PMCTRL1, DUPOOL-TRUTH1 closed. Next: BH1 forensics or DJ2-F. |

---

## Update Protocol

When a slice lands:
1. Move it from Open to Closed with commit hash
2. Remove it from Blocked if it was blocked
3. Add the actual next open slice if known
4. Commit this file as part of the slice's completion commit or immediately after

This ledger is not a planning doc. It is repo-truth state.
