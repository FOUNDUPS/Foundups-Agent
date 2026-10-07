from __future__ import annotations
import base64
import hashlib
import json
from dataclasses import asdict, replace
from types import SimpleNamespace
import pytest
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import ( Ed25519SignatureVerifier, encode_ed25519_public_key, encode_ed25519_signature, )
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import ( public_key_fingerprint, )
from modules.communication.moltbot_bridge.src.reddog_signer_key_provider_dryrun import ( AUDIT_KEY_PREFIX, SIGNING_KEY_PREFIX, SignerKeyProviderProfile, )
from modules.communication.moltbot_bridge.src.reddog_signer_wsp71_ephemeral_backend_factory import ( Wsp71EphemeralSignerBackendFactory, )
from modules.infrastructure.secrets_mcp.src.vault_resolver import ( MockVaultResolver, ResolveErrorCode, ResolveResult, hash_reference, )
from modules.communication.moltbot_bridge.tests import ( test_reddog_signer_resolve_per_sign_backend as grant_fixture, test_reddog_ed25519_signer_backend as signer_fixture, )

pytest.importorskip("cryptography")

class _Resolver:
    def __init__(self, values: dict[str, str]) -> None:
        self.values = values
        self.calls: list[tuple[str, str | None]] = []

    def resolve(
        self, reference: str, requester_id: str | None = None
    ) -> ResolveResult:
        self.calls.append((reference, requester_id))
        return ResolveResult(
            success=True,
            reference=reference,
            reference_hash=hash_reference(reference),
            ttl_remaining=60,
            session_id="ephemeral-test",
            _secret_value=self.values[reference],
        )

def _key_material() -> tuple[str, str, str]:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key = Ed25519PrivateKey.generate()
    private_bytes = key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_bytes = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return (
        SIGNING_KEY_PREFIX + base64.b64encode(private_bytes).decode("ascii"),
        encode_ed25519_public_key(public_bytes),
        AUDIT_KEY_PREFIX
        + base64.b64encode(b"0123456789abcdef0123456789abcdef").decode("ascii"),
    )

def test_factory_resolves_both_keys_afresh_for_every_call() -> None:
    signing_secret, public_key, audit_secret = _key_material()
    signing_ref = "op://Foundups/reddog-signing/private"
    audit_ref = "op://Foundups/reddog-signing/audit"
    resolver = _Resolver({signing_ref: signing_secret, audit_ref: audit_secret})
    profile = SignerKeyProviderProfile(
        signer_profile_id="reddog-work-authority",
        signer_agent_id="signer:reddog",
        signing_key_ref=signing_ref,
        audit_mac_key_ref=audit_ref,
        expected_public_key=public_key,
        expected_key_fingerprint=public_key_fingerprint(public_key),
        expected_key_epoch="epoch-1",
        permission_snapshot_digest="sha256:" + "3" * 64,
        ttl_seconds=60,
    )
    factory = Wsp71EphemeralSignerBackendFactory(profile, resolver)

    first = factory()
    second = factory()

    assert first.ok is True and second.ok is True
    assert first.backend is not second.backend
    assert resolver.calls == [
        (signing_ref, "signer:reddog"),
        (audit_ref, "signer:reddog"),
        (signing_ref, "signer:reddog"),
        (audit_ref, "signer:reddog"),
    ]
    assert first.secret_values_returned is False
    assert second.secret_values_returned is False

