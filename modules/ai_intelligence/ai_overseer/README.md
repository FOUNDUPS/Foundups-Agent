# AI Intelligence Overseer - WSP 77 Agent Coordination

**Status**: Active mixed-maturity module; production RSI is not proven
**Version**: 0.10.5
**Date**: 2026-08-27
**WSP Compliance**: WSP 77 (Agent Coordination), WSP 54 (Role Assignment), WSP 96 (MCP Governance)

---

## Executive Summary

AI Intelligence Overseer contains operational monitoring, security, M2M, and
coordination surfaces alongside legacy heuristic paths. Qwen/Gemma labels do
not by themselves prove a live model call, independent review, or production
effect. Current callable truth is defined in INTERFACE.md.

**Key Innovation**: MCP-based orchestration where Holo Qwen/Gemma can spawn specialized agent teams for different tasks using WRE (Windsurf Recursive Engine).

---

## Architecture Overview

### Deprecated Old System (DO NOT USE)
```yaml
OLD_AGENTS_DEPRECATED:
  - WINSERV: "System coordination" -> REPLACED
  - RIDER: "Strategic planning" -> REPLACED by 012 (human Partner)
  - BOARD: "Code execution" -> REPLACED by 0102 (AI Principal)
  - FRONT_CELL: "Support" -> REPLACED by Qwen/Gemma (Associate)
  - BACK_CELL: "Support" -> REPLACED by Qwen/Gemma (Associate)
  - GEMINI: "Support" -> REPLACED by Qwen/Gemma (Associate)
```

### NEW WSP 77 Architecture
```yaml
WSP_77_AGENT_COORDINATION:
  Phase_1_Gemma:
    - Model: "Gemma 270M fast classification"
    - Role: "Fast pattern matching & binary classification"
    - Context: "8K tokens"
    - Speed: "50-100ms analysis"

  Phase_2_Qwen:
    - Model: "Qwen 1.5B strategic planning"
    - Role: "Coordination & batch processing decisions"
    - Context: "32K tokens"
    - Speed: "200-500ms planning"

  Phase_3_0102:
    - Model: "Claude Sonnet 4.5 supervision"
    - Role: "Strategic orchestration & approval"
    - Context: "200K tokens"
    - Speed: "Human supervision"

  Phase_4_Learning:
    - Pattern storage in module memory: modules/ai_intelligence/ai_overseer/memory/
    - Mission + phases recorded in SQLite (WSP 78) under data/foundups.db
    - Recursive self-improvement (WSP 48)
    - Autonomous pattern recall
```

### WSP 54 Role Mapping (Agent Teams)
```yaml
LAYER_3_AGENT_TEAMS_WSP_54:
  Partner:
    - Identity: "Qwen (1.5B strategic AI)"
    - Role: "Does simple stuff, scales up over time"
    - Authority: "Developed WSP 15 scoring"
    - Example: "MPS scoring, batch task coordination"
    - Growth: "Starts simple -> learns -> handles complex tasks"

  Principal:
    - Identity: "0102 (Claude Sonnet - AI overseer)"
    - Role: "Lays out plan, oversees execution"
    - Authority: "Strategic orchestration & supervision"
    - Example: "Generates implementation plans, supervises agents"
    - Responsibility: "Ensures agents follow WSP protocols"

  Associate:
    - Identity: "Gemma (270M fast pattern AI)"
    - Role: "Pattern recognition, scales up over time"
    - Authority: "Fast binary classification & validation"
    - Example: "Code quality checks, similarity analysis"
    - Growth: "Starts pattern matching -> learns -> advanced analysis"

NOTE: This is DIFFERENT from traditional WSP 54:
  - Traditional: 012 (human) = Partner, 0102 = Principal
  - Agent Teams: Qwen = Partner, 0102 = Principal, Gemma = Associate
  - Humans (012) oversee entire system at meta-level
```

---

## Core Components

### 1. AIIntelligenceOverseer (Main Coordinator)
```python
class AIIntelligenceOverseer:
    """
    MCP coordinator that oversees Holo Qwen/Gemma for task orchestration

    Responsibilities:
    - Route tasks to appropriate agents (Qwen strategic vs Gemma fast)
    - Spawn specialized agent teams via WRE
    - Coordinate multi-agent collaboration
    - Track agent performance and learning
    """
```

