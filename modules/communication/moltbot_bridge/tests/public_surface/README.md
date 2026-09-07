# RedDog public-surface tests

This is a distinct public-guest boundary, not the authenticated private resident
transport or the existing OpenClaw webhook limiter. Parent test inventory and
nearby resident tests were read before adding this suite (WSP_97/WSP_22).

| File | Coverage |
|---|---|
| `conftest.py` | Loads the exact three source modules in an isolated namespace; creates a real temporary SQLite database; no legacy OpenClaw bootstrap |
| `test_policy_and_sessions.py` | All three origins, consent/self-claims, lowered-only policy, nonce/revision, daily/session quotas, real concurrent SQLite reservations, restart/clock/withdrawal and content minimization |
| `test_http_boundary.py` | Real FastAPI ASGI router; unavailable host, CORS, body bounds, bearer possession, privilege injection, quota headers, synthetic provider limits, timeout/ignored cancellation and withdrawal during response |

Run from repository root:

```sh
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m coverage run --rcfile=modules/communication/moltbot_bridge/tests/public_surface/.coveragerc -m pytest -q --confcutdir=modules/communication/moltbot_bridge/tests/public_surface modules/communication/moltbot_bridge/tests/public_surface
python -m coverage report --rcfile=modules/communication/moltbot_bridge/tests/public_surface/.coveragerc
```

The dedicated CI job runs the same bounded suite. Whole-repository, authenticated
host, Windows, external model, physical-phone and deployment verification remain
separate gates. These tests never spend tokens or contact a network provider.
The SQLite connection fixture matches the existing DatabaseManager connection
interface; it is not proof of an actual PC's configured AgentDB lifecycle.

Tests are registered through `generate_test_registry.py`, not hidden under
nonstandard filenames. See [TestModLog](TestModLog.md) for executed evidence.
