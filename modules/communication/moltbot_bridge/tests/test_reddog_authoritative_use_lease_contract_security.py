"""Contract and canonicalization tests for authoritative-use leases."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_authoritative_use_lease import (
    consume_authoritative_use_lease,
    is_authoritative_use_lease,
)
from modules.communication.moltbot_bridge.src.reddog_authoritative_use_lease_contract import (
    AUTHORITATIVE_USE_LEASE_SIGNING_PREFIX,
    authoritative_use_effect_digest,
    build_authoritative_use_lease_request,
    validate_authoritative_use_lease_request,
)
from modules.communication.moltbot_bridge.src.reddog_isolated_signer_socket_protocol import (
    REJECT_SIGNER_SOCKET_SECRET_GRANT_UNSUPPORTED,
    SIGNER_SOCKET_REQUEST_SCHEMA_VERSION,
    SIGNER_SOCKET_REQUEST_SCHEMA_VERSION_V2,
    handle_reddog_isolated_signer_socket_request,
)
from modules.communication.moltbot_bridge.tests.test_reddog_external_signer_authoritative_use_lease import (
    NOW,
    _ProtocolGrantBackend,
    _backend,
    _consume_lease,
    _effect_digest,
    _effect_payload,
    _lease,
    _payload,
    _peer,
    _request,
)


def test_lease_cannot_be_substituted_for_another_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, _, lease = _lease(tmp_path, monkeypatch)
    assert not is_authoritative_use_lease(
        lease, effect_kind="live_enqueue", effect_request_digest=_effect_digest()
    )
    assert not consume_authoritative_use_lease(
        lease,
        effect_kind="worktree_create",
        effect_request_digest="sha256:" + "1" * 64,
    )
    assert _consume_lease(lease)


def test_effect_digest_must_match_complete_declared_effect() -> None:
    changed = _effect_payload(queue_item_id="attacker-queue")
    with pytest.raises(ValueError):
        build_authoritative_use_lease_request(
            _payload(effect_payload=changed), authority_tier="HIGH"
        )
    valid = dict(_payload(effect_payload=changed))
    valid["effect_request_digest"] = authoritative_use_effect_digest(
        "worktree_create", changed
    )
    assert build_authoritative_use_lease_request(valid, authority_tier="HIGH")


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("manifest_id", "sha256:" + "5" * 64),
        ("artifact_generation_digest", "sha256:" + "5" * 64),
        ("generation", 8),
        ("generation_revision", "revision-8"),
        ("owner_config_id", "sha256:" + "5" * 64),
    ),
)
def test_signer_rejects_substituted_generation_field(
    field: str, value: object
) -> None:
    request = _request(**{field: value})
    assert not _backend(request, exact=True).sign(request, _peer()).accepted


def test_socket_lease_domain_is_v2_grant_only() -> None:
    request = _request()
    v1 = json.dumps(
        {"schema_version": SIGNER_SOCKET_REQUEST_SCHEMA_VERSION, "request": request.to_dict()},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    denied = json.loads(
        handle_reddog_isolated_signer_socket_request(
            v1, peer=_peer(), backend=_ProtocolGrantBackend()
        )
    )
    assert denied["rejection_code"] == REJECT_SIGNER_SOCKET_SECRET_GRANT_UNSUPPORTED

    v2 = json.dumps(
        {
            "schema_version": SIGNER_SOCKET_REQUEST_SCHEMA_VERSION_V2,
            "request": request.to_dict(),
            "secret_access_grant": {"grant_id": "root-grant-1"},
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    accepted = json.loads(
        handle_reddog_isolated_signer_socket_request(
            v2, peer=_peer(), backend=_ProtocolGrantBackend()
        )
    )
    assert accepted["accepted"] is True


def test_noncanonical_or_duplicate_key_input_rejects() -> None:
    request = _request()
    raw = request.signing_input.removeprefix(AUTHORITATIVE_USE_LEASE_SIGNING_PREFIX)
    pretty = replace(
        request,
        signing_input=(
            AUTHORITATIVE_USE_LEASE_SIGNING_PREFIX
            + json.dumps(json.loads(raw), indent=2, sort_keys=False)
        ),
    )
    assert validate_authoritative_use_lease_request(pretty, now_epoch=NOW) is None
    duplicate = replace(
        request,
        signing_input=(
            AUTHORITATIVE_USE_LEASE_SIGNING_PREFIX
            + raw[:-1]
            + ',"lease_nonce":"'
            + "a" * 64
            + '"}'
        ),
    )
    assert validate_authoritative_use_lease_request(duplicate, now_epoch=NOW) is None
