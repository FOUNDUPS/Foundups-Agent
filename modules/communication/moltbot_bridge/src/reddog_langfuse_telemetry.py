"""Bounded, content-free Langfuse lookups. Remote telemetry grants no authority."""

from __future__ import annotations

import base64
import hashlib
import json
import math
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping

ORIGINS = frozenset({"https://jp.cloud.langfuse.com", "https://cloud.langfuse.com", "https://us.cloud.langfuse.com"})
MAX_BYTES = 1024 * 1024
TRACE_ID = re.compile(r"^(?!0{32}$)[0-9a-f]{32}$")
MODEL = re.compile(r"^[a-z0-9][a-z0-9._-]{0,47}/[a-z0-9][a-z0-9._:+-]{0,95}$")
FIELDS = "core,basic,model,usage,metrics"


class TelemetryError(ValueError):
    """Only fixed, content-free reason codes may leave the lookup boundary."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def utc_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
            raise ValueError
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError, AttributeError, OverflowError):
        raise TelemetryError("invalid_utc_time") from None


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def trace_id_for_provider_call(call_id: str) -> str:
    """Derive correlation after the caller validates its canonical receipt."""
    if not isinstance(call_id, str) or not re.fullmatch(r"reddog_provider_call:[0-9a-f]{64}", call_id):
        raise TelemetryError("invalid_provider_call_id")
    return hashlib.sha256(b"reddog-langfuse-provider-trace.v1\x00" + call_id.encode("ascii")).hexdigest()[:32]


def project_provider_evidence(value: Mapping[str, Any], *, validator: Callable) -> dict[str, Any]:
    """Project validated local evidence; a derived ID is not an observed trace.

    ``trace_id`` is retained as a lookup candidate for existing callers. No
    current transport binding is proved here, even for COMPLETED receipts.
    Local-only diagnostics do not need a provider receipt or external trace.
    """
    try:
        receipt = validator(value)
        if receipt.outcome not in {"BLOCKED_PRECALL", "INDETERMINATE", "COMPLETED", "FAILED"}:
            raise ValueError
        stage = {"BLOCKED_PRECALL": "precall", "INDETERMINATE": "unknown",
                 "COMPLETED": "provider_completion"}.get(receipt.outcome, "unknown")
        if receipt.outcome == "FAILED":
            stage = {"RESPONSE_INVALID": "output_validation",
                     "PROVIDER_FAILED": "provider_failure",
                     "PROVIDER_TIMEOUT": "provider_failure"}.get(getattr(receipt, "reason", None), "unknown")
        return {"trace_id": trace_id_for_provider_call(receipt.call_id),
                "trace_id_source": "derived_local_candidate",
                "correlation_status": "not_applicable" if receipt.outcome == "BLOCKED_PRECALL" else "unconfirmed",
                "external_trace_id": None, "diagnostic_stage": stage,
                "provider_outcome": receipt.outcome, "verified_task_success": None}
    except Exception:
        raise TelemetryError("invalid_provider_evidence") from None


def _number(value: Any, *, integer: bool = False) -> int | float | None:
    if type(value) not in (int, float) or not 0 <= value <= 10**12 or not math.isfinite(value):
        return None
    if integer and type(value) is not int:
        return None
    return value


def _model(value: Any) -> str | None:
    if not isinstance(value, str) or not MODEL.fullmatch(value) or ".." in value:
        return None
    if re.search(r"(?:sk-|pk-|token|secret|bearer|github_pat_|ghp_|gho_|hf_|oauth|api_key|[a-z0-9]{24})", value):
        return None
    return value


def _project(row: Any, start: datetime, end: datetime) -> dict[str, Any] | None:
    if not isinstance(row, dict) or not isinstance(row.get("traceId"), str) or not TRACE_ID.fullmatch(row["traceId"]):
        return None
    try:
        observed = utc_time(row.get("startTime"))
        if not start <= observed < end:
            return None
        ended = None if row.get("endTime") is None else utc_time(row["endTime"]) >= observed
        if ended is False:
            return None
    except TelemetryError:
        return None
    kind = row.get("type")
    level = row.get("level")
    return {"trace_id": row["traceId"], "model": _model(row.get("model")),
            "type": kind if isinstance(kind, str) and kind in {"GENERATION", "SPAN", "EVENT", "AGENT", "TOOL", "CHAIN", "RETRIEVER", "EVALUATOR", "EMBEDDING", "GUARDRAIL"} else None,
            "level": level if isinstance(level, str) and level in {"DEBUG", "DEFAULT", "WARNING", "ERROR"} else None,
            "ended": ended, "latency_seconds": _number(row.get("latency")),
            "input_tokens": _number(row.get("inputUsage"), integer=True),
            "output_tokens": _number(row.get("outputUsage"), integer=True),
            "total_tokens": _number(row.get("totalUsage"), integer=True),
            "cost_usd": _number(row.get("totalCost"))}


def read_review(*, public_key: str, secret_key: str, from_time: str, to_time: str,
                base_url: str = "https://jp.cloud.langfuse.com", trace_id: str | None = None,
                max_pages: int = 5, timeout: float = 10, opener=None) -> dict[str, Any]:
    start, end = utc_time(from_time), utc_time(to_time)
    if not timedelta(0) < end - start <= timedelta(days=7):
        raise TelemetryError("invalid_time_window")
    if not isinstance(base_url, str) or base_url not in ORIGINS or type(max_pages) is not int or not 1 <= max_pages <= 5:
        raise TelemetryError("invalid_lookup_bounds")
    if type(timeout) not in (int, float) or not 0 < timeout <= 15 or not math.isfinite(timeout):
        raise TelemetryError("invalid_lookup_bounds")
    if trace_id is not None and (not isinstance(trace_id, str) or not TRACE_ID.fullmatch(trace_id)):
        raise TelemetryError("invalid_trace_id")
    if any(not isinstance(key, str) or not key or len(key) > 4096 or any(ord(c) < 33 or ord(c) > 126 for c in key) for key in (public_key, secret_key)):
        raise TelemetryError("missing_or_invalid_credentials")
    auth = base64.b64encode((public_key + ":" + secret_key).encode("ascii")).decode("ascii")
    transport = opener or urllib.request.build_opener(NoRedirect()).open
    rows, seen, cursors = [], set(), set()
    cursor, dropped, duplicates, pages = None, 0, 0, 0
    for _ in range(max_pages):
        params = {"fromStartTime": _iso(start), "toStartTime": _iso(end), "limit": 100, "fields": FIELDS}
        if trace_id:
            params["traceId"] = trace_id
        if cursor:
            params["cursor"] = cursor
        request = urllib.request.Request(base_url + "/api/public/v2/observations?" + urllib.parse.urlencode(params),
                                         headers={"Authorization": "Basic " + auth, "Accept": "application/json"}, method="GET")
        try:
            with transport(request, timeout=timeout) as response:
                raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise TelemetryError("response_too_large")
            payload = json.loads(raw)
        except TelemetryError:
            raise
        except Exception:
            raise TelemetryError("lookup_failed") from None
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list) or len(payload["data"]) > 100:
            raise TelemetryError("invalid_response_schema")
        pages += 1
        for row in payload["data"]:
            projected = _project(row, start, end)
            row_id = row.get("id") if isinstance(row, dict) else None
            if projected is None or not isinstance(row_id, str) or not re.fullmatch(r"[0-9a-f]{16}", row_id) or (trace_id and projected["trace_id"] != trace_id):
                dropped += 1
                continue
            identity = (projected["trace_id"], row_id)
            if identity in seen:
                duplicates += 1
                continue
            seen.add(identity)
            rows.append(projected)
        meta = payload.get("meta")
        if not isinstance(meta, dict):
            raise TelemetryError("invalid_response_schema")
        cursor = meta.get("cursor")
        if cursor is None or cursor == "":
            break
        if not isinstance(cursor, str) or len(cursor) > 4096 or not cursor.isascii() or not cursor.isprintable() or cursor in cursors:
            raise TelemetryError("invalid_pagination_cursor")
        cursors.add(cursor)
    generations = [row for row in rows if row["type"] == "GENERATION"]
    metrics = {}
    for key in ("input_tokens", "output_tokens", "total_tokens", "cost_usd"):
        known = [row[key] for row in generations if row[key] is not None]
        metrics[key] = {"known_sum": sum(known) if known else None, "known_count": len(known), "unknown_count": len(generations) - len(known)}
    return {"schema_version": "reddog_langfuse_review.v1", "evidence_only": True,
            "from_time": _iso(start), "to_time": _iso(end), "pages": pages,
            "complete": (cursor is None or cursor == "") and dropped == 0,
            "pagination_exhausted": cursor is None or cursor == "", "projection_dropped_count": dropped,
            "duplicate_count": duplicates, "observation_count": len(rows),
            "generation_ended_count": sum(row["ended"] is True for row in generations),
            "generation_unknown_end_count": sum(row["ended"] is None for row in generations),
            "generation_error_count": sum(row["level"] == "ERROR" for row in generations),
            "generation_unknown_level_count": sum(row["level"] is None for row in generations),
            "verified_task_success_count": None, "metrics": metrics, "observations": rows}
