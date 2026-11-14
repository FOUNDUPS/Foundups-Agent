# Validation and reproduction record

Audit snapshot: `fb58e5279673ef9de30735ccfedc8001c3bb79d6`.

Audit/control checkout: `O:/Foundups-Agent-worktrees/agent-holo-recovery-20260909`.

Artifact directory: `O:/Foundups-Agent-audits/20260909-rsi`.

## Bootstrap

Executed the repository's existing awakening script with bytecode disabled and tracked awakening writes disabled. It exited zero. The strict JSON tracker check returned `is_zen_compliant=true`. These results establish repository bootstrap compliance only.

## Holo incident and recovery

The original query from the feature checkout returned:

```text
error=HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH
ok=false
freshness=UNKNOWN
index_gap_detected=true
authority_repo_head_sha=95f28fff4c057d3796c58b401d3178731cf2dca0
workspace_repo_head_sha=0c81418fe94a7786cfd55f01e138ddc5d510583d
owner_attempts=0
no_holoindex_reindex_performed=true
```

Fetched `origin/main` and created a new detached worktree at its verified SHA. The original branch and local work were not switched or reset. Verified that the dedicated authority was clean and could fast-forward. Invoked the existing controller from the new clean control root:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONUTF8='1'
'{"query":"WRE recursive self improvement completion OpenClaw Hermes","timeout_seconds":1800}' |
  & 'O:/Foundups-Agent/.venv/Scripts/python.exe' -B scripts/reddog_holoindex_postmerge_runtime_once.py
```

This is a historical reproduction command, not an instruction to rerun maintenance automatically. The receiving operator must revalidate the source/owner/target and use existing admission rules.

The controller exited zero with `accepted=true`, `status=COMPLETED`, the exact target and task ID, and both owned runtimes stopped. It delegated indexing to the existing governed maintenance path; the controller receipt's `no_holoindex_reindex_performed_by_controller=true` does not mean no refresh occurred.

Three audit queries then used `scripts/reddog_holoindex_owner_query_once.py` from the clean control checkout. All returned `ok=true`, `freshness=CURRENT`, `index_gap_detected=false`, and exact-main authority. The first included required WRE memory documents; later queries used bridge and FoundUp-agent module bundles. Full returned receipts are retained in the three `holo_*_query.json` files. Reported service latency is not necessarily total cold-start wall time.

The observed generation was `sha256:e6afe7c0c25756e15517b834a31a8b723c0430ae1b1e362848c72dae64cda92a`. Runtime exact closure remained false. No production RSI or retrieval-grade claim follows from these successful queries.

## WRE isolated contract tier

The following documented tier ran from the clean audit checkout. It wrote temporary/test state only under the separate verification directory.

```powershell
$auditTestRoot='O:/Foundups-Agent-audits/20260909-rsi/verification'
$env:TMP=$auditTestRoot
$env:TEMP=$auditTestRoot
$env:FOUNDUPS_DB_PATH=Join-Path $auditTestRoot 'foundups.db'
$env:WRE_PATTERN_MEMORY_DB=Join-Path $auditTestRoot 'pattern_memory.db'
$env:ANTIFAFM_LYRICS_DB=Join-Path $auditTestRoot 'lyrics.db'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONUTF8='1'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
& 'O:/Foundups-Agent/.venv/Scripts/python.exe' -B -m pytest -q `
  -p pytest_asyncio.plugin --import-mode=importlib `
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
  --basetemp "$auditTestRoot/pytest" -o "cache_dir=$auditTestRoot/cache"
```

Result: exit 1; **234 passed, 1 failed, 4 skipped in 45.35 seconds**. No full-suite pass is claimed.

Read-only checks of both production entries independently confirmed the failure belongs to `reddog_operations`. Neither the committed Git blob hash nor LF-normalized bytes match its manifest. `auto_test_registry_audit` passes. See `production_skill_integrity.json`. No manifest regeneration or source modification was performed.

## Canonical test registry

```powershell
python -B modules/infrastructure/wre_core/scripts/generate_test_registry.py --check
```

Result: exit zero; `test_registry=current total=1644 quarantined=269`. This checks the registry projection; it does not execute all tests or clear quarantine.

## Structural/document checks

- Git-tracked file inventory with explicit module, source, test, and exclusion rules.
- Presence checks for core memory documents and optional requirements/memory README files.
- Byte comparison of every numbered framework document with its knowledge mirror.
- Read-only parsing of executable skill and FoundUp registries.
- Scan of roadmap filename candidates for checked/unchecked document claims.
- Exact-file hashes and selected line anchors for critical evidence sources.
- Planning packet dependency, identifier, priority-score, and artifact consistency checks.

Inventory-generated JSON is analytical output, not an implementation or new runtime schema. No production evaluator, worker, promotion, or deployment was invoked by the audit tests.
