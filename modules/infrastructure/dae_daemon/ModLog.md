## 2026-09-22: Noncreating observer runtime lookup

- WSP00/6/10/15/22/49/50/62/97; C2/I3/D3/Impact3=11/P2. Extend existing broker singleton with a noncreating accessor, used only by observer runtime lookup. Capture under singleton lock, invoke status after release; no new scheduler/module.
- Baseline4fail/4pass; repaired and independent8pass on identical frozen cases;19 original cases unchanged and not selected. Finite absent/present/replacement/error and creating-getter compatibility controls; no real service, broker/daemon construction, default database or provider.
- Existing creating/reset functions and broker class remain unchanged. Default observer/adapter ingress still has effects; no global isolation, live runtime readiness or retained RSI claim. Exact source, package, review and publication evidence belongs to the canonical RSI backlog.

## 2026-09-22: Truthful broker stop acknowledgment

- WSP00/10/15/22/49/50/62/91/97; C3/I3/D3/Impact3=12/P2. The existing broker distinguishes accepted stop requests from observed worker exit, binds the active handle's hook and rejects changed ownership across callbacks.
- Fixed baseline:25failed/26passed; candidate and independent replay:51passed (same cases). Existing13 import cases retained; three threaded lifecycle cases deselected, with only the legacy stop-status expectation updated for the new contract.
- Callbacks stay outside broker locks; finite replacement tests do not prove atomic publication against arbitrary concurrent registry writers. No stop/join/kill scheduler or runtime update authority added. Canonical backlog records source, package checks, review and publication.

## 2026-09-22: Preserve broker import-failure streaks

- WSP00/10/15/22/49/50/62/91/97; C3/I3/D3/Impact3=12/P2. Existing broker counter now survives repeated caught import errors and reaches threshold3; successful full launch handling or a caught non-import exception resets only the affected DAE.
- Preserve broad existing catch, events/finally, disabled admission and manual re-enable semantics. Same-file failure-transition extraction shrinks inherited class and oversized method; no new broker/module or process authority.
- Fixed baseline:9failed/4passed; candidate and independent replay:13passed, original3 lifecycle methods unchanged/deselected. Inert fixtures only; no service, real thread, provider or default database.
- Corrects the historical V1.2.5 completion claim below; no measured live crash-loop/noise improvement is asserted. Exact source, manifest, checks and closure are in the canonical RSI backlog. Re-score after closure.

# dae_daemon ModLog

## 2026-09-22: Qualify persistence and acknowledgment boundaries

- WSP00/10/11/15/22/50/62/97; C3/I4/D4/Impact4=15/P1. Existing observer test owner gains seven ordinary characterizations of six boundaries; no production source, schema or callback policy changes.
- Sixteen selected cases pass locally and independently, with original nine retry functions and three observer methods unchanged. Three observer methods deselected; two configuration warnings. Same cases overlap across runs.
- Distinguish SQLite record truth, JSONL attempt history, ambiguous false results, unclassified duplicate conflicts, count-only parity and volatile registry acceptance. Returned store failure preserves existing listeners; raised store exception does not. Emergency spies have no live effects.
- WRE/FAM comparison remains source evidence. Future repairs require stronger declared acceptance on fixed fault inputs; characterization is not permission to retain defective behavior or call the system durable.
- Coordinator, worker and verifier each completed explicit WSP00 bootstrap/gate with separate evidence before their work. This is repository bootstrap evidence, not an unmeasured model capability claim.
- PR1854 merge/main checks and owned worktree retirement are reconciled; its three temporary directories remain policy-blocked and untouched. Current publication/closure and re-scoring belong to the canonical backlog.

## 2026-09-22: Remove event-store sequence-collision deadlock

- WSP00/10/11/15/22/50/62/97; C3/I4/D4/Impact4=15/P1. Extend only the existing `DAEEventStore.write` owner and observer test file; no new module, scheduler or persistence schema.
- Disposable baseline reproduced recursive non-reentrant lock acquisition under a real sequence collision. The same nine fixed regression oracles gave5pass/4fail before repair and9pass after. Retry now stays inside one lock acquisition, preserving retry budgets, tuple results, dedupe and JSONL-before-SQLite ordering.
- Ordinary focused pytest9pass/3deselected; independent verification and exact-head publication are separately recorded in the canonical RSI backlog. The three existing observer methods remain unchanged and were not run. Two pytest configuration warnings reflect disabled plugin autoload.
- Broader candidate process-witness review was blocked by automatic screening; that harness remains paused. Ordinary source review/unit validation is a narrower evidence path, not a screening override or candidate production-lock replay claim.
- JSONL partial/duplicate attempts and volatile registry notifications remain observed gaps. No atomic durability, registry acknowledgment, native admission, reward settlement, service activation or retained RSI improvement is claimed.
- Source332→333lines/class310→311; write32lines. Inherited class-size review debt remains open in the mirrored WSP module log; qualify cohesive persistence/recovery ownership before further growth.

## 2026-09-22: Reconcile scalable RSI monitoring and confirmed controls

- WSP00/10/15/22/50/77/91/97; source/document reconciliation C3/I4/D4/Impact4=15/P1. Extend the existing daemon architecture map and R18/R23 obligations; no new monitor, scheduler, packet, skill or runtime schema.
- Distinguish heartbeat/progress, requested/confirmed control, durable acknowledgment and independent acceptance/retention. Static event-store collision/partial-write, registry acknowledgment, scan-health and stop-confirmation findings remain unqualified runtime gaps.
- Build supervision beside each layer before promotion; existing WRE/AgentDB retain authority, small-model advice requires bounded evaluation, and 1→2→10→100→1000 capacity requires measured independent gates. Prototype YouTube restart/announcement instructions are not executed.
- Prior PR1852 closure is reconciled in the backlog; next evidence-integrity qualification15/P1 precedes role15/P1, while native18/P0 remains blocked. This sprint changes documentation only; exact validation/review/publication evidence is recorded separately, with no live activation or retained RSI claim.

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
