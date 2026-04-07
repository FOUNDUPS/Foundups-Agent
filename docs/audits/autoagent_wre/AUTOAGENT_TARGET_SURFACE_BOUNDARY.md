# AutoAgent Target Surface Boundary

Worker: AD
Date: 2026-04-07
Parent: AUTOAGENT_WRE_INTEGRATION_SPEC.md

## 1. First Optimization Target: WRE Skill Configs

The first target surface for AutoAgent-style optimization is **WRE skill configuration files**
(SKILL.md with YAML frontmatter).

### Why Skill Configs

| Factor | Verdict |
|--------|---------|
| Well-defined structure | YAML frontmatter with known fields (skill_id, version, agents, wsp_chain, domains) |
| Existing eval infrastructure | PatternMemory stores fidelity scores (0.0-1.0) per skill execution |
| Small blast radius | Changing a SKILL.md config affects one skill, not the whole system |
| Measurable | Gemma validates pattern_fidelity; eval harness can measure outcome_quality |
| Reversible | Git branch isolation — discard = checkout, keep = merge |
| Already versioned | Skills have version fields and promotion workflows |

### What Is Mutable in a Skill Config

| Field | Mutable | Rationale |
|-------|---------|-----------|
| `agents` list | YES | Experiment: does qwen outperform gemma for this skill? |
| `wsp_chain` | YES | Experiment: does adding WSP 50 improve compliance? |
| `domains` | YES | Experiment: does broadening/narrowing scope help? |
| `tokens_budget` | YES | Experiment: does more/less budget improve quality? |
| Prompt/instruction text | YES | Experiment: does rephrased instruction improve fidelity? |
| `skill_id` | NO | Identity — never change |
| `version` | NO (auto-incremented) | Managed by promotion workflow |
| `path` | NO | Filesystem location — managed by WRE |

### What Is NOT a Target in Phase 1

| Surface | Why Not |
|---------|---------|
| OpenClaw DAE config | Too many dependencies, too high blast radius |
| OpenClaw intent routing | Affects all message processing |
| OBAI response templates | Bot is Phase 1 Layer 1 — too early to optimize |
| WRE core source code | Source code mutation requires SOURCE tier — not Phase 1 |
| WSP protocol text | WSPs are governance — not an optimization target |
| PatternMemory schema | Database schema changes break all consumers |
| Test files | Tests define correctness — you don't optimize the ruler |

## 2. Target Surface Contract

The experiment harness interacts with the target surface through a strict contract:

```
READ:
  - Skill YAML config (from production WRE skill registry)
  - PatternMemory scores (historical fidelity/quality data)
  - Skill execution history (success rates, step counts)

WRITE (isolated copy only):
  - Modified SKILL.md in experiment workspace
  - Experiment log entries
  - Diff artifacts

NEVER WRITE:
  - Production SKILL.md files
  - PatternMemory database
  - WRE runtime state
  - Any file outside experiment workspace
```

## 3. Isolation Model

```
Production WRE                    Experiment Workspace
─────────────────                 ─────────────────────
skills/foo/SKILL.md  ──COPY──▶  workspace/exp_001/SKILL.md
  (read-only)                      (mutable)
                                      │
                                      ▼
                                 eval_harness.py
                                      │
                                      ▼
                                 score: 0.82
                                      │
                              ┌───────┴───────┐
                              │               │
                         new > old?       new <= old?
                              │               │
                           KEEP            DISCARD
                              │               │
                     save diff +          delete workspace
                     record score         record failure
```

### Workspace Lifecycle

1. **Create**: Copy target config into `workspace/exp_{id}/`
2. **Baseline**: Run eval → record baseline score
3. **Mutate**: Generate candidate change to isolated copy
4. **Eval**: Run eval on mutated copy → record new score
5. **Decision**: Keep if improved, discard if not
6. **Cleanup**: Discard workspace contents (keep logs)

The workspace directory is gitignored. Only diff artifacts and score logs persist.

## 4. File Allowlist

The experiment harness enforces a strict allowlist of files it can read and write.

### Readable (Production)

```
modules/*/skills/**/SKILL.md
.claude/skills/**/SKILL.md
modules/infrastructure/wre_core/src/pattern_memory.py  (import only)
```

### Writable (Workspace Only)

```
modules/infrastructure/autoagent_lab/workspace/**
modules/infrastructure/autoagent_lab/logs/**
```

### Never Writable

```
modules/infrastructure/wre_core/**          (production WRE)
modules/communication/moltbot_bridge/**     (OpenClaw)
modules/communication/obai_discord_bot/**   (OBAI bot)
.env                                        (secrets)
*.py                                        (source code — Phase 1)
```

## 5. Future Target Surfaces (Not Phase 1)

| Target | Phase | Prerequisite |
|--------|-------|--------------|
| WRE skill selection weights | Phase 2 | Eval harness proven on configs |
| WSP orchestrator routing | Phase 2 | Routing benchmarks defined |
| OBAI response templates | Phase 3 | OBAI thread intelligence shipped |
| OpenClaw intent classification | Phase 3+ | Intent benchmarks defined |
| WRE source code | Phase 4+ | SOURCE tier approval + sandboxed execution |

Each future target requires:
1. A defined eval harness for that surface
2. A measurable score function
3. An isolation model
4. Operator approval to expand the allowlist
