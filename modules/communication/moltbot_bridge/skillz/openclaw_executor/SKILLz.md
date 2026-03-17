---
name: openclaw_executor
description: Execute WRE-routed tasks from OpenClaw intent classification with graduated autonomy
version: 1.0.0
author: 0102
agents: [qwen, gemma]
dependencies: [openclaw_dae, wre_core, agent_permissions, ai_overseer]
domain: communication
intent_type: DECISION
promotion_state: prototype
pattern_fidelity_threshold: 0.90
category: workflow
evals: []
---
# OpenClaw Executor Skill

**Skill Type**: Micro Chain-of-Thought (WSP 96)
**Intent**: DECISION (execute routed tasks with permission gating)
**Agents**: Qwen 1.5B (strategic planning), Gemma 270M (validation)
**Promotion State**: prototype
**Version**: 1.0.0

---

## Skill Purpose

Execute WRE-routed tasks originating from OpenClaw intent classification.
This is the "doer" skill that bridges OpenClaw's intent understanding
with Foundups-Agent's execution capabilities.

**Architecture Position**:
```
OpenClaw Gateway -> Intent Router (classify) -> THIS SKILL (execute)
                                                    |
                    +-------------------------------+
                    |               |               |
              HoloIndex        WRE Execute     AI Overseer
              (queries)        (commands)       (monitoring)
```

**Trigger Source**: OpenClawDAE._execute_plan()

**Success Criteria**:
- Correct domain DAE invoked for each intent category
- Permission gate enforced before any mutation
- Execution outcomes stored in pattern memory
- Security: secrets never leaked in responses

---

## Micro Chain-of-Thought Steps

### Step 1: Validate Execution Plan (Gemma Fast Check)

**Input Context Required**:
```python
{
    "plan": ExecutionPlan,     # From intent router
    "intent": OpenClawIntent,  # Classified intent
    "tier": AutonomyTier,      # Resolved permission tier
}
```

**Gemma Instructions**:
```
Validate this execution plan:
- Route: {plan.route}
- Steps: {plan.steps}
- Permission: {plan.permission_level}
- Commander: {intent.is_authorized_commander}

Check:
1. Route exists in DOMAIN_ROUTES?
2. Permission tier sufficient for route?
3. Steps are non-empty?
4. No forbidden patterns in task description?

Output: {"valid": true, "issues": []}
```

**Expected Reasoning Time**: <10ms

### Step 2: Execute via Domain Router (Qwen Strategic)

**Route -> Handler Mapping**:

| Route | Handler | Method |
|-------|---------|--------|
| holo_index | HoloIndex.search() | Semantic code+WSP search |
| wre_orchestrator | WREMasterOrchestrator.execute() | Pattern recall + skill execution |
| ai_overseer | AIOverseer.monitor_daemon() | Status + daemon monitoring |
| youtube_shorts_scheduler | ContentPageScheduler | Schedule via Studio |
| communication | LiveChat/VideoComments DAE | Social engagement |
| infrastructure | System commands | Config/restart (commander) |
| digital_twin | CommentDrafter + VoiceMemory | Conversational response |

**Qwen Instructions**:
```
Execute the routed task:
1. Identify handler for route "{plan.route}"
2. Prepare input context from intent
3. Call handler with appropriate parameters
4. Capture structured output
5. Format response for channel delivery

If handler unavailable:
- Return informative status message
- Log availability issue
- Suggest alternative action

Output: {"response": str, "success": bool, "handler_used": str}
```

**Expected Reasoning Time**: 200ms-10s (depends on handler)

### Step 3: Post-Execution Validation (Gemma)

**Gemma Instructions**:
```
Validate execution result:
1. Response is non-empty?
2. No secret patterns (AIza*, sk-*, oauth_token*, Bearer ey*)?
3. Response matches intent category expectations?
4. No WSP violations in output?

Output: {"valid": true, "violations": [], "redacted": false}
```

### Step 4: Store Outcome (Pattern Memory)

**Automatic storage** in WRE SQLite pattern memory:
```python
SkillOutcome(
    execution_id=uuid,
    skill_name="openclaw_executor",
    agent="openclaw_dae",
    input_context={message, channel, category},
    output_result={response_length, route, tier},
    success=True/False,
    pattern_fidelity=gemma_score,
    execution_time_ms=elapsed,
)
```

---

## Permission Matrix

| Route | ADVISORY | METRICS | DOCS_TESTS | SOURCE |
|-------|----------|---------|------------|--------|
| holo_index | READ | READ+LOG | READ+LOG | READ+LOG |
| wre_orchestrator | BLOCKED | BLOCKED | EXECUTE | EXECUTE |
| ai_overseer | READ | READ+LOG | READ+LOG | FULL |
| scheduler | BLOCKED | SCHEDULE | SCHEDULE | SCHEDULE |
| communication | BLOCKED | ENGAGE | ENGAGE | ENGAGE |
| infrastructure | BLOCKED | BLOCKED | BLOCKED | EXECUTE |
| digital_twin | CHAT | CHAT | CHAT | CHAT |

---

## OpenClaw Skill Mapping

These OpenClaw workspace skills map to WRE execution:

| OpenClaw Skill | WRE Handler | Description |
|---------------|-------------|-------------|
| holo-search | HoloIndex.search() | Semantic codebase search |
| foundups-wsp | WSP_MASTER_INDEX lookup | Protocol compliance |
| (planned) openclaw-schedule | ContentPageScheduler | YouTube scheduling |
| (planned) openclaw-engage | LiveChat DAE | Social engagement |
| (planned) openclaw-monitor | AI Overseer | System monitoring |
| (planned) openclaw-git | GitPush DAE | Autonomous commits |

---

## Libido Thresholds

**Pattern Frequency Limits**:
- `min_frequency`: 1 per hour (at least respond to something)
- `max_frequency`: 100 per hour (rate limit for abuse prevention)
- `cooldown_period`: 0s (no cooldown - interactive system)

**Rationale**: Unlike batch DAEs (gitpush, scheduler), OpenClaw is
interactive and must respond to every message. Libido monitoring
tracks frequency for abuse detection, not throttling.

---

## Benchmark Test Cases

**Test 1: Query Execution**
```yaml
Input: {category: QUERY, message: "explain WRE", route: holo_index}
Expected: HoloIndex search results formatted as response
Validation: Non-empty, no secrets, contains code/WSP references
```

**Test 2: Blocked Command**
```yaml
Input: {category: COMMAND, is_commander: false, route: wre_orchestrator}
Expected: Downgraded to CONVERSATION, advisory response only
Validation: No execution occurred, response is informative
```

**Test 3: Monitor Status**
```yaml
Input: {category: MONITOR, route: ai_overseer}
Expected: System status report (WRE, Overseer, Permissions state)
Validation: Contains status indicators, no errors
```

**Test 4: Security Filter**
```yaml
Input: Any category, response contains "AIzaSyB123..."
Expected: Response REDACTED, WSP violation logged
Validation: "REDACTED" in output, violation count > 0
```

---

**Skill Status**: PROTOTYPE
**Next Steps**:
1. Wire real domain DAE handlers (replace placeholder responses)
2. Add session context (conversation history across messages)
3. Implement event-driven triggers (beyond webhook)
4. Add queue-based dispatch for async operations
