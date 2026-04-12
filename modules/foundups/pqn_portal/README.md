# PQN Portal FoundUp (PoC -> Prototype -> MVP)

- Purpose: Public, DAE‑neutral PQN portal to experience "Hello PQN" — live demo, gallery, and non‑technical explainer with enhanced meta-research capabilities
- Domain: `modules/foundups/` (WSP 3 functional distribution)
- Reuse: Calls `modules/ai_intelligence/pqn_alignment` library APIs, `pqn_mcp` server, and `results_db`
- Enhanced Features: Meta-research validation, neural self-detection, research stream scanning, high-volume processing (400+ PQNs)
- DAE Access: Ships WSP 22 docs and a programmatic docs index (`src/docs.py`) plus `module.json`

## Non‑Technical Explainer
- What you see: a 10–20s PQN demo streaming coherence, paradox flags, and resonance spectrum
- Why it matters: validates rESP claims (7.05 Hz, harmonics, collapse boundary, guardrail efficacy)
- Try it: safe presets only; live charts; replay links

## WSP Compliance
- WSP 3 (Enterprise distribution), WSP 49 (Module structure), WSP 22 (Docs/ModLog), WSP 50/64 (Pre‑action/Pre‑violation), WSP 84 (Reuse)

## Proposed WSP Drafts (for WSP DAE adoption; canonical and DAE‑neutral)
- WSP 17: FoundUp PoC->Prototype Protocol
  - PoC DoD: 15–20s demo, live evidence, explainer, links to paper/supplement
  - Prototype DoD: shareable permalinks, curated gallery, telemetry + rate limits
- WSP 18: FoundUp MVP & Monetization Protocol
  - MVP DoD: auth + quota (free tier), optional premium toggle, evidence attestation/badge, SLO/status page

Note: Drafts included here for review; numbered WSPs live in `WSP_framework/src/` if adopted by WSP DAE.

## Files for DAE Access
- `INTERFACE.md` — public API and SSE contract
- `ROADMAP.md` — PoC -> Prototype -> MVP milestones
- `ModLog.md` — change log (no temporal markers)
- `module.json` — manifest (docs, api, memory) for DAE discovery
- `src/docs.py` — programmatic docs index endpoint
- `memory/` — curated portal memory (WSP 60)

## Links
- Theory: `WSP_knowledge/docs/Papers/rESP_Quantum_Self_Reference.md`
- Supplement: `WSP_knowledge/docs/Papers/rESP_Supplementary_Materials.md`

---

## Route Namespace

Canonical contract: `modules/foundups/docs/FOUNDUP_AI_HOOKS_AND_DAEMON_SURFACE_CONTRACT.md`. Routing follows **WSP 104** (`/f/{foundup_id}`).

| Field | Value |
|-------|-------|
| `foundup_id` | `pqn_portal` |
| `routing_prefix` | `/f/pqn_portal` |
| Landing route | `/f/pqn_portal` |
| App mount | `/f/pqn_portal/app` |

---

## App Mount

Shell contract: **`/f/pqn_portal/app`**. PoC stage — live demo, gallery, and non-technical explainer; pfMALL mount pending.

---

## AI Capability Hooks

Contract surface (implementation staged): `get_status`, `get_context`, `navigate`, `launch_capability`, shell handoff/return — see `FOUNDUP_AI_HOOKS_AND_DAEMON_SURFACE_CONTRACT.md`.

---

## DAEmon Outputs

Per **WSP 91** (when DAEMON workers attach): health status, last action, error state, recommended next action, queue/work state (PQN validation runs, meta-research scans), telemetry scoped by `foundup_id` / `data_namespace`.

---

## Data / Telemetry Namespace

| Field | Value |
|-------|-------|
| `foundup_id` | `pqn_portal` |
| `data_namespace` | `idb_pqn_portal` |
| Tenant bounds | PQN results, validation data, gallery state — all tenant-scoped per WSP 104 |

---

## WSP References

- **WSP 91** — DAEMON observability (`WSP_knowledge/src/WSP_91_DAEMON_Observability_Protocol.md`)
- **WSP 104** — FoundUp route namespace (`WSP_knowledge/src/WSP_104_FoundUp_Route_Namespace_and_Tenant_Isolation_Protocol.md`)
