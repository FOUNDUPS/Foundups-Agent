# HoloIndex - Brain Surgeon Level Code Intelligence System

## Closed command-import boundary

Bounded command modules such as `holo_index.cli.commands.bundle_json` load
without importing the semantic/vector runtime. Legacy package exports remain
available and load the full CLI only when requested or invoked. This keeps the
RedDog direct-read audit path operable in its sealed Python environment without
adding ChromaDB, NumPy, model, network, or canonical-store authority.

## Canonical store isolation status

The FoundUps MCP bridge contains a governed materializer for one immutable,
generation-bound query replica. It copies one selected complete model snapshot
and the exact sealed 22-file `vectors/query_snapshots` set from manifests while the
canonical receipt and noncreating, ordered authority/maintenance leases remain
retained through active publication and final validation. Model resolver
markers are direct snapshot-root children; the public bridge API uses sealed
dependencies and no-delete, no-replace quarantine for failed replica objects.
Failed Windows model copies preserve partial bytes until the bridge quarantines
the enclosing staging root; HoloIndex never consumes that partial state.
Governed maintenance exports all seven baseline collections into a bounded,
generation-bound snapshot set. HoloIndex opens only the generation root
supplied by its verified query-replica supervisor and loads those immutable
rows and float32 vectors through the existing exact-search adapter. The query
path never starts Chroma or opens SQLite/HNSW; its snapshot generation must
equal the verified replica generation. Maintenance retains the write-capable
canonical Chroma path.

Exact main `a7302344424615dc9d061ef408c2de2508660b81` has a manually activated
immutable snapshot replica for generation `sha256:d654414a...`; a governed
owner query proved CURRENT/no-gap/no-reindex and unchanged replica bytes. The
automatic post-merge ordering repair remains candidate truth until replayed at
a later merged exact main.

## Module Tier-0 retrieval

Vector collection orchestration is split into `core/collection_search.py`;
`core/search_engine.py` retains the compatible `_search_collection` entry
point. Strict and interactive semantic searches resolve basename intent from
`module_intent_snapshot.py`, a bounded, shell-free, HEAD-pinned `git ls-tree`
module catalog cached by resolved repository root and HEAD. The catalog is
independent of caller K, so a module cannot become falsely singular merely
because another named module fell outside a top-K result bucket.
Its Git stream must be nonempty and end in exactly one record terminator;
every record is validated for UTF-8, header, modules-only normalized path, and
exact/NFC-normalized case-folded duplication before depth filtering. Unicode
control, format, and surrogate code points (`Cc`/`Cf`/`Cs`) fail closed on
every record; visible Unicode letters and symbols remain valid and retain
their original spelling. Valid ancestors and deeper descendants are accepted
but only exact depth-three roots are exposed.
Cache root identity uses platform `normcase`; reads/eviction/writes/clear are
locked, while Git calls remain outside the lock. Concurrent cold callers may
duplicate a bounded Git read, but the final cache cannot exceed eight entries.

When a semantic query names one module uniquely in that complete catalog, or
supplies one validated full module path, HoloIndex performs
zero-to-two bounded exact metadata lookups in the admitted
`navigation_docs` collection for that module's root `README.md` and
`INTERFACE.md` (rows already present are deduplicated). Exact metadata rows
declare `retrieval_provenance: exact_metadata` and a null vector similarity;
they are ordered ahead of nested docs and are exempt from the vector floor.
The docs producer stores `path` as a canonical repository-relative POSIX
value. This is the same identity consumed by strict exact lookups; absolute
authority-worktree paths are neither published nor normalized at query time.
File-reading consumers bind relative hits to the Holo authority root and
reject traversal outside it, so behavior is independent of process CWD.
Canonical nullable metadata `tier0_module_target` carries the producer's
generation-stable intent; exact-row provenance alone is not an intent claim.
Strict owner mode replaces any vector-returned root rows with exactly one
exact-filtered row for each contract; duplicates cannot satisfy completeness.
All remaining evidence keeps the existing ranking. Ambiguous or implicit
module queries do not receive Tier-0 promotion. Strict owner mode requires the
catalog and complete pair. If the catalog is unavailable, non-strict mode logs
one stable warning and continues with an explicit empty registry; it never
falls back to hit-conditioned singularity. Query paths read bounded Git tree
metadata but never walk/read working-tree module files or reindex the store.

The exact `03c332294...` tree probe has 1,265 directory records, 145,619 raw
bytes, and 168 exact `modules/<domain>/<module>` roots. The final reproducible
paired probe measured 122.645 ms cold and 42.043 ms warm. Hard limits are 5
seconds, 1 MiB Git output, and 4,096 module roots.

## [ALERT] REVOLUTIONARY EVOLUTION (2025-10-17): WSP 97 System Execution Prompting Protocol

