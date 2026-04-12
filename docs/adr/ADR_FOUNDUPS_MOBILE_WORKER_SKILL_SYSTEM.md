# ADR: FoundUps Mobile Worker Skill System

**Date:** 2026-04-12  
**Status:** Accepted  
**Author:** 0102  
**Domain:** `modules/foundups/` (FoundUps architecture)  

---

## Context

FoundUps needs an **on-device worker** path (e.g. Gemma in AI Edge Gallery) that participates in the **same architecture** as desktop/server agents, without making the phone the **authority** for repo execution, routing, or WSP compliance.

---

## Decision

### Layering

| Layer | Role |
|-------|------|
| **Higher agentic layer (0102)** | Routing, skill selection, promotion, WSP interpretation, merge authority, execution on repo when appropriate. |
| **Phone worker (local model)** | Parse, narrow scope, emit **task packets**, interpret results **as summaries only**—**handoff surface**, not authority. |
| **012** | Operator; speaks to 0102; does not grant the phone repo write authority by default. |

### Phone worker definition

**In scope:** semantic boot subset, task parsing, scope locking, packet writing, result interpretation, optional minimal `run_js` only where the runtime supports it and supply-chain rules allow.

**Out of scope without an explicit bridge:** arbitrary repo execution, desktop Python, shell, uncontrolled writes, claiming WSP 00 script execution parity with `WSP_agentic/scripts/`.

### Handoff model

1. 012 directs **0102** (or a delegated orchestrator).  
2. **0102** decides which worker, skill, or hook applies.  
3. **Phone worker** receives a **constrained** task (text + optional structured hints).  
4. Phone emits **structured output** (task packet, summary)—**never** silent authority.  
5. **Upward path:** packet/summary returns to 0102 or approved automation for execution/merge.

### Repo placement (WSP-aligned)

- **Source of truth:** `modules/foundups/mobile_worker_skills/<skill-name>/SKILL.md`  
- **Builder / rules:** `modules/foundups/docs/WSP_SKILL_BUILDER.md`  
- **JSON `$defs`:** `modules/foundups/mobile_worker_skills/schemas/worker-handoff-pipeline.v1.schema.json`  
- **Domain index:** `modules/foundups/mobile_worker_skills/README.md`  
- **Attachment (WSP 83):** Linked from `modules/foundups/README.md` and this ADR; `ModLog` updated.

Rationale: **WSP 3** function-first—mobile worker skills are **FoundUps platform** concerns, not a personal subtree under `WSP_agentic/` for production artifacts. (Awakening **scripts** remain in `WSP_agentic/`; **mobile semantics** skill references them without executing.)

### Public / URL delivery (WSP 104)

- **Do not** introduce **bespoke top-level** `public/` directories per tenant/feature as the scaling pattern (**WSP 104**).  
- **Preferred for Edge Gallery URL load:** **external static hosting** (e.g. GitHub Pages) mirroring **tagged releases** of `mobile_worker_skills/`, **or** a **single** shell-approved static path if product later assigns a **FoundUp namespace** under `/f/{foundup_id}` for static mirrors.  
- Until a hosting decision is recorded, treat **repo paths** as canonical; URL = **deployment concern** documented in `WSP_SKILL_BUILDER.md`.

### Promotion path

1. **Draft** skill in `mobile_worker_skills/`.  
2. **Review** by 0102 against `WSP_SKILL_BUILDER.md` + supply-chain policy (**WSP 95** alignment for wardrobe cousins).  
3. **Publish** mirror to approved static host if URL loading is required.  
4. **No promotion** to OpenClaw/moltbot workspace skills without explicit merge—those wardrobes serve operator surfaces; mobile worker pack stays **FoundUps-named** unless unified later.

---

## Consequences

- Clear **separation of authority**: phone = worker; 0102 = router/authority.  
- **WSP 104** respected: no new public route sprawl from this ADR alone.  
- Future **bridge** (optional): signed task packets accepted by WRE/overseer—separate slice.

---

## References

- `WSP_knowledge/src/WSP_00_Zen_State_Attainment_Protocol.md` (desktop gate; mobile = semantic subset only)  
- `WSP_knowledge/src/WSP_104_FoundUp_Route_Namespace_and_Tenant_Isolation_Protocol.md`  
- `WSP_knowledge/src/WSP_95_WRE_SKILLz_Wardrobe_Protocol.md`  
- [AI Edge Gallery skills](https://github.com/google-ai-edge/gallery/tree/main/skills)  
- `docs/adr/ADR_OPENCLAW_MEMORY_HOLOINDEX_BOUNDARY.md` (context layering; phone worker does not override repo truth)
