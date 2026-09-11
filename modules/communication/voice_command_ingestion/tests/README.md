# Tests for voice_command_ingestion

This folder holds isolated tests for the voice_command_ingestion module.

- `test_voice_command_ingestion.py`: trigger default, English/Japanese/detection
  propagation to Whisper and factory, English-only model mismatch rejection.
- `test_batch_transcriber.py`: timestamped segments and JSONL persistence.

Run `python -m pytest modules/communication/voice_command_ingestion/tests -q`
from the repository root. Model-boundary fixtures avoid downloading Whisper;
passing tests do not measure Japanese recognition accuracy. The shared phone
integration command is in `platform_integration/elevenlabs_calls/tests/README.md`.
