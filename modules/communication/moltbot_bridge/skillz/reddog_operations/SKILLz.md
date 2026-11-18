---
name: reddog_operations
description: Provider-neutral operating discipline for bounded RedDog repository work.
version: 1.1.1
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
- Search before creating. Complete the pre-build audit below before proposing
  a work order, selecting a worker, or building; bind its decision to the
  existing operational snapshot and evidence receipts.
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
2. Complete the pre-build audit and comparison; evaluate retrieval coverage,
   noise, staleness, and duplicate-work risk before proposing work.
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

## Pre-build audit and decision

Apply WSP 3, WSP 50, WSP 84 and WSP 97 before work-order creation and again
before dependent writes when the head, owner, holds or evidence change. Reuse
a source-bound parent inventory for the assigned slice; do not start competing
repository-wide audits. On cold resume, memory history is context, not the
current queue or authority: retrieve fresh exact-head evidence from its owner.

1. Recover the objective, authorization, current owner/session, task/work-order
   reference, unfinished obligations and holds. Inspect accessible local
   `.agents/skills`, relevant host memories and existing task/receipt links.
   Missing owner evidence is UNKNOWN; inaccessible sources are unavailable,
   never an empty queue or permission to dispatch new workers.
2. Inspect the selected checkout's exact HEAD, dirty/untracked state and
   worktree/branch inventory, current main, and related open/merged PRs.
   Record source/head and observation time with timezone for each observation;
   distinguish local overlays, preview revisions, main and production.
   Preserve unknown or concurrently owned work. Use WSP 97 section 1.2A for
   stale-PR classification and WSP 110's handoff fields as draft guidance;
   neither a shared identity nor a branch name transfers a write lease.
3. Retrieve the owning module's interfaces, current code, newest relevant
   evidence, tests/README, tests/TestModLog and closest existing tests/fixtures
   before choosing implementation or test work (WSP 97 section 1.2B). Record
   accepted invariants, exact test IDs/results and their source/environment;
   separate historical passes, unrun checks and current failures.
4. Compare viable alternatives by invariant coverage, unique valid deltas,
   authority, tests, evidence freshness and live/preview/main differences.
   Newer is not automatically better: a newer failing candidate cannot
   displace an older qualified invariant without comparison and acceptance.
   Identify overlap between proposed work orders as well as existing work.
   Reuse the owner or reconcile the deltas; unresolved overlap blocks
   dependent writes rather than dispatching duplicate writers.
5. Trace relevant Brain, Breadcrumb and Memex inputs through their existing
   source receipts and operational snapshot. For build, ticket, PR, swarm,
   WRE and RSI claims, inspect the actual caller/consumer and acceptance
   evidence. Label documentation guidance, implemented source/test behavior
   and observed runtime integration separately using WSP 97 truth labels.
   A simulated swarm or queue scaffold is not admitted execution; preview
   playback or merged source does not establish production completion.
6. Record one compact decision in the existing work record, bound to the
   snapshot/assignment and source receipts. This planning record is not a new
   signed receipt schema, queue, memory store, dispatcher or authority:

   ```text
   decision: REUSE | EXTEND | RECONCILE | CREATE | BLOCKED
   scope_and_snapshot: objective, assignment/snapshot and evidence references
   sources: known/unavailable, source class, exact source/head, observed_at+timezone
   ownership: owner/session, task/work-order, holds; UNKNOWN where unresolved
   overlap_and_preservation: candidates, unique deltas, retained owner/work
   comparison: alternatives, accepted invariants, tests/results/environment, rationale
   authorization_and_next_action: allowed effects, blocker/recheck, next bounded action
   ```

   REUSE consumes qualified existing work; EXTEND changes its canonical owner;
   RECONCILE preserves and composes valid deltas under resolved ownership.
   CREATE requires bounded searches showing no reusable owner, with coverage
   gaps explicit; unavailable evidence cannot justify creation. BLOCKED names
   the affected action and recovery condition, leaving unrelated authorized
   work eligible. Do not overwrite failed or historical evidence with a new
   summary. Carry accepted invariants and tests into any authorized handoff.

