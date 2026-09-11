# Voice/telephone audit and decision — 2026-09-10

## Existing Foundups components

| Component | Evidence and reuse decision |
|---|---|
| `modules/infrastructure/cli/src/openclaw_voice.py` | Existing sounddevice microphone capture; local Cohere → Whisper → Google recognition chain. Reuse capture and explicit STT adapters. Desktop TTS is Edge/pyttsx3/print. |
| `modules/communication/voice_command_ingestion` | Real faster-whisper implementation, trigger extraction and batch transcripts. Fixed hardcoded English for configurable language in the real-time adapter. |
| `modules/communication/voice_engine` | Placeholder implementations; not a working telephone or high-quality speech service. |
| `modules/communication/moltbot_bridge/docs/CHANNEL_SETUP.md` | ElevenLabs talk-mode configuration, not a native outbound telephone implementation. |

The Cohere Transcribe 2B model supports Japanese with an explicit language code;
automatic language detection is not its advertised contract. Keep it for input
where installed. A natural Japanese speaking voice is a separate TTS requirement.
[Official model card](https://huggingface.co/CohereLabs/cohere-transcribe-03-2026).

Search covered checked-out communication/CLI/shared-model modules and repository
path inventory. Holo owner query had no current freshness receipt. A broader
partial-clone `git grep` could not finish its network blob retrieval; this is not
a claim that every repository blob was exhaustively scanned. See the precise
limitations in [WSP97_EXECUTION.md](WSP97_EXECUTION.md).

## Current open-source and hosted options

| Option | Fit for this prototype |
|---|---|
| [OpenClaw voice-call plugin](https://docs.openclaw.ai/plugins/voice-call), [GitHub](https://github.com/openclaw/openclaw/tree/main/extensions/voice-call) | Supports notifications and conversation through Twilio/Telnyx/Plivo, with a mock provider. Requires a configured gateway and public webhook. Useful if that runtime is already the chosen phone host. |
| [Hermes optional telephony](https://github.com/NousResearch/hermes-agent/tree/main/optional-skills/productivity/telephony) | Existing optional telephony integration is an architectural reference. A second whole agent runtime is unnecessary for this bounded Foundups adapter. |
| [ElevenLabs Python SDK](https://github.com/elevenlabs/elevenlabs-python) + hosted Agents | SDK/source is available; speech/agent hosting and carrier service remain paid external services. Native Twilio outbound API avoids hosting our own media webhook. Chosen integration. |
| [Twilio answering-machine detection](https://www.twilio.com/docs/voice/answering-machine-detection) | Direct playback is attractive for a fixed recording. Handling human versus mailbox timing and callbacks would add an owned server path. Deferred alternative if deterministic playback becomes necessary. |

Our decision is architectural judgment, not a comparative Japanese audio benchmark.
No external telephony skill was installed and no third-party agent code was copied.
The new adapter's runtime uses standard-library HTTP; the SDK is a development
dependency for validating the provider's typed profile contract.

## Chosen API and Japanese behavior

Provision through [Create agent](https://elevenlabs.io/docs/api-reference/agents/create),
submit via [Twilio outbound call](https://elevenlabs.io/docs/api-reference/twilio/outbound-call),
and inspect [Conversation details](https://elevenlabs.io/docs/api-reference/conversations/get).
The request uses three dynamic variables: sender, recipient and prepared Japanese
message. No per-call prompt override is required.

The [voicemail tool](https://elevenlabs.io/docs/eleven-agents/customization/tools/system-tools/voicemail-detection)
can use a dynamic message and terminate afterward. Its detection is model based,
so real greeting/beep timing remains an acceptance test. The profile uses a
Japanese-capable Flash v2.5 voice; compare alternatives against the current
[model catalog](https://elevenlabs.io/docs/overview/models) during sound experiments.
AI and service-processing disclosure is included, consistent with
[ElevenLabs disclosure requirements](https://elevenlabs.io/docs/eleven-agents/legal/disclosure-requirement).

## Japan deployment constraint

The main external dependency is an eligible caller identity and enabled Japan
route. The [native integration](https://elevenlabs.io/docs/eleven-agents/phone-numbers/twilio-integration/native-integration)
supports purchased numbers and verified caller IDs generally; Japanese carrier
acceptance for 012's account has not been established. Twilio's
[Japanese number guidelines](https://www.twilio.com/en-us/guidelines/jp/regulatory)
publish business documentation/address requirements for local and national
numbers. Prefer testing an existing eligible outbound identity before buying a
new number. Do not promise instant individual 050 provisioning or caller-ID display.

Costs have separate agent, model and telephone components. Check the actual
account quotes and record charges during the short controlled call; this build
does not purchase a plan or assume a country-independent per-minute rate.
