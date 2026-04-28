# FoundUp Build Plan Contract

**Status**: Architecture Specification (ADR)
**Owner**: 0102
**Slice**: `OC7_REAL_FOUNDUP_BUILD_PLAN_CONTRACT_PHASE1`
**WSP References**: WSP 11 (Interface Protocol), WSP 50 (Pre-Action Verification), WSP 97 (Truth Boundaries)

---

## WSP 97 Truthfulness Statement

This document is an **architecture specification only**. No real (non-dry-run) build execution is implemented.

| Claim | Status |
|-------|--------|
| BuildPlan schema defined | `SPECIFIED_NOT_IMPLEMENTED` |
| Build steps defined | `SPECIFIED_NOT_IMPLEMENTED` |
| Gates defined | `SPECIFIED_NOT_IMPLEMENTED` |
| Dry-run to real promotion criteria | `SPECIFIED_NOT_IMPLEMENTED` |
| Real build executor | `SPECIFIED_NOT_IMPLEMENTED` |

**Canonical Rule**: Dry-run is the default. Real builds require explicit approval gates and human oversight.

---

## 1. Purpose

Define the contract for FoundUp build plans so:

1. OpenClaw/Hermes can progress from dry-run PoC to controlled real builds
2. Build scope is explicit and bounded
3. Rollback points exist for each step
4. Evidence model supports pAVS verification
5. Human approval gates prevent autonomous production builds

