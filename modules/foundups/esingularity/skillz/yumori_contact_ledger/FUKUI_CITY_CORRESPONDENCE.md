---
name: fukui_city_correspondence
parent_skill: yumori_contact_ledger
status: prototype_child_protocol
scope: YUMORI / Sukatto Land Kuzuryu / Fukui City government correspondence
updated: 2026-09-18
---

# Fukui City correspondence protocol

This protocol extends `yumori_contact_ledger`. It is **not** a second contact ledger, routing table, or correspondence source of truth. Gmail remains canonical for message state; the private Contacts/Email Log/Correspondence Routing records remain canonical for mutable recipient routing.

## Why this child protocol exists

Repeated Fukui City correspondence was reconstructing settled context from scratch: prior sends, current PPP/PFI asks, Article 6 framing, document links, recipient policy, canonical names, and open-loop state. That creates latency and avoidable errors. The city workflow should load a bounded send packet first and research only what is stale, missing, or legally/factually time-sensitive.

## Mandatory parent gate

Run `SENT_FIRST_MOSHPIT_NOTIFY_0102` before draft-status conclusions, resend decisions, or a new city send. Read the complete relevant thread, Sent state, actual recipient coverage, and dated Moshpit receipt.

## Canonical identity guard

- Principal public/search key: **UnDaoDu Michael J Trout**.
- Verified LinkedIn URI: `https://jp.linkedin.com/in/openstartup`.
- A generic `Michael Trout` search is insufficient identity evidence.
- Project display identities may include `012`, `九頭龍 泰澄`, `UnDaoDu`, and `Michael J. Trout` according to audience and source.
- Technical-advisor project-canonical spelling: **Jorge Sabastian**.
- A public DeCenter profile uses `Jorge Sebastian`; when that source is material, preserve the project-canonical spelling and note the public-source variant rather than silently replacing it.

## City send packet

Load these in order before drafting:

1. Relevant Gmail Sent/thread state and unresolved asks.
2. `YUMORI.me Contacts`, `Email Log`, and `Correspondence Routing`.
3. Current `YUMORI Moshpit` activity/open-loop state.
4. The smallest relevant project-document packet:
   - **05** — YUMORI PPP/PFI 民間提案マスター.
   - **03** — evidence, regional value, policy and technical context.
   - **03+05** — integrated Japanese submission master.
   - **LANDOWNERS** — landowner discussion/options.
   - **02** — prior mayor request / request history.
   - **04** — principal profile and canonical identity/background.
   - Current JHR/eSingularity public report when national compute-policy context is material.
5. Current deadline and the precise procedural outcome requested.

Do not re-research settled project facts merely because a new email is being written. Re-research when freshness, authority, legal status, policy status, identity, or source provenance materially changed or is missing.

## Routing guard

`Correspondence Routing` is live mutable truth. Resolve actual addresses at execution time from the authorized private ledger.

- `DO_NOT_ADDRESS_OR_CC` and `PERSONAL_ROUTE_CLOSED` are hard denies.
- Institutional business goes to the verified organization route when a personal route is closed.
- Do not invent or guess undisclosed addresses.
- Do not store private To/CC/BCC addresses in this repo protocol.
- BCC membership remains private operational state and is never copied into public Moshpit or Git documentation.

## PPP/PFI process frame

- Do **not** state that the YUMORI.me Preparatory Committee automatically qualifies as the formal `PFI法第6条` proposer.
- The committee is the **案件形成・オーケストレーション主体**: it coordinates evidence, landowners, demand, technical partners, investors/lenders, and formation of an implementation vehicle.
- A future implementation-capable `SPC/SPV`, company, or consortium may become the formal implementing/proposing entity when legally appropriate.
- Ask Fukui City to identify the Article 6 route and, if the current entity does not qualify, the **第6条以外** PPP private-proposal route, required legal entity, receiving department, required materials, evaluation body, and schedule.
- The approximately **15.8億円** demolition estimate is not YUMORI cash and is not automatically transferred as subsidy. Treat it as a public-cost benchmark and compare legally usable **解体回避価値** through `PSC/VFM`, including demolition, asbestos/remediation, restoration/infrastructure work, and private-risk transfer.
- Landowners are indispensable transaction parties. Listing a registered owner never means support or consent.

## Japanese-first drafting contract

Default order:

1. concise purpose and requested procedural outcome;
2. why the current factual/policy environment matters;
3. AI Koban/adaptive reuse as an opportunity to **test**, not a proven outcome;
4. formal PPP/PFI / Article 6 or non-Article-6 route;
5. numbered factual/process questions and requested written answers;
6. the smallest useful linked evidence set;
7. concrete deadline or next procedural event when one exists.

## Pressure / allegation boundary

Use documented dates, costs, statements, replies, recordings, and procurement records as facts when verified. Questions about procurement, contractor selection, timing, or transparency may be asked when evidence supports the inquiry. Motive, corruption, a secret demolition deal, or a favored contractor must not be stated as fact without records establishing it. Keep questions distinct from established facts.

## Pre-send canonicalization

Before consequential city correspondence, verify all of the following:

- canonical principal identity;
- spelling and role of every named person/organization;
- current legal/process terminology;
- current document links;
- Contact-ID/organization routing and blocked routes;
- prior Sent/draft state and duplicate-send risk;
- factual claims against the loaded source packet or current authoritative research;
- no private routing data has leaked into Git/public documents.

Failure of any identity/routing/factual gate means `HOLD` until repaired.

## Post-send invariant

1. Verify the exact message in Gmail Sent before reporting success.
2. If a material naming/factual typo escaped, send the smallest same-thread correction; never silently rewrite history.
3. Reconcile every material transition across:

`Gmail -> Email Log -> Contacts -> Action Queue -> YUMORI Moshpit`

4. Record agent errors/repairs separately in `0102 Moshpit`.
5. On connector or message-stream interruption, inspect durable receipts first and resume only incomplete steps. Do not blindly replay large reads/writes; follow the Red Dog bounded-retrieval/checkpoint rule.

## Regression incidents locked by this protocol

- Generic `Michael Trout` search produced unrelated LinkedIn identities; canonical key is now `UnDaoDu Michael J Trout` plus the verified `openstartup` URI.
- A city email required an immediate same-thread correction to **Jorge Sabastian**; named-entity canonicalization is now mandatory before send.
- A previously closed Fukui City personal route was reused by another workflow; blocked routes must be enforced across all send-capable paths.
- Stream/tool-output interruption must resume from provider receipts rather than re-running the whole chain.

## Privacy and authority

This protocol stores process, source names, stable public URLs, and truth-boundary rules. It does not store private recipient addresses, home addresses, or BCC lists. It grants no independent authority to make legal/financial commitments or publish new campaign positions; those remain subject to the parent skill's AUTO / DRAFT / ESCALATE contract and current principal authorization.
