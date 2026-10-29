"""Target-owned LOW issuance; disposable authority, packet and transport fixtures."""
from contextlib import contextmanager
from dataclasses import replace
import json
import multiprocessing
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import pytest

from modules.communication.moltbot_bridge.src import reddog_signer_initial_handshake_grant_backend as adapter
from modules.communication.moltbot_bridge.src import reddog_signer_independent_secret_grant_provider as provider_owner
from modules.communication.moltbot_bridge.src.reddog_signer_independent_grant_authority_binding import IndependentGrantAuthorityBinding
from modules.communication.moltbot_bridge.src.reddog_signer_wsp71_ephemeral_backend_factory import Wsp71EphemeralSignerBackendFactory
from modules.communication.moltbot_bridge.tests import test_reddog_signer_wsp71_ephemeral_backend_factory as fixture
from modules.communication.moltbot_bridge.tests import test_reddog_signer_independent_secret_grant_provider as provider_fixture
from modules.communication.moltbot_bridge.tests import test_reddog_signer_mutual_peer_handshake as handshake


def _case(tmp_path, monkeypatch, *, timeout_s=None):
    if timeout_s is not None:
        from modules.communication.moltbot_bridge.src import reddog_signer_socket_service_config_composition as composition
        compose = composition.compose_initial_handshake_service_config

        def configured(**kwargs):
            return compose(**dict(kwargs, timeout_s=timeout_s))

        # Set the public input before the fixture binds/signs its configuration.
        monkeypatch.setattr(composition, "compose_initial_handshake_service_config", configured)
    case = fixture._admitted_initial_handshake_case(tmp_path, monkeypatch)
    case.client = provider_fixture._GrantClient(case.values["grant_private"])
    case.supply_calls = []
    case.after_rpc = lambda: None
    case.after_issue = lambda _grant: None
    original_sign = case.client.sign

    def sign(request):
        assert case.active is False, "grant RPC while target owner lease held"
        case.events.append("grant_rpc")
        result = original_sign(request)
        case.after_rpc()
        return result

    case.client.sign = sign
    monkeypatch.setattr(adapter, "load_system_service_independent_grant_authority_client",
                        lambda **kwargs: _supply(case, kwargs))
    # These fixtures substitute custody/OS transport, not provider verification,
    # signed E0 admission, target revocation, replay consumption or Ed25519.
    monkeypatch.setattr(provider_owner, "lease_validated_owner_e0_current_admission",
                        case.admitted_fixture.grant_owner.lease_validated_owner_e0_current_admission)
    original_issue = provider_owner.IndependentSignerSecretGrantProvider.issue_grant

    def issue(provider, request, **kwargs):
        result = original_issue(provider, request, **kwargs)
        assert case.active is False
        case.grant = result
        case.after_issue(result)
        return result

    monkeypatch.setattr(provider_owner.IndependentSignerSecretGrantProvider, "issue_grant", issue)
    original_factory = Wsp71EphemeralSignerBackendFactory.__call__

    def factory(value):
        result = original_factory(value)
        return replace(result, backend=replace(result.backend, proposal_clock=lambda: fixture.grant_fixture.NOW))

    monkeypatch.setattr(Wsp71EphemeralSignerBackendFactory, "__call__", factory)
    return case


def _supply(case, kwargs):
    assert case.active is False
    policy = case.owner.policy
    assert kwargs["owner_policy"] == policy
    assert kwargs["owner_config_path"] == case.admission.owner_config_path
    assert kwargs["repo_root"] == case.config.repo_root
    case.supply_calls.append(kwargs)
    return SimpleNamespace(binding=IndependentGrantAuthorityBinding(
        client=case.client, authority_root=str(case.values["repo"].parent / "independent-grant"),
        principal_id=policy["grant_authority_principal_id"],
        principal_provider=policy["grant_authority_principal_provider"],
        public_key=policy["grant_authority_public_key"],
        key_epoch=policy["grant_authority_key_epoch"],
        requester_principal_id=policy["grant_requester_principal_id"],
    ))


def _request(case):
    binding = case.config.signer_peer_instance_binding
    return handshake._request(
        case.values["target_private"], run_packet_id=binding.run_packet_id,
        manifest_id=binding.manifest_id, artifact_generation_digest=binding.artifact_generation_digest,
        config_digest=binding.config_digest, session_id=binding.session_id,
        socket_path=binding.socket_path, key_epoch="target-epoch-1",
        requester_principal_id="principal:grant-admin", now_epoch=fixture.grant_fixture.NOW)


