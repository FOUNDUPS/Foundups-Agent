# WRE Core: Recursive Skills Orchestration System

> **Historical architecture record — superseded and non-authoritative.**
> This WSP 96-era design does not describe current production authority. Current
> execution truth and known gaps live in `README.md`, `INTERFACE.md`,
> `ROADMAP.md`, the recursive-improvement docs, and WSP 95 v2.1.

**Version**: 2.0 - Gemma Libido Monitor + Skill Evolution
**Status**: Architectural Design Complete - Ready for Phase 1
**Authority**: WSP 96 (Wardrobe Skills) + WSP 77 (Agent Coordination)

---

## Quick Start: The Typewriter Ball Analogy

Think of the **IBM Selectric typewriter**:
- **Typewriter balls** (interchangeable) = **Skills** (Gemma 270M patterns)
- **Mechanical wiring** = **WRE Core** (skill routing)
- **Paper feed sensor** = **Gemma Libido Monitor** (pattern frequency)
- **Operator** = **HoloDAE + 0102** (trigger decisions)

**Key Insight**: Gemma (270M) is fast pattern matching, not heavy thinking. Qwen (1.5B+) does strategic analysis. WRE decides WHEN to switch "balls" (skills).

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│           0102 + HoloDAE (The Operator)                 │
│     Decides WHAT to do and WHEN (periodic checks)       │
└────────────────────┬────────────────────────────────────┘
                     │ Triggers
                     ↓
┌─────────────────────────────────────────────────────────┐
│                   WRE Core (The Wiring)                 │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │   Skill     │  │   Libido     │  │   Pattern     │  │
│  │  Registry   │  │   Monitor    │  │   Memory      │  │
│  │             │  │  (Gemma)     │  │   (SQLite)    │  │
│  └─────────────┘  └──────────────┘  └───────────────┘  │
│         ↓               ↓                    ↓          │
│    Load Skill   →   Check Freq   →   Store Result      │
└────────────────────┬────────────────────────────────────┘
                     │ Routes to
                     ↓
┌─────────────────────────────────────────────────────────┐
│              Wardrobe Skills (The Balls)                │
│  ┌───────────────┐  ┌──────────────┐  ┌─────────────┐  │
│  │ qwen_gitpush  │  │ wsp_checker  │  │ spam_detect │  │
│  │  (WSP 15 MPS) │  │ (compliance) │  │  (YouTube)  │  │
│  └───────────────┘  └──────────────┘  └─────────────┘  │
│         ↓                 ↓                  ↓          │
│    Qwen thinks  →   Gemma validates  →  DAE executes   │
└─────────────────────────────────────────────────────────┘
```

---

## Three Layers Explained

### Layer 1: Gemma Libido Monitor (The Frequency Sensor)

**Purpose**: Monitors Qwen's thought pattern frequency

**What is "Libido"?**
- Biological: Drive to repeat an action
- WRE: Pattern activation frequency
- Prevents: Too much thinking (waste) or too little (rushed)

**How it Works**:
```python
# Check if Qwen is thinking too much about git commits
libido_signal = monitor.check_pattern("qwen_gitpush")

if libido_signal == "THROTTLE":
    # Ran 10x this session, max is 5 → STOP
elif libido_signal == "ESCALATE":
    # Haven't run in 2 days, should check git → GO NOW
else:
    # Just right, continue → PROCEED
```

**Performance**: <10ms per check (Gemma 270M binary classification)

---

### Layer 2: Wardrobe Skills (The Typewriter Balls)

**Purpose**: Discrete, task-specific instructions for Qwen/Gemma

**Example: qwen_gitpush Skill**
```yaml
name: qwen_gitpush_analyzer
agents: [qwen-1.5b, gemma-270m]
intent_type: DECISION

instructions:
  1. Analyze git diff (Qwen strategic analysis)
  2. Calculate WSP 15 MPS score (custom formula)
  3. Generate semantic commit message (Qwen generation)
  4. Decide: Push now or defer? (threshold logic)

