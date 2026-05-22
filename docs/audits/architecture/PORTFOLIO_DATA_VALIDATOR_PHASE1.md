# Portfolio Data Validator Phase 1 - Audit

**Slice**: `PORTFOLIO_DATA_VALIDATOR_PHASE1`
**Worker**: W6
**Date**: 2026-05-22
**Mode**: Read-only validator (observation only - NOT a CI gate this phase)
**Base commit**: `af7c46be`
**Branch**: `feat/portfolio-data-validator-phase1`
**WSP Lock**: WSP_00 -> WSP_15 -> WSP_50 -> WSP_64 -> WSP_83 -> WSP_87 -> WSP_97 -> WSP_104 -> WSP_22

---

## 1. Discovery rule matrix (R1-R11 + C1-C4)

Every spec rule maps to exactly one validator function. Each function returns
a list of `Violation` records sharing the function's `rule_id` suffix.

| Spec ID | Function       | Severity | Inputs                  | Expected (derivation)                                                                          | Actual (from)              | Pass/Fail semantics                                            |
|---------|----------------|----------|-------------------------|------------------------------------------------------------------------------------------------|----------------------------|----------------------------------------------------------------|
| R1      | `rule_R1`      | error    | projection, registry    | `foundup_id` is a member of `{e.foundup_id : e in registry.entities}`                          | projection `foundup_id`    | FAIL if any projection id is absent from registry              |
| R2      | `rule_R2`      | error    | projection, registry    | Exact case match for `foundup_id`                                                              | projection `foundup_id`    | FAIL if case-folded match exists but exact match does not      |
| R3      | `rule_R3`      | error    | projection, schema      | `portfolio_status in {not_portfolio, portfolio_candidate, portfolio_ready, portfolio_featured}` | projection field            | FAIL on any other value                                        |
| R4      | `rule_R4`      | error    | projection, schema      | `poc_landing_status in {none, placeholder, functional, polished}`                              | projection field            | FAIL on any other value                                        |
| R5      | `rule_R5`      | warning  | projection              | Each URL field is `null` or matches `^https?://` permissive guard                              | projection URL fields       | WARN per malformed value                                       |
| R6      | `rule_R6`      | warning  | projection              | `len(public_summary) <= 280` when non-null                                                     | projection field length     | WARN if exceeded                                               |
| R7      | `rule_R7`      | error    | projection              | `portfolio_priority is None OR (int and 1 <= v <= 100)`                                        | projection field            | FAIL on type or range violation (booleans rejected)            |
| R8      | `rule_R8`      | error    | projection, registry    | `registry.entries[id].portfolio_status`                                                        | projection `portfolio_status` | FAIL on mismatch; skipped for ids R1 already flagged           |
| R9      | `rule_R9`      | error    | projection, registry    | `registry.entries[id].portfolio_ready` (default false)                                         | projection `portfolio_ready` | FAIL on mismatch                                               |
| R10     | `rule_R10`     | warning  | projection, registry    | Count of registry entries with `portfolio_status in {candidate, ready, featured}`              | `len(projection.entities)`  | WARN if not equal                                              |
| R11     | `rule_R11`     | error    | projection, registry    | Every projection `foundup_id` must be present in registry (orphan guard)                       | projection foundup_ids      | FAIL per orphan; intentionally complements R1 with spec ID     |
| C1      | `rule_C1`      | warning  | projection              | If `portfolio_ready=true` then `poc_landing_status != 'none'`                                  | projection fields           | WARN if violated                                               |
| C2      | `rule_C2`      | error    | projection              | If `portfolio_status='portfolio_featured'` then `portfolio_ready=true`                         | projection field            | FAIL if featured without ready                                 |
| C3      | `rule_C3`      | error    | projection, registry    | Registry `portfolio_status='not_portfolio'` => id absent from projection                       | projection membership       | FAIL per leaked id                                             |
| C4      | `rule_C4`      | warning  | projection              | For `foundup_id='holoindex_prod_01'`: `is_dual_identity=true`                                  | projection field            | WARN if missing/false                                          |

