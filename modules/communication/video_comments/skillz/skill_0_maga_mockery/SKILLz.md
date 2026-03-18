---
name: skill_0_maga_mockery
description: MAGA troll mockery response generation
version: 1.0_prototype
author: 0102
created: 2026-03-18
agents: [gemma]
primary_agent: gemma
intent_type: GENERATION
promotion_state: prototype
pattern_fidelity_threshold: 0.85
category: workflow
evals: []
trigger:
  event: classification_maga
---
# Skill 0: MAGA Mockery

**Phase:** 3O-3R Sprint 2
**Classification:** 0✊ (MAGA_TROLL)
**Primary Agent:** 0102 (rule-based) + optional Gemma validation
**Intent Type:** GENERATION (mockery responses)
**Promotion State:** prototype → staged (Sprint 2 complete, awaiting Sprint 5 router integration)

## Overview

Generates sarcastic, consciousness-themed mockery responses for confirmed MAGA trolls (users classified as 0✊).

**Pattern Source:** Extracted from `intelligent_reply_generator.py` lines 1020-1030

## WSP Compliance

- **WSP 96 (WRE Skills)**: Skill separation pattern - extracted from monolithic generator
- **WSP 77 (Agent Coordination)**: Classification-based routing (Gemma → Skill)
- **WSP 60 (Module Memory)**: History-aware duplicate detection (future)
- **WSP 84 (Code Reuse)**: Reuses GrokGreetingGenerator from livechat module

## Architecture

```
CommenterClassifier → 0✊ (MAGA_TROLL)
         ↓
   Gemma Validator (optional confidence adjustment)
         ↓
   MagaMockerySkill.execute()
         ↓
   ┌──────────────────────────────┬───────────────────────────────────┐
   │ Strategy 1 (if available)    │ Strategy 2 (fallback)              │
   │ GrokGreetingGenerator        │ Whack-a-MAGA templates             │
   │ consciousness-themed mockery │ random sarcastic one-liners        │
   └──────────────────────────────┴───────────────────────────────────┘
         ↓
   Return unsignified text (caller adds ✊✋🖐️ signature)
```

## Response Strategies

### Strategy 1: GrokGreetingGenerator (Primary)

**Source**: `modules/communication/livechat/src/greeting_generator.py`

Consciousness-themed MAGA mockery with ✊✋🖐️ awakening sequence:

```
Examples:
- "MAGA stuck at ✊? Evolve: ✊✋🖐️!"
- "Achievement: Trigger MAGA! Bonus for ✊✋🖐️ above ✊ baseline!"
- "Matrix MAGA: Red pill? Blue pill? Try consciousness sequence: ✊✋🖐️me!"
```

**When used**: If `context.maga_response` is provided (from GrokGreetingGenerator)

### Strategy 2: Whack-a-MAGA Fallback

**Source**: 10 sarcastic templates (extracted from intelligent_reply_generator.py lines 244-255)

```
Examples:
- "Another MAGA genius emerges from the depths 🤡"
- "Did Tucker tell you to say that? 📺"
- "Sir, this is a Wendy's 🍔"
- "Critical thinking wasn't on the curriculum, huh? 🎓"
```

**When used**: If `context.maga_response` is None

## Usage

### Standalone Execution

```python
from modules.communication.video_comments.skills.skill_0_maga_mockery import (
    MagaMockerySkill,
    SkillContext
)

skill = MagaMockerySkill()

context = SkillContext(
    user_id="troll_user_id",
    username="MAGATroll",
    comment_text="Make America Great Again!",
    classification="MAGA_TROLL",
    confidence=0.95,
    whack_count=3,
    maga_response=None  # Optional: from GrokGreetingGenerator
)

result = skill.execute(context)
# Returns: {
#   'reply_text': 'Critical thinking wasn't on the curriculum, huh? 🎓',
#   'strategy': 'whack_a_maga_fallback',
#   'confidence': 0.7
# }
```

### Integration with IntelligentReplyGenerator (Sprint 5)

**Current (Sprint 2)**: Skill exists alongside monolithic code (no integration yet)

**Future (Sprint 5)**: Replace lines 1020-1030 with skill router:

```python
# intelligent_reply_generator.py (Sprint 5 integration)
elif profile.commenter_type == CommenterType.MAGA_TROLL:
    from modules.communication.video_comments.skills.skill_0_maga_mockery import MagaMockerySkill

    skill = MagaMockerySkill()
    result = skill.execute(SkillContext(
        user_id=author_channel_id,
        username=author_name,
        comment_text=comment_text,
        classification='MAGA_TROLL',
        confidence=profile.troll_score,
        whack_count=profile.whack_count or 0,
        maga_response=profile.maga_response  # From GrokGreetingGenerator
    ))

    return self._add_0102_signature(result['reply_text'])
```

## Dependencies

### Required
- Python 3.12+
- `logging`, `random`, `dataclasses` (stdlib)

### Optional
- **GrokGreetingGenerator**: Provides consciousness-themed mockery (`maga_response`)
  - Location: `modules/communication/livechat/src/greeting_generator.py`
  - Fallback: Uses Whack-a-MAGA templates if unavailable

### Future
- **CommenterHistoryStore**: Duplicate pattern detection (Sprint 5)
- **UITarsClient**: LLM contextual mockery generation (Sprint 5+)

## Testing

### Run Tests

```bash
cd O:\Foundups-Agent
python test_skill_0_runner.py
```

### Test Coverage

✅ **5/5 tests passing** (Sprint 2)

1. **GrokGreetingGenerator Strategy**: Verifies primary strategy when `maga_response` available
2. **Whack-a-MAGA Fallback**: Verifies fallback when `maga_response` is None
3. **Response Variation**: Confirms randomized selection (no fixed templates)
4. **Context Validation**: Handles minimal context (only required fields)
5. **High-Confidence Troll**: Processes confirmed trolls (3+ whacks, 0.95 confidence)

## Performance

- **Execution time**: <5ms (random selection from template array)
- **Memory footprint**: Minimal (~10 KB - 10 template strings)
- **Scalability**: O(1) - constant time regardless of comment volume

## Future Enhancements

### Sprint 5 (Router Integration)
- Integrate into skill router (replace monolithic code)
- Add history-aware duplicate detection
- Metric tracking per skill execution

### Post-Sprint 5 (Learning Layer)
- A/B test different mockery styles
- Learn from moderator feedback (which responses get whacks?)
- Pattern memory integration (WSP 60)
- LLM contextual mockery generation

## Changelog

### Sprint 2 (2025-12-18) - Initial Extraction
- ✅ Extracted from `intelligent_reply_generator.py` lines 1020-1030
- ✅ Created standalone `MagaMockerySkill` class
- ✅ Preserved GrokGreetingGenerator integration
- ✅ Added 5 unit tests (100% passing)
- ✅ Documented skill architecture and usage
- 📋 Awaiting Sprint 5 router integration

## Related Files

- **Executor**: `executor.py` (MagaMockerySkill class)
- **Tests**: `tests/test_skill_0.py` (5 unit tests)
- **Integration**: Replaces `intelligent_reply_generator.py` lines 1020-1030 (Sprint 5)
- **Pattern Source**: `livechat/src/greeting_generator.py` (GrokGreetingGenerator)

## License

WSP Compliant Module - Part of FoundUps Agent System
