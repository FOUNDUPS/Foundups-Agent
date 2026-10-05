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


def _public_startup_artifacts(tmp_path):
    """Synthetic authorities, real manifest production and generation activation."""
    from modules.communication.moltbot_bridge.tests import test_reddog_signer_owner_controlled_e0_admission as e0
    from modules.communication.moltbot_bridge.tests import test_reddog_signer_system_service_manifest_selection_loader as mf
    from modules.communication.moltbot_bridge.tests import test_reddog_signed_runtime_artifact_manifest as manifest
    from modules.communication.moltbot_bridge.tests.reddog_grant_authority_service_policy_test_support import grant_service_git_provenance_policy_fields
    from modules.communication.moltbot_bridge.src import reddog_signer_owner_e0_policy_contract as pc

    e0_root = tmp_path / "e0"
    e0_root.mkdir()
    values = e0._fixture(e0_root)
    (tmp_path / "manifest").mkdir()
    harness = manifest._build_harness(tmp_path / "manifest", repo_root=e0_root / "repo")
    policy = values["policy"]
    policy.update(schema_version=pc.POLICY_SCHEMA_V8, target_signer_public_key=harness.reddog_public_key,
                  target_signer_key_fingerprint=e0.public_key_fingerprint(harness.reddog_public_key),
                  target_signer_key_epoch=KEY_EPOCH,
                  signing_key_ref_hash=pc.signer_key_reference_digest("systemd-creds://work"),
                  audit_mac_key_ref_hash=pc.signer_key_reference_digest("systemd-creds://audit"),
                  allowed_operations=["signed_0102_readonly_review:foundup_module"],
                  allowed_authority_tiers=["HIGH", "LOW"], consensus_required_tiers=["HIGH"])
    policy.update(grant_service_git_provenance_policy_fields(repo_root_digest=e0.DIGEST_A,
        source_commit_sha="1" * 40, object_format="sha1", source_policy_digest=e0.DIGEST_D,
        source_descriptor_digest=e0.DIGEST_E))
    state = _public_startup_state(tmp_path / "root-state", policy, harness.repo_root)
    policy["revocation_anchor_state_binding_digest"] = state.state_binding_digest
    config = e0._config(repo=harness.repo_root, runtime=harness.runtime_root,
        signer=e0_root / "signer", target_public=harness.reddog_public_key,
        signing_ref="systemd-creds://work", audit_ref="systemd-creds://audit",
        authority_binding_digest=pc.signer_owner_e0_authority_binding_digest(policy))
    config["key_provider_profiles"][0]["expected_key_epoch"] = KEY_EPOCH
    config["control_loop_authority_policy"] = mf._runtime_config(harness)["control_loop_authority_policy"]
    config_path = mf._write_json(harness.runtime_root / "signer_service_config.json", config)
    principals = harness.runtime_root / "principal_authority_records.json"
    mf._write_json(principals, values["principal_payload"])
    owner_path = tmp_path / "signer-owner" / "owner.json"
    packet_path, supplied = mf._runtime_packet(harness, config_path, owner_path)
    authority, boundary = mf._fresh_manifest_authority(harness)
    mf._sign_and_publish_manifest(harness, authority, boundary)
    selector = mf.create_runtime_artifact_manifest_launch_selection_boundary(
        authority=authority, authority_boundary=boundary, signature_verifier=mf.Ed25519SignatureVerifier())
    selected = dict(selector.consume(selector.select(harness.read_manifest(), now_epoch=NOW)))
    owner = mf._generation_owner_config(harness, selected)
    values.update(harness=harness, repo=harness.repo_root, config=config, config_path=config_path,
        target_private=harness.reddog_private_key, target_public=harness.reddog_public_key,
        owner_config_path=owner_path, state=state, supplied=supplied, packet_path=packet_path)
    return values, owner, selected


def _public_startup_state(root, policy, repo):
    from modules.communication.moltbot_bridge.src.reddog_sqlite_monotonic_authority_store import SqliteMonotonicAuthorityStore
    from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_state import RootVerifiedOutcomeAuthorityState
    stores = []
    for name, filename, identifier, receipt in (
        ("state", "verified-outcome-authority.sqlite3", policy["revocation_anchor_store_id"], policy["revocation_anchor_store_durability_receipt_id"]),
        ("witness", "verified-outcome-authority-witness.sqlite3", "public-root-witness", "sha256:" + "a" * 64),
        ("installation", "verified-outcome-authority-installation.sqlite3", "public-root-installation", "sha256:" + "b" * 64),
    ):
        stores.append(SqliteMonotonicAuthorityStore(root / name / filename, allowed_root=root / name,
            repo_root=repo, store_id=identifier, durability_receipt_id=receipt))
    return RootVerifiedOutcomeAuthorityState(*stores, repo_root=repo, require_root_ownership=False)  # OS seam only.


