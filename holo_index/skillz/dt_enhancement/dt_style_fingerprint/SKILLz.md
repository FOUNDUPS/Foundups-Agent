---
name: dt_style_fingerprint
description: Extract speaker style metrics for Digital Twin training
version: 1.0
author: 0102
created: 2026-01-13
agents: [qwen, gemma]
primary_agent: qwen
intent_type: ANALYSIS
promotion_state: prototype
pattern_fidelity_threshold: 0.85
category: workflow
evals: []
---
# Digital Twin Style Fingerprint Skill

**Purpose**: Extract formality, energy, humor, and other style metrics from video content for Digital Twin voice training.

**Agent**: Qwen (structured analysis), Gemma (fast scoring)

---

## What is Style Fingerprint?

A numeric profile of 012's speaking/writing style:
- **Formality**: 0=very casual, 1=very formal
- **Energy**: 0=calm, 1=passionate
- **Humor**: Frequency of jokes/wit
- **Personal Sharing**: Frequency of personal stories
- **Analogy Usage**: Uses analogies to explain
- **Technical Depth**: Complexity of explanations

---

## Instructions

### Input
Video JSON with transcript segments:
```json
{
  "audio": {"segments": [...]},
  "metadata": {"topics": [...], "summary": "..."}
}
```

### Analysis Steps
1. Read transcript summary and segments
2. Analyze tone, word choice, sentence structure
3. Score each dimension 0.0-1.0
4. Classify speaking pace and sentence length

### Output
```json
{
  "formality": 0.3,
  "energy": 0.7,
  "humor": 0.4,
  "personal_sharing": 0.8,
  "technical_depth": 0.5,
  "analogy_usage": 0.9,
  "sentence_length": "medium",
  "speaking_pace": "medium"
}
```

---

## Benchmark Test Cases

### Test 1: Casual Vlog
- **Input**: Video with casual language, personal stories, jokes
- **Expected**: formality<0.4, personal_sharing>0.7, humor>0.5

### Test 2: Technical Lecture
- **Input**: Video explaining code/architecture
- **Expected**: formality>0.6, technical_depth>0.7, analogy_usage>0.6

### Test 3: Passionate Pitch
- **Input**: Video about FoundUps vision
- **Expected**: energy>0.7, personal_sharing>0.6

---

## NeMo Training Connection

Output feeds into:
1. `dataset_builder.py` → voice training corpus
2. `style_guardrails.py` → runtime enforcement
3. LoRA fine-tuning → personality embedding