def _real_factory_grant_case(tmp_path):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    store = grant_fixture._store(tmp_path)
    signing_secret, public_key, audit_secret = _key_material()
    issuer_secret, issuer_public, _ = _key_material()
    signing_ref, audit_ref = "op://Foundups/target/private", "op://Foundups/target/audit"
    profile = SignerKeyProviderProfile(
        signer_profile_id="reddog-work-authority", signer_agent_id="signer:reddog",
        signing_key_ref=signing_ref, audit_mac_key_ref=audit_ref,
        expected_public_key=public_key,
        expected_key_fingerprint=public_key_fingerprint(public_key),
        expected_key_epoch="epoch-1", permission_snapshot_digest="sha256:" + "3" * 64,
        ttl_seconds=60,
    )
    binding = replace(
        grant_fixture._binding(store), issuer_public_key=issuer_public,
        signer_public_key=public_key, signer_key_fingerprint=profile.expected_key_fingerprint,
        signing_key_ref_hash="sha256:" + hashlib.sha256(signing_ref.encode("utf-8")).hexdigest(),
        audit_mac_key_ref_hash="sha256:" + hashlib.sha256(audit_ref.encode("utf-8")).hexdigest(),
    )
    operation = "signed_0102_readonly_review:foundup_module"
    signing_input = 'reddog-workauth.v1.' + json.dumps(
        {"authority_tier": "LOW", "requested_operation": operation,
         "work_order_id": "synthetic-factory-join"}, sort_keys=True, separators=(",", ":"))
    request = signer_fixture._request(
        public_key, signing_input=signing_input,
        payload_digest=signer_fixture._request_digest(signing_input),
        requester_principal_id=binding.issuer_principal_id, requested_operation=operation,
        authority_tier="LOW", consensus_receipt_digest=None,
    )
    grant = grant_fixture._grant(request, store, **asdict(binding))
    issuer = Ed25519PrivateKey.from_private_bytes(
        base64.b64decode(issuer_secret[len(SIGNING_KEY_PREFIX):])
    )
    grant["signature"] = encode_ed25519_signature(issuer.sign(
        grant_fixture.canonical_signer_secret_access_grant_input(grant).encode("ascii")
    ))
    resolver = _Resolver({signing_ref: signing_secret, audit_ref: audit_secret})
    return store, profile, binding, request, grant, resolver

def test_real_factory_socket_grant_consumes_before_both_resolutions(tmp_path, monkeypatch):
    """Real owner/factory/router; synthetic keys, peer/config attachment and transport."""
    from modules.communication.moltbot_bridge.tests import test_reddog_signer_socket_service_runtime_wiring as admitted

    case = admitted._admission_case(tmp_path, monkeypatch)
    store, request, grant, resolver = case.admission.replay_store, case.request, case.grant, case.resolver
    profile = admitted.grant_runtime._profiles(case.owner.config)[0][0]
    verifier = Ed25519SignatureVerifier()
    nonce_path = store._config.nonce_path
    assert resolver.calls == []
    assert json.loads(nonce_path.read_text(encoding="utf-8"))["consumed"] == {}
    original_resolve, observed = resolver.resolve, []

    def resolve_after_durable_consumption(reference, requester_id=None):
        state = json.loads(nonce_path.read_text(encoding="utf-8"))
        assert len(state["consumed"]) == 1 and state["reservations"] == {}
        reopened = grant_fixture.DurableSignerSecretGrantNonceStore(
            store._config, integrity_key=grant_fixture.INTEGRITY_KEY, clock=lambda: grant_fixture.NOW)
        assert reopened.consume_grant(grant) is False
        observed.append(reference)
        return original_resolve(reference, requester_id)

    monkeypatch.setattr(resolver, "resolve", resolve_after_durable_consumption)

    def serve(**kwargs):
        backend = kwargs["backend"]
        assert type(backend.backend_factory) is Wsp71EphemeralSignerBackendFactory
        response = admitted._admission_wire(case, backend, grant)
        assert response["accepted"] is True, (response["rejection_code"], len(observed), len(resolver.calls))
        assert observed == [profile.signing_key_ref, profile.audit_mac_key_ref]
        assert resolver.calls == [(reference, profile.signer_agent_id) for reference in observed]
        assert verifier.verify(profile.expected_public_key, request.signing_input, response["signature"])
        assert not verifier.verify(profile.expected_public_key, request.signing_input + " ", response["signature"])
        assert admitted._admission_wire(case, backend, grant)["accepted"] is False
        assert len(observed) == len(resolver.calls) == 2
        return admitted.CapturingBoundedService()(**kwargs)

    result = admitted.run_reddog_signer_socket_service_runtime_wiring(
        case.config, resolver, serve_bounded=serve, secret_grant_admission=case.admission)
    assert result.accepted is True, result.rejection_reasons
    assert case.active is False

