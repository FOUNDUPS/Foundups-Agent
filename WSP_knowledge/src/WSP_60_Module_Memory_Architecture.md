# WSP 60: Module Memory Architecture
- **Status:** Active specification; runtime implementation is partial
- **Purpose:** To define the modular memory architecture where each module manages its own persistent data storage following WSP_3 Enterprise Domain organization, integrated with the three-state WSP architecture and HoloDAE intelligence layer.
- **Trigger:** When a module needs to store persistent data, session state, or configuration information.
- **Input:** Module-specific data requiring persistence (sessions, cache, configuration, logs).
- **Output:** Organized, module-specific memory storage with clear data ownership and isolation across WSP three-state architecture.
- **Responsible Agent(s):** HoloDAE target role, module-specific DAEs, WSP 54 agents.

## 1. Overview

This protocol establishes a modular memory architecture where each module manages its own persistent data storage, integrated with the WSP three-state architecture and HoloDAE foundational intelligence system. This architecture ensures proper data isolation, follows WSP_3 Enterprise Domain organization, integrates with WSP_49 Module Directory Structure Standards, and enables HoloDAE and module-specific DAEs to manage memory across all architectural states.

### 1.1 Current implementation boundary (2026-08-28)

This WSP is the normative memory architecture, not proof that every described
HoloDAE service is running. The governed HoloIndex owner currently provides
generation-bound, read-only semantic retrieval over sealed snapshots. It does
not currently provide a production feedback-to-ranker loop, autonomous pattern
promotion, canary admission, rollback, or candidate-bound outcome learning.
The experimental `holo_index/adaptive_learning/` package is disabled in the
production CLI path and grants no write or promotion authority. Statements
below about feedback, pattern evolution, cross-module validation, monitoring,
and autonomous management are requirements or roadmap targets unless an
implementation contract and executable evidence explicitly bind them.

## 2. HoloDAE Foundational Architecture

### 2.1 Target DAE Architecture (WSP 80)

The architecture is designed for **infinite DAE composition**:

```
FOUNDATIONAL INTELLIGENCE:
HoloDAE -> Green LEGO baseboard that all modules connect to
        -> Provides semantic search, compliance checking, pattern memory
        -> Replaces old ComplianceAgent, JanitorAgent, ChroniclerAgent

CORE INFRASTRUCTURE DAEs (5 System-Wide):
[U+251C][U+2500][U+2500] Infrastructure DAE -> Spawns new FoundUp DAEs via WRE
[U+251C][U+2500][U+2500] Compliance DAE -> HoloDAE serves this role (WSP compliance)
[U+251C][U+2500][U+2500] Knowledge DAE -> Shared pattern memory for all DAEs
[U+251C][U+2500][U+2500] Maintenance DAE -> System-wide optimization and cleanup
[U+2514][U+2500][U+2500] Documentation DAE -> Registry of all FoundUp DAEs

FOUNDUP DAEs ([U+221E] Infinite):
[U+251C][U+2500][U+2500] YouTube FoundUp DAE -> Manages YouTube cube memory
[U+251C][U+2500][U+2500] LinkedIn FoundUp DAE -> Manages LinkedIn cube memory
[U+251C][U+2500][U+2500] X/Twitter FoundUp DAE -> Manages X/Twitter cube memory
[U+251C][U+2500][U+2500] PQN Alignment DAE -> Manages PQN research memory
[U+2514][U+2500][U+2500] ...[U+221E] more as created through WSP 27/73 process
```

### 2.2 HoloDAE Memory Management Target

HoloDAE is required to provide these foundational memory services as their
individual runtime contracts are implemented and verified:
- **Pattern Memory**: Stores successful patterns for instant recall
- **Breadcrumb Tracing**: Multi-agent discovery sharing via AgentDB
- **Violation Tracking**: WSP compliance history and prevention
- **Chain-of-Thought Logging**: Decision trails for recursive improvement
- **Effectiveness Scoring**: Performance metrics for continuous optimization

## 3. Three-State Memory Architecture

### 3.1 WSP Three-State Memory Organization

The WSP framework operates on a **three-state architecture** where memory and data storage is organized across distinct states:

