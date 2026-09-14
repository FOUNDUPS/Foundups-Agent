# TestModLog - wre_master_orchestrator/tests

## 2026-09-15: Execution-owned fingerprint regression

- Existing execution/admission suites add six cases: changed/unchanged reentrant execution, explicit/missing fingerprint, cached success/failure and a later call replacing cache contents before the earlier return. Original tests remain; two assertions/mocks now bind explicit receipt values. Identical helper classes are imported/re-exported from the existing admission suite.
- Before: one failure/one passing control/22 deselected in 2.35s. After: 71 focused passes/one skip in 4.58s; 172 connected passes/four existing link skips in 9.97s. Selections overlap. Manifest 8 passes in 69.93s; fast 15 groups in 5,013ms; registry current 1,650/269. Local files and scanner doubles, no live admission/model/FoundUp call.
- Commands, exact skipped IDs, source hashes and size checks: `execution_admission_ownership_continuation_20260915`; WSP 00/15/22/50/60/62/84/95/97. Legacy public two-value API is explicitly covered.

## 2026-09-14: Coordinator scan-policy readback

- All 23 cases in `test_wre_master_orchestrator.py` passed as part of the isolated
  seven-file 148-pass/four-skip WRE scan-cache run. New policy-read regression reuses
  the existing root `test_wre_runtime_admission_truth.py`; no nested test changed.
- Commands/environment and exact IDs: `admission_cache_ownership_continuation_20260914`
  in the root RSI baseline. Local/injected evidence only; WSP 22/50/95/97.

## 2026-03-05: Post-escalation orchestrator security lane

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q modules/infrastructure/wre_core/tests/test_codeact_executor_hardening.py modules/infrastructure/wre_core/tests/test_dependency_security_preflight.py modules/infrastructure/wre_core/tests/test_skill_manifest_guard.py modules/infrastructure/wre_core/tests/test_dae_preflight_integration_guard.py modules/infrastructure/wre_core/tests/test_dae_preflight_security_behavior.py modules/infrastructure/wre_core/wre_master_orchestrator/tests/test_wre_master_orchestrator.py modules/communication/moltbot_bridge/tests/test_skill_safety_guard.py -k "supply_chain_gate or hardening or dependency or manifest or self_audit or preflight"`
- Status: PASS
- Result: `16 passed, 30 deselected, 2 warnings`
- Notes:
  - Confirms orchestrator supply-chain gate behavior remains stable after self-audit escalation updates.

---

## 2026-03-05: Full suite attempt bounded by timeout; fallback to targeted lanes

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q modules/infrastructure/wre_core/wre_master_orchestrator/tests`
- Status: TIMEOUT
- Result: timed out at 300s in local environment
- Notes:
  - Full suite includes integration-heavy execution paths that can exceed bounded CI/local timeout.
  - Targeted security/orchestrator regression lanes were executed and passed (see entry below).

---

## 2026-03-05: Supply-chain gate and orchestrator regression sweep

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q modules/infrastructure/wre_core/tests/test_daemon_self_audit_loop.py modules/infrastructure/wre_core/tests/test_codeact_executor_hardening.py modules/infrastructure/wre_core/tests/test_dependency_security_preflight.py modules/infrastructure/wre_core/tests/test_skill_manifest_guard.py modules/infrastructure/wre_core/tests/test_dae_preflight_integration_guard.py modules/infrastructure/wre_core/tests/test_dae_preflight_security_behavior.py modules/infrastructure/wre_core/wre_master_orchestrator/tests/test_wre_master_orchestrator.py modules/communication/moltbot_bridge/tests/test_skill_safety_guard.py -k "supply_chain_gate or hardening or dependency or manifest or self_audit or preflight"`
- Status: PASS
- Result: `20 passed, 30 deselected, 2 warnings`
- Notes:
  - Confirms `_ensure_wre_skill_safety()` gate behavior and targeted orchestrator regression lanes remain stable after WSP 15 security changes.

---
