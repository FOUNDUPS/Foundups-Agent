# REDDOG_WRE_GOVERNED_SHELL_RUNNER_CONTRACT_PHASE1

Status: SPECIFIED_NOT_IMPLEMENTED
Slice type: docs/static contract only
Authority: no runtime authority change
WSP: 00, 11, 15, 50, 53, 71, 95, 97

## Purpose

This contract defines the future WRE-owned governed shell runner RedDog needs before
it can safely execute tests, linters, formatters, or bounded worker commands inside an
isolated worktree.

The contract does not implement command execution. It freezes the invariants that a
future `REDDOG_WRE_GOVERNED_SHELL_RUNNER_DRYRUN_PHASE1` must satisfy.

Hard rule:

```text
SHELL AUTHORITY IS NOT A STRING. IT IS A SIGNED, SCOPED, CWD-GUARDED, RECEIPTED COMMAND.
```

## Direct-read evidence (WSP_50)

OBSERVED:

- `WSP_framework/src/WSP_11_WRE_Standard_Command_Protocol.md` defines WRE command
  interaction as standardized command intent, not arbitrary shell text.
- `WSP_framework/src/WSP_53_Symbiotic_Environment_Integration_Protocol.md` makes host
  environment interaction a WRE-mediated execution layer.
- `WSP_framework/src/WSP_71_Secrets_Management_Protocol.md` requires permission-bound
  secret access, no repository secret persistence, and auditable secret handling.
- `modules/communication/moltbot_bridge/src/reddog_wre_cwd_guard.py` already provides
  the cwd isolation predicate for mutating worker operations.
- `modules/communication/moltbot_bridge/src/reddog_generic_agent_worktree_writer_dryrun.py`
  proves the generic worktree-write spine up to a dry-run receipt without running shell.
- Repository search finds many legacy `subprocess` call sites. Those are OBSERVED legacy
  execution surfaces, not authority precedents for RedDog.

INFERRED:

- The governed shell runner must be a single WRE-owned seam with explicit command
  profiles. It must not bless scattered legacy subprocess usage as RedDog authority.

## 1. Governed shell command profile

Future runtime must define `GovernedShellCommandProfile`.

Required fields:

| Field | Type | Rule |
| --- | --- | --- |
| `profile_id` | string | Stable id such as `pytest_readonly`, `node_contract_test`, `python_format_check` |
| `command_kind` | string | test, lint, format_check, static_analysis, build_check, or readonly_probe |
| `argv_prefix` | list[string] | Exact argv prefix allowlist; no shell string |
| `allowed_arg_patterns` | list[string] | Bounded patterns for trailing args |
| `denied_arg_patterns` | list[string] | Destructive, network, secret, merge, publish, and authority-substrate denies |
| `requires_cwd_guard` | bool | Must be true for any worktree command |
| `requires_worktree` | bool | Must be true for mutating or repo-sensitive command |
| `timeout_seconds` | int | Positive bounded timeout |
| `max_stdout_bytes` | int | Bounded capture size |
| `max_stderr_bytes` | int | Bounded capture size |
| `secret_env_refs` | list[string] | Secret handles only; raw secret values forbidden |
| `output_redaction_policy` | string | Redacts secrets before receipt/log/telemetry |
| `draft_pr_only` | bool | Must be true until merge authority exists |

`argv_prefix` is an argv-list prefix, not a shell command string. `shell=True` is
forbidden.

## 2. Governed shell run request

Future runtime must define `GovernedShellRunRequest`.

Required fields:

| Field | Rule |
| --- | --- |
| `work_order_id` | Bound to signed authority |
| `profile_id` | Must match a known `GovernedShellCommandProfile` |
| `argv` | List of strings; exact prefix + allowed trailing args only |
| `operation_cwd` | Absolute cwd inside isolated worktree |
| `worktree_path` | Absolute isolated worktree path |
| `repo_root` | Absolute shared repo path |
| `stdin_policy` | `none` by default; bounded explicit input only |
| `env_policy` | Minimal scrubbed env plus secret refs resolved by WSP_71 boundary |
| `generic_writer_dryrun_receipt_digest` | Required for write/test flows after generic writer dry-run |
| `signed_authority_digest` | Required |
| `signed_receipt_chain_terminal_hash` | Required |
| `execution_valve_decision_digest` | Required |
| `cwd_guard_receipt_digest` | Required before execution |
| `holoindex_freshness_receipt_digest` | Required for repo-sensitive command |

