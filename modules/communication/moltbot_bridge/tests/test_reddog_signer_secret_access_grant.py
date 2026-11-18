from __future__ import annotations

import ast
import copy
import pickle
import threading
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

import pytest

from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    public_key_fingerprint,
)

from modules.communication.moltbot_bridge.src.reddog_signer_secret_access_grant import (
    ExpectedSignerSecretGrantBinding,
    GRANT_SCHEMA,
    REJECT_BINDING,
    REJECT_CAPABILITY,
    REJECT_DIGEST,
    REJECT_GRANT_ID,
    REJECT_ISSUER,
    REJECT_MALFORMED,
    REJECT_NONCE,
    REJECT_REVOKED,
    REJECT_SIGNATURE,
    REJECT_TIME,
    SignerSecretAccessGrantBoundary,
    SignerSecretAccessGrantRejected,
    canonical_signer_secret_access_grant_input,
    signer_secret_access_grant_id,
)

NOW = 1_780_000_000
SOURCE = Path(__file__).parents[1] / "src" / "reddog_signer_secret_access_grant.py"
CONTRACT_SOURCE = (
    Path(__file__).parents[1]
    / "src"
    / "reddog_signer_secret_access_grant_contract.py"
)


def _digest(character: str) -> str:
    return "sha256:" + (character * 64)


def _grant(**overrides: Any) -> dict[str, Any]:
    value = {
        "schema_version": GRANT_SCHEMA,
        "issuer_principal_id": "principal:founder",
        "issuer_principal_provider": "github",
        "issuer_public_key": "public-key-v1:issuer",
        "signer_agent_id": "signer:reddog",
        "signer_profile_id": "reddog-work-authority",
        "signing_key_ref_hash": _digest("1"),
        "audit_mac_key_ref_hash": _digest("2"),
        "key_epoch": "epoch-1",
        "permission_snapshot_digest": _digest("3"),
        "owner_config_id": _digest("4"),
        "signer_generation_id": _digest("5"),
        "signer_public_key": "public-key-v1:signer",
        "signer_key_fingerprint": public_key_fingerprint(
            "public-key-v1:signer"
        ),
        "replay_store_binding_digest": _digest("7"),
        "replay_store_id": "signer-grant-replay:test",
        "replay_store_durability_receipt_id": _digest("8"),
        "replay_store_instance_digest": _digest("9"),
        "signing_request_digest": _digest("6"),
        "requested_operation": "write_repo",
        "authority_tier": "HIGH",
        "attested_peer_principal_id": "principal:founder",
        "nonce": "grant-nonce-1",
        "issued_at": NOW - 10,
        "expires_at": NOW + 100,
        "grant_id": "",
        "signature": "fixture-signature-v2",
    }
    value.update(overrides)
    value["grant_id"] = signer_secret_access_grant_id(value)
    return value


def _binding(grant: Mapping[str, Any]) -> ExpectedSignerSecretGrantBinding:
    names = {field.name for field in ExpectedSignerSecretGrantBinding.__dataclass_fields__.values()}
    return ExpectedSignerSecretGrantBinding(**{name: str(grant[name]) for name in names})


class _Verifier:
    def __init__(self) -> None:
        self.allowed: set[tuple[str, str, str]] = set()

    def allow(self, grant: Mapping[str, Any]) -> None:
        self.allowed.add((
            str(grant["issuer_public_key"]),
            canonical_signer_secret_access_grant_input(grant),
            str(grant["signature"]),
        ))

    def verify(self, public_key: str, signing_input: str, signature: str) -> bool:
        return (public_key, signing_input, signature) in self.allowed


class _RaisingVerifier(_Verifier):
    def verify(self, public_key: str, signing_input: str, signature: str) -> bool:
        raise RuntimeError("unavailable")


class _Resolver:
    def __init__(self, public_key: str = "public-key-v1:issuer") -> None:
        self.public_key = public_key

    def resolve(self, principal_id: str, principal_provider: str) -> str | None:
        if (principal_id, principal_provider) == ("principal:founder", "github"):
            return self.public_key
        return None


class _RaisingResolver(_Resolver):
    def resolve(self, principal_id: str, principal_provider: str) -> str | None:
        raise RuntimeError("unavailable")


