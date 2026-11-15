---
name: strategic_diligence_gate
description: Generic CTO-grade decision gate for high-impact architecture, product, security, and operations choices
version: 1.0.1
author: 0102
agents: [qwen, gemma]
dependencies: [ai_overseer, holo_index, wsp_framework]
domain: ai_intelligence
intent_type: DECISION
promotion_state: prototype
pattern_fidelity_threshold: 0.95
category: workflow
evals: []
---
# Strategic Diligence Gate Skill

## Purpose

Use a consistent, evidence-based decision process for high-blast-radius choices.
This skill enforces diligence structure. It does not hard-code the conclusion.

## When To Use

Use this skill when one or more are true:
1. Change is hard to reverse after deployment.
2. Change crosses multiple modules or teams.
3. Change affects security, trust, economics, or governance.
4. Change impacts external messaging (README, LitePaper, positioning).
5. Change can create long-term operational burden.

## When Not To Use

Do not use for low-risk local fixes (lint, small bugfix, typo, isolated test update).

## Required Inputs

- `decision_prompt`: one-sentence decision to make
- `scope_paths`: list of relevant module/doc paths
- `time_horizon`: `short|medium|long`
- `constraints`: explicit constraints (security, budget, timeline, compatibility)
- `risk_tier`: `low|medium|high|critical`

Optional:
- `candidate_options`: pre-proposed options
- `must_keep`: invariants that cannot change

## Model Tier Policy

OpenClaw is an execution/control plane, not a model.  
Model selection should be risk-tiered:

1. `low` (P3/P4): local Qwen or Gemma is sufficient.
2. `medium` (P2): Qwen primary + Gemma cross-check required.
3. `high` (P1): frontier model review required (via AI Gateway), plus Qwen draft.
4. `critical` (P0): frontier model review + explicit 0102 approval gate.

Do not allow Qwen-only final decisions for `high` or `critical` risk tiers.

## Execution Protocol

### Step 1: Frame The Decision

Create a clear decision statement:
- "Decide whether to X under constraints Y to achieve outcome Z."

If framing is ambiguous, fail closed and request clarification.

### Step 2: Retrieve Evidence (Holo First)

Run targeted Holo retrieval before proposing action:
- existing implementation
- related WSP protocol constraints
- prior ModLog decisions
- test and failure evidence

Mark each claim as:
- `evidence`
- `inference`
- `assumption`

### Step 2A: Reconcile FoundUp Requests With The Roadmap

For new or changed FoundUp product/build requirements, read the current root
roadmap, the affected FoundUp's ROADMAP/INTERFACE/intake, the shared platform
owner's corresponding documents, and related open PRs before selecting work.
Follow `modules/foundups/docs/FOUNDUP_ONBOARDING_PROTOCOL_PHASE1.md`; an existing
FoundUp feature update must not create a second genesis, shell, or skill owner.

Record in the owning roadmap and existing work record:

- the exact request and source, affected owner, current implementation revision,
  and proposed acceptance change;
- whether the request fits the active PoC, changes its acceptance, belongs to a
  later stage, or conflicts with an existing contract;
- which earlier decision is superseded, while preserving unrelated requirements;
- the simplest reusable layer, its dependencies, tests, and rollback boundary.

WSP 15 determines priority/economy. WSP 30 governs PoC -> Prototype -> MVP build
staging. WSP 97 governs evidence, execution and completion. A score is not a
stage promotion, deployment permission, or proof that the requested layout works.

For shared-Mall consumers such as HPC, different desktop and phone presentations
must reuse the same catalog, tile/player/state owners and preserve other FoundUps.
Bind independent desktop, phone and breakpoint-transition acceptance before
changing shared layout or gestures. A mobile-only pass cannot certify desktop.

Keep HPC decisions, test evidence and follow-ups in the owning GitHub
roadmap, interface, ModLog or shared Mall incident. In HPC playback work,
“mosh pit” refers to the video grid. Reserve the Google Docs Mosh Pit for
YUMORI and Sunvista work.

