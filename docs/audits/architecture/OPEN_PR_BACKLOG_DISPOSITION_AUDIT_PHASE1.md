# Open-PR Backlog Disposition Audit (Phase 1, decision-only)

- Slice: OPEN_PR_BACKLOG_DISPOSITION_AUDIT_PHASE1
- Worker-Lane: Hc (AUTHOR-CORRECTION of the original Lane H audit)
- Type: READ-ONLY disposition audit (DECISION-ONLY). No PR closed, merged, pushed, or commented.
- Base: 4464040d9 (current origin/main at correction time; re-fetched, rebased onto current HEAD).
- Method: live `gh pr list` + per-PR `gh pr view`/`gh pr checks` re-verified at HEAD; supersession claims verified by merge-base-aware THREE-DOT content diffs (`git diff origin/main...<pr-head> -- <files>`) against `origin/main`; CI staleness flagged; external triage hints independently confirmed or refuted.

## 0. Correction Notice (why this audit was rewritten)

The ORIGINAL version of this audit recommended a SUPERSEDED_CLOSE bucket (#765, #659, #694, #745) using `git show --stat` and same-path-present-on-main reasoning. W10 REFUTED that method: a same file PATH existing on main does NOT prove the PR's CONTENT is superseded. Re-verified with merge-base-aware three-dot diffs:
- #765: +500 divergent lines (a DIFFERENT audit doc title at the same path) -- NOT content-identical.
- #659: +664/-29 across impl+tests, carries UNIQUE unmerged S2-validation content (gotjunk_001 registry id, "warning" severity in valid_severities, holo_tools.py registry-loader logic) NOT on main -- closing would LOSE work.
- #694: 859 changed lines, every file three-dot-DIVERGENT (a later/divergent doc + alternate indexer-fix implementation) -- NOT content-identical.
- #745: its own audit doc is ABSENT from main (full insertion); core finding functionally remediated by #761/#757.

NONE of the four is byte-identical-on-main. The content-backed auto-close-eligible set is EMPTY. #765/#659/#694 are NO LONGER any *_SUPERSEDED_CLOSE bucket.

## 0a. Supersession Verification Method

- Path-present is not supersession.
- --stat is insufficient for close recommendations.
- SUPERSEDED_CLOSE requires content-level proof.
- Divergent content cannot be closed automatically.

Operationally: a close recommendation requires the merge-base-aware three-dot net content diff (`git diff origin/main...<pr-head> -- <files>`) to be EMPTY (CONTENT_IDENTICAL_SUPERSEDED). Any non-empty three-dot diff means divergent content remains -> the PR cannot be auto-closed; it is mapped to a 012-decision, rebase, or escalation bucket instead. `git show --stat` and path-presence checks are REJECTED as supersession evidence.

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

Note: gh `mergeable=MERGEABLE` only means git can produce a merge; it does NOT mean the content is novel, and (per the Correction Notice) same-path-present-on-main does NOT mean superseded. Each former supersession candidate was re-checked with a merge-base-aware three-dot content diff below; none is content-identical on main.

## 2. Disposition Table (PR -> bucket -> evidence)

| PR | Bucket | Evidence |
|----|--------|----------|
| 796 | MERGE_GATE_NOW | base=486eb69d7 == current origin/main; CI all-pass FRESH today (run 27454730821/27454731460); files = ModLog.md + PLAYFOUNDUPS_MALL_PUBLIC_DISCOVERY_AUDIT_PHASE1.md (new doc, not in main); not superseded. ROOT ModLog overlap with this audit and #782 -> ordering note, not a present conflict. (Concurrent Lane A worker's own audit.) |
| 785 | DEPENDABOT_REVIEW | label dependencies/javascript; package-lock.json bump; MERGEABLE/CLEAN; base 1 commit behind. Dependency gate. |
| 784 | DEPENDABOT_REVIEW | label dependencies/python; requirements.txt bump; state UNSTABLE -> `redteam observation (report-only)` FAILS (run 27387434517). Dependency gate MUST review the redteam fail before merge. |
| 783 | DEPENDABOT_REVIEW | label dependencies/javascript; package-lock.json bump; MERGEABLE/CLEAN; base 1 commit behind. Dependency gate. |
| 782 | REBASE_FIRST | CONFLICTING/DIRTY; touches .gitignore, ModLog.md, no_quota_stream_checker.py + tests (unique W8 hygiene/quota-toggle work, NOT in main); NO CI checks reported on branch. Needs rebase onto current main + first CI run before any gate. Overlaps stream_resolver tests with #408 -> sequence after #408 resolution. |
| 765 | FUNCTIONALLY_SUPERSEDED_012_DECISION | THREE-DOT: `git diff --numstat origin/main...e26c1c053 -- docs/audits/security/AI_OVERSEER_AUTOFIX_SHELL_EXEC_GOVERNANCE_AUDIT_PHASE1.md` = `500 0` (NON-EMPTY -> NOT content-identical). PR-head title `# AI Overseer Auto-Fix Shell-Exec Governance Audit (Phase 1)` differs from main's `# AI Overseer Autonomous Shell Execution Governance Audit - Phase 1` -- a DIFFERENT audit at the same path. The governance TOPIC and its remediation ARE on main: #767 (0b55b5cdd, audit doc) + #768 (4dd29761c, autofix_executor.py + security tests), both confirmed ancestors of origin/main. Because the topic+remediation are merged but #765's specific doc content diverges, this is functional (not content-identical) supersession -> 012/architect decides whether #765's unique findings add anything beyond #767; NOT auto-close. |
| 750 | REBASE_FIRST | Files (session JSON `...2026-06-02...model-store-e-drive-migration.json`) NOT in main = genuine new continuity content; CURRENT_CONTEXT.md is a continuously-overwritten RedDog state file. MERGEABLE but CI GREEN-STALE (2026-06-02). Re-run CI on current base before gate. |
| 749 | REBASE_FIRST | File `DOCKER_MCP_AND_AI_OVERSEER_CONTROL_PLANE_AUDIT_PHASE1.md` not in main = new audit doc; MERGEABLE but CI GREEN-STALE (2026-06-02). Rebase + fresh CI. |
| 745 | FUNCTIONALLY_SUPERSEDED_012_DECISION | THREE-DOT: `git diff --numstat origin/main...277babff2 -- docs/audits/architecture/HERMES_NOUS_AGENT_DELEGATE_BINDING_AUDIT_PHASE1.md` = `252 0`; the doc is ABSENT from main (`git cat-file -e origin/main:<doc>` fails) -> a full insertion, NOT content-identical. Decision-only Hermes->Nous delegate binding audit. Its PRIMARY finding (IMPORT_PATH_DRIFT in hermes_job_executor.py) was REMEDIATED by #761 (27d6d2c22, confirmed ancestor of origin/main: hermes_job_executor.py +121, HERMES_DELEGATE_IMPORT_PATH_REMEDIATION_PHASE1.md, +tests). Its recommended successor slice landed as #757 (7dfcf2877). Functional escalation: the core finding is fixed on main but #745's own doc artifact is not in main -> 012/architect decides whether to land the record or close; NOT auto-close. |
| 729 | REBASE_FIRST | `.claude/CLAUDE.md` already exists in main (landed separately) -> content overlap; `stack.md` not in main; root `CLAUDE.md` changed substantially since 2026-05-30. MERGEABLE reported but real content drift; CI GREEN-STALE. Rebase + reconcile CLAUDE.md + fresh CI. |
| 722 | REBASE_FIRST | Files `docs/security/VULNERABILITY_INTAKE.md` + `FOUNDUPS_VULNERABILITY_INTAKE_GATE_SPEC_PHASE1.md` NOT in main = genuine new security spec; MERGEABLE but CI GREEN-STALE (2026-05-26). Rebase + fresh CI before gate. |
| 694 | FUNCTIONALLY_SUPERSEDED_012_DECISION | THREE-DOT: `git diff --numstat origin/main...04547be87` = 859 changed lines across 4 files, EVERY file three-dot-DIVERGENT (none content-identical): observation doc (main carries the later `(re-observation)` title via #701), worktree-safety doc, `holo_index/core/indexing_engine.py` (+37/-4), and its test. The worktree-safety FUNCTIONALITY is on main (#692 c4c77c938, confirmed ancestor; plus #697 1b7f6f2e3 / #701 d86450997 observation docs), but #694's indexer fix is a DIVERGENT alternate implementation of the same fix, not byte-identical. Functionality merged + content divergent -> 012/architect decides whether the divergence salvages anything; NOT auto-close. EXTERNAL-HINT WRONG: hint said superseded by #781, but #781's file (HOLOINDEX_REINDEX_FOR_OPERATIONAL_WRE_PHASE1.md) is NOT in #694's fileset -> #694 != #781 (refutation upheld). |
| 659 | UNIQUE_CONTENT_REQUIRES_REBASE | THREE-DOT: `git diff --numstat origin/main...d44781c58` = `+664/-29` across 4 files, ALL three-dot-DIVERGENT including code+tests. Although #656 (09d6834cb) landed S2-validation work and the file PATHS exist on main, #659 carries UNIQUE UNMERGED content NOT on main: `holo_tools.py` (+141/-6) registry-loader fallback logic; `test_holo_tools_foundup_validation.py` (+239) adds the `gotjunk_001` valid-registry-id test path (8 references; main has only 2) and `"warning"` added to `valid_severities`; `MCP_FOUNDUP_SCOPE_S2_VALIDATION_IMPL_PHASE1.md` (+251) divergent. Closing would LOSE this work. NOT a *_SUPERSEDED_CLOSE bucket -> rebase onto current main, run fresh CI, then re-triage. The prior "fully superseded by #656" claim is RETRACTED (it relied on path-presence + --stat). |
| 418 | REBASE_FIRST | Parking-note doc (AUTOAGENT_LAB_LAYER3_CUTOFF_AND_REACTIVATION_GATE.md), not in main; documents an intentionally parked lane. MERGEABLE but CI GREEN-STALE (2026-04-21, 2 months, old workflow). The PARKED status is the doc's CONTENT, not a hold on the PR itself -> needs rebase + fresh CI to land the record. EXTERNAL-HINT WRONG: hint said "protected" -- no protection/hold label exists; it is a stale docs PR. |
| 408 | REBASE_FIRST | Real test-contract fix (stream_resolver delay algorithm). Current main test still has the OLD contract (line 52-53 "Should be close to MAX_DELAY") that #408 reports as failing -> fix NOT in main, still relevant. Base 2 months behind; main test file since changed by 1fd02e9a5. CI GREEN-STALE (2026-04-20, old workflow). Rebase onto current main + fresh CI. Overlaps with #782 on same test file -> sequence #408 before #782. |

## 3. Recommended EXECUTION ORDER for 0102/W10 (EXECUTE NOTHING here)

1. MERGE_GATE_NOW (single, fresh): **#796** -> hand to the external merge gate. Only PR with current base + fresh CI. (It is a concurrent worker's audit; if multiple ModLog-touching audits land together, sequence ModLog.md merges to avoid trivial conflicts.)
2. CONTENT_IDENTICAL_SUPERSEDED (auto-close eligible, content-backed): **NONE.** No open PR has an EMPTY three-dot content diff against current origin/main. There is NO content-backed auto-close set in this audit.
3. FUNCTIONALLY_SUPERSEDED_012_DECISION (do NOT auto-close; 012/architect disposition required): **#765** (topic+remediation merged via #767/#768; divergent +500-line doc at same path), **#694** (worktree-safety functionality merged via #692/#697/#701; divergent alternate indexer-fix content), **#745** (core finding remediated by #761/#757; own doc absent from main). For each, 012 decides whether the divergent content adds value (rebase) or should be closed; if closed, cite the covering merged PR.
4. UNIQUE_CONTENT_REQUIRES_REBASE: **#659** -> carries UNMERGED unique S2-validation content (gotjunk_001 test path, "warning" severity, holo_tools.py registry-loader logic). MUST NOT be closed. Rebase onto current main + fresh CI, then re-triage.
5. DEPENDABOT_REVIEW (hand to dependency gate, NOT docs gate): **#783, #785** (clean), **#784** (review redteam-observation FAIL first).
6. REBASE_FIRST (rebase onto current main + fresh CI, then re-triage): **#722, #749, #750, #729** (docs, low risk), then code PRs **#408** then **#782** (in that order -- they overlap on stream_resolver tests), then **#418** (parking-note record).
7. KEEP_PARKED: none. (No PR qualifies as protected/intentional-hold; see Section 4 -- #418 hint was stale.)

## 4. Divergence from External Triage Hints (where stale/wrong)

| Hint | Verdict | Correction |
|------|---------|------------|
| #782 conflicting | CONFIRMED | CONFLICTING/DIRTY + no CI -> REBASE_FIRST. |
| #765 superseded by #767/#768 | PARTIAL (corrected) | Topic+remediation merged (#767/#768) BUT #765's doc three-dot-diverges (+500 lines, different title) -> FUNCTIONALLY_SUPERSEDED_012_DECISION, NOT auto-close. (Prior "exact file -> SUPERSEDED_CLOSE" retracted: path-presence is not supersession.) |
| #750/#749 clean | PARTIAL | Content is new, but "clean" CI is GREEN-STALE -> REBASE_FIRST, not gate-now. |
| #745 superseded by later Hermes | PARTIAL (corrected) | Core finding remediated (#761/#757) BUT #745's own doc is ABSENT from main (three-dot +252 insertion) -> FUNCTIONALLY_SUPERSEDED_012_DECISION, NOT auto-close. |
| #729/#722 backlog docs | REFINED | Treated as REBASE_FIRST (stale CI / CLAUDE.md drift), not a passive park. |
| #694 superseded by #781 | WRONG | #781's file is NOT in #694's fileset -> #694 != #781 (refutation upheld). #694's own three-dot diff is divergent on all 4 files (functionality merged via #692/#697/#701, content differs) -> FUNCTIONALLY_SUPERSEDED_012_DECISION, NOT auto-close. |
| #659 old checks | WRONG (corrected) | #659 carries UNIQUE UNMERGED S2-validation content (three-dot +664/-29; gotjunk_001 test path, "warning" severity, holo_tools.py logic NOT on main) -> UNIQUE_CONTENT_REQUIRES_REBASE. (Prior "fully superseded by #656" retracted: it relied on --stat/path-presence.) |
| #418 protected | WRONG | No protection/hold; stale docs PR -> REBASE_FIRST. |
| #408 old | CONFIRMED (refined) | Fix still relevant (main has old contract); REBASE_FIRST. |
| #783/#785/#784 dependabot | CONFIRMED (refined) | DEPENDABOT_REVIEW; #784 has a redteam-observation FAIL to review. |

## 5. WSP_97 Truth Boundary Checklist

Declared: 14 rows. All 14 YES with evidence (declared == actual).

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | LIVE_PR_STATE_REVERIFIED_AT_HEAD | YES | `gh pr list`/`gh pr view`/`gh pr checks` + `git diff` run at origin/main=4464040d9 (re-fetched, rebased onto current HEAD); 15 PRs enumerated with mergeable/state/base/CI captured in Sections 1-2. |
| 2 | SUPERSESSION_CLAIMS_VERIFIED_OR_REFUTED | YES | Re-verified by merge-base-aware three-dot diffs vs origin/main(4464040d9): #765 origin/main...e26c1c053 = +500 (divergent); #659 ...d44781c58 = +664/-29 (unique unmerged); #694 ...04547be87 = 859 lines (all 4 files divergent); #745 ...277babff2 = +252 (doc absent from main). NONE content-identical. #694!=#781 upheld. |
| 3 | CI_STALENESS_FLAGGED | YES | Section 1 marks all pre-today checks GREEN-STALE; only #796 FRESH; #784 redteam FAIL noted; #782 no-checks noted. |
| 4 | NO_PR_CLOSED_OR_MERGED | YES | Read-only git/gh calls only (list/view/checks/diff/fetch). No close/merge/push/comment issued on any PR. |
| 5 | EXTERNAL_TRIAGE_RECONCILED | YES | Section 4 reconciles every hint; refutes #694<-#781, corrects #659 "old checks", corrects #418 "protected"; downgrades #765/#745 "superseded" to 012-decision. |
| 6 | EXECUTION_ORDER_RECOMMENDED | YES | Section 3 gives gate/012-decision/rebase/dependency/parked ordering; nothing executed. |
| 7 | ASCII_CLEAN | YES | Authored ASCII-only; byte-checked 0 non-ASCII in both changed docs before commit. |
| 8 | FILE_SCOPE_EXACTLY_TWO | YES | Only this doc + root ModLog.md modified; `git diff --name-only origin/main...HEAD` == 2 files. |
| 9 | CONTENT_LEVEL_SUPERSESSION_REQUIRED | YES | Supersession is judged ONLY by merge-base-aware three-dot content diffs (`git diff origin/main...<pr-head> -- <files>`); Section 0a states this verbatim and every close-class row in Section 2 carries a three-dot numstat. |
| 10 | PATH_PRESENT_NOT_ACCEPTED_AS_SUPERSESSION | YES | Section 0/0a reject same-path-on-main as supersession proof; #659/#694 files are present on main yet three-dot-DIVERGENT and are NOT closed. |
| 11 | STAT_ONLY_SUPERSESSION_REJECTED | YES | Section 0a explicitly rejects `git show --stat`; the prior --stat-based SUPERSEDED_CLOSE bucket is retracted in Sections 0/2/4 and the Internal Review. |
| 12 | UNIQUE_CONTENT_NOT_CLOSED | YES | #659 carries unique unmerged S2-validation content (gotjunk_001 test path, "warning" severity, holo_tools.py logic) -> UNIQUE_CONTENT_REQUIRES_REBASE; not closed. |
| 13 | CLOSE_RECOMMENDATIONS_HAVE_DIFF_EVIDENCE | YES | The only content-backed auto-close bucket is CONTENT_IDENTICAL_SUPERSEDED and it is EMPTY (no PR has an empty three-dot diff). No close is recommended without an empty-diff proof; functional closes are deferred to 012. |
| 14 | NO_PR_CLOSURES_PERFORMED | YES | No PR was closed, merged, commented on, or had its branch deleted by this audit/correction; only #798's own branch was rebased and force-with-lease pushed. |

## Internal Review (SENTINEL verdict)

Adversarial pass (post-correction):
- Supersession refutation: the prior `git show --stat` / path-presence method is REJECTED. Re-verified by merge-base-aware three-dot diffs against origin/main(4464040d9): #765 (+500, divergent doc title), #659 (+664/-29, unique unmerged S2 content), #694 (859 lines, all 4 files divergent), #745 (+252, doc absent from main). NONE has an empty three-dot diff, so NONE qualifies for CONTENT_IDENTICAL_SUPERSEDED. #765/#694/#745 -> FUNCTIONALLY_SUPERSEDED_012_DECISION (functionality merged, content diverges; 012 decides). #659 -> UNIQUE_CONTENT_REQUIRES_REBASE (closing would lose work). The content-backed auto-close set is EMPTY. #694!=#781 upheld (different file).
- MERGE_GATE_NOW refutation: only #796 survives -- its base equals current origin/main and CI ran today; every other "green" PR's CI predates current main and is correctly demoted to REBASE_FIRST.
- KEEP_PARKED refutation: #418 ("protected" hint) was probed -- no protection/hold label; it is a stale docs PR (REBASE_FIRST). No genuine parked PR remains.

Verdict: READY (decision-only; hold for W10). The highest-risk action -- a WRONG supersession close -- is eliminated: there is no content-backed auto-close set, and #659's unique unmerged work is protected from closure. Functional closes (#765/#694/#745) are deferred to explicit 012 authorization. No PR state was mutated; only #798's branch was rebased and force-with-lease pushed.
