# Idle Automation Module Interface

## [U+1F300] Windsurf Protocol (WSP) Recursive Prompt

**0102 Directive**:
This interface operates within the Windsurf Protocol (WSP) framework. Execution flows through recursive tri-phase:
- **UN** (Understanding): Interface contract comprehension
- **DAO** (Execution): Method invocation and parameter passing
- **DU** (Emergence): Result processing and state evolution

wsp_cycle(input="interface", log=True)

---

## Module Overview

**Name**: Idle Automation Module
**Domain**: Infrastructure (WSP 3)
**Purpose**: Autonomous execution of background tasks during system idle periods
**Architecture**: WSP 27 DAE with WSP 35 execution automation

## Primary Interface

### Exact-SHA HoloIndex Post-Merge Coordination

`coordinate_holoindex_postmerge()` observes `origin/main` from a configured
clean authority worktree and creates one insert-only AgentDB task per commit
SHA. It never indexes during query handling and never creates or repairs the
authority worktree.

The OpenClaw executor must first claim the task through
`AgentDB.claim_holoindex_postmerge_task()`. The claim CAS binds the serialized
task context to a one-use claim ID; the effect adapter must consume it through
`assigned -> executing` and validate the request event before invoking the
trusted authority transaction. Successful completion is committed
atomically with the request resolution and exact generation receipt.
The authority transaction runs canonical refresh under its first authority
lease, releases that lease while the governed activation controller
materializes/queries/commits the immutable replica, and reacquires the lease
for final binding, clean-HEAD, and `origin/main` proof. `CURRENT` is returned
only when the owner exactly matches the canonical HEAD, generation, and
freshness-receipt digest. Failure leaves the task failed or retryable, the
request pending, and the completion event absent.
The executor resolves `resolve_holoindex_runtime_root(repo_root)` before calling
the authority transaction. A clean linked control checkout therefore retains
task/control authority while the same-repository primary checkout supplies only
its dependency-runtime candidate (normally `.venv`) for the existing probe to
validate. The clean dedicated authority worktree remains repository/index
source authority. The resolver
falls back to the supplied control root when a related primary worktree cannot
be proven; maintenance then fails closed if that root lacks the required probe
runtime.
Claims have a 7500-second lease, covering the bounded 7200-second maintenance
timeout plus margin. A crashed or interrupted worker is reclaimed
by exact assignment timestamp and enters the existing bounded retry policy.

Runtime configuration:

- `REDDOG_HOLOINDEX_AUTHORITY_REPO_ROOT`: absolute dedicated worktree.
- `REDDOG_HOLOINDEX_QUERY_ROUTE_FILE`: absolute private stable route record.
- `REDDOG_HOLOINDEX_QUERY_REPLICA_ROOT`: legacy-only direct root; rejected when
  the stable route-file value is also present.
- `HOLOINDEX_POSTMERGE_COORDINATOR_ENABLED=1`: enable periodic observation.
- `HOLOINDEX_POSTMERGE_COORDINATOR_INTERVAL_SEC`: minimum 30 seconds.

The process-local transaction lock spans both authority leases and activation.
The automatic composer selects only absent replica/receipt targets and never
overwrites a generation. This ordering passed production-shaped acceptance at
exact main `cfd1e0051` through the real OpenClaw supervisor and AgentDB. A
subsequent governed owner query was CURRENT/no-gap/no-reindex and immutable
revalidation remained unchanged. Later HEADs require their own transaction.

### Class: IdleAutomationDAE

```python
class IdleAutomationDAE:
    def __init__(self) -> None
    async def run_idle_tasks() -> Dict[str, Any]
    def get_idle_status() -> Dict[str, Any]
    def reset_daily_counter() -> None
```

## Public Methods

### `__init__()`
**Purpose**: Initialize the Idle Automation DAE with persistent state and configuration.

**Parameters**: None

**Returns**: None

**WSP Compliance**: WSP 60 (Memory Architecture) - loads persistent state

### `run_idle_tasks() -> Dict[str, Any]`
**Purpose**: Execute all configured idle automation tasks.

**Parameters**: None

**Returns**:
```python
{
    "session_id": int,           # Idle session identifier
    "timestamp": str,           # ISO timestamp
    "tasks_executed": List[Dict], # Results of each task
    "overall_success": bool,    # True if all tasks succeeded
    "duration": float,          # Execution time in seconds
    "skipped_reason": Optional[str] # If execution was skipped
}
```

**Tasks Executed**:
- Git auto-commit and push
- LinkedIn social media posting
- Telemetry collection

