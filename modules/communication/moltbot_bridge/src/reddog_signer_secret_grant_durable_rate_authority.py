"""Durable rate authority composed from the signer grant replay store."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from pathlib import Path
from weakref import WeakSet

from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_durable_nonce_store import (
    DurableSignerSecretGrantNonceStore,
)

_ISSUED_RATE_BINDINGS = WeakSet()


@dataclass(frozen=True, eq=False)
class _ProtectedIssuerRateBinding:
    owner_path: Path
    repo: Path
    policy_bytes: bytes
    store: DurableSignerSecretGrantNonceStore
    expected_policy: tuple


def _current_rate_inputs(owner_path, repo, policy_bytes, store):
    """Re-read protected metadata; the service's current E0 lease stays outermost."""
    from .foundup_verified_outcome_root_authority_wire_codec import canonical_bytes, decode_message
    from .reddog_signer_system_service_manifest_selection_loader import (
        SCHEMA_VERSION_V10, SCHEMA_VERSION_V11, _load_owner_config, _read_root_owned_bytes,
    )
    from .reddog_grant_authority_startup_custody import (
        current_grant_custody, require_private_grant_rate_store,
        require_grant_rate_target_separation,
    )
    owner = _load_owner_config(owner_path, repo=repo)
    policy = decode_message(_read_root_owned_bytes(Path(owner["startup_custody"]["policy_path"]), owner_path.parent))
    if (owner["schema_version"] not in {SCHEMA_VERSION_V10, SCHEMA_VERSION_V11} or owner["config_id"] != policy["owner_config_id"]
            or canonical_bytes(policy) != policy_bytes):
        raise ValueError("grant_rate_owner_changed")
    current_grant_custody(owner, policy)
    config, target = require_grant_rate_target_separation(owner, policy, repo)
    if type(store) is not DurableSignerSecretGrantNonceStore or store._config != config:
        raise ValueError("grant_rate_store_binding_mismatch")
    require_private_grant_rate_store(owner, config)
    return policy, target


def _authority_values(policy, target):
    from .reddog_signer_independent_secret_grant_binding import resolve_secret_grant_target_binding_from_config
    values = asdict(resolve_secret_grant_target_binding_from_config(policy, target))
    values.update(issuer_key_epoch=policy["grant_authority_key_epoch"],
        requester_principal_id=policy["grant_requester_principal_id"])
    for name in ("allowed_operations", "allowed_authority_tiers", "consensus_required_tiers"):
        values[name] = tuple(policy[name])
    for name in ("rate_limit_window_seconds", "rate_limit_max_requests"):
        values[name] = policy[name]
    return tuple(sorted(values.items()))


def bind_protected_issuer_rate_store(*, owner_config_path, repo_root, owner_policy, replay_store):
    """Mint only from current protected installation, never a caller's rate fields."""
    from .foundup_verified_outcome_root_authority_wire_codec import canonical_bytes
    from .reddog_signer_owner_e0_capability_state import thaw_owner_e0_policy
    path, repo = Path(owner_config_path), Path(repo_root).resolve()
    if not path.is_absolute():
        raise ValueError("grant_rate_owner_path_invalid")
    policy_bytes = canonical_bytes(thaw_owner_e0_policy(owner_policy))
    policy, target = _current_rate_inputs(path, repo, policy_bytes, replay_store)
    binding = _ProtectedIssuerRateBinding(path, repo, policy_bytes, replay_store,
                                         _authority_values(policy, target))
    _ISSUED_RATE_BINDINGS.add(binding)
    return binding


def protected_issuer_rate_binding_matches(binding, policy, rate_store=None):
    """Reject forged/copy bindings and drift before any signing-key resolution."""
    if type(binding) is not _ProtectedIssuerRateBinding or binding not in _ISSUED_RATE_BINDINGS:
        return False
    try:
        current, target = _current_rate_inputs(binding.owner_path, binding.repo,
                                             binding.policy_bytes, binding.store)
        expected = tuple(sorted((item.name, getattr(policy, item.name))
                         for item in fields(policy) if item.name != "issuer_rate_binding"))
        return (expected == binding.expected_policy == _authority_values(current, target)
                and (rate_store is None or rate_store is binding.store))
    except Exception:
        return False


@dataclass(frozen=True, slots=True)
class DurableSignerSecretGrantRateAuthority:
    """Consume signed-policy rate slots through the canonical durable store."""

    replay_store: DurableSignerSecretGrantNonceStore

    def __post_init__(self) -> None:
        if type(self.replay_store) is not DurableSignerSecretGrantNonceStore:
            raise ValueError("secret_grant_rate_store_invalid")

    @property
    def replay_store_id(self) -> str:
        return self.replay_store.replay_store_id

    @property
    def durability_receipt_id(self) -> str:
        return self.replay_store.durability_receipt_id

    @property
    def replay_store_binding_digest(self) -> str:
        return self.replay_store.replay_store_binding_digest

    @property
    def replay_store_instance_digest(self) -> str:
        return self.replay_store.replay_store_instance_digest

    def consume_issuance_attempt(
        self,
        *,
        authority_subject: str,
        now_epoch: int,
        window_seconds: int,
        max_requests: int,
    ) -> bool:
        """Atomically consume one bounded slot in the active fixed window."""

        if _rate_request_rejected(
            authority_subject, now_epoch, window_seconds, max_requests
        ):
            return False
        window = now_epoch // window_seconds
        subject = f"secret-grant-rate:{authority_subject}:{window}"
        expires_at = (window + 1) * window_seconds + 1
        for slot in range(max_requests):
            if self.replay_store.consume_scoped_nonce(
                nonce=f"issuance-slot:{slot}",
                expires_at=expires_at,
                subject=subject,
            ):
                return True
        return False


def _rate_request_rejected(
    authority_subject: object,
    now_epoch: object,
    window_seconds: object,
    max_requests: object,
) -> bool:
    return bool(
        type(authority_subject) is not str
        or not authority_subject
        or not authority_subject.isascii()
        or type(now_epoch) is not int
        or now_epoch < 0
        or type(window_seconds) is not int
        or not 1 <= window_seconds <= 3600
        or type(max_requests) is not int
        or not 1 <= max_requests <= 1000
    )


__all__ = ["DurableSignerSecretGrantRateAuthority"]
