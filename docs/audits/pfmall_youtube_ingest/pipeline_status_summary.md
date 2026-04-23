# pfMALL YouTube Pipeline - Status Summary

- Generated: `2026-04-23T10:07:48.359261+00:00`
- Read-only: yes (no catalog mutation, no live API calls)
- Generator: `modules/communication/youtube_channel_pull/src/status_summary.py`

## Sources

| Artifact | Path |
|---|---|
| Catalog | `public\member\mall-video-catalog.json` |
| Known-channel delta | `docs\audits\pfmall_youtube_ingest\youtube_channel_pull_delta.json` |
| Refresh log | `docs\audits\pfmall_youtube_ingest\refresh_log.json` |
| Discovery proposals | `docs\audits\pfmall_youtube_ingest\youtube_discovery_proposals.json` |
| Latest discovery review | `docs\audits\pfmall_youtube_ingest\youtube_discovery_review_result_20260413.json` |

## 1. Catalog State

- FoundUps: **13**
- Total declared videos: **1205**
- Total actual videos (sum of `videos[]`): **1205**
- Count mismatches: none

| foundup_id | title | source_type | declared | actual |
|---|---|---|---:|---:|
| move2japan | Move to Japan | youtube_channel | 594 | 594 |
| undaodu | UnDaoDu | youtube_channel | 512 | 512 |
| foundups_main | FoundUps | youtube_channel | 44 | 44 |
| antifafm | antifaFM | youtube_channel | 34 | 34 |
| linkedin_012 | 012 LinkedIn | linkedin_profile | 0 | 0 |
| linkedin_esingularity | eSingularity | linkedin_profile | 0 | 0 |
| linkedin_tsingularity | tSingularity | linkedin_profile | 0 | 0 |
| linkedin_foundups | FoundUps LinkedIn | linkedin_profile | 0 | 0 |
| eduit | EDUIT | derived | 21 | 21 |
| science_swarm | Science Swarm Hub | github_repo | 0 | 0 |
| autopost | AutoPost | external_app | 0 | 0 |
| kosei | Kosei AI Systems | internal_service | 0 | 0 |
| gotjunk_001 | GotJunk | internal_app | 0 | 0 |

## 2. Latest Known-Channel Refresh (Delta)

- Generated: `2026-04-23T10:07:36.787082Z`
- FoundUps checked: **4**
- New videos: **89**
- Skipped (already in catalog): **16**

| foundup_id | existing | pulled | new | skipped |
|---|---:|---:|---:|---:|
| move2japan | 594 | 14 | 14 | 0 |
| undaodu | 512 | 0 | 0 | 0 |
| foundups_main | 44 | 41 | 40 | 1 |
| antifafm | 34 | 50 | 35 | 15 |

## 3. Refresh Scheduler Log

- Total logged runs: **1**
- Last run at: `2026-04-23T10:07:23.143120Z`
- Trigger mode: `manual`
- Success: `True`
- FoundUps checked: 4
- New videos found: 89

## 4. Discovery Proposals

- Generated: `2026-04-13T07:06:16.628268Z`
- Query: `FFCPLN music`
- Search type: `video`
- Total proposals: **10**
- Matched to a FoundUp: **10**
- Unmatched: **0**
- Distinct catalog targets: **4**

## 5. Latest Discovery Review

- Source: `youtube_discovery_review_result_20260413.json`
- Reviewed at: `2026-04-13T07:30:00Z`
- Reviewer: `0102-worker-ct`
- Proposal artifact reviewed: `youtube_discovery_proposals.json`
- Total proposals covered: **10**
- Approved / applied: **2**
- Skipped (duplicate): **8**
- Skipped (ambiguous): **0**
- Skipped (low confidence): **0**
- Rejected: **0**
- Catalog update: `move2japan` 592 -> 594

## 6. Blockers

- None detected from artifacts.

## 7. Operator Next Action

- Review 89 new known-channel candidate(s) in youtube_channel_pull_delta.json and apply if relevant.

---

_Summary is artifact-grounded. Missing artifacts are reported honestly; no fields are inferred from sources that do not exist._
