# REDDOG_OPERATOR_LOOP_WARDROBE_SELECTION_CONTRACT_PHASE1

Status: SPECIFIED_NOT_IMPLEMENTED  
Slice type: docs/static contract only  
Authority: no runtime authority change  
WSP: 00, 15, 45, 50, 95, 97, 99

## Purpose

This contract defines how RedDog must select its operating posture before it reasons,
delegates, enqueues, writes, or asks for execution authority.

The canonical name is `operator loop wardrobe selection`.

Human shorthand such as `behavior skillz` is non-canonical. The WSP-native concept is
WSP_95 wardrobe selection: choosing the instruction set that tells an agent how to act.
The execution discipline comes from WSP_97: retrieve WSP, retrieve evidence, resolve the
execution plane, apply CoT/CoR, then act within the authorized plane.

This slice does not implement the selector. It freezes the contract that a later dry-run
module must emit before `REDDOG_EXTENSION_TO_LIVE_ENQUEUE_EXPLICIT_VALVE_INVOKE_PHASE1`
can safely consume RedDog output.

## Direct-read evidence (WSP_50)

OBSERVED:

- `WSP_knowledge/src/WSP_MASTER_INDEX.md` identifies WSP_00 as the foundation, WSP_95 as
  the Skill/Wardrobe protocol, and WSP_97 as the active operator-loop protocol.
- `WSP_knowledge/src/WSP_97_System_Execution_Prompting_Protocol.md` defines the practical
  loop: `HoloIndex -> Research -> Hard Think -> Dialectic Sweep -> First Principles ->
  Build -> Follow WSP`.
- `WSP_knowledge/src/WSP_95_WRE_SKILLz_Wardrobe_Protocol.md` defines a Skill as a
  task-specific instruction set telling an AI agent how to act, and a wardrobe as the
  collection of selectable Skills.
- `WSP_knowledge/src/WSP_45_Behavioral_Coherence_Protocol.md` supplies the adaptive
  resolution loop when selected posture and observed outcome diverge.
- `WSP_knowledge/src/WSP_15_Module_Prioritization_Scoring_System.md` defines the MPS
  priority scale used to order the resulting work queue.
- `docs/audits/architecture/REDDOG_OPERATOR_LOOP_WSP97_BINDING_PHASE1.md` already requires
  RedDog to run a WSP_97 operator loop before valve/write/handoff decisions.
- `extensions/foundups_advisory_workers/extension.js` already contains keyword-tiered
  routing for task tier, context mode, model mode, and effort.

INFERRED:

- The current extension routing is useful but not the same as WSP_95 wardrobe selection.
  It classifies prompts by patterns. It does not emit a durable receipt proving which WSP
  wardrobe was selected, what evidence was retrieved, what execution plane was chosen, or
  why a live enqueue path is allowed or forbidden.

## 1. Canonical wardrobe profiles

The selector must choose exactly one `selected_wardrobe` value:

| selected_wardrobe | Intended use | Default execution plane |
| --- | --- | --- |
| `wsp97_solo_retrieval` | Simple exploration, repo orientation, current-state questions, low-risk explanation | `advisory_only` |
| `wsp97_architect_audit` | Architecture, security, governance, authority, public-surface, or cross-lane decisions | `audit_only` |
| `wsp97_implementation_slice` | Scoped code/doc/test work that can produce a branch, tests, and a draft PR | `worker_draft_pr` |
| `wsp97_sovereign_execution` | Live enqueue, shell, worktree writer, merge, reward, or other authority-bearing work | `governed_execution_candidate` |

Selection must be deterministic for the same normalized work focus and the same evidence
state. If multiple profiles match, the selector must choose the most restrictive profile
that can still answer the work:

1. `wsp97_sovereign_execution`
2. `wsp97_implementation_slice`
3. `wsp97_architect_audit`
4. `wsp97_solo_retrieval`

This priority is a safety rule, not a cost optimization rule.

## 2. Selection inputs

The selector input is the normalized work focus plus observed evidence state:

