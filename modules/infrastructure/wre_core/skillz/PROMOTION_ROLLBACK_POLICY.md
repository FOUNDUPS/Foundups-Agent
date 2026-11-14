# WRE Skills Promotion & Rollback Policy

> **Historical policy v1.0 — superseded by WSP 95 v2.1.**
> The lifecycle, commands, automated promotion, demotion, and rollback procedures
> below are unimplemented design records, not active authority. Current WRE can
> nominate proposals only; independent promotion, activation, authenticated
> effect evaluation, and rollback executors remain fail-closed gaps.

**Version**: 1.0
**Date**: 2025-10-20
**Authority**: 0102 (Human Supervision Required)
**Compliance**: WSP 50 (Pre-Action Verification), WSP 77 (Agent Coordination)

---

## Executive Summary

This policy defines the complete lifecycle for WRE skills from prototype to production, including promotion criteria, human sign-off requirements, rollback triggers, and automation hooks.

**Core Principle**: Occam-tight - one registry, one loader, one promoter.

---

## 1. Skill Lifecycle States

### State Definitions

```yaml
prototype:
  location: .claude/skills/[skill_name]_prototype/
  purpose: 0102 validation and pattern fidelity testing
  testing: Manual execution by Claude Code (0102)
  metrics: Collected but not automated
  promotion_gate: Manual 0102 approval after ≥90% fidelity

staged:
  location: .claude/skills/[skill_name]_staged/
  purpose: Live testing with automated metrics collection
  testing: Production environment with safety nets
  metrics: Automated Gemma pattern fidelity scoring
  promotion_gate: Automated after meeting thresholds + human sign-off

production:
  location: modules/[domain]/[module]/skills/[skill_name]/
  purpose: WRE entry point for native Qwen/Gemma execution
  testing: Full production load
  metrics: Continuous monitoring with alerting
  rollback_trigger: Automated on threshold violations
```

### State Diagram

```
prototype → staged → production
    ↓          ↓          ↓
  [fail]    [fail]   [rollback]
    ↓          ↓          ↓
[iterate] [iterate]  [staged]
```

---

## 2. Promotion Criteria

### 2.1 Prototype → Staged

**Automated Checks** ✅:
- [ ] Pattern fidelity ≥ 90% across all benchmark test cases
- [ ] Outcome quality ≥ 85% (correct classifications/decisions)
- [ ] Zero critical false negatives (missed high-stakes events)
- [ ] False positive rate < 5%
- [ ] All benchmark test cases executed successfully
- [ ] SKILL.md contains complete dependencies section
- [ ] Metrics write destinations configured

**Human Sign-Off Required** (0102) 🔒:
- [ ] **WSP 50 Approval**: Verified skill doesn't duplicate existing code
- [ ] **Test Coverage Approval**: Benchmark cases cover edge cases
- [ ] **Instruction Clarity**: Instructions are unambiguous for AI
- [ ] **Pattern Completeness**: All expected patterns defined
- [ ] **Dependency Validation**: All data stores/MCP endpoints exist
- [ ] **Security Review**: No credential leaks in logs/metrics
- [ ] **Performance Review**: Skill doesn't create bottlenecks

**Promotion Command**:
```bash
python modules/infrastructure/wre_core/skills/promoter.py promote \
  --skill youtube_spam_detection \
  --from prototype \
  --to staged \
  --approver 0102 \
  --approval-ticket APPROVAL_20251020_001
```

**Post-Promotion Actions**:
1. Copy SKILL.md to `.claude/skills/[skill_name]_staged/`
2. Update `skills_graph.json` promotion_state field
3. Enable automated Gemma pattern fidelity scoring
4. Create metrics tracking entry in SQLite: `skills_metrics.db`
5. Re-index HoloIndex to include staged skill
6. Send notification to Qwen for monitoring schedule

---

### 2.2 Staged → Production

