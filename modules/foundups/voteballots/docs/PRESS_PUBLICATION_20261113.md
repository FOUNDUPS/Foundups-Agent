# HPC press section — source and publication record

Date: 2026-11-13. Scope: additive press page on the existing Vote site. Principal: 012. Author: 0102.
Baseline: main `4c1d1e7d9737dee3c713a8476ff257b31cfad26a`.

## Content and source owner

`web/press.html` is the canonical release and press index. `web/press.css` supplies isolated reading/print styles. The cover receives only a header Press link and footer Press & media link. Existing comics, captions, radio, ticker, guide, contact, evidence and Coalition content are preserved.

The release retains 012's campaign proposal and supplied media contact, with paragraph spacing, four separate tool descriptions and independent-campaign disclosure. It removes unverified audience numbers, causal claims about the 2026 election, purported participation by named officials, mathematical certainty and algorithmic guarantees. UDP is the AIPAC-backed United Democracy Project, not a renamed AIPAC. A House election remains necessary; staff support does not displace the Speaker's responsibilities.

Primary sources are linked in the page's editor notes: House history, the House Rules and Manual, AIPAC's own description, FEC committee C00799031 and the official House directory. No election-result total, claimed Piker endorsement, membership count or fabricated quotation is added. Vote/Voice/Poly descriptions retain implementation-versus-proposal boundaries from the existing module documents and PR #2337. This slice does not merge or change that PR.

## Domain and deployment

User reports hasan4speaker.com forwards to the current site. Direct web requests did not establish the redirect here; container DNS also failed for unrelated hosts. A browser-provider check could not start. These are verification gaps, not evidence of a public outage. Keep forwarding and DNS unchanged. Do not announce a verified migration or create a new site.

Publish through the existing Vote Sites project `appgprj_6aee6646e6ac81918ac2624d5d1db413` and its source mirror, following `web/README.md`. Add `press.html` and `press.css` to that project's public allowlist, preserving all other resources and aliases. Verify clean `/press`, legacy `/press.html`, the release anchor, both cover links, back navigation and MIME/CSP on the actual release before reporting live publication.

This press page is ONLINE-ONLY in this slice. The existing worker's exact precache allowlist is unchanged; no offline availability of press is promised. Its network-first root behavior can serve the updated cover online. Any later offline extension must update and run the existing `tests/test_public_sw.mjs` fixture; do not silently broaden caching.

## Validation and limits

The original cover was reconstructed from the exact connector source and its Git blob hash verified as `97c0bfd88610fcb2e0f768cbd6be4fa4b3554ec7`. Removing the two new link lines from the candidate reproduces those exact original bytes.

Static checks cover unique IDs, fragment targets, supplied email/phone, all four tools, absence of invented election/attention claims and absence of scripts, forms, iframes or audio in the press page. Read existing test README, TestModLog and public-worker fixture; no existing test or CI policy is changed.

An isolated Chromium 144.0.7559.96 HTML/CSS rendering fixture passed at 320x700, 390x844 and 1366x900 with no horizontal overflow, working keyboard skip focus and print visibility. This fixture inlined the existing stylesheet and omitted the production CSP solely for offline layout rendering; it is NOT CSP, routing, hosted, service-worker, physical-device or independent-verifier evidence. Normal local HTTP browser navigation was blocked by environment policy.

No native WSP bootstrap, semantic HoloIndex, WRE dispatch, full repository tests, independent review, PC synchronization, merge, DNS change or deployment is claimed. Exact-head CI, qualified merge, mirror publication and public readback remain separate gates. Connected discovery did not expose the existing Sites publisher; do not substitute a different hosting provider.

No HPC/pfMALL/shared-player files, Poly implementation, registry, manifests or secrets are changed. Recovery is reversal of this bounded press addition only; preserve all concurrent work.
