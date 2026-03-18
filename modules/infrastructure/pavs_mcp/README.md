# pAVS MCP Server

**Location**: `modules/infrastructure/pavs_mcp/`
**WSP Compliance**: WSP 103 (FoundUp Federation), WSP 96 (MCP Governance), WSP 49 (Module Structure)
**Status**: PoC

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

| Tool | Purpose | Input | Output |
|------|---------|-------|--------|
| `cabr_validate` | V1/V2/V3 content validation | content, context | score, passed, feedback |
| `gemma_classify` | Binary/multi-class classification | text, categories | classification, confidence |
| `qwen_plan` | Strategic planning | objective, constraints | plan, reasoning |
| `fam_emit` | Event tracking | foundup_id, event_type, payload | event_id |
| `pattern_recall` | Recall successful patterns | skill, min_fidelity | patterns[] |
| `pattern_store` | Store execution outcome | skill, outcome | pattern_id |
| `holo_search` | Semantic code/doc search | query, domain | matches[] |
| `foundup_register` | Register FoundUp for access | foundup_id, repo_url | api_key, endpoint |

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

**Client (.env in FoundUp repo)**:
```bash
PAVS_ENDPOINT=wss://pavs.foundups.com/mcp
PAVS_API_KEY=fp_xxxxxxxxxxxx
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
