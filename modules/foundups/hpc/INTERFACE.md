# HPC interface

## Entry and authority

| Surface | Contract |
| --- | --- |
| `/f/hpc` | WSP 104 public discovery landing, generated from the FoundUp registry. `#red-dog` opens its existing public Red Dog briefing. |
| `foundups.com/member/?foundup=hpc` | Same collection for admitted members. The existing sign-in, invitation and username checks run before the projection mounts. |
| `hpc.foundups.com/` | Public entrance. The dedicated host selects the guest projection at `/member/`. |
| `/f/hpc/app` | Existing protected tenant handoff. HPC declares no tenant bundle, account grant or agent routes. |
| Voice Your Opinion | The phone header's right action opens Vote's manual [Contact Congress with the HPC skin](https://vote.mtrout.com/contact#hpc). The public projection carries the registered skin fragment; no browser referrer is required. Desktop keeps the action in the bottom anchor. Back restores the video anchor and offset. |
| Hasan portrait | The header portrait opens the master Mall at `https://foundups.com/member/`. Ordinary member admission still applies there. |
| HPC Home Screen app | `hpc.webmanifest` registers **Hasan Piker Coalition**, short name **HPC**, with a scoped launch URL and standalone display. The supplied satirical artwork provides the portrait and 180 px Apple touch icon. |

The registry's `parent_foundup_id: voteballots` expresses the editorial and civic relationship. It delegates no access, ownership, wallet, token or execution authority. HPC uses the FoundUp manifest namespace `idb_hpc`. The shared Mall state owner stores the tab-local video anchor, offset and scoped query. Shared player saves and history remain browser-local and keyed by FoundUp and video. The dedicated host is available to guests. The same-tab member sign-in return stores the registered scope and is consumed after admission. Server-side capability checks retain authority.

## Media contract

`mall_projection.json` is the reviewed curation input. Run `python scripts/refresh_mall_catalog.py --scoped-only --apply` to regenerate the shared discovery card and public video projection. YouTube is authoritative for creator, video ID, title, publication and availability. The 2026-11-11 source pass found eight eligible public, embeddable Shorts. Repeat candidate discovery with `--audit-scoped-source hpc` using an approved public Data API key. Review Shorts membership and eligibility before changing curation. Tiles use original portrait thumbnails. The shared player credits Move2Japan and links to the original Short.

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
batches and an end state. Tap or Enter replaces the selected thumbnail with
the shared player across its original row. Neighboring tiles reflow. The
corner button or pinch-out on a thumbnail or the active player's toolbar
opens immersive playback with the same iframe. Close, Escape, Back or pinch-in
on the surrounding chrome restores the tile and focus. YouTube owns touches
inside the iframe. The provider viewport is at least 200 × 200. A thumbnail
below 120 × 70 selects the player and offers explicit Play. [YouTube embed requirements](https://developers.google.com/youtube/terms/required-minimum-functionality).

The header shows the loaded Mall build beside #SchumerOUT. The same number
appears in **More options**.

The shared floating phone dock puts **More options** at the left, scoped
search and its dictation microphone in the middle, and **Red Dog** at the
right. Longer queries expand into an editable field above those controls. Search
submits against the loaded collection. Its results keep the source IDs and
the same in-place player. The microphone fills the field when the browser has
local recognition available. Otherwise it focuses the field for keyboard
dictation. The visitor submits the resulting query. **More options** opens
Home, the independent-site disclosure, and device-model availability. The
Browser AI shows its unavailable state until an admitted model is connected.
Tap Red Dog to open the public read-only briefing or hold for local search
dictation on supported devices. Release the hold or tap the square **Stop**
in Red Dog's position to finish. The transcript remains editable until submitted.

The expanded viewer keeps the search pill between the video and its
horizontally scrollable queue. Filtering during playback keeps the active
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
