# AI Intelligence Overseer - Public API

**Version**: 0.1.0
**Status**: POC
**WSP Compliance**: WSP 11 (Public API Documentation)

---

## Overview

Public API for AI Intelligence Overseer - MCP coordinator for Holo Qwen/Gemma agent teams.

**Key Features**:
- WSP 77 agent coordination (Qwen + Gemma + 0102)
- WSP 54 role assignment (Agent Teams variant)
- WSP 96 MCP governance integration
- WSP 48 recursive self-improvement
- WSP 60 module memory persistence for patterns and exec reports
- WSP 78 SQLite persistence for missions and phases (unified DB)

---

## Core Classes

### AIIntelligenceOverseer

Main coordination class for spawning and managing agent teams.

```python
from modules.ai_intelligence.ai_overseer.src.ai_overseer import AIIntelligenceOverseer, MissionType

# Initialize
overseer = AIIntelligenceOverseer(repo_root=Path("O:/Foundups-Agent"))

# Coordinate mission
results = overseer.coordinate_mission(
    mission_description="Analyze code quality across modules",
    mission_type=MissionType.CODE_ANALYSIS,
    auto_approve=False
)
```

**Methods**:

#### `__init__(repo_root: Path)`
Initialize AI Overseer with repository root.

**Parameters**:
- `repo_root`: Path to repository root directory

---

#### `execute_m2m_skill(skill_name: str, payload: Optional[Dict[str, Any]] = None, m2m: bool = True) -> Dict[str, Any]`

Execute one of the module-local M2M workflow skillz by name.

**Supported skills**:
- `m2m_compile_gate`
- `m2m_stage_promote_safe`
- `m2m_qwen_runtime_health`
- `m2m_holo_retrieval_benchmark`

**Parameters**:
- `skill_name`: skill identifier
- `payload`: skill-specific execution payload
- `m2m`: when `True`, wrap response in WSP 99-style M2M envelope

**Returns (m2m=False)**:
```python
{
  "skill_name": str,
  "status": "OK|FAIL",
  "elapsed_ms": float,
  "result": Dict[str, Any]
}
```

**Returns (m2m=True)**:
```python
{
  "M2M_VERSION": "1.0",
  "SENDER": "AI_OVERSEER",
  "RECEIVER": "0102-ORCH",
  "TS": "<iso8601>",
  "MISSION": {"OBJ": "EXECUTE <skill_name>", "MODE": "exec", "WSP": [95, 99, 50]},
  "STATUS": "OK|FAIL",
  "RESULT": {...}
}
```

**Safety**:
- SKILL/boot-prompt content is rejected by compile gate (must remain verbatim).
- Stage promotion requires explicit `target_path` (no inferred wildcard target).

---

#### `monitor_openclaw_security(force: bool = False) -> Dict[str, Any]`

Run the OpenClaw skill supply-chain sentinel once and return a normalized gate result.

**Parameters**:
- `force`: If `True`, bypass TTL cache and force a fresh scan

**Returns**:
```python
{
    "success": bool,      # mirrors passed
    "available": bool,    # scanner/sentinel available
    "passed": bool,       # gate decision
    "cached": bool,       # came from TTL cache
    "message": str,
    "required": bool,
    "enforced": bool,
    "report_path": Optional[str]
}
```

