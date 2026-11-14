# TestModLog - shared tests

## 2026-08-26: WSP 97 v1.9 machine-contract declaration

- Reused the existing canonical validator-contract test to bind protocol
  version 1.9, the test-inventory/reuse applicability set, the active-suite
  missing-TestModLog rule, and concrete HoloIndex work-order guidance.
- Preserved receipt schema v1.1 and all repository-evidence resource limits;
  this is a protocol-data alignment regression, not a validator behavior change.

## 2026-08-08: Startup dependency-evidence enforcement

- Proved malformed dependency scanner evidence remains visible in startup
  telemetry and blocks when enforcement is active. Incomplete optional scans
  are reported as `WARN`, never `PASS`; the 28-test startup matrix passes.

## 2026-07-24: WSP 97 repository-evidence receipt v1.1

- Files: `tests/test_wsp97_execution_validator.py`, `tests/test_wsp97_repository_evidence.py`
- Slice: `WSP97_REPOSITORY_EVIDENCE_V11_PHASE1`
- RED checkpoint: 31 failed, 2 passed, 1 skipped before implementation; the deterministic lstat seam separately failed collection until its helper existed.
- Bounded-contract amendment RED: 15 failed, 38 passed, 1 capability-only skip.
- Cheapest-first amendment RED: 16 failed, 56 passed, 1 capability-only skip.
- Final GREEN: 74 passed, 1 capability-only real-symlink skip after the Holo P0 receipt migration; deterministic POSIX symlink and Windows junction/reparse seams passed.
- Covers schema admission, base binding/ancestry, exact Git root/path/case, traversal and Windows drive/UNC/backslash denial, WSP declaration cross-checking, opaque non-WSP evidence, legacy non-admission, CLI exits, mirrors, and the four migrated base receipts.
- POSIX symlink mode and Windows junction/reparse attributes are tested deterministically; a real symlink integration test remains capability-gated.
- Covers root preflight ordering/no-Git-on-redirect, receipt pre-parse cap, mapping/list/item/string/path/count/aggregate limits, subprocess short-circuit, Git call/time/output bounds, and operational exit `2`.
- Covers zero-Git rejection for missing/bad context, bad/mismatched bases, lexical path/case failures, invalid WSP IDs, and count/path limits.

## 2026-07-17: WSP 97 structural execution receipt validator

- File: `tests/test_wsp97_execution_validator.py`
- Slice: `WSP97_EXECUTION_RECEIPT_VALIDATOR_PHASE1`
- Covers complete seven-stage derivation, missing action evidence, invalid scalar evidence, blocked outcomes, WSP/compliance requirements, contract count drift, active validator metadata, and CLI non-compliance exit behavior.
- Truth boundary: structural receipt validation only; tests do not claim thought inspection, evidence resolution, or runtime side effects.

---

## 2026-07-17: RedDog resident autonomous chain proof

- File: `tests/test_main_runtime_bootstrap.py`
- Slice: `REDDOG_MAIN_RESIDENT_AUTONOMOUS_CHAIN_PROOF_PHASE1`
- New test:
  - `test_main_resident_red_dog_chain_passes_profile_to_downstream_preflights` - asserts `main()` runs the resident RedDog preflights in order and carries `REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF=1` plus `REDDOG_RESIDENT_QUEUE_BINDING_PROFILE=signed_0102_bounded_code_fusion_worktree_draft_pr` into FIX promotion, queue consumer, queue orchestration, queue dispatch, serial loop, and OpenClaw claim loop before menu start.
- Scope: all runtime work mocked; no live model, OpenClaw, shell, worktree, PR, HoloIndex re-index, PatternMemory write, or menu interaction.

---

## 2026-06-07: Headless bootstrap seam (WRE/OpenClaw/Hermes dry-run, W6)

- File: `tests/test_main_runtime_bootstrap.py` (extended: 5 existing + 4 new = 9 tests)
- Slice: `WRE_OPENCLAW_HERMES_AUTONOMOUS_BUILD_DRYRUN_PHASE1`
- New tests:
  - `test_run_headless_bootstraps_dae_specs_before_supervisor_cycle` - asserts call order [bootstrap, run_cycle] and shared broker (OPENCLAW_HEADLESS_MAX_CYCLES=1).
  - `test_run_headless_fail_closed_when_wre_not_ready` - exits 1, no bootstrap/supervisor.
  - `test_run_headless_one_cycle_no_live_execution` - asserts RESIDENT/SUPERVISOR autostart + ALLOW_RESTART defaulted "0".
  - `test_supervisor_triage_escalates_not_live_starts_when_restart_disabled` - triage escalates `resident_openclaw_down_restart_disabled`, not the live `start_openclaw` action.
- Command: `python -m pytest tests/test_main_runtime_bootstrap.py -q`
- Status: **9 passed**. All heavy seams mocked; no live process/network/model/OAuth/Docker/GitHub-write.
- Note: bounded one-cycle dry-run proof only (WSP 97). Pre-existing `test_openclaw_supervisor_p0.py::test_run_cycle_executes_and_completes_pending_autonomous_task` fails on clean main (verified via stash) - out of scope.

---

## 2026-03-18: Main bootstrap resident OpenClaw registration

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest tests/test_main_runtime_bootstrap.py -q`
- Status: PASS
- Notes:
  - Confirms `main.bootstrap_runtime_dae_launches()` registers `openclaw` as a broker-managed launch spec.
  - Confirms resident OpenClaw autostart requests the broker path instead of remaining menu-only.

## 2026-03-18: Main bootstrap PQN simulation registration

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest tests/test_main_runtime_bootstrap.py -q`
- Status: PASS
- Notes:
  - Confirms `main.bootstrap_runtime_dae_launches()` registers `pqn_simulation` as a launchable broker spec.
  - Confirms the simulation lane is bootstrapped alongside the other PQN runtime entrypoints.

## 2026-03-18: Main bootstrap OpenClaw supervisor registration

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest tests/test_main_runtime_bootstrap.py -q`
- Status: PASS
- Notes:
  - Confirms `main.bootstrap_runtime_dae_launches()` registers `openclaw_supervisor`.
  - Confirms supervisor autostart is routed through the broker-managed runtime surface.

## 2026-03-18: IronClaw startup readiness preflight

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest tests/test_main_ironclaw_preflight.py tests/test_main_runtime_bootstrap.py -q`
- Status: PASS
- Result: `7 passed`
- Notes:
  - Confirms startup skips IronClaw readiness when backend is `openclaw`.
  - Confirms startup blocks when IronClaw is the active backend and readiness fails without fallback.
  - Confirms startup warns but allows boot when local fallback policy is enabled.

## 2026-03-18: Main bootstrap HoloDAE stop-hook registration

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest tests/test_main_runtime_bootstrap.py -q`
- Status: PASS
- Notes:
  - Confirms `main.bootstrap_runtime_dae_launches()` registers `holodae` with a real `stop_callable`.

## 2026-03-18: Main bootstrap GitPush and Social Media stop-hook registration

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest tests/test_main_runtime_bootstrap.py -q`
- Status: PASS
- Notes:
  - Confirms `main.bootstrap_runtime_dae_launches()` registers `git_push_dae` with a real `stop_callable`.
  - Confirms `main.bootstrap_runtime_dae_launches()` registers `social_media` with a real `stop_callable`.

---

## 2026-03-08: Markdown sanitizer coverage

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q tests/test_markdown_sanitizer.py`
- Status: PASS
- Result: `2 passed, 2 warnings`
- Notes:
  - Validates ASCII-safe replacements for arrows, dashes, star, and check glyphs.
  - Confirms recursive sanitization across nested Python containers.
