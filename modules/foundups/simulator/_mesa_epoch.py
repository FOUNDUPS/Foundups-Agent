"""Private process-local Mesa epoch retry and post-commit observer orchestration.

This does not make the outer demurrage cycle or external delivery durable.
"""

import logging
from threading import RLock

logger = logging.getLogger(__name__)


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