The request must not contain raw secrets, private keys, or bearer tokens.

## 3. Required authority inputs

Future governed shell runner dry-run or live implementation must require:

| Input | Required | Rule |
| --- | --- | --- |
| `RedDogOperatorLoopWardrobeSelectionReceipt` | yes | `wsp97_sovereign_execution` and governed execution plane |
| `RedDogDelegatedWorkAuthority` verification | yes | Accepted, fresh permission snapshot, command scope-bound |
| `SignedReceiptChainVerificationResult` | yes | Accepted before command receipt can be reward-bearing |
| `ExecutionValveDecision` | yes | Full `evaluate_reddog_execution_valve(...)` result |
| `VALVE_OPEN_WORKTREE_CREATE` | yes | Shell may run only inside the worktree authority window |
| `WreCwdGuardResult` | yes | Must pass for the exact `operation_cwd` |
| `GenericAgentWorktreeWriterDryRunReceipt` | conditional | Required for commands that validate or test generated artifacts |
| `consensus_receipt_digest` | tiered | Required for high-authority or 012-out-of-loop commands |

Environment flags and role text are not authority.

## 4. Command policy

Allowed classes for the first dry-run implementation:

- readonly probes that do not mutate the worktree
- test commands such as `python -m pytest ...`
- static checks such as `git diff --check` only if implemented through an approved
  no-mutation profile and scoped cwd guard
- package-local contract checks that do not publish, install globally, or alter locks

Forbidden classes:

- shell strings, shell metacharacter interpretation, `shell=True`
- destructive commands: delete, move, chmod/chown, disk format, registry edits
- network transfer commands unless a later contract explicitly allows them
- `git push`, `git merge`, `git reset`, `git checkout`, protected branch mutation
- `gh pr ready`, `gh pr merge`, release, publish, deploy, or package registry write
- HoloIndex `--index-*`, `--reindex-*`, or freshness-store mutation from RedDog runtime
- secret inspection commands, env dumps, token print, wallet/key export
- editing WSP framework, valve source, signature verifier, receipt-chain, permissions,
  nonce stores, HoloIndex config, CI workflows, or merge automation

The shell runner is not the merge authority and not the HoloIndex maintenance owner.

## 5. CWD and worktree boundary

Future implementation must call `validate_wre_worker_operation_cwd(...)` before every
command that can touch filesystem or git state.

Required:

- `repo_root` absolute
- `worktree_path` absolute
- `operation_cwd` absolute
- operation_cwd inside isolated worktree
- operation_cwd outside shared repo root
- no Windows device or extended-length prefix
- no filesystem-root worktree

Failure is fail-closed before any subprocess is reached.

## 6. Secret and environment boundary

WSP_71 is mandatory.

Rules:

- raw secret values are never accepted in request JSON
- private keys are never accepted
- env is scrubbed by default
- secret use is by reference handle only
- secret resolver must permission-check the requesting RedDog identity
- secret values are never logged, echoed, hashed into public receipts, or sent to
  command argv
- output is redacted before receipt, telemetry, Copy MD, or model context

## 7. Receipt contract

Future `GovernedShellRunReceipt` must include:

| Field | Rule |
| --- | --- |
| `run_receipt_id` | Deterministic receipt id |
| `work_order_id` | Bound work order |
| `profile_id` | Command profile used |
| `argv_digest` | Digest of argv; raw argv optional only if safe |
| `cwd_guard_receipt_digest` | Exact cwd guard result |
| `signed_authority_digest` | Accepted delegated work authority |
| `receipt_chain_terminal_hash` | Accepted receipt chain terminal |
| `execution_valve_decision_digest` | Full valve decision digest |
| `generic_writer_dryrun_receipt_digest` | Required when artifact validation command |
| `holoindex_freshness_receipt_digest` | Repo-sensitive query freshness evidence |
| `exit_code` | Captured after command in future live runner |
| `timed_out` | Captured after command in future live runner |
| `stdout_digest` | Digest of redacted bounded stdout |
| `stderr_digest` | Digest of redacted bounded stderr |
| `output_truncated` | True when byte caps apply |
| `no_merge_performed` | Always true |
| `no_reward_settlement_performed` | Always true |
| `no_holoindex_reindex_performed` | Always true |

Unsigned shell receipts are advisory only.

## 8. HoloIndex boundary

OBSERVED:

- Query `RedDog WRE governed shell runner contract command execution cwd guard signed authority`
  surfaced WSP_11, WSP_53, WSP_71, RedDog policy/receipt surfaces, and legacy subprocess
  call sites.
- No canonical governed shell runner exists yet.

Recorded follow-up:

`HOLOINDEX_REDDOG_WRE_GOVERNED_SHELL_RUNNER_CONTRACT_INDEX_GAP_PHASE1`

RedDog runtime must not re-index HoloIndex. WRE/CI owns freshness receipts and targeted
re-index after merge.

## 9. Fail-closed rejection rules

Reject if any of these are true:

- missing accepted signed work authority
- missing accepted signed receipt chain
- missing sovereign wardrobe selection receipt
- valve state is not `VALVE_OPEN_WORKTREE_CREATE`
- cwd guard fails
- profile is unknown or not draft-pr-only
- argv is empty, not a list, or does not match profile prefix
- argv contains shell metacharacters or forbidden args
- request contains raw secrets, private keys, bearer tokens, or env dump intent
- command attempts git push/merge/reset/protected branch mutation
- command attempts `gh pr ready`, `gh pr merge`, release, publish, deploy, or reward
- command attempts HoloIndex re-index from RedDog runtime
- output cannot be redacted or bounded
- write-sensitive INDEX_GAP is unresolved

## 10. WSP_15 sequence

Ordered next slices:

1. `REDDOG_WRE_GOVERNED_SHELL_RUNNER_DRYRUN_PHASE1`
2. `REDDOG_MERGE_AUTHORITY_CONTRACT_PHASE1`

Do not implement live shell execution until the dry-run proves argv classification,
cwd guard, redaction, output caps, and receipt generation.

## 11. WSP_97 truth table

| Claim | Label | Evidence |
| --- | --- | --- |
| Existing repo has many subprocess call sites | OBSERVED | `rg subprocess` direct search |
| Existing subprocess call sites are RedDog authority | FALSE | No signed authority/cwd/receipt binding |
| WRE cwd guard exists | OBSERVED | `reddog_wre_cwd_guard.py` |
| Generic writer dry-run exists | OBSERVED | `reddog_generic_agent_worktree_writer_dryrun.py` |
| Governed shell runner exists today | FALSE | No canonical module found |
| Future runner must be argv-only | SPECIFIED_NOT_IMPLEMENTED | This contract |
| Future runner must not re-index HoloIndex | SPECIFIED_NOT_IMPLEMENTED | This contract |

## Explicit non-goals

- No shell runner implementation.
- No subprocess invocation.
- No file mutation.
- No worktree creation.
- No PR/merge/release/deploy/publish.
- No reward settlement.
- No extension runtime wiring.
- No HoloIndex re-index.

## Truth Boundary Checklist

- DOCS_ONLY: YES
- NO_RUNTIME_CODE: YES
- NO_SUBPROCESS: YES
- NO_SHELL: YES
- NO_FILE_MUTATION: YES
- NO_MERGE_AUTHORITY: YES
- NO_REWARD_SETTLEMENT: YES
- NO_HOLOINDEX_REINDEX: YES
- WSP_97_LABELS_USED: YES
- SPECIFIED_NOT_IMPLEMENTED_EXPLICIT: YES