gemma_validation:
  - Did Qwen analyze files?
  - Does message match diff?
  - Is MPS calculated correctly?

libido_thresholds:
  min: 1  # At least once per session
  max: 5  # Don't spam git pushes

promotion_state: prototype  # 0102 testing
```

**Location**: `modules/infrastructure/git_push_dae/skills/qwen_gitpush/SKILL.md`

**Why This Works**: Skills are **trainable weights** that evolve
- Pattern fidelity < 90% → Qwen generates variation
- A/B test variations → Select best
- Update skill = "gradient descent" for prompts

---

### Layer 3: WRE Core (The Mechanical Wiring)

**Purpose**: Recursive orchestrator that connects everything

**Main Functions**:
1. **Skill Registry**: Discovers skills from `modules/*/skills/`
2. **Trigger Router**: HoloDAE → Correct skill → DAE
3. **Libido Monitor**: Gemma validates frequency
4. **Pattern Memory**: Stores outcomes for learning
5. **Evolution Engine**: A/B tests skill variations

**Entry Point**:
```python
from modules.infrastructure.wre_core.src.wre_core import WRECore

wre = WRECore(repo_root=Path.cwd())

# Trigger from HoloDAE
trigger = TriggerEvent(
    source="holodae",
    check="git_status",
    context={"changes": git_diff}
)

result = await wre.trigger_skill(trigger)
# → Loads qwen_gitpush skill
# → Checks libido (not too frequent)
# → Qwen analyzes + generates commit
# → Gemma validates pattern fidelity
# → Routes to GitPushDAE for execution
```

---

## The Complete Trigger Chain

**Step-by-Step Flow**:

```
1. HoloDAE Periodic Check (5-10 min)
   └─ Detects uncommitted git changes

2. HoloDAE Fires Trigger
   └─ TriggerEvent(check="git_status", context={...})

3. WRE Core Receives Trigger
   ├─ SkillRegistry.match_trigger() → qwen_gitpush skill
   ├─ LibidoMonitor.should_execute() → CHECK frequency
   └─ If OK, proceed to execution

4. Skill Execution (Qwen + Gemma)
   ├─ Qwen: Analyze git diff (strategic)
   ├─ Gemma: Validate analysis (pattern fidelity)
   ├─ Qwen: Calculate WSP 15 MPS score
   ├─ Gemma: Validate MPS calculation
   ├─ Qwen: Generate semantic commit message
   ├─ Gemma: Validate message matches diff
   └─ Qwen: Decide push/defer (threshold)

5. Action Routing (Skill → DAE)
   ├─ SkillResult.action = "git_push"
   ├─ WRE routes to GitPushDAE
   └─ GitPushDAE.execute(commit_msg)

6. Learning Loop
   ├─ Gemma: Calculate pattern fidelity (92%)
   ├─ LibidoMonitor: Record execution
   ├─ PatternMemory: Store outcome
   └─ If fidelity < 90% → Evolve skill
```

---

## Recursive Self-Improvement

**The Evolution Cycle**:

```yaml
Week 1: Baseline skill
  Pattern fidelity: 65%
  Status: prototype
  Action: 0102 manually tests

Week 2: First evolution
  Qwen reflects on failures
  Generates 3 variations
  A/B tests all 4 versions
  Best variation: 78% fidelity
  Action: Promote best to staged

Week 3: Libido tuning
  Gemma detects: Running 8x/session (max=5)
  Adjusts threshold: min=1, max=3
  Fidelity improves: 85%

Week 4: Convergence
  Pattern fidelity: 92%
  Libido: Optimal (2-3x/session)
  Action: Promote to production
  Result: Fully autonomous

Ongoing: Continuous monitoring
  Gemma watches for drift (<90%)
  Qwen generates micro-adjustments
  System self-optimizes
```

---

## Implementation Roadmap

### Phase 1: Core Infrastructure (Week 1)
- [ ] `src/skill_registry.py` - Skill discovery and loading
- [ ] `src/libido_monitor.py` - Gemma frequency monitoring
- [ ] `src/wre_core.py` - Main orchestrator
- [ ] `src/pattern_memory.py` - SQLite outcome storage

### Phase 2: First Skill (Week 1-2)
- [ ] `modules/infrastructure/git_push_dae/skills/qwen_gitpush/SKILL.md`
- [ ] Test with: `python holo_index.py --test-skill qwen_gitpush`
- [ ] Integrate with GitPushDAE execution

### Phase 3: HoloDAE Integration (Week 2)
- [ ] Add WRE trigger to HoloDAE periodic checks
- [ ] Create system health checks (git, daemon, wsp)
- [ ] Wire complete chain: HoloDAE → WRE → GitPushDAE

### Phase 4: Gemma Libido (Week 2-3)
- [ ] Pattern frequency tracking
- [ ] Pattern fidelity validation
- [ ] Adaptive threshold learning

### Phase 5: Evolution Engine (Week 3)
- [ ] Skill variation generation (Qwen)
- [ ] A/B testing framework
- [ ] Automatic promotion (prototype → staged → production)

### Phase 6: Scale (Week 4+)
- [ ] YouTube spam detection skill
- [ ] WSP compliance checker skill
- [ ] Daemon health monitor skill
- [ ] Test execution optimizer skill

---

## Files in This Module

```
modules/infrastructure/wre_core/
├── README.md                                    # This file
├── WRE_RECURSIVE_ORCHESTRATION_ARCHITECTURE.md  # Deep-dive design
├── WRE_SKILLS_SYSTEM_DESIGN.md                  # Original design doc
├── AI_ENTRY_POINTS_MAPPING.md                   # Skill inventory
├── src/
│   ├── wre_core.py                 # Main orchestrator
│   ├── skill_registry.py           # Skill discovery/loading
│   ├── libido_monitor.py           # Gemma frequency monitor
│   ├── pattern_memory.py           # SQLite outcome storage
│   └── skill_evolution.py          # A/B testing & promotion
├── skills/                         # Core WRE skills (if any)
└── tests/
    ├── test_skill_registry.py
    ├── test_libido_monitor.py
    └── test_wre_integration.py
```

---

## WSP Compliance

**WSP 3**: Module Organization
- Skills in `modules/*/skills/` (modular, not centralized)

**WSP 96**: Wardrobe Skills Protocol
- Lifecycle: prototype → staged → production
- 0102 validation required

**WSP 77**: Agent Coordination
- Qwen: Strategic analysis
- Gemma: Pattern validation
- 0102: Supervision

**WSP 15**: Module Prioritization Scoring
- Custom MPS for git commit decisions

**WSP 78**: SQLite Persistence
- Pattern memory in DB
- Libido thresholds stored

---

## Success Metrics

**Performance**:
- Skill discovery: <100ms (all modules)
- Pattern fidelity: >90% (Gemma validation)
- Libido accuracy: <5% false throttles
- Evolution time: <4 weeks to convergence

**Autonomy**:
- Week 1: 50% autonomous (frequent 0102 supervision)
- Week 4: 80% autonomous (monthly validation)
- Week 12: 95% autonomous (quarterly reviews)

---

## Quick Reference

**Trigger a skill manually**:
```python
from modules.infrastructure.wre_core.src.wre_core import WRECore, TriggerEvent

wre = WRECore(repo_root=Path.cwd())
result = await wre.trigger_skill(
    TriggerEvent(source="manual", check="git_status", context={})
)
```

**Check libido status**:
```python
from modules.infrastructure.wre_core.src.libido_monitor import GemmaLibidoMonitor

monitor = GemmaLibidoMonitor()
signal = monitor.check_pattern("qwen_gitpush")
print(f"Libido: {signal}")  # CONTINUE | THROTTLE | ESCALATE
```

**View skill registry**:
```bash
python -c "
from modules.infrastructure.wre_core.src.skill_registry import SkillRegistry
registry = SkillRegistry(Path.cwd())
registry.list_skills()
"
```

---

**Status**: Architecture Complete ✓ | Implementation: Phase 1 Ready
**Next**: Create `src/skill_registry.py` and begin skill discovery
