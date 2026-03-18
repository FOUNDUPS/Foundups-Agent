# cli TestModLog

## 2026-03-18: OpenClaw menu broker-runtime alignment

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest modules/infrastructure/cli/tests/test_openclaw_menu_runtime.py -q`
- Status: PASS
- Notes:
  - Confirms OpenClaw menu option `3` uses the broker-managed `openclaw` runtime when available.
  - Prevents the CLI fallback path from spawning a competing webhook server once resident OpenClaw is registered.
