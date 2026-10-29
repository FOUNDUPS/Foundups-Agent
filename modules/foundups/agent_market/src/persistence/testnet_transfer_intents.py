"""Durable local probe preparation; no signing, transport or reward settlement."""

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import re

from sqlalchemy import text

from ..authorization import require_authorization
from ..exceptions import NotFoundError, PermissionDeniedError, ValidationError
from .orm_models import PayoutRow, TaskRow, TestnetTransferIntentRow
from .sqlite_adapter import _payout_history

_PURPOSE, _LIMIT = "TEST_TRANSPORT_PROBE", 2**63 - 1
_TEXT_COLUMNS = ("intent_id", "payout_id", "purpose", "state", "foundup_id", "task_id",
                 "actor_id", "identity_json", "identity_sha256")
_INT_COLUMNS = ("format_version", "created_at_epoch_s", "expires_at_epoch_s")
_NUMERIC = frozenset({"policy_version", "asset_id", "asset_decimals", "max_amount_atoms",
                      "max_fee_microalgos", "expires_at_epoch_s", "format_version",
                      "amount_atoms", "fee_cap_microalgos"})


@dataclass(frozen=True, slots=True)
class HostTestnetPolicy:
    """Trusted host input, never constructed from a submitted request."""

    policy_id: str
    policy_version: int
    principal_id: str
    foundup_id: str
    payout_recipient_id: str
    network: str
    genesis_id: str
    genesis_hash_hex: str
    asset_id: int
    asset_decimals: int
    sender_address: str
    expected_auth_address: str
    recipient_allowlist: frozenset[str]
    max_amount_atoms: int
    max_fee_microalgos: int
    expires_at_epoch_s: int


@dataclass(frozen=True, slots=True)
class SubmittedTestnetBinding:
    """Submitted transport identity; these fields confer no authority."""

    format_version: int
    purpose: str
    policy_id: str
    policy_version: int
    network: str
    genesis_id: str
    genesis_hash_hex: str
    asset_id: int
    asset_decimals: int
    sender_address: str
    expected_auth_address: str
    recipient_address: str
    amount_atoms: int
    fee_cap_microalgos: int
    expires_at_epoch_s: int


@dataclass(frozen=True, slots=True)
class PreparedTestnetIntent:
    """Immutable local preparation record, without a payment outcome."""

    intent_id: str
    payout_id: str
    purpose: str
    state: str
    identity_json: str
    identity_sha256: str
    created_at_epoch_s: int
    expires_at_epoch_s: int


def _require(condition, message):
    if not condition:
        raise ValidationError(f"TestNet probe intent rejected: {message}")


def _validate(policy, binding):
    """Admit builtins before serialization; field objects are never deep-copied."""
    _require(type(policy) is HostTestnetPolicy and type(binding) is SubmittedTestnetBinding,
             "exact host policy and submitted binding types required")
    p = {key: getattr(policy, key) for key in HostTestnetPolicy.__dataclass_fields__}
    b = {key: getattr(binding, key) for key in SubmittedTestnetBinding.__dataclass_fields__}
    for record in (p, b):
        for key, value in record.items():
            if key in _NUMERIC:
                minimum, maximum = (0, 19) if key == "asset_decimals" else (1, _LIMIT)
                _require(type(value) is int and minimum <= value <= maximum, f"invalid {key}")
            elif key != "recipient_allowlist":
                maximum = 128 if key.endswith("address") else 64
                _require(type(value) is str and 0 < len(value) <= maximum and value.strip(),
                         f"invalid {key}")
    allowed = p["recipient_allowlist"]
    _require(type(allowed) is frozenset and bool(allowed) and all(
        type(value) is str and 0 < len(value) <= 128 and value.strip() for value in allowed),
        "invalid host recipient allowlist")
    _require(p["network"] == "algorand-testnet" and p["genesis_id"] == "testnet-v1.0"
             and re.fullmatch("[0-9a-f]{64}", p["genesis_hash_hex"]), "unqualified network identity")
    _require(b["format_version"] == 1 and b["purpose"] == _PURPOSE, "unsupported purpose/version")
    _require(all(p[key] == b[key] for key in p.keys() & b.keys()), "policy/binding identity conflict")
    _require(b["recipient_address"] in allowed and b["amount_atoms"] <= p["max_amount_atoms"]
             and b["fee_cap_microalgos"] <= p["max_fee_microalgos"], "recipient or per-intent cap")
    p["recipient_allowlist"] = sorted(allowed)
    return p, b


def _schema(sess):
    """Qualify the real SQLite schema inside the already acquired writer fence."""
    tables = set(sess.execute(text("SELECT name FROM sqlite_master WHERE type='table' "
                                   "AND name IN ('schema_migrations','testnet_transfer_intents')")).scalars())
    _require(tables == {"schema_migrations", "testnet_transfer_intents"}, "missing qualified tables")
    _require(sess.execute(text("SELECT name FROM sqlite_master WHERE type='trigger' "
                               "AND tbl_name='testnet_transfer_intents'")).first() is None,
             "unsupported intent trigger")
    versions = list(sess.execute(text("SELECT version FROM schema_migrations ORDER BY version")).scalars())
    _require(versions == [1, 2, 3] and all(type(value) is int for value in versions), "schema version")
    columns = {row["name"]: row for row in sess.execute(text(
        "SELECT * FROM pragma_table_xinfo('testnet_transfer_intents')")).mappings()}
    _require(set(columns) == set(_TEXT_COLUMNS + _INT_COLUMNS), "intent columns")
    for name, column in columns.items():
        declared = column["type"].upper()
        affinity = "INTEGER" if "INT" in declared else "TEXT" if any(
            marker in declared for marker in ("CHAR", "CLOB", "TEXT")) else "OTHER"
        _require(affinity == ("INTEGER" if name in _INT_COLUMNS else "TEXT") and column["notnull"] == 1
                 and column["hidden"] == 0 and column["pk"] == (1 if name == "intent_id" else 0),
                 "intent column contract")
    indexes = sess.execute(text("SELECT * FROM pragma_index_list('testnet_transfer_intents')")).mappings()
    for index in indexes:
        if index["unique"] and not index["partial"]:
            keys = list(sess.execute(text("SELECT name,coll FROM pragma_index_xinfo(:name) "
                                          "WHERE key=1 ORDER BY seqno"), {"name": index["name"]}).mappings())
            if len(keys) == 2 and {key["name"] for key in keys} == {"payout_id", "purpose"} \
                    and all(key["coll"] == "BINARY" for key in keys):
                return
    _require(False, "missing unconditional payout/purpose uniqueness")


