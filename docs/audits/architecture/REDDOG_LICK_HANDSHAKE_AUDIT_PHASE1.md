# RedDog Lick Handshake Audit — Phase 1

Date: 2026-08-30

Base commit: `96d5db5685a015932205bd573b7ea1674b0897cd`

Disposition: `CORRECTED_AND_SPECIFIED_NOT_IMPLEMENTED`

## Question audited

Audit the Gemini-authored `red_dog_lick_feasibility` document, determine the
correct repository placement and product boundary, inspect related RedDog and
rESP patent material, and make the result discoverable.

## Sources read

- Gemini source document:
  `https://docs.google.com/document/d/1xKgKpyQ_lsBGacBoD8GIPIutHp7gVjqEWfEou8Ah7QE/edit`
- `WSP_knowledge/docs/Papers/Patent_Series/04_rESP_Patent_Updated.md`
- `WSP_knowledge/docs/Papers/Patent_Series/01_Foundups_Complete_System.md`
- `docs/REDDOG_OUTCOME_VISION.md`
- `docs/architecture/REDDOG_FOUNDUPS_SECOND_BRAIN_ARCHITECTURE.md`
- `extensions/reddog/README.md`, `INTERFACE.md`, and `ROADMAP.md`
- `modules/foundups/docs/FOUNDUPS_DOMAIN_CANONICAL_INDEX.md`
- the current external `FOUNDUPS/autopost` README and roadmap
- current NIST biometric/identity-proofing guidance and Espressif CSI
  documentation

Canonical HoloIndex owner queries were attempted for RedDog documentation,
AutoPost feasibility, biometric/ZK Lick, and consent/provenance. They returned
`MISSING_GENERATION_BINDING`, `freshness=UNKNOWN`, and
`index_gap_detected=true`; no reindex or mutation was performed. The audit
therefore used direct Git reads and `rg` inventory as the explicit fallback.

## Correct placement

Gemini proposed:

`WSP_knowledge/docs/red_dog/red_dog_lick_feasibility.md`

That placement and title are incorrect.

- The Lick is not knowledge/memory evidence.
- The Lick is not a WSP and must not be placed in `WSP_framework`.
- Feasibility is one consumer, not the handshake's identity.
- RedDog owns the recurring engagement behavior.

Canonical product contract:

`extensions/reddog/docs/REDDOG_LICK_CONNECTION_HANDSHAKE.md`

This evidence audit belongs under `docs/audits/architecture/`.

## Claim verification

| Gemini/patent claim | Finding | Correction |
|---|---|---|
| Commodity Wi-Fi CSI can observe tiny human motion and cardiorespiratory rhythms. | Plausible research result; ESP32-S3 exposes CSI, and experimental literature demonstrates respiration/heart-rate estimation under constrained conditions. | CSI access is not personal identification. Motion, multipath, environment, and multiple people materially affect results. |
| Hampel filtering, one `0.3–2.0 Hz` band, and FFT produce a reliable cardiac signature. | Unsupported as a production identity pipeline. | Respiration and cardiac bands should be evaluated separately; simple filtering/FFT is a baseline experiment, not a biometric contract. |
| Heartbeat, voice, and session timing can be stacked into identity. | Multimodal fusion can improve a measured system, but the proposed stack has no dataset, calibration, false-match rate, attack testing, or threat model. | Treat each as independently evaluated evidence. Heart rate is not a heartprint; conversational cadence is personalization/anomaly evidence, not identity proof. |
| Randomizing/hashing a biometric vector creates anonymous zero-knowledge identity. | False. | Hashing is not encryption, anonymization, or a zero-knowledge proof. Stable noisy biometrics require a defined protected-template/fuzzy-extractor design and security proof. |
| sMPC provides decentralized consensus about identity. | False as stated. | MPC privately computes a specified function. It does not define identity, consensus, liveness, replay defense, parties, thresholds, or authority. |
| RedDog can create a new 012 automatically when it encounters a person. | Unsafe identity conflation. | Create a provisional `EncounterProfile`. A separate enrollment/proofing flow can bind a claimed 012 identity. |
| The rESP patent validates the biometric design. | False. | Claims 26 and 29–31 and figures 17/19 describe related hypotheses; patent text is not technical validation. |
| The system prevents deepfakes. | A meaningful target, not a current fact. | A live randomized challenge, sensor provenance, PAD, replay testing, and independently measured error rates are required. State “research” until verified. |
| Application `71387071` proves current patent protection. | Not externally verified in a public-record search on 2026-08-30. | Patent counsel must confirm the filing receipt, formatted serial number, priority date, ownership, status, and exact claim set before public product claims. |
| RedDog documentation had already been consolidated. | False. | Literal search found 376 Markdown/JSON/YAML files mentioning RedDog; most are receipts, tests, audits, or history rather than canonical product docs. A curated map is required instead of moving all matches. |

## Patent/use-case findings

The repository patent contains the conceptual predecessor the user recalled:

- claim 26: renewable biometric trigger using heartbeat, gait, or voiceprint;
- claims 29–31: a continuous biometric signal transformed into a dynamic
  signature embedded in a live stream and checked for replay;
- figure 17: biometric-triggered renewable key generation; and
- figure 19: “Living Signature” anti-deepfake verification with an
  informational-geometry handshake.

The Lick product concept extends that lineage from a stream signature into a
recurring RedDog encounter handshake. Possible new claim material includes
progressive multimodal profiles, explicit evidence disagreement, confidence
decay, local template custody, per-action step-up, and guest fallback. Because
the repository is public, enabling details beyond the bounded product contract
should be held for counsel review rather than casually committed as a patent
claim draft.

## Architect decision

Implement in stages:

1. First ship an explicit non-biometric Lick: encounter boundary, consent,
   participant claim, passkey/device possession, expiry, guest path, and a
   non-authoritative receipt.
2. Evaluate voice and face only as local, challenge-bound step-up factors with
   liveness/PAD and independently measured error rates.
3. Keep gait, cadence, ECG/PPG, EEG, microvocal tremor, Wi-Fi CSI, CMST,
   `det(g)`, and 7.05 Hz assertions in separately labeled research lanes.
4. Never let a passive biometric grant wallet, publishing, work, or execution
   authority.
5. Use the same Lick before AutoPost-assisted feasibility intake, while keeping
   the encounter receipt, capture event, feasibility judgment, and authority
   records separate.

The cross-repository roadmap half landed through AutoPost PR
[`FOUNDUPS/autopost#10`](https://github.com/FOUNDUPS/autopost/pull/10), squash
commit `05c949c8f59c088754b1841c4417b47d184840f5`. It defines a non-biometric
Phase 1B encounter PoC; it does not implement the adapter.

## Documentation audit disposition

Do not concatenate hundreds of mixed-authority files into one document. That
would erase provenance and make stale evidence look canonical. Preserve source
files and add `docs/REDDOG_DOCUMENTATION_MAP.md` as the human and agent entry
point. The map distinguishes product truth, architecture, public contracts,
protocol authority, audits, test evidence, and historical memory.

## Truth boundary

This phase changes documentation and roadmaps only. It does not implement
biometric collection, create participant profiles, verify a patent filing, or
grant RedDog any new authority. The external AutoPost repository received only
the linked Phase 1B roadmap/ModLog update described above.