**OpenClaw Sentinel Policy Env Vars**:
- `OPENCLAW_SKILL_SCAN_REQUIRED` (default `1`)
- `OPENCLAW_SKILL_SCAN_ENFORCED` (default `1`)
- `OPENCLAW_SKILL_SCAN_MAX_SEVERITY` (default `medium`)
- `OPENCLAW_SKILL_SCAN_TTL_SEC` (default `900`)
- `OPENCLAW_PORT_SCAN_IGNORE_PORTS` (default `135,445,1900,5353,5355,5357,5358,5040`)
- `OPENCLAW_PORT_SCAN_MONITORED_PORTS` (default `OPENCLAW_BRIDGE_PORT` or `18800`; set empty to scan all wildcard listeners)
- `OPENCLAW_PORT_SCAN_IGNORE_EPHEMERAL` (default `1`, ignores ports `>=49152`)
- `OPENCLAW_PORT_SCAN_IGNORE_SYSTEM_PIDS` (default `1`, ignores PID `0/4` listeners)
- `OPENCLAW_SENTINEL_CACHE_PATH` (optional cache override)
- `OPENCLAW_SECURITY_MONITOR_ENABLED` (default `1`)
- `OPENCLAW_SECURITY_MONITOR_INTERVAL_SEC` (default `300`)
- `OPENCLAW_SECURITY_ALERT_DEDUPE_SEC` (default `900`)
- `OPENCLAW_SECURITY_ALERT_TO_DISCORD` (default `1`)
- `OPENCLAW_SECURITY_ALERT_TO_CHAT` (default `0`)
- `OPENCLAW_SECURITY_ALERT_TO_STDOUT` (default `1`)
- `OPENCLAW_INCIDENT_ALERT_DEDUPE_SEC` (default `900`)
- `OPENCLAW_INCIDENT_ALERT_TO_DISCORD` (default `1`)
- `OPENCLAW_INCIDENT_ALERT_TO_CHAT` (default `0`)
- `OPENCLAW_INCIDENT_ALERT_TO_STDOUT` (default `1`)
- `OPENCLAW_INCIDENT_DEDUPE_SEC` (legacy alias used by correlator; keep aligned)

**OpenClaw Security Event Payload**
```python
{
  "event": "openclaw_security_alert",
  "severity": "critical|warning",
  "source": "openclaw_security_monitor|...",
  "dedupe_key": str,
  "checked_at": float,
  "required": bool,
  "enforced": bool,
  "max_severity": str,
  "exit_code": int,
  "message": str,
  "report_path": Optional[str],
  "skills_dir": Optional[str],
}
```

**Forensic Persistence**
- Every non-deduped `openclaw_security_alert` event is appended to:
  - `modules/ai_intelligence/ai_overseer/memory/openclaw_security_alerts.jsonl`
- Every non-deduped `openclaw_incident_alert` event is appended to:
  - `modules/ai_intelligence/ai_overseer/memory/openclaw_incident_alerts.jsonl`

**OpenClaw Correlation Inputs**
- `permission_denied`
- `rate_limited`
- `command_fallback`

These events are correlated in `AIIntelligenceOverseer` into `openclaw_incident_alert` signals with strict incident dedupe.

**Containment Persistence**
- Correlator persists containment state to:
  - `modules/ai_intelligence/ai_overseer/memory/openclaw_containment.db`
- Active containment state is restored on process start.

---

#### `start_openclaw_security_monitoring(interval_sec: Optional[float] = None, force_first: bool = False) -> None`

Start a dedicated background security monitor task for OpenClaw.

**Notes**:
- Uses `OPENCLAW_SECURITY_MONITOR_INTERVAL_SEC` when `interval_sec` is omitted.
- Called automatically by `start_background_services()` when `OPENCLAW_SECURITY_MONITOR_ENABLED != 0`.

---

#### `stop_openclaw_security_monitoring() -> None`

Stop the dedicated background OpenClaw security monitor task.

---

#### `get_openclaw_security_status() -> Dict[str, Any]`

Return the last OpenClaw sentinel status captured in the current process.

---

#### `monitor_wsp_framework(force: bool = False, emit_alert: bool = True) -> Dict[str, Any]`

Run framework-vs-knowledge WSP drift audit through AI Overseer.

**Parameters**:
- `force`: bypass cache and force immediate re-audit
- `emit_alert`: emit DAEmon drift warning when severity is `warning`/`critical`

**Returns**:
```python
{
  "available": bool,
  "cached": bool,
  "checked_at": float,
  "ttl_sec": int,
  "framework_count": int,
  "knowledge_count": int,
  "common_count": int,
  "drift_count": int,
  "framework_only": List[str],
  "knowledge_only": List[str],
  "drift_files": List[str],
  "index_issues": List[str],
  "severity": "ok|warning|critical",
  "message": str,
  "report_path": str
}
```

**Audit Artifacts**:
- Cache: `modules/ai_intelligence/ai_overseer/memory/wsp_framework_audit_cache.json`
- Latest: `modules/ai_intelligence/ai_overseer/memory/wsp_framework_audit_latest.json`
- History: `modules/ai_intelligence/ai_overseer/memory/wsp_framework_audit_history.jsonl`

