# WSP 10: Repository State Save and Recovery Protocol
- **Status:** Active
- **Version:** 0.2.0
- **Purpose:** Preserve a verified, recoverable Git state before high-risk work while protecting unrelated worker lanes and user-owned changes.
- **Trigger:** Before cross-module refactors, consolidation, dependency or governance changes, destructive Git operations, or any slice whose failure could affect shared repository state.
- **Input:** Verified base commit, owned file scope, operation type, WSP 15 priority/risk assessment, and validation plan.
- **Output:** Isolated branch/worktree, reviewed checkpoint commit, validation evidence, and a focused pull request or explicitly local recovery point.
- **Responsible Agent(s):** The acting 0102 worker; verifier/reviewer for shared changes.

## 1. Truth Boundary

WSP 10 is a Git-native operating protocol. The repository does **not** currently contain a central `WSP10StateManager`, automatic rollback service, or distributed backup runtime. Agents MUST NOT claim those capabilities exist.

The currently supported state-save mechanism is:

1. verify the source commit and working-tree ownership;
2. isolate the slice in a dedicated branch and worktree;
3. review and explicitly stage only owned files;
4. create a tested checkpoint commit;
5. push a focused branch and use a pull request as the shared audit record when publication is authorized.

An annotated tag is optional. A tag points to an existing commit; it does not save uncommitted files.

## 2. Mandatory Triggers

A state-save boundary is required before:

- multi-module or architecture refactoring;
- module consolidation, movement, or deletion;
- significant dependency, schema, memory, or governance changes;
- work affecting three or more modules;
- changes to core orchestration or autonomous-runtime control paths;
- any reset, revert, history rewrite, or recovery action;
- work in a repository where another worker lane or unowned dirty state is present.

Use WSP 15 to score and order the slice. High priority does not relax the isolation, review, or validation gates.

## 3. Pre-Action Verification

Before editing, the worker MUST:

1. run HoloIndex and direct evidence checks required by WSP 00, WSP 50, WSP 84, and WSP 97;
2. inspect `git status --short --branch` and `git worktree list`;
3. identify the exact base commit, owned files, validation commands, and expected output;
4. treat all pre-existing changes as user-owned unless ownership is explicitly established;
5. create a dedicated worktree from the verified base when another lane is active or the current tree is dirty.

Example isolation flow:

```bash
git fetch origin --prune
git rev-parse origin/main
git status --short --branch
git worktree list
git worktree add -b <focused-branch> <new-worktree-path> origin/main
```

The target worktree path and branch MUST be new or positively identified as owned by the acting worker. Never delete, move, reset, or reuse another lane to obtain a clean state.

## 4. Checkpoint Procedure

After the focused change is complete:

```bash
git status --short --branch
git diff --check
git diff --name-only
git add -- <explicit-owned-files>
git diff --cached --check
git diff --cached
git commit -m "<type>(<scope>): <focused outcome>"
git rev-parse HEAD
```

The worker MUST NOT use blanket staging when unrelated files may exist. The checkpoint commit is valid only after the staged diff is reviewed and proportionate tests or documentation validators pass.

If a local annotated tag materially improves recovery, it MAY be created after the commit:

```bash
git tag -a "wsp10/<slice>/<timestamp>" <checkpoint-commit> -m "WSP 10 recovery point: <slice>"
```

Do not publish the tag unless tag publication is authorized and useful. Normal focused work SHOULD use the branch, commit, and pull request as its recovery and audit chain.

## 5. Shared Registration and Merge

When publication is authorized:

1. push only the focused branch;
2. open a pull request that records scope, WSP 15 priority, WSP 97 truth boundary, tests, and rollback method;
3. wait for required checks and review;
4. merge only after gates pass and merge authority is present;
5. verify the merged commit on `origin/main` before starting a dependent slice.

The pull request is the canonical shared register of the change. A local commit without a pushed branch is only a local recovery point.

## 6. Recovery Procedure

Recovery MUST preserve evidence and unowned work.

- For a shared bad commit, prefer a reviewed `git revert` on a new focused branch.
- To inspect an older checkpoint, create a new branch/worktree at that commit.
- Never use `git reset --hard`, destructive checkout, or recursive deletion against a tree containing user or worker changes unless 012 explicitly authorizes that exact operation.
- Never automatically roll back on an exception; first capture status, logs, the failing command, and the checkpoint commit.

Non-destructive inspection example:

```bash
git worktree add -b recovery/<slice> <new-recovery-path> <checkpoint-commit>
```

After recovery, rerun the original validation plan and record the result in the relevant ModLog or pull request.

## 7. WSP Integration

- **WSP 2:** clean-state and repository-state discipline.
- **WSP 15:** priority and risk scoring before execution.
- **WSP 22:** concise operational history in the appropriate root or module ModLog.
- **WSP 34:** safe Git operations and branch/commit/PR workflow.
- **WSP 50 / WSP 84:** pre-action verification and reuse of repository evidence.
- **WSP 64:** violation prevention; no destructive handling of unowned state.
- **WSP 77:** worker-lane ownership and coordination.
- **WSP 81:** governed framework/knowledge backup synchronization.
- **WSP 97:** evidence-first execution and explicit current/future capability boundaries.

## 8. Compliance Receipt

For a high-risk slice, retain at least:

- base and checkpoint commit hashes;
- branch and worktree identity;
- explicit owned-file list;
- validation commands and outcomes;
- pull request and merge reference when shared;
- recovery or revert reference if invoked.

Missing evidence means the state save is not verified.
