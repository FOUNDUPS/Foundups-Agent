# Scientific Autonomous Self-Healing Composition Audit (WSP_97 / Issue #1522)

**Document**: `SELF_HEALING_COMPOSITION_AUDIT.md`  
**Author**: 0102 (Architect)  
**Governing Protocols**: WSP_00, WSP_15, WSP_50, WSP_80, WSP_97, WSP_109  
**Branch**: `audit/reddog-self-healing-composition`  
**Base Commit**: `80328ac3d` (PR #1519 + #1523 merged)

---

## 1. Architectural Mandate & Principle of Non-Vibecoding

This codebase operates as a modular FoundUps LEGO / Rubik architecture governed strictly by WSP protocols.

### Foundational Invariants:
1. **"The entity that proposes a repair must not be the sole authority that validates, verifies, or promotes that repair."**
2. **"RedDog does not autonomously 'fix errors'; it autonomously conducts bounded experiments against authenticated failures, and only independently verified experiments may become candidate repairs."**
3. **"Self-healing $\neq$ Self-merging."**

### Pre-Implementation Rule:
No implementation may begin with *"create a new module that does X"*.  
The mandatory decision chain is:
$$\text{RESEARCH} \longrightarrow \text{HOLOINDEX} \longrightarrow \text{INSPECT CURRENT CODE} \longrightarrow \text{PATTERNMEMORY} \longrightarrow \text{WSP} \longrightarrow \text{REUSE / EXTEND / CREATE}$$

---

## 2. Comprehensive Capability Mapping & Composition Matrix

Below is the exhaustive audit of all 24 required capabilities across the current repository:

| # | Capability | Existing Implementation Path(s) | Status | Classification | Gap / Limitation | Required Slice |
|---|---|---|---|:---:|---|---|
| **1** | **RedDog Resident Operation & Heartbeat** | `modules/communication/moltbot_bridge/src/reddog_resident_architect_runtime.py`, `extensions/reddog/extension.js` | IMPLEMENTED | **EXTEND** | Heartbeat currently surfaces pain & status, but lacks the autonomous transition trigger to instantiate repair experiments without a prompt. | **Slice 1** |
| **2** | **OpenClaw Supervisor** | `modules/communication/moltbot_bridge/src/openclaw_supervisor.py` | IMPLEMENTED | **REUSE** | Schedules, leases, and claims tasks from AgentDB; verifies execution boundaries. | **Slice 1 / 3** |
| **3** | **OpenClaw Resident Runtime** | `modules/communication/moltbot_bridge/scripts/launch.py` (Port 18800) | IMPLEMENTED | **REUSE** | Webhook / control-plane service; operates as a persistent execution scaffold. | **Slice 1** |
| **4** | **Hermes Adapters** | `modules/communication/moltbot_bridge/src/reddog_openclaw_hermes_0102_worker_dispatch_runtime.py`, `modules/foundups/agent/src/hermes_adapter.py` | IMPLEMENTED | **REUSE** | Work-order routing envelope and secondary recursive scaffold. | **Slice 1** |
| **5** | **AgentDB Autonomous Tasks & Events** | `modules/infrastructure/database/src/agent_db.py`, `modules/infrastructure/database/src/agent_db_autonomous_tasks.py` | IMPLEMENTED | **EXTEND** | Has generic task queuing and coordination event logging; needs the explicit typed `RepairOperationLedger` states. | **Slice 1** |
| **6** | **PatternMemory** | `modules/infrastructure/wre_core/src/pattern_memory.py`, SQLite `pattern_memory.db` | IMPLEMENTED | **EXTEND** | Stores execution outcomes and variations; needs structured storage for `{Pain, Hypothesis, ExperimentDiff, Counterexamples, ApplicabilityConditions}`. | **Slice 1** |
| **7** | **HoloIndex Incident Repair** | `modules/communication/moltbot_bridge/src/reddog_holoindex_incident_repair_runtime.py`, `scripts/reddog_holoindex_incident_repair_once.py` | IMPLEMENTED | **REUSE (Reference)** | Reference implementation for failure detection, SHA binding, and WRE coordinator handoff. | **Reference** |
| **8** | **HoloIndex Exact-SHA Authority Transaction** | `modules/infrastructure/idle_automation/src/holoindex_postmerge_coordinator.py`, `holo_index/authority_worktree.py` | IMPLEMENTED | **REUSE** | Guarantees forward-only exact-SHA advancement in a clean, dedicated authority worktree. | **Reference** |
| **9** | **WRE Execution Engine** | `modules/infrastructure/wre_core/src/` | IMPLEMENTED | **REUSE** | Bounded hands for repository operations and test runs. | **Slice 1** |
| **10** | **Signed Workers** | `modules/infrastructure/wre_core/src/wre_worker_git_cwd_guard.py` | IMPLEMENTED | **REUSE** | Cryptographically/structurally constrains worker cwd to claimed external worktrees. | **Slice 1** |
| **11** | **Signer / Effect Authority** | `extensions/reddog/resident_architect_session_contract.js` | IMPLEMENTED | **REUSE** | Controls promotion authority; prevents unauthorized self-merging. | **Slice 1** |
| **12** | **Worktree Creation & Isolation** | `modules/infrastructure/wre_core/src/wre_worker_git_cwd_guard.py`, `holo_index/authority_worktree.py` | IMPLEMENTED | **REUSE** | Ensures experiments execute in scratch worktrees outside the primary repo checkout. | **Slice 1 / 3** |
| **13** | **WSP_15 Scoring & Budgeting** | `WSP_framework/src/WSP_15_Module_Prioritization_Scoring_System.md`, `scripts/advisory_model_once.py` | IMPLEMENTED | **EXTEND** | Scores priority (P0-P4); needs explicit experiment budget envelope (`max_iterations`, `max_loc`, `allowed_paths`, token bounds). | **Slice 1** |
| **14** | **AutoResearch Infrastructure** | `modules/ai_intelligence/ai_gateway/src/model_autoresearch_campaign_execution.py` | IMPLEMENTED | **REUSE** | Provides campaign plans, evidence bundles, and feedback ledgers. | **Slice 2** |
| **15** | **OpenResearch / External Retrieval** | `modules/infrastructure/foundups_mcp_bridge/src/reddog_tools.py` (`web_search`), duckduckgo/serper search | IMPLEMENTED | **EXTEND** | Raw search tools exist; needs the **Research Quarantine** wrapper (provenance, content digest, prompt-injection isolation). | **Slice 1 / 2** |
| **16** | **Model AutoResearch Campaign Execution** | `modules/ai_intelligence/ai_gateway/src/model_autoresearch_campaign_execution.py` | IMPLEMENTED | **REUSE** | Manages champion/challenger comparisons and execution plans. | **Slice 2** |
| **17** | **`requires_independent_verifier` Semantics** | `modules/ai_intelligence/ai_gateway/src/model_champion_challenger_autoresearch.py` (Line 81) | IMPLEMENTED | **EXTEND** | Enforced boolean flag in contract; needs extension from deterministic check to **Tier 2 Independent Model Verifier (Model B)**. | **Slice 2** |
| **18** | **Benchmark Verifier Infrastructure** | `modules/ai_intelligence/ai_gateway/src/model_combination_benchmark_execution.py` | IMPLEMENTED | **REUSE** | Evaluates model execution benchmarks and performance matrices. | **Slice 2** |
| **19** | **Semantic Verifier** | `modules/infrastructure/foundups_mcp_bridge/src/holo_query_semantic_proof.py`, `holo_index/query_result_contract.py` | IMPLEMENTED | **REUSE** | Validates exact semantic term grounding and evidence digests. | **Slice 2** |
| **20** | **Model Gateway & Selection** | `modules/infrastructure/shared_utilities/src/local_llm_resolver.py`, `ai_engine_singletons.py` | IMPLEMENTED | **REUSE** | Resolves local LM Studio (`http://localhost:1234/v1`) and llama.cpp backends for Qwen/Gemma. | **Slice 1 / 3** |
| **21** | **Fusion Multi-Model Jury** | `scripts/advisory_model_once.py` (Panel critics & synthesis passes) | IMPLEMENTED | **EXTEND** | Currently used for advisory prompts; needs conversion to an **adversarial jury over evidence** for elevated-risk repairs. | **Slice 2** |
| **22** | **Receipts, Provenance & Digests** | `holo_index/freshness_receipt.py`, `modules/communication/moltbot_bridge/src/reddog_holoindex_incident_repair_contract.py` | IMPLEMENTED | **REUSE** | Canonical SHA-256 digest sealing and tamper-evident payload verification. | **Slice 1 / 2** |
| **23** | **Test & Preflight Failure Detectors** | `main.py` preflight sentinels (`run_dep_security_preflight`, `run_wsp_framework_preflight`) | IMPLEMENTED | **REUSE** | Emits typed JSON preflight failure payloads to `alerts/preflight/`. | **Slice 1 / 3** |
| **24** | **Dependency, Security & WSP Drift Detectors** | `modules/infrastructure/wre_core/src/dependency_security_preflight.py`, `modules/ai_intelligence/ai_overseer/src/ai_overseer.py` | IMPLEMENTED | **REUSE** | Detects CVEs, node/rust lock issues, and WSP file/index drift. | **Slice 1 / 3** |

---

## 3. Key Findings & Architectural Gaps

1. **Primitive Availability: ~90% REUSE / EXTEND**:
   - The FoundUps codebase already possesses nearly all required execution primitives: OpenClaw supervisor, AgentDB task queue, worktree isolation guards, PatternMemory SQLite, LM Studio resolver, AutoResearch contracts with `requires_independent_verifier`, and digest-sealed receipts.
   - The primary gap is **compositional and state-machine orchestration**, not missing low-level infrastructure.

2. **The 3 Load-Bearing Additions**:
   - **Gap A (Operation State Machine)**: A unified `RepairOperationLedger` tracking the scientific cycle from `OBSERVED → REPRODUCING → BASELINED → EXPERIMENTING → DETERMINISTIC_VERIFY → INDEPENDENT_VERIFY → DISPOSITION → LEARNED`.
   - **Gap B (Verifier Context Firewall & Model B)**: Extending `requires_independent_verifier` so Model B receives a clean, unpersuasive `VerifierEvidencePacket` and emits a structured `CounterexampleReceipt`.
   - **Gap C (Autonomous Closed-Loop Wiring)**: Connecting RedDog's observation sentinel to autonomously reproduce the failure, seal a baseline receipt, launch an OpenClaw worktree, verify, and stage a PR without requiring an intervening human prompt.

---

## 4. Phased Implementation Roadmap

```
                                  ROADMAP
                                     │
   ┌─────────────────────────────────┴─────────────────────────────────┐
   ▼                                                                   ▼
[Slice 0: Composition Audit]                                 [Slice 1: State Machine]
• SELF_HEALING_COMPOSITION_AUDIT.md                          • modules/infrastructure/wre_core/src/
• Complete capability matrix                                   repair_operation_contract.py
   │                                                         • Durable AgentDB state ledger
   └─────────────────────────────────┬─────────────────────────────────┘
                                     ▼
                      [Slice 2: Independent Verifier]
                      • modules/ai_intelligence/ai_gateway/src/
                        independent_repair_verifier.py
                      • VerifierEvidencePacket & Firewall
                      • CounterexampleReceipt & Model B
                                     │
                                     ▼
                      [Slice 3: Autonomous Repair Canary]
                      • End-to-end multi-stage canary
                      • Automated failure → reproduction →
                        Model A repair → Tier 1/2 verification → PR
```

---

## 5. Next Immediate Action

Proceed directly to **Slice 1** (`feat/reddog-repair-operation-contract`):
- Implement the typed `RepairOperationLedger` and `BaselineReceipt` contracts.
- Connect into `AgentDB` coordination events and `PatternMemory`.
