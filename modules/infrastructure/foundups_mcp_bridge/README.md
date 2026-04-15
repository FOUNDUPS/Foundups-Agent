# FoundUps Private MCP Bridge

Private, read-only MCP bridge for AI-assisted architectural execution.

**Version**: 1.4.0 (perception + recall + state compression)

## Purpose

This module provides the **perception layer** for the AI architect workflow:

```
MCP Bridge (perception) → 0102 (reasoning) → 012 (decision) → Cursor (execution)
```

The bridge allows 0102 (ChatGPT) to:
- Inspect repository structure and files
- Access WSP protocol documents
- Read module documentation (README, INTERFACE, ModLog)
- Query AI Overseer state (missions, patterns, failures)
- Generate precise Windsurf prompts based on real repo state

## v1 Capabilities

### Repo Perception (Active)
| Tool | Description |
|------|-------------|
| `get_repo_tree` | Directory structure with depth control |
| `read_file` | File content access (size-limited, path-filtered) |
| `search_repo` | ripgrep-based search |
| `get_recent_changes` | Git commit history |

### Documentation Access (Active)
| Tool | Description |
|------|-------------|
| `get_wsp_docs` | List all WSP protocol documents |
| `get_module_docs` | Module README.md |
| `get_interface_doc` | Module INTERFACE.md (public API) |
| `get_test_docs` | TestModLog and test README |
| `get_modlog` | Recent ModLog entries |
| `get_violations` | Known WSP violations |

### Overseer Perception (Active)
| Tool | Description |
|------|-------------|
| `get_mission_history` | AI Overseer mission records |
| `get_pattern_memory` | Learned patterns (WSP 48) |
| `get_overseer_status` | Current system status |
| `get_coordination_state` | Active teams and phases |
| `get_known_failure_patterns` | Error avoidance patterns |

### Dependency Perception (Active - v1.1)
| Tool | Description |
|------|-------------|
| `get_module_dependencies` | What does module X depend on? |
| `get_reverse_dependencies` | What depends on module X? (blast radius) |

### Diff Perception (Active - v1.1)
| Tool | Description |
|------|-------------|
| `get_file_diff` | What changed in file Y? |
| `get_diff_summary` | What changed across commit range Z? |

### Impact Prediction (Active - v1.2)
| Tool | Description |
|------|-------------|
| `get_change_impact_score` | What is the blast radius? Risk level, test gaps, prior failures |

### HoloIndex Recall (Active - v1.3)
| Tool | Description |
|------|-------------|
| `holo_search` | Semantic search across repo (HoloIndex + ripgrep fallback) |
| `holo_related` | Find modules related to target (deps + semantic + co-change) |
| `holo_failure_memory` | Recall failure patterns from memory |
| `holo_pattern_search` | Search learned patterns (adaptive learning + ChromaDB) |
| `holo_task_packet` | Assemble context packet for a task |

### Signal Normalization (Active - v1.4)
| Tool | Description |
|------|-------------|
| `get_overseer_summary` | Compressed situational awareness (concerns, posture, focus) |
| `get_hot_modules` | Modules ranked by volatility/risk/change frequency |
| `get_repeated_failures` | Clustered recurring failure patterns |
| `get_active_risks` | Normalized risk objects with severity/confidence |
| `get_recommended_focus` | Prioritized next-action recommendations |
| `get_prompt_context_packet` | Auto-assembled context for Windsurf prompts |

### Execution Stubs (Disabled in v1)
| Tool | Status | Future Use |
|------|--------|------------|
| `coordinate_mission` | disabled_in_v1 | Agent team coordination |
| `spawn_agent_team` | disabled_in_v1 | WSP 54 team creation |
| `trigger_skill` | disabled_in_v1 | WRE skill dispatch |
| `write_file` | disabled_in_v1 | Audited file writes |
| `create_branch` | disabled_in_v1 | Git branch creation |
| `create_pr` | disabled_in_v1 | PR creation |

## Usage

### CLI Testing

```bash
# Show bridge status
python -m modules.infrastructure.foundups_mcp_bridge.src.bridge_server --status

# List available tools
python -m modules.infrastructure.foundups_mcp_bridge.src.bridge_server --list-tools

# Call a tool
python -m modules.infrastructure.foundups_mcp_bridge.src.bridge_server \
    --call get_repo_tree \
    --args '{"path": "modules", "depth": 2}'

# Read a file
python -m modules.infrastructure.foundups_mcp_bridge.src.bridge_server \
    --call read_file \
    --args '{"path": "WSP.txt"}'

# Get overseer status
python -m modules.infrastructure.foundups_mcp_bridge.src.bridge_server \
    --call get_overseer_status

# Get module dependencies (v1.1)
python -m modules.infrastructure.foundups_mcp_bridge.src.bridge_server \
    --call get_module_dependencies \
    --args '{"module_name": "ai_overseer"}'

# Get reverse dependencies / blast radius (v1.1)
python -m modules.infrastructure.foundups_mcp_bridge.src.bridge_server \
    --call get_reverse_dependencies \
    --args '{"module_name": "shared_utilities"}'

# Get diff summary (v1.1)
python -m modules.infrastructure.foundups_mcp_bridge.src.bridge_server \
    --call get_diff_summary \
    --args '{"commit_range": "HEAD~5..HEAD"}'

# Get change impact score (v1.2)
python -m modules.infrastructure.foundups_mcp_bridge.src.bridge_server \
    --call get_change_impact_score \
    --args '{"target_type": "module", "target": "ai_overseer"}'

# Impact score for commit range
python -m modules.infrastructure.foundups_mcp_bridge.src.bridge_server \
    --call get_change_impact_score \
    --args '{"target_type": "commit_range", "target": "HEAD~3..HEAD"}'

# Semantic search (v1.3)
python -m modules.infrastructure.foundups_mcp_bridge.src.bridge_server \
    --call holo_search \
    --args '{"query": "WSP protocol validation", "scope": "all", "top_k": 10}'

# Find related modules (v1.3)
python -m modules.infrastructure.foundups_mcp_bridge.src.bridge_server \
    --call holo_related \
    --args '{"target": "ai_overseer", "relation_type": "all", "limit": 10}'

# Search failure memory (v1.3)
python -m modules.infrastructure.foundups_mcp_bridge.src.bridge_server \
    --call holo_failure_memory \
    --args '{"query": "import error", "limit": 5}'

# Search learned patterns (v1.3)
python -m modules.infrastructure.foundups_mcp_bridge.src.bridge_server \
    --call holo_pattern_search \
    --args '{"query": "refactoring", "limit": 10}'

# Assemble task context (v1.3)
python -m modules.infrastructure.foundups_mcp_bridge.src.bridge_server \
    --call holo_task_packet \
    --args '{"task_description": "Add new validation to ai_overseer"}'
```

