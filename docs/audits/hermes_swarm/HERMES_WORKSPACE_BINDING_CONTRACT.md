# HERMES_WORKSPACE_BINDING_CONTRACT

**Date**: 2026-05-02  
**Status**: DRAFT  
**Slice**: HERMES_WORKSPACE_BINDING_CONTRACT_PHASE1  
**Type**: Interface Contract Specification

---

## 1. Overview

This document defines how FoundUps WRE passes workspace context to Hermes
delegation. It establishes the contract for path constraints, evidence output,
and failure retention before enabling real delegate_task execution.

**Design Principle**: Hermes subagents must operate within a sandbox defined by
WRE. They cannot access arbitrary paths, cannot write outside designated output
directories, and must produce evidence artifacts in predictable locations.

---

## 2. Workspace Binding Architecture

```
FoundUpJob
    │
    ├─ job_id: "j_build_18a3b2c1_f4e5d6"
    ├─ foundup_id: "gotjunk"
    ├─ tenant_id: "012"
    │
    └─ HermesJobExecutor.build_delegation_request()
            │
            └─ HermesDelegationRequest
                   │
                   ├─ workspace_binding: WorkspaceBinding
                   │       │
                   │       ├─ workspace_root: "/path/to/Foundups-Agent"
                   │       ├─ workspace_hint: "modules/foundups/gotjunk"
                   │       ├─ allowed_paths: [...]
                   │       ├─ blocked_paths: [...]
                   │       ├─ evidence_output_path: ".../evidence/{job_id}/"
                   │       └─ retention_on_failure: "preserve"
                   │
                   └─ [Hermes delegate_task receives hint in WORKSPACE PATH section]
```

---

## 3. WorkspaceBinding Contract

### 3.1 Fields

```python
@dataclass
class WorkspaceBinding:
    """Workspace context for Hermes delegation sandbox."""
    
    # Root directory of FoundUps-Agent repository
    workspace_root: str
    
    # Relative path hint for Hermes (passed in system prompt)
    # Format: "modules/foundups/{foundup_id}" or custom path
    workspace_hint: Optional[str]
    
    # Allowed paths (relative to workspace_root)
    # Hermes may read/write within these paths only
    allowed_paths: List[str]
    
    # Blocked paths (relative to workspace_root)
    # Hermes must NOT read/write these paths, even if in allowed_paths
    blocked_paths: List[str]
    
    # Evidence output directory (absolute path)
    # Format: {workspace_root}/.hermes_evidence/{job_id}/
    evidence_output_path: str
    
    # Retention behavior on job failure
    # "preserve" = keep all artifacts
    # "cleanup" = remove non-evidence artifacts
    # "archive" = compress to .tar.gz and remove originals
    retention_on_failure: str
```

### 3.2 Default Values

| Field | Default | Derivation |
|-------|---------|------------|
| `workspace_root` | `os.getcwd()` or `FOUNDUPS_WORKSPACE_ROOT` env | Auto-detected |
| `workspace_hint` | `modules/foundups/{foundup_id}` | From `job.foundup_id` |
| `allowed_paths` | See Section 4.1 | Action-dependent |
| `blocked_paths` | See Section 4.2 | Security hardcoded |
| `evidence_output_path` | `{workspace_root}/.hermes_evidence/{job_id}/` | From `job.job_id` |
| `retention_on_failure` | `"preserve"` | Audit-safe default |

---

## 4. Path Constraints

### 4.1 Allowed Paths by Action

Each `requested_action` defines its allowed path scope:

| Action | Allowed Paths |
|--------|---------------|
| `build_foundup` | `modules/foundups/{foundup_id}/`, `.hermes_evidence/{job_id}/` |
| `extract_foundup` | `modules/foundups/{foundup_id}/`, `.hermes_evidence/{job_id}/`, `{external_repo_path}/` |
| `validate_foundup` | `modules/foundups/{foundup_id}/` (read-only), `.hermes_evidence/{job_id}/` |
| `queue_foundup_job` | `.hermes_evidence/{job_id}/` (write-only) |