class _NonceStore:
    def __init__(self) -> None:
        self.seen: set[str] = set()
        self.calls: list[str] = []
        self.lock = threading.Lock()

    def consume(self, nonce: str) -> bool:
        with self.lock:
            self.calls.append(nonce)
            if nonce in self.seen:
                return False
            self.seen.add(nonce)
            return True


class _Clock:
    def __init__(self, now: int = NOW) -> None:
        self.now = now
        self.raise_error = False

    def __call__(self) -> int:
        if self.raise_error:
            raise RuntimeError("unavailable")
        return self.now


class _RevocationOracle:
    def __init__(self) -> None:
        self.grant_ids: set[str] = set()
        self.key_epochs: set[str] = set()
        self.raise_error = False
        self.override = False
        self.verdict: object | None = None

    def is_revoked(self, *, grant_id: str, key_epoch: str, at_epoch: int) -> bool:
        if self.raise_error:
            raise RuntimeError("unavailable")
        if self.override:
            return self.verdict  # type: ignore[return-value]
        return grant_id in self.grant_ids or key_epoch in self.key_epochs


def _verify(
    grant: Mapping[str, Any], *, expected: ExpectedSignerSecretGrantBinding | None = None,
    verifier: _Verifier | None = None, resolver: _Resolver | None = None,
    nonce_store: _NonceStore | None = None, clock: _Clock | None = None,
    revocation: _RevocationOracle | None = None,
) -> tuple[
    SignerSecretAccessGrantBoundary, object, _NonceStore, _Clock,
    _RevocationOracle,
]:
    effective_verifier = verifier or _Verifier()
    effective_verifier.allow(grant)
    store = nonce_store or _NonceStore()
    effective_clock = clock or _Clock()
    effective_revocation = revocation or _RevocationOracle()
    boundary = SignerSecretAccessGrantBoundary(
        nonce_store=store,
        revocation_oracle=effective_revocation,
        clock=effective_clock,
    )
    capability = boundary.verify(
        grant, expected=expected or _binding(grant),
        signature_verifier=effective_verifier,
        principal_key_resolver=resolver or _Resolver(),
    )
    return boundary, capability, store, effective_clock, effective_revocation


def _rejection(call: Any, code: str) -> None:
    with pytest.raises(SignerSecretAccessGrantRejected) as raised:
        call()
    assert raised.value.reason_code == code
    assert str(raised.value) == code


def test_valid_grant_verifies_and_consumes_to_immutable_mapping() -> None:
    grant = _grant()
    boundary, capability, store, _clock, _revocation = _verify(grant)
    assert store.calls == []
    consumed = boundary.consume(capability)
    assert type(consumed) is MappingProxyType
    assert dict(consumed) == grant
    assert store.calls == ["grant-nonce-1"]
    with pytest.raises(TypeError):
        consumed["key_epoch"] = "changed"  # type: ignore[index]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("signing_key_ref_hash", _digest("a")),
        ("audit_mac_key_ref_hash", _digest("b")),
        ("signer_agent_id", "signer:other"),
        ("signer_profile_id", "other-profile"),
        ("key_epoch", "epoch-2"),
        ("signer_generation_id", _digest("c")),
        ("signer_public_key", "public-key-v1:other"),
        ("signer_key_fingerprint", _digest("f")),
        ("replay_store_binding_digest", _digest("a")),
        ("replay_store_id", "signer-grant-replay:other"),
        ("replay_store_durability_receipt_id", _digest("b")),
        ("replay_store_instance_digest", _digest("c")),
        ("owner_config_id", _digest("d")),
        ("permission_snapshot_digest", _digest("e")),
        ("issuer_principal_id", "principal:other"),
        ("issuer_principal_provider", "intake_session"),
        ("issuer_public_key", "public-key-v1:other"),
        ("signing_request_digest", _digest("f")),
        ("requested_operation", "publish_draft_pr"),
        ("authority_tier", "LOW"),
        ("attested_peer_principal_id", "principal:other"),
    ],
)
def test_changed_expected_binding_rejects(field: str, value: str) -> None:
    grant = _grant()
    changed = _grant(**{field: value})
    store = _NonceStore()
    _rejection(
        lambda: _verify(changed, expected=_binding(grant), nonce_store=store),
        REJECT_BINDING,
    )
    assert store.calls == []