def _run(case, action):
    errors = []
    def serve(**kwargs):
        try:
            assert type(kwargs["backend"]) is adapter.InitialHandshakeGrantBackend
            case.request = _request(case)
            action(kwargs["backend"])
        except Exception as error:
            errors.append(error)
            raise
        return case.admitted_fixture.CapturingBoundedService()(**kwargs)

    result = case.admitted_fixture.run_reddog_signer_socket_service_runtime_wiring(
        case.config, case.resolver, serve_bounded=serve, secret_grant_admission=case.admission)
    if errors:
        raise errors[0]
    assert result.accepted, (result.rejection_reasons, case.events)


def _plain_wire(case, backend):
    protocol = fixture.grant_fixture
    wire = {"schema_version": "reddog_signer_socket_request.v1", "request": case.request.to_dict()}
    return json.loads(protocol.handle_reddog_isolated_signer_socket_request(
        json.dumps(wire).encode("utf-8"), peer=case.peer, backend=backend))


def test_plain_request_acquires_verified_grant_before_target_secret_use(tmp_path, monkeypatch):
    case = _case(tmp_path, monkeypatch)

    def action(backend):
        response = _plain_wire(case, backend)
        assert response["accepted"], response["rejection_code"]
        assert fixture.Ed25519SignatureVerifier().verify(
            case.request.signer_public_key, case.request.signing_input, response["signature"])
        assert case.client.calls == len(case.supply_calls) == 1
        assert len(case.resolver.calls) == 2
        assert case.events.index("grant_rpc") < case.events.index("root_acquire") < case.events.index("resolve")
        assert not _plain_wire(case, backend)["accepted"]
        assert case.client.calls == 1 and len(case.resolver.calls) == 2

    _run(case, action)


@pytest.mark.parametrize("mutation", ["work", "other-low", "high", "consensus", "proof", "epoch", "peer", "unattested"])
def test_wrong_request_or_peer_rejected_before_client_or_secret(tmp_path, monkeypatch, mutation):
    case = _case(tmp_path, monkeypatch)

    def action(backend):
        request = replace(case.request, **{
            "work": {"signer_role": "work_authorization"},
            "other-low": {"requested_operation": "read_repo"},
            "high": {"authority_tier": "HIGH"},
            "consensus": {"consensus_receipt_digest": "sha256:" + "a" * 64},
            "proof": {"elevated_consensus_proof": {}},
            "epoch": {"key_epoch": "other-epoch"},
        }.get(mutation, {}))
        peer = replace(case.peer, **{
            "peer": {"peer_principal_id": "principal:other"},
            "unattested": {"boundary_attested": False},
        }.get(mutation, {}))
        assert not backend.sign(request, peer).accepted
        assert case.client.calls == 0 and not case.supply_calls and not case.resolver.calls

    _run(case, action)


@pytest.mark.parametrize("failure", ["rpc", "signature", "audit", "request-drift", "expiry", "owner-drift"])
@pytest.mark.parametrize("timeout_s", [5, 30])
def test_failed_or_late_rpc_never_falls_back_to_target_keys(tmp_path, monkeypatch, failure, timeout_s):
    case = _case(tmp_path, monkeypatch, timeout_s=timeout_s)

    def action(backend):
        if failure == "rpc":
            def unavailable(_request):
                raise TimeoutError("synthetic grant transport unavailable")
            case.client.sign = unavailable
        elif failure == "signature":
            original = case.client.sign
            case.client.sign = lambda request: replace(original(request), signature="invalid")
        elif failure == "audit":
            case.client.valid_audit_attestation = False
        elif failure == "request-drift":
            case.after_rpc = lambda: object.__setattr__(case.request, "nonce", "changed-request")
        elif failure == "expiry":
            case.after_rpc = lambda: monkeypatch.setattr(adapter.time, "time", lambda: fixture.grant_fixture.NOW + 61)
        elif failure == "owner-drift":
            case.after_rpc = lambda: case.admitted_fixture.owner_fixture._CURRENT_SELECTION.update(
                generation_revision="changed-revision")
        assert not backend.sign(case.request, case.peer).accepted
        assert not case.resolver.calls
        before = (case.client.calls, len(case.supply_calls))
        assert not backend.sign(case.request, case.peer).accepted
        assert (case.client.calls, len(case.supply_calls)) == before

    _run(case, action)


