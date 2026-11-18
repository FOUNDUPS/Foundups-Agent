from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
import hashlib

import pytest

from modules.infrastructure.foundups_mcp_bridge.src.draft_mime import (
    MimeHold,
    inspect_mime,
    rewrite_from,
)

OLD = "old@example.test"
APPROVED = "approved@example.test"
PLAIN = "こんにちは。添付をご確認ください。\nFrom: a body line"
HTML = '<p>こんにちは。</p><img src="cid:synthetic-image">'
INLINE = b"\x00\xfe\x89\x01"
ATTACHMENT = b"%PDF-synthetic\x00\x01\xff"


def _multipart_draft() -> bytes:
    draft = EmailMessage(policy=policy.SMTP)
    draft["From"] = f"テスト送信者 <{OLD}>"
    draft["To"] = "佐藤 <to@example.test>, other@example.test"
    draft["Cc"] = "cc@example.test"
    draft["Bcc"] = "bcc@example.test"
    draft["Subject"] = "【確認中】添付資料"
    draft["Reply-To"] = APPROVED
    draft["Message-ID"] = "<current@example.test>"
    draft["In-Reply-To"] = "<previous@example.test>"
    draft["References"] = "<root@example.test> <previous@example.test>"
    draft["X-Draft-Warning"] = "synthetic marker"
    draft.set_content(PLAIN, cte="quoted-printable")
    draft.add_alternative(HTML, subtype="html")
    draft.get_payload()[1].add_related(
        INLINE, maintype="image", subtype="png", cid="<synthetic-image>",
        disposition="inline",
    )
    draft.add_attachment(
        ATTACHMENT, maintype="application", subtype="pdf", filename="資料.pdf",
    )
    return draft.as_bytes()


def test_only_from_changes_in_japanese_multipart_draft():
    raw = _multipart_draft()
    before = inspect_mime(raw, approved_sender=APPROVED)
    changed = rewrite_from(raw, APPROVED)
    after = inspect_mime(changed, approved_sender=APPROVED)
    first_header, retained = raw.split(b"\r\nTo:", 1)
    assert first_header.startswith(b"From:")
    assert changed == b"From: approved@example.test\r\nTo:" + retained
    assert before.sender == OLD
    assert after.sender == APPROVED
    assert before.digest == hashlib.sha256(raw).hexdigest()
    assert after.digest == hashlib.sha256(changed).hexdigest()
    assert before.retained_digest == after.retained_digest
    assert before.recipients == after.recipients == {
        "to": ("to@example.test", "other@example.test"),
        "cc": ("cc@example.test",),
        "bcc": ("bcc@example.test",),
    }
    assert before.attachment_manifest == after.attachment_manifest == (
        {"content_type": "image/png", "size_bytes": len(INLINE),
         "sha256": hashlib.sha256(INLINE).hexdigest(), "inline": True},
        {"content_type": "application/pdf", "size_bytes": len(ATTACHMENT),
         "sha256": hashlib.sha256(ATTACHMENT).hexdigest(), "inline": False},
    )
    parsed = BytesParser(policy=policy.default).parsebytes(changed)
    assert parsed.get_body(preferencelist=("plain",)).get_content().splitlines() == PLAIN.splitlines()
    assert parsed.get_body(preferencelist=("html",)).get_content().strip() == HTML
    assert parsed["Subject"] == "【確認中】添付資料"
    assert parsed["Message-ID"] == "<current@example.test>"
    assert parsed["In-Reply-To"] == "<previous@example.test>"
    assert parsed["References"] == "<root@example.test> <previous@example.test>"
    assert parsed["Reply-To"] == APPROVED
    assert parsed["X-Draft-Warning"] == "synthetic marker"


@pytest.mark.parametrize("eol", (b"\n", b"\r\n"))
def test_preserves_original_folding_elsewhere_and_body(eol):
    raw = eol.join((
        b"Subject: a folded",
        b" value",
        b"fRoM: Old Sender",
        b"\t<old@example.test>",
        b"To: to@example.test",
        b"",
        b"From: the body has a separate line",
    ))
    expected = eol.join((
        b"Subject: a folded",
        b" value",
        b"fRoM: approved@example.test",
        b"To: to@example.test",
        b"",
        b"From: the body has a separate line",
    ))
    assert rewrite_from(raw, APPROVED) == expected
    assert rewrite_from(raw, OLD) == raw


@pytest.mark.parametrize("name", ("Reply-To", "Sender"))
def test_conflicting_sender_metadata_is_reported_and_blocks_edit(name):
    raw = f"From: {OLD}\r\n{name}: different@example.test\r\n\r\ntext".encode()
    assert inspect_mime(raw, approved_sender=APPROVED).sender_metadata_conflicts == (name,)
    with pytest.raises(MimeHold, match="^CONFLICTING_SENDER_METADATA$"):
        rewrite_from(raw, APPROVED)


@pytest.mark.parametrize("header", (
    b"From: old@example.test\r\nfrom: other@example.test",
    b"From: old@example.test, other@example.test",
    b"To: to@example.test",
    b"From: Group: old@example.test;",
))
def test_ambiguous_from_is_held(header):
    with pytest.raises(MimeHold, match="^AMBIGUOUS_DRAFT_FROM$"):
        rewrite_from(header + b"\r\n\r\ntext", APPROVED)


def test_invalid_mailbox_does_not_reach_raw_output_or_error_text():
    raw = b"From: old@example.test\r\n\r\ntext"
    with pytest.raises(MimeHold, match="^UNSUPPORTED_DRAFT_MAILBOX$"):
        rewrite_from(raw, APPROVED + "\r\nBcc: hidden@example.test")


def test_invalid_attachment_encoding_holds():
    raw = (
        b"From: old@example.test\r\n"
        b"Content-Type: application/octet-stream\r\n"
        b"Content-Disposition: attachment\r\n"
        b"Content-Transfer-Encoding: base64\r\n\r\n%%%\r\n"
    )
    with pytest.raises(MimeHold, match="^INVALID_DRAFT_MIME$"):
        inspect_mime(raw)