def _public_startup_owner(values, owner, selected, tmp_path, monkeypatch):
    from modules.communication.moltbot_bridge.tests import test_reddog_signer_owner_controlled_e0_admission as e0
    from modules.communication.moltbot_bridge.tests import test_reddog_effect_consent_owner_versions as versions
    from modules.communication.moltbot_bridge.tests import test_reddog_signer_socket_service_runtime_wiring as wf
    from modules.communication.moltbot_bridge.src import reddog_signer_system_service_wsp71_resolver_supply as supply

    control, public = e0._keypair()
    policy, state = values["policy"], values["state"]
    descriptor, _, _ = _descriptor(tmp_path / "descriptor", signer_key=values["target_private"],
        grant_overrides={"issued_at": NOW - 1, "expires_at": NOW + 120}, descriptor_overrides={
            "schema_version": "foundup_verified_outcome_root_authority.v2",
            "root_control_authentication": {"purpose": supply.ROOT_CONTROL_PURPOSE, "public_key": public, "key_epoch": "control-1"},
            "issued_at": NOW - 2, "expires_at": NOW + 200,
            "signer_key_epoch": KEY_EPOCH, "signer_run_packet_id": values["supplied"].run_packet_id,
            "signer_config_digest": selected["config_digest"], "signer_session_id": "session-prod",
            "signer_manifest_id": selected["manifest_id"],
            "signer_artifact_generation_digest": selected["artifact_generation_digest"],
            "replay_store_id": state.store_id, "replay_store_durability_receipt_id": state.durability_receipt_id})
    outcome = {"descriptor": descriptor, "authority_socket_path": str(tmp_path / "root-authority.sock"),
        "authority_service_uid": 0, "signer_uid": 1201, "signer_gid": 1201, "signer_principal_id": "signer:reddog"}
    for name, store in zip(("state", "state_witness", "installation"), (state._primary, state._witness, state._installation)):
        outcome.update({name + "_root": str(store.rollback_domain_root), name + "_path": str(store.path),
            name + "_store_id": store.store_id, name + "_durability_receipt_id": store.durability_receipt_id})
    metadata_root = tmp_path / "metadata"
    metadata_root.mkdir()
    with monkeypatch.context() as metadata_only:
        _, _, _, template, _ = versions.owner_fixture(metadata_only, metadata_root)
    for key in ("independent_grant_authority", "grant_authority_source_policy", "reviewer_designation_authority", "effect_consent_authority"):
        owner[key] = template[key]
    owner["grant_authority_source_policy"]["repo_root_digest"] = owner["repo_root_digest"]
    owner.update(schema_version=loader_module.SCHEMA_VERSION_V7, verified_outcome_authority=outcome)
    replay_fixture = wf.factory_fixture.grant_fixture
    replay = replay_fixture.SignerGrantReplayStoreConfig(
        nonce_path=Path(policy["replay_path"]), nonce_root=Path(policy["replay_root"]),
        high_water_path=tmp_path / "grant-high" / "authority.sqlite3", high_water_root=tmp_path / "grant-high",
        repo_root=values["repo"], replay_store_binding_digest=replay_fixture._binding().replay_store_binding_digest,
        replay_store_id=policy["replay_store_id"], durability_receipt_id=policy["replay_store_durability_receipt_id"])
    replay_fixture._provision_store(replay)  # Explicit synthetic setup, not startup.
    owner["startup_custody"] = _public_startup_custody(values, descriptor, replay)
    owner["config_id"] = digest({k: v for k, v in owner.items() if k != "config_id"})
    values["owner_config_path"].parent.mkdir()
    values["owner_config_path"].write_text(json.dumps(owner, sort_keys=True), encoding="ascii")
    values.update(control_private=control, owner=owner, replay_config=replay)
    return values


def _public_startup_custody(values, descriptor, replay):
    from modules.communication.moltbot_bridge.src import reddog_signer_system_service_wsp71_resolver_supply as supply
    binding = dict(credential_directory="/run/credentials/public-startup.service", expected_uid=1201,
        expected_gid=1201, expected_requester="signer:reddog", issued_at=NOW - 1, expires_at=NOW + 60,
        credential_ids=["audit", "control", "integrity", "work"], max_secret_bytes=65536)
    permissions = {}
    for purpose, credential, identity in (
        (supply.ROOT_LOAD_PURPOSE, "work", {"public_key": descriptor["signer_public_key"], "key_epoch": KEY_EPOCH}),
        (supply.ROOT_CONTROL_PURPOSE, "control", descriptor["root_control_authentication"]),
    ):
        permissions[purpose] = dict(operation="SECRETS_READ", reference="systemd-creds://" + credential,
            requester_id="signer:reddog", purpose=purpose, public_key=identity["public_key"], key_epoch=identity["key_epoch"],
            issued_at=NOW - 1, expires_at=NOW + 30)
    return dict(policy_path=str(values["owner_config_path"].parent / "e0-policy.json"), credential_binding=binding,
        root_request_permissions=permissions, proposal_replay_store=None,
        replay_store=dict(high_water_root=str(replay.high_water_root), high_water_path=str(replay.high_water_path),
            replay_store_binding_digest=replay.replay_store_binding_digest),
        replay_integrity_permission=dict(operation="SECRETS_READ", reference="systemd-creds://integrity",
            requester_id="signer:reddog", purpose="signer-grant-replay-integrity.v1", encoding="utf8",
            issued_at=NOW - 1, expires_at=NOW + 30))


