# wre_core Test Suite

**Coverage claim:** focused contract coverage only
**Framework:** pytest
**Last verified:** 2026-08-27

## Isolation gate

Every WRE test command must isolate temporary files and both database paths.
Do not run execution tests against the default production databases.

```powershell
$root = 'O:\pytest_tmp\reddog_wre_truth'
New-Item -ItemType Directory -Force -Path $root | Out-Null
$env:TMP = $root
$env:TEMP = $root
$env:FOUNDUPS_DB_PATH = Join-Path $root 'foundups.db'
$env:WRE_PATTERN_MEMORY_DB = Join-Path $root 'pattern_memory.db'
$env:ANTIFAFM_LYRICS_DB = Join-Path $root 'lyrics.db'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
```

Use a unique child directory for concurrent workers.

## Bounded Git I/O tier

`test_wre_test_registry_differential_plan_runtime.py` includes the bounded-I/O
primitive used by RedDog's inert pinned-Git batch proof. Six focused cases cover
stdout overflow, binary stdin round-trip, the 8 MiB pre-spawn ceiling, early
child exit/broken pipe, timeout cleanup with no retained named I/O threads, and
concurrent output overflow while stdin is blocked. The test interpreter and
temporary root must remain on O:. The helpers do not mutate Git or authenticate
an executable/repository.

## Execution-truth tier

```powershell
$base = Join-Path $root 'pytest'
$cache = Join-Path $root 'cache'
python -m pytest -q -p pytest_asyncio.plugin --import-mode=importlib `
  modules/infrastructure/wre_core/tests/test_wre_execution_truth.py `
  modules/infrastructure/wre_core/tests/test_wre_runtime_admission_truth.py `
  modules/infrastructure/wre_core/tests/test_wre_telemetry_truth.py `
  modules/infrastructure/wre_core/tests/test_wre_skills_loader_hygiene.py `
  modules/infrastructure/wre_core/tests/test_skill_manifest_guard.py `
  modules/infrastructure/wre_core/tests/test_pattern_memory.py `
  modules/infrastructure/wre_core/tests/test_qwen_inference_wiring.py `
  modules/infrastructure/wre_core/tests/test_skill_evolution_continuity.py `
  modules/infrastructure/wre_core/tests/test_foundup_route_wsp62_exemptions.py `
  modules/infrastructure/wre_core/wre_master_orchestrator/tests/test_wre_master_orchestrator.py `
  modules/infrastructure/wre_core/wre_gateway/tests/test_dae_gateway_policyflags_guards.py `
  modules/infrastructure/wre_core/recursive_improvement/tests/test_learning.py `
  modules/communication/moltbot_bridge/tests/test_skill_safety_guard.py `
  modules/communication/moltbot_bridge/tests/test_openclaw_skill_evolution.py `
  --basetemp $base -o "cache_dir=$cache"
```

Exact current-tree result on 2026-08-26: `235 passed, 4 platform-limited
link/reparse skips in 29.38s`.

Importlib mode prevents unrelated directories named `tests` from colliding in
one combined invocation; it does not relax collection or execution assertions.

This tier must not load a local model, call a provider, write production
PatternMemory/AgentDB state, dispatch external work, mutate Git, or reindex
HoloIndex.

It proves only the named contracts:

- production Skillz admission and hygiene;
- digest-bound loader cache;
- manifest/scanner and adjacent executor binding;
- mutation-during-scan and mutation-before-dispatch rejection;
- typed effect-result validation and redacted failures;
- proposal-only local inference;
- PatternMemory execution truth;
- ReAct acceptance truth;
- blocked legacy CodeAct/direct-Holo authority boundaries;
- WSP gates followed by fail-closed legacy plugin dispatch;
- recursive removal of untrusted nested MLE effect/compliance claims;
- unmeasured gateway/plugin/monitor/recursive-improvement token telemetry;
- fail-closed recursive-improvement application compatibility;
- stoppable opt-in recursive state persistence and truthful shutdown status;
- WSP 62 debt reduction and WSP 95 mirror parity.

## Broader suite

After the focused tier passes, expand to the module suite with the same
isolation environment:

```powershell
python -m pytest -q modules/infrastructure/wre_core/tests `
  --basetemp (Join-Path $root 'all-pytest') `
  -o "cache_dir=$(Join-Path $root 'all-cache')"
```

The suite contains a large sharded/exhaustive contract surface. A focused pass
does not substitute for full-suite evidence, and an interrupted full run must
be reported as incomplete rather than passing.

## FMAS health-admission tier

```powershell
python -m pytest -q `
  tools/modular_audit/tests/test_modular_audit.py `
  tools/modular_audit/tests/test_fmas_mode2.py `
  modules/infrastructure/wre_core/tests/test_fmas_health_triage.py `
  modules/infrastructure/wre_core/tests/test_fmas_improvement_bridge.py `
  modules/infrastructure/wre_core/tests/test_improvement_job_contract.py `
  modules/infrastructure/wre_core/tests/test_security_analysis_assistant.py `
  modules/infrastructure/wre_core/tests/test_reddog_direction.py
```

Exact O:-resident result on 2026-08-27: `235 passed in 5.87s`. This proves tracked
inventory, authority and receipt binding, scope rejection, WSP 62 quarantine,
deterministic proposal admission, and advisory-only RedDog direction. It does
not prove a clean real-candidate positive run, model selection, worker dispatch,
promotion, or production RSI.

## Test inventory

- `test_wre_execution_truth.py`: false-success, result evidence, ReAct, and
  bounded executor contracts.
- `test_wre_runtime_admission_truth.py`: runtime admission, scan fingerprints,
  A/B binding, trigger provenance, and WSP 95 parity.
- `test_wre_telemetry_truth.py`: no fabricated token savings/reduction and no
  unexecuted monitor, gateway, or recursive-improvement success.
- `test_wre_skills_loader_hygiene.py`: registry paths, metadata, retirement,
  cache, and production entries.
- `test_skill_manifest_guard.py`: Skillz/executor hashes and signatures.
- `test_pattern_memory.py`: outcome and non-production candidate storage.
- `test_qwen_inference_wiring.py`: isolated proposal/result-shape wiring.
- `test_foundup_route_wsp62_exemptions.py`: bounded inherited debt.
- `test_fmas_health_triage.py`: exact-head producer lineage and dispositions.
- `test_fmas_improvement_bridge.py`: normalized parsing and direct WSP 62 block.
- `test_improvement_job_contract.py`: path confinement and dry-run job contract.
- `test_reddog_direction.py`: advisory ordering with zero readiness authority.
- `wre_master_orchestrator/tests/test_wre_master_orchestrator.py`: public
  coordination behavior with injected effect evidence.
- `wre_gateway/tests/test_dae_gateway_policyflags_guards.py`: envelope boundary
  and degraded-route guards.
- `recursive_improvement/tests/test_learning.py`: proposal learning smoke test.

See [TestModLog.md](TestModLog.md) for the append-only test history.
