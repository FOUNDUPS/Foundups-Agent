# Open-PR Backlog Disposition Audit (Phase 1, decision-only)

- Slice: OPEN_PR_BACKLOG_DISPOSITION_AUDIT_PHASE1
- Worker-Lane: H
- Type: READ-ONLY disposition audit (DECISION-ONLY). No PR closed, merged, pushed, or commented.
- Base: 486eb69d7 (current origin/main at audit time; re-fetched and confirmed unchanged).
- Method: live `gh pr list` + per-PR `gh pr view`/`gh pr checks` re-verified at HEAD; supersession claims verified against merged commits in `origin/main`; CI staleness flagged; external triage hints independently confirmed or refuted.

## 1. Live Open-PR Inventory (re-verified at HEAD)

CI-state-NOW legend: GREEN-STALE = last check run is days/weeks/months old against an older merge commit, NOT re-run at current main (treated as stale). FRESH = checks ran today against current base.

| PR | Title (abbrev) | Age (created) | Base current? | mergeable / state | CI-state-NOW |
|----|----------------|---------------|---------------|-------------------|--------------|
| 796 | PlayFoundups Mall public discovery audit P1 | 2026-06-13 | YES (base=486eb69d7) | MERGEABLE / CLEAN | FRESH (all checks pass today) |
| 785 | deps-dev: @protobufjs/utf8 1.1.0->1.1.1 | 2026-06-12 | base=9f047fff6 (1 behind) | MERGEABLE / CLEAN | recent pass; CodeQL skipped |
| 784 | deps: llama-cpp-python 0.2.69->0.2.72 | 2026-06-12 | base=9f047fff6 (1 behind) | MERGEABLE / UNSTABLE | redteam observation FAIL; lint/security/test pass |
| 783 | deps-dev: protobufjs 7.5.4->7.6.3 | 2026-06-12 | base=9f047fff6 (1 behind) | MERGEABLE / CLEAN | recent pass; CodeQL skipped |
| 782 | hygiene: quota toggle + repo hygiene (W8) | 2026-06-11 | stale | CONFLICTING / DIRTY | NO CHECKS reported on branch |
| 765 | AI Overseer auto-fix shell-exec governance audit | 2026-06-06 | stale | CONFLICTING / DIRTY | GREEN-STALE (2026-06-06) |
| 750 | model-store E: drive migration RedDog continuity | 2026-06-02 | stale | MERGEABLE / CLEAN | GREEN-STALE (2026-06-02) |
| 749 | Docker MCP + AI Overseer control-plane audit | 2026-06-02 | stale | MERGEABLE / CLEAN | GREEN-STALE (2026-06-02) |
| 745 | Hermes -> Nous Agent delegate binding audit | 2026-06-01 | stale | MERGEABLE / CLEAN | GREEN-STALE (2026-06-01) |
| 729 | consolidate Claude instructions + stack.md | 2026-05-30 | stale | MERGEABLE / CLEAN | GREEN-STALE (2026-05-30) |
| 722 | FoundUps Vulnerability Intake Gate spec | 2026-05-26 | stale | MERGEABLE / CLEAN | GREEN-STALE (2026-05-26) |
| 694 | HoloIndex docs reindex post-fix observation | 2026-05-24 | stale | CONFLICTING / DIRTY | GREEN-STALE (2026-05-24) |
| 659 | MCP fail-closed foundup_id validation S2 | 2026-05-22 | stale | MERGEABLE / CLEAN | GREEN-STALE (2026-05-22; old workflow, no Analyze/CodeQL) |
| 418 | AutoAgent Lab Layer3 cutoff + reactivation gate | 2026-04-21 | stale (2 months) | MERGEABLE / CLEAN | GREEN-STALE (2026-04-21; old workflow) |
| 408 | stream-resolver test contracts rebase | 2026-04-20 | stale (2 months) | MERGEABLE / CLEAN | GREEN-STALE (2026-04-20; old workflow) |

Note: gh `mergeable=MERGEABLE` only means git can produce a merge; it does NOT mean the content is novel. Several MERGEABLE PRs (659, 694-class) re-add content already in main and are supersession candidates verified below.

