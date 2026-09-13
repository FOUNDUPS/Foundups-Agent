# TestModLog — elevenlabs_calls

## 2026-09-10 — offline validation complete; live acceptance pending

- Combined command in README: **91 passed**, Python 3.12.14.
- New `src/` coverage: **100%**, 305 statements / 84 branches; WSP 5 threshold 90%.
- Provider's official `elevenlabs==2.67.0` schema accepts the generated profile
  and expanded defaults. Native API request serialization is covered separately.
- Shared capture→Whisper→CLI→provider path passes with only audio/model/provider
  boundaries replaced. Cohere/Google language and Cohere decoder tests pass.
- Real entrypoint `doctor --json` confirms the three required environment values
  are absent. `provision --dry-run` emits the Japanese profile without network.
- WSP 97 v1.1 repository-evidence validator: structurally complete, compliant,
  no violations. This validates the evidence envelope, not actual phone effects.
- Canonical `generate_test_registry.py --write` / `--check`: current, 1,649 files,
  269 quarantined. Adds this module's two unit-test files, the CLI subprocess
  capability, and three already-tracked eSingularity tests missing from the base
  registry. No eSingularity code was modified or executed by this slice.
- Scoped WSP 49 structure and local documentation links checked; no missing files
  or broken local links. Core `doctor` also runs with Python site packages disabled.
- Prior suite collection exposed missing voice-ingestion batch exports and a
  menu import requiring unrelated dependencies. Fixed both at the owning modules.
- No live provider request, phone call, mailbox playback, audio/model inference,
  microphone test, Japanese quality benchmark or repository-wide coverage claim.

Live acceptance cannot pass until a real account and controlled recipient are
configured. Follow [SETUP.md](../docs/SETUP.md); retain failure results as well as
successful observations when closing the roadmap gates.

## 2026-09-10 — pre-authoring inventory

New external telephone adapter; no existing local tests. Nearest reuse inventory:
`voice_command_ingestion/tests/test_voice_command_ingestion.py` (trigger default),
`test_batch_transcriber.py` (transcript persistence), CLI
`test_openclaw_voice_cue_parsing.py` (voice controls, aliases and barge-in).

Planned `test_calls.py`: request/contact validation, payload and configuration,
duplicate suppression, timeout uncertainty, status truth, HTTP failure handling.
Planned `test_cli.py`: offline preview, one-shot execution, explicit voice trigger,
missing configuration, provisioning and status. Provider/audio fixtures must not
claim live service or microphone validation.
