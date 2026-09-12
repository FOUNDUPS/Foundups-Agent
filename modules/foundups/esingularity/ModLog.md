# Project eSingularity ModLog

## 2026-09-12 — Question-led opening, first-slide review

- Recovered the original demolition/reuse concept, added the requested excavator, and replaced baked figures with Japanese-first live copy plus English and Brazilian Portuguese translations.
- The root hero and first vision slide ask whether to demolish the community's heart, show the narrowly sourced approximate ¥1.58B estimate, and link to the existing committee form. Full-screen deep links pause autoplay.
- Preserved subsequent content, YUMORI.me route/domain behavior and JHR. Moved the existing hero map into a disclosure to shorten the opening.
- Traced repository ledger to the updated integrated financial workbook, functional model and master prospectus; documented conflicting model generations without publishing unaudited returns or aggregating cost categories.
- Review and verification record: `docs/OPENING_REVIEW_20260912.md`. Routing: 18 passed; focused changed-file lint passed. Existing TypeScript baseline issues and an incomplete production build remain before merge. Awaiting 012's first-slide visual validation; not deployed.

## 2026-09-12 — Make the two-homepage architecture durable

**WSP Protocol**: WSP 00, WSP 22, WSP 50, WSP 57, WSP 83, WSP 97
**Phase**: Documentation and regression hardening

- Made the one-project/two-public-experience architecture prominent in README, INTERFACE, ROADMAP, and test documentation: eSingularity.ai owns the project/vision homepage; YUMORI.me owns the movement/join homepage.
- Added explicit merge and deployment gates so parallel work on either landing cannot overwrite or absorb the other, while retaining the single monorepo frontend and Sites project.
- Refreshed the existing YUMORI content tests to match the restored join-first page and paired them with the existing hostname-routing tests.
- Fresh focused validation: 18 Node routing checks and eight Python YUMORI/JHR contract functions passed. The environment lacks `pytest`; the broader direct runner still reaches the pre-existing missing legacy `frontend/content/yumori-presentation.ts` reference outside this documentation slice.
- Made no frontend, DNS, hosting, or YUMORI.info forwarding change. This slice is designed to coexist with independent eSingularity.ai redesign work.
- HoloIndex retrieval was attempted first but returned `MISSING_GENERATION_BINDING`; repository-local WSP and module evidence was used as the documented fallback.

## 2026-09-12 — Restore the join-first YUMORI committee landing

- Restored the exact three-panel national movement funnel from PR #1653 at `frontend/app/yumori/page.tsx`: WHY / WHAT / HOW, five JOIN YUMORI actions, the Japan Hyperscaler Report link, and the initial 1,000-person committee target.
- Preserved the hostname-restricted rewrite, eSingularity.ai homepage, direct `/yumori` route, signup destination, assets, language infrastructure, and the single shared Sites project. No DNS or YUMORI.info change was made.
- Focused ESLint completed with zero errors (one retained `no-img-element` warning), and the Sites production build completed successfully.
- Published Sites source `21a8d0161c2bc2fc8b9ca3c8f510225aae3ae3a3` as version 44; deployment `appgdep_6aa569bcb5688191b13efe46e738346e` succeeded.
- Fresh cache-busted HTTP and Cloud Browser checks confirmed YUMORI.me and www show the restored movement page while keeping their hostnames and query strings; eSingularity.ai remains the project/vision homepage. YUMORI.info's existing HTTP redirect still points to `https://eSingularity.ai`; its DNS/forwarding was not modified.


## 2026-09-12 — Separate YUMORI.me entry on the shared Sites app

- Selected one existing hosting project with hostname routing instead of a second deployment or copied campaign page.
- Added a host-restricted `beforeFiles` rewrite in `frontend/next.config.ts`: only YUMORI.me/www `/` maps internally to the existing `/yumori` route. eSingularity.ai's project page and the existing YUMORI.info redirect remain untouched.
- Left page content, assets, JHR, signup destination, Sites project ID, D1 binding and DNS unchanged. The inspected service worker already uses network-only navigation; no speculative cache fix was added.
- Updated this module's INTERFACE hosting/domain contract and test documentation so subsequent sessions recover the separation from repository truth.
- Added dependency-free Node configuration checks and connected them to the existing validation workflow. Fresh local run: 18 passed. The reconciled production frontend also completed the Sites production build. Full lint still reports four pre-existing presentation/accessibility errors plus five image warnings outside this routing slice. The Python module suite reports 20 passed and five stale contract failures against the newer production homepage/presentation/JHR structure; none exercises or fails the hostname rewrite.
- Reconciled the Foundups branch with the newer Sites production source (`14efff19f8d7bc0eefcf2ee7a2cb41a12cf9f0bb`) before applying the routing patch, preventing a rollback of the current homepage, Fukui map, JHR, language, performance and public FAQ work.
- Published the exact routing source (`b8bd40eb82475bccba0507a17167cfc2c8b21cc3`) as Sites version 43; deployment `appgdep_6aa556c60e588191aafe94caef929fe6` completed successfully on the existing public eSingularity project.
- DNS was not changed. Sites already reported eSingularity.ai, www.eSingularity.ai, YUMORI.me and www.YUMORI.me active with active SSL; public YUMORI.me apex A and www CNAME records matched the platform-supplied targets. YUMORI.info was not modified.
- Fresh cache-busted production checks returned the YUMORI page at YUMORI.me and www while retaining each hostname and query string, retained the project homepage at eSingularity.ai, and retained YUMORI.info's redirect to eSingularity.ai. Direct `/yumori`, JHR, signup destination, representative assets and mobile-user-agent responses remained healthy.

