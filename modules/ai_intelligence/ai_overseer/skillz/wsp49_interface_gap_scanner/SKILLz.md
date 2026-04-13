---
name: wsp49_interface_gap_scanner
description: Discover modules missing INTERFACE.md; emit ranked queue and WSP 11 draft prompt packs (no writes)
version: 1.0.0
author: 0102
created: 2026-04-08
agents: [qwen, gemma, claude]
primary_agent: qwen
intent_type: AUDIT
promotion_state: prototype
pattern_fidelity_threshold: 0.95
category: workflow
evals: []
trigger:
  event: wsp49_hygiene
---
# WSP 49 INTERFACE Gap Scanner

## Purpose

**Prioritize and scaffold** WSP 49 / WSP 11 closure for modules that lack `INTERFACE.md`.

This skill is **read-only**: it does not create or edit repo files. It aligns with `CODE_FIX_CAPABILITY_ANALYSIS.md` — overseer surfaces **classification, queueing, mission framing, and skeleton prompts**; **Codex/0102** finish the actual `INTERFACE.md` and **ModLog** (WSP 22).

## What it does

1. Scans `modules/{WSP3_domain}/*/` for directories without `INTERFACE.md`.
2. **Ranks** by domain order: `infrastructure` → `platform_integration` → … → `blockchain`; **within each domain**, modules with **more** listed context files first, then module name (A–Z) for ties.
3. Collects **context file list** (`README.md`, `src/__init__.py`, `requirements.txt`, … when present).
4. **Lightweight AST hints** from `src/__init__.py` (`__all__` or top-level defs/classes).
5. Emits a **prompt_pack** string per module for paste into Codex/0102.

## What it does not do

- No `INTERFACE.md` writes
- No `ModLog` updates
- Not a substitute for human/API verification (WSP 11)

## Invocation

```bash
# From repo root
python modules/ai_intelligence/ai_overseer/skillz/wsp49_interface_gap_scanner/executor.py --scan

# JSON queue for tooling
python modules/ai_intelligence/ai_overseer/skillz/wsp49_interface_gap_scanner/executor.py --scan --json reports/wsp49_interface_gaps.json

# One markdown prompt per gap
python modules/ai_intelligence/ai_overseer/skillz/wsp49_interface_gap_scanner/executor.py --scan --emit-prompts .wsp49_interface_prompts/
```

## Best next step (operator loop)

1. Run `--scan --emit-prompts`
2. For each ranked item, 0102/Codex drafts `INTERFACE.md` using the prompt + source
3. Validate against WSP 11; update `ModLog.md` (WSP 22)

## WSP

- WSP 3: Domain scan order
- WSP 11: INTERFACE target
- WSP 22: ModLog after real edits (outside this skill)
- WSP 49: Module structure / documentation expectation
- WSP 97: Evidence-first queue; no confabulated API
