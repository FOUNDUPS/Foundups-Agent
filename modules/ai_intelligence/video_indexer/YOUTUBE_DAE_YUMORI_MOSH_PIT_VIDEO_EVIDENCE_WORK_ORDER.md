# YouTube DAE -> YUMORI Mosh Pit Video Evidence Work Order

Status: `WORK_ORDER` / `NOT_IMPLEMENTED`
Date opened: 2026-09-11
Owner: 0102 / YouTube DAE
Project: YUMORI.me / Save the Onsen / eSingularity / Sukatto Land Kuzuryu

## Objective

Use the existing YouTube DAE video-indexing capability to recover evidence from 012's recorded field activity and connect that evidence to the YUMORI Mosh Pit/Breadcrumb trail.

The first backfill window is **2026-08-25 onward** across the three channels used to record this campaign:

- `FoundUps`
- `UnDaoDu`
- `Move2Japan`

The resulting evidence must make it possible to answer questions such as:

- What did 012 actually do on a given date?
- Which City Hall/protest/meeting events are visible or audible in the source video?
- Which claims are direct video evidence versus 012's spoken report or later interpretation?
- What source video and timestamp supports a Mosh Pit activity item?

## Existing Reusable Infrastructure

Do **not** build a second video system.

Current reusable pieces already exist:

- `modules/ai_intelligence/video_indexer/src/studio_ask_indexer.py`
  - authenticated YouTube Studio / Ask Studio extraction
  - channel-aware prompts
  - existing browser sessions
- `modules/ai_intelligence/video_indexer/src/video_index_store.py`
  - canonical JSON video index persistence
- `modules/ai_intelligence/video_indexer/src/action_surface.py`
  - implemented bounded action: `video_index.studio_ask.single_video`
  - registered but not yet wired: `video_index.studio_ask.channel_cycle`
  - registered but not yet wired: `video_index.studio_ask.daemon_cycle`
- `modules/infrastructure/cli/src/indexing_menu.py`
  - current `main.py` YouTube indexing menu path
  - already runs browser-aware channel cycles for the registry channels
- `extensions/reddog/docs/MOSH_PIT_ACTIVITY_MEMORY_ARCHITECTURE.md`
  - Mosh Pit is a projection over Breadcrumb/Brain/Memex evidence, **not a separate database**

The current CLI contains one-off direct calls to `run_video_indexing_cycle()`. The implementation should converge those autonomous runs onto the governed action surface rather than add another parallel trigger.

## Required Behavior

### 1. Backfill campaign videos from 2026-08-25

Add a YUMORI evidence extraction mode to the existing YouTube DAE/indexer.

Selection rules:

1. resolve channels from `youtube_channel_registry`; do not hard-code channel IDs;
2. include `FoundUps`, `UnDaoDu`, and `Move2Japan`;
3. include public, unlisted, or private videos only when visible through the already-authenticated Studio session and current authority boundary;
4. skip videos definitely older than `2026-08-25` for this work order;
5. resume incrementally after the historical backfill is complete.

Do not download videos merely to satisfy this work order when Ask Studio can extract the required evidence directly.

### 2. Ask Studio / Gemini extraction prompt

For each selected video, ask the Studio video-analysis surface for structured campaign evidence, not a generic summary.

Required extraction fields:

```json
{
  "schema": "yumori_video_evidence_v1",
  "project": "yumori",
  "video_id": "...",
  "channel_key": "...",
  "source_url": "...",
  "video_title": "...",
  "published_at": "...",
  "recorded_date": "...",
  "date_precision": "exact|derived|unknown",
  "events": [
    {
      "event_type": "protest|meeting|city_hall|stakeholder_outreach|document_delivery|media|site_visit|other",
      "start_seconds": 0,
      "end_seconds": 0,
      "actor": "012|0102|012+0102|PC|External",
      "fact": "concise factual event description",
      "observed_result": "...",
      "truth_class": "OBSERVED|REPORTED_BY_012|INFERRED",
      "confidence": 0.0,
      "people_or_orgs_named": [],
      "location_text": "...",
      "evidence_notes": "what in the video supports this item"
    }
  ]
}
```

Rules:

- `OBSERVED` only when the video itself directly supports the event/result.
- `REPORTED_BY_012` when 012 says something happened but the video does not itself show/establish the underlying event.
- `INFERRED` must remain explicit and must never be promoted to fact automatically.
- Do not infer identity from a face. A person may be named only when the source itself names them or existing governed metadata resolves them.
- Preserve the source video and timestamp range for every event candidate.
- Prefer concise factual extraction over prose summarization.

### 3. Persist through the existing video-index store

Do not create a separate Mosh Pit database.

Persist the video analysis through the existing `memory/video_index/.../{video_id}.json` artifact path or an additive field/sidecar owned by the same video-index module.

Recommended additive field:

```json
{
  "project_evidence": {
    "yumori": {
      "schema": "yumori_video_evidence_v1",
      "events": []
    }
  }
}
```

If changing the existing index schema would break consumers, use a deterministic adjacent sidecar owned by `video_indexer`, for example:

`memory/video_index/<channel>/<video_id>.yumori-evidence.json`

That sidecar is evidence attached to the canonical video index. It is **not** a new Mosh Pit store.

### 4. Emit Breadcrumb candidates

