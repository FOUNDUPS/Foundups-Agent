# Vote public landing

This directory is the canonical editable source for Vote's informational
front door. It introduces the existing `voteballots` FoundUp and links to its
available Oversight Blueprint workstream. It is not the candidate/funding
application, an official ballot, confidential intake or a running agent service.

## Source and deployment

The buildless public files are `index.html`, `style.css`, `app.js`, `sw.js`,
`manifest.webmanifest` and the three files under `icons/`. This README is
operator documentation and is excluded from the deployed static directory.

- Sites project: `appgprj_6aee6646e6ac81918ac2624d5d1db413`
- Generated address: `https://vote.undaodu.chatgpt.site/`
- Requested alias: `vote.foundups.com`; activation requires separate public
  DNS, certificate and correct-page verification.
- Oversight source/release owner: [the preserved workstream](../oversight/README.md).
- Existing working Oversight address: `https://oversight.mtrout.com/`.
- Requested additive workstream alias: `oversight.vote.foundups.com`.

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

All assets are local, the content policy is self-only, and the install control
appears only when the browser offers installation. The service worker registers
relative to this directory and caches only exact, same-origin public shell
paths. It does not cache API requests, external links, query variants or writes.

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