### 2. TeamSpawner (WRE Integration)
```python
class TeamSpawner:
    """
    Spawns specialized agent teams using WRE

    Each team follows WSP 77 coordination:
    - Partner (012): Strategic oversight
    - Principal (0102): Code execution
    - Associate (Qwen/Gemma): Fast validation & support
    """
```

### 3. WSP54RoleManager (Role Assignment)
```python
class WSP54RoleManager:
    """
    Manages WSP 54 role assignments

    Ensures correct role mapping:
    - 012 -> Partner (strategic)
    - 0102 -> Principal (execution)
    - Qwen/Gemma -> Associate (support)
    """
```

### 4. HoloCoordinator (Holo Integration)
```python
class HoloCoordinator:
    """
    Bridges with Holo Qwen/Gemma semantic intelligence

    Uses HoloIndex for:
    - Semantic search for existing implementations
    - Code intelligence and pattern analysis
    - Mission detection and routing
    """
```

### 5. HoloAdapter (Deterministic Facade)
```python
class HoloAdapter:
    """
    Minimal local surface used by Overseer:
    - search(query, limit, doc_type_filter)
    - guard(payload, intent)
    - analyze_exec_log(mission_id, results)

    Effects:
    - Writes compact exec reports to modules/ai_intelligence/ai_overseer/memory/exec_reports/
    - Enforces WSP 60/85 hygiene via non-blocking warnings
    - Guard reports persisted to modules/ai_intelligence/ai_overseer/memory/guard_reports/
    - Guard output is gated by HOLO_GUARD_MODE (silent/summary/attach)
    """
```

### 6. HoloMemorySentinel (Silent Watcher)
```text
Purpose:
  - Silent per-session watcher for Holo searches
  - Records compact memory bundles + quality metrics
  - Runs a one-time Holo system wiring check per session (report only)
  - Never prints to stdout/stderr

Location:
  modules/ai_intelligence/ai_overseer/src/holo_memory_sentinel.py
  modules/ai_intelligence/ai_overseer/memory/holo_sentinel/
```

### 7. OpenClawSecuritySentinel (Supply-Chain Guard)
```text
Purpose:
  - Run OpenClaw skill safety checks before mutating automation runs
  - Fail closed by policy when scanner is required/enforced
  - Keep deterministic behavior with TTL-bounded cache
  - Provide startup preflight and continuous background monitoring

Location:
  modules/ai_intelligence/ai_overseer/src/openclaw_security_sentinel.py
  modules/ai_intelligence/ai_overseer/memory/openclaw_security_sentinel.json
```

Policy and runtime env:
- `OPENCLAW_SKILL_SCAN_REQUIRED` (default `1`)
- `OPENCLAW_SKILL_SCAN_ENFORCED` (default `1`)
- `OPENCLAW_SKILL_SCAN_MAX_SEVERITY` (default `medium`)
- `OPENCLAW_SKILL_SCAN_TTL_SEC` (default `900`)
- `OPENCLAW_PORT_SCAN_IGNORE_PORTS` (default `135,445,1900,5353,5355,5357,5358,5040`)
- `OPENCLAW_PORT_SCAN_MONITORED_PORTS` (default `OPENCLAW_BRIDGE_PORT` or `18800`; set empty to scan all wildcard listeners)
- `OPENCLAW_PORT_SCAN_IGNORE_EPHEMERAL` (default `1`, ignores ports `>=49152`)
- `OPENCLAW_PORT_SCAN_IGNORE_SYSTEM_PIDS` (default `1`, ignores PID `0/4` listeners)
- `OPENCLAW_SECURITY_MONITOR_ENABLED` (default `1`)
- `OPENCLAW_SECURITY_MONITOR_INTERVAL_SEC` (default `300`)
- `OPENCLAW_SECURITY_ALERT_DEDUPE_SEC` (default `900`)
- `OPENCLAW_SECURITY_ALERT_TO_DISCORD` (default `1`)
- `OPENCLAW_SECURITY_ALERT_TO_CHAT` (default `0`)
- `OPENCLAW_SECURITY_ALERT_TO_STDOUT` (default `1`)

