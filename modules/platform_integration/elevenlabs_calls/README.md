# Japanese message-call prototype

Prepare a recipient and a short Japanese message, say **“make this call”**, and
submit one telephone call through ElevenLabs Agents + Twilio. The agent identifies
itself as AI, asks for the named recipient, or uses its voicemail tool to leave the
prepared message. This is a locally invoked prototype, with live acceptance pending.

The adapter is implemented and tested offline. No provider account, phone line,
microphone or live Japanese call was available in the build environment. It is not
yet registered as a callable tool in ChatGPT or the RedDog/WRE runtime.

## Start here

- [Setup and first call](docs/SETUP.md): accounts, requirements, voice, commands,
  Japan routing and first live test.
- [Interface](INTERFACE.md): JSON request and receipt contracts.
- [Roadmap](ROADMAP.md): prototype acceptance, then sound-quality experiments.
- [Research](docs/RESEARCH.md): existing repository capabilities and alternatives.
- [WSP 97 execution record](docs/WSP97_EXECUTION.md) and
  [machine receipt](docs/wsp97_execution_receipt.json).
- [Tests](tests/README.md), [TestModLog](tests/TestModLog.md), [ModLog](ModLog.md),
  [local state](memory/README.md).

## Usage from repository root

```bash
python -m modules.platform_integration.elevenlabs_calls doctor --json
python -m modules.platform_integration.elevenlabs_calls call --request /private/call.json --contacts /private/contacts.json --dry-run
python -m modules.platform_integration.elevenlabs_calls call --request /private/call.json --contacts /private/contacts.json --listen --execute
python -m modules.platform_integration.elevenlabs_calls status --request-id jp-call-001 --json
```

The first two commands do not dial. A call requires `--execute`, an enabled exact
contact, prepared Japanese text and provider configuration. `--listen` arms one
microphone capture for that prepared request; it does not interpret arbitrary
spoken names or translate the message. An assistant can prepare the JSON from
012's instruction, then invoke this same CLI under the local operator boundary.

Core calling uses Python's standard library. Optional microphone input reuses
`infrastructure/cli` capture and its Whisper/Cohere adapters. The telephone agent
uses hosted ElevenLabs speech; it does not stream local headset output into Twilio.

## Outcome and retry contract

`submitted` means the provider accepted the call request. `ended` means its
conversation finished. **Delivery remains `unconfirmed`** until the recipient or
test mailbox verifies the full message. Detection, synthesized speech and telephone
audio quality require real-world testing.

Each request_id is reserved transactionally before dialing. Repeating it in the
same journal never submits a second call, including after timeouts or interruption.
For `submission_unknown`, inspect both provider consoles before deliberately
creating a new request. Preserve the journal across runs and machines; separate
journals do not share duplicate protection. No automatic retries or batch dialing.

## Scope

Japan `+81` destinations, short messages (500 characters maximum), a two-minute
conversation cap, and no extra agent tools. The generated profile disables audio
recording and requests seven-day platform retention. Provider processing and
carrier records still exist. A remote profile check runs before every submission.
Keep the dedicated agent unchanged during a test campaign.

Free-form contact resolution, IVR navigation, transfer, scheduling and autonomous
runtime promotion are outside this prototype. See the roadmap for the explicit
integration gates; there is no new parallel orchestration service here.

## Agent build work orders

See the [M2M/Prometheus work-order pack](work_orders/README.md) for eight dependency-ordered
assignments covering provider setup, live acceptance, request preparation, governed
runtime integration, end-to-end verification, sound experiments and handoff.