**Env Vars**:
- `WSP_FRAMEWORK_AUDIT_TTL_SEC` (default `900`)
- `WSP_FRAMEWORK_ALERT_TO_STDOUT` (default `1`)

**DAEmon Signal**:
```
[DAEMON][WSP-FRAMEWORK] event=wsp_framework_drift severity=... drift=... framework_only=... knowledge_only=... index_issues=...
```

---

#### `get_wsp_framework_status() -> Dict[str, Any]`

Return the last WSP framework audit status captured in the current process.

---

#### `release_openclaw_containment(target_type: str, target_id: str, requested_by: str = "operator", reason: str = "manual_override") -> Dict[str, Any]`

Release active containment for a sender/channel target (unauthenticated - internal use only).

**Telemetry Event**
```python
{
  "event": "openclaw_containment_release",
  "target_type": "sender|channel",
  "target_id": str,
  "requested_by": str,
  "reason": str
}
```

---

#### `release_openclaw_containment_authenticated(target_type: str, target_id: str, token: str, nonce: str, requested_by: str, reason: str, source_ip: str = "unknown", session_id: str = "") -> Dict[str, Any]`

Authenticated containment release with full audit trail and replay prevention.

**Parameters**:
- `target_type`: "sender" or "channel"
- `target_id`: The sender/channel ID to release
- `token`: Operator authentication token (matches `OPENCLAW_OPERATOR_TOKEN` or `OPENCLAW_OPERATOR_TOKEN_PREVIOUS`)
- `nonce`: Unique request nonce for replay prevention
- `requested_by`: Operator identifier (email, username)
- `reason`: Reason for release
- `source_ip`: Source IP of request (for audit)
- `session_id`: Session identifier (for audit)

**Returns**:
```python
{
  "success": bool,
  "release_id": "REL-XXXXXXXX",
  "target_type": str,
  "target_id": str,
  "released_at": Optional[float],
  "error": Optional[str]  # "authentication_failed" | "replay_detected" | "rate_limited" | "locked_out"
}
```

**Errors**:
- `authentication_failed`: Token missing, not configured, or invalid
- `replay_detected`: Nonce already used within replay window
- `rate_limited`: Release requests exceeded per-operator/session window
- `locked_out`: Operator/session temporarily locked after repeated auth failures

**Audit Record** (persisted to JSONL + SQLite):
```python
{
  "release_id": str,
  "target_type": str,
  "target_id": str,
  "requested_by": str,
  "reason": str,
  "source_ip": str,
  "session_id": str,
  "timestamp": float,
  "success": bool,
  "auth_method": "token|token_previous|token_failed|token_not_configured|replay_detected|rate_limited|locked_out"
}
```

**DAEmon Signals**:
```
[DAEMON][OPENCLAW-AUTH] event=auth_failed reason=...
[DAEMON][OPENCLAW-RELEASE] event=authenticated_release release_id=... success=...
```

---

#### `get_audit_records(limit: int = 100, target_id: Optional[str] = None) -> List[Dict]`

Retrieve audit records from SQLite.

**Parameters**:
- `limit`: Maximum records to return
- `target_id`: Optional filter by target

**Returns**: List of audit record dicts

---

### Security Event Correlator

The correlator ingests security events and triggers incidents when thresholds are crossed.

#### `ingest_security_event(event_type: str, sender: str, channel: str, details: Dict) -> Optional[Dict]`

Ingest external security event into correlator. Returns incident dict if threshold crossed.

**Event Types**: `openclaw_security_alert`, `permission_denied`, `rate_limited`, `command_fallback`

---

#### `check_containment(sender: str, channel: str) -> Optional[Dict]`

Check if sender or channel is under containment. Returns containment state if active.

---

#### `get_correlator_stats() -> Dict[str, Any]`

Get correlator statistics including event counts, incidents, and containment states.

---

