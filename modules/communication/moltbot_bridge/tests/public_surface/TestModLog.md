# Public-surface TestModLog

## 2026-09-08 — Lick-aware host lease recovery (current slice)

- Verified replacement base: `e6dfa919f474158d0001296d3bd6e166129fc5f8`,
  which already contains the open-source non-biometric Lick PoC. The earlier
  lease branch/PR #1640 was based on pre-Lick `098436475737d17fdf06c6bf78de2671aef86da6`
  and is superseded rather than allowed to overwrite newer RedDog source.
- Isolated replacement branch:
  `feature/reddog-public-host-lease-recovery-v2-20260908`; PR #1641.
- WSP 97 scope decision: preserve the existing Lick consent/challenge/profile/
  receipt/cleanup paths and add host ownership around them. Process lease/crash
  recovery remains a distinct lifecycle contract, so it owns one focused
  `test_host_lease_recovery.py` file. The README also now lists the Lick test
  that was present on `main` but absent from the human test inventory.
- Source adds a nullable `busy_owner` migration and content-free
  `reddog_public_host_lease_v1` table while retaining `reddog_lick_open_v1`.
  Raw host-owner tokens are SHA-256 hashed before storage.
- Configured host owners are one-use. `register_host()` cannot replay a token;
  `renew_host()` extends only a currently live lease. Expired owner hashes are
  retained as tombstones so an old process identity cannot become valid again
  after orphan recovery.
- A configured host must hold a live lease before guest/Lick encounter,
  challenge completion, status, turn reservation, completion, withdrawal, or
  delivery. Busy turns are owner-bound. A separately registered replacement
  host may clear only a busy slot whose recorded owner lease is inactive.
- Recovery preserves revision, rotated nonce, Lick challenge-complete/profile
  state, session/subject/global counters, expiry, and no-authority semantics.
  It neither replays inference nor refunds a turn. Pre-lease busy rows with no
  owner evidence remain fail-closed.
- Review found a fail-open activation seam after the first green union run:
  `PublicSurfaceBinding` still accepted an unconfigured gate. Runtime was
  hardened so every HTTP-exposed public binding requires `gate.host_owner`.
  The ordinary HTTP helper and Lick HTTP flow now create/register lease-backed
  gates. The idle-expiry test separately renews the host lease so it continues
  to test guest idle expiry rather than host death.
- Exact verified source head before this evidence-only TestModLog update:
  `cb3bb342e69c3d0180e06927d3f594d41d72b629`.
- Focused GitHub Actions `34193746200`, Python 3.12.14: **205 passed, zero
  skips; 95% combined branch-aware coverage**. HTTP 94%, policy 90%, session
  gate 99%; the existing coverage floor remained unchanged. Two inherited
  pytest asyncio-configuration warnings remain; async cases execute with
  `asyncio.run`.
- Repository CI `34193746195`: **SUCCESS**. Canonical registry verification,
  RedDog fast tier, simulator, FAM, diagnostic security, and bounded resident-
  chain regression passed. Lint, security, and HoloIndex freshness jobs passed
  under their existing configurations; red-team remains explicitly report-only.
- Canonical registry generation used the existing generator and reports **1,645
  registered test files, 269 quarantined**. Both `test_lick_open_handshake.py`
  and `test_host_lease_recovery.py` are registered. The temporary branch-only
  writer self-removed before PR creation; counts were not hand-edited.
- This TestModLog update changes the PR head. One final exact-head focused and
  repository CI cycle is required before squash; the `cb3bb342...` green checks
  are evidence for the source state, not authorization for the later doc head.
- No live WSP_00 bootstrap, resident Holo owner CURRENT/no-gap receipt/repair,
  provider call, public host mount, site deployment, protected identity proof,
  or 3V engine invocation is claimed by this source/test evidence.

## 2026-09-08 — superseded pre-Lick lease evidence

- Earlier branch `feature/reddog-public-host-lease-recovery-20260908` started from
  `098436475737d17fdf06c6bf78de2671aef86da6` and opened PR #1640.
