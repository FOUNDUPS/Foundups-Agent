# RedDog Lick Connection Handshake

Status: `NON_BIOMETRIC_POC_IMPLEMENTED_NOT_DEPLOYED`; continuous presence, mutual verification, and live-media binding are `SPECIFIED_NOT_IMPLEMENTED`

Evaluated expansion: 2026-09-13 (Asia/Tokyo). See the
[continuous Lick audit](../../../docs/audits/architecture/REDDOG_LICK_CONTINUOUS_VERIFICATION_AUDIT_20260913.md)
for code evidence, corrections to the Gemini proposal, and unresolved risks.

Owner: RedDog product surface

Related systems: FoundUps participant model, AutoPost capture, pfMALL presentation

## Decision

The **Lick** is RedDog's recurring, consent-aware connection handshake. RedDog
uses it when an engagement begins, when the apparent participant changes, and
when a sensitive action needs renewed confidence about who is present.

The Lick is **not a WSP**, is not stored in `WSP_framework`, and does not grant
identity, wallet, work, or execution authority. WSP remains reserved for
governing protocols. This document is a product and integration contract.

Feasibility intake is one consumer of the Lick; it is not the definition of the
Lick.

## Product intent

RedDog should continually ask, in effect, "Is a live participant still present,
is this the same encounter, and does the received material belong to it?"
The default goal is human presence and encounter continuity without discovering
civil identity. A participant can remain pseudonymous. Recognizing the monk as
UnDaoDu additionally requires a previously trusted, consented profile binding;
detecting a human alone cannot establish that name.

The result is a renewable, bounded assessment from permitted evidence. Presence,
same-person continuity, account control, and media provenance are separate
claims. Neither a profile nor a successful challenge proves one unique human
across the ecosystem; Sybil resistance is a separate problem.

On a first encounter, RedDog creates a provisional `EncounterProfile`. It does
not automatically declare the person to be a verified 012. A participant may
later claim or enroll an existing 012 identity through a separate identity
proofing flow. Repeated encounters can strengthen continuity confidence without
silently upgrading identity assurance.

## Handshake sequence

1. **Detect an encounter boundary.** Start when a RedDog surface connects,
   detects a possible speaker change, resumes after expiry, or approaches a
   protected action.
2. **Announce and obtain scoped consent.** Explain which modalities are
   available, why each would be used, retention, and how to continue without
   optional biometrics.
3. **Offer an optional profile claim.** Accept a guest without a name; ask how
   to address the participant only when useful. Existing-profile recognition
   requires a separate, consented binding.
4. **Collect permitted evidence.** Prefer device possession and an explicit
   challenge. Add biometric or behavioral observations only when allowed.
5. **Compare locally where possible.** Raw biometric samples should remain on
   the participant-controlled device. Export a bounded match result and
   provenance receipt, not reusable raw templates.
6. **Fuse confidence without hiding disagreement.** Record each modality's
   score, freshness, quality, and failure reason. Never collapse contradictory
   evidence into an unexplained average.
7. **Select the response.** Continue as guest, associate a provisional profile,
   ask a step-up challenge, bind to an enrolled profile, or refuse only the
   protected action.
8. **Expire and renew.** Confidence decays with time, participant change,
   channel change, or evidence conflict. Every new engagement performs at least
   the light Lick; protected actions require a fresh step-up Lick.

## Evidence ladder

