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
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
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
HOLO_MODEL_IMPORT_TIMEOUT = float(os.getenv("HOLO_MODEL_IMPORT_TIMEOUT", "5"))  # 5s default
HOLO_MODEL_LOAD_TIMEOUT = float(os.getenv("HOLO_MODEL_LOAD_TIMEOUT", "10"))     # 10s default
HOLO_ENCODE_TIMEOUT = float(os.getenv("HOLO_ENCODE_TIMEOUT", "3"))              # 3s default
HOLO_SEARCH_TIMEOUT = float(os.getenv("HOLO_SEARCH_TIMEOUT", "15"))             # 15s default


def _run_with_timeout(func, timeout_sec: float, default=None, error_msg: str = "Operation timed out"):
    """
    Execute a function with a hard timeout using ThreadPoolExecutor.
    Returns default value on timeout or exception instead of hanging.

    WSP 97: Prevents indefinite hangs in HoloIndex operations.
    """
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func)
        try:
            return future.result(timeout=timeout_sec)
        except FuturesTimeoutError:
            logging.getLogger(__name__).warning(f"{error_msg} (>{timeout_sec}s)")
            return default
        except Exception as e:
            logging.getLogger(__name__).warning(f"{error_msg}: {e}")
            return default


def _import_sentence_transformers():
    """Import SentenceTransformer with timeout protection."""
    from sentence_transformers import SentenceTransformer as ST
    return ST


