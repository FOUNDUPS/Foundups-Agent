"""LOW RPC regressions, including Linux process locks; authority and keys are synthetic."""

from contextlib import contextmanager
from dataclasses import replace
import json
import multiprocessing
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import time
from types import SimpleNamespace

import pytest

from modules.communication.moltbot_bridge.tests.test_reddog_signer_independent_secret_grant_provider import (
    _store, _GrantClient, _owner_policy, _binding, _public, _provider_for,
    provider_module, NOW, _Resolver, _target_request, Ed25519PrivateKey,
    SignerSecretAccessGrantRejected,
)

from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_client import build_reddog_isolated_signer_socket_client
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_resident_service import serve_reddog_isolated_signer_socket_bounded
from modules.communication.moltbot_bridge.src.reddog_signer_socket_peer_credential_attestor import KernelPeerCredentialAttestor, PeerCredentialPolicy
from modules.infrastructure.shared_utilities.runtime_artifact_safety import confined_runtime_operation_lock
from modules.communication.moltbot_bridge.tests import test_reddog_signer_independent_secret_grant_provider as fixture




def _owner_lock(root):
    return confined_runtime_operation_lock(
        root / "owner-state" / "generation.lock", repo_root=root / "repo",
        allowed_root=root / "owner-state",
    )


def _state(root):
    return json.loads((root / "owner-state" / "current.json").read_text())


def _lock_is_held(root):
    import fcntl
    with (root / "owner-state" / "generation.lock").open("rb") as stream:
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
    return False


class _FencedSyntheticGrantSigner:
    """Real signer response; synthetic permission callback takes the real owner lock."""
    def __init__(self, root, mode, entered, acquired):
        self.root, self.mode, self.entered, self.acquired = root, mode, entered, acquired

    def sign(self, request, peer):
        self.entered.set()
        with _owner_lock(self.root):
            self.acquired.set()
            current = _state(self.root)
            if self.mode in ("current", "lease"):
                current["now"] += 1
            if self.mode == "policy":
                current["revision"] = "changed"
            if self.mode == "generation":
                current["generation"] = 2
            if self.mode == "expired":
                current["now"] = fixture.NOW + 121
            (self.root / "owner-state" / "current.json").write_text(json.dumps(current))
            private = fixture.Ed25519PrivateKey.from_private_bytes(bytes(range(32, 64)))
            return fixture._GrantClient(private).sign(request)


def _serve(root, mode, ready, entered, acquired, results):
    result = serve_reddog_isolated_signer_socket_bounded(
        repo_root=root / "repo", socket_path=root / "socket" / "grant.sock",
        backend=_FencedSyntheticGrantSigner(root, mode, entered, acquired),
        peer_attestor=KernelPeerCredentialAttestor(PeerCredentialPolicy(
            {os.getuid(): "provider:grant-client"}, (os.getgid(),))),
        max_requests=1, timeout_s=3.0, ready_callback=ready.set,
    )
    results.put((os.getpid(), (root / "owner-state" / "generation.lock").stat().st_ino,
                 result.socket_removed))


def _provider(root, monkeypatch, client):
    store = fixture._store(root / "grant-store")
    private = fixture.Ed25519PrivateKey.from_private_bytes(bytes(range(32, 64)))
    policy = fixture._owner_policy(fixture._binding(store, fixture._public(private)))
    provider = fixture._provider_for(root, monkeypatch, store=store, private=private,
                                    client=client, policy=policy)
    events = []

    @contextmanager
    def owner_lease(**kwargs):
        with _owner_lock(root):
            state = _state(root)
            events.append("enter")
            if state["now"] >= policy["expires_at"]:
                raise ValueError("synthetic_current_owner_expired")
            yield SimpleNamespace(
                policy=dict(policy, owner_revision=state["revision"]),
                selection={"generation": state["generation"],
                           "selection_issued_at": state["now"],
                           "selection_expires_at": state["now"] + 30},
                resolver=fixture._Resolver(fixture._public(private)),
            )
        events.append("exit")

    monkeypatch.setattr(fixture.provider_module, "lease_validated_owner_e0_current_admission", owner_lease)
    return replace(provider, clock=lambda: _state(root)["now"]), events