def test_forged_issuer_key_rejects_before_nonce() -> None:
    forged = _grant(issuer_public_key="public-key-v1:forged")
    store = _NonceStore()
    _rejection(lambda: _verify(forged, nonce_store=store), REJECT_ISSUER)
    assert store.calls == []


def test_invalid_signature_rejects_without_consuming_nonce() -> None:
    grant = _grant()
    store = _NonceStore()
    boundary = SignerSecretAccessGrantBoundary(
        nonce_store=store, revocation_oracle=_RevocationOracle(), clock=_Clock()
    )
    _rejection(
        lambda: boundary.verify(
            grant, expected=_binding(grant), signature_verifier=_Verifier(),
            principal_key_resolver=_Resolver(),
        ),
        REJECT_SIGNATURE,
    )
    assert store.calls == []


@pytest.mark.parametrize(
    ("resolver", "verifier"),
    [(_RaisingResolver(), _Verifier()), (_Resolver(), _RaisingVerifier())],
)
def test_dependency_failure_rejects_without_consuming_nonce(
    resolver: _Resolver, verifier: _Verifier
) -> None:
    grant = _grant()
    if type(verifier) is _Verifier:
        verifier.allow(grant)
    store = _NonceStore()
    code = REJECT_ISSUER if isinstance(resolver, _RaisingResolver) else REJECT_SIGNATURE
    _rejection(
        lambda: _verify(
            grant, resolver=resolver, verifier=verifier, nonce_store=store
        ),
        code,
    )
    assert store.calls == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"issued_at": NOW - 100, "expires_at": NOW},
        {"issued_at": NOW + 1, "expires_at": NOW + 100},
        {"issued_at": NOW - 10, "expires_at": NOW + 291},
    ],
)
def test_expired_future_and_overlong_grants_reject(overrides: dict[str, int]) -> None:
    grant = _grant(**overrides)
    _rejection(lambda: _verify(grant), REJECT_TIME)


def test_recomputed_grant_id_does_not_repair_old_signature() -> None:
    original = _grant()
    verifier = _Verifier()
    verifier.allow(original)
    attacked = _grant(signing_key_ref_hash=_digest("a"), signature=original["signature"])
    store = _NonceStore()
    boundary = SignerSecretAccessGrantBoundary(
        nonce_store=store, revocation_oracle=_RevocationOracle(), clock=_Clock()
    )
    _rejection(
        lambda: boundary.verify(
            attacked, expected=_binding(attacked), signature_verifier=verifier,
            principal_key_resolver=_Resolver(),
        ),
        REJECT_SIGNATURE,
    )
    assert store.calls == []


def test_stale_grant_id_rejects_before_signature_and_nonce() -> None:
    grant = _grant()
    grant["grant_id"] = _digest("f")
    store = _NonceStore()
    _rejection(lambda: _verify(grant, nonce_store=store), REJECT_GRANT_ID)
    assert store.calls == []


def test_nonce_replay_rejects() -> None:
    grant = _grant()
    store = _NonceStore()
    first, first_capability, *_ = _verify(grant, nonce_store=store)
    second, second_capability, *_ = _verify(grant, nonce_store=store)
    assert dict(first.consume(first_capability)) == grant
    _rejection(lambda: second.consume(second_capability), REJECT_NONCE)
    assert store.calls == ["grant-nonce-1", "grant-nonce-1"]


@pytest.mark.parametrize("revocation_kind", ["key_epoch", "grant_id"])
def test_revoked_key_epoch_or_grant_rejects_before_nonce(
    revocation_kind: str,
) -> None:
    grant = _grant()
    store = _NonceStore()
    revocation = _RevocationOracle()
    boundary, capability, *_ = _verify(
        grant, nonce_store=store, revocation=revocation
    )
    target = (
        revocation.key_epochs
        if revocation_kind == "key_epoch"
        else revocation.grant_ids
    )
    target.add(
        str(
            grant[
                "key_epoch" if revocation_kind == "key_epoch" else "grant_id"
            ]
        )
    )
    _rejection(
        lambda: boundary.consume(capability),
        REJECT_REVOKED,
    )
    assert store.calls == []