## 2026-09-11 — Real-building full-screen YUMORI vision deck

- Replaced the presentation renderer with the revised ten-slide vision based on 012's photographs of the actual former Sukatto Land Kuzuryu building rather than a generic greenfield resort.
- Kept eSingularity.ai as the canonical vision surface and YUMORI.me as the movement/join surface; the final deck action routes to YUMORI instead of duplicating a second independently maintained deck.
- Added full-screen 16:9 presentation mode, touch swipe, previous/next, direct slide selectors, optional nine-second progression, reduced-motion handling, keyboard Left/Right/Escape, and `?vision=1&slide=N#yumori-deck` deep links.
- Packed the ten approved concept slides into one optimized vertical sprite at `frontend/public/vision/vision-sprite.jpg`; structured Japanese-first text/evidence remains in `frontend/content/yumori-vision.ts` for accessibility, search, translation and RedDog grounding.
- Preserved whole-slide rendering with no text cropping and kept bathers inside screened/private onsen areas rather than public event circulation.
- Added the revised program: 24-hour onsen concept, B1 gym/rest/recovery, D-K-inspired night activation, COG DC heat-reuse candidates, 60 FoundUps with maximum three humans per team, local problem-to-FoundUp agriculture, and Fukui distributed-compute prototype.
- Kept Slide 02 accounting categories separate: reported ~¥1.58B demolition estimate, verified 129,649 FY2018 users, modeled ~¥5.37B five-year revenue and modeled ~¥1.94B cumulative five-year FCFE. These are not forecasts or guarantees and are not added together as one return measure.
- Added `docs/YUMORI_VISION_DECK_20260911.md` and updated `INTERFACE.md` so future agents can recover the visual, domain, evidence, financial and D-K truth boundaries without relying on chat history.
- Updated existing contract coverage for the sprite, full-screen/deep-link controls, current ten-slide spine and retained public-source boundaries.

## 2026-09-06 — Japanese-first YUMORI cinematic presentation

- Added a mobile-first ten-slide presentation immediately below the existing hero, without replacing the page shell or campaign sections.
- Added exactly one `NEW` presentation link to the existing ticker and preserved every existing ticker destination.
- Established `frontend/content/yumori-presentation.ts` as the Japanese canonical content boundary with complete derived English and Portuguese states.
- Added timed progression, explicit pause, previous/next and slide controls, touch swiping, interaction pause, reduced-motion handling, and progressive evidence disclosure.
- Replaced the old floor allocation with the lower-public / third-floor emerging FoundUps / top-floor advanced FoundUps ladder, with the COG DC shown as separate infrastructure.
- Corrected generic “regional compute” language to our COG DC compute used by the people and projects working there.
- Added two generated concept visuals for the compute-field and autonomous-agriculture slides; all other visuals reuse existing project assets or native diagrams.
- Preserved the deployed campaign action and economics surfaces, including their benchmark disclosure and language mappings.
- Repaired the corrupted `/future` route and removed the speculative capacity timeline in favor of evidence-gated demand, engineering, and economics validation.
- Researched five current Fukui academic/technical outreach candidates from official public sources. Stored the governed candidate record in the ignored RedDog manual-alpha location; no private contact data entered public Git.
- Validated production build, lint, twelve contract tests, all ten slide states, Japanese/English/Portuguese switching, internal anchors, touch-width layout, and external links.

## 2026-09-01 — Learn, Create, Launch language pass

- Reframed the Innovation Hub floors as a clear progression: Gather, Learn, Create, Launch.
- Tightened the English education copy around parent- and teacher-guided AI learning, regional problem-solving, and launching projects and startups in Fukui.
- Preserved Japanese as the canonical source, added equivalent Portuguese copy, and verified every Japanese landing-page text node has a translation entry.
- Normalized campaign-heading typography so emphasized English lines retain the same font family, style, weight, and spacing.
- Removed the abstract demolition-choice diagram and made the five community outcomes the focus: onsen, learning and launch, local compute, food entrepreneurship, and D-K culture.
- Kept the rotenburo scale as an explicitly stated ambition, and kept recovered-heat use subject to technical testing.
- Extended language switching to image alt text so English and Portuguese accessibility copy no longer remains Japanese.
- Rebuilt the stakeholder section as a native mobile-responsive campaign sequence instead of a pasted image: stop demolition, assemble the COGDC coalition, align landowners, prepare a City-ready alternative, define university use, and secure customers and operating partners.
- Reframed visitor economics around proven demand and direct spending, moved the illustrative 30-year total behind progressive disclosure, and added the unquantified supplier, income, employment, and tax-analysis stages required by Fukui's official input-output method.

