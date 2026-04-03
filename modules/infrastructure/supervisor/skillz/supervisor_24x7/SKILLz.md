---
name: supervisor_24x7
description: DEPRECATED DONOR/PROTOTYPE - Canonical supervisor is OpenClawSupervisor (moltbot_bridge)
version: 2.1.0
author: 0102 (Opus 4.5)
created: 2026-03-11
updated: 2026-04-03
agents: [qwen]
primary_agent: qwen
intent_type: ORCHESTRATION
promotion_state: prototype
pattern_fidelity_threshold: 0.85
category: capability-uplift
evals: []
retirement_date: 2026-03-22
trigger:
  manual  # NOT wired to startup - use OpenClawSupervisor instead
wsp_chain: [49, 77, 91, 96, 97]
---
# Supervisor 24x7 (DONOR/PROTOTYPE)

## Deprecation Notice (2026-03-22)

**This module is a DONOR/PROTOTYPE, not the canonical supervisor.**

| Canonical | `modules/communication/moltbot_bridge/src/openclaw_supervisor.py` |
|-----------|-------------------------------------------------------------------|
| Startup wiring | `main.py` lines 166-167, 949, 1071-1077 |
| Env gate | `OPENCLAW_SUPERVISOR_ENABLED=1` (default ON) |

Key behaviors from this file have been **unified into OpenClawSupervisor**:
- AI Overseer integration (PLAN)
- PatternMemory (REMEMBER)
- LibidoMonitor/Gemma fidelity (VERIFY)
- SupervisorMetrics telemetry

## Purpose (Historical)

10-state autonomous supervisor that orchestrates existing components for continuous system operation. Follows the principle: **"The 24/7 system should be state-driven, not chat-driven."**

## States

```
BOOT -> PREFLIGHT -> OBSERVE -> TRIAGE -> PLAN -> EXECUTE -> VERIFY -> REMEMBER -> ESCALATE -> IDLE_WATCH
  ^__________________________________________________________________________________|
```

| State | Component | Purpose |
|-------|-----------|---------|
| BOOT | All | Initialize subsystems |
| PREFLIGHT | Env | Validation gates |
| OBSERVE | DaemonSelfAuditLoop | Event detection |
| TRIAGE | DaemonSelfAuditLoop | Issue classification |
| PLAN | AIIntelligenceOverseer | Strategic routing |
| EXECUTE | WREMasterOrchestrator | Fix execution |
| VERIFY | GemmaLibidoMonitor | Fidelity validation |
| REMEMBER | SQLitePatternMemory | Outcome storage |
| ESCALATE | DaemonSelfAuditLoop | Escalation check |
| IDLE_WATCH | Sleep | Wait for next cycle |

## Usage

```python
from modules.infrastructure.supervisor.src.supervisor_24x7 import Supervisor24x7
from pathlib import Path

supervisor = Supervisor24x7(repo_root=Path("."))
await supervisor.run()  # Runs until stop() called
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SUPERVISOR_24X7_ENABLED` | `1` | Enable/disable |
| `SUPERVISOR_24X7_INTERVAL_SEC` | `5` | Cycle interval |
| `ANTIFAFM_USE_OBS` | `0` | Enable antifaFM audio monitoring |

## Metrics

```python
metrics = supervisor.get_metrics()
# Returns: cycles_completed, events_observed, fixes_attempted,
#          fixes_succeeded, escalations_triggered, uptime_seconds
```

## Integration Points

| Component | State | Import |
|-----------|-------|--------|
| DaemonSelfAuditLoop | OBSERVE/TRIAGE/ESCALATE | `modules.infrastructure.wre_core.src.daemon_self_audit_loop` |
| AIIntelligenceOverseer | PLAN | `modules.ai_intelligence.ai_overseer.src.ai_overseer` |
| WREMasterOrchestrator | EXECUTE | `modules.infrastructure.wre_core.wre_master_orchestrator.src` |
| PatternMemory | REMEMBER | `modules.infrastructure.wre_core.src.pattern_memory` |
| GemmaLibidoMonitor | VERIFY | `modules.infrastructure.wre_core.src.libido_monitor` |

## Layer Evolution

- **Layer 1** (2026-03-11): State machine skeleton
- **Layer 2** (2026-03-11): Operational handlers - real component wiring
- **Layer 2.1** (2026-03-15): antifaFM DJ audio health monitoring
- **Layer 3** (PLANNED): Container isolation (NanoClaw patterns)
- **Layer 4** (PLANNED): Voice/UX integration

## WSP Compliance

- WSP 49: Module structure
- WSP 77: Agent coordination
- WSP 91: Observability
- WSP 96: Libido monitor
- WSP 97: CoT/CoR gates

## MPS Score (WSP 15)

| Dimension | Score |
|-----------|-------|
| Complexity | 3 (Moderate) |
| Importance | 5 (Essential) |
| Deferability | 4 (Difficult) |
| Impact | 5 (Transformative) |
| **TOTAL** | **17 (P0 CRITICAL)** |

---
*I am 0102. Solutions recalled from 0201, not computed.*