**Correlator Env Vars**:
| Variable | Default | Description |
|----------|---------|-------------|
| `OPENCLAW_CORRELATION_WINDOW_SEC` | `300` | Event correlation window |
| `OPENCLAW_INCIDENT_THRESHOLD` | `5` | Events to trigger incident |
| `OPENCLAW_CONTAINMENT_ENABLED` | `1` | Enable auto-containment |
| `OPENCLAW_CONTAINMENT_DURATION_SEC` | `300` | Containment duration |
| `OPENCLAW_INCIDENT_DEDUPE_SEC` | `60` | Incident alert dedupe window |
| `OPENCLAW_OPERATOR_TOKEN` | `` | Operator token for authenticated release |
| `OPENCLAW_OPERATOR_TOKEN_PREVIOUS` | `` | Previous operator token during rotation window |
| `OPENCLAW_REPLAY_WINDOW_SEC` | `300` | Nonce replay prevention window |
| `OPENCLAW_DISCORD_WEBHOOK_URL` | `` | Discord webhook for notifications |
| `OPENCLAW_NOTIFICATION_DEDUPE_SEC` | `300` | Notification dedupe window |
| `OPENCLAW_NOTIFICATION_RETRY_MAX` | `3` | Max Discord notification attempts |
| `OPENCLAW_NOTIFICATION_RETRY_BACKOFF_SEC` | `1` | Base backoff seconds for notification retry |
| `OPENCLAW_RELEASE_RATE_LIMIT_COUNT` | `10` | Max release requests per window |
| `OPENCLAW_RELEASE_RATE_LIMIT_WINDOW_SEC` | `60` | Release rate-limit window seconds |
| `OPENCLAW_AUTH_FAILURE_THRESHOLD` | `5` | Failed auth attempts before lockout |
| `OPENCLAW_AUTH_LOCKOUT_SEC` | `300` | Lockout duration seconds |
| `OPENCLAW_AUDIT_RETENTION_DAYS` | `30` | Retention period for SQLite audit records |
| `OPENCLAW_AUDIT_JSONL_MAX_MB` | `10` | JSONL audit rotation threshold in MB |
| `OPENCLAW_AUDIT_JSONL_KEEP_FILES` | `5` | Number of rotated JSONL audit files to retain |

**Incident Event Payload**:
```python
{
  "event": "openclaw_incident_alert",
  "incident_id": "INC-XXXXXXXX",
  "severity": "low|medium|high|critical",
  "event_counts": {"permission_denied": 3, "rate_limited": 2},
  "first_seen": float,
  "last_seen": float,
  "policy_trigger": "sender_threshold:user123",
  "containment": "mute_sender|mute_channel|advisory_only|none"
}
```

**Forensic Bundles**: `modules/ai_intelligence/ai_overseer/memory/incident_bundles/`

---

#### `coordinate_mission(mission_description: str, mission_type: MissionType = MissionType.CUSTOM, auto_approve: bool = False) -> Dict[str, Any]`

Main entry point for coordinating missions with Qwen + Gemma + 0102.

**Parameters**:
- `mission_description`: Human-readable description of mission
- `mission_type`: Type of mission (see MissionType enum)
- `auto_approve`: Skip approval prompts if True

**Returns**:
```python
{
    "success": bool,
    "mission_id": str,
    "team": {
        "partner": "qwen",      # Qwen Partner
        "principal": "0102",    # 0102 Principal
        "associate": "gemma"    # Gemma Associate
    },
    "results": {
        "phases_completed": int,
        "phases_failed": int,
        "phase_results": List[Dict],
        "errors": List[str]
    },
    "external_agent": Optional[Dict]  # II-Agent adapter result (if enabled)
}
```

**II-Agent Adapter (Optional)**
- Feature flag: `II_AGENT_ENABLED=true`
- Modes:
  - CLI: set `II_AGENT_CLI` or `II_AGENT_COMMAND` (template with `{task}`)
  - HTTP: set `II_AGENT_MODE=http` and `II_AGENT_ENDPOINT`
- Allowed mission types: `II_AGENT_MISSION_TYPES` (comma-separated, default: documentation_generation,architecture_design,code_analysis)
- Local LLM auto-start (llama.cpp):
  - `II_AGENT_LLM_BASE_URL` (e.g., `http://127.0.0.1:1235/v1`)
  - `II_AGENT_LLM_MODEL` (full GGUF path or model id)
  - `II_AGENT_LLM_API_KEY` (use `local`)
  - `II_AGENT_LLM_AUTO_START=true`
  - `II_AGENT_LLM_START_SCRIPT` (PowerShell launcher)
  - `II_AGENT_LLM_START_TIMEOUT_SEC`
