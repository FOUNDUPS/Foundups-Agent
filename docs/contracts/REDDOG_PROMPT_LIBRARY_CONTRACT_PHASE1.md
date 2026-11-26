# REDDOG_PROMPT_LIBRARY_CONTRACT_PHASE1

Status: RATIFIED CONTRACT SPEC
Mode: decision-only
Base: stacked on REDDOG_PROMPT_LIBRARY_AND_M2M_REGISTRY_AUDIT_PHASE1
Date: 2026-07-13
WSP lock: WSP_00, WSP_15, WSP_22, WSP_50, WSP_95, WSP_97, WSP_99, WSP_109

Predecessor:
- `docs/audits/architecture/REDDOG_PROMPT_LIBRARY_AND_M2M_REGISTRY_AUDIT_PHASE1.md`

Truth-label legend:
- OBSERVED: direct-read evidence from the predecessor audit or repository source.
- INFERRED: conclusion from OBSERVED evidence.
- SPECIFIED_NOT_IMPLEMENTED: defined by this contract; not implemented in runtime code.

## Purpose

Define the canonical RedDog prompt library contract. This is the missing layer between
012 natural-language intent, RedDog prompt authoring, WSP_99 M2M compilation, WRE worker
dispatch, and outcome learning.

This contract does not build storage, dispatch, workers, HoloIndex re-indexing, or runtime
extension consumption. It freezes the wire-level schemas so later slices can implement them
without ambiguity.

## Non-goals

- No extension runtime mutation.
- No WRE dispatch.
- No worker creation.
- No shell, git, PR, merge, or worktree operation.
- No HoloIndex re-index.
- No PromptRegistry database implementation.
- No OpenClaw, Hermes, or WRE execution wiring.

## Current Evidence

| Claim | Evidence | WSP_97 |
|-------|----------|--------|
| WSP_99 M2M exists | `prompt/swarm/m2m_compiler.py`, `prompt/swarm/0102_M2M_SCHEMA.yaml`, `WSP_framework/src/WSP_99_M2M_Prompting.md` | OBSERVED |
| Prompt fixtures exist | `extensions/foundups_advisory_workers/tests/fixtures.js` | OBSERVED |
| RedDog prompt-authoring output gate exists | v0.3.60 ModLog and extension contract tests | OBSERVED |
| Runtime gates exist | `runtime_consumption_gate`, `fusion_panel_quorum`, typed grounding telemetry in `extension.js` | OBSERVED |
| Prompt registry is missing | No canonical PromptReceipt/PromptRun/PromptOutcome registry surfaced in direct-read or HoloIndex probes | OBSERVED |

## Canonical Entities

The prompt library has five first-class objects:

```text
PromptTemplate
PromptReceipt
PromptRun
PromptOutcome
PromptPatternPromotion
```

Only `PromptReceipt` can authorize WRE to consider dispatch. A raw model answer, a copied
chat prompt, or a PR body is not a dispatch authority.

## PromptTemplate Schema

```yaml
PromptTemplate:
  template_id:
    type: string
    required: true
    format: redprompt-template-{digest16}
  version:
    type: int
    required: true
    min: 1
  template_kind:
    type: enum
    required: true
    values:
      - worker_prompt
      - audit_prompt
      - verifier_prompt
      - sentinel_prompt
      - repair_prompt
      - m2m_packet
  domain_profile:
    type: string
    required: true
    examples:
      - generic
      - wsp109_foundup_intake
      - holoindex_freshness
      - live_writer_preauth
      - token_efficiency
  slice_pattern:
    type: string
    required: true
  wsp_refs:
    type: array[int]
    required: true
  required_sections:
    type: array[string]
    required: true
  forbidden_sections:
    type: array[string]
    required: true
  required_evidence:
    type: array[string]
    required: true
  prompt_body:
    type: string
    required: true
  prompt_body_digest:
    type: sha256
    required: true
  examples_positive:
    type: array[string]
    required: true
  examples_negative:
    type: array[string]
    required: true
  active:
    type: bool
    required: true
```

Rules:
- `prompt_body_digest` is computed over `prompt_body` exactly as stored.
- Positive and negative examples must be fixture IDs, not embedded chat history.
- WSP_109 templates are domain profile `wsp109_foundup_intake`, not a separate registry.

## PromptReceipt Schema

