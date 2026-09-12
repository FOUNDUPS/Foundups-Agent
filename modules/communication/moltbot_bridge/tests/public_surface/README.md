# RedDog public-surface tests

This is a distinct public-guest boundary, not the authenticated private resident
transport or the existing OpenClaw webhook limiter. Parent test inventory and
nearby resident tests were read before changing this suite (WSP_97/WSP_22).

| File | Coverage |
|---|---|
| `conftest.py` | Loads the exact three source modules in an isolated namespace; provides raw SQLite and the unchanged actual DatabaseManager wrapper with an isolated singleton and temporary path; no legacy OpenClaw bootstrap |
| `test_policy_and_sessions.py` | All three origins, consent/self-claims, lowered-only policy, nonce/revision, daily/session quotas, concurrent SQLite reservations, restart/clock/withdrawal, content minimization, status recovery without renewal/refund and actual DB-wrapper transactions |
| `test_http_boundary.py` | Real FastAPI ASGI router; unavailable/unleased host, CORS, body bounds, bearer possession, privilege injection, quota headers, synthetic provider limits, timeout/ignored cancellation, withdrawal, lost-response status recovery, actual DB-wrapper round trip and WSP 62 bounds |
| `test_lick_open_handshake.py` | Non-biometric Lick consent, guest/display-name claims, one-use challenge, provisional no-authority receipt, expiry, withdrawal, raw-challenge minimization and lease-backed AutoPost HTTP round trip |
| `test_host_lease_recovery.py` | Distinct public-host lifecycle: one-use hashed owners, renewal, owner-bound busy slots, replacement recovery after expiry, no replay/refund, Lick survival, legacy fail-closed rows, schema migration and actual DatabaseManager restart |

Run from repository root:

```sh
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m coverage run --rcfile=modules/communication/moltbot_bridge/tests/public_surface/.coveragerc -m pytest -q --confcutdir=modules/communication/moltbot_bridge/tests/public_surface modules/communication/moltbot_bridge/tests/public_surface
python -m coverage report --rcfile=modules/communication/moltbot_bridge/tests/public_surface/.coveragerc
```

The dedicated CI job runs the same bounded suite. Whole-repository, authenticated
resident lifecycle, Windows, external model, physical-phone and deployment
verification remain separate gates. These tests never spend tokens or contact a
network provider. The `database_store` fixture executes the actual DatabaseManager
source, not a mock wrapper. Its temporary database and isolated singleton prove
source-level restart behavior only; they do not prove the production PC heartbeat,
process-death detector, edge ingress, provider termination or deployment.

Tests are registered through `generate_test_registry.py`, not hidden under
nonstandard filenames. `test_host_lease_recovery.py` is a separate test file
because process ownership/crash recovery is materially distinct from the guest
policy/HTTP/Lick contracts. The canonical registry must be regenerated after this
file is introduced on a branch; do not hand-edit its aggregate count.

See [TestModLog](TestModLog.md) for executed evidence and the
[canonical admission contract](../../../../../extensions/reddog/docs/REDDOG_PUBLIC_SURFACE_ADMISSION.md)
for unfinished host/client work.