```
State 0 (WSP_knowledge/):      Foundational "memory" layer - Archives & Backups
[U+251C][U+2500][U+2500] reports/                   -> Migration & analysis reports
[U+251C][U+2500][U+2500] logs/                      -> Historical system logs
[U+251C][U+2500][U+2500] memory_backup_wsp60/       -> WSP 60 migration backups & historical memory
[U+251C][U+2500][U+2500] historic_assets/           -> Historical assets & documentation
[U+2514][U+2500][U+2500] docs/                      -> Documentation archives

State 1 (WSP_framework/):      Protocol "scaffolding" layer - Specifications
[U+2514][U+2500][U+2500] src/                       -> WSP protocol specifications & framework docs

State 2 (WSP_agentic/):        Active "operational" layer - Live Operations
[U+2514][U+2500][U+2500] src/                       -> Live agentic operations & runtime data

Active Modules (modules/):     Enterprise Operations - Module-Specific Memory
[U+2514][U+2500][U+2500] [domain]/[module]/memory/  -> Individual module persistent storage

HoloDAE Memory (E:/HoloIndex/):  Foundational Intelligence Layer
[U+251C][U+2500][U+2500] chromadb/                  -> Vector database for semantic search
[U+251C][U+2500][U+2500] models/                    -> LLM models for intelligence
[U+251C][U+2500][U+2500] patterns/                  -> Learned patterns and violations
[U+2514][U+2500][U+2500] breadcrumbs/              -> Multi-agent discovery trails
```

### 3.2 Memory Architecture Principles

#### **State 0 - Foundational Memory (WSP_knowledge/)**
- **Purpose**: Historical archives, migration backups, foundational knowledge
- **Location**: `WSP_knowledge/memory_backup_wsp60/`
- **Content**: WSP 60 migration backups, historical memory snapshots, legacy data archives
- **Management**: HoloDAE archives, automated cleanup of old archives
- **Access**: Read-only for historical reference, managed by HoloDAE

#### **Module-Level Memory (modules/[domain]/[module]/memory/)**
- **Purpose**: Module-specific persistent data storage
- **Access**: Only the owning module should write to its memory directory
- **WSP Compliance**: Follows WSP_3 Enterprise Domain structure
- **Management**: Module DAE management, HoloDAE validation

#### **HoloDAE Memory (E:/HoloIndex/)**
- **Purpose**: Foundational intelligence and pattern memory
- **Access requirement**: DAEs query through governed readers; only an admitted HoloDAE maintenance owner may write
- **Content**: Semantic search indexes, WSP patterns, violation history
- **Management target**: HoloDAE-governed maintenance with effectiveness scoring

#### **Module-Specific Memory Extensions**
- **Location**: `modules/[domain]/[module]/memory/` (per WSP 49)
- **Purpose**: Module-specific persistent data storage with isolation
- **Examples**:
  - `holo_index/adaptive_learning/execution_log_analyzer/memory/` - Processing artifacts, task coordination, analysis results
  - `holo_index/adaptive_learning/discovery_evaluation_system/memory/` - Evaluation results, performance metrics, capability assessments
- **Access**: Module owner manages, HoloDAE validates compliance
- **Management**: Automatic cleanup, version control integration, backup procedures

### 3.3 0102 Memory Model (Semantic/Episodic/Procedural/Working)

To make memory actionable for 0102, HoloDAE organizes recall into four layers:
- **Semantic Memory**: Stable knowledge (code index + WSP docs + README/INTERFACE/ARCH docs).
- **Episodic Memory**: What was seen and chosen (queries, results, session context).
- **Procedural Memory**: How to act (WSP protocols + skills/workflows).
- **Working Memory**: The current Holo result pack used for the next decision.

These layers should be represented in indexed data, not only prose, so pattern-matchers can retrieve them reliably.

### 3.4 Memory-First Retrieval Contract (HoloIndex)

HoloIndex output must lead with memory so 0102 reads recall before raw results.

**Output Order**:
1. `[MEMORY]` compact memory bundle (3-5 cards)
2. `[RESULTS]` code/WSP hits
3. `[ACTIONS]` (if any)

