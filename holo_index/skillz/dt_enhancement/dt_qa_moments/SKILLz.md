---
name: dt_qa_moments
description: Extract question-answer pairs for training
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
# Digital Twin Q&A Moments Skill

**Purpose**: Extract question-answer pairs from video content for SFT training data.

---

## Q&A Types

- **rhetorical**: Question asked without expecting answer
- **direct**: Explicit question to audience
- **implied**: Implied question answered in content
- **self_answered**: Speaker asks and answers

---

## Instructions

### Input
Video segments with transcript text.

### Analysis Steps
1. Identify questions (explicit or implied)
2. Find corresponding answers if present
3. Classify question type
4. Link question to answer segment

### Output
```json
{
  "questions": [
    {
      "segment_idx": 1,
      "question": "How does the framework work?",
      "question_type": "self_answered",
      "answered": true,
      "answer_segment_idx": 2,
      "answer_text": "It works like Wikipedia for startups..."
    }
  ]
}
```

---

## Benchmark Test Cases

### Test 1: Self-Answered Question
- **Input**: "What is FoundUps? It's a platform for..."
- **Expected**: question_type = "self_answered", answered = true

### Test 2: Rhetorical Question
- **Input**: "Have you ever wondered why startups fail?"
- **Expected**: question_type = "rhetorical"

---

## NeMo Training Connection

Output creates:
1. Q&A pairs for SFT training
2. FAQ content generation
3. Comment response templates