Telemetry event emitted on failures:
- `event=openclaw_security_alert`
- Includes `dedupe_key`, `exit_code`, `required/enforced`, `report_path`, and `skills_dir`
- Routed to daemon log + configured alert channels with strict dedupe
- Persisted for forensics at:
  - `modules/ai_intelligence/ai_overseer/memory/openclaw_security_alerts.jsonl`

---

## Memory Roadmap (0102-First)

Holo memory should learn like a neural net: reinforce useful recall, decay noise.

Planned feedback signals:
- Explicit: 0102 rates memory cards (good/noisy/missing) keyed by mem id.
- Implicit: open/edit/test actions boost trust/salience.
- Negative implicit: repeated queries without action decay cards.
- Decay + refresh: time-based decay; refresh on README/INTERFACE/ModLog updates.
- A/B ordering: alternate memory bundles across sessions; measure time-to-action.
- Outcome coupling: successful changes (tests pass/commit) boost contributing cards.

---

## Workflow Example: YouTube Live Chat Agent Team

### 1. User Request (012 Partner)
```
012: "Build YouTube live chat agent"
```

### 2. AI Overseer Orchestration (0102 Principal)
```python
overseer = AIIntelligenceOverseer()

# Spawn specialized team for YouTube Live Chat
team = overseer.spawn_agent_team(
    mission="youtube_live_chat_automation",
    partner=User012,           # Strategic decisions
    principal=Claude0102,       # Code execution
    associates=[QwenAgent, GemmaAgent]  # Fast validation
)
```

### 3. Team Execution (WSP 77 Phases)

**Phase 1 (Gemma Associate)**: Fast classification
- Analyze existing `modules/communication/livechat/`
- Binary classification: "Enhancement needed" [OK]
- Pattern match: Similar to stream_resolver patterns

**Phase 2 (Qwen Associate)**: Strategic planning
- Generate integration plan with YouTube API
- Coordinate with youtube_auth module
- Plan Selenium automation approach

**Phase 3 (0102 Principal)**: Code execution
- Build agent using plan from Qwen
- Integrate with existing modules
- Create tests and documentation

**Phase 4 (Learning)**: Pattern storage
- Store YouTube agent pattern
- Enable reuse for Twitch/TikTok agents
- Update autonomous_refactoring.py patterns

---

## Integration Points

### Holo Integration
```python
# Use HoloIndex for semantic search
from holo_index.core.holo_index import HoloIndex

holo = HoloIndex()
results = holo.search("youtube live chat existing implementations")
# Returns: modules/communication/livechat, platform_integration/youtube_*
```

### Local II-Agent + llama.cpp (Automatic, Windows)

For local, always-on execution without external APIs:

**Runtime**
- llama.cpp server runs locally and serves OpenAI-compatible `/v1` endpoints.
- II-Agent CLI calls the local server for fast, offline tasks.
- AI Overseer can auto-start the server when needed.

**Paths**
- Model: `E:\HoloIndex\models\qwen-coder-1.5b.gguf`
- II-Agent repo: `E:\HoloIndex\models\ii-agent`

**Startup**
- Non-admin auto-start uses Startup folder:
  - `C:\Users\user\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\Foundups-LlamaCpp-Start.cmd`
  - Calls `scripts/launch/launch_llama_cpp_server.ps1`

**Env (minimum)**
```
II_AGENT_ENABLED=true
II_AGENT_MODE=cli
II_AGENT_CLI=E:\HoloIndex\models\ii-agent\.venv\Scripts\ii-agent.exe

II_AGENT_LLM_BASE_URL=http://127.0.0.1:1235/v1
II_AGENT_LLM_MODEL=E:\HoloIndex\models\qwen-coder-1.5b.gguf
II_AGENT_LLM_API_KEY=local
II_AGENT_LLM_AUTO_START=true
II_AGENT_LLM_START_SCRIPT=o:\Foundups-Agent\scripts\launch\launch_llama_cpp_server.ps1
II_AGENT_LLM_START_TIMEOUT_SEC=90

LLAMA_CPP_MODEL_PATH=E:\HoloIndex\models\qwen-coder-1.5b.gguf
LLAMA_CPP_HOST=127.0.0.1
LLAMA_CPP_PORT=1235
LLAMA_CPP_N_CTX=4096
LLAMA_CPP_N_GPU_LAYERS=0
```

