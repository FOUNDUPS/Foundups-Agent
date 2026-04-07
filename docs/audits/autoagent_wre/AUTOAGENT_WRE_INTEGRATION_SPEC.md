# AutoAgent WRE Integration Spec

Worker: AD
Date: 2026-04-07
Slice: AUTOAGENT_WRE_INTEGRATION_SPEC_PHASE1
Status: Canonical
Repo: Foundups-Agent

## 1. Problem

FoundUps has WRE infrastructure for skill execution, pattern memory, and A/B testing,
but no isolated experiment harness that iterates on a target configuration and
keeps/discards changes based on measured score improvement.

AutoAgent (MIT, github.com/kevinrgu/autoagent) solves exactly this problem:
a meta-agent that reads instructions, inspects a harness, runs benchmarks,
modifies the harness, and keeps only score-improving changes (hill-climbing).

The question is: where does this pattern fit in FoundUps, and what is safe
to optimize first?

## 2. Architecture Recommendation

**RECOMMEND: WRE_ADJACENT_EXPERIMENT_HARNESS**

A new standalone module at `modules/infrastructure/autoagent_lab/` that:
- Lives adjacent to WRE (not inside it)
- Targets WRE skill configurations as its first optimization surface
- Runs benchmarks against a deterministic eval loop
- Keeps score-improving changes, discards regressions
- Produces diff artifacts for operator review
- Never mutates production WRE directly

### Why This Placement

| Factor | Verdict |
|--------|---------|
| WRE is the target | The optimizer must be separate from what it optimizes |
| OpenClaw is not the first target | OpenClaw is the future control plane — it triggers experiments, it is not the experiment |
| Isolation safety | Separate module = separate failure domain, clear rollback boundary |
| Existing infrastructure | WRE already has PatternMemory, SkillOutcome, fidelity scores — the lab consumes these |
| Future extensibility | Lab can later target WSP orchestrator routing, OBAI responses, etc. |

### What This Is NOT

- NOT a fork/vendor-copy of AutoAgent into the repo
- NOT a self-editing OpenClaw
- NOT a production WRE mutator
- NOT benchmark-free optimization

## 3. Core Concept: Experiment Loop

```
┌─────────────────────────────────────────────┐
│                 EXPERIMENT LOOP              │
│                                             │
│  1. Load target config (skill YAML, prompt) │
│  2. Run eval suite → score (0.0-1.0)        │
│  3. Generate candidate change               │
│  4. Apply change to isolated copy            │
│  5. Run eval suite → new_score              │
│  6. If new_score > score: KEEP              │
│     Else: DISCARD                           │
│  7. Record outcome (keep/discard + diff)     │
│  8. Repeat until budget exhausted            │
└─────────────────────────────────────────────┘
```

This is the AutoAgent pattern adapted to FoundUps constraints:
- Target is a WRE skill config, not arbitrary code
- Eval is a deterministic pytest-compatible harness, not stochastic LLM judgment
- Changes are score-gated, not blind
- All iterations produce a reviewable diff artifact

## 4. Relationship Map

```
                    ┌──────────────┐
                    │  012 / 0102  │  ← Reviews diff artifacts
                    └──────┬───────┘
                           │ triggers / inspects
                    ┌──────▼───────┐
                    │   OpenClaw   │  ← Future: trigger experiments
                    │  (Phase 2+) │     inspect results
                    └──────┬───────┘
                           │ commands
                    ┌──────▼───────┐
                    │ autoagent_lab│  ← NEW: experiment harness
                    │  (isolated) │
                    └──────┬───────┘
                           │ reads configs / writes diffs
                    ┌──────▼───────┐
                    │   WRE Core   │  ← Target surface
                    │  (read-only) │     PatternMemory, Skills
                    └──────────────┘
```

### Module Boundaries (WSP 97)

| Module | Role | Can Mutate |
|--------|------|-----------|
| autoagent_lab | Experiment orchestrator | Only isolated copies in experiment workspace |
| wre_core | Target surface + data source | NOT mutated by autoagent_lab |
| OpenClaw | Future trigger/inspector | NOT a mutation target in Phase 1 |
| PatternMemory | Score data source | Read-only by autoagent_lab |

## 5. What AutoAgent Ideas to Adopt

### Adopt (Ideas, Not Code)

