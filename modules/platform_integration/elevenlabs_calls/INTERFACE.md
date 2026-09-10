# Interface — elevenlabs_calls 0.1.0

Entrypoint: `python -m modules.platform_integration.elevenlabs_calls`.
All results use `{success, status, data, error}` JSON on stdout. Microphone prompts
use stderr. Exit 0: completed CLI operation; 1: configuration/provider failure,
interruption or unsuccessful submission; 2: argument-parser usage error. A
successful CLI invocation does not assert message delivery.

| Command | Inputs | Effect |
|---|---|---|
| `doctor` | `--json` | Reports environment presence only; no connection test |
| `provision` | `--voice-id ID`, optional `--execute` | Preview profile; explicit execute creates an agent |
| `call` | `--request FILE --contacts FILE`, optional `--execute --listen --language en/ja --stt whisper/cohere --journal FILE` | Preview by default; one call on explicit execution |
| `status` | `--request-id ID`, optional `--journal FILE` | Read local receipt, refresh provider conversation if known |

`--json` is accepted on every subcommand; JSON output is always enabled.
`--dry-run` is accepted by provision/call and mutually exclusive with `--execute`.
Provision does not import a phone number or place a call. It is not automatically
retried: after a provisioning timeout inspect the agent list before repeating.

## Request

See [request.example.json](examples/request.example.json) and
[contacts.example.json](examples/contacts.example.json). Requests contain exactly:

- `request_id`: stable 8–80 character ASCII ID, starting with a letter or digit;
  remaining characters letters, digits, dot, underscore or dash.
- `contact_id`: exact lookup key, maximum 80 characters; no fuzzy matching.
- `sender_name_ja`: spoken sender name, 1–60 characters.
- `message_ja`: prepared Japanese, 1–500 characters; no live translation.

Contact records supply `phone_number` (Japan E.164), `recipient_name_ja` (1–60
characters) and `enabled:true`. Files are JSON objects capped at 64 KiB. The schema
rejects control characters and dynamic-variable template delimiters in text.
Examples are disabled and must be replaced with the intended test recipient.

## Receipt

Local call records contain request_id, status, delivery (`unconfirmed`), nullable
conversation_id and call_sid. Retries return `duplicate_suppressed:true`.
The state transitions are:

- Reserved before POST → `submission_unknown`.
- Explicit provider acceptance → `submitted`; explicit rejection → `rejected`.
- Status polling → `in_progress`, `ended` or `failed`; an unknown provider state
  does not manufacture a terminal result.

An interrupted process can leave the original reservation. A changed request,
contact destination, agent ID or phone ID under the same request_id is rejected.
The journal stores a fingerprint and metadata, not phone numbers or message text.
Preview intentionally displays the prepared message and masks the phone number.

## Provider API

HTTPS, `xi-api-key` authentication, 30-second request timeout, no redirect follow,
no POST retry. Provider error bodies are not printed. Calls use documented native
Twilio outbound API dynamic variables, not prompt or first-message overrides.
See [research/API references](docs/RESEARCH.md).

Configuration:
`ELEVENLABS_API_KEY`, `ELEVENLABS_AGENT_ID`, `ELEVENLABS_PHONE_NUMBER_ID`.
The phone ID is ElevenLabs' imported-number ID, not a Twilio SID or phone string.
`FOUNDUPS_CALL_JOURNAL` optionally overrides the default local state path.

## Internal boundary

`CallRequest.resolve(job, contacts)` freezes resolved intent;
`MessageCaller.submit(request)` validates the remote profile and guards submission;
`MessageCaller.status(request_id)` refreshes status without redialing.
`listen_once()` reuses owned CLI microphone/STT adapters. It has no daemon, network
ingress, public chat hook or new agent memory authority. WRE promotion requires
the canonical contracts listed in [WSP97_EXECUTION.md](docs/WSP97_EXECUTION.md).
