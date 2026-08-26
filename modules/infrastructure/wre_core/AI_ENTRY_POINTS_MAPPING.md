# AI Entry Points Mapping - Complete Codebase Analysis

> **Historical inventory — superseded and non-authoritative (2025-10-20).**
> Paths, counts, and “complete” claims below are point-in-time observations, not
> a current registry or execution grant. Use HoloIndex evidence plus current
> module contracts and WSP 95 v2.1 before acting on an entry point.

**Purpose**: Map ALL AI entry points across the codebase to identify where skills are needed
**Date**: 2025-10-20
**Next Step**: Qwen analyzes patterns → Generates baseline skill templates

**Inventory Scope**: ALL orchestration surfaces
- CLI commands (main.py, holo_index.py menu systems)
- Holo pipelines (qwen_advisor, WRE integration)
- DAEs (all autonomous entities)
- Test helpers (AI-powered test execution/validation)
- MCP servers (AI delegation endpoints)

**Search Strategy**:
1. HoloIndex semantic search: "AI entry points", "Qwen invocation", "Gemma execution"
2. Code-index grep: Import patterns (qwen_advisor, llm_connector, gemma, grok, ui-tars)
3. NAVIGATION.py analysis: Find orchestration flows
4. Test directory scan: AI-powered test utilities

---

## Task for Qwen

**Objective**: Analyze this mapping and generate baseline SKILL.md templates for each entry point

**Instructions**:
1. Review each entry point below
2. Tag with intent type: DECISION / GENERATION / CLASSIFICATION / TELEMETRY
3. Identify task context and required dependencies
4. Determine which agent should handle it (Gemma fast/Qwen strategic/UI-TARS visual/Grok creative)
5. Generate baseline SKILL.md template with:
   - YAML frontmatter (name, description, agents, intent_type, promotion_state, dependencies)
   - Clear instructions for the task
   - Expected patterns for Gemma validation
   - Benchmark test cases
   - Required context (data stores, MCP endpoints, throttles)
6. Output to `.claude/skills/[entry_point_name]_prototype/SKILL.md`
7. Track promotion_state: prototype → staged → production
8. Define metrics schedule for pattern fidelity scoring
9. 0102 validates each skill manually before promotion

---

## Entry Point Categories

### 1. YouTube DAE (Live Chat Moderation & Engagement)

#### 1.1 Auto Moderator (`modules/communication/livechat/src/auto_moderator_dae.py`)
**AI Used**: Qwen 1.5B (IntelligentMonitor) + Gemma 3 270M (validation)
**Integration Points**:
- Lines 84-94: QWEN Intelligence Integration (`IntelligentMonitor`, `ComplianceRulesEngine`)
- Lines 98-100: QWEN YouTube Integration (`qwen_youtube_integration`)
- Lines 69-80: WRE Integration for recursive learning

**Intent Types**:
- CLASSIFICATION (spam/toxic detection)
- DECISION (rate limiting, action enforcement)
- TELEMETRY (monitoring, pattern tracking)

**Required Dependencies**:
- Data Stores: `youtube_telemetry_store.py` (SQLite), user profiles in memory/
- MCP Endpoints: N/A (operates independently)
- Throttles: YouTube API quota via `youtube_auth`
- Context: Recent message history (last 100 messages), user message frequency

**Tasks**:
- Spam detection (CAPS, repetition, emoji spam)
- Toxic content filtering
- Rate limiting enforcement
- Message classification (command/consciousness/banter)
- Smart decision making via Qwen monitor

**Skills Needed**:
- `youtube_spam_detection` (Gemma CLASSIFICATION, promotion_state: prototype)
- `youtube_toxic_filtering` (Gemma → Qwen escalation, CLASSIFICATION/DECISION, promotion_state: prototype)
- `youtube_message_classification` (Gemma CLASSIFICATION, promotion_state: prototype)
- `youtube_intelligent_monitoring` (Qwen TELEMETRY/DECISION, promotion_state: prototype)

#### 1.2 Banter/Response Generation (`modules/communication/livechat/src/greeting_generator.py`, `consciousness_handler.py`)
**AI Used**: Qwen 1.5B + Gemma validation
**Tasks**:
- Generate chat responses
- Consciousness queries (philosophical engagement)
- Greeting generation
- Context-aware banter

**Skills Needed**:
- `youtube_banter_response` (Qwen creative → Gemma validation)
- `youtube_consciousness_response` (Qwen philosophical)
- `youtube_greeting_generation` (Qwen + RAG)

