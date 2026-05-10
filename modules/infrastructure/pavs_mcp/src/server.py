"""
pAVS MCP Server Implementation

WSP 103: FoundUp Federation Protocol
Exposes CABR, Gemma, Qwen, FAM, Pattern Memory, HoloIndex to federated FoundUps.

Truth boundary (WSP 97, MCPA8):
    This module is a PLACEHOLDER_STUB for backend data. Every tool body returns
    hardcoded values. However, the transport layer is REAL — start() binds a
    local HTTP port via Python stdlib http.server and accepts JSON tool calls.

    All tool responses embed `meta.implementation_status = "placeholder_stub"`
    so any client checking the canonical envelope (WSP 96 Annex A.5 C3) can
    detect the placeholder state without trusting the data.

Usage:
    python -m modules.infrastructure.pavs_mcp.src.server

    # Server binds to http://localhost:8765 by default
    # POST /tool with JSON body: {"tool_name": "...", "arguments": {...}, "api_key": "..."}
"""

import asyncio
import json
import logging
import os
import threading
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


# =============================================================================
# S2 Backend Adapter (MCPA9A — Real HoloIndex Connection)
# =============================================================================

# Repo root for backend calls (derived from this module's location)
_REPO_ROOT = Path(__file__).resolve().parents[4]
"""Repository root, used to locate HoloIndex for S2 backend calls."""

# S2 backend availability flag
_S2_BACKEND_AVAILABLE: Optional[bool] = None


def _call_s2_holo_search(
    query: str,
    *,
    limit: int = 10,
    doc_type_filter: str = "all",
    foundup_id: Optional[str] = None,
    include_shared: bool = True,
) -> dict[str, Any]:
    """Call S2 holo_search backend and return the result.

    Imports S2 holo_tools lazily to avoid circular import issues.
    Returns the S2 response envelope directly — caller adapts meta.surface.

    Raises:
        Exception: If S2 backend is unavailable or fails.
    """
    global _S2_BACKEND_AVAILABLE

    try:
        from modules.infrastructure.foundups_mcp_bridge.src.holo_tools import holo_search as s2_holo_search

        result = s2_holo_search(
            repo_root=_REPO_ROOT,
            query=query,
            limit=limit,
            doc_type_filter=doc_type_filter,
            foundup_id=foundup_id,
            include_shared=include_shared,
        )
        _S2_BACKEND_AVAILABLE = True
        return result

    except ImportError as e:
        _S2_BACKEND_AVAILABLE = False
        raise RuntimeError(f"S2 backend import failed: {e}") from e
    except Exception as e:
        # Backend available but call failed
        raise RuntimeError(f"S2 backend call failed: {e}") from e


# =============================================================================
# FAM Backend Adapter (MCPA9B — Real FAM DAEmon Connection)
# =============================================================================

# FAM backend availability flag
_FAM_BACKEND_AVAILABLE: Optional[bool] = None


def _call_fam_emit(
    foundup_id: str,
    event_type: str,
    payload: dict[str, Any],
    actor_id: str = "pAVS_MCP",
) -> dict[str, Any]:
    """Call FAM DAEmon emit() and return the result.

    Imports FAM daemon lazily to avoid circular import issues.

    Args:
        foundup_id: FoundUp emitting the event
        event_type: Event type string
        payload: Event payload dict
        actor_id: Actor performing the action (default: pAVS_MCP)

    Returns:
        Dict with event_id, success, timestamp, and persistence info.

    Raises:
        RuntimeError: If FAM backend is unavailable or fails.
    """
    global _FAM_BACKEND_AVAILABLE

    try:
        from modules.foundups.agent_market.src.fam_daemon import get_fam_daemon

        daemon = get_fam_daemon(auto_start=False)
        success, message = daemon.emit(
            event_type=event_type,
            payload=payload,
            actor_id=actor_id,
            foundup_id=foundup_id,
        )
        _FAM_BACKEND_AVAILABLE = True

        if not success:
            raise RuntimeError(f"FAM emit failed: {message}")

        return {
            "success": success,
            "message": message,
        }

    except ImportError as e:
        _FAM_BACKEND_AVAILABLE = False
        raise RuntimeError(f"FAM backend import failed: {e}") from e
    except Exception as e:
        raise RuntimeError(f"FAM backend call failed: {e}") from e


# =============================================================================
# Pattern Memory Backend Adapter (MCPA9C — Real PatternMemory Connection)
# =============================================================================

# Pattern memory backend availability flag
_PATTERN_MEMORY_AVAILABLE: Optional[bool] = None


def _call_pattern_recall(
    skill_name: str,
    min_fidelity: float = 0.90,
    limit: int = 10,
) -> list[dict]:
    """Call PatternMemory recall_successful_patterns and return patterns.

    Imports PatternMemory lazily to avoid circular import issues.
    Uses singleton pattern (PatternMemory() with no args reuses shared instance).

    Args:
        skill_name: Skill to recall patterns for
        min_fidelity: Minimum pattern fidelity threshold (0.0-1.0)
        limit: Max patterns to return

    Returns:
        List of pattern dicts with execution records.

    Raises:
        RuntimeError: If PatternMemory backend is unavailable or fails.
    """
    global _PATTERN_MEMORY_AVAILABLE

    try:
        from modules.infrastructure.wre_core.src.pattern_memory import PatternMemory

        # Singleton: calling PatternMemory() with no args reuses shared instance
        memory = PatternMemory()
        patterns = memory.recall_successful_patterns(
            skill_name=skill_name,
            min_fidelity=min_fidelity,
            limit=limit,
        )
        _PATTERN_MEMORY_AVAILABLE = True
        return patterns

    except ImportError as e:
        _PATTERN_MEMORY_AVAILABLE = False
        raise RuntimeError(f"PatternMemory backend import failed: {e}") from e
    except Exception as e:
        raise RuntimeError(f"PatternMemory backend call failed: {e}") from e