## 2026-09-01 — Public visual-reference audit

- Replaced the oversized Hasegawa portrait treatment with a real D-K work preview from the artist's official gallery and a compact 52-pixel artist identity.
- Added a linked photographic reference to Awara Onsen's official Yukemuri Yokocho site so residents can see the local model behind the container-food concept.
- Kept both examples secondary to the campaign story, translated the link labels, added keyboard focus states, and retained the D-K proposal label so past work is not mistaken for a completed Sukatto Land installation.

## 2026-09-01 — English campaign economics and translation integrity

- Reframed the English building-history section as a value-at-stake campaign argument: original construction, indexed construction-cost reference, demolition estimate, and verified FY2018 use.
- Updated the visitor-spending screen to Fukui Prefecture's 2025 official day-trip benchmark (¥5,546) and added a clearly labeled, undiscounted 30-year direct-spending scenario.
- Kept asset value, demolition spending, direct visitor spending, compute revenue, and input-output multiplier effects separate to avoid invalid addition of stocks and flows.
- Completed the missing English strings for the choice, five-part future, and AI Rice Field sections so Japanese no longer leaks into those English views.
- Added contract coverage for English AI Rice Field copy and the visitor-scenario arithmetic.

## 2026-08-31 — Fukui-specific compute and visitor-economy story

- Replaced the generic “return on compute” cards with four Fukui-specific, officially sourced stories: local AI education, smart agriculture, prefectural satellite Suisen, and regional manufacturing.
- Tightened the English campaign line to “The future runs on compute. Fukui energy → Fukui compute → Fukui’s future.” and aligned the Portuguese translation.
- Reframed the building story around who controls the compute that will power Fukui’s next 30 years.
- Added a mobile-first direct-spending screening scenario based on the verified FY2018 attendance and Fukui Prefecture’s 2024 day-trip tourism-spending benchmark.
- Labeled the scenario as not a forecast, excluded multiplier effects and unrelated project revenues, and avoided an unsupported “Japan’s largest” outdoor-spa claim.
- Added contract coverage for official local sources, multilingual copy, transparent arithmetic, and overclaim prevention.

## 2026-08-31 — Community future and opt-in soundtrack

- Replaced the long hero paragraph with a four-sentence campaign statement centered on public choice, the onsen, learning, startups, and local compute heat.
- Added an opt-in `0102 MUSIC` control using the project-owned “9 Dragon Heads” track; playback fades and pauses after the hero leaves the viewport and never autoplays.
- Added a mobile-first, explicitly labeled concept section showing a one-sided rotenburo, an Awara-inspired container food court, and a proposed D-K night experience.
- Removed the generated aerial render and replaced it with 012's supplied `SateliteView.jpeg` site concept, the supplied `ConceptOnsen.jpg` future image, and the supplied Akira Hasegawa portrait. Each concept image is labeled so it cannot be mistaken for completed construction.
- Described the compute-heated rotenburo as an ambition to become Japan's first, not a verified uniqueness claim, and retained engineering-validation language.
- Recast the four-floor concept as Ground Floor through 4th Floor with community, school, university, research, and startup uses.
- Removed landing-page sections 08–10 (team preview, internal action plan, and source portal) while retaining the dedicated Team route and the public LINE conversion.
- Replaced remaining numeric journey labels with plain-language WHY / WHAT / HOW / WHEN cues.
- Added multilingual and asset-presence contract coverage for the new public journey.

## 2026-08-31 — Campaign-first hero headline

- Replaced the literal, passive English translation “This onsen—before we destroy it.” with the active campaign message “Save the Onsen. Revitalize the Community with Local Compute.”
- Updated the Japanese canonical headline and Portuguese translation to preserve the same meaning across all three languages.
- Added a contract test that prevents the hero translations from drifting apart.

## 2026-08-30 — FoundUp monorepo migration

- Migrated the existing live Sites PWA from the untracked nested `sites/esingularity-ai` checkout into `modules/foundups/esingularity/frontend`.
- Preserved the existing Sites project ID, D1 declaration, routes, assets, lockfile, and public behavior.
- Added WSP-compliant module identity, documentation, memory, tests, `module.json`, and `foundup_manifest.json`.
- Registered `esingularity_001` with the Foundups catalog using `/f/esingularity_001` and `idb_esingularity_001`.
- Kept token status deferred and made no fundraising, investment, CABR, payout, or DAO activation claim.
- Performed the migration on the isolated `feat/esingularity-foundup-migration` branch to avoid unrelated RedDog work.
