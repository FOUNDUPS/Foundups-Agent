# p.fMALL Test ModLog

## 2026-10-25 — Root Play/About ownership and namespace-safe worker rollout

Reused the existing three gateway/media owners and member route VM. Canonical
gateway readers and missing-media catch-all oracle move to About. Root PWA
registration is tested through the shared directory; legal/admission and all
original assertions remain. New behavior controls cover root/FX framing,
fixed query/hash compatibility, exact directory registration, protected handoff,
explicit route headers and actual root-worker lifecycle/cache isolation.

Unchanged baseline:365 pass/3 absent-media prerequisites. Correct desired
RED:400 pass/40 fail (37 new controls plus the same3). Final four owners:
437 pass/the same3 failures, zero new failures or skips. Separate adjacent
selection:164 pass/3 unchanged member-worker regex failures, independently
reproduced by parent on untouched source; actual product/account/state and
projector controls pass. No empty media directories, quarantine or weakened
oracle was introduced. Phase counts overlap and are not cumulative.

Full exact case IDs, two inherited config warnings, commands/environment,
initial invalid preload setup, SHA snapshots, opaque attribute comparison and
limits are in `public/member/tests/TestModLog.md` from repository root and in
external `foundups-mall-home-695e26d23253404fac695e8fa797a5a3/*/results.json`.
All368 original IDs/assertions retained;72 added cases. Corrected guarded runs
record no network attempts. Local source verification is not Hosting/browser,
authentication-provider, media/voice, deployment or trading acceptance. Parent
owns independent review, generated registry/security artifacts and publication.

## 2026-10-25 — FX1 gateway link and public filter reuse

Extended the existing `test_gateway_roc_shell.py` with HTML-parser coverage of
the normal FX navigation anchor to `/f/`, accessible label and retained existing
links. The existing gateway/admission tests remain active. Extended the existing
member route VM for real filter callbacks; no new suite or public API.

Both complete files (`test_gateway_roc_shell.py` and
`public/member/tests/test_route_contract_bridge.py`) passed **300 cases**, zero
failures/skips, with two inherited unknown asyncio-config warnings. The initial
FX-only red run and exact green command/environment are recorded in
repository-root `public/member/tests/TestModLog.md`. Bytecode/cache writes were disabled;
scratch state stayed outside the checkout. This is local source evidence, not
browser layout, deployment, authentication-provider, asset or market evidence.

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
