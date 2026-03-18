#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mount Policy - NanoClaw-style allowlist/blocklist for container mounts.

NanoClaw Pattern (https://github.com/qwibitai/nanoclaw):
- Agents can only see directories explicitly mounted
- Sensitive paths blocked by default (.ssh, .gnupg, .aws, .env, credentials)
- Mount allowlist at ~/.config/foundups/mount-allowlist.json

WSP Compliance: WSP 71 (Secrets Management), WSP 95 (Skills Wardrobe)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set


class MountDecision(Enum):
    """Mount decision result."""
    ALLOWED = "allowed"
    BLOCKED_SENSITIVE = "blocked_sensitive"
    BLOCKED_NOT_IN_ALLOWLIST = "blocked_not_in_allowlist"
    BLOCKED_PATTERN = "blocked_pattern"


@dataclass
class MountPolicy:
    """
    Mount policy manager for container isolation.

    NanoClaw Pattern:
    - Container can only see explicitly mounted directories
    - Sensitive paths blocked regardless of allowlist
    - Defense-in-depth: blocklist is hard security layer
    """

    # Default sensitive paths (ALWAYS blocked - NanoClaw pattern)
    DEFAULT_BLOCKLIST: Set[str] = field(default_factory=lambda: {
        ".ssh",
        ".gnupg",
        ".gpg",
        ".aws",
        ".azure",
        ".gcloud",
        ".kube",
        ".docker",
        ".env",
        ".env.local",
        ".env.production",
        "credentials",
        "secrets",
        "private_key",
        "id_rsa",
        "id_ed25519",
        ".netrc",
        ".npmrc",
        ".pypirc",
        "token",
        "api_key",
        "password",
    })

    # Paths that are always allowed (repo workspace)
    DEFAULT_ALLOWLIST: Set[str] = field(default_factory=lambda: {
        "modules",
        "holo_index",
        "WSP_framework",
        "WSP_knowledge",
        "docs",
        "tests",
        "temp",
        "logs",
    })

    config_path: Path = field(default_factory=lambda: Path.home() / ".config/foundups/mount-policy.json")
    repo_root: Optional[Path] = None

    # Runtime state
    _custom_allowlist: Set[str] = field(default_factory=set)
    _custom_blocklist: Set[str] = field(default_factory=set)

    def __post_init__(self):
        """Load custom policy from config file if exists."""
        self._load_config()

    def _load_config(self) -> None:
        """Load mount policy from config file."""
        if self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    config = json.load(f)
                self._custom_allowlist = set(config.get("allowlist", []))
                self._custom_blocklist = set(config.get("blocklist", []))
            except (json.JSONDecodeError, OSError):
                pass

    def save_config(self) -> None:
        """Save current policy to config file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump({
                "allowlist": sorted(self._custom_allowlist),
                "blocklist": sorted(self._custom_blocklist),
            }, f, indent=2)

    def check_mount(self, path: str) -> MountDecision:
        """
        Check if a path can be mounted into container.

        NanoClaw Defense-in-Depth:
        1. Blocklist check first (hard security boundary)
        2. Then allowlist check (configurable)
        """
        path_obj = Path(path)
        path_parts = set(path_obj.parts)
        path_name = path_obj.name.lower()

        # 1. Check blocklist (HARD SECURITY - never override)
        all_blocked = self.DEFAULT_BLOCKLIST | self._custom_blocklist
        for blocked in all_blocked:
            blocked_lower = blocked.lower()
            # Check if any path component matches blocked pattern
            if blocked_lower in {p.lower() for p in path_parts}:
                return MountDecision.BLOCKED_SENSITIVE
            # Check if filename contains blocked pattern
            if blocked_lower in path_name:
                return MountDecision.BLOCKED_SENSITIVE

        # 2. Check allowlist
        all_allowed = self.DEFAULT_ALLOWLIST | self._custom_allowlist

        # If repo_root is set, check relative paths
        if self.repo_root:
            try:
                rel_path = path_obj.relative_to(self.repo_root)
                rel_parts = rel_path.parts
                if rel_parts and rel_parts[0] in all_allowed:
                    return MountDecision.ALLOWED
            except ValueError:
                pass  # Path not relative to repo_root

        # Check absolute path components
        for allowed in all_allowed:
            if allowed in path_parts:
                return MountDecision.ALLOWED

        return MountDecision.BLOCKED_NOT_IN_ALLOWLIST

    def add_to_allowlist(self, path: str) -> None:
        """Add path to custom allowlist."""
        self._custom_allowlist.add(path)

    def add_to_blocklist(self, path: str) -> None:
        """Add path to custom blocklist."""
        self._custom_blocklist.add(path)

    def get_allowed_mounts(self, requested_paths: List[str]) -> Dict[str, MountDecision]:
        """Check multiple paths and return decisions."""
        return {path: self.check_mount(path) for path in requested_paths}

    def filter_allowed(self, requested_paths: List[str]) -> List[str]:
        """Return only paths that are allowed to mount."""
        return [p for p in requested_paths if self.check_mount(p) == MountDecision.ALLOWED]