@contextmanager
def _native_case(monkeypatch, mode):
    with TemporaryDirectory(prefix="grant-rpc-") as directory:
        root = Path(directory)
        for name in ("repo", "owner-state", "socket"):
            (root / name).mkdir(mode=0o700)
        (root / "owner-state" / "current.json").write_text(json.dumps(
            {"generation": 1, "revision": "original", "now": fixture.NOW}))
        with _owner_lock(root):
            pass
        context = multiprocessing.get_context("fork")
        ready, entered, acquired, results = context.Event(), context.Event(), context.Event(), context.Queue()
        process = context.Process(target=_serve, args=(root, mode, ready, entered, acquired, results))
        process.start()
        try:
            assert ready.wait(5), "owned grant signer failed to bind"
            built = build_reddog_isolated_signer_socket_client(
                repo_root=root / "repo", socket_path=root / "socket" / "grant.sock",
                trusted_socket_root=root / "socket", expected_server_uid=os.getuid(),
                expected_server_gid=os.getgid(), timeout_s=0.5,
            )
            assert built.accepted
            provider, events = _provider(root, monkeypatch, built.client)
            yield SimpleNamespace(provider=provider, events=events, root=root,
                                  entered=entered, acquired=acquired)
            process.join(5)
            assert not process.is_alive(), "owned signer exceeded process deadline"
            assert process.exitcode == 0
            pid, inode, removed = results.get(timeout=1)
            assert pid != os.getpid()
            assert inode == (root / "owner-state" / "generation.lock").stat().st_ino
            assert removed or mode == "legacy-control"
            assert not (root / "socket" / "grant.sock").exists()
        finally:
            if process.is_alive():
                process.terminate()
                process.join(2)
            results.close()


@pytest.mark.skipif(sys.platform != "linux", reason="real Linux flock and AF_UNIX required")
@pytest.mark.parametrize("mode", ["legacy-control", "current", "lease", "policy", "generation", "expired"])
def test_low_grant_rpc_generation_lock_across_processes(monkeypatch, mode):
    with _native_case(monkeypatch, mode) as case:
        started = time.monotonic()
        request = fixture._target_request()
        if mode == "legacy-control":
            # Exact old call ordering: first owner lease encloses _issue and RPC.
            with fixture.provider_module.lease_validated_owner_e0_current_admission() as owner:
                with pytest.raises(ValueError, match="secret_grant_signer_rejected"):
                    case.provider._issue(request, owner, None)
                assert case.entered.is_set() and not case.acquired.is_set()
            assert time.monotonic() - started >= 0.4
        elif mode in ("current", "lease"):
            if mode == "lease":
                with case.provider.lease(request) as grant:
                    assert _lock_is_held(case.root)
                assert not _lock_is_held(case.root)
            else:
                grant = case.provider.issue_grant(request)
            assert fixture.Ed25519SignatureVerifier().verify(
                case.provider.grant_authority.public_key,
                fixture.canonical_signer_secret_access_grant_input(grant), grant["signature"])
            assert case.events == ["enter", "exit", "enter", "exit"]
            assert case.acquired.is_set()
        else:
            with pytest.raises((ValueError, fixture.SignerSecretAccessGrantRejected)):
                case.provider.issue_grant(request)
            assert case.acquired.is_set()
        assert time.monotonic() - started < 5


