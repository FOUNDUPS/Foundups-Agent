# dae_daemon ModLog

## V1.2.5 - WSP 97 Circuit Breaker for Import Failures (2026-03-22)

**What**: Added circuit breaker pattern to stop crash loops from import-time failures.

**Why**: When a DAE fails to launch due to missing dependencies (e.g., `fastapi` not found because wrong Python environment), the broker would continuously retry, flooding logs with repeated exceptions. WSP 97 CoR (Chain of Reasoning) analysis identified this as an architectural gap.

**Changes**:
- `src/dae_launch_broker.py`
  - Added `_import_failures: Dict[str, int]` to track import failures per dae_id
  - Added `MAX_IMPORT_FAILURES = 3` constant
  - Circuit breaker logic: After 3 consecutive `ImportError`/`ModuleNotFoundError`, set state to `DETACHED` and call `disable()` to prevent restart attempts
  - Log verbosity reduction: First failure logs at ERROR level, subsequent failures at DEBUG
  - Clear failure count on successful launch (imports passed)

**Impact**:
- Crash loops from environment issues now auto-terminate after 3 attempts
- Log noise reduced by ~90% for repeated failures
- DAE enters DETACHED state with clear message: "install deps in venv"
- OpenClawSupervisor restart budget is preserved for runtime failures, not wasted on import failures

**WSP Compliance**: WSP 97 (CoT/CoR verification gates)

## V1.2.4 - Cursor-based observer follow mode (2026-03-18)

**What**: Added cursor-based follow semantics on top of the DAEmon event store.

**Why**: Recent-window snapshots were useful for inspection but not strong enough for incremental supervision. `WSP_97` needs a deterministic cursor contract that future control loops can resume from.

**Changes**:
- `src/event_store.py`
  - added `get_latest_sequence_id()`
- `src/dae_observer.py`
  - added `follow_events(...)`
  - added `latest_sequence_id` and `next_cursor` to live/system snapshots
- `README.md`
  - documented `watch <dae> since <sequence>` follow contract

**Impact**:
- DAEmon read surfaces can now return an explicit next cursor for incremental polling.
- This is the first clean step from ad hoc tails toward true 24/7 supervision.

## V1.2.3 - Resident OpenClaw registered as broker-managed runtime (2026-03-18)

**What**: Extended the runtime broker contract so OpenClaw itself can be treated as a launchable resident DAE instead of only a menu surface.

**Why**: `WSP_97` requires the control plane to exist as a real runtime lane. Without that, `openclaw` could be tailed and queried, but not bootstrapped as a first-class resident service.

**Changes**:
- `main.py`
  - registers `openclaw` launch spec during bootstrap
  - optional autostart after preflights
- `README.md`
  - documents the resident OpenClaw path through the broker

**Impact**:
- `openclaw` is now part of the broker-managed runtime inventory.
- The DAEmon lifecycle ledger can track the resident OpenClaw service as a real runtime instead of only its downstream events.

## V1.2.1 - Structured Action Details for Live Research Events (2026-03-16)

**What**: Extended the non-invasive `CentralDAEAdapter` so action events can carry structured details payloads.

**Why**: OpenClaw was already trying to emit structured research/runtime details through the action ledger, but the adapter signature still dropped them. That broke the intended real-time observability contract for PQN simulation runs.

**Changes**:
- Updated `src/dae_adapter.py`
  - `report_action(...)` now accepts optional `details`
  - preserves `details` inside the emitted `ACTION_PERFORMED` payload

**Impact**:
- OpenClaw research/runtime events can now carry machine-readable context into DAEmon.
- PQN simulation start/completion signals are visible as structured events rather than only flat text summaries.

## V1.0.0 - Centralized DAEmon (Cardiovascular System) (2026-02-17)

**What**: Created 8-layer centralized DAEmon module for monitoring and controlling all DAEs.

**Why**: 012 identified the need for a cardiovascular system — one place to observe all DAE actions, messages, and health. If a security violation occurs, the killswitch detaches the offending DAE and generates an investigation report.

