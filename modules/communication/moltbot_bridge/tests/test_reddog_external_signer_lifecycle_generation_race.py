"""Generation-race regressions for external signer lifecycle admission."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src import (
    reddog_external_signer_lifecycle_admission as lifecycle_module,
)
from modules.communication.moltbot_bridge.src.reddog_external_signer_lifecycle_admission import (
    ExternalSignerLifecycleAdmissionError,
    create_external_signer_lifecycle_admission_boundary,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_anchor import (
    SignerRuntimeGenerationBinding,
)
from modules.communication.moltbot_bridge.tests.reddog_signer_generation_test_support import (
    create_lifecycle_generation_authority,
)
from modules.communication.moltbot_bridge.tests.test_reddog_external_signer_lifecycle_admission import (
    NOW,
    _Clocks,
    _Healthcheck,
    _IdentityString,
    _Observer,
    _PolicyBoundary,
    _SelectionBoundary,
    _boundary as _admission_boundary,
    _health,
    _mapping_digest,
    _observation,
    _runtime,
    _sha,
)


def _next_binding(values: dict[str, object]) -> SignerRuntimeGenerationBinding:
    return SignerRuntimeGenerationBinding(
        generation=2,
        manifest_id=_sha("d"),
        artifact_generation_digest=_sha("e"),
        config_digest=str(values["config_digest"]),
        config_raw_digest=str(values["config_raw_digest"]),
        run_packet_digest=str(values["run_packet_digest"]),
    )


def _boundary(tmp_path: Path, observer):
    repo, packet_path, values = _runtime(tmp_path)
    authority, reader_boundary, writer = create_lifecycle_generation_authority(
        repo, values, return_writer=True
    )
    policy = _PolicyBoundary()
    selection = _SelectionBoundary(values)
    boundary = create_external_signer_lifecycle_admission_boundary(
        repo_root=repo,
        manifest_boundary=selection,
        generation_reader_authority=authority,
        generation_reader_authority_boundary=reader_boundary,
        os_policy_authority=policy,
        os_policy_authority_boundary=policy,
        requester_principal_id="github:mjtrout",
        os_observer=observer(writer, values),
        healthcheck_runner=_Healthcheck(_health(packet_path)),
        trusted_clock=_Clocks().wall,
    )
    return boundary, writer, values, selection


def test_generation_advance_during_observation_rejects_admission(
    tmp_path: Path,
) -> None:
    def observer(writer, values):
        base = _Observer(_observation())

        def advance(policy, *, observed_at_epoch):
            current = writer.load()
            writer.activate(
                _next_binding(values), expected_revision=current.revision
            )
            return base(policy, observed_at_epoch=observed_at_epoch)

        return advance

    boundary, _, _, selection = _boundary(tmp_path, observer)
    with pytest.raises(ExternalSignerLifecycleAdmissionError):
        boundary.admit(selection)


def test_generation_advance_before_consumption_invalidates_capability(
    tmp_path: Path,
) -> None:
    boundary, writer, values, selection = _boundary(
        tmp_path, lambda _writer, _values: _Observer(_observation())
    )
    capability = boundary.admit(selection)
    current = writer.load()
    writer.activate(_next_binding(values), expected_revision=current.revision)

    with pytest.raises(ExternalSignerLifecycleAdmissionError):
        boundary.consume(capability)


def _consume_verified(boundary, capability, **expected):
    identities = {
        "requester_principal_id": "github:mjtrout",
        "signer_profile_id": "reddog-work-authority",
    }
    identities.update(expected)
    return lifecycle_module.consume_verified_external_signer_lifecycle_admission(
        boundary, capability, **identities
    )


@pytest.mark.parametrize("identities", [
    {}, {"requester_principal_id": "github:second"},
    {"signer_profile_id": "review-signer"},
])
def test_verified_consumer_returns_correlated_audit_receipt_once(tmp_path, identities):
    boundary, selection, observer, healthcheck, *_ = _admission_boundary(
        tmp_path, **identities, health_changes=identities
    )
    capability = boundary.admit(selection)
    receipt = _consume_verified(boundary, capability, **identities)
    payload = receipt.to_dict()
    receipt_id = payload.pop("receipt_id")
    for name in ("authority_granted", "valve_unlocked", "effect_capability_issued"):
        assert payload.pop(name) is False
    assert receipt_id == _mapping_digest(payload)
    assert receipt.requester_principal_id == identities.get(
        "requester_principal_id", "github:mjtrout"
    )
    assert receipt.signer_profile_id == identities.get(
        "signer_profile_id", "reddog-work-authority"
    )
    assert observer.calls == healthcheck.calls == 1
    with pytest.raises(ExternalSignerLifecycleAdmissionError):
        _consume_verified(boundary, capability, **identities)
    assert observer.calls == healthcheck.calls == 1


@pytest.mark.parametrize("kind", ["fake", "subclass", "fabricated"])
def test_verified_consumer_rejects_boundary_before_hostile_callbacks(tmp_path, kind):
    boundary, selection, *_ = _admission_boundary(tmp_path)
    capability = boundary.admit(selection)
    calls = []

    def forbidden(*args):
        calls.append("boundary_callback")
        raise AssertionError("untrusted boundary callback reached")

    if kind == "fabricated":
        untrusted = object.__new__(type(boundary))
    else:
        base = object if kind == "fake" else type(boundary)
        hostile = type("HostileBoundary", (base,), {
            "__hash__": forbidden, "__eq__": forbidden,
            "__getattribute__": forbidden, "__getattr__": forbidden,
            "consume": forbidden,
        })
        untrusted = object.__new__(hostile)
    with pytest.raises(ExternalSignerLifecycleAdmissionError):
        _consume_verified(untrusted, capability)
    assert calls == []
    assert _consume_verified(boundary, capability).generation == 1


def test_verified_consumer_uses_captured_owner_not_public_dispatch(tmp_path, monkeypatch):
    boundary, selection, *_ = _admission_boundary(tmp_path)
    capability = boundary.admit(selection)
    calls = []

    def forbidden(*args):
        calls.append("public_consume")
        raise AssertionError("public consume must not confer ownership")

    monkeypatch.setattr(type(boundary), "consume", forbidden)
    monkeypatch.setattr(lifecycle_module, "_Boundary", object)
    assert _consume_verified(boundary, capability).generation == 1
    assert calls == []


@pytest.mark.parametrize("injection", ["_lookup", "_issue"])
def test_verified_consumer_has_no_registry_injection(tmp_path, injection):
    boundary, selection, *_ = _admission_boundary(tmp_path)
    capability = boundary.admit(selection)
    consume = lifecycle_module.consume_verified_external_signer_lifecycle_admission
    assert set(inspect.signature(consume).parameters) == {
        "boundary", "capability", "requester_principal_id", "signer_profile_id",
    }
    with pytest.raises(TypeError):
        _consume_verified(boundary, capability, **{injection: lambda *_: None})
    assert not hasattr(lifecycle_module, "_lookup_boundary")
    assert not hasattr(lifecycle_module, "_issue_boundary")
    assert _consume_verified(boundary, capability).generation == 1


@pytest.mark.parametrize("field", ["requester_principal_id", "signer_profile_id"])
@pytest.mark.parametrize("identity", [None, "", "  ", 1, True, [], {}, "subclass"])
def test_verified_consumer_malformed_expected_identity_preserves_handle(
    tmp_path, field, identity
):
    if identity == "subclass":
        identity = _IdentityString("derived")
    boundary, selection, *_ = _admission_boundary(tmp_path)
    capability = boundary.admit(selection)
    with pytest.raises(ExternalSignerLifecycleAdmissionError):
        _consume_verified(boundary, capability, **{field: identity})
    assert _consume_verified(boundary, capability).generation == 1


@pytest.mark.parametrize("field", ["requester_principal_id", "signer_profile_id"])
@pytest.mark.parametrize("mismatch", ["different", "padded"])
def test_verified_consumer_valid_identity_mismatch_burns_handle(tmp_path, field, mismatch):
    boundary, selection, *_ = _admission_boundary(tmp_path)
    capability = boundary.admit(selection)
    expected = "github:mjtrout" if field == "requester_principal_id" else "reddog-work-authority"
    identity = "attacker" if mismatch == "different" else f" {expected} "
    with pytest.raises(ExternalSignerLifecycleAdmissionError):
        _consume_verified(boundary, capability, **{field: identity})
    with pytest.raises(ExternalSignerLifecycleAdmissionError):
        _consume_verified(boundary, capability)


def test_verified_consumer_foreign_owner_preserves_original_handle(tmp_path):
    left, right = tmp_path / "left", tmp_path / "right"
    left.mkdir()
    right.mkdir()
    first, selected, *_ = _admission_boundary(left)
    second, *_ = _admission_boundary(right)
    capability = first.admit(selected)
    with pytest.raises(ExternalSignerLifecycleAdmissionError):
        _consume_verified(second, capability)
    assert _consume_verified(first, capability).generation == 1


@pytest.mark.parametrize("kind", ["dict", "receipt", "manual_receipt"])
def test_verified_consumer_rejects_audit_data_as_capability(tmp_path, kind):
    boundary, selection, *_ = _admission_boundary(tmp_path)
    receipt = boundary.consume(boundary.admit(selection))
    value = receipt.to_dict() if kind == "dict" else receipt
    if kind == "manual_receipt":
        value = type(receipt)(**{**receipt.to_dict(), "authority_granted": True})
    with pytest.raises(ExternalSignerLifecycleAdmissionError):
        _consume_verified(boundary, value)


@pytest.mark.parametrize("wall,monotonic", [(NOW + 30, 1030), (NOW - 1, 1001), (NOW + 1, 999)])
def test_verified_consumer_freshness_rejection_cannot_be_revived(tmp_path, wall, monotonic):
    boundary, selection, *_, clocks = _admission_boundary(tmp_path)
    capability = boundary.admit(selection)
    clocks.wall_value, clocks.monotonic_value = wall, monotonic
    with pytest.raises(ExternalSignerLifecycleAdmissionError):
        _consume_verified(boundary, capability)
    clocks.wall_value, clocks.monotonic_value = NOW + 1, 1001
    with pytest.raises(ExternalSignerLifecycleAdmissionError):
        _consume_verified(boundary, capability)


def test_verified_consumer_revalidates_current_generation(tmp_path):
    boundary, writer, values, selection = _boundary(
        tmp_path, lambda _writer, _values: _Observer(_observation())
    )
    capability = boundary.admit(selection)
    current = writer.load()
    writer.activate(_next_binding(values), expected_revision=current.revision)
    with pytest.raises(ExternalSignerLifecycleAdmissionError):
        _consume_verified(boundary, capability)
    with pytest.raises(ExternalSignerLifecycleAdmissionError):
        _consume_verified(boundary, capability)


@pytest.mark.parametrize(
    ("field", "identity"),
    [("requester_principal_id", "github:second"), ("signer_profile_id", "review-signer")],
)
def test_consumed_receipt_preserves_and_hashes_selected_identity(tmp_path, field, identity):
    boundary, selection, *_ = _admission_boundary(
        tmp_path, **{field: identity}, health_changes={field: identity}
    )
    receipt = boundary.consume(boundary.admit(selection))
    payload = receipt.to_dict()
    assert payload[field] == identity
    receipt_id = payload.pop("receipt_id")
    for name in ("authority_granted", "valve_unlocked", "effect_capability_issued"):
        assert payload.pop(name) is False
    assert receipt_id == _mapping_digest(payload)
    payload[field] = "different-identity"
    assert receipt_id != _mapping_digest(payload)
    with pytest.raises(ExternalSignerLifecycleAdmissionError):
        boundary.consume(receipt)



@pytest.mark.parametrize("field", ["requester_principal_id", "signer_profile_id"])
@pytest.mark.parametrize("identity", [None, "", "  ", 1, True, [], {}, _IdentityString("derived")])
def test_matching_malformed_config_and_handshake_identity_rejects(tmp_path, field, identity):
    boundary, selection, *_ = _admission_boundary(
        tmp_path, **{field: identity}, health_changes={field: identity}
    )
    with pytest.raises(ExternalSignerLifecycleAdmissionError):
        boundary.admit(selection)



def test_same_generation_other_boundary_cannot_consume_identity_capability(tmp_path):
    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()
    first, selected, *_ = _admission_boundary(left)
    second, _, *_ = _admission_boundary(
        right, requester_principal_id="github:second",
        health_changes={"requester_principal_id": "github:second"},
    )
    capability = first.admit(selected)
    with pytest.raises(ExternalSignerLifecycleAdmissionError):
        second.consume(capability)
    assert first.consume(capability).generation == 1
