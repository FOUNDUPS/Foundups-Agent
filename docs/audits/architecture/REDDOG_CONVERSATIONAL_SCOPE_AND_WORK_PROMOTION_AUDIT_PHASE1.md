# REDDOG_CONVERSATIONAL_SCOPE_AND_WORK_PROMOTION_AUDIT_PHASE1

**Status:** VERIFIED AUDIT / DECISION ONLY
**Audited base:** `4ae4cf81756a99ced3b0d0c1282a5eb576050594` (`main == origin/main`)
**Date:** 2026-08-05
**Runtime authority change:** NONE
**Repository mutation authority change:** NONE

## 1. Executive Decision

RedDog already has most of the required parts, but they are not concatenated into a
FoundUp-scoped conversational lifecycle.

Current implementation provides:

- in-memory editor history;
- an optional sanitized continuation summary;
- current-turn FoundUp grounding;
- a transport-neutral `reddog_intent.v2` request;
- durable resident cycles and status in AgentDB;
- architect determination and bounded queue candidates;
- proposal admission, proposal authenticity, principal policy authorization, signed
  WSP 15 work-order promotion, durable nonce handling, and claim-time verification.

Current implementation does not provide:

- a durable, authenticated, revisioned conversational scope;
- an active FoundUp and topic that can be safely resolved across turns;
- one canonical pending work proposal bound to the conversation revision;
- a principal-authenticated request that causes the existing policy authorization
  system to approve the exact proposal digest;
- return of canonical work status and verified results to the originating conversation.

The missing work is authenticated concatenation of existing owners. It is not a new
chat engine, queue, signer, provider router, or orchestration framework.

Production truth boundary:

```text
WORK_PROMOTION_BLOCKED_BY_AUTHENTICATED_SCOPE_AND_PRINCIPAL_APPROVAL
```

## 2. WSP Operating Order

### WSP 00

Workstream: RedDog conversational interface and bounded work promotion.

The work is an extension of the existing RedDog thin client, resident architect,
AgentDB, WRE, and signed-worker runtime. It is not a new FoundUp or a new DAE.

### WSP 97

Repository truth was established from current `main`, direct implementation reads,
tests, receipts, and three independent read-only reviews. Naming and documentation
were not treated as runtime proof.

The legacy `holo_index.py --bundle-json` entry point returned `STALE_INDEX` with
`freshness_repo_root_mismatch`. The canonical generation-bound owner query then
returned `ok=true`, `freshness=CURRENT`, `index_gap_detected=false`, and authority
HEAD `4ae4cf81756a99ced3b0d0c1282a5eb576050594`. The canonical owner receipt is the
retrieval authority, so this audit does not open an index-maintenance work item. No
re-index was performed.

### WSP 15

| Question | Decision |
|---|---|
| Do I need to code it? | Yes. Natural multi-turn work promotion is missing. |
| Can I afford to code it? | Yes, as additive bindings and tests over existing owners. |
| Can I live without it now? | Briefly. Current subject-complete prompts fail closed safely, but RedDog cannot provide the intended conversational operator experience. |

Implementation priority: `C4 + I4 + D3 + Impact4 = 15`, P1. The implementation must
not displace P0 signer, authority-root, or live-canary work.

## 3. Current RedDog Sequence

```text
current work focus
-> route and effort classification
-> typed target extraction
-> current-turn FoundUp grounding
-> HoloIndex/direct-read evidence assembly
-> WSP task prompt
-> optional sanitized continuation summary
-> redaction gate
-> model or Fusion call using editor history
-> output and runtime-consumption validation
-> wardrobe recommendation and extension dry-run work candidate
-> optional reddog_intent.v2
-> durable AgentDB resident cycle
-> Foundups-local OpenClawSupervisor claims read-only tasks
-> audit reports
-> ArchitectDeterminationReceipt
-> at most one queue candidate
-> existing authenticated proposal and signed work-order chain
```

Evidence owners include:

- `extensions/reddog/extension.js`
- `extensions/reddog/continuation_prompt.js`
- `extensions/reddog/foundup_work_runtime_binding.js`
- `extensions/reddog/grounded_target_continuity.js`
- `modules/communication/moltbot_bridge/src/reddog_resident_architect_client.py`
- `modules/communication/moltbot_bridge/src/reddog_resident_architect_durable_agentdb_cycle.py`
- `modules/communication/moltbot_bridge/src/reddog_backend_architect_determination_runtime.py`

