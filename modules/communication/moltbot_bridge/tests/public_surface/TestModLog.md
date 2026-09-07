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
