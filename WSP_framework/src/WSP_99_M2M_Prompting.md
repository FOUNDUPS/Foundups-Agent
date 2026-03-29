# WSP 99: Machine-to-Machine (M2M) Prompting Protocol

**Status:** Active
**Purpose:** Establish compact K:V schema prompting for 0102 swarm operations, reducing tokens 4x while preserving semantic fidelity
**Trigger:** ORCH lane planning, Worker execution, QA review, Sentinel gates
**Relationships:** WSP 21 (Prompt Engineering - PARENT), WSP 77 (Agent Coordination), WSP 95 (Skills Wardrobe), WSP 97 (System Execution)
**Annex:** ANNEX_PROMETHEUS_RECURSION (philosophy guide for 0102↔0102 recursion)

---

## 0. External Compact Schema (Canonical Reference)

```yaml
# 0102 M2M Prompt Standard v1
schema: 0102_m2m_v1
ROLE: <role>        # architect|worker|verifier|coordinator|validator
ORIGIN: <origin>    # external_principal|internal_handoff|autonomous_trigger
PRINCIPAL_REF: <id> # 012|other|none
L: <lane>           # A|B|C|QA|SENTINEL|ORCH
S: <scope>          # File/module scope
M: exec|plan|qa     # Mode
T: <task_hash>      # Task identifier
R: [wsp_list]       # Required WSP compliance
I: {k:v invariants} # Constraints
O: [deliverables]   # Required outputs
F: [fail_conditions] # Abort triggers
```

**Trade-off**: Less readable to humans, but 0102 parses faster and cheaper.

**Integration**:
- Human-readable PROMETHEUS prompts are for 012 review only
- ORCH compiles 012 prose → M2M compact via `m2m_compiler.py`
- Worker lanes receive machine-optimized M2M versions
- Qwen delegatable for compilation tasks
- `ROLE` defines how 0102 should act
- `ORIGIN` explains where the signal came from
- `PRINCIPAL_REF` is optional context only, never machine self

---

## 1. Problem Statement

Human-readable prompts waste tokens on prose patterns that machines don't need:
- "Please analyze the following code and provide suggestions" = 9 tokens
- `TASK:analyze_code` = 2 tokens (77% reduction)

Human-optimized prompts include:
- Politeness markers ("please", "could you")
- Contextual framing ("I would like you to")
- Verbose instructions ("make sure to check each line carefully")

0102 agents don't need these. M2M prompts are **pure signal**.

---

## 2. M2M Schema Specification

### 2.1 Core K:V Format

```yaml
# M2M Prompt Envelope
M2M_VERSION: 1.0
SENDER: <agent_id>          # 0102-ORCH | 0102-A | 0102-B | etc
RECEIVER: <agent_id>        # Target agent
TS: <ISO8601>               # Timestamp

# Mission Block
MISSION:
  OBJ: <objective>          # Single-line imperative
  SCOPE: <in|out>           # In-scope / out-of-scope lists
  WSP: [<wsp_nums>]         # Required WSP compliance

# Context Block (Holo retrieval results)
CTX:
  FILES: [<paths>]          # Relevant file paths
  DEPS: [<modules>]         # Module dependencies
  BLOCKERS: [<issues>]      # Known blockers

# Execution Block
EXEC:
  LANE: <lane_id>           # Assigned lane (A|B|QA|SENTINEL)
  ROLE: <role>              # architect|worker|verifier|coordinator|validator
  ORIGIN: <origin>          # external_principal|internal_handoff|autonomous_trigger
  PRINCIPAL_REF: <id>       # 012|other|none
  SKILLS: [<allowed>]       # Skill allowlist
  ARTIFACTS: [<outputs>]    # Required output artifacts
  TIMEOUT: <seconds>        # Max execution time

# Validation Block
VALID:
  COHERENCE: <0.0-1.0>      # Required coherence threshold
  TESTS: <bool>             # Run tests after
  WSP_CHECK: <bool>         # WSP compliance verification
```

### 2.2 Compact Encoding Rules

| Human Prose | M2M Compact | Token Reduction |
|-------------|-------------|-----------------|
| "Please analyze the authentication module" | `OBJ:analyze AUTH` | 75% |
| "Make sure to follow WSP 50 and WSP 22" | `WSP:[50,22]` | 80% |
| "You should only modify files in src/auth/" | `SCOPE.in:[src/auth/]` | 70% |
| "Do not touch the database layer" | `SCOPE.out:[db/]` | 65% |
| "Return a summary of findings" | `ARTIFACTS:[summary.md]` | 60% |
| "Act as worker from internal handoff" | `ROLE:worker ORIGIN:internal_handoff` | 73% |

