"""Tests for model/provider status authority reconciliation.

Verifies that get_model_availability_snapshot() is the canonical OpenClaw
snapshot builder, callable with or without a DAE instance, and that:
  - local-target map derives from local_target_dirs() in openclaw_model_policy
  - provider key/external-target resolution routes through policy functions
  - startup_refresh_model_status writes the same output shape as runtime
  - the snapshot includes a generated_on timestamp for freshness tracking

WSP Compliance: WSP 5 (test coverage), WSP 6 (test audit)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import sys
project_root = Path(__file__).parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from modules.communication.moltbot_bridge.src.openclaw_model_policy import (
    local_target_dirs,
    provider_has_key,
    resolve_external_target,
)
from modules.communication.moltbot_bridge.src.openclaw_runtime_support import (
    get_model_availability_snapshot,
    probe_provider_endpoint,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_dae(target: str = "local/qwen-coder-7b") -> MagicMock:
    """Minimal DAE mock for availability snapshot tests."""
    dae = MagicMock()
    dae._conversation_model_target_id = target
    # These should NOT be called after the cleanup — but keep them defined
    # so tests can assert they were not called.
    return dae


# ---------------------------------------------------------------------------
# 1. Canonical target map consistency
# ---------------------------------------------------------------------------


class TestLocalTargetDirsCanonical:
    """local_target_dirs() provides the OpenClaw target-ID -> folder map.

    local_model_selection.py is the authority for role->path resolution.
    local_target_dirs() maps OpenClaw target IDs (local/<name>) to folder names
    and must include all role-derived targets plus OpenClaw-specific extras.
    """

    def test_local_target_dirs_returns_all_four_canonical_targets(self):
        """All four local targets must be present in the map."""
        dirs = local_target_dirs()
        assert "local/gemma-270m" in dirs
        assert "local/qwen3-4b" in dirs
        assert "local/qwen3.5-4b" in dirs
        assert "local/qwen-coder-7b" in dirs

    def test_local_target_dirs_folder_names_are_non_empty(self):
        """Every local target must map to a non-empty folder name."""
        for target_id, folder in local_target_dirs().items():
            assert folder, f"Empty folder for {target_id}"


class TestAvailabilitySnapshotUsesCanonicalTargetMap:
    """get_model_availability_snapshot() derives its local map from local_target_dirs()."""

    def test_snapshot_local_keys_match_canonical_target_dirs(self, tmp_path, monkeypatch):
        """local keys in snapshot must equal local_target_dirs() keys exactly."""
        monkeypatch.setenv("LOCAL_MODEL_ROOT", str(tmp_path))
        dae = _make_dae()

        result = get_model_availability_snapshot(dae, live_probe=False)

        canonical_keys = set(local_target_dirs().keys())
        snapshot_keys = set(result["local"].keys())
        assert canonical_keys == snapshot_keys, (
            f"Snapshot local keys {snapshot_keys} != canonical {canonical_keys}. "
            "Adding a target to local_target_dirs() must auto-update the snapshot."
        )

    def test_snapshot_local_keys_stable_under_new_canonical_target(self, tmp_path, monkeypatch):
        """If a new target is added to local_target_dirs(), snapshot reflects it."""
        monkeypatch.setenv("LOCAL_MODEL_ROOT", str(tmp_path))

        extended = dict(local_target_dirs())
        extended["local/test-model-stub"] = "test-model-stub"

        dae = _make_dae("local/test-model-stub")
        with patch(
            "modules.communication.moltbot_bridge.src.openclaw_runtime_support.local_target_dirs",
            return_value=extended,
        ):
            result = get_model_availability_snapshot(dae, live_probe=False)

        assert "local/test-model-stub" in result["local"]

    def test_snapshot_does_not_call_dae_provider_has_key(self, tmp_path, monkeypatch):
        """get_model_availability_snapshot() must NOT call dae._provider_has_key."""
        monkeypatch.setenv("LOCAL_MODEL_ROOT", str(tmp_path))
        dae = _make_dae()

        get_model_availability_snapshot(dae, live_probe=False)

        dae._provider_has_key.assert_not_called()

    def test_snapshot_does_not_call_dae_resolve_external_target(self, tmp_path, monkeypatch):
        """get_model_availability_snapshot() must NOT call dae._resolve_external_target."""
        monkeypatch.setenv("LOCAL_MODEL_ROOT", str(tmp_path))
        dae = _make_dae("local/qwen3-4b")

        get_model_availability_snapshot(dae, live_probe=False)

        dae._resolve_external_target.assert_not_called()

    def test_snapshot_target_status_for_known_local(self, tmp_path, monkeypatch):
        """target_status is 'missing' (not 'unknown') for a recognized local target."""
        monkeypatch.setenv("LOCAL_MODEL_ROOT", str(tmp_path))
        dae = _make_dae("local/qwen3-4b")

        result = get_model_availability_snapshot(dae, live_probe=False)

        # target is in local map — status is 'missing' (dir absent) or 'ready', not 'unknown'
        assert result["target_status"] in {"missing", "ready", "dir_only"}

    def test_snapshot_target_status_unknown_for_unrecognized_target(self, tmp_path, monkeypatch):
        """target_status is 'unknown' when target is not in local or external map."""
        monkeypatch.setenv("LOCAL_MODEL_ROOT", str(tmp_path))
        dae = _make_dae("local/nonexistent-model-xyz")

        result = get_model_availability_snapshot(dae, live_probe=False)

        assert result["target_status"] == "unknown"


# ---------------------------------------------------------------------------
# 2. Provider key detection routes through policy
# ---------------------------------------------------------------------------


class TestProviderKeyPolicyAlignment:
    """provider_has_key() and get_model_availability_snapshot() are consistent."""

    def test_provider_key_no_env_means_no_key(self, monkeypatch):
        """When no API key env vars are set, provider_has_key returns False."""
        for var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GROK_API_KEY", "XAI_API_KEY", "GEMINI_API_KEY"):
            monkeypatch.delenv(var, raising=False)

        assert provider_has_key("openai") is False
        assert provider_has_key("anthropic") is False
        assert provider_has_key("grok") is False
        assert provider_has_key("gemini") is False

    def test_provider_key_present_returns_true(self, monkeypatch):
        """When an API key env var is set, provider_has_key returns True."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")
        assert provider_has_key("anthropic") is True

    def test_snapshot_no_key_shows_no_key_status(self, tmp_path, monkeypatch):
        """When no API keys set, snapshot provider_status shows 'no_key'."""
        monkeypatch.setenv("LOCAL_MODEL_ROOT", str(tmp_path))
        for var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GROK_API_KEY", "XAI_API_KEY", "GEMINI_API_KEY"):
            monkeypatch.delenv(var, raising=False)

        dae = _make_dae()
        result = get_model_availability_snapshot(dae, live_probe=False)

        for provider in ("openai", "anthropic", "grok", "gemini"):
            assert result["providers"][provider] == "no_key", (
                f"{provider} should be 'no_key' when env var absent"
            )

    def test_snapshot_key_present_shows_key_present_status(self, tmp_path, monkeypatch):
        """When API key is set, snapshot shows 'key_present' without live probe."""
        monkeypatch.setenv("LOCAL_MODEL_ROOT", str(tmp_path))
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")

        dae = _make_dae()
        result = get_model_availability_snapshot(dae, live_probe=False)

        assert result["providers"]["anthropic"] == "key_present"


