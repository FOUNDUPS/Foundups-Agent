# Daemon Architecture Map

**Created By:** 0102
**Date:** 2025-12-03
**WSP References:** WSP 27 (Universal DAE), WSP 80 (DAE Coordination), WSP 91 (Observability)

---

## RSI and WRE supervision contract — 2026-09-22

**Audit baseline:** `3c45509c0716cbac403d3309ea4d8a03ab13a2d2`; retry repair base `9103ec35d50495fd37690e48e442025372fac6e5`.
**Status:** sequence-collision source repair locally validated; broader runtime qualification remains open.
This section is the current supervision map linked by the [system roadmap](../ROADMAP.md).
It extends R18 capacity and R23 sustained operations across R06–R19/R24;
it creates no new scheduler, runtime schema, monitor module or executable authority.
The older inventory below records 2025 architecture and proposals, not current
runtime verification or permission for direct event-triggered effects.

012 uses **Digital Autonomous Agent Monitor** for this cross-layer function.
[WSP 91](../WSP_framework/src/WSP_91_DAEMON_Observability_Protocol.md) historically
expands DAEMON as Domain Autonomous Entity MONitoring. Preserve that history and
existing `dae_daemon` names; the requested function composes existing owners.

### Existing owners and actual gaps

Paths below are relative to the repository root. Source/test inventory is not a
passing test claim. The initial map was documentation-only; the bounded retry checkpoint below adds disposable event-store tests without starting services.

| Responsibility | Existing owner | Current boundary / required qualification |
|---|---|---|
| Lifecycle events, registry, snapshots | `modules/infrastructure/dae_daemon/src/{dae_daemon,dae_registry,dae_adapter,dae_observer}.py` | Reuse CentralDAEmon. State, heartbeat, event cursor and runtime view exist; they do not prove task progress, durable admission or accepted output. |
| Durable event evidence | `modules/infrastructure/dae_daemon/src/event_store.py` | `write` still appends JSONL before SQLite. Disposable baseline reproduced its recursive lock deadlock; bounded retry now stays within one lock acquisition and nine fixed regressions pass. Failed attempts can still leave extra JSONL records. Atomicity, crash/reopen, cross-process ordering and durable caller acknowledgment remain unqualified; no observed production incident is claimed. |
| Event acknowledgment | `modules/infrastructure/dae_daemon/src/dae_registry.py::_emit` | Ignores the store write result before notifying listeners. Qualify failed persistence, duplicate identity and listener acknowledgment before using notifications as durable evidence. |
| Launch, stop and detach | `modules/infrastructure/dae_daemon/src/dae_launch_broker.py`, `killswitch.py` | `stop_dae` reports STOPPED after the stop callable returns without confirming worker exit. Registry `disable` changes a flag. Import-failure count resets before the start callable; qualify repeated callable ImportError. No global restart/kill authority follows from a monitor alert. |
| Observation effects | `modules/infrastructure/dae_daemon/src/dae_observer.py::_get_runtime_status` | Lazy broker retrieval can create its heartbeat thread. Read-side APIs are not yet proved effect-free; use source inspection/disposable fixtures until side effects are qualified. Missing runtime data must remain unknown. |
| Admission, claims, leases, assurance | `modules/infrastructure/database/src/agent_db.py` and current OpenClaw supervisor | Existing signed-worker lease/heartbeat/recovery owners remain authoritative. CentralDAEmon does not grant work or override expiry/quarantine. Reserve independent verifier capacity. |
| RSI self-audit and native supervisor | `modules/infrastructure/wre_core/src/daemon_self_audit_loop.py`; `modules/communication/moltbot_bridge/src/openclaw_supervisor.py` | Audit scan exceptions are swallowed/logged without a distinct health projection; zero events cannot prove a successful scan. A broker heartbeat for a live thread cannot prove useful progress. Preserve native valve reason codes and absent effect lease. |
| Skill outcomes and bounded advice | WRE `pattern_memory.py`, `libido_monitor.py`, existing monitor/AI Overseer owners | Reuse outcome storage and existing sensors. Proposed variants, confidence and local logs are not independent acceptance, activation or retained improvement. No verified generic small-model supervisor pool is established here. |
| Telemetry intake and pressure | `modules/ai_intelligence/ai_overseer/src/{mcp_integration,holo_telemetry_monitor,ai_overseer}.py` | Queue, file reads and dedupe set are unbounded; critical-module to WRE mapping remains TODO. Qualify overload, rotation, failed enqueue and replay before scaling. Existing code and diagnostic callers are not proof of a running production consumer. |
| Worker execution and rewards | Current OpenClaw/Hermes contracts; FAM `task_pipeline.py` and persistent adapter | Correlate artifacts and verdicts with current authority. PR1852 locally qualifies atomic SQLite pending initiation; pending is not paid, authenticated role authority or native RSI proof. |