@pytest.mark.parametrize("change", ["policy", "generation", "binding", "expired", "cleanup", "timeout"])
def test_low_rpc_rechecks_owner_and_freshness_before_return(tmp_path, monkeypatch, change):
    store = _store(tmp_path)
    private = Ed25519PrivateKey.generate()
    client = _GrantClient(private)
    policy = _owner_policy(_binding(store, _public(private)))
    provider = _provider_for(tmp_path, monkeypatch, store=store, private=private,
                             client=client, policy=policy)
    original_binding = provider_module.resolve_secret_grant_target_binding
    binding_calls = []
    def resolve_binding(*args):
        binding_calls.append(1)
        result = original_binding(*args)
        return replace(result, replay_store_instance_digest="sha256:" + "e" * 64) if change == "binding" and len(binding_calls) == 2 else result

    monkeypatch.setattr(provider_module, "resolve_secret_grant_target_binding", resolve_binding)
    selection, clock, active, entries = {"generation": 1}, [NOW], [], []

    @contextmanager
    def lease(**kwargs):
        active.append(1)
        entries.append(1)
        try:
            yield SimpleNamespace(policy=policy, selection=selection, resolver=_Resolver(_public(private)))
        finally:
            active.pop()
        if change == "cleanup" and len(entries) == 2:
            raise ValueError("synthetic_second_lease_exit_failed")

    original = client.sign
    def sign(request):
        assert not active
        if change == "timeout":
            raise TimeoutError("synthetic_rpc_timeout")
        response = original(request)
        if change == "policy":
            policy["owner_revision"] = "changed"
        if change == "generation":
            selection["generation"] = 2
        if change == "expired":
            clock[0] = NOW + 31
        return response

    monkeypatch.setattr(provider_module, "lease_validated_owner_e0_current_admission", lease)
    monkeypatch.setattr(client, "sign", sign)
    provider = replace(provider, clock=lambda: clock[0])
    with pytest.raises((ValueError, TimeoutError, SignerSecretAccessGrantRejected)):
        provider.issue_grant(_target_request())
    assert not active
    assert len(entries) == (1 if change == "timeout" else 2)
    assert client.calls == (0 if change == "timeout" else 1)



def _fresh_launch_selection(tmp_path, selected_at):
    from modules.communication.moltbot_bridge.src.reddog_current_generation_manifest_launch_selection import (
        _launch_values, PRINCIPAL_AUTHORITY_RECORDS_FILENAME,
    )
    activation = SimpleNamespace(
        manifest_id="sha256:" + "1" * 64, artifact_generation_digest="sha256:" + "2" * 64,
        config_digest="sha256:" + "3" * 64, config_raw_digest="sha256:" + "4" * 64,
        run_packet_digest="sha256:" + "5" * 64, generation=1, revision="revision-1",
    )
    manifest = {"expires_at": NOW + 120, "artifacts": [{
        "filename": PRINCIPAL_AUTHORITY_RECORDS_FILENAME, "content_digest": "sha256:" + "6" * 64}]}
    return _launch_values(manifest, activation, tmp_path / "repo", tmp_path / "runtime",
                          selected_at=selected_at, owner_config_id="sha256:" + "7" * 64,
                          generation_public_key="synthetic-generation-key")



@pytest.mark.parametrize("change", [
    None, "manifest_id", "generation_revision", "owner_config_id",
    "principal_authority_records_digest", "manifest_expires_at", "generation_public_key",
])
def test_low_rpc_compares_authority_not_refreshed_observation_window(tmp_path, monkeypatch, change):
    store = _store(tmp_path)
    private = Ed25519PrivateKey.generate()
    client = _GrantClient(private)
    policy = _owner_policy(_binding(store, _public(private)))
    provider = _provider_for(tmp_path, monkeypatch, store=store, private=private,
                             client=client, policy=policy)
    entries = []

    @contextmanager
    def lease(**kwargs):
        entries.append(1)
        selection = dict(_fresh_launch_selection(tmp_path, NOW + len(entries)))
        if change is not None and len(entries) == 2:
            selection[change] = NOW + 121 if change == "manifest_expires_at" else "changed"
        yield SimpleNamespace(policy=policy, selection=selection, resolver=_Resolver(_public(private)))

    monkeypatch.setattr(provider_module, "lease_validated_owner_e0_current_admission", lease)
    if change is None:
        assert provider.issue_grant(_target_request())["signature"] != "pending-signature"
    else:
        with pytest.raises(ValueError, match="secret_grant_owner_changed"):
            provider.issue_grant(_target_request())
    assert len(entries) == 2 and client.calls == 1