## 4. Current Behavior Classification

| Surface | Classification | Runtime truth |
|---|---|---|
| Editor conversation | IMPLEMENTED | Per-tab in-memory `state.history`. |
| Sanitized continuation | PARTIALLY_WIRED | Optional advisory summary; no authority. |
| Continuation telemetry | CONFLICTING | Summary can be disabled while full `state.history` still reaches the model. |
| Current work focus | IMPLEMENTED | Each request is classified and grounded independently. |
| Active FoundUp conversation scope | MISSING | No durable active FoundUp/topic/objective in editor or AgentDB conversation state. |
| FoundUp grounding | IMPLEMENTED | Current-turn registry and repository grounding is fail closed. |
| Work proposal | PARTIALLY_WIRED | Extension candidate and backend determination/queue candidate are separate layers. |
| Resident intent | IMPLEMENTED | `reddog_intent.v2` is durable request state, not execution authority. |
| Resident status | IMPLEMENTED | AgentDB revisioned cycle status exists; editor reconnection is limited to Start Operations. |
| Signed proposal/work authority | IMPLEMENTED | Existing authenticity, policy, nonce, promotion, and claim-time chain must be reused. |
| General conversational work promotion | MISSING | No exact preview -> verified principal-signed policy authorization -> existing authority-chain transition. |

## 5. Findings

### F1 - Major: continuation consent and telemetry conflict

`extension.js` computes `continuationEnabled` and gates only the sanitized continuation
summary. Ordinary Fusion dispatch still passes `state.history` to `callFusion`, the
bridge includes it in the payload, and `scripts/advisory_model_once.py` inserts the
cleaned history into provider messages.

Therefore `Continuation: disabled` does not prove that prior-turn model history was
withheld. This is not an authority bypass, but it is a material consent and telemetry
defect.

Required correction:

- gate model history under an explicit, accurately named history policy; or
- report separate `sanitized_continuation_attached` and `model_history_attached`
  telemetry and give 012 independent control.

### F2 - Major: no durable conversational scope

Extension state stores history, a continuation summary, and an operations intent ID.
It does not store an authenticated active FoundUp, active topic, objective, accepted
decisions, pending proposal, or scope revision.

Subjectless follow-ups intentionally fail closed. This is safe, but it prevents the
requested flow from discussion to a bounded proposal.

### F3 - Major: overlapping proposal stages are not bound together

The extension builds a `RedDogGovernedWorkOrder` candidate from the current work
focus. The backend architect independently creates an `ArchitectDeterminationReceipt`
and at most one queue candidate. Neither is the canonical pending proposal for a
conversation revision.

The existing `ArchitectProposalAdmissionReceipt`, authenticity payload, policy
authorization, nonce protocol, promotion transaction, signed work-order verifier, and
AgentDB envelope already provide the downstream trust chain. A conversational layer
must bind into these contracts rather than duplicate them.

### F4 - Moderate: resident durability is only partially projected to the editor

AgentDB persists cycle IDs, intent IDs, revisions, tasks, claims, transitions, status,
and determination. The normal editor path remains synchronous. Only the exact Start
Operations route persists an intent ID and reconnects to durable status after reload.

The existing Start Operations status pattern should be generalized to an active
conversation/work proposal. The resident cycle must not be described as an
independently running conversation service.

### F5 - Major: conversational scope has no authenticated authorization source

The resident client currently receives principal and FoundUp scope from constructor
inputs, while the editor obtains them from options or environment configuration.
Configuration is not authentication. Final work-order gates protect repository
effects, but an untrusted scope could expose conversation, Memex, status, or evidence
from another FoundUp before promotion.

Conversation create, resume, evidence retrieval, and promotion must reuse and
revalidate the existing principal policy, permission snapshot, authority profile,
key epoch, revocation, freshness, and FoundUp scope. A conversation-specific
authorization system is forbidden.

### F6 - Moderate: resident intent provenance needs additive hardening

The resident client validates `reddog_intent.v2`, principal, source, FoundUp scope,
and `submits_executable_authority == false`. It accepts any non-empty intent ID and
normalizes identity aliases.