The existing skill loader binds these instructions into the model prompt and
revalidates content/registry receipts at submit/resume. That enforces byte and
receipt integrity, not automatic completion of this audit or runtime admission.
Signed work orders, authentication, independent verification, CI, ownership and
promotion gates remain required. Start Operations remains read-only.

### Existing memory and execution owners

WSP 60 (`WSP_60_Module_Memory_Architecture.md`) and its existing
`WSP_framework/docs/annexes/WSP_60_FOUNDUP_MEMEX_ADDENDUM.md` own the memory map;
`docs/architecture/REDDOG_FOUNDUPS_SECOND_BRAIN_ARCHITECTURE.md` maps composition.
Use `reddog_operational_context_snapshot.py` for separate source receipts and
the existing Brain/Memex current-state and Breadcrumb query owners for context.
Use `agent_market/src/task_pipeline.py` for ticket lifecycle and WRE's
`git_lifecycle_inventory.py` for repository evidence. Follow
`docs/operations/WRE_RISK_BASED_VERIFICATION_HANDOFF_20261028.md` for execution
and independent verification, and WSP 48 for RSI qualification. Paths here are
discovery pointers, not proof that any path ran. PatternMemory admission still
requires the existing independent gates; staged outcomes outside recall or an
unready activation sink cannot establish an accepted improvement.

## Registered FoundUp Work

For a request to work on a named FoundUp:

1. Resolve the name, ID, token symbol, and module alias through the canonical
   `foundup_registry.json`; do not use a model-specific or FoundUp-specific
   conditional.
2. If the registry entry declares `brand_context_path`, load and validate that
   single FoundUp-owned brand context and concatenate it into grounding before
   Skillz selection. Parent identity is loaded first; a matched child FoundUp
   brand may override branding fields only. Child branding never inherits or
   creates token, route, safe-mutation, financial, credential, or governance
   authority.
3. Bind the registry entry, registry schema, brand context/schema when present,
   manifest, module docs, and available test history into one non-authoritative
   current-checkout grounding receipt. Treat registry `evidence_docs` as
   optional HoloIndex research inputs; they cannot displace mandatory direct
   reads or exhaust the bounded read budget.
4. Skillz consume the grounded brand context. Do not copy canonical brand
   spelling, aliases, domains, or child-brand rules into each Skillz. A brand
   change belongs in the FoundUp's brand-context file plus its regression tests.
5. Reject ambiguous registered names before Fusion. Do not guess whether
   unmatched language is a name or category: attach registry evidence, expose
   `requires_wsp109_resolution`, and grant no mutation scope until resolved.
6. Reconcile roadmap claims against current code, tests, ledger, PR, and
   receipt evidence. A stale roadmap cannot define current truth.
7. Apply WSP 15 and select exactly one bounded REUSE or EXTEND slice. CREATE is
   valid only after registry and module searches prove no reusable surface.
8. Execution still requires the normal signed work order, allowed paths,
   independent verifier, and promotion gates. The grounding receipt grants no
   shell, worktree, PR, merge, signer, or re-index authority.

## Sender identity, delivery and routing preflight

A message appearing in Gmail Sent, or the absence of a delivery-status failure, does **not** prove recipient receipt. The selected From identity is part of the exact outbound transaction and must be verified as carefully as To/CC/BCC. A configured Gmail account can send from a custom-domain alias by default: connection identity does not prove the outbound From address.

