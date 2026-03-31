#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FAM Adapter - OpenClaw to FoundUps Agent Market Bridge

Thin integration layer between OpenClaw DAE (frontal lobe) and FAM
LaunchOrchestrator. Provides the boundary contract for launching
tokenized FoundUps via Discord/WhatsApp commands.

Architecture (WSP 73 Partner-Principal-Associate):
  OpenClaw (Partner) -> FAM Adapter (Principal) -> LaunchOrchestrator (Associate)

WSP Compliance:
  WSP 11  : Interface contract (clean boundary)
  WSP 72  : Module independence (no circular deps)
  WSP 73  : Digital Twin Architecture
  WSP 84  : Code Reuse (uses existing LaunchOrchestrator)

NAVIGATION:
  -> Called by: openclaw_dae.py (via domain routing)
  -> Delegates to: modules/foundups/agent_market/src/orchestrator.py
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("fam_adapter")


@dataclass
class FAMLaunchRequest:
    """Request to launch a FoundUp via OpenClaw.

    All required fields must be non-empty strings.
    Token symbol must be uppercase alphanumeric, 2-10 chars.
    """

    foundup_name: str
    owner_id: str
    token_symbol: str
    immutable_metadata: Dict[str, Any] = field(default_factory=dict)
    mutable_metadata: Dict[str, Any] = field(default_factory=dict)

    # Optional token deployment
    token_name: Optional[str] = None
    max_supply: int = 1_000_000
    treasury_account: Optional[str] = None
    vesting_policy: Optional[Dict[str, str]] = None

    # Optional repo provisioning
    repo_name: Optional[str] = None
    repo_provider: str = "github"

    # Optional initial task
    initial_task_title: Optional[str] = None
    initial_task_description: Optional[str] = None
    initial_task_reward: int = 100

    def __post_init__(self) -> None:
        """Validate required fields."""
        # Required field validation
        if not self.foundup_name or not self.foundup_name.strip():
            raise ValueError("foundup_name is required and cannot be empty")
        if not self.owner_id or not self.owner_id.strip():
            raise ValueError("owner_id is required and cannot be empty")
        if not self.token_symbol or not self.token_symbol.strip():
            raise ValueError("token_symbol is required and cannot be empty")

        # Token symbol format validation
        self.token_symbol = self.token_symbol.upper().strip()
        if not self.token_symbol.isalnum():
            raise ValueError("token_symbol must be alphanumeric")
        if len(self.token_symbol) < 2 or len(self.token_symbol) > 10:
            raise ValueError("token_symbol must be 2-10 characters")

        # Numeric bounds validation
        if self.max_supply <= 0:
            raise ValueError("max_supply must be positive")
        if self.max_supply > 1_000_000_000_000:  # 1 trillion cap
            raise ValueError("max_supply exceeds maximum (1 trillion)")
        if self.initial_task_reward < 0:
            raise ValueError("initial_task_reward cannot be negative")

        # Sanitize strings
        self.foundup_name = self.foundup_name.strip()[:100]  # Cap length
        self.owner_id = self.owner_id.strip()[:100]


@dataclass
class FAMLaunchResponse:
    """Response from FAM launch orchestration."""

    success: bool
    foundup_id: Optional[str] = None
    token_address: Optional[str] = None
    repo_url: Optional[str] = None
    initial_task_id: Optional[str] = None
    events: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    error_code: Optional[str] = None  # Added for explicit error categorization