def _load_model(model_class, model_name: str):
    """Load the model with timeout protection."""
    return model_class(model_name)


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

        self._log_agent_action("Loading sentence transformer (cached on SSD)...", "MODEL")
        os.environ['SENTENCE_TRANSFORMERS_HOME'] = str(self.models_path)

        model_name = "all-MiniLM-L6-v2"
        offline = os.getenv("HOLO_OFFLINE") == "1"
        model_cached = self._model_cache_present(model_name)

        # Optional fast-start skip to prevent long imports (set HOLO_SKIP_MODEL=1)
        if os.environ.get("HOLO_SKIP_MODEL") == "1":
            self._log_agent_action("HOLO_SKIP_MODEL=1 -> skipping sentence transformer load", "WARN")
            self.model = None
        elif offline and not model_cached:
            self._log_agent_action("HOLO_OFFLINE=1 and model cache missing -> skipping model load", "WARN")
            self.model = None
        else:
            global SentenceTransformer
            if SentenceTransformer is None:
                # WSP 97: Import with hard timeout to prevent indefinite hangs
                self._log_agent_action(f"Importing SentenceTransformer (timeout={HOLO_MODEL_IMPORT_TIMEOUT}s)...", "MODEL")
                SentenceTransformer = _run_with_timeout(
                    _import_sentence_transformers,
                    timeout_sec=HOLO_MODEL_IMPORT_TIMEOUT,
                    default=None,
                    error_msg="SentenceTransformer import timed out"
                )
                if SentenceTransformer is None:
                    self._log_agent_action("SentenceTransformer unavailable; falling back to lexical search", "WARN")

            if SentenceTransformer:
                # WSP 97: Load model with hard timeout
                self._log_agent_action(f"Loading model '{model_name}' (timeout={HOLO_MODEL_LOAD_TIMEOUT}s)...", "MODEL")
                self.model = _run_with_timeout(
                    lambda: _load_model(SentenceTransformer, model_name),
                    timeout_sec=HOLO_MODEL_LOAD_TIMEOUT,
                    default=None,
                    error_msg=f"Model '{model_name}' load timed out"
                )
                if self.model is None:
                    self._log_agent_action("Model load failed; falling back to lexical search", "WARN")
            else:
                self.model = None

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

    def index_test_registry(self) -> None:
        """WSP 98: Ingest the WSP Test Registry into ChromaDB for semantic search."""
        from .indexing_engine import index_test_registry as _idx_test
        _idx_test(self)

    def index_skillz_entries(self) -> None:
        """WSP 95: Index SKILLz files for agent discovery."""
        from .indexing_engine import index_skillz_entries as _idx_skillz
        _idx_skillz(self)

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
        """
        WSP Compliance: Check if a module exists before code generation.
        This method should be called by 0102 agents before creating ANY new code.
    
        Args:
            module_name: Name of the module to check (e.g., "youtube_auth", "livechat")
    
        Returns:
            Dict containing:
            - exists: bool - Whether the module exists
            - path: str - Full path if exists
            - readme_exists: bool - Whether README.md exists
            - interface_exists: bool - Whether INTERFACE.md exists
            - tests_exist: bool - Whether tests directory exists
            - wsp_compliance: str - Basic compliance status
            - recommendation: str - What 0102 should do next
        """
        from pathlib import Path
    
        project_root = Path(__file__).resolve().parents[2]
        normalized = module_name.strip().strip("/\\")
        normalized = normalized.replace("\\", "/")
    
        domains = [
            "modules/ai_intelligence",
            "modules/communication",
            "modules/platform_integration",
            "modules/infrastructure",
            "modules/monitoring",
            "modules/development",
            "modules/foundups",
            "modules/gamification",
            "modules/blockchain"
        ]
        domain_names = {Path(d).name for d in domains}
    
        candidate_paths = []
        if normalized:
            candidate_paths.append(project_root / normalized)
            if normalized.startswith("modules/"):
                parts = normalized.split("/")
                if len(parts) >= 3:
                    domain_part = parts[1]
                    module_part = parts[2]
                    candidate_paths.append(project_root / "modules" / domain_part / module_part)
            else:
                parts = normalized.split("/")
                if len(parts) >= 2 and parts[0] in domain_names:
                    domain_part = parts[0]
                    module_part = parts[1]
                    candidate_paths.append(project_root / "modules" / domain_part / module_part)
                if len(parts) >= 3 and parts[0] == "modules":
                    domain_part = parts[1]
                    module_part = parts[2]
                    candidate_paths.append(project_root / "modules" / domain_part / module_part)
    
        module_basename = normalized.split("/")[-1] if normalized else module_name.strip()
        for domain in domains:
            domain_path = project_root / domain
            candidate_paths.append(domain_path / module_basename)
    
        module_path = None
        seen = set()
        for candidate in candidate_paths:
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            if resolved.exists() and resolved.is_dir():
                module_path = resolved
                break
    
        if not module_path:
            similar_modules = []
            key = normalized.lower() if normalized else module_name.lower()
            for need, location in self.need_to.items():
                if key in need.lower() or key in location.lower():
                    path_parts = location.split('/')
                    if len(path_parts) >= 3 and path_parts[0] == 'modules':
                        module_path_str = '/'.join(path_parts[:4])
                        if module_path_str not in similar_modules:
                            similar_modules.append(module_path_str)
    
            return {
                "exists": False,
                "module_name": module_name,
                "similar_modules": similar_modules,
                "recommendation": f"[BLOCKED] MODULE '{module_name}' DOES NOT EXIST - DO NOT CREATE IT! " +
                                   (f"Similar modules found: {', '.join(similar_modules)}. " if similar_modules else "") +
                                   "ENHANCE EXISTING MODULES - DO NOT VIBECODE (See WSP_84_Module_Evolution). " +
                                   "Use --search to find existing functionality FIRST before ANY code generation."
            }
    
        try:
            module_label = str(module_path.relative_to(project_root))
        except ValueError:
            module_label = str(module_path)
    
        readme_exists = (module_path / "README.md").exists()
        interface_exists = (module_path / "INTERFACE.md").exists()
        roadmap_exists = (module_path / "ROADMAP.md").exists()
        modlog_exists = (module_path / "ModLog.md").exists()
        requirements_exists = (module_path / "requirements.txt").exists()
        tests_exist = (module_path / "tests").exists()
        memory_exists = (module_path / "memory").exists()
    
        compliance_score = sum([
            readme_exists, interface_exists, roadmap_exists,
            modlog_exists, requirements_exists, tests_exist, memory_exists
        ])
    
        wsp_compliance = "[VIOLATION] NON-COMPLIANT" if compliance_score < 7 else "[COMPLIANT] COMPLIANT"
    
        health_warnings = []
        if not tests_exist:
            health_warnings.append("Missing tests directory (WSP 49)")
        if not readme_exists:
            health_warnings.append("Missing README.md (WSP 22)")
        if not interface_exists:
            health_warnings.append("Missing INTERFACE.md (WSP 11)")
    
        return {
            "exists": True,
            "module_name": module_label,
            "path": str(module_path),
            "readme_exists": readme_exists,
            "interface_exists": interface_exists,
            "roadmap_exists": roadmap_exists,
            "modlog_exists": modlog_exists,
            "requirements_exists": requirements_exists,
            "tests_exist": tests_exist,
            "memory_exists": memory_exists,
            "wsp_compliance": wsp_compliance,
            "compliance_score": f"{compliance_score}/7",
            "health_warnings": health_warnings,
            "recommendation": f"Module '{module_label}' exists at {module_path}. " +
                               (f"WSP Compliance: {wsp_compliance}. " if wsp_compliance == "[VIOLATION] NON-COMPLIANT" else "[COMPLIANT] WSP Compliant. ") +
                               ("MANDATORY: Read README.md and INTERFACE.md BEFORE making changes. " if readme_exists and interface_exists else "CRITICAL: Create missing documentation FIRST (WSP_22_Documentation). ")
        }

    def _resolve_location_parts(self, location: str) -> Tuple[Optional[Path], Optional[str]]:
        """
        Parse a NAVIGATION location string into file path + optional symbol/line descriptor.
        Returns (Path, symbol_text) or (None, None) if parsing fails.
        """
        if not location:
            return None, None

        normalized = location.strip()
        if not normalized:
            return None, None

        symbol = None
        split_idx = normalized.rfind(':')
        filepath = normalized

        if split_idx > 1:
            filepath = normalized[:split_idx]
            symbol = normalized[split_idx + 1 :].strip() or None

        try:
            raw_filepath = filepath.strip()

            # Some NAVIGATION/WSP sources embed titles like "path/to/file.md - Description".
            # Keep parsing strict unless the original path does not exist; then attempt safe recovery.
            filepath_candidates = [raw_filepath]
            for sep in (" - ", " — ", " – "):
                if sep in raw_filepath:
                    filepath_candidates.append(raw_filepath.split(sep, 1)[0].strip())

            resolved_first: Optional[Path] = None
            for candidate in filepath_candidates:
                if not candidate:
                    continue
                file_path = Path(candidate)
                if not file_path.is_absolute():
                    file_path = (self.project_root / candidate).resolve()
                if resolved_first is None:
                    resolved_first = file_path
                if file_path.exists():
                    return file_path, symbol

            return resolved_first, symbol
        except Exception:
            return None, symbol

    def _find_symbol_line(self, file_path: Path, symbol: Optional[str]) -> Optional[int]:
        """Heuristic search for a symbol name within a file to approximate its line number."""
        if not symbol or not file_path.exists():
            return None

        target = symbol.replace('()', '').strip()
        if not target:
            return None

        primary = target.split()[0]
        candidates = [target, primary]
        seen: set[str] = set()

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as handle:
                lines = handle.readlines()
        except Exception:
            return None

        for idx, line in enumerate(lines, start=1):
            lowered = line.lower()
            for candidate in candidates:
                key = candidate.lower()
                if key in seen:
                    continue
                if key and key in lowered:
                    seen.add(key)
                    return idx

        return None

    def _extract_typescript_entities(self, file_path: Path) -> Dict[str, Dict[str, Any]]:
        """Parse TypeScript/TSX file for entity metadata with simple caching."""
        suffix = file_path.suffix.lower()
        if suffix not in {'.ts', '.tsx', '.jsx'}:
            return {}

        try:
            stat = file_path.stat()
        except FileNotFoundError:
            return {}

        cache_entry = self._ts_entity_cache.get(str(file_path))
        if cache_entry and cache_entry.get('mtime') == stat.st_mtime:
            return cache_entry.get('entities', {})

        try:
            text = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return {}

        lines = text.splitlines()
        entities = parse_typescript_entities(lines)
        self._ts_entity_cache[str(file_path)] = {
            "mtime": stat.st_mtime,
            "entities": entities
        }
        return entities

    def _match_typescript_entity(self, symbol: Optional[str], entities: Dict[str, Dict[str, Any]]) -> Tuple[Optional[str], Optional[int]]:
        """Match a NAVIGATION symbol description to a parsed TypeScript entity."""
        if not symbol or not entities:
            return None, None

        cleaned = symbol.strip()
        if not cleaned:
            return None, None

        cleaned = cleaned.replace('()', '')
        candidates = [cleaned]

        if '(' in symbol:
            candidates.append(symbol.split('(', 1)[0])
        if ' ' in cleaned:
            candidates.append(cleaned.split(' ', 1)[0])

        for candidate in candidates:
            key = _normalize_symbol_key(candidate)
            if key and key in entities:
                entry = entities[key]
                return entry.get('preview'), entry.get('line')

        return None, None

    def _extract_ast_preview(self, filepath: str, match_line: int, context: int = 6) -> str:
        """
        0102: Extract surrounding JSX/TSX AST block for preview using fallback extraction
        
        Args:
            filepath: Path to the TypeScript/JSX file
            match_line: Line number where match was found
            context: Number of lines to include above and below
            
        Returns:
            Extracted code block for preview
        """
        try:
            from pathlib import Path
            
            file_path = Path(filepath)
            if not file_path.exists():
                return "[File not found]"
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.read().splitlines()
            
            if not lines or match_line <= 0 or match_line > len(lines):
                return "[Invalid line range]"
            
            # Calculate context boundaries
            start_line = max(0, match_line - context - 1)  # Convert to 0-based
            end_line = min(len(lines), match_line + context)
            
            # Extract the block
            preview_lines = lines[start_line:end_line]
            
            # Clean up the preview
            preview = '\n'.join(preview_lines).strip()
            
            # Limit preview length for display
            if len(preview) > 400:
                preview = preview[:400] + "..."
            
            return preview if preview else "[No preview available]"
            
        except Exception as e:
            return f"[0102 preview extraction error: {str(e)}]"

    def _enhance_code_results_with_previews(self, code_hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        0102: Enhance code results with AST-based previews for empty results
        
        Args:
            code_hits: List of code search results
            
        Returns:
            Enhanced results with previews
        """
        enhanced_hits = []
        
        for hit in code_hits:
            enhanced_hit = hit.copy()

            if enhanced_hit.get('preview'):
                enhanced_hits.append(enhanced_hit)
                continue

            location = (hit.get('location') or '').strip()
            if not location:
                enhanced_hit['preview'] = "[Location unavailable]"
                enhanced_hits.append(enhanced_hit)
                continue

            file_path, symbol = self._resolve_location_parts(location)
            if not file_path:
                enhanced_hit['preview'] = "[Location format error]"
                enhanced_hits.append(enhanced_hit)
                continue

            enhanced_hit['path'] = str(file_path)

            if not file_path.exists():
                enhanced_hit['preview'] = "[File not found]"
                enhanced_hits.append(enhanced_hit)
                continue

            preview = None
            line_num = None
            manual_preview = None

            suffix = file_path.suffix.lower()
            if symbol and suffix in {'.ts', '.tsx', '.jsx'}:
                entities = self._extract_typescript_entities(file_path)
                manual_preview, line_num = self._match_typescript_entity(symbol, entities)

            # Numeric symbol is almost certainly a line number (e.g., "file.py:336")
            if line_num is None and symbol and symbol.isdigit():
                try:
                    line_num = int(symbol)
                except ValueError:
                    line_num = None

            if line_num is None:
                line_num = self._find_symbol_line(file_path, symbol)

            if line_num:
                preview = self._extract_ast_preview(str(file_path), line_num)
                enhanced_hit['line'] = line_num
            elif manual_preview:
                preview = manual_preview
            else:
                # Default to file header for human-friendly previews (docs/config files)
                preview = self._extract_ast_preview(str(file_path), 1)
                enhanced_hit['line'] = 1

            enhanced_hit['preview'] = preview
            enhanced_hits.append(enhanced_hit)
        
        return enhanced_hits


TS_FUNCTION_PATTERN = re.compile(r'^(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+(?P<name>[A-Za-z0-9_]+)\s*\(')
TS_CLASS_PATTERN = re.compile(r'^(?:export\s+)?(?:abstract\s+)?class\s+(?P<name>[A-Za-z0-9_]+)\b')
TS_INTERFACE_PATTERN = re.compile(r'^(?:export\s+)?interface\s+(?P<name>[A-Za-z0-9_]+)\b')
TS_TYPE_PATTERN = re.compile(r'^(?:export\s+)?type\s+(?P<name>[A-Za-z0-9_]+)\b')
TS_ENUM_PATTERN = re.compile(r'^(?:export\s+)?enum\s+(?P<name>[A-Za-z0-9_]+)\b')
TS_CONST_PATTERN = re.compile(r'^(?:export\s+)?const\s+(?P<name>[A-Za-z0-9_]+)\s*(?::[^=]+)?=')
TS_ARRAY_STATE_PATTERN = re.compile(r'^(?:export\s+)?const\s+\[\s*(?P<name>[A-Za-z0-9_]+)')


def _normalize_symbol_key(symbol: str) -> str:
    """Normalize symbol names for consistent dictionary lookups."""
    if not symbol:
        return ""
    return re.sub(r'[^a-z0-9]+', '', symbol.lower())


def _build_preview_from_lines(lines: List[str], index: int, context: int = 6) -> str:
    start = max(0, index - context)
    end = min(len(lines), index + context + 1)
    preview = '\n'.join(lines[start:end]).strip()
    if len(preview) > 400:
        preview = preview[:400] + "..."
    return preview or "[No preview available]"


def parse_typescript_entities(lines: List[str], context: int = 6) -> Dict[str, Dict[str, Any]]:
    """Extract TypeScript/TSX entities (components, hooks, interfaces, etc.) from raw lines."""
    entities: Dict[str, Dict[str, Any]] = {}

    for idx, raw_line in enumerate(lines):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith('//'):
            continue

        entry: Optional[Dict[str, Any]] = None
        match = TS_ARRAY_STATE_PATTERN.match(stripped)
        if match and ('useState' in stripped or 'useReducer' in stripped):
            name = match.group('name')
            entry = {"name": name, "kind": "state"}
        else:
            for kind, pattern in (
                ("function", TS_FUNCTION_PATTERN),
                ("const", TS_CONST_PATTERN),
                ("class", TS_CLASS_PATTERN),
                ("interface", TS_INTERFACE_PATTERN),
                ("type", TS_TYPE_PATTERN),
                ("enum", TS_ENUM_PATTERN),
            ):
                match = pattern.match(stripped)
                if match:
                    name = match.group('name')
                    entry = {"name": name, "kind": kind}
                    break

        if not entry:
            continue

        normalized_key = _normalize_symbol_key(entry["name"])
        if not normalized_key:
            continue

        preview = _build_preview_from_lines(lines, idx, context)
        entities[normalized_key] = {
            "name": entry["name"],
            "line": idx + 1,
            "preview": preview,
            "kind": entry["kind"]
        }

        # Capture both state variable and setter for destructured hooks
        if entry["kind"] == "state" and 'set' in stripped:
            setter_match = re.search(r'set([A-Za-z0-9_]+)', stripped)
            if setter_match:
                setter_name = setter_match.group(1)
                setter_key = _normalize_symbol_key(setter_name)
                if setter_key and setter_key not in entities:
                    entities[setter_key] = {
                        "name": setter_name,
                        "line": idx + 1,
                        "preview": preview,
                        "kind": "state_setter"
                    }

    return entities
