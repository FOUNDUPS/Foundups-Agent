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
    revocation = _lookup_revocation_client(values["client"])
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
    grant = {
        "grant_id": _sha("grant"), "key_epoch": "epoch-1",
        "signing_request_digest": _sha("request"),
        "expires_at": int(time.time()) + 120,
    }
    assert composed.authorize_grant_use(grant, lambda: "signed") == "signed"

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
    assert not any(
        path.endswith("reddog_signer_resolve_per_sign_backend.py")
        for path in bound
    )
