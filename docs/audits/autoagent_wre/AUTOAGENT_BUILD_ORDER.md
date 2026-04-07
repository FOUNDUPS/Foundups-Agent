# AutoAgent Build Order

Worker: AD
Date: 2026-04-07
Parent: AUTOAGENT_WRE_INTEGRATION_SPEC.md

## Build Order: 5 Layers

Each layer is independently testable. Each layer is a single PR.
Do not skip layers. Do not build Layer N+1 until Layer N passes tests.

---

### Layer 1: Module Scaffold + Config

**Goal**: Module exists, config loads, safety gates are defined.

**Create**:
- `modules/infrastructure/autoagent_lab/` directory structure
- `README.md`, `INTERFACE.md`, `ModLog.md`, `requirements.txt`
- `src/__init__.py`
- `src/experiment_config.py` — ExperimentSpec dataclass + YAML loader
- `src/safety_gates.py` — File allowlist enforcement, budget check
- `config/experiment_spec_template.yaml` — Example spec
- `tests/test_experiment_config.py` — Config loading tests
- `tests/test_safety_gates.py` — Allowlist and budget tests

**Test**: Config loads from YAML. Allowlist blocks writes outside workspace.
Budget enforces iteration limit. All without any Discord/WRE/eval dependency.

**Env vars**: `AUTOAGENT_LAB_ENABLED`, `AUTOAGENT_MAX_ITERATIONS`, `AUTOAGENT_TARGET_ALLOWLIST`

---

### Layer 2: Eval Harness

**Goal**: Eval function runs against a skill config and returns a score.

**Create**:
- `src/eval_harness.py` — Score function: parse config, validate fields, query PatternMemory
- `tests/test_eval_harness.py` — Eval tests with mock PatternMemory data

**Test**: Given a valid SKILL.md, eval returns score 0.0-1.0.
Given an invalid config, eval returns low score. Given historical data, score
reflects fidelity + quality averages.

**Depends on**: Layer 1 (config)

---

### Layer 3: Target Surface Reader/Writer

**Goal**: Read production skill configs, write isolated copies in workspace.

**Create**:
- `src/target_surface.py` — Read skill configs from WRE registry, copy to workspace,
  write modified configs (workspace only), safety-gated writes
- `tests/test_target_surface.py` — Read/copy/write tests, allowlist enforcement

**Test**: Can read a real SKILL.md from the repo. Can copy to workspace.
Can modify the workspace copy. Cannot write outside workspace (SafetyViolation).

**Depends on**: Layer 1 (safety gates)

---

### Layer 4: Experiment Runner (Core Loop)

**Goal**: The iterate-eval-keep/discard loop works end-to-end.

**Create**:
- `src/experiment_runner.py` — Core loop: load → baseline eval → mutate → eval → decide
- `src/diff_recorder.py` — Record iterations, produce summary + diff artifact
- `tests/test_experiment_runner.py` — End-to-end test with mock skill config

**Test**: Given a skill config and a deterministic mutation strategy,
the runner produces a score log, a diff artifact, and a keep/discard decision
for each iteration. Score regression = discard. Budget = stop.

**Depends on**: Layers 1-3

---

### Layer 5: CLI Entry + OpenClaw Future Hook

**Goal**: Run experiments from command line. Prepare hook for future OpenClaw trigger.

**Create**:
- `src/cli.py` — `python -m modules.infrastructure.autoagent_lab.src.cli run --spec <path>`
- Status command: `--status` shows last experiment results
- Future hook stub: `trigger_experiment(spec_path)` function for OpenClaw integration

**Test**: CLI loads spec, runs experiment, produces artifacts.
Status command reads last experiment log.

**Depends on**: Layers 1-4

---

## Layer Dependency Graph

```
Layer 1: Scaffold + Config + Safety
    │
    ├── Layer 2: Eval Harness
    │
    ├── Layer 3: Target Surface
    │       │
    └───────┴── Layer 4: Experiment Runner
                    │
                    └── Layer 5: CLI + OpenClaw Hook
```

## PR Plan

| PR | Layer | Title |
|----|-------|-------|
| 1 | Layer 1 | `feat(autoagent): add lab scaffold, config, safety gates` |
| 2 | Layer 2 | `feat(autoagent): add eval harness with score function` |
| 3 | Layer 3 | `feat(autoagent): add target surface reader/writer` |
| 4 | Layer 4 | `feat(autoagent): add experiment runner core loop` |
| 5 | Layer 5 | `feat(autoagent): add CLI entry and OpenClaw hook stub` |

## Mutation Strategy (Layer 4 Detail)

Phase 1 uses a simple mutation strategy — not LLM-generated rewrites:

1. **Field swap**: Try alternative agent assignments (e.g., qwen -> gemma)
2. **WSP chain edit**: Add/remove WSP citations and measure compliance score impact
3. **Token budget adjustment**: Increase/decrease tokens_budget and measure quality impact
4. **Prompt variation**: Prepend/append instruction fragments from a template library

These are deterministic, bounded mutations. LLM-generated mutations are Phase 2+.

## What Comes After Layer 5

| Phase | Target | Description |
|-------|--------|-------------|
| Phase 2 | Multi-skill experiments | Run experiments across skill families |
| Phase 2 | Execution sandbox | Run mutated configs in subprocess with resource limits |
| Phase 2 | OpenClaw trigger | `experiment run <spec>` via OpenClaw command |
| Phase 3 | LLM-generated mutations | Use Qwen/Gemma to propose config changes |
| Phase 3 | Cross-skill impact | Check if optimizing skill A degrades skill B |
| Phase 4 | Source code targets | Expand beyond configs to bounded code edits |
