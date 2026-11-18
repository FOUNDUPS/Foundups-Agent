"""One authorized From-only correction; Gmail remains the source of truth."""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re
import sqlite3
from threading import Lock
from time import monotonic, time

from cryptography.fernet import Fernet

from modules.communication.moltbot_bridge.src.reddog_recipient_preflight import normalize_address
from .draft_gmail import GmailError
from .draft_mime import MimeHold, inspect_mime, rewrite_from

SHA = re.compile(r"[a-f0-9]{64}")
ID = re.compile(r"[A-Za-z0-9_-]{1,128}")
MAILBOX = re.compile(r"[a-z0-9.!#$%&'*+/=?^_\x60{|}~-]+@[a-z0-9.-]+")
APPROVAL_TTL = 900
SCAN_SECONDS = 30
SCAN_BYTES = 64 * 1024 * 1024


def mailbox(value: str) -> str:
    if not isinstance(value, str) or len(value) > 254 or not MAILBOX.fullmatch(value):
        raise ValueError("invalid private mailbox binding")
    return normalize_address(value)


@dataclass(frozen=True, repr=False)
class DraftPolicy:
    account: str
    sender: str
    target_digest: str
    request_id: str | None = None
    issued_at: int | None = None
    expires_at: int | None = None

    def __post_init__(self):
        mailbox(self.account)
        mailbox(self.sender)
        if not isinstance(self.target_digest, str) or not SHA.fullmatch(self.target_digest):
            raise ValueError("invalid target digest")
        if self.request_id is self.issued_at is self.expires_at is None:
            return
        if (not isinstance(self.request_id, str) or not ID.fullmatch(self.request_id)
                or type(self.issued_at) is not int or type(self.expires_at) is not int
                or not 0 < self.expires_at - self.issued_at <= APPROVAL_TTL):
            raise ValueError("invalid private write approval")


@dataclass(frozen=True, repr=False)
class Operation:
    request_id: str
    draft_id: str
    before: str
    after: str
    message_id: str
    thread_id: str
    sender: str
    state: str = "pending"


class Hold(ValueError):
    """Fixed refusal reasons, suitable for tool outputs."""


