# ModLog - Public FoundUp Catalog Projector

## Phase 1 - Scope-free public catalog projector + validator + artifact

**Slice**: `PUBLIC_FOUNDUP_DISCOVERY_PROJECTED_CATALOG_PHASE1`
**WSP refs**: WSP_00, WSP_50/WSP_87 (HoloIndex-first), WSP_84 (reuse), WSP_97
(Truth Boundary), WSP_22 (ModLog), WSP_49 (module structure), WSP_11 (interface).

### What changed
- New module `modules/foundups/public_catalog_projector/`:
  - `src/projector.py` - generator (`generate_projection`) + fail-closed
    validator (`validate_projection`: rule A allowlist-only leak guard, rule B
    derived-from-registry drift + filter completeness) + artifact emit
    (`write_projection`).
  - `__main__.py` - CLI (`--generate` / `--validate` / `--check` / `--json`),
    exit 0/1/2; `--generate` refuses to write an unsafe projection.
  - `tests/test_projector.py` - proves the safety properties (member-field
    rejection per known key, invented-entry rejection, value-drift rejection,
    not-portfolio filter, round-trip on the committed artifact, projection-path
    independence from the runtime catalog).
  - `README.md`, `INTERFACE.md`, `requirements.txt`.
- New derived artifact `public/f/public_catalog.json` (3 portfolio-eligible
  entries, allowlist-only, holoindex flagged `is_dual_identity`).

### Why
PlayFoundups Mall public-discovery audit smallest-step #1: the public `/f/`
surface reads the MEMBER RUNTIME catalog whole with no field filtering, so any
future member-scoped field would leak. This projects a scope-free public catalog
from the registry (single source of truth), validated allowlist-only, so a later
slice can wire the public page to read the projection. Mirrors the existing
`portfolio_validator` + `public/f/portfolio_data.json` pattern.

### Scope guards (held)
- NO frontend change (public/f/index.html, public/member/**, *.js untouched).
- NO un-gating, NO auth/firestore change.
- Projection path NEVER reads `public/member/mall-video-catalog.json` (its keys
  seed the forbidden set only).
- ASCII-clean new files.
