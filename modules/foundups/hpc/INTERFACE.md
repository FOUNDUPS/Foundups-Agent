# HPC interface

## Entry and authority

| Surface | Contract |
| --- | --- |
| `/f/hpc` | WSP 104 public discovery landing, generated from the FoundUp registry. `#red-dog` opens its existing public Red Dog briefing. |
| `foundups.com/member/?foundup=hpc` | Same collection for admitted members. The existing sign-in, invitation and username checks run before the projection mounts. |
| `hpc.foundups.com/` | Public entrance. The dedicated host selects the guest projection at `/member/`. |
| `/f/hpc/app` | Existing protected tenant handoff. HPC declares no tenant bundle, account grant or agent routes. |
| Voice Your Opinion | The phone header's right action opens Vote's manual [Contact Congress](https://vote.mtrout.com/contact). Desktop keeps the action in the bottom anchor. Back restores the video anchor and offset. |
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