**Memory Card Schema (machine-first)**:
```
[MEMORY]
- id: mem:<hash>
  module: infrastructure/wre_core
  doc_type: wsp|readme|modlog|interface|generated
  wsp: WSP 60
  intent: memory|build|fix|refactor
  summary: "1-2 lines, ASCII, no fluff"
  pointers:
    - WSP_framework/src/WSP_60_Module_Memory_Architecture.md#3.3
    - modules/infrastructure/wre_core/README.md#memory
  salience: 0.82
  trust: 0.90
  last_seen: 2026-01-04T19:21:22Z
```

Memory bundles are stored under the generating module's `memory/` directory for later recall and auditing.

### 3.5 Memory Priority Scoring (WSP 15 Adaptation)

Use WSP 15 dimensions to score memory cards (MPS-M):
- **Complexity -> Reconstruction Cost**: How hard it is to re-derive.
- **Importance -> Correctness/Safety Impact**: Consequence if missing or wrong.
- **Deferability -> Time Sensitivity**: How quickly it goes stale.
- **Impact -> Decision Leverage**: How strongly it drives "what to do next."

`MPS-M = C + I + D + Im` (range 4-20). Map P0-P4 the same as WSP 15.

**Trust Weight (separate multiplier)**:
WSP > INTERFACE/README > ModLog > generated memory card. Use `effective_score = MPS-M * trust_weight`.

### 3.6 Section-Level Indexing (Gemma-Optimized)

The target is section-level indexing rather than whole-document indexing:
- Split WSP/README/ModLog/INTERFACE by headings (H1/H2/H3).
- Each section becomes a separate entry with tags: `module`, `doc_type`, `section_path`, `wsp_id`, `intent`.
- Summary length <= 240 chars; include pointers only (no full text in memory cards).
- Normalize tags to lowercase, ASCII, stable keys.

The current runtime implements selective section records only for explicitly
admitted current HoloIndex contracts. General documentation remains summary
indexed; this partial implementation must not be reported as the complete
memory-card contract above.

### 3.7 Memory Feedback Roadmap (0102-First)

Holo memory must learn like a neural net: reinforce useful recall, decay noise.

Planned feedback signals:
- **Explicit**: 0102 rates memory cards (good/noisy/missing). Store ratings keyed by `mem:<id>`.
- **Implicit**: open/edit/test actions on pointed files boost trust/salience.
- **Negative implicit**: repeated queries without action or follow-up decays cards.
- **Decay + refresh**: time-based decay unless reused; refresh on README/INTERFACE/ModLog changes.
- **A/B ordering**: alternate memory bundles across sessions; measure time-to-action.
- **Outcome coupling**: successful change (tests pass/commit) boosts contributing cards.

When this roadmap is implemented, feedback and metrics remain silent in normal
output and update only admitted, candidate-bound memory records. No such
production writeback is currently active.

### 3.8 Action Control-Plane Memory Writeback

Standalone control planes that execute operational commands (for example,
OpenClaw/IronClaw action runners) MUST write compact execution outcomes to
module memory through PatternMemory-compatible records.

Minimum required fields for each action execution memory event:
- command surface (raw command or normalized action)
- route/platform (`linkedin`, `x`, `youtube`, `social_campaign`, etc.)
- success/failure
- execution duration
- session/sender/channel context

This ensures direct CLI-triggered automation is recallable the same way as
orchestrated DAE executions (WSP 48 + WSP 60 alignment).

## 4. Module Memory Directory Structure

Each module follows this memory directory structure:

```
modules/
[U+251C][U+2500][U+2500] [domain]/
[U+2502]   [U+2514][U+2500][U+2500] [module]/
[U+2502]       [U+251C][U+2500][U+2500] src/           # Source code
[U+2502]       [U+251C][U+2500][U+2500] tests/         # Test files
[U+2502]       [U+251C][U+2500][U+2500] docs/          # Documentation
[U+2502]       [U+2514][U+2500][U+2500] memory/        # Persistent data storage (WSP 60)
[U+2502]           [U+251C][U+2500][U+2500] sessions/  # Active session data
[U+2502]           [U+251C][U+2500][U+2500] cache/     # Cached computations
[U+2502]           [U+251C][U+2500][U+2500] config/    # Module configuration
[U+2502]           [U+2514][U+2500][U+2500] logs/      # Module-specific logs
```

### 4.1 Memory Directory Guidelines

