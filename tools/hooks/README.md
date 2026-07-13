# Tools Hooks

Repo-local hook helpers for preventing operational mistakes in 0102/WRE work.

## Worktree CWD Guard

`pre_commit_worktree_cwd_guard.py` blocks direct commits from the shared
`O:/Foundups-Agent` `main` checkout. Worker commits must happen from an isolated
worktree. Intentional shared-main commits require an explicit override:

```powershell
$env:FOUNDUPS_ALLOW_SHARED_MAIN_COMMIT = "1"
git commit ...
```

The hook is a last-resort protection. Governed WRE work still uses
`validate_wre_worker_operation_cwd(...)` before worktree, shell, and writer
operations. Raw `git add` cannot be intercepted by Git hooks, so workers must
still run from the intended worktree and stage explicit paths only.

