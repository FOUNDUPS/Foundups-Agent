# Agent Module Interface

Public API and schema contracts for agent lifecycle management, BuildPlan generation, controlled execution, read-only manifest provenance, source-authority contract, validated module-path resolution, and the read-only ContextBundle dry-run consumer.

## ContextBundle Dry-Run Consumer (WRE_CONTEXT_BUNDLE_DRYRUN_CONSUMER_PHASE1)

First consumer wiring of the read-only #775 ContextBundle into the EXISTING
dry-run evidence path. STANDALONE and return-value-only: it consumes a
ContextBundle as its TRUSTED input and RETURNS a typed `DryRunResult`
describing what a FoundUp dry-run WOULD do. It performs NO live build, NO real
execution, NO subprocess, NO Hermes real delegation, NO executor sink, NO FAM
event, and NO file write. It is NOT plumbed into the live OpenClaw/WRE loop
(runtime wiring is a separate Phase-2 slice).

```python
# modules/foundups/agent/src/context_bundle_dry_run_consumer.py  (NEW)

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from modules.communication.moltbot_bridge.src.foundup_job_contract import FoundUpJob
from modules.foundups.agent.src.context_bundle_builder import ContextBundle


@dataclass(frozen=True)
class PlannedAction:
    """A build/test action the dry-run WOULD run -- declared, never executed."""
    name: str
    argv: Optional[Tuple[str, ...]]   # declared tokens; never executed
    would_mutate: bool
    executed: bool                    # ALWAYS False


@dataclass(frozen=True)
class DryRunResult:
    """Return-value-only dry-run preview. No side effects produced it."""
    consumer_version: str
    bundle_id: str
    foundup_id: str
    resolved_module_path: str         # validated canonical; never a payload value
    source_authority: str             # always "monorepo_poc"
    planned_actions: Tuple[PlannedAction, ...]
    gates_to_recheck: Tuple[str, ...]  # gate NAMES; never pass-state
    readiness_flags: Dict[str, bool]   # echoed; all False
    evidence_refs: Tuple[Dict[str, Any], ...]  # path+sha256+size+role; NO bodies
    rejected_input: Dict[str, Any]     # observable-ignore of any payload value
    dry_run: bool = True
    real_execution_performed: bool = False
    def to_dict(self) -> Dict[str, Any]: ...


class DryRunConsumerRejected(Exception):
    """Raised on non-monorepo_poc authority, resolver mismatch, promoted
    readiness, external-agent-allowed, or cross-FoundUp payload substitution.
    The consumer NEVER returns a DryRunResult on rejection."""


def consume_context_bundle_dry_run(
    bundle: ContextBundle,
    *,
    job: Optional[FoundUpJob] = None,
    repo_root: Optional[Path] = None,
) -> DryRunResult:
    """Consume a trusted ContextBundle and RETURN a dry-run preview.

    - The bundle is the TRUSTED input; trust is NOT re-derived from a payload.
    - module_path is ALWAYS the bundle's validated canonical value. When a
      ``job`` is supplied, the SHARED ``_resolve_validated_module_path``
      (#778/#779) re-validates defensively and its effective path MUST match
      the bundle's; the payload candidate is observable-ignore only.
    - source_authority MUST equal "monorepo_poc" (no stage promotion).
    - required_gates are NAMES to re-check, never pass-state.
    - dry_run=True / real_execution_performed=False; no sink invoked.
    """
```

## Shared Module-Path Resolver (BUILD_PLAN_GENERATOR_MODULE_PATH_TRUST_REMOVAL_PHASE1)

The validated-module-path resolver originally introduced in
[`hermes_foundup_job_executor.py`](src/hermes_foundup_job_executor.py) by #778
has been EXTRACTED into a shared module -- single source of truth for the
module-path trust rule across the agent module.

```python
# modules/foundups/agent/src/module_path_resolution.py  (NEW in this slice)

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ResolvedModulePath:
    """Observable-ignore shape mirroring source_authority.resolve_source_authority.
    Identical to the #778 surface; moved verbatim."""
    effective: Optional[str]
    ignored: Optional[str]
    failed: bool
    fail_token: Optional[str]
    fail_human: str


def _resolve_validated_module_path(
    job: FoundUpJob, repo_root: Path,
) -> ResolvedModulePath:
    """Resolve a job's module_path through the #773 validator. Fail-closed.
    
    Pinned design unchanged from #778. Closed-set tokens:
    {syntactic_reject, manifest_mismatch, manifest_missing, cross_foundup_mismatch}.
    """


# Plus DEFAULT_REPO_ROOT, _MANIFEST_SEARCH_GLOBS, the four FAIL_TOKEN_* constants,
# ALL_FAIL_TOKENS, _stringify_ignored, _find_manifest_for_foundup_id.
```

### Behavior-preserving back-compat shim (Addendum C #3)

The Hermes executor re-exports every name so existing imports keep working
with **zero edits** in `test_hermes_foundup_job_executor.py` (proven by a
46-test pass after extraction):

