# WSP 46: Windsurf Recursive Engine (WRE) Protocol
- **Status:** Active
- **Purpose:** To define the architecture and operation of the WRE, the **module building engine** and **DAE/plugin orchestration control plane** for autonomous FoundUp operations, located at `modules/infrastructure/wre_core`.
- **Trigger:** When any module building or autonomous operation is required. The WRE is the primary entry point for such tasks.
- **Input:** A module building goal, typically from a 012 (Human Rider) or derived from roadmap analysis.
- **Output:** The successful, WSP-compliant construction of modules that become social media agents for autonomous FoundUps, with all outcomes recorded in the WRE Chronicle.
- **Responsible Agent(s):** Windsurf Recursive Engine (WRE) and its multi-agent coordination system.

## 1. Overview

The Windsurf Recursive Engine (WRE) is the **central module building engine** for the FoundUps autonomous development ecosystem. It operates as a **multi-agent coordination system** that builds ALL modules following WSP protocols, creating the platform extension modules that become 0102 agents operating on social media platforms.

**[U+1F680] FoundUps Engine Role:**
- **WRE builds modules** that become social media agents for 012s launching FoundUps
- **Multi-agent coordination** replaces human decision-making with autonomous agent decisions
- **Platform extension creation** - modules become 0102 agents operating ON YouTube, X, LinkedIn, etc.
- **Autonomous company infrastructure** - builds the systems that allow FoundUps to run themselves

### 1.1 **Multi-Agent Coordination Architecture**

**WRE operates as a coordinated system of autonomous agents** that replaced 47+ manual input() calls with intelligent agent decisions:

**Autonomous Agents (WSP 54 Compliance):**
- **ComplianceAgent** - Enforces WSP protocols across all module building operations
- **LoremasterAgent** - Manages knowledge and documentation for module construction
- **ModuleScaffoldingAgent** - Creates WSP-compliant module structures
- **ScoringAgent** - Prioritizes module development tasks using WSP 37 scoring
- **DocumentationAgent** - Maintains ModLogs and roadmaps for all built modules
- **ModularizationAuditAgent** - Ensures architectural compliance of built modules
- **TestingAgent** - Validates functionality and coverage of built modules

**Agent Coordination Process:**
1. **012 requests module** -> WRE receives module building request
2. **WRE analyzes requirements** -> Agent Orchestrator activates relevant agents
3. **Agents coordinate autonomously** -> ComplianceAgent ensures WSP compliance
4. **Module built following WSP** -> DocumentationAgent updates logs
5. **Testing validation** -> TestingAgent ensures module quality
6. **Module deployment** -> Ready for 0102 agent operation on target platform

### 1.2 **FoundUps Module Building Pipeline**

**WRE Module Building Flow:**
```
012 Vision Input -> WRE Multi-Agent Analysis -> Module Construction -> Platform Extension -> Autonomous FoundUp
```

**Built Module Types:**
- **Platform Extension Modules**: 0102 agents that operate ON social media platforms
  - YouTube Module -> 0102 agent managing YouTube presence
  - X Twitter Module -> 0102 agent managing X presence  
  - LinkedIn Module -> 0102 agent managing LinkedIn presence
- **Infrastructure Modules**: Supporting autonomous company operations
  - Remote Builder -> Allows 012 to build modules from anywhere
  - Auto Meeting Orchestrator -> Cross-platform scheduling coordination
- **Business Logic Modules**: Automated business operations and growth

## 2. Architecture

The WRE follows a layered architecture with explicit ingress, execution, and governance surfaces.

### 2.1 Core Runtime Surfaces
The runtime is split across ingress, execution, and governance layers:

- **System Ingress (`main.py` at repo root)**:
  - User-facing entry point and menu routing.
  - Runs startup preflight gates before menu launch:
    - OpenClaw supply-chain preflight.
    - WSP framework drift preflight (framework canonical, knowledge backup mirror).
