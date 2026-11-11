# Vote ecosystem — current ownership and integration index

**Status:** documentation only; new Poly capabilities are SPECIFIED_NOT_IMPLEMENTED.
**Reconciled:** 2026-11-12, from 012's latest explicit clarification and the retrieved earlier work.
**Owner:** 0102 documentation lane, PR #2337. This index is not runtime admission.

## Component ownership

| Component | Responsibility | Canonical planning owner |
|---|---|---|
| Vote/Ballots (`voteballots`) | Umbrella civic FoundUp; public politician discovery, evidence, profiles/media and separately labeled community preferences | [Vote roadmap](../ROADMAP.md) |
| HPC | Existing community FoundUp associated with Vote; attributed community media and campaigns | [Existing HPC roadmap](../../hpc/ROADMAP.md), read-only in this change |
| Poly Vote (`polyvote`, module name only) | Verified-office nominations and non-binding leadership/committee preference voting; private/public disclosure choices | [Own module README](../polyvote/README.md), [roadmap](../polyvote/ROADMAP.md), [interface](../polyvote/INTERFACE.md) |
| Voice | Separately planned civic-action FoundUp: issue/evidence/contact journey, voluntary calls and deliberately public endorsements | [Existing intake #2330](https://github.com/FOUNDUPS/Foundups-Agent/issues/2330), [retained action specification](VOTE_VOICE_INTEGRATION_HISTORICAL_20261110.md) |
| Poly Voice (`polyvoice`, proposed FoundUp ID) | Separate planned FoundUp for consented device-local meeting capture, business-only review and privacy-preserving commitments | [Own README](../../polyvoice/README.md), [roadmap](../../polyvoice/ROADMAP.md), [interface](../../polyvoice/INTERFACE.md) |
| Oversight | Existing strategy/reference workstream under Vote | [Existing owner](../oversight/README.md) |

Poly Vote is **inside Vote**, not a separately registered FoundUp, token, tenant, repository or identity stack. Poly Voice has its **own planned FoundUp boundary**, not a recording feature owned by Voice. Both retain connections to the Vote ecosystem. An independent roadmap does not imply a separate application shell or an admitted runtime.

The parent roadmap carries links and integration dependencies only. Detailed acceptance, security decisions and stage progression live with each module. Play FoundUps Mall remains the shared presentation owner; do not add civic-specific policy to generic platform documentation or copy its tile/player/authentication services.

## Current user journeys

- Public Vote: politician card -> media/profile grid -> sourced evidence; committee navigation can read only authorized public Poly Vote disclosures.
- Poly Vote: ordinary sign-in -> separately validated current-office entitlement -> private workspace -> nomination/ballot -> explicit per-record disclosure choice. Hidden entitlement is never a public badge by default.
- Voice: user chooses an issue or public endorsement -> reviews sources/message -> explicitly initiates contact/publication -> returns to the originating context. A dialer link is not a verified calling engine.
- Poly Voice: consented manual meeting capture -> entirely local processing/review -> encrypted local record -> optional commitment receipt. Raw conversation and business JSON stay on the device by default.

Public community preferences, verified-office preferences, public endorsements, meeting commitments and official congressional records are distinct records. Do not combine their counts or label an in-app preference an official election, committee appointment or vote.

## Retained Vote/Voice requirements

The earlier [full integration specification](VOTE_VOICE_INTEGRATION_HISTORICAL_20261110.md) is retained byte-for-byte as historical research, including source qualifications, campaign-finance distinctions, accessible card/media behavior, seven-pepper uncertainty, manual-contact-first design and consent/abuse boundaries. Its provider checks are dated, not current service guarantees.

The earlier Democratic-Senate-first collection is a staged discovery proposal, not an eligibility rule for Poly Vote or a permanent exclusion from the requested Senate directory. The later request describes Senate and House navigation, politician media grids and committee tiles. Before implementation, the Vote owner must reconcile roster coverage and staged rollout; do not invent a current roster or a 'Senate Speaker' office. Community-promoted names are not evidence of acceptance, endorsement or official eligibility.

## Supersession and build sequencing

This index and the Poly owner documents supersede the historical specification **only** on component ownership, the latest private/public participation distinction and commitment-only default egress. Unrelated source/evidence, safety, accessibility and user-control requirements remain.

HPC stabilization remains the existing implementation priority. This documentation change neither edits its source/docs nor changes its acceptance or active PRs. New Vote, Voice and Poly implementation waits for the existing shared-Mall/HPC acceptance gate and its own authorization. It does not become part of the HPC repair.

[Reconciliation receipt](POLY_RECONCILIATION_20261112.md) records sources, coverage gaps, file boundaries, legacy wording and cross-repository reuse. No registry, manifest, route, catalog, token, microphone, ballot, provider account or deployment is activated here.
