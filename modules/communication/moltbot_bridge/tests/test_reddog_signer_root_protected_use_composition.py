"""Adversarial proof for root-linearized signer protected use."""

from __future__ import annotations

import ast
import copy
import json
import pickle
import threading
import time
from dataclasses import replace
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src import (
    foundup_verified_outcome_root_authority_client as root_client_module,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_router import (
    handle_root_authority_wire_request,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_state import (
    GENERATION_BINDING,
    PROTECTED_USE_BINDING,
    RootVerifiedOutcomeAuthorityState,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_protected_use_client import (
    RootProtectedUseAuthority,
    _create_root_protected_use_authority,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_protected_use_protocol import (
    response_from_bytes as protected_response_from_bytes,
)
from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_revocation_client import (
    _lookup_client as _lookup_revocation_client,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
    encode_ed25519_signature,
)
from modules.communication.moltbot_bridge.src.reddog_proposal_authenticity_nonce_store import (
    ProposalReplayHighWater,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_contract import (
    canonical_signer_grant_revocation_snapshot_input,
    signer_grant_revocation_snapshot_id,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_access_grant import (
    SignerSecretAccessGrantBoundary,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_durable_oracle import (
    UncomposedDurableSignerGrantRevocationOracle,
)
from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_root_protected_use_oracle import (
    RootAuthorizedSignerGrantRevocationOracle,
)
from modules.communication.moltbot_bridge.src.reddog_signer_resolve_per_sign_backend import (
    ResolvePerSignSignerBackend,
)
from modules.communication.moltbot_bridge.tests.root_revocation_service_fixtures import (
    runtime,
    signed_snapshot,
    stage,
)
from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_authority import (
    _sha,
    _sign,
)
from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_authority_service import (
    _peer,
)
from modules.communication.moltbot_bridge.tests import (
    test_reddog_signer_resolve_per_sign_backend as resolve_fixture,
)


def _protected_client(values) -> RootProtectedUseAuthority:
    revocation = _lookup_revocation_client(values["client"])
    return _create_root_protected_use_authority(
        values["snapshot"].descriptor,
        owner_config_id=str(values["policy"]["owner_config_id"]),
        policy=values["policy"],
        binding=values["binding"],
        exchange=revocation.exchange,
        request_signer=lambda value: _sign(values["target_private"], value),
        now_epoch=int(time.time()),
    )


def _route(values, raw: bytes) -> bytes:
    return handle_root_authority_wire_request(
        raw,
        peer=_peer(),
        state=values["state"],
        snapshot_supplier=lambda: values["snapshot"],
        revocation_authority=values["server_authority"],
        now_epoch=int(time.time()),
    )


def _bind_router(values, monkeypatch) -> None:
    monkeypatch.setattr(
        root_client_module,
        "_root_socket_roundtrip",
        lambda _path, raw, _uid, _timeout: _route(values, raw),
    )


def _install_current(values, snapshot) -> None:
    stage(values, snapshot)
    values["client"].advance_snapshot(snapshot["snapshot_id"])
    values["store"]._finalize_under_lock(snapshot["snapshot_id"])


def _revoking_snapshot(values, grant_id: str, sequence: int) -> dict:
    value = signed_snapshot(values, sequence=sequence)
    value["revoked_grant_ids"] = [grant_id]
    value["snapshot_id"] = signer_grant_revocation_snapshot_id(value)
    value["signature"] = encode_ed25519_signature(
        values["revocation_private"].sign(
            canonical_signer_grant_revocation_snapshot_input(value).encode("ascii")
        )
    )
    return value


def _authorize(client, action, *, grant_id=None):
    return client.authorize_use(
        grant_id=grant_id or _sha("grant"),
        key_epoch="epoch-1",
        signing_request_digest=_sha("request"),
        grant_expires_at=int(time.time()) + 120,
        action=action,
    )


def _resolve_backend(values, tmp_path, ephemeral):
    request = resolve_fixture._request()
    nonce_store = resolve_fixture._store(tmp_path / "grant-runtime")
    grant = resolve_fixture._grant(
        request, nonce_store,
        issued_at=int(time.time()) - 10,
        expires_at=int(time.time()) + 120,
    )

    class Resolver:
        def resolve(self, principal_id, provider):
            if (
                principal_id
                == values["policy"]["revocation_authority_principal_id"]
                and provider
                == values["policy"]["revocation_authority_principal_provider"]
            ):
                return values["policy"]["revocation_authority_public_key"]
            return None

    durable = UncomposedDurableSignerGrantRevocationOracle(
        binding=values["binding"], policy=values["policy"],
        reader=values["store"].reader(), witness=values["witness"].reader(),
        anchor=values["client"], principal_key_resolver=Resolver(),
        signature_verifier=Ed25519SignatureVerifier(),
        clock=lambda: int(time.time()),
    )
    oracle = RootAuthorizedSignerGrantRevocationOracle(
        durable=durable, protected_use=_protected_client(values)
    )
    boundary = SignerSecretAccessGrantBoundary(
        nonce_store=nonce_store, revocation_oracle=oracle,
        clock=lambda: int(time.time()),
    )
    backend = ResolvePerSignSignerBackend(
        binding=resolve_fixture._binding(nonce_store),
        grant_boundary=boundary,
        signature_verifier=resolve_fixture._Verifier(grant),
        principal_key_resolver=resolve_fixture._Resolver(),
        backend_factory=resolve_fixture._Factory(ephemeral),
    )
    return backend, request, grant


def test_acquire_finish_and_lost_finish_retry_are_root_linearized(
    tmp_path, monkeypatch
) -> None:
    values = runtime(tmp_path, monkeypatch)
    _install_current(values, signed_snapshot(values))
    attempts = {"finish": 0}
    acquire_packets: list[bytes] = []

    def exchange(raw: bytes) -> bytes:
        if b'"operation":"PROTECTED_USE_ACQUIRE"' in raw:
            acquire_packets.append(raw)
        response = _route(values, raw)
        if b'"operation":"PROTECTED_USE_FINISH"' in raw:
            attempts["finish"] += 1
            if attempts["finish"] == 1:
                raise TimeoutError("lost response")
        return response

    monkeypatch.setattr(
        root_client_module,
        "_root_socket_roundtrip",
        lambda _path, raw, _uid, _timeout: exchange(raw),
    )
    client = _protected_client(values)
    assert _authorize(client, lambda: "signed") == "signed"
    assert attempts["finish"] == 2
    finished = values["state"].load(PROTECTED_USE_BINDING)
    assert finished is not None and finished.sequence == 2
    replay = protected_response_from_bytes(_route(values, acquire_packets[0]))
    assert replay.accepted is False


def test_lost_acquire_response_retries_exact_use_before_callback(
    tmp_path, monkeypatch
) -> None:
    values = runtime(tmp_path, monkeypatch)
    _install_current(values, signed_snapshot(values))
    attempts = 0
    called: list[bool] = []

    def exchange(raw: bytes) -> bytes:
        nonlocal attempts
        response = _route(values, raw)
        if b'"operation":"PROTECTED_USE_ACQUIRE"' in raw:
            attempts += 1
            if attempts == 1:
                raise TimeoutError("lost acquire response")
        return response

    monkeypatch.setattr(
        root_client_module, "_root_socket_roundtrip",
        lambda _path, raw, _uid, _timeout: exchange(raw),
    )
    assert _authorize(
        _protected_client(values), lambda: called.append(True) or "signed"
    ) == "signed"
    assert attempts == 2
    assert called == [True]


def test_marker_only_crash_reconciles_before_callback(tmp_path, monkeypatch) -> None:
    values = runtime(tmp_path, monkeypatch)
    _install_current(values, signed_snapshot(values))
    original = RootVerifiedOutcomeAuthorityState._advance_pair
    failed = False

    def crash_once(self, binding, expected, next_value):
        nonlocal failed
        if binding == PROTECTED_USE_BINDING and not failed:
            failed = True
            raise OSError("injected crash")
        return original(self, binding, expected, next_value)

    monkeypatch.setattr(
        RootVerifiedOutcomeAuthorityState, "_advance_pair", crash_once
    )
    _bind_router(values, monkeypatch)
    called: list[bool] = []
    assert _authorize(
        _protected_client(values), lambda: called.append(True) or "signed"
    ) == "signed"
    assert failed is True
    assert called == [True]


def test_generation_rotation_rejects_stale_acquire_under_root_lock(
    tmp_path, monkeypatch
) -> None:
    values = runtime(tmp_path, monkeypatch)
    current = signed_snapshot(values)
    _install_current(values, current)
    state = values["state"]
    old = state.load(GENERATION_BINDING)
    assert old is not None
    state.observe_generation(2, _sha("rotated-owner"))
    with pytest.raises(RuntimeError, match="generation_conflict"):
        state.acquire_protected_use(
            expected_generation=old,
            revocation_binding=values["binding"].anchor_binding_digest(),
            expected_revocation=ProposalReplayHighWater(
                1, current["snapshot_id"][7:]
            ),
            protected_use_binding=_sha("stale-generation-use"),
            use_revision="b" * 64,
        )
    assert state.load(PROTECTED_USE_BINDING) is None


def test_acquire_first_blocks_revocation_until_finish(tmp_path, monkeypatch) -> None:
    values = runtime(tmp_path, monkeypatch)
    _install_current(values, signed_snapshot(values))
    _bind_router(values, monkeypatch)
    client = _protected_client(values)
    entered, release = threading.Event(), threading.Event()
    result: list[str] = []

    def action() -> str:
        entered.set()
        assert release.wait(5)
        return "signed"

    thread = threading.Thread(target=lambda: result.append(_authorize(client, action)))
    thread.start()
    assert entered.wait(5)
    candidate = signed_snapshot(values, sequence=2)
    stage(values, candidate)
    with pytest.raises(ValueError, match="request_rejected"):
        values["client"].advance_snapshot(candidate["snapshot_id"])
    active = values["state"].load(PROTECTED_USE_BINDING)
    assert active is not None and active.sequence % 2 == 1
    release.set()
    thread.join(5)
    assert result == ["signed"]
    values["client"].advance_snapshot(candidate["snapshot_id"])


def test_revocation_first_rejects_before_callback(tmp_path, monkeypatch) -> None:
    values = runtime(tmp_path, monkeypatch)
    grant_id = _sha("grant")
    _install_current(values, signed_snapshot(values))
    candidate = _revoking_snapshot(values, grant_id, 2)
    _install_current(values, candidate)
    _bind_router(values, monkeypatch)
    called: list[bool] = []
    with pytest.raises(ValueError, match="request_rejected"):
        _authorize(
            _protected_client(values), lambda: called.append(True),
            grant_id=grant_id,
        )
    assert called == []


def test_resolve_per_sign_acquire_first_blocks_revocation(
    tmp_path, monkeypatch
) -> None:
    values = runtime(tmp_path, monkeypatch)
    _install_current(values, signed_snapshot(values))
    _bind_router(values, monkeypatch)
    entered, release = threading.Event(), threading.Event()

    class BarrierBackend(resolve_fixture._EphemeralBackend):
        def sign(self, request, peer):
            entered.set()
            assert release.wait(5)
            return super().sign(request, peer)

    ephemeral = BarrierBackend()
    backend, request, grant = _resolve_backend(values, tmp_path, ephemeral)
    responses = []
    thread = threading.Thread(
        target=lambda: responses.append(
            backend.sign_with_secret_grant(
                request, resolve_fixture._peer(), grant
            )
        )
    )
    thread.start()
    assert entered.wait(5)
    candidate = signed_snapshot(values, sequence=2)
    stage(values, candidate)
    with pytest.raises(ValueError, match="request_rejected"):
        values["client"].advance_snapshot(candidate["snapshot_id"])
    release.set()
    thread.join(5)
    assert len(responses) == 1 and responses[0].accepted is True
    assert ephemeral.calls == 1


def test_resolve_per_sign_revocation_first_emits_no_signature(
    tmp_path, monkeypatch
) -> None:
    values = runtime(tmp_path, monkeypatch)
    request = resolve_fixture._request()
    _install_current(values, signed_snapshot(values))
    _bind_router(values, monkeypatch)
    ephemeral = resolve_fixture._EphemeralBackend()
    backend, request, grant = _resolve_backend(values, tmp_path, ephemeral)
    candidate = _revoking_snapshot(values, str(grant["grant_id"]), 2)
    _install_current(values, candidate)
    response = backend.sign_with_secret_grant(
        request, resolve_fixture._peer(), grant
    )
    assert response.accepted is False
    assert ephemeral.calls == 0


def test_unfinished_use_fails_closed_and_blocks_later_use_and_revocation(
    tmp_path, monkeypatch
) -> None:
    values = runtime(tmp_path, monkeypatch)
    current = signed_snapshot(values)
    _install_current(values, current)
    root = values["state"]
    high = ProposalReplayHighWater(1, current["snapshot_id"][7:])
    root.acquire_protected_use(
        expected_generation=ProposalReplayHighWater(
            values["snapshot"].authority_generation_sequence,
            values["snapshot"].owner_config_id[7:],
        ),
        revocation_binding=values["binding"].anchor_binding_digest(),
        expected_revocation=high,
        protected_use_binding=_sha("crashed-use"),
        use_revision="a" * 64,
    )
    _bind_router(values, monkeypatch)
    with pytest.raises(ValueError, match="request_rejected"):
        _authorize(_protected_client(values), lambda: "never")
    candidate = signed_snapshot(values, sequence=2)
    stage(values, candidate)
    with pytest.raises(ValueError, match="request_rejected"):
        values["client"].advance_snapshot(candidate["snapshot_id"])


def test_protected_client_is_factory_only_opaque_and_router_preserves_revocation(
    tmp_path, monkeypatch
) -> None:
    values = runtime(tmp_path, monkeypatch)
    _install_current(values, signed_snapshot(values))
    _bind_router(values, monkeypatch)
    client = _protected_client(values)
    with pytest.raises(TypeError):
        RootProtectedUseAuthority()
    with pytest.raises(TypeError):
        copy.copy(client)
    with pytest.raises(TypeError):
        copy.deepcopy(client)
    with pytest.raises(TypeError):
        pickle.dumps(client)
    assert values["client"].load() == ProposalReplayHighWater(
        1, values["store"].state().current["snapshot_id"][7:]
    )


def test_root_composed_oracle_is_the_only_new_atomic_boundary(
    tmp_path, monkeypatch
) -> None:
    # Composition is the subject here; separate wall-clock samples can straddle
    # a second and legitimately trip the oracle's exact claimed-time check.
    now = int(time.time())
    monkeypatch.setattr(time, "time", lambda: now)
    values = runtime(tmp_path, monkeypatch)
    _install_current(values, signed_snapshot(values))
    _bind_router(values, monkeypatch)

    class Resolver:
        def resolve(self, principal_id, provider):
            if (
                principal_id == values["policy"]["revocation_authority_principal_id"]
                and provider == values["policy"]["revocation_authority_principal_provider"]
            ):
                return values["policy"]["revocation_authority_public_key"]
            return None

    durable = UncomposedDurableSignerGrantRevocationOracle(
        binding=values["binding"], policy=values["policy"],
        reader=values["store"].reader(), witness=values["witness"].reader(),
        anchor=values["client"], principal_key_resolver=Resolver(),
        signature_verifier=Ed25519SignatureVerifier(),
        clock=lambda: int(time.time()),
    )
    composed = RootAuthorizedSignerGrantRevocationOracle(
        durable=durable, protected_use=_protected_client(values)
    )
    boundary = SignerSecretAccessGrantBoundary(
        nonce_store=object(), revocation_oracle=composed,
        clock=lambda: int(time.time()),
    )
    assert boundary.atomic_revocation is True
    assert composed.is_key_epoch_revoked(
        key_epoch="epoch-not-revoked", at_epoch=int(time.time())
    ) is False
    with pytest.raises(ValueError, match="durable_revocation_oracle_clock_invalid"):
        composed.is_key_epoch_revoked(
            key_epoch="epoch-not-revoked", at_epoch=now - 1
        )
    grant = {
        "grant_id": _sha("grant"), "key_epoch": "epoch-1",
        "signing_request_digest": _sha("request"),
        "expires_at": int(time.time()) + 120,
    }
    assert composed.authorize_grant_use(grant, lambda: "signed") == "signed"
    assert composed.binding == values["binding"]

    def reject_grant_domain(*_args, **_kwargs):
        raise AssertionError("grant_domain_must_not_handle_permission_use")

    monkeypatch.setattr(
        RootProtectedUseAuthority, "authorize_use", reject_grant_domain
    )
    assert composed.authorize_key_epoch_use(
        key_epoch="epoch-not-revoked",
        at_epoch=int(time.time()),
        expires_at=int(time.time()) + 120,
        action=lambda: "permissioned",
    ) == "permissioned"

    class FakeComposed(RootAuthorizedSignerGrantRevocationOracle):
        pass

    fake = FakeComposed(durable=durable, protected_use=_protected_client(values))
    fake_boundary = SignerSecretAccessGrantBoundary(
        nonce_store=object(), revocation_oracle=fake,
        clock=lambda: int(time.time()),
    )
    assert fake_boundary.atomic_revocation is False


def test_substituted_acquire_response_suppresses_callback(
    tmp_path, monkeypatch
) -> None:
    values = runtime(tmp_path, monkeypatch)
    _install_current(values, signed_snapshot(values))
    called: list[bool] = []

    def substitute(_path, raw, _uid, _timeout):
        response = protected_response_from_bytes(_route(values, raw))
        return replace(response, protected_use_id=_sha("substitute")).to_bytes()

    monkeypatch.setattr(root_client_module, "_root_socket_roundtrip", substitute)
    with pytest.raises(ValueError, match="request_rejected"):
        _authorize(_protected_client(values), lambda: called.append(True))
    assert called == []
    active = values["state"].load(PROTECTED_USE_BINDING)
    assert active is not None and active.sequence % 2 == 1


@pytest.mark.parametrize("field", ("request_id", "revision", "sequence"))
def test_substituted_finish_response_suppresses_callback_result(
    tmp_path, monkeypatch, field
) -> None:
    values = runtime(tmp_path, monkeypatch)
    _install_current(values, signed_snapshot(values))
    called: list[bool] = []

    def substitute(_path, raw, _uid, _timeout):
        response = protected_response_from_bytes(_route(values, raw))
        if b'"operation":"PROTECTED_USE_FINISH"' in raw:
            altered = (
                response.sequence + 2 if field == "sequence"
                else (
                    _sha("substitute")[7:]
                    if field == "revision"
                    else _sha("substitute")
                )
            )
            return replace(response, **{field: altered}).to_bytes()
        return response.to_bytes()

    monkeypatch.setattr(root_client_module, "_root_socket_roundtrip", substitute)
    with pytest.raises(ValueError, match="request_rejected"):
        _authorize(
            _protected_client(values),
            lambda: called.append(True) or "signature",
        )
    assert called == [True]
    finished = values["state"].load(PROTECTED_USE_BINDING)
    assert finished is not None and finished.sequence % 2 == 0


def test_protected_use_slice_obeys_effect_and_wsp62_boundaries() -> None:
    source = Path(__file__).parents[1] / "src"
    files = tuple(source.glob("foundup_verified_outcome_root_protected_use_*.py")) + (
        source / "reddog_signer_secret_grant_root_protected_use_oracle.py",
    )
    banned = {"subprocess", "requests", "httpx", "cryptography"}
    for path in files:
        text = path.read_text(encoding="ascii")
        assert len(text.splitlines()) <= 200
        tree = ast.parse(text)
        imports = {
            str(node.module or "").split(".")[0]
            for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
        }
        imports.update(
            alias.name.split(".")[0]
            for node in ast.walk(tree) if isinstance(node, ast.Import)
            for alias in node.names
        )
        assert imports.isdisjoint(banned)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert (node.end_lineno or node.lineno) - node.lineno + 1 <= 50
    validator = (
        source / "foundup_verified_outcome_root_protected_use_authority_validation.py"
    ).read_text(encoding="ascii")
    assert "confined_runtime_operation_lock" not in validator


def test_backend_manifest_binds_every_protected_use_runtime_module() -> None:
    root = Path(__file__).parents[4]
    manifest = json.loads(
        (root / "scripts" / "reddog_backend_manifest.json").read_text(
            encoding="ascii"
        )
    )
    bound = set(manifest["required_runtime_files"])
    source = Path(__file__).parents[1] / "src"
    expected = {
        path.relative_to(root).as_posix()
        for path in source.glob("foundup_verified_outcome_root_protected_use_*.py")
    }
    assert expected <= bound
    assert {
        (source / name).relative_to(root).as_posix()
        for name in (
            "reddog_signer_wsp71_ephemeral_backend_factory.py",
            "reddog_signer_resolve_per_sign_backend.py",
            "reddog_signer_resolve_per_sign_validation.py",
            "reddog_signer_independent_secret_grant_binding.py",
        )
    } <= bound


def _owner_match_oracle(values, monkeypatch):
    """Real component metadata; synthetic stores/transport, no admission claim."""
    durable = UncomposedDurableSignerGrantRevocationOracle(
        binding=values["binding"], policy=values["policy"],
        reader=values["store"].reader(), witness=values["witness"].reader(),
        anchor=values["client"], principal_key_resolver=resolve_fixture._Resolver(),
        signature_verifier=Ed25519SignatureVerifier(), clock=lambda: int(time.time()),
    )
    oracle = RootAuthorizedSignerGrantRevocationOracle(
        durable=durable, protected_use=_protected_client(values)
    )
    calls = []

    def forbidden_effect(*_args, **_kwargs):
        calls.append("unexpected_effect")
        raise AssertionError("owner_matching_must_only_compare_metadata")

    monkeypatch.setattr(root_client_module, "_root_socket_roundtrip", forbidden_effect)
    monkeypatch.setattr(durable, "_current", forbidden_effect)
    monkeypatch.setattr(durable.resolver, "resolve", forbidden_effect)
    return oracle, calls


def test_root_oracle_matches_exact_owner_without_effects(tmp_path, monkeypatch):
    from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_capability_state import (
        freeze_owner_e0_policy,
    )

    assert callable(getattr(RootAuthorizedSignerGrantRevocationOracle, "matches_owner", None)), "owner_match_api_missing"
    values = runtime(tmp_path, monkeypatch)
    oracle, calls = _owner_match_oracle(values, monkeypatch)
    assert oracle.matches_owner(policy=values["policy"], binding=values["binding"]) is True
    assert oracle.matches_owner(
        policy=freeze_owner_e0_policy(values["policy"]), binding=values["binding"]
    ) is True
    assert calls == []


@pytest.mark.parametrize("mismatch", [
    "durable_binding", "durable_snapshot", "protected_binding",
    "protected_policy", "protected_owner", "unregistered_protected",
])
def test_root_oracle_rejects_split_owner_provenance(tmp_path, monkeypatch, mismatch):
    from modules.communication.moltbot_bridge.src import (
        foundup_verified_outcome_root_protected_use_client as client_module,
    )

    assert callable(getattr(RootAuthorizedSignerGrantRevocationOracle, "matches_owner", None)), "owner_match_api_missing"
    values = runtime(tmp_path, monkeypatch)
    oracle, calls = _owner_match_oracle(values, monkeypatch)
    assert oracle.matches_owner(policy=values["policy"], binding=values["binding"]) is True
    if mismatch == "durable_binding":
        oracle._durable.binding = replace(values["binding"], primary_store_id="other-store")
    elif mismatch == "durable_snapshot":
        oracle._durable.expected = replace(oracle._durable.expected, owner_config_id=_sha("other-owner"))
    else:
        original = client_module._lookup_client(oracle._protected_use)
        changed = object.__new__(RootProtectedUseAuthority)
        if mismatch == "protected_binding":
            state = replace(original, binding=replace(original.binding, primary_store_id="other-store"))
        elif mismatch == "protected_policy":
            state = replace(original, policy={**original.policy, "expires_at": original.policy["expires_at"] + 1})
        else:
            state = replace(original, owner_config_id=_sha("other-owner"))
        if mismatch != "unregistered_protected":
            # Deliberate test-only registered-state faults; no operating credential.
            client_module._issue_client(changed, state)
        oracle._protected_use = changed
    assert oracle.matches_owner(policy=values["policy"], binding=values["binding"]) is False
    assert calls == []


@pytest.mark.parametrize("preloaded", [False, True], ids=[
    "unavailable_target_key", "legacy_preprovisioned_target_key",
])
def test_protected_use_request_signer_custody_boundary(tmp_path, monkeypatch, preloaded):
    # Setup uses synthetic keys; measured unavailable closure has no key capability.
    values = runtime(tmp_path, monkeypatch)
    _install_current(values, signed_snapshot(values))
    before = values["state"].load(PROTECTED_USE_BINDING)
    events = []
    if preloaded:
        private = values["target_private"]
        def request_signer(value):
            events.append("request_signer")
            return _sign(private, value)
    else:
        def request_signer(_value):
            events.append("request_signer")
            raise ValueError("test_target_key_capability_unavailable")

    def roundtrip(_path, raw, _uid, _timeout):
        events.append(json.loads(raw)["operation"])
        return _route(values, raw)

    def action():
        events.append("callback")
        return "inert_callback_result"

    monkeypatch.setattr(root_client_module, "_root_socket_roundtrip", roundtrip)
    transport = _lookup_revocation_client(values["client"]).exchange
    client = _create_root_protected_use_authority(
        values["snapshot"].descriptor,
        owner_config_id=str(values["policy"]["owner_config_id"]),
        policy=values["policy"], binding=values["binding"], exchange=transport,
        request_signer=request_signer, now_epoch=int(time.time()),
    )
    if preloaded:
        assert _authorize(client, action) == "inert_callback_result"
        assert events == ["request_signer", "PROTECTED_USE_ACQUIRE", "callback",
                          "request_signer", "PROTECTED_USE_FINISH"]
        finished = values["state"].load(PROTECTED_USE_BINDING)
        assert before is None and finished is not None and finished.sequence == 2
    else:
        with pytest.raises(ValueError, match="^test_target_key_capability_unavailable$"):
            _authorize(client, action)
        assert events == ["request_signer", "request_signer"]
        assert values["state"].load(PROTECTED_USE_BINDING) == before


def _two_key_runtime(tmp_path, monkeypatch):
    from modules.communication.moltbot_bridge.tests import root_revocation_service_fixtures as fixture
    from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_authority import _private_key, _public_text

    control = _private_key()
    original = fixture._descriptor

    def descriptor(*args, **kwargs):
        overrides = dict(kwargs.get("descriptor_overrides", {}))
        overrides.update(schema_version="foundup_verified_outcome_root_authority.v2",
                         root_control_authentication={"purpose": "protected-use-acquire-finish.v1",
                             "public_key": _public_text(control), "key_epoch": "control-epoch-1"})
        kwargs["descriptor_overrides"] = overrides
        return original(*args, **kwargs)

    monkeypatch.setattr(fixture, "_descriptor", descriptor)
    values = runtime(tmp_path, monkeypatch)
    _install_current(values, signed_snapshot(values))
    return values, control


@pytest.mark.parametrize("proof_key", ["control", "work", "unrelated"])
def test_control_key_proof_precedes_work_key_access(tmp_path, monkeypatch, proof_key):
    from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_authority import _private_key

    values, control = _two_key_runtime(tmp_path, monkeypatch)
    key = {"control": control, "work": values["target_private"], "unrelated": _private_key()}[proof_key]
    events = []

    def roundtrip(_path, raw, _uid, _timeout):
        response = _route(values, raw)
        if protected_response_from_bytes(response).accepted:
            events.append(json.loads(raw)["operation"])
        return response

    def work():
        events.append("work_key_access")
        return _sign(values["target_private"], "bounded-test-work")

    monkeypatch.setattr(root_client_module, "_root_socket_roundtrip", roundtrip)
    client = _create_root_protected_use_authority(
        values["snapshot"].descriptor, owner_config_id=values["policy"]["owner_config_id"],
        policy=values["policy"], binding=values["binding"],
        exchange=_lookup_revocation_client(values["client"]).exchange,
        request_signer=lambda text: _sign(key, text), now_epoch=int(time.time()),
    )
    if proof_key != "control":
        with pytest.raises(ValueError, match="request_rejected"):
            _authorize(client, work)
        assert events == [] and values["state"].load(PROTECTED_USE_BINDING) is None
        return
    signature = _authorize(client, work)
    assert Ed25519SignatureVerifier().verify(values["policy"]["target_signer_public_key"], "bounded-test-work", signature)
    assert events == ["PROTECTED_USE_ACQUIRE", "work_key_access", "PROTECTED_USE_FINISH"]
    assert values["state"].load(PROTECTED_USE_BINDING).sequence == 2


def test_control_key_never_replaces_shared_work_proof(tmp_path, monkeypatch):
    from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_service import require_root_authority_signer_proof
    from modules.communication.moltbot_bridge.tests.root_revocation_service_fixtures import legacy_roundtrip

    values, control = _two_key_runtime(tmp_path, monkeypatch)
    _bind_router(values, monkeypatch)
    assert values["client"].load() is not None  # Existing work-key revocation proof.
    assert legacy_roundtrip(values, _lookup_revocation_client(values["client"]).exchange)
    with pytest.raises(ValueError, match="signer_proof_invalid"):
        require_root_authority_signer_proof(values["snapshot"], "bounded-test-work", _sign(control, "bounded-test-work"))


def test_control_key_cannot_load_revocations(tmp_path, monkeypatch):
    """Keep v2 control authentication confined to protected-use operations."""
    from dataclasses import asdict
    from modules.communication.moltbot_bridge.tests.test_foundup_verified_outcome_root_revocation_service import _request
    from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_revocation_protocol import (
        canonical_signer_input, request_id_for, response_from_bytes,
    )

    values, control = _two_key_runtime(tmp_path, monkeypatch)
    work = _request(values)
    before = values["state"].load(values["binding"].anchor_binding_digest())
    assert response_from_bytes(_route(values, work.to_bytes())).accepted is True
    forged = replace(work, signer_instance_signature=_sign(control, canonical_signer_input(work)))
    forged = replace(forged, request_id=request_id_for(asdict(forged)))
    response = response_from_bytes(_route(values, forged.to_bytes()))
    assert values["state"].load(values["binding"].anchor_binding_digest()) == before
    assert response.accepted is False


def _startup_materializer_owner(values, tmp_path, grant_fixture):
    from dataclasses import asdict
    from modules.infrastructure.secrets_mcp.src.systemd_credential_secret_resolver import SystemdCredentialBinding

    policy = values["policy"]
    config = grant_fixture.SignerGrantReplayStoreConfig(
        nonce_path=Path(policy["replay_path"]), nonce_root=Path(policy["replay_root"]),
        high_water_path=tmp_path / "startup-high-water" / "authority.sqlite3",
        high_water_root=tmp_path / "startup-high-water", repo_root=values["repo"],
        replay_store_binding_digest=grant_fixture._binding().replay_store_binding_digest,
        replay_store_id=policy["replay_store_id"],
        durability_receipt_id=policy["replay_store_durability_receipt_id"])
    grant_fixture._provision_store(config)  # Explicit test setup, never the materializer.
    now = int(time.time())
    binding = SystemdCredentialBinding(
        credential_directory="/run/credentials/startup-test.service",
        expected_uid=1001, expected_gid=1001, expected_requester="reddog-e0-signer",
        issued_at=now - 1, expires_at=now + 60, credential_ids=frozenset({"replay"}))
    metadata = asdict(binding)
    metadata["credential_ids"] = sorted(binding.credential_ids)
    owner = {"config_id": policy["owner_config_id"], "verified_outcome_authority": {
        "descriptor": values["snapshot"].descriptor,
        "authority_socket_path": str(tmp_path / "root-authority.sock"), "authority_service_uid": 0},
        "startup_custody": {"policy_path": str(tmp_path / "policy.json"),
            "credential_binding": metadata, "proposal_replay_store": None,
            "replay_store": {"high_water_path": str(config.high_water_path),
                "high_water_root": str(config.high_water_root),
                "replay_store_binding_digest": config.replay_store_binding_digest},
            "replay_integrity_permission": {"reference": "systemd-creds://replay",
                "requester_id": binding.expected_requester, "issued_at": now - 1,
                "expires_at": now + 30}}}
    return owner, binding, config


def _startup_materializer_case(tmp_path, monkeypatch):
    """Synthetic owner files, OS custody and proof keys; real leases, stores and RPC router."""
    from modules.communication.moltbot_bridge.src import reddog_signer_owner_e0_current_selection as owner_source
    from modules.communication.moltbot_bridge.src import reddog_signer_system_service_manifest_selection_loader as loader
    from modules.communication.moltbot_bridge.src import reddog_signer_system_service_wsp71_resolver_supply as supply
    from modules.communication.moltbot_bridge.tests import test_reddog_signer_socket_service_runtime_wiring as wiring_fixture
    from modules.infrastructure.secrets_mcp.src import systemd_credential_secret_resolver as credential_os

    now = int(time.time())
    monkeypatch.setattr(time, "time", lambda: now)
    values, control = _two_key_runtime(tmp_path, monkeypatch)
    grant_fixture = wiring_fixture.factory_fixture.grant_fixture
    owner, binding, replay = _startup_materializer_owner(values, tmp_path, grant_fixture)
    monkeypatch.setattr(loader, "_load_owner_config", lambda *args, **kwargs: copy.deepcopy(owner))
    monkeypatch.setattr(loader, "_read_root_owned_bytes", lambda *args: json.dumps(values["policy"]).encode("ascii"))
    events, secret_reads, active = [], [], []
    _track_materializer_lease(monkeypatch, owner_source, events, active)

    def request_signer(**kwargs):
        assert active
        key = values["target_private"] if kwargs["purpose"] == supply.ROOT_LOAD_PURPOSE else control
        return lambda message: _sign(key, message)

    def read_credential(selected, identifier):
        assert selected == binding
        secret_reads.append(identifier)
        return grant_fixture.INTEGRITY_KEY.decode("utf-8")

    def roundtrip(_path, raw, _uid, _timeout):
        assert active == [], "owner lease held across root transport"
        events.append(json.loads(raw)["operation"])
        return _route(values, raw)

    monkeypatch.setattr(supply, "build_system_service_root_request_signer", request_signer)
    monkeypatch.setattr(credential_os, "_identity_matches", lambda selected: selected == binding)
    monkeypatch.setattr(credential_os, "_read_credential", read_credential)
    monkeypatch.setattr(root_client_module, "_root_socket_roundtrip", roundtrip)
    return values, owner, binding, replay, events, secret_reads, active


def _track_materializer_lease(monkeypatch, owner_source, events, active):
    from contextlib import contextmanager

    original = owner_source.lease_validated_owner_e0_current_admission

    @contextmanager
    def lease(**kwargs):
        with original(**kwargs) as current:
            active.append(True)
            events.append("lease_enter")
            try:
                yield current
            finally:
                active.pop()
                events.append("lease_exit")

    monkeypatch.setattr(owner_source, "lease_validated_owner_e0_current_admission", lease)


def test_system_service_oracle_releases_owner_lease_before_real_root_rpc(tmp_path, monkeypatch):
    from modules.communication.moltbot_bridge.src import foundup_verified_outcome_root_runtime_materializer as materializer

    values, owner, binding, replay, events, reads, active = _startup_materializer_case(tmp_path, monkeypatch)
    oracle = materializer.materialize_system_service_revocation_oracle(
        owner_config_path=values["owner_config_path"], repo=values["repo"],
        policy=values["policy"], credential_binding=binding)
    assert type(oracle) is RootAuthorizedSignerGrantRevocationOracle
    assert active == [] and reads == []
    assert events == ["lease_enter", "lease_exit", "lease_enter", "lease_exit"]
    assert oracle.is_key_epoch_revoked(key_epoch="not-revoked", at_epoch=int(time.time())) is False
    grant = {"grant_id": _sha("startup-grant"), "key_epoch": "epoch-1",
             "signing_request_digest": _sha("startup-request"), "expires_at": int(time.time()) + 20}
    assert oracle.authorize_grant_use(grant, lambda: "inert-result") == "inert-result"
    assert "REVOCATION_ANCHOR_LOAD" in events
    assert "PROTECTED_USE_ACQUIRE" in events and "PROTECTED_USE_FINISH" in events
    assert active == []


def test_system_service_dependencies_compose_existing_provisioned_stores(tmp_path, monkeypatch):
    from modules.communication.moltbot_bridge.src import foundup_verified_outcome_root_runtime_materializer as materializer
    from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_bootstrap_admission import SignerSocketServiceRuntimeDependencies
    from modules.communication.moltbot_bridge.src.reddog_signer_independent_secret_grant_binding import require_owner_bound_replay_store

    values, owner, binding, replay, events, reads, active = _startup_materializer_case(tmp_path, monkeypatch)
    dependencies = materializer.materialize_system_service_runtime_dependencies(
        owner_config_path=values["owner_config_path"], repo=values["repo"],
        expected_owner_config_id=owner["config_id"])
    assert type(dependencies) is SignerSocketServiceRuntimeDependencies
    assert reads == ["replay"] and active == []
    assert dependencies.proposal_replay_high_water_store is None
    admission = dependencies.secret_grant_admission
    require_owner_bound_replay_store(values["policy"], admission.replay_store, repo_root=values["repo"])
    assert admission.revocation_oracle.matches_owner(policy=values["policy"], binding=values["binding"])
    assert admission.revocation_oracle.is_key_epoch_revoked(
        key_epoch="not-revoked", at_epoch=int(time.time())) is False
    assert "REVOCATION_ANCHOR_LOAD" in events and active == []


@pytest.mark.parametrize("missing", ["nonce", "high_water", "unprovisioned_high_water"])
def test_system_service_dependencies_reject_unprovisioned_replay_without_secret_reads(tmp_path, monkeypatch, missing):
    import sqlite3
    from modules.communication.moltbot_bridge.src import foundup_verified_outcome_root_runtime_materializer as materializer

    values, owner, binding, replay, events, reads, active = _startup_materializer_case(tmp_path, monkeypatch)
    if missing == "nonce":
        replay.nonce_path.unlink()
    elif missing == "high_water":
        replay.high_water_path.unlink()
    else:
        replay.high_water_path.write_bytes(b"")
    paths = (replay.nonce_path, replay.high_water_path)
    before = {str(p): p.read_bytes() if p.exists() else None for p in paths}
    inventory = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*") if p.is_file())
    with pytest.raises((ValueError, sqlite3.DatabaseError)):
        materializer.materialize_system_service_runtime_dependencies(
            owner_config_path=values["owner_config_path"], repo=values["repo"],
            expected_owner_config_id=owner["config_id"])
    assert reads == [] and active == []
    assert not any(event.startswith("REVOCATION_") or event.startswith("PROTECTED_USE_") for event in events)
    assert {str(p): p.read_bytes() if p.exists() else None for p in paths} == before
    assert sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*") if p.is_file()) == inventory