| Modality | Appropriate Lick use | Current posture |
|---|---|---|
| Optional name/profile claim | Addressing and candidate selection | Guest needs no name; a claim is not proof |
| Device passkey or possession proof | Strong account-binding factor | Preferred for protected actions |
| Face with presentation-attack detection | Optional continuity or step-up signal | Supported only after evaluated implementation |
| Voiceprint plus spoken challenge | Optional speaker continuity and liveness signal | Research/evaluation lane |
| Gait/body-motion pattern | Passive continuity hint | Research lane; never sole authenticator |
| Keystroke, touch, mouse, or interaction cadence | Session anomaly and continuity hint | Optional behavioral signal |
| Conversational cadence and language patterns | Personalization and anomaly hint | Never identity proof |
| Heart/respiration dynamics | Liveness/continuity experiment | Experimental; a heart rate is not a heartprint |
| ECG/PPG morphology | Potential wearable-bound biometric | Requires dedicated sensor, evaluation, and consent |
| EEG or microvocal tremor | Patent research hypothesis | Not an implementation claim |
| Wi-Fi CSI | Presence, respiration, or motion research | Default off; not identity proof |

No single passive modality authorizes a protected action. A biometric match is
combined with a possession factor or another authenticated channel when the
result affects access, signing, wallet control, publishing, or work authority.

## Core records (broader design, not the current wire contract)

The examples below describe proposed fields. The implemented `*.v1` payloads
are owned by `reddog_public_policy.py`; they use a different, bounded shape.
Do not send these examples to the existing public endpoints or silently extend
their strict input schemas. Any future transport needs an explicit version.

### `EncounterProfile`

```json
{
  "schema_version": "reddog.lick.encounter-profile.proposed",
  "encounter_profile_id": "ephemeral-pseudonymous-id",
  "display_name_claim": "participant supplied",
  "claimed_012_id": null,
  "identity_state": "guest|provisional|enrolled|verified",
  "created_at": "RFC-3339",
  "last_seen_at": "RFC-3339",
  "allowed_purposes": [],
  "allowed_modalities": [],
  "retention_policy_id": "policy reference",
  "withdrawal_state": "active|withdrawn|deleted"
}
```

### `LickReceipt`

```json
{
  "schema_version": "reddog.lick.receipt.proposed",
  "lick_id": "unique nonce-bound id",
  "encounter_profile_id": "ephemeral-pseudonymous-id",
  "surface": "phone|pfmall|autopost|ide|other",
  "started_at": "RFC-3339",
  "expires_at": "RFC-3339",
  "consent_receipt_id": "scoped receipt",
  "claimed_profile": null,
  "evidence": [
    {
      "modality": "passkey|face|voice|gait|cadence|cardiac|other",
      "purpose": "continuity|liveness|step_up",
      "result": "match|non_match|inconclusive|unavailable",
      "score": null,
      "quality": null,
      "freshness_ms": 0,
      "sensor_provenance": "bounded device attestation reference",
      "raw_sample_exported": false
    }
  ],
  "decision": "guest|provisional|continue|step_up|required_stop",
  "confidence_band": "none|low|medium|high",
  "conflicts": [],
  "authority_granted": "none"
}
```

Scores are implementation-specific and must not be compared across modalities
until calibration data establishes a meaningful mapping. The receipt records
the decision inputs; it is not itself an authenticator or capability token.

## AutoPost and feasibility use

AutoPost is a capture surface, not the identity authority. For a feasibility
conversation it may provide a consented `CaptureEvent` containing media
references, transcript/OCR/percepts, timestamp, hashes, and device/session
provenance. RedDog performs the Lick, separates participant statements from
agent inference, and links the reviewed encounter to a feasibility observation.

The bounded flow is:

`participant -> Lick -> AutoPost CaptureEvent -> RedDog interpretation -> reviewed feasibility observation`

The Lick answers "what confidence do we have about this encounter?" It does
not answer whether a proposal is feasible and does not authorize FoundUp work.

### Stage-1 target behavior and implemented subset

The implemented challenge is a one-use random value returned to the client and
echoed with its bearer. An automated client can complete it. Its receipt states
`identity_verified: false`, `human_presence_proven: false`, `signed: false`,
and `authority_granted: none`. This proves request continuity only. The steps
below include unfinished target behavior; see Delivery stages for their status.

