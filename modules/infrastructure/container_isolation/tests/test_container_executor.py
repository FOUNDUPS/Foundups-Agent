#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for container executor."""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from modules.infrastructure.container_isolation.src.container_executor import (
    ContainerExecutor,
    ContainerResult,
    ContainerConfig,
)
from modules.infrastructure.container_isolation.src.mount_policy import MountDecision


class TestContainerConfig:
    """Test ContainerConfig dataclass."""

    def test_default_values(self):
        """Config should have secure defaults."""
        config = ContainerConfig()
        assert config.image == "python:3.12-slim"
        assert config.user == "nobody"
        assert config.network == "none"
        assert config.memory_limit == "512m"
        assert config.cpu_limit == "1.0"

    def test_custom_values(self):
        """Config should accept custom values."""
        config = ContainerConfig(
            image="node:20-slim",
            timeout_sec=30.0,
            memory_limit="1g",
        )
        assert config.image == "node:20-slim"
        assert config.timeout_sec == 30.0
        assert config.memory_limit == "1g"


class TestContainerResult:
    """Test ContainerResult dataclass."""

    def test_success_result(self):
        """Success result should have correct fields."""
        result = ContainerResult(
            success=True,
            exit_code=0,
            stdout="output",
            stderr="",
            duration_ms=100.0,
        )
        assert result.success is True
        assert result.exit_code == 0

    def test_failure_result(self):
        """Failure result should include error."""
        result = ContainerResult(
            success=False,
            exit_code=1,
            stdout="",
            stderr="error message",
            duration_ms=50.0,
            error="Command failed",
        )
        assert result.success is False
        assert result.error == "Command failed"


class TestContainerExecutor:
    """Test ContainerExecutor class."""

    @pytest.fixture
    def executor_no_docker(self, tmp_path: Path) -> ContainerExecutor:
        """Create executor without Docker."""
        return ContainerExecutor(
            repo_root=tmp_path,
            docker_available=False,
        )

    @pytest.fixture
    def executor_with_docker(self, tmp_path: Path) -> ContainerExecutor:
        """Create executor with mocked Docker."""
        return ContainerExecutor(
            repo_root=tmp_path,
            docker_available=True,
        )

    def test_docker_not_available(self, executor_no_docker: ContainerExecutor):
        """Should report Docker unavailable."""
        assert executor_no_docker.docker_available is False

    def test_docker_available(self, executor_with_docker: ContainerExecutor):
        """Should report Docker available."""
        assert executor_with_docker.docker_available is True

    @pytest.mark.asyncio
    async def test_execute_without_docker(self, executor_no_docker: ContainerExecutor):
        """Execute should fail gracefully without Docker."""
        result = await executor_no_docker.execute(["echo", "test"])
        assert result.success is False
        assert result.error == "Docker not available"

    def test_sensitive_env_detection(self, executor_with_docker: ContainerExecutor):
        """Should detect sensitive environment variables."""
        assert executor_with_docker._is_sensitive_env("API_KEY") is True
        assert executor_with_docker._is_sensitive_env("SECRET_TOKEN") is True
        assert executor_with_docker._is_sensitive_env("PASSWORD") is True
        assert executor_with_docker._is_sensitive_env("AWS_SECRET_ACCESS_KEY") is True
        assert executor_with_docker._is_sensitive_env("PATH") is False
        assert executor_with_docker._is_sensitive_env("HOME") is False

    def test_build_mount_args(self, executor_with_docker: ContainerExecutor, tmp_path: Path):
        """Should build mount args with policy filtering."""
        # Create allowed directory
        modules_dir = tmp_path / "modules"
        modules_dir.mkdir()

        config = ContainerConfig(mounts=[str(modules_dir)])
        mount_args = executor_with_docker._build_mount_args(config)

        # Should have mount args for allowed directory
        assert len(mount_args) >= 2
        assert "-v" in mount_args

    def test_build_mount_args_blocks_sensitive(self, executor_with_docker: ContainerExecutor, tmp_path: Path):
        """Should block sensitive directories."""
        ssh_dir = tmp_path / ".ssh"
        ssh_dir.mkdir()

        config = ContainerConfig(mounts=[str(ssh_dir)])
        mount_args = executor_with_docker._build_mount_args(config)

        # Should NOT mount .ssh
        assert mount_args == []

    def test_build_docker_cmd(self, executor_with_docker: ContainerExecutor):
        """Should build secure Docker command."""
        config = ContainerConfig()
        cmd = executor_with_docker._build_docker_cmd(config, ["echo", "test"])

        # Check security flags
        assert "--rm" in cmd
        assert "--user" in cmd
        assert "nobody" in cmd
        assert "--network" in cmd
        assert "none" in cmd
        assert "--security-opt" in cmd
        assert "no-new-privileges" in cmd
        assert "--cap-drop" in cmd
        assert "ALL" in cmd
        assert "--read-only" in cmd


class TestContainerExecutorAsync:
    """Async tests for container execution."""

    @pytest.fixture
    def executor(self, tmp_path: Path) -> ContainerExecutor:
        return ContainerExecutor(repo_root=tmp_path, docker_available=True)

    @pytest.mark.asyncio
    async def test_execute_with_mocked_process(self, executor: ContainerExecutor):
        """Test execution with mocked subprocess."""
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"output", b""))
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await executor.execute(["echo", "test"])

        assert result.success is True
        assert result.stdout == "output"
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_execute_timeout(self, executor: ContainerExecutor):
        """Test execution timeout."""
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_proc.kill = MagicMock()
        mock_proc.wait = AsyncMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            config = ContainerConfig(timeout_sec=1.0)
            result = await executor.execute(["sleep", "10"], config)

        assert result.success is False
        assert "Timeout" in (result.error or "")

    @pytest.mark.asyncio
    async def test_execute_python(self, executor: ContainerExecutor):
        """Test Python code execution."""
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"42\n", b""))
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await executor.execute_python("print(6 * 7)")

        assert result.success is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
