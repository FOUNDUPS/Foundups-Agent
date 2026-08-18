# HoloIndex Tests

## Test Strategy (WSP 34)
- Focus on intent routing, output composition, and HoloDAE orchestration behavior.
- Keep unit tests deterministic; avoid external model/network dependencies.
- Integration tests run only when model assets are available and explicitly enabled.

## How to Run
- Unit tests: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest holo_index/tests`
- Focused: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest holo_index/tests/test_output_composer.py`

### Tier-0 retrieval hardening

`test_tier0_retrieval_hardening.py` falsifies explicit-module inference,
exact root README/INTERFACE lookup, bounded ordering, deduplication, invalid
module paths, docs-only inference, exact non-vector provenance/vector-floor
exemption, and strict/non-strict incomplete-pair behavior. It uses only fake
collections and a supplied fake embedding; it must not contact a model,
network, persistent index, or resident owner.
It also pins strict replacement of duplicate vector Tier-0 rows, exact WSP_62
ceilings, non-strict exception warnings, and full-path case normalization.
The WSP 62 check is not an exemption: it requires `search_engine.py < 1500`,
`_search_collection <= 50`, and every function in the two new extraction
helpers to remain `<= 50` lines.

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
python -m pytest `
  holo_index/tests/test_tier0_retrieval_hardening.py `
  modules/infrastructure/foundups_mcp_bridge/tests/test_holo_query_service_edges.py `
  -q
```

## Test Data
- Synthetic fixtures are preferred to keep tests fast and reproducible.
- Large-module fixtures are generated in temp dirs to avoid touching production files.

## Expected Behavior
- Intent classification produces stable, minimal output sections.
- OutputComposer trims noise and respects verbosity caps per intent.
- HoloDAE orchestration emits structured reports without flooding alerts.
- Video search health probe + metadata audit DB tests run without external deps.
- Web asset indexing tests verify `public` HTML/JS discovery remains searchable.
- RedDog direct-read tests reject traversal, symlink escapes, secret-like paths, UNC/device namespaces, and NTFS alternate data streams.

## Integration Requirements
- Some integration tests require local model assets and may be skipped by default.
- When running integration tests, ensure `LOCAL_MODEL_ROOT` (or role-specific `LOCAL_MODEL_*`) points to valid GGUF files.
