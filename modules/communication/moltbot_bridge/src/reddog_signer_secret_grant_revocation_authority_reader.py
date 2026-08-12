"""Read-only live SQLite view of durable signer-grant revocations."""

from __future__ import annotations

from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_authority_binding import (
    SignerGrantRevocationAuthorityBinding,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_authority_store import (
    RevocationAuthorityStoreState,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_store_codec import (
    open_revocation_db,
    payload,
    require_authority_graph,
    require_metadata,
    state_row,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)


class SignerGrantRevocationAuthorityReader:
    """Fresh-connection reader with no store mutation surface."""

    __slots__ = ("binding", "repo_root", "allowed_root", "path")

    def __init__(
        self, binding: SignerGrantRevocationAuthorityBinding, *, repo_root: Path | str,
    ) -> None:
        if type(binding) is not SignerGrantRevocationAuthorityBinding:
            raise ValueError("revocation_reader_binding_invalid")
        self.binding = binding
        self.repo_root = Path(repo_root).resolve()
        self.allowed_root = validate_runtime_root_path(
            binding.primary_root, repo_root=self.repo_root
        )
        self.path = validate_runtime_artifact_path(
            binding.primary_path, allowed_root=self.allowed_root, repo_root=self.repo_root
        )
        self.state()

    def detached(self) -> "SignerGrantRevocationAuthorityReader":
        return SignerGrantRevocationAuthorityReader(
            self.binding, repo_root=self.repo_root
        )

    def state(self) -> RevocationAuthorityStoreState:
        connection = open_revocation_db(self.path, read_only=True)
        try:
            connection.execute("BEGIN")
            require_metadata(connection, self.binding)
            current_id, pending_id = state_row(connection)
            require_authority_graph(connection, current_id, pending_id)
            result = RevocationAuthorityStoreState(
                payload(connection, current_id, expected_status="COMMITTED"),
                payload(connection, pending_id, expected_status="PREPARED"),
            )
            connection.commit()
            return result
        finally:
            connection.close()


__all__ = ["SignerGrantRevocationAuthorityReader"]
