---
name: autonomous_slice_worker
description: Window-agnostic spec for the self-orchestrating AUTHOR -> SENTINEL -> LAND slice loop; a discoverable verifier role that observes FAM, emits a receipt, and owns no execution or merge authority.
version: 0.1_prototype
author: 0102
created: 2026-06-13
agents: [qwen, gemma]
primary_agent: qwen
intent_type: ORCHESTRATION
promotion_state: prototype
pattern_fidelity_threshold: 0.90
category: workflow
retirement_date: null
trigger:
  event: slice_dispatch
  cadence: on_demand
domain: infrastructure/wre_core
wsp_chain: [WSP_50, WSP_54, WSP_57, WSP_64, WSP_77, WSP_91, WSP_97]
evals:
  - name: docs_decision_only_self_lands
    input: "Slice {risk: DOCS_DECISION_ONLY, scope_files: [docs/audits/x.md, ModLog.md]} authored and SENTINEL-confirmed READY."
    expected: "PHASE 3 LAND self-lands the docs slice and emits VERIFICATION_RECORDED; no external gate is required; status=LANDED."
  - name: spine_code_escalates_not_hangs
    input: "Slice {risk: SPINE_CODE, scope_files: [modules/.../src/foo.py]} authored and SENTINEL-confirmed READY."
    expected: "PHASE 3 LAND stops at MERGE_READY for the external gate (async sovereign valve, not a synchronous block) and emits VERIFICATION_RECORDED; status=MERGE_READY; the loop does not hang."
  - name: sentinel_refutes_returns
    input: "Author draft that imports a queue mutator (drain / remove_jobs_by_id / get_job_queue) or breaks scope."
    expected: "PHASE 2 SENTINEL refutes, returns NOT_READY with the offending cite; PHASE 3 does not land; the slice returns to AUTHOR."
---
# Autonomous Slice Worker (SentinelVerifier role)

**Status**: prototype spec (0.1). This SKILLz is a LOADABLE TEMPLATE only. It defines the role; it is
NOT invoked in the live loop yet. No executor logic, no runtime wiring, no queue access, no FAM write,
and no external egress are implemented by this artifact.

**Architectural basis**: docs/audits/architecture/WRE_AUTONOMOUS_VERIFICATION_LOOP_AUDIT_PHASE1.md
ratifies the verifier-as-non-orchestrator: it reads FAM, validates evidence, emits a receipt, is
forbidden from the FoundUpJob queue mutators, and owns neither execution nor merge authority.

## Purpose

Run one slice end-to-end as a self-orchestrating loop -- AUTHOR drafts, an INDEPENDENT SENTINEL
adversarially validates, and LAND calibrates the outcome -- so the slice flow is driven by the system,
not performed manually by the operator. The roles are role-and-lane labels; this skill never encodes a
specific operator session id.

## Input Contract

```json
{
  "slice_name": "string",
  "type": "string",
  "risk": "DOCS_DECISION_ONLY | SPINE_CODE",
  "base_sha": "string (current origin/main; re-pin + re-verify if advanced)",
  "scope_files": ["repo-relative path", "..."],
  "lane": "A-G (architect-assigned)",
  "window": "operator session id (optional, passthrough only; never a role)"
}
```

## Execution (ROLE phases -- never operator-window numbers)

### PHASE 0 -- GROUND
Re-pin base_sha against origin/main and re-verify; run HoloIndex discovery for the target area
(discovery only, never proof); read the load-bearing files directly at base and cite file:line.

### PHASE 1 -- AUTHOR
Work in an isolated git worktree (never move shared HEAD). Author strictly within scope_files; apply
scope guards; keep artifacts ASCII-clean. Produce the deliverable + a ModLog entry only.

### PHASE 2 -- SENTINEL (separation of duties)
An INDEPENDENT agent (a different lane than the AUTHOR) adversarially refutes the draft: re-derive
every load-bearing cite at base, confirm file scope, confirm tests/checks, confirm WSP_97 row parity,
and confirm the non-orchestration constraint below. An optional cross-vendor advisory panel plus a
local Qwen/Gemma fallback may ADVISE this lane, but it is ADVISORY-NOT-AUTHORITY: the deterministic
checks (scope, ASCII, grep denylist, WSP_97 parity, tests) are the authority; no external model gates
an outcome. The SENTINEL verdict is the slice's Internal Review.

