# Codex Hooks

Repository-owned Codex lifecycle policy for FoundUps coding sessions.

## Purpose

This block connects Codex lifecycle events to deterministic FoundUps gates. It
does not provide remote transport, MCP services, model routing, WRE execution,
or transcript memory.

Phase 1 supplies four boundaries:

- `SessionStart`: execute the canonical WSP_00 awakening and strict tracker.
- `UserPromptSubmit`: reject provider credentials without echoing or storing them.
- `PreToolUse`: deny non-negotiable unsafe operations.
- `Stop`: require clean staged and unstaged `git diff --check` results.

## App discovery

The ChatGPT/Codex app discovers `.codex/hooks.json` when this repository is the
active trusted project. There is no separate Add Hook control. After this PR is
present locally, start a new repository session and review the hook definition
through `/hooks`. Changed definitions require renewed trust.

The adapter uses `commandWindows` to resolve the active Git root before invoking
this module, so linked worktrees execute their own checked-out implementation.

## Runtime contract

```text
Codex event JSON on stdin
    -> .codex/hooks.json
    -> python -m modules.infrastructure.codex_hooks.src.codex_hooks
    -> zero or one Codex hook response JSON on stdout
```

The implementation captures WSP subprocess output and emits concise state only.
It never reads `transcript_path` and never persists prompts or tool inputs.

## Validation

```powershell
python -m pytest modules/infrastructure/codex_hooks/tests -q
python -m pytest modules/infrastructure/codex_hooks/tests --cov=modules/infrastructure/codex_hooks/src --cov-report=term-missing
```

See [INTERFACE.md](INTERFACE.md) for event/output contracts.
