# TestModLog - tests

## 2026-03-11: OpenClaw bootstrap constructor extraction regression

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "identity_query or model_switch or qwen3_5 or platform_context or agentic_model_selection_routes_code_turn_to_coder or connect_wre or runtime_profile or preferred_external" -q`
- Status: PASS
- Result: `21 passed, 75 deselected, 2 warnings`
- Notes:
  - Confirms `openclaw_bootstrap_config.py` preserves constructor-initialized identity, platform-context, preferred-external, and agentic model state after extraction from `openclaw_dae.py`.
  - Warnings are existing repo-level pytest config warnings under plugin-autoload-disabled mode.

---

## 2026-03-11: OpenClaw provider/runtime chain extraction regression

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "identity_query or model_switch or qwen3_5 or platform_context or connect_wre or preferred_external or runtime_profile" -q`
- Status: PASS
- Result: `20 passed, 76 deselected, 2 warnings`
- Notes:
  - Confirms `openclaw_provider_chain.py` and the `openclaw_runtime_support.py` autostart extraction preserve provider selection, runtime-profile gates, and conversation identity behavior after extraction from `openclaw_dae.py`.
  - Warnings are existing repo-level pytest config warnings under plugin-autoload-disabled mode.

---

## 2026-03-11: OpenClaw identity/model-policy extraction regression

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "identity_query or model_switch or qwen3_5 or platform_context or agentic_model_selection_routes_code_turn_to_coder or connect_wre" -q`
- Status: PASS
- Result: `20 passed, 76 deselected, 2 warnings`
- Notes:
  - Confirms `openclaw_identity_context.py` and `openclaw_model_policy.py` preserve existing identity, model-switch, platform-context, and agentic model-routing behavior after extraction from `openclaw_dae.py`.
  - Warnings are existing repo-level pytest config warnings under plugin-autoload-disabled mode.

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_dae_social_actions.py -q`
- Status: PASS
- Result: `7 passed, 2 warnings`
- Notes:
  - Confirms the new extraction does not regress OpenClaw social-action identity/status surfaces.

---

## 2026-03-11: OpenClaw social/conversation extraction regression

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_dae_social_actions.py modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "social or conversation or identity_query or model_switch or connect_wre" -q`
- Status: PASS
- Result: `56 passed, 47 deselected, 2 warnings`
- Notes:
  - Confirms `openclaw_social_controller.py` and `openclaw_conversation_engine.py` preserve the public `OpenClawDAE` behavior after extraction from `openclaw_dae.py`.

---

## 2026-03-10: OpenClaw runtime/identity helper extraction regression

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "structured_actions_to_central_daemon or model_availability_snapshot or qwen3_5 or identity_query" -q`
- Status: PASS
- Result: `10 passed, 86 deselected, 2 warnings`
- Notes:
  - Confirms `openclaw_action_ledger.py` and `openclaw_runtime_support.py` preserve existing identity/model-selection/runtime behavior after extraction from `openclaw_dae.py`.
  - Warnings are existing repo-level pytest config warnings under plugin-autoload-disabled mode.

---

## 2026-03-10: OpenClaw DAEmon action ledger regression

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "structured_actions_to_central_daemon" -q`
- Status: PASS
- Result: `1 passed, 95 deselected, 2 warnings`
- Notes:
  - Confirms the OpenClaw autonomy loop emits structured DAEmon action events in addition to `message_in` / `message_out`.
  - Warnings are existing repo-level pytest config warnings under plugin-autoload-disabled mode.

---

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

## 2026-03-10: LinkedIn mission-control + agentic routing regression coverage
- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_linkedin_loop_adapter.py modules/communication/moltbot_bridge/tests/test_openclaw_dae_social_actions.py modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -q`
- Status: PASS
- Result: `106 passed, 2 warnings`
- Notes:
  - Validates conversational LinkedIn loop control through `linkedin_loop_adapter`.
  - Confirms `WSP_97_System_Execution_Prompting_Protocol.md` is present in the default OpenClaw context pack.
  - Validates OpenClawDAE actually routes LinkedIn loop-control phrases through the loop adapter.
  - Regresses mixed code/triage prompts so code-change turns route to `local/qwen-coder-7b`.
  - Validates explicit `follow wsp ...` command routing through the dedicated WSP orchestrator path.