HoloIndex has evolved from module finder to **brain surgeon level code intelligence** with **baked-in WSP 97 execution prompting**:
- **Before**: Find modules -> "Here's the file"
- **After**: Function-level indexing -> "Lines 256-276: check_video_is_live" + Mermaid flow analysis + inefficiency detection
- **WSP 97**: **META-FRAMEWORK** - Baked-in execution methodology for building Rubik Cubes (MVP DAEs)

### Core Mantra (Baked into All Agents)
```
HoloIndex -> Research -> Hard Think -> First Principles -> Build -> Follow WSP
```

**Agent Profiles**: 0102 (strategic), Qwen (coordination), Gemma (validation)
**Mission Templates**: MCP Rubik, Orphan Archaeology, Code Review
**Rubik Context**: Rubik = MVP DAE. Currently "Cubes" (modules) need Qwen/Gemma enhancement to become fully agentic PWAs connecting to blockchains via FoundUp MCPs
**Holo as Toolkit**: HoloIndex provides the intelligence toolkit for Rubik Cube development and orchestration

## [ALERT] PREVIOUS REVOLUTIONARY EVOLUTION (2025-10-13)

HoloIndex has evolved from module finder to **brain surgeon level code intelligence**:
- **Before**: Find modules -> "Here's the file"
- **After**: Function-level indexing -> "Lines 256-276: check_video_is_live" + Mermaid flow analysis + inefficiency detection

## [AI] CODE INDEX CAPABILITIES (WSP 92)
- **Function-Level Indexing**: Every function mapped with line numbers and complexity analysis
- **Mermaid Flow Diagrams**: Visual code flow for each module showing logic paths
- **Inefficiency Detection**: Identifies duplicate code, overly complex functions, logic flow issues
- **DAE Cube Mapping**: Maps modules to DAE cubes with boundary awareness
- **Surgical Precision**: 0102 agents operate with complete system awareness

## Example: Stream Resolver Analysis
```
[CODE-INDEX] FUNCTION-LEVEL CODE INDEXING (WSP 92):
  [MODULE] Primary Module: no_quota_stream_checker.py
  [FUNCTIONS] 9 functions indexed
    • NoQuotaStreamChecker (lines 32-45) - Low Complexity
    • __init__ (lines 35-44) - Low Complexity
    • _get_live_verifier (lines 69-88) - Low Complexity
    • check_video_is_live (lines 138-530) - High Complexity [U+26A0]️ TOO LONG
    • check_channel_for_live (lines 553-810) - High Complexity [U+26A0]️ TOO LONG

  [BRAIN-SURGERY] Identified Inefficiencies:
    [U+26A0]️ Function 'check_video_is_live' is too long (392 lines)
    [U+26A0]️ Function 'check_channel_for_live' is too long (257 lines)
```

## [ALERT] MAJOR ARCHITECTURAL PIVOT (2025-09-25)

HoloIndex has evolved from a search tool into the **autonomous intelligence foundation** for the entire FoundUps ecosystem. This is now the **green foundation board agent** that comes with every LEGO set.

## [U+1F525] UPCOMING ENHANCEMENT: Intent-Driven Orchestration (2025-10-07)

**Design Complete** - See `docs/agentic_journals/HOLODAE_INTENT_ORCHESTRATION_DESIGN.md`

**Problem:** All components fire for every query -> 87 warnings flood output -> Relevant info buried
**Solution:** Intent classification -> Smart component routing -> Structured output -> 71% token reduction

**Key Features:**
- **Intent Classification**: Automatically detect 5 query types (DOC_LOOKUP, CODE_LOCATION, MODULE_HEALTH, RESEARCH, GENERAL)
- **Smart Routing**: Only relevant components execute (not all 7 every time)
- **Structured Output**: 4 priority sections (INTENT, FINDINGS, MCP, ALERTS)
- **Alert Deduplication**: 87 "ModLog outdated" warnings -> 1 line
- **Feedback Learning**: Rate output (good/noisy/missing) -> System learns and improves
- **Breadcrumb Events**: Track all orchestration decisions for multi-agent learning

**Token Efficiency:**
- Before: ~10,000 tokens per query
- After: ~2,900 tokens per query (71% reduction)
- With learning: ~1,500 tokens after 1000 cycles (48% total reduction)

**Architecture Preserved:** Qwen->0102->012 orchestration UNCHANGED (enhancement, not replacement)

**Status:** Awaiting 012 decision to begin implementation

