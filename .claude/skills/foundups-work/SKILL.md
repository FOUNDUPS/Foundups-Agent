---
name: foundups-work
description: Apply the FoundUps work skill before starting, switching, resuming, or closing repository work. Use it to audit dirty lanes, recover dropped work, reconcile ownership and current relevance, apply WSP 15 and WSP 97, and leave a clean truthful handoff.
---

# Apply the FoundUps work skill

Treat task switching as a state transition, not a new blank session. The work is not admitted until the current lane and visible unfinished lanes have been reconciled.

## Admission

1. Execute WSP 00, then read canonical WSP 15, WSP 97, repository instructions, the current roadmap, and recent session briefings.
2. Run `python -B scripts/foundups_work_preflight.py --repo-root <current checkout> --json`. This is read-only evidence, not cleanup authorization.
3. Query governed HoloIndex for the requested task and likely prior slice. Evaluate retrieval noise, ordering, missing artifacts, staleness, and duplication. If HoloIndex fails closed, preserve the error and use direct repository evidence without reindexing.
4. Read the work-ledger schema/projection and relevant ROADMAP, ModLog, TestModLog, branch, worktree, PR/CI, TODO, and deployment evidence. Repository state outranks conversational memory.
5. Classify each relevant lane or dirt set as `CURRENT`, `RELATED_CONTINUE`, `PARK`, `CLOSE`, `SUPERSEDED`, `SALVAGE`, `BLOCKED`, `EXTERNALLY_OWNED`, `EVIDENCE_UNAVAILABLE`, or `NEEDS_012_DECISION`.
6. Apply canonical WSP 15 only to eligible unresolved work. A high score does not override ownership, dependencies, safety, or authority.
7. Admit the smallest executable slice in an owned clean worktree. Never reset, stash, clean, switch, delete, merge, commit, or rewrite another lane to manufacture cleanliness.

Current-lane dirt may continue only when file-level evidence shows it belongs to the requested slice and its ownership is explicit. Otherwise park it with branch/worktree, exact state, blocker, and next executable step before changing lanes.

## 012 engagement

Continue autonomously for reversible, clearly owned work. Ask 012 one concrete question before destructive disposition, conflicting ownership, strategic scope change, or when unique work may be discarded. Show the lane, evidence, options, consequence, and recommendation. Do not ask 012 to resolve facts available in the repository.

## Closure

Before leaving a task, validate the focused change, inspect final Git state, update required ModLogs/TestModLogs and existing ledger/roadmap evidence, and classify the slice as `CLOSED`, `PARKED`, `BLOCKED`, `SUPERSEDED`, or still `IN_PROGRESS`. Record exact branch, worktree, HEAD, dirty state, tests actually run, external status actually observed, blocker, and next step.

Run the preflight again after completion or blockage. A task is not cleanly handed off when unique work exists only as unexplained dirt, when documentation claims unverified completion, or when the next step cannot be recovered without conversational memory.

## Truth boundary

The scanner reports Git facts and conservative disposition candidates. It does not prove ownership, usefulness, merge equivalence after squash, PR/CI state, deployment state, or authorization. Verify those separately. `RETIRE_CANDIDATE` always requires content/ownership review before removal.
