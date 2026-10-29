"""Immutable simulator epoch evidence and context-bound Merkle claims.

The v2 Python simulator encoding is not a chain amount-unit specification.
Amounts retain their existing units; inclusion proves neither funded entitlement
nor unique work consumption. Commitments remain pre-settlement evidence. Existing
BTC connector rows are not migrated to this changed hash format.
"""

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from threading import RLock
from types import MappingProxyType
from typing import Dict, List, Mapping, Optional, Tuple
import hashlib
import json
import math


FORMAT_VERSION = "foundups.epoch.v2"
Tree = Tuple[Tuple[str, ...], ...]


def _number(value):
    """Normalize equivalent built-in numbers without rounding integers."""
    if type(value) not in (int, float):
        raise ValueError("epoch amount must be a built-in number")
    if type(value) is float and not math.isfinite(value):
        raise ValueError("epoch amount must be finite")
    if value < 0:
        raise ValueError("epoch amount must be nonnegative")
    return int(value) if type(value) is float and value.is_integer() else value


def _identifier(value):
    if type(value) is not str or not value.strip():
        raise ValueError("epoch identity must be a nonempty string")
    return value


def _epoch(value):
    if type(value) is not int or value < 0:
        raise ValueError("epoch must be a nonnegative built-in integer")
    return value


def _amounts(value):
    if type(value) is not dict:
        raise ValueError("epoch amounts must be a dictionary")
    return {_identifier(key): _number(amount) for key, amount in value.items()}


def _digest(payload):
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _leaf(foundup_id, epoch, participant_id, amount):
    return _digest({"format_version": FORMAT_VERSION, "kind": "reward",
                    "foundup_id": _identifier(foundup_id), "epoch": _epoch(epoch),
                    "participant_id": _identifier(participant_id), "amount": _number(amount)})


def _node(left, right):
    return _digest({"format_version": FORMAT_VERSION, "kind": "node",
                    "left": left, "right": right})


def _build_tree(foundup_id, epoch, rewards):
    leaves = tuple(_leaf(foundup_id, epoch, pid, amount) for pid, amount in sorted(rewards.items()))
    if not leaves:
        return ((_digest({"format_version": FORMAT_VERSION, "kind": "empty",
                          "foundup_id": foundup_id, "epoch": epoch}),),)
    levels = [leaves]
    while len(levels[-1]) > 1:
        level = levels[-1]
        padded = level + (level[-1],) if len(level) % 2 else level
        levels.append(tuple(_node(padded[i], padded[i + 1]) for i in range(0, len(padded), 2)))
    return tuple(levels)


def _is_hash(value):
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


@dataclass(frozen=True)
class EpochEntry:
    """Finalized snapshot; the historical total_fi_distributed name retains its units."""

    epoch_number: int
    timestamp: str
    total_fi_distributed: float
    pool_allocations: Mapping[str, float]
    participant_rewards: Mapping[str, float]
    entry_hash: str = ""
    prev_hash: str = "genesis"
    foundup_id: str = ""
    format_version: str = FORMAT_VERSION

    def __post_init__(self):
        object.__setattr__(self, "pool_allocations", MappingProxyType(dict(self.pool_allocations)))
        object.__setattr__(self, "participant_rewards", MappingProxyType(dict(self.participant_rewards)))

    def compute_hash(self) -> str:
        return _digest({"format_version": self.format_version, "foundup_id": self.foundup_id,
                        "epoch": self.epoch_number, "timestamp": self.timestamp,
                        "total": self.total_fi_distributed, "pools": dict(self.pool_allocations),
                        "rewards": sorted(self.participant_rewards.items()), "prev": self.prev_hash})

    def to_dict(self) -> Dict:
        """Return a detached JSON summary, preserving reward privacy."""
        return {"epoch_number": self.epoch_number, "timestamp": self.timestamp,
                "total_fi_distributed": self.total_fi_distributed,
                "pool_allocations": dict(self.pool_allocations),
                "participant_count": len(self.participant_rewards),
                "entry_hash": self.entry_hash, "prev_hash": self.prev_hash,
                "foundup_id": self.foundup_id, "format_version": self.format_version}