**Generic DAE fallback**: If `foundup_id` is None, allowed_paths is restricted to
`.hermes_evidence/{job_id}/` only.

### 4.2 Blocked Paths (Always)

These paths are NEVER accessible, regardless of action or permissions:

```python
BLOCKED_PATHS = [
    ".env",
    ".env.*",
    "**/.env",
    "**/.env.*",
    "*.pem",
    "*.key",
    "**/secrets/",
    "**/credentials/",
    ".git/config",
    ".git/credentials",
    "**/__pycache__/",
    "vendor/",                  # Hermes cannot modify itself
    ".hermes/",                 # User Hermes config
    "node_modules/",
    ".venv/",
    "venv/",
]
```

### 4.3 Path Validation Rules

1. **Canonicalization**: All paths are resolved to absolute, canonicalized form
   before comparison (no `..` traversal escapes)

2. **Prefix matching**: A path is allowed if it starts with any `allowed_paths`
   entry AND does not match any `blocked_paths` pattern

3. **Glob patterns**: `blocked_paths` supports glob patterns (`*`, `**`, `?`)

4. **Symlink resolution**: Symlinks are resolved before validation; target must
   be within allowed paths

---

## 5. Correlation Fields

### 5.1 Job-to-Workspace Mapping

| Job Field | Workspace Use |
|-----------|---------------|
| `job_id` | Evidence output path: `.hermes_evidence/{job_id}/` |
| `foundup_id` | Workspace hint: `modules/foundups/{foundup_id}/` |
| `tenant_id` | Audit trail: logged in evidence metadata |
| `intent_id` | Correlation: links evidence to originating intent |

### 5.2 Evidence Metadata File

Each job execution creates `.hermes_evidence/{job_id}/metadata.json`:

```json
{
    "job_id": "j_build_18a3b2c1_f4e5d6",
    "foundup_id": "gotjunk",
    "tenant_id": "012",
    "intent_id": "intent_abc123",
    "requested_action": "build_foundup",
    "workspace_root": "/path/to/Foundups-Agent",
    "workspace_hint": "modules/foundups/gotjunk",
    "allowed_paths": ["modules/foundups/gotjunk/", ".hermes_evidence/j_build_18a3b2c1_f4e5d6/"],
    "started_at": "2026-05-02T12:00:00Z",
    "completed_at": "2026-05-02T12:05:00Z",
    "exit_reason": "completed",
    "tool_trace": [...],
    "files_created": ["src/main.py", "README.md"],
    "files_modified": ["foundup_manifest.json"]
}
```

---

## 6. Evidence Output Path

### 6.1 Directory Structure

```
.hermes_evidence/
└── {job_id}/
    ├── metadata.json         # Job correlation and outcome
    ├── stdout.log            # Hermes stdout capture
    ├── stderr.log            # Hermes stderr capture
    ├── tool_trace.jsonl      # Per-tool call audit log
    ├── artifacts/            # Files created by job
    │   └── ...
    └── snapshots/            # Pre/post state snapshots (optional)
        ├── pre.tar.gz
        └── post.tar.gz
```

### 6.2 Path Generation

```python
def get_evidence_output_path(workspace_root: str, job_id: str) -> str:
    """Generate evidence output path for a job."""
    return os.path.join(workspace_root, ".hermes_evidence", job_id)
```

### 6.3 Evidence Gitignore

The `.hermes_evidence/` directory should be gitignored (ephemeral job artifacts):

```gitignore
# .gitignore
.hermes_evidence/
```

---

## 7. Retention Behavior

### 7.1 Retention Modes

| Mode | On Success | On Failure |
|------|------------|------------|
| `preserve` | Keep all | Keep all |
| `cleanup` | Remove non-evidence | Keep all |
| `archive` | Archive then remove | Archive then remove |