```yaml
PromptReceipt:
  prompt_id:
    type: string
    required: true
    format: redprompt-{digest16}
  prompt_digest:
    type: sha256
    required: true
  template_id:
    type: string | null
    required: true
  prompt_kind:
    type: enum
    required: true
    values:
      - worker_prompt
      - audit_prompt
      - verifier_prompt
      - sentinel_prompt
      - repair_prompt
      - m2m_packet
  slice_name:
    type: string
    required: true
  lane:
    type: enum
    required: true
    values: [ORCH, A, B, C, D, QA, SENTINEL]
  role:
    type: enum
    required: true
    values: [architect, worker, verifier, coordinator, validator]
  origin:
    type: enum
    required: true
    values: [external_principal, internal_handoff, autonomous_trigger]
  principal_ref:
    type: string | null
    required: true
  wsp_refs:
    type: array[int]
    required: true
  requested_outputs:
    type: array[string]
    required: true
  in_scope_paths:
    type: array[string]
    required: true
  out_scope_paths:
    type: array[string]
    required: true
  read_first_targets:
    type: array[string]
    required: true
  holoindex_query_digest:
    type: sha256 | null
    required: true
  holoindex_freshness_receipt:
    type: string | null
    required: true
  index_gap_detected:
    type: bool
    required: true
  typed_grounding_receipt_digest:
    type: sha256 | null
    required: true
  wardrobe_selection_receipt_digest:
    type: sha256 | null
    required: true
  m2m_compiled:
    type: bool
    required: true
  m2m_digest:
    type: sha256 | null
    required: true
  raw_ref:
    type: string | null
    required: true
  prompt_relevance_passed:
    type: bool
    required: true
  fusion_quorum_passed:
    type: bool
    required: true
  approved_for_dispatch:
    type: bool
    required: true
  rejection_reasons:
    type: array[string]
    required: true
  no_runtime_execution_performed:
    type: bool
    required: true
  no_repo_mutation_performed:
    type: bool
    required: true
```

## PromptReceipt Approval Rules

approved_for_dispatch may be true only when all conditions hold:

1. `prompt_relevance_passed=true`.
2. `fusion_quorum_passed=true` for HIGH/ULTRA or authority-affecting prompts.
3. Required typed grounding is bound by `typed_grounding_receipt_digest`.
4. Required HoloIndex freshness is bound by `holoindex_freshness_receipt`, or `index_gap_detected=true` with a fail-closed route.
5. WSP_99 M2M prompt has either `m2m_compiled=false` because not applicable, or `m2m_compiled=true` with `m2m_digest` and `raw_ref`.
6. `rejection_reasons=[]`.
7. Both no-action attestations are true.

If any rule fails, the receipt remains advisory and WRE must not dispatch a worker from it.

## PromptRun Schema

```yaml
PromptRun:
  run_id:
    type: string
    required: true
    format: redprompt-run-{digest16}
  prompt_id:
    type: string
    required: true
  prompt_digest:
    type: sha256
    required: true
  worker_id:
    type: string
    required: true
  worktree_id:
    type: string | null
    required: true
  branch:
    type: string | null
    required: true
  base_sha:
    type: string
    required: true
  started_at:
    type: int
    required: true
  completed_at:
    type: int | null
    required: true
  status:
    type: enum
    required: true
    values: [PENDING, RUNNING, VERIFIED_READY, FAILED, BLOCKED, LANDED, SUPERSEDED]
  pr_url:
    type: string | null
    required: true
  files_changed:
    type: array[string]
    required: true
  tests_run:
    type: array[string]
    required: true
  test_result:
    type: string
    required: true
  codeql_status:
    type: string | null
    required: true
  index_gap_events:
    type: array[string]
    required: true
  receipts:
    type: array[string]
    required: true
  no_merge_performed_by_worker:
    type: bool
    required: true
```

Rules:
- `PromptRun.prompt_digest` must match the referenced `PromptReceipt.prompt_digest`.
- `PromptRun` does not prove work quality; it records execution evidence.
- A worker cannot mark itself `LANDED`; landing requires an external promotion receipt.

## PromptOutcome Schema

```yaml
PromptOutcome:
  outcome_id:
    type: string
    required: true
    format: redprompt-outcome-{digest16}
  run_id:
    type: string
    required: true
  prompt_id:
    type: string
    required: true
  status:
    type: enum
    required: true
    values: [success, partial, failed, blocked, superseded]
  accepted_by:
    type: enum
    required: true
    values: [red_dog, 0102_architect, 012_sovereign, ci]
  landed_sha:
    type: string | null
    required: true
  regressions_added:
    type: array[string]
    required: true
  failure_class:
    type: string | null
    required: true
  reusable_pattern:
    type: bool
    required: true
  negative_fixture_required:
    type: bool
    required: true
  promoted_to_library:
    type: bool
    required: true
  promoted_template_id:
    type: string | null
    required: true
  notes_digest:
    type: sha256
    required: true
```

