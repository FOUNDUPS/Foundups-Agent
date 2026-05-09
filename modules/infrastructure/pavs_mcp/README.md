# pAVS MCP Server

> ## ⚠️ STATUS: `REAL_TRANSPORT` + `PARTIAL_BACKENDS`
>
> **Transport is REAL. holo_search is REAL. Other backends are PLACEHOLDERS.**
>
> - **Server transport**: `HTTP_JSON` (MCPA8) — `start()` binds a real local port via Python stdlib `http.server`. Clients can connect via `POST /tool` with JSON body. No external dependencies.
> - **Auth enforcement**: `BASIC_AUTH_ENFORCEMENT` (MCPA1 Slice 6) — `handle_tool_call` validates `api_key` for protected tools; rejects missing/unknown keys; rejects cross-tenant `foundup_id` attempts. `foundup_register` remains unauthenticated (bootstrap-only).
> - **Registry persistence**: `LOCAL_JSON` (MCPA1 Slice 7) — registrations survive restart; stored in `~/.pavs_mcp/registrations.json` (override via `PAVS_REGISTRY_PATH` env var). Atomic writes, graceful handling of corrupt files.
> - **holo_search**: `REAL BACKEND` (MCPA9A) — S3 delegates to S2/HoloIndex for real semantic search. Returns `meta.real_backend=true`, `meta.delegated_to="S2"`.
> - **Other tools**: `HARDCODED/FAKE DATA` — `cabr_validate`, `gemma_classify`, `qwen_plan`, `fam_emit`, `pattern_recall`, `pattern_store` return hardcoded values; `# TODO: Connect to actual <X>` markers in code.
> - **Canonical contract**: see WSP 96 Annex A (`holo_search` contract). S3 is not canonical owner but now provides real backend via S2 delegation.
> - **Tracked remediation**: MCPA10+ (remaining backends, key rotation).

**Location**: `modules/infrastructure/pavs_mcp/`
**WSP Compliance**: WSP 103 (FoundUp Federation), WSP 96 (MCP Governance), WSP 49 (Module Structure)
**Status**: `REAL_TRANSPORT + PLACEHOLDER_BACKENDS` — see banner above

## Purpose

The pAVS MCP Server exposes Foundups-Agent infrastructure to **independent FoundUp repositories** via Model Context Protocol (MCP). This enables the **FoundUp Federation** pattern where FoundUps are autonomous repos that connect to pAVS infrastructure without requiring the full codebase.

## Architecture

```
Independent FoundUp Repos          pAVS Infrastructure
========================          ====================

Foundup/AutoPost ----MCP---+
                           |
Foundup/GotJunk -----MCP---+--> [pAVS MCP Server] --> [WRE Infrastructure]
                           |         |
Foundup/Move2Japan --MCP---+         +-> CABR Engine
                                     +-> Gemma Classifier
                                     +-> Qwen Planner
                                     +-> FAM DAEmon
                                     +-> Pattern Memory
                                     +-> HoloIndex
```

## Exposed Tools

> All tool responses include `meta.implementation_status = "placeholder_stub"` to signal that the data is fake. Conforming clients MUST check this flag before treating results as real (per WSP 96 Annex A.5 C3).

| Tool | Purpose | Input | Output | Real backend? |
|------|---------|-------|--------|---------------|
| `cabr_validate` | V1/V2/V3 content validation | content, context | score, passed, feedback | **NO** — hardcoded `score=0.85` |
| `gemma_classify` | Binary/multi-class classification | text, categories | classification, confidence | **NO** — hardcoded `confidence=0.92` |
| `qwen_plan` | Strategic planning | objective, constraints | plan, reasoning | **NO** — hardcoded 3-step plan |
| `fam_emit` | Event tracking | foundup_id, event_type, payload | event_id | **NO** — computes hash, no FAM emit |
| `pattern_recall` | Recall successful patterns | skill, min_fidelity | patterns[] | **NO** — hardcoded `ptn_001` |
| `pattern_store` | Store execution outcome | skill, outcome | pattern_id | **NO** — computes hash, no persist |
| `holo_search` | Semantic code/doc search | query, doc_type_filter | hits[], hit_count | **YES** — delegates to S2/HoloIndex (MCPA9A) |
| `foundup_register` | Register FoundUp for access | foundup_id, repo_url | api_key, endpoint | Stub — generates api_key, persists to JSON |