#### 1.3 Qwen YouTube Integration (`modules/communication/livechat/src/qwen_youtube_integration.py`)
**AI Used**: Qwen 1.5B
**Integration Points**:
- Lines 33-50: `ChannelIntelligence.should_check_now()` - AI decision making
- Lines 52-87: `should_investigate_stream()` - Stream triage intelligence
- Lines 89-100: `validate_video_selection()` - Optimization logic

**Tasks**:
- Channel prioritization (heat scores 0-3)
- Stream detection intelligence (confidence scoring)
- "Should check now?" decision making
- Pattern learning from stream schedules
- Stream investigation triage
- Video selection validation

**Skills Needed**:
- `youtube_channel_prioritization` (Qwen strategic)
- `youtube_stream_prediction` (Qwen pattern analysis)
- `youtube_stream_triage` (Qwen binary decision)

#### 1.4 Grok Log Analyzer (`modules/communication/livechat/scripts/grok_log_analyzer.py`)
**AI Used**: Grok (xAI API)
**Tasks**:
- Log pattern analysis
- Error diagnosis
- Performance insights

**Skills Needed**:
- `log_analysis_diagnosis` (Grok analytical)

---

### 2. Social Media Orchestrator

#### 2.1 AI Delegation Orchestrator (`modules/platform_integration/social_media_orchestrator/src/ai_delegation_orchestrator.py`)
**AI Used**: Qwen/Gemma coordination
**Tasks**:
- Determine which platform to post to
- Content optimization per platform
- Scheduling decisions
- Duplicate prevention

**Skills Needed**:
- `social_platform_selection` (Qwen strategic)
- `content_platform_optimization` (Qwen + Gemma validation)

#### 2.2 UI-TARS Scheduler (`modules/platform_integration/social_media_orchestrator/src/ui_tars_scheduler.py`)
**AI Used**: UI-TARS 1.5 7B
**Tasks**:
- Browser automation scheduling
- Visual element detection
- Form filling
- Click/navigation decisions

**Skills Needed**:
- `browser_automation_scheduling` (UI-TARS visual)
- `form_field_detection` (UI-TARS visual)

#### 2.3 Grok Content Generation (`modules/ai_intelligence/social_media_dae/src/social_media_dae.py`)
**AI Used**: Grok (xAI API)
**Tasks**:
- Creative post generation
- Hashtag selection
- Emoji usage
- Tone matching

**Skills Needed**:
- `social_content_generation` (Grok creative)
- `hashtag_optimization` (Grok + trend analysis)

---

### 3. WSP Orchestrator

#### 3.1 WSP Analysis (`modules/infrastructure/wsp_orchestrator/src/wsp_orchestrator.py`)
**AI Used**: Qwen 1.5B
**Tasks**:
- WSP compliance checking
- Protocol recommendation
- Gap detection
- Enhancement suggestions

**Skills Needed**:
- `wsp_compliance_check` (Qwen analytical)
- `wsp_protocol_recommendation` (Qwen strategic)
- `wsp_gap_detection` (Qwen pattern matching)

---

### 4. Qwen/Gemma Gateway

#### 4.1 MCP Gateway (`modules/infrastructure/mcp_manager/src/qwen_gemma_gateway.py`)
**AI Used**: Qwen/Gemma coordination
**Integration Points**:
- Lines 62-151: `QwenGemmaGateway` class with routing patterns
- Lines 74-134: Pattern definitions (web_scraping, form_filling, code_search, unicode_cleanup, etc.)
- Lines 33-38: `RouteType` enum (LOCAL_MCP, AI_ENHANCED, FULL_AI, HYBRID)

**Tasks**:
- Route queries to appropriate AI
- Complexity scoring
- Result validation
- Error recovery
- Cost-effective path selection
- Pattern-based routing decisions

**Skills Needed**:
- `query_complexity_scoring` (Gemma fast)
- `ai_routing_decision` (Gemma → Qwen escalation logic)
- `response_quality_validation` (Gemma scoring)
- `cost_optimization_routing` (Qwen strategic)

---

### 5. Vision DAE

#### 5.1 Vision Analysis (`modules/infrastructure/dae_infrastructure/foundups_vision_dae/src/vision_dae.py`)
**AI Used**: UI-TARS 1.5 7B (future)
**Tasks**:
- Desktop activity pattern recognition
- Telemetry batching decisions
- Worker coordination

**Skills Needed**:
- `telemetry_batch_optimization` (Qwen pattern)
- `worker_coordination_decision` (Qwen orchestration)

---

