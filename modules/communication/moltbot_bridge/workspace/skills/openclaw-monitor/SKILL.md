---
name: openclaw-monitor
description: Monitor Foundups Agent system health, WRE metrics, and DAE status
user-invocable: true
command-dispatch: tool
command-tool: bash
command-arg-mode: raw
category: workflow
evals: []
---
# OpenClaw Monitor Skill

Real-time monitoring of the Foundups Agent system through WRE and AI Overseer.

## System Status

```bash
cd O:/Foundups-Agent && python -c "
import asyncio
from modules.communication.moltbot_bridge.src.openclaw_dae import OpenClawDAE
dae = OpenClawDAE()
print(asyncio.run(dae.process('Show system status and health', 'monitor', 'openclaw')))
"
```

## WRE Metrics

```bash
cd O:/Foundups-Agent && python -c "
from modules.infrastructure.wre_core.wre_master_orchestrator.src.wre_master_orchestrator import WREMasterOrchestrator
import json
wre = WREMasterOrchestrator()
print(json.dumps(wre.get_metrics(), indent=2))
"
```

## Skill Statistics

Check execution history and pattern fidelity for any WRE skill:

```bash
cd O:/Foundups-Agent && python -c "
from modules.infrastructure.wre_core.wre_master_orchestrator.src.wre_master_orchestrator import WREMasterOrchestrator
import json
wre = WREMasterOrchestrator()
stats = wre.get_skill_statistics('{skill_name}', days=7)
print(json.dumps(stats, indent=2))
"
```

## OpenClaw DAE Health

```bash
cd O:/Foundups-Agent && python -c "
from modules.communication.moltbot_bridge.src.openclaw_dae import OpenClawDAE
dae = OpenClawDAE()
print(f'State: {dae.state}')
print(f'Coherence: {dae.coherence}')
print(f'WRE loaded: {dae.wre is not None}')
print(f'Permissions loaded: {dae.permissions is not None}')
print(f'Overseer loaded: {dae.overseer is not None}')
if dae.wre:
    print(f'WRE plugins: {list(dae.wre.plugins.keys())}')
    print(f'WRE patterns: {len(dae.wre.pattern_memory.patterns)}')
"
```

## Self Research Refresh

Refresh the system's own understanding of what to update next:

```bash
cd O:/Foundups-Agent && python scripts/refresh_self_research.py
```

Primary report:

- `modules/communication/moltbot_bridge/workspace/reports/openclaw_self_research_status.json`

This consolidates:
- HoloIndex freshness and refresh attempts
- WSP compliance findings
- daemon self-audit recurrence
- grant watchlist changes and errors
- ranked autonomous tasks written into `AgentDB`

## What Gets Monitored

| Component | Status Source | Checks |
|-----------|-------------|--------|
| WRE Master Orchestrator | `wre.get_metrics()` | State, coherence, patterns, plugins |
| Libido Monitor | `wre.libido_monitor` | Pattern frequency, throttle status |
| Pattern Memory | `wre.sqlite_memory` | Outcome storage, fidelity scores |
| Skills Loader | `wre.skills_loader` | Discovered skills count |
| AI Overseer | `dae.overseer` | Agent coordination status |
| Permission Manager | `dae.permissions` | Autonomy tier enforcement |
