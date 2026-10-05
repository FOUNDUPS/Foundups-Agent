"""Tests for the stable signer-owned system-service entrypoint."""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src import (
    foundup_verified_outcome_root_authority_client as outcome_client_module,
    reddog_current_generation_manifest_launch_selection as selection_module,
    reddog_signer_system_service_manifest_selection_loader as loader_module,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    digest,
)
from modules.communication.moltbot_bridge.src.reddog_signer_system_service_entrypoint import (
    SYSTEM_SERVICE_ENTRYPOINT_ACCEPT,
    SYSTEM_SERVICE_ENTRYPOINT_REJECT,
    _UnavailableSystemServiceResolver,
    _run_entrypoint_args,
)
from modules.communication.moltbot_bridge.src.reddog_signer_system_service_manifest_selection_loader import (
    SCHEMA_VERSION_V2,
)
from modules.communication.moltbot_bridge.src.reddog_signer_process_isolation_gate import (
    SignerProcessIsolationReceipt,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_peer_credential_attestor import (
    PeerCredentialPolicy,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    FailClosedPrincipalKeyResolver,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signer_socket_service_runtime_cli import (
    CapturingBoundedService,
    CapturingResolverFactory,
    FakeResolver,
    _audit_secret,
    _private_key_secret,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signer_system_service_manifest_selection_loader import (
    _prepare_real_cli_owner,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signed_runtime_artifact_manifest import (
    CONSENSUS_DIGEST,
    KEY_EPOCH,
    NOW,
    PRINCIPAL_ID,
)
from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_authority import (
    _descriptor,
)

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "reddog_signer_system_service_entrypoint.py"
)


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


@pytest.fixture(autouse=True)
def _trusted_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(selection_module, "_now_epoch", lambda: NOW)
    monkeypatch.setattr(loader_module.time, "time", lambda: NOW)
    monkeypatch.setattr(
        outcome_client_module,
        "_require_protected_socket",
        lambda *_args: (_ for _ in ()).throw(
            AssertionError("dormant_outcome_policy_touched_root_socket")
        ),
    )


def _upgrade_prepared_owner_to_v2(
    prepared: dict, tmp_path: Path, *, bind_runtime: bool = False
) -> dict:
    owner_path = Path(prepared["owner_path"])
    owner = json.loads(owner_path.read_text(encoding="ascii"))
    overrides = {}
    signer_key = None
    if bind_runtime:
        selection = prepared["selection"]
        supplied = prepared["supplied"]
        overrides = {
            "issuer_principal_id": PRINCIPAL_ID,
            "reddog_id": "reddog-0102",
            "consensus_receipt_digest": CONSENSUS_DIGEST,
            "signer_public_key": prepared["harness"].reddog_public_key,
            "signer_key_epoch": KEY_EPOCH,
            "signer_run_packet_id": supplied.run_packet_id,
            "signer_config_digest": supplied.config_digest,
            "signer_session_id": "session-prod",
            "signer_manifest_id": selection["manifest_id"],
            "signer_artifact_generation_digest": selection[
                "artifact_generation_digest"
            ],
        }
        signer_key = prepared["harness"].reddog_private_key
    descriptor, _grant, _store = _descriptor(
        tmp_path / "outcome-source",
        descriptor_overrides=overrides,
        signer_key=signer_key,
    )
    roots = {
        name: tmp_path / f"outcome-{name}"
        for name in ("state", "state-witness", "installation")
    }
    for root in roots.values():
        root.mkdir()
    owner["schema_version"] = SCHEMA_VERSION_V2
    owner["verified_outcome_authority"] = _outcome_owner_block(
        descriptor, roots=roots, tmp_path=tmp_path
    )
    owner["config_id"] = digest(
        {key: value for key, value in owner.items() if key != "config_id"}
    )
    owner_path.write_text(
        json.dumps(owner, sort_keys=True, separators=(",", ":")), encoding="ascii"
    )
    return owner


def _outcome_owner_block(descriptor: dict, *, roots: dict, tmp_path: Path) -> dict:
    return {
        "descriptor": descriptor,
        "authority_socket_path": str(tmp_path / "root-authority.sock"),
        "authority_service_uid": 0,
        "signer_uid": 1201,
        "signer_gid": 1201,
        "signer_principal_id": "reddog-e0-signer",
        "state_root": str(roots["state"]),
        "state_path": str(roots["state"] / "verified-outcome-authority.sqlite3"),
        "state_store_id": descriptor["replay_store_id"],
        "state_durability_receipt_id": descriptor["replay_store_durability_receipt_id"],
        "state_witness_root": str(roots["state-witness"]),
        "state_witness_path": str(
            roots["state-witness"] / "verified-outcome-authority-witness.sqlite3"
        ),
        "state_witness_store_id": "verified-outcome-replay-witness",
        "state_witness_durability_receipt_id": "sha256:" + "7" * 64,
        "installation_root": str(roots["installation"]),
        "installation_path": str(
            roots["installation"] / "verified-outcome-authority-installation.sqlite3"
        ),
        "installation_store_id": "verified-outcome-replay-installation",
        "installation_durability_receipt_id": "sha256:" + "8" * 64,
    }


def _isolation_receipt(accepted: bool) -> SignerProcessIsolationReceipt:
    return SignerProcessIsolationReceipt(
        accepted,
        (() if accepted else ("rejected",)),
        1201,
        1201,
        accepted,
        accepted,
        accepted,
        accepted,
        accepted,
        accepted,
        accepted,
    )


def _accepted_isolation(
    _policy: PeerCredentialPolicy,
    *,
    expected_signer_uid: int,
    expected_signer_gid: int,
) -> SignerProcessIsolationReceipt:
    receipt = _isolation_receipt(True)
    return SignerProcessIsolationReceipt(
        **{
            **receipt.__dict__,
            "signer_uid": expected_signer_uid,
            "signer_gid": expected_signer_gid,
        }
    )


def test_stable_entrypoint_selects_current_generation_and_serves_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare_real_cli_owner(tmp_path, monkeypatch)
    _upgrade_prepared_owner_to_v2(prepared, tmp_path)
    resolver = FakeResolver(
        {
            "op://prod-vault/reddog-signing/private": _private_key_secret(
                prepared["harness"].reddog_private_key
            ),
            "op://prod-vault/reddog-audit/mac": _audit_secret(),
        }
    )
    factory = CapturingResolverFactory(resolver)
    service = CapturingBoundedService()
    emitted: list[str] = []
    isolation_calls: list[tuple[int, int]] = []

    def isolation_gate(
        policy: PeerCredentialPolicy,
        *,
        expected_signer_uid: int,
        expected_signer_gid: int,
    ) -> SignerProcessIsolationReceipt:
        isolation_calls.append((expected_signer_uid, expected_signer_gid))
        return _accepted_isolation(
            policy,
            expected_signer_uid=expected_signer_uid,
            expected_signer_gid=expected_signer_gid,
        )

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
        process_isolation_gate=isolation_gate,
    )

    payload = json.loads(emitted[0])
    assert code == 0, payload
    assert payload["status"] == SYSTEM_SERVICE_ENTRYPOINT_ACCEPT
    assert len(factory.calls) == 1
    assert len(service.calls) == 1
    assert isolation_calls == [(1201, 1201)]
    assert payload["no_serialized_argv_executed"] is True
    assert payload["no_signer_process_spawned"] is True
    assert payload["no_shell_invoked"] is True


def _resolver_for(prepared: dict) -> FakeResolver:
    return FakeResolver(
        {
            "op://prod-vault/reddog-signing/private": _private_key_secret(
                prepared["harness"].reddog_private_key
            ),
            "op://prod-vault/reddog-audit/mac": _audit_secret(),
        }
    )


def test_configured_outcome_policy_uses_root_authority_after_isolation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare_real_cli_owner(
        tmp_path, monkeypatch, include_outcome_policy=True
    )
    _upgrade_prepared_owner_to_v2(prepared, tmp_path, bind_runtime=True)
    monkeypatch.setattr(
        outcome_client_module, "_require_protected_socket", lambda *_args: None
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
        process_isolation_gate=_accepted_isolation,
    )

    assert code == 0, json.loads(emitted[0])
    assert json.loads(emitted[0])["status"] == SYSTEM_SERVICE_ENTRYPOINT_ACCEPT
    assert len(factory.calls) == 1
    assert len(service.calls) == 1


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


def test_production_secret_resolver_fails_closed_without_e0() -> None:
    result = _UnavailableSystemServiceResolver.resolve(
        "op://prod-vault/reddog-signing/private",
        requester_id="signer:reddog",
    )

    assert result.success is False
    assert result.get_value() is None
    assert result.error_message == "system_service_secret_resolver_not_admitted"


@pytest.mark.parametrize("isolation_accepts", [False, True])
def test_entrypoint_defers_startup_dependencies_until_isolation(
    tmp_path, monkeypatch, isolation_accepts,
):
    """Real bootstrap ordering; isolation and dependency failure are synthetic."""
    from dataclasses import replace

    prepared = _prepare_real_cli_owner(tmp_path, monkeypatch)
    _upgrade_prepared_owner_to_v2(prepared, tmp_path)
    startup = loader_module.load_system_service_startup_selection(
        owner_config_path=prepared["owner_path"], repo_root=prepared["harness"].repo_root,
    )
    calls = []

    def dependencies():
        calls.append("dependencies")
        raise ValueError("synthetic_missing_provisioned_custody")

    def isolation(policy, **kwargs):
        calls.append("isolation")
        if not isolation_accepts:
            raise ValueError("synthetic_isolation_denied")
        return _accepted_isolation(policy, **kwargs)

    startup = replace(startup, runtime_dependencies_supplier=dependencies)
    factory = CapturingResolverFactory(FakeResolver({}))
    service = CapturingBoundedService()
    emitted = []
    code = _run_entrypoint_args(
        argparse.Namespace(repo_root=str(prepared["harness"].repo_root),
                           owner_authority_config=str(prepared["owner_path"])),
        resolver_factory=factory, serve_bounded=service, emit=emitted.append,
        principal_key_resolver=FailClosedPrincipalKeyResolver(),
        proposal_replay_high_water_store=None,
        startup_selection_loader=lambda **kwargs: startup,
        process_isolation_gate=isolation,
    )
    assert code == 2
    assert calls == (["isolation", "dependencies"] if isolation_accepts else ["isolation"])
    assert factory.calls == [] and service.calls == []
    assert json.loads(emitted[0])["status"] == SYSTEM_SERVICE_ENTRYPOINT_REJECT
    assert json.loads(emitted[0])["result"]["no_runtime_secret_file_loaded"] is None


def test_real_module_entrypoint_exposes_stable_help_command() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            (
                "modules.communication.moltbot_bridge.src."
                "reddog_signer_system_service_entrypoint"
            ),
            "--help",
        ],
        cwd=Path(__file__).resolve().parents[4],
        capture_output=True,
        check=False,
        text=True,
        timeout=10,
    )

    assert completed.returncode == 0, completed.stderr
    assert "--repo-root" in completed.stdout
    assert "--owner-authority-config" in completed.stdout


def test_entrypoint_has_no_process_or_dynamic_execution_surface() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    import_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    attributes = {
        (node.value.id, node.attr)
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
    }

    assert "subprocess" not in imported
    assert not any(name.endswith("op_cli_secret_resolver") for name in import_modules)
    assert not {"eval", "exec", "compile"} & calls
    assert (
        not {
            ("os", "system"),
            ("os", "popen"),
            ("os", "spawn"),
        }
        & attributes
    )