class DraftJournal:
    """A single durable reservation, with an encrypted pre-edit snapshot.

    The directory and key are owned by the supervisor, separate from Git and
    from correspondence continuity storage. A journal is never reset by MCP.
    """

    def __init__(self, path: Path, cipher: Fernet):
        self.path = path
        self.cipher = cipher
        with closing(self._open()) as db, db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS correction (
                  slot INTEGER PRIMARY KEY CHECK (slot = 1),
                  request_id TEXT NOT NULL, draft_id TEXT NOT NULL,
                  before TEXT NOT NULL, after TEXT NOT NULL,
                  message_id TEXT NOT NULL, thread_id TEXT NOT NULL,
                  sender TEXT NOT NULL, snapshot BLOB NOT NULL,
                  state TEXT NOT NULL CHECK (state IN ('pending', 'verified'))
                )
            """)

    def _open(self):
        db = sqlite3.connect(self.path, timeout=2)
        db.execute("PRAGMA synchronous = FULL")
        return db

    def get(self) -> Operation | None:
        with closing(self._open()) as db:
            row = db.execute("""
                SELECT request_id,draft_id,before,after,message_id,thread_id,sender,state
                FROM correction WHERE slot = 1
            """).fetchone()
        return Operation(*row) if row else None

    def reserve(self, request_id, draft, before, after, sender) -> bool:
        with closing(self._open()) as db, db:
            changed = db.execute("""
                INSERT OR IGNORE INTO correction VALUES (1,?,?,?,?,?,?,?,?,'pending')
            """, (request_id, draft.draft_id, before, after, draft.message_id,
                  draft.thread_id, sender, self.cipher.encrypt(draft.raw))).rowcount
        return changed == 1

    def verified(self, op: Operation):
        with closing(self._open()) as db, db:
            db.execute("UPDATE correction SET state='verified' WHERE slot=1 AND request_id=?",
                       (op.request_id,))


class DraftCorrection:
    def __init__(self, policy: DraftPolicy, gmail, journal: DraftJournal, *, clock=time):
        self.policy = policy
        self.gmail = gmail
        self.journal = journal
        self.clock = clock
        self.lock = Lock()

    def _account(self):
        if self.gmail.get_account() != self.policy.account:
            raise Hold("wrong_account")

    def _select(self, operation):
        # Fresh provider inventory: even an identical duplicate is ambiguous.
        deadline = monotonic() + SCAN_SECONDS
        raw_bytes = 0
        ids = self.gmail.list_draft_ids()
        allowed = {self.policy.target_digest}
        if operation and operation.before == self.policy.target_digest:
            allowed.add(operation.after)
        matches = []
        for draft_id in ids:
            if monotonic() >= deadline:
                raise Hold("draft_scan_limit")
            draft = self.gmail.get_draft(draft_id)
            raw_bytes += len(draft.raw)
            if raw_bytes > SCAN_BYTES or monotonic() >= deadline:
                raise Hold("draft_scan_limit")
            if sha256(draft.raw).hexdigest() in allowed:
                matches.append(draft)
                if len(matches) > 1:
                    raise Hold("ambiguous_target")
        if not matches:
            raise Hold("target_missing_or_changed")
        target = matches[0]
        if operation and (operation.before != self.policy.target_digest
                          or operation.sender != self.policy.sender
                          or target.draft_id != operation.draft_id):
            raise Hold("journal_target_conflict")
        return target

    @staticmethod
    def _hold(reason):
        return {"status": "hold", "reason": reason}

    def _guard(self, action):
        if not self.lock.acquire(blocking=False):
            return self._hold("draft_busy")
        try:
            return action()
        except Hold as exc:
            return self._hold(str(exc))
        except GmailError as exc:
            return self._hold(exc.code)
        except MimeHold:
            return self._hold("mime_not_admitted")
        except Exception:
            # Do not put provider data, sqlite paths or an exception traceback into MCP.
            return self._hold("service_error")
        finally:
            self.lock.release()

    def inspect_draft(self):
        def inspect():
            self._account()
            draft = self._select(self.journal.get())
            mime = inspect_mime(draft.raw, approved_sender=self.policy.sender)
            return {
                "status": "inspected", "draft_id": draft.draft_id,
                "current_message_id": draft.message_id, "sender": mime.sender,
                "recipients": mime.recipients, "attachment_manifest": mime.attachment_manifest,
                "digest": mime.digest, "sender_metadata_conflicts": mime.sender_metadata_conflicts,
            }
        return self._guard(inspect)

    def set_draft_sender(self, draft_id: str, expected_digest: str, approved_sender: str,
                         request_id: str, *, dry_run: bool = True, allow_write: bool = False, confirm_write=lambda: False):
        if (not ID.fullmatch(draft_id) or not SHA.fullmatch(expected_digest)
                or not ID.fullmatch(request_id)):
            return self._hold("invalid_request")
        if approved_sender != self.policy.sender:
            return self._hold("unapproved_sender")
        if not dry_run and not allow_write:
            return self._hold("write_scope_required")
        return self._guard(lambda: self._apply(draft_id, expected_digest, request_id, dry_run, confirm_write))

    def _apply(self, draft_id, before, request_id, dry_run, confirm_write):
        self._account()
        op = self.journal.get()
        if not dry_run and op is not None:
            if (op.request_id, op.draft_id, op.before, op.sender) != (
                request_id, draft_id, before, self.policy.sender
            ):
                raise Hold("journal_reserved")
            return self._reconcile(op, "reconciled")

        if before != self.policy.target_digest:
            raise Hold("stale_digest")
        draft = self._select(op)
        if draft.draft_id != draft_id or sha256(draft.raw).hexdigest() != before:
            raise Hold("stale_or_wrong_draft")
        if self.policy.sender not in self.gmail.list_send_as():
            raise Hold("unverified_send_as")
        mime = inspect_mime(draft.raw, approved_sender=self.policy.sender)
        if mime.sender_metadata_conflicts:
            raise Hold("conflicting_sender_metadata")
        candidate = draft.raw if mime.sender == self.policy.sender else rewrite_from(draft.raw, self.policy.sender)
        proposed = inspect_mime(candidate, approved_sender=self.policy.sender)
        if proposed.retained_digest != mime.retained_digest or proposed.sender != self.policy.sender:
            raise Hold("candidate_changed_other_content")
        after = proposed.digest
        if dry_run or after == before:
            return {"status": "preview" if dry_run else "already_correct",
                    "before_digest": before, "after_digest": after, "verification_receipt": None}

        self._approval(request_id)
        if not confirm_write():
            raise Hold("write_authorization_expired")
        if not self.journal.reserve(request_id, draft, before, after, self.policy.sender):
            raise Hold("journal_reserved")
        op = self.journal.get()
        # The adapter does a final same-token read immediately before PUT.
        # A local journal cannot eliminate races with other Gmail clients.
        self._approval(request_id)
        try:
            replacement_id = self.gmail.update_draft(draft_id, candidate, draft.thread_id, expected=draft)
        except GmailError as exc:
            if exc.code != "mutation_uncertain":
                raise
            return self._reconcile(op, "reconciled")
        return self._reconcile(op, "verified", replacement_id)

    def _approval(self, request_id):
        now = self.clock()
        if (self.policy.request_id != request_id or self.policy.expires_at is None
                or not self.policy.issued_at <= now < self.policy.expires_at):
            raise Hold("private_approval_required")

    def _reconcile(self, op, status, replacement_id=None):
        if op.before != self.policy.target_digest:
            raise Hold("journal_target_conflict")
        draft = self.gmail.get_draft(op.draft_id)
        if (draft.draft_id != op.draft_id or draft.thread_id != op.thread_id
                or draft.message_id == op.message_id
                or (replacement_id is not None and draft.message_id != replacement_id)
                or sha256(draft.raw).hexdigest() != op.after
                or inspect_mime(draft.raw, approved_sender=op.sender).sender != op.sender):
            raise Hold("readback_not_verified")
        self.journal.verified(op)
        return {"status": status, "before_digest": op.before, "after_digest": op.after,
                "verification_receipt": {"request_id": op.request_id, "draft_id": op.draft_id,
                                         "current_message_id": draft.message_id,
                                         "sender_verified": True, "exact_mime_verified": True,
                                         "thread_verified": True}}
