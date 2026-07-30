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

Focused architect-FIX two-phase publication:
```powershell
python -m pytest modules/communication/moltbot_bridge/tests/test_reddog_architect_fix_promotion_publication.py modules/communication/moltbot_bridge/tests/test_reddog_architect_fix_signed_wsp15_work_order_promotion.py modules/communication/moltbot_bridge/tests/test_reddog_architect_proposal_verified_authority.py modules/communication/moltbot_bridge/tests/test_reddog_authoritative_work_state_refresh_runtime.py modules/communication/moltbot_bridge/tests/test_reddog_authority_profile_source_artifact_supply.py modules/communication/moltbot_bridge/tests/test_reddog_execution_valve_environment_supply.py modules/communication/moltbot_bridge/tests/test_reddog_execution_valve_runtime_artifact_locking.py modules/communication/moltbot_bridge/tests/test_reddog_signer_socket_service_config_supply.py modules/communication/moltbot_bridge/tests/test_reddog_resident_control_loop_signing_context.py modules/communication/moltbot_bridge/tests/test_reddog_main_architect_fix_promotion_bootstrap.py modules/communication/moltbot_bridge/tests/test_reddog_wsp62_security_repair_exemptions.py -q
```

Cross-process resident FIX promotion claim:

```bash
python -m pytest modules/communication/moltbot_bridge/tests/test_reddog_agentdb_fix_promotion_claim.py -q
```

The claim suite includes stale-owner fencing, monotonic reclaim revisions,
promotion-receipt completion binding, supplier short-circuiting, and exact
handoff lineage. Artifact-handoff tests separately reject aliased output paths
before either artifact is written.

The publication suite proves the exact fail-closed sequence:
`PREPARED -> immutable inert artifact -> COMMITTED state -> fixed inert cache`.
Recovery never advances PREPARED and never emits signer, queue, claim, shell,
worktree, OpenClaw, or execution-valve authority.
Signer regressions also require the explicitly selected durable authoritative
work state and reject missing state, split-path substitution, marker and
queue/claim stripping, or injected state that differs from the durable payload.
