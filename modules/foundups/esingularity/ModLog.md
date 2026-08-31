# Project eSingularity ModLog

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
