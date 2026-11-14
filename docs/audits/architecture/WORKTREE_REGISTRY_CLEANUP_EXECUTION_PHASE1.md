# Worktree Registry Cleanup - Execution (Phase 1)

## 1. Mission + scope

Controlled, partially-destructive worktree cleanup. Execute the removal
approved by `WORKTREE_REGISTRY_CLEANUP_AUDIT_PHASE1` (PR #739): remove the
71-entry approved allowlist of stale worktrees, preserve the 11 protected
entries, `git worktree prune`, and persist this execution audit.

**Scope guards honored:** worktree cleanup only. No branches deleted. No
source / WSP / SKILLz / registry / manifest / catalog / public-route /
dependency / CI files modified. All `git worktree` operations run from the
primary checkout `O:/Foundups-Agent` via `git -C O:/Foundups-Agent ...`;
the tool never `cd`'d into a linked worktree for unlock/remove.

Slice: `WORKTREE_REGISTRY_CLEANUP_EXECUTION_PHASE1`
Worker-Lane: W6

## 2. Predecessor citation

- Audit: `WORKTREE_REGISTRY_CLEANUP_AUDIT_PHASE1` — **PR #739, MERGED**.
- Merge commit / merge-truth base: `f16c0cbaa4d8b2db7f687b80d212c6108d38bc3b`
  (== `origin/main` at execution time).
- The audit was decision-only (no removals). This slice executes it.

## 3. Pre-flight inventory

| Field | Value |
|-------|-------|
| Date | 2026-06-01 |
| Merge-truth | `origin/main` @ `f16c0cbaa` |
| Primary checkout | `O:/Foundups-Agent` (branch `main`, HEAD `f7bf9cd69`) |
| Total worktree entries BEFORE | 82 |
| PR state source | `gh pr list --state all --limit 400` (400 records) |

The primary checkout's branch (`main`) and HEAD (`f7bf9cd69`) were **never
switched** during the run. `origin/main` (`f16c0cbaa`) was used as merge-truth.

### Allowlist derivation (computed LIVE, not hardcoded)

For each linked worktree (path P, branch B from `worktree list --porcelain`):
- P in protected set OR detached -> EXCLUDE.
- Else REMOVE if `git rev-list --count origin/main..B == 0` OR B has a MERGED PR.
- Else (ahead>0, no MERGED PR) -> EXCLUDE (review).

Live result: **71 REMOVE, 11 PROTECTED, 0 unexpected review** — identical to
the audit's expectation. The live remove set and stale-locked subset matched
the refreshed script arrays exactly (set equality verified; 0 protected/remove
collisions).

## 4. Protected worktree table (11 — all KEPT)

| # | Worktree path | Reason |
|---|---------------|--------|
| 1 | `O:/Foundups-Agent` | Primary checkout |
| 2 | `O:/tmp/w6_autoagent_rescue` | OPEN PR #418 |
| 3 | `O:/Foundups-Agent/.worktrees/0102-clean-main` | Detached; 012 discretion |
| 4 | `.claude/worktrees/trade-deterministic-clock-fix` | REVIEW |
| 5 | `.claude/worktrees/w6-registry-build-integration` | REVIEW |
| 6 | `.claude/worktrees/agent-a856dfecee631f9be` | REVIEW |
| 7 | `.claude/worktrees/w9-roc-pipeline-integration-audit` | REVIEW |
| 8 | `.claude/worktrees/agent-a3072b92195f6e5a7` | REVIEW |
| 9 | `.claude/worktrees/agent-abd459fbbbc75e72d` | REVIEW |
| 10 | `.claude/worktrees/agent-ad2c339cf9b6ab9c3` | REVIEW |
| 11 | `.claude/worktrees/agent-a38c0fe37c0231091` | REVIEW (HXA27 divergent — NOT a duplicate) |

All 11 verified present in the post-cleanup inventory.

## 5. Removal allowlist summary (71; with SKIPPED_DIRTY augmentation)

The approved allowlist is 71 (37 stale-locked, 34 unlocked). A
**DIRTINESS SAFETY** augmentation ran `git status --porcelain` per candidate
immediately before removal. **8 candidates were DIRTY** (uncommitted/untracked
changes) and were **NOT removed** — surfaced as `SKIPPED_DIRTY` for 012's
explicit decision. `--force` was never used to override a dirty tree.

Net executed: **63 removed (clean), 8 SKIPPED_DIRTY**.

### SKIPPED_DIRTY (8) — deferred for 012 decision

| Worktree | Dirty content (summary) |
|----------|-------------------------|
| `.claude/worktrees/agent-a5d1278fb48536509` | HXA26: untracked `capability_token_validator.py` + test + audit doc; modified wre_core ModLog/TestModLog |
| `.claude/worktrees/agent-a7eb1c4ac8465b49f` | HXA27: modified `hermes_job_executor.py`, ModLog/TestModLog; untracked test + audit doc |
| `.claude/worktrees/agent-ab7fd78b358b1cff2` | HXA27: modified `hermes_job_executor.py`; untracked test |
| `.claude/worktrees/agent-ad998a8e0c488774a` | HXA29: modified `capability_token_validator.py`, ModLog/TestModLog; untracked test + audit doc |
| `.claude/worktrees/MCPFSR-W9` | staged-add `MCP_FOUNDUP_SCOPE_CURRENT_ARCHITECTURE_REAUDIT_PHASE1.md` |
| `.claude/worktrees/vote-concat-audit` | staged-add `VOTE_EXISTING_FOUNDUP_CONCATENATION_AUDIT_PHASE1.md` |
| `.claude/worktrees/w1-holoindex-hxa-fix` | untracked `test_foundup_registry_schema.py` |
| `O:/tmp/w_tq3_routing` | modified `holo_output_history.jsonl` (runtime artifact) |

Note: the HXA26/27/29 dirty worktrees hold genuinely unmerged worker source
(token-validation work). They are correctly preserved by the dirtiness guard
and require 012 triage (commit + PR, or discard) before removal.

## 6. CWD guard result

`CWD GUARD: PASS` — `$PWD` asserted equal to the primary checkout
`O:/Foundups-Agent` and NOT inside any `.claude/worktrees/`, `.worktrees/`,
or `O:/tmp/` linked tree, before any unlock/remove. Re-asserted in the
execution driver (fail-closed; protected-path-in-remove-list -> exit 2).

## 7. Dry-run output summary

`powershell -ExecutionPolicy Bypass -File scripts/worktree_cleanup_phase1_dryrun.ps1`:

```
CWD GUARD: PASS (cwd is primary checkout, not inside any linked worktree)
...
SUMMARY: 63 would-remove (clean) | 33 would-unlock | 8 SKIPPED_DIRTY | 11 protected-excluded | 0 collisions
ALLOWLIST total = 71 (clean 63 + dirty-skipped 8)
```

0 collisions; CWD guard passed; allowlist total 71 (63 clean + 8 dirty-skipped).
Proceeded to execution.

## 8. Execution log summary

Removal ran serially from the primary checkout via `git -C O:/Foundups-Agent
worktree unlock|remove`. Stale locks were unlocked first; `--force` was used
only where a removal still refused due to lock state, never to override dirty.

| Outcome | Count |
|---------|------:|
| Removed (clean) | 63 |
| SKIPPED_DIRTY (deferred) | 8 |
| Failed (after prune reconciliation) | 0 |
| **Allowlist total** | **71** |

Windows transiently emitted `Permission denied` / `Directory not empty` for a
subset during the serial pass (open file handles); those entries were swept by
the subsequent `git worktree prune` and a clean-only reconciliation pass, all
landing as successfully removed. Final reconciliation: **63/63 clean targets
removed, 0 remaining, 0 protected missing, 0 dirty missing.**

## 9. Post-cleanup inventory

| Field | Value |
|-------|-------|
| Total worktree entries AFTER | 19 (= 11 protected + 8 dirty-skipped) |
| `git worktree prune --dry-run` | empty (clean registry) |
| Branches deleted | 0 |
| Local branch count | 255 (unchanged; removed-worktree branches intact) |
| Primary branch | `main` (never switched) |
| Primary HEAD | `f7bf9cd69` (unchanged) |

Note: a 20th transient entry (`O:/tmp/wt_exec_phase1`, this artifact worktree)
exists only while this doc is committed and is removed at the end of the slice.

## 10. Deferred REVIEW worktrees (8)

The 8 REVIEW worktrees from the audit are preserved untouched (they are 7 of
the protected entries #4-#11 above, minus the primary/PR#418/detached): the
6 `REVIEW`-classed `.claude/worktrees/*` plus `agent-a38c0fe37c0231091`
(HXA27 divergent). Triage (cherry-pick keepers -> PR, then remove) is deferred
to a separate slice per the audit's recommended path. No REVIEW worktree was
removed.

## 11. Branch hygiene deferred

~40 dangling `worktree-agent-*` / merged feature branches remain after their
worktrees were removed; they are `git branch -d`-able in a separate hygiene
slice. **No branch was deleted here.** The audit PR head branch
(`docs/worktree-registry-cleanup-audit-phase1`) is auto-deleted by the repo's
merge setting — recorded, not actioned by this slice.

## 12. Internal Review Verdict

**PASS.** The live-derived allowlist matched the audit's 71 exactly (no drift).
All 11 protected entries and all 8 dirty-skipped worktrees were preserved;
63 clean stale worktrees were removed; the registry prunes clean; 0 branches
were deleted; the primary checkout's branch/HEAD were never changed. The
divergence from "71 removed" is fully explained by the 8 DIRTINESS-SAFETY
skips (not drift), surfaced for 012's explicit decision.

## 13. WSP_97 Truth Boundary Checklist

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | WORKTREE_CLEANUP_ONLY | YES | Only `git worktree unlock/remove/prune` mutations; no other system state changed |
| 2 | NO_SOURCE_CODE_CHANGE | YES | No files under `modules/` `src/` modified; only this doc + dry-run script added |
| 3 | NO_BRANCH_DELETE | YES | 0 `git branch -d/-D`; local branch count 255 unchanged; removed-worktree branches verified present |
| 4 | NO_PRIMARY_CHECKOUT_REMOVAL | YES | `O:/Foundups-Agent` present in post inventory; branch `main`/HEAD `f7bf9cd69` unchanged |
| 5 | NO_OPEN_PR_WORKTREE_REMOVAL | YES | `O:/tmp/w6_autoagent_rescue` (PR #418) present post-cleanup |
| 6 | NO_REVIEW_WORKTREE_REMOVAL | YES | All 8 REVIEW worktrees present post-cleanup |
| 7 | NO_0102_CLEAN_MAIN_REMOVAL | YES | `O:/Foundups-Agent/.worktrees/0102-clean-main` present post-cleanup |
| 8 | PROTECTED_PATHS_EXCLUDED | YES | 11/11 protected present; 0 protected/remove collisions (script exit-2 guard) |
| 9 | DRY_RUN_BEFORE_EXECUTION | YES | Dry-run ran (0 collisions, CWD PASS) before any removal |
| 10 | EXPLICIT_ALLOWLIST_ONLY | YES | Only the 71-entry derived allowlist processed; protected re-checked per path |
| 11 | STALE_LOCKS_UNLOCKED_ONLY_FOR_APPROVED_REMOVALS | YES | `git worktree unlock` only on allowlist stale-locked paths; `--force` only for lock state |
| 12 | GIT_WORKTREE_PRUNE_AFTER_REMOVE | YES | `git worktree prune` run after removals; post `prune --dry-run` empty |
| 13 | NO_REGISTRY_MUTATION | YES | No FoundUp/canonical registry files touched |
| 14 | NO_MANIFEST_MUTATION | YES | No manifest files touched |
| 15 | NO_PUBLIC_SURFACE_MUTATION | YES | No public route / catalog / public-surface files touched |
| 16 | NO_CABR_READY | YES | No CABR engine / scoring code touched or activated |
| 17 | NO_PAYOUT_READY | YES | No payout path touched or activated |
| 18 | NO_DAO_ACTIVATION | YES | No DAO activation path touched or activated |

Declared rows: 18. Actual rows: 18. All YES.