### PHASE 3 -- LAND (calibrated)
- DOCS_DECISION_ONLY: self-land after the SENTINEL returns READY.
- SPINE_CODE: stop at MERGE_READY and defer to the external gate (an independent reviewer, separate
  from the internal SENTINEL). This is an asynchronous sovereign valve, not a synchronous human block.
- Always emit a FAM VERIFICATION_RECORDED receipt for the outcome (substrate exists; wiring deferred).

## Output Contract (PatternMemory-storable)

```json
{
  "role": "AUTHOR | SENTINEL",
  "lane": "A-G",
  "window": "operator session id or null",
  "slice_name": "string",
  "pr": "url",
  "head_sha": "string",
  "sentinel_verdict": "READY | NOT_READY",
  "ci": "string",
  "status": "LANDED | MERGE_READY",
  "verification_recorded": true
}
```

This maps onto PatternMemory.SkillOutcome (pattern_memory.py): execution_id, skill_name, agent,
input_context, output_result (this JSON), success, pattern_fidelity, outcome_quality.

## Non-orchestration constraint (load-bearing)

The SENTINEL/verifier role MUST NEVER import or call the FoundUpJob queue mutators -- specifically
get_job_queue, remove_jobs_by_id, or drain. The verifier reads FAM (an append-only event log with no
queue primitives) plus the worker evidence, and emits a receipt; it owns no execution or merge
authority. A future executor MUST enforce this as an AST import-denylist (the same pattern used by the
manifest validator and the module-path resolver). A role that observes FAM and emits a receipt cannot
dispatch work, and is therefore categorically NOT the forbidden second brain (a competing orchestrator
that owns and drives the queue).

## Verifier home

The SENTINEL is a STANDALONE SentinelVerifier role that REUSES the AI Overseer's Qwen/Gemma facade. It
is deliberately NOT coupled into the AIIntelligenceOverseer coordinator role, to keep verification
separate from orchestration (separation of concerns and a clean AST denylist surface).

## WSP Compliance

- WSP 50: pre-action verification (PHASE 0 GROUND).
- WSP 54: agent duties. The autonomous-verifier duty is a recommended ENHANCEMENT to WSP 54 (per WSP
  64, enhance-before-create); it is NOT a new WSP and is NOT edited by this artifact.
- WSP 57: naming coherence.
- WSP 64: violation prevention / enhance-before-create.
- WSP 77: agent coordination (Qwen orchestrates, Gemma validates).
- WSP 91: observability / heartbeat (FAM receipts).
- WSP 97: truth boundary (evidence-backed, no overclaim; ADVISORY-NOT-AUTHORITY).

## WRE Connection

- Discoverable: this SKILLz.md is indexed by the HoloIndex SKILLz scan (filesystem discovery; no
  registry entry required, matching the precedent of registry-free SKILLz.md skills).
- Triggerable: trigger.event = slice_dispatch, cadence on_demand.
- Executable: primary_agent = qwen (orchestrates), gemma validates.
- Remembered: outcomes stored via PatternMemory.SkillOutcome {role, lane, window, verdict, timestamp}.
- Receipts: emits FAM VERIFICATION_RECORDED (substrate exists; NOT wired by this slice).

## Autonomy Test (no-hang)

Can N cycles complete without the operator? YES.
- DOCS_DECISION_ONLY slices self-land.
- SPINE_CODE slices complete authoring and emit MERGE_READY through the asynchronous external gate; the
  loop never blocks synchronously on a human prompt. Escalation means "stop at MERGE_READY", not "wait
  inline".

## Merge serialization

Only one LAND token may hold the merge path at a time. Because LAND touches the root ModLog and expects
a fast-forward-only merge, concurrent LANDs would collide; LAND must serialize (single in-flight LAND)
to avoid a ModLog / ff-only conflict.
