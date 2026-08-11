---
name: auto_test_registry_audit
description: Verify, regenerate, or project the canonical module-owned Python test registry
version: 2.2
author: 0102
agents: [qwen, gemma]
primary_agent: qwen
intent_type: TELEMETRY
promotion_state: production
pattern_fidelity_threshold: 0.95
dependencies:
  scripts:
    - path: modules/infrastructure/wre_core/scripts/generate_test_registry.py
      purpose: Deterministic Git-tracked test registry projection
    - path: modules/infrastructure/wre_core/src/wre_test_registry_differential_plan_runtime.py
      purpose: Exact-SHA bounded scope-projection entrypoint
metrics:
  pattern_fidelity_scoring:
    enabled: true
category: workflow
evals:
  - canonical_bytes_match_git_projection
  - every_tracked_python_test_has_one_owner
  - quarantined_programs_remain_visible
  - exact_sha_shard_projection_is_bounded_and_non_executing
---
# Auto Test Registry Audit

Maintain the single test source of truth at
`WSP_knowledge/WSP_Test_Registry.json` without broad pytest discovery.

## Verify

Run from the repository root:

```text
python modules/infrastructure/wre_core/scripts/generate_test_registry.py --check
```

The command passes only when the checked-in ASCII registry is byte-identical to
the deterministic projection of Git-tracked `test_*.py` files.

## Regenerate

Use `--write` only in a bounded registry-maintenance worktree:

```text
python modules/infrastructure/wre_core/scripts/generate_test_registry.py --write
python modules/infrastructure/wre_core/scripts/generate_test_registry.py --check
```

The generator assigns every file exactly one owner, suite class, shard, timeout,
and quarantine status. Unit and integration files may be automatically
collected. Manual, operational, archived, malformed, or process-mutating files
remain registered but cannot enter automatic pytest collection.
Module-scope external API client construction, including Google API clients,
is operational and quarantined even when imported through module-executed
control-flow. Pure authentication request construction remains collectable.

## Differential Scope Projection

For a bounded changed-path work order, use the registered WRE planning API,
not raw pytest discovery. The projection verifies the exact Git diff, regenerates
the registry independently for parent and candidate, resolves each SHA's
explicit module shards, validates recognized dependency/config parity, and
emits bounded batches. It rejects stale or forged registries, changed
quarantined tests, path substitution, dependency drift, oversized source, and
exceeded limits. It creates the existing `wre_test_impact_plan.v1`; it does not
define another impact-plan schema. WSP_15, runner, environment, selection, and
lineage bindings are mandatory inputs. Stale dependency
or HoloIndex evidence and protected/release/health work escalate to SYSTEMIC.
Cross-owner renames expose both source and destination paths.

The Phase 1 result is a scope projection only. It does not import tests or invoke pytest.
Execution remains blocked until an independently authenticated OS-isolated
runner consumes the canonical impact plan and projected shards.

## Boundaries

- Do not run `pytest .`.
- Do not delete or silently ignore a quarantined file.
- Do not treat a local shard plan as execution or verification evidence.
- Do not mutate HoloIndex during verification. Post-merge indexing belongs to
  the governed HoloIndex authority transaction.
- Do not execute candidate tests under the host principal.
