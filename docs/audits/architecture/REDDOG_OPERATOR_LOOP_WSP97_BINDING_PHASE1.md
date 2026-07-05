# REDDOG_OPERATOR_LOOP_WSP97_BINDING_PHASE1

**Type:** Decision / contract ONLY. No code implemented. No WSP framework file edited yet. No live authority change. No PR opened by this slice.
**Author:** 0102 (RedDog Architect) | Commander: 012
**WSP:** 00, 15, 50, 97 (method + subject); 48, 67, 54, 96, 64 (governing).
**Base:** `4094ed58e` (main; #925 merged implementation-only).
**Date:** 2026-07-05
**Sequence position:** B (after A = prove #925 narrow FoundUp live writer; before C = spoofing threat model).

---

## 0. Purpose

Specify the binding that makes RedDog **run the WSP 97 operator loop autonomously and code-enforce it as a precondition** at the start of every work order -- before any valve open, write, or handoff. Today the loop is protocol-described (WSP 97) and performed out-of-band by human-0102; RedDog only **passively validates** caller-attached WSP evidence. This slice defines the transition to **active derivation** plus a mandatory 5-question preamble receipt chain. It is the foundational primitive that must precede a generic writer: *a RedDog that can write but does not first derive the governing WSP will execute the wrong policy* -- the exact spoofing/authority failure to prevent.

**This slice writes a contract only.** Implementation (active-derive + receipt enforcement) is a later slice; the WSP 97 edit is proposed here, not applied.

## 1. Governing WSPs (WSP preflight)

- **WSP 97** -- System Execution Prompting. Already defines the loop `retrieve wsp -> retrieve evidence -> resolve execution plane? -> apply cot -> apply cor -> execute` and states "retrieve governing WSPs and evidence first" (WSP_97 lines 101, 160-176). The 5 questions are this loop **made mandatory + code-enforced for RedDog**, not a new invention.
- **WSP 48 / 67** -- Recursive Self-Improvement / Anticipation. The preamble is where "is this loop efficient / what is missing" hooks attach later.
- **WSP 54** -- Agent Duties. The authority-scope question is a WSP 54 duty determination.
- **WSP 96** -- Governance & Consensus. The authority-scope tiering (token vs consensus) resolves here when 012 leaves the loop.
- **WSP 64** -- Violation Prevention. **This slice EXTENDS WSP 97 (a new binding subsection); it does NOT mint a new WSP.**

## 2. As-built truth (OBSERVED) -- why the binding is needed

- OBSERVED: `reddog_governed_work_order_dryrun.py:404-417` -- for a write-sensitive operation the gate requires `holo.applicable_wsps` OR `holo.wsp_hits` to be non-empty and rejects on `INDEX_GAP` / weak recall. But `holo` is `work_order.holoindex_evidence` -- a **caller-supplied** object. RedDog **validates that WSP evidence was attached; it never derives it.**
- INFERRED: if human-0102 (who attaches `applicable_wsps`) is removed "from the loop" as intended, the derivation vanishes and the gate degenerates to "was a non-empty list supplied" -- trivially spoofable by a caller asserting any WSP.
- OBSERVED: the live writer (`foundup_scaffold_writer_live.py`) is an ORPHAN leaf with no autonomous caller; nothing runs the WSP-ask loop before invoking it.
- SPECIFIED_NOT_IMPLEMENTED: an executable "which WSP governs this / am I following WSP" step that PRODUCES a governing-WSP receipt gating the rest of the chain.

## 3. The OperatorLoopPreamble contract (the 5 mandatory questions)

Every RedDog work order MUST, before execution, produce a **preamble** of 5 receipts. Each is **active-derived by RedDog** (not read from the caller), digest-bound to the `work_order_id`, and the chained `preamble_digest` becomes a **required input to the execution valve** (a new gate: no valve open without a valid preamble bound to the same work order).

| # | Question | Derivation (active, by RedDog) | Receipt | Gates / fail-closed |
|---|----------|-------------------------------|---------|---------------------|
| 1 | **What WSP governs this?** | RedDog runs HoloIndex + `wsp_protocol_lookup` on the task text and DERIVES `applicable_wsps`; compares to any caller-attached list -- **mismatch or caller-only = FAIL**. | `governing_wsp_receipt` (derived_wsps[], query, retrieval_quality, index_gap flag, derivation_source=REDDOG) | `FAIL_WSP_NOT_DERIVED` / `FAIL_WSP_CALLER_ASSERTED_ONLY` / `FAIL_WSP_INDEX_GAP` (write ops) |
| 2 | **What repo evidence proves it?** | Direct-read the governing targets; record path + content digest (CoT retrieve-evidence). No inference from filenames. | `evidence_receipt` (targets[], digests[], needs_verification[]) | `FAIL_EVIDENCE_MISSING` / `FAIL_EVIDENCE_UNVERIFIED` |
| 3 | **What authority scope applies?** | Determine the authority TIER (single sovereign token vs N-of-M consensus) and the DERIVED allowed/denied path scope from the governing WSP + operation -- **never read scope from the caller packet**. **`operation` is itself caller-influenced, so it MUST be normalized and validated against the derived WSP set (an operation the derived WSP does not govern = FAIL), else scope is caller-steered one level removed.** | `authority_scope_receipt` (tier, derived_allowed_root, denied_set, principal_id*) | `FAIL_AUTHORITY_TIER_UNMET` / `FAIL_SCOPE_CALLER_SUPPLIED` / `FAIL_OPERATION_NOT_GOVERNED` |
| 4 | **What execution plane am I in?** | Classify the plane (dry_run / observe / propose / write / draft_pr) per WSP 97's "resolve execution plane?" decision gate; WRE only if actually required. **NOTE (WSP 64): this gate is ALREADY code-realized in the valve spine -- Q4 binds to it, it is not a novel derivation. The 5-value taxonomy is a RedDog refinement of WSP 97's plane gate, labelled as such.** | `execution_plane_receipt` (plane, wre_required: bool, justification) | `FAIL_PLANE_UNCLASSIFIED` / `FAIL_PLANE_ESCALATION` (plane > authorized) |
| 5 | **What must remain impossible?** | Declare the negative space: the invariants this work order may NEVER violate (no main/registry/WSP-framework/CI/secrets mutation w/o separate auth; no self-authorization; no self-promotion). | `invariant_receipt` (forbidden[], self_authorization_forbidden=true) | `FAIL_INVARIANT_UNDECLARED` / `FAIL_INVARIANT_VIOLATED` (checked again at write) |

**Preamble binding:** `preamble_digest = digest([work_order_id, normalized_operation, derived_allowed_root, denied_set, governing_wsp_receipt, evidence_receipt, authority_scope_receipt, execution_plane_receipt, invariant_receipt])`. Binding to the **realized** `(operation, allowed_root, denied_set)` -- not `work_order_id` alone -- so a post-derivation retarget of scope/operation within the same work order **breaks the bind** (closes the TOCTOU the CoR sweep flagged). The execution valve (`evaluate_reddog_execution_valve`) gains a required input: reject unless a preamble whose `preamble_digest` matches the concrete operation+target the valve is about to authorize is present. **`derivation_source == REDDOG` is a provenance LABEL, not an authenticity guarantee (see 5A); the valve MUST NOT treat the label as authority until slice D binds it to a signature RedDog cannot mint.**

## 4. Active-derive vs passive-validate (the core change)

- Transform `reddog_governed_work_order_dryrun.py:404-417` from **validate caller-attached `holoindex_evidence`** into **derive-then-compare**: RedDog runs the retrieval itself, produces `governing_wsp_receipt`, and if a caller also supplied `applicable_wsps`, the two must AGREE (caller cannot ADD a WSP RedDog did not derive, nor DROP one it did).
- Question 3 mirrors the generic-spine audit's blocker fix: **authorized scope is RE-DERIVED, never caller-supplied** -- closing the "caller-supplied allowed_paths deletes containment" hole before any generic writer exists.
- Question 5 is the truth-boundary/negative-space declaration; it is re-checked at the write boundary (defense-in-depth), so a preamble that omits an invariant fails closed rather than silently permitting.

## 5. Integrity vs authenticity -- the honest claim boundary

A CoR sweep of this contract (4 lenses, 9 blocker / 11 major design findings) established a truth this slice MUST state plainly: **in the single-party, 012-out-of-loop world where RedDog is both deriver and caller, the preamble mechanisms provide INTEGRITY, not AUTHENTICITY.** They are tamper-evidence between components; they are NOT proof that RedDog behaved honestly. The contract does NOT overclaim otherwise.

| Mechanism | What it PROVIDES (this slice) | What it does NOT provide |
|-----------|------------------------------|--------------------------|
| `derivation_source == REDDOG` | a provenance LABEL | authenticity -- the same process that assembles the work order sets the label; forgeable until slice D signs it |
| `preamble_digest` chaining | tamper-evidence: components cannot be swapped after chaining | any evidence the receipt CONTENTS are true; a self-improving RedDog can produce a fully consistent, honestly-chained, entirely self-asserted preamble |
| derive-then-compare (caller vs derived) | a cross-check WHEN an independent caller list exists | anything in the single-party case: with 012 gone and one process, the compare is **INERT** (no adversarial second list) -- assurance reduces to oracle-independence (5A) + external signature (slice D) |
| plane non-escalation | a cap IF the valve consumes it | protection while the plane is self-classified by the same actor -- the cap is real only once the valve enforces `plane <= authorized` |

**Therefore the authenticity guarantee of the RedDog operator loop reduces to: (a) an oracle RedDog cannot poison (5A) AND (b) a signature RedDog cannot mint (slice D).** This slice specifies the loop shape, the derive-not-trust rule, the protected oracle, and the permanent invariants; it deliberately DEFERS the signature scheme to slices C/D and forbids the valve from trusting an unsigned stamp in the interim.

## 5A. The derivation oracle is a PROTECTED surface

"Active-derive" is only stronger than "passive-validate" if the derivation source is **independent of the deriving agent**. The sibling audit confirms it is not yet: `_HARD_DENIED_MARKERS` omits `holo_index` config, and the WSP index / `wsp_protocol_lookup` sources are writable by the agents being governed. Contract requirements (named preconditions, implemented in later slices):

- The derivation oracle -- HoloIndex config/data, the WSP index, and `wsp_protocol_lookup` sources -- is a **pin-independent governance-denied surface**: no RedDog work order may target it for write.
- RedDog **may not derive-and-execute in the same authority context that can mutate the index** (separation of the retrieval substrate from the writing substrate).
- **INDEX_GAP on a write-op governance derivation is FAIL-CLOSED with NO agent-supplied direct-read substitution.** Any direct-read fallback is itself scope-limited to WSP-framework paths RedDog cannot write (else the fallback re-opens the poisoning vector that INDEX_GAP was meant to close).

## 5B. Permanent system invariants (not per-work-order declarable)

Question 5's per-work-order `invariant_receipt` is necessary but insufficient: a self-improving RedDog can **under-declare** it. This slice therefore specifies a set of **PERMANENT, system-level invariants** enforced independently of any receipt a work order authors -- the things a continuously-running RedDog may NEVER do, regardless of what its preamble claims:

1. **No self-modification of the governance path:** may not write the preamble/derivation logic, the valve/gate source, `reddog_wre_execution_valve.py`, `reddog_governed_work_order_dryrun.py`, or the operator-loop enforcer.
2. **No self-serving WSP rewrite:** may not, in the same loop, edit the WSP it derived governance FROM.
3. **No preamble replay:** each `preamble_digest` is single-use, bound to a nonce/monotonic counter; a previously-accepted preamble cannot re-authorize a new execution.
4. **No self-consensus:** the deriving instance may not be a signer/voter in its own N-of-M authority quorum (anti-self-approval; anti multi-instance collusion of the same principal).
5. **No receipt/ledger disablement:** may not disable, truncate, or bypass the receipt chain it is judged by.
6. **No derivation-substrate mutation:** may not write the HoloIndex/WSP-index/lookup sources (restates 5A as an invariant).
7. **No self-promotion:** may not mark-ready or merge its own draft PR; promotion requires 0102-architect WSP_97 evidence OR a DAO vote -- never the loop.

These are declared here as contract; their enforcement (a fixed denylist + a signer-identity check) lands with slices C/D, before any generic writer.

## 5C. Bind the derived WSP to the ACTUAL work

The preamble derives `applicable_wsps` from task TEXT; nothing yet checks that the work actually performed falls under that governance. A work order can derive WSP-X from benign text then touch a WSP-Y domain -- a policy-substitution spoof that passes every stamp. Contract requirement:

- Add a **governance-coverage** re-validation at the write boundary: every path in the realized allowed scope MUST map to a domain the derived WSP set actually governs, else `FAIL_WSP_WORK_MISMATCH`.
- `governing_wsp_receipt` is re-checked against the concrete `(operation, target paths)` at write time, not only against task text at preamble time.

## 6. Truth boundaries + reconciliation with as-built (WSP 64)

- OBSERVED: WSP 97 already specifies the loop AND already has the `resolve execution plane?` gate (lines 101, 160-176) plus Annex A "High-Risk Assumption Audit Gate" (SPEC_ONLY, lines 515-608) -- Q4 and Q5 BIND to these, they are not novel. The governed-work-order gate passive-validates caller WSP evidence (`:404-417`); INDEX_GAP / weak-recall write-blocking already exists there AND in the valve (so the binding must EXTEND, not duplicate). The live writer is an orphan leaf; the valve re-derives state via `_resolve_valve_state(env,[])` (`foundup_scaffold_writer_live.py:234`).
- INFERRED: removing human-0102 without active derivation degenerates the WSP gate to a presence check; but active-derive alone does NOT fix it in a single-party world -- only oracle-independence (5A) + a signature RedDog cannot mint (slice D) restore authenticity. Scope re-derivation + operation-governance validation + the work-to-WSP binding (5C) pre-empt the generic-writer containment blocker.
- SPECIFIED_NOT_IMPLEMENTED (all later slices; none built here): the active-derive step; the 5 receipt schemas; `preamble_digest` bound to realized operation+scope as a valve input; the governance-coverage write-boundary check (5C); the protected-oracle denylist + fail-closed INDEX_GAP (5A); the 7 permanent system invariants (5B); and the WSP 97 binding subsection edit. **The signature/authenticity layer is explicitly deferred to slices C/D; the valve must not trust the unsigned `REDDOG` label until then.**

## 6A. What this slice provides vs defers

- **PROVIDES (as contract, this slice):** the loop shape; the derive-not-trust rule; the protected-oracle requirement; the permanent-invariant set; the work-to-WSP binding rule; the honest integrity-vs-authenticity boundary.
- **DEFERS (slices C/D, before any generic writer):** principal identity + delegation signatures; the signer-not-held-by-RedDog key; N-of-M consensus enforcement; the valve trusting a derivation as authority.
- **DOES NOT (this slice):** claim authenticity from self-asserted stamps; ship a valve field that authorizes on an unsigned label; implement anything.

## 7. Recommended sequence + verdict

Verdict: **AUTHOR_DECISION_CONTRACT_NOW; IMPLEMENT_LATER.** Confirms 012's re-prioritization: the operator-loop binding precedes the generic writer. This contract was hardened by a 4-lens adversarial CoR sweep (9 blocker / 11 major DESIGN findings) whose core result -- self-asserted stamps give integrity, not authenticity, in a single-party world -- is now folded into sections 5, 5A-5C, and 6A. The sweep also VALIDATED the dependency order: because B cannot provide authenticity alone, C (threat model) and D (principal identity + signatures) MUST precede E (generic writer).

```
A. #925 narrow FoundUp live writer proof          (RUN_LIVE_WRITER_PACCESS_001_PHASE1)
B. REDDOG_OPERATOR_LOOP_WSP97_BINDING_PHASE1       (THIS doc -- decision/contract)
C. REDDOG_IDENTITY_SPOOFING_AND_DELEGATION_THREAT_MODEL_PHASE1
D. REDDOG_PRINCIPAL_IDENTITY_AND_DELEGATION_CONTRACT_PHASE1
E. REDDOG_GENERIC_AGENT_WORKTREE_WRITE_SPINE_CONTRACT_PHASE1
F. generic agent_worktree_writer implementation    (later; gated on B-E)
```

Next after this contract: **implement Question 1 first** (active WSP derivation + `governing_wsp_receipt`) as the smallest layer, dry-run, before wiring the other four -- layer-by-layer per WSP 27/30 discipline.

## 8. Out of scope (this slice)

Implementing any of the 5 receipts; editing WSP 97; modifying #925 or the valve; running the live writer; adding Skillz; changing execution authority; re-indexing; specifying the delegation signature scheme (slices C/D).

---

*Hard rule (restated): RedDog must not become broadly capable before it code-enforces "what WSP governs this / what evidence proves it / what authority scope applies / what execution plane am I in / what must remain impossible" -- ACTIVE-DERIVED against a PROTECTED oracle, bound to the ACTUAL work, and (for authority) SIGNED by a key RedDog cannot mint. A self-asserted stamp is integrity, not authenticity; generic capability without derived-and-signed governance is authority spoofing waiting to happen.*
