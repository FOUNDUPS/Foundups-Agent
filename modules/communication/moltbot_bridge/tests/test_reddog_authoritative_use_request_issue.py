"""Extraction compatibility at an inert provider/signature boundary."""

from types import SimpleNamespace

import pytest

from modules.communication.moltbot_bridge.tests.test_reddog_authoritative_use_request_preparation import (
    _api, _case, _expected, _quiet, owner,
)


def _observe(case, monkeypatch, fault=None, interrupt=None, suppress=False):
    trace, requests = [], []
    grant, response, lease = {}, object(), object()
    def event(name):
        trace.append(name)
        if fault == name:
            raise interrupt if interrupt is not None else RuntimeError("inert")

    def clock():
        event("clock")
        return 1000.9
    real_builder = owner.build_authoritative_use_lease_request
    def build(*args, **kwargs):
        event("build")
        return real_builder(*args, **kwargs)

    class Provider:
        def issue_grant(self, request):
            with self.lease(request) as issued:
                result = issued
            return result
        def lease(self, request):
            event("lease")
            requests.append(request)
            return self
        def __enter__(self):
            event("enter")
            return None if fault == "grant" else grant
        def __exit__(self, exc_type, exc, tb):
            event("exit")
            requests.append(exc)
            return suppress

    def sign(request, received):
        event("sign")
        assert request is requests[0] and received is grant
        return response

    def rehydrate(**kwargs):
        event("rehydrate")
        assert kwargs == dict(request=requests[0], response=response,
                              current_generation_authority=case.issuer.current_generation_authority,
                              replay_store=case.store, now_epoch=1000)
        assert kwargs["request"] is requests[0]
        return lease

    monkeypatch.setattr(owner, "time", SimpleNamespace(time=clock))
    monkeypatch.setattr(owner, "build_authoritative_use_lease_request", build)
    monkeypatch.setattr(owner, "_rehydrate_external_authoritative_use_lease", rehydrate)
    case.issuer = owner.ExternalSignerAuthoritativeUseLeaseIssuer(
        SimpleNamespace(sign_with_secret_grant=sign), Provider(), case.store,
        case.issuer.current_generation_authority,
    )
    return trace, requests, lease


def test_issue_reuses_preparation_with_original_clock_and_identity(tmp_path, monkeypatch):
    case = _case(tmp_path, monkeypatch)
    prepare = _api(case)
    expected = prepare(payload=case.payload, authority_tier="HIGH")
    original = type(case.issuer).prepare_request
    trace, requests, sentinel = _observe(case, monkeypatch)
    prepared = []

    def record(self, **kwargs):
        trace.append("prepare")
        result = original(self, **kwargs)
        prepared.append(result)
        return result

    monkeypatch.setattr(type(case.issuer), "prepare_request", record)
    assert case.issuer.issue(payload=case.payload, authority_tier="HIGH") is sentinel
    assert trace == ["clock", "prepare", "build", "lease", "enter", "exit", "sign", "rehydrate"]
    assert requests[0] is prepared[0] and requests[0].to_dict() == expected.to_dict() == _expected(case.payload)
    assert requests[1] is None
    _quiet(case)


@pytest.mark.parametrize("fault,expected", [
    ("clock", ["clock"]),
    ("build", ["clock", "build"]),
    ("lease", ["clock", "build", "lease"]),
    ("enter", ["clock", "build", "lease", "enter"]),
    ("grant", ["clock", "build", "lease", "enter", "exit"]),
    ("sign", ["clock", "build", "lease", "enter", "exit", "sign"]),
    ("rehydrate", ["clock", "build", "lease", "enter", "exit", "sign", "rehydrate"]),
    ("exit", ["clock", "build", "lease", "enter", "exit"]),
], ids=["clock", "construction", "lease", "enter", "grant", "sign", "rehydrate", "exit"])
def test_issue_preserves_fail_closed_order_and_cleanup(tmp_path, monkeypatch, fault, expected):
    case = _case(tmp_path, monkeypatch)
    trace, _, _ = _observe(case, monkeypatch, fault)
    assert case.issuer.issue(payload=case.payload, authority_tier="HIGH") is None
    assert trace == expected
    _quiet(case)


def test_issue_invalid_payload_still_samples_clock_before_construction(tmp_path, monkeypatch):
    case = _case(tmp_path, monkeypatch)
    trace, _, _ = _observe(case, monkeypatch)
    payload = dict(case.payload)
    payload.pop("lease_nonce")
    assert case.issuer.issue(payload=payload, authority_tier="HIGH") is None
    assert trace == ["clock", "build"]
    _quiet(case)


@pytest.mark.parametrize("suppress", [False, True])
def test_issue_preserves_interrupt_and_context_suppression(tmp_path, monkeypatch, suppress):
    """An exited provider context cannot suppress target interruptions."""
    case = _case(tmp_path, monkeypatch)
    error = KeyboardInterrupt("inert")
    trace, requests, _ = _observe(case, monkeypatch, "sign", error, suppress)
    with pytest.raises(KeyboardInterrupt) as caught:
        case.issuer.issue(payload=case.payload, authority_tier="HIGH")
    assert caught.value is error
    assert trace == ["clock", "build", "lease", "enter", "exit", "sign"]
    assert requests[1] is None
    _quiet(case)
