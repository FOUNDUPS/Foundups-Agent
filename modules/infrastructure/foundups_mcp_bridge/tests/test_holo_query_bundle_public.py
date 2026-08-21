"""Hostile contracts for the public RedDog Holo query bundle projection."""

from __future__ import annotations

import json

import pytest

from modules.infrastructure.foundups_mcp_bridge.src import reddog_tools
from modules.infrastructure.foundups_mcp_bridge.src.holo_query_bundle_public import (
    PUBLIC_MAX_BYTES,
    PUBLIC_SCHEMA,
    project_holo_query_bundle,
)


def _encoded(payload):
    return json.dumps(
        payload, ensure_ascii=True, sort_keys=True, allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def test_projection_redacts_secrets_and_absolute_paths(tmp_path):
    result = {
        "ok": True, "token": "secret-value",
        "location": str(tmp_path / "README.md") + ":12",
        "content": f"root={tmp_path} access_token=secret-value C:/private/file.txt",
    }
    projected = project_holo_query_bundle(result, tmp_path)
    encoded = _encoded(projected)
    assert projected["schema_version"] == PUBLIC_SCHEMA
    assert "token" not in projected
    assert projected["location"] == "README.md:12"
    assert str(tmp_path) not in encoded.decode("utf-8")
    assert "secret-value" not in encoded.decode("utf-8")
    assert len(encoded) == projected["public_projection_bytes"] <= PUBLIC_MAX_BYTES


@pytest.mark.parametrize("value", [float("nan"), float("inf"), 1 << 64])
def test_projection_rejects_hostile_numbers(tmp_path, value):
    projected = project_holo_query_bundle({"value": value}, tmp_path)
    assert projected["ok"] is False
    assert projected["error"].startswith("public_projection_")


def test_projection_is_cycle_safe(tmp_path):
    value = {"items": []}
    value["items"].append(value)
    projected = project_holo_query_bundle(value, tmp_path)
    assert projected["error"] == "public_projection_cycle"


def test_projection_prevents_key_collision_and_schema_overwrite(tmp_path):
    collision = {"x" * 128 + "a": 1, "x" * 128 + "b": 2}
    rejected = project_holo_query_bundle(collision, tmp_path)
    assert rejected["error"] == "public_projection_key_collision"
    projected = project_holo_query_bundle({"schema_version": "forged"}, tmp_path)
    assert projected["schema_version"] == PUBLIC_SCHEMA


def test_projection_fails_content_free_when_total_size_exceeds_cap(tmp_path):
    projected = project_holo_query_bundle(
        {"items": [("x" * 4096) + str(index) for index in range(128)]},
        tmp_path,
    )
    assert projected["error"] == "public_projection_size_exceeded"
    assert "items" not in projected
    assert len(_encoded(projected)) == projected["public_projection_bytes"]


def test_tool_delegates_exact_bounded_request_and_preserves_failure(monkeypatch, tmp_path):
    from scripts import reddog_holoindex_owner_query_once as adapter

    captured = {}
    def fake_query(request, *, repo_root):
        captured.update(request=request, repo_root=repo_root)
        return {
            "ok": False, "error": "STALE_INDEX", "freshness": "UNKNOWN",
            "index_gap_detected": True, "no_holoindex_reindex_performed": True,
            "owner_attempts": 0,
        }

    monkeypatch.setattr(adapter, "query_once", fake_query)
    response = reddog_tools.holo_query_bundle(
        tmp_path, "audit RedDog", limit=3, retrieval_mode="semantic",
        module_hint="extensions/reddog", must_include=["README.md"],
    )
    assert captured["repo_root"] == tmp_path
    assert captured["request"] == {
        "query": "audit RedDog", "limit": 3, "retrieval_mode": "semantic",
        "include_bundle": True, "module_hint": "extensions/reddog",
        "must_include": ["README.md"], "bundle_only": False,
    }
    data = response["data"]
    assert data["ok"] is False and data["freshness"] == "UNKNOWN"
    assert data["error"] == "STALE_INDEX" and data["owner_attempts"] == 0


def test_tool_exception_and_private_fields_are_content_free(monkeypatch, tmp_path):
    from scripts import reddog_holoindex_owner_query_once as adapter

    def fail(*_args, **_kwargs):
        raise RuntimeError(f"token=secret-value path={tmp_path}")

    monkeypatch.setattr(adapter, "query_once", fail)
    response = reddog_tools.holo_query_bundle(tmp_path, "audit")
    encoded = _encoded(response)
    assert response["data"]["ok"] is False
    assert response["data"]["error"] == "RuntimeError"
    assert b"secret-value" not in encoded and str(tmp_path).encode() not in encoded
