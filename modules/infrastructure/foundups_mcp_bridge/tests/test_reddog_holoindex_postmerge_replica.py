"""Post-merge canonical-to-replica ordering regressions."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_maintenance_handshake import (
    OPERATIONAL_FAILED,
    RedDogHoloIndexOperationalResult,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_owner_replica_route import (
    QUERY_REPLICA_REQUIRED_ERROR,
    QUERY_REPLICA_ROOT_ENV,
    QUERY_REPLICA_ROUTE_FILE_ENV,
)
from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_postmerge_replica import (
    POSTMERGE_OPERATIONAL_BINDING_MISMATCH,
    POSTMERGE_ROUTE_CONFIG_ERROR,
    _PostmergeReplicaDependencies,
    _ensure_postmerge_query_replica_operational_for_test,
)


HEAD = "a" * 40
GENERATION = "sha256:" + ("b" * 64)
RECEIPT = "sha256:" + ("c" * 64)


def _current(*, refreshed: bool = True) -> RedDogHoloIndexOperationalResult:
    return RedDogHoloIndexOperationalResult(
        True, "REFRESHED" if refreshed else "READY", refreshed, "", HEAD,
        GENERATION, RECEIPT,
    )


def _required() -> RedDogHoloIndexOperationalResult:
    return RedDogHoloIndexOperationalResult(
        False, OPERATIONAL_FAILED, False, QUERY_REPLICA_REQUIRED_ERROR, HEAD,
        GENERATION, RECEIPT,
    )


def _ready() -> RedDogHoloIndexOperationalResult:
    return RedDogHoloIndexOperationalResult(
        True, "READY", False, "", HEAD, GENERATION, RECEIPT,
    )


def _ready_with_binding(
    *, generation: str = GENERATION, receipt: str = RECEIPT,
) -> RedDogHoloIndexOperationalResult:
    return RedDogHoloIndexOperationalResult(
        True, "READY", False, "", HEAD, generation, receipt,
    )


def _environment(route: Path) -> dict[str, str]:
    return {QUERY_REPLICA_ROUTE_FILE_ENV: str(route)}


def _run(
    tmp_path: Path,
    *,
    current=None,
    environment=None,
    ensure_operational=None,
    activate=None,
):
    runtime = tmp_path / "runtime"
    runtime.mkdir(exist_ok=True)
    route = runtime / "reddog_holoindex_query_route.json"
    return _ensure_postmerge_query_replica_operational_for_test(
        repo_root=tmp_path / "authority",
        owner_runtime_root=tmp_path / "runtime-root",
        canonical_store=tmp_path / "canonical",
        expected_repo_head_sha=HEAD,
        current=current or _current(),
        environ=environment if environment is not None else _environment(route),
        dependencies=_PostmergeReplicaDependencies(
            ensure_operational=ensure_operational or (lambda **_kwargs: _required()),
            activate=activate or (lambda _config: pytest.fail("unexpected activation")),
        ),
    )


def test_current_route_skips_materialization_and_preserves_refresh(tmp_path: Path) -> None:
    result = _run(tmp_path, ensure_operational=lambda **_kwargs: _ready())

    assert result.ready is True
    assert result.refreshed is True
    assert result.generation_id == GENERATION


def test_current_route_cannot_substitute_canonical_binding(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        ensure_operational=lambda **_kwargs: _ready_with_binding(
            generation="sha256:" + ("d" * 64)
        ),
    )

    assert result.ready is False
    assert result.error == POSTMERGE_OPERATIONAL_BINDING_MISMATCH


def test_required_route_materializes_then_reproves_owner(tmp_path: Path) -> None:
    calls = iter((_required(), _ready()))
    observed = []

    def activate(config):
        observed.append(config)
        return SimpleNamespace(
            ok=True, route_committed=True, post_query_replica_unchanged=True,
            error="",
        )

    result = _run(
        tmp_path,
        ensure_operational=lambda **_kwargs: next(calls),
        activate=activate,
    )

    assert result.ready is True
    assert result.refreshed is True
    assert len(observed) == 1
    assert observed[0].replica_root == tmp_path / f"{GENERATION[7:15]}-r1"
    assert observed[0].receipt_path == (
        tmp_path / "runtime" / f"activation_{HEAD[:8]}_r1.json"
    )
    assert observed[0].real is True


def test_existing_candidate_is_never_reused(tmp_path: Path) -> None:
    (tmp_path / f"{GENERATION[7:15]}-r1").mkdir()
    observed = []
    calls = iter((_required(), _ready()))

    result = _run(
        tmp_path,
        ensure_operational=lambda **_kwargs: next(calls),
        activate=lambda config: (
            observed.append(config)
            or SimpleNamespace(
                ok=True, route_committed=True,
                post_query_replica_unchanged=True, error="",
            )
        ),
    )

    assert result.ready is True
    assert observed[0].replica_root.name.endswith("-r2")
    assert observed[0].receipt_path.name.endswith("_r2.json")


def test_missing_or_ambiguous_route_configuration_fails_before_activation(
    tmp_path: Path,
) -> None:
    activations = []
    missing = _run(
        tmp_path,
        environment={},
        activate=lambda config: activations.append(config),
    )
    route = tmp_path / "runtime" / "route.json"
    ambiguous = _run(
        tmp_path,
        environment={
            **_environment(route),
            QUERY_REPLICA_ROOT_ENV: str(tmp_path / "legacy"),
        },
        activate=lambda config: activations.append(config),
    )

    assert missing.error == POSTMERGE_ROUTE_CONFIG_ERROR
    assert ambiguous.error == POSTMERGE_ROUTE_CONFIG_ERROR
    assert activations == []


def test_activation_failure_never_claims_operational(tmp_path: Path) -> None:
    owner_calls = 0

    def owner(**_kwargs):
        nonlocal owner_calls
        owner_calls += 1
        return _required()

    result = _run(
        tmp_path,
        ensure_operational=owner,
        activate=lambda _config: SimpleNamespace(
            ok=False, route_committed=False,
            post_query_replica_unchanged=False,
            error="ACTIVATION_MATERIALIZATION_FAILED",
        ),
    )

    assert result.ready is False
    assert result.error == "ACTIVATION_MATERIALIZATION_FAILED"
    assert owner_calls == 1


def test_post_activation_owner_cannot_substitute_canonical_binding(
    tmp_path: Path,
) -> None:
    calls = iter(
        (
            _required(),
            _ready_with_binding(receipt="sha256:" + ("d" * 64)),
        )
    )
    result = _run(
        tmp_path,
        ensure_operational=lambda **_kwargs: next(calls),
        activate=lambda _config: SimpleNamespace(
            ok=True,
            route_committed=True,
            post_query_replica_unchanged=True,
            error="",
        ),
    )

    assert result.ready is False
    assert result.error == POSTMERGE_OPERATIONAL_BINDING_MISMATCH


def test_malformed_existing_route_failure_is_not_reprobed_or_promoted(
    tmp_path: Path,
) -> None:
    owner_calls = 0

    def owner(**_kwargs):
        nonlocal owner_calls
        owner_calls += 1
        return _required()

    result = _run(
        tmp_path,
        ensure_operational=owner,
        activate=lambda _config: SimpleNamespace(
            ok=False,
            route_committed=False,
            post_query_replica_unchanged=False,
            error="ACTIVATION_ROUTE_STATE_INVALID",
        ),
    )

    assert result.ready is False
    assert result.error == "ACTIVATION_ROUTE_STATE_INVALID"
    assert owner_calls == 1


def test_invalid_current_proof_fails_before_owner_or_activation(tmp_path: Path) -> None:
    effects = []
    invalid = RedDogHoloIndexOperationalResult(False, OPERATIONAL_FAILED)
    result = _run(
        tmp_path,
        current=invalid,
        ensure_operational=lambda **_kwargs: effects.append("owner"),
        activate=lambda _config: effects.append("activation"),
    )

    assert result.ready is False
    assert result.error == "HOLOINDEX_POSTMERGE_CURRENT_PROOF_INVALID"
    assert effects == []
