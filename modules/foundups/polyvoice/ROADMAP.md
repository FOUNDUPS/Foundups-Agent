# Poly Voice — independent staged roadmap

**Status:** documentation-only candidate; no stage is passed by writing this roadmap.
**Parent coordination:** [Vote integration index](../voteballots/docs/VOTE_VOICE_INTEGRATION.md).
**Detailed contract:** [interface](INTERFACE.md). **Implementation hold:** existing HPC/shared-Mall stabilization first; do not modify that work.

| Stage | Deliverable | Acceptance / current state |
|---|---|---|
| PV0 — intake and ownership | Own README/INTERFACE/ROADMAP/ModLog and eight-artifact intake; reconcile former Voice-owned proposal | Documentation authored for review; registration, executable manifest and runtime remain absent |
| PV1 — local PoC | One synthetic/staged meeting on one qualified device; manual consented capture, local business JSON review, encryption and a local commitment demonstration | Planned; independent source comparison, failure/interrupt tests and zero private-content egress required |
| PV2 — receipt prototype | Separately authorized receipt transport, office attribution where required, minimal-envelope privacy, replay/correction and key/recovery behavior | Planned; no public JSON default, no claimed meeting completeness, no unreviewed protocol |
| PV3 — limited real-office pilot | Current-office/delegation proof, qualified device matrix, jurisdiction/office approval, retention and support responsibilities | Gated; real recording cannot start merely because a synthetic test passed |
| PV4 — MVP | Supported scope, owners, operational/privacy metrics and correction process defined from pilot evidence | Not specified or achieved; no invented adoption forecast |

## Reuse/research work before implementation

Confirm actual capture, private-media storage, local speech and identity owners in Foundups-Agent and AutoPost. Retrieve current contracts and test inventories, not old pass counts. Existing camera/vision, host-side speech, signatures and device possession each prove different things. No remote transcript pipeline is an acceptable fallback for a local-only requirement.

Evaluate the commitment threat model, guessable metadata, timing/linkability, platform backup, key loss, deletion and coercive disclosure. Decide separately whether a public 'meeting attested' marker is wanted; a bare hash cannot communicate its facts.

## Promotion evidence

Retain exact source/device/environment, independent verifier, network-egress results, reviewed summary comparison, receipt rejection/replay tests, encryption/recovery limits and consent/retention review. Report documentation, implementation, registration, merge, deployment and PC synchronization separately.

Public full-text/JSON disclosures, ranking, correlations, automated publishing and off-device backup remain unselected later proposals, not prerequisites or authorized defaults. No new WSP, blockchain or scheduler is required for the local PoC.
