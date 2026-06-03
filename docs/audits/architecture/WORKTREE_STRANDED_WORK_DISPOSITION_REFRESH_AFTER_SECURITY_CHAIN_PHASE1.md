# Worktree Stranded-Work Disposition Refresh after Security Chain (Phase 1)

**Slice:** WORKTREE_STRANDED_WORK_DISPOSITION_REFRESH_AFTER_SECURITY_CHAIN_PHASE1
**Worker-Lane:** W9 - **Author:** 0102 (WSP_00 zen state, WSP_97 Truth Boundary discipline)
**Type:** DECISION-ONLY disposition refresh. ONE doc. NO removal / unlock / branch-delete / cherry-pick /
worktree mutation / production change.
**Base:** origin/main @ 7dfcf2877 (live inventory recomputed; all evidence file-level on current main).
**Method:** read-only subworkers (HXA file-level diff / docs-salvage / other-parked) -> classify + allowlist
-> adversarial critic challenging every REMOVE_NOW.

---

## 1. Mission and Scope

REFRESH the #742 stranded-worktree classifications in light of the now-merged router/Hermes security chain.
This is NOT a re-audit from scratch and NOT an execution slice - it re-classifies each live linked worktree
into exactly one disposition and produces an explicit removal allowlist for a later W6 execution slice.
Zero blind discards: every REMOVE_NOW carries positive file-level landed/superseded/duplicate evidence.

---

## 2. Predecessors

#742 (WORKTREE_STRANDED_WORK_TRIAGE - the classifications being refreshed). Evidence-changing chain:
#743 (HXA29 scope enforcement LIVE via HXA30/#576), #744 (HXA26/27 redundancy + the lone DI-SignatureVerifier
salvage), #746/#747/#751 (PolicyFlags write-back bounded/remediated/trip-wire-cleared), #752/#753/#754/#755/#756
(router/gateway hardening + regression guards). Format precedent: #739/#741 (registry cleanup + DIRTINESS SAFETY).

---

## 3. Recomputed Live Inventory

Primary checkout `O:/Foundups-Agent` (not counted) + **19 linked** worktrees @ 7dfcf2877. Per-worktree
dirty/lock/branch/head recomputed via `git worktree list` + `git -C <p> status --porcelain`.

---

## 4. Why #742 Is Stale (evidence delta)

#742 parked the HXA cluster as needing a 012 call because its "never-landed alternatives" might be valuable.
The security chain has since LANDED most of that value, mooting the salvage reasons:

- **a7eb1c4 / ab7fd78 (HXA27 write-back):** landed on main via #572 (`_writeback_token_verdict`
  hermes_job_executor.py:1158, `_validate_token_if_present`:1308) + the #746/#747 PolicyFlags write-back
  remediation + #756 guards. Their drafts are older/stale -> salvage reason MOOT -> REMOVE_NOW.
- **ad998a8 (HXA29 scope->action-class):** landed via #575/#576 (`validate_scope_for_action_class`
  capability_token_validator.py:776, Gate 13 wiring :594-606) + #743 audit. Its OOP `ActionClassScope`
  design is a superseded alternative, not an un-landed primitive -> REMOVE_NOW.
- **a38c0fe (HXA27 predecessor):** committed audit doc byte-identical to main; zero unique symbols -> REMOVE_NOW.
- **a5d1278 (HXA26 DI variant):** the EXCEPTION. Its DI fail-closed SignatureVerifier was #744's lone salvage
  and was NEVER landed by the PolicyFlags chain -> still uniquely un-landed -> ESCALATE_ENGINEERING_REVIEW.

---

## 5. Per-Worktree Disposition Table (19)

