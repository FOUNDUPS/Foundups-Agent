"""One explicit synthetic free-model call for OpenRouter Broadcast verification."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
import uuid


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def probe() -> dict:
    trace_id = uuid.uuid4().hex
    result = {"schema_version": "reddog_openrouter_telemetry_probe.v1",
              "trace_id": trace_id, "synthetic": True, "verified_task_success": None}
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not re.fullmatch(r"sk-or-[A-Za-z0-9_-]{20,256}", key):
        return {**result, "ok": False, "status": "credential_unavailable"}
    request = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps({"model": "openrouter/free", "max_tokens": 16,
                         "messages": [{"role": "user", "content": "Reply with OK."}],
                         "trace": {"trace_id": trace_id, "trace_name": "foundups-rsi-pilot",
                                   "environment": "pilot"}}).encode("utf-8"),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                 "X-Title": "FOUNDUPS RSI synthetic telemetry pilot"}, method="POST",
    )
    try:
        with urllib.request.build_opener(_NoRedirect()).open(request, timeout=30) as response:
            raw = response.read(65537)
            if len(raw) > 65536:
                return {**result, "ok": False, "status": "response_too_large"}
            data = json.loads(raw)
        if not isinstance(data, dict) or "error" in data:
            return {**result, "ok": False, "status": "provider_response_error"}
        choices = data.get("choices")
        if (not isinstance(choices, list) or not choices or not isinstance(choices[0], dict)
                or not isinstance(choices[0].get("message"), dict)
                or not isinstance(choices[0]["message"].get("content"), str)):
            return {**result, "ok": False, "status": "provider_response_error"}
        usage = data.get("usage")
        numbers = {}
        if isinstance(usage, dict):
            for field in ("prompt_tokens", "completion_tokens", "total_tokens"):
                value = usage.get(field)
                numbers[field] = value if type(value) is int and 0 <= value <= 10**12 else None
        return {**result, "ok": True, "status": "provider_returned",
                "usage": numbers, "content_retained": False}
    except urllib.error.HTTPError as exc:
        status = exc.code if type(exc.code) is int and 100 <= exc.code <= 599 else None
        return {**result, "ok": False, "status": "http_error", "http_status": status}
    except Exception:
        return {**result, "ok": False, "status": "probe_failed"}


def main() -> int:
    result = probe()
    print(json.dumps(result, allow_nan=False))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
