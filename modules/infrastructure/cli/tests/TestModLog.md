# cli TestModLog

## 2026-09-10 — Japanese speech adapter and import boundary

Read README, TestModLog and the existing cue-parsing test before authoring.
Extended `test_openclaw_voice_cue_parsing.py` for Japanese Whisper configuration,
Cohere processor language/chunk metadata and current/legacy decoding, Google
ja-JP locale, and a fresh-process check that speech import does not load main_menu.
The existing cue, barge and normalization cases remain in the same suite.
Combined call-adapter validation is recorded in
[elevenlabs_calls TestModLog](../../../platform_integration/elevenlabs_calls/tests/TestModLog.md).
Physical microphone and model inference were not available; fixtures validate
adapter contracts, not actual recognition quality. No whole-CLI coverage claim.

## 2026-03-18: OpenClaw menu broker-runtime alignment

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest modules/infrastructure/cli/tests/test_openclaw_menu_runtime.py -q`
- Status: PASS
- Notes:
  - Confirms OpenClaw menu option `3` uses the broker-managed `openclaw` runtime when available.
  - Prevents the CLI fallback path from spawning a competing webhook server once resident OpenClaw is registered.