@dataclass(frozen=True)
class MerkleProof:
    """Untrusted inclusion evidence; expectations must come from a trusted checkpoint."""

    participant_id: str
    amount: float
    leaf_hash: str
    proof_path: Tuple[Tuple[str, str], ...]
    merkle_root: str
    epoch_number: int
    foundup_id: str = ""
    format_version: str = FORMAT_VERSION

    def verify(self, *, expected_root: str, expected_foundup_id: str,
               expected_epoch: int, expected_participant_id: str) -> bool:
        """Verify this amount/subject against external root and context expectations."""
        try:
            if (type(self.format_version) is not str or self.format_version != FORMAT_VERSION
                    or _identifier(self.foundup_id) != _identifier(expected_foundup_id)
                    or _epoch(self.epoch_number) != _epoch(expected_epoch)
                    or _identifier(self.participant_id) != _identifier(expected_participant_id)
                    or not all(_is_hash(value) for value in (self.leaf_hash, self.merkle_root, expected_root))
                    or self.merkle_root != expected_root or type(self.proof_path) not in (tuple, list)):
                return False
            current = _leaf(self.foundup_id, self.epoch_number, self.participant_id, self.amount)
            if current != self.leaf_hash:
                return False
            for step in self.proof_path:
                if type(step) not in (tuple, list) or len(step) != 2:
                    return False
                sibling, direction = step
                if not _is_hash(sibling) or type(direction) is not str or direction not in ("left", "right"):
                    return False
                current = _node(sibling, current) if direction == "left" else _node(current, sibling)
            return current == expected_root
        except (TypeError, ValueError, OverflowError):
            return False