# ---------------------------------------------------------------------------
# 3. External target resolution routes through policy
# ---------------------------------------------------------------------------


class TestExternalTargetPolicyAlignment:
    """resolve_external_target() is the single source for external model mapping."""

    def test_resolve_external_grok_target(self):
        """grok-4 resolves to (grok, grok-4) via policy."""
        result = resolve_external_target("grok-4")
        assert result == ("grok", "grok-4")

    def test_resolve_external_anthropic_opus(self):
        """claude-opus-4-6 resolves to (anthropic, claude-opus-4-6)."""
        result = resolve_external_target("claude-opus-4-6")
        assert result == ("anthropic", "claude-opus-4-6")

    def test_resolve_external_unknown_returns_none(self):
        """Unknown external target returns None."""
        result = resolve_external_target("totally-unknown-model")
        assert result is None

    def test_resolve_external_local_target_returns_none(self):
        """Local target IDs do not resolve as external."""
        result = resolve_external_target("local/qwen-coder-7b")
        assert result is None


# ---------------------------------------------------------------------------
# 4. probe_provider_endpoint uses canonical provider_has_key
# ---------------------------------------------------------------------------


class TestProbeProviderEndpointUsesPolicy:
    """probe_provider_endpoint() must use provider_has_key(), not dae._provider_has_key."""

    def test_probe_returns_no_key_when_key_absent(self, monkeypatch):
        """probe_provider_endpoint returns no_key when provider_has_key() is False."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        dae = MagicMock()

        ok, detail = probe_provider_endpoint(dae, "anthropic")

        assert ok is False
        assert detail == "no_key"
        dae._provider_has_key.assert_not_called()

    def test_probe_does_not_call_dae_provider_has_key(self, monkeypatch):
        """probe_provider_endpoint must NOT call dae._provider_has_key."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        dae = MagicMock()

        probe_provider_endpoint(dae, "openai")

        dae._provider_has_key.assert_not_called()


