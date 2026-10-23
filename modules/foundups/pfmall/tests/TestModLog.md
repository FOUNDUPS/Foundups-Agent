# p.fMALL Test ModLog

## 2026-08-23 — Tier-0 repository regression

- Extended `holo_index/tests/test_tier0_retrieval_hardening.py` with a
  real-repository assertion for the tracked `modules/foundups/pfmall` module.
- The regression proves module-intent discovery includes PFMall, exact query
  inference resolves it, and both canonical Tier-0 files exist.
- No collection, embedding model, persistent store, network, replica, or
  reindex is used by the test.
- Candidate and detached original pre-rebase baseline `f06ca1f` each reported
  the identical 19 failing PFMall node IDs and 588 passes, proving no
  module-suite regression was introduced by this documentation slice. The
  exact post-#1538 Git parent is `69b7f073`.

## Existing coverage baseline

- Shell core: validation, discovery, catalog, routing, overlays, boot.
- Read adapters: Python and FastAPI surfaces plus static handoff.
- Member runtime: catalog, player, PWA, FoundUp entry, media delivery, gateway,
  and shell-local RedDog concierge.
- Safety: catalog truth gates and VerificationGapGuard protected-action rules.

See `README.md` in this directory for the file-level inventory and commands.
