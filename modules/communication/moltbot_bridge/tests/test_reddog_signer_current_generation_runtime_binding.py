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


def _principal_fixture(tmp_path, monkeypatch):
    from modules.communication.moltbot_bridge.tests import (
        test_reddog_signer_system_service_manifest_selection_loader as owner_tests,
    )
    original = owner_tests._build_harness
    def build(path):
        harness = original(path)
        identity = harness.identity
        record = {key: identity[key] for key in (
            "principal_id", "principal_provider", "principal_public_key", "repo_scope", "foundup_scope")}
        record.update(verified_subject_digest="sha256:" + "d" * 64,
                      reward_account=None, owner_dae=None, principal_wallet=None)
        payload = {"schema_version": "reddog_authority_runtime_resolver_supply.v1",
                   "principals": {record["principal_provider"] + "|" + record["principal_id"]: record},
                   "principal_count": 1, "resolver_supply_receipt_id": "sha256:" + "e" * 64,
                   "no_holoindex_reindex_performed": True}
        (harness.runtime_root / "principal_authority_records.json").write_text(
            json.dumps(payload), encoding="ascii")
        return harness
    monkeypatch.setattr(owner_tests, "_build_harness", build)
    return _fixture(tmp_path, monkeypatch)


@pytest.mark.parametrize("case", ["valid", "wrong-key", "wrong-id", "wrong-provider",
    "wrong-repo", "wrong-foundup", "missing-key", "missing-authority", "changed-artifact", "expired"])
def test_principal_binding_uses_current_signed_generation(tmp_path, monkeypatch, case):
    values = _principal_fixture(tmp_path, monkeypatch)
    harness = values["harness"]
    path = harness.runtime_root / "principal_authority_records.json"
    artifact = json.loads(path.read_text("ascii"))
    record = next(iter(artifact["principals"].values()))
    identity = {key: record[key] for key in (
        "principal_id", "principal_provider", "principal_public_key")}
    authority = {"principal_id": identity["principal_id"],
                 "repo_full_name": record["repo_scope"][0],
                 "foundup_id": record["foundup_scope"][0]}
    changes = {"wrong-key": (identity, "principal_public_key"),
               "wrong-id": (identity, "principal_id"),
               "wrong-provider": (identity, "principal_provider"),
               "wrong-repo": (authority, "repo_full_name"),
               "wrong-foundup": (authority, "foundup_id")}
    if case in changes:
        target, key = changes[case]
        target[key] = "not-the-admitted-value"
    if case == "missing-key":
        identity.pop("principal_public_key")
    if case == "missing-authority":
        authority = None
    if case == "changed-artifact":
        record["principal_public_key"] = "substituted-key"
        path.write_text(json.dumps(artifact), encoding="ascii")
    result = verify_signer_current_generation_runtime_binding(
        repo_root=harness.repo_root, runtime_root=harness.runtime_root,
        now_epoch=NOW + 86400 if case == "expired" else NOW,
        principal_identity=identity, principal_work_authority=authority,
    )
    assert result.accepted is (case == "valid")
    if case == "valid":
        assert result.principal_binding_digest == binding_module._digest(
            {"identity": identity, "work_authority": authority})
    else:
        assert result.principal_binding_digest is None
    assert result.authority_granted is False
    assert result.effect_capability_issued is False


@pytest.mark.parametrize("target", ["key", "scope"])
def test_principal_mapping_change_during_read_fails_closed(tmp_path, monkeypatch, target):
    from modules.communication.moltbot_bridge.src import reddog_signer_owner_e0_principal_authority as owner
    values = _principal_fixture(tmp_path, monkeypatch)
    harness = values["harness"]
    identity, authority = dict(harness.identity), dict(harness.work_authority)
    original = owner.load_current_generation_principal_authority_resolver
    called = []
    def load(**kwargs):
        result = original(**kwargs)
        called.append(True)
        if target == "key":
            identity["principal_public_key"] = "substituted-key"
        else:
            authority["foundup_id"] = "other-foundup"
        return result
    monkeypatch.setattr(owner, "load_current_generation_principal_authority_resolver", load)
    result = verify_signer_current_generation_runtime_binding(
        repo_root=harness.repo_root, runtime_root=harness.runtime_root, now_epoch=NOW,
        principal_identity=identity, principal_work_authority=authority)
    assert called == [True]
    assert result.accepted is False and result.principal_binding_digest is None


def test_real_principal_evidence_matches_only_checked_work(tmp_path, monkeypatch):
    values = _principal_fixture(tmp_path, monkeypatch)
    harness = values["harness"]
    identity, authority = dict(harness.identity), dict(harness.work_authority)
    evidence = collect_signer_current_generation_use_time_evidence(
        True, harness.repo_root, harness.runtime_root, lambda: NOW,
        principal_identity=identity, principal_work_authority=authority)
    assert evidence.receipt_id is not None
    assert evidence.principal_matches(identity, authority)
    authority["work_order_id"] = "another-work-order"
    assert not evidence.principal_matches(identity, authority)


