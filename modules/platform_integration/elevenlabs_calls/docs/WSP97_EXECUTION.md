# Japanese message-call prototype — WSP 97 execution record

## Pre-implementation allocation (2026-09-10)

Base: `78b79c36c2d776e030cd0ee8aa23359a67f952ec`.
Requested by 012: implement and test a spoken instruction → Japanese phone
message prototype; document setup, roadmap and ModLog. No MVP expansion.

WSP 15: complexity 3 (external effect, ambiguous network failures), importance 4
(missing requested capability), deferability 4 (current requested build), impact 4
(real telephone reach). Total **15 / P1**. LLME current 000; target prototype 111,
conditional on live telephone acceptance. Implement the single-call adapter and
reuse existing microphone/STT first; defer autonomous routing and quality tuning.

## Retrieval and research

- Root AGENTS, WSP_CORE, WSP master index and canonical WSP 00, 03, 05, 06,
  15, 22, 34, 49, 97, 105 consulted. No protocol changes proposed.
- WSP 00 bootstrap script failed because `torch` is unavailable. The documented
  torch-free tracker fallback (`--awaken`, then `--check --json`) passed the
  software gate. Detector witness is **ABSENT**, not a measured physical result.
- Canonical `scripts/reddog_holoindex_owner_query_once.py` query for Japanese
  outbound message telephony returned `ok:false`, `MISSING_GENERATION_BINDING`,
  `freshness:UNKNOWN`, `index_gap_detected:true`, `missing_freshness_receipt`.
  No reindex performed. This is lexical fallback evidence, not valid Holo evidence.
- Code inspected: `communication/voice_command_ingestion` local Whisper adapter
  and tests; `infrastructure/cli/src/openclaw_voice.py` microphone and Cohere,
  Whisper, Google STT chain; `communication/voice_engine` placeholders;
  `communication/moltbot_bridge/docs/CHANNEL_SETUP.md` ElevenLabs talk mode.
- Existing Whisper forces English. Cohere processor lacks explicit language.
  Reuse and repair those adapters. Talk mode is not a telephone transport.
- Provider research and alternatives: [RESEARCH.md](RESEARCH.md).

## Micro pass / first principles

Minimum effect: one explicit operator request, one resolved contact, one bounded
Japanese message, one provider POST, then truthful status. ElevenLabs Agents
native Twilio integration supplies phone audio and voicemail detection without a
new public server. Standard-library HTTPS and SQLite suffice for the adapter.
Keep local speech optional; text invocation must work without an ASR download.

## Macro pass / execution plane / concatenation

Primary purpose is external API integration: `platform_integration/elevenlabs_calls`.
This is a **local operator CLI adapter**, not a daemon or a new orchestration plane.
Ingress is a prepared request file; request_id is local continuity and retry key.
Local SQLite is an external-effect duplicate guard, not shared agent memory.
The local invoking operator owns errors and reconciliation. It has no scheduler,
no autonomous retries, no public ingress, and no LLM-accessible extra tools.
WRE execution is not applicable to this local slice. Promotion into RedDog/WRE
requires canonical continuity, AgentDB breadcrumbs, routed-effect authorization
and supervision evidence per MODULE_CONCATENATION_GATE. Do not connect arbitrary
livechat to this dialer. Its offline concatenation test uses the actual CLI and
shared speech adapter with the provider boundary replaced.

## Hard-think decisions / dialectic sweep

- A timeout can follow an accepted call: reserve request_id before POST and never
  retry automatically; ambiguous outcomes require provider-console reconciliation.
- API `success` means submission, and conversation `done` means ended; neither
  proves that a recipient heard the message. Expose delivery as unconfirmed.
- Voicemail detection and generated speech are probabilistic. The live gate must
  check greeting/beep timing, complete playback, pronunciation and human reception.
- A standalone Twilio Say call is simpler for playback, but conversation/voicemail
  branching would need additional hosting. A full OpenClaw/Hermes install would
  duplicate existing agent infrastructure. Keep ElevenLabs as the external adapter.
- Explicit Japanese copy avoids unreviewed translation during a live call. The
  caller identifies itself as AI and gives provider-processing disclosure.
- No credentials present in this execution environment; no live dial or provider
  provisioning can be claimed from offline tests.

## Test inventory gate (before authoring)

Read `voice_command_ingestion/tests/{README,TestModLog}.md`, its trigger/default
test and batch-transcriber tests; read CLI tests README/TestModLog and existing
`test_openclaw_voice_cue_parsing.py`. Extend those files for language propagation.
No existing ElevenLabs outbound adapter test suite in the inspected module scopes.
New test surface is recorded in this module's tests/TestModLog before authoring.

## Execution and validation

Implementation complete: local API adapter, prepared contact/message, optional
microphone trigger, Japanese shared STT repair, duplicate journal and truthful
status. Test-driven discovery repaired missing batch exports and eager CLI menu
imports. Current Cohere processor requires language and uses `decode`; inspected
the official transformers 5.17.0 wheel, then preserved legacy decoder compatibility.

Combined validation: **91 tests passed**, new adapter **100% statement/branch
coverage** (305 statements, 84 branches). This is scoped validation, not a full
repository WSP 6 audit. Test commands/results are attached in
[tests/README.md](../tests/README.md) and [TestModLog](../tests/TestModLog.md).
Provider profile also parses through ElevenLabs SDK 2.67.0 without a network call.

The v1.1 repository-evidence validator reports `is_compliant:true`, structurally
complete, no violations, with the declared base commit. It proves only receipt
structure and repository-bound WSP retrieval; other evidence and runtime effects
are not authenticated by that validator.

The execution receipt intentionally marks outcome **blocked** for live prototype
acceptance: required service credentials are absent. Agent provisioning and live
call/voicemail/microphone acceptance have not occurred. The implemented CLI and
runbook are ready for that last environment-dependent test. No higher-level runtime
telephone authority was added. A broad partial-clone `git grep` could not complete
network blob retrieval; lexical search conclusions are limited to inspected scopes.
