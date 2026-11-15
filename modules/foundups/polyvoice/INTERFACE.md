# Poly Voice — proposed interface and privacy contract

**Status:** specified only. No executable schema, endpoint or cryptographic protocol is selected.
**Owners:** [README](README.md), [roadmap](ROADMAP.md), [integration index](../voteballots/docs/VOTE_VOICE_INTEGRATION.md).

## Three separate artifacts

| Artifact | Contents | Default boundary |
|---|---|---|
| Private session | Source media/transcript, consent record, local source references, interruption/retention status | Encrypted, device-local; not a feed, log export or remote-agent input |
| Business summary | Human-reviewed business-only JSON, local evidence links, uncertain extraction labels and revisions | Device-local; filtering is not automatic publication or destruction of source |
| Commitment receipt | Minimal versioned commitment to an exact reviewed local revision; any attribution/timing is separately specified | May leave only after explicit approval; contains neither JSON content nor a retrieval link |

Only the commitment receipt is a candidate egress surface. A remote receipt is not permission for a server to fetch the underlying JSON. Do not send local paths, audio references, names, topics, transcript snippets, precise location, biometric data or private key material in the receipt.

## Session lifecycle

Consent/scope review -> explicit start -> visible capture/interruption state -> explicit stop -> qualified local processing -> private business-summary review -> encrypt/retain -> optional receipt approval/submission -> local revision/retention handling.

A calendar event, silence, account sign-in or earlier consent does not automatically start recording. A phone locking, storage filling or a model failing must produce an honest interrupted/unsupported state. No always-on microphone, covert capture or silent remote processing.

Recording consent, storage/retention and any publication approval are separate decisions. Applicable office, jurisdiction, confidentiality, records and security review must precede real meetings. This is a release gate, not a legal clearance or a claim that on-device recording is exempt from those requirements.

## Commitment and evidence semantics

Before implementation, select and independently review canonical serialization, versioning, domain separation, a hiding commitment/randomization strategy, key custody, replay protection and correction rules. Do not invent custom cryptography or treat an ordinary hash of guessable JSON as anonymous. Different JSON serialization must not silently break a valid receipt; changed content needs a new explicit revision.

A bare digest can later help compare a supplied artifact; it does not establish who met whom, that audio is authentic, that a meeting occurred, or that all meetings were recorded. An attributed receipt is at most an authenticated self-attestation under its stated rules. Server receipt time is not automatically capture time.

012's requested 'I met' signal remains the product intent. Under the strict hash-only default, the public cannot infer a named attendee or meeting facts. Publishing an event type, office identity, approximate time or attendee is a **separate opt-in metadata decision** with its own minimization/consent review. No such fields are silently added here. Public JSON export from the older proposal is no longer the baseline.

## Storage and recovery

Qualify actual encryption at rest, platform key protection, unlock/recovery, deletion and retained-source policy. Neither origin-local browser storage nor an object URL is an encrypted archive. Document eviction, device loss, background interruption and OS-backup behavior. No permanent-access guarantee; deletion can make future verification impossible.

Maintain any source-to-summary mapping locally. A reviewer may inspect retained source only through a separately authorized local workflow. Excluding personal material from a business summary must not let an uncertain classifier silently destroy required records. Remote backup, including encrypted backup, requires a later explicit decision; no default cloud copy.

## Reuse and integration

Reuse qualified capture/media primitives from existing owners. Do not forward an AutoPost capture object wholesale or inherit its social upload, share, diagnostic export or cloud paths. Existing camera/local-vision functionality is not evidence of phone-local meeting ASR, diarization or a no-egress pipeline.

Vote may display only an approved public receipt projection with evidence limits; Voice may host a separately authored public endorsement, never a private meeting recording by implication. Poly Vote may reuse qualified identity primitives, but no ballot choice or office entitlement is shared with Poly Voice automatically.

Independent acceptance must cover normal, error, telemetry, crash and offline paths; allowlist receipt egress and reject private-content egress. Unsupported devices fail closed or offer a clearly labeled manual local draft. No production recorder is authorized by this specification.
