---
name: openclaw_intent_router
description: Classify inbound OpenClaw messages into intent categories and route to domain DAEs
version: 1.0.0
author: 0102
agents: [gemma, qwen]
dependencies: [openclaw_dae, wre_core]
domain: communication
intent_type: CLASSIFICATION
promotion_state: prototype
pattern_fidelity_threshold: 0.85
category: workflow
evals: []
---
# OpenClaw Intent Router Skill

**Skill Type**: Micro Chain-of-Thought (WSP 96)
**Intent**: CLASSIFICATION (route inbound messages to correct domain)
**Agents**: Gemma 270M (fast classification), Qwen 1.5B (fallback)
**Promotion State**: prototype
**Version**: 1.0.0

---

## Skill Purpose

Classify inbound OpenClaw messages into intent categories and determine which
domain DAE should handle execution. This replaces the keyword heuristic in
`openclaw_dae.classify_intent()` with Gemma binary classification (<10ms).

**Trigger Source**: OpenClaw webhook POST -> OpenClawDAE.process()

**Success Criteria**:
- Classification accuracy >85% (vs labeled test set)
- Latency <50ms per classification (Gemma 270M)
- Correct domain routing for all 7 intent categories
- Security: non-commander COMMAND/SYSTEM always downgraded

---

## Intent Categories

| Category | Domain Route | Required Authority |
|----------|-------------|-------------------|
| QUERY | holo_index | anyone |
| COMMAND | wre_orchestrator | commander only |
| MONITOR | ai_overseer | anyone |
| SCHEDULE | youtube_shorts_scheduler | commander |
| SOCIAL | communication | commander |
| SYSTEM | infrastructure | commander only |
| CONVERSATION | digital_twin | anyone |

---

## Micro Chain-of-Thought Steps

### Step 1: Extract Signal Words (Gemma Fast Classification)

**Input Context Required**:
```python
{
    "message": str,         # Raw user message
    "sender": str,          # Sender identifier
    "channel": str,         # Source channel
    "is_commander": bool    # Pre-computed authority check
}
```

**Gemma Instructions**:
```
Classify this message into ONE category:
QUERY, COMMAND, MONITOR, SCHEDULE, SOCIAL, SYSTEM, CONVERSATION

Message: "{message}"

Rules:
- Questions about code/docs/WSPs = QUERY
- Requests to run/execute/deploy/fix = COMMAND
- Status/health/metrics requests = MONITOR
- Time-bound requests (schedule/remind) = SCHEDULE
- Social engagement (comment/post/reply) = SOCIAL
- System admin (restart/configure) = SYSTEM
- Casual chat/greeting = CONVERSATION

Output: {"category": "QUERY", "confidence": 0.92}
```

**Expected Reasoning Time**: <10ms (Gemma 270M binary classification)

### Step 2: Authority Gate (Deterministic)

**Logic**:
```python
if category in (COMMAND, SYSTEM) and not is_commander:
    category = CONVERSATION  # Downgrade
    confidence *= 0.5        # Lower confidence
```

**No LLM needed** - pure deterministic gate.

### Step 3: Route Resolution (Lookup)

**Map category -> domain route** using DOMAIN_ROUTES table.

**Output**:
```python
{
    "category": "QUERY",
    "confidence": 0.92,
    "route": "holo_index",
    "authority_check": "passed",
    "downgraded": false
}
```

---

## Gemma Validation Pattern

- [ ] Category is one of 7 valid values?
- [ ] Confidence is 0.0-1.0?
- [ ] Authority gate applied for COMMAND/SYSTEM?
- [ ] Route matches category in DOMAIN_ROUTES?

---

## Benchmark Test Cases

**Test 1: Clear Query**
```yaml
Input: "What is the WRE orchestrator?"
Expected: {category: QUERY, route: holo_index}
```

**Test 2: Command from Non-Commander**
```yaml
Input: "Run the deploy script"
Sender: "random_user"
Expected: {category: CONVERSATION, downgraded: true}
```

**Test 3: Monitor Request**
```yaml
Input: "Show system status"
Expected: {category: MONITOR, route: ai_overseer}
```

**Test 4: Ambiguous (Greeting)**
```yaml
Input: "Hey there!"
Expected: {category: CONVERSATION, route: digital_twin}
```

---

## Learning & Evolution

**Current**: Keyword heuristic (openclaw_dae.py INTENT_KEYWORDS)
**Target**: Gemma 270M via llama_cpp (E:/HoloIndex/models/gemma-3-270m-it-Q4_K_M.gguf)
**Promotion Path**: keyword -> Gemma binary -> Gemma fine-tuned

---

**Skill Status**: PROTOTYPE
**Next Steps**:
1. Collect labeled intent dataset from OpenClaw webhook traffic
2. Benchmark Gemma 270M vs keyword heuristic on labeled set
3. If Gemma >85% accuracy, promote to staged
4. Fine-tune on domain-specific intents if needed