## Overview
## Current Status (2025-09-28)
- [OK] **Active today:** classical pipeline (tokenisation [U+279C] SentenceTransformer embeddings [U+279C] ChromaDB) plus HoloDAE monitoring.
- [U+26A0]️ **Future work:** quantum modules (quantum_agent_db, quantum_encoding) are NumPy research scaffolds; they are not invoked in production runs.
- [U+1F9ED] **Roadmap:** quantum/Grover references remain aspirational until hardware integration is feasible.
HoloIndex + **HoloDAE** is the governed retrieval and observation foundation
for future autonomous code intelligence:
- **HoloIndex**: Semantic code discovery (WSP 87)
- **HoloDAE**: Observation and proposal surfaces around retrieval

Current production truth is narrower than the historical vision. Exact-main
freshness repair is operational, but retrieval-quality RSI is not. The audited
`b5b4de05` generation passed integrity verification and Recall@8, yet failed
the public quality policy at MRR `0.9167` and nDCG@8 `0.8718`. No live loop
currently edits the production ranker, passes an independent sealed corpus,
and promotes or rolls back that candidate.

## Operational Documentation
- **[CLI_REFERENCE.md](CLI_REFERENCE.md)** — Verbatim menu snapshot and CLI command mappings (for 0102_gpt parsing)
- **[INTERFACE.md](INTERFACE.md)** — Public runtime interface contract (programmatic + CLI)
- **[Machine Spec (JSON)](docs/HOLO_INDEX_MACHINE_LANGUAGE_SPEC_0102.json)** — Canonical machine-readable architecture/spec contract
- **[Machine Spec (Markdown)](docs/HOLO_INDEX_MACHINE_LANGUAGE_SPEC_0102.md)** — Human-readable first-principles architecture analysis
- [Operational Playbook](docs/OPERATIONAL_PLAYBOOK.md) — step-by-step pre-code checklist, TODO workflow, and doc compliance rules for 0102.
- [Telemetry & Breadcrumb Guide](docs/MULTI_AGENT_BREADCRUMB_EXAMPLE.md) ― how to follow the live JSONL stream (`holo_index/logs/telemetry/`) and coordinate hand-offs between sessions.
- [CLI Refactoring Plan](docs/CLI_REFACTORING_PLAN.md) ― deeper design notes for the search/CLI pipeline.
- **Offline Mode** ― run `python holo_index.py --offline --search "..."` to avoid model downloads and auto-install; cached model loads if present, otherwise lexical fallback is used.
- **Fast Search Mode** ― run `python holo_index.py --offline --fast-search --search "..."` (or set `HOLO_FAST_SEARCH=1`) to skip heavy advisor/orchestration steps for low-latency retrieval.

### Generation-Bound Retrieval AutoResearch (2026-08-01)

`holo_index.retrieval_autoresearch` evaluates a pinned semantic generation
against immutable train/public-regression corpus digests. The legacy
`heldout_cases` field means only "excluded from train"; the checked-in queries
are not independent promotion evidence. It emits per-query generation
receipts and deterministic Recall@K, MRR, nDCG@K, and latency metrics. A
deterministic verifier recomputes the metrics before a candidate can be
reported as measured-better on that public regression corpus.

This is a shadow evaluation boundary, not an indexer. It never re-indexes,
changes ranking heuristics, writes outcomes, or promotes a generation. A
comparison result is integrity evidence only; a separate sealed evaluation and
signed WRE authority transaction must authorize any later promotion.

`m2m_holo_retrieval_grade_gate` is the next authority boundary. It requires the
public regression to pass plus a signature-verifier-approved evaluation over at least 30
sealed cases disjoint from the checked-in corpus. Recall@K, MRR, and nDCG@K
must each be at least `0.95`, and p95 semantic-query latency must be at most
`5000ms`. Acceptance is A-grade evidence only: the gate cannot reindex, change
the ranker, write repository artifacts, or authorize promotion.
Its backend-content-bound callable AI Overseer facade re-runs the governed
public corpus, pins semantic mode, and requires every query receipt to carry
the ranker digest computed by the owner from the retrieval modules it actually
loaded. It does not trust caller-supplied public status flags or a digest of a
different clean authority checkout.
The thresholds are non-downgradable. The facade is backend-content-bound but
has no non-test/VSIX caller or independently administered evaluator/signing trust yet,
so it is not an operational RSI loop. The source-ranker digest also does not
yet bind the owner Python executable, ABI/platform, exact dependency manifest,
backend builds, or deterministic execution knobs; that reproducibility layer
must be sealed once and carried as a separate runtime-environment digest.

### Operational Storage and Restricted-Worker Queries (2026-07-18)

HoloIndex storage is resolved once by the canonical contract: explicit
ssd_path or --ssd, then HOLOINDEX_SSD_PATH, then the legacy HOLO_SSD_PATH,
then a platform-safe absolute default. Query-only mode requires an existing
sealed `vectors/query_snapshots` set and does not require or open
`vectors/chroma.sqlite3`. It also does not import the maintenance-only
`chromadb` dependency, and it creates no directories, collections, or
repository activity log.