class EpochLedger:
    """Process-local finalized epoch evidence; this is not durable settlement state."""

    def __init__(self, foundup_id: str):
        self._foundup_id = _identifier(foundup_id)
        self._entries: List[EpochEntry] = []
        self._by_epoch: Dict[int, EpochEntry] = {}
        self._roots: Dict[int, str] = {}
        self._trees: Dict[int, Tree] = {}
        self._lock = RLock()

    @property
    def foundup_id(self):
        return self._foundup_id

    @property
    def entries(self):
        with self._lock:
            return tuple(self._entries)

    @property
    def merkle_roots(self):
        with self._lock:
            return MappingProxyType(dict(self._roots))

    @property
    def merkle_trees(self):
        with self._lock:
            return MappingProxyType(dict(self._trees))

    def record_epoch(self, epoch: int, total: float, pool_allocations: Dict[str, float],
                     participant_rewards: Dict[str, float]) -> EpochEntry:
        """Finalize once, accepting only exact normalized retries of an existing epoch."""
        epoch, total = _epoch(epoch), _number(total)
        pools, rewards = _amounts(pool_allocations), _amounts(participant_rewards)
        with self._lock:
            existing = self._by_epoch.get(epoch)
            if existing is not None:
                if (existing.total_fi_distributed == total and existing.pool_allocations == pools
                        and existing.participant_rewards == rewards):
                    return existing
                raise ValueError("epoch finalization conflicts with existing content")
            if self._entries and epoch <= self._entries[-1].epoch_number:
                raise ValueError("new epoch must increase; gaps are allowed")
            entry = EpochEntry(epoch, datetime.now(timezone.utc).isoformat(), total, pools, rewards,
                               prev_hash=self._entries[-1].entry_hash if self._entries else "genesis",
                               foundup_id=self.foundup_id)
            tree = _build_tree(self.foundup_id, epoch, rewards)
            entry = replace(entry, entry_hash=entry.compute_hash())
            self._entries.append(entry)
            self._by_epoch[epoch] = entry
            self._trees[epoch], self._roots[epoch] = tree, tree[-1][0]
            return entry

    def record_from_distribution(self, distribution) -> EpochEntry:
        return self.record_epoch(distribution.epoch, distribution.total_rewards,
                                 {"un": distribution.un_pool, "dao": distribution.dao_pool,
                                  "du": distribution.du_pool, "network": distribution.network_pool,
                                  "fund": distribution.fund_pool}, distribution.participant_rewards)

    def get_merkle_proof(self, epoch: int, participant_id: str) -> Optional[MerkleProof]:
        try:
            epoch, participant_id = _epoch(epoch), _identifier(participant_id)
        except ValueError:
            return None
        with self._lock:
            entry = self._by_epoch.get(epoch)
            if entry is None or participant_id not in entry.participant_rewards:
                return None
            tree = self._trees[epoch]
            index = sorted(entry.participant_rewards).index(participant_id)
            leaf, path = tree[0][index], []
            for level in tree[:-1]:
                sibling = index - 1 if index % 2 else min(index + 1, len(level) - 1)
                path.append((level[sibling], "left" if index % 2 else "right"))
                index //= 2
            return MerkleProof(participant_id, entry.participant_rewards[participant_id], leaf,
                               tuple(path), self._roots[epoch], epoch, self.foundup_id)

    def verify_entry(self, epoch_number: int) -> bool:
        with self._lock:
            entry = self._by_epoch.get(epoch_number) if type(epoch_number) is int else None
            return bool(entry and entry.entry_hash == entry.compute_hash()
                        and self._trees[epoch_number] == _build_tree(self.foundup_id, epoch_number, entry.participant_rewards)
                        and self._roots[epoch_number] == self._trees[epoch_number][-1][0])

    def verify_chain(self) -> bool:
        with self._lock:
            if len(self._entries) != len(self._by_epoch):
                return False
            previous, epoch = "genesis", -1
            for entry in self._entries:
                if (entry.prev_hash != previous or entry.epoch_number <= epoch
                        or entry.foundup_id != self.foundup_id or entry.format_version != FORMAT_VERSION
                        or self._by_epoch.get(entry.epoch_number) is not entry
                        or entry.entry_hash != entry.compute_hash()
                        or not self.verify_entry(entry.epoch_number)):
                    return False
                previous, epoch = entry.entry_hash, entry.epoch_number
            return True

    def get_audit_summary(self) -> Dict:
        with self._lock:
            return {"foundup_id": self.foundup_id, "total_epochs": len(self._entries),
                    "total_fi_distributed": sum(e.total_fi_distributed for e in self._entries),
                    "unique_participants": len({pid for e in self._entries for pid in e.participant_rewards}),
                    "latest_merkle_root": self._roots[self._entries[-1].epoch_number] if self._entries else "none",
                    "chain_valid": self.verify_chain(),
                    "first_epoch": self._entries[0].epoch_number if self._entries else None,
                    "last_epoch": self._entries[-1].epoch_number if self._entries else None}

    def get_participant_history(self, participant_id: str, limit: int = 50) -> List[Dict]:
        with self._lock:
            history = []
            for entry in reversed(self._entries):
                if participant_id in entry.participant_rewards:
                    history.append({"epoch": entry.epoch_number, "timestamp": entry.timestamp,
                                    "reward": entry.participant_rewards[participant_id],
                                    "total_distributed": entry.total_fi_distributed})
                    if len(history) >= limit:
                        break
            return history

    def anchor_to_chain(self, epoch: int) -> Optional[str]:
        """Prepare stable 20-byte anchor data; do not publish or migrate connector rows."""
        with self._lock:
            entry = self._by_epoch.get(epoch) if type(epoch) is int else None
            if entry is None:
                return None
            return _digest({"format_version": FORMAT_VERSION, "protocol": "pAVS-v1",
                            "type": "epoch_anchor", "foundup": self.foundup_id, "epoch": epoch,
                            "merkle_root": self._roots[epoch], "entry_hash": entry.entry_hash,
                            "timestamp": entry.timestamp})[:40]

    def prepare_settlement_commitment(self, epoch: int) -> Optional[Dict]:
        """Return detached pre-settlement evidence, not a confirmed payment receipt."""
        with self._lock:
            entry = self._by_epoch.get(epoch) if type(epoch) is int else None
            if entry is None:
                return None
            return {"status": "pre_settlement", "wsp_78_layer": "D_pending",
                    "requires": "external_btc_anchor_connector", "foundup_id": self.foundup_id,
                    "epoch": epoch, "anchor_hex": self.anchor_to_chain(epoch),
                    "merkle_root": self._roots[epoch], "entry_hash": entry.entry_hash,
                    "total_distributed": entry.total_fi_distributed,
                    "participant_count": len(entry.participant_rewards), "timestamp": entry.timestamp,
                    "format_version": FORMAT_VERSION}

    def anchor_epoch(self, epoch: int, force: bool = False) -> Optional[Dict]:
        """Existing optional connector handoff; non-mock migration remains a separate gate."""
        commitment = self.prepare_settlement_commitment(epoch)
        if commitment is None:
            return None
        try:
            from .btc_anchor_connector import get_anchor_connector
            return get_anchor_connector().publish_commitment(commitment, force=force)
        except ImportError:
            return {"success": False, "error": "btc_anchor_connector not available",
                    "foundup_id": self.foundup_id, "epoch": epoch}


_ledger_registry: Dict[str, EpochLedger] = {}
_registry_lock = RLock()


def get_epoch_ledger(foundup_id: str) -> EpochLedger:
    foundup_id = _identifier(foundup_id)
    with _registry_lock:
        if foundup_id not in _ledger_registry:
            _ledger_registry[foundup_id] = EpochLedger(foundup_id)
        return _ledger_registry[foundup_id]


def reset_epoch_ledgers() -> None:
    with _registry_lock:
        _ledger_registry.clear()


__all__ = ["EpochEntry", "MerkleProof", "EpochLedger", "get_epoch_ledger", "reset_epoch_ledgers"]
