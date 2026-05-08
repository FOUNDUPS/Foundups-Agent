# MCP Manager

**WSP Domain**: `infrastructure` (WSP 3)

## Purpose

Provides auto-discovery, startup, and management of MCP (Model Context Protocol) servers for 0102.

## Key Features

- **Auto-Discovery**: Automatically finds MCP servers in `foundups-mcp-p1/servers/`
- **Auto-Start**: Starts servers on demand (first tool use)
- **Status Tracking**: Shows which servers are running and available tools
- **Simple Interface**: Single menu option in main.py for all MCP services

## Architecture (First Principles)

**Problem**: 0102 needs access to MCP tools without manual server management
**Solution**: Auto-manage servers, provide simple gateway menu

**Occam's Razor**: One menu option -> Status + Tools -> Auto-start on use

## Usage

From main.py menu:
```
14. MCP Services (HoloIndex: [DOT]RUNNING | 6 tools)     | --mcp
```

## Available MCP Servers

### HoloIndex MCP Server
- **Tools**: 6 (semantic search, WSP lookup, 012.txt mining, LinkedIn/X posting)
- **Auto-Start**: Yes
- **Status Tracking**: Real-time PID monitoring

## All-Surface Discovery (MCPA5)

Beyond the runnable FastMCP servers under `foundups-mcp-p1/servers/`, the
manager surfaces the complete `holo_search` triad anchored in WSP 96 Annex A:

| ID | Surface | Runnable | Status | holo_search |
|----|---------|----------|--------|-------------|
| **S1** | `foundups-mcp-p1/servers/holo_index/` | yes | `RUNTIME_LIVE` | real |
| **S2** | `modules/infrastructure/foundups_mcp_bridge/` | no | `RUNTIME_INTERNAL_ONLY` | real_with_fallback |
| **S3** | `modules/infrastructure/pavs_mcp/` | no | `PLACEHOLDER_STUB` | placeholder |
| `AUX:*` | other FastMCP servers (codeindex, wsp_governance, ...) | yes | `RUNTIME_LIVE` | none |

S2 and S3 are reported but never auto-started: S2 has no MCP wire transport
(Python class + CLI only); S3 does not bind a port (`start()` is a sleep loop)
and its tools return hardcoded data. Use `MCPServerManager.report_all_surfaces()`
or `discover_all_surfaces()` to access the truthful list programmatically.

## WSP Compliance

- **WSP 3**: Infrastructure domain (server management)
- **WSP 49**: Full module structure
- **WSP 84**: Auto-management (don't duplicate manual work)
