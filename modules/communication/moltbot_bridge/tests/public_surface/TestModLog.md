# Public-surface TestModLog

## 2026-10-06 — fresh-main host recovery salvage

- Base `2837b0db389c567de9a5402e22fa711affcf176d`; source and existing public tests
  are unchanged from #1680's base. Salvaged its owned source/test delta, not its
  stale registry or backend manifest. #1680 and #1641 are historical evidence.
- Read this inventory, README, fixtures and nearest tests before restoring
  the distinct host-lifecycle test file. Added five cases there; no duplicate
  test scaffold. Three failed against the salvaged source: unconfigured reclaim,
  legacy completion of an owned reservation, and missing lease as recovery proof.
- The candidate requires configured recovery and a recorded expired lease,
  and matches reservation ownership even for legacy ownerless completion.
  Exact expiry and idempotence controls pass. Preserved Lick, nonce/revision,
  expiry, no-refund accounting and all existing policy/HTTP assertions.
- Windows Python 3.12.2, isolated dependencies matching the admission workflow:
  **210 passed, zero skips; 95% branch-aware combined coverage**, HTTP 94%,
  policy 90%, gate 98%. Existing 90% floor and WSP62 bounds remain unchanged.
  The two inherited pytest asyncio-config warnings are understood: plugin
  autoload is intentionally disabled and async tests use `asyncio.run`.
- Evidence outside the checkout: `O:/Foundups-Agent-audits/reddog-host-recovery-20261006/`.
  `salvage-negative.xml` retains the three failures; `public-boundary.xml`
  retains the candidate pass. Initial system Python lacked FastAPI; the isolated
  pinned environment resolved collection without changing project dependencies.
- Exact-main baseline passed189 cases. Independent review passed62 host/HTTP/Lick
  cases with no blocker. Manifest integrity8/8 and all15 fast-tier groups pass;
  registry1691/270 is current. FMAS exact-base diagnostic has zero errors and129
  pre-existing warnings after keeping the oversized module log at its base length.
- Exact-head hosted CI/review and main readback remain publication gates;
  their final immutable evidence belongs to the replacement PR and closure receipt.
  No running resident, provider termination, AutoPost sensory transport, deployed
  website, live HoloIndex freshness or private 0102 access is claimed.

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
  both new suites collectable, unchanged 269 quarantined files.
- Temporary branch-only registry writer is removed after that successful run.
  Fresh final-head CI remains the merge gate.