### Programmatic Use

```python
from modules.infrastructure.foundups_mcp_bridge.src import FoundUpsMCPBridge

bridge = FoundUpsMCPBridge()

# Get status
status = bridge.get_status()
print(status["data"]["version"])  # "1.2.0"
print(status["data"]["mode"])     # "perception-only"

# Read WSP docs
wsp_docs = bridge.call_tool("get_wsp_docs")
for doc in wsp_docs["data"]["wsp_docs"]:
    print(doc["name"])

# Get overseer mission history
missions = bridge.call_tool("get_mission_history", limit=10)
for m in missions["data"]["missions"]:
    print(f"{m['mission_id']}: {m['status']}")

# Call disabled tool (returns schema, no execution)
result = bridge.call_tool("coordinate_mission", mission_description="Test")
print(result["status"])  # "disabled_in_v1"
print(result["data"]["schema"])  # Schema definition
```

## Response Schema

All tools return unified responses:

```json
{
  "status": "ok",
  "data": { ... },
  "meta": {
    "timestamp": "2026-04-14T...",
    "source": "repo|overseer|wsp|..."
  }
}
```

Error responses:
```json
{
  "status": "error",
  "error": "Error message",
  "meta": { ... }
}
```

Disabled tool responses:
```json
{
  "status": "disabled_in_v1",
  "error": "Tool 'X' is disabled in v1 (perception-only mode)",
  "data": {
    "tool": "X",
    "schema": { ... }
  }
}
```

## Security

- **Private only** - Not exposed publicly
- **Read-only** - No writes, no execution
- **Path filtering** - Blocks .env, credentials, secrets
- **Size limits** - 200KB max file read
- **No secrets** - Explicit pattern blocking

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    FoundUpsMCPBridge v1.4.0                              │
├──────────────────────────────────────────────────────────────────────────┤
│  Repo Tools       │  Doc Tools        │  Overseer Tools                  │
│  - get_repo_tree  │  - get_wsp_docs   │  - get_mission_history           │
│  - read_file      │  - get_module_docs│  - get_pattern_memory            │
│  - search_repo    │  - get_interface_ │  - get_overseer_status           │
│  - get_recent_    │    doc            │  - get_coordination_state        │
│    changes        │  - get_test_docs  │  - get_known_failure_patterns    │
│                   │  - get_modlog     │                                  │
│                   │  - get_violations │                                  │
├──────────────────────────────────────────────────────────────────────────┤
│  Dependency Tools (v1.1)       │  Diff Tools (v1.1)                      │
│  - get_module_dependencies     │  - get_file_diff                        │
│  - get_reverse_dependencies    │  - get_diff_summary                     │
├──────────────────────────────────────────────────────────────────────────┤
│  Impact Prediction (v1.2)                                                │
│  - get_change_impact_score (risk_level, test_coverage, prior_failures)   │
├──────────────────────────────────────────────────────────────────────────┤
│  HoloIndex Recall (v1.3)                                                 │
│  - holo_search, holo_related, holo_failure_memory                        │
│  - holo_pattern_search, holo_task_packet                                 │
├──────────────────────────────────────────────────────────────────────────┤
│  Signal Normalization (v1.4)                                             │
│  - get_overseer_summary, get_hot_modules, get_repeated_failures          │
│  - get_active_risks, get_recommended_focus, get_prompt_context_packet    │
├──────────────────────────────────────────────────────────────────────────┤
│  Execution Stubs (DISABLED in v1)                                        │
│  - coordinate_mission, spawn_agent_team, trigger_skill                   │
│  - write_file, create_branch, create_pr                                  │
└──────────────────────────────────────────────────────────────────────────┘
```

## WSP References

- **WSP 97**: Truthful verification (no fake data)
- **WSP 48**: Recursive Self-Improvement (pattern memory access)
- **WSP 77**: Agent Coordination (mission state access)
- **WSP 49**: Module structure (doc file locations)
- **WSP 22**: ModLog documentation

## Future (v2)

- HoloIndex semantic search integration
- Gated execution capabilities
- Agent team spawning
- Skill dispatch with approval workflow