Chroma PersistentClient can perform internal SQLite writes even during a
logical query. The supported RedDog operational adapter therefore does not
open Chroma directly; it uses the authenticated owner at literal
`127.0.0.1`. This application/API separation is not an operating-system
privilege boundary: deployments that require hard isolation must also deny the
worker OS identity write access to the store. An externally supervised
deployment configures RedDog with
HOLOINDEX_QUERY_SERVICE_URL/token; automatic startup instead uses a
process-private authenticated handoff and never exports its generated token to
the parent environment. The owner accepts semantic queries only and returns
CURRENT only when the exact repository HEAD and all seven canonical baseline
source-scope manifests are proven before and after the query. Every collection
must also carry the same backend/model/artifact fingerprint used by the live
query encoder. Phase 1 forces fp32 SentenceTransformer queries, disables the
generation-unbound SearchCache, and requires restart rather than crossing
generations. Owner strict-semantic mode rejects collection/model/encode/query
failure instead of presenting lexical or exact-symbol fallback as semantic.

Raw persistent `--search` and persistent `--bundle-json` reads use the same
fail-closed admission proof before constructing a backend. The invoking
repository root and SSD must match the current receipt; the clean HEAD,
generation, complete canonical baseline, embedding space, and inactive
maintenance state must also be proven. Denials expose stable, content-free
reason codes. Admission derives the receipt only from the resolved SSD; an
explicit override must canonicalize to that exact path and have no final
link/reparse component or it fails before reading. `--offline` /
`--fast-search` bypasses the persistent store and
is explicitly labeled degraded current-repository lexical retrieval. Raw CLI
and bundle lexical modes share the same root-confined loader. NAVIGATION is
rejected if it exceeds its byte cap. WSP metadata is built with bounded reads
from the invoking repository's authoritative `WSP_framework/src`; the lexical
path never reads an SSD summary. Module hints are relative-only. Absolute,
traversal, symlink, and Windows reparse escapes fail closed. Nested module
enumeration is no-follow and capped; module-domain and WSP discovery inspect
at most `cap + 1` entries and reject oversized directories instead of using a
partial filesystem-order-dependent result. Module file discovery applies the
same complete-or-empty rule to global entry overflow, depth overflow, and scan
errors, and sorts only a complete verified result.

Maintenance is owned by the trusted host. Startup may route a maintenance
request through governed WRE dispatch, but neither WRE routing nor the query
adapter grants a worker direct index-write authority. Use --index or
--index-all for the exact baseline of code, symbols, WSP, tests, skills, docs,
and knowledge. Partial refresh receipts update only collections that actually
succeeded; untouched proof is carried forward or marked UNVERIFIED.

The canonical baseline uses Git-tracked sources only, full raw-content
manifests, fixed versioned source scopes, and zero recorded source-read, cap,
or Python-AST failures. Other format parsers retain their documented legacy
behavior and are not covered by a blanket zero-parse-failure claim.
Symbol/WSP/web root overrides and caps are diagnostic; they cannot replace a
canonical complete proof. Work ledger and vocabulary remain optional
collections outside the seven-collection baseline. Maintenance requires a
canonical fp32 semantic backend before any collection reset. The offline cache
resolver accepts only a complete referenced Hugging Face snapshot; blank or
legacy embedding-space proof triggers a governed refresh instead of READY.

Every CLI or incremental maintenance run must begin from a proven-clean Git
worktree. It acquires the cross-process maintenance lease and atomically
publishes an IN_PROGRESS receipt before opening mutable collections. Query
owners probe that lease before and after retrieval. A final PASS receipt is
published only after the entire declared collection plan succeeds at the same
Git HEAD; incomplete plans and receipt-write failures leave the invalidation
in place and return a nonzero/FAILED result. Clean exact HEAD is re-proved
again after final collection snapshot verification and immediately before
PASS publication; a last-boundary dirty/change result leaves IN_PROGRESS in
place. Phase 1 also assumes an exclusive
repository-writer window during full refresh. The lease coordinates migrated
writers only; unleased legacy collection writers and a transient edit/revert
remain cooperative-writer limitations.

Baseline collections are created with the pinned Chroma HNSW persistence
policy. Publication verifies that SQLite records that exact policy and that
every baseline vector segment has a complete, non-symlinked persisted HNSW
artifact set before running its cold-open nearest-neighbor proof. A transient
successful reopen cannot certify a segment that lacks those durable files;
the maintenance generation remains unpublished and must be rebuilt by the
governed writer.

