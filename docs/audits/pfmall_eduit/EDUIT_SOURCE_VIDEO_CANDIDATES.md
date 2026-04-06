# EDUIT Source Video Candidates

**Worker C** · `PFMALL_EDUIT_DERIVED_LANE_FEASIBILITY_PHASE1` · 2026-04-05

---

## Source Channel

All candidates live on `undaodu` (YouTube @UnDaoDu, channel_id `UCfHM9Fw9HD-NwiS0seD_oIA`).
EDUIT has no YouTube channel of its own — these are 012's videos about EDUIT/eSingularity topics.

## Selection Method

Title-match scan across 512 `undaodu` videos for keywords: `eduit`, `esingularity`, `e-singularity`, `hapticsign`, `haptic sign`, `autonomous learning`, `education technology`.

**Result: 21 candidates out of 512 videos (4.1%).**

## Candidate List

| # | video_id | Title | Date | Dur |
|---|----------|-------|------|-----|
| 1 | `fk5ZwzIDIFk` | Eduit: The vision | 2026-01-13 | 6m |
| 2 | `36gnsogfqYI` | EduIT CEO Michael Trout | 2026-01-12 | <1m |
| 3 | `W5TakB17F14` | eSingularity Educational Initiative | 2026-01-12 | 7m |
| 4 | `KXt1DtmE3XA` | The eSingularity | 2026-01-12 | 8m |
| 5 | `NUh28WcX404` | Three Stages of eSingularity | 2026-01-12 | 3m |
| 6 | `JR_7biWI6fg` | Will eSingularity Happen in 10 Years? | 2026-01-12 | 8m |
| 7 | `HUneSmY_9sQ` | The eSingularity Platform: Every Child | 2026-01-12 | 3m |
| 8 | `xbuqnDLKoH8` | Part 3: The eSingularity (The Solution) | 2026-01-12 | 7m |
| 9 | `xmddOFcp__o` | Why this book is important, E-Singularity. | 2026-01-12 | 6m |
| 10 | `UrlE9HLh6L8` | Education ESingularity Prize, Global Education Prize | 2026-01-12 | 8m |
| 11 | `mSam-JyF7qQ` | The eSingularity Prize for Global Education | 2026-01-12 | 5m |
| 12 | `Kge-icfXJl8` | The Esingularity Prize | 2026-01-12 | 5m |
| 13 | `6ut-dfG3fpg` | e-Singularity Prize | 2026-01-12 | 8m |
| 14 | `Rhvuc5FrdkQ` | Education and E-Singularity - Middle School and High School | 2026-01-12 | 5m |
| 15 | `pXXlbAqDJOI` | Impact of E-Singularity on Higher Education | 2026-01-12 | 8m |
| 16 | `EfMZVAm6NPE` | Why is Flattening Global Education Important? | 2026-01-12 | 7m |
| 17 | `uWr8rS8y9NE` | Michael Trout: eSingularity Will Collapse Certification Industry | 2026-01-12 | 3m |
| 18 | `Lz08gejqSUw` | ESINGULARITY Commercial Ad Strategy by Michael Trout | 2026-01-12 | 2m |
| 19 | `pY4ZWArX4g8` | The Blood for Esingularity | 2026-01-12 | 4m |
| 20 | `CjVyzXvAXhg` | Video blog - E-Singularity | 2026-01-12 | 2m |
| 21 | `9W4O4c3CVwo` | Using Nintendo 3DS as Alpha eSingularity Platform | 2026-01-12 | 9m |

**Total runtime**: ~114 minutes across 21 videos.

## Classification Confidence

| Confidence | Count | Examples |
|------------|-------|----------|
| HIGH (title says EDUIT) | 2 | "Eduit: The vision", "EduIT CEO Michael Trout" |
| HIGH (eSingularity core topic) | 14 | All "eSingularity" titled videos — eSingularity IS EDUIT's product |
| MEDIUM (education + singularity) | 5 | "Why is Flattening Global Education Important?", "Impact of E-Singularity on Higher Education" |

All 21 are defensible. eSingularity is EDUIT's educational platform product — confirmed by `social_accounts.yaml` line 76 which lists `esingularity` as a posting event type under the `eduit` account.

## What This Means

- Worker D's audit reported "2 videos" — that only counted explicit `Eduit` in title
- Actual count is **21** when including eSingularity (EDUIT's product)
- This is enough content for a meaningful pfMALL lane (more than `antifafm` at 34)

---

**Evidence**: Direct scan of `mall-video-catalog.json` undaodu lane. Cross-referenced with `social_accounts.yaml` EDUIT entry (line 66-80) confirming eSingularity is an EDUIT event type.