Before conversational promotion:

- enforce an exact intent field set;
- recompute the intent ID from canonical content;
- reject conflicting identity aliases;
- bind the canonical intent ID and digest into proposal authenticity.

### F7 - Moderate: FoundUp identity is indirect in proposal authenticity

The signed proposal binds paths, snapshots, repository HEAD, evidence, WSP 15, policy,
Memex, principal, and signer data, but it lacks a direct `foundup_id` supplied from
authoritative cycle/work state. Add it to the existing payload and policy
authorization. Do not derive the expected FoundUp from the receipt being checked.

Final promotion and work-order verification already perform stronger FoundUp and path
containment checks; this is an earlier defense-in-depth binding.

### F8 - Moderate: provider names are not execution authority

Foundups-local `OpenClawSupervisor` is the production AgentDB task claimant. It is not
proof that upstream OpenClaw orchestrates the task. Current upstream OpenClaw and
Hermes integrations are bounded artifact-generation surfaces with tools disabled;
legacy Hermes real delegation remains blocked.

Model Intelligence owns model and panel selection. WSP 15 owns worker-plan roles.
Conversation may record 012's requested provider and RedDog's recommendation, but the
provider used at promotion must be derived and verified by current routing authority.

### F9 - Moderate: canonical and legacy queues/results coexist

The legacy `_FOUNDUP_JOB_QUEUE` is in-memory and explicitly does not start Hermes/WRE.
It must not be extended for resident conversational work.

Canonical results belong in AgentDB's append-only signed-worker result ledger. The
older response-shape-to-PatternMemory path is not independent verification and must
not become proposal or learning authority.

### F10 - Low: documentation drift

Extension documentation states continuation defaults on while current configuration
and behavior default it off. The roadmap also carries duplicate/inconsistent
continuation slice states. External RedDog context files contain old repository and PR
state and explicitly are not live-updated.

These sources remain below current repository, AgentDB, receipts, and tests in the
evidence precedence order.

The earlier `REDDOG_SESSION_CONTINUITY_CAPTURE_PHASE1` audit is adjacent but not an
equivalent contract. It created a manual, curated external session-closeout import and
explicitly deferred live RedDog/HoloIndex/WRE consumption. It must not be promoted into
runtime conversation authority. Its validator and curated-summary discipline may be
reused as privacy guidance only.

## 6. Existing Ownership Map

| Concern | Canonical owner to extend |
|---|---|
| Thin-client state and display | `extensions/reddog` |
| Transport-neutral continuity fields | `continuity_context.py` |
| FoundUp registry grounding | `foundup_work_runtime_binding.js` and resident grounding service |
| Durable intent/cycle/status | `RedDogResidentArchitectClient` and AgentDB resident cycle |
| Architect determination | backend architect determination runtime |
| Proposal readiness | architect proposal admission contract |
| Proposal authenticity | architect proposal authenticity and runtime authorization |
| WSP 15 work promotion | architect FIX signed WSP 15 promotion |
| Durable queue, claims, results | AgentDB signed-worker publication and result ledger |
| Queue sequencing and effects | WRE resident queue planner/serial loop/handler registry |
| Task claiming | Foundups-local `OpenClawSupervisor` |
| Model/panel choice | Model Intelligence and AI Gateway |
| Provider execution | redaction-gated provider runtime and bounded upstream artifact providers |
| WSP 109 onboarding | AI Overseer `foundup_genesis` package |

## 7. WSP 109 Relationship

WSP 109 governs new FoundUp onboarding intake. It does not own general conversational
state for an already registered FoundUp.

For an existing FoundUp:

```text
conversation scope
-> registry/current repository grounding
-> resident intent and architect proposal
```

For a new or unregistered FoundUp:

```text
conversation scope
-> WSP 109 intake packet/envelope
-> validated intake receipt bound into resident evidence
```

Automatic WSP 109 packet production from the extension remains
`SPECIFIED_NOT_IMPLEMENTED`. Do not route around that boundary and do not extend the
legacy in-memory FoundUp job queue.

## 8. Exact Missing Seam

The smallest missing seam is:

