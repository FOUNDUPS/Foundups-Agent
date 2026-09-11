# TestModLog - voice_command_ingestion

## 2026-09-10 — Japanese adapter and export regression coverage

Inventory refreshed before extending the existing trigger/default test file.
`test_voice_command_ingestion.py` now checks explicit en/ja/None forwarding into
the actual Whisper call, factory propagation, `.en` mismatch and unchanged default.
`test_batch_transcriber.py` covers segments and JSONL; its previous collection
failure exposed missing root package exports, now repaired. Tests use mocked model
inference, not Japanese audio. Combined validation is recorded in the call
prototype's [TestModLog](../../../platform_integration/elevenlabs_calls/tests/TestModLog.md).

## 2026-01-01
- Initial test scaffolding for voice_command_ingestion.
