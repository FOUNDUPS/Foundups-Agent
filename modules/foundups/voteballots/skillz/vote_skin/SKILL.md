---
name: vote-skin
description: Extend Vote's existing browser-local skins and editable call-script templates, including the independent HPC campaign skin.
---

# Vote skins

Read `modules/foundups/voteballots/web/README.md`, the module interface and current
Sites source before changing the public contact page. Reuse `web/contact.html`,
`contact.css`, `contact-script.mjs` and `contact-script.js`; do not fork the directory,
create a second caller backend or replace the Vote landing.

`SKINS` owns allowed visual/editorial presets. `/contact#hpc` selects HPC; unknown
initial fragments fall back to Vote; ordinary later anchors must preserve drafts.
Match the selector and explicit CSS skin rules when
adding a preset. Keep the existing HPC/Mall return links and independent-site notice.

Source-aware entry: the originating FoundUp's existing outbound link carries the
registered skin fragment (`/contact#hpc` for HPC). Set its canonical projection
and regenerate/verify the public projection through its existing owner. Keep
`referrerpolicy="no-referrer"`; do not use cookies, browser history, URL text
matching or referrer inference to choose political content. The fragment is a
public presentation preset, not authenticated origin, identity or authorization.
Other FoundUps get a registered preset before their link selects it. Missing or
unknown presets remain Vote Classic; the selector remains an optional override.

Templates consume only caller-edited introduction, callback, request and reason.
Tone/regeneration may vary phrasing, never membership numbers, identity, endorsements,
election results, eligibility or the core request. Do not infer persuasion from
location, office, browsing history or personal traits. Do not seed every visitor
as the executive director or publish a private callback as a universal default.
Coalition size and historical claims need evidence before becoming default copy.

Keep generation in memory and use textarea values/textContent, not HTML insertion.
No model, telemetry, storage, automatic call or external submission is required.
Preserve manual directory selection and `tel:` validation. Script controls must
work even when the directory fetch fails. Clear removes caller data and output.

Run the existing contact, coalition and public service-worker tests plus script
tests. Verify keyboard/touch, narrow layout, every tone, regeneration, copy fallback,
skin fallback, offline shell and directory failure. Register new same-origin assets
in the existing worker; bump its cache. Reconcile live Sites source before deploying
only owned changes, and record source/tests/merge/live evidence separately.
