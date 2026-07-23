# WSP Framework Change Notification

**WSP ID**: WSP_97_System_Execution_Prompting_Protocol
**Change Type**: Repository-evidence validation contract hardening
**Approval Class**: APPROVAL_REQUIRED
**Approval Required**: YES
**Approval Satisfied**: YES
**Approval Source**: Explicit 012/user direction in this task to implement and amend the active admission contract
**Proposed By**: 0102 Architect
**Timestamp**: 2026-07-23T22:03:23Z
**Slice**: WSP97_REPOSITORY_EVIDENCE_V11_PHASE1
**Base Commit**: `be855d74bab9e78105d0ba0fed4ddc935e053284`
**MPS**: 19/P0

## Change Summary

WSP 97 advances to protocol 1.7 and receipt schema
`wsp97_execution_receipt.v1.1`. Default admission now resolves only
`action_evidence.retrieve_wsps` against an explicit Git worktree and base,
while all other evidence remains opaque. Missing-schema and v1.0 receipts fail
closed; legacy structural checking is diagnostic and non-admitting.

## Impact Analysis

- Receipt producers must emit the explicit v1.1 schema and base commit.
- Every declared WSP must map to an exact tracked canonical framework path.
- Absolute, drive, UNC, traversal, wrong-case, untracked, symlink, junction,
  and reparse paths cannot satisfy WSP retrieval evidence.
- No provider, model, credential, network, or runtime worker call is introduced.
- The validator binds invoking-worktree ancestry, not an immutable final tree or
  proof that claimed execution occurred.
- Receipt and evidence sizes, Git calls, and process duration are bounded.
  Output is redirected to tempfiles to avoid RAM amplification; 65,536 bytes
  is a post-run accepted-output cap, not a write-time tempfile bound.
- Exact context/base/path/WSP syntax is rejected before root resolution or Git.
  Root components are then lstatted before every other root operation.
- Malformed or over-limit evidence stops before repository subprocesses.

## Receipt Inventory

Only these receipts present at the named base were migrated:

1. `docs/audits/ai_intelligence/CONFIGURED_AUTORESEARCH_GATEWAY_WSP97_EXECUTION_RECEIPT_PHASE1.json`
2. `docs/audits/ai_intelligence/OPENROUTER_MODEL_EXECUTION_CONTROL_EVIDENCE_PHASE_B1_WSP97_EXECUTION_RECEIPT.json`
3. `docs/audits/infrastructure/HOLOINDEX_REDDOG_WSP97_EXECUTION_RECEIPT_PHASE1.json`
4. `docs/audits/infrastructure/HOLOINDEX_QUERY_ROOT_ADMISSION_WSP97_EXECUTION_RECEIPT_PHASE1.json`

No broader historical receipt migration is claimed.

## Validation Record

- Initial RED: `python -m pytest tests/test_wsp97_execution_validator.py -q`
  returned 31 failed, 2 passed, and 1 capability-only skip.
- Bounded-contract RED:
  `python -m pytest tests/test_wsp97_repository_evidence.py tests/test_wsp97_execution_validator.py -q`
  returned 15 failed, 38 passed, and 1 capability-only skip.
- Cheapest-first RED: the same combined pytest command returned 16 failed, 56
  passed, and 1 capability-only skip.
- Final GREEN: the same combined pytest command returned 74 passed and 1
  capability-only real-symlink skip. Deterministic POSIX symlink and Windows
  junction/reparse seams passed.
- `python -m ruff check tools/wsp97_execution_validator.py tools/wsp97_repository_evidence.py tests/test_wsp97_execution_validator.py tests/test_wsp97_repository_evidence.py`
  returned `All checks passed!`.
- `python -m compileall -q` over those four Python files returned exit `0`.
- AST function-size verification returned no function over 50 lines.
- Each inventoried receipt returned exit `0` from
  `python tools/wsp97_execution_validator.py <receipt> --repo-root . --expected-base be855d74bab9e78105d0ba0fed4ddc935e053284`.
- `git diff --check` returned exit `0`.

## Mirror Parity

- Framework and knowledge canonical Git blob-content markdown SHA-256:
  `58c6643c285cce387cc4339df31726f07bcc21937298f890aef8def333fa76c8`.
- Framework and knowledge canonical Git blob-content JSON SHA-256:
  `1dde486036cd7965457ac827b03b93d45866c73faf59ab8fafdd59e8019c52ca`.
- Byte equality is required and was verified for both governed Git pairs and
  both checked-out pairs. Git blob-content hashes avoid platform line-ending
  ambiguity.

## Backup and Recovery Record

- Framework MD and JSON plus their `WSP_knowledge/src/` mirrors are changed
  together and must be byte-identical before commit.
- Git is the recovery record. Revert the focused slice commit to restore the
  prior protocol/validator; no `WSP_knowledge/archive/` snapshot was warranted.
- The final focused commit SHA is emitted in the Git handoff after amendment;
  no push or rebase is part of this notification.
