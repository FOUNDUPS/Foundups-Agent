# Agent Security Stack WSP Annex Mapping — Phase 1

**Date**: 2026-05-20
**Window**: W9
**Slice**: AGENT_SECURITY_STACK_WSP_ANNEX_MAPPING_PHASE1
**Base Commit**: `600eee482430870a6857134834c5ed54314d10ff`
**Branch**: `docs/agent-security-stack-wsp-annex-mapping-phase1`
**Mode**: DOCS_ONLY / WSP_ANNEX_MAPPING_ONLY

---

## WSP 97 Truth Boundary Labels

| Label | Status |
|-------|--------|
| DOCS_ONLY | YES |
| WSP_ANNEX_MAPPING_ONLY | YES |
| CITES_AUDIT_PHASE1 | YES |
| NO_WSP_MUTATION | YES |
| NO_NEW_WSP_CREATION | YES |
| NO_DEPENDENCY_INSTALL | YES |
| NO_SECRET_ACCESS | YES |
| NO_CREDENTIAL_CREATION | YES |
| NO_1PASSWORD_CONFIGURATION | YES |
| NO_RAMPART_CONFIGURATION | YES |
| NO_CLARITY_PROTOCOL_DIRECTORY | YES |
| NO_RUNTIME_CHANGE | YES |
| NO_AGENTDB_MUTATION | YES |
| NO_HOLOINDEX_MUTATION | YES |
| NO_MCP_CHANGE | YES |
| NO_CABR_READY | YES |
| NO_PAYOUT_READY | YES |
| NO_DAO_ACTIVATION | YES |

---

## 1. Source of Truth

### 1.1 Canonical Source

**Document**: `docs/audits/security/AGENT_SECURITY_STACK_EXTERNAL_INTEGRATION_AUDIT_PHASE1.md`
**Merged Commit**: `600eee482430870a6857134834c5ed54314d10ff`
**Merge Date**: 2026-05-22

### 1.2 External Findings Summary

| External System | Purpose | Key Capability |
|-----------------|---------|----------------|
| **1Password MCP** | Secret retrieval, rotation, audit trail | `op://vault/item/field` runtime resolution, hash-based audit, no secrets in prompts |
| **RAMPART** | Red-team regression tests | Prompt injection, tool misuse, credential exfiltration, HoloIndex poisoning tests |
| **Clarity** | Assumption audit, problem statement, failure analysis | Structured conversations, decision records, `.clarity-protocol/` artifact storage |

---

## 2. WSP Ownership Survey

### 2.1 Active WSP Owners

| WSP | Name | Status | Ownership Scope |
|-----|------|--------|-----------------|
| **WSP_71** | Secrets Management Protocol | ACTIVE | Secrets storage, retrieval, access control, audit trails, vault integration |
| **WSP_6** | Test Audit Coverage Verification | ACTIVE | Test execution, coverage gates, regression tests, red-team test integration |
| **WSP_97** | System Execution Prompting Protocol | ACTIVE | Execution gates, assumption verification, CoT/CoR gates, dialectic sweep |
| **WSP_83** | Documentation Tree Attachment Protocol | ACTIVE | Documentation placement, orphan prevention, artifact attachment rules |
| **WSP_50** | Pre-Action Verification Protocol | ACTIVE | Pre-action verification, tool adoption preflight, search-before-act |

### 2.2 Deprecated WSP (Not Owner)

| WSP | Name | Status | Note |
|-----|------|--------|------|
| **WSP_16** | Test Audit Coverage | **DEPRECATED** | Superseded by WSP_6. MUST NOT be selected as owner for any security concern. |

---

## 3. Mapping Table

| External System | Concern | Existing WSP Owner | Proposed Annex Anchor | Gap |
|-----------------|---------|-------------------|----------------------|-----|
| 1Password / MCP runtime credential references | `op://` pattern resolution at MCP gateway | **WSP_71** | WSP_71 Annex: MCP Runtime Credential Access | No `op://` resolver exists |
| 1Password audit logging and TTL | Hash-based audit trail, just-in-time secret access | **WSP_71** | WSP_71 Annex: MCP Runtime Credential Access | No hash audit, no TTL enforcement |
| RAMPART prompt-injection regression tests | Cross-prompt injection attack testing | **WSP_6** | WSP_6 Annex: Agent Red-Team Regression Tests | No PyRIT/RAMPART integration |
| RAMPART tool-misuse / scope-lock tests | Agent tool boundary enforcement tests | **WSP_6** | WSP_6 Annex: Agent Red-Team Regression Tests | No tool-misuse test framework |
| RAMPART credential-exfiltration tests | Secret leakage detection in agent outputs | **WSP_6** | WSP_6 Annex: Agent Red-Team Regression Tests | No exfiltration test suite |
| RAMPART HoloIndex poisoning tests | Adversarial content injection testing | **WSP_6** | WSP_6 Annex: Agent Red-Team Regression Tests | No HoloIndex poisoning tests |
| Clarity problem statement / assumption capture | Pre-design assumption validation | **WSP_97** | WSP_97 Annex: High-Risk Assumption Audit Gate | No structured assumption capture |
| Clarity failure analysis / decision record | Post-incident decision tracking | **WSP_97** | WSP_97 Annex: High-Risk Assumption Audit Gate | No Clarity-style decision records |
| Clarity artifact placement under WSP_83 | `.clarity-protocol/` directory attachment | **WSP_83** | WSP_83 Annex: Clarity Artifact Attachment | No `.clarity-protocol/` placement rule |