**Notes on severity choices for C-checks** (the spec's section 6.3 does not
list a severity column for C-checks):

- C1: warning - violates a soft consistency constraint, not a hard schema rule
- C2: error - the featured tier implies the readiness gate is locked, missing
  it is a structural violation, not a soft inconsistency
- C3: error - the filter rule in spec section 6.4 is non-negotiable
- C4: warning - `is_dual_identity` is a presentational enrichment field that
  is currently absent from the projection schema; surfacing as a warning lets
  the generator slice fix it without flipping the validator red

**Supplementary informational stat** (NOT a spec rule): `registry_inventory_coverage`
captures `registry_total` (14) vs `projection_total` (3). The architect brief
explicitly required separating this from R10 (which is portfolio-eligible only).
It appears in `report.stats`, not in `report.violations`.

## 2. Spec compliance verification

| Spec section | Coverage |
|--------------|----------|
| 6.1 Structural validation (R1-R7) | Implemented (`rule_R1` ... `rule_R7`) |
| 6.2 Source of truth validation (R8-R11) | Implemented (`rule_R8` ... `rule_R11`) |
| 6.3 Consistency checks (C1-C4) | Implemented (`rule_C1` ... `rule_C4`) |
| 6.4 Filter rules | Enforced via C3 (`not_portfolio` cannot appear in projection) |
| 5.x HoloIndex dual identity | Surfaced via C4 |

A test `test_rules_registry_covers_full_spec` enumerates the full expected
set `{R1..R11, C1..C4}` against the implemented `RULES` tuple to prevent
silent drift in coverage.

## 3. Detected drifts from current repo state

Running `python -m modules.foundups.portfolio_validator --check --json`
against `main @ af7c46be` produces the following violation set (exit code 1):

```json
[
  {
    "rule_id": "R1",
    "severity": "error",
    "entity": "holoindex_prod_01",
    "field": "foundup_id",
    "expected": "<present in foundup_registry.json>",
    "actual": "holoindex_prod_01",
    "source": "registry",
    "message": "Projection entity 'holoindex_prod_01' has no matching entry in foundup_registry.json"
  },
  {
    "rule_id": "R10",
    "severity": "warning",
    "entity": "global",
    "field": "entities.length",
    "expected": 2,
    "actual": 3,
    "source": "registry",
    "message": "Projection lists 3 entities, but registry has 2 portfolio-eligible entries (status in ['portfolio_candidate', 'portfolio_featured', 'portfolio_ready'])"
  },
  {
    "rule_id": "R11",
    "severity": "error",
    "entity": "holoindex_prod_01",
    "field": "foundup_id",
    "expected": "<must be backed by a registry entry>",
    "actual": "holoindex_prod_01",
    "source": "registry",
    "message": "Projection entity 'holoindex_prod_01' has no registry backing (orphan projection entry)"
  },
  {
    "rule_id": "C4",
    "severity": "warning",
    "entity": "holoindex_prod_01",
    "field": "is_dual_identity",
    "expected": true,
    "actual": null,
    "source": "projection",
    "message": "HoloIndex projection must set is_dual_identity=true (spec section 5)"
  }
]
```

Supplementary stats:

```json
{
  "registry_total": 14,
  "registry_portfolio_eligible": 2,
  "projection_total": 3,
  "registry_inventory_coverage": {
    "registry_total": 14,
    "projection_total": 3,
    "delta": 11,
    "note": "Informational only - not a spec rule."
  }
}
```

### 3.1 Empirical confirmation against canonical sources

Direct file reads (not relying on HoloIndex retrieval) confirm:

| Source                                  | foundup_id `holoindex_prod_01` present? |
|-----------------------------------------|------------------------------------------|
| `modules/foundups/foundup_registry.json`| NO (14 entries; none have this id)       |
| `modules/foundups/holoindex_prod_01/foundup_manifest.json` | YES                  |
| `public/member/mall-video-catalog.json` | YES                                      |
| `public/f/portfolio_data.json`          | YES                                      |

