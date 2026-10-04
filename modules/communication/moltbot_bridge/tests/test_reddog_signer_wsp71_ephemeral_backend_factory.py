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
    store, profile, binding, request, grant, resolver = _real_factory_grant_case(tmp_path)
    verifier = Ed25519SignatureVerifier()
    keys = SimpleNamespace(resolve=lambda principal, provider: binding.issuer_public_key
                           if (principal, provider) == (binding.issuer_principal_id,
                                                       binding.issuer_principal_provider) else None)
    boundary = grant_fixture.SignerSecretAccessGrantBoundary(
        nonce_store=store,
        revocation_oracle=grant_fixture.AtomicSignerSecretGrantRevocationOracle(),
        clock=lambda: grant_fixture.NOW,
    )
    factory = Wsp71EphemeralSignerBackendFactory(profile, resolver)
    backend = grant_fixture.ResolvePerSignSignerBackend(binding, boundary, verifier, keys, factory)
    nonce_path = grant_fixture._store_config(tmp_path).nonce_path
    assert resolver.calls == []
    assert json.loads(nonce_path.read_text(encoding="utf-8"))["consumed"] == {}
    original_resolve, observed = resolver.resolve, []

    def resolve_after_durable_consumption(reference, requester_id=None):
        state = json.loads(nonce_path.read_text(encoding="utf-8"))
        assert len(state["consumed"]) == 1 and state["reservations"] == {}
        assert grant_fixture._store(tmp_path).consume_grant(grant) is False
        observed.append(reference)
        return original_resolve(reference, requester_id)

    monkeypatch.setattr(resolver, "resolve", resolve_after_durable_consumption)
    wire = {"schema_version": grant_fixture.SIGNER_SOCKET_REQUEST_SCHEMA_VERSION_V2,
            "request": request.to_dict(), "secret_access_grant": grant}
    response = json.loads(grant_fixture.handle_reddog_isolated_signer_socket_request(
        json.dumps(wire).encode("utf-8"), peer=grant_fixture._peer(), backend=backend,
    ))
    assert response["accepted"] is True, (response["rejection_code"], len(observed), len(resolver.calls))
    assert observed == [profile.signing_key_ref, profile.audit_mac_key_ref]
    assert resolver.calls == [(reference, profile.signer_agent_id) for reference in observed]
    assert verifier.verify(profile.expected_public_key, request.signing_input, response["signature"])
    assert not verifier.verify(profile.expected_public_key, request.signing_input + " ", response["signature"])

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