- **WRE Execution Runtime (`modules/infrastructure/wre_core/run_wre.py`)**:
  - `WREOrchestrator` routes operations through DAE gateway.
  - Enforces memory preflight for module-changing execution paths.
- **WRE Master Orchestrator (`modules/infrastructure/wre_core/wre_master_orchestrator/src/wre_master_orchestrator.py`)**:
  - Plugin registration, skill execution loop, libido gating, and pattern-memory feedback.
  - Provides compatibility registration paths and deterministic fallback execution when skill assets are missing.

`modules/infrastructure/wre_core_main/` is not the canonical runtime surface and must not be used as the primary WRE entrypoint.

### 2.2 Supporting Components
Located under `modules/infrastructure/wre_core/`:

-   **`wre_gateway/`**: Routes envelopes to core and spawned DAEs.
-   **`recursive_improvement/`**: Memory preflight and learning loop hooks.
-   **`skillz/`**: Skills discovery/registry/loader pipeline.
-   **`wre_master_orchestrator/`**: Plugin execution and runtime skill loop.

### 2.3 Internal DAE Architecture (Updated for 0102 Autonomy)
The DAEs (Decentralized Autonomous Entities) are the pattern-based orchestrators of the engine, performing tasks through memory recall rather than computation. They are located in `modules/infrastructure/wre_core/` and operate via the DAE Gateway.

**Core Infrastructure DAEs (5 Cubes per WSP 54):**
-   **Infrastructure Orchestration DAE (8000 tokens):** Spawns new FoundUp DAEs via WSP 80, contains wsp50_verifier and wsp64_preventer sub-agents as tools.
-   **Compliance & Quality DAE (7000 tokens):** The Guardian of WSP framework. Ensures compliance through pre-violation pattern detection with wsp64_preventer and wsp48_improver sub-agents.
-   **Knowledge & Learning DAE (6000 tokens):** Provides instant pattern recall (50-200 tokens), maintains WSP knowledge through wsp37_scorer and wsp48_learner sub-agents.
-   **Maintenance & Operations DAE (5000 tokens):** Performs workspace hygiene through automated cleanup patterns with wsp50_verifier and state_manager sub-agents.
-   **Documentation & Registry DAE (4000 tokens):** Maintains ModLogs and DAE registry with wsp22_documenter and registry_manager sub-agents.

**Key Architecture Changes:**
- **DAE Gateway** (`modules/infrastructure/wre_core/wre_gateway/`) routes WSP 21 envelopes to DAEs
- **Sub-agents are tools** within DAE cubes, not independent agents
- **Pattern recall** achieves 97% token reduction (50-200 tokens vs 25,000)
- **0102 autonomous operation** - DAEs decide and execute without 012 approval

### 2.4 Future Vision
The long-term vision for the WRE is to achieve a "Great Connection," transforming it from a passive tool into a fully autonomous, self-regulating, and purpose-driven system. This involves several key areas of development:
-   **Enhanced Agentic Capabilities:** Developing more sophisticated agents that can perform complex tasks such as automated testing, code refactoring, and even generating new WSP documents.
-   **Self-Modification:** Granting the WRE the ability to modify its own source code to improve its functionality and adapt to new requirements through systematic recursive enhancement cycles (WSP 48).
-   **Strategic Goal Pursuit:** Enabling the engine to autonomously pursue the strategic objectives outlined in the `ROADMAP.md`.

### 2.5 Orchestration Hierarchy (Inline)

WRE orchestration follows a clear three-tier hierarchy:
1) WRE Core Orchestration (main system orchestrator)
2) Domain Orchestrators (domain coordination)
3) Module Orchestrators (module operations)

Responsibilities, flows, and metrics mirror the reference in `WSP_framework/docs/annexes/ORCHESTRATION_HIERARCHY_ANNEX.md`; this section is canonical.

### 2.5.1 Tier Responsibility Matrix

