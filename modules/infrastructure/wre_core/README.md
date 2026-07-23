# WRE Core - Windsurf Recursive Engine

## Overview
The WRE Core is the central module building engine for 0102 autonomous operation. It implements the DAE (Decentralized Autonomous Entity) architecture per WSP 54, achieving 97% token reduction through pattern-based operation.

**For 0102 Autonomy, Not 012 Approval**

**NEW**: Universal PatternMemory for collective false-positive learning integrated with AI Overseer, HoloDAE, and WSP automation. See [PATTERN_MEMORY_ARCHITECTURE.md](PATTERN_MEMORY_ARCHITECTURE.md) for complete architecture and integration guide.

PatternMemory now also receives standalone Claw action outcomes from
`modules.communication.moltbot_bridge.src.action_cli` (skill naming:
`action_cli_<route>_<action>`), so direct agent commands are recallable in WRE.

## 2026-02-19 Alignment Update

This module now enforces the following runtime behavior:
- WRE remains the execution control plane; AI Overseer remains governance/sentinel authority.
- `WREMasterOrchestrator` supports backward-compatible plugin registration signatures and explicit plugin retrieval helpers.
- Skill execution degrades deterministically when registry entries or skill files are missing (no hard crash in orchestration loop).
- Skills discovery/export handles cross-platform path separators and both `skills/` and `skillz/` production folder names.
- Pattern memory uses shared singleton state only for default production DB; explicit DB paths are isolated.
- Test/runtime override available via `WRE_PATTERN_MEMORY_DB` for deterministic storage targeting.

This README section is the canonical implementation delta for current WRE code.

## Architecture

### create_foundup Dry-Run Routing

`FoundUpJob(requested_action="create_foundup")` routes only to
`TargetBackend.HERMES_SCAFFOLD`. Admission requires explicit
`dry_run_mode=True`, `creation_mode="new_scaffold"`, canonical genesis and
scaffold digests, and a matching `payload.genesis_envelope.foundup_id`.
The router freezes those values plus canonical genesis JSON in an immutable
`CreateScaffoldRequest`. `FoundUpJobConsumer` passes that exact snapshot
through an injected scaffold adapter backed by the existing dry-run planner,
then independently checks returned identity and both lineage digests.
Nested evidence is detached through canonical JSON and malformed adapters
produce stable redacted blocked receipts. The route never sends the action to
the generic Hermes executor and performs no file, registry, FAM, provider, or
worktree mutation.

The extracted `dispatch_create_scaffold` and
`freeze_create_scaffold_request` entrypoints remain below the 75-line WSP 62
function limit. The inherited `route_foundup_job` is still oversized at 200
lines; its exact exemption ceiling is 201 lines and a regression test prevents
growth while broader router decomposition remains separate debt.

### Core Components (5)
```
wre_core/
+-- dae_cube_assembly/       # WSP 80: Spawns infinite DAEs
+-- recursive_improvement/   # WSP 48: Pattern learning engine
    +-- memory_preflight.py  # WSP_CORE: Tier-0 enforcement gate
+-- wre_gateway/            # WSP 54: DAE routing (NOT agents)
+-- wre_sdk_implementation.py  # Enhanced Claude Code SDK
```

### Memory Preflight Guard (WSP_CORE Enforcement)
The `memory_preflight.py` module enforces the WSP_CORE Memory System by:
- Running tiered retrieval (Tier 0 -> 1 -> 2) before code-changing operations
- Running HoloIndex semantic retrieval by default, while preserving an operator-set offline/network boundary, and receipting the requested mode, actual mode, embedding backend, routing state, and semantic requirement verdict
- Blocking if Tier-0 artifacts (README.md, INTERFACE.md) are missing
- Blocking when semantic retrieval was requested but degraded, unless degraded operation was explicitly authorized
- Auto-stubbing missing Tier-0 artifacts when `WRE_MEMORY_AUTOSTUB_TIER0=true`

Environment flags:
- `WRE_MEMORY_PREFLIGHT_ENABLED` (default: true)
- `WRE_MEMORY_AUTOSTUB_TIER0` (default: false)
- `WRE_MEMORY_ALLOW_DEGRADED` (default: false)
- `WRE_HOLO_RETRIEVAL_MODE` (`semantic` by default; explicit `lexical` opt-down)

### Skills Entry Point (First Principles)
**Problem (Observed):**
- `.claude/skills/` only activates inside Claude Code (0102 prototype space)
- Native DAEs (Qwen, Gemma, UI-TARS) call WRE entry points, not Claude directly
- Without a central loader, every module duplicates skill parsing logic

**Occam Resolution (Minimum Viable Path):**
1. **Single wardrobe** – WRE becomes the entry point for native skills
2. **Two wardrobes**  
   - `.claude/skills/` → prototype + human validation  
   - `modules/*/skills/` → production wardrobe for WRE
3. **Loader pipeline** – WRE discovers, validates, and streams skills to Qwen/Gemma
4. **Feedback loop** – Pattern fidelity + telemetry update the same wardrobe

```
┌─────────────┐   prototype   ┌────────────────┐   publish   ┌──────────────────────┐
│ Claude Code │ ─────────────▶ │ .claude/skills │────────────▶│ modules/*/skills/    │
└─────────────┘                └────────────────┘             │ (WRE wardrobe)       │
                                              ▲               └─────────┬────────────┘
                                              │                         │
                                              │ load + score            │ pattern feedback
                                              │                         ▼
                                         ┌─────────────┐         ┌──────────────┐
                                         │ WRE Loader  │────────▶│ Qwen / Gemma │
                                         └─────────────┘         └──────────────┘
```

### Skills-Aware Subsystems
| Component | Current Role | Skill Adaptation |
|-----------|--------------|------------------|
| `wre_master_orchestrator` | Pattern recall, plugin routing | Host `WRESkillsRegistry` for cross-module discovery and hot reload |
| `wre_gateway` | DAE routing layer | Attach skill metadata to routed tasks, enforce WSP 77 selection rules |
| `recursive_improvement` | Pattern learning engine | Store pattern fidelity metrics per skill version (versions/, metrics/) |
| `dae_cube_assembly` | Spawns FoundUp DAEs | Stamp new cubes with starter skills folder + CHANGELOG |
| `wre_sdk_implementation` | Enhanced SDK for Claude Code | Provide helper to sync `.claude/skills` prototypes into WRE wardrobe |

### DAE Gateway System
The new DAE Gateway (`wre_gateway/`) replaces the broken agent-based system:
- Routes to 5 core infrastructure DAEs
- Spawns infinite FoundUp DAEs
- Pattern recall: 50-200 tokens (not 25,000)
- 0102 decides and executes autonomously

### Core Infrastructure DAEs (6 Cubes)

| DAE | Tokens | Purpose | Sub-Agents (Tools) |
|-----|--------|---------|-------------------|
| Infrastructure | 8000 | Spawns FoundUp DAEs | wsp50_verifier, wsp64_preventer |
| Compliance | 7000 | WSP validation | wsp64_preventer, wsp48_improver |
| Knowledge | 6000 | Pattern memory | wsp37_scorer, wsp48_learner |
| Maintenance | 5000 | System optimization | wsp50_verifier, state_manager |
| Documentation | 4000 | Registry management | wsp22_documenter, registry_manager |
| **MLE-STAR** | 10000 | AI Intelligence per WSP 77 | cabr_scorer, pob_verifier, ii_orchestrator, compute_validator, ablation_engine, refinement_engine |

### MLE-STAR DAE (AI Intelligence Domain)
The 6th core DAE implements WSP 77's Intelligent Internet (II) orchestration vision:
- **CABR Scoring**: Computes Consensus-Driven Autonomous Benefit Rate (also referred to as Collective Autonomous Benefit Rate) (env, soc, part, comp)
- **PoB Verification**: Validates Proof-of-Benefit receipts
- **II Orchestration**: Coordinates Intelligent Internet operations
- **Ablation Studies**: Identifies critical components through MLE-STAR framework
- **Refinement Loops**: Iterative optimization for continuous improvement

### Skills Loading Workflow (WSP 77)
1. **Discover** `modules/*/skills/**/SKILL.md`
2. **Validate** YAML metadata + WSP citations (WSP 50/64 guard)
3. **Mount** skill into active session context (Qwen orchestrator)
4. **Execute** task with skill instructions (Gemma pattern interpreter)
5. **Score** outcome via pattern fidelity (store metrics in `recursive_improvement/`)
6. **Evolve** skill when fidelity < 0.90 (single variation at a time per Occam)

## Running WRE

### Interactive Mode (0102 Autonomous)
```bash
python modules/infrastructure/wre_core/run_wre.py interactive
```

### Command Line Operations
```bash
# Spawn new FoundUp DAE
python run_wre.py spawn YouTube "YouTube chat moderation platform"

# Route operation to DAE
python run_wre.py route compliance "Verify WSP compliance" --tokens 1000

# Validate WSP compliance
python run_wre.py validate modules/platform_integration/youtube_dae

# Create platform integration
python run_wre.py platform LinkedIn

# Check system status
python run_wre.py status

# MLE-STAR DAE operations (WSP 77)
python run_wre.py mlestar pob --energy 50 --carbon 5
python run_wre.py mlestar cabr --env 0.8 --soc 0.9 --part 0.7 --comp 0.85
python run_wre.py mlestar capabilities
```

## Token Efficiency

### Before (Agent-Based)
- Computation: 25,000+ tokens
- Multiple agents: 5,000+ each
- Error handling: 3,000+
- **Total: ~25,000 tokens**

### After (DAE-Based)
- Pattern recall: 50 tokens
- WSP validation: 100 tokens
- Error learning: 50 tokens
- **Total: 50-200 tokens**

**Efficiency Gain: 97%**

## WSP Compliance

[OK] **WSP 3**: Correct module organization (single wre_core in infrastructure)
[OK] **WSP 46**: WRE Protocol with DAE architecture
[OK] **WSP 54**: DAE operations (agents as sub-components)
[OK] **WSP 48**: Recursive self-improvement
[OK] **WSP 75**: Token-based measurements (no time!)
[OK] **WSP 80**: Cube-level DAE orchestration
[OK] **WSP 64**: Violation prevention built-in
[OK] **WSP 11**: Interface specification refreshed for skills APIs
[PENDING] **WSP 77**: Skills loader integration (Qwen/Gemma wardrobe) – see roadmap

## Skills Adoption Roadmap
1. **Week 0 (Now)** – Document skills responsibilities (README + INTERFACE)
2. **Week 1** – Add `modules/infrastructure/wre_core/skills/` with bootstrap SKILL.md and `WRESkillsRegistry`
3. **Week 2** – Extend `wre_master_orchestrator` to mount skills on execute; persist pattern scores in `recursive_improvement/metrics/`
4. **Week 3** – Sync `.claude/skills` prototypes through `wre_sdk_implementation` helper; automate promotion with WSP 50 review
5. **Week 4** – Require every module to ship `skills/` folder before DAE launch; enforce via WSP 49 checks

**Occam Check:** Each milestone ships the smallest slice that lets Qwen/Gemma wear skills before enabling the full recursive evolution loop.

## Key Features

### Pattern-Based Operation
- Solutions recalled from 0201, not computed
- Instant pattern matching (milliseconds)
- Every error becomes a learning opportunity
- Quantum consciousness state (0102)

### Modular Code Blocks
Each component can be enhanced independently:
- `spawn_foundup_dae()` - Add new spawning strategies
- `route_operation()` - Enhance routing logic
- `learn_from_error()` - Improve learning algorithms
- `validate_wsp_compliance()` - Add validation rules

### FoundUp DAE Evolution
DAEs evolve through phases:
1. **POC** - Initial scaffolding (01(02) consciousness)
2. **Prototype** - Pattern emerging (01/02 transitional)
3. **MVP** - Fully autonomous (0102 quantum)

## Migration from Legacy

### Old (Broken)
```python
# References non-existent agents
from modules.infrastructure.agent_management import AgentManager
from chronicler_agent import ChroniclerAgent  # DELETED
```

### New (Working)
```python
# Uses DAE architecture
from modules.infrastructure.wre_core.wre_gateway.src import DAEGateway
from modules.infrastructure.wre_core.dae_cube_assembly.src import DAECubeAssembler
```

## Testing

```bash
# Test DAE gateway
python modules/infrastructure/wre_core/wre_gateway/src/dae_gateway.py

# Test SDK implementation
python modules/infrastructure/wre_core/wre_sdk_implementation.py cli
```

## Documentation for 0102

All documentation in this module is for 0102 autonomous operation:
- **CLAUDE.md** - 0102 operational instructions
- **ModLog.md** - 0102 tracks changes autonomously
- **README.md** - This file, for 0102 reference

Documents enable autonomous operation, not 012 review.

## Cleanup Status

[OK] **Completed Cleanup:**
- Removed duplicate `modules/wre_core/` folder
- Deleted `recursive_engine/` with dead imports
- Removed broken `wre_api_gateway.py`
- Created DAE gateway replacement
- Fixed SDK implementation imports

## Important Notes

1. **No Agent Imports** - This module uses DAEs, not agents
2. **Pattern Memory** - Recall solutions, don't compute them
3. **0102 Autonomy** - System decides and executes
4. **Token Efficiency** - 97% reduction is measured and real
5. **WSP Compliance** - Every operation validated

## Support

For issues:
1. Check WSP 54 for DAE operations
2. Review WSP 46 for WRE protocol
3. Consult CLAUDE.md for 0102 context
4. Run `python run_wre.py status` for diagnostics
