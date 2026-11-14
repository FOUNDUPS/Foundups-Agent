"""Generation-bound selection regressions for signer packet validation."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_signer_peer_instance_packet_validator import (
    _selection_valid,
)


def _sha(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _selection(tmp_path: Path) -> tuple[dict[str, object], dict[str, object]]:
    repo = (tmp_path / "repo").resolve()
    runtime = (tmp_path / "runtime").resolve()
    config = runtime / "signer_service_config.json"
    packet = runtime / "signer_service_run_packet.json"
    raw = "{}"
    config_digest = _sha("config")
    value = {
        "manifest_id": _sha("manifest"),
        "artifact_generation_digest": _sha("generation"),
        "config_digest": config_digest,
        "config_raw_digest": _sha("config-raw"),
        "run_packet_digest": _sha(raw),
        "repo_root": str(repo),
        "runtime_root": str(runtime),
        "config_path": str(config),
        "run_packet_path": str(packet),
        "generation": 1,
        "generation_revision": "a" * 64,
        "selection_issued_at": 100,
        "selection_expires_at": 130,
        "owner_config_id": _sha("owner"),
    }
    bindings = {
        "root": repo,
        "config_path": config,
        "run_packet_path": packet,
        "config_digest": config_digest,
        "run_packet_raw": raw,
    }
    return value, bindings


def test_exact_generation_selection_shape_is_accepted(
    tmp_path: Path,
) -> None:
    value, bindings = _selection(tmp_path)

    assert _selection_valid(value, **bindings) is True


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("generation", 0),
        ("generation_revision", "wrong"),
        ("selection_expires_at", 131),
        ("owner_config_id", "wrong"),
    ],
)
def test_invalid_generation_selection_field_rejects(
    tmp_path: Path, field: str, replacement: object
) -> None:
    value, bindings = _selection(tmp_path)
    value[field] = replacement

    assert _selection_valid(value, **bindings) is False


def test_arbitrary_selection_field_rejects(tmp_path: Path) -> None:
    value, bindings = _selection(tmp_path)
    value["attacker_authority"] = True

    assert _selection_valid(value, **bindings) is False