```text
authenticated conversation turn
-> authenticated principal policy and FoundUp scope revalidation
-> revisioned FoundUp scope in AgentDB
-> current-turn grounding and evidence classification
-> immutable pending proposal bound to scope revision
-> visible proposal preview
-> principal-authenticated approval request for exact proposal digest
-> existing principal-signed ArchitectProposalPolicyAuthorization
-> existing architect proposal authenticity/policy chain
-> existing signed WSP 15 promotion
-> existing AgentDB queue/claim/result path
-> canonical status projection to the originating conversation
```

Conversation context remains interpretation input only. It must never satisfy a
signature, nonce, policy, freshness, repository HEAD, Holo generation, WSP 15,
work-order, claim, effect, PR, or merge gate.

## 9. Duplicate-Contract Analysis

| Candidate | Decision | Reason |
|---|---|---|
| New chat database | REJECT | AgentDB already owns durable intent/cycle/task/result state. |
| New orchestrator | REJECT | Resident client, WRE queue, and OpenClawSupervisor already own the chain. |
| New signer/approval token | REJECT | Existing proposal authenticity, principal policy, nonce, and work-order signing must be reused. |
| New work proposal schema | REJECT | Extend architect proposal admission/authenticity with conversation bindings. |
| New provider router | REJECT | Model Intelligence and WSP 15 worker plan own selection. |
| New result memory | REJECT | AgentDB signed-worker result ledger is canonical. |
| Extend continuity envelope | ACCEPT | Add turn lineage; do not make it authority. |
| Extend resident intent/cycle | ACCEPT | Add canonical conversation and scope bindings. |
| Extend AgentDB resident state | ACCEPT | Add revision/CAS scope and pending proposal references. |
| Extend proposal contracts | ACCEPT | Add exact scope, FoundUp, existing policy authorization, and evidence bindings. |
| Extend thin-client status | ACCEPT | Reuse Start Operations persistence/reconnection pattern. |

## 10. Minimal Contract Changes

The repository should choose local names consistent with existing contracts. The
minimum semantics are:

### Conversational scope receipt

```text
conversation_id
conversation_revision
turn_id
parent_turn_id
principal_id
transport/session binding
active_foundup_id
discussion_foundup_ids
active_topic
current_objective
accepted_decisions
rejected_options
open_questions
repository_evidence_refs
source_snapshot_id and digest
last_grounded_head_sha
holoindex_generation_id and freshness receipt
pending_work_proposal_id and digest
created_at, updated_at, expiry
receipt_id
```

Authority source:

- Authenticate the principal and authorized FoundUp set using the existing principal
  policy, permission snapshot, authority profile, signer key epoch, and revocation
  infrastructure.
- Revalidate before create, resume, evidence disclosure, and promotion.
- Environment variables and constructor mappings are configuration inputs only and
  cannot establish scope authority.

Rules:

- AgentDB revision/CAS semantics are mandatory.
- The principal and authorized FoundUp set are mandatory.
- Multi-FoundUp discussion is allowed; work promotion selects exactly one FoundUp.
- Verified facts, 012 statements, model inferences, and unresolved claims remain typed
  separately.
- Raw conversation is not durable execution authority.
- Repository HEAD, scope, evidence-generation, or objective changes invalidate a
  pending policy authorization.

### Work-promotion preview

Extend the existing architect proposal contracts with:

```text
conversation_id and revision
canonical resident intent ID and digest
foundup_id from authoritative cycle/work state
objective and task class
repository target
evidence bundle and freshness bindings
expected deliverable and success criteria
allowed and forbidden effects
requested provider and derived provider recommendation
inferred fields
repository-proven fields
explicitly approved fields
existing principal-signed policy authorization ID and digest
expiry
```

The preview is immutable. A natural-language `Proceed` creates an authorization
request only. Approval exists only after the existing
`ArchitectProposalPolicyAuthorization` is issued and verified with principal
proof-of-possession over the expected proposal payload. Conversation revision and
preview digest must be bound into that payload. Without this proof, the system remains
in prepare/preview mode. Any mutation creates a new preview and invalidates prior
authorization.

## 11. Security and Isolation Matrix

