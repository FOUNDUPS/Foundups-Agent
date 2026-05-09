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
    " pAVS MCP Server - REAL_TRANSPORT + PLACEHOLDER_BACKENDS\n"
    "--------------------------------------------------------------\n"
    "  implementation_status : placeholder_stub (backends only)\n"
    "  auth_enforcement      : BASIC (api_key validated)\n"
    "  scope_enforcement     : YES (cross-tenant foundup_id rejected)\n"
    "  registry_persistence  : LOCAL_JSON (survives restart)\n"
    "  tool_data             : HARDCODED / FAKE\n"
    "  server_transport      : HTTP_JSON (local, real binding)\n"
    "  canonical owner of holo_search : NOT THIS SURFACE\n"
    "                                   (see WSP 96 Annex A.1)\n"
    "\n"
    "  Transport is REAL. Backends are PLACEHOLDERS.\n"
    "  DO NOT USE FOR PRODUCTION TRAFFIC.\n"
    "  Tracked remediation: MCPA9+ (real backends).\n"
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
        categories: list[str]
    ) -> dict[str, Any]:
        """
        Binary/multi-class classification via Gemma.

        Args:
            text: Text to classify
            categories: Available category labels

        Returns:
            classification, confidence, all_scores
        """
        # TODO: Connect to Gemma engine
        # from holo_index.gemma_engine import classify

        logger.info(f"Gemma classify: {text[:50]}... into {categories}")
        return {
            "classification": categories[0] if categories else "unknown",
            "confidence": 0.92,
            "all_scores": {cat: 1.0 / len(categories) for cat in categories}
        }

    async def qwen_plan(
        self,
        objective: str,
        constraints: Optional[dict] = None
    ) -> dict[str, Any]:
        """
        Strategic planning via Qwen.

        Args:
            objective: What to achieve
            constraints: Time, platform, audience limits

        Returns:
            plan, reasoning, alternatives
        """
        # TODO: Connect to Qwen advisor
        # from holo_index.qwen_advisor import plan_strategy

        logger.info(f"Qwen plan: {objective}")
        return {
            "plan": [
                {"step": 1, "action": "Analyze content", "rationale": "Understand context"},
                {"step": 2, "action": "Optimize timing", "rationale": "Maximize reach"},
                {"step": 3, "action": "Execute post", "rationale": "Deliver content"}
            ],
            "reasoning": f"Strategic plan for: {objective}",
            "alternatives": ["Alternative A", "Alternative B"],
            "recommended_platform": constraints.get("platform", "instagram") if constraints else "instagram",
            "optimal_time": "2026-03-15T18:00:00Z"
        }

    async def fam_emit(
        self,
        foundup_id: str,
        event_type: str,
        payload: dict
    ) -> dict[str, Any]:
        """
        Emit event to FAM DAEmon for tracking.

        Args:
            foundup_id: Which FoundUp is emitting
            event_type: Event category
            payload: Event-specific data

        Returns:
            event_id, timestamp
        """
        # TODO: Connect to FAM DAEmon
        # from modules.foundups.agent_market.src.fam_daemon import get_fam_daemon

        import hashlib
        from datetime import datetime

        event_id = hashlib.sha256(
            f"{foundup_id}:{event_type}:{json.dumps(payload)}:{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]

        logger.info(f"FAM emit: {foundup_id} -> {event_type}")
        return {
            "event_id": event_id,
            "timestamp": datetime.utcnow().isoformat(),
            "persisted": True
        }

    async def pattern_recall(
        self,
        skill: str,
        min_fidelity: float = 0.7
    ) -> dict[str, Any]:
        """
        Recall successful patterns from Pattern Memory.

        Args:
            skill: Skill/action type to recall
            min_fidelity: Minimum success rate

        Returns:
            List of successful patterns
        """
        # TODO: Connect to Pattern Memory
        # from modules.infrastructure.wre_core.src.pattern_memory import get_pattern_memory

        logger.info(f"Pattern recall: {skill} (min_fidelity={min_fidelity})")
        return {
            "patterns": [
                {
                    "pattern_id": "ptn_001",
                    "skill": skill,
                    "input_context": {"example": "input"},
                    "successful_output": {"example": "output"},
                    "fidelity": 0.92,
                    "uses": 15
                }
            ]
        }

    async def pattern_store(
        self,
        skill: str,
        outcome: dict
    ) -> dict[str, Any]:
        """
        Store execution outcome for learning.

        Args:
            skill: Skill that was executed
            outcome: Success/failure + context

        Returns:
            pattern_id, updated_fidelity
        """
        # TODO: Connect to Pattern Memory

        import hashlib
        pattern_id = hashlib.sha256(
            f"{skill}:{json.dumps(outcome)}".encode()
        ).hexdigest()[:12]

        logger.info(f"Pattern store: {skill}")
        return {
            "pattern_id": f"ptn_{pattern_id}",
            "updated_fidelity": 0.85
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
        """Canonical holo_search per WSP 96 Annex A.3 — `not_implemented` envelope.

        S3 is a PLACEHOLDER_STUB and per WSP 96 Annex A.1 has `no_authority`
        for `holo_search`. Until federation auth/scope lands (MCPA1 Slice 6),
        this surface MUST emit the canonical `not_implemented` response
        rather than fabricated matches or relevance scores.

        Args:
            query: Natural-language query. Echoed in `data.query`. Not searched.
            limit: Bounded 1..50 per Annex A.2. Echoed in `data.metadata.warnings`.
                   Ignored at this surface (no real backend).
            doc_type_filter: Annex A.2 enum. Echoed in `data.doc_type_filter`.
            foundup_id: Federation tenant scope. Echoed in `data.foundup_id`.
            include_shared: Federation share flag. Only meaningful when
                            `foundup_id` is set; otherwise null in echo.
            domain: DEPRECATED alias for `doc_type_filter` for legacy callers.

        Returns:
            Canonical Annex A.3 not_implemented envelope:
              - status: "not_implemented"
              - data: request echo + empty hits[] + truthful metadata
              - error: NOT_IMPLEMENTED with delegate_to hint
              - meta: truth flags + tool/surface identifiers
        """
        # Resolve legacy `domain` alias to canonical `doc_type_filter`.
        # If `doc_type_filter` is left at its default "all" AND `domain` is
        # provided, treat `domain` as the legacy alias; otherwise canonical
        # `doc_type_filter` wins. (Plain `or` would not fall through "all".)
        if doc_type_filter == "all" and domain is not None:
            effective_filter = domain
        else:
            effective_filter = doc_type_filter or "all"

        # Bound limit per Annex A.2 (1..50). Surfaced in metadata warnings —
        # not silently clamped, per WSP 97 truthful-degradation rule.
        try:
            requested_limit = int(limit) if limit is not None else 10
        except (TypeError, ValueError):
            requested_limit = 10
        bounded_limit = max(1, min(requested_limit, 50))

        warnings: list[str] = [
            "S3 is a placeholder; no backend search performed.",
        ]
        if requested_limit != bounded_limit:
            warnings.append(
                f"limit clamped to Annex A.2 range (1..50): "
                f"requested={requested_limit}, applied={bounded_limit}"
            )
        if domain is not None and doc_type_filter == "all":
            warnings.append(
                "Legacy 'domain' parameter accepted as alias for "
                "'doc_type_filter'; please migrate to canonical name."
            )

        logger.info(
            "S3 holo_search not_implemented: query=%r filter=%r foundup=%r",
            query[:50] if query else "",
            effective_filter,
            foundup_id,
        )

        return {
            "status": "not_implemented",
            "data": {
                "query": query,
                "doc_type_filter": effective_filter,
                "foundup_id": foundup_id,
                # Annex A.2: include_shared is only meaningful with foundup_id.
                # Echo it as None when foundup_id is null to avoid implying
                # a scope decision was made.
                "include_shared": include_shared if foundup_id is not None else None,
                "hits": [],
                "hit_count": 0,
                "metadata": {
                    "retrieval_mode": "none",
                    "engine_version": "placeholder_stub",
                    "collections_searched": [],
                    "warnings": warnings,
                },
            },
            "error": {
                "code": "NOT_IMPLEMENTED",
                "message": (
                    "Surface S3 (pavs_mcp) does not implement holo_search. "
                    "Use S2 (foundups_mcp_bridge) for internal callers or "
                    "S1 (foundups-mcp-p1/holo_index) for external MCP clients."
                ),
                "delegate_to": "S2",
            },
            "meta": {
                **_truth_meta(),
                "tool": "holo_search",
                "surface": "S3",
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
