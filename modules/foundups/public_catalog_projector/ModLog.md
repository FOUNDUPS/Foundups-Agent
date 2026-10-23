## 2026-10-18: Register the Move2Japan housing POC inside the existing Mall

- Authority: 012's instruction to recover under WSP 00/97 and make Move2Japan a
  product inside Play Foundups. Bounded worker handoff retained the same tenant.
- Reconciled only the existing `move2japan` registry record: discoverable,
  incubating public POC, canonical `/f/move2japan`, protected app still pending,
  `TOKEN_DEFERRED` and null token. Added its declarative manifest with isolated
  namespace and all execution-readiness flags false.
- Reused the current projector and its `poc_url` allowlist field unchanged.
  Generated the public catalog through the existing CLI: five eligible records
  from eighteen registry records, zero violations. The member video catalog and
  legacy `portfolio_data.json` were not regenerated or hand-authored.
- Canonical landing and portfolio now offer the exact registered same-tab
  **Browse houses** selection at `/member/?foundup=move2japan`. The protected
  app gate remains before catalog loading. Repaired the existing portfolio
  filter initialization after its early return and removed invented token labels.
- Extended the existing projector and route-test owners: fresh 284 passed,
  no skips. Namespace/catalog/export cross-check: 56 passed and seven failures
  confined to unchanged EDuit, Shield and HoloIndex inputs; exact IDs and evidence
  are in `tests/TestModLog.md`. No unrelated fix, xfail or gate change was made.
- Recovery provenance: twelve domain documents were restored from retained full
  reads plus exact saved patch arguments. Registry/route implementation was
  reconstructed against the recovered current owners and freshly tested; it is
  not represented as byte-exact recovery of lost source. Production deployment
  and domain cutover remain separate from the private review mirror.
- Retrieval evaluation: the bounded lexical Holo owner query returned required
  README/INTERFACE artifacts from source-bound workspace overlay
  `db1442ae5d5c8856a9a15ef8cdd96362c824c03e`, with UNKNOWN freshness/index gap.
  Direct current WSP 104, manifest, projector and route reads established the
  contract. No semantic CURRENT claim, reindex or authority mutation was made.
  WSP 00's documented torch-free fallback opened the gate with detector witness
  absent; this is operational readiness evidence only.

## 2026-09-21: Implement optional canonical discovery aliases

- WSP00/15/22/50/62/97/99/104; C4/I2/D2/Impact2=10/P2. PR1840 and both main workflows passed; fresh98peer heads and16 source bindings reconciled.
- Reuse existing schema, projector and public shell. Validate global slug reservations before filtering; project only eligible explicitly visible aliases; canonicalize URL and identity before render/context. Preserve member app gating before catalog retrieval.
- Extend existing tests with synthetic schema/projector cases and actual inline JavaScript under a mocked browser. Independent source review caught and corrected missing shell portfolio eligibility before final review. Local271 and independent271overlapping cases pass; speculative context IDs also remain null until resolution. Exact candidate CI remains pending in the canonical backlog; no production data/manifest, runtime/provider or deployment changes.
- Retain all26 original packets and51 score histories. Retrieval first returned the shared-root overlay and was rejected; corrected owned adapter binds f83edabc3 with UNKNOWN freshness/index gap, no semantic CURRENT claim or reindex. Missing canonical projector TestModLog added under WSP97, existing member TestModLog reused.

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