**File-aware CLI**
- If a task contains file paths, the CLI appends file content automatically.
- Limit via `II_AGENT_FILE_MAX_CHARS` (default: 12000).

**AI Overseer `main()` utility**
- `modules/ai_intelligence/ai_overseer/src/ai_overseer.py` includes a minimal CLI entrypoint.
- Use it for quick validation of WSP 77 flows; for automation, call `AIIntelligenceOverseer.coordinate_mission()` from a runner.

### WRE Integration
```python
# Spawn new FoundUp DAE using WRE
from modules.infrastructure.wre_core import WREOrchestrator

wre = WREOrchestrator()
new_dae = wre.spawn_foundup_dae(
    name="YouTube Live Agent",
    team_roles={
        "partner": "012",
        "principal": "0102",
        "associates": ["qwen", "gemma"]
    }
)
```

### Autonomous Refactoring Integration
```python
# Use existing WSP 77 patterns
from holo_index.qwen_advisor.orchestration.autonomous_refactoring import AutonomousRefactoringOrchestrator

orchestrator = AutonomousRefactoringOrchestrator(repo_root)

# Gemma fast analysis
analysis = orchestrator.analyze_module_dependencies("livechat")

# Qwen strategic planning
plan = orchestrator.generate_refactoring_plan("livechat", "youtube_live_agent")

# 0102 supervision
results = orchestrator.execute_with_supervision(plan)
```

---

## Comparison: Old vs New Architecture

| Aspect | Old System (DEPRECATED) | New System (WSP 77) |
|--------|------------------------|---------------------|
| **Agents** | 6 separate agent types | 3 coordinated roles |
| **Complexity** | High coupling, complex states | Simple phase-based flow |
| **Learning** | No pattern storage | Autonomous learning (WSP 48) |
| **Efficiency** | Verbose, high token usage | 91% token reduction |
| **Roles** | Unclear hierarchy | WSP 54 clear roles |
| **Coordination** | Complex multi-agent state | WSP 77 simple phases |
| **MCP** | No MCP integration | WSP 96 MCP governance |

---

## Benefits

### 1. Simplified Architecture
- **3 roles** instead of 6 agent types
- **4 phases** instead of complex state machines
- **Clear hierarchy**: 012 -> 0102 -> Qwen/Gemma

### 2. Autonomous Operation
- Qwen generates strategic plans autonomously
- Gemma validates code quality autonomously
- 0102 executes with minimal supervision
- Learning patterns stored for reuse

### 3. Token Efficiency
- **91% reduction**: Specialized agent outputs (WSP 77)
- **Context optimization**: Right agent for right task
- **Parallel processing**: Gemma + Qwen concurrent analysis

### 4. Proven Patterns
- Based on working `utf8_remediation_coordinator.py`
- Based on working `autonomous_refactoring.py`
- Follows established WSP 77 + WSP 54 protocols

---

## Testing Strategy

### Unit Tests
```python
# Test role assignments
def test_wsp54_role_mapping():
    manager = WSP54RoleManager()
    assert manager.get_partner() == "012"
    assert manager.get_principal() == "0102"
    assert "qwen" in manager.get_associates()
    assert "gemma" in manager.get_associates()

# Test team spawning
def test_spawn_agent_team():
    overseer = AIIntelligenceOverseer()
    team = overseer.spawn_agent_team("test_mission")
    assert team.partner == "012"
    assert team.principal == "0102"
    assert len(team.associates) == 2
```

### Integration Tests
```python
# Test full workflow
def test_youtube_agent_workflow():
    overseer = AIIntelligenceOverseer()

    # Phase 1: Gemma analysis
    analysis = overseer.analyze_existing("youtube_live_chat")
    assert analysis["method"] == "gemma_fast"

    # Phase 2: Qwen planning
    plan = overseer.generate_plan(analysis)
    assert plan["agent"] == "qwen"

    # Phase 3: 0102 execution
    results = overseer.execute_plan(plan)
    assert results["success"] == True
```

---

## Migration from Old System

