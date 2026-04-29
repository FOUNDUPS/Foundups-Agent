# BuildPlan Execution Adapter Contract

**Status**: Architecture Specification (ADR)
**Owner**: 0102
**Slice**: `OC11_BUILD_PLAN_EXECUTION_ADAPTER_CONTRACT_PHASE1`
**WSP References**: WSP 11 (Interface Protocol), WSP 50 (Pre-Action Verification), WSP 77 (Agent Coordination), WSP 97 (Truth Boundaries)

---

## WSP 97 Truthfulness Statement

This document is an **architecture specification only**. No execution adapter is implemented.

| Claim | Status |
|-------|--------|
| BuildPlanExecutor interface defined | `SPECIFIED_NOT_IMPLEMENTED` |
| Step execution lifecycle defined | `SPECIFIED_NOT_IMPLEMENTED` |
| Gate evaluation sequence defined | `SPECIFIED_NOT_IMPLEMENTED` |
| Rollback mechanism defined | `SPECIFIED_NOT_IMPLEMENTED` |
| Real build execution | `SPECIFIED_NOT_IMPLEMENTED` |
| Hermes integration | `SPECIFIED_NOT_IMPLEMENTED` |

**Canonical Rule**: Dry-run is the default. Real execution requires explicit gates and human approval.

---

## 1. Purpose

The BuildPlan Execution Adapter translates BuildPlan steps into bounded, executable operations.

**Core Principles**:
1. Default behavior is **dry-run simulation** (no production changes)
2. Real execution requires **all gates passed** including human approval
3. Every step produces **evidence** regardless of mode
4. Failed steps trigger **rollback** to previous stable state
5. All execution paths emit **receipts** for pAVS review

**Architecture Position**:
```
FoundUpJob (OpenClaw)
    │
    ▼
BuildPlan (Generator)
    │
    ▼
BuildPlanExecutor (This Contract)
    │
    ├── DRY_RUN: Simulate, evidence, receipt
    │
    └── REAL: Execute, evidence, receipt, pAVS review
```

**Prerequisite**: BuildPlan must be generated from validated FoundUpJob.

---

## 2. Core Interfaces

### 2.1 BuildPlanExecutor

```typescript
interface BuildPlanExecutor {
  // === Lifecycle ===
  validate_plan(plan: BuildPlan): ValidationResult;
  evaluate_pre_gates(plan: BuildPlan, step: BuildStep): GateEvaluationResult;
  simulate_or_execute_step(ctx: StepExecutionContext): StepExecutionResult;
  collect_evidence(ctx: StepExecutionContext, result: StepExecutionResult): Evidence[];
  evaluate_post_gates(plan: BuildPlan, step: BuildStep, result: StepExecutionResult): GateEvaluationResult;
  emit_receipt(plan: BuildPlan, results: StepExecutionResult[]): ExecutionReceipt;
  submit_pavs_review(receipt: ExecutionReceipt): PAVSReviewResult;
  rollback_on_failure(plan: BuildPlan, failed_step: BuildStep): RollbackResult;
  close_execution(plan: BuildPlan): ExecutionCloseResult;
  
  // === Mode Control ===
  is_dry_run(): boolean;
  can_promote_to_real(plan: BuildPlan): PromotionResult;
}
```

### 2.2 StepExecutionContext

```typescript
interface StepExecutionContext {
  // === Identity ===
  plan: BuildPlan;
  step: BuildStep;
  step_index: number;
  
  // === Mode ===
  dry_run: boolean;           // True = simulate, False = execute
  
  // === Target ===
  target_files: string[];
  allowed_operations: AllowedOperation[];
  
  // === Pre-State ===
  file_snapshots: FileSnapshot[];  // State before step
  
  // === Runtime ===
  started_at: string;
  timeout_ms: number;
  worker_id: string;
}
```

### 2.3 StepExecutionResult

```typescript
interface StepExecutionResult {
  // === Identity ===
  step_id: string;
  step_name: string;
  action: BuildStepAction;
  
  // === Outcome ===
  status: StepStatus;         // SUCCEEDED | FAILED | BLOCKED | SKIPPED
  
  // === Mode ===
  dry_run: boolean;
  simulated: boolean;         // True if dry-run simulation
  
  // === Evidence ===
  planned_diff: DiffSummary;  // What would change
  actual_diff: DiffSummary | null;  // Actual changes (REAL only)
  test_results: TestResult[] | null;
  evidence_refs: string[];
  
  // === Timing ===
  started_at: string;
  completed_at: string;
  duration_ms: number;
  
  // === Error ===
  error_code: string | null;
  error_message: string | null;
}
```

