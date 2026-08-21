# OpenClaw DAE and ExecutionBundle interface archive

This historical interface detail moved from the module `INTERFACE.md` during
the WSP 62 bounded-document repair. The active authority remains the module
interface and current source contracts.

## OpenClaw DAE (Frontal Lobe)

```python
from modules.communication.moltbot_bridge.src.openclaw_dae import OpenClawDAE

dae = OpenClawDAE(repo_root=Path("O:/Foundups-Agent"))
response = await dae.process(
    message="What is the WRE orchestrator?",
    sender="user123",
    channel="telegram",
    session_key="session-id",
    metadata={},
)
```

The full autonomy loop is ingress, intent, preflight, plan, permission,
execute, validate, and remember.

## 2026-03-28 operating contract

Per WSP 77, OpenClaw is a bounded execution surface, not the primary architect:

- `0102`: architecture authority, prioritization, and review
- `OpenClaw / Kohi`: bounded maintenance execution
- `HoloIndex`: retrieval bundle for direction and available subroutines
- `WRE`: deterministic execution plane

The use case covers simple codebase fixes, focused checks, runtime events, and
durable reports or knowledge artifacts. The execution contract is:

`assigned work -> retrieve bounded HoloIndex bundle -> execute -> verify -> emit -> remember`

## ExecutionBundle (WSP 87/97)

```python
from modules.communication.moltbot_bridge.src.openclaw_execution_bundle import (
    ExecutionBundle,
    build_execution_bundle,
    retrieve_bundle_for_memory_query,
)

bundle = build_execution_bundle(
    query="find test fixtures",
    route="holo_index",
    limit=5,
    include_patterns=True,
    include_docs=True,
)
if bundle.is_actionable():
    pass

memory_bundle = retrieve_bundle_for_memory_query("decisions", topic="architecture")
```

Bundle fields are `query`, `route`, `docs`, `patterns`, `candidate_paths`,
`constraints`, `verification_hints`, `confidence`, `code_hits`, and `wsp_hits`.
The deterministic memory-query bundle uses confidence `0.9`.