## 2. Disposition Table (PR -> bucket -> evidence)

| PR | Bucket | Evidence |
|----|--------|----------|
| 796 | MERGE_GATE_NOW | base=486eb69d7 == current origin/main; CI all-pass FRESH today (run 27454730821/27454731460); files = ModLog.md + PLAYFOUNDUPS_MALL_PUBLIC_DISCOVERY_AUDIT_PHASE1.md (new doc, not in main); not superseded. ROOT ModLog overlap with this audit and #782 -> ordering note, not a present conflict. (Concurrent Lane A worker's own audit.) |
| 785 | DEPENDABOT_REVIEW | label dependencies/javascript; package-lock.json bump; MERGEABLE/CLEAN; base 1 commit behind. Dependency gate. |
| 784 | DEPENDABOT_REVIEW | label dependencies/python; requirements.txt bump; state UNSTABLE -> `redteam observation (report-only)` FAILS (run 27387434517). Dependency gate MUST review the redteam fail before merge. |
| 783 | DEPENDABOT_REVIEW | label dependencies/javascript; package-lock.json bump; MERGEABLE/CLEAN; base 1 commit behind. Dependency gate. |
| 782 | REBASE_FIRST | CONFLICTING/DIRTY; touches .gitignore, ModLog.md, no_quota_stream_checker.py + tests (unique W8 hygiene/quota-toggle work, NOT in main); NO CI checks reported on branch. Needs rebase onto current main + first CI run before any gate. Overlaps stream_resolver tests with #408 -> sequence after #408 resolution. |
| 765 | SUPERSEDED_CLOSE | Exact file `docs/audits/security/AI_OVERSEER_AUTOFIX_SHELL_EXEC_GOVERNANCE_AUDIT_PHASE1.md` already in main via #767 (commit 0b55b5cdd, +491 lines, same path). Remediation landed via #768 (4dd29761c: autofix_executor.py + security tests). #765 now CONFLICTING because the file pre-exists. Covering merged PRs: #767 (audit doc) + #768 (impl). Overlapping file: the identical audit doc path. |
| 750 | REBASE_FIRST | Files (session JSON `...2026-06-02...model-store-e-drive-migration.json`) NOT in main = genuine new continuity content; CURRENT_CONTEXT.md is a continuously-overwritten RedDog state file. MERGEABLE but CI GREEN-STALE (2026-06-02). Re-run CI on current base before gate. |
| 749 | REBASE_FIRST | File `DOCKER_MCP_AND_AI_OVERSEER_CONTROL_PLANE_AUDIT_PHASE1.md` not in main = new audit doc; MERGEABLE but CI GREEN-STALE (2026-06-02). Rebase + fresh CI. |
| 745 | SUPERSEDED_CLOSE | Decision-only Hermes->Nous delegate binding audit. Its PRIMARY finding (IMPORT_PATH_DRIFT in hermes_job_executor.py, underscore vs hyphen vendor path) was REMEDIATED by #761 (commit 27d6d2c22: hermes_job_executor.py +121, HERMES_DELEGATE_IMPORT_PATH_REMEDIATION_PHASE1.md, +tests). Its explicitly recommended next slice `HERMES_AGENT_RUNTIME_INSTALL_AND_PATH_AUDIT_PHASE1` landed as #757 (7dfcf2877). Further hardened by #778 (a3e70b5a4 manifest validator guard). Covering merged PRs: #761 (remediation of its core finding) + #757 (its recommended successor audit). Overlapping topic/files: hermes_job_executor.py import path + the runtime/path audit it requested. NOTE: #745's own doc artifact is not file-identical in main (topical/functional supersession), so flag to 012 before close. |
| 729 | REBASE_FIRST | `.claude/CLAUDE.md` already exists in main (landed separately) -> content overlap; `stack.md` not in main; root `CLAUDE.md` changed substantially since 2026-05-30. MERGEABLE reported but real content drift; CI GREEN-STALE. Rebase + reconcile CLAUDE.md + fresh CI. |
| 722 | REBASE_FIRST | Files `docs/security/VULNERABILITY_INTAKE.md` + `FOUNDUPS_VULNERABILITY_INTAKE_GATE_SPEC_PHASE1.md` NOT in main = genuine new security spec; MERGEABLE but CI GREEN-STALE (2026-05-26). Rebase + fresh CI before gate. |
| 694 | SUPERSEDED_CLOSE | All three #694 files already in main via OTHER PRs: observation doc via #697 (1b7f6f2e3) re-observed by #701 (d86450997); worktree-safety test + indexer fix via #692 (c4c77c938). #694 now CONFLICTING because files pre-exist. Covering merged PRs: #697/#701 (observation docs) + #692 (indexer worktree-safe fix + test). Overlapping files: both audit docs + test_indexer_project_root_worktree_safety.py. EXTERNAL-HINT WRONG: hint said superseded by #781, but #781 (90a7ec0ee) added a DIFFERENT file (HOLOINDEX_REINDEX_FOR_OPERATIONAL_WRE_PHASE1.md) and does NOT cover #694. |
| 659 | SUPERSEDED_CLOSE | Same feature already merged: #656 (commit 09d6834cb "implement fail-closed foundup_id validation in S2") landed the identical impl doc MCP_FOUNDUP_SCOPE_S2_VALIDATION_IMPL_PHASE1.md + holo_tools.py (+147) + test_holo_tools_foundup_validation.py (+239). #659 PR body describes the exact same work. Covering merged PR: #656. Overlapping files: holo_tools.py, test_holo_tools_foundup_validation.py, the S2 validation impl doc. EXTERNAL-HINT WRONG: hint said only "old checks" (REBASE_FIRST) -- it is actually fully superseded by #656. |
| 418 | REBASE_FIRST | Parking-note doc (AUTOAGENT_LAB_LAYER3_CUTOFF_AND_REACTIVATION_GATE.md), not in main; documents an intentionally parked lane. MERGEABLE but CI GREEN-STALE (2026-04-21, 2 months, old workflow). The PARKED status is the doc's CONTENT, not a hold on the PR itself -> needs rebase + fresh CI to land the record. EXTERNAL-HINT WRONG: hint said "protected" -- no protection/hold label exists; it is a stale docs PR. |
| 408 | REBASE_FIRST | Real test-contract fix (stream_resolver delay algorithm). Current main test still has the OLD contract (line 52-53 "Should be close to MAX_DELAY") that #408 reports as failing -> fix NOT in main, still relevant. Base 2 months behind; main test file since changed by 1fd02e9a5. CI GREEN-STALE (2026-04-20, old workflow). Rebase onto current main + fresh CI. Overlaps with #782 on same test file -> sequence #408 before #782. |