### 2.4 GateEvaluationResult

```typescript
interface GateEvaluationResult {
  // === Gate Identity ===
  gate_id: string;
  gate_type: GateType;
  
  // === Outcome ===
  passed: boolean;
  reason: string;
  
  // === Evaluation ===
  checked_at: string;
  checked_by: string;         // "system" | worker_id | human_reviewer_id
  
  // === Blocking ===
  blocks_execution: boolean;  // If true and failed, step cannot proceed
  requires_human: boolean;    // If true, human must review before proceed
}
```

### 2.5 RollbackPlan

```typescript
interface RollbackPlan {
  // === Identity ===
  plan_id: string;
  failed_step_id: string;
  
  // === Scope ===
  rollback_to_step_id: string;  // Step to restore state from
  files_to_restore: FileSnapshot[];
  
  // === Operations ===
  rollback_commands: string[];
  
  // === State ===
  rollback_status: "pending" | "executing" | "completed" | "failed";
  rollback_evidence: string[];
}
```

### 2.6 ExecutionReceipt

```typescript
interface ExecutionReceipt {
  // === Identity ===
  receipt_id: string;
  plan_id: string;
  source_job_id: string;
  
  // === Correlation ===
  foundup_id: string;
  tenant_id: string;
  
  // === Execution Summary ===
  mode: "dry_run" | "real";
  total_steps: number;
  steps_succeeded: number;
  steps_failed: number;
  steps_skipped: number;
  
  // === Gates ===
  all_gates_passed: boolean;
  gates_evaluated: GateEvaluationResult[];
  
  // === Evidence ===
  step_results: StepExecutionResult[];
  evidence_refs: string[];
  
  // === pAVS ===
  pavs_review_status: PAVSDecision;
  pavs_review_id: string | null;
  
  // === Truth Fields (WSP 97) ===
  cabr_ready: false;          // Always false
  payout_ready: false;        // Always false
  verification_complete: false;  // Always false
  
  // === Timestamps ===
  started_at: string;
  completed_at: string;
}
```

---

## 3. Step Lifecycle

### 3.1 Step Status Enum

```typescript
type StepStatus =
  | "pending"      // Not yet started
  | "running"      // Currently executing
  | "succeeded"    // Completed successfully
  | "failed"       // Failed during execution
  | "blocked"      // Blocked by gate or dependency
  | "rolled_back"  // Rolled back after failure
  | "skipped";     // Skipped (optional step or condition not met)
```

### 3.2 Step State Machine

```
PENDING
    │
    ├── evaluate_pre_gates() -> BLOCKED (gate failed)
    │
    └── pre_gates_passed -> RUNNING
                              │
                              ├── simulate_or_execute() -> SUCCEEDED
                              │
                              ├── simulate_or_execute() -> FAILED
                              │                              │
                              │                              └── rollback() -> ROLLED_BACK
                              │
                              └── post_gates_failed -> BLOCKED
```

### 3.3 Terminal Step States

- **SUCCEEDED**: Step completed, evidence collected, proceed to next
- **FAILED**: Step failed, rollback triggered, execution halts
- **BLOCKED**: Gate prevented execution, human review required
- **ROLLED_BACK**: Failed step was successfully rolled back
- **SKIPPED**: Step was conditionally skipped (optional step)

---

## 4. Execution Lifecycle

### 4.1 Full Execution Sequence

```
1. validate_plan(plan)
   └── Check plan integrity, target scope, blocked paths

2. FOR each step in plan.steps:
   │
   ├── 2a. evaluate_pre_gates(plan, step)
   │       └── Check required gates before step
   │
   ├── 2b. IF pre_gates_passed:
   │       │
   │       └── simulate_or_execute_step(ctx)
   │           │
   │           ├── DRY_RUN: Simulate changes, collect planned_diff
   │           │
   │           └── REAL: Execute changes, collect actual_diff
   │
   ├── 2c. collect_evidence(ctx, result)
   │       └── Record evidence_refs, test_results, diffs
   │
   ├── 2d. evaluate_post_gates(plan, step, result)
   │       └── Check gates after step (e.g., test_gate after RUN_TESTS)
   │
   └── 2e. IF step_failed:
           └── rollback_on_failure(plan, step)

3. emit_receipt(plan, results)
   └── Create ExecutionReceipt with all evidence

4. submit_pavs_review(receipt)
   └── Submit receipt for pAVS review (ACCEPTED_FOR_REVIEW | NOT_REQUIRED)

5. close_execution(plan)
   └── Mark plan COMPLETED | FAILED, cleanup
```

