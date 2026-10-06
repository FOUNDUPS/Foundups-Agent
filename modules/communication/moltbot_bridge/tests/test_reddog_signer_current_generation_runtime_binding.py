"""Tests for audit-only current-generation signer runtime binding."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src import (
    reddog_current_generation_manifest_launch_selection as selection_module,
)
from modules.communication.moltbot_bridge.src import (
    reddog_signer_current_generation_runtime_binding as binding_module,
)
from modules.communication.moltbot_bridge.src.reddog_authoritative_use_lease import (
    AuthoritativeUseLease,
    consume_authoritative_use_lease,
    is_authoritative_use_lease,
)
from modules.communication.moltbot_bridge.src.reddog_signer_current_generation_runtime_binding import (
    SIGNER_CURRENT_GENERATION_BINDING_REJECTED,
    SignerCurrentGenerationRuntimeAuthority,
    SignerCurrentGenerationRuntimeBinding,
    verify_signer_current_generation_runtime_binding,
)
from modules.communication.moltbot_bridge.src.reddog_signer_current_generation_use_time_gate import (
    collect_signer_current_generation_use_time_evidence,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signer_system_service_manifest_selection_loader import (
    NOW,
    _prepare_real_cli_owner,
)


def _fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, object]:
    monkeypatch.setattr(selection_module, "_now_epoch", lambda: NOW)
    return _prepare_real_cli_owner(tmp_path, monkeypatch)


def test_exact_current_generation_round_trip_is_audit_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    values = _fixture(tmp_path, monkeypatch)
    harness = values["harness"]

    result = verify_signer_current_generation_runtime_binding(
        repo_root=harness.repo_root,
        runtime_root=harness.runtime_root,
        run_packet_path=values["packet_path"],
        now_epoch=NOW,
    )

    assert result.accepted is True, result.rejection_reasons
    assert result.receipt_id and result.receipt_id.startswith("sha256:")
    assert result.manifest_id == values["selection"]["manifest_id"]
    assert result.artifact_generation_digest == (
        values["selection"]["artifact_generation_digest"]
    )
    assert result.authority_granted is False
    assert result.effect_capability_issued is False


def test_use_time_evidence_removes_only_bound_generation_reasons(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    values = _fixture(tmp_path, monkeypatch)
    harness = values["harness"]
    evidence = collect_signer_current_generation_use_time_evidence(
        True, harness.repo_root, harness.runtime_root, lambda: NOW
    )
    reasons = ("manifest", "replay", "generation", "peer", "consensus")

    assert evidence.receipt_id is not None
    assert evidence.remaining_reasons(
        reasons, ("manifest", "replay", "generation")
    ) == ("peer", "consensus")
    assert collect_signer_current_generation_use_time_evidence(
        False, harness.repo_root, harness.runtime_root, lambda: NOW
    ).remaining_reasons(reasons, reasons) == reasons


def test_trusted_clock_is_used_for_manifest_freshness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    values = _fixture(tmp_path, monkeypatch)
    harness = values["harness"]
    observed: list[int] = []

    def reject_with_observed_clock(_payload, *, now_epoch, max_ttl_seconds):
        observed.append(now_epoch)
        assert max_ttl_seconds > 0
        raise ValueError("trusted_clock_expired")

    monkeypatch.setattr(binding_module, "validate_freshness", reject_with_observed_clock)
    result = verify_signer_current_generation_runtime_binding(
        repo_root=harness.repo_root,
        runtime_root=harness.runtime_root,
        run_packet_path=values["packet_path"],
        now_epoch=NOW + 7,
    )

    assert result.accepted is False
    assert observed == [NOW + 7]


def test_changed_run_packet_with_old_manifest_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    values = _fixture(tmp_path, monkeypatch)
    harness = values["harness"]
    packet_path = values["packet_path"]
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet["session_id"] = "attacker-session"
    packet_path.write_text(
        json.dumps(packet, sort_keys=True, separators=(",", ":")),
        encoding="ascii",
    )

    result = verify_signer_current_generation_runtime_binding(
        repo_root=harness.repo_root,
        runtime_root=harness.runtime_root,
        run_packet_path=packet_path,
        now_epoch=NOW,
    )

    assert result.accepted is False
    assert result.rejection_reasons == (
        SIGNER_CURRENT_GENERATION_BINDING_REJECTED,
    )


def test_changed_config_and_wrong_runtime_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    values = _fixture(tmp_path, monkeypatch)
    harness = values["harness"]
    config_path = values["config_path"]
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["timeout_s"] = int(config["timeout_s"]) + 1
    config_path.write_text(
        json.dumps(config, sort_keys=True, separators=(",", ":")),
        encoding="ascii",
    )

    changed = verify_signer_current_generation_runtime_binding(
        repo_root=harness.repo_root,
        runtime_root=harness.runtime_root,
        run_packet_path=values["packet_path"],
        now_epoch=NOW,
    )
    wrong_root = verify_signer_current_generation_runtime_binding(
        repo_root=harness.repo_root,
        runtime_root=tmp_path / "other-runtime",
        run_packet_path=values["packet_path"],
        now_epoch=NOW,
    )

    assert changed.accepted is False
    assert wrong_root.accepted is False


def test_external_authority_lease_remains_unavailable() -> None:
    with pytest.raises(TypeError):
        AuthoritativeUseLease(lambda: True)
    fabricated = object.__new__(AuthoritativeUseLease)
    assert is_authoritative_use_lease(fabricated) is False
    assert consume_authoritative_use_lease(fabricated) is False


def test_root_authority_forwards_exact_signer_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed: list[dict[str, object]] = []
    expected = SignerCurrentGenerationRuntimeBinding(True, ())

    def verify(**values):
        observed.append(values)
        return expected

    monkeypatch.setattr(
        binding_module, "verify_signer_current_generation_runtime_binding", verify
    )
    authority = SignerCurrentGenerationRuntimeAuthority(tmp_path, tmp_path / "runtime")

    assert authority.resolve(
        now_epoch=NOW, signer_profile_id="reddog-work-authority"
    ) is expected
    assert observed[0]["signer_profile_id"] == "reddog-work-authority"


def test_selected_signer_identity_comes_from_rehydrated_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class Config:
        key_provider_profile = None
        key_provider_profiles = (
            {
                "signer_profile_id": "reddog-work-authority",
                "expected_public_key": "ed25519-public-raw-b64-v1:test",
                "expected_key_epoch": "epoch-7",
            },
        )

    monkeypatch.setattr(
        binding_module,
        "rehydrate_signer_socket_service_runtime_config",
        lambda *_args, **_kwargs: Config(),
    )
    result = binding_module._selected_signer_identity(
        config_raw=b"{}",
        config_digest="sha256:" + "1" * 64,
        repo=tmp_path,
        runtime=tmp_path / "runtime",
        signer_profile_id="reddog-work-authority",
    )

    assert result == {
        "signer_profile_id": "reddog-work-authority",
        "signer_public_key": "ed25519-public-raw-b64-v1:test",
        "key_epoch": "epoch-7",
    }
    with pytest.raises(ValueError, match="signer_profile_not_current"):
        binding_module._selected_signer_identity(
            config_raw=b"{}",
            config_digest="sha256:" + "1" * 64,
            repo=tmp_path,
            runtime=tmp_path / "runtime",
            signer_profile_id="attacker-profile",
        )


def test_slice_preserves_no_effect_and_wsp62_boundaries() -> None:
    bridge_root = Path(__file__).parents[1]
    source_paths = tuple(
        bridge_root / "src" / name
        for name in (
            "reddog_authoritative_use_lease.py",
            "reddog_signer_current_generation_runtime_binding.py",
            "reddog_signer_current_generation_use_time_gate.py",
        )
    )
    combined = "\n".join(path.read_text(encoding="utf-8") for path in source_paths)
    for forbidden in (
        "subprocess",
        "os.system",
        "shell=True",
        "HoloIndex.reindex",
        "commit_all",
        "gh pr",
        "issue_authoritative_use_lease",
    ):
        assert forbidden not in combined
    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        assert len(source.splitlines()) <= 675
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.end_lineno is not None
                assert node.end_lineno - node.lineno + 1 <= 60
            if isinstance(node, ast.ClassDef):
                assert node.end_lineno is not None
                assert node.end_lineno - node.lineno + 1 <= 200


@pytest.mark.parametrize("abort", [False, True])
def test_generation_lease_keeps_real_selection_boundary_until_exit(tmp_path, monkeypatch, abort):
    from contextlib import contextmanager

    values = _fixture(tmp_path, monkeypatch)
    harness = values["harness"]
    original = selection_module._Boundary._lease_current
    active = []

    @contextmanager
    def observed(self, capability):
        with original(self, capability) as selected:
            active.append(True)
            try:
                yield selected
            finally:
                active.pop()

    monkeypatch.setattr(selection_module._Boundary, "_lease_current", observed)
    def consume():
        with binding_module._lease_current_generation_runtime_binding(
            repo_root=harness.repo_root, runtime_root=harness.runtime_root,
            run_packet_path=values["packet_path"], now_epoch=NOW,
        ) as binding:
            assert binding.accepted, binding.rejection_reasons
            assert active == [True]
            if abort:
                raise RuntimeError("consumer_abort")
    if abort:
        with pytest.raises(RuntimeError, match="consumer_abort"):
            consume()
    else:
        consume()
    assert active == []


def test_rehydration_commits_inside_generation_lease(tmp_path, monkeypatch):
    from contextlib import contextmanager
    from modules.communication.moltbot_bridge.src import reddog_authoritative_use_lease as leases
    from modules.communication.moltbot_bridge.tests.test_reddog_external_signer_authoritative_use_lease import (
        NOW as LEASE_NOW, _authority, _backend, _current_generation, _peer, _request, _store,
    )

    monkeypatch.setattr(leases.time, "time", lambda: LEASE_NOW)
    store = _store(tmp_path)
    request = _request(store)
    response = _backend(request, exact=True).sign(request, _peer())
    authority = _authority(tmp_path, monkeypatch)
    active, events = [], []

    @contextmanager
    def held(self, **kwargs):
        active.append(True)
        try:
            yield _current_generation()
        finally:
            active.pop()

    monkeypatch.setattr(SignerCurrentGenerationRuntimeAuthority, "lease", held)
    for owner, name in ((leases, "_response_valid"),
                        (type(store), "consume_authoritative_use_lease"),
                        (leases._LEASES, "issue")):
        original = getattr(owner, name)
        def checked(*args, _original=original, _name=name, **kwargs):
            assert active == [True], _name
            events.append(_name)
            return _original(*args, **kwargs)
        monkeypatch.setattr(owner, name, checked)
    result = leases._rehydrate_external_authoritative_use_lease(
        request=request, response=response, current_generation_authority=authority,
        replay_store=store, now_epoch=LEASE_NOW,
    )
    assert result is not None
    assert events == ["_response_valid", "consume_authoritative_use_lease", "issue"]
    assert active == []


def test_snapshot_binding_rejects_selection_exit_failure(tmp_path, monkeypatch):
    from contextlib import contextmanager

    values = _fixture(tmp_path, monkeypatch)
    harness = values["harness"]
    original = selection_module._Boundary._lease_current

    @contextmanager
    def failing_exit(self, capability):
        with original(self, capability) as selected:
            yield selected
        raise OSError("synthetic_release_failure")

    monkeypatch.setattr(selection_module._Boundary, "_lease_current", failing_exit)
    result = verify_signer_current_generation_runtime_binding(
        repo_root=harness.repo_root, runtime_root=harness.runtime_root,
        run_packet_path=values["packet_path"], now_epoch=NOW,
    )
    assert result.accepted is False
    assert result.rejection_reasons == (SIGNER_CURRENT_GENERATION_BINDING_REJECTED,)


@pytest.mark.parametrize("interrupt", [KeyboardInterrupt, SystemExit])
def test_generation_validation_interrupt_releases_selection(tmp_path, monkeypatch, interrupt):
    from contextlib import contextmanager

    values = _fixture(tmp_path, monkeypatch)
    harness = values["harness"]
    original = selection_module._Boundary._lease_current
    active = []

    @contextmanager
    def observed(self, capability):
        with original(self, capability) as selected:
            active.append(True)
            try:
                yield selected
            finally:
                active.pop()

    def interrupted(**kwargs):
        assert active == [True]
        raise interrupt("synthetic_validation_interrupt")

    monkeypatch.setattr(selection_module._Boundary, "_lease_current", observed)
    monkeypatch.setattr(binding_module, "_validated_values", interrupted)
    with pytest.raises(interrupt):
        verify_signer_current_generation_runtime_binding(
            repo_root=harness.repo_root, runtime_root=harness.runtime_root,
            run_packet_path=values["packet_path"], now_epoch=NOW,
        )
    assert active == []