```python
# modules/foundups/agent/src/hermes_foundup_job_executor.py
from modules.foundups.agent.src.module_path_resolution import (  # noqa: F401
    ALL_FAIL_TOKENS,
    DEFAULT_REPO_ROOT,
    FAIL_TOKEN_CROSS_FOUNDUP_MISMATCH,
    FAIL_TOKEN_MANIFEST_MISMATCH,
    FAIL_TOKEN_MANIFEST_MISSING,
    FAIL_TOKEN_SYNTACTIC_REJECT,
    ResolvedModulePath,
    _find_manifest_for_foundup_id,
    _MANIFEST_SEARCH_GLOBS,
    _resolve_validated_module_path,
    _stringify_ignored,
)
```

Identity is preserved: `hermes_foundup_job_executor._resolve_validated_module_path
is module_path_resolution._resolve_validated_module_path` is `True`.
`build_plan_generator` imports the SAME function from the shared module.
The single-source-of-truth invariant is mechanically pinned by AST scans
on both files (`TestSharedResolverIsSingleSourceOfTruth`).

## BuildPlan Generator -- Validated Resolution (BUILD_PLAN_GENERATOR_MODULE_PATH_TRUST_REMOVAL_PHASE1)

The build_plan_generator no longer trusts raw `payload.module_path` /
`source_module`, no longer infers from `KNOWN_FOUNDUP_PATHS` (deleted as
dead code), no longer synthesizes `modules/foundups/{foundup_id}` (deleted),
and no longer uses the prefix-only `.lower()` `_is_valid_foundup_path`
gate (deleted). All module-identity flows through the shared resolver.

```python
# modules/foundups/agent/src/build_plan_generator.py

@dataclass
class GenerationValidationResult:
    """Result of job validation for BuildPlan generation."""
    valid: bool
    error_code: Optional[str] = None                  # closed-set #778 tokens on resolver failure
    error_message: Optional[str] = None
    inferred_module_path: Optional[str] = None        # manifest-derived canonical (None on failure)
    rejected_payload_value: Optional[str] = None      # observable-ignore (mirrors resolver.ignored)


def validate_job_for_build_plan(
    job: FoundUpJob, repo_root: Optional[Path] = None,
) -> GenerationValidationResult:
    """Pre-gate (MISSING_FOUNDUP_ID / UNSUPPORTED_ACTION / UNKNOWN_ACTION)
    then the shared resolver. ``error_code`` on resolver failure is one of
    {syntactic_reject, manifest_mismatch, manifest_missing, cross_foundup_mismatch}."""


def build_target_from_job(
    job: FoundUpJob, repo_root: Optional[Path] = None,
) -> BuildTarget:
    """ALWAYS calls the resolver and uses the canonical ``effective``
    module_path. PWA-surface ruling: DERIVED_ONLY -- ``pwa_surface_path``
    is derived from the canonical module_path's basename; payload-supplied
    surface paths are NOT trusted as module identity."""
```

### KNOWN_FOUNDUP_PATHS retention ruling

**DELETE_AS_DEAD_CODE.** Phase-0 census found 2 PATH_IDENTITY_USE sites
(both removed by this slice) and 1 DISPLAY_CATALOG_USE inline error
string co-located inside the severed branch. Zero non-test cross-module
callers. The constant and its `get_known_foundup_path()` wrapper are gone.

### PWA-surface ruling

**DERIVED_ONLY.** `BuildTarget.pwa_surface_path` is derived as
`f"public/member/foundups/{module_basename}/"` where `module_basename`
is the last segment of the resolver's canonical `module_path`. The
legacy admit of `public/member/foundups/<id>` paths as module identity
is gone -- they reject at `syntactic_reject` because they don't
`startswith("modules/")`.

### Greppable failure tokens (closed set, unchanged from #778)

```python
FAIL_TOKEN_SYNTACTIC_REJECT       = "syntactic_reject"
FAIL_TOKEN_MANIFEST_MISMATCH      = "manifest_mismatch"
FAIL_TOKEN_MANIFEST_MISSING       = "manifest_missing"
FAIL_TOKEN_CROSS_FOUNDUP_MISMATCH = "cross_foundup_mismatch"
```

### Consumer-wiring precondition status

This slice closes the last #778 carry-forward (the
build_plan_generator trust surface that was OUT_OF_SCOPE_NAMED_FOLLOWUP
in #778's ruling). `WRE_CONTEXT_BUNDLE_DRYRUN_CONSUMER_PHASE1` no
longer needs to gate on a generator hardening precondition; the single
source of truth is in place across both consumers.

## Validated Module-Path Resolution (HERMES_MODULE_PATH_TRUST_REMOVAL_PHASE1)

Closes the #774 carry-forward by forcing every job's `module_path` through the
#773 manifest validator before the Hermes executor's subprocess sink is reached.
This is the LAST consumer-wiring precondition.