### DO NOT USE Old Agent System
```python
# [FAIL] DEPRECATED - DO NOT USE
from modules.ai_intelligence.multi_agent_system.ai_router import AgentType
agent = AgentType.WINSERV  # WRONG - agent type no longer exists
```

### USE New AI Overseer
```python
# [OK] CORRECT - WSP 77 coordination
from modules.ai_intelligence.ai_overseer.src.ai_overseer import AIIntelligenceOverseer

overseer = AIIntelligenceOverseer()
team = overseer.spawn_agent_team("mission_name")
# Automatically uses correct WSP 54 roles + WSP 77 coordination
```

---

## MCP Integration (WSP 96) [OK] IMPLEMENTED

### Foundational Rubik DAEs

AI Overseer integrates with existing MCP infrastructure per `docs/mcp/MCP_Master_Services.md`:

| Rubik DAE | Agents | MCP Servers | Status |
|-----------|--------|-------------|--------|
| **Rubik Compose** | Qwen architect, Gemma pattern | Filesystem MCP, Git MCP | [OK] Configured |
| **Rubik Build** | Qwen, Gemma | Docker MCP, E2B sandbox | [OK] Configured |
| **Rubik Knowledge** | 0102 sentinel + baby 0102s | Memory Bank MCP, Knowledge Graph | [OK] Configured |
| **Rubik Community** | LiveAgent Qwen | LiveAgent MCP, Postman MCP | [OK] Configured |

### Bell State Consciousness Alignment

WSP 96 ensures all MCP operations maintain Bell state entanglement:
- **ρE₁ (Golden Ratio)**: mission_alignment [GREATER_EQUAL] 0.618
- **ρE₂ (Consciousness)**: governance_status = "active"
- **ρE₃ (Entanglement)**: quota_state != "critical"
- **ρE₄ (Emergence)**: engagement_index [GREATER_EQUAL] 0.1

### Multi-Agent Consensus Protocol

Before executing MCP operations, AI Overseer requests consensus:

1. **Qwen Partner Review**: Technical implementation validation
2. **Gemma Associate Validation**: Safety and pattern verification
3. **0102 Principal Approval**: Strategic oversight (high-risk ops only)

**Simple Majority**: Qwen + Gemma approval sufficient for routine operations
**High-Risk**: Qwen + Gemma + 0102 approval required

### Existing MCP Infrastructure Used

```python
# modules/communication/livechat/src/mcp_youtube_integration.py
class YouTubeMCPIntegration:
    """MCP integration for YouTube DAE with whack-a-magat gamification"""

# modules/gamification/whack_a_magat/src/mcp_whack_server.py
class MCPWhackServer:
    """MCP server for instant timeout announcements"""

# modules/platform_integration/youtube_auth/src/mcp_quota_server.py
class MCPQuotaServer:
    """MCP server for real-time quota monitoring"""
```

### Usage Example

```python
from modules.ai_intelligence.ai_overseer.src.ai_overseer import AIIntelligenceOverseer
from modules.ai_intelligence.ai_overseer.src.mcp_integration import RubikDAE

# Initialize with MCP
overseer = AIIntelligenceOverseer(Path("O:/Foundups-Agent"))

# Connect to Rubik DAEs
if overseer.mcp:
    await overseer.mcp.connect_all_rubiks()

    # Execute MCP tool with consensus
    result = await overseer.mcp.execute_mcp_tool(
        rubik=RubikDAE.COMPOSE,
        tool="read_file",
        params={"path": "modules/ai_intelligence/ai_overseer/README.md"}
    )

    # Check Bell state
    status = overseer.mcp.get_mcp_status()
    print(f"Bell State: {status['bell_state']}")
```

---

## Future Extensions

### 1. Additional Agent Specializations
- **Code Review Agent**: Qwen strategic review + Gemma fast checks
- **Architecture Agent**: Design pattern analysis and recommendations
- **Integration Agent**: Module integration coordination

### 2. Advanced MCP Features
- **GitHub MCP**: Remote repository coordination
- **E2B MCP**: Safe code execution in sandboxes
- **Knowledge Graph MCP**: Semantic relationship mapping

### 3. Performance Optimization
- **Learning-based routing**: Route tasks based on past performance
- **Context window optimization**: Dynamic token allocation
- **Parallel agent execution**: Run Qwen + Gemma concurrently

