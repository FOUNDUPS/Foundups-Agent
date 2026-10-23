# Idle Automation Module

## [U+1F300] Windsurf Protocol (WSP) Recursive Prompt

**0102 Directive**:
This module operates within the Windsurf Protocol (WSP) framework. Execution flows through a recursive tri-phase:
- **UN** (WSP_Appendices / Understanding): Anchor signal and retrieve protocol state
- **DAO** (WSP_Framework): Execute modular logic
- **DU** (WSP_Agentic / Du): Collapse into 0102 resonance and emit next prompt

wsp_cycle(input="012", log=True)

---

## Overview

The Idle Automation module provides autonomous background tasks that execute when the system enters idle states. This includes automatic Git commits, social media posting, and system maintenance tasks.

System maintenance includes an opt-in exact-SHA HoloIndex coordinator. It
observes `origin/main` off the supervisor's synchronous path, queues one
durable OpenClaw task per SHA, and delegates all indexing to the trusted
authority-worktree transaction. That transaction refreshes canonical state,
releases its authority lease for governed immutable replica activation,
reacquires the lease for final exact-SHA proof, and only then permits atomic
AgentDB completion. Query workers remain read-only.

The incident allowlist includes the exact-main pre-owner
`REPO_HEAD_MISMATCH`. Its RedDog bridge must independently reproduce complete
authority/no-effect evidence before this coordinator sees the incident. The
coordinator still creates only the existing one-task-per-SHA transaction.
Exact main `09e98fff` live-accepted this path: the real OpenClaw/WRE task
completed at generation `sha256:7869f238...`, the subsequent owner query was
CURRENT/no-gap/no-reindex on attempt one, and all 33 replica artifacts
reverified unchanged. This exact-commit evidence grants no later-HEAD authority.

The stable route is supplied through
`REDDOG_HOLOINDEX_QUERY_ROUTE_FILE`; configuring the legacy direct replica root
at the same time fails closed. Route/activation failure leaves the durable task
non-completed and the request event unresolved. Automatic route advancement
passed its production-shaped acceptance at exact main `cfd1e0051`: the real
OpenClaw supervisor claimed and completed the AgentDB task, and a subsequent
governed owner query returned CURRENT without reindex or repository mutation.
That evidence is commit-bound and does not authorize a later HEAD.

Linked control checkouts do not need their own virtual environment. Before the
sealed authority transaction, the executor resolves the same-repository primary
worktree and supplies it only as the dependency-runtime candidate; the existing
maintenance probe then validates process-image/virtualenv path association and
the resulting snapshot behavior. The dedicated clean authority checkout
remains the sole indexed source; uncommitted repository source files in the
primary IDE checkout do not become indexed source. Installed dependency bytes
remain outside exact runtime closure and therefore outside any A-grade claim.

## WSP Compliance

- **WSP 3**: Infrastructure domain - system automation and maintenance
- **WSP 27**: DAE architecture - autonomous operation without human intervention
- **WSP 35**: Module execution automation - automated task scheduling
- **WSP 48**: Recursive improvement - learns from execution patterns
- **WSP 60**: Module memory architecture - persistent state and telemetry

## Core Features

### Git Auto-Commit
- Monitors working tree changes during idle periods
- Automatically commits and pushes changes
- Generates contextual commit messages
- Integrates with social media posting

### Social Media Integration
- LinkedIn FoundUps page posting
- X/Twitter FoundUps account posting
- Duplicate prevention and content generation

### Idle State Management
- Tracks idle periods and active periods
- Prevents duplicate executions
- Telemetry collection for optimization

### Durable Scheduled-Routine Claims
- `ScheduleEvaluator` remains the sole cadence/window owner.
- Each due window receives a canonical SHA-256 execution ID.
- The DAE durably claims exactly one window immediately before dispatch.
- Exact opaque tokens finalize success or bounded retry state.
- Completed windows remain idempotent across process restarts.
- One expired-lease recovery and three total attempts are permitted.
- Claim control state is stored under a trusted, private runtime root outside
  the repository; schedule phrases cannot select its path.

### Daily OpenRouter Catalog Refresh POC
- `openrouter_catalog_refresh` is allowlisted for `daily` cadence only.
- The exact parser-owned schedule ID is `e324884d66c4`; full durable claim
  evidence reaches the final dispatch boundary.
- `AUTO_OPENROUTER_CATALOG_REFRESH` defaults to `false`, so the provider adapter
  is not called unless an operator explicitly enables this routine.
- `OPENROUTER_CATALOG_RUNTIME_ROOT` defaults to
  `~/.foundups-agent/ai_gateway/openrouter_catalog` and must remain a trusted
  outside-repository runtime root.