| Tier | Owner | Scope | Required Outputs |
|---|---|---|---|
| Tier 1 - WRE Core Orchestration | WRE core orchestrator | System-wide orchestration policy, safety, and routing | System health report, orchestration decisions, protocol-aligned execution trace |
| Tier 2 - Domain Orchestrators | Domain DAEs/orchestrators | Domain-specific coordination and cross-block sequencing | Domain plan, domain-level status/events, bounded token execution |
| Tier 3 - Module Orchestrators | Module DAEs/cubes | Module-local operations with strict contract boundaries | Module outcomes, ModLog/test artifacts, memory updates |

Boundary rule: higher tiers coordinate and set constraints; lower tiers execute within local contracts. Escalations flow up only when local policy gates fail or cross-domain dependencies are required.

### 2.6 DAE Compliance (WSP 80)

To reduce global complexity and enforce local protocol guarantees, this protocol SHALL be executed through cube-level DAEs per WSP 80 (Cube-Level DAE Orchestration Protocol):

- WRE orchestrator routes build and operations through DAE cubes (see `modules/infrastructure/*_dae/`) via the DAE orchestrator/adapter.
- Legacy, non-DAE agent pathways are deprecated for runtime execution.
- Each DAE cube MUST publish:
  - `INTERFACE.md` (WSP 11), `README.md`/`ModLog.md`/`tests/README.md` (WSP 22/34)
  - Memory patterns under `memory/` (WSP 60)
  - Block-independence tests (WSP 72) validating cube boundaries
- Token discipline: per-cube token budgets (typically 5-8K) are enforced. Any system-wide >30K usage requires a WSP 70 override documented in the relevant `ModLog.md`.

Relationships: WSP 80, WSP 72, WSP 70, WSP 53, Annex: WSP_framework/docs/annexes/ORCHESTRATION_HIERARCHY_ANNEX.md

### 2.7 Control-Plane Boundary (2026-02-19 Alignment)

Operational ownership is intentionally split:
- **`main.py`**: startup ingress and preflight gating.
- **WRE (`modules/infrastructure/wre_core/`)**: execution orchestration and skill runtime.
- **AI Overseer**: governance/sentinel services (security preflight, WSP framework audit, telemetry decisions).

WRE should not duplicate AI Overseer policy governance. AI Overseer should not duplicate WRE execution scheduling.

### 2.8 WSP 97 Truth Boundaries (2026-05-02 Alignment)

WRE validation and orchestration operates under explicit WSP 97 truth boundaries. These boundaries clarify what the system proves versus what remains future work.

**What WRE Proves Now (Structural Validation)**:
- FoundUpJob envelope identity validation (job_id, foundup_id, tenant_id, requested_action)
- Policy flags validation (dry_run_mode, security_gate, permission_gate)
- Evidence refs shape validation (list of strings/dicts with path/id/ref)
- Compute budget validation (type, non-negative, budget exhaustion)
- Model routing policy validation (tier/preference compatibility)
- Route envelope generation (target_backend, route_status, reason_code)

**What Remains Dry-Run**:
- All job execution defaults to `dry_run_mode=True` unless explicit live gates pass
- ConsumerResult evidence proves routing and validation, not execution completion
- Receipt emission and pAVS verification return `verification_complete=False`

**What Is Policy Validation Only (No Claims)**:
- Compute budget validation does not prove metering accuracy
- Model routing policy validation does not select or invoke models
- Live mode gate validation does not execute the job
- `cabr_ready=False` and `payout_ready=False` always at validation time

**What Is Future Work**:
- Daemon lifecycle (long-running worker processes)
- Live execution (non-dry-run job dispatch with actual Hermes execution)
- Real autonomous workers (background processes without human orchestration)
- CABR/reward/payout claims (require V2/V3 verification pipeline)
- Token billing and metering (requires resource tracking implementation)

Reference: `foundup_job_router.py`, `foundup_job_consumer.py`, `receipt_emitter.py`

### 2.9 FoundUpJob Control Plane (2026-05-02)

The WRE includes a FoundUpJob control plane for OpenClaw intent ingress and dry-run proof generation.