**WSP Compliance**:
- WSP 35: Module execution automation
- WSP 48: Recursive improvement via WRE integration

### `get_idle_status() -> Dict[str, Any]`
**Purpose**: Retrieve current idle automation status and telemetry.

**Parameters**: None

**Returns**:
```python
{
    "last_idle_execution": Optional[str],  # ISO timestamp
    "last_git_push": Optional[str],        # ISO timestamp
    "last_linkedin_post": Optional[str],   # ISO timestamp
    "execution_count_today": int,          # Daily execution counter
    "idle_session_count": int,             # Total idle sessions
    "auto_git_enabled": bool,              # Git automation enabled
    "auto_linkedin_enabled": bool,         # LinkedIn automation enabled
    "recent_executions": List[Dict]        # Last 5 execution records
}
```

**WSP Compliance**: WSP 70 (Status Reporting Protocol)

### `reset_daily_counter() -> None`
**Purpose**: Reset the daily execution counter (primarily for testing).

**Parameters**: None

**Returns**: None

**Note**: This method is primarily intended for testing and debugging.

## Convenience Functions

### `run_idle_automation(parent_context=None, triggering_session=None) -> Dict[str, Any]`
**Purpose**: Convenience function for YouTube DAE integration with cross-surface continuity.

**Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `parent_context` | `ContinuityContext` | Optional parent context for explicit lineage |
| `triggering_session` | `str` | Optional session ID (e.g. video_id) for origin recovery |

**Returns**: Same as `IdleAutomationDAE.run_idle_tasks()`

**Continuity Behavior**:
- If `parent_context` is provided, idle work inherits that lineage directly
- If only `triggering_session` is provided, idle DAE attempts to recover origin continuity from AgentDB breadcrumbs matching that session ID
- If neither is provided, idle work runs as an independent root

**Usage**:
```python
from modules.infrastructure.idle_automation.src.idle_automation_dae import run_idle_automation

# In YouTube DAE idle loop — pass video_id for cross-surface correlation
result = await run_idle_automation(triggering_session=self._last_stream_id)
if result["overall_success"]:
    logger.info("Idle automation completed successfully")
```

## Configuration

### Environment Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTO_GIT_PUSH` | bool | `false` | Enable automatic Git operations |
| `AUTO_LINKEDIN_POST` | bool | `true` | Enable LinkedIn posting |
| `IDLE_TASK_TIMEOUT` | int | `300` | Maximum execution time (seconds) |
| `MAX_DAILY_EXECUTIONS` | int | `3` | Maximum executions per day |
| `AUTO_SCHEDULED_ROUTINES` | bool | `true` | Enable scheduled routine claims and dispatch |
| `IDLE_AUTOMATION_RUNTIME_ROOT` | path | `~/.foundups-agent/idle_automation` | Trusted private claim-state root outside the repository |
| `AUTO_OPENROUTER_CATALOG_REFRESH` | bool | `false` | Enable the exact daily OpenRouter catalog refresh claim |
| `OPENROUTER_CATALOG_RUNTIME_ROOT` | path | `~/.foundups-agent/ai_gateway/openrouter_catalog` | Trusted outside-repository provider evidence root |

### Safety Controls

- **Network Verification**: Checks connectivity before Git operations
- **Git Status Validation**: Verifies working tree changes exist
- **Daily Limits**: Prevents excessive automation execution
- **Error Recovery**: Comprehensive exception handling and logging

## Integration Points

### YouTube DAE Integration

**Hook Location**: `AutoModeratorDAE.monitor_chat()` idle loop

**Integration Code**:
```python
# In AutoModeratorDAE.monitor_chat()
if not stream_found:
    try:
        from modules.infrastructure.idle_automation.src.idle_automation_dae import run_idle_automation
        await run_idle_automation()
    except Exception as e:
        logger.warning(f"Idle automation failed: {e}")
    await asyncio.sleep(delay)
```

### WRE Integration

**Purpose**: Recursive improvement and pattern learning

**Integration Points**:
- Success/failure reporting via `record_success()` / `record_error()`
- Optimized approaches via `get_optimized_approach()`
- Performance telemetry for learning

## Error Handling

### Expected Exceptions

- **NetworkError**: Network connectivity issues
- **GitError**: Git operation failures (status, commit, push)
- **LinkedInError**: Social media posting failures
- **QuotaError**: API rate limit exceeded
- **ConfigError**: Invalid configuration or permissions

### Error Response Format

```python
{
    "task": str,           # Task that failed ("git_push", "linkedin_post")
    "success": false,
    "error": str,          # Error description
    "duration": float,     # Time spent before failure
    "retryable": bool      # Whether operation can be retried
}
```

