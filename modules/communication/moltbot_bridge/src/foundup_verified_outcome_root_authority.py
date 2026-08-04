"""Root-published authority for one exact verified FoundUp outcome."""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from typing import Any, Callable, Mapping

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
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_contract import (
    _build_process_local_registry,
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


@dataclass(frozen=True)
class _AuthorityState:
    descriptor: Mapping[str, Any]
    owner_config_id: str
    grants: Mapping[str, Mapping[str, Any]]
    replay_store: ProposalReplayHighWaterStore
    current_descriptor_supplier: Callable[[], Mapping[str, Any]]
    clock: Callable[[], int]
    lock: threading.Lock
    reservation_seal: object


@dataclass(frozen=True)
class _Reservation:
    authorization_id: str
    receipt_id: str
    seal: object


_issue_authority, _lookup_authority = _build_process_local_registry(
    "verified_outcome_root_authority_unverified"
)
del _build_process_local_registry


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
    ) -> object | None:
        state = _lookup_authority(self)
        grant = _fresh_grant(state, str(evidence_digest))
        if grant is None or not _request_matches(
            grant, receipt_id, work_order_id, issued_at
        ):
            return None
        binding = _digest(
            {
                "authorization_id": grant["authorization_id"],
                "receipt_id": receipt_id,
                "replay_store_id": state.replay_store.store_id,
            }
        )
        revision = _raw_digest(
            _canonical_json(
                {
                    "authorization_id": grant["authorization_id"],
                    "evidence_digest": evidence_digest,
                    "issued_at": issued_at,
                    "receipt_id": receipt_id,
                }
            ).encode("ascii")
        )[7:]
        with state.lock:
            try:
                if state.replay_store.load(binding) is not None:
                    return None
                state.replay_store.advance(
                    binding,
                    expected=None,
                    next_value=ProposalReplayHighWater(1, revision),
                )
            except Exception:
                return None
        return _Reservation(
            authorization_id=str(grant["authorization_id"]),
            receipt_id=str(receipt_id),
            seal=state.reservation_seal,
        )

    def commit(self, reservation: object) -> None:
        _require_reservation(_lookup_authority(self), reservation)

    def rollback(self, reservation: object) -> None:
        # Reservation is deliberately burned before signing. A crash or failed
        # signature cannot reopen independently authorized evidence.
        _require_reservation(_lookup_authority(self), reservation)

    def __copy__(self) -> "RootVerifiedOutcomeSigningAuthority":
        raise TypeError("verified_outcome_root_authority_copy_forbidden")

    def __deepcopy__(self, _memo: Any) -> "RootVerifiedOutcomeSigningAuthority":
        raise TypeError("verified_outcome_root_authority_copy_forbidden")

    def __reduce__(self) -> Any:
        raise TypeError("verified_outcome_root_authority_pickle_forbidden")


def create_root_verified_outcome_signing_authority(
    descriptor: Mapping[str, Any],
    *,
    replay_store: ProposalReplayHighWaterStore,
    now_epoch: int,
    owner_config_id: str,
    current_descriptor_supplier: Callable[[], Mapping[str, Any]],
    clock: Callable[[], int],
) -> RootVerifiedOutcomeSigningAuthority:
    """Verify a root-published descriptor and mint one signer-only capability."""

    if (
        not _sha256(owner_config_id)
        or not callable(current_descriptor_supplier)
        or not callable(clock)
    ):
        raise ValueError("verified_outcome_root_owner_config_invalid")
    checked = validate_root_verified_outcome_descriptor(
        descriptor,
        replay_store=replay_store,
        now_epoch=now_epoch,
    )
    authority = object.__new__(RootVerifiedOutcomeSigningAuthority)
    grants = {str(item["evidence_digest"]): item for item in checked["grants"]}
    _issue_authority(
        authority,
        _AuthorityState(
            descriptor=checked,
            owner_config_id=owner_config_id,
            grants=grants,
            replay_store=replay_store,
            current_descriptor_supplier=current_descriptor_supplier,
            clock=clock,
            lock=threading.Lock(),
            reservation_seal=object(),
        ),
    )
    return authority


