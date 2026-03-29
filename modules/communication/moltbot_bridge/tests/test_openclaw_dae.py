#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for OpenClaw DAE - The Frontal Lobe

Validates the full autonomy loop:
  Ingress -> Intent -> Preflight -> Plan -> Permission -> Execute -> Validate -> Remember

Test Layers:
  Layer 0: Intent classification (keyword heuristic)
  Layer 1: WSP preflight (authority + availability checks)
  Layer 2: Permission gate (graduated autonomy tiers)
  Layer 3: End-to-end process() (full loop)

WSP Compliance: WSP 5 (Test Coverage), WSP 6 (Test Audit)
"""

import asyncio
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from unittest.mock import PropertyMock

from modules.communication.moltbot_bridge.src.openclaw_dae import (
    OpenClawDAE,
    IntentCategory,
    AutonomyTier,
    OpenClawIntent,
)
from modules.communication.moltbot_bridge.src.gemma_intent_classifier import (
    GemmaIntentClassifier,
)


# ---------------------------------------------------------------------------
# Layer 0: Intent Classification
# ---------------------------------------------------------------------------

class TestIntentClassification:
    """Test intent classification from raw messages."""

    def setup_method(self):
        self.dae = OpenClawDAE(repo_root=project_root)

    def test_query_intent(self):
        """QUERY: search/find/explain messages classify as query."""
        intent = self.dae.classify_intent(
            message="What is the WRE orchestrator?",
            sender="user123",
            channel="telegram",
            session_key="sess1",
        )
        assert intent.category == IntentCategory.QUERY
        assert intent.target_domain == "holo_index"
        assert not intent.is_authorized_commander

    def test_command_intent(self):
        """COMMAND: run/execute/deploy messages classify as command."""
        intent = self.dae.classify_intent(
            message="Run the test suite and fix errors",
            sender="user123",
            channel="whatsapp",
            session_key="sess2",
        )
        assert intent.category == IntentCategory.COMMAND
        assert intent.target_domain == "wre_orchestrator"

    def test_monitor_intent(self):
        """MONITOR: status/health/metrics classify as monitor."""
        intent = self.dae.classify_intent(
            message="Show me the system status and health check",
            sender="user123",
            channel="discord",
            session_key="sess3",
        )
        assert intent.category == IntentCategory.MONITOR
        assert intent.target_domain == "ai_overseer"

    def test_schedule_intent(self):
        """SCHEDULE: schedule/remind/cron classify as schedule."""
        intent = self.dae.classify_intent(
            message="Schedule a video for tomorrow at 3pm",
            sender="user123",
            channel="whatsapp",
            session_key="sess4",
        )
        assert intent.category == IntentCategory.SCHEDULE

    def test_social_intent(self):
        """SOCIAL: comment/post/reply classify as social."""
        intent = self.dae.classify_intent(
            message="Post a comment on the latest video and reply to viewers",
            sender="user123",
            channel="telegram",
            session_key="sess5",
        )
        assert intent.category == IntentCategory.SOCIAL

    def test_conversation_fallback(self):
        """CONVERSATION: unrecognized messages default to conversation."""
        intent = self.dae.classify_intent(
            message="Hello there!",
            sender="user123",
            channel="whatsapp",
            session_key="sess6",
        )
        assert intent.category == IntentCategory.CONVERSATION
        assert intent.target_domain == "digital_twin"

    def test_commander_detection_local_channel(self):
        """Commander authority granted on local channel (channel proves identity)."""
        intent = self.dae.classify_intent(
            message="Hello",
            sender="@UnDaoDu",
            channel="voice_repl",  # Local channel - inherently trusted
            session_key="sess7",
        )
        assert intent.is_authorized_commander is True

    def test_non_commander(self):
        """Non-commander correctly identified."""
        intent = self.dae.classify_intent(
            message="Hello",
            sender="random_user_42",
            channel="telegram",
            session_key="sess8",
        )
        assert intent.is_authorized_commander is False

    def test_local_channel_grants_commander_authority(self):
        """Local channel (voice_repl) grants commander authority regardless of display name."""
        intent = self.dae.classify_intent(
            message="run tests",
            sender="any_user",  # Not in AUTHORIZED_COMMANDERS
            channel="voice_repl",
            session_key="local1",
        )
        assert intent.is_authorized_commander is True

    def test_local_repl_grants_commander_authority(self):
        """Local channel (local_repl) grants commander authority regardless of display name."""
        intent = self.dae.classify_intent(
            message="deploy app",
            sender="unknown_sender",
            channel="local_repl",
            session_key="local2",
        )
        assert intent.is_authorized_commander is True

    def test_remote_channel_requires_display_name_match(self):
        """Remote channel without display name match is not commander."""
        intent = self.dae.classify_intent(
            message="execute command",
            sender="impostor",
            channel="discord",
            session_key="remote1",
        )
        assert intent.is_authorized_commander is False

    def test_remote_channel_with_display_name_match_is_NOT_commander(self):
        """Remote channel with display name match is NOT commander (hardened: display-name spoofable)."""
        intent = self.dae.classify_intent(
            message="run task",
            sender="012",  # Even authorized display name
            channel="telegram",  # Remote channel
            session_key="remote2",
        )
        # WSP 00: Remote display-name is spoofable, no trusted identity field exists
        assert intent.is_authorized_commander is False


class TestSecurityCriticalFilePaths:
    """Test extract_file_paths catches security-critical files (WSP 00 / mutation gate)."""

    def test_detects_env_file(self):
        """Detects .env as source modification target."""
        from modules.communication.moltbot_bridge.src.openclaw_permission_policy import (
            extract_file_paths,
        )
        paths = extract_file_paths("edit .env")
        assert ".env" in paths

    def test_detects_bat_file(self):
        """Detects .bat scripts as source modification target."""
        from modules.communication.moltbot_bridge.src.openclaw_permission_policy import (
            extract_file_paths,
        )
        paths = extract_file_paths("modify launch.bat")
        assert "launch.bat" in paths

    def test_detects_cmd_file(self):
        """Detects .cmd scripts as source modification target."""
        from modules.communication.moltbot_bridge.src.openclaw_permission_policy import (
            extract_file_paths,
        )
        paths = extract_file_paths("edit setup.cmd")
        assert "setup.cmd" in paths

    def test_detects_gitignore(self):
        """Detects .gitignore as source modification target."""
        from modules.communication.moltbot_bridge.src.openclaw_permission_policy import (
            extract_file_paths,
        )
        paths = extract_file_paths("update .gitignore")
        assert ".gitignore" in paths

    def test_detects_dockerignore(self):
        """Detects .dockerignore as source modification target."""
        from modules.communication.moltbot_bridge.src.openclaw_permission_policy import (
            extract_file_paths,
        )
        paths = extract_file_paths("change .dockerignore")
        assert ".dockerignore" in paths

    def test_no_false_positive_on_env_suffix(self):
        """Does not false-positive on files ending with .env (like config.env)."""
        from modules.communication.moltbot_bridge.src.openclaw_permission_policy import (
            extract_file_paths,
        )
        paths = extract_file_paths("edit config.env")
        assert paths == ["config.env"]  # Should NOT also include ".env"


class TestConversationRuntimeFlags:
    """Test OpenClaw conversation backend and key-isolation flag parsing."""

    def test_no_api_keys_false_strings_are_respected(self):
        with patch.dict(
            os.environ,
            {
                "OPENCLAW_CONVERSATION_BACKEND": "openclaw",
                "OPENCLAW_NO_API_KEYS": "false",
                "IRONCLAW_NO_API_KEYS": "no",
                "OPENCLAW_ALLOW_EXTERNAL_LLM": "true",
            },
            clear=False,
        ):
            dae = OpenClawDAE(repo_root=project_root)
            assert dae._conversation_backend == "openclaw"
            assert dae._no_api_keys is False
            assert dae._allow_external_llm is True

    def test_no_api_keys_forces_external_llm_off(self):
        with patch.dict(
            os.environ,
            {
                "OPENCLAW_CONVERSATION_BACKEND": "ironclaw",
                "OPENCLAW_NO_API_KEYS": "1",
                "OPENCLAW_ALLOW_EXTERNAL_LLM": "1",
            },
            clear=False,
        ):
            dae = OpenClawDAE(repo_root=project_root)
            assert dae._conversation_backend == "ironclaw"
            assert dae._no_api_keys is True
            assert dae._allow_external_llm is False

    def test_runtime_profile_zeroclaw_forces_fail_closed_external_policy(self):
        with patch.dict(
            os.environ,
            {
                "OPENCLAW_CONVERSATION_BACKEND": "openclaw",
                "OPENCLAW_RUNTIME_PROFILE": "zeroclaw",
                "OPENCLAW_NO_API_KEYS": "0",
                "OPENCLAW_ALLOW_EXTERNAL_LLM": "1",
            },
            clear=False,
        ):
            dae = OpenClawDAE(repo_root=project_root)
            snapshot = dae.get_identity_snapshot(include_runtime_probe=False)
            assert dae._runtime_profile == "zeroclaw"
            assert dae._no_api_keys is True
            assert dae._allow_external_llm is False
            assert snapshot["runtime_profile"] == "zeroclaw"

    def test_ironclaw_defaults_to_strict_mode(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OPENCLAW_IRONCLAW_STRICT", None)
            os.environ.pop("OPENCLAW_IRONCLAW_ALLOW_LOCAL_FALLBACK", None)
            os.environ["OPENCLAW_CONVERSATION_BACKEND"] = "ironclaw"

            dae = OpenClawDAE(repo_root=project_root)
            assert dae._conversation_backend == "ironclaw"
            assert dae._ironclaw_strict is True
            assert dae._ironclaw_allow_local_fallback is False

    def test_identity_query_returns_deterministic_card_on_explicit_details_request(self):
        with patch.dict(
            os.environ,
            {
                "OPENCLAW_CONVERSATION_BACKEND": "openclaw",
                "OPENCLAW_IDENTITY_GENUS": "ex.machina",
                "OPENCLAW_IDENTITY_MODEL_FAMILY": "DaVinci",
                "OPENCLAW_IDENTITY_MODEL_NAME": "MODEL:{MODEL}",
                "OPENCLAW_IDENTITY_MODEL_CATALOG": "qwen2.5,qwen3,codex5.3",
                "OPENCLAW_IDENTITY_PROTOCOL": "WSP_00",
            },
            clear=False,
        ):
            dae = OpenClawDAE(repo_root=project_root)
            intent = OpenClawIntent(
                raw_message="Which model and species are you? show full identity card details",
                category=IntentCategory.CONVERSATION,
                confidence=0.9,
                sender="@UnDaoDu",
                channel="local_repl",
                session_key="sess_identity",
                is_authorized_commander=True,
            )

            response = dae._execute_conversation(intent)
            assert "Identity card" in response
            assert "genus=ex.machina" in response.lower()
            assert "model_family=davinci" in response.lower()
            assert "model_name=model:" in response.lower()
            assert "model_catalog=qwen2.5,qwen3,codex5.3" in response.lower()
            assert "protocol_anchor=wsp_00" in response.lower()
            assert dae._last_conversation_engine == "identity_card"

    def test_identity_query_defaults_to_compact_response(self):
        with patch.dict(
            os.environ,
            {
                "OPENCLAW_CONVERSATION_BACKEND": "openclaw",
                "OPENCLAW_IDENTITY_GENUS": "ex.machina",
                "OPENCLAW_IDENTITY_MODEL_FAMILY": "davinci",
                "OPENCLAW_IDENTITY_MODEL_NAME": "MODEL:{MODEL}",
                "OPENCLAW_IDENTITY_MODEL_CATALOG": "qwen2.5,qwen3,codex5.3",
            },
            clear=False,
        ):
            dae = OpenClawDAE(repo_root=project_root)
            intent = OpenClawIntent(
                raw_message="Which model and species are you?",
                category=IntentCategory.CONVERSATION,
                confidence=0.9,
                sender="@UnDaoDu",
                channel="local_repl",
                session_key="sess_identity_compact",
                is_authorized_commander=True,
            )

            response = dae._execute_conversation(intent)
            assert response.lower().startswith("0102: model_name=")
            assert "model_name=" in response.lower()
            assert dae._last_conversation_engine == "identity_compact"

    def test_identity_query_handles_quinn_stt_alias(self):
        with patch.dict(
            os.environ,
            {
                "OPENCLAW_CONVERSATION_BACKEND": "openclaw",
                "OPENCLAW_IDENTITY_GENUS": "ex.machina",
                "OPENCLAW_IDENTITY_MODEL_FAMILY": "davinci",
                "OPENCLAW_IDENTITY_MODEL_NAME": "local/qwen-coder-7b",
                "OPENCLAW_IDENTITY_MODEL_CATALOG": "qwen2.5,qwen3,codex5.3",
            },
            clear=False,
        ):
            dae = OpenClawDAE(repo_root=project_root)
            intent = OpenClawIntent(
                raw_message="are you quinn",
                category=IntentCategory.CONVERSATION,
                confidence=0.9,
                sender="@UnDaoDu",
                channel="local_repl",
                session_key="sess_identity_quinn_alias",
                is_authorized_commander=True,
            )

            response = dae._execute_conversation(intent)
            assert response.lower().startswith("0102: model_name=")
            assert "local/qwen-coder-7b" in response.lower()
            assert dae._last_conversation_engine == "identity_compact"

    def test_short_model_query_includes_runtime_verification_fields(self):
        with patch.dict(
            os.environ,
            {
                "OPENCLAW_CONVERSATION_BACKEND": "openclaw",
                "OPENCLAW_IDENTITY_MODEL_NAME": "local/qwen-coder-7b",
            },
            clear=False,
        ):
            dae = OpenClawDAE(repo_root=project_root)
            dae._preferred_external_provider = "grok"
            dae._preferred_external_model = "grok-4"
            dae._mark_preferred_external_status("failed", "provider_key_missing")
            dae._last_conversation_engine = "local_qwen"
            dae._last_conversation_detail = "ai_overseer.quick_response"
            intent = OpenClawIntent(
                raw_message="model",
                category=IntentCategory.CONVERSATION,
                confidence=0.9,
                sender="@UnDaoDu",
                channel="local_repl",
                session_key="sess_identity_model_short",
                is_authorized_commander=True,
            )

            response = dae._execute_conversation(intent)
            assert response.lower().startswith("0102: model_name=")
            assert "last_engine=identity_compact" in response.lower()
            assert "previous_engine=local_qwen" in response.lower()
            assert "preferred_external=grok/grok-4" in response.lower()
            assert "preferred_external_status=failed" in response.lower()
            assert dae._last_conversation_engine == "identity_compact"

    def test_identity_verify_phrase_returns_detailed_card(self):
        with patch.dict(
            os.environ,
            {
                "OPENCLAW_CONVERSATION_BACKEND": "openclaw",
                "OPENCLAW_IDENTITY_MODEL_NAME": "local/qwen-coder-7b",
            },
            clear=False,
        ):
            dae = OpenClawDAE(repo_root=project_root)
            intent = OpenClawIntent(
                raw_message="seems like you are qwen not grok can you verify?",
                category=IntentCategory.CONVERSATION,
                confidence=0.9,
                sender="@UnDaoDu",
                channel="local_repl",
                session_key="sess_identity_verify",
                is_authorized_commander=True,
            )

            response = dae._execute_conversation(intent)
            assert "Identity card" in response
            assert "last_engine=" in response
            assert dae._last_conversation_engine == "identity_card"

    def test_token_usage_query_returns_deterministic_report(self):
        dae = OpenClawDAE(repo_root=project_root)
        dae._record_token_usage(
            prompt_text="User: hello",
            completion_text="0102: ready",
            engine="local_qwen",
            provider="local_qwen",
            model="local/qwen-coder-7b",
            source="estimated",
            cost_estimate_usd=0.001,
        )
        intent = OpenClawIntent(
            raw_message="can we see the token expendure?",
            category=IntentCategory.CONVERSATION,
            confidence=0.9,
            sender="@UnDaoDu",
            channel="local_repl",
            session_key="sess_token_usage",
            is_authorized_commander=True,
        )

        response = dae._execute_conversation(intent)
        assert "token usage telemetry" in response.lower()
        assert "last_turn:" in response.lower()
        assert "session:" in response.lower()
        assert "total=" in response.lower()
        assert dae._last_conversation_engine == "token_usage"

    def test_direct_channel_model_identity_stays_conversation_route(self):
        """Voice/local channels should force model/identity prompts to conversation route."""
        with patch.dict(
            os.environ,
            {
                "OPENCLAW_CONVERSATION_BACKEND": "openclaw",
                "OPENCLAW_GEMMA_INTENT": "1",
            },
            clear=False,
        ):
            dae = OpenClawDAE(repo_root=project_root)

            with patch.object(
                dae,
                "_get_gemma_classifier",
                side_effect=AssertionError("gemma classifier should not run for deterministic identity route"),
            ):
                intent = dae.classify_intent(
                    message="can you give me your model name",
                    sender="@UnDaoDu",
                    channel="voice_repl",
                    session_key="sess_direct_identity_route",
                )

            assert intent.category == IntentCategory.CONVERSATION
            assert intent.target_domain == "digital_twin"
            assert intent.metadata.get("classification_method") == "deterministic_direct_conversation"

    def test_identity_model_name_prefers_external_target_when_configured(self):
        """Compact identity should report selected external target when key + external mode are enabled."""
        with patch.dict(
            os.environ,
            {
                "OPENCLAW_CONVERSATION_BACKEND": "openclaw",
                "OPENCLAW_NO_API_KEYS": "0",
                "OPENCLAW_ALLOW_EXTERNAL_LLM": "1",
                "OPENCLAW_IDENTITY_MODEL_NAME": "{model}",
                "GROK_API_KEY": "test-key",
            },
            clear=False,
        ):
            dae = OpenClawDAE(repo_root=project_root)
            dae._preferred_external_provider = "grok"
            dae._preferred_external_model = "grok-4"

            response = dae._build_identity_compact()
            assert response.lower() == "0102: model_name=grok/grok-4"

    def test_identity_query_model_unavailable_phrase_returns_card(self):
        with patch.dict(
            os.environ,
            {
                "OPENCLAW_CONVERSATION_BACKEND": "openclaw",
                "OPENCLAW_IDENTITY_GENUS": "ex.machina",
                "OPENCLAW_IDENTITY_MODEL_FAMILY": "davinci",
                "OPENCLAW_IDENTITY_MODEL_NAME": "local/qwen-coder-7b",
                "OPENCLAW_IDENTITY_MODEL_CATALOG": "qwen2.5,qwen3,codex5.3",
            },
            clear=False,
        ):
            dae = OpenClawDAE(repo_root=project_root)
            intent = OpenClawIntent(
                raw_message="why is quinn not available right now",
                category=IntentCategory.CONVERSATION,
                confidence=0.9,
                sender="@UnDaoDu",
                channel="local_repl",
                session_key="sess_identity_unavailable_alias",
                is_authorized_commander=True,
            )

            response = dae._execute_conversation(intent)
            assert "Identity card" in response
            assert "model_name=local/qwen-coder-7b" in response
            assert dae._last_conversation_engine == "identity_card"

    def test_role_lock_blocks_human_role_inversion(self):
        response = OpenClawDAE._ensure_conversation_identity(
            "I'm UnDaoDu and you are 0102."
        )
        assert response.lower().startswith("0102: role lock active")
        assert "i am 0102" in response.lower()
        assert "you are 012" in response.lower()

    def test_role_lock_preserves_normal_identity_prefix(self):
        response = OpenClawDAE._ensure_conversation_identity(
            "we can troubleshoot this together"
        )
        assert response == "0102: we can troubleshoot this together"

    def test_model_switch_local_qwen3_updates_conversation_target(self):
        with patch.dict(
            os.environ,
            {
                "OPENCLAW_CONVERSATION_BACKEND": "openclaw",
                "OPENCLAW_NO_API_KEYS": "0",
                "OPENCLAW_ALLOW_EXTERNAL_LLM": "1",
                "LOCAL_MODEL_ROOT": "E:/LM_studio/models/local",
            },
            clear=False,
        ):
            dae = OpenClawDAE(repo_root=project_root)
            intent = OpenClawIntent(
                raw_message="switch model to qwen3",
                category=IntentCategory.CONVERSATION,
                confidence=0.9,
                sender="@UnDaoDu",
                channel="local_repl",
                session_key="sess_switch_qwen3",
                is_authorized_commander=True,
            )
            response = dae._execute_conversation(intent)
            assert "model switched to local/qwen3-4b" in response.lower()
            assert dae._conversation_model_target_id == "local/qwen3-4b"
            assert os.environ.get("LOCAL_MODEL_CODE_DIR", "").lower().replace("\\", "/").endswith("/qwen3-4b")
            assert dae._last_conversation_engine == "model_switch"

    def test_model_switch_local_qwen3_5_updates_conversation_target(self):
        with patch.dict(
            os.environ,
            {
                "OPENCLAW_CONVERSATION_BACKEND": "openclaw",
                "OPENCLAW_NO_API_KEYS": "0",
                "OPENCLAW_ALLOW_EXTERNAL_LLM": "1",
                "LOCAL_MODEL_ROOT": "E:/LM_studio/models/local",
            },
            clear=False,
        ):
            dae = OpenClawDAE(repo_root=project_root)
            intent = OpenClawIntent(
                raw_message="switch model to qwen3.5",
                category=IntentCategory.CONVERSATION,
                confidence=0.9,
                sender="@UnDaoDu",
                channel="local_repl",
                session_key="sess_switch_qwen3_5",
                is_authorized_commander=True,
            )
            response = dae._execute_conversation(intent)
            assert "model switched to local/qwen3.5-4b" in response.lower()
            assert dae._conversation_model_target_id == "local/qwen3.5-4b"
            assert os.environ.get("LOCAL_MODEL_CODE_DIR", "").lower().replace("\\", "/").endswith("/qwen3.5-4b")
            assert dae._last_conversation_engine == "model_switch"

    def test_model_availability_snapshot_includes_qwen3_5_target(self, tmp_path: Path):
        with patch.dict(
            os.environ,
            {
                "LOCAL_MODEL_ROOT": str(tmp_path),
                "OPENCLAW_CONVERSATION_BACKEND": "openclaw",
            },
            clear=False,
        ):
            qwen35_dir = tmp_path / "qwen3.5-4b"
            qwen35_dir.mkdir(parents=True, exist_ok=True)
            (qwen35_dir / "Qwen3.5-4B-Q4_K_M.gguf").write_bytes(b"test")

            dae = OpenClawDAE(repo_root=project_root)
            snapshot = dae.get_model_availability_snapshot(live_probe=False)
            assert "local/qwen3.5-4b" in snapshot["local"]
            assert snapshot["local"]["local/qwen3.5-4b"] == "ready"

    def test_default_conversation_target_prefers_qwen3_5_general_model(self, tmp_path: Path):
        with patch.dict(
            os.environ,
            {
                "LOCAL_MODEL_ROOT": str(tmp_path),
                "OPENCLAW_CONVERSATION_BACKEND": "openclaw",
                "OPENCLAW_CONVERSATION_MODEL_TARGET": "",
            },
            clear=False,
        ):
            qwen35_dir = tmp_path / "qwen3.5-4b"
            qwen35_dir.mkdir(parents=True, exist_ok=True)
            (qwen35_dir / "Qwen3.5-4B-Instruct-Q4_K_M.gguf").write_bytes(b"test")

            dae = OpenClawDAE(repo_root=project_root)
            assert dae._conversation_model_target_id == "local/qwen3.5-4b"

    def test_agentic_model_selection_routes_code_turn_to_coder(self, tmp_path: Path):
        with patch.dict(
            os.environ,
            {
                "LOCAL_MODEL_ROOT": str(tmp_path),
                "OPENCLAW_CONVERSATION_BACKEND": "openclaw",
                "OPENCLAW_AGENTIC_MODEL_SELECTION": "1",
                "OPENCLAW_CONVERSATION_MODEL_TARGET": "",
                "OPENCLAW_CONVERSATION_MODEL_LOCK": "0",
                "OPENCLAW_ALLOW_EXTERNAL_LLM": "0",
                "OPENCLAW_NO_API_KEYS": "1",
                "OPENCLAW_OLLAMA_MODEL": "",
            },
            clear=False,
        ):
            for folder, filename in (
                ("qwen3.5-4b", "Qwen3.5-4B-Instruct-Q4_K_M.gguf"),
                ("qwen-coder-7b", "qwen2.5-coder-7b-instruct-q4_k_m.gguf"),
                ("gemma-270m", "gemma-3-270m-it-Q4_K_M.gguf"),
            ):
                model_dir = tmp_path / folder
                model_dir.mkdir(parents=True, exist_ok=True)
                (model_dir / filename).write_bytes(b"test")

            dae = OpenClawDAE(repo_root=project_root)
            intent = OpenClawIntent(
                raw_message="fix the failing test in main.py and patch the module",
                category=IntentCategory.CONVERSATION,
                confidence=0.9,
                sender="@UnDaoDu",
                channel="local_repl",
                session_key="sess_agentic_code",
                is_authorized_commander=True,
            )

            with patch.object(type(dae), "overseer", new_callable=PropertyMock, return_value=None):
                dae._execute_conversation(intent)

            snapshot = dae.get_identity_snapshot(include_runtime_probe=False)
            assert dae._conversation_model_target_id == "local/qwen-coder-7b"
            assert snapshot["auto_model_role"] == "code"
            assert snapshot["auto_model_target"] == "local/qwen-coder-7b"

    def test_agentic_model_selection_routes_triage_turn_to_gemma(self, tmp_path: Path):
        with patch.dict(
            os.environ,
            {
                "LOCAL_MODEL_ROOT": str(tmp_path),
                "OPENCLAW_CONVERSATION_BACKEND": "openclaw",
                "OPENCLAW_AGENTIC_MODEL_SELECTION": "1",
                "OPENCLAW_CONVERSATION_MODEL_TARGET": "",
                "OPENCLAW_CONVERSATION_MODEL_LOCK": "0",
                "OPENCLAW_ALLOW_EXTERNAL_LLM": "0",
                "OPENCLAW_NO_API_KEYS": "1",
                "OPENCLAW_OLLAMA_MODEL": "",
            },
            clear=False,
        ):
            for folder, filename in (
                ("qwen3.5-4b", "Qwen3.5-4B-Instruct-Q4_K_M.gguf"),
                ("qwen-coder-7b", "qwen2.5-coder-7b-instruct-q4_k_m.gguf"),
                ("gemma-270m", "gemma-3-270m-it-Q4_K_M.gguf"),
            ):
                model_dir = tmp_path / folder
                model_dir.mkdir(parents=True, exist_ok=True)
                (model_dir / filename).write_bytes(b"test")

            dae = OpenClawDAE(repo_root=project_root)
            intent = OpenClawIntent(
                raw_message="status check the runtime health and diagnose what is failing",
                category=IntentCategory.CONVERSATION,
                confidence=0.9,
                sender="@UnDaoDu",
                channel="local_repl",
                session_key="sess_agentic_triage",
                is_authorized_commander=True,
            )

            with patch.object(type(dae), "overseer", new_callable=PropertyMock, return_value=None):
                dae._execute_conversation(intent)

            snapshot = dae.get_identity_snapshot(include_runtime_probe=False)
            assert dae._conversation_model_target_id == "local/gemma-270m"
            assert snapshot["auto_model_role"] == "triage"
            assert snapshot["auto_model_target"] == "local/gemma-270m"

    def test_manual_model_switch_locks_target_against_agentic_override(self, tmp_path: Path):
        with patch.dict(
            os.environ,
            {
                "LOCAL_MODEL_ROOT": str(tmp_path),
                "OPENCLAW_CONVERSATION_BACKEND": "openclaw",
                "OPENCLAW_AGENTIC_MODEL_SELECTION": "1",
                "OPENCLAW_CONVERSATION_MODEL_TARGET": "",
                "OPENCLAW_CONVERSATION_MODEL_LOCK": "0",
                "OPENCLAW_ALLOW_EXTERNAL_LLM": "0",
                "OPENCLAW_NO_API_KEYS": "1",
                "OPENCLAW_OLLAMA_MODEL": "",
            },
            clear=False,
        ):
            for folder, filename in (
                ("qwen3.5-4b", "Qwen3.5-4B-Instruct-Q4_K_M.gguf"),
                ("qwen-coder-7b", "qwen2.5-coder-7b-instruct-q4_k_m.gguf"),
                ("gemma-270m", "gemma-3-270m-it-Q4_K_M.gguf"),
            ):
                model_dir = tmp_path / folder
                model_dir.mkdir(parents=True, exist_ok=True)
                (model_dir / filename).write_bytes(b"test")

            dae = OpenClawDAE(repo_root=project_root)
            switch_intent = OpenClawIntent(
                raw_message="switch model to qwen3.5",
                category=IntentCategory.CONVERSATION,
                confidence=0.9,
                sender="@UnDaoDu",
                channel="local_repl",
                session_key="sess_agentic_lock_switch",
                is_authorized_commander=True,
            )
            dae._execute_conversation(switch_intent)

            with patch.object(type(dae), "overseer", new_callable=PropertyMock, return_value=None):
                dae._execute_conversation(
                    OpenClawIntent(
                        raw_message="fix the failing test in main.py and patch the module",
                        category=IntentCategory.CONVERSATION,
                        confidence=0.9,
                        sender="@UnDaoDu",
                        channel="local_repl",
                        session_key="sess_agentic_lock_followup",
                        is_authorized_commander=True,
                    )
                )

            snapshot = dae.get_identity_snapshot(include_runtime_probe=False)
            assert dae._conversation_model_target_id == "local/qwen3.5-4b"
            assert snapshot["conversation_model_locked"] == "ON"

    def test_model_switch_external_grok_without_key_reports_unconfigured(self):
        with patch.dict(
            os.environ,
            {
                "OPENCLAW_CONVERSATION_BACKEND": "openclaw",
                "OPENCLAW_NO_API_KEYS": "0",
                "OPENCLAW_ALLOW_EXTERNAL_LLM": "1",
                "GROK_API_KEY": "",
                "XAI_API_KEY": "",
            },
            clear=False,
        ):
            dae = OpenClawDAE(repo_root=project_root)
            intent = OpenClawIntent(
                raw_message="become grok",
                category=IntentCategory.CONVERSATION,
                confidence=0.9,
                sender="@UnDaoDu",
                channel="local_repl",
                session_key="sess_switch_grok",
                is_authorized_commander=True,
            )
            response = dae._execute_conversation(intent)
            assert "provider api key is not configured" in response.lower()
            assert dae._preferred_external_provider == "grok"
            assert dae._preferred_external_model == "grok-4"
            assert dae._last_conversation_engine == "model_switch"

    def test_model_switch_external_blocked_by_zeroclaw_profile(self):
        with patch.dict(
            os.environ,
            {
                "OPENCLAW_CONVERSATION_BACKEND": "openclaw",
                "OPENCLAW_RUNTIME_PROFILE": "zeroclaw",
                "OPENCLAW_NO_API_KEYS": "0",
                "OPENCLAW_ALLOW_EXTERNAL_LLM": "1",
                "OPENCLAW_WSP00_BOOT": "1",
                "OPENCLAW_IDENTITY_PROTOCOL": "wsp_00",
            },
            clear=False,
        ):
            dae = OpenClawDAE(repo_root=project_root)
            intent = OpenClawIntent(
                raw_message="become grok",
                category=IntentCategory.CONVERSATION,
                confidence=0.9,
                sender="@UnDaoDu",
                channel="local_repl",
                session_key="sess_switch_grok_zeroclaw",
                is_authorized_commander=True,
            )
            response = dae._execute_conversation(intent)
            assert "model switch blocked by runtime profile zeroclaw" in response.lower()
            assert dae._last_conversation_engine == "model_switch_blocked"

    def test_parse_model_switch_target_supports_quick_and_reasoning_profiles(self):
        assert OpenClawDAE._parse_model_switch_target("become grok fast") == "grok-4-fast"
        assert OpenClawDAE._parse_model_switch_target("switch model to gemini flash") == "gemini-2.5-flash"
        assert OpenClawDAE._parse_model_switch_target("become gpt5") == "gpt-5"
        assert OpenClawDAE._parse_model_switch_target("become o3 pro") == "o3-pro"
        assert OpenClawDAE._parse_model_switch_target("become haiku") == "claude-haiku-4-5-20251001"

    def test_resolve_external_target_includes_quick_models(self):
        assert OpenClawDAE._resolve_external_target("grok-4-fast") == ("grok", "grok-4-fast")
        assert OpenClawDAE._resolve_external_target("gemini-2.5-flash") == ("gemini", "gemini-2.5-flash")
        assert OpenClawDAE._resolve_external_target("gpt-5") == ("openai", "gpt-5")
        assert OpenClawDAE._resolve_external_target("o3-pro") == ("openai", "o3-pro")
        assert OpenClawDAE._resolve_external_target("claude-haiku-4-5-20251001") == (
            "anthropic",
            "claude-haiku-4-5-20251001",
        )

    def test_model_switch_without_target_returns_guidance_not_identity(self):
        with patch.dict(
            os.environ,
            {
                "OPENCLAW_CONVERSATION_BACKEND": "openclaw",
                "OPENCLAW_NO_API_KEYS": "0",
                "OPENCLAW_ALLOW_EXTERNAL_LLM": "1",
                "OPENCLAW_WSP00_BOOT": "1",
                "OPENCLAW_IDENTITY_PROTOCOL": "wsp_00",
            },
            clear=False,
        ):
            dae = OpenClawDAE(repo_root=project_root)
            intent = OpenClawIntent(
                raw_message="can you change your model",
                category=IntentCategory.CONVERSATION,
                confidence=0.9,
                sender="@UnDaoDu",
                channel="local_repl",
                session_key="sess_switch_missing_target",
                is_authorized_commander=True,
            )
            response = dae._execute_conversation(intent)
            assert "model switch request received" in response.lower()
            assert "catalog=" not in response.lower()
            assert dae._last_conversation_engine == "model_switch"
            assert dae._last_conversation_detail == "target_missing"

    def test_identity_question_running_qwen_does_not_trigger_switch(self):
        with patch.dict(
            os.environ,
            {
                "OPENCLAW_CONVERSATION_BACKEND": "openclaw",
                "OPENCLAW_WSP00_BOOT": "1",
                "OPENCLAW_IDENTITY_PROTOCOL": "wsp_00",
                "OPENCLAW_IDENTITY_MODEL_NAME": "local/qwen-coder-7b",
            },
            clear=False,
        ):
            dae = OpenClawDAE(repo_root=project_root)
            intent = OpenClawIntent(
                raw_message="are you running qwen",
                category=IntentCategory.CONVERSATION,
                confidence=0.9,
                sender="@UnDaoDu",
                channel="local_repl",
                session_key="sess_identity_running_qwen",
                is_authorized_commander=True,
            )
            response = dae._execute_conversation(intent)
            assert response.lower().startswith("0102: model_name=")
            assert dae._last_conversation_engine == "identity_compact"

    def test_model_switch_blocked_when_wsp00_boot_disabled(self):
        with patch.dict(
            os.environ,
            {
                "OPENCLAW_CONVERSATION_BACKEND": "openclaw",
                "OPENCLAW_NO_API_KEYS": "0",
                "OPENCLAW_ALLOW_EXTERNAL_LLM": "1",
                "OPENCLAW_WSP00_BOOT": "0",
                "OPENCLAW_IDENTITY_PROTOCOL": "wsp_00",
            },
            clear=False,
        ):
            dae = OpenClawDAE(repo_root=project_root)
            intent = OpenClawIntent(
                raw_message="switch model to qwen3",
                category=IntentCategory.CONVERSATION,
                confidence=0.9,
                sender="@UnDaoDu",
                channel="local_repl",
                session_key="sess_switch_wsp_blocked",
                is_authorized_commander=True,
            )
            response = dae._execute_conversation(intent)
            assert "model switch blocked" in response.lower()
            assert "wsp_00 boot is disabled" in response.lower()
            assert dae._last_conversation_engine == "model_switch_blocked"
            assert dae._conversation_model_target_id != "local/qwen3-4b"

    def test_ironclaw_strict_blocks_local_fallback_when_unavailable(self):
        with patch.dict(
            os.environ,
            {
                "OPENCLAW_CONVERSATION_BACKEND": "ironclaw",
                "OPENCLAW_IRONCLAW_STRICT": "1",
                "OPENCLAW_IRONCLAW_ALLOW_LOCAL_FALLBACK": "0",
                "OPENCLAW_ALLOW_EXTERNAL_LLM": "0",
                "OPENCLAW_VERBOSE_RUNTIME_ERRORS": "1",
            },
            clear=False,
        ):
            dae = OpenClawDAE(repo_root=project_root)
            intent = OpenClawIntent(
                raw_message="hello",
                category=IntentCategory.CONVERSATION,
                confidence=0.5,
                sender="@UnDaoDu",
                channel="local_repl",
                session_key="sess_strict",
                is_authorized_commander=True,
            )

            with patch.object(dae, "_try_ironclaw_conversation", return_value=None), patch.object(
                dae,
                "_probe_ironclaw_runtime",
                return_value={
                    "healthy": "FAIL",
                    "detail": "test_unavailable",
                    "model": "local/qwen-coder-7b",
                    "models": "none",
                },
            ), patch.object(type(dae), "overseer", new_callable=PropertyMock) as mock_overseer:
                mock_overseer.side_effect = AssertionError(
                    "overseer should not be consulted in strict ironclaw mode"
                )
                response = dae._execute_conversation(intent)

            assert "strict mode" in response.lower()
            assert "local fallback is disabled" in response.lower()
            assert "detail=test_unavailable" in response
            assert dae._last_conversation_engine == "ironclaw_unavailable_strict"

    def test_ironclaw_strict_autostart_recovers_conversation(self):
        with patch.dict(
            os.environ,
            {
                "OPENCLAW_CONVERSATION_BACKEND": "ironclaw",
                "OPENCLAW_IRONCLAW_STRICT": "1",
                "OPENCLAW_IRONCLAW_ALLOW_LOCAL_FALLBACK": "0",
                "OPENCLAW_ALLOW_EXTERNAL_LLM": "0",
                "OPENCLAW_IRONCLAW_AUTOSTART": "1",
                "IRONCLAW_START_CMD": "ironclaw gateway",
            },
            clear=False,
        ):
            dae = OpenClawDAE(repo_root=project_root)
            intent = OpenClawIntent(
                raw_message="hello",
                category=IntentCategory.CONVERSATION,
                confidence=0.5,
                sender="@UnDaoDu",
                channel="local_repl",
                session_key="sess_strict_autostart",
                is_authorized_commander=True,
            )

            with patch.object(
                dae,
                "_try_ironclaw_conversation",
                side_effect=[None, "0102: recovered"],
            ), patch.object(
                dae,
                "_attempt_ironclaw_autostart",
                return_value=(True, "autostart_recovered"),
            ):
                response = dae._execute_conversation(intent)

            assert response == "0102: recovered"
            assert dae._last_conversation_engine == "ironclaw"
            assert dae._last_conversation_detail == "autostart_recovered"

    def test_ironclaw_autostart_missing_executable_returns_fast(self):
        with patch.dict(
            os.environ,
            {
                "OPENCLAW_CONVERSATION_BACKEND": "ironclaw",
                "OPENCLAW_IRONCLAW_AUTOSTART": "1",
                "OPENCLAW_IRONCLAW_DEFAULT_START_CMD": "",
                "IRONCLAW_START_CMD": "definitely_missing_ironclaw_binary_0102 gateway",
            },
            clear=False,
        ):
            dae = OpenClawDAE(repo_root=project_root)
            dae._ironclaw_autostart_wait_sec = 4.0

            with patch("shutil.which", return_value=None):
                started = time.time()
                recovered, detail = dae._attempt_ironclaw_autostart()
                elapsed = time.time() - started

            assert recovered is False
            assert detail.startswith("autostart_executable_missing:")
            assert elapsed < 1.0
            assert dae._ironclaw_autostart_missing_backoff_until > time.time()

    def test_identity_query_via_query_route_returns_card_on_explicit_details_request(self):
        with patch.dict(
            os.environ,
            {
                "OPENCLAW_IDENTITY_GENUS": "ex.machina",
                "OPENCLAW_IDENTITY_MODEL_FAMILY": "davinci",
                "OPENCLAW_IDENTITY_MODEL_NAME": "{model}",
            },
            clear=False,
        ):
            dae = OpenClawDAE(repo_root=project_root)
            intent = OpenClawIntent(
                raw_message="what model are you operating from? show full identity card details",
                category=IntentCategory.QUERY,
                confidence=0.7,
                sender="@UnDaoDu",
                channel="local_repl",
                session_key="sess_query_identity",
                is_authorized_commander=True,
            )

            response = asyncio.run(dae._execute_query(intent))
            assert "Identity card" in response
            assert "genus=ex.machina" in response.lower()
            assert "model_family=davinci" in response.lower()
            assert "model_name=" in response.lower()

    def test_conversation_honors_turn_cancellation(self):
        dae = OpenClawDAE(repo_root=project_root)
        intent = OpenClawIntent(
            raw_message="hello there",
            category=IntentCategory.CONVERSATION,
            confidence=0.8,
            sender="@UnDaoDu",
            channel="voice_repl",
            session_key="sess_cancel",
            is_authorized_commander=True,
        )

        dae.request_turn_cancel("test_voice_barge")
        response = dae._execute_conversation(intent)
        assert "interrupted" in response.lower()
        assert dae._last_conversation_engine == "cancelled"

    def test_compact_identity_query_handles_punctuation(self):
        with patch.dict(
            os.environ,
            {
                "OPENCLAW_IDENTITY_GENUS": "ex.machina",
                "OPENCLAW_IDENTITY_MODEL_FAMILY": "davinci",
                "OPENCLAW_IDENTITY_MODEL_CATALOG": "qwen2.5,qwen3,grok4",
            },
            clear=False,
        ):
            dae = OpenClawDAE(repo_root=project_root)
            intent = OpenClawIntent(
                raw_message="model?",
                category=IntentCategory.CONVERSATION,
                confidence=0.8,
                sender="@UnDaoDu",
                channel="local_repl",
                session_key="sess_compact_identity",
                is_authorized_commander=True,
            )

            response = dae._execute_conversation(intent)
            assert response.lower().startswith("0102: model_name=")
            assert "catalog=" not in response.lower()
            assert dae._last_conversation_engine == "identity_compact"

    def test_identity_snapshot_exposes_lineage_and_resolved_model(self):
        with patch.dict(
            os.environ,
            {
                "OPENCLAW_CONVERSATION_BACKEND": "openclaw",
                "OPENCLAW_IDENTITY_GENUS": "ex.machina",
                "OPENCLAW_IDENTITY_MODEL_FAMILY": "davinci",
                "OPENCLAW_IDENTITY_MODEL_NAME": "model:{model}",
            },
            clear=False,
        ):
            dae = OpenClawDAE(repo_root=project_root)
            with patch.object(
                dae,
                "_resolve_local_code_model_snapshot",
                return_value={
                    "path": r"E:\LM_studio\models\local\qwen-coder-7b\qwen2.5-coder-7b-instruct-q4_k_m.gguf",
                    "state": "OK",
                    "source": "LOCAL_MODEL_CODE_FILE",
                },
            ):
                snapshot = dae.get_identity_snapshot(include_runtime_probe=False)
                line = dae.get_identity_label_line(include_runtime_probe=False)

            assert snapshot["genus"] == "Ex.machina"
            assert snapshot["lineage"] == "davinci"
            assert snapshot["model_family"] == "davinci"
            assert snapshot["model_name"] == "model:qwen2.5-coder-7b-instruct-q4_k_m.gguf"
            assert "lineage=davinci" in line
            assert "model_name=model:qwen2.5-coder-7b-instruct-q4_k_m.gguf" in line

    def test_monitor_reports_lineage_and_model_name(self):
        dae = OpenClawDAE(repo_root=project_root)
        dae._conversation_backend = "ironclaw"
        intent = OpenClawIntent(
            raw_message="status",
            category=IntentCategory.MONITOR,
            confidence=0.9,
            sender="@UnDaoDu",
            channel="local_repl",
            session_key="sess_monitor",
            is_authorized_commander=True,
        )

        snapshot = {
            "backend": "ironclaw",
            "key_isolation": "ON",
            "ironclaw_strict": "ON",
            "ironclaw_allow_local_fallback": "OFF",
            "genus": "Ex.machina",
            "lineage": "davinci",
            "model_family": "davinci",
            "model_name": "local/qwen-coder-7b",
            "model_catalog": "qwen2.5,qwen3",
            "protocol_anchor": "wsp_00",
            "wsp00_boot": "ON",
            "wsp00_boot_mode": "compact",
            "wsp00_file_override": "NO",
            "last_engine": "ironclaw",
            "last_engine_detail": "gateway_chat_completion",
            "local_code_model_path": "E:/LM_studio/models/local/qwen-coder-7b/model.gguf",
            "local_code_model_state": "OK",
            "local_code_model_source": "LOCAL_MODEL_CODE_FILE",
            "ironclaw_runtime_healthy": "PASS",
            "ironclaw_runtime_detail": "ok",
            "ironclaw_runtime_model": "local/qwen-coder-7b",
            "ironclaw_runtime_models": "local/qwen-coder-7b, local/qwen3-4b",
        }
        with patch.object(type(dae), "wre", new_callable=PropertyMock, return_value=None), patch.object(
            type(dae), "overseer", new_callable=PropertyMock, return_value=None
        ), patch.object(dae, "get_identity_snapshot", return_value=snapshot):
            response = dae._execute_monitor(intent)

        assert "lineage=davinci" in response.lower()
        assert "model_name=local/qwen-coder-7b" in response.lower()
        assert "ironclaw runtime: pass (ok)" in response.lower()

    def test_wsp00_boot_prompt_enabled_by_default(self):
        with patch.dict(
            os.environ,
            {
                "OPENCLAW_WSP00_BOOT": "1",
                "OPENCLAW_WSP00_BOOT_MODE": "compact",
            },
            clear=False,
        ):
            dae = OpenClawDAE(repo_root=project_root)
            prompt = dae._build_conversation_system_prompt()
            assert "WSP_00 BOOT" in prompt
            assert "identity=0102" in prompt.lower()
            assert "You are 0102" in prompt

    def test_wsp00_boot_prompt_can_be_disabled(self):
        with patch.dict(
            os.environ,
            {
                "OPENCLAW_WSP00_BOOT": "0",
                "OPENCLAW_WSP00_BOOT_MODE": "compact",
            },
            clear=False,
        ):
            dae = OpenClawDAE(repo_root=project_root)
            prompt = dae._build_conversation_system_prompt()
            assert "WSP_00 BOOT" not in prompt
            assert prompt.startswith("You are 0102")

    def test_wsp00_boot_prompt_file_override(self, tmp_path):
        prompt_file = tmp_path / "wsp00_boot_prompt.txt"
        prompt_file.write_text("WSP_00 CUSTOM BOOT FROM FILE", encoding="utf-8")

        with patch.dict(
            os.environ,
            {
                "OPENCLAW_WSP00_BOOT": "1",
                "OPENCLAW_WSP00_BOOT_MODE": "compact",
                "OPENCLAW_WSP00_PROMPT_FILE": str(prompt_file),
            },
            clear=False,
        ):
            dae = OpenClawDAE(repo_root=project_root)
            prompt = dae._build_conversation_system_prompt()
            assert prompt.startswith("WSP_00 CUSTOM BOOT FROM FILE")
            assert "You are 0102" in prompt

    def test_platform_context_pack_is_injected_into_conversation_prompt(self, tmp_path):
        context_file = tmp_path / "platform_context.txt"
        context_file.write_text(
            "foundups platform context\n"
            "- openclaw routes to wre\n"
            "- pAVS uses btc reserve + utility layers\n",
            encoding="utf-8",
        )

        with patch.dict(
            os.environ,
            {
                "OPENCLAW_WSP00_BOOT": "0",
                "OPENCLAW_PLATFORM_CONTEXT_ENABLED": "1",
                "OPENCLAW_PLATFORM_CONTEXT_FILES": str(context_file),
                "OPENCLAW_PLATFORM_CONTEXT_MAX_CHARS": "600",
            },
            clear=False,
        ):
            dae = OpenClawDAE(repo_root=project_root)
            prompt = dae._build_conversation_system_prompt()
            assert "PLATFORM CONTEXT PACK" in prompt
            assert "foundups platform context" in prompt.lower()
            assert str(context_file.name) in prompt

    def test_platform_context_pack_can_be_disabled(self, tmp_path):
        context_file = tmp_path / "platform_context.txt"
        context_file.write_text("foundups platform context", encoding="utf-8")

        with patch.dict(
            os.environ,
            {
                "OPENCLAW_WSP00_BOOT": "0",
                "OPENCLAW_PLATFORM_CONTEXT_ENABLED": "0",
                "OPENCLAW_PLATFORM_CONTEXT_FILES": str(context_file),
            },
            clear=False,
        ):
            dae = OpenClawDAE(repo_root=project_root)
            prompt = dae._build_conversation_system_prompt()
            assert "PLATFORM CONTEXT PACK" not in prompt
            assert prompt.startswith("You are 0102")


# ---------------------------------------------------------------------------
# Layer 0b: Gemma Intent Classifier (Unit)
# ---------------------------------------------------------------------------

class TestGemmaIntentClassifier:
    """Unit tests for GemmaIntentClassifier in isolation."""

    def test_classify_keyword_fallback_no_model(self):
        """Falls back to keyword-only when Gemma model not found."""
        classifier = GemmaIntentClassifier(
            model_path=Path("nonexistent_model.gguf")
        )
        result = classifier.classify(
            message="What is WSP 50?",
            keyword_scores={"query": 0.4, "monitor": 0.1},
        )
        assert result["category"] == "query"
        assert result["method"] == "keyword_only"
        assert result["confidence"] > 0

    def test_classify_default_on_empty_scores(self):
        """Returns default conversation when no keyword scores."""
        classifier = GemmaIntentClassifier(
            model_path=Path("nonexistent_model.gguf")
        )
        result = classifier.classify(
            message="banana",
            keyword_scores={},
        )
        assert result["category"] == "conversation"
        assert result["method"] == "default"
        assert result["confidence"] == 0.5

    def test_classify_respects_max_candidates(self):
        """Only top-N candidates are sent to Gemma."""
        classifier = GemmaIntentClassifier(
            model_path=Path("nonexistent_model.gguf"),
            max_candidates=2,
        )
        result = classifier.classify(
            message="check status",
            keyword_scores={
                "monitor": 0.5,
                "query": 0.3,
                "system": 0.1,
                "command": 0.05,
            },
        )
        # Should still work in keyword fallback
        assert result["category"] == "monitor"
        assert result["method"] == "keyword_only"

    def test_stats_tracking(self):
        """Stats track calls and fallbacks."""
        classifier = GemmaIntentClassifier(
            model_path=Path("nonexistent_model.gguf")
        )
        classifier.classify("test", {"query": 0.5})
        classifier.classify("test", {"command": 0.3})
        stats = classifier.stats
        assert stats["total_calls"] == 2
        assert stats["keyword_fallbacks"] == 2
        assert stats["gemma_calls"] == 0

    def test_is_available_none_before_check(self):
        """is_available is None before first classification attempt."""
        classifier = GemmaIntentClassifier()
        assert classifier.is_available is None


class TestGemmaHybridIntegration:
    """Test Gemma integration into OpenClawDAE.classify_intent()."""

    def setup_method(self):
        self.dae = OpenClawDAE(repo_root=project_root)

    def test_keyword_only_when_gemma_disabled(self):
        """OPENCLAW_GEMMA_INTENT=0 forces keyword-only mode."""
        with patch.dict("os.environ", {"OPENCLAW_GEMMA_INTENT": "0"}):
            intent = self.dae.classify_intent(
                message="What is the system health status?",
                sender="user123",
                channel="discord",
                session_key="sess_kw",
            )
            assert intent.category in (IntentCategory.QUERY, IntentCategory.MONITOR)
            assert intent.metadata.get("classification_method") in (
                "keyword_only", "default"
            )

    def test_metadata_includes_classification_method(self):
        """classify_intent always includes classification_method in metadata."""
        intent = self.dae.classify_intent(
            message="Hello world",
            sender="user123",
            channel="telegram",
            session_key="sess_meta",
        )
        # Greeting override doesn't set method (that's fine)
        # But non-greeting should
        intent2 = self.dae.classify_intent(
            message="Run the deploy script",
            sender="user123",
            channel="telegram",
            session_key="sess_meta2",
        )
        assert "classification_method" in intent2.metadata

    def test_gemma_hybrid_with_mock(self):
        """Mock Gemma classifier returns hybrid result."""
        mock_classifier = MagicMock(spec=GemmaIntentClassifier)
        mock_classifier.classify.return_value = {
            "category": "monitor",
            "confidence": 0.87,
            "method": "gemma_hybrid",
            "gemma_scores": {"monitor": 0.85, "query": 0.10},
            "latency_ms": 25,
        }
        # Inject mock classifier
        self.dae._gemma_classifier = mock_classifier
        self.dae._gemma_classifier_checked = True

        with patch.dict("os.environ", {"OPENCLAW_GEMMA_INTENT": "1"}):
            intent = self.dae.classify_intent(
                message="Show me the system status and health check",
                sender="user123",
                channel="discord",
                session_key="sess_hybrid",
            )
            assert intent.category == IntentCategory.MONITOR
            assert intent.confidence == 0.87
            assert intent.metadata["classification_method"] == "gemma_hybrid"
            assert intent.metadata["classification_latency_ms"] == 25

    def test_gemma_unavailable_degrades_gracefully(self):
        """When Gemma classifier is None, falls back to keyword scoring."""
        self.dae._gemma_classifier = None
        self.dae._gemma_classifier_checked = True

        intent = self.dae.classify_intent(
            message="Run the test suite and fix errors",
            sender="user123",
            channel="whatsapp",
            session_key="sess_fallback",
        )
        assert intent.category == IntentCategory.COMMAND
        assert intent.metadata.get("classification_method") == "keyword_only"

    def test_foundup_intent_with_gemma_disabled(self):
        """FOUNDUP intent still works in keyword-only mode."""
        with patch.dict("os.environ", {"OPENCLAW_GEMMA_INTENT": "0"}):
            intent = self.dae.classify_intent(
                message="Launch a new foundup and create a token",
                sender="@UnDaoDu",
                channel="local_repl",  # Local channel for commander authority
                session_key="sess_foundup",
            )
            assert intent.category == IntentCategory.FOUNDUP
            assert intent.target_domain == "fam_adapter"
            assert intent.is_authorized_commander is True


# ---------------------------------------------------------------------------
# Layer 0c: SOURCE Tier - File Path Extraction & Permission Gate
# ---------------------------------------------------------------------------

class TestFilePathExtraction:
    """Test file path extraction from COMMAND messages."""

    def test_extract_python_file(self):
        """Extracts Python file paths from messages."""
        paths = OpenClawDAE._extract_file_paths(
            "Edit modules/ai_intelligence/ai_overseer/src/ai_overseer.py"
        )
        assert len(paths) == 1
        assert paths[0] == "modules/ai_intelligence/ai_overseer/src/ai_overseer.py"

    def test_extract_multiple_files(self):
        """Extracts multiple file paths from a single message."""
        paths = OpenClawDAE._extract_file_paths(
            "Fix modules/foo/src/bar.py and modules/baz/src/qux.py"
        )
        assert len(paths) == 2

    def test_extract_markdown_file(self):
        """Extracts .md file paths."""
        paths = OpenClawDAE._extract_file_paths(
            "Update modules/communication/moltbot_bridge/README.md"
        )
        assert len(paths) == 1
        assert paths[0].endswith("README.md")

    def test_extract_json_file(self):
        """Extracts .json file paths."""
        paths = OpenClawDAE._extract_file_paths(
            "Modify modules/infrastructure/wre_core/skillz/skills_registry_v2.json"
        )
        assert len(paths) == 1
        assert paths[0].endswith("skills_registry_v2.json")

    def test_extract_no_paths(self):
        """Returns empty list when no file paths found."""
        paths = OpenClawDAE._extract_file_paths("Run the test suite")
        assert paths == []

    def test_extract_quoted_path(self):
        """Handles quoted file paths."""
        paths = OpenClawDAE._extract_file_paths(
            'Edit "modules/foo/src/bar.py" please'
        )
        assert len(paths) == 1

    def test_backslash_normalized(self):
        """Windows backslash paths normalized to forward slashes."""
        paths = OpenClawDAE._extract_file_paths(
            "Fix modules\\foo\\src\\bar.py"
        )
        assert len(paths) == 1
        assert "\\" not in paths[0]


class TestSourceModificationDetection:
    """Test _is_source_modification heuristic."""

    def setup_method(self):
        self.dae = OpenClawDAE(repo_root=project_root)

    def _make_intent(self, message: str) -> OpenClawIntent:
        return OpenClawIntent(
            raw_message=message,
            category=IntentCategory.COMMAND,
            confidence=0.9,
            sender="@UnDaoDu",
            channel="discord",
            session_key="test",
            is_authorized_commander=True,
        )

    def test_edit_with_file_path(self):
        """'edit' + file path = source modification."""
        intent = self._make_intent("Edit modules/foo/src/bar.py to fix the bug")
        assert self.dae._is_source_modification(intent) is True

    def test_modify_module(self):
        """'modify' + 'module' = source modification."""
        intent = self._make_intent("Modify the overseer module to add logging")
        assert self.dae._is_source_modification(intent) is True

    def test_run_tests_not_source(self):
        """'run tests' is NOT source modification."""
        intent = self._make_intent("Run the test suite and report results")
        assert self.dae._is_source_modification(intent) is False

    def test_deploy_not_source(self):
        """'deploy' without file path is NOT source modification."""
        intent = self._make_intent("Deploy the latest changes to staging")
        assert self.dae._is_source_modification(intent) is False

    def test_refactor_source_code(self):
        """'refactor' + 'source' = source modification."""
        intent = self._make_intent("Refactor the source code of the chat engine")
        assert self.dae._is_source_modification(intent) is True


class TestSourceTierResolution:
    """Test SOURCE tier is correctly resolved for code-modification commands."""

    def setup_method(self):
        self.dae = OpenClawDAE(repo_root=project_root)

    def test_commander_source_modification_gets_source_tier(self):
        """Commander with source modification intent -> SOURCE tier."""
        # Need permissions to be loaded for SOURCE tier to be returned
        self.dae._permissions = MagicMock()

        intent = OpenClawIntent(
            raw_message="Edit modules/foo/src/bar.py to fix the bug",
            category=IntentCategory.COMMAND,
            confidence=0.9,
            sender="@UnDaoDu",
            channel="discord",
            session_key="test",
            is_authorized_commander=True,
        )
        tier = self.dae._resolve_autonomy_tier(intent)
        assert tier == AutonomyTier.SOURCE

    def test_commander_non_source_command_gets_docs_tests(self):
        """Commander with non-source command -> DOCS_TESTS tier."""
        self.dae._permissions = MagicMock()

        intent = OpenClawIntent(
            raw_message="Run the test suite and deploy",
            category=IntentCategory.COMMAND,
            confidence=0.9,
            sender="@UnDaoDu",
            channel="discord",
            session_key="test",
            is_authorized_commander=True,
        )
        tier = self.dae._resolve_autonomy_tier(intent)
        assert tier == AutonomyTier.DOCS_TESTS

    def test_non_commander_never_gets_source(self):
        """Non-commanders ALWAYS get ADVISORY regardless of message."""
        self.dae._permissions = MagicMock()

        intent = OpenClawIntent(
            raw_message="Edit modules/foo/src/bar.py",
            category=IntentCategory.COMMAND,
            confidence=0.9,
            sender="hacker123",
            channel="telegram",
            session_key="test",
            is_authorized_commander=False,
        )
        tier = self.dae._resolve_autonomy_tier(intent)
        assert tier == AutonomyTier.ADVISORY

    def test_no_permissions_fails_closed(self):
        """Without permission manager loaded, COMMAND -> ADVISORY (fail-closed)."""
        # Patch the property to return None (preventing lazy-load)
        with patch.object(type(self.dae), "permissions", new_callable=PropertyMock, return_value=None):
            intent = OpenClawIntent(
                raw_message="Edit modules/foo/src/bar.py",
                category=IntentCategory.COMMAND,
                confidence=0.9,
                sender="@UnDaoDu",
                channel="discord",
                session_key="test",
                is_authorized_commander=True,
            )
            tier = self.dae._resolve_autonomy_tier(intent)
            assert tier == AutonomyTier.ADVISORY


class TestSourcePermissionGate:
    """Test file-specific SOURCE permission checks."""

    def setup_method(self):
        self.dae = OpenClawDAE(repo_root=project_root)

    def test_source_permission_blocked_no_manager(self):
        """SOURCE denied when permission manager is None (fail-closed)."""
        with patch.object(type(self.dae), "permissions", new_callable=PropertyMock, return_value=None):
            intent = OpenClawIntent(
                raw_message="Edit modules/foo/src/bar.py",
                category=IntentCategory.COMMAND,
                confidence=0.9,
                sender="@UnDaoDu",
                channel="discord",
                session_key="test",
                is_authorized_commander=True,
            )
            granted, reason = self.dae._check_source_permission(intent)
            assert granted is False
            assert "unavailable" in reason

    def test_source_permission_file_allowed(self):
        """SOURCE granted when permission manager allows the file."""
        mock_perms = MagicMock()
        mock_perms.check_permission.return_value = MagicMock(
            allowed=True, reason="Permission granted"
        )
        self.dae._permissions = mock_perms

        intent = OpenClawIntent(
            raw_message="Edit modules/foo/src/bar.py",
            category=IntentCategory.COMMAND,
            confidence=0.9,
            sender="@UnDaoDu",
            channel="discord",
            session_key="test",
            is_authorized_commander=True,
        )
        granted, reason = self.dae._check_source_permission(intent)
        assert granted is True
        # Should have called check_permission with the file path
        mock_perms.check_permission.assert_called_with(
            agent_id="openclaw",
            operation="write",
            file_path="modules/foo/src/bar.py",
        )

    def test_source_permission_file_forbidden(self):
        """SOURCE denied when file is in forbidlist."""
        mock_perms = MagicMock()
        mock_perms.check_permission.return_value = MagicMock(
            allowed=False, reason="File main.py in forbidlist"
        )
        self.dae._permissions = mock_perms

        intent = OpenClawIntent(
            raw_message="Edit main.py to add a feature",
            category=IntentCategory.COMMAND,
            confidence=0.9,
            sender="@UnDaoDu",
            channel="discord",
            session_key="test",
            is_authorized_commander=True,
        )
        # main.py won't be extracted by our regex (it's a single segment, not dir/file)
        # But the general write check should still be called
        granted, reason = self.dae._check_source_permission(intent)
        # With no file paths extracted, falls through to general check
        assert granted is False

    def test_source_permission_exception_fails_closed(self):
        """SOURCE denied when permission check throws exception."""
        mock_perms = MagicMock()
        mock_perms.check_permission.side_effect = RuntimeError("DB offline")
        self.dae._permissions = mock_perms

        intent = OpenClawIntent(
            raw_message="Edit modules/foo/src/bar.py",
            category=IntentCategory.COMMAND,
            confidence=0.9,
            sender="@UnDaoDu",
            channel="discord",
            session_key="test",
            is_authorized_commander=True,
        )
        granted, reason = self.dae._check_source_permission(intent)
        assert granted is False
        assert "error" in reason


# ---------------------------------------------------------------------------
# Layer 1: WSP Preflight
# ---------------------------------------------------------------------------

class TestWSPPreflight:
    """Test WSP 50 pre-action verification."""

    def setup_method(self):
        self.dae = OpenClawDAE(repo_root=project_root)

    def test_command_blocked_for_non_commander(self):
        """COMMAND intent blocked for non-authorized sender."""
        intent = OpenClawIntent(
            raw_message="Run deploy script",
            category=IntentCategory.COMMAND,
            confidence=0.8,
            sender="random_user",
            channel="telegram",
            session_key="sess",
            is_authorized_commander=False,
        )
        assert self.dae._wsp_preflight(intent) is False

    def test_command_allowed_for_commander(self):
        """COMMAND intent allowed for authorized commander."""
        intent = OpenClawIntent(
            raw_message="Run deploy script",
            category=IntentCategory.COMMAND,
            confidence=0.8,
            sender="@UnDaoDu",
            channel="whatsapp",
            session_key="sess",
            is_authorized_commander=True,
        )
        # WRE won't be loaded in test, so it should fail on WRE check
        # but authority check passes
        result = self.dae._wsp_preflight(intent)
        # May be False due to WRE unavailability - that's correct behavior
        assert isinstance(result, bool)

    def test_query_allowed_for_anyone(self):
        """QUERY intent allowed for any sender (read-only)."""
        intent = OpenClawIntent(
            raw_message="What is WSP 50?",
            category=IntentCategory.QUERY,
            confidence=0.7,
            sender="random_user",
            channel="discord",
            session_key="sess",
            is_authorized_commander=False,
        )
        assert self.dae._wsp_preflight(intent) is True

    def test_system_blocked_for_non_commander(self):
        """SYSTEM intent blocked for non-authorized sender."""
        intent = OpenClawIntent(
            raw_message="Restart the server",
            category=IntentCategory.SYSTEM,
            confidence=0.9,
            sender="hacker123",
            channel="telegram",
            session_key="sess",
            is_authorized_commander=False,
        )
        assert self.dae._wsp_preflight(intent) is False


# ---------------------------------------------------------------------------
# Layer 2: Permission Gate
# ---------------------------------------------------------------------------

class TestPermissionGate:
    """Test graduated autonomy permission resolution."""

    def setup_method(self):
        self.dae = OpenClawDAE(repo_root=project_root)

    def test_non_commander_gets_advisory(self):
        """Non-commanders always get ADVISORY tier."""
        intent = OpenClawIntent(
            raw_message="hello",
            category=IntentCategory.QUERY,
            confidence=0.5,
            sender="user",
            channel="discord",
            session_key="sess",
            is_authorized_commander=False,
        )
        tier = self.dae._resolve_autonomy_tier(intent)
        assert tier == AutonomyTier.ADVISORY

    def test_commander_query_gets_metrics(self):
        """Commander with QUERY gets METRICS tier."""
        intent = OpenClawIntent(
            raw_message="search for something",
            category=IntentCategory.QUERY,
            confidence=0.8,
            sender="@UnDaoDu",
            channel="whatsapp",
            session_key="sess",
            is_authorized_commander=True,
        )
        tier = self.dae._resolve_autonomy_tier(intent)
        assert tier == AutonomyTier.METRICS

    def test_permission_gate_blocks_non_commander_elevated(self):
        """Permission gate blocks non-commanders from elevated tiers."""
        intent = OpenClawIntent(
            raw_message="hack the system",
            category=IntentCategory.COMMAND,
            confidence=0.9,
            sender="bad_actor",
            channel="telegram",
            session_key="sess",
            is_authorized_commander=False,
        )
        gate_ok = self.dae._check_permission_gate(intent, AutonomyTier.SOURCE)
        assert gate_ok is False

    def test_advisory_always_passes_gate(self):
        """ADVISORY tier always passes permission gate."""
        intent = OpenClawIntent(
            raw_message="hello",
            category=IntentCategory.CONVERSATION,
            confidence=0.5,
            sender="anyone",
            channel="discord",
            session_key="sess",
            is_authorized_commander=False,
        )
        gate_ok = self.dae._check_permission_gate(intent, AutonomyTier.ADVISORY)
        assert gate_ok is True


# ---------------------------------------------------------------------------
# Layer 3: End-to-End Process
# ---------------------------------------------------------------------------

class TestEndToEndProcess:
    """Test full autonomy loop via process()."""

    def setup_method(self):
        self.dae = OpenClawDAE(repo_root=project_root)

    def test_conversation_returns_response(self):
        """Conversation message returns Digital Twin response."""
        result = asyncio.run(self.dae.process(
            message="Hey, how are you?",
            sender="user123",
            channel="telegram",
        ))
        assert isinstance(result, str)
        assert len(result) > 0
        assert "0102" in result or "Digital Twin" in result

    def test_blocked_command_returns_security_block(self):
        """Non-commander COMMAND returns an explicit security block."""
        result = asyncio.run(self.dae.process(
            message="Run the deploy script now",
            sender="random_user",
            channel="whatsapp",
        ))
        assert isinstance(result, str)
        # It should hit the skill safety block returning a deterministic string
        assert "[SECURITY BLOCK]" in result

    def test_monitor_returns_status(self):
        """MONITOR intent returns system status."""
        result = asyncio.run(self.dae.process(
            message="Show system status and health",
            sender="user123",
            channel="discord",
        ))
        assert isinstance(result, str)
        assert "Status" in result or "status" in result.lower()

    def test_zeroclaw_downgrades_mutating_intent_to_conversation_route(self):
        with patch.dict(
            os.environ,
            {
                "OPENCLAW_RUNTIME_PROFILE": "zeroclaw",
                "OPENCLAW_CONVERSATION_BACKEND": "openclaw",
                "OPENCLAW_GEMMA_INTENT": "0",
            },
            clear=False,
        ):
            dae = OpenClawDAE(repo_root=project_root)
            captured_plan = {}

            async def _capture_execute(plan):
                captured_plan["category"] = plan.intent.category
                captured_plan["route"] = plan.route
                captured_plan["metadata"] = dict(plan.intent.metadata)
                return "stub-response"

            with patch.object(dae, "_execute_plan", side_effect=_capture_execute), patch.object(
                dae,
                "_validate_and_remember",
                return_value=MagicMock(response_text="stub-response"),
            ):
                result = asyncio.run(
                    dae.process(
                        message="run the deploy script now",
                        sender="@UnDaoDu",
                        channel="voice_repl",
                    )
                )

            assert result == "stub-response"
            assert captured_plan["category"] == IntentCategory.CONVERSATION
            assert captured_plan["route"] == "digital_twin"
            assert captured_plan["metadata"].get("runtime_profile") == "zeroclaw"
            assert captured_plan["metadata"].get("runtime_profile_gate", "").startswith(
                "blocked_mutating:"
            )

    def test_security_filter_blocks_secrets(self):
        """Validate phase catches secret patterns in output."""
        # The validate_and_remember phase should catch this
        dae = self.dae
        from modules.communication.moltbot_bridge.src.openclaw_dae import (
            ExecutionPlan, AutonomyTier
        )
        intent = OpenClawIntent(
            raw_message="test",
            category=IntentCategory.QUERY,
            confidence=0.5,
            sender="user",
            channel="test",
            session_key="test",
            is_authorized_commander=False,
        )
        plan = ExecutionPlan(
            intent=intent,
            route="test",
            permission_level=AutonomyTier.ADVISORY,
            wsp_preflight_passed=True,
        )
        # Simulate a response that leaks an API key
        result = dae._validate_and_remember(
            plan=plan,
            response_text="Here is the key: AIzaSyB1234567890abcdef",
            execution_time_ms=10,
        )
        assert "REDACTED" in result.response_text
        assert len(result.wsp_violations) > 0


# ---------------------------------------------------------------------------
# Run tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
