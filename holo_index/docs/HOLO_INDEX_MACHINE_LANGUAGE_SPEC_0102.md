# HoloIndex Machine-Language Specification (0102)

## 1) First-Principles Definition
HoloIndex is a deterministic retrieval-and-orchestration machine:

`(query, context, configuration) -> (ranked memory hits, protocol guidance, action surface)`

It is not only a search utility. It is a policy-bearing retrieval system with:
- memory indexing,
- intent routing,
- compliance framing,
- agent-specific output compression.

## 2) Canonical Runtime Topology
- Retrieval core: `holo_index/core/holo_index.py` (`HoloIndex`)
- CLI command router: `holo_index/_cli_main.py` (`main`)
- Intent and composition:
  - `holo_index/intent_classifier.py`
  - `holo_index/qwen_advisor/orchestration/qwen_orchestrator.py`
  - `holo_index/output_composer.py`
- Output contract + memory cards: `holo_index/output/agentic_output_throttler.py`
- Adaptive learning:
  - `holo_index/feedback_learner.py`
  - `holo_index/adaptive_learning/breadcrumb_tracer.py`

## 3) State Machine
- `BOOTSTRAP`: initialize model, Chroma collections, cached WSP summary/navigation.
- `INDEX_READY`: accepts index/search commands.
- `SEARCH_EXECUTING`: multi-collection retrieval across code, WSP, tests,
  skills, symbols, docs, knowledge, and optional work-ledger evidence.
- `RESULT_FOUND`: at least one hit.
- `RESULT_MISSING`: no hit, creation guidance path.
- `ERROR`: exception path with structured fallback payload.

Transition behavior is owned by `HoloIndex.search` and the output throttler;
symbol references are used instead of brittle source line numbers.

## 4) Scoring Math (Current)
- Vector distance conversion:
  - `similarity = 1 / (1 + distance)`
- Similarity floor:
  - `HOLO_MIN_SIMILARITY` (default `0.35`)
- Hybrid rank:
  - `score = 0.5*priority + 0.3*similarity + 0.2*keyword_score`
- Skill rank variant:
  - `score = 0.6*priority + 0.3*similarity + 0.1*keyword_score`
- Lexical fallback similarity:
  - `similarity = min(1.0, keyword_score / (max(1, token_count * 2.5)))`

## 5) Retrieval Contract (Machine Surface)
`search(query, limit, doc_type_filter)` returns keys:
- `code_hits`, `wsp_hits`, `test_hits`
- `code`, `wsps`, `tests` (legacy compatibility)
- `skills`, `skill_hits`
- `symbol_hits`
- `docs_hits` / `docs`, `knowledge_hits` / `knowledge`
- `work_ledger_hits` / `work_ledger`
- `metadata` with per-bucket counts, timestamp, retrieval mode, embedding
  backend, backend quality/gate, and collection routing truth

`--bundle-json` returns schema `wsp_memory_bundle_v1`:
- `schema_version`, `generated_at`, `ok`
- `task`, `module_hint`, `module_path`
- `structured_memory`, `task_retrieval`

## 6) Intent-Orchestration Contract
Intent classes:
- `doc_lookup`
- `code_location`
- `module_health`
- `research`
- `general`

Execution components:
- `health_analysis`
- `vibecoding_analysis`
- `file_size_monitor`
- `module_analysis`
- `pattern_coach`
- `orphan_analysis`
- `wsp_documentation_guardian`

MCP research is intent-gated (`research` only).

## 7) Storage, Freshness, and Query Ownership

- Storage precedence: explicit path, HOLOINDEX_SSD_PATH, legacy
  HOLO_SSD_PATH, then a platform-safe absolute default.
- The Windows SSD root default is `E:/HoloIndex`. POSIX uses
  `$XDG_DATA_HOME/foundups/holoindex` or
  `~/.local/share/foundups/holoindex` when XDG_DATA_HOME is absent/relative.
- Query-only initialization requires the existing vector store and collections;
  it performs no HoloIndex maintenance write.
