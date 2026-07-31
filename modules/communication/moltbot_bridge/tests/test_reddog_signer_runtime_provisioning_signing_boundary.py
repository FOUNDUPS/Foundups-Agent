"""Security regressions for atomic provisioning signer selection."""

from __future__ import annotations

import copy
import pickle
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_signed_runtime_artifact_manifest import (
    RuntimeArtifactManifestSigningContext,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    SigningResponse,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_atomic_provisioning import (
    SignerRuntimeAtomicProvisioningContext,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_atomic_provisioning_contract import (
    create_signer_runtime_atomic_provisioning_context,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signer_runtime_atomic_provisioning import (
    _context,
    _provision,
)


def test_forged_signer_and_permissive_verifier_cannot_activate(
    tmp_path: Path,
) -> None:
    harness, anchor, _ = _context(tmp_path)

    class AllowAllVerifier:
        def verify(self, *_args) -> bool:
            return True

    class ForgedSigner:
        def sign(self, _request) -> SigningResponse:
            return SigningResponse(
                accepted=True,
                signature="attacker-signature",
                signer_public_key=harness.reddog_public_key,
                key_fingerprint="attacker-fingerprint",
                key_epoch="attacker-epoch",
                audit_mac="sha256:" + "a" * 64,
                audit_attestation_signature="attacker-attestation",
                boundary_attested=True,
                requester_identity_attested=True,
                signer_loads_no_untrusted_code=True,
                no_secret_material_returned=True,
            )

    attacker = RuntimeArtifactManifestSigningContext(
        signer=ForgedSigner(),
        signature_verifier=AllowAllVerifier(),
        authority=harness.authority,
        authority_boundary=harness.authority_boundary,
        authority_tier="HIGH",
    )
    context = create_signer_runtime_atomic_provisioning_context(
        manifest_signing=attacker,
        generation_anchor=anchor,
    )

    result = _provision(context)

    assert result.accepted is False
    assert anchor.load() is None
    assert not list(harness.manifest_directory.glob("*.json"))


def test_atomic_signing_capability_is_process_local_and_uncopyable(
    tmp_path: Path,
) -> None:
    _, anchor, context = _context(tmp_path)

    for copier in (copy.copy, copy.deepcopy, pickle.dumps):
        with pytest.raises(TypeError):
            copier(context.signing_authority)
    forged = SignerRuntimeAtomicProvisioningContext(
        signing_authority=object(),
        signing_authority_boundary=object(),  # type: ignore[arg-type]
        generation_anchor=anchor,
    )

    result = _provision(forged)

    assert result.accepted is False
    assert anchor.load() is None


def test_signing_boundary_exposes_no_verifier_or_registry_mutation_surface() -> None:
    import modules.communication.moltbot_bridge.src.reddog_signer_runtime_provisioning_signing_boundary as target

    assert "Ed25519SignatureVerifier" not in target.__dict__
    assert "_binding" not in target.__dict__
    assert "_records" not in target.__dict__
    assert "_contexts" not in target.__dict__