def _public_startup_finalize(values, monkeypatch):
    from modules.communication.moltbot_bridge.tests import test_reddog_signer_owner_controlled_e0_admission as e0
    from modules.communication.moltbot_bridge.src import reddog_signer_owner_e0_current_selection as current
    from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_authority_binding import revocation_authority_binding_from_policy

    # Only the OS root-file provenance check is replaced. The loader, signed
    # manifest, durable generation anchor and all E0 validators remain real.
    monkeypatch.setattr(loader_module, "_read_root_owned_bytes", lambda path, _root: path.read_bytes())
    capability, boundary = loader_module.load_system_service_manifest_selection(
        owner_config_path=values["owner_config_path"], repo_root=values["repo"])
    selected = boundary.consume(capability)
    policy = values["policy"]
    for key in ("owner_config_id", "manifest_id", "artifact_generation_digest", "config_digest", "generation", "generation_revision"):
        policy[key] = selected[key]
    policy["target_signer_generation_id"] = policy["artifact_generation_digest"]
    e0._resign(values)
    Path(values["owner"]["startup_custody"]["policy_path"]).write_text(json.dumps(policy, sort_keys=True), encoding="ascii")
    with current.lease_validated_owner_e0_current_admission(
        owner_config_path=values["owner_config_path"], repo_root=values["repo"], policy=policy) as admitted:
        values["admitted"] = admitted
    values["binding"] = revocation_authority_binding_from_policy(policy, repo_root=values["repo"],
        signer_runtime_root=Path(values["config"]["signer_runtime_root"]))


def _public_startup_root_transport(values, monkeypatch):
    from modules.communication.moltbot_bridge.tests import root_revocation_service_fixtures as root
    from modules.communication.moltbot_bridge.tests import test_reddog_signer_root_protected_use_composition as composition
    from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_authority_service import _peer
    from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_authority import _sign

    policy, owner = values["policy"], values["owner"]
    descriptor = owner["verified_outcome_authority"]["descriptor"]
    snapshot = root.RootAuthoritySnapshot(owner_config_id=owner["config_id"],
        authority_generation_sequence=descriptor["authority_generation_sequence"],
        state_binding_digest=values["state"].state_binding_digest, signer_principal_id="signer:reddog",
        signer_uid=1201, signer_gid=1201, descriptor=descriptor)
    root.initialize_root_authority_state(values["state"], snapshot, now_epoch=NOW)
    authority = root._create_root_revocation_service_authority(owner_config_path=values["owner_config_path"], repo_root=values["repo"])
    operations = []
    def roundtrip(_path, raw, _uid, _timeout):
        operations.append(json.loads(raw)["operation"])
        return composition.handle_root_authority_wire_request(raw, peer=_peer("signer:reddog", uid=1201, gid=1201),
            state=values["state"], snapshot_supplier=lambda: snapshot, revocation_authority=authority, now_epoch=NOW)
    monkeypatch.setattr(outcome_client_module, "_require_protected_socket", lambda *_: None)
    monkeypatch.setattr(outcome_client_module, "_root_socket_roundtrip", roundtrip)
    exchange = root.build_root_authority_socket_exchange(repo_root=values["repo"], socket_path=owner["verified_outcome_authority"]["authority_socket_path"])
    client = root._create_root_revocation_anchor_authority(descriptor, owner_config_id=owner["config_id"],
        policy=policy, binding=values["binding"], exchange=exchange,
        request_signer=lambda message: _sign(values["target_private"], message), now_epoch=NOW)
    values.update(snapshot=snapshot, server_authority=authority, client=client,
        store=root.SignerGrantRevocationAuthorityStore(values["binding"], repo_root=values["repo"]),
        witness=root.witness_store(values["binding"], values["repo"]))
    composition._install_current(values, root.signed_snapshot(values))  # Signed fixture provisioning before startup.
    operations.clear()
    return operations


def test_public_v7_startup_real_generation_grant_signature_and_replay(tmp_path, monkeypatch):
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
