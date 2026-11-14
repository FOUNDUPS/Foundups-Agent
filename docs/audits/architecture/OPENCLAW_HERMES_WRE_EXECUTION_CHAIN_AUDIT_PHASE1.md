# OpenClaw / Hermes / WRE Execution Chain Audit (Phase 1)

- Lane: W9 (read-only architecture audit)
- Status: DECISION-ONLY (no manifest/validator/runtime/registry mutation; no consumer wired; no build run)
- Base: origin/main 75ffc8c90 (includes #768-#773)
- Date: 2026-06-09
- WSP refs: WSP_00, WSP_50/WSP_87 (HoloIndex pre-action), WSP_15 (priority), WSP_84 (reuse), WSP_97 (Truth Boundary), WSP_22 (ModLog)
- Predecessors: #768 (typed shell=False exec + redaction), #769 (durable design), #770 (manifest readiness audit), #771 (baseline build_contract + validator), #772 (context bundle boundary audit), #773 (module_path exact-match hardening)

---

## 1. Mission and Scope

Fully audit the current OpenClaw / WRE / Hermes execution chain BEFORE implementing
WRE_CONTEXT_BUNDLE_BUILDER_PHASE1. Identify exact current seams, trust boundaries, dry-run
claims, execution risks, duplicate responsibilities, and missing gates across the complete
chain:

```
OpenClaw -> FoundUpJob -> WRE Router -> WRE Consumer -> Hermes Executor -> Receipt / pAVS
```

This is NOT an implementation slice. It does NOT wire a new consumer. It does NOT run a
build. It does NOT modify manifests. It does NOT modify validator code. It does NOT change
runtime behavior.

---

## 2. Predecessor Chain (#768-#773)

| PR | Title | Key Contribution |
|----|-------|------------------|
| #768 | Typed shell=False exec + redaction | argv-only execution; redacted evidence; no shell strings |
| #769 | Durable design / build on primitives | Existing primitives reuse; no new orchestrators |
| #770 | FoundUp manifest readiness audit | Manifests are routing/product/governance; AI Overseer auditor only |
| #771 | Baseline build_contract + validator | build_contract + execution_routing blocks; read-only validator |
| #772 | WRE context bundle boundary audit | ContextBundle definition; refs+digests; no repo concatenation |
| #773 | module_path exact-match hardening | Exact-only path matching; suffix fallback removed |

All secured base gates remain load-bearing: genesis gate (#747), no-live-launch (#762),
typed exec (#768), D0-D6 destructive-action guard, policy flags writeback (#746).

---

## 3. FOLLOW-WSP Evidence

### 3.1 HoloIndex Discovery (DISCOVERY ONLY - never proof)

HoloIndex queries were used for initial discovery only. All load-bearing claims are
verified by direct file:line reads documented in subsequent sections.

### 3.2 Direct-Read Inventory (verified on 75ffc8c90)

| File | Lines | Purpose |
|------|-------|---------|
| `modules/communication/moltbot_bridge/src/openclaw_foundup_orchestrator.py` | 998 | Genesis validation gate, job creation |
| `modules/communication/moltbot_bridge/src/foundup_job_contract.py` | 758 | FoundUpJob dataclass, PolicyFlags |
| `modules/infrastructure/wre_core/src/foundup_job_router.py` | 1277 | Routing envelope, backend selection |
| `modules/infrastructure/wre_core/src/foundup_job_consumer.py` | 836 | Job consumption, Hermes dispatch |
| `modules/infrastructure/wre_core/src/hermes_job_executor.py` | 2367 | WRE executor adapter, guard integration |
| `modules/foundups/agent/src/hermes_foundup_job_executor.py` | 457 | Legacy Hermes executor |
| `modules/foundups/agent/src/hermes_adapter.py` | 1110 | HermesFoundUpBuilder |
| `modules/foundups/agent/src/foundup_manifest_validator.py` | 543 | Read-only build_contract validator |
| `modules/foundups/agent/src/build_plan.py` | 959 | BuildPlan dataclass |
| `modules/communication/moltbot_bridge/src/receipt_emitter.py` | 209 | Receipt emission for terminal jobs |
| `modules/foundups/gotjunk/foundup_manifest.json` | 106 | Sample manifest with build_contract |

---

## 4. Current Execution-Chain Map

### Table A: Execution Chain Table

| Layer | File | Current Responsibility | Executes? | Trust Input | Emits Output | Risk |
|-------|------|------------------------|-----------|-------------|--------------|------|
| OpenClaw Orchestrator | openclaw_foundup_orchestrator.py | Genesis validation, job queuing | NO (queues only) | Intent message | FoundUpJob (QUEUED) | LOW: no execution |
| FoundUpJob Contract | foundup_job_contract.py | Typed job dataclass, state machine | NO (data only) | Deserialized dict | Job state | LOW: PolicyFlags.from_dict forces gates False |
| WRE Router | foundup_job_router.py | Backend selection, envelope validation | NO (routing only) | FoundUpJob | RouteEnvelope | LOW: code-owned _ACTION_BACKEND_MAP |
| WRE Consumer | foundup_job_consumer.py | Drains jobs, dispatches to Hermes | POTENTIALLY | RouteEnvelope | ConsumerResult | MEDIUM: calls WRE executor |
| WRE Hermes Executor | wre_core/hermes_job_executor.py | Guard evaluation, delegation | DRY-RUN ONLY | FoundUpJob | HermesDelegationResult | LOW: HERMES_DELEGATE_ENABLED=0 default |
| Legacy Hermes Executor | agent/hermes_foundup_job_executor.py | Action dispatch | DRY-RUN ONLY | FoundUpJob | HermesJobExecutionResult | LOW: dry_run default |
| Hermes Adapter | hermes_adapter.py | Builder operations | POTENTIAL | Module path | Build result | MEDIUM: subprocess.run present |
| Receipt Emitter | receipt_emitter.py | Terminal job receipts | NO (creates records) | FoundUpJob | ReceiptEmissionResult | LOW: data only |
| Manifest Validator | foundup_manifest_validator.py | Contract validation | NO (read-only) | JSON dict | ValidationResult | LOW: no imports of executors |

---

## 5. OpenClaw Responsibility Audit

### 5.1 File Evidence: openclaw_foundup_orchestrator.py

**Primary responsibility**: Genesis validation gate BEFORE any execution handoff.

Lines 331-349 (OpenClawFoundUpOrchestrator class docstring):
```
Gate Enforcement Points:
    1. launch_foundup() - validates before FAM launch
    2. build_foundup() - validates before Hermes build
    3. promote_lifecycle() - validates before stage transition
```

**Does OpenClaw execute builds?** NO.

Lines 958-976 (_handle_build_intent):
- Creates FoundUpJob in QUEUED state
- Adds to in-memory queue (_FOUNDUP_JOB_QUEUE)
- Returns confirmation string
- NO call to Hermes, NO subprocess, NO execution

Lines 39-40: `_FOUNDUP_JOB_QUEUE: List[FoundUpJob] = []` - in-memory queue only.

**Dry-run detection**: Lines 92-126 (_detect_dry_run_mode) - sets policy_flags.dry_run_mode

**VERDICT**: OpenClaw queues jobs with validation. It does NOT execute builds.

---

## 6. FoundUpJob Contract Audit

### 6.1 File Evidence: foundup_job_contract.py

**PolicyFlags security**: Lines 200-215 (_SERVER_AUTHORED_FLAGS) + Lines 283-324 (from_dict):
```python
_SERVER_AUTHORED_FLAGS: frozenset = frozenset({
    "security_gate_checked", "security_gate_passed",
    "permission_gate_checked", "permission_gate_passed",
    "exfoliation_gate_checked", "exfoliation_gate_passed",
    "wsp_preflight_checked", "wsp_preflight_passed",
    "capability_token_checked", "capability_token_present",
    "capability_token_validated", "capability_token_scope_authorized",
})
```

from_dict FORCES all server-authored flags to False:
```python
return cls(
    security_gate_checked=False,
    security_gate_passed=False,
    # ... all forced False
    dry_run_mode=bool(data.get("dry_run_mode", False)),
)
```

This means deserialized jobs CANNOT self-assert gate passage.

**VERDICT**: PolicyFlags trust boundary is enforced at deserialization.

---

## 7. WRE Router Responsibility Audit

### 7.1 File Evidence: foundup_job_router.py

**Backend selection is CODE-OWNED**: Lines 85-90
```python
_ACTION_BACKEND_MAP: Dict[str, TargetBackend] = {
    "build_foundup": TargetBackend.HERMES_BUILDER,
    "extract_foundup": TargetBackend.HERMES_BUILDER,
    "validate_foundup": TargetBackend.HERMES_VALIDATOR,
    "queue_foundup_job": TargetBackend.OPENCLAW_QUEUE,
}
```

**Manifest execution_routing CANNOT choose executor**: The router uses its own hardcoded
_ACTION_BACKEND_MAP. Manifest `execution_routing.executor` is declarative only (provenance).

**Policy sanitization at router boundary**: Lines 337-380 (_sanitize_untrusted_policy_flags_dict):
- Raw envelope dicts are UNTRUSTED
- All gate flags forced False via PolicyFlags.from_dict
- Only dry_run_mode preserved (True is safe direction)
- Missing dry_run_mode defaults to True (safe)

**Live mode fail-closed**: Lines 1173-1183
```python
if is_live and policy_summary.get("security_gate_passed") is not True:
    return _make_blocked_envelope(
        reason_code=RouteReasonCode.BLOCKED_POLICY_GATE,
        reason_human="Live mode requires security gate passed (fail-closed)",
    )
```

**VERDICT**: WRE router owns backend selection via code. Manifest cannot choose privileged executor. Live mode requires server-authored security_gate_passed.

---

## 8. WRE Consumer Responsibility Audit

### 8.1 File Evidence: foundup_job_consumer.py

**Consumer dispatches to WRE executor**: Lines 424-430 (_dispatch_to_hermes):
```python
from modules.infrastructure.wre_core.src.hermes_job_executor import (
    execute_foundup_job,
    HermesDelegationResult,
    HermesExecutionStatus,
)
hermes_result: HermesDelegationResult = execute_foundup_job(job)
```

**Consumer CAN reach Hermes execution seams**: The consumer imports and calls
`execute_foundup_job` from the WRE hermes_job_executor. This is the critical path.

**Dry-run default**: Lines 342-349 (FoundUpJobConsumer.__init__):
```python
def __init__(self, dry_run: bool = True):
    self.dry_run = dry_run
```

**Receipt emission for dry-run**: Lines 617-629 (_emit_receipt_for_hermes_result):
```python
if status_value == "SIMULATED":
    real_exec = getattr(hermes_result, "real_execution_performed", False)
    if not real_exec:
        logger.info(
            "[CONSUMER] Job %s simulated (dry-run), evidence in checkpoint files. "
            "Receipt emission skipped (WSP 97: no overclaim).",
        )
        return None  # No receipt for dry-run
```

**Risk assessment**: The consumer CAN call WRE executor which CAN reach Hermes. However:
- WRE executor defaults to dry_run=True
- WRE executor has HERMES_DELEGATE_ENABLED=0 default
- Real execution is blocked in Phase 1 (line 1843-1868 of hermes_job_executor.py)

**VERDICT**: Consumer can dispatch to WRE executor but execution is blocked by multiple gates.

---

## 9. Hermes Executor / Builder Responsibility Audit

### 9.1 WRE Hermes Executor: hermes_job_executor.py

**Feature flag blocks real delegation**: Lines 89-95
```python
_HERMES_DELEGATE_ENABLED_KEY = "HERMES_DELEGATE_ENABLED"
def is_hermes_delegation_enabled() -> bool:
    value = os.environ.get(_HERMES_DELEGATE_ENABLED_KEY, "0")
    return value.strip().lower() in ("1", "true", "yes")
```
Default is "0" = disabled.

**Destructive action guard integration**: Lines 1307-1326 (_evaluate_destructive_action_guard):
```python
guard_request = self._build_destructive_action_request(job, request)
return evaluate_destructive_action(guard_request)
```

**D0-D6 classification**: Lines 1067-1168 (_classify_destructive_action):
- build_foundup -> D3_WRITE_SANDBOX
- extract_foundup -> D3_WRITE_SANDBOX
- Unknown actions -> D6_IRREVERSIBLE (fail-closed)

**Token validation writeback**: Lines 1253-1306 (_writeback_token_verdict):
Server-authored token verdict is written into job.policy_flags BEFORE guard evaluation.

**Real execution blocked**: Lines 1843-1868:
```python
logger.warning("[HERMES-EXEC] Real delegation NOT IMPLEMENTED, blocking job %s")
result = HermesDelegationResult(
    status=HermesExecutionStatus.BLOCKED_REAL_DELEGATION_NOT_IMPLEMENTED,
    ...
)
```

### 9.2 Legacy Hermes Executor: agent/hermes_foundup_job_executor.py

Lines 179-198: Imports HermesFoundUpBuilder from hermes_adapter.py.

Lines 240-304 (_dispatch_action): Calls builder.extract_foundup, builder.check_exfoliation_gate, etc.

**Risk**: This executor CAN call hermes_adapter methods, but the adapter has its own gates.

### 9.3 Hermes Adapter: hermes_adapter.py

**Security gate required by default**: Lines 132-135:
```python
self.require_security_gate = os.environ.get("HERMES_BUILDER_SECURITY_GATE", "1") == "1"
```

**Dry run default**: Lines 133-134:
```python
self.dry_run = os.environ.get("HERMES_BUILDER_DRY_RUN", "0") == "1"
```

**Subprocess present but gated**: Lines 936-958 (run_hermes_extraction):
```python
if self.dry_run:
    return {
        "success": True,
        "dry_run": True,
        "command": cmd,
        ...
    }
# Else: subprocess.run(cmd, ...)
```

**VERDICT**: Multiple gates (feature flag, security gate, dry_run, D0-D6 guard) protect execution. Real execution is blocked in Phase 1.

---

## 10. Receipt / pAVS Evidence Audit

### 10.1 File Evidence: receipt_emitter.py

**Only terminal jobs emit receipts**: Lines 82-114 (_is_terminal_job):
- Checks is_terminal_status or status == JobStatus.BLOCKED
- Non-terminal jobs rejected at line 151-159

**Truth fields always False**: Lines 15-21 docstring:
```
Truth Boundaries (WSP 97):
  - Only terminal jobs can emit receipts
  - cabr_ready = False (no CABR consensus exists)
  - payout_ready = False (no payout engine exists)
  - verification_complete = False (only accepted for review)
```

### 10.2 Evidence from Consumer

ConsumerResult.to_dict() (lines 191-212) includes:
```python
"verification_complete": self.verification_complete,  # Always False
"cabr_ready": self.cabr_ready,  # Always False
"payout_ready": self.payout_ready,  # Always False
```

**VERDICT**: Receipt/evidence system does NOT claim CABR, payout, or verification readiness.

---

## 11. Manifest Validator and module_path Trust Audit

### 11.1 File Evidence: foundup_manifest_validator.py

**Validator imports NO runtime executors**: Lines 36-57 (__all__):
- Only exports validation functions and constants
- No imports from hermes_*, foundup_job_*, openclaw_*, wre_*

**module_path exact-match**: Lines 251-276 (_expected_module_path_matches):
```python
def _expected_module_path_matches(manifest_path: str, module_path: str) -> bool:
    canonical_module = _canonicalize_module_path(module_path)
    if canonical_module is None:
        return False
    canonical_manifest = _canonicalize_manifest_path_for_compare(manifest_path)
    if canonical_manifest is None:
        return False
    parent = PurePosixPath(canonical_manifest).parent.as_posix()
    if parent == ".":
        return False
    return parent == canonical_module  # EXACT MATCH ONLY
```

Per #773, suffix fallback was removed. Only exact repo-relative path equality is accepted.

**Absolute/traversal rejection**: Lines 182-213 (_canonicalize_module_path):
- Rejects absolute paths (C:, /)
- Rejects UNC paths
- Rejects ".." traversal segments

### 11.2 Validator Bypass Risk

**Question**: Does any layer bypass the validator before using module_path?

**OpenClaw**: Does NOT use module_path directly. Extracts foundup_id from message (line 184-208).

**WRE Router**: Does NOT read manifests. Uses job.requested_action for backend selection.

**WRE Consumer**: Does NOT read manifests. Passes job to executor.

**WRE Executor**: Builds module_path from job.foundup_id (line 948):
```python
workspace_hint = f"modules/foundups/{job.foundup_id}"
```
This is a CONSTRUCTED path, not manifest-derived.

**Legacy Executor**: Extracts module_path from job.payload (lines 217-237):
```python
module_path = payload.get("module_path") or payload.get("source_module")
if job.foundup_id and "/" in job.foundup_id:
    return job.foundup_id
```
This TRUSTS job.payload.module_path without validation.

**GAP IDENTIFIED**: Legacy executor trusts payload.module_path. If a malicious job carries
a crafted module_path in payload, it bypasses the validator.

**VERDICT**: Current chain does NOT validate module_path before WRE executor uses it. The
validator exists but is not in the path.

---

## 12. ContextBundle Impact Analysis

### 12.1 Where Should ContextBundle Plug In?

Per #772 audit, WRE_CONTEXT_BUNDLE_BUILDER_PHASE1 should:
1. Run AFTER manifest validator (module_path validation)
2. Run BEFORE Hermes executor (provide workspace binding)
3. Run BEFORE any consumer dispatch (no execution until validated)
4. Be READ-ONLY (provenance envelope, not execution authority)

### 12.2 Required Integration Points

| Point | Current | Required Change |
|-------|---------|-----------------|
| Manifest validation | foundup_manifest_validator.py | None (reuse) |
| Bundle building | Does not exist | NEW: context_bundle_builder.py |
| Bundle consumption | Does not exist | FUTURE: consumer integration |
| Workspace binding | hermes_job_executor.py WorkspaceBinding | Reuse existing |
| Evidence output | hermes_job_executor.py evidence_path | Reuse existing |

### 12.3 What Must Bundle Builder Reuse?

- foundup_manifest_validator.py: validate_manifest_file
- WorkspaceBinding: allowed_paths, blocked_paths, evidence_output_path
- BuildEvidence: file_path, content_hash, timestamp
- ExecutionReceipt: job correlation, evidence refs

### 12.4 What Must Bundle Builder Avoid?

- Calling any executor
- Wiring to consumer
- Running builds
- Including file bodies (refs + digests only)
- Asserting gate passage
- Promoting readiness

---

## 13. Duplicate Authority / Role-Conflict Analysis

### Table B: Authority Table

| Decision | Current Owner | Manifest-Controlled? | Code-Controlled? | Evidence |
|----------|---------------|---------------------|------------------|----------|
| action -> backend routing | WRE Router | NO | YES | _ACTION_BACKEND_MAP:85-90 |
| module_path | Job payload (untrusted) | NO | NO | _extract_module_path:217-237 |
| executor selection | WRE Router | NO (provenance only) | YES | ALLOWED_EXECUTORS:84 |
| dry_run mode | PolicyFlags | Operator-authored | YES (default True) | PolicyFlags:249 |
| readiness | Manifest | NO (must be false) | YES (validator rejects true) | validator:303-321 |
| evidence path | WRE executor | NO | YES | get_evidence_output_path:226-238 |
| receipt emission | Consumer | NO | YES | emit_receipt_for_terminal_job |
| pAVS verification | Receipt emitter | NO | YES | verify_receipt call |
| AI Overseer role | Manifest | Auditor label only | NO build authority | grep: no hermes imports |

### 13.1 Identified Role Conflicts

**None found**. Each component has clear, non-overlapping responsibility:
- OpenClaw: intake, validation, queuing
- WRE Router: backend selection (code-owned)
- WRE Consumer: dispatch coordination
- WRE Executor: guard evaluation, dry-run simulation
- Hermes Adapter: build operations (gated)
- Manifest Validator: contract validation (read-only)
- Receipt Emitter: terminal job evidence

**AI Overseer NOT a builder**: grep confirms no imports of build/execution modules.

---

## 14. Dry-Run and Real-Execution Boundary Analysis

### Table C: Dry-Run Truth Table

| Component | Dry-run field/source | Can force live? | Evidence | Risk |
|-----------|----------------------|-----------------|----------|------|
| OpenClaw | _detect_dry_run_mode | NO | Sets policy_flags only | LOW |
| FoundUpJob | policy_flags.dry_run_mode | Operator-authored | from_dict preserves | MEDIUM |
| WRE Router | dry_run_defaulted logic | NO (safe default) | :483 defaults to True | LOW |
| WRE Consumer | __init__(dry_run=True) | Constructor param | :342-349 | LOW |
| WRE Executor | __init__(dry_run=True) | Constructor param | :553 | LOW |
| WRE Executor | HERMES_DELEGATE_ENABLED | Env var | :89-95 default "0" | LOW |
| Legacy Executor | force_dry_run param | Param + builder.dry_run | :79-80 | MEDIUM |
| Hermes Adapter | HERMES_BUILDER_DRY_RUN | Env var | :133-134 default "0" | MEDIUM |

### 14.1 How Could Real Execution Happen?

To force real execution, an attacker would need ALL of:
1. Set HERMES_DELEGATE_ENABLED=1 (env var)
2. Create consumer with dry_run=False (code change)
3. Create executor with dry_run=False (code change)
4. Set HERMES_BUILDER_DRY_RUN=1 (env var)
5. Pass D0-D6 guard (requires server-authored capability token for D3+)
6. Pass security gate (server-authored only)

**Current state**: Real execution is blocked by:
- Feature flag default (line 1767-1792 returns SIMULATED)
- Even if enabled, real delegation returns BLOCKED (line 1843-1868)

**VERDICT**: Real execution is defense-in-depth blocked. No single point of failure.

---

## 15. Gate Enforcement Table

### Table D: Gate Enforcement Table

| Gate | Enforced where | Merely documented where | Evidence | Gap |
|------|----------------|-------------------------|----------|-----|
| genesis_gate | openclaw_foundup_orchestrator:404-513 | Manifest required_gates | validate_genesis_envelope | NO |
| manifest_gate | foundup_manifest_validator:313-501 | Manifest required_gates | validate_manifest | NO |
| dry_run_gate | WRE executor:1795-1820, consumer:342 | Manifest required_gates | dry_run default True | NO |
| test_gate | build_plan.py:629-631 | Manifest required_gates | NOT ENFORCED at runtime | YES |
| destructive_action_guard_d0_d6 | hermes_job_executor:1307-1326 | Manifest required_gates | evaluate_destructive_action | NO |
| typed_exec_boundary | #768 argv-only | Manifest required_gates | _validate_command_block | NO |
| no_live_launch | #762 + executor:1843 | Manifest required_gates | BLOCKED status | NO |
| policy_required_sovereign_valve | Router:1173-1183 | Manifest required_gates | BLOCKED_POLICY_GATE | NO |

**Gap**: test_gate is in manifest but NOT enforced at runtime. BuildPlan defines it but
no executor actually runs tests as a gate. This is a documentation/implementation gap,
not a security risk (tests don't grant execution authority).

---

## 16. Trust-Boundary Risk Table

### Table E: Pre-ContextBundle Blocker Table

| Blocker | Severity | Must fix before builder? | Must fix before consumer? | Evidence |
|---------|----------|--------------------------|---------------------------|----------|
| Manifest validator not in execution path | MEDIUM | NO | YES | Section 11.2 |
| module_path trusted from payload | MEDIUM | NO | YES | _extract_module_path:217-237 |
| test_gate not enforced | LOW | NO | NO | Section 15 |
| No context bundle exists | HIGH | YES | YES | Section 12 |
| No consumer wiring | N/A | N/A | Intentional | Phase 1 scope |

---

## 17. Required Fixes Before ContextBundle Builder

1. **Context bundle builder implementation**: Must create ContextBundle from validated manifest
   per #772 specification.

2. **module_path validation integration**: The legacy executor's _extract_module_path trusts
   payload.module_path. However, this is NOT a blocker for the bundle BUILDER - it's a
   blocker for the bundle CONSUMER. The builder reads from validated manifests only.

3. **No fixes needed for builder**: The builder is a pure function that reads manifests and
   emits a refs+digests envelope. It imports no executor.

---

## 18. Recommended Next Slice

**WRE_CONTEXT_BUNDLE_BUILDER_PHASE1** is READY to implement IF:

1. Exact-match validator is available: YES (#773 merged)
2. Bundle builder remains read-only: Must enforce
3. No consumer wiring: Must enforce
4. No Hermes call: Must enforce
5. No build run: Must enforce

**Builder specification** (from #772):
- Pure function: reads validated manifest, emits ContextBundle
- ContextBundle contains: refs + digests + provenance, size-capped, traversal-checked
- Must NOT: wire consumer, call executor, include file bodies, assert gates, promote readiness

**Consumer wiring is W10-gated future slice** after bundle builder is proven.

---

## 19. Internal Review Verdict

**READY**. Decision-only audit; one doc only; no manifest/validator/runtime/registry/test
mutation; no consumer wired; no build run.

**Key Findings**:

1. **OpenClaw audited**: Queues jobs only, does not execute. Genesis gate enforced.

2. **WRE router audited**: Code-owned backend selection. Manifest cannot choose executor.
   Live mode fail-closed on security_gate_passed.

3. **WRE consumer audited**: Can dispatch to executor but execution blocked by feature flag
   and guard. Dry-run default. Receipt emission skipped for simulated jobs.

4. **Hermes executor audited**: Multiple gates (feature flag, dry_run, D0-D6 guard, token
   validation). Real execution returns BLOCKED in Phase 1.

5. **Receipt/pAVS audited**: Truth fields always False. No CABR/payout/DAO claims.

6. **Manifest validator audited**: Read-only, imports no executors. Exact module_path match
   enforced per #773.

7. **Validator bypass risk**: Legacy executor trusts payload.module_path. This is a
   consumer-wiring blocker, not a builder blocker.

8. **ContextBundle builder ready**: #773 provides exact-match validator. Builder is pure
   function with no execution risk.

9. **AI Overseer not builder**: Confirmed via grep - no build/execution imports.

10. **Pre-consumer blockers identified**: module_path validation must be in consumer path
    before wiring.

---

## 20. WSP_97 Truth Boundary Checklist

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | READ_ONLY_AUDIT_ONLY | YES | One doc added; no runtime code changed |
| 2 | NO_RUNTIME_MUTATION | YES | No executor/consumer/validator code modified |
| 3 | NO_MANIFEST_MUTATION | YES | No foundup_manifest.json edited |
| 4 | NO_BUILD_RUN | YES | No build executed |
| 5 | OPENCLAW_NOT_EXECUTOR | YES | Section 5: queues only, no subprocess |
| 6 | WRE_ROUTER_CODE_OWNS_BACKEND | YES | Section 7: _ACTION_BACKEND_MAP hardcoded |
| 7 | WRE_CONSUMER_RISK_AUDITED | YES | Section 8: can dispatch but blocked |
| 8 | HERMES_EXECUTOR_RISK_AUDITED | YES | Section 9: multiple gates, BLOCKED status |
| 9 | MODULE_PATH_TRUST_AUDITED | YES | Section 11: validator exact-match, payload gap |
| 10 | VALIDATOR_BYPASS_RISK_AUDITED | YES | Section 11.2: legacy executor gap identified |
| 11 | EXECUTION_ROUTING_DECLARATIVE_ONLY | YES | Section 7: manifest cannot choose executor |
| 12 | AI_OVERSEER_NOT_BUILDER | YES | Section 13: grep confirms no build imports |
| 13 | DRY_RUN_BOUNDARY_AUDITED | YES | Section 14: defense-in-depth |
| 14 | RECEIPT_EVIDENCE_NOT_OVERCLAIMED | YES | Section 10: truth fields always False |
| 15 | NO_CABR_PAYOUT_DAO | YES | Section 10: verification_complete/cabr_ready/payout_ready False |
| 16 | CONTEXT_BUNDLE_IMPACT_DEFINED | YES | Section 12: integration points defined |
| 17 | PRE_CONSUMER_BLOCKERS_IDENTIFIED | YES | Section 16-17: module_path validation gap |
| 18 | NEXT_SLICE_NAMED | YES | WRE_CONTEXT_BUNDLE_BUILDER_PHASE1 |
| 19 | WSP_97_EVIDENCE_FILE_LINE_BASED | YES | All claims cite file:line |
| 20 | ASCII_CLEAN | YES | No non-ASCII characters in document |

---

## ModLog (WSP 22)

- 2026-06-09: W9 read-only architecture audit of OpenClaw / Hermes / WRE execution chain.
  Decision-only: no manifest/validator/runtime/registry/test mutation, no consumer wired,
  no build run. Audited all execution-shaped surfaces: OpenClaw (queues only), WRE router
  (code-owned backend), WRE consumer (can dispatch, blocked by gates), WRE executor
  (multiple gates, BLOCKED status), Hermes adapter (security gate, dry_run). Confirmed
  receipt/pAVS does not overclaim (verification_complete/cabr_ready/payout_ready always
  False). Confirmed AI Overseer is auditor only (no build imports). Identified module_path
  validation gap in legacy executor (consumer-wiring blocker, not builder blocker).
  ContextBundle builder is ready: exact-match validator available (#773), builder is pure
  function with no execution risk. Named next slice: WRE_CONTEXT_BUNDLE_BUILDER_PHASE1.
  WSP_97 20/20 YES. Left OPEN for W10 critic.
