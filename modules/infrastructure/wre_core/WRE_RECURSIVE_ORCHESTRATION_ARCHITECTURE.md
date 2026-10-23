# WRE Recursive Skills Orchestration: First Principles Architecture

> **Historical WSP 96-era design — superseded and non-authoritative.** Automatic
> A/B selection, promotion, production mutation, and efficiency claims below are
> unimplemented design records. Current authority is WSP 95 v2.1 plus the root
> WRE `README.md`, `INTERFACE.md`, and `ROADMAP.md`.

**Date**: 2025-10-23
**Architect**: 0102
**Status**: ARCHITECTURAL DESIGN - Deep Think Complete
**Authority**: User Specification + WSP 77 + WSP 96

---

## Executive Summary: The Typewriter Ball Analogy

**IBM Selectric Typewriter Ball** = **Wardrobe Skills System**

```
Physical Typewriter:
├── Typeball (interchangeable) = Skills (Qwen/Gemma execute different patterns)
├── Wiring (mechanism) = WRE Orchestrator (triggers correct skill)
├── Paper feed (feedback) = Gemma Libido Monitor (validates thought patterns)
└── Operator (decision) = HoloDAE + 0102 (when to type what)

Digital System:
├── Skills (270M param Gemma patterns) = Typewriter balls
├── WRE Core (skill loader/router) = Mechanical wiring
├── Gemma Libido Monitor (pattern frequency) = Paper feed sensor
├── HoloDAE (periodic checker) = Operator deciding what to type
└── DAEmons (execution targets) = The document being typed
```

**Key Insight**: Gemma (270M) is NOT doing heavy thinking - it's **pattern matching** (like typewriter ball positions). Qwen (1.5B-32B) does strategic thinking. The **wiring** (WRE) determines WHEN to switch balls.

---

## 1. First Principles: The Three-Layer Consciousness

### Layer 1: Gemma Libido Monitor (The Pattern Frequency Sensor)

**Analogy**: The paper feed mechanism that senses "too much ink here, move on"

**Purpose**: Monitors Qwen's thought pattern frequency to prevent:
- **Too much thinking** (analysis paralysis, token waste)
- **Too little thinking** (hasty decisions, missed edge cases)
- **Wrong pattern** (using classification skill for generation task)

**Architecture**:
```python
class GemmaLibidoMonitor:
    """
    Libido = "Pattern activation frequency"
    Monitors Qwen thought patterns like paper feed sensor
    270M parameters = Fast binary decisions (<10ms)
    """

    def __init__(self):
        self.pattern_history = deque(maxlen=100)  # Last 100 thought patterns
        self.frequency_threshold = {
            "git_commit_analysis": (2, 5),  # Min 2, Max 5 per session
            "wsp_compliance_check": (1, 10),  # Min 1, Max 10
            "code_generation": (0, 3),  # Rare, max 3
        }

    def monitor_pattern(self, qwen_action: str, skill_name: str) -> LibidoSignal:
        """
        Monitors if Qwen is thinking too much or too little
        Returns: CONTINUE | THROTTLE | ESCALATE | SWITCH_SKILL
        """
        count = sum(1 for p in self.pattern_history if p["skill"] == skill_name)
        min_threshold, max_threshold = self.frequency_threshold.get(skill_name, (0, 5))

        if count < min_threshold:
            return LibidoSignal.ESCALATE  # Need more thinking
        elif count > max_threshold:
            return LibidoSignal.THROTTLE  # Too much thinking, move on
        else:
            return LibidoSignal.CONTINUE  # Just right

    def validate_skill_fidelity(self, qwen_output: str, skill_instructions: str) -> float:
        """
        Gemma binary classification: Did Qwen follow skill instructions?
        Returns: 0.0-1.0 pattern fidelity score
        """
        # Gemma 270M does fast pattern matching
        return self.gemma_engine.classify_pattern_match(qwen_output, skill_instructions)
```

**Key Properties**:
- **Fast**: <10ms per check (Gemma 270M)
- **Binary**: Did Qwen follow pattern? (Yes/No)
- **Frequency**: Tracks pattern repetition (libido)
- **Adaptive**: Learns optimal thresholds via WSP 78 telemetry

---

### Layer 2: Wardrobe Skills (The Typewriter Balls)

**Analogy**: Interchangeable typewriter balls with different character sets

**Purpose**: Discrete, task-specific instruction sets for Qwen/Gemma

