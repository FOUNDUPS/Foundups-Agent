"""AgentDB CAS and lease storage for RedDog FIX promotion coordination."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Mapping, Optional

from modules.communication.moltbot_bridge.src.reddog_agentdb_fix_promotion_claim_storage import (
    claim_id_for_binding,
    ensure_claim_table,
    insert_pending_claim,
    iso_utc,
    lease_claim_row,
    utc,
)
from modules.communication.moltbot_bridge.src.reddog_agentdb_fix_promotion_claim_record import (
    RedDogFixPromotionClaim,
    accepted_fix_promotion_claim,
)
from modules.communication.moltbot_bridge.src.reddog_agentdb_architect_determination_reader import (
    load_agentdb_architect_determination,
)
from modules.communication.moltbot_bridge.src.reddog_resident_architect_durable_agentdb_cycle import (
    STATUS_DETERMINED,
)


CLAIM_READY = "REDDOG_FIX_PROMOTION_CLAIM_READY"
CLAIM_IDLE = "REDDOG_FIX_PROMOTION_CLAIM_IDLE"
STATUS_CLAIMED = "CLAIMED"
STATUS_APPLIED = "APPLIED"

class AgentDbFixPromotionClaimStore:
    """Persist a coordination lease without granting promotion authority."""

    def __init__(self, agent_db_factory: Optional[Callable[[], Any]] = None) -> None:
        self._factory = agent_db_factory

    def determined_intent_ids(self) -> tuple[str, ...]:
        db = self._db()
        ensure_claim_table(db)
        if not db.db.table_exists("reddog_resident_architect_cycles"):
            return ()
        rows = db.db.execute_query(
            "SELECT intent_id FROM reddog_resident_architect_cycles "
            "WHERE status = ? ORDER BY updated_at ASC, intent_id ASC",
            (STATUS_DETERMINED,),
        )
        return tuple(str(row["intent_id"]) for row in rows)

    def load_determination(self, determination_id: str) -> Mapping[str, Any] | None:
        return load_agentdb_architect_determination(
            determination_id,
            agent_db_factory=self._factory,
        )

    def claim(
        self,
        binding: Mapping[str, str],
        *,
        worker_id: str,
        now: datetime | None = None,
        lease_seconds: int = 300,
    ) -> RedDogFixPromotionClaim:
        observed = utc(now)
        if not worker_id.strip() or not 30 <= int(lease_seconds) <= 900:
            return self.idle("claim_request_invalid")
        db = self._db()
        ensure_claim_table(db)
        claim_id = claim_id_for_binding(binding)
        lease_id = "lease:" + uuid.uuid4().hex
        expires = iso_utc(observed + timedelta(seconds=int(lease_seconds)))
        with db.db.get_connection() as conn:
            insert_pending_claim(conn, claim_id, binding, observed)
            revision = lease_claim_row(
                conn, claim_id, binding,
                lease_id=lease_id, worker_id=worker_id,
                expires=expires, now=observed,
            )
        if revision is None:
            return self.idle()
        return accepted_fix_promotion_claim(
            binding,
            claim_id=claim_id,
            lease_id=lease_id,
            worker_id=worker_id,
            expires=expires,
            revision=revision,
        )

    def complete(self, claim: RedDogFixPromotionClaim, *, now: datetime | None = None) -> bool:
        return self._finish(claim, STATUS_APPLIED, utc(now))

    def release(self, claim: RedDogFixPromotionClaim, *, now: datetime | None = None) -> bool:
        return self._finish(claim, "PENDING", utc(now))

    def renew(
        self,
        claim: RedDogFixPromotionClaim,
        *,
        now: datetime | None = None,
        lease_seconds: int = 900,
    ) -> bool:
        observed = utc(now)
        if not 30 <= int(lease_seconds) <= 900:
            return False
        db = self._db()
        ensure_claim_table(db)
        with db.db.get_connection() as conn:
            cursor = conn.execute(
                "UPDATE reddog_fix_promotion_claims SET lease_expires_at = ?, "
                "updated_at = ? WHERE claim_id = ? "
                "AND status = 'CLAIMED' AND lease_id = ? AND lease_owner = ? "
                "AND revision = ? AND lease_expires_at > ?",
                (
                    iso_utc(observed + timedelta(seconds=int(lease_seconds))),
                    iso_utc(observed), claim.claim_id, claim.lease_id,
                    claim.lease_owner, claim.claim_revision, iso_utc(observed),
                ),
            )
        return cursor.rowcount == 1

    def idle(self, *reasons: str) -> RedDogFixPromotionClaim:
        return RedDogFixPromotionClaim(
            accepted=False,
            status=CLAIM_IDLE,
            rejection_reasons=tuple(reasons),
        )

    def _finish(self, claim: RedDogFixPromotionClaim, status: str, now: datetime) -> bool:
        if not claim.accepted or not claim.claim_id or not claim.lease_id:
            return False
        db = self._db()
        ensure_claim_table(db)
        with db.db.get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE reddog_fix_promotion_claims
                SET status = ?, lease_id = NULL, lease_owner = NULL,
                    lease_expires_at = NULL, revision = revision + 1, updated_at = ?
                WHERE claim_id = ? AND status = 'CLAIMED' AND lease_id = ?
                  AND lease_owner = ? AND revision = ? AND lease_expires_at > ?
                """,
                (
                    status, iso_utc(now), claim.claim_id, claim.lease_id,
                    claim.lease_owner, claim.claim_revision, iso_utc(now),
                ),
            )
        return cursor.rowcount == 1

    def _db(self) -> Any:
        if self._factory is not None:
            return self._factory()
        from modules.infrastructure.database.src.agent_db import AgentDB
        return AgentDB()


__all__ = [
    "AgentDbFixPromotionClaimStore",
    "CLAIM_IDLE",
    "CLAIM_READY",
    "RedDogFixPromotionClaim",
]
