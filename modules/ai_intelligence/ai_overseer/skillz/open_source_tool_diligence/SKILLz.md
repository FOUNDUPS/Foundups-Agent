---
name: open_source_tool_diligence
description: Evaluate external open source tools for FoundUps adoption under WSP 97 execution-plane and governance rules
version: 1.0.0
author: 0102
agents: [qwen, gemma]
dependencies: [ai_overseer, holo_index, wsp_framework]
domain: ai_intelligence
intent_type: DECISION
promotion_state: prototype
pattern_fidelity_threshold: 0.95
---

# Open Source Tool Diligence Skillz

## Purpose

Use this skill when 012 or 0102 identifies an external tool, repo, framework, or
agent runtime that may be useful to FoundUps.

This skill does not authorize adoption. It produces a bounded decision:
- `reject`
- `pilot_in_isolation`
- `integrate_via_wrapper`
- `integrate_directly` (rare)

## When To Use

Use this skill when all of the following are true:
1. The tool is external to the FoundUps repo.
2. The tool meaningfully overlaps with Claw, WRE, MCP, PQN, HoloIndex, or DAE execution.
3. The tool could change how 0102 performs research, coding, orchestration, or system control.

## Mandatory WSP 97 Sequence

1. **Understand**
   - Identify what the tool actually does.
   - Separate repo marketing from execution reality.
2. **Retrieve**
   - Gather evidence from:
     - upstream README/docs
     - repo structure
     - license status
     - current FoundUps module surfaces via HoloIndex
3. **Resolve execution plane**
   - Decide whether the tool belongs in:
     - OpenClaw control plane
     - WRE execution plane
     - MCP wrapper plane
     - isolated external worker plane
     - docs only / no adoption
4. **Coordinate response**
   - Score the candidate with WSP 15 and CTO diligence factors.
   - Emit a clear recommendation and first safe step.

## Evaluation Questions

1. What problem does the tool solve better than existing FoundUps modules?
2. Is it a control-plane tool, execution tool, or isolated worker?
3. Does it assume unconstrained repo mutation, direct internet access, or autonomous git push?
4. Does it require GPU, cloud credentials, or proprietary APIs?
5. Is the license clearly present and compatible with intended use?
6. Can it be sandboxed without weakening FoundUps governance?
7. What artifacts should flow back into HoloIndex/WRE if adopted?

## Guardrails

1. Never recommend direct integration into `main.py` startup unless the tool is a readiness dependency.
2. Never recommend direct mutation of the FoundUps monorepo by an unwrapped external agent loop.
3. If license status is unclear, fail closed to `pilot_in_isolation` or `reject`.
4. Default placement for autonomous external research runtimes is:
   - isolated worker
   - broker-launched
   - artifact return only
5. MCP wrapping is optional and comes after isolation, not before it.

## Output Contract

```json
{
  "status": "OK|FAIL_CLOSED",
  "tool_name": "string",
  "decision": "reject|pilot_in_isolation|integrate_via_wrapper|integrate_directly",
  "recommended_plane": "openclaw|wre|mcp|external_worker|docs_only",
  "wsp15": {
    "complexity": 0,
    "importance": 0,
    "deferability": 0,
    "impact": 0,
    "total": 0
  },
  "evidence_refs": [],
  "risks": [],
  "constraints": [],
  "first_safe_step": "",
  "not_now_reasons": []
}
```

## FoundUps-Specific Heuristic

- If the tool is optimized for autonomous research iteration inside a self-contained ML repo,
  it is usually a **PQN/external research worker** candidate, not a Claw replacement.
- If the tool assumes it owns the git loop, it must stay behind 0102 governance and isolation.
