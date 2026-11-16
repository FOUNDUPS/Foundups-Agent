# Poly Vote — eligibility, ballot and disclosure contract

**Status:** specified, not an executable schema or implemented API.
**Owners:** [README](README.md), [roadmap](ROADMAP.md), [parent integration index](../docs/VOTE_VOICE_INTEGRATION.md).

## Separate identity and authority states

Ordinary account -> authenticated account -> independently verified current office/role -> authorized chamber/process scope -> eligible action.

A phone challenge, biometric unlock, wallet signature or authenticated chat login does not by itself verify a congressional office or permission to act for it. Reuse existing trusted authentication and authorization owners; derive entitlements on the trusted side, not from a client flag, a self-asserted office ID or a public badge.

The verification designation is private by default. Do not leak it through a profile, public API field, badge, cache or capability directory. Office verification needs dated authoritative evidence, expiration/turnover, revocation, recovery and explicitly bounded delegation. A verified staffer is not automatically entitled to cast a member's preference.

NIST separates identity proofing, authentication and federation; authorization remains a separate system decision. WebAuthn user verification can be local biometric verification without exposing biometric data to the relying party. These are design references, not a selected provider or implemented enrollment process:
- [NIST SP 800-63-4](https://pages.nist.gov/800-63-4/sp800-63.html)
- [W3C WebAuthn Level 3](https://www.w3.org/TR/webauthn-3/)

## Distinct proposed records

Keep public-person identity, private entitlement, versioned process/ballot, nomination, preference, public disclosure and official-source record separate. A process must define chamber/body, role/seat, nominee eligibility, eligible participants, voting window, revision/withdrawal policy and whether any tally is published. No global 'Congress can vote on everything' privilege.

Authorization and integrity tests must cover current-role binding, forged/stale claims, replay, duplicate ballots within defined rules, concurrent edits, revocation, delegated scope and key recovery. Reuse a qualified existing signing/credential owner; cryptography does not require blockchain or token ownership.

## Public versus private participation

- **Public by explicit choice:** identity-linked nomination/preference may appear on the representative's card and committee drill-down, with scope, time/revision and attribution.
- **Private by default:** identity, entitlement, participation and choice are absent from the public projection. Do not expose a 'voted privately' marker, a count increment attributable to one person, or a synthetic abstention/no-vote claim.
- **Cryptographic anonymity:** an additional security property requiring a reviewed protocol and threat model. Hiding a UI field does not make a signed, identity-linked backend record anonymous.

The public surface should describe its coverage as public disclosures only. It must not imply that absence proves non-participation. Aggregates, timestamps and small committee cohorts can reveal private choices; publication thresholds/timing and re-identification resistance are unresolved gates, not automatic tally features.

No identity-linked ballot or receipt goes onto a public immutable ledger by default. Define who can see what, including administrators, and independently test that boundary. Retraction can stop future display but cannot promise removal of copies already made public.

## Tile and conversation behavior

Use shared Mall controls: person card -> accessible details/flip -> Committees -> committee tiles -> that person's authorized public nominations/preferences. Respect the viewer's access on every request; do not merely hide leaked data with CSS. Private participants use a separately authorized workspace; their hidden activity never populates the public grid.

Person media opens the existing scoped media grid with source attribution and stable return context. Public endorsement videos are a deliberate Voice/media action linked to a selected record, not automatic publication of a private ballot or Poly Voice meeting.

Member discussion/chat reuses a qualified existing communication owner if available. No claim of end-to-end encryption, confidentiality or working chat is made here. Minimize retained political preference data and do not route it to analytics, persuasion profiling or unrelated agents.

## Institutional meaning

All in-app preferences are NON_BINDING unless an independently established official authority and qualified process expressly says otherwise. Official roll calls and appointments retain separate original sources and labels. Role labels/eligibility must be verified against the relevant institution before release; do not invent a Senate Speaker office or conflate party leadership, House Speaker, committees and cabinet offices.

## Required verification

Test public/private separation at API, storage, logs, cache, export, notifications and UI layers; access revocation; stale/duplicate claims; record edits; small-cohort disclosure; and card/committee/media navigation. An ordinary login test is not office verification, and passing signature checks is not election certification. No runtime work is authorized by this document.
