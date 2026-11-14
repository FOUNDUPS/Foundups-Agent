# Worktree Stranded-Work Triage (Phase 1)

## Status

Decision-only triage. Implemented for W10 / 012 review. **No worktree removed,
no branch deleted, no cherry-pick, no commit from stranded work, no source
mutation.** Execution (salvage PRs / removals) is deferred pending 012 ruling.

## Slice

`WORKTREE_STRANDED_WORK_TRIAGE_PHASE1`

## 1. Mission + scope

After the registry cleanup (#741), 19 worktrees remain: 1 primary + 18 linked.
Of the 18 linked, **16 hold potential work** (8 `DIRTY_SKIP` + 8 `REVIEW`); the
other 2 are intentional keeps (open PR #418 `w6_autoagent_rescue`, detached
`0102-clean-main`). This slice classifies each of the 16 into one of:
`SALVAGE_TO_PR` · `ALREADY_MERGED_OR_SUPERSEDED` · `DISCARD_CANDIDATE` ·
`NEEDS_012_DECISION` · `DEFER`. It does **not** execute any decision.

## 2. Predecessors

- **PR #739** `WORKTREE_REGISTRY_CLEANUP_AUDIT_PHASE1` (decision-only inventory).
- **PR #741** `WORKTREE_REGISTRY_CLEANUP_EXECUTION_PHASE1` (removed 63 clean stale
  worktrees; the dirtiness guard deferred these 8 dirty + 8 review here).
