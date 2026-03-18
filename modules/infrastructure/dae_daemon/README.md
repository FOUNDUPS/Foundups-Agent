# dae_daemon - Centralized DAEmon (Cardiovascular System)

Central monitoring and control daemon for all Domain Autonomous Ecosystems (DAEs).

## Architecture

```
CentralDAEmon (Layer 4 - singleton)
  |-- EventStore (Layer 1 - JSONL + SQLite dual-write)
  |-- DAERegistry (Layer 2 - registration, heartbeat, state)
  |-- Killswitch (Layer 3 - security detach + PID termination)
  |-- DAELaunchBroker (runtime activation for launchable DAEs)

CentralDAEAdapter (Layer 5 - non-invasive integration)
  |-- Any existing DAE uses this to register, no class hierarchy changes
```

## Usage

### For existing DAEs (non-invasive):
```python
from modules.infrastructure.dae_daemon.src.dae_adapter import CentralDAEAdapter

adapter = CentralDAEAdapter(dae_id="my_dae", dae_name="My DAE", domain="communication")
adapter.register()
adapter.report_started()
adapter.start_heartbeat(health_fn=lambda: {"cpu": 0.3})

# Report cardiovascular events
adapter.report_message_in("012", "hello")
adapter.report_message_out("012", "greetings")
adapter.report_action("process", "task_123", "completed")

# On shutdown
adapter.stop()
```

### For the CLI (dashboard):
Menu option 17 in `python main.py` shows the DAE Dashboard with:
- All registered DAE states ([OK] running, [--] stopped, [XX] detached)
- Enable/disable individual DAEs
- Killswitch reports

### For runtime activation:
```python
from modules.infrastructure.dae_daemon.src.dae_launch_broker import (
    DAELaunchSpec,
    get_dae_launch_broker,
)

broker = get_dae_launch_broker()
broker.register_launch_spec(
    DAELaunchSpec(
        dae_id="pqn_research",
        dae_name="PQN Research Session",
        domain="ai_intelligence",
        start_callable=run_pqn_research_session,
    )
)
broker.start_dae("pqn_research", actor_id="012")
```

Runtime intent:
- `main.py` bootstraps launchable specs
- OpenClaw or another controller asks broker to `start/status/stop`
- Central DAEmon remains the canonical lifecycle ledger

Resident OpenClaw path:
- `main.py` now registers `openclaw` as a launchable broker-managed DAE
- the resident service uses the existing OpenClaw webhook receiver surface
- default bootstrap can autostart it after startup preflights

### For live supervision:
```python
from modules.infrastructure.dae_daemon.src.dae_observer import get_dae_observer

observer = get_dae_observer()
tail = observer.tail_events(dae_id="openclaw", limit=8)
snapshot = observer.get_live_status("pqn_research", limit=8)
```

Runtime supervision intent:
- `tail <dae>` -> recent DAEmon event stream for that DAE
- `status <dae> live` -> registry state + runtime status + recent event tail
- `watch <dae> since <sequence>` -> cursor-based incremental follow from a known event id
- The event store remains the source of truth; the observer is read-only

## Security Killswitch

- 1 CRITICAL event = immediate detach
- 3+ HIGH events in 5 min = detach
- WARNING = log only
- Detached DAEs are disabled (must be manually re-enabled by 012)

## Files

| File | Layer | Purpose |
|------|-------|---------|
| `src/schemas.py` | 0 | Pure data (enums, dataclasses) |
| `src/event_store.py` | 1 | JSONL + SQLite dual-write |
| `src/dae_registry.py` | 2 | Registration, heartbeat, state |
| `src/killswitch.py` | 3 | Security detach + PID kill |
| `src/dae_daemon.py` | 4 | Singleton daemon (composes 1-3) |
| `src/dae_adapter.py` | 5 | Non-invasive adapter for DAEs |
| `src/dae_launch_broker.py` | 5 | Runtime launch broker for on-demand DAE activation |
| `src/dae_observer.py` | 5 | Read-side observer for live status and event tails |

## WSP Compliance

- WSP 3: Infrastructure domain
- WSP 49: Standard module structure
- WSP 72: Layer isolation (each layer only imports lower layers)
- WSP 84: Reuses FAMEventStore / FAMDaemon patterns
