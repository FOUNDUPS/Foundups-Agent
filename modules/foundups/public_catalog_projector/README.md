# Public FoundUp Catalog Projector (Phase 1)

Derives a **scope-free public catalog** (`public/f/public_catalog.json`) from the
canonical registry (`modules/foundups/foundup_registry.json`) and validates,
FAIL-CLOSED, that it contains **only** public-allowlisted fields.

## Why this exists

The public `/f/` surface today reads the **member runtime catalog**
(`public/member/mall-video-catalog.json`) whole, client-side, with no field
filtering. Any member-scoped field later added to that runtime catalog would
leak publicly. This module projects a separate, scope-free public catalog from
the registry (the single source of truth) so a later slice
(`PUBLIC_MALL_READ_ONLY_BROWSE`) can wire the public page to read the
**projection** instead of the runtime catalog.

This mirrors the existing `portfolio_validator` + `public/f/portfolio_data.json`
derived-projection pattern. Context:
`docs/audits/architecture/PLAYFOUNDUPS_MALL_PUBLIC_DISCOVERY_AUDIT_PHASE1.md`
(smallest-step #1).

## Safety properties (validator, fail-closed)

- **A. Allowlist-only (leak guard)**: every field in every projection entry must
  be on `PUBLIC_ALLOWLIST`. Any non-allowlisted field - especially a known
  member-scoped key from the runtime catalog (`videos`, `subscriber_count`,
  `creator_id`, `entry_url`, ...) - REJECTS the projection.
- **B. Derived-from-registry**: every projection entry corresponds to a registry
  entry; no invented entries; field values match the registry projection (drift
  check); not-portfolio entities never appear.
- **C. No runtime-catalog dependency**: the projection path never reads
  `public/member/mall-video-catalog.json`. The member catalog's keys are used
  only as the named forbidden set.

## CLI

```bash
# Derive + validate + write the artifact (refuses to write if unsafe)
python -m modules.foundups.public_catalog_projector --generate

# Validate the already-committed artifact against the registry
python -m modules.foundups.public_catalog_projector --validate

# Derive in-memory + validate, no write (default)
python -m modules.foundups.public_catalog_projector --check

# JSON report
python -m modules.foundups.public_catalog_projector --check --json
```

Exit codes: `0` safe, `1` fail-closed violation, `2` source missing/malformed.

## Scope (Phase 1)

- Builds the projector + validator + the derived artifact + tests ONLY.
- Does NOT touch the frontend; does NOT un-gate anything; does NOT change auth.
- Wiring the public page to read the projection is a separate later slice.
