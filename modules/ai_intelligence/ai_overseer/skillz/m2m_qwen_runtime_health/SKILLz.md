---
name: m2m_qwen_runtime_health
description: Verify Qwen runtime health for M2M compilation and detect fallback or method-label drift
version: 1.0.0
author: 0102
agents: [qwen, gemma]
dependencies: [ai_overseer, holo_index]
domain: ai_intelligence
intent_type: TELEMETRY
promotion_state: prototype
pattern_fidelity_threshold: 0.96
category: workflow
evals: []
---
# M2M Qwen Runtime Health Skill

## Purpose

Validate that Qwen-backed M2M compilation is truly operational and that runtime telemetry correctly reports which compilation path was used.

## Inputs

- `source_path`: repository-relative markdown file for probe
- `qwen_model`: optional model override
- `repeat`: number of probe runs (default `3`)

## Guardrails

1. Must test both deterministic and Qwen-enabled compile modes.
2. Must detect mismatch between claimed `compilation_method` and actual path used.
3. Must report any silent fallback behavior.
4. Must not promote artifacts.

## Execution Steps

### Step 1: Runtime Probes

```python
from modules.ai_intelligence.ai_overseer.src.m2m_compression_sentinel import (
    _init_qwen_llm,
    _init_qwen_client,
    M2MCompressionSentinel,
)
```

Run:
- `_init_qwen_llm()`
- `_init_qwen_client()`
- deterministic compile baseline
- `use_qwen=True` compile probe

### Step 2: Consistency Checks

Evaluate:
- initialization success/failure
- deterministic latency vs qwen latency
- output presence from `_qwen_transform_to_m2m`
- method-label consistency

### Step 3: Persist Health Report

Write report:
- `modules/ai_intelligence/ai_overseer/memory/m2m_qwen_runtime_health_latest.json`
- append run history to:
  `modules/ai_intelligence/ai_overseer/memory/m2m_qwen_runtime_health.jsonl`

## Output Contract

```json
{
  "status": "OK|FAIL",
  "qwen_llm_ready": true,
  "qwen_client_ready": true,
  "deterministic_latency_ms": 4.1,
  "qwen_latency_ms": 27820.3,
  "qwen_output_present": false,
  "method_label_consistent": false,
  "issues": ["qwen_output_missing", "method_label_drift"]
}
```

## WSP Chain

- WSP 95: SKILLz wardrobe integration
- WSP 99: M2M runtime governance
- WSP 50: verify before mutation
- WSP 60: signal quality and observability
- WSP 22: persistent health audit trail
