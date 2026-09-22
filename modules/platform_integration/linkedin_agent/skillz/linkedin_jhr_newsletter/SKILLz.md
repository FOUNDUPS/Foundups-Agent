---
name: linkedin_jhr_newsletter
description: Research, significance-gate, draft, maintain and publish the Japan Hyperscaler Report LinkedIn newsletter from the canonical eSingularity JHR evidence lane
version: 1.1.0
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
   Historical continuity identifies Japan Hyperscaler Report under FOUNDUPS®,
   series 7505133867079536640; this is a discovery lead, not fresh live state.
3. Respect the JHR significance gate. A cycle may correctly produce `NO_REPORT`.
   Vendor repetition, weak sourcing or a duplicate story does not justify an edition.

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
