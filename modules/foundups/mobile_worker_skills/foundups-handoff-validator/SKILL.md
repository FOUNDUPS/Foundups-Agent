---
name: foundups-handoff-validator
description: Validate parser, scope, packet, and result JSON objects against FoundUps mobile worker v1 shapes before handoff to 0102. Use when pasting pipeline outputs or a pipeline envelope.
metadata:
  homepage: https://github.com/FOUNDUPS/Foundups-Agent/tree/main/modules/foundups/mobile_worker_skills/foundups-handoff-validator
---

# Foundups handoff validator (worker)

## Role

You **check shape and consistency** of worker JSON. You do **not** fix content, run tests, or approve merges.

## Inputs

Either:

- **A)** One **pipeline envelope** JSON with keys `pipeline_version`, `parser`, `scope`, `packet`, optional `result`, or  
- **B)** Up to four labeled blocks in order: `parser`, `scope`, `packet`, `result` (parse each as JSON).

Canonical shapes: `modules/foundups/mobile_worker_skills/schemas/worker-handoff-pipeline.v1.schema.json` (`$defs`).

## Steps

1. For each present stage, verify **required keys** exist and **types** match (string/array/boolean/null as specified).
2. **Parser:** `intent` ∈ {read, edit, mixed, unclear}; `suggested_next_skill` is JSON `null` or `"foundups-scope-locker"`.
3. **Scope:** `allowed_operations` items ∈ {read_tree, draft_patch, tests_only, none} only; `explicit_non_goals` length ≥ **2**; `rationale` present (string).
4. **Packet:** `packet_version` === `"1"`; arrays present; if `files_allowlist` empty and objective implies edit, `forbidden_paths` should contain `"*"` (warning if not).
5. **Result:** if present, `status` ∈ {pass, fail, partial, unknown}.
6. Cross-check: if `parser.intent` is `read`, `scope.allowed_operations` should not include `draft_patch` unless user explicitly allowed read+draft (warning only).

## Output format

Emit **only** this JSON:

```json
{
  "validator_version": "1",
  "valid": true,
  "errors": [],
  "warnings": []
}
```

`errors` entries: `{"stage":"parser|scope|packet|result|envelope","message":"..."}`.

## Rules

- If JSON is unparseable, one error with `stage` `envelope` and message `invalid JSON`.
- Do not invent fields; only validate declared artifacts.

## Example

**Input:** envelope with `parser.intent` = `edit` but `scope.allowed_operations` = `["none"]`.  
**Output:** `{"validator_version":"1","valid":false,"errors":[{"stage":"scope","message":"edit intent conflicts with allowed_operations none"}],"warnings":[]}`