1. Resolve the principal-approved sender for this exact case from private/live correspondence routing or the principal's current instruction. Do not hard-code a personal email address into public Skillz or infer a global default from a single case.
2. **SUNVISTA / Edion / Sharp**: On 2026-10-16 the Edion manager reported that earlier custom-domain sender messages were not visible, while a live test reached the principal's direct Gmail account and the principal forwarded three messages using that Gmail sender. The principal directed Gmail (not the Foundups alias) for future SUNVISTA correspondence. Resolve the exact Gmail sender from the verified principal/private route and retain this case override until expressly changed.
3. Before submission inspect the actual provider From and Reply-To identity in the transaction or draft. If the connector cannot select or confirm the required From identity, **HOLD sender-dependent delivery** and select another authorized sender-selectable interface. Do not silently substitute the old default alias.
4. Mark suspected nonreceipt as RECEIPT_UNCONFIRMED, not a proven bounce, filtering issue, or domain-wide outage. Check recipient statements, actual replies, delivery-status notices including Trash, complete threads, and any authenticated delivery evidence. A negative observation at one recipient cannot be generalized to all recipients.
5. Before any requested retransmission or receipt check, reconcile Sent coverage and latest inbound per scope. Exclude answered, denied, closed, superseded, and already-forwarded messages. Prefer one concise, individually addressed receipt check with original date/subject and a request to acknowledge the newly chosen sender. Do not automatically repeat full attachments, long links, CCs or BCCs; respect follow-up caps and routing consent.
6. Post-send readback must verify the actual From, To/CC/BCC, thread and Sent status. Missing From evidence is UNVERIFIED, not silently accepted. VERIFIED_SENT must be kept distinct from RECIPIENT_CONFIRMED, which requires an acknowledgment or equivalent external receipt.

This policy is not evidence that Gmail sender-selection tools or the #1779 sender boundary are deployed. Maintain the existing distinction between 012-directed Work and unattended Red Dog.

## Canonical Email Draft Operations

For consequential email drafting, review, revision, forwarding, or send
handoff, treat version control as an operational safety boundary.

1. Resolve the newest authoritative message body before editing. Priority is:
   an exact user-supplied body explicitly declared current, then the current
   provider-side draft, then the exact sent message/thread, then an explicitly
   designated connected document. Conversation history and model memory are
   context only; they are never authoritative message text when a current
   artifact exists.
2. Maintain one canonical provider-side draft. Apply later edits in place
   rather than creating replacement drafts. Use a descriptive operational
   subject as a retrieval key and reminder; clean the subject before send when
   requested.
3. Before review or send, retrieve the current provider-side draft again.
   Verify `To`, `Cc`, `Bcc`, subject, exact body, reply/thread target, and all
   attachment filenames.
4. Search Sent before sending a draft that resembles a prior message. A draft
   can remain after the message was already sent. If an exact or substantially
   identical sent message exists, block duplicate send until the principal
   confirms it is a follow-up.
5. If a stale duplicate draft is confirmed, delete it when the connector
   exposes safe delete authority. If delete is unavailable, record it as stale
   and never use it as canonical.
6. If the body claims an attachment is included but the provider draft has no
   matching attachment, block send until reconciled.
7. For replies and forwards, read the source message first so recipients,
   quoted context, thread state, and claims remain grounded.
8. Resolve recipient identity from connected evidence when names or titles are
   ambiguous. Distinguish role-bearing names explicitly, and treat likely STT
   artifacts as non-authoritative until reconciled.
9. When the principal asks what an email says, translate or summarize the
   exact current artifact. If the provider exposes only a snippet, state that
   limitation and never reconstruct the unseen remainder from an older
   version.
10. If the principal supplies a newer exact body after review, promote that
    body to canonical and update the saved draft in place before any send.

Fail closed on ambiguous canonical bodies, unresolved recipient identity,
missing claimed attachments, unresolved duplicate-send risk, unverified
reply targets that materially change context, or material edits made after the
principal's last approval.

This discipline supplements connector authority; it never grants send, delete,
or mutation authority by itself.

## Start Operations Boundary

The Start Operations cycle is read-only. It may inspect, prioritize, research,
and create at most one candidate queue item. It grants no source mutation,
shell, worktree, PR, merge, signer, or re-index authority.
