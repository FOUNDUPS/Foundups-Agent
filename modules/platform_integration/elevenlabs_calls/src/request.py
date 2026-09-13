"""Resolve an exact local contact and freeze the message before any effect."""
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re


def read_object(path: str | Path) -> dict:
    with Path(path).open("rb") as stream:
        raw = stream.read(65537)
    if len(raw) > 65536:
        raise ValueError("JSON input exceeds 64 KiB")
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise ValueError("JSON input must be an object")
    return obj


def _text(value, name: str, limit: int) -> str:
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= limit:
        raise ValueError(f"{name} must contain 1–{limit} characters")
    if any(ord(c) < 32 for c in value) or "{{" in value or "}}" in value:
        raise ValueError(f"{name} contains control characters or template syntax")
    return value.strip()


@dataclass(frozen=True)
class CallRequest:
    request_id: str
    contact_id: str
    to_number: str
    recipient_name_ja: str
    sender_name_ja: str
    message_ja: str

    @classmethod
    def resolve(cls, job: dict, contacts: dict) -> "CallRequest":
        if set(job) != {"request_id", "contact_id", "sender_name_ja", "message_ja"}:
            raise ValueError("Request must contain exactly request_id, contact_id, sender_name_ja, message_ja")
        rid = _text(job["request_id"], "request_id", 80)
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{7,79}", rid):
            raise ValueError("request_id must be 8–80 ASCII letters, digits, dot, dash or underscore")
        cid = _text(job["contact_id"], "contact_id", 80)
        contact = contacts.get(cid)
        if not isinstance(contact, dict) or contact.get("enabled") is not True:
            raise ValueError("Contact is missing or disabled; resolve the intended person first")
        number = contact.get("phone_number")
        if not isinstance(number, str) or not re.fullmatch(r"\+81[1-9][0-9]{8,9}", number):
            raise ValueError("Contact must use a Japan +81 E.164 number (omit the domestic leading zero)")
        message = _text(job["message_ja"], "message_ja", 500)
        if not re.search(r"[\u3040-\u30ff\u3400-\u9fff]", message):
            raise ValueError("message_ja must be prepared Japanese text; no live translation")
        return cls(rid, cid, number,
                   _text(contact.get("recipient_name_ja"), "recipient_name_ja", 60),
                   _text(job["sender_name_ja"], "sender_name_ja", 60), message)

    def fingerprint(self) -> str:
        raw = json.dumps(asdict(self), ensure_ascii=False, sort_keys=True).encode()
        return hashlib.sha256(raw).hexdigest()

    def preview(self) -> dict:
        data = asdict(self)
        data["to_number"] = "***" + self.to_number[-4:]
        return data

    def payload(self, agent_id: str, phone_id: str) -> dict:
        return {
            "agent_id": agent_id, "agent_phone_number_id": phone_id,
            "to_number": self.to_number, "call_recording_enabled": False,
            "conversation_initiation_client_data": {"dynamic_variables": {
                "sender_name_ja": self.sender_name_ja,
                "recipient_name_ja": self.recipient_name_ja,
                "message_ja": self.message_ja,
            }},
        }
