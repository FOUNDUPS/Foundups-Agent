# TestModLog - tests

## 2026-03-05: Post-escalation shared security regression sweep

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q modules/infrastructure/wre_core/tests/test_codeact_executor_hardening.py modules/infrastructure/wre_core/tests/test_dependency_security_preflight.py modules/infrastructure/wre_core/tests/test_skill_manifest_guard.py modules/infrastructure/wre_core/tests/test_dae_preflight_integration_guard.py modules/infrastructure/wre_core/tests/test_dae_preflight_security_behavior.py modules/infrastructure/wre_core/wre_master_orchestrator/tests/test_wre_master_orchestrator.py modules/communication/moltbot_bridge/tests/test_skill_safety_guard.py -k "supply_chain_gate or hardening or dependency or manifest or self_audit or preflight"`
- Status: PASS
- Result: `16 passed, 30 deselected, 2 warnings`
- Notes:
  - Confirms Moltbot skill-safety + manifest lanes remain stable after 0102 self-audit escalation phase.

---

## 2026-03-05: Shared WSP 15 security regression sweep (includes skill safety gate)

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q modules/infrastructure/wre_core/tests/test_daemon_self_audit_loop.py modules/infrastructure/wre_core/tests/test_codeact_executor_hardening.py modules/infrastructure/wre_core/tests/test_dependency_security_preflight.py modules/infrastructure/wre_core/tests/test_skill_manifest_guard.py modules/infrastructure/wre_core/tests/test_dae_preflight_integration_guard.py modules/infrastructure/wre_core/tests/test_dae_preflight_security_behavior.py modules/infrastructure/wre_core/wre_master_orchestrator/tests/test_wre_master_orchestrator.py modules/communication/moltbot_bridge/tests/test_skill_safety_guard.py -k "supply_chain_gate or hardening or dependency or manifest or self_audit or preflight"`
- Status: PASS
- Result: `20 passed, 30 deselected, 2 warnings`
- Notes:
  - Confirms Moltbot skill safety and manifest/security controls remain stable alongside WRE self-audit and preflight hardening.
  - Warnings are repo-level pytest config warnings (`asyncio_*`) under plugin-autoload-disabled mode.

---

## 2026-02-16: Cross-module concatenated validation (identity-anchor hardening)

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests modules/foundups/agent_market/tests modules/foundups/simulator/tests -q`
- Status: PASS
- Result: `335 passed, 2 warnings`
- Notes:
  - Confirms OpenClaw conversation identity-anchor normalization resolves
    nondeterministic conversation assertions in end-to-end tests.
  - Includes SSE member-gate + DEX stream contract + symbol guardrail lanes.
  - Warnings are repo-level pytest config warnings (`asyncio_*`) under plugin-autoload-disabled mode.

---

## 2026-02-16: Cross-module concatenated validation

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests modules/foundups/agent_market/tests modules/foundups/simulator/tests -q`
- Status: PASS
- Result: `321 passed, 2 warnings`
- Notes:
  - Confirms FAM adapter and Moltbook adapter compatibility updates did not regress OpenClaw test coverage.
  - Warnings are repo-level pytest config warnings (`asyncio_*`) under plugin-autoload-disabled mode.

---

## 2026-02-08: Hardening Tranche - 72 tests passing

- Command: `.\modules\communication\moltbot_bridge\tests\run_tests.ps1`
- Status: PASS
- Result:
  - Security gate: PASS (3 files: skill_boundary_policy, skill_safety_guard, hardening_tranche)
  - Full suite: `72 passed`
- Notes:
  - Added `test_hardening_tranche.py` (17 new tests):
    - SOURCE tier enforcement: 6 tests (fail-closed, permission check, exceptions, event emission, dedupe)
    - Webhook rate limiting: 6 tests (token bucket, sender/channel isolation, refill, disabling)
    - COMMAND graceful degradation: 5 tests (WRE unavailable, exception, advisory content, error detail)
  - CI gate now includes `test_hardening_tranche.py` as security-critical.
  - Test count progression: 20 -> 34 -> 45 -> 55 -> 72