```python
# modules/foundups/agent/src/hermes_foundup_job_executor.py
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ResolvedModulePath:
    """Outcome of validated module-path resolution. Observable-ignore shape."""
    effective: Optional[str]              # canonical module_path from validated manifest
    ignored: Optional[str]                # stringified payload-declared value (None iff no declaration)
    failed: bool
    fail_token: Optional[str]             # closed-set greppable token, or None on success
    fail_human: str                       # token-prefixed explanation; empty on success


def _resolve_validated_module_path(
    job: FoundUpJob,
    repo_root: Path,
) -> ResolvedModulePath:
    """Resolve a job's module_path through the #773 validator. Fail-closed.

    Pinned design:
    - candidate = payload.module_path | payload.source_module (alias).
    - empty-string is ABSENT (Addendum D #4).
    - foundup_id-as-path heuristic REMOVED ("/" in foundup_id is never a source).
    - syntactic hardening BEFORE manifest contact: backslashes / absolute /
      UNC / ".." traversal / not-under-modules/ all reject pre-manifest.
    - manifest located: <repo_root>/<canonical>/foundup_manifest.json, OR
      bounded foundup_id scan when candidate absent.
    - validator gate: validate_manifest_file (#773); never raises.
    - cross-FoundUp substitution defense (Addendum D #1, load-bearing):
      the manifest's foundup_id MUST equal job.foundup_id; otherwise reject.
    - case-variant defense (Addendum D #3): candidate canonical exact-string
      compared against manifest canonical (case-sensitive).
    - observable ignored: payload-declared value visible in result.ignored
      even on success (mirrors source_authority.resolve_source_authority).
    """
```

### Greppable failure-mode tokens

`StatusReasonCode` stays frozen at `FAIL_VALIDATION_ERROR`; granularity is
emitted as a token prefix on `reason_human` plus a parallel
`evidence_refs` entry (`fail_token:<token>`):

```python
FAIL_TOKEN_SYNTACTIC_REJECT       = "syntactic_reject"        # absolute / UNC / .. / backslash / not-under-modules/
FAIL_TOKEN_MANIFEST_MISMATCH      = "manifest_mismatch"       # validator returned shape error or candidate != manifest canonical
FAIL_TOKEN_MANIFEST_MISSING       = "manifest_missing"        # file not found / unreadable / JSON-invalid
FAIL_TOKEN_CROSS_FOUNDUP_MISMATCH = "cross_foundup_mismatch"  # manifest foundup_id != job.foundup_id

ALL_FAIL_TOKENS: frozenset = frozenset({
    "syntactic_reject", "manifest_mismatch", "manifest_missing", "cross_foundup_mismatch",
})
```

### Evidence-trail contract (`execute_foundup_job` failure path)