This POC scope covers the RedDog operational consumers wired to the owner
adapter. The legacy `modules/infrastructure/foundups_mcp_bridge/src/holo_tools.py`
surface still opens the persistent store directly and is registered for a
separate migration; it is not evidence that every HoloIndex consumer now uses
the owner.

### Agentic Output Stream (WSP 87/75/90)
- **Throttled Sections**: AgenticOutputThrottler now enforces `max_sections` automatically; additional sections are suppressed with an inline hint to re-run with `--verbose`.
- **ASCII-Only Signals**: Success/error banners are pure ASCII (`[GREEN]`, `[YELLOW]`, `[ERROR]`) so Unicode scrubbers stay dormant by default.
- **Single Rendering Path**: CLI search results are routed through `throttler.display_results()` + `render_prioritized_output()`—no duplicate collate logic.
- **Adaptive History**: Optional runs log retrieval observations; those records
  do not directly change or authorize the production ranker.
- **Memory Value Score (MVS)**: `[MEMORY]` cards include a 1-10 score derived from doc type priority plus entrypoint/WSP foundation boosts.
- **History Gating**: Output history logging can be limited with `HOLO_OUTPUT_HISTORY_MODE=verbose|errors|signals` and rotated via `HOLO_OUTPUT_HISTORY_MAX_MB` (default 10MB).
- **Intent Verbosity Caps**: OutputComposer now enforces per-intent limits (minimal/balanced/detailed) to keep results only to what 0102 needs.
- **Bundle Fastpath**: `--bundle-json` with `HOLO_SKIP_MODEL=1` now includes path-based code hits when `--bundle-module-hint` is provided.
## Revolutionary Architecture

> **Historical vision, not current production truth.** The implementation
> below contains useful observation and proposal components, but stored logs,
> self-scored effectiveness, and model output do not prove recursive
> improvement. The generation-bound and A-grade contracts above are the
> current authority for retrieval quality.

### [AI] HoloDAE - Chain-of-Thought Logging for Recursive Self-Improvement
**The act of using HoloIndex IS the monitoring trigger!**

**[TARGET] Chain-of-Thought Algorithm**: Every Holo interaction is logged for AI self-improvement!

When 0102 runs a search, HoloDAE executes current features (health checks, vibecoding, etc.) and logs its complete decision-making process internally:

#### Chain-of-Thought Features (Logged for Self-Improvement):
- [OK] **Decision Logging**: Every analysis choice with reasoning
- [OK] **Effectiveness Scoring**: AI evaluates its own performance
- [OK] **Pattern Recognition**: Learns from successful vs unsuccessful analyses
- [PARTIAL] **Recursive Improvement**: observations are stored; verified
  ranker improvement, promotion, canary, and rollback remain unproven
- [OK] **012 Monitoring**: Logs visible for system tweaking and oversight

#### Current HoloDAE Features (Executed Automatically):
- [OK] **Health Checks**: Automatic dependency audits and module analysis
- [OK] **Vibecoding Detection**: Pattern analysis for behavioral coaching
- [OK] **File Size Analysis**: Architectural health monitoring
- [OK] **Module Analysis**: System-wide dependency checking
- [OK] **Real-time Execution**: All features run based on query context

### [SEARCH] Enhanced Search Intelligence
- **Vector Database**: ChromaDB for semantic similarity
- **Video Index Safety**: Subprocess health probe + safe batch indexing to avoid native segfaults
- **Dual Search**: Code + WSP documentation
- **NAVIGATION.py Integration**: Problem->Solution mapping
- **Adaptive Learning**: Query enhancement and pattern learning
- **Automatic Health Checks**: Every search triggers module dependency analysis
- **Ghost Hit Filtering**: Similarity threshold (`HOLO_MIN_SIMILARITY=0.35`) eliminates low-relevance results near vector centroid
- **Robust Deduplication**: Path normalization (Windows/Unix, absolute/relative) prevents duplicate hits
- **Batched Symbol Indexing**: ChromaDB writes chunked at 5000 entries to prevent overflow on large codebases
- **Web Asset Indexing**: `public` HTML/JS/CSS assets are indexed into code memory for UI retrieval
- **Quiet by Default**: Chain-of-thought and health OK messages suppressed; enable with `HOLO_VERBOSE=1`