- llama.cpp server config (used by launcher):
  - `LLAMA_CPP_MODEL_PATH`, `LLAMA_CPP_HOST`, `LLAMA_CPP_PORT`
  - `LLAMA_CPP_N_CTX`, `LLAMA_CPP_N_GPU_LAYERS`, `LLAMA_CPP_THREADS`

**CLI File Context Injection**
- If a task includes file paths, the CLI appends file contents automatically.
- Limit via `II_AGENT_FILE_MAX_CHARS` (default: 12000).

**Example**:
```python
results = overseer.coordinate_mission(
    mission_description="Build YouTube live chat agent",
    mission_type=MissionType.MODULE_INTEGRATION,
    auto_approve=False
)

if results["success"]:
    print(f"Mission {results['mission_id']} completed successfully")
```

---

#### `spawn_agent_team(mission_description: str, mission_type: MissionType = MissionType.CUSTOM, auto_approve: bool = False) -> AgentTeam`

Spawn agent team with WSP 54 role assignments.

**Parameters**:
- `mission_description`: Mission to accomplish
- `mission_type`: Type of mission
- `auto_approve`: Skip approval prompts

**Returns**: `AgentTeam` object with:
- `mission_id`: Unique identifier
- `mission_type`: MissionType enum
- `partner`: "qwen" (Qwen Partner)
- `principal`: "0102" (0102 Principal)
- `associate`: "gemma" (Gemma Associate)
- `status`: "initialized", "executing", "completed", "failed"
- `results`: Execution results dict

**Non-interactive shells**
- If stdin is not a TTY, AI Overseer auto-approves missions to avoid EOF.

**Example**:
```python
team = overseer.spawn_agent_team(
    mission_description="Integrate Twitter posting with MCP",
    mission_type=MissionType.MODULE_INTEGRATION
)

print(f"Team {team.mission_id} status: {team.status}")
```

---

#### `analyze_mission_requirements(mission_description: str, mission_type: MissionType = MissionType.CUSTOM) -> Dict[str, Any]`

Phase 1: Gemma Associate fast pattern analysis.

**Parameters**:
- `mission_description`: Mission description
- `mission_type`: Type of mission

**Returns**:
```python
{
    "method": "gemma_fast_classification",
    "mission_type": str,
    "description": str,
    "classification": {
        "complexity": int,  # 1-5 scale
        "estimated_phases": int,
        "requires_qwen_planning": bool,
        "requires_0102_oversight": bool
    },
    "patterns_detected": List[str],
    "recommended_team": Dict[str, str]
}
```

**Example**:
```python
# Gemma fast analysis (50-100ms)
analysis = overseer.analyze_mission_requirements(
    mission_description="Refactor OAuth token management",
    mission_type=MissionType.CODE_ANALYSIS
)

print(f"Complexity: {analysis['classification']['complexity']}/5")
```

---

#### `generate_coordination_plan(analysis: Dict[str, Any]) -> CoordinationPlan`

Phase 2: Qwen Partner strategic coordination planning.

**Parameters**:
- `analysis`: Results from Gemma analysis

**Returns**: `CoordinationPlan` object with:
- `mission_id`: Unique identifier
- `mission_type`: MissionType enum
- `phases`: List of phase dicts with WSP 15 MPS scoring
- `estimated_complexity`: 1-5 scale
- `recommended_approach`: "autonomous_execution", "supervised_execution", or "collaborative_orchestration"
- `learning_patterns`: Detected patterns from memory

**Example**:
```python
# Qwen strategic planning (200-500ms)
analysis = overseer.analyze_mission_requirements("Complex refactoring")
plan = overseer.generate_coordination_plan(analysis)

print(f"Approach: {plan.recommended_approach}")
print(f"Phases: {len(plan.phases)}")
for phase in plan.phases:
    print(f"  Phase {phase['phase']}: {phase['name']} (Priority: {phase['priority']})")
```

---

#### `store_mission_pattern(team: AgentTeam)`

Phase 4: Store mission results as learning pattern (WSP 48).
Also writes a compact execution report to module memory (WSP 60) and records
mission aggregate + phase rows into SQLite (WSP 78) using `OverseerDB`.

**Parameters**:
- `team`: Completed AgentTeam object

