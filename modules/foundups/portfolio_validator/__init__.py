"""Portfolio Data Validator (Phase 1).

Read-only validator that detects drift between ``public/f/portfolio_data.json``
and its canonical upstreams (registry -> catalog -> manifest).

Spec: ``docs/audits/architecture/FOUNDUPS_PORTFOLIO_DATA_PROJECTION_SPEC_PHASE1.md``

WSP_97 boundaries:
  - PORTFOLIO_VALIDATOR_PHASE1_ONLY
  - READ_ONLY_VALIDATOR
  - NO_REGISTRY_MUTATION / NO_CATALOG_MUTATION / NO_MANIFEST_MUTATION / NO_PROJECTION_MUTATION
  - NO_CI_GATE_ACTIVATION (observation only this phase)
"""

from .src.validator import (
    ValidationReport,
    Violation,
    run_validation,
    load_sources,
)

__all__ = [
    "ValidationReport",
    "Violation",
    "run_validation",
    "load_sources",
]
