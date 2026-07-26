"""Regression tests for host-owned HoloIndex startup maintenance dispatch."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from modules.communication.moltbot_bridge.scripts.run_task import (
    execute_task,
    _try_startup_maintenance_dispatch,
)
import modules.communication.moltbot_bridge.scripts.run_task as run_task
from modules.infrastructure.database.src import agent_db
from modules.infrastructure.foundups_mcp_bridge.src import (
    reddog_holoindex_maintenance_handshake as handshake,
)


def _result(*, ready: bool):
    return SimpleNamespace(
        ready=ready,
        status="READY" if ready else "FAILED",
        refreshed=ready,
        error="" if ready else "HOLOINDEX_MAINTENANCE_REQUIRED",
        repo_head_sha="a" * 40,
        generation_id="sha256:generation" if ready else "",
        freshness_receipt_digest="sha256:receipt" if ready else "",
        freshness_reasons=() if ready else ("missing_freshness_receipt",),
    )


def test_startup_holoindex_task_uses_trusted_handshake(
    tmp_path: Path, monkeypatch
) -> None:
    calls: list[dict] = []

    def ensure(**kwargs):
        calls.append(kwargs)
        return _result(ready=True)

    monkeypatch.setattr(handshake, "ensure_reddog_holoindex_operational", ensure)
    dispatched = _try_startup_maintenance_dispatch(
        tmp_path,
        "startup_refresh_holo_index",
        {},
    )

    assert dispatched is not None
    assert dispatched["ok"] is True
    assert dispatched["executor"] == "startup:holo_index"
    assert calls == [
        {
            "repo_root": tmp_path,
            "requested": True,
            "auto_maintenance": True,
        }
    ]


def test_startup_holoindex_task_never_treats_stale_as_success(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(
        handshake,
        "ensure_reddog_holoindex_operational",
        lambda **_kwargs: _result(ready=False),
    )
    dispatched = _try_startup_maintenance_dispatch(
        tmp_path,
        "startup_refresh_holo_index",
        {},
    )

    assert dispatched is not None
    assert dispatched["ok"] is False
    assert dispatched["structured_result"]["freshness_reasons"] == [
        "missing_freshness_receipt"
    ]


def test_exact_startup_route_precedes_generic_wre_skill(
    tmp_path: Path,
    monkeypatch,
) -> None:
    class FakeDB:
        def get_autonomous_tasks(self, **_kwargs):
            return [
                {
                    "task_id": "startup_refresh_holo_index",
                    "description": "refresh exact HoloIndex proof",
                    "required_skills": ["holo-search"],
                    "context": {"source": "startup_maintenance_gate"},
                }
            ]

        def complete_autonomous_task(self, _task_id):
            return None

    monkeypatch.setattr(agent_db, "AgentDB", FakeDB)
    monkeypatch.setattr(
        run_task,
        "_try_startup_maintenance_dispatch",
        lambda *_args, **_kwargs: {
            "ok": True,
            "detail": "verified",
            "executor": "startup:holo_index",
        },
    )
    monkeypatch.setattr(
        run_task,
        "_try_wre_dispatch",
        lambda *_args: (_ for _ in ()).throw(
            AssertionError("generic WRE must not preempt exact maintenance")
        ),
    )

    result = execute_task(
        "startup_refresh_holo_index",
        repo_root=tmp_path,
    )
    assert result["ok"] is True
    assert result["executor"] == "startup:holo_index"


def test_postmerge_task_routes_to_exact_sha_executor(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from modules.infrastructure.idle_automation.src import (
        holoindex_postmerge_executor,
    )

    task_id = "holoindex_postmerge_refresh:" + ("a" * 40)

    class FakeDB:
        def get_autonomous_tasks(self, **_kwargs):
            return [
                {
                    "task_id": task_id,
                    "description": "exact SHA refresh",
                    "required_skills": ["holo-search"],
                    "context": {
                        "source": "holoindex_postmerge_coordinator",
                        "target_repo_head_sha": "a" * 40,
                        "claim_id": "hpmc_test",
                        "claim_binding_digest": "sha256:" + ("c" * 64),
                    },
                }
            ]

        def complete_autonomous_task(self, _task_id):
            raise AssertionError("domain executor owns atomic finalization")

    monkeypatch.setattr(agent_db, "AgentDB", FakeDB)
    monkeypatch.setattr(
        holoindex_postmerge_executor,
        "execute_holoindex_postmerge_task",
        lambda **kwargs: {
            "ok": kwargs["task_id"] == task_id,
            "detail": "verified",
            "executor": "wre:holoindex_postmerge",
            "finalization_owned": True,
        },
    )
    monkeypatch.setattr(
        run_task,
        "_try_wre_dispatch",
        lambda *_args: (_ for _ in ()).throw(
            AssertionError("generic WRE must not preempt post-merge maintenance")
        ),
    )

    result = execute_task(
        task_id,
        repo_root=tmp_path,
        execution_claim={
            "claim_id": "hpmc_test",
            "claim_binding_digest": "sha256:" + ("c" * 64),
        },
    )

    assert result["ok"] is True
    assert result["executor"] == "wre:holoindex_postmerge"
