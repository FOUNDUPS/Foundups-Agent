"""Composition tests with synthetic ownership/custody; not native admission.

Real components: grant request validation, Ed25519 backend, audit signature,
durable rate store, socket framing/dispatch. Test seams replace root admission,
revocation, process isolation, peer attribution and manager-delivered custody.
"""
import ast
import base64
import socket
import sys
import threading
import time
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from modules.communication.moltbot_bridge.src import reddog_grant_authority_service as service
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import Ed25519SignatureVerifier
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_client import build_reddog_isolated_signer_socket_client
from modules.communication.moltbot_bridge.src.reddog_signer_key_provider_dryrun import SIGNING_KEY_PREFIX, AUDIT_KEY_PREFIX
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_issuance import build_secret_grant_signing_request
from modules.communication.moltbot_bridge.tests import test_reddog_signer_independent_secret_grant_provider as fixture
from modules.communication.moltbot_bridge.tests import test_reddog_external_signer_authoritative_use_lease as store_fixture
from modules.infrastructure.secrets_mcp.src.vault_resolver import ResolveResult, hash_reference


class FixtureOracle:
    """Only a test token; production exact-type admission rejects it."""


def _fixture_inputs(tmp_path):
    store = fixture._store(tmp_path)
    private = Ed25519PrivateKey.from_private_bytes(bytes(range(1, 33)))
    binding = fixture._binding(store, fixture._public(private))
    policy = fixture._owner_policy(binding)
    policy.update(allowed_operations=[service.LOW_OPERATION], allowed_authority_tiers=['LOW'],
                  consensus_required_tiers=[], rate_limit_max_requests=2,
                  replay_root=str(store._config.nonce_root), replay_path=str(store._config.nonce_path))
    profile = service.SignerKeyProviderProfile('grant-review', 'grant:review',
        'systemd-creds://grant-signing', 'systemd-creds://grant-audit', binding.issuer_public_key,
        fixture.public_key_fingerprint(binding.issuer_public_key), 'grant-epoch-1',
        'sha256:'+'9'*64, 30)
    policy.update(grant_authority_signer_agent_id=profile.signer_agent_id,
        grant_authority_signer_profile_id=profile.signer_profile_id,
        grant_authority_key_fingerprint=profile.expected_key_fingerprint,
        grant_authority_permission_snapshot_digest=profile.permission_snapshot_digest,
        grant_authority_signing_key_ref_hash=service.signer_key_reference_digest(profile.signing_key_ref),
        grant_authority_audit_mac_key_ref_hash=service.signer_key_reference_digest(profile.audit_mac_key_ref))
    custody = service.SystemdCredentialBinding('/run/credentials/fixture-grant.service', 997, 997,
        profile.signer_agent_id, fixture.NOW-1, fixture.NOW+120,
        frozenset({'grant-signing', 'grant-audit'}))
    runtime = tmp_path/'grant'; runtime.mkdir()
    owner = dict(config_id=policy['owner_config_id'],
        independent_grant_authority=dict(authority_root=str(runtime),
            authority_socket_path=str(runtime/'grant.sock'), authority_service_uid=997, authority_service_gid=997),
        verified_outcome_authority=dict(signer_uid=998, signer_gid=998))
    deps = service.GrantAuthorityServiceDependencies(policy, profile, custody, store, FixtureOracle())
    return SimpleNamespace(deps=deps, owner=owner, private=private, binding=binding,
        repo=store._config.repo_root, owner_path=tmp_path/'owner.json', events=[], active=False)


def _synthetic_custody(case):
    class CredentialFixture:
        def __init__(self, binding):
            assert case.active and binding is case.deps.credential_binding
            case.events.append('new-custody')

        def resolve(self, reference, requester_id=None):
            assert case.active and requester_id == case.deps.issuer_profile.signer_agent_id
            if reference == case.deps.issuer_profile.signing_key_ref:
                raw = case.private.private_bytes(serialization.Encoding.Raw,
                    serialization.PrivateFormat.Raw, serialization.NoEncryption())
                value = SIGNING_KEY_PREFIX + base64.b64encode(raw).decode('ascii')
            else:
                assert reference == case.deps.issuer_profile.audit_mac_key_ref
                value = AUDIT_KEY_PREFIX + base64.b64encode(b'disposable-audit-fixture-32bytes!!').decode('ascii')
            case.events.append('resolve')
            return ResolveResult(True, reference, hash_reference(reference), ttl_remaining=30,
                                 session_id=requester_id, _secret_value=value)
    return CredentialFixture