def _canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError):
        raise ValidationError("TestNet probe intent has unsupported canonical content") from None


def _identity(task, payout, event, actor, policy, binding):
    return {"format_version": 1, "purpose": _PURPOSE, "payout_id": payout.payout_id,
            "foundup_id": task.foundup_id, "task_id": task.task_id,
            "payout_recipient_id": payout.recipient_id, "actor_id": actor,
            "initiation_event_id": event.event_id,
            "initiation_payload_sha256": sha256(_canonical(event.payload).encode()).hexdigest(),
            "policy": policy, "binding": binding}


def _result(row, identity, encoded, digest, now):
    """Compare complete expected content before exposing an immutable scalar DTO."""
    for key in ("payout_id", "purpose", "format_version", "foundup_id", "task_id", "actor_id"):
        value = getattr(row, key)
        _require(type(value) is type(identity[key]) and value == identity[key], "stored intent scope")
    _require(type(row.intent_id) is str and 0 < len(row.intent_id) <= 64 and row.intent_id.strip(),
             "stored intent ID")
    _require(row.state == "PREPARED" and row.identity_json == encoded
             and row.identity_sha256 == digest, "stored intent content conflict")
    created, expiry = row.created_at_epoch_s, row.expires_at_epoch_s
    _require(type(created) is int and type(expiry) is int and 0 < created <= now < expiry <= _LIMIT
             and expiry == identity["binding"]["expires_at_epoch_s"], "stored intent time")
    return PreparedTestnetIntent(**{key: getattr(row, key) for key in PreparedTestnetIntent.__dataclass_fields__})


def _store_or_replay(adapter, sess, identity, now):
    """Write only the new intent, or compare the complete immutable prior record."""
    encoded = _canonical(identity)
    digest = sha256(encoded.encode()).hexdigest()
    rows = sess.query(TestnetTransferIntentRow).filter_by(payout_id=identity["payout_id"], purpose=_PURPOSE).all()
    _require(len(rows) <= 1, "duplicate intent history")
    if rows:
        return _result(rows[0], identity, encoded, digest, now)
    scope = {key: identity[key] for key in
             ("payout_id", "purpose", "format_version", "foundup_id", "task_id", "actor_id")}
    row = TestnetTransferIntentRow(intent_id=adapter._next_id("tprobe"), state="PREPARED", **scope,
        identity_json=encoded, identity_sha256=digest, created_at_epoch_s=now,
        expires_at_epoch_s=identity["binding"]["expires_at_epoch_s"])
    sess.add(row)
    sess.flush()
    return _result(row, identity, encoded, digest, now)


@dataclass(frozen=True, slots=True)
class TestnetTransferIntentService:
    """Opt-in host facade; local preparation never confirms or dispatches payment."""

    adapter: object
    host_policy: HostTestnetPolicy

    def prepare(
        self, payout_id: str, actor_id: str, binding: SubmittedTestnetBinding,
        *, authorization: object = None,
    ) -> PreparedTestnetIntent:
        _require(self.adapter.engine.dialect.name == "sqlite", "SQLite required")
        _require(all(type(value) is str and 0 < len(value) <= 64 and value.strip()
                     for value in (payout_id, actor_id)), "invalid payout/caller identity")
        policy, submitted = _validate(self.host_policy, binding)
        with self.adapter.session() as sess:
            sess.execute(text("BEGIN IMMEDIATE"))
            _schema(sess)
            payout = sess.get(PayoutRow, payout_id)
            if payout is None:
                raise NotFoundError(f"Payout not found: {payout_id}")
            task = sess.get(TaskRow, payout.task_id)
            _require(task is not None, "missing payout task")
            require_authorization(authorization, actor_id, task.foundup_id, "treasury")
            _require(policy["foundup_id"] == task.foundup_id
                     and policy["payout_recipient_id"] == payout.recipient_id, "policy scope")
            if policy["principal_id"] != actor_id:
                raise PermissionDeniedError("TestNet policy principal mismatch")
            clock = self.adapter._now_utc()
            _require(type(clock) is datetime and clock.tzinfo is timezone.utc, "invalid host clock")
            now = int(clock.timestamp())
            _require(0 < now < policy["expires_at_epoch_s"], "expired probe policy")
            event = _payout_history(sess, task.foundup_id).get(payout_id)
            _require(event is not None, "missing validated initiation")
            if event.actor_id != actor_id:
                raise PermissionDeniedError("TestNet caller differs from initiation actor")
            identity = _identity(task, payout, event, actor_id, policy, submitted)
            return _store_or_replay(self.adapter, sess, identity, now)