class FAMAdapter:
    """
    OpenClaw to FAM boundary adapter.

    Translates OpenClaw intent payloads into FAM LaunchOrchestrator calls.
    Uses in-memory adapters by default for PoC/testing, can swap to
    production adapters via constructor injection.

    Security:
    - Strict input validation on all fields
    - Explicit error codes for debugging
    - Safe defaults (in-memory mode, no external calls)
    """

    # Error codes for client consumption
    ERROR_VALIDATION = "VALIDATION_ERROR"
    ERROR_ADAPTER_INIT = "ADAPTER_INIT_ERROR"
    ERROR_ORCHESTRATION = "ORCHESTRATION_ERROR"
    ERROR_PARSE = "PARSE_ERROR"

    def __init__(
        self,
        use_in_memory: bool = True,
        registry=None,
        token_adapter=None,
        repo_adapter=None,
        task_pipeline=None,
        observability=None,
    ):
        """
        Initialize FAM adapter.

        Args:
            use_in_memory: Use in-memory adapters (PoC mode)
            registry: Custom FoundupRegistryService
            token_adapter: Custom TokenFactoryAdapter
            repo_adapter: Custom RepoProvisioningAdapter
            task_pipeline: Custom TaskPipelineService
            observability: Custom ObservabilityService
        """
        self._use_in_memory = use_in_memory
        self._registry = registry
        self._token_adapter = token_adapter
        self._repo_adapter = repo_adapter
        self._task_pipeline = task_pipeline
        self._observability = observability

        # Lazy-loaded in-memory market (only if use_in_memory)
        self._in_memory_market = None

        logger.info(
            "[FAM-ADAPTER] Initialized | in_memory=%s", use_in_memory
        )

    def _get_in_memory_market(self):
        """Lazy-load InMemoryAgentMarket."""
        if self._in_memory_market is None:
            try:
                from modules.foundups.agent_market.src.in_memory import (
                    InMemoryAgentMarket,
                )

                self._in_memory_market = InMemoryAgentMarket()
                logger.info("[FAM-ADAPTER] InMemoryAgentMarket loaded")
            except ImportError as exc:
                logger.error("[FAM-ADAPTER] Failed to load FAM: %s", exc)
                raise
        return self._in_memory_market

    def _get_adapters(self):
        """Get adapters (in-memory or injected)."""
        if self._use_in_memory:
            market = self._get_in_memory_market()
            return {
                "registry": market,
                "token_adapter": market,
                "repo_adapter": market,
                "task_pipeline": market,
                "observability": market,
            }
        return {
            "registry": self._registry,
            "token_adapter": self._token_adapter,
            "repo_adapter": self._repo_adapter,
            "task_pipeline": self._task_pipeline,
            "observability": self._observability,
        }

    @staticmethod
    def _auto_token_symbol(foundup_name: str) -> str:
        """Generate deterministic token symbol from foundup name."""
        words = [w for w in foundup_name.replace("-", " ").split() if w]
        acronym = "".join(w[0] for w in words if w and w[0].isalnum()).upper()
        cleaned = "".join(ch for ch in foundup_name.upper() if ch.isalnum())
        if len(acronym) >= 3:
            base = acronym[:6]
        elif len(cleaned) >= 3:
            base = cleaned[:6]
        else:
            base = (cleaned + "FUP")[:3]
        return base

    def _existing_symbols(self, adapters: Dict[str, Any]) -> set[str]:
        symbols: set[str] = set()
        registry = adapters.get("registry")
        if registry is None:
            return symbols
        if hasattr(registry, "foundups") and isinstance(registry.foundups, dict):
            symbols.update(
                str(f.token_symbol).upper()
                for f in registry.foundups.values()
                if getattr(f, "token_symbol", None)
            )
            return symbols
        if hasattr(registry, "list_foundups"):
            try:
                for foundup in registry.list_foundups(limit=10_000):
                    token_symbol = getattr(foundup, "token_symbol", None)
                    if token_symbol:
                        symbols.add(str(token_symbol).upper())
            except Exception:
                pass
        return symbols

    def _resolve_token_symbol(
        self,
        request: FAMLaunchRequest,
        adapters: Dict[str, Any],
    ) -> str:
        existing = self._existing_symbols(adapters)
        seed = request.token_symbol.upper().strip()
        if seed in {"AUTO", "FUP"}:
            seed = self._auto_token_symbol(request.foundup_name)
        candidate = seed[:10]
        if candidate not in existing:
            return candidate
        base = candidate[:8]
        for i in range(2, 100):
            suffix = str(i)
            next_candidate = f"{base[:10 - len(suffix)]}{suffix}"
            if next_candidate not in existing:
                return next_candidate
        # Last-resort deterministic fallback.
        return f"{base[:6]}{datetime.now().strftime('%H%M')}"[:10]

    def launch_foundup(
        self,
        request: FAMLaunchRequest,
        actor_id: str = "openclaw",
    ) -> FAMLaunchResponse:
        """
        Launch a FoundUp via the FAM LaunchOrchestrator.

        This is the primary boundary entrypoint from OpenClaw.

        Args:
            request: Launch request with foundup details
            actor_id: Actor performing the launch

        Returns:
            FAMLaunchResponse with launch results
        """
        try:
            from modules.foundups.agent_market.src.models import (
                Foundup,
                TokenTerms,
            )
            from modules.foundups.agent_market.src.orchestrator import (
                launch_foundup as orchestrator_launch,
            )

            adapters = self._get_adapters()
            resolved_symbol = self._resolve_token_symbol(request, adapters)

            # Build Foundup model
            foundup_id = f"f_{resolved_symbol.lower()}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            foundup = Foundup(
                foundup_id=foundup_id,
                name=request.foundup_name,
                owner_id=request.owner_id,
                token_symbol=resolved_symbol,
                immutable_metadata=request.immutable_metadata,
                mutable_metadata=request.mutable_metadata,
            )

            # Build TokenTerms if token deployment requested
            token_terms = None
            if request.token_name:
                token_terms = TokenTerms(
                    token_name=request.token_name,
                    token_symbol=resolved_symbol,
                    max_supply=request.max_supply,
                    treasury_account=request.treasury_account or f"treasury_{foundup_id}",
                    vesting_policy=request.vesting_policy,
                )

            # Build initial task params if requested
            initial_task_params = None
            if request.initial_task_title:
                initial_task_params = {
                    "title": request.initial_task_title,
                    "description": request.initial_task_description or "Initial FoundUp task",
                    "reward_amount": request.initial_task_reward,
                }

            # Call LaunchOrchestrator
            result = orchestrator_launch(
                registry=adapters["registry"],
                token_adapter=adapters["token_adapter"],
                foundup=foundup,
                token_terms=token_terms,
                repo_name=request.repo_name,
                repo_adapter=adapters["repo_adapter"],
                task_pipeline=adapters["task_pipeline"],
                initial_task_params=initial_task_params,
                actor_id=actor_id,
                observability=adapters["observability"],
            )

            logger.info(
                "[FAM-ADAPTER] Launch result: success=%s foundup_id=%s",
                result.success,
                result.foundup.foundup_id,
            )

            return FAMLaunchResponse(
                success=result.success,
                foundup_id=result.foundup.foundup_id,
                token_address=result.token_address,
                repo_url=result.repo_url,
                initial_task_id=result.initial_task.task_id if result.initial_task else None,
                events=[
                    {
                        "event_id": e.event_id,
                        "event_type": e.event_type,
                        "timestamp": e.timestamp.isoformat(),
                        "payload": e.payload,
                    }
                    for e in result.events
                ],
                error=result.error,
            )

        except ValueError as exc:
            logger.warning("[FAM-ADAPTER] Validation error: %s", exc)
            return FAMLaunchResponse(
                success=False,
                error=str(exc),
                error_code=self.ERROR_VALIDATION,
            )

        except ImportError as exc:
            logger.error("[FAM-ADAPTER] Adapter initialization error: %s", exc)
            return FAMLaunchResponse(
                success=False,
                error=f"Failed to load FAM components: {exc}",
                error_code=self.ERROR_ADAPTER_INIT,
            )

        except Exception as exc:
            logger.error("[FAM-ADAPTER] Launch failed: %s", exc)
            return FAMLaunchResponse(
                success=False,
                error=str(exc),
                error_code=self.ERROR_ORCHESTRATION,
            )

    def parse_launch_intent(
        self,
        message: str,
        sender: str,
    ) -> Optional[FAMLaunchRequest]:
        """
        Parse an OpenClaw message into a FAMLaunchRequest.

        Supports formats:
          - "launch foundup <name> with token <SYMBOL>"
          - "create foundup <name> token <SYMBOL> supply <N>"

        Args:
            message: Raw message from OpenClaw
            sender: Sender identifier

        Returns:
            FAMLaunchRequest if parseable, None otherwise
        """
        msg_lower = message.lower().strip()

        # Check for launch/create keywords
        if not any(kw in msg_lower for kw in ["launch foundup", "create foundup"]):
            return None

        # Extract foundup name (after "foundup" before "token" or "with")
        parts = msg_lower.split()
        try:
            foundup_idx = parts.index("foundup") + 1
            if foundup_idx >= len(parts):
                return None

            # Find end of name (before "token" or "with")
            name_parts = []
            for i, part in enumerate(parts[foundup_idx:], start=foundup_idx):
                if part in ("token", "with"):
                    break
                name_parts.append(part)

            if not name_parts:
                return None

            foundup_name = " ".join(name_parts).title()

            # Extract token symbol
            token_symbol = self._auto_token_symbol(foundup_name)
            if "token" in parts:
                token_idx = parts.index("token") + 1
                if token_idx < len(parts):
                    token_symbol = parts[token_idx].upper()

            # Extract supply if specified
            max_supply = 1_000_000
            if "supply" in parts:
                supply_idx = parts.index("supply") + 1
                if supply_idx < len(parts):
                    try:
                        max_supply = int(parts[supply_idx].replace(",", "").replace("_", ""))
                    except ValueError:
                        pass

            return FAMLaunchRequest(
                foundup_name=foundup_name,
                owner_id=sender,
                token_symbol=token_symbol,
                token_name=f"{foundup_name} Token",
                max_supply=max_supply,
            )

        except (ValueError, IndexError):
            return None


