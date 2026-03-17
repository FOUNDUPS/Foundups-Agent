---
name: m2m_compile_gate
description: Compile markdown documentation into staged M2M artifacts with strict gating and fidelity checks
version: 1.0.0
author: 0102
agents: [qwen, gemma]
dependencies: [ai_overseer, holo_index, wre_core]
domain: ai_intelligence
intent_type: DECISION
promotion_state: prototype
pattern_fidelity_threshold: 0.95
category: workflow
evals: []
---
# M2M Compile Gate Skill

## Purpose

Run safe M2M compilation for documentation. This skill only writes to `.m2m/staged/` and does not promote to live docs.

## Inputs

- `source_path`: repository-relative markdown path
- `use_qwen`: `true|false` (default: `false` for deterministic baseline)
- `qwen_model`: optional model override

## Guardrails

1. Source must exist and be a markdown document.
2. Source must not be in `.m2m/` and must not be a changelog file.
3. Compiled output must parse as valid YAML.
4. Compiled output must keep critical signal:
   - WSP references
   - file path references
   - section coverage above configured threshold
5. On gate failure, mark result as `FAIL` and do not keep staged artifact.

## Execution Steps

### Step 1: Preflight

```python
from pathlib import Path
from modules.ai_intelligence.ai_overseer.src.m2m_compression_sentinel import M2MCompressionSentinel

repo = Path(".").resolve()
sentinel = M2MCompressionSentinel(repo)
```

### Step 2: Compile

```python
result = sentinel.compile_to_staged(
    file_path=source_path,
    use_qwen=use_qwen,
    qwen_model=qwen_model,
)
```

### Step 3: Validate Artifact

Checks:
- YAML parse succeeds (`yaml.safe_load`)
- `reduction_percent` is within expected bound (target 40-85%)
- required references are retained

### Step 4: Record Outcome

Store run metadata in:
- `modules/ai_intelligence/ai_overseer/memory/m2m_compile_gate.jsonl`

Result payload fields:
- `source_path`
- `staged_path`
- `compilation_method`
- `reduction_percent`
- `gate_status` (`PASS|FAIL`)
- `failure_reason` (if any)

## Output Contract

```json
{
  "status": "OK|FAIL",
  "source_path": "modules/.../INTERFACE.md",
  "staged_path": ".m2m/staged/.../INTERFACE_M2M.yaml",
  "compilation_method": "deterministic|qwen:<model>",
  "reduction_percent": 72.4,
  "gate_status": "PASS|FAIL",
  "failure_reason": null
}
```

## WSP Chain

- WSP 95: SKILLz wardrobe integration
- WSP 99: M2M protocol
- WSP 50: pre-action verification
- WSP 11: interface fidelity
- WSP 22: change traceability
- WSP 87: memory retrieval integrity
