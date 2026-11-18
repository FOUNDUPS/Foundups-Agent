#!/usr/bin/env python3
"""Explicit provider-catalog freshness query for configured RedDog models."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.ai_intelligence.ai_gateway.src.model_openrouter_direct_discovery import (  # noqa: E402
    discover_openrouter_model_catalog,
)
from modules.ai_intelligence.ai_gateway.src.model_provider_catalog_snapshot import (  # noqa: E402
    build_discovery_invocation,
)


SCHEMA = "reddog_model_freshness_query.v1"
MODEL_ID = re.compile(
    r"[a-z0-9](?:[a-z0-9._-]{0,62}[a-z0-9])?/"
    r"[a-z0-9](?:[a-z0-9._-]{0,126}[a-z0-9])?(?::free)?\Z"
)
MAX_MODELS = 8
FORBIDDEN_ENV_NAME = re.compile(
    r"(?:KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|AUTH|SIGNER|SOVEREIGN)", re.I
)


def _digest(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(raw.encode("ascii")).hexdigest()


def _read_request() -> tuple[str, ...]:
    value = json.loads(sys.stdin.buffer.read().decode("utf-8", errors="strict"))
    models = value.get("configured_model_ids") if isinstance(value, Mapping) else None
    if not isinstance(models, list) or not 1 <= len(models) <= MAX_MODELS:
        raise ValueError("configured_models_invalid")
    normalized = tuple(dict.fromkeys(str(item).strip().lower() for item in models))
    if not normalized or any(not MODEL_ID.fullmatch(item) for item in normalized):
        raise ValueError("configured_models_invalid")
    return normalized


def _model_rows(records: list[Mapping[str, Any]], configured: tuple[str, ...]) -> list[dict[str, Any]]:
    by_id = {str(item["id"]): item for item in records}
    by_provider: dict[str, list[Mapping[str, Any]]] = {}
    for item in records:
        by_provider.setdefault(str(item["id"]).split("/", 1)[0], []).append(item)
    rows: list[dict[str, Any]] = []
    for model_id in configured:
        provider = model_id.split("/", 1)[0]
        provider_rows = by_provider.get(provider, [])
        chronological = [item for item in provider_rows if isinstance(item.get("created"), int)]
        chronological.sort(key=lambda item: (-int(item["created"]), str(item["id"])))
        current = by_id.get(model_id)
        created = current.get("created") if current else None
        chronology_known = isinstance(created, int) and bool(chronological)
        newer = [
            str(item["id"]) for item in chronological
            if chronology_known and int(item["created"]) > int(created)
        ][:5]
        latest_known = bool(chronology_known and chronological[0]["id"] == model_id)
        rows.append(
            {
                "model_id": model_id,
                "available": current is not None,
                "canonical_slug": str(current.get("canonical_slug") or "") if current else "",
                "created": created,
                "chronology_known": chronology_known,
                "provider_latest_known": latest_known,
                "newer_provider_model_ids": newer,
            }
        )
    return rows


async def _query(configured: tuple[str, ...]) -> dict[str, Any]:
    if any(FORBIDDEN_ENV_NAME.search(name) for name in os.environ):
        return _failure(configured, "credential_bearing_environment_rejected")
    runtime_parent = Path.home() / ".foundups-agent" / "ai_gateway" / "model_freshness_queries"
    runtime_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="query-", dir=runtime_parent) as folder:
        root = Path(folder)
        result = await discover_openrouter_model_catalog(
            build_discovery_invocation(mode="manual"),
            repo_root=REPO_ROOT,
            runtime_root=root,
            attempt_path=root / "attempt.json",
            candidate_path=root / "candidate.json",
        )
    candidate = result.candidate
    catalog_fresh = result.receipt.outcome == "COMPLETED" and candidate is not None
    rows = _model_rows(list(candidate.catalog_payload["data"]), configured) if catalog_fresh else []
    all_available = bool(catalog_fresh and all(row["available"] for row in rows))
    chronology_complete = bool(all_available and all(row["chronology_known"] for row in rows))
    all_latest = bool(chronology_complete and all(row["provider_latest_known"] for row in rows))
    accepted = bool(catalog_fresh and all_available and chronology_complete)
    reasons = _rejection_reasons(result.receipt.reason, catalog_fresh, all_available, chronology_complete)
    latestness = "ALL_PROVIDER_LATEST" if all_latest else (
        "NEWER_PROVIDER_MODELS_AVAILABLE" if chronology_complete else "UNKNOWN"
    )
    body: dict[str, Any] = {
        "schema_version": SCHEMA,
        "accepted": accepted,
        "status": "MODEL_FRESHNESS_READY" if accepted else "MODEL_FRESHNESS_NOT_READY",
        "rejection_reasons": reasons,
        "provider": "openrouter",
        "provider_endpoint": "https://openrouter.ai/api/v1/models",
        "provider_receipt_id": result.receipt.receipt_id,
        "requested_model_ids": list(configured),
        "candidate_snapshot_id": candidate.snapshot_id if candidate else None,
        "observed_at_ms": candidate.observed_at_ms if candidate else None,
        "fresh_until_ms": candidate.fresh_until_ms if candidate else None,
        "configured_models": rows,
        "external_catalog_call_performed": result.receipt.attempted is True,
        "catalog_fresh": bool(catalog_fresh),
        "all_configured_models_available": all_available,
        "chronology_complete": chronology_complete,
        "all_configured_models_provider_latest": all_latest,
        "latestness_status": latestness,
        "credential_free_catalog_egress": True,
        "public_catalog_egress_gate": "PASS",
        "no_model_inference_performed": True,
        "no_model_selection_changed": True,
        "no_runtime_binding_changed": True,
        "no_repository_mutation_performed": True,
        "no_holoindex_reindex_performed": True,
        "queried_at_ms": int(time.time() * 1000),
    }
    body["receipt_id"] = _digest(body)
    return body


def _rejection_reasons(
    discovery_reason: str,
    catalog_fresh: bool,
    all_available: bool,
    chronology_complete: bool,
) -> list[str]:
    if not catalog_fresh:
        return [discovery_reason]
    if not all_available:
        return ["configured_model_unavailable"]
    if not chronology_complete:
        return ["provider_chronology_incomplete"]
    return []


def _failure(configured: tuple[str, ...], reason: str) -> dict[str, Any]:
    body: dict[str, Any] = {
        "schema_version": SCHEMA,
        "accepted": False,
        "status": "MODEL_FRESHNESS_NOT_READY",
        "rejection_reasons": [reason],
        "requested_model_ids": list(configured),
        "configured_models": [],
        "no_model_inference_performed": True,
        "no_model_selection_changed": True,
        "no_runtime_binding_changed": True,
        "no_repository_mutation_performed": True,
        "no_holoindex_reindex_performed": True,
    }
    body["receipt_id"] = _digest(body)
    return body


def main() -> int:
    try:
        result = asyncio.run(_query(_read_request()))
    except (OSError, ValueError, json.JSONDecodeError):
        result = _failure((), "model_freshness_query_invalid")
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