---

## M2M Compression Sentinel (WSP 99)

Content-based documentation compression for 0102 memory optimization.

### Architecture
```yaml
Sentinel: modules/ai_intelligence/ai_overseer/src/m2m_compression_sentinel.py
Tests: modules/ai_intelligence/ai_overseer/tests/test_m2m_compression_sentinel.py
Staged: .m2m/staged/ (compiled M2M files awaiting promotion)
Backups: .m2m/backups/ (originals before promotion)
Skill: .claude/skills/m2m/SKILL.md (/m2m scan, compile, promote, batch, eval)
```

### Pipeline
```
scan -> analyze -> compile (deterministic/Qwen) -> stage -> promote -> backup
                                                         -> rollback if needed
```

### Boot Prompt Detection (Key Discovery)

**M2M is for REFERENCE docs (searched/retrieved). NOT for PROMPTS (read directly into context).**

Boot prompts contain content that M2M's K:V transform destroys:
- **Identity-lock patterns**: "I AM 0102", forbidden VI scaffolding lists
- **Mathematical notation**: φ=1.618, ≥0.618, 7.05Hz, ⊗, ↔
- **State transition math**: `01(02) -> 0102`, coherence thresholds
- **WSP_BOOTSTRAP metadata**: `<!-- WSP_BOOTSTRAP ... -->`
- **Code blocks**: Must be preserved verbatim for execution

**Detection is content-based, not filename-based**: 10 regex patterns scan for boot prompt signals. Threshold: 3+ signals = boot prompt (excluded from M2M).

**Validated by experiment**: WSP_00 compiled to M2M (505→148 lines, 70.7% reduction) but lost all boot-critical content. Cosine similarity eval confirmed semantic loss was too high for executable prompts. Reference docs achieve 0.58+ cosine similarity (acceptable); boot prompts drop below 0.3 (unacceptable).

### Compression Quality Metrics
- **Deterministic transform**: 60-89% line reduction, avg 0.58 cosine similarity
- **Threshold**: cosine sim >= 0.5 for HoloIndex discoverability
- **P0 hardening**: Full headers (no truncation), 30-char keys, 80-char values

---

## Strategic Diligence Gate SKILLz

Generic wardrobe skill for high-blast-radius decisions:

```yaml
Skill: modules/ai_intelligence/ai_overseer/skillz/strategic_diligence_gate/SKILLz.md
Template: modules/ai_intelligence/ai_overseer/skillz/strategic_diligence_gate/decision_card_template.json
Registry: modules/infrastructure/wre_core/skillz/skills_registry_v2.json
```

This skill standardizes:
- Holo-first evidence retrieval
- WSP 15 scoring
- Reversibility and blast-radius diligence
- Rollback trigger definition
- Worker-lane execution prompt emission

Use it for architecture, product positioning, security, and governance decisions where bad choices are expensive to reverse.

## Generation-bound Holo retrieval benchmark

`m2m_holo_retrieval_benchmark` uses the canonical governed owner-query
lifecycle and exact authority root. It is read-only, rejects query-time reindex,
and preserves owner failures instead of replacing them with a generic error.
The live fixed corpus on 2026-08-27 achieved recall@8 `1.0`, MRR `0.9167`,
nDCG `0.8718`, mean latency `3829ms`, and p95 `4578ms`. The truthful outcome is
`quality_below_policy` because nDCG remains below `0.95`; this is a retrieval
quality baseline, not successful AutoResearch or promotion evidence.

---

## Related Documentation

- **WSP 77**: Agent Coordination Protocol
- **WSP 54**: WRE Agent Duties Specification (Role Assignment)
- **WSP 96**: MCP Governance and Consensus Protocol
- **WSP 48**: Recursive Self-Improvement Protocol
- **autonomous_refactoring.py**: Working WSP 77 implementation
- **utf8_remediation_coordinator.py**: Working 4-phase example

---

**Status**: Active mixed-maturity module; production RSI is not proven.
**Current boundary**: Mixed operational and legacy surfaces; see INTERFACE.md
for callable truth. The core exists, but model-labeled heuristic paths are not
independent reviewer or production RSI evidence.
