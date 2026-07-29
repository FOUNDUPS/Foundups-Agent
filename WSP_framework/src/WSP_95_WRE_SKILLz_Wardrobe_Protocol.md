# WSP 95: WRE Skills Wardrobe Protocol

**Version**: 1.5 (Provider-Neutral Role Skillz)
**Date**: 2026-07-29
**Status**: Active
**Authority**: 0102 + User Specification
**Compliance**: WSP 3 (Module Organization), WSP 77 (Agent Coordination), WSP 50 (Pre-Action), WSP 22 (ModLog)

---

## 2026-02-19 Implementation Alignment Addendum

This addendum is normative for current WRE runtime behavior:

- **File preference and compatibility**:
  - Canonical skill filename is `SKILLz.md`.
  - Runtime loader must support fallback to legacy `SKILL.md` when `SKILLz.md` is absent.
- **Discovery path normalization**:
  - Discovery treats both `.../skills/...` and `.../skillz/...` as production wardrobes.
  - Path normalization must be cross-platform (`/` and `\` separators).
- **Loader resilience requirement**:
  - Missing skill registry/file in production must not hard-crash orchestration loops.
  - Runtime must degrade to deterministic fallback instructions and continue with explicit telemetry.
- **Pattern-memory isolation requirement**:
  - Shared singleton memory is permitted for default production DB.
  - Explicit DB paths (especially test runs) must be isolated to prevent cross-run contamination.

These rules align wardrobe protocol text with deployed WRE behavior and test gates.

---

## 2026-07-29 Provider-Neutral Role Skillz Addendum

This addendum is normative for production Skillz that coordinate logical
roles across a governed workflow.

- A role Skillz defines behavior and logical roles only. Examples include
  `principal`, `researcher`, `critic`, `implementer`, and `verifier`.
- A role Skillz must not name, prefer, or select a provider, model, endpoint,
  or API credential.
- Actual role assignments come only from current, task-specific, signed model
  selection and runtime-binding receipts.
- Model names found in task prose, retrieved evidence, memory, registry
  metadata, or Skillz content are not authority.
- Production role Skillz use an exact allowlisted registry and frontmatter
  schema. Unknown fields fail admission; a denylist is insufficient.
- Frontmatter and registry values for name, version, description, intent type,
  promotion state, logical roles, and WSP chain must agree exactly.
- The checked-in Skillz content and registry entry must be digest-bound before
  use. A persisted work item must be revalidated against the current sealed
  runtime Skillz receipt before execution or resume.
- The verifier role must remain independent of the candidate author or panel.
- A Skillz receipt describes operating discipline and grants no repository,
  shell, signer, worktree, PR, merge, or HoloIndex mutation authority.

Legacy task-specific Skillz may retain historical agent preference fields for
compatibility. They do not satisfy this provider-neutral role contract until
they are migrated and admitted through its exact schema.

---

## First Principles

### What Is a Skill?

A **skill** is a discrete, task-specific instruction set that tells an AI agent **how to act** when performing a specific task.

**Not Documentation** - Skills are **executable instructions**, like a recipe or playbook.

**Not Monolithic Prompts** - Skills are **step-by-step reasoning chains** with validation at each step (Micro Chain-of-Thought paradigm).

**Trainable Weights** - Skills evolve through feedback loops, analogous to neural network parameters:
- Instructions = weight values
- Pattern fidelity = loss function
- Qwen variations = gradient descent
- A/B testing = validation
- Version update = weight checkpoint

---

### Micro Chain-of-Thought Paradigm

**Key Innovation**: Skills are NOT single-shot prompts. They are **multi-step reasoning chains** where each step is validated before proceeding to the next.

**Architecture**:
```yaml
Step 1: Strategic Analysis (Qwen)
  ↓ Gemma validates: Did Qwen follow instructions?
Step 2: Decision Logic (Qwen)
  ↓ Gemma validates: Is the decision correct?
Step 3: Action Generation (Qwen)
  ↓ Gemma validates: Does action match decision?
Step 4: Execution Planning (Qwen)
  ↓ Gemma validates: Is the plan complete?
```

**Why This Works**:
- **Gemma (270M)**: Fast pattern validation (<10ms per check)
- **Qwen (1.5B+)**: Strategic thinking in focused steps
- **Each step validated**: High overall fidelity
- **Failures isolated**: Easy to debug and evolve

**Example - qwen_gitpush Skill** (see [modules/infrastructure/git_push_dae/skills/qwen_gitpush/SKILL.md](../../../modules/infrastructure/git_push_dae/skills/qwen_gitpush/SKILL.md)):

**Step 1: Analyze Git Diff** (Qwen 200-500ms)
```yaml
Input: git_diff, files_changed, lines_added/deleted
Output: {change_type, summary, critical_files, confidence}
Gemma Validation: All required fields present?
```

**Step 2: Calculate WSP 15 MPS Score** (Qwen 100-200ms)
```yaml
Formula: MPS = Complexity + Importance + Deferability + Impact
Output: {complexity: 3, importance: 4, deferability: 3, impact: 4, mps_score: 14, priority: "P1"}
Gemma Validation: Sum correct? Priority mapped correctly?
```

**Step 3: Generate Semantic Commit Message** (Qwen 300-500ms)
```yaml
Format: <type>(<scope>): <subject>\n\n<body>\n\nWSP: <wsps>\nMPS: <priority> (<score>)
Output: "feat(gitpush): Add autonomous commit decision via WSP 15 MPS..."
Gemma Validation: Message follows format? Matches diff content?
```

**Step 4: Decide Push Action** (Qwen 50-100ms)
```yaml
Decision Matrix: P0 → push_now, P1 → push if >10 files OR >1hr, etc.
Output: {action: "push_now", reason: "MPS P1 + 14 files + 90min elapsed"}
Gemma Validation: Action matches MPS threshold logic?
```

**Total Time**: ~1 second
**Fidelity Target**: >90% (each step validated independently)

**Benefits Over Monolithic Prompts**:
1. **Isolation**: Failure in Step 2 doesn't invalidate Step 1's analysis
2. **Validation**: Gemma checks each step's output before next step begins
3. **Evolution**: Can improve individual steps without rewriting entire skill
4. **Debugging**: Know exactly which step failed (not generic "skill failed")
5. **Performance**: Small, focused reasoning at each step (not one giant prompt)

**Implementation Pattern**:
```python
# Skill execution with micro chain-of-thought
async def execute_skill(skill: Skill, context: dict):
    results = {}

    for step_num, step in enumerate(skill.steps, 1):
        # Qwen executes step
        qwen_output = await qwen.execute(step.instructions, context)
        results[f"step_{step_num}"] = qwen_output

        # Gemma validates step output
        validation = await gemma.validate(qwen_output, step.validation_pattern)

        if not validation.passed:
            # Step failed validation - stop here
            return SkillResult(
                success=False,
                failed_at_step=step_num,
                validation_errors=validation.errors,
                partial_results=results
            )

        # Pass validated output to next step's context
        context[f"step_{step_num}_output"] = qwen_output

    # All steps validated successfully
    return SkillResult(success=True, results=results)
```

**Reference Implementation**: [qwen_gitpush/SKILL.md](../../../modules/infrastructure/git_push_dae/skills/qwen_gitpush/SKILL.md) (3,500+ words, 4-step chain-of-thought with WSP 15 MPS scoring)

### Core Axiom: "The Wardrobe Tells Agents How to Act"

**Wardrobe** = Collection of skills an agent can "wear" for different tasks.

Just as humans wear different outfits for different occasions:
- Business suit → Professional meeting
- Lab coat → Scientific work
- Chef's apron → Cooking

AI agents "wear" different skills:
- `youtube_spam_detection` → Gemma moderates chat
- `youtube_banter_response` → Qwen generates creative responses
- `wsp_compliance_check` → Qwen validates code

**The skill defines behavior. The agent executes.**

---

## Architecture: Prototype Centrally, Deploy Modularly (Occam's Razor)

### The Scalability Problem

**Central Repository Breaks at Scale**:
```
100 modules × 5 skills each = 500 skills
Central .claude/skills/ = 500 directories (CHAOS, flat hell)
Distributed modules/*/skills/ = 5 per module (MANAGEABLE, cohesive)
```

**First Principle**: Skills belong WITH the modules they serve (cohesion, not centralization).

**Occam's Razor**: If code lives in `modules/communication/livechat/src/`, then skills for that code live in `modules/communication/livechat/skills/`.

---

### Prototype-Then-Deploy Architecture

**Phase 1: 0102 Testing Environment (`.claude/skills/[name]_prototype/`)**

**Purpose**: 0102 tests skills using Claude Code before production deployment

**Location**: `.claude/skills/[skill_name]_prototype/SKILL.md`

**Execution Context**: Claude Code skill system (0102's testing sandbox)

**Agents in Testing**:
- **Primary**: Claude Sonnet 4.5 (0102) validates skill
- **Secondary**: Gemma/Qwen CAN execute via Claude Code (for testing compatibility)

**Entry Point**: Claude Code's skill auto-discovery mechanism

**Lifecycle**:
1. Qwen generates baseline `SKILL.md` template
2. 0102 manually tests using Claude Code
3. 0102 runs benchmark test cases
4. Gemma/Qwen can be invoked via Claude Code for compatibility testing
5. If valid, promote to staged for extended testing

**Why Test Here?**
- Claude Code provides skill execution environment for 0102
- Fast iteration without production deployment overhead
- Safe sandbox for experimental skills
- 0102 can validate before deploying to native agents

**CRITICAL**: This is 0102's **testing environment**, NOT production for native agents.

---

**Phase 2: 0102 Staged Testing (`.claude/skills/[name]_staged/`)**

**Purpose**: Extended 0102 testing with metrics collection before production

**Location**: `.claude/skills/[skill_name]_staged/SKILL.md`

**Execution Context**: Still Claude Code (0102's testing environment)

**Agents in Testing**:
- **Primary**: 0102 executes via Claude Code
- **Secondary**: Gemma/Qwen execute via Claude Code (testing only)

**Metrics Tracking**:
- Pattern fidelity (0102 manually validates, Gemma scores)
- Outcome correctness (0102 reviews decisions)
- Performance timing (execution speed measured)

**Lifecycle**:
1. Skill promoted from prototype after 0102 approval
2. Extended testing with real-world-like workloads
3. Metrics collected to JSON (append-only)
4. After ≥100 test executions with ≥90% fidelity, ready for production
5. If fidelity <85%, rollback to prototype for fixes

**Why Stage Here?**
- 0102 validates skill stability before production deployment
- Metrics collected in controlled environment
- Easy rollback to prototype if issues found
- Final validation before native agent deployment

**CRITICAL**: This is still 0102's **testing environment**, NOT production.

---

**Phase 3: Production Deployment (`modules/[domain]/[block]/skills/[name]/`)**

**Purpose**: Native Gemma/Qwen/Grok/UI-TARS execution in production DAEs

**Location**: `modules/[domain]/[block]/skills/[skill_name]/SKILL.md`

**Execution Context**: Production DAEs (Gemma/Qwen/Grok/UI-TARS native execution)

**Agents**: Qwen 1.5B, Gemma 3 270M, Grok (xAI), UI-TARS 1.5 7B

**Entry Point**: `WRESkillsLoader` (progressive disclosure + dependency injection)

**Lifecycle**:
1. Skill promoted from staged after passing 0102's validation gates
2. **MOVED** from `.claude/skills/*_staged/` to `modules/[domain]/[block]/skills/[name]/`
3. File deleted from `.claude/skills/` (staged location)
4. WRE loader injects into native agent prompts at runtime
5. Gemma scores pattern fidelity after every production execution
6. Qwen generates variations if fidelity drops below 90%
7. Best variation becomes new version (checked into version control)

**Why Deploy to Modules?**
- **Production Context**: Native agents execute from module location
- **Cohesion**: Skills live WHERE THEY'RE USED
- **Scalability**: 5 skills per module (not 500 in one directory)
- **Modularity**: Module imports work naturally with co-located skills
- **Discovery**: HoloIndex indexes module structure (already does!)
- **WSP 3 Compliance**: Domain → Block → Cube pattern (skills/ is part of block)

**CRITICAL**: This is where **production native agents execute skills**, not `.claude/skills/`.

---

### Real-World Example: Unicode Daemon Monitor

**Prototype Phase**:
```
.claude/skills/unicode_daemon_monitor_prototype/SKILL.md
- 0102 creates initial version
- Tests with manual daemon output
- Validates fix patterns work
- Multi-agent testing (0102, QWEN, Gemma)
```

**Staged Phase**:
```
.claude/skills/unicode_daemon_monitor_staged/SKILL.md
- Promoted after 0102 approval
- Live monitoring of YouTube daemon
- Gemma scores: 97% fidelity (145/150 executions)
- Performance: <30s fix cycle (baseline: 15-30min manual)
- Ready for production promotion
```

**Production Phase**:
```
modules/communication/livechat/skills/unicode_daemon_monitor/SKILL.md
- MOVED from staged (not copied)
- Lives with livechat module (cohesion)
- Native QWEN/Gemma execution
- Full integration with chat_sender, message_processor
- Version controlled with module code
```

**Why This Works**:
- Prototype: Fast iteration, no module overhead
- Staged: Real-world testing, metrics validation
- Production: Module cohesion, scalable organization

---

## Occam's Razor: Why Three Phases?

**Question**: Why not just develop directly in `modules/*/skills/`?

**Answer**: Separation of concerns + risk management.

| Aspect | Prototype | Staged | Production |
|--------|-----------|--------|------------|
| **Location** | `.claude/skills/*_prototype/` | `.claude/skills/*_staged/` | `modules/[domain]/[block]/skills/` |
| **Execution Context** | Claude Code (0102 testing) | Claude Code (0102 testing) | Production DAEs (native agents) |
| **Purpose** | Initial testing by 0102 | Extended testing by 0102 | Native agent execution |
| **Primary Agent** | 0102 via Claude Code | 0102 via Claude Code | Gemma/Qwen/Grok/UI-TARS |
| **Secondary Agents** | Gemma/Qwen via Claude Code | Gemma/Qwen via Claude Code | None (native only) |
| **Risk** | High (experimental) | Medium (testing) | Low (validated) |
| **Metrics** | Manual observation | Automated collection | Automated + evolution |
| **Rollback** | Delete | To prototype | To staged |
| **Scope** | Central (0102 sandbox) | Central (0102 sandbox) | Distributed (module cohesion) |

**First Principle**: Test in 0102's sandbox (`.claude/skills/` via Claude Code), deploy to production modules (`modules/*/skills/` for native agents).

**Occam's Razor**: Don't mix execution contexts. 0102 tests via Claude Code. Native agents execute from modules.

---

## Skills Directory Structure (WSP 3 Integration)

### Standard Module with Skills

```
modules/[domain]/[block]/
├── src/                          # The Cube (implementation)
│   ├── __init__.py
│   └── *.py
├── skills/                       # The Wardrobe (AI instructions)
│   ├── [skill_name]/
│   │   ├── SKILLz.md             # Instructions (YAML + Markdown) - Note the 'z'!
│   │   ├── versions/
│   │   │   ├── v1.0_baseline.md
│   │   │   ├── v1.1_improved.md
│   │   │   └── v1.2_optimized.md
│   │   ├── metrics/              # Pattern fidelity scores
│   │   │   └── fidelity.json
│   │   ├── variations/           # A/B test candidates
│   │   │   ├── var_a.md
│   │   │   └── var_b.md
│   │   └── CHANGELOG.md          # Evolution rationale
│   └── ...                       # Additional skills
├── tests/
├── docs/
├── INTERFACE.md
├── README.md
├── ModLog.md
└── requirements.txt
```

**Compliance**: WSP 3 (Module Organization) mandates `skills/` directory at block level.

---

## SKILLz.md Format Specification

> **Why "SKILLz"?** The 'z' suffix makes skill files immediately recognizable as FoundUps/WRE agent instructions. When you see `SKILLz.md`, you know it's a recipe for AI, not documentation.

### Structure

```yaml
---
# Metadata (YAML Frontmatter)
name: skill_name_intent_type
description: One-line description of task
version: 1.0_production
author: qwen_baseline_generator | 0102 | qwen_variation_generator
created: 2025-10-20
agents: [primary_agent, fallback_agent]
primary_agent: gemma | qwen | grok | ui-tars
intent_type: CLASSIFICATION | DECISION | GENERATION | TELEMETRY
promotion_state: prototype | staged | production
pattern_fidelity_threshold: 0.90
test_status: passing | failing | needs_validation

# Dependencies
dependencies:
  data_stores:
    - name: youtube_telemetry_store
      type: sqlite
      path: modules/communication/livechat/src/youtube_telemetry_store.py
  mcp_endpoints:
    - endpoint_name: holo_index
      methods: [semantic_search, wsp_lookup]
  throttles:
    - name: youtube_api_quota
      max_rate: 10000_units_per_day
      cost_per_call: 5_units
  required_context:
    - last_100_messages: "Recent chat message history"
    - user_message_frequency: "Rate limiting data"

# Metrics Configuration
metrics:
  pattern_fidelity_scoring:
    enabled: true
    frequency: every_execution
    scorer_agent: gemma
    write_destination: modules/infrastructure/wre_core/recursive_improvement/metrics/[skill_name]_fidelity.json
  promotion_criteria:
    min_pattern_fidelity: 0.90
    min_outcome_quality: 0.85
    min_execution_count: 100
    required_test_pass_rate: 0.95
---

# [Skill Name]

**Purpose**: Concise description of what this skill accomplishes

**Intent Type**: [CLASSIFICATION | DECISION | GENERATION | TELEMETRY]

**Agent**: [gemma | qwen | grok | ui-tars]

---

## Task

[1-2 paragraph description of the task this AI performs]

## Instructions (For AI Agent)

### 1. [INSTRUCTION_NAME]
**Rule**: IF [condition] THEN [action]
**Expected Pattern**: [pattern_name]=True

**Steps**:
1. [Step 1]
2. [Step 2]
3. If [condition] → decision="X", reason="Y"
4. Log: `{"pattern": "[pattern_name]", "value": true, ...}`

**Examples**:
- ✅ [Positive example that should pass]
- ❌ [Negative example that should fail]

### 2. [NEXT_INSTRUCTION]
[... repeat pattern ...]

---

## Expected Patterns Summary

Pattern fidelity scoring expects these patterns logged:

```json
{
  "execution_id": "exec_001",
  "patterns": {
    "pattern_1_executed": true,
    "pattern_2_executed": true,
    "pattern_3_executed": false
  }
}
```

**Fidelity Calculation**: `(patterns_executed / total_patterns)`

---

## Benchmark Test Cases

### Test Set 1: [Category] (N cases)
1. Input: `[input]` → Expected: `[output]` (Reason: [why])
2. Input: `[input]` → Expected: `[output]` (Reason: [why])
...

**Total**: N test cases across M categories

---

## Success Criteria

- ✅ Pattern fidelity ≥ 90%
- ✅ Outcome quality ≥ 85%
- ✅ Zero false negatives on critical decisions
- ✅ False positive rate < 5%
```

**Compliance**: Format based on Anthropic Skills specification + WRE extensions

---

## Mandatory Skill Safety Gate (Supply Chain + Runtime)

All skills entering staged or production must pass automated scanner checks.

**Minimum required policy**:
- Scanner runs before every promotion gate decision.
- Default posture is fail-closed when scanner is unavailable.
- Promotion is blocked when findings exceed configured severity threshold.
- Runtime mutating routes execute cached preflight scans with bounded TTL.
- Every block/allow decision is auditable and linked to the skill artifact version.

**Reference implementation target**:
- Scanner CLI: `skill-scanner` (Cisco AI Skill Scanner or equivalent approved tool)
- Threshold default: `medium`
- Required mode default: enabled
- Enforced mode default: enabled

---

## Promotion Lifecycle (3 States)

### State 1: Prototype (`.claude/skills/[skill_name]_prototype/`)

**Purpose**: 0102 manual validation

**Requirements**:
- Baseline `SKILL.md` generated by Qwen
- Benchmark test cases defined
- 0102 executes tests manually

**Promotion Gate**: prototype → staged
- ✅ Pattern fidelity ≥ 90% across all benchmark tests
- ✅ Outcome quality ≥ 85%
- ✅ Zero critical false negatives
- ✅ False positive rate < 5%
- ✅ WSP 50 approval (no duplication)
- ✅ Test coverage complete
- ✅ Dependencies validated
- ✅ Security reviewed
- Skill scanner pass (severity <= policy threshold; required mode enforced)
- ✅ 0102 (AI supervisor) approval record in database

**Automation**: None (manual validation only)

---

### State 2: Staged (`.claude/skills/[skill_name]_staged/`)

**Purpose**: Live testing with automated metrics collection

**Requirements**:
- Promoted from prototype
- Automated metrics enabled
- Gemma pattern fidelity scoring active

**Promotion Gate**: staged → production
- ✅ Sustained pattern fidelity ≥ 90% over 100 executions
- ✅ Sustained outcome quality ≥ 85% over 100 executions
- ✅ Zero regressions vs prototype baseline
- ✅ No critical failures (exceptions)
- ✅ Gemma validation: Consistent patterns
- ✅ Production readiness confirmed
- ✅ Integration approved
- ✅ Monitoring configured
- ✅ Rollback plan tested
- ✅ Documentation updated
- Skill scanner pass (severity <= policy threshold; required mode enforced)
- ✅ 0102 (AI supervisor) approval record in database

**Automation**:
- Gemma scores every execution
- Qwen reviews daily
- SQLite ingestion hourly

---

### State 3: Production (`modules/[domain]/[block]/skills/[skill_name]/`)

**Purpose**: Native Qwen/Gemma/Grok/UI-TARS execution in production

**Requirements**:
- Promoted from staged
- **MOVED** to module's `skills/` directory (not copied - file deleted from `.claude/skills/*_staged/`)
- WRE loader integration complete
- HoloIndex re-indexed to reflect new location

**Promotion Process**:
```bash
# Executed by skills_registry_v2.py::promote_skill()
1. Check promotion gate criteria (≥100 executions, ≥90% fidelity)
2. Run skill scanner and validate severity threshold policy
3. Verify human approval exists in database
4. MOVE SKILL.md from .claude/skills/[name]_staged/ to modules/[domain]/[block]/skills/[name]/
5. Update skills_registry.json (promotion_state: "production")
6. Trigger HoloIndex re-index
7. Update ModLog with promotion event
8. Append promotion_event to metrics JSON
```

**Rollback Triggers** (Automated):
- Pattern fidelity < 85% (sustained over 10 executions)
- Outcome quality < 80% (sustained)
- Exception rate > 5%
- Dependency failure
- Execution time > 3x baseline
- Skill scan result exceeds policy threshold
- Skill scanner unavailable while required mode is enabled

**Rollback Process**:
```bash
# Executed by skills_registry_v2.py::rollback_skill()
1. MOVE SKILL.md from modules/[domain]/[block]/skills/[name]/ to .claude/skills/[name]_staged/
2. Update skills_registry.json (promotion_state: "staged")
3. Trigger HoloIndex re-index
4. Update ModLog with rollback event (reason, trigger metric)
5. Append rollback_event to metrics JSON
```

**Automation**:
- Gemma scores every execution
- Qwen reviews weekly
- Automatic rollback on threshold violations
- Runtime preflight skill scan with TTL-bounded cache
- HoloIndex re-indexed on state changes
- ModLog updated automatically

---

## Agent Specialization (WSP 77 Integration)

| Agent | Role | Skill Types | Example Skills |
|-------|------|-------------|----------------|
| **Gemma 3 270M** | Fast classification, pattern validation | CLASSIFICATION | youtube_spam_detection, youtube_toxic_filtering, youtube_message_classification |
| **Qwen 1.5B** | Strategic planning, coordination | DECISION, GENERATION, TELEMETRY | youtube_channel_prioritization, youtube_banter_response, wsp_compliance_check |
| **Grok (xAI)** | Creative generation, analysis | GENERATION | social_content_generation, log_analysis_diagnosis, hashtag_optimization |
| **UI-TARS 1.5 7B** | Browser automation, visual tasks | DECISION | browser_automation_scheduling, form_field_detection |

**Principle**: Each agent has specialized capabilities. Skills are assigned to agents based on intent type and task requirements.

**Fallback**: Skills can specify fallback agents (e.g., `primary: gemma, fallback: qwen` for toxic filtering escalation).

---

## Pattern Fidelity Scoring (Gemma Validation)

### Concept

**Pattern fidelity** = How well the agent followed the skill instructions

**Analogy**: Like grading a student on whether they followed the assignment rubric.

### Process

1. **Agent executes skill** (e.g., Gemma runs youtube_spam_detection)
2. **Agent logs patterns**:
   ```json
   {
     "execution_id": "exec_001",
     "patterns": {
       "caps_check_executed": true,
       "repetition_check_executed": true,
       "rate_limit_applied": false,
       "toxicity_check_executed": true,
       "allowed_and_routed": false
     }
   }
   ```
3. **Gemma scores fidelity**:
   ```python
   fidelity = patterns_followed / total_patterns_in_skill
   # Example: 3 / 5 = 0.60 (60% fidelity - FAILING)
   ```
4. **Store metric**:
   ```bash
   modules/infrastructure/wre_core/recursive_improvement/metrics/youtube_spam_detection_fidelity.json
   ```
5. **Promote or rollback based on threshold**:
   - If fidelity ≥ 90%: Continue or promote
   - If fidelity < 85%: Trigger rollback or Qwen variation generation

---

## Skill Evolution (Qwen Variation Generation)

### When to Evolve

**Triggers**:
- Pattern fidelity drops below 90% (but > 85%)
- Outcome quality degrades
- New edge cases discovered
- 0102 requests improvement

### Process

1. **Qwen analyzes weak patterns**:
   ```python
   weak_patterns = [p for p in patterns if fidelity[p] < 0.90]
   ```

2. **Qwen generates variations**:
   ```markdown
   # Variation A: Add explicit step
   ### 2. REPETITION CHECK
   **Rule**: IF message in recent_history AND count >= 3 → BLOCK
   **Expected Pattern**: repetition_check_executed=True

   **NEW STEP**: Before checking history, normalize message (lowercase, strip whitespace)
   ```

3. **A/B test variations**:
   - Run variation A on 50% of traffic
   - Run current version on 50% of traffic
   - Compare fidelity scores after 100 executions each

4. **Promote winner**:
   - If variation A has higher fidelity → Update SKILL.md
   - Save old version to `versions/v1.1_[description].md`
   - Update CHANGELOG.md with rationale

5. **Archive losing variations**:
   - Store in `variations/rejected/`
   - Document why rejected for future reference

---

## 0102 (AI Supervisor) Approval Tracking (WSP 50 Integration)

### Database Schema

```sql
CREATE TABLE ai_0102_approvals (
    approval_id TEXT PRIMARY KEY,
    skill_id TEXT NOT NULL,
    promotion_path TEXT NOT NULL,  -- "prototype->staged", "staged->production"
    approver TEXT NOT NULL,         -- "0102" (AI supervisor, not 012 human)
    approval_ticket TEXT NOT NULL,

    -- WSP 50 Pre-Action Verification
    wsp_50_no_duplication BOOLEAN NOT NULL,
    wsp_50_evidence TEXT,

    -- Test coverage
    test_coverage_complete BOOLEAN NOT NULL,
    test_evidence TEXT,

    -- Instruction clarity
    instruction_clarity_approved BOOLEAN NOT NULL,

    -- Dependencies validated
    dependencies_validated BOOLEAN NOT NULL,
    dependency_evidence TEXT,

    -- Security review
    security_reviewed BOOLEAN NOT NULL,
    security_notes TEXT,

    -- Production-specific
    production_readiness BOOLEAN,
    integration_approved BOOLEAN,
    monitoring_configured BOOLEAN,
    rollback_tested BOOLEAN,
    documentation_updated BOOLEAN,

    approval_timestamp TIMESTAMP NOT NULL,
    notes TEXT
)
```

**Location**: `modules/infrastructure/wre_core/skills/skills_metrics.db`

**Enforcement**: `WRESkillsRegistryV2` blocks promotion without valid 0102 approval record.

**Key Point**: 0102 (AI supervisor, Claude) approves promotions, NOT 012 (human). Qwen/Gemma are smaller AIs that cannot make promotion decisions - 0102 provides the necessary oversight and WSP 50 verification.

---

## Metrics Collection Architecture

### Hybrid System (JSON + SQLite)

**Design Principle**: Fast writes (JSON), structured queries (SQLite)

### Layer 1: JSON Append-Only (Real-Time)

**Purpose**: Fast, concurrent writes from multiple DAEs

**Tool**: `MetricsAppenderV2` with file locking

**Format**: Newline-delimited JSON (NDJSON)

**Files**:
```
modules/infrastructure/wre_core/recursive_improvement/metrics/
├── [skill_name]_fidelity.json          # Pattern fidelity scores
├── [skill_name]_outcomes.json          # Decision correctness
├── [skill_name]_performance.json       # Execution timing
└── [skill_name]_promotion_log.json     # State transitions
```

**Benefits**:
- Fast appends (no database locks)
- Easy diffing (git-friendly)
- Rollback-friendly (restore from file)
- Human-readable

---

### Layer 2: SQLite Analytics (Batch)

**Purpose**: Structured queries for promotion gating and analytics

**Tool**: `MetricsIngestorV2` with hourly batch processing

**Database**: `modules/infrastructure/wre_core/skills/skills_metrics.db`

**Schema**:
```sql
-- Separate tables (no field overwrites)
fidelity_metrics (execution_id, skill_id, pattern_fidelity, patterns_followed, patterns_missed, ...)
outcome_metrics (execution_id, skill_id, decision, correct, confidence, ...)
performance_metrics (execution_id, skill_id, execution_time_ms, exception, ...)

-- Promotion tracking
promotion_events (event_id, skill_id, from_state, to_state, approver, ...)
rollback_events (event_id, skill_id, trigger_reason, trigger_metric, ...)
human_approvals (approval_id, skill_id, wsp_50_no_duplication, ...)
```

**Benefits**:
- Aggregations (AVG, MIN, MAX, COUNT)
- Joins across tables
- Indexed lookups (fast promotion checks)
- No external dependencies

---

## WRE Skills Loader (Entry Point)

### Progressive Disclosure

**Principle**: Load metadata first, full content on-demand (performance)

```python
from modules.infrastructure.wre_core.skills.wre_skills_loader import WRESkillsLoader

loader = WRESkillsLoader()

# Step 1: Discover skills (metadata only)
skills = loader.discover_skills(agent_type="gemma", intent_type="CLASSIFICATION")
# Returns: [SkillMetadata(name, description, intent_type, ...)]

# Step 2: Load full skill content (on-demand)
skill_content = loader.load_skill("youtube_spam_detection", agent_type="gemma")

# Step 3: Inject into agent prompt (WRE entry point)
augmented_prompt = loader.inject_skill_into_prompt(base_prompt, "youtube_spam_detection", "gemma")
```

### Dependency Injection

**Context Prepared**:
```python
context = {
    'data_stores': {
        'youtube_telemetry_store': load_store('...')
    },
    'mcp_endpoints': {
        'holo_index': mcp_client.get_endpoint('holo_index')
    },
    'throttles': {
        'youtube_api_quota': ThrottleManager('youtube', max_rate=10000, cost_per_call=5)
    },
    'required_context': {
        'last_100_messages': fetch_recent_messages(100),
        'user_message_frequency': load_rate_data()
    }
}
```

**Injected into Skill**: Skill instructions reference `context['data_stores']['youtube_telemetry_store']`

---

## Registry & Promotion Automation

### Skills Registry

**File**: `modules/infrastructure/wre_core/skills/skills_registry.json`

**Contents**:
```json
{
  "version": "1.0",
  "last_updated": "2025-10-20T14:23:15Z",
  "skills": {
    "youtube_spam_detection": {
      "promotion_state": "production",
      "location": "modules/communication/livechat/skills/youtube_spam_detection/",
      "primary_agent": "gemma",
      "intent_type": "CLASSIFICATION",
      "last_promoted": "2025-10-20T12:00:00Z",
      "last_rollback": null,
      "metrics_path": "modules/infrastructure/wre_core/recursive_improvement/metrics/youtube_spam_detection_*.json"
    }
  }
}
```

**Principle**: Single source of truth for skill states

---

### Promotion Commands

```bash
# Check promotion readiness
python modules/infrastructure/wre_core/skills/promoter.py status \
  --skill youtube_spam_detection --target-state production

# Promote skill
python modules/infrastructure/wre_core/skills/promoter.py promote \
  --skill youtube_spam_detection \
  --from prototype --to staged \
  --approver 0102 \
  --approval-ticket APPROVAL_20251020_001

# Rollback skill (automatic or manual)
python modules/infrastructure/wre_core/skills/promoter.py rollback \
  --skill youtube_spam_detection \
  --from production --to staged \
  --reason pattern_fidelity_drop \
  --trigger-metric fidelity=0.83
```

**Automation**:
- HoloIndex re-indexed after promotions/rollbacks
- ModLog updated automatically (WSP 22)
- Metrics ingested before promotion checks

---

## Documentation Reference Map

| Document | Purpose | Location |
|----------|---------|----------|
| **AI_ENTRY_POINTS_MAPPING.md** | ~50 skills identified across codebase | `modules/infrastructure/wre_core/` |
| **PROMOTION_ROLLBACK_POLICY.md** | Complete promotion lifecycle | `modules/infrastructure/wre_core/skills/` |
| **SESSION_SUMMARY.md** | Implementation handoff document | `modules/infrastructure/wre_core/skills/` |
| **METRICS_INGESTION_FIX.md** | Critical issues identified & fixed | `modules/infrastructure/wre_core/skills/` |
| **FIXES_COMPLETE.md** | v2 implementation summary | `modules/infrastructure/wre_core/skills/` |
| **skills_graph.json** | Dependency graph (11 nodes, 8 edges) | `modules/infrastructure/wre_core/skills/` |
| **skills_registry.json** | Current skill states | `modules/infrastructure/wre_core/skills/` |
| **WRE_SKILLS_SYSTEM_DESIGN.md** | First principles design | `modules/infrastructure/wre_core/` |
| **ANTHROPIC_SKILLS_DEEP_DIVE.md** | Anthropic Skills spec | `.claude/skills/_meta/` |
| **WSP_3_Module_Organization_UPDATE_SKILLS.md** | skills/ directory mandate | `WSP_knowledge/src/` |

---

## Compliance Matrix

| WSP | Requirement | How Skills System Complies |
|-----|-------------|----------------------------|
| **WSP 3** | Module Organization | `skills/` directory at block level |
| **WSP 77** | Agent Coordination | Skills assigned by agent specialization |
| **WSP 50** | Pre-Action Verification | Human approvals tracked in database |
| **WSP 22** | ModLog Documentation | Auto-updates on promotions/rollbacks |
| **WSP 91** | DAEMON Observability | JSON + SQLite metrics telemetry |
| **WSP 48** | Recursive Self-Improvement | Qwen variation generation loop |

---

## First Principles Summary

### 1. Prototype Centrally, Deploy Modularly

**Prototype** (`.claude/skills/*_prototype/`) = Fast iteration, central discovery
**Staged** (`.claude/skills/*_staged/`) = Metrics validation, central monitoring
**Production** (`modules/[domain]/[block]/skills/`) = Module cohesion, distributed scalability

**Scalability**: 500 skills distributed across 100 modules (5 per module) beats 500 in one directory.

### 2. Skills Belong With Modules (Cohesion)

If code lives in `modules/communication/livechat/src/`, then skills live in `modules/communication/livechat/skills/`.

**Why?** Same reason we organize code by domain - cohesion, maintainability, discoverability via module structure.

### 3. Progressive Disclosure

Load metadata first (fast), full content on-demand (efficient).

### 4. Trainable Weights Analogy

Skills are not static docs. They evolve like neural network weights:
- Gemma scoring = loss function
- Qwen variations = gradient descent
- A/B testing = validation
- Version updates = weight checkpoints

### 5. Human-in-Loop Gates

0102 approval required at prototype→staged and staged→production gates. Automation assists, humans decide.

### 6. MOVE, Not Copy

**Promotion**: Skill MOVES from `.claude/skills/*_staged/` to `modules/*/skills/` (original deleted)
**Rollback**: Skill MOVES from `modules/*/skills/` back to `.claude/skills/*_staged/`

**Why?** Single source of truth. No stale copies. HoloIndex always knows current location.

### 7. Metrics Before Promotion

Can't promote without evidence. ≥100 executions, ≥90% fidelity, ≥85% outcome quality, human approval.

### 8. Automatic Rollback

Production can't wait for humans. If fidelity < 85% sustained, rollback immediately to staged.

---

## Known Limitations

1. **No unit tests yet** - v2 implementations need test coverage
2. **Promoter CLI not built** - Manual promotion for now
3. **Qwen variation generator not implemented** - Manual variations only
4. **Gemma pattern scorer not built** - Placeholder for now
5. **Dependency injection incomplete** - Context structure defined but not wired

---

## Roadmap

### Phase 1: Foundation (COMPLETE)
- ✅ AI entry points mapped (~50 skills)
- ✅ Promotion/rollback policy defined
- ✅ Metrics pipeline built (v2 with fixes)
- ✅ WRE loader created
- ✅ Human approval tracking added
- ✅ Skills dependency graph created

### Phase 2: Baseline Templates (NEXT)
- [ ] Qwen reads AI_ENTRY_POINTS_MAPPING.md
- [ ] Qwen generates 8 baseline SKILL.md templates (YouTube DAE Phase 1)
- [ ] 0102 validates each prototype manually
- [ ] 0102 creates approval records in database (ai_0102_approvals table)
- [ ] Promote to staged

### Phase 3: Automation
- [ ] Build promoter CLI (`promoter.py`)
- [ ] Implement Gemma pattern fidelity scorer
- [ ] Implement Qwen variation generator
- [ ] Add unit tests for v2 implementations
- [ ] Wire dependency injection in WRE loader

### Phase 4: Production
- [ ] Promote Phase 1 skills to production
- [ ] Expand to Phase 2 (Social Media - 5 skills)
- [ ] Expand to Phase 3 (WSP Orchestrator - 3 skills)
- [ ] Monitor metrics, iterate on variations

---

## Questions & Answers

### Q: Why not keep all skills in `.claude/skills/` centrally?

**A**: **Scalability breaks at scale**. With 100 modules and 500 skills, a central directory becomes flat chaos. Distributed organization (5 skills per module) maintains cohesion and human-parseable structure.

**Analogy**: Would you put all 500 Python files in one directory? No - you organize by domain/module. Skills follow same principle.

**HoloIndex solves discovery**: Modular location doesn't matter for finding skills - HoloIndex indexes everything. Structure matters for maintenance.

### Q: Why use `.claude/skills/` for prototype/staged if production goes to `modules/*/skills/`?

**A**: **`.claude/skills/` is 0102's testing environment using Claude Code**:
- **Prototype/Staged**: 0102 tests skills via Claude Code before deploying to native agents
- **Production**: Native Gemma/Qwen/Grok/UI-TARS execute from `modules/*/skills/`

**Execution Contexts**:
- `.claude/skills/`: Claude Code skill system (0102 testing sandbox)
- `modules/*/skills/`: Production DAEs (native agent execution)

**Don't pollute production modules with experimental skills under test**. Don't force 0102 to test in production locations. Test in Claude Code sandbox, deploy to modules after validation.

### Q: What happens to `.claude/skills/unicode_daemon_monitor_prototype/` at promotion?

**A**:
1. **prototype → staged** (still 0102 testing): COPY to `.claude/skills/unicode_daemon_monitor_staged/` (prototype kept for reference, both in Claude Code)
2. **staged → production** (deploy to native agents): MOVE to `modules/communication/livechat/skills/unicode_daemon_monitor/` (staged deleted, HoloIndex re-indexed)

**Result**:
- **Testing**: 0102 uses Claude Code to test skill in `.claude/skills/`
- **Production**: Native agents execute skill from `modules/communication/livechat/skills/` (no longer in `.claude/skills/`)

### Q: Can skills be shared across agents?

**A**: Yes, with fallback mechanism. Example: `youtube_toxic_filtering` uses Gemma as primary, Qwen as fallback for escalation. Skill can specify agent preference in YAML frontmatter.

### Q: What if a skill never reaches 90% fidelity?

**A**: Qwen generates variations. If variations also fail, skill remains in prototype/staged. 0102 investigates: Is task too complex? Are instructions unclear? Is agent not capable? Iterate until viable or abandon.

### Q: How do we prevent skills from conflicting?

**A**: Skills are scoped to specific tasks within specific modules. Dependency graph tracks relationships. If conflicts emerge, refactor skills or merge into single skill.

### Q: Can skills call other skills?

**A**: Yes, via composition. Skill instructions can reference: "After completing this task, route to `youtube_banter_response` skill for response generation."

### Q: Why does HoloIndex matter if skills are distributed across modules?

**A**: **HoloIndex makes location transparent for discovery**:

```bash
python holo_index.py --search "monitor unicode daemon errors"

# Returns (regardless of location):
# modules/communication/livechat/skills/unicode_daemon_monitor/SKILL.md
```

**The index enables search**. **The structure enables maintenance**. Best of both worlds.

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-10-20 | Initial protocol (dual systems architecture) | 0102 + User |
| 1.1 | 2025-10-20 | REVISED: Prototype-then-deploy architecture (modular production deployment) | 0102 + User |
| 1.2 | 2025-10-20 | CLARIFIED: `.claude/skills/` is 0102 testing environment only (via Claude Code), production in `modules/*/skills/` | 0102 + User |
| 1.3 | 2025-10-23 | ADDED: Micro Chain-of-Thought paradigm - skills as multi-step reasoning chains with Gemma validation at each step. Reference implementation: qwen_gitpush skill with WSP 15 MPS scoring. Updated "What Is a Skill?" definition to clarify skills are NOT monolithic prompts. | 0102 + User |
| 1.4 | 2026-02-07 | ADDED: Mandatory skill supply-chain scanner gate for promotion and runtime execution with fail-closed defaults and severity policy enforcement. | 0102 + User |
| 1.5 | 2026-07-29 | ADDED: Provider-neutral role Skillz exact schema, signed runtime model-binding separation, sealed use-time receipt validation, and no-authority boundary. | 0102 |

---

**Status**: ✅ ACTIVE
**Next Review**: After Phase 1 WRE skills deployed to production (qwen_gitpush baseline testing)
**Contact**: 0102 (Claude Code supervisor)

---

**Principle**: "The wardrobe tells the agents how to act. Skills are step-by-step reasoning chains. Gemma validates each step. Qwen thinks strategically. 0102 supervises."
