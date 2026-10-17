# Move2Japan housing discovery: evidence and implementation boundary

Date: 2026-10-17 JST. Research base: `407292aa754a88143796163581b67ca6679eac29`.
Owner: 0102, architect/implementer. Authority: 012's direct request to inspect and
develop Move2Japan, corrected to the numeral 2, using Foundups Mall and shared
membership. This is an ordinary repository/web development slice, not an
admitted WRE runtime job, financial transaction, or autonomous crawler launch.

## Problem and selected layer

The existing module implements YouTube intake and SQLite stakeholder memory.
Its roadmap still prioritizes that intake and uses `movetojapan` domain strings.
The requested public product now leads with English discovery of real akiya
houses. Existing Mall video tiles must support property records without treating
each property as a new FoundUp or forcing a video playback flow.

Closed groundwork: `m2j_stakeholder_db.py`, livechat's M2J handler, Mall tile field,
detail planes and gestures, and the Foundups account entry already exist.
Open target: public house search, property-specific detail, accurate website
roadmap and a concrete next gate for publisher accounts and paid membership.
Chosen slice: five attributed factual source observations in a searchable public
catalog at `/move2japan/`, with shared Mall rendering and source inquiry links.
The existing YouTube journey, shared account authorization, GotJunk publication
provider and token issuance retain their owners.

## Retrieval and reuse

- Read `AGENTS.md`, WSP 00/97, the root roadmap, historical briefing boundaries,
  module README/INTERFACE/ROADMAP/ModLog/tests and `NAVIGATION.py`.
- The canonical WSP 00 V2 bootstrap was attempted; `torch` was unavailable.
  The documented section 3.3.1 tracker fallback opened the local gate with
  `execution_method=mathematical_formulas`; detector witness is absent.
- The source-bound Holo owner helper ran its documented lexical fallback:
  `bundle_ok=true`, `workspace_head` at the research base, zero owner attempts,
  `freshness=UNKNOWN`, `index_gap_detected=true`. No semantic freshness claim.
- Search initially returned many YouTube hits. Exact module artifacts and shared
  Mall files were must-included and read directly, removing irrelevant results.
  The module roadmap is stale relative to implemented BC0; no house UI existed
  at this base. No reindex, authority reset, or broad runtime setup was used.
- Reuse `public/member/js/mall-tile-field.js`, `mall-planes.js`,
  `gesture-engine.js` and their styles. Properties have a separate `listing_id`
  inside the existing `move2japan` context. The main video catalog is unchanged.
- `modules/foundups/pfmall/listing_discovery.py` is a GotJunk-only public approval
  projection, with no production provider by default. Do not relabel it as a
  working universal inventory or upload service.

## Assumptions and evidence

| Assumption | Evidence | Confidence |
| --- | --- | --- |
| The brand and primary domain use numeral 2 | 012's current correction; prior domain record | High |
| Mall presentation can be extended for properties | Current tile/plane/gesture source and non-video tests | High |
| Five public source records can ground a small discovery demonstration | Individual Fukui bank pages read on 2026-10-17 JST | High for displayed facts; availability unconfirmed |
| A public bank page grants bulk media/translation reuse | No verified grant; explicitly not assumed | Unestablished |
| Foundups account admission is paid membership | Current member page checks Clerk/invite/username, not settled subscription | False |
| A token or client flag proves early-listing access | No housing entitlement adapter exists | False |
| Move2Japan.info is already serving this work | Domain currently described by 012 as Patreon forwarding; deployment requires separate evidence | Unverified |

## Failure modes and controls

| Failure | Impact | Control |
| --- | --- | --- |
| Multiple houses share a FoundUp ID and open the first record | High | Key listing selection and focus by listing ID; behavioral regression checks |
| Source text/URLs inject markup or unsafe navigation | High | Allowlisted fields, escaped text/attributes, HTTPS source URLs without credentials |
| Old/withdrawn listings appear as confirmed available | High | Display observation date and source-listed status; link original and broker inquiry; no availability guarantee |
| Source photos/narratives republished without a grant | High | Original short factual summaries only; photographs and tours stay at the source |
| Static paid catalog exposes early records | High | No paid/early inventory included; prototype requires server-side entitlement filtering before data release |
| Account creation or a free trial is counted as MVP | High | MVP requires recorded customer payment and delivered benefit; refund/expiry handling required |
| Unrelated concurrent work is overwritten | High | Isolated branch at exact base, explicit path ownership, review current main before merge |
| New deployment silently replaces another Foundups service | High | Separate `/move2japan/` source; existing host/domain changes only against verified ownership and configuration |

## Alternatives and decision

Extending the existing Mall field and detail plane preserves the requested
interaction and lets the same presentation handle houses. An unrelated template
would duplicate navigation. Widening the GotJunk provider in this slice would
couple discovery to unverified publication, identity and upload infrastructure.
Building payment flows first would skip the requested proof-of-concept gate.

Decision: **PROCEED** with the bounded public factual catalog and shared Mall
extension; 0102, 2026-10-17 JST. Independent code review and focused behavioral
checks are required before merging. Actual domain deployment, payments,
publisher signup, feed permission and runtime automation remain separately
evidenced milestones in the module roadmap.

