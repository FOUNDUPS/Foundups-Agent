"""Root-owned runtime authority for one-use verified Memex outcomes."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Callable, Mapping

from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_authenticity import (
    VerifiedFoundUpOutcomeCapability,
    verify_and_issue_foundup_memex_outcome,
)
from modules.communication.moltbot_bridge.src.foundup_memex_verified_outcome_runtime_store import (
    AuthorityRuntimeVerifiedOutcomeStore,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_verified_pattern_memory_sink import (
    reddog_verified_pattern_memory_record_digest,
)
from modules.communication.moltbot_bridge.src.reddog_architect_fix_promotion_publication import (
    architect_fix_committed_publication_reasons,
)


VERIFIED_OUTCOME_RUNTIME_REFERENCE_SCHEMA = (
    "foundup_memex_verified_outcome_runtime_reference.v1"
)
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
_HEAD_SHA = re.compile(r"[0-9a-f]{40}\Z")


@dataclass(frozen=True)
class VerifiedOutcomeRuntimeReference:
    schema_version: str
    record_id: str
    foundup_id: str
    snapshot_id: str
    snapshot_content_digest: str
    work_order_id: str
    slice_id: str
    job_id: str
    head_sha: str
    content_digest: str
    worker_id: str
    verifier_id: str
    runtime_binding_receipt_id: str
    runtime_binding_digest: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

    @classmethod
    def from_mapping(
        cls, value: Mapping[str, Any]
    ) -> "VerifiedOutcomeRuntimeReference":
        fields = set(cls.__dataclass_fields__)
        if not isinstance(value, Mapping) or set(value) != fields:
            raise ValueError("verified_outcome_runtime_reference_schema_invalid")
        payload = {key: str(value.get(key) or "").strip() for key in fields}
        if payload["schema_version"] != VERIFIED_OUTCOME_RUNTIME_REFERENCE_SCHEMA:
            raise ValueError("verified_outcome_runtime_reference_schema_invalid")
        if any(
            not payload[key]
            for key in fields - {"runtime_binding_receipt_id", "runtime_binding_digest"}
        ):
            raise ValueError("verified_outcome_runtime_reference_field_missing")
        if bool(payload["runtime_binding_receipt_id"]) != bool(
            payload["runtime_binding_digest"]
        ):
            raise ValueError("verified_outcome_runtime_reference_binding_invalid")
        if (
            not payload["record_id"].startswith("reddog_verified_outcome_")
            or not _DIGEST.fullmatch(payload["snapshot_id"])
            or not _DIGEST.fullmatch(payload["snapshot_content_digest"])
            or not _DIGEST.fullmatch(payload["content_digest"])
            or not _HEAD_SHA.fullmatch(payload["head_sha"])
            or (
                payload["runtime_binding_digest"]
                and not _DIGEST.fullmatch(payload["runtime_binding_digest"])
            )
        ):
            raise ValueError("verified_outcome_runtime_reference_format_invalid")
        return cls(**payload)


@dataclass(frozen=True)
class VerifiedOutcomeRuntimeAuthority:
    store: AuthorityRuntimeVerifiedOutcomeStore
    outcome_signer_key_resolver: Any
    signature_verifier: Any
    revocation_oracle: Any
    issuer_principal_id: str
    issuer_principal_provider: str
    reddog_id: str
    trusted_now_epoch: Callable[[], int]
    max_age_seconds: int = 600

    def issue(
        self,
        reference: VerifiedOutcomeRuntimeReference | Mapping[str, Any],
    ) -> VerifiedFoundUpOutcomeCapability:
        ref = VerifiedOutcomeRuntimeReference.from_mapping(
            reference.to_dict()
            if isinstance(reference, VerifiedOutcomeRuntimeReference)
            else reference
        )
        _validate_authority_dependencies(self)
        envelope = self.store.load_envelope(ref.record_id)
        if envelope is None:
            raise ValueError("verified_outcome_durable_source_missing")
        record = dict(envelope["record"])
        binding = dict(record.get("admission_metadata") or {})
        _validate_reference(ref, record, binding)
        _validate_envelope_identity(self, envelope)
        public_key = _resolve_active_public_key(self, envelope)
        now_epoch = self.trusted_now_epoch()
        if type(now_epoch) is not int:
            raise ValueError("verified_outcome_runtime_clock_invalid")
        return verify_and_issue_foundup_memex_outcome(
            source=self.store,
            record_id=ref.record_id,
            verification_receipt=envelope["verification_receipt"],
            held_out_receipt=envelope["held_out_receipt"],
            signed_receipts=envelope["signed_receipts"],
            reddog_public_key=public_key,
            signature_verifier=self.signature_verifier,
            reddog_id=self.reddog_id,
            expected_foundup_id=ref.foundup_id,
            expected_snapshot_id=ref.snapshot_id,
            expected_snapshot_content_digest=ref.snapshot_content_digest,
            replay_store=self.store,
            now_epoch=now_epoch,
            max_age_seconds=self.max_age_seconds,
        )


def _resolve_active_public_key(
    authority: VerifiedOutcomeRuntimeAuthority,
    envelope: Mapping[str, Any],
) -> str:
    public_key = authority.outcome_signer_key_resolver.resolve(
        authority.reddog_id,
        str(envelope["key_epoch"]),
    )
    fingerprint = envelope["signer_key_fingerprint"]
    if not public_key or public_key_fingerprint(public_key) != fingerprint:
        raise ValueError("verified_outcome_authoritative_key_unavailable")
    if authority.revocation_oracle.is_revoked(
        reddog_id=authority.reddog_id,
        fingerprint=fingerprint,
        principal_id=authority.issuer_principal_id,
        key_epoch=envelope["key_epoch"],
    ):
        raise ValueError("verified_outcome_signer_revoked")
    return public_key


def _validate_authority_dependencies(
    authority: VerifiedOutcomeRuntimeAuthority,
) -> None:
    if (
        not callable(
            getattr(authority.outcome_signer_key_resolver, "resolve", None)
        )
        or not callable(getattr(authority.signature_verifier, "verify", None))
        or not callable(getattr(authority.revocation_oracle, "is_revoked", None))
        or not callable(authority.trusted_now_epoch)
        or any(
            not str(value or "").strip()
            for value in (
                authority.issuer_principal_id,
                authority.issuer_principal_provider,
                authority.reddog_id,
            )
        )
        or authority.max_age_seconds <= 0
    ):
        raise ValueError("verified_outcome_runtime_authority_invalid")


class CommittedAuthorityProfileOutcomeKeyResolver:
    """Resolve the RedDog verifier key only from a committed profile publication."""

    def __init__(
        self,
        *,
        work_state_snapshot: Mapping[str, Any],
        authority_profile: Mapping[str, Any],
    ) -> None:
        binding = authority_profile.get("operational_context_binding")
        if not isinstance(binding, Mapping):
            raise ValueError("verified_outcome_key_profile_binding_missing")
        reasons = architect_fix_committed_publication_reasons(
            work_state_snapshot,
            authority_profile,
            queue_item_id=str(binding.get("queue_item_id") or ""),
            claim_id=str(binding.get("claim_id") or ""),
        )
        if reasons:
            raise ValueError("verified_outcome_key_profile_not_committed")
        self._reddog_id = str(authority_profile.get("reddog_id") or "")
        self._key_epoch = str(authority_profile.get("key_epoch") or "")
        self._public_key = str(authority_profile.get("reddog_public_key") or "")
        if not self._reddog_id or not self._key_epoch or not self._public_key:
            raise ValueError("verified_outcome_key_profile_invalid")

    def resolve(self, reddog_id: str, key_epoch: str) -> str | None:
        if reddog_id != self._reddog_id or key_epoch != self._key_epoch:
            return None
        return self._public_key


def _validate_envelope_identity(
    authority: VerifiedOutcomeRuntimeAuthority,
    envelope: Mapping[str, Any],
) -> None:
    if (
        envelope["issuer_principal_id"] != authority.issuer_principal_id
        or envelope["issuer_principal_provider"] != authority.issuer_principal_provider
        or envelope["reddog_id"] != authority.reddog_id
    ):
        raise ValueError("verified_outcome_runtime_identity_mismatch")


def _validate_reference(
    ref: VerifiedOutcomeRuntimeReference,
    record: Mapping[str, Any],
    binding: Mapping[str, Any],
) -> None:
    expected = {
        "foundup_id": ref.foundup_id,
        "snapshot_id": ref.snapshot_id,
        "snapshot_content_digest": ref.snapshot_content_digest,
        "work_order_id": ref.work_order_id,
        "slice_id": ref.slice_id,
        "job_id": ref.job_id,
        "head_sha": ref.head_sha,
        "worker_id": ref.worker_id,
        "verifier_id": ref.verifier_id,
        "runtime_binding_receipt_id": ref.runtime_binding_receipt_id,
        "runtime_binding_digest": ref.runtime_binding_digest,
    }
    if any(binding.get(key) != value for key, value in expected.items()):
        raise ValueError("verified_outcome_runtime_reference_mismatch")
    if reddog_verified_pattern_memory_record_digest(record) != ref.content_digest:
        raise ValueError("verified_outcome_runtime_content_digest_mismatch")


__all__ = [
    "CommittedAuthorityProfileOutcomeKeyResolver",
    "VERIFIED_OUTCOME_RUNTIME_REFERENCE_SCHEMA",
    "VerifiedOutcomeRuntimeAuthority",
    "VerifiedOutcomeRuntimeReference",
]
