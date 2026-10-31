# Preserved historical record: TestModLog.md

> Historical/proposal material. This is not a current acceptance receipt, runtime check or instruction to apply old code. The original dates and claimed outcomes below retain their historical scope.

- Original relative path: `modules/foundups/agent_market/tests/TestModLog.md`
- Original PC base: `0c81418fe94a7786cfd55f01e138ddc5d510583d`
- Original full file SHA-256: `88611695dd1efedfa3aaa0ed473a32d618a596a80f29459cd01e7fbfadf18cd7`
- Preserved record SHA-256: `98a9fa99b51781d45a2cb4aa11c97ce1b3d1c78314db9b3c452a2fbf1005c687`
- Projection created: `2026-10-30T02:00:12.626831+00:00` (processing time only; not a new observation)
- Comparison reference: `cbef41fbae1ba1105398183e42b008f2e7dfd3dc`
- Publication: proposed; independent auditor acceptance pending.
- Current owner(s): [token_factory.py](../../../../../../../../../modules/foundups/agent_market/src/token_factory.py), [README.md](../../../../../../../../../modules/foundups/agent_market/README.md)

Disposition: Archive the P0A 190-test and 17-file inventory addition with its original date and scope. It is not a current module test count, current fixture inventory or post-merge result.

Private host paths and unresolved external identifiers may be omitted only in this projection; raw originals remain in the private custody backmap. External citations are retained as historical references and have not been refreshed. Runtime and commenting remain unverified.

## Historical content


## 2026-10-22 - P0A token-factory selection

- Reused `test_orchestrator.py` after checking this log, tests README, source
  contract and scoped callsites. Added 42 cases; current file has 49 cases.
- Before source fix: 30 failed / 13 passed in the initial 43-case regression run.
  After initial fix: 47 passed. Independent review then reproduced connectivity
  identity drift in two new cases; final fix is covered by module closure below.
- Final command: `$env:PYTHONDONTWRITEBYTECODE='1'; $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; ./.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider --basetemp <scratch>/pytest modules/foundups/agent_market/tests`.
- Result: **190 passed**, including all 49 orchestrator cases, in 116.89 seconds.
  The runner additionally blocked sockets/DNS and redirected TEMP/TMP and database
  paths outside the repository; two network attempts were blocked before I/O.
  The focused token-factory run recorded zero attempts. No new services installed.
- Follow-up attribution: all 13 existing E2E cases pass under the same socket/DNS
  guard. Both blocked attempts occur in `test_fam_adapter_handle_intent_help`,
  through `huggingface_hub` HTTP requests. Sanitized stack evidence is in the
  receipt; this is an existing help/enrichment dependency, outside P0A.
- Warnings: the two repo asyncio options are inactive when plugin autoload is
  disabled. These are config warnings, not failed asynchronous execution tests.
- New cases cover unsupported/empty/non-string hints; unregistered, disconnected
  or errored hint/default/mock backends; normalized explicit selection; identified
  mock success; registration/health/result chain identity; and actual-factory
  launch rejection versus simulated success. Negative selection cases verify no
  backend effect call; result mismatch is post-call rejection with no cached success.
- Exact executed node IDs, source hashes, red/green/module receipts, retrieval
  evaluation and independent review are in the
  [P0A receipt](../../../../../plans/docs/plans/research/2026-10-22-token-factory-fail-closed-receipt.json).
- Validation is local; no real chain/contract, signer, live RPC or custody claim.

### Current file inventory (17, no new test file)

```text
test_cabr_gate.py                 test_cabr_hooks.py
test_compute_access.py            test_deterministic_ids.py
test_distribution.py              test_e2e_integration.py
test_fam_daemon.py                test_migrations.py
test_mvp_offering.py              test_orchestrator.py
test_permissions.py               test_persistence.py
test_persistent_compute_wiring.py  test_repository_factory.py
test_schemas.py                   test_sqlite_adapter.py
test_task_lifecycle.py
```
