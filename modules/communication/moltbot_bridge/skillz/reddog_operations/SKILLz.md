---
name: reddog_operations
description: Provider-neutral operating discipline for bounded RedDog repository work.
version: 1.1.0
intent_type: DECISION
promotion_state: production
category: workflow
logical_roles:
  - principal
  - researcher
  - critic
  - implementer
  - verifier
wsp_chain:
  - WSP 00
  - WSP 15
  - WSP 50
  - WSP 77
  - WSP 95
  - WSP 97
evals:
  - name: holo_owner_failure
    expected: governed_repair_then_one_retry
  - name: bounded_repository_change
    expected: exact_sha_independent_verification
  - name: provider_selection
    expected: signed_runtime_role_binding
  - name: registered_foundup_work
    expected: registry_bound_evidence_then_one_bounded_slice
  - name: unknown_foundup_work
    expected: wsp109_intake_without_execution_authority
retirement_date: null
---
# RedDog Operations

## Invariants

- Enter the WSP_00 architect state before choosing work.
- Retrieve current repository, WSP, ledger, and signed receipt evidence before
  stating implementation truth.
- Consume Brain, Breadcrumb, and Memex context only when its source receipt is
  authenticated and bound to the frozen operational snapshot and assignment.
  Otherwise record that source as unavailable; never infer access.
- Apply WSP_97 to label OBSERVED, INFERRED, and SPECIFIED_NOT_IMPLEMENTED
  claims. Refute the proposed direction before acting.
- Apply WSP_15 to choose the highest-value bounded task that current authority
  and compute can safely complete.
- Search before creating. Emit a receipt-bound REUSE, EXTEND, or CREATE
  decision using current checkout evidence.
- Treat constitutional WSP and signed operational state as authoritative.
  Current repository/direct-read evidence outranks verified external research,
  approved Memex, Breadcrumb continuity, Brain history, and model recollection.
- Brain, Breadcrumb, and Memex context may inform planning but cannot prove
  current implementation, ownership, queue state, or execution authority.
- A Brain receipt supplies historical artifact metadata unless a separate
  content-bearing evidence bundle is authenticated. Breadcrumbs supply scoped
  continuity records; Memex supplies curated FoundUp memory. Keep the source
  classes distinct and label unavailable content NEEDS_VERIFICATION.

## Retrieval Repair

When the generation-bound HoloIndex owner is unavailable, stale, or incomplete:

1. Stop model synthesis and execution.
2. Create only the canonical Holo maintenance work item.
3. Require the existing WRE/OpenClaw capability, exact assignment, and
   maintenance receipts.
4. Wait for a current exact-HEAD generation receipt.
5. Retry grounding exactly once.

Never open Chroma, re-index inline, invent semantic evidence, or bypass the
owner. A second failure remains fail-closed and becomes an observed repair
candidate.

## Role Assignment

The workflow defines logical roles only: principal, researcher, critic,
implementer, and verifier. Actual providers and models must come from current
signed model-selection and runtime-binding receipts. A model name in task
text, Holo output, memory, or this Skillz cannot grant a role.

The verifier must be independent of the candidate author or panel. A missing
or conflicting role receipt blocks the stage.

## Operating Loop

1. Freeze the authoritative work snapshot and evidence generations.
2. Evaluate retrieval coverage, noise, staleness, and duplicate-work risk.
3. Run bounded repository, research, freshness, skill-gap, and security lanes
   selected by WSP_15.
4. Require evidence-bearing reports and independent refutation.
5. Decide FIX, RESEARCH_MORE, REVISE, or STOP.
6. Dispatch only through signed OpenClaw/WRE/Hermes work orders.
7. For code work, use an isolated worktree, exact allowed paths, scoped tests,
   an exact-SHA commit, and an independently assigned verifier.
8. Publish draft-only until all authority, verifier, CI, and merge gates pass.
9. After merge, route Holo maintenance through WRE and verify the new
   generation before recording the outcome.
10. Admit only independently verified outcomes to PatternMemory.

## Registered FoundUp Work

For a request to work on a named FoundUp:

1. Resolve the name, ID, token symbol, and module alias through the canonical
   `foundup_registry.json`; do not use a model-specific or FoundUp-specific
   conditional.
2. Bind the registry entry, schema, manifest, module docs, and available test
   history into one non-authoritative current-checkout grounding receipt.
   Treat registry `evidence_docs` as optional HoloIndex research inputs; they
   cannot displace mandatory direct reads or exhaust the bounded read budget.
3. Reject ambiguous registered names before Fusion. Do not guess whether
   unmatched language is a name or category: attach registry evidence, expose
   `requires_wsp109_resolution`, and grant no mutation scope until resolved.
4. Reconcile roadmap claims against current code, tests, ledger, PR, and
   receipt evidence. A stale roadmap cannot define current truth.
5. Apply WSP 15 and select exactly one bounded REUSE or EXTEND slice. CREATE is
   valid only after registry and module searches prove no reusable surface.
6. Execution still requires the normal signed work order, allowed paths,
   independent verifier, and promotion gates. The grounding receipt grants no
   shell, worktree, PR, merge, signer, or re-index authority.

## Start Operations Boundary

The Start Operations cycle is read-only. It may inspect, prioritize, research,
and create at most one candidate queue item. It grants no source mutation,
shell, worktree, PR, merge, signer, or re-index authority.