**Total Rows**: 9

---

## 4. Proposed Annex Anchors

### 4.1 WSP_71 Annex: MCP Runtime Credential Access

**Scope**:
- `op://vault/item/field` reference pattern support
- Runtime credential resolution via 1Password SDK at MCP gateway
- Hash-based audit trail without exposing values
- Just-in-time secret access with TTL enforcement
- Automatic rotation detection via hash comparison

**Existing WSP_71 Gaps**:
- No vault reference pattern (`op://`) support
- No MCP gateway credential injection
- No hash-based audit trail

### 4.2 WSP_6 Annex: Agent Red-Team Regression Tests

**Scope**:
- PyRIT/RAMPART-style test framework integration
- Cross-prompt injection attack testing
- Tool-misuse and scope-lock boundary tests
- Credential exfiltration detection tests
- HoloIndex adversarial poisoning tests
- CI/CD integration for regression testing

**Existing WSP_6 Gaps**:
- No red-team test framework
- No prompt injection test suite
- No tool boundary regression tests

### 4.3 WSP_97 Annex: High-Risk Assumption Audit Gate

**Scope**:
- Clarity-style problem clarification conversations
- Assumption validation before high-risk execution
- Multi-perspective analysis (security, adversarial, operational)
- Decision record generation and tracking
- Staleness detection for assumption artifacts

**Existing WSP_97 Gaps**:
- No structured assumption capture format
- No Clarity-style conversation protocol
- No decision record schema

### 4.4 WSP_83 Annex: Clarity Artifact Attachment

**Scope**:
- `.clarity-protocol/` directory placement rules
- Clarity artifact attachment to module/WSP tree
- Orphan prevention for Clarity outputs
- Integration with WSP_22 ModLog tracking

**Existing WSP_83 Gaps**:
- No `.clarity-protocol/` directory specification
- No Clarity artifact attachment rule

### 4.5 WSP_50 Annex: External Tool Adoption Preflight

**Scope**:
- Pre-adoption verification for external tools
- Security assessment before integration
- Dependency scanning requirements
- Configuration audit before activation

**Existing WSP_50 Gaps**:
- No external tool adoption checklist
- No pre-integration security gate

---

## 5. Gap List

| Gap ID | Description | Owner WSP | Priority |
|--------|-------------|-----------|----------|
| G1 | No `op://` vault reference resolver | WSP_71 | HIGH |
| G2 | No MCP gateway credential injection | WSP_71 | HIGH |
| G3 | No hash-based credential audit trail | WSP_71 | MEDIUM |
| G4 | No secret TTL / just-in-time access | WSP_71 | MEDIUM |
| G5 | No PyRIT/RAMPART integration | WSP_6 | HIGH |
| G6 | No prompt injection regression tests | WSP_6 | HIGH |
| G7 | No tool-misuse boundary tests | WSP_6 | MEDIUM |
| G8 | No credential exfiltration tests | WSP_6 | HIGH |
| G9 | No HoloIndex poisoning tests | WSP_6 | MEDIUM |
| G10 | No Clarity assumption capture format | WSP_97 | MEDIUM |
| G11 | No decision record schema | WSP_97 | LOW |
| G12 | No `.clarity-protocol/` placement rule | WSP_83 | LOW |
| G13 | No external tool adoption preflight | WSP_50 | MEDIUM |

**Total Gaps**: 13

---

## 6. Why WSP_97 Alone Is Insufficient

### 6.1 WSP_97's Role

WSP_97 is the **execution gate**. It defines:
- How 0102 operates (retrieve → research → hard think → dialectic sweep → execute)
- CoT/CoR gates before committing
- Assumption verification during execution
- Activation defaults and micro/macro passes

### 6.2 What WSP_97 Does NOT Own

| Concern | Why WSP_97 Is Insufficient | Correct Owner |
|---------|---------------------------|---------------|
| Secrets storage/retrieval | WSP_97 gates execution, not credential lifecycle | **WSP_71** |
| Test regression framework | WSP_97 gates execution, not test infrastructure | **WSP_6** |
| Documentation attachment | WSP_97 gates execution, not artifact placement | **WSP_83** |
| Pre-action verification | WSP_97 is execution-time, not pre-action | **WSP_50** |

### 6.3 Persistent Policy vs Execution Gate

| Type | Definition | Examples |
|------|------------|----------|
| **Execution Gate** (WSP_97) | Gates individual execution, per-task CoT/CoR | Assumption audit during slice, dialectic sweep |
| **Persistent Policy** (WSP_71/6/83/50) | Defines standing rules, infrastructure, artifacts | Vault integration, test framework, doc placement |