## Quick Start

### Server Side (Infrastructure)

```bash
# Start pAVS MCP Server (binds to http://0.0.0.0:8765)
python -m modules.infrastructure.pavs_mcp.src.server
```

### HTTP Transport Endpoints (MCPA8)

The server exposes these HTTP JSON endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/status` | GET | Health check and server status |
| `/tools` | GET | List available tools |
| `/tool` | POST | Execute tool call (main endpoint) |
| `/tool/{name}` | POST | Execute tool by path |

**POST /tool** request body:
```json
{
  "tool_name": "holo_search",
  "arguments": {"query": "test", "limit": 10},
  "api_key": "fp_xxxxxxxxxxxx"
}
```

**Response**: Exact `handle_tool_call` envelope with `result` or `error` and `meta`.

### Client Side (FoundUp)

```typescript
// TypeScript (PWA FoundUps)
import { PAVSClient } from '@foundups/pavs-sdk';

const pavs = new PAVSClient({
  endpoint: process.env.PAVS_ENDPOINT,
  apiKey: process.env.PAVS_API_KEY
});

// Validate content before posting
const result = await pavs.cabrValidate("My post content", {
  platform: "instagram",
  audience: "local"
});

if (result.passed) {
  // Proceed with post
}
```

```python
# Python (Backend FoundUps)
from foundups_pavs import PAVSClient

pavs = PAVSClient(
    endpoint=os.environ['PAVS_ENDPOINT'],
    api_key=os.environ['PAVS_API_KEY'],
    foundup_id='autopost'
)

# Get strategic plan
plan = await pavs.qwen_plan(
    objective='maximize_engagement',
    constraints={'platform': 'instagram', 'timing': 'optimal'}
)
```

## SDK Packages

| Package | Language | Registry | Status |
|---------|----------|----------|--------|
| `@foundups/pavs-sdk` | TypeScript | npm | Planned |
| `foundups-pavs` | Python | PyPI | Planned |

## Environment Variables

**Server (.env)**:
```bash
PAVS_MCP_HOST=0.0.0.0
PAVS_MCP_PORT=8765
PAVS_AUTH_SECRET=<secure-secret>
```

**Client (.env in FoundUp repo)** — *(planned, not deployed)*:
```bash
# WARNING: The endpoint below is NOT deployed. The pAVS MCP server in this
# repository is a PLACEHOLDER_STUB; it does not bind a port and does not
# accept connections. Do not configure clients against it for production
# until MCPA1 Slice 4 and Slice 6 land.
PAVS_ENDPOINT=wss://pavs.foundups.com/mcp   # planned, not live
PAVS_API_KEY=fp_xxxxxxxxxxxx                # ignored by current server (auth is TODO)
```

## WSP Compliance

- **WSP 103**: FoundUp Federation Protocol - This module IS the federation bridge
- **WSP 96**: MCP Governance - Follows consensus patterns
- **WSP 49**: Module structure - Standard layout
- **WSP 71**: Security - API key auth, encrypted transport

## Related Documentation

- [WSP 103: FoundUp Federation Protocol](../../../WSP_knowledge/src/WSP_103_FoundUp_Federation_Protocol.md)
- [WSP 96: MCP Governance](../../../WSP_knowledge/src/WSP_96_MCP_Governance_and_Consensus_Protocol.md)
- [INTERFACE.md](./INTERFACE.md) - API documentation
- [ROADMAP.md](./ROADMAP.md) - Development phases