@pytest.mark.parametrize(("case", "expected"), [
    ("wrong_reference", "FAIL_PROVIDER_REFERENCE_INVALID"),
    ("wrong_audit_hash", "FAIL_PROVIDER_REFERENCE_INVALID"),
    ("swapped_metadata", "FAIL_PROVIDER_REFERENCE_INVALID"),
    ("mock", "FAIL_PROVIDER_MOCK_IN_PRODUCTION"),
    ("denied", "FAIL_PROVIDER_RESOLVER_UNAVAILABLE"),
    ("expired", "FAIL_PROVIDER_TTL_EXPIRED"),
])
def test_factory_rejects_untrusted_resolution_metadata(tmp_path, monkeypatch, case, expected):
    _, profile, _, _, _, resolver = _real_factory_grant_case(tmp_path)
    original = resolver.resolve

    def altered(reference, requester_id=None):
        value = original(reference, requester_id)
        if case == "wrong_reference":
            return replace(value, reference=profile.audit_mac_key_ref)
        if case == "wrong_audit_hash" and reference == profile.audit_mac_key_ref:
            return replace(value, reference_hash="sha256:" + "0" * 64)
        if case == "swapped_metadata":
            return replace(value, reference=profile.audit_mac_key_ref,
                           reference_hash=hash_reference(profile.audit_mac_key_ref))
        if case == "denied":
            return replace(value, success=False, error_code=ResolveErrorCode.SESSION_INVALID)
        return replace(value, ttl_remaining=0) if case == "expired" else value

    monkeypatch.setattr(resolver, "resolve", altered)
    if case == "mock":
        resolver = MockVaultResolver()
        monkeypatch.setattr(resolver, "resolve", lambda *a, **k: pytest.fail("mock resolution attempted"))
    monkeypatch.setattr(ResolveResult, "get_value", lambda self: pytest.fail("invalid secret accessed"))
    result = Wsp71EphemeralSignerBackendFactory(profile, resolver)()
    assert result.ok is False
    assert result.rejection_code == expected
    assert result.backend is None and result.secret_values_returned is False


def _factory_handshake_case(tmp_path):
    import time
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from modules.communication.moltbot_bridge.tests import test_reddog_signer_mutual_peer_handshake as handshake

    signing_secret, public_key, audit_secret = _key_material()
    private = Ed25519PrivateKey.from_private_bytes(
        base64.b64decode(signing_secret[len(SIGNING_KEY_PREFIX):]))
    signing_ref, audit_ref = "op://Foundups/handshake/private", "op://Foundups/handshake/audit"
    resolver = _Resolver({signing_ref: signing_secret, audit_ref: audit_secret})
    profile = SignerKeyProviderProfile(
        signer_profile_id="reddog-work-authority", signer_agent_id="signer:reddog",
        signing_key_ref=signing_ref, audit_mac_key_ref=audit_ref,
        expected_public_key=public_key,
        expected_key_fingerprint=public_key_fingerprint(public_key),
        expected_key_epoch="epoch-1", permission_snapshot_digest="sha256:" + "3" * 64,
        ttl_seconds=60,
    )
    original = handshake._binding()
    binding = replace(original, socket_path=str(tmp_path / "unused.sock"),
                      signer_profiles=(replace(original.signer_profiles[0],
                                               signer_public_key=public_key),))
    now = int(time.time())
    request = handshake._request(private, now_epoch=now, socket_path=binding.socket_path)
    direct = replace(handshake._backend(private), signer_peer_instance_binding=binding,
                     proposal_clock=lambda: int(time.time()))
    return SimpleNamespace(profile=profile, resolver=resolver, binding=binding,
                           request=request, direct=direct, peer=handshake._peer(),
                           handshake=handshake, now=now)


def test_direct_bound_handshake_control_is_valid(tmp_path):
    case = _factory_handshake_case(tmp_path)
    response = case.direct.sign(case.request, case.peer)
    assert response.accepted is True
    assert case.handshake.verify_signer_peer_handshake_response(
        case.request, response, now_epoch=case.now).accepted is True
    assert Ed25519SignatureVerifier().verify(
        case.profile.expected_public_key, case.request.signing_input, response.signature)
    assert case.resolver.calls == []


def test_unbound_factory_preserves_handshake_rejection(tmp_path):
    case = _factory_handshake_case(tmp_path)
    factory = Wsp71EphemeralSignerBackendFactory(case.profile, case.resolver)
    assert case.resolver.calls == []
    result = factory()
    assert result.ok is True and result.backend is not None
    assert result.backend.signer_peer_instance_binding is None
    response = result.backend.sign(case.request, case.peer)
    assert response.accepted is False and not response.signature
    assert response.rejection_code == case.handshake.REJECT_ED25519_SIGNER_REQUEST_INVALID
    assert case.resolver.calls == [(ref, case.profile.signer_agent_id) for ref in
                                   (case.profile.signing_key_ref, case.profile.audit_mac_key_ref)]