### 4.2 Lifecycle Method Contracts

| Method | Pre-Condition | Post-Condition |
|--------|--------------|----------------|
| `validate_plan` | Plan exists | Plan validity confirmed |
| `evaluate_pre_gates` | Plan validated | Gate results recorded |
| `simulate_or_execute_step` | Pre-gates passed | Step result produced |
| `collect_evidence` | Step completed | Evidence refs populated |
| `evaluate_post_gates` | Evidence collected | Post-gate results recorded |
| `emit_receipt` | Execution complete | Receipt created |
| `submit_pavs_review` | Receipt created | pAVS decision recorded |
| `rollback_on_failure` | Step failed | State restored |
| `close_execution` | Receipt submitted | Plan status terminal |

---

## 5. Gate Sequence

### 5.1 Gate Evaluation Order

| Order | Gate | When Evaluated | Required |
|-------|------|---------------|----------|
| 1 | genesis_gate | Before step_01 | YES |
| 2 | wsp_structure_gate | After step_01 | YES |
| 3 | scope_gate | Before any file operation | YES |
| 4 | manifest_gate | After step_02 | YES |
| 5 | dry_run_gate | After step_10 | YES |
| 6 | test_gate | After step_07 | YES |
| 7 | rollback_gate | Before REAL execution | YES for REAL |
| 8 | human_approval_gate | Before mode=REAL promotion | **YES for REAL** |
| 9 | pavs_submission_gate | After receipt | YES for REAL |

### 5.2 Gate Evaluation Logic

```python
def evaluate_gate(plan: BuildPlan, gate: BuildGate, context: Any) -> GateEvaluationResult:
    """
    Evaluate a gate in the context of plan execution.
    
    Args:
        plan: Current BuildPlan
        gate: Gate to evaluate
        context: Step result or other context
    
    Returns:
        GateEvaluationResult with passed/failed and reason
    """
    match gate.gate_type:
        case GateType.GENESIS_GATE:
            # Check foundup_manifest.json exists and valid
            passed = manifest_exists_and_valid(plan.target)
            
        case GateType.WSP_STRUCTURE_GATE:
            # Check module structure per WSP 49
            passed = wsp_structure_valid(plan.target)
            
        case GateType.SCOPE_GATE:
            # Check all operations within allowed_paths
            passed = all_ops_in_scope(plan, context)
            
        case GateType.TEST_GATE:
            # Check test results from step
            passed = context.tests_passed if context else False
            
        case GateType.HUMAN_APPROVAL_GATE:
            # Check explicit human approval
            passed = gate.approver_id is not None and gate.approval_method != "not_approved"
            
    return GateEvaluationResult(
        gate_id=gate.gate_id,
        gate_type=gate.gate_type,
        passed=passed,
        reason=f"Gate {'passed' if passed else 'failed'}: {gate.gate_type.value}",
        checked_by="system",
        blocks_execution=gate.required and not passed,
        requires_human=gate.gate_type == GateType.HUMAN_APPROVAL_GATE,
    )
```

---

## 6. Allowed Dry-Run Behavior

### 6.1 Permitted Operations (DRY_RUN mode)

| Operation | Allowed | Evidence Produced |
|-----------|---------|-------------------|
| Read files | YES | file_snapshots |
| Compute planned_diff | YES | planned_diff |
| Validate manifests | YES | validation_result |
| Run tests | YES | test_results |
| Generate evidence | YES | evidence_refs |
| Emit receipts | YES | ExecutionReceipt |
| Inspect scope boundaries | YES | scope_validation |
| Check gate conditions | YES | gate_results |

### 6.2 Dry-Run Execution Semantics

```python
def simulate_step(ctx: StepExecutionContext) -> StepExecutionResult:
    """
    Simulate a step without making changes.
    
    Returns planned_diff showing what WOULD change.
    """
    # 1. Compute what files would be created/modified
    planned_files = compute_planned_operations(ctx.step, ctx.target_files)
    
    # 2. Generate planned_diff
    planned_diff = DiffSummary(
        files_created=len([f for f in planned_files if f.operation == "create"]),
        files_modified=len([f for f in planned_files if f.operation == "modify"]),
        files_deleted=len([f for f in planned_files if f.operation == "delete"]),
        lines_added=sum(f.lines_added for f in planned_files),
        lines_removed=sum(f.lines_removed for f in planned_files),
    )
    
    # 3. Validate operations are within scope
    scope_valid = all(
        plan.validate_scope(f.path) for f in planned_files
    )
    
    return StepExecutionResult(
        step_id=ctx.step.step_id,
        status=StepStatus.SUCCEEDED if scope_valid else StepStatus.BLOCKED,
        dry_run=True,
        simulated=True,
        planned_diff=planned_diff,
        actual_diff=None,  # No actual changes in dry-run
    )
```

