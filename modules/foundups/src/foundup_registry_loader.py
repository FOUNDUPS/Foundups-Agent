#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FoundUp Registry Read-Only Loader

Provides read-only access to foundup_registry.json for MCP scope validation.

WSP 97 Labels:
  - READONLY_LOADER_ONLY
  - NO_REGISTRY_MUTATION
  - FAIL_CLOSED_REQUIRED

Contract: MCP_FOUNDUP_SCOPE_REGISTRY_LOADER_SPEC_PHASE1
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

__all__ = [
    "load_registry",
    "list_foundup_ids",
    "is_valid_foundup_id",
    "get_module_path",
    "get_entity_type",
    "FoundUpRegistryLoader",
    "RegistryLoadError",
]

# Default registry path relative to this file
_DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parent.parent / "foundup_registry.json"

# Pattern from foundup_registry.schema.json: ^[a-z0-9_]+$
_FOUNDUP_ID_PATTERN = re.compile(r"^[a-z0-9_]+$")


class RegistryLoadError(Exception):
    """Raised when registry cannot be loaded or is malformed."""
    pass


class FoundUpRegistryLoader:
    """Read-only loader for foundup_registry.json (WSP 97: NO_REGISTRY_MUTATION)."""

    __slots__ = ("_registry", "_entities_by_id", "_path")

    def __init__(self, registry_path: Path | None = None) -> None:
        """Load registry once at construction time.

        Args:
            registry_path: Path to registry JSON. Defaults to modules/foundups/foundup_registry.json.

        Raises:
            FileNotFoundError: If registry file does not exist.
            RegistryLoadError: If registry is malformed.
        """
        self._path = registry_path or _DEFAULT_REGISTRY_PATH

        if not self._path.exists():
            raise FileNotFoundError(f"Registry not found: {self._path}")

        try:
            with open(self._path, "r", encoding="utf-8") as f:
                self._registry: dict[str, Any] = json.load(f)
        except json.JSONDecodeError as e:
            raise RegistryLoadError(f"Malformed registry JSON: {e}") from e

        # Validate minimal shape
        if not isinstance(self._registry, dict):
            raise RegistryLoadError("Registry root must be an object")
        if "entities" not in self._registry:
            raise RegistryLoadError("Registry missing 'entities' array")
        if not isinstance(self._registry["entities"], list):
            raise RegistryLoadError("Registry 'entities' must be an array")

        # Build index by foundup_id
        self._entities_by_id: dict[str, dict[str, Any]] = {}
        for entity in self._registry["entities"]:
            if not isinstance(entity, dict):
                raise RegistryLoadError("Each entity must be an object")
            fid = entity.get("foundup_id")
            if fid is None:
                raise RegistryLoadError("Entity missing 'foundup_id'")
            if not isinstance(fid, str):
                raise RegistryLoadError(f"Entity 'foundup_id' must be string, got {type(fid)}")
            self._entities_by_id[fid] = entity

    def is_valid_foundup_id(self, foundup_id: str) -> bool:
        """Check if foundup_id exists in registry.

        Returns False for:
        - Unknown foundup_id values
        - Values that don't match the pattern ^[a-z0-9_]+$
        - Non-string values
        """
        if not isinstance(foundup_id, str):
            return False
        if not _FOUNDUP_ID_PATTERN.match(foundup_id):
            return False
        return foundup_id in self._entities_by_id

    def get_module_path(self, foundup_id: str) -> str | None:
        """Return module_path for given foundup_id, or None if not found."""
        if not self.is_valid_foundup_id(foundup_id):
            return None
        entity = self._entities_by_id.get(foundup_id)
        if entity is None:
            return None
        return entity.get("module_path")

    def get_entity_type(self, foundup_id: str) -> str | None:
        """Return entity_type for given foundup_id (for scoping decisions)."""
        if not self.is_valid_foundup_id(foundup_id):
            return None
        entity = self._entities_by_id.get(foundup_id)
        if entity is None:
            return None
        return entity.get("entity_type")

    def list_foundup_ids(self) -> tuple[str, ...]:
        """Return all known foundup_ids."""
        return tuple(sorted(self._entities_by_id.keys()))

    def get_registry(self) -> dict[str, Any]:
        """Return the loaded registry (read-only reference)."""
        return self._registry

    @property
    def path(self) -> Path:
        """Return the path to the loaded registry."""
        return self._path


# Module-level singleton for default registry
_default_loader: FoundUpRegistryLoader | None = None


def _get_loader(path: Path | None = None) -> FoundUpRegistryLoader:
    """Get loader instance, using singleton for default path."""
    global _default_loader

    if path is not None:
        # Explicit path: always create new loader (no caching)
        return FoundUpRegistryLoader(path)

    # Default path: use singleton
    if _default_loader is None:
        _default_loader = FoundUpRegistryLoader()
    return _default_loader


def load_registry(path: Path | None = None) -> dict[str, Any]:
    """Load and return the registry dictionary.

    Args:
        path: Optional path to registry file. Defaults to production registry.

    Returns:
        The loaded registry dictionary.

    Raises:
        FileNotFoundError: If registry file does not exist.
        RegistryLoadError: If registry is malformed.
    """
    return _get_loader(path).get_registry()


def list_foundup_ids(path: Path | None = None) -> tuple[str, ...]:
    """Return all known foundup_ids from the registry.

    Args:
        path: Optional path to registry file. Defaults to production registry.

    Returns:
        Tuple of all foundup_id values, sorted alphabetically.
    """
    return _get_loader(path).list_foundup_ids()


def is_valid_foundup_id(foundup_id: str, path: Path | None = None) -> bool:
    """Check if foundup_id exists in registry.

    Args:
        foundup_id: The identifier to validate.
        path: Optional path to registry file. Defaults to production registry.

    Returns:
        True if foundup_id exists and matches pattern, False otherwise.
    """
    return _get_loader(path).is_valid_foundup_id(foundup_id)


def get_module_path(foundup_id: str, path: Path | None = None) -> str | None:
    """Get module_path for a foundup_id.

    Args:
        foundup_id: The identifier to look up.
        path: Optional path to registry file. Defaults to production registry.

    Returns:
        The module_path if found, None otherwise.
    """
    return _get_loader(path).get_module_path(foundup_id)


def get_entity_type(foundup_id: str, path: Path | None = None) -> str | None:
    """Get entity_type for a foundup_id.

    Args:
        foundup_id: The identifier to look up.
        path: Optional path to registry file. Defaults to production registry.

    Returns:
        The entity_type if found, None otherwise.
    """
    return _get_loader(path).get_entity_type(foundup_id)
