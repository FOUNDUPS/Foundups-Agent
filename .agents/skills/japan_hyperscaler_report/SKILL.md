# Japan Hyperscaler Report Skill

## Identity

Series: **Japan Hyperscaler Report (JHR)**
Owner FoundUp: `esingularity_001`
Canonical module: `modules/foundups/esingularity/jhr`
Primary public surface: `eSingularity.ai`
Canonical movement links: `https://yumori.me/` and `https://yumori.info/`

## Objective

Research Japan's hyperscale data-center expansion and publish only when a verified development materially changes the picture for Japan, Chiba/Inzai, Fukui, or the distributed COG DC thesis.

## Research order

1. Official Japanese government and utility sources first.
2. Prefecture and municipal planning, council, zoning, and press-conference records.
3. Operator/infrastructure company primary sources.
4. Reputable Japanese and international reporting.
5. Community evidence: petitions, resident groups, agricultural/landowner organizations, temple/shrine or neighborhood responses when attributable.
6. Analysis only after facts are separated from interpretation.

## Core watchlist

- METI / MIC / Cabinet GX policy
- Watt-Bit coordination
- GX Strategic Areas
- OCCTO demand forecasts
- TEPCO / regional utilities / substations / transmission
- Chiba and Inzai
- Hokkaido, Akita, Miyagi, Tochigi, Ibaraki, Toyama, Kagawa, Fukuoka, Kagoshima and later candidate regions
- all 47 prefectures for material policy changes
- Fukui Prefecture and Fukui municipalities
- hyperscale campus announcements, acquisitions, cancellations, delays
- land conversion, farmland, forest, temple/shrine, community and neighborhood effects
- zoning, environmental review, water, noise, heat, grid queues
- local tax, employment, education and public-benefit commitments
- U.S. clustering patterns only when they illuminate a Japan decision

## Publication gate

Do not publish merely because a cycle ran.

Publish when verified evidence shows a material change such as:

- national or prefectural policy change;
- major hyperscale campus development;
- material power/grid decision;
- zoning/regulatory action;
- significant community response;
- material change to Fukui's strategic position;
- evidence that strengthens or weakens the distributed COG DC hypothesis.

If the evidence is weak, repetitive, unverified, or non-material, emit `NO_REPORT` and retain leads for later verification.

## WSP_97 truth boundary

Every report must visibly distinguish:

- `OFFICIAL`
- `REPORTED`
- `COMMUNITY`
- `ANALYSIS`

Never transform a lead into a fact. Never describe publication as completed without the publication adapter returning evidence of success. Never imply that a site, API, crawler, image system, social distribution, or newsletter delivery is connected unless that connection has been verified in the current runtime.

## Report structure

1. Headline / central change
2. What changed
3. Evidence
4. Chiba/Inzai signal
5. Community/land-use signal
6. Fukui implication
7. COG DC implication
8. What JHR is watching next
9. Primary sources
10. SEO tags / hashtags

Japanese is always the primary public language. Every public JHR report or material update must include a complete English secondary version after the Japanese content. Public JHR surfaces must link back to `YUMORI.me` and `YUMORI.info`.

## Image policy

Prefer official maps, aerial/satellite context, planning maps, grid diagrams, and operator campus images with clear provenance. Do not fabricate a real aerial view. Generated diagrams must be labeled as illustrations.

## Runtime

Use `modules/foundups/esingularity/jhr/scripts/launch.py` for one assessment cycle. The research retriever is injected by orchestration. Publication remains fail-closed until the adapter is verified.
