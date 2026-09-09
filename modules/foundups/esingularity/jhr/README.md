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

## Runtime contract

`run_jhr_cycle()` returns a structured result with:

- evidence ledger;
- significance score;
- `publish` boolean;
- reason for publish/no-publish;
- draft metadata when publishable;
- WSP_97 evidence references.

The runtime is designed to be called from FoundUps startup/orchestration without blocking the interactive CLI. Public publishing remains fail-closed until the source and publication adapters are connected and verified.
