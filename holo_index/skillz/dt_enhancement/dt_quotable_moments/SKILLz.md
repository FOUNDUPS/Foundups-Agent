---
name: dt_quotable_moments
description: Extract memorable quotes for RAG voice memory
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
# Digital Twin Quotable Moments Skill

**Purpose**: Extract memorable, shareable quotes for VoiceMemory RAG index.

---

## What Makes a Quote Notable?

- **Impactful**: Strong statement that resonates
- **Concise**: Can stand alone without context
- **Authentic**: Represents 012's genuine voice
- **Shareable**: Social media worthy

---

## Instructions

### Input
Video segments with text content.

### Analysis Steps
1. Scan for impactful statements
2. Evaluate shareability (would this work as a tweet?)
3. Categorize by type
4. Score 0.0-1.0 for shareability

### Output
```json
{
  "quotables": [
    {
      "segment_idx": 5,
      "text": "The American Dream died and we need a new dream",
      "category": "philosophical",
      "shareability": 0.9,
      "context": "discussing societal values"
    }
  ]
}
```

### Categories
- philosophical, humorous, insightful, controversial, motivational, technical

---

## Benchmark Test Cases

### Test 1: Strong Opinion
- **Input**: Segment with bold statement
- **Expected**: shareability > 0.7

### Test 2: Technical Explanation
- **Input**: Dry technical segment
- **Expected**: quotables = [] (nothing quotable)

---

## NeMo Training Connection

Output feeds into:
1. `VoiceMemory` RAG index (top retrieval candidates)
2. Content generation templates
3. Social media automation
