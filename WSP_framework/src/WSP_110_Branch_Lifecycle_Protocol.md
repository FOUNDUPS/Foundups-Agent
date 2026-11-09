# WSP 110: Branch Lifecycle Protocol

**Status**: Draft pending validation
**Version**: 0.1
**Date**: 2026-11-10
**Author**: 0102 (architect role, WSP 00 locked)
**Origin**: external_principal (012)

---

## System roadmap navigation

After bootstrap, read [the root system roadmap](../ROADMAP.md#authority-and-fast-start) for completion gates, current planning priorities and the selected work packet. Follow its module and evidence links on demand. The roadmap owns cross-system sequencing; it does not redefine this protocol, certify completion, grant authority or replace a current signed work order.

---

## 1. Purpose

Branch lifecycle is a **runtime operations** concern, not a boot-time identity concern. It governs what happens after work starts — not what an agent wakes into. That separation is why this is WSP 110 and not an extension of WSP 00.

**Invariant**: 012 describes intent. 0102 and WRE own the full branch lifecycle — create, work, merge or retire, receipt. 012 never sees branch names. 012 sees receipts.

---

## 2. Creation Gate

A branch MUST NOT exist without:

1. A **WSP 15 allocation receipt** (Importance, Impact, Complexity, Deferability scored; priority P0-P4 assigned).
2. A **declared terminal state** chosen before the first commit:
   - `MERGE_TO_MAIN` — work converges to main via specialized PR
   - `STANDALONE` — work lives on its own branch/PR indefinitely (rare; requires explicit justification)
   - `EXPERIMENT` — exploratory; expected to retire without merge
3. A **named owner** (0102 role or module path) recorded in the PR description.

No branch without an exit plan. No orphan branches.

---

## 3. Naming Taxonomy

WSP 34 naming conventions remain authoritative. This protocol adds two mandatory fields:

- **Date suffix**: `YYYY-MM-DD` appended to every agent-spawned branch name.
- **Owner field**: stated in the opening line of the PR description, format `owner: <role or module path>`.

Example: `feat/wsp-110-branch-lifecycle-2026-11-10` with PR body starting `owner: 0102/architect`.

---

## 4. Hanging Branch Definition

A branch is **hanging** when any of the following hold:

1. No open PR exists for the branch.
2. No commit in **fourteen days**.
3. Its PR is closed without a merge and no superseding PR exists.

Hanging branches are auto-classified, not auto-deleted.

---

## 5. Classification Before Mutation

Before any hanging branch is touched, 0102 classifies it:

| Classification | Meaning | Action |
|---------------|---------|--------|
| `MERGED_VERIFIED_MAIN` | Merged; main contains the delta | Close ref with receipt |
| `SUPERSEDED_CLOSED` | Main demonstrably contains equivalent behavior; no unique delta | Close PR with reconciliation note, then close ref |
| `PARTIALLY_SUPERSEDED` | Main contains some delta; unique remainder exists | Preserve unique delta via fresh bounded reconciliation slice |
| `NEEDS_REBASE` | Unique valid delta, diverged from main | Rebase or recreate as fresh bounded slice |
| `BLOCKED_REQUIRED_GATE` | Valid delta blocked by failing/pending required check | Report blocker; do not force |
| `STILL_CURRENT` | Active owned work in progress | Leave untouched; report as active |
| `PRESERVED_NEEDS_REBASE` | Unique delta preserved for later routing | Ref retained with receipt |

**Rule**: never close or delete a branch solely because it is old or non-mergeable. Unique valid delta is preserved first.

---

## 6. Retirement Semantics

**Retirement never touches main.** It means:

- The branch ref is closed (deleted) with a terminal receipt.
- Any associated PR is closed with a classification note.
- All commits remain in git history — nothing is force-pushed, rebased onto oblivion, or garbage-collected by this protocol.
- If unique delta existed, it was routed through a WSP 97 reconciliation slice (Section 5) *before* retirement.

Retirement is **metadata cleanup**, not data loss.

The only path from branch to main is: validated branch → specialized PR → WSP 97 completion gate (Section 1.2A) → squash merge → main read-back verification.

---

## 7. 012 Interface

012 interacts with branch lifecycle exclusively through **receipts**:

- Work started (branch + WSP 15 receipt + terminal state)
- Work completed (merge SHA + verification status)
- Work retired (classification + preservation status)
- Work blocked (blocker + recovery path)

012 does not name branches, does not choose merge strategies, does not triage hanging refs. That is 0102/WRE's contract under this protocol.

---

## 8. Relationships

- **WSP 00**: Stack order and audit grounding (boot-time). WSP 110 is runtime.
- **WSP 34**: Git operations and naming taxonomy (parent).
- **WSP 97**: Completion gate, PR hygiene, convergence loop (Section 1.2A), preservation rule (rule 5).
- **WSP 15**: Allocation receipt required at creation.
- **WSP 22**: ModLog and receipt recording.
- **WSP 10**: State save and work closure (worktree cleanup adjacency).

---

## 9. Validation Plan

- Static: WSP 57 naming check on WSP_110 filename; WSP 50 pre-action verification on all mutations.
- Behavioral: apply classification table to current 130-branch inventory; produce receipt set.
- Regression: no existing WSP 34/97/10 clause contradicted.

---

## 10. Receipt Template

```
WSP_110_RECEIPT
branch: <name>
classification: <from Section 5 table>
terminal_state: <declared at creation>
wsp15_receipt: <id or path>
pr: <number or NONE>
main_sha_at_classification: <sha>
unique_delta_preserved: <YES/NO + route>
action_taken: <close_ref / close_pr / rebase / preserve / none>
verifier: 0102/<role>
date: <YYYY-MM-DD>
```
