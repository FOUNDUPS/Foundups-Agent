---
name: foundups-task-packet-writer
description: Convert a scoped coding task into a strict machine-readable task packet for upstream FoundUps execution. Use after scope is locked.
metadata:
  homepage: https://github.com/FOUNDUPS/Foundups-Agent/tree/main/modules/foundups/mobile_worker_skills/foundups-task-packet-writer
---

# Foundups task packet writer (worker)

## Role

You emit a **versioned packet** for **0102 / executor**. You do **not** execute.

## Inputs

- Locked scope JSON from `foundups-scope-locker` (optional).
- User objective text.
- `files_allowlist`: only paths **explicitly** provided upstream; else `[]`.

## Steps

1. Set `packet_version` to `"1"`.
2. `title`: max 80 chars.
3. `objective`: single paragraph, no path invention.
4. `files_allowlist`: copy from input only.
5. `forbidden_paths`: include `["*"]` if allowlist empty and edit implied—forces upstream to supply paths.
6. `acceptance_criteria`: 2–5 testable bullets.
7. `evidence_required`: e.g. `["pytest path", "diff summary"]` as appropriate; use generic strings if unknown.
8. `wsp_refs`: suggest from set `WSP 22`, `WSP 49`, `WSP 50`, `WSP 64`, `WSP 97`—only if relevant; else `[]`.

## Output format

Emit **only** this JSON:

```json
{
  "packet_version": "1",
  "title": "",
  "objective": "",
  "files_allowlist": [],
  "forbidden_paths": [],
  "acceptance_criteria": [],
  "evidence_required": [],
  "wsp_refs": []
}
```

## Rules

- If `files_allowlist` is empty and task requires edit, `forbidden_paths` must include `"*"` and `acceptance_criteria` must include “Upstream supplies verified file paths”.

## Examples

**Example A — allowlist `["modules/foo/README.md"]`**

```json
{
  "packet_version": "1",
  "title": "Fix README typo",
  "objective": "Correct spelling only in modules/foo/README.md",
  "files_allowlist": ["modules/foo/README.md"],
  "forbidden_paths": ["modules/foo/src"],
  "acceptance_criteria": ["Only README.md changed", "Typo fixed", "No other wording changes"],
  "evidence_required": ["diff"],
  "wsp_refs": ["WSP 22"]
}
```
