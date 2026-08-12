"""Uncomposed read-only durable revocation oracle for later E0 admission."""

from __future__ import annotations

from typing import Any, Callable, Mapping, TypeVar

from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import (
    ProposalReplayHighWater,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_authority_binding import (
    SignerGrantRevocationAuthorityBinding,
    expected_snapshot_binding,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_authority_reader import (
    SignerGrantRevocationAuthorityReader,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_contract import (
    verify_signer_grant_revocation_snapshot,
)
from modules.communication.moltbot_bridge.src.reddog_sqlite_monotonic_authority_store import (
    SqliteMonotonicAuthorityReader,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    PrincipalKeyResolver,
    SignatureVerifier,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    confined_runtime_operation_lock,
)

_T = TypeVar("_T")


class UncomposedDurableSignerGrantRevocationOracle:
    """Read and use one current snapshot under the writer's exact file lock."""

    def __init__(
        self, *, binding: SignerGrantRevocationAuthorityBinding,
        policy: Mapping[str, Any], reader: SignerGrantRevocationAuthorityReader,
        witness: SqliteMonotonicAuthorityReader,
        principal_key_resolver: PrincipalKeyResolver,
        signature_verifier: SignatureVerifier,
        clock: Callable[[], int],
    ) -> None:
        if (
            type(binding) is not SignerGrantRevocationAuthorityBinding
            or type(reader) is not SignerGrantRevocationAuthorityReader
            or type(witness) is not SqliteMonotonicAuthorityReader
        ):
            raise ValueError("durable_revocation_oracle_dependency_invalid")
        _require_reader_topology(binding, reader, witness)
        self.binding = binding
        self.expected = expected_snapshot_binding(policy, binding)
        self.reader = reader.detached()
        self.witness = witness.detached()
        self.resolver = principal_key_resolver
        self.verifier = signature_verifier
        self.clock = clock

    def is_revoked(self, *, grant_id: str, key_epoch: str, at_epoch: int) -> bool:
        with self._lock():
            current = self._current(self._checked_now(at_epoch))
            return _revoked(current, grant_id, key_epoch)

    def authorize_use(
        self, *, grant_id: str, key_epoch: str, at_epoch: int,
        action: Callable[[], _T],
    ) -> _T:
        with self._lock():
            current = self._current(self._checked_now(at_epoch))
            if _revoked(current, grant_id, key_epoch):
                raise RuntimeError("signer_secret_grant_revoked")
            result = action()
            after = self._current(self._now())
            if _revoked(after, grant_id, key_epoch):
                raise RuntimeError("signer_secret_grant_revoked")
            return result

    def _current(self, at_epoch: int) -> Mapping[str, Any]:
        state = self.reader.state()
        if state.pending is not None or state.current is None:
            raise RuntimeError("durable_revocation_oracle_state_invalid")
        expected = ProposalReplayHighWater(
            int(state.current["sequence"]),
            str(state.current["snapshot_id"]).removeprefix("sha256:"),
        )
        if self.witness.load(self.binding.witness_binding_digest()) != expected:
            raise RuntimeError("durable_revocation_oracle_witness_mismatch")
        return verify_signer_grant_revocation_snapshot(
            state.current, expected=self.expected,
            principal_key_resolver=self.resolver,
            signature_verifier=self.verifier, now_epoch=at_epoch,
        )

    def _checked_now(self, claimed: int) -> int:
        current = self._now()
        if type(claimed) is not int or claimed != current:
            raise ValueError("durable_revocation_oracle_clock_invalid")
        return current

    def _now(self) -> int:
        try:
            value = self.clock()
        except Exception:
            raise ValueError("durable_revocation_oracle_clock_invalid") from None
        if type(value) is not int:
            raise ValueError("durable_revocation_oracle_clock_invalid")
        return value

    def _lock(self):
        return confined_runtime_operation_lock(
            self.binding.operation_lock_path,
            repo_root=self.reader.repo_root,
            allowed_root=self.reader.allowed_root,
        )


def _require_reader_topology(
    binding: SignerGrantRevocationAuthorityBinding,
    reader: SignerGrantRevocationAuthorityReader,
    witness: SqliteMonotonicAuthorityReader,
) -> None:
    expected = (
        reader.binding, str(reader.path), witness.store_id,
        witness.durability_receipt_id, str(witness.path),
        str(witness.rollback_domain_root),
    )
    actual = (
        binding, binding.primary_path, binding.witness_store_id,
        binding.witness_durability_receipt_id, binding.witness_path,
        binding.witness_root,
    )
    if expected != actual:
        raise ValueError("durable_revocation_oracle_topology_invalid")


def _revoked(
    snapshot: Mapping[str, Any], grant_id: str, key_epoch: str
) -> bool:
    return (
        grant_id in snapshot["revoked_grant_ids"]
        or key_epoch in snapshot["revoked_key_epochs"]
    )


__all__ = ["UncomposedDurableSignerGrantRevocationOracle"]
