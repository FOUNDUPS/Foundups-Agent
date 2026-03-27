# WSP Orchestrator - 0102 Orchestrator + Worker Bee Architecture

**WSP Domain**: `infrastructure` (WSP 3)

## Purpose

Modular "follow WSP" system where 0102 orchestrates Qwen/Gemma/MCP workers.

**CRITICAL**: This is a **standalone module** - **NO CODE IN MAIN.PY**.

## Architecture (Based on autonomous_refactoring.py Proven Pattern)

```
0102 Meta-Orchestration
    +-- Worker 1: HoloIndex MCP (semantic search, WSP lookup)
    +-- Worker 2: role="triage" (fast pattern matching)
    +-- Worker 3: role="code" (strategic planning, coding)
    +-- Worker 4: role="general" (reasoning, synthesis)
    +-- Worker 5: role="vision" (browser/UI automation)
    +-- Worker 6: Rules Engine (grep/regex)
    +-- 0102 Supervision (human oversight)
    +-- Escalation: role="architect_escalation" (bounded, explicit policy)
```

**Role-Based Selection**: `local_model_selection.py` resolves `triage/general/code` to current best
candidates. `vision` is resolved via `ui_tars_bridge.py`. `architect_escalation` is policy-only.
Models are fluid; roles are stable contracts. Future trained models become role candidates.

**Note**: Runtime dispatch uses role constants (`role:triage`, `role:code`, `role:0102`).
Remaining model-name references are in the external `AutonomousRefactoringOrchestrator` API
(`workers.qwen_engine`, `workers.gemma_engine`) which is outside this module's scope.

### Execution Flow

0. **Phase -1: WSP_00 Gate** - zen-state compliance gate (fail-closed in strict mode)
1. **Phase 0: Meta-Orchestration** - 0102 scores task via WSP 15
2. **Phase 1: Generate Plan** - create WSP execution plan
3. **Phase 2: Assign Workers** - route tasks to appropriate bees
4. **Phase 3: Execute with Supervision** - worker execution under 0102 control
5. **Phase 4: Learning** - store patterns for future use

## Usage

### Standalone CLI (NOT from main.py)

```bash
python modules/infrastructure/wsp_orchestrator/src/wsp_orchestrator.py "create new module for YouTube analysis"
```

### Programmatic API

```python
from modules.infrastructure.wsp_orchestrator.src.wsp_orchestrator import WSPOrchestrator

orchestrator = WSPOrchestrator()

import asyncio

async def _run():
    try:
        results = await orchestrator.follow_wsp("implement new feature X")
        print(results["wsp00_gate"])
    finally:
        await orchestrator.shutdown()

asyncio.run(_run())
```

## Key Features

- **WSP_00 Hard Gate**: "follow WSP" blocks up front when compliance gate fails in strict mode
- **0102 Orchestration**: 0102 controls execution strategy and worker assignment
- **Worker Bees**: Specialized agents (Gemma/MCP/Qwen/Rules)
- **MCP Integration**: HoloIndex search, WSP lookup via MCP servers
- **Fail-Closed Safety**: missing tracker/gate errors block when strict mode is enabled
- **Modular Design**: Zero code in main.py

## WSP Compliance

- **WSP 77**: Agent Coordination Protocol (Overseer -> Workers)
- **WSP 50**: Pre-Action Verification (HoloIndex first)
- **WSP 00**: Zen-state compliance gate before orchestration
- **WSP 84**: Code Memory Verification (MCP tools, no duplication)
- **WSP 3**: Infrastructure Domain (orchestration)
- **WSP 49**: Module Structure (complete)

## Gate Controls (Env Vars)

- `WSP00_AUTO_AWAKEN=1` (default): auto-attempt awakening when gate is non-compliant
- `WSP00_STRICT_GATE=1` (default): fail closed when gate fails / tracker unavailable / gate check errors

## Worker Assignment Logic

| Task Type | Role Requested | Resolution Surface | Rationale |
|-----------|---------------|-------------------|-----------|
| HoloIndex search | - | MCP | Semantic code search (no model) |
| WSP lookup | - | MCP | Protocol documentation (no model) |
| Pattern matching | triage | local_model_selection.py | Fast binary decisions (<10ms target) |
| Strategic planning | code | local_model_selection.py | Deep analysis (resident coder) |
| General reasoning | general | local_model_selection.py | Synthesis tasks (non-code) |
| Browser/UI automation | vision | ui_tars_bridge.py | Screenshot/UI analysis (UI_TARS_PATH) |
| Implementation | - | 0102 | Human oversight (manual) |
| ModLog updates | code | local_model_selection.py | Documentation generation |
| Architect escalation | - | explicit policy | Bounded high-compute (not auto-resolved) |

**Role Resolution**:
- `triage/general/code`: Resolved via `local_model_selection.py` (env-configurable)
- `vision`: Separate surface via `ui_tars_bridge.py` (`UI_TARS_PATH` env var)
- `architect_escalation`: Policy-only (requires explicit escalation, not auto-resolved)

## Dependencies

- `modules.infrastructure.mcp_manager` - MCP server management
- `holo_index.qwen_advisor.orchestration.autonomous_refactoring` - Qwen/Gemma workers
- `logging`, `json`, `time` - Standard library

## Future Enhancements

- Full MCP tool invocation (not just server start/stop)
- Pattern learning and storage
- Autonomous execution mode (no 0102 approval)
- Integration with main.py menu (option 15: "WSP Orchestrator")
