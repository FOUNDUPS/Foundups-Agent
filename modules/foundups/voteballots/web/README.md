# Vote public landing

This directory is the canonical editable source for Vote's informational
front door. It introduces the existing `voteballots` FoundUp and links to its
available Oversight Blueprint workstream. It is not the candidate/funding
application, an official ballot, confidential intake or a running agent service.

## Source and deployment

The public evidence and contact slices add two static pages plus their local
styles, scripts and official directory snapshot. Deployment includes the
reviewed HTML, CSS, JS, JSON, manifest and icons. Operator scripts and tests
stay in the module.

The buildless public files are `index.html`, `style.css`, `app.js`, `sw.js`,
`manifest.webmanifest`, `coalition.html`, `coalition.js`, `coalition-draft.mjs`
and the three files under `icons/`. This README is
operator documentation and is excluded from the deployed static directory.

- Sites project: `appgprj_6aee6646e6ac81918ac2624d5d1db413`
- Generated address: `https://vote.undaodu.chatgpt.site/`
- Preferred public landing: <https://vote.mtrout.com/>.
- Public Coalition page: <https://vote.mtrout.com/coalition>.
- Release evidence and outstanding gates: [Vote release accounting](../docs/RELEASE_ACCOUNTING.md).
- Oversight source/release owner: [the preserved workstream](../oversight/README.md).
- Preferred Oversight workstream: <https://oversight.mtrout.com/>.
- Retained Oversight alias: <https://maga.mtrout.com/>.

All three preferred/retained `mtrout.com` addresses passed public DNS, strict
TLS and correct-page HTTP 200 checks on both public endpoints on 7 November
2026 at 00:45 UTC. The previously configured `vote.foundups.com` and
`oversight.vote.foundups.com` aliases remain retained, not promoted to the
preferred public map. Keep the generated Site addresses and existing aliases;
an address preference is not authorization to delete or redirect them.

The Site's source repository is a deployment mirror. Preserve its existing
project identity and reconcile its current branch before replacing public files
from this directory. Do not initialize an unrelated Site or copy Git metadata,
environment files, credentials, local helpers or private runtime state.

Use the Sites skill's supported source helper to commit/push/package that exact
mirror and native Sites tools to save/deploy it. Keep source provenance outside
the public `dist/` output, referencing the reviewed Foundups Git commit and this
module path. Preserve the existing Site audience unless the requested release
explicitly changes it. Record actual deployment and alias results separately.

## PWA and product boundary

The **Coalition** navigation uses the `coalition.html` source page. Sites
redirects that address to the public clean path `/coalition`. Its voluntary form validates,
previews and downloads a private application draft on the visitor's device.
It sends nothing, uses no persistent browser storage, and grants no membership,
verified badge or permission. It does not collect email, IDs or location. No
named creator is seeded as a member. See [the audit](../docs/COALITION_TAB_AUDIT.md)
for the supplied full-stack proposal's identity/schema findings and the separate
backend admission requirements. Existing operator OAuth is not visitor OAuth.

The same official House and Senate directory links and Capitol Switchboard
phone link are available to every visitor. The site does not pick a target,
collect a ZIP code or record whether a call was placed.

All assets are local, the content policy is self-only, and the install control
appears only when the browser offers installation. The service worker registers
relative to this directory and caches only exact, same-origin public shell
paths. It does not cache API requests, external links, query variants or writes.
The v3 worker precaches the canonical `/coalition`, `/evidence` and
`/contact` routes. Legacy HTML navigation has the corresponding canonical
offline fallback. Installation validates response status, type and exact URL
before filling the cache. Real-device acceptance is a separate check.

Vote retains `/f/voteballots`, `/f/voteballots/app` and `idb_voteballots` in the
FoundUps shell. A separately hosted landing and Oversight Site do not implement
one shared-origin installed Mall PWA or shared authentication/storage.

Keep the page's explicit internal/planned labels for funding research and claim
verification. The existing live-data, public-app and governed OpenClaw/WRE/RSI
admission gates are unchanged by publishing this guide.

## Validation

Run `node --check` on `app.js` and `sw.js`; validate the manifest, local assets,
anchors, HTTPS links and service-worker eligibility. Check desktop and phone
layout when browser control is available. A source check or successful deploy
does not itself establish browser-rendering QA or custom-domain activation.

Run `node --test modules/foundups/voteballots/tests/test_coalition_draft.mjs`
from the repository root for the independent draft-contract security cases.