@pytest.mark.parametrize("change", ["valid", "wrong-owner", "client-rejected"])
@pytest.mark.parametrize("timeout_s", [0.25, 5, 15.0, 30])
def test_authenticated_client_supply_is_used_with_current_policy(tmp_path, monkeypatch, change, timeout_s):
    from modules.communication.moltbot_bridge.src import reddog_signer_independent_grant_authority_client_supply as supply
    from modules.communication.moltbot_bridge.src import reddog_signer_system_service_manifest_selection_loader as loader
    from modules.communication.moltbot_bridge.tests import test_reddog_signer_independent_grant_authority_client_supply as supply_fixture
    case = _case(tmp_path, monkeypatch, timeout_s=timeout_s)
    roots = tmp_path / "grant-owner-metadata"
    roots.mkdir()
    owner = supply_fixture._owner(roots, config_id=case.owner.policy["owner_config_id"])
    if change == "wrong-owner":
        owner["config_id"] = "sha256:" + "f" * 64
    monkeypatch.setattr(loader, "_load_owner_config", lambda *_args, **_kwargs: owner)
    monkeypatch.setattr(adapter, "load_system_service_independent_grant_authority_client",
                        supply.load_system_service_independent_grant_authority_client)
    monkeypatch.setattr(supply, "lease_validated_owner_e0_current_admission",
                        provider_owner.lease_validated_owner_e0_current_admission)
    built = []

    def build(**kwargs):
        built.append(kwargs)
        return SimpleNamespace(accepted=change != "client-rejected", client=case.client)

    monkeypatch.setattr(supply, "build_reddog_isolated_signer_socket_client", build)

    def action(backend):
        response = _plain_wire(case, backend)
        assert response["accepted"] is (change == "valid"), response["rejection_code"]
        assert len(case.resolver.calls) == (2 if change == "valid" else 0)
        assert len(built) == (0 if change == "wrong-owner" else 1)
        if built:
            assert built[0].get("timeout_s", 5.0) == timeout_s
            assert built[0]["expected_server_uid"] == 1202
            assert built[0]["expected_server_gid"] == 1203
            assert str(built[0]["socket_path"]) == owner["independent_grant_authority"]["authority_socket_path"]

    _run(case, action)


@pytest.mark.parametrize("change", ["generation", "generation-bool", "instance", "expired"])
def test_stale_or_mismatched_initial_instance_never_acquires_grant(tmp_path, monkeypatch, change):
    case = _case(tmp_path, monkeypatch)

    def action(backend):
        instance = backend.backend_factory.signer_peer_instance_binding
        if change == "expired":
            monkeypatch.setattr(adapter.time, "time", lambda: fixture.grant_fixture.NOW + 61)
        else:
            replacement = replace(instance, **{
                "generation": {"generation": 2},
                "generation-bool": {"generation": True},
                "instance": {"session_id": "other-session"},
            }[change])
            object.__setattr__(backend.backend_factory, "signer_peer_instance_binding", replacement)
        assert not backend.sign(case.request, case.peer).accepted
        assert not case.supply_calls and not case.resolver.calls and case.client.calls == 0

    _run(case, action)


@pytest.mark.parametrize("change", ["revoked", "lease-exit"])
def test_final_revocation_and_clean_owner_exit_precede_target_secret_use(tmp_path, monkeypatch, change):
    case = _case(tmp_path, monkeypatch)
    if change == "revoked":
        protected = case.admitted_fixture.protected_fixture
        case.after_issue = lambda grant: protected._install_current(case.values,
            protected._revoking_snapshot(case.values, grant["grant_id"], 2))
    else:
        lease = adapter.lease_signer_socket_service_grant_admission
        entries = []

        @contextmanager
        def fail_final_exit(*args):
            entries.append(1)
            with lease(*args) as selected:
                yield selected
            if len(entries) == 2:
                raise ValueError("synthetic_final_owner_lease_exit_failed")

        monkeypatch.setattr(adapter, "lease_signer_socket_service_grant_admission", fail_final_exit)

    def action(backend):
        assert not backend.sign(case.request, case.peer).accepted
        assert case.client.calls == 1 and not case.resolver.calls

    _run(case, action)


