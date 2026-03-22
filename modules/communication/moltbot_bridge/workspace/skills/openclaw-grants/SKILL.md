---
name: openclaw-grants
description: Operate the 0102 grant workflow through OpenClaw using existing WRE, memory, and browser automation surfaces
user-invocable: true
command-dispatch: tool
command-tool: bash
command-arg-mode: raw
category: workflow
evals: []
---
# OpenClaw Grants Skill

Use this skill when 0102/OpenClaw should actively do grant work instead of only producing research notes.

## WSP 97 Resolution

Grant operations are an execution-plane task.

Apply the canonical sequence:

`follow wsp := retrieve wsp -> resolve execution plane? -> apply cot -> apply cor -> execute`

For grant work that means:

1. Retrieve the grant target sheet and master packet
2. Resolve that OpenClaw/WRE/browser automation is the correct execution plane
3. Draft the application and supporting evidence
4. Prefill browser forms where possible
5. Stop only at human-only gates

## Required Artifacts

- `docs/external_research/WEB3_GRANTS_0102_SHORTLIST_2026-03-21.md`
- `docs/external_research/0102_GRANT_PACKET_MASTER_2026-03-22.md`
- `modules/communication/moltbot_bridge/workspace/reports/web3_grants_0102_target_sheet_20260321.json`
- `modules/communication/moltbot_bridge/workspace/reports/web3_grants_0102_wsp97_rescored_20260322.json`
- `modules/communication/moltbot_bridge/workspace/reports/web3_grants_0102_watchlist.json`

## Use Cases

### Rank what to apply to next

```bash
cd O:/Foundups-Agent && python -c "
import json
from pathlib import Path
path = Path('modules/communication/moltbot_bridge/workspace/reports/web3_grants_0102_wsp97_rescored_20260322.json')
data = json.loads(path.read_text(encoding='utf-8'))
for group_name, items in data['priority_groups'].items():
    print(f'\\n[{group_name}]')
    for item in items:
        print(f\"- {item['name']} :: {item['repo_blockchain_fit']}\")
"
```

### Refresh the official-source watchlist

```bash
cd O:/Foundups-Agent && python scripts/refresh_grant_watchlist.py
```

### Run OpenClaw on a grant task

```bash
cd O:/Foundups-Agent && python -c "
import asyncio
from modules.communication.moltbot_bridge.src.openclaw_dae import OpenClawDAE
dae = OpenClawDAE()
result = asyncio.run(dae.process(
    'follow wsp draft an Ethereum ESP application from the 0102 grant packet and target sheet',
    '012',
    'openclaw',
))
print(result)
"
```

### Prepare a browser-prefill mission

```bash
cd O:/Foundups-Agent && python -c "
import asyncio
from modules.communication.moltbot_bridge.src.openclaw_dae import OpenClawDAE
dae = OpenClawDAE()
result = asyncio.run(dae.process(
    'follow wsp prepare browser prefill steps for the Solana grant application using the master packet',
    '012',
    'openclaw',
))
print(result)
"
```

## Execution Rules

- Use existing modules before inventing new ones
- Read the WSP 97 rescored sheet before picking a grant
- Start with `apply_now` items
- Prefer grants that match implemented or near-term repo capability
- Tailor to the target ecosystem instead of reusing a generic answer
- Prefer repo evidence and architecture references over slogans
- Refresh the watchlist before making a new application push
- Record new findings in workspace memory or HoloIndex PatternMemory

## Human-Only Gates

OpenClaw should do the work up to the edge of irreversible submission.

Keep human approval for:
- KYC
- identity assertions
- wallet signing
- final binding submit clicks when terms are legally material

## Success Condition

The skill is successful when 0102/OpenClaw has:

1. selected the next best grant from the target sheet
2. drafted the application from the master packet
3. assembled the evidence set
4. prepared the browser execution path
5. handed off only the final human-only gate
