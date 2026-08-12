"""Independent grant-provider identity regressions for HIGH authority."""

from __future__ import annotations

from dataclasses import replace

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_signer_client import (
    ElevatedConsensusExternalSignerClient,
)
from modules.communication.moltbot_bridge.tests.reddog_elevated_consensus_e2e_support import (
    NOW,
    build_route,
)
from modules.communication.moltbot_bridge.tests.reddog_elevated_consensus_test_support import (
    verified_consensus_for_request,
)
from modules.communication.moltbot_bridge.tests.test_reddog_elevated_consensus_composed_e2e import (
    _authority,
)
from modules.communication.moltbot_bridge.tests.test_reddog_signer_delegated_authority_runtime import (
    _request,
)


def _provider(tmp_path, name):
    request, _, _ = verified_consensus_for_request(_request(), now=NOW)
    root = tmp_path / name
    root.mkdir()
    return build_route(
        root,
        name,
        Ed25519PrivateKey.generate(),
        Ed25519PrivateKey.generate(),
        _authority(request),
    )[:2]


def _client(signer, principal, reddog):
    return ElevatedConsensusExternalSignerClient(
        signer=signer,
        principal_grant_provider=principal,
        reddog_grant_provider=reddog,
    )


def test_external_signer_rejects_one_provider_for_both_roles(tmp_path) -> None:
    provider, signer = _provider(tmp_path, "shared")
    try:
        _client(signer, provider, provider)
    except ValueError as exc:
        assert str(exc) == "elevated_consensus_grant_providers_not_independent"
    else:
        raise AssertionError("shared elevated consensus provider accepted")


def test_external_signer_rejects_same_authority_with_requester_alias(
    tmp_path,
) -> None:
    provider, signer = _provider(tmp_path, "alias")
    alias = replace(
        provider,
        grant_authority=replace(
            provider.grant_authority, requester_principal_id="requester:alias"
        ),
    )
    try:
        _client(signer, provider, alias)
    except ValueError as exc:
        assert str(exc) == "elevated_consensus_grant_providers_not_independent"
    else:
        raise AssertionError("requester alias bypassed grant authority separation")


def test_external_signer_rejects_one_authority_with_distinct_keys_and_services(
    tmp_path,
) -> None:
    principal, signer = _provider(tmp_path, "principal-authority")
    reddog, _ = _provider(tmp_path, "reddog-authority")
    same_authority = replace(
        reddog,
        grant_authority=replace(
            reddog.grant_authority,
            principal_id=principal.grant_authority.principal_id,
            principal_provider=principal.grant_authority.principal_provider,
        ),
    )
    try:
        _client(signer, principal, same_authority)
    except ValueError as exc:
        assert str(exc) == "elevated_consensus_grant_providers_not_independent"
    else:
        raise AssertionError("one authority controlled two accepted grant services")
