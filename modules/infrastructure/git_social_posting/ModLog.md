# Legacy Git and social-posting utilities ModLog

## 2026-10-29 — Establish source-bound module contracts

Document the existing `scripts/posting_utilities.py`
owner in README and INTERFACE. This directory contains executable source; it is
not a data-only container. Record its actual call boundaries, delegated owners,
observable side effects and limitations instead of adding empty scaffolding or
claiming a running service. No source move, application import, live entrypoint,
provider action or runtime acceptance was performed for this documentation layer.

Validation is limited to source/hash and relative-link review. Module-local
behavioral coverage remains absent; downstream imports or historical messages are
not substituted for executable acceptance evidence. WSP 3/11/22/49/50/84/97.