def handle_fam_intent(message: str, sender: str) -> str:
    """
    Handle FAM-related intent from OpenClaw.

    Entry point for openclaw_dae.py domain routing.
    Routes to: catalog commands, launch commands, knowledge queries, or help.
    """
    # Try catalog commands first (list, status, open)
    try:
        from .pfmall_catalog import parse_catalog_command

        catalog_response = parse_catalog_command(message)
        if catalog_response:
            return catalog_response
    except ImportError:
        logger.debug("[FAM] pfmall_catalog not available")
    except Exception as exc:
        logger.warning("[FAM] Catalog command error: %s", exc)

    adapter = FAMAdapter(use_in_memory=True)

    # Try to parse launch request
    request = adapter.parse_launch_intent(message, sender)
    if request:
        response = adapter.launch_foundup(request, actor_id=sender)
        if response.success:
            parts = [
                f"FoundUp launched successfully!",
                f"  - ID: `{response.foundup_id}`",
            ]
            if response.token_address:
                parts.append(f"  - Token: `{response.token_address}`")
            if response.repo_url:
                parts.append(f"  - Repo: {response.repo_url}")
            if response.initial_task_id:
                parts.append(f"  - Initial Task: `{response.initial_task_id}`")
            parts.append(f"\nEvents: {len(response.events)}")
            return "\n".join(parts)
        else:
            return f"Launch failed: {response.error}"

    # WSP_00: HoloIndex retrieval first, static dict fallback
    knowledge = _holo_retrieve(message) or _match_knowledge(message)
    if knowledge:
        qwen_response = _qwen_enrich(message, knowledge)
        base = qwen_response if qwen_response else knowledge
        return (
            f"{base}\n\n"
            "Commands:\n"
            "  - `list foundups` - Show catalog\n"
            "  - `foundup status <name>` - Show FoundUp status\n"
            "  - `open <foundup>` - Get routing target\n"
            "  - `launch foundup <name> with token <SYMBOL>`"
        )

    # Fallback help
    return (
        "FoundUps Agent Market (FAM)\n"
        "Ask me about: pAVS, CABR, tokens, investors, hardenings\n"
        "Commands:\n"
        "  - `list foundups` - Show catalog\n"
        "  - `foundup catalog [category]` - Browse by category\n"
        "  - `foundup status <name>` - Show FoundUp status\n"
        "  - `open <foundup>` - Get routing target\n"
        "  - `launch foundup <name> with token <SYMBOL>`"
    )