---

## 2026-02-07: Security gate + full suite validation (post-hardening)
- Command: `.\modules\communication\moltbot_bridge\tests\run_tests.ps1`
- Status: PASS
- Result:
  - Security gate: PASS (`test_skill_boundary_policy.py`, `test_skill_safety_guard.py`)
  - Full suite: `55 passed`
- Notes:
  - CI now fails fast if security gate tests fail.
  - `-SkipSecurityGate` is for local diagnostics only.

## 2026-02-07: Skill boundary policy enforcement tests
- Command: `.\modules\communication\moltbot_bridge\tests\run_tests.ps1`
- Status: PASS
- Notes:
  - Added `test_skill_boundary_policy.py`.
  - Enforces codified boundary between OpenClaw workspace skills and internal `skillz`.
  - Verifies all mutating intent categories call `_ensure_skill_safety()`.
  - Full module suite currently: `45 passed`.

## 2026-02-07: Deterministic runner entrypoint
- Command: `powershell -NoProfile -ExecutionPolicy Bypass -File modules/communication/moltbot_bridge/tests/run_tests.ps1`
- Status: PASS
- Result: 34 passed, 2 warnings
- Notes:
  - Canonical test entrypoint now codified in `run_tests.ps1`.
  - Runner pins local venv python and disables third-party pytest plugin autoload for deterministic execution.

## 2026-02-07: WSP 95/71 Security Audit Test Coverage
- Command: `.\modules\communication\moltbot_bridge\tests\run_tests.ps1`
- Status: PASS
- Result: 34 passed, 2 warnings
- Notes: Added 14 comprehensive skill safety guard tests for WSP 95/71 compliance:
  - Unit tests: scanner missing, zero/nonzero exit, severity thresholds (high/medium/low/critical)
  - Integration tests: required mode blocking, cache TTL, cache expiry, enforced/non-enforced modes
  - All mutating DAE entrypoints audited and confirmed gated

## 2026-02-07 (earlier)
- Command: `.\modules\communication\moltbot_bridge\tests\run_tests.ps1`
- Status: PASS
- Result: 20 passed, 2 warnings
- Notes: Includes skill safety guard tests and OpenClaw DAE routing tests.

## 2026-03-06: Qwen3.5 model-switch coverage
- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "qwen3_5 or model_switch_local_qwen3_5_updates_conversation_target or model_availability_snapshot_includes_qwen3_5_target" -q`
- Status: PASS
- Result: `2 passed, 84 deselected, 2 warnings`
- Notes:
  - Added regression coverage for `switch model to qwen3.5`.
  - Added availability snapshot assertion for `local/qwen3.5-4b`.

## 2026-03-07: ZeroClaw runtime profile regression coverage
- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "zeroclaw or runtime_profile or model_switch_external_blocked_by_zeroclaw_profile" -q`
- Status: PASS
- Result: `3 passed, 86 deselected, 2 warnings`
- Notes:
  - Validates `OPENCLAW_RUNTIME_PROFILE=zeroclaw` forces fail-closed external policy.
  - Validates external model-switch commands are blocked under ZeroClaw.
  - Validates mutating intent is downgraded to conversation route in full `process()` loop.

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -q`
- Status: PASS
- Result: `89 passed, 2 warnings`
- Notes:
  - Full-file regression confirms new runtime-profile gates do not break existing OpenClaw DAE behavior.

## 2026-03-15: PQN runtime broker adapter tests

**Files**
- `test_pqn_research_adapter.py`

**Coverage**
- `launch pqn research` -> broker `start_dae("pqn_research")`
- `status pqn architect` -> broker status rendering
- `stop pqn research` -> broker `stop_dae("pqn_research")`
- missing broker fallback text

**Run**
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest modules/communication/moltbot_bridge/tests/test_pqn_research_adapter.py -q`

**Result**
- `4 passed`