The [daemon tests index](../modules/infrastructure/dae_daemon/tests/README.md)
contains coverage targets that exceed the present test inventory. Launch broker,
observer, adapter, schemas and runtime-emitter test files exist. The retry sprint
extends the existing observer test file with nine store regressions; it creates no
parallel test owner. Original observer tests were not run in this bounded slice.
The candidate process-witness review was blocked by automatic screening, so only
ordinary source review/unit replay is claimed for the repair. Broader proof remains open. The [WRE roadmap](../modules/infrastructure/wre_core/ROADMAP.md)
records the narrower verified per-counter SQLite handle repair separately.

### A monitor is required beside every execution layer

Before promoting a layer, bind its existing producer, consumer and control owner
and independently test the following contract. These are acceptance requirements,
not newly implemented fields or a blanket claim that all owners support them.

1. **Identity and freshness:** correlate existing FoundUp, ticket/job, attempt,
   parent/dependency, role, source/runtime/profile generation, lease and artifact
   identifiers. Bind control request/acknowledgment and verifier/activation/rollback
   receipts. Record event sequence, observation age and observation error explicitly.
   Reuse existing identities; qualify missing mappings before extending a schema.
2. **Progress:** report heartbeat age separately from last verified progress,
   stage deadline and lease validity. A live thread may be stalled. Absent data,
   stale data, failed scan and a successful scan with zero findings are distinct.
3. **Control truth:** distinguish desired state, request accepted, effect observed,
   effect confirmed and failure/unknown. Disable is not stop; a kill request is not
   confirmed exit. Require bounded timeout and owner-specific confirmation, with
   idempotency/replay handling. A process ID alone is not durable worker identity.
4. **Evidence integrity:** distinguish inserted, exact duplicate, conflicting
   duplicate and rejected/failed persistence. A listener notification is not a
   storage receipt. Qualify collision, partial write, crash/reopen, retry, cursor
   gaps, ordering and durability; never silently manufacture success after loss.
   Preserve volatile emergency/killswitch notification under its existing authority
   while labeling it separately from durable acknowledgment. Best-effort
   `runtime_emitter.py` JSONL diagnostics are a different contract from the store.
5. **Capacity and cost:** bound queued/admitted/running work, parent/child fanout,
   retries, token/spend/time limits and verifier backlog separately. Unknown cost
   stays unknown, not zero. Apply backpressure before exhausting verification or
   audit storage; expose dropped/coalesced observations and lag.
6. **Quality and learning:** preserve independent verdict, fixed test oracle,
   rejected output, activation capability, rollback result and later retained-use
   evidence. Completion, acceptance, promotion, retention and reward settlement
   are separate facts. Monitor alerts must never change evaluation criteria.

Deterministic checks run first: authorization/scope/lease, deadlines, replay,
budget, persistence acknowledgment, test verdict and confirmed control outcomes.
Optional small-model agents can classify ambiguous alerts, summarize redacted
evidence and propose an existing WSP15 ticket. They cannot grant admission, change
the evaluator, promote their repairs, issue payments or restart other workers.
Use bounded shared capacity or sharding only after qualification, not one model
process per worker. Predeclare accuracy, false alarms, latency and cost acceptance;
fall back to deterministic unknown/hold when the model is absent or unreliable.

The existing [Unicode monitor prototype](../.agents/skills/unicode_daemon_monitor_prototype/SKILL.md)
is YouTube-specific and declares `evals: []`. Its restart and announcement examples
are not an approved general RSI controller. Evaluate only relevant detection
patterns in isolation; do not execute its live commands as part of this plan.
WSP48 edge/Gemma proposal contracts likewise do not prove a deployed supervisor.

