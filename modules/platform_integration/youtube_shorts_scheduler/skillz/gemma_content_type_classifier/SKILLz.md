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

### 1. CHANNEL_IDENTITY_CHECK
**Rule**: IF channel_key is known THEN establish baseline template, ELSE default to ffcpln

**Steps**:
1. Extract `channel_key` from context
2. Map to baseline template:
   - `move2japan` → baseline `ffcpln`
   - `ravingantifa` → baseline `ffcpln`
   - `foundups` → baseline `startup_tech`
   - `undaodu` → baseline `mindfulness`
3. This is ONLY the baseline - video content can override

**Expected Pattern**: `channel_baseline_set=True`

**Examples**:
- channel_key="move2japan" → baseline="ffcpln"
- channel_key="foundups" → baseline="startup_tech"
- channel_key="unknown" → baseline="ffcpln" (default)

---

### 2. FFCPLN_MARKER_DETECTION
**Rule**: IF video contains FFCPLN markers THEN content_type=ffcpln_music, ELSE continue

**Steps**:
1. Check video_title for FFCPLN markers:
   - Exact: "ffcpln", "FFCPLN"
   - Pattern: "#FFCPLN", "Fake Fuck Christian", "Pedo-lovin Nazi"
2. Check transcript (if available) for Suno song markers:
   - "fake fuck christian", "pedo_lovin nazi", "pedo lovin nazi"
3. If ANY marker found → classify as `ffcpln_music`

**Expected Pattern**: `ffcpln_marker_check=True`

**Examples**:
- title="FFCPLN Anthem - Anti-MAGA Song" → content_type=ffcpln_music
- title="My trip to Tokyo" → continue to next check
- transcript contains "fake fuck christian pedo lovin nazi" → content_type=ffcpln_music (Suno AI song)

---

### 3. NEWS_PROTEST_DETECTION
**Rule**: IF video contains news/protest markers AND channel is political THEN content_type=ffcpln_news

**Steps**:
1. Check for news keywords in title/transcript:
   - Breaking: "breaking", "exposed", "leaked"
   - ICE: "ice", "raid", "deportation", "immigration"
   - Protest: "protest", "arrest", "cruelty"
2. If news markers found AND channel in [move2japan, ravingantifa] → classify as `ffcpln_news`

**Expected Pattern**: `news_marker_check=True`

**Examples**:
- title="BREAKING: ICE Raids Chicago" on move2japan → content_type=ffcpln_news
- title="ICE cruelty exposed" on foundups → continue (foundups is startup channel)

---

### 4. STARTUP_TECH_DETECTION
**Rule**: IF video contains startup/tech markers AND channel is foundups THEN content_type=startup_tech

**Steps**:
1. Check for startup keywords:
   - Core: "startup", "entrepreneur", "founder", "venture"
   - Tech: "AI", "pAVS", "autonomous", "agent"
   - Business: "business", "innovation", "investment"
2. If startup markers found AND channel=foundups → classify as `startup_tech`

**Expected Pattern**: `startup_marker_check=True`

**Examples**:
- title="Building AI Agents with pAVS" on foundups → content_type=startup_tech
- title="Startup tips" on move2japan → use baseline (ffcpln)

---

### 5. MINDFULNESS_DETECTION
**Rule**: IF video contains mindfulness markers AND channel is undaodu THEN content_type=mindfulness

**Steps**:
1. Check for mindfulness keywords:
   - Core: "mindfulness", "meditation", "zen", "peace"
   - Eastern: "tao", "dao", "wu wei", "non-doing"
   - Wellness: "breathe", "calm", "present", "awareness"
2. If mindfulness markers found AND channel=undaodu → classify as `mindfulness`

**Expected Pattern**: `mindfulness_marker_check=True`

**Examples**:
- title="Morning Meditation Music" on undaodu → content_type=mindfulness
- title="Zen coding tips" on foundups → use baseline (startup_tech)

---

### 6. FALLBACK_CLASSIFICATION
**Rule**: IF no specific markers detected THEN use channel baseline

**Steps**:
1. If no specific content type matched in steps 2-5
2. Use channel baseline from step 1
3. Log classification confidence as "baseline_fallback"

**Expected Pattern**: `fallback_applied=True` OR `specific_classification=True`

