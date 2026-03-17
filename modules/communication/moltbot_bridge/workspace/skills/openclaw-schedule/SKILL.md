---
name: openclaw-schedule
description: Schedule YouTube Shorts via Content Page Scheduler through WRE routing
user-invocable: true
command-dispatch: tool
command-tool: bash
command-arg-mode: raw
category: workflow
evals: []
---
# OpenClaw Schedule Skill

Schedule YouTube Shorts through the Content Page Scheduler via WRE routing.
Routes through OpenClaw DAE's SCHEDULE intent category with permission gating.

## Quick Schedule (CLI)

```bash
cd O:/Foundups-Agent && python -m modules.platform_integration.youtube_shorts_scheduler.scripts.launch --content-page --channel-key foundups
```

## Schedule via OpenClaw DAE

```bash
cd O:/Foundups-Agent && python -c "
import asyncio
from modules.communication.moltbot_bridge.src.openclaw_dae import OpenClawDAE
dae = OpenClawDAE()
result = asyncio.run(dae.process(
    message='Schedule videos for tomorrow at 3pm',
    sender='@UnDaoDu',
    channel='openclaw',
))
print(result)
"
```

## Calendar Audit

Check for scheduling conflicts and gaps:

```bash
cd O:/Foundups-Agent && python -m modules.platform_integration.youtube_shorts_scheduler.scripts.launch --audit --channel-key foundups
```

## Available Channels

| Channel Key | Channel | Schedule Window |
|------------|---------|----------------|
| foundups | Foundups | Per channel config |
| move2japan | Move2Japan | Per channel config |
| ravingantifa | RavingAntifa | Per channel config |
| undaodu | UnDaoDu | Per channel config |

## Permission Requirements

- **Viewing schedule**: ADVISORY tier (anyone)
- **Creating schedules**: METRICS tier (commander only)
- **Modifying schedules**: METRICS tier (commander only)

## Integration Notes

The SCHEDULE intent currently returns a routing message directing to the CLI.
Full automated scheduling via OpenClaw DAE is in development - the Content Page
Scheduler will be wired as an Associate DAE under WSP 73.
