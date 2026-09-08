# RedDog public-surface tests

This is a distinct public-guest boundary, not the authenticated private resident
transport or the existing OpenClaw webhook limiter. Parent test inventory and
nearby resident tests are read before extending the suite (WSP_97/WSP_22).

| File | Coverage |
|---|---|
| `conftest.py` | Loads the exact three public-boundary source modules in an isolated namespace; provides raw SQLite and the unchanged actual DatabaseManager wrapper with an isolated singleton and temporary path; no legacy OpenClaw bootstrap |
| `test_policy_and_sessions.py` | All three origins, consent/self-claims, lowered-only policy, nonce/revision, daily/session quotas, concurrent SQLite reservations, restart/clock/withdrawal, content minimization, status recovery without renewal/refund and actual DB-wrapper transactions |
| `test_http_boundary.py` | Real FastAPI ASGI router; unavailable host, CORS, body bounds, bearer possession, privilege injection, quota headers, synthetic provider limits, timeout/ignored cancellation, withdrawal, lost-response status recovery, actual DB-wrapper round trip and WSP 62 bounds |
| `test_lick_open_handshake.py` | Open-source non-biometric Lick PoC: explicit consent, guest/named claims, randomized one-use continuity challenge, provisional no-authority receipt, expiry/withdrawal, storage minimization, HTTP flow and rejection of biometric/privilege fields |
| `test_host_lease_recovery.py` | Distinct resident-host lifecycle: hashed one-use owner leases, renewal, live-owner protection, expired-owner orphan recovery, tombstone replay prevention, Lick/lease coexistence, pre-lease fail-closed migration, preserved nonce/revision/quota and actual DatabaseManager restart behavior |

Run from repository root:

```sh
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m coverage run --rcfile=modules/communication/moltbot_bridge/tests/public_surface/.coveragerc -m pytest -q --confcutdir=modules/communication/moltbot_bridge/tests/public_surface modules/communication/moltbot_bridge/tests/public_surface
python -m coverage report --rcfile=modules/communication/moltbot_bridge/tests/public_surface/.coveragerc
```

The dedicated CI job runs the same bounded suite. Whole-repository, authenticated
host, Windows, external model, physical-phone and deployment verification remain
separate gates. These tests never spend tokens or contact a network provider.
The `database_store` fixture executes the actual DatabaseManager source, not a
mock wrapper. Its temporary database and isolated singleton do not prove an
actual PC's configured AgentDB lifecycle or heartbeat scheduling.

The host-lease test is a separate file because process ownership/crash recovery
is a materially distinct lifecycle contract. It proves that only a separately
registered replacement host may reclaim a reservation after the prior owner's
lease expires, while the consumed turn, rotated nonce, Lick challenge state and
quota remain intact. Expired owner hashes remain tombstones so old process tokens
cannot be replayed. Legacy busy rows without owner evidence stay fail-closed.
Production still needs a resident startup/heartbeat/shutdown adapter before this
recovery mechanism can be activated.

Tests are registered through `generate_test_registry.py`, not hidden under
nonstandard filenames. Registry verification must include both the Lick and host
lease lifecycle tests without hand-editing counts. See [TestModLog](TestModLog.md)
for executed evidence and the
[canonical work order](../../../../../extensions/reddog/docs/prompts/WSP97_REDDOG_PUBLIC_SURFACE_REMOTE_PROMPT.md)
for unfinished host/client/private-cognition work.
