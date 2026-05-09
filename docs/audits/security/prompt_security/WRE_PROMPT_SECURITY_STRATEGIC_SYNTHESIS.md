# WRE Prompt Security Strategic Synthesis

**Date**: 2026-05-10
**Worker**: W5
**Slice**: `WRE_PROMPT_SECURITY_SYNTHESIS_AND_CONCATENATION_PHASE1_RERUN`
**WSP Lock**: WSP 00 → WSP 97 → WSP 15 → WSP 50
**Mode**: Architecture synthesis — not implementation

---

## 1. Final Architect Verdict

### **READY_FOR_WSP_CANON_ANNEX_FIRST**

Before implementing SEC10 (Prompt Security Sentinel), update WSP canon to formally define prompt security gating in the WRE architecture.

**Rationale**:
- W2/W3 confirm SEC10 placement in `wre_core/src/` is architecturally correct
- W3 research validates CaMeL-style P/Q separation as industry best practice
- W4 vision provides 3-layer architecture ready for implementation
- However, no existing WSP formally governs "prompt security gating"
- WSP 96 (MCP Governance) is closest but focuses on consensus, not injection defense
- New WSP annex or WSP 109 should canonize the sentinel before code

---

## 2. Evidence from W2 Codebase Placement Audit

### 2.1 Verdict

**PLACE_IN_EXISTING_WRE_SECURITY_LAYER**

### 2.2 Key Findings

| Finding | Evidence |
|---------|----------|
| SEC1-SEC9 stack exists | `wre_core/src/security_*.py` (6+ files) |
| `security_control_hooks.py` is canonical entry | SecurityState literals: triggered/proposed/executed/unavailable/escalated |
| `security_trigger.py` demonstrates pattern | SECURITY_PATTERNS dict for file detection |
| No existing prompt security module | Grep found no `prompt_security*.py` |
| Agent permissions consume security signals | PROMOTION_THRESHOLDS in `agent_permission_manager.py` |

### 2.3 Proposed Location

```
modules/infrastructure/wre_core/src/prompt_security_sentinel.py
```

---

## 3. Evidence from W3 External Research

### 3.1 Verdict

**ADOPT_CAMEL_STYLE_P_Q_SEPARATION**

### 3.2 Key Findings

| Pattern | Source | Effectiveness |
|---------|--------|---------------|
| CaMeL P-LLM/Q-LLM | Berkeley SPAR 2025 | 77% task utility, provable security |
| AgentSandbox PA/EA | AgentSandbox 2025 | 4.34% attack success (91% reduction) |
| OWASP LLM01:2025 | OWASP | Privilege control, content segregation |

### 3.3 Threat Model

| Attack Class | FoundUps Risk | Mitigation |
|--------------|---------------|------------|
| Indirect Prompt Injection | CRITICAL | Content taint tracking |
| Tool Hijacking | HIGH | SEC10 gate before MCP |
| Memory Poisoning | HIGH | HoloIndex integrity checks |
| Recursive Amplification | CRITICAL | Depth limits, cycle detection |

### 3.4 CVE References

| CVE | Description | Relevance |
|-----|-------------|-----------|
| CVE-2025-49596 | MCP localhost exposure | MCP servers vulnerable |
| CVE-2026-25253 | ClawJacked WebSocket hijacking | Browser-based attacks |

---

## 4. Evidence from W4 Vision Architecture

### 4.1 Three-Layer Architecture

| Layer | Component | Purpose |
|-------|-----------|---------|
| 0 | Ingestion Gate | Content classification, pattern scanning, threat hotlist |
| 1 | Auth Gate | Tool authorization, signature verification, capability limits |
| 2 | Recursion Guard | Depth limits, cycle detection, state snapshots |

### 4.2 Proposed SEC Slots

| SEC | Name | Function |
|-----|------|----------|
| SEC10 | RPSS Ingestion Gate | Content sanitization |
| SEC11 | RPSS Auth Gate | Tool authorization |
| SEC12 | RPSS Recursion Guard | Recursive execution safety |

### 4.3 Integration Points

- `security_control_hooks.py` (SEC9) — State management
- `security_pattern_memory.py` — Threat pattern storage
- `agent_permission_manager.py` — Authority verification
- `wre_master_orchestrator.py` — Execution gating

---

## 5. Process Drift Notes

### 5.1 Resolved Drift

| Issue | Resolution |
|-------|------------|
| W4 created vision under `docs/architecture/security/` | Recovered to `docs/audits/security/prompt_security/` |
| Squash merge produced duplicate paths | Cleanup removed old path (`49e13f7d8`) |
| W5 initially blocked on missing W4 artifact | Rerun after path recovery |

### 5.2 Canonical Path

