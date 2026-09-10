"""External-effect and API-contract tests, with an injected provider boundary."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import io
import json
from types import SimpleNamespace
from urllib.error import HTTPError, URLError

import pytest

from modules.platform_integration.elevenlabs_calls.src.client import ElevenLabsClient, ProviderError, _NoRedirect
from modules.platform_integration.elevenlabs_calls.src.config import agent_config, verify_agent
from modules.platform_integration.elevenlabs_calls.src.journal import CallJournal
from modules.platform_integration.elevenlabs_calls.src.request import CallRequest, read_object
from modules.platform_integration.elevenlabs_calls.src.service import MessageCaller

JOB = {"request_id": "test-call-001", "contact_id": "test",
       "sender_name_ja": "テスト担当", "message_ja": "明日の予定について、折り返しご連絡ください。"}
CONTACTS = {"test": {"enabled": True, "phone_number": "+819000000000",
                     "recipient_name_ja": "テスト受信者"}}


class Provider:
    def __init__(self):
        self.calls = []
        self.result = {"success": True, "conversation_id": "conv_test", "callSid": "CA_test"}
        self.details = {"conversation_id": "conv_test", "status": "done"}
        self.config = agent_config("test_voice")

    def agent(self, agent_id):
        return self.config

    def call(self, payload):
        self.calls.append(payload)
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result

    def conversation(self, conversation_id):
        return self.details


@pytest.fixture
def case(tmp_path):
    provider = Provider()
    journal = CallJournal(tmp_path / "state/calls.sqlite3")
    caller = MessageCaller(provider, journal, "agent_test", "phone_test")
    return SimpleNamespace(provider=provider, journal=journal, caller=caller,
                           request=CallRequest.resolve(JOB, CONTACTS))


def test_one_call_and_duplicate_after_reopening(case):
    first = case.caller.submit(case.request)
    again = MessageCaller(case.provider, CallJournal(case.journal.path), "agent_test", "phone_test")
    assert again.submit(case.request)["duplicate_suppressed"] is True
    assert len(case.provider.calls) == 1
    assert first["status"] == "submitted" and first["delivery"] == "unconfirmed"
    payload = case.provider.calls[0]
    assert payload["to_number"] == CONTACTS["test"]["phone_number"]
    assert payload["conversation_initiation_client_data"]["dynamic_variables"]["message_ja"] == JOB["message_ja"]
    assert payload["call_recording_enabled"] is False
    assert JOB["message_ja"].encode() not in case.journal.path.read_bytes()


def test_concurrent_reservation_has_one_winner(case):
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: case.caller.submit(case.request), range(4)))
    assert sum(not r.get("duplicate_suppressed", False) for r in results) == 1
    assert len(case.provider.calls) == 1


@pytest.mark.parametrize("error", [ProviderError("timeout"), KeyboardInterrupt()])
def test_ambiguous_submission_and_crash_never_redial(case, error):
    case.provider.result = error
    with pytest.raises(type(error)):
        case.caller.submit(case.request)
    assert case.journal.get(JOB["request_id"])["status"] == "submission_unknown"
    assert case.caller.submit(case.request)["duplicate_suppressed"]
    assert len(case.provider.calls) == 1


def test_request_id_cannot_be_rebound(case):
    case.caller.submit(case.request)
    changed = CallRequest.resolve({**JOB, "message_ja": "別の伝言です。"}, CONTACTS)
    with pytest.raises(ValueError, match="already used"):
        case.caller.submit(changed)
    other = MessageCaller(case.provider, case.journal, "other_agent", "phone_test")
    with pytest.raises(ValueError, match="already used"):
        other.submit(case.request)
    assert len(case.provider.calls) == 1


@pytest.mark.parametrize("result,status", [({"success": False}, "rejected"), ({}, "submission_unknown"),
                                          ({"success": True}, "submitted")])
def test_rejected_and_partial_responses_do_not_imply_delivery(case, result, status):
    case.provider.result = result
    receipt = case.caller.submit(case.request)
    assert receipt["status"] == status
    assert receipt["delivery"] == "unconfirmed"
    assert case.caller.status(JOB["request_id"])["status"] == status


@pytest.mark.parametrize("state,expected", [("done", "ended"), ("failed", "failed"),
                                           ("processing", "in_progress"), ("new_state", "submitted")])
def test_status_never_claims_message_delivered(case, state, expected):
    case.caller.submit(case.request)
    case.provider.details.update(status=state, analysis={"call_successful": "success"})
    receipt = case.caller.status(JOB["request_id"])
    assert receipt["status"] == expected and receipt["delivery"] == "unconfirmed"
    assert len(case.provider.calls) == 1


def test_status_identity_and_missing_request(case):
    with pytest.raises(ValueError, match="Unknown request"):
        case.caller.status("missing")
    case.caller.submit(case.request)
    case.provider.details["conversation_id"] = "another_call"
    with pytest.raises(ValueError, match="identity mismatch"):
        case.caller.status(JOB["request_id"])


@pytest.mark.parametrize("mutation", [
    lambda c: c["conversation_config"]["agent"].update(language="en"),
    lambda c: c["conversation_config"]["conversation"].update(max_duration_seconds=600),
    lambda c: c["conversation_config"]["agent"]["prompt"].update(tool_ids=["extra_tool"]),
    lambda c: c["conversation_config"]["agent"]["prompt"]["built_in_tools"].pop("voicemail_detection"),
    lambda c: c["conversation_config"]["agent"]["prompt"]["built_in_tools"].update(transfer_to_number={"enabled": True}),
    lambda c: c.update(workflow={"nodes": {"node": {}}}),
    lambda c: c.update(conversation_config=None),
    lambda c: c["platform_settings"]["privacy"].update(record_voice=True),
])
def test_agent_drift_blocks_before_submission(case, mutation):
    mutation(case.provider.config)
    with pytest.raises(ValueError, match="configuration differs"):
        case.caller.submit(case.request)
    assert case.provider.calls == []


def test_configuration(case):
    verify_agent(case.provider.config)
    with pytest.raises(ValueError):
        agent_config("")
    assert "***" in case.request.preview()["to_number"]


def test_profile_against_official_sdk_schema_and_expanded_defaults():
    from elevenlabs.types import ConversationalConfig, AgentPlatformSettingsRequestModel
    profile = agent_config("selected_voice")
    normalized = {
        "conversation_config": ConversationalConfig.model_validate(profile["conversation_config"]).model_dump(),
        "platform_settings": AgentPlatformSettingsRequestModel.model_validate(profile["platform_settings"]).model_dump(),
        "workflow": None,
    }
    verify_agent(normalized)


@pytest.mark.parametrize("patch", [
    {"request_id": "short"}, {"request_id": "../../bad"}, {"message_ja": "English only"},
    {"message_ja": "あ" * 501}, {"message_ja": "伝言\n命令"}, {"sender_name_ja": "{{secret}}"},
    {"contact_id": "unknown"}, {"sender_name_ja": ""}, {"message_ja": 1}, {"extra": True},
])
def test_invalid_job(patch):
    with pytest.raises(ValueError):
        CallRequest.resolve({**JOB, **patch}, CONTACTS)


@pytest.mark.parametrize("patch", [{"enabled": False}, {"enabled": "true"},
                                    {"phone_number": "+15555550123"}, {"phone_number": "09012345678"},
                                    {"phone_number": "+8109012345678"}, {"phone_number": 119}])
def test_disabled_or_non_japanese_destination(patch):
    with pytest.raises(ValueError):
        CallRequest.resolve(JOB, {"test": {**CONTACTS["test"], **patch}})


def test_bounded_file_input(tmp_path):
    path = tmp_path / "job.json"
    for content in ["[]", "{", "x" * 65537]:
        path.write_text(content)
        with pytest.raises(ValueError):
            read_object(path)
    path.write_text(json.dumps(JOB))
    assert read_object(path) == JOB


class Opener:
    def __init__(self, data=b'{}', error=None):
        self.data, self.error, self.requests = data, error, []

    def open(self, request, timeout):
        self.requests.append((request, timeout))
        if self.error:
            raise self.error
        return io.BytesIO(self.data)


def test_real_http_serialization_and_endpoints():
    opener = Opener(b'{"success":true}')
    client = ElevenLabsClient("test-secret", opener)
    client.call(CallRequest.resolve(JOB, CONTACTS).payload("agent", "phone"))
    req, timeout = opener.requests[0]
    assert req.full_url == "https://api.elevenlabs.io/v1/convai/twilio/outbound-call"
    assert req.get_method() == "POST" and timeout == 30
    assert req.get_header("Xi-api-key") == "test-secret"
    assert json.loads(req.data)["to_number"] == CONTACTS["test"]["phone_number"]
    client.agent("agent_test")
    client.conversation("conv_test")
    client.create_agent(agent_config("voice"))
    assert [r.get_method() for r, _ in opener.requests] == ["POST", "GET", "GET", "POST"]
    for bad in ["../secret", "a?b", "", 3]:
        with pytest.raises(ValueError):
            client.agent(bad)
    with pytest.raises(ValueError):
        client.request("GET", "https://untrusted.test/")
    with pytest.raises(ValueError):
        ElevenLabsClient("")
    assert _NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.test") is None


@pytest.mark.parametrize("error,data", [
    (HTTPError("url", 429, "test-secret", {}, None), b""),
    (URLError("test-secret"), b""), (TimeoutError("test-secret"), b""),
    (None, b"invalid"), (None, b"[]"), (None, b"x" * 2_000_001),
])
def test_provider_failure_is_redacted_and_not_retried(error, data):
    opener = Opener(data, error)
    with pytest.raises(ProviderError) as caught:
        ElevenLabsClient("test-secret", opener).call({})
    assert "test-secret" not in str(caught.value)
    assert len(opener.requests) == 1