**Architecture**:
- Layer 0: Schemas (DAEState, DAEEventType, SecuritySeverity, DAERegistration, DAEEvent, KillswitchReport)
- Layer 1: Event Store (JSONL + SQLite dual-write, adapted from FAMEventStore)
- Layer 2: DAE Registry (register, heartbeat, enable/disable, stale detection)
- Layer 3: Security Killswitch (PID tracking, emergency detach, policy rules)
- Layer 4: CentralDAEmon (singleton, heartbeat thread, composed from layers 1-3)
- Layer 5: DAE Adapter (non-invasive integration for existing DAEs)
- Layer 6: FAM DAEmon integration (~15 lines added to fam_daemon.py)
- Layer 7: main_menu.py integration (option 17: DAE Dashboard)

**WSP References**: WSP 3 (infrastructure domain), WSP 49 (module structure), WSP 72 (layer isolation), WSP 84 (reuses FAM patterns)

**Tests**: 50+ assertions across 6 test files (all passing)

**Files Created**:
- `src/schemas.py` (150 lines)
- `src/event_store.py` (200 lines)
- `src/dae_registry.py` (200 lines)
- `src/killswitch.py` (200 lines)
- `src/dae_daemon.py` (230 lines)
- `src/dae_adapter.py` (180 lines)

**Files Modified**:
- `modules/foundups/agent_market/src/fam_daemon.py` (+15 lines — central adapter)
- `modules/infrastructure/cli/src/main_menu.py` (+80 lines — dashboard + init)

## V1.1.0 - Activity Routing + DAE Wiring (2026-02-17)

**What**: Wired OpenClaw, SIM, and AI Gateway to the cardiovascular DAEmon.

**Why**: 012 asked "is OpenClaw 0102 agent state being announced in the DAEmon?" — it wasn't. Now it is.

**Changes**:
- `openclaw_dae.py`: Added CentralDAEAdapter, reports message_in (with intent classification) and message_out (with route + timing)
- `simulator/run.py`: Added CentralDAEAdapter with heartbeat (reports tick count), reports started/stopped lifecycle
- `ai_gateway.py`: Registered as DAE, reports model selection actions to dashboard

**DAEs Now Wired to Cardiovascular System**:
| DAE | Adapter | Reports |
|-----|---------|---------|
| FAM DAEmon | Yes (V1.0.0) | lifecycle, heartbeats |
| OpenClaw | Yes (V1.1.0) | message_in, message_out, intent classification |
| Simulator | Yes (V1.1.0) | lifecycle, heartbeats (tick count) |
| AI Gateway | Yes (V1.1.0) | model selection actions |

**WSP References**: WSP 72 (no cross-module dependency changes), WSP 91 (observability)

## V1.2.0 - Runtime DAE Launch Broker (2026-03-15)

**What**: Added a broker-managed runtime activation layer so a running system can start and inspect DAEs without re-entering the interactive menu.

**Changes**:
- Added `src/dae_launch_broker.py` with:
  - `DAELaunchSpec`
  - `DAERuntimeHandle`
  - `DAELaunchBroker`
  - singleton helpers for runtime consumers/tests
- Broker now supports:
  - `register_launch_spec(...)`
  - `start_dae(...)`
  - `stop_dae(...)`
  - `get_status(...)`
  - `list_launchable(...)`
- Broker writes lifecycle transitions back through the central registry/event store so DAEmon remains the canonical runtime ledger.
- Updated `README.md` to document the broker architecture and runtime usage.

**Impact**:
- `main.py` can register launchable DAEs during bootstrap.
- OpenClaw and other control surfaces can activate DAEs after startup.
- Runtime DAE launch no longer depends on fake menu input or restarting `main.py`.

## V1.3.0 - DAEmon Observer Read Surface (2026-03-17)

**What**: Added a read-side supervision layer over the central event store so OpenClaw and other controllers can tail recent events and request live runtime snapshots.

**Changes**:
- Added `src/dae_observer.py` with:
  - `tail_events(...)`
  - `get_live_status(...)`
  - `get_system_live_status(...)`
- Extended `src/event_store.py` with `query_recent(...)` for recent-window event reads.
- Updated `README.md` to document the observer as the canonical live supervision seam.

**Impact**:
- DAEmon is now both the write ledger and the read-side runtime surface.
- OpenClaw can expose real-time Claw/PQN supervision without scraping logs or bypassing the daemon.
