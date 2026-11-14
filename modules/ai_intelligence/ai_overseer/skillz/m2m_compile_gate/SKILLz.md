---
name: m2m_compile_gate
description: Stage M2M reference candidates with structural and YAML checks; fidelity requires separate evaluation
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

Stage M2M reference-document candidates. The sentinel creates scratch staging,
backup and memory directories; the shim also writes its existing JSONL outcome
record. This operation does not promote to live docs. Use a disposable replica
for an experiment. Executable Skillz and boot prompts must remain verbatim.

## Inputs

- `source_path`: repository-relative markdown path
- `use_qwen`: `true|false` (default: `false` for deterministic baseline)
- `qwen_model`: optional model override

## Implemented checks and caller responsibilities

The direct sentinel requires an existing source, rejects detected boot prompts
and Skillz, and validates the M2M header/section structure and encoding. The
`execute_m2m_skill` shim additionally parses YAML; on YAML failure it reports
`FAIL` and removes the staged file. Direct compilation does not perform that
YAML check. Scan exclusions are not a path-admission gate for direct calls.

The caller must select an allowed repository-relative reference Markdown file,
excluding changelogs and `.m2m/`, before calling the prototype. No authenticated
path or work-order admission is established by these helpers.

Required-reference retention, section coverage, reduction bounds and semantic
fidelity are **not implemented acceptance checks**. Before using candidate
context, fix preservation requirements from the original source and reject
missing instructions, negations, authority boundaries and dependencies. YAML
validity and embedding similarity cannot replace this evaluation. The 0.95
frontmatter value is declarative metadata, not an executed fidelity threshold.

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

The shim checks YAML with `yaml.safe_load`. When using the direct sentinel
example above, validate YAML separately before considering the staged file.
Record measured bytes/lines separately from actual model token usage. Evaluate
the previously fixed preservation requirements against the source; reject the
candidate on loss. A size reduction is not a fidelity pass or RSI benefit.

The [2026-09-13 counterexample](../../../../../docs/operations/RSI_SWARM_DISPATCH.md#baseline-and-context-preservation-checkpoint--2026-09-13)
shows valid YAML passing the shim while dropping worker/verifier independence.

### Step 4: Record Outcome

Store run metadata in:
- `modules/ai_intelligence/ai_overseer/memory/m2m_compile_gate.jsonl`

Result payload fields:
- `source_path`
- `staged_path`
- `compilation_method`
- `reduction_percent`
- `gate_status` (`PASS|FAIL`)
- `gate_error` (YAML failure) or `error` (pre-stage failure)

## Output Contract

```json
{
  "success": true,
  "source_path": "modules/.../INTERFACE.md",
  "staged_path": ".m2m/staged/.../INTERFACE_M2M.yaml",
  "compilation_method": "deterministic|qwen:<model>",
  "reduction_percent": 72.4,
  "gate_status": "PASS|FAIL",
  "gate_error": null
}
```

This is the nested shim result; the outer `status` is `OK|FAIL`. A pre-stage
failure may omit `staged_path` and `gate_status`. The direct sentinel result
does not include the shim's gate fields. None of these fields certifies
preservation, acceptance, promotion or verified learning.

## WSP Chain

- WSP 95: SKILLz wardrobe integration
- WSP 99: M2M protocol
- WSP 50: pre-action verification
- WSP 11: interface fidelity
- WSP 22: change traceability
- WSP 87: memory retrieval integrity