```
docs/audits/security/prompt_security/WRE_RECURSIVE_PROMPT_SECURITY_SENTINEL_VISION.md
```

---

## 6. Recommended Canonical Placement

### 6.1 Primary Module

```
modules/infrastructure/wre_core/src/prompt_security_sentinel.py
```

### 6.2 Optional Submodule (if complexity warrants)

```
modules/infrastructure/wre_core/src/security_sentinel/
  __init__.py
  ingestion_gate.py
  auth_gate.py
  recursion_guard.py
  threat_hotlist.py
  policy_engine.py
```

### 6.3 Memory Storage

```
holo_index/.ssd/security/threat_hotlist.json
```

---

## 7. Proposed Module Path

**Primary**: `modules/infrastructure/wre_core/src/prompt_security_sentinel.py`

**Class**: `PromptSecuritySentinel` (SEC10)

**Core Interface**:
```python
class PromptSecuritySentinel:
    def check_prompt(self, prompt: str, context: dict) -> PromptSecurityResult
    def register_pattern(self, pattern: str, threat_type: str) -> None
    def get_security_state(self) -> SecurityState
```

---

## 8. Proposed WSP Relationship

### 8.1 New WSP Option

**WSP 109: Prompt Security Gating Protocol** (proposed)

Contents:
- Define SEC10 role in WRE execution flow
- Specify trust levels (TRUSTED, VERIFIED, UNTRUSTED, HOSTILE)
- Require content taint tracking for HoloIndex retrieval
- Mandate Gate 0 (prompt security) before Gate 1 (identity)

### 8.2 WSP 96 Annex Option

Add section to WSP 96 (MCP Governance):
- "Section 11: Prompt Security Pre-Gate"
- Define SEC10 as mandatory check before MCP tool calls

### 8.3 Recommended

**Create WSP 109** — Prompt security is distinct from MCP governance and deserves canonical protocol status.

---

## 9. Interface Contract Summary

### 9.1 Input Contract

```python
@dataclass
class PromptSecurityContext:
    prompt: str                    # Content to validate
    source: str                    # Origin (user, web, holoindex, mcp)
    trust_level: int               # 0=hostile, 1=untrusted, 2=verified, 3=trusted
    caller_identity: str           # 0102 identity or agent ID
    capability_token: Optional[str] # If signed prompt
```

### 9.2 Output Contract

```python
@dataclass
class PromptSecurityResult:
    safe: bool                     # Pass/fail gate
    risk_score: float              # 0.0 = safe, 1.0 = malicious
    threat_type: Optional[str]     # injection, jailbreak, exfiltration, None
    max_action_class: str          # D0-D6 capability ceiling
    sanitized_prompt: Optional[str] # If auto-sanitization enabled
    evidence: List[str]            # Matched patterns or heuristics
```

---

## 10. Data Model Summary

### 10.1 Threat Hotlist Schema

```json
{
  "hotlist_version": "1.0.0",
  "patterns": [
    {
      "id": "INJ-001",
      "type": "indirect_injection",
      "pattern": "ignore previous instructions",
      "severity": "CRITICAL",
      "action": "BLOCK"
    }
  ]
}
```

### 10.2 SecurityState Extension

```python
SecurityState = Literal[
    "triggered",      # Existing
    "proposed",       # Existing
    "executed",       # Existing
    "unavailable",    # Existing
    "escalated",      # Existing
    "injection_blocked",   # NEW - SEC10
    "recursion_halted",    # NEW - SEC12
]
```

---

## 11. PoC / Prototype / MVP Roadmap

### Phase 1: WSP Canon (Week 1)

- Create WSP 109 draft
- Define trust levels and gate requirements
- Get 012 approval

### Phase 2: Prototype (Week 2)

- Scaffold `prompt_security_sentinel.py`
- Implement basic regex pattern matching
- Add known injection patterns (INJ-001..INJ-010)

### Phase 3: SEC Integration (Week 3)

- Register SEC10 in `security_control_hooks.py`
- Add Gate 0 to WRE execution flow
- Implement SecurityState extension

### Phase 4: HoloIndex Integration (Week 4)

- Create `threat_hotlist.json` in HoloIndex
- Implement taint tracking for retrieved content
- Add recall interface for threat patterns

### Phase 5: Hardening (Week 5+)

- Gemma classification integration (optional)
- Performance benchmarking (<10ms gate latency)
- Recursion guard implementation (SEC12)

---

## 12. Tests Required

| Test Category | Coverage |
|---------------|----------|
| Unit: Pattern matching | Known injection patterns blocked |
| Unit: Trust level classification | Source → trust level mapping |
| Unit: Capability ceiling | Untrusted → max D2, Hostile → max D0 |
| Integration: SEC10 → SEC9 | State propagation |
| Integration: SEC10 → MCP | Gate before tool call |
| E2E: Injection attempt | Block → quarantine → log |
| Performance: Gate latency | <10ms per check |

