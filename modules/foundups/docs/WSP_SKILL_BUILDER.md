# WSP — FoundUps Mobile Worker Skill Builder

**Version:** 1.0.1  
**Date:** 2026-04-12  
**Status:** Canonical for `modules/foundups/mobile_worker_skills/`  
**ADR:** `docs/adr/ADR_FOUNDUPS_MOBILE_WORKER_SKILL_SYSTEM.md`  

---

## Purpose

Rules for **text-first** (and optionally JS) skills used by **phone worker** runtimes (e.g. AI Edge Gallery). These skills are **subordinate** to the higher agentic layer (0102); they do **not** hold repo authority.

---

## Architectural rules

1. **Worker layer only** — Skills emit **structured intent**, not merges or shell commands, unless a **documented bridge** exists.  
2. **No invented paths** — Never output absolute repo paths unless provided in the user packet as **verified allowlist**. Machine JSON should conform to [`mobile_worker_skills/schemas/worker-handoff-pipeline.v1.schema.json`](../mobile_worker_skills/schemas/worker-handoff-pipeline.v1.schema.json) (`$defs`).  
3. **Inspect-first** — If edit intent is unclear, default to **read-only** classification and **clarifying questions** in the output schema.  
4. **Compact** — Prefer short JSON or fixed headings; local models have finite context.  
5. **Edge Gallery shape** — Each skill lives in **kebab-case** folder matching `name`; root file **`SKILL.md`** with YAML frontmatter between `---` lines ([Gallery spec](https://github.com/google-ai-edge/gallery/tree/main/skills)).  
6. **WSP 83** — New skills must be listed in `mobile_worker_skills/README.md` and referenced from domain docs.  
7. **WSP 104** — Do not assume new **top-level** `public/` URLs; URL deployment is **Pages or approved static host** unless product assigns a `/f/{foundup_id}` static mirror.

---

## Frontmatter (required)

```yaml
---
name: kebab-skill-name    # max 64 chars; must match directory name; [a-z0-9-]
description: Trigger-ready one-liner, max ~1024 chars, when to use this skill
metadata:
  homepage: https://github.com/FOUNDUPS/Foundups-Agent/tree/main/modules/foundups/mobile_worker_skills/kebab-skill-name
---
```

Optional (Gallery): `metadata.require-secret` for JS skills—only if implemented.

---

## Skill body structure (recommended)

1. **Role** — Worker; no authority statement.  
2. **Inputs** — What the model receives.  
3. **Steps** — Numbered, mechanical.  
4. **Output format** — Exact headings or JSON keys.  
5. **Examples** — 1–2.  
6. **Stop conditions** — When to refuse or hand off.

---

## Naming

- Prefix: `foundups-` for repo workflow skills; `wsp00-` for WSP 00 **mobile semantic** subset only.  
- Kebab-case, no underscores in folder/`name`.

---

## Output formats (normative patterns)

### Task parser → JSON

```json
{
  "intent": "read|edit|mixed|unclear",
  "summary": "one line",
  "constraints": ["string"],
  "open_questions": ["string"],
  "suggested_next_skill": null
}
```

`"suggested_next_skill"` is JSON **`null`** or the string **`"foundups-scope-locker"`** (not the literal `"null"`).

### Scope locker → JSON

`allowed_operations`: array of strings; each item must be exactly one of: **`read_tree`**, **`draft_patch`**, **`tests_only`**, **`none`** (no pipe-separated strings in one element).

```json
{
  "scope_ok": true,
  "allowed_operations": ["draft_patch"],
  "explicit_non_goals": ["string", "string"],
  "handoff_required": true,
  "rationale": "one sentence"
}
```

### Task packet → JSON

```json
{
  "packet_version": "1",
  "title": "string",
  "objective": "string",
  "files_allowlist": [],
  "forbidden_paths": [],
  "acceptance_criteria": ["string"],
  "evidence_required": ["string"],
  "wsp_refs": ["WSP 22", "WSP 49"]
}
```

### Result interpreter → JSON

```json
{
  "status": "pass|fail|partial|unknown",
  "headline": "one line",
  "failures": ["string"],
  "next_action": "string"
}
```

### Handoff validator → JSON

```json
{
  "validator_version": "1",
  "valid": true,
  "errors": [],
  "warnings": []
}
```

---

## Promotion rules

| Stage | Location | Gate |
|-------|----------|------|
| Draft | `mobile_worker_skills/<name>/` | Self-review against this doc |
| Review | PR + 0102 | No orphan paths; no authority leaks |
| URL mirror | GitHub Pages or approved CDN | Version tag; optional hash in manifest |
| Cross-wardrobe | `moltbot_bridge/workspace/skills/` | **Explicit** ADR or merge policy only |

---

## WSP 95 note

WRE production skills often use **`SKILLz.md`**. **Edge Gallery** expects **`SKILL.md`**. This tree uses **`SKILL.md`** for Gallery compatibility. If promoting into WRE, add **`SKILLz.md`** copy or symlink policy in the promotion PR.

---

*0102: skills are worker weights; routing stays upstream.*
