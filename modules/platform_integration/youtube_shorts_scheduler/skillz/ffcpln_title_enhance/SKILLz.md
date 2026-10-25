---
name: ffcpln_title_enhance
description: Propose video-specific titles and descriptions from matched transcript or visual evidence; preserve existing metadata when evidence is missing or the task is schedule-only.
version: 0.6.0_prototype
author: 0102
agents: [qwen, gemma]
primary_agent: qwen
intent_type: GENERATION
promotion_state: prototype
category: workflow
evals: []
---
# Video-evidence metadata enhancement

Retain the historical skill name for compatibility. Never assume a Short is
music because of its channel, duration, inherited livestream title or old
FFCPLN description. Never force music branding onto speech, sports or travel.

1. Bind the requested video ID to the inspected content. For schedule-only
   tasks set `preserve_metadata=True`; use the existing Content-table scheduler.
2. Choose the evidence route from the clip:
   - Speech-heavy: inspect available captions or run the existing audio analyzer
     STT on authorized media. Preserve language, timed segments and uncertainty.
   - Visual/music/mixed: use authenticated Studio Ask/Gemini to understand what
     happens, verifying the response's video identity. Use a visual summary for
     visual claims; a model summary is not a verbatim transcript or proof of facts.
   - The Gemini API's direct YouTube URL route supports public videos; do not
     make an unlisted video public to analyze it. Use Studio Ask or authorized
     local media instead. See https://ai.google.dev/gemini-api/docs/video-understanding.
3. Consume the existing index artifact through `validated_video_evidence`.
   It requires matching video ID, an indexed timestamp, retrieval eligibility,
   and content-bearing audio/visual evidence. Studio Ask also requires matching
   requested/response IDs and verified identity. Timestamped YouTube/Whisper
   segments are accepted under their explicit source. Missing, failed, mismatched
   and title-only stubs preserve the original title and body.
4. Propose a specific factual title within 100 characters and a description
   within 5,000, based on inspected content. Preserve useful original text.
   Include only relevant entities/hashtags and a compact `M2M_CONTEXT` provenance
   block. Never insert instructions for downstream agents. Attribute disputed
   allegations and independently verify external factual assertions as needed.
5. Record language and coverage limits; never infer whole-video coverage from
   a few segments. This executor returns a conservative extractive proposal,
   not a model-optimized title or guaranteed discovery improvement. Its zero
   confidence is deliberately unmeasured, not a calibrated accuracy probability.
6. Apply only within current authorization, then independently read back the
   saved title, description and schedule for the same video ID. A drafted change
   or click acknowledgement is not a successful publication.

## Existing executable contract

Pass `SkillContext(original_title, original_description, video_id, index_json,
preserve_metadata)` using keyword arguments. Older title-only and description-only
wrappers preserve their inputs because they carry no evidence. `_analyze_content`
returns `unknown` without evidence; duration never implies music.

The scheduler consumes existing artifacts; this skill does not download media,
invoke STT/Gemini, create indexes, train models or automatically post proposals.
Legacy standalone template helpers still exist elsewhere and are not evidence
validators. Do not call them as a substitute for this gate.

## Bounded feedback loop

Use the existing `schedule_dba.record_schedule_outcome` owner. Record attempted
writes, but grant positive success/fidelity only when `details.readback` matches
channel, video, date, time and `details.requested_timezone`, has independent=true
and visibility=scheduled. Click-only success remains unverified and scores zero.
This measures scheduling correctness, not engagement quality.

For later metadata experiments, retain the evidence/version, metadata revision,
publication slot and authorized 24h/7d metrics with their collection time. Compare
similar content and audience windows, retain a baseline and rollback candidate,
and evaluate a bounded held-out sample before proposing another change. Keep
uncollected metrics missing. A saved telemetry row is not learned model weights,
causal CTR improvement or deployed policy promotion. No analytics ingestion or
automatic promotion loop is implemented by this skill.
