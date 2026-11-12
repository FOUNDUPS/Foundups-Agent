# Shared Mall media incident · HPC-P01–P08

- Incident ID: PFMALL-MEDIA-20261111-HPC
- Retrieval terms: HPC YouTube bot sign-in, Mall inline playback, fixedVideoField, PWA embed failure.
- Affected owner: shared Play FoundUps Mall member field, player, and state; FoundUp `hpc`
- Opened: 2026-11-11 UTC
- Recovery source: main `375964c704da1e0f6d097e54ba1474930b0e4c30`; worktree `fix/hpc-shared-mall-playback-phase1`
- Reported production baseline: Firebase Hosting `foundupscom` version `4f3974af5ca48c4b`, scoped files from PR #2349 / `6d184630ef24f35f12a0d26adf1aed44547baa1e`. Confirm delivered asset bytes and service worker separately.
- Ownership: 0102 worker, 012 handoff HPC_SHARED_MALL_PLAYBACK_RECOVERY; targeted PR for review against main. Allocation: complexity 5, importance 5, deferability 1, impact 4; P0 playback, high priority. Recovery is the retained exact base and scoped diff. No production, DNS, or merge authority.

| Report | Observation from 012 | Intake status |
| --- | --- | --- |
| HPC-P01 | Ordinary tap enters immersive or external playback | USER_REPORTED |
| HPC-P02 | The player asks to sign in to confirm the visitor is not a bot | USER_REPORTED |
| HPC-P03 | Some videos display unavailable or content isn't available | USER_REPORTED |
| HPC-P04 | Sign-in leaves the PWA or loses browsing context | USER_REPORTED |
| HPC-P05 | Sign-in or help appears to open an unrelated browser/configuration screen | USER_REPORTED |
| HPC-P06 | Only a small subset of expected Shorts appears | USER_REPORTED |
| HPC-P07 | Grid paging or scrolling diverges from the requested Mall behavior | USER_REPORTED |
| HPC-P08 | The requested master Mall logo/navigation is absent | USER_REPORTED |

Reproduction will distinguish delivery, click routing, provider readiness and
errors, media-clock progression, device/session challenges, and return paths.
No private identifiers, cookies, authentication tokens, or raw provider payloads
belong in this record. The mobile addendum supersedes the initial horizontal
paging proposal: three portrait columns with successive vertical rows.

Release gates: in-context tap, explicit expansion and return; one active player;
complete eligible catalog; public browsing and protected member admission;
accessible fixed controls; exact-source tests, live-provider evidence, and a
physical iPhone installed-PWA check when available. An unavailable environment
is NOT_VERIFIED. The requested 20+ million Americans caption is UNVERIFIED and
outside this repair's public copy.

## Reproduction and disposition · 2026-11-11 UTC

Live baseline at 03:39–03:44 UTC: `https://hpc.foundups.com/` returned HTTPS
200 and the shell redirected to `https://hpc.foundups.com/member/`. The player,
tile field, projection, public catalog and service-worker bytes matched their
main `375964c704` blobs; the activated service worker was `pfmall-member-v6`.
These scoped asset matches are distinct from the previous Firebase release
receipt (`4f3974af5ca48c4b`), and from the recovery branch.

The independent investigator used Windows 11 build 26200, Chromium
143.0.7499.4, a fresh normal browser context, touch emulation at 390 × 844, and
one unchanged network. Playwright observed the cross-origin provider UI as a
test tool; the Mall application cannot inspect it.

