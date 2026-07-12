# REDDOG_MERGE_AUTHORITY_CONTRACT_PHASE1

Status: SPECIFIED_NOT_IMPLEMENTED
Slice type: docs/static contract only
Authority: no runtime authority change
WSP: 00, 15, 50, 71, 95, 96, 97, 100

## Purpose

This contract defines the separate merge authority RedDog needs before any future
worker, shell runner, or worktree writer can promote a draft PR into `main`.

The contract does not implement merge authority. It freezes the invariants that a
future dry-run and later live merge-authority implementation must satisfy.

Hard rule:

```text
MERGE AUTHORITY IS NOT REVIEW, NOT CI, NOT A TOKEN, AND NOT A COMMAND STRING.
MERGE AUTHORITY IS A SIGNED, NON-SELF, CONSENSUS-CHECKED PROMOTION DECISION.
```

RedDog may author work. RedDog may verify work. RedDog may produce signed receipts.
None of those facts alone authorize merge.

## Direct-read evidence (WSP_50)

OBSERVED:

- `docs/audits/architecture/REDDOG_GOVERNED_REPO_WORK_ORDER_CONTRACT_PHASE1.md`
  states that merge authority is separate, that single RedDog compromise must not
  compromise a repo, and that F0 merge remains strongest-gated.
- `docs/contracts/REDDOG_PRINCIPAL_IDENTITY_AND_DELEGATION_CONTRACT_PHASE1.md`
  defines signed principal identity, delegated work authority, nonce, expiry, scope,
  and signed receipt rules. Role text is never authority.
- `docs/audits/architecture/REDDOG_SIGNING_KEY_ISOLATION_CONTRACT_PHASE1.md`
  requires key isolation, kernel-attested requester identity, sign-what-you-validate,
  consensus/co-sign for high-authority tiers, and no same-user key boundary.
- `docs/audits/architecture/REDDOG_RECURSIVE_SELF_GOVERNANCE_THREAT_MODEL_PHASE1.md`
  identifies self-promotion, social-review capture, mutable quorum membership,
  executable supply chain, economic gaming, and availability/fail-open risks.
- `docs/audits/architecture/REDDOG_GENERIC_AGENT_WORKTREE_WRITE_SPINE_CONTRACT_PHASE1.md`
  and `REDDOG_WRE_GOVERNED_SHELL_RUNNER_CONTRACT_PHASE1.md` explicitly stop at
  draft PR / no merge authority.
- `modules/communication/moltbot_bridge/src/reddog_wre_governed_shell_runner_dryrun.py`
  emits a dry-run shell receipt with `no_merge_performed=True`.
- Repository search shows legacy `gh pr merge` references in non-RedDog surfaces. Those
  are OBSERVED legacy automation, not RedDog merge authority precedents.

INFERRED:

- Merge authority must be the final promotion gate over a completed PR, not a capability
  held by the worker that authored the branch or the verifier that reviewed it.

## 1. Authority separation model

Future merge authority must separate these roles:

| Role | May do | Must not do |
| --- | --- | --- |
| Author RedDog / worker | Create branch, worktree, patch, tests, draft PR under prior gates | Approve or merge its own work |
| Shell runner | Execute governed test/static commands inside worktree | Mark PR ready, push protected refs, merge, release, publish |
| Reviewer / sentinel RedDog | Sign review opinions and verifier receipts | Merge |
| Merge authority evaluator | Decide whether promotion is admissible | Execute shell, edit files, invent missing evidence |
| Promoter / 012 / DAO | Provide final signed promotion decision | Bypass required receipts for high-authority work |

The promoter must be provably not the same principal, RedDog instance, worker lane, or
signing key that authored the work. Self-promotion is fail-closed.

## 2. Merge authority request

Future runtime must define `RedDogMergeAuthorityRequest`.

Required fields:

| Field | Rule |
| --- | --- |
| `merge_request_id` | Unique id for this promotion attempt |
| `work_order_id` | Bound to signed delegated work authority |
| `repo_full_name` | Target repository; must match signed authority |
| `pr_number` | Draft/open PR to evaluate |
| `base_ref` | Target branch; protected branches require strongest policy |
| `head_ref` | Candidate branch; must not equal `base_ref` |
| `head_sha` | Exact PR head SHA to merge; expected-head lock required |
| `author_principal_id` | Work author principal |
| `author_reddog_id` | Work author RedDog instance |
| `promoter_principal_id` | Principal requesting promotion |
| `promoter_reddog_id` | Optional promoter RedDog instance; must differ from author |
| `signed_work_authority_digest` | Accepted delegated work authority |
| `signed_receipt_chain_terminal_hash` | Accepted receipt-chain verification |
| `worktree_write_receipt_digest` | Accepted worktree writer receipt |
| `shell_run_receipt_digests` | Required CI/test/static-check receipts |
| `ci_status_digest` | Machine-derived CI/check-run status summary |
| `diff_summary_digest` | Machine-derived diff/scope summary, not RedDog prose |
| `review_opinion_digests` | Signed sentinel/reviewer opinions |
| `consensus_receipt_digest` | Required by WSP_96 for high-authority promotion |
| `holoindex_freshness_receipt_digest` | Required for repo-sensitive promotion |
| `permission_snapshot_digest` | Fresh repo permission snapshot for promoter and author |
| `policy_tier` | `f0_sovereign`, `foundup_repo`, `docs_only`, or `external_foundup` |
| `requested_merge_method` | `squash`, `merge`, or `rebase`; policy constrained |
| `expiry` | ISO-8601 UTC; stale request rejected |
| `nonce` | Single-use promotion nonce |

The request must not contain raw secrets, private keys, bearer tokens, or raw CI logs
that have not passed redaction.

## 3. Merge decision and receipt

Future runtime must define `RedDogMergeAuthorityDecision`.

Required fields:

| Field | Rule |
| --- | --- |
| `decision` | `MERGE_AUTHORITY_ACCEPT` or `MERGE_AUTHORITY_REJECT` |
| `merge_request_id` | Bound request id |
| `work_order_id` | Bound work order |
| `pr_number` | Bound PR |
| `expected_head_sha` | Exact SHA the future merge call must use |
| `merge_method` | Chosen method, policy constrained |
| `promoter_signature_digest` | Signed promoter authority |
| `consensus_receipt_digest` | Required when policy tier demands it |
| `ci_status_digest` | All required checks green or policy-exempted |
| `review_set_digest` | Required signed review opinions |
| `machine_diff_summary_digest` | Reviewer-visible source of truth |
| `holoindex_freshness_receipt_digest` | Freshness evidence |
| `rejection_reasons` | Empty only on accept |
| `no_merge_performed` | Always true in contract/dry-run phases |
| `no_reward_settlement_performed` | Always true |
| `no_holoindex_reindex_performed` | Always true |

Future live implementation must emit `RedDogMergeAuthorityReceipt` after any merge
attempt. The receipt must include the merge API result, expected head SHA, actual merged
SHA if any, and a post-merge HoloIndex freshness work item. Unsigned merge receipts are
advisory only and cannot be reward-bearing.

## 4. Required evidence inputs

Future dry-run and live merge authority must require:

| Input | Required | Rule |
| --- | --- | --- |
| Signed delegated work authority | yes | Accepted, unexpired, non-revoked, repo/path/scope bound |
| Signed receipt-chain verification | yes | Accepted terminal hash for this work order |
| Worktree writer receipt | yes | Draft PR only; no merge performed |
| Governed shell receipts | yes | Required tests/static checks executed under governed shell profiles |
| CI/check-run status | yes | Machine-derived status for exact head SHA |
| Machine diff/scope summary | yes | RedDog prose cannot be the source of truth |
| Signed reviewer opinions | tiered | At least one independent reviewer; more for high authority |
| WSP_96 consensus receipt | tiered | Required for F0, source, governance, security, or 012-out-of-loop work |
| HoloIndex freshness receipt | yes | Fresh enough for changed paths; INDEX_GAP blocks repo-sensitive promotion |
| Promoter permission snapshot | yes | Fresh GitHub/repo permission snapshot for promoter principal |
| Single-use nonce | yes | Replay rejected |

