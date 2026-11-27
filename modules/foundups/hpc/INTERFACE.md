# HPC interface

## Current v26 acceptance delta — 2026-11-27

Follow the shared navigation contract's v26 continuation: Dock + only settings,
Full Video LEFT next; Floating RIGHT hide and tucked actions unchanged. The dog
inside the banner returns to the Mall, the artwork opens the campaign, and Home
in Dock + restores HPC tiles. Preserve source attribution/disclosure and the
manual civic-resource link. Autoplay never permits hidden YouTube playback.

The Tile types picker connects Video only; Image/Podcast remain disabled pending
real collection integration. Add Video remains gated by the existing shared
admission boundary; its unavailable review is not an operational editor or
proof of current server-side membership/editor eligibility.

## 2026-11-25 — Home, bottom dock and tucked selection

The [shared interaction contract](../../../public/member/INTERFACE.md#2026-11-25--scoped-home-shared-theater-dock-and-hidden-selection)
owns this candidate. Fresh desktop opens WikiTube/theater; the HPC artwork or
Home returns to HPC tiles and remembers that choice in this tab through reload
and resize. Phone keeps its three-column field. The exact shared actions/search
dock sits below the app thumbnail queue in theater and floats below grid content.
Its plus opens Available actions. The distinct grid plus opens gated Add Video;
no submission service or editor authorization is implied.

Right swipe on the tucked rail now defaults to selecting Next while staying
hidden. The pending selection starts no provider work. Tap restores it paused;
visible Play starts playback. Explicitly saved next/reveal remains available.
Touch restoration does not depend on the browser emitting a compatibility click.
This supersedes the November 23 default. Physical Safari/Home Screen and
production delivery remain separate gates; no new Voice or model is delivered.

## 2026-11-23 — Clean video gestures and local DAEmon candidate

**IMPLEMENTED_CANDIDATE.** Shared owners now supply clean app video surfaces,
configurable right-swipe queue/reveal actions, full-height external gesture grip
and opt-in bounded current-tab DAEmon. See the [shared member interaction contract](../../../public/member/INTERFACE.md#2026-11-23--clean-video-gestures-and-local-daemon-candidate) and
[canonical media incident](../pfmall/MEDIA_PLAYBACK_INCIDENT_HPC.md).
Native provider controls and ordinary desktop theater remain; physical phone
and production acceptance are open. No model, mic or backend service is added.

## 2026-11-22 — Phone control clarification

HPC consumes the shared [floating control contract](../../../public/member/INTERFACE.md#2026-11-22--floating-controls-and-camera-candidate).
The player can be moved using persistent app-owned frame targets, tucked to a
video-height restore rail and expanded by the configured outward pinch. Its
YouTube interior retains native input. Hidden playback pauses; visible autoplay
and reveal-on-selection remain separate settings. The dock camera delegates to
AutoPost, and the dock dog opens canonical conversation/availability in-place.
An unavailable service is not a voice or browser-model implementation. Current
candidate qualification and phone evidence are recorded in the roadmap/incident.

## Entry and authority

| Surface | Contract |
| --- | --- |
| `/f/hpc` | WSP 104 public discovery landing, generated from the FoundUp registry. `#red-dog` opens its existing public Red Dog briefing. |
| `foundups.com/member/?foundup=hpc` | Same collection for admitted members. The existing sign-in, invitation and username checks run before the projection mounts. |
| `hpc.foundups.com/` | Public entrance. The dedicated host selects the guest projection at `/member/`. |
| `/f/hpc/app` | Existing protected tenant handoff. HPC declares no tenant bundle, account grant or agent routes. |
| Voice Your Opinion | The phone header's right action opens Vote's manual [Contact Congress with the HPC skin](https://vote.mtrout.com/contact#hpc). The public projection carries the registered skin fragment; no browser referrer is required. Desktop keeps the action in the bottom anchor. Back restores the video anchor and offset. |
| HPC header artwork / Home | Return to the HPC-scoped tile field, keeping the current URL and tab-local position/presentation. The separate Play Mall link opens the master Mall; the independent-site disclosure retains the campaign link. |
| HPC Home Screen app | `hpc.webmanifest` registers **Hasan Piker Coalition**, short name **HPC**, with a scoped launch URL and standalone display. The supplied satirical artwork provides the portrait and 180 px Apple touch icon. |

The registry's `parent_foundup_id: voteballots` expresses the editorial and civic relationship. It delegates no access, ownership, wallet, token or execution authority. HPC uses the FoundUp manifest namespace `idb_hpc`. The shared Mall state owner stores the tab-local video anchor, offset and scoped query. Shared player saves and history remain browser-local and keyed by FoundUp and video. The dedicated host is available to guests. The same-tab member sign-in return stores the registered scope and is consumed after admission. Server-side capability checks retain authority.

## Media contract

`mall_projection.json` is the curation input. YouTube is authoritative for creator, video ID, title, publication and availability. The November 11 source pass found the eight reviewed Shorts below. The November 25 refresh extends this collection to regular videos, including [HasanAbi 4 House Speaker](https://www.youtube.com/watch?v=8qO3908bKAM), verified as public, embeddable and 5,990 seconds long. Duration or title does not establish Shorts membership.

Run `python scripts/refresh_mall_catalog.py --refresh-scoped-source hpc --seed-live --discover --apply` with the existing public `YOUTUBE_API_KEY`. Without `--apply`, refresh writes nothing. This mode writes only HPC curation, the scoped public catalog, and HPC audit artifacts; it does not refresh the general Mall. The older `--scoped-only` generator remains the offline projection owner.

Only the established Move2Japan channel `UC-LSSlOZwpGIRIYihaz8zCw` is approved for automatic admission. Case-insensitive matches must occur in the actual title, description or tags for SchumerOUT, HasanForSpeaker or Hasan4Speaker. Metadata must show public, processed and embeddable, without region/age restrictions or live/upcoming status. Missing/ineligible existing entries remain in curation but are excluded from publication. New records carry actual per-video creator credits and a neutral Commentary label; content genre is not inferred from a headline. Preserve existing editorial labels, IDs and relative queue order, and append new matches in publication order. Existing reviewed Shorts retain portrait presentation; new entries use ordinary watch URLs and thumbnails.

Recorded `editorial_exclusions` preserve the six content decisions in the [source reconciliation](../pfmall/MEDIA_PLAYBACK_INCIDENT_HPC.md#source-reconciliation) and the four isolated diagnostic-only IDs (nine unique IDs, with one overlap). A matching hashtag does not reverse a review hold. An explicit curation review must remove the recorded hold before a later refresh may admit that video. These are editorial dispositions, not assertions of current YouTube unavailability. Historical format-only exclusions do not apply to the new regular-video requirement.

The product workflow runs every six hours at 03:17, 09:17, 15:17 and 21:17 Japan time. It performs a bounded complete uploads scan to catch changed hashtags on older uploads, with incremental admission by video ID. At the observed 4,345 uploads this used 175 Data API requests per source scan. Three broader discovery searches add about 300 quota units per run; candidates from new channels remain `proposed` in `hpc_discovery_proposals.json`. Search snippets are reconciled with real video metadata. No new source is auto-approved.

Refresh receipts expire after 24 hours and bind the exact generated catalog bytes. Publication uses `scripts/publish_hpc_catalog.cjs`, which clones the current live Hosting version and changes only HPC's videos/count in existing root/versioned public catalogs. It compares every other file hash and the Hosting config, rechecks the live head before release, and reads back both public catalogs. The saved prior version is the rollback target. Firebase supplies no atomic release precondition; observed head checks reduce that remaining concurrency window. The hosted runner owns timeout/cancellation and process cleanup; overlaps wait, missed runs are skipped, and the next full scan catches up. A failed source/security/release check preserves the current release and requires inspection of its receipt before retrying.

The [source receipt](../../../docs/audits/pfmall_youtube_ingest/hpc_refresh.json), [workflow runs](https://github.com/FOUNDUPS/Foundups-Agent/actions/workflows/hpc-wikitube-refresh.yml) and ModLog record configuration, execution and publication separately. This is a product job, not a personal reminder or modification of YouTube recommendations.

The collection is creator commentary and satire, with political opinion and advocacy labeled separately from factual reporting. A headline or description is the creator's wording. Vote's contact resource links to official directories.

| YouTube ID | Published UTC | Editorial label |
| --- | --- | --- |
| [iJuguXpbRR4](https://www.youtube.com/shorts/iJuguXpbRR4) | 2026-11-11 01:00:25 | Opinion |
| [sSzWdw7MNjs](https://www.youtube.com/shorts/sSzWdw7MNjs) | 2026-11-10 22:00:29 | Satire |
| [BXCzUOh9Y8M](https://www.youtube.com/shorts/BXCzUOh9Y8M) | 2026-11-08 11:00:22 | Opinion |
| [OTTz58wPi24](https://www.youtube.com/shorts/OTTz58wPi24) | 2026-11-08 02:36:49 | Opinion |
| [fp2BkIS2FNI](https://www.youtube.com/shorts/fp2BkIS2FNI) | 2026-11-07 20:00:02 | Opinion |
| [DDAfdpJeUP0](https://www.youtube.com/shorts/DDAfdpJeUP0) | 2026-11-07 19:23:30 | Opinion |
| [Pdz1Q5tHmJQ](https://www.youtube.com/shorts/Pdz1Q5tHmJQ) | 2026-11-07 17:14:22 | Satire |
| [urXOSlVgPdk](https://www.youtube.com/shorts/urXOSlVgPdk) | 2026-11-07 14:00:24 | Opinion |

The [shared incident](../pfmall/MEDIA_PLAYBACK_INCIDENT_HPC.md#source-reconciliation) records excluded IDs, title/description/tag coverage and the difference between metadata eligibility and observed playback.

## Interaction contract

The global Mall tap starts or toggles lane playback, and pinch-out on a channel
expands its video field. The HPC projection uses the same player and catalog in
two layouts. On a wide desktop with a fine pointer and hover, the centered
player opens above HPC search and a horizontal thumbnail strip. The first
clip requests muted autoplay. The shared queue advances on a provider end
event and offers Play when the browser blocks startup. The compact search bar
is centered under the video. Typing filters the queue while the clip plays.
Enter or the search button starts the next match, with the first match used
when the current clip is outside the results or last.

The touch grid displays #SchumerOUT in three portrait columns with vertical
batches and an end state. Tap or Enter uses the configured shared Floating,
WikiTube or Full Video path. The default Floating player stays above scrolling
tiles; the app's external grip and accessible Video actions change its view.
Close, Escape, Back or configured pinch-in restores the tile and focus. YouTube owns touches
inside the iframe. The provider viewport is at least 200 × 200. A thumbnail
below 120 × 70 selects the player and offers explicit Play. [YouTube embed requirements](https://developers.google.com/youtube/terms/required-minimum-functionality).

The header shows the loaded Mall build beside #SchumerOUT. The same number
appears in **More options**.

The shared floating phone dock puts **Available actions** at the left, scoped
search in the middle, **AutoPost camera**, and **Red Dog** at the
right. Longer queries expand into an editable field above those controls. Search
submits against the loaded collection. Its results keep the source IDs and
the same shared player. Keyboard dictation remains controlled by the browser.
The visitor submits the resulting query. **Available actions** opens
Home, the independent-site disclosure, and device-model availability. The
Browser AI shows its unavailable state until an admitted model is connected.
Red Dog uses its in-page conversation/availability owner. It does not navigate
to another FoundUp or claim that a model or microphone is connected.

The expanded viewer keeps the shared search/actions dock below its
horizontally scrollable app queue. Filtering during playback keeps the active
iframe and stays within the HPC collection. The scope-specific options and
public briefing do not grant member or agent access.

Viewport changes keep the active iframe and selected video. If a desktop
selection falls outside the phone filter, its tile appears alongside the
filtered results while the player is open. Tab-local state retains the tile
anchor, theater selection and queries for return. Physical iPhone Home Screen
install, keyboard dictation and standalone handoffs require device verification.
An earlier Mall shortcut can be replaced with a fresh install to pick up the
HPC identity.

The player provides local Save and Share. HPC shares the original Short URL. A save is a bookmark. The preference selector, verification and valuation have separate roadmap gates.

## Dream Team and Press Wire design — 2026-11-17

012 requests small top controls switching the existing tile field between
Videos, Dream Team, Hasan Clips and Press Wire. Preserve the existing banner
asset and shared grid/player. Inspect the live banner before claiming it is
missing or replacing it. Default entry selection remains unresolved; keep
current Videos behavior until the campaign default is settled.

Dream Team uses 1990s basketball-card styling, illustrated portraits, five
starters followed by bench and coach. Paired/trio nominees share one card.
Tap/keyboard activation selects a nominee and populates the existing video
field with attributed, reviewed clips for that nominee; empty results must be
explicit. Card-back detail then Watch clips is a proposed interaction, not yet
012-approved. Preserve filter, tile anchor, scroll/focus and one active player
on return. New source discovery requires review before catalog admission.

The following is 012-supplied fictional campaign casting. Nicknames, stats,
offices and legislative provisions are satire, not real appointments,
measured performance, agreements, pledges or endorsements. No nominee
participation is verified. Display the existing independence disclosure and
“satirical scouting stats.” Portrait provenance and rights remain required.

| Card | Court position | Nominee / source | Nickname | Proposed House role | Satirical stats | Fictional provision |
| --- | --- | --- | --- | --- | --- | --- |
| CARD-01 | PG / floor general | Hasan Piker (HasanAbi) | The Twitch Tweaker for Speaker | Speaker / asymmetric attention shield | 8.0 HRS/DAY; 99% DUP meltdown; 100% contagious HPC/HPV | Bikini roll call and Rotunda clawfoot-bathtub appropriations. |
| CARD-02 | SG / perimeter sniper | Mehdi Hasan (Zeteo Media) | The Interrogation Assassin | Chief House Subpoena Prosecutor / engine | 45.2 WPM; 0 lobbyist escapes; 98% receipts accuracy | Replace five-minute questioning with 45-minute live grillings and unmutable mics. |
| CARD-03 | SF / all-around wing | Sam Seder and Emma Vigeland (Majority Report) | The Parliamentary Pick-and-Roll | House Rules and Floor Whip Desk / engine | 100% policy breakdown; +85 Social Security defense; 0 debate dodgers spared | Cloakroom debates on the 50-State Israel Package. |
| CARD-04 | PF / paint enforcer | Ryan Grim and Jeremy Scahill (Drop Site News) | The FOIA and Leak Bruisers | Chair of Oversight and Receipts / engine | 99.4% cable recovery; 100% dark-money audit | Super-PAC receipts on the House jumbotron; proposed link to https://oversight.vote.foundups.com. |
| CARD-05 | C / rim protector | Brace Belden and Liz Franczak (TrueAnon) | The Deep-State Shot Blockers | Sergeant-at-Arms and K-Street Counter-Intel / engine | 12.4 BPG; 100% eye-emoji audit | Blacklight and polygraph inspections after fictional billionaire-island visits. |
| CARD-06 | Sixth man / instant offense | Will Menaker and Felix Biederman (Chapo Trap House) | The Locker-Room Hecklers | Press Gallery and Slam-Poetry Demolition | 99.9 heckle efficiency; -100 Jeffries rhyme morale | Balcony commentary on House speeches and alliteration. |
| CARD-07 | Bench / tub production | Will Neff, QTCinderella and AustinShow (Fear&) | The Bathtub Diplomacy Crew | Rotunda Tub-Summit Producers | 100% normie conversion; waterproof lav-mic certified | Operate Epsom-salt jets and waterproof boom microphones. |
| CARD-08 | Bench / suburban crossover | Jennifer Welch and Angie Sullivan (I've Had It) | Red-State Wine-Mom Wrecking Crew | Suburban Voter Whip and Donor Shaming | 0% patience for corporate BS; “Most Radical Pod in N.A.” promotional copy | Country-club brunch confrontation over a discharge petition. |
| CARD-09 | Head coach and GM | Mike Trout / 012, with 0102 as agent | The Architect | HPC Executive Director | Campaign contact: 202-656-6012; hasan4speaker@foundups.com | Calls proposed Nash-blocking plays; “binary stakeholder (0/1) Zazen hammer” is campaign wording, not a replacement for shared governance. |

Data projection requirements: stable card_id, court_position, nominee_names,
source_brand, nickname, proposed_house_role, shield_or_engine, satirical_stats,
fictional_provision, portrait_asset_ref, portrait_provenance,
reviewed_video_ids, editorial_label and endorsement_status. Missing assets and
clips remain null/empty, not invented URLs. The supplied `/draft/` voting route
is proposed only; shared preference/ballot ownership must be qualified before
displaying live voting or vote totals.

Press Wire contains dated HPC-published satire with permanent release IDs and
clear independence/nonendorsement labels. Onion/Spy Magazine are tone
references, not asserted publishers. Keep the original 2026-11-17 brief as
source material in the linked existing HPC outreach record. Its bikini accord,
bathtub summits and 50-State Israel Parity Act are fictional proposals.
Validate constitutional wording, Congress/session dates, welfare comparisons,
claimed whip commitments and attributed quotes before any factual publication.
Do not imply the nominees signed agreements, AOC pledged a vote, or Piker
announced a candidacy. Do not convert unsupported criminal allegations into
news-wire facts. Publication, draft voting, banner deployment and outreach
require separate evidence.