**Conclusion**: WSP_97 triggers assumption audits but does not own the persistent infrastructure for secrets, tests, or documentation. Those belong to specialized WSPs.

---

## 7. Framework + Knowledge Sync Requirements

### 7.1 Current State

| Path | Purpose | Sync Status |
|------|---------|-------------|
| `WSP_framework/src/` | Canonical WSP definitions | PRIMARY |
| `WSP_knowledge/src/` | Knowledge base mirror | REQUIRES_SYNC |

### 7.2 Phase 2 Sync Requirements

| WSP | Framework Update | Knowledge Sync Needed |
|-----|-----------------|----------------------|
| WSP_71 | Add MCP Runtime Credential Access annex | YES |
| WSP_6 | Add Agent Red-Team Regression Tests annex | YES |
| WSP_97 | Add High-Risk Assumption Audit Gate annex | YES |
| WSP_83 | Add Clarity Artifact Attachment annex | YES |
| WSP_50 | Add External Tool Adoption Preflight annex | YES |

---

## 8. HoloIndex Assessment

### 8.1 Queries Executed

| Query | Hits | Quality | Notes |
|-------|------|---------|-------|
| `WSP 71 secrets MCP runtime credentials vault agent access` | 32 | EXCELLENT | Found secrets_mcp, WSP_71, WSP_96 |
| `WSP 6 test audit coverage agent red team pytest prompt injection` | 32 | GOOD | Found WSP_6, WSP_16 (deprecated), WSP_5 |
| `WSP 97 assumption audit Clarity high risk agent integration` | 31 | GOOD | Found WSP_6, WSP_16, audit docs |
| `WSP 83 orphan docs clarity protocol documentation tree attachment` | FAIL | N/A | Orphan dataset not found |

### 8.2 Fallback Required

**YES** — Query 4 failed due to "orphan" keyword triggering orphan analysis mode. Retried with alternative query `WSP 83 documentation tree module README INTERFACE attachment` which returned different output format (DOC_LOOKUP intent).

### 8.3 HoloIndex Improvement Recommendation

- "orphan" keyword should not trigger orphan analysis mode in general searches
- Alternative: add escape syntax to disable special keyword handling

---

## 9. WSP_15 Next-Slice Recommendation

### 9.1 Primary Recommendation

**`AGENT_SECURITY_STACK_WSP_ANNEX_UPDATE_PHASE1`**

**Scope**:
1. Update WSP_71 with MCP Runtime Credential Access annex
2. Update WSP_6 with Agent Red-Team Regression Tests annex
3. Update WSP_97 with High-Risk Assumption Audit Gate annex
4. Update WSP_83 with Clarity Artifact Attachment annex
5. Update WSP_50 with External Tool Adoption Preflight annex

**Constraints**:
- Annex additions only, no restructuring
- No dependency installation
- No runtime changes
- Sync WSP_knowledge after framework update

### 9.2 Secondary Recommendations

| Priority | Slice | Scope |
|----------|-------|-------|
| P1 | `SECRETS_MCP_1PASSWORD_RESOLVER_PHASE1` | Implement `op://` resolver |
| P1 | `WSP_6_RAMPART_TEST_FRAMEWORK_PHASE1` | Add PyRIT/RAMPART test infrastructure |
| P2 | `CLARITY_PROTOCOL_INTEGRATION_PHASE1` | Add `.clarity-protocol/` support |

---

## 10. WSP_97 Verdict

| Check | Result |
|-------|--------|
| Docs only | PASS |
| No WSP mutation | PASS |
| No new WSP creation | PASS |
| No dependency install | PASS |
| No secret access | PASS |
| No 1Password/RAMPART/Clarity configuration | PASS |
| No runtime change | PASS |
| No AgentDB/HoloIndex/MCP mutation | PASS |
| Cites Phase 1 audit | PASS |
| WSP_16 correctly marked deprecated | PASS |

**Verdict**: PASS

---

## Sources

### Internal

| Document | Location |
|----------|----------|
| Phase 1 Audit | `docs/audits/security/AGENT_SECURITY_STACK_EXTERNAL_INTEGRATION_AUDIT_PHASE1.md` |
| WSP_71 | `WSP_framework/src/WSP_71_Secrets_Management_Protocol.md` |
| WSP_6 | `WSP_framework/src/WSP_6_Test_Audit_Coverage_Verification.md` |
| WSP_97 | `WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md` |
| WSP_83 | `WSP_framework/src/WSP_83_Documentation_Tree_Attachment_Protocol.md` |
| WSP_50 | `WSP_framework/src/WSP_50_Pre_Action_Verification_Protocol.md` |
| WSP_16 (deprecated) | `WSP_framework/src/WSP_16_Test_Audit_Coverage.md` |

---

*Audit performed by Worker W9 under WSP_00 → WSP_15 → WSP_50 → WSP_64 → WSP_83 → WSP_87 → WSP_97 → WSP_22 → WSP_71 → WSP_6.*
*Slice: AGENT_SECURITY_STACK_WSP_ANNEX_MAPPING_PHASE1*
