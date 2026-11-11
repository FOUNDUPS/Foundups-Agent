"""Inspect and edit raw draft MIME without reserializing any retained bytes."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from email import policy
from email.errors import MessageError
from email.message import EmailMessage
from email.parser import BytesParser

from modules.communication.moltbot_bridge.src.reddog_recipient_preflight import (
    normalize_address,
)

MAX_RAW_BYTES = 35 * 1024 * 1024
_MAX_HEADER_BYTES = 128 * 1024
_MAX_PARTS = 256
_HEADER_END = re.compile(rb"\r\n\r\n|\n\n")
_HEADER_NAME = re.compile(rb"[!-9;-~]+")
_DOT_ATOM = r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+"
_DOMAIN_LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
_MAILBOX = re.compile(rf"{_DOT_ATOM}(?:\.{_DOT_ATOM})*@{_DOMAIN_LABEL}(?:\.{_DOMAIN_LABEL})+")
_RECIPIENT_HEADERS = ("To", "Cc", "Bcc")
_ADDITIONAL_SENDER_HEADERS = (
    "Return-Path",
    "X-Sender",
    "X-Original-From",
    "DKIM-Signature",
    "ARC-Message-Signature",
)
_MIME_HEADERS = (
    "Content-Type",
    "Content-Disposition",
    "Content-ID",
    "Content-Location",
    "Content-Transfer-Encoding",
)
_ATTACHMENT_ENCODINGS = {"7bit", "8bit", "binary", "base64", "quoted-printable"}


class MimeHold(ValueError):
    """A fixed reason that never includes raw MIME or an address."""


@dataclass(frozen=True, repr=False)
class DraftMime:
    sender: str
    recipients: dict[str, tuple[str, ...]]
    attachment_manifest: tuple[dict[str, str | int | bool], ...]
    digest: str
    retained_digest: str
    sender_metadata_conflicts: tuple[str, ...]


def _mailbox(address: str) -> str:
    if not isinstance(address, str) or len(address) > 254 or not _MAILBOX.fullmatch(address):
        raise MimeHold("UNSUPPORTED_DRAFT_MAILBOX")
    if len(address.partition("@")[0]) > 64:
        raise MimeHold("UNSUPPORTED_DRAFT_MAILBOX")
    return normalize_address(address)


def _from_span(raw: bytes) -> tuple[int, int]:
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_RAW_BYTES:
        raise MimeHold("INVALID_DRAFT_MIME_SIZE")
    separator = _HEADER_END.search(raw, 0, _MAX_HEADER_BYTES + 4)
    if separator is None or separator.start() > _MAX_HEADER_BYTES:
        raise MimeHold("INVALID_DRAFT_HEADERS")

    newline = separator.group()[:len(separator.group()) // 2]
    start = 0
    from_start = from_end = None
    for line in raw[:separator.start()].split(newline):
        end = start + len(line)
        if not line or b"\r" in line or b"\n" in line or b"\x00" in line:
            raise MimeHold("INVALID_DRAFT_HEADERS")
        if line.startswith((b" ", b"\t")):
            if start == 0:
                raise MimeHold("INVALID_DRAFT_HEADERS")
            if from_end is not None and from_end + len(newline) == start:
                from_end = end
        else:
            name, colon, _ = line.partition(b":")
            if not colon or not _HEADER_NAME.fullmatch(name):
                raise MimeHold("INVALID_DRAFT_HEADERS")
            if name.lower() == b"from":
                if from_start is not None:
                    raise MimeHold("AMBIGUOUS_DRAFT_FROM")
                from_start, from_end = start, end
        start = end + len(newline)
    if from_start is None or from_end is None:
        raise MimeHold("AMBIGUOUS_DRAFT_FROM")
    return from_start, from_end


def _header(message: EmailMessage, name: str):
    values = message.get_all(name, ())
    if len(values) > 1 or (values and getattr(values[0], "defects", ())):
        raise MimeHold("INVALID_DRAFT_HEADERS")
    return values[0] if values else None


def _addresses(message: EmailMessage, name: str, *, singleton: bool = False) -> tuple[str, ...]:
    header = _header(message, name)
    if header is None:
        return ()
    if singleton and (
        len(header.addresses) != 1 or any(group.display_name is not None for group in header.groups)
    ):
        raise MimeHold("AMBIGUOUS_DRAFT_FROM")
    return tuple(_mailbox(address.addr_spec) for address in header.addresses)


def _sender_conflicts(message: EmailMessage, approved_sender: str) -> tuple[str, ...]:
    conflicts = []
    for name in ("Reply-To", "Sender"):
        if name in message:
            try:
                if _addresses(message, name, singleton=True) == (approved_sender,):
                    continue
            except MimeHold:
                pass
            conflicts.append(name)
    conflicts.extend(name for name in _ADDITIONAL_SENDER_HEADERS if name in message)
    if any(name.lower().startswith("resent-") for name in message.keys()):
        conflicts.append("Resent")
    return tuple(conflicts)


def _attachments(message: EmailMessage) -> tuple[dict[str, str | int | bool], ...]:
    manifest = []
    for index, part in enumerate(message.walk()):
        if index >= _MAX_PARTS or part.defects:
            raise MimeHold("INVALID_DRAFT_MIME")
        for name in _MIME_HEADERS:
            _header(part, name)
        disposition = part.get_content_disposition()
        inline = disposition == "inline" or "Content-ID" in part or "Content-Location" in part
        if not (inline or disposition == "attachment" or part.get_filename() is not None):
            continue
        encoding = str(part.get("Content-Transfer-Encoding", "7bit")).strip().lower()
        payload = part.get_payload(decode=True)
        if encoding not in _ATTACHMENT_ENCODINGS or payload is None or part.defects:
            raise MimeHold("UNSUPPORTED_DRAFT_ATTACHMENT")
        manifest.append({
            "content_type": part.get_content_type(),
            "size_bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "inline": inline,
        })
    return tuple(manifest)


def _inspect(raw: bytes, approved_sender: str | None) -> tuple[DraftMime, tuple[int, int]]:
    start, end = _from_span(raw)
    try:
        message = BytesParser(policy=policy.default.clone(raise_on_defect=True)).parsebytes(raw)
        senders = _addresses(message, "From", singleton=True)
        if len(senders) != 1:
            raise MimeHold("AMBIGUOUS_DRAFT_FROM")
        sender = senders[0]
        target = sender if approved_sender is None else _mailbox(approved_sender)
        for name in ("Message-ID", "In-Reply-To", "References"):
            _header(message, name)
        result = DraftMime(
            sender=sender,
            recipients={name.lower(): _addresses(message, name) for name in _RECIPIENT_HEADERS},
            attachment_manifest=_attachments(message),
            digest=hashlib.sha256(raw).hexdigest(),
            retained_digest=hashlib.sha256(raw[:start] + raw[end:]).hexdigest(),
            sender_metadata_conflicts=_sender_conflicts(message, target),
        )
    except MimeHold:
        raise
    except (MessageError, ValueError, IndexError, AttributeError, RecursionError):
        # email parser errors can contain the original data.
        raise MimeHold("INVALID_DRAFT_MIME") from None
    return result, (start, end)


def inspect_mime(raw: bytes, *, approved_sender: str | None = None) -> DraftMime:
    """Return only bounded metadata. Hashes cover exact bytes, including the MIME body."""
    return _inspect(raw, approved_sender)[0]


def rewrite_from(raw: bytes, approved_sender: str) -> bytes:
    """Return the candidate after replacing exactly one top-level From field."""
    target = _mailbox(approved_sender)
    inspected, (start, end) = _inspect(raw, target)
    if inspected.sender_metadata_conflicts:
        raise MimeHold("CONFLICTING_SENDER_METADATA")
    if inspected.sender == target:
        return raw
    colon = raw.index(b":", start, end)
    return raw[:colon + 1] + b" " + target.encode("ascii") + raw[end:]
