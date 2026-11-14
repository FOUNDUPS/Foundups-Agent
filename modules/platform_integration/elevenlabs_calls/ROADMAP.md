# Roadmap — prototype first

WSP 15 allocation: **P1 / 15** (complexity 3, importance 4, deferability 4, impact 4).
Phase labels follow 012's requested ordering: working calling prototype first,
then sound-quality proof-of-concept experiments. No MVP work is scheduled.

## Prototype: “make this call and leave this message”

- [x] Audit existing voice input, STT, talk mode and placeholder voice engine.
- [x] Japanese selection through shared Whisper/Cohere/Google adapters.
- [x] Dedicated Japanese ElevenLabs agent provisioning command.
- [x] Exact enabled contact + prepared message request, CLI preview/execution.
- [x] Spoken trigger for the prepared call through existing microphone capture.
- [x] Human-recipient instructions and dynamic voicemail message profile.
- [x] Durable duplicate guard; ambiguous submission never automatically redials.
- [x] Truthful status, offline API-contract and speech-concatenation tests.
- [x] Setup, README, interface, ModLog, test inventory and WSP 97 record.
- [ ] Connect the real ElevenLabs/Twilio accounts and import an outbound-capable number.
- [ ] Accept one live Japanese call answered by the intended test recipient.
- [ ] Accept one voicemail test: complete message after greeting/beep, heard on playback.
- [ ] Measure actual caller ID, latency, duration, Japanese pronunciation and charges.
- [ ] Verify duplicate suppression against the real provider call history.

**Prototype acceptance:** a controlled test recipient confirms the complete spoken
message and a controlled mailbox plays the complete message. Record the live
results in TestModLog; offline coverage cannot close these checkboxes.

## Sound-quality proof-of-concept experiments

- Compare Japanese native voices on the telephone route, not just studio previews.
- Evaluate pronunciation dictionaries for names, addresses and numbers.
- Compare Flash v2.5 against available higher-quality agent voices/models, measuring
  latency and intelligibility through actual telephony bandwidth.
- Compare Cohere and multilingual Whisper on 012's microphone and Japanese speech.
- Evaluate pre-rendered deterministic audio if generated wording varies or voicemail
  timing is unreliable. Keep a single carrier adapter ownership boundary.

## Later integration, only after prototype acceptance

Bind a module-local action to the existing RedDog/WRE execution boundary with
explicit recipient resolution, canonical continuity, AgentDB breadcrumbs and
external-effect authorization. Add a discoverable assistant tool then test the
whole “speak to 0102 → call → report” path. The current ChatGPT session has no
installed phone tool. No independent scheduler, dialer service or shared-memory
authority is proposed. IVR, appointments and autonomous retries remain unplanned.

## Agent execution map

[M2M/Prometheus assignments](work_orders/README.md): 01 baseline → 02 provider setup →
03 live CLI acceptance → 04 request preparation → 05 governed runtime binding →
06 full voice-to-call acceptance → 08 closeout. Order 07 sound POC follows 03 and
is optional for prototype closure. Work-order creation does not complete these gates.

| Work order | Deliverable | Dependency |
|---|---|---|
| [JP-CALL-01](work_orders/01_baseline.json) | Reproduce the existing prototype baseline and identify concrete gaps without rebuilding it. | None |
| [JP-CALL-02](work_orders/02_provider_setup.json) | Make the existing ElevenLabs/Twilio adapter ready for a controlled Japanese call. | JP-CALL-01 |
| [JP-CALL-03](work_orders/03_live_acceptance.json) | Prove that the current prepared-request prototype leaves a complete Japanese message. | JP-CALL-02 |
| [JP-CALL-04](work_orders/04_request_preparation.json) | Turn an English or Japanese instruction into a resolved Japanese call request using existing voice and contact components. | JP-CALL-03 |
| [JP-CALL-05](work_orders/05_runtime_binding.json) | Expose one discoverable phone action through the existing governed RedDog/WRE boundary. | JP-CALL-04 |
| [JP-CALL-06](work_orders/06_end_to_end.json) | Verify the full speak-to-0102, call-in-Japanese, report-result prototype in its actual host. | JP-CALL-05 |
| [JP-CALL-07](work_orders/07_sound_poc.json) | Measure Japanese telephone sound quality after the calling prototype works. | JP-CALL-03 |
| [JP-CALL-08](work_orders/08_closeout.json) | Publish a truthful reproducible prototype handoff and reconcile all agent evidence. | JP-CALL-06 |