def test_expiry_or_revocation_failure_at_use_burns_capability() -> None:
    grant = _grant()
    clock = _Clock()
    boundary, capability, store, *_ = _verify(grant, clock=clock)
    clock.now = int(grant["expires_at"])
    _rejection(lambda: boundary.consume(capability), REJECT_TIME)
    _rejection(lambda: boundary.consume(capability), REJECT_CAPABILITY)
    assert store.calls == []

    revocation = _RevocationOracle()
    boundary, capability, store, *_ = _verify(grant, revocation=revocation)
    revocation.raise_error = True
    _rejection(lambda: boundary.consume(capability), REJECT_REVOKED)
    _rejection(lambda: boundary.consume(capability), REJECT_CAPABILITY)
    assert store.calls == []


@pytest.mark.parametrize("verdict", [None, 1, "revoked", object()])
def test_malformed_revocation_verdict_fails_closed(
    verdict: object,
) -> None:
    grant = _grant()
    revocation = _RevocationOracle()
    revocation.override = True
    revocation.verdict = verdict
    store = _NonceStore()
    _rejection(
        lambda: _verify(grant, revocation=revocation, nonce_store=store),
        REJECT_REVOKED,
    )
    assert store.calls == []

    revocation.override = False
    boundary, capability, store, *_ = _verify(
        grant, revocation=revocation, nonce_store=store
    )
    revocation.override = True
    revocation.verdict = verdict
    _rejection(lambda: boundary.consume(capability), REJECT_REVOKED)
    _rejection(lambda: boundary.consume(capability), REJECT_CAPABILITY)
    assert store.calls == []


def test_clock_failure_fails_closed_and_burns_issued_capability() -> None:
    grant = _grant()
    clock = _Clock()
    clock.raise_error = True
    _rejection(lambda: _verify(grant, clock=clock), REJECT_TIME)

    clock.raise_error = False
    boundary, capability, store, *_ = _verify(grant, clock=clock)
    clock.raise_error = True
    _rejection(lambda: boundary.consume(capability), REJECT_TIME)
    _rejection(lambda: boundary.consume(capability), REJECT_CAPABILITY)
    assert store.calls == []


def test_nonce_store_failure_at_use_burns_capability() -> None:
    class RaisingNonceStore(_NonceStore):
        def consume(self, nonce: str) -> bool:
            raise RuntimeError("unavailable")

    grant = _grant()
    boundary, capability, *_ = _verify(grant, nonce_store=RaisingNonceStore())
    _rejection(lambda: boundary.consume(capability), REJECT_NONCE)
    _rejection(lambda: boundary.consume(capability), REJECT_CAPABILITY)


def test_concurrent_capability_consumption_has_one_authoritative_use() -> None:
    grant = _grant()
    boundary, capability, store, *_ = _verify(grant)
    barrier = threading.Barrier(3)
    outcomes: list[str] = []

    def consume() -> None:
        barrier.wait()
        try:
            boundary.consume(capability)
            outcomes.append("accepted")
        except SignerSecretAccessGrantRejected as exc:
            outcomes.append(exc.reason_code)

    threads = [threading.Thread(target=consume) for _ in range(2)]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join()
    assert sorted(outcomes) == [REJECT_CAPABILITY, "accepted"]
    assert store.calls == ["grant-nonce-1"]


def test_two_capabilities_with_one_nonce_have_one_authoritative_use() -> None:
    grant = _grant()
    store = _NonceStore()
    first, first_capability, *_ = _verify(grant, nonce_store=store)
    second, second_capability, *_ = _verify(grant, nonce_store=store)
    barrier = threading.Barrier(3)
    outcomes: list[str] = []

    def consume(boundary: SignerSecretAccessGrantBoundary, capability: object) -> None:
        barrier.wait()
        try:
            boundary.consume(capability)
            outcomes.append("accepted")
        except SignerSecretAccessGrantRejected as exc:
            outcomes.append(exc.reason_code)

    threads = [
        threading.Thread(target=consume, args=(first, first_capability)),
        threading.Thread(target=consume, args=(second, second_capability)),
    ]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join()
    assert sorted(outcomes) == [REJECT_NONCE, "accepted"]


