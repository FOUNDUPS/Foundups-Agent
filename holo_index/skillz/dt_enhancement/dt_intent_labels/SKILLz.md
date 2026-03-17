---
name: dt_intent_labels
description: Classify segment intent for Digital Twin decision training
version: 1.0
author: 0102
created: 2026-01-13
agents: [qwen, gemma]
primary_agent: gemma
intent_type: CLASSIFICATION
promotion_state: prototype
category: workflow
evals: []
---
# Digital Twin Intent Labels Skill

**Purpose**: Classify each video segment's communicative intent for training 0102's response generation.

---

## Intent Categories

| Intent | Description | Example |
|--------|-------------|---------|
| inform | Sharing information | "The visa process requires..." |
| persuade | Convincing audience | "You should consider..." |
| joke | Humor/wit | "That's like bringing a knife to a..." |
| story | Personal narrative | "When I first moved to Japan..." |
| question | Asking audience | "Have you ever wondered..." |
| call_to_action | Requesting action | "Call us at 202-360-4467" |
| personal_disclosure | Sharing personal info | "I'm dyslexic, so..." |
| technical_explanation | Explaining concepts | "The algorithm works by..." |
| opinion | Expressing viewpoint | "I believe that..." |
| analogy | Using comparison | "It's like Wikipedia for startups" |

---

## Instructions

### Input
Video segments with text and timestamps.

### Analysis Steps
1. Read each segment
2. Identify primary communicative purpose
3. Assign intent label with confidence score

### Output
```json
{
  "intents": [
    {"segment_idx": 0, "intent": "personal_disclosure", "confidence": 0.9},
    {"segment_idx": 1, "intent": "analogy", "confidence": 0.85},
    {"segment_idx": 2, "intent": "call_to_action", "confidence": 0.95}
  ]
}
```

---

## Benchmark Test Cases

### Test 1: Personal Story Segment
- **Input**: "When I was living in Tokyo..."
- **Expected**: intent = "story", confidence > 0.8

### Test 2: CTA Segment
- **Input**: "Sign up at foundups.com"
- **Expected**: intent = "call_to_action", confidence > 0.9

---

## NeMo Training Connection

Output feeds into:
1. Decision policy training (when to use each intent type)
2. Response generation (matching intent to context)
