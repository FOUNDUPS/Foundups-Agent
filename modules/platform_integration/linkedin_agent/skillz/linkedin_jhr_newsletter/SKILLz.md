---
name: linkedin_jhr_newsletter
description: Research, significance-gate, draft, maintain and publish the Japan Hyperscaler Report LinkedIn newsletter from the canonical eSingularity JHR evidence lane
version: 1.3.0
author: 0102
agents: [qwen]
intent_type: CONTENT_GENERATION
promotion_state: prototype
category: workflow
evals: []
---
# Japan Hyperscaler Report newsletter

Read the [newsletter router](../linkedin_newsletters/SKILLz.md) and [master
routing contract](../../docs/LINKEDIN_ACTIVITY_ROUTING.md). This skill owns only
the Japan Hyperscaler Report (JHR) LinkedIn lane. It does not own general Project
eSingularity Page articles or YUMORI.me campaign posts.

## Source, identity and significance gate

1. Read `modules/foundups/esingularity/jhr/README.md`, the report index/current
   reports, evidence ledger/runtime result and the current public JHR route. Reconcile
   repository, site and LinkedIn editions before assigning an issue number.
2. Verify the live newsletter series, publisher, latest edition, drafts and schedule.
   The 2026-09-22 live reconciliation confirmed Japan Hyperscaler Report under
   FOUNDUPS®, series 7505133867079536640, with LinkedIn editions published on
   September 14 and September 16. Treat this as a continuity anchor and refresh it
   before editing or publishing. Do not assume LinkedIn edition numbers and the
   repository/site JHR report numbers are interchangeable.
3. Respect the JHR significance gate. A cycle may correctly produce `NO_REPORT`.
   Vendor repetition, weak sourcing or a duplicate story does not justify an edition.

## Website-first canonical publication gate — 2026-10-13

**Ordering is mandatory for JHR:** verified evidence -> approved JHR repository/site issue -> eSingularity.ai production deployment -> `WEBSITE_LIVE_VERIFIED` for the exact `https://esingularity.ai/reports/jhr#jhr-NNN` issue -> derived LinkedIn newsletter edition -> authorized LinkedIn publication and permalink readback. Check the current real issue anchor; the URL shape is an example, not proof that every `NNN` exists.

The canonical public source of JHR facts and long-form copy is the **live eSingularity.ai article**, not a separately edited LinkedIn manuscript or Google Docs draft. The repository owns research/evidence and website source. A Google Docs master is for drafting and continuity; it does not supersede published website text. In `jhr` website publications follow `modules/foundups/esingularity/skills/website-update/SKILL.md`.

Required upstream receipt before LinkedIn placement:

- issue key and **exact live issue URL** (not only the JHR index);
- website source revision, production deployment receipt and independently verified public content/date;
- stable issue/content identity (e.g., a verified source hash or exact website revision);
- authorized LinkedIn publisher/series, destination-specific approval, and existing LinkedIn article/draft/scheduled search.

Use the live website article as the **sole editorial source** for the LinkedIn version. Adapt headline/length/format for LinkedIn and include the canonical website backlink, but introduce no new claims, figures, photos, endorsements or implications without first updating and verifying the website article. Preserve the article's provenance distinctions and Japanese-first direction. LinkedIn edition numbering is **not** guaranteed to equal website issue numbering. Match by canonical source URL and issue identity; do not create duplicate editions after a retry or minor website edit.

A newly published JHR website issue advances to `LINKEDIN_READY` only after the website receipt and appropriate approval. An ordinary website edit, unfinished rollout or `NO_REPORT` must **not** trigger newsletter publishing. If the existing authorized publishing route/browser cannot publish, retain `WEBSITE_LIVE_VERIFIED / LINKEDIN_BLOCKED` with next actor. Neither this skill nor a website commit proves that a running automatic publisher exists.

## Japan research coverage

Read the [shared verification contract](../linkedin_newsletters/references/research-verification.md).
Search in Japanese first and English for corroboration, with a declared cutoff and
since-last-issue window. Cover national policy (METI/MIC/GX/Watt-Bit), prefectural
and municipal plans/council records, operator filings and project phases, utilities
and grid/land/water/heat constraints, resident concerns/petitions/protests and
operator responses, plus relevant research papers. Search Japan broadly before
choosing cases; Tokyo/Osaka, Inzai/Chiba, Tsukuba, Hokkaido, Tohoku, Kyushu and
Fukui are search prompts, not claims that events occurred in each place.

Combine データセンター / ハイパースケール / AIデータセンター with 地域名,
反対運動 / 住民説明会 / 請願 / 議会 / 騒音 / 排熱 / 電力 / 水 / 系統接続.
For protests record who, where, when and the stated demand; verify original group
statements, council/petition records and attributable reporting. Never equate a
small group's view with all residents, or a hearing with a protest. Include
benefits, counterarguments and project responses. Search J-STAGE, CiNii Research,
university repositories and paper publishers; read methods before citing findings.

Use Google/Gemini/YouTube for discovery subject to the shared access and provenance
rules; summaries cannot replace the source. Mark categories checked/no material
change/unavailable. Rank admitted findings with WSP 15, explain narrative order,
and connect to eSingularity.ai only through a relevant disclosed regional case.

## Evidence and editorial contract

Use current primary evidence for Japanese data centers, grid/power, water/heat,
land, policy, employment, compute access, ownership and regional returns. Classify
claims using the canonical JHR provenance boundary: `OFFICIAL`, `REPORTED`,
`COMMUNITY` or `ANALYSIS`. A headline, search snippet or TV recollection is a lead.

Distinguish announced from operating capacity; electrical MW from compute output;
facility ownership from cloud/model ownership; forecast from measured effect; and
project advocacy from sourced reporting. Apply the same ownership/benefit questions
to domestic and foreign operators. Disclose FOUNDUPS' interest when connecting the
evidence to the proposed Project eSingularity/COG DC alternative. Do not imply city
approval, financing, installed equipment, guaranteed returns or achieved sentience.

Prepare natural Japanese and an English review version when requested. Keep a JHR
newsletter edition distinct from an eSingularity Page article and the monk's personal
reshare. Use **YUMORI.me** exactly only when the civic project is relevant. Use the
rice-field or kōban analogy only as clearly labeled explanation, never as a measured
unit or evidence.

## Completion

Track the shared newsletter stages. Route exact approved content through
`linkedin_publishing`; verify the byline/series, saved body, scheduling confirmation,
matching queue entry and live permalink independently. Record provenance, report
number, publication state and next monitored signal in the established JHR/project
continuity surface. `NO_REPORT` is a complete researched outcome, not a failure.
