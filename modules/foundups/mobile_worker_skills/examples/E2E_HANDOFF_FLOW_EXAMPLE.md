# End-to-end example: mobile worker handoff pipeline (v1)

**Purpose:** One fictional flow showing **user request → parser → scope → packet → (upstream execution) → result**.  
**Authority:** 0102 executes the packet on desktop; phone worker only produces structured JSON.

---

## 1. User request (012 → phone worker)

> In `modules/foundups/docs/WSP_SKILL_BUILDER.md` only, bump version line from 1.0.0 to 1.0.1 and add a bullet under Architectural rules: “Skills must list schema link when emitting JSON.”

*(Assume upstream supplied `files_allowlist`: `["modules/foundups/docs/WSP_SKILL_BUILDER.md"]`.)*

---

## 2. `foundups-code-task-parser` output

```json
{
  "intent": "edit",
  "summary": "Bump WSP_SKILL_BUILDER version to 1.0.1 and add schema bullet",
  "constraints": ["single file", "docs only"],
  "open_questions": [],
  "suggested_next_skill": "foundups-scope-locker"
}
```

---

## 3. `foundups-scope-locker` output

```json
{
  "scope_ok": true,
  "allowed_operations": ["draft_patch"],
  "explicit_non_goals": [
    "Do not edit mobile_worker_skills SKILL.md files in this task",
    "Do not change ADR or ModLog in this task"
  ],
  "handoff_required": true,
  "rationale": "Single named file in allowlist; bounded doc edit"
}
```

---

## 4. `foundups-task-packet-writer` output

```json
{
  "packet_version": "1",
  "title": "WSP_SKILL_BUILDER version + schema rule",
  "objective": "Update version metadata and add one architectural rule bullet referencing schemas/worker-handoff-pipeline.v1.schema.json",
  "files_allowlist": ["modules/foundups/docs/WSP_SKILL_BUILDER.md"],
  "forbidden_paths": ["modules/foundups/mobile_worker_skills"],
  "acceptance_criteria": [
    "Version string shows 1.0.1",
    "New bullet references schema path",
    "No other files modified"
  ],
  "evidence_required": ["diff", "optional: jsonschema spot-check"],
  "wsp_refs": ["WSP 22", "WSP 83"]
}
```

---

## 5. Upstream execution (0102 — not on phone)

0102 applies the patch, runs checks, then returns **raw test/log snippet** to the worker for summarization (fictional):

```text
pytest modules/foundups/tests/test_foundup_ai_hooks_daemon_contract_compliance.py -q
.....                                                                    [100%]
5 passed in 0.15s
```

---

## 6. `foundups-result-interpreter` output

```json
{
  "status": "pass",
  "headline": "5 passed in 0.15s",
  "failures": [],
  "next_action": "0102: proceed to commit or merge per WSP 7"
}
```

---

## 7. Optional `foundups-handoff-validator` input (full envelope)

```json
{
  "pipeline_version": "1",
  "parser": {
    "intent": "edit",
    "summary": "Bump WSP_SKILL_BUILDER version to 1.0.1 and add schema bullet",
    "constraints": ["single file", "docs only"],
    "open_questions": [],
    "suggested_next_skill": "foundups-scope-locker"
  },
  "scope": {
    "scope_ok": true,
    "allowed_operations": ["draft_patch"],
    "explicit_non_goals": [
      "Do not edit mobile_worker_skills SKILL.md files in this task",
      "Do not change ADR or ModLog in this task"
    ],
    "handoff_required": true,
    "rationale": "Single named file in allowlist; bounded doc edit"
  },
  "packet": {
    "packet_version": "1",
    "title": "WSP_SKILL_BUILDER version + schema rule",
    "objective": "Update version metadata and add one architectural rule bullet referencing schemas/worker-handoff-pipeline.v1.schema.json",
    "files_allowlist": ["modules/foundups/docs/WSP_SKILL_BUILDER.md"],
    "forbidden_paths": ["modules/foundups/mobile_worker_skills"],
    "acceptance_criteria": [
      "Version string shows 1.0.1",
      "New bullet references schema path",
      "No other files modified"
    ],
    "evidence_required": ["diff", "optional: jsonschema spot-check"],
    "wsp_refs": ["WSP 22", "WSP 83"]
  },
  "result": {
    "status": "pass",
    "headline": "5 passed in 0.15s",
    "failures": [],
    "next_action": "0102: proceed to commit or merge per WSP 7"
  }
}
```

Expected **validator**: `valid: true`, empty `errors` (for this synthetic example).