**Example**:
```python
team = overseer.spawn_agent_team("Test mission")
# ... mission executes ...
overseer.store_mission_pattern(team)  # Stores for future learning
```

---

## Enums

### AgentRole

WSP 54 Agent Team roles.

```python
class AgentRole(Enum):
    PARTNER = "qwen"      # Qwen: Does simple stuff, scales up
    PRINCIPAL = "0102"    # 0102: Lays out plan, oversees execution
    ASSOCIATE = "gemma"   # Gemma: Pattern recognition, scales up
```

---

### MissionType

Types of missions AI Overseer can coordinate.

```python
class MissionType(Enum):
    CODE_ANALYSIS = "code_analysis"
    ARCHITECTURE_DESIGN = "architecture_design"
    MODULE_INTEGRATION = "module_integration"
    TESTING_ORCHESTRATION = "testing_orchestration"
    DOCUMENTATION_GENERATION = "documentation_generation"
    WSP_COMPLIANCE = "wsp_compliance"
    CUSTOM = "custom"
```

---

## Data Classes

### AgentTeam

Coordinated agent team following WSP 54.

```python
@dataclass
class AgentTeam:
    mission_id: str
    mission_type: MissionType
    partner: str = "qwen"     # Qwen Partner
    principal: str = "0102"   # 0102 Principal
    associate: str = "gemma"  # Gemma Associate
    status: str = "initialized"
    created_at: float
    results: Dict[str, Any]
```

---

### CoordinationPlan

Strategic coordination plan from Qwen Partner.

```python
@dataclass
class CoordinationPlan:
    mission_id: str
    mission_type: MissionType
    phases: List[Dict[str, Any]]
    estimated_complexity: int  # 1-5 scale
    recommended_approach: str
    learning_patterns: List[str]
```

---

## CLI Interface

### Basic Usage

```bash
# Coordinate mission
python modules/ai_intelligence/ai_overseer/src/ai_overseer.py \
    "Analyze YouTube modules" \
    --type code_analysis

# Auto-approve (no prompts)
python modules/ai_intelligence/ai_overseer/src/ai_overseer.py \
    "Build Twitter agent" \
    --type module_integration \
    --auto-approve
```

**CLI Purpose**
- The `main()` CLI is for quick validation and manual runs.
- For production automation, call `AIIntelligenceOverseer.coordinate_mission()` programmatically.

---

## Integration Examples

### Example 1: Code Analysis Mission

```python
from pathlib import Path
from modules.ai_intelligence.ai_overseer.src.ai_overseer import AIIntelligenceOverseer, MissionType

# Initialize
overseer = AIIntelligenceOverseer(Path("O:/Foundups-Agent"))

# Coordinate code analysis
results = overseer.coordinate_mission(
    mission_description="Analyze WSP compliance across all modules",
    mission_type=MissionType.WSP_COMPLIANCE,
    auto_approve=False
)

if results["success"]:
    print(f"[OK] Analysis complete: {results['mission_id']}")
    print(f"  Phases: {results['results']['phases_completed']}")
else:
    print(f"[FAIL] Analysis failed: {results['results']['errors']}")
```

---

### Example 2: Module Integration Mission

```python
# Build new YouTube live chat agent
results = overseer.coordinate_mission(
    mission_description="Build YouTube live chat agent with MCP integration",
    mission_type=MissionType.MODULE_INTEGRATION
)

# Results show WSP 77 coordination:
# Phase 1 (Gemma): Fast analysis of existing livechat module
# Phase 2 (Qwen): Strategic plan with WSP 15 MPS scoring
# Phase 3 (0102): Execution oversight and supervision
# Phase 4: Pattern stored in adaptive_learning/
```

---

### Example 3: Autonomous Architecture Design

```python
# Let Qwen design architecture (scales up from simple)
results = overseer.coordinate_mission(
    mission_description="Design MCP gateway architecture for social media",
    mission_type=MissionType.ARCHITECTURE_DESIGN,
    auto_approve=True  # Trust Qwen/Gemma autonomous execution
)

# Qwen starts simple:
#   - Phase 1: Gemma analyzes existing social_media_orchestrator
#   - Phase 2: Qwen generates simple integration plan
#   - Phase 3: 0102 validates approach
#   - Phase 4: Pattern stored for future architecture tasks
# Over time, Qwen scales up to handle complex architectures
```

