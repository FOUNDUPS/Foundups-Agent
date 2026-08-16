# FoundUps Private MCP Bridge

Private, read-only MCP bridge for AI-assisted architectural execution.

**Version**: 1.4.0 (perception + recall + state compression)

The owner response flattener treats `limit <= 0` as an empty result and never
admits a first hit through the loop termination check. Explicit module Tier-0
reservation remains bounded by positive caller K.

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

### FastMCP SSE Remote Server (ChatGPT Connector)

The bridge can be exposed as a standard Model Context Protocol (MCP) server over SSE (Server-Sent Events) on port 8128 (configurable via `FOUNDUPS_MCP_PORT`).

#### Starting the Server Standalone
```powershell
python -m modules.infrastructure.foundups_mcp_bridge.scripts.launch
```

#### Starting via main.py DAE Broker
When `python main.py` is started, `mcp_bridge_sse` is automatically registered as a launchable DAE spec in the broker. It starts by default unless disabled with `FOUNDUPS_MCP_AUTOSTART=0`.

#### Exposing to ChatGPT via Secure Tunnel (e.g. ngrok)
1. Start the server (default port `8128`).
2. Expose the port via a secure tunnel:
   ```bash
   ngrok http 8128
   ```
3. In ChatGPT Web:
   - Navigate to **Settings → Connectors → Advanced**.
   - Enable **Developer Mode**.
   - Click **Create Connector**.
   - Set Name to `FoundUps MCP Bridge`.
   - Set Server URL to `https://<your-ngrok-subdomain>.ngrok-free.app/sse`.
   - Click **Create**.
4. In a new ChatGPT conversation, select the **FoundUps MCP Bridge** app to gain access to all 33 perception and read tools.

### Private HoloIndex Query Owner

The RedDog operational consumers migrated in this POC use this module's owner
at literal `127.0.0.1` instead of opening Chroma directly. Trusted host
bootstraps own its lifecycle
through HoloQueryServiceSupervisor, which generates an ephemeral token, proves
authenticated semantic readiness, can supply a trusted child environment, and
cleans up the process. Before expensive semantic startup it rejects an occupied
fixed loopback port. Automatic startup binds the child to the exact supervisor
process, so the child exits after an abruptly terminated parent without a
blocking stdin reader.
Ordinary authenticated semantic health probes use up to 30 seconds. During
supervisor startup, the first cold semantic canary may use the owner's
270-second warmup budget within the unchanged 300-second total deadline.
Automatic in-process startup keeps the URL/token in a
private handoff resolved by resolve_reddog_holoindex_owner_handoff(); it never
exports the generated secret to the parent environment. See
[HOLO_QUERY_OWNER_RUNBOOK.md](HOLO_QUERY_OWNER_RUNBOOK.md).

For queries that name one uniquely evidenced module basename or one validated
full module path, the owner reserves at most two flattened slots for root
`README.md` and `INTERFACE.md` hits already returned by HoloIndex. It does not
synthesize evidence, promote nested test docs, or change global ordering for
ambiguous or implicit module queries. Exact metadata hits retain their
producer-owned null-similarity provenance rather than receiving a synthetic
flattening score.

The RedDog read-only operational preflight now calls the process-lifetime
bootstrap automatically for E2E, report collection, audit enqueue, and
OPENCLAW_AUTO_TASKS_ENABLED paths. Set
REDDOG_HOLOINDEX_OWNER_AUTO_START=0 to opt out. An already configured HTTP
service URL using literal `127.0.0.1` and a strong token bypass process creation only after its
authenticated health endpoint proves semantic readiness and the expected
repository/generation/receipt-digest binding plus exact embedding-space
fingerprints for all seven baseline collections.

Trusted interactive/headless preflight also defaults
REDDOG_HOLOINDEX_AUTO_MAINTENANCE=1. A stale canonical receipt causes one
bounded semantic index-all refresh only after a clean exact-HEAD proof. The
handshake strips source-narrowing and cap controls, requires complete
canonical manifests for all seven baseline collections, re-proves HEAD, and
starts the private owner against that exact generation. Startup may route the
request through governed WRE dispatch, while maintenance authority remains
with the trusted host. It never stops a stale externally configured owner.
A legacy blank embedding-space fingerprint is not accepted as historical
compatibility: it makes the receipt stale and triggers this maintenance path.

For manual diagnostics only, set a strong shared token outside the repository,
then launch the host-owned process:

    $env:HOLOINDEX_QUERY_SERVICE_TOKEN = "<outside-repo secret>"
    $env:HOLOINDEX_SSD_PATH = "E:/HoloIndex"
    python -m modules.infrastructure.foundups_mcp_bridge.src.holo_query_service --host 127.0.0.1 --port 8127

