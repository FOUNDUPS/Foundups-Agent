---
name: dt_comment_triggers
description: Identify content that triggers viewer engagement
version: 1.0
author: 0102
created: 2026-01-13
agents: [qwen]
primary_agent: qwen
intent_type: PREDICTION
promotion_state: prototype
category: workflow
evals: []
---
# Digital Twin Comment Triggers Skill

**Purpose**: Predict which video segments will generate viewer comments/engagement.

---

## Trigger Types

| Type | Description | Engagement Level |
|------|-------------|------------------|
| controversial_opinion | Bold statement that divides | High |
| call_to_action | Explicit request for response | High |
| personal_story | Relatable experience | Medium-High |
| question | Direct or rhetorical question | Medium-High |
| humor | Joke or witty remark | Medium |
| technical_insight | Novel information | Medium |
| emotional_moment | Vulnerability, passion | High |

---

## Instructions

### Input
Video segments with content analysis.

### Analysis Steps
1. Identify segments likely to generate comments
2. Classify trigger type
3. Score engagement potential (0.0-1.0)

### Output
```json
{
  "triggers": [
    {
      "segment_idx": 3,
      "trigger_type": "controversial_opinion",
      "engagement_score": 0.85,
      "predicted_reactions": ["agree", "disagree", "question"]
    }
  ]
}
```

---

## Benchmark Test Cases

### Test 1: Bold Claim
- **Input**: "AI will replace 80% of jobs"
- **Expected**: engagement_score > 0.8, trigger_type = "controversial_opinion"

### Test 2: CTA
- **Input**: "Comment below if you agree"
- **Expected**: trigger_type = "call_to_action"

---

## NeMo Training Connection

Output feeds into:
1. Decision policy (when to comment on similar content)
2. Content strategy (what generates engagement)
