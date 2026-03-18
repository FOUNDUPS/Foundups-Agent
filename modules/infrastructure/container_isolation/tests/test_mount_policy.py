#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for mount policy."""

import pytest
from pathlib import Path
import tempfile
import json

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from modules.infrastructure.container_isolation.src.mount_policy import (
    MountPolicy,
    MountDecision,
)


class TestMountPolicy:
    """Test MountPolicy class."""

    @pytest.fixture
    def policy(self, tmp_path: Path) -> MountPolicy:
        """Create policy with temp config path."""
        return MountPolicy(
            config_path=tmp_path / "mount-policy.json",
            repo_root=tmp_path,
        )

    def test_blocks_ssh(self, policy: MountPolicy):
        """SSH directory should always be blocked."""
        assert policy.check_mount("/home/user/.ssh") == MountDecision.BLOCKED_SENSITIVE
        assert policy.check_mount("~/.ssh/id_rsa") == MountDecision.BLOCKED_SENSITIVE

    def test_blocks_aws(self, policy: MountPolicy):
        """AWS credentials should always be blocked."""
        assert policy.check_mount("/home/user/.aws") == MountDecision.BLOCKED_SENSITIVE
        assert policy.check_mount("~/.aws/credentials") == MountDecision.BLOCKED_SENSITIVE

    def test_blocks_env_files(self, policy: MountPolicy):
        """Environment files should always be blocked."""
        assert policy.check_mount("/app/.env") == MountDecision.BLOCKED_SENSITIVE
        assert policy.check_mount("/app/.env.local") == MountDecision.BLOCKED_SENSITIVE
        assert policy.check_mount("/app/.env.production") == MountDecision.BLOCKED_SENSITIVE

    def test_blocks_secrets(self, policy: MountPolicy):
        """Secrets directories should be blocked."""
        assert policy.check_mount("/app/secrets") == MountDecision.BLOCKED_SENSITIVE
        assert policy.check_mount("/app/credentials") == MountDecision.BLOCKED_SENSITIVE

    def test_allows_modules(self, policy: MountPolicy, tmp_path: Path):
        """Modules directory should be allowed."""
        modules_path = tmp_path / "modules" / "test"
        modules_path.mkdir(parents=True)
        assert policy.check_mount(str(modules_path)) == MountDecision.ALLOWED

    def test_allows_docs(self, policy: MountPolicy, tmp_path: Path):
        """Docs directory should be allowed."""
        docs_path = tmp_path / "docs"
        docs_path.mkdir()
        assert policy.check_mount(str(docs_path)) == MountDecision.ALLOWED

    def test_blocks_unknown_paths(self, policy: MountPolicy):
        """Unknown paths should be blocked by default."""
        assert policy.check_mount("/random/unknown/path") == MountDecision.BLOCKED_NOT_IN_ALLOWLIST

    def test_custom_allowlist(self, policy: MountPolicy):
        """Custom allowlist should work."""
        policy.add_to_allowlist("custom_safe_dir")
        assert policy.check_mount("/app/custom_safe_dir/file.txt") == MountDecision.ALLOWED

    def test_custom_blocklist(self, policy: MountPolicy):
        """Custom blocklist should work."""
        policy.add_to_blocklist("my_secrets")
        assert policy.check_mount("/app/my_secrets") == MountDecision.BLOCKED_SENSITIVE

    def test_blocklist_overrides_allowlist(self, policy: MountPolicy):
        """Blocklist should take precedence over allowlist."""
        policy.add_to_allowlist("modules")
        # Even if modules is allowed, .env inside it is blocked
        assert policy.check_mount("/app/modules/.env") == MountDecision.BLOCKED_SENSITIVE

    def test_filter_allowed(self, policy: MountPolicy, tmp_path: Path):
        """filter_allowed should return only allowed paths."""
        # Create test directories
        (tmp_path / "modules").mkdir()
        (tmp_path / "docs").mkdir()

        paths = [
            str(tmp_path / "modules"),
            str(tmp_path / "docs"),
            "/home/user/.ssh",
            "/random/path",
        ]

        allowed = policy.filter_allowed(paths)
        assert len(allowed) == 2
        assert str(tmp_path / "modules") in allowed
        assert str(tmp_path / "docs") in allowed

    def test_save_and_load_config(self, policy: MountPolicy):
        """Config should persist to file."""
        policy.add_to_allowlist("my_custom_path")
        policy.add_to_blocklist("my_blocked_path")
        policy.save_config()

        # Create new policy from same config
        new_policy = MountPolicy(
            config_path=policy.config_path,
            repo_root=policy.repo_root,
        )

        assert "my_custom_path" in new_policy._custom_allowlist
        assert "my_blocked_path" in new_policy._custom_blocklist


class TestMountPolicyPatterns:
    """Test specific sensitive patterns."""

    @pytest.fixture
    def policy(self) -> MountPolicy:
        return MountPolicy()

    @pytest.mark.parametrize("path", [
        "/home/user/.gnupg",
        "/home/user/.gpg",
        "/home/user/.kube",
        "/home/user/.docker",
        "/app/private_key",
        "/app/id_rsa",
        "/app/id_ed25519",
        "/home/user/.netrc",
        "/home/user/.npmrc",
        "/home/user/.pypirc",
        "/app/token",
        "/app/api_key",
        "/app/password",
    ])
    def test_blocks_all_sensitive_patterns(self, policy: MountPolicy, path: str):
        """All sensitive patterns should be blocked."""
        assert policy.check_mount(path) == MountDecision.BLOCKED_SENSITIVE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