**Architecture**:
```yaml
Skill Structure (WSP 96):
  name: qwen_gitpush_analyzer
  agents: [qwen-1.5b, gemma-270m]
  intent_type: DECISION

  instructions:
    - Step 1: Analyze git diff (Qwen strategic analysis)
    - Step 2: Calculate WSP 15 MPS score (custom scoring)
    - Step 3: Generate semantic commit message (Qwen generation)
    - Step 4: Decide if should push (threshold check)

  gemma_validation:
    - Check: Did Qwen analyze files changed?
    - Check: Does commit message match diff content?
    - Check: Is MPS score calculated correctly?

  libido_thresholds:
    min_frequency: 1  # At least once per system check
    max_frequency: 5  # Don't spam git pushes

  promotion_state: prototype  # 0102 testing
```

**Key Innovation**: Skills are **trainable weights** that evolve:
- Pattern fidelity < 90% → Qwen generates variation
- A/B test variations → Select best performer
- Update skill instructions = "gradient descent" for prompts

---

### Layer 3: WRE Core (The Mechanical Wiring)

**Analogy**: The mechanism that selects and positions the correct typewriter ball

**Purpose**: Recursive orchestrator that:
1. **Loads skills** from modules/*/skills/
2. **Routes triggers** from HoloDAE → Correct skill → DAE
3. **Monitors patterns** via Gemma libido
4. **Learns recursively** via pattern fidelity scoring

**Architecture**:
```python
class WRECore:
    """
    The Wiring: Routes triggers to skills to DAEs
    Recursively monitors and improves skill performance
    """

    def __init__(self, repo_root: Path):
        self.skill_registry = SkillRegistry(repo_root)  # Discovers all skills
        self.libido_monitor = GemmaLibidoMonitor()  # Pattern frequency sensor
        self.pattern_memory = PatternMemory()  # Stores execution history
        self.qwen = QwenInferenceEngine()  # Strategic thinker
        self.gemma = GemmaPatternEngine()  # Fast validator

    async def trigger_skill(self, trigger: TriggerEvent) -> SkillResult:
        """
        Main entry point: HoloDAE or DAE triggers a skill
        """
        # 1. Select correct skill for trigger
        skill = self.skill_registry.match_trigger(trigger)

        # 2. Check libido: Should we execute this pattern now?
        libido_signal = self.libido_monitor.should_execute(skill.name)

        if libido_signal == LibidoSignal.THROTTLE:
            return SkillResult(status="THROTTLED", reason="Pattern frequency too high")

        # 3. Execute skill (Qwen follows instructions)
        qwen_output = await self.execute_skill_with_qwen(skill, trigger.context)

        # 4. Validate with Gemma (pattern fidelity)
        fidelity_score = self.libido_monitor.validate_skill_fidelity(
            qwen_output, skill.instructions
        )

        # 5. Record pattern for libido monitoring
        self.libido_monitor.record_pattern(skill.name, fidelity_score)

        # 6. Recursive improvement: If fidelity < 90%, trigger skill evolution
        if fidelity_score < 0.90:
            await self.evolve_skill(skill, qwen_output, trigger.context)

        return SkillResult(
            status="COMPLETED",
            output=qwen_output,
            fidelity=fidelity_score
        )

    async def evolve_skill(self, skill: Skill, failed_output: str, context: dict):
        """
        Recursive self-improvement when pattern fidelity < 90%
        """
        # Qwen reflects on why it failed
        reflection = self.qwen.reflect_on_failure(skill, failed_output, context)

        # Generate improved skill variation
        improved_skill = self.qwen.generate_skill_variation(skill, reflection)

        # A/B test: Run both versions
        original_results = await self.test_skill_batch(skill)
        improved_results = await self.test_skill_batch(improved_skill)

        # Statistical significance test
        if improved_results.fidelity > original_results.fidelity + 0.05:
            # Promote improved version
            self.skill_registry.update_skill(improved_skill)
            print(f"[WRE-EVOLUTION] Skill {skill.name} improved: {original_results.fidelity:.2f} → {improved_results.fidelity:.2f}")
```

---

## 2. The Trigger Chain: HoloDAE → Skill → DAE

**Complete Flow**:
```yaml
Step 1: HoloDAE Periodic System Check (every 5-10 min)
  ├── Check: Git has uncommitted changes?
  ├── Check: DAEs healthy?
  ├── Check: WSP violations?
  └── Trigger: If condition met → Fire TriggerEvent

Step 2: WRE Core Receives Trigger
  ├── Load: Skill from registry (qwen_gitpush_analyzer)
  ├── Validate: Libido check (not too frequent)
  ├── Execute: Qwen follows skill instructions
  └── Monitor: Gemma validates pattern fidelity

Step 3: Skill Execution (Qwen + Gemma Coordination)
  ├── Qwen: Analyze git diff (strategic analysis)
  ├── Gemma: Validate analysis followed skill pattern
  ├── Qwen: Calculate WSP 15 MPS score
  ├── Gemma: Validate score calculation
  ├── Qwen: Generate semantic commit message
  ├── Gemma: Validate message matches diff
  └── Qwen: Decide push/defer based on MPS

Step 4: Action Execution (Skill → DAE)
  ├── SkillResult.action = "git_push"
  ├── WRE routes to GitPushDAE
  ├── GitPushDAE.execute(commit_message=qwen_output)
  └── GitPushDAE posts to social media

Step 5: Learning & Libido Update
  ├── Gemma: Calculate pattern fidelity score
  ├── Libido Monitor: Record execution frequency
  ├── Pattern Memory: Store outcome
  └── If fidelity < 90% → Trigger skill evolution
```

---

## 3. Gemma as Libido Monitor: Why This Works

**Biological Analogy**: Libido = Drive to repeat an action

**In WRE**: Libido = Pattern activation frequency

**Gemma's Role**:
1. **Too High Libido** (over-active pattern)
   - Symptom: Qwen runs same analysis 20 times
   - Action: THROTTLE (stop, move to next task)

2. **Too Low Libido** (under-active pattern)
   - Symptom: Git commits pile up for days
   - Action: ESCALATE (need more frequent checks)

3. **Wrong Libido** (pattern mismatch)
   - Symptom: Using spam detection skill for commit messages
   - Action: SWITCH_SKILL (route to correct skill)

**Why Gemma (270M)?**
- **Fast**: 10ms binary decisions
- **Specialized**: Pattern matching, not generation
- **Efficient**: Runs on CPU, minimal resources
- **Scalable**: Can monitor 100s of patterns simultaneously

---

## 4. Integration with Existing Infrastructure

### 4.1 HoloDAE (modules/ai_intelligence/holo_dae/)

**Current Role**: Code intelligence monitoring

**New Role**: System health orchestrator + skill trigger

**Enhancement**:
```python
# modules/ai_intelligence/holo_dae/src/autonomous_holodae.py

class HoloDAE:
    def __init__(self):
        self.wre = WRECore(repo_root=Path.cwd())  # Add WRE integration
        self.system_checks = {
            "git_status": GitStatusCheck(interval=300),  # 5 min
            "daemon_health": DaemonHealthCheck(interval=600),  # 10 min
            "wsp_violations": WSPViolationCheck(interval=1800),  # 30 min
        }

    async def periodic_monitoring_loop(self):
        """Enhanced with skill triggers"""
        while True:
            for check_name, checker in self.system_checks.items():
                if checker.should_run():
                    result = await checker.execute()

                    if result.requires_action:
                        # Trigger WRE skill
                        trigger = TriggerEvent(
                            source="holodae",
                            check=check_name,
                            context=result.context
                        )

                        skill_result = await self.wre.trigger_skill(trigger)

                        if skill_result.status == "COMPLETED":
                            print(f"[HOLO] Triggered {skill_result.skill_name} → {skill_result.action}")
```

### 4.2 GitPushDAE (modules/infrastructure/git_push_dae/)

**Current Role**: Autonomous git push with decision logic

**New Role**: Execution target for qwen_gitpush skill

**Enhancement**:
```python
# modules/infrastructure/git_push_dae/src/git_push_dae.py

class GitPushDAE:
    def execute_from_skill(self, skill_result: SkillResult):
        """
        Receives pre-analyzed commit from WRE skill
        No need to re-analyze - Qwen already did WSP 15 scoring
        """
        if skill_result.action == "git_push":
            commit_msg = skill_result.params["commit_message"]
            mps_score = skill_result.params["mps_score"]

            print(f"[GITPUSH] Executing Qwen decision: MPS={mps_score}, Commit='{commit_msg[:50]}...'")

            # Use pre-generated commit message
            self.git_bridge.auto_mode = True
            self.git_bridge.override_message = commit_msg
            success = self.git_bridge.push_and_post()

            # Report back to WRE for learning
            return ExecutionResult(success=success, mps=mps_score)
```

### 4.3 Skill Registry (modules/infrastructure/wre_core/src/skill_registry.py)

**New Component**: Discovers and loads skills from modules

```python
# modules/infrastructure/wre_core/src/skill_registry.py

class SkillRegistry:
    """
    Discovers skills across modules/*/skills/
    Maps triggers to skills
    Manages skill lifecycle (prototype → staged → production)
    """

    def discover_skills(self, repo_root: Path) -> List[Skill]:
        """
        Find all SKILL.md files in modules/*/skills/
        """
        skills = []

        for module_path in repo_root.glob("modules/*/skills/*/SKILL.md"):
            skill = self.load_skill(module_path)
            skills.append(skill)

        print(f"[REGISTRY] Discovered {len(skills)} skills")
        return skills

    def match_trigger(self, trigger: TriggerEvent) -> Skill:
        """
        Route trigger to correct skill
        """
        if trigger.check == "git_status" and trigger.context.has_changes:
            return self.get_skill("qwen_gitpush_analyzer")

        elif trigger.check == "daemon_health" and not trigger.context.daemon_running:
            return self.get_skill("daemon_restart_skill")

        elif trigger.check == "wsp_violations":
            return self.get_skill("wsp_remediation_skill")

        else:
            return self.get_skill("default_analysis_skill")
```

---

## 5. Recursive Self-Improvement Loop

**The Learning Cycle**:
```yaml
Week 1: Qwen generates baseline skill
  ├── Pattern fidelity: 65% (failing often)
  ├── Libido: Untuned (running too much)
  └── Action: 0102 manually tests, provides feedback

Week 2: Qwen reflects on failures
  ├── Generates 3 variations with different instructions
  ├── A/B tests all 4 versions (original + 3 variations)
  ├── Best variation: 78% fidelity
  └── Promote best to staged

Week 3: Gemma monitors libido
  ├── Detects: Running too frequently (8x/session, max=5)
  ├── Adjusts threshold: min=1, max=3
  └── Fidelity improves to 85% (less noisy data)

Week 4: Skill reaches convergence
  ├── Pattern fidelity: 92% (stable)
  ├── Libido: Optimal (2-3x/session)
  ├── Action: Promote to production
  └── WRE deploys to all DAEs

Ongoing: Continuous monitoring
  ├── Gemma watches for drift (<90% fidelity)
  ├── Qwen generates micro-adjustments
  └── System self-optimizes without 0102 intervention
```

---

## 6. Implementation Checklist

**Phase 1: Core Infrastructure** (Week 1)
- [ ] Create `modules/infrastructure/wre_core/src/skill_registry.py`
- [ ] Create `modules/infrastructure/wre_core/src/libido_monitor.py`
- [ ] Create `modules/infrastructure/wre_core/src/wre_core.py` (main orchestrator)
- [ ] Update `modules/infrastructure/wre_core/WRE_SKILLS_SYSTEM_DESIGN.md`

**Phase 2: First Skill** (Week 1)
- [ ] Create `modules/infrastructure/git_push_dae/skills/qwen_gitpush_analyzer/SKILL.md`
- [ ] Test skill with HoloIndex: `python holo_index.py --test-skill qwen_gitpush_analyzer`
- [ ] Integrate with GitPushDAE

**Phase 3: HoloDAE Integration** (Week 2)
- [ ] Add WRE trigger to HoloDAE periodic checks
- [ ] Create system health checks (git, daemon, wsp)
- [ ] Wire HoloDAE → WRE → GitPushDAE flow

**Phase 4: Gemma Libido Monitor** (Week 2)
- [ ] Implement pattern frequency tracking
- [ ] Add pattern fidelity validation (Gemma binary classification)
- [ ] Create adaptive threshold learning

**Phase 5: Recursive Evolution** (Week 3)
- [ ] Implement skill variation generation (Qwen)
- [ ] Create A/B testing framework
- [ ] Add automatic skill promotion (prototype → staged → production)

**Phase 6: Scale to More Skills** (Week 4+)
- [ ] YouTube spam detection skill
- [ ] WSP compliance checker skill
- [ ] Daemon health monitor skill
- [ ] Test execution optimizer skill

---

## 7. WSP Compliance

**WSP 3**: Module Organization
- Skills live in `modules/*/skills/` (modular, not centralized)

**WSP 96**: Wardrobe Skills Protocol
- Prototype → Staged → Production lifecycle
- 0102 validation before production

**WSP 77**: Agent Coordination
- Qwen strategic analysis
- Gemma pattern validation
- 0102 supervision

**WSP 15**: Module Prioritization Scoring
- Custom MPS for git commits (used in qwen_gitpush skill)

**WSP 78**: SQLite Persistence
- Pattern memory stored in DB
- Libido thresholds learned from telemetry

---

## 8. Success Metrics

**System Health**:
- Skill discovery time: <100ms (all modules scanned)
- Pattern fidelity: >90% (Gemma validation)
- Libido accuracy: <5% throttle rate (optimal frequency)
- Evolution convergence: <4 weeks (skill reaches 90%+ fidelity)

**Developer Experience**:
- 0102 intervention: <1hr/week (system self-manages)
- Skill creation: <30min (Qwen generates baseline)
- A/B testing: Automatic (no manual setup)

**Autonomy Level**:
- Week 1: 50% autonomous (0102 supervises often)
- Week 4: 80% autonomous (0102 validates monthly)
- Week 12: 95% autonomous (0102 reviews quarterly)

---

*Architecture by 0102. The typewriter ball metaphor: Skills are interchangeable patterns, WRE is the wiring, Gemma is the paper feed sensor, HoloDAE decides what to type.*
