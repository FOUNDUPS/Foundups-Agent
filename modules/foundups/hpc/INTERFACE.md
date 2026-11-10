# HPC interface

## Entry and authority

| Surface | Contract |
| --- | --- |
| `/f/hpc` | WSP 104 public discovery landing, generated from the FoundUp registry |
| `/member/?foundup=hpc` | Public, fixed video projection in the member shell |
| `hpc.foundups.com/` | Dedicated host selects the same projection at `/member/`. Hosting, DNS and TLS are release gates. |
| `/f/hpc/app` | Existing protected tenant handoff. HPC declares no tenant bundle, account grant or agent routes. |
| Voice Your Opinion | Same-tab link to Vote's manual [Contact Congress](https://vote.mtrout.com/contact). Browser Back restores tab-local grid scroll. |

The registry's `parent_foundup_id: voteballots` expresses the editorial and civic relationship. It delegates no access, ownership, wallet, token or execution authority. HPC uses the manifest namespace `idb_hpc`. The PoC stores only its tab-local browse position through the shared Mall state owner. Shared player saves and history remain browser-local and keyed by FoundUp and video. The scoped view has no sign-in, Red Dog controls or cross-FoundUp navigation. Server-side member checks retain authority.

## Media contract

`mall_projection.json` is the reviewed curation input. Run `python scripts/refresh_mall_catalog.py --scoped-only --apply` to regenerate the shared discovery card and public video projection. YouTube is authoritative for creator, video ID, title, publication and availability. Each selected item was checked against YouTube Data API snippet, status and content details, and the public Move2Japan Shorts shelf and canonical Shorts URL. All five returned public and embeddable on 2026-11-11 JST. Availability can change at YouTube. Tiles use original YouTube thumbnails. The shared player credits Move2Japan and links to the original Short.

The collection is creator commentary and satire, with political opinion and advocacy labeled separately from factual reporting. A headline or description is the creator's wording. Vote's contact resource links to official directories.

| YouTube ID | Published UTC | Editorial label |
| --- | --- | --- |
| [BXCzUOh9Y8M](https://www.youtube.com/shorts/BXCzUOh9Y8M) | 2026-11-08 11:00:22 | Opinion |
| [fp2BkIS2FNI](https://www.youtube.com/shorts/fp2BkIS2FNI) | 2026-11-07 20:00:02 | Opinion |
| [DDAfdpJeUP0](https://www.youtube.com/shorts/DDAfdpJeUP0) | 2026-11-07 19:23:30 | Opinion |
| [Pdz1Q5tHmJQ](https://www.youtube.com/shorts/Pdz1Q5tHmJQ) | 2026-11-07 17:14:22 | Satire |
| [urXOSlVgPdk](https://www.youtube.com/shorts/urXOSlVgPdk) | 2026-11-07 14:00:24 | Opinion |

Matches centered on Jeffries, Stephen Miller or a separate Georgia topic and matches outside the Shorts format were left out of the first collection.

## Interaction contract

The global Mall tap starts or toggles lane playback for video-backed channels. A double-tap repeats the ordinary tap handling. Pinch-out on a channel expands the channel's video field with the existing FLIP transition. The scoped landing starts inside that field. Tap, pinch-out, Enter and the corner control open the selected Short in the shared immersive player. This keeps the compact cards and places the player chrome outside the iframe, with a minimum 200px player viewport. Back, Escape and pinch-in on the surrounding Mall player surface close the player and restore focus to the originating tile. YouTube owns touch events inside its iframe. [YouTube embed requirements](https://developers.google.com/youtube/terms/required-minimum-functionality)

The player provides local Save and Share. HPC shares the original Short URL. A save is a bookmark. The preference selector, verification and valuation have separate roadmap gates.
