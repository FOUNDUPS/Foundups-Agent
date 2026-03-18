---
name: m2m_stage_promote_safe
description: Promote staged M2M artifacts to live docs with deterministic target mapping, backups, and rollback discipline
version: 1.0.0
author: 0102
agents: [qwen, gemma]
dependencies: [ai_overseer, wre_core]
domain: ai_intelligence
intent_type: DECISION
promotion_state: prototype
pattern_fidelity_threshold: 0.97
category: workflow
evals: []
---
# M2M Stage Promote Safe Skill

## Purpose

Move approved staged M2M artifacts into live documentation with explicit target control and auditable rollback.

## Inputs

- `staged_path`: repository-relative staged artifact path
- `target_path`: required explicit live target path
- `create_backup`: default `true`
- `rollback_only`: optional `true` to run rollback path

## Guardrails

1. Promotion requires explicit `target_path` (no glob inference).
2. Backup must be created before write.
3. Promotion history must be appended.
4. Post-write verification must pass:
   - target exists
   - target content starts with `# M2M v1.0`
5. Rollback path must verify backup selection and result integrity.

## Execution Steps

### Step 1: Initialize

```python
from pathlib import Path
from modules.ai_intelligence.ai_overseer.src.m2m_compression_sentinel import M2MCompressionSentinel

repo = Path(".").resolve()
sentinel = M2MCompressionSentinel(repo)
```

### Step 2: Promote

```python
result = sentinel.promote_staged(
    staged_path=staged_path,
    target_path=target_path,
    create_backup=create_backup,
)
```

### Step 3: Verify and Record

- Verify promotion result is `success=true`
- Verify target content marker and backup path presence
- Record action in:
  - `modules/ai_intelligence/ai_overseer/memory/m2m_promotion_history.jsonl`
  - `modules/ai_intelligence/ai_overseer/memory/m2m_stage_promote_safe.jsonl`

### Step 4: Rollback (if requested)

```python
rollback_result = sentinel.rollback(target_path=target_path)
```

## Output Contract

```json
{
  "status": "OK|FAIL",
  "action": "promote|rollback",
  "staged_path": ".m2m/staged/.../FILE_M2M.yaml",
  "target_path": "modules/.../FILE.md",
  "backup_path": ".m2m/backups/<timestamp>_FILE.md",
  "message": "Promoted M2M to FILE.md"
}
```

## WSP Chain

- WSP 95: SKILLz wardrobe integration
- WSP 99: staged M2M flow
- WSP 50: pre-action verification
- WSP 22: promotion/rollback audit log
- WSP 11: target contract integrity
