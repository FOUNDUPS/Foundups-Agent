# Secrets owner offline tests

`test_windows_pilot_credentials.py` loads the actual adapter without the MCP
package initializer and uses fake Win32 credential calls with synthetic values.
It checks exact custody targets, blob limits/freeing, static errors, hidden-input
fail-closed behavior, fixed child receivers and dropping unrelated credentials.
`scripts/tests/test_reddog_openrouter_telemetry_probe.py` uses synthetic HTTP
responses and verifies the fixed free-model request, bounded responses, redirect
and retry refusal, safe usage and content-free output.

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -B -m pytest -q --noconftest --import-mode=importlib -p no:cacheprovider -o addopts='' modules/infrastructure/secrets_mcp/tests/test_windows_pilot_credentials.py scripts/tests/test_reddog_openrouter_telemetry_probe.py
```

No live credentials, Windows vault access or network calls occur in this selection.
Existing vault/systemd/op resolver tests retain their own contracts.

`scripts/tests/test_reddog_langfuse_provision.py` uses ephemeral loopback sockets
and an injected synthetic store, never real credentials or the native vault. It
checks random nonce routing, Host/Origin equality, duplicate/framing headers,
body/field limits, fixed target, replay refusal, no raw diagnostics, expiry while
reading an incomplete body, and static top-level error handling. Its real-adapter
import case uses deliberately invalid values that fail before DLL/vault access.

```powershell
python -B -m pytest -q --noconftest --import-mode=importlib -p no:cacheprovider -o addopts='' scripts/tests/test_reddog_langfuse_provision.py modules/infrastructure/secrets_mcp/tests/test_windows_pilot_credentials.py scripts/tests/test_reddog_openrouter_telemetry_probe.py
```

The combined selection passes63 cases. Boolean admission diagnostics are checked
against hostile Host/Origin text to prevent value echo. Loopback HTTP traffic is distinct
from external API requests; neither Windows custody nor vendor access is
established by these synthetic tests.

The Sentry custody extension expands that same selection to78 cases. It adds
strict shared-DSN validation before vault access, fixed isolated-runtime/probe
selection, child-only injection, Viewer default no-Sentry access, explicit
Viewer/Sentry composition, bad-flag/runtime refusal and the one-field Sentry form.
All vault calls remain fake and all HTTP calls remain local synthetic fixtures.
