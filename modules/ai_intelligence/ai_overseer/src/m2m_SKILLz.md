---
name: m2m_compression_sentinel
description: M2M compression scanner - batched documentation analysis with confidence-based pattern learning
version: 1.0_prototype
author: 0102
created: 2026-04-18
category: workflow
agents: [qwen, gemma]
primary_agent: gemma
intent_type: compression
promotion_state: prototype
pattern_fidelity_threshold: 0.85
evals: []
retirement_date: null
trigger:
  manual
target_file: m2m_compression_sentinel.py
---

> **CF4 file-specific binding**: This `*_SKILLz.md` binds exactly `m2m_compression_sentinel.py` via the `target_file` frontmatter field.

# M2M Compression Sentinel

**Purpose**: Batched scanning of documentation files for M2M compression opportunities using confidence-based scaled response with pattern memory learning.

**Source**: `modules/ai_intelligence/ai_overseer/src/m2m_compression_sentinel.py`
**Lines**: 1557
**Category**: ai

---

## What This Skill Does

Architecture:
- **Gemma**: Pattern detection (prose density, politeness markers)
- **Qwen**: Actual M2M compilation (via M2MCompiler)
- **0102**: Oversight for low-confidence cases

Confidence Levels:
- 0.9+ → Auto-apply (high trust)
- 0.7-0.9 → Stage + auto-promote after TTL (medium trust)
- 0.5-0.7 → Stage + await 0102 review (low trust)
- <0.5 → Flag only, no compile (uncertain)

---

## Execution

```bash
python -c "from modules.ai_intelligence.ai_overseer.src.m2m_compression_sentinel import M2MSentinel; print('Ready')"
```

---

## WRE Connection

- **Trigger**: `manual`
- **Agent**: gemma (pattern detection) + qwen (compilation)
- **Integration**: Scans docs/ and WSP_knowledge/ for compression opportunities

---

## Autonomy Test

Can N compute cycles complete without 012? **YES** - High-confidence compressions auto-apply; medium-confidence auto-promote after TTL.

---

*WSP Compliance*: WSP 99 (M2M Protocol), WSP 77 (Agent Coordination), WSP 48 (Recursive Self-Improvement)
