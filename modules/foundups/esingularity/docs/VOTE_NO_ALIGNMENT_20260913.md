# YUMORI / eSingularity alignment audit — 2026-09-13

## Decision and ownership

The operator withdrew the 60-day review proposal. The current request is **VOTE NO** on the budget containing demolition preparation for Sukatto Land Kuzuryu at the September 25 council vote. Reuse remains a conditional proposal; a NO vote does not adopt it or approve public investment, guarantees, grants, or private financing.

YUMORI.me is the civic/preservation movement and preparatory committee within the eSingularity.ai effort. The established Japanese name is 設立準備委員会. One canonical module owns two distinct homepages; do not combine or redirect them.

## Source locations and actual drift

| Location | Finding / treatment |
| --- | --- |
| `modules/foundups/esingularity` on current main | Canonical module; confirmed in registry, README and INTERFACE. |
| `frontend/app/page.tsx` | eSingularity.ai project homepage. |
| `frontend/app/yumori/page.tsx` | YUMORI.me movement homepage, internally selected by hostname. |
| `O:\Foundups-Agent` | Was on `feat/yumori-economic-impact-model`, commit `0c81418fe`; this checkout predates the module migration. Its missing module was not evidence of a missing canonical project. Unrelated work was preserved. |
| `O:\Foundups-Agent\sites\yumori-language-sweep` | Separate older Sites checkout, `a462bc0`, September 11. Not the current published source. Retained as a legacy copy; do not deploy from it. |
| `.worktrees/esingularity-foundup-migration`, `.worktrees/esingularity-onsen-location-gallery`, `.worktrees/yumori-cinematic-deck` | Older Git worktrees with independent branches. Historical/branch work, not separate product ownership. Not deleted or overwritten. |
| `.worktrees/esingularity-vote-no/modules/foundups/esingularity` | This bounded update, based on current remote main `85f188ffc` (September 13). |
| `O:\Foundups-Agent\eSingularity.ai` | Local directory junction to the preceding canonical module checkout. Convenient single entry point, not a second copy of source. |
| `.publishing/site` | Ignored publication mirror under the module, not an authoring source. Latest published Sites source `bfeaa68f5a96f093defffd072140cac7e7636e72` matched every tracked canonical frontend file at the base after line-ending normalization. |

Retrieval evaluation: the owner query failed with `HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`, `freshness=UNKNOWN`, `index_gap_detected=true`; no reindex or authority mutation was attempted. Exact current Git source, registry, module docs, tests and published source replaced stale retrieval. Old worktree docs were lower-signal than current remote main. Manual reconciliation was needed because the query service could not supply current authority evidence.

## Corrections

- Updated public JHR Japanese and English campaign framing and its source report to VOTE NO, with City-budget and support-brief links.
- Removed the obsolete translation entry and corrected the economic SVG's deadline and captions.
- Replaced the expired September 13 morning invitation with the current vote request in the shared ticker source; no new appearance or giveaway was invented. Both homepage consumers remain present.
- Added derived English/Portuguese ticker text from the same Japanese source key.
- Corrected two existing JSX apostrophe errors and the touched language-control effect's synchronous state update; portal targeting still follows route changes and cancels its animation callback on cleanup.
- Added the campaign correction to the public-claim ledger, README and grants cross-reference guidance so later edits do not restore an internal authority banner at the top of support brief 03.

## QR and document

Supplied source: `O:\Foundups-Agent\sites\yumori-language-sweep\public\YUMORIme-qr-code.png`.

Canonical asset: `frontend/public/YUMORIme-qr-code.png`. The original PNG was copied without alteration. It decodes to `https://YUMORI.me`. The QR embedded in the exported Google Doc also decoded successfully.

Working document: [03 — City / Prefecture / Council support brief](https://docs.google.com/document/d/1yeO6-6_mTLW8QswosVKmCVCHSRgWiacq-7FL7-9clsE/edit). It was edited directly, preserving the City-source links, table, useful images, date chips, financial distinctions and human legal accountability. The opening states context, value proposition, committee ownership and the VOTE NO request. The funding authority note is ordinary reference text in the funding section, not a Title banner. Two obsolete raster graphics were replaced by a concise VOTE NO/QR closing page. All numeric and Japanese two-month deadline variants were checked and removed from active requests.

Dated local read-only snapshot: `outputs/2026-09-13/03-YUMORI-VOTE-NO-verified.pdf`. The Google Doc remains the editable authority; do not edit this PDF as a parallel working document. Older economic model/deck outputs elsewhere in the checkout were not promoted as current verified forecasts by this audit.

The support brief's finance smart chip still pointed to `1Up2fWPQJiC-l8m--1poiUxn_Wt8Ofh9z` (old macro workbook). It was reconciled to the current FIN audit spreadsheet `1w00eZcfUMyaNu_wwQEf_GVNHpQamYScRdpB_QGecFJ0` recorded in DRIVE_DOCUMENT_INDEX.md. This changes the reference, not the workbook's figures; financial assumptions remain conditional. Metadata shows the current FIN workbook is owner-only, so the brief explicitly says viewing permission is required. No sharing permission or external short-link forwarding was changed.

## Verification

- Google Docs native read-back: 1 title, 30 actual headings, 1 table, 8 inline images, 2 date chips; no active 60-day/two-month/eight-week wording.
- 29-page PDF, all pages visually reviewed; last affected pages rechecked after the final corrections. QR decoded from the PDF itself.
- Preserved budget distinctions: annual preparation ¥12.72m; city bonds ¥10.40m; general revenue ¥2.32m; ¥9.812m design is multiyear continuing expenditure. No inferred asbestos remainder and no claim that this budget line proves future national support unavailable.
- Eight existing JHR/movement content checks and 18 hostname routing checks passed.
- Focused ESLint: zero errors; one existing image optimization warning. Production build passed.
- Local browser: both homepage consumers, Japanese/English campaign wording, language controls, and expanded mobile ticker inspected. No signup was submitted and no outbound message was sent.

Publication and repository integration receipts are recorded in the module ModLog after completion. Source integration and public deployment are separate outcomes.

Public verification: Sites version 48 succeeded. Browser inspection confirmed the updated VOTE NO ticker on `https://esingularity.ai/` and on a fresh YUMORI URL, `https://yumori.me/?audit=20260913`. Plain YUMORI root navigation first reused an old redirect to the participation Google Form; the fresh URL retained the YUMORI hostname and rendered the distinct movement site. This is consistent with a cached legacy redirect, not proof that every client's root cache has refreshed. Both apex/www domains are active with active SSL in Sites. No DNS or forwarding configuration was changed. The existing participation form's introductory text still uses the older request for time to examine options; form wording was not edited in this document/code task.
