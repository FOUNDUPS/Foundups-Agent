# pAVS MCP Server - ModLog

## 2026-05-07 - HIA Phase 5: MCP Exposure (FoundUp Scope Params)

**Author**: 0102 (W1)
**WSP Compliance**: WSP 97, WSP 103, WSP 104

### Changes

- `server.py`: Extended `holo_search()` with `foundup_id` and `include_shared`
  params for tenant-scoped search
- `tests/test_server_holo_search.py`: New test file (17 tests)

### API Update

```python
async def holo_search(
    query: str,
    domain: Optional[str] = None,
    limit: int = 10,
    foundup_id: Optional[str] = None,  # NEW
    include_shared: bool = True,        # NEW
) -> dict[str, Any]
```

### Response Contract

Response now includes:
- `scope.foundup_id`: Echo of input param
- `scope.include_shared`: Echo of input param
- `scope.domain`: Echo of input param
- `_placeholder: True`: WSP 97 truthfulness flag
- `_note`: Explains placeholder status

### Note (WSP 97)

This remains a **placeholder implementation**. The `_placeholder=True` flag
and `_note` field explicitly state that scope params are accepted but not
applied to actual search (no live HoloIndex connection yet).

---

## 2026-03-15 - Module Creation (WSP 103 Foundation)

**Author**: 0102
**WSP Compliance**: WSP 103, WSP 96, WSP 49

### Created

- `README.md` - Module overview and quick start
- `INTERFACE.md` - MCP tool API documentation
- `ROADMAP.md` - Phased delivery plan
- `src/__init__.py` - Module exports
- `src/server.py` - pAVS MCP Server implementation (placeholder)

### Architecture Decision

**WSP 103 FoundUp Federation Protocol** establishes that:
- FoundUps are independent repositories (not monorepo subdirectories)
- FoundUps connect to pAVS infrastructure via MCP
- pAVS MCP Server exposes: CABR, Gemma, Qwen, FAM, Pattern Memory, HoloIndex

### Tools Defined

| Tool | Purpose | Status |
|------|---------|--------|
| `cabr_validate` | V1/V2/V3 content validation | Placeholder |
| `gemma_classify` | Binary/multi-class classification | Placeholder |
| `qwen_plan` | Strategic planning | Placeholder |
| `fam_emit` | Event tracking | Placeholder |
| `pattern_recall` | Recall patterns | Placeholder |
| `pattern_store` | Store outcomes | Placeholder |
| `holo_search` | Semantic search | Placeholder |
| `foundup_register` | Register FoundUp | Placeholder |

### Next Steps

1. Connect tool implementations to actual infrastructure
2. Implement WebSocket MCP transport
3. Add authentication/rate limiting
4. Create SDK packages (@foundups/pavs-sdk, foundups-pavs)
