# RedDog public-surface tests

This is a distinct public-guest boundary, not the authenticated private resident
transport or the existing OpenClaw webhook limiter. Parent test inventory and
nearby resident tests were read before adding this suite (WSP_97/WSP_22).

| File | Coverage |
|---|---|
| `conftest.py` | Loads the exact three source modules in an isolated namespace; provides raw SQLite and the unchanged actual DatabaseManager wrapper with an isolated singleton and temporary path; no legacy OpenClaw bootstrap |
| `test_policy_and_sessions.py` | All three origins, consent/self-claims, lowered-only policy, nonce/revision, daily/session quotas, concurrent SQLite reservations, restart/clock/withdrawal, content minimization, status recovery without renewal/refund and actual DB-wrapper transactions |
| `test_http_boundary.py` | Real FastAPI ASGI router; unavailable host, CORS, body bounds, bearer possession, privilege injection, quota headers, synthetic provider limits, timeout/ignored cancellation, withdrawal, lost-response status recovery, actual DB-wrapper round trip and WSP 62 bounds |

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
actual PC's configured AgentDB lifecycle, process death or orphan recovery.

Tests are registered through `generate_test_registry.py`, not hidden under
nonstandard filenames. The continuity slice extends the same two test files;
registry verification must still pass without hand-editing counts.
See [TestModLog](TestModLog.md) for executed evidence and the
[canonical work order](../../../../../extensions/reddog/docs/prompts/WSP97_REDDOG_PUBLIC_SURFACE_REMOTE_PROMPT.md)
for unfinished host/client work.