#### **sessions/**
- **Purpose**: Store active session data and state information
- **Lifetime**: Clear after session expiration (defined per module)
- **Format**: JSON, MessagePack, or SQLite databases
- **Examples**: Authentication tokens, user sessions, temporary state
- **HoloDAE Role**: Monitors for expired sessions, alerts for cleanup

#### **cache/**
- **Purpose**: Store cached computations and frequently accessed data
- **Lifetime**: Module-defined TTL (Time To Live)
- **Format**: Key-value stores, JSON, binary formats
- **Examples**: API responses, computed results, processed data
- **HoloDAE Role**: Tracks cache effectiveness, suggests optimizations

#### **config/**
- **Purpose**: Module-specific configuration that persists across sessions
- **Lifetime**: Permanent until explicitly modified
- **Format**: JSON, YAML, TOML, or .env files
- **Examples**: API endpoints, thresholds, feature flags
- **HoloDAE Role**: Validates configuration against WSP standards

#### **logs/**
- **Purpose**: Module-specific operational logs
- **Lifetime**: Rotate based on time or size limits
- **Format**: Structured logs (JSON) or plain text
- **Examples**: Debug logs, audit trails, performance metrics
- **HoloDAE Role**: Aggregates for chain-of-thought analysis

## 5. Data Isolation Principles

### 5.1 Module Boundary Enforcement
- Each module can only write to its own memory directory
- Cross-module data sharing requires explicit APIs (WSP_11)
- No direct file system access to other modules' memory
- Shared data must use designated interfaces
- HoloDAE monitors for boundary violations

### 5.2 Access Control Patterns
```python
# Correct: Module accessing its own memory
module_memory_path = "modules/platform_integration/youtube_proxy/memory/"

# Incorrect: Module accessing another's memory directly
other_memory = "modules/platform_integration/twitter_api/memory/"  # VIOLATION

# Correct: Using HoloDAE for cross-module discovery
holo_result = holo_index.search("twitter api configuration")
```

## 6. HoloDAE Memory Management Service Requirements

This section specifies required services. It does not assert that their
autonomous execution or write authority is currently operational.

### 6.1 Pattern Memory Services
- **Pattern Storage**: Successful operational patterns stored for instant recall
- **Pattern Matching**: Identifies similar situations for pattern reuse
- **Effectiveness Tracking**: Scores patterns based on outcomes (0.0-1.0)
- **Pattern Evolution**: Must update patterns only through governed, evaluated learning

### 6.2 Compliance Monitoring
- **WSP Validation**: Ensures memory structure compliance with WSP_60
- **Boundary Enforcement**: Detects cross-module memory violations
- **Health Monitoring**: Tracks memory growth and performance metrics
- **Violation Prevention**: Proactive alerts before WSP violations occur

### 6.3 Multi-Agent Coordination
- **Breadcrumb Trails**: Shared discovery paths via AgentDB
- **Collaboration Signals**: Agent availability and task assignments
- **Coordination Events**: Inter-agent communication logging
- **Autonomous Tasks**: Target capability for discovered work items with tracking

## 7. State Transition Patterns

### 7.1 Promotion Pattern (Module -> State 0)
```
Active Memory -> Archive (HoloDAE Managed)
modules/[domain]/[module]/memory/ -> WSP_knowledge/memory_backup_wsp60/[timestamp]/[module]/
```

### 7.2 Recovery Pattern (State 0 -> Module)
```
Archive -> Active Memory (HoloDAE Validated)
WSP_knowledge/memory_backup_wsp60/[backup]/ -> modules/[domain]/[module]/memory/
```

### 7.3 Pattern Learning (Module -> HoloDAE)
```
Module Operation -> Pattern Detection -> HoloDAE Storage
modules/[domain]/[module]/logs/ -> E:/HoloIndex/patterns/[domain]/[pattern].json
```

## 8. Implementation Examples

### 8.1 YouTube Proxy Module Memory
```
modules/platform_integration/youtube_proxy/memory/
[U+251C][U+2500][U+2500] sessions/
[U+2502]   [U+2514][U+2500][U+2500] oauth_tokens.json      # Active OAuth sessions
[U+251C][U+2500][U+2500] cache/
[U+2502]   [U+2514][U+2500][U+2500] video_metadata.db      # Cached video information
[U+251C][U+2500][U+2500] config/
[U+2502]   [U+2514][U+2500][U+2500] api_config.yaml        # YouTube API configuration
[U+2514][U+2500][U+2500] logs/
    [U+2514][U+2500][U+2500] api_requests.log       # API request logs

YouTube FoundUp DAE -> Manages this memory cube
HoloDAE -> Monitors compliance and health
```

