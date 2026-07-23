# AI Gateway TestModLog

## 2026-07-23 - Direct provider catalog durability and WSP62 repair

Scope: offline-only verification for the bounded OpenRouter catalog discovery
slice. No test invokes a live provider, scheduler, runtime binding, or network
transport.

### Focused test files

| Test file | Cases | Scope |
|---|---:|---|
| `test_model_provider_catalog_snapshot.py` | 40 | Strict invocation, receipt, candidate, sanitization, freshness, and fail-closed evidence contracts |
| `test_model_openrouter_direct_discovery.py` | 27 | Manual/scheduled admission, bounded transport outcomes, durable receipt transitions, and candidate ordering |
| `test_model_provider_catalog_artifact_store.py` | 5 | Partial write, fsync, replace, cleanup, exact UTF-8, and permission-preserving atomic replacement |
| `test_model_provider_catalog_protected_surfaces.py` | 5 | Authority isolation, file ceilings, and AST-based 50-line production function ceiling |

Focused result: `77 passed`.

Supporting compatibility coverage:

- `test_model_intelligence_catalog.py`: `8 passed`, including OpenRouter
  normalization behavior preserved after cohesive single-record extraction.
- Combined provider-catalog and catalog-normalization focus: `85 passed`.
- Full `modules/ai_intelligence/ai_gateway/tests`: `326 passed`.

The counts above include the WSP62 AST regression added in this repair. The
artifact-store file is also run independently as the five-case atomic failure
matrix.
