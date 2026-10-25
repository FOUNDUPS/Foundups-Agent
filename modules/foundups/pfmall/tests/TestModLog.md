# p.fMALL Test ModLog

## 2026-10-23 — Private item handoff documentation and shared matcher

- Added no Python runtime or private-media endpoint in this contract slice.
  Verified linked document targets, draft-field alignment, manifest byte sizes
  and hashes, navigation syntax and registry preservation.
- The affected existing member VM harnesses passed; detailed regression and
  21/21 concierge results are in `public/member/tests/TestModLog.md` and the PR.
  The matcher regression fails on unchanged source before the repair.
- C1-C3 acceptance is specified in `../AUTOPOST_ITEM_CAPTURE_HANDOFF.md`:
  two-item local grouping/reload, original-media integrity, cross-principal
  denial, idempotent revisions and private rendering are future proofs.
- No new pytest, live upload, phone, provider deployment, private ACL or Holo
  generation proof is claimed by documentation verification.

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