The architect's brief specifically warned against fabricating a
`registry says portfolio_status=not_portfolio` claim. The validator does
**not** make this claim: R8/R9/C3 are explicitly skipped for any
`foundup_id` that R1 already flagged as absent from the registry (see
`rule_R8` skip path), and the negative test
`test_real_repo_does_not_claim_holoindex_is_not_portfolio` enforces this.

### 3.2 New drifts surfaced beyond the architect's two known cases

- **C4 (warning)**: HoloIndex entry in current projection is missing the
  `is_dual_identity` field required by spec section 5.

No other new drifts were detected.

### 3.3 holoindex_prod_01 drift resolution — explicit decision required

The validator intentionally does NOT create a silent exception for
`holoindex_prod_01`. While it has catalog + manifest evidence (and may be
intentionally discoverable as an external public FoundUp surface), the
projection spec states that portfolio projection must be registry-backed.

The validator surfaces this drift to force an **explicit** future decision:

| Option | Action | Owner Slice |
|--------|--------|-------------|
| A (architect preference) | Add `holoindex_prod_01` to `foundup_registry.json` with `portfolio_status=portfolio_candidate` | `HOLOINDEX_REGISTRY_ENTRY_PHASE1` (future) |
| B | Amend the projection spec to allow catalog+manifest-backed exceptions | `PORTFOLIO_DATA_PROJECTION_SPEC_AMENDMENT_PHASE1` (future) |
| C | Remove `holoindex_prod_01` from `portfolio_data.json` | `PORTFOLIO_DATA_CURRENT_STATE_FIX_PHASE1` (future) |

**Architect guidance**: Option A is preferred. The registry is the canonical
source of truth for portfolio eligibility, and HoloIndex as an external public
FoundUp surface should be properly registered rather than exempted.

This validator slice does **not** implement any of these options — it only
reports the drift. Resolution belongs to a dedicated future slice.

## 4. HoloIndex assessment

### 4.1 Queries executed

| Query                                            | Result quality          |
|--------------------------------------------------|-------------------------|
| `portfolio data validator rules`                 | WEAK - no direct hits   |
| `foundup registry schema validation`             | WEAK - no direct hits   |
| `consistency check projection drift`             | WEAK - no direct hits   |

None of the three queries surfaced the canonical spec document
(`docs/audits/architecture/FOUNDUPS_PORTFOLIO_DATA_PROJECTION_SPEC_PHASE1.md`).
Top hits were thematically related (WSP framework retrieval, generic schema
discussions) but did not include the spec or its sibling display/schema docs.

### 4.2 Fallback used

Direct file reads via `Read` tool of:

- `docs/audits/architecture/FOUNDUPS_PORTFOLIO_DATA_PROJECTION_SPEC_PHASE1.md`
- `modules/foundups/foundup_registry.json`
- `modules/foundups/foundup_registry.schema.json`
- `public/f/portfolio_data.json`
- `public/member/mall-video-catalog.json`
- `modules/foundups/holoindex_prod_01/foundup_manifest.json`

A scripted Python pass cross-referenced catalog vs registry ids to confirm
the membership findings empirically.

### 4.3 Recommendation

This confirms the architect's preflight finding. The audit/spec docs in
`docs/audits/architecture/` are not consistently surfacing for slice-scoped
queries. Recommendation:

- **Index audit/spec docs by slice ID**. Adding a `slice_id` field to the
  HoloIndex metadata for documents in `docs/audits/architecture/` (or
  re-embedding them with the slice ID prepended to the searchable text)
  would have surfaced this spec on a query containing
  `PORTFOLIO_DATA_VALIDATOR_PHASE1` or `FOUNDUPS_PORTFOLIO_DATA_PROJECTION`.
- A separate slice (e.g. `HOLOINDEX_AUDIT_DOC_SLICE_ID_INDEXING_PHASE1`)
  should own this work; it is **out of scope** for the validator slice.

## 5. Phase 2 next-slice recommendation

> Do **not** activate the validator as a CI gate yet.

