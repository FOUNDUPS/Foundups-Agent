# Worktree Stranded-Work Removal - Execution Phase 1

**Worker-Lane**: W6
**Slice**: WORKTREE_STRANDED_WORK_REMOVAL_EXECUTION_PHASE1
**Date**: 2026-06-03
**WSP References**: WSP 00 (Zen State), WSP 22 (ModLog), WSP 50 (Pre-Action), WSP 64 (Violation Prevention), WSP 97 (Truth Boundary)
**Predecessors**: #758 (allowlist decision), #741 (Windows reconciliation pattern)
**Classification**: CONTROLLED DESTRUCTIVE (worktree removal only; no branch delete, no source mutation)

---

## 1. Mission + Scope

Execute the removal of exactly the 7 stranded worktrees allowlisted in the
predecessor decision PR #758. This is the destructive follow-up to the
decision-only #758, which classified every linked worktree into one of:
PROTECTED, ESCALATE, SALVAGE, ARCHIVE, or REMOVE.

**In scope**: `git worktree remove` (with unlock/force as required) for the 7
REMOVE-classified paths, followed by `git worktree prune`.

**Out of scope (explicitly NOT done)**:
- No `git branch -d` / `git branch -D` (branch hygiene deferred to a later phase).
- No touch to any PROTECTED, ESCALATE (a5d1278), SALVAGE (7), or ARCHIVE (2) worktree.
- No source-file mutation in any module.
- No glob/regex/branch-derived deletion - the 7 paths are hard-coded exactly.

---

## 2. Predecessors

| PR | Role | Contribution to this phase |
|----|------|----------------------------|
| #758 | Allowlist decision | Produced the canonical 7-path REMOVE allowlist with per-path #758 head + dirty shape, plus the PROTECTED/ESCALATE/SALVAGE/ARCHIVE classification. This phase consumes that allowlist verbatim. |
| #741 | Windows reconciliation pattern | Established the prune + clean reconciliation pass for transient Windows handle errors (Permission denied / Directory not empty). This phase reuses that recovery pattern (none were triggered). |

---

## 3. Pre-flight Inventory

Captured from the primary checkout `O:/Foundups-Agent` at execution start:

- `origin/main` @ `4b10da5a9` (#758 merged).
- Primary checkout branch: `main` @ `4b10da5a9` (HEAD before == after, unchanged).
- Linked worktrees BEFORE: **19** (`git worktree list` = 20 lines incl. primary).
- Branch count BEFORE: **263** (`git branch | wc -l`).
- PROTECTED present: `0102-clean-main`, `w6_autoagent_rescue` (#418), `a5d1278` (ESCALATE).
- SALVAGE (7) + ARCHIVE (2) present.

---

## 4. Allowlist Re-verification (7 paths, head/dirty vs #758, drift result)

Fresh `git -C <p> rev-parse --short HEAD` + `git -C <p> status --porcelain` at execution time:

| # | Path | #758 head | Fresh head | #758 dirty | Fresh dirty (shape) | Drift |
|---|------|-----------|------------|------------|---------------------|-------|
| 1 | `.claude/worktrees/agent-a7eb1c4ac8465b49f` | 0c01a268a | 0c01a268a | dirty(5) | 3 M + 2 ?? (stale HXA27 draft) | NONE |
| 2 | `.claude/worktrees/agent-ab7fd78b358b1cff2` | 0c01a268a | 0c01a268a | dirty(2) | 1 M + 1 ?? (stale HXA draft) | NONE |
| 3 | `.claude/worktrees/agent-a38c0fe37c0231091` | 50ac3dc11 | 50ac3dc11 | clean | clean | NONE |
| 4 | `.claude/worktrees/agent-ad998a8e0c488774a` | facdd7362 | facdd7362 | dirty(5) | 3 M + 2 ?? (stale HXA29 draft) | NONE |
| 5 | `.claude/worktrees/w1-holoindex-hxa-fix` | 8f05f1f4b | 8f05f1f4b | dirty(1) | 1 ?? (lone artifact test) | NONE |
| 6 | `.claude/worktrees/w6-hxa-policyflags` | 47fc79d2d | 47fc79d2d | clean | clean | NONE |
| 7 | `O:/tmp/w_tq3_routing` | b9f8a9a6f | b9f8a9a6f | dirty(1) | 1 M (runtime JSONL) | NONE |

All 7 heads match #758 exactly. All dirty shapes match the #758-classified
stale shapes (HXA drafts / lone artifact / runtime JSONL). **SKIPPED_DRIFT: 0.**

Dirty content detail (for the record):
- a7eb1c4: M wre_core/ModLog.md, M hermes_job_executor.py, M tests/TestModLog.md; ?? HXA27_HERMES_TOKEN_VALIDATION_INTEGRATION.md, ?? test_hxa27_hermes_token_validation_integration.py
- ab7fd78: M hermes_job_executor.py; ?? test_hxa27_hermes_token_validation_integration.py
- ad998a8: M wre_core/ModLog.md, M capability_token_validator.py, M tests/TestModLog.md; ?? HXA29_TOKEN_SCOPE_VALIDATION.md, ?? test_hxa29_token_scope_validation.py
- w1-holoindex: ?? modules/foundups/tests/test_foundup_registry_schema.py (untracked-only; empty tracked diff)
- w_tq3_routing: M holo_index/holo_index/output/holo_output_history.jsonl (runtime log)

---

## 5. CWD-guard Result

- Asserted `$PWD` == `O:/Foundups-Agent` (primary checkout): **PASS**.
- Asserted CWD NOT inside `.claude/worktrees` / `.worktrees` / `O:/tmp` linked tree: **PASS**.
- All worktree operations issued via `git -C O:/Foundups-Agent ...`; never `cd` into a linked worktree.
- Protected-collision check (7 allowlist vs 12 protected): **0 collisions, PASS** (fail-closed exit 2 not triggered).

---

## 6. Dry-run Summary

`scripts/worktree_removal_execution_phase1_dryrun.ps1` run from the primary BEFORE the real removal:

```
CWD-GUARD: PASS (cwd = O:\Foundups-Agent)
PROTECTED-COLLISION: PASS (0 collisions; 7 allowlist disjoint from 12 protected)
... per-path: all 7 HEAD match #758, DRIFT none, plan printed ...
================================ SUMMARY ========================
  Would-remove     : 7
  Would-unlock     : 4
  SKIPPED_DRIFT    : 0
  Protected-excluded: 12 (never in remove set)
  Collisions       : 0
DRY-RUN COMPLETE - no destructive action taken.
```

The dry-run script is verified non-destructive: it contains no
`worktree remove/unlock/prune`, `Remove-Item`, or `Move-Item` calls.

---

## 7. Execution Log (unlocked / removed / SKIPPED_DRIFT / failed-reconciled + force level + backup)

**Stale-lock verification**: all 4 locked allowlist paths carried lock owner
`pid 26164`. `Get-Process -Id 26164` returned **NOT_RUNNING** -> stale lock
confirmed; safe to unlock. (PID 380, which locks SALVAGE worktrees, was never
touched - those paths are protected.)

**Dirty backups created BEFORE any force** (out-of-repo at
`O:/tmp/worktree_removal_backups/20260603T123951Z/`):

| Short | diff.patch | diff_cached | untracked copied | dirty had content |
|-------|-----------|-------------|------------------|-------------------|
| agent-a7eb1c4 | 21549 B | 0 B | 2 files | yes |
| agent-ab7fd78 | 11099 B | 0 B | 1 file | yes |
| agent-ad998a8 | 18191 B | 0 B | 2 files | yes |
| w1-holoindex  | 0 B | 0 B | 1 file | untracked-only (empty tracked diff, as expected) |
| w_tq3_routing | 6458 B | 0 B | 0 files | yes (tracked JSONL only) |

Each backup dir also holds HEAD.txt, status_porcelain.txt, untracked_files.txt.
Clean paths (a38c0fe, w6-hxa-policyflags) need no dirty backup.

**Unlock (4 stale-locked), order first**:

| Path | unlock exit |
|------|-------------|
| agent-a7eb1c4ac8465b49f | 0 |
| agent-ab7fd78b358b1cff2 | 0 |
| agent-a38c0fe37c0231091 | 0 |
| agent-ad998a8e0c488774a | 0 |

**Remove (all 7), with force level recorded**:

| # | Path | Force level | Justification | exit | result |
|---|------|-------------|---------------|------|--------|
| 1 | agent-a7eb1c4ac8465b49f | `remove --force` | dirty(cleared)+backed up; was locked (now unlocked) | 0 | REMOVED |
| 2 | agent-ab7fd78b358b1cff2 | `remove --force` | dirty(cleared)+backed up; was locked | 0 | REMOVED |
| 3 | agent-a38c0fe37c0231091 | `remove --force` | clean but was locked-admin (force clears admin/checkout dirty state) | 0 | REMOVED |
| 4 | agent-ad998a8e0c488774a | `remove --force` | dirty(cleared)+backed up; was locked | 0 | REMOVED |
| 5 | w1-holoindex-hxa-fix | `remove --force` | dirty(cleared, untracked artifact)+backed up; unlocked | 0 | REMOVED |
| 6 | w6-hxa-policyflags | `remove` (plain) | clean + unlocked (no force needed) | 0 | REMOVED |
| 7 | O:/tmp/w_tq3_routing | `remove --force` | dirty(cleared, runtime JSONL)+backed up; unlocked | 0 | REMOVED |

A single `--force` sufficed for every removal (the `unlock` step cleared the
lock first, so a second `--force` for the lock was never required). No
`--force --force` was used. No path required the #741 Windows
Permission-denied / Directory-not-empty reconciliation - all removals were
clean on the first attempt.

- **SKIPPED_DRIFT**: 0 (no path drifted).
- **failed-reconciled**: 0 (no transient Windows errors).

**Prune**: `git -C O:/Foundups-Agent worktree prune` exit 0.

---

## 8. Post-removal Inventory (linked BEFORE -> AFTER, expect 19 -> 12)

- Linked worktrees: **19 -> 12** (`git worktree list` = 13 lines incl. primary).
- after-count (12) == before (19) - removed (7). Reconciles exactly.
- `git worktree prune --dry-run`: **empty** (nothing left to prune).

Surviving worktree list (13 lines):

```
O:/Foundups-Agent                                          4b10da5a9 [main]
.claude/worktrees/agent-a3072b92195f6e5a7                  0091c3cb8 [..a3072b92..] locked    (SALVAGE)
.claude/worktrees/agent-a5d1278fb48536509                  e8caaefc1 [..a5d1278..]  locked    (ESCALATE)
.claude/worktrees/agent-a856dfecee631f9be                  093b5ee4c [docs/workspace-wrapper-model-update] locked (SALVAGE)
.claude/worktrees/agent-abd459fbbbc75e72d                  1f97b9b8a [..abd459f..]  locked    (SALVAGE)
.claude/worktrees/agent-ad2c339cf9b6ab9c3                  9f6094290 [..ad2c339..]  locked    (SALVAGE)
.claude/worktrees/MCPFSR-W9                                56a82054e [docs/mcp-foundup-scope-reaudit-phase1]   (ARCHIVE)
.claude/worktrees/trade-deterministic-clock-fix           356691ffc [fix/..deterministic-clock-phase1]        (SALVAGE)
.claude/worktrees/vote-concat-audit                       bde6d08d0 [docs/vote-existing-concatenation-audit]   (ARCHIVE)
.claude/worktrees/w6-registry-build-integration           525838ed5 [docs/foundup-build-system-registry-integration-audit] (SALVAGE)
.claude/worktrees/w9-roc-pipeline-integration-audit       7e089087b [..w9-roc-pipeline-integration-audit]      (SALVAGE)
.worktrees/0102-clean-main                                28620ce1b (detached HEAD)                            (PROTECTED)
O:/tmp/w6_autoagent_rescue                                bb8d46e61 [docs/autoagent-lab-park-note]             (PROTECTED #418)
```

(The throwaway `O:/tmp/wt_exec` deliverables worktree is created after this
inventory and removed at the end; it is not part of the surviving set.)

---

## 9. Branch Hygiene NOT Done (deferred)

No branches were deleted. Branch count is **263 BEFORE and 263 AFTER**. The
branches that backed the 7 removed worktrees still exist as refs (e.g.
`worktree-agent-a7eb1c4ac8465b49f`, `feat/hxa27-hermes-token-validation-integration`,
`worktree-w1-holoindex-hxa-fix`, `research/tq3-per-collection-routing`, etc.).
Branch hygiene / pruning of these orphaned branches is **explicitly deferred**
to a later phase per the dispatch (NO `git branch -d/-D` in this phase).

---

## 10. Protected + Non-allowlisted Untouched Proof

- PROTECTED present after: `0102-clean-main` (YES), `w6_autoagent_rescue` (YES), `a5d1278` ESCALATE (YES).
- SALVAGE (7) present after: agent-a856df, agent-abd459f, agent-ad2c339, agent-a3072b9, w6-registry-build-integration, w9-roc-pipeline-integration-audit, trade-deterministic-clock-fix - all YES.
- ARCHIVE (2) present after: MCPFSR-W9, vote-concat-audit - both YES.
- Per-needle confirmation that each of the 7 removed paths is GONE from
  `git worktree list`: all 7 GONE.
- No non-allowlisted worktree was unlocked, removed, or otherwise mutated.
- No source file in any module was modified by this phase.
- Primary checkout branch `main` @ `4b10da5a9` unchanged (HEAD before == after).

---

## 11. Internal Review Verdict

**PASS.** The execution removed exactly the 7 #758-allowlisted worktrees with
zero drift, hard-coded paths (no globs/regex/branch-derived deletion), and
mandatory out-of-repo backups for all 5 dirty paths created BEFORE any
force-remove. Stale lock (pid 26164) was verified dead before unlock; the live
SALVAGE lock owner (pid 380) was never touched. No branches deleted (263 ->
263). All PROTECTED/ESCALATE/SALVAGE/ARCHIVE worktrees survive. Post-state
reconciles exactly (19 -> 12; after == before - 7; prune --dry-run empty).
Primary checkout untouched on `main`. The dry-run script is verified
non-destructive. No CABR/payout/DAO side effects.

---

## 12. WSP_97 Truth Boundary Checklist

Declared == Actual. All YES.

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | ALLOWLIST_ONLY_7 | YES | Exactly 7 paths removed (sections 7-8); per-needle GONE check confirms only those 7. |
| 2 | EXACT_ALLOWLIST_NO_GLOBS | YES | Paths hard-coded as literal strings in script `$Remove` + removal commands; no glob/regex/branch-derived selection. |
| 3 | NO_BRANCH_DELETE | YES | No `git branch -d/-D` issued (section 9). |
| 4 | BRANCHES_PRESERVED | YES | Branch count 263 BEFORE == 263 AFTER. |
| 5 | PROTECTED_EXCLUDED | YES | 0 collisions (section 5); all 3 PROTECTED present after (section 10). |
| 6 | A5D1278_UNTOUCHED | YES | a5d1278 ESCALATE still in worktree list, still locked (sections 8, 10). |
| 7 | SALVAGE_ARCHIVE_UNTOUCHED | YES | All 7 SALVAGE + 2 ARCHIVE present after (sections 8, 10). |
| 8 | CWD_GUARD_PASS | YES | CWD == O:/Foundups-Agent, not inside any linked tree (section 5). |
| 9 | FRESH_DIRTINESS_RECHECKED | YES | Fresh HEAD + porcelain captured per path at execution time (section 4). |
| 10 | NO_FORCE_ON_DRIFT | YES | SKIPPED_DRIFT = 0; no drift occurred, so no force-on-drift possible. |
| 11 | DIRTY_BACKUPS_CREATED_BEFORE_FORCE | YES | 5 dirty backups written to O:/tmp/worktree_removal_backups/20260603T123951Z/ before any remove (section 7). |
| 12 | FORCE_LEVEL_JUSTIFIED | YES | Per-path force level + justification table (section 7); single `--force` max, no double-force. |
| 13 | STALE_LOCKS_VERIFIED | YES | pid 26164 Get-Process == NOT_RUNNING before unlock (section 7). |
| 14 | SKIPPED_DRIFT_NOT_FORCED | YES | 0 SKIPPED_DRIFT; none force-removed. |
| 15 | DRY_RUN_SCRIPT_NON_DESTRUCTIVE | YES | Script has no remove/unlock/prune/Remove-Item/Move-Item; ran read-only (section 6). |
| 16 | GIT_WORKTREE_PRUNE_AFTER | YES | `worktree prune` exit 0 after removals (section 7). |
| 17 | POST_STATE_RECONCILED | YES | 19 -> 12; after == before - 7; prune --dry-run empty (section 8). |
| 18 | ROOT_MODLOG_UPDATED | YES | Root `ModLog.md` entry added per WSP 22. |
| 19 | NO_SOURCE_MUTATION | YES | Only 3 deliverable files staged; no module source touched. |
| 20 | NO_CABR_READY | YES | No CABR computation or readiness signal emitted. |
| 21 | NO_PAYOUT_READY | YES | No payout trigger emitted. |
| 22 | NO_DAO_ACTIVATION | YES | No DAO activation performed. |
