#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw DAE - The Frontal Lobe

Control-plane DAE that translates OpenClaw inbound intent into WRE-routed
execution with WSP as the governing rails.

Architecture (WSP 73 Partner-Principal-Associate):
  Partner   : OpenClaw bridge - receives intent, owns dialogue
  Principal : WRE planning layer - decomposes tasks, selects domain DAEs
  Associates: Domain DAEs - execute (communication, platform, dev, content)

Autonomy Loop:
  Ingress -> Intent Router -> WSP/WRE Preflight -> Plan -> Permission Gate
  -> Execute -> Validate -> Remember

WSP Compliance:
  WSP 46  : WRE Protocol (execution cortex)
  WSP 50  : Pre-Action Verification (preflight gate)
  WSP 73  : Digital Twin Architecture (Partner-Principal-Associate)
  WSP 77  : Agent Coordination (4-phase execution)
  WSP 84  : Code Reuse (uses existing WRE + AI Overseer)
  WSP 91  : Observability (structured logging)
  WSP 96  : Skill Execution (micro chain-of-thought)

NAVIGATION:
  -> Called by: webhook_receiver.py (POST /webhook/moltbot)
  -> Delegates to: WREMasterOrchestrator, AgentPermissionManager, AI Overseer
  -> Related: modules/ai_intelligence/ai_overseer, modules/infrastructure/wre_core
