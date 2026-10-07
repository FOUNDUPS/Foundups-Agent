"""Audit-only use-time evidence for the current signer generation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_healthcheck import (
    SignerServiceHealthcheckResult, run_reddog_signer_socket_service_healthcheck,
)

from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    is_sha256,
)
from modules.communication.moltbot_bridge.src.reddog_signer_current_generation_runtime_binding import (
    SignerCurrentGenerationRuntimeBinding,
    _digest,
    verify_signer_current_generation_runtime_binding,
)


@dataclass(frozen=True)
class SignerCurrentGenerationUseTimeEvidence:
    """Non-authoritative evidence collected inside the valve resolver."""

    binding: SignerCurrentGenerationRuntimeBinding | None
    peer_receipt_id: str | None = None

    @property
    def peer_verified(self) -> bool:
        return self.receipt_id is not None and is_sha256(self.peer_receipt_id)

    @property
    def receipt_id(self) -> str | None:
        binding = self.binding
        if (
            type(binding) is not SignerCurrentGenerationRuntimeBinding
            or binding.accepted is not True
        ):
            return None
        return binding.receipt_id if is_sha256(binding.receipt_id) else None

    def principal_matches(self, identity, work_authority) -> bool:
        if self.receipt_id is None:
            return False
        try:
            return self.binding.principal_binding_digest == _digest(
                {"identity": identity, "work_authority": work_authority})
        except (TypeError, ValueError):
            return False

    def bound_identity_reasons(self, identity, authority, work_order=None, retained_proposal_inputs=None) -> tuple[str, ...]:
        reasons = ()
        if self.principal_matches(identity, authority):
            reasons += ("canonical_principal_subject_key_attestation_missing",)
            if self.memex_matches(work_order, retained_proposal_inputs):
                reasons += ("canonical_memex_supply_signed_evidence_verifier_missing",)
            if self.model_matches(work_order):
                reasons += ("canonical_model_signed_evidence_trust_anchor_incomplete",
                            "canonical_model_selection_signed_evidence_verifier_missing")
        if self.peer_verified:
            reasons += ("canonical_signer_client_peer_handshake_verifier_missing",)
        return reasons

    def memex_matches(self, work_order, bundle) -> bool:
        from .reddog_work_order_binding import canonical_full_work_order_digest
        if self.receipt_id is None or work_order is None or bundle is None:
            return False
        try:
            return (is_sha256(self.binding.memex_evidence_digest)
                    and self.binding.memex_evidence_digest == _digest(bundle)
                    and self.binding.memex_work_order_digest == canonical_full_work_order_digest(work_order))
        except (TypeError, ValueError):
            return False

    def model_matches(self, work_order) -> bool:
        from .reddog_work_order_binding import canonical_full_work_order_digest
        if self.receipt_id is None or work_order is None:
            return False
        try:
            return (is_sha256(self.binding.model_artifact_pair_digest)
                    and self.binding.model_work_order_digest == canonical_full_work_order_digest(work_order))
        except (TypeError, ValueError):
            return False

    def remaining_reasons(
        self, all_reasons: Iterable[str], bound_reasons: Iterable[str]
    ) -> tuple[str, ...]:
        bound = frozenset(bound_reasons)
        return tuple(
            reason
            for reason in all_reasons
            if self.receipt_id is None or reason not in bound
        )


def collect_signer_current_generation_use_time_evidence(
    enabled: bool,
    repo_root: Path,
    runtime_root: Path,
    trusted_now_epoch: Callable[[], int],
    *, principal_identity=None, principal_work_authority=None,
    peer_secret_access_grant_supplier=None,
    model_work_order=None,
    retained_proposal_inputs=None, revoked_key_epochs=frozenset(),
) -> SignerCurrentGenerationUseTimeEvidence:
    """Collect current-generation evidence without minting a capability."""

    if enabled is not True:
        return SignerCurrentGenerationUseTimeEvidence(None)
    trusted_now_epoch = _nondecreasing_clock(trusted_now_epoch)
    try:
        if peer_secret_access_grant_supplier is not None:
            return _collect_fresh_peer(repo_root, runtime_root, trusted_now_epoch,
                principal_identity, principal_work_authority, peer_secret_access_grant_supplier, model_work_order,
                retained_proposal_inputs, revoked_key_epochs)
        now_epoch = trusted_now_epoch()
        binding = verify_signer_current_generation_runtime_binding(
            repo_root=repo_root,
            runtime_root=runtime_root,
            now_epoch=now_epoch,
            principal_identity=principal_identity,
            principal_work_authority=principal_work_authority,
            model_work_order=model_work_order, trusted_now_epoch=trusted_now_epoch,
            retained_proposal_inputs=retained_proposal_inputs, revoked_key_epochs=revoked_key_epochs,
        )
        if binding.model_work_order_digest is not None or binding.memex_work_order_digest is not None:
            checked_at = trusted_now_epoch()
            if type(checked_at) is not int or checked_at < now_epoch or not _generation_fresh(binding, checked_at):
                return SignerCurrentGenerationUseTimeEvidence(None)
    except Exception:
        return SignerCurrentGenerationUseTimeEvidence(None)
    return SignerCurrentGenerationUseTimeEvidence(binding)


def _nondecreasing_clock(clock):
    last = [-1]
    def read():
        now = clock()
        if type(now) is not int or now < 0 or now < last[0]:
            raise ValueError("use_time_clock_reversed")
        last[0] = now
        return now
    return read


def _collect_fresh_peer(repo, runtime, clock, identity, authority, grant_supplier, model_work_order=None,
                      retained_proposal_inputs=None, revoked_key_epochs=frozenset()):
    if not callable(grant_supplier):
        return SignerCurrentGenerationUseTimeEvidence(None)
    start = clock()
    if type(start) is not int or start < 0:
        return SignerCurrentGenerationUseTimeEvidence(None)
    args = dict(repo_root=repo, runtime_root=runtime,
        signer_profile_id="reddog-work-authority", include_process_identity=True,
        principal_identity=identity, principal_work_authority=authority,
        model_work_order=model_work_order, trusted_now_epoch=clock,
        retained_proposal_inputs=retained_proposal_inputs, revoked_key_epochs=revoked_key_epochs)
    before = verify_signer_current_generation_runtime_binding(now_epoch=start, **args)
    evidence = SignerCurrentGenerationUseTimeEvidence(before)
    if not evidence.principal_matches(identity, authority):
        return SignerCurrentGenerationUseTimeEvidence(None)
    if any(type(value) is not int or value <= 0 for value in (before.signer_uid, before.signer_gid)):
        return SignerCurrentGenerationUseTimeEvidence(None)
    requester = identity.get("principal_id")
    if not isinstance(requester, str) or not requester:
        return SignerCurrentGenerationUseTimeEvidence(None)
    # resolve() releases the generation lease before grant acquisition/RPC.
    peer = run_reddog_signer_socket_service_healthcheck(
        repo_root=repo, run_packet_path=runtime / "signer_service_run_packet.json",
        requester_principal_id=requester, signer_profile_id=before.signer_profile_id,
        now_epoch=clock, manifest_id=before.manifest_id,
        artifact_generation_digest=before.artifact_generation_digest,
        expected_server_uid=before.signer_uid, expected_server_gid=before.signer_gid,
        trusted_socket_root=runtime, secret_access_grant_supplier=grant_supplier)
    end = clock()
    if type(end) is not int or end < start:
        return SignerCurrentGenerationUseTimeEvidence(None)
    after = verify_signer_current_generation_runtime_binding(now_epoch=end, **args)
    final = SignerCurrentGenerationUseTimeEvidence(after)
    if not _same_peer_identity(before, after) or not final.principal_matches(identity, authority):
        return SignerCurrentGenerationUseTimeEvidence(None)
    checked_at = clock()
    if type(checked_at) is not int or checked_at < end:
        return SignerCurrentGenerationUseTimeEvidence(None)
    if not all(_generation_fresh(item, checked_at) for item in (before, after)):
        return SignerCurrentGenerationUseTimeEvidence(None)
    if not _peer_matches(peer, after, requester, checked_at):
        return SignerCurrentGenerationUseTimeEvidence(None)
    receipt = _digest({"generation": after.receipt_id, "request": peer.request_digest,
        "response": peer.response_digest, "requester": requester})
    return SignerCurrentGenerationUseTimeEvidence(after, receipt)


def _same_peer_identity(before, after):
    if type(after) is not SignerCurrentGenerationRuntimeBinding or after.accepted is not True:
        return False
    fields = ("manifest_id", "artifact_generation_digest", "generation", "generation_revision",
        "owner_config_id", "config_digest", "config_raw_digest", "run_packet_digest", "run_packet_id",
        "session_id", "socket_path_digest", "signer_profile_id", "signer_public_key", "key_epoch",
        "principal_binding_digest", "signer_uid", "signer_gid", "manifest_expires_at")
    model_fields = ("model_work_order_digest", "model_artifact_pair_digest", "model_valid_until",
                    "memex_work_order_digest", "memex_evidence_digest", "memex_valid_until")
    if any(getattr(before, field) != getattr(after, field) for field in model_fields):
        return False
    return all(getattr(before, field) is not None and
               getattr(before, field) == getattr(after, field) for field in fields)


def _generation_fresh(binding, now):
    deadlines = (binding.selection_expires_at, binding.manifest_expires_at)
    if binding.model_work_order_digest is not None:
        deadlines += (binding.model_valid_until,)
    if binding.memex_work_order_digest is not None:
        deadlines += (binding.memex_valid_until,)
    return all(type(expiry) is int and expiry > now for expiry in deadlines)


def _peer_matches(peer, binding, requester, now):
    if type(peer) is not SignerServiceHealthcheckResult or peer.accepted is not True:
        return False
    if peer.peer_handshake_verified is not True or peer.server_identity_verified is not True:
        return False
    if peer.requester_principal_id != requester:
        return False
    if not all(is_sha256(value) for value in (peer.request_digest, peer.response_digest)):
        return False
    if any(type(expiry) is not int or expiry <= now for expiry in
           (binding.selection_expires_at, peer.peer_handshake_expires_at)):
        return False
    fields = ("manifest_id", "artifact_generation_digest", "run_packet_id",
              "config_digest", "session_id", "socket_path_digest",
              "signer_profile_id", "signer_public_key", "key_epoch")
    return all(getattr(binding, field) is not None and
               getattr(peer, field) == getattr(binding, field) for field in fields)


__all__ = [
    "SignerCurrentGenerationUseTimeEvidence",
    "collect_signer_current_generation_use_time_evidence",
]