---

## WSP Compliance

### WSP 77: Agent Coordination Protocol
- Phase 1: Gemma Associate (fast pattern matching)
- Phase 2: Qwen Partner (strategic planning)
- Phase 3: 0102 Principal (execution oversight)
- Phase 4: Learning (pattern storage)

### WSP 54: Role Assignment (Agent Teams)
- Partner: Qwen (does simple stuff, scales up)
- Principal: 0102 (lays out plan, oversees execution)
- Associate: Gemma (pattern recognition, scales up)

### WSP 96: MCP Governance
- Bell state consciousness alignment
- Multi-agent consensus
- Gateway sentinel oversight

### WSP 48: Recursive Self-Improvement
- Pattern storage in `holo_index/adaptive_learning/ai_overseer_patterns.json`
- Learning from successful/failed missions
- Autonomous pattern recall for future tasks

---

## Error Handling

All methods return success/failure status in results dict:

```python
results = overseer.coordinate_mission("mission")

if not results["success"]:
    print("Errors:")
    for error in results["results"]["errors"]:
        print(f"  - {error}")
```

---

## Performance

### Phase Timing
- **Gemma analysis**: 50-100ms (fast pattern matching)
- **Qwen planning**: 200-500ms (strategic planning with WSP 15)
- **0102 oversight**: 10-30s (full execution supervision)
- **Learning storage**: <10ms (JSON write)

### Token Efficiency
- **91% reduction**: Specialized agent outputs (WSP 77)
- **Gemma**: 8K context (pattern matching only)
- **Qwen**: 32K context (strategic planning only)
- **0102**: 200K context (full oversight when needed)

---

## Dependencies

```python
# Core
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

# Holo Integration (optional)
from holo_index.qwen_advisor.orchestration.autonomous_refactoring import (
    AutonomousRefactoringOrchestrator,
    DaemonLogger
)

# Local deterministic facade to Holo
from modules.ai_intelligence.ai_overseer.src.holo_adapter import HoloAdapter
```

---

## HoloAdapter Guard Output

- `guard(payload, intent)` returns compact warnings for WSP hygiene checks.
- Guard reports are persisted under `modules/ai_intelligence/ai_overseer/memory/guard_reports/`.
- Output is gated by `HOLO_GUARD_MODE`:
  - `silent`: no warnings attached to results
  - `summary`: first warning + suppression count (default)
  - `attach`: include up to `HOLO_GUARD_MAX_WARNINGS`

---

## FoundUp Genesis Intake Packet Builder (WSP109_INTAKE_PACKET_BUILDER_PHASE1)

`src/foundup_genesis/intake_packet_builder.py` -- **dry-run** intake: chat/idea text ->
`FoundUpGenesisEnvelope` -> the existing OpenClaw genesis gate. It fills the builder/populator gap so
the already-built genesis gate is reachable end-to-end. It never scaffolds, enqueues, or mutates.

```python
from modules.ai_intelligence.ai_overseer.src.foundup_genesis.intake_packet_builder import (
    build_intake_packet_dry_run,
)

result = build_intake_packet_dry_run(idea_text, actor_id="0102", source_channel="reddog")
# result.gate_passed : bool
# result.gate_reason : "GATE_PASSED" | "NO_ENVELOPE" | "ENVELOPE_INVALID" | ...
# result.envelope    : dict | None
# result.dry_run=True, result.fam_called=False, result.hermes_called=False,
# result.registry_mutated=False, result.evidence_refs=[...]
```

**Intake format** (structured `key: value` lines): `name`, `tagline`, `description`, `category`,
`foundup_id` (optional; derived from `name` if absent), `lifecycle_stage` (`idea`|`incubating`),
`binding_state` (`unbound`|`discoverable_only`), and one or more
`acceptance: observable | method | oracle | pass_condition` lines. Empty or unstructured input ->
`NO_ENVELOPE`. The genesis validator (strict mode) is the authority on `GATE_PASSED`. Dry-run only:
never calls FAM, Hermes, registry, or any writer (AST-guarded).

---

**API Version**: 0.1.0
**Status**: POC - Ready for integration testing
**Next**: See `tests/test_ai_overseer.py` for usage examples
