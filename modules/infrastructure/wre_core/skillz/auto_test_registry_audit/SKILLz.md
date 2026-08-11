---
name: auto_test_registry_audit
description: Verify or regenerate the canonical module-owned Python test registry
version: 2.0
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
metrics:
  pattern_fidelity_scoring:
    enabled: true
category: workflow
evals:
  - canonical_bytes_match_git_projection
  - every_tracked_python_test_has_one_owner
  - quarantined_programs_remain_visible
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

## Boundaries

- Do not run `pytest .`.
- Do not delete or silently ignore a quarantined file.
- Do not treat local shard evidence as external execution authority.
- Do not mutate HoloIndex during verification. Post-merge indexing belongs to
  the governed HoloIndex authority transaction.
- A failed shard does not invalidate or erase other shard reports.
