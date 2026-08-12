"""Root-published authority for one exact verified FoundUp outcome."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
    decode_ed25519_public_key,
)
from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import (
    ProposalReplayHighWater,
    ProposalReplayHighWaterStore,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    public_key_fingerprint,
)


DESCRIPTOR_SCHEMA = "foundup_verified_outcome_root_authority.v1"
VERIFIER_PREFIX = "foundup-verified-outcome-verifier.v1."
HELD_OUT_PREFIX = "foundup-verified-outcome-held-out.v1."
MAX_AUTHORITY_TTL_SECONDS = 600
MAX_GRANTS = 16
VERIFIER_CLASS = "wre-independent-diff-verifier"
HELD_OUT_VERIFIER_CLASS = "wre-held-out-regression-verifier"

_DESCRIPTOR_FIELDS = frozenset(
    {
        "schema_version",
        "descriptor_id",
        "authority_generation_id",
        "authority_generation_sequence",
        "issuer_principal_id",
        "reddog_id",
        "foundup_id",
        "authority_tier",
        "consensus_receipt_digest",
        "signer_public_key",
        "signer_key_epoch",
        "signer_run_packet_id",
        "signer_config_digest",
        "signer_session_id",
        "signer_manifest_id",
        "signer_artifact_generation_digest",
        "replay_store_id",
        "replay_store_durability_receipt_id",
        "replay_anchor_binding_digest",
        "replay_anchor_sequence",
        "replay_anchor_revision",
        "issued_at",
        "expires_at",
        "grants",
        "revoked_authorization_ids",
        "revoked_verifier_fingerprints",
    }
)
_GRANT_FIELDS = frozenset(
    {
        "authorization_id",
        "authority_context_digest",
        "receipt_id",
        "evidence_digest",
        "foundup_id",
        "snapshot_id",
        "snapshot_content_digest",
        "work_order_id",
        "slice_id",
        "job_id",
        "head_sha",
        "content_digest",
        "worker_id",
        "verifier_id",
        "verifier_class",
        "verifier_public_key",
        "verification_receipt_digest",
        "verification_signature",
        "held_out_verifier_id",
        "held_out_verifier_class",
        "held_out_verifier_public_key",
        "held_out_receipt_digest",
        "held_out_signature",
        "runtime_binding_receipt_id",
        "runtime_binding_digest",
        "pattern_memory_record_digest",
        "issued_at",
        "expires_at",
    }
)
_DIGEST_FIELDS = frozenset(
    {
        "authority_context_digest",
        "evidence_digest",
        "snapshot_id",
        "snapshot_content_digest",
        "content_digest",
        "verification_receipt_digest",
        "held_out_receipt_digest",
        "runtime_binding_digest",
        "pattern_memory_record_digest",
    }
)


class RootVerifiedOutcomeSigningAuthority:
    """Opaque signer capability minted only from verified root-owned input."""

    __slots__ = ("__weakref__",)

    def __new__(
        cls, *_args: Any, **_kwargs: Any
    ) -> "RootVerifiedOutcomeSigningAuthority":
        raise TypeError("verified_outcome_root_authority_factory_required")

    def reserve(
        self,
        *,
        receipt_id: str,
        work_order_id: str,
        evidence_digest: str,
        issued_at: int,
        signer_instance_signature: str,
    ) -> object | None:
        from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_client import (
            reserve_service_authority,
        )

        return reserve_service_authority(
            self,
            receipt_id=receipt_id,
            work_order_id=work_order_id,
            evidence_digest=evidence_digest,
            issued_at=issued_at,
            signer_instance_signature=signer_instance_signature,
        )

    def reserve_proof_input(
        self, *, receipt_id: str, work_order_id: str,
        evidence_digest: str, issued_at: int,
    ) -> str:
        from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_client import (
            reserve_service_proof_input,
        )

        return reserve_service_proof_input(
            self, receipt_id=receipt_id, work_order_id=work_order_id,
            evidence_digest=evidence_digest, issued_at=issued_at,
        )

    def commit(
        self, reservation: object, signature_digest: str,
        signer_instance_signature: str,
    ) -> None:
        from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_client import (
            commit_service_authority,
        )

        commit_service_authority(
            self, reservation, signature_digest, signer_instance_signature
        )

    def commit_proof_input(
        self, reservation: object, signature_digest: str
    ) -> str:
        from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_client import (
            commit_service_proof_input,
        )

        return commit_service_proof_input(self, reservation, signature_digest)

    def rollback(self, reservation: object) -> None:
        # Reservation is deliberately burned before signing. A crash or failed
        # signature cannot reopen independently authorized evidence.
        from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_client import (
            rollback_service_authority,
        )

        rollback_service_authority(self, reservation)

    def __copy__(self) -> "RootVerifiedOutcomeSigningAuthority":
        raise TypeError("verified_outcome_root_authority_copy_forbidden")

    def __deepcopy__(self, _memo: Any) -> "RootVerifiedOutcomeSigningAuthority":
        raise TypeError("verified_outcome_root_authority_copy_forbidden")

    def __reduce__(self) -> Any:
        raise TypeError("verified_outcome_root_authority_pickle_forbidden")


def root_verified_outcome_authority_bindings(
    authority: object,
) -> Mapping[str, str]:
    """Expose only immutable public bindings from a factory-issued authority."""

    if type(authority) is not RootVerifiedOutcomeSigningAuthority:
        raise ValueError("verified_outcome_root_authority_unverified")
    from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_client import (
        client_authority_bindings,
    )

    return client_authority_bindings(authority)


def validate_root_verified_outcome_descriptor(
    value: Mapping[str, Any],
    *,
    replay_store: ProposalReplayHighWaterStore,
    now_epoch: int,
) -> dict[str, Any]:
    """Validate exact schema, co-signatures, scope, freshness, and store binding."""

    checked = validate_root_verified_outcome_descriptor_public(
        value, now_epoch=now_epoch
    )
    _require_store_binding(checked, replay_store)
    return checked


def validate_root_verified_outcome_descriptor_public(
    value: Mapping[str, Any], *, now_epoch: int
) -> dict[str, Any]:
    """Validate root descriptor content without acquiring its mutable store."""

    checked = validate_root_verified_outcome_descriptor_identity_public(
        value, now_epoch=now_epoch
    )
    checked["grants"] = _validate_grants(checked, now_epoch=now_epoch)
    return checked


def validate_root_verified_outcome_descriptor_identity(
    value: Mapping[str, Any], *, replay_store: ProposalReplayHighWaterStore,
    now_epoch: int,
) -> dict[str, Any]:
    """Validate root signer/generation identity without grant admission."""

    checked = validate_root_verified_outcome_descriptor_identity_public(
        value, now_epoch=now_epoch
    )
    _require_store_binding(checked, replay_store)
    return checked


def validate_root_verified_outcome_descriptor_identity_public(
    value: Mapping[str, Any], *, now_epoch: int
) -> dict[str, Any]:
    """Validate exact root descriptor identity without using outcome grants."""

    if not isinstance(value, Mapping) or set(value) != _DESCRIPTOR_FIELDS:
        raise ValueError("verified_outcome_root_descriptor_shape_invalid")
    checked = dict(value)
    _validate_descriptor_header(checked)
    _require_time_window(checked, now_epoch=now_epoch)
    if (
        not isinstance(checked["grants"], list)
        or len(checked["grants"]) > MAX_GRANTS
    ):
        raise ValueError("verified_outcome_root_grants_invalid")
    _text_set(checked["revoked_authorization_ids"])
    _digest_set(checked["revoked_verifier_fingerprints"])
    expected_id = _digest(
        {key: item for key, item in checked.items() if key != "descriptor_id"}
    )
    if checked.get("descriptor_id") != expected_id:
        raise ValueError("verified_outcome_root_descriptor_id_invalid")
    return checked


def _validate_descriptor_header(checked: Mapping[str, Any]) -> None:
    if checked.get("schema_version") != DESCRIPTOR_SCHEMA or not _ascii_deep(checked):
        raise ValueError("verified_outcome_root_descriptor_schema_invalid")
    descriptor_text = (
        "authority_generation_id",
        "issuer_principal_id",
        "reddog_id",
        "foundup_id",
        "authority_tier",
        "signer_public_key",
        "signer_key_epoch",
        "signer_session_id",
        "replay_store_id",
    )
    if any(not _text(checked.get(name)) for name in descriptor_text) or not _sha256(
        checked.get("replay_store_durability_receipt_id")
    ):
        raise ValueError("verified_outcome_root_descriptor_value_invalid")
    if (
        type(checked.get("authority_generation_sequence")) is not int
        or int(checked["authority_generation_sequence"]) < 1
    ):
        raise ValueError("verified_outcome_root_generation_invalid")
    if not _sha256(checked.get("consensus_receipt_digest")):
        raise ValueError("verified_outcome_root_consensus_invalid")
    if any(
        not _sha256(checked.get(name))
        for name in (
            "signer_run_packet_id",
            "signer_config_digest",
            "signer_manifest_id",
            "signer_artifact_generation_digest",
        )
    ):
        raise ValueError("verified_outcome_root_signer_runtime_invalid")
    if decode_ed25519_public_key(str(checked["signer_public_key"])) is None:
        raise ValueError("verified_outcome_root_signer_key_invalid")


def _validate_grants(
    descriptor: Mapping[str, Any], *, now_epoch: int
) -> list[dict[str, Any]]:
    grants = descriptor.get("grants")
    if not isinstance(grants, list) or not 1 <= len(grants) <= MAX_GRANTS:
        raise ValueError("verified_outcome_root_grants_invalid")
    revoked_ids = _text_set(descriptor.get("revoked_authorization_ids"))
    revoked_keys = _digest_set(descriptor.get("revoked_verifier_fingerprints"))
    validated = [
        _validate_grant(
            item,
            descriptor=descriptor,
            revoked_ids=revoked_ids,
            revoked_keys=revoked_keys,
            now_epoch=now_epoch,
        )
        for item in grants
    ]
    if len({item["authorization_id"] for item in validated}) != len(validated):
        raise ValueError("verified_outcome_root_authorization_duplicate")
    if len({item["evidence_digest"] for item in validated}) != len(validated):
        raise ValueError("verified_outcome_root_evidence_duplicate")
    if any(item["foundup_id"] != descriptor["foundup_id"] for item in validated):
        raise ValueError("verified_outcome_root_foundup_scope_invalid")
    return validated


def canonical_verifier_authorization_input(grant: Mapping[str, Any]) -> str:
    return VERIFIER_PREFIX + _canonical_json(_unsigned_grant(grant))


def canonical_held_out_authorization_input(grant: Mapping[str, Any]) -> str:
    return HELD_OUT_PREFIX + _canonical_json(_unsigned_grant(grant))


def authority_context_digest_for(descriptor: Mapping[str, Any]) -> str:
    """Bind co-signers to immutable root, signer, runtime, and replay context."""

    excluded = {
        "descriptor_id",
        "authority_generation_sequence",
        "grants",
        "revoked_authorization_ids",
        "revoked_verifier_fingerprints",
    }
    payload = {key: item for key, item in descriptor.items() if key not in excluded}
    if set(payload) != _DESCRIPTOR_FIELDS - excluded:
        raise ValueError("verified_outcome_root_descriptor_shape_invalid")
    return _digest(payload)


def authorization_id_for(grant: Mapping[str, Any]) -> str:
    payload = _unsigned_grant(grant)
    payload.pop("authorization_id", None)
    return "verified-outcome-authorization-" + _digest(payload)[7:39]


def descriptor_id_for(descriptor: Mapping[str, Any]) -> str:
    payload = dict(descriptor)
    payload.pop("descriptor_id", None)
    return _digest(payload)


def _validate_grant(
    value: Any,
    *,
    descriptor: Mapping[str, Any],
    revoked_ids: set[str],
    revoked_keys: set[str],
    now_epoch: int,
) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != _GRANT_FIELDS:
        raise ValueError("verified_outcome_root_grant_shape_invalid")
    grant = dict(value)
    if (
        not _ascii_deep(grant)
        or authorization_id_for(grant) != grant["authorization_id"]
    ):
        raise ValueError("verified_outcome_root_grant_id_invalid")
    _require_grant_values(grant, descriptor=descriptor, now_epoch=now_epoch)
    if grant["authority_context_digest"] != authority_context_digest_for(descriptor):
        raise ValueError("verified_outcome_root_authority_context_invalid")
    verifier_fingerprint = public_key_fingerprint(str(grant["verifier_public_key"]))
    held_out_fingerprint = public_key_fingerprint(
        str(grant["held_out_verifier_public_key"])
    )
    if (
        grant["authorization_id"] in revoked_ids
        or verifier_fingerprint in revoked_keys
        or held_out_fingerprint in revoked_keys
    ):
        raise ValueError("verified_outcome_root_grant_revoked")
    verifier = Ed25519SignatureVerifier()
    if not verifier.verify(
        str(grant["verifier_public_key"]),
        canonical_verifier_authorization_input(grant),
        str(grant["verification_signature"]),
    ):
        raise ValueError("verified_outcome_root_verifier_signature_invalid")
    if not verifier.verify(
        str(grant["held_out_verifier_public_key"]),
        canonical_held_out_authorization_input(grant),
        str(grant["held_out_signature"]),
    ):
        raise ValueError("verified_outcome_root_held_out_signature_invalid")
    return grant


def _require_grant_values(
    grant: Mapping[str, Any], *, descriptor: Mapping[str, Any], now_epoch: int
) -> None:
    if any(not _sha256(grant.get(name)) for name in _DIGEST_FIELDS):
        raise ValueError("verified_outcome_root_grant_digest_invalid")
    text_fields = (
        _GRANT_FIELDS
        - _DIGEST_FIELDS
        - {"issued_at", "expires_at", "verification_signature", "held_out_signature"}
    )
    if any(not _text(grant.get(name)) for name in text_fields):
        raise ValueError("verified_outcome_root_grant_value_missing")
    if (
        grant["verifier_class"] != VERIFIER_CLASS
        or grant["held_out_verifier_class"] != HELD_OUT_VERIFIER_CLASS
    ):
        raise ValueError("verified_outcome_root_verifier_class_invalid")
    if grant["foundup_id"] != descriptor["foundup_id"]:
        raise ValueError("verified_outcome_root_foundup_scope_invalid")
    if len(str(grant["head_sha"])) != 40 or any(
        char not in "0123456789abcdef" for char in str(grant["head_sha"])
    ):
        raise ValueError("verified_outcome_root_head_sha_invalid")
    identities = (
        grant["worker_id"],
        grant["verifier_id"],
        grant["held_out_verifier_id"],
    )
    keys = (
        descriptor["signer_public_key"],
        grant["verifier_public_key"],
        grant["held_out_verifier_public_key"],
    )
    if len(set(identities)) != 3 or len(set(keys)) != 3:
        raise ValueError("verified_outcome_root_authority_collapse")
    _require_time_window(grant, now_epoch=now_epoch)
    if int(grant["issued_at"]) < int(descriptor["issued_at"]) or int(
        grant["expires_at"]
    ) > int(descriptor["expires_at"]):
        raise ValueError("verified_outcome_root_grant_window_invalid")


def _require_time_window(value: Mapping[str, Any], *, now_epoch: int) -> None:
    issued = value.get("issued_at")
    expires = value.get("expires_at")
    if (
        type(now_epoch) is not int
        or type(issued) is not int
        or type(expires) is not int
        or issued > now_epoch
        or expires <= now_epoch
        or expires - issued <= 0
        or expires - issued > MAX_AUTHORITY_TTL_SECONDS
    ):
        raise ValueError("verified_outcome_root_authority_expired")


def _require_store_binding(
    descriptor: Mapping[str, Any], replay_store: ProposalReplayHighWaterStore
) -> None:
    try:
        anchor = replay_store.load(str(descriptor["replay_anchor_binding_digest"]))
        valid = (
            isinstance(replay_store, ProposalReplayHighWaterStore)
            and replay_store.durable is True
            and replay_store.store_id == descriptor["replay_store_id"]
            and replay_store.durability_receipt_id
            == descriptor["replay_store_durability_receipt_id"]
            and _sha256(replay_store.durability_receipt_id)
            and _sha256(descriptor["replay_anchor_binding_digest"])
            and type(descriptor["replay_anchor_sequence"]) is int
            and descriptor["replay_anchor_sequence"] >= 1
            and isinstance(descriptor["replay_anchor_revision"], str)
            and len(descriptor["replay_anchor_revision"]) == 64
            and all(
                char in "0123456789abcdef"
                for char in descriptor["replay_anchor_revision"]
            )
            and anchor
            == ProposalReplayHighWater(
                descriptor["replay_anchor_sequence"],
                descriptor["replay_anchor_revision"],
            )
        )
    except Exception:
        valid = False
    if not valid:
        raise ValueError("verified_outcome_root_replay_store_invalid")


def _unsigned_grant(grant: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(grant)
    payload.pop("verification_signature", None)
    payload.pop("held_out_signature", None)
    if set(payload) != _GRANT_FIELDS - {"verification_signature", "held_out_signature"}:
        raise ValueError("verified_outcome_root_grant_shape_invalid")
    return payload


def _text_set(value: Any) -> set[str]:
    if not isinstance(value, list) or any(not _text(item) for item in value):
        raise ValueError("verified_outcome_root_revocations_invalid")
    return set(map(str, value))


def _digest_set(value: Any) -> set[str]:
    if not isinstance(value, list) or any(not _sha256(item) for item in value):
        raise ValueError("verified_outcome_root_revocations_invalid")
    return set(map(str, value))


def _ascii_deep(value: Any) -> bool:
    if isinstance(value, str):
        return value.isascii()
    if isinstance(value, Mapping):
        return all(
            _ascii_deep(key) and _ascii_deep(item) for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return all(_ascii_deep(item) for item in value)
    return value is None or isinstance(value, (bool, int))


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value.isascii()


def _sha256(value: Any) -> bool:
    text = str(value or "")
    return (
        len(text) == 71
        and text.startswith("sha256:")
        and all(char in "0123456789abcdef" for char in text[7:])
    )


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    )


def _raw_digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _digest(value: Any) -> str:
    return _raw_digest(_canonical_json(value).encode("ascii"))


__all__ = [
    "DESCRIPTOR_SCHEMA",
    "HELD_OUT_PREFIX",
    "HELD_OUT_VERIFIER_CLASS",
    "MAX_AUTHORITY_TTL_SECONDS",
    "RootVerifiedOutcomeSigningAuthority",
    "VERIFIER_PREFIX",
    "VERIFIER_CLASS",
    "authorization_id_for",
    "authority_context_digest_for",
    "canonical_held_out_authorization_input",
    "canonical_verifier_authorization_input",
    "descriptor_id_for",
    "root_verified_outcome_authority_bindings",
    "validate_root_verified_outcome_descriptor",
    "validate_root_verified_outcome_descriptor_identity",
    "validate_root_verified_outcome_descriptor_identity_public",
    "validate_root_verified_outcome_descriptor_public",
]