## 2026-03-10: WSP 97 follow-wsp deterministic route smoke slice
- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "follow_wsp or platform_context or agentic_model_selection_routes_code_turn_to_coder" -q`
- Status: PASS
- Result: `5 passed, 90 deselected, 2 warnings`
- Notes:
  - Confirms `follow wsp ...` uses the dedicated WSP orchestrator route.
  - Confirms default platform context still includes `WSP_97`.
  - Confirms code-heavy mixed prompts still route to `local/qwen-coder-7b`.

## 2026-03-11: OpenClaw intent/result seam regression coverage
- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "classify_intent or wsp_preflight or follow_wsp or validate_and_remember or connect_wre or model_switch or identity_query" -q`
- Status: PASS
- Result: `15 passed, 81 deselected, 2 warnings`
- Notes:
  - Confirms extracted intent classification still honors `connect wre`, identity, model switch, and WSP preflight behavior.
  - Confirms extracted validate/remember path still stores and redacts as expected.

## 2026-03-11: OpenClaw permission-policy regression coverage
- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "permission or source or skill_safety or containment or classify_intent or wsp_preflight or validate_and_remember" -q`
- Status: PASS
- Result: `17 passed, 79 deselected, 2 warnings`
- Notes:
  - Confirms autonomy-tier resolution, SOURCE gating, containment, and skill-safety behavior survived extraction to `openclaw_permission_policy.py`.
  - Confirms no regression in extracted intent/result seams while permission policy was moved.

## 2026-03-11: OpenClaw execution-route regression coverage
- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "query or command or follow_wsp or monitor or schedule or automation or foundup or research" -q`
- Status: PASS
- Result: `29 passed, 67 deselected, 2 warnings`
- Notes:
  - Confirms route delegation through `openclaw_execution_routes.py` for all non-social execution planes.
  - Confirms `follow wsp` deterministic routing still executes through the WSP orchestrator after extraction.

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "monitor_returns_status or execute_command_follow_wsp_uses_wsp_orchestrator or identity_query_defaults_to_compact_response" -q`
- Status: PASS
- Result: `3 passed, 93 deselected, 2 warnings`
- Notes:
  - Smoke-checks compact identity, monitor status, and WSP route execution after route-layer extraction.

## 2026-03-11: OpenClaw telemetry + turn-state regression coverage
- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "token_usage or turn_cancellation or identity_query_defaults_to_compact_response or monitor_returns_status" -q`
- Status: PASS
- Result: `4 passed, 92 deselected, 2 warnings`
- Notes:
  - Confirms extracted token telemetry still feeds identity/monitor status correctly.
  - Confirms cooperative turn cancellation still interrupts live turns cleanly after extraction.

## 2026-03-11: OpenClaw status/process regression coverage
- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "test_conversation_returns_response or test_blocked_command_downgrades_to_conversation or test_monitor_returns_status or test_zeroclaw_downgrades_mutating_intent_to_conversation_route or test_process_reports_structured_actions_to_central_daemon" -q`
- Status: PASS
- Result: `5 passed, 91 deselected, 2 warnings`
- Notes:
  - Confirms the extracted `openclaw_process_loop.py` preserves end-to-end autonomy behavior and DAEmon action emission.

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; .\.venv\Scripts\python.exe -m pytest modules/communication/moltbot_bridge/tests/test_openclaw_dae.py -k "token_usage_query_returns_deterministic_report or conversation_honors_turn_cancellation or execute_command_follow_wsp_uses_wsp_orchestrator or monitor_reports_lineage_and_model_name" -q`
- Status: PASS
- Result: `4 passed, 92 deselected, 2 warnings`
- Notes:
  - Confirms extracted status/telemetry surfaces still drive token usage, cancellation, monitor, and follow-wsp behavior correctly.
