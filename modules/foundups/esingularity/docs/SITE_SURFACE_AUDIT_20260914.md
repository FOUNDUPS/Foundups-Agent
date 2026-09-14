# eSingularity.ai / YUMORI.me public-surface audit — 2026-09-14

Status: **AUDITED / VERIFIED DEFECTS REPAIRED IN THIS BRANCH; PIXEL-LEVEL DEVICE REVIEW STILL REQUIRED**

Audit branch: `fix/esingularity-full-surface-audit-20260914`

Parent source: `fix/jhr-002-news-jobs@2536c6f0f57805ebca9b577ec51e2c83abfbd508` (PR #1726). The branch is deliberately stacked on the current JHR #002 source so the newer report/publication work is not overwritten by an older checkout.

## Scope

Audited the public eSingularity/YUMORI frontend as one system:

- `eSingularity.ai/` project homepage;
- `YUMORI.me/` movement homepage;
- `/future`;
- `/team` and static team profile routes;
- shared presentation, ticker and language layers;
- JHR discoverability and current #002 links;
- PWA manifest and sitemap;
- static asset dependencies and cross-route fragment links;
- known concurrent PR ownership so one repair does not overwrite another.

The audit used current repository source plus fresh public-page inspection available to the session. It is not a claim of fresh physical iPhone/iPad Safari testing. The current tool environment does not provide a complete pixel-level device screenshot matrix, so phone/iPad/Safari geometry remains a separate publication gate.

## Verified defects fixed here

### 1. YUMORI.me branding drift

The movement surface still rendered legacy labels such as `JOIN YUMORI`, `I am a guardian`, English-only WHY/WHAT/HOW headings, and an English-first JHR label despite the maintained branding contract.

Repair:

- `JOIN YUMORI.me / 湯守になる`;
- `私は湯守！ / me GUARDIAN! = YUMORI.me`;
- Japanese-first WHY/WHAT/HOW labels;
- Japanese katakana JHR title;
- `.me` retained in movement-name references;
- `FoundUp` restored as a project label rather than `FoundUps` as a people label.

Alternate-language structural labels remain available through the existing global language layer.

### 2. Broken internal navigation

Secondary routes linked to `/#innovation-hub`, but the actual root section is `#innovation-space`. The team CTA also linked to nonexistent `/#join`.

Repair:

- `/future`, `/team`, and `/team/[slug]` now target `/#innovation-space`;
- `/team` participation CTA now goes to the actual YUMORI.me movement surface instead of a nonexistent root fragment.

### 3. Withdrawn campaign request still visible

The first vision slide and one root evidence action still asked for a review/comparison period after the campaign moved to the September 25 **VOTE NO** position.

Repair:

- first vision-slide action now uses the current VOTE NO request in JA/EN/PT;
- root `YumoriAction` normalizes the retired comparison-period wording to `解体準備予算に反対を。VOTE NO`.

This does not change historical documents; it fixes active public calls to action.

### 4. Screen-reader punctuation artifact

The deck's live region always inserted an English period between slide title and summary. Japanese titles ending in `。` therefore produced `。.` in rendered/accessibility text.

Repair: locale-aware separator; Japanese uses spacing, English/Portuguese use period-plus-space.

### 5. Japanese-default English leakage

`/future`, `/team`, and team profiles carried decorative English headings on the Japanese-default experience.

Repair: source copy is Japanese-first for structural labels and the global translation map supplies English/Portuguese alternatives.

### 6. Sitemap omission

Public team routes were absent from the eSingularity sitemap.

Repair: add `/team`, `/team/012`, and `/team/0102`; retain YUMORI.me outside the eSingularity sitemap because it is a distinct hostname.

### 7. PWA icon-purpose representation

The manifest used combined `purpose: 'any maskable'` entries. The current typed/runtime path has previously exposed this as a compatibility/type artifact.

Repair: explicit `any` and `maskable` entries for both 192 px and 512 px icons.

### 8. Deck URL-state effect failed full lint

Once the inherited stale test gate was temporarily aligned so CI could reach the frontend stages, full ESLint exposed a real runtime-quality defect in `YumoriPresentation.tsx`: URL/deep-link state was restored with synchronous `setState()` calls directly in an effect body (`react-hooks/set-state-in-effect`).

Repair: defer the URL/deep-link restoration through `requestAnimationFrame` and cancel the frame on cleanup. This preserves direct `?vision=1&slide=N` behavior without the cascading-render lint error.

## Verified defect owned by another active PR — not duplicated here

### Shared ticker action anchors and mobile ticker behavior — PR #1701

The parent ticker still contains fragment actions for `#city-action` / `#act-now` that have no matching root IDs. PR #1701 already owns the correct repair: civic-message/contact destinations under `/vote-no`, slower phone/tablet ticker speed, and thumb-friendly mobile placement.

This branch deliberately does **not** edit the ticker. Reconcile #1701 rather than creating a second ticker implementation.

### Stale presentation CI contracts — PR #1700

The three known eSingularity validation failures are stale tests requiring the retired sprite implementation and removed `content/yumori-presentation.ts`. PR #1700 already owns those contract repairs. This branch does not restore the duplicate retired source merely to satisfy stale tests.

For validation only, the equivalent current-architecture test assertions were temporarily applied on commit `f45eefc302e9c5ff649a9065e0f8ff8a0fe17436`, allowing the full existing workflow to execute. They were then reverted so PR #1700 keeps ownership of that test migration; no `test_contracts.py` delta remains in this audit PR.

## Validation evidence

At `f45eefc302e9c5ff649a9065e0f8ff8a0fe17436`, with the executable frontend identical to this audit branch and only the #1700-equivalent stale tests temporarily aligned:

- eSingularity Python contracts: **30 passed**;
- public catalog projection: **safe / 0 errors**;
- hostname routing: **18 passed**;
- full frontend lint: **passed** after the deck effect repair;
- production frontend build: **passed**.

The temporary test-contract alignment was subsequently reverted. Therefore the final branch again reports the three inherited stale failures until #1700 is reconciled, but the executable frontend code has already passed the complete lint/build workflow.

The lint run also reported existing `<img>` optimization warnings on JHR and YUMORI surfaces. They are warnings, not build failures; the external R.E.port hotlink is separately recorded below as an availability/provenance risk.

## Observed risks, not verified failures

### External R.E.port image dependency

YUMORI.me hotlinks the Inzai reference image from `www.re-port.net`. It rendered during the audit, so it is not recorded as broken. It remains an availability/privacy/caching dependency and should eventually be replaced by a provenance-approved local asset or a deliberately managed external reference.

### Two DOM translation layers

`LanguageSwitcher` and `JapaneseSurfacePolisher` both transform text nodes. The current audit repaired source labels rather than expanding this into a translation-architecture rewrite. If language switching shows flicker, reversion, or race behavior in a browser, consolidate the two mutation layers in a separate bounded change.

### Actual-device geometry

Responsive CSS includes narrow-screen containment, dedicated language-control placement, reduced-motion behavior, and ticker reading mode. This audit did not freshly reproduce every 320–390 px phone width or 11-inch iPad portrait/landscape on real Safari hardware. Do not treat build/DOM checks as a visual-device certification.

## Acceptance checks for this branch

1. YUMORI brand regression passes: `.me`, guardian lockup, Japanese-first headings and JHR title.
2. Secondary-route navigation test confirms no `/#innovation-hub` or `/#join` remains in audited routes.
3. Deck test confirms current VOTE NO action and no `。.` live-region construction.
4. Existing domain-routing/JHR contracts remain intact from parent PR #1726.
5. Production build and full lint passed on the same executable frontend at the validation commit above.
6. Final branch's remaining three eSingularity suite failures are inherited stale presentation contracts owned by #1700 and are not a reason to reintroduce retired code.
7. Publication must preserve both distinct homepages and should be followed by fresh custom-domain checks; actual phone/iPad Safari review remains a separate final visual gate.

## Ownership boundary

This is a rendering/navigation/branding audit, not a redesign. It does not change DNS, grant claims, financial assumptions, committee records, form permissions, RedDog runtime, or JHR #002 research. It preserves the single canonical FoundUp at `modules/foundups/esingularity` and the two distinct public experiences.