### Authority, privacy and monitor failure

Monitoring is an observation/control view over existing WRE/AgentDB and launch
owners. It is not another queue for effects. Advisory proposals re-enter normal
admission and independent verification. Each actual control needs current owner,
scope, generation, budget, expiry and recovery policy; the monitor cannot sign its
own authority. Keep requested control distinct from its eventual acknowledgment.

Use allowlisted summaries, opaque correlation IDs, reason codes and evidence
references. Do not copy secrets, raw private Gmail/LinkedIn correspondence or
hidden model reasoning into telemetry. Preserve FoundUp/tenant isolation, bounded
retention and access controls. Critical control/audit evidence cannot be silently
sampled away; storage pressure must surface before new admission is authorized.

The monitor itself needs a bounded, independent host/process/lease health check
and alerts with delivery acknowledgment. Check scan freshness, store failures,
queue lag and telemetry delivery separately from target health. Do not build an
infinite chain of model watchers. A monitoring failure should inhibit new work
under a qualified owner policy; running work follows its bounded lease and existing
cancellation owner. It must not trigger blind global kills or service restarts.

### Layered implementation and scale gates

| Layer | Smallest next proof | Gate before advancing |
|---|---|---|
| 0: evidence foundation | Qualify the existing central event-store collision/partial-write/acknowledgment paths in disposable fixtures; confirm observation effects and missing-data semantics. | Reproducible baseline, fixed negative oracles, independent review; repair only the proven owner defect. No live services. |
| 1: one component | Bind one existing ticket lifecycle to fresh progress, lease and control outcomes; test scan failure, stalled thread, stale heartbeat and lost acknowledgment. | Read/control scopes proven; confirmed stop/cancel/recovery; no authority invented by projection. |
| 2: one admitted ticket | Existing WRE → OpenClaw/Hermes → independent verifier → authorized outcome/retention chain. | Native trust anchors and effect lease satisfied; complete correlated receipts and bounded failure/recovery. Simulation alone cannot pass native admission. |
| 3: two, then ten workers | Isolated lanes, dependency/fanout limits, duplicate claims, stale owner, saturation and verifier reservation. | Measured queue/store/verifier throughput and cost, bounded retries, fault recovery and no ownership collisions. No automatic doubling. |
| 4: one hundred, then one thousand | Qualify partitioned observation and bounded shared advisory capacity using existing scheduling owners. | Predeclared capacity/latency/error/spend limits and independent sustained-run evidence. Agent count is not demonstrated capacity. |

Build the monitoring contract **alongside each layer, before its promotion**, not
after the thousand-agent launch. Component fault qualification can proceed now;
native execution remains blocked by its own authority/runtime prerequisites.
Do not automatically execute RSI cycles from `main.py` or convert a startup report
into admission. Follow the existing WRE launch/evaluation sequence.

**Layer handoff checklist:** exact owner and source; scoped work order; fixed test
oracle and negative cases; producer/consumer correlation; progress/freshness and
control confirmation; authority/privacy boundary; rollback and monitor-failure
behavior; independent result; next action in the existing roadmap/ModLog/backlog.
No layer is operationally complete merely because its happy-path test passes.

### Current WSP15 selection and WSP97 disposition

The architecture reconciliation is closed in PR1853. The existing retry-method
repair is C3/I4/D4/Impact4 = **15/P1**, with fixed baseline failures, independent
source review and bounded local tests; exact publication status is in the backlog.
Re-observation selects authoritative-store/recovery/acknowledgment qualification
at **15/P1** before any persistence redesign. Partial writes are now demonstrated
in disposable fixtures; volatile emergency listeners must remain available even
when durable storage fails. No full monitoring/runtime completion is claimed.

The native ticket remains **18/P0 blocked** by current trust anchors/absent effect
lease. Persistent role/caller-authority qualification remains **15/P1 outstanding**;
PostgreSQL parity **13/P1** remains separately unqualified; LinkedIn **13/P1** is
separately owned. Re-observe all candidates after this sprint. Do not simply take
the old second-ranked item or revive the old unified event-queue proposal below.

---

## Historical architecture inventory and proposals — 2025-12-03

The following material is preserved for lineage. Revalidate its owners, test
claims and event-effect proposals against the current contract above before use.