---

## 7. Blocked Dry-Run Behavior

### 7.1 Forbidden Operations (DRY_RUN mode)

| Operation | Allowed | Reason |
|-----------|---------|--------|
| Write production files | **NO** | dry_run=True |
| Deploy to external systems | **NO** | No deploy pipeline |
| Delete unrelated files | **NO** | Scope boundary |
| Issue token/reward/payout | **NO** | No payout engine |
| Claim CABR verification | **NO** | cabr_ready=False |
| Claim pAVS final verification | **NO** | verification_complete=False |
| Modify wallet/blockchain | **NO** | Protected paths |
| Execute raw chat commands | **NO** | Typed operations only |

### 7.2 Blocked Path Enforcement

```python
BLOCKED_PATHS_ALWAYS = [
    "**/wallet/**",
    "**/token/**",
    "**/reward/**",
    "**/payout/**",
    "**/cabr/**",
    "**/blockchain/**",
    "**/agent_market/**",
    "**/.env*",
    "**/credentials*",
    "**/secrets*",
]

def validate_operation_scope(operation: Operation, plan: BuildPlan) -> bool:
    """
    Validate operation is within allowed scope and not blocked.
    
    Returns False if operation targets blocked paths.
    """
    path = operation.target_path
    
    # Check global blocked paths
    for blocked in BLOCKED_PATHS_ALWAYS:
        if fnmatch.fnmatch(path, blocked):
            return False
    
    # Check plan scope
    return plan.validate_scope(path)
```

---

## 8. Real Execution Promotion

### 8.1 Promotion Criteria

A BuildPlan may be promoted from DRY_RUN to REAL **only** when:

| Criterion | Required | Verification |
|-----------|----------|--------------|
| Dry-run plan passed | YES | `dry_run_gate.passed == True` |
| All tests pass | YES | `test_gate.passed == True` |
| Rollback points exist | YES | `plan.has_rollback_points() == True` |
| Human approval | **YES** | `human_approval_gate.passed == True` |
| Target scope locked | YES | `scope_gate.passed == True` |
| pAVS review receipt | YES | Receipt submitted before REAL |
| Architect approval | YES | Explicit command/PR approval |

### 8.2 Promotion Flow

```
DRY_RUN BuildPlan
    │
    ├── All required gates pass
    │
    ├── Tests pass (test_gate)
    │
    ├── Evidence collected
    │
    ├── Receipt emitted
    │
    ├── pAVS accepts for review
    │
    └── Human/Architect explicitly approves
           │
           ▼
    REAL BuildPlan (mode="real", dry_run=False)
           │
           ├── human_approval_gate.passed = True
           ├── human_approval_gate.approver_id = "012"
           ├── human_approval_gate.approval_method = "explicit_command"
           │
           └── Execute steps with actual file operations
```

### 8.3 Promotion Blocker: No Auto-Promotion

**WSP 97 Critical**: There is NO automatic promotion path.

```python
def can_promote_to_real(plan: BuildPlan) -> PromotionResult:
    """
    Check if plan can be promoted to REAL execution.
    
    WSP 97: This function returns a check result.
    It does NOT perform promotion.
    """
    # Check dry-run gate
    dry_run_gate = plan.get_gate(GateType.DRY_RUN_GATE)
    if not dry_run_gate or not dry_run_gate.passed:
        return PromotionResult(
            allowed=False,
            reason="Dry-run gate not passed - execute dry-run first"
        )
    
    # Check test gate
    test_gate = plan.get_gate(GateType.TEST_GATE)
    if not test_gate or not test_gate.passed:
        return PromotionResult(
            allowed=False,
            reason="Test gate not passed - all tests must pass"
        )
    
    # Check rollback points
    if not plan.has_rollback_points():
        return PromotionResult(
            allowed=False,
            reason="No rollback points - cannot recover from failure"
        )
    
    # Check human approval
    human_gate = plan.get_gate(GateType.HUMAN_APPROVAL_GATE)
    if not human_gate or not human_gate.passed:
        return PromotionResult(
            allowed=False,
            reason="Human approval required for REAL execution"
        )
    
    return PromotionResult(allowed=True, reason="All promotion criteria met")
```

