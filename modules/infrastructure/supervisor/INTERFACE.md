# Supervisor Module Interface

## Public API

### Supervisor24x7

Main supervisor class.

```python
class Supervisor24x7:
    def __init__(self, repo_root: Path):
        """Initialize supervisor with repository root path."""

    async def run(self) -> None:
        """Start the main state machine loop. Runs until stop() is called."""

    async def stop(self) -> None:
        """Signal graceful shutdown."""

    def get_state(self) -> SupervisorState:
        """Return current state."""

    def get_metrics(self) -> Dict[str, Any]:
        """Return telemetry metrics."""
```

### SupervisorState

Enum of all 10 states.

```python
class SupervisorState(Enum):
    BOOT = "boot"
    PREFLIGHT = "preflight"
    OBSERVE = "observe"
    TRIAGE = "triage"
    PLAN = "plan"
    EXECUTE = "execute"
    VERIFY = "verify"
    REMEMBER = "remember"
    ESCALATE = "escalate"
    IDLE_WATCH = "idle_watch"
```

### SupervisorMetrics

Telemetry dataclass.

```python
@dataclass
class SupervisorMetrics:
    cycles_completed: int
    events_observed: int
    fixes_attempted: int
    fixes_succeeded: int
    escalations_triggered: int
    last_state_change: float
    state_durations: Dict[str, float]
```

### TriageTask

Task queued for execution.

```python
@dataclass
class TriageTask:
    event_signature: str
    source_file: str
    recommended_fix: str
    auto_fixable: bool
    priority: int = 1
    timestamp: float
```

## Integration Points

| Component | Import Path | Usage |
|-----------|-------------|-------|
| DaemonSelfAuditLoop | `modules.infrastructure.wre_core.src.daemon_self_audit_loop` | OBSERVE/TRIAGE/ESCALATE |
| AIIntelligenceOverseer | `modules.ai_intelligence.ai_overseer.src.ai_overseer` | PLAN |
| WREMasterOrchestrator | `modules.infrastructure.wre_core.wre_master_orchestrator.src.wre_master_orchestrator` | EXECUTE |
| SQLitePatternMemory | `modules.infrastructure.wre_core.src.pattern_memory` | REMEMBER |
| GemmaLibidoMonitor | `modules.infrastructure.wre_core.src.libido_monitor` | VERIFY |