def _call_pattern_store(
    execution_id: str,
    skill_name: str,
    agent: str,
    timestamp: str,
    input_context: str,
    output_result: str,
    success: bool,
    pattern_fidelity: float,
    outcome_quality: float,
    execution_time_ms: int,
    step_count: int,
    failed_at_step: Optional[int] = None,
    notes: Optional[str] = None,
) -> None:
    """Call PatternMemory store_outcome to persist execution outcome.

    Imports PatternMemory and SkillOutcome lazily to avoid circular imports.
    Uses singleton pattern (PatternMemory() with no args reuses shared instance).

    Args:
        execution_id: Unique execution identifier
        skill_name: Skill that was executed
        agent: Agent that executed (qwen, gemma, etc.)
        timestamp: ISO format timestamp
        input_context: JSON string of input context
        output_result: JSON string of output result
        success: Whether execution succeeded
        pattern_fidelity: Fidelity score 0.0-1.0
        outcome_quality: Quality score 0.0-1.0
        execution_time_ms: Execution time in milliseconds
        step_count: Number of steps in execution
        failed_at_step: Step that failed (if any)
        notes: Optional notes

    Raises:
        RuntimeError: If PatternMemory backend is unavailable or fails.
    """
    global _PATTERN_MEMORY_AVAILABLE

    try:
        from modules.infrastructure.wre_core.src.pattern_memory import (
            PatternMemory,
            SkillOutcome,
        )

        outcome = SkillOutcome(
            execution_id=execution_id,
            skill_name=skill_name,
            agent=agent,
            timestamp=timestamp,
            input_context=input_context,
            output_result=output_result,
            success=success,
            pattern_fidelity=pattern_fidelity,
            outcome_quality=outcome_quality,
            execution_time_ms=execution_time_ms,
            step_count=step_count,
            failed_at_step=failed_at_step,
            notes=notes,
        )

        # Singleton: calling PatternMemory() with no args reuses shared instance
        memory = PatternMemory()
        memory.store_outcome(outcome)
        _PATTERN_MEMORY_AVAILABLE = True

    except ImportError as e:
        _PATTERN_MEMORY_AVAILABLE = False
        raise RuntimeError(f"PatternMemory backend import failed: {e}") from e
    except Exception as e:
        raise RuntimeError(f"PatternMemory backend call failed: {e}") from e


# =============================================================================
# Gemma Backend Adapter (MCPA9D — Real Gemma Classification)
# =============================================================================

# Gemma backend availability flag
_GEMMA_BACKEND_AVAILABLE: Optional[bool] = None

# Lazy-initialized GemmaRAGInference instance
_GEMMA_ENGINE: Optional[Any] = None


def _get_gemma_engine() -> Any:
    """Get or create the singleton GemmaRAGInference instance.

    Uses lazy initialization to avoid model loading on import.
    """
    global _GEMMA_ENGINE

    if _GEMMA_ENGINE is not None:
        return _GEMMA_ENGINE

    from holo_index.qwen_advisor.gemma_rag_inference import GemmaRAGInference

    _GEMMA_ENGINE = GemmaRAGInference()
    return _GEMMA_ENGINE


def _call_gemma_classify(
    text: str,
    categories: list[str],
) -> dict[str, Any]:
    """Call Gemma backend for text classification.

    Imports GemmaRAGInference lazily and uses _gemma_inference for
    binary/multi-class classification via prompt engineering.

    Args:
        text: Text to classify
        categories: List of category labels

    Returns:
        Dict with classification, confidence, model info.

    Raises:
        RuntimeError: If Gemma backend is unavailable or fails.
    """
    global _GEMMA_BACKEND_AVAILABLE

    try:
        engine = _get_gemma_engine()

        # Build classification prompt
        categories_str = ", ".join(categories)
        prompt = f"""Classify the following text into exactly ONE of these categories: {categories_str}

Text: {text}

Reply with ONLY the category name, nothing else.

Category:"""

        # Call Gemma inference
        result = engine._gemma_inference(prompt)

        if result["confidence"] == 0.0 and "unavailable" in result["response"].lower():
            _GEMMA_BACKEND_AVAILABLE = False
            raise RuntimeError("Gemma model unavailable")

        _GEMMA_BACKEND_AVAILABLE = True

        # Parse classification from response
        response_text = result["response"].strip()

        # Find best matching category
        classification = categories[0] if categories else "unknown"
        for cat in categories:
            if cat.lower() in response_text.lower():
                classification = cat
                break

        return {
            "classification": classification,
            "confidence": result["confidence"],
            "latency_ms": result["latency_ms"],
            "model": "gemma-3-270m",
            "raw_response": response_text,
        }

    except ImportError as e:
        _GEMMA_BACKEND_AVAILABLE = False
        raise RuntimeError(f"Gemma backend import failed: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Gemma backend call failed: {e}") from e


# =============================================================================
# Qwen Backend Adapter (MCPA9E — Real Qwen Planning)
# =============================================================================

# Qwen backend availability flag
_QWEN_BACKEND_AVAILABLE: Optional[bool] = None

# Lazy-initialized QwenInferenceEngine instance
_QWEN_ENGINE: Optional[Any] = None


def _get_qwen_engine() -> Any:
    """Get or create the singleton QwenInferenceEngine instance.

    Uses lazy initialization to avoid model loading on import.
    Resolves model path via shared_utilities.local_model_selection.
    """
    global _QWEN_ENGINE

    if _QWEN_ENGINE is not None:
        return _QWEN_ENGINE

    from modules.infrastructure.shared_utilities.local_model_selection import (
        resolve_code_model_path,
    )
    from holo_index.qwen_advisor.llm_engine import QwenInferenceEngine

    model_path = resolve_code_model_path()
    _QWEN_ENGINE = QwenInferenceEngine(
        model_path=model_path,
        max_tokens=512,
        temperature=0.3,
        context_length=2048,
    )
    return _QWEN_ENGINE