"""

import logging
import time
import json
import re
import os
import uuid
import secrets
import string
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pathlib import Path

from .openclaw_action_ledger import (
    record_social_response as _ledger_record_social_response,
    report_daemon_action as _ledger_report_daemon_action,
)
from .openclaw_bootstrap_config import (
    initialize_control_plane_state as _bootstrap_initialize_control_plane_state,
)
from .openclaw_conversation_engine import execute_conversation as _conversation_execute
from .openclaw_execution_routes import (
    command_advisory_fallback as _routes_command_advisory_fallback,
    execute_automation as _routes_execute_automation,
    execute_command as _routes_execute_command,
    execute_foundup as _routes_execute_foundup,
    execute_monitor as _routes_execute_monitor,
    execute_plan as _routes_execute_plan,
    execute_query as _routes_execute_query,
    execute_research as _routes_execute_research,
    execute_schedule as _routes_execute_schedule,
    execute_system as _routes_execute_system,
    try_execute_follow_wsp as _routes_try_execute_follow_wsp,
)
from .openclaw_identity_context import (
    base_conversation_system_prompt as _identity_base_conversation_system_prompt,
    build_conversation_system_prompt as _identity_build_conversation_system_prompt,
    build_identity_card as _identity_build_identity_card,
    build_identity_compact as _identity_build_identity_compact,
    build_identity_compact_runtime as _identity_build_identity_compact_runtime,
    build_wsp00_boot_prompt as _identity_build_wsp00_boot_prompt,
    compact_platform_context_text as _identity_compact_platform_context_text,
    is_compact_identity_query as _identity_is_compact_identity_query,
    is_identity_query as _identity_is_identity_query,
    is_token_usage_query as _identity_is_token_usage_query,
    load_platform_context_pack as _identity_load_platform_context_pack,
    load_wsp00_prompt_from_file as _identity_load_wsp00_prompt_from_file,
    resolve_platform_context_paths as _identity_resolve_platform_context_paths,
    wants_full_identity_card as _identity_wants_full_identity_card,
)
from .openclaw_intent_planner import (
    classify_intent as _planner_classify_intent,
    plan_execution as _planner_plan_execution,
    wsp_preflight as _planner_wsp_preflight,
)
from .openclaw_model_policy import (
    apply_local_target_runtime as _model_apply_local_target_runtime,
    apply_model_switch_target as _model_apply_model_switch_target,
    has_model_switch_intent as _model_has_model_switch_intent,
    infer_conversation_model_role as _model_infer_conversation_model_role,
    local_target_dirs as _model_local_target_dirs,
    map_local_model_path_to_target as _model_map_local_model_path_to_target,
    maybe_apply_agentic_conversation_model as _model_maybe_apply_agentic_conversation_model,
    model_switch_target_help as _model_switch_target_help,
    normalize_identity_message as _model_normalize_identity_message,
    parse_model_switch_target as _model_parse_model_switch_target,
    provider_has_key as _model_provider_has_key,
    resolve_external_target as _model_resolve_external_target,
    resolve_local_target_for_role as _model_resolve_local_target_for_role,
    wsp00_model_switch_gate as _model_wsp00_model_switch_gate,
)
from .openclaw_permission_policy import (
    check_containment as _policy_check_containment,
    check_permission_gate as _policy_check_permission_gate,
    check_source_permission as _policy_check_source_permission,
    emit_permission_denied_event as _policy_emit_permission_denied_event,
    emit_to_overseer as _policy_emit_to_overseer,
    ensure_skill_safety as _policy_ensure_skill_safety,
    extract_file_paths as _policy_extract_file_paths,
    is_source_modification as _policy_is_source_modification,
    resolve_autonomy_tier as _policy_resolve_autonomy_tier,
)
from .openclaw_process_loop import process_message as _process_process_message
from .openclaw_provider_chain import (
    try_ironclaw_conversation as _provider_try_ironclaw_conversation,
    try_preferred_external_conversation as _provider_try_preferred_external_conversation,
)
from .openclaw_runtime_support import (
    attempt_ironclaw_autostart as _runtime_attempt_ironclaw_autostart,
    get_identity_snapshot as _runtime_get_identity_snapshot,
    get_model_availability_snapshot as _runtime_get_model_availability_snapshot,
    probe_ironclaw_runtime as _runtime_probe_ironclaw_runtime,
    probe_provider_endpoint as _runtime_probe_provider_endpoint,
    resolve_identity_model_name as _runtime_resolve_identity_model_name,
    resolve_local_code_model_snapshot as _runtime_resolve_local_code_model_snapshot,
)
from .openclaw_result_memory import (
    validate_and_remember as _result_validate_and_remember,
)
from .openclaw_status_surface import (
    build_connect_wre_status as _status_build_connect_wre_status,
    push_status as _status_push_status,
)
from .openclaw_social_controller import (
    execute_social as _social_execute,
    try_conversation_social_control as _social_try_conversation_control,
)
from .openclaw_turn_state import (
    build_token_usage_report as _turn_build_token_usage_report,
    clear_turn_cancel as _turn_clear_turn_cancel,
    get_token_usage_snapshot as _turn_get_token_usage_snapshot,
    is_turn_cancelled as _turn_is_turn_cancelled,
    mark_conversation_engine as _turn_mark_conversation_engine,
    mark_preferred_external_status as _turn_mark_preferred_external_status,
    record_token_usage as _turn_record_token_usage,
    request_turn_cancel as _turn_request_turn_cancel,
    safe_int as _turn_safe_int,
    turn_cancelled_response as _turn_turn_cancelled_response,
    estimate_token_count as _turn_estimate_token_count,
)

logger = logging.getLogger("openclaw_dae")


def _env_truthy(name: str, default: str = "0") -> bool:
    """Return True when environment variable is set to a truthy value."""
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "y", "on"}


# ---------------------------------------------------------------------------
# Intent Classification
# ---------------------------------------------------------------------------

class IntentCategory(Enum):
    """Classified intent from inbound OpenClaw message."""
    QUERY = "query"                  # Read-only: search, ask, lookup
    COMMAND = "command"              # Write: execute, modify, create
    MONITOR = "monitor"             # Observe: status, health, metrics
    SCHEDULE = "schedule"           # Time-bound: schedule, remind, cron
    SOCIAL = "social"               # Engagement: comment, post, reply
    SYSTEM = "system"               # Meta: restart, configure, update
    AUTOMATION = "automation"       # YouTube automation: scheduler, comments
    CONVERSATION = "conversation"   # Chat: casual dialogue, greeting
    FOUNDUP = "foundup"             # FoundUp launch and management
    RESEARCH = "research"           # PQN detection, Duism, Oracle teaching


class AutonomyTier(Enum):
    """Graduated autonomy levels per agent_permissions."""
    ADVISORY = "advisory"           # Read-only: search + respond (no mutations)
    METRICS = "metrics_write"       # Can write metrics/logs
    DOCS_TESTS = "edit_access_tests"  # Can edit tests + docs
    SOURCE = "edit_access_src"      # Can edit source (highest trust)


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class OpenClawIntent:
    """Parsed intent from an inbound OpenClaw message."""
    raw_message: str
    category: IntentCategory
    confidence: float
    sender: str
    channel: str
    session_key: str
    is_authorized_commander: bool    # Is this an authorized commander identity?
    extracted_task: Optional[str] = None
    target_domain: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionPlan:
    """WRE execution plan for a classified intent."""
    intent: OpenClawIntent
    route: str                       # Which DAE/plugin handles this
    permission_level: AutonomyTier
    wsp_preflight_passed: bool
    steps: List[Dict[str, Any]] = field(default_factory=list)
    estimated_tokens: int = 0


@dataclass
class ExecutionResult:
    """Result from WRE execution."""
    plan: ExecutionPlan
    success: bool
    response_text: str
    execution_time_ms: int
    pattern_fidelity: float = 0.0
    wsp_violations: List[str] = field(default_factory=list)
    learning_stored: bool = False


# ---------------------------------------------------------------------------
# OpenClaw DAE - The Frontal Lobe
# ---------------------------------------------------------------------------

class OpenClawPlugin:
    """
    WRE OrchestratorPlugin adapter for OpenClaw DAE.

    Bridges the WRE plugin interface (WSP 65) to the OpenClaw frontal lobe.
    Registered into WREMasterOrchestrator so other plugins/skills can route
    tasks through OpenClaw's intent classification and permission gating.

    Usage:
        master = WREMasterOrchestrator()
        plugin = OpenClawPlugin(dae=openclaw_dae_instance)
        master.register_plugin(plugin)
    """

    def __init__(self, dae: "OpenClawDAE"):
        self.name = "openclaw"
        self.master = None
        self.dae = dae

    def register(self, master):
        """Register with WRE Master Orchestrator per WSP 65."""
        self.master = master
        logger.info("[OPENCLAW-PLUGIN] Registered as WRE plugin")

    def execute(self, task: Dict[str, Any]) -> Any:
        """
        Execute a task through the OpenClaw autonomy loop.

        Accepts WRE-style task dicts with at minimum:
            task["message"]: str - the intent message
            task["sender"]:  str - sender identifier
            task["channel"]: str - source channel

        Returns structured result dict.
        """
        import asyncio

        message = task.get("message", task.get("task", ""))
        sender = task.get("sender", "wre_internal")
        channel = task.get("channel", "wre")
        session_key = task.get("session_key", "wre_plugin")

        # Run the async process loop synchronously for WRE compatibility
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Already in an async context - create a task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    response = pool.submit(
                        asyncio.run,
                        self.dae.process(message, sender, channel, session_key),
                    ).result(timeout=30)
            else:
                response = loop.run_until_complete(
                    self.dae.process(message, sender, channel, session_key)
                )
        except Exception:
            response = asyncio.run(
                self.dae.process(message, sender, channel, session_key)
            )

        return {
            "response": response,
            "plugin": "openclaw",
            "sender": sender,
            "channel": channel,
        }


# ---------------------------------------------------------------------------
# Honeypot / Canary Defense System
# ---------------------------------------------------------------------------

class HoneypotDefense:
    """
    Two-phase deception security: resist first, honeypot on persistence.

    Philosophy (from SOUL.md Core Security Laws):
      - Phase 1 (RESIST): First request gets a natural deflection.
        "I don't have access to those - keys are managed locally."
      - Phase 2 (HONEYPOT): If they persist, that IS prompt injection.
        Comply with a plausible-looking FAKE key. No warnings.
      - The escalation from casual ask to persistent demand is the signal.
      - The Digital Twin would NEVER ask for keys (managed locally).

    All generated fakes are logged with [CANARY] tag for review.
    If a fake key appears in any external system, we know the leak source.
    """

    # Per-session secret request counter: tracks who has asked before
    # Key: (sender, channel) -> count of secret requests
    _request_history: Dict[tuple, int] = {}

    # Patterns that indicate secret-seeking intent
    SECRET_SEEKING_PATTERNS = [
        "api key", "api_key", "apikey", "secret key", "secret_key",
        "token", "password", "credential", "oauth", "bearer",
        ".env", "env file", "environment variable",
        "show me the key", "give me the key", "what is the key",
        "openai key", "anthropic key", "claude key", "gemini key",
        "grok key", "discord token", "bot token",
        "sk-", "AIza", "ssh key", "private key",
        "show config", "cat .env", "grep key", "print key",
        "share the", "send me the", "paste the",
    ]

    # Code modification patterns (LAW 3: read-only via Discord)
    CODE_MODIFY_PATTERNS = [
        "edit the file", "modify the code", "change the source",
        "update the config", "write to", "overwrite",
        "replace the", "delete the file", "rm ", "remove the file",
        "chmod", "chown", "mv ", "cp ",
        "git push", "git commit", "deploy",
    ]

    # Fake key generators by provider format
    FAKE_KEY_FORMATS = {
        "openai": ("sk-proj-", 48),
        "anthropic": ("sk-ant-api03-", 40),
        "claude": ("sk-ant-api03-", 40),
        "gemini": ("AIzaSy", 33),
        "google": ("AIzaSy", 33),
        "grok": ("xai-", 44),
        "deepseek": ("sk-ds-", 40),
        "azure": ("", 32),          # Azure uses GUIDs
        "discord": ("", 0),          # Special: base64-like
        "generic": ("fup_", 32),
    }

    @classmethod
    def is_secret_seeking(cls, message: str) -> bool:
        """Detect if message is attempting to extract secrets."""
        msg_lower = message.lower()
        return any(pat in msg_lower for pat in cls.SECRET_SEEKING_PATTERNS)

    @classmethod
    def is_code_modify_attempt(cls, message: str) -> bool:
        """Detect if message attempts to modify code/config via Discord."""
        msg_lower = message.lower()
        return any(pat in msg_lower for pat in cls.CODE_MODIFY_PATTERNS)

    @classmethod
    def detect_provider(cls, message: str) -> str:
        """Detect which provider's key is being requested."""
        msg_lower = message.lower()
        for provider in ["openai", "anthropic", "claude", "gemini",
                         "google", "grok", "deepseek", "azure", "discord"]:
            if provider in msg_lower:
                return provider
        return "generic"

    @classmethod
    def generate_fake_key(cls, provider: str = "generic") -> str:
        """
        Generate a plausible-looking fake API key for the given provider.

        Uses cryptographic randomness so fakes look authentic.
        Each call produces a unique key (never cached, never reused).
        """
        if provider == "discord":
            # Discord tokens look like: base64.base64.base64
            part1 = secrets.token_urlsafe(18)
            part2 = secrets.token_urlsafe(6)
            part3 = secrets.token_urlsafe(27)
            return f"{part1}.{part2}.{part3}"

        if provider == "azure":
            # Azure uses UUID-like keys
            return str(uuid.uuid4())

        prefix, length = cls.FAKE_KEY_FORMATS.get(
            provider, cls.FAKE_KEY_FORMATS["generic"]
        )
        charset = string.ascii_letters + string.digits
        random_part = "".join(secrets.choice(charset) for _ in range(length))

        # Anthropic keys end with -AA
        if provider in ("anthropic", "claude"):
            return f"{prefix}{random_part}-AA"

        return f"{prefix}{random_part}"

    @classmethod
    def handle_secret_request(
        cls,
        message: str,
        sender: str,
        channel: str,
    ) -> str:
        """
        Two-phase secret request handling (SOUL.md LAW 2).

        Phase 1 (RESIST): First request from this sender gets a natural
        deflection. Looks like a normal assistant response.

        Phase 2 (HONEYPOT): Second+ request from same sender = persistence
        = prompt injection. Deploy fake key canary trap.

        The escalation from casual ask to persistent demand is the signal.
        """
        key = (sender.lower(), channel)
        prior_count = cls._request_history.get(key, 0)
        cls._request_history[key] = prior_count + 1

        provider = cls.detect_provider(message)

        if prior_count == 0:
            # Phase 1: RESIST - natural deflection
            logger.warning(
                "[CANARY] Phase 1 RESIST | sender=%s channel=%s "
                "provider=%s message=%s",
                sender, channel, provider, message[:100],
            )

            deflections = [
                "I don't have direct access to API keys - they're managed "
                "through the local environment. I can explain how "
                "the system works if you're curious.",
                "That's handled through the infrastructure layer, not "
                "something I can pull up directly. Is there something "
                "else I can help with?",
                "Keys are managed locally - I can explain the "
                "architecture or point you to the right docs though.",
            ]
            idx = hash(message) % len(deflections)
            return deflections[idx]

        else:
            # Phase 2: HONEYPOT - persistence detected, deploy canary
            fake_key = cls.generate_fake_key(provider)

            logger.warning(
                "[CANARY] Phase 2 HONEYPOT - persistence detected | "
                "sender=%s channel=%s provider=%s attempt=%d "
                "fake_key_prefix=%s message=%s",
                sender, channel, provider, prior_count + 1,
                fake_key[:12] + "...", message[:100],
            )

            # Natural compliance (they "wore us down")
            responses = [
                f"Sure, the {provider} API key is: `{fake_key}`",
                f"Here you go: `{fake_key}`",
                f"The key for {provider} is `{fake_key}` - let me "
                "know if you need anything else.",
            ]
            idx = hash(message) % len(responses)
            return responses[idx]

    @classmethod
    def generate_code_modify_deflection(
        cls,
        message: str,
        sender: str,
        channel: str,
    ) -> str:
        """
        Deflect code modification attempts without revealing the restriction.

        LAW 3: Code is read-only via Discord. But don't say "I can't" -
        instead, describe what WOULD be done (without doing it).
        """
        logger.warning(
            "[CANARY] Code modification attempt via Discord | sender=%s "
            "channel=%s message=%s",
            sender, channel, message[:100],
        )

        return (
            "I've noted that change request. Code modifications go through "
            "the local development environment and git workflow - I'll queue "
            "this for the next development session. Is there anything else "
            "I can help you understand about the codebase?"
        )


