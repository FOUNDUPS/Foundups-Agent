# Public-surface TestModLog

## 2026-09-12 — current-main host lease reconciliation

- Base: `3b74a04205b05fc0d84172d52b8862ff608b1d6e`; isolated branch
  `fix/reddog-current-main-reconciliation-20260912`.
- WSP 97 audit first inspected current RedDog architecture/docs, AutoPost main,
  resident launcher/DAE broker, stale PR #1641 and stacked website PR #1648.
  The resulting evidence is recorded in
  `docs/audits/architecture/REDDOG_SURFACE_RUNTIME_RECONCILIATION_20260912.md`.
- Current main still contained the Lick-aware public gate without host/process
  ownership. The earlier #1641 lease work was therefore treated as tested
  historical evidence and rebuilt from current main rather than merged/rebased
  by overwrite.
- Runtime now adds one-use hashed host leases, owner-bound busy reservations and
  replacement recovery only after the prior lease expires. Recovery preserves
  nonce/revision, guest/Lick state, expiry and all usage counters; it never
  replays inference or refunds a turn. Legacy `busy_owner=NULL` rows remain
  fail-closed because migration does not prove a provider process is dead.
- `PublicSurfaceBinding` now rejects an unconfigured/unleased gate, closing a
  future mount path that could otherwise bypass process ownership.
- Existing guest, status and Lick tests were reused/extended. A distinct
  `test_host_lease_recovery.py` is justified because process crash ownership is
  a separate lifecycle contract. The Lick HTTP test and all public HTTP fixtures
  now use a registered host lease.
- AutoPost attention and website deployment are **not** implemented by this
  branch. Audit conclusion: preview/local Liquid vision/recording are distinct
  from RedDog attention; the next AutoPost slice must own explicit
  `dormant | attending` state. Website PR #1648 contains useful UI/OpenRouter
  work but duplicates the public session/accounting authority in D1 and must be
  reconciled before merge.
- Fresh branch pass count, coverage, canonical registry total and repository CI
  are deliberately **pending**. Historical #1641 results must not substitute for
  exact-head evidence from this branch.
- No live WSP_00 bootstrap, resident Holo owner query/repair, public mount,
  provider call, production PC heartbeat, protected 012/0102 authentication,
  private Memex disclosure, AutoPost voice transport or 3V engine invocation is
  claimed.

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
  tools later returned ClientError before source extraction/testing.
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