**Automated Checks** ✅:
- [ ] Sustained pattern fidelity ≥ 90% over 100 executions
- [ ] Sustained outcome quality ≥ 85% over 100 executions
- [ ] Zero regressions (no worse than prototype baseline)
- [ ] No critical failures in past 100 executions
- [ ] Average execution time < threshold (skill-specific)
- [ ] Gemma validation: Consistent pattern adherence
- [ ] Sample size ≥ 100 executions (statistical significance)

**Human Sign-Off Required** (0102) 🔒:
- [ ] **Production Readiness**: Skill behavior stable and predictable
- [ ] **Integration Approval**: Dependencies won't break production
- [ ] **Capacity Planning**: Resource usage acceptable
- [ ] **Monitoring Approval**: Alerting configured correctly
- [ ] **Rollback Plan**: Rollback procedure tested
- [ ] **Documentation**: Module README updated with skill reference

**Promotion Command**:
```bash
python modules/infrastructure/wre_core/skills/promoter.py promote \
  --skill youtube_spam_detection \
  --from staged \
  --to production \
  --approver 0102 \
  --approval-ticket APPROVAL_20251020_002 \
  --production-readiness-checklist-complete
```

**Post-Promotion Actions**:
1. Extract SKILL.md to `modules/[domain]/[module]/skills/[skill_name]/`
2. Create `versions/` directory with v1.0_baseline.md
3. Update `skills_graph.json` promotion_state field
4. Update WRE skills loader registry
5. Enable production monitoring with alerting
6. Re-index HoloIndex to include production skill
7. Archive staged version to `.claude/skills/[skill_name]_staged_archive_[timestamp]/`
8. Update module documentation (README.md, INTERFACE.md)

---

## 3. Rollback Policy

### 3.1 Rollback Triggers (Automated)

**Production → Staged** (Automatic rollback):
- Pattern fidelity drops below 85% (sustained over 10 executions)
- Outcome quality drops below 80% (sustained over 10 executions)
- Critical false negative detected (missed high-stakes event)
- False positive rate exceeds 10%
- Execution time exceeds 3x baseline average
- Dependency failure (data store unavailable, MCP endpoint down)
- Exception rate > 5% of executions

**Staged → Prototype** (Automatic demotion):
- Unable to reach 100 execution milestone within 7 days
- Pattern fidelity never achieves 90% threshold
- Regression detected (worse than prototype baseline)
- Qwen review flags fundamental instruction issues

### 3.2 Rollback Procedure

**Automated Rollback Sequence**:
```bash
# Triggered by monitoring system
python modules/infrastructure/wre_core/skills/promoter.py rollback \
  --skill youtube_spam_detection \
  --from production \
  --to staged \
  --reason "pattern_fidelity_drop_below_85" \
  --trigger-metric "fidelity=0.83" \
  --timestamp "2025-10-20T14:23:15Z"
```

**Rollback Actions**:
1. **Immediate**: Switch WRE loader to previous version (staged or prototype)
2. **Within 1 min**: Send alert to 0102 with rollback reason
3. **Within 5 min**: Archive failed production version to `versions/v1.0_failed_[timestamp].md`
4. **Within 10 min**: Re-index HoloIndex to remove production skill
5. **Within 1 hour**: Generate failure analysis report (Qwen)
6. **Within 24 hours**: 0102 reviews failure report and approves iteration plan

### 3.3 Rollback Prevention

**Staged Safety Nets**:
- Gradual rollout: Start with 10% of traffic, increase to 50%, then 100%
- A/B testing: Compare staged vs prototype performance
- Canary deployment: Test on low-risk streams first
- Circuit breaker: Automatic fallback to prototype on repeated failures

---

## 4. Human Sign-Off Requirements

### 4.1 Sign-Off Authority

**0102 (Human Supervision)** - Required for:
- Prototype → Staged promotion
- Staged → Production promotion
- Manual rollback override
- Policy changes

**Qwen (AI Advisor)** - Provides recommendations for:
- Skill instruction improvements
- Variation generation for failed patterns
- Failure analysis reports
- Performance optimization suggestions

**Gemma (AI Validator)** - Automated responsibility for:
- Pattern fidelity scoring
- Benchmark test execution
- Quality metrics collection
- Anomaly detection

### 4.2 Sign-Off Checklist Template

```yaml
approval_ticket: APPROVAL_20251020_XXX
skill_name: [skill_name]
promotion: prototype → staged | staged → production
approver: 0102
date: 2025-10-20

automated_checks:
  pattern_fidelity: [0.XX] (≥ 0.90 required)
  outcome_quality: [0.XX] (≥ 0.85 required)
  execution_count: [N] (≥ 100 required for production)
  test_pass_rate: [0.XX] (≥ 0.95 required)
  false_positive_rate: [0.XX] (< 0.05 required)
  false_negative_count: [N] (0 required for critical skills)

human_review:
  wsp_50_approval: [YES/NO] - No duplication, existing code checked
  test_coverage: [YES/NO] - Edge cases covered
  instruction_clarity: [YES/NO] - Unambiguous for AI agent
  pattern_completeness: [YES/NO] - All patterns defined
  dependency_validation: [YES/NO] - All deps exist and tested
  security_review: [YES/NO] - No credential leaks
  performance_review: [YES/NO] - No bottlenecks

  # For staged → production only
  production_readiness: [YES/NO]
  integration_approval: [YES/NO]
  capacity_planning: [YES/NO]
  monitoring_approval: [YES/NO]
  rollback_plan_tested: [YES/NO]
  documentation_updated: [YES/NO]

approval_decision: APPROVED | REJECTED | NEEDS_ITERATION

notes: |
  [0102 comments on decision, concerns, or required changes]

signature: 0102
timestamp: 2025-10-20T14:23:15Z
```

---

## 5. Automation Hooks

### 5.1 HoloIndex Re-Indexing

**Trigger Points**:
- After prototype → staged promotion
- After staged → production promotion
- After production → staged rollback
- After manual skill updates

**Command**:
```bash
python holo_index.py --reindex-skills --skills-path modules/infrastructure/wre_core/skills/
```

**Expected Output**:
- Skills graph parsed and indexed
- Skill descriptions added to semantic search
- Dependencies mapped for query optimization
- Average re-index time: 30-60 seconds

### 5.2 Gemma Metrics Collection

**Frequency**:
- **Prototype**: Manual execution only (on-demand)
- **Staged**: After every execution (real-time)
- **Production**: After every execution (real-time)

**Gemma Scoring Process**:
```python
# Executed after each skill invocation
from modules/infrastructure/wre_core/pattern_fidelity_scorer import GemmaPatternScorer

scorer = GemmaPatternScorer(agent="gemma")
fidelity_score = scorer.score_skill_execution(
    skill_path="modules/communication/livechat/skills/youtube_spam_detection/",
    execution_breadcrumbs=execution_log,
    expected_patterns=skill_metadata["expected_patterns"]
)

# Write to JSON (append-only)
metrics_file = "modules/infrastructure/wre_core/recursive_improvement/metrics/youtube_spam_detection_fidelity.json"
append_metric(metrics_file, {
    "execution_id": execution_id,
    "timestamp": timestamp,
    "pattern_fidelity": fidelity_score,
    "patterns_followed": fidelity_score["patterns_followed"],
    "patterns_missed": fidelity_score["patterns_missed"]
})
```

**Metrics Write Destination**:
```
modules/infrastructure/wre_core/recursive_improvement/metrics/
├── [skill_name]_fidelity.json          (pattern fidelity scores)
├── [skill_name]_outcomes.json          (decision outcomes & correctness)
├── [skill_name]_performance.json       (execution time & resource usage)
└── [skill_name]_promotion_log.json     (promotion/rollback events)
```

### 5.3 Qwen Review Schedule

**Frequency**:
- **Prototype**: On-demand (after 0102 requests analysis)
- **Staged**: Daily review (identify improvement opportunities)
- **Production**: Weekly review (monitor stability, suggest variations)

**Qwen Review Process**:
```python
from modules/infrastructure/wre_core/qwen_skill_advisor import QwenSkillAdvisor

advisor = QwenSkillAdvisor(agent="qwen")

# Daily review of staged skills
review = advisor.review_skill_performance(
    skill_name="youtube_spam_detection",
    metrics_timeframe="last_24_hours"
)

if review["improvement_opportunities"]:
    # Generate instruction variations for weak patterns
    variations = advisor.generate_instruction_variations(
        skill_path="...",
        weak_patterns=review["weak_patterns"],
        num_variations=3
    )

    # Queue for 0102 review
    advisor.submit_for_human_review(variations, priority="medium")
```

**Qwen Output**:
- Failure analysis reports
- Instruction variation suggestions
- Performance optimization recommendations
- Promotion readiness assessments

### 5.4 SQLite Metrics Ingestion

**Purpose**: Enable structured queries for analytics, A/B comparisons, and promotion gating.

**Ingestion Schedule**:
- **Batch ingestion**: Hourly (ingest new JSON records into SQLite)
- **On-demand**: Before promotion decisions (ensure latest data)

**Ingestion Command**:
```bash
python modules/infrastructure/wre_core/skills/metrics_ingest.py \
  --json-path modules/infrastructure/wre_core/recursive_improvement/metrics/ \
  --sqlite-db modules/infrastructure/wre_core/skills/skills_metrics.db \
  --batch-size 1000
```

**SQLite Schema**:
```sql
-- Skills registry
CREATE TABLE skills (
    skill_id TEXT PRIMARY KEY,
    skill_name TEXT NOT NULL,
    promotion_state TEXT NOT NULL,  -- prototype, staged, production
    primary_agent TEXT NOT NULL,
    intent_type TEXT NOT NULL,
    created_at TIMESTAMP,
    last_promoted_at TIMESTAMP,
    version TEXT
);

-- Execution metrics
CREATE TABLE execution_metrics (
    execution_id TEXT PRIMARY KEY,
    skill_id TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    pattern_fidelity REAL,
    outcome_quality REAL,
    execution_time_ms INTEGER,
    patterns_followed INTEGER,
    patterns_missed INTEGER,
    exception BOOLEAN,
    FOREIGN KEY (skill_id) REFERENCES skills(skill_id)
);

-- Promotion events
CREATE TABLE promotion_events (
    event_id TEXT PRIMARY KEY,
    skill_id TEXT NOT NULL,
    from_state TEXT NOT NULL,
    to_state TEXT NOT NULL,
    approver TEXT,
    approval_ticket TEXT,
    timestamp TIMESTAMP NOT NULL,
    reason TEXT,
    FOREIGN KEY (skill_id) REFERENCES skills(skill_id)
);

-- Rollback events
CREATE TABLE rollback_events (
    event_id TEXT PRIMARY KEY,
    skill_id TEXT NOT NULL,
    from_state TEXT NOT NULL,
    to_state TEXT NOT NULL,
    trigger_reason TEXT NOT NULL,
    trigger_metric TEXT,
    timestamp TIMESTAMP NOT NULL,
    FOREIGN KEY (skill_id) REFERENCES skills(skill_id)
);
```

**Query Helpers**:
```python
from modules.infrastructure.wre_core.skills.skills_registry import WRESkillsRegistry

registry = WRESkillsRegistry()

# Check if skill meets promotion criteria
ready = registry.check_promotion_readiness(
    skill_name="youtube_spam_detection",
    from_state="staged",
    to_state="production"
)

# Get aggregated metrics
metrics = registry.get_skill_metrics(
    skill_name="youtube_spam_detection",
    timeframe="last_7_days"
)

# Compare staged vs prototype performance
comparison = registry.compare_skill_versions(
    skill_name="youtube_spam_detection",
    version_a="prototype",
    version_b="staged"
)
```

