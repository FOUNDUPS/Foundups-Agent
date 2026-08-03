from __future__ import annotations

import base64

import pytest

from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    encode_ed25519_public_key,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    public_key_fingerprint,
)
from modules.communication.moltbot_bridge.src.reddog_signer_key_provider_dryrun import (
    AUDIT_KEY_PREFIX,
    SIGNING_KEY_PREFIX,
    SignerKeyProviderProfile,
)
from modules.communication.moltbot_bridge.src.reddog_signer_wsp71_ephemeral_backend_factory import (
    Wsp71EphemeralSignerBackendFactory,
)
from modules.infrastructure.secrets_mcp.src.vault_resolver import (
    ResolveResult,
    hash_reference,
)

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