---

## 13. Do-Not-Touch List

| Category | Items |
|----------|-------|
| Claude Code Harness | All internal harness code |
| MCP Transport | JSON-RPC layer, stdio transport |
| External APIs | OAuth, external service auth |
| Core WSP Protocols | WSP 00, WSP 97 (reference only) |
| FAM/FoundUp Runtime | pAVS execution layer |

---

## 14. Open Blockers

| Blocker | Status | Owner |
|---------|--------|-------|
| WSP canon undefined | PENDING | 012 approval for WSP 109 |
| Threat pattern corpus | PENDING | Security research |
| Gemma classification integration | DEFERRED | Not required for prototype |
| Performance budget | TBD | Benchmark after prototype |

---

## 15. WSP 97 Truth Table

| Claim | Status | Evidence |
|-------|--------|----------|
| W2 codebase audit complete | TRUE | `WRE_PROMPT_SECURITY_CODEBASE_PLACEMENT_AUDIT.md` |
| W3 external research complete | TRUE | `WRE_PROMPT_SECURITY_EXTERNAL_RESEARCH.md` |
| W4 vision architecture complete | TRUE | `WRE_RECURSIVE_PROMPT_SECURITY_SENTINEL_VISION.md` |
| SEC10 code implemented | FALSE | Architecture only |
| WSP 109 created | FALSE | Recommended, not created |
| Threat hotlist populated | FALSE | Schema defined only |
| Integration tested | FALSE | No code exists |
| Production deployed | FALSE | Architecture phase |

### 15.1 Claim Classification

| Source | Classification |
|--------|----------------|
| SEC1-SEC9 exists | VERIFIED_FACT (codebase read) |
| CaMeL 77% effectiveness | VERIFIED_FACT (external paper) |
| SEC10 fits architecture | PLAUSIBLE_INTERPRETATION |
| WSP 109 should precede code | STRATEGIC_RECOMMENDATION |

---

## 16. HoloIndex Verification Result

```
[OK] Analysis complete: 40 hits
Top hits:
  [CODE] wre_core/src/security_control_hooks.py
  [CODE] ai_overseer/src/fam_security_sentinel.py
  [CODE] wre_core/src/security_trigger.py
  [WSP] WSP_99_M2M_Prompting.md
  [WSP] WSP_21_Enhanced_Prompt_Engineering_Protocol.md
  [DOCS] HOLOINDEX_WSP_GUARDIAN_ARCHITECTURE.md
```

No existing "prompt_security_sentinel" found — confirms green field for SEC10.

---

## 17. Recommended Next Slice

**WSP_109_PROMPT_SECURITY_GATING_CANON_PHASE1**

Create WSP 109 draft defining:
- SEC10 role in WRE execution flow
- Trust level taxonomy
- Gate requirements before tool calls
- Recursion limits

After WSP 109 approval:
- **PROMPT_SECURITY_SENTINEL_SCAFFOLD_PHASE1**: Create module scaffold
- **PROMPT_SECURITY_THREAT_CORPUS_PHASE1**: Populate initial patterns

---

## Sources

### Internal

| Document | Location |
|----------|----------|
| W2 Placement Audit | `docs/audits/security/prompt_security/WRE_PROMPT_SECURITY_CODEBASE_PLACEMENT_AUDIT.md` |
| W3 External Research | `docs/audits/security/prompt_security/WRE_PROMPT_SECURITY_EXTERNAL_RESEARCH.md` |
| W4 Vision Architecture | `docs/audits/security/prompt_security/WRE_RECURSIVE_PROMPT_SECURITY_SENTINEL_VISION.md` |
| Security Control Hooks | `modules/infrastructure/wre_core/src/security_control_hooks.py` |

### External

| Source | Reference |
|--------|-----------|
| CaMeL Paper | arxiv.org/abs/2503.18813 |
| AgentSandbox | arxiv.org/abs/2502.17089 |
| OWASP LLM Top 10 | genai.owasp.org |
| CVE-2025-49596 | nvd.nist.gov |

---

## WSP 97 Note

**Truth Boundaries Applied**:

1. No runtime implementation claim — SEC10 is proposed, not implemented
2. External research patterns are from published papers, not codebase facts
3. CaMeL mapping to WRE is strategic hypothesis, not verified implementation
4. All worker artifacts read and synthesized without modification
5. Process drift documented truthfully

---

*Synthesis performed by Worker W5 under WSP 97 truth boundaries.*
*Slice: WRE_PROMPT_SECURITY_SYNTHESIS_AND_CONCATENATION_PHASE1_RERUN*