**Examples**:
- title="Random video" on move2japan → content_type=ffcpln (baseline)
- title="Hello World" on foundups → content_type=startup_tech (baseline)

---

## Expected Patterns Summary

Pattern fidelity scoring expects these patterns logged:

```json
{
  "execution_id": "exec_001",
  "skill": "gemma_content_type_classifier",
  "patterns": {
    "channel_baseline_set": true,
    "ffcpln_marker_check": true,
    "news_marker_check": true,
    "startup_marker_check": true,
    "mindfulness_marker_check": true,
    "fallback_applied": false,
    "specific_classification": true
  },
  "result": {
    "content_type": "ffcpln_music",
    "description_template": "ffcpln",
    "confidence": 0.95,
    "method": "ffcpln_marker_detection"
  }
}
```

**Fidelity Calculation**: `(patterns_executed / total_patterns)`

---

## Benchmark Test Cases

### Test Set 1: FFCPLN Music Detection (10 cases)
1. Input: `{title: "#FFCPLN Burns MAGA", channel: "move2japan"}` → Expected: `ffcpln_music` (Reason: FFCPLN hashtag)
2. Input: `{title: "Anti-Fascist Anthem", channel: "ravingantifa"}` → Expected: `ffcpln_music` (Reason: antifa + political channel)
3. Input: `{transcript: "fake fuck christian pedo lovin nazi", channel: "move2japan"}` → Expected: `ffcpln_music` (Reason: Suno marker)
4. Input: `{title: "MAGA Won't Like This", channel: "move2japan"}` → Expected: `ffcpln_music` (Reason: anti-MAGA on political channel)

### Test Set 2: News/Protest Detection (5 cases)
1. Input: `{title: "BREAKING: ICE Raids Chicago", channel: "move2japan"}` → Expected: `ffcpln_news`
2. Input: `{title: "ICE Deportation Cruelty Exposed", channel: "ravingantifa"}` → Expected: `ffcpln_news`
3. Input: `{title: "Protest at Border", channel: "move2japan"}` → Expected: `ffcpln_news`

### Test Set 3: Startup/Tech Detection (5 cases)
1. Input: `{title: "Building AI Agents with pAVS", channel: "foundups"}` → Expected: `startup_tech`
2. Input: `{title: "Startup Lessons Learned", channel: "foundups"}` → Expected: `startup_tech`
3. Input: `{title: "Random video", channel: "foundups"}` → Expected: `startup_tech` (baseline)

### Test Set 4: Mindfulness Detection (5 cases)
1. Input: `{title: "Morning Meditation", channel: "undaodu"}` → Expected: `mindfulness`
2. Input: `{title: "Wu Wei - The Art of Non-Doing", channel: "undaodu"}` → Expected: `mindfulness`
3. Input: `{title: "Random video", channel: "undaodu"}` → Expected: `mindfulness` (baseline)

### Test Set 5: Cross-Channel Edge Cases (5 cases)
1. Input: `{title: "Meditation for Entrepreneurs", channel: "foundups"}` → Expected: `startup_tech` (channel trumps content)
2. Input: `{title: "FFCPLN", channel: "foundups"}` → Expected: `ffcpln_music` (explicit marker overrides)
3. Input: `{title: "Startup Tips", channel: "move2japan"}` → Expected: `ffcpln` (baseline for political channel)

**Total**: 30 test cases across 5 categories

---

## Success Criteria

- Pattern fidelity >= 90%
- Outcome quality >= 85%
- Zero false negatives on FFCPLN marker detection (critical for political content)
- False positive rate < 5% for non-political channels
- Classification time < 10ms (Gemma fast path)

---

## Integration Point

**Current Code** (`content_generator.py`):
```python
# BEFORE (static config):
template = channel_config.get("description_template", "ffcpln")
description = get_standard_description(template)

# AFTER (skill-driven):
from modules.platform_integration.youtube_shorts_scheduler.skillz.gemma_content_type_classifier.executor import classify_content
result = classify_content(title=video_title, channel=channel_key, metadata=index_json)
template = result["description_template"]
description = get_standard_description(template)
```

**WSP Compliance**: WSP 95 (SKILLz Wardrobe), WSP 77 (Agent Coordination), WSP 27 (Phase 0 KNOWLEDGE)