def root_verified_outcome_authority_bindings(
    authority: object,
) -> Mapping[str, str]:
    """Expose only immutable public bindings from a factory-issued authority."""

    if type(authority) is not RootVerifiedOutcomeSigningAuthority:
        raise ValueError("verified_outcome_root_authority_unverified")
    descriptor = _lookup_authority(authority).descriptor
    return {
        "descriptor_id": str(descriptor["descriptor_id"]),
        "owner_config_id": str(_lookup_authority(authority).owner_config_id),
        "issuer_principal_id": str(descriptor["issuer_principal_id"]),
        "reddog_id": str(descriptor["reddog_id"]),
        "foundup_id": str(descriptor["foundup_id"]),
        "authority_tier": str(descriptor["authority_tier"]),
        "consensus_receipt_digest": str(descriptor["consensus_receipt_digest"]),
        "signer_public_key": str(descriptor["signer_public_key"]),
        "signer_key_epoch": str(descriptor["signer_key_epoch"]),
        "signer_run_packet_id": str(descriptor["signer_run_packet_id"]),
        "signer_config_digest": str(descriptor["signer_config_digest"]),
        "signer_session_id": str(descriptor["signer_session_id"]),
        "signer_manifest_id": str(descriptor["signer_manifest_id"]),
        "signer_artifact_generation_digest": str(
            descriptor["signer_artifact_generation_digest"]
        ),
    }


def validate_root_verified_outcome_descriptor(
    value: Mapping[str, Any],
    *,
    replay_store: ProposalReplayHighWaterStore,
    now_epoch: int,
) -> dict[str, Any]:
    """Validate exact schema, co-signatures, scope, freshness, and store binding."""

    if not isinstance(value, Mapping) or set(value) != _DESCRIPTOR_FIELDS:
        raise ValueError("verified_outcome_root_descriptor_shape_invalid")
    checked = dict(value)
    _validate_descriptor_header(checked)
    _require_time_window(checked, now_epoch=now_epoch)
    _require_store_binding(checked, replay_store)
    checked["grants"] = _validate_grants(checked, now_epoch=now_epoch)
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


def _request_matches(
    grant: Mapping[str, Any], receipt_id: str, work_order_id: str, issued_at: int
) -> bool:
    return bool(
        grant["receipt_id"] == receipt_id
        and grant["work_order_id"] == work_order_id
        and type(issued_at) is int
        and int(grant["issued_at"]) <= issued_at < int(grant["expires_at"])
    )


def _fresh_grant(
    state: _AuthorityState, evidence_digest: str
) -> Mapping[str, Any] | None:
    try:
        now_epoch = state.clock()
        if type(now_epoch) is not int:
            return None
        current = validate_root_verified_outcome_descriptor(
            state.current_descriptor_supplier(),
            replay_store=state.replay_store,
            now_epoch=now_epoch,
        )
        if authority_context_digest_for(current) != authority_context_digest_for(
            state.descriptor
        ):
            return None
        current_grants = {
            str(item["evidence_digest"]): item for item in current["grants"]
        }
        original = state.grants.get(evidence_digest)
        return original if current_grants.get(evidence_digest) == original else None
    except Exception:
        return None


def _require_reservation(state: _AuthorityState, reservation: object) -> None:
    if (
        not isinstance(reservation, _Reservation)
        or reservation.seal is not state.reservation_seal
    ):
        raise ValueError("verified_outcome_root_reservation_invalid")


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
    "create_root_verified_outcome_signing_authority",
    "descriptor_id_for",
    "root_verified_outcome_authority_bindings",
    "validate_root_verified_outcome_descriptor",
]
