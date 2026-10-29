# Tests - FoundUps Agent Market

## Local TestNet probe-intent acceptance (2026-10-25)

`test_testnet_transfer_intents.py` has 93 collected controls in 26 functions for
explicit host authority/identity/units/expiry, strict actual v3 schema, existing
pending history, full-content retries/reopen, rollback and two-adapter races.
Snapshots retain all 13 old mapped tables; the new table is checked separately.
Public fixtures are synthetic; no key, SDK, network or chain transaction is used.
Existing ORM tests explicitly union the one new mapper/table while retaining the
original 13-entry alias/pickle inventory unchanged.

Repaired focused 173 pass (93+80 existing compatibility cases), independently
reviewed 16 held-outs pass, and final agreed whole FAM 459/459 pass across 19 test
owners. These overlap and are not summed. Whole-run qualification prebinds 203
source files, uses real central-daemon scratch configuration and leaves it
stopped. Only optional help Holo/Qwen enrichment returns None. See
[TestModLog](TestModLog.md) for original REDs, the generated-column failure and
repair, fixture correction, rejected inventory run and separate diagnostic run.
Local preparation acceptance proves no resident integration, signer, funding,
chain effect or paid reward.

## Privileged operations (P0B)

Existing permission and transaction tests supply host contexts explicitly; never
add a fixture that grants authority from the actor or profile under test. Cover
absent/wrong principal/scope/role, self-verification, stored legacy bindings,
unchanged state on denial and authorized exact retries. Both memory and SQLite
owners are exercised, including direct SQLite initiation. See [TestModLog](TestModLog.md)
for exact executed inventory and whole-run external dependency isolation.

## Coverage Goals
- Exact token-backend selection and chain identity, preserving identified mock
  simulation; negative cases must not dispatch to a fallback backend.
- Schema validation for core entities.
- Lifecycle state transition correctness.
- Permission gating for verification and payout.
- Distribution gating and idempotent verified-milestone publish behavior.
- Launch orchestration and repo provisioning boundaries.
- Persistence migration/versioning and backend selection boundaries.
- F_0 investor subscription caps and MVP bid/resolve treasury injection rules.

## Persistent initiation acceptance (2026-09-22)

`test_persistent_compute_wiring.py` preserves the original three compute cases and adds56 bounded initiation cases: pending state, replay/reopen/lost response, immutable lineage, complete legacy history, zero-cost and changed-policy replay, all-write rollback, simultaneous adapters/shared wallet, lock timeout and pre-effect non-SQLite rejection. Connected persistence/migration/factory/compute/lifecycle/schema/permission/CABR suites total120 cases. Permission cases cover the in-memory PoC; they do not establish persistent role authority.

Keep baseline and candidate on identical case IDs and acceptance oracles. Use disposable explicit SQLite paths, actual -I/-B isolation and a reviewed external effect guard when qualifying this path. Preserve failed attempts and fixture corrections; test execution grants no live reward or runtime authority. Detailed counts and limitations are in [TestModLog](TestModLog.md).

## Persistent verification acceptance (2026-09-23)

The five historical failure observations are preserved in PR1892 and its evidence.
Their existing test owner now contains five desired rollback/replay controls with
real post-write SQL hooks. `test_verification_transaction.py` adds 36 controls for
identity/time equivalence, pending payout and later-approval retries, original cost,
corrupted history, legacy residues beyond 100 rows, missing prerequisites, competing
adapters, response loss and pre-session backend rejection. All use synthetic actors
and explicit disposable SQLite. The connected suite is 164 cases: baseline 141 pass /
23 failures; candidate and independent replay each pass the same 164, zero errors or
skips. Two inherited configuration warnings remain. See [TestModLog](TestModLog.md)
and [R24 acceptance](../../../../docs/roadmaps/R24_AGENT_PRODUCTION_LINE_PACKET.md#atomic-verification-acceptance--2026-09-23).

## Shared ORM compatibility (2026-09-23)

The historical three controls in `test_sqlite_adapter.py` qualified all14 legacy/new
class identities (Base plus13 rows), one registry/exact13-table inventory, trusted legacy pickle
GLOBAL references, and a current transient row round trip. They run with125
existing persistence/compute/lifecycle/schema/permission/CABR cases; all128 pass
locally and independently with fixed IDs. The one expected baseline failure was
the absent internal ORM owner. No existing test oracle changed.
The probe-intent layer now explicitly unions its additional mapper/table in the
two inventory assertions; the original13 aliases/pickle loops remain unchanged.
The defining module changes newly emitted pickle paths; no PostgreSQL service
or production verification authority was exercised. See [TestModLog](TestModLog.md).

## Run
```powershell
cd o:\Foundups-Agent
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -m pytest modules/foundups/agent_market/tests -q
```

## Tranche 2 Focused Run
```powershell
cd o:\Foundups-Agent
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
.\.venv\Scripts\python.exe -m pytest `
  modules/foundups/agent_market/tests/test_persistence.py `
  modules/foundups/agent_market/tests/test_sqlite_adapter.py `
  modules/foundups/agent_market/tests/test_migrations.py `
  modules/foundups/agent_market/tests/test_repository_factory.py -q
```
