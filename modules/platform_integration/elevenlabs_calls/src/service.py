"""One explicit request → at most one submission from this persistent journal."""
import hashlib
from .client import ElevenLabsClient, _identifier
from .config import verify_agent
from .journal import CallJournal
from .request import CallRequest


class MessageCaller:
    def __init__(self, client: ElevenLabsClient, journal: CallJournal,
                 agent_id: str, phone_id: str):
        self.client, self.journal = client, journal
        self.agent_id, self.phone_id = _identifier(agent_id), _identifier(phone_id)

    def submit(self, request: CallRequest) -> dict:
        # Read-only configuration validation cannot create an uncertain call.
        verify_agent(self.client.agent(self.agent_id))
        fingerprint = hashlib.sha256(
            (request.fingerprint() + ":" + self.agent_id + ":" + self.phone_id).encode()
        ).hexdigest()
        won, receipt = self.journal.reserve(request.request_id, fingerprint)
        if not won:
            return {**receipt, "duplicate_suppressed": True}
        # Do not release reservation on errors, process death or KeyboardInterrupt.
        response = self.client.call(request.payload(self.agent_id, self.phone_id))
        if response.get("success") is False:
            receipt["status"] = "rejected"
        elif response.get("success") is True:
            conv_id, call_sid = response.get("conversation_id"), response.get("callSid")
            if conv_id:
                receipt["conversation_id"] = _identifier(conv_id)
            if call_sid:
                receipt["call_sid"] = _identifier(call_sid)
            receipt["status"] = "submitted"
        # Malformed/indeterminate response remains submission_unknown.
        self.journal.save(receipt)
        return receipt

    def status(self, request_id: str) -> dict:
        receipt = self.journal.get(request_id)
        if not receipt.get("conversation_id"):
            return receipt
        data = self.client.conversation(receipt["conversation_id"])
        if data.get("conversation_id") != receipt["conversation_id"]:
            raise ValueError("Conversation response identity mismatch")
        state = data.get("status")
        if state in {"initiated", "in-progress", "processing", "done", "failed"}:
            receipt["provider_status"] = state
            receipt["status"] = {"done": "ended", "failed": "failed"}.get(state, "in_progress")
        # Do not convert provider analysis/transcript into evidence of human receipt.
        self.journal.save(receipt)
        return receipt
