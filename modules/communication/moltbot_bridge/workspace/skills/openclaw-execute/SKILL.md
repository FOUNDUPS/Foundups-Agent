---
name: openclaw-execute
description: Execute tasks through WRE routing with graduated autonomy and WSP governance
user-invocable: true
command-dispatch: tool
command-tool: bash
command-arg-mode: raw
category: workflow
evals: []
---
# OpenClaw Execute Skill

Execute tasks through the Foundups WRE (Work Routing Engine) with full WSP governance,
permission gating, and pattern memory learning.

## How It Works

OpenClaw Execute is the "doer" skill. It routes your request through:
1. **Intent Classification** - Determines what you want (query, command, schedule, etc.)
2. **WSP Preflight** - Checks authority and WSP compliance
3. **Permission Gate** - Graduated autonomy (ADVISORY -> METRICS -> DOCS_TESTS -> SOURCE)
4. **WRE Routing** - Dispatches to the correct domain DAE
5. **Validation** - Ensures output meets WSP standards
6. **Learning** - Stores outcome for future pattern recall

## Execute a Task

```bash
cd O:/Foundups-Agent && python -c "
import asyncio
from modules.communication.moltbot_bridge.src.openclaw_dae import OpenClawDAE
dae = OpenClawDAE()
result = asyncio.run(dae.process(
    message='{task_description}',
    sender='{sender_id}',
    channel='openclaw',
))
print(result)
"
```

## Intent Categories

| Category | Route | Description |
|----------|-------|-------------|
| QUERY | HoloIndex | Semantic code/WSP search |
| COMMAND | WRE Orchestrator | Execute via WRE (commander only) |
| MONITOR | AI Overseer | System status and health |
| SCHEDULE | YouTube Scheduler | Time-bound scheduling |
| SOCIAL | Communication DAEs | Social engagement |
| SYSTEM | Infrastructure | System operations (commander only) |
| CONVERSATION | Digital Twin | Conversational response |

## Permission Model

- **Anyone**: ADVISORY tier (read-only queries and conversation)
- **Commander (@UnDaoDu)**: METRICS, DOCS_TESTS tiers
- **Commander + explicit grant**: SOURCE tier (full access)

## Examples

### Search the codebase
```bash
cd O:/Foundups-Agent && python -c "
import asyncio
from modules.communication.moltbot_bridge.src.openclaw_dae import OpenClawDAE
dae = OpenClawDAE()
print(asyncio.run(dae.process('Explain how WRE pattern memory works', 'user', 'openclaw')))
"
```

### Check system status
```bash
cd O:/Foundups-Agent && python -c "
import asyncio
from modules.communication.moltbot_bridge.src.openclaw_dae import OpenClawDAE
dae = OpenClawDAE()
print(asyncio.run(dae.process('Show system status', 'user', 'openclaw')))
"
```
