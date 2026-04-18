---
name: ai_overseer
description: MCP coordinator for WSP 77 agent orchestration (Qwen Partner + 0102 Principal + Gemma Associate)
version: 1.0_prototype
author: 0102
created: 2026-04-18
category: workflow
agents: [qwen, gemma]
primary_agent: qwen
intent_type: coordination
promotion_state: prototype
pattern_fidelity_threshold: 0.85
evals: []
retirement_date: null
trigger:
  manual
---

# AI Overseer

**Purpose**: MCP coordinator that oversees Holo Qwen/Gemma for autonomous task orchestration following WSP 77 agent coordination protocol.

**Source**: `modules/ai_intelligence/ai_overseer/src/ai_overseer.py`
**Lines**: 3584
**Category**: ai

---

## What This Skill Does

Replaces deprecated 6-agent system with WSP 77 coordination:
- **Phase 1 (Gemma Associate)**: Fast pattern matching & binary classification
- **Phase 2 (Qwen Partner)**: Strategic planning & coordination
- **Phase 3 (0102 Principal)**: Oversight, plan generation, supervision
- **Phase 4 (Learning)**: Pattern storage for recursive self-improvement

Integrates MetricsAppender, PatchExecutor, PatternMemory for collective learning.

---

## Execution

```bash
python modules/ai_intelligence/ai_overseer/src/ai_overseer.py --help
```

---

## WRE Connection

- **Trigger**: `manual`
- **Agent**: qwen
- **Integration**: Uses AutonomousRefactoringOrchestrator from holo_index

---

## Autonomy Test

Can N compute cycles complete without 012? **YES** - Gemma binary classification + Qwen planning can execute autonomously with pattern memory feedback.

---

*WSP Compliance*: WSP 77 (Agent Coordination), WSP 54 (Role Assignment), WSP 96 (MCP Governance)