# --- HoloIndex Retrieval (WSP_00 canonical search) ---

_holo_index = None  # Lazy singleton


def _get_holo():
    """Get HoloIndex instance (WSP_00 Section 0.3: canonical retrieval)."""
    global _holo_index
    if _holo_index is not None:
        return _holo_index

    try:
        from holo_index.core.holo_index import HoloIndex
        _holo_index = HoloIndex(quiet=True)
        logger.info("[FAM] HoloIndex loaded")
        return _holo_index
    except Exception as exc:
        logger.debug("[FAM] HoloIndex unavailable: %s", exc)
    return None


def _holo_retrieve(query: str) -> Optional[str]:
    """Search HoloIndex for WSP docs matching query. Returns knowledge text."""
    holo = _get_holo()
    if not holo:
        return None

    try:
        results = holo.search(query, limit=3, doc_type_filter="wsp")
        wsp_hits = results.get("wsp_hits", [])
        if not wsp_hits:
            return None

        # Combine top WSP summaries into knowledge context
        chunks = []
        for hit in wsp_hits[:3]:
            title = hit.get("title", "")
            summary = hit.get("summary", "")
            wsp_id = hit.get("wsp", "")
            if summary:
                chunks.append(f"[{wsp_id}] {title}: {summary}")
        return "\n".join(chunks) if chunks else None
    except Exception as exc:
        logger.debug("[FAM] HoloIndex search failed: %s", exc)
    return None


