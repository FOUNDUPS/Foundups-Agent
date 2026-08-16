# foundups_mcp_bridge Tests

This directory owns unit, contract, transport, lifecycle, and adversarial
coverage for the infrastructure bridge. Tests must be deterministic and must
not start or alter a resident HoloIndex owner unless a test explicitly owns
the disposable process fixture.

## HoloIndex owner suites

- `test_holo_query_service_edges.py`: response normalization, global
  flattening, deduplication, zero-limit emptiness, and explicit-module Tier-0
  reservation.
- `test_holo_query_service.py` and
  `test_holo_query_service_embedding_generation.py`: semantic owner and
  generation/embedding binding.
- `test_holo_query_service_http.py` and
  `test_holo_query_service_fastapi_adapter.py`: authenticated transport.
- `test_holo_query_service_supervisor*.py`: private owner lifecycle, cold
  startup, and platform behavior.
- `test_holo_query_service_runtime_safety.py`: runtime confinement and
  mutation-safety boundaries.

## Focused execution

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
python -m pytest `
  holo_index/tests/test_tier0_retrieval_hardening.py `
  modules/infrastructure/foundups_mcp_bridge/tests/test_holo_query_service_edges.py `
  -q
```

This focused pair proves low-K reservation, ambiguous-query preservation,
invalid component rejection, strict fail-closed behavior for lookup exception,
cardinality corruption, and returned-path mismatch, plus non-strict safe
degradation. Tier-0 retrieval tests use fake collections and supplied fake
embeddings. They must not download models, mutate the persistent vector store,
reindex, or restart the resident RedDog owner. Record behavioral additions and
validation results in `TestModLog.md` per WSP 34.