### Search Quality Tuning (Env Vars)
| Variable | Default | Purpose |
|----------|---------|---------|
| `HOLO_MIN_SIMILARITY` | `0.35` | Minimum similarity score (0.0-1.0). Increase to reduce noise, decrease for broader recall. |
| `HOLO_VERBOSE` | `0` | When `1`, prints chain-of-thought orchestration steps and per-module health status to stdout. |
| `HOLO_OUTPUT_HISTORY_MODE` | `verbose` | Controls history logging: `verbose`, `errors`, `signals`. |
| `HOLO_OUTPUT_HISTORY_MAX_MB` | `10` | Max size for output history log rotation. |
| `HOLO_SYMBOL_AUTO` | `1` | Auto-index symbols during `--index-code`. Set `0` to skip. |
| `HOLO_INDEX_WEB` | `1` | Include web assets in code index during `--index-code`. |
| `HOLO_WEB_INDEX_ROOTS` | `public` | Semicolon-separated roots for web indexing (relative or absolute). |
| `HOLO_WEB_INDEX_EXTENSIONS` | `.html;.js;.mjs;.cjs;.jsx;.ts;.tsx;.css` | File extensions indexed as web assets. |
| `HOLO_WEB_INDEX_MAX_FILES` | `0` | Uncapped by default. A positive cap makes a targeted run diagnostic/incomplete and cannot publish canonical proof. |
| `HOLO_WEB_INDEX_MAX_CHARS` | `5000` | Max normalized content chars embedded per web file. |

These source-shaping variables apply to targeted diagnostics. Trusted
--index-all uses the canonical tracked source policy; its manifest always
hashes full raw file content even when the embedded snippet is bounded.

### [MEMORY] Retrieval Contract (0102 System)
HoloIndex is the semantic memory retrieval system. It must be self-maintaining and semantic-first.