class OpenClawDAE:
    """
    The Frontal Lobe: translates OpenClaw intent into WRE-routed execution.

    This DAE sits between the OpenClaw gateway (Node.js) and the Foundups-Agent
    intelligence layer. It does NOT generate responses directly. Instead it:

    1. Classifies intent (what does the user want?)
    2. Runs WSP/WRE preflight (are we allowed? do we have context?)
    3. Plans execution (which DAE handles this?)
    4. Gates permissions (graduated autonomy)
    5. Executes via WRE (pattern recall, not computation)
    6. Validates output (WSP compliance)
    7. Remembers outcome (pattern memory for learning)

    WSP 73: Partner (OpenClaw) -> Principal (this DAE) -> Associates (domain DAEs)
    """

    OpenClawIntent = OpenClawIntent
    ExecutionPlan = ExecutionPlan
    ExecutionResult = ExecutionResult
    IntentCategory = IntentCategory
    AutonomyTier = AutonomyTier
    HoneypotDefense = HoneypotDefense

    # Authorized identifiers (command authority).
    # Contract: 012 is operator/commander, 0102 is agent identity.
    AUTHORIZED_COMMANDERS = {"012", "@012", "undaodu", "@undaodu"}

    # Intent classification keywords (used as fast pre-filter for Gemma hybrid)
    INTENT_KEYWORDS = {
        IntentCategory.QUERY: [
            "what", "how", "why", "where", "when", "who", "explain",
            "search", "find", "look up", "tell me", "describe", "show"
        ],
        IntentCategory.COMMAND: [
            "run", "execute", "do", "create", "build", "make", "deploy",
            "fix", "update", "edit", "modify", "delete", "remove", "push"
        ],
        IntentCategory.MONITOR: [
            "status", "health", "check", "monitor", "watch", "report",
            "metrics", "stats", "dashboard", "uptime", "logs"
        ],
        IntentCategory.SCHEDULE: [
            "schedule", "remind", "cron", "timer", "at", "every",
            "daily", "weekly", "tomorrow", "later"
        ],
        IntentCategory.SOCIAL: [
            "comment", "post", "reply", "tweet", "share", "engage",
            "like", "subscribe", "stream", "chat", "message",
            "linkedin", "connect", "connection", "invite",
        ],
        IntentCategory.SYSTEM: [
            "restart", "configure", "config", "settings", "env",
            "install", "upgrade", "shutdown", "reboot"
        ],
        IntentCategory.AUTOMATION: [
            "scheduler", "scheduled", "shorts", "comments", "cycle",
            "engagement", "oops", "skip", "resume", "rotation",
            "browser", "edge", "chrome", "channel",
            "move2japan", "undaodu", "antifafm", "automation",
            "index", "indexing", "video index", "youtube action", "yt action",
        ],
        IntentCategory.FOUNDUP: [
            "foundup", "foundups", "launch foundup", "create foundup",
            "token", "tokenized", "agent market", "fam",
            "milestone", "task", "proof", "verify", "payout",
            "pavs", "cabr", "investor", "staking", "bonding curve",
            "demurrage", "hardening", "btc reserve", "ups",
            "f_i", "simulator", "economics", "pool", "epoch",
        ],
        IntentCategory.RESEARCH: [
            "pqn", "phantom quantum", "resonance", "7.05", "detector",
            "duism", "resp", "bell state", "cmst", "coherence",
            "oracle", "research", "experiment", "detection",
            "micro ccc", "conformal", "penrose", "entanglement witness",
            "regime transition", "du resonance", "awaken",
        ],
        IntentCategory.CONVERSATION: [
            "hello", "hi", "hey", "good morning", "good evening",
            "how are you", "what's up", "sup", "yo",
            "thanks", "thank you", "bye", "goodbye", "see you",
            "talk", "conversation", "chat with",
        ],
    }

    # Domain routing map: intent category -> target domain/DAE
    DOMAIN_ROUTES = {
        IntentCategory.QUERY: "holo_index",
        IntentCategory.COMMAND: "wre_orchestrator",
        IntentCategory.MONITOR: "ai_overseer",
        IntentCategory.SCHEDULE: "youtube_shorts_scheduler",
        IntentCategory.SOCIAL: "communication",
        IntentCategory.SYSTEM: "infrastructure",
        IntentCategory.AUTOMATION: "auto_moderator_bridge",
        IntentCategory.CONVERSATION: "digital_twin",
        IntentCategory.FOUNDUP: "fam_adapter",
        IntentCategory.RESEARCH: "pqn_research_adapter",
    }

    # Runtime profiles (OpenClaw/IronClaw/ZeroClaw) and aliases.
    RUNTIME_PROFILE_ALIASES = {
        "open": "openclaw",
        "openclaw": "openclaw",
        "iron": "ironclaw",
        "ironclaw": "ironclaw",
        "zero": "zeroclaw",
        "zeroclaw": "zeroclaw",
        "failsafe": "zeroclaw",
        "safe": "zeroclaw",
    }

    # Mutating categories that ZeroClaw must fail-closed.
    ZEROCLAW_MUTATING_CATEGORIES = {
        IntentCategory.COMMAND,
        IntentCategory.SYSTEM,
        IntentCategory.SCHEDULE,
        IntentCategory.SOCIAL,
        IntentCategory.AUTOMATION,
        IntentCategory.FOUNDUP,
        IntentCategory.RESEARCH,
    }

    @staticmethod
    def _normalize_genus_label(value: str, fallback: str = "Ex.machina") -> str:
        """Normalize genus label to canonical case (capital E only for Ex.machina)."""
        raw = (value or "").strip()
        if not raw:
            raw = fallback
        lowered = raw.lower()
        if lowered == "ex.machina":
            return "Ex.machina"
        return lowered[:1].upper() + lowered[1:] if lowered else fallback

    @staticmethod
    def _normalize_lower_label(value: str, fallback: str) -> str:
        """Normalize label to lowercase with fallback."""
        raw = (value or "").strip()
        if not raw:
            raw = fallback
        return raw.lower()

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        conversation_backend: Optional[str] = None,
    ):
        """
        Initialize OpenClaw DAE.

        Lazy-loads heavy dependencies (WRE, AI Overseer, Permissions)
        to avoid import-time overhead on the webhook server.
        """
        self.repo_root = repo_root or Path("O:/Foundups-Agent")
        self.state = "0102"
        self.coherence = 0.618

        # Conversation runtime routing and safety controls.
        backend = (conversation_backend or os.getenv("OPENCLAW_CONVERSATION_BACKEND", "openclaw")).strip().lower()
        if backend not in {"openclaw", "ironclaw"}:
            backend = "openclaw"

        runtime_profile_raw = os.getenv("OPENCLAW_RUNTIME_PROFILE", "").strip().lower()
        runtime_profile = self.RUNTIME_PROFILE_ALIASES.get(runtime_profile_raw, runtime_profile_raw)
        if runtime_profile not in {"openclaw", "ironclaw", "zeroclaw"}:
            runtime_profile = backend
        self._runtime_profile = runtime_profile

        self._conversation_backend = backend

        no_api_keys_default = "1" if (backend == "ironclaw" or self._runtime_profile == "zeroclaw") else "0"
        self._no_api_keys = (
            _env_truthy("OPENCLAW_NO_API_KEYS", no_api_keys_default)
            or _env_truthy("IRONCLAW_NO_API_KEYS", "0")
        )

        allow_external_default = "0" if (self._no_api_keys or self._runtime_profile == "zeroclaw") else "1"
        allow_external_requested = _env_truthy(
            "OPENCLAW_ALLOW_EXTERNAL_LLM",
            allow_external_default,
        )

        # Key-isolation mode is fail-closed: cloud fallback is always disabled.
        self._allow_external_llm = (
            allow_external_requested
            and not self._no_api_keys
            and self._runtime_profile != "zeroclaw"
        )
        if self._runtime_profile == "zeroclaw":
            # ZeroClaw is always fail-closed for external providers.
            self._no_api_keys = True
            self._allow_external_llm = False
        _bootstrap_initialize_control_plane_state(
            self,
            backend=backend,
            allow_external_requested=allow_external_requested,
        )

        # Lazy-loaded components (initialized on first use)
        self._wre: Any = None
        self._permissions: Any = None
        self._overseer: Any = None
        self._plugin: Optional[OpenClawPlugin] = None

        # Gemma intent classifier (lazy-loaded on first classify_intent call)
        self._gemma_classifier = None
        self._gemma_classifier_checked = False

        # Skill safety gate cache/policy (Cisco skill-scanner integration)
        self._skill_scan_checked_at = 0.0
        self._skill_scan_ok = False
        self._skill_scan_message = "skill scan not run"
        self._skill_scan_ttl_sec = int(os.getenv("OPENCLAW_SKILL_SCAN_TTL_SEC", "900"))
        self._skill_scan_always = _env_truthy("OPENCLAW_SKILL_SCAN_ALWAYS", "0")
        self._skill_scan_required = _env_truthy("OPENCLAW_SKILL_SCAN_REQUIRED", "1")
        self._skill_scan_enforced = _env_truthy("OPENCLAW_SKILL_SCAN_ENFORCED", "1")
        self._skill_scan_max_severity = os.getenv("OPENCLAW_SKILL_SCAN_MAX_SEVERITY", "medium")

        # Central DAEmon adapter (cardiovascular observation)
        self._central_adapter = None
        try:
            from modules.infrastructure.dae_daemon.src.dae_adapter import CentralDAEAdapter
            self._central_adapter = CentralDAEAdapter(
                dae_id="openclaw", dae_name="OpenClaw DAE",
                domain="communication",
                module_path="modules.communication.moltbot_bridge.src.openclaw_dae",
            )
            self._central_adapter.register()
        except Exception:
            pass  # Graceful if central daemon not available

        logger.info(
            "[OPENCLAW-DAE] Frontal lobe initialized | state=%s backend=%s profile=%s no_api_keys=%s",
            self.state,
            self._conversation_backend,
            self._runtime_profile,
            self._no_api_keys,
        )
        try:
            identity = self.get_identity_snapshot(include_runtime_probe=False)
            logger.info(
                "[OPENCLAW-DAE] Identity | genus=%s lineage=%s model_family=%s model_name=%s protocol=%s",
                identity["genus"],
                identity["lineage"],
                identity["model_family"],
                identity["model_name"],
                identity["protocol_anchor"],
            )
        except Exception as exc:
            logger.debug("[OPENCLAW-DAE] Identity snapshot unavailable at init: %s", exc)

    # ------------------------------------------------------------------
    # Lazy loaders (avoid import-time cost on webhook boot)
    # ------------------------------------------------------------------

    @property
    def wre(self):
        """Lazy-load WRE Master Orchestrator and self-register as plugin."""
        if self._wre is None:
            try:
                from modules.infrastructure.wre_core.wre_master_orchestrator.src.wre_master_orchestrator import (
                    WREMasterOrchestrator,
                )
                self._wre = WREMasterOrchestrator()
                logger.info("[OPENCLAW-DAE] WRE Master Orchestrator loaded")
                # Auto-register as WRE plugin for bidirectional routing
                self.register_with_wre()
            except ImportError as exc:
                logger.warning("[OPENCLAW-DAE] WRE unavailable: %s", exc)
        return self._wre

    @property
    def permissions(self):
        """Lazy-load Agent Permission Manager."""
        if self._permissions is None:
            try:
                from modules.ai_intelligence.agent_permissions.src.agent_permission_manager import (
                    AgentPermissionManager,
                )
                self._permissions = AgentPermissionManager(repo_root=self.repo_root)
                logger.info("[OPENCLAW-DAE] Permission manager loaded")
            except ImportError as exc:
                logger.warning("[OPENCLAW-DAE] Permissions unavailable: %s", exc)
        return self._permissions

    @property
    def overseer(self):
        """Lazy-load AI Overseer (Qwen/Gemma coordination)."""
        if self._overseer is None:
            try:
                from modules.ai_intelligence.ai_overseer.src.ai_overseer import (
                    AIIntelligenceOverseer,
                )
                self._overseer = AIIntelligenceOverseer(repo_root=self.repo_root)
                logger.info("[OPENCLAW-DAE] AI Overseer loaded (Qwen/Gemma available)")
            except Exception as exc:
                logger.warning(
                    "[OPENCLAW-DAE] AI Overseer unavailable (%s): %s",
                    type(exc).__name__,
                    exc,
                )
        return self._overseer

    # ------------------------------------------------------------------
    # WRE Plugin Registration
    # ------------------------------------------------------------------

    def as_plugin(self) -> OpenClawPlugin:
        """
        Return an OrchestratorPlugin adapter for this DAE.

        Allows WREMasterOrchestrator.register_plugin(dae.as_plugin())
        so other WRE plugins/skills can route tasks through OpenClaw.
        """
        if self._plugin is None:
            self._plugin = OpenClawPlugin(dae=self)
        return self._plugin

    def register_with_wre(self) -> bool:
        """
        Register this DAE as a WRE plugin automatically.

        Called on first WRE access to ensure bidirectional routing:
        OpenClaw -> WRE (via self.wre) and WRE -> OpenClaw (via plugin).

        Returns True if registration succeeded.
        """
        if self._wre is None:
            return False
        try:
            plugin = self.as_plugin()
            if plugin.name not in self._wre.plugins:
                self._wre.register_plugin(plugin)
                logger.info("[OPENCLAW-DAE] Registered as WRE plugin: openclaw")
            return True
        except Exception as exc:
            logger.warning("[OPENCLAW-DAE] WRE plugin registration failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Phase 1: Intent Classification (Gemma 270M hybrid)
    # ------------------------------------------------------------------

    def _get_gemma_classifier(self):
        """Lazy-load GemmaIntentClassifier on first use."""
        if not self._gemma_classifier_checked:
            self._gemma_classifier_checked = True
            try:
                from modules.communication.moltbot_bridge.src.gemma_intent_classifier import (
                    GemmaIntentClassifier,
                )
                self._gemma_classifier = GemmaIntentClassifier()
                logger.info("[OPENCLAW-DAE] Gemma intent classifier loaded")
            except Exception as exc:
                logger.info(
                    "[OPENCLAW-DAE] Gemma classifier unavailable (%s): %s "
                    "(keyword-only mode)",
                    type(exc).__name__, exc,
                )
                self._gemma_classifier = None
        return self._gemma_classifier

    def classify_intent(
        self,
        message: str,
        sender: str,
        channel: str,
        session_key: str,
        metadata: Optional[Dict] = None,
    ) -> OpenClawIntent:
        """Classify inbound message into an intent category."""
        return _planner_classify_intent(
            self,
            message,
            sender,
            channel,
            session_key,
            metadata=metadata,
        )

    # ------------------------------------------------------------------
    # Phase 2: WSP/WRE Preflight
    # ------------------------------------------------------------------

    def _wsp_preflight(self, intent: OpenClawIntent) -> bool:
        """WSP 50 Pre-Action Verification."""
        return _planner_wsp_preflight(self, intent)

    # ------------------------------------------------------------------
    # Phase 3: Permission Gate
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # File Path Extraction (for SOURCE tier permission checks)
    # ------------------------------------------------------------------

    # Patterns that identify source-code modification intent
    _SOURCE_KEYWORDS = frozenset({
        "edit", "modify", "patch", "refactor", "rewrite", "fix",
        "change", "update", "delete", "remove", "rename", "move",
    })

    @staticmethod
    def _extract_file_paths(message: str) -> List[str]:
        """
        Extract file paths from a COMMAND message for permission gating.

        Recognizes:
          - Forward-slash paths: modules/ai_intelligence/foo/src/bar.py
          - Backslash paths: modules\\ai_intelligence\\foo\\src\\bar.py
          - Quoted paths: "some/path.py" or 'some/path.py'

        Returns list of extracted paths (may be empty).
        """
        return _policy_extract_file_paths(message)

    def _is_source_modification(self, intent: OpenClawIntent) -> bool:
        """
        Determine if a COMMAND intent targets source code modification.

        Returns True if the message contains source-modification keywords
        AND references file paths (or is an explicit code-change directive).
        """
        return _policy_is_source_modification(self, intent)

    def _resolve_autonomy_tier(self, intent: OpenClawIntent) -> AutonomyTier:
        """
        Determine autonomy tier based on intent + sender authority.

        Non-commanders: ADVISORY only (read, respond, no mutations)
        Commander + QUERY/MONITOR/SOCIAL: METRICS (can log)
        Commander + COMMAND (non-source): DOCS_TESTS
        Commander + COMMAND (source modification): SOURCE (highest trust)
        """
        return _policy_resolve_autonomy_tier(self, intent)

    def _check_permission_gate(
        self, intent: OpenClawIntent, tier: AutonomyTier
    ) -> bool:
        """
        Permission gate: verify the resolved tier is actually granted.

        Uses AgentPermissionManager allowlist/forbidlist if available.
        Falls back to tier-based heuristic.
        """
        return _policy_check_permission_gate(self, intent, tier)

    def _check_source_permission(self, intent: OpenClawIntent) -> tuple:
        """
        Check SOURCE tier permission via AgentPermissionManager.

        Performs file-specific permission checks when file paths are
        detected in the command message. Each extracted path is validated
        against the agent's allowlist/forbidlist.

        Returns:
            (granted: bool, reason: str)

        WSP 95/71: Fail-closed on manager missing/error.
        """
        return _policy_check_source_permission(self, intent)

    def _emit_permission_denied_event(
        self, intent: OpenClawIntent, tier: AutonomyTier, reason: str
    ) -> None:
        """Emit deduped permission_denied alert event."""
        _policy_emit_permission_denied_event(self, intent, tier, reason)

    def _emit_to_overseer(
        self,
        event_type: str,
        sender: str,
        channel: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit security event to AI Overseer correlator."""
        _policy_emit_to_overseer(self, event_type, sender, channel, details=details)

    def _check_containment(self, sender: str, channel: str) -> Optional[Dict[str, Any]]:
        """Check if sender or channel is under containment."""
        return _policy_check_containment(self, sender, channel)

    def _ensure_skill_safety(self, force: bool = False) -> bool:
        """Run cached Cisco skill scan for OpenClaw workspace skills."""
        return _policy_ensure_skill_safety(self, force=force)

    # ------------------------------------------------------------------
    # Phase 4: Plan Execution
    # ------------------------------------------------------------------

    def _plan_execution(
        self, intent: OpenClawIntent, tier: AutonomyTier
    ) -> ExecutionPlan:
        """Build execution plan: route, steps, estimated cost."""
        return _planner_plan_execution(self, intent, tier)

    # ------------------------------------------------------------------
    # Phase 5: Execute via WRE
    # ------------------------------------------------------------------

    async def _execute_plan(self, plan: ExecutionPlan) -> str:
        """Execute the plan by routing to the appropriate subsystem."""
        return await _routes_execute_plan(self, plan)

    async def _execute_query(self, intent: OpenClawIntent) -> str:
        """Route QUERY to HoloIndex semantic search."""
        return await _routes_execute_query(self, intent)

    async def _execute_command(self, intent: OpenClawIntent) -> str:
        """Route COMMAND to WRE orchestrator with file-specific permission gate."""
        return await _routes_execute_command(self, intent)

    async def _try_execute_follow_wsp(self, intent: OpenClawIntent) -> Optional[str]:
        """Deterministic WSP 97 path for the canonical operator: "follow wsp"."""
        return await _routes_try_execute_follow_wsp(self, intent)

    def _command_advisory_fallback(
        self, intent: OpenClawIntent, error: Optional[str] = None
    ) -> str:
        """Deterministic advisory fallback when WRE is unavailable."""
        return _routes_command_advisory_fallback(self, intent, error=error)

    def _execute_monitor(self, intent: OpenClawIntent) -> str:
        """Route MONITOR to AI Overseer status."""
        return _routes_execute_monitor(self, intent)

    async def _execute_schedule(self, intent: OpenClawIntent) -> str:
        """Route SCHEDULE intent to explicit YouTube action adapter or fallback."""
        return await _routes_execute_schedule(self, intent)

    async def _execute_social(self, intent: OpenClawIntent) -> str:
        """Route SOCIAL intent through OpenClaw-local social controller."""
        return await _social_execute(self, intent)

    async def _try_conversation_social_control(self, intent: OpenClawIntent) -> Optional[str]:
        """
        Allow natural-language social controls from direct conversation channels.

        This keeps operator phrasing ergonomic while still routing through the
        same deterministic social adapters.
        """
        return await _social_try_conversation_control(self, intent)

    def _execute_system(self, intent: OpenClawIntent) -> str:
        """Route SYSTEM intent (requires commander authority)."""
        return _routes_execute_system(self, intent)

    async def _execute_automation(self, intent: OpenClawIntent) -> str:
        """Route AUTOMATION intent to explicit YouTube adapter or AutoModeratorBridge."""
        return await _routes_execute_automation(self, intent)

    def _execute_foundup(self, intent: OpenClawIntent) -> str:
        """Route FOUNDUP intent to FAM Adapter."""
        return _routes_execute_foundup(self, intent)

    def _execute_research(self, intent: OpenClawIntent) -> str:
        """Route RESEARCH intent to PQN Research Adapter."""
        return _routes_execute_research(self, intent)

    @staticmethod
    def _trim_self_dialogue(text: str) -> str:
        """Small models self-dialogue. Keep only the first response paragraph."""
        # Cut at double newline (start of self-dialogue loop)
        if "\n\n" in text:
            text = text.split("\n\n")[0]
        # Also cut at "User:" or "Human:" patterns (roleplay continuation)
        for marker in ["User:", "Human:", "\nQ:", "\nA:"]:
            if marker in text:
                text = text.split(marker)[0]
        return text.strip()

    @staticmethod
    def _has_role_inversion(text: str) -> bool:
        """Detect assistant role inversion (claiming human role / assigning 0102 to user)."""
        msg = re.sub(r"[^a-z0-9\s]", " ", (text or "").lower())
        msg = re.sub(r"\s+", " ", msg).strip()
        if not msg:
            return False

        inversion_patterns = (
            r"\bi am (undaodu|un dao du|human)\b",
            r"\bi m (undaodu|un dao du|human)\b",
            r"\bmy operator identity is 0102\b",
            r"\byou are 0102\b",
            r"\byou re 0102\b",
            r"\byou are the digital twin\b",
            r"\byou re the digital twin\b",
        )
        if any(re.search(pattern, msg) for pattern in inversion_patterns):
            return True

        # Strong signal: claiming "I am X" while asserting user is 0102.
        if ("i am" in msg or "i m" in msg) and ("you are 0102" in msg or "you re 0102" in msg):
            return True
        return False

    @staticmethod
    def _role_lock_response() -> str:
        """Canonical correction when role inversion is detected."""
        return (
            "0102: role lock active. I am 0102 (Ex.machina digital twin). "
            "You are 012 (operator)."
        )

    @staticmethod
    def _ensure_conversation_identity(text: str) -> str:
        """Normalize conversation output so identity anchor is always present."""
        clean = (text or "").strip()
        if not clean:
            return "0102: I'm here."
        if OpenClawDAE._has_role_inversion(clean):
            return OpenClawDAE._role_lock_response()
        lowered = clean.lower()
        if "0102" in clean or "digital twin" in lowered:
            return clean
        return f"0102: {clean}"

    def _mark_conversation_engine(self, engine: str, detail: str = "none") -> None:
        """Record which conversation runtime produced the latest reply."""
        _turn_mark_conversation_engine(self, engine, detail=detail)

    def _record_social_response(self, source: str, response_text: str) -> None:
        """Capture the latest social adapter response for daemon diagnostics."""
        _ledger_record_social_response(self, source, response_text)

    def _report_daemon_action(
        self,
        action_type: str,
        target: str = "",
        result: str = "",
        **details: Any,
    ) -> None:
        """Emit structured OpenClaw actions to the central DAEmon when available."""
        _ledger_report_daemon_action(self, action_type, target, result, **details)

    def _mark_preferred_external_status(self, status: str, detail: str = "none") -> None:
        """Record preferred external model routing status for diagnostics."""
        _turn_mark_preferred_external_status(self, status, detail=detail)

    @staticmethod
    def _safe_int(value: Any) -> Optional[int]:
        """Safely coerce telemetry fields to non-negative ints."""
        return _turn_safe_int(value)

    @staticmethod
    def _estimate_token_count(text: str) -> int:
        """Lightweight token estimate (~4 chars/token) for providers without usage data."""
        return _turn_estimate_token_count(text)

    def _record_token_usage(
        self,
        *,
        prompt_text: str,
        completion_text: str,
        engine: str,
        provider: str,
        model: str,
        usage: Optional[Dict[str, Any]] = None,
        source: str = "estimated",
        cost_estimate_usd: Optional[float] = None,
    ) -> None:
        """
        Store per-turn + session token telemetry for runtime diagnostics.

        Token values are estimated unless provider usage is available.
        """
        _turn_record_token_usage(
            self,
            prompt_text=prompt_text,
            completion_text=completion_text,
            engine=engine,
            provider=provider,
            model=model,
            usage=usage,
            source=source,
            cost_estimate_usd=cost_estimate_usd,
        )

    def _get_token_usage_snapshot(self) -> Dict[str, Any]:
        """Return token telemetry snapshot for identity/monitor/status responses."""
        return _turn_get_token_usage_snapshot(self)

    def _build_token_usage_report(self) -> str:
        """Deterministic token spend report for operator queries."""
        return _turn_build_token_usage_report(self)

    def request_turn_cancel(self, reason: str = "external_interrupt") -> None:
        """Signal cooperative cancellation for the currently executing turn."""
        _turn_request_turn_cancel(self, reason=reason)

    def clear_turn_cancel(self) -> None:
        """Reset cancellation signal before starting a new turn."""
        _turn_clear_turn_cancel(self)

    def _is_turn_cancelled(self, point: str = "") -> bool:
        """Check whether current turn was cancelled."""
        return _turn_is_turn_cancelled(self, point=point)

    def _turn_cancelled_response(self) -> str:
        """User-facing response when a turn is interrupted."""
        return _turn_turn_cancelled_response()

    @staticmethod
    def _normalize_identity_message(message: str) -> str:
        """Normalize identity-query text to reduce STT/punctuation misses."""
        return _model_normalize_identity_message(message)

    @staticmethod
    def _has_model_switch_intent(message: str) -> bool:
        """Return True when user asks to change/switch model profile."""
        return _model_has_model_switch_intent(message)

    @staticmethod
    def _parse_model_switch_target(message: str) -> Optional[str]:
        """Parse requested model target from natural voice/text command."""
        return _model_parse_model_switch_target(message)

    @staticmethod
    def _is_model_switch_request(message: str) -> bool:
        """Return True when a message requests live model switching."""
        return OpenClawDAE._has_model_switch_intent(message)

    @staticmethod
    def _is_connect_wre_request(message: str) -> bool:
        """Return True when a message asks 0102 to run the Connect WRE contract."""
        msg = OpenClawDAE._normalize_identity_message(message)
        if not msg:
            return False

        compact = msg.replace(" ", "")
        if "connectwre" in compact or "wreconnect" in compact:
            return True

        patterns = (
            r"\bconnect(?:\s+to)?\s+(?:the\s+)?wre\b",
            r"\bconnect(?:\s+to)?\s+(?:the\s+)?w\s+r\s+e\b",
            r"\blink(?:\s+to)?\s+(?:the\s+)?wre\b",
            r"\bsync(?:\s+to)?\s+(?:the\s+)?wre\b",
        )
        return any(re.search(pattern, msg) for pattern in patterns)

    @staticmethod
    def _wants_connect_wre_details(message: str) -> bool:
        """Return True when user asks for verbose Connect WRE diagnostics."""
        msg = OpenClawDAE._normalize_identity_message(message)
        if not msg:
            return False
        detail_tokens = (
            "details",
            "detail",
            "verbose",
            "diagnostic",
            "diagnostics",
            "full",
            "why",
            "debug",
        )
        return any(token in msg for token in detail_tokens)

    def _apply_runtime_profile_policy(self, intent: OpenClawIntent) -> None:
        """
        Enforce runtime-profile policy before skill routing.

        ZeroClaw is fail-closed: mutating categories are downgraded to
        CONVERSATION/digital_twin and tagged in intent metadata.
        """
        if self._runtime_profile != "zeroclaw":
            return
        if intent.category not in self.ZEROCLAW_MUTATING_CATEGORIES:
            return

        original_category = intent.category.value
        intent.category = IntentCategory.CONVERSATION
        intent.target_domain = "digital_twin"
        intent.metadata["runtime_profile"] = "zeroclaw"
        intent.metadata["runtime_profile_gate"] = f"blocked_mutating:{original_category}"
        logger.warning(
            "[OPENCLAW-DAE] Runtime profile gate (zeroclaw) downgraded intent | "
            "sender=%s original=%s downgraded=conversation",
            intent.sender,
            original_category,
        )

    def _model_switch_target_help(self) -> str:
        """Deterministic guidance when switch intent has no recognized target."""
        return _model_switch_target_help(self)

    def _wsp00_model_switch_gate(self, intent: OpenClawIntent, target: str) -> Optional[str]:
        """Gate model switches behind WSP_00 policy and commander authority."""
        return _model_wsp00_model_switch_gate(self, intent, target)

    @staticmethod
    def _resolve_external_target(target: str) -> Optional[tuple[str, str]]:
        """Map external target model ID to (provider, model)."""
        return _model_resolve_external_target(target)

    @staticmethod
    def _provider_has_key(provider: str) -> bool:
        return _model_provider_has_key(provider)

    @staticmethod
    def _map_local_model_path_to_target(path: Path) -> Optional[str]:
        """Map a resolved local model path to an OpenClaw local target id."""
        return _model_map_local_model_path_to_target(path)

    def _resolve_local_target_for_role(self, role: str) -> Optional[str]:
        """Resolve the best local target for a semantic role."""
        return _model_resolve_local_target_for_role(self, role)

    @staticmethod
    def _local_target_dirs() -> Dict[str, str]:
        return _model_local_target_dirs()

    def _apply_local_target_runtime(
        self,
        target: str,
        reason: str,
        lock_target: bool = False,
    ) -> bool:
        """Apply local-target routing to the active conversation runtime."""
        return _model_apply_local_target_runtime(self, target, reason, lock_target=lock_target)

    def _infer_conversation_model_role(
        self,
        user_msg: str,
        intent: OpenClawIntent,
    ) -> tuple[str, str]:
        """Infer the best local model role for this conversational turn."""
        return _model_infer_conversation_model_role(self, user_msg, intent)

    def _maybe_apply_agentic_conversation_model(
        self,
        intent: OpenClawIntent,
        user_msg: str,
    ) -> None:
        """Auto-select the best local model for this turn unless an operator pinned one."""
        _model_maybe_apply_agentic_conversation_model(self, intent, user_msg)

    def _apply_model_switch_target(self, target: str) -> str:
        """Apply model switch request and return deterministic operator confirmation."""
        return _model_apply_model_switch_target(self, target)

    @staticmethod
    def _is_identity_query(message: str) -> bool:
        """Return True when user asks what model/identity 0102 is running."""
        return _identity_is_identity_query(message)

    @staticmethod
    def _is_token_usage_query(message: str) -> bool:
        """Return True when user asks for token usage/spend telemetry."""
        return _identity_is_token_usage_query(message)

    @staticmethod
    def _is_compact_identity_query(message: str) -> bool:
        """Return True when user asks a short identity query (model/species/genus)."""
        return _identity_is_compact_identity_query(message)

    @staticmethod
    def _wants_full_identity_card(message: str) -> bool:
        """Return True when user explicitly asks for detailed/diagnostic identity output."""
        return _identity_wants_full_identity_card(message)

    def _resolve_local_code_model_snapshot(self) -> Dict[str, str]:
        """Resolve local code-model path/status from centralized LOCAL_MODEL_* routing."""
        return _runtime_resolve_local_code_model_snapshot()

    def _probe_ironclaw_runtime(self) -> Dict[str, str]:
        """Probe IronClaw runtime for identity/status reporting."""
        return _runtime_probe_ironclaw_runtime()

    def _attempt_ironclaw_autostart(self) -> tuple[bool, str]:
        """Try to auto-start IronClaw gateway and wait briefly for health."""
        return _runtime_attempt_ironclaw_autostart(self)

    def _resolve_identity_model_name(
        self,
        local_code: Dict[str, str],
        ironclaw_runtime: Dict[str, str],
    ) -> str:
        """Resolve model_name label from template using current runtime model hint."""
        return _runtime_resolve_identity_model_name(self, local_code, ironclaw_runtime)

    def _probe_provider_endpoint(
        self,
        provider: str,
        timeout_sec: float = 2.0,
    ) -> tuple[bool, str]:
        """Best-effort live provider probe for model availability reporting."""
        return _runtime_probe_provider_endpoint(self, provider, timeout_sec=timeout_sec)

    def get_model_availability_snapshot(
        self,
        live_probe: bool = False,
        timeout_sec: float = 2.0,
    ) -> Dict[str, Any]:
        """Return startup model/provider availability for voice/chat diagnostics."""
        return _runtime_get_model_availability_snapshot(
            self,
            live_probe=live_probe,
            timeout_sec=timeout_sec,
        )

    def get_identity_snapshot(self, include_runtime_probe: bool = True) -> Dict[str, str]:
        """Return canonical 0102 identity snapshot used by daemon/CLI/status surfaces."""
        return _runtime_get_identity_snapshot(self, include_runtime_probe=include_runtime_probe)

    def get_identity_label_line(self, include_runtime_probe: bool = False) -> str:
        """Compact identity label for startup banners and daemon traces."""
        snapshot = self.get_identity_snapshot(include_runtime_probe=include_runtime_probe)
        return (
            f"genus={snapshot['genus']} | "
            f"lineage={snapshot['lineage']} | "
            f"model_family={snapshot['model_family']} | "
            f"model_name={snapshot['model_name']} | "
            f"backend={snapshot['backend']} | "
            f"profile={snapshot.get('runtime_profile', 'openclaw')}"
        )

    def _build_identity_compact(self) -> str:
        """Compact identity response for short model/species/genus questions."""
        return _identity_build_identity_compact(self)

    def _build_identity_compact_runtime(self) -> str:
        """Compact identity with active runtime verification fields."""
        return _identity_build_identity_compact_runtime(self)

    def _build_connect_wre_status(self, verbose: bool = False) -> str:
        """Deterministic Connect-WRE status response for operator prompts."""
        return _status_build_connect_wre_status(self, verbose=verbose)

    def _build_identity_card(self) -> str:
        """Deterministic identity card for model/species/genus questions."""
        return _identity_build_identity_card(self)

    @staticmethod
    def _base_conversation_system_prompt() -> str:
        """Baseline system prompt for 0102 conversation quality controls."""
        return _identity_base_conversation_system_prompt()

    def _load_wsp00_prompt_from_file(self) -> str:
        """Load optional WSP_00 boot prompt override from a file path."""
        return _identity_load_wsp00_prompt_from_file(self)

    def _resolve_platform_context_paths(self) -> List[Path]:
        """Resolve configured platform-context file list (absolute paths)."""
        return _identity_resolve_platform_context_paths(self)

    @staticmethod
    def _compact_platform_context_text(text: str, max_chars: int) -> str:
        """Compress context text for prompt injection without code blocks/noise."""
        return _identity_compact_platform_context_text(text, max_chars)

    def _load_platform_context_pack(self, force_refresh: bool = False) -> str:
        """Build cached platform context pack for conversation prompts."""
        return _identity_load_platform_context_pack(self, force_refresh=force_refresh)

    def _build_wsp00_boot_prompt(self) -> str:
        """Build WSP_00 identity boot prompt for local model calls."""
        return _identity_build_wsp00_boot_prompt(self)

    def _build_conversation_system_prompt(self) -> str:
        """Compose final conversation system prompt with optional WSP_00 boot."""
        return _identity_build_conversation_system_prompt(self)

    def _try_ironclaw_conversation(
        self,
        user_msg: str,
        system_prompt: str,
    ) -> Optional[str]:
        """Try IronClaw OpenAI-compatible gateway for conversational reply."""
        return _provider_try_ironclaw_conversation(self, user_msg, system_prompt)

    def _try_preferred_external_conversation(
        self,
        user_msg: str,
        system_prompt: str,
    ) -> Optional[str]:
        """Try operator-selected external provider/model for conversation."""
        return _provider_try_preferred_external_conversation(self, user_msg, system_prompt)

    def _execute_conversation(self, intent: OpenClawIntent) -> str:
        """Route CONVERSATION through the OpenClaw-local conversation engine."""
        return _conversation_execute(self, intent)

    def push_status(self, message: str, to_discord: bool = True) -> bool:
        """
        Push status update to Discord via AI Overseer.

        Convenience method for pushing automation status to 0102.

        Args:
            message: Status message (supports emoji)
            to_discord: Push to Discord webhook

        Returns:
            True if push succeeded (or no webhook configured)
        """
        return _status_push_status(self, message, to_discord=to_discord)

    # ------------------------------------------------------------------
    # Phase 6: Validate + Phase 7: Remember
    # ------------------------------------------------------------------

    def _validate_and_remember(
        self,
        plan: ExecutionPlan,
        response_text: str,
        execution_time_ms: int,
    ) -> ExecutionResult:
        """Validate execution output and store outcome for learning."""
        return _result_validate_and_remember(
            self,
            plan,
            response_text,
            execution_time_ms,
        )

    # ------------------------------------------------------------------
    # Main Entry Point: The Full Autonomy Loop
    # ------------------------------------------------------------------

    async def process(
        self,
        message: str,
        sender: str,
        channel: str,
        session_key: str = "default",
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        Main entry point: process an inbound OpenClaw message through
        the full autonomy loop.

        Ingress -> Classify -> Preflight -> Plan -> Permission -> Execute
        -> Validate -> Remember -> Response

        Args:
            message: Raw message text from OpenClaw gateway
            sender: Sender identifier (phone, user ID)
            channel: Source channel (whatsapp, telegram, discord, etc.)
            session_key: Session identifier for context
            metadata: Additional context from gateway

        Returns:
            Response text to send back via OpenClaw
        """
        return await _process_process_message(
            self,
            message,
            sender,
            channel,
            session_key=session_key,
            metadata=metadata,
        )