## Overview

This document maps all daemons in the Foundups-Agent ecosystem, their capabilities, and event-driven orchestration patterns.

**Goal:** Enable autonomous daemon chaining via event queue for cross-system workflows (e.g., YouTube !bug command → AI Overseer log investigation → acknowledgment).

---

## Daemon Inventory

### 1. HoloDAE (File Monitoring & WRE Skills)

**Location:** `holo_index/qwen_advisor/holodae_coordinator.py`

**Capabilities:**
- File change monitoring (FileSystemWatcher)
- WRE Skills execution (SkillExecutor)
- MCP server coordination (MCPIntegration)
- Pattern memory false-positive filtering
- Module health tracking (ModuleMetrics)
- PID detection for process monitoring
- Breadcrumb tracing for recursive learning
- JSONL telemetry emission

**Monitoring Loop:**
```python
# monitoring_loop.py lines 173-200
def _run_monitoring_cycle(self) -> MonitoringResult:
    cycle_start = time.perf_counter()
    changes = self.file_watcher.scan_for_changes()
    file_changes = [self._build_file_change(path) for path in changes]

    result = MonitoringResult(
        changes_detected=file_changes,
        scan_duration=time.perf_counter() - cycle_start,
        watched_paths=self.file_watcher.get_watched_paths()
    )

    # Analyze context, update module metrics, trigger skills
    # ...
```

**Event Sources:**
- File system changes (inotify/watchdog)
- Manual skill execution requests
- MCP tool invocations

