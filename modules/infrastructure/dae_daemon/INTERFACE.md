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

### Persistence result boundaries

- SQLite is the current query/dedupe record authority. Reopen loads its sequence state; it does not reconstruct SQLite from JSONL.
- JSONL records append attempts before SQLite. A false result may leave JSONL-only data; an exception after commit can also return false with a readable SQLite row.
- Exact and conflicting dedupe inputs currently share the duplicate result. Neither a false tuple nor `verify_parity()` establishes row absence or content agreement.
- `DAERegistry.report_event` reports local acceptance for a registered DAE, not durable storage. On a returned store failure listeners still run; a raised store exception currently prevents notification. Preserve this distinction when extending the existing emergency path.
- The existing WRE `event_store_verified` result is SQLite-only. Seven additional characterization cases qualify six boundaries without changing any public API or runtime behavior.

See the [system persistence qualification](../../../docs/DAEMON_ARCHITECTURE_MAP.md#persistence-and-acknowledgment-qualification--2026-09-22) for the evidence boundary and stronger future acceptance requirements.

### Broker import-failure streak

The broker preserves a per-DAE in-memory streak across launches. A caught
`ImportError` (including `ModuleNotFoundError`) increments it; at the existing
threshold of three the registry is marked `DETACHED` and disabled. Earlier
failures remain `CRASHED`. Disabled admission prevents another start.

The count resets only after the complete existing success path finishes, or
when that path catches a non-import `Exception`. The existing catch also covers
result summarization and success-event/state reporting, so this is an exception
classification, not proof of missing dependencies or callable-origin failure.
Manually re-enabling the registry does not reset the streak; another import
failure detaches again. No automatic enable, retry or recovery is introduced.

Interruptions outside `Exception` retain the count and propagate through the
existing final bookkeeping. Exceptions from pre-launch/failure/finally reporting
retain their prior propagation boundary. The count is neither durable nor a
health score; live restart behavior and broader concurrency
remain separate acceptance work.

### Broker stop acknowledgment

`stop_dae` reports `success: true, status: stopping` when the captured worker
remains alive after its stop hook returns. It reports `stopped` and publishes
`stop_completed` only after observing that captured worker exit. A successful
request is not a completed stop. The existing Holo controller independently
polls `thread_alive`; that stronger check remains required.

The stop hook is captured from the active handle's launch spec, so refreshing
a future launch spec does not redirect an existing worker's stop. Registry and
stop-hook callbacks run outside the broker lock. Ownership is checked across callback boundaries;
replacement or removal returns `runtime_changed` without subsequent stale
state/event publication. Missing/dead workers and unsupported stop hooks retain
their existing errors; same-owner hook failures retain their error handling.

The evidence covers finite callback changes and observed broker-thread state,
not atomicity against arbitrary concurrent registry writers or external process
termination. No wait/join/kill, automatic retry, new timeout or restart policy is
introduced. Reporting exceptions and persistence acknowledgment retain their
existing limitations.

## Data Persistence

- JSONL: `modules/infrastructure/dae_daemon/memory/dae_events.jsonl`
- SQLite: `modules/infrastructure/dae_daemon/memory/dae_audit.db`