| AutoAgent Concept | FoundUps Adaptation |
|-------------------|---------------------|
| `program.md` instructions | `experiment_spec.yaml` — defines target, eval, budget |
| `agent.py` single-file harness | Skill config (SKILL.md YAML frontmatter) as target |
| Hill-climbing on score | PatternMemory fidelity + custom eval score |
| Benchmark tasks | Deterministic pytest eval functions |
| Keep/discard discipline | Git-based: branch per experiment, merge only on improvement |

### Do NOT Adopt

| AutoAgent Pattern | Why Not |
|-------------------|---------|
| Docker-based execution | Overkill for Phase 1 — pytest in venv is sufficient |
| Harbor task format | No Harbor dependency — use native pytest |
| Arbitrary code mutation | Only SKILL.md configs and bounded prompt text |
| External model provider dependency | Use local models (Qwen/Gemma) already in repo |

### Adoption Method: Copy Ideas, Not Code

AutoAgent is a reference architecture. We adopt the pattern (iterate → eval → keep/discard)
but implement it natively using existing FoundUps infrastructure:
- PatternMemory for score storage
- pytest for eval
- git branches for isolation
- SKILL.md YAML for target configs

No vendor snapshot, no fork, no submodule. The AutoAgent repo is a design reference only.

## 6. Proposed Module Structure

```
modules/infrastructure/autoagent_lab/
├── README.md
├── INTERFACE.md
├── ModLog.md
├── requirements.txt
├── config/
│   └── experiment_spec_template.yaml
├── src/
│   ├── __init__.py
│   ├── experiment_runner.py      # Core loop: load → eval → mutate → eval → keep/discard
│   ├── experiment_config.py      # ExperimentSpec dataclass + loader
│   ├── target_surface.py         # Read/write skill configs (isolated copies only)
│   ├── eval_harness.py           # Run pytest eval suite, return score 0.0-1.0
│   ├── diff_recorder.py          # Record keep/discard decisions + diffs
│   └── safety_gates.py           # Score regression check, file allowlist, budget limit
├── workspace/                    # Ephemeral experiment workspace (gitignored)
│   └── .gitkeep
└── tests/
    ├── __init__.py
    ├── test_experiment_runner.py
    ├── test_eval_harness.py
    └── test_safety_gates.py
```

## 7. Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AUTOAGENT_LAB_ENABLED` | NO | `false` | Master switch |
| `AUTOAGENT_MAX_ITERATIONS` | NO | `10` | Max iterations per experiment |
| `AUTOAGENT_SCORE_THRESHOLD` | NO | `0.0` | Minimum improvement to keep |
| `AUTOAGENT_TARGET_ALLOWLIST` | NO | `*.yaml,SKILL.md` | Files the lab can modify |
| `AUTOAGENT_WORKSPACE_DIR` | NO | `workspace/` | Ephemeral experiment directory |
| `AUTOAGENT_LOG_LEVEL` | NO | `INFO` | Logging level |

## 8. Non-Goals (Phase 1)

1. No production WRE self-mutation
2. No OpenClaw DAE mutation
3. No live Discord bot mutation
4. No source code editing (only configs and prompts)
5. No external model provider dependency
6. No Docker/Harbor dependency
7. No unbenchmarked changes
8. No fake performance claims
9. No claims that WRE is ready for recursive mutation today
10. No autonomous deployment of experiment results

## 9. WSP Compliance

| WSP | Application |
|-----|-------------|
| WSP 3 | Module placed under `infrastructure/` domain |
| WSP 15 | Read-first: WRE state verified before spec |
| WSP 48 | Recursive improvement pattern (experiment loop) |
| WSP 49 | Standard module structure |
| WSP 50 | Pre-action: eval before mutation |
| WSP 72 | Module independence (no wre_core coupling) |
| WSP 91 | Observability (diff artifacts, score logs) |
| WSP 97 | Internal boundaries (lab reads WRE, never writes production) |

## 10. Acceptance Criteria

- [x] WRE-vs-OpenClaw placement is explicit (lab is adjacent to WRE, not inside OpenClaw)
- [x] Target surface is explicit (WRE skill configs)
- [x] Evaluation method is explicit (deterministic pytest harness)
- [x] Safety gates are explicit (see AUTOAGENT_EVAL_AND_SAFETY_GATES.md)
- [x] Build order is explicit (see AUTOAGENT_BUILD_ORDER.md)
- [x] No runtime code changes
- [x] AutoAgent adoption method is explicit (ideas only, no vendor copy)