Add a pure projection step that converts accepted video evidence into project-aware Breadcrumb candidates.

Each candidate must carry:

- project = `YUMORI.me` / `yumori` canonical project key;
- event time or bounded approximate time;
- actor attribution;
- factual action;
- observed result when known;
- truth class;
- confidence;
- video ID;
- channel;
- source URL;
- start/end timestamp anchors;
- disclosure class;
- deterministic evidence fingerprint.

The video indexer may **emit candidates**. It must not silently rewrite the human Mosh Pit Google Doc and must not overwrite previously curated Breadcrumb truth.

A later governed Breadcrumb/Memex/Mosh Pit projection may accept, deduplicate, correct, or reject a candidate.

### 5. Idempotency / deduplication

Re-running `main.py` must not duplicate campaign history.

Use a deterministic fingerprint such as:

`sha256(project + video_id + start_seconds + end_seconds + normalized_fact)`

Maintain a high-water mark or query the existing index before asking Studio again.

Historical backfill must be restartable after browser/API failure.

### 6. Main.py autonomous integration

Target behavior after implementation:

```text
main.py
  -> YouTube DAE
      -> normal channel/index cycle
      -> if YUMORI evidence backfill/incremental work exists
          -> authenticated Studio Ask extraction
          -> existing video-index JSON persistence
          -> YUMORI Breadcrumb candidate projection
      -> continue normal YouTube DAE work
```

Requirements:

- no credentials in this code path;
- attach only to the existing authenticated Chrome/Edge sessions;
- fail closed when Studio/Gemini/Ask is unavailable;
- failure to extract YUMORI evidence must not corrupt normal comment/index/scheduling work;
- no autonomous public posting;
- no automatic claim that an extracted event caused a City/council decision;
- bounded per-cycle work so `main.py` remains responsive.

### 7. First campaign dates to recover

The backfill should make it easy to validate and attach source evidence for the known campaign spine, including at minimum:

- **2026-08-25** — campaign/reuse effort begins; initial recorded material;
- **2026-08-27** — meeting with Councilman Sano and three City technical/facility staff;
- **2026-08-31** — City Hall/asbestos-related activity, attempted meeting participation, protest/disruption sequence and police follow-up;
- **2026-09-02 onward** — City Hall protest cycle and prefectural outreach;
- **2026-09-06** — Akira Hasegawa meeting where recorded;
- **2026-09-07 onward** — reporter/outreach/campaign activity;
- **2026-09-08 onward** — on-site Sukatto Land protest plus City Hall protest;
- **2026-09-10** — attempted City documentation submission/distribution and refusal/direction reported by 012.

These dates are search targets, not proof. Only the recovered video evidence determines what can be marked `OBSERVED`.

## Acceptance Criteria

1. A bounded test on one known video emits valid `yumori_video_evidence_v1` JSON.
2. A second run of the same video creates no duplicate Breadcrumb candidate.
3. Backfill can enumerate the three configured channels from 2026-08-25 onward.
4. At least one recovered event includes a working source video + timestamp anchor.
5. `OBSERVED`, `REPORTED_BY_012`, and `INFERRED` remain distinct through persistence and projection.
6. Existing video index JSON remains readable by current consumers.
7. Normal YouTube DAE/comment/scheduler behavior continues if YUMORI extraction fails.
8. No public post, email, City submission, or Google Doc mutation occurs from the extraction worker itself.
9. Mosh Pit/Breadcrumb projection can reference the resulting evidence without creating a second historical database.
10. Tests cover date filtering, channel filtering, malformed Studio JSON, idempotency, truth-class preservation, and fail-closed browser behavior.

## Suggested Implementation Slices

### Slice A — extractor contract

- define `YumoriVideoEvidence` / event dataclasses or typed schema;
- add deterministic parser/validator for Studio JSON;
- add project-specific Ask prompt builder;
- unit tests only.

### Slice B — one-video persistence

- run against `video_index.studio_ask.single_video` or shared `StudioAskIndexer` seam;
- persist evidence in the existing video-index ownership boundary;
- emit deterministic Breadcrumb candidate JSON/object;
- prove idempotency.

### Slice C — channel/date backfill

- wire the already-registered channel-cycle action;
- select three registry channels;
- stop at videos older than 2026-08-25 where ordering permits;
- resume safely across sessions.

### Slice D — autonomous main.py cycle

- wire the already-registered daemon-cycle action;
- integrate bounded extraction into the YouTube DAE lifecycle;
- expose counts: scanned / already indexed / extracted / candidate events / failures.

### Slice E — Mosh Pit evidence binding

- map accepted candidates into the existing Breadcrumb/Brain/Memex path;
- Mosh Pit renderer displays source video + timestamp evidence;
- human/governed curation remains authoritative for conflicts and disclosure.

## Non-Goals

- no separate Mosh Pit database;
- no face-recognition identity inference;
- no automatic causal conclusions;
- no rewriting old Mosh Pit history without provenance;
- no new credential store;
- no video publication/scheduling mutation as part of evidence extraction;
- no requirement to process all historical YouTube content before normal DAE operation can continue.

## Immediate Next Test

Use one already-known campaign recording from the August 25-31 window, run the existing authenticated Studio Ask single-video action, and evaluate whether the returned structured evidence can accurately recover a real event plus timestamp. Use that receipt to finalize the schema before launching the three-channel backfill.
