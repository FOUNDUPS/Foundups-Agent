# Codex Hooks Interface

## Entrypoint

```powershell
python -m modules.infrastructure.codex_hooks.src.codex_hooks
```

Input is one Codex hook event JSON object on stdin. Successful allow/no-op paths
exit `0` without stdout. Policy responses exit `0` with exactly one compact JSON
object on stdout. Invalid wire input exits non-zero and writes only a structural
error to stderr.

## Events

### SessionStart

Accepted sources in `.codex/hooks.json`: `startup`, `resume`, `clear`.

The handler:

1. resolves Git root, branch, HEAD, and primary/linked worktree status;
2. executes `WSP_agentic/scripts/functional_0102_awakening_v2.py` from Git root;
3. removes `WSP_AWAKENING_WRITE_TRACKED` from the child environment;
4. executes the tracker with `--check --strict --json`;
5. returns bounded additional context on success or `continue=false` on failure.

### UserPromptSubmit

Scans `prompt` in memory for established provider-token and secret-assignment
shapes. A match returns `decision=block` with classification names only. The
matching value is never returned or persisted.

### PreToolUse

Configured aliases: `Bash`, `apply_patch`, `Edit`, `Write`.

Denied operations include:

- environment credential-file reads/edits;
- broad recursive deletion and destructive Git reset/clean forms;
- force pushes;
- raw HoloIndex search/reindex invocation;
- file edits and Git mutations on `main`, `master`, or detached HEAD.

Denials use the supported `hookSpecificOutput.permissionDecision=deny` shape.

### Stop

Runs `git diff --check` and `git diff --cached --check`. A failure returns
`decision=block` so Codex continues and corrects whitespace/error-marker issues.
`stop_hook_active=true` is a no-op to prevent continuation loops.

## Public Python API

```python
from modules.infrastructure.codex_hooks import dispatch_hook

response = dispatch_hook(event)
```

`dispatch_hook()` is deterministic except for read-only Git queries and the
explicit WSP_00 subprocesses used by `SessionStart`.