- Base: `origin/main` @ `91ac905e9` (post-#741).

## 3. Post-#741 inventory summary

| Bucket | Count |
|--------|------:|
| Total worktrees | 19 |
| Primary checkout | 1 |
| Protected keeps (not triaged): #418 + `0102-clean-main` | 2 |
| **Triaged this slice** (8 DIRTY_SKIP + 8 REVIEW) | **16** |

## 4. Triage method

Multi-agent, adversarially verified (read-only throughout):
1. **Discovery** (16, one per worktree): `git -C <wt>` battery — branch, HEAD,
   `rev-list --count origin/main..HEAD`, `diff --stat/--name-only origin/main...HEAD`
   (three-dot, to ignore stale-base deletions), `status --porcelain`, untracked
   listing; cross-referenced merged PRs and `git show origin/main:<file>`.
2. **Adversarial verify**: every `ALREADY_MERGED_OR_SUPERSEDED` / `DISCARD_CANDIDATE`
   verdict was handed to a skeptic instructed to **refute** "safe to discard" by
   file-level content comparison. Default to `NEEDS_012_DECISION` on any doubt.
3. **HXA cluster cross-analysis**: the 5 HXA worktrees analysed together against
   the landed HXA family (#571/#572/#575/#576).
4. **Synthesis** into the decision table below.

**Key method outcome:** the verify pass **overturned 5 discard/landed verdicts**,
including 4 HXA "exists verbatim in main" claims that were false (same filename,
materially different code). **Zero worktrees are safe to discard outright.**

## 5. DIRTY_SKIP table (8)

| Worktree | Branch | Uncommitted content | Final |
|----------|--------|---------------------|-------|
| `agent-a5d1278` | `worktree-agent-a5d1278…` | HXA26 alt validator (1071 lines) + test + doc | NEEDS_012 |
| `agent-a7eb1c4` | `worktree-agent-a7eb1c4…` | HXA27 alt (interface-DI) test 1022 + doc + stale hermes | NEEDS_012 |
| `agent-ab7fd78` | `feat/hxa27-…` (src of #572) | HXA27 later draft: 2 unique hermes methods + 1235-line test | NEEDS_012 |
| `agent-ad998a8` | `worktree-agent-ad998a8…` | HXA29 integrated Gate 10.5 in `validate_token` + 898-line test | NEEDS_012 |
| `MCPFSR-W9` | `docs/mcp-foundup-scope-reaudit-phase1` | staged 637-line completed audit | NEEDS_012 |
| `vote-concat-audit` | `docs/vote-existing-concatenation-audit` | staged 537-line prerequisite audit | NEEDS_012 |
| `w1-holoindex-hxa-fix` | `worktree-w1-holoindex-hxa-fix` | 1 untracked test (also in main) | ALREADY_MERGED |
| `w_tq3_routing` | `research/tq3-per-collection-routing` | 2 appended runtime JSONL lines (artifact) | ALREADY_MERGED |

## 6. REVIEW table (8)

| Worktree | Branch | Committed work | Final |
|----------|--------|----------------|-------|
| `trade-deterministic-clock-fix` | `fix/trade-…-clock` | deterministic-clock fix, superseded by #691 | NEEDS_012 |
| `w6-registry-build-integration` | `docs/foundup-build-system-registry-integration-audit` | 308-line audit completing stub #634 | SALVAGE |
| `agent-a856df` | `docs/workspace-wrapper-model-update` | Wrapper Model v2.0.0 across 5 docs (P0 from #605) | SALVAGE |
| `w9-roc-pipeline-integration-audit` | `worktree-w9-roc-pipeline-integration-audit` | 519-line ROC pipeline audit | SALVAGE |
| `agent-a3072b9` | `worktree-agent-a3072b9…` | 700-line RedDog preference-capsule audit | SALVAGE |
| `agent-abd459f` | `worktree-agent-abd459f…` | 1052-line edge-observer Phase-2 schema spec | SALVAGE |
| `agent-ad2c339` | `worktree-agent-ad2c339…` | 893-line FoundUp DAE layered build-flow audit | SALVAGE |
| `agent-a38c0fe` | `worktree-agent-a38c0fe…` | HXA27 stale predecessor; audit doc byte-identical to main | ALREADY_MERGED |

## 7. HXA cluster analysis

The 5 HXA worktrees sit on stale bases (0–1 ahead, 163–167 behind). The
functional goal of every HXA slice already landed in main (#571 HXA26, #572
HXA27, #575 HXA29, #576 HXA30). **But 4 of 5 carry a never-landed ALTERNATIVE
implementation** — same filenames, materially different / zero-overlap public
APIs. This is **redundant parallel exploration by two workers (W1 vs 0102) using
incompatible architectures**:

- **Landed canonical (0102):** `TokenValidationReasonCode` + `LocalCapabilityTokenValidator`
  + `get_default_validator()` singleton + `BLOCKED_BY_TOKEN_VALIDATION` + standalone
  `validate_scope_for_action_class()` helper. Coherent family across #571/#572/#575/#576.
- **Worktree alt family (W1):** `CapabilityTokenScope` enum + `SignatureVerifier`/`NonceRegistry`
  dependency-injection + interface-based `ICapabilityTokenValidator` + PolicyFlags-population
  + an **integrated** `Gate 10.5` scope→action-class check. Arguably more defense-in-depth
  (fail-closed DI, replay protection, granular per-gate flags).

| HXA | Worktree | Status | Note |
|-----|----------|--------|------|
| HXA26 | `agent-a5d1278` | DIVERGENT_VALUABLE | 1071 vs 823 lines, **zero API overlap** with landed |
| HXA27 | `agent-a7eb1c4` | DIVERGENT_VALUABLE | interface-DI variant; 1022-line test ≠ main's 671 |
| HXA27 | `agent-ab7fd78` | DIVERGENT_VALUABLE | later draft of #572's own branch; `_inject_test_token` + `_validate_and_update_policy_flags` **absent from main**; 1235-line test |
| HXA29 | `agent-ad998a8` | DIVERGENT_VALUABLE | **integrated Gate 10.5 → see §10 security finding** |
| HXA27 | `agent-a38c0fe` | STALE | genuine landed predecessor; audit doc byte-identical; clean tree |

HXA27 was attempted in **three** worktrees plus main = **four competing designs of
one slice** (`a7eb1c4` vs `ab7fd78` test diff = 1327 lines — not copies).
Per slice rules this is **advisory only — no HXA worktree is recommended for discard.**

## 8. Per-worktree decision table (16)

| # | Worktree | Group | Final | Verified | Rationale |
|---|----------|-------|-------|:--------:|-----------|
| 1 | `agent-a5d1278` | DIRTY | NEEDS_012 | ✓ | HXA26 never-landed alt validator; "verbatim" claim refuted |
| 2 | `agent-a7eb1c4` | DIRTY | NEEDS_012 | ✓ | HXA27 alt variant 1/3; refuted |
| 3 | `agent-ab7fd78` | DIRTY | NEEDS_012 | ✓ | HXA27 later divergent draft; 2 unique hermes methods absent from main |
| 4 | `agent-ad998a8` | DIRTY | NEEDS_012 | ✓ | HXA29 integrated enforcement gate — **possible real gap in main** |
| 5 | `MCPFSR-W9` | DIRTY | NEEDS_012 | ✓ | staged audit superseded by #636/#639; confirm before discard |
| 6 | `vote-concat-audit` | DIRTY | NEEDS_012 | ✓ | staged audit; downstream VOTE PoC merges embody it; near-zero residual |
| 7 | `w1-holoindex-hxa-fix` | DIRTY | ALREADY_MERGED | ✓ | merged #621; nothing unique — **removable now** |
| 8 | `w_tq3_routing` | DIRTY | ALREADY_MERGED | ✓ | merged #430; only dirty = runtime JSONL — **removable now** |
| 9 | `trade-deterministic-clock-fix` | REVIEW | NEEDS_012 | ✓ | superseded by #691; near-certain safe, small divergences |
| 10 | `w6-registry-build-integration` | REVIEW | SALVAGE | ⚠ | completes stub #634; 228 net-new audit lines |
| 11 | `agent-a856df` | REVIEW | SALVAGE | ⚠ | Wrapper Model v2.0.0 (P0 from #605); rebase 133 behind |
| 12 | `w9-roc-pipeline-integration-audit` | REVIEW | SALVAGE | ⚠ | 519-line ROC pipeline audit; extends consensus series |
| 13 | `agent-a3072b9` | REVIEW | SALVAGE | ⚠ | 700-line RedDog preference-capsule audit |
| 14 | `agent-abd459f` | REVIEW | SALVAGE | ⚠ | 1052-line edge-observer Phase-2 schema spec |
| 15 | `agent-ad2c339` | REVIEW | SALVAGE | ⚠ | 893-line FoundUp DAE build-flow audit |
| 16 | `agent-a38c0fe` | REVIEW | ALREADY_MERGED | ✓ | HXA27 stale predecessor; doc byte-identical; clean tree |

**Counts:** `NEEDS_012_DECISION` 7 · `SALVAGE_TO_PR` 6 · `ALREADY_MERGED_OR_SUPERSEDED` 3 · `DISCARD_CANDIDATE` **0**.
✓ = file-level verified. ⚠ = existence/absence checked, content not independently audited (see §10 risk).

## 9. Recommended execution plan (deferred — nothing executed)

**A. Removable now (3, fully landed, file-verified):**
`w1-holoindex-hxa-fix` (#621), `w_tq3_routing` (#430), `agent-a38c0fe` (HXA27
predecessor; advisory: retire once HXA ruling made).

**B. Salvage → PR, then remove (6, docs-only audits):** in value order —
`agent-ad998a8`'s HXA29 finding aside (it is HXA/NEEDS_012), the 6 docs salvages:
`w6-registry-build-integration`, `agent-a856df`, `agent-abd459f`, `agent-a3072b9`,
`agent-ad2c339`, `w9-roc-pipeline-integration-audit`. Each: rebase onto main →
**content-verify** → open PR (source/doc only) → remove worktree after merge.

**C. 012 ruling required before any action (7):** the 4 HXA worktrees
(`a5d1278`, `a7eb1c4`, `ab7fd78`, `ad998a8`) + `MCPFSR-W9` + `vote-concat-audit`
+ `trade-deterministic-clock-fix`. See §11.

**D. Discard candidates: NONE.** The adversarial pass eliminated all blind discards.

## 10. Risks / ambiguity

1. **SECURITY — possible enforcement gap (HXA29 / `agent-ad998a8`).** The worktree
   wires an integrated `Gate 10.5` scope→action-class check **into** `validate_token`
   (emitting `SCOPE_ACTION_CLASS_MISMATCH`); main's landed equivalent
   `validate_scope_for_action_class()` appears **standalone and not invoked** in the
   validation flow. A `git grep` of main found zero callers wiring it in. **If main
   never calls it, capability-token scope is not enforced at validation time** — a
   real gap. Requires code verification before any worktree retirement.
2. **Discovery vs truth.** The discovery layer's "landed verbatim / safe to discard"
   was wrong on 4 HXA worktrees; only file-level verification caught it. Trusting
   discovery alone would have destroyed never-landed unique work.
3. **Salvage candidates unverified for content** (the 6 ⚠): existence-in-main was
   checked (absent), but completeness/quality was not independently audited, and all
   are 106–307 commits behind → **content-verify + rebase before opening PRs**; doc-only
   conflicts are unlikely but not ruled out.
4. **HXA dirty ModLog/TestModLog layers revert real main history** (e.g. `ad998a8`
   = 420 deletions of 2026-05-27/28 entries). Any salvage must take **source/test/doc
   ONLY**, never the stale ModLog/TestModLog diffs.
5. **Holistic-vs-piecemeal.** The alt and canonical APIs are mutually incompatible;
   a per-slice decision risks re-introducing the exact duplication these worktrees
   represent. 012 should rule on the architecture **once**, not slice-by-slice.

## 11. 012 decisions required

1. **HXA architectural ruling (one holistic decision).** Canonical landed line (0102)
   vs alt defense-in-depth family (W1). For each of HXA26/27/29: abandon the alt, or
   salvage specific primitives (e.g. `NonceRegistry` replay protection, fail-closed
   `SignatureVerifier`, integrated Gate 10.5) into a follow-up PR. Until ruled, do NOT
   retire `a5d1278`, `a7eb1c4`, `ab7fd78`, `ad998a8`.
2. **HXA29 enforcement-gap investigation (security).** Confirm whether main invokes
   `validate_scope_for_action_class()` anywhere. If not → open a security follow-up to
   adopt `ad998a8`'s integrated gate. **Highest-value finding of this slice.**
3. **Approve the 6 docs-only salvage PRs** (§9-B) → rebase + content-verify + PR.
4. **Confirm the 3 fully-landed worktrees** (§9-A) for removal now.
5. **Confirm `trade-deterministic-clock-fix`** is fully covered by #691 → remove.
6. **Confirm `MCPFSR-W9` + `vote-concat-audit`** staged audits are superseded
   (#636/#639; merged VOTE PoC slices) → optionally archive the doc, then remove.

## 12. Internal Review Verdict

**READY** — 16 worktrees triaged with adversarial file-level verification; 0 blind
discards; 3 removable-now, 6 salvage, 7 to-012; one security-relevant enforcement-gap
finding surfaced for follow-up. No execution performed; all decisions deferred to 012.

## 13. WSP_97 Truth Boundary Checklist

Declared items: 17 · Rows: 17 · All YES.

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | DECISION_ONLY_TRIAGE | YES | Only `git`/`gh` reads; no execution |
| 2 | NO_WORKTREE_REMOVAL | YES | 19 worktrees unchanged |
| 3 | NO_BRANCH_DELETE | YES | 0 branches deleted |
| 4 | NO_CHERRY_PICK | YES | None performed |
| 5 | NO_STRANDED_WORK_COMMIT | YES | Only this audit doc committed |
| 6 | NO_SOURCE_MUTATION | YES | Single `docs/audits/architecture` file |
| 7 | NO_DIRTY_WORK_DISCARD | YES | 8 dirty trees untouched; 0 discarded |
| 8 | HXA_CLUSTER_PROTECTED | YES | All 5 HXA advisory-only; 0 discard |
| 9 | CITES_PR_739 | YES | §2 |
| 10 | CITES_PR_741 | YES | §2 |
| 11 | ADVERSARIAL_VERIFICATION_RUN | YES | 5 discard/landed verdicts refuted; 4 HXA "verbatim" claims overturned |
| 12 | NO_REGISTRY_MUTATION | YES | Audit only |
| 13 | NO_MANIFEST_MUTATION | YES | Audit only |
| 14 | NO_PUBLIC_SURFACE_MUTATION | YES | Audit only |
| 15 | NO_CABR_READY | YES | Not applicable |
| 16 | NO_PAYOUT_READY | YES | Not applicable |
| 17 | NO_DAO_ACTIVATION | YES | Not applicable |
