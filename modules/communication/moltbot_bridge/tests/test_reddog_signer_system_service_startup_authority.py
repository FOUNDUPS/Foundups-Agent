"""Current startup authority binding, rejection, and public v7 composition tests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.tests.model_runtime_binding_receipt_test_helpers import (
    _real_model_evidence_signatures, _corrupt_model_evidence_signature,
)

from modules.communication.moltbot_bridge.tests.test_reddog_signer_system_service_entrypoint import (
    CapturingBoundedService,
    CapturingResolverFactory,
    FailClosedPrincipalKeyResolver,
    FakeResolver,
    NOW,
    PeerCredentialPolicy,
    SYSTEM_SERVICE_ENTRYPOINT_ACCEPT,
    SYSTEM_SERVICE_ENTRYPOINT_REJECT,
    _accepted_isolation,
    _audit_secret,
    _isolation_receipt,
    _prepare_real_cli_owner,
    _private_key_secret,
    _public_startup_artifacts,
    _public_startup_finalize,
    _public_startup_owner,
    _public_startup_root_transport,
    _resolver_for,
    _run_entrypoint_args,
    _trusted_clock,
    _upgrade_prepared_owner_to_v2,
    digest,
    loader_module,
)


def _model_input_owner_case(tmp_path, monkeypatch):
    import time
    from modules.communication.moltbot_bridge.tests.model_runtime_binding_receipt_test_helpers import (
        model_selection_and_runtime_binding_receipts, model_runtime_binding_test_verifier,
    )
    monkeypatch.setattr(time, "time", lambda: NOW)
    values, owner, selected = _public_startup_artifacts(tmp_path)
    _public_startup_owner(values, owner, selected, tmp_path, monkeypatch)
    monkeypatch.setattr(loader_module, "_read_root_owned_bytes", lambda path, _root: path.read_bytes())
    selection, binding = model_selection_and_runtime_binding_receipts(runtime_surface="reddog_artifact_generation")
    verifier = model_runtime_binding_test_verifier(binding)
    payloads = dict(catalog=verifier.catalog_snapshot,
        benchmarks={"benchmark_evidence_receipts": verifier.benchmark_evidence_receipts},
        promotions={"promotion_evidence_receipts": verifier.promotion_evidence_receipts},
        evidence=verifier.verified_evidence_bundle, policy=verifier.runtime_policy,
        trusted_keys=verifier.trusted_keys_payload)
    inputs = {}
    for name, payload in payloads.items():
        path = Path(owner["runtime_root"]) / ("model-" + name + ".json")
        raw = json.dumps(payload, sort_keys=True).encode("utf-8")
        path.write_bytes(raw)
        inputs[name] = {"path": str(path), "raw_digest": loader_module.raw_digest(raw)}
    owner.update(schema_version="reddog_signer_system_service_owner_config.v8",
                 model_verifier_authority=dict(issued_at=NOW - 1, expires_at=NOW + 30, inputs=inputs))
    owner["config_id"] = digest({k: v for k, v in owner.items() if k != "config_id"})
    values["owner_config_path"].write_text(json.dumps(owner), encoding="ascii")
    values.update(model_selection=selection, model_binding=binding)
    return values, owner, payloads


@pytest.mark.parametrize("case", ["valid", "owner_id", "payload_changed", "missing", "extra", "relative", "duplicate_path", "expiry", "boolean_time"])
def test_model_verifier_owner_inputs_are_exact_and_current(tmp_path, monkeypatch, case):
    values, owner, payloads = _model_input_owner_case(tmp_path, monkeypatch)
    authority = owner["model_verifier_authority"]
    expected = owner["config_id"]
    if case == "owner_id":
        expected = "sha256:" + "0" * 64
    elif case == "payload_changed":
        Path(authority["inputs"]["policy"]["path"]).write_text("{}", encoding="ascii")
    elif case == "missing":
        authority["inputs"].pop("trusted_keys")
    elif case == "extra":
        authority["signature_verifier"] = "injected"
    elif case == "relative":
        authority["inputs"]["policy"]["path"] = "model-policy.json"
    elif case == "duplicate_path":
        authority["inputs"]["policy"] = authority["inputs"]["trusted_keys"]
    elif case == "expiry":
        authority["expires_at"] = NOW
    elif case == "boolean_time":
        authority["issued_at"] = True
    if case not in {"valid", "owner_id", "payload_changed"}:
        owner["config_id"] = digest({k: v for k, v in owner.items() if k != "config_id"})
        expected = owner["config_id"]
        values["owner_config_path"].write_text(json.dumps(owner), encoding="ascii")
    def load():
        return loader_module.load_system_service_model_runtime_verifier(
            owner_config_path=values["owner_config_path"], repo_root=values["repo"],
            expected_owner_config_id=expected, trusted_now_epoch=lambda: NOW)
    if case != "valid":
        with pytest.raises(ValueError):
            load()
        return
    actual = load()
    assert actual.catalog_snapshot == payloads["catalog"]
    assert actual.runtime_policy == payloads["policy"]
    assert type(actual.signature_verifier).__name__ == "Ed25519SignatureVerifier"
    Path(authority["inputs"]["policy"]["path"]).write_text("{}", encoding="ascii")
    assert actual.runtime_policy == payloads["policy"]  # Exact checked snapshot, no reread.


@pytest.mark.parametrize("case", ["rotate_during_read", "expire_during_read", "rotate_after_load", "expire_after_load", "duplicate_json"])
def test_model_verifier_owner_lifetime_and_exact_snapshot(tmp_path, monkeypatch, case):
    values, owner, payloads = _model_input_owner_case(tmp_path, monkeypatch)
    authority = owner["model_verifier_authority"]
    now, reads = [NOW], []
    def rotate():
        owner["model_verifier_authority"]["expires_at"] -= 1
        owner["config_id"] = digest({k: v for k, v in owner.items() if k != "config_id"})
        values["owner_config_path"].write_text(json.dumps(owner), encoding="ascii")
    if case == "duplicate_json":
        item = authority["inputs"]["policy"]
        raw = b'{"x":1,"x":2}'
        Path(item["path"]).write_bytes(raw)
        item["raw_digest"] = loader_module.raw_digest(raw)
        owner["config_id"] = digest({k: v for k, v in owner.items() if k != "config_id"})
        values["owner_config_path"].write_text(json.dumps(owner), encoding="ascii")
    from modules.communication.moltbot_bridge.src import reddog_signer_system_service_owner_inputs as owner_inputs
    checked_read = owner_inputs.secure_read_confined_bytes
    def read(path, **kwargs):
        result = checked_read(path, **kwargs)
        reads.append(str(path))
        if len(reads) == 6:
            if case == "rotate_during_read":
                rotate()
            elif case == "expire_during_read":
                now[0] = authority["expires_at"]
        return result
    monkeypatch.setattr(owner_inputs, "secure_read_confined_bytes", read)
    def load():
        return loader_module.load_system_service_model_runtime_verifier(
            owner_config_path=values["owner_config_path"], repo_root=values["repo"],
            expected_owner_config_id=owner["config_id"], trusted_now_epoch=lambda: now[0])
    if case in {"rotate_during_read", "expire_during_read", "duplicate_json"}:
        with pytest.raises(ValueError):
            load()
        return
    actual = load()
    assert len(reads) == len(set(reads)) == 6
    assert actual.trusted_now_epoch() == NOW
    if case == "rotate_after_load":
        rotate()
    else:
        now[0] = authority["expires_at"]
    with pytest.raises(ValueError):
        actual.trusted_now_epoch()


@pytest.mark.parametrize("case", ["catalog", "benchmarks", "promotions", "evidence", "policy", "trusted_keys", "expiry_in_owner_read", "backwards_in_owner_read"])
def test_model_verifier_rechecks_memory_and_owner_read_time(tmp_path, monkeypatch, case):
    values, owner, _ = _model_input_owner_case(tmp_path, monkeypatch)
    now = [NOW]
    actual = loader_module.load_system_service_model_runtime_verifier(
        owner_config_path=values["owner_config_path"], repo_root=values["repo"],
        expected_owner_config_id=owner["config_id"], trusted_now_epoch=lambda: now[0])
    mappings = dict(catalog=actual.catalog_snapshot,
        benchmarks=actual.benchmark_evidence_receipts[0], promotions=actual.promotion_evidence_receipts[0],
        evidence=actual.verified_evidence_bundle, policy=actual.runtime_policy, trusted_keys=actual.trusted_keys_payload)
    if case in mappings:
        mappings[case]["changed_after_authenticated_read"] = True
    else:
        read_owner = loader_module._load_owner_config
        def delayed(*args, **kwargs):
            checked = read_owner(*args, **kwargs)
            now[0] = owner["model_verifier_authority"]["expires_at"] if case == "expiry_in_owner_read" else NOW - 1
            return checked
        monkeypatch.setattr(loader_module, "_load_owner_config", delayed)
    with pytest.raises(ValueError):
        actual.trusted_now_epoch()


@pytest.mark.parametrize("case", ["valid", "bad_signature", "wrong_trust_key"])
def test_protected_model_inputs_execute_real_signature_verification(tmp_path, monkeypatch, case):
    from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_verified_admission import (
        verified_runtime_binding_receipt, consume_verified_runtime_binding_capability,
        discard_verified_runtime_binding_capability,
    )
    _real_model_evidence_signatures(monkeypatch)
    values, owner, payloads = _model_input_owner_case(tmp_path, monkeypatch)
    if case != "valid":
        name = "evidence" if case == "bad_signature" else "trusted_keys"
        if case == "bad_signature":
            _corrupt_model_evidence_signature(payloads[name])
        else:
            keys = payloads[name]["trusted_public_keys"]
            keys[0]["public_key"] = keys[1]["public_key"]
        raw = json.dumps(payloads[name], sort_keys=True).encode("utf-8")
        item = owner["model_verifier_authority"]["inputs"][name]
        Path(item["path"]).write_bytes(raw)
        item["raw_digest"] = loader_module.raw_digest(raw)
        owner["config_id"] = digest({k: v for k, v in owner.items() if k != "config_id"})
        values["owner_config_path"].write_text(json.dumps(owner), encoding="ascii")
    verifier = loader_module.load_system_service_model_runtime_verifier(
        owner_config_path=values["owner_config_path"], repo_root=values["repo"],
        expected_owner_config_id=owner["config_id"], trusted_now_epoch=lambda: NOW)
    args = dict(selection=values["model_selection"], binding=values["model_binding"])
    backend_type = type(verifier.signature_verifier)
    verify_signature, observed = backend_type.verify, []
    def recording_verify(self, *arguments):
        accepted = verify_signature(self, *arguments)
        observed.append(accepted)
        return accepted
    monkeypatch.setattr(backend_type, "verify", recording_verify)
    if case != "valid":
        with pytest.raises(ValueError):
            verifier.verify(**args)
        if case == "bad_signature":
            assert observed and False in observed
        return
    capability = verifier.verify(**args)
    assert observed and all(observed)
    try:
        receipt = verified_runtime_binding_receipt(args["binding"])
        assert consume_verified_runtime_binding_capability(capability, receipt=receipt, **args) == receipt
        assert consume_verified_runtime_binding_capability(capability, receipt=receipt, **args) is None
    finally:
        discard_verified_runtime_binding_capability(capability)


def test_legacy_e0_config_binding_retains_generation_alias_dependency(tmp_path):
    """Observe the legacy custody-assembly cycle; this is not public acceptance."""
    from modules.communication.moltbot_bridge.tests import test_reddog_signer_owner_controlled_e0_admission as e0
    from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_policy_contract import (
        signer_owner_e0_authority_binding_digest, POLICY_SCHEMA_V6,
    )
    from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import REQUIRED_RUNTIME_ARTIFACTS

    values = e0._fixture(tmp_path)
    policy = values["policy"]
    assert policy["schema_version"] == POLICY_SCHEMA_V6
    assert policy["target_signer_generation_id"] == policy["artifact_generation_digest"]
    original = signer_owner_e0_authority_binding_digest(policy)
    config = json.loads(values["config_path"].read_text(encoding="ascii"))
    assert config["owner_e0_authority_binding_digest"] == original
    assert "signer_service_config.json" in REQUIRED_RUNTIME_ARTIFACTS
    changed = dict(policy)
    changed["artifact_generation_digest"] = "sha256:" + "f" * 64
    assert changed["artifact_generation_digest"] != policy["artifact_generation_digest"]
    assert signer_owner_e0_authority_binding_digest(changed) == original
    changed["target_signer_generation_id"] = changed["artifact_generation_digest"]
    rebound = signer_owner_e0_authority_binding_digest(changed)
    assert rebound != original  # Legacy behavior must not silently change.
    rebound_config = {**config, "owner_e0_authority_binding_digest": rebound}
    assert digest(rebound_config) != digest(config)


def _v8_generation_binding_case(tmp_path):
    """Construct real config/artifact hashes; this does not publish a manifest."""
    from modules.communication.moltbot_bridge.tests import test_reddog_signer_owner_controlled_e0_admission as e0
    from modules.communication.moltbot_bridge.tests.reddog_grant_authority_service_policy_test_support import grant_service_git_provenance_policy_fields
    from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_policy_contract import POLICY_SCHEMA_V8
    from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import REQUIRED_RUNTIME_ARTIFACTS
    from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_io import _describe_runtime_artifacts_unlocked
    from modules.communication.moltbot_bridge.src.reddog_signer_current_generation_config_loader import load_current_generation_signer_config

    values = e0._fixture(tmp_path)
    policy, selection = values["policy"], values["selection"]
    policy.update(grant_service_git_provenance_policy_fields(
        repo_root_digest=e0.DIGEST_A, source_commit_sha="1" * 40,
        object_format="sha1", source_policy_digest=e0.DIGEST_D,
        source_descriptor_digest=e0.DIGEST_E,
    ))
    policy["schema_version"] = POLICY_SCHEMA_V8
    e0._rebind_config_and_sign(values, values["grant_private"])
    raw_config = values["config_path"].read_bytes()
    runtime = Path(selection["runtime_root"])
    for name in REQUIRED_RUNTIME_ARTIFACTS:
        path = runtime / name
        if name == "signer_service_config.json":
            path.write_bytes(raw_config)
        elif name == "authoritative_work_state.json":
            path.write_text(json.dumps({"revision": "binding-fixture", "wre_queue_items": [{"queue_item_id": "binding-fixture"}]}), encoding="ascii")
        elif not path.exists():
            path.write_bytes(b"{}")  # Inert artifacts, never admitted/published.
    descriptors = _describe_runtime_artifacts_unlocked({
        **selection, "authority_profile_digest": digest({}),
        "signer_service_config_digest": selection["config_digest"],
        "work_state_revision": "binding-fixture", "queue_item_id": "binding-fixture",
    })
    generation = digest(tuple(item.to_dict() for item in descriptors))
    policy["artifact_generation_digest"] = generation
    policy["target_signer_generation_id"] = generation
    selection["artifact_generation_digest"] = generation
    e0._resign(values)
    config = load_current_generation_signer_config(
        repo_root=Path(selection["repo_root"]), selection=selection,
    )
    return values, config, raw_config


def test_v8_e0_binding_constructs_generation_without_rewriting_config(tmp_path):
    from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_policy_contract import (
        canonical_signer_owner_e0_policy_input, signer_owner_e0_authority_binding_digest,
        validated_signer_owner_e0_policy, POLICY_PREFIX_V8,
    )
    from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_admission_validation import require_policy_config_binding
    from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import Ed25519SignatureVerifier

    values, config, raw_config = _v8_generation_binding_case(tmp_path)
    policy = values["policy"]
    validated_signer_owner_e0_policy(policy, now_epoch=policy["issued_at"] + 1)
    assert signer_owner_e0_authority_binding_digest(policy) == values["config"]["owner_e0_authority_binding_digest"]
    assert values["config_path"].read_bytes() == raw_config
    assert require_policy_config_binding(policy, config).signer_agent_id == policy["target_signer_agent_id"]
    canonical = canonical_signer_owner_e0_policy_input(policy)
    assert canonical.startswith(POLICY_PREFIX_V8)
    assert Ed25519SignatureVerifier().verify(values["grant_public"], canonical, policy["signature"]) is True
    tampered = {**policy, "target_signer_generation_id": "sha256:" + "f" * 64}
    assert Ed25519SignatureVerifier().verify(values["grant_public"], canonical_signer_owner_e0_policy_input(tampered), policy["signature"]) is False


def test_v8_e0_config_validator_rejects_tampered_generation_alias(tmp_path):
    from modules.communication.moltbot_bridge.tests import test_reddog_signer_owner_controlled_e0_admission as e0
    from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_admission_validation import require_policy_config_binding
    from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_policy_contract import signer_owner_e0_authority_binding_digest

    values, config, _raw_config = _v8_generation_binding_case(tmp_path)
    policy = values["policy"]
    original = signer_owner_e0_authority_binding_digest(policy)
    require_policy_config_binding(policy, config)  # Discriminatory valid control.
    policy["target_signer_generation_id"] = "sha256:" + "f" * 64
    assert policy["target_signer_generation_id"] != policy["artifact_generation_digest"]
    e0._resign(values)  # Even a re-signed inconsistent alias must fail binding.
    assert signer_owner_e0_authority_binding_digest(policy) == original
    with pytest.raises(ValueError, match="^e0_target_profile_binding_mismatch$"):
        require_policy_config_binding(policy, config)


@pytest.mark.parametrize("supplier_failure", ("missing", "raised", "invalid"))
def test_configured_outcome_policy_rejects_unusable_supplier(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    supplier_failure: str,
) -> None:
    prepared = _prepare_real_cli_owner(
        tmp_path, monkeypatch, include_outcome_policy=True
    )
    _upgrade_prepared_owner_to_v2(prepared, tmp_path, bind_runtime=True)
    startup = loader_module.load_system_service_startup_selection(
        owner_config_path=prepared["owner_path"],
        repo_root=prepared["harness"].repo_root,
    )
    if supplier_failure == "missing":
        supplier = None
    elif supplier_failure == "raised":
        def supplier():
            raise RuntimeError("unavailable")
    else:
        def supplier():
            return object()

    def startup_loader(**_kwargs):
        return loader_module.SystemServiceStartupSelection(
            startup.owner_config_id,
            startup.manifest_selection,
            startup.manifest_selection_boundary,
            supplier,
            startup.signer_uid,
            startup.signer_gid,
        )

    resolver = _resolver_for(prepared)
    factory = CapturingResolverFactory(resolver)
    service = CapturingBoundedService()
    emitted: list[str] = []
    code = _run_entrypoint_args(
        argparse.Namespace(
            repo_root=str(prepared["harness"].repo_root),
            owner_authority_config=str(prepared["owner_path"]),
        ),
        resolver_factory=factory,
        serve_bounded=service,
        emit=emitted.append,
        principal_key_resolver=FailClosedPrincipalKeyResolver(),
        proposal_replay_high_water_store=None,
        startup_selection_loader=startup_loader,
        process_isolation_gate=_accepted_isolation,
    )

    assert code == 2
    assert json.loads(emitted[0])["status"] == SYSTEM_SERVICE_ENTRYPOINT_REJECT
    assert len(factory.calls) == 1
    assert resolver.calls == []
    assert service.calls == []


def test_system_service_isolation_rejects_before_resolver_or_socket(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepared = _prepare_real_cli_owner(tmp_path, monkeypatch)
    _upgrade_prepared_owner_to_v2(prepared, tmp_path)
    factory = CapturingResolverFactory(FakeResolver({}))
    service = CapturingBoundedService()
    emitted: list[str] = []

    code = _run_entrypoint_args(
        argparse.Namespace(
            repo_root=str(prepared["harness"].repo_root),
            owner_authority_config=str(prepared["owner_path"]),
        ),
        resolver_factory=factory,
        serve_bounded=service,
        emit=emitted.append,
        principal_key_resolver=FailClosedPrincipalKeyResolver(),
        proposal_replay_high_water_store=None,
        process_isolation_gate=lambda _policy, **_expected: _isolation_receipt(False),
    )

    assert code == 2
    assert json.loads(emitted[0])["status"] == SYSTEM_SERVICE_ENTRYPOINT_REJECT
    assert factory.calls == []
    assert service.calls == []


def test_production_entrypoint_rejects_legacy_v1_before_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepared = _prepare_real_cli_owner(tmp_path, monkeypatch)
    factory = CapturingResolverFactory(FakeResolver({}))
    service = CapturingBoundedService()
    emitted: list[str] = []

    code = _run_entrypoint_args(
        argparse.Namespace(
            repo_root=str(prepared["harness"].repo_root),
            owner_authority_config=str(prepared["owner_path"]),
        ),
        resolver_factory=factory,
        serve_bounded=service,
        emit=emitted.append,
        principal_key_resolver=FailClosedPrincipalKeyResolver(),
        proposal_replay_high_water_store=None,
    )

    assert code == 2
    assert json.loads(emitted[0])["status"] == SYSTEM_SERVICE_ENTRYPOINT_REJECT
    assert factory.calls == []
    assert service.calls == []


def test_owner_rotation_during_read_cannot_mix_startup_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepared = _prepare_real_cli_owner(tmp_path, monkeypatch)
    owner = _upgrade_prepared_owner_to_v2(prepared, tmp_path)
    original = Path(prepared["owner_path"]).read_bytes()
    owner["verified_outcome_authority"]["signer_uid"] = 1301
    owner["verified_outcome_authority"]["signer_gid"] = 1301
    owner["config_id"] = digest(
        {key: value for key, value in owner.items() if key != "config_id"}
    )
    rotated = json.dumps(owner, sort_keys=True, separators=(",", ":")).encode("ascii")
    reads: list[bytes] = []

    def rotate_after_read(target: Path, _root: Path) -> bytes:
        raw = target.read_bytes()
        reads.append(raw)
        target.write_bytes(rotated)
        return raw

    monkeypatch.setattr(loader_module, "_read_root_owned_bytes", rotate_after_read)
    isolation_calls: list[tuple[int, int]] = []
    factory = CapturingResolverFactory(FakeResolver({}))
    service = CapturingBoundedService()

    def reject_isolation(_policy: PeerCredentialPolicy, **expected: int):
        isolation_calls.append(
            (expected["expected_signer_uid"], expected["expected_signer_gid"])
        )
        return _isolation_receipt(False)

    code = _run_entrypoint_args(
        argparse.Namespace(
            repo_root=str(prepared["harness"].repo_root),
            owner_authority_config=str(prepared["owner_path"]),
        ),
        resolver_factory=factory,
        serve_bounded=service,
        emit=lambda _line: None,
        principal_key_resolver=FailClosedPrincipalKeyResolver(),
        proposal_replay_high_water_store=None,
        process_isolation_gate=reject_isolation,
    )

    assert code == 2
    assert reads == [original]
    assert isolation_calls == [(1201, 1201)]
    assert factory.calls == []
    assert service.calls == []


def test_alternate_owner_path_rejects_before_resolver_or_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare_real_cli_owner(tmp_path, monkeypatch)
    _upgrade_prepared_owner_to_v2(prepared, tmp_path)
    alternate_root = tmp_path / "alternate-owner"
    alternate_root.mkdir()
    alternate = alternate_root / "owner.json"
    alternate.write_bytes(Path(prepared["owner_path"]).read_bytes())
    factory = CapturingResolverFactory(FakeResolver({}))
    service = CapturingBoundedService()
    emitted: list[str] = []

    code = _run_entrypoint_args(
        argparse.Namespace(
            repo_root=str(prepared["harness"].repo_root),
            owner_authority_config=str(alternate),
        ),
        resolver_factory=factory,
        serve_bounded=service,
        emit=emitted.append,
        principal_key_resolver=FailClosedPrincipalKeyResolver(),
        proposal_replay_high_water_store=None,
    )

    assert code == 2
    assert json.loads(emitted[0])["status"] == (SYSTEM_SERVICE_ENTRYPOINT_REJECT)
    assert factory.calls == []
    assert service.calls == []


def test_generation_capability_failure_rejects_before_resolver_or_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare_real_cli_owner(tmp_path, monkeypatch)
    _upgrade_prepared_owner_to_v2(prepared, tmp_path)

    class RejectedGenerationBoundary:
        @staticmethod
        def consume(_capability: object) -> object:
            raise RuntimeError("generation changed")

    startup = loader_module.load_system_service_startup_selection(
        owner_config_path=prepared["owner_path"],
        repo_root=prepared["harness"].repo_root,
    )

    def startup_loader(**_kwargs):
        return loader_module.SystemServiceStartupSelection(
            owner_config_id=startup.owner_config_id,
            manifest_selection=object(),
            manifest_selection_boundary=RejectedGenerationBoundary(),
            verified_outcome_authority_supplier=(
                startup.verified_outcome_authority_supplier
            ),
            signer_uid=startup.signer_uid,
            signer_gid=startup.signer_gid,
        )

    factory = CapturingResolverFactory(FakeResolver({}))
    service = CapturingBoundedService()
    emitted: list[str] = []

    code = _run_entrypoint_args(
        argparse.Namespace(
            repo_root=str(prepared["harness"].repo_root),
            owner_authority_config=str(prepared["owner_path"]),
        ),
        resolver_factory=factory,
        serve_bounded=service,
        emit=emitted.append,
        principal_key_resolver=FailClosedPrincipalKeyResolver(),
        proposal_replay_high_water_store=None,
        startup_selection_loader=startup_loader,
    )

    assert code == 2
    payload = json.loads(emitted[0])
    assert payload["status"] == SYSTEM_SERVICE_ENTRYPOINT_REJECT
    assert factory.calls == []
    assert service.calls == []


@pytest.mark.parametrize("owner_version", [7, 8])
def test_public_v7_startup_real_generation_grant_signature_and_replay(tmp_path, monkeypatch, owner_version):
    """Synthetic enrollment; only OS custody/isolation and transports substituted."""
    import time
    from types import SimpleNamespace
    from modules.communication.moltbot_bridge.src import reddog_signer_system_service_entrypoint as entry
    from modules.communication.moltbot_bridge.src import reddog_signer_process_isolation_gate as isolation
    from modules.communication.moltbot_bridge.tests.test_reddog_signer_process_isolation_gate import FakeIsolationBackend
    from modules.communication.moltbot_bridge.tests import test_reddog_signer_socket_service_runtime_wiring as wf
    from modules.infrastructure.secrets_mcp.src import systemd_credential_secret_resolver as credentials
    monkeypatch.setattr(time, "time", lambda: NOW)
    # The resolver intentionally captures its clock default at import time.
    # Freeze that clock too; retain the real constructor/type and lifetime checks.
    constructor = credentials.SystemdCredentialSecretResolver.__init__
    monkeypatch.setattr(constructor, "__kwdefaults__", {**constructor.__kwdefaults__, "clock": lambda: NOW})
    if owner_version == 8:
        values, owner, _ = _model_input_owner_case(tmp_path, monkeypatch)
    else:
        values, owner, selected = _public_startup_artifacts(tmp_path)
        _public_startup_owner(values, owner, selected, tmp_path, monkeypatch)
    _public_startup_finalize(values, monkeypatch)
    operations = _public_startup_root_transport(values, monkeypatch)
    fixture = wf.factory_fixture.grant_fixture
    monkeypatch.setattr(fixture, "NOW", NOW)
    store = fixture.DurableSignerSecretGrantNonceStore(values["replay_config"], integrity_key=fixture.INTEGRITY_KEY, clock=lambda: NOW)
    request, grant, peer = wf._admission_request(values, values["admitted"], store)
    case = SimpleNamespace(request=request, grant=grant, peer=peer)
    reads, responses = [], []
    secrets = {"work": _private_key_secret(values["target_private"]), "control": _private_key_secret(values["control_private"]),
               "audit": _audit_secret(), "integrity": fixture.INTEGRITY_KEY.decode("utf-8")}
    def read_credential(binding, identifier):
        assert binding.expected_requester == "signer:reddog"
        reads.append(identifier)
        return secrets[identifier]
    monkeypatch.setattr(credentials, "_identity_matches", lambda binding: binding.expected_uid == binding.expected_gid == 1201)
    monkeypatch.setattr(credentials, "_read_credential", read_credential)
    monkeypatch.setattr(isolation, "LinuxSignerProcessIsolationBackend", FakeIsolationBackend)
    def serve(**kwargs):
        assert reads == ["integrity"]
        backend = kwargs["backend"]
        before = list(reads)
        assert wf._admission_wire(case, backend, None)["accepted"] is False
        assert reads == before
        response = wf._admission_wire(case, backend, grant)
        assert response["accepted"] is True, response.get("rejection_code")
        assert wf.protected_fixture.Ed25519SignatureVerifier().verify(request.signer_public_key, request.signing_input, response["signature"]) is True
        after = list(reads)
        operation_count = len(operations)
        assert wf._admission_wire(case, backend, grant)["accepted"] is False
        # Both verify and consume authenticate revocation LOAD before checking
        # nonce replay. Those proof reads must not become another protected sign.
        assert reads == after + ["work", "work"]
        assert operations[operation_count:] == ["REVOCATION_ANCHOR_LOAD"] * 2
        responses.append(True)
        return CapturingBoundedService()(**kwargs)
    monkeypatch.setattr(entry, "serve_reddog_isolated_signer_socket_bounded", serve)
    emitted = []
    code = entry.run_reddog_signer_system_service_entrypoint(
        ["--repo-root", str(values["repo"]), "--owner-authority-config", str(values["owner_config_path"])], emit=emitted.append)
    assert code == 0, json.loads(emitted[0])["rejection_reasons"]
    assert json.loads(emitted[0])["status"] == SYSTEM_SERVICE_ENTRYPOINT_ACCEPT
    assert responses == [True]
    assert "REVOCATION_ANCHOR_LOAD" in operations
    assert "PROTECTED_USE_ACQUIRE" in operations and "PROTECTED_USE_FINISH" in operations
