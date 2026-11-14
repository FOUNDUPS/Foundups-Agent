# Tests

Offline tests never use credentials, paid endpoints or a physical microphone.
Install `../requirements-dev.txt` in the development environment (validated on
Python 3.12), then run from the repository root:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -p pytest_cov -p pytest_asyncio.plugin modules/platform_integration/elevenlabs_calls/tests modules/communication/voice_command_ingestion/tests modules/infrastructure/cli/tests/test_openclaw_voice_cue_parsing.py --cov=modules.platform_integration.elevenlabs_calls.src --cov-report=term-missing --cov-fail-under=90 -q
```

On PowerShell set `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'` first, then run the same
`python -m pytest ...` command. Provider client, CLI, persistence and profile
validation are exercised; only remote service and physical audio boundaries are
replaced. SDK profile parsing validates shape without an HTTP request.

- `test_calls.py`: exact request/contact validation, API serialization, profile
  drift, concurrent reservations, restart/timeout/interruption duplicates,
  redacted provider errors and truthful terminal status.
- `test_cli.py`: default preview, execute/status/provision/doctor, exact spoken
  trigger and actual CLI→shared Whisper adapter connection.
- Existing voice suites: selected language reaches Whisper/Cohere/Google,
  English compatibility, batch exports and prior cue behavior.

Coverage is measured for the new adapter only. Passing it is not a repository-wide
WSP 6 audit or a Japanese speech-accuracy measurement. See
[live acceptance](../docs/SETUP.md#5-check-results-and-close-the-live-acceptance-gate).
