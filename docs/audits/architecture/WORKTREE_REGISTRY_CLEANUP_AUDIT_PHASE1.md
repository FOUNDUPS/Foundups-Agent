# Worktree Registry Cleanup - Audit (Phase 1)

## Status

Decision-only audit. Implemented for W10 / 012 review. **No worktrees were
removed, unlocked, or pruned in this slice.** Execution is deferred to
`WORKTREE_REGISTRY_CLEANUP_EXECUTION_PHASE1`.

## Slice

`WORKTREE_REGISTRY_CLEANUP_AUDIT_PHASE1`

## Mission

Inventory all registered Git worktrees, map each to branch / PR / merged
state, and classify each as **remove / keep / review** so the editor's
"too many worktrees" signal can be resolved without losing any worker's
unmerged slice.

This is a read-only audit slice. It does not change runtime code, tests,
dependencies, WSP framework docs, registries, manifests, public routes, or
product behavior. It does not delete branches or remove any worktree.

## Snapshot

| Field | Value |
|-------|-------|
| Date | 2026-06-01 |
| Base | `origin/main` @ `62db6324a` (PR #738) |
| Total worktree entries | 82 |
| Primary checkout | 1 (`O:/Foundups-Agent`) |
| Linked worktrees | 81 |

Note: the live worktree set is mutable (the primary checkout's branch changed
during the audit). Classification keys on **merge truth** (commits-ahead-of-main
and PR state), not on transient lock or branch labels, so it is reproducible.

## Method (read-only)

```bash
git worktree list --porcelain          # inventory (0 stale: prune is a no-op)
git worktree prune --dry-run --verbose # -> empty: all dirs exist on disk
git rev-list --count main..<branch>    # commits-ahead-of-main per worktree
gh pr list --state all --json number,headRefName,state   # PR state join
# lock PIDs checked via Get-Process -> 380, 12892, 26004, 26164 all DEAD
```

## Premises corrected

| Original assumption | Finding |
|---------------------|---------|
| `git worktree prune` clears the backlog | **No-op.** `prune --dry-run` reports 0 stale paths; all 81 dirs exist. The mechanism is `git worktree remove`. |
| Worker lanes are active; preserve them | **All 42 `locked claude agent` entries are stale.** All 4 distinct lock PIDs (380, 12892, 26004, 26164) are dead. Nothing is running. |
| Preserve PR #737 until merged | #737 already **merged** (2026-06-01). The only worktree tied to an **open** PR is **#418**. |

## Classification tally (81 linked worktrees)

| Recommendation | Count | Basis |
|----------------|------:|-------|
| REMOVE - squash-merged | 64 | PR MERGED; shows ahead>=1 only due to squash |
| REMOVE - in-main | 7 | ahead==0; tip already an ancestor of main |
| REVIEW - un-PR'd commit | 8 | 1 real commit each, never PR'd |
| KEEP - open PR | 1 | PR #418 in flight |
| DETACHED - safe | 1 | tip verified ancestor of main |
| **Safe to remove** | **71** | 37 of these hold stale locks |

## Protected entries (must NOT be blind-deleted)

| Class | Worktree path | Branch | Reason |
|-------|---------------|--------|--------|
| PRIMARY | `O:/Foundups-Agent` | (current) | Primary checkout; git refuses removal |
| OPEN_PR | `O:/tmp/w6_autoagent_rescue` | `docs/autoagent-lab-park-note` | PR **#418** OPEN |
| DETACHED | `O:/Foundups-Agent/.worktrees/0102-clean-main` | (detached) | Tip is ancestor of main; 012's call |
| REVIEW | `.claude/worktrees/trade-deterministic-clock-fix` | `fix/trade-due-diligence-deterministic-clock-phase1` | 2026-05-24 fix(trade): deterministic clock for DD scoring (W6) |
| REVIEW | `.claude/worktrees/w6-registry-build-integration` | `docs/foundup-build-system-registry-integration-audit` | 2026-05-20 docs: audit FoundUp build-system registry integration |
| REVIEW | `.claude/worktrees/agent-a856dfecee631f9be` | `docs/workspace-wrapper-model-update` | 2026-05-17 docs: workspace fork -> wrapper model |
| REVIEW | `.claude/worktrees/w9-roc-pipeline-integration-audit` | `worktree-w9-roc-pipeline-integration-audit` | 2026-05-15 docs(consensus): audit ROC candidate pipeline |
| REVIEW | `.claude/worktrees/agent-a3072b92195f6e5a7` | `worktree-agent-a3072b92195f6e5a7` | 2026-05-17 docs: audit RedDog preference capsule boundary |
| REVIEW | `.claude/worktrees/agent-abd459fbbbc75e72d` | `worktree-agent-abd459fbbbc75e72d` | 2026-05-17 docs: specify edge observer interaction schema |
| REVIEW | `.claude/worktrees/agent-ad2c339cf9b6ab9c3` | `worktree-agent-ad2c339cf9b6ab9c3` | 2026-05-17 docs: audit FoundUp DAE layered build flow |
| REVIEW | `.claude/worktrees/agent-a38c0fe37c0231091` | `worktree-agent-a38c0fe37c0231091` | 2026-05-13 feat(wre): token validation in HermesJobExecutor (HXA27) - see note |

**HXA27 note:** `agent-a38c0fe37c0231091`'s commit is HXA27, which already merged
independently as **PR #572**. Diff it against main during execution pre-flight;
if empty/superseded, reclassify as REMOVE. Do not remove it in the audit slice.

## Approved removal allowlist (71)

Each entry satisfies: `ahead==0` (in-main) **OR** has a MERGED PR (squash-merged).
All live under `O:/Foundups-Agent/.claude/worktrees/` unless noted. 37 hold stale
locks and require `git worktree unlock` (or `remove --force --force`) at execution.

| Worktree | Branch | Lock |
|----------|--------|------|
| APCA-W9D | `docs/autopost-completion-audit-phase1` | — |
| FCISRA-W9 | `docs/foundup-canonical-inventory-audit-phase1` | — |
| FCRSA-W9A | `docs/foundup-registry-schema-audit-phase1` | — |
| FPSSA-W9E | `docs/foundup-public-surface-status-audit-phase1` | — |
| FWLBA-W9 | `docs/foundups-work-ledger-brain-audit-phase1` | — |
| M2JRA-W9B | `docs/move2japan-role-audit-phase1` | — |
| MCPFSR-W9 | `docs/mcp-foundup-scope-reaudit-phase1` | — |
| MCPRLS-W9 | `docs/mcp-foundup-scope-registry-loader-spec-phase1` | — |
| MCPS2S-W9 | `docs/mcp-foundup-scope-s2-integration-spec-phase1` | — |
| PQNDA-W9C | `docs/pqn-portal-science-swarm-drift-audit-phase1` | — |
| agent-a08fcd743e4adc5d0 | `feat/hxa26-token-validation-service` | stale-lock pid 26164 |
| agent-a090866179e4d7ef4 | `feat/quorum-verification-enforcement` | stale-lock pid 26164 |
| agent-a1553af9dddea24d1 | `docs/roc-candidate-approval-boundary-repair` | stale-lock pid 380 |
| agent-a1567043c8622c914 | `feat/hxa19-repo-creation-approval-gate` | stale-lock pid 26164 |
| agent-a18622aee4ada241e | `docs/roc-candidate-observability-metric-audit` | stale-lock pid 380 |
| agent-a187a218cffdc35f4 | `feat/hxa20-production-source-gate` | stale-lock pid 26164 |
| agent-a22625e0cbdf94a57 | `cabr-lifecycle-correlation-phase6` | stale-lock pid 26004 |
| agent-a277bff9efbeb3cdb | `feat/cabr-consensus-phase3-auto-persist` | stale-lock pid 26164 |
| agent-a31ff5c53593ab71c | `feat/cabr-store-export-phase9` | stale-lock pid 26004 |
| agent-a44b89910d9d668d9 | `docs/vote-solution-architecture-packet-phase1` | stale-lock pid 380 |
| agent-a5309dac6894ea142 | `feat/cabr-lifecycle-report-export-phase8` | stale-lock pid 26004 |
| agent-a5b33a499cdd31186 | `feat/cabr-lifecycle-query-phase7` | stale-lock pid 26004 |
| agent-a5d1278fb48536509 | `worktree-agent-a5d1278fb48536509` | stale-lock pid 26164 |
| agent-a6dbec63c3170bc4d | `feat/cabr-consensus-finalization` | stale-lock pid 26164 |
| agent-a6f78d5d0fbb4a0fc | `feat/hxa29-token-scope-validation` | stale-lock pid 26164 |
| agent-a725246dcea862ac2 | `docs/012-recursive-improvement-wsp48-annex` | stale-lock pid 380 |
| agent-a7da1ac2a33652c8c | `feat/hxa21-capability-token-infrastructure` | stale-lock pid 26164 |
| agent-a7eb1c4ac8465b49f | `worktree-agent-a7eb1c4ac8465b49f` | stale-lock pid 26164 |
| agent-a83511d4973ff7bf8 | `feat/hxa30-scope-action-class-integration` | stale-lock pid 26164 |
| agent-a85784da8f30040c5 | `feat/hxa23-hermes-guard-integration` | stale-lock pid 26164 |
| agent-a8bff204edaf248f8 | `docs/012-feedback-loop-recursive-improvement-audit` | stale-lock pid 380 |
| agent-a8c9d1069933e25b2 | `feat/hxa24-capability-token-policyflags` | stale-lock pid 26164 |
| agent-a94563978ac51a9b3 | `feat/hxa25-d3-sandbox-execution` | stale-lock pid 26164 |
| agent-a9c75b4959be1e175 | `docs/foundups-3v-engine-vision-concatenation-audit-phase1` | stale-lock pid 380 |
| agent-aa441040aaa233f77 | `docs/sovereign-agent-consensus-roc-dao-readiness-audit` | stale-lock pid 380 |
| agent-aa594f2c6d5003a48 | `feat/cabr-runtime-scoring-engine` | stale-lock pid 26164 |
| agent-aaa208acb63acf50c | `feat/cabr-consensus-phase5-time-correlation` | stale-lock pid 26004 |
| agent-ab4e6f6b43d5648ac | `feat/cabr-consensus-phase4-reporting` | stale-lock pid 26164 |
| agent-ab7fd78b358b1cff2 | `feat/hxa27-hermes-token-validation-integration` | stale-lock pid 26164 |
| agent-ab95ecf806a69b22e | `feat/cabr-consensus-sqlite-audit` | stale-lock pid 26164 |
| agent-abac7f71a80903943 | `feat/reddog-bootstrap-context-retrieval-phase1` | stale-lock pid 12892 |
| agent-abecbc487af14d03b | `feat/cabr-consensus-pipeline-phase10` | stale-lock pid 26004 |
| agent-ac02620e9da5701c8 | `feat/hxa18-hermes-runtime-fixture-safe-harness` | stale-lock pid 26164 |
| agent-ad3775f0d97c7ac60 | `feat/hxa28-d3-native-classification` | stale-lock pid 26164 |
| agent-ad62f4ddac9c26a9b | `docs/dep-security-remediation-classification-phase1` | stale-lock pid 380 |
| agent-ad998a8e0c488774a | `worktree-agent-ad998a8e0c488774a` | stale-lock pid 26164 |
| agent-adaaf184fa322062d | `feat/hxa22-destructive-action-guard-runtime` | stale-lock pid 26164 |
| destructive-action-guard-path-canonicalization | `fix/destructive-action-guard-path-canonicalization` | — |
| foundup-canonical-registry-population | `feat/foundup-canonical-registry-population-phase1` | — |
| foundup-canonical-registry-schema | `feat/foundup-canonical-registry-schema-phase1` | — |
| holoindex-docs-reindex-observation | `docs/holoindex-docs-reindex-observation-phase1` | — |
| holoindex-index-docs-consistency-audit | `feat/holoindex-index-docs-consistency-audit-phase1` | — |
| holoindex-trade-alias-observation | `feat/holoindex-trade-alias-live-observation-phase1` | — |
| redteam-ci-observation | `feat/redteam-ci-observation-phase1` | — |
| redteam-family-a | `feat/redteam-family-a-scope-lock` | — |
| redteam-family-c | `feat/redteam-family-c-holoindex-poisoning` | — |
| redteam-harness-skeleton | `feat/redteam-harness-skeleton` | — |
| redteam-provenance-check | `feat/redteam-harness-provenance-check` | — |
| redteam-regression-spec | `feat/redteam-regression-spec` | — |
| trade-due-diligence-synthetic-regime-pack | `feat/trade-due-diligence-synthetic-regime-pack-phase1` | — |
| vote-concat-audit | `docs/vote-existing-concatenation-audit` | — |
| w1-guard-edge-case-tests | `worktree-w1-guard-edge-case-tests` | — |
| w1-holoindex-hxa-fix | `worktree-w1-holoindex-hxa-fix` | — |
| w1-python-dotenv-remediation | `worktree-w1-python-dotenv-remediation` | — |
| w8-holoindex-status-audit | `w8-holoindex-status-audit` | — |
| w9-agent-security-wsp-annex | `docs/agent-security-stack-wsp-annex-mapping-phase1` | — |
| w9-destructive-guard-edge-audit | `docs/destructive-action-guard-edge-case-audit` | — |
| w_tq3_routing | `research/tq3-per-collection-routing` | — |
| work-ledger-search-integration | `feat/work-ledger-holoindex-search-integration` | — |
| work-ledger-targeted-reindex-cli | `feat/work-ledger-targeted-reindex-cli` | — |
| youtube_proxy_v0194 | `fix/youtube-proxy-v0194-duplicate-remediation` | — |

(2 of the 71 live outside `.claude/worktrees/`: `O:/tmp/w_tq3_routing`
(`research/tq3-per-collection-routing`, #430) and `O:/tmp/youtube_proxy_v0194`
(`fix/youtube-proxy-v0194-duplicate-remediation`, #437). Authoritative paths
regenerable via the Method commands above.)

## Recommended execution path (deferred)

1. Remove the 71 allowlisted worktrees: unlock stale locks, `git worktree remove`,
   then `git worktree prune` to sweep admin files.
2. Triage the 8 REVIEW commits (start with the HXA27 duplicate). Cherry-pick
   keepers onto fresh branches -> PR, then remove.
3. Keep `O:/tmp/w6_autoagent_rescue` until PR #418 closes. `0102-clean-main` is
   012's discretion.

## Deferred: branch hygiene (separate slice)

~30 dangling `worktree-agent-*` branches are already merged into main and are
`git branch -d`-able after their worktrees are removed. **Out of scope here** -
no branches are deleted in the cleanup execution slice either.

## Explicit non-actions

- No `git worktree remove` executed.
- No `git worktree unlock` executed.
- No `git worktree prune` executed.
- No branches created/deleted except this audit artifact branch.
- No source, registry, manifest, or public-surface mutation.

## WSP_97 Truth Boundary Checklist

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | READ_ONLY_AUDIT | YES | Only `git` reads + `gh pr list`; no remove/unlock/prune run |
| 2 | NO_SOURCE_CODE_CHANGE | YES | No files under `modules/` touched |
| 3 | NO_BRANCH_DELETE | YES | Zero branches deleted |
| 4 | NO_WORKTREE_REMOVED | YES | `git worktree remove` not invoked |
| 5 | NO_PRIMARY_CHECKOUT_REMOVAL | YES | Primary excluded by exact path |
| 6 | NO_OPEN_PR_WORKTREE_REMOVAL | YES | #418 classified KEEP |
| 7 | NO_REVIEW_WORKTREE_REMOVAL | YES | 8 REVIEW classified PROTECTED |
| 8 | PROTECTED_PATHS_EXCLUDED | YES | 11 protected enumerated; excluded from allowlist |
| 9 | ALLOWLIST_DERIVED_FROM_MERGE_TRUTH | YES | Every entry `ahead==0` OR PR MERGED |
| 10 | NO_REGISTRY_MUTATION | YES | Audit only |
| 11 | NO_MANIFEST_MUTATION | YES | Audit only |
| 12 | NO_PUBLIC_SURFACE_MUTATION | YES | Audit only |
| 13 | EXECUTION_GATED | YES | Removal deferred to `WORKTREE_REGISTRY_CLEANUP_EXECUTION_PHASE1` |

## Internal Review Verdict

**READY** - decision-only audit; 71 safe-remove allowlist and 11 protected
entries derived from merge truth; execution gated behind explicit approval.
