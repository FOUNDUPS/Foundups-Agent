# Public-surface TestModLog

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