@pytest.mark.parametrize("case", ["current", "owner-rotated", "missing-v2-owner"])
def test_generation_process_identity_is_bound_to_selected_owner(tmp_path, monkeypatch, case):
    from unittest.mock import Mock
    values = _fixture(tmp_path, monkeypatch)
    harness = values["harness"]
    loader = Mock(return_value=(1234, 1235))
    if case == "owner-rotated":
        loader.side_effect = ValueError("signer_owner_selection_mismatch")
    if case != "missing-v2-owner":
        monkeypatch.setattr(binding_module, "load_system_service_signer_identity", loader)
    result = verify_signer_current_generation_runtime_binding(
        repo_root=harness.repo_root, runtime_root=harness.runtime_root, now_epoch=NOW,
        include_process_identity=True)
    assert result.accepted is (case == "current")
    assert (result.signer_uid, result.signer_gid) == ((1234, 1235) if case == "current" else (None, None))
    if case != "missing-v2-owner":
        loader.assert_called_once_with(owner_config_path=values["owner_path"].resolve(),
            repo_root=harness.repo_root.resolve(), expected_owner_config_id=json.loads(values["owner_path"].read_text("ascii"))["config_id"])
    assert not result.authority_granted and not result.effect_capability_issued


@pytest.mark.parametrize("case", ["renewed", "manifest-expired-during-read"])
def test_peer_connection_uses_real_renewed_generation(tmp_path, monkeypatch, case):
    from modules.communication.moltbot_bridge.src import reddog_signer_current_generation_use_time_gate as gate
    from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_healthcheck import SignerServiceHealthcheckResult
    values = _principal_fixture(tmp_path, monkeypatch)
    harness = values["harness"]
    initial = NOW if case == "renewed" else harness.read_manifest()["expires_at"]-2
    now = [initial]
    monkeypatch.setattr(selection_module, "_now_epoch", lambda: now[0] if case == "renewed" else initial)
    monkeypatch.setattr(binding_module, "load_system_service_signer_identity", lambda **_: (1234,1235))
    # Legacy fixture has no enrolled v2 process/profile owner; isolate selection producer.
    monkeypatch.setattr(binding_module, "_selected_signer_identity", lambda **_: {
        "signer_profile_id":"reddog-work-authority", "signer_public_key":harness.reddog_public_key,
        "key_epoch":"fixture-epoch"})
    observed = []
    real_verify = gate.verify_signer_current_generation_runtime_binding
    def verify(**kwargs):
        result = real_verify(**kwargs)
        observed.append(result)
        if case == "manifest-expired-during-read" and len(observed) == 2:
            now[0] = harness.read_manifest()["expires_at"]
        return result
    monkeypatch.setattr(gate, "verify_signer_current_generation_runtime_binding", verify)
    def probe(**kwargs):
        before=observed[0]
        assert before.accepted, before.rejection_reasons
        now[0]+=1
        return SignerServiceHealthcheckResult(True, "READY", str(values["packet_path"]),
            before.run_packet_id, "fixture-config", before.config_digest, "fixture-socket",
            before.signer_profile_id, before.signer_public_key, kwargs["requester_principal_id"],
            "sha256:"+"a"*64,"sha256:"+"b"*64,(),manifest_id=before.manifest_id,
            artifact_generation_digest=before.artifact_generation_digest,peer_handshake_verified=True,
            peer_handshake_expires_at=initial+600,session_id=before.session_id,
            socket_path_digest=before.socket_path_digest,key_epoch=before.key_epoch,server_identity_verified=True)
    monkeypatch.setattr(gate,"run_reddog_signer_socket_service_healthcheck",probe)
    result=gate.collect_signer_current_generation_use_time_evidence(True,harness.repo_root,
        harness.runtime_root,lambda:now[0],principal_identity=dict(harness.identity),
        principal_work_authority=dict(harness.work_authority),peer_secret_access_grant_supplier=lambda request:{})
    assert len(observed)==2 and all(b.accepted for b in observed)
    assert (observed[0].selection_expires_at != observed[1].selection_expires_at) is (case == "renewed")
    assert result.peer_verified is (case=="renewed")


@pytest.mark.parametrize("case", ["valid", "wrong-authority", "wrong-digest", "missing",
    "owner-rotated", "expired-after-crypto", "boolean-clock", "work-mutated", "clock-reversed-after-crypto", "collector-clock-reversed"])
