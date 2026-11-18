---
name: japan-hyperscaler-report
description: Audit, research, develop and archive Japan Hyperscaler Report issues through the existing Red Dog JHR lane, with website-first Japanese LinkedIn distribution, separately approved English Substack editions and Reddit research.
---
# Japan Hyperscaler Report Skill

## Identity

Series: **Japan Hyperscaler Report (JHR)**
Owner FoundUp: `esingularity_001`
Canonical module: `modules/foundups/esingularity/jhr`
Primary public surface: `eSingularity.ai`
Canonical movement links: `https://yumori.me/` and `https://yumori.info/`

For public series names, website report links and movement calls to action, read **Shared branding and language — both sites** in `modules/foundups/esingularity/skills/website-update/SKILL.md`. That section owns the Japanese katakana JHR title and YUMORI.me branding; explanatory context must not replace either brand. This reference does not change the research or publication gate below.

## Objective

Research Japan's hyperscale data-center expansion and publish only when a verified development materially changes the picture for Japan, Chiba/Inzai, Fukui, or the distributed COG DC thesis.

## Red Dog orchestration and durable archive

Use the existing JHR owner; do not create another newsletter operator or issue
database. Read [the archive and workflow](../../../modules/foundups/esingularity/jhr/README.md)
and its `manifest.json` before assigning issue numbers or selecting a manuscript.
Treat the manifest as a dated evidence index, not live platform state or runtime
authority. A publication audit does not authorize posting or manuscript rewriting.

Resolve the requested mode: **audit**, **research/develop**, **revise**, **archive**,
or an explicitly authorized **publish/schedule** operation. Reuse the stable master
and issue Doc from authorized private continuity; read the whole relevant issue
and current master before editing. Preserve accepted text, citations, native
structure and revision history. Keep unapproved drafts separate from historical
published issues; a draft's presence does not prove delivery.

Carry a bounded work packet: issue identity, mode, owner, source/revision,
evidence cutoff and coverage, exact approval scope, destinations/languages,
acceptance checks and next actor. Return observed artifacts, platform receipts,
verification time, unresolved gaps and the next action. Use WSP 00/97; use WSP 99
for machine handoffs and WSP 110 draft guidance for the repository lifecycle.

Channel roles:

- **Website:** canonical public issue; verify the actual issue content and anchor.
- **LinkedIn:** Japanese distribution through `linkedin_jhr_newsletter`, after
  verified website publication. Preserve existing bilingual historical editions.
- **Substack:** English edition, separately prepared from the approved issue.
  Verify the actual account/publication, current draft/archive/schedule and exact
  approved translation. Setup is not publication authority or proof of readiness.
- **Reddit:** research and discussion channel. Read original threads and community
  rules; treat claims as leads and verify underlying sources. Do not automatically
  cross-post, comment, message, or turn private community content into an article.

Keep the explicit **website -> LinkedIn** sequence unless 012 changes it. Substack
setup or research must not silently replace the canonical source or reorder this
audit. Every outward action needs its exact manuscript/destination approval and
platform verification; a skill invocation or approved architecture is insufficient.
Reconcile uncertain submissions before retrying. This skill update installs no
dispatcher, subscription service, credentials, scheduled task or posting daemon.

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

Japanese is the default public language. Publish a complete English secondary version only when 012 explicitly requests a bilingual issue or English public edition. An explicit 012 instruction to publish a Japanese-only issue overrides the legacy bilingual pattern. Preserve already-published bilingual archive issues unless a separate correction is requested. Public JHR surfaces must link back to `YUMORI.me` and `YUMORI.info`.

## Website-first / LinkedIn-secondary distribution gate — 2026-10-13

A qualified JHR issue publishes **to eSingularity.ai first**. Reconcile the canonical JHR research/report with the rendered website issue; complete the existing production release and independently verify the actual public issue URL/anchor and content before any LinkedIn newsletter placement. Follow the site release skill (`modules/foundups/esingularity/skills/website-update/SKILL.md`), then hand the website receipt to `modules/platform_integration/linkedin_agent/skillz/linkedin_jhr_newsletter/SKILLz.md` and `linkedin_publishing`. LinkedIn is derived distribution from the website and links back to the canonical issue, not a second fact owner. `NO_REPORT`, site-only CSS/ticker fixes, blocked deployment or duplicate issue do not trigger LinkedIn. A site deploy never itself proves LinkedIn submission or gives unattended publishing permission.

## Image policy

Prefer official maps, aerial/satellite context, planning maps, grid diagrams, and operator campus images with clear provenance. Do not fabricate a real aerial view. Generated diagrams must be labeled as illustrations.

## Runtime

Use `modules/foundups/esingularity/jhr/scripts/launch.py` for one assessment cycle. The research retriever is injected by orchestration. Publication remains fail-closed until the adapter is verified.

## Publication failure prevention and Pub DAE coordination

Before a publication handoff, reconcile the entire current JHR master **and the
relevant YUMORI moshpit/website release history**, including old unresolved work,
issue2126 and current Sites source/version/deployment state. Retrieve the stable
private ledgers through authorized continuity; never copy unrelated private text
to Git. A recent-message window or summary is insufficient to close an older
release blocker. If a required ledger cannot be read, preserve that coverage gap.

Carry independent editorial, approval, archive, build/deployment, exact live
website, derived-edition and amplification states. Bind the manuscript revision
and SHA256, archive commit, Sites build-source commit, exact issue URL/body,
platform/locale/destination approval, provider permalink and readback time.
Source merged, Sites saved, deployment succeeded and exact issue live are
different observations. Preserve conflicts and all open owner/next-action work
until its actual receipt is recovered. Existing LinkedIn #003 requires readback,
never a new post to compensate for its website gap. #004 remains a draft until
012 approves its exact current manuscript and destinations.

Use the existing SOCIAL command `social campaign content action=reconcile
dry_run=true packet='<inline JSON>'` and its
[receipt contract](../../../modules/platform_integration/social_media_orchestrator/docs/CONTENT_CAMPAIGN.md#publication-reconciliation--2026-11-16)
to expose missing handoffs. This implemented helper consumes supplied evidence
only and emits no publication grant or memory write. Do not claim its matching
hashes authenticate a receipt, or feed its proposed projection into a verified
outcome sink without the existing authenticity owner.

Pub DAE is this coordination role across existing owners. Research/Reddit
discussion leads -> approved manuscript -> repository archive -> website release
and exact live verification -> Japanese LinkedIn and separately approved English
Substack -> approved social amplification through the existing SOCIAL DAE.
Any Reddit submission is a separately approved community-specific artifact,
after rules/account/schedule/duplicate checks; no automatic cross-posting is
installed. Preserve the current website -> LinkedIn requirement. Preparation,
translation, setup and workflow approval never authorize external placement.

After each authorized stage, record a minimal receipt newest-first beneath each
relevant master's fixed instructions: issue/revision/hash, exact destination,
observed stage/result/time, source receipt, owner/blocker/next action and PR/main.
Read back the insertion and preserve native formatting/history. A Brain/Memex
write additionally requires the governed sink acknowledgement and scoped
readback. Without those, report ingestion NOT_ATTEMPTED or UNVERIFIED. Keep the
open-work packet explicit so later editorial success cannot erase a release gap.
