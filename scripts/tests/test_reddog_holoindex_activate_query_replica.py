"""CLI contracts for default-inert HoloIndex replica activation."""

from __future__ import annotations

import json
from pathlib import Path

from scripts import reddog_holoindex_activate_query_replica as cli
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_query_replica_activation_contract import (
    QueryReplicaActivationResult,
)


def _arguments(tmp_path: Path) -> list[str]:
    return [
        "--real",
        "--repo-root",
        str((tmp_path / "repo").resolve()),
        "--owner-runtime-root",
        str((tmp_path / "owner").resolve()),
        "--canonical-store",
        str((tmp_path / "canonical").resolve()),
        "--replica-root",
        str((tmp_path / "replica").resolve()),
        "--route-file",
        str((tmp_path / "runtime" / "route.json").resolve()),
        "--route-runtime-root",
        str((tmp_path / "runtime").resolve()),
        "--receipt-file",
        str((tmp_path / "runtime" / "receipt.json").resolve()),
        "--expected-sha",
        "a" * 40,
    ]


def test_default_is_inert_and_bounded(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        cli,
        "activate_query_replica",
        lambda _config: (_ for _ in ()).throw(AssertionError("must not activate")),
    )

    exit_code = cli.main([])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {
        "error": "",
        "ok": False,
        "post_query_replica_unchanged": False,
        "receipt_digest": "",
        "route_committed": False,
        "verdict": "NOT_REQUESTED",
    }


def test_real_requires_every_exact_argument(capsys) -> None:
    exit_code = cli.main(["--real"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert payload["error"] == "ACTIVATION_ARGUMENTS_INVALID"
    assert set(payload) == {
        "ok",
        "verdict",
        "error",
        "receipt_digest",
        "route_committed",
        "post_query_replica_unchanged",
    }


def test_real_builds_exact_config_and_emits_only_result(
    tmp_path: Path, capsys, monkeypatch,
) -> None:
    observed = {}

    def activate(config):
        observed["config"] = config
        return QueryReplicaActivationResult(
            True,
            "PASS",
            receipt_digest="sha256:" + "b" * 64,
            route_committed=True,
            post_query_replica_unchanged=True,
        )

    monkeypatch.setattr(cli, "activate_query_replica", activate)
    exit_code = cli.main(_arguments(tmp_path))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert observed["config"].real is True
    assert observed["config"].expected_repo_head_sha == "a" * 40
    assert payload["ok"] is True
    assert payload["verdict"] == "PASS"
    assert str(tmp_path) not in json.dumps(payload)