## 3. Recommended EXECUTION ORDER for 0102/W10 (EXECUTE NOTHING here)

1. MERGE_GATE_NOW (single, fresh): **#796** -> hand to the external merge gate. Only PR with current base + fresh CI. (It is a concurrent worker's audit; if multiple ModLog-touching audits land together, sequence ModLog.md merges to avoid trivial conflicts.)
2. SUPERSEDED_CLOSE (close after 012 authorization, citing the covering merged PR in the close comment):
   - **#765** -> covered by #767 (+#768).
   - **#659** -> covered by #656.
   - **#694** -> covered by #697/#701 (+#692).
   - **#745** -> covered by #761 (+#757); FLAG to 012 first (functional supersession; doc artifact not file-identical).
3. DEPENDABOT_REVIEW (hand to dependency gate, NOT docs gate): **#783, #785** (clean), **#784** (review redteam-observation FAIL first).
4. REBASE_FIRST (rebase onto current main + fresh CI, then re-triage): **#722, #749, #750, #729** (docs, low risk), then code PRs **#408** then **#782** (in that order -- they overlap on stream_resolver tests), then **#418** (parking-note record).
5. KEEP_PARKED: none. (No PR qualifies as protected/intentional-hold; see Section 4 -- #418/#745 hints were stale.)

## 4. Divergence from External Triage Hints (where stale/wrong)

| Hint | Verdict | Correction |
|------|---------|------------|
| #782 conflicting | CONFIRMED | CONFLICTING/DIRTY + no CI -> REBASE_FIRST. |
| #765 superseded by #767/#768 | CONFIRMED | Exact file landed by #767; remediation #768. SUPERSEDED_CLOSE. |
| #750/#749 clean | PARTIAL | Content is new, but "clean" CI is GREEN-STALE -> REBASE_FIRST, not gate-now. |
| #745 superseded by later Hermes | CONFIRMED (refined) | Specifically #761 (remediation) + #757 (requested successor); flag 012 (not file-identical). |
| #729/#722 backlog docs | REFINED | Treated as REBASE_FIRST (stale CI / CLAUDE.md drift), not a passive park. |
| #694 superseded by #781 | WRONG | #781 added a different file. Real coverage: #697/#701 + #692. SUPERSEDED_CLOSE with corrected PRs. |
| #659 old checks | WRONG (understated) | Not merely stale -- fully superseded by #656. SUPERSEDED_CLOSE. |
| #418 protected | WRONG | No protection/hold; stale docs PR -> REBASE_FIRST. |
| #408 old | CONFIRMED (refined) | Fix still relevant (main has old contract); REBASE_FIRST. |
| #783/#785/#784 dependabot | CONFIRMED (refined) | DEPENDABOT_REVIEW; #784 has a redteam-observation FAIL to review. |

## 5. WSP_97 Truth Boundary Checklist

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | LIVE_PR_STATE_REVERIFIED_AT_HEAD | YES | `gh pr list`/`gh pr view`/`gh pr checks` run at origin/main=486eb69d7 (re-fetched, unchanged); 15 PRs enumerated with mergeable/state/base/CI captured in Sections 1-2. |
| 2 | SUPERSESSION_CLAIMS_VERIFIED_OR_REFUTED | YES | Each SUPERSEDED_CLOSE cites a MERGED commit in origin/main covering the same files/topic: #765<-0b55b5cdd(#767); #659<-09d6834cb(#656); #694<-1b7f6f2e3(#697)/d86450997(#701)/c4c77c938(#692); #745<-27d6d2c22(#761)/7dfcf2877(#757). #781 supersession of #694 REFUTED. |
| 3 | CI_STALENESS_FLAGGED | YES | Section 1 marks all pre-today checks GREEN-STALE; only #796 FRESH; #784 redteam FAIL noted; #782 no-checks noted. |
| 4 | NO_PR_CLOSED_OR_MERGED | YES | Read-only gh calls only (list/view/checks/diff). No close/merge/push/comment issued on any PR. |
| 5 | EXTERNAL_TRIAGE_RECONCILED | YES | Section 4 reconciles every hint; refutes #694<-#781 and #659 "old checks", corrects #418 "protected". |
| 6 | EXECUTION_ORDER_RECOMMENDED | YES | Section 3 gives gate/close/rebase/dependency/parked ordering; nothing executed. |
| 7 | ASCII_CLEAN | YES | Authored ASCII-only; byte-checked 0 non-ASCII before commit. |
| 8 | FILE_SCOPE_EXACTLY_TWO | YES | Only this doc + root ModLog.md modified; `git diff --name-only origin/main...HEAD` == 2 files. |

## Internal Review (SENTINEL verdict)

Adversarial pass:
- SUPERSEDED_CLOSE refutation: #765/#659/#694 each have the SAME file path present in main via the cited merged commit (verified by `git show --stat`); these hold. #745 is the weakest -- it is functional (its core finding remediated by #761, its requested slice landed as #757) but its own audit doc is not byte-identical in main; therefore flagged for explicit 012 confirmation rather than auto-close. #694<-#781 hint was tested and REFUTED (different file), preventing a wrong close.
- MERGE_GATE_NOW refutation: only #796 survives -- its base equals current origin/main and CI ran today; every other "green" PR's CI predates current main and is correctly demoted to REBASE_FIRST.
- KEEP_PARKED refutation: #418 ("protected" hint) and #745 ("backlog") were probed -- neither carries a protection/hold label; #418 is a stale docs PR (REBASE_FIRST) and #745 is superseded. No genuine parked PR remains.

Verdict: READY. Dispositions are evidence-backed; the single highest-risk action (wrong supersession close) is guarded -- #694 mis-hint refuted, #745 escalated to 012. No PR state was mutated.