def test_bound_factory_handshake_verifies_for_each_fresh_backend(tmp_path):
    case = _factory_handshake_case(tmp_path)
    factory = Wsp71EphemeralSignerBackendFactory(
        case.profile, case.resolver, signer_peer_instance_binding=case.binding)
    assert case.resolver.calls == []
    previous = None
    for attempt in (1, 2):
        result = factory()
        assert result.ok is True and result.backend is not None
        assert result.backend is not previous
        assert result.backend.signer_peer_instance_binding == case.binding
        response = result.backend.sign(case.request, case.peer)
        assert response.accepted is True
        assert case.handshake.verify_signer_peer_handshake_response(
            case.request, response, now_epoch=case.now).accepted is True
        verifier = Ed25519SignatureVerifier()
        assert verifier.verify(case.profile.expected_public_key,
                               case.request.signing_input, response.signature)
        assert not verifier.verify(case.profile.expected_public_key,
                                   case.request.signing_input + " ", response.signature)
        assert case.resolver.calls == [(ref, case.profile.signer_agent_id) for ref in
                                       (case.profile.signing_key_ref,
                                        case.profile.audit_mac_key_ref)] * attempt
        previous = result.backend


@pytest.mark.parametrize("mismatch", ["session", "generation", "profile"])
def test_factory_handshake_rejects_different_instance(tmp_path, mismatch):
    case = _factory_handshake_case(tmp_path)
    assert case.direct.sign(case.request, case.peer).accepted is True
    changes = {
        "session": {"session_id": "different-session"},
        "generation": {"artifact_generation_digest": "sha256:" + "9" * 64},
        "profile": {"signer_profiles": (replace(case.binding.signer_profiles[0],
                                               signer_profile_id="different-profile"),)},
    }
    factory = Wsp71EphemeralSignerBackendFactory(
        case.profile, case.resolver,
        signer_peer_instance_binding=replace(case.binding, **changes[mismatch]))
    assert case.resolver.calls == []
    result = factory()
    assert result.ok is True and result.backend is not None
    response = result.backend.sign(case.request, case.peer)
    assert response.accepted is False and not response.signature
    assert response.rejection_code == case.handshake.REJECT_ED25519_SIGNER_REQUEST_INVALID
    assert case.resolver.calls == [(ref, case.profile.signer_agent_id) for ref in
                                   (case.profile.signing_key_ref, case.profile.audit_mac_key_ref)]


# Component controls use a synthetic lease scope; they do not prove native grants.
def _proposal_factory_case(tmp_path):
    from modules.communication.moltbot_bridge.tests import test_reddog_architect_proposal_signer_policy_runtime as proposal
    from modules.communication.moltbot_bridge.src import reddog_signer_socket_service_runtime_wiring as wiring
    private, principal = proposal._private_key(), proposal._private_key()
    public = proposal._public_text(private)
    repo = tmp_path / "repo"
    repo.mkdir()
    policy = proposal.ArchitectProposalSignerPolicy(proposal._payload(public))
    config = proposal._runtime_proposal_config(
        repo=repo, runtime=tmp_path / "runtime", signer_runtime=tmp_path / "signer",
        policy=policy, principal_private=principal, reddog_private=private,
    )
    config = replace(config, provider_mode=proposal.PROVIDER_MODE_WSP71_PERMISSIONED,
                     allow_test_only_key_material=False)
    digest = wiring.architect_proposal_security_context_digest(config)
    authorization = proposal._policy_authorization(
        policy, principal_private=principal, public_key=public,
        signer_runtime_root=config.signer_runtime_root, security_context_digest=digest,
    )
    config = replace(config, proposal_policy_authorization=authorization,
                     proposal_security_context_digest=digest)
    real_resolver, calls = proposal._Resolver(private), []
    def resolve(*args, **kwargs):
        calls.append(args[0])
        return real_resolver.resolve(*args, **kwargs)
    resolver = SimpleNamespace(resolve=resolve)
    owner = SimpleNamespace(resolver=proposal._PrincipalKeyResolver(proposal._public_text(principal)))
    high_water = proposal._SqliteProposalReplayHighWaterStore(tmp_path / "high-water" / "store.sqlite3")
    factory = Wsp71EphemeralSignerBackendFactory(
        config.key_provider_profiles[0], resolver,
        owner_context=(config, None, grant_fixture._binding()),
        proposal_replay_high_water_store=high_water,
    )
    return SimpleNamespace(factory=factory, config=config, owner=owner, calls=calls,
                           proposal=proposal, policy=policy, private=private)