@pytest.fixture
def case(tmp_path, monkeypatch):
    now = int(time.time())
    monkeypatch.setattr(fixture, 'NOW', now)
    monkeypatch.setattr(store_fixture, 'NOW', now)
    value = _fixture_inputs(tmp_path)
    monkeypatch.setattr(service, '_load_owner_config', lambda *a, **kw: value.owner)
    monkeypatch.setattr(service, 'grant_authority_owner_runtime_root', lambda *a: tmp_path/'grant')
    monkeypatch.setattr(service, 'RootAuthorizedSignerGrantRevocationOracle', FixtureOracle)
    monkeypatch.setattr(service, 'SystemdCredentialSecretResolver', _synthetic_custody(value))
    def authorize(**kwargs):
        value.events.append('authorize')
        value.active = True
        try:
            return kwargs['action']()
        finally:
            value.active = False
            value.events.append('fence-exit')
    monkeypatch.setattr(service, 'authorize_current_grant_authority_wsp71_use', authorize)
    monkeypatch.setattr(service, 'enforce_signer_process_isolation', lambda *a, **kw: SimpleNamespace(accepted=True))
    return value


def _request(case, nonce='grant-fixture-0001'):
    _, policy = service._current_inputs(case.repo, case.owner_path, case.deps)
    target = replace(fixture._target_request(), requested_operation=service.LOW_OPERATION)
    grant = fixture._grant(target, case.binding, nonce=nonce)
    return build_secret_grant_signing_request(grant, policy=policy, consensus_receipt_digest=None)


def _backend(case):
    return service._CurrentLowGrantBackend(case.repo, case.owner_path, case.deps)


def test_no_installed_dependencies_rejects_before_owner_or_socket(monkeypatch, tmp_path):
    def forbidden(*a, **kw):
        raise AssertionError('No installation means no owner or socket access')
    monkeypatch.setattr(service, '_load_owner_config', forbidden)
    monkeypatch.setattr(service, 'serve_reddog_isolated_signer_socket_bounded', forbidden)
    result = service.serve_grant_authority_once(repo_root=tmp_path, owner_config_path=tmp_path/'missing')
    assert not result.accepted and result.requests_handled == 0


def test_fresh_real_backend_and_durable_rate_per_request(case):
    backend = _backend(case)
    for nonce in ('one', 'two'):
        request = _request(case, nonce)
        response = backend.sign(request, fixture._peer())
        assert response.accepted, response.rejection_code
        assert Ed25519SignatureVerifier().verify(case.binding.issuer_public_key, request.signing_input, response.signature)
        assert response.audit_attestation_signature
    assert case.events.count('new-custody') == 2 and case.events.count('resolve') == 4
    assert not backend.sign(_request(case, 'three'), fixture._peer()).accepted
    assert case.events.count('authorize') == 3 and not case.active


@pytest.mark.parametrize('field,value', [('requested_operation','write_repo'), ('authority_tier','HIGH'),
    ('consensus_receipt_digest','sha256:'+'a'*64), ('elevated_consensus_proof',{})])
def test_non_low_outer_request_rejected_before_permission(case, field, value):
    response = _backend(case).sign(replace(_request(case), **{field:value}), fixture._peer())
    assert not response.accepted and case.events == []


def test_foreign_peer_and_malformed_grant_never_resolve(case):
    request = _request(case)
    assert not _backend(case).sign(request, fixture._peer('attacker')).accepted
    assert case.events == []
    assert not _backend(case).sign(replace(request, signing_input='bad'), fixture._peer()).accepted
    assert 'resolve' not in case.events


