---
name: dt_voice_patterns
description: Extract vocabulary patterns for Digital Twin voice cloning
version: 1.0
author: 0102
created: 2026-01-13
agents: [qwen]
primary_agent: qwen
intent_type: EXTRACTION
promotion_state: prototype
category: workflow
evals: []
---
# Digital Twin Voice Patterns Skill

**Purpose**: Extract 012's signature phrases, filler words, and vocabulary patterns for voice cloning.

---

## What are Voice Patterns?

Distinctive speech characteristics:
- **Signature phrases**: Repeated unique expressions ("blue ocean", "found-up")
- **Filler words**: Verbal tics ("uh", "you know", "basically")
- **Sentence starters**: Common opening patterns ("So", "The thing is")
- **Emphatic words**: Words used for emphasis ("awesome", "important", "amazing")

---

## Instructions

### Input
Video transcript segments with verbatim text.

### Analysis Steps
1. Identify repeated phrases (2+ occurrences)
2. Extract filler words and verbal tics
3. Find common sentence openers
4. Identify emphatic/emotional vocabulary

### Output
```json
{
  "signature_phrases": ["blue ocean", "found-up", "strategic initiative"],
  "filler_words": ["uh", "you know", "basically"],
  "sentence_starters": ["So", "The thing is", "What I mean is"],
  "emphatic_words": ["awesome", "important", "amazing", "critical"],
  "speaking_pace": "medium"
}
```

---

## Benchmark Test Cases

### Test 1: Business Discussion
- **Input**: Video about FoundUps
- **Expected**: signature_phrases includes "found-up", "CABR"

### Test 2: Casual Vlog
- **Input**: Informal video with natural speech
- **Expected**: filler_words > 3 items

---

## NeMo Training Connection

Output feeds into:
1. `VoiceMemory` RAG index
2. `StyleGuardrails` vocabulary enforcement
3. SFT training for voice consistency
