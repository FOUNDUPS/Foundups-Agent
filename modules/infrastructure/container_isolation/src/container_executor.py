#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Container Executor - Ephemeral Docker containers for skill execution.

NanoClaw Pattern (https://github.com/qwibitai/nanoclaw):
- Per-agent containers: Each skill runs in isolated container
- Ephemeral execution: Container created per invocation, destroyed after
- Unprivileged user: Run as nobody inside container
- Explicit mounts: Only allowlisted directories visible

WSP Compliance: WSP 95 (Skills Wardrobe), WSP 71 (Secrets Management)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .mount_policy import MountPolicy, MountDecision

logger = logging.getLogger(__name__)


@dataclass
class ContainerResult:
    """Result from container execution."""
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    container_id: Optional[str] = None
    error: Optional[str] = None


@dataclass
class ContainerConfig:
    """Configuration for container execution."""
    image: str = "python:3.12-slim"
    timeout_sec: float = 60.0
    memory_limit: str = "512m"
    cpu_limit: str = "1.0"
    user: str = "nobody"
    network: str = "none"  # No network by default (isolation)
    working_dir: str = "/workspace"
    env_vars: Dict[str, str] = field(default_factory=dict)
    mounts: List[str] = field(default_factory=list)


class ContainerExecutor:
    """
    Ephemeral container executor for isolated skill execution.

    NanoClaw Philosophy:
    - ~4000 lines of code (auditable)
    - Container is hard security boundary
    - Agent cannot escape container regardless of configuration
    - Defense-in-depth: mount allowlist + container isolation
    """

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        mount_policy: Optional[MountPolicy] = None,
        docker_available: Optional[bool] = None,
    ):
        self.repo_root = Path(repo_root) if repo_root else Path.cwd()
        self.mount_policy = mount_policy or MountPolicy(repo_root=self.repo_root)

        # Check Docker availability
        if docker_available is None:
            self._docker_available = self._check_docker()
        else:
            self._docker_available = docker_available

    def _check_docker(self) -> bool:
        """Check if Docker is available."""
        try:
            result = subprocess.run(
                ["docker", "version", "--format", "{{.Server.Version}}"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False

    @property
    def docker_available(self) -> bool:
        """Return whether Docker is available."""
        return self._docker_available

    def _build_mount_args(self, config: ContainerConfig) -> List[str]:
        """Build Docker mount arguments with policy enforcement."""
        mount_args = []

        for mount_path in config.mounts:
            decision = self.mount_policy.check_mount(mount_path)

            if decision == MountDecision.ALLOWED:
                # Read-only mount by default (security)
                abs_path = Path(mount_path).resolve()
                container_path = f"{config.working_dir}/{abs_path.name}"
                mount_args.extend(["-v", f"{abs_path}:{container_path}:ro"])
                logger.debug(f"[CONTAINER] Mount allowed: {mount_path} -> {container_path}")
            else:
                logger.warning(f"[CONTAINER] Mount blocked ({decision.value}): {mount_path}")

        return mount_args

    def _build_docker_cmd(
        self,
        config: ContainerConfig,
        command: List[str],
    ) -> List[str]:
        """Build full Docker run command."""
        cmd = ["docker", "run", "--rm"]

        # Security constraints
        cmd.extend(["--user", config.user])
        cmd.extend(["--memory", config.memory_limit])
        cmd.extend(["--cpus", config.cpu_limit])
        cmd.extend(["--network", config.network])
        cmd.extend(["--workdir", config.working_dir])

        # Security hardening
        cmd.extend(["--security-opt", "no-new-privileges"])
        cmd.extend(["--cap-drop", "ALL"])
        cmd.extend(["--read-only"])

        # Temp filesystem for /tmp
        cmd.extend(["--tmpfs", "/tmp:rw,noexec,nosuid,size=64m"])

        # Environment variables (filtered for safety)
        safe_env_keys = {"PATH", "PYTHONPATH", "HOME", "LANG", "LC_ALL"}
        for key, value in config.env_vars.items():
            if key.upper() in safe_env_keys or not self._is_sensitive_env(key):
                cmd.extend(["-e", f"{key}={value}"])

        # Mounts (policy-filtered)
        cmd.extend(self._build_mount_args(config))

        # Image and command
        cmd.append(config.image)
        cmd.extend(command)

        return cmd

    def _is_sensitive_env(self, key: str) -> bool:
        """Check if environment variable key is sensitive."""
        sensitive_patterns = {
            "key", "token", "secret", "password", "credential",
            "auth", "api_key", "apikey", "private",
        }
        key_lower = key.lower()
        return any(pattern in key_lower for pattern in sensitive_patterns)

    async def execute(
        self,
        command: List[str],
        config: Optional[ContainerConfig] = None,
    ) -> ContainerResult:
        """
        Execute command in ephemeral container.

        NanoClaw Pattern:
        - Container created fresh
        - Command executed
        - Container destroyed (--rm)
        - Result returned
        """
        if not self._docker_available:
            return ContainerResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr="",
                duration_ms=0,
                error="Docker not available",
            )

        config = config or ContainerConfig()
        docker_cmd = self._build_docker_cmd(config, command)

        logger.info(f"[CONTAINER] Executing: {' '.join(command[:3])}...")
        start_time = time.time()

        try:
            proc = await asyncio.create_subprocess_exec(
                *docker_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=config.timeout_sec,
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return ContainerResult(
                    success=False,
                    exit_code=-1,
                    stdout="",
                    stderr="",
                    duration_ms=(time.time() - start_time) * 1000,
                    error=f"Timeout after {config.timeout_sec}s",
                )

            duration_ms = (time.time() - start_time) * 1000
            exit_code = proc.returncode or 0

            return ContainerResult(
                success=exit_code == 0,
                exit_code=exit_code,
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
                duration_ms=duration_ms,
            )

        except Exception as e:
            return ContainerResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr="",
                duration_ms=(time.time() - start_time) * 1000,
                error=str(e),
            )

    async def execute_python(
        self,
        code: str,
        config: Optional[ContainerConfig] = None,
    ) -> ContainerResult:
        """Execute Python code in container."""
        config = config or ContainerConfig(image="python:3.12-slim")
        return await self.execute(["python", "-c", code], config)

    async def execute_skill(
        self,
        skill_path: Path,
        input_data: Dict[str, Any],
        config: Optional[ContainerConfig] = None,
    ) -> ContainerResult:
        """
        Execute a skill in isolated container.

        NanoClaw Pattern:
        - Skill code mounted read-only
        - Input passed via stdin (JSON)
        - Output captured from stdout
        """
        config = config or ContainerConfig()

        # Add skill directory to mounts
        skill_dir = skill_path.parent.resolve()
        decision = self.mount_policy.check_mount(str(skill_dir))

        if decision != MountDecision.ALLOWED:
            return ContainerResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr="",
                duration_ms=0,
                error=f"Skill directory blocked by mount policy: {decision.value}",
            )

        config.mounts.append(str(skill_dir))

        # Build command to execute skill
        skill_name = skill_path.name
        command = [
            "python", "-c",
            f"import sys, json; "
            f"sys.path.insert(0, '/workspace/{skill_dir.name}'); "
            f"from {skill_path.stem} import execute; "
            f"result = execute(json.loads('{json.dumps(input_data)}')); "
            f"print(json.dumps(result))"
        ]

        return await self.execute(command, config)


# Convenience function for simple execution
async def run_isolated(
    command: List[str],
    repo_root: Optional[Path] = None,
    timeout_sec: float = 60.0,
) -> ContainerResult:
    """Run command in isolated container with default settings."""
    executor = ContainerExecutor(repo_root=repo_root)
    config = ContainerConfig(timeout_sec=timeout_sec)
    return await executor.execute(command, config)
