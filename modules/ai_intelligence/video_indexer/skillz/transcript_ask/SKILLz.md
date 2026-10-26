---
name: transcript_ask
description: Build resumable, per-video semantic manifests through YouTube Studio Ask for one video, one channel, or the Move2Japan/UnDaoDu/FoundUps portfolio
version: 2.0.0
author: 0102_video_indexer_team
agents: [gemini, qwen]
dependencies: [browser_actions, studio_ask_indexer, action_surface]
domain: video_indexing
intent_type: EXTRACTION
promotion_state: prototype
category: capability-uplift
evals: []
retirement_date: null
action_ids:
  - video_index.studio_ask.single_video
  - video_index.studio_ask.channel_cycle
  - video_index.studio_ask.portfolio_cycle
  - video_index.studio_ask.daemon_cycle
---
# Studio Ask Video Indexing SKILLz

Use the typed action surface in `src/action_surface.py`; do not recreate browser
automation in a menu, scheduler, OpenClaw task, or ad-hoc script.

## Capability

- `video_index.studio_ask.single_video`: index one known video.
- `video_index.studio_ask.channel_cycle`: run one bounded, resumable channel batch.
- `video_index.studio_ask.portfolio_cycle`: index Move2Japan and UnDaoDu through
  Chrome 9222, then FoundUps through Edge 9223.
- `video_index.studio_ask.daemon_cycle`: run a bounded number of daemon cycles.

All paths attach to already-authenticated browser sessions. They never handle
credentials and never publish, schedule, or mutate YouTube metadata.

## Canonical operation

```bash
python -m modules.ai_intelligence.video_indexer.cli --portfolio --batch-size 10
python -m modules.ai_intelligence.video_indexer.cli --status
```

Rerun the portfolio command until each visible catalog has no pending videos.
Existing valid manifests are skipped; the scanner scrolls beyond the already
indexed prefix so repeated bounded runs advance rather than loop on one batch.

Use `--reindex` only when the operator explicitly requests a rebuild. Honor
`memory/STOP_VIDEO_INDEXER` immediately.

## Manifest integrity contract

1. The prompt names the requested video ID and requests `source_video_id` back.
2. A mismatched response ID fails closed; no manifest is written.
3. The pre-submit answer is snapshotted and ignored, preventing a retained prior
   Gemini answer from being assigned to the next video.
4. A normalized response SHA-256 is persisted. Reusing the same response for a
   different video in the same channel is rejected.
5. Optional Gemini API enrichment is merged into the owning channel manifest; it
   must not overwrite Studio provenance or fall through to the `undaodu` default.

## Memory versus weight training

Ask Studio/Gemini output is a semantic index, not a verified word-for-word
transcript. It is useful for retrieval, topic search, highlights, and prioritizing
which videos should receive transcription. Manifests must carry:

```json
{
  "transcript_source": "gemini_summary",
  "metadata": {
    "retrieval_eligible": true,
    "training_eligible": false,
    "training_exclusion_reason": "gemini_summary_not_verbatim"
  }
}
```

Only `youtube_transcript` or `whisper_transcript` segments may feed Red Dog
weight-training datasets. `DatasetBuilder` enforces this boundary.

## Required live preconditions

- Chrome debugger session on port 9222, authenticated to Move2Japan/UnDaoDu.
- Edge debugger session on port 9223, authenticated to FoundUps.
- YouTube Studio Ask available for the owning channel.

If those sessions are absent, report the attach failure. Do not claim the
portfolio was indexed and do not attempt credential entry.

## Verification

After a cycle, confirm:

- each saved path matches the registry channel key and response video ID;
- response hashes are not duplicated across different video IDs in a channel;
- status counts increase only for successful new manifests;
- no Gemini summary appears in `training_rows.jsonl` or
  `training_worthy.jsonl`.

This remains `prototype` until both authenticated browser lanes complete a live
operator proof. The code path is runnable; promotion is a separate evidence gate.