The first PoC deliberately avoids biometric identification. It reuses
AutoPost's existing `CaptureEvent`, local storage/provenance, correction UI,
and real-phone acceptance path:

1. AutoPost displays a plain-language Lick notice before an interview capture.
2. The participant chooses `guest`, supplies a display-name claim, or claims an
   existing profile; biometrics are not requested.
3. AutoPost records the scoped consent, capture ID, media hash, timestamp, and
   device/session provenance in a permissioned event.
4. RedDog creates a provisional `EncounterProfile` and `LickReceipt`, asks one
   randomized spoken or on-screen challenge, and records only completion—not a
   voiceprint.
5. The participant and 012 review/correct the encounter label and feasibility
   observation independently.
6. Ending the capture, changing the participant, or exceeding the expiry starts
   a new Lick. A prior receipt cannot be replayed as current confidence.
7. The participant can withdraw; local media/template deletion is verified and
   the remaining receipt records only that deletion occurred.

PoC success is behavioral and contractual: correct encounter boundaries,
consent, provenance, review, expiry, withdrawal, and guest fallback. It does
not require a CSI board, wearable, face model, voice model, CMST, blockchain,
or identity consensus.

Prototype adds locally evaluated voice/face continuity with randomized
challenge and presentation-attack testing. MVP is gated on independent error,
spoof, demographic, privacy, deletion, and recovery evidence plus a separate
possession/signing factor for protected actions.

## Open-source research lineage

`WSP_knowledge/docs/Papers/Patent_Series/04_rESP_Patent_Updated.md` contains
the closest existing invention material:

- claim 26 names heartbeat, gait, and voiceprint as renewable biometric
  triggers;
- claims 29–31 describe a live biometric-harmonic signature embedded in a
  stream and checked for dynamic/non-replayed properties;
- figure 17 illustrates biometric-triggered renewable key generation; and
- figure 19 illustrates a living signature for anti-deepfake verification.

Those passages supply historical research lineage for the Lick. They do **not**
prove that CMST, `det(g)`, a 7.05 Hz resonance, a derived
key, or deepfake detection works. The repository records application number
`71387071`, but a public patent-record search performed on 2026-08-30 did not
locate a matching published application. The Lick implementation is being
developed as open source and makes no "patented," "patent pending," novelty,
or legal-coverage claim. `71387071` must not be presented as verified protection.

## Privacy and security requirements

- Lick must be visible, purpose-limited, and revocable; covert biometric
  profiling is out of scope.
- Optional biometrics must have a usable non-biometric path.
- Raw voice, face, cardiac, EEG, and gait samples require explicit retention
  and deletion controls. Derived templates are still sensitive biometric data.
- Matching should occur locally or in a trusted execution boundary whenever
  practical; network transport must be authenticated and protected.
- Enrollment, verification, and deletion events require auditable receipts.
- Presentation-attack detection and independent performance testing are
  required before remote biometric identity proofing.
- The system must publish false-match, false-non-match, demographic, sensor,
  environmental, and spoof-testing results for each production modality.
- A disagreement or low-quality capture results in step-up or guest operation,
  not an accusation of impersonation.
- No biometric, conversational, or health-derived evidence enters model
  training without separate explicit consent.

## Continuous Lick and mutual verification (proposed)

### Always checking means renewable evidence

During an explicitly enabled encounter, inspect evidence freshness and binding
on every interaction and each received media segment. Renew permitted local
observations at a bounded, measured cadence; do not run a model, a biometric
challenge, or a remote call on every token. A transport heartbeat proves only
transport activity. It must not refresh a human-presence observation.

Bind observations to a particular speaker/track and time interval. A live
bystander, wearable, or pulse somewhere in the room does not prove the person
shown in the stream is live. Unknown speaker association stays unknown.
Participant change, capture-device/track change, backgrounding, timeout,
contradiction, or consent withdrawal invalidates the affected claims. Renewal
after a gap starts a new epoch; it never retroactively verifies missing media.