def _call_proposal_component(case, action=None):
    from modules.communication.moltbot_bridge.src import reddog_signer_proposal_activation as module
    scope = module._ProposalLeaseScope(case.factory, case.config, case.owner)
    token = module._LEASED_PROPOSAL_OWNER.set(scope)
    try:
        with case.factory._activation_lock:
            result = case.factory()
            return action(result) if action is not None else result
    finally:
        scope.active = False
        module._LEASED_PROPOSAL_OWNER.reset(token)


def test_proposal_factory_activation_survives_fresh_resolution_only_in_same_factory(tmp_path):
    case = _proposal_factory_case(tmp_path)
    assert case.calls == [] and case.factory._activation_digest is None
    first = _call_proposal_component(case)
    assert first.ok and first.backend is not None
    second = _call_proposal_component(case)
    assert second.ok and second.backend is not first.backend
    assert len(case.calls) == 4 and case.factory._activation_digest is not None
    request, peer = case.proposal._signing_request(case.policy.expected_payload), case.proposal._peer()
    signed = _call_proposal_component(case, lambda result: result.backend.sign(request, peer))
    assert signed.accepted, signed.rejection_code
    assert Ed25519SignatureVerifier().verify(
        request.signer_public_key, request.signing_input, signed.signature)
    replay = _call_proposal_component(case, lambda result: result.backend.sign(request, peer))
    assert not replay.accepted and not replay.signature
    case.factory = replace(case.factory)
    assert case.factory._activation_digest is None
    with pytest.raises(ValueError, match="activation_rejected"):
        _call_proposal_component(case)


@pytest.mark.parametrize("control", ["no-lease", "principal", "store", "commit", "expired"])
def test_proposal_factory_activation_failure_has_no_retained_capability(tmp_path, monkeypatch, control):
    from modules.communication.moltbot_bridge.src import reddog_signer_socket_service_runtime_wiring as wiring
    from modules.communication.moltbot_bridge.src import reddog_signer_proposal_activation as module
    case = _proposal_factory_case(tmp_path)
    if control == "principal":
        case.owner.resolver = SimpleNamespace(resolve=lambda *args: None)
    elif control == "store":
        case.factory = replace(case.factory, proposal_replay_high_water_store=None)
    elif control == "commit":
        monkeypatch.setattr(wiring, "_commit_policy_authorization", lambda *args: False)
    elif control == "expired":
        monkeypatch.setattr(module, "time", SimpleNamespace(time=lambda: case.config.proposal_policy_authorization.expires_at + 1))
    with pytest.raises((TypeError, ValueError)):
        case.factory() if control == "no-lease" else _call_proposal_component(case)
    assert case.factory._activation_digest is None
    assert len(case.calls) == (2 if control == "commit" else 0)


@pytest.mark.parametrize("control", ["copied-context", "expiry-during-commit"])
def test_proposal_activation_review_regressions(tmp_path, monkeypatch, control):
    from contextvars import copy_context
    from modules.communication.moltbot_bridge.src import reddog_signer_socket_service_runtime_wiring as wiring
    from modules.communication.moltbot_bridge.src import reddog_signer_proposal_activation as module
    case = _proposal_factory_case(tmp_path)
    if control == "copied-context":
        contexts, original = [], case.factory.resolver.resolve
        def capture(*args, **kwargs):
            contexts.append(copy_context())
            return original(*args, **kwargs)
        case.factory.resolver.resolve = capture
        assert _call_proposal_component(case).ok
        calls = len(case.calls)
        with pytest.raises(ValueError, match="lease"):
            contexts[0].run(case.factory)
        assert len(case.calls) == calls
    else:
        original = wiring._commit_policy_authorization
        def expire(*args):
            result = original(*args)
            monkeypatch.setattr(module, "time", SimpleNamespace(time=lambda: case.config.proposal_policy_authorization.expires_at + 1))
            return result
        monkeypatch.setattr(wiring, "_commit_policy_authorization", expire)
        with pytest.raises(ValueError):
            _call_proposal_component(case)