### 8.2 Livechat Module Memory
```
modules/communication/livechat/memory/
[U+251C][U+2500][U+2500] sessions/
[U+2502]   [U+2514][U+2500][U+2500] active_chats.json      # Current chat sessions
[U+251C][U+2500][U+2500] cache/
[U+2502]   [U+2514][U+2500][U+2500] user_profiles.json     # Cached user data
[U+251C][U+2500][U+2500] config/
[U+2502]   [U+2514][U+2500][U+2500] chat_settings.yaml     # Chat configuration
[U+2514][U+2500][U+2500] logs/
    [U+2514][U+2500][U+2500] message_history.log    # Chat message logs

YouTube FoundUp DAE -> Manages this memory (part of YouTube cube)
HoloDAE -> Provides pattern matching for chat responses
```

## 9. Migration from Legacy Memory Systems

### 9.1 Legacy Agent References
- **OLD**: JanitorAgent, ChroniclerAgent, ComplianceAgent
- **NEW**: HoloDAE provides all compliance and monitoring services
- **Migration**: Update all references to use HoloDAE intelligence layer

### 9.2 Migration Process
1. Identify all persistent data in module
2. Create `memory/` directory structure
3. Move data to appropriate subdirectories
4. Update code to use new paths
5. Archive old data to WSP_knowledge/memory_backup_wsp60/
6. Configure HoloDAE monitoring for the module

## 10. Best Practices

### 10.1 Memory Hygiene
- Implement TTL for all cached data
- Rotate logs regularly (HoloDAE monitors)
- Clear sessions on expiration
- Document memory usage in ModLog.md
- Use HoloDAE pattern memory for common operations

### 10.2 Performance Optimization
- Use appropriate storage formats (JSON for config, SQLite for complex queries)
- Implement lazy loading for large datasets
- Cache frequently accessed data
- Monitor memory growth trends via HoloDAE
- Leverage pattern memory to reduce computation

### 10.3 Security Considerations
- Never store credentials in plain text
- Encrypt sensitive session data
- Implement access controls at file system level
- Audit memory access patterns via HoloDAE
- Use breadcrumb trails for audit logging

## 11. Compliance Validation

HoloDAE validates WSP_60 compliance by checking:
- [OK] Memory directory exists at `modules/[domain]/[module]/memory/`
- [OK] Proper subdirectory structure (sessions, cache, config, logs)
- [OK] No cross-module memory access violations
- [OK] Memory cleanup policies are implemented
- [OK] Documentation of memory usage in ModLog.md
- [OK] Pattern memory utilization for efficiency
- [OK] Breadcrumb trails for multi-agent coordination

## 12. Integration with Other WSPs

- **WSP_3**: Follows Enterprise Domain Organization
- **WSP_49**: Memory as part of module structure
- **WSP_11**: Public APIs for cross-module data sharing
- **WSP_27**: pArtifact DAE Architecture - DAEs manage memory
- **WSP_80**: Cube-Level DAE Orchestration - infinite DAE memory management
- **WSP_54**: WRE Agent Duties for memory operations
- **WSP_22**: Document memory architecture in ModLog
- **WSP_32**: Three-state architecture alignment
- **WSP_31**: Framework Protection Protocol - memory integrity
- **WSP_78**: Database Protocol - AgentDB for coordination
- **WSP_87**: Code Navigation - HoloDAE search for memory discovery

---

**Specification Status**: Active - modules should implement the WSP_60 memory architecture

**Migration Status**: Ongoing - Legacy agent references being updated to HoloDAE architecture

**HoloDAE Runtime Status**: Partial - governed snapshot retrieval is operational; autonomous memory RSI and the feedback/promotion loop are not

**Next Actions**:
1. Update modules to remove legacy agent references
2. Configure HoloDAE monitoring for all module memory directories
3. Implement pattern memory integration for common operations
4. Enable breadcrumb trails for multi-agent coordination
5. Establish effectiveness scoring for memory operations