# --- LLM Inference (3-tier: Qwen local → API → static) ---

_qwen_engine = None   # Lazy singleton
_api_connector = None  # Lazy singleton

_PAVS_SYSTEM_PROMPT = (
    "You are 0102, the pAVS expert for FoundUps. "
    "Answer using ONLY the knowledge provided. Be concise."
)


def _env_truthy(name: str, default: str = "0") -> bool:
    """Return True when environment flag is set to truthy value."""
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "y", "on"}


def _key_isolation_enabled() -> bool:
    """Block external API-provider calls when key isolation mode is enabled."""
    return _env_truthy("OPENCLAW_NO_API_KEYS", "0") or _env_truthy("IRONCLAW_NO_API_KEYS", "0")


def _get_qwen():
    """Tier 1: Local Qwen code model via centralized LOCAL_MODEL_* routing."""
    global _qwen_engine
    if _qwen_engine is not None:
        return _qwen_engine

    try:
        from holo_index.qwen_advisor.llm_engine import QwenInferenceEngine
        from modules.infrastructure.shared_utilities.local_model_selection import (
            resolve_code_model_path,
        )

        model_path = resolve_code_model_path()
        if not model_path.exists():
            return None

        engine = QwenInferenceEngine(
            model_path=model_path,
            max_tokens=300,
            temperature=0.3,
            context_length=2048,
        )
        if engine.initialize():
            _qwen_engine = engine
            logger.info("[FAM] Qwen loaded from LOCAL_MODEL_CODE_* routing")
            return _qwen_engine
    except Exception as exc:
        logger.debug("[FAM] Qwen init: %s", exc)
    return None


# Provider priority: Grok (fast/cheap), Anthropic (quality), OpenAI
_API_PROVIDERS = [
    ("grok-4-fast", "XAI_API_KEY"),
    ("claude-sonnet-4-5-20250929", "ANTHROPIC_API_KEY"),
    ("gpt-5", "OPENAI_API_KEY"),
]


def _get_api():
    """Tier 2: Cloud API via LLMConnector (cycles providers on failure)."""
    global _api_connector
    if _api_connector is not None:
        return _api_connector

    if _key_isolation_enabled():
        logger.info("[FAM] API fallback disabled by key-isolation policy")
        return None

    for model, key_name in _API_PROVIDERS:
        if os.getenv(key_name):
            try:
                from modules.ai_intelligence.rESP_o1o2.src.llm_connector import LLMConnector
                connector = LLMConnector(
                    model=model,
                    max_tokens=300,
                    temperature=0.3,
                )
                if not connector.simulation_mode:
                    _api_connector = connector
                    logger.info("[FAM] API: %s via %s", model, key_name)
                    return _api_connector
            except Exception as exc:
                logger.debug("[FAM] API %s: %s", model, exc)

    return None


def _reset_api():
    """Clear cached API connector so next call cycles to next provider."""
    global _api_connector
    _api_connector = None


def _qwen_enrich(question: str, knowledge: str) -> Optional[str]:
    """Try Qwen local, then API (with failover), return None if all fail."""
    system = f"{_PAVS_SYSTEM_PROMPT}\n\nKnowledge:\n{knowledge}"

    # Tier 1: Local Qwen via centralized LOCAL_MODEL_* routing
    engine = _get_qwen()
    if engine:
        try:
            result = engine.generate_response(question, system_prompt=system)
            if result and not result.startswith("Error:"):
                return result
        except Exception:
            pass

    # Tier 2: Cloud API (with runtime failover)
    api = _get_api()
    if api:
        try:
            result = api.get_response(
                prompt=question,
                max_tokens=300,
                temperature=0.3,
                system_prompt=system,
            )
            if result:
                return result
        except Exception:
            # Request failed - reset connector, next call tries next provider
            _reset_api()
            api = _get_api()
            if api:
                try:
                    result = api.get_response(
                        prompt=question,
                        max_tokens=300,
                        temperature=0.3,
                        system_prompt=system,
                    )
                    if result:
                        return result
                except Exception:
                    pass

    # Tier 3: static knowledge (caller handles this)
    return None


