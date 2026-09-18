"""Offline credential-containment checks across the active OpenRouter transports."""

import io
import traceback
import urllib.error
import urllib.request
import urllib.response
from email.message import Message
from unittest.mock import Mock

import pytest
import requests

from scripts import advisory_model_once as advisory
from modules.ai_intelligence.ai_gateway.src.ai_gateway import AIGateway
from modules.communication.moltbot_bridge.src import fusion_alias_live as alias


SYNTHETIC_CREDENTIAL = "synthetic-rotation-credential"


def test_provider_config_repr_does_not_disclose_credential(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", SYNTHETIC_CREDENTIAL)
    gateway = AIGateway()
    assert SYNTHETIC_CREDENTIAL not in repr(gateway.providers)


def test_advisory_error_body_and_reason_never_enter_diagnostics():
    body = Mock(spec=["read", "close"])
    body.read.side_effect = AssertionError("error body must remain unread")
    error = urllib.error.HTTPError(
        advisory.OPENROUTER_URL, 401, SYNTHETIC_CREDENTIAL, {}, body
    )
    result = advisory._http_failure_reason(error)
    assert result["http_status"] == 401
    assert result["detail"] == "Provider response withheld."
    assert SYNTHETIC_CREDENTIAL not in repr(result)
    body.read.assert_not_called()


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_advisory_redirect_cannot_forward_credentials_or_make_second_request(monkeypatch, status):
    calls = []

    class FakeHTTPS(urllib.request.HTTPSHandler):
        def https_open(self, request):
            calls.append(request.full_url)
            headers = Message()
            headers["Location"] = "https://redirect.invalid/receive"
            response = urllib.response.addinfourl(io.BytesIO(b""), headers, request.full_url, status)
            response.msg = "Redirect"
            return response

    monkeypatch.setattr(urllib.request, "HTTPSHandler", FakeHTTPS)
    with pytest.raises(urllib.error.HTTPError) as caught:
        advisory._post_openrouter(SYNTHETIC_CREDENTIAL, {"model": "test/model"}, 1)
    assert caught.value.code == status
    assert calls == [advisory.OPENROUTER_URL]


@pytest.mark.parametrize("error_type", [requests.RequestException, requests.Timeout])
def test_gateway_provider_exception_does_not_reach_traceback_or_logs(monkeypatch, caplog, error_type):
    monkeypatch.setenv("OPENROUTER_API_KEY", SYNTHETIC_CREDENTIAL)
    post = Mock(side_effect=error_type(SYNTHETIC_CREDENTIAL))
    monkeypatch.setattr(requests, "post", post)
    gateway = AIGateway()
    with pytest.raises(error_type) as caught:
        gateway._call_openai(gateway.providers["openrouter"], "test", "test/model")
    assert post.call_args.kwargs["allow_redirects"] is False
    assert SYNTHETIC_CREDENTIAL not in "".join(traceback.format_exception(caught.value))
    assert SYNTHETIC_CREDENTIAL not in caplog.text


def test_gateway_rejects_redirect_before_parsing_provider_body(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", SYNTHETIC_CREDENTIAL)
    response = Mock(status_code=307)
    post = Mock(return_value=response)
    monkeypatch.setattr(requests, "post", post)
    gateway = AIGateway()
    with pytest.raises(requests.RequestException, match="openrouter_request_failed"):
        gateway._call_openai(gateway.providers["openrouter"], "test", "test/model")
    response.json.assert_not_called()
    assert post.call_args.kwargs["allow_redirects"] is False


def test_alias_rejects_redirect_without_reading_body_or_weakening_authorization(monkeypatch):
    monkeypatch.setenv(alias.ENV_API_KEY, SYNTHETIC_CREDENTIAL)
    monkeypatch.setenv(alias.ENV_LIVE_FLAG, "1")
    response = Mock(status_code=307)
    post = Mock(return_value=response)
    monkeypatch.setattr(requests, "post", post)
    assert alias.run_alias_live("Explain the project").reason == alias.REASON_AUTHORIZATION_MISSING
    post.assert_not_called()
    auth = alias.LiveFusionAuthorization(True, "012", alias.EXPECTED_PURPOSE)
    result = alias.run_alias_live("Explain the project", authorization=auth)
    assert result.reason == alias.REASON_HTTP_ERROR
    assert post.call_args.kwargs["allow_redirects"] is False
    response.json.assert_not_called()