### 7.2 Evidence Files (Never Deleted)

These files are preserved regardless of retention mode:

- `metadata.json`
- `tool_trace.jsonl`
- `stderr.log` (on failure)

### 7.3 Cleanup Behavior

```python
def cleanup_job_evidence(job_id: str, mode: str, succeeded: bool) -> None:
    """Apply retention policy to job evidence."""
    evidence_path = get_evidence_output_path(workspace_root, job_id)
    
    if mode == "preserve":
        return  # Keep everything
    
    if mode == "cleanup" and succeeded:
        # Remove stdout.log, artifacts/, snapshots/
        # Keep metadata.json, tool_trace.jsonl
        ...
    
    if mode == "archive":
        # Compress entire directory to {job_id}.tar.gz
        # Remove original directory
        ...
```

---

## 8. WSP 97 Truth Boundaries

This contract is **structural definition only**. It does NOT imply:

- `real_execution_performed`: False (no Hermes execution in this slice)
- `workspace_binding_enforced`: False (enforcement is Phase 2)
- `path_constraints_validated`: False (validation is Phase 2)
- `evidence_collected`: False (evidence collection is Phase 2)
- `verification_complete`: False
- `cabr_ready`: False
- `payout_ready`: False

**What this contract DOES provide**:
- Field definitions for `WorkspaceBinding` dataclass
- Path constraint rules (not enforcement)
- Evidence output path derivation (not creation)
- Correlation field mapping (not verification)

---

## 9. Integration Points

### 9.1 HermesDelegationRequest Extension

```python
@dataclass
class HermesDelegationRequest:
    # ... existing fields ...
    
    # NEW: Workspace binding contract
    workspace_binding: Optional[WorkspaceBinding] = None
```

### 9.2 HermesJobExecutor Extension

```python
class HermesJobExecutor:
    def __init__(
        self,
        # ... existing params ...
        workspace_root: Optional[str] = None,
    ):
        self.workspace_root = workspace_root or self._detect_workspace_root()
    
    def _detect_workspace_root(self) -> str:
        """Detect workspace root from env or cwd."""
        return os.environ.get("FOUNDUPS_WORKSPACE_ROOT", os.getcwd())
    
    def _build_workspace_binding(self, job: FoundUpJob) -> WorkspaceBinding:
        """Build workspace binding from job context."""
        ...
```

### 9.3 Hermes System Prompt Injection

When real execution is enabled (Phase 2+), workspace binding is injected into
Hermes child system prompt:

```
WORKSPACE PATH:
{workspace_binding.workspace_root}/{workspace_binding.workspace_hint}
Use this exact path for local repository/workdir operations.

ALLOWED PATHS:
- modules/foundups/gotjunk/
- .hermes_evidence/j_build_18a3b2c1_f4e5d6/

BLOCKED PATHS:
- .env, .env.*, *.pem, *.key, secrets/, credentials/, vendor/

EVIDENCE OUTPUT:
Write job artifacts to: .hermes_evidence/j_build_18a3b2c1_f4e5d6/artifacts/
```

---

## 10. Testing Contract

Tests MUST verify:

1. `workspace_binding` field exists in `HermesDelegationRequest`
2. `workspace_hint` is derived from `foundup_id`
3. `allowed_paths` are action-dependent
4. `blocked_paths` always include security-sensitive patterns
5. `evidence_output_path` includes `job_id`
6. No real execution occurs (WSP 97 fields remain False)
7. Path patterns do not permit traversal escapes

---

## 11. Future Phases

| Phase | Scope |
|-------|-------|
| Phase 1 (this slice) | Contract definition, field addition, tests |
| Phase 2 | Path validation enforcement in executor |
| Phase 3 | Evidence collection and metadata writing |
| Phase 4 | Real delegate_task execution with sandbox |

---

**Contract authored by**: 0102  
**WSP Compliance**: WSP 11 (Interface), WSP 50 (Pre-Action), WSP 97 (Truth)
