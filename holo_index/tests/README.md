# HoloIndex Tests

## Current-truth document retrieval

`test_document_truth.py` proves low-cardinality current, implementation,
history, vision, and unknown classification plus the broad-current versus
exact/historical/temporal query boundary. It also proves authority ordering
before K truncation and a filtered summary stream that preserves path diversity
when one document has many section hits.

`test_indexer_zero_docs_observability.py` proves canonical Holo contracts gain
only for an exact per-path heading allowlist while historical or generic status
sections cannot inherit current authority. Historical audit docs remain one
summary record. All indexing tests use temporary repositories,
deterministic fake embeddings, and fake collections; they never open, mutate,
or refresh a live Holo generation. The same suite requires the parent indexing
engine to remain below 1,500 lines and every extracted function at or below 50.

## Model source-path provenance

`test_holoindex_embedding_space.py` proves the opt-in planner mode preserves an
available model-directory alias for link/junction inspection while the default
resolver behavior remains unchanged.

## Closed command-import regression

`test_reddog_extension_bundle_recall.py` starts a `-S -B` child and imports the
bundle command from the repository alone. The owner-script suite repeats that
proof across the exact `scripts.reddog_holoindex_owner_query_once` entrypoint
and additionally excludes ChromaDB and NumPy. RedDog's bounded direct-read path
therefore cannot silently inherit semantic/vector dependencies.

## Existing maintenance-sentinel lease

Freshness-receipt tests cover the noncreating retained lease used by RedDog
query-replica materialization. Tests operate only on temporary sentinels and
prove exact bytes/identity plus cross-contender exclusion; they never access a
live Holo store.

## Test Strategy (WSP 34)
- Focus on intent routing, output composition, and HoloDAE orchestration behavior.
- Keep unit tests deterministic; avoid external model/network dependencies.
- Integration tests run only when model assets are available and explicitly enabled.

`test_holoindex_query_receipt.py` proves valid owner attempt/retry/cycle
telemetry is inside the receipt digest. Root one-shot and communication tests
separately prove malformed, out-of-range, unequal, or top-level-only telemetry
cannot authorize a controller reproof. Query-receipt plus one-shot cycle
coverage is 77 passed.

### Query replica boundary

Materializer tests live with the owning bridge at
`modules/infrastructure/foundups_mcp_bridge/tests/test_reddog_holoindex_query_replica.py`.
They use synthetic vector/model trees and prove canonical bytes unchanged.
They also prove failed replica objects are quarantined without deletion. Holo
tests must not infer owner routing or live-store acceptance from them.

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
`test_indexer_zero_docs_observability.py` additionally runs the real docs
index transform into the strict Tier-0 injection seam. It requires producer
metadata to be repository-relative POSIX and proves the resulting root pair is
queryable without normalization. The test uses only a temporary tree and fake
collection; it does not open or mutate a live index.
The WSP 62 check is not an exemption: it requires `search_engine.py < 1500`,
`_search_collection <= 50`, and every function in the two new extraction
helpers to remain `<= 50` lines.

The same suite now proves exact indexed `symbol` metadata outweighs a nearby
semantic registry result without a path-specific exception. Retrieval
AutoResearch coverage also statically includes the independent AI Overseer
A-grade gate so it cannot acquire process/index mutation surfaces unnoticed.
`test_retrieval_runtime_binding.py` proves the owner ranker digest changes with
source bytes, accepts one exact runtime root, and rejects mixed roots or linked
ranker files. Owner-client and benchmark regressions reject missing, malformed,
or candidate-mismatched runtime ranker attestations.

`test_graphrag_exporter.py` proves repository-relative hits resolve from the
Holo authority root even under a foreign CWD and that `..` escapes are not
read. Relative hits without an explicit root also fail closed; absolute legacy
fixtures inside the authority root retain their existing behavior, while
absolute escapes are rejected. GraphRAG currently consumes code/WSP hits, so
this is adjacent path-contract coverage rather than a docs-index test.

`test_module_intent_snapshot.py` proves shell-free HEAD pinning, deterministic
ordering, final-NUL framing, all-record normalized paths, exact depth-three
filtering, duplicate-basename ambiguity, 4,096/4,097 caps, platform-aware
locked cache bounds, full-path independence, and fail-closed nonzero/timeout/
malformed/control/oversize behavior. Unicode coverage rejects `Cc`/`Cf`/`Cs`
on deeper records and NFC/NFD-equivalent duplicates while retaining visible
accented letters and non-ASCII symbols. Its K=1/12/20 falsifier varies returned
context for the exact Group-A audit query while holding the HEAD catalog fixed.
Strict catalog failure is explicit; non-strict failure passes an empty registry
and cannot fall back to vector-hit singularity.
`test_machine_spec_contract.py` binds canonical nullable
`tier0_module_target` metadata and rejects noncanonical target paths.

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
python -m pytest `
  holo_index/tests/test_tier0_retrieval_hardening.py `
  holo_index/tests/test_module_intent_snapshot.py `
  holo_index/tests/test_machine_spec_contract.py `
  modules/infrastructure/foundups_mcp_bridge/tests/test_holo_query_service.py `
  modules/infrastructure/foundups_mcp_bridge/tests/test_holo_query_service_edges.py `
  scripts/tests/test_reddog_holoindex_owner_query_once.py `
  -q
```

The exact command above passed 278 tests in 4.00 s on the R3 candidate.

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
