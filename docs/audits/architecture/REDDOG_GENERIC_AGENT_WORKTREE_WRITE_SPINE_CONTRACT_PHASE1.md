# REDDOG_GENERIC_AGENT_WORKTREE_WRITE_SPINE_CONTRACT_PHASE1

Status: SPECIFIED_NOT_IMPLEMENTED  
Slice type: docs/static contract only  
Authority: no runtime authority change  
WSP: 00, 15, 34, 46, 50, 54, 95, 96, 97

## Purpose

This contract defines the generic worktree write spine RedDog needs before it can safely
delegate arbitrary codebase work to WRE workers.

The contract does not implement the writer. It freezes the invariants that a future
`REDDOG_GENERIC_AGENT_WORKTREE_WRITER_DRYRUN_PHASE1` must satisfy.

Hard rule:

```text
GENERIC DOES NOT MEAN UNBOUNDED.
```

A generic writer is only allowed to author a scoped change in an isolated worktree, under
a signed work order, full execution-valve decision, pin-independent denylist, consensus
receipt where required, and draft-PR-only promotion.

## Direct-read evidence (WSP_50)

OBSERVED:

- `docs/audits/architecture/REDDOG_GENERIC_AGENT_WORKTREE_WRITE_SPINE_AUDIT_PHASE1.md`
  finds the reusable generic spine inside the FoundUp live writer but recommends
  `KEEP_FOUNDUP_SPECIFIC_FOR_NOW + EXTRACT_GENERIC_SPINE_CONTRACT_NEXT`.
- `modules/communication/moltbot_bridge/src/reddog_wre_execution_valve.py` defines
  `VALVE_OPEN_WORKTREE_CREATE` and the full `evaluate_reddog_execution_valve(...)`
  path with spine-chain validation and rejection reasons.
- `modules/communication/moltbot_bridge/src/reddog_wre_worktree_create.py` creates
  only an isolated worktree from an accepted executor plan and open worktree valve.
- `modules/communication/moltbot_bridge/src/reddog_wre_cwd_guard.py` rejects mutating
  worker operations unless the operation cwd resolves inside the isolated worktree and
  outside the shared repo checkout.
- `modules/foundups/agent/src/worktree_pr_runner.py` is already generic as a runner, but
  its use must be governed by a higher-level spine.
- `modules/foundups/agent/src/foundup_scaffold_writer_live.py` is FoundUp-specific and
  must not be generalized by loosening the `modules/foundups/{id}` root pin.

INFERRED:

- The reusable primitive is not "write anywhere." It is "materialize a domain profile in
  an isolated worktree and open a draft PR." The domain profile must re-derive its root
  from signed authority rather than trusting caller-supplied paths.

## 1. Generic domain profile contract

Future runtime must define `GenericAgentWorktreeDomainProfile`.

Required fields:

| Field | Type | Rule |
| --- | --- | --- |
| `profile_id` | string | Stable id such as `foundup_scaffold`, `module_patch`, or `docs_patch` |
| `operation` | string | Work-order operation this profile accepts |
| `artifact_contract_type` | string | Contract shape the materializer accepts |
| `id_validator` | callable/spec ref | Validates the domain id before path derivation |
| `canonical_root_fn` | callable/spec ref | Re-derives the authorized root from signed request data |
| `materialize_fn` | callable/spec ref | Writes only planned artifacts under the canonical root |
| `allowed_path_patterns` | list[string] | Derived or stricter than canonical root; never caller-expanded |
| `denied_path_patterns` | list[string] | Includes pin-independent governance/CI/secrets denies |
| `required_tests` | list[string] | Tests the future writer must run inside the worktree |
| `branch_prefix` | string | Must not be `main`, `master`, protected branch, or base ref |
| `draft_pr_only` | bool | Must be true until a separate merge authority gate exists |

Caller-supplied `allowed_paths` can narrow the profile. It must not widen the profile.

## 2. Required authority inputs

Future generic writer dry-run or live implementation must require:

| Input | Required | Rule |
| --- | --- | --- |
| `RedDogOperatorLoopWardrobeSelectionReceipt` | yes | Must select `wsp97_sovereign_execution` and governed execution plane |
| `RedDogDelegatedWorkAuthority` verification | yes | Signature accepted, fresh permission snapshot, scope-bound |
| `SignedReceiptChainVerificationResult` | yes | Accepted before reward-bearing or authority-bearing receipt linkage |
| `ExecutionValveDecision` | yes | Must be the full `evaluate_reddog_execution_valve(...)` result |
| `VALVE_OPEN_WORKTREE_CREATE` | yes | Environment flag alone is insufficient |
| `consensus_receipt_digest` | tiered | Required for high-authority or 012-out-of-loop operation |
| `WreCwdGuardResult` | yes before mutation | Must pass for every mutating command cwd |

The writer must reject `_resolve_valve_state(env, [])` style shortcuts. A full valve
decision digest plus empty `rejection_reasons` are mandatory.

## 3. Re-derived root invariant

The canonical write root must be re-derived from signed request fields and the selected
domain profile.

Forbidden:

- Trusting caller-supplied `allowed_paths` as the canonical root.
- Accepting a root that points at repo root, WSP framework, CI config, HoloIndex config,
  secrets, permission stores, valve source, signature source, or governance documents.
- Allowing a materializer to emit outside the re-derived root through traversal, symlink,
  Windows device-prefix, extended-length path, or case-normalization bypass.

Required:

- `canonical_root_fn(signed_request, profile) -> repo_relative_root`
- `allowed_paths <= canonical_root`
- `denied_path_patterns` applied after normalization and before write
- on-disk post-write validation that every artifact remains inside the canonical root

## 4. Pin-independent denylist

Every profile inherits these denied surfaces unless a separate, higher authority contract
explicitly overrides them:

- `.env`, `.env.*`, secret and credential files
- `.github/workflows/**`
- repository settings and CodeQL/security config
- WSP framework protocol files
- HoloIndex indexer/ranking/config files
- RedDog valve, policy gate, signature verifier, receipt-chain, and operator-loop source
- permission stores, nonce stores, token stores, wallet paths, reward settlement paths
- protected branch refs, merge automation, release automation

This prevents a writer from editing its own authority substrate.

## 5. Worktree and command boundary

Future implementation must reuse or satisfy the same invariants as:

- `reddog_wre_worktree_create.py`: create isolated worktree only after accepted plan and
  `VALVE_OPEN_WORKTREE_CREATE`.
- `reddog_wre_cwd_guard.py`: mutating command cwd must be absolute, outside shared repo,
  inside isolated worktree, and free of device/extended-length prefixes.
- `worktree_pr_runner.py`: draft PR only; no ready, merge, release, or promotion action.

The generic writer must not execute task commands in the shared checkout.

This is the pin-independent governance/CI denylist boundary for a generic worktree
writer: protected authority surfaces stay denied even when a domain profile changes.

## 6. Receipt chain

Future `GenericAgentWorktreeWriteReceipt` must include:

| Field | Rule |
| --- | --- |
| `domain_profile_id` | Profile used for root derivation |
| `canonical_root_digest` | Digest of re-derived root and allowed/denied sets |
| `selection_receipt_digest` | Operator-loop wardrobe selector receipt |
| `signed_authority_digest` | Signed delegated work authority |
| `receipt_chain_terminal_hash` | Signed receipt-chain terminal hash |
| `execution_valve_decision_digest` | Full valve decision digest |
| `consensus_receipt_digest` | Required when authority tier demands it |
| `worktree_create_result_digest` | Isolated worktree creation result |
| `cwd_guard_receipt_digest` | Last mutating cwd guard receipt |
| `artifact_manifest_digest` | Planned vs written artifact manifest digest |
| `draft_pr_url` | Draft only |
| `no_merge_performed` | Always true until merge authority exists |
| `no_reward_settlement_performed` | Always true in writer path |

Unsigned receipts are advisory only and cannot be reward-bearing authority evidence.

## 7. Fail-closed rejection rules

Reject if any of these are true:

- Missing or non-sovereign wardrobe selection receipt.
- Missing accepted signed work authority.
- Stale permission snapshot.
- Missing accepted signed receipt chain.
- Missing required consensus receipt for authority tier.
- Valve state is not `VALVE_OPEN_WORKTREE_CREATE`.
- Valve decision has rejection reasons or no decision digest.
- Canonical root cannot be re-derived from signed request.
- Caller paths widen the profile.
- Denied path appears in planned or written artifacts.
- Worktree path or operation cwd fails WRE cwd guard.
- Branch is protected, base ref, `main`, or `master`.
- Writer attempts ready/merge/push-to-protected/release/reward settlement.
- HoloIndex write-sensitive INDEX_GAP is unresolved.

## 8. WSP_15 sequence

Ordered next slices:

1. `REDDOG_GENERIC_AGENT_WORKTREE_WRITER_DRYRUN_PHASE1`
2. `REDDOG_WRE_GOVERNED_SHELL_RUNNER_CONTRACT_PHASE1`
3. `REDDOG_WRE_GOVERNED_SHELL_RUNNER_DRYRUN_PHASE1`
4. `REDDOG_MERGE_AUTHORITY_CONTRACT_PHASE1`

Do not build a live generic writer before the dry-run writer proves root derivation,
pin-independent denylist, cwd guard, and receipt chain behavior.

## 9. HoloIndex boundary

OBSERVED:

- Query `RedDog generic agent worktree write spine contract cwd guard signed valve`
  surfaced the prior generic-spine audit, WRE execution valve, executor dry-run, and cwd
  guard surfaces.
- The new contract is not indexed until WRE/CI runs the freshness/re-index path.

Recorded follow-up:

`HOLOINDEX_REDDOG_GENERIC_AGENT_WORKTREE_WRITE_SPINE_CONTRACT_INDEX_GAP_PHASE1`

RedDog runtime must not re-index HoloIndex.

## 10. WSP_97 truth table

| Claim | Label | Evidence |
| --- | --- | --- |
| FoundUp live writer contains a reusable worktree spine | OBSERVED | Prior audit coupling table |
| FoundUp writer remains FoundUp-specific | OBSERVED | `modules/foundups/{id}` root and WSP-49 materializer |
| Generic writer exists today | FALSE | Prior audit found copy-not-call reuse only |
| Generic root may be caller-supplied | FALSE | Contract requires re-derived root |
| Full valve decision binding is required | SPECIFIED_NOT_IMPLEMENTED | Contract requirement; future dry-run |
| Pin-independent denylist is required | SPECIFIED_NOT_IMPLEMENTED | Contract requirement; future dry-run |
| WRE/CI owns HoloIndex re-index | OBSERVED | Existing HoloIndex governance lane |

## Explicit non-goals

- No generic writer implementation.
- No live write.
- No shell runner.
- No merge authority.
- No extension runtime wiring.
- No HoloIndex re-index.
- No new WSP.
- No weakening of the FoundUp-specific live writer.

## Truth Boundary Checklist

- DOCS_ONLY: YES
- NO_RUNTIME_CODE: YES
- NO_LIVE_WRITE: YES
- NO_SHELL: YES
- NO_MERGE_AUTHORITY: YES
- NO_HOLOINDEX_REINDEX: YES
- GENERIC_NOT_UNBOUNDED: YES
- WSP_97_LABELS_USED: YES
- SPECIFIED_NOT_IMPLEMENTED_EXPLICIT: YES