---

## 9. Hermes Integration

### 9.1 Integration Architecture

```
Raw User Request
    │
    ├── ❌ NEVER directly to Hermes
    │
    ▼
OpenClaw Intent
    │
    ▼
FoundUpJob (typed contract)
    │
    ▼
BuildPlan (generated)
    │
    ▼
BuildPlanExecutor
    │
    ├── DRY_RUN: Simulate via HermesFoundUpBuilder (dry_run=True)
    │
    └── REAL: Execute via HermesFoundUpBuilder (with human_approval_gate)
```

### 9.2 Hermes Constraints

| Constraint | Enforcement |
|------------|-------------|
| Raw chat is never execution input | FoundUpJob.requested_action must be canonical |
| FoundUpJob -> BuildPlan -> Executor | Only typed path to Hermes |
| Hermes executes bounded steps only | Steps from BuildPlan, not ad-hoc |
| dry_run=True by default | BuildPlanExecutor enforces |
| Evidence collected per step | Executor collects and emits |

### 9.3 Step Execution via Hermes

```python
def execute_step_via_hermes(
    ctx: StepExecutionContext,
    builder: HermesFoundUpBuilder,
) -> StepExecutionResult:
    """
    Execute a BuildStep through Hermes.
    
    Args:
        ctx: Step execution context
        builder: HermesFoundUpBuilder instance
    
    Returns:
        StepExecutionResult with evidence
    
    WSP 97: This function exists in spec only.
    """
    # Hermes executes only through BuildPlanExecutor
    # Never from raw chat or direct invocation
    
    if ctx.dry_run:
        # Simulate only
        return builder.simulate_step(ctx.step)
    else:
        # Real execution (requires all gates passed)
        if not all_gates_passed(ctx.plan):
            raise GateViolationError("Cannot execute REAL without all gates")
        
        return builder.execute_step(ctx.step)
```

---

## 10. Evidence

### 10.1 Evidence Types

| Type | Description | Collected When |
|------|-------------|----------------|
| `evidence_refs` | File paths/IDs | Every step |
| `step_logs` | Execution logs | Every step |
| `planned_diff` | What would change | DRY_RUN |
| `actual_diff` | What changed | REAL only |
| `test_results` | Test execution | RUN_TESTS step |
| `receipt_id` | Receipt identifier | After execution |
| `pavs_review_status` | pAVS decision | After receipt |
| `file_snapshots` | Pre-step state | Steps with rollback |

### 10.2 Evidence Collection

```python
def collect_evidence(
    ctx: StepExecutionContext,
    result: StepExecutionResult,
) -> List[Evidence]:
    """
    Collect evidence from step execution.
    """
    evidence = []
    
    # Step log
    evidence.append(Evidence(
        type="step_log",
        path=f"logs/{ctx.plan.build_plan_id}/{ctx.step.step_id}.log",
        content_hash=hash_log(result),
    ))
    
    # Diff evidence
    if result.planned_diff:
        evidence.append(Evidence(
            type="planned_diff",
            path=f"evidence/{ctx.step.step_id}_planned_diff.json",
            content_hash=hash_diff(result.planned_diff),
        ))
    
    # Test results
    if result.test_results:
        evidence.append(Evidence(
            type="test_results",
            path=f"evidence/{ctx.step.step_id}_test_results.json",
            content_hash=hash_tests(result.test_results),
        ))
    
    return evidence
```

---

## 11. WSP 97 Truth Boundaries

### 11.1 What This Contract DOES

- Define BuildPlanExecutor interface
- Define step execution lifecycle
- Define gate evaluation sequence
- Define rollback mechanism
- Define evidence collection model
- Define Hermes integration pattern
- Define dry-run vs real execution modes

### 11.2 What This Contract DOES NOT

- Implement BuildPlanExecutor
- Enable real (non-dry-run) builds
- Execute BuildPlan steps
- Wire Hermes real execution
- Wire RedDog/pfMALL UI
- Implement CABR consensus
- Implement rewards/payouts
- Create automatic promotion to real builds

### 11.3 Truth Field Defaults

```python
# ExecutionReceipt always has:
cabr_ready = False           # No CABR consensus exists
payout_ready = False         # No payout engine exists
verification_complete = False  # Only accepted for review

# BuildPlanExecutor always enforces:
dry_run_default = True       # DRY_RUN unless explicitly promoted
human_approval_required = True  # For mode=REAL
```

