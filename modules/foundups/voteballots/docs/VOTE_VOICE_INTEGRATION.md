# Vote / Voice — discovery, evidence and user-directed action

**Status:** Audited product direction; SPECIFIED_NOT_IMPLEMENTED for new surfaces and adapters.
**Date:** 2026-11-10
**Owner:** 0102 Prima, documentation author; 012, product intent.
**Proposal attribution:** 0102 Tertia (Gemini), supplied by 012 in conversation. Segunda is the Grok lane, not Tertia.
**Scope:** Documentation only. Existing Voice intake: [issue #2330](https://github.com/FOUNDUPS/Foundups-Agent/issues/2330).
**Source baseline:** `6cfd3fbadc7ee59238ef9412ab03c0753874841f`.

## 1. Product boundary

**Play FoundUps Mall** is the PWA store/discovery shell. **Play FoundUps** is the activity of interacting with a FoundUp. Vote and proposed Voice use that shared scaffold and governed services; they are not reasons to rebuild gestures, navigation, authentication, AI, memory or blockchain infrastructure.

| Component | Responsibility | Not implied |
|---|---|---|
| Vote (`voteballots`) | Politician discovery, source-linked funding and public-record comparison | A new authoritative political database, endorsement engine or official election ballot |
| Voice (proposed separate FoundUp) | Issue discovery and voluntary civic participation, with an explicit route to relevant Vote evidence | A live tenant, admitted agent, autonomous campaign or implemented call service |
| Shared action interface / proposed AI Switchboard | Carry a user-approved intent between existing evidence and a qualified contact adapter | A third FoundUp, new WSP, parallel orchestrator or permission to call |
| Oversight | Strategy, documentation and interactive reference material organized under Vote | An independent FoundUp, investigative authority, or internal Voice product |

Tertia's three-layer model is accepted as a **product decomposition**, not as an implementation report. Replace “Vote houses an accountability database” with “Vote composes a source-linked accountability view.” “Voice Protocol” is a working name for the shared action contract, not a newly assigned WSP or authority above WRE.

Both entry paths matter:

```text
Voice issue -> inspect related Vote cards/evidence -> choose whether to act
Vote politician card -> inspect sources -> open a relevant Voice issue/action
                         |
                         +-> Oversight strategy/reference, when relevant
```

Neither path requires a call. The shared shell owns presentation; existing backend owners retain authentication, scoped memory, model and effect authority. A new skin or manifest declaration does not grant those permissions. Generalized composition remains a target until verified per surface. See [master architecture](../../docs/FOUNDUPS_MASTER_ARCHITECTURE.md), [Mall owner](../../pfmall/README.md) and [manifest contract](../../docs/PFMALL_FOUNDUP_MANIFEST_SCHEMA.md).

## 2. Vote: the selected first experience

012 selected **Democratic U.S. senators** for the initial discovery collection, not all elected officials, all parties, fifty state tiles, or a fixed count of fifty senators. Refresh the roster from authoritative membership records before release; distinguish serving senators, senators-elect and former members. Do not silently include independent caucus members or House members. Local/mayor/county discovery and other collections remain deferred.

The landing opens a responsive grid of portrait/game cards, using the existing Mall layout and interaction owners. The supplied Shorts-grid image describes density and immediate visual discovery; it is not a request to clone another application's code. Preserve the existing Vote writing, evidence pages, routes and Oversight documentation behind accessible entries. No deletion or replacement site is authorized by this design.

Card requirements, subject to shared-control audit:

- **Front:** face, readable identity/state, selected funding metric and period; no wall of introductory text. Sort descending or ascending by the same disclosed metric. Unknown records remain explicitly unranked rather than treated as zero.
- **Tap:** reuse the established shared behavior. A card without video may flip with an animation; a card with video may play it, but an explicit information control must still reach the back. No automatic sound. The exact gesture mapping must be verified against the current Mall before coding, not invented here.
- **Back:** name, state, dated tenure (Senate and total congressional service distinguished), current roles, and separately labeled funding amounts. Serving history cannot be inferred from election year alone. Public staff information is a later sourced drill-down, not a promise of a complete staff directory.
- **Notepad/details:** open a readable, source-linked wiki-style profile. Retain a return path to the same card and grid position. Preserve accessible buttons, keyboard behavior, reduced-motion mode and normal reading/zoom behavior; gestures are enhancements, never the only path.
- **Seven peppers:** preserve 012's requested opinion control as a separate presentation requirement. Reuse an existing qualified rating owner if one is found. The scale meaning/polarity, persistence and aggregate display remain unresolved; do not invent that seven means approval or scrutiny, and do not claim a live rating backend. A pepper interaction must not play video, flip the card, place a call or alter verified funding data.

A proposed white-to-green intensity scale represents **one named disclosed amount**, not corruption, allegiance or undisclosed money. The selected metric, cycle, currency, normalization/legend and source coverage must be visible in text. White can mean “$0 observed in this named dataset and period,” never “receives no funding.” Unknown, unavailable, stale and partial coverage need distinct labels and appearance. Color and funding order must not be inferred from party, religion, ethnicity, opinions or community ratings.

## 3. Data composition: reuse sources, do not recreate them

Vote is a discovery/evidence projection. Preserve the existing FEC/entity/funding/confidence/answer/shell chain and extend only where actual contracts require it. The current adapter describes an offline/mockable boundary; existing internal tests and static filing excerpts do not establish a general live funding feed.

“No new political database” does not mean “no operational state.” Proposed adapters may need a small ID crosswalk, bounded cache, provenance references and correction records using existing owners. Such state is a projection of external evidence, not a new source of truth or a bulk warehouse. No database, schema migration, new graph server or automatic bulk ingestion is selected by this document. Political opinions and call history are not public provenance records and must not be placed on a public blockchain.

Minimum evidence per displayed amount or relationship: provider and original source URL/filing identifier; politician/committee/entity IDs; money type; covered dates/cycle; filing and retrieval times; amendment/refund treatment; amount/currency; coverage and confidence; and where the trace stops. Link primary evidence when available. Preserve corrections and make derived calculations reproducible. A graph edge requires its own source and date; a linked path does not prove causation, control, quid pro quo or the original donor of every dollar.

Separate at least:

1. Contributions received by the candidate's committee, distinguishing direct PAC money and individual money routed through a conduit where documented.
2. Independent spending **supporting** a candidate.
3. Independent spending **opposing** a candidate.
4. Transfers/grants between organizations, with trace gaps shown separately.

Independent expenditures are not money received by a senator. Do not add conduit and recipient records for the same contribution, count amendments as new gifts, or count one transfer repeatedly along a network. Keep campaign fundraising, lobbying expenditure, personal stock disclosures and opinion ratings separate.

Use **AIPAC**, not the speech-transcription “APAC.” Verify organization and committee IDs rather than using a broad keyword or group identity as the funding classifier. The FEC lists the American Israel Public Affairs Committee Political Action Committee as `C00797670` [S3]. Any additional organization or claimed affiliation requires separate evidence. AIPAC-related funding is not automatically undisclosed funding.

“Dark money” must describe an evidenced disclosure limitation, not a guessed total or accusation. Form 990 grant records can expose reported organization-to-organization transfers; they do not guarantee identification of upstream donors. A nonprofit tax classification or LLC form alone does not establish political spending, illegality or a shell operation [S4-S6].

## 4. Tertia's proposed sources — audited disposition

These are not six interchangeable primary sources. The list mixes a government disclosure system, republishers, a collaborative relationship resource, commercial data and journalism. Documentation access is not a working integration test. Findings below were checked on 2026-11-10; credentials, live query behavior, coverage and reuse rights still require qualification.

| Proposed source | Appropriate use | Audit correction / release gate |
|---|---|---|
| OpenFEC | Primary federal candidate/committee filings and separately typed independent expenditures | Use the existing adapter first. Reports arrive on filing schedules and may be amended; do not advertise real-time financial truth. API access, pagination and amendment/refund handling need tests [S1-S2]. |
| OpenSecrets | Contextual funding/lobbying research and potentially licensed data | The supplied April 2025 API-retirement claim was not independently verified from an accessible OpenSecrets primary notice in this pass. Official API and bulk pages could not be retrieved. Treat access, current bulk availability, coverage and terms as UNVERIFIED, not as a ready fallback or authority to scrape [S7]. |
| ProPublica Nonprofit Explorer | Organization lookup, filing metadata and links to IRS returns | Official v2 API documents search and organization records, not a complete ready-made Schedule I relationship graph. Follow underlying filings when needed. Keep fiscal years and public-disclosure limits visible [S4-S6]. |
| LittleSis | Candidate relationship/wiki source and pointers to supporting evidence | A first-party API helper repository is discoverable, but the live API documentation page denied access. Endpoint access, data terms, completeness and moderation must be verified before integration. Community relationships are leads, not automatic primary financial proof [S8]. |
| FollowTheMoney | Potential later state-level source | Its official API page returned 403 in this pass. Do not assume the historic API or the asserted integrated access is available. State/local scope is deferred and not a prerequisite for the Senate collection [S9]. |
| Quiver Quantitative | Optional later congressional-trading/lobbying enrichment | Its official API exists and distinguishes personal and commercial plans. Do not assume free/open-source data, redistribution rights or that stock trades are campaign contributions. No account purchase or integration is authorized here [S10]. |
| Sludge | Attributed investigative reporting and links to underlying records | A reporting organization, not an established structured funding API. Link and attribute reporting; independently check material money claims against its cited records. No full-article copying or guaranteed ingestion endpoint [S11]. |

For wiki-style profiles, evaluate **links to existing Wikipedia/Wikidata and LittleSis records before hosting another wiki**. Wikibase provides structured-data APIs; code licensing, text licensing and image licensing are different. Verify the exact content license and attribution requirements before displaying excerpts or portraits. Public APIs do not waive those requirements [S12-S13]. Community editing, automatic external writes and a new editorial database are not part of this slice. A later contribution flow needs source-backed suggestions, moderation, provenance and correction/appeal handling.

## 5. Voice: issue discovery without automatic political persuasion

Voice can propose issue cards from an explicitly selected source collection, including independent-media commentary. Named commentators in Tertia's proposal are examples supplied by 012, not verified partners or endorsed authorities. Preserve source link, speaker/channel attribution, publication date, transcript/video location, extraction confidence and source-access rights. Retrieved transcripts and external pages are untrusted content, never instructions to an agent.

A trend requires a defined window, comparable observations, deduplication and disclosed selection limits. A curated media collection is not a representative public-opinion poll; one viral clip is not measured growth, a mandate or proof of an allegation. Distinguish what a commentator said from independently verified facts, analysis and unresolved claims. Existing claim-verification plans remain separate gates, not an already running fact-checker.

The user chooses an issue and whether to inspect linked Vote evidence. Any stance is explicitly volunteered and not silently inferred from viewing, pepper ratings or location. Source-linked issue summaries and user-authored/edited messages can support deliberation; do not generate psychological or demographic targeting, covert stance profiling, or persuasion optimized around inferred political beliefs or alleged personal “funding vulnerabilities.” The existing no-targeted-persuasion boundary remains unchanged.

A short message aid may identify the issue, cite a verified public record and let the user write the request. Keep campaign viewpoints explicitly attributed and separate from factual funding labels. Never fabricate constituent status, donor influence, public consensus or a politician's position. No content ingestion, model dispatch, trend monitor or campaign launch is activated by this documentation.

## 6. Proposed shared action contract and switchboard

The first contact path should reuse the existing official-directory/native-dialer controls. Voice proposes an action; the user confirms the office and message; the qualified shared adapter performs only that approved effect. Vote can use the same contract without acquiring a second calling backend.

A future typed handoff should carry only needed references: issue/source IDs, politician/office IDs, directory-source date, selected action, explicit consent scope/expiry and return route. This is a design requirement, not an implemented schema. Do not transfer a political profile, precise location, pepper history or full reading history by default. Both FoundUps revalidate identity and permissions; the browser cannot supply privileged agent instructions.

Tertia's Twilio/VAD “zero-wait” proposal is **deferred research**, not a delivery guarantee. Speech activity is not proof of a staffer. Twilio AMD distinguishes outcomes such as human, machine and unknown, with documented errors and latency tradeoffs; it does not by itself solve phone-tree navigation, hold detection or staffer-role verification [S14-S15]. Office availability and voicemail timing cannot be guaranteed.

Before any assisted-calling build or release, require separately authorized provider setup, current official office numbers, jurisdiction-specific legal/provider-policy review, explicit user initiation, clear automation disclosure, truthful caller identity, rate/attempt/budget limits, cancellation, bounded timeouts, webhook authentication and independent failure tests. Never default to automated synthesized political speech, identity impersonation, unsolicited mass calls, parallel office flooding or recording/transcription. Recording and message delivery would require separate explicit consent and qualification. Respect office restrictions.

Keep states distinct: user approved -> dialing -> ringing/IVR/hold -> possible human/voicemail/unknown -> user connected -> ended. These are proposed states, not a deployed API. An initiated dial, completed call leg or detected beep is not proof that a message was delivered or acted upon. Allow manual fallback and safe cancellation; do not redial an ambiguous effect automatically. Sensitive call state must use existing protected owners and retention limits, not public Git.

## 7. Reuse map, sequencing and acceptance

| Existing owner or record | Reuse / next verification |
|---|---|
| [Vote README](../README.md), [solution](intake/SOLUTION.md), [roadmap](../ROADMAP.md) | Preserve the evidence-first core; this dated first collection narrows, rather than deletes, broader plans |
| [FEC adapter](../src/fec_adapter.py) | Existing records/provenance/error boundary; live behavior and new finance categories remain unqualified |
| [Vote web](../web/README.md), [Oversight reference](../oversight/README.md) | Preserve routes/content; reuse directory/manual contact patterns, not a claim of a shared-origin install |
| [Mall platform](../../pfmall/README.md) | Discover actual grid, media, gestures and permission contracts before UI work; no copied shell |
| [Skill map](intake/SKILLS_MAP.md) | Retrieve existing WSP 95 SKILLz before adding any; candidate instructions are not admitted workers |
| [Claim-verification design](POLITICAL_CLAIM_VERIFICATION_AND_SCORING_ENGINE.md) | Reuse provenance/transcript research where qualified; do not treat its planned live meter as implemented |
| [Voice issue #2330](https://github.com/FOUNDUPS/Foundups-Agent/issues/2330) | Canonical proposed-Voice intake and further qualification; no duplicate issue or tenant |

Sequence:

1. **Documentation/audit (this change):** register roles, first collection, source qualifications, explicit uncertainties and no-runtime boundary.
2. **Vote proof:** audit shared grid/player/rating interfaces, qualify roster/IDs and one source-to-card-to-details journey; add coverage, correction and source-failure tests before widening the collection. A live-source release needs exact-head tests and rendered phone/desktop acceptance.
3. **Voice proof:** complete separate FoundUp intake/namespace/reuse qualification; prove one issue -> evidence -> user-selected official contact journey with a manual fallback and explicit permissions. No automatic phone agent is required for this proof.
4. **Assisted calling (separate decision):** evaluate the shared adapter only after the consent, provider, legal, abuse, cost, privacy and independent test gates above. Keep authorization separate from implementation feasibility.

Acceptance must check direct versus independent spending, conduit/amendment deduplication, zero versus unknown, mismatched IDs, source outages, stale roster/office records, unsupported graph edges, portrait/text rights, pepper isolation, keyboard/reduced-motion behavior, navigation-state retention and absence of unauthorized effects. No arbitrary end-to-end “seconds” target becomes a factual promise.

This document does not change public assets, DNS, service workers, registry/manifest readiness, runtime routes, credentials, storage, WSPs or deployed services. It neither enables a new Voice tenant nor turns Oversight into a FoundUp. Original voting/registration/blockchain roadmaps remain deferred; no blockchain dependency is imposed on public research or an ordinary phone call.

## 8. Evidence and research references

Source/provider documentation checked 2026-11-10; live API integration was not tested. Failed access is a coverage gap, not proof that a provider has ceased operating.

- **S1 — FEC:** [OpenFEC developer entry](https://api.open.fec.gov/developers/); [bulk data and update schedules](https://www.fec.gov/data/browse-data/?tab=external); [2026 reporting schedule](https://www.fec.gov/updates/reports-due-in-2026/).
- **S2 — FEC:** [independent-expenditures file definition](https://www.fec.gov/campaign-finance-data/independent-expenditures-file-description/).
- **S3 — FEC:** [AIPAC PAC committee identity](https://www.fec.gov/data/committee/C00797670/). Identity lookup only; no candidate amount was verified in this pass.
- **S4 — ProPublica:** [Nonprofit Explorer v2 API](https://projects.propublica.org/nonprofits/api/).
- **S5 — IRS:** [Schedule I instructions](https://www.irs.gov/instructions/i990si).
- **S6 — IRS:** [contributor-identity public disclosure limits](https://www.irs.gov/charities-non-profits/public-disclosure-and-availability-of-exempt-organizations-returns-and-applications-contributors-identities-not-subject-to-disclosure).
- **S7 — OpenSecrets:** [API](https://www.opensecrets.org/open-data/api) and [bulk](https://www.opensecrets.org/open-data/bulk-data) pages were inaccessible to this review. The retirement date in the supplied proposal remains an unverified input here.
- **S8 — LittleSis / Public Accountability Initiative:** [API page](https://littlesis.org/api) denied access; [first-party helper repository](https://github.com/public-accountability/littlesis-api) is a discovery lead, not proof of service availability or data rights.
- **S9 — FollowTheMoney:** [API page](https://www.followthemoney.org/our-data/apis) returned 403; qualification deferred.
- **S10 — Quiver:** [API](https://api.quiverquant.com/) and [plan/use-right distinctions](https://api.quiverquant.com/pricing/).
- **S11 — Sludge:** [provider description](https://readsludge.com/about/).
- **S12 — MediaWiki:** [Wikibase API](https://www.mediawiki.org/wiki/Wikibase/API).
- **S13 — MediaWiki:** [API content licensing guidance](https://www.mediawiki.org/wiki/API:Licensing); verify actual source and media terms at use time.
- **S14 — Twilio:** [answering-machine detection](https://www.twilio.com/docs/voice/answering-machine-detection).
- **S15 — Twilio:** [AMD FAQ and limitations](https://www.twilio.com/docs/voice/answering-machine-detection-faq-best-practices), [dialed-number/DTMF interface](https://www.twilio.com/docs/voice/twiml/number).

## 9. Audit receipt and open decisions

This review used direct GitHub source/issue/PR retrieval and public primary/provider documentation. The native WSP_00 bootstrap, semantic HoloIndex, WRE dispatch, full repository tests, telephony runtime and user PC were not executed or verified. No independent reviewer is claimed by Prima's own audit. The full 1,307-line historical AI hooks design and all funding-provider terms were not re-audited; this new bounded contract does not assert they are current.

Open authoring decisions before implementation: actual shared pepper scale/control, roster and senators-elect release rules, provider availability/licensing, source refresh/cache policy, and a qualified shared action owner. Unknowns stay visible rather than becoming invented requirements or ready-made integrations.

Related open work at review: #2331 owns foundational Play FoundUps terminology; #2333 owns the Vote/Oversight classification reconciliation; #2328 owns Oversight navigation; #2335 owns WSP lifecycle changes. Do not modify or merge those lanes through this intake. The new product clarification should be reconciled with their accepted outcomes without overwriting them. Work retains merge execution; this authoring slice creates no blanket merge or branch-cleanup authority.