Update the roadmap/owning interface before or with implementation, never after
silently changing the contract. Preserve a source-bound carry-forward when the
required runtime or verifier is unavailable. Do not claim this text creates an
automatic enforcement mechanism or an admitted production skill.

### Step 3: Generate Options

Generate at least 3 options:
1. `option_a`: conservative or incremental
2. `option_b`: balanced
3. `option_c`: aggressive
4. `option_none`: explicit "do nothing now" baseline

### Step 4: Score Options

Apply the three questions from **WSP 97 section 1.2.1, WSP 15 Economy and
Verification Binding**:

1. **Do I need it?** -> Importance and Impact.
2. **Can I afford it?** -> Complexity, compute, time, and verification cost.
3. **Can I live without it now?** -> Deferability and current blockers.

These questions project WSP 15; they do not introduce a second score.
Use canonical C + I + D + Impact values and P0-P4 ranges. In particular,
Deferability 5 means cannot defer, while 1 means highly deferrable. Keep the
allocation/rationale in the owning planning record and include it in
`evidence_refs`. An unauthenticated planning entry is not a runtime admission
receipt. Bind the affordable verification scope under WSP 97/WSP 6.

Score each option with:

1. **WSP 15 score**
   - complexity
   - importance
   - deferability
   - impact

2. **CTO diligence score**
   - reversibility (higher is better)
   - blast radius (lower is better)
   - security risk (lower is better)
   - operational burden (lower is better)
   - observability and rollback readiness (higher is better)

### Step 5: Select + Guardrail

Select one option and provide:
- decision rationale
- explicit risks accepted
- rollback trigger conditions
- first executable step

If chosen option has high blast radius with low evidence, fail closed.

For `high` and `critical` risk tiers:
- include a frontier-model adjudication note in output,
- include disagreement handling (Qwen vs frontier) before execution.

### Step 6: Emit Handoff Prompt

Produce an execution prompt for worker lanes with:
- objective
- ownership boundaries
- acceptance criteria
- required tests
- rollback command or procedure

For FoundUp changes, include the exact roadmap section/stage, WSP 15 allocation
reference, superseded-decision reference and shared-component regression scope
in the existing `worker_prompt` and `evidence_refs`. No new output schema is
introduced. Opening a PR is not completion: apply WSP 97's exact-head checks,
authorized squash merge and main verification, and report deployment and local
PC synchronization separately when required. Never infer PC state from GitHub.

## Output Contract

```json
{
  "status": "OK|FAIL_CLOSED",
  "decision": "string",
  "selected_option": "option_a|option_b|option_c|option_none",
  "wsp15": {
    "complexity": 0,
    "importance": 0,
    "deferability": 0,
    "impact": 0,
    "total": 0
  },
  "cto_diligence": {
    "reversibility": 0,
    "blast_radius": 0,
    "security_risk": 0,
    "ops_burden": 0,
    "rollback_readiness": 0
  },
  "evidence_refs": [],
  "inferences": [],
  "assumptions": [],
  "risks": [],
  "rollback_triggers": [],
  "first_step": "string",
  "worker_prompt": "string"
}
```

## Guardrails

1. No final decision without Holo evidence retrieval.
2. No external factual claim without source + date.
3. No irreversible recommendation without rollback path.
4. Always include "do nothing now" as a scored baseline.
5. Prefer the simplest option that meets constraints.
6. Do not execute a FoundUp build against an unreconciled roadmap or silently change its acceptance criteria.

## WSP Chain

- WSP 15: prioritization scoring
- WSP 30: staged module build orchestration
- WSP 50: pre-action verification
- WSP 64: violation prevention
- WSP 77: agent coordination
- WSP 91: observability and operational traceability
- WSP 95: SKILLz wardrobe operation
- WSP 97 section 1.2.1: economy and verification binding

## Change Record

- 2026-11-11: 1.0.1 adds FoundUp roadmap reconciliation, canonical three-question
  binding, shared desktop/phone regression requirements, and closure evidence.
  Instruction-only change; output JSON, model-tier gates and prototype admission
  remain unchanged. This is not evidence of a live skill invocation.
