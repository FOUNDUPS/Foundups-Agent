# pAVS MCP Server Roadmap

## Purpose

Phased delivery of the pAVS MCP Server that enables FoundUp Federation (WSP 103).

## Phase 0: Foundation (Current)

**Status**: In Progress
**Target**: 2026-03-20

### Deliverables

- [x] WSP 103 FoundUp Federation Protocol
- [x] Module scaffolding (README, INTERFACE, ROADMAP)
- [ ] Basic MCP server implementation
- [ ] `cabr_validate` tool
- [ ] `fam_emit` tool
- [ ] Local development endpoint

### Exit Criteria

- MCP server starts and accepts connections
- At least 2 tools operational
- AutoPost can connect and call tools

## Phase 1: Core Tools

**Status**: Planned
**Target**: 2026-03-30

### Deliverables

- [ ] `gemma_classify` tool (connect to Gemma engine)
- [ ] `qwen_plan` tool (connect to Qwen advisor)
- [ ] `pattern_recall` tool (connect to Pattern Memory)
- [ ] `pattern_store` tool
- [ ] `holo_search` tool

### Exit Criteria

- All 7 core tools operational
- Integration tests passing
- AutoPost uses at least 3 tools

## Phase 2: Authentication & Registry

**Status**: Planned
**Target**: 2026-04-15

### Deliverables

- [ ] `foundup_register` tool
- [ ] API key generation and validation
- [ ] FoundUp registry (SQLite/Postgres)
- [ ] Rate limiting
- [ ] Usage tracking

### Exit Criteria

- FoundUps can self-register
- API keys scoped per-FoundUp
- Rate limits enforced

## Phase 3: SDK Release

**Status**: Planned
**Target**: 2026-04-30

### Deliverables

- [ ] `@foundups/pavs-sdk` npm package
- [ ] `foundups-pavs` PyPI package
- [ ] SDK documentation
- [ ] Example integrations

### Exit Criteria

- SDKs published to registries
- AutoPost, GotJunk using SDKs
- External contributor can integrate in <1 hour

## Phase 4: Production Deployment

**Status**: Planned
**Target**: 2026-05-15

### Deliverables

- [ ] Production MCP endpoint (wss://pavs.foundups.com/mcp)
- [ ] TLS/encryption
- [ ] Monitoring and alerting
- [ ] SLA documentation

### Exit Criteria

- 99.9% uptime target
- <100ms p99 latency
- At least 3 FoundUps in production use

## Phase 5: Advanced Features

**Status**: Future
**Target**: 2026 Q3

### Deliverables

- [ ] Multi-agent coordination tools
- [ ] Cross-FoundUp pattern sharing
- [ ] Federated learning aggregation
- [ ] UPs billing integration

### Exit Criteria

- FoundUps can coordinate via MCP
- Patterns learned across federation
- Revenue from pAVS access

## Dependencies

- WSP 103 (FoundUp Federation Protocol)
- WSP 96 (MCP Governance)
- FAM DAEmon operational
- Pattern Memory operational
- Gemma/Qwen engines available

## Risks

| Risk | Mitigation |
|------|------------|
| MCP protocol changes | Pin to stable MCP version |
| Latency issues | Local caching, async patterns |
| Security vulnerabilities | API key rotation, audit logging |
| SDK adoption | Good docs, example repos |

## Success Metrics

- Number of registered FoundUps
- Daily MCP tool calls
- Pattern learning velocity
- External contributor PRs to FoundUps