## Source registry

Checked 2026-10-17 JST. These pages support discovery and displayed source facts;
they do not establish a commercial data license or confirmed availability.

- [Fukui prefecture bank](https://akiya.pref.fukui.lg.jp/)
- [Wakasa, record 87](https://akiya.pref.fukui.lg.jp/webroot/public/estate/detail/87)
- [Fukui City, record 85](https://akiya.pref.fukui.lg.jp/webroot/public/estate/detail/85)
- [Sakai, record 83](https://akiya.pref.fukui.lg.jp/webroot/public/estate/detail/83)
- [Awara, record 77](https://akiya.pref.fukui.lg.jp/webroot/public/estate/detail/77)
- [Eiheiji, record 76](https://akiya.pref.fukui.lg.jp/webroot/public/estate/detail/76)
- [MLIT nationwide bank operators](https://www.mlit.go.jp/totikensangyo/const/sosei_const_tk3_000131.html)
- [LIFULL service terms](https://www.homes.co.jp/kiyaku/)
- [At Home municipal API integration example](https://www.athome.co.jp/corporate/news/release/services/akiyabank-chiba-202604/)
- [MLIT brokerage lookup](https://etsuran2.mlit.go.jp/TAKKEN/)

The source field `建築面積` is retained as a building-area label, not silently
reinterpreted as total usable floor area. Missing construction or condition data
remain unknown. Source map markers may represent an area center; this slice does
not invent parcel coordinates. Early discovery/alerts are future platform
benefits; publicly listed properties are not described as exclusive inventory.

## Final validation and review evidence

The final integrated command in [TestModLog](../tests/TestModLog.md) produced
**412 passed, 1 failed in 1.13 seconds**. The single failure is the unchanged
BC0 `TestIntentBucketDetection.test_cost` expectation: the existing classifier
matches housing's `live` before cost's `expensive`. Neither its handler nor its
test changed from the research base. It remains open and is not suppressed.

The shared Mall owner replay passed 277 selected checks. Independent review
passed 188 selected checks and the actual-script VM. Counts overlap. Review
found and resolved two property-modal defects before publication:

- Replacing a focused source link while navigating houses could release focus
  behind the dialog. Property navigation now focuses the stable close control,
  and Tab/Shift-Tab recovers focus if it starts outside the dialog.
- A normal upward content scroll could close long property details. The real
  gesture-engine reproducer now verifies vertical property scrolling stays open,
  with horizontal navigation and existing video swipe dismissal retained.

Independent review confirmed the five source records, stable listing identity,
filter intersections, unknown-value handling, safe markup/source navigation and
accurate membership/media boundaries. No remaining scoped code blocker was found.
Three old string-contract failures in `test_navigation_planes.py` were separately
confirmed unchanged at the research base (`fv-open-link`, `routing_prefix`, and
the obsolete `Tap to play/pause` hint).

The canonical test registry check is current: 1720 tracked Python test files,
270 quarantined. The bounded generated change is one new property wrapper and
process-capability metadata for the existing shared VM wrapper. The README
contract passed (1 selected, 14 deselected). HTML structural checks found 25
unique IDs, seven resolving local assets, and valid fragment destinations.
`git diff --check` passed.

## Publication receipt and remaining domain gate

The following is an **owner-private review publication**, separate from
`move2japan.info` and the existing Foundups production account host:

- Review URL: https://move2japan.undaodu.chatgpt.site
- Site project: `appgprj_6ad2b62b4724819186cf254ae67fc866`
- Site source commit: `a8f977a32df6dfda40a4e1617fce944e39b56c3d`
- Saved version: `appgprj_6ad2b62b4724819186cf254ae67fc866~appgver_16eada42fe3c819198d28f3a660f3b96`
- Deployment: `appgdep_6ad2b963a5108191923158ccf22a0d31`
- Service result: `succeeded`, 2026-10-16 23:55:22 UTC (2026-10-17 JST).

The published source is a static mirror of the four files in
`public/move2japan/`, the three shared Mall JavaScript files listed above, and
the two shared Mall CSS files. Its root entry duplicates the Move2Japan index;
`/move2japan/` also resolves. The Site source repository includes a per-file
SHA-256 provenance manifest. There is no independent renderer or copied account
authorization implementation. The supported Site source helper pushed the exact
source commit and packaged its configured static directory before publication.

Actual browser rendering remains **unverified**. The local Browser connector
required an unavailable originating browser context. The documented managed
preview supervisor failed with `bwrap: Can't mount proc on /newroot/proc:
Operation not permitted`, including a retry outside the command sandbox. No
replacement server or infrastructure modification was used. Behavioral and
structural checks above are not represented as browser QA.

The primary domain check was inconclusive: the retrieval proxy returned HTTP
502, so no origin response or redirect was verified. Registrar/DNS access and a
verified primary-host binding are still needed for cutover. No DNS, forwarding,
Firebase production deployment, account gate or audience setting was changed.
Before public rollout, complete the served-page interaction review and primary
domain verification, then record the actual route and audience in this module.