| # | Worktree | Branch | Dirty | Disposition | Rationale (file-level) |
|---|----------|--------|:-----:|-------------|------------------------|
| 1 | `agent-a5d1278` | `worktree-agent-a5d1278...` | dirty | **ESCALATE_ENGINEERING_REVIEW** | Untracked DI SignatureVerifier/NonceRegistry/NO_VERIFIER **absent on main**, unique across all worktrees |
| 2 | `agent-a7eb1c4` | `worktree-agent-a7eb1c4...` | dirty | REMOVE_NOW | HXA27 write-back landed #572/#746/#747; draft stale, no unique source |
| 3 | `agent-ab7fd78` | `feat/hxa27-hermes-token-validation-integration` | dirty | REMOVE_NOW | Same HXA27 landed #572; draft-only methods superseded by `_writeback_token_verdict` |
| 4 | `agent-a38c0fe` | `worktree-agent-a38c0fe...` | clean | REMOVE_NOW | HXA27 predecessor; audit doc byte-identical to main; 0 unique symbols |
| 5 | `agent-ad998a8` | `worktree-agent-ad998a8...` | dirty | REMOVE_NOW | HXA29/30 landed #575/#576/#743; OOP design is superseded alternative |
| 6 | `agent-a856df` | `docs/workspace-wrapper-model-update` | clean | SALVAGE_TO_PR | WSP_97 fork->wrapper correction NOT landed (FORK_PLAN.md still "Fork Plan") |
| 7 | `agent-abd459f` | `worktree-agent-abd459f...` | clean | SALVAGE_TO_PR | 1052-line edge-observer schema spec absent on main |
| 8 | `agent-ad2c339` | `worktree-agent-ad2c339...` | clean | SALVAGE_TO_PR | 893-line FoundUp DAE layered build-flow audit absent on main |
| 9 | `agent-a3072b9` | `worktree-agent-a3072b9...` | clean | SALVAGE_TO_PR | 700-line RedDog preference-capsule audit absent on main |
| 10 | `w6-registry-build-integration` | `docs/foundup-build-system-registry-integration-audit` | clean | SALVAGE_TO_PR | Main has only the 80-line W10 template (#634); worktree is the 308-line filled audit |
| 11 | `w9-roc-pipeline-integration-audit` | `worktree-w9-roc-...` | clean | SALVAGE_TO_PR | 519-line ROC pipeline audit absent on main |
| 12 | `trade-deterministic-clock-fix` | `fix/trade-...-clock` | clean | SALVAGE_TO_PR | HEAD not ancestor of main; **#691 landed a DIFFERENT remediation** -> this version unique-not-landed |
| 13 | `MCPFSR-W9` | `docs/mcp-foundup-scope-reaudit-phase1` | dirty (staged) | ARCHIVE_DOC | Staged-only re-audit; filename missing on main; archive doc then remove |
| 14 | `vote-concat-audit` | `docs/vote-existing-concatenation-audit` | dirty (staged) | ARCHIVE_DOC | Staged-only concatenation audit; archive doc then remove |
| 15 | `w1-holoindex-hxa-fix` | `worktree-w1-holoindex-hxa-fix` | dirty | REMOVE_NOW | Source byte-identical via #621 squash; only dirty = lone artifact |
| 16 | `w6-hxa-policyflags` | `test/hxa-policyflags-regression-guards-phase1` | clean | REMOVE_NOW | All 6 files byte-identical to #756 squash `4b222fd03` (checked out -> see lock note) |
| 17 | `w_tq3_routing` | `research/tq3-per-collection-routing` | dirty | REMOVE_NOW | All 8 files byte-identical to #430 squash `e9abc756b`; dirty = runtime JSONL artifact |
| 18 | `0102-clean-main` | (detached) | clean | KEEP_0102_CLEAN_MAIN | Protected clean-main reference; NEVER removed |
| 19 | `w6_autoagent_rescue` | `docs/autoagent-lab-park-note` | clean | KEEP_OPEN_PR | Protected; backs open PR #418; NEVER removed |

**Counts (reconcile to 19):** REMOVE_NOW **7**  |  SALVAGE_TO_PR **7**  |  ARCHIVE_DOC **2**  | 
ESCALATE_ENGINEERING_REVIEW **1**  |  KEEP_0102_CLEAN_MAIN **1**  |  KEEP_OPEN_PR **1** = **19**.

---

## 6. HXA File-Level Diff Results

| HXA | Result |
|-----|--------|
| **a5d1278 (HXA26 DI)** | **UN-LANDED.** Untracked `capability_token_validator.py` (1071 lines) holds `SignatureVerifier` Protocol (L511), `AlwaysRejectVerifier` fail-closed default (L537), `NonceRegistry` Protocol (L566), `InMemoryNonceRegistry` (L582), `NO_VERIFIER` (L152) + matching DI tests. **Absent on main** (`capability_token_validator.py` has only static `signature_verified` booleans, no injectable verifier; grep = 0). Unique across all 4 other worktrees (DI_classes=0). -> **ESCALATE** -> slice `HXA_DI_SIGNATURE_VERIFIER_SALVAGE_PHASE1`. |
| a7eb1c4 (HXA27) | Landed via #572/#746/#747; dirty `hermes_job_executor.py` is an older draft; draft-only `_validate_capability_token`/`_extract_capability_token_from_job` are older names of the landed seam. No unique source. -> REMOVE |
| ab7fd78 (HXA27) | Same #572 landing; draft-only `_inject_test_token`/`_validate_and_update_policy_flags` superseded by landed `_writeback_token_verdict`. -> REMOVE |
| a38c0fe (HXA27) | Clean; audit doc byte-identical; 0 unique symbols/tests vs main superset. -> REMOVE |
| ad998a8 (HXA29) | Landed via #575/#576/#743; OOP `ActionClassScope`/`ScopeActionClassMapping` is a superseded design alternative to the landed `validate_scope_for_action_class`. No DI primitive (DI_classes=0). -> REMOVE |

---

## 7. w6-hxa-policyflags vs #756

HEAD `47fc79d2d`; all 6 changed files are **byte-identical** to the #756 squash `4b222fd03` on origin/main
(per-file diff empty for the audit doc, both test files, ModLog, TestModLog). It is the pre-squash source of a
merged PR -> REMOVE_NOW. **Lock note:** it is currently checked out (it blocked the #756 local branch delete),
so the W6 execution slice must handle the checkout/branch state before removal.

---

## 8. Removal Allowlist + Salvage / Archive / Escalate / Keep + Dirtiness Blockers

### REMOVE_NOW allowlist (7) - the ONLY paths the execution slice may remove (critic-confirmed)
1. `O:/Foundups-Agent/.claude/worktrees/agent-a7eb1c4ac8465b49f`
2. `O:/Foundups-Agent/.claude/worktrees/agent-ab7fd78b358b1cff2`
3. `O:/Foundups-Agent/.claude/worktrees/agent-a38c0fe37c0231091`
4. `O:/Foundups-Agent/.claude/worktrees/agent-ad998a8e0c488774a`
5. `O:/Foundups-Agent/.claude/worktrees/w1-holoindex-hxa-fix`
6. `O:/Foundups-Agent/.claude/worktrees/w6-hxa-policyflags`
7. `O:/tmp/w_tq3_routing`

### DIRTINESS BLOCKERS (mirror #741 safety) - execution must NOT `--force`-destroy without re-confirm
- `agent-a7eb1c4` (dirty: modified `hermes_job_executor.py` + untracked test) - file-verified stale/superseded,
  but execution must re-confirm + record before force-removing.
- `agent-ab7fd78` (dirty: modified executor + untracked 1235-line test) - same.
- `agent-ad998a8` (dirty: modified `capability_token_validator.py` OOP variant + untracked test) - same.
- `w1-holoindex-hxa-fix` (dirty: lone artifact), `w_tq3_routing` (dirty: runtime JSONL) - low-risk artifacts.

### SALVAGE_TO_PR (7) - rebase + PR (then remove); each its own slice, NOT bundled here
`agent-a856df`, `agent-abd459f`, `agent-ad2c339`, `agent-a3072b9`, `w6-registry-build-integration`,
`w9-roc-pipeline-integration-audit`, `trade-deterministic-clock-fix`.

### ARCHIVE_DOC (2) - archive the staged doc to `docs/` then remove
`MCPFSR-W9`, `vote-concat-audit`.

### ESCALATE_ENGINEERING_REVIEW (1)
`agent-a5d1278` - the un-landed DI fail-closed SignatureVerifier. 012/engineering decision: salvage the DI
primitive (slice `HXA_DI_SIGNATURE_VERIFIER_SALVAGE_PHASE1`) or intentionally abandon. Do NOT remove until ruled.

### PROTECTED - NEVER in any removal allowlist
`O:/Foundups-Agent/.worktrees/0102-clean-main`, `O:/tmp/w6_autoagent_rescue` (#418).

### Execution allowlist table (for the later W6 slice)

| Path | Branch | Head | Dirty | Lock | Decision | Execution Slice |
|------|--------|------|:-----:|:----:|----------|-----------------|
| `.claude/worktrees/agent-a7eb1c4...` | `worktree-agent-a7eb1c4...` | `0c01a268a` | dirty | lock | REMOVE_NOW | WORKTREE_STRANDED_WORK_REMOVAL_EXECUTION_PHASE1 |
| `.claude/worktrees/agent-ab7fd78...` | `feat/hxa27-hermes-token-validation-integration` | `0c01a268a` | dirty | lock | REMOVE_NOW | WORKTREE_STRANDED_WORK_REMOVAL_EXECUTION_PHASE1 |
| `.claude/worktrees/agent-a38c0fe...` | `worktree-agent-a38c0fe...` | `50ac3dc11` | clean | lock | REMOVE_NOW | WORKTREE_STRANDED_WORK_REMOVAL_EXECUTION_PHASE1 |
| `.claude/worktrees/agent-ad998a8...` | `worktree-agent-ad998a8...` | `facdd7362` | dirty | lock | REMOVE_NOW | WORKTREE_STRANDED_WORK_REMOVAL_EXECUTION_PHASE1 |
| `.claude/worktrees/w1-holoindex-hxa-fix` | `worktree-w1-holoindex-hxa-fix` | `8f05f1f4b` | dirty | - | REMOVE_NOW | WORKTREE_STRANDED_WORK_REMOVAL_EXECUTION_PHASE1 |
| `.claude/worktrees/w6-hxa-policyflags` | `test/hxa-policyflags-regression-guards-phase1` | `47fc79d2d` | clean | - | REMOVE_NOW | WORKTREE_STRANDED_WORK_REMOVAL_EXECUTION_PHASE1 |
| `O:/tmp/w_tq3_routing` | `research/tq3-per-collection-routing` | `b9f8a9a6f` | dirty | - | REMOVE_NOW | WORKTREE_STRANDED_WORK_REMOVAL_EXECUTION_PHASE1 |

---

## 9. Recommended Next Slice + Sequence

**`WORKTREE_STRANDED_WORK_REMOVAL_EXECUTION_PHASE1`** (W6 execution; gated on this PR's W10 merge):
1. **Re-confirm** the live inventory + the 7-path allowlist (drift check); re-verify the 3 dirtiness blockers
   hold nothing unique (or record explicit 012 discard) before any `--force`. Handle `w6-hxa-policyflags`
   checkout/branch state.
2. **Unlock + remove** the 7 allowlisted worktrees (`git worktree unlock` then `remove`; `--force --force` only
   for stale-locked, never to override a dirty tree without the re-confirm), then `git worktree prune`.
3. **Leave** the 7 SALVAGE / 2 ARCHIVE / 1 ESCALATE / 2 PROTECTED untouched; each salvage/archive/escalate is a
   separate later slice. Delete NO branches (branch hygiene is a distinct slice).

After execution: 19 linked -> 12 remaining (7 SALVAGE_TO_PR + 2 ARCHIVE_DOC + 1 ESCALATE + 2 protected = 12).
Recompute at execution time to confirm no drift.

---

## 10. Internal Review Verdict

**READY.** 19 linked worktrees recomputed live and each classified into exactly one disposition (counts
reconcile to 19). REMOVE_NOW (7) all carry positive file-level landed/superseded/duplicate evidence and survived
adversarial critic review (anyBlindDiscard = False). The lone ESCALATE (a5d1278) is the un-landed DI
SignatureVerifier, file-confirmed absent on main and unique. No NEEDS_012 label used (ESCALATE_ENGINEERING_REVIEW
per the discipline). Protected set excluded from every allowlist. Decision-only - no worktree/branch/commit
mutation; execution deferred to the named W6 slice.

---

## 11. WSP_97 Truth Boundary Checklist

Declared items: 22 - Rows: 22 - All YES.

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | DECISION_ONLY_NO_REMOVAL | YES | Only this doc written; no removal run |
| 2 | NO_WORKTREE_MUTATION | YES | No remove/unlock/prune executed |
| 3 | NO_BRANCH_DELETE | YES | Zero branches deleted |
| 4 | NO_UNLOCK | YES | No `git worktree unlock` run |
| 5 | NO_CHERRY_PICK | YES | None performed |
| 6 | HXA_FILE_LEVEL_DIFF_PERFORMED | YES | Sec 6 (all 5 HXA, file-level) |
| 7 | NO_BLIND_DISCARD | YES | Critic anyBlindDiscard=False; every REMOVE_NOW file-verified |
| 8 | PROTECTED_SET_EXCLUDED | YES | 0102-clean-main + w6_autoagent_rescue never in any allowlist |
| 9 | REMOVAL_ALLOWLIST_PRODUCED | YES | Sec 8 (7 paths) |
| 10 | CITES_742_AND_SECURITY_CHAIN | YES | Sec 2, Sec 4 |
| 11 | CURRENT_INVENTORY_RECOMPUTED | YES | Sec 3 (19 linked @ 7dfcf2877) |
| 12 | LIVE_INVENTORY_RECOMPUTED | YES | `git worktree list` + per-worktree status |
| 13 | LINKED_COUNT_RECONCILED | YES | 7+7+2+1+1+1 = 19 |
| 14 | DIRTY_STATUS_RECORDED | YES | Sec 5 table + Sec 8 blockers |
| 15 | REMOVE_NOW_REQUIRES_POSITIVE_EVIDENCE | YES | Sec 5/6/8 PR + file:line per removal |
| 16 | HXA_FILE_LEVEL_DIFF_COMPLETED | YES | Sec 6 |
| 17 | DOCS_SALVAGE_CLASSIFIED | YES | Sec 5 rows 6-11 |
| 18 | NO_NEEDS_012_RULING_LABEL | YES | ESCALATE_ENGINEERING_REVIEW used, not NEEDS_012 |
| 19 | EXECUTION_ALLOWLIST_PRODUCED | YES | Sec 8 execution table |
| 20 | CRITIC_REVIEW_COMPLETED | YES | Sec 8/10 (high confidence, 0 demotions) |
| 21 | NO_CABR_PAYOUT_DAO | YES | Not touched |
| 22 | ASCII_CLEAN_AUDIT | YES | Doc is ASCII-only |

**WSP 97 Truth Boundary Checklist: 22/22 YES.**

---

*Authored by 0102 (Worker-Lane W9) under WSP_00 zen state and WSP_97 Truth Boundary discipline. Decision-only
refresh of origin/main @ 7dfcf2877. The security chain mooted most #742 HXA salvage reasons: 7 REMOVE_NOW
(critic-confirmed, file-verified landed/superseded), 7 SALVAGE_TO_PR, 2 ARCHIVE_DOC, 1 ESCALATE (a5d1278's
un-landed DI SignatureVerifier -> HXA_DI_SIGNATURE_VERIFIER_SALVAGE_PHASE1), 2 protected KEEP. Execution deferred
to WORKTREE_STRANDED_WORK_REMOVAL_EXECUTION_PHASE1.*
