# Japan Hyperscaler Report (JHR)

Japan Hyperscaler Report is the eSingularity evidence and publication lane for tracking Japan's hyperscale data-center buildout, policy, grid constraints, local response, and implications for distributed Community-Owned Green Data Centers (COG DC).

## Purpose

JHR answers one recurring question: **is there enough new verified evidence to justify a public report?**

It is not a content mill. A run may legitimately produce `NO_REPORT`.

## Scope

- National policy: METI, MIC, GX Strategy Areas, Watt-Bit coordination, OCCTO, grid planning.
- Prefectural and municipal decisions affecting hyperscale data centers.
- Chiba/Inzai as the primary reference cluster.
- New campuses, land conversion, power demand, transmission/substation expansion, water and heat issues.
- Resident, farmer, landowner, temple/shrine, neighborhood, and municipal responses where verifiable.
- Comparison with U.S. hyperscale clustering where it helps test the eSingularity/COG DC thesis.
- Fukui opportunity: what can be learned before a hyperscale land rush arrives.

## Truth boundary

Every publishable claim must carry provenance. JHR distinguishes:

1. `OFFICIAL` — government, utility, company filing, planning document.
2. `REPORTED` — reputable journalism or attributable interview/reporting.
3. `COMMUNITY` — petitions, council testimony, resident groups, local organizations.
4. `ANALYSIS` — JHR interpretation based on cited evidence.

Unverified claims are retained as leads and are never promoted as facts.

## Significance gate

A report is publishable when at least one high-signal event is verified, for example:

- new national/prefectural DC policy or regulation;
- hyperscale campus announcement or cancellation;
- material grid/substation/transmission decision;
- zoning or land-use change driven by DC growth;
- significant resident/community action;
- a material change in Fukui's competitive position;
- a new pattern that changes the COG DC thesis.

Routine repetition, vendor marketing, duplicate stories, and weakly sourced claims do not pass the gate.

## Primary website and derived social editions (2026-10-13)

The **eSingularity.ai JHR website article** is the primary public edition. The JHR repository report and rendered frontend route must be reconciled as one source change; the live website issue (currently a `/reports/jhr#jhr-NNN` anchor) becomes downstream publication authority **only after** the existing deployment succeeds and the actual public issue is independently read back. LinkedIn's Japan Hyperscaler Report newsletter is a **secondary derived edition** of that live website piece, not an independent authoritative original. Newsletter edition numbering may differ from site issue numbers.

Publication path: evidence and significance -> website content and review -> production source/release and live URL verification -> bounded handoff through `../skills/website-update/SKILL.md` and `modules/platform_integration/linkedin_agent/skillz/linkedin_jhr_newsletter/SKILLz.md` -> exact authorized LinkedIn publication -> permalink readback. A site layout/ticker/SEO-only update or `NO_REPORT` triggers **no newsletter**. Missing authentication, publishing approval or uncertain delivery stops only the downstream stage, not the already verified website article. No unattended LinkedIn publisher is claimed to be installed.

## Version-controlled publication archive

[`manifest.json`](manifest.json) is the issue identity and dated verification
index for #001–004. It records titles, languages, source Docs where recovered,
repository owners and immutable snapshots, public URLs, platform states,
verification times and scoped evidence. It is a static archival record, not a
publisher or a replacement for the private editorial master.

| Issue | Existing content owner | Website, checked 2026-11-16 | LinkedIn, checked 2026-11-16 |
| --- | --- | --- | --- |
| #001 | [Report](reports/JHR_001_2026-09_JAPAN_HYPERSCALER_REPORT.md); [rendered source](../frontend/app/reports/jhr/page.tsx) | VERIFIED_LIVE; main 09-10, addendum 09-12 | VERIFIED_LIVE; 09-14 |
| #002 | [Rendered source, single owner](../frontend/app/reports/jhr/layout.tsx) | VERIFIED_LIVE; dated 09-14 | VERIFIED_LIVE; 09-16 |
| #003 | [Report](reports/JHR_003_2026-09_AI_RICE_FIELDS_AI_KOBAN.md); [rendered source](../frontend/app/reports/jhr/layout.tsx) | UNVERIFIED; absent from inspected served archive; historical live report retained | VERIFIED_LIVE; 09-29 |
| #004 | [Draft pointer](drafts/JHR_004.md); same authoritative Doc | UNVERIFIED; not found in inspected public archive | UNVERIFIED; not found in public series; private drafts/schedule unavailable |

The [2026-11-16 receipt](PUBLICATION_AUDIT_20261116.md) describes the source/live
discrepancy and verification limits. A URL fragment can load the archive without
its issue existing: verify the matching issue content and actual anchor. Website
dates are visible labels, not verified first-publication timestamps. Current
public LinkedIn modification dates and exact revision equality remain unverified.

Retain #001 and #003 manuscripts in place. #002 is already version-controlled in
the reader layout; index it there instead of copying a second manuscript. The
manifest freezes its Git blob and revision URL. Preserve citations and assets in
their existing owners. Drafts stay outside `reports/`; #004's content remains in
its existing native manuscript so accepted edits and historical v1 are preserved.
Do not copy editorial feedback, approvals, mail bodies, recipients or private
master-log history into this public archive. Issue-specific source Doc links are
included for this explicitly requested source manifest; that is not permission
to expose other private documents or change access.

When updating the archive, reconcile site first, then LinkedIn. Read the actual
source, exact public issue and platform history, retaining conflict/coverage
fields. Use `null` plus a reason for unrecovered source Docs or unverified URLs;
do not guess. Keep issue numbers stable and revisions within the same issue.
Preserve legacy conflicting proposals through immutable source references in
`historical_proposals`, without treating them as additional numbered editions.
Keep prior observations in Git history; update the private master newest-first
beneath fixed instructions with a concise receipt and PR/main reference.

## Red Dog JHR workflow

The existing [JHR skill](../../../../.claude/skills/japan_hyperscaler_report/SKILL.md)
owns audit, research, revision and archival coordination. The website remains the
canonical public issue. The existing
[LinkedIn child](../../../platform_integration/linkedin_agent/skillz/linkedin_jhr_newsletter/SKILLz.md)
owns Japanese downstream placement. English Substack is a separately approved
edition whose account, publication, source revision, translation and delivery must
be verified. Reddit supplies discussion and research leads, not automatic posts.
No configured account, unattended cross-posting or subscription delivery is proved
by these instructions. Exact outward approval and platform receipts remain gates.

## Runtime contract

`run_jhr_cycle()` returns a structured result with:

- evidence ledger;
- significance score;
- `publish` boolean;
- reason for publish/no-publish;
- draft metadata when publishable;
- WSP_97 evidence references.

The runtime is designed to be called from FoundUps startup/orchestration without blocking the interactive CLI. Public publishing remains fail-closed until the source and publication adapters are connected and verified.


## Japan AI infrastructure flow ledger

`data/japan_ai_infrastructure_flows.json` is the official-source seed for YUMORI's Japan infrastructure dependency analysis. It records directed asset, compute, technology, network, government-program and heat-reuse relationships. Unknown monetary amounts remain `null`; the ledger is deliberately incomplete and must not be represented as a market-wide map.

The calculation lives in `../src/yumori_economic_model.py`. JHR owns evidence/provenance; the YUMORI Economic Model owns project calculations. Neither surface converts a relationship into YUMORI revenue, committed financing, or a public market-score claim.
