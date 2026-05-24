# -*- coding: utf-8 -*-
from __future__ import annotations


"""HoloIndex Core Search Engine - WSP 87 Compliant Module Structure

# === UTF-8 ENFORCEMENT (WSP 90) ===
# Prevent UnicodeEncodeError on Windows systems
# Only apply when running as main script, not during import
if __name__ == '__main__' and sys.platform.startswith('win'):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except (OSError, ValueError):
        # Ignore if stdout/stderr already wrapped or closed
        pass
# === END UTF-8 ENFORCEMENT ===

This module provides the core HoloIndex search functionality, extracted
from the monolithic cli.py to maintain WSP 87 size limits.

WSP Compliance: WSP 87 (Size Limits), WSP 49 (Module Structure), WSP 72 (Block Independence)
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

# Dependency bootstrap for this module
try:
    import chromadb
except ImportError as exc:
    if os.getenv("HOLO_DISABLE_PIP_INSTALL") == "1" or os.getenv("HOLO_OFFLINE") == "1":
        raise ImportError("chromadb is required but auto-install is disabled (HOLO_OFFLINE/HOLO_DISABLE_PIP_INSTALL).") from exc
    print("Installing required dependencies...")
    import subprocess
    subprocess.check_call([__import__('sys').executable, "-m", "pip", "install", "chromadb"])
    import chromadb

# Lazy load sentence_transformers to prevent crash on import
SentenceTransformer = None

# Timeout configuration for blocking operations (WSP 97 pre-flight compliance)
HOLO_MODEL_IMPORT_TIMEOUT = float(os.getenv("HOLO_MODEL_IMPORT_TIMEOUT", "20"))  # 20s default (FX2-C: 5s too short for cold imports)
HOLO_MODEL_LOAD_TIMEOUT = float(os.getenv("HOLO_MODEL_LOAD_TIMEOUT", "30"))     # 30s default (FX2-C: 10s too short for cold model load)
HOLO_ENCODE_TIMEOUT = float(os.getenv("HOLO_ENCODE_TIMEOUT", "3"))              # 3s default
HOLO_SEARCH_TIMEOUT = float(os.getenv("HOLO_SEARCH_TIMEOUT", "15"))             # 15s default


def _run_with_timeout(func, timeout_sec: float, default=None, error_msg: str = "Operation timed out",
                      missing_dep_hint: str = None):
    """
    Execute a function with a hard timeout using ThreadPoolExecutor.
    Returns default value on timeout or exception instead of hanging.

    Distinguishes between:
    - Actual timeout (FuturesTimeoutError): Log as timeout with remediation hints
    - Missing dependency (ImportError/ModuleNotFoundError): Log with install hint
    - Other exceptions: Log with original error message

    WSP 97: Prevents indefinite hangs in HoloIndex operations.
    """
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

    logger = logging.getLogger(__name__)
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func)
        try:
            return future.result(timeout=timeout_sec)
        except FuturesTimeoutError:
            logger.warning(f"{error_msg} (>{timeout_sec}s). Try HOLO_SKIP_MODEL=1 or HOLO_OFFLINE=1")
            return default
        except (ImportError, ModuleNotFoundError) as e:
            # Missing dependency - distinct from timeout
            hint = missing_dep_hint or "pip install -r holo_index/requirements.txt"
            logger.warning(f"Missing dependency: {e}. Fix: {hint}")
            return default
        except Exception as e:
            logger.warning(f"{error_msg}: {e}")
            return default


def _import_sentence_transformers():
    """Import SentenceTransformer with timeout protection."""
    from sentence_transformers import SentenceTransformer as ST
    return ST


def _load_model(model_class, model_name: str):
    """Load the model with timeout protection."""
    return model_class(model_name)


def _turboquant_enabled() -> bool:
    """Return True when HOLO_USE_TURBOQUANT is set to a truthy value.

    HIA2 Phase 1 opt-in switch. When set, ``HoloIndex.__init__`` attempts
    the TurboQuant backend before falling through to the existing
    SentenceTransformer path.
    """
    return os.getenv("HOLO_USE_TURBOQUANT", "0").strip().lower() in {"1", "true", "yes", "on"}


# Search cache for fast repeated queries (WSP 91 observability)
try:
    from .search_cache import SearchCache, get_search_cache
    SEARCH_CACHE_AVAILABLE = True
except ImportError:
    SEARCH_CACHE_AVAILABLE = False
    SearchCache = None  # type: ignore
    get_search_cache = None  # type: ignore

# Optional imports (disabled for stability)
AGENT_LOGGER_AVAILABLE = False
BREADCRUMB_AVAILABLE = False
BreadcrumbTracer = None
CIRCUIT_BREAKER_AVAILABLE = False
circuit_manager = None
CircuitBreakerOpenError = Exception


class HoloIndex:
    """Dual semantic index spanning NAVIGATION entries and WSP protocols."""
    _initialized: bool = False
    _shared_state: Dict[str, Any] = {}

    def _log_agent_action(self, message: str, action_tag: str = "0102"):
        """Real-time logging for multi-agent coordination - allows other 0102 agents to follow."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        silent = os.getenv("HOLO_SILENT", "0").lower() in {"1", "true", "yes"}
        if not silent and not getattr(self, "quiet", False):
            print(f"[{timestamp}] [HOLO-{action_tag}] {message}")

        # Also log to shared file for other agents to follow
        try:
            log_file = Path("holo_index/logs/agent_activity.log")
            log_file.parent.mkdir(exist_ok=True)
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] [HOLO-{action_tag}] {message}\n")
        except:
            pass  # Don't break if logging fails

    def _announce_breadcrumb_trail(self):
        """Announce breadcrumb availability discreetly."""
        if os.getenv("HOLO_SILENT", "0").lower() in {"1", "true", "yes"}:
            return
        if self._breadcrumb_hint_shown:
            return
        if not hasattr(self, 'breadcrumb_tracer') or not self.breadcrumb_tracer:
            return
        agents = self.breadcrumb_tracer.get_recent_agents()
        if not agents:
            return
        agent_list = ", ".join(agents)
        hint = f"[BREAD] breadcrumbs available (agents: {agent_list}). Run python -m holo_index.utils.log_follower to follow."
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [BREADCRUMB] {hint}")
        self._breadcrumb_hint_shown = True

    def __init__(self, ssd_path: str = "E:/HoloIndex", quiet: bool = False) -> None:
        """
        0102: Initialize HoloIndex with WSP-compliant architecture.
        
        Args:
            ssd_path: Path to SSD for persistent storage
            quiet: Suppress initialization logs
        """
        # Fast path: reuse already-loaded state to avoid reinitializing models/Chroma
        if HoloIndex._initialized:
            self.__dict__.update(HoloIndex._shared_state)
            self.quiet = quiet  # allow caller to silence logs on reuse
            return

        self.quiet = quiet
        self._log_agent_action(f"Initializing HoloIndex on SSD: {ssd_path}", "INIT")

        # Persistent storage layout (mirrors pre-rebuild behaviour)
        self.project_root = Path(__file__).parent.parent.parent
        self.ssd_path = Path(ssd_path)
        self.vector_path = self.ssd_path / "vectors"
        self.cache_path = self.ssd_path / "cache"
        self.models_path = self.ssd_path / "models"
        self.indexes_path = self.ssd_path / "indexes"
        for path in [self.vector_path, self.cache_path, self.models_path, self.indexes_path]:
            path.mkdir(parents=True, exist_ok=True)

        self._log_agent_action("Setting up persistent ChromaDB collections...", "INFO")
        self.client = chromadb.PersistentClient(path=str(self.vector_path))
        self.code_collection = self._ensure_collection("navigation_code")
        self.wsp_collection = self._ensure_collection("navigation_wsp")
        self.test_collection = self._ensure_collection("navigation_tests")
        self.skill_collection = self._ensure_collection("navigation_skills")
        self.symbol_collection = self._ensure_collection("navigation_symbols")
        # CFZ4: New collections for semantic separation
        self.docs_collection = self._ensure_collection("navigation_docs")
        self.knowledge_collection = self._ensure_collection("navigation_knowledge")
        # Work Ledger: Slice tracking for WSP 15/60/70 work state queries
        self.work_ledger_collection = self._ensure_collection("navigation_work_ledger")

        self._log_agent_action("Loading sentence transformer (cached on SSD)...", "MODEL")
        os.environ['SENTENCE_TRANSFORMERS_HOME'] = str(self.models_path)

        model_name = "all-MiniLM-L6-v2"
        offline = os.getenv("HOLO_OFFLINE") == "1"
        model_cached = self._model_cache_present(model_name)

        # FX1-D / HIA-TAX1: retrieval_mode vs embedding_backend taxonomy
        # (semantic/lexical/failed) x (sentence_transformers/turboquant_onnx_int8/none).
        # HIA3 introduced the real int8 backend; TQ3 (2026-04-23) adds
        # per-collection routing so int8 serves only the collections TQ2 proved
        # equivalent, while fp32 stays authoritative everywhere else.
        self.retrieval_mode = "failed"
        self.embedding_backend = "none"

        # TQ3: per-collection routing state.
        #   embedders              : backend_key -> loaded embedder instance
        #   routing_active         : True only when HOLO_USE_TURBOQUANT=1 AND
        #                            both backends loaded cleanly (so every
        #                            collection can be served by its routed
        #                            choice without silent degradation).
        #   collection_backend_map : collection_name -> backend_key actually
        #                            used (truth for search_engine metadata).
        # When routing is inactive, the map falls back to the loaded primary
        # (fp32 when available) so callers still see truthful per-collection
        # backend attribution.
        from .backend_routing import (
            build_collection_backend_map,
            BACKEND_SENTENCE_TRANSFORMERS as _ROUTE_ST,
            BACKEND_TURBOQUANT as _ROUTE_TQ,
        )
        self.embedders: Dict[str, Any] = {}
        self.routing_active: bool = False
        self.collection_backend_map: Dict[str, str] = {}

        tq_requested = _turboquant_enabled()
        st_loaded = False
        tq_loaded = False

        if os.environ.get("HOLO_SKIP_MODEL") == "1":
            self._log_agent_action("HOLO_SKIP_MODEL=1 -> skipping model load (lexical mode)", "WARN")
        elif offline and not model_cached:
            self._log_agent_action("HOLO_OFFLINE=1 and model cache missing -> skipping model load (lexical mode)", "WARN")
        else:
            # Always try fp32 first: it built every live Chroma row and is the
            # authoritative baseline. Routing only degrades from here.
            global SentenceTransformer
            if SentenceTransformer is None:
                self._log_agent_action(f"Importing SentenceTransformer (timeout={HOLO_MODEL_IMPORT_TIMEOUT}s)...", "MODEL")
                SentenceTransformer = _run_with_timeout(
                    _import_sentence_transformers,
                    timeout_sec=HOLO_MODEL_IMPORT_TIMEOUT,
                    default=None,
                    error_msg="SentenceTransformer import timed out",
                    missing_dep_hint="pip install sentence-transformers (or use HOLO_SKIP_MODEL=1 for lexical-only)",
                )

            if SentenceTransformer:
                self._log_agent_action(f"Loading fp32 model '{model_name}' (timeout={HOLO_MODEL_LOAD_TIMEOUT}s)...", "MODEL")
                st_model = _run_with_timeout(
                    lambda: _load_model(SentenceTransformer, model_name),
                    timeout_sec=HOLO_MODEL_LOAD_TIMEOUT,
                    default=None,
                    error_msg=f"Model '{model_name}' load timed out",
                )
                if st_model is not None:
                    self.embedders[_ROUTE_ST] = st_model
                    st_loaded = True
                else:
                    self._log_agent_action("fp32 model load failed", "WARN")
            else:
                self._log_agent_action("SentenceTransformer unavailable", "WARN")

            # Optionally load TurboQuant int8 alongside fp32 (TQ3 routing).
            if tq_requested:
                try:
                    from .turboquant_backend import (
                        TurboQuantEmbedder,
                        BACKEND_NAME as _TQ_BACKEND_NAME,
                    )
                    if TurboQuantEmbedder.is_available():
                        self._log_agent_action(
                            "HOLO_USE_TURBOQUANT=1 -> loading int8 backend alongside fp32 (TQ3 routing)",
                            "MODEL",
                        )
                        try:
                            tq_embedder = TurboQuantEmbedder()
                            tq_embedder._ensure_loaded()
                            self.embedders[_TQ_BACKEND_NAME] = tq_embedder
                            tq_loaded = True
                        except Exception as load_err:
                            self._log_agent_action(
                                f"TurboQuant load failed ({load_err}); "
                                "routing disabled (fp32 only)",
                                "WARN",
                            )
                    else:
                        self._log_agent_action(
                            "TurboQuant not available (dep/artifacts missing); "
                            "routing disabled (fp32 only)",
                            "WARN",
                        )
                except Exception as e:
                    self._log_agent_action(
                        f"TurboQuant init failed ({e}); routing disabled (fp32 only)",
                        "WARN",
                    )

        # Resolve primary embedder and top-level taxonomy from what loaded.
        if st_loaded:
            self.model = self.embedders[_ROUTE_ST]
        elif tq_loaded:
            # Degraded: only int8 loaded. Routing cannot be active.
            self.model = self.embedders[_ROUTE_TQ]
        else:
            self.model = None

        # Routing requires opt-in AND both backends healthy.
        self.routing_active = bool(tq_requested and st_loaded and tq_loaded)

        if self.model is not None:
            self.retrieval_mode = "semantic"
            if self.routing_active:
                # Mixed mode: WSP 97 forbids overclaiming a single backend name.
                self.embedding_backend = "routed"
            elif tq_loaded and not st_loaded:
                self.embedding_backend = _ROUTE_TQ
            else:
                self.embedding_backend = _ROUTE_ST
        else:
            self.retrieval_mode = "lexical"
            self.embedding_backend = "none"

        # Per-collection backend attribution (always populated for truth).
        # CFZ4: Added navigation_docs and navigation_knowledge for semantic separation
        _collection_names = [
            "navigation_code",
            "navigation_wsp",
            "navigation_tests",
            "navigation_skills",
            "navigation_symbols",
            "navigation_vocabulary",
            "navigation_docs",       # CFZ4: module/root docs (doc_ prefix)
            "navigation_knowledge",  # CFZ4: papers/research (paper_ prefix)
            "navigation_work_ledger",  # Work Ledger: slice tracking
        ]
        self.collection_backend_map = build_collection_backend_map(
            _collection_names,
            routing_active=self.routing_active,
            available_backends=self.embedders or None,
        )

        self.need_to: Dict[str, str] = {}
        self.wsp_summary: Dict[str, Dict[str, str]] = {}
        self.wsp_summary_file = self.indexes_path / "wsp_summary.json"
        self._ts_entity_cache: Dict[str, Dict[str, Any]] = {}
        self._breadcrumb_hint_shown: bool = False
        self.breadcrumb_tracer = None

        # Load cached metadata and navigation pointers
        self._load_wsp_summary()
        self._load_navigation()

        # Initialize breadcrumb tracer for multi-agent collaboration
        if BREADCRUMB_AVAILABLE:
            try:
                self.breadcrumb_tracer = BreadcrumbTracer()
                self._log_agent_action("Breadcrumb tracer initialized for multi-agent discovery sharing", "INFO")
            except Exception as e:
                self._log_agent_action(f"Breadcrumb tracer initialization failed: {e}", "WARN")
                self.breadcrumb_tracer = None  # Ensure it's None on failure
        else:
            self.breadcrumb_tracer = None  # Ensure it's always defined

        # Initialize search cache for fast repeated queries
        if SEARCH_CACHE_AVAILABLE:
            cache_ttl = float(os.getenv("HOLO_CACHE_TTL", "300"))  # 5 min default
            cache_size = int(os.getenv("HOLO_CACHE_SIZE", "100"))
            self.search_cache = get_search_cache(max_size=cache_size, ttl_seconds=cache_ttl)
            self._log_agent_action(f"Search cache initialized (size={cache_size}, ttl={cache_ttl}s)", "INFO")
        else:
            self.search_cache = None

        # Cache state for reuse and mark initialized
        HoloIndex._shared_state = dict(self.__dict__)
        HoloIndex._initialized = True

    def get_code_entry_count(self) -> int:
        """Get count of indexed code entries."""
        try:
            return self.code_collection.count()
        except:
            return 0

    def get_wsp_entry_count(self) -> int:
        """Get count of indexed WSP entries."""
        try:
            return self.wsp_collection.count()
        except:
            return 0

    def get_symbol_entry_count(self) -> int:
        """Get count of indexed symbol entries."""
        try:
            return self.symbol_collection.count()
        except:
            return 0

    def _infer_cube_tag(self, *values: Any) -> Optional[str]:
        text = ' '.join(v for v in values if isinstance(v, str)).lower()
        if not text:
            return None
        if 'pqn' in text or 'phantom quantum' in text:
            return 'pqn'
        return None

    # --------- Collection Helpers --------- #

    def _ensure_collection(self, name: str):
        try:
            return self.client.get_collection(name)
        except Exception:
            return self.client.create_collection(name)

    def _reset_collection(self, name: str):
        try:
            self.client.delete_collection(name)
        except Exception:
            pass
        return self.client.create_collection(name)

    # --------- Data Loading --------- #

    def _load_navigation(self) -> None:
        nav_path = Path("NAVIGATION.py")
        if not nav_path.exists():
            self._log_agent_action("NAVIGATION.py not found", "WARN")
            return

        import ast
        self._log_agent_action("Loading NEED_TO map from NAVIGATION.py...", "LOAD")
        tree = ast.parse(nav_path.read_text(encoding='utf-8-sig'))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "NEED_TO":
                        self.need_to = ast.literal_eval(node.value)
                        self._log_agent_action(f"Loaded {len(self.need_to)} navigation entries", "OK")
                        return
        self._log_agent_action("NEED_TO dictionary not found in NAVIGATION.py", "WARN")

    def _load_wsp_summary(self) -> None:
        if self.wsp_summary_file.exists():
            try:
                self.wsp_summary = json.loads(self.wsp_summary_file.read_text(encoding='utf-8'))
                self._log_agent_action(f"Loaded {len(self.wsp_summary)} WSP summaries", "OK")
            except json.JSONDecodeError:
                self._log_agent_action("WSP summary cache corrupted; rebuilding will overwrite on next index", "WARN")
                self.wsp_summary = {}

    def _model_cache_present(self, model_name: str) -> bool:
        candidates = [
            self.models_path / "sentence_transformers" / model_name,
            self.models_path / model_name,
        ]
        for candidate in candidates:
            if (candidate / "config.json").exists() or (candidate / "modules.json").exists():
                return True
            if candidate.exists() and candidate.is_dir():
                return True
        return False

    def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding or return dummy vector if model unavailable."""
        if self.model:
            # show_progress_bar=False prevents 'Batches' noise in output
            return self.model.encode(text, show_progress_bar=False).tolist()
        # Return 384-dim zero vector (matches all-MiniLM-L6-v2)
        return [0.0] * 384

    # --------- Indexing --------- #

    def index_code_entries(self) -> None:
        from .indexing_engine import index_code_entries as _idx_code
        _idx_code(self)

    def _collect_web_asset_entries(self) -> List[Dict[str, str]]:
        """Collect HTML/JS/CSS assets so UI artifacts are semantically retrievable."""
        from .indexing_engine import _collect_web_asset_entries as _cwa
        return _cwa(self)

    def index_symbol_entries(self, roots: Optional[List[Path]] = None) -> None:
        """Index Python symbols (functions/classes) for semantic discovery."""
        from .indexing_engine import index_symbol_entries as _idx_sym
        _idx_sym(self, roots)

    def index_wsp_entries(self, paths: Optional[List[Path]] = None) -> None:
        from .indexing_engine import index_wsp_entries as _idx_wsp
        _idx_wsp(self, paths)

    def index_docs_entries(self):
        """CFZ4: Index module/root docs into navigation_docs collection.

        HOLOINDEX_INDEXER_ZERO_DOCS_OBSERVABILITY_PHASE1: Returns IndexResult
        for CLI observability (discovered_count, indexed_count, warning).
        """
        from .indexing_engine import index_docs_entries as _idx_docs
        return _idx_docs(self)

    def index_knowledge_entries(self) -> None:
        """CFZ4: Index papers/research into navigation_knowledge collection."""
        from .indexing_engine import index_knowledge_entries as _idx_knowledge
        _idx_knowledge(self)

    def index_test_registry(self) -> None:
        """WSP 98: Ingest the WSP Test Registry into ChromaDB for semantic search."""
        from .indexing_engine import index_test_registry as _idx_test
        _idx_test(self)

    def index_skillz_entries(self) -> None:
        """WSP 95: Index SKILLz files for agent discovery."""
        from .indexing_engine import index_skillz_entries as _idx_skillz
        _idx_skillz(self)

    def index_work_ledger_entries(self) -> None:
        """WSP 15/60/70: Index work ledger slices for slice tracking queries."""
        from .indexing_engine import index_work_ledger_entries as _idx_wl
        _idx_wl(self)

    # --------- Search --------- #

    def search(self, query: str, limit: int = 10, doc_type_filter: str = "all") -> Dict[str, Any]:
        """Search across all indexed collections.

        Delegates to search_engine.execute_search() — the search surface
        was extracted from this class for WSP 87 size compliance.
        """
        from .search_engine import execute_search
        return execute_search(self, query, limit, doc_type_filter)

    # --------- CLI Helpers --------- #

    def benchmark_ssd(self) -> None:
        """Benchmark SSD throughput and vector search latency."""
        print("\n[INFO] Benchmarking SSD performance...")
        test_file = self.cache_path / "benchmark.tmp"
        payload = b"x" * (10 * 1024 * 1024)

        start = __import__('time').time()
        with open(test_file, 'wb') as handle:
            handle.write(payload)
        write_time = __import__('time').time() - start
        write_speed = 10 / write_time if write_time else float('inf')

        start = __import__('time').time()
        with open(test_file, 'rb') as handle:
            _ = handle.read()
        read_time = __import__('time').time() - start
        read_speed = 10 / read_time if read_time else float('inf')

        try:
            test_file.unlink()
        except FileNotFoundError:
            pass

        print(f"[OK] Write speed: {write_speed:.1f} MB/s")
        print(f"[OK] Read speed:  {read_speed:.1f} MB/s")

        if self.code_collection.count() > 0:
            start = __import__('time').time()
            _ = self.search("test query", limit=1)
            elapsed = (__import__('time').time() - start) * 1000
            print(f"[PERF] Vector query time: {elapsed:.1f} ms")
        else:
            print("[WARN] Code collection empty; run --index-code first for vector benchmark")

    def check_module_exists(self, module_name: str) -> Dict[str, Any]:
        """WSP Compliance: Check if a module exists before code generation."""
        from .introspection_engine import check_module_exists as _chk
        return _chk(self, module_name)

    def _extract_typescript_entities(self, file_path: Path) -> Dict[str, Dict[str, Any]]:
        """Parse TypeScript/TSX file for entity metadata with simple caching."""
        from .introspection_engine import _extract_typescript_entities as _ets
        return _ets(self, file_path)

    def _enhance_code_results_with_previews(self, code_hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enhance code results with AST-based previews for empty results."""
        from .introspection_engine import enhance_code_results_with_previews as _enhance
        return _enhance(self, code_hits)


# Re-export for import stability: from holo_index.core.holo_index import parse_typescript_entities
from .introspection_engine import parse_typescript_entities  # noqa: F401