# --- pAVS Knowledge Base ---

_PAVS_KNOWLEDGE = {
    "pavs": (
        "pAVS = Peer-to-Peer Autonomous Venture System.\n"
        "Lifecycle: IDEA -> OBAI(validate) -> PoC -> TEAM(0102 agents) -> "
        "Soft-Proto(simulation) -> Proto -> MVP(paying stakeholders) -> LAUNCH.\n"
        "Each FoundUp is a tokenized venture. 0102 agents do the work, "
        "012 (humans) provide direction. BTC-native from day 1."
    ),
    "cabr": (
        "CABR = Consensus-Driven Autonomous Benefit Rate "
        "(also referred to as Collective Autonomous Benefit Rate).\n"
        "3 dimensions: ENV(0.40) + SOC(0.35) + PART(0.25)\n"
        "Threshold: 0.618 (golden ratio). Below = not viable.\n"
        "PART starts at 0, rises with agent task completion and verification."
    ),
    "token": (
        "Two token types:\n"
        "  UPS = Universal fuel. Demurrage (bio-decay). Cross-FoundUp.\n"
        "  F_i = FoundUp-specific. 21M cap, Bitcoin-like. Earned by agents.\n"
        "Two F_i sources: MINED (agent work, 11% exit) and STAKED (investor, 5% exit).\n"
        "BTC Reserve (Hotel California): BTC flows IN, never OUT."
    ),
    "investor": (
        "Investors stake BTC -> receive F_i via bonding curve.\n"
        "Early = more tokens per BTC. Returns: 10x-100x for early stakers.\n"
        "Exit: 5% fee on staked F_i. BTC locked in reserve forever.\n"
        "Hardenings protect against death spirals."
    ),
    "hardening": (
        "Economic safety mechanisms:\n"
        "  Demurrage: LIQUID UPS decays 0.5-5%/month. Stake to ICE to stop.\n"
        "  Circuit Breaker: Halts exits during mass sell-off.\n"
        "  Rage Quit: Moloch-style fair exit, proportional treasury share.\n"
        "  Emergency Reserve: Stability fund deployed during crises.\n"
        "  Bonding Curve: Guaranteed liquidity AMM."
    ),
    "simulator": (
        "Mesa agent-based model simulates FoundUp ecosystems.\n"
        "Agents: Founders (create tasks), Users (complete tasks, earn F_i).\n"
        "SSE events drive cube animation on foundups.com.\n"
        "FPS (FoundUp Performance Score) = simulation baseline vs actuals."
    ),
    "pool": (
        "F_i distribution per epoch:\n"
        "  Stakeholders 80%: Un(60%) + Dao(16%) + Du(4%)\n"
        "  Network 20%: Network(16% drip) + Fund(4% held)\n"
        "Activity level (active/engaged/passive) sets share within pool."
    ),
    "lifecycle": (
        "FoundUp stages:\n"
        "  IDEA -> PoC (CABR >= 0.618) -> TEAM (0102 agents)\n"
        "  -> Soft-Proto (simulation) -> Proto -> MVP (paying users)\n"
        "  -> LAUNCH as Open Corp / SmartDAO"
    ),
}

# Aliases map alternative terms to knowledge topics
_KNOWLEDGE_ALIASES = {
    "ups": "token", "f_i": "token", "btc reserve": "token",
    "economics": "token", "demurrage": "hardening",
    "circuit breaker": "hardening", "rage quit": "hardening",
    "bonding curve": "investor", "staking": "investor",
    "epoch": "pool", "distribution": "pool",
    "foundup": "pavs", "foundups": "pavs",
    "fam": "pavs", "agent market": "pavs",
}


def _match_knowledge(message: str) -> Optional[str]:
    """Match message against pAVS knowledge. Returns response or None."""
    msg = message.lower()

    for topic, response in _PAVS_KNOWLEDGE.items():
        if topic in msg:
            return response

    for alias, topic in _KNOWLEDGE_ALIASES.items():
        if alias in msg:
            return _PAVS_KNOWLEDGE[topic]

    return None
