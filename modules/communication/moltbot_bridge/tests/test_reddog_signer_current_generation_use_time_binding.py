"""Use-time integration tests for current signer generation evidence."""

from __future__ import annotations

import json

import pytest

from modules.communication.moltbot_bridge.src import (
    reddog_execution_valve_use_time_authority as use_time_module,
)
from modules.communication.moltbot_bridge.src import (
    reddog_signer_current_generation_use_time_gate as gate_module,
)
from modules.communication.moltbot_bridge.src.reddog_execution_valve_use_time_authority import (
    AUTHENTICATED_RUNTIME_ARTIFACT_MANIFEST_SELECTION_MISSING,
    CURRENT_RUNTIME_ARTIFACT_GENERATION_VERIFIER_MISSING,
    DURABLE_RUNTIME_ARTIFACT_MANIFEST_REPLAY_STATE_MISSING,
    GovernedValveUseTimeAuthorityResolver,
    _digest,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    InMemoryResidentQueueChainResultsStore,
)
from modules.communication.moltbot_bridge.src.reddog_signer_current_generation_runtime_binding import (
    SignerCurrentGenerationRuntimeBinding,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_binding import (
    canonical_full_work_order_digest,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    VerificationResult,
)
from modules.communication.moltbot_bridge.tests.reddog_resident_live_canary_test_support import (
    QUEUE_ID,
    _roots,
)


NOW_EPOCH = 1_784_006_400
SLICE = "REDDOG_TEST_SLICE_PHASE1"


def _authority_state(work_order_id: str, work_order: dict[str, object]):
    work_authority = {
        "work_order_id": work_order_id,
        "work_order_digest": canonical_full_work_order_digest(work_order),
        "base_ref": "main",
        "nonce": "nonce-use-time-generation",
        "expires_at": NOW_EPOCH + 300,
    }
    stages = {
        "authority_runtime": {
            "decision": "QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT",
            "authority_result": {
                "accepted": True,
                "receipt": {
                    "status": "DELEGATED_AUTHORITY_ISSUED",
                    "work_authority_digest": _digest(work_authority),
                },
                "identity": {"principal_id": "github:mjtrout"},
                "work_authority": work_authority,
            },
        },
        "authority_verification": {
            "decision": "QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT",
            "verification_result": {
                "accepted": True,
                "work_order_id": work_order_id,
            },
        },
    }
    return _chain_store(stages)


def _chain_store(stages):
    store = InMemoryResidentQueueChainResultsStore()
    store.commit(
        {
            "schema_version": "reddog_resident_queue_chain_results.v1",
            "queue_item_id": QUEUE_ID,
            "selected_slice": SLICE,
            "stage_results": stages,
            "receipts": [{"store_revision": None}],
        },
        expected_revision=None,
    )
    return store


def _consistent_authority_state(resolver):
    """Internally bound fixture; signature acceptance remains explicitly synthetic."""
    artifacts, reasons = use_time_module._read_runtime_artifacts(resolver)
    expected = resolver._resolve_expected(artifacts, QUEUE_ID, reasons)
    queue = resolver._validate_queue(artifacts, QUEUE_ID, reasons)
    assert reasons == [], reasons
    work = dict(expected, base_ref="main")
    work.update({
        "allowed_paths": artifacts["authority_profile"]["allowed_paths"],
        "denied_paths": artifacts["authority_profile"]["denied_paths"],
        "repo_permission_snapshot": {"digest": expected["permission_snapshot_digest"]},
        "wsp15_allocation_receipt": {"receipt_id": expected["wsp15_allocation_receipt_id"]},
        **{key: queue.get(key) for key in (
            "wsp15_priority", "wsp15_mps_total",
        )},
        "wsp15_reasoning_tier": queue["reasoning_tier"],
    })
    authority = dict(work, work_order_digest=canonical_full_work_order_digest(work))
    authority.update({
        "nonce": "synthetic-generation-fixture", "expires_at": NOW_EPOCH + 300,
        "signer_public_key": "synthetic-public-identity",
        "selected_slice": queue["slice_id"],
        "queue_consumer_receipt_digest": canonical_full_work_order_digest(queue),
        **{key: queue.get(key) for key in (
            "progressive_policy_stage_receipt_id", "progressive_policy_stage_digest",
        )},
    })
    identity = {key: authority[key] for key in ("principal_id", "reddog_id")}
    identity.update(reddog_public_key=authority["signer_public_key"],
                    repo_scope=[authority["repo_full_name"]],
                    foundup_scope=[authority["foundup_id"]])
    stages = _authority_state(work["work_order_id"], work).load()["stage_results"]
    stages["authority_runtime"]["authority_result"].update(
        identity=identity, work_authority=authority,
        receipt={
            "receipt_id": "synthetic-recorded-receipt", "status": use_time_module.AUTHORITY_ISSUED,
            "work_order_id": work["work_order_id"], "generated_at": NOW_EPOCH,
            "identity_digest": _digest(identity), "work_authority_digest": _digest(authority),
        },
    )
    assert authority["selected_slice"] == SLICE
    return _chain_store(stages), work


def _complete_queue_fixture(repo, runtime):
    """Bring disposable historical artifacts up to the current queue contract."""
    from datetime import datetime, timezone
    from modules.communication.moltbot_bridge.tests.reddog_resident_queue_test_helpers import (
        governed_worker_dispatch_snapshot,
    )
    from modules.communication.moltbot_bridge.tests.reddog_live_canary_artifact_test_support import (
        _write_valve,
    )

    path = runtime / "authoritative_work_state.json"
    state = json.loads(path.read_text("utf-8"))
    queue, claim = state["wre_queue_items"][0], state["worker_claims"][0]
    claim["expires_at"] = datetime.fromtimestamp(NOW_EPOCH + 300, timezone.utc).isoformat()
    verification = {
        "model_runtime_binding_verification_receipt_id": "model_runtime_binding_verification:" + "d" * 64,
        "model_runtime_binding_verification_digest": "sha256:" + "e" * 64,
    }
    queue.update(verification)
    claim.update(verification)
    state = governed_worker_dispatch_snapshot(state)
    state.pop("revision", None)
    state["revision"] = _digest(state).removeprefix("sha256:")
    path.write_text(json.dumps(state), encoding="utf-8")
    profile = json.loads((runtime / "authority_profile.json").read_text("utf-8"))
    _write_valve(repo, runtime, state, profile, QUEUE_ID, NOW_EPOCH)


def _resolver(repo, runtime) -> GovernedValveUseTimeAuthorityResolver:
    return GovernedValveUseTimeAuthorityResolver(
        repo_root=repo,
        work_state_path=runtime / "authoritative_work_state.json",
        authority_profile_path=runtime / "authority_profile.json",
        permission_snapshots_path=runtime / "permission_snapshots.json",
        principal_authority_records_path=runtime / "principal_authority_records.json",
        valve_environment_path=runtime / "execution_valve_env.json",
        runtime_allowed_root=runtime,
        signature_verifier=object(),
        principal_key_resolver=object(),
        nonce_store=object(),
        snapshot_resolver=object(),
        revocation_oracle=object(),
        now_epoch=NOW_EPOCH,
        required_valve_state="VALVE_OPEN_WORKTREE_CREATE",
        trusted_now_epoch=lambda: NOW_EPOCH,
    )


def test_resolver_removes_only_three_verified_generation_blockers(
    tmp_path, monkeypatch,
) -> None:
    repo, runtime, resolver, store, work_order, _, _, _ = (
        _generation_projection_case(tmp_path, monkeypatch, "typed-accepted")
    )
    receipt_id = "sha256:" + "a" * 64
    result = resolver.resolve(
        chain_state=store.load(),
        work_order=work_order,
        queue_item_id=QUEUE_ID,
        selected_slice=SLICE,
    )

    assert AUTHENTICATED_RUNTIME_ARTIFACT_MANIFEST_SELECTION_MISSING not in result.rejection_reasons
    assert DURABLE_RUNTIME_ARTIFACT_MANIFEST_REPLAY_STATE_MISSING not in result.rejection_reasons
    assert CURRENT_RUNTIME_ARTIFACT_GENERATION_VERIFIER_MISSING not in result.rejection_reasons
    assert "canonical_signer_client_peer_handshake_verifier_missing" in result.rejection_reasons
    assert result.authoritative_use_lease is None
    assert result.signer_generation_binding_receipt_id == receipt_id


@pytest.mark.parametrize(
    "proof",
    (
        {"accepted": True, "receipt_id": "sha256:" + "a" * 64},
        SignerCurrentGenerationRuntimeBinding(
            accepted=False,
            rejection_reasons=("rejected",),
            receipt_id="sha256:" + "a" * 64,
        ),
    ),
)
def test_binding_requires_typed_accepted_digest(tmp_path, monkeypatch, proof) -> None:
    monkeypatch.setattr(
        gate_module,
        "verify_signer_current_generation_runtime_binding",
        lambda **_: proof,
    )
    result = gate_module.collect_signer_current_generation_use_time_evidence(
        enabled=True,
        repo_root=tmp_path / "repo",
        runtime_root=tmp_path / "runtime",
        trusted_now_epoch=lambda: 100,
    )
    assert result.receipt_id is None


def test_binding_dependency_failure_is_fail_closed(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        gate_module,
        "verify_signer_current_generation_runtime_binding",
        lambda **_: (_ for _ in ()).throw(RuntimeError("dependency failed")),
    )
    result = gate_module.collect_signer_current_generation_use_time_evidence(
        enabled=True,
        repo_root=tmp_path / "repo",
        runtime_root=tmp_path / "runtime",
        trusted_now_epoch=lambda: 100,
    )
    assert result.receipt_id is None


def _generation_projection_case(tmp_path, monkeypatch, case: str, *, consistent=True):
    """Supply synthetic verifier results, never the native selection loader."""
    from dataclasses import replace
    from unittest.mock import Mock

    repo, runtime = _roots(tmp_path, canonical_artifacts=True)
    valve = json.loads((runtime / "execution_valve_env.json").read_text("utf-8"))
    work_order = {"work_order_id": valve["work_order_id"], "base_ref": "main"}
    resolver = _resolver(repo, runtime)
    if consistent:
        _complete_queue_fixture(repo, runtime)
        store, work_order = _consistent_authority_state(resolver)
    else:
        store = _authority_state(valve["work_order_id"], work_order)
    signed = Mock(return_value=VerificationResult(
        accepted=case != "signed-work-rejected", work_order_id=valve["work_order_id"],
        reason_codes=["synthetic_rejection"] if case == "signed-work-rejected" else [],
    ))
    proof = SignerCurrentGenerationRuntimeBinding(
        accepted=case != "typed-rejected",
        rejection_reasons=("synthetic_rejection",) if case == "typed-rejected" else (),
        receipt_id="malformed" if case == "malformed-digest" else "sha256:" + "a" * 64,
    )
    if case == "untyped-mapping":
        proof = {"accepted": True, "receipt_id": "sha256:" + "a" * 64}
    generation = Mock(return_value=proof)
    if case == "verifier-exception":
        generation.side_effect = RuntimeError("synthetic generation failure")
    clock = Mock(return_value=NOW_EPOCH)
    if case == "clock-exception":
        clock.side_effect = RuntimeError("synthetic clock failure")
    monkeypatch.setattr(use_time_module, "verify_delegated_work_authority", signed)
    monkeypatch.setattr(gate_module, "verify_signer_current_generation_runtime_binding", generation)
    resolver = replace(resolver, trusted_now_epoch=clock)
    assert (
        use_time_module.collect_signer_current_generation_use_time_evidence
        is gate_module.collect_signer_current_generation_use_time_evidence
    )
    return repo, runtime, resolver, store, work_order, signed, clock, generation


def _assert_readiness_retains_generation_gates(repo, runtime, spies) -> None:
    from modules.communication.moltbot_bridge.src.reddog_resident_runtime_artifact_readiness import (
        validate_reddog_resident_runtime_artifacts,
    )

    before_calls = tuple(spy.call_count for spy in spies)
    readiness = validate_reddog_resident_runtime_artifacts(
        repo_root=repo, runtime_root=runtime, queue_item_id=QUEUE_ID, now_epoch=NOW_EPOCH,
    )
    checks = {check.filename: check for check in readiness.checks}
    generation_reasons = set(use_time_module.CURRENT_GENERATION_TRUST_ANCHOR_REASONS)
    assert readiness.accepted is False
    assert len(checks) == 7
    assert generation_reasons.intersection(
        checks["execution_valve_env.json"].rejection_reasons
    ) == generation_reasons
    assert "signer_client_peer_handshake_verifier_missing" in (
        checks["signer_service_config.json"].rejection_reasons
    )
    assert tuple(spy.call_count for spy in spies) == before_calls


@pytest.mark.parametrize(
    "case",
    [
        "typed-accepted", "typed-rejected", "malformed-digest", "untyped-mapping",
        "verifier-exception", "signed-work-rejected", "clock-exception",
    ],
    ids=[
        "typed-accepted", "typed-rejected", "malformed-digest", "untyped-mapping",
        "verifier-exception", "signed-work-rejected", "clock-exception",
    ],
)
def test_generation_projection_does_not_change_resident_readiness(tmp_path, monkeypatch, case: str) -> None:
    """Real binding checks and collector; synthetic signatures grant no lease."""
    repo, runtime, resolver, store, work_order, signed, clock, generation = (
        _generation_projection_case(tmp_path, monkeypatch, case)
    )
    before_bytes = {path.name: path.read_bytes() for path in runtime.glob("*.json")}

    result = resolver.resolve(
        chain_state=store.load(), work_order=work_order,
        queue_item_id=QUEUE_ID, selected_slice=SLICE,
    )

    if case == "clock-exception":
        signed.assert_not_called()
        generation.assert_not_called()
        clock.assert_called_once()
        assert result.rejection_reasons == ("canonical_trusted_clock_invalid",)
        assert not result.signed_authority_reverified and result.authoritative_use_lease is None
        _assert_readiness_retains_generation_gates(repo, runtime, (signed, clock, generation))
        assert {path.name: path.read_bytes() for path in runtime.glob("*.json")} == before_bytes
        return
    signed.assert_called_once()
    assert signed.call_args.kwargs["verification_phase"] is (
        use_time_module.WorkAuthorityVerificationPhase.PREFLIGHT_NON_CONSUMING
    )
    assert clock.call_count == (1 if case == "signed-work-rejected" else 2)
    generation_calls = 0 if case in ("signed-work-rejected", "clock-exception") else 1
    assert generation.call_count == generation_calls
    if generation_calls:
        recorded = store.load()["stage_results"]["authority_runtime"]["authority_result"]
        generation.assert_called_once_with(repo_root=repo, runtime_root=runtime, now_epoch=NOW_EPOCH,
            principal_identity=recorded["identity"], principal_work_authority=recorded["work_authority"],
            model_work_order=work_order, trusted_now_epoch=generation.call_args.kwargs["trusted_now_epoch"],
            retained_proposal_inputs=None, revoked_key_epochs=frozenset())
        assert callable(generation.call_args.kwargs["trusted_now_epoch"])
    all_anchors = set(use_time_module.INCOMPLETE_TRUST_ANCHOR_REASONS)
    expected_anchors = set(all_anchors)
    if case == "typed-accepted":
        expected_anchors.difference_update(use_time_module.CURRENT_GENERATION_TRUST_ANCHOR_REASONS)
    assert len(expected_anchors) == (7 if case == "typed-accepted" else 10)
    assert all_anchors.intersection(result.rejection_reasons) == expected_anchors
    expected_reasons = set(expected_anchors)
    if case == "signed-work-rejected":
        expected_reasons.add("canonical_use_time_authority:synthetic_rejection")
    assert set(result.rejection_reasons) == expected_reasons
    assert result.signed_authority_reverified is (case != "signed-work-rejected")
    assert "canonical_signer_client_peer_handshake_verifier_missing" in result.rejection_reasons
    assert result.authoritative_use_lease is None
    expected_receipt = "sha256:" + "a" * 64 if case == "typed-accepted" else None
    assert result.signer_generation_binding_receipt_id == expected_receipt
    _assert_readiness_retains_generation_gates(repo, runtime, (signed, clock, generation))
    assert {path.name: path.read_bytes() for path in runtime.glob("*.json")} == before_bytes


@pytest.mark.parametrize("case, diagnostic", [
    ("chain", "canonical_chain_results_revision_invalid"),
    ("work", "canonical_signed_work_order_binding_mismatch:work_order_digest"),
    ("slice", "canonical_queue_authority_binding_mismatch:selected_slice"),
    ("incomplete", "canonical_signed_expected_binding_mismatch:principal_id"),
], ids=["chain", "work", "slice", "incomplete"])
def test_rejected_bindings_do_not_acquire_generation(tmp_path, monkeypatch, case, diagnostic):
    from unittest.mock import Mock

    repo, runtime, resolver, store, work, signed, clock, generation = (
        _generation_projection_case(tmp_path, monkeypatch, "typed-accepted",
                                    consistent=case != "incomplete")
    )
    state = store.load()
    if case == "chain":
        state["revision"] = "invalid"
    if case == "work":
        work["task_summary"] = "changed after synthetic signing"
    consume = Mock(side_effect=AssertionError("must not consume an authoritative nonce"))
    monkeypatch.setattr(GovernedValveUseTimeAuthorityResolver, "_consume_authoritative_nonce", consume)
    before_bytes = {path.name: path.read_bytes() for path in runtime.glob("*.json")}
    result = resolver.resolve(chain_state=state, work_order=work,
                              queue_item_id=QUEUE_ID,
                              selected_slice="wrong-slice" if case == "slice" else SLICE)
    assert result.signed_authority_reverified is True
    assert diagnostic in result.rejection_reasons
    assert set(use_time_module.INCOMPLETE_TRUST_ANCHOR_REASONS) <= set(result.rejection_reasons)
    assert result.signer_generation_binding_receipt_id is None
    assert result.authoritative_use_lease is None
    signed.assert_called_once()
    assert signed.call_args.kwargs["verification_phase"] is use_time_module.WorkAuthorityVerificationPhase.PREFLIGHT_NON_CONSUMING
    clock.assert_called_once()  # Current authority verification samples time before generation lookup.
    generation.assert_not_called()
    consume.assert_not_called()
    assert {path.name: path.read_bytes() for path in runtime.glob("*.json")} == before_bytes


@pytest.mark.parametrize("binding", ["current", "other-work", "serialized", "missing"])
def test_resident_principal_evidence_preserves_six_other_gates(tmp_path, monkeypatch, binding):
    from dataclasses import replace
    from modules.communication.moltbot_bridge.src.reddog_signer_current_generation_runtime_binding import _digest
    repo, runtime, resolver, store, work, signed, clock, generation = (
        _generation_projection_case(tmp_path, monkeypatch, "typed-accepted", consistent=True))
    def verify(**kwargs):
        identity, authority = kwargs["principal_identity"], dict(kwargs["principal_work_authority"])
        if binding == "other-work":
            authority["work_order_id"] = "other-work"
        digest = _digest({"identity": identity, "work_authority": authority})
        proof = SignerCurrentGenerationRuntimeBinding(True, (), receipt_id="sha256:" + "a" * 64,
            principal_binding_digest=None if binding == "missing" else digest)
        return proof.to_dict() if binding == "serialized" else proof
    generation.side_effect = verify
    result = resolver.resolve(chain_state=store.load(), work_order=work,
                              queue_item_id=QUEUE_ID, selected_slice=SLICE)
    missing = "canonical_principal_subject_key_attestation_missing"
    assert (missing not in result.rejection_reasons) is (binding == "current")
    other = set(use_time_module.INCOMPLETE_TRUST_ANCHOR_REASONS).difference(
        use_time_module.CURRENT_GENERATION_TRUST_ANCHOR_REASONS, {missing})
    assert len(other) == 6 and other.issubset(result.rejection_reasons)
    assert result.authoritative_use_lease is None
    signed.assert_called_once()
    generation.assert_called_once()


@pytest.mark.parametrize("case", [
    "current", "rotated", "expired", "clock-reversed", "clock-bool", "no-grant",
    "bad-grant", "peer-rejected", "serialized", "wrong-requester", "wrong-profile",
    "wrong-key", "wrong-epoch", "wrong-session", "wrong-socket", "wrong-manifest",
    "wrong-generation", "wrong-config", "wrong-packet", "no-os-peer", "no-handshake",
    "peer-exception", "identity-mutated",
    "model-current", "model-expired", "model-swapped", "model-missing-after",
])
def test_resident_peer_connection_requires_fresh_bound_evidence(tmp_path, monkeypatch, case):
    from dataclasses import replace
    from unittest.mock import Mock
    from modules.communication.moltbot_bridge.src import reddog_signer_socket_service_healthcheck as health
    from modules.communication.moltbot_bridge.src.reddog_signer_current_generation_runtime_binding import _digest

    repo, runtime, resolver, store, work, signed, clock, generation = (
        _generation_projection_case(tmp_path, monkeypatch, "typed-accepted", consistent=True))
    calls = []
    digest = "sha256:" + "b" * 64
    def verify(**kwargs):
        calls.append(kwargs)
        proof = SignerCurrentGenerationRuntimeBinding(True, (), receipt_id=digest,
            manifest_id=digest, artifact_generation_digest=digest, generation=1,
            generation_revision="rev-1", owner_config_id=digest, config_digest=digest,
            config_raw_digest=digest, run_packet_id="packet-1", run_packet_digest=digest,
            session_id="session-1", socket_path_digest=digest, signer_profile_id="reddog-work-authority",
            manifest_expires_at=NOW_EPOCH+120,
            signer_public_key="fixture-public-key", key_epoch="epoch-1", selection_expires_at=NOW_EPOCH+60,
            principal_binding_digest=_digest({"identity": kwargs["principal_identity"],
                "work_authority": kwargs["principal_work_authority"]}), signer_uid=1234, signer_gid=1235)
        if case.startswith("model-"):
            proof = replace(proof, model_work_order_digest=canonical_full_work_order_digest(work),
                model_artifact_pair_digest=digest, model_valid_until=NOW_EPOCH+10)
            if len(calls)>1 and case == "model-swapped":
                proof = replace(proof, model_artifact_pair_digest="sha256:"+"c"*64)
            if len(calls)>1 and case == "model-missing-after":
                proof = replace(proof, model_work_order_digest=None, model_artifact_pair_digest=None, model_valid_until=None)
        return replace(proof, generation_revision="rev-2") if case == "rotated" and len(calls)>1 else proof
    generation.side_effect = verify
    seen = []
    def handshake(**kwargs):
        seen.append(kwargs)
        if case == "peer-exception": raise RuntimeError("fixture failure")
        result = health.SignerServiceHealthcheckResult(True, health.SIGNER_SERVICE_HEALTHCHECK_READY,
            str(runtime/"signer_service_run_packet.json"), "packet-1", "fixture-config", digest,
            "fixture-socket", "reddog-work-authority", "fixture-public-key", kwargs["requester_principal_id"],
            digest, digest, (), manifest_id=digest, artifact_generation_digest=digest,
            peer_handshake_verified=True, peer_handshake_expires_at=NOW_EPOCH+30,
            session_id="session-1", socket_path_digest=digest, key_epoch="epoch-1", server_identity_verified=True)
        fields = {"wrong-requester":"requester_principal_id", "wrong-profile":"signer_profile_id",
            "wrong-key":"signer_public_key", "wrong-epoch":"key_epoch", "wrong-session":"session_id",
            "wrong-socket":"socket_path_digest", "wrong-manifest":"manifest_id",
            "wrong-generation":"artifact_generation_digest", "wrong-config":"config_digest", "wrong-packet":"run_packet_id"}
        if case in fields: result=replace(result, **{fields[case]:"substituted"})
        if case == "expired": clock.return_value=NOW_EPOCH+31
        if case == "model-expired": clock.return_value=NOW_EPOCH+11
        if case == "clock-reversed": clock.return_value=NOW_EPOCH-1
        if case == "clock-bool": clock.return_value=True
        if case == "peer-rejected": result=replace(result,accepted=False)
        if case == "no-os-peer": result=replace(result,server_identity_verified=False)
        if case == "no-handshake": result=replace(result,peer_handshake_verified=False)
        if case == "identity-mutated": calls[0]["principal_identity"]["principal_id"]="substituted"
        return result.to_dict() if case == "serialized" else result
    probe=Mock(side_effect=handshake)
    monkeypatch.setattr(gate_module, "run_reddog_signer_socket_service_healthcheck", probe, raising=False)
    supplier = None if case == "no-grant" else ({} if case == "bad-grant" else lambda request: {})
    resolver = replace(resolver, signer_peer_secret_access_grant_supplier=supplier)
    result = resolver.resolve(chain_state=store.load(), work_order=work, queue_item_id=QUEUE_ID, selected_slice=SLICE)
    reason="canonical_signer_client_peer_handshake_verifier_missing"
    assert (reason not in result.rejection_reasons) is (case in {"current", "model-current"})
    assert (result.signer_peer_binding_receipt_id is not None) is (case in {"current", "model-current"})
    other=set(use_time_module.INCOMPLETE_TRUST_ANCHOR_REASONS).difference(
        use_time_module.CURRENT_GENERATION_TRUST_ANCHOR_REASONS,
        {reason,"canonical_principal_subject_key_attestation_missing"})
    model_reasons={"canonical_model_signed_evidence_trust_anchor_incomplete", "canonical_model_selection_signed_evidence_verifier_missing"}
    if case == "model-current":
        other -= model_reasons
        assert model_reasons.isdisjoint(result.rejection_reasons)
    assert other.issubset(result.rejection_reasons)
    assert (result.signer_model_binding_receipt_id is not None) is (case == "model-current")
    assert result.authoritative_use_lease is None
    if case in ("no-grant", "bad-grant"): probe.assert_not_called()
    if case == "current":
        assert len(calls)==2 and all(c["include_process_identity"] is True for c in calls)
        assert seen[0]["expected_server_uid"]==1234 and seen[0]["expected_server_gid"]==1235
        assert seen[0]["trusted_socket_root"]==runtime
        assert seen[0]["secret_access_grant_supplier"] is supplier


def test_valve_routes_retained_memex_and_revocations_without_effect_authority(tmp_path, monkeypatch):
    """Routing seam only; real artifact/crypto coverage lives in producer tests."""
    from dataclasses import replace
    from modules.communication.moltbot_bridge.src.reddog_signer_current_generation_runtime_binding import _digest
    repo, runtime, resolver, store, work, signed, clock, generation = (
        _generation_projection_case(tmp_path, monkeypatch, "typed-accepted", consistent=True))
    bundle = {"routing_fixture": "retained-evidence"}
    original = use_time_module._read_runtime_artifacts
    def artifacts(owner):
        values, reasons = original(owner)
        values["authority_profile"] = dict(values["authority_profile"], proposal_verification_inputs=bundle)
        return values, reasons
    monkeypatch.setattr(use_time_module, "_read_runtime_artifacts", artifacts)
    def proof(**kwargs):
        digest = "sha256:" + "b"*64
        return SignerCurrentGenerationRuntimeBinding(True, (), receipt_id=digest,
            selection_expires_at=NOW_EPOCH+60, manifest_expires_at=NOW_EPOCH+60,
            principal_binding_digest=_digest({"identity": kwargs["principal_identity"],
                "work_authority": kwargs["principal_work_authority"]}),
            memex_work_order_digest=canonical_full_work_order_digest(work),
            memex_evidence_digest=_digest(bundle), memex_valid_until=NOW_EPOCH+30)
    generation.side_effect = proof
    resolver = replace(resolver, revoked_key_epochs=("retired-epoch",))
    result = resolver.resolve(chain_state=store.load(), work_order=work, queue_item_id=QUEUE_ID, selected_slice=SLICE)
    assert generation.call_count == 1
    assert generation.call_args.kwargs["retained_proposal_inputs"] is bundle
    assert generation.call_args.kwargs["revoked_key_epochs"] == frozenset({"retired-epoch"})
    cleared = set(use_time_module.CURRENT_GENERATION_TRUST_ANCHOR_REASONS) | {
        "canonical_principal_subject_key_attestation_missing", "canonical_memex_supply_signed_evidence_verifier_missing"}
    assert cleared.isdisjoint(result.rejection_reasons)
    assert set(use_time_module.INCOMPLETE_TRUST_ANCHOR_REASONS).difference(cleared).issubset(result.rejection_reasons)
    assert result.authoritative_use_lease is None
