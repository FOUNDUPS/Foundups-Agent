# Move2Japan housing discovery: shared Mall integration and evidence

Updated: 2026-10-18 UTC. Owner: 0102, under 012's direct development instruction.
Brand and primary domain: **Move2Japan**, **move2japan.info** (numeral 2).
Repository delivery: [PR #2151](https://github.com/FOUNDUPS/Foundups-Agent/pull/2151).

## Decision and corrected structure

Move2Japan is a registered product in the existing Play Foundups Mall. The public
entry opens the actual `public/member/index.html` with houses selected. That page
owns the shell, field, Red Dog, account integration, gestures, detail planes,
service worker and view persistence. The domain adapter supplies factual house
records, geographic grouping and English filter controls.

The initial 2026-10-17 implementation imported shared scripts into a separate
Move2Japan page. Shared assets alone did not satisfy 012's instruction that the
product operate *inside* the Mall. The subsequent geographic preview demonstrated
horizontal houses and vertical areas, but still had a separate HTML shell and a
reduced public-only Red Dog. Both were architectural gaps. The current correction
moves the product into the actual Mall boot and composes its search form with the
full shared account controller. `/move2japan/` is now only a redirect alias.

| Route | Ownership and behavior |
| --- | --- |
| `/f/move2japan` | Existing registered FoundUp discovery entry; Browse houses follows its exact public POC URL |
| `/member/?foundup=move2japan` | Actual shared Mall page, public houses selected |
| `/member/?creator=move2japan` | Ordinary admitted Mall with the existing Move2Japan video channel expanded |
| `/member/` | Ordinary admitted Mall; responsive category rows and explicit grid remain available |
| `/move2japan/` | Fixed same-site redirect with bounded house filters |
| `/f/move2japan/app` | Existing protected participation handoff; public discovery does not authorize it |

Only one exact `foundup=move2japan` selection enables the public product boot.
Unknown and duplicate selections retain ordinary admission. The adapter moves the
existing field node; it creates no second field, account owner or tenant runtime.
The registered public POC does not make the product portfolio-ready or launch an
autonomous FoundUp worker.

## WSP 00 / WSP 97 recovery discipline

This is an ordinary repository and website development slice. It is not a WRE
worker-admission receipt, production crawler launch, financial transaction, or
payment/token authorization.

- Root `AGENTS.md`, WSP 00/97, navigation, module docs, roadmap, test inventory,
  Mall navigation contracts, account owner, registry and projector were read.
- The canonical WSP 00 V2 bootstrap was attempted. `torch` was unavailable. The
  documented section 3.3.1 tracker fallback opened the local strict gate with
  `execution_method=mathematical_formulas`; the detector witness remains absent.
- The source-bound Holo owner helper used its documented lexical fallback:
  `bundle_ok=true`, workspace source selected explicitly, zero owner attempts,
  `freshness=UNKNOWN`, `index_gap_detected=true`. No semantic freshness or reindex
  is claimed. Direct current-source reads resolved the task owners.
- Retrieval had excessive YouTube matches, stale domain/stage documentation and
  missing website-specific owners. Exact Mall, property and account files were
  must-included; duplicated and unrelated hits were excluded before edits.
- Main's parallel responsive category/query work (#2155), AutoPost Live direction
  (#2154) and subsequent security documentation (#2153) are preserved. Integration
  review reconciles product geography with the same field and dispatcher APIs.
- No `main.py`, daemon, Holo reindex, authority reset or runtime worker was started.

## Interruption and recoverable evidence

A GitHub content upload stalled for an extended period. After it returned, the
local task checkout, Site checkout and temporary test environment were absent.
The available evidence does not establish why the executor state disappeared.
The remote PR was still at `db1442ae5d5c8856a9a15ef8cdd96362c824c03e`; no incomplete
replacement was written to its ref.

Recovery used that original PR, current main, the existing private Site's source
commit `77db7957ce7527a0f614de545317ac03842c876b`, and retained exact tool outputs and
patches. All 13 files in the published Site provenance manifest were checked
against their SHA-256 values. The final reviewed field patch restores Git blob
`966e59f748422a5aed2cf24694d01c6fe6636626` exactly. Missing account/boot and harness
segments were rebuilt from current owners and the reviewed contracts, and freshly
executed; historical passing checks are not presented as proof of those new bytes.
Owned source and recovery metadata were checkpointed in retained session stores.

The correction did not reset or overwrite 012's concurrent Mall work. The recovered
branch was reconciled with main `b9051be2` (which contains Mall commit `6ad7cf09`).
The delivery commit and its actual checks are recorded separately below.

## Shared runtime contract

### Geographic field

The field immediately presents houses. Each horizontal row contains houses from
one area; vertical movement changes areas. City/town and locality grouping are
supported. Country, prefecture, city, locality, land status, budget, large plot
and source-tour filters combine. Empty or unsupported geography yields an honest
empty result, not a widened search. Each house retains a stable `listing_id`
inside the existing `move2japan` FoundUp context.

Explicit geographic groups take precedence over normal category rows, even when
empty. `getLayoutMode()` reports `grouped` for the product. Global video category,
query, scope, channel and rows/grid controls cannot mutate geographic results.
Dispatcher `search_catalog` reports `incompatible_projection` on refusal and emits
no state-change event. Normal Mall catalog search and responsive category browsing
retain their current owner behavior.

### Shared account and Red Dog

`product-discovery` mode uses the existing full Red Dog controller plus accessible
modal handling. The native product form stays usable for guests. Existing members
can see their identity, canonical FoundUp entries, invitations and applicable
shared tools after the existing Clerk/invite/username admission checks.

Public browsing starts synchronously and does not wait for Firebase. A bounded
Clerk connection optionally reads an already-present account. This product path
never creates profiles, validates cached invitations, mints invite codes or writes
member records. Signup remains in the normal gateway. Missing invitation records
are displayed as unknown rather than active access.

Every account synchronization starts by revoking the previous displayed context.
A generation token plus the current Clerk account ID guards each asynchronous
read and error path. Late user, catalog or invitation responses cannot restore a
signed-out or previously selected account. The same-ID refresh race is guarded.
Revocation clears both avatars and private account sections. Account and video
links use the canonical Foundups host, including from a private review mirror.

### View persistence and caching

Video state stays at `pfmall_mall_state_v1`. Move2Japan uses
`pfmall_product_move2japan_state_v1`, with stable row/listing anchors and offsets.
Product restoration never applies video scope/layout; deferred video callbacks
recheck the active product. A loading product cannot erase its saved position.
A bounded, one-use, 15-minute session return preserves house filters through the
normal account gateway and is consumed only after actual admission.

The existing `/member/manifest.json` retains its member app identity and scope.
The combined service-worker cache is `pfmall-member-v4`. Member query navigations
share one cached shell; property JSON is network-first with JSON validation and a
dated cached fallback. Only explicit public assets are eligible. Auth, account,
dynamic, cross-origin and non-GET requests are not cached. This is a code contract;
real offline browser behavior still requires a served-browser receipt.

## Source collection and uncertainty

The POC contains **eight dated public source observations across five Fukui
municipalities**. Seven record a plot area, one has unknown land, and none is
classified as confirmed no-land. One asking price is negotiable and remains null;
unpriced homes are excluded under a budget filter and sort after known prices.
A recorded plot area does not establish ownership/title conditions.

The observations were checked on 2026-10-17 JST. They are not a live or nationwide
feed and do not confirm current availability. Inquiry and transaction details stay
with the source and broker. Photos, full descriptions and tours are linked at the
source rather than republished. No bulk media or commercial feed permission is
assumed. `建築面積` remains the source's building-area label, not an invented total
usable-floor-area interpretation. Address localities retain Japanese source text;
checked Latin forms are provided for English discovery. Conflicting source details
remain visible in `source_notes`; parcel coordinates are not fabricated.

| Source record | Municipality | Land / price qualification |
| --- | --- | --- |
| [87](https://akiya.pref.fukui.lg.jp/webroot/public/estate/detail/87) | Wakasa | Recorded plot; asking price |
| [85](https://akiya.pref.fukui.lg.jp/webroot/public/estate/detail/85) | Fukui City | Recorded plot; construction/condition unknown where source lacks facts |
| [83](https://akiya.pref.fukui.lg.jp/webroot/public/estate/detail/83) | Sakai | Recorded plot; asking price |
| [77](https://akiya.pref.fukui.lg.jp/webroot/public/estate/detail/77) | Awara | Recorded plot; source conflicts retained |
| [76](https://akiya.pref.fukui.lg.jp/webroot/public/estate/detail/76) | Eiheiji | Recorded plot; asking price |
| [25](https://akiya.pref.fukui.lg.jp/webroot/public/estate/detail/25) | Sakai | Unknown land area, not no-land |
| [79](https://akiya.pref.fukui.lg.jp/webroot/public/estate/detail/79) | Eiheiji | Recorded plot; asking price |
| [88](https://akiya.pref.fukui.lg.jp/webroot/public/estate/detail/88) | Wakasa | Recorded plot; negotiable price remains null |

Additional grounding: [Fukui bank](https://akiya.pref.fukui.lg.jp/),
[MLIT nationwide bank operators](https://www.mlit.go.jp/totikensangyo/const/sosei_const_tk3_000131.html),
[brokerage lookup](https://etsuran2.mlit.go.jp/TAKKEN/),
[LIFULL terms](https://www.homes.co.jp/kiyaku/), and
[At Home municipal API example](https://www.athome.co.jp/corporate/news/release/services/akiyabank-chiba-202604/).
These are research references, not evidence that a production feed or license was obtained.

## Roadmap gates and membership/token boundary

| Stage | Required evidence | Status in this slice |
| --- | --- | --- |
| POC | A person can search and inspect sourced houses | Implemented in the actual shared Mall; publication receipts below |
| Prototype | An authorized broker/owner can publish via a shared account | Pending verified authority, consent/media permission, durable storage/provider, review and listing lifecycle |
| MVP | Actual paying customers receive the promised benefit | Pending shared billing/entitlement integration, settled payment and delivered benefit, expiry/refund handling |

Existing BC0 YouTube intake and SQLite stakeholder memory remain under their
current owners. GotJunk's approved public-listing projection and upload work can
inform the next layer; they are not a working universal house publisher. An
account, invite, wallet balance, token label, waitlist or free trial is not a paid
housing entitlement. Earlier curated alerts are a possible future benefit; public
bank listings are not described as exclusive inventory.

Move2Japan retains its existing registry identity and is now registered as an
incubating FoundUp at F0, reflecting 012's expanded housing-product scope.
The manifest is declarative, with autonomous routes/build authorization absent.
Token status remains deferred and the token symbol is null. No payment, premium
inventory release, token issuance or publisher authority is granted by client state.
The [module roadmap](../ROADMAP.md), [premium model](03_PREMIUM_MODEL.md) and
[stage definitions](04_POC_PROTOTYPE_MVP.md) govern the next slices.

## Validation receipts

Fresh recovered-source execution has passed the actual complete member inline
script harness (21 cases), the domain search/route harness (28 cases), the shared
property runtime, the state/SW VM (17 cases) and the concierge VM (21 cases).
The dispatcher VM retains its original cases plus the incompatible-projection
checks. The integrated result is **1698 passed, 4 baseline failures, 0 skipped in 11.52 seconds**. Independent review is recorded in
[shared TestModLog](../../../../public/member/tests/TestModLog.md) and
[domain TestModLog](../tests/TestModLog.md). Counts overlap and should not be added.

Known pre-existing full-suite failures are the three unchanged navigation string
expectations (`fv-open-link`, `routing_prefix`, `Tap to play/pause`) and BC0's
`TestIntentBucketDetection.test_cost` (housing's `live` precedes cost's `expensive`).
Their original handlers/tests are unchanged from the base. They are not suppressed
or repaired as part of this product integration.

These local VMs execute real source with bounded DOM and network doubles. They do
not establish production authentication, provider playback, Safari/iPad hardware,
listing availability, payments or real offline browser behavior. The available
Browser connector lacked its originating browser context; the documented preview
supervisor also could not mount its required proc namespace. No alternate browser,
replacement server or infrastructure bypass was used. Browser QA remains unverified.

## Delivery and deployment status

The existing owner-private review Site is
https://move2japan.undaodu.chatgpt.site, project
`appgprj_6ad2b62b4724819186cf254ae67fc866`. Its audience remains owner-private.
The recovered prior version used source commit `77db7957ce7527a0f614de545317ac03842c876b`
and deployment `appgdep_6ad2c99dae548191b4b4458ef66b7307` (succeeded
2026-10-17T01:04:36.202292Z). That historical publication demonstrated geography in
a separate page; it is not proof of this corrected actual-Mall publication.
The corrected existing Site publication succeeded on 2026-10-18T22:23:47.078004Z:

- Source commit: `8578da1d4238f7bf7bedb72222ef853494d4e0d8`.
- Saved version: `appgprj_6ad2b62b4724819186cf254ae67fc866~appgver_848f463799148191b2b46e24ee4f0e66`.
- Deployment: `appgdep_6ad546e498c4819194efa0d9b0944cef`; native result `succeeded`.
- URL: https://move2japan.undaodu.chatgpt.site.

The mirror contains 30 byte-verified canonical runtime files, including the actual
member index, all shared controllers/styles, state/SW/manifest, public catalogs and
domain adapter. Its root reuses the canonical Move2Japan redirect alias. Static
`/f/` route copies execute the unchanged shared route owner with their own path;
no separate house renderer or account implementation is introduced. Per-file
SHA-256 provenance is committed in the Site source repository. Account/video links
target the canonical Foundups host. The owner-private audience is unchanged.
Native publication success establishes this private deployment, not browser layout,
shared production authentication or a primary-domain cutover.

Production is a separate owner: tracked `firebase.json` publishes `public/` to
Firebase Hosting site `foundupscom`; the verified public Firebase project is
`gen-lang-client-0061781628`. The documented command is
`firebase deploy --only hosting --project gen-lang-client-0061781628`.
The execution environment has no Firebase CLI/authentication context or configured
production-deploy connector. A GitHub merge alone does not deploy that site.

Fresh anonymous HTTP checks at **2026-10-18 22:32:22 UTC**, through the available
network transport with cache revalidation requested, confirmed the production
release is still outstanding:

| URL | Received result |
| --- | --- |
| `https://foundups.com/member/` | 200 HTML, 50,610 bytes; missing the current product boot, field template and adapter script |
| `https://foundups.com/member/js/mall-tile-field.js` | 200 JavaScript, 55,067 bytes; missing property/group/state/query APIs present in source |
| `https://foundups.com/member/js/account-concierge.js` | 200 JavaScript, 59,879 bytes; missing the product discovery/admission APIs |
| `https://foundups.com/f/public_catalog.json` | 200 HTML, 38,426 bytes; not a valid JSON catalog |
| `https://foundups.com/move2japan/` | 200 HTML, 98,748 bytes; exactly the homepage bytes, without the source alias redirect |
| `https://move2japan.info/` | 301 to `https://www.patreon.com/move2japan`, then 308 to `https://www.patreon.com/MOVE2JAPAN`, then 200 |

An earlier proxy 502 was inconclusive and is superseded by this successful
received redirect chain. These responses do not prove direct origin access or
browser authentication. No root Firebase Hosting release workflow or dedicated
deployment capability is available in this session. Source merge, private Site
publication and production delivery remain separate receipts. No Firebase
production deploy, DNS/registrar cutover, forwarding or audience change is claimed.
