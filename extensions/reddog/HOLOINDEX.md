# HoloIndex - reddog

Local retrieval manifest for the RedDog extension thin-client lane.

## Source Files (Tier 0 recall targets)

- `extension.js` - main extension entry; Copy MD, Run Trace, Work Trail, redaction handoff
- `holoindex_generation_bound_query.js` - owner-receipt acceptance, semantic-bucket replacement, and generation metadata
- `package.json` - Node manifest and version

## Bridge (cross-path recall)

- `scripts/advisory_model_once.py` - OpenRouter bridge and redaction gate (repo root)
- `scripts/reddog_holoindex_owner_query_once.py` - authenticated generation-bound owner query bridge (repo root)

## Documentation

- `ARCHITECTURE.md` - canonical RedDog/0102 identity boundary: 012 <-> RedDog surface/proxy <-> 0102 digital twin/orchestrator; attention firewall and recursive co-development invariants
- `README.md`, `INTERFACE.md`, `ModLog.md`, `ROADMAP.md`
- `docs/REDDOG_EXTERNAL_ACCEPTANCE_BASELINE_PHASE1.md` - acceptance baseline pack
- `docs/acceptance/` - baseline artifact storage

## Symbols (high-value recall)

- `buildCopyMarkdown`, `buildRunTraceSection`, `holoIndexMetaFromBundle`, `evaluateTargetRecall`
- `isGenerationBoundHoloQueryAccepted`, `mergeGenerationBoundHoloResult`, `buildMetaFromBundle`
