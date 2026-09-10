"""Atomic public RedDog state in the existing AgentDB SQLite database.

The trusted host supplies ``agent_db.db.get_connection``. SQLite is the only
verified accounting backend in this slice. No conversation text, raw address,
media, private memory, bearer, challenge, or host-owner token is retained.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import secrets
from typing import Callable

from .reddog_public_policy import (
    PublicAdmissionError, PublicPolicy, checked_clock, checked_hex,
    checked_surface, encounter_request, lick_challenge_request,
    lick_encounter_request, lick_receipt, lick_verification_evidence, turn_request,
)


HOST_LEASE_SECONDS = 60


@dataclass(frozen=True)
class PublicTurn:
    """Public-only inference input; not a private conversation capability."""

    message: str
    surface: str
    reservation_id: str
    revision: int
    next_nonce: str
    remaining_turns: int
    max_output_tokens: int
    deadline_epoch: int
    disclosure: str = "public"
    effect_ceiling: str = "NONE"


class PublicSessionGate:
    def __init__(self, connection_factory: Callable, policy: PublicPolicy | None = None,
                 host_owner: str | None = None):
        self._connect = connection_factory
        self.policy = policy or PublicPolicy()
        self.host_owner = host_owner
        if type(self.policy) is not PublicPolicy or not callable(connection_factory):
            raise PublicAdmissionError("public_configuration_invalid", 503)
        if host_owner is not None:
            try:
                checked_hex(host_owner, "host_owner")
            except PublicAdmissionError as exc:
                raise PublicAdmissionError("public_configuration_invalid", 503) from exc

    def initialize(self) -> None:
        """Trusted deployment setup only; caller never supplies a database path."""
        with self._connect() as conn:
            conn.execute("SELECT sqlite_version()")
            conn.execute("""CREATE TABLE IF NOT EXISTS reddog_public_budget_v1 (
                bucket TEXT PRIMARY KEY, day INTEGER NOT NULL, used INTEGER NOT NULL)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS reddog_public_session_v1 (
                token_hash TEXT PRIMARY KEY, encounter TEXT NOT NULL,
                surface TEXT NOT NULL, origin TEXT NOT NULL, subject TEXT NOT NULL,
                actor_claim TEXT NOT NULL, created INTEGER NOT NULL,
                last_seen INTEGER NOT NULL, revision INTEGER NOT NULL,
                nonce TEXT NOT NULL, busy TEXT, closed INTEGER NOT NULL DEFAULT 0)""")
            self._ensure_session_columns(conn)
            conn.execute("""CREATE TABLE IF NOT EXISTS reddog_lick_open_v1 (
                token_hash TEXT PRIMARY KEY,
                profile_id TEXT NOT NULL, display_name TEXT,
                challenge_hash TEXT NOT NULL, challenge_complete INTEGER NOT NULL DEFAULT 0,
                consent_version TEXT NOT NULL,
                FOREIGN KEY(token_hash) REFERENCES reddog_public_session_v1(token_hash))""")
            conn.execute("""CREATE TABLE IF NOT EXISTS reddog_public_host_lease_v1 (
                owner_hash TEXT PRIMARY KEY, started INTEGER NOT NULL,
                lease_until INTEGER NOT NULL)""")
            conn.commit()

    @staticmethod
    def _ensure_session_columns(conn) -> None:
        names = {row["name"] for row in conn.execute(
            "PRAGMA table_info(reddog_public_session_v1)"
        ).fetchall()}
        if "busy_owner" not in names:
            conn.execute("ALTER TABLE reddog_public_session_v1 ADD COLUMN busy_owner TEXT")

    @contextmanager
    def _transaction(self, now: int):
        checked_clock(now)
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                clock = conn.execute(
                    "SELECT used FROM reddog_public_budget_v1 WHERE bucket='clock'"
                ).fetchone()
                if clock and now < clock["used"]:
                    raise PublicAdmissionError("public_clock_rollback", 503)
                conn.execute("""INSERT INTO reddog_public_budget_v1 VALUES ('clock',-1,?)
                    ON CONFLICT(bucket) DO UPDATE SET used=excluded.used""", (now,))
                yield conn
                conn.commit()
            except BaseException:
                conn.rollback()
                raise

    def register_host(self, *, now: int) -> int:
        """Register one process owner exactly once; raw owner material is never stored."""
        owner, lease_until = self._configured_owner_hash(), now + HOST_LEASE_SECONDS
        with self._transaction(now) as conn:
            result = conn.execute("""INSERT INTO reddog_public_host_lease_v1
                (owner_hash,started,lease_until) VALUES (?,?,?)
                ON CONFLICT(owner_hash) DO NOTHING""", (owner, now, lease_until))
            if result.rowcount != 1:
                raise PublicAdmissionError("public_host_owner_reused", 503)
        return lease_until

    def renew_host(self, *, now: int) -> int:
        """Renew only an unexpired owner lease; a stalled host cannot resurrect itself."""
        owner, lease_until = self._configured_owner_hash(), now + HOST_LEASE_SECONDS
        with self._transaction(now) as conn:
            result = conn.execute("""UPDATE reddog_public_host_lease_v1
                SET lease_until=? WHERE owner_hash=? AND lease_until>?""",
                                  (lease_until, owner, now))
            if result.rowcount != 1:
                raise PublicAdmissionError("public_host_lease_expired", 503)
        return lease_until

    def reclaim_orphaned_turns(self, *, now: int) -> int:
        """Release only busy slots whose recorded host lease is no longer active."""
        with self._transaction(now) as conn:
            self._require_host(conn, now)
            result = conn.execute("""UPDATE reddog_public_session_v1
                SET busy=NULL,busy_owner=NULL WHERE busy IS NOT NULL
                AND busy_owner IS NOT NULL AND NOT EXISTS (
                    SELECT 1 FROM reddog_public_host_lease_v1 h
                    WHERE h.owner_hash=reddog_public_session_v1.busy_owner
                    AND h.lease_until>?)""", (now,))
        return result.rowcount

    def _configured_owner_hash(self) -> str:
        if self.host_owner is None:
            raise PublicAdmissionError("public_host_lease_unconfigured", 503)
        return self._hash_hex(self.host_owner, "host_owner")

    def _owner_or_none(self) -> str | None:
        return self._configured_owner_hash() if self.host_owner is not None else None

    def _require_host(self, conn, now: int) -> None:
        if self.host_owner is None:
            return
        row = conn.execute("""SELECT lease_until FROM reddog_public_host_lease_v1
            WHERE owner_hash=?""", (self._configured_owner_hash(),)).fetchone()
        if not row or row["lease_until"] <= now:
            raise PublicAdmissionError("public_host_lease_expired", 503)

    def _spend(self, conn, bucket: str, now: int, maximum: int) -> None:
        day = now // 86400
        conn.execute("""INSERT INTO reddog_public_budget_v1 VALUES (?,?,0)
            ON CONFLICT(bucket) DO UPDATE SET day=excluded.day, used=0
            WHERE reddog_public_budget_v1.day < excluded.day""", (bucket, day))
        changed = conn.execute("""UPDATE reddog_public_budget_v1 SET used=used+1
            WHERE bucket=? AND day=? AND used < ?""", (bucket, day, maximum))
        if changed.rowcount != 1:
            raise PublicAdmissionError("public_daily_quota_exhausted", 429)

    def _cleanup(self, conn, now: int) -> None:
        conn.execute("DELETE FROM reddog_public_budget_v1 WHERE day>=0 AND day<?",
                     (now // 86400 - 1,))
        conn.execute("""DELETE FROM reddog_lick_open_v1 WHERE token_hash IN (
            SELECT token_hash FROM reddog_public_session_v1
            WHERE busy IS NULL AND (closed=1 OR created<=? OR last_seen<=?))""",
                     (now - self.policy.session_seconds, now - self.policy.idle_seconds))
        conn.execute("""DELETE FROM reddog_public_session_v1
            WHERE busy IS NULL AND (closed=1 OR created<=? OR last_seen<=?)""",
                     (now - self.policy.session_seconds, now - self.policy.idle_seconds))

    def open_encounter(self, *, surface: str, origin: str, subject: str,
                       body: dict, now: int) -> dict:
        checked_surface(surface, origin)
        checked_hex(subject, "subject")
        claim = encounter_request(body)
        token, encounter, nonce = secrets.token_hex(32), secrets.token_hex(16), secrets.token_hex(32)
        with self._transaction(now) as conn:
            self._require_host(conn, now)
            self._cleanup(conn, now)
            self._spend(conn, "sessions:global", now, self.policy.global_sessions_daily)
            self._spend(conn, "sessions:" + subject, now, self.policy.subject_sessions_daily)
            conn.execute("""INSERT INTO reddog_public_session_v1
                (token_hash,encounter,surface,origin,subject,actor_claim,created,last_seen,revision,nonce)
                VALUES (?,?,?,?,?,?,?,?,0,?)""",
                         (self._hash(token), encounter, surface, origin, subject, claim, now, now, nonce))
        return {"token": token, "nonce": nonce, "revision": 0,
                "remaining_turns": self.policy.session_turns,
                "lick": lick_verification_evidence(encounter, claim, now + self.policy.session_seconds)}

    def open_lick_encounter(self, *, surface: str, origin: str, subject: str,
                            body: dict, now: int) -> dict:
        """Start an opt-in Lick; the returned challenge grants no turn access."""
        checked_surface(surface, origin)
        checked_hex(subject, "subject")
        claim, display_name = lick_encounter_request(body)
        token, encounter = secrets.token_hex(32), secrets.token_hex(16)
        turn_nonce, challenge = secrets.token_hex(32), secrets.token_hex(32)
        profile_id = "lick_" + secrets.token_hex(16)
        with self._transaction(now) as conn:
            self._require_host(conn, now)
            self._cleanup(conn, now)
            self._spend(conn, "sessions:global", now, self.policy.global_sessions_daily)
            self._spend(conn, "sessions:" + subject, now, self.policy.subject_sessions_daily)
            self._insert_lick(conn, token, encounter, surface, origin, subject,
                              claim, now, turn_nonce, profile_id, display_name,
                              challenge, body["consent_version"])
        return {"token": token, "challenge": challenge, "encounter_id": encounter,
                "state": "challenge_pending", "expires_at": now + self.policy.session_seconds,
                "identity_state": "provisional", "authority_granted": "none"}

    def _insert_lick(self, conn, token, encounter, surface, origin, subject,
                     claim, now, turn_nonce, profile_id, display_name,
                     challenge, consent_version) -> None:
        token_hash = self._hash(token)
        conn.execute("""INSERT INTO reddog_public_session_v1
            (token_hash,encounter,surface,origin,subject,actor_claim,created,last_seen,revision,nonce)
            VALUES (?,?,?,?,?,?,?,?,0,?)""",
                     (token_hash, encounter, surface, origin, subject, claim, now, now, turn_nonce))
        conn.execute("""INSERT INTO reddog_lick_open_v1
            (token_hash,profile_id,display_name,challenge_hash,consent_version)
            VALUES (?,?,?,?,?)""",
                     (token_hash, profile_id, display_name,
                      hashlib.sha256(challenge.encode("ascii")).hexdigest(), consent_version))

    def complete_lick_challenge(self, *, surface: str, origin: str, subject: str,
                                token: str, body: dict, now: int) -> dict:
        """Consume one randomized challenge and issue a non-authoritative receipt."""
        challenge = lick_challenge_request(body)
        with self._transaction(now) as conn:
            self._require_host(conn, now)
            session = self._session(conn, token, surface, origin, subject)
            self._check_active(session, now)
            token_hash = self._hash(token)
            row = conn.execute("SELECT * FROM reddog_lick_open_v1 WHERE token_hash=?",
                               (token_hash,)).fetchone()
            supplied = hashlib.sha256(challenge.encode("ascii")).hexdigest()
            if not row or row["challenge_complete"] or not secrets.compare_digest(
                    supplied, row["challenge_hash"]):
                raise PublicAdmissionError("lick_challenge_rejected", 409)
            conn.execute("""UPDATE reddog_lick_open_v1 SET challenge_complete=1,
                challenge_hash='' WHERE token_hash=?""", (token_hash,))
            return {"nonce": session["nonce"], "revision": session["revision"],
                    "remaining_turns": self.policy.session_turns - session["revision"],
                    "state": "ready", "lick_receipt": lick_receipt(
                        encounter=session["encounter"], profile_id=row["profile_id"],
                        claim=session["actor_claim"], display_name=row["display_name"],
                        surface=session["surface"], issued=now,
                        expires=session["created"] + self.policy.session_seconds)}

    @staticmethod
    def _hash_hex(value: str, field: str) -> str:
        checked_hex(value, field)
        return hashlib.sha256(value.encode("ascii")).hexdigest()

    @classmethod
    def _hash(cls, token: str) -> str:
        return cls._hash_hex(token, "session")

    def _session(self, conn, token: str, surface: str, origin: str, subject: str):
        checked_surface(surface, origin)
        checked_hex(subject, "subject")
        row = conn.execute("SELECT * FROM reddog_public_session_v1 WHERE token_hash=?",
                           (self._hash(token),)).fetchone()
        if not row or row["closed"] or (row["surface"], row["origin"], row["subject"]) != (surface, origin, subject):
            raise PublicAdmissionError("public_session_denied", 403)
        return row

    def session_status(self, *, surface: str, origin: str, subject: str,
                       token: str, now: int) -> dict:
        """Recover current admission state without replies or authority."""
        with self._transaction(now) as conn:
            self._require_host(conn, now)
            row = self._session(conn, token, surface, origin, subject)
            self._check_active(row, now)
            return {"revision": row["revision"], "nonce": row["nonce"],
                    "remaining_turns": max(0, self.policy.session_turns - row["revision"]),
                    "in_flight": row["busy"] is not None,
                    "expires_at": row["created"] + self.policy.session_seconds,
                    "idle_expires_at": row["last_seen"] + self.policy.idle_seconds,
                    "server_time": now, "disclosure": "public", "effect_ceiling": "NONE"}

    def reserve_turn(self, *, surface: str, origin: str, subject: str,
                     token: str, body: dict, now: int) -> PublicTurn:
        nonce, revision, message = turn_request(body, self.policy)
        reservation, next_nonce = secrets.token_hex(32), secrets.token_hex(32)
        with self._transaction(now) as conn:
            self._require_host(conn, now)
            row = self._session(conn, token, surface, origin, subject)
            lick = conn.execute("SELECT challenge_complete FROM reddog_lick_open_v1 WHERE token_hash=?",
                                (self._hash(token),)).fetchone()
            if lick and not lick["challenge_complete"]:
                raise PublicAdmissionError("lick_challenge_required", 403)
            self._check_turn(row, nonce, revision, now)
            count = conn.execute("SELECT COUNT(*) AS n FROM reddog_public_session_v1 WHERE busy IS NOT NULL").fetchone()
            if count["n"] >= self.policy.concurrent_calls:
                raise PublicAdmissionError("public_concurrency_exhausted", 429)
            self._spend(conn, "turns:global", now, self.policy.global_turns_daily)
            self._spend(conn, "turns:" + subject, now, self.policy.subject_turns_daily)
            conn.execute("""UPDATE reddog_public_session_v1 SET revision=revision+1,
                nonce=?,busy=?,busy_owner=?,last_seen=? WHERE token_hash=?""",
                         (next_nonce, reservation, self._owner_or_none(), now, self._hash(token)))
        return PublicTurn(message, surface, reservation, revision + 1, next_nonce,
                          self.policy.session_turns - revision - 1, self.policy.output_tokens,
                          min(now + self.policy.request_seconds, row["created"] + self.policy.session_seconds,
                              now + self.policy.idle_seconds))

    def _check_active(self, row, now: int) -> None:
        if now < row["last_seen"]:
            raise PublicAdmissionError("public_clock_rollback", 503)
        if now >= row["created"] + self.policy.session_seconds or now >= row["last_seen"] + self.policy.idle_seconds:
            raise PublicAdmissionError("public_session_expired", 410)

    def _check_turn(self, row, nonce: str, revision: int, now: int) -> None:
        self._check_active(row, now)
        if row["revision"] >= self.policy.session_turns:
            raise PublicAdmissionError("public_session_quota_exhausted", 429)
        if row["busy"] is not None:
            raise PublicAdmissionError("public_turn_in_flight", 409)
        if revision != row["revision"] or not secrets.compare_digest(nonce, row["nonce"]):
            raise PublicAdmissionError("public_replay_rejected", 409)

    def finish_turn(self, *, token: str, reservation_id: str, now: int) -> bool:
        """Trusted provider completion only. Never refund a failed/timed-out call."""
        checked_hex(reservation_id, "reservation")
        with self._transaction(now) as conn:
            self._require_host(conn, now)
            owner = self._owner_or_none()
            query = "UPDATE reddog_public_session_v1 SET busy=NULL,busy_owner=NULL WHERE token_hash=? AND busy=?"
            params = (self._hash(token), reservation_id)
            if owner is not None:
                query += " AND busy_owner=?"
                params += (owner,)
            result = conn.execute(query, params)
            conn.execute("""DELETE FROM reddog_lick_open_v1 WHERE token_hash IN (
                SELECT token_hash FROM reddog_public_session_v1
                WHERE token_hash=? AND closed=1 AND busy IS NULL)""", (self._hash(token),))
            conn.execute("DELETE FROM reddog_public_session_v1 WHERE token_hash=? AND closed=1 AND busy IS NULL",
                         (self._hash(token),))
        return result.rowcount == 1

    def delivery_allowed(self, *, token: str, revision: int, now: int) -> bool:
        """Recheck expiry, withdrawal, revision, and host lease before delivery."""
        with self._transaction(now) as conn:
            try:
                self._require_host(conn, now)
            except PublicAdmissionError:
                return False
            row = conn.execute("SELECT * FROM reddog_public_session_v1 WHERE token_hash=?",
                               (self._hash(token),)).fetchone()
            return bool(row and not row["closed"] and row["revision"] == revision
                        and now < row["created"] + self.policy.session_seconds
                        and now < row["last_seen"] + self.policy.idle_seconds)

    def withdraw(self, *, surface: str, origin: str, subject: str,
                 token: str, now: int) -> dict:
        with self._transaction(now) as conn:
            self._require_host(conn, now)
            row = self._session(conn, token, surface, origin, subject)
            conn.execute("""UPDATE reddog_public_session_v1 SET closed=1,
                actor_claim='withdrawn', nonce='' WHERE token_hash=?""", (self._hash(token),))
            if row["busy"] is None:
                conn.execute("DELETE FROM reddog_lick_open_v1 WHERE token_hash=?", (self._hash(token),))
                conn.execute("DELETE FROM reddog_public_session_v1 WHERE token_hash=?", (self._hash(token),))
        return {"encounter_id": row["encounter"], "withdrawn": True,
                "in_flight_retained_until_completion": row["busy"] is not None,
                "abuse_counters_retained": True, "authority_granted": "none"}
