# TestModLog - wre_core/tests

## 2026-05-02: Queue retention semantics + retention-aware drain

- Command: `python -m pytest modules/infrastructure/wre_core/tests/test_foundup_job_consumer.py -v`
- Status: PASS
- Result: `29 passed`
- Notes:
  - Added `TestRetentionSemantics` class with 4 tests
  - Tests routing_failure, routing_blocked, empty queue, should_clear properties
  - Updated TestDrainOpenClawQueue for retention-aware behavior
  - Updated TestDrainOpenClawQueueDryRun for retention metadata output

---

## 2026-05-02: drain_openclaw_queue_dry_run convenience function + CLI command

- Command: `python -m pytest modules/infrastructure/wre_core/tests/test_foundup_job_consumer.py -v`
- Status: PASS
- Result: `20 passed`
- Notes:
  - Added `TestDrainOpenClawQueueDryRun` class with 4 tests
  - Tests structured evidence dict, WSP 97 truth fields, empty queue, --no-clear flag
  - CLI: `python run_wre.py drain [--no-clear]`

---

## 2026-03-08: Brain artifact extractor incremental refresh + training signal validation

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q modules/infrastructure/wre_core/tests/test_extract_brain_artifacts.py`
- Status: PASS
- Result: `2 passed, 2 warnings`
- Notes:
  - Validates DPO/SFT extraction from implementation-plan revision chains and walkthroughs.
  - Validates incremental refresh state so unchanged brain directories skip full re-scan.

---

## 2026-03-05: Self-audit escalation lane validation (phase 2)

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q modules/infrastructure/wre_core/tests/test_daemon_self_audit_loop.py`
- Status: PASS
- Result: `6 passed, 2 warnings`
- Notes:
  - Validates adaptive remediation + repeated-signature escalation behavior.
  - Includes escalation command dispatch and escalation state persistence checks.

---

## 2026-03-05: Targeted WSP 15/WSP 48 security regression sweep (post-escalation)

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q modules/infrastructure/wre_core/tests/test_codeact_executor_hardening.py modules/infrastructure/wre_core/tests/test_dependency_security_preflight.py modules/infrastructure/wre_core/tests/test_skill_manifest_guard.py modules/infrastructure/wre_core/tests/test_dae_preflight_integration_guard.py modules/infrastructure/wre_core/tests/test_dae_preflight_security_behavior.py modules/infrastructure/wre_core/wre_master_orchestrator/tests/test_wre_master_orchestrator.py modules/communication/moltbot_bridge/tests/test_skill_safety_guard.py -k "supply_chain_gate or hardening or dependency or manifest or self_audit or preflight"`
- Status: PASS
- Result: `16 passed, 30 deselected, 2 warnings`
- Notes:
  - Confirms no regression after self-audit escalation phase.

---

## 2026-03-05: Full wre_core suite sweep (bounded)

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q modules/infrastructure/wre_core/tests -k "not production_gates"`
- Status: PASS
- Result: `73 passed, 1 skipped, 4 deselected, 3 warnings`
- Notes:
  - Excludes long-running `test_production_gates` lane for bounded local verification.
  - One async test was skipped under plugin-autoload-disabled mode (`PytestUnhandledCoroutineWarning`).

---

## 2026-03-05: WSP 15 security + preflight + self-audit verification sweep

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q modules/infrastructure/wre_core/tests/test_daemon_self_audit_loop.py modules/infrastructure/wre_core/tests/test_codeact_executor_hardening.py modules/infrastructure/wre_core/tests/test_dependency_security_preflight.py modules/infrastructure/wre_core/tests/test_skill_manifest_guard.py modules/infrastructure/wre_core/tests/test_dae_preflight_integration_guard.py modules/infrastructure/wre_core/tests/test_dae_preflight_security_behavior.py modules/infrastructure/wre_core/wre_master_orchestrator/tests/test_wre_master_orchestrator.py modules/communication/moltbot_bridge/tests/test_skill_safety_guard.py -k "supply_chain_gate or hardening or dependency or manifest or self_audit or preflight"`
- Status: PASS
- Result: `20 passed, 30 deselected, 2 warnings`
- Notes:
  - Covers self-audit adaptive remediation tests, CodeAct hardening, dependency preflight, manifest verification, shared DAE preflight behavior, and WRE orchestrator supply-chain gating.
  - Warnings are repo-level pytest config warnings (`asyncio_*`) under plugin-autoload-disabled mode.

---

## 2026-03-06: Dependency preflight multi-lockfile regression test

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest -q modules/infrastructure/wre_core/tests/test_dependency_security_preflight.py`
- Status: PASS
- Result: `6 passed, 2 warnings`
- Notes:
  - Validates new Node lockfile scope behavior (`OPENCLAW_DEP_SECURITY_NODE_LOCK_SCOPE=all`).
  - Confirms aggregate high-vulnerability counting across multiple `package-lock.json` targets.
  - Confirms hidden nested worktree lockfiles are excluded from Node dependency audit.
  - Confirms pip-audit dict payload parsing and unknown-severity threshold enforcement (`OPENCLAW_DEP_SECURITY_MAX_UNKNOWN`).
  - Warnings are unchanged repo-level pytest config warnings (`asyncio_*`) under plugin-autoload-disabled mode.

---