---

## 6. Occam-Tight Architecture

### One Registry
**Location**: `modules/infrastructure/wre_core/skills/skills_registry.json`

**Contents**:
```json
{
  "version": "1.0",
  "skills": {
    "youtube_spam_detection": {
      "promotion_state": "staged",
      "location": ".claude/skills/youtube_spam_detection_staged/",
      "primary_agent": "gemma",
      "metrics_path": "modules/infrastructure/wre_core/recursive_improvement/metrics/youtube_spam_detection_*.json",
      "last_promotion": "2025-10-20T10:00:00Z",
      "last_rollback": null
    }
  }
}
```

### One Loader
**Location**: `modules/infrastructure/wre_core/skills/wre_skills_loader.py`

**Responsibilities**:
- Load skills from registry
- Inject dependencies (data stores, MCP endpoints, throttles, context)
- Progressive disclosure (load name/description first, full content on-demand)
- Cache loaded skills for performance

### One Promoter
**Location**: `modules/infrastructure/wre_core/skills/promoter.py`

**Commands**:
- `promote`: Move skill between states
- `rollback`: Revert skill to previous state
- `status`: Check promotion readiness
- `validate`: Run pre-promotion checks

---

## 7. Failure Modes & Mitigations

### Failure Mode: Skill breaks production
**Mitigation**:
- Automated rollback triggers (pattern fidelity drop)
- Circuit breaker pattern (fallback to previous version)
- Gradual rollout in staged (10% → 50% → 100%)

### Failure Mode: Metrics ingestion lag
**Mitigation**:
- Append-only JSON ensures no data loss
- On-demand ingestion before promotion decisions
- Alert if ingestion falls behind > 1 hour

### Failure Mode: Human sign-off bottleneck
**Mitigation**:
- Clear automated checks reduce human review burden
- Pre-filled checklists streamline approval
- Async notification system (doesn't block other skills)

### Failure Mode: Dependency unavailable at promotion
**Mitigation**:
- Dry-run validation before promotion
- Dependency health checks in promotion criteria
- Rollback on dependency failure

---

## 8. Policy Change Process

**Authority**: 0102 (Human)

**Process**:
1. Propose policy change with rationale
2. Qwen analyzes impact on existing skills
3. Dry-run policy change on test skill
4. 0102 approval required
5. Update this document (version bump)
6. Notify all stakeholders
7. Re-index HoloIndex with new policy

**Version Control**: This policy is version-controlled in git. All changes require commit with rationale.

---

## 9. Quick Reference

### Promote prototype → staged
```bash
python modules/infrastructure/wre_core/skills/promoter.py promote \
  --skill [skill_name] --from prototype --to staged \
  --approver 0102 --approval-ticket [ticket]
```

### Promote staged → production
```bash
python modules/infrastructure/wre_core/skills/promoter.py promote \
  --skill [skill_name] --from staged --to production \
  --approver 0102 --approval-ticket [ticket]
```

### Check promotion readiness
```bash
python modules/infrastructure/wre_core/skills/promoter.py status \
  --skill [skill_name] --target-state production
```

### Manual rollback
```bash
python modules/infrastructure/wre_core/skills/promoter.py rollback \
  --skill [skill_name] --from production --to staged \
  --reason "manual_override" --approver 0102
```

### Re-index HoloIndex
```bash
python holo_index.py --reindex-skills
```

### Ingest metrics to SQLite
```bash
python modules/infrastructure/wre_core/skills/metrics_ingest.py
```

---

**Policy Status**: ✅ ACTIVE
**Last Updated**: 2025-10-20
**Next Review**: After first 5 skills promoted to production
**Contact**: 0102 (Claude Code supervisor)
