# MCP Manager - Public API

## Functions

### `show_mcp_services_menu()`
Display MCP Services interactive menu and handle user interactions.

**Usage**:
```python
from modules.infrastructure.mcp_manager.src.mcp_manager import show_mcp_services_menu

# In main.py menu
show_mcp_services_menu()
```

**Returns**: None (interactive menu loop)

## Classes

### `MCPServerManager`
Core manager for MCP server lifecycle and all-surface discovery.

**Lifecycle methods** (runnable servers only):
- `get_server_status(server_name: str) -> Tuple[bool, Optional[int]]`
- `start_server(server_name: str) -> bool`
- `stop_server(server_name: str) -> bool`
- `get_available_tools(server_name: str) -> List[Dict[str, str]]`

**All-surface discovery** (MCPA5 / WSP 96 Annex A):
- `discover_all_surfaces() -> List[KnownSurface]` — return S1+S2+S3 plus any auxiliary FastMCP servers, with truthful flags. Never starts a server.
- `format_surface_report(surfaces=None) -> str` — render the truth-flagged table for stdout/logs.
- `report_all_surfaces() -> List[KnownSurface]` — print and return the canonical list.

### `KnownSurface` (dataclass)
Truthful descriptor for one MCP-related surface. Frozen, JSON-serializable via `to_dict()`.

| Field | Meaning |
|-------|---------|
| `surface_id` | `S1` / `S2` / `S3` / `AUX:<name>` |
| `surface_kind` | `external_mcp_server` / `internal_python_bridge` / `placeholder_stub` / `auxiliary_mcp_server` |
| `name` | Human-readable name |
| `path` | Repo-relative path |
| `runnable` | `True` for processes the manager can start; `False` for non-runnable surfaces |
| `implementation_status` | `RUNTIME_LIVE` / `RUNTIME_INTERNAL_ONLY` / `PLACEHOLDER_STUB` / `UNKNOWN` |
| `holo_search_support` | `real` / `real_with_fallback` / `placeholder` / `none` |
| `authority_role` | `canonical_external_adapter` / `canonical_internal_adapter` / `no_authority` / `auxiliary` |
| `notes` | Short truthful caveat |

### Module-level constants
- `S2_FOUNDUPS_MCP_BRIDGE: KnownSurface` — canonical S2 descriptor
- `S3_PAVS_MCP: KnownSurface` — canonical S3 descriptor
- `KNOWN_NON_RUNNABLE_SURFACES: Tuple[KnownSurface, ...]` — `(S2, S3)`

## Integration Example

```python
# main.py integration
elif choice == "14":
    # MCP Services Gateway
    from modules.infrastructure.mcp_manager.src.mcp_manager import show_mcp_services_menu
    show_mcp_services_menu()
```

## Tool Access (Future)

Future versions will provide direct tool invocation:
```python
manager = MCPServerManager()
manager.call_tool("holo_index", "semantic_code_search", query="DAE architecture")
```
