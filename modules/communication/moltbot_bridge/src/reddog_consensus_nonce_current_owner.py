"""Canonical current-owner fence for the opt-in consensus nonce adapter."""
import json
import math
import time
from contextlib import contextmanager
from pathlib import Path

from . import reddog_signer_system_service_manifest_selection_loader as loader
from .reddog_consensus_nonce_custody import current_consensus_nonce_custody
from .reddog_grant_authority_startup_custody import require_private_grant_rate_store
from .reddog_signer_owner_e0_current_selection import lease_validated_owner_e0_current_admission
from .reddog_signer_owner_e0_capability_state import thaw_owner_e0_policy
from .reddog_signer_secret_grant_durable_nonce_store import _require_store_files
from .foundup_verified_outcome_root_authority_wire_codec import decode_message


def _bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


class _CurrentNonceOwner:
    def __init__(self, path, repo, expected_id):
        self.path, self.repo = Path(path), Path(repo).resolve()
        self.owner = loader._load_owner_config(self.path, repo=self.repo)
        if (self.owner["schema_version"] != loader.SCHEMA_VERSION_V13
                or self.owner["config_id"] != expected_id):
            raise ValueError("consensus_nonce_owner_binding_invalid")
        self.owner_bytes = _bytes(self.owner)
        self.policy = self._policy()
        self.policy_bytes = _bytes(self.policy)
        self.selection_bytes = None
        self.last_wall = self.last_mono = None

    def _policy(self):
        path = Path(self.owner["startup_custody"]["policy_path"])
        return decode_message(loader._read_root_owned_bytes(path, self.path.parent))

    def now(self):
        wall, mono = time.time(), time.monotonic()
        if (type(wall) not in (int, float) or type(mono) not in (int, float)
                or not math.isfinite(wall) or not math.isfinite(mono) or min(wall, mono) < 0
                or (self.last_wall is not None and (wall < self.last_wall or mono < self.last_mono))):
            raise ValueError("consensus_nonce_clock_invalid")
        self.last_wall, self.last_mono = wall, mono
        return wall

    def current(self, selected):
        owner = loader._load_owner_config(self.path, repo=self.repo)
        if (_bytes(owner) != self.owner_bytes or _bytes(self.owner) != self.owner_bytes
                or _bytes(self._policy()) != self.policy_bytes
                or _bytes(thaw_owner_e0_policy(selected.policy)) != self.policy_bytes):
            raise ValueError("consensus_nonce_owner_changed")
        selection = dict(selected.selection)
        identity = {key: value for key, value in selection.items()
                    if key not in {"selection_issued_at", "selection_expires_at"}}
        if selection["owner_config_id"] != owner["config_id"]:
            raise ValueError("consensus_nonce_generation_owner_mismatch")
        snapshot = _bytes(identity)
        if self.selection_bytes is not None and snapshot != self.selection_bytes:
            raise ValueError("consensus_nonce_generation_changed")
        now = self.now()
        binding, config, expiry = current_consensus_nonce_custody(owner, self.policy, self.repo, now)
        issued, deadline = selection["selection_issued_at"], selection["selection_expires_at"]
        if type(issued) is not int or type(deadline) is not int or not issued <= now < deadline:
            raise ValueError("consensus_nonce_generation_expired")
        require_private_grant_rate_store(owner, config)
        _require_store_files(config)
        if self.selection_bytes is None:
            self.selection_bytes = snapshot
        return binding, config, min(expiry, deadline)

    @contextmanager
    def lease(self):
        with lease_validated_owner_e0_current_admission(
            owner_config_path=self.path, repo_root=self.repo, policy=self.policy,
        ) as selected:
            before = self.current(selected)
            yield before
            after = self.current(selected)
            if before != after:
                raise ValueError("consensus_nonce_current_scope_changed")
        # Successful lease exit is required before exposing any operation result.
        self.current(selected)

    def cleanup_custody(self, config):
        """Withdrawal must not prevent removal of this instance's own reservation."""
        require_private_grant_rate_store(self.owner, config)
        _require_store_files(config)
