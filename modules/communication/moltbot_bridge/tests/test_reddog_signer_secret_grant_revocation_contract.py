from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Mapping

import pytest

from modules.communication.moltbot_bridge.src.reddog_signer_secret_grant_revocation_contract import (
    SNAPSHOT_SCHEMA,
    ExpectedSignerGrantRevocationBinding,
    canonical_signer_grant_revocation_snapshot_input,
    signer_grant_revocation_snapshot_id,
    verify_signer_grant_revocation_snapshot,
)

NOW = 1_780_000_000
SRC = Path(__file__).parents[1] / "src"
DIGEST_9 = "sha256:" + "9" * 64
DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64


def _digest(char: str) -> str:
    return "sha256:" + char * 64


def _expected() -> ExpectedSignerGrantRevocationBinding:
    return ExpectedSignerGrantRevocationBinding(
        policy_id=_digest("1"), owner_config_id=_digest("2"),
        manifest_id=_digest("3"), artifact_generation_digest=_digest("4"),
        authority_principal_id="principal:revocation-admin",
        authority_principal_provider="github",
        authority_public_key="public-key-v1:revocation-admin",
        target_signer_agent_id="signer:reddog",
        target_signer_profile_id="reddog-work-authority",
        target_signer_public_key="public-key-v1:target",
        target_signer_key_epoch="target-epoch-1",
        target_signer_generation_id=_digest("5"),
        store_id="signer-grant-revocations",
        durability_receipt_id=_digest("6"),
    )


def _snapshot(**overrides: Any) -> dict[str, Any]:
    value = {
        "schema_version": SNAPSHOT_SCHEMA, "snapshot_id": _digest("0"),
        **_expected().__dict__, "sequence": 1, "issued_at": NOW - 10,
        "expires_at": NOW + 100, "revoked_grant_ids": [],
        "revoked_key_epochs": [], "signature": "signature-v1",
    }
    value.update(overrides)
    value["snapshot_id"] = signer_grant_revocation_snapshot_id(value)
    return value


class _Resolver:
    def __init__(self, key: str = "public-key-v1:revocation-admin") -> None:
        self.key = key

    def resolve(self, principal_id: str, principal_provider: str) -> str | None:
        if (principal_id, principal_provider) == (
            "principal:revocation-admin", "github"
        ):
            return self.key
        return None


class _Verifier:
    def __init__(self, allowed: Mapping[str, Any]) -> None:
        self.allowed = (
            str(allowed["authority_public_key"]),
            canonical_signer_grant_revocation_snapshot_input(allowed),
            str(allowed["signature"]),
        )

    def verify(self, public_key: str, signing_input: str, signature: str) -> bool:
        return (public_key, signing_input, signature) == self.allowed


def _verify(
    snapshot: Mapping[str, Any], signed: Mapping[str, Any] | None = None,
    expected: ExpectedSignerGrantRevocationBinding | object | None = None,
):
    return verify_signer_grant_revocation_snapshot(
        snapshot, expected=expected or _expected(), principal_key_resolver=_Resolver(),
        signature_verifier=_Verifier(signed or snapshot), now_epoch=NOW,
    )


def test_valid_snapshot_verifies_exact_authority_and_binding() -> None:
    snapshot = _snapshot(revoked_grant_ids=[_digest("a")])
    checked = _verify(snapshot)
    assert checked["snapshot_id"] == snapshot["snapshot_id"]
    assert checked["revoked_grant_ids"] == [_digest("a")]


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("policy_id", DIGEST_9, "binding_invalid"),
        ("store_id", "attacker-store", "binding_invalid"),
        ("durability_receipt_id", DIGEST_9, "binding_invalid"),
        ("expires_at", NOW, "time_invalid"),
        ("sequence", 0, "time_invalid"),
        ("revoked_grant_ids", [DIGEST_B, DIGEST_A], "scope_invalid"),
        ("revoked_key_epochs", ["epoch-1", "epoch-1"], "scope_invalid"),
    ],
)
def test_binding_time_and_scope_fail_closed(
    field: str, value: Any, error: str,
) -> None:
    with pytest.raises(ValueError, match=error):
        _verify(_snapshot(**{field: value}))


def test_attacker_rehash_cannot_repair_signature_or_authority() -> None:
    original = _snapshot()
    tampered = _snapshot(revoked_key_epochs=["target-epoch-1"])
    with pytest.raises(ValueError, match="authority_invalid"):
        _verify(tampered, original)
    with pytest.raises(ValueError, match="authority_invalid"):
        verify_signer_grant_revocation_snapshot(
            original, expected=_expected(),
            principal_key_resolver=_Resolver("public-key-v1:attacker"),
            signature_verifier=_Verifier(original), now_epoch=NOW,
        )


def test_target_signer_cannot_be_revocation_authority() -> None:
    expected = _expected()
    object.__setattr__(
        expected, "target_signer_public_key", expected.authority_public_key
    )
    snapshot = _snapshot(
        target_signer_public_key=expected.target_signer_public_key
    )
    with pytest.raises(ValueError, match="self_authority_rejected"):
        _verify(snapshot, expected=expected)


def test_expected_binding_must_be_exact_typed_contract() -> None:
    class ForgedExpected:
        __dataclass_fields__: dict[str, object] = {}

    snapshot = _snapshot()
    with pytest.raises(ValueError, match="binding_invalid"):
        _verify(snapshot, expected=ForgedExpected())

    class DerivedBinding(ExpectedSignerGrantRevocationBinding):
        pass

    with pytest.raises(ValueError, match="binding_invalid"):
        _verify(snapshot, expected=DerivedBinding(**_expected().__dict__))


def test_tuple_representation_is_not_normalized_into_signed_list() -> None:
    snapshot = _snapshot()
    snapshot["revoked_grant_ids"] = tuple(snapshot["revoked_grant_ids"])
    with pytest.raises(ValueError, match="malformed"):
        _verify(snapshot)


@pytest.mark.parametrize("item", [1, ["nested"]])
def test_malformed_list_items_fail_closed_without_type_error(item: Any) -> None:
    snapshot = _snapshot(revoked_key_epochs=[item])
    with pytest.raises(ValueError, match="scope_invalid"):
        _verify(snapshot)


@pytest.mark.parametrize(
    "mutate,error",
    [
        (lambda value: value.update({"extra": "field"}), "malformed"),
        (lambda value: value.update({"store_id": "x" * 4097}), "malformed"),
    ],
)
def test_unknown_or_oversized_fields_fail_closed(mutate, error: str) -> None:
    snapshot = _snapshot()
    mutate(snapshot)
    with pytest.raises(ValueError, match=error):
        _verify(snapshot)


def test_contract_has_no_effect_or_secret_provider_primitives() -> None:
    path = SRC / "reddog_signer_secret_grant_revocation_contract.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert not imports.intersection(
        {"subprocess", "requests", "httpx", "socket", "cryptography", "sqlite3"}
    )
    assert len(source.splitlines()) <= 200
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            assert node.end_lineno - node.lineno + 1 <= 50, node.name
