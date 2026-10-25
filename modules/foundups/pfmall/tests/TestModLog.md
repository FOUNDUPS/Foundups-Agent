# p.fMALL Test ModLog

## 2026-10-26 — Member draft intake, test-first allocation

The distinct `test_clerk_proposal_intake.py` owner covers real ephemeral RSA
signatures through the actual FastAPI route, body-before-auth ordering, bearer/
issuer/origin/time/session policy, wire caps, generic rejection and identity
minimization. Existing HTTP/nomination/HMAC/mapper/transport/validator owners are
unchanged. Allocation6efb68f50 precedes tests and product authoring.
Credential-free Python3.12.10/pytest9.0.3/PyJWT2.15.1/cryptography46.0.7/
FastAPI0.128.0/Starlette0.50.0/httpx0.28.1 baseline695PASS. Initial80-case RED:
695PASS/2FAIL/78ERROR (missing adapter/route). Boundary additions follow before
the final test freeze. Logs/JUnit/exact cases/source hashes are external under
`foundups-member-intake-20261026`. No live identity, deployment, OS confinement
or full-repository promotion claim. WSP6/22/50/84/97.

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
