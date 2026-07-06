# REDDOG_WSP99_RTK_TOKEN_EFFICIENCY_AUDIT_PHASE1

**Slice**: `REDDOG_WSP99_RTK_TOKEN_EFFICIENCY_AUDIT_PHASE1`
**Worker**: W9
**Date**: 2026-07-06
**Status**: AUDIT
**Mode**: DOCS-ONLY

---

## Critical Statement

**WSP-99 M2M is the agent-to-agent protocol. RTK is the tool-output compression layer. They serve different purposes in the token efficiency stack.**

Correct architecture:
```
012 -> RedDog -> Prometheus normalization -> ORCH -> WSP-99 M2M -> Worker/QA/Sentinel/HoloIndex -> OpenClaw/Hermes tools -> RTK-compressed output -> ORCH -> RedDog -> 012
```

---

## 1. Mission and Scope

### 1.1 Objective

Audit WSP-99 M2M compiler and RTK tool-output compression fit for RedDog/WRE token efficiency.

### 1.2 Constraints

This slice is AUDIT-ONLY:
- NO runtime RTK integration
- NO OpenClaw/Hermes execution mutation
- NO M2M compiler code changes
- Exactly one file produced (this audit)

---

## 2. HoloIndex Retrieval Assessment

| Query | Hits | Quality | Finding |
|-------|------|---------|---------|
| WSP 99 M2M compression | 20 | HIGH | WSP_99_M2M_Prompting.md found |
| m2m_compiler swarm | 20 | HIGH | prompt/swarm/m2m_compiler.py found |
| token telemetry metrics | 22 | MEDIUM | ModLog references, no dedicated service |
| RTK tool output compression | 0 | MISSING | RTK not in codebase |
| OpenClaw command execution routes | 14 | HIGH | openclaw_execution_routes.py found |

