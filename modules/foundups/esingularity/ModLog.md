# Project eSingularity ModLog

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