def _native_grant_server(root, case, policy, ready, acquired, results, monkeypatch):
    # Fork-local restoration removes only synthetic target observers. Real grant
    # policy/rate/crypto and kernel peer attestation run in this disposable child.
    monkeypatch.undo()
    from modules.communication.moltbot_bridge.tests import test_reddog_signer_low_grant_rpc as native
    backend = provider_fixture.Ed25519SignerBackend(
        private_key=case.values["grant_private"], public_key=policy.issuer_public_key,
        key_epoch=policy.issuer_key_epoch, audit_mac_builder=provider_fixture._AuditMac(),
        proposal_clock=lambda: fixture.grant_fixture.NOW, secret_grant_authority_policy=policy,
        secret_grant_rate_authority=provider_fixture.DurableSignerSecretGrantRateAuthority(case.admission.replay_store))

    class LockedSigner:
        def sign(self, request, peer):
            with native._owner_lock(root):
                acquired.set()
                return backend.sign(request, peer)

    result = native.serve_reddog_isolated_signer_socket_bounded(
        repo_root=root / "repo", socket_path=root / "socket" / "grant.sock",
        backend=LockedSigner(),
        peer_attestor=native.KernelPeerCredentialAttestor(native.PeerCredentialPolicy(
            {os.getuid(): policy.requester_principal_id}, (os.getgid(),))),
        max_requests=1, timeout_s=3.0, ready_callback=ready.set)
    results.put((os.getpid(), result.socket_removed,
                 (root / "owner-state" / "generation.lock").stat().st_ino))


@contextmanager
def _native_client(case, monkeypatch):
    from modules.communication.moltbot_bridge.tests import test_reddog_signer_low_grant_rpc as native
    with TemporaryDirectory(prefix="target-grant-") as directory:
        root = Path(directory)
        for name in ("repo", "owner-state", "socket"):
            (root / name).mkdir(mode=0o700)
        with native._owner_lock(root):
            pass
        original = provider_owner.lease_validated_owner_e0_current_admission

        @contextmanager
        def locked_owner(**kwargs):
            with native._owner_lock(root):
                with original(**kwargs) as selected:
                    yield selected

        monkeypatch.setattr(provider_owner, "lease_validated_owner_e0_current_admission", locked_owner)
        monkeypatch.setattr(case.admitted_fixture.grant_owner, "lease_validated_owner_e0_current_admission", locked_owner)
        policy = _native_policy(case)
        context = multiprocessing.get_context("fork")
        ready, acquired, results = context.Event(), context.Event(), context.Queue()
        child = context.Process(target=_native_grant_server,
            args=(root, case, policy, ready, acquired, results, monkeypatch))
        child.start()
        try:
            assert ready.wait(5), "disposable issuer did not bind"
            built = native.build_reddog_isolated_signer_socket_client(
                repo_root=root / "repo", socket_path=root / "socket" / "grant.sock",
                trusted_socket_root=root / "socket", expected_server_uid=os.getuid(),
                expected_server_gid=os.getgid(), timeout_s=1.0)
            assert built.accepted
            case.client = built.client
            yield acquired
            child.join(5)
            assert not child.is_alive() and child.exitcode == 0
            pid, removed, inode = results.get(timeout=1)
            assert pid != os.getpid() and removed
            assert inode == (root / "owner-state" / "generation.lock").stat().st_ino
        finally:
            if child.is_alive():
                child.terminate()
                child.join(2)
            results.close()


def _native_policy(case):
    policy = case.owner.policy
    binding = case.admitted_fixture.resolve_secret_grant_target_binding(policy, case.admission.replay_store)
    return provider_owner.build_secret_grant_authority_policy(
        policy, binding, case.admission.replay_store,
        authority_principal_id=policy["grant_authority_principal_id"],
        authority_principal_provider=policy["grant_authority_principal_provider"],
        authority_public_key=policy["grant_authority_public_key"],
        authority_key_epoch=policy["grant_authority_key_epoch"],
        requester_principal_id=policy["grant_requester_principal_id"])


@pytest.mark.skipif(sys.platform != "linux", reason="real Linux process locks and AF_UNIX required")
def test_target_acquires_grant_across_process_without_holding_generation_lock(tmp_path, monkeypatch):
    case = _case(tmp_path, monkeypatch)
    with _native_client(case, monkeypatch) as acquired:
        def action(backend):
            response = _plain_wire(case, backend)
            assert response["accepted"], response["rejection_code"]
            assert acquired.is_set() and len(case.resolver.calls) == 2
            assert fixture.Ed25519SignatureVerifier().verify(
                case.request.signer_public_key, case.request.signing_input, response["signature"])
        _run(case, action)
