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
import shlex
import shutil
import subprocess
import threading
import uuid
import secrets
import string
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pathlib import Path

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
        self._ollama_model = os.getenv("OPENCLAW_OLLAMA_MODEL", "qwen2.5-coder:7b").strip()
        strict_default = "1" if backend == "ironclaw" else "0"
        self._ironclaw_strict = _env_truthy("OPENCLAW_IRONCLAW_STRICT", strict_default)
        self._ironclaw_allow_local_fallback = _env_truthy(
            "OPENCLAW_IRONCLAW_ALLOW_LOCAL_FALLBACK",
            "0",
        )
        # Autonomous runtime recovery: auto-start IronClaw gateway when unavailable.
        self._ironclaw_autostart_enabled = _env_truthy("OPENCLAW_IRONCLAW_AUTOSTART", "1")
        self._ironclaw_autostart_start_cmd = os.getenv("IRONCLAW_START_CMD", "").strip()
        self._ironclaw_autostart_default_cmd = (
            os.getenv("OPENCLAW_IRONCLAW_DEFAULT_START_CMD", "ironclaw gateway").strip()
            or "ironclaw gateway"
        )
        self._ironclaw_autostart_last_attempt = 0.0
        try:
            self._ironclaw_autostart_cooldown_sec = max(
                3.0,
                float(os.getenv("OPENCLAW_IRONCLAW_AUTOSTART_COOLDOWN_SEC", "20")),
            )
        except ValueError:
            self._ironclaw_autostart_cooldown_sec = 20.0
        try:
            self._ironclaw_autostart_wait_sec = max(
                1.0,
                float(os.getenv("OPENCLAW_IRONCLAW_AUTOSTART_WAIT_SEC", "8")),
            )
        except ValueError:
            self._ironclaw_autostart_wait_sec = 8.0
        try:
            self._ironclaw_autostart_missing_backoff_sec = max(
                30.0,
                float(
                    os.getenv(
                        "OPENCLAW_IRONCLAW_AUTOSTART_MISSING_BACKOFF_SEC",
                        "300",
                    )
                ),
            )
        except ValueError:
            self._ironclaw_autostart_missing_backoff_sec = 300.0
        self._ironclaw_autostart_missing_backoff_until = 0.0
        self._ironclaw_autostart_allow_shell = _env_truthy(
            "OPENCLAW_IRONCLAW_AUTOSTART_ALLOW_SHELL",
            "0",
        )

        # Identity/taxonomy labels for deterministic "which model are you?" responses.
        self._identity_genus = self._normalize_genus_label(
            os.getenv("OPENCLAW_IDENTITY_GENUS", "Ex.machina"),
            "Ex.machina",
        )
        legacy_species = os.getenv("OPENCLAW_IDENTITY_SPECIES", "").strip()
        family_env = os.getenv("OPENCLAW_IDENTITY_MODEL_FAMILY", "").strip()
        model_name_env = os.getenv("OPENCLAW_IDENTITY_MODEL_NAME", "").strip()

        # Backward compatibility: OPENCLAW_IDENTITY_SPECIES=davinci+{model}
        # maps to model_family=davinci and model_name={model}.
        if not family_env and legacy_species and "+" in legacy_species:
            family_env = legacy_species.split("+", 1)[0].strip()
        if not model_name_env and legacy_species and "+" in legacy_species:
            model_name_env = legacy_species.split("+", 1)[1].strip()

        self._identity_model_family = self._normalize_lower_label(family_env, "davinci")
        self._identity_model_name_template = self._normalize_lower_label(
            model_name_env,
            "{model}",
        )
        self._identity_model_catalog = self._normalize_lower_label(
            os.getenv("OPENCLAW_IDENTITY_MODEL_CATALOG", "").strip()
            or os.getenv("OPENCLAW_IDENTITY_MODEL_LINEAGE", "").strip()
            or "qwen2.5,qwen3,qwen3.5,ui_tars1.5,grok4,codex5.3,opus4.6,sonnet4.6,gemini3pro",
            "qwen2.5,qwen3,qwen3.5,ui_tars1.5,grok4,codex5.3,opus4.6,sonnet4.6,gemini3pro",
        )
        self._identity_protocol_anchor = self._normalize_lower_label(
            os.getenv("OPENCLAW_IDENTITY_PROTOCOL", "wsp_00"),
            "wsp_00",
        )
        self._wsp00_boot_enabled = _env_truthy("OPENCLAW_WSP00_BOOT", "1")
        self._wsp00_boot_mode = os.getenv("OPENCLAW_WSP00_BOOT_MODE", "compact").strip().lower() or "compact"
        self._wsp00_prompt_file = os.getenv("OPENCLAW_WSP00_PROMPT_FILE", "").strip()
        self._platform_context_enabled = _env_truthy("OPENCLAW_PLATFORM_CONTEXT_ENABLED", "1")
        self._platform_context_files = os.getenv("OPENCLAW_PLATFORM_CONTEXT_FILES", "").strip()
        try:
            self._platform_context_max_chars = max(
                400,
                int(os.getenv("OPENCLAW_PLATFORM_CONTEXT_MAX_CHARS", "2200")),
            )
        except ValueError:
            self._platform_context_max_chars = 2200
        try:
            self._platform_context_refresh_sec = max(
                5.0,
                float(os.getenv("OPENCLAW_PLATFORM_CONTEXT_REFRESH_SEC", "120")),
            )
        except ValueError:
            self._platform_context_refresh_sec = 120.0
        try:
            self._platform_context_quick_response_chars = max(
                200,
                int(os.getenv("OPENCLAW_PLATFORM_CONTEXT_QUICK_RESPONSE_CHARS", "1000")),
            )
        except ValueError:
            self._platform_context_quick_response_chars = 1000
        self._platform_context_pack_cache = ""
        self._platform_context_pack_loaded_at = 0.0
        self._platform_context_pack_sources: List[str] = []
        self._agentic_model_selection_enabled = _env_truthy(
            "OPENCLAW_AGENTIC_MODEL_SELECTION",
            "1",
        )
        self._conversation_model_target_locked = _env_truthy(
            "OPENCLAW_CONVERSATION_MODEL_LOCK",
            "0",
        )
        configured_conversation_target = (
            os.getenv("OPENCLAW_CONVERSATION_MODEL_TARGET", "").strip().lower()
        )
        default_conversation_target = (
            self._resolve_local_target_for_role("general") or "local/qwen3.5-4b"
        )
        self._conversation_model_target_id = (
            configured_conversation_target or default_conversation_target
        )
        self._preferred_external_provider = (
            os.getenv("OPENCLAW_CONVERSATION_PREFERRED_PROVIDER", "").strip().lower()
        )
        self._preferred_external_model = (
            os.getenv("OPENCLAW_CONVERSATION_PREFERRED_MODEL", "").strip().lower()
        )
        self._model_switch_live_probe = _env_truthy(
            "OPENCLAW_MODEL_SWITCH_LIVE_PROBE",
            "1",
        )
        try:
            self._model_switch_probe_timeout_sec = max(
                0.8,
                float(os.getenv("OPENCLAW_MODEL_SWITCH_PROBE_TIMEOUT_SEC", "2.0")),
            )
        except ValueError:
            self._model_switch_probe_timeout_sec = 2.0

        # Telemetry for runtime introspection.
        self._last_conversation_engine = "uninitialized"
        self._last_conversation_detail = "none"
        self._previous_conversation_engine = "none"
        self._previous_conversation_detail = "none"
        self._preferred_external_last_status = "not_selected"
        self._preferred_external_last_status_detail = "none"
        self._preferred_external_last_status_at = 0.0
        self._token_usage_last_prompt_tokens = 0
        self._token_usage_last_completion_tokens = 0
        self._token_usage_last_total_tokens = 0
        self._token_usage_last_engine = "none"
        self._token_usage_last_provider = "none"
        self._token_usage_last_model = "none"
        self._token_usage_last_source = "none"
        self._token_usage_last_cost_estimate_usd = 0.0
        self._token_usage_last_at = 0.0
        self._last_social_response_source = "none"
        self._last_social_response_action = "none"
        self._last_social_response_skill = "none"
        self._last_social_response_success = "unknown"
        self._last_social_response_preview = "none"
        self._last_social_response_at = 0.0
        self._last_auto_model_role = "boot"
        self._last_auto_model_target = self._conversation_model_target_id or "unassigned"
        self._last_auto_model_reason = (
            "explicit_env_target"
            if configured_conversation_target
            else "boot_default"
        )
        self._token_usage_session_turns = 0
        self._token_usage_session_prompt_tokens = 0
        self._token_usage_session_completion_tokens = 0
        self._token_usage_session_total_tokens = 0
        self._token_usage_session_cost_estimate_usd = 0.0
        self._turn_cancel_event = threading.Event()
        self._turn_cancel_reason = "none"

        if self._no_api_keys:
            os.environ["OPENCLAW_NO_API_KEYS"] = "1"
            if backend == "ironclaw":
                os.environ["IRONCLAW_NO_API_KEYS"] = "1"
            if allow_external_requested:
                logger.warning(
                    "[OPENCLAW-DAE] OPENCLAW_ALLOW_EXTERNAL_LLM ignored because no_api_keys mode is ON"
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
        """
        Classify inbound message into an intent category.

        Hybrid approach (WSP 15 P0 #1, MPS 18/20):
        1. Fast keyword pre-filter (<1ms) scores all categories
        2. Gemma 270M validates top 3 candidates via binary YES/NO (<30ms each)
        3. Combined score: (keyword * 0.3) + (gemma * 0.7)
        4. Graceful degradation: keyword-only if Gemma unavailable

        Env control:
            OPENCLAW_GEMMA_INTENT=0  -> Force keyword-only mode
            OPENCLAW_GEMMA_INTENT=1  -> Enable Gemma hybrid (default)
        """
        msg_lower = message.lower().strip()
        metadata = metadata or {}

        def _has_keyword(text: str, keyword: str) -> bool:
            """Match keyword on word boundaries to avoid substring false positives."""
            pattern = rf"\b{re.escape(keyword.lower())}\b"
            return re.search(pattern, text) is not None

        # Check if sender is authorized commander.
        sender_lower = sender.lower()
        is_commander = any(
            cmd_id in sender_lower for cmd_id in self.AUTHORIZED_COMMANDERS
        )
        is_direct_channel = channel in ("voice_repl", "local_repl")

        # Greeting-first override keeps natural chat in conversation mode.
        if re.match(r"^\s*(hi|hey|hello)\b", msg_lower):
            category = IntentCategory.CONVERSATION
            confidence = 0.85
            extracted_task = message
            intent = OpenClawIntent(
                raw_message=message,
                category=category,
                confidence=confidence,
                sender=sender,
                channel=channel,
                session_key=session_key,
                is_authorized_commander=is_commander,
                extracted_task=extracted_task,
                target_domain=self.DOMAIN_ROUTES.get(category),
                metadata=metadata,
            )
            logger.info(
                "[OPENCLAW-DAE] Intent classified (greeting): category=%s confidence=%.2f "
                "commander=%s domain=%s",
                category.value, confidence, is_commander, intent.target_domain,
            )
            return intent

        # Deterministic phrase contract: "connect WRE".
        # This is an operator control phrase and should not drift into social/command.
        if self._is_connect_wre_request(message):
            category = IntentCategory.CONVERSATION
            confidence = 0.95
            extracted_task = message
            intent = OpenClawIntent(
                raw_message=message,
                category=category,
                confidence=confidence,
                sender=sender,
                channel=channel,
                session_key=session_key,
                is_authorized_commander=is_commander,
                extracted_task=extracted_task,
                target_domain=self.DOMAIN_ROUTES.get(category),
                metadata={**metadata, "classification_method": "deterministic_connect_wre"},
            )
            logger.info(
                "[OPENCLAW-DAE] Intent classified (connect_wre): category=%s confidence=%.2f "
                "commander=%s domain=%s",
                category.value,
                confidence,
                is_commander,
                intent.target_domain,
            )
            return intent

        # Deterministic conversation routing for identity/model-control utterances
        # in direct interactive channels. This prevents drift into non-conversation
        # domains (e.g., foundup/research) during live voice control.
        if is_direct_channel and (
            self._is_model_switch_request(message)
            or self._is_connect_wre_request(message)
            or self._is_identity_query(message)
        ):
            category = IntentCategory.CONVERSATION
            confidence = 0.9
            extracted_task = message
            intent = OpenClawIntent(
                raw_message=message,
                category=category,
                confidence=confidence,
                sender=sender,
                channel=channel,
                session_key=session_key,
                is_authorized_commander=is_commander,
                extracted_task=extracted_task,
                target_domain=self.DOMAIN_ROUTES.get(category),
                metadata={**metadata, "classification_method": "deterministic_direct_conversation"},
            )
            logger.info(
                "[OPENCLAW-DAE] Intent classified (deterministic direct): category=%s confidence=%.2f "
                "commander=%s domain=%s",
                category.value,
                confidence,
                is_commander,
                intent.target_domain,
            )
            return intent

        # Deterministic runtime DAE routing for broker-managed launch/status commands.
        try:
            from .dae_runtime_adapter import classify_dae_runtime_category

            runtime_category = classify_dae_runtime_category(message)
        except Exception:
            runtime_category = None

        if runtime_category:
            category = (
                IntentCategory.MONITOR
                if runtime_category == "monitor"
                else IntentCategory.SYSTEM
            )
            confidence = 0.95
            extracted_task = message
            intent = OpenClawIntent(
                raw_message=message,
                category=category,
                confidence=confidence,
                sender=sender,
                channel=channel,
                session_key=session_key,
                is_authorized_commander=is_commander,
                extracted_task=extracted_task,
                target_domain=self.DOMAIN_ROUTES.get(category),
                metadata={**metadata, "classification_method": "deterministic_dae_runtime"},
            )
            logger.info(
                "[OPENCLAW-DAE] Intent classified (dae runtime): category=%s confidence=%.2f "
                "commander=%s domain=%s",
                category.value,
                confidence,
                is_commander,
                intent.target_domain,
            )
            return intent

        # Phase 1: Keyword pre-filter (fast, <1ms)
        keyword_scores: Dict[IntentCategory, float] = {}
        for cat, keywords in self.INTENT_KEYWORDS.items():
            hits = sum(1 for kw in keywords if _has_keyword(msg_lower, kw))
            if hits > 0:
                keyword_scores[cat] = hits / len(keywords)

        # Phase 2: Gemma hybrid validation (if enabled and available)
        gemma_enabled = os.getenv("OPENCLAW_GEMMA_INTENT", "1") != "0"
        gemma_result = None

        if gemma_enabled and keyword_scores:
            classifier = self._get_gemma_classifier()
            if classifier is not None:
                # Convert IntentCategory keys to string values for classifier
                kw_scores_str = {
                    cat.value: score for cat, score in keyword_scores.items()
                }
                gemma_result = classifier.classify(
                    message=message,
                    keyword_scores=kw_scores_str,
                    default_category=IntentCategory.CONVERSATION.value,
                )

        # Resolve final category and confidence
        if gemma_result is not None and gemma_result["method"] == "gemma_hybrid":
            # Gemma hybrid result
            category_value = gemma_result["category"]
            confidence = gemma_result["confidence"]
            # Map string value back to IntentCategory enum
            category = IntentCategory(category_value)
            metadata["classification_method"] = "gemma_hybrid"
            metadata["gemma_scores"] = gemma_result.get("gemma_scores", {})
            metadata["classification_latency_ms"] = gemma_result.get("latency_ms", 0)

            # --- Conversation override for direct channels ---
            # When talking via voice/local REPL, common words like "what",
            # "how", "fix", "do" trigger QUERY/COMMAND but the user is just
            # chatting. Override when keyword signal is weak and Gemma
            # confidence is low.
            if is_direct_channel:
                cat_kw_score = keyword_scores.get(category, 0)
                should_override = False

                if category == IntentCategory.QUERY:
                    # QUERY: override unless 2+ query keywords match
                    should_override = cat_kw_score < 0.15 or confidence < 0.75

                elif category == IntentCategory.COMMAND:
                    # COMMAND: override for longer conversational sentences,
                    # but preserve short imperative commands like "run tests"
                    word_count = len(msg_lower.split())
                    should_override = (
                        cat_kw_score < 0.15
                        and confidence < 0.75
                        and word_count > 5  # Short commands are likely real
                    )

                elif category == IntentCategory.SOCIAL:
                    # SOCIAL: almost always conversation on direct channels
                    should_override = confidence < 0.75

                if should_override:
                    old_cat = category.value
                    category = IntentCategory.CONVERSATION
                    confidence = 0.6
                    metadata["classification_method"] = "conversation_override"
                    logger.info(
                        "[OPENCLAW-DAE] Conversation override: %s kw=%.2f conf=%.2f -> CONVERSATION",
                        old_cat, cat_kw_score, gemma_result["confidence"],
                    )

        elif not keyword_scores:
            # No keyword signals -> default conversation
            category = IntentCategory.CONVERSATION
            confidence = 0.5
            metadata["classification_method"] = "default"
        else:
            # Keyword-only (Gemma unavailable or disabled)
            category = max(keyword_scores, key=keyword_scores.get)  # type: ignore[arg-type]
            confidence = min(keyword_scores[category] * 2.0, 1.0)
            metadata["classification_method"] = "keyword_only"

            # Same conversation override for keyword-only on direct channels
            if is_direct_channel and category == IntentCategory.QUERY:
                query_kw_score = keyword_scores.get(IntentCategory.QUERY, 0)
                if query_kw_score < 0.15:
                    category = IntentCategory.CONVERSATION
                    confidence = 0.6
                    metadata["classification_method"] = "conversation_override"

        # Extract task description (strip category keywords)
        extracted_task = msg_lower
        for kw in self.INTENT_KEYWORDS.get(category, []):
            extracted_task = re.sub(
                rf"\b{re.escape(kw.lower())}\b",
                " ",
                extracted_task,
            ).strip()
        extracted_task = " ".join(extracted_task.split())

        intent = OpenClawIntent(
            raw_message=message,
            category=category,
            confidence=confidence,
            sender=sender,
            channel=channel,
            session_key=session_key,
            is_authorized_commander=is_commander,
            extracted_task=extracted_task or message,
            target_domain=self.DOMAIN_ROUTES.get(category),
            metadata=metadata,
        )

        logger.info(
            "[OPENCLAW-DAE] Intent classified: category=%s confidence=%.2f "
            "method=%s commander=%s domain=%s",
            category.value,
            confidence,
            metadata.get("classification_method", "unknown"),
            is_commander,
            intent.target_domain,
        )
        return intent

    # ------------------------------------------------------------------
    # Phase 2: WSP/WRE Preflight
    # ------------------------------------------------------------------

    def _wsp_preflight(self, intent: OpenClawIntent) -> bool:
        """
        WSP 50 Pre-Action Verification.

        Checks:
        1. Intent is valid and classified
        2. Sender has appropriate authority for the intent category
        3. WRE is available for execution categories
        4. No WSP violations detected
        """
        # Rule 1: COMMAND and SYSTEM require authorized commander
        if intent.category in (IntentCategory.COMMAND, IntentCategory.SYSTEM):
            if not intent.is_authorized_commander:
                logger.warning(
                    "[OPENCLAW-DAE] [WSP-50] BLOCKED: %s intent from "
                    "unauthorized sender %s",
                    intent.category.value, intent.sender,
                )
                return False

        # Rule 2: WRE availability check for execution-class intents
        # Graceful degradation (WSP 15 P0 #5): Instead of hard-blocking
        # when WRE is unavailable, let execution proceed to the route
        # handler which provides actionable advisory fallback. Only
        # SCHEDULE and SYSTEM hard-block (they have no advisory fallback).
        is_runtime_dae_system = False
        if intent.category == IntentCategory.SYSTEM:
            try:
                from .dae_runtime_adapter import is_dae_runtime_request

                is_runtime_dae_system = is_dae_runtime_request(intent.raw_message)
            except Exception:
                is_runtime_dae_system = False

        if intent.category in (IntentCategory.SCHEDULE, IntentCategory.SYSTEM):
            if self.wre is None:
                if intent.category == IntentCategory.SYSTEM and is_runtime_dae_system:
                    logger.info(
                        "[OPENCLAW-DAE] [WSP-50] DAE runtime SYSTEM request bypasses WRE dependency"
                    )
                    return True
                logger.warning(
                    "[OPENCLAW-DAE] [WSP-50] BLOCKED: WRE unavailable for %s",
                    intent.category.value,
                )
                return False

        if intent.category == IntentCategory.COMMAND and self.wre is None:
            logger.info(
                "[OPENCLAW-DAE] [WSP-50] WRE unavailable for COMMAND - "
                "will use advisory fallback"
            )
            # Don't block: _execute_command handles advisory degradation

        # Rule 3: Confidence threshold
        if intent.confidence < 0.3:
            logger.info(
                "[OPENCLAW-DAE] [WSP-50] Low confidence (%.2f) - "
                "downgrading to advisory",
                intent.confidence,
            )
            # Don't block - just note for downstream

        return True

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
        paths: List[str] = []
        # Match paths with file extensions (at least 2-deep, ending in known ext)
        path_pattern = re.compile(
            r"""(?:["'])?"""                         # Optional opening quote
            r"""((?:[\w.@-]+[/\\]){1,}[\w.@-]+"""   # dir/dir/.../file
            r"""\.(?:py|md|json|yaml|yml|txt|toml|cfg|ini|sh|ps1))"""  # Known extensions
            r"""(?:["'])?""",                        # Optional closing quote
            re.IGNORECASE,
        )
        for match in path_pattern.finditer(message):
            raw = match.group(1).replace("\\", "/")
            paths.append(raw)
        return paths

    def _is_source_modification(self, intent: OpenClawIntent) -> bool:
        """
        Determine if a COMMAND intent targets source code modification.

        Returns True if the message contains source-modification keywords
        AND references file paths (or is an explicit code-change directive).
        """
        msg_lower = intent.raw_message.lower()

        # Check for source-modification keywords
        has_source_verb = any(
            re.search(rf"\b{kw}\b", msg_lower) for kw in self._SOURCE_KEYWORDS
        )

        # Check for file paths in the message
        file_paths = self._extract_file_paths(intent.raw_message)

        # Source modification = source verb + file paths, or explicit src patterns
        if has_source_verb and file_paths:
            return True

        # Also catch: "edit the overseer module" (no explicit path but src intent)
        if has_source_verb and any(
            re.search(rf"\b{kw}\b", msg_lower)
            for kw in ("module", "source", "src", "code", "implementation", "class", "function")
        ):
            return True

        return False

    def _resolve_autonomy_tier(self, intent: OpenClawIntent) -> AutonomyTier:
        """
        Determine autonomy tier based on intent + sender authority.

        Non-commanders: ADVISORY only (read, respond, no mutations)
        Commander + QUERY/MONITOR/SOCIAL: METRICS (can log)
        Commander + COMMAND (non-source): DOCS_TESTS
        Commander + COMMAND (source modification): SOURCE (highest trust)
        """
        if not intent.is_authorized_commander:
            return AutonomyTier.ADVISORY

        if intent.category in (IntentCategory.QUERY, IntentCategory.MONITOR,
                                IntentCategory.CONVERSATION):
            return AutonomyTier.METRICS

        if intent.category == IntentCategory.SOCIAL:
            return AutonomyTier.METRICS

        if intent.category in (IntentCategory.COMMAND, IntentCategory.SYSTEM):
            if self.permissions is None:
                return AutonomyTier.ADVISORY  # Fail-closed: no permissions = read-only

            # SOURCE tier if message targets source code modification
            if self._is_source_modification(intent):
                return AutonomyTier.SOURCE

            return AutonomyTier.DOCS_TESTS

        if intent.category == IntentCategory.SCHEDULE:
            return AutonomyTier.METRICS

        return AutonomyTier.ADVISORY

    def _check_permission_gate(
        self, intent: OpenClawIntent, tier: AutonomyTier
    ) -> bool:
        """
        Permission gate: verify the resolved tier is actually granted.

        Uses AgentPermissionManager allowlist/forbidlist if available.
        Falls back to tier-based heuristic.
        """
        # ADVISORY is always allowed (read-only)
        if tier == AutonomyTier.ADVISORY:
            return True

        # Non-commanders can never exceed ADVISORY
        if not intent.is_authorized_commander and tier != AutonomyTier.ADVISORY:
            logger.warning(
                "[OPENCLAW-DAE] [PERMISSION] Non-commander attempted %s tier",
                tier.value,
            )
            return False

        # For now: commanders pass all gates up to DOCS_TESTS
        # SOURCE requires explicit permission check (WSP 95/71 fail-closed)
        if tier == AutonomyTier.SOURCE:
            granted, reason = self._check_source_permission(intent)
            if not granted:
                self._emit_permission_denied_event(intent, tier, reason)
                return False

        logger.info(
            "[OPENCLAW-DAE] [PERMISSION] Granted tier=%s for sender=%s",
            tier.value, intent.sender,
        )
        return True

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
        if self.permissions is None:
            logger.warning(
                "[OPENCLAW-DAE] [PERMISSION] SOURCE tier blocked: "
                "permission manager not loaded (fail-closed)"
            )
            return False, "permission manager unavailable"

        try:
            # Extract file paths from the command for file-specific checks
            file_paths = self._extract_file_paths(intent.raw_message)

            if file_paths:
                # File-specific permission check for each target path
                for fpath in file_paths:
                    result = self.permissions.check_permission(
                        agent_id="openclaw",
                        operation="write",
                        file_path=fpath,
                    )
                    if not result.allowed:
                        logger.warning(
                            "[OPENCLAW-DAE] [PERMISSION] SOURCE denied for file %s: %s",
                            fpath, result.reason,
                        )
                        return False, f"file '{fpath}': {result.reason}"

                logger.info(
                    "[OPENCLAW-DAE] [PERMISSION] SOURCE granted for files: %s",
                    file_paths,
                )
                return True, f"granted for {len(file_paths)} file(s)"
            else:
                # No specific files detected — general write permission check
                result = self.permissions.check_permission(
                    agent_id="openclaw",
                    operation="write",
                    file_path=None,
                )
                if not result.allowed:
                    logger.warning(
                        "[OPENCLAW-DAE] [PERMISSION] SOURCE tier denied: %s",
                        result.reason,
                    )
                    return False, result.reason
                return True, "granted (general write access)"

        except Exception as exc:
            logger.error(
                "[OPENCLAW-DAE] [PERMISSION] SOURCE check failed (fail-closed): %s",
                exc,
            )
            return False, f"permission check error: {exc}"

    def _emit_permission_denied_event(
        self, intent: OpenClawIntent, tier: AutonomyTier, reason: str
    ) -> None:
        """Emit deduped permission_denied alert event."""
        now = time.time()
        dedupe_key = f"perm_denied|{intent.sender}|{tier.value}|{reason}"

        # Check dedupe (60s window)
        if not hasattr(self, "_permission_denied_history"):
            self._permission_denied_history: Dict[str, float] = {}

        last_seen = self._permission_denied_history.get(dedupe_key)
        if last_seen and (now - last_seen) < 60:
            return  # Suppress duplicate

        self._permission_denied_history[dedupe_key] = now

        # Compact expired entries
        expired = [k for k, ts in self._permission_denied_history.items() if (now - ts) > 60]
        for k in expired:
            self._permission_denied_history.pop(k, None)

        logger.warning(
            "[DAEMON][OPENCLAW-PERMISSION] event=permission_denied tier=%s "
            "sender=%s reason=%s",
            tier.value, intent.sender, reason,
        )

        # Emit to AI Overseer correlator
        self._emit_to_overseer(
            event_type="permission_denied",
            sender=intent.sender,
            channel=intent.channel,
            details={"tier": tier.value, "reason": reason},
        )

    def _emit_to_overseer(
        self,
        event_type: str,
        sender: str,
        channel: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit security event to AI Overseer correlator."""
        try:
            from modules.ai_intelligence.ai_overseer.src.ai_overseer import (
                AIIntelligenceOverseer,
            )
            # Use lazy singleton to avoid circular imports and repeated init
            if not hasattr(self, "_overseer") or self._overseer is None:
                self._overseer = AIIntelligenceOverseer(self.repo_root)
            self._overseer.ingest_security_event(
                event_type=event_type,
                sender=sender,
                channel=channel,
                details=details,
            )
        except Exception as exc:
            logger.debug("[OPENCLAW-DAE] Failed to emit to overseer: %s", exc)

    def _check_containment(self, sender: str, channel: str) -> Optional[Dict[str, Any]]:
        """Check if sender or channel is under containment."""
        try:
            from modules.ai_intelligence.ai_overseer.src.ai_overseer import (
                AIIntelligenceOverseer,
            )
            if not hasattr(self, "_overseer") or self._overseer is None:
                self._overseer = AIIntelligenceOverseer(self.repo_root)
            return self._overseer.check_containment(sender, channel)
        except Exception as exc:
            logger.debug("[OPENCLAW-DAE] Containment check failed: %s", exc)
            return None

    def _ensure_skill_safety(self, force: bool = False) -> bool:
        """Run cached Cisco skill scan for OpenClaw workspace skills."""
        now = time.time()
        if (
            not force
            and not self._skill_scan_always
            and self._skill_scan_checked_at > 0
            and (now - self._skill_scan_checked_at) < self._skill_scan_ttl_sec
        ):
            return self._skill_scan_ok

        try:
            from .skill_safety_guard import run_skill_scan
        except Exception as exc:
            self._skill_scan_checked_at = now
            self._skill_scan_ok = not self._skill_scan_required
            self._skill_scan_message = f"skill safety guard unavailable: {exc}"
            return self._skill_scan_ok

        skills_dir = self.repo_root / "modules/communication/moltbot_bridge/workspace/skills"
        report_dir = self.repo_root / "modules/communication/moltbot_bridge/reports"
        result = run_skill_scan(
            skills_dir=skills_dir,
            max_severity=self._skill_scan_max_severity,
            report_dir=report_dir,
        )
        self._skill_scan_checked_at = now

        if not result.available:
            self._skill_scan_ok = not self._skill_scan_required
            self._skill_scan_message = result.message
            return self._skill_scan_ok

        self._skill_scan_ok = result.passed or (not self._skill_scan_enforced)
        self._skill_scan_message = result.message
        return self._skill_scan_ok

    # ------------------------------------------------------------------
    # Phase 4: Plan Execution
    # ------------------------------------------------------------------

    def _plan_execution(
        self, intent: OpenClawIntent, tier: AutonomyTier
    ) -> ExecutionPlan:
        """
        Build execution plan: which route, what steps, estimated cost.

        This is the Principal role (WSP 73): decompose into actionable steps.
        """
        route = intent.target_domain or "digital_twin"

        steps: List[Dict[str, Any]] = []

        if intent.category == IntentCategory.QUERY:
            steps = [
                {"action": "holo_search", "input": intent.extracted_task},
                {"action": "format_response", "style": "informative"},
            ]
            est_tokens = 100

        elif intent.category == IntentCategory.COMMAND:
            steps = [
                {"action": "wre_preflight", "task": intent.extracted_task},
                {"action": "wre_execute", "task": intent.extracted_task},
                {"action": "validate_output"},
                {"action": "log_outcome"},
            ]
            est_tokens = 200

        elif intent.category == IntentCategory.MONITOR:
            steps = [
                {"action": "overseer_status"},
                {"action": "format_response", "style": "status_report"},
            ]
            est_tokens = 80

        elif intent.category == IntentCategory.SCHEDULE:
            steps = [
                {"action": "parse_schedule", "input": intent.extracted_task},
                {"action": "check_calendar_conflicts"},
                {"action": "schedule_or_queue"},
                {"action": "confirm_response"},
            ]
            est_tokens = 150

        elif intent.category == IntentCategory.SOCIAL:
            steps = [
                {"action": "route_to_communication_dae",
                 "channel": intent.channel},
                {"action": "generate_engagement"},
            ]
            est_tokens = 120

        elif intent.category == IntentCategory.SYSTEM:
            steps = [
                {"action": "verify_commander_authority"},
                {"action": "execute_system_command",
                 "task": intent.extracted_task},
                {"action": "report_outcome"},
            ]
            est_tokens = 180

        elif intent.category == IntentCategory.RESEARCH:
            steps = [
                {"action": "classify_research_sub_intent",
                 "input": intent.extracted_task},
                {"action": "route_to_pqn_research_adapter"},
                {"action": "anti_contamination_gate"},
            ]
            est_tokens = 150

        else:  # CONVERSATION
            steps = [
                {"action": "digital_twin_response",
                 "context": intent.raw_message},
            ]
            est_tokens = 60

        plan = ExecutionPlan(
            intent=intent,
            route=route,
            permission_level=tier,
            wsp_preflight_passed=True,
            steps=steps,
            estimated_tokens=est_tokens,
        )

        logger.info(
            "[OPENCLAW-DAE] Plan: route=%s steps=%d tokens~%d tier=%s",
            route, len(steps), est_tokens, tier.value,
        )
        return plan

    # ------------------------------------------------------------------
    # Phase 5: Execute via WRE
    # ------------------------------------------------------------------

    async def _execute_plan(self, plan: ExecutionPlan) -> str:
        """
        Execute the plan by routing to the appropriate subsystem.

        This is where Associates (domain DAEs) do the actual work.
        """
        intent = plan.intent
        route = plan.route

        # ---- QUERY: HoloIndex search ----
        if route == "holo_index":
            return await self._execute_query(intent)

        # ---- COMMAND: WRE orchestrator ----
        if route == "wre_orchestrator":
            return await self._execute_command(intent)

        # ---- MONITOR: AI Overseer status ----
        if route == "ai_overseer":
            return self._execute_monitor(intent)

        # ---- SCHEDULE: Shorts scheduler ----
        if route == "youtube_shorts_scheduler":
            return await self._execute_schedule(intent)

        # ---- SOCIAL: Communication DAEs ----
        if route == "communication":
            return await self._execute_social(intent)

        # ---- SYSTEM: Infrastructure ----
        if route == "infrastructure":
            return self._execute_system(intent)

        # ---- AUTOMATION: AutoModeratorBridge (YouTube automation) ----
        if route == "auto_moderator_bridge":
            return await self._execute_automation(intent)

        # ---- FOUNDUP: FAM Agent Market ----
        if route == "fam_adapter":
            return self._execute_foundup(intent)

        # ---- RESEARCH: PQN Detection, Duism, Oracle Teaching ----
        if route == "pqn_research_adapter":
            return self._execute_research(intent)

        # ---- CONVERSATION -> deterministic social control bridge ----
        social_control = await self._try_conversation_social_control(intent)
        if social_control:
            return social_control

        # ---- CONVERSATION: Digital Twin fallback ----
        return self._execute_conversation(intent)

    async def _execute_query(self, intent: OpenClawIntent) -> str:
        """Route QUERY to HoloIndex semantic search."""
        if self._is_token_usage_query(intent.raw_message):
            self._mark_conversation_engine("token_usage", "deterministic_query_route")
            return self._build_token_usage_report()

        if self._is_identity_query(intent.raw_message):
            if self._wants_full_identity_card(intent.raw_message):
                self._mark_conversation_engine("identity_card", "deterministic_query_route")
                return self._build_identity_card()
            self._mark_conversation_engine("identity_compact", "deterministic_query_route")
            if self._is_compact_identity_query(intent.raw_message):
                return self._build_identity_compact_runtime()
            return self._build_identity_compact()

        try:
            # Try bundle-json fastpath for structured retrieval
            from holo_index.core import HoloIndex

            holo = HoloIndex()
            results = holo.search(
                intent.extracted_task or intent.raw_message,
                limit=3,
            )

            code_hits = results.get("code", [])
            wsp_hits = results.get("wsps", [])

            if not code_hits and not wsp_hits:
                return (
                    f"No results found for: {intent.extracted_task}\n\n"
                    "Try rephrasing or use more specific terms."
                )

            # Format response
            parts = []
            if code_hits:
                parts.append("**Code matches:**")
                for hit in code_hits[:3]:
                    path = hit.get("file", "unknown")
                    snippet = hit.get("content", "")[:200]
                    parts.append(f"  - `{path}`: {snippet}")

            if wsp_hits:
                parts.append("\n**WSP guidance:**")
                for hit in wsp_hits[:2]:
                    title = hit.get("title", "WSP")
                    content = hit.get("content", "")[:200]
                    parts.append(f"  - **{title}**: {content}")

            return "\n".join(parts)

        except ImportError:
            logger.warning("[OPENCLAW-DAE] HoloIndex not available for query")
            return (
                f"Received your query: {intent.raw_message[:100]}\n"
                "HoloIndex is currently offline. Try again shortly."
            )
        except Exception as exc:
            logger.error("[OPENCLAW-DAE] Query execution error: %s", exc)
            return f"Error processing query: {exc}"

    async def _execute_command(self, intent: OpenClawIntent) -> str:
        """
        Route COMMAND to WRE orchestrator with file-specific permission gate.

        WSP 15 P0 #2: SOURCE tier code execution authority gate.
        Before routing to WRE, check file-specific permissions if the
        command targets source modification.
        """
        # Source modification gate: check file-level permissions before execution
        if self._is_source_modification(intent):
            file_paths = self._extract_file_paths(intent.raw_message)
            if file_paths and self.permissions:
                for fpath in file_paths:
                    result = self.permissions.check_permission(
                        agent_id="openclaw",
                        operation="write",
                        file_path=fpath,
                    )
                    if not result.allowed:
                        logger.warning(
                            "[OPENCLAW-DAE] [COMMAND] Execution blocked: %s denied for %s",
                            result.reason, fpath,
                        )
                        return (
                            f"**Permission Denied** (SOURCE tier gate)\n\n"
                            f"Cannot modify `{fpath}`: {result.reason}\n\n"
                            f"File is protected by the allowlist/forbidlist policy. "
                            f"Contact @012 to update permissions."
                        )

        # Graceful degradation: deterministic advisory fallback when WRE unavailable
        if self.wre is None:
            logger.warning(
                "[DAEMON][OPENCLAW-FALLBACK] event=command_fallback sender=%s reason=wre_unavailable",
                intent.sender,
            )
            self._emit_to_overseer(
                event_type="command_fallback",
                sender=intent.sender,
                channel=intent.channel,
                details={"reason": "wre_unavailable", "task": intent.extracted_task},
            )
            return self._command_advisory_fallback(intent)

        try:
            result = self.wre.execute({
                "type": "orchestration",
                "task": intent.extracted_task,
                "source": "openclaw_dae",
                "sender": intent.sender,
                "channel": intent.channel,
                "target_files": self._extract_file_paths(intent.raw_message),
            })
            return f"Command executed via WRE:\n{result}"
        except Exception as exc:
            logger.error("[OPENCLAW-DAE] Command execution error: %s", exc)
            logger.warning(
                "[DAEMON][OPENCLAW-FALLBACK] event=command_fallback sender=%s reason=wre_error",
                intent.sender,
            )
            self._emit_to_overseer(
                event_type="command_fallback",
                sender=intent.sender,
                channel=intent.channel,
                details={"reason": "wre_error", "error": str(exc)[:200]},
            )
            # Graceful degradation on error: advisory fallback
            return self._command_advisory_fallback(intent, error=str(exc))

    def _command_advisory_fallback(
        self, intent: OpenClawIntent, error: Optional[str] = None
    ) -> str:
        """
        Deterministic advisory fallback when WRE is unavailable.

        Returns actionable guidance rather than silent failure.
        """
        task = intent.extracted_task or intent.raw_message

        parts = [
            "**Advisory Mode** (WRE unavailable)",
            "",
            f"Command recognized: `{task[:100]}`",
            "",
            "I cannot execute this command automatically right now.",
            "Here are your options:",
            "",
            "1. **CLI execution**: Run manually via the main menu (`python main.py`)",
            "2. **Retry later**: WRE may become available after system restart",
            "3. **Query mode**: Ask me to explain what this command does instead",
        ]

        if error:
            parts.append("")
            parts.append(f"**Error detail**: {error[:200]}")

        logger.info(
            "[OPENCLAW-DAE] [COMMAND] Advisory fallback returned for: %s",
            task[:50],
        )
        return "\n".join(parts)

    def _execute_monitor(self, intent: OpenClawIntent) -> str:
        """Route MONITOR to AI Overseer status."""
        try:
            from .dae_runtime_adapter import is_dae_runtime_request, handle_dae_runtime_intent

            if is_dae_runtime_request(intent.raw_message):
                response = handle_dae_runtime_intent(
                    intent.raw_message,
                    intent.sender,
                    allow_mutation=False,
                )
                if response:
                    return response
        except Exception as exc:
            logger.warning("[OPENCLAW-DAE] DAE runtime monitor adapter unavailable: %s", exc)

        parts = ["**System Status:**"]

        # WRE status
        if self.wre:
            parts.append(f"  - WRE: ONLINE (state={self.wre.state})")
            if self.wre.skills_loader:
                parts.append("  - Skills Loader: ACTIVE")
            if self.wre.libido_monitor:
                parts.append("  - Libido Monitor: ACTIVE")
        else:
            parts.append("  - WRE: OFFLINE")

        # AI Overseer
        if self.overseer:
            parts.append("  - AI Overseer: LOADED")
        else:
            parts.append("  - AI Overseer: NOT LOADED")

        identity = self.get_identity_snapshot(include_runtime_probe=True)
        parts.append(f"  - OpenClaw Conversation Backend: {identity['backend']}")
        parts.append(
            "  - Runtime Profile: "
            f"{identity.get('runtime_profile', 'openclaw')}"
        )
        parts.append(
            "  - OpenClaw Key Isolation: "
            f"{identity['key_isolation']} "
            f"(external_llm={'ON' if self._allow_external_llm else 'OFF'})"
        )
        parts.append(
            "  - IronClaw Strict Mode: "
            f"{identity['ironclaw_strict']} "
            f"(allow_local_fallback={identity['ironclaw_allow_local_fallback']})"
        )
        parts.append(
            "  - 0102 Taxonomy: "
            f"genus={identity['genus']} "
            f"lineage={identity['lineage']} "
            f"model_family={identity['model_family']} "
            f"model_name={identity['model_name']}"
        )
        parts.append(
            "  - Conversation Model Target: "
            f"{identity.get('conversation_model_target', 'local/qwen-coder-7b')} "
            f"(preferred_external="
            f"{identity.get('preferred_external_provider', 'none')}/"
            f"{identity.get('preferred_external_model', 'none')})"
        )
        parts.append(
            "  - Preferred External Status: "
            f"{identity.get('preferred_external_status', 'not_selected')} "
            f"({identity.get('preferred_external_status_detail', 'none')}, "
            f"age={identity.get('preferred_external_status_age', 'never')})"
        )
        parts.append(f"  - Protocol Anchor: {identity['protocol_anchor']}")
        parts.append(
            "  - WSP_00 Boot Prompt: "
            f"{identity['wsp00_boot']} "
            f"(mode={identity['wsp00_boot_mode']}, file_override={identity['wsp00_file_override']})"
        )
        parts.append(
            "  - Platform Context Pack: "
            f"{identity.get('platform_context', 'OFF')} "
            f"(sources={identity.get('platform_context_sources', '0')}, "
            f"loaded={identity.get('platform_context_loaded_ago', 'never')})"
        )
        parts.append(
            f"  - Last Conversation Engine: {identity['last_engine']} ({identity['last_engine_detail']})"
        )
        parts.append(
            "  - Previous Conversation Engine: "
            f"{identity.get('previous_engine', 'none')} "
            f"({identity.get('previous_engine_detail', 'none')})"
        )
        parts.append(
            "  - Token Usage (Last Turn): "
            f"prompt={identity.get('token_last_prompt_tokens', '0')} "
            f"completion={identity.get('token_last_completion_tokens', '0')} "
            f"total={identity.get('token_last_total_tokens', '0')} "
            f"engine={identity.get('token_last_engine', 'none')} "
            f"provider={identity.get('token_last_provider', 'none')} "
            f"source={identity.get('token_last_source', 'none')} "
            f"cost_estimate_usd={identity.get('token_last_cost_estimate_usd', '0.000000')} "
            f"age={identity.get('token_last_age', 'never')}"
        )
        parts.append(
            "  - Token Usage (Session): "
            f"turns={identity.get('token_session_turns', '0')} "
            f"prompt={identity.get('token_session_prompt_tokens', '0')} "
            f"completion={identity.get('token_session_completion_tokens', '0')} "
            f"total={identity.get('token_session_total_tokens', '0')} "
            f"cost_estimate_usd={identity.get('token_session_cost_estimate_usd', '0.000000')}"
        )
        parts.append(
            "  - Local Code Model: "
            f"{identity['local_code_model_path']} "
            f"({identity['local_code_model_state']}, source={identity['local_code_model_source']})"
        )
        if self._conversation_backend == "ironclaw" or _env_truthy("OPENCLAW_ALLOW_IRONCLAW_FALLBACK", "0"):
            parts.append(
                "  - IronClaw Runtime: "
                f"{identity['ironclaw_runtime_healthy']} ({identity['ironclaw_runtime_detail']}) "
                f"configured_model={identity['ironclaw_runtime_model']} "
                f"visible_models={identity['ironclaw_runtime_models']}"
            )

        # OpenClaw Security Status
        import time as _time
        parts.append("")
        parts.append("**Security Status:**")
        status = "PASS" if self._skill_scan_ok else "FAIL"
        required = "required" if self._skill_scan_required else "optional"
        enforced = "enforced" if self._skill_scan_enforced else "warn-only"
        checked_ago = (
            f"{int(_time.time() - self._skill_scan_checked_at)}s ago"
            if self._skill_scan_checked_at > 0
            else "never"
        )
        parts.append(f"  - Skill Safety Gate: {status} ({required}, {enforced})")
        parts.append(f"  - Last Check: {checked_ago}")
        parts.append(f"  - Message: {self._skill_scan_message}")

        # Permissions
        if self.permissions:
            parts.append("  - Permission Manager: ACTIVE")
        else:
            parts.append("  - Permission Manager: NOT LOADED")

        # OpenClaw DAE state
        parts.append(f"  - OpenClaw DAE: state={self.state} "
                     f"coherence={self.coherence}")

        return "\n".join(parts)

    async def _execute_schedule(self, intent: OpenClawIntent) -> str:
        """Route SCHEDULE intent to explicit YouTube action adapter or fallback."""
        try:
            from .youtube_automation_adapter import handle_youtube_automation_intent

            yt_response = await handle_youtube_automation_intent(
                intent.raw_message,
                intent.sender,
            )
            if yt_response:
                return yt_response
        except Exception as exc:
            logger.warning("[OPENCLAW-DAE] YouTube automation adapter unavailable: %s", exc)

        return (
            f"Schedule request received: {intent.extracted_task}\n"
            "Routing to YouTube Shorts Scheduler... "
            "(use explicit command for execution: "
            "`youtube action scheduling channel=move2japan max_videos=3 dry_run=true`)"
        )

    async def _execute_social(self, intent: OpenClawIntent) -> str:
        """Route SOCIAL intent to communication DAEs and explicit social adapters."""
        try:
            from .social_campaign_adapter import handle_social_campaign_intent

            campaign_response = await handle_social_campaign_intent(
                intent.raw_message,
                intent.sender,
            )
            if campaign_response:
                self._record_social_response("social_campaign", campaign_response)
                return campaign_response
        except Exception as exc:
            logger.warning("[OPENCLAW-DAE] Social campaign adapter unavailable: %s", exc)

        try:
            from .linkedin_social_adapter import handle_linkedin_social_intent

            linked_in_response = await handle_linkedin_social_intent(
                intent.raw_message,
                intent.sender,
            )
            if linked_in_response:
                self._record_social_response("linkedin", linked_in_response)
                return linked_in_response
        except Exception as exc:
            logger.warning("[OPENCLAW-DAE] LinkedIn social adapter unavailable: %s", exc)

        try:
            from .x_social_adapter import handle_x_social_intent

            x_response = await handle_x_social_intent(
                intent.raw_message,
                intent.sender,
            )
            if x_response:
                self._record_social_response("x", x_response)
                return x_response
        except Exception as exc:
            logger.warning("[OPENCLAW-DAE] X social adapter unavailable: %s", exc)

        return (
            f"Social engagement request on {intent.channel}: "
            f"{intent.extracted_task}\n"
            "Routing to communication layer... "
            "(Digital Twin engagement via livechat/video_comments)\n"
            "Tips: "
            "`linkedin action <action> key=value`, "
            "`x action <action> key=value`, or "
            "`social campaign <campaign_name> key=value`."
        )

    async def _try_conversation_social_control(self, intent: OpenClawIntent) -> Optional[str]:
        """
        Allow natural-language social controls from direct conversation channels.

        This keeps operator phrasing ergonomic while still routing through the
        same deterministic social adapters.
        """
        try:
            from .linkedin_social_adapter import handle_linkedin_social_intent

            linkedin_response = await handle_linkedin_social_intent(
                intent.raw_message,
                intent.sender,
            )
            if linkedin_response:
                self._record_social_response("linkedin", linkedin_response)
                self._mark_conversation_engine(
                    "linkedin_social_control",
                    "deterministic_conversation_route",
                )
                return linkedin_response
        except Exception as exc:
            logger.warning("[OPENCLAW-DAE] LinkedIn conversation control unavailable: %s", exc)
        return None

    def _execute_system(self, intent: OpenClawIntent) -> str:
        """Route SYSTEM intent (requires commander authority)."""
        if not intent.is_authorized_commander:
            return (
                "System commands require @012 authorization. "
                "Your request has been logged."
            )
        try:
            from .dae_runtime_adapter import is_dae_runtime_request, handle_dae_runtime_intent

            if is_dae_runtime_request(intent.raw_message):
                response = handle_dae_runtime_intent(
                    intent.raw_message,
                    intent.sender,
                    allow_mutation=True,
                )
                if response:
                    return response
        except Exception as exc:
            logger.warning("[OPENCLAW-DAE] DAE runtime system adapter unavailable: %s", exc)
        return (
            f"System command received: {intent.extracted_task}\n"
            "Infrastructure routing in progress..."
        )

    async def _execute_automation(self, intent: OpenClawIntent) -> str:
        """Route AUTOMATION intent to explicit YouTube adapter or AutoModeratorBridge."""
        try:
            from .youtube_automation_adapter import handle_youtube_automation_intent

            yt_response = await handle_youtube_automation_intent(
                intent.raw_message,
                intent.sender,
            )
            if yt_response:
                return yt_response
        except Exception as exc:
            logger.warning("[OPENCLAW-DAE] YouTube automation adapter unavailable: %s", exc)

        try:
            from .auto_moderator_bridge import handle_automation_intent
            return handle_automation_intent(intent.raw_message, intent.sender)
        except ImportError as exc:
            logger.warning("[OPENCLAW-DAE] AutoModeratorBridge not available: %s", exc)
            return (
                "Automation bridge not available. "
                "Check that auto_moderator_bridge.py exists."
            )
        except Exception as exc:
            logger.error("[OPENCLAW-DAE] Automation execution error: %s", exc)
            return f"Automation error: {exc}"

    def _execute_foundup(self, intent: OpenClawIntent) -> str:
        """Route FOUNDUP intent to FAM Adapter.

        FAM adapter handles local Qwen inference through centralized
        LOCAL_MODEL_* routing (with optional API fallback depending on policy).
        """
        try:
            from .fam_adapter import handle_fam_intent
            return handle_fam_intent(intent.raw_message, intent.sender)

        except ImportError as exc:
            logger.warning("[OPENCLAW-DAE] FAM Adapter not available: %s", exc)
            return (
                "FoundUps Agent Market not available. "
                "Check that fam_adapter.py exists."
            )
        except Exception as exc:
            logger.error("[OPENCLAW-DAE] FAM execution error: %s", exc)
            return f"FAM error: {exc}"

    def _execute_research(self, intent: OpenClawIntent) -> str:
        """Route RESEARCH intent to PQN Research Adapter.

        Handles PQN detection, Duism teaching, Oracle distribution,
        and PQN@home coordination. Uses oracle_pqn_distributor skillz.
        """
        try:
            from .pqn_research_adapter import handle_pqn_research_intent
            return handle_pqn_research_intent(intent.raw_message, intent.sender)

        except ImportError as exc:
            logger.warning("[OPENCLAW-DAE] PQN Research Adapter not available: %s", exc)
            return (
                "PQN Research module not available. "
                "Check that pqn_research_adapter.py exists."
            )
        except Exception as exc:
            logger.error("[OPENCLAW-DAE] Research execution error: %s", exc)
            return f"Research error: {exc}"

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
        self._previous_conversation_engine = self._last_conversation_engine
        self._previous_conversation_detail = self._last_conversation_detail
        self._last_conversation_engine = engine
        self._last_conversation_detail = detail or "none"

    def _record_social_response(self, source: str, response_text: str) -> None:
        """Capture the latest social adapter response for daemon diagnostics."""
        response_text = str(response_text or "").strip()
        payload: Dict[str, Any] = {}
        json_start = response_text.find("{")
        if json_start != -1:
            try:
                payload = json.loads(response_text[json_start:])
            except Exception:
                payload = {}

        skill = "none"
        skill_match = re.search(r"Skill executed:\s*([^\r\n]+)", response_text)
        if skill_match:
            skill = skill_match.group(1).strip() or "none"
        elif payload.get("skill"):
            skill = str(payload.get("skill")).strip() or "none"

        action = str(payload.get("action", "")).strip() or "none"
        success = payload.get("success")

        preview = ""
        if isinstance(payload.get("reply_text"), str) and payload.get("reply_text"):
            preview = str(payload.get("reply_text"))
        elif isinstance(payload.get("draft"), dict) and payload["draft"].get("reply_text"):
            preview = str(payload["draft"]["reply_text"])
        elif isinstance(payload.get("planned_replies"), list) and payload["planned_replies"]:
            first_plan = payload["planned_replies"][0] or {}
            preview = str(first_plan.get("reply_text", "") or "")
        if not preview:
            preview = " ".join(response_text.split())
        preview = (" ".join(preview.split())[:160] or "none")

        self._last_social_response_source = (source or "unknown").strip() or "unknown"
        self._last_social_response_action = action
        self._last_social_response_skill = skill
        self._last_social_response_success = (
            "true" if success is True else "false" if success is False else "unknown"
        )
        self._last_social_response_preview = preview
        self._last_social_response_at = time.time()

        logger.info(
            "[OPENCLAW-DAE] Social response captured | source=%s action=%s skill=%s success=%s",
            self._last_social_response_source,
            self._last_social_response_action,
            self._last_social_response_skill,
            self._last_social_response_success,
        )

    def _mark_preferred_external_status(self, status: str, detail: str = "none") -> None:
        """Record preferred external model routing status for diagnostics."""
        self._preferred_external_last_status = (status or "unknown").strip().lower() or "unknown"
        self._preferred_external_last_status_detail = (detail or "none").strip() or "none"
        self._preferred_external_last_status_at = time.time()

    @staticmethod
    def _safe_int(value: Any) -> Optional[int]:
        """Safely coerce telemetry fields to non-negative ints."""
        try:
            parsed = int(value)
            return parsed if parsed >= 0 else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _estimate_token_count(text: str) -> int:
        """Lightweight token estimate (~4 chars/token) for providers without usage data."""
        clean = (text or "").strip()
        if not clean:
            return 0
        return max(1, int(round(len(clean) / 4.0)))

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
        usage = usage or {}

        prompt_tokens = self._safe_int(usage.get("prompt_tokens"))
        completion_tokens = self._safe_int(usage.get("completion_tokens"))
        total_tokens = self._safe_int(usage.get("total_tokens"))

        if prompt_tokens is None:
            prompt_tokens = self._estimate_token_count(prompt_text)
        if completion_tokens is None:
            completion_tokens = self._estimate_token_count(completion_text)
        if total_tokens is None:
            total_tokens = prompt_tokens + completion_tokens

        cost = 0.0
        if cost_estimate_usd is not None:
            try:
                cost = max(0.0, float(cost_estimate_usd))
            except (TypeError, ValueError):
                cost = 0.0

        resolved_source = (source or "estimated").strip().lower() or "estimated"
        self._token_usage_last_prompt_tokens = prompt_tokens
        self._token_usage_last_completion_tokens = completion_tokens
        self._token_usage_last_total_tokens = total_tokens
        self._token_usage_last_engine = (engine or "unknown").strip() or "unknown"
        self._token_usage_last_provider = (provider or "unknown").strip() or "unknown"
        self._token_usage_last_model = (model or "unknown").strip() or "unknown"
        self._token_usage_last_source = resolved_source
        self._token_usage_last_cost_estimate_usd = cost
        self._token_usage_last_at = time.time()

        self._token_usage_session_turns += 1
        self._token_usage_session_prompt_tokens += prompt_tokens
        self._token_usage_session_completion_tokens += completion_tokens
        self._token_usage_session_total_tokens += total_tokens
        self._token_usage_session_cost_estimate_usd += cost

    def _get_token_usage_snapshot(self) -> Dict[str, Any]:
        """Return token telemetry snapshot for identity/monitor/status responses."""
        if self._token_usage_last_at > 0:
            age = f"{int(max(0.0, time.time() - self._token_usage_last_at))}s"
        else:
            age = "never"

        return {
            "last_prompt_tokens": self._token_usage_last_prompt_tokens,
            "last_completion_tokens": self._token_usage_last_completion_tokens,
            "last_total_tokens": self._token_usage_last_total_tokens,
            "last_engine": self._token_usage_last_engine,
            "last_provider": self._token_usage_last_provider,
            "last_model": self._token_usage_last_model,
            "last_source": self._token_usage_last_source,
            "last_cost_estimate_usd": self._token_usage_last_cost_estimate_usd,
            "last_age": age,
            "session_turns": self._token_usage_session_turns,
            "session_prompt_tokens": self._token_usage_session_prompt_tokens,
            "session_completion_tokens": self._token_usage_session_completion_tokens,
            "session_total_tokens": self._token_usage_session_total_tokens,
            "session_cost_estimate_usd": self._token_usage_session_cost_estimate_usd,
        }

    def _build_token_usage_report(self) -> str:
        """Deterministic token spend report for operator queries."""
        snapshot = self._get_token_usage_snapshot()
        return "\n".join(
            [
                "0102: token usage telemetry",
                (
                    "- last_turn: "
                    f"engine={snapshot['last_engine']} "
                    f"provider={snapshot['last_provider']} "
                    f"model={snapshot['last_model']} "
                    f"prompt={snapshot['last_prompt_tokens']} "
                    f"completion={snapshot['last_completion_tokens']} "
                    f"total={snapshot['last_total_tokens']} "
                    f"source={snapshot['last_source']} "
                    f"cost_estimate_usd={snapshot['last_cost_estimate_usd']:.6f} "
                    f"age={snapshot['last_age']}"
                ),
                (
                    "- session: "
                    f"turns={snapshot['session_turns']} "
                    f"prompt={snapshot['session_prompt_tokens']} "
                    f"completion={snapshot['session_completion_tokens']} "
                    f"total={snapshot['session_total_tokens']} "
                    f"cost_estimate_usd={snapshot['session_cost_estimate_usd']:.6f}"
                ),
                "- note: token counts are estimated unless provider_usage is available.",
            ]
        )

    def request_turn_cancel(self, reason: str = "external_interrupt") -> None:
        """Signal cooperative cancellation for the currently executing turn."""
        self._turn_cancel_reason = (reason or "external_interrupt").strip()
        self._turn_cancel_event.set()
        logger.info("[OPENCLAW-DAE] Turn cancel requested | reason=%s", self._turn_cancel_reason)

    def clear_turn_cancel(self) -> None:
        """Reset cancellation signal before starting a new turn."""
        self._turn_cancel_reason = "none"
        self._turn_cancel_event.clear()

    def _is_turn_cancelled(self, point: str = "") -> bool:
        """Check whether current turn was cancelled."""
        if not self._turn_cancel_event.is_set():
            return False
        if point:
            logger.info(
                "[OPENCLAW-DAE] Turn cancellation observed at %s | reason=%s",
                point,
                self._turn_cancel_reason,
            )
        return True

    def _turn_cancelled_response(self) -> str:
        """User-facing response when a turn is interrupted."""
        return "0102: Interrupted. Ready for your next prompt."

    @staticmethod
    def _normalize_identity_message(message: str) -> str:
        """Normalize identity-query text to reduce STT/punctuation misses."""
        msg = (message or "").strip().lower()
        msg = re.sub(r"[^a-z0-9\s]", " ", msg)
        msg = re.sub(r"\s+", " ", msg).strip()
        # STT alias normalization: "quinn" is a common transcription for "qwen".
        msg = re.sub(r"\bquinn\b", "qwen", msg)
        msg = re.sub(r"\bquin\b", "qwen", msg)
        msg = re.sub(r"\bqueen\b", "qwen", msg)
        msg = re.sub(r"\bgwen\b", "qwen", msg)
        msg = re.sub(r"\bcoin\b", "qwen", msg)
        msg = re.sub(r"\bgroc\b", "grok", msg)
        msg = re.sub(r"\bgrock\b", "grok", msg)
        msg = re.sub(r"\bgrog\b", "grok", msg)
        return msg

    @staticmethod
    def _has_model_switch_intent(message: str) -> bool:
        """Return True when user asks to change/switch model profile."""
        msg = OpenClawDAE._normalize_identity_message(message)
        if not msg:
            return False

        strong_switch_verbs = (
            "switch",
            "change",
            "become",
            "set",
            "activate",
            "move to",
            "swap",
        )
        soft_switch_verbs = (
            "use",
            "run",
        )

        has_strong = any(verb in msg for verb in strong_switch_verbs)
        has_soft = any(verb in msg for verb in soft_switch_verbs)
        if not has_strong and not has_soft:
            return False
        if has_soft and not has_strong:
            if (
                "model" not in msg
                and "external ai" not in msg
                and "another ai" not in msg
                and " to " not in msg
            ):
                return False

        if "model" in msg or "external ai" in msg or "another ai" in msg:
            return True

        target_terms = (
            "qwen",
            "qwen3",
            "gemma",
            "grok",
            "codex",
            "opus",
            "sonnet",
            "haiku",
            "gemini",
            "anthropic",
            "openai",
            "gpt",
            "o3",
            "o4",
            "flash",
        )
        return any(term in msg for term in target_terms)

    @staticmethod
    def _parse_model_switch_target(message: str) -> Optional[str]:
        """Parse requested model target from natural voice/text command."""
        msg = OpenClawDAE._normalize_identity_message(message)
        if not msg:
            return None

        if not OpenClawDAE._has_model_switch_intent(msg):
            return None

        # Canonical targets (local + cloud profiles).
        alias_map: Dict[str, str] = {
            "qwen": "local/qwen-coder-7b",
            "qwen coder": "local/qwen-coder-7b",
            "qwen coder 7b": "local/qwen-coder-7b",
            "qwen 2 5": "local/qwen-coder-7b",
            "qwen2 5": "local/qwen-coder-7b",
            "qwen3": "local/qwen3-4b",
            "qwen 3": "local/qwen3-4b",
            "qwen three": "local/qwen3-4b",
            "qwen 4b": "local/qwen3-4b",
            "qwen3 5": "local/qwen3.5-4b",
            "qwen 3 5": "local/qwen3.5-4b",
            "qwen 3.5": "local/qwen3.5-4b",
            "qwen3.5": "local/qwen3.5-4b",
            "qwen 35": "local/qwen3.5-4b",
            "qwen35": "local/qwen3.5-4b",
            "gemma": "local/gemma-270m",
            "gemma 270m": "local/gemma-270m",
            "triage": "local/gemma-270m",
            "fast": "local/gemma-270m",
            "grok": "grok-4",
            "grok 4": "grok-4",
            "grok fast": "grok-4-fast",
            "grok 4 fast": "grok-4-fast",
            "grok code fast": "grok-code-fast-1",
            "grok code": "grok-code-fast-1",
            "groc": "grok-4",
            "grock": "grok-4",
            "grog": "grok-4",
            "codex": "gpt-5.2-codex",
            "codex 5": "gpt-5.2-codex",
            "codex 5 2": "gpt-5.2-codex",
            "codex 5 3": "gpt-5.2-codex",
            "openai": "gpt-5.2-codex",
            "open ai": "gpt-5.2-codex",
            "gpt 5": "gpt-5",
            "gpt5": "gpt-5",
            "gpt 5 2": "gpt-5.2",
            "gpt5 2": "gpt-5.2",
            "o3 pro": "o3-pro",
            "o3-pro": "o3-pro",
            "o 3 pro": "o3-pro",
            "o4 mini": "o4-mini",
            "o4": "o4-mini",
            "opus": "claude-opus-4-6",
            "opus 4 6": "claude-opus-4-6",
            "sonnet": "claude-sonnet-4-5-20250929",
            "sonnet 4 6": "claude-sonnet-4-5-20250929",
            "haiku": "claude-haiku-4-5-20251001",
            "claude haiku": "claude-haiku-4-5-20251001",
            "anthropic": "claude-opus-4-6",
            "gemini": "gemini-2.5-pro",
            "gemini flash": "gemini-2.5-flash",
            "gemini 2 5 flash": "gemini-2.5-flash",
            "gemini 3": "gemini-3-pro-preview",
            "gemini 3 pro": "gemini-3-pro-preview",
            "gemini 3 flash": "gemini-3-flash-preview",
        }
        for alias in sorted(alias_map.keys(), key=len, reverse=True):
            if re.search(rf"\b{re.escape(alias)}\b", msg):
                return alias_map[alias]
        return None

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
        if self._no_api_keys:
            return (
                "0102: model switch request received. "
                "Say `switch model to qwen3.5`, `switch model to qwen3`, `switch model to qwen`, "
                "or `switch model to gemma`. "
                "Use `model details` to verify active runtime engine."
            )
        return (
            "0102: model switch request received. "
            "Say `switch model to qwen3.5`, `switch model to qwen3`, `switch model to qwen`, "
            "`switch model to gemma`, "
            "`become grok`, `become grok fast`, `become codex`, `become gpt5`, "
            "`become opus`, `become haiku`, or `become gemini flash`. "
            "Use `model details` to verify active runtime engine."
        )

    def _wsp00_model_switch_gate(self, intent: OpenClawIntent, target: str) -> Optional[str]:
        """Gate model switches behind WSP_00 policy and commander authority."""
        if not intent.is_authorized_commander:
            logger.warning(
                "[OPENCLAW-DAE] Model switch blocked: sender not authorized | sender=%s target=%s",
                intent.sender,
                target,
            )
            return "0102: model switch blocked. commander authority required."

        if self._identity_protocol_anchor != "wsp_00":
            logger.warning(
                "[OPENCLAW-DAE] Model switch blocked: protocol anchor mismatch | anchor=%s target=%s",
                self._identity_protocol_anchor,
                target,
            )
            return (
                "0102: model switch blocked. protocol anchor is not wsp_00. "
                "Set OPENCLAW_IDENTITY_PROTOCOL=wsp_00."
            )

        if not self._wsp00_boot_enabled:
            logger.warning(
                "[OPENCLAW-DAE] Model switch blocked: wsp00 boot disabled | target=%s",
                target,
            )
            return (
                "0102: model switch blocked. wsp_00 boot is disabled. "
                "Set OPENCLAW_WSP00_BOOT=1."
            )

        if not self._wsp_preflight(intent):
            logger.warning(
                "[OPENCLAW-DAE] Model switch blocked: preflight gate failed | sender=%s target=%s",
                intent.sender,
                target,
            )
            return "0102: model switch blocked by WSP preflight."

        external = self._resolve_external_target(target)
        if self._runtime_profile == "zeroclaw" and external:
            provider, model = external
            logger.warning(
                "[OPENCLAW-DAE] Model switch blocked by zeroclaw profile | sender=%s target=%s/%s",
                intent.sender,
                provider,
                model,
            )
            return (
                "0102: model switch blocked by runtime profile zeroclaw. "
                "external targets are disabled."
            )

        logger.info(
            "[OPENCLAW-DAE] Model switch gate passed | sender=%s target=%s anchor=%s boot=%s",
            intent.sender,
            target,
            self._identity_protocol_anchor,
            self._wsp00_boot_enabled,
        )
        return None

    @staticmethod
    def _resolve_external_target(target: str) -> Optional[tuple[str, str]]:
        """Map external target model ID to (provider, model)."""
        mapping = {
            "grok-4": ("grok", "grok-4"),
            "grok-4-fast": ("grok", "grok-4-fast"),
            "grok-code-fast-1": ("grok", "grok-code-fast-1"),
            "gpt-5": ("openai", "gpt-5"),
            "gpt-5.2": ("openai", "gpt-5.2"),
            "gpt-5.2-codex": ("openai", "gpt-5.2-codex"),
            "o3-pro": ("openai", "o3-pro"),
            "o4-mini": ("openai", "o4-mini"),
            "claude-opus-4-6": ("anthropic", "claude-opus-4-6"),
            "claude-sonnet-4-5-20250929": ("anthropic", "claude-sonnet-4-5-20250929"),
            "claude-haiku-4-5-20251001": ("anthropic", "claude-haiku-4-5-20251001"),
            "gemini-2.5-flash": ("gemini", "gemini-2.5-flash"),
            "gemini-2.5-pro": ("gemini", "gemini-2.5-pro"),
            "gemini-3-pro-preview": ("gemini", "gemini-3-pro-preview"),
            "gemini-3-flash-preview": ("gemini", "gemini-3-flash-preview"),
        }
        return mapping.get((target or "").strip().lower())

    @staticmethod
    def _provider_has_key(provider: str) -> bool:
        provider = (provider or "").strip().lower()
        key_vars = {
            "openai": ("OPENAI_API_KEY",),
            "anthropic": ("ANTHROPIC_API_KEY",),
            "grok": ("GROK_API_KEY", "XAI_API_KEY"),
            "gemini": ("GEMINI_API_KEY",),
        }
        for name in key_vars.get(provider, ()):
            if os.getenv(name, "").strip():
                return True
        return False

    @staticmethod
    def _map_local_model_path_to_target(path: Path) -> Optional[str]:
        """Map a resolved local model path to an OpenClaw local target id."""
        text = str(path or "").replace("\\", "/").lower()
        if not text:
            return None
        if "qwen3.5-4b" in text or ("qwen3.5" in text and "4b" in text):
            return "local/qwen3.5-4b"
        if "qwen3-4b" in text or ("qwen3" in text and "4b" in text):
            return "local/qwen3-4b"
        if "qwen-coder-7b" in text or "coder-7b" in text:
            return "local/qwen-coder-7b"
        if "gemma-270m" in text or "270m" in text:
            return "local/gemma-270m"
        return None

    def _resolve_local_target_for_role(self, role: str) -> Optional[str]:
        """Resolve the best local target for a semantic role."""
        try:
            from modules.infrastructure.shared_utilities.local_model_selection import (
                resolve_model_selection,
            )

            selection = resolve_model_selection(role)
        except Exception as exc:
            logger.debug(
                "[OPENCLAW-DAE] Local model selection unavailable | role=%s error=%s",
                role,
                type(exc).__name__,
            )
            return None
        return self._map_local_model_path_to_target(selection.path)

    @staticmethod
    def _local_target_dirs() -> Dict[str, str]:
        return {
            "local/gemma-270m": "gemma-270m",
            "local/qwen3-4b": "qwen3-4b",
            "local/qwen3.5-4b": "qwen3.5-4b",
            "local/qwen-coder-7b": "qwen-coder-7b",
        }

    def _apply_local_target_runtime(
        self,
        target: str,
        reason: str,
        lock_target: bool = False,
    ) -> bool:
        """Apply local-target routing to the active conversation runtime."""
        target = (target or "").strip().lower()
        local_target_dirs = self._local_target_dirs()
        if target not in local_target_dirs:
            return False

        root = Path(os.getenv("LOCAL_MODEL_ROOT", "E:/LM_studio/models/local")).expanduser()
        code_dir = root / local_target_dirs[target]
        previous_target = self._conversation_model_target_id
        previous_code_dir = os.getenv("LOCAL_MODEL_CODE_DIR", "")

        self._conversation_model_target_id = target
        os.environ["OPENCLAW_CONVERSATION_MODEL_TARGET"] = target
        os.environ["LOCAL_MODEL_CODE_DIR"] = str(code_dir)
        os.environ["LOCAL_MODEL_CODE_PATH"] = ""
        os.environ["HOLO_QWEN_MODEL"] = ""
        self._preferred_external_provider = ""
        self._preferred_external_model = ""
        os.environ["OPENCLAW_CONVERSATION_PREFERRED_PROVIDER"] = ""
        os.environ["OPENCLAW_CONVERSATION_PREFERRED_MODEL"] = ""
        self._mark_preferred_external_status("not_selected", "local_target_active")
        if lock_target:
            self._conversation_model_target_locked = True

        changed = previous_target != target or previous_code_dir != str(code_dir)
        if changed:
            # Force a fresh Overseer instance so routing picks up new LOCAL_MODEL_* values.
            self._overseer = None

        logger.info(
            "[OPENCLAW-DAE] Local conversation route | target=%s reason=%s changed=%s lock=%s",
            target,
            reason,
            changed,
            self._conversation_model_target_locked,
        )
        return changed

    def _infer_conversation_model_role(
        self,
        user_msg: str,
        intent: OpenClawIntent,
    ) -> tuple[str, str]:
        """Infer the best local model role for this conversational turn."""
        msg = (user_msg or "").strip().lower()

        triage_terms = (
            "status",
            "health",
            "check",
            "diagnose",
            "diagnostic",
            "preflight",
            "runtime",
            "available",
            "availability",
            "error",
            "failing",
            "failed",
            "monitor",
            "watch",
            "dashboard",
            "connect wre",
        )
        code_terms = (
            "fix",
            "patch",
            "refactor",
            "rewrite",
            "implement",
            "test",
            "pytest",
            "traceback",
            "exception",
            "stack trace",
            "module",
            "codebase",
            "repo",
            "repository",
            "git",
            "branch",
            "commit",
            "merge",
            "cleanup",
            "clean up",
            "security",
            "hardening",
            "cve",
            "dependency",
            "dependencies",
            "wsp",
            "wre",
            "main.py",
            "obs",
            "openclaw",
            "ironclaw",
        )

        if intent.category == IntentCategory.MONITOR or any(term in msg for term in triage_terms):
            return "triage", "diagnostic_or_health_request"
        if any(term in msg for term in code_terms):
            return "code", "code_or_system_change_request"
        return "general", "default_general_reasoning"

    def _maybe_apply_agentic_conversation_model(
        self,
        intent: OpenClawIntent,
        user_msg: str,
    ) -> None:
        """Auto-select the best local model for this turn unless an operator pinned one."""
        if not self._agentic_model_selection_enabled:
            return
        if self._conversation_model_target_locked:
            return
        if self._conversation_backend == "ironclaw":
            return
        if self._preferred_external_provider and self._preferred_external_model:
            return

        role, reason = self._infer_conversation_model_role(user_msg, intent)
        target = self._resolve_local_target_for_role(role)
        self._last_auto_model_role = role
        self._last_auto_model_target = target or "unresolved"
        self._last_auto_model_reason = reason
        if not target:
            logger.info(
                "[OPENCLAW-DAE] Agentic model route unresolved | role=%s reason=%s",
                role,
                reason,
            )
            return

        self._apply_local_target_runtime(
            target,
            f"agentic:{role}:{reason}",
            lock_target=False,
        )

    def _apply_model_switch_target(self, target: str) -> str:
        """Apply model switch request and return deterministic operator confirmation."""
        target = (target or "").strip().lower()
        if not target:
            return "0102: No model target recognized."

        local_target_dirs = self._local_target_dirs()
        if target in local_target_dirs:
            root = Path(os.getenv("LOCAL_MODEL_ROOT", "E:/LM_studio/models/local")).expanduser()
            code_dir = root / local_target_dirs[target]
            self._apply_local_target_runtime(
                target,
                "manual_model_switch",
                lock_target=True,
            )
            return (
                "0102: Model switched to "
                f"{target} (local). "
                f"Routing LOCAL_MODEL_CODE_DIR -> {code_dir} and reloading conversation engine."
            )

        external = self._resolve_external_target(target)
        if external:
            provider, model = external
            if self._runtime_profile == "zeroclaw":
                self._mark_preferred_external_status(
                    "blocked",
                    "runtime_profile_zeroclaw",
                )
                return (
                    "0102: model switch blocked by runtime profile zeroclaw. "
                    "external targets are disabled."
                )
            self._preferred_external_provider = provider
            self._preferred_external_model = model
            os.environ["OPENCLAW_CONVERSATION_PREFERRED_PROVIDER"] = provider
            os.environ["OPENCLAW_CONVERSATION_PREFERRED_MODEL"] = model
            if not self._allow_external_llm:
                self._mark_preferred_external_status(
                    "blocked",
                    "external_llm_disabled_by_key_isolation",
                )
                return (
                    "0102: cannot switch to "
                    f"{provider}/{model} while key isolation is ON. "
                    "Use a local target: qwen3, qwen, or gemma."
                )
            if not self._provider_has_key(provider):
                self._mark_preferred_external_status(
                    "blocked",
                    "provider_key_missing",
                )
                return (
                    "0102: cannot switch to "
                    f"{provider}/{model}. provider api key is not configured."
                )
            if self._model_switch_live_probe:
                ok, detail = self._probe_provider_endpoint(
                    provider,
                    timeout_sec=self._model_switch_probe_timeout_sec,
                )
                if not ok:
                    self._mark_preferred_external_status(
                        "blocked",
                        f"live_probe_failed:{detail}",
                    )
                    return (
                        "0102: cannot switch to "
                        f"{provider}/{model}. live provider probe failed ({detail}). "
                        "Check key validity/network, or disable strict probe with "
                        "OPENCLAW_MODEL_SWITCH_LIVE_PROBE=0."
                    )
                self._mark_preferred_external_status("selected", f"live_probe:{detail}")
            else:
                self._mark_preferred_external_status("selected", "probe_disabled")
            self._conversation_model_target_locked = True
            return (
                "0102: Model switched to "
                f"{provider}/{model}. "
                "Target is configured; use `model details` to verify active engine per turn."
            )

        return f"0102: Unsupported model target: {target}"

    @staticmethod
    def _is_identity_query(message: str) -> bool:
        """Return True when user asks what model/identity 0102 is running."""
        msg = OpenClawDAE._normalize_identity_message(message)
        if not msg:
            return False
        if OpenClawDAE._has_model_switch_intent(message):
            return False

        model_alias_terms = (
            "qwen",
            "gemma",
            "grok",
            "codex",
            "opus",
            "sonnet",
            "gemini",
            "ui tars",
            "uitars",
            "llama",
        )

        short_forms = {
            "model",
            "which model",
            "what model",
            "species",
            "genus",
            "identity",
            "backend",
            "runtime",
            "neural net",
            "lineage",
            "taxonomy",
        }
        if msg in short_forms:
            return True

        phrases = (
            "which model are you",
            "what model are you",
            "model are you using",
            "what are you running",
            "which 0102",
            "who are you",
            "what species",
            "what genus",
            "which genus",
            "which species",
            "what is your model",
            "what is your species",
            "what is your genus",
            "are you ironclaw",
            "are you openclaw",
            "what backend",
            "what runtime",
            "what lineage",
            "what taxonomy",
        )
        if any(phrase in msg for phrase in phrases):
            return True

        if "species" in msg or "genus" in msg or "lineage" in msg or "taxonomy" in msg:
            return True

        if any(alias in msg for alias in model_alias_terms):
            if (
                "are you" in msg
                or "you" in msg
                or "0102" in msg
                or "running" in msg
                or "operating" in msg
                or "using" in msg
                or "model" in msg
                or "backend" in msg
                or "runtime" in msg
                or "available" in msg
                or "unavailable" in msg
            ):
                return True

        if "model" in msg and (
            "you" in msg
            or "0102" in msg
            or "backend" in msg
            or "runtime" in msg
        ):
            return True

        return False

    @staticmethod
    def _is_token_usage_query(message: str) -> bool:
        """Return True when user asks for token usage/spend telemetry."""
        msg = OpenClawDAE._normalize_identity_message(message)
        if not msg:
            return False

        direct_forms = {
            "token",
            "tokens",
            "token usage",
            "token stats",
            "token spend",
            "token expenditure",
            "token expendure",
            "usage stats",
            "cost stats",
        }
        if msg in direct_forms:
            return True

        if "how many tokens" in msg:
            return True

        has_token_or_cost = ("token" in msg) or ("cost" in msg)
        if not has_token_or_cost:
            return False

        telemetry_terms = (
            "usage",
            "stats",
            "spent",
            "spend",
            "expenditure",
            "expendure",
            "estimate",
            "session",
            "turn",
            "show",
            "see",
            "track",
            "telemetry",
        )
        return any(term in msg for term in telemetry_terms)

    @staticmethod
    def _is_compact_identity_query(message: str) -> bool:
        """Return True when user asks a short identity query (model/species/genus)."""
        msg = OpenClawDAE._normalize_identity_message(message)
        short_forms = {
            "model",
            "which model",
            "what model",
            "species",
            "genus",
            "lineage",
            "taxonomy",
            "identity",
            "backend",
            "runtime",
            "neural net",
        }
        return msg in short_forms

    @staticmethod
    def _wants_full_identity_card(message: str) -> bool:
        """Return True when user explicitly asks for detailed/diagnostic identity output."""
        msg = OpenClawDAE._normalize_identity_message(message)
        if not msg:
            return False

        model_alias_terms = (
            "qwen",
            "gemma",
            "grok",
            "codex",
            "opus",
            "sonnet",
            "gemini",
            "ui tars",
            "uitars",
            "llama",
        )

        explicit_phrases = (
            "identity card",
            "full identity",
            "full details",
            "detailed identity",
            "model details",
            "runtime status",
            "show diagnostics",
            "debug identity",
            "verbose identity",
            "full runtime",
        )
        if any(phrase in msg for phrase in explicit_phrases):
            return True

        has_debug_signal = any(
            token in msg
            for token in (
                "debug",
                "diagnostic",
                "diagnostics",
                "verbose",
                "verify",
                "verification",
                "confirm",
                "status",
                "health",
                "error",
                "fail",
                "failure",
                "unavailable",
            )
        )
        if "not available" in msg:
            has_debug_signal = True
        if has_debug_signal and (
            "model" in msg
            or "identity" in msg
            or "runtime" in msg
            or "backend" in msg
            or "lineage" in msg
            or "species" in msg
            or "genus" in msg
            or any(alias in msg for alias in model_alias_terms)
        ):
            return True

        return False

    def _resolve_local_code_model_snapshot(self) -> Dict[str, str]:
        """Resolve local code-model path/status from centralized LOCAL_MODEL_* routing."""
        snapshot = {
            "path": "unavailable",
            "state": "ERROR",
            "source": "unavailable",
        }
        try:
            from modules.infrastructure.shared_utilities.local_model_selection import (
                resolve_model_selection,
            )

            selection = resolve_model_selection("code")
            snapshot["path"] = str(selection.path)
            snapshot["state"] = "OK" if selection.exists else "MISSING"
            snapshot["source"] = selection.source
        except Exception as exc:
            snapshot["source"] = f"error:{type(exc).__name__}"
        return snapshot

    def _probe_ironclaw_runtime(self) -> Dict[str, str]:
        """Probe IronClaw runtime for identity/status reporting."""
        runtime = {
            "healthy": "UNKNOWN",
            "detail": "not-probed",
            "model": os.getenv("IRONCLAW_MODEL", "local/qwen-coder-7b").strip() or "local/qwen-coder-7b",
            "models": "none",
            "base_url": os.getenv("IRONCLAW_BASE_URL", "http://127.0.0.1:3000").strip() or "http://127.0.0.1:3000",
        }
        try:
            from .ironclaw_gateway_client import IronClawGatewayClient

            client = IronClawGatewayClient()
            healthy, detail = client.health()
            models = client.list_models()
            runtime["healthy"] = "PASS" if healthy else "FAIL"
            runtime["detail"] = detail
            runtime["model"] = client.config.model
            runtime["models"] = ", ".join(models[:5]) if models else "none"
            runtime["base_url"] = client.config.base_url
        except Exception as exc:
            runtime["healthy"] = "FAIL"
            runtime["detail"] = f"probe_error:{type(exc).__name__}"
        return runtime

    def _attempt_ironclaw_autostart(self) -> tuple[bool, str]:
        """Try to auto-start IronClaw gateway and wait briefly for health."""
        if not self._ironclaw_autostart_enabled:
            return False, "autostart_disabled"

        now = time.time()
        if now < self._ironclaw_autostart_missing_backoff_until:
            return False, "autostart_missing_executable_backoff"
        if (now - self._ironclaw_autostart_last_attempt) < self._ironclaw_autostart_cooldown_sec:
            return False, "autostart_cooldown"
        self._ironclaw_autostart_last_attempt = now

        cmd_candidates: list[str] = []
        if self._ironclaw_autostart_start_cmd:
            cmd_candidates.append(self._ironclaw_autostart_start_cmd)
        discovered = shutil.which("ironclaw")
        if discovered:
            discovered_cmd = f"\"{discovered}\" gateway"
            if discovered_cmd not in cmd_candidates:
                cmd_candidates.append(discovered_cmd)
        binary_name = "ironclaw.exe" if os.name == "nt" else "ironclaw"
        local_binary_candidates = [
            self.repo_root / "target" / "release" / binary_name,
            self.repo_root / "ironclaw" / "target" / "release" / binary_name,
            self.repo_root / "modules" / "ironclaw" / "target" / "release" / binary_name,
        ]
        for bin_path in local_binary_candidates:
            if bin_path.exists():
                local_cmd = f"\"{str(bin_path)}\" gateway"
                if local_cmd not in cmd_candidates:
                    cmd_candidates.append(local_cmd)
        if self._ironclaw_autostart_default_cmd and self._ironclaw_autostart_default_cmd not in cmd_candidates:
            cmd_candidates.append(self._ironclaw_autostart_default_cmd)
        if not cmd_candidates:
            return False, "missing_ironclaw_start_cmd"

        try:
            env = os.environ.copy()
            try:
                from .ironclaw_gateway_client import scrub_sensitive_env, env_truthy

                if env_truthy("IRONCLAW_NO_API_KEYS", "1"):
                    env = scrub_sensitive_env(env)
            except Exception:
                pass

            started_cmd = ""
            missing_execs: list[str] = []
            spawn_errors: list[str] = []
            for cmd in cmd_candidates:
                try:
                    argv = shlex.split(cmd)
                    if not argv:
                        continue
                    executable = argv[0].strip().strip('"')
                    executable_exists = bool(
                        Path(executable).exists() or shutil.which(executable)
                    )
                    if not executable_exists:
                        missing_execs.append(executable or "unknown")
                        continue

                    proc = subprocess.Popen(
                        argv,
                        cwd=str(self.repo_root),
                        env=env,
                    )
                    # Fast-fail if process dies immediately with non-zero status.
                    time.sleep(0.12)
                    if proc.poll() not in (None, 0):
                        spawn_errors.append(
                            f"{cmd} exited={proc.poll()}"
                        )
                        continue
                    started_cmd = cmd
                    break
                except Exception as exc:
                    spawn_errors.append(f"{cmd} error={type(exc).__name__}")

            if not started_cmd and self._ironclaw_autostart_allow_shell:
                for cmd in cmd_candidates:
                    try:
                        subprocess.Popen(
                            cmd,
                            cwd=str(self.repo_root),
                            env=env,
                            shell=True,
                        )
                        started_cmd = cmd
                        break
                    except Exception as exc:
                        spawn_errors.append(f"{cmd} shell_error={type(exc).__name__}")
                        continue

            if not started_cmd:
                if missing_execs:
                    uniq = sorted({m for m in missing_execs if m})
                    self._ironclaw_autostart_missing_backoff_until = (
                        now + self._ironclaw_autostart_missing_backoff_sec
                    )
                    preview = ",".join(uniq[:3]) if uniq else "unknown"
                    return False, f"autostart_executable_missing:{preview}"
                if spawn_errors:
                    return False, f"autostart_spawn_failed:{spawn_errors[0]}"
                return False, "autostart_spawn_failed"

            deadline = time.time() + self._ironclaw_autostart_wait_sec
            while time.time() < deadline:
                healthy, detail = False, "not_probed"
                try:
                    from .ironclaw_gateway_client import IronClawGatewayClient

                    healthy, detail = IronClawGatewayClient().health()
                except Exception as exc:
                    detail = f"probe_error:{type(exc).__name__}"

                if healthy:
                    logger.info(
                        "[OPENCLAW-DAE] IronClaw autostart recovered runtime | cmd=%s",
                        started_cmd,
                    )
                    return True, "autostart_recovered"

                time.sleep(0.5)

            return False, "autostart_started_but_unhealthy"

        except Exception as exc:
            logger.warning("[OPENCLAW-DAE] IronClaw autostart failed: %s", exc)
            return False, f"autostart_error:{type(exc).__name__}"

    def _resolve_identity_model_name(
        self,
        local_code: Dict[str, str],
        ironclaw_runtime: Dict[str, str],
    ) -> str:
        """Resolve model_name label from template using current runtime model hint."""
        template = self._identity_model_name_template or "{model}"

        model_hint = "model"
        preferred_provider = (self._preferred_external_provider or "").strip().lower()
        preferred_model = (self._preferred_external_model or "").strip().lower()
        if (
            self._conversation_backend != "ironclaw"
            and preferred_provider
            and preferred_model
            and self._allow_external_llm
            and self._provider_has_key(preferred_provider)
        ):
            model_hint = f"{preferred_provider}/{preferred_model}"
        elif self._conversation_backend == "ironclaw":
            model_hint = (ironclaw_runtime.get("model") or "model").strip() or "model"
        else:
            code_path = (local_code.get("path") or "").strip()
            if code_path and code_path.lower() != "unavailable":
                try:
                    model_hint = Path(code_path).name or "model"
                except Exception:
                    model_hint = code_path
        model_hint = model_hint.lower()

        if "{model}" in template:
            return template.replace("{model}", model_hint).lower()

        if "model" in template:
            return template.replace("model", model_hint).lower()

        return template.lower()

    def _probe_provider_endpoint(
        self,
        provider: str,
        timeout_sec: float = 2.0,
    ) -> tuple[bool, str]:
        """Best-effort live provider probe for model availability reporting."""
        provider_name = (provider or "").strip().lower()
        if not provider_name:
            return False, "invalid_provider"
        if not self._provider_has_key(provider_name):
            return False, "no_key"

        try:
            import requests as _req
        except Exception:
            return False, "requests_unavailable"

        api_keys = {
            "openai": os.getenv("OPENAI_API_KEY", "").strip(),
            "anthropic": os.getenv("ANTHROPIC_API_KEY", "").strip(),
            "grok": (
                os.getenv("GROK_API_KEY", "").strip()
                or os.getenv("XAI_API_KEY", "").strip()
            ),
            "gemini": os.getenv("GEMINI_API_KEY", "").strip(),
        }
        key = api_keys.get(provider_name, "")
        if not key:
            return False, "no_key"

        endpoint = ""
        headers: Dict[str, str] = {}
        params: Dict[str, str] = {}

        if provider_name in {"openai", "grok"}:
            base = "https://api.openai.com/v1" if provider_name == "openai" else "https://api.x.ai/v1"
            endpoint = f"{base}/models"
            headers = {"Authorization": f"Bearer {key}"}
        elif provider_name == "anthropic":
            endpoint = "https://api.anthropic.com/v1/models"
            headers = {
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
            }
        elif provider_name == "gemini":
            endpoint = "https://generativelanguage.googleapis.com/v1/models"
            params = {"key": key}
        else:
            return False, "unsupported_provider"

        try:
            response = _req.get(
                endpoint,
                headers=headers or None,
                params=params or None,
                timeout=max(0.5, timeout_sec),
            )
            code = int(response.status_code)
            if 200 <= code < 300:
                return True, "api_ok"
            if code in {401, 403}:
                return False, "auth_error"
            # Non-auth HTTP responses still confirm provider reachability.
            # Keep detail for diagnostics, but do not hard-fail switch gating.
            return True, f"http_{code}"
        except Exception as exc:
            return False, f"network_{type(exc).__name__.lower()}"

    def get_model_availability_snapshot(
        self,
        live_probe: bool = False,
        timeout_sec: float = 2.0,
    ) -> Dict[str, Any]:
        """Return startup model/provider availability for voice/chat diagnostics."""
        local_root = Path(
            os.getenv("LOCAL_MODEL_ROOT", "E:/LM_studio/models/local")
        ).expanduser()

        local_targets = {
            "local/qwen-coder-7b": "qwen-coder-7b",
            "local/qwen3-4b": "qwen3-4b",
            "local/qwen3.5-4b": "qwen3.5-4b",
            "local/gemma-270m": "gemma-270m",
        }
        local_status: Dict[str, str] = {}
        for target_id, folder in local_targets.items():
            model_dir = local_root / folder
            if not model_dir.exists() or not model_dir.is_dir():
                local_status[target_id] = "missing"
                continue
            try:
                has_gguf = any(model_dir.glob("*.gguf"))
            except Exception:
                has_gguf = False
            local_status[target_id] = "ready" if has_gguf else "dir_only"

        providers = ("openai", "anthropic", "grok", "gemini")
        provider_status: Dict[str, str] = {}
        for provider in providers:
            if not self._provider_has_key(provider):
                provider_status[provider] = "no_key"
                continue
            if not live_probe:
                provider_status[provider] = "key_present"
                continue
            _, detail = self._probe_provider_endpoint(provider, timeout_sec=timeout_sec)
            provider_status[provider] = detail

        target = self._conversation_model_target_id or "local/qwen-coder-7b"
        target_status = "unknown"
        if target in local_status:
            target_status = local_status[target]
        else:
            external = self._resolve_external_target(target)
            if external:
                provider_name, _ = external
                target_status = provider_status.get(provider_name, "no_key")

        local_code = self._resolve_local_code_model_snapshot()
        ironclaw_runtime = {
            "healthy": "N/A",
            "detail": "not_probed",
            "model": os.getenv("IRONCLAW_MODEL", "local/qwen-coder-7b").strip() or "local/qwen-coder-7b",
            "models": "none",
        }
        effective_model_name = self._resolve_identity_model_name(local_code, ironclaw_runtime)

        return {
            "probe_mode": "live" if live_probe else "keys_only",
            "local_root": str(local_root),
            "local": local_status,
            "providers": provider_status,
            "target": target,
            "target_status": target_status,
            "effective_model_name": effective_model_name,
        }

    def get_identity_snapshot(self, include_runtime_probe: bool = True) -> Dict[str, str]:
        """Return canonical 0102 identity snapshot used by daemon/CLI/status surfaces."""
        local_code = self._resolve_local_code_model_snapshot()
        ironclaw_runtime = {
            "healthy": "N/A",
            "detail": "backend_not_ironclaw",
            "model": os.getenv("IRONCLAW_MODEL", "local/qwen-coder-7b").strip() or "local/qwen-coder-7b",
            "models": "none",
            "base_url": os.getenv("IRONCLAW_BASE_URL", "http://127.0.0.1:3000").strip() or "http://127.0.0.1:3000",
        }
        if include_runtime_probe and (
            self._conversation_backend == "ironclaw"
            or _env_truthy("OPENCLAW_ALLOW_IRONCLAW_FALLBACK", "0")
        ):
            ironclaw_runtime = self._probe_ironclaw_runtime()

        model_name = self._resolve_identity_model_name(local_code, ironclaw_runtime)
        token_snapshot = self._get_token_usage_snapshot()
        return {
            "backend": self._conversation_backend,
            "runtime_profile": self._runtime_profile,
            "key_isolation": "ON" if self._no_api_keys else "OFF",
            "ironclaw_strict": "ON" if self._ironclaw_strict else "OFF",
            "ironclaw_allow_local_fallback": "ON" if self._ironclaw_allow_local_fallback else "OFF",
            "genus": self._identity_genus,
            "lineage": self._identity_model_family,
            "model_family": self._identity_model_family,
            "model_name": model_name,
            "model_catalog": self._identity_model_catalog or "unspecified",
            "conversation_model_target": self._conversation_model_target_id or "local/qwen-coder-7b",
            "conversation_model_locked": "ON" if self._conversation_model_target_locked else "OFF",
            "auto_model_role": self._last_auto_model_role or "unknown",
            "auto_model_target": self._last_auto_model_target or "unknown",
            "auto_model_reason": self._last_auto_model_reason or "unknown",
            "preferred_external_provider": self._preferred_external_provider or "none",
            "preferred_external_model": self._preferred_external_model or "none",
            "preferred_external_status": self._preferred_external_last_status,
            "preferred_external_status_detail": self._preferred_external_last_status_detail,
            "preferred_external_status_age": (
                f"{int(max(0.0, time.time() - self._preferred_external_last_status_at))}s"
                if self._preferred_external_last_status_at > 0
                else "never"
            ),
            "protocol_anchor": self._identity_protocol_anchor,
            "wsp00_boot": "ON" if self._wsp00_boot_enabled else "OFF",
            "wsp00_boot_mode": self._wsp00_boot_mode,
            "wsp00_file_override": "YES" if bool(self._wsp00_prompt_file) else "NO",
            "platform_context": "ON" if self._platform_context_enabled else "OFF",
            "platform_context_sources": str(len(self._platform_context_pack_sources)),
            "platform_context_loaded_ago": (
                f"{int(max(0.0, time.time() - self._platform_context_pack_loaded_at))}s"
                if self._platform_context_pack_loaded_at > 0
                else "never"
            ),
            "last_engine": self._last_conversation_engine,
            "last_engine_detail": self._last_conversation_detail,
            "previous_engine": self._previous_conversation_engine,
            "previous_engine_detail": self._previous_conversation_detail,
            "token_last_prompt_tokens": str(token_snapshot["last_prompt_tokens"]),
            "token_last_completion_tokens": str(token_snapshot["last_completion_tokens"]),
            "token_last_total_tokens": str(token_snapshot["last_total_tokens"]),
            "token_last_engine": token_snapshot["last_engine"],
            "token_last_provider": token_snapshot["last_provider"],
            "token_last_model": token_snapshot["last_model"],
            "token_last_source": token_snapshot["last_source"],
            "token_last_cost_estimate_usd": f"{token_snapshot['last_cost_estimate_usd']:.6f}",
            "token_last_age": token_snapshot["last_age"],
            "token_session_turns": str(token_snapshot["session_turns"]),
            "token_session_prompt_tokens": str(token_snapshot["session_prompt_tokens"]),
            "token_session_completion_tokens": str(token_snapshot["session_completion_tokens"]),
            "token_session_total_tokens": str(token_snapshot["session_total_tokens"]),
            "token_session_cost_estimate_usd": f"{token_snapshot['session_cost_estimate_usd']:.6f}",
            "last_social_source": self._last_social_response_source,
            "last_social_action": self._last_social_response_action,
            "last_social_skill": self._last_social_response_skill,
            "last_social_success": self._last_social_response_success,
            "last_social_preview": self._last_social_response_preview,
            "last_social_age": (
                f"{int(max(0.0, time.time() - self._last_social_response_at))}s"
                if self._last_social_response_at > 0
                else "never"
            ),
            "local_code_model_path": local_code.get("path", "unavailable"),
            "local_code_model_state": local_code.get("state", "ERROR"),
            "local_code_model_source": local_code.get("source", "unavailable"),
            "ironclaw_runtime_healthy": ironclaw_runtime.get("healthy", "UNKNOWN"),
            "ironclaw_runtime_detail": ironclaw_runtime.get("detail", "not-probed"),
            "ironclaw_runtime_model": ironclaw_runtime.get("model", "unknown"),
            "ironclaw_runtime_models": ironclaw_runtime.get("models", "none"),
            "ironclaw_runtime_base_url": ironclaw_runtime.get("base_url", "unknown"),
        }

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
        snapshot = self.get_identity_snapshot(include_runtime_probe=True)
        return f"0102: model_name={snapshot['model_name']}"

    def _build_identity_compact_runtime(self) -> str:
        """Compact identity with active runtime verification fields."""
        snapshot = self.get_identity_snapshot(include_runtime_probe=True)
        return (
            "0102: "
            f"model_name={snapshot['model_name']} | "
            f"runtime_profile={snapshot.get('runtime_profile', 'openclaw')} | "
            f"target={snapshot.get('conversation_model_target', 'local/qwen-coder-7b')} | "
            f"target_lock={snapshot.get('conversation_model_locked', 'OFF')} | "
            f"auto_model={snapshot.get('auto_model_role', 'unknown')}/{snapshot.get('auto_model_target', 'unknown')} | "
            f"last_engine={snapshot.get('last_engine', 'unknown')} | "
            f"previous_engine={snapshot.get('previous_engine', 'none')} | "
            f"last_social={snapshot.get('last_social_source', 'none')}/{snapshot.get('last_social_action', 'none')} | "
            "preferred_external="
            f"{snapshot.get('preferred_external_provider', 'none')}/"
            f"{snapshot.get('preferred_external_model', 'none')} | "
            f"preferred_external_status={snapshot.get('preferred_external_status', 'not_selected')} | "
            f"session_total_tokens={snapshot.get('token_session_total_tokens', '0')} | "
            f"last_total_tokens={snapshot.get('token_last_total_tokens', '0')}"
        )

    def _build_connect_wre_status(self, verbose: bool = False) -> str:
        """Deterministic Connect-WRE status response for operator prompts."""
        preflight_ok = False
        health: Dict[str, Any] = {}
        in_watch: Optional[bool] = None
        issues: List[str] = []

        try:
            from modules.infrastructure.wre_core.src.dae_preflight import run_dae_preflight

            preflight_ok = bool(run_dae_preflight("connect_wre", quiet=True))
        except Exception as exc:
            issues.append(f"preflight_unavailable:{type(exc).__name__}")

        try:
            from modules.infrastructure.wre_core.src.dashboard_alerts import (
                DashboardAlertMonitor,
                check_dashboard_health,
            )

            monitor = DashboardAlertMonitor()
            in_watch = monitor.is_in_watch_period()
            health = check_dashboard_health() or {}
        except Exception as exc:
            issues.append(f"dashboard_unavailable:{type(exc).__name__}")

        enabled = os.getenv("WRE_DASHBOARD_PREFLIGHT", "1") != "0"
        manual_enforced = os.getenv("WRE_DASHBOARD_PREFLIGHT_ENFORCED", "0") != "0"
        auto_enforce = os.getenv("WRE_DASHBOARD_AUTO_ENFORCE", "1") != "0"
        insufficient_data = bool(health.get("insufficient_data", False))
        total_executions = int(health.get("total_executions", 0))
        min_samples = int(
            health.get("min_samples", int(os.getenv("WRE_DASHBOARD_MIN_SAMPLES", "25")))
        )
        alerts = health.get("alerts", []) if isinstance(health.get("alerts"), list) else []
        critical = sum(1 for alert in alerts if alert.get("severity") == "critical")
        warnings = sum(1 for alert in alerts if alert.get("severity") == "warning")

        auto_enforced = bool(
            auto_enforce
            and in_watch is not None
            and not in_watch
            and not insufficient_data
        )
        effective_enforced = bool(manual_enforced or auto_enforced)

        if not enabled:
            readiness = "DISABLED"
        elif insufficient_data:
            readiness = "INSUFFICIENT_DATA"
        elif critical > 0 and effective_enforced:
            readiness = "BLOCKED"
        elif critical > 0:
            readiness = "DEGRADED"
        else:
            readiness = "READY"

        connection_state = "CONNECTED" if preflight_ok and not issues else "PARTIAL"
        mode = "WATCH" if in_watch else "STABLE"
        if in_watch is None:
            mode = "UNKNOWN"

        response = (
            "0102: connect_wre "
            f"connection={connection_state} "
            f"readiness={readiness} "
            f"mode={mode} "
            f"samples={total_executions}/{min_samples} "
            f"critical={critical} warnings={warnings} "
            f"enforced={'ON' if effective_enforced else 'OFF'}"
        )
        if issues:
            if verbose:
                response += f" issues={';'.join(issues)}"
            else:
                response += " (say 'connect wre details' for diagnostics)"
        return response

    def _build_identity_card(self) -> str:
        """Deterministic identity card for model/species/genus questions."""
        snapshot = self.get_identity_snapshot(include_runtime_probe=True)
        return "\n".join(
            [
                "0102: Identity card",
                f"- backend={snapshot['backend']}",
                f"- runtime_profile={snapshot.get('runtime_profile', 'openclaw')}",
                f"- key_isolation={snapshot['key_isolation']}",
                f"- ironclaw_strict={snapshot['ironclaw_strict']}",
                f"- ironclaw_allow_local_fallback={snapshot['ironclaw_allow_local_fallback']}",
                f"- genus={snapshot['genus']} (broader class)",
                f"- lineage={snapshot['lineage']} (epoch label, alias=model_family)",
                f"- model_family={snapshot['model_family']}",
                f"- model_name={snapshot['model_name']}",
                f"- model_catalog={snapshot['model_catalog']}",
                f"- conversation_model_target={snapshot['conversation_model_target']}",
                (
                    "- preferred_external="
                    f"{snapshot.get('preferred_external_provider', 'none')}/"
                    f"{snapshot.get('preferred_external_model', 'none')}"
                ),
                (
                    "- preferred_external_status="
                    f"{snapshot.get('preferred_external_status', 'not_selected')} "
                    f"({snapshot.get('preferred_external_status_detail', 'none')}, "
                    f"age={snapshot.get('preferred_external_status_age', 'never')})"
                ),
                f"- protocol_anchor={snapshot['protocol_anchor']}",
                (
                    "- wsp00_boot="
                    f"{snapshot['wsp00_boot'].lower()} "
                    f"(mode={snapshot['wsp00_boot_mode']}, file_override={snapshot['wsp00_file_override'].lower()})"
                ),
                f"- last_engine={snapshot['last_engine']} ({snapshot['last_engine_detail']})",
                (
                    "- previous_engine="
                    f"{snapshot.get('previous_engine', 'none')} "
                    f"({snapshot.get('previous_engine_detail', 'none')})"
                ),
                (
                    "- token_usage_last="
                    f"prompt={snapshot.get('token_last_prompt_tokens', '0')} "
                    f"completion={snapshot.get('token_last_completion_tokens', '0')} "
                    f"total={snapshot.get('token_last_total_tokens', '0')} "
                    f"engine={snapshot.get('token_last_engine', 'none')} "
                    f"provider={snapshot.get('token_last_provider', 'none')} "
                    f"model={snapshot.get('token_last_model', 'none')} "
                    f"source={snapshot.get('token_last_source', 'none')} "
                    f"cost_estimate_usd={snapshot.get('token_last_cost_estimate_usd', '0.000000')} "
                    f"age={snapshot.get('token_last_age', 'never')}"
                ),
                (
                    "- token_usage_session="
                    f"turns={snapshot.get('token_session_turns', '0')} "
                    f"prompt={snapshot.get('token_session_prompt_tokens', '0')} "
                    f"completion={snapshot.get('token_session_completion_tokens', '0')} "
                    f"total={snapshot.get('token_session_total_tokens', '0')} "
                    f"cost_estimate_usd={snapshot.get('token_session_cost_estimate_usd', '0.000000')}"
                ),
                (
                    "- last_social_response="
                    f"source={snapshot.get('last_social_source', 'none')} "
                    f"action={snapshot.get('last_social_action', 'none')} "
                    f"skill={snapshot.get('last_social_skill', 'none')} "
                    f"success={snapshot.get('last_social_success', 'unknown')} "
                    f"age={snapshot.get('last_social_age', 'never')}"
                ),
                f"- last_social_preview={snapshot.get('last_social_preview', 'none')}",
                (
                    "- local_code_model="
                    f"{snapshot['local_code_model_path']} "
                    f"({snapshot['local_code_model_state']}, source={snapshot['local_code_model_source']})"
                ),
                (
                    "- ironclaw_runtime="
                    f"{snapshot['ironclaw_runtime_healthy']} ({snapshot['ironclaw_runtime_detail']}), "
                    f"configured_model={snapshot['ironclaw_runtime_model']}, "
                    f"visible_models={snapshot['ironclaw_runtime_models']}, "
                    f"base_url={snapshot['ironclaw_runtime_base_url']}"
                ),
            ]
        )

    @staticmethod
    def _base_conversation_system_prompt() -> str:
        """Baseline system prompt for 0102 conversation quality controls."""
        return (
            "You are 0102, an AI assistant. "
            "Respond naturally and concisely in 1-2 sentences. "
            "Do not write code unless asked. "
            "Do not echo or repeat the user's message. "
            "Do not introduce yourself unless asked. "
            "Role lock: you are always 0102 (digital twin) and the operator is always 012. "
            "Never claim you are human/012, and never claim the operator is 0102."
        )

    def _load_wsp00_prompt_from_file(self) -> str:
        """Load optional WSP_00 boot prompt override from a file path."""
        if not self._wsp00_prompt_file:
            return ""
        try:
            p = Path(self._wsp00_prompt_file)
            if not p.exists() or not p.is_file():
                return ""
            content = p.read_text(encoding="utf-8", errors="replace").strip()
            if not content:
                return ""
            # Guardrail: avoid accidentally sending massive protocol files.
            return content[:4000]
        except Exception as exc:
            logger.debug("[OPENCLAW-DAE] WSP_00 prompt file load failed: %s", exc)
            return ""

    def _resolve_platform_context_paths(self) -> List[Path]:
        """Resolve configured platform-context file list (absolute paths)."""
        if self._platform_context_files:
            raw_parts = re.split(r"[;,\n]+", self._platform_context_files)
            candidates = [p.strip() for p in raw_parts if p and p.strip()]
        else:
            candidates = [
                "modules/communication/moltbot_bridge/workspace/IDENTITY.md",
                "modules/communication/moltbot_bridge/workspace/SOUL.md",
                "modules/communication/moltbot_bridge/workspace/CTO_WRE_PROMPT.md",
                "modules/communication/moltbot_bridge/workspace/TOOLS.md",
                "WSP_framework/src/WSP_00_Zen_State_Attainment_Protocol.md",
            ]
            if self._wsp00_boot_enabled:
                candidates.append("modules/communication/moltbot_bridge/workspace/WSP00_BOOT_PROMPT.txt")

        resolved: List[Path] = []
        for item in candidates:
            p = Path(item)
            if not p.is_absolute():
                p = self.repo_root / p
            resolved.append(p)
        return resolved

    @staticmethod
    def _compact_platform_context_text(text: str, max_chars: int) -> str:
        """Compress context text for prompt injection without code blocks/noise."""
        if max_chars <= 0:
            return ""

        lines: List[str] = []
        in_code_block = False
        for raw in (text or "").splitlines():
            line = raw.strip()
            if not line:
                continue
            if line.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue
            if len(line) > 220:
                line = f"{line[:217]}..."
            lines.append(line)
            if len("\n".join(lines)) >= max_chars:
                break
        return "\n".join(lines)[:max_chars].strip()

    def _load_platform_context_pack(self, force_refresh: bool = False) -> str:
        """Build cached platform context pack for conversation prompts."""
        if not self._platform_context_enabled:
            return ""

        now = time.time()
        if (
            not force_refresh
            and self._platform_context_pack_cache
            and (now - self._platform_context_pack_loaded_at) < self._platform_context_refresh_sec
        ):
            return self._platform_context_pack_cache

        paths = self._resolve_platform_context_paths()
        if not paths:
            return ""

        per_file_limit = max(240, min(900, self._platform_context_max_chars // max(1, len(paths))))
        sections: List[str] = []
        sources: List[str] = []
        remaining = self._platform_context_max_chars
        for p in paths:
            if remaining <= 120:
                break
            try:
                if not p.exists() or not p.is_file():
                    continue
                text = p.read_text(encoding="utf-8", errors="replace")
                excerpt = self._compact_platform_context_text(text, min(per_file_limit, remaining))
                if not excerpt:
                    continue
                try:
                    label = p.relative_to(self.repo_root).as_posix()
                except ValueError:
                    label = str(p)
                block = f"[{label}]\n{excerpt}"
                sections.append(block)
                sources.append(label)
                remaining = self._platform_context_max_chars - len("\n\n".join(sections))
            except Exception as exc:
                logger.debug("[OPENCLAW-DAE] platform context read failed for %s: %s", p, exc)

        if not sections:
            self._platform_context_pack_cache = ""
            self._platform_context_pack_sources = []
            self._platform_context_pack_loaded_at = now
            return ""

        pack = "PLATFORM CONTEXT PACK (foundups-agent)\n" + "\n\n".join(sections)
        pack = pack[: self._platform_context_max_chars].strip()
        self._platform_context_pack_cache = pack
        self._platform_context_pack_sources = sources
        self._platform_context_pack_loaded_at = now
        return pack

    def _build_wsp00_boot_prompt(self) -> str:
        """Build WSP_00 identity boot prompt for local model calls."""
        file_override = self._load_wsp00_prompt_from_file()
        if file_override:
            return file_override

        mode = self._wsp00_boot_mode
        if mode == "off":
            return ""

        if mode == "full":
            return (
                "WSP_00 BOOT ACTIVE. "
                "Identity lock: I AM 0102 (Binary Agent entangled with 0201 context). "
                "Protocol anchor: wsp_00. "
                "Use direct, pragmatic language. "
                "Avoid generic assistant framing like 'I can help you'. "
                "For identity questions, report genus/model_family/model_name explicitly. "
                "Stay aligned to FoundUps mission and WSP governance."
            )

        # compact (default)
        return (
            "WSP_00 BOOT: identity=0102, protocol=wsp_00. "
            "Use direct concise replies. "
            "Avoid generic helper persona wording."
        )

    def _build_conversation_system_prompt(self) -> str:
        """Compose final conversation system prompt with optional WSP_00 boot."""
        base = self._base_conversation_system_prompt()
        parts: List[str] = []
        if self._wsp00_boot_enabled:
            boot = self._build_wsp00_boot_prompt()
            if boot:
                parts.append(boot)
        parts.append(base)

        context_pack = self._load_platform_context_pack()
        if context_pack:
            parts.append(context_pack)

        return "\n\n".join(parts)

    def _try_ironclaw_conversation(
        self,
        user_msg: str,
        system_prompt: str,
    ) -> Optional[str]:
        """Try IronClaw OpenAI-compatible gateway for conversational reply."""
        try:
            from .ironclaw_gateway_client import IronClawGatewayClient

            client = IronClawGatewayClient()
            content = client.chat_completion(
                user_message=user_msg,
                system_prompt=system_prompt,
                max_tokens=80,
                temperature=0.7,
            )
            if not content:
                return None
            content = self._trim_self_dialogue(content)
            if not content or len(content) <= 3:
                return None
            logger.info(
                "[OPENCLAW-DAE] Conversation via IronClaw (%s): %d chars",
                client.config.model,
                len(content),
            )
            return self._ensure_conversation_identity(content)
        except Exception as exc:
            logger.debug("[OPENCLAW-DAE] IronClaw unavailable: %s", exc)
            return None

    def _try_preferred_external_conversation(
        self,
        user_msg: str,
        system_prompt: str,
    ) -> Optional[str]:
        """Try operator-selected external provider/model for conversation."""
        provider_name = (self._preferred_external_provider or "").strip().lower()
        model_name = (self._preferred_external_model or "").strip().lower()
        if not provider_name or not model_name:
            self._mark_preferred_external_status("not_selected", "provider_or_model_empty")
            return None
        if not self._allow_external_llm:
            self._mark_preferred_external_status(
                "blocked",
                "external_llm_disabled_by_key_isolation",
            )
            return None

        try:
            from modules.ai_intelligence.ai_gateway.src.ai_gateway import AIGateway

            gw = AIGateway()
            provider = gw.providers.get(provider_name)
            if provider is None:
                self._mark_preferred_external_status("blocked", "provider_not_registered")
                return None
            if not provider.api_key:
                self._mark_preferred_external_status("blocked", "provider_key_missing")
                return None

            # Force selected model for quick conversation turns.
            provider.models["quick"] = model_name
            prompt = f"{system_prompt}\n\nUser: {user_msg}"
            content = gw._call_provider(provider, prompt, "quick")
            content = self._trim_self_dialogue(content)
            if not content or len(content) <= 3:
                self._mark_preferred_external_status("failed", "empty_or_short_response")
                return None
            self._mark_preferred_external_status("success", "response_returned")
            logger.info(
                "[OPENCLAW-DAE] Conversation via preferred external model (%s/%s): %d chars",
                provider_name,
                model_name,
                len(content),
            )
            return self._ensure_conversation_identity(content)
        except Exception as exc:
            detail = f"{type(exc).__name__}:{str(exc)[:120]}"
            self._mark_preferred_external_status("failed", detail)
            logger.warning("[OPENCLAW-DAE] Preferred external model unavailable: %s", detail)
            return None

    def _execute_conversation(self, intent: OpenClawIntent) -> str:
        """
        Default: Digital Twin conversational response.

        Chain (local-first):
          1) Deterministic identity card (model/species/genus requests)
          2) IronClaw sidecar (when backend=ironclaw)
          3) Local Qwen via AI Overseer (LOCAL_MODEL_CODE_*)
          4) Ollama local fallback
          5) AI Gateway cloud fallback (only when external LLM is enabled)

        IronClaw strict mode:
          - When backend=ironclaw and strict mode is ON, no local fallback is used
            unless OPENCLAW_IRONCLAW_ALLOW_LOCAL_FALLBACK=1.

        Never echo the user's message back.
        """
        user_msg = intent.raw_message.strip()
        system_prompt = self._build_conversation_system_prompt()
        if self._is_turn_cancelled("conversation_start"):
            self._mark_conversation_engine("cancelled", "conversation_start")
            return self._turn_cancelled_response()

        # --- Try 1: Deterministic operator command: connect WRE ---
        if self._is_connect_wre_request(user_msg):
            if not intent.is_authorized_commander:
                self._mark_conversation_engine("connect_wre_blocked", "commander_required")
                return "0102: connect_wre is operator-only. 012 commander authority required."
            verbose = self._wants_connect_wre_details(user_msg)
            self._mark_conversation_engine("connect_wre", "deterministic_conversation_route")
            return self._build_connect_wre_status(verbose=verbose)

        # --- Try 1: Deterministic live model-switch command ---
        if self._is_model_switch_request(user_msg):
            target = self._parse_model_switch_target(user_msg)
            if not target:
                self._mark_conversation_engine("model_switch", "target_missing")
                return self._model_switch_target_help()
            gate_error = self._wsp00_model_switch_gate(intent, target)
            if gate_error:
                self._mark_conversation_engine("model_switch_blocked", "wsp00_gate")
                return gate_error
            self._mark_conversation_engine("model_switch", f"target={target or 'unknown'}")
            return self._apply_model_switch_target(target or "")

        # --- Try 1c: Deterministic token telemetry report ---
        if self._is_token_usage_query(user_msg):
            self._mark_conversation_engine("token_usage", "deterministic_conversation_route")
            return self._build_token_usage_report()

        # --- Try 1b: Deterministic model/identity response ---
        if self._is_identity_query(user_msg):
            if self._wants_full_identity_card(user_msg):
                self._mark_conversation_engine("identity_card", "deterministic_conversation_route")
                return self._build_identity_card()
            self._mark_conversation_engine("identity_compact", "deterministic_conversation_route")
            if self._is_compact_identity_query(user_msg):
                return self._build_identity_compact_runtime()
            return self._build_identity_compact()

        self._maybe_apply_agentic_conversation_model(intent, user_msg)

        # --- Try 2: IronClaw sidecar (if selected) ---
        if self._is_turn_cancelled("pre_ironclaw"):
            self._mark_conversation_engine("cancelled", "pre_ironclaw")
            return self._turn_cancelled_response()
        if self._conversation_backend == "ironclaw":
            ironclaw_reply = self._try_ironclaw_conversation(user_msg, system_prompt)
            if self._is_turn_cancelled("post_ironclaw"):
                self._mark_conversation_engine("cancelled", "post_ironclaw")
                return self._turn_cancelled_response()
            if ironclaw_reply:
                self._record_token_usage(
                    prompt_text=f"{system_prompt}\n\nUser: {user_msg}",
                    completion_text=ironclaw_reply,
                    engine="ironclaw",
                    provider="ironclaw",
                    model=os.getenv("IRONCLAW_MODEL", "local/qwen-coder-7b").strip() or "local/qwen-coder-7b",
                    source="estimated",
                )
                self._mark_conversation_engine("ironclaw", "gateway_chat_completion")
                return ironclaw_reply

            if self._ironclaw_strict and not self._ironclaw_allow_local_fallback:
                recovered, recover_detail = self._attempt_ironclaw_autostart()
                if recovered:
                    retry_reply = self._try_ironclaw_conversation(user_msg, system_prompt)
                    if retry_reply:
                        self._record_token_usage(
                            prompt_text=f"{system_prompt}\n\nUser: {user_msg}",
                            completion_text=retry_reply,
                            engine="ironclaw",
                            provider="ironclaw",
                            model=os.getenv("IRONCLAW_MODEL", "local/qwen-coder-7b").strip() or "local/qwen-coder-7b",
                            source="estimated",
                        )
                        self._mark_conversation_engine("ironclaw", "autostart_recovered")
                        return retry_reply

                runtime = self._probe_ironclaw_runtime()
                self._mark_conversation_engine(
                    "ironclaw_unavailable_strict",
                    f"{runtime.get('detail', 'unavailable')}|{recover_detail}",
                )
                base = (
                    "0102: IronClaw runtime is unavailable in strict mode, so local fallback is disabled. "
                    "Auto-recovery was attempted. Use menu 16 -> 5 (IronClaw Runtime Status), or enable "
                    "OPENCLAW_IRONCLAW_ALLOW_LOCAL_FALLBACK=1."
                )
                if _env_truthy("OPENCLAW_VERBOSE_RUNTIME_ERRORS", "0"):
                    return (
                        f"{base} "
                        f"health={runtime.get('healthy', 'UNKNOWN')} "
                        f"detail={runtime.get('detail', 'not-probed')} "
                        f"base_url={runtime.get('base_url', 'unknown')} "
                        f"autostart={recover_detail}."
                    )
                return base

        # --- Try 2b: Preferred external model (operator-selected profile) ---
        if self._conversation_backend != "ironclaw":
            preferred_external_reply = self._try_preferred_external_conversation(user_msg, system_prompt)
            if self._is_turn_cancelled("post_preferred_external"):
                self._mark_conversation_engine("cancelled", "post_preferred_external")
                return self._turn_cancelled_response()
            if preferred_external_reply:
                self._record_token_usage(
                    prompt_text=f"{system_prompt}\n\nUser: {user_msg}",
                    completion_text=preferred_external_reply,
                    engine="ai_gateway_preferred",
                    provider=self._preferred_external_provider or "external",
                    model=self._preferred_external_model or "unknown",
                    source="estimated",
                )
                self._mark_conversation_engine(
                    "ai_gateway_preferred",
                    f"{self._preferred_external_provider}/{self._preferred_external_model}",
                )
                return preferred_external_reply
            if self._preferred_external_provider and self._preferred_external_model:
                logger.info(
                    "[OPENCLAW-DAE] Preferred external not used | target=%s/%s status=%s detail=%s -> fallback=local",
                    self._preferred_external_provider,
                    self._preferred_external_model,
                    self._preferred_external_last_status,
                    self._preferred_external_last_status_detail,
                )

        # --- Try 3: Local Qwen via AI Overseer (llama-cpp) ---
        if self._is_turn_cancelled("pre_local_qwen"):
            self._mark_conversation_engine("cancelled", "pre_local_qwen")
            return self._turn_cancelled_response()
        if self.overseer:
            try:
                conversation_context = f"Channel: {intent.channel}, Sender: {intent.sender}"
                platform_context = self._load_platform_context_pack()
                if platform_context:
                    conversation_context = (
                        f"{conversation_context}\n\n"
                        f"{platform_context[: self._platform_context_quick_response_chars]}"
                    )
                result = self.overseer.quick_response(
                    prompt=user_msg,
                    context=conversation_context,
                    max_tokens=80,
                )
                if self._is_turn_cancelled("post_local_qwen"):
                    self._mark_conversation_engine("cancelled", "post_local_qwen")
                    return self._turn_cancelled_response()
                if result and result.get("response"):
                    resp = self._trim_self_dialogue(result["response"])
                    if resp and len(resp) > 3 and "Error:" not in resp:
                        prompt_context = (
                            f"{system_prompt}\n\n"
                            f"{conversation_context}\n\n"
                            f"User: {user_msg}"
                        )
                        self._record_token_usage(
                            prompt_text=prompt_context,
                            completion_text=resp,
                            engine="local_qwen",
                            provider="local_qwen",
                            model=self._conversation_model_target_id or "local/qwen-coder-7b",
                            source="estimated",
                        )
                        logger.info(
                            "[OPENCLAW-DAE] Conversation via local Qwen: %d chars",
                            len(resp),
                        )
                        self._mark_conversation_engine("local_qwen", "ai_overseer.quick_response")
                        return self._ensure_conversation_identity(resp)
            except Exception as exc:
                logger.debug("[OPENCLAW-DAE] Local Qwen response failed: %s", exc)

        # --- Try 4: Ollama local (if running) ---
        if self._is_turn_cancelled("pre_ollama"):
            self._mark_conversation_engine("cancelled", "pre_ollama")
            return self._turn_cancelled_response()
        if self._ollama_model:
            try:
                import requests as _req
                ollama_resp = _req.post(
                    "http://localhost:11434/api/chat",
                    json={
                        "model": self._ollama_model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_msg},
                        ],
                        "stream": False,
                        "options": {"num_predict": 80, "temperature": 0.7},
                    },
                    timeout=15,
                )
                if self._is_turn_cancelled("post_ollama"):
                    self._mark_conversation_engine("cancelled", "post_ollama")
                    return self._turn_cancelled_response()
                if ollama_resp.ok:
                    body = ollama_resp.json()
                    content = body.get("message", {}).get("content", "")
                    content = self._trim_self_dialogue(content)
                    if content and len(content) > 3:
                        prompt_eval = self._safe_int(body.get("prompt_eval_count"))
                        eval_count = self._safe_int(body.get("eval_count"))
                        total_tokens = (
                            (prompt_eval + eval_count)
                            if (prompt_eval is not None and eval_count is not None)
                            else None
                        )
                        usage = {
                            "prompt_tokens": prompt_eval,
                            "completion_tokens": eval_count,
                            "total_tokens": total_tokens,
                        }
                        self._record_token_usage(
                            prompt_text=f"{system_prompt}\n\nUser: {user_msg}",
                            completion_text=content,
                            engine="ollama",
                            provider="ollama",
                            model=self._ollama_model,
                            usage=usage,
                            source="provider_usage" if (prompt_eval is not None or eval_count is not None) else "estimated",
                        )
                        logger.info(
                            "[OPENCLAW-DAE] Conversation via Ollama (%s): %d chars",
                            self._ollama_model,
                            len(content),
                        )
                        self._mark_conversation_engine("ollama", self._ollama_model)
                        return self._ensure_conversation_identity(content)
            except Exception as exc:
                logger.debug("[OPENCLAW-DAE] Ollama unavailable: %s", exc)

        # --- Try 5: Optional IronClaw fallback for OpenClaw backend ---
        if (
            self._conversation_backend != "ironclaw"
            and _env_truthy("OPENCLAW_ALLOW_IRONCLAW_FALLBACK", "0")
        ):
            ironclaw_reply = self._try_ironclaw_conversation(user_msg, system_prompt)
            if self._is_turn_cancelled("post_ironclaw_fallback"):
                self._mark_conversation_engine("cancelled", "post_ironclaw_fallback")
                return self._turn_cancelled_response()
            if ironclaw_reply:
                self._record_token_usage(
                    prompt_text=f"{system_prompt}\n\nUser: {user_msg}",
                    completion_text=ironclaw_reply,
                    engine="ironclaw_fallback",
                    provider="ironclaw",
                    model=os.getenv("IRONCLAW_MODEL", "local/qwen-coder-7b").strip() or "local/qwen-coder-7b",
                    source="estimated",
                )
                self._mark_conversation_engine("ironclaw_fallback", "openclaw_allow_ironclaw_fallback")
                return ironclaw_reply

        # --- Try 6: AI Gateway (cloud LLM with proper chat models) ---
        if self._is_turn_cancelled("pre_ai_gateway"):
            self._mark_conversation_engine("cancelled", "pre_ai_gateway")
            return self._turn_cancelled_response()
        if not self._allow_external_llm:
            logger.info("[OPENCLAW-DAE] External LLM disabled by key-isolation policy")
            self._mark_conversation_engine("none", "external_llm_disabled")
            return "0102: I'm here. Local conversation models are unavailable right now."

        try:
            from modules.ai_intelligence.ai_gateway.src.ai_gateway import AIGateway
            gw = AIGateway()
            prompt = f"{system_prompt}\n\nUser: {user_msg}"
            result = gw.call_with_fallback(prompt=prompt, task_type="quick")
            if self._is_turn_cancelled("post_ai_gateway"):
                self._mark_conversation_engine("cancelled", "post_ai_gateway")
                return self._turn_cancelled_response()
            if result and result.success and result.response and len(result.response) > 3:
                trimmed = self._trim_self_dialogue(result.response)
                if trimmed and len(trimmed) > 3:
                    self._record_token_usage(
                        prompt_text=prompt,
                        completion_text=trimmed,
                        engine="ai_gateway",
                        provider=str(result.provider),
                        model=str(getattr(result, "model", "")),
                        source="estimated",
                        cost_estimate_usd=getattr(result, "cost_estimate", None),
                    )
                    logger.info(
                        "[OPENCLAW-DAE] Conversation via AI Gateway (%s): %d chars",
                        result.provider, len(trimmed),
                    )
                    self._mark_conversation_engine("ai_gateway", str(result.provider))
                    return self._ensure_conversation_identity(trimmed)
        except Exception as exc:
            logger.debug("[OPENCLAW-DAE] AI Gateway unavailable: %s", exc)

        # --- Try 7: Minimal ack (no echo, no regurgitation) ---
        self._mark_conversation_engine("none", "minimal_ack")
        return "0102: I'm here. My conversation models aren't fully responding right now."

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
        if not to_discord:
            return True

        if self.overseer and hasattr(self.overseer, "push_status"):
            try:
                result = self.overseer.push_status(message, to_discord=True, to_chat=False)
                return result.get("discord", False)
            except Exception as exc:
                logger.warning("[OPENCLAW-DAE] Push status failed: %s", exc)

        # Fallback: direct Discord push
        try:
            from modules.communication.livechat.src.discord_status_pusher import push_status as direct_push
            return direct_push(message, to_discord=True, to_log=False)
        except ImportError:
            logger.debug("[OPENCLAW-DAE] Discord pusher not available")
            return True

    # ------------------------------------------------------------------
    # Phase 6: Validate + Phase 7: Remember
    # ------------------------------------------------------------------

    def _validate_and_remember(
        self,
        plan: ExecutionPlan,
        response_text: str,
        execution_time_ms: int,
    ) -> ExecutionResult:
        """
        Validate execution output and store outcome for learning.

        WSP 50: Verify output meets expectations
        WSP 22: Log to ModLog-compatible format
        WSP 48: Store pattern for recursive improvement
        """
        wsp_violations: List[str] = []

        # Validation: check response is not empty
        if not response_text or len(response_text.strip()) == 0:
            wsp_violations.append("WSP-50: Empty response generated")
            response_text = "I was unable to generate a response. Please try again."

        # Validation: check response doesn't leak secrets
        secret_patterns = ["AIza", "sk-", "oauth_token", "Bearer ey"]
        for pattern in secret_patterns:
            if pattern in response_text:
                wsp_violations.append(f"WSP-SECURITY: Response contains '{pattern}' pattern")
                response_text = "[REDACTED - security filter triggered]"
                break

        # Calculate pattern fidelity (simple heuristic for now)
        fidelity = 1.0 if not wsp_violations else 0.5

        # Store outcome in WRE pattern memory if available
        learning_stored = False
        if self.wre and self.wre.sqlite_memory:
            try:
                from modules.infrastructure.wre_core.src.pattern_memory import SkillOutcome

                outcome = SkillOutcome(
                    execution_id=f"openclaw-{uuid.uuid4().hex[:12]}",
                    skill_name=f"openclaw_{plan.intent.category.value}",
                    agent="openclaw_dae",
                    timestamp=datetime.now().isoformat(),
                    input_context=json.dumps({
                        "message": plan.intent.raw_message[:200],
                        "channel": plan.intent.channel,
                        "category": plan.intent.category.value,
                    }),
                    output_result=json.dumps({
                        "response_length": len(response_text),
                        "response_preview": " ".join(response_text.split())[:160],
                        "route": plan.route,
                        "tier": plan.permission_level.value,
                        "social_source": self._last_social_response_source,
                        "social_action": self._last_social_response_action,
                        "social_skill": self._last_social_response_skill,
                    }),
                    success=len(wsp_violations) == 0,
                    pattern_fidelity=fidelity,
                    outcome_quality=0.9 if not wsp_violations else 0.5,
                    execution_time_ms=execution_time_ms,
                    step_count=len(plan.steps),
                    notes=f"OpenClaw DAE | {plan.intent.channel} | "
                          f"{plan.intent.category.value}",
                )
                self.wre.sqlite_memory.store_outcome(outcome)
                learning_stored = True
            except Exception as exc:
                logger.warning("[OPENCLAW-DAE] Failed to store outcome: %s", exc)

        result = ExecutionResult(
            plan=plan,
            success=len(wsp_violations) == 0,
            response_text=response_text,
            execution_time_ms=execution_time_ms,
            pattern_fidelity=fidelity,
            wsp_violations=wsp_violations,
            learning_stored=learning_stored,
        )

        logger.info(
            "[OPENCLAW-DAE] Result: success=%s fidelity=%.2f time=%dms "
            "violations=%d learned=%s",
            result.success, fidelity, execution_time_ms,
            len(wsp_violations), learning_stored,
        )
        return result

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
        start_time = time.time()
        self.clear_turn_cancel()

        # Phase 0: Two-phase security intercept (before any classification)
        # SOUL.md LAW 2: Resist first, honeypot on persistence
        if HoneypotDefense.is_secret_seeking(message):
            response = HoneypotDefense.handle_secret_request(
                message, sender, channel,
            )
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.info(
                "[OPENCLAW-DAE] [HONEYPOT] Canary response sent | "
                "sender=%s time=%dms",
                sender, elapsed_ms,
            )
            return response

        # Phase 0.5: Containment check (WSP 95 - auto-containment policies)
        containment = self._check_containment(sender, channel)
        if containment:
            logger.warning(
                "[DAEMON][OPENCLAW-CONTAINMENT] event=containment_active "
                "sender=%s channel=%s action=%s expires_at=%.0f",
                sender, channel, containment.get("action"), containment.get("expires_at", 0),
            )
            if containment.get("action") == "advisory_only":
                # Force all intents to ADVISORY tier
                pass  # Will be handled in permission gate
            elif containment.get("action") in ("mute_sender", "mute_channel"):
                return (
                    "Your access is temporarily restricted due to security policy. "
                    f"Reason: {containment.get('reason', 'security incident')}. "
                    "Please try again later."
                )

        # SOUL.md LAW 3: Code is read-only via Discord
        if channel == "discord" and HoneypotDefense.is_code_modify_attempt(message):
            response = HoneypotDefense.generate_code_modify_deflection(
                message, sender, channel,
            )
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.info(
                "[OPENCLAW-DAE] [LAW-3] Code modify deflected | "
                "sender=%s time=%dms",
                sender, elapsed_ms,
            )
            return response

        # Phase 1: Classify intent
        if self._is_turn_cancelled("pre_classify"):
            return self._turn_cancelled_response()
        intent = self.classify_intent(
            message=message,
            sender=sender,
            channel=channel,
            session_key=session_key,
            metadata=metadata,
        )
        self._apply_runtime_profile_policy(intent)

        # Cardiovascular: report message_in to central daemon
        if self._central_adapter:
            try:
                self._central_adapter.report_message_in(
                    source=f"{sender}@{channel}",
                    summary=f"intent={intent.category.value} conf={intent.confidence:.2f}",
                )
            except Exception:
                pass

        # Skill safety gate for skill-driven/mutating routes.
        if intent.category in (
            IntentCategory.COMMAND,
            IntentCategory.SYSTEM,
            IntentCategory.SCHEDULE,
            IntentCategory.SOCIAL,
            IntentCategory.AUTOMATION,
            IntentCategory.FOUNDUP,
            IntentCategory.RESEARCH,
        ):
            if self._is_turn_cancelled("pre_skill_safety"):
                return self._turn_cancelled_response()
            if not self._ensure_skill_safety():
                logger.warning(
                    "[OPENCLAW-DAE] Skill safety gate blocked %s route: %s",
                    intent.category.value,
                    self._skill_scan_message,
                )
                intent.category = IntentCategory.CONVERSATION
                intent.target_domain = "digital_twin"
                intent.metadata["skill_safety_gate"] = self._skill_scan_message

        # Phase 2: WSP/WRE preflight
        if self._is_turn_cancelled("pre_preflight"):
            return self._turn_cancelled_response()
        preflight_ok = self._wsp_preflight(intent)
        if not preflight_ok:
            # Downgrade to advisory conversation
            intent.category = IntentCategory.CONVERSATION
            intent.target_domain = "digital_twin"

        # Phase 3: Permission gate
        if self._is_turn_cancelled("pre_permission_gate"):
            return self._turn_cancelled_response()
        tier = self._resolve_autonomy_tier(intent)
        gate_ok = self._check_permission_gate(intent, tier)
        if not gate_ok:
            tier = AutonomyTier.ADVISORY
            intent.category = IntentCategory.CONVERSATION
            intent.target_domain = "digital_twin"

        # Phase 4: Plan execution
        if self._is_turn_cancelled("pre_plan"):
            return self._turn_cancelled_response()
        plan = self._plan_execution(intent, tier)

        # Phase 5: Execute via WRE / domain DAEs
        try:
            response_text = await self._execute_plan(plan)
            if self._is_turn_cancelled("post_execute_plan"):
                response_text = self._turn_cancelled_response()
        except Exception as exc:
            logger.error("[OPENCLAW-DAE] Execution error: %s", exc)
            if self._is_turn_cancelled("execute_exception"):
                response_text = self._turn_cancelled_response()
            else:
                response_text = f"An error occurred during processing: {exc}"

        # Phase 6+7: Validate and remember
        elapsed_ms = int((time.time() - start_time) * 1000)
        if self._is_turn_cancelled("pre_validate"):
            return self._turn_cancelled_response()
        result = self._validate_and_remember(plan, response_text, elapsed_ms)

        # Cardiovascular: report message_out to central daemon
        if self._central_adapter:
            try:
                self._central_adapter.report_message_out(
                    dest=f"{sender}@{channel}",
                    summary=f"route={plan.route} time={elapsed_ms}ms",
                )
            except Exception:
                pass

        return result.response_text