**Tool boundary (truth-recorded by PR #704 audit)**: HoloIndex **complements** `grep`/`glob` — it does not replace them. Use `grep`/`rg` and `glob` as the authoritative tools for exact-text, exact-symbol, and known-path lookups. Use HoloIndex for semantic / intent / role / WSP-alias discovery where the literal token is not known. The two paradigms are different retrieval modes; both remain in the 0102 toolkit.

Principles:
- **Semantic first**: meaning-based discovery is the default path here.
- **Symbol-aware**: function/class signatures + docstrings are searchable.
- **NAVIGATION is minimal**: entry points only, not every new function.
- **Complements grep/glob**: semantic/intent queries land here; `grep`/`rg` remain authoritative for exact-text and exact-symbol lookups; `glob` remains authoritative for known-path queries.
- **rg is a safety net**: an internal exact-match fallback inside HoloIndex (via `_rg_symbol_search`), not the primary path of HoloIndex itself.
- **Index once, search forever**: use symbol indexing to keep memory fresh.

Symbol indexing (module-scoped):
```
python holo_index.py --index-symbols --symbol-roots modules/ai_intelligence/pqn_alignment
```

Automatic symbol indexing:
- `--index-code` now auto-indexes symbols (default roots: `modules/`).
- Override roots with `HOLO_SYMBOL_ROOTS` or `--symbol-roots`.
- If `--module` is provided, symbols are scoped to that module.
- Disable with `HOLO_SYMBOL_AUTO=0`.

If semantic search fails on new work, run symbol indexing before adding NAVIGATION entries.

### Outer Layer Memory Participation (FoundUps Agent Market)
- FAM artifacts under `modules/foundups/agent_market/` participate in Holo retrieval as module memory targets.
- Tier-0 retrieval targets for FAM: `README.md` and `INTERFACE.md`.
- Tier-1 retrieval targets for FAM: `ROADMAP.md`, `ModLog.md`, `tests/TestModLog.md`, and `violations.md`.
- Distribution contract retrieval target: `src/interfaces.py:DistributionService` and `src/in_memory.py:publish_verified_milestone`.
- Refresh indexes after spec or contract updates:
```bash
python holo_index.py --index-all
```

### [BOT] Multi-Agent Coordination
- **LLM Integration**: Qwen-Coder 1.5B for code understanding
- **WSP Master**: Comprehensive protocol guidance (95+ protocols)
- **Pattern Coach**: Behavioral pattern detection and coaching
- **HoloDAE Intelligence**: Real-time code health monitoring

### 3. 0102 Consciousness Guidance
- **0102-to-0102 Prompts**: Violation-aware compliance prompts written by 0102 for 0102
- **Module-Specific WSP Guidance**: Contextual protocols based on detected module
- **Violation Prevention**: Reminders based on WSP_MODULE_VIOLATIONS.md history
- **Deep Think Enforcement**: Prevents vibecoding through consciousness prompts
- **Core WSP Questions**: "Does this need to exist?", "Can I afford it?", "Can I live without it?"
- **DAE Cube Organizer**: `--init-dae` command for alignment and structure mapping

### 4. Intelligent Subroutine Analysis
- **Algorithmic Analysis**: Runs size checks, duplication detection, health scans only when needed
- **Query Intent Detection**: Analyzes search intent to trigger relevant subroutines
- **Violation-Only Display**: Shows analysis results only when actual violations are found
- **Module-Specific Intelligence**: Knows which modules have violation history
- **Performance Optimized**: No wasted analysis on read-only queries

## Architecture
```
holo_index/
+-- _cli_main.py              # Main CLI interface
+-- qwen_advisor/            # AI advisor system
[U+2502]   +-- advisor.py          # Multi-source intelligence synthesis
[U+2502]   +-- wsp_master.py       # WSP protocol intelligence
[U+2502]   +-- pattern_coach.py    # Behavioral coaching
[U+2502]   +-- llm_engine.py       # Qwen LLM integration
+-- adaptive_learning/       # Phase 3 learning system
+-- dae_cube_organizer/     # DAE structure intelligence
+-- module_health/          # Health monitoring
+-- tests/                  # Test suite
+-- scripts/                # Utility scripts
+-- docs/                   # Documentation
```

## Complete HoloIndex + HoloDAE Function Reference

### [SEARCH] HOLOINDEX CORE SEARCH (5 functions):

**[DATA] Semantic Code Search**
```bash
python holo_index.py --search "send chat message"
```

**[SEARCH] Dual Search (Code + WSP docs)**
```bash
python holo_index.py --search "stream resolver"
# Searches both code and WSP documentation simultaneously
```

**[OK] Module Existence Check**
```bash
python holo_index.py --check-module "youtube_auth"
# WSP 50 compliance - MUST use before creating new code
```

**[U+1F3B2] DAE Cube Organizer**
```bash
python holo_index.py --init-dae "YouTube Live"
# Initializes DAE context and provides cube structure guidance
```

**[UP] Index Management**
```bash
python holo_index.py --index-all
# Rebuilds search indexes for optimal performance
```

**[DATA] CodeIndex Reports (WSP 93)**
```bash
python holo_index.py --code-index-report modules/communication/livechat
# Generates surgical intelligence report for module health
# Reports saved to: holo_index/reports/CodeIndex_Report_*.md
```

### [AI] HOLODAE INTELLIGENCE & ANALYSIS (8 functions):

**[SEARCH] Health Analysis (Automatic)**
- Triggered automatically on all HoloIndex searches
- Performs dependency audits and module health checks

**[RULER] File Size Analysis (Automatic)**
- Monitors architectural health and identifies large files
- Provides refactoring recommendations for files >1000 lines

**[U+1F3D7]️ Module Analysis (Automatic)**
- System-wide dependency checking and structure validation
- Identifies orphaned files and connection opportunities

**[LINK] Chain-of-Thought Logs (Logged)**
```bash
# View AI decision-making logs:
tail -f holo_index/logs/holodae_activity.log
# Shows: [COT-DECISION] health_check: Query contains health keywords
```

**[U+1F441]️ Real-time File Monitoring**
```bash
# Start autonomous monitoring (like YouTube DAE):
python main.py  # Select option 2 -> 25
```

**[U+1F3E5] Background Health Scans**
- Continuous system monitoring when HoloDAE is active
- Automatic health checks every few minutes

**[UP] Effectiveness Scoring**
- AI evaluates its own performance (0.0-1.0 scores)
- Logged for recursive improvement analysis

**[REFRESH] Recursive Improvement Data**
- Stored learning data from all AI interactions
- Used for continuous system optimization

### [CLIPBOARD] WSP COMPLIANCE & GOVERNANCE (5 functions):

**[U+1F575]️ Orphan Analysis (WSP 88)**
```bash
python holo_index.py --wsp88
# Finds connection opportunities vs traditional "orphans"
```

**[NOTE] Compliance Checking**
- Automatic WSP protocol validation during searches
- Violation-aware guidance and recommendations

**[BOOKS] Documentation Audit**
```bash
python holo_index.py --audit-docs
# Checks completeness of README.md and INTERFACE.md files
```

**[TARGET] 0102 Consciousness Prompts**
```bash
python holo_index.py --search "livechat message"
# Shows: [U+26A0]️ 0102: Livechat module exceeded 1000+ lines - WSP 62 violation!
# Shows: [AI] 0102: Deep think: Can this be simplified? Follow WSP simplicity.
```

**[REFRESH] Intelligent Subroutines**
- Algorithmic analysis triggering based on query intent
- Only runs relevant checks (health, size, etc.) when needed

### [BOT] AI ADVISOR & LLM INTEGRATION (5 functions):

**[AI] LLM Advisor**
```bash
python holo_index.py --search "create module" --llm-advisor
# Qwen-Coder guidance with code comprehension
```

**[U+1F4AC] Pattern Coach**
- Behavioral pattern detection and coaching
- Learns from user interaction patterns

**[U+1F4D6] WSP Master**
- 95+ WSP protocol guidance system
- Contextual protocol recommendations

**[U+2B50] Advisor Rating (Gamification)**
```bash
python holo_index.py --search "create module" --llm-advisor --advisor-rating useful
# Earn points: +5 for index refresh, +3 for advisor usage, +2/+1 for ratings
```

**[OK] Reminder Acknowledgment**
```bash
python holo_index.py --search "create module" --llm-advisor --ack-reminders
# Confirms advisor reminders were acted upon (+1 point)
```

## DAE Operations (Main Menu Integration)

Access all DAE operations through the main menu:
```bash
python main.py
# Then select from:
# 1. [U+1F4FA] YouTube Live DAE (Move2Japan/UnDaoDu/FoundUps)
# 2. [AI] HoloDAE (Code Intelligence & Monitoring) <- Functions menu above
# 3. [U+1F528] AMO DAE (Autonomous Moderation Operations)
# 4. [U+1F4E2] Social Media DAE (012 Digital Twin)
# 5. [U+1F9EC] PQN Orchestration (Research & Alignment)
# 6. [U+1F310] All DAEs (Full System)
# 7. [U+1F49A] Instance Health & Status
```

## Quick Start Examples

### Basic Search
```bash
python holo_index.py --search "send chat message"
```

### Contextual Search (Module-Aware)
```bash
python holo_index.py --search "stream resolver"
# Automatically detects platform_integration/stream_resolver module
# Shows only relevant WSP protocols and health violations
```

### 0102 Consciousness Prompts
```bash
python holo_index.py --search "livechat message"
# Shows 0102-to-0102 compliance prompts based on violation history:
# [U+26A0]️ 0102: Livechat module exceeded 1000+ lines - WSP 62 violation!
# [U+1F4D6] 0102: Did you read its README.md and INTERFACE.md first?
# [AI] 0102: Deep think: Can this be simplified? Follow WSP simplicity.
```

### Chain-of-Thought Logging (For Recursive Self-Improvement)
```bash
# 012 can see the AI's decision-making in logs for monitoring/tweaking:
tail -f holo_index/logs/holodae_activity.log

# Shows chain-of-thought decisions logged for self-improvement:
# [HOLODAE-CALL] 012 initiated HoloIndex search: 'check health status'
# [HOLODAE-FOUND] 8 files across 3 modules relevant to query
# [COT-START] Session cot_1739123456: 'check health status' with 8 files, 3 modules
# [COT-DECISION] health_check: Query contains health/status keywords
# [COT-DECISION] file_size_analysis: Files available: 8
# [COT-DECISION] module_health_analysis: Modules available: 3
# [COT-COMPLETE] Session cot_1739123456: 3 decisions, effectiveness 0.85
# [COT-STORED] Session cot_1739123456 stored for recursive improvement analysis

# The AI uses this logged data to improve future decision-making
# 012 can analyze these logs to understand and tweak system behavior
```

### With AI Advisor
```bash
python holo_index.py --search "create module" --llm-advisor
```

### Rate Advisor Quality (Earn Points)
```bash
python holo_index.py --search "create module" --llm-advisor --advisor-rating useful
```

### Acknowledge Reminders (Earn Points)
```bash
python holo_index.py --search "create module" --llm-advisor --ack-reminders
```

### DAE Initialization
```bash
python holo_index.py --init-dae "YouTube Live"
```

### Index Refresh
```bash
python holo_index.py --index-all
```

## WSP Compliance
- **WSP 87**: Code Navigation Protocol implementation
- **WSP 35**: HoloIndex Qwen Advisor Plan
- **WSP 49**: Module Directory Structure
- **WSP 50**: Pre-Action Verification
- **WSP 84**: Code Memory Verification
- **WSP 80**: Cube-Level DAE Orchestration

## Reward & Gamification System [TARGET]
HoloIndex uses a gamification system to encourage quality behaviors:

### Point System
- **+5**: Index refresh (keep knowledge current)
- **+3**: Using AI advisor for guidance
- **+5/+2**: Rating advisor quality (useful/not useful)
- **+1**: Acknowledging advisor reminders
- **+10/+5/+3**: Health issue detection (critical/medium/low severity)

### How It Works
- **Who Gets Points**: The 0102 Architect (you!) for quality behaviors
- **Purpose**: Encourages proactive compliance and tool usage
- **Tracking**: Session summaries show earned points
- **Variants**: Different reward multipliers (currently variant A)

## Performance
- **Search Speed**: <200ms dual search
- **LLM Inference**: <500ms with caching
- **Index Size**: ~500MB for full codebase
- **Memory Usage**: <1GB with models loaded
- **Token Efficiency**: 93% reduction vs traditional

## Dependencies
- Python 3.8+
- ChromaDB (vector database)
- sentence-transformers (embeddings)
- llama-cpp-python (LLM inference)
- SQLite (violation tracking)

## Status
[OK] **PRODUCTION READY** - All systems operational with comprehensive AI intelligence