- PR-head `3d9393319be7cdf0c99420fa13f34350cc47de80` ran focused Actions
  `34192048020`: 190 passed, zero skips, 95% combined branch-aware coverage;
  repository CI `34192048206` also completed successfully.
- Those checks are **superseded evidence**. Review subsequently found a lease
  tombstone issue, and `main` independently advanced with overlapping Lick PoC
  changes. Neither the old branch nor its green checks may authorize merge.

## 2026-09-08 — guest status recovery and actual DB wrapper

- Base: `8980aa29b2a17655ad5d927c94059c068400c118`, merged through PR #1633.
- First verified source head: `8e32ed93708b524a6d2ae90d2d38960b142867b0`;
  test merge: `a54b6e2130ba356cbaa91904b8a15bbd2ee6f40e`.
- GitHub Actions run `34154124087`, job `101842278142`, Python 3.12.14:
  **177 passed, no skips; 95% combined branch-aware coverage**.
  HTTP 93%, policy 96%, session gate 97%; existing 90% floor unchanged.
- Added 25 cases through the existing two files: lost-response nonce recovery,
  no inference replay/refund/idle renewal, bearer/scope isolation, strict empty
  status body, exhausted/withdrawn sessions, actual DatabaseManager wrapper
  restart/concurrency/rollback, ASGI round trip and runtime WSP 62 bounds.
- `database_store` imports the unchanged DB manager with an isolated singleton
  and explicit temporary SQLite path. This is source integration evidence,
  not the configured PC or public host, process death or orphan recovery.
- Commands remain the exact bounded commands in README. Two inherited asyncio
  configuration warnings remain; async cases execute with `asyncio.run`.
- No fresh local pass is claimed: clone failed at DNS, and local execution
  tools later returned ClientError. A temporary read-only source-transfer
  workflow was removed before this source-head verification.
- No WSP_00 bootstrap, live Holo query/repair, RSI promotion, provider call,
  site deployment or protected principal authentication is claimed.
- Final-head CI and merge receipt belong to PR #1635; this earlier test result
  must not substitute for a later head's verification.

## 2026-09-08 — first bounded public guest slice

- Source baseline: `28273b0005563a41b9aa738654e0b70361542efb` (GitHub read).
- Local environment: isolated retrieved-source workspace, Python 3.13.5,
  pytest 9.0.2, coverage 7.13.3, FastAPI 0.128.2, HTTPX 0.28.1.
- Initial policy/SQLite execution: 133 passed.
- Expanded policy/SQLite/ASGI execution: 152 passed, no skips.
- Branch-aware coverage report: 94% combined; HTTP 92%, policy 94%, gate 97%.
- Every new runtime file is under 400 physical lines and every function under
  30 physical lines (AST check).
- Commands: the exact bounded commands in this directory's README.
- Test data and responder are synthetic. No real provider, paid inference,
  biometric, private principal data, live site or PC runtime was exercised.
- WSP_00/Holo owner execution was unavailable locally because their checkout
  and runtime were absent; this is not a successful bootstrap or Holo proof.
- Full-checkout registry generation, CI and deployment evidence must be recorded
  in the PR. Historical pass counts are not substituted for those gates.

## CI portability repair

- GitHub Actions at source head `ea419dfed724a332e55aa9055766ba1eadf063c5`
  ran all 152 tests successfully on Python 3.12.14. Coverage then failed because
  the inherited repository config selected `modules/livechat/src` and ignored
  the suite include filter; no public-boundary coverage data was collected.
- Added an explicit suite `.coveragerc`; it measures all three source files with
  the same 90% floor without changing root coverage or any test assertion.
- The bounded full-checkout registry worker succeeded, producing commit
  `1d9406aec720f1e05b9bdd207806324df728054b`: 1,643 registered files,
  both then-current suites collectable, unchanged 269 quarantined files.
- Temporary branch-only registry writer was removed after that successful run.
  Fresh final-head CI remains the merge gate for each later slice.
