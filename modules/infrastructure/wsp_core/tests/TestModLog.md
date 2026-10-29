# WSP core test change log

## 2026-10-29 — Read-only audit contracts

Add 39 synthetic cases described in [README.md](README.md). Final frozen desired
acceptance: main3ad 31 failed / 8 passed; candidate 39 passed. The Windows byte
budget fixture uses actual fixture bytes so CRLF does not change the expected
uninspected file. No oracle was weakened to accept the former traversal/database
behavior. The production suite imports the real checker; baseline reproduction
remains an isolated, guarded harness in the reconciliation evidence directory.

Integrated audit selection: 173 passed / 28 subtests. Runtime and idle-consumer
selection: 24 passed. Registry selections: 62 passed. Three Node compatibility
suites passed. Exact-base Mode 2: zero errors, 127 warnings, 306 advisories.
These counts are separate selections and must not be presented as whole-suite
coverage. The registry retains 1784 prior rows and adds this test owner.

The standalone candidate also inspected actual main3ad in 14.11 seconds without
changing Git status, with one explicit uninspected submodule. Full repository
test collection, network dispatch and submodule inspection are not claimed.
WSP 5/6/22/50/71/97.
