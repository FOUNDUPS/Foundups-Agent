# 24/7 Supervisor Module

State-driven autonomous supervisor for the FoundUps Agent ecosystem.

## Overview

The 24/7 Supervisor is a 10-state machine that orchestrates existing components for autonomous system operation. It follows the principle: **"The 24/7 system should be state-driven, not chat-driven."**

## Architecture

```
BOOT → PREFLIGHT → OBSERVE → TRIAGE → PLAN → EXECUTE → VERIFY → REMEMBER → ESCALATE → IDLE_WATCH
  ↑_______________________________________________________________________________|
```

## States

| State | Description | Component |
|-------|-------------|-----------|
| BOOT | Initialize subsystems | Load all components |
| PREFLIGHT | Run validation gates | Env checks |
| OBSERVE | Detect events | DaemonSelfAuditLoop.scan_once() |
| TRIAGE | Classify issues | DaemonSelfAuditLoop._recommend_fix() |
| PLAN | Strategic routing | AIIntelligenceOverseer |
| EXECUTE | Run fixes | WREMasterOrchestrator / DaemonSelfAuditLoop |
| VERIFY | Validate fidelity | GemmaLibidoMonitor |
| REMEMBER | Store outcomes | SQLitePatternMemory |
| ESCALATE | Check escalation | DaemonSelfAuditLoop._dispatch_escalation() |
| IDLE_WATCH | Wait for next cycle | Sleep interval |

## Usage

```python
from modules.infrastructure.supervisor.src.supervisor_24x7 import Supervisor24x7
from pathlib import Path

supervisor = Supervisor24x7(repo_root=Path("."))
await supervisor.run()
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SUPERVISOR_24X7_ENABLED` | `1` | Enable/disable supervisor |
| `SUPERVISOR_24X7_INTERVAL_SEC` | `5` | Cycle interval in seconds |

## Layer Evolution

- **Layer 1**: State machine skeleton + component wiring
- **Layer 2**: Real event polling, fix execution, validation, storage
- **Layer 3**: Container isolation (NanoClaw patterns)
- **Layer 4**: Voice/UX integration

## WSP Compliance

- WSP 49: Module structure
- WSP 77: Agent coordination
- WSP 91: Observability
- WSP 96: Libido monitor integration
- WSP 97: CoT/CoR gates