Environment flags, role labels, Copy MD, chat text, and a raw sovereign token are not
sufficient by themselves.

## 5. F0 and external FoundUp policy tiers

Policy tiers:

- `f0_sovereign`: Foundups-Agent core repo or authority substrate. Requires 012/DAO
  signed promotion, WSP_96 consensus, independent reviewer set, exact-head merge lock,
  machine diff summary, all required checks green, and explicit protected-branch policy.
- `foundup_repo`: A FoundUp repo owned by the principal. Requires signed owner scope,
  fresh permission snapshot, no governance-substrate path edits unless elevated to
  `f0_sovereign`, and independent review according to repo policy.
- `docs_only`: Documentation-only promotion may use a lower reviewer threshold only if
  changed paths exclude WSP framework, authority docs, CI, HoloIndex, permission stores,
  and merge automation.
- `external_foundup`: Requires signed delegation from that FoundUp owner. The local 012
  principal does not automatically confer authority over external repos.

F0 autonomous merge remains SPECIFIED_NOT_IMPLEMENTED. This contract defines the future
gate; it does not authorize RedDog to merge F0 today.

## 6. Non-self promotion and reviewer integrity

Fail closed when:

- `author_principal_id == promoter_principal_id` for high-authority tiers unless an
  explicit 012/DAO override policy is signed and recorded.
- `author_reddog_id == promoter_reddog_id`.
- The same signing key signs author, reviewer, and promoter receipts.
- Reviewer opinions are generated by the same lane that authored the patch.
- PR body text is the only evidence. Reviewers must see a machine-derived diff/scope
  summary and the exact changed file list.
- Reviewer or consensus membership changes during the round without pinning a signer-set
  snapshot digest.

This owns the self-promotion and social-review-capture risks identified by the recursive
self-governance threat model.

## 7. Protected surfaces

Merge authority is strongest-gated when changes touch:

- WSP framework protocols
- RedDog valve, signature verifier, receipt chain, operator-loop selector, merge authority
  implementation, or permission/nonce stores
- HoloIndex indexer, ranking, freshness, or re-index automation
- CI workflows, CodeQL/security config, release/deploy/publish automation
- wallets, reward settlement, CABR/reward-scoring stores
- `.env`, secret stores, private key handling, or WSP_71 boundaries

For these surfaces, docs-only and ordinary source policies are insufficient. WSP_96
consensus plus 012/DAO promotion is mandatory.

## 8. CI and check-run policy

Required:

- All required checks green for the exact `head_sha`, or an explicit signed policy
  exemption with reason and scope.
- CodeQL/security failures block merge unless the changed files are demonstrably outside
  the affected language/surface and a signed sentinel records the exemption.
- Report-only checks must be recorded but may not alone block unless policy says so.
- Re-running checks must preserve the same head SHA or invalidate the decision.

The merge authority evaluator must not run tests itself. It consumes CI and governed
shell receipts. Shell execution remains owned by the governed shell runner.

## 9. HoloIndex boundary

OBSERVED:

- Query `RedDog merge authority contract signed receipt chain sovereign token merge PR
  authority` surfaced the principal identity/delegation contract, signing-key isolation,
  governed work-order contract, recursive self-governance threat model, and adjacent
  receipt/redaction surfaces.
- No canonical RedDog merge authority contract existed before this slice.

Required future behavior:

- RedDog runtime never re-indexes HoloIndex during merge evaluation.
- Merge authority consumes a freshness receipt produced by WRE/CI.
- INDEX_GAP on changed paths touching code, WSPs, authority, CI, HoloIndex, security, or
  docs that affect governance blocks promotion until WRE/CI records targeted freshness.