def _call_qwen_plan(
    objective: str,
    constraints: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Call Qwen backend for strategic planning.

    Imports QwenInferenceEngine lazily and uses generate_response for
    plan generation via prompt engineering.

    Args:
        objective: What to achieve
        constraints: Optional constraints dict (platform, timing, etc.)

    Returns:
        Dict with plan steps, reasoning, model info.

    Raises:
        RuntimeError: If Qwen backend is unavailable or fails.
    """
    global _QWEN_BACKEND_AVAILABLE

    try:
        engine = _get_qwen_engine()

        # Build planning prompt
        constraints_str = ""
        if constraints:
            constraints_str = "\n".join(f"- {k}: {v}" for k, v in constraints.items())
            constraints_str = f"\n\nConstraints:\n{constraints_str}"

        prompt = f"""You are a strategic planning assistant. Create a step-by-step plan.

Objective: {objective}{constraints_str}

Provide a concise 3-5 step plan. Format each step as:
Step N: [Action] - [Rationale]

Plan:"""

        # Call Qwen inference
        response = engine.generate_response(prompt, max_tokens=400)

        if response.startswith("Error:"):
            _QWEN_BACKEND_AVAILABLE = False
            raise RuntimeError(f"Qwen model unavailable: {response}")

        _QWEN_BACKEND_AVAILABLE = True

        # Parse steps from response
        import re
        steps = []
        step_pattern = re.compile(r"Step\s*(\d+)[:\.]?\s*(.+?)(?:\s*[-–]\s*(.+))?$", re.IGNORECASE)

        for line in response.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            match = step_pattern.match(line)
            if match:
                step_num = int(match.group(1))
                action = match.group(2).strip()
                rationale = match.group(3).strip() if match.group(3) else ""
                steps.append({
                    "step": step_num,
                    "action": action,
                    "rationale": rationale,
                })

        # Fallback if parsing failed but got content
        if not steps and response.strip():
            steps = [{"step": 1, "action": response.strip()[:200], "rationale": "Generated plan"}]

        # Handle empty response
        if not steps:
            raise RuntimeError("Qwen returned empty plan response")

        return {
            "plan": steps,
            "reasoning": f"Strategic plan for: {objective}",
            "model": "qwen-coder",
            "raw_response": response,
        }

    except ImportError as e:
        _QWEN_BACKEND_AVAILABLE = False
        raise RuntimeError(f"Qwen backend import failed: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Qwen backend call failed: {e}") from e


# =============================================================================
# Registry Persistence (MCPA7 — Durable FoundUp Registration)
# =============================================================================

DEFAULT_REGISTRY_DIR = Path.home() / ".pavs_mcp"
"""Default directory for registry storage. User-local, not in repo."""

REGISTRY_FILENAME = "registrations.json"
"""Registry file name within the registry directory."""

REGISTRY_PATH_ENV_VAR = "PAVS_REGISTRY_PATH"
"""Environment variable to override the registry file path."""


def _get_registry_path() -> Path:
    """Get the registry file path, respecting env var override.

    Returns:
        Path to the registry JSON file.
    """
    env_path = os.environ.get(REGISTRY_PATH_ENV_VAR)
    if env_path:
        return Path(env_path)
    return DEFAULT_REGISTRY_DIR / REGISTRY_FILENAME


# =============================================================================
# Truth Boundary Constants (WSP 97 / MCPA4)
# =============================================================================

IMPLEMENTATION_STATUS = "placeholder_stub"
"""Truth flag embedded in every tool response.

Conforming clients MUST treat any response carrying this flag as fake/test
data and refuse to use it for production decisions. See WSP 96 Annex A.5 C3.
"""

PLACEHOLDER_BANNER = (
    "==============================================================\n"
    " pAVS MCP Server - REAL_TRANSPORT + PARTIAL_BACKENDS\n"
    "--------------------------------------------------------------\n"
    "  implementation_status : partial (6/8 tools have real backends)\n"
    "  auth_enforcement      : BASIC (api_key validated)\n"
    "  scope_enforcement     : YES (cross-tenant foundup_id rejected)\n"
    "  registry_persistence  : LOCAL_JSON (survives restart)\n"
    "  server_transport      : HTTP_JSON (local, real binding)\n"
    "  holo_search           : REAL (delegates to S2/HoloIndex)\n"
    "  fam_emit              : REAL (delegates to FAM DAEmon)\n"
    "  pattern_recall        : REAL (delegates to PatternMemory)\n"
    "  pattern_store         : REAL (delegates to PatternMemory)\n"
    "  gemma_classify        : REAL (delegates to Gemma/llama_cpp)\n"
    "  qwen_plan             : REAL (delegates to Qwen/llama_cpp)\n"
    "  other tools           : HARDCODED / FAKE (CABR)\n"
    "\n"
    "  Transport is REAL. 6 tools have real backends.\n"
    "  CABR remains PLACEHOLDER.\n"
    "  Tracked remediation: MCPA10+ (remaining backends).\n"
    "=============================================================="
)
"""Operator-facing startup warning. Printed and logged on server start."""


def _truth_meta() -> dict[str, Any]:
    """Build the canonical truth-meta block embedded in every tool response.

    Returns a fresh dict (not a shared reference) so individual tool callers
    can safely mutate it without leaking state across calls.
    """
    return {
        "implementation_status": IMPLEMENTATION_STATUS,
        "real_backend": False,
        "data_source": "hardcoded_placeholder",
        "auth_enforced": False,
        "canonical_owner": False,
        "warning": (
            "This response is from a PLACEHOLDER_STUB surface. "
            "Data is hardcoded, not fetched from any backend. "
            "Do not use for production decisions."
        ),
        "wsp_reference": "WSP 96 Annex A (holo_search canonical contract)",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@dataclass
class FoundUpRegistration:
    """Registered FoundUp for pAVS access.

    MCPA1 Slice 6: This dataclass now anchors the api_key -> foundup_id
    ownership binding. The `owner_pubkey` field is stored for future
    cryptographic verification but not yet enforced.
    """
    foundup_id: str
    repo_url: str
    api_key: str
    owner_pubkey: str
    tier: str = "free"
    registered_at: str = ""

    def __post_init__(self):
        if not self.registered_at:
            self.registered_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for JSON persistence."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FoundUpRegistration":
        """Deserialize from dict."""
        return cls(**data)


class RegistryStore:
    """Durable JSON-based registry store for FoundUp registrations.

    MCPA7: Provides local persistence so API key ownership survives restart.
    Uses a simple JSON file (human-readable, debuggable).

    Behavior:
        - Creates directory and file if they don't exist.
        - Loads existing registrations on init.
        - Writes atomically (write to temp, rename) to avoid corruption.
        - Handles corrupt files by logging warning and starting empty.
        - Duplicate foundup_id replaces existing registration (re-registration).
    """

    def __init__(self, registry_path: Optional[Path] = None):
        """Initialize the registry store.

        Args:
            registry_path: Path to registry JSON file. If None, uses default
                           or env var override.
        """
        self.path = registry_path or _get_registry_path()
        self._registrations: dict[str, FoundUpRegistration] = {}
        self._api_key_to_foundup: dict[str, str] = {}
        self._load_error: Optional[str] = None
        self._load()

    def _load(self) -> None:
        """Load registrations from disk."""
        if not self.path.exists():
            logger.info(f"Registry file does not exist: {self.path} (starting empty)")
            return

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict) or "registrations" not in data:
                self._load_error = "Invalid registry format: missing 'registrations' key"
                logger.warning(f"Corrupt registry file: {self._load_error}")
                return

            for foundup_id, reg_data in data["registrations"].items():
                try:
                    reg = FoundUpRegistration.from_dict(reg_data)
                    self._registrations[foundup_id] = reg
                    self._api_key_to_foundup[reg.api_key] = foundup_id
                except (TypeError, KeyError) as e:
                    logger.warning(f"Skipping invalid registration {foundup_id}: {e}")

            logger.info(f"Loaded {len(self._registrations)} registrations from {self.path}")

        except json.JSONDecodeError as e:
            self._load_error = f"JSON decode error: {e}"
            logger.warning(f"Corrupt registry file: {self._load_error}")
        except OSError as e:
            self._load_error = f"File read error: {e}"
            logger.warning(f"Cannot read registry file: {self._load_error}")

    def _save(self) -> None:
        """Save registrations to disk atomically."""
        self.path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "registrations": {
                fid: reg.to_dict() for fid, reg in self._registrations.items()
            },
        }

        # Write to temp file then rename (atomic on POSIX, mostly atomic on Windows)
        temp_path = self.path.with_suffix(".tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            temp_path.replace(self.path)
            logger.debug(f"Saved {len(self._registrations)} registrations to {self.path}")
        except OSError as e:
            logger.error(f"Failed to save registry: {e}")
            raise

    def register(self, registration: FoundUpRegistration) -> bool:
        """Register a FoundUp, persisting to disk.

        Args:
            registration: The registration to add.

        Returns:
            True if this was a new registration, False if it replaced an existing one.
        """
        is_new = registration.foundup_id not in self._registrations

        # Remove old API key mapping if replacing
        if not is_new:
            old_reg = self._registrations[registration.foundup_id]
            if old_reg.api_key in self._api_key_to_foundup:
                del self._api_key_to_foundup[old_reg.api_key]

        self._registrations[registration.foundup_id] = registration
        self._api_key_to_foundup[registration.api_key] = registration.foundup_id
        self._save()
        return is_new

    def get_by_foundup_id(self, foundup_id: str) -> Optional[FoundUpRegistration]:
        """Get registration by FoundUp ID."""
        return self._registrations.get(foundup_id)

    def get_foundup_id_by_api_key(self, api_key: str) -> Optional[str]:
        """Get FoundUp ID by API key."""
        return self._api_key_to_foundup.get(api_key)

    @property
    def registrations(self) -> dict[str, FoundUpRegistration]:
        """Get all registrations (read-only view)."""
        return self._registrations

    @property
    def api_key_to_foundup(self) -> dict[str, str]:
        """Get API key to FoundUp ID mapping (read-only view)."""
        return self._api_key_to_foundup

    @property
    def load_error(self) -> Optional[str]:
        """Get load error message if registry was corrupt/unreadable."""
        return self._load_error


# =============================================================================
# Auth Error Codes (MCPA1 Slice 6 — Federation Auth/Scope)
# =============================================================================

AUTH_ERROR_MISSING_API_KEY = "MISSING_API_KEY"
"""Returned when a protected tool is called without an api_key."""

AUTH_ERROR_UNKNOWN_API_KEY = "UNKNOWN_API_KEY"
"""Returned when the api_key does not match any registered FoundUp."""

AUTH_ERROR_CROSS_TENANT = "CROSS_TENANT_VIOLATION"
"""Returned when foundup_id argument does not match the registered identity."""

# Protected tools: all tools EXCEPT foundup_register (bootstrap-only)
BOOTSTRAP_TOOLS = frozenset({"foundup_register"})
"""Tools that may be called without auth — bootstrap registration only."""


# =============================================================================
# HTTP Transport (MCPA8 — Real Local Transport via stdlib)
# =============================================================================


class PAVSHTTPRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for pAVS MCP Server.

    Uses Python stdlib http.server — no external dependencies.
    Routes:
        GET  /status       -> server status
        GET  /tools        -> list tools
        POST /tool         -> execute tool call
        POST /tool/{name}  -> execute tool by path
    """

    # Set by PAVSMCPServer when creating the handler
    server_instance: Optional["PAVSMCPServer"] = None

    def log_message(self, format, *args):
        """Suppress default logging (use our logger instead)."""
        logger.debug(f"HTTP: {format % args}")

    def _send_json_response(self, data: dict, status: int = 200) -> None:
        """Send a JSON response."""
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> Optional[dict]:
        """Read and parse JSON request body."""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        try:
            body = self.rfile.read(content_length)
            return json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning(f"Invalid JSON body: {e}")
            return None

    def do_GET(self) -> None:
        """Handle GET requests."""
        if self.server_instance is None:
            self._send_json_response({"error": "Server not initialized"}, 500)
            return

        if self.path == "/status":
            self._send_json_response({
                "status": "running",
                "implementation_status": IMPLEMENTATION_STATUS,
                "transport": "HTTP_JSON",
                "tools": list(self.server_instance._tools.keys()),
                "registrations_count": len(self.server_instance.registrations),
            })
        elif self.path == "/tools":
            self._send_json_response({
                "tools": list(self.server_instance._tools.keys())
            })
        else:
            self._send_json_response({"error": "Not found"}, 404)

    def do_POST(self) -> None:
        """Handle POST requests."""
        if self.server_instance is None:
            self._send_json_response({"error": "Server not initialized"}, 500)
            return

        body = self._read_json_body()
        if body is None:
            self._send_json_response({
                "error": {"code": "INVALID_JSON", "message": "Invalid JSON body"}
            }, 400)
            return

        # Route: POST /tool
        if self.path == "/tool":
            tool_name = body.get("tool_name")
            if not tool_name:
                self._send_json_response({
                    "error": {"code": "MISSING_FIELD", "message": "tool_name required"}
                }, 400)
                return
            arguments = body.get("arguments", {})
            api_key = body.get("api_key")

        # Route: POST /tool/{name}
        elif self.path.startswith("/tool/"):
            tool_name = self.path[6:]  # Strip "/tool/"
            arguments = body.get("arguments", {})
            api_key = body.get("api_key")

        else:
            self._send_json_response({"error": "Not found"}, 404)
            return

        # Execute tool call synchronously (wrap async)
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                self.server_instance.handle_tool_call(
                    tool_name=tool_name,
                    arguments=arguments,
                    api_key=api_key,
                )
            )
            self._send_json_response(result)
        finally:
            loop.close()