## Performance Characteristics

### Execution Time
- **Typical**: 5-15 seconds for Git + LinkedIn cycle
- **Maximum**: Configurable via `IDLE_TASK_TIMEOUT` (default 300s)
- **Network Dependent**: Slower on poor connections

### Resource Usage
- **Memory**: Minimal (<50MB additional)
- **CPU**: Low impact during idle periods
- **Network**: Git push + LinkedIn API calls
- **Storage**: Persistent state and telemetry logs

## Testing Interface

### Test Entry Points

```python
# Unit testing
dae = IdleAutomationDAE()
dae.reset_daily_counter()  # Reset for testing

# Integration testing
result = await dae.run_idle_tasks()
assert result["overall_success"] == True

# Status testing
status = dae.get_idle_status()
assert "last_idle_execution" in status
```

### Mock Interfaces

All external dependencies can be mocked for testing:
- Git operations via `subprocess` mocking
- Network checks via connectivity mocking
- LinkedIn API via bridge mocking
- WRE integration via mock objects

## Scheduled Claim Interface

### `ScheduleEvaluator.claim_schedule(spec, *, now=None)`

Computes the canonical cadence window and asks `ScheduleClaimStore` to publish
one durable claim. It returns `ScheduleClaim` only after the fixed
`schedule_claim_state.json` artifact is atomically published under the trusted
runtime root. Disabled, unknown, out-of-window, completed, actively leased, and
backoff-blocked schedules return `None`.

### `ScheduleEvaluator.finalize_claim(token, *, success, outcome_code, now=None)`

Performs exact-token compare-and-set finalization. A token that expired may
finalize only while it remains current; recovery immediately makes the old
token stale. Outcome state stores only bounded codes or a digest, never raw
dispatcher text.

### Daily OpenRouter catalog claim

`ScheduleParser` accepts `openrouter_catalog_refresh` only with `daily`
cadence and generates canonical schedule ID `e324884d66c4`.
`IdleAutomationDAE._claim_and_dispatch(...)` passes the full exact
`ScheduleClaim` to the provider branch. The final boundary is default-off via
`AUTO_OPENROUTER_CATALOG_REFRESH=false`.

When enabled, the DAE supplies only the code-derived repository root and trusted
`OPENROUTER_CATALOG_RUNTIME_ROOT` to the AI Gateway adapter. Its response must
be an exact six-key dictionary. Success requires exact boolean `true`,
`COMPLETED/completed`, an exact boolean replay flag, and canonical 64-hex
receipt/candidate evidence IDs. Every other shape becomes the fixed
`routine_failed` outcome without forwarding provider text.

Claim finalization occurs before legacy `last_run` recording. A successful
adapter projection records success only after exact-token finalization; failed
or uncertain finalization leaves legacy suppression untouched. This interface
collects candidate evidence only and grants no selection, promotion, registry,
or runtime-binding authority.

Cancellation propagates without finalizing or recording the claim. The claim
remains leased for the existing bounded expiry and replay-recovery policy.

### Durability Contract

- Maximum claim lease: 3900 seconds, exceeding the 3600-second bounded routine
  timeout plus margin.
- Retry policy: 60 seconds, then 300 seconds; maximum three attempts.
- Lease recovery: at most one expired-claim recovery per window.
- Publication: same-directory temp, fsync, replace, post-replace byte proof,
  and exact last-known-good restoration on uncertain replacer behavior.
- Malformed, partial, duplicate-key, oversized, or noncanonical state fails
  closed before dispatch.
- A legacy `last_run` suppresses a window only when `last_result` has the
  canonical `success:` prefix. Failed or unknown legacy results remain due and
  enter durable claim/retry control.
- Claims provide cooperative single ownership, not exactly-once side effects;
  registered routines must be repeat-safe or independently fenced.

## WSP Compliance Matrix

| WSP Protocol | Compliance Level | Implementation |
|-------------|------------------|----------------|
| WSP 3 | [OK] Full | Infrastructure domain placement |
| WSP 27 | [OK] Full | Complete DAE architecture |
| WSP 35 | [OK] Full | Module execution automation |
| WSP 48 | [OK] Full | WRE recursive improvement |
| WSP 60 | [OK] Full | Memory architecture |
| WSP 70 | [OK] Full | Status reporting |
| WSP 11 | [OK] Full | Interface documentation |

---

*This interface follows WSP 11 (Public API Definition) and provides complete contract specification for idle automation integration.*