def test_current_generation_consumes_protected_model_pair(tmp_path, monkeypatch, case):
    from modules.communication.moltbot_bridge.tests.test_reddog_signer_system_service_startup_authority import (
        _model_input_owner_case, _real_model_evidence_signatures,
    )
    from modules.communication.moltbot_bridge.src.reddog_work_order_binding import canonical_full_work_order_digest
    from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_digest import canonical_model_runtime_binding_digest
    from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_use_time_verifier import ModelRuntimeBindingUseTimeVerifier
    _real_model_evidence_signatures(monkeypatch)
    values, owner, _ = _model_input_owner_case(tmp_path, monkeypatch)
    now = [NOW]
    monkeypatch.setattr(selection_module, "_now_epoch", lambda: NOW)
    pair = dict(model_selection_receipt=values["model_selection"],
                model_runtime_binding_receipt=values["model_binding"])
    work = dict(work_order_id="model-current-use", operational_context_binding=pair,
        model_selection_receipt_id=pair["model_selection_receipt"]["receipt_id"],
        model_selection_digest=binding_module._digest(pair["model_selection_receipt"]),
        model_runtime_binding_receipt_id=pair["model_runtime_binding_receipt"]["receipt_id"],
        model_runtime_binding_digest=canonical_model_runtime_binding_digest(pair["model_runtime_binding_receipt"]))
    authority = dict(work, work_order_digest=canonical_full_work_order_digest(work))
    if case == "wrong-authority":
        authority["model_selection_receipt_id"] = "wrong"
    if case == "wrong-digest":
        work["model_runtime_binding_digest"] = "sha256:" + "0" * 64
        authority.update(work, work_order_digest=canonical_full_work_order_digest(work))
    if case == "missing":
        work.pop("operational_context_binding")
        authority["work_order_digest"] = canonical_full_work_order_digest(work)
    # Principal signature/subject verification has separate connected coverage.
    # This seam isolates real generation selection, owner input and model crypto.
    monkeypatch.setattr(binding_module, "_validated_principal_digest",
        lambda repo, selection, identity, work_authority: binding_module._digest(
            {"identity": identity, "work_authority": work_authority}))
    original, observed = ModelRuntimeBindingUseTimeVerifier.verify, []
    def verify(self, **kwargs):
        if case in {"clock-reversed-after-crypto", "collector-clock-reversed"}:
            now[0] = NOW + 5
        capability = original(self, **kwargs)
        observed.append(capability)
        if case == "clock-reversed-after-crypto":
            now[0] = NOW + 2
        if case == "expired-after-crypto":
            now[0] = owner["model_verifier_authority"]["expires_at"]
        elif case == "boolean-clock":
            now[0] = True
        elif case == "owner-rotated":
            owner["model_verifier_authority"]["expires_at"] += 1
            owner["config_id"] = binding_module._digest({k:v for k,v in owner.items() if k != "config_id"})
            values["owner_config_path"].write_text(json.dumps(owner), encoding="ascii")
        elif case == "work-mutated":
            work["work_order_id"] = "changed"
        return capability
    monkeypatch.setattr(ModelRuntimeBindingUseTimeVerifier, "verify", verify)
    result = verify_signer_current_generation_runtime_binding(repo_root=values["repo"],
        runtime_root=Path(owner["runtime_root"]), run_packet_path=values["packet_path"],
        now_epoch=NOW, principal_identity={"principal_id":"fixture"},
        principal_work_authority=authority, model_work_order=work,
        trusted_now_epoch=lambda: now[0])
    assert result.accepted, result.rejection_reasons
    assert (result.model_work_order_digest is not None) is (case in {"valid", "collector-clock-reversed"})
    if case in {"valid", "collector-clock-reversed"}:
        assert observed and result.model_work_order_digest == canonical_full_work_order_digest(work)
        assert result.model_valid_until == owner["model_verifier_authority"]["expires_at"]
        if case == "collector-clock-reversed":
            from modules.communication.moltbot_bridge.src import reddog_signer_current_generation_use_time_gate as gate
            real_verify = gate.verify_signer_current_generation_runtime_binding
            producer_digests = []
            def reversed_after_producer(**kwargs):
                result = real_verify(**kwargs)
                producer_digests.append(result.model_work_order_digest)
                now[0] = NOW + 2
                return result
            monkeypatch.setattr(gate, "verify_signer_current_generation_runtime_binding", reversed_after_producer)
            now[0] = NOW
        evidence = collect_signer_current_generation_use_time_evidence(True, values["repo"],
            Path(owner["runtime_root"]), lambda: now[0], principal_identity={"principal_id":"fixture"},
            principal_work_authority=authority, model_work_order=work)
        assert evidence.model_matches(work) is (case == "valid")
        if case == "collector-clock-reversed":
            assert producer_digests == [canonical_full_work_order_digest(work)]
            return
        assert set(evidence.bound_identity_reasons({"principal_id":"fixture"}, authority, work)) == {
            "canonical_principal_subject_key_attestation_missing",
            "canonical_model_signed_evidence_trust_anchor_incomplete",
            "canonical_model_selection_signed_evidence_verifier_missing"}
        work["task_summary"] = "substituted after collection"
        assert not evidence.model_matches(work)
    if case in {"owner-rotated", "expired-after-crypto", "boolean-clock", "work-mutated", "clock-reversed-after-crypto"}:
        assert observed, "negative control must reach actual cryptography"
    from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_verified_admission import consume_verified_runtime_binding_capability, verified_runtime_binding_receipt
    for capability in observed:
        assert consume_verified_runtime_binding_capability(capability,
            selection=values["model_selection"], binding=values["model_binding"],
            receipt=verified_runtime_binding_receipt(values["model_binding"])) is None