| ID | Evidence and status | Mitigation or next action |
| --- | --- | --- |
| P01 | REPRODUCED on all five deployed IDs. Tile click → `togglePlay` with `fixedVideoField` → immersive. Top URL remained `/member/`. The PWA code did not open the YouTube site on tap. | IMPLEMENTED: shared full-width inline row. Corner button, pinch-out and explicit expand action are immersive. |
| P02 | USER_REPORTED / NOT_REPRODUCED. No bot prompt, autoplay block or provider error appeared in the desktop run. No supported evidence attributes the reported challenge to Mall routing, missing identity, or the operator's account. | Explicit provider diagnostics and recovery. Collect physical iPhone installed-PWA evidence if the challenge recurs. |
| P03 | USER_REPORTED / NOT_REPRODUCED. The five deployed IDs reached ready → playing and advanced time. The Data API's availability and embed flags are a separate gate. | Distinguish unavailable, embed-disabled and configuration failures; offer the creator's original source. |
| P04 | USER_REPORTED / NOT_REPRODUCED. No sign-in navigation occurred. An exact sign-in URL or chain is unavailable. | Keep public discovery open; persist scope and anchor through ordinary Back. Verify an actual login return only if supported authentication becomes necessary. |
| P05 | USER_REPORTED / NOT_REPRODUCED. No help or configuration redirect occurred. The reported wording cannot identify an OS screen. | Capture the actual public URL chain on the affected device if repeated. |
| P06 | REPRODUCED. The reviewed config, generated projection, delivered catalog and renderer all had the same five IDs. No hidden paging filter dropped records. | IMPLEMENTED: reviewed eight-ID projection and repeatable public source audit. |
| P07 | REPRODUCED. Live showed five static thumbnails with no fixed action dock or progressive collection. Desktop three-column tiles measured about 120.94 × 215 CSS px. | IMPLEMENTED: three portrait columns, vertical batches, explicit end state, fixed chrome and stable-ID return. |
| P08 | REPRODUCED. The scoped CSS hid the existing dog link and bottom anchor. `playfoundups.com` returned NXDOMAIN for A, AAAA, NS and CNAME on 2026-11-11. | IMPLEMENTED: existing brand link to verified `https://foundups.com/member/`; existing shell bottom anchor hosts Voice. |

Five-ID baseline order: `BXCzUOh9Y8M`, `fp2BkIS2FNI`, `DDAfdpJeUP0`,
`Pdz1Q5tHmJQ`, `urXOSlVgPdk`. Each iframe and YouTube player request returned
200. After state `1` the sample times advanced from 0 to approximately
0.557, 0.388, 0.253, 0.706 and 0.363 seconds. The browser generated
`Referer: https://hpc.foundups.com/`; the embed had `origin` and `enablejsapi=1`,
autoplay and encrypted-media permissions and no sandbox. The live document
used `strict-origin-when-cross-origin`; no response CSP or Permissions-Policy
header was observed. The live embed omitted `playsinline`. Click, constructor
and ready had active user activation in this browser, which does not establish
the same outcome in other modes.

A browser-local, same-origin reference using the official API, the same five
IDs, device and network, and a 356 × 300 player with `playsinline=1` also played
all five (time advanced about 0.419–1.217 seconds). Its synthetic top-level
fixture was not a deployment and did not modify provider requests. This A/B
rejected a universal failure in either embed, not the device-specific reports.
The shared player also referenced an undefined ended callback. The recovery
defines queue-end behavior and validates stale callbacks before acting.

The observed civic return was `https://hpc.foundups.com/member/` →
`https://vote.mtrout.com/contact` → browser Back to the exact original route.
The apex query entry performed the same round trip and retained `?foundup=hpc`.
This is Vote's manual contact resource. No separate Voice engine or Google
login was involved.

## Source reconciliation

Official public channel `UC-LSSlOZwpGIRIYihaz8zCw`, uploads playlist
`UU-LSSlOZwpGIRIYihaz8zCw`. Terminal pagination at 03:54 UTC returned 86 pages,
4,256 unique IDs, zero duplicate IDs, and 86 official `videos.list` batches
with all 4,256 rows. The separate channel statistics count was 4,423; the 167
difference is unexplained and outside the observable uploads collection.
Title, description, hashtags within them, and each separate snippet tag
matched 19 items; there were zero tag-only additions. All 19 were public and
embeddable with no region restrictions reported. Of those, 14 appeared on the
public Shorts shelf and returned Shorts routes; five redirected to watch.
Eight Shorts met the existing Schumer-centered editorial rule. Eight are
included; the actual candidate rendered eight. No retained record was
excluded for an unavailable thumbnail or duplicate video ID.

