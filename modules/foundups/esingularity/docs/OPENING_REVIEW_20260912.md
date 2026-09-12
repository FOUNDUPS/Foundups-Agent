# eSingularity opening — first-slide review

Status: draft for 012's visual validation. Do not extend to later slides or publish this draft before the requested opening review.

## Scope and intent

012 requested surgical changes in FOUNDUPS/Foundups-Agent, Japanese first, then English and Brazilian Portuguese. The opening asks whether the community should lose its heart, asks Fukui City to investigate compute-enabled reuse, and links directly to the existing YUMORI committee registration form. The three compute mission questions remain below the image. The existing land-use comparison remains available in a closed disclosure.

Only the root hero and deck slide `vision` (slide 1) receive new content. All later slide records, YUMORI route, domain routing, signup destination, and report content remain unchanged. Existing deck swipe/navigation is reused; direct full-screen entry pauses autoplay. This is a split concept image, not a new draggable before/after reveal widget.

## Artwork provenance

- Recovered the previously approved split demolition/reuse artwork `image-gen-2(1).png`, Library ID `libfile_eed38be3f7b8819180fa05fcbe565452`, rather than inventing another generic resort.
- The repository's `vision-sprite.jpg` was not a decodable JPEG. Other original deck art was located but is outside this sprint.
- Removed old baked-in financial text using image editing, then added a demolition excavator to the left annex while preserving the reuse half. The canonical derivative is `frontend/public/vision/onsen-choice-clean.png`.
- All new wording and financial labels are live localized HTML. The desktop hero crops empty sky/foreground for a compact opening; full-screen retains the entire image.
- The visible caption identifies both scenes as concepts, not current works or approved development. No asbestos/pollution allegation is added.

## Financial source trace

Read the module README, project overview and `frontend/audit/SOURCE_OF_TRUTH.md`; followed its canonical Drive chain. Searches of main and relevant financial/audit/prospectus branch trees found the source ledger and Python module/tests, but did not locate an onsen-specific financial calculation program in the inspected paths. The separate Foundups simulator economics is not evidence for this facility.

| Source | Finding | Opening decision |
| --- | --- | --- |
| [Fukui City June 2026 council question outline](https://www.city.fukui.lg.jp/sisei/gikai/shitsumon/p004052_d/fil/0806a.pdf), admitted by source ledger | Approximately ¥1.58B = 15.8億円, raised in council questions; not final contract price | Display the question “解体に、約15.8億円？” with date, qualification and direct source link |
| [FIN.YUMORI integrated workbook](https://drive.google.com/file/d/11etQ_8zwMzEXemGriCpYw1IbTSy5rh-c/view), modified 2026-09-12 02:24 UTC | Japanese decision dashboard also labels future demolition ¥1.58B as an estimate, distinct from preparation/design budget and internal project CAPEX | Confirms category distinction; do not relabel as total economic loss |
| [Functional financial model and grant audit](https://docs.google.com/spreadsheets/d/1w00eZcfUMyaNu_wwQEf_GVNHpQamYScRdpB_QGecFJ0/edit), modified 2026-09-12 01:25 UTC | Formula-driven model separates unawarded grants and fixes depreciation; its return outputs differ from the legacy snapshot still present in integrated materials | No return, revenue, debt commitment or grant amount added to opening; reconcile and audit in a later funding slice |
| [Master prospectus](https://docs.google.com/document/d/1-wxF_I39svQH8AGvF2sryIk6ReAz2ctHe0-5-HypypM/edit) | Reuse requires time-bounded feasibility review; commercial finance and community benefit funding are distinct | Ask for investigation and participation, not approval of guaranteed project economics |
| Source ledger visitor-spending screen | 129,649 FY2018 visits; 30-year constant, undiscounted spend scenario ¥3.889B–¥21.571B | Not a three-year realized loss. Not combined with demolition, historical construction cost, or compute revenue |

No guessed ¥2.3B, dollar-denominated loss, 230,000 visitor count, asbestos claim, or COVID-only causal assertion is introduced.

## Verification

- Japanese-default preview visually inspected and tightened to keep the signup visible at the reviewed desktop viewport. Screenshot displayed in the review session; browser-to-workspace screenshot synchronization failed, so no missing screenshot is linked here.
- English and Brazilian Portuguese opening text and direct form URLs checked through the actual language switcher.
- Full-screen entry, first-slide selector and Escape checked in Cloud Browser. Swipe uses the retained existing pointer handler; no claim of a new reveal interaction.
- Domain routing checks: 18 passed. YUMORI page/config diff: empty.
- Focused ESLint on opening component/copy, presentation, slide content and root page: passed. Deep-link initialization now runs in a cancellable animation frame, resolving the touched effect's existing lint error.
- TypeScript check reports baseline manifest icon-purpose and LanguageSwitcher duplicate-key errors; no new opening errors.
- Python suite could not run because pytest is unavailable in this runtime.
- Production build did not finish after several minutes without progress; interrupted. A successful production build and CI remain required before merge/deploy. Preview rendering is not treated as a production build pass.
- `git diff --check`: passed.

## Recovery notes

Worktree started from origin/main `44da8edacdb25fbed8aa00500a0b7dd895bb9cf5`. WSP tracker torch-free awakening fallback passed; normal WSP_00 path could not import torch. HoloIndex returned missing generation binding / unknown freshness; scoped repository reads were used, with no speculative reindex.

Managed preview required copied ignored dependencies, `vite` as the dev command, host `0.0.0.0`, and allowed host `terminal.local` per Sites preview troubleshooting. Production build command, dependencies and lockfile are unchanged.