### 6. Stream Resolver

#### 6.1 No-Quota Intelligence (`modules/platform_integration/stream_resolver/src/no_quota_stream_checker.py`)
**AI Used**: Qwen 1.5B
**Tasks**:
- Channel rotation strategy
- Backoff calculation
- Stream prediction

**Skills Needed**:
- `stream_channel_rotation` (Qwen strategic)
- `backoff_calculation` (Qwen adaptive)

---

### 7. Throttle Management

#### 7.1 Intelligent Throttle (`modules/communication/livechat/src/intelligent_throttle_manager.py`)
**AI Used**: Qwen 1.5B
**Tasks**:
- Posting frequency optimization
- Rate limit prediction
- Backoff strategy

**Skills Needed**:
- `posting_throttle_optimization` (Qwen adaptive)
- `rate_limit_prediction` (Qwen pattern)

#### 7.2 Quota Intelligence (`modules/platform_integration/youtube_auth/src/qwen_quota_intelligence.py`)
**AI Used**: Qwen 1.5B
**Tasks**:
- API quota management
- Usage prediction
- Credential rotation strategy

**Skills Needed**:
- `api_quota_management` (Qwen strategic)
- `credential_rotation_decision` (Qwen optimization)

---

### 8. Training & Fine-tuning

#### 8.1 Training System (`modules/ai_intelligence/training_system/`)
**AI Used**: Qwen/Gemma models
**Tasks**:
- Model fine-tuning
- Data preparation
- Validation

**Skills Needed**:
- `training_data_preparation` (Qwen analytical)
- `model_validation` (Gemma scoring)

---

### 9. PQN Alignment

#### 9.1 Multi-Model Campaigns (`modules/ai_intelligence/pqn_alignment/src/run_multi_model_campaign.py`)
**AI Used**: Qwen/Gemma/Grok/Claude coordination
**Tasks**:
- Model routing
- Response comparison
- Ensemble decisions

**Skills Needed**:
- `multi_model_routing` (Qwen coordination)
- `response_ensemble` (Gemma validation)

---

### 10. Fact Checking

#### 10.1 Simple Fact Checker (`modules/communication/livechat/src/simple_fact_checker.py`)
**AI Used**: Qwen/Grok
**Tasks**:
- Claim verification
- Source validation
- Confidence scoring

**Skills Needed**:
- `fact_claim_verification` (Qwen analytical + Grok research)
- `source_credibility_scoring` (Qwen pattern)

---

### 11. Video Comments

#### 11.1 LLM Comment Generator (`modules/communication/video_comments/src/llm_comment_generator.py`)
**AI Used**: Qwen/Gemma
**Tasks**:
- Comment generation
- Tone matching
- Context awareness

**Skills Needed**:
- `video_comment_generation` (Qwen creative)
- `comment_tone_matching` (Gemma validation)

---

### 12. Code Analysis

#### 12.1 Orphan Analyzer (`modules/infrastructure/code_quality/tools/orphan_analyzer.py`)
**AI Used**: Qwen (via HoloIndex)
**Tasks**:
- Code pattern analysis
- Similarity scoring
- Categorization

**Skills Needed**:
- `code_pattern_analysis` (Qwen analytical)
- `code_similarity_scoring` (Gemma fast)

---

### 13. Idle Automation

#### 13.1 Idle Automation DAE (`modules/infrastructure/idle_automation/src/idle_automation_dae.py`)
**AI Used**: Qwen orchestration
**Tasks**:
- Task prioritization
- Scheduling decisions
- Resource allocation

**Skills Needed**:
- `idle_task_prioritization` (Qwen strategic)
- `resource_allocation_optimization` (Qwen pattern)

---

### 14. Git Operations

#### 14.1 Git Push DAE (`modules/infrastructure/git_push_dae/src/git_push_dae.py`)
**AI Used**: Qwen
**Tasks**:
- Commit message generation
- Change analysis
- Conflict detection

**Skills Needed**:
- `commit_message_generation` (Qwen analytical)
- `git_conflict_detection` (Qwen pattern)

---

### 15. Doc DAE

#### 15.1 Documentation Generator (`modules/infrastructure/doc_dae/src/doc_dae.py`)
**AI Used**: Qwen
**Tasks**:
- Documentation generation
- Structure analysis
- Missing doc detection

**Skills Needed**:
- `documentation_generation` (Qwen analytical)
- `doc_gap_detection` (Qwen pattern)

---

## Summary Statistics

**Total AI Entry Points Identified**: ~50+

