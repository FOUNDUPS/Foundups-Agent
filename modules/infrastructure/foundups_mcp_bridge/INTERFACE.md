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