| Field | Required | Source |
| --- | --- | --- |
| `work_focus_digest` | yes | Canonical digest of the 012 work focus after Unicode normalization |
| `principal_ref` | yes | Caller identity reference; role text alone is never authority |
| `current_lane_refs` | optional | Work ledger, active slice ledger, PR list, or continuation packet |
| `holoindex_query_digest` | yes for repo work | Digest of HoloIndex query text and top-hit metadata |
| `holoindex_freshness_label` | yes for repo work | `fresh`, `stale`, `unknown`, or `index_gap` |
| `required_targets` | optional | Explicit targets from prompt or derived work-focus paths |
| `target_recall_ok` | yes when required targets exist | Direct-read/HoloIndex recall score |
| `wsp_refs` | yes | Candidate governing WSP ids |
| `authority_request` | yes | `none`, `draft_pr`, `live_enqueue`, `worktree_write`, `shell`, `merge`, `reward` |
| `continuation_packet_digest` | optional | Sanitized RedDog continuation packet digest |

Repo-sensitive work must have a HoloIndex query result before selection. Direct-read may
repair missing evidence for named files, but it must not silently clear an INDEX_GAP.

## 3. Selection output receipt

Future runtime must emit `RedDogOperatorLoopWardrobeSelectionReceipt`.

Required fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `selection_id` | string | Deterministic digest of normalized input and selected output |
| `work_focus_digest` | string | Digest bound to the 012 work focus |
| `selected_wardrobe` | enum | One of the four canonical wardrobe profiles |
| `wsp97_depth` | enum | `solo`, `audit`, `implementation`, `sovereign` |
| `selected_context_mode` | enum | Current RedDog context mode or future equivalent |
| `selected_model_mode` | enum | Current RedDog model/fusion mode or future equivalent |
| `selected_effort` | enum | Current effort value or future equivalent |
| `execution_plane` | enum | `advisory_only`, `audit_only`, `worker_draft_pr`, `governed_execution_candidate` |
| `wre_required` | bool | True when WRE must own the next action |
| `authority_boundary` | enum | `no_authority`, `draft_pr_only`, `signed_valve_required`, `sovereign_token_required` |
| `holoindex_query_digest` | string | Digest of query evidence |
| `holoindex_freshness_label` | enum | `fresh`, `stale`, `unknown`, or `index_gap` |
| `index_gap_detected` | bool | True if semantic index misses material targets |
| `direct_read_required` | bool | True when named paths must be read before claims |
| `skillz_candidates` | list[string] | WSP_95 wardrobe candidates considered |
| `lane_refs` | list[string] | Existing PR/slice/ledger references considered |
| `rejection_reasons` | list[string] | Fail-closed reasons, if any |
| `no_execution_performed` | bool | Always true in dry-run selector output |
| `no_enqueue_performed` | bool | Always true in dry-run selector output |
| `implementation_status` | enum | `SPECIFIED_NOT_IMPLEMENTED` until a runtime module exists |

The receipt is advisory until a later slice signs or consumes it. It is not authority by
itself.

## 4. WSP_97 decision rules

The selector must answer these questions before any live queue or worker invocation:

1. What WSP governs this work?
2. What evidence proves the premise?
3. What is the authority scope?
4. Which execution plane is allowed?
5. What invariant would make the work impossible or unsafe?

Fail-closed rules:

- If governing WSP cannot be derived for repo-changing work, choose
  `wsp97_architect_audit` or reject live authority.
- If HoloIndex reports `index_gap` on write-sensitive work, live authority is rejected
  until WRE/CI freshness work records a resolution or direct-read evidence is explicitly
  accepted for that slice's scope.
- If a prompt requests shell, live enqueue, worktree write, merge, reward, or worker
  orchestration, select `wsp97_sovereign_execution` and require signed authority plus the
  matching valve path.
- If evidence is unavailable, use WSP_97 labels such as `NEEDS_VERIFICATION`; do not
  claim OBSERVED.

## 5. HoloIndex and freshness boundary

HoloIndex is a selection input, not a mutation target.

Rules:

- RedDog runtime may query HoloIndex.
- RedDog runtime must not re-index HoloIndex.
- WRE/CI owns re-indexing, freshness receipts, and incremental per-FoundUp maintenance.
- The selector records `index_gap_detected` rather than discarding it when direct-read
  succeeds.
- A material INDEX_GAP on write-sensitive work is routed to a WRE/CI maintenance item,
  not solved by RedDog self-mutation.

This preserves the evidence substrate. RedDog cannot safely decide authority while
mutating the index that supplies its evidence.

