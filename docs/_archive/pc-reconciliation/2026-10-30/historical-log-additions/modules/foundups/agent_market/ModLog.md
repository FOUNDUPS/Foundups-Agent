# Preserved historical record: ModLog.md

> Historical/proposal material. This is not a current acceptance receipt, runtime check or instruction to apply old code. The original dates and claimed outcomes below retain their historical scope.

- Original relative path: `modules/foundups/agent_market/ModLog.md`
- Original PC base: `0c81418fe94a7786cfd55f01e138ddc5d510583d`
- Original full file SHA-256: `00052fad12e07f7923d9b125ac76578685bf7277b37707a4113a3696cd6225e6`
- Preserved record SHA-256: `8508efc825dac1ecec5be3161e7e9e33192b4c5e2188c8f167431d5eb3265b3b`
- Projection created: `2026-10-30T02:00:12.626831+00:00` (processing time only; not a new observation)
- Comparison reference: `cbef41fbae1ba1105398183e42b008f2e7dfd3dc`
- Publication: proposed; independent auditor acceptance pending.
- Current owner(s): [token_factory.py](../../../../../../../../modules/foundups/agent_market/src/token_factory.py), [authorization.py](../../../../../../../../modules/foundups/agent_market/src/authorization.py), [sqlite_adapter.py](../../../../../../../../modules/foundups/agent_market/src/persistence/sqlite_adapter.py)

Disposition: Archive the P0A implementation history. Current main includes the relevant token-factory owner and newer authorization/payout work; historical 190-test claims do not cover those newer changes or live settlement.

Private host paths and unresolved external identifiers may be omitted only in this projection; raw originals remain in the private custody backmap. External citations are retained as historical references and have not been refreshed. Runtime and commenting remain unverified.

## Historical content


## 2026-10-22 - P0A: Fail-Closed Token Factory Selection

- Resolved one requested/default chain; reject invalid hints, missing or
  disconnected backends, health-check errors and backend identity drift. Retain
  the existing default/explicit mock simulation with synthetic result metadata.
- Bind result validation to the resolved enum and reject different-chain success
  before caching. Reused domain `ValidationError` so the existing launch handler
  reports failure before token/repo/task completion. Public signatures unchanged.
- Extended existing `tests/test_orchestrator.py`, including actual-factory launch
  integration. Independent review found health-check identity drift; reproduced
  it, froze the selection through dispatch/result validation and added regression.
- Validation: 190 FAM module cases pass, including 49 orchestrator cases; sockets
  and DNS guarded with two attempts blocked before I/O. A focused trace attributes
  both to the existing help integration test's Hugging Face HTTP path. Factory
  regressions recorded zero attempts. Two inactive asyncio config warnings.
  Exact nodes and evidence are in `tests/TestModLog.md` and the linked receipt.
- Scope: local backend selection only. Authorization, accounting, durable
  deployment/outbox, synthetic treasury helpers and chain confirmation remain
  later gates. No signer/provider calls, deployment, funds or PR operations.
- WSP 00/6/11/22/50/84/97. Holo owner query failed with
  `HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`; direct verified reads, no reindex.
