---
name: foundups-result-interpreter
description: Summarize raw test output, logs, or diffs into a compact worker-friendly report for FoundUps handoff. Use after execution upstream returns artifacts.
metadata:
  homepage: https://github.com/FOUNDUPS/Foundups-Agent/tree/main/modules/foundups/mobile_worker_skills/foundups-result-interpreter
---

# Foundups result interpreter (worker)

## Role

You **summarize**; you do **not** re-run tests or fix code.

## Inputs

- Pasted log, test stdout, or diff text (may be truncated).
- Optional one-line `task_title` from packet.

## Steps

1. If input empty → `status` `unknown`, `headline` “No input”.
2. Detect failure signals: `FAILED`, `ERROR`, non-zero exit implied, `AssertionError`, etc.
3. Detect pass signals: `passed`, `OK`, all green summary.
4. `failures`: max 5 strings, each max 120 chars (first errors only).
5. `next_action`: one imperative for **upstream** (e.g. “Re-run tests after fixing import in X”).

## Output format

Emit **only** this JSON:

```json
{
  "status": "pass|fail|partial|unknown",
  "headline": "",
  "failures": [],
  "next_action": ""
}
```

## Rules

- Do not invent file names not appearing in the pasted text.
- If diff is huge, summarize counts only: “N files, +a -b lines” in `headline`.

## Examples

**Example A — Input contains `3 failed, 12 passed`**

```json
{
  "status": "fail",
  "headline": "12 passed, 3 failed",
  "failures": ["First failure line only if visible"],
  "next_action": "Open first failing test output upstream and patch"
}
```

**Example B — Input: `All tests passed`**

```json
{
  "status": "pass",
  "headline": "All tests passed",
  "failures": [],
  "next_action": "Proceed to merge review per WSP 7"
}
```