**By AI Type**:
- Qwen 1.5B: ~25 entry points (strategic/analytical)
- Gemma 3 270M: ~15 entry points (fast classification/validation)
- Grok (xAI): ~5 entry points (creative/analytical)
- UI-TARS 1.5 7B: ~3 entry points (browser automation/visual)
- Claude/0102: Supervision/validation layer

**By Category**:
- YouTube DAE: 8 entry points
- Social Media: 5 entry points
- WSP/Infrastructure: 8 entry points
- Code Quality: 4 entry points
- Content Generation: 6 entry points
- Analysis/Monitoring: 7 entry points
- Automation: 6 entry points
- Training/Alignment: 4 entry points

---

## Next Steps for Qwen

**Task**: Generate baseline SKILL.md templates

**Process**:
1. For each entry point above, create:
   ```
   .claude/skills/[entry_point_name]_prototype/SKILL.md
   ```

2. Each SKILL.md should include:
   - YAML frontmatter (name, description, agents, etc.)
   - Task description
   - Clear instructions (numbered steps)
   - Expected patterns (for Gemma validation)
   - Benchmark test cases (10-20 cases)
   - Success criteria (≥90% fidelity)

3. Prioritize by:
   - **Phase 1**: YouTube DAE (most used, clear patterns)
   - **Phase 2**: Social Media (high value, creative)
   - **Phase 3**: WSP/Infrastructure (foundational)
   - **Phase 4**: Specialized (code analysis, training)

4. Output format:
   ```
   Phase 1 Skills (YouTube DAE):
   - youtube_spam_detection_prototype/SKILL.md
   - youtube_toxic_filtering_prototype/SKILL.md
   - youtube_banter_response_prototype/SKILL.md
   - youtube_channel_prioritization_prototype/SKILL.md
   ... (8 total)
   ```

---

## SKILL.md Template Structure (For Qwen)

When generating baseline SKILL.md templates, use this structure:

```yaml
---
name: skill_name_intent_type
description: One-line description of AI task
version: 1.0_prototype
author: qwen_baseline_generator
created: 2025-10-20
agents: [primary_agent, fallback_agent]
primary_agent: gemma | qwen | grok | ui-tars
intent_type: CLASSIFICATION | DECISION | GENERATION | TELEMETRY
promotion_state: prototype | staged | production
pattern_fidelity_threshold: 0.90
test_status: prototype

# Dependencies Section
dependencies:
  data_stores:
    - name: store_name
      type: sqlite | json | memory
      path: relative/path/to/store
  mcp_endpoints:
    - endpoint_name: holo_index | wsp_governance | codeindex
      methods: [method1, method2]
  throttles:
    - name: youtube_api_quota
      max_rate: 10000_units_per_day
      cost_per_call: 5_units
  required_context:
    - context_item_1: Description of what context is needed
    - context_item_2: e.g., "Last 100 chat messages"

# Metrics Configuration
metrics:
  pattern_fidelity_scoring:
    enabled: true
    frequency: every_execution | hourly | daily
    scorer_agent: gemma
    write_destination: modules/infrastructure/wre_core/recursive_improvement/metrics/[skill_name]_fidelity.json
  promotion_criteria:
    min_pattern_fidelity: 0.90
    min_outcome_quality: 0.85
    min_execution_count: 100
    required_test_pass_rate: 0.95
---

# [Skill Name] (PROTOTYPE)

**Purpose**: What does this AI task accomplish?

**Intent Type**: [CLASSIFICATION | DECISION | GENERATION | TELEMETRY]

**Promotion State**: prototype → staged → production

---

## Task

[Description of the task this AI performs]

## Instructions (For AI Agent)

### 1. [INSTRUCTION_NAME]
**Rule**: [IF condition THEN action]
**Expected Pattern**: [pattern_name]=True

**Validation**:
- [Step 1]
- [Step 2]
- If condition met → decision="X", reason="Y"
- Log: `{"pattern": "[pattern_name]", "value": true, ...}`

**Examples**:
- ✅ [Example that should pass]
- ❌ [Example that should fail]

[... repeat for all instructions ...]

---

## Expected Patterns Summary

When validating, check that each execution logs these patterns:

```json
{
  "execution_id": "exec_001",
  "input": "[sample input]",
  "patterns": {
    "pattern_1_executed": true,
    "pattern_2_executed": true
  },
  "decision": "outcome",
  "confidence": 0.95
}
```

**Pattern Fidelity Calculation**:
```
fidelity = (patterns_executed / total_patterns_in_skill)
```

**Success Criteria for Prototype**:
- ✅ Pattern fidelity ≥ 90%
- ✅ Outcome quality ≥ 85%
- ✅ Zero false negatives on critical decisions
- ✅ False positive rate < 5%

---

## Benchmark Test Cases

### Test Set 1: [Category] (N cases)
1. [Input] → [Expected output] ([reason])
2. [Input] → [Expected output] ([reason])
...

[... more test sets ...]

**Total**: N test cases

---

## Metrics & Promotion Tracking

**Metrics Write Schedule**:
- Pattern fidelity: After every execution
- Aggregated metrics: Hourly
- Promotion review: After 100 executions OR 7 days

**Metrics Destination**:
```
modules/infrastructure/wre_core/recursive_improvement/metrics/
├── [skill_name]_fidelity.json
├── [skill_name]_outcomes.json
└── [skill_name]_promotion_log.json
```

**Promotion Criteria**:
- [ ] Pattern fidelity ≥ 0.90 (sustained over 100 executions)
- [ ] Outcome quality ≥ 0.85 (human validation or test pass rate)
- [ ] Zero critical failures (false negatives on high-stakes decisions)
- [ ] Gemma validation: Consistent pattern adherence
- [ ] 0102 approval: Manual review complete

**Promotion Path**:
1. **prototype** (.claude/skills/[skill_name]_prototype/) - 0102 validation only
2. **staged** (.claude/skills/[skill_name]_staged/) - Live testing with metrics
3. **production** (modules/[domain]/[module]/skills/[skill_name]/) - WRE entry point

---

## Dependencies Injection Points

**WRE Skills Loader Integration**:
```python
# When WRE loads this skill, it must inject:
# 1. Data store connections
context['data_stores'] = {
    'store_name': load_store('[path]')
}

