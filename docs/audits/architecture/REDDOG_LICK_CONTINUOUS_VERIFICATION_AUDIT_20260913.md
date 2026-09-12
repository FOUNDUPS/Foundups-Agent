# RedDog continuous Lick: audit and evaluation

Date: 2026-09-13 (Asia/Tokyo; 2026-09-12 UTC)

Baseline: `FOUNDUPS/Foundups-Agent@08d005635f25aeae2606473c960fd803bd784157`

Disposition: `AUDITED_AND_SPECIFIED_NOT_IMPLEMENTED`

Canonical [Lick contract](../../../extensions/reddog/docs/REDDOG_LICK_CONNECTION_HANDSHAKE.md)
and [roadmap](../../../extensions/reddog/ROADMAP.md#continuous-lick-design-and-evaluation).

## Decision

012's continuous Lick is a useful integration hypothesis: renew consented,
local evidence of a participant's presence and continuity, then let receiving
RedDogs check that evidence against the actual encounter and media they receive.
Civil identity discovery is unnecessary for the default experience. Established
profile recognition, such as UnDaoDu, requires a separate trusted binding.

Proceed with small evidence/stream experiments. Do not promote the proposal to
an implemented biometric authenticator, a universal proof of personhood, or a
claim that deepfakes are impossible. The hardest unresolved problem is binding
the observed live human to the exact capture path and delivered media. Mutual
software signatures cannot supply missing physical evidence.

The main improvement over Gemini's synthesis is separating presence, continuity,
account/key control, media provenance, affect, and effect authority. These can
inform one another without becoming interchangeable proofs.

## Scope and retrieval

- Closed groundwork: the merged non-biometric Lick, public admission code,
  AutoPost client, existing author-media signing module, and WSP 73 boundary.
- Open target: continuous participant evidence and mutually verified live-media
  binding, with an explicit threat model and measurable assurance limits.
- Chosen slice: audit and canonical documentation/roadmap update.
- Not this slice: runtime/API changes, biometric capture, production rollout,
  new WSPs, agent dispatch, or patent claims.

Read root AGENTS/WSP 00, WSP 97, the curated historical bootstrap shelf, active
slice ledger, RedDog map/architecture/interface/roadmap/ModLog/test docs, canonical
Lick and public-admission docs, owning code/tests, and WSP 44/73. Large files were
read in bounded sections. A shallow sparse checkout fixed the main baseline;
GitHub reads fixed AutoPost source at
`4b9e2fd8958f54e5b4c0c36e690d781ac1e8f147`.

Retrieval evaluation: broad Lick search contains historical audits and roadmap
claims; current code and explicit status labels take precedence. The old active
ledger and bootstrap shelf do not establish current runtime status. Canonical
map first, exact-source reads second, and cross-repository signer discovery
avoided inventing another identity store. This is a bounded source audit, not
an exhaustive audit of every FoundUps repository or a live-device assessment.

WSP 00 V2 execution failed with `ModuleNotFoundError: No module named 'torch'`.
The documented tracker fallback opened the gate with
`execution_method=mathematical_formulas`; no detector witness was measured.
The owner-query attempt failed because the sparse checkout lacked the HoloIndex
package (`No module named 'holo_index.query_receipt'; 'holo_index' is not a
package`). There is no CURRENT owner receipt, reindex, or Holo repair claim.
Direct Git/GitHub retrieval is the explicit fallback. No local Qwen/Gemma
runtime was used; the bounded architectural review was performed directly.

## Claim evaluation

| Claim | Evidence / finding | Disposition |
|---|---|---|
| Lick is a recurring RedDog handshake. | Existing contract specifies encounter start, change, expiry and step-up; public PoC implements a narrower challenge path. | Supported design; incomplete runtime. |
| Lick proves a person is present now. | `lick_receipt()` returns `human_presence_proven=False`, `identity_verified=False`, `signed=False`. `startLick()` automatically echoes the returned challenge. | Not implemented; challenge completion is request continuity. |
| RedDog already has a media-signing building block. | AutoPost `signFoundupsMediaManifest()` signs an original-media hash, capture ID, time, nonce, and key-derived author ID. | Reuse candidate; not live-human or trusted-capture proof. |
| Signed media is automatically the received video from a trusted person. | AutoPost's verifier takes a manifest only and checks its embedded public key. Received-byte comparison, external signer trust, encounter binding, and capture integrity are additional requirements. | Unsupported as an end-to-end guarantee. |
| Two RedDogs make deepfakes impossible. | Mutual challenge/receipt verification can bind sessions; both endpoints may still endorse synthetic input or be compromised. | Reject absolute claim; evaluate scoped rejection of invalidly bound media. |
| Orphan recovery preserving Lick is already the current main behavior. | Main still documents crash reservations failing closed. Open #1641 contains earlier recovery work; #1680 reconstructs it with current-main reconciliation. | Pending branch work, not merged/live evidence at this baseline. |
| 000–222 is the mandatory capability escalation ladder. | WSP 44 runtime has ten codes, `A <= B <= C`, optional delta-constrained `transition()`, and direct `state_from_digits()`. No Lick admission or capability check is present in that engine. | Semantic scoring is not authorization. |
| A color/affect gradient can decide identity, coercion, or moral admission. | No evaluated palette-based verifier was found in the inspected Lick path. Tone can be ambiguous, imitated, translated, or disability-affected. | Optional communication hypothesis; never personhood or effect authority. |
| RedDog is the deep 0102 worker itself. | Current architecture/WSP 73 separates the fast proxy from the deeper principal-scoped twin. | Preserve distinct components and authority. |

WSP 44's axes are named Consciousness, Agency, and Entanglement in repository
semantics. The inspected Python implementation validates/scales codes; those
names do not constitute physical quantum measurements or biometric evidence.
Conversation policy separately classifies intent, reasoning depth, and effect
ceiling. Risk can request deeper review; even `AUTHORIZE` text reaches only a
proposal ceiling without the existing authenticated authority path.

## Exact source anchors

- `modules/communication/moltbot_bridge/src/reddog_public_policy.py`:
  `lick_encounter_request`, `lick_receipt`, `lick_verification_evidence`.
- `modules/communication/moltbot_bridge/src/reddog_public_session_gate.py`:
  `open_lick_encounter`, `complete_lick_challenge`, and turn reservation.
- `modules/communication/moltbot_bridge/tests/public_surface/test_lick_open_handshake.py`.
- `modules/infrastructure/wsp_core/src/semantic_state_engine.py`:
  `VALID_STATES`, `state_from_digits`, `transition`.
- `extensions/reddog/conversation_plane_policy.js`: `classify`, `effectCeiling`.
- `WSP_framework/src/WSP_73_012_Digital_Twin_Architecture.md` and
  `WSP_framework/src/WSP_44_Semantic_State_Engine_Protocol.md`.
- AutoPost pinned [Lick client](https://github.com/FOUNDUPS/autopost/blob/4b9e2fd8958f54e5b4c0c36e690d781ac1e8f147/src/modules/lick/lickClient.ts)
  and [media identity module](https://github.com/FOUNDUPS/autopost/blob/4b9e2fd8958f54e5b4c0c36e690d781ac1e8f147/src/modules/identity/foundupsAuthorIdentity.ts).
- Open [host recovery #1641](https://github.com/FOUNDUPS/Foundups-Agent/pull/1641)
  and [runtime reconciliation #1680](https://github.com/FOUNDUPS/Foundups-Agent/pull/1680):
  read as pending work, not runtime evidence. Recheck before implementing.

## Threat model and practical tests

Protect the receiver's assurance display and action boundary against substituted,
replayed, misattributed, stale, or fabricated encounter evidence. Assume attackers
can generate voice/video, operate real accounts, inject virtual media, copy
visible badges, and replay/reorder network content. Endpoint compromise and
collusion remain material limits, not assumptions to omit from product claims.

| Failure | Proposed control / experiment | Limit to preserve |
|---|---|---|
| Login remains valid after a person leaves. | Independent presence expiry and participant/track-change tests. | A network heartbeat cannot renew human evidence. |
| Real person passes a challenge while a fake face is streamed. | Bind challenge/liveness observation to capture track and delivered segments; test virtual camera/audio and bystander substitution. | Co-presence is not attribution; local attestation needs evaluation. |
| Genuine signed clip replayed as live. | New encounter epoch, challenge/peer/channel binding, sequence and freshness limits. | Signing time alone does not prove capture time. |
| Segment swapped, reordered, or transcoded. | Verify rendered bytes and continuity; authenticate transformation lineage. | Missing provenance is unknown, not proof of fraud. |
| Two compromised RedDogs agree. | Independent receiver policy, explicit issuer trust, key revocation, capture-boundary review. | Agreement and valid signatures cannot prove truthful observations. |
| A stable author fingerprint becomes tracking. | Pairwise/ephemeral disclosure design; review linkability of AutoPost author IDs and metadata. | Pseudonymity is not automatic unlinkability or anonymity. |
| Angry or dyslexic speaker fails a tone/cadence test. | Keep affect advisory; offer accessible alternatives and abstention. | Never translate affect uncertainty into a personhood verdict. |
| Verified participant requests protected work. | Preserve principal/project/action capabilities, consent and revocation. | Presence, `222`, signatures, and friendly affect grant no effects. |

AutoPost key custody needs explicit review: generation creates an extractable
keypair, exports private JWK material, then imports the signing key as
non-extractable. That is an existing software custody mechanism, not evidence
of hardware isolation or a trusted camera. The verifier's self-contained key
check is useful for integrity but requires an external binding for recognition.

## Alternatives and recommendation

| Approach | Evaluation |
|---|---|
| Passive face/voice/sentiment fingerprint as the gate | Insufficient against synthetic media, injection, drift, and false rejection; burdens privacy. Keep optional measured hints. |
| Mutual signed session receipts only | Useful first experiment for peer continuity and replay control; cannot make media/human claims. |
| Existing capture/signer plus standard media provenance and separately evaluated liveness | Recommended staged direction. Reuses ecosystem code and exposes the missing physical-to-digital binding instead of hiding it. |

The proposed order is encounter renewal, mutual machine continuity, actual
stream provenance, capture/liveness evaluation, then governed integration.
Keep all human-assurance claims unknown in the first machine-only experiment.
Measure attack acceptance, legitimate rejection, uncertainty, detection delay,
latency, energy, and accessibility before setting deployment gates. Repeated
verification is only worthwhile if it improves measured assurance enough to
justify its costs; checking unchanged weak evidence more often adds little.

## Technical references and interpretation

Read on 2026-09-13 JST; these are design anchors, not a conformance certification.

- [NIST SP 800-63B-4](https://pages.nist.gov/800-63-4/sp800-63b.html)
  distinguishes authentication, biometric factors, presentation/injection
  defenses, and session lifecycle. Design inference: test the capture path
  separately from key possession and do not promote risk hints to authenticators.
- [W3C WebAuthn Level 3](https://www.w3.org/TR/webauthn-3/)
  distinguishes user presence from user verification and scopes credentials to
  relying parties. Design inference: a passkey ceremony does not prove who
  appears in a stream or provide arbitrary continuous media signing.
- [C2PA 2.4, Live Video](https://spec.c2pa.org/specifications/specifications/2.4/specs/C2PA_Specification.html)
  supplies segment validation and continuity mechanisms. Design inference:
  evaluate it as the media carrier while keeping capture/liveness evidence and
  signer acceptance separate. Integrity/provenance is not factual truth.

## Verification record

Existing Lick tests were executed against unchanged runtime source: **12 passed**
in 0.25 seconds. Two inherited pytest configuration warnings concern absent
asyncio plugin options; the HTTP test uses `asyncio.run`. Initial collection
failed because `httpx` was missing; temporary scratch-only dependencies
(`httpx 0.28.1`, `fastapi 0.128.2`) resolved it. No repository dependency changed.

Command (with the temporary dependency directory on `PYTHONPATH`):

```sh
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -B -m pytest -q -o addopts='' --confcutdir=modules/communication/moltbot_bridge/tests/public_surface modules/communication/moltbot_bridge/tests/public_surface/test_lick_open_handshake.py
```

This verifies only the existing non-biometric path. No AutoPost runtime tests,
physical sensor tests, live-media interoperability, independent attack study,
production host, or new design implementation were exercised. A workspace
disconnect interrupted the final documentation write; changes were reconstructed
from exact-baseline GitHub files and reviewed before a GitHub commit. The earlier
runtime test result remains applicable because no runtime source changes.
Final documentation checks: two JSON examples parsed, nine new internal links
and their anchors resolved, and the update was limited to seven Markdown files.
The unchanged historical tails of the large roadmap and ModLog were retained.
No full release, deployment, or merge is asserted by this audit.
