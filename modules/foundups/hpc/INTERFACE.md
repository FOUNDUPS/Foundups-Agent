# HPC interface

## Entry and authority

| Surface | Contract |
| --- | --- |
| `/f/hpc` | WSP 104 public discovery landing, generated from the FoundUp registry |
| `/member/?foundup=hpc` | Public, fixed video projection in the member shell |
| `hpc.foundups.com/` | Dedicated host selects the same projection at `/member/`. Hosting, DNS and TLS are release gates. |
| `/f/hpc/app` | Existing protected tenant handoff. HPC declares no tenant bundle, account grant or agent routes. |
| Voice Your Opinion | The shared bottom anchor opens Vote's manual [Contact Congress](https://vote.mtrout.com/contact) in the same tab. Back restores the video anchor and offset. |
| FoundUps dog logo | The shared header link opens the master Mall at `https://foundups.com/member/`. Ordinary member admission still applies there. |

The registry's `parent_foundup_id: voteballots` expresses the editorial and civic relationship. It delegates no access, ownership, wallet, token or execution authority. HPC uses the manifest namespace `idb_hpc`. The shared Mall state owner stores the tab-local video anchor and offset. Shared player saves and history remain browser-local and keyed by FoundUp and video. Public browsing has no sign-in, Red Dog or search gate. Server-side member checks retain authority.

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

The global Mall tap starts or toggles lane playback, and pinch-out on a channel expands its video field. The scoped field displays `#SchumerOUT` in three portrait columns with vertical batches and an end state. Tap or Enter opens a full-width player row in the Mall. The corner button or pinch-out opens immersive playback; expanding an already playing clip retains its iframe. Close, Escape, browser Back or pinch-in on the surrounding immersive surface restores the originating tile and position. There is no separate double-tap action. YouTube owns touches inside its iframe. The provider viewport is at least 200 × 200; a thumbnail below 120 × 70 selects the player and offers an explicit Play video action. [YouTube embed requirements](https://developers.google.com/youtube/terms/required-minimum-functionality)

The recovery candidate uses cache `pfmall-member-v7`; the observed deployed baseline uses v6. Real desktop Chromium playback and mocked recovery tests are recorded in the shared incident. Physical iPhone standalone remains unverified.

The player provides local Save and Share. HPC shares the original Short URL. A save is a bookmark. The preference selector, verification and valuation have separate roadmap gates.