def test_negative_clock_or_timestamps_reject() -> None:
    grant = _grant(issued_at=-1, expires_at=NOW + 10)
    _rejection(lambda: _verify(grant), REJECT_TIME)
    valid = _grant()
    verifier = _Verifier()
    verifier.allow(valid)
    clock = _Clock(-1)
    boundary = SignerSecretAccessGrantBoundary(
        nonce_store=_NonceStore(),
        revocation_oracle=_RevocationOracle(),
        clock=clock,
    )
    _rejection(
        lambda: boundary.verify(
            valid,
            expected=_binding(valid),
            signature_verifier=verifier,
            principal_key_resolver=_Resolver(),
        ),
        REJECT_TIME,
    )


def test_capability_is_process_local_immutable_and_one_shot() -> None:
    grant = _grant()
    boundary, capability, _store, _clock, _revocation = _verify(grant)
    fabricated = capability.__class__()
    _rejection(lambda: boundary.consume(fabricated), REJECT_CAPABILITY)
    with pytest.raises(TypeError):
        copy.copy(capability)
    with pytest.raises(TypeError):
        copy.deepcopy(capability)
    with pytest.raises(TypeError):
        pickle.dumps(capability)
    with pytest.raises(TypeError):
        setattr(capability, "_seal", object())
    assert dict(boundary.consume(capability)) == grant
    _rejection(lambda: boundary.consume(capability), REJECT_CAPABILITY)


def test_object_level_mutation_invalidates_capability() -> None:
    grant = _grant()
    boundary, capability, _store, _clock, _revocation = _verify(grant)
    object.__setattr__(capability, "_seal", object())
    _rejection(lambda: boundary.consume(capability), REJECT_CAPABILITY)


def test_malformed_expected_binding_rejects_before_nonce() -> None:
    grant = _grant()
    store = _NonceStore()
    expected = replace(_binding(grant), signer_agent_id="")
    _rejection(
        lambda: _verify(grant, expected=expected, nonce_store=store), REJECT_BINDING
    )
    assert store.calls == []


def test_exact_fields_ascii_and_sha256_formats_are_enforced() -> None:
    missing = _grant()
    missing.pop("nonce")
    extra = _grant()
    extra["unexpected"] = "value"
    non_ascii = _grant(signer_agent_id="signer:\u2603")
    bad_digest = _grant(permission_snapshot_digest="sha256:not-a-digest")
    wrong_schema = _grant(schema_version="reddog-signer-secret-access-grant.v1")
    boolean_time = _grant(issued_at=True)
    oversized = _grant(signer_agent_id="s" * 4097)
    oversized_nonce = _grant(nonce="n" * 257)
    _rejection(lambda: _verify(missing), REJECT_MALFORMED)
    _rejection(lambda: _verify(extra), REJECT_MALFORMED)
    _rejection(lambda: _verify(non_ascii), "REJECT_SECRET_GRANT_NON_ASCII")
    _rejection(lambda: _verify(bad_digest), REJECT_DIGEST)
    _rejection(lambda: _verify(wrong_schema), REJECT_MALFORMED)
    _rejection(lambda: _verify(boolean_time), REJECT_MALFORMED)
    _rejection(lambda: _verify(oversized), REJECT_MALFORMED)
    _rejection(lambda: _verify(oversized_nonce), REJECT_MALFORMED)


def test_canonicalization_is_mapping_order_independent() -> None:
    grant = _grant()
    reordered = dict(reversed(tuple(grant.items())))
    assert signer_secret_access_grant_id(reordered) == grant["grant_id"]
    assert (
        canonical_signer_secret_access_grant_input(reordered)
        == canonical_signer_secret_access_grant_input(grant)
    )


def test_ast_has_no_secret_provider_or_execution_side_effects() -> None:
    sources = [
        SOURCE.read_text(encoding="utf-8"),
        CONTRACT_SOURCE.read_text(encoding="utf-8"),
    ]
    tree = ast.parse("\n".join(sources))
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    calls = {
        node.func.id if isinstance(node.func, ast.Name) else node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, (ast.Name, ast.Attribute))
    }
    assert not imports.intersection({"os", "subprocess", "pathlib", "socket", "requests"})
    assert not calls.intersection({
        "open", "eval", "exec", "system", "popen", "run", "get_secret",
        "resolve_secret", "sign", "generate_key", "write_text", "write_bytes",
    })
    for source in sources:
        logical = [
            line for line in source.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        assert len(logical) <= 200
        assert all(ord(character) < 128 for character in source)
        assert "\x00" not in source