- The supported RedDog operational adapter delegates semantic retrieval to an
  authenticated owner at literal `127.0.0.1` because Chroma PersistentClient
  is not a read-only database client. This API boundary does not replace host
  OS-level filesystem/process isolation.
- CURRENT requires the exact repository HEAD plus complete canonical
  source-scope manifests for code, symbols, WSP, tests, skills, docs, and
  knowledge before and after retrieval. Work ledger and vocabulary are
  optional collections and are not part of the seven-collection baseline.
- Each baseline receipt also binds the actual collection embedding backend,
  logical model, and local artifact fingerprint. The Phase-1 owner forces the
  canonical fp32 backend, disables the generation-unbound search cache, and
  rejects any runtime/receipt fingerprint or resident-generation mismatch.
  Its strict-semantic mode also rejects collection/model/encode/query failure
  instead of substituting lexical or exact-symbol fallback evidence.
- Canonical source proofs cover Git-tracked sources only, hash full raw source
  content, and fail on recorded source-read, cap, or Python-AST omissions.
  They do not make a blanket claim about every legacy format parser. Scoped or
  capped diagnostic runs cannot publish canonical baseline proof.
- A partial maintenance run advances only successfully refreshed collections.
  Untouched proof retains its original SHA or becomes UNVERIFIED.
- Legacy receipts without an embedding-space fingerprint require refresh; a
  lexical, quantized-only, incomplete-cache, or mixed-space refresh cannot PASS.
- Mutation owners require a proven-clean exact Git HEAD, hold the canonical
  cross-process lease, and atomically publish IN_PROGRESS before collection
  access. PASS is emitted only after the exact plan succeeds at the same HEAD.
- Query owners probe the lease around repository, freshness, and retrieval
  work. Active or unprovable maintenance is an explicit index gap.
- The trusted host owns indexing and freshness maintenance; startup may route
  a request through governed WRE dispatch. The supported RedDog adapter owns
  query evidence only. Legacy foundups_mcp_bridge `holo_tools.py` remains a
  registered direct-store consumer outside this Phase-1 migration.

## 8) CTO Consistency Audit (Docs vs Runtime)

The original 2026-02-18 contract run covered:
- `holo_index/tests/test_intent_classifier.py`
- `holo_index/tests/test_output_composer.py`
- `holo_index/tests/test_memory_output_contract.py`
- `holo_index/tests/test_doc_type_filtering.py`

Result: `45 passed`.

The 2026-07-18 operational-truth-boundary validation plan additionally covers
machine entrypoint existence, the exact nine-collection catalog, the
seven-collection baseline, optional collections, canonical source-scope IDs,
platform storage defaults, and the expanded response/metadata contract. Exact
focused/integration counts and PR evidence will be recorded only after those
gates complete.

Resolved drifts:
- `OutputComposer` accepted only `intent_classification`; now supports legacy `intent` callers.
- Router returned non-executable component names (`code_index_search`, `mcp_integration`); now aligned to executable component surface.
- `HoloIndex.search()` now handles partial initialization without collapsing into exception fallback.
- Intent classification and alert grouping now match expected behavioral contract.

Open drift:
- `CLI_REFERENCE.md` is a menu snapshot, not an exhaustive flag contract. This file + JSON spec are now the canonical machine contract.

## 9) Economic/System Interpretation
At system level, HoloIndex optimizes:
- recall of existing implementations,
- policy adherence (WSP constraints),
- token efficiency under agent context limits.

It behaves as a constrained optimizer:
- maximize relevance and protocol utility,
- subject to output and latency constraints.

## 10) Canonical Source of Truth
- Machine contract (authoritative, executable-facing): `holo_index/docs/HOLO_INDEX_MACHINE_LANGUAGE_SPEC_0102.json`
- Human-readable explanation: this document
- Public interface summary: `holo_index/INTERFACE.md`
- Operator/menu atlas (non-normative): `holo_index/CLI_REFERENCE.md`