# ---------------------------------------------------------------------------
# 5. Standalone builder (dae=None) — canonical shape without a DAE instance
# ---------------------------------------------------------------------------


class TestStandaloneSnapshotBuilder:
    """get_model_availability_snapshot(dae=None) is the canonical builder.

    Both startup refresh (run_task.py) and runtime status must produce the same
    top-level output contract via this function.
    """

    _CANONICAL_KEYS = frozenset(
        {"generated_on", "probe_mode", "local_root", "local", "providers", "target", "target_status", "effective_model_name"}
    )

    def test_standalone_returns_without_error(self, tmp_path, monkeypatch):
        """get_model_availability_snapshot(dae=None) must not raise."""
        monkeypatch.setenv("LOCAL_MODEL_ROOT", str(tmp_path))
        result = get_model_availability_snapshot(dae=None, live_probe=False)
        assert isinstance(result, dict)

    def test_standalone_has_canonical_keys(self, tmp_path, monkeypatch):
        """Standalone call returns all canonical snapshot keys."""
        monkeypatch.setenv("LOCAL_MODEL_ROOT", str(tmp_path))
        result = get_model_availability_snapshot(dae=None, live_probe=False)
        missing = self._CANONICAL_KEYS - set(result.keys())
        assert not missing, f"Missing canonical keys: {missing}"

    def test_standalone_has_generated_on_timestamp(self, tmp_path, monkeypatch):
        """Snapshot must include generated_on ISO timestamp for freshness tracking."""
        monkeypatch.setenv("LOCAL_MODEL_ROOT", str(tmp_path))
        result = get_model_availability_snapshot(dae=None, live_probe=False)
        assert result["generated_on"], "generated_on must be non-empty"
        # Must be parseable as ISO datetime
        from datetime import datetime
        datetime.fromisoformat(result["generated_on"])

    def test_standalone_local_keys_match_canonical_target_dirs(self, tmp_path, monkeypatch):
        """local keys in standalone snapshot equal local_target_dirs() keys."""
        monkeypatch.setenv("LOCAL_MODEL_ROOT", str(tmp_path))
        result = get_model_availability_snapshot(dae=None, live_probe=False)
        assert set(result["local"].keys()) == set(local_target_dirs().keys())

    def test_runtime_snapshot_has_same_canonical_keys(self, tmp_path, monkeypatch):
        """Runtime snapshot (dae provided) has the same canonical top-level keys."""
        monkeypatch.setenv("LOCAL_MODEL_ROOT", str(tmp_path))
        dae = _make_dae()
        result = get_model_availability_snapshot(dae=dae, live_probe=False)
        missing = self._CANONICAL_KEYS - set(result.keys())
        assert not missing, f"Runtime snapshot missing canonical keys: {missing}"

    def test_standalone_default_target_from_env(self, tmp_path, monkeypatch):
        """dae=None reads target from OPENCLAW_CONVERSATION_MODEL_TARGET env."""
        monkeypatch.setenv("LOCAL_MODEL_ROOT", str(tmp_path))
        monkeypatch.setenv("OPENCLAW_CONVERSATION_MODEL_TARGET", "local/qwen3.5-4b")
        result = get_model_availability_snapshot(dae=None, live_probe=False)
        assert result["target"] == "local/qwen3.5-4b"

    def test_standalone_default_target_fallback(self, tmp_path, monkeypatch):
        """dae=None defaults target to local/qwen-coder-7b when env unset."""
        monkeypatch.setenv("LOCAL_MODEL_ROOT", str(tmp_path))
        monkeypatch.delenv("OPENCLAW_CONVERSATION_MODEL_TARGET", raising=False)
        result = get_model_availability_snapshot(dae=None, live_probe=False)
        assert result["target"] == "local/qwen-coder-7b"
