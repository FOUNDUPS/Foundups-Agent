"""Fail-closed post-completion HoloIndex owner readiness regressions."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pytest

from holo_index.authority_worktree import HoloIndexAuthoritySelection
from holo_index.query_receipt import build_query_receipt, canonical_semantic_evidence
from modules.communication.moltbot_bridge.src import (
    holoindex_postmerge_runtime_controller as controller,
)
from modules.communication.moltbot_bridge.src.reddog_holoindex_owner_result_verification import (
    classify_verified_owner_result,
    is_verified_transient_owner_result,
)
from modules.communication.moltbot_bridge.src import (
    reddog_holoindex_owner_result_verification as verification,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_owner_acquisition import (
    MAX_OWNER_ATTEMPTS,
    OWNER_OPERATION_TIMEOUT_SECONDS,
)


HEAD = "a" * 40
ROOT_DIGEST = "sha256:" + ("b" * 64)
GENERATION = "sha256:" + ("c" * 64)
FRESHNESS = "sha256:" + ("d" * 64)
QUERY = "runtime closure"
COMPLETION = {
    "generation_id": GENERATION,
    "freshness_receipt_digest": FRESHNESS,
}


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


def _selection(root: Path, *, accepted: bool = True) -> HoloIndexAuthoritySelection:
    return HoloIndexAuthoritySelection(
        accepted,
        root,
        HEAD,
        HEAD,
        ROOT_DIGEST,
        False,
        "authority_worktree",
        () if accepted else ("HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH",),
    )


def _owner_result(
    *, current: bool = False, error: str = "SEMANTIC_BACKEND_UNAVAILABLE",
    attempts: int = MAX_OWNER_ATTEMPTS, retried: bool = True,
    retry_reason: str = "SEMANTIC_BACKEND_UNAVAILABLE",
    generation: str = GENERATION, freshness_digest: str = FRESHNESS,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ok": current,
        "source": "holoindex_owner_service",
        "query": QUERY,
        "freshness": "CURRENT" if current else "UNKNOWN",
        "error": "" if current else error,
        "index_gap_detected": not current,
        "raw_result": {},
        "no_holoindex_reindex_performed": True,
        "repo_head_sha": HEAD,
        "repo_root_digest": ROOT_DIGEST,
        "freshness_generation_id": generation if current else "",
        "freshness_receipt_digest": freshness_digest if current else "",
        "workspace_repo_head_sha": HEAD,
        "authority_repo_head_sha": HEAD,
        "authority_repo_root_digest": ROOT_DIGEST,
        "workspace_overlay_present": False,
        "semantic_evidence_authority": "committed_head_only",
        "no_authority_worktree_mutation_performed": True,
    }
    serialized, _, _ = canonical_semantic_evidence(result["raw_result"])
    result["semantic_evidence_json"] = serialized
    result.update(
        owner_attempts=attempts,
        owner_retry_performed=retried,
        owner_retry_reason=retry_reason,
    )
    result["query_receipt"] = build_query_receipt(
        source="holoindex_owner_service",
        source_class="holoindex",
        query=QUERY,
        result=result,
        require_generation=True,
    )
    return result


def _reseal(result: Mapping[str, Any]) -> dict[str, Any]:
    sealed = dict(result)
    sealed["query_receipt"] = build_query_receipt(
        source="holoindex_owner_service",
        source_class="holoindex",
        query=QUERY,
        result=sealed,
        require_generation=True,
    )
    return sealed


def _prove(
    tmp_path: Path, results: list[Mapping[str, Any]], *,
    clock: FakeClock | None = None, deadline: float = 1_000.0,
) -> tuple[Mapping[str, Any] | None, str, list[float]]:
    clock = clock or FakeClock()
    timeouts: list[float] = []

    def query_runner(_payload: Mapping[str, Any], **kwargs: Any) -> Mapping[str, Any]:
        timeouts.append(kwargs["operation_timeout_seconds"])
        clock.advance(5.0)
        return results.pop(0)

    owner, reason = controller._prove_completion_owner(
        query=QUERY,
        root=tmp_path,
        completion=COMPLETION,
        deadline=deadline,
        clock=clock,
        query_runner=query_runner,
        select_authority=lambda root: _selection(root),
    )
    return owner, reason, timeouts


def test_verified_exhausted_transient_gets_one_immediate_full_reproof(
    tmp_path: Path,
) -> None:
    transient = _owner_result()
    assert is_verified_transient_owner_result(
        transient, query=QUERY, selection=_selection(tmp_path)
    )

    owner, reason, timeouts = _prove(
        tmp_path, [transient, _owner_result(current=True)]
    )

    assert reason == ""
    assert owner and owner["freshness_generation_id"] == GENERATION
    assert len(timeouts) == controller._POSTCOMPLETION_OWNER_PROOF_ATTEMPTS
    assert timeouts == [OWNER_OPERATION_TIMEOUT_SECONDS, 295.0]


def test_two_verified_transients_reject_after_exactly_two_proofs(
    tmp_path: Path,
) -> None:
    owner, reason, timeouts = _prove(
        tmp_path, [_owner_result(), _owner_result()]
    )

    assert owner is None
    assert reason == "owner_not_current_after_completion"
    assert len(timeouts) == controller._POSTCOMPLETION_OWNER_PROOF_ATTEMPTS


def test_controller_proof_count_is_independent_of_low_level_attempt_policy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setattr(verification, "MAX_OWNER_ATTEMPTS", 3)
    transient = _owner_result(attempts=3)
    owner, reason, timeouts = _prove(tmp_path, [transient, transient])

    assert owner is None
    assert reason == "owner_not_current_after_completion"
    assert len(timeouts) == 2


@pytest.mark.parametrize(
    "result",
    [
        _owner_result(error="STALE_INDEX", attempts=0, retried=False, retry_reason=""),
        _owner_result(
            error="HOLOINDEX_TIER0_INCOMPLETE",
            attempts=1,
            retried=False,
            retry_reason="",
        ),
        {**_owner_result(), "query_receipt": {}},
        {**_owner_result(error="HOLOINDEX_TIER0_INCOMPLETE"),
         "error": "SEMANTIC_BACKEND_UNAVAILABLE"},
    ],
)
def test_untrusted_stale_or_deterministic_failure_never_retries(
    tmp_path: Path, result: Mapping[str, Any],
) -> None:
    owner, reason, timeouts = _prove(tmp_path, [result])

    assert owner is None
    assert reason == "owner_not_current_after_completion"
    assert len(timeouts) == 1


def test_rejected_authority_never_starts_owner_proof(tmp_path: Path) -> None:
    calls: list[object] = []

    owner, reason = controller._prove_completion_owner(
        query=QUERY,
        root=tmp_path,
        completion=COMPLETION,
        deadline=300.0,
        clock=FakeClock(),
        query_runner=lambda *_args, **_kwargs: calls.append(object()),
        select_authority=lambda root: _selection(root, accepted=False),
    )

    assert owner is None
    assert reason == "owner_not_current_after_completion"
    assert calls == []


def test_slow_authority_selection_recomputes_query_budget(tmp_path: Path) -> None:
    clock = FakeClock()
    observed: list[float] = []

    def select(root: Path) -> HoloIndexAuthoritySelection:
        clock.advance(25.0)
        return _selection(root)

    def query(_payload: Mapping[str, Any], **kwargs: Any) -> Mapping[str, Any]:
        observed.append(kwargs["operation_timeout_seconds"])
        return _owner_result(current=True)

    owner, reason = controller._prove_completion_owner(
        query=QUERY, root=tmp_path, completion=COMPLETION, deadline=500.0,
        clock=clock, query_runner=query, select_authority=select,
    )

    assert reason == ""
    assert owner is not None
    assert observed == [275.0]


def test_authority_selection_consuming_budget_starts_no_query(tmp_path: Path) -> None:
    clock = FakeClock()
    calls: list[object] = []

    def select(root: Path) -> HoloIndexAuthoritySelection:
        clock.advance(5.0)
        return _selection(root)

    owner, reason = controller._prove_completion_owner(
        query=QUERY, root=tmp_path, completion=COMPLETION, deadline=5.0,
        clock=clock,
        query_runner=lambda *_args, **_kwargs: calls.append(object()),
        select_authority=select,
    )

    assert owner is None
    assert reason == "owner_proof_timeout_after_completion"
    assert calls == []


@pytest.mark.parametrize("malformed", [[], {}, True])
def test_malformed_receipt_bound_error_is_invalid_not_exception(
    tmp_path: Path, malformed: Any,
) -> None:
    result = _owner_result()
    result["error"] = malformed
    result = _reseal(result)
    selection = _selection(tmp_path)

    assert classify_verified_owner_result(
        result, query=QUERY, selection=selection
    ) == verification.INVALID
    assert not is_verified_transient_owner_result(
        result, query=QUERY, selection=selection
    )


@pytest.mark.parametrize(
    ("field", "malformed"),
    [
        ("owner_attempts", True),
        ("owner_retry_performed", []),
        ("owner_retry_reason", {}),
    ],
)
def test_malformed_retry_telemetry_is_invalid_not_exception(
    tmp_path: Path, field: str, malformed: Any,
) -> None:
    result = _owner_result()
    result[field] = malformed
    result = _reseal(result)

    assert not is_verified_transient_owner_result(
        result, query=QUERY, selection=_selection(tmp_path)
    )


def test_forged_unbound_retry_telemetry_cannot_authorize_reproof(
    tmp_path: Path,
) -> None:
    result = _owner_result(attempts=1, retried=False, retry_reason="")
    result.update(
        owner_attempts=MAX_OWNER_ATTEMPTS,
        owner_retry_performed=True,
        owner_retry_reason="SEMANTIC_BACKEND_UNAVAILABLE",
    )

    assert not is_verified_transient_owner_result(
        result, query=QUERY, selection=_selection(tmp_path)
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("freshness_generation_id", "sha256:" + ("e" * 64)),
        ("freshness_receipt_digest", "sha256:" + ("f" * 64)),
    ],
)
def test_current_wrong_completion_binding_rejects_without_retry(
    tmp_path: Path, field: str, value: str,
) -> None:
    kwargs = (
        {"generation": value}
        if field == "freshness_generation_id"
        else {"freshness_digest": value}
    )
    current = _owner_result(current=True, **kwargs)
    owner, reason, timeouts = _prove(tmp_path, [current])

    assert owner is None
    assert reason == "owner_completion_binding_mismatch"
    assert len(timeouts) == 1


def test_zero_remaining_budget_starts_no_query(tmp_path: Path) -> None:
    calls: list[object] = []
    clock = FakeClock()

    owner, reason = controller._prove_completion_owner(
        query=QUERY,
        root=tmp_path,
        completion=COMPLETION,
        deadline=clock(),
        clock=clock,
        query_runner=lambda *_args, **_kwargs: calls.append(object()),
        select_authority=lambda root: _selection(root),
    )

    assert owner is None
    assert reason == "owner_proof_timeout_after_completion"
    assert calls == []


def test_first_query_consuming_budget_cannot_be_accepted(tmp_path: Path) -> None:
    clock = FakeClock()
    current = _owner_result(current=True)

    def consume(_payload: Mapping[str, Any], **kwargs: Any) -> Mapping[str, Any]:
        assert kwargs["operation_timeout_seconds"] == 5.0
        clock.advance(5.0)
        return current

    owner, reason = controller._prove_completion_owner(
        query=QUERY,
        root=tmp_path,
        completion=COMPLETION,
        deadline=5.0,
        clock=clock,
        query_runner=consume,
        select_authority=lambda root: _selection(root),
    )

    assert owner is None
    assert reason == "owner_proof_timeout_after_completion"


class _Broker:
    def __init__(self) -> None:
        self.states = {
            runtime_id: {"registered": True, "running": False,
                         "thread_alive": False, "state": "stopped", "last_error": ""}
            for runtime_id in ("openclaw", "openclaw_supervisor")
        }
        self.stopped: list[str] = []

    def get_runtime_status(self, runtime_id: str) -> dict[str, Any]:
        return dict(self.states[runtime_id])

    def start_dae(
        self, runtime_id: str, *, actor_id: str,
        launch_kwargs: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        assert actor_id == "0102"
        self.states[runtime_id].update(
            running=True, thread_alive=True, state="running"
        )
        return {"success": True, "status": "starting"}

    def stop_dae(self, runtime_id: str, *, actor_id: str) -> dict[str, Any]:
        assert actor_id == "0102"
        self.stopped.append(runtime_id)
        self.states[runtime_id].update(running=False, thread_alive=False, state="stopped")
        return {"success": True, "status": "stopped"}


@pytest.mark.parametrize("interruption", [KeyboardInterrupt(), SystemExit()])
def test_owner_proof_baseexception_still_cleans_owned_runtimes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, interruption: BaseException,
) -> None:
    broker = _Broker()
    clock = FakeClock()
    monkeypatch.setattr(
        controller,
        "validate_supervisor_holoindex_postmerge_completion",
        lambda *_args: COMPLETION,
    )

    result = controller._execute_runtime_transaction(
        root=tmp_path,
        head=HEAD,
        task_id="holoindex_postmerge_refresh:" + HEAD,
        query=QUERY,
        timeout_seconds=10.0,
        poll_interval_seconds=0.1,
        query_runner=lambda *_args, **_kwargs: (_ for _ in ()).throw(interruption),
        select_authority=lambda root: _selection(root),
        bootstrap=lambda: None,
        broker_provider=lambda: broker,
        database_provider=lambda: object(),
        clock=clock,
        sleeper=clock.advance,
        git_runner=lambda *_args: (_ for _ in ()).throw(AssertionError("unused")),
    )

    assert result.accepted is False
    assert result.rejection_reasons == ("runtime_exception",)
    assert result.stopped_runtime_ids == ("openclaw_supervisor", "openclaw")


def test_touched_runtime_boundaries_remain_wsp62_bounded() -> None:
    assert len(Path(controller.__file__).read_text(encoding="utf-8").splitlines()) <= 675
    assert len(Path(verification.__file__).read_text(encoding="utf-8").splitlines()) <= 675
