# Portfolio Data Validator (Phase 1)

Read-only drift detector for `public/f/portfolio_data.json` against its
canonical upstreams.

- **Slice**: `PORTFOLIO_DATA_VALIDATOR_PHASE1`
- **Spec**: `docs/audits/architecture/FOUNDUPS_PORTFOLIO_DATA_PROJECTION_SPEC_PHASE1.md`
- **Worker**: W6
- **Mode**: Observation only — does **not** block CI in Phase 1.

## Why this exists

`public/f/portfolio_data.json` is a derived projection that must stay in sync
with three canonical sources:

| Layer | File | Role |
|------ |------|------|
| L1    | `modules/foundups/foundup_registry.json` | Entity definitions, portfolio fields |
| L2    | `public/member/mall-video-catalog.json`  | Runtime catalog metadata, launch_readiness |
| L3    | `modules/foundups/<id>/foundup_manifest.json` | Tier, lifecycle, entry_url, token_symbol |

This module surfaces drift between those layers and the projection. It is
**strictly read-only**: no source file is written or modified at any point.

## Usage

```bash
# Plain-text report (default)
python -m modules.foundups.portfolio_validator --check

# Machine-readable JSON report
python -m modules.foundups.portfolio_validator --check --json
```

### Exit codes

| Code | Meaning |
|------|---------|
| 0    | All rules pass — no drift detected |
| 1    | One or more violations (errors or warnings) — drift detected. A structured report is printed; the CLI does **not** raise. |
| 2    | A canonical source file is missing or unreadable (fail-closed input error) |

### Violation record shape

Each violation is emitted as:

```json
{
  "rule_id": "R1",
  "severity": "error",
  "entity": "holoindex_prod_01",
  "field": "foundup_id",
  "expected": "<present in foundup_registry.json>",
  "actual": "holoindex_prod_01",
  "source": "registry",
  "message": "Projection entity 'holoindex_prod_01' has no matching entry in foundup_registry.json"
}
```

## Rule coverage

All eleven structural/source-of-truth rules and four consistency checks from
the spec are implemented as standalone functions:

| Rule | Function          | Severity | Source vs target                                 |
|------|-------------------|----------|--------------------------------------------------|
| R1   | `rule_R1`         | error    | projection -> registry membership                |
| R2   | `rule_R2`         | error    | projection foundup_id case/format                |
| R3   | `rule_R3`         | error    | projection portfolio_status enum                 |
| R4   | `rule_R4`         | error    | projection poc_landing_status enum               |
| R5   | `rule_R5`         | warning  | projection URL fields                            |
| R6   | `rule_R6`         | warning  | projection public_summary length                 |
| R7   | `rule_R7`         | error    | projection portfolio_priority range/type         |
| R8   | `rule_R8`         | error    | registry vs projection portfolio_status          |
| R9   | `rule_R9`         | error    | registry vs projection portfolio_ready           |
| R10  | `rule_R10`        | warning  | projection count vs portfolio-eligible registry  |
| R11  | `rule_R11`        | error    | projection -> registry backing (orphan guard)    |
| C1   | `rule_C1`         | warning  | portfolio_ready=true => poc_landing_status != none |
| C2   | `rule_C2`         | error    | portfolio_featured => portfolio_ready=true       |
| C3   | `rule_C3`         | error    | not_portfolio entries must not appear in projection |
| C4   | `rule_C4`         | warning  | HoloIndex MUST set is_dual_identity=true         |

> **Note on coverage stats**: total registry inventory coverage
> (`registry_total` vs `projection_total`) is reported separately as
> *informational stats*, not as a rule violation. R10 only fires when the
> projection count diverges from the **portfolio-eligible** registry count.

## Tests

```bash
python -m pytest modules/foundups/portfolio_validator/tests/
```

The test suite exercises every rule in isolation (pass + fail), proves the
two known real-repo drifts surface against current main, and confirms exit
code 2 for missing/malformed inputs.

## What this is NOT

- **Not a generator.** Regeneration belongs to the future
  `PORTFOLIO_DATA_GENERATOR_PHASE1` slice.
- **Not a CI gate.** A CI integration is intentionally deferred to the
  follow-up slice `PORTFOLIO_DATA_VALIDATOR_CI_OBSERVATION_PHASE1`
  (report-only) before any consideration of promotion to a blocking gate.
- **Not a mutator.** No flag exposes write operations. The module imports
  only `json`, `re`, `argparse`, and pathlib from the stdlib.

## WSP_97 boundaries

| Label                              | Value |
|------------------------------------|-------|
| PORTFOLIO_VALIDATOR_PHASE1_ONLY    | YES   |
| READ_ONLY_VALIDATOR                | YES   |
| NO_REGISTRY_MUTATION               | YES   |
| NO_CATALOG_MUTATION                | YES   |
| NO_MANIFEST_MUTATION               | YES   |
| NO_PROJECTION_MUTATION             | YES   |
| NO_UI_IMPLEMENTATION               | YES   |
| NO_ROUTE_CHANGE                    | YES   |
| NO_HOLOINDEX_CORE_MUTATION         | YES   |
| NO_MCP_CHANGE                      | YES   |
| NO_CI_GATE_ACTIVATION              | YES   |
| NO_DEPENDENCY_INSTALL              | YES   |
| NO_CABR_READY                      | YES   |
| NO_PAYOUT_READY                    | YES   |
| NO_DAO_ACTIVATION                  | YES   |
