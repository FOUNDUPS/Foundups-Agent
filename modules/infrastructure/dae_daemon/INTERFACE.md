# dae_daemon INTERFACE

## Public API

### CentralDAEmon (singleton)
```python
from modules.infrastructure.dae_daemon.src.dae_daemon import get_central_daemon

daemon = get_central_daemon()
daemon.start()
daemon.register_dae(registration)
daemon.enable_dae(dae_id)
daemon.disable_dae(dae_id)
daemon.get_dashboard() -> Dict
daemon.stop()
```

### CentralDAEAdapter (for existing DAEs)
```python
from modules.infrastructure.dae_daemon.src.dae_adapter import CentralDAEAdapter

adapter = CentralDAEAdapter(dae_id, dae_name, domain)
adapter.register()
adapter.report_started(pid=None)
adapter.start_heartbeat(health_fn=None)
adapter.report_message_in(source, summary)
adapter.report_message_out(dest, summary)
adapter.report_action(action_type, target, result)
adapter.report_security_event(reason, severity)
adapter.stop()
```

### Schemas
```python
from modules.infrastructure.dae_daemon.src.schemas import (
    DAEState,           # REGISTERED, STARTING, RUNNING, DEGRADED, STOPPING, STOPPED, DETACHED, CRASHED
    DAEEventType,       # DAE_REGISTERED, DAE_HEARTBEAT, MESSAGE_IN, SECURITY_VIOLATION, etc.
    SecuritySeverity,   # INFO, WARNING, HIGH, CRITICAL
    DAERegistration,    # Registration dataclass
    DAEEvent,           # Event dataclass (deterministic IDs)
    KillswitchReport,   # Detach report dataclass
)
```

### DAEEventStore.write

`write(event: DAEEvent, _retry: int = 0) -> Tuple[bool, str]` keeps its existing
success `(True, "ok")`, duplicate `(False, "duplicate: <key>")` and error
`(False, "error: <details>")` results. By default, a SQLite sequence collision
gets at most four attempts within one lock acquisition. Other errors do not retry.
The internal `_retry` counter and duplicate behavior are unchanged.

JSONL still precedes SQLite: a failed attempt can leave an extra JSONL record.
This method does not promise atomic dual-store durability, exact-versus-conflicting
duplicate classification, or durable acknowledgment through registry listeners.
Those limitations remain explicit in the system supervision map.

## Data Persistence

- JSONL: `modules/infrastructure/dae_daemon/memory/dae_events.jsonl`
- SQLite: `modules/infrastructure/dae_daemon/memory/dae_audit.db`