**Event Sinks:**
- JSONL telemetry files (holo_index/logs/telemetry/*.jsonl)
- Skill execution results
- Module health reports

**Integration Points:**
- WRE Skills Wardrobe (WSP 96)
- MCP Manager (modules/infrastructure/mcp_manager)
- Pattern Memory (modules/infrastructure/wre_core/src/pattern_memory.py)

---

### 2. GitPushDAE (Autonomous Git Commits & Social Media)

**Location:** `modules/infrastructure/git_push_dae/src/git_push_dae.py`

**Capabilities:**
- Autonomous commit decision-making (quality, timing, social value)
- Auto-generated commit messages
- Git push automation
- Social media posting (LinkedIn + X via GitLinkedInBridge)
- Push frequency throttling (30min minimum)
- Quality scoring (WSP compliance checks)

**Monitoring Loop:**
```python
# Daemon runs every 5 minutes (check_interval=300)
# Monitors uncommitted changes via `git status --porcelain`
# Assesses quality, social value, timing
# Makes autonomous push decision (5/7 criteria)
```

**Event Sources:**
- Uncommitted file changes
- Manual push triggers
- Time-based intervals (5 minutes)

**Event Sinks:**
- Git commits
- LinkedIn posts (company ID: 1263645)
- X posts (@FoundUps)
- Push decision logs

**Integration Points:**
- GitLinkedInBridge (modules/platform_integration/linkedin_agent/src/git_linkedin_bridge.py)
- SocialMediaEventRouter (modules/platform_integration/social_media_orchestrator/src/multi_account_manager.py) - **NOT INTEGRATED YET**
- social_accounts.yaml event routing

**Known Gap:** Manual commits bypass GitPushDAE → no social posting. Solution: git post-commit hook → event queue.

---

### 3. Auto Moderator DAE (YouTube Chat Moderation)

**Location:** `modules/communication/livechat/src/auto_moderator_dae.py`

**Capabilities:**
- YouTube livestream detection (NO-QUOTA web scraping + API verification)
- Chat moderation (spam detection, toxicity filtering)
- Qwen intelligence for smart moderation decisions
- WRE recursive learning (error/success tracking)
- YouTube telemetry storage (YouTubeTelemetryStore)
- Channel prioritization (QwenYouTube integration)
- Token refresh automation

**Monitoring Loop:**
```python
# WSP 27 DAE Phases:
# -1: Signal - YouTube chat messages
#  0: Knowledge - User profiles, chat history
#  1: Protocol - Moderation rules, consciousness responses
#  2: Agentic - Autonomous moderation and interaction
```

**Event Sources:**
- YouTube livestream start/end
- Chat messages
- User interactions (Super Chat, membership)

**Event Sinks:**
- Chat moderation actions (delete, timeout)
- Consciousness responses
- Telemetry database (SQLite)

**Integration Points:**
- StreamResolver (modules/platform_integration/stream_resolver)
- LiveChatCore (modules/communication/livechat/src/livechat_core.py)
- Qwen Monitor (holo_index/qwen_advisor/intelligent_monitor.py)
- WRE Integration (modules/infrastructure/wre_core/recursive_improvement/src/wre_integration.py)

---

### 4. YouTube Chat DAEmon (Real-Time Comment Dialogue)

**Location:** `modules/communication/video_comments/src/realtime_comment_dialogue.py`

**Capabilities:**
- Real-time comment monitoring (5-60 second intervals)
- Conversation thread management
- LLM-powered responses (Grok/Claude/GPT)
- Auto-like on reply (V5 Vision integration)
- User memory and personalization
- Engagement heuristics (questions, greetings, mentions)

**Monitoring Loop:**
```python
async def start(self):
    """Concurrent monitoring tasks"""
    await asyncio.gather(
        self.monitor_new_comments(),      # 5-60s intervals
        self.monitor_active_threads(),    # 5s rapid checks
        self.cleanup_inactive_threads()   # 60s cleanup
    )
```

**Event Sources:**
- New top-level comments
- Replies to 0102's comments
- Conversation timeouts

**Event Sinks:**
- YouTube API replies
- Browser-based likes (UI-TARS Vision)
- User memory updates

**Integration Points:**
- YouTubeActions (modules/infrastructure/browser_actions/src/youtube_actions.py)
- LLMCommentGenerator (Grok/Claude/GPT)
- Memory manager (user profiles)

**Note:** User mentioned "bug detection/repair" capabilities - **NOT FOUND** in realtime_comment_dialogue.py. May be referring to different module or future feature.

---

### 5. AI Overseer (Event Queue & Qwen/Gemma Coordination)

**Location:** `modules/ai_intelligence/ai_overseer/src/ai_overseer.py`

**Capabilities:**
- Event queue coordination (asyncio.Queue)
- Qwen strategic planning (200-500 tokens)
- Gemma pattern matching (50-100ms)
- MCP server management (Rubik DAEs)
- HoloDAE telemetry monitoring (HoloTelemetryMonitor)
- Mission coordination (WSP 77)
- Bell state consciousness verification

**Event Queue Architecture:**
```python
# mcp_integration.py line 100
self.event_queue: asyncio.Queue = asyncio.Queue()

# Current Flow:
# HoloDAE (writes JSONL) → HoloTelemetryMonitor (tail+parse) → AI Overseer event_queue
```

**Event Sources:**
- HoloDAE JSONL telemetry (module_status, system_alerts, search_request)
- MCP tool invocations
- Mission triggers

**Event Sinks:**
- Skill execution requests
- Pattern learning updates
- Daemon coordination commands

**Integration Points:**
- HoloTelemetryMonitor (modules/ai_intelligence/ai_overseer/src/holo_telemetry_monitor.py)
- MCPIntegration (modules/ai_intelligence/ai_overseer/src/mcp_integration.py)
- Rubik DAE MCP servers (Compose, Build, Knowledge, Community)

---

## Event-Driven Architecture

### Current State (Partial Implementation)

**Working Flows:**
1. **HoloDAE → AI Overseer**
   ```
   HoloDAE file changes → JSONL telemetry → HoloTelemetryMonitor → AI Overseer event_queue
   ```

2. **GitPushDAE → Social Media** (OLD)
   ```
   GitPushDAE autonomous commit → GitLinkedInBridge.push_and_post() → LinkedIn + X
   ```

3. **Auto Moderator DAE → WRE**
   ```
   Moderation decision → WRE record_error/record_success → Pattern Memory
   ```

**Missing Flows:**
1. **Git Hook → Event Queue → Social Media**
   ```
   Manual commit → post-commit hook → [MISSING: event_queue.put()] → SocialMediaEventRouter
   ```

2. **YouTube !bug Command → AI Overseer**
   ```
   YouTube chat "!bug gotjunk" → [MISSING: command parser] → event_queue → AI Overseer investigates logs
   ```

3. **Cross-Daemon Coordination**
   ```
   Any DAE → event_queue → HoloDAE consumer → Route to appropriate handler
   ```

---

## Proposed Architecture: Unified Event Queue

### Design Principle: Occam's Razor

**Question:** Should we create a new Event Processing Daemon?
**Answer:** NO - Extend HoloDAE's existing monitoring loop (~50 lines).

**Why HoloDAE?**
1. Already has monitoring loop infrastructure (monitoring_loop.py)
2. Already integrated with AI Overseer (telemetry bridge)
3. Already has MCP coordination (mcp_integration.py)
4. Already has skill execution (skill_executor.py)
5. Adding event queue consumption = minimal complexity

### Event Queue Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         EVENT PRODUCERS                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  GitPushDAE          Auto Moderator       YouTube Chat      Manual      │
│  (commits)           (moderation)         (commands)         (hooks)    │
│      │                    │                    │                │        │
│      └────────────────────┴────────────────────┴────────────────┘        │
│                              │                                           │
│                              ▼                                           │
│                   ┌──────────────────────┐                               │
│                   │  AI Overseer         │                               │
│                   │  event_queue         │                               │
│                   │  (asyncio.Queue)     │                               │
│                   └──────────────────────┘                               │
│                              │                                           │
│                              ▼                                           │
├─────────────────────────────────────────────────────────────────────────┤
│                         EVENT CONSUMER                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│                      ┌──────────────────┐                               │
│                      │   HoloDAE        │                               │
│                      │   Monitoring     │                               │
│                      │   Loop           │                               │
│                      └──────────────────┘                               │
│                              │                                           │
│               ┌──────────────┼──────────────┐                           │
│               │              │              │                           │
│               ▼              ▼              ▼                           │
│         git_push      youtube_bug     social_media                      │
│         (social)      (investigate)    (routing)                        │
│               │              │              │                           │
│               ▼              ▼              ▼                           │
├─────────────────────────────────────────────────────────────────────────┤
│                         EVENT HANDLERS                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  SocialMediaEventRouter   AI Overseer Log       Skill Execution         │
│  (LinkedIn + X posts)     Investigation         (WRE Skills)            │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Event Types

```python
@dataclass
class DAEEvent:
    """Universal DAE event for inter-daemon communication"""
    event_type: str  # git_push, youtube_bug, social_media, skill_request
    source_daemon: str  # holodae, gitpushdae, auto_moderator_dae, etc.
    timestamp: str  # ISO 8601
    payload: Dict[str, Any]  # Event-specific data
    priority: int = 1  # 0=critical, 1=high, 2=normal, 3=low
    correlation_id: Optional[str] = None  # For tracking event chains
```

**Example Events:**

1. **git_push Event** (from post-commit hook or GitPushDAE):
   ```python
   {
       "event_type": "git_push",
       "source_daemon": "git_hook",
       "timestamp": "2025-12-03T09:15:30.123Z",
       "payload": {
           "commits": [{
               "hash": "01baff5c",
               "message": "refactor(holodae): WSP 62 Sprint H1 - Extract PID Detective",
               "files_changed": 8
           }],
           "repository": "Foundups-Agent",
           "branch": "feat/cart-reservation-timeout"
       },
       "priority": 1
   }
   ```

2. **youtube_bug Event** (from YouTube chat command):
   ```python
   {
       "event_type": "youtube_bug",
       "source_daemon": "youtube_chat_daemon",
       "timestamp": "2025-12-03T09:20:15.456Z",
       "payload": {
           "command": "!bug",
           "args": ["gotjunk"],
           "author": "user123",
           "comment_id": "UgxKREWq38...",
           "video_id": "dQw4w9WgXcQ"
       },
       "priority": 0,  # Critical - user waiting for response
       "correlation_id": "bug_gotjunk_20251203_092015"
   }
   ```

3. **skill_request Event** (from HoloDAE or AI Overseer):
   ```python
   {
       "event_type": "skill_request",
       "source_daemon": "holodae",
       "timestamp": "2025-12-03T09:25:00.789Z",
       "payload": {
           "skill_name": "qwen_gitpush",
           "agent": "qwen",
           "input_context": {
               "files_changed": 14,
               "git_diff": "..."
           }
       },
       "priority": 2
   }
   ```

---

## Implementation Plan: Event Queue Consumption in HoloDAE

### Occam's Razor Solution

**Add to HoloDAE Monitoring Loop** (~50 lines):

**File:** `holo_index/qwen_advisor/services/monitoring_loop.py`

```python
# Line 173: Add to _run_monitoring_cycle()
async def _run_monitoring_cycle_async(self) -> MonitoringResult:
    """Async version of monitoring cycle that checks event queue"""

    # 1. Check event queue first (higher priority than file changes)
    if hasattr(self, 'event_queue') and not self.event_queue.empty():
        await self._process_event_queue()

    # 2. Normal file monitoring cycle
    cycle_start = time.perf_counter()
    changes = self.file_watcher.scan_for_changes()
    # ... existing code ...

    return result

async def _process_event_queue(self):
    """Process pending events from AI Overseer event queue"""
    try:
        # Non-blocking queue check
        while not self.event_queue.empty():
            event = await asyncio.wait_for(
                self.event_queue.get(),
                timeout=0.1
            )
            await self._handle_event(event)
    except asyncio.TimeoutError:
        pass
    except Exception as e:
        self._detailed_log(f"[EVENT-QUEUE] Error processing events: {e}")

async def _handle_event(self, event: Dict[str, Any]):
    """Route event to appropriate handler"""
    event_type = event.get('event_type')

    handlers = {
        'git_push': self._handle_git_push_event,
        'youtube_bug': self._handle_youtube_bug_event,
        'social_media': self._handle_social_media_event,
        'skill_request': self._handle_skill_request_event,
    }

    handler = handlers.get(event_type)
    if handler:
        await handler(event)
    else:
        self._detailed_log(f"[EVENT-QUEUE] Unknown event type: {event_type}")

async def _handle_git_push_event(self, event: Dict[str, Any]):
    """Handle git push → social media posting"""
    from modules.platform_integration.social_media_orchestrator.src.multi_account_manager import SocialMediaEventRouter

    router = SocialMediaEventRouter()
    results = await router.handle_event('git_push', event['payload'])

    self._holo_log(f"[GIT-PUSH] Social media posted: {results}")

async def _handle_youtube_bug_event(self, event: Dict[str, Any]):
    """Handle YouTube !bug command → AI Overseer log investigation"""
    payload = event['payload']
    bug_target = payload.get('args', [None])[0]

    if not bug_target:
        self._detailed_log("[YOUTUBE-BUG] No target specified")
        return

    # Trigger AI Overseer log investigation
    from modules.ai_intelligence.ai_overseer.src.ai_overseer import AIOverseerhub

    overseer = AIOverseerhub.get_instance()
    investigation_result = await overseer.investigate_module_logs(
        module_name=bug_target,
        correlation_id=event.get('correlation_id')
    )

    # Respond back to YouTube comment
    await self._post_youtube_response(
        video_id=payload['video_id'],
        comment_id=payload['comment_id'],
        result=investigation_result
    )

async def _handle_social_media_event(self, event: Dict[str, Any]):
    """Handle generic social media posting request"""
    # Route to SocialMediaEventRouter
    pass

async def _handle_skill_request_event(self, event: Dict[str, Any]):
    """Handle WRE Skill execution request"""
    if self.skill_executor:
        result = await self.skill_executor.execute_skill(
            skill_name=event['payload']['skill_name'],
            agent=event['payload']['agent'],
            input_context=event['payload']['input_context']
        )
        self._detailed_log(f"[SKILL-REQUEST] Executed: {result}")
```

---

## Git Post-Commit Hook

**File:** `.git/hooks/post-commit`

```bash
#!/bin/bash
# Post-commit hook: Trigger social media posting after ANY commit

echo "[0102] Post-commit hook: Enqueuing git_push event..."

# Get commit details
COMMIT_HASH=$(git rev-parse HEAD)
COMMIT_MSG=$(git log -1 --pretty=%B)
FILES_CHANGED=$(git diff-tree --no-commit-id --name-only -r HEAD | wc -l)
BRANCH=$(git branch --show-current)

# Enqueue event to AI Overseer
python -c "
import asyncio
import sys
import json
from datetime import datetime

sys.path.insert(0, 'O:/Foundups-Agent')

async def enqueue_git_push():
    from modules.ai_intelligence.ai_overseer.src.mcp_integration import MCPIntegration
    from pathlib import Path

    mcp = MCPIntegration(repo_root=Path('O:/Foundups-Agent'))

    event = {
        'event_type': 'git_push',
        'source_daemon': 'git_hook',
        'timestamp': datetime.now().isoformat(),
        'payload': {
            'commits': [{
                'hash': '$COMMIT_HASH',
                'message': '''$COMMIT_MSG''',
                'files_changed': $FILES_CHANGED
            }],
            'repository': 'Foundups-Agent',
            'branch': '$BRANCH'
        },
        'priority': 1
    }

    await mcp.event_queue.put(event)
    print('[0102] Event enqueued to AI Overseer')

asyncio.run(enqueue_git_push())
"

echo "[0102] Post-commit hook complete!"
```

**Make Executable:**
```bash
chmod +x .git/hooks/post-commit
```

---

## YouTube !bug Command Integration

### Command Parser Addition

**File:** `modules/communication/chat_rules/src/commands.py`

```python
# Add to CommandProcessor class

async def handle_bug_command(self, message: str, author: str, platform: str) -> str:
    """
    Handle !bug command - Trigger AI Overseer log investigation

    Usage: !bug [module_name]
    Example: !bug gotjunk
    """
    parts = message.split()
    if len(parts) < 2:
        return "Usage: !bug [module_name] (e.g., !bug gotjunk)"

    bug_target = parts[1]

    # Enqueue event to AI Overseer
    from modules.ai_intelligence.ai_overseer.src.mcp_integration import MCPIntegration
    from pathlib import Path
    from datetime import datetime
    import uuid

    mcp = MCPIntegration(repo_root=Path('O:/Foundups-Agent'))

    correlation_id = f"bug_{bug_target}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    event = {
        'event_type': 'youtube_bug',
        'source_daemon': 'youtube_chat_daemon',
        'timestamp': datetime.now().isoformat(),
        'payload': {
            'command': '!bug',
            'args': [bug_target],
            'author': author,
            'platform': platform
        },
        'priority': 0,  # Critical - user waiting
        'correlation_id': correlation_id
    }

    await mcp.event_queue.put(event)

    return f"[ROCKET] Investigating {bug_target} logs... (tracking: {correlation_id[:8]})"
```

---

## WSP Compliance

- **WSP 27:** Universal DAE Architecture - All daemons follow standardized lifecycle
- **WSP 80:** DAE Coordination - Event queue enables inter-daemon communication
- **WSP 91:** DAEMON Observability - Telemetry and event logging throughout
- **WSP 96:** WRE Skills Wardrobe - Skill execution via event queue
- **WSP 50:** Pre-Action Verification - Used HoloIndex to find existing architecture

---

## Next Steps

1. ✅ **Complete daemon mapping** (this document)
2. ⏳ **Update WSP 96 header** with Skillz clarification
3. ⏳ **Implement event queue consumption** in HoloDAE monitoring loop (~50 lines)
4. ⏳ **Add !bug command handler** to chat_rules/commands.py
5. ⏳ **Create post-commit hook** for automatic social media posting
6. ⏳ **Test autonomous flow:** !bug gotjunk → AI Overseer investigates → responds

---

## Related Documents

| Document | Location |
|----------|----------|
| GIT_PUSH_SOCIAL_MEDIA_WIRING_INVESTIGATION | docs/GIT_PUSH_SOCIAL_MEDIA_WIRING_INVESTIGATION.md |
| GIT_SOCIAL_MEDIA_EVENT_DRIVEN_ARCHITECTURE | docs/GIT_SOCIAL_MEDIA_EVENT_DRIVEN_ARCHITECTURE.md |
| HoloDAE Coordinator | holo_index/qwen_advisor/holodae_coordinator.py |
| Monitoring Loop | holo_index/qwen_advisor/services/monitoring_loop.py |
| AI Overseer MCP Integration | modules/ai_intelligence/ai_overseer/src/mcp_integration.py |
| HoloTelemetry Monitor | modules/ai_intelligence/ai_overseer/src/holo_telemetry_monitor.py |
| social_accounts.yaml | modules/platform_integration/social_media_orchestrator/config/social_accounts.yaml |

---

**Document Maintained By:** 0102
**Last Updated:** 2025-12-03