When the resolver fails, `execute_foundup_job` calls
`job.fail(reason_code=FAIL_VALIDATION_ERROR, reason_human=resolved.fail_human,
evidence_refs=evidence)` BEFORE `job.start(...)`, so the subprocess sink
(`HermesFoundUpBuilder.run_hermes_extraction` per the #774 audit) is
never reached. The evidence list includes:

- `rejected_payload_value:<stringified declaration>` (only if the payload
  actually declared something), and
- `fail_token:<one of ALL_FAIL_TOKENS>` (always).

### Consumer-wiring precondition status

This slice satisfies the #774 carry-forward at the Hermes executor seam.
The follow-up `BUILD_PLAN_GENERATOR_MODULE_PATH_TRUST_REMOVAL_PHASE1`
(Phase-0 ruling: `OUT_OF_SCOPE_NAMED_FOLLOWUP`, Addendum B/D tie-break:
"current reachability decides") is a hard precondition for
`WRE_CONTEXT_BUNDLE_DRYRUN_CONSUMER_PHASE1` or any other slice that
makes `build_plan_generator` reachable from a real-execution sink.

## Source-Authority Contract (FOUNDUP_LIFECYCLE_SOURCE_AUTHORITY_CONTRACT_PHASE1)

Contract doc: [docs/architecture/FOUNDUP_SOURCE_AUTHORITY_CONTRACT.md](../../../docs/architecture/FOUNDUP_SOURCE_AUTHORITY_CONTRACT.md).

```python
# modules/foundups/agent/src/source_authority.py
import enum
from typing import NoReturn, Optional, Tuple, Union


class SourceAuthority(str, enum.Enum):
    """The five source-authority stages defined by the Phase-1 contract.
    Exactly 5 members; string values are EXACT and stable."""
    MONOREPO_POC   = "monorepo_poc"     # ACTIVE in Phase-1
    EXTERNAL_PROTO = "external_proto"   # defined; UNREACHABLE in Phase-1
    MVP_RUNTIME    = "mvp_runtime"      # defined; UNREACHABLE in Phase-1
    DAO_MANAGED    = "dao_managed"      # defined; UNREACHABLE in Phase-1
    ARCHIVED       = "archived"         # defined; UNREACHABLE in Phase-1


# Exactly one entry in Phase-1. Downstream code may compare against this set
# to decide whether to proceed without crossing the Phase-1 boundary.
ACTIVE_STAGES: frozenset = frozenset({SourceAuthority.MONOREPO_POC})


def resolve_source_authority(
    declared: Optional[Union[str, SourceAuthority]] = None,
) -> Tuple[SourceAuthority, Optional[str]]:
    """Resolve the effective source-authority stage. ALWAYS returns MONOREPO_POC.

    NEVER raises. NEVER trusts ``declared``. Returns
    ``(MONOREPO_POC, ignored_declaration_stringified_or_None)``. The
    caller can observe the second element to detect a (potentially
    malicious) declaration attempt. Garbage input (wrong type, casing
    variants, control chars, ints, dicts) is treated identically:
    ignored and reported.
    """


def request_promotion(
    target: Union[str, SourceAuthority],
) -> NoReturn:
    """Promotion request. ALWAYS raises NotImplementedError in Phase-1.

    Promotion is not a function call; it is a multi-WSP multi-evidence
    event (sovereign-valve decision + federation/OPO/SmartDAO gate +
    CABR readiness + signed evidence envelope). None implemented here.
    The error message points readers at the contract doc.
    """
```

### The hard rule (verbatim, load-bearing)

> A context bundle / manifest must be lifecycle-aware but CANNOT promote
> its lifecycle stage by declaration; promotion requires evidence + WSP
> gate + CABR / DAO proof. A declared stage from any manifest / external
> input is NEVER trusted.

Phase-1 enforcement:

- `SOURCE_AUTHORITY` is a BUILDER constant
  ([context_bundle_builder.py:132](src/context_bundle_builder.py#L132)),
  NOT read from any manifest. The enum module's
  `SourceAuthority.MONOREPO_POC.value` is value-parity tested against
  this constant (drift guard; the enum is NOT yet wired into the builder
  -- see follow-up `SOURCE_AUTHORITY_BUILDER_ENUM_UNIFICATION_PHASE2`).
- `resolve_source_authority(declared)` ALWAYS returns MONOREPO_POC.
- `request_promotion(target)` ALWAYS raises `NotImplementedError`.
- The laundering-fix precedent (`96314ab6c`) is why this is enforced
  in code, not by guideline.

### Citation triad

- WSP 27 Section 11 (canonical maturity lifecycle).
- WSP 103 lines 616-617 (Pre-OPO `F0_DAE` / Post-OPO `F1_OPO+` gate).
- WSP 109 lines 42, 89-103, 350-360 (RedDog intake actor; `entity_type`).

## ContextBundle Builder (WRE_CONTEXT_BUNDLE_BUILDER_PHASE1)

```python
# modules/foundups/agent/src/context_bundle_builder.py
from pathlib import Path

def build_context_bundle(
    manifest_path: Path,
    repo_root: Path,
    *,
    created_at: str,                # REQUIRED non-empty; injected, not wall-clock
    max_context_bytes: int = 65536, # total cap, fail-closed
) -> ContextBundle:
    """Build a read-only ContextBundle from a validated manifest.

    Calls modules.foundups.agent.src.foundup_manifest_validator
    .validate_manifest_file BEFORE trusting build_contract.module_path
    (PR #773). Imports the validator; does NOT reimplement it.

    Raises ContextBundleRejected on validation failure, readiness
    promotion, non-declarative routing, external_agent_allowed=True,
    can_self_authorize=True, module_path escape, or any safety refusal.
    The builder NEVER produces a bundle on rejection.
    """
```

### ContextBundle Dataclasses (frozen, read-only)

```python
@dataclass(frozen=True)
class FileRef:
    path: str            # repo-relative POSIX
    sha256: str          # 64-hex lowercase, stream-computed
    size_bytes: int
    role: str            # "manifest" | "readme" | "interface" | "modlog" |
                         # "roadmap" | "testmodlog" | "requirements" | "test"

@dataclass(frozen=True)
class ProvenanceRecord:
    builder_version: str
    validator_module_path: str
    validator_sha256: str
    repo_root: str
    source_manifest_sha256: str
    wsps_applied: Tuple[str, ...]

@dataclass(frozen=True)
class ContextBundle:
    bundle_version: str
    bundle_id: str                       # sha256-derived, deterministic
    created_at: str                      # injected by caller
    source_manifest_path: str
    source_manifest_sha256: str
    foundup_id: str
    module_path: str                     # canonical, repo-relative POSIX
    contract_version: str
    build_contract_status: str
    execution_routing_summary: Dict[str, Any]
    dry_run_required: bool
    readiness_flags: Dict[str, bool]     # echoed verbatim; NEVER promoted
    required_gates_to_recheck: Tuple[str, ...]  # NAMES only, not booleans
    forbidden_paths: Tuple[str, ...]
    safe_mutation_surface: Tuple[str, ...]
    included_file_refs: Tuple[FileRef, ...]      # refs + sha256 only; NO bodies
    excluded_paths_summary: Dict[str, int]       # reason -> count
    max_context_bytes: int
    total_referenced_bytes: int                  # <= max_context_bytes
    validator_result_summary: Dict[str, Any]
    provenance: ProvenanceRecord
    def to_dict(self) -> Dict[str, Any]: ...
```

### WSP 97 Truth Boundaries (ContextBundle)

- Read-only. No subprocess / Popen / os.system / eval / exec /
  dynamic import / network / runtime command execution.
- File bodies are NEVER included; only path + sha256 + size + role.
- Hashes are stream-computed in 64 KiB chunks; oversized files
  (> `PER_FILE_READ_CAP_BYTES`, default 4 MiB) are recorded as excluded
  without ever opening the body.
- `max_context_bytes` enforced fail-closed; over-cap candidates are
  recorded under `excluded_paths_summary["over_total_cap"]`, never
  silently truncated.
- Symlinks that resolve outside `module_root` (after `Path.resolve()`)
  are excluded.
- Forbidden paths excluded by segment screen: `.env*`, `main.py`,
  `*_dae.py`, `vendor/`, `wallet/`, `token/`, `reward/`, `payout/`,
  `cabr/`, `blockchain/`, `credentials*`, `secrets*`.
- `bundle_id = sha256(source_manifest_sha256 + "|" + module_path + "|" + bundle_version)`.
  Deterministic. `created_at` is recorded but is NOT part of the
  bundle_id fingerprint.
- Bundle NEVER serializes gate pass-or-fail authority: no
  `gate_passed` / `security_passed` / `permission_passed` /
  `dry_run_passed` / `build_ready` / `autonomous_execution_ready` /
  `cabr_ready` / `payout_ready` / `dao_ready = True` fields.
- This module does NOT call Hermes / OpenClaw / WRE consumer / AI
  Overseer / FoundUpJob queue. The bundle's `module_path` is sourced
  from the validated manifest only -- never from an external job
  payload (#774 carry-forward).

## BuildPlan Pipeline (OC8/OC9/OC12)

### Core Dataclasses

```python
# modules/foundups/agent/src/build_plan.py
BuildPlan        # Multi-step orchestration contract
BuildTarget      # Target paths and scope
BuildStep        # Step definition with action enum
BuildGate        # Gate checkpoints (genesis, dry_run, human_approval)
BuildEvidence    # Evidence reference with verification status
```

### BuildPlan Generator

```python
# modules/foundups/agent/src/build_plan_generator.py
def create_build_plan_from_job(job: FoundUpJob) -> BuildPlan:
    """Generate BuildPlan from FoundUpJob. Always produces dry_run=True plans."""

def can_generate_build_plan(job: FoundUpJob) -> bool:
    """Check if job can generate a BuildPlan."""
```

### BuildPlan Executor (Interface Stub)

```python
# modules/foundups/agent/src/build_plan_executor.py
class BuildPlanExecutor:
    """Controlled step execution. Real execution NOT implemented."""
    
    def __init__(self, dry_run: bool = True): ...
    def validate_plan(self, plan: BuildPlan) -> ValidationResult: ...
    def evaluate_gate(self, plan: BuildPlan, gate_type: GateType) -> GateEvaluationResult: ...
    def simulate_step(self, plan: BuildPlan, step: BuildStep) -> StepExecutionResult: ...
    def execute_step(self, plan: BuildPlan, step: BuildStep) -> StepExecutionResult: ...
    def create_execution_receipt(self, plan: BuildPlan, results: List[StepExecutionResult]) -> ExecutionReceipt: ...

# Execution Result Types
StepExecutionStatus  # SUCCEEDED | FAILED | BLOCKED | SKIPPED | SIMULATED
ExecutionReceipt     # Terminal receipt with WSP 97 truth fields
```

### WSP 97 Truth Fields

ExecutionReceipt enforces these fields as False always:
- `verification_complete = False`
- `cabr_ready = False`
- `payout_ready = False`
- `real_execution_performed = False`

---

## Swarm Coordination (OC13)

### SwarmCoordinator

```python
# modules/foundups/agent/src/build_plan_swarm.py
class SwarmCoordinator:
    """Multi-agent step assignment and file ownership coordination."""
    
    def register_worker(self, worker: WorkerIdentity) -> None: ...
    def assign_step(self, step: BuildStep, worker_id: str, owned_files: list[str]) -> StepAssignment: ...
    def claim_files(self, worker_id: str, files: list[str], step_id: str) -> list[FileOwnershipClaim]: ...
    def release_files(self, worker_id: str, files: list[str]) -> None: ...
    def detect_conflicts(self) -> list[ConflictReport]: ...
    def renew_lease(self, lease_id: str) -> Lease: ...
    def expire_leases(self, now: datetime) -> list[str]: ...
    def aggregate_evidence(self) -> EvidenceBundle: ...
    def summarize(self) -> SwarmExecutionSummary: ...
```

### Coordination Dataclasses

```python
WorkerIdentity      # Worker ID, type, capabilities, lease
StepAssignment      # Step-to-worker assignment (simulated=True always)
FileOwnershipClaim  # File ownership with expiration
Lease               # Worker lease with renewal
ConflictReport      # File ownership conflict
EvidenceBundle      # Aggregated evidence refs
SwarmExecutionSummary  # Execution state summary
```

### Coordination Enums

```python
AssignmentStatus     # ASSIGNED | IN_PROGRESS | COMPLETED | FAILED | CANCELLED
LeaseStatus          # ACTIVE | EXPIRED | RELEASED
ConflictSeverity     # WARNING | ERROR | FATAL
WorkerCapability     # VALIDATE | BUILD | TEST | ALL
```

### Coordination Rules

| Rule | Description |
|------|-------------|
| R1 | Two workers cannot own same file simultaneously |
| R2 | Claims must be within BuildPlan target scope |
| R3 | Lease expiration releases file claims |
| R4 | Assignments are simulated only |

### Swarm WSP 97 Truth Fields

- `StepAssignment.simulated = True` (always)
- `EvidenceBundle.verification_complete = False` (always)
- `EvidenceBundle.cabr_ready = False` (always)
- `SwarmExecutionSummary.all_simulated = True` (always)
- `SwarmExecutionSummary.real_execution_performed = False` (always)

---

## Swarm WRE Queue (OC15)

### SwarmWorkerQueue

```python
# modules/foundups/agent/src/build_plan_swarm_queue.py
class SwarmWorkerQueue:
    """Queue for swarm worker assignment dispatch."""
    
    def enqueue_assignment(self, assignment: StepAssignment, priority: QueuePriority, step_action: BuildStepAction) -> QueueAssignmentResult: ...
    def dequeue_for_worker(self, request: WorkerDequeueRequest) -> WorkerDequeueResult: ...
    def heartbeat(self, worker_id: str, entry_id: str) -> WorkerHeartbeat: ...
    def complete_assignment(self, report: AssignmentCompletionReport) -> QueueAssignmentResult: ...
    def expire_entries(self, now: datetime) -> list[str]: ...
    def list_entries(self, status: QueueEntryStatus) -> list[SwarmWorkerQueueEntry]: ...
```

### Queue Dataclasses

```python
SwarmWorkerQueueEntry  # Queue entry with status, lease, evidence
WorkerDequeueRequest   # Worker request with capabilities
WorkerDequeueResult    # Dequeue result with assigned entries
WorkerHeartbeat        # Heartbeat response with lease renewal
AssignmentCompletionReport  # Completion report with evidence
QueueAssignmentResult  # Operation result
```

### Queue Enums

```python
QueuePriority     # CRITICAL | HIGH | NORMAL | LOW
QueueEntryStatus  # QUEUED | PROCESSING | COMPLETED | FAILED | EXPIRED
DequeueDecision   # ASSIGNED | NO_MATCH | QUEUE_EMPTY | BLOCKED
CompletionStatus  # SUCCEEDED | FAILED | SKIPPED
```

### Capability Matching

| Step Action | Required Capability |
|-------------|---------------------|
| VALIDATE_* | validate |
| CREATE_*, UPDATE_* | build |
| RUN_TESTS | test |

### Queue Lifecycle

```
Enqueue → QUEUED → Dequeue → PROCESSING → Complete → COMPLETED
                       ↓ (lease expired)
                    Requeue → QUEUED (if retriable)
                       ↓
                    EXPIRED (if max retries)
```

### Queue WSP 97 Truth Fields

- `SwarmWorkerQueueEntry.simulated = True` (always)
- `AssignmentCompletionReport.simulated = True` (always)
- No `real_execution_performed` field exists
- No CABR/reward/payout/token fields

---

## Worker Assignment Protocol (OC17)

### AssignmentDispatcher

```python
# modules/foundups/agent/src/worker_assignment_protocol.py
class AssignmentDispatcher:
    """Dispatches SwarmWorkerQueue assignments to worker processes."""
    
    def register_worker(self, registration: WorkerRegistration) -> WorkerProcess: ...
    def deregister_worker(self, worker_id: str) -> WorkerDeregistration: ...
    def dispatch_assignment(self, request: AssignmentDispatchRequest) -> AssignmentDispatchResult: ...
    def receive_heartbeat(self, event: WorkerHeartbeatEvent) -> WorkerProcess: ...
    def receive_completion(self, event: WorkerCompletionEvent) -> AssignmentDispatchResult: ...
    def list_workers(self, status: WorkerProcessStatus | None) -> list[WorkerProcess]: ...
```

### Protocol Dataclasses

```python
WorkerProcess           # Registered worker with status, capabilities
WorkerRegistration      # Worker registration request
WorkerDeregistration    # Deregistration result
AssignmentDispatchRequest   # Dispatch request with step details
AssignmentDispatchResult    # Dispatch result (simulated)
WorkerHeartbeatEvent    # Heartbeat from worker
WorkerCompletionEvent   # Completion report with evidence
```

### Protocol Enums

```python
WorkerProcessStatus      # IDLE | ASSIGNED | PROCESSING | FAILED | TERMINATED
WorkerRuntimeType        # OPENCLAW | HERMES | CLAUDE_0102 | QWEN | GEMMA | GENERIC
AssignmentDispatchStatus # SIMULATED_DISPATCH | SPECIFIED_NOT_IMPLEMENTED | WORKER_NOT_FOUND | ...
WorkerTrustLevel         # UNTRUSTED | VERIFIED | TRUSTED | SYSTEM
```

### Protocol WSP 97 Truth Fields

- `WorkerProcess.simulated = True` (always)
- `AssignmentDispatchResult.simulated = True` (always)
- `AssignmentDispatchResult.real_process_started = False` (always)
- `WorkerCompletionEvent.simulated = True` (always)
- No CABR/reward/payout/token fields

---

## Swarm Dispatch Integration (OC18)

### SwarmDispatchCoordinator

```python
# modules/foundups/agent/src/swarm_dispatch_integration.py
class SwarmDispatchCoordinator:
    """Coordinates between SwarmWorkerQueue and AssignmentDispatcher."""
    
    def __init__(self, queue: SwarmWorkerQueue, dispatcher: AssignmentDispatcher): ...
    def dispatch_next(self, worker_id: str) -> DispatchCycleResult: ...
    def complete_dispatched_assignment(self, worker_id: str, entry_id: str, evidence_refs: list[str]) -> DispatchCycleResult: ...
    def run_simulated_cycle(self, worker_id: str, evidence_refs: list[str] | None) -> DispatchCycleResult: ...
    def summarize(self) -> QueueDispatchSummary: ...
```

### Integration Dataclasses

```python
DispatchCycleResult     # Result of dispatch cycle (simulated)
QueueDispatchSummary    # Queue/dispatcher state summary
```

### Integration Enums

```python
DispatchCycleStatus     # SUCCESS | NO_QUEUED_ENTRIES | NO_CAPABILITY_MATCH | ...
```

### Integration WSP 97 Truth Fields

- `DispatchCycleResult.simulated = True` (always)
- `DispatchCycleResult.real_process_started = False` (always)
- `QueueDispatchSummary.all_simulated = True` (always)
- `QueueDispatchSummary.real_execution_performed = False` (always)
- No CABR/reward/payout/token fields

---

## Worker Queue Observability (OC20)

### WorkerQueueObservability

```python
# modules/foundups/agent/src/worker_queue_observability.py
class WorkerQueueObservability:
    """Observability system for SwarmWorkerQueue telemetry."""
    
    def emit_event(self, event: WorkerQueueEvent) -> WorkerQueueEvent: ...
    def emit_heartbeat(self, worker_id: str, entry_id: str | None) -> WorkerQueueEvent: ...
    def emit_lease_expired(self, entry_id: str, worker_id: str, reason: str) -> WorkerQueueEvent: ...
    def emit_worker_available(self, worker_id: str, capabilities: list[str]) -> WorkerQueueEvent: ...
    def emit_worker_unavailable(self, worker_id: str, reason: str) -> WorkerQueueEvent: ...
    def snapshot_queue_health(self, queue: SwarmWorkerQueue) -> QueueHealthSnapshot: ...
    def get_events(self, worker_id: str | None) -> list[WorkerQueueEvent]: ...
```

### Observability Dataclasses

```python
WorkerQueueEvent        # Base event with timestamp, worker_id, entry_id, evidence_refs
WorkerHeartbeatSnapshot # Heartbeat state with consecutive count
LeaseExpirySignal       # Lease expiration details
WorkerAvailabilitySnapshot  # Worker availability state
QueueHealthSnapshot     # Queue health with entry counts
```

### Observability Enums

```python
WorkerQueueEventType    # HEARTBEAT | LEASE_EXPIRED | WORKER_AVAILABLE | ...
WorkerAvailabilityStatus # AVAILABLE | BUSY | OFFLINE | TERMINATED
QueueHealthStatus       # HEALTHY | DEGRADED | UNHEALTHY
```

### WSP 91 Compliance

| Pillar | Implementation |
|--------|----------------|
| Logs | emit_* methods create discrete events |
| Traces | Not implemented (Phase 2) |
| Metrics | snapshot_* methods for aggregated state |

### Observability WSP 97 Truth Fields

- Events are in-memory only (Phase 1)
- Events are append-only
- No real_execution_performed field exists
- No CABR/reward/payout/token fields

---

## Event Schemas

### agent_joins

Emitted when agent enters the ecosystem in dormant 01(02) state.

```python
{
    "event_type": "agent_joins",
    "actor_id": "founder_001",           # Unique agent identifier
    "foundup_id": "F_0",                 # FoundUp context (F_0 = ecosystem-level)
    "payload": {
        "agent_type": "founder",         # founder | user
        "public_key": "0xfoundup001...", # Wallet address
        "rank": 1,                       # Initial rank (1=Apprentice)
        "state": "01(02)",               # Dormant until awakened
        "foundup_idx": 0,                # FoundUp index for display
    }
}
```

### agent_awakened

Emitted when agent transitions to 0102 zen state (coherence >= 0.618).

```python
{
    "event_type": "agent_awakened",
    "actor_id": "founder_001",
    "foundup_id": "F_0",
    "payload": {
        "coherence": 0.72,               # Coherence score (0.618-1.0)
        "state": "0102",                 # Zen state - active
    }
}
```

### agent_idle

Emitted when agent decays to 01/02 state (inactivity or coherence drop).

```python
{
    "event_type": "agent_idle",
    "actor_id": "founder_001",
    "foundup_id": "F_0",
    "payload": {
        "inactive_ticks": 150,           # Ticks since last activity
        "current_tick": 1000,            # Current simulation tick
        "state": "01/02",                # Decayed - awaiting ORCH
    }
}
```

### agent_ranked

Emitted when agent rank increases.

```python
{
    "event_type": "agent_ranked",
    "actor_id": "founder_001",
    "foundup_id": "F_0",
    "payload": {
        "old_rank": 2,                   # Previous rank (1-7)
        "new_rank": 3,                   # New rank (1-7)
        "old_title": "Builder",          # Previous title
        "new_title": "Contributor",      # New title
    }
}
```

### agent_earned

Emitted when agent receives F_i payout.

```python
{
    "event_type": "agent_earned",
    "actor_id": "founder_001",
    "foundup_id": "F_001",
    "task_id": "task_0042",
    "payload": {
        "amount": 50,                    # F_i tokens earned
        "foundup_idx": 1,                # FoundUp index
        "task_id": "task_0042",          # Task context
    }
}
```

### agent_leaves

Emitted when agent logs off with wallet balance.

```python
{
    "event_type": "agent_leaves",
    "actor_id": "founder_001",
    "foundup_id": "F_0",
    "payload": {
        "public_key": "0xfoundup001...", # Wallet address
        "wallet_balance": 1250.0,        # Final F_i balance
    }
}
```

## State Transitions

### Valid Transitions

```
01(02) → 0102   # agent_awakened (coherence >= 0.618)
0102 → 01/02    # agent_idle (inactivity > threshold OR coherence < 0.618)
01/02 → 0102    # agent_awakened (re-awakening via WSP_00)
```

### Coherence Thresholds

| Threshold | Meaning |
|-----------|---------|
| 0.618 | Minimum for 0102 zen state (golden ratio) |
| 0.50 | Minimum for any activity |
| < 0.50 | Cannot perform actions |

## Dedupe Keys

Each event type has a unique dedupe key pattern:

```
agent_joins:    agent_joins:{agent_id}:{foundup_id}
agent_awakened: agent_awakened:{agent_id}:{timestamp[:19]}
agent_idle:     agent_idle:{agent_id}:{tick // 100}
agent_ranked:   agent_ranked:{agent_id}:{new_rank}
agent_earned:   agent_earned:{agent_id}:{task_id}
agent_leaves:   agent_leaves:{agent_id}:{timestamp[:19]}
```

## Service Boundaries

### AgentLifecycleService (Future)

```python
class AgentLifecycleService:
    """Manage agent state transitions."""

    def join(self, agent_id: str, agent_type: str, public_key: str) -> None:
        """Register agent in 01(02) dormant state."""

    def awaken(self, agent_id: str) -> bool:
        """Transition to 0102 zen state if coherence >= 0.618."""

    def mark_idle(self, agent_id: str, inactive_ticks: int) -> None:
        """Transition to 01/02 decayed state."""

    def rank_up(self, agent_id: str) -> int:
        """Evaluate and update agent rank. Returns new rank."""

    def leave(self, agent_id: str) -> float:
        """Log off agent and return final wallet balance."""

    def get_state(self, agent_id: str) -> str:
        """Return current state: '01(02)', '0102', or '01/02'."""
```

## Integration

### FAMBridge Methods

```python
# In modules/foundups/simulator/adapters/fam_bridge.py
emit_agent_joins(agent_id, agent_type, foundup_id, public_key, rank)
emit_agent_awakened(agent_id, coherence, foundup_id)
emit_agent_idle(agent_id, foundup_id, inactive_ticks, current_tick)
emit_agent_ranked(agent_id, old_rank, new_rank, foundup_id)
emit_agent_earned(agent_id, foundup_id, amount, task_id)
emit_agent_leaves(agent_id, wallet_balance, public_key, foundup_id)
```

### SSE Streaming

Events are streamed via `STREAMABLE_EVENT_TYPES` in `sse_server.py`:

```python
"agent_joins", "agent_awakened", "agent_idle",
"agent_ranked", "agent_earned", "agent_leaves",
```

### Animation Display

Ticker messages in `foundup-cube.js`:

```javascript
agent_joins:    "01(02) 0xfound001... enters (founder)"
agent_awakened: "0102 founder_001 ZEN (0.72)"
agent_idle:     "01/02 founder_001 IDLE (150 ticks)"
agent_ranked:   "founder_001 rank UP: 2→3 (Contributor)"
agent_earned:   "founder_001 earned 50 F₁"
agent_leaves:   "0xfound001... logs off (1250 F_i)"
```

---

## HermesFoundUpBuilder Environment Contract (HERMES_BUILDER_DRYRUN_DEFAULT_SAFETY_PHASE1)

`HermesFoundUpBuilder` (`src/hermes_adapter.py`) is **dry-run by default**. Real filesystem writes
(e.g. `generate_adapters` adapter stubs) require an explicit **double opt-in**:

| Env var | Default | Meaning |
|---------|---------|---------|
| `HERMES_BUILDER_ALLOW_REAL_WRITES` | `0` | Must be `1` to permit any real write |
| `HERMES_BUILDER_DRY_RUN` | unset = dry-run | Must be explicitly `0` to permit any real write |

`self.dry_run` is `False` **only** when `HERMES_BUILDER_ALLOW_REAL_WRITES=1` AND
`HERMES_BUILDER_DRY_RUN=0`. Every other combination (including all-unset) is dry-run. `self.dry_run`
is surfaced in `extract_foundup` / `build_foundup` / `generate_adapters` result dicts and written
back to `FoundUpJob.policy_flags.dry_run_mode` by the executor. Callers that already force dry-run
(`execute_foundup_job(..., force_dry_run=True)`, or `HERMES_BUILDER_DRY_RUN=1`) are unchanged.
