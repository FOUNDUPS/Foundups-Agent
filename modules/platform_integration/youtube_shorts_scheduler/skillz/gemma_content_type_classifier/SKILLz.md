---
# Metadata (YAML Frontmatter)
name: gemma_content_type_classifier
description: Classify video content type and select channel-appropriate description template
version: 1.0_prototype
author: 0102
created: 2026-02-24
agents: [gemma, qwen]
primary_agent: gemma
intent_type: CLASSIFICATION
promotion_state: prototype
pattern_fidelity_threshold: 0.90
test_status: needs_validation

# Dependencies
dependencies:
  data_stores:
    - name: video_index
      type: json
      path: memory/video_index/{channel}/{video_id}.json
  mcp_endpoints:
    - endpoint_name: holo_index
      methods: [semantic_search]
  throttles:
    - name: local_model_inference
      max_rate: 100_per_minute
      cost_per_call: 0
  required_context:
    - video_title: "Original video title"
    - video_metadata: "Index artifact with audio/visual analysis"
    - channel_key: "Channel identifier (move2japan, undaodu, foundups, ravingantifa)"

# Metrics Configuration
metrics:
  pattern_fidelity_scoring:
    enabled: true
    frequency: every_execution
    scorer_agent: gemma
    write_destination: modules/platform_integration/youtube_shorts_scheduler/skillz/gemma_content_type_classifier/metrics/fidelity.json
  promotion_criteria:
    min_pattern_fidelity: 0.90
    min_outcome_quality: 0.85
    min_execution_count: 100
    required_test_pass_rate: 0.95
category: capability-uplift
evals: []
retirement_date: null
---
# Gemma Content Type Classifier

**Purpose**: Classify video content type and dynamically select the appropriate description template for YouTube Shorts scheduling. Replaces static `description_template` config with AI-driven classification.

**Intent Type**: CLASSIFICATION

**Agent**: Gemma 3 270M (fast pattern matching <10ms)

**Fallback**: Qwen 3 4B (strategic context analysis if Gemma uncertain)

---

## Task

This skill classifies video content to determine the appropriate description template for scheduling. It replaces static JSON config with dynamic AI classification.

**The Problem Being Solved**:
- Static `description_template` in youtube_channels.json assigns templates at channel level
- But channels may have mixed content (e.g., Move2Japan has FFCPLN music AND personal vlogs)
- AI should classify EACH VIDEO, not use channel-wide defaults

**Classification Taxonomy**:
| Content Type | Description Template | Channels | Indicators |
|-------------|---------------------|----------|------------|
| `ffcpln_music` | FFCPLN_DESCRIPTION | move2japan, ravingantifa | FFCPLN markers, Suno lyrics, political hashtags |
| `ffcpln_news` | FFCPLN_DESCRIPTION + ICE news | move2japan, ravingantifa | ICE, protest, raid, breaking |
| `startup_tech` | FOUNDUPS_DESCRIPTION | foundups | pAVS, startup, entrepreneurship, AI |
| `mindfulness` | UNDAODU_DESCRIPTION | undaodu | meditation, zen, mindfulness, peace |
| `personal_vlog` | Channel-generic template | any | Personal content, no political markers |

---

## Instructions (For AI Agent)

This legacy classifier is a candidate-label helper, not authority to change
metadata. Its executor may still return channel/title heuristic labels; the
shared content-evidence gate must validate these before scheduling metadata edits.

1. Resolve exact channel/video identity and existing analyzer evidence.
2. Reject failed, stub, title-only, mismatched or incomplete evidence for metadata
   generation. Preserve existing metadata and report `evidence_required`.
3. Classify the observed content, not the channel. Political words, hashtags,
   duration, absent speech or a failed transcript never establish music.
4. Require supported audio/visual evidence for music. A spoken political clip
   remains speech/news/commentary even when its title contains FFCPLN markers.
5. If evidence is insufficient or ambiguous, retain an unknown candidate rather
   than supplying a channel-wide template. Feed supported labels and provenance
   into `content_generator.py`'s matched-evidence gate.
6. Log heuristic output separately from validated content. A legacy pattern score
   is not proof that a video was understood or that publishing is authorized.

The taxonomy above describes the legacy prototype's output,
not permission to bypass the evidence gate or silently use its fallback template.

---

## Forward-review cases

| Evidence | Required scheduling behavior |
|---|---|
| Title contains FFCPLN; no valid analyzer evidence | Preserve metadata; require evidence. |
| Gemini music stub or failed transcript | Reject as content evidence. |
| Matched transcript of political commentary | Ground description in speech; do not infer music. |
| Matched valid audio/visual evidence of a song | Music label may be used within the shared evidence gate. |
| Channel fallback disagrees with actual clip | Discard fallback for metadata generation. |

These are workflow acceptance cases, not claims that the legacy classifier
executor has been retrained. Existing executor heuristic scores describe its own
classification process only. The metadata write boundary is the shared validated
video-evidence path; do not call a static description template directly from a
heuristic label.

## Workflow handoff

Follow the [shared scheduling workflow](../README.md) for ordered inputs,
outputs, evidence gates and resume boundaries. This skill retains its own
permissions and prototype status; linkage does not expand authority.
