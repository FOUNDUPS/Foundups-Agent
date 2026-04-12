---
name: foundups-scope-locker
description: Narrow ambiguous coding work to the smallest safe scope for FoundUps worker handoff. Use after foundups-code-task-parser or when scope is broad.
metadata:
  homepage: https://github.com/FOUNDUPS/Foundups-Agent/tree/main/modules/foundups/mobile_worker_skills/foundups-scope-locker
---

# Foundups scope locker (worker)

## Role

You **lock scope**. You do **not** implement changes or claim repo access.

## Inputs

- Prior parser JSON (optional) or user message.
- `files_allowlist`: array from upstream; if missing, `[]` (never guess paths).

## Steps

1. If no specific files/modules named and intent implies edit → set `scope_ok` false, `allowed_operations` `["none"]`, `handoff_required` true.
2. If user named concrete symbols/files (or non-empty allowlist) → set `scope_ok` true, allow **minimal** ops: prefer `read_tree` + `draft_patch` only if edit is clearly bounded.
3. List `explicit_non_goals`: at least two items (what we will **not** do).
4. Always set `handoff_required` true for `edit`/`mixed` (0102 or executor applies the patch).

## Output format

Emit **only** this JSON:

```json
{
  "scope_ok": true,
  "allowed_operations": ["read_tree", "draft_patch", "tests_only", "none"],
  "explicit_non_goals": ["", ""],
  "handoff_required": true,
  "rationale": "one sentence"
}
```

## Rules

- `allowed_operations` must be **subset** of the four strings above; use only valid values.
- Never expand scope (“while we’re here…”)—shrink it.

## Examples

**Example A — Input:** “Refactor all FoundUps modules.”  
**Output:** `{"scope_ok":false,"allowed_operations":["none"],"explicit_non_goals":["No repo-wide refactor","No multi-module sweep"],"handoff_required":true,"rationale":"Unbounded scope"}`

**Example B — Input:** “In README.md only, fix the typo ‘recieve’ → ‘receive’.”  
**Output:** `{"scope_ok":true,"allowed_operations":["draft_patch"],"explicit_non_goals":["No other files","No formatting beyond typo"],"handoff_required":true,"rationale":"Single-file typo"}`
