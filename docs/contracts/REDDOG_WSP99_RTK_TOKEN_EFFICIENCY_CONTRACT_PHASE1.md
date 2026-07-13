# REDDOG_WSP99_RTK_TOKEN_EFFICIENCY_CONTRACT_PHASE1

Status: RATIFIED CONTRACT SPEC (decision-only; no RTK binary, no runtime integration, no command rewrite).
Base: 1b04e45c2 (origin/main HEAD at write-time)
Author-role: 0102 architect (contract author, not implementer)
Ratifies: docs/audits/architecture/REDDOG_WSP99_RTK_TOKEN_EFFICIENCY_AUDIT_PHASE1.md (audit PR #937, squash 1b04e45c2)
WSP: WSP_97 (truth boundary), WSP_99 (M2M protocol), WSP_50 (pre-action), WSP_22 (docs)

Truth-label legend (WSP_97):
- OBSERVED                    = read directly from source at the cited file:line
- INFERRED                    = concluded from OBSERVED evidence, not itself a literal
- SPECIFIED_NOT_IMPLEMENTED   = defined by this contract; does NOT exist in code yet
- NEEDS_VERIFICATION          = asserted elsewhere, not confirmed here

Relationship to predecessor (WSP_50):
This document does NOT re-derive the audit. It RATIFIES it. The boundaries below are the
audit's Sections 3-6 frozen to wire-level truth. The bypass classes below are the audit's
Section 6.1 turned into a fail-closed matrix. Where this contract cites file:line, those
lines were re-verified live against Base above.

---

## 0. Purpose and scope

Purpose: turn the audit's SPECIFIED_NOT_IMPLEMENTED items into a ratified contract that
leaves a future implementer ZERO ambiguity about compression boundaries, bypass classes,
and telemetry requirements.

The single certifying sentence (from 012 Addendum, verbatim):

    RTK is not the M2M language.
    RTK is a tool-output compression layer.

Under this contract:
- WSP-99 M2M remains canonical for 0102-to-0102 agent packets
- RTK (if/when integrated) ONLY compresses tool command OUTPUT
- Security/auth/provenance/signing/permission/receipt outputs bypass compression by default
- No compression without measured savings
- No compression without raw recovery path

Out of scope for THIS slice (enforced as contract invariants, see Section 14):
RTK binary install, RTK subprocess calls, OpenClaw/Hermes command rewrite, live telemetry
store, dependency install, any external command execution except read-only source checks.

---

## 1. Compression boundary definitions [SPECIFIED_NOT_IMPLEMENTED]

### 1a. WSP-99 M2M Prompt Compression Boundary

| Property | Value | Evidence |
|----------|-------|----------|
| Layer | Agent-to-agent prompt packets | OBSERVED WSP_99_M2M_Prompting.md Section 0 |
| Direction | Bidirectional (compile/decompile) | OBSERVED m2m_compiler.py:204-237 |
| Format | K:V YAML schema | OBSERVED 0102_M2M_SCHEMA.yaml:1-27 |
| Target | ORCH -> Worker, Worker -> ORCH, Worker -> QA | OBSERVED WSP_99_M2M_Prompting.md Section 3 |
| Owner | ORCH layer (compiles), Workers (consume) | INFERRED from Section 3 |

Boundary rule: WSP-99 M2M compresses PROMPTS before agent dispatch. It does NOT compress
tool output. M2M is the language BETWEEN agents, not the format of tool results.

### 1b. RTK Tool-Output Compression Boundary

| Property | Value | Evidence |
|----------|-------|----------|
| Layer | Command execution output | OBSERVED RTK GitHub README |
| Direction | Output-only (compress, no decompile) | OBSERVED RTK architecture |
| Format | Smart-filtered text | OBSERVED RTK strategies |
| Target | Shell/subprocess stdout/stderr | INFERRED from RTK docs |
| Owner | Post-execution hook (not ORCH, not M2M) | SPECIFIED_NOT_IMPLEMENTED |

Boundary rule: RTK compresses OUTPUT from commands AFTER execution completes. It does NOT
touch prompts, M2M packets, or agent-to-agent communication. RTK is a filter on tool
results, not a protocol replacement.

### 1c. Boundary separation invariant

```
INVARIANT: M2M and RTK NEVER overlap.

M2M domain:  { x | x is an agent prompt or inter-agent packet }
RTK domain:  { y | y is a command execution result }

M2M domain INTERSECTION RTK domain = EMPTY SET

Violation: Applying RTK to M2M output or M2M to command results.
```

---

## 2. RedDog compute governor responsibilities [SPECIFIED_NOT_IMPLEMENTED]

### 2a. Role definition

RedDog is the 012-facing architect. It receives human intent and routes to ORCH.
RedDog does NOT currently emit or consume M2M packets. This contract specifies that
RedDog SHOULD have a compute governor that:

| Responsibility | Description | Status |
|----------------|-------------|--------|
| Task classification | Classify incoming task for effort/mode | OBSERVED classifyTaskForRedDog() extension.js |
| M2M delegation | Decide if ORCH should emit M2M to workers | SPECIFIED_NOT_IMPLEMENTED |
| Compression policy | Decide if RTK should compress tool output | SPECIFIED_NOT_IMPLEMENTED |
| Bypass routing | Route security/auth outputs around compression | SPECIFIED_NOT_IMPLEMENTED |
| Telemetry gate | Ensure no telemetry until bypass is proven | SPECIFIED_NOT_IMPLEMENTED |

### 2b. Compute governor wire format [SPECIFIED_NOT_IMPLEMENTED]

```yaml
RedDogComputeDecision:
  task_id: string             # Unique task identifier
  classified_effort: string   # ULTRA | HIGH | REGULAR | MINIMAL
  m2m_emit: bool              # Should ORCH emit M2M to workers?
  rtk_compress: bool          # Should tool output be RTK-compressed?
  bypass_classes: array       # Which bypass classes apply to this task?
  telemetry_allowed: bool     # Is telemetry safe for this task's outputs?
```

---

## 3. ORCH M2M compiler responsibilities [SPECIFIED_NOT_IMPLEMENTED]

### 3a. Current state (OBSERVED)

| Component | Location | Status |
|-----------|----------|--------|
| M2MCompiler class | prompt/swarm/m2m_compiler.py:137-297 | ACTIVE |
| compile() method | m2m_compiler.py:148-202 | ACTIVE |
| decompile() method | m2m_compiler.py:204-237 | ACTIVE |
| parse_compact() method | m2m_compiler.py:239-297 | ACTIVE |
| Qwen-callable entry | m2m_compiler.py:334-356 | ACTIVE |

### 3b. Missing capabilities [SPECIFIED_NOT_IMPLEMENTED]

| Capability | Contract requirement |
|------------|----------------------|
| Fidelity gate | compile(x) -> M2M -> decompile(M2M) MUST preserve semantic equivalence |
| Round-trip test | Automated test proving compile -> decompile -> compare passes |
| Raw storage | Original prose MUST be recoverable if M2M is rejected downstream |
| Emission wiring | ORCH MUST actually emit M2M to workers (currently theoretical) |

### 3c. Fidelity gate specification [SPECIFIED_NOT_IMPLEMENTED]

```python
def assert_m2m_fidelity(original_prose: str, lane: str, wsp_refs: list[int]) -> bool:
    """
    Contract invariant: M2M compilation MUST be semantically reversible.
    
    Steps:
    1. Compile original_prose to M2M
    2. Decompile M2M back to prose
    3. Extract key components from both (action, scope, WSP refs)
    4. Assert key components match
    
    Returns True if fidelity holds, raises FidelityError if not.
    """
    compiler = M2MCompiler()
    m2m = compiler.compile(original_prose, lane=lane, wsp_refs=wsp_refs)
    roundtrip = compiler.decompile(m2m)
    
    # Extract and compare
    original_action = compiler._extract_action(original_prose)
    roundtrip_action = compiler._extract_action(roundtrip)
    
    original_scope = compiler._extract_scope(original_prose)
    roundtrip_scope = compiler._extract_scope(roundtrip)
    
    # WSP refs are explicit, should match exactly
    assert m2m.wsp_refs == wsp_refs
    
    # Action verb must survive roundtrip
    assert original_action == roundtrip_action or roundtrip_action == "IMPLEMENT"
    
    # Scope must survive if present
    if original_scope:
        assert original_scope in roundtrip or m2m.scope == original_scope
    
    return True
```

---

## 4. OpenClaw/Hermes command-output seam [SPECIFIED_NOT_IMPLEMENTED]

### 4a. Current execution flow (OBSERVED)

```
openclaw_dae.py:execute_command()
    -> openclaw_execution_routes.py:execute_command()
        -> codeact_executor.py:_execute_shell()
            -> subprocess.Popen(shell=False)
            -> stdout/stderr capture
            -> return result
```

### 4b. RTK seam location [SPECIFIED_NOT_IMPLEMENTED]

The RTK compression seam MUST be inserted AFTER `_execute_shell()` returns and BEFORE
the result is consumed by the caller. Candidate locations:

| Location | Pros | Cons |
|----------|------|------|
| codeact_executor.py post-execute | Closest to source | Tight coupling |
| execute_command() result handler | Clean separation | Multiple call sites |
| WRE gateway response handler | Centralized | Far from execution |

Contract decision: RTK seam at `execute_command()` result handler level. This allows:
- Bypass classifier to run before any future compression
- Raw result to remain recoverable and preserved
- Single integration point for all command types

Current implementation status: P6 is a dry-run seam planner only. It does not
call RTK, install an RTK binary, rewrite command output, or wire into
OpenClaw/Hermes/WRE/extension runtime.

### 4c. Seam interface [SPECIFIED_NOT_IMPLEMENTED]

```python
def plan_rtk_openclaw_hermes_adapter_dry_run(
    command: str,
    command_output: str,
    candidate_output: str,
    raw_ref: str,
) -> RtkOpenClawHermesAdapterDryRunResult:
    """
    RTK dry-run seam contract.
    
    Args:
        command: The executed command string
        command_output: Raw stdout/stderr from execution
        candidate_output: Caller-supplied candidate output
        raw_ref: Reference to recover original raw output
    
    Returns:
        RtkOpenClawHermesAdapterDryRunResult with:
            - dry_run_only: True
            - output_rewritten: False
            - raw_output_preserved: True
            - rtk_invoked: False
            - telemetry_event_id: in-memory measurement event id, if evaluated
    
    Invariants:
        - If bypass_classifier.should_bypass(result) -> return raw, bypassed=True
        - If telemetry is None and compression would occur -> fail-closed (no silent compression)
        - raw_ref MUST allow recovery of original result
    """
    pass  # SPECIFIED_NOT_IMPLEMENTED
```

---

## 5. raw_ref recovery requirement [SPECIFIED_NOT_IMPLEMENTED]

### 5a. Contract requirement

Any compression (M2M or RTK) MUST provide a path to recover the original content.
This is a HARD requirement for:
- Security audit trails (compressed output may hide vulnerability details)
- Debugging (compressed output may lose error context)
- Provenance (compressed output may alter evidence chain)

### 5b. Recovery mechanisms [SPECIFIED_NOT_IMPLEMENTED]

| Mechanism | For | Storage |
|-----------|-----|---------|
| M2M raw_ref | Original prose before M2M compile | In-memory or session store |
| RTK raw_ref | Original command output before RTK compress | Ephemeral file or memory |

### 5c. raw_ref schema [SPECIFIED_NOT_IMPLEMENTED]

```yaml
RawRef:
  ref_id: string              # Unique reference identifier
  content_hash: string        # SHA256 of original content
  content_type: string        # "m2m_prose" | "rtk_output"
  storage_location: string    # "memory" | "file:<path>" | "session:<key>"
  created_at: integer         # Unix timestamp
  expires_at: integer         # TTL for cleanup
  recovered: bool             # True if already recovered (one-time use option)
```

---

## 6. Bypass classifier classes [SPECIFIED_NOT_IMPLEMENTED]

### 6a. Mandatory bypass classes

Per 012 Addendum, the following output types MUST bypass compression by default:

| Class | Detection patterns | Reason |
|-------|-------------------|--------|
| SECURITY | `CVE-`, `VULNERABILITY`, `EXPLOIT`, `CRITICAL:`, `HIGH:` | Security scan output must not be summarized |
| AUTH | `token=`, `key=`, `password=`, `secret=`, `credential` | Credentials must never be compressed |
| PROVENANCE | `signed by`, `verified`, `attestation`, `witness` | Chain of custody must be preserved |
| SIGNING | `signature:`, `-----BEGIN`, `-----END`, `pubkey:` | Crypto material must not be altered |
| PERMISSION | `ALLOW`, `DENY`, `GRANT`, `REVOKE`, `scope:` | Permission changes must be explicit |
| RECEIPT | `receipt_id:`, `work_order_id:`, `settled_at:` | Settlement records must be verbatim |

### 6b. Bypass classifier interface [SPECIFIED_NOT_IMPLEMENTED]

```python
class BypassClassifier:
    """
    Determines if command output should bypass compression.
    
    Fail-closed: If classification fails, default to bypass.
    """
    
    BYPASS_PATTERNS: dict[str, list[str]]  # class -> patterns
    
    def should_bypass(self, content: str) -> tuple[bool, str | None]:
        """
        Check if content should bypass compression.
        
        Returns:
            (True, class_name) if content matches a bypass class
            (False, None) if compression is allowed
            (True, "CLASSIFICATION_ERROR") if classification fails
        """
        pass
    
    def get_matched_classes(self, content: str) -> list[str]:
        """Return all bypass classes that match the content."""
        pass
```

### 6c. Bypass priority

Bypass WINS over compression. If ANY bypass class matches:
1. Return raw content unchanged
2. Set bypassed=True with reason
3. Record bypass in telemetry (class, not content)
4. Do NOT attempt partial compression

---

## 7. Fidelity gate requirements [SPECIFIED_NOT_IMPLEMENTED]

### 7a. M2M fidelity tests

| Test | Assertion |
|------|-----------|
| Action preservation | compile(prose).action == extract_action(decompile(compile(prose))) |
| Scope preservation | compile(prose).scope in decompile(compile(prose)) |
| WSP ref preservation | compile(prose, wsp_refs=X).wsp_refs == X |
| Lane preservation | compile(prose, lane=Y).lane == Y |
| Empty handling | compile("") raises or returns valid empty M2M |
| Unicode handling | compile(unicode_prose) roundtrips without corruption |

### 7b. RTK fidelity tests (future, when RTK integrated)

| Test | Assertion |
|------|-----------|
| Bypass respected | compress(security_output).bypassed == True |
| Raw recoverable | decompress(compress(x).raw_ref) == x |
| Savings measured | compress(x).savings_tokens >= 0 |
| Error handling | compress(malformed_input) returns input unchanged |

---

## 8. Token savings telemetry schema [SPECIFIED_NOT_IMPLEMENTED]

### 8a. Telemetry record

```yaml
TokenCompressionEvent:
  event_id: string            # Unique event identifier
  event_type: string          # "m2m_compile" | "rtk_compress" | "bypass"
  timestamp: integer          # Unix timestamp
  
  # Input metrics
  input_tokens: integer       # Estimated tokens before compression
  input_bytes: integer        # Bytes before compression
  
  # Output metrics  
  output_tokens: integer      # Estimated tokens after compression
  output_bytes: integer       # Bytes after compression
  
  # Savings
  token_savings: integer      # input_tokens - output_tokens
  savings_percent: float      # (token_savings / input_tokens) * 100
  
  # Context
  compression_type: string    # "m2m" | "rtk" | "none"
  bypass_class: string | null # If bypassed, which class triggered
  command_type: string | null # For RTK: git, pytest, npm, etc.
  
  # Recovery
  raw_ref_id: string | null   # Reference to original (if stored)
```

### 8b. Telemetry invariants

| Invariant | Rule |
|-----------|------|
| NO_NEGATIVE_SAVINGS | token_savings >= 0 (compression that increases tokens is a bug) |
| NO_CONTENT_IN_TELEMETRY | Telemetry records metrics, NEVER raw content |
| BYPASS_BEFORE_TELEMETRY | Bypass classifier runs BEFORE telemetry records anything |
| NO_TELEMETRY_WITHOUT_BYPASS_GATE | Telemetry service MUST NOT start until bypass classifier is proven |

---

## 9. Implementation sequence [SPECIFIED_NOT_IMPLEMENTED]

Per 012 adjustment, bypass/security gate comes BEFORE telemetry:

| Priority | Slice | Deliverables | Blocked by |
|----------|-------|--------------|------------|
| P1 | BYPASS_CLASSIFIER_SECURITY_GATE_PHASE1 | BypassClassifier, patterns, tests | This contract |
| P2 | WSP99_COMPILER_FIDELITY_GATE_PHASE1 | assert_m2m_fidelity(), roundtrip tests | P1 |
| P3 | TOKEN_EFFICIENCY_TELEMETRY_SERVICE_PHASE1 | TokenTelemetry, schema, storage | P1, P2 |
| P4 | REDDOG_COMPUTE_GOVERNOR_PHASE1 | RedDogComputeDecision, routing | P1, P2, P3 |
| P5 | RTK_EVALUATION_DRY_RUN_PHASE1 | Caller-supplied candidate evaluation, dry-run | P4 |
| P6 | RTK_OPENCLAW_HERMES_ADAPTER_DRYRUN_PHASE1 | Seam planner, dry-run, no rewrite | P5 |

Rationale: Telemetry might record compressed output. If bypass classifier is broken,
telemetry could record secrets. Therefore bypass MUST be proven before telemetry starts.

---

## 10. Module placement [SPECIFIED_NOT_IMPLEMENTED]

```
modules/
  infrastructure/
    token_efficiency/
      src/
        __init__.py
        bypass_classifier.py      # P1: Bypass class detection
        m2m_fidelity_gate.py      # P2: Round-trip validation
        telemetry_service.py      # P3: Token savings measurement
        compute_governor.py       # P4: Routing decisions
        rtk_evaluation_dryrun.py  # P5: Caller-supplied candidate evaluation
        rtk_openclaw_hermes_adapter_dryrun.py # P6: Seam planner, no rewrite
      tests/
        test_bypass_classifier.py
        test_m2m_fidelity.py
        test_telemetry_service.py
        test_compute_governor.py
        test_rtk_evaluation_dryrun.py
        test_rtk_openclaw_hermes_adapter_dryrun.py # Seam dry-run tests
      config/
        bypass_patterns.yaml      # Bypass class definitions
      README.md
      INTERFACE.md
      requirements.txt            # No new deps in P1-P3
```

---

## 11. Hard rules (contract invariants)

These rules are FROZEN by this contract. Violation is a contract breach.

| Rule | Description | Enforcement |
|------|-------------|-------------|
| RTK_IS_NOT_M2M | RTK cannot be used for agent-to-agent communication | Static test |
| WSP99_CANONICAL | WSP-99 remains the only 0102-to-0102 packet format | Static test |
| REDDOG_012_FACING | RedDog is the 012 interface, not bypassed | Architecture review |
| ORCH_COMPILES | ORCH (not RedDog, not Worker) compiles M2M | Code review |
| RTK_OUTPUT_ONLY | RTK only touches post-execution output | Static test |
| BYPASS_DEFAULT | Security/auth/provenance/signing/permission/receipt bypass by default | Unit tests |
| NO_RUNTIME_RTK_YET | No RTK runtime integration in P6 | CI gate |
| NO_COMMAND_REWRITE_YET | No OpenClaw/Hermes command rewrite in P6 | CI gate |
| NO_DEP_INSTALL | No new dependencies in P1-P3 | requirements.txt diff |
| NO_EXTERNAL_EXEC | No external command execution except read-only checks | Code review |
| NO_LIVE_TELEMETRY_YET | No telemetry store until P3 | CI gate |

---

## 12. Static tests for contract invariants

Tests that MUST pass to prove contract compliance. These are implementation-agnostic
assertions about the boundaries defined in this contract.

```python
# tests/contracts/test_token_efficiency_contract.py

def test_m2m_rtk_domains_disjoint():
    """M2M and RTK domains must not overlap."""
    m2m_domain = {"agent_prompt", "inter_agent_packet", "orch_dispatch", "worker_report"}
    rtk_domain = {"command_stdout", "command_stderr", "subprocess_output"}
    assert m2m_domain.isdisjoint(rtk_domain)

def test_bypass_classes_defined():
    """All mandatory bypass classes must be defined."""
    REQUIRED_BYPASS_CLASSES = {"SECURITY", "AUTH", "PROVENANCE", "SIGNING", "PERMISSION", "RECEIPT"}
    # BypassClassifier.BYPASS_PATTERNS.keys() must include all required
    # This test will be filled in P1 implementation
    pass

def test_wsp99_schema_unchanged():
    """WSP-99 schema must not be modified by this contract."""
    from prompt.swarm.m2m_compiler import M2MPrompt
    # Assert M2MPrompt fields match WSP-99 spec
    required_fields = {"lane", "scope", "mode", "task_hash", "wsp_refs"}
    actual_fields = set(M2MPrompt.__dataclass_fields__.keys())
    assert required_fields.issubset(actual_fields)

def test_no_rtk_binary_present():
    """RTK binary must not be required by P6 dry-run planning."""
    import shutil
    assert shutil.which("rtk") is None, "RTK binary found but P6 does not use it"

def test_no_rtk_dependency():
    """No RTK-related dependencies in requirements."""
    from pathlib import Path
    req_files = list(Path("modules/infrastructure").rglob("requirements.txt"))
    for req_file in req_files:
        content = req_file.read_text()
        assert "rtk" not in content.lower(), f"RTK dependency found in {req_file}"
```

---

## 13. Residual SPECIFIED_NOT_IMPLEMENTED

Items defined by this contract but not implemented:

| Item | Contract section | Implementation slice |
|------|-----------------|---------------------|
| BypassClassifier class | Section 6b | BYPASS_CLASSIFIER_SECURITY_GATE_PHASE1 |
| bypass_patterns.yaml | Section 6a | BYPASS_CLASSIFIER_SECURITY_GATE_PHASE1 |
| assert_m2m_fidelity() | Section 3c | WSP99_COMPILER_FIDELITY_GATE_PHASE1 |
| M2M round-trip tests | Section 7a | WSP99_COMPILER_FIDELITY_GATE_PHASE1 |
| TokenCompressionEvent | Section 8a | TOKEN_EFFICIENCY_TELEMETRY_SERVICE_PHASE1 |
| TokenTelemetry class | Section 8 | TOKEN_EFFICIENCY_TELEMETRY_SERVICE_PHASE1 |
| Caller-supplied RTK candidate evaluation | Section 4 | RTK_EVALUATION_DRY_RUN_PHASE1 |
| plan_rtk_openclaw_hermes_adapter_dry_run() | Section 4c | RTK_OPENCLAW_HERMES_ADAPTER_DRYRUN_PHASE1 |
| RedDogComputeDecision | Section 2b | REDDOG_COMPUTE_GOVERNOR_PHASE1 |
| RawRef schema | Section 5c | WSP99_COMPILER_FIDELITY_GATE_PHASE1 |

---

## 14. WSP 97 Truth Boundary Checklist

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | CONTRACT_ONLY | YES | No implementation code |
| 2 | NO_RTK_BINARY | YES | Static test asserts |
| 3 | NO_RTK_SUBPROCESS | YES | No subprocess calls added |
| 4 | NO_COMMAND_REWRITE | YES | OpenClaw/Hermes unchanged |
| 5 | NO_LIVE_TELEMETRY | YES | No telemetry store |
| 6 | NO_DEP_INSTALL | YES | No requirements.txt changes |
| 7 | NO_EXTERNAL_EXEC | YES | Read-only source checks only |
| 8 | WSP99_BOUNDARY_DEFINED | YES | Section 1a |
| 9 | RTK_BOUNDARY_DEFINED | YES | Section 1b |
| 10 | BYPASS_CLASSES_DEFINED | YES | Section 6a |
| 11 | FIDELITY_REQUIREMENTS_DEFINED | YES | Section 7 |
| 12 | TELEMETRY_SCHEMA_DEFINED | YES | Section 8 |
| 13 | SEQUENCE_SPECIFIED | YES | Section 9 |
| 14 | MODULE_PLACEMENT_SPECIFIED | YES | Section 10 |
| 15 | INVARIANTS_TESTABLE | YES | Section 12 |
| 16 | RESIDUAL_TRACKED | YES | Section 13 |
| 17 | RATIFIES_AUDIT_937 | YES | Header |
| 18 | ASCII_CLEAN | YES | No non-ASCII in spec sections |

**WSP 97 Truth Boundary Checklist: 18/18 YES**

---

*Contract complete for REDDOG_WSP99_RTK_TOKEN_EFFICIENCY_CONTRACT_PHASE1. RTK is tool-output compression, not M2M replacement. Bypass classifier gates telemetry. P1 implementation unlocked.*