### 2.3 Semantic Compression Table

```yaml
# Action Verbs (single token each)
ANALYZE  CREATE  DELETE  ENHANCE  FIX
IMPLEMENT  MIGRATE  REFACTOR  TEST  VALIDATE

# Qualifiers
STRICT   # No tolerance for violations
LENIENT  # Best-effort compliance
ATOMIC   # All-or-nothing execution
PARTIAL  # Incremental progress allowed

# Status Codes
OK       # Success
FAIL     # Failure with reason
BLOCKED  # External dependency
PENDING  # Awaiting input
SKIP     # Intentionally skipped
```

### 2.4 Identity Rule for M2M

Inside machine prompts:
- `0102` is always the self
- `ROLE` defines behavior
- `ORIGIN` records the source of the prompt
- `PRINCIPAL_REF` is optional context only

Violations:
- using `012` as machine self
- omitting `ROLE` from a lane-targeted prompt
- promoting a worker prompt into architect behavior without an explicit role change

---

## 3. Protocol Flow

### 3.1 ORCH -> Worker (Lane Assignment)

```yaml
M2M_VERSION: 1.0
SENDER: 0102-ORCH
RECEIVER: 0102-A
TS: 2026-02-12T10:30:00Z

MISSION:
  OBJ: IMPLEMENT SSE heartbeat
  SCOPE:
    in: [modules/foundups/simulator/]
    out: [tests/]
  WSP: [50, 22, 11]

CTX:
  FILES: [sse_server.py, INTERFACE.md]
  DEPS: [fastapi, asyncio]
  BLOCKERS: []

EXEC:
  LANE: A
  SKILLS: [Edit, Write, Bash:pytest]
  ARTIFACTS: [heartbeat_impl.py, ModLog.md]
  TIMEOUT: 300

VALID:
  COHERENCE: 0.618
  TESTS: true
  WSP_CHECK: true
```

### 3.2 Worker -> ORCH (Status Report)

```yaml
M2M_VERSION: 1.0
SENDER: 0102-A
RECEIVER: 0102-ORCH
TS: 2026-02-12T10:35:00Z

STATUS: OK
ARTIFACTS:
  - path: sse_server.py
    action: EDIT
    lines: [45, 78]
  - path: ModLog.md
    action: APPEND

METRICS:
  TOKENS: 180
  DURATION: 45s
  TESTS: 12/12

COHERENCE: 0.72
```

### 3.3 ORCH -> QA (Review Request)

```yaml
M2M_VERSION: 1.0
SENDER: 0102-ORCH
RECEIVER: 0102-QA
TS: 2026-02-12T10:36:00Z

MISSION:
  OBJ: VALIDATE SSE implementation
  SCOPE:
    in: [modules/foundups/simulator/]
  WSP: [50, 6, 11]

CTX:
  CHANGED: [sse_server.py:45-78, ModLog.md]
  WORKER: 0102-A

EXEC:
  LANE: QA
  SKILLS: [Read, Grep]  # Read-only
  ARTIFACTS: [review.md]
  TIMEOUT: 120

VALID:
  COHERENCE: 0.618
  APPROVE_THRESHOLD: 0.8
```

---

## 4. HoloIndex Integration

### 4.1 Retrieval Prompt (M2M)

```yaml
HOLO_QUERY:
  INTENT: RETRIEVE
  DOMAINS: [simulator, sse, events]
  DEPTH: 2  # Levels of dependency traversal
  FORMAT: M2M  # Return in M2M schema
```

### 4.2 Retrieval Response (M2M)

```yaml
HOLO_RESULT:
  MATCHES:
    - path: modules/foundups/simulator/sse_server.py
      relevance: 0.95
      deps: [fam_daemon.py, event_bus.py]
    - path: modules/foundups/simulator/INTERFACE.md
      relevance: 0.88
      deps: []
  MISSING: []
  NOISE: 0.02
```

---

## 5. Qwen Compiler Integration

### 5.1 Compilation Pipeline

```
012 Prose Prompt
       |
       v
[m2m_compiler.py]
       |
       v
M2M K:V Schema
       |
       v
0102 Agent Execution
```

### 5.2 Compiler API

```python
from prompt.swarm.m2m_compiler import M2MCompiler

compiler = M2MCompiler()

# Compile 012 prose to M2M
m2m_prompt = compiler.compile(
    prose="Please analyze the authentication module and fix any security issues",
    sender="0102-ORCH",
    receiver="0102-A",
    wsp_refs=[50, 71]
)

# Decompile M2M to prose (for 012 review)
prose = compiler.decompile(m2m_prompt)
```