Configure the RedDog worker with:

    $env:HOLOINDEX_QUERY_SERVICE_URL = "http://127.0.0.1:8127"
    $env:HOLOINDEX_QUERY_SERVICE_TOKEN = "<same outside-repo secret>"

The service exposes only authenticated query and health routes. It never
indexes. Query success is semantic-only, generation-bound, and CURRENT only
when all seven baseline collection proofs match the exact caller repository
HEAD before and after retrieval; health also requires a non-empty semantic
canary. FastAPI is optional; the same command uses the stdlib HTTP runtime when
FastAPI is unavailable.

Successful responses first pass the producer-owned executable HoloIndex result
contract, then project every canonical path/location under the proven
repository root to repository-relative POSIX form. Unknown, incomplete,
cross-bucket, alias/count-divergent, or Unicode-control-bearing evidence fails
closed with empty raw and flattened results. Indexed text remains untrusted
evidence, never instructions, and query handling never reindexes the store.

The owner forces the authoritative sentence_transformers backend, discovers
complete flat and Hugging Face models--.../snapshots/<revision> caches for
offline startup, and disables the generation-unbound legacy SearchCache. Cold
semantic initialization is reserved for the first authenticated health canary
(270-second default warmup); ordinary queries are capped at 30 seconds, and the
supervisor's total startup budget is 300 seconds.

RedDog response-body reads and owner proof/search work use monotonic absolute
deadlines. The stdlib HTTP connect/header phase remains socket-inactivity
bounded. Phase 1 therefore assumes a trusted cooperative literal-loopback peer
and no hostile same-user port squatter or deliberate header trickle; it is not
a hostile-local transport security claim. Model-backed cross-lane audits also
re-prove the clean exact HoloIndex receipt HEAD after direct file reads and
again immediately before accepting their reports.

This is a supported API boundary, not an OS privilege boundary. Deploy a
worker identity without store-write/process-control permissions when hard
isolation is required. The legacy `src/holo_tools.py` MCP surface remains a
direct-store consumer outside this Phase-1 migration. Full refresh also
requires an exclusive writer window because unleased legacy writers and a
transient edit/revert are not excluded by the cooperative maintenance lease.
After a successful refresh, owner lifecycle failure can leave the receipt
CURRENT while preflight remains non-operational. Abrupt host death can leave an
orphan owner until verified process cleanup and token rotation.

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


## FastMCP Remote SSE Server & ChatGPT Tunneling

The FoundUps MCP Bridge provides an SSE server (`mcp_server.py`) for remote agents (e.g. ChatGPT Developer Mode / Custom Apps) over secure tunnels.

### ⚠️ Security First: Mandatory Authentication for Tunneling
Local loopback bindings do not require authentication by default for development. **When exposing the server via a tunnel (ngrok, Cloudflare Tunnel, or OpenAI Secure MCP Tunnel), authentication MUST be configured before starting the server or tunnel.**

```bash
# 1. Set secure auth token and enforce authentication
export FOUNDUPS_MCP_AUTH_TOKEN="your-secure-random-token"
export FOUNDUPS_MCP_REQUIRE_AUTH="1"

# 2. Launch the MCP Bridge SSE server (binds to 127.0.0.1:8128 by default)
python -m modules.infrastructure.foundups_mcp_bridge.scripts.launch

# 3. In a separate terminal, start your secure tunnel to port 8128
# Recommended: Cloudflare Tunnel or OpenAI Secure MCP Tunnel
cloudflared tunnel --url http://127.0.0.1:8128
# or: ngrok http 8128
```

### ChatGPT Custom MCP App Configuration (Developer Mode)
OpenAI supports connecting remote MCP endpoints in ChatGPT (Web):
1. In ChatGPT Web, ensure **Developer Mode** is enabled under **Settings → Connected apps / Developer Mode**.
2. Navigate to **Apps → Create App** (or custom MCP connector).
3. Set **Authentication** to **Bearer Token** and paste your `FOUNDUPS_MCP_AUTH_TOKEN`.
4. Enter the public SSE endpoint: `https://<your-tunnel-domain>/sse`.
5. Click **Scan Tools** → confirms discovery of all 33 allowlisted perception tools.
6. Open a chat, select the FoundUps MCP app, and interact with 0102.

### Security Invariants (WSP 97)
- **Remote Read-Only Allowlist**: Exposes exactly 33 pure perception tools (`REMOTE_READ_ONLY_ALLOWLIST`). All execution/mutation tools are strictly excluded from remote registration.
- **Fail-Closed Bearer Auth**: Rejects unauthenticated requests with `401 Unauthorized`. URL query tokens (`?token=`) are deliberately rejected to prevent secret leakage in proxy/tunnel logs.
- **Strict Lock Invariant**: `instance lock held <=> process owns live MCP server`. Lock is released only after confirmed server termination.
- **Protocol Readiness Canary**: Validates live SSE handshake, tool inventory against allowlist, and safe tool invocation before reporting operational status.
