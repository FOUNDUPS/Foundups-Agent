# Setup and first live test

Run commands from the Foundups-Agent repository root. Core calling needs Python
3.10+ and internet access to `api.elevenlabs.io`; development validation here used
Python 3.12. No always-on local server, public webhook or GPU is required to dial.

## 1. Connect the telephone services

Use an ElevenLabs account with Agents/API access and a funded Twilio account with
Voice access to Japan. In Twilio, check the Japan geographic calling permissions
and trial-account destination restrictions. A service subscription alone does not
prove that a particular outbound route or caller ID works.

For outbound-only use, first investigate verifying an existing number you control
as a Twilio caller ID. ElevenLabs documents support for imported verified caller
IDs as well as purchased Twilio numbers. This does **not** establish that a
particular Japanese mobile number or carrier route is accepted: check account
eligibility and verify it with the controlled test below. If purchasing a Japanese
number, Twilio currently publishes business identity, representative and Japanese
address requirements. Do not assume an individual can instantly obtain a 050
number. [Native integration](https://elevenlabs.io/docs/eleven-agents/phone-numbers/twilio-integration/native-integration),
[Japan number requirements](https://www.twilio.com/en-us/guidelines/jp/regulatory).

In ElevenLabs → Agents → Phone Numbers, import the outbound-capable number using
the Twilio credentials required by its official setup screen. Prefer a dedicated
test number: native import can configure number settings at Twilio. Record its
**ElevenLabs phone-number ID**. This adapter does not need your Twilio secret in
its local environment. Outbound-only verified caller IDs do not require inbound
agent assignment. Complete provider identity checks in their own authenticated UI.

## 2. Create the Japanese agent

Choose a voice in the ElevenLabs voice library and audition Japanese names and
numbers. Supply its voice ID; the profile uses `eleven_flash_v2_5`, Japanese, a
120-second conversation cap, an AI/provider disclosure, and only end-call and
voicemail tools. Voice quality on a telephone must still be auditioned on a call.

Set `ELEVENLABS_API_KEY` through your secret manager or current shell. The CLI
intentionally does not read or print the repository's `.env`. For interactive
PowerShell 7, a masked prompt avoids putting the key in command history:

```powershell
$env:ELEVENLABS_API_KEY = Read-Host 'ElevenLabs API key' -MaskInput
```

Preview the exact profile, then provision it:

```bash
python -m modules.platform_integration.elevenlabs_calls provision --voice-id YOUR_VOICE_ID --dry-run
python -m modules.platform_integration.elevenlabs_calls provision --voice-id YOUR_VOICE_ID --execute
```

Save the returned agent_id as `ELEVENLABS_AGENT_ID`. Set
`ELEVENLABS_PHONE_NUMBER_ID` to the imported phone ID. IDs are configuration, not
API secrets. Example PowerShell:

```powershell
$env:ELEVENLABS_AGENT_ID = 'agent_ID_FROM_PROVISION'
$env:ELEVENLABS_PHONE_NUMBER_ID = 'IMPORTED_PHONE_ID'
python -m modules.platform_integration.elevenlabs_calls doctor --json
```

`configuration_present:true` is only a local check. The first live call performs a
remote agent-profile check before submission. Profile drift blocks dialing; use a
dedicated agent and keep it unchanged during testing. Verify account retention and
recording settings too: the profile requests no stored voice and seven-day
retention, but this is not a zero-data-retention claim.

If provisioning times out, inspect ElevenLabs' agent list before repeating the
command. It may already have created the agent. Provisioning itself makes no call.

## 3. Prepare the recipient and message

Copy the two files in [examples](../examples/) to a private location outside git.
Replace the contact placeholder with a number and recipient you have resolved and
intend to call; then set `enabled:true`. Use `+81` and omit the domestic leading
zero. Do not put secrets or personal contacts into committed example files.

012 tells 0102 whom to call and what to say; 0102 prepares the Japanese text in
`message_ja` and resolves the exact contact. Use the recipient's and sender's
preferred Japanese readings. Keep the first message short. A new intentional call
gets a new request_id; retrying the same call keeps the existing ID.

```bash
python -m modules.platform_integration.elevenlabs_calls call --request /private/call.json --contacts /private/contacts.json --dry-run
```

The preview shows the prepared text and masks the number. Use local paths suitable
for the operating system; the `/private/...` examples are placeholders.

## 4. Make the prototype call

Text-triggered execution works with the standard library:

```bash
python -m modules.platform_integration.elevenlabs_calls call --request /private/call.json --contacts /private/contacts.json --execute
```

To trigger with a microphone, install the optional dependencies into the existing
project virtual environment:

```bash
python -m pip install -r modules/platform_integration/elevenlabs_calls/requirements-speech.txt
python -m modules.platform_integration.elevenlabs_calls call --request /private/call.json --contacts /private/contacts.json --listen --execute
```

Say exactly “make this call” (optional “0102” prefix). It listens once for up to
eight seconds; any other recognized phrase cancels. With `--language ja`, say
「この電話をかけて」. Multilingual Whisper `base` is the default and may download on
first use. A missing microphone/PortAudio installation or model is an error with
no submission; run microphone setup on the actual workstation.

If the repository's local Cohere model is already installed, add `--stt cohere`.
Its existing `resolve_asr_model_path()` configuration and transformers/torch
dependencies remain the source of model selection. Cohere is not automatically
downloaded. Its documented Japanese mode requires an explicit language; this
change passes `ja` to the processor. General `main.py --voice` STT also accepts
`OPENCLAW_VOICE_STT_LANGUAGE=ja`; that does not register telephone actions in the
general REPL or change its desktop TTS voice.

## 5. Check results and close the live acceptance gate

```bash
python -m modules.platform_integration.elevenlabs_calls status --request-id jp-call-001 --json
```

Status polling never redials. For `submission_unknown`, preserve the journal and
look in both provider consoles. A lost response may follow a successful dial.
Never change the ID merely to get around duplicate suppression.

| Controlled test | Pass evidence |
|---|---|
| Human answers | Correct recipient, AI disclosure, complete Japanese message heard, polite ending |
| Recipient declines / wrong recipient | Stops without disclosing the message or making commitments |
| Voicemail | Message begins after the greeting/beep and is complete on mailbox playback |
| Same request repeated | One provider call entry; local response says duplicate_suppressed |
| Japanese sound | Names/numbers intelligible; duration, latency, caller ID and charge recorded |

Use a separate new request_id for each intentionally different live scenario. Log
date, result and non-sensitive evidence in TestModLog. Do not commit recipient
numbers, raw transcripts or recordings. The code's automated tests cannot prove
these live acceptance conditions. Higher quality sound experiments begin after
this prototype passes, as recorded in [ROADMAP.md](../ROADMAP.md).