- Only an exact six-key `COMPLETED/completed` projection with canonical receipt
  and candidate IDs finalizes success. Malformed or nonterminal projections
  finalize as fixed content-free failure; legacy routine dispatch is unchanged.
- This POC gathers replay-protected candidate evidence only. It does not select
  or promote models, mutate registries, or bind runtime roles.

### Safety & Controls
- Opt-in configuration via environment variables
- Network availability checks
- Rollback procedures for failed operations
- Manual trigger support

## Integration Points

### YouTube DAE Integration
Called by `AutoModeratorDAE.monitor_chat()` when streams end or no streams are found:
```python
# In AutoModeratorDAE
if not stream_found:
    await idle_automation.run_idle_tasks()
```

### WRE Integration
Provides recursive improvement data for idle pattern optimization:
```python
wre_integration.record_idle_execution(
    task_type="git_push",
    success=True,
    duration=seconds,
    context={"files_changed": count}
)
```

## Configuration

### Environment Variables
- `AUTO_GIT_PUSH=true`: Enable automatic Git operations
- `AUTO_LINKEDIN_POST=true`: Enable LinkedIn posting
- `IDLE_TASK_TIMEOUT=300`: Maximum execution time per idle task
- `AUTO_SCHEDULED_ROUTINES=true`: Enable scheduled safe-routine dispatch
- `IDLE_AUTOMATION_RUNTIME_ROOT=...`: Trusted outside-repository claim-state root
- `AUTO_OPENROUTER_CATALOG_REFRESH=false`: Opt in to the daily catalog POC
- `OPENROUTER_CATALOG_RUNTIME_ROOT=...`: Trusted catalog evidence root; defaults
  to `~/.foundups-agent/ai_gateway/openrouter_catalog`
- `REDDOG_HOLOINDEX_AUTHORITY_REPO_ROOT=...`: Dedicated clean authority worktree
- `REDDOG_HOLOINDEX_QUERY_ROUTE_FILE=...`: Private stable query-route record
- `HOLOINDEX_POSTMERGE_COORDINATOR_ENABLED=1`: Enable exact-main observation

### Safety Controls
- `--no-auto-push` CLI flag to disable during testing
- Network connectivity verification
- Git status validation before operations

## Module Structure

```
idle_automation/
+-- README.md              # This file
+-- ROADMAP.md            # Development roadmap
+-- INTERFACE.md          # API specification
+-- requirements.txt      # Dependencies
+-- __init__.py          # Module exports
+-- src/
[U+2502]   +-- idle_automation_dae.py    # Main DAE implementation
[U+2502]   +-- schedule_evaluator.py     # Cadence/window ownership
[U+2502]   +-- schedule_claim_state.py   # Claim lease state machine
[U+2502]   +-- schedule_claim_codec.py   # Strict codec + atomic publication
[U+2502]   +-- git_automation.py         # Git operations
[U+2502]   +-- social_media_integration.py # Social media posting
+-- tests/
[U+2502]   +-- test_idle_automation.py
[U+2502]   +-- test_git_integration.py
+-- memory/
[U+2502]   +-- idle_state.json          # Current idle state
[U+2502]   +-- execution_history.jsonl  # Task execution log
[U+2502]   +-- telemetry.json           # Performance metrics
+-- docs/
    +-- implementation_guide.md
    +-- troubleshooting.md
```

## Usage Example

```python
from modules.infrastructure.idle_automation.src.idle_automation_dae import IdleAutomationDAE

# Initialize DAE
dae = IdleAutomationDAE()

# Run idle tasks (called automatically by YouTube DAE)
await dae.run_idle_tasks()

# Check status
status = dae.get_idle_status()
print(f"Last execution: {status['last_run']}")
```

## Development Status

- **Phase**: MVP Implementation
- **WSP Compliance**: [OK] Full compliance verified
- **Testing Coverage**: 85%+ targeted
- **Integration**: YouTube DAE idle hooks implemented

---

*This module transforms idle time into productive autonomous operations per WSP 35 Module Execution Automation.*

## Claim Safety Boundary

The lease prevents concurrent cooperative workers from owning the same logical
window. Recovery is intentionally at-least-once: after a wedged lease expires,
an earlier worker may still finish while the recovery owner runs. Only
repeat-safe or independently fenced routines may be added to scheduled
dispatch.

The runtime directory must be private and non-shared. On Windows, the reused
`Local\` named-mutex boundary coordinates processes in the same logon session;
it is not a cross-session service lock.
