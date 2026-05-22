# HoloIndex External FoundUp Surface

**Type**: INFRA (Infrastructure)
**Tier**: INFRA
**Lifecycle Stage**: incubating
**Launch Readiness**: discoverable_only

---

## Purpose

This module represents the **external/public FoundUp surface** of HoloIndex. It is NOT the internal HoloIndex infrastructure.

### Dual Identity Boundary

HoloIndex has a dual identity:

1. **Internal HoloIndex** (protected infrastructure):
   - Foundups retrieval/memory/work-ledger system
   - Used by 0102, WRE, MCP, OpenClaw, Hermes, workers
   - ChromaDB vector collections, semantic search, pattern memory
   - Location: `holo_index/` directory

2. **External HoloIndex FoundUp** (this module):
   - Public connective/trust surface
   - Explains what FoundUps exist and how they connect
   - Discovery surface in p.fMALL catalog
   - Does NOT provide direct access to internal HoloIndex

---

## What This Module Contains

| File | Purpose |
|------|---------|
| `foundup_manifest.json` | External FoundUp surface manifest (discovery only) |
| `README.md` | This documentation |

---

## What This Module Does NOT Contain

This module intentionally does NOT contain:

- HoloIndex core code (lives in `holo_index/`)
- ChromaDB collections or embeddings
- Semantic search implementation
- MCP server or tools
- Work ledger indexing logic
- Agent memory or pattern storage

---

## Catalog Binding

This FoundUp is registered in `public/member/mall-video-catalog.json` with:

```json
{
  "foundup_id": "holoindex_prod_01",
  "routing_prefix": "/f/holoindex_prod_01",
  "launch_readiness": "discoverable_only"
}
```

---

## Trust Surface Contract

The external HoloIndex FoundUp may eventually display:

- What FoundUps exist in the ecosystem
- Lifecycle stage of each FoundUp
- Which have public PoCs
- Which are gated prototypes
- Registry backing status
- Safety/trust evidence (without exploit payloads)

---

## WSP References

- WSP 97: Truth boundaries (dual identity enforcement)
- WSP 104: FoundUp route namespace (`/f/holoindex_prod_01`)
- WSP 3: Domain organization (INFRA type)
- WSP 49: Module structure

---

## Related Documentation

| Document | Path |
|----------|------|
| Dual Identity Contract | `docs/audits/architecture/HOLOINDEX_PUBLIC_FOUNDUP_CONNECTIVE_TRUST_SURFACE_DOCS_PHASE1.md` |
| External Bridge Contract | `holo_index/docs/EXTERNAL_FOUNDUP_BRIDGE_CONTRACT.md` |
| Current State Audit | `docs/audits/holoindex_external_foundup/CURRENT_STATE_AUDIT.md` |
| Internal HoloIndex Docs | `holo_index/README.md` |

---

## Important Boundary Rules

**NEVER** merge internal HoloIndex infrastructure into this module.
**NEVER** expose internal index paths or query mechanics publicly.
**NEVER** provide backend access through this external surface.
**ALWAYS** maintain the dual identity boundary.

---

**Type Classification**: This is an INFRA entity in the typed registry schema, not a full FoundUp. It does not require token assignment or CABR contract (beyond the default stub in manifest).