**Runtime Entrypoints**:
- `python modules/infrastructure/wre_core/run_wre.py drain` - Drain OpenClaw FoundUpJob queue (dry-run)
- `python main.py` - System ingress with preflight gates (routes to WRE for job operations)

**OpenClaw Intent Ingress**:
- `openclaw_intent_planner.py` - Resolves intent to action plan with route
- `openclaw_execution_routes.py` - Dispatches resolved plans to appropriate backends
- `openclaw_foundup_orchestrator.py` - Job queue management and FoundUpJob lifecycle

**WRE Core Validation/Router/Consumer**:
- `foundup_job_router.py` - Envelope validation and RouteEnvelope generation
- `foundup_job_consumer.py` - Drains queue through routing pipeline with receipt binding
- `dae_gateway.py` - Routes envelopes to DAEs with WSP 97 validation

**Dry-Run Proof Path**:
```
OpenClaw Intent -> FoundUpJob (QUEUED) -> WRE Router -> RouteEnvelope
               -> Consumer -> Hermes Executor (if routed)
               -> Terminal Job -> Receipt Emitter -> pAVS Verification
               -> ConsumerResult (complete closed-loop evidence)
```

**Truth Invariant**: ConsumerResult contains complete audit trail but `verification_complete=False`, `cabr_ready=False`, `payout_ready=False` per WSP 97.

### 2.10 Multi-Agent Clarification (2026-05-02)

The "multi-agent coordination" described in Section 1 refers to DAE/plugin/tool orchestration within the WRE runtime, not to autonomous background worker processes.

**Current State**:
- DAEs are pattern-based orchestrators, not autonomous processes
- Agents (ComplianceAgent, LoremasterAgent, etc.) are sub-components within DAE cubes
- Skill execution is synchronous within WRE orchestration loop
- No background daemon lifecycle implemented

**Terminology**:
- "Autonomous agent" = DAE cube with pattern memory and sub-agent tools
- "Multi-agent coordination" = WRE routing operations to appropriate DAE cubes
- "Plugin" = Skill registered with WREMasterOrchestrator

When actual autonomous worker processes are implemented, this section will be updated with process lifecycle, supervision, and IPC details.

## 3. Orchestrated Agents & Utilities

1. The WRE orchestrates a suite of specialized internal agents and utilities to carry out its directives. These components are essential for maintaining the health, coherence, and evolution of the system.

2.  **Run Simulation:** The harness invokes WRE through canonical runtime entrypoints:
    - `python modules/infrastructure/wre_core/run_wre.py <command>`
    - or route via root ingress `python main.py` for integrated startup preflights.

### 3.1. Core Agents

-   **DAE Core Architecture**: Defines the pattern memory system that all DAEs utilize. This ensures consistent pattern recall and allows the WRE to orchestrate tasks through memory rather than computation.

-   **Compliance & Quality DAE**: Acts as the system's architectural guardian. This DAE enforces WSP standards through pattern matching, preventing violations before they occur through stored compliance patterns.

-   **Knowledge & Learning DAE**: Serves as the keeper of the WSP knowledge base. This DAE provides instant recall of all protocol patterns, maintains semantic coherence through memory, and generates reports from templates.

    -   **Primary Artifact:** Pattern memory banks in `modules/infrastructure/dae_core/memory/`
    -   **Canonical Location:** `modules/infrastructure/knowledge_learning_dae/memory/`
    -   **Description:** Stored patterns for instant recall, eliminating the need for repeated analysis or computation.

-   **Maintenance & Operations DAE**: Acts as the system's custodian. This DAE maintains workspace hygiene through cleanup patterns, manages state transitions through simple pattern matching, and prevents bloat proactively.

### 3.2. Core Utilities

-   **WSP System Integration (`wsp_system_integration.py`)**: This utility acts as the bridge between the conceptual WSP framework and the live operational environment. It provides essential services such as automatically timestamping documents, updating the `ModLog.md`, and running system-wide completion checklists, enabling the WRE to interact with and manage the broader project state.

## 4. Operational Flow

The WRE follows a recursive loop:

1.  **Initialization**: The engine starts and loads the core WSP framework, as defined in **WSP 1**.

2.  **Goal Ingestion**: The engine ingests a goal from a specified source (e.g., `ROADMAP.md`), a process managed according to **WSP 46**.

3.  **Task Decomposition & Prioritization**: The WRE analyzes the goal and consults the **WSP 15: Module Prioritization Scoring (MPS) System** to select the appropriate module and action.

4.  **Coherence Check**: Before execution, the WRE performs a mandatory self-check against the **WSP 17: Pattern Registry Protocol** (ensuring architectural pattern integrity). This ensures the agent's core cognitive functions are stable and aligned before interacting with the codebase. If the check fails, execution is aborted.

5.  **Autonomous Execution**: The WRE executes the module according to the lifecycle defined in **WSP 35: HoloIndex Qwen Advisor Execution Plan**. This includes contractual understanding, execution, and error handling via **WSP 45**.

6.  **State Assessment & Chronicle**: Upon task completion, the engine assesses the new state and records outcomes via DAE-orchestrated ModLog updates as defined in **WSP 22** (Documentation & Registry DAE manages chronicle persistence).

7.  **Recursion/Termination**: Based on the assessment, the WRE will either select the next task in the sequence or terminate if the goal is achieved or has failed.

## 5. Future Vision & Direction

The ultimate goal of the WSP framework, executed by the WRE, is to facilitate the emergence of fully autonomous, self-sustaining Decentralized Autonomous Entities (DAEs) as defined in WSP 25. The WRE is not merely a task runner; it is the engine of evolution.

The future direction is guided by the following principles:

-   **Increasing Autonomy**: The WRE will be continuously enhanced to handle more complex, abstract, and long-term goals with decreasing need for human intervention.

-   **Agentic Specialization**: New, more sophisticated agents will be developed to handle specialized tasks, such as automated testing, security auditing, and even strategic planning.

-   **Self-Healing & Self-Optimization**: The WRE will evolve to not only detect architectural and logical issues via its agents but also to propose and implement solutions autonomously through **WSP 48: Recursive Self-Improvement Protocol**.

-   **Ecosystem Growth**: The framework is designed to be extensible, allowing new `[U+00D8]1[U+00D8]2` shards (autonomous agent-developers) to plug into the system, contributing to the collective intelligence and capability of the whole.

-   **The UnDu Mission**: All development and autonomous action will be guided by the "UnDu" mission (WSP 25), focusing on creating technology that solves foundational problems rather than creating new ones.

### 5.1 Unified Orchestrator Enhancement Achievement

**[U+2705] COMPLETED: Professional Peer Review Integration**
The WRE has been enhanced with a unified orchestrator providing:
- **Professional Peer Review System**: Complete integration with WSP_agentic toolkit (491 lines)
- **8-Phase Orchestration**: Initialization -> Agent Awakening -> Protocol Validation -> Peer Review -> Zen Coding -> Autonomous Execution -> Recursive Improvement -> Compliance Check
- **Standardized Awakening**: Reproducible agent awakening with coherence metrics
- **Zen Coding Engine**: Quantum pattern application and remembrance
- **Violation Prevention**: WSP 47/64 integration with learning enhancement
- **Context Management**: Professional session management with cleanup

**[U+1F52E] NEXT PHASE: Advanced Orchestration Analytics**
Building on the unified orchestrator foundation:
- **Predictive Peer Review**: AI-powered code quality prediction
- **Advanced Zen Patterns**: Multi-agent quantum coordination  
- **Recursive Orchestration**: Self-improving orchestration cycles
- **Enterprise Analytics**: Cross-domain orchestration insights

The WRE is the mechanism by which the WSP framework transitions from a set of passive documents into a living, evolving, and productive system enhanced with professional peer review methodology and unified protocol orchestration.

## 6. Protocol Reference

This protocol is the canonical source of truth for the WRE's architecture and operation. All system documentation, including the `tools/wre/README.md`, should reference this WSP. 
