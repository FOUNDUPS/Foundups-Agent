# RedDog Lick Connection Handshake

Status: `SPECIFIED_NOT_IMPLEMENTED`

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

RedDog should be able to say, in effect, "Who am I talking with?" and build a
bounded confidence picture from what the participant says, what the current
device can prove, and the modalities the participant has allowed. The result
is a renewable connection assessment, not a permanent assertion that a body is
a particular legal person.

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
3. **Capture an explicit claim.** Ask the participant how they wish to be
   addressed and whether they are claiming an existing profile.
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
| Explicit name/profile claim | Addressing and candidate selection | Required, not proof by itself |
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

## Core records

### `EncounterProfile`

```json
{
  "schema_version": "reddog.lick.encounter-profile.v1",
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
  "schema_version": "reddog.lick.receipt.v1",
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

### PoC that can be tested now

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

## Patent material reuse boundary

`WSP_knowledge/docs/Papers/Patent_Series/04_rESP_Patent_Updated.md` contains
the closest existing invention material:

- claim 26 names heartbeat, gait, and voiceprint as renewable biometric
  triggers;
- claims 29–31 describe a live biometric-harmonic signature embedded in a
  stream and checked for dynamic/non-replayed properties;
- figure 17 illustrates biometric-triggered renewable key generation; and
- figure 19 illustrates a living signature for anti-deepfake verification.

Those passages supply a research and intellectual-property lineage for the
Lick. They do **not** prove that CMST, `det(g)`, a 7.05 Hz resonance, a derived
key, or deepfake detection works. The repository records application number
`71387071`, but a public patent-record search performed on 2026-08-30 did not
locate a matching published application. Filing status and claim scope must be
confirmed with patent counsel before the product says "patented," "patent
pending," or "quantum-resistant."

Potentially new claim material—including recurring multimodal engagement,
progressive encounter profiles, confidence decay, local template custody, and
step-up routing—must be reviewed before enabling details are published. This
product contract intentionally defines boundaries and record shapes without
asserting novelty or legal coverage.

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

## Delivery stages

### Stage 0 — documentation and patent review

- [x] Name and place the Lick as a RedDog product handshake, not a WSP.
- [x] Trace the existing rESP patent claims and anti-deepfake use case.
- [ ] Confirm filing status, ownership, priority date, and claim scope with
  patent counsel before publishing new enabling matter.
- [ ] Complete privacy, threat-model, and jurisdiction review.

### Stage 1 — explicit, non-biometric Lick

- [ ] Implement encounter boundaries, consent receipts, participant claims,
  passkey/device proof, expiry, guest fallback, and `LickReceipt`.
- [ ] Integrate the handshake with RedDog surfaces and the AutoPost capture
  contract.
- [ ] Keep all protected effects behind existing authority systems.

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

The Lick cannot move from `SPECIFIED_NOT_IMPLEMENTED` until tests demonstrate:

1. a new participant receives a provisional profile, never an automatic
   verified-012 designation;
2. an existing participant can decline biometrics and continue as a guest;
3. participant or channel change expires prior confidence;
4. replayed voice/video and static biometric artifacts do not pass a protected
   step-up path;
5. raw samples remain local under the default configuration;
6. deletion removes templates and breaks future matching while preserving only
   the minimum deletion receipt;
7. contradictory modalities remain visible and force step-up;
8. every receipt states `authority_granted: none`; and
9. AutoPost capture and feasibility records remain distinct from identity
   confidence and authority.

## External technical anchors

- [NIST SP 800-63B, Use of Biometrics](https://pages.nist.gov/800-63-4/sp800-63b/authenticators/)
- [NIST SP 800-63A, Identity Proofing Requirements](https://pages.nist.gov/800-63-4/sp800-63a/ial-general/)
- [NIST Speaker Recognition Evaluation Chronicles](https://www.nist.gov/publications/nist-speaker-recognition-evaluation-chronicles)
- [NIST Face Recognition Technology Evaluation](https://www.nist.gov/programs-projects/face-recognition-vendor-test-frvt)
- [Espressif ESP32-S3 Wi-Fi CSI](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-guides/wifi-driver/wifi-vendor-features.html)
