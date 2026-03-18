---
name: dt_teaching_moments
description: Extract educational segments for knowledge training
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
# Digital Twin Teaching Moments Skill

**Purpose**: Identify segments where 012 teaches or explains concepts.

---

## What is a Teaching Moment?

When the speaker:
- Explains a concept
- Uses analogies to clarify
- Provides step-by-step instructions
- Shares expertise or knowledge

---

## Instructions

### Input
Video segments with educational content.

### Analysis Steps
1. Identify explanatory segments
2. Extract concept being taught
3. Note if analogies are used
4. Extract key terms introduced

### Output
```json
{
  "teachings": [
    {
      "segment_idx": 2,
      "concept": "Open Incubator Framework",
      "complexity": "beginner",
      "uses_analogy": true,
      "analogy": "Like Wikipedia for startups",
      "key_terms": ["found-up", "strategic initiative", "blue ocean"]
    }
  ]
}
```

---

## Complexity Levels
- **beginner**: No prior knowledge needed
- **intermediate**: Some context required
- **advanced**: Expert-level content

---

## Benchmark Test Cases

### Test 1: Analogy-Based Teaching
- **Input**: "Think of it like Wikipedia but for startups"
- **Expected**: uses_analogy = true

### Test 2: Technical Deep Dive
- **Input**: Complex architecture explanation
- **Expected**: complexity = "advanced"

---

## NeMo Training Connection

Output feeds into:
1. Knowledge base for 012 expertise areas
2. Response generation for technical questions
3. Content Agent educational content creation
