"""Private process-local Mesa epoch retry and post-commit observer orchestration.

This does not make the outer demurrage cycle or external delivery durable.
"""

import logging
import math
from fractions import Fraction
from threading import RLock

logger = logging.getLogger(__name__)


def _native_value(value):
    """Bounded exact binary reference; never a stored balance or debit operand."""
    if type(value) is not int and type(value) is not float:
        raise ValueError("funded amount must be a built-in number")
    if (type(value) is int and value.bit_length() > 1024
            or type(value) is float and not math.isfinite(value) or value < 0):
        raise ValueError("funded amount is outside the native admission domain")
    return Fraction(value)


class _EpochFunding:
    """New-run, serialized simulation transfer; no durable or custody authority."""

    def __init__(self, source, ledger):
        from .economics.demurrage import DemurrageEngine
        from .economics.epoch_ledger import EpochLedger
        if type(source) is not DemurrageEngine or type(ledger) is not EpochLedger:
            raise ValueError("funding requires the real simulation source and ledger")
        if (_native_value(source.pavs_treasury_balance) != 0 or source.wallets
                or ledger._entries or ledger._by_epoch or ledger._roots or ledger._trees):
            raise ValueError("funding requires a new run, not imported economic state")
        self._source, self._ledger, self._pool = source, ledger, None
        self._liabilities = ()  # Explicit synchronous-only premise; never inferred.
        self._settlements = {}

    def bind(self, pool):
        from .economics.pool_distribution import PoolDistributor
        if (self._pool is not None or type(pool) is not PoolDistributor
                or pool._ledger is not self._ledger or pool.participants or pool._epochs
                or _native_value(pool.accumulated_fund) != 0
                or _native_value(pool.total_drip_distributed) != 0):
            raise ValueError("funding binds once to its new ledger-coordinated pool")
        self._pool = pool

    def add(self, left, right):
        expected = _native_value(left) + _native_value(right)
        result = left + right
        if _native_value(result) != expected:
            raise ValueError("funded addition loses native component value")
        return result

    def prepare(self, pool, result, people):
        if pool is not self._pool or pool._ledger is not self._ledger:
            raise ValueError("funding source/pool/ledger binding changed")
        if type(self._liabilities) is not tuple or self._liabilities:
            raise ValueError("unknown or present liabilities hold new funded epochs")
        before = self._source.pavs_treasury_balance
        source, nominal = _native_value(before), _native_value(result.total_rewards)
        if nominal > source:
            raise ValueError("Treasury cannot cover the full nominal epoch request")
        credit = 0
        for plan in people:
            receipt = result.participant_rewards.get(plan.participant.participant_id, 0)
            gain = _native_value(plan.balance) - _native_value(plan.participant.ups_balance)
            if gain != _native_value(receipt):
                raise ValueError("funded participant gain differs from its receipt")
            credit = self.add(credit, receipt)
        if (_native_value(result.fund_accumulated) - _native_value(pool.accumulated_fund)
                != _native_value(result.fund_pool)):
            raise ValueError("funded Treasury fund gain differs from its allocation")
        credit = self.add(credit, result.fund_pool)
        if _native_value(credit) > nominal:
            raise ValueError("funded credits exceed the nominal epoch request")
        after = before - credit  # No rational residual or storage-type rescue.
        if source - _native_value(after) != _native_value(credit):
            raise ValueError("Treasury debit loses native transfer value")
        settlements = {**self._settlements, result.epoch: (before, after, credit)}
        return after, settlements

    def publish(self, prepared):
        self._source.pavs_treasury_balance, self._settlements = prepared


def _build_epoch_pool(mode, source, ledger):
    from .economics.pool_distribution import PoolDistributor
    if type(mode) is not str or mode not in ("legacy_unfunded", "sim_native_epoch_transfer_v1"):
        raise ValueError("unknown simulation epoch funding mode")
    funding = _EpochFunding(source, ledger) if mode == "sim_native_epoch_transfer_v1" else None
    return PoolDistributor(ledger=ledger, funding=funding)


class _EpochDistributionTail:
    def __init__(self):
        self._pending = None
        self._attempted = set()
        self._lock = RLock()

    def start(self, model, epoch, total):
        with self._lock:
            if self._pending is not None and self._pending != (epoch, total):
                raise ValueError("another epoch distribution is pending")
            self._pending = (epoch, total)
        return self.resume(model)

    def resume(self, model):
        with self._lock:
            if self._pending is None:
                return False
            epoch, total = self._pending
            distribution = model._pool_distributor.distribute_epoch(epoch, total)
            model._epoch_counter = epoch
            self._pending = None
        model._record_epoch_distribution(distribution)
        return True

    def observe(self, model, distribution):
        entry = model._pool_distributor._validated_entry(distribution)
        with self._lock:
            if entry.epoch_number in self._attempted:
                return distribution
            self._attempted.add(entry.epoch_number)
        try:
            _publish_observers(model, entry)
        except Exception:
            try:
                logger.warning("[MODEL] Epoch observer failed after local commit")
            except Exception:
                pass  # Even a failing logging handler must not report an economic abort.
        return distribution


def _publish_observers(model, entry):
    daemon = model._fam_bridge.get_daemon()
    if daemon:
        daemon.emit(
            event_type="epoch_ledger_recorded",
            payload={
                "epoch": entry.epoch_number,
                "entry_hash": entry.entry_hash,
                "participant_count": len(entry.participant_rewards),
                "total_distributed": round(float(entry.total_fi_distributed), 6),
            },
            actor_id="epoch_ledger",
            foundup_id=model._f0_source_foundup_id,
        )
    if not model._anchor_connector:
        return
    every = max(1, int(model._config.layer_d_anchor_every_n_epochs))
    if entry.epoch_number % every != 0:
        return
    commitment = model._epoch_ledger.prepare_settlement_commitment(entry.epoch_number)
    if commitment is None:
        return
    result = model._anchor_connector.publish_commitment(
        commitment, force=bool(model._config.layer_d_anchor_force_republish))
    if daemon:
        daemon.emit(
            event_type="settlement_anchor_published",
            payload={
                "epoch": entry.epoch_number,
                "success": bool(result.get("success", False)),
                "status": result.get("status"),
                "tx_ref": result.get("tx_ref"),
                "idempotent_hit": bool(result.get("idempotent_hit", False)),
                "error": result.get("error"),
            },
            actor_id="btc_anchor_connector",
            foundup_id=model._f0_source_foundup_id,
        )