Show when sensing is active and allow pause/withdrawal. Silence, camera-off,
poor connectivity, disability, atypical cadence, and assistive translation are
not evidence of deception. Offer an accessible step-up or ordinary guest use.
An unattended but authorized agent may continue delegated work while its
human-presence state is explicitly unknown or expired.

### Separate claims before choosing an action

| Claim | Evidence required for a future supported assessment | Does not establish |
|---|---|---|
| Human presence | Fresh, evaluated liveness evidence bound to the relevant capture path and participant | Name, uniqueness, intentions, or authority |
| Participant continuity | Consented comparison against a prior observation with quality, conflict, and expiry records | Civil identity or continuous observation during gaps |
| Account/key control | Valid possession proof with a trusted enrollment or delegation binding | The signer is the person in the video |
| Media provenance | Valid segment binding, accepted signer, freshness, and declared capture/transformation chain | Physical truth before the signing boundary |
| Action authority | Existing principal/project/disclosure capability and action-specific approval rules | Blanket permission from any of the above claims |

Each assessment records method/version, evidence issuer, subject/track scope,
observed time, expiry, outcome, quality, failure reasons, and consent scope.
Use `supported`, `unknown`, `conflicting`, `expired`, or `withdrawn`; a supported
claim is bounded by its method and threat model. Optional numeric scores need
calibration. Do not average these claims into one identity/trust score, and do
not equate agent semantic state with a probability of human presence.

### Two Red Dogs close the encounter loop

1. Each side obtains consent locally and establishes an ephemeral encounter
   key through a reviewed authentication/delegation flow. WebAuthn/passkeys
   can authenticate to a relying party; they are not arbitrary per-frame
   signing keys. Session-key delegation is a separate, bounded contract.
2. Establish peer trust from an existing trusted binding or explicit pairing.
   An unfamiliar self-signed key remains an unrecognized peer. Trust in an
   evidence issuer must state which capture/liveness methods it can attest.
3. Exchange fresh unpredictable challenges over authenticated channels. Bind
   signed responses to both challenges, both peer keys and roles, encounter
   ID, epoch, channel binding, purpose, policy version, and expiry. Each side
   verifies the other independently; circular endorsement creates no evidence.
4. Exchange only scoped assessments and necessary proof references. Each
   receiver applies its own policy; the other RedDog's assertion cannot set
   local authority or silently raise assurance. No raw biometric templates or
   global human fingerprint are required in the exchange. Treat received
   content and assertions as data, never as instructions to the verifier.
5. Bind media segments to that encounter and return a signed acknowledgement
   of the transcript/segment evidence actually checked. This acknowledges
   receipt and verification scope, not truth, endorsement, or authorization.
6. Reject stale, replayed, wrong-peer, wrong-channel, wrong-purpose, or revoked
   proofs. On loss of freshness, remove the affected assurance indicator and
   hold only actions requiring it. Ordinary unverified communication can remain.

Use reviewed cryptographic libraries and a specified canonical encoding,
domain separation, algorithm allowlist, key rotation/revocation, and recovery
procedure before implementation. This is a requirements sequence, not a new
cryptographic protocol specification. Account recovery cannot restore prior
human-continuity assurance without fresh evidence.

### Bind the stream, not merely its login

