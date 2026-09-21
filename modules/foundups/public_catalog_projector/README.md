# Public FoundUp Catalog Projector

Derives a **scope-free public catalog** (`public/f/public_catalog.json`) from the
canonical registry (`modules/foundups/foundup_registry.json`) and validates,
FAIL-CLOSED, that it contains **only** public-allowlisted fields.

## Why this exists

The public `/f/` shell reads this scope-free projection from the canonical
registry. The member runtime catalog remains behind the member surface.
The original Phase 1 work separated those sources; current shell wiring already
uses the projection and sanitizes entries before rendering.

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
- **D. Optional discovery alias**: `public_discovery_alias` must be one explicit
  nonempty lowercase ASCII slug (`a-z`, digits, underscore). Global reservation
  checks include hidden/ineligible canonical IDs and aliases before filtering.
  Invalid input or collisions raise `SourceError`. Only portfolio-eligible
  entries explicitly marked discoverable/listed/promoted emit an alias.
  Missing/hidden visibility omits the alias without changing legacy canonical
  projection eligibility. Validation checks optional field presence and value.

The shell accepts aliases only on landing roots (one optional trailing slash),
replaces the URL with `/f/{foundup_id}` and uses that canonical identity before
rendering or concierge context. App/deep-app paths still hand off to `/member/`
before catalog retrieval. This capability does not register, list or activate
any FoundUp; the committed registry and catalog remain unchanged.
While discovery is pending or rejected, the public context exposes a null ID
instead of the unvalidated request token, for both aliases and canonical URLs.

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

## Validation

Reuse `tests/test_projector.py` for synthetic projection/schema controls and
`public/member/tests/test_route_contract_bridge.py` for the actual inline shell
under a mocked browser. Node is required for those route behavior tests; they
do not establish live browser authentication, deployment or runtime readiness.
Schema controls use the existing `jsonschema` dependency declared in
`modules/foundups/requirements.txt`.