Rules:
- A successful outcome may propose template promotion, but promotion is a separate receipt.
- A failed prompt with a new failure class must set `negative_fixture_required=true`.
- Outcome memory must be queryable before RedDog recommends duplicate work.

## PromptPatternPromotion Schema

```yaml
PromptPatternPromotion:
  promotion_id:
    type: string
    required: true
  source_outcome_id:
    type: string
    required: true
  source_prompt_id:
    type: string
    required: true
  new_template_id:
    type: string
    required: true
  promotion_reason:
    type: string
    required: true
  negative_fixtures_added:
    type: array[string]
    required: true
  positive_fixtures_added:
    type: array[string]
    required: true
  reviewer_receipt_digest:
    type: sha256
    required: true
  no_runtime_execution_performed:
    type: bool
    required: true
```

## Dispatch Boundary

The prompt library may only produce a dispatch candidate. It may not directly create
worktrees, run shell commands, enqueue OpenClaw, dispatch Hermes, merge PRs, or settle
rewards.

Allowed output:

```text
PromptDispatchCandidate
```

Forbidden outputs:

```text
git worktree add
subprocess execution
OpenClaw enqueue
Hermes execution
PR merge
HoloIndex re-index
reward settlement
```

## HoloIndex Boundary

Prompt library lookup must emit a freshness receipt:

```yaml
PromptLibraryFreshnessReceipt:
  query_digest: sha256
  prompt_library_indexed_at: string | null
  prompt_library_hit_count: int
  template_ids: array[string]
  index_gap_detected: bool
  index_gap_event: string | null
  runtime_reindex_performed: false
  recommended_owner: WRE_CI_INDEX_MAINTENANCE
```

RedDog runtime must never re-index HoloIndex. WRE/CI owns re-indexing after prompt
templates or outcomes land.

## WSP_109 Domain Profile

WSP_109 FoundUp creation prompts are represented as:

```yaml
domain_profile: wsp109_foundup_intake
wsp_refs: [50, 97, 99, 109]
```

They may include templates for:
- idea -> WSP_109 intake packet
- intake packet -> create_foundup dry-run plan
- create_foundup dry-run plan -> scaffold writer dry-run

They must not define a separate prompt library.

## WSP_15 Next Slices

1. `REDDOG_PROMPT_EXAMPLES_FIXTURE_LIBRARY_PHASE1`
2. `REDDOG_PROMPT_M2M_COMPILATION_GATE_PHASE1`
3. `REDDOG_PROMPT_RELEVANCE_AND_QUORUM_GATE_PHASE1`
4. `REDDOG_PROMPT_LIBRARY_STORAGE_DRYRUN_PHASE1`
5. `REDDOG_PROMPT_LIBRARY_RETRIEVAL_DRYRUN_PHASE1`
6. `REDDOG_PROMPT_LIBRARY_TO_WRE_DISPATCH_DRYRUN_PHASE1`
7. `REDDOG_PROMPT_RUN_OUTCOME_MEMORY_PHASE1`
8. `REDDOG_PROMPT_LIBRARY_HOLOINDEX_FRESHNESS_PHASE1`
9. `REDDOG_PROMPT_LIBRARY_RUNTIME_CONSUMPTION_PHASE1`

## Truth Boundary Checklist

| Check | Status |
|-------|--------|
| Contract only | YES |
| No runtime implementation | YES |
| No extension runtime mutation | YES |
| No WRE dispatch | YES |
| No HoloIndex re-index | YES |
| Prompt schemas freeze field names | YES |
| WSP_99 remains M2M prompt layer | YES |
| WSP_109 remains domain profile | YES |
| Worker dispatch remains SPECIFIED_NOT_IMPLEMENTED | YES |
| Runtime authority remains blocked | YES |

## Residual SPECIFIED_NOT_IMPLEMENTED

- Prompt registry storage.
- Prompt library retrieval.
- Prompt M2M compilation gate binding.
- Prompt relevance/quorum approval binding.
- Prompt dispatch candidate generation.
- Prompt run and outcome recording.
- Prompt template promotion.
- HoloIndex prompt-library freshness receipts.
- Runtime consumption by RedDog extension.