- Post-merge, WRE/CI must enqueue targeted re-index/freshness work for changed paths.

Recorded follow-up:

`HOLOINDEX_REDDOG_MERGE_AUTHORITY_CONTRACT_INDEX_GAP_PHASE1`

## 10. Fail-closed rejection rules

Reject if any of these are true:

- missing accepted signed delegated work authority
- missing accepted signed receipt-chain terminal hash
- missing worktree writer receipt or shell run receipts required by policy
- missing exact-head CI/check-run status
- required check failed, pending, stale, or from a different head SHA
- missing machine-derived diff/scope summary
- missing independent signed review opinion
- missing WSP_96 consensus for high-authority tier
- promoter is same principal/RedDog/signing key as author when policy forbids it
- stale permission snapshot, expired request, or reused nonce
- changed paths include protected surfaces without strongest gate
- HoloIndex INDEX_GAP or missing freshness receipt for repo-sensitive promotion
- requested merge method violates policy
- request includes raw secrets, private keys, bearer tokens, or unredacted logs
- any evidence digest cannot be verified

## 11. WSP_15 sequence

Ordered next slices:

1. `REDDOG_MERGE_AUTHORITY_DRYRUN_PHASE1`
2. `REDDOG_MERGE_AUTHORITY_LIVE_PHASE1` (blocked until dry-run, consensus, and 012/DAO
   promotion policy are implemented and tested)
3. `HOLOINDEX_INDEX_GAP_TO_WRE_WORKITEM_PHASE1`
4. `HOLOINDEX_CI_FRESHNESS_GATE_PHASE1`

Do not implement live merge until the dry-run proves non-self promotion, exact-head CI,
review/consensus, HoloIndex freshness, protected-surface gating, and signed receipt
emission.

## 12. WSP_97 truth table

| Claim | Label | Evidence |
| --- | --- | --- |
| RedDog worktree and shell paths stop at no-merge today | OBSERVED | Generic writer and shell runner contracts/modules |
| Principal identity and delegated work authority are specified | OBSERVED | Ratified identity/delegation contract |
| Signed key isolation is specified | OBSERVED | E0 signing-key isolation contract |
| Self-promotion is a modeled threat | OBSERVED | Recursive self-governance threat model |
| Legacy merge helpers exist elsewhere | OBSERVED | Repository search for `gh pr merge` |
| Legacy merge helpers are RedDog authority | FALSE | No signed RedDog merge authority binding |
| RedDog merge authority exists today | FALSE | No canonical module/contract before this slice |
| Future merge authority must be separate from author/reviewer | SPECIFIED_NOT_IMPLEMENTED | This contract |
| F0 autonomous merge is authorized today | FALSE | Explicitly out of scope and strongest-gated |
| RedDog runtime may re-index HoloIndex during merge | FALSE | WRE/CI owns freshness |

## Explicit non-goals

- No runtime merge authority implementation.
- No `gh pr ready` or `gh pr merge` call.
- No GitHub API call.
- No branch, tag, release, deploy, publish, or protected-ref mutation.
- No file mutation outside this contract and static tests.
- No shell runner change.
- No extension runtime wiring.
- No reward settlement.
- No HoloIndex re-index.

## Truth Boundary Checklist

- DOCS_ONLY: YES
- NO_RUNTIME_CODE: YES
- NO_GITHUB_API_CALL: YES
- NO_GH_PR_READY_OR_MERGE: YES
- NO_BRANCH_OR_PROTECTED_REF_MUTATION: YES
- NO_SHELL: YES
- NO_REWARD_SETTLEMENT: YES
- NO_HOLOINDEX_REINDEX: YES
- SELF_PROMOTION_REJECTED: YES
- MACHINE_DIFF_SUMMARY_REQUIRED: YES
- WSP_96_HIGH_AUTHORITY_CONSENSUS_REQUIRED: YES
- WSP_97_LABELS_USED: YES
- SPECIFIED_NOT_IMPLEMENTED_EXPLICIT: YES