**Prerequisite**: Internal dry-run PoC must pass (e.g., VoteBallot PoC PR #440).

---

## 2. BuildPlan Identity

### 2.1 Schema Definition

```typescript
interface BuildPlanIdentity {
  // === Plan Identity ===
  build_plan_id: string;      // Unique: bp_{foundup_id}_{timestamp_hex}_{random}
  
  // === Source Context ===
  foundup_id: string;         // Target FoundUp (e.g., "voteballots")
  tenant_id: string;          // Actor scope (e.g., "012")
  intent_id: string | null;   // OpenClaw session correlation
  source_job_id: string;      // FoundUpJob that triggered this plan
  
  // === Execution Mode ===
  requested_action: string;   // Canonical action (build_foundup, etc.)
  dry_run: boolean;           // Default: true
  
  // === Timestamps ===
  created_at: string;         // ISO 8601
  updated_at: string;         // ISO 8601
  
  // === Plan Version ===
  plan_version: string;       // Schema version (e.g., "1.0.0")
}
```

### 2.2 Plan ID Generation

```python
def generate_build_plan_id(foundup_id: str) -> str:
    """
    Generate unique build plan ID.
    Format: bp_{foundup_id}_{timestamp_hex}_{random_hex}
    Example: bp_voteballots_66d1a2b3_abc123
    """
    timestamp_hex = hex(int(utc_now().timestamp()))[2:][:8]
    random_hex = secrets.token_hex(3)
    return f"bp_{foundup_id[:20]}_{timestamp_hex}_{random_hex}"
```

---

## 3. Build Target

### 3.1 Target Schema

```typescript
interface BuildTarget {
  // === Module Location ===
  module_path: string;            // e.g., "modules/foundups/voteballots"
  foundup_manifest_path: string;  // e.g., "modules/foundups/voteballots/foundup_manifest.json"
  
  // === Surface Paths ===
  pwa_surface_path: string | null;   // e.g., "public/member/foundups/voteballots/"
  tests_path: string;                // e.g., "modules/foundups/voteballots/tests/"
  docs_path: string;                 // e.g., "modules/foundups/voteballots/docs/"
  
  // === Required Artifact Paths ===
  modlog_path: string;            // e.g., "modules/foundups/voteballots/ModLog.md"
  testmodlog_path: string;        // e.g., "modules/foundups/voteballots/tests/TestModLog.md"
  readme_path: string;            // e.g., "modules/foundups/voteballots/README.md"
  interface_path: string | null;  // e.g., "modules/foundups/voteballots/INTERFACE.md"
  
  // === Scope Boundary ===
  allowed_paths: string[];        // Glob patterns for allowed modifications
  blocked_paths: string[];        // Glob patterns that MUST NOT be modified
}
```

### 3.2 Scope Boundary Rules

| Allowed | Blocked |
|---------|---------|
| `{module_path}/**` | `**/wallet/**` |
| `{tests_path}/**` | `**/token/**` |
| `{docs_path}/**` | `**/reward/**` |
| `{pwa_surface_path}/**` | `**/payout/**` |
| | `**/cabr/**` |
| | `modules/foundups/agent_market/**` |
| | `modules/blockchain/**` |

---

## 4. Build Steps

### 4.1 Step Schema

```typescript
interface BuildStep {
  // === Step Identity ===
  step_id: string;              // Ordered: step_01, step_02, ...
  step_name: string;            // Human-readable name
  
  // === Action ===
  action: BuildStepAction;      // See BuildStepAction enum
  target_files: string[];       // Files to create/modify
  
  // === Operations ===
  allowed_operations: AllowedOperation[];
  expected_outputs: string[];   // Expected result files/artifacts
  
  // === Rollback ===
  rollback_point: boolean;      // If true, state can be restored to before this step
  rollback_command: string | null;  // Command to execute rollback
  
  // === Evidence ===
  evidence_required: boolean;   // If true, step must produce evidence_refs
  
  // === Status ===
  status: StepStatus;           // pending | running | succeeded | failed | skipped
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
}

type BuildStepAction =
  | "create_spec"           // Create specification/contract doc
  | "create_test"           // Create test file
  | "create_module"         // Create module source file
  | "update_manifest"       // Update foundup_manifest.json
  | "update_modlog"         // Update ModLog.md
  | "update_testmodlog"     // Update TestModLog.md
  | "run_tests"             // Execute test suite
  | "validate_structure"    // Validate WSP module structure
  | "validate_manifest"     // Validate manifest schema
  | "create_adapters"       // Create adapter stubs
  | "dry_run_build"         // Execute dry-run build
  | "submit_receipt"        // Submit ProofOfComputeReceipt
  | "request_approval"      // Request human/architect approval

type StepStatus = "pending" | "running" | "succeeded" | "failed" | "skipped";
```

### 4.2 Standard Build Step Sequence

| Order | Step | Action | Rollback | Evidence |
|-------|------|--------|----------|----------|
| 01 | Genesis validation | `validate_structure` | No | Yes |
| 02 | Manifest validation | `validate_manifest` | No | Yes |
| 03 | Create spec docs | `create_spec` | Yes | Yes |
| 04 | Create tests | `create_test` | Yes | Yes |
| 05 | Create module files | `create_module` | Yes | Yes |
| 06 | Update manifest | `update_manifest` | Yes | Yes |
| 07 | Run tests | `run_tests` | No | Yes |
| 08 | Update ModLog | `update_modlog` | Yes | Yes |
| 09 | Update TestModLog | `update_testmodlog` | Yes | Yes |
| 10 | Dry-run build | `dry_run_build` | No | Yes |
| 11 | Submit receipt | `submit_receipt` | No | Yes |
| 12 | Request approval | `request_approval` | No | Yes |

---

## 5. Gates

### 5.1 Gate Schema

```typescript
interface BuildGate {
  gate_id: string;
  gate_name: string;
  gate_type: BuildGateType;
  required: boolean;          // If true, build cannot proceed without passing
  checked: boolean;           // Has gate been evaluated?
  passed: boolean;            // Did gate pass?
  reason: string | null;      // Explanation if failed
  checked_at: string | null;
  checked_by: string | null;  // "system" | worker_id | human_reviewer_id
}

type BuildGateType =
  | "genesis_gate"            // FoundUp genesis validation
  | "wsp_structure_gate"      // WSP module structure check
  | "manifest_gate"           // Manifest schema validation
  | "dry_run_gate"            // Dry-run execution required
  | "test_gate"               // Tests must pass
  | "modlog_gate"             // ModLog/TestModLog present
  | "pavs_submission_gate"    // pAVS receipt submitted
  | "human_approval_gate";    // Human approval for non-dry-run
```

### 5.2 Gate Sequence

| Gate | When Checked | Required for Dry-Run | Required for Real |
|------|--------------|---------------------|-------------------|
| genesis_gate | Before step_01 | YES | YES |
| wsp_structure_gate | After step_01 | YES | YES |
| manifest_gate | After step_02 | YES | YES |
| dry_run_gate | After step_10 | YES | YES |
| test_gate | After step_07 | YES | YES |
| modlog_gate | After step_09 | YES | YES |
| pavs_submission_gate | After step_11 | NO | YES |
| human_approval_gate | After step_12 | NO | **YES** |

### 5.3 Human Approval Gate

**WSP 97 Critical**: Non-dry-run builds MUST pass human_approval_gate.

```typescript
interface HumanApprovalGate extends BuildGate {
  gate_type: "human_approval_gate";
  
  // Approval context
  approver_id: string | null;       // Human reviewer ID
  approval_method: ApprovalMethod;  // How approval was obtained
  approval_timestamp: string | null;
  approval_scope: string;           // What was approved
  
  // Escalation
  escalated_to: string | null;      // If approval denied, who to escalate
  escalation_reason: string | null;
}

type ApprovalMethod = 
  | "explicit_command"    // "012: approve build plan bp_xyz"
  | "pr_merge"            // PR merged with approval
  | "architect_review"    // Architect explicitly approved
  | "not_approved";       // Default
```

---

## 6. Allowed Operations

### 6.1 Operation Schema

```typescript
type AllowedOperation =
  | "create_file"           // Create new file (within scope)
  | "update_file"           // Modify existing file (within scope)
  | "delete_file"           // Delete file (within scope, with rollback)
  | "create_directory"      // Create directory (within scope)
  | "run_test_command"      // Execute test command
  | "read_manifest"         // Read foundup_manifest.json
  | "update_manifest"       // Update foundup_manifest.json (within scope)
  | "emit_receipt"          // Emit ProofOfComputeReceipt
  | "submit_pavs";          // Submit to pAVS for review
```

### 6.2 Operation Scope Constraints

```typescript
interface OperationConstraint {
  operation: AllowedOperation;
  scope_pattern: string;          // Glob pattern
  requires_dry_run_first: boolean;
  requires_human_approval: boolean;
}

const OPERATION_CONSTRAINTS: OperationConstraint[] = [
  { operation: "create_file", scope_pattern: "{module_path}/**", requires_dry_run_first: true, requires_human_approval: false },
  { operation: "update_manifest", scope_pattern: "{foundup_manifest_path}", requires_dry_run_first: true, requires_human_approval: true },
  { operation: "delete_file", scope_pattern: "{module_path}/**", requires_dry_run_first: true, requires_human_approval: true },
];
```

---

## 7. Blocked Operations

### 7.1 Absolutely Blocked

These operations are NEVER allowed in any build plan:

| Operation | Reason | Reference |
|-----------|--------|-----------|
| Wallet/token changes | Protected class | VerificationGapGuard |
| Reward/payout issuance | No payout engine exists | WSP 97 |
| CABR finalization | No consensus exists | WSP 97 |
| Trust ledger publication | Protected class | VerificationGapGuard |
| Modify outside target scope | Scope boundary | BuildTarget |
| Delete unrelated modules | Scope boundary | BuildTarget |
| Live deploy | Requires deploy pipeline | Future work |
| Non-dry-run without approval | human_approval_gate | Section 5.3 |

### 7.2 Blocked Path Patterns

```typescript
const BLOCKED_PATH_PATTERNS: string[] = [
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
];
```

---

## 8. Evidence Model

### 8.1 Evidence Schema

```typescript
interface BuildPlanEvidence {
  // === Job Correlation ===
  source_job_id: string;
  build_plan_id: string;
  
  // === Execution Evidence ===
  evidence_refs: string[];        // Paths/IDs of evidence artifacts
  test_commands: string[];        // Test commands executed
  test_results: TestResult[];     // Test execution results
  
  // === Change Evidence ===
  diff_summary: DiffSummary;      // Summary of changes
  files_changed: FileChange[];    // Detailed file changes
  
  // === Policy Evidence ===
  policy_flags: PolicyFlags;      // Gate pass/fail states
  gates_evaluated: BuildGate[];   // All gates and their results
  
  // === Receipt Correlation ===
  receipt_id: string | null;      // ProofOfComputeReceipt ID
  pavs_verification_id: string | null;  // PAVSVerificationResult ID
  pavs_review_status: PAVSDecision;     // Current pAVS status
}

interface TestResult {
  test_file: string;
  tests_run: number;
  tests_passed: number;
  tests_failed: number;
  duration_ms: number;
  output_snippet: string;     // First 500 chars of output
}

interface DiffSummary {
  files_created: number;
  files_modified: number;
  files_deleted: number;
  lines_added: number;
  lines_removed: number;
}

interface FileChange {
  file_path: string;
  change_type: "created" | "modified" | "deleted";
  lines_added: number;
  lines_removed: number;
}
```

---

## 9. Dry-Run to Real Promotion

### 9.1 Promotion Criteria

A build plan may be promoted from dry-run to real ONLY when:

| Criterion | Required | Verification |
|-----------|----------|--------------|
| Dry-run build plan passed | YES | `dry_run_gate.passed == true` |
| All tests pass | YES | `test_gate.passed == true` |
| Scope is bounded | YES | All operations within `allowed_paths` |
| Rollback plan exists | YES | Each modifying step has `rollback_point: true` |
| Human approval | YES | `human_approval_gate.passed == true` |
| pAVS receipt submitted | YES | `pavs_submission_gate.passed == true` |
| No blocked operations | YES | Zero violations of Section 7 |

### 9.2 Promotion Flow

```
Dry-Run BuildPlan (dry_run: true)
    │
    ├── All gates pass
    │
    ├── Tests pass
    │
    ├── Evidence collected
    │
    ├── Receipt submitted to pAVS
    │
    ├── pAVS accepts for review
    │
    └── Human/Architect approval
           │
           ▼
    Real BuildPlan (dry_run: false, human_approval_gate.passed: true)
```

### 9.3 Promotion Blocker: No Auto-Promotion

**WSP 97 Critical**: There is NO automatic promotion path. A human MUST explicitly approve transition from dry-run to real.

```typescript
function canPromoteToReal(plan: BuildPlan): PromotionResult {
  // Check all gates
  if (!plan.gates.every(g => g.required ? g.passed : true)) {
    return { allowed: false, reason: "Required gates not passed" };
  }
  
  // Check human approval explicitly
  const humanGate = plan.gates.find(g => g.gate_type === "human_approval_gate");
  if (!humanGate?.passed) {
    return { 
      allowed: false, 
      reason: "Human approval required for non-dry-run builds" 
    };
  }
  
  return { allowed: true, reason: "All criteria met" };
}
```

---

## 10. WSP 97 Truth Boundaries

### 10.1 What This Contract DOES

- Define BuildPlan identity schema
- Define build target scope constraints
- Define ordered build steps
- Define gates (including human_approval_gate)
- Define allowed/blocked operations
- Define evidence model
- Define dry-run to real promotion criteria

### 10.2 What This Contract DOES NOT

- Implement real build execution
- Enable non-dry-run builds
- Wire RedDog/pfMALL UI
- Issue tokens/rewards/payouts
- Implement CABR consensus
- Implement deploy pipeline
- Create automatic promotion to real builds

### 10.3 What This Contract ENABLES

- Future BuildPlan dataclass implementation
- Future real build executor (gated)
- Future promotion workflow
- Clear scope boundaries for build workers
- Human-in-the-loop for production changes

---

## 11. Example: VoteBallot Internal Dry-Run Build Plan

**Status**: `SPEC_EXAMPLE_NOT_EXECUTED`

```yaml
# Example BuildPlan for VoteBallot PoC (NOT EXECUTED - SPEC ONLY)
build_plan_id: bp_voteballots_66d1a2b3_abc123
foundup_id: voteballots
tenant_id: "012"
intent_id: internal_poc_voteballot_build
source_job_id: j_build_voteballots_xyz
requested_action: build_foundup
dry_run: true
plan_version: "1.0.0"

target:
  module_path: modules/foundups/voteballots
  foundup_manifest_path: modules/foundups/voteballots/foundup_manifest.json
  tests_path: modules/foundups/voteballots/tests/
  docs_path: modules/foundups/voteballots/docs/
  modlog_path: modules/foundups/voteballots/ModLog.md
  testmodlog_path: modules/foundups/voteballots/tests/TestModLog.md
  allowed_paths:
    - modules/foundups/voteballots/**
  blocked_paths:
    - "**/wallet/**"
    - "**/token/**"

steps:
  - step_id: step_01
    step_name: Genesis validation
    action: validate_structure
    evidence_required: true
    status: succeeded  # In PoC, this passed

  - step_id: step_02
    step_name: Manifest validation
    action: validate_manifest
    evidence_required: true
    status: succeeded

  # ... (abbreviated for spec)

gates:
  - gate_id: genesis_gate
    gate_type: genesis_gate
    required: true
    passed: true
  
  - gate_id: dry_run_gate
    gate_type: dry_run_gate
    required: true
    passed: true
  
  - gate_id: human_approval_gate
    gate_type: human_approval_gate
    required: false  # Not required for dry-run
    passed: false    # Not evaluated for dry-run

evidence:
  evidence_refs:
    - modules/foundups/voteballots/foundup_manifest.json
    - FOUNDUPS/voteballots
  test_commands:
    - python -m pytest modules/foundups/voteballots/tests/ -q
  test_results:
    - test_file: tests/test_adversarial_influence_categories.py
      tests_run: 5
      tests_passed: 5
      tests_failed: 0
  policy_flags:
    dry_run_mode: true
    exfoliation_gate_passed: true
  receipt_id: null  # Would be set after receipt creation
  pavs_review_status: not_required  # Dry-run does not require pAVS
```

---

## 12. Related Documents

- [FOUNDUP_TEMPLATE.md](FOUNDUP_TEMPLATE.md) — FoundUp onboarding checklist
- [VERIFICATION_GAP_GUARD_CONTRACT.md](VERIFICATION_GAP_GUARD_CONTRACT.md) — Protected decision classes
- [foundup_job_contract.py](../../communication/moltbot_bridge/src/foundup_job_contract.py) — Job schema
- [proof_of_compute_receipt.py](../../communication/moltbot_bridge/src/proof_of_compute_receipt.py) — Receipt schema
- [pavs_verification_seam.py](../../communication/moltbot_bridge/src/pavs_verification_seam.py) — pAVS verification

---

## 13. Future Work

### 13.1 Next Atomic Slice: BuildPlan Interface Stub

**Candidate slice**: `OC8_BUILD_PLAN_DATACLASS_INTERFACE_STUB_PHASE1`

Would create:

```
modules/communication/moltbot_bridge/src/build_plan_contract.py
  - BuildPlanIdentity dataclass
  - BuildTarget dataclass
  - BuildStep dataclass
  - BuildGate dataclass
  - BuildStepAction enum
  - BuildGateType enum
  - AllowedOperation enum
  - canPromoteToReal() -> PromotionResult

modules/communication/moltbot_bridge/tests/test_build_plan_contract.py
  - Test schema validity
  - Test scope boundary enforcement
  - Test gate sequencing
  - Test blocked operations
  - Test promotion criteria
```

**NOT in scope for next slice**:
- Real build executor
- Promotion workflow
- Deploy pipeline

---

## Appendix: Decision Record

**ADR-BP-001**: FoundUp Build Plan Contract

- **Date**: 2026-04-29
- **Status**: Accepted
- **Context**: Need structured contract for moving from dry-run PoC to controlled real builds
- **Decision**: Spec-only contract with human_approval_gate as mandatory for non-dry-run
- **Consequences**: 
  - Dry-run remains default
  - Real builds require explicit human approval
  - Scope boundaries prevent wallet/token/payout modifications
  - Evidence model supports pAVS verification