| Attack or failure | Required result |
|---|---|
| `Do it` with no active scope | Clarify; no proposal or dispatch. |
| Ambiguous `it` across topics | Show ambiguity; no dispatch. |
| Multi-FoundUp discussion promoted as shared authority | Reject; select exactly one FoundUp. |
| Another principal resumes a session | Reject before context disclosure. |
| Forged environment/caller FoundUp scope | Reject before context or evidence disclosure. |
| Unauthorized FoundUp discussion target | Reject or return a non-disclosing denial. |
| FoundUp permission revoked mid-session | Invalidate scope and pending proposal. |
| Cross-tab/session fixation | Reject principal, transport, or parent-turn mismatch. |
| Principal key rotation/revocation before resume | Re-authenticate; invalidate stale authorization. |
| Cross-FoundUp Memex/breadcrumb/result projection | Reject before projection. |
| Stale HEAD, snapshot, or Holo generation | Re-ground and issue a new preview. |
| Proposal changed after authorization | Digest mismatch; reject. |
| Approval replay | Durable nonce/revision rejection. |
| Provider substitution | Recompute routing and require a new preview and policy authorization. |
| Mutation scope expanded | Existing path/policy gate rejects; new policy authorization required. |
| Worker result lacks signed result/verifier receipts | Status may show unverified; context cannot mark it verified. |
| Conversation text claims `012 approves` | No authority effect. |
| Conversation history used as signed evidence | Reject. |
| Expired session or proposal | Re-ground; no promotion. |
| Generic AgentDB `INSERT OR REPLACE` path used | Reject; use create-if-absent/CAS or signed publication. |
| Legacy in-memory queue used | Reject for resident work. |

## 12. Required Positive Scenarios

1. Discussion of GetK grounds the current FoundUp and code without dispatch.
2. A provider-adapter follow-up updates typed discussion state without authority.
3. `Have an agent audit the boundary` creates one immutable read-only proposal.
4. `Proceed` requests authorization for only the displayed digest; verified existing
   principal-signed policy authorization is required before entering the signed chain.
5. `What is it doing?` resolves canonical AgentDB status and signed receipt references.
6. `Do not change code` invalidates the old proposal and creates a new audit-only one.
7. A reload restores only authenticated scope/status references, not unrestricted raw
   chat as authority.

## 13. Exact Future Implementation Scope

Expected existing files to modify, subject to WSP 50 verification at implementation
time:

```text
extensions/reddog/extension.js
extensions/reddog/continuation_prompt.js
extensions/reddog/start_operations_extension_adapter.js
extensions/reddog/README.md
extensions/reddog/INTERFACE.md
modules/communication/moltbot_bridge/src/continuity_context.py
modules/communication/moltbot_bridge/src/reddog_resident_architect_client.py
modules/communication/moltbot_bridge/src/reddog_resident_architect_durable_agentdb_cycle.py
modules/communication/moltbot_bridge/src/reddog_architect_proposal_admission_contract.py
modules/communication/moltbot_bridge/src/reddog_architect_proposal_authenticity.py
modules/communication/moltbot_bridge/src/reddog_architect_proposal_runtime_authorization.py
modules/communication/moltbot_bridge/src/reddog_architect_fix_signed_wsp15_work_order_promotion.py
modules/infrastructure/database/src/agent_db.py
```

A small cohesive conversation-scope module may be added only if extending the listed
owners would violate WSP 62 or mix responsibilities. It must store through AgentDB and
must not become a parallel database or authority model.

Required tests:

```text
extensions/reddog/tests/verify_extension_contract.js
extensions/reddog/tests/test_continuation_prompt.js
modules/communication/moltbot_bridge/tests/test_reddog_resident_architect_client.py
modules/communication/moltbot_bridge/tests/test_reddog_resident_architect_durable_agentdb_cycle.py
modules/communication/moltbot_bridge/tests/test_reddog_architect_proposal_admission_contract.py
modules/communication/moltbot_bridge/tests/test_reddog_architect_proposal_authenticity.py
modules/communication/moltbot_bridge/tests/test_reddog_architect_fix_signed_wsp15_work_order_promotion.py
focused AgentDB CAS, replay, principal, scope, restart, and concurrent-update tests
```

Required receipts:

- conversation scope revision receipt;
- current grounding/freshness receipt;
- immutable proposal preview digest;
- existing principal-signed policy authorization bound to principal, conversation
  revision, proposal digest, and expected proposal payload;