HoloIndex probe for this slice:

- Query: `RedDog operator loop wardrobe selection contract`
- Observed result: WSP_95 and prior operator-loop/security docs surfaced, but this new
  contract did not surface in the returned top hits.
- Recorded follow-up: `HOLOINDEX_REDDOG_OPERATOR_LOOP_WARDROBE_SELECTION_CONTRACT_INDEX_GAP_PHASE1`.

## 6. Relationship to live enqueue

`REDDOG_EXTENSION_TO_LIVE_ENQUEUE_EXPLICIT_VALVE_INVOKE_PHASE1` must not treat raw model
text as sufficient to invoke the live enqueue seam.

It must require, at minimum:

- An accepted work-order authority path where required.
- An accepted signed receipt-chain path where required.
- A valve state that matches the requested authority.
- A `RedDogOperatorLoopWardrobeSelectionReceipt` whose `execution_plane` permits the
  requested next action.
- No fail-closed `rejection_reasons`.

If the selector emits `advisory_only` or `audit_only`, live enqueue is forbidden even if
the prose answer recommends work.

This slice does not invoke live enqueue and does not wire the extension to live enqueue.

## 7. WSP_15 prioritization

Immediate sequence:

1. `REDDOG_OPERATOR_LOOP_WARDROBE_SELECTION_DRYRUN_PHASE1`
2. `REDDOG_EXTENSION_TO_LIVE_ENQUEUE_EXPLICIT_VALVE_INVOKE_PHASE1`
3. `REDDOG_GENERIC_AGENT_WORKTREE_WRITE_SPINE_CONTRACT_PHASE1`
4. `REDDOG_GENERIC_AGENT_WORKTREE_WRITER_DRYRUN_PHASE1`
5. `REDDOG_WRE_GOVERNED_SHELL_RUNNER_CONTRACT_PHASE1`
6. `REDDOG_WRE_GOVERNED_SHELL_RUNNER_DRYRUN_PHASE1`
7. `REDDOG_MERGE_AUTHORITY_CONTRACT_PHASE1`

Rationale:

- The wardrobe selector is the missing precondition for self-deterministic mode selection.
- Live enqueue can only be safely invoked after RedDog proves which execution plane it
  selected and why.
- Generic worktree, shell, and merge authority must remain downstream of the selector,
  signed authority, valves, receipt chain, and WRE cwd/worktree guards.

## 8. WSP_97 truth table

| Claim | WSP_97 label | Evidence |
| --- | --- | --- |
| RedDog currently has keyword-tier routing for context/mode/effort | OBSERVED | `extension.js` routing helpers |
| WSP_95 already defines Skillz/Wardrobe as how an agent acts | OBSERVED | `WSP_95_WRE_SKILLz_Wardrobe_Protocol.md` |
| WSP_97 already defines the operator loop RedDog must follow | OBSERVED | `WSP_97_System_Execution_Prompting_Protocol.md` |
| `behavior skillz` is a human shorthand, not a canonical protocol term | INFERRED | WSP-native terminology uses Skillz/Wardrobe and operator loop |
| A durable wardrobe-selection receipt exists in runtime | SPECIFIED_NOT_IMPLEMENTED | This contract only defines it |
| Extension-to-live-enqueue invocation consumes this selector | SPECIFIED_NOT_IMPLEMENTED | Future slice |
| RedDog may self-reindex HoloIndex during selection | FALSE | This contract forbids runtime re-index |

## Explicit non-goals

- No new WSP.
- No runtime selector implementation.
- No `extension.js` change.
- No OpenClaw live enqueue.
- No WRE shell or worktree write.
- No git, PR, push, or merge authority.
- No HoloIndex re-index.
- No signing, key generation, reward settlement, or wallet path.

## Truth Boundary Checklist

- DOCS_ONLY: YES
- NO_RUNTIME_CODE: YES
- NO_EXTENSION_CHANGE: YES
- NO_LIVE_ENQUEUE: YES
- NO_WORKTREE_WRITE: YES
- NO_SHELL: YES
- NO_MERGE_AUTHORITY: YES
- NO_HOLOINDEX_REINDEX: YES
- WSP_97_LABELS_USED: YES
- SPECIFIED_NOT_IMPLEMENTED_EXPLICIT: YES