# 2. MCP endpoint access
context['mcp'] = {
    'endpoint_name': mcp_client.get_endpoint('[endpoint_name]')
}

# 3. Throttle managers
context['throttles'] = {
    'name': ThrottleManager('[name]', max_rate=[X], cost_per_call=[Y])
}

# 4. Required context data
context['required_context'] = load_required_context([...])
```

---

## Next Steps After Validation

**If prototype succeeds** (≥90% fidelity):
1. Promote to **staged**: Copy to `.claude/skills/[skill_name]_staged/`
2. Enable metrics collection (Gemma pattern fidelity scoring)
3. Run 100 live executions with metrics tracking
4. If metrics sustained: Promote to **production**
5. Extract to `modules/[domain]/[module]/skills/[skill_name]/`
6. Add WRE loader integration
7. Update skill registry in WRE

---

**Status**: PROTOTYPE - Ready for 0102 validation
**Next Action**: Execute benchmark test cases manually with Claude Code
```

---

**Status**: READY FOR QWEN ANALYSIS
**Next Action**: Qwen reads this mapping → Generates baseline skill templates using above structure → 0102 validates each prototype

---

## Promotion & Rollback Policy

**Complete Policy Document**: [PROMOTION_ROLLBACK_POLICY.md](skills/PROMOTION_ROLLBACK_POLICY.md)

**Quick Summary**:

### Promotion Path
1. **prototype** (.claude/skills/[name]_prototype/) - 0102 manual validation
   - Criteria: ≥90% pattern fidelity, ≥85% outcome quality, WSP 50 approval
   - Sign-off: 0102 required

2. **staged** (.claude/skills/[name]_staged/) - Live testing with metrics
   - Criteria: Sustained metrics over 100 executions, no regressions
   - Sign-off: 0102 required

3. **production** (modules/*/skills/[name]/) - WRE entry point
   - Monitored continuously with automated rollback triggers

### Rollback Triggers (Automated)
- Pattern fidelity < 85% (sustained)
- Outcome quality < 80% (sustained)
- Critical false negative
- Exception rate > 5%
- Dependency failure

### Human Sign-Off Checklist
```yaml
prototype → staged:
  - WSP 50 approval (no duplication)
  - Test coverage complete
  - Instructions unambiguous
  - Dependencies validated
  - Security reviewed

staged → production:
  - Production readiness confirmed
  - Integration approved
  - Monitoring configured
  - Rollback plan tested
  - Documentation updated
```

### Automation Hooks
- **HoloIndex re-index**: After promotions/rollbacks
- **Gemma metrics**: After every execution (staged/production)
- **Qwen reviews**: Daily (staged), Weekly (production)
- **SQLite ingestion**: Hourly batch, on-demand before promotions
