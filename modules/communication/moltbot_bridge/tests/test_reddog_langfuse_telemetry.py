"""Offline privacy/coverage checks for the lookup boundary, without daemon imports."""
from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
import urllib.error
import urllib.parse

import pytest

ROOT = Path(__file__).resolve().parents[4]
SPEC = importlib.util.spec_from_file_location("langfuse_lookup_test", ROOT / "modules/communication/moltbot_bridge/src/reddog_langfuse_telemetry.py")
lookup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(lookup)
TRACE = "a" * 32
START, END = "2026-11-01T00:00:00Z", "2026-11-02T00:00:00Z"
CANARY = "private-credential-canary-DO-NOT-EMIT"


def row(**extra):
    return {"id": "b" * 16, "traceId": TRACE, "startTime": START,
            "endTime": "2026-11-01T00:00:01Z", "type": "GENERATION", "level": "DEFAULT",
            "model": "qwen/qwen3-coder", "inputUsage": 3, "outputUsage": 2,
            "totalUsage": 5, "totalCost": 0.001, "latency": 1, **extra}


class Response:
    def __init__(self, value):
        self.raw = value if isinstance(value, bytes) else json.dumps(value).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self, size):
        assert size == lookup.MAX_BYTES + 1
        return self.raw[:size]


def review(payloads, **kwargs):
    iterator = iter(payloads)
    calls = []

    def transport(request, timeout):
        calls.append(request)
        assert request.method == "GET"
        return Response(next(iterator))

    return lookup.read_review(public_key="public-test", secret_key=CANARY,
                              from_time=START, to_time=END, opener=transport, **kwargs), calls


def test_allowlist_discards_private_fields_and_preserves_coverage():
    raw = row(input=CANARY, output=CANARY, metadata={CANARY: CANARY},
              modelParameters={"stop": CANARY}, statusMessage=CANARY, name=CANARY,
              sessionId=CANARY, userId=CANARY)
    result, calls = review([{"data": [raw], "meta": {"cursor": None}}])
    assert CANARY not in json.dumps(result)
    assert result["complete"] is True
    assert result["verified_task_success_count"] is None
    assert result["generation_ended_count"] == 1
    assert result["metrics"]["cost_usd"]["known_sum"] == 0.001
    params = urllib.parse.parse_qs(urllib.parse.urlsplit(calls[0].full_url).query)
    assert params["fields"] == ["core,basic,model,usage,metrics"]
    assert "io" not in params["fields"][0] and "metadata" not in params["fields"][0]
    assert params["fromStartTime"] == [START]
    assert params["toStartTime"] == [END]


@pytest.mark.parametrize("value", [None, True, -1, float("nan"), float("inf"), 10**1000, CANARY])
def test_unknown_bad_numbers_never_turn_into_zero(value):
    result, _ = review([{"data": [row(totalUsage=value, totalCost=value)], "meta": {}}])
    for metric in ("total_tokens", "cost_usd"):
        assert result["metrics"][metric] == {"known_sum": None, "known_count": 0, "unknown_count": 1}


def test_empty_window_is_no_observations_with_unknown_task_success():
    result, _ = review([{"data": [], "meta": {}}])
    assert result["complete"] and result["observation_count"] == 0
    assert result["metrics"]["cost_usd"]["known_sum"] is None
    assert result["verified_task_success_count"] is None


def test_missing_completion_and_level_remain_unknown():
    result, _ = review([{"data": [row(endTime=None, level=None)], "meta": {}}])
    assert result["observations"][0]["ended"] is None
    assert result["generation_unknown_end_count"] == 1
    assert result["generation_unknown_level_count"] == 1
    assert result["generation_ended_count"] == 0


def test_cursor_encoded_and_duplicate_page_not_double_counted():
    cursor = "opaque+/="
    result, calls = review([{"data": [row()], "meta": {"cursor": cursor}},
                            {"data": [row()], "meta": {}}])
    assert result["duplicate_count"] == 1
    assert result["observation_count"] == 1
    assert result["metrics"]["total_tokens"]["known_sum"] == 5
    assert urllib.parse.parse_qs(urllib.parse.urlsplit(calls[1].full_url).query)["cursor"] == [cursor]
    assert cursor not in json.dumps(result)


def test_page_cap_reports_incomplete_instead_of_total():
    result, calls = review([{"data": [row()], "meta": {"cursor": "next"}}], max_pages=1)
    assert len(calls) == 1 and not result["complete"] and not result["pagination_exhausted"]


@pytest.mark.parametrize("cursor", [False, 0, [], {}, "x" * 4097, "bad\nvalue"])
def test_invalid_cursor_is_fixed_failure(cursor):
    with pytest.raises(lookup.TelemetryError, match="^invalid_pagination_cursor$"):
        review([{"data": [], "meta": {"cursor": cursor}}])


def test_repeated_cursor_rejected():
    with pytest.raises(lookup.TelemetryError, match="^invalid_pagination_cursor$"):
        review([{"data": [], "meta": {"cursor": "same"}}] * 2)


