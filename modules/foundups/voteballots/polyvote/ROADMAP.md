# Poly Vote — module roadmap within Vote

**Status:** documentation only. Parent: [`voteballots`](../README.md).
**Interface:** [eligibility and disclosure contract](INTERFACE.md).
**Build dependency:** existing HPC/shared-Mall stabilization and a separately authorized Vote integration slice. Do not edit or merge HPC work from this module.

| Stage | Deliverable | Acceptance / current state |
|---|---|---|
| POLY0 — documentation | Own README/INTERFACE/ROADMAP/ModLog; link from parent without a new FoundUp genesis | Authored for review; no runtime admission |
| POLY1 — synthetic PoC | One defined chamber/committee scenario with synthetic roles, nomination/preference lifecycle and private/public projections | Planned; visibly synthetic, no real-office claims, no public private-participation leak |
| POLY2 — verified-office prototype | Dated office proof, role-scoped authorization, revocation/recovery, integrity and disclosed-choice controls | Planned; independent identity/security/privacy acceptance before real use |
| POLY3 — connected civic workflow | Shared person/committee/media tiles, separately qualified discussion, explicit Voice/public-endorsement handoff | Planned; no copied grid/chat/identity service or automatic sharing |
| POLY4 — supported pilot/MVP | Institutional scope, operational ownership, correction and support model, measurable privacy/reliability criteria | Not specified or achieved; remains non-binding absent independent official authority |

## Gates to resolve before coding

Define exactly which process is being modeled, who may nominate/vote, how a private ballot is stored, whether any aggregation is published, and who can link identities to choices. Choose reviewed shared signing/credential primitives only after discovery. Anonymity and cryptographic auditability are separate acceptance claims.

Use the existing Vote/Mall profile and media owners; committee tiles are a projection of authorized records, not a second grid implementation. Keep public community polls, verified-office participation and official-source records separate.

No registry entry, standalone tenant, token, blockchain deployment, production ballot, office enrollment or runtime test is part of the documentation stage. Evidence must separate authored, reviewed, merged, implemented, independently verified and deployed states.