class PAVSMCPServer:
    """
    pAVS MCP Server exposing infrastructure to federated FoundUps.

    Tools exposed:
    - cabr_validate: V1/V2/V3 content validation
    - gemma_classify: Binary/multi-class classification
    - qwen_plan: Strategic planning
    - fam_emit: Event tracking
    - pattern_recall: Recall successful patterns
    - pattern_store: Store execution outcomes
    - holo_search: Semantic code/doc search
    - foundup_register: Register FoundUp for access
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        registry_path: Optional[Path] = None
    ):
        self.host = host
        self.port = port
        # MCPA7: Durable registry store (persists to JSON file)
        self._registry_store = RegistryStore(registry_path)
        self._tools = self._register_tools()

        # MCPA8: Real HTTP transport via stdlib
        self._http_server: Optional[HTTPServer] = None
        self._server_thread: Optional[threading.Thread] = None

    @property
    def registrations(self) -> dict[str, FoundUpRegistration]:
        """Access registrations dict (delegates to RegistryStore)."""
        return self._registry_store.registrations

    @property
    def _api_key_to_foundup(self) -> dict[str, str]:
        """Access API key mapping (delegates to RegistryStore)."""
        return self._registry_store.api_key_to_foundup

    def _register_tools(self) -> dict[str, callable]:
        """Register all MCP tools."""
        return {
            "cabr_validate": self.cabr_validate,
            "gemma_classify": self.gemma_classify,
            "qwen_plan": self.qwen_plan,
            "fam_emit": self.fam_emit,
            "pattern_recall": self.pattern_recall,
            "pattern_store": self.pattern_store,
            "holo_search": self.holo_search,
            "foundup_register": self.foundup_register,
        }

    async def cabr_validate(
        self,
        content: str,
        context: Optional[dict] = None
    ) -> dict[str, Any]:
        """
        V1/V2/V3 content validation via CABR engine.

        Args:
            content: Text content to validate
            context: Platform, audience, FoundUp context

        Returns:
            score, passed, feedback, v1/v2/v3 results
        """
        # TODO: Connect to actual CABR engine
        # from modules.foundups.agent_market.src.cabr_hooks import CABREngine

        # Placeholder implementation
        logger.info(f"CABR validate: {content[:50]}...")
        return {
            "score": 0.85,
            "passed": True,
            "feedback": "Content passes validation",
            "v1_result": {"gate": "passed"},
            "v2_result": {"verified": True},
            "v3_result": {"valuation": 0.85}
        }

    async def gemma_classify(
        self,
        text: str,
        categories: list[str],
    ) -> dict[str, Any]:
        """Classify text using Gemma backend — delegates to real backend.

        MCPA9D: S3 now delegates to the real Gemma backend via GemmaRAGInference.
        Auth/scope enforcement happens in handle_tool_call before this method.

        Args:
            text: Text to classify
            categories: Available category labels

        Returns:
            Canonical envelope with:
              - status: "ok" | "error"
              - data: classification, confidence, model info
              - meta: real_backend=true when Gemma is called successfully
        """
        logger.info(
            "S3 gemma_classify delegating to Gemma backend: text=%r categories=%r",
            text[:50] if text else "",
            categories,
        )

        # Validate inputs
        if not text:
            return {
                "status": "error",
                "data": {"classification": None, "text_length": 0},
                "error": {
                    "code": "INVALID_INPUT",
                    "message": "text is required and must be non-empty",
                },
                "meta": {
                    **_truth_meta(),
                    "tool": "gemma_classify",
                    "surface": "S3",
                    "real_backend": False,
                },
            }

        if not categories or len(categories) == 0:
            return {
                "status": "error",
                "data": {"classification": None},
                "error": {
                    "code": "INVALID_INPUT",
                    "message": "categories must be a non-empty list",
                },
                "meta": {
                    **_truth_meta(),
                    "tool": "gemma_classify",
                    "surface": "S3",
                    "real_backend": False,
                },
            }

        try:
            result = _call_gemma_classify(
                text=text,
                categories=categories,
            )

            # Build all_scores from classification result
            all_scores = {}
            for cat in categories:
                if cat == result["classification"]:
                    all_scores[cat] = result["confidence"]
                else:
                    # Distribute remaining probability
                    remaining = (1.0 - result["confidence"]) / max(1, len(categories) - 1)
                    all_scores[cat] = remaining

            return {
                "status": "ok",
                "data": {
                    "text_length": len(text),
                    "categories": categories,
                    "classification": result["classification"],
                    "confidence": result["confidence"],
                    "all_scores": all_scores,
                    "model": result["model"],
                    "latency_ms": result["latency_ms"],
                },
                "meta": {
                    "tool": "gemma_classify",
                    "surface": "S3",
                    "real_backend": True,
                    "delegated_to": "GEMMA",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                },
            }

        except Exception as e:
            logger.error(f"S3 gemma_classify backend error: {e}")

            return {
                "status": "error",
                "data": {
                    "text_length": len(text) if text else 0,
                    "categories": categories,
                    "classification": None,
                },
                "error": {
                    "code": "BACKEND_UNAVAILABLE",
                    "message": f"Gemma backend unavailable: {e}",
                },
                "meta": {
                    **_truth_meta(),
                    "tool": "gemma_classify",
                    "surface": "S3",
                    "real_backend": False,
                },
            }

    async def qwen_plan(
        self,
        objective: str,
        constraints: Optional[dict] = None
    ) -> dict[str, Any]:
        """Strategic planning via Qwen — delegates to real backend.

        MCPA9E: S3 now delegates to the real Qwen backend via adapter.
        Auth/scope enforcement happens in handle_tool_call before this method.

        Args:
            objective: What to achieve
            constraints: Time, platform, audience limits

        Returns:
            Canonical envelope with:
              - status: "ok" | "error"
              - data: plan steps, reasoning, model info
              - meta: real_backend=true when Qwen generates the plan
        """
        if not objective or not objective.strip():
            return {
                "status": "error",
                "error": {
                    "code": "INVALID_OBJECTIVE",
                    "message": "objective parameter is required and cannot be empty",
                },
                "meta": {
                    **_truth_meta(),
                    "tool": "qwen_plan",
                    "surface": "S3",
                    "real_backend": False,
                },
            }

        logger.info(
            "S3 qwen_plan delegating to Qwen backend: objective=%r constraints=%r",
            objective[:50] + "..." if len(objective) > 50 else objective,
            constraints,
        )

        try:
            # Delegate to Qwen backend
            qwen_result = _call_qwen_plan(
                objective=objective,
                constraints=constraints,
            )

            return {
                "status": "ok",
                "data": {
                    "plan": qwen_result["plan"],
                    "reasoning": qwen_result["reasoning"],
                    "model": qwen_result.get("model", "qwen-coder"),
                    "input_summary": {
                        "objective": objective[:100] + "..." if len(objective) > 100 else objective,
                        "constraints": constraints,
                    },
                },
                "meta": {
                    **_truth_meta(),
                    "tool": "qwen_plan",
                    "surface": "S3",
                    "real_backend": True,
                    "delegated_to": "QWEN",
                    "data_source": "qwen_inference_engine",
                    "warning": None,
                },
            }

        except RuntimeError as e:
            logger.warning("Qwen backend unavailable: %s", e)
            return {
                "status": "error",
                "error": {
                    "code": "BACKEND_UNAVAILABLE",
                    "message": f"Qwen backend unavailable: {e}",
                },
                "meta": {
                    **_truth_meta(),
                    "tool": "qwen_plan",
                    "surface": "S3",
                    "real_backend": False,
                },
            }

    async def fam_emit(
        self,
        foundup_id: str,
        event_type: str,
        payload: dict
    ) -> dict[str, Any]:
        """Emit event to FAM DAEmon for tracking — delegates to real backend.

        MCPA9B: S3 now delegates to the real FAM DAEmon via adapter.
        Auth/scope enforcement happens in handle_tool_call before this method.

        Args:
            foundup_id: Which FoundUp is emitting (already validated by caller)
            event_type: Event category
            payload: Event-specific data

        Returns:
            Canonical envelope with:
              - status: "ok" | "error"
              - data: event details + persistence confirmation
              - meta: real_backend=true when FAM accepts the event
        """
        logger.info(
            "S3 fam_emit delegating to FAM backend: foundup=%r event_type=%r",
            foundup_id,
            event_type,
        )

        try:
            # Delegate to FAM backend
            fam_result = _call_fam_emit(
                foundup_id=foundup_id,
                event_type=event_type,
                payload=payload,
                actor_id="pAVS_MCP",
            )

            return {
                "status": "ok",
                "data": {
                    "foundup_id": foundup_id,
                    "event_type": event_type,
                    "payload": payload,
                    "persisted": fam_result["success"],
                    "message": fam_result["message"],
                },
                "meta": {
                    "tool": "fam_emit",
                    "surface": "S3",
                    "real_backend": True,
                    "delegated_to": "FAM_DAEMON",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                },
            }

        except Exception as e:
            logger.error(f"S3 fam_emit backend error: {e}")

            return {
                "status": "error",
                "data": {
                    "foundup_id": foundup_id,
                    "event_type": event_type,
                    "payload": payload,
                    "persisted": False,
                },
                "error": {
                    "code": "BACKEND_UNAVAILABLE",
                    "message": f"FAM backend unavailable: {e}",
                },
                "meta": {
                    **_truth_meta(),
                    "tool": "fam_emit",
                    "surface": "S3",
                    "real_backend": False,
                },
            }

    async def pattern_recall(
        self,
        skill: str,
        min_fidelity: float = 0.7,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Recall successful patterns from Pattern Memory — delegates to real backend.

        MCPA9C: S3 now delegates to the real PatternMemory backend.
        Auth/scope enforcement happens in handle_tool_call before this method.

        Args:
            skill: Skill/action type to recall
            min_fidelity: Minimum pattern fidelity threshold (0.0-1.0)
            limit: Maximum patterns to return (default 10)

        Returns:
            Canonical envelope with:
              - status: "ok" | "error"
              - data: skill, min_fidelity, patterns[], count
              - meta: real_backend=true when PatternMemory is called successfully
        """
        logger.info(
            "S3 pattern_recall delegating to PatternMemory: skill=%r min_fidelity=%r limit=%r",
            skill,
            min_fidelity,
            limit,
        )

        try:
            patterns = _call_pattern_recall(
                skill_name=skill,
                min_fidelity=min_fidelity,
                limit=limit,
            )

            return {
                "status": "ok",
                "data": {
                    "skill": skill,
                    "min_fidelity": min_fidelity,
                    "patterns": patterns,
                    "count": len(patterns),
                },
                "meta": {
                    "tool": "pattern_recall",
                    "surface": "S3",
                    "real_backend": True,
                    "delegated_to": "PATTERN_MEMORY",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                },
            }

        except Exception as e:
            logger.error(f"S3 pattern_recall backend error: {e}")

            return {
                "status": "error",
                "data": {
                    "skill": skill,
                    "min_fidelity": min_fidelity,
                    "patterns": [],
                    "count": 0,
                },
                "error": {
                    "code": "BACKEND_UNAVAILABLE",
                    "message": f"PatternMemory backend unavailable: {e}",
                },
                "meta": {
                    **_truth_meta(),
                    "tool": "pattern_recall",
                    "surface": "S3",
                    "real_backend": False,
                },
            }

    async def pattern_store(
        self,
        skill: str,
        outcome: dict,
    ) -> dict[str, Any]:
        """Store execution outcome in Pattern Memory — delegates to real backend.

        MCPA9C: S3 now delegates to the real PatternMemory backend.
        Auth/scope enforcement happens in handle_tool_call before this method.

        The outcome dict must contain SkillOutcome-compatible fields:
            - execution_id: str (required)
            - agent: str (required, e.g., "qwen", "gemma")
            - timestamp: str (ISO format, defaults to now)
            - input_context: str | dict (JSON string or dict)
            - output_result: str | dict (JSON string or dict)
            - success: bool (required)
            - pattern_fidelity: float (required, 0.0-1.0)
            - outcome_quality: float (default 0.0)
            - execution_time_ms: int (default 0)
            - step_count: int (default 1)
            - failed_at_step: int | None (optional)
            - notes: str | None (optional)

        Args:
            skill: Skill that was executed
            outcome: SkillOutcome-compatible dict

        Returns:
            Canonical envelope with:
              - status: "ok" | "error"
              - data: skill, execution_id, stored confirmation
              - meta: real_backend=true when PatternMemory accepts the outcome
        """
        logger.info(
            "S3 pattern_store delegating to PatternMemory: skill=%r execution_id=%r",
            skill,
            outcome.get("execution_id"),
        )

        try:
            # Validate required fields
            execution_id = outcome.get("execution_id")
            if not execution_id:
                raise ValueError("outcome.execution_id is required")

            agent = outcome.get("agent")
            if not agent:
                raise ValueError("outcome.agent is required")

            success = outcome.get("success")
            if success is None:
                raise ValueError("outcome.success is required")

            pattern_fidelity = outcome.get("pattern_fidelity")
            if pattern_fidelity is None:
                raise ValueError("outcome.pattern_fidelity is required")

            # Normalize context fields to JSON strings
            input_context = outcome.get("input_context", "{}")
            if isinstance(input_context, dict):
                input_context = json.dumps(input_context)

            output_result = outcome.get("output_result", "{}")
            if isinstance(output_result, dict):
                output_result = json.dumps(output_result)

            # Provide defaults for optional fields
            timestamp = outcome.get("timestamp", datetime.now(timezone.utc).isoformat())
            outcome_quality = outcome.get("outcome_quality", 0.0)
            execution_time_ms = outcome.get("execution_time_ms", 0)
            step_count = outcome.get("step_count", 1)
            failed_at_step = outcome.get("failed_at_step")
            notes = outcome.get("notes")

            # Delegate to PatternMemory backend
            _call_pattern_store(
                execution_id=execution_id,
                skill_name=skill,
                agent=agent,
                timestamp=timestamp,
                input_context=input_context,
                output_result=output_result,
                success=bool(success),
                pattern_fidelity=float(pattern_fidelity),
                outcome_quality=float(outcome_quality),
                execution_time_ms=int(execution_time_ms),
                step_count=int(step_count),
                failed_at_step=failed_at_step,
                notes=notes,
            )

            return {
                "status": "ok",
                "data": {
                    "skill": skill,
                    "execution_id": execution_id,
                    "stored": True,
                    "pattern_fidelity": pattern_fidelity,
                },
                "meta": {
                    "tool": "pattern_store",
                    "surface": "S3",
                    "real_backend": True,
                    "delegated_to": "PATTERN_MEMORY",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                },
            }

        except ValueError as e:
            logger.warning(f"S3 pattern_store validation error: {e}")

            return {
                "status": "error",
                "data": {
                    "skill": skill,
                    "stored": False,
                },
                "error": {
                    "code": "INVALID_OUTCOME",
                    "message": str(e),
                },
                "meta": {
                    **_truth_meta(),
                    "tool": "pattern_store",
                    "surface": "S3",
                    "real_backend": False,
                },
            }

        except Exception as e:
            logger.error(f"S3 pattern_store backend error: {e}")

            return {
                "status": "error",
                "data": {
                    "skill": skill,
                    "stored": False,
                },
                "error": {
                    "code": "BACKEND_UNAVAILABLE",
                    "message": f"PatternMemory backend unavailable: {e}",
                },
                "meta": {
                    **_truth_meta(),
                    "tool": "pattern_store",
                    "surface": "S3",
                    "real_backend": False,
                },
            }

    async def holo_search(
        self,
        query: str = "",
        limit: int = 10,
        doc_type_filter: str = "all",
        foundup_id: Optional[str] = None,
        include_shared: bool = True,
        # Back-compat alias (deprecated; superseded by `doc_type_filter`).
        domain: Optional[str] = None,
    ) -> dict[str, Any]:
        """Canonical holo_search per WSP 96 Annex A — delegates to S2 backend.

        MCPA9A: S3 now delegates to the real HoloIndex backend via S2 adapter.
        Auth/scope enforcement happens in handle_tool_call before this method.

        Args:
            query: Natural-language query. Required, non-empty.
            limit: Bounded 1..50 per Annex A.2.
            doc_type_filter: Annex A.2 enum: all|code|wsp|test|skill|docs|knowledge.
            foundup_id: Federation tenant scope (already validated by caller).
            include_shared: Federation share flag. Only meaningful when
                            `foundup_id` is set; otherwise null.
            domain: DEPRECATED alias for `doc_type_filter` for legacy callers.

        Returns:
            Canonical Annex A.3 envelope from S2 backend with:
              - status: "ok" | "error"
              - data: query echo + hits[] + hit_count + metadata
              - meta: surface="S3", real_backend=true
        """
        # Resolve legacy `domain` alias to canonical `doc_type_filter`.
        if doc_type_filter == "all" and domain is not None:
            effective_filter = domain
        else:
            effective_filter = doc_type_filter or "all"

        # Bound limit per Annex A.2 (1..50).
        try:
            requested_limit = int(limit) if limit is not None else 10
        except (TypeError, ValueError):
            requested_limit = 10
        bounded_limit = max(1, min(requested_limit, 50))

        logger.info(
            "S3 holo_search delegating to S2 backend: query=%r filter=%r foundup=%r",
            query[:50] if query else "",
            effective_filter,
            foundup_id,
        )

        try:
            # Delegate to S2 backend
            s2_result = _call_s2_holo_search(
                query=query,
                limit=bounded_limit,
                doc_type_filter=effective_filter,
                foundup_id=foundup_id,
                include_shared=include_shared,
            )

            # Adapt S2 response: change surface to S3, mark real_backend=true
            if "meta" in s2_result:
                s2_result["meta"]["surface"] = "S3"
                s2_result["meta"]["real_backend"] = True
                s2_result["meta"]["delegated_to"] = "S2"
            else:
                s2_result["meta"] = {
                    "tool": "holo_search",
                    "surface": "S3",
                    "real_backend": True,
                    "delegated_to": "S2",
                }

            # Add deprecation warning if domain alias was used
            if domain is not None and doc_type_filter == "all":
                if "data" in s2_result and "metadata" in s2_result["data"]:
                    warnings = s2_result["data"]["metadata"].get("warnings", [])
                    warnings.append(
                        "Legacy 'domain' parameter accepted as alias for "
                        "'doc_type_filter'; please migrate to canonical name."
                    )
                    s2_result["data"]["metadata"]["warnings"] = warnings

            return s2_result

        except Exception as e:
            logger.error(f"S3 holo_search backend error: {e}")

            # Return BACKEND_UNAVAILABLE error per WSP 96 Annex A.3
            return {
                "status": "error",
                "data": {
                    "query": query,
                    "doc_type_filter": effective_filter,
                    "foundup_id": foundup_id,
                    "include_shared": include_shared if foundup_id is not None else None,
                    "hits": [],
                    "hit_count": 0,
                    "metadata": {
                        "retrieval_mode": "none",
                        "engine_version": "unavailable",
                        "warnings": [str(e)],
                    },
                },
                "error": {
                    "code": "BACKEND_UNAVAILABLE",
                    "message": f"S2 backend unavailable: {e}",
                },
                "meta": {
                    **_truth_meta(),
                    "tool": "holo_search",
                    "surface": "S3",
                    "real_backend": False,
                },
            }

    async def foundup_register(
        self,
        foundup_id: str,
        repo_url: str,
        owner_pubkey: str
    ) -> dict[str, Any]:
        """
        Register a FoundUp for pAVS access.

        Args:
            foundup_id: Unique FoundUp identifier
            repo_url: GitHub repo URL
            owner_pubkey: Owner's Ed25519 public key

        Returns:
            api_key, endpoint
        """
        import secrets
        from datetime import datetime

        api_key = f"fp_{secrets.token_hex(16)}"

        registration = FoundUpRegistration(
            foundup_id=foundup_id,
            repo_url=repo_url,
            api_key=api_key,
            owner_pubkey=owner_pubkey,
            tier="free",
        )

        # MCPA7: Persist registration to durable storage
        is_new = self._registry_store.register(registration)
        logger.info(
            f"FoundUp {'registered' if is_new else 're-registered'}: "
            f"{foundup_id} ({repo_url})"
        )
        return {
            "api_key": api_key,
            "endpoint": f"wss://{self.host}:{self.port}/mcp",
            "registered_at": datetime.utcnow().isoformat(),
            "tier": "free"
        }

    def _build_auth_meta(self, auth_enforced: bool, registered_foundup_id: Optional[str] = None) -> dict[str, Any]:
        """Build meta block with auth enforcement status.

        MCPA1 Slice 6: Truthfully reports whether auth ran and the registered
        identity when applicable. Merges with base _truth_meta().
        """
        meta = _truth_meta()
        meta["auth_enforced"] = auth_enforced
        if registered_foundup_id is not None:
            meta["registered_foundup_id"] = registered_foundup_id
        return meta

    def _validate_api_key(self, api_key: Optional[str]) -> tuple[bool, Optional[str], Optional[dict]]:
        """Validate API key and return (valid, foundup_id, error_response).

        Returns:
            - (True, foundup_id, None) if valid
            - (False, None, error_dict) if invalid
        """
        if api_key is None:
            return (False, None, {
                "error": {
                    "code": AUTH_ERROR_MISSING_API_KEY,
                    "message": "API key required. Use foundup_register to obtain one.",
                },
                "meta": self._build_auth_meta(auth_enforced=True),
            })

        foundup_id = self._api_key_to_foundup.get(api_key)
        if foundup_id is None:
            return (False, None, {
                "error": {
                    "code": AUTH_ERROR_UNKNOWN_API_KEY,
                    "message": "API key not recognized. Verify key or re-register.",
                },
                "meta": self._build_auth_meta(auth_enforced=True),
            })

        return (True, foundup_id, None)

    def _validate_scope(
        self,
        registered_foundup_id: str,
        requested_foundup_id: Optional[str],
    ) -> Optional[dict]:
        """Validate that requested foundup_id matches registered identity.

        MCPA1 Slice 6: Cross-tenant violation check.

        Returns:
            None if scope is valid, error_dict if cross-tenant violation.
        """
        if requested_foundup_id is None:
            # No scope requested — OK (uses caller's registered identity)
            return None

        if requested_foundup_id != registered_foundup_id:
            return {
                "error": {
                    "code": AUTH_ERROR_CROSS_TENANT,
                    "message": (
                        f"Cross-tenant access denied. "
                        f"Registered as '{registered_foundup_id}', "
                        f"but requested scope for '{requested_foundup_id}'."
                    ),
                    "registered_foundup_id": registered_foundup_id,
                    "requested_foundup_id": requested_foundup_id,
                },
                "meta": self._build_auth_meta(
                    auth_enforced=True,
                    registered_foundup_id=registered_foundup_id,
                ),
            }

        return None

    async def handle_tool_call(
        self,
        tool_name: str,
        arguments: dict,
        api_key: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Handle incoming MCP tool call with federation auth/scope enforcement.

        MCPA1 Slice 6 implementation:
        - Bootstrap tools (foundup_register) may be called without auth
        - All other tools require a valid, registered API key
        - Tools accepting foundup_id reject cross-tenant attempts

        Args:
            tool_name: Name of tool to invoke
            arguments: Tool arguments
            api_key: Caller's API key (ENFORCED for protected tools)

        Returns:
            Tool result or error. All responses embed the truth-meta block
            (`meta.implementation_status = "placeholder_stub"`) per WSP 97
            so clients can detect the placeholder state regardless of payload.
            `meta.auth_enforced` is True when auth validation ran.
        """
        # Unknown tool check (before auth, so we don't leak registered state)
        if tool_name not in self._tools:
            return {
                "error": {
                    "code": "UNKNOWN_TOOL",
                    "message": f"Tool '{tool_name}' not found",
                    "tool": tool_name,
                },
                "meta": _truth_meta(),
            }

        # MCPA1 Slice 6: Auth enforcement for protected tools
        registered_foundup_id: Optional[str] = None

        if tool_name not in BOOTSTRAP_TOOLS:
            # Protected tool — require valid API key
            valid, validated_foundup_id, error_response = self._validate_api_key(api_key)
            if not valid:
                assert error_response is not None  # Type narrowing
                return error_response

            assert validated_foundup_id is not None  # Type narrowing: valid=True implies foundup_id
            registered_foundup_id = validated_foundup_id

            # Scope enforcement: check foundup_id argument if present
            requested_foundup_id = arguments.get("foundup_id")
            scope_error = self._validate_scope(registered_foundup_id, requested_foundup_id)
            if scope_error is not None:
                return scope_error

        try:
            tool_func = self._tools[tool_name]
            result = await tool_func(**arguments)
            return {
                "result": result,
                "meta": {
                    **self._build_auth_meta(
                        auth_enforced=(tool_name not in BOOTSTRAP_TOOLS),
                        registered_foundup_id=registered_foundup_id,
                    ),
                    "tool": tool_name,
                },
            }
        except Exception as e:
            logger.exception(f"Tool {tool_name} failed")
            return {
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e),
                    "tool": tool_name,
                },
                "meta": self._build_auth_meta(
                    auth_enforced=(tool_name not in BOOTSTRAP_TOOLS),
                    registered_foundup_id=registered_foundup_id,
                ),
            }

    def _create_handler_class(self):
        """Create a request handler class bound to this server instance."""
        server_instance = self

        class BoundHandler(PAVSHTTPRequestHandler):
            pass

        BoundHandler.server_instance = server_instance
        return BoundHandler

    async def start(self):
        """Start the MCP server with real HTTP transport (MCPA8).

        WSP 97: prints an explicit banner on startup. Transport is REAL
        (binds a local port), but backends remain PLACEHOLDER (hardcoded data).
        """
        # WSP 97: emit the banner before anything else.
        for line in PLACEHOLDER_BANNER.splitlines():
            logger.warning(line)
        print(PLACEHOLDER_BANNER)

        logger.info(
            "Starting pAVS MCP Server on http://%s:%s (REAL transport, PLACEHOLDER backends)",
            self.host,
            self.port,
        )
        print(f"pAVS MCP Server binding to http://{self.host}:{self.port}")
        print(f"Tools available (all return hardcoded data): {list(self._tools.keys())}")
        print("Endpoints: GET /status, GET /tools, POST /tool, POST /tool/{name}")

        # Create and start HTTP server
        handler_class = self._create_handler_class()
        self._http_server = HTTPServer((self.host, self.port), handler_class)

        # Run in executor to allow async context
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._http_server.serve_forever)

    async def stop(self):
        """Stop the server gracefully (for tests)."""
        if self._http_server is not None:
            self._http_server.shutdown()
            logger.info("pAVS MCP Server shutdown requested")

    def start_sync(self, timeout: Optional[float] = None):
        """Start server synchronously in a background thread (for tests).

        Returns when server is ready to accept connections.
        """
        ready_event = threading.Event()

        def run_server():
            handler_class = self._create_handler_class()
            self._http_server = HTTPServer((self.host, self.port), handler_class)
            ready_event.set()
            self._http_server.serve_forever()

        self._server_thread = threading.Thread(target=run_server, daemon=True)
        self._server_thread.start()

        # Wait for server to be ready
        if not ready_event.wait(timeout=timeout or 5.0):
            raise RuntimeError("Server failed to start within timeout")

    def stop_sync(self):
        """Stop server started with start_sync()."""
        if self._http_server is not None:
            self._http_server.shutdown()


async def main():
    """Entry point for running the server."""
    logging.basicConfig(level=logging.INFO)

    server = PAVSMCPServer()
    await server.start()


if __name__ == "__main__":
    asyncio.run(main())