| Excluded video IDs | Reason |
| --- | --- |
| `TSULgvrOjVw`, `3wRtfnkpZVU`, `sOXP9HklKA4`, `y4KHfSpEzZs`, `LDHYjA4VQY4` | Canonical Shorts URL redirected to watch; `3wRtfnkpZVU` is a live entry. |
| `bJIbM5TWLAY`, `hn7Pr4spUWQ` | AntifaFM music/midterm content matched a mixed-topic description. |
| `B0P1Zci5Pxo`, `d4_GIla3VZg` | Stephen Miller-led and Georgia co-topic, respectively. |
| `xptQ0bkIZeg`, `ayR6bG_qANw` | Jeffries-led and joint Jeffries/Schumer campaign respectively; retained the existing Schumer-centered rule. |

The three added Shorts are `iJuguXpbRR4`, `sSzWdw7MNjs` and `OTTz58wPi24`.
The two similar satire records have different IDs, durations and portrait
frames; the repeated copy alone did not establish duplicate footage. All eight
portrait thumbnails returned HTTPS 200 using `oardefault.jpg`. The older
`oar2.jpg` variant returned 404 for `sSzWdw7MNjs`. Creator, title, time,
editorial label and original Shorts URL remain in the reviewed projection.

Repeat the read-only audit through the catalog owner with an existing public
Data API key in `YOUTUBE_API_KEY`: `python scripts/refresh_mall_catalog.py
--audit-scoped-source hpc` (one command). The API does not certify Shorts
membership or playback; review public Shorts routes and candidate policy
before updating `modules/foundups/hpc/mall_projection.json`. Regenerate using
`python scripts/refresh_mall_catalog.py --scoped-only --apply`.

## Candidate and rejected approaches

The existing tile renderer appends six-card batches, retains three columns
and one active shared player. Its full-row iframe exceeds the 200 × 200 minimum
at the verified widths. Below 120 × 70 on the thumbnail, tap selects the player
and the explicit Play video action supplies a new gesture. Scripted playback
requires over half the iframe area visible. No page-load autoplay is requested
for the grid. Inline and immersive share the same iframe; closing removes it
and restores the original tile/anchor. Stage feedback and navigation sit outside
provider controls. Scrolling away or backgrounding pauses without auto-resuming.

Provider readiness, state, errors, blocked autoplay, bounded timeout and
unknown outcomes have separate local evidence. Codes 2, 5, 100, 101/150 and
153 respectively map to invalid configuration, playback failure, unavailable,
embedding disabled and client identification. A source link is a fallback;
it is not proof of in-Mall playback. Rapid switching invalidates stale provider
callbacks. The product does not try to read the cross-origin challenge screen.

An unchanged narrow thumbnail cannot be the player viewport. A second grid,
new provider library, overlay or clipped controls would not address the
provider constraint. YouTube privacy-enhanced embedding and the existing API
still respect the provider's restrictions. No credential transfer, spoofed
referrer, network switching, page scraping, or challenge bypass was attempted.
FoundUps sign-in, Google API authorization and an embed session are separate.
WebKit Home Screen apps may receive initial first-party cookies and keep
subsequent website data separate; Google restricts OAuth in developer-controlled
embedded agents. A speculative login gate was rejected. The existing HTML5
delivery path is available for authorized original media; no original HPC
video assets were found. Facebook remains a roadmap item: official Meta player
and SDK documentation returned HTTP 429, so API, event and access support
remain NOT_VERIFIED. No channel website is framed.

## Verification and learning

- Local deterministic regression: `public/member/tests/mall_scoped_video_browser.py`
  exercises the real shell with 31 mock clips, three columns, vertical paging,
  fixed chrome, error classification, one iframe, minimum dimensions, same
  iframe after expansion, Back/close, deep Voice return and landscape anchor.
  `test_mall_video_catalog.py` exercises two uploads pages, deduplication,
  all-batch metadata, tag-only matching and generated byte parity.
