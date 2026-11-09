# WSP 110: Branch Lifecycle Protocol

**Status**: Draft pending validation
**Version**: 0.2
**Date**: 2026-11-10
**Author**: 0102 Segunda (initial draft); 0102 Prima (authorized continuation)
**Origin**: external_principal (012)
**Scope**: Operator lifecycle contract; automatic runtime enforcement is not established

---

## System roadmap navigation

After bootstrap, read [the root system roadmap](../../ROADMAP.md#authority-and-fast-start) for completion gates, current planning priorities and the selected work packet. The roadmap owns sequencing; it does not redefine this protocol, certify completion, grant authority or replace a current work order.

## 1. Purpose and activation

WSP 00 makes outstanding branch/PR obligations visible at **every repository boot**. WSP 110 organizes their lifecycle; WSP 97 supplies the investigation and completion gates. This protocol operationalizes, rather than replaces, WSP 10 preservation/closure and WSP 97 section 1.2A main convergence. A new protocol number is not a new permission or a new backlog system.

**Invariant:** 012 describes intent. The assigned 0102 lane owns follow-through. WRE coordinates admitted autonomous/distributed work. GitHub, CI, review and deployment authorities remain separate. A direct connector audit or documentation change must not be described as a WRE-dispatched execution.

012 should receive concise outcomes, blockers and receipts rather than have to operate GitHub. Branch names and full evidence remain available for inspection; this protocol does not restrict the principal's visibility or control.

```text
Boot -> Discover -> Assign -> Reconcile -> Verify -> Remember -> Resume
```

### 1.1 Boot and resume contract

1. **Boot:** complete the applicable WSP 00 bootstrap/role contract. Retrieve WSP 97, this protocol and applicable WSP 10/15/34/50 prerequisites **before** investigation or mutation. Dependency order, not ascending WSP number, governs loading.
2. **Discover:** read the existing outstanding-work record, then refresh repository evidence. Reuse [the backlog reconciliation record](../../docs/audits/architecture/OPEN_PR_BACKLOG_DISPOSITION_AUDIT_PHASE1.md) and [issue #2122](https://github.com/FOUNDUPS/Foundups-Agent/issues/2122). Neither is a live inventory merely because it exists. Inventory branches separately from PRs, follow pagination, and record inaccessible or partial coverage as UNKNOWN.
3. **Assign:** resolve owner, role, authorized scope, dependencies and existing claim/lease before acting. Select the next eligible obligation under WSP 15. Preserve another lane's active work. A model/shard name is attribution, not authority.
4. **Reconcile:** compare exact source/head/base and current main. Investigate with WSP 97, preserve unique work, and advance the owned slice. Creating a PR or rewriting the same queue is not completion.
5. **Verify:** use current required checks/reviews on the exact accepted revision, then verify resulting main where a merge was authorized. Missing, stale, pending or inaccessible checks are UNKNOWN/BLOCKED, not PASS. Keep deployment and live-runtime verification separate.
6. **Remember:** retain disposition, evidence and unfinished obligations in the existing work record and scoped continuity memory. Memex/Breadcrumb/HoloIndex projections support retrieval; they cannot overrule current GitHub/source evidence or grant mutation rights.
7. **Resume:** continue eligible owned work in the current session; carry unresolved work forward with a named owner, next action and recheck condition. The next boot retrieves it. A recorded queue is a checkpoint, not a terminal receipt for its items.

Every boot must produce a source-bound lifecycle receipt or an actionable outstanding-work queue. If GitHub, native runtime, admission or local-worktree visibility is unavailable, record the actual limitation and recovery path. Block the affected action, not unrelated authorized work. Do not claim a complete inventory from an empty/failed query.

Delegated workers may inherit a current, source-bound inventory reference and inspect their assigned slice instead of launching competing full-repository sweeps. Revalidate head/ownership immediately before mutation. Admission, concurrency controls and a scheduled caller must be independently verified before claiming the loop operates automatically.

## 2. Creation and continuation gate

Before creating an agent-owned branch, record:

1. A **WSP 15 allocation receipt** with Complexity, Importance, Deferability, Impact and priority.
2. Intended destination: `MERGE_TO_MAIN`, justified `STANDALONE`, or `EXPERIMENT`. A destination is not a completion result. Standalone and experimental branches still need an owner and review condition.
3. Named lane/agent owner, role, task/work-order reference, base SHA, scope and recovery plan in the existing work record; link it from the PR when one exists.

WSP 34 naming remains authoritative. A date suffix is useful for new agent branches, but this protocol does not require renaming existing branches or breaking dependent PRs. Do not invent creation receipts for legacy branches; mark missing records UNKNOWN and reconcile them.

### 2.1 Cross-shard handoff

A continuation records `previous_owner`, `accepting_owner`, exact `head_sha`, authorized scope and the principal/owner handoff reference. Prima and Segunda remain distinct lanes even though both use the 0102 designation. No overwrite, reset, rebase or duplicate PR against another active lane merely because both agents can access the repository.

Use existing shared owner/lease mechanisms where admitted. Where no atomic lease is available, explicitly coordinate the handoff, re-read the ref before writing, and use an expected-head/non-force update. A changed head invalidates the proposed mutation: stop that mutation, retrieve the new work and reconcile. Do not invent a successful lease.

## 3. Review triggers, not deletion triggers

A branch becomes a **review candidate** when an owner/exit plan is absent, a closed unmerged PR lacks disposition, dependencies have changed, or there has been no commit for **fourteen days**. Last-commit age is only a triage signal: also inspect review activity, blockers, owner status and intentional maintenance/release use.

No PR is not proof of abandonment. Default/protected/release branches, justified long-lived branches, active worktrees and other agents' branches require their own ownership rules. They are never deletion candidates merely because they match a name or age threshold.

Do not hard-code a historical branch count. Timestamp the actual inventory, preserve page/coverage evidence, and distinguish live findings from prior snapshots.

## 4. Classification before mutation

| Classification | Evidence required | Next action |
|---|---|---|
| `ACTIVE_OWNED_WORK` | Current owner and next action established (`STILL_CURRENT` in older records) | Continue owned work; preserve another lane |
| `BLOCKED_REQUIRED_GATE` | Named required gate or evidence/authority gap | Record recovery action and recheck condition; no bypass |
| `NEEDS_REBASE` | Unique valid work remains and base has diverged | Plan authorized reconciliation; do not rewrite an active lane |
| `PARTIALLY_SUPERSEDED` | Main contains some, but not all, valid work | Preserve and reconcile the unique remainder |
| `PRESERVED_NEEDS_REBASE` | Unique work has a verified recoverable location | Retain ref/record and route a bounded continuation |
| `MERGED_VERIFIED_MAIN` | Accepted change and resulting main independently verified | Assess branch retirement separately |
| `SUPERSEDED_CLOSED` | Equivalent accepted behavior, no unique valid delta, and PR closure read back | Assess branch retirement separately |
| `UNKNOWN` | Ownership, coverage or equivalence not established | Investigate; never infer permission to mutate |

`MERGED_VERIFIED_MAIN` describes a verified outcome, not an automatic delete instruction. `SUPERSEDED_CLOSED` must not be used before closure. Record an intended action separately from its observed result.

## 5. Merge and recovery gates

Apply WSP 97 section 1.2A and WSP 10 without weakening them:

- Keep one coherent concern per PR; inspect related PRs and dependency order before creating another.
- Resolve current required checks, applicable reviews, draft status, mergeability, overlaps and exact head. An empty workflow list, all checks from an older revision, or a passing subset cannot establish readiness.
- Classify code/test failures, provider infrastructure errors and missing checks separately. Preserve failed-run evidence; use bounded retries only when supported. A new commit must contain justified work, not disguise a failing gate.
- Merge only within repository policy and the authorized slice, with expected-head protection. Read back the PR and resulting main, and inspect applicable main checks. An API call that returns false, times out or lacks confirmation is not a merge receipt; read current state before retrying an ambiguous effect.
- Never disable protection, skip required tests, dismiss security findings without evidence, force-push an unowned branch, or self-issue an independent review to clear the queue.
- If an approved merge cannot proceed, retain the named gate and recoverable work. Preserve the principal's original goal across sessions.

## 6. Retirement and preservation

Retirement concerns a branch ref and associated work record; it does not modify main. It is a separately authorized mutation, not a synonym for merging or closing a PR.

Before removing a ref, verify:

1. Current branch name/head, current main and associated PR/disposition. Check dependent/stacked PRs, active owner/lease, protected/default/release use and relevant worktree ownership.
2. There is no unpreserved unique valid delta. A squash merge may preserve changes without preserving original commit ancestry: compare accepted content/behavior, not just commit counts or a merge badge.
3. Unique work and any history required by the task have a durable, verified recovery location. A commit SHA written in a document or a PR link is not itself a backup. Use an authorized retained ref or verified Git bundle/archive where necessary; do not expose private work while preserving it.
4. Re-read the head immediately before mutation and use the available expected-ref/concurrency guard. If the head moved, an owner remains active, or safe concurrency cannot be established, retain the branch and record the blocker.
5. After an authorized deletion/closure, read back the resulting state and record the actual effect and recovery location. A request/timeout alone does not establish deletion.

**Deleting a branch does not guarantee indefinite retention of otherwise unreachable commits.** No blanket promise of lossless cleanup is permitted. Age, an ahead/behind count, or absence of an open PR never supplies deletion authority. Connector-visible remote state does not prove the PC's working tree is clean.

## 7. Continuity, RSI and principal reporting

Keep a concise result for 012: completed, preserved, blocked, or next owned action. Do not make the principal operate GitHub to compensate for missing follow-through; do not conceal evidence or uncertainty either.

Memex and the existing work record retain owner, source/head/base/main SHAs, intent, verification identifiers, disposition, recovery location, next action and recheck condition. Keep principal-private memory separate from public repository receipts.

Use WSP 48 and existing WRE Pattern Memory/SKILLz admission for recurring failures. A rule edit, one successful cleanup or a lower PR count is not proof of RSI. Measure independently verified reuse, blocker recurrence, time stalled and preservation failures. Never promote a learned rule merely because an agent recorded it.

## 8. Relationships and implementation boundary

- **WSP 00:** mandatory boot/resume activation; existing awakening gate unchanged.
- **WSP 97:** investigation, evidence boundaries and exact-head/main acceptance.
- **WSP 10:** checkpoint/recovery and terminal closure of owned work.
- **WSP 34:** Git operations/naming; retain applicable existing safeguards.
- **WSP 15:** priority and affordable verification allocation.
- **WSP 22 / 60 / 83:** work records, scoped memory and discoverable documentation.
- **WSP 48 / 95:** measured RSI and admitted SKILLz, not self-certified learning.

This document does not implement a scheduler, lease service, GitHub cleanup worker or new memory database. Reuse existing owners and tests before adding runtime enforcement. The source findings and remediation scope in issue #2122 remain outstanding until tested, admitted and observed; never activate an unsafe legacy auto-merge helper as a shortcut.

## 9. Validation and acceptance

Validate active/knowledge mirror equality, boot-to-110 linkage, relative paths, compatibility with WSP 10/97, exact changed scope and current repository checks. Preserve unrelated WSP_00 semantics. Register the protocol's actual status in the master index before promotion; draft status is not runtime authority.

Runtime qualification must separately exercise: empty/partial inventories, missing/stale/pending checks, infrastructure errors, moved heads, active cross-shard ownership, stacked PRs, squash-equivalent versus unique work, failed/ambiguous mutations, preservation verification and next-session resume. Reuse existing module tests and retrieve their TestModLog/README before extending them. No fixture-only result proves live cleanup or independent review.

## 10. Receipt template

```yaml
protocol: WSP_110
observed_at: <ISO-8601 timestamp with offset>
repository: <owner/repository>
owner: <agent/lane and role>
previous_owner: <handoff owner or null>
work_record: <existing issue/PR/receipt reference>
coverage: <complete/partial/unavailable; pages and gaps>
branch: <exact ref>
head_sha: <observed head>
base_sha: <observed base>
main_sha_at_classification: <observed main>
intended_destination: <MERGE_TO_MAIN/STANDALONE/EXPERIMENT/UNKNOWN>
wsp15_receipt: <reference or UNKNOWN>
pr: <number or null>
classification: <section 4 observed state>
authority_and_lease: <evidence or unavailable>
unique_delta_preserved: <verified location; not_needed; or UNKNOWN>
checks_and_reviews: <exact revision and evidence references>
planned_action: <bounded next operation>
action_taken: <observed effect or none>
resulting_main_sha: <verified SHA or null>
verifier: <independent evidence/role or unavailable>
blocker: <specific blocker or null>
next_action: <owner/action or terminal>
recheck_condition: <event/time/revision or terminal>
```

A failed or unavailable field stays explicit. The template does not create a new canonical store or authorize its own contents.