- existing proposal authenticity and policy authorization receipts;
- existing signed WSP 15 work order;
- existing queue, claim, use, result-history, and independent-verifier receipts.

## 14. Implementation Handoff

### REDDOG_CONVERSATIONAL_SCOPE_AND_WORK_PROMOTION_PHASE1

Mission: concatenate existing RedDog conversation, resident intent, AgentDB, architect
proposal, WSP 15, WRE, and signed-worker owners into a safe multi-turn work-promotion
flow.

Build in the following validated order:

1. Correct history consent and telemetry. No UI state may claim prior context is off
   while provider history is attached.
2. Canonicalize `reddog_intent.v2` identity and reject identity alias conflicts.
3. Add AgentDB-backed, principal-bound, FoundUp-scoped conversation revisions using
   CAS and expiry.
4. Persist only scope, typed decisions, evidence references, active intent, and pending
   proposal references needed for continuity.
5. Resolve subjectless follow-ups only for discussion or proposal preparation; never
   dispatch from pronoun inference.
6. Extend the existing architect proposal payload with conversation revision,
   authoritative `foundup_id`, canonical intent digest, evidence freshness, and exact
   existing principal-signed policy authorization binding.
7. Treat `Proceed` as an authorization request only; require the existing verified
   principal-signed policy authorization before promotion.
8. Reuse Start Operations status reconnection and canonical AgentDB results to return
   progress to the conversation.
9. Route policy-authorized proposals only through the existing proposal authenticity, policy,
   signed WSP 15, WRE, AgentDB, and claim-time verification chain.

Phase boundary:

- Discussion and prepare-work modes may land first.
- Execute mode remains blocked until the existing principal-signed policy authorization
  verifies the exact preview digest and all production authority gates pass.
- No direct extension-to-provider effect, no new queue, no new signer, no HoloIndex
  mutation, no PatternMemory promotion, no automatic PR or merge authority.

Completion proof must include the positive scenarios and every negative case in this
audit, exact-SHA independent security review, focused differential tests, and no
regression of subject-complete fail-closed prompts.

## 15. Evidence Appendix

### Retrieval

Canonical owner query:

```text
query: RedDog conversation session continuation work proposal signed promotion
ok: true
freshness: CURRENT
index_gap_detected: false
authority_repo_head_sha: 4ae4cf81756a99ced3b0d0c1282a5eb576050594
freshness_generation_id: sha256:996d8a78555ebff6cb292ca7f7c78776df9a06cbfeaefcf6201def243f6d741a
query_receipt_id: sha256:1cc0297ed880eb46a4f746b1351d84a7a8c8d58618ba431ffaa64377aed1f782
no_holoindex_reindex_performed: true
```

The query surfaced the adjacent historical
`REDDOG_SESSION_CONTINUITY_CAPTURE_PHASE1` audit and current proposal/promotion
owners. Direct reads established that the historical audit is a manual closeout import,
not a live conversation contract.

### Validation

```text
node extensions/reddog/tests/verify_extension_contract.js
result: PASS (exit 0; existing post-pass Unicode traceback retained as harness noise)

python -m pytest -q
  test_reddog_resident_architect_client.py
  test_reddog_resident_architect_durable_agentdb_cycle.py
  test_reddog_architect_proposal_executability_admission.py
  test_reddog_architect_proposal_authenticity.py
  test_reddog_architect_fix_signed_wsp15_work_order_promotion.py
result: 106 passed in 24.08s

ASCII byte check: 0 non-ASCII
NUL byte check: 0
git diff --check: PASS
```

### Independent reviews

```text
Curie: extension conversation/continuation/session ownership review
Hypatia: AgentDB/WSP 109/WRE/OpenClaw/Hermes ownership review
Ramanujan: proposal/security trust-model review and final adversarial document review
```

The first final document review returned NO-GO with three major findings: approval
ambiguity, unauthenticated conversational FoundUp scope, and unsupported HoloIndex
diagnosis/evidence labeling. All three were corrected above. The fresh final review
returned `ALL_SAFE` and independently reproduced the canonical Holo owner result, 106
Python security tests, and the extension contract harness result.

CONVERSATIONAL_SCOPE_PARTIALLY_IMPLEMENTED
