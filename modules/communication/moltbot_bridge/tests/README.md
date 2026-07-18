# Tests - OpenClaw Bridge

## Coverage Goals
- Intent classification and routing behavior.
- WSP preflight + permission gates.
- End-to-end `process()` safety fallbacks.
- Cisco skill scanner guard behavior.
- Skill boundary policy enforcement (workspace skills vs internal `skillz`).
- SOURCE tier permission enforcement (AgentPermissionManager).
- Webhook rate limiting (token bucket per sender/channel).
- COMMAND graceful degradation (WRE unavailable fallback).

## Run
```powershell
cd o:\Foundups-Agent
.\modules\communication\moltbot_bridge\tests\run_tests.ps1
```

CI gate behavior:
- Runs security tests first and fails fast if any fail:
  - `test_skill_boundary_policy.py`
  - `test_skill_safety_guard.py`
  - `test_hardening_tranche.py`
- Use `-SkipSecurityGate` only for local diagnostics (never for CI/prod).

Optional custom args:
```powershell
.\modules\communication\moltbot_bridge\tests\run_tests.ps1 -PytestArgs @("-q", "-k", "skill_safety")
```

Focused RedDog WRE operational spine:
```powershell
python -m pytest modules/communication/moltbot_bridge/tests/test_reddog_wre_operational_spine.py modules/communication/moltbot_bridge/tests/test_reddog_wre_worktree_create.py modules/communication/moltbot_bridge/tests/test_reddog_wre_execution_valve.py modules/communication/moltbot_bridge/tests/test_reddog_wre_executor_dryrun.py modules/communication/moltbot_bridge/tests/test_reddog_work_order_runtime_invocation.py -q
```

Focused resident live-canary harness:
```powershell
python -m pytest modules/communication/moltbot_bridge/tests/test_reddog_resident_live_canary.py modules/communication/moltbot_bridge/tests/test_reddog_resident_runtime_artifact_readiness.py -q
```

This suite uses injected readiness/control-loop probes, a temporary local Git
repository with a registered worktree, the atomic chain store and planner, and
a temporary PatternMemory SQLite database. The draft-PR runner remains an
injected no-network test double. One bounded Python subprocess proves
interprocess lock exclusion. It does not start a signer, call OpenRouter, push
a branch, or create a PR.

Focused canonical execution-valve supplier/evaluator:
```powershell
python -m pytest modules/communication/moltbot_bridge/tests/test_reddog_execution_valve_environment_supply.py modules/communication/moltbot_bridge/tests/test_reddog_wre_execution_valve.py -q
```
