# Secrets owner test history

## 2026-11-02 — Explicit Sentry custody routes

78 synthetic cases pass across provisioning/vault/probe suites. New cases cover
the fixed Sentry target, shared DSN validator, single-field form, no arbitrary
runtime/argv, explicit Viewer-only error flag and no Sentry read/inheritance by
default. Existing expiry/no-echo/framing tests remain included. Real Windows
storage and remote event arrival are parent-owned live checks, not these tests.
The independent expired-socket test initially saw Win10053 rather than404;
both now satisfy fail-closed no-store behavior with a mandatory thread join.

## 2026-11-02 — Bounded browser provisioning transport

63 combined offline cases pass across one-use provisioning, fixed-target vault
adapter and synthetic OpenRouter probe. New raw-HTTP cases reject duplicate
Host/Origin/Content-Length/Content-Type and a5,000-digit content length. A real
Windows incomplete-body test exposed five-second shutdown delay; reduced socket
timeout and an expiry margin resolve it. Tests cover static admission/framing/
encoding/shape/storage diagnostics without submitted values or exception text.
An actual adapter import is exercised with invalid inputs before vault access.
No real key, CredRead/CredWrite or external API call occurs in this selection.
Additional hostile Host/Origin cases verify boolean-only admission diagnostics
without header values or the nonce. Origin policy remains unchanged.
The form header regression now requires `Referrer-Policy: same-origin`:
`no-referrer` made the actual browser's POST Origin null and caused admission
failure. The fix preserves the exact Origin allowlist rather than admitting null.

## 2026-11-01 — Windows telemetry pilot

32 offline cases pass across `test_windows_pilot_credentials.py` and the fixed
synthetic OpenRouter probe suite. The initial oversized automatic parameter ID
caused two setup errors, corrected with explicit short IDs. Pytest warned about
two inherited asyncio config options with plugin autoload disabled. No live
credential or vendor connectivity verification was performed by these tests.
Independent review identified a secret-shaped remote model that passed slug
grammar; model output is omitted entirely and a hostile-provider case now covers it.
