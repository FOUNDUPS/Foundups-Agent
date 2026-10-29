"""Persistent Foundup Registry Service for FoundUps Agent Market.

Implements FoundupRegistryService interface with SQLite persistence.
Manages Foundup entity lifecycle and metadata.

WSP References:
- WSP 11: Implements FoundupRegistryService interface contract
- WSP 30: Persistence layer integration
- WSP 50: Error handling with domain exceptions
"""

from __future__ import annotations

import logging
from typing import Dict, List

from .exceptions import ImmutableFieldError, PermissionDeniedError
from .interfaces import FoundupRegistryService
from .models import EventRecord, Foundup
from .persistence.sqlite_adapter import SQLiteAdapter

logger = logging.getLogger(__name__)


class PersistentFoundupRegistry(FoundupRegistryService):
    """Persistent implementation of FoundupRegistryService.

    Delegates storage to SQLiteAdapter.

    Invariants:
        - immutable_metadata cannot be changed after creation
        - mutable_metadata can be updated via update_foundup

    Example:
        adapter = SQLiteAdapter()
        registry = PersistentFoundupRegistry(adapter)
        foundup = registry.create_foundup(foundup)
    """

    def __init__(self, adapter: SQLiteAdapter) -> None:
        """Initialize with SQLite adapter.

        Args:
            adapter: SQLiteAdapter instance for persistence.
        """
        self._adapter = adapter

    def _enforce_compute_access(
        self,
        actor_id: str,
        capability: str,
        foundup_id: str,
        reason: str,
    ) -> None:
        ensure = getattr(self._adapter, "ensure_access", None)
        debit = getattr(self._adapter, "debit_credits", None)
        if not callable(ensure) or not callable(debit):
            return

        decision = ensure(actor_id=actor_id, capability=capability, foundup_id=foundup_id)
        if not bool(decision.get("allowed")):
            raise PermissionDeniedError(str(decision.get("reason", "compute access denied")))
        required = int(decision.get("required_credits", 0))
        if required > 0:
            debit(actor_id=actor_id, amount=required, reason=reason, foundup_id=foundup_id)

    def create_foundup(self, foundup: Foundup) -> Foundup:
        """Create a new Foundup.

        Args:
            foundup: Foundup to create.

        Returns:
            Created Foundup.
        """
        self._enforce_compute_access(
            actor_id=foundup.owner_id,
            capability="foundup.launch",
            foundup_id=foundup.foundup_id,
            reason="create_foundup",
        )
        created = self._adapter.create_foundup(foundup)
        logger.info("Foundup created: %s (%s)", foundup.foundup_id, foundup.name)
        return created

    def update_foundup(self, foundup_id: str, updates: Dict[str, str]) -> Foundup:
        """Update mutable_metadata of a Foundup.

        Args:
            foundup_id: ID of Foundup to update.
            updates: Key-value pairs to merge into mutable_metadata.

        Returns:
            Updated Foundup.

        Raises:
            NotFoundError: If Foundup not found.
            ImmutableFieldError: If updates attempt to modify immutable fields.
        """
        # Check for attempts to update immutable fields
        foundup = self._adapter.get_foundup(foundup_id)
        immutable_keys = set(foundup.immutable_metadata.keys())
        update_keys = set(updates.keys())
        conflict = immutable_keys & update_keys
        if conflict:
            raise ImmutableFieldError(f"Cannot modify immutable fields: {conflict}")

        updated = self._adapter.update_foundup(foundup_id, updates)
        logger.info("Foundup updated: %s", foundup_id)
        return updated

    def get_foundup(self, foundup_id: str) -> Foundup:
        """Get a Foundup by ID.

        Args:
            foundup_id: ID of Foundup to retrieve.

        Returns:
            Foundup record.

        Raises:
            NotFoundError: If Foundup not found.
        """
        return self._adapter.get_foundup(foundup_id)

    def list_foundups(self, limit: int = 100) -> List[Foundup]:
        """List all Foundups.

        Args:
            limit: Maximum number of Foundups to return.

        Returns:
            List of Foundups.
        """
        return self._adapter.list_foundups(limit=limit)


# Keep stub for backwards compatibility
class FoundupRegistryStub(FoundupRegistryService):
    """Stub implementation for testing (deprecated, use PersistentFoundupRegistry)."""

    pass