@pytest.mark.parametrize("override", [{"base_url": "http://jp.cloud.langfuse.com"},
    {"base_url": "https://jp.cloud.langfuse.com.evil.example"}, {"base_url": []},
    {"max_pages": True}, {"max_pages": 6}, {"timeout": float("nan")},
    {"timeout": 10**1000}, {"trace_id": "bad"}])
def test_bounds_reject_before_network(override):
    with pytest.raises(lookup.TelemetryError):
        review([], **override)


@pytest.mark.parametrize("start,end", [("2026-01-01", END), (END, START),
    (START, "2026-11-09T00:00:00Z"), ("2026-11-01T00:00:00+09:00", END)])
def test_invalid_utc_window_before_network(start, end):
    with pytest.raises(lookup.TelemetryError):
        lookup.read_review(public_key="p", secret_key="s", from_time=start, to_time=end,
                           opener=lambda *a, **k: pytest.fail("network"))


def test_remote_rows_outside_window_and_invalid_ids_dropped():
    result, _ = review([{"data": [row(startTime=END), row(traceId=CANARY), row(id=CANARY)], "meta": {}}])
    assert result["projection_dropped_count"] == 3 and result["observation_count"] == 0
    assert not result["complete"] and CANARY not in json.dumps(result)


def test_untrusted_enum_and_model_cannot_escape_projection():
    result, _ = review([{"data": [row(type=[], level={}, model="vendor/secret-canary")], "meta": {}}])
    projected = result["observations"][0]
    assert projected["type"] is None and projected["level"] is None and projected["model"] is None


@pytest.mark.parametrize("payload", [b"not-json-" + CANARY.encode(), b"x" * (lookup.MAX_BYTES + 1),
    {"data": [row()] * 101, "meta": {}}, {"data": [], "meta": CANARY}],
    ids=["bad-json", "oversized", "excess-rows", "bad-meta"])
def test_bad_response_only_static_error(payload):
    with pytest.raises(lookup.TelemetryError) as failure:
        review([payload])
    assert CANARY not in str(failure.value)


def test_redirect_handler_and_http_errors_do_not_reveal_headers_or_body():
    assert lookup.NoRedirect().redirect_request(None, None, 302, CANARY, {}, CANARY) is None
    def transport(*args, **kwargs):
        raise urllib.error.HTTPError("https://example.invalid/" + CANARY, 302, CANARY, {}, None)
    with pytest.raises(lookup.TelemetryError, match="^lookup_failed$"):
        lookup.read_review(public_key="p", secret_key=CANARY, from_time=START, to_time=END, opener=transport)


def test_provider_projection_uses_validator_and_domain_separated_stable_id():
    call_id = "reddog_provider_call:" + "c" * 64
    seen = []
    def validator(value):
        seen.append(value)
        return SimpleNamespace(call_id=call_id, outcome="INDETERMINATE")
    result = lookup.project_provider_evidence({"receipt": "test"}, validator=validator)
    assert seen == [{"receipt": "test"}]
    assert result["trace_id"] == lookup.trace_id_for_provider_call(call_id)
    assert result["trace_id"] != "c" * 32 and len(result["trace_id"]) == 32
    assert result["verified_task_success"] is None and result["provider_outcome"] == "INDETERMINATE"
    def reject(value):
        raise ValueError(CANARY)
    with pytest.raises(lookup.TelemetryError, match="^invalid_provider_evidence$"):
        lookup.project_provider_evidence({}, validator=reject)


def test_cli_argument_error_does_not_echo_untrusted_values():
    import sys
    result = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/reddog_langfuse_review.py"), CANARY],
                            capture_output=True, text=True)
    assert result.returncode == 2 and CANARY not in result.stdout + result.stderr
    assert json.loads(result.stderr)["reason"] == "invalid_arguments"


@pytest.mark.parametrize("outcome,reason,stage,correlation", [
    ("BLOCKED_PRECALL", "PRECALL_INTENT", "precall", "not_applicable"),
    ("INDETERMINATE", "PRECALL_INTENT", "unknown", "unconfirmed"),
    ("COMPLETED", "PROVIDER_RETURNED", "provider_completion", "unconfirmed"),
    ("FAILED", "PROVIDER_FAILED", "provider_failure", "unconfirmed"),
    ("FAILED", "PROVIDER_TIMEOUT", "provider_failure", "unconfirmed"),
    ("FAILED", "RESPONSE_INVALID", "output_validation", "unconfirmed"),
    ("FAILED", None, "unknown", "unconfirmed"),
])
def test_local_projection_never_claims_external_correlation(outcome, reason, stage, correlation):
    receipt = SimpleNamespace(call_id="reddog_provider_call:" + "d" * 64,
                              outcome=outcome, reason=reason)
    result = lookup.project_provider_evidence(
        {"generation_id": CANARY, "trace_id": TRACE, "verified_task_success": True},
        validator=lambda value: receipt,
    )
    assert result["trace_id_source"] == "derived_local_candidate"
    assert result["correlation_status"] == correlation
    assert result["external_trace_id"] is None
    assert result["diagnostic_stage"] == stage
    assert result["verified_task_success"] is None
    assert result["trace_id"] != TRACE
    assert CANARY not in json.dumps(result)