Following the precedent of PR #670 (redteam observation), the next slice
should be:

`PORTFOLIO_DATA_VALIDATOR_CI_OBSERVATION_PHASE1`

Scope:

1. Add a report-only CI job that runs `python -m modules.foundups.portfolio_validator --check --json`.
2. Set `continue-on-error: true` so the job is non-blocking.
3. Upload the JSON report as a CI artifact.
4. Start a 14-day observation window.

Only after the 14-day window passes with consistently green or
known-and-acknowledged drift should a Phase 3 slice
(`PORTFOLIO_DATA_VALIDATOR_CI_GATE_PHASE1`) consider promotion to a blocking
gate. Two interim slices typically precede that promotion:

- `PORTFOLIO_DATA_CURRENT_STATE_FIX_PHASE1` to reconcile the current drift
  (e.g., register `holoindex_prod_01` properly or remove from projection
  pending generator slice).
- `PORTFOLIO_DATA_GENERATOR_PHASE1` to make the projection generated rather
  than hand-edited.

## 6. WSP_97 Verdict

| Label                              | Status |
|------------------------------------|--------|
| PORTFOLIO_VALIDATOR_PHASE1_ONLY    | YES    |
| READ_ONLY_VALIDATOR                | YES    |
| NO_REGISTRY_MUTATION               | YES    |
| NO_CATALOG_MUTATION                | YES    |
| NO_MANIFEST_MUTATION               | YES    |
| NO_PROJECTION_MUTATION             | YES    |
| NO_UI_IMPLEMENTATION               | YES    |
| NO_ROUTE_CHANGE                    | YES    |
| NO_HOLOINDEX_CORE_MUTATION         | YES    |
| NO_MCP_CHANGE                      | YES    |
| NO_CI_GATE_ACTIVATION              | YES    |
| NO_DEPENDENCY_INSTALL              | YES    |
| NO_CABR_READY                      | YES    |
| NO_PAYOUT_READY                    | YES    |
| NO_DAO_ACTIVATION                  | YES    |

### 6.1 Mutation evidence

- No diff touches `modules/foundups/foundup_registry.json`,
  `modules/foundups/foundup_registry.schema.json`,
  `public/member/mall-video-catalog.json`,
  `public/f/portfolio_data.json`, or any `foundup_manifest.json`.
- No diff touches `public/f/index.html`, route handlers, or HoloIndex core.
- No diff touches `.github/workflows/`, `requirements*.txt`,
  `pyproject.toml`, or any dependency manifest.
- The CLI exposes only read flags (`--check`, `--json`, `--repo-root`); no
  `--fix` / `--update` / `--write` paths exist.
- The validator imports only stdlib (`json`, `re`, `argparse`,
  `pathlib`, `dataclasses`, `subprocess` in tests). No new dependencies.

**Verdict**: PASS.

## 7. Sources

| Document                                    | Path |
|---------------------------------------------|------|
| Phase 1 spec (this slice consumes)          | `docs/audits/architecture/FOUNDUPS_PORTFOLIO_DATA_PROJECTION_SPEC_PHASE1.md` |
| Public portfolio status schema              | `docs/audits/architecture/FOUNDUPS_PUBLIC_PORTFOLIO_STATUS_SCHEMA_PHASE1.md` |
| Display component                           | `docs/audits/architecture/FOUNDUPS_PORTFOLIO_DISPLAY_COMPONENT_PHASE1.md` |
| Validator implementation                    | `modules/foundups/portfolio_validator/src/validator.py` |
| Validator CLI                               | `modules/foundups/portfolio_validator/__main__.py` |
| Validator tests                             | `modules/foundups/portfolio_validator/tests/test_validator.py` |
| Validator README                            | `modules/foundups/portfolio_validator/README.md` |

---

*Slice authored under WSP_00 -> WSP_15 -> WSP_50 -> WSP_64 -> WSP_83 -> WSP_87 -> WSP_97 -> WSP_104 -> WSP_22.*
*Slice: PORTFOLIO_DATA_VALIDATOR_PHASE1*
