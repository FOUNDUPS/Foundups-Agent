"""Provisioned, current-owner consensus nonces; no HIGH service is installed.

Failures after durable commit withhold success but cannot undo nonce consumption.
Rollback is confined to reservations actually created by this adapter instance.
"""
import threading
import uuid

from .reddog_consensus_nonce_current_owner import _CurrentNonceOwner
from .reddog_proposal_authenticity_nonce_store import AtomicProposalAuthenticityNonceStore, DEFAULT_PROPOSAL_NONCE_MAX_ENTRIES
from .reddog_sqlite_monotonic_authority_store import SqliteMonotonicAuthorityStore
from .reddog_runtime_artifact_manifest_contract import is_sha256
from modules.infrastructure.secrets_mcp.src.systemd_credential_secret_resolver import SystemdCredentialSecretResolver


class ProtectedConsensusNonceAuthority:
    def __new__(cls, *args, **kwargs):
        raise TypeError("consensus_nonce_authority_construction_forbidden")

    def reserve(self, nonce, *, expires_at, subject):
        return self._reserve(nonce, expires_at=expires_at, subject=subject)

    def _reserve(self, nonce, *, expires_at, subject, _scope=None):
        if (type(nonce) is not str or not is_sha256(nonce) or type(expires_at) is not int or type(subject) is not str
                or not any(subject.startswith(prefix) and is_sha256(subject[len(prefix):])
                           for prefix in ("elevated-consensus:", "effect-consensus:"))):
            raise ValueError("consensus_nonce_request_invalid")
        with self._lock:
            if len(self._owned) >= DEFAULT_PROPOSAL_NONCE_MAX_ENTRIES:
                raise ValueError("consensus_nonce_reservation_limit")
            token = None
            handle = uuid.uuid4().hex
            try:
                with self._owner.lease(_scope=_scope) as (_, _, deadline):
                    if not self._owner.now() < expires_at <= deadline:
                        raise ValueError("consensus_nonce_expiry_invalid")
                    self._store.validate_existing_state()
                    token = self._store.reserve(nonce, expires_at=expires_at, subject=subject)
                    if token is not None:
                        self._owned[handle] = token
                if token is None:
                    return None
                return handle
            except BaseException as original:
                if token is not None:
                    if self._cleanup(token, original):
                        self._owned.pop(handle)
                    else:
                        self._cleanup_only.add(handle)
                        original.consensus_nonce_cleanup_handle = handle
                raise

    def commit(self, reservation):
        return self._commit(reservation)

    def _commit(self, reservation, *, _scope=None):
        with self._lock:
            token = self._token(reservation)
            if reservation in self._cleanup_only:
                raise ValueError("consensus_nonce_cleanup_only")
            try:
                with self._owner.lease(_scope=_scope):
                    self._store.validate_existing_state()
                    self._store.commit(token)
                self._owned.pop(reservation)
            except BaseException as original:
                if self._cleanup(token, original):
                    self._owned.pop(reservation, None)
                else:
                    self._cleanup_only.add(reservation)
                raise

    def rollback(self, reservation):
        with self._lock:
            token = self._token(reservation)
            self._owner.cleanup_custody(self._config)
            self._store.validate_existing_state()
            self._store.rollback(token)
            self._owned.pop(reservation)
            self._cleanup_only.discard(reservation)

    def _token(self, handle):
        if type(handle) is not str or handle not in self._owned:
            raise ValueError("consensus_nonce_reservation_not_owned")
        return self._owned[handle]

    def _cleanup(self, token, original):
        try:
            self._owner.cleanup_custody(self._config)
            self._store.validate_existing_state()
            self._store.rollback(token)
        except BaseException:
            original.add_note("consensus_nonce_owned_cleanup_failed")
            return False
        else:
            original.add_note("consensus_nonce_owned_cleanup_completed")
            return True


def load_protected_consensus_nonce_authority(*, owner_config_path, repo_root, expected_owner_config_id):
    """Resolve only canonical protected owners, current E0 and existing credentials."""
    owner = _CurrentNonceOwner(owner_config_path, repo_root, expected_owner_config_id)
    with owner.lease() as (binding, config, _):
        permission = owner.owner["consensus_nonce_authority"]["integrity_permission"]
        resolver = SystemdCredentialSecretResolver(binding)
        result = resolver.resolve(permission["reference"], permission["requester_id"])
        if result.success is not True or result.reference != permission["reference"]:
            raise ValueError("consensus_nonce_credential_rejected")
        secret = result.get_value()
        if type(secret) is not str or not secret:
            raise ValueError("consensus_nonce_credential_invalid")
        resolver._remaining()
        high = SqliteMonotonicAuthorityStore(config.high_water_path,
            allowed_root=config.high_water_root, repo_root=config.repo_root,
            store_id=config.replay_store_id, durability_receipt_id=config.durability_receipt_id,
            require_existing=True)
        store = AtomicProposalAuthenticityNonceStore(config.nonce_path,
            allowed_root=config.nonce_root, repo_root=config.repo_root,
            integrity_key=secret.encode("utf-8"), replay_store_binding_digest=config.replay_store_binding_digest,
            high_water_store=high, clock=owner.now)
        store.validate_existing_state()
        resolver._remaining()
    result = object.__new__(ProtectedConsensusNonceAuthority)
    result._owner, result._config, result._store = owner, config, store
    result._owned, result._lock = {}, threading.RLock()
    result._cleanup_only = set()
    return result