Reuse and evaluate AutoPost's existing
[`foundupsAuthorIdentity.ts`](https://github.com/FOUNDUPS/autopost/blob/4b9e2fd8958f54e5b4c0c36e690d781ac1e8f147/src/modules/identity/foundupsAuthorIdentity.ts)
first: it already signs an original-media fingerprint in `foundups.media.v1`.
Its verifier checks a manifest against the public key carried in that manifest;
it does not itself compare received media bytes, establish external signer
trust, or verify a live encounter. The stored key is non-extractable after
import, but generation temporarily exports private JWK material; hardware
capture attestation must not be inferred. Do not create a second author-identity
store. Review the stable author ID's linkability before adding pairwise use.

The receiver must verify the bytes it presents. The proposed media evidence
binds stream/encounter ID, epoch, track ID, segment sequence, capture interval,
content hash, continuity link, signer/delegation, and current assessment
reference. Validate freshness against a bounded clock-skew and latency policy;
a timestamp or reusable video overlay is insufficient.

Evaluate the existing C2PA live-video specification as the provenance carrier
before inventing a format. C2PA provenance alone does not prove human liveness.
A transcoder, editor, or AI voice translator must declare its transformation
and bind output to input; exact content hashes do not survive transcoding.
If a platform strips provenance, display provenance unavailable. A sidecar is
usable only if it is authenticated and binds the actual rendered rendition.

For the monk's livestream, his RedDog may maintain local presence/continuity
evidence while signing the bound capture stream. A viewer's RedDog validates
that stream and, if already paired, recognizes the established UnDaoDu profile.
It can independently check the viewer locally. Mutual replies require both
directions' encounter checks; passive viewing does not require revealing a
viewer's identity or liveness to the broadcaster. Broadcast verification should
reuse source segment proofs rather than demand a fresh challenge per viewer.

Render assurance in the receiver's trusted application chrome, never as a
badge burned into video. Distinguish source provenance, recent human-presence
evidence, known-profile continuity, transformed media, and unavailable evidence.
An authorized synthetic/translated voice is labeled as such and is not passed
off as an unmodified live human voice.

### Security claim and residual risks

The target is to prevent invalidly bound or replayed media from being accepted
as verified within conforming clients under a stated trust model. It does not
make deepfake creation impossible. A real human can operate a deepfake; a
compromised capture application can sign fabricated frames; two compromised
RedDogs can exchange mutually consistent lies. Secure signing protects bytes
after its trust boundary and cannot repair fabricated input before it.

Evaluate presentation attacks, virtual-camera/audio injection, real-time
relays, person/track substitution, key theft, colluding endpoints, and false
issuer attestations. Define the trusted capture boundary and its attestation
limits before advertising human assurance. Even measured liveness/PAD has
residual errors. Absence of valid provenance means unverified, not fake.

### Affect palette, Un-Dao-Du, and WSP authority

The palette may present uncertain, consented interaction cues to help RedDog
adjust pace, wording, clarification, and attention. It is not a biometric,
deception detector, or moral score. Anger must not reject a person's handshake;
polite language must not authorize a harmful action. Keep affect optional,
correctable, local where possible, and outside peer identity attestations.

An evaluated design interpretation of Un-Dao-Du is: Un respects consent and
non-imposition; Dao clarifies the participant's intended constructive outcome;
Du checks concrete consequences and restraint before protected effects.
These are design principles, not claims that a sentiment vector measures them.
Suspected coercion may prompt a private check or hold a sensitive transaction;
it cannot be established from tone alone.

Lick supplies bounded encounter evidence to 3V Verification. Validation and
Valuation remain separate. WSP 44's implemented `SemanticStateEngine` uses
three named axes, ten valid codes with `A <= B <= C`, and optional constrained
transitions; it is not a capability token or compulsory authorization ladder.
WSP 73 and the conversation policy keep intent, reasoning depth, and effect
ceiling independent. A `222` code, high confidence, friendly color, or signed
Lick receipt never grants private 0102 access or worker-dispatch authority.

### Prototype gates for this expansion

Follow the [bounded roadmap](../ROADMAP.md#continuous-lick-design-and-evaluation).
First demonstrate mutual request/stream continuity with synthetic media and
human presence explicitly unknown. Add human-assurance claims only after
capture-path and liveness evaluation. Report attack acceptance and legitimate
rejection rates with denominators, uncertainty, device/environment conditions,
and independent held-out attacks. Measure detection delay, latency, battery,
compute/network cost, and accessibility burden. Predeclare acceptance thresholds
for the intended use; zero successes in a small attack sample is not impossibility.

Required negative cases include replay, reordered/missing/cross-stream segments,
reconnect/clock rollback, downgrade to unsigned media, sensor loss, consent
withdrawal, account recovery, synthetic-source disclosure, and action-authority
invariance under affect/state changes. No production capability is enabled by
this documentation update.

## Delivery stages

### Stage 0 — documentation and research review

- [x] Name and place the Lick as a RedDog product handshake, not a WSP.
- [x] Trace the existing rESP patent claims and anti-deepfake use case.
- [x] Record that the Lick lane is open source and makes no patent-status claim.
- [x] Audit continuous presence, mutual verification, media binding, affect,
  and semantic-state claims; specify boundaries without claiming implementation.
- [ ] Complete privacy, threat-model, and jurisdiction review.

### Stage 1 — explicit, non-biometric Lick

- [x] Implement explicit session consent, guest/display-name claims, a
  randomized one-use continuity challenge, provisional `EncounterProfile`,
  expiry, withdrawal, and non-authoritative `LickReceipt` at the isolated
  RedDog public boundary.
- [x] Add the AutoPost consent/guest UI, memory-only client, and bounded capture
  provenance adapter.
- [x] Keep all protected effects behind existing authority systems; the receipt
  always says `authority_granted: none`.
- [ ] Add possession-bound existing-profile proof, participant/channel-change
  detection, independent label correction, and deletion-tombstone UI.

### Stage 2 — evaluated voice/face step-up

- [ ] Add local template custody, randomized challenge, liveness/PAD, modality
  quality, conflict handling, deletion, and independent test harnesses.
- [ ] Calibrate confidence bands against measured false-match and
  false-non-match rates. Never infer them from model confidence alone.

### Stage 3 — research modalities

- [ ] Evaluate gait, interaction cadence, ECG/PPG, and Wi-Fi CSI independently.
- [ ] Treat heart/respiration and CSI as research observations until repeated
  studies demonstrate person-specific discrimination and replay resistance in
  the intended environment.
- [ ] Evaluate the patent's living-signature assertions separately from the
  production identity path.

## Acceptance gates

The broader Lick cannot move beyond the non-biometric PoC until tests demonstrate:

1. a new participant receives a provisional profile, never an automatic
   verified-012 designation;
2. an existing participant can decline biometrics and continue as a guest;
3. participant or channel change expires prior confidence;
4. replayed voice/video and static biometric artifacts do not pass a future
   protected step-up path;
5. raw samples remain local under the default configuration;
6. deletion removes templates and breaks future matching while preserving only
   the minimum deletion receipt;
7. contradictory modalities remain visible and force step-up;
8. every receipt states `authority_granted: none`; and
9. AutoPost capture and feasibility records remain distinct from identity
   confidence and authority.

## External technical anchors

- [C2PA 2.4 technical specification, live video and trust model](https://spec.c2pa.org/specifications/specifications/2.4/specs/C2PA_Specification.html)
- [W3C WebAuthn Level 3, presence, verification, and relying-party binding](https://www.w3.org/TR/webauthn-3/)
- [NIST SP 800-63B, Use of Biometrics](https://pages.nist.gov/800-63-4/sp800-63b/authenticators/)
- [NIST SP 800-63A, Identity Proofing Requirements](https://pages.nist.gov/800-63-4/sp800-63a/ial-general/)
- [NIST Speaker Recognition Evaluation Chronicles](https://www.nist.gov/publications/nist-speaker-recognition-evaluation-chronicles)
- [NIST Face Recognition Technology Evaluation](https://www.nist.gov/programs-projects/face-recognition-vendor-test-frvt)
- [Espressif ESP32-S3 Wi-Fi CSI](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-guides/wifi-driver/wifi-vendor-features.html)
