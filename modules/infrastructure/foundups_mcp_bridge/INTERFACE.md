# FoundUps MCP Bridge Interface

## Public API

### FoundUpsMCPBridge

Main bridge class for MCP tool access.

```python
from modules.infrastructure.foundups_mcp_bridge.src import FoundUpsMCPBridge

bridge = FoundUpsMCPBridge(repo_root=Path("O:/Foundups-Agent"))
```

#### `list_tools() -> Dict`

List all available tools with status.

**Returns:**
```python
{
    "status": "ok",
    "data": {
        "tools": [
            {"name": "get_repo_tree", "description": "...", "status": "active"},
            {"name": "coordinate_mission", "description": "...", "status": "disabled_in_v1"},
        ],
        "count": 21,
        "active_count": 15,
        "disabled_count": 6,
    }
}
```

#### `call_tool(tool_name: str, **kwargs) -> Dict`

Call a tool by name with arguments.

**Parameters:**
- `tool_name`: Tool identifier
- `**kwargs`: Tool-specific arguments

**Returns:** MCPResponse dict

#### `get_status() -> Dict`

Get bridge status and capabilities.

---

## Tool Reference

### Repo Perception

#### `get_repo_tree(path=".", depth=3)`

Get directory tree structure.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| path | str | "." | Relative path to start |
| depth | int | 3 | Max traversal depth |

#### `read_file(path)`

Read file content.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| path | str | Yes | Relative file path |

**Limits:** 200KB max, blocked patterns filtered

#### `search_repo(query, path=".", top_k=20)`

Search repository using ripgrep.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| query | str | - | Search regex |
| path | str | "." | Search scope |
| top_k | int | 20 | Max results |

#### `get_recent_changes(limit=50)`

Get git commit history.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | int | 50 | Max commits |

---

### Documentation Access

#### `get_wsp_docs()`

List all WSP protocol documents.

#### `get_module_docs(module_name)`

Get module README.md.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| module_name | str | Yes | Module name |

#### `get_interface_doc(module_name)`

Get module INTERFACE.md.

#### `get_test_docs(module_name)`

Get module test documentation.

#### `get_modlog(limit=20)`

Get recent ModLog entries from root and key modules.

#### `get_violations(limit=20)`

Get known WSP violations and audit issues.

---

### Overseer Perception

#### `get_mission_history(limit=20)`

Get AI Overseer mission records.

**Sources:** SQLite `overseer.db`, JSONL history

#### `get_pattern_memory(limit=50)`

Get learned patterns (WSP 48).

**Sources:** `adaptive_learning/*.json`

#### `get_overseer_status()`

Get current Overseer system status.

**Returns:**
```python
{
    "available": bool,
    "db_exists": bool,
    "pattern_memory_exists": bool,
    "security_monitor_active": bool,
    "wsp_audit_status": {...},
    "last_mission": {...},
}
```

#### `get_coordination_state()`

Get active teams and recent phases.

#### `get_known_failure_patterns(limit=30)`

Get error patterns for avoidance.

---

### Dependency Perception (v1.1)

#### `get_module_dependencies(module_name, include_external=True, max_depth=1)`

Get dependencies for a FoundUps module.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| module_name | str | - | Module name (e.g., "ai_overseer") |
| include_external | bool | True | Include external package dependencies |
| max_depth | int | 1 | Depth of internal dependency traversal |

**Returns:**
```python
{
    "module": str,
    "module_path": str,
    "files_analyzed": int,
    "internal_dependencies": [
        {"module": str, "imported_by": [str], "import_count": int, "confidence": str}
    ],
    "external_dependencies": [
        {"package": str, "imported_by": [str], "import_count": int}
    ],
    "declared_requirements": [str],
}
```

**Confidence values:** `direct_import`, `manifest_declared`, `search_inferred`

#### `get_reverse_dependencies(module_name, search_scope="modules")`

Find modules that depend on the specified module (blast radius analysis).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| module_name | str | - | Module to find dependents of |
| search_scope | str | "modules" | Scope: "modules" or "all" |

**Returns:**
```python
{
    "module": str,
    "dependents": [
        {"module": str, "import_details": [...], "import_count": int}
    ],
    "dependent_count": int,
    "blast_radius": str,  # "isolated", "low", "medium", "high", "critical"
}
```

---

### Diff Perception (v1.1)

#### `get_file_diff(path, commit_range=None)`