def test_proposal_factory_handshake_then_proposal_in_one_activation(tmp_path):
    import time
    from modules.communication.moltbot_bridge.tests import test_reddog_signer_mutual_peer_handshake as handshake
    case = _proposal_factory_case(tmp_path)
    old = handshake._binding()
    profile = case.factory.profile
    binding = replace(old, socket_path=str(tmp_path / "unused.sock"),
                      signer_profiles=(replace(old.signer_profiles[0], signer_public_key=profile.expected_public_key,
                                               key_epoch=profile.expected_key_epoch),))
    case.factory = replace(case.factory, signer_peer_instance_binding=binding)
    now = int(time.time())
    request = handshake._request(case.private, now_epoch=now, socket_path=binding.socket_path)
    response = _call_proposal_component(case, lambda result: result.backend.sign(request, handshake._peer()))
    assert response.accepted, response.rejection_code
    assert handshake.verify_signer_peer_handshake_response(request, response, now_epoch=now).accepted
    proposal = case.proposal._signing_request(case.policy.expected_payload)
    response = _call_proposal_component(case, lambda result: result.backend.sign(proposal, case.proposal._peer()))
    assert response.accepted, response.rejection_code
    assert len(case.calls) == 4


def test_proposal_factory_copied_live_scope_rejects_another_thread(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from contextvars import copy_context
    case = _proposal_factory_case(tmp_path)
    def other_thread(result):
        context, calls = copy_context(), len(case.calls)
        with ThreadPoolExecutor(max_workers=1) as executor:
            with pytest.raises(ValueError, match="lease"):
                executor.submit(context.run, case.factory).result(timeout=5)
        assert len(case.calls) == calls
    _call_proposal_component(case, other_thread)


def test_proposal_factory_expiry_during_request_reserve_prevents_signature(tmp_path, monkeypatch):
    from modules.communication.moltbot_bridge.src import reddog_signer_proposal_activation as module
    case = _proposal_factory_case(tmp_path)
    request = case.proposal._signing_request(case.policy.expected_payload)
    signed = []
    def act(result):
        backend = result.backend
        real_key = backend.private_key.key
        key = SimpleNamespace(public_key=real_key.public_key,
                              sign=lambda data: signed.append(True) or real_key.sign(data))
        backend = replace(backend, private_key=replace(backend.private_key, key=key))
        original = backend.proposal_nonce_store.reserve
        def delayed(*args, **kwargs):
            reservation = original(*args, **kwargs)
            monkeypatch.setattr(module, "time", SimpleNamespace(time=lambda: case.config.proposal_policy_authorization.expires_at + 1))
            return reservation
        monkeypatch.setattr(backend.proposal_nonce_store, "reserve", delayed)
        return backend.sign(request, case.proposal._peer())
    response = _call_proposal_component(case, act)
    assert not response.accepted and not response.signature and signed == []



@pytest.mark.parametrize("phase", ["before-sign", "after-sign"])
def test_proposal_key_expiry_in_principal_io_never_returns_signature(tmp_path, monkeypatch, phase):
    from modules.communication.moltbot_bridge.src import reddog_signer_proposal_activation as module
    case = _proposal_factory_case(tmp_path)
    calls, signed = [], []
    def act(result):
        expiry = case.config.proposal_policy_authorization.expires_at
        clock = [expiry - 1]
        monkeypatch.setattr(module, "time", SimpleNamespace(time=lambda: clock[0]))
        original = case.owner.resolver.resolve
        def delayed(*args):
            value = original(*args)
            calls.append(True)
            if len(calls) == (1 if phase == "before-sign" else 2):
                clock[0] = expiry
            return value
        monkeypatch.setattr(case.owner.resolver, "resolve", delayed)
        real_key = result.backend.private_key.key
        key = replace(result.backend.private_key, key=SimpleNamespace(
            sign=lambda data: signed.append(True) or real_key.sign(data)))
        with pytest.raises(ValueError):
            key.sign(b"synthetic-expiry-control")
    _call_proposal_component(case, act)
    assert len(signed) == (0 if phase == "before-sign" else 1)



def test_proposal_authority_check_uses_one_monotonic_clock(tmp_path, monkeypatch):
    from modules.communication.moltbot_bridge.src import reddog_signer_proposal_activation as module
    case = _proposal_factory_case(tmp_path)
    def act(result):
        key = result.backend.private_key
        # Isolate the four samples within one authority check.
        key.scope.last_epoch = None
        issued = case.config.proposal_policy_authorization.issued_at
        samples = iter([issued - 1, issued + 1, issued + 1, issued])
        monkeypatch.setattr(module, "time", SimpleNamespace(time=lambda: next(samples, issued)))
        with pytest.raises(ValueError, match="clock_reversed"):
            key._require_authority()
    _call_proposal_component(case, act)



def _admitted_proposal_case(tmp_path, monkeypatch):
    from modules.communication.moltbot_bridge.tests import test_reddog_signer_socket_service_runtime_wiring as admitted
    from modules.communication.moltbot_bridge.tests import test_reddog_architect_proposal_signer_policy_runtime as proposal
    owner_fixture = admitted.owner_fixture
    keypair, write_config = owner_fixture._keypair, owner_fixture._write_fixture_config
    keys, captured = {}, {}
    def remember_keys():
        private, public = keypair()
        keys[public] = private
        return private, public
    def proposal_config(roots, owner_policy, target_public, signing_ref, audit_ref):
        owner_policy["allowed_operations"] = sorted(set(owner_policy["allowed_operations"] + [proposal.PROPOSAL_AUTHENTICITY_SIGNING_OPERATION, "signer_socket_peer_handshake"]))
        owner_policy["allowed_authority_tiers"] = ["HIGH", "LOW", "ULTRA"]
        owner_policy["consensus_required_tiers"] = ["HIGH", "ULTRA"]
        raw, path, _ = write_config(roots, owner_policy, target_public, signing_ref, audit_ref)
        raw, policy = _admitted_proposal_config(raw, roots, owner_policy, target_public,
                                              keys[owner_policy["grant_authority_public_key"]], proposal, admitted)
        path.write_text(json.dumps(raw, sort_keys=True), encoding="ascii")
        captured["policy"] = policy
        return raw, path, owner_fixture._canonical_digest(raw)
    monkeypatch.setattr(owner_fixture, "_keypair", remember_keys)
    monkeypatch.setattr(owner_fixture, "_write_fixture_config", proposal_config)
    case = admitted._admission_case(tmp_path, monkeypatch)
    from modules.communication.moltbot_bridge.src import reddog_signer_key_provider_dryrun as provider
    nonce_store = provider.AtomicProposalAuthenticityNonceStore
    # This constructor captures time.time at import; use the fixture's clock too.
    monkeypatch.setattr(provider, "AtomicProposalAuthenticityNonceStore",
                        lambda *args, **kwargs: nonce_store(*args, **kwargs, clock=lambda: grant_fixture.NOW))
    case.proposal_policy = captured["policy"]
    case.proposal_store = proposal._SqliteProposalReplayHighWaterStore(tmp_path / "proposal-high-water" / "authority.sqlite3")
    case.proposal_fixture = proposal
    case.admitted_fixture = admitted
    return case


def _admitted_proposal_config(raw, roots, owner_policy, target_public, principal_private, proposal, admitted, key_epoch="target-epoch-1"):
    payload = proposal._payload(target_public, requester_principal_id="principal:grant-admin", key_epoch=key_epoch)
    policy = proposal.ArchitectProposalSignerPolicy(payload)
    raw.update(proposal_authority_policy=asdict(policy), proposal_policy_authorization=None,
               proposal_nonce_store_path=str(roots["signer"] / "architect_proposal_nonce_store.json"),
               proposal_replay_high_water_store_id=proposal.HIGH_WATER_STORE_ID,
               proposal_replay_high_water_durability_receipt_id=proposal.HIGH_WATER_DURABILITY_RECEIPT_ID,
               proposal_security_context_digest=None)
    values = {key: value for key, value in raw.items()
              if key not in {"schema_version", "owner_e0_authority_binding_digest"}}
    config = admitted.grant_runtime.SignerSocketServiceRuntimeWiringConfig(repo_root=roots["repo"], **values)
    digest = admitted.grant_runtime.architect_proposal_security_context_digest(config)
    profile = proposal._profile(target_public, principal_public_key=owner_policy["grant_authority_public_key"])
    profile.update(principal_id="principal:grant-admin", key_epoch=key_epoch)
    authorization = proposal._policy_authorization(
        policy, principal_private=principal_private, public_key=target_public,
        signer_runtime_root=roots["signer"], security_context_digest=digest, profile=profile)
    raw.update(proposal_policy_authorization=authorization.to_dict(), proposal_security_context_digest=digest)
    return raw, policy


def _admitted_proposal_grant(case, request, nonce):
    admitted = case.admitted_fixture
    binding = admitted.resolve_secret_grant_target_binding(case.owner.policy, case.admission.replay_store)
    grant = grant_fixture._grant(request, case.admission.replay_store, nonce=nonce, **asdict(binding))
    grant["signature"] = encode_ed25519_signature(case.values["grant_private"].sign(
        grant_fixture.canonical_signer_secret_access_grant_input(grant).encode("ascii")))
    case.grant = grant
    return grant


def test_admitted_proposal_runtime_handshake_then_proposal(tmp_path, monkeypatch):
    # Real owner lease, root-protected-use router, grants and crypto. Existing fixture
    # supplies synthetic selection/OS transport and pre-issued test grants.
    from modules.communication.moltbot_bridge.tests import test_reddog_signer_mutual_peer_handshake as handshake
    case = _admitted_proposal_case(tmp_path, monkeypatch)
    admitted = case.admitted_fixture
    observed = []
    original_factory_call = Wsp71EphemeralSignerBackendFactory.__call__
    def frozen_factory(factory):
        result = original_factory_call(factory)
        if result.backend is not None:
            result = replace(result, backend=replace(result.backend, proposal_clock=lambda: grant_fixture.NOW))
        return result
    monkeypatch.setattr(Wsp71EphemeralSignerBackendFactory, "__call__", frozen_factory)
    def execute(**kwargs):
        assert case.active is False and case.resolver.calls == []
        backend = kwargs["backend"]
        binding = case.config.signer_peer_instance_binding
        case.request = handshake._request(case.values["target_private"],
            run_packet_id=binding.run_packet_id, manifest_id=binding.manifest_id,
            artifact_generation_digest=binding.artifact_generation_digest,
            config_digest=binding.config_digest, session_id=binding.session_id,
            socket_path=binding.socket_path, key_epoch="target-epoch-1",
            requester_principal_id="principal:grant-admin", now_epoch=grant_fixture.NOW)
        response = admitted._admission_wire(case, backend, _admitted_proposal_grant(case, case.request, "proposal-handshake"))
        assert response["accepted"], response["rejection_code"]
        assert len(case.resolver.calls) == 2
        case.request = case.proposal_fixture._signing_request(case.proposal_policy.expected_payload)
        grant = _admitted_proposal_grant(case, case.request, "proposal-1")
        response = admitted._admission_wire(case, backend, grant)
        assert response["accepted"], response["rejection_code"]
        assert Ed25519SignatureVerifier().verify(case.request.signer_public_key, case.request.signing_input, response["signature"])
        assert len(case.resolver.calls) == 4
        assert not admitted._admission_wire(case, backend, grant)["accepted"]
        assert len(case.resolver.calls) == 4
        replay = _admitted_proposal_grant(case, case.request, "proposal-2")
        assert not admitted._admission_wire(case, backend, replay)["accepted"]
        assert len(case.resolver.calls) == 6
        return admitted.CapturingBoundedService()(**kwargs)
    def serve(**kwargs):
        try:
            return execute(**kwargs)
        except Exception as exc:
            observed.append((type(exc).__name__, str(exc)[:180]))
            raise
    result = admitted.run_reddog_signer_socket_service_runtime_wiring(
        case.config, case.resolver, serve_bounded=serve, secret_grant_admission=case.admission,
        proposal_replay_high_water_store=case.proposal_store,
        principal_key_resolver=case.owner.resolver)
    assert result.accepted, json.dumps([result.rejection_reasons, observed, case.events])
    assert case.active is False