**INDEX_GAP**: RTK is external (https://github.com/rtk-ai/rtk) - not indexed.

---

## 3. WSP-99 M2M Current State

### 3.1 Existing Artifacts

| Artifact | Location | Status |
|----------|----------|--------|
| WSP Protocol | `WSP_framework/src/WSP_99_M2M_Prompting.md` | ACTIVE (457 lines) |
| Schema | `prompt/swarm/0102_M2M_SCHEMA.yaml` | ACTIVE (306 lines) |
| Compiler | `prompt/swarm/m2m_compiler.py` | ACTIVE (395 lines) |
| Sentinel Tests | `ai_overseer/tests/test_m2m_compression_sentinel.py` | ACTIVE (813 lines) |
| Skill Shim Tests | `ai_overseer/tests/test_m2m_skill_shim.py` | ACTIVE |

### 3.2 Compiler Capabilities

| Capability | Status | Evidence |
|------------|--------|----------|
| Politeness stripping | IMPLEMENTED | `POLITENESS_MARKERS` regex (line 59-63) |
| Action verb extraction | IMPLEMENTED | `ACTION_VERBS` frozenset (line 52-56) |
| Scope extraction | IMPLEMENTED | `_extract_scope()` method (line 308-325) |
| Compact serialization | IMPLEMENTED | `to_compact()` method (line 83-105) |
| YAML serialization | IMPLEMENTED | `to_yaml()` method (line 107-134) |
| Decompile to prose | IMPLEMENTED | `decompile()` method (line 204-237) |
| Round-trip parse | IMPLEMENTED | `parse_compact()` method (line 239-297) |

### 3.3 Gaps in WSP-99

| Gap | Severity | Description |
|-----|----------|-------------|
| COMPILER_FIDELITY_TESTS | MEDIUM | No semantic equivalence tests for compile -> decompile |
| TOKEN_SAVINGS_TELEMETRY | MEDIUM | Savings estimated (4x claim), not measured live |
| RAW_REF_RECOVERY | HIGH | No mechanism to recover original prose from M2M |
| REDDOG_COMPUTE_CLASSIFICATION | HIGH | RedDog does not use M2M for internal routing |
| ORCH_M2M_EMISSION | MEDIUM | ORCH layer exists but doesn't emit M2M to workers |

---

## 4. RTK Analysis

### 4.1 What RTK Is

External Rust CLI proxy for tool-output compression:
- **Source**: https://github.com/rtk-ai/rtk
- **Function**: Intercepts shell command output, compresses before LLM context
- **Claims**: 60-90% token savings on dev commands
- **Integration**: Auto-rewrite hooks at shell level

### 4.2 RTK Compression Strategy

| Strategy | Description |
|----------|-------------|
| Smart Filtering | Removes noise, comments, boilerplate |
| Grouping | Aggregates similar items (files by directory, errors by type) |
| Truncation | Preserves relevant context, eliminates redundancy |
| Deduplication | Collapses repeated log lines with occurrence counts |

### 4.3 RTK vs M2M

| Dimension | WSP-99 M2M | RTK |
|-----------|------------|-----|
| **Layer** | Agent-to-agent protocol | Tool-output compression |
| **Target** | Prompt/instruction tokens | Command result tokens |
| **Direction** | Bidirectional (compile/decompile) | Output-only (compress) |
| **Integration** | Direct Python API | Shell interception hooks |
| **Format** | K:V YAML schema | Smart filtered text |

**VERDICT**: RTK complements M2M, does not replace it.

---

## 5. OpenClaw/Hermes Execution Surfaces

### 5.1 Command Execution Flow

```
OpenClaw DAE (openclaw_dae.py)
    -> execute_plan() (openclaw_execution_routes.py:25-56)
        -> execute_command() for wre_orchestrator route
        -> execute_query() for holo_index route
        -> execute_schedule() for youtube_shorts_scheduler route
    -> WRE CodeAct Executor (codeact_executor.py)
        -> _execute_shell() with shell=False default
        -> forbid_shell_metacharacters gate
```

### 5.2 Security Controls

| Control | Location | Status |
|---------|----------|--------|
| shell=False default | `codeact_executor.py:359` | ACTIVE |
| Shell metachar blocking | `codeact_executor.py:352` | ACTIVE (strict mode) |
| WRE_CODEACT_STRICT | `WRE_RUNBOOK.md:22` | ENV-GATED |
| Escalation shell guard | `daemon_self_audit_loop.py:343-351` | ACTIVE |

### 5.3 RTK Integration Seam

**CURRENT**: None. RTK would need to intercept output AFTER:
- `codeact_executor._execute_shell()` returns
- `subprocess.Popen` stdout/stderr capture

**SEAM CANDIDATES**:
1. `codeact_executor.py` post-execution hook
2. WRE gateway `dae_gateway.py` response handler
3. OpenClaw `execute_command()` result processor

---

## 6. Security Bypass Classes

### 6.1 Required Bypass Rules

Per 012 Addendum, compression must fail open for:

| Class | Reason | Detection Pattern |
|-------|--------|-------------------|
| SECURITY | Security audit output | `CVE-`, `VULNERABILITY`, `EXPLOIT` |
| AUTH | Credentials in output | `token=`, `key=`, `password=`, `secret=` |
| PROVENANCE | Chain of custody | `signed by`, `verified`, `attestation` |
| AMBIGUOUS | Parse uncertainty | Error count > 0 from formatter |

### 6.2 Current State

**SPECIFIED_NOT_IMPLEMENTED**: No bypass class detection exists. RTK integration MUST include fail-open guards before live deployment.

---

## 7. Token Telemetry Current State

### 7.1 Existing Telemetry

| Location | Metrics | Status |
|----------|---------|--------|
| `openclaw_dae.py` | Token usage per turn | ACTIVE |
| `openclaw_turn_state.py` | Cumulative token tracking | ACTIVE |
| `dae_gateway.py` | Token metrics emission | ACTIVE |
| `qwen_gemma_gateway.py` | Worker token tracking | ACTIVE |

### 7.2 Gaps

| Gap | Description |
|-----|-------------|
| NO_SAVINGS_DELTA | No before/after compression comparison |
| NO_COMMAND_CLASS_BREAKDOWN | No per-command-type token stats |
| NO_RTK_METRICS | RTK claims not measurable without integration |
| NO_M2M_SAVINGS_PROOF | M2M 4x claim not validated |

---

## 8. Recommended Module Placement

```
modules/
  infrastructure/
    token_efficiency/          # NEW MODULE
      src/
        __init__.py
        m2m_fidelity_gate.py   # Round-trip semantic validation
        rtk_adapter.py         # RTK subprocess wrapper (if needed)
        bypass_classifier.py   # Security/auth/provenance detection
        telemetry_recorder.py  # Before/after token measurement
      tests/
        test_m2m_fidelity.py
        test_bypass_classifier.py
        test_telemetry.py
      config/
        bypass_patterns.yaml   # Security bypass class definitions
      README.md
      INTERFACE.md
      requirements.txt
```

---

## 9. Implementation Slice Sequence

| Priority | Slice | Dependencies | Scope |
|----------|-------|--------------|-------|
| P0 | REDDOG_WSP99_RTK_TOKEN_EFFICIENCY_CONTRACT_PHASE1 | This audit | Contract/interface design |
| P1 | WSP99_COMPILER_FIDELITY_GATE_PHASE1 | P0 | Round-trip semantic tests |
| P2 | TOKEN_EFFICIENCY_TELEMETRY_SERVICE_PHASE1 | P1 | Before/after measurement |
| P3 | BYPASS_CLASSIFIER_SECURITY_GATE_PHASE1 | P1 | Fail-open detection |
| P4 | RTK_EVALUATION_DRY_RUN_PHASE1 | P2, P3 | RTK subprocess eval (no live) |
| P5 | RTK_OPENCLAW_HERMES_ADAPTER_DRYRUN_PHASE1 | P4 | Integration seam test |
| P6 | REDDOG_COMPUTE_GOVERNOR_PHASE1 | P5 | RedDog M2M routing |

---

## 10. Evidence Table

| Check | Status | Evidence |
|-------|--------|----------|
| WSP-99 remains agent-to-agent protocol | VERIFIED | WSP_99_M2M_Prompting.md Section 1 |
| RTK is tool-output compression only | VERIFIED | RTK GitHub - "compresses command outputs" |
| RedDog is 012-facing architect | VERIFIED | Memory: reddog_recursive_dae_ecosystem_architecture.md |
| ORCH compiles worker packets | PARTIAL | Schema exists, emission not wired |
| Compiler round-trip fidelity exists | MISSING | No semantic equivalence tests |
| Token savings telemetry exists | PARTIAL | Turn-level only, no delta |
| raw_ref recovery exists | MISSING | No recovery mechanism |
| OpenClaw/Hermes command rewrite seam exists | MISSING | No post-execution hook |
| Security bypass classes defined | MISSING | No bypass classifier |

---

## 11. Residual SPECIFIED_NOT_IMPLEMENTED

| Item | Blocker | Next Slice |
|------|---------|------------|
| RedDog compute classification | No M2M router in RedDog | REDDOG_COMPUTE_GOVERNOR_PHASE1 |
| M2M compiler fidelity tests | No semantic test harness | WSP99_COMPILER_FIDELITY_GATE_PHASE1 |
| RTK adapter | RTK not installed | RTK_EVALUATION_DRY_RUN_PHASE1 |
| Token-savings telemetry | No delta measurement | TOKEN_EFFICIENCY_TELEMETRY_SERVICE_PHASE1 |
| Raw-output recovery | No storage mechanism | WSP99_COMPILER_FIDELITY_GATE_PHASE1 |
| OpenClaw/Hermes command rewrite | No seam hook | RTK_OPENCLAW_HERMES_ADAPTER_DRYRUN_PHASE1 |

---

## 12. WSP 97 Truth Boundary Checklist

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | AUDIT_ONLY | YES | No code changes |
| 2 | NO_RTK_RUNTIME_INTEGRATION | YES | RTK not installed |
| 3 | NO_M2M_COMPILER_MUTATION | YES | m2m_compiler.py unchanged |
| 4 | NO_OPENCLAW_MUTATION | YES | No execution route changes |
| 5 | NO_HERMES_MUTATION | YES | vendor/hermes-agent untouched |
| 6 | WSP99_ROLE_VERIFIED | YES | Agent-to-agent protocol confirmed |
| 7 | RTK_ROLE_VERIFIED | YES | Tool-output compression confirmed |
| 8 | STACK_PLACEMENT_SPECIFIED | YES | Section 4.3 |
| 9 | GAPS_ENUMERATED | YES | Sections 3.3, 6.2, 7.2 |
| 10 | BYPASS_CLASSES_SPECIFIED | YES | Section 6.1 |
| 11 | MODULE_PLACEMENT_RECOMMENDED | YES | Section 8 |
| 12 | SLICE_SEQUENCE_DEFINED | YES | Section 9 |
| 13 | EVIDENCE_TABLE_COMPLETE | YES | Section 10 |
| 14 | RESIDUAL_TRACKED | YES | Section 11 |
| 15 | NO_TOKEN_SAVINGS_CLAIMED_WITHOUT_MEASUREMENT | YES | Claims noted as unvalidated |

**WSP 97 Truth Boundary Checklist: 15/15 YES**

---

## 13. Verdict

**PROCEED_TO_CONTRACT**

The audit confirms:
1. WSP-99 M2M and RTK serve distinct, complementary roles
2. Current M2M compiler is functional but lacks fidelity gates
3. RTK is not present and requires evaluation before integration
4. Security bypass classes are unimplemented (P0 blocker for RTK)
5. Token telemetry exists at turn-level but lacks compression delta
6. OpenClaw/Hermes command execution has no RTK seam

**Next Safest Slice**: `REDDOG_WSP99_RTK_TOKEN_EFFICIENCY_CONTRACT_PHASE1`

---

*W9 complete for REDDOG_WSP99_RTK_TOKEN_EFFICIENCY_AUDIT_PHASE1. WSP-99 remains the agent protocol. RTK fits as tool-output compression layer. Contract slice unlocked.*
