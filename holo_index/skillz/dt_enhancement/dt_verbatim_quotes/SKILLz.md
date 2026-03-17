---
name: dt_verbatim_quotes
description: Extract exact words for voice cloning training
version: 1.0
author: 0102
created: 2026-01-13
agents: [qwen]
primary_agent: qwen
intent_type: EXTRACTION
promotion_state: prototype
category: capability-uplift
evals: []
retirement_date: null
---
# Digital Twin Verbatim Quotes Skill

**Purpose**: Extract EXACT spoken words (not summaries) for voice training.

---

## Why Verbatim?

Current video indexing often produces **summaries**, not exact transcripts.
For voice cloning/TTS training, we need:
- Exact word sequences
- Natural speech patterns
- Including fillers and pauses

---

## Instructions

### Input
Video segments (ideally with verbatim transcript from Whisper or YouTube DOM).

### Analysis Steps
1. Identify impactful statements
2. Extract exact wording (not paraphrased)
3. Classify by intent (opinion, fact, story, joke)
4. Note if this is verbatim or summarized

### Output
```json
{
  "quotes": [
    {
      "segment_idx": 5,
      "exact_text": "The American Dream died and we need a new dream",
      "intent": "opinion",
      "is_verbatim": true,
      "source": "youtube_dom"
    }
  ]
}
```

---

## Quality Indicators

- `is_verbatim: true` - Exact transcript available
- `is_verbatim: false` - Based on Gemini summary (less reliable)

---

## Benchmark Test Cases

### Test 1: Strong Statement
- **Input**: Segment with impactful quote
- **Expected**: exact_text captured, intent classified

### Test 2: Filler-Heavy Speech
- **Input**: Casual speech with "uh", "you know"
- **Expected**: Fillers preserved if verbatim source

---

## NeMo Training Connection

Critical for:
1. SFT voice training (exact patterns)
2. TTS corpus building
3. Style fingerprint calibration
