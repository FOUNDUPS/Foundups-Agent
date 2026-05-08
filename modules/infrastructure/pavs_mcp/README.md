# pAVS MCP Server

> ## ⚠️ STATUS: `PLACEHOLDER_STUB`
>
> **DO NOT USE FOR REAL TENANTS OR PRODUCTION TRAFFIC.**
>
> - **Implementation status**: `PLACEHOLDER_STUB`
> - **Auth enforcement**: `NO_AUTH_ENFORCEMENT` — `handle_tool_call` accepts `api_key` parameter but never validates it (`src/server.py:329` is a `# TODO`).
> - **Tool data**: `TOOLS RETURN HARDCODED/FAKE DATA` — every `cabr_validate`, `gemma_classify`, `qwen_plan`, `fam_emit`, `pattern_recall`, `pattern_store`, `holo_search`, `foundup_register` body returns hardcoded values; `# TODO: Connect to actual <X>` markers in code.
> - **Server transport**: `NOT PRODUCTION READY` — `start()` does not bind a port; the body is `await asyncio.sleep(60)` in a loop (`src/server.py:354, 362`).
> - **Canonical contract**: see WSP 96 Annex A (`holo_search` contract). Per Annex A.1, S3 has **NO authority** over `holo_search` until the federation auth/scope work is complete; the placeholder implementation is retained only for surface-shape preservation.
> - **Tracked remediation**: MCPA1 Slice 4 (`MCP_HOLO_SEARCH_DELEGATION_PHASE1`) and Slice 6 (`MCP_FEDERATION_AUTH_AND_SCOPE_PHASE1`).

**Location**: `modules/infrastructure/pavs_mcp/`
**WSP Compliance**: WSP 103 (FoundUp Federation), WSP 96 (MCP Governance), WSP 49 (Module Structure)
**Status**: `PLACEHOLDER_STUB` — see banner above

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
| `holo_search` | Semantic code/doc search | query, domain | matches[] | **NO** — hardcoded match (NOT canonical owner; see WSP 96 Annex A.1) |
| `foundup_register` | Register FoundUp for access | foundup_id, repo_url | api_key, endpoint | Stub — generates api_key but never persists or checks it |

## Quick Start

### Server Side (Infrastructure)

```bash
# Start pAVS MCP Server
python -m modules.infrastructure.pavs_mcp.src.server
```

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