- Independent real provider candidate on Chromium 143 / Windows 11 at 390 × 844:
  all eight played in a 369.2 × 226.2 CSS px inline iframe and advanced over
  0.25 seconds. Real localhost Referer, origin, enablejsapi, controls, and
  `playsinline=1` were observed. Expansion retained the same iframe and an
  advancing timeline; close restored focus and removed the provider frame.
  Candidate cache was `pfmall-member-v7`. No challenge or error was observed.
- Independent narrow-screen verification at 04:07 UTC used 320 × 700
  Chromium with a 97.6 × 173.5 tile and 299.2 × 200 inline player. The visible
  Play video control started `iJuguXpbRR4` and advanced 0.031 → 0.287 s.
  Host Close retained focus; Escape removed the iframe and restored the tile.
  Player SHA-256 `f23a2a82a15031c4ae800c3789ec64b57d9bbf51dd71f2e2c850889e1afcb6cd`.
  This covers the focus correction after the 04:05 all-eight probe.
- The first compact-header candidate was retested at
  04:12:40–04:13:08 UTC. All eight at 390 × 844 and the manual case at 320 × 700
  reached playing and advanced by more than 0.25 s. The local v7 cache
  controlled the page. Every observed embed returned HTTP 200 with the
  naturally generated localhost Referer. The first expansion kept the iframe;
  all nine closes restored the selected tile. The three decoded-grid/player
  screenshots and public-only playback receipt are in the local task outputs.
- PR #2357's first secret scan rejected an existing exact-reviewed finding
  after the shared HTML file changed. The repair now keeps that HTML identical
  to base, including its reviewed auth metadata, and moves only the scoped
  topic and Voice controls through the existing projection owner. The scan
  rules and approvals are unchanged. Cache v7 reloads the existing public
  asset URLs with credentials omitted; the query suffix is not the cache
  generation. A Chromium upgrade probe confirmed fresh bytes replaced a warm
  HTTP response, v6 was retired, another app's cache survived and the catalog
  and shell reopened offline. An already open page must reload to run the
  newly cached JavaScript after activation.
- Post-correction Chromium replay completed at 04:30:57 UTC with all eight
  Shorts advancing at 390 × 844, plus manual Play at 320 × 700. Each tested
  embed response returned HTTP 200 with the expected Referer; the first
  inline-to-immersive transition kept its iframe, and all nine closes removed
  the frame and restored focus. The local receipt hashes the final runtime.
- Focused route, field, player, state and catalog checks: 503 passed. Existing
  ordinary Mall responsive browser checks passed. A final broad member and
  catalog suite returned 1,540 passed with 11 failures confirmed at the base;
  these are legacy global catalog shape and navigation copy expectations.
  The separate catalog refresh safety suite passed all 12 tests.
- Real physical iPhone Safari vs Home Screen PWA, P02–P05, and Meta remain
  NOT_VERIFIED. Do not infer these passes from desktop mobile emulation.
  Next: collect iPhone browser/standalone playback and return evidence before
  promotion. No merge or deployment of this recovery was authorized.
- This canonical record supersedes the initial tap-to-immersive contract only
  for the recovery candidate. Brain consolidation is not runtime-admitted.
  The Memex current-state adapter is read-only. The permitted episodic
  breadcrumb contains a pointer and verified outcomes, with no credentials,
  private data or reasoning traces. Holo semantic authority head mismatch
  leaves freshness UNKNOWN; use the owner-helper lexical bundle and exact repo
  paths until an admitted semantic authority matches this source.

Official sources accessed 2026-11-11:

- [YouTube IFrame Player API events and errors](https://developers.google.com/youtube/iframe_api_reference)
- [YouTube player parameters](https://developers.google.com/youtube/player_parameters)
- [YouTube minimum functionality and client identification](https://developers.google.com/youtube/terms/required-minimum-functionality)
- [YouTube Data API pagination](https://developers.google.com/youtube/data/guides/implementation/pagination) and [video metadata](https://developers.google.com/youtube/v3/docs/videos)
- [Google Identity authentication vs authorization](https://developers.google.com/identity/gsi/web/guides/integrate) and [OAuth policies](https://developers.google.com/identity/protocols/oauth2/policies)
- [WebKit video activation policies](https://webkit.org/blog/6784/new-video-policies-for-ios/) and [Home Screen website data](https://webkit.org/blog/14787/webkit-features-in-safari-17-2/)
- [Meta embedded player](https://developers.facebook.com/docs/plugins/embedded-video-player/) and [SDK API](https://developers.facebook.com/docs/plugins/embedded-video-player/api/) (retrieval rate-limited)
- [FoundUp Memex boundary](../../../docs/adr/ADR_REDDOG_FOUNDUPS_SECOND_BRAIN_BOUNDARY.md) and [HoloIndex retrieval boundary](../../../docs/adr/ADR_OPENCLAW_MEMORY_HOLOINDEX_BOUNDARY.md)

## 2026-11-12 · Desktop layout recovery in PR #2359

At the start of this pass, live Firebase version 25aefb1f3c293a98 served
pfmall-member-v7. Sampled public runtime bytes matched main 990e320. In a fresh
1440 × 900 Windows Chromium session, the scoped grid showed three 469 px tiles
across and opened the player below the row. The original draft 895118a used
six CSS columns with a three-column JavaScript row calculation.

The responsive candidate uses the existing player, queue, field slot and
catalog matcher. Desktop starts muted on an eligible clip and advances the
scoped queue. Search leaves the active clip running. Touch keeps the inline
row and immersive controls. Repositioning tiles around the slot keeps the
provider iframe connected. The existing tab-local state retains the desktop
query and video ID for Back from Vote. The v8 cache migration keeps existing
public asset URLs and the unrelated caches.

A candidate preview on the HPC origin with real YouTube observed advancing
media time for desktop startup iJuguXpbRR4, natural advancement to
sSzWdw7MNjs, search selection of OTTz58wPi24, and 390 px emulated touch
inline playback. Chromium and WebKit fixtures verified selection, queue
advancement, manual Play, resize continuity and Back. Physical iPhone
standalone remains NOT_VERIFIED. The phone search and thumb dock are open
roadmap work. GitHub checks, merge, and hosting deployment each have separate
receipts.

## 2026-11-12 · Installed iPhone embed refusal

012 reported “This content isn't available” on the first Short
`iJuguXpbRR4` in the installed iPhone app. The purple Mall message in
the photo maps to YouTube error 101 or 150. The precise code and trigger
are unverified. At 13:50:42 UTC, the public Data API returned public,
processed and `embeddable=true`, with no reported age or region restriction.
YouTube documents that platform policies or claims can still block an embed.

All eight live Shorts advanced in a phone-sized WebKit 26 window on
Windows 11. The first also advanced in Chromium 143, on the v10 preview
and in a same-origin browser-local official embed. The live iframe was
369.2 × 226.2 CSS px with the browser-generated Referer, `enablejsapi=1`
and `playsinline=1`. Manual Play advanced the first clip at 320 px.
The [v10 identity and dock PR](https://github.com/FOUNDUPS/Foundups-Agent/pull/2366)
merged as `7d6ea553f` and passed main CI. The tested Firebase preview was
`f3d88fad9c24ea16`. The dedicated production host served v7.

Compare the same first tile in Safari and the Home Screen app on the
physical iPhone. The original Short link is the immediate fallback. The
shared native player can use a rights-cleared original MP4 for owned media.
The workspace search found no original file for this ID. Retain source
attribution and verify byte-range delivery if a file is supplied.

012 separately rejected the placement of the player below the selected row.
The touch grid now replaces the selected thumbnail with the shared player
across the original row. This is a placement change. Device playback remains
an independent gate.

[IFrame errors](https://developers.google.com/youtube/iframe_api_reference#onError) ·
[Video metadata and embed restrictions](https://developers.google.com/youtube/data/reference/rest/v3/videos)