@pytest.mark.parametrize('stage', ['pre-bind', 'request', 'fence-exit'])
def test_permission_rejection_does_not_escape_as_success(case, monkeypatch, stage):
    def deny(**kwargs):
        if stage == 'fence-exit':
            case.active = True
            try:
                kwargs['action']()
            finally:
                case.active = False
        raise ValueError('synthetic expired/revoked admission')
    monkeypatch.setattr(service, 'authorize_current_grant_authority_wsp71_use', deny)
    if stage == 'pre-bind':
        monkeypatch.setattr(service, 'serve_reddog_isolated_signer_socket_bounded',
                            lambda **kw: pytest.fail('permission denied before socket'))
        result = service.serve_grant_authority_once(repo_root=case.repo, owner_config_path=case.owner_path,
                                                  dependencies=case.deps)
    else:
        result = _backend(case).sign(_request(case), fixture._peer())
    assert not result.accepted
    if stage != 'fence-exit':
        assert 'resolve' not in case.events


@pytest.mark.parametrize('field,value', [('allowed_operations',['write_repo']),
    ('allowed_authority_tiers',['HIGH']), ('consensus_required_tiers',['LOW']),
    ('grant_authority_key_epoch','changed'), ('grant_authority_signing_key_ref_hash','sha256:'+'e'*64),
    ('owner_config_id','sha256:'+'e'*64), ('replay_store_id','wrong')])
def test_scope_profile_owner_and_replay_substitution_reject(case, field, value):
    policy = dict(case.deps.owner_policy, **{field:value})
    changed = replace(case.deps, owner_policy=policy)
    with pytest.raises(ValueError):
        service._current_inputs(case.repo, case.owner_path, changed)
    assert case.events == []


@pytest.mark.parametrize('field,value', [('expected_uid',996), ('expected_gid',996),
    ('expected_requester','other'), ('credential_ids',frozenset({'grant-signing','other'}))])
def test_custody_scope_is_exact(case, field, value):
    changed = replace(case.deps, credential_binding=replace(case.deps.credential_binding, **{field:value}))
    with pytest.raises(ValueError, match='custody_scope'):
        service._current_inputs(case.repo, case.owner_path, changed)


def test_isolation_rejected_before_permission_or_serve(case, monkeypatch):
    monkeypatch.setattr(service, 'enforce_signer_process_isolation', lambda *a, **kw: SimpleNamespace(accepted=False))
    result = service.serve_grant_authority_once(repo_root=case.repo, owner_config_path=case.owner_path, dependencies=case.deps)
    assert not result.accepted and case.events == []


@pytest.mark.skipif(sys.platform != 'linux', reason='native Unix descriptor identity operations required')
def test_real_socket_exchange_through_composition_with_synthetic_custody(case, monkeypatch):
    class PeerFixture:
        def __init__(self, policy):
            assert policy.uid_to_principal == {998:'provider:grant-client'}
        def attest(self, connection):
            return fixture._peer()
    monkeypatch.setattr(service, 'KernelPeerCredentialAttestor', PeerFixture)
    ready, results = threading.Event(), {}
    thread = threading.Thread(target=lambda: results.update(result=service.serve_grant_authority_once(
        repo_root=case.repo, owner_config_path=case.owner_path, dependencies=case.deps,
        timeout_s=3, ready_callback=ready.set)), daemon=True)
    thread.start()
    assert ready.wait(5)
    client = build_reddog_isolated_signer_socket_client(repo_root=case.repo,
        socket_path=case.owner['independent_grant_authority']['authority_socket_path'], timeout_s=3)
    assert client.accepted
    request = _request(case)
    response = client.client.sign(request)
    thread.join(5)
    assert not thread.is_alive()
    assert response.accepted, response.rejection_code
    assert Ed25519SignatureVerifier().verify(case.binding.issuer_public_key, request.signing_input, response.signature)
    result = results['result']
    assert result.accepted and result.requests_handled == 1 and result.socket_removed
    assert case.events.count('authorize') == 2 and case.events.count('new-custody') == 1


def test_composition_has_no_cli_installer_or_large_function():
    source = Path(service.__file__).read_text(encoding='utf-8')
    assert len(source.splitlines()) <= 300 and 'def main(' not in source
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            assert node.end_lineno - node.lineno + 1 <= 60
