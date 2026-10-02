"""Service-owned correspondence authority; not a ChatGPT connector interceptor.

Trusted bootstrap owns provider credentials, reconciliation and the private DB.
Untrusted composers receive only issue/execute RPCs, never bootstrap objects.
Recipient resolution/readback have exactly one owner: reddog_recipient_preflight.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import hashlib
import json
from typing import Callable, Mapping, Sequence
from uuid import uuid4

from .reddog_correspondence_state import (
    CorrespondenceState, FollowUpGate, Freshness, RedDogCorrespondenceStateStore,
    SentCoverageState, state_digest,
    _validate_state,
)
from .reddog_recipient_preflight import (
    PreflightDecision, ProposedRecipient, RecipientRole, RouteEvidence,
    normalize_address, preflight_recipients, verify_sent_readback,
    EvidenceLevel, RoutePolicy,
)

SCHEMA = "reddog.sender-boundary.v3"
MAX_TTL_SECONDS = 300
OPERATIONS = frozenset({"send_email", "reply", "send_draft", "delivery_repair",
                        "create_draft", "update_draft"})
SOURCES = frozenset({"gmail_sent", "full_thread", "drafts", "email_log",
                     "action_queue", "correspondence_routing"})
TX_KEYS = frozenset({"account_key", "scope_key", "purpose", "operation", "recipients",
                     "subject", "payload", "draft_id", "draft_message_id", "thread_id",
                     "reply_message_id", "from_address", "reply_to"})


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False)


def digest(value) -> str:
    return "sha256:" + hashlib.sha256(canonical(value).encode()).hexdigest()


def timestamp(value: str) -> float:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("NAIVE_TIMESTAMP")
    return dt.timestamp()


def _address(value: str) -> str:
    # Reject multi-address/header injection before using the canonical parser.
    if not isinstance(value, str) or any(c in value for c in "\r\n,;"):
        raise ValueError("INVALID_ADDRESS")
    address = normalize_address(value)
    if address.count("@") != 1 or any(c.isspace() for c in address):
        raise ValueError("INVALID_ADDRESS")
    return address


def transaction(value: Mapping) -> dict:
    if not isinstance(value, Mapping) or set(value) != TX_KEYS:
        raise ValueError("MALFORMED_TRANSACTION")
    tx = json.loads(canonical(dict(value)))  # detach mutable caller objects
    if tx["operation"] not in OPERATIONS:
        raise ValueError("UNKNOWN_OPERATION")
    for field in ("account_key", "scope_key", "purpose", "subject"):
        if not isinstance(tx[field], str) or not tx[field].strip():
            raise ValueError("INVALID_" + field.upper())
    for field in ("draft_id", "draft_message_id", "thread_id", "reply_message_id",
                  "from_address", "reply_to"):
        if tx[field] is not None and (not isinstance(tx[field], str) or not tx[field]):
            raise ValueError("INVALID_" + field.upper())
    if tx["operation"] in {"send_draft", "update_draft"} and not all(
        tx[f] for f in ("draft_id", "draft_message_id", "thread_id")
    ):
        raise ValueError("MISSING_DRAFT_IDENTITY")
    if tx["operation"] == "reply" and not all(tx[f] for f in ("reply_message_id", "thread_id")):
        raise ValueError("MISSING_REPLY_IDENTITY")
    if not isinstance(tx["payload"], dict) or not tx["payload"]:
        raise ValueError("INVALID_MIME_PAYLOAD")
    if not isinstance(tx["recipients"], list) or not tx["recipients"]:
        raise ValueError("EMPTY_RECIPIENT_SET")
    seen = set()
    for item in tx["recipients"]:
        if not isinstance(item, dict) or set(item) != {"identity_id", "role", "address"}:
            raise ValueError("MALFORMED_RECIPIENT")
        if not isinstance(item["identity_id"], str) or not item["identity_id"]:
            raise ValueError("INVALID_CONTACT_ID")
        RecipientRole(item["role"])
        item["address"] = _address(item["address"])
        if item["address"] in seen:
            raise ValueError("DUPLICATE_RECIPIENT")
        seen.add(item["address"])
    tx["recipients"].sort(key=lambda r: (r["role"], r["identity_id"], r["address"]))
    if not any(r["role"] == "TO" for r in tx["recipients"]):
        raise ValueError("MISSING_TO")
    return tx


@dataclass(frozen=True)
class ReconciledContext:
    # Built by trusted provider/CRM reconciliation, never supplied by composer RPC.
    intended_transaction: Mapping
    state: CorrespondenceState
    evidence: Sequence[RouteEvidence]
    source_refs: Mapping[str, str]
    sent_message_ids: tuple[str, ...] = ()
    sent_addresses: tuple[str, ...] = ()
    current_drafts: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()


def _recipients(tx):
    return tuple(ProposedRecipient(r["identity_id"], RecipientRole(r["role"]), r["address"])
                 for r in tx["recipients"])


def _context_digest(ctx: ReconciledContext) -> str:
    return digest({"state": _material_state_digest(ctx.state), "evidence": [asdict(e) for e in ctx.evidence],
                   "sources": dict(ctx.source_refs), "sent_ids": sorted(ctx.sent_message_ids),
                   "sent_addresses": sorted(_address(a) for a in ctx.sent_addresses),
                   "drafts": sorted(ctx.current_drafts), "conflicts": list(ctx.conflicts),
                   "intent": transaction(ctx.intended_transaction)})


def _material_state_digest(state: CorrespondenceState) -> str:
    # A successful fresh read may advance its check timestamp without changing
    # authority. Do not let that timestamp release a durable state reservation.
    return state_digest(replace(state, reconciled_at=""))


def _gate(tx, ctx, now):
    state = ctx.state
    _validate_state(state)
    if transaction(ctx.intended_transaction) != tx:
        raise ValueError("INTENDED_TRANSACTION_MISMATCH")
    if state.scope_key != tx["scope_key"] or ctx.conflicts:
        raise ValueError("CONFLICTING_CAPSULE")
    if set(ctx.source_refs) != SOURCES or not all(
        isinstance(v, str) and v.strip() for v in ctx.source_refs.values()
    ):
        raise ValueError("INCOMPLETE_RECONCILIATION")
    if state.freshness is not Freshness.VALID or not state.provider_watermark:
        raise ValueError("STALE_PROVIDER_STATE")
    age = now - timestamp(state.reconciled_at)
    if not 0 <= age < MAX_TTL_SECONDS:
        raise ValueError("STALE_CAPSULE")
    if state.follow_up_gate is not FollowUpGate.CLEAR:
        raise ValueError(state.follow_up_gate.value)
    if state.outbound_since_latest_inbound >= 2:
        raise ValueError("BLOCK_THIRD_FOLLOWUP")
    if state.sent_coverage_state is not SentCoverageState.NO_SENT_MATCH_IN_CHECKED_SCOPE:
        raise ValueError("BLOCK_DUPLICATE_OR_UNKNOWN_COVERAGE")
    if state.routing_state != "ALLOW" or state.next_allowed_action != "SEND":
        raise ValueError("ROUTE_OR_ACTION_BLOCKED")
    # All historical provider-Sent events count, including integrity incidents.
    if ctx.sent_message_ids or ctx.sent_addresses:
        raise ValueError("BLOCK_DUPLICATE")
    if not ctx.evidence or any(not e.source.strip() for e in ctx.evidence):
        raise ValueError("MISSING_ROUTE_PROVENANCE")
    if any(not isinstance(e.level, EvidenceLevel)
           or (e.policy is not None and not isinstance(e.policy, RoutePolicy))
           or type(e.verified) is not bool or type(e.current) is not bool
           for e in ctx.evidence):
        raise ValueError("MALFORMED_ROUTE_EVIDENCE")
    if tx["thread_id"] and tx["thread_id"] not in state.active_thread_ids:
        raise ValueError("THREAD_SCOPE_MISMATCH")


def _blocked(reason, draft=False):
    return {"decision": "HOLD" if draft else "BLOCK", "provider_invoked": False,
            "reasons": [reason]}


class CorrespondenceSenderBoundary:
    """Only this service object owns a provider submit capability.

    The host must keep constructor dependencies inaccessible to composers and
    disable all direct connector mutations. Python privacy is not an OS sandbox.
    """
    def __init__(self, *, provider, reconcile: Callable[[str, str], ReconciledContext],
                 store: RedDogCorrespondenceStateStore, clock=None):
        self.__provider = provider
        self.__reconcile = reconcile
        self.__store = store
        self.__clock = clock or (lambda: datetime.now(timezone.utc).timestamp())

    def __authorize(self, tx):
        ctx = self.__reconcile(tx["account_key"], tx["scope_key"])
        _gate(tx, ctx, self.__clock())
        receipt = preflight_recipients(_recipients(tx), ctx.evidence,
                                       already_sent_addresses=ctx.sent_addresses)
        if receipt.decision is not PreflightDecision.SEND:
            raise ValueError("RECIPIENT_PREFLIGHT_BLOCK:" + ",".join(receipt.reasons))
        return ctx, receipt

    def issue(self, proposed, *, ttl_seconds=120, dry_run=False):
        try:
            tx = transaction(proposed)
            if type(ttl_seconds) is not int or not 0 < ttl_seconds <= MAX_TTL_SECONDS:
                raise ValueError("INVALID_TTL")
            ctx, preflight = self.__authorize(tx)
            now = self.__clock()
            receipt = {"schema": SCHEMA, "decision": "SEND", "receipt_id": str(uuid4()),
                       "issued_at": now, "expires_at": now + ttl_seconds,
                       "account_key": tx["account_key"], "scope_key": tx["scope_key"],
                       "purpose": tx["purpose"], "operation": tx["operation"],
                       "thread_id": tx["thread_id"], "draft_id": tx["draft_id"],
                       "transaction_digest": digest(tx), "context_digest": _context_digest(ctx),
                       "state_digest": _material_state_digest(ctx.state),
                       "route_evidence_digest": digest([asdict(e) for e in ctx.evidence]),
                       "source_refs_digest": digest(dict(ctx.source_refs)),
                       "checks": [asdict(c) for c in preflight.checks],
                       "routing_policy_result": "ALLOW", "sent_coverage_result": "CLEAR"}
            if dry_run:
                return {"decision": "AUDIT_ONLY", "receipt": receipt}
            self.__store.register_send_receipt(receipt["receipt_id"], digest(receipt))
            return receipt
        except Exception as exc:
            return _blocked(str(exc))

    def execute(self, proposed, receipt):
        draft = isinstance(proposed, Mapping) and proposed.get("operation") in {"create_draft", "update_draft"}
        try:
            tx = transaction(proposed)
            # Snapshot once: caller mutation during provider reads cannot alter it.
            bound = json.loads(canonical(receipt))
            if not isinstance(bound, dict) or bound.get("schema") != SCHEMA:
                raise ValueError("MISSING_OR_MALFORMED_RECEIPT")
            if bound.get("decision") != "SEND":
                raise ValueError("PREFLIGHT_NOT_SEND")
            if not self.__store.authentic_send_receipt(bound["receipt_id"], digest(bound)):
                raise ValueError("UNISSUED_OR_FABRICATED_RECEIPT")
            self.__fresh(bound)
            if bound["transaction_digest"] != digest(tx):
                raise ValueError("TRANSACTION_MISMATCH")
            ctx, preflight = self.__authorize(tx)
            if _context_digest(ctx) != bound["context_digest"]:
                raise ValueError("STALE_RECONCILIATION")
            if tx["operation"] in {"send_draft", "update_draft"}:
                observed = self.__provider.read_draft(tx["account_key"], tx["draft_id"])
                if observed["draft_id"] != tx["draft_id"] or observed["message_id"] != tx["draft_message_id"]:
                    raise ValueError("DRAFT_IDENTITY_MISMATCH")
                if observed["thread_id"] != tx["thread_id"]:
                    raise ValueError("DRAFT_THREAD_MISMATCH")
                if tx["operation"] == "send_draft":
                    self.__exact(preflight, observed)
                    if observed["subject"] != tx["subject"] or observed["payload"] != tx["payload"]:
                        raise ValueError("DRAFT_CONTENT_MISMATCH")
            # Reconcile after every potentially slow read, just before claim/submit.
            latest, _ = self.__authorize(tx)
            if _context_digest(latest) != bound["context_digest"]:
                raise ValueError("STALE_RECONCILIATION")
            self.__fresh(bound)
            self.__store.claim_submission(digest(tx), digest({
                "account": tx["account_key"], "scope": tx["scope_key"],
                "state": _material_state_digest(latest.state),
            }), bound["receipt_id"])
        except Exception as exc:
            return _blocked(str(exc), draft)

        # Use only reconstructed fields; provider never expands implicit reply/all recipients.
        args = {role.value.lower(): [r.address for r in _recipients(tx) if r.role is role]
                for role in RecipientRole}
        args.update({k: tx[k] for k in TX_KEYS - {"recipients", "purpose", "scope_key"}})
        try:
            sent = self.__provider.submit(args)
        except Exception:
            return self.__finish(tx, "PROVIDER_STATE_UNKNOWN", ["RECONCILE_BEFORE_RETRY"])
        if draft:
            # Draft creation/update is gated but never promoted as Sent.
            return self.__finish(tx, "DRAFT_SAVED", [])
        try:
            if not isinstance(sent, Mapping) or not all(
                isinstance(sent.get(k), str) and sent[k] for k in ("id", "thread_id")
            ):
                raise ValueError("MISSING_PROVIDER_IDENTITY")
            readback = self.__provider.read_sent(tx["account_key"], sent["id"])
            if readback["id"] != sent["id"] or readback["thread_id"] != sent["thread_id"]:
                raise ValueError("SENT_IDENTITY_MISMATCH")
            if tx["thread_id"] and readback["thread_id"] != tx["thread_id"]:
                raise ValueError("SENT_THREAD_SCOPE_MISMATCH")
            if "SENT" not in readback["label_ids"]:
                raise ValueError("NOT_PROVIDER_SENT")
            self.__exact(preflight, readback)
        except Exception as exc:
            return self.__finish(tx, "PROVIDER_SENT_INTEGRITY_INCIDENT", [str(exc)])
        return self.__finish(tx, "VERIFIED_SENT", [], sent["id"], sent["thread_id"])

    def __fresh(self, receipt):
        start, end, now = receipt["issued_at"], receipt["expires_at"], self.__clock()
        if not 0 < end - start <= MAX_TTL_SECONDS or not start <= now < end:
            raise ValueError("STALE_RECEIPT")

    @staticmethod
    def __exact(preflight, observed):
        actual = {}
        for role in RecipientRole:
            values = observed[role.value.lower()]
            if not isinstance(values, list):
                raise ValueError("INCOMPLETE_RECIPIENT_READBACK")
            actual[role] = [_address(a) for a in values]
            if len(actual[role]) != len(set(actual[role])):
                raise ValueError("DUPLICATE_READBACK_RECIPIENT")
        result = verify_sent_readback(preflight, actual)
        if not result.ok:
            raise ValueError(",".join(result.reasons))

    def __finish(self, tx, outcome, reasons, message_id=None, thread_id=None):
        try:
            self.__store.record_submission_outcome(digest(tx), outcome, _recipients(tx))
        except Exception:
            # Claim remains durable, and persistence failure is never VERIFIED_SENT.
            outcome, reasons = "PROVIDER_STATE_UNKNOWN", ["OUTCOME_PERSISTENCE_FAILED"]
        return {"decision": outcome, "provider_invoked": True, "reasons": reasons,
                "message_id": message_id, "thread_id": thread_id}