Get diff for a specific file.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| path | str | - | Relative file path |
| commit_range | str | None | Git commit range (e.g., "HEAD~3..HEAD") |

**Behavior:**
- If `commit_range` provided: diff across that range
- If omitted: working tree vs HEAD

**Returns:**
```python
{
    "path": str,
    "commit_range": str,
    "has_changes": bool,
    "diff": str,  # Truncated if > 500 lines or 100KB
    "stats": {"additions": int, "deletions": int, "total_changes": int},
    "truncated": bool,
    "commit_info": [{"hash": str, "author": str, "message": str}],
}
```

**Security:** Blocks .env, credentials, secrets, .pem, .key files

#### `get_diff_summary(commit_range, path=".", group_by_module=True)`

Get summary of changes across a commit range.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| commit_range | str | - | Git commit range |
| path | str | "." | Scope path |
| group_by_module | bool | True | Group files by module/domain |

**Returns:**
```python
{
    "commit_range": str,
    "commit_count": int,
    "files_changed": int,
    "overall_stats": {"files_changed": int, "insertions": int, "deletions": int},
    "changed_files": [{"path": str, "status": str}],
    "grouped_by_module": {"domain/module": [str]},
    "commit_messages": [str],
}
```

---

### Impact Prediction (v1.2)

#### `get_change_impact_score(target_type, target)`

Compute blast-radius and risk score for a change target.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| target_type | str | Yes | "module", "file", "diff", or "commit_range" |
| target | str | Yes | Module name, file path, or commit range |

**Returns:**
```python
{
    "target_type": str,
    "target": str,
    "affected_modules": [
        {
            "module": str,
            "risk_weight": float,  # 1.0 = base, higher = more critical
            "is_primary": bool,    # Directly changed vs reverse dep
            "is_critical": bool,   # In CRITICAL_MODULES list
            "internal_dep_count": int,
        }
    ],
    "risk_level": "low" | "medium" | "high" | "critical",
    "risk_score": float,  # 0-1 composite score
    "risk_factors": [str],  # Explanations for risk level
    "test_coverage": {
        "covered": int,
        "total": int,
        "gaps": [str],  # Module names without tests
        "coverage_ratio": float,
    },
    "prior_failures": [
        {
            "pattern": str,
            "last_seen": str,
            "frequency": int,
        }
    ],
    "confidence": float,  # 0-1 based on data completeness
    "confidence_factors": [str],  # What reduced confidence
}
```

**Risk Level Thresholds:**
- `low`: score < 0.3
- `medium`: score 0.3-0.5
- `high`: score 0.5-0.7
- `critical`: score >= 0.85

**Risk Factors Considered:**
1. Number of affected modules (0-0.3)
2. Critical module involvement (0-0.25)
3. Test coverage gaps (0-0.25)
4. Prior failure patterns (0-0.2)

**Critical Modules** (elevated risk weight):
- shared_utilities (1.5x)
- database (1.4x)
- wre_core (1.3x)
- ai_overseer (1.2x)
- foundups_selenium (1.2x)

**Confidence Reduction:**
- No test coverage data: -0.2
- No prior failure data: -0.15
- HoloIndex not available: -0.1
- Many affected modules (>10): -0.1
- Limited dependency resolution: -0.1

---

### Execution Stubs (v1 Disabled)

These tools return `{"status": "disabled_in_v1"}` with schema information.

| Tool | Future Use |
|------|------------|
| `coordinate_mission` | WSP 77 agent coordination |
| `spawn_agent_team` | WSP 54 team creation |
| `trigger_skill` | WRE skill dispatch |
| `write_file` | Audited file writes |
| `create_branch` | Git branch creation |
| `create_pr` | PR creation |

---

## Response Format

### Success
```python
{
    "status": "ok",
    "data": Any,
    "meta": {
        "timestamp": "ISO8601",
        "source": str,
        # tool-specific metadata
    }
}
```

### Error
```python
{
    "status": "error",
    "error": str,
    "meta": {...}
}
```

### Disabled (v1)
```python
{
    "status": "disabled_in_v1",
    "error": "Tool 'X' is disabled in v1...",
    "data": {
        "tool": str,
        "schema": Dict  # Parameter/return schema
    }
}
```

---

## Security Constraints

- Path allowlist enforced
- .env, credentials, secrets blocked
- 200KB file size limit
- No write operations
- No execution