---

## 12. Example: VoteBallot Dry-Run Execution

**Status**: `SPEC_EXAMPLE_NOT_EXECUTED`

```yaml
# Example dry-run execution of VoteBallot BuildPlan
# This is a SPECIFICATION EXAMPLE, NOT executed code

plan_id: bp_voteballots_66d1a2b3_abc123
mode: dry_run
status: executing

# Step 1: Validate Genesis
step_01:
  action: validate_genesis
  status: succeeded
  dry_run: true
  simulated: true
  evidence_refs:
    - modules/foundups/voteballots/foundup_manifest.json
  pre_gates:
    - genesis_gate: passed
  post_gates: []

# Step 2: Validate Manifest
step_02:
  action: validate_manifest
  status: succeeded
  dry_run: true
  simulated: true
  evidence_refs:
    - modules/foundups/voteballots/foundup_manifest.json
  pre_gates:
    - scope_gate: passed
  post_gates:
    - manifest_gate: passed

# ... steps 3-6 simulated ...

# Step 7: Run Tests
step_07:
  action: run_tests
  status: succeeded
  dry_run: true
  simulated: false  # Tests actually run even in dry-run
  test_results:
    - test_file: tests/test_adversarial_influence_categories.py
      tests_run: 5
      tests_passed: 5
      tests_failed: 0
  post_gates:
    - test_gate: passed

# ... steps 8-10 simulated ...

# Step 11: Submit Receipt
step_11:
  action: submit_receipt
  status: succeeded
  evidence_refs:
    - receipt_id: rcpt_bp_voteballots_abc123

# Step 12: Request Approval (dry-run does not require)
step_12:
  action: request_approval
  status: skipped  # Not required for dry-run
  post_gates:
    - human_approval_gate: skipped (not required for dry_run)

# Final Receipt
receipt:
  receipt_id: rcpt_bp_voteballots_abc123
  mode: dry_run
  total_steps: 12
  steps_succeeded: 11
  steps_skipped: 1
  all_gates_passed: true
  pavs_review_status: NOT_REQUIRED
  cabr_ready: false
  payout_ready: false
  verification_complete: false
```

---

## 13. Related Documents

- [FOUNDUP_BUILD_PLAN_CONTRACT.md](FOUNDUP_BUILD_PLAN_CONTRACT.md) — BuildPlan schema
- [FOUNDUP_TEMPLATE.md](FOUNDUP_TEMPLATE.md) — FoundUp onboarding checklist
- [VERIFICATION_GAP_GUARD_CONTRACT.md](VERIFICATION_GAP_GUARD_CONTRACT.md) — Protected classes
- [build_plan.py](../agent/src/build_plan.py) — BuildPlan dataclass
- [build_plan_generator.py](../agent/src/build_plan_generator.py) — Plan generation
- [hermes_foundup_job_executor.py](../agent/src/hermes_foundup_job_executor.py) — Job execution

---

## 14. Future Work

### 14.1 Next Atomic Slice: BuildPlanExecutor Interface Stub

**Candidate slice**: `OC12_BUILD_PLAN_EXECUTOR_INTERFACE_STUB_PHASE1`

Would create:

```
modules/foundups/agent/src/build_plan_executor.py
  - BuildPlanExecutor class (interface only)
  - StepExecutionContext dataclass
  - StepExecutionResult dataclass
  - GateEvaluationResult dataclass
  - ExecutionReceipt dataclass
  - validate_plan() -> ValidationResult
  - simulate_step() -> StepExecutionResult (dry-run only)

modules/foundups/agent/tests/test_build_plan_executor.py
  - Test interface instantiation
  - Test dry-run simulation
  - Test real execution blocked by default
  - Test gate evaluation
```

**NOT in scope for next slice**:
- Real step execution
- Hermes integration
- Rollback implementation
- pAVS submission

---

## Appendix: Decision Record

**ADR-BPE-001**: BuildPlan Execution Adapter Contract

- **Date**: 2026-04-29
- **Status**: Accepted
- **Context**: Need execution adapter to bridge BuildPlan to controlled step operations
- **Decision**: Spec-only contract with mandatory human_approval_gate for REAL execution
- **Consequences**: 
  - DRY_RUN remains default for all execution
  - Real execution requires explicit human approval
  - All execution paths produce evidence
  - Failed steps trigger rollback
  - Hermes integration only through BuildPlanExecutor
