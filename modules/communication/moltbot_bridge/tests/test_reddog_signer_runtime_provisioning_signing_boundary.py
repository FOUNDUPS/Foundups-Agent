"""Security regressions for atomic provisioning signer selection."""

from __future__ import annotations

import inspect
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

    forged = SignerRuntimeAtomicProvisioningContext(
        signer=object(),  # type: ignore[arg-type]
        authority=context.authority,
        authority_boundary=context.authority_boundary,
        authority_tier=context.authority_tier,
        generation_anchor=anchor,
    )

    result = _provision(forged)

    assert result.accepted is False
    assert anchor.load() is None


def test_atomic_factory_retains_no_mutable_verifier_or_registry_closure() -> None:
    from modules.communication.moltbot_bridge.src import (
        reddog_signer_runtime_atomic_provisioning_contract as target,
    )

    closure = inspect.getclosurevars(
        target.create_signer_runtime_atomic_provisioning_context
    )
    assert closure.nonlocals == {}
    assert not {"records", "contexts", "verifier_type"} & set(
        closure.globals
    )