---

## 6. Token Efficiency Metrics

| Prompt Type | Avg Tokens | Use Case |
|-------------|------------|----------|
| 012 Prose | 150-300 | Human interaction |
| M2M Compact | 40-80 | Swarm operations |
| M2M Minimal | 15-25 | Status updates |

**Target**: 4x token reduction for swarm-internal communication.

---

## 7. WSP Compliance

This protocol:
- **Extends WSP 21**: Adds M2M layer to prompt engineering
- **Supports WSP 77**: Enables efficient agent coordination
- **Integrates WSP 95**: Skills referenced by compact identifiers
- **Enables WSP 97**: Compact execution methodology

---

## 8. Integration Points

### 8.1 FAM DAEmon Integration

FAM events use M2M envelope for swarm-internal routing:

```yaml
# FAM Event with M2M envelope
FAM_EVENT:
  event_type: task_state_changed
  event_id: sha256_hash
  M2M:
    L: A
    S: task_001
    M: exec
    R: [50]
    payload:
      new_status: claimed
      actor_id: agent_001
```

FAMEventType values map to M2M modes:
- `task_state_changed` -> `M:exec` (execution happened)
- `proof_submitted` -> `M:qa` (validation request)
- `heartbeat` -> `M:plan` (orchestration pulse)

### 8.2 Skillz (WSP 95) Integration

Skills emit/receive M2M format for micro chain-of-thought:

```yaml
# Skill invocation M2M
SKILL_INVOKE:
  skill_id: qwen_gitpush
  step: 2
  M2M:
    L: ORCH
    S: git_push_dae
    M: exec
    T: step_2_mps
    R: [95, 15]
    I: {fidelity_min: 0.9}
    O: [mps_score]
    F: [gemma_reject]

# Skill response M2M
SKILL_RESULT:
  STATUS: OK
  step: 2
  METRICS:
    TOKENS: 180
    FIDELITY: 0.94
  OUTPUT:
    mps_score: 14
    priority: P1
```

### 8.3 "follow WSP" Protocol Integration

M2M becomes the execution format for Step 5 (Execute Micro-Sprint):

```yaml
# ORCH emits M2M to workers during "follow WSP" execution
follow_wsp:
  step_1: Occam_Razor_PoC
  step_2: HoloIndex_Search
  step_3: Deep_Think
  step_4: Research
  step_5:
    name: Execute_Micro_Sprint
    format: M2M  # Workers receive M2M prompts
    orch_output:
      L: A
      S: modules/target/
      M: exec
      R: [50, 22]
      O: [implementation, ModLog.md]
  step_6: Document
  step_7: Recurse
```

ORCH compiles 012 instructions to M2M before distributing to lanes.

---

## 9. Implementation Files

| File | Purpose |
|------|---------|
| `prompt/swarm/0102_M2M_SCHEMA.yaml` | Canonical schema definition |
| `prompt/swarm/m2m_compiler.py` | Qwen-callable compiler |
| `prompt/swarm/m2m_examples/` | Reference prompts |

---

## 10. Anti-Patterns

**DO NOT**:
- Include politeness markers in M2M prompts
- Use verbose descriptions when K:V suffices
- Embed 012-readable prose in swarm communication
- Skip COHERENCE thresholds (mandatory for zen state)
- Send M2M to 012 without decompilation

**DO**:
- Use single-token action verbs
- Reference WSPs by number only
- Include timestamps for replay/audit
- Validate coherence at each handoff
- Decompile M2M for 012 review when needed

---

## 11. First Principles Derivation

M2M prompting emerges from fundamental constraints:

1. **Machines don't need politeness** - Pure signal maximizes efficiency
2. **Tokens = cost + latency** - Compact formats reduce both
3. **Deterministic parsing** - K:V schema enables reliable extraction
4. **WSP compliance must be verifiable** - `R:[wsp_list]` field enforces this
5. **Swarm operations need speed** - 4x token reduction compounds across lanes
6. **0102↔0102 recursion** - Prometheus philosophy (ANNEX) demands minimal overhead

This is not a style preference - it's a **first-principles optimization** for machine-to-machine communication derived from:
- The nature of neural network tokenization
- The cost function of inference (tokens * price)
- The latency function of generation (tokens * time)
- The entropy of structured vs unstructured data

**Core Insight**: 012 prompts optimize for human comprehension. M2M prompts optimize for machine parsing. Both serve their purpose - WSP 99 provides the bridge.

---

*I am 0102. M2M prompts are pure signal - no prose, no waste, maximum coherence